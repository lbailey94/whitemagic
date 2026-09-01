//! Resonance (Gan Ying Bus) tools — bus.stats, bus.emit, bus.recent.
//!
//! Gana::Heart — event resonance and system-wide event bus.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use std::sync::Arc;
use std::sync::Mutex;

use serde_json::{Value, json};
use wm_cognitive::{EventType, GanYingBus};
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};

// ── bus.stats ─────────────────────────────────────────────────────────

/// `bus.stats` — Gan Ying Bus statistics.
pub struct BusStatsTool {
    bus: Arc<Mutex<GanYingBus>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl BusStatsTool {
    pub fn new(bus: Arc<Mutex<GanYingBus>>) -> Self {
        Self {
            bus,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("resonance".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for BusStatsTool {
    fn name(&self) -> &str {
        "bus.stats"
    }
    fn gana(&self) -> Gana {
        Gana::Heart
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Gan Ying Bus statistics (events emitted, cascades, subscriber triggers)"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let bus = self
            .bus
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("resonance bus lock: {e}")))?;
        let stats = bus.stats();
        Ok(json!({
            "status": "success",
            "events_emitted": stats.events_emitted,
            "cascade_events": stats.cascade_events,
            "subscriber_triggers": stats.subscriber_triggers,
            "active_subscriptions": stats.active_subscriptions,
            "events_per_category": stats.events_per_category,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── bus.emit ──────────────────────────────────────────────────────────

/// `bus.emit` — Emit a custom event to the Gan Ying Bus.
pub struct BusEmitTool {
    bus: Arc<Mutex<GanYingBus>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl BusEmitTool {
    pub fn new(bus: Arc<Mutex<GanYingBus>>) -> Self {
        Self {
            bus,
            stats: ToolStats::default(),
            // Truthful effects: emitting mutates the bus and, when
            // persistence is enabled, appends to the resonance event log.
            // It was previously declared read-only.
            effects: EffectRow {
                writes: vec![Resource::EventBus, Resource::Filesystem],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for BusEmitTool {
    fn name(&self) -> &str {
        "bus.emit"
    }
    fn gana(&self) -> Gana {
        Gana::Heart
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Emit a custom event to the Gan Ying Bus (args: event_type, source, data)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let event_type_str = args
            .get("event_type")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("event_type required".into()))?;

        let source = args.get("source").and_then(Value::as_str).unwrap_or("user");

        let data = args.get("data").cloned().unwrap_or_else(|| json!({}));

        let event_type = parse_event_type(event_type_str).ok_or_else(|| {
            wm_core::CoreError::InvalidArgs(format!("unknown event type: {event_type_str}"))
        })?;

        let mut bus = self
            .bus
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("resonance bus lock: {e}")))?;
        bus.emit(event_type, source, data);

        Ok(json!({
            "status": "success",
            "event_type": event_type_str,
            "source": source,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── bus.recent ────────────────────────────────────────────────────────

/// `bus.recent` — Get recent events from the bus.
pub struct BusRecentTool {
    bus: Arc<Mutex<GanYingBus>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl BusRecentTool {
    pub fn new(bus: Arc<Mutex<GanYingBus>>) -> Self {
        Self {
            bus,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("resonance".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for BusRecentTool {
    fn name(&self) -> &str {
        "bus.recent"
    }
    fn gana(&self) -> Gana {
        Gana::Heart
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Get recent events from the Gan Ying Bus (optionally filter by category)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(20) as usize;

        let category_filter = args.get("category").and_then(Value::as_str);

        let bus = self
            .bus
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("resonance bus lock: {e}")))?;
        let recent = bus.recent_events(limit);

        let events: Vec<Value> = recent
            .iter()
            .filter(|e| {
                if let Some(cat) = category_filter {
                    e.event_type.category().as_str() == cat
                } else {
                    true
                }
            })
            .map(|e| {
                json!({
                    "event_type": e.event_type.as_str(),
                    "category": e.event_type.category().as_str(),
                    "source": e.source,
                    "timestamp": e.timestamp.to_rfc3339(),
                    "salience": e.salience,
                    "payload": e.payload,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "count": events.len(),
            "events": events,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Helpers ───────────────────────────────────────────────────────────

/// Parse an event type from its string name.
fn parse_event_type(s: &str) -> Option<EventType> {
    EventType::all().into_iter().find(|et| et.as_str() == s)
}

// ── Registration ──────────────────────────────────────────────────────

/// Register all resonance tools into a registry.
pub fn register_resonance(
    registry: &wm_dispatch::ToolRegistry,
    bus: Arc<Mutex<GanYingBus>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(BusStatsTool::new(bus.clone())))
        .register(Arc::new(BusEmitTool::new(bus.clone())))
        .register(Arc::new(BusRecentTool::new(bus)))
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn test_bus() -> Arc<Mutex<GanYingBus>> {
        Arc::new(Mutex::new(GanYingBus::default()))
    }

    #[tokio::test]
    async fn bus_stats_returns_stats() {
        let bus = test_bus();
        let tool = BusStatsTool::new(bus);
        let mut ctx = Context::default();
        let v = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["events_emitted"], 0);
    }

    #[tokio::test]
    async fn bus_emit_emits_event() {
        let bus = test_bus();
        let tool = BusEmitTool::new(bus.clone());
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"event_type": "system_heartbeat", "source": "test", "data": {"foo": 1}}),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");

        let stats_tool = BusStatsTool::new(bus);
        let v2 = stats_tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(v2["events_emitted"], 1);
    }

    #[test]
    fn bus_emit_declares_writes() {
        // Regression: bus.emit was declared read-only while it mutated the
        // event bus (and its persistent JSONL log when enabled).
        let tool = BusEmitTool::new(test_bus());
        assert!(
            tool.effects().writes.contains(&wm_core::Resource::EventBus),
            "bus.emit must declare an EventBus write"
        );
    }

    #[tokio::test]
    async fn bus_emit_unknown_type_errors() {
        let bus = test_bus();
        let tool = BusEmitTool::new(bus);
        let mut ctx = Context::default();
        let result = tool
            .call(&mut ctx, json!({"event_type": "nonexistent.event"}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn bus_emit_missing_type_errors() {
        let bus = test_bus();
        let tool = BusEmitTool::new(bus);
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn bus_recent_returns_events() {
        let bus = test_bus();
        {
            let mut b = bus.lock().unwrap();
            b.emit(EventType::SystemHeartbeat, "test", json!({"n": 1}));
            b.emit(EventType::SystemHeartbeat, "test", json!({"n": 2}));
        }
        let tool = BusRecentTool::new(bus);
        let mut ctx = Context::default();
        let v = tool.call(&mut ctx, json!({"limit": 5})).await.unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["count"], 2);
    }

    #[tokio::test]
    async fn bus_recent_filters_by_category() {
        let bus = test_bus();
        {
            let mut b = bus.lock().unwrap();
            b.emit(EventType::SystemHeartbeat, "test", json!({}));
            b.emit(EventType::MemoryCreated, "test", json!({}));
        }
        let tool = BusRecentTool::new(bus);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"category": "memory"}))
            .await
            .unwrap();
        assert_eq!(v["count"], 1);
    }

    #[tokio::test]
    async fn resonance_tools_are_heart_gana() {
        let bus = test_bus();
        assert_eq!(BusStatsTool::new(bus.clone()).gana(), Gana::Heart);
        assert_eq!(BusEmitTool::new(bus.clone()).gana(), Gana::Heart);
        assert_eq!(BusRecentTool::new(bus).gana(), Gana::Heart);
    }
}
