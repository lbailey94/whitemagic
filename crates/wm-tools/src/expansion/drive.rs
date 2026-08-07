//! Drive & emotion tools — `drive.snapshot` and `drive.event`.
//!
//! Gana::Ghost — "Intrinsic motivation, emotion, drive state"
//!
//! Tools:
//! - `drive.snapshot` — Show current drive state and bias
//! - `drive.event` — Inject a drive event to update drive state

#![forbid(unsafe_code)]
#![allow(clippy::significant_drop_tightening)]

use serde_json::{Value, json};
use std::sync::{Arc, Mutex};
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};
use wm_drive::{DriveCore, DriveEvent, DriveEventKind};

// ── drive.snapshot ────────────────────────────────────────────────────

/// Show current drive state, bias, and event count.
pub struct DriveSnapshotTool {
    core: Arc<Mutex<DriveCore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DriveSnapshotTool {
    /// Create a new drive snapshot tool.
    pub fn new(core: Arc<Mutex<DriveCore>>) -> Self {
        Self {
            core,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for DriveSnapshotTool {
    fn name(&self) -> &str {
        "drive.snapshot"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Show current drive state (curiosity, satisfaction, caution, energy, social) and tool selection bias"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let (snapshot, bias) = {
            let core = self
                .core
                .lock()
                .map_err(|e| wm_core::CoreError::Tool(format!("drive core lock error: {e}")))?;
            (core.snapshot(), core.bias())
        };

        Ok(json!({
            "status": "success",
            "drives": snapshot["drives"],
            "event_count": snapshot["event_count"],
            "bias": {
                "exploration_weight": bias.exploration_weight,
                "conservative_weight": bias.conservative_weight,
                "lightweight_weight": bias.lightweight_weight,
                "social_weight": bias.social_weight,
                "confidence": bias.confidence,
            },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── drive.event ───────────────────────────────────────────────────────

/// Inject a drive event to update the drive state.
pub struct DriveEventTool {
    core: Arc<Mutex<DriveCore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DriveEventTool {
    /// Create a new drive event tool.
    pub fn new(core: Arc<Mutex<DriveCore>>) -> Self {
        Self {
            core,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for DriveEventTool {
    fn name(&self) -> &str {
        "drive.event"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Inject a drive event (tool_success, tool_error, novel_input, etc.) to update drive state"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let kind_str = args
            .get("kind")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("kind (string) required".into()))?;

        let kind = match kind_str {
            "tool_success" => DriveEventKind::ToolSuccess,
            "tool_error" => DriveEventKind::ToolError,
            "novel_input" => DriveEventKind::NovelInput,
            "low_confidence" => DriveEventKind::LowConfidence,
            "high_confidence" => DriveEventKind::HighConfidence,
            "resource_pressure" => DriveEventKind::ResourcePressure,
            "resource_relief" => DriveEventKind::ResourceRelief,
            "social_interaction" => DriveEventKind::SocialInteraction,
            "decay" => DriveEventKind::Decay,
            other => {
                return Err(wm_core::CoreError::InvalidArgs(format!(
                    "unknown drive event kind: '{other}'. Valid: tool_success, tool_error, novel_input, low_confidence, high_confidence, resource_pressure, resource_relief, social_interaction, decay"
                )));
            }
        };

        let detail = args.get("detail").and_then(Value::as_str);

        let mut event = DriveEvent::new(kind);
        if let Some(d) = detail {
            event = event.with_detail(d);
        }

        let (event_count, snapshot) = {
            let mut core = self
                .core
                .lock()
                .map_err(|e| wm_core::CoreError::Tool(format!("drive core lock error: {e}")))?;
            core.process_event(&event);
            (core.event_count(), core.snapshot())
        };

        Ok(json!({
            "status": "success",
            "event_kind": kind_str,
            "event_count": event_count,
            "drives": snapshot["drives"],
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register drive tools into a registry.
pub fn register_drive(
    registry: &wm_dispatch::ToolRegistry,
    core: Arc<Mutex<DriveCore>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(DriveSnapshotTool::new(core.clone())))
        .register(Arc::new(DriveEventTool::new(core)))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_core() -> Arc<Mutex<DriveCore>> {
        Arc::new(Mutex::new(DriveCore::new()))
    }

    #[test]
    fn drive_snapshot_returns_state() {
        let core = make_core();
        let tool = DriveSnapshotTool::new(core);
        let result = tool.call(&mut Context::default(), json!({})).unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["drives"]["curiosity"].as_f64().is_some());
        assert!(obj["bias"]["exploration_weight"].as_f64().is_some());
    }

    #[test]
    fn drive_event_tool_success() {
        let core = make_core();
        let tool = DriveEventTool::new(core);
        let result = tool
            .call(&mut Context::default(), json!({"kind": "tool_success"}))
            .unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["event_kind"], "tool_success");
        assert_eq!(result["event_count"], 1);
    }

    #[test]
    fn drive_event_tool_error() {
        let core = make_core();
        let tool = DriveEventTool::new(core.clone());
        tool.call(&mut Context::default(), json!({"kind": "tool_error"}))
            .unwrap();
        // Check caution increased
        let snap_tool = DriveSnapshotTool::new(core);
        let snap = snap_tool.call(&mut Context::default(), json!({})).unwrap();
        let caution = snap["drives"]["caution"].as_f64().unwrap();
        assert!(
            caution > 0.3,
            "caution should be above baseline after error"
        );
    }

    #[test]
    fn drive_event_novel_input() {
        let core = make_core();
        let tool = DriveEventTool::new(core);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"kind": "novel_input", "detail": "new user query"}),
            )
            .unwrap();
        assert_eq!(result["event_kind"], "novel_input");
    }

    #[test]
    fn drive_event_missing_kind() {
        let core = make_core();
        let tool = DriveEventTool::new(core);
        let result = tool.call(&mut Context::default(), json!({}));
        assert!(result.is_err());
    }

    #[test]
    fn drive_event_unknown_kind() {
        let core = make_core();
        let tool = DriveEventTool::new(core);
        let result = tool.call(&mut Context::default(), json!({"kind": "unknown_kind"}));
        assert!(result.is_err());
    }

    #[test]
    fn drive_event_decay() {
        let core = make_core();
        let tool = DriveEventTool::new(core.clone());
        // Boost curiosity first
        tool.call(&mut Context::default(), json!({"kind": "novel_input"}))
            .unwrap();
        // Then decay
        tool.call(&mut Context::default(), json!({"kind": "decay"}))
            .unwrap();
        assert_eq!(core.lock().unwrap().event_count(), 2);
    }
}
