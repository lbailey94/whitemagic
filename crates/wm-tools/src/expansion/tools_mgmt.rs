//! Tools management — effectiveness_report, retire.

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};

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
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
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
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
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
