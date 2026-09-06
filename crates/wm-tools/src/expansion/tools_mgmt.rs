//! Tools management — usage_report, effectiveness_report, retire.

#![forbid(unsafe_code)]

use std::sync::Arc;

use async_trait::async_trait;

use serde_json::{Value, json};
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};
use wm_dispatch::ToolRegistry;

/// `tools.usage_report` — registry-wide usage ranking from live dispatch stats.
///
/// Unlike `tools.effectiveness_report` (which only sees its own counters),
/// this tool holds a snapshot of the tool registry. Tool `Arc`s are shared
/// across registries, so the per-tool `ToolStats` atomics it reads are the
/// same ones the dispatch pipeline updates — the report is always live.
pub struct ToolsUsageReportTool {
    registry: Arc<ToolRegistry>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ToolsUsageReportTool {
    #[must_use]
    pub fn new(registry: Arc<ToolRegistry>) -> Self {
        Self {
            registry,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
impl Tool for ToolsUsageReportTool {
    fn name(&self) -> &str {
        "tools.usage_report"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Rank all registered tools by usage from live dispatch stats: calls, success rate, latency, and retirement candidates"
    }
    fn input_schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "sort": {
                    "type": "string",
                    "enum": ["calls", "effectiveness", "latency"],
                    "description": "Sort key (default: calls, descending; effectiveness ascending — worst first; latency descending — slowest first)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of tools to return (default: 25, 0 = all)"
                },
                "min_calls": {
                    "type": "integer",
                    "description": "Only include tools with at least this many calls (default: 0)"
                },
                "retire_candidates_only": {
                    "type": "boolean",
                    "description": "Only include tools flagged for retirement (>= 10 calls, effectiveness < 0.2)"
                }
            }
        })
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let sort = args.get("sort").and_then(Value::as_str).unwrap_or("calls");
        let limit = args
            .get("limit")
            .and_then(Value::as_u64)
            .map_or(25, |l| l as usize);
        let min_calls = args.get("min_calls").and_then(Value::as_u64).unwrap_or(0);
        let retire_only = args
            .get("retire_candidates_only")
            .and_then(Value::as_bool)
            .unwrap_or(false);

        let tools = self.registry.all_ref();
        let total_registered = tools.len();

        let mut entries: Vec<(u64, f32, u64, Value)> = tools
            .iter()
            .filter_map(|t| {
                let snap = t.stats().snapshot();
                if snap.call_count < min_calls {
                    return None;
                }
                let should_retire = t.stats().should_retire(10, 0.2);
                if retire_only && !should_retire {
                    return None;
                }
                let entry = json!({
                    "name": t.name(),
                    "gana": format!("{:?}", t.gana()),
                    "call_count": snap.call_count,
                    "success_count": snap.success_count,
                    "effectiveness": (f64::from(snap.effectiveness) * 100.0).round() / 100.0,
                    "p50_latency_ms": (snap.p50_latency_ns as f64 / 1_000_000.0 * 100.0).round() / 100.0,
                    "peak_latency_ms": (snap.peak_latency_ns as f64 / 1_000_000.0 * 100.0).round() / 100.0,
                    "last_used_unix": snap.last_used_unix,
                    "should_retire": should_retire,
                });
                Some((snap.call_count, snap.effectiveness, snap.p50_latency_ns, entry))
            })
            .collect();

        match sort {
            // Worst effectiveness first — retirement review order.
            "effectiveness" => entries.sort_by(|a, b| {
                a.1.partial_cmp(&b.1)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then(b.0.cmp(&a.0))
            }),
            // Slowest first — latency hot-spot order.
            "latency" => entries.sort_by_key(|x| std::cmp::Reverse(x.2)),
            // Default: most-called first — usage-distribution order.
            _ => entries.sort_by_key(|x| std::cmp::Reverse(x.0)),
        }

        let matched = entries.len();
        let used_count = tools
            .iter()
            .filter(|t| {
                t.stats()
                    .call_count
                    .load(std::sync::atomic::Ordering::Relaxed)
                    > 0
            })
            .count();
        let report: Vec<Value> = entries
            .into_iter()
            .map(|(_, _, _, e)| e)
            .take(if limit == 0 { usize::MAX } else { limit })
            .collect();

        Ok(json!({
            "status": "success",
            "sort": sort,
            "total_registered": total_registered,
            "total_used": used_count,
            "matched": matched,
            "tools": report,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

pub struct ToolsEffectivenessReportTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl ToolsEffectivenessReportTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for ToolsEffectivenessReportTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for ToolsEffectivenessReportTool {
    fn name(&self) -> &str {
        "tools.effectiveness_report"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Report on tool effectiveness from dispatch stats"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let total = self
            .stats
            .call_count
            .load(std::sync::atomic::Ordering::Relaxed);
        let successes = self
            .stats
            .success_count
            .load(std::sync::atomic::Ordering::Relaxed);
        let failures = total.saturating_sub(successes);
        let effectiveness = if total > 0 {
            successes as f32 / total as f32
        } else {
            1.0
        };
        Ok(json!({
            "status": "success",
            "total_calls": total,
            "successes": successes,
            "failures": failures,
            "effectiveness": (effectiveness * 100.0).round() / 100.0,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `tools.retire` — check if a tool should be retired based on effectiveness.
pub struct ToolsRetireTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl ToolsRetireTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for ToolsRetireTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for ToolsRetireTool {
    fn name(&self) -> &str {
        "tools.retire"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Check if a tool should be retired based on effectiveness threshold"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let tool_name = args
            .get("tool")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");
        let threshold = args
            .get("threshold")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.10) as f32;
        let effectiveness = args
            .get("effectiveness")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(1.0) as f32;
        let should_retire = effectiveness < threshold;
        Ok(json!({
            "status": "success",
            "tool": tool_name,
            "effectiveness": effectiveness,
            "threshold": threshold,
            "should_retire": should_retire,
            "recommendation": if should_retire { "retire" } else { "keep" },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;
    use wm_dispatch::ToolRegistryBuilder;

    struct StubTool {
        name: &'static str,
        stats: ToolStats,
        effects: EffectRow,
    }

    impl StubTool {
        fn new(name: &'static str) -> Self {
            Self {
                name,
                stats: ToolStats::default(),
                effects: EffectRow::pure(),
            }
        }
    }

    #[async_trait]
    impl Tool for StubTool {
        fn name(&self) -> &str {
            self.name
        }
        fn gana(&self) -> Gana {
            Gana::Ghost
        }
        fn effects(&self) -> &EffectRow {
            &self.effects
        }
        async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
            Ok(json!({"status": "success"}))
        }
        fn stats(&self) -> &ToolStats {
            &self.stats
        }
    }

    fn registry_with_usage() -> Arc<ToolRegistry> {
        let hot = Arc::new(StubTool::new("stub.hot"));
        for _ in 0..20 {
            hot.stats
                .record_success(Duration::from_millis(1), Duration::from_millis(1));
        }
        let failing = Arc::new(StubTool::new("stub.failing"));
        for _ in 0..2 {
            failing
                .stats
                .record_success(Duration::from_millis(1), Duration::from_millis(1));
        }
        for _ in 0..13 {
            failing.stats.record_failure(Duration::from_millis(1));
        }
        let unused = Arc::new(StubTool::new("stub.unused"));

        let mut builder = ToolRegistryBuilder::new();
        builder.register(hot);
        builder.register(failing);
        builder.register(unused);
        Arc::new(builder.build())
    }

    #[tokio::test]
    async fn usage_report_ranks_by_calls() {
        let tool = ToolsUsageReportTool::new(registry_with_usage());
        let mut ctx = Context::default();
        let out = tool.call(&mut ctx, json!({})).await.unwrap();

        assert_eq!(out["status"], "success");
        assert_eq!(out["total_registered"], 3);
        assert_eq!(out["total_used"], 2);
        let tools = out["tools"].as_array().unwrap();
        assert_eq!(tools.len(), 3);
        assert_eq!(tools[0]["name"], "stub.hot");
        assert_eq!(tools[0]["call_count"], 20);
        assert_eq!(tools[1]["name"], "stub.failing");
    }

    #[tokio::test]
    async fn usage_report_flags_retirement_candidates() {
        let tool = ToolsUsageReportTool::new(registry_with_usage());
        let mut ctx = Context::default();
        let out = tool
            .call(&mut ctx, json!({"retire_candidates_only": true}))
            .await
            .unwrap();

        let tools = out["tools"].as_array().unwrap();
        assert_eq!(tools.len(), 1);
        assert_eq!(tools[0]["name"], "stub.failing");
        assert_eq!(tools[0]["should_retire"], true);
    }

    #[tokio::test]
    async fn usage_report_min_calls_and_effectiveness_sort() {
        let tool = ToolsUsageReportTool::new(registry_with_usage());
        let mut ctx = Context::default();
        let out = tool
            .call(&mut ctx, json!({"min_calls": 1, "sort": "effectiveness"}))
            .await
            .unwrap();

        let tools = out["tools"].as_array().unwrap();
        assert_eq!(tools.len(), 2, "unused tool filtered by min_calls");
        assert_eq!(
            tools[0]["name"], "stub.failing",
            "worst effectiveness first"
        );
    }
}
