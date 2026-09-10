//! Security circuit breakers — runtime tool-call anomaly monitor.
//!
//! Rust port of `whitemagic/security/security_breaker.py` (Edgerunner
//! Violet security layer). Detects suspicious tool-call patterns and
//! returns graduated responses (log / warn / throttle / block):
//!
//! - **rapid_fire**: N calls to the same tool within a window
//! - **lateral_movement**: many distinct tools in a short window
//! - **escalation**: READ → WRITE → DELETE sequencing
//! - **mutation_burst**: repeated WRITE/DELETE operations in a window
//!
//! The monitor is in-memory and per-process. It runs alongside the
//! dispatch pipeline's availability circuit breakers — this one is
//! security-shaped, not availability-shaped.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::collections::{HashMap, VecDeque};
use std::sync::{Arc, Mutex, MutexGuard};
use std::time::{Instant, SystemTime, UNIX_EPOCH};
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};

const MAX_CALL_LOG: usize = 10_000;
const MAX_ALERTS: usize = 5_000;

/// A security anomaly detection alert.
#[derive(Debug, Clone)]
pub struct SecurityAlert {
    /// Pattern name (`rapid_fire`, `lateral_movement`, `escalation`, `mutation_burst`).
    pub pattern: String,
    /// Severity 0.0–1.0.
    pub severity: f64,
    /// Graduated action: `log` | `warn` | `throttle` | `block`.
    pub action: String,
    /// Tool that triggered (or `*` for multi-tool patterns).
    pub tool: String,
    /// Human-readable detail.
    pub detail: String,
    /// Unix epoch seconds (fractional) for parity with the Python original.
    pub timestamp: f64,
}

impl SecurityAlert {
    fn to_json(&self) -> Value {
        json!({
            "pattern": self.pattern,
            "severity": self.severity,
            "action": self.action,
            "tool": self.tool,
            "detail": self.detail,
            "timestamp": self.timestamp,
        })
    }
}

struct CallEntry {
    tool: String,
    safety: String,
    #[allow(dead_code)]
    agent_id: String,
    at: Instant,
}

fn now_unix_f64() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0.0, |d| d.as_secs_f64())
}

/// Monitors tool-call patterns for security anomalies.
pub struct SecurityMonitor {
    rapid_fire_threshold: usize,
    rapid_fire_window_s: f64,
    lateral_threshold: usize,
    lateral_window_s: f64,
    escalation_window_s: f64,
    call_log: VecDeque<CallEntry>,
    per_tool_times: HashMap<String, VecDeque<Instant>>,
    alerts: VecDeque<SecurityAlert>,
    total_calls: u64,
    blocked_count: u64,
}

impl Default for SecurityMonitor {
    fn default() -> Self {
        Self::new()
    }
}

impl SecurityMonitor {
    /// Create a monitor with the Python defaults (10/5s, 15/10s, 30s).
    #[must_use]
    pub fn new() -> Self {
        Self {
            rapid_fire_threshold: 10,
            rapid_fire_window_s: 5.0,
            lateral_threshold: 15,
            lateral_window_s: 10.0,
            escalation_window_s: 30.0,
            call_log: VecDeque::with_capacity(MAX_CALL_LOG),
            per_tool_times: HashMap::new(),
            alerts: VecDeque::new(),
            total_calls: 0,
            blocked_count: 0,
        }
    }

    /// Record a tool call and check for anomalies. Returns an alert when
    /// one fires, otherwise `None`.
    pub fn record_call(
        &mut self,
        tool: &str,
        safety: &str,
        agent_id: &str,
    ) -> Option<SecurityAlert> {
        let now = Instant::now();
        let safety = safety.to_ascii_uppercase();
        if self.call_log.len() == MAX_CALL_LOG {
            self.call_log.pop_front();
        }
        self.call_log.push_back(CallEntry {
            tool: tool.to_string(),
            safety: safety.clone(),
            agent_id: agent_id.to_string(),
            at: now,
        });
        let times = self.per_tool_times.entry(tool.to_string()).or_default();
        if times.len() >= 200 {
            times.pop_front();
        }
        times.push_back(now);
        self.total_calls += 1;

        let alert = self
            .check_rapid_fire(tool, now)
            .or_else(|| self.check_lateral_movement(now))
            .or_else(|| self.check_escalation(tool, &safety, now));

        if let Some(alert) = &alert {
            if self.alerts.len() == MAX_ALERTS {
                self.alerts.pop_front();
            }
            if alert.action == "block" {
                self.blocked_count += 1;
            }
            self.alerts.push_back(alert.clone());
        }
        alert
    }

