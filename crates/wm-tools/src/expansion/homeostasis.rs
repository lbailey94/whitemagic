//! Homeostasis tools — check, adjust, history, alerts.
//!
//! Dipper Gana tools for monitoring and adjusting the cognitive system's
//! internal balance based on real hardware metrics from SubstrateMonitor.

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_substrate::anomaly::AnomalyDetector;
use wm_substrate::homeostatic::HomeostaticLoop;
use wm_substrate::{BatteryState, SubstrateMonitor, ThermalState};

/// `homeostasis.check` — check all homeostasis metrics.
///
/// Samples current hardware state and returns a comprehensive report
/// including CPU, memory, swap, thermal, battery, health score, and
/// recommendations based on current load.
pub struct HomeostasisCheckTool {
    monitor: Arc<SubstrateMonitor>,
    homeostatic_loop: Arc<std::sync::Mutex<HomeostaticLoop>>,
    anomaly_detector: Arc<std::sync::Mutex<AnomalyDetector>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl HomeostasisCheckTool {
    pub fn new(
        monitor: Arc<SubstrateMonitor>,
        homeostatic_loop: Arc<std::sync::Mutex<HomeostaticLoop>>,
        anomaly_detector: Arc<std::sync::Mutex<AnomalyDetector>>,
    ) -> Self {
        Self {
            monitor,
            homeostatic_loop,
            anomaly_detector,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

impl Tool for HomeostasisCheckTool {
    fn name(&self) -> &str {
        "homeostasis.check"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Check all homeostasis metrics (CPU, memory, thermal, battery, health score)"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let hv = self.monitor.sample();
        let health = hv.health_score();
        let stressed = hv.is_stressed();

        let mut recommendations: Vec<&str> = Vec::new();
        if hv.cpu_load > 0.7 {
            recommendations.push("Reduce concurrent tool dispatches — CPU load is high");
        }
        if hv.memory_pressure > 0.7 {
            recommendations.push("Consider flushing caches — memory pressure is critical");
        }
        if hv.swap_usage > 0.5 {
            recommendations.push("Swap usage elevated — reduce working set");
        }
        if matches!(hv.thermal_state, ThermalState::Hot | ThermalState::Critical) {
            recommendations.push("Thermal throttling risk — shed non-essential work");
        }
        if matches!(hv.battery_state, BatteryState::Discharging) && hv.battery_percent < 0.2 {
            recommendations.push("Battery low — enter eco mode");
        }

        // Run anomaly detection and homeostatic loop
        let (actions, alerts) = {
            let Ok(mut detector) = self.anomaly_detector.lock() else {
                return Ok(
                    json!({"status": "error", "message": "anomaly_detector mutex poisoned"}),
                );
            };
            let alerts = detector.check(&hv);
            let Ok(mut loop_) = self.homeostatic_loop.lock() else {
                return Ok(
                    json!({"status": "error", "message": "homeostatic_loop mutex poisoned"}),
                );
            };
            let actions = loop_.sample_cycle(&hv, &detector);
            (actions, alerts)
        };

        if !alerts.is_empty() {
            recommendations.push("Anomaly detected — see alerts for details");
        }
        if recommendations.is_empty() {
            recommendations.push("All metrics within normal range");
        }

        let action_list: Vec<Value> = actions
            .iter()
            .map(wm_substrate::homeostatic::HomeostaticAction::to_json)
            .collect();
        let alert_list: Vec<Value> = alerts
            .iter()
            .map(wm_substrate::anomaly::AnomalyAlert::to_json)
            .collect();

        Ok(json!({
            "status": "success",
            "metrics": hv.to_json(),
            "health_score": health,
            "stressed": stressed,
            "guna": hv.guna.as_str(),
            "recommendations": recommendations,
            "homeostatic_actions": action_list,
            "anomaly_alerts": alert_list,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `homeostasis.adjust` — simulate adjusted health score with custom weights.
///
/// Accepts optional weight parameters (cpu_weight, memory_weight, swap_weight,
/// thermal_weight) and returns what the health score would be under those
/// weights. Does not mutate the actual SubstrateMonitor — this is a
/// simulation/planning tool.
pub struct HomeostasisAdjustTool {
    monitor: Arc<SubstrateMonitor>,
    stats: ToolStats,
    effects: EffectRow,
}

impl HomeostasisAdjustTool {
    pub fn new(monitor: Arc<SubstrateMonitor>) -> Self {
        Self {
            monitor,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

impl Tool for HomeostasisAdjustTool {
    fn name(&self) -> &str {
        "homeostasis.adjust"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Simulate adjusted health score with custom metric weights"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let hv = self.monitor.sample();

        let cpu_weight = args
            .get("cpu_weight")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.3) as f32;
        let memory_weight = args
            .get("memory_weight")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.3) as f32;
        let swap_weight = args
            .get("swap_weight")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.2) as f32;
        let thermal_weight = args
            .get("thermal_weight")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.2) as f32;

        let total_weight = cpu_weight + memory_weight + swap_weight + thermal_weight;
        if total_weight <= 0.0 {
            return Err(wm_core::CoreError::InvalidArgs(
                "Weights must sum to > 0".into(),
            ));
        }

        // Normalize weights
        let cw = cpu_weight / total_weight;
        let mw = memory_weight / total_weight;
        let sw = swap_weight / total_weight;
        let tw = thermal_weight / total_weight;

        let cpu_health = 1.0 - hv.cpu_load.min(1.0);
        let mem_health = 1.0 - hv.memory_pressure.min(1.0);
        let swap_health = 1.0 - hv.swap_usage.min(1.0);
        let thermal_health = hv.thermal_state.health_factor();

        let adjusted_score = cpu_health
            .mul_add(
                cw,
                mem_health.mul_add(mw, swap_health.mul_add(sw, thermal_health * tw)),
            )
            .clamp(0.0, 1.0);
        let default_score = hv.health_score();

        Ok(json!({
            "status": "success",
            "current_metrics": {
                "cpu_load": hv.cpu_load,
                "memory_pressure": hv.memory_pressure,
                "swap_usage": hv.swap_usage,
                "thermal_state": hv.thermal_state.as_str(),
            },
            "weights": {
                "cpu": cw,
                "memory": mw,
                "swap": sw,
                "thermal": tw,
            },
            "default_health_score": default_score,
            "adjusted_health_score": adjusted_score,
            "delta": adjusted_score - default_score,
            "stressed_under_new_weights": adjusted_score < 0.3,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `homeostasis.history` — historical homeostasis readings.
pub struct HomeostasisHistoryTool {
    monitor: Arc<SubstrateMonitor>,
    stats: ToolStats,
    effects: EffectRow,
}

impl HomeostasisHistoryTool {
    pub fn new(monitor: Arc<SubstrateMonitor>) -> Self {
        Self {
            monitor,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

impl Tool for HomeostasisHistoryTool {
    fn name(&self) -> &str {
        "homeostasis.history"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Historical homeostasis readings (recent samples)"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(20) as usize;

        let history = self.monitor.history(limit);
        let samples: Vec<Value> = history
            .iter()
            .map(|hv| {
                json!({
                    "timestamp": hv.timestamp.to_rfc3339(),
                    "cpu_load": hv.cpu_load,
                    "memory_pressure": hv.memory_pressure,
                    "swap_usage": hv.swap_usage,
                    "thermal_state": hv.thermal_state.as_str(),
                    "temperature_c": hv.temperature_c,
                    "battery_state": hv.battery_state.as_str(),
                    "battery_percent": hv.battery_percent,
                    "guna": hv.guna.as_str(),
                    "health_score": hv.health_score(),
                    "stressed": hv.is_stressed(),
                })
            })
            .collect();

        let avg_health = if samples.is_empty() {
            0.0
        } else {
            history
                .iter()
                .map(wm_substrate::HarmonyVector::health_score)
                .sum::<f32>()
                / history.len() as f32
        };

        Ok(json!({
            "status": "success",
            "count": samples.len(),
            "avg_health_score": (avg_health * 100.0).round() / 100.0,
            "samples": samples,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `homeostasis.alerts` — current alerts and warnings.
///
/// Checks current hardware state against standard thresholds and returns
/// any active alerts. Severity levels: info, warning, critical.
pub struct HomeostasisAlertsTool {
    monitor: Arc<SubstrateMonitor>,
    anomaly_detector: Arc<std::sync::Mutex<AnomalyDetector>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl HomeostasisAlertsTool {
    pub fn new(
        monitor: Arc<SubstrateMonitor>,
        anomaly_detector: Arc<std::sync::Mutex<AnomalyDetector>>,
    ) -> Self {
        Self {
            monitor,
            anomaly_detector,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

impl Tool for HomeostasisAlertsTool {
    fn name(&self) -> &str {
        "homeostasis.alerts"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Current alerts and warnings based on homeostasis thresholds"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let hv = self.monitor.sample();
        let mut alerts: Vec<Value> = Vec::new();

        // CPU alerts
        if hv.cpu_load > 0.9 {
            alerts.push(json!({
                "metric": "cpu_load",
                "severity": "critical",
                "value": hv.cpu_load,
                "threshold": 0.9,
                "message": "CPU saturated — dispatch may be blocked",
            }));
        } else if hv.cpu_load > 0.7 {
            alerts.push(json!({
                "metric": "cpu_load",
                "severity": "warning",
                "value": hv.cpu_load,
                "threshold": 0.7,
                "message": "CPU load high — consider reducing concurrency",
            }));
        }

        // Memory alerts
        if hv.memory_pressure > 0.9 {
            alerts.push(json!({
                "metric": "memory_pressure",
                "severity": "critical",
                "value": hv.memory_pressure,
                "threshold": 0.9,
                "message": "Memory exhausted — flush caches immediately",
            }));
        } else if hv.memory_pressure > 0.7 {
            alerts.push(json!({
                "metric": "memory_pressure",
                "severity": "warning",
                "value": hv.memory_pressure,
                "threshold": 0.7,
                "message": "Memory pressure high — reduce working set",
            }));
        }

        // Swap alerts
        if hv.swap_usage > 0.8 {
            alerts.push(json!({
                "metric": "swap_usage",
                "severity": "critical",
                "value": hv.swap_usage,
                "threshold": 0.8,
                "message": "Swap nearly full — system may thrash",
            }));
        } else if hv.swap_usage > 0.5 {
            alerts.push(json!({
                "metric": "swap_usage",
                "severity": "warning",
                "value": hv.swap_usage,
                "threshold": 0.5,
                "message": "Swap usage elevated — performance degraded",
            }));
        }

        // Thermal alerts
        match hv.thermal_state {
            ThermalState::Critical => {
                alerts.push(json!({
                    "metric": "thermal",
                    "severity": "critical",
                    "value": hv.temperature_c,
                    "threshold": 90,
                    "message": "Critical temperature — shed all non-essential work",
                }));
            }
            ThermalState::Hot => {
                alerts.push(json!({
                    "metric": "thermal",
                    "severity": "warning",
                    "value": hv.temperature_c,
                    "threshold": 75,
                    "message": "Temperature hot — reduce load",
                }));
            }
            _ => {}
        }

        // Battery alerts
        if matches!(hv.battery_state, BatteryState::Discharging) {
            if hv.battery_percent < 0.1 {
                alerts.push(json!({
                    "metric": "battery",
                    "severity": "critical",
                    "value": hv.battery_percent,
                    "threshold": 0.1,
                    "message": "Battery critically low — enter eco mode immediately",
                }));
            } else if hv.battery_percent < 0.2 {
                alerts.push(json!({
                    "metric": "battery",
                    "severity": "warning",
                    "value": hv.battery_percent,
                    "threshold": 0.2,
                    "message": "Battery low — prepare for eco mode",
                }));
            }
        }

        // Overall health alert
        if hv.is_stressed() {
            alerts.push(json!({
                "metric": "health_score",
                "severity": "critical",
                "value": hv.health_score(),
                "threshold": 0.3,
                "message": "System under stress — governance may block writes",
            }));
        }

        // Anomaly detector alerts (z-score based)
        let anomaly_alerts: Vec<Value> = {
            let Ok(mut detector) = self.anomaly_detector.lock() else {
                return Ok(
                    json!({"status": "error", "message": "anomaly_detector mutex poisoned"}),
                );
            };
            detector
                .check(&hv)
                .iter()
                .map(wm_substrate::anomaly::AnomalyAlert::to_json)
                .collect()
        };
        for alert in &anomaly_alerts {
            alerts.push(json!({
                "metric": alert["dimension"],
                "severity": alert["severity"],
                "value": alert["current_value"],
                "z_score": alert["z_score"],
                "message": format!("Anomaly: {} deviation (z={:.2})", alert["direction"], alert["z_score"].as_f64().unwrap_or(0.0)),
            }));
        }

        let critical_count = alerts
            .iter()
            .filter(|a| a["severity"] == "critical")
            .count();
        let warning_count = alerts.iter().filter(|a| a["severity"] == "warning").count();

        Ok(json!({
            "status": "success",
            "total_alerts": alerts.len(),
            "critical": critical_count,
            "warnings": warning_count,
            "healthy": alerts.is_empty(),
            "alerts": alerts,
            "anomaly_alerts": anomaly_alerts,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_monitor() -> Arc<SubstrateMonitor> {
        Arc::new(SubstrateMonitor::new(50))
    }

    fn test_loop() -> Arc<std::sync::Mutex<HomeostaticLoop>> {
        Arc::new(std::sync::Mutex::new(HomeostaticLoop::default()))
    }

    fn test_detector() -> Arc<std::sync::Mutex<AnomalyDetector>> {
        Arc::new(std::sync::Mutex::new(AnomalyDetector::default()))
    }

    #[test]
    fn homeostasis_check_returns_metrics() {
        let monitor = test_monitor();
        let tool = HomeostasisCheckTool::new(monitor, test_loop(), test_detector());
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({}));
        assert!(result.is_ok());
        let v = result.unwrap();
        assert_eq!(v["status"], "success");
        assert!(v["metrics"]["cpu_load"].is_number());
        assert!(v["health_score"].is_number());
        assert!(v["recommendations"].is_array());
        assert!(v["homeostatic_actions"].is_array());
        assert!(v["anomaly_alerts"].is_array());
    }

    #[test]
    fn homeostasis_check_has_recommendations() {
        let monitor = test_monitor();
        let tool = HomeostasisCheckTool::new(monitor, test_loop(), test_detector());
        let mut ctx = Context::default();
        let v = tool.call(&mut ctx, json!({})).unwrap();
        let recs = v["recommendations"].as_array().unwrap();
        assert!(!recs.is_empty());
    }

    #[test]
    fn homeostasis_adjust_with_default_weights() {
        let monitor = test_monitor();
        let tool = HomeostasisAdjustTool::new(monitor);
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({}));
        assert!(result.is_ok());
        let v = result.unwrap();
        assert_eq!(v["status"], "success");
        assert!(v["adjusted_health_score"].is_number());
        assert!(v["default_health_score"].is_number());
    }

    #[test]
    fn homeostasis_adjust_with_custom_weights() {
        let monitor = test_monitor();
        let tool = HomeostasisAdjustTool::new(monitor);
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"cpu_weight": 0.5, "memory_weight": 0.3, "swap_weight": 0.1, "thermal_weight": 0.1}),
            )
            .unwrap();
        let weights = &v["weights"];
        assert!((weights["cpu"].as_f64().unwrap() - 0.5).abs() < 0.01);
        assert!((weights["memory"].as_f64().unwrap() - 0.3).abs() < 0.01);
    }

    #[test]
    fn homeostasis_adjust_zero_weights_errors() {
        let monitor = test_monitor();
        let tool = HomeostasisAdjustTool::new(monitor);
        let mut ctx = Context::default();
        let result = tool.call(
            &mut ctx,
            json!({"cpu_weight": 0.0, "memory_weight": 0.0, "swap_weight": 0.0, "thermal_weight": 0.0}),
        );
        assert!(result.is_err());
    }

    #[test]
    fn homeostasis_history_returns_samples() {
        let monitor = test_monitor();
        // Take a few samples
        let _ = monitor.sample();
        let _ = monitor.sample();
        let _ = monitor.sample();

        let tool = HomeostasisHistoryTool::new(monitor);
        let mut ctx = Context::default();
        let v = tool.call(&mut ctx, json!({"limit": 5})).unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["count"], 3);
        assert!(v["samples"].is_array());
        assert!(v["avg_health_score"].is_number());
    }

    #[test]
    fn homeostasis_history_empty_when_no_samples() {
        let monitor = test_monitor();
        let tool = HomeostasisHistoryTool::new(monitor);
        let mut ctx = Context::default();
        let v = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(v["count"], 0);
    }

    #[test]
    fn homeostasis_alerts_returns_array() {
        let monitor = test_monitor();
        let _ = monitor.sample();
        let tool = HomeostasisAlertsTool::new(monitor, test_detector());
        let mut ctx = Context::default();
        let v = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(v["status"], "success");
        assert!(v["alerts"].is_array());
        assert!(v["healthy"].is_boolean());
        assert!(v["total_alerts"].is_number());
        assert!(v["anomaly_alerts"].is_array());
    }

    #[test]
    fn homeostasis_alerts_has_severity_counts() {
        let monitor = test_monitor();
        let _ = monitor.sample();
        let tool = HomeostasisAlertsTool::new(monitor, test_detector());
        let mut ctx = Context::default();
        let v = tool.call(&mut ctx, json!({})).unwrap();
        assert!(v["critical"].is_number());
        assert!(v["warnings"].is_number());
    }

    #[test]
    fn homeostasis_tools_are_dipper_gana() {
        let monitor = test_monitor();
        assert_eq!(
            HomeostasisCheckTool::new(monitor.clone(), test_loop(), test_detector()).gana(),
            Gana::Dipper
        );
        assert_eq!(
            HomeostasisAdjustTool::new(monitor.clone()).gana(),
            Gana::Dipper
        );
        assert_eq!(
            HomeostasisHistoryTool::new(monitor.clone()).gana(),
            Gana::Dipper
        );
        assert_eq!(
            HomeostasisAlertsTool::new(monitor, test_detector()).gana(),
            Gana::Dipper
        );
    }
}
