//! v4 integration tools — reflex, workspace, and timescale MCP tools.
//!
//! Tools:
//! - `reflex.dispatch` — dispatch a reflex by ID through the reflex table
//! - `reflex.status` — show reflex dispatch table status
//! - `workspace.spotlight` — query current spotlight state
//! - `workspace.events` — query recent events from the backlog
//! - `workspace.publish` — publish an event to the global workspace
//! - `workspace.stats` — workspace statistics
//! - `timescale.status` — show timescale bus status
//! - `timescale.hooks` — list hooks per tier with stats

#![forbid(unsafe_code)]

use std::sync::{Arc, Mutex};

use serde_json::{Value, json};
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};
use wm_reflex::{ReflexArgs, ReflexDispatchTable, ReflexId};
use wm_timescale::{Tier, TimescaleBus};
use wm_workspace::{CoreId, EventType, GlobalWorkspace, Salience};

// ── Helper: parse CoreId from string ─────────────────────────────────

fn parse_core_id(s: &str) -> Result<CoreId, wm_core::CoreError> {
    match s.to_lowercase().as_str() {
        "citta" => Ok(CoreId::Citta),
        "dream" => Ok(CoreId::Dream),
        "brain_wave" | "brainwave" => Ok(CoreId::BrainWave),
        "autonomous" => Ok(CoreId::Autonomous),
        "dispatch" => Ok(CoreId::Dispatch),
        "reflex" => Ok(CoreId::Reflex),
        "self_model" | "selfmodel" => Ok(CoreId::SelfModel),
        "drive" => Ok(CoreId::Drive),
        "homeostasis" => Ok(CoreId::Homeostasis),
        "sensor" => Ok(CoreId::Sensor),
        _ => {
            if let Some(rest) = s.strip_prefix("custom_") {
                rest.parse::<u16>().map(CoreId::Custom).map_err(|_| {
                    wm_core::CoreError::InvalidArgs(format!("invalid custom core ID: {s}"))
                })
            } else {
                Err(wm_core::CoreError::InvalidArgs(format!(
                    "unknown core ID: {s}"
                )))
            }
        }
    }
}

fn parse_event_type(s: &str) -> Result<EventType, wm_core::CoreError> {
    match s.to_lowercase().as_str() {
        "error" => Ok(EventType::Error),
        "reward" => Ok(EventType::Reward),
        "attention_request" | "attention" => Ok(EventType::AttentionRequest),
        "novel_detection" | "novel" => Ok(EventType::NovelDetection),
        "threshold_crossing" | "threshold" => Ok(EventType::ThresholdCrossing),
        "drive_update" | "drive" => Ok(EventType::DriveUpdate),
        "safety_alert" | "safety" => Ok(EventType::SafetyAlert),
        _ => Err(wm_core::CoreError::InvalidArgs(format!(
            "unknown event type: {s}"
        ))),
    }
}

fn parse_tier(s: &str) -> Result<Tier, wm_core::CoreError> {
    match s.to_lowercase().as_str() {
        "reflex" | "0" => Ok(Tier::Reflex),
        "reactive" | "1" => Ok(Tier::Reactive),
        "planning" | "2" => Ok(Tier::Planning),
        "consolidation" | "3" => Ok(Tier::Consolidation),
        "evolutionary" | "4" => Ok(Tier::Evolutionary),
        _ => Err(wm_core::CoreError::InvalidArgs(format!(
            "unknown tier: {s}"
        ))),
    }
}

const fn command_name(cmd: wm_reflex::ReflexCommand) -> &'static str {
    match cmd {
        wm_reflex::ReflexCommand::EmergencyStop => "emergency_stop",
        wm_reflex::ReflexCommand::ReducePower => "reduce_power",
        wm_reflex::ReflexCommand::ApplyCorrection => "apply_correction",
        wm_reflex::ReflexCommand::IssueAlert => "issue_alert",
        wm_reflex::ReflexCommand::Drop => "drop",
        wm_reflex::ReflexCommand::NoOp => "noop",
        wm_reflex::ReflexCommand::Custom => "custom",
    }
}