    fn check_rapid_fire(&self, tool: &str, now: Instant) -> Option<SecurityAlert> {
        let times = self.per_tool_times.get(tool)?;
        let cutoff = now
            .checked_sub(std::time::Duration::from_secs_f64(self.rapid_fire_window_s))
            .unwrap_or(now);
        let recent = times.iter().filter(|t| **t >= cutoff).count();
        if recent >= self.rapid_fire_threshold {
            let severity = (recent as f64 / (self.rapid_fire_threshold as f64 * 2.0)).min(1.0);
            let action = if recent >= self.rapid_fire_threshold * 2 {
                "block"
            } else {
                "throttle"
            };
            return Some(SecurityAlert {
                pattern: "rapid_fire".into(),
                severity,
                action: action.into(),
                tool: tool.to_string(),
                detail: format!(
                    "{recent} calls to '{tool}' in {}s (threshold: {})",
                    self.rapid_fire_window_s, self.rapid_fire_threshold
                ),
                timestamp: now_unix_f64(),
            });
        }
        None
    }

    fn check_lateral_movement(&self, now: Instant) -> Option<SecurityAlert> {
        let cutoff = now
            .checked_sub(std::time::Duration::from_secs_f64(self.lateral_window_s))
            .unwrap_or(now);
        let mut recent_tools = std::collections::HashSet::new();
        for entry in self.call_log.iter().rev() {
            if entry.at < cutoff {
                break;
            }
            recent_tools.insert(entry.tool.as_str());
        }
        let distinct = recent_tools.len();
        if distinct >= self.lateral_threshold {
            let severity = (distinct as f64 / (self.lateral_threshold as f64 * 2.0)).min(1.0);
            return Some(SecurityAlert {
                pattern: "lateral_movement".into(),
                severity,
                action: "warn".into(),
                tool: "*".into(),
                detail: format!(
                    "{distinct} distinct tools called in {}s (threshold: {})",
                    self.lateral_window_s, self.lateral_threshold
                ),
                timestamp: now_unix_f64(),
            });
        }
        None
    }

    fn check_escalation(&self, tool: &str, safety: &str, now: Instant) -> Option<SecurityAlert> {
        if safety != "WRITE" && safety != "DELETE" {
            return None;
        }
        let cutoff = now
            .checked_sub(std::time::Duration::from_secs_f64(self.escalation_window_s))
            .unwrap_or(now);
        let mut recent: Vec<&str> = Vec::new();
        for entry in self.call_log.iter().rev() {
            if entry.at < cutoff {
                break;
            }
            recent.push(entry.safety.as_str());
        }
        recent.reverse();

        if safety == "DELETE" {
            let has_read = recent.contains(&"READ");
            let has_write = recent.contains(&"WRITE");
            if has_read && has_write {
                return Some(SecurityAlert {
                    pattern: "escalation".into(),
                    severity: 0.8,
                    action: "warn".into(),
                    tool: tool.to_string(),
                    detail: format!(
                        "Privilege escalation pattern detected: READ→WRITE→DELETE within {}s (current: {tool})",
                        self.escalation_window_s
                    ),
                    timestamp: now_unix_f64(),
                });
            }
        }

        let mutations = recent
            .iter()
            .filter(|s| **s == "WRITE" || **s == "DELETE")
            .count();
        if mutations >= 5 {
            return Some(SecurityAlert {
                pattern: "mutation_burst".into(),
                severity: 0.6,
                action: "throttle".into(),
                tool: tool.to_string(),
                detail: format!(
                    "{mutations} mutation operations in {}s",
                    self.escalation_window_s
                ),
                timestamp: now_unix_f64(),
            });
        }
        None
    }

    /// Recent alerts (oldest → newest, capped at `limit`).
    #[must_use]
    pub fn recent_alerts(&self, limit: usize) -> Vec<Value> {
        let skip = self.alerts.len().saturating_sub(limit);
        self.alerts
            .iter()
            .skip(skip)
            .map(SecurityAlert::to_json)
            .collect()
    }

    /// Monitor status: totals, alert pattern counts, config.
    #[must_use]
    pub fn status(&self) -> Value {
        let mut pattern_counts: HashMap<&str, u64> = HashMap::new();
        for alert in &self.alerts {
            *pattern_counts.entry(alert.pattern.as_str()).or_insert(0) += 1;
        }
        json!({
            "total_calls_monitored": self.total_calls,
            "total_alerts": self.alerts.len(),
            "blocked_count": self.blocked_count,
            "alert_patterns": pattern_counts,
            "recent_alerts": self.recent_alerts(5),
            "config": {
                "rapid_fire_threshold": self.rapid_fire_threshold,
                "rapid_fire_window_s": self.rapid_fire_window_s,
                "lateral_threshold": self.lateral_threshold,
                "lateral_window_s": self.lateral_window_s,
                "escalation_window_s": self.escalation_window_s,
            },
        })
    }

    /// Reset all state (tests / maintenance).
    pub fn reset(&mut self) {
        self.call_log.clear();
        self.per_tool_times.clear();
        self.alerts.clear();
        self.total_calls = 0;
        self.blocked_count = 0;
    }
}

type Monitor = Arc<Mutex<SecurityMonitor>>;

fn lock_monitor(monitor: &Monitor) -> wm_core::Result<MutexGuard<'_, SecurityMonitor>> {
    monitor
        .lock()
        .map_err(|e| CoreError::Internal(format!("security monitor lock poisoned: {e}")))
}

// ── Tools ──────────────────────────────────────────────────────────────

/// `security.breaker.record` — record a tool call and check patterns.
pub struct SecurityBreakerRecordTool {
    monitor: Monitor,
    stats: ToolStats,
    effects: EffectRow,
}