// ── Tool: reflex.dispatch ─────────────────────────────────────────────

pub struct ReflexDispatchTool {
    table: Arc<Mutex<ReflexDispatchTable>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReflexDispatchTool {
    pub fn new(table: Arc<Mutex<ReflexDispatchTable>>) -> Self {
        Self {
            table,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for ReflexDispatchTool {
    fn name(&self) -> &str {
        "reflex.dispatch"
    }
    fn gana(&self) -> Gana {
        Gana::Heart
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let reflex_id: ReflexId = args
            .get("reflex_id")
            .and_then(serde_json::Value::as_u64)
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("reflex_id (number 0-255) required".into())
            })? as ReflexId;

        let sensor_id = args
            .get("sensor_id")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(0) as u16;

        let timestamp_ns = args
            .get("timestamp_ns")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(0);

        let payload_hex = args
            .get("payload")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("");

        let mut reflex_args = ReflexArgs::new(sensor_id, timestamp_ns);
        if !payload_hex.is_empty() {
            let payload = hex_decode(payload_hex)?;
            reflex_args.set_payload(&payload).map_err(|e| {
                wm_core::CoreError::InvalidArgs(format!("reflex payload error: {e}"))
            })?;
        }

        let mut table = self
            .table
            .lock()
            .map_err(|e| wm_core::CoreError::Governance(format!("reflex table lock error: {e}")))?;
        let result = table
            .dispatch(reflex_id, &reflex_args)
            .map_err(|e| wm_core::CoreError::Tool(format!("reflex dispatch error: {e}")))?;

        Ok(json!({
            "reflex_id": reflex_id,
            "actuator_id": result.actuator_id,
            "command": command_name(result.command),
            "priority": result.priority,
            "payload": hex_encode(result.payload()),
            "dispatch_count": table.dispatch_count(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: reflex.status ───────────────────────────────────────────────

pub struct ReflexStatusTool {
    table: Arc<Mutex<ReflexDispatchTable>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReflexStatusTool {
    pub fn new(table: Arc<Mutex<ReflexDispatchTable>>) -> Self {
        Self {
            table,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for ReflexStatusTool {
    fn name(&self) -> &str {
        "reflex.status"
    }
    fn gana(&self) -> Gana {
        Gana::Heart
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let table = self
            .table
            .lock()
            .map_err(|e| wm_core::CoreError::Governance(format!("reflex table lock error: {e}")))?;
        let registered_handlers = table.registered_count();
        let safety_mask = format!("{:#010x}", table.safety_mask());
        let dispatch_count = table.dispatch_count();
        let builtins: Vec<Value> = wm_reflex::builtins::BUILTINS
            .iter()
            .map(|b| {
                json!({
                    "id": b.id,
                    "name": b.name,
                    "registered": table.is_registered(b.id),
                })
            })
            .collect();
        drop(table);
        Ok(json!({
            "registered_handlers": registered_handlers,
            "safety_mask": safety_mask,
            "dispatch_count": dispatch_count,
            "builtins": builtins,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: workspace.spotlight ─────────────────────────────────────────

pub struct WorkspaceSpotlightTool {
    workspace: Arc<Mutex<GlobalWorkspace>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl WorkspaceSpotlightTool {
    pub fn new(workspace: Arc<Mutex<GlobalWorkspace>>) -> Self {
        Self {
            workspace,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for WorkspaceSpotlightTool {
    fn name(&self) -> &str {
        "workspace.spotlight"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let ws = self
            .workspace
            .lock()
            .map_err(|e| wm_core::CoreError::Governance(format!("workspace lock error: {e}")))?;
        match ws.spotlight() {
            Some(entry) => Ok(json!({
                "core": entry.core.to_string(),
                "event_type": entry.winning_event_type.to_string(),
                "salience": {
                    "urgency": entry.salience.urgency,
                    "novelty": entry.salience.novelty,
                    "confidence": entry.salience.confidence,
                    "composite": entry.salience.composite(),
                },
                "strength": ws.spotlight_strength(),
                "age_ms": entry.age().as_millis(),
                "candidates": entry.candidates,
                "transfers": ws.spotlight_transfers(),
                "arbitration_cycles": ws.arbitration_cycles(),
            })),
            None => Ok(json!({
                "spotlight": null,
                "transfers": ws.spotlight_transfers(),
                "arbitration_cycles": ws.arbitration_cycles(),
            })),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: workspace.events ────────────────────────────────────────────

pub struct WorkspaceEventsTool {
    workspace: Arc<Mutex<GlobalWorkspace>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl WorkspaceEventsTool {
    pub fn new(workspace: Arc<Mutex<GlobalWorkspace>>) -> Self {
        Self {
            workspace,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for WorkspaceEventsTool {
    fn name(&self) -> &str {
        "workspace.events"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let count = args
            .get("count")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;
        let count = count.min(256);

        let ws = self
            .workspace
            .lock()
            .map_err(|e| wm_core::CoreError::Governance(format!("workspace lock error: {e}")))?;
        let events: Vec<Value> = ws
            .recent_events(count)
            .iter()
            .map(|e| {
                json!({
                    "core": e.core.to_string(),
                    "event_type": e.event_type.to_string(),
                    "salience": {
                        "urgency": e.salience.urgency,
                        "novelty": e.salience.novelty,
                        "confidence": e.salience.confidence,
                        "composite": e.composite_salience(),
                    },
                    "payload": e.payload,
                    "age_ms": e.age().as_millis(),
                })
            })
            .collect();

        Ok(json!({
            "events": events,
            "total_published": ws.events_published(),
            "backlog_len": ws.backlog().len(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: workspace.publish ───────────────────────────────────────────

pub struct WorkspacePublishTool {
    workspace: Arc<Mutex<GlobalWorkspace>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl WorkspacePublishTool {
    pub fn new(workspace: Arc<Mutex<GlobalWorkspace>>) -> Self {
        Self {
            workspace,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for WorkspacePublishTool {
    fn name(&self) -> &str {
        "workspace.publish"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let core_str = args
            .get("core")
            .and_then(serde_json::Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("core (string) required".into()))?;
        let core = parse_core_id(core_str)?;

        let event_type_str = args
            .get("event_type")
            .and_then(serde_json::Value::as_str)
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("event_type (string) required".into())
            })?;
        let event_type = parse_event_type(event_type_str)?;

        let urgency = args
            .get("urgency")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.5) as f32;
        let novelty = args
            .get("novelty")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.5) as f32;
        let confidence = args
            .get("confidence")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.5) as f32;
        let payload = args.get("payload").cloned().unwrap_or_else(|| json!({}));

        let event = wm_workspace::WorkspaceEvent::new(
            core,
            event_type,
            Salience::new(urgency, novelty, confidence),
            payload,
        );

        let mut ws = self
            .workspace
            .lock()
            .map_err(|e| wm_core::CoreError::Governance(format!("workspace lock error: {e}")))?;
        let won = ws.publish(&event);

        Ok(json!({
            "won_spotlight": won,
            "spotlight_core": ws.spotlight_core().map(|c| c.to_string()),
            "spotlight_strength": ws.spotlight_strength(),
            "events_published": ws.events_published(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: workspace.stats ─────────────────────────────────────────────

pub struct WorkspaceStatsTool {
    workspace: Arc<Mutex<GlobalWorkspace>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl WorkspaceStatsTool {
    pub fn new(workspace: Arc<Mutex<GlobalWorkspace>>) -> Self {
        Self {
            workspace,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for WorkspaceStatsTool {
    fn name(&self) -> &str {
        "workspace.stats"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let ws = self
            .workspace
            .lock()
            .map_err(|e| wm_core::CoreError::Governance(format!("workspace lock error: {e}")))?;
        let stats = ws.stats();
        let events_published = stats.events_published;
        let spotlight_transfers = stats.spotlight_transfers;
        let arbitration_cycles = stats.arbitration_cycles;
        let events_per_core: serde_json::Map<_, _> = stats
            .events_per_core
            .iter()
            .map(|(c, n)| (c.to_string(), json!(n)))
            .collect();
        let events_per_type: serde_json::Map<_, _> = stats
            .events_per_type
            .iter()
            .map(|(t, n)| (t.to_string(), json!(n)))
            .collect();
        drop(ws);
        Ok(json!({
            "events_published": events_published,
            "spotlight_transfers": spotlight_transfers,
            "arbitration_cycles": arbitration_cycles,
            "events_per_core": events_per_core,
            "events_per_type": events_per_type,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: timescale.status ────────────────────────────────────────────

pub struct TimescaleStatusTool {
    bus: Arc<Mutex<TimescaleBus>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TimescaleStatusTool {
    pub fn new(bus: Arc<Mutex<TimescaleBus>>) -> Self {
        Self {
            bus,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for TimescaleStatusTool {
    fn name(&self) -> &str {
        "timescale.status"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let bus = self.bus.lock().map_err(|e| {
            wm_core::CoreError::Governance(format!("timescale bus lock error: {e}"))
        })?;
        let tiers: Vec<Value> = Tier::all()
            .iter()
            .map(|t| {
                let config = bus.tier_config(*t);
                json!({
                    "name": t.name(),
                    "index": t.index(),
                    "active": bus.is_tier_active(*t),
                    "hook_count": bus.hook_count(*t),
                    "interval_ms": config.interval.as_millis(),
                    "budget_ms": config.budget.as_millis(),
                })
            })
            .collect();
        let brain_wave = format!("{:?}", bus.brain_wave());
        let total_hooks = bus.total_hook_count();
        let total_ticks = bus.total_ticks();
        let total_timeouts = bus.total_timeouts();
        let active_tiers: Vec<_> = bus.active_tiers().iter().map(|t| t.name()).collect();
        let inactive_tiers: Vec<_> = bus.inactive_tiers().iter().map(|t| t.name()).collect();
        drop(bus);
        Ok(json!({
            "brain_wave": brain_wave,
            "total_hooks": total_hooks,
            "total_ticks": total_ticks,
            "total_timeouts": total_timeouts,
            "active_tiers": active_tiers,
            "inactive_tiers": inactive_tiers,
            "tiers": tiers,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Tool: timescale.hooks ─────────────────────────────────────────────

pub struct TimescaleHooksTool {
    bus: Arc<Mutex<TimescaleBus>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TimescaleHooksTool {
    pub fn new(bus: Arc<Mutex<TimescaleBus>>) -> Self {
        Self {
            bus,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for TimescaleHooksTool {
    fn name(&self) -> &str {
        "timescale.hooks"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let tier_str = args
            .get("tier")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("reflex");
        let tier = parse_tier(tier_str)?;

        let bus = self.bus.lock().map_err(|e| {
            wm_core::CoreError::Governance(format!("timescale bus lock error: {e}"))
        })?;
        let hooks: Vec<Value> = bus
            .tier_stats(tier)
            .iter()
            .map(|(id, name, snap)| {
                json!({
                    "id": id,
                    "name": name,
                    "tick_count": snap.tick_count,
                    "success_count": snap.success_count,
                    "timeout_count": snap.timeout_count,
                    "error_count": snap.error_count,
                    "last_duration_us": snap.last_duration_us,
                    "avg_duration_us": snap.avg_duration_us,
                })
            })
            .collect();
        let active = bus.is_tier_active(tier);
        let hook_count = bus.hook_count(tier);
        drop(bus);
        Ok(json!({
            "tier": tier.name(),
            "active": active,
            "hook_count": hook_count,
            "hooks": hooks,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Hex helpers ───────────────────────────────────────────────────────

fn hex_encode(data: &[u8]) -> String {
    use std::fmt::Write;
    let mut s = String::with_capacity(data.len() * 2);
    for b in data {
        let _ = write!(s, "{b:02x}");
    }
    s
}

fn hex_decode(s: &str) -> Result<Vec<u8>, wm_core::CoreError> {
    if s.len() % 2 != 0 {
        return Err(wm_core::CoreError::InvalidArgs(
            "payload hex must have even length".into(),
        ));
    }
    (0..s.len())
        .step_by(2)
        .map(|i| {
            u8::from_str_radix(&s[i..i + 2], 16)
                .map_err(|e| wm_core::CoreError::InvalidArgs(format!("invalid hex: {e}")))
        })
        .collect()
}

// ── Registration ──────────────────────────────────────────────────────

/// Register all v4 integration tools into a registry.
pub fn register_v4(
    registry: &wm_dispatch::ToolRegistry,
    reflex_table: Arc<Mutex<ReflexDispatchTable>>,
    timescale_bus: Arc<Mutex<TimescaleBus>>,
    workspace: Arc<Mutex<GlobalWorkspace>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(ReflexDispatchTool::new(Arc::clone(&reflex_table))))
        .register(Arc::new(ReflexStatusTool::new(reflex_table)))
        .register(Arc::new(WorkspaceSpotlightTool::new(Arc::clone(
            &workspace,
        ))))
        .register(Arc::new(WorkspaceEventsTool::new(Arc::clone(&workspace))))
        .register(Arc::new(WorkspacePublishTool::new(Arc::clone(&workspace))))
        .register(Arc::new(WorkspaceStatsTool::new(workspace)))
        .register(Arc::new(TimescaleStatusTool::new(Arc::clone(
            &timescale_bus,
        ))))
        .register(Arc::new(TimescaleHooksTool::new(timescale_bus)))
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use wm_reflex::{ReflexDispatchTable, builtins};
    use wm_workspace::GlobalWorkspace;

    fn test_reflex_table() -> Arc<Mutex<ReflexDispatchTable>> {
        let mut table = ReflexDispatchTable::permissive();
        builtins::register_builtins(&mut table);
        Arc::new(Mutex::new(table))
    }

    fn test_workspace() -> Arc<Mutex<GlobalWorkspace>> {
        Arc::new(Mutex::new(GlobalWorkspace::new()))
    }

    fn test_timescale_bus() -> Arc<Mutex<TimescaleBus>> {
        Arc::new(Mutex::new(TimescaleBus::default()))
    }

    #[test]
    fn reflex_dispatch_e_stop() {
        let table = test_reflex_table();
        let tool = ReflexDispatchTool::new(Arc::clone(&table));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({"reflex_id": 0})).unwrap();
        assert_eq!(result["command"], "emergency_stop");
        assert_eq!(result["priority"], 255);
    }

    #[test]
    fn reflex_dispatch_with_payload() {
        let table = test_reflex_table();
        let tool = ReflexDispatchTool::new(Arc::clone(&table));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool
            .call(&mut ctx, json!({"reflex_id": 0, "payload": "deadbeef"}))
            .unwrap();
        assert_eq!(result["command"], "emergency_stop");
    }

    #[test]
    fn reflex_dispatch_not_registered() {
        let table = test_reflex_table();
        let tool = ReflexDispatchTool::new(Arc::clone(&table));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let err = tool.call(&mut ctx, json!({"reflex_id": 200})).unwrap_err();
        assert!(err.to_string().contains("no handler registered"));
    }

    #[test]
    fn reflex_dispatch_missing_id() {
        let table = test_reflex_table();
        let tool = ReflexDispatchTool::new(Arc::clone(&table));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let err = tool.call(&mut ctx, json!({})).unwrap_err();
        assert!(err.to_string().contains("reflex_id"));
    }

    #[test]
    fn reflex_status_shows_builtins() {
        let table = test_reflex_table();
        let tool = ReflexStatusTool::new(Arc::clone(&table));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["registered_handlers"], 8);
        assert!(result["dispatch_count"].as_u64().unwrap() == 0);
    }

    #[test]
    fn workspace_spotlight_empty() {
        let ws = test_workspace();
        let tool = WorkspaceSpotlightTool::new(Arc::clone(&ws));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert!(result["spotlight"].is_null());
    }

    #[test]
    fn workspace_spotlight_after_publish() {
        let ws = test_workspace();
        let pub_tool = WorkspacePublishTool::new(Arc::clone(&ws));
        let spot_tool = WorkspaceSpotlightTool::new(Arc::clone(&ws));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);

        pub_tool
            .call(
                &mut ctx,
                json!({
                    "core": "reflex",
                    "event_type": "safety_alert",
                    "urgency": 0.9,
                    "novelty": 0.8,
                    "confidence": 0.95,
                }),
            )
            .unwrap();

        let result = spot_tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["core"], "reflex");
        assert_eq!(result["event_type"], "safety_alert");
    }

    #[test]
    fn workspace_publish_wins_spotlight() {
        let ws = test_workspace();
        let tool = WorkspacePublishTool::new(Arc::clone(&ws));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool
            .call(
                &mut ctx,
                json!({
                    "core": "citta",
                    "event_type": "attention_request",
                    "urgency": 0.7,
                    "novelty": 0.6,
                    "confidence": 0.8,
                }),
            )
            .unwrap();
        assert_eq!(result["won_spotlight"], true);
        assert_eq!(result["spotlight_core"], "citta");
    }

    #[test]
    fn workspace_publish_missing_core() {
        let ws = test_workspace();
        let tool = WorkspacePublishTool::new(Arc::clone(&ws));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let err = tool
            .call(&mut ctx, json!({"event_type": "error"}))
            .unwrap_err();
        assert!(err.to_string().contains("core"));
    }

    #[test]
    fn workspace_publish_invalid_core() {
        let ws = test_workspace();
        let tool = WorkspacePublishTool::new(Arc::clone(&ws));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let err = tool
            .call(
                &mut ctx,
                json!({"core": "nonexistent", "event_type": "error"}),
            )
            .unwrap_err();
        assert!(err.to_string().contains("unknown core"));
    }

    #[test]
    fn workspace_events_after_publish() {
        let ws = test_workspace();
        let pub_tool = WorkspacePublishTool::new(Arc::clone(&ws));
        let events_tool = WorkspaceEventsTool::new(Arc::clone(&ws));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);

        for i in 0..3 {
            pub_tool
                .call(
                    &mut ctx,
                    json!({
                        "core": "citta",
                        "event_type": "attention_request",
                        "urgency": f64::from(i).mul_add(0.1, 0.5),
                        "novelty": 0.5,
                        "confidence": 0.5,
                    }),
                )
                .unwrap();
        }

        let result = events_tool.call(&mut ctx, json!({"count": 10})).unwrap();
        assert_eq!(result["total_published"], 3);
        assert_eq!(result["events"].as_array().unwrap().len(), 3);
    }

    #[test]
    fn workspace_stats_shows_counts() {
        let ws = test_workspace();
        let pub_tool = WorkspacePublishTool::new(Arc::clone(&ws));
        let stats_tool = WorkspaceStatsTool::new(Arc::clone(&ws));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);

        pub_tool
            .call(
                &mut ctx,
                json!({
                    "core": "citta",
                    "event_type": "attention_request",
                    "urgency": 0.7,
                    "novelty": 0.5,
                    "confidence": 0.8,
                }),
            )
            .unwrap();

        let result = stats_tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["events_published"], 1);
        assert_eq!(result["spotlight_transfers"], 1);
    }

    #[test]
    fn timescale_status_default() {
        let bus = test_timescale_bus();
        let tool = TimescaleStatusTool::new(Arc::clone(&bus));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["brain_wave"], "Gamma");
        assert_eq!(result["total_hooks"], 0);
        let tiers = result["tiers"].as_array().unwrap();
        assert_eq!(tiers.len(), 5);
    }

    #[test]
    fn timescale_hooks_empty_tier() {
        let bus = test_timescale_bus();
        let tool = TimescaleHooksTool::new(Arc::clone(&bus));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({"tier": "reflex"})).unwrap();
        assert_eq!(result["tier"], "Reflex");
        assert_eq!(result["hook_count"], 0);
    }

    #[test]
    fn timescale_hooks_invalid_tier() {
        let bus = test_timescale_bus();
        let tool = TimescaleHooksTool::new(Arc::clone(&bus));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let err = tool
            .call(&mut ctx, json!({"tier": "nonexistent"}))
            .unwrap_err();
        assert!(err.to_string().contains("unknown tier"));
    }

    #[test]
    fn parse_core_id_all_builtins() {
        assert_eq!(parse_core_id("citta").unwrap(), CoreId::Citta);
        assert_eq!(parse_core_id("CITTA").unwrap(), CoreId::Citta);
        assert_eq!(parse_core_id("dream").unwrap(), CoreId::Dream);
        assert_eq!(parse_core_id("reflex").unwrap(), CoreId::Reflex);
        assert_eq!(parse_core_id("brain_wave").unwrap(), CoreId::BrainWave);
        assert_eq!(parse_core_id("brainwave").unwrap(), CoreId::BrainWave);
        assert_eq!(parse_core_id("self_model").unwrap(), CoreId::SelfModel);
        assert_eq!(parse_core_id("custom_42").unwrap(), CoreId::Custom(42));
    }

    #[test]
    fn parse_event_type_all_types() {
        assert_eq!(parse_event_type("error").unwrap(), EventType::Error);
        assert_eq!(parse_event_type("reward").unwrap(), EventType::Reward);
        assert_eq!(
            parse_event_type("attention_request").unwrap(),
            EventType::AttentionRequest
        );
        assert_eq!(
            parse_event_type("attention").unwrap(),
            EventType::AttentionRequest
        );
        assert_eq!(
            parse_event_type("novel_detection").unwrap(),
            EventType::NovelDetection
        );
        assert_eq!(
            parse_event_type("safety_alert").unwrap(),
            EventType::SafetyAlert
        );
    }

    #[test]
    fn parse_tier_all_tiers() {
        assert_eq!(parse_tier("reflex").unwrap(), Tier::Reflex);
        assert_eq!(parse_tier("reactive").unwrap(), Tier::Reactive);
        assert_eq!(parse_tier("planning").unwrap(), Tier::Planning);
        assert_eq!(parse_tier("consolidation").unwrap(), Tier::Consolidation);
        assert_eq!(parse_tier("evolutionary").unwrap(), Tier::Evolutionary);
        assert_eq!(parse_tier("0").unwrap(), Tier::Reflex);
        assert_eq!(parse_tier("4").unwrap(), Tier::Evolutionary);
    }

    #[test]
    fn hex_roundtrip() {
        let data = vec![0xde, 0xad, 0xbe, 0xef];
        let encoded = hex_encode(&data);
        assert_eq!(encoded, "deadbeef");
        let decoded = hex_decode(&encoded).unwrap();
        assert_eq!(decoded, data);
    }

    #[test]
    fn hex_decode_odd_length_fails() {
        assert!(hex_decode("abc").is_err());
    }

    #[test]
    fn register_v4_creates_8_tools() {
        let table = test_reflex_table();
        let bus = test_timescale_bus();
        let ws = test_workspace();
        let registry = wm_dispatch::ToolRegistry::new();
        let reg = register_v4(&registry, table, bus, ws);
        assert_eq!(reg.len(), 8);
    }
}