impl SecurityBreakerRecordTool {
    #[must_use]
    pub fn new(monitor: Monitor) -> Self {
        Self {
            monitor,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::DharmaRules],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for SecurityBreakerRecordTool {
    fn name(&self) -> &str {
        "security.breaker.record"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Record a tool call in the security circuit breaker. Args: tool (str), safety (READ|WRITE|DELETE, default READ), agent_id (optional). Returns an alert when a suspicious pattern fires."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let tool = args
            .get("tool")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("tool is required".into()))?;
        let safety = args.get("safety").and_then(Value::as_str).unwrap_or("READ");
        let agent_id = args
            .get("agent_id")
            .and_then(Value::as_str)
            .unwrap_or("default");
        let mut monitor = lock_monitor(&self.monitor)?;
        match monitor.record_call(tool, safety, agent_id) {
            Some(alert) => {
                let mut out = alert.to_json();
                out["alert"] = json!(true);
                Ok(out)
            }
            None => Ok(json!({"alert": false, "tool": tool})),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `security.breaker.status` — monitor totals and config.
pub struct SecurityBreakerStatusTool {
    monitor: Monitor,
    stats: ToolStats,
    effects: EffectRow,
}

impl SecurityBreakerStatusTool {
    #[must_use]
    pub fn new(monitor: Monitor) -> Self {
        Self {
            monitor,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
impl Tool for SecurityBreakerStatusTool {
    fn name(&self) -> &str {
        "security.breaker.status"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Security circuit-breaker status: total calls, alerts, blocked count, pattern counts, config."
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let monitor = lock_monitor(&self.monitor)?;
        Ok(json!({"status": "success", "monitor": monitor.status()}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `security.breaker.alerts` — recent alerts.
pub struct SecurityBreakerAlertsTool {
    monitor: Monitor,
    stats: ToolStats,
    effects: EffectRow,
}

impl SecurityBreakerAlertsTool {
    #[must_use]
    pub fn new(monitor: Monitor) -> Self {
        Self {
            monitor,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
impl Tool for SecurityBreakerAlertsTool {
    fn name(&self) -> &str {
        "security.breaker.alerts"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Recent security circuit-breaker alerts. Args: limit (default 50)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args
            .get("limit")
            .and_then(Value::as_u64)
            .map_or(50, |v| usize::try_from(v).unwrap_or(50));
        let monitor = lock_monitor(&self.monitor)?;
        Ok(json!({"status": "success", "alerts": monitor.recent_alerts(limit)}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `security.breaker.reset` — clear monitor state.
pub struct SecurityBreakerResetTool {
    monitor: Monitor,
    stats: ToolStats,
    effects: EffectRow,
}

impl SecurityBreakerResetTool {
    #[must_use]
    pub fn new(monitor: Monitor) -> Self {
        Self {
            monitor,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::DharmaRules],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for SecurityBreakerResetTool {
    fn name(&self) -> &str {
        "security.breaker.reset"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Reset the security circuit-breaker state (in-memory monitor)."
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut monitor = lock_monitor(&self.monitor)?;
        monitor.reset();
        Ok(json!({"status": "success", "reset": true}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the security circuit-breaker surface (4 tools).
#[must_use]
pub fn register_security_breaker(
    registry: &wm_dispatch::ToolRegistry,
) -> wm_dispatch::ToolRegistry {
    let monitor: Monitor = Arc::new(Mutex::new(SecurityMonitor::new()));
    registry
        .register(Arc::new(SecurityBreakerRecordTool::new(monitor.clone())))
        .register(Arc::new(SecurityBreakerStatusTool::new(monitor.clone())))
        .register(Arc::new(SecurityBreakerAlertsTool::new(monitor.clone())))
        .register(Arc::new(SecurityBreakerResetTool::new(monitor)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn clean_sequence_has_no_alerts() {
        let mut monitor = SecurityMonitor::new();
        assert!(monitor.record_call("memory.search", "READ", "a").is_none());
        assert!(monitor.record_call("memory.read", "READ", "a").is_none());
        assert_eq!(monitor.status()["total_alerts"], 0);
    }

    #[test]
    fn rapid_fire_throttles_then_blocks() {
        let mut monitor = SecurityMonitor::new();
        let mut last = None;
        for _ in 0..10 {
            last = monitor.record_call("shell.exec", "READ", "a");
        }
        let alert = last.expect("rapid_fire alert at threshold");
        assert_eq!(alert.pattern, "rapid_fire");
        assert_eq!(alert.action, "throttle");

        last = None;
        for _ in 0..10 {
            last = monitor.record_call("shell.exec", "READ", "a");
        }
        let blocked = last.expect("block at 2x threshold");
        assert_eq!(blocked.action, "block");
        assert_eq!(monitor.status()["blocked_count"], 1);
    }

    #[test]
    fn escalation_read_write_delete() {
        let mut monitor = SecurityMonitor::new();
        let _ = monitor.record_call("memory.search", "READ", "a");
        let _ = monitor.record_call("memory.update", "WRITE", "a");
        let alert = monitor
            .record_call("memory.delete", "DELETE", "a")
            .expect("escalation alert");
        assert_eq!(alert.pattern, "escalation");
        assert_eq!(alert.action, "warn");
    }

    #[test]
    fn lateral_movement_across_tools() {
        let mut monitor = SecurityMonitor::new();
        let mut last = None;
        for i in 0..15 {
            last = monitor.record_call(&format!("tool.{i}"), "READ", "a");
        }
        let alert = last.expect("lateral movement alert");
        assert_eq!(alert.pattern, "lateral_movement");
        assert_eq!(alert.tool, "*");
    }

    #[test]
    fn mutation_burst_throttles() {
        let mut monitor = SecurityMonitor::new();
        let mut last = None;
        for _ in 0..5 {
            last = monitor.record_call("memory.update", "WRITE", "a");
        }
        let alert = last.expect("mutation burst alert");
        assert_eq!(alert.pattern, "mutation_burst");
        assert_eq!(alert.action, "throttle");
    }

    #[test]
    fn reset_clears_state() {
        let mut monitor = SecurityMonitor::new();
        for _ in 0..10 {
            let _ = monitor.record_call("shell.exec", "READ", "a");
        }
        assert!(monitor.status()["total_alerts"].as_u64().unwrap_or(0) > 0);
        monitor.reset();
        assert_eq!(monitor.status()["total_alerts"], 0);
        assert_eq!(monitor.status()["total_calls_monitored"], 0);
    }
}
