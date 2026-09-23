//! Autonomous cycle tools — spiral.report, consolidation.connect, consolidation.compress, emergence.scan, retention.prune.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_memory::{AssociationStore, MemoryStore};

pub struct SpiralReportTool {
    tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SpiralReportTool {
    pub fn new(tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>) -> Self {
        Self {
            tracker,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
impl Tool for SpiralReportTool {
    fn name(&self) -> &str {
        "spiral.report"
    }
    fn gana(&self) -> Gana {
        Gana::Encampment
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Report on autonomy expansion or circling (spiral direction, novelty, suspensions)"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let report = {
            let tracker = self
                .tracker
                .lock()
                .map_err(|e| wm_core::CoreError::Internal(format!("spiral tracker lock: {e}")))?;
            tracker.report()
        };
        Ok(report.to_json())
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `consolidation.connect` — propose typed associations for disconnected memories.
///
/// Runs the connect autonomous cycle, gated by Harmony Vector health score.
/// Proposes typed associations for memories that have no incoming or outgoing
/// links. Proposals require human review before action.
pub struct ConsolidationConnectTool {
    store: Arc<MemoryStore>,
    associations: Arc<AssociationStore>,
    spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConsolidationConnectTool {
    pub fn new(
        store: Arc<MemoryStore>,
        associations: Arc<AssociationStore>,
        spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    ) -> Self {
        Self {
            store,
            associations,
            spiral_tracker,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Runs an autonomous cycle: scans memory galaxies and
                // logs the cycle record to the Substrate galaxy.
                reads: super::common::memory_galaxy_reads(),
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for ConsolidationConnectTool {
    fn name(&self) -> &str {
        "consolidation.connect"
    }
    fn gana(&self) -> Gana {
        Gana::Encampment
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Propose typed associations for disconnected memories (gated, human review)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let health_score = args
            .get("health_score")
            .and_then(Value::as_f64)
            .unwrap_or(0.8) as f32;

        let mut runner = wm_cognitive::AutonomousCycleRunner::default();
        let cycle_ctx =
            wm_cognitive::CycleContext::new(&self.store, &self.associations, health_score);
        let result = runner.run_cycle(wm_cognitive::CycleType::Connect, &cycle_ctx);

        // Record in spiral tracker
        if let Ok(mut tracker) = self.spiral_tracker.lock() {
            tracker.record(&result);
        }

        Ok(json!({
            "status": "success",
            "cycle": result.cycle.name(),
            "cycle_status": format!("{:?}", result.status),
            "purpose": result.purpose,
            "memories_scanned": result.memories_scanned,
            "proposals_generated": result.proposals_generated,
            "duration_ms": result.duration_ms,
            "requires_human_review": true,
            "notes": result.notes,
            "connections": result.connections,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `consolidation.compress` — propose merging semantically overlapping memories.
///
/// Runs the compress autonomous cycle. Finds pairs of memories with high
/// semantic similarity and proposes merging the lower-importance one into
/// the higher-importance one. Requires human review.
pub struct ConsolidationCompressTool {
    store: Arc<MemoryStore>,
    associations: Arc<AssociationStore>,
    spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConsolidationCompressTool {
    pub fn new(
        store: Arc<MemoryStore>,
        associations: Arc<AssociationStore>,
        spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    ) -> Self {
        Self {
            store,
            associations,
            spiral_tracker,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Runs an autonomous cycle: scans memory galaxies and
                // logs the cycle record to the Substrate galaxy.
                reads: super::common::memory_galaxy_reads(),
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for ConsolidationCompressTool {
    fn name(&self) -> &str {
        "consolidation.compress"
    }
    fn gana(&self) -> Gana {
        Gana::Encampment
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Propose merging semantically overlapping memories (gated, human review)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let health_score = args
            .get("health_score")
            .and_then(Value::as_f64)
            .unwrap_or(0.8) as f32;

        let mut runner = wm_cognitive::AutonomousCycleRunner::default();
        let cycle_ctx =
            wm_cognitive::CycleContext::new(&self.store, &self.associations, health_score);
        let result = runner.run_cycle(wm_cognitive::CycleType::Compress, &cycle_ctx);

        // Record in spiral tracker
        if let Ok(mut tracker) = self.spiral_tracker.lock() {
            tracker.record(&result);
        }

        Ok(json!({
            "status": "success",
            "cycle": result.cycle.name(),
            "cycle_status": format!("{:?}", result.status),
            "purpose": result.purpose,
            "memories_scanned": result.memories_scanned,
            "proposals_generated": result.proposals_generated,
            "duration_ms": result.duration_ms,
            "requires_human_review": true,
            "notes": result.notes,
            "compressions": result.compressions,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `emergence.scan` — detect tag/topic emergence patterns.
///
/// Runs the emergence autonomous cycle. Scans all galaxies and aggregates
/// tag frequencies to detect emerging patterns. Logged to Gnosis but does
/// not require human review (no destructive action).
pub struct EmergenceScanTool {
    store: Arc<MemoryStore>,
    associations: Arc<AssociationStore>,
    spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl EmergenceScanTool {
    pub fn new(
        store: Arc<MemoryStore>,
        associations: Arc<AssociationStore>,
        spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    ) -> Self {
        Self {
            store,
            associations,
            spiral_tracker,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Runs an autonomous cycle: scans memory galaxies and
                // logs the cycle record to the Substrate galaxy.
                reads: super::common::memory_galaxy_reads(),
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for EmergenceScanTool {
    fn name(&self) -> &str {
        "emergence.scan"
    }
    fn gana(&self) -> Gana {
        Gana::Encampment
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Detect tag/topic emergence patterns across memories (gated, logged)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let health_score = args
            .get("health_score")
            .and_then(Value::as_f64)
            .unwrap_or(0.8) as f32;

        let mut runner = wm_cognitive::AutonomousCycleRunner::default();
        let cycle_ctx =
            wm_cognitive::CycleContext::new(&self.store, &self.associations, health_score);
        let result = runner.run_cycle(wm_cognitive::CycleType::Emergence, &cycle_ctx);

        // Record in spiral tracker
        if let Ok(mut tracker) = self.spiral_tracker.lock() {
            tracker.record(&result);
        }

        Ok(json!({
            "status": "success",
            "cycle": result.cycle.name(),
            "cycle_status": format!("{:?}", result.status),
            "purpose": result.purpose,
            "memories_scanned": result.memories_scanned,
            "proposals_generated": result.proposals_generated,
            "duration_ms": result.duration_ms,
            "requires_human_review": false,
            "notes": result.notes,
            "emergences": result.emergences,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `retention.prune` — identify memories ready for forgetting.
///
/// Runs the prune autonomous cycle. Computes composite retention scores
/// from importance, neuro_score, and access recency. High-importance
/// memories require human review before any action.
pub struct RetentionPruneTool {
    store: Arc<MemoryStore>,
    associations: Arc<AssociationStore>,
    spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl RetentionPruneTool {
    pub fn new(
        store: Arc<MemoryStore>,
        associations: Arc<AssociationStore>,
        spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    ) -> Self {
        Self {
            store,
            associations,
            spiral_tracker,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Runs an autonomous cycle: scans memory galaxies and
                // logs the cycle record to the Substrate galaxy.
                reads: super::common::memory_galaxy_reads(),
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for RetentionPruneTool {
    fn name(&self) -> &str {
        "retention.prune"
    }
    fn gana(&self) -> Gana {
        Gana::Encampment
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Identify memories ready for forgetting based on decay + neuro_score (gated, human review)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let health_score = args
            .get("health_score")
            .and_then(Value::as_f64)
            .unwrap_or(0.8) as f32;

        let mut runner = wm_cognitive::AutonomousCycleRunner::default();
        let cycle_ctx =
            wm_cognitive::CycleContext::new(&self.store, &self.associations, health_score);
        let result = runner.run_cycle(wm_cognitive::CycleType::Prune, &cycle_ctx);

        // Record in spiral tracker
        if let Ok(mut tracker) = self.spiral_tracker.lock() {
            tracker.record(&result);
        }

        Ok(json!({
            "status": "success",
            "cycle": result.cycle.name(),
            "cycle_status": format!("{:?}", result.status),
            "purpose": result.purpose,
            "memories_scanned": result.memories_scanned,
            "proposals_generated": result.proposals_generated,
            "duration_ms": result.duration_ms,
            "requires_human_review": true,
            "notes": result.notes,
            "prunes": result.prunes,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `sensorimotor.scan` — poll sensors, evaluate reflexes, execute commands.
///
/// Runs the sensorimotor autonomous cycle. Polls all registered sensors,
/// evaluates reflex rules against current readings, and executes any triggered
/// actuator commands. Results are logged to Gnosis and recorded in the spiral
/// tracker. Does not require human review.
pub struct SensorimotorScanTool {
    store: Arc<MemoryStore>,
    associations: Arc<AssociationStore>,
    spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    sensorimotor_bus: Arc<std::sync::Mutex<wm_substrate::sensorimotor::SensorimotorBus>>,
    reflex_loop: Arc<std::sync::Mutex<wm_substrate::sensorimotor::ReflexLoop>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SensorimotorScanTool {
    pub fn new(
        store: Arc<MemoryStore>,
        associations: Arc<AssociationStore>,
        spiral_tracker: Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
        sensorimotor_bus: Arc<std::sync::Mutex<wm_substrate::sensorimotor::SensorimotorBus>>,
        reflex_loop: Arc<std::sync::Mutex<wm_substrate::sensorimotor::ReflexLoop>>,
    ) -> Self {
        Self {
            store,
            associations,
            spiral_tracker,
            sensorimotor_bus,
            reflex_loop,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Runs an autonomous cycle: scans memory galaxies and
                // logs the cycle record to the Substrate galaxy.
                reads: super::common::memory_galaxy_reads(),
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for SensorimotorScanTool {
    fn name(&self) -> &str {
        "sensorimotor.scan"
    }
    fn gana(&self) -> Gana {
        Gana::Encampment
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Poll sensors, evaluate reflex rules, and execute triggered actuator commands (gated, logged)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let health_score = args
            .get("health_score")
            .and_then(Value::as_f64)
            .unwrap_or(0.8) as f32;

        let mut runner = wm_cognitive::AutonomousCycleRunner::default();
        let cycle_ctx =
            wm_cognitive::CycleContext::new(&self.store, &self.associations, health_score)
                .with_sensorimotor(&self.sensorimotor_bus, &self.reflex_loop);

        let result = runner.run_cycle(wm_cognitive::CycleType::Sensorimotor, &cycle_ctx);

        if let Ok(mut tracker) = self.spiral_tracker.lock() {
            tracker.record(&result);
        }

        Ok(json!({
            "status": "success",
            "cycle": result.cycle.name(),
            "cycle_status": format!("{:?}", result.status),
            "purpose": result.purpose,
            "memories_scanned": result.memories_scanned,
            "proposals_generated": result.proposals_generated,
            "duration_ms": result.duration_ms,
            "requires_human_review": false,
            "notes": result.notes,
            "sensorimotor": result.sensorimotor,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::Galaxy;
    use wm_memory::Memory;

    fn parts() -> (
        tempfile::TempDir,
        Arc<MemoryStore>,
        Arc<AssociationStore>,
        Arc<std::sync::Mutex<wm_cognitive::SpiralTracker>>,
    ) {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let assoc = Arc::new(AssociationStore::open(store.env()).unwrap());
        let tracker = Arc::new(std::sync::Mutex::new(wm_cognitive::SpiralTracker::default()));
        (tmp, store, assoc, tracker)
    }

    #[tokio::test]
    async fn spiral_report_reflects_recorded_cycles() {
        let tracker = Arc::new(std::sync::Mutex::new(wm_cognitive::SpiralTracker::default()));
        tracker
            .lock()
            .unwrap()
            .record(&wm_cognitive::CycleResult::new(
                wm_cognitive::CycleType::Connect,
                wm_cognitive::CycleStatus::Completed,
            ));

        let result = SpiralReportTool::new(tracker)
            .call(&mut Context::default(), json!({}))
            .await
            .unwrap();
        assert_eq!(result["total_cycles_run"], 1);
        assert_eq!(result["cycles"][0]["cycle"], "consolidation.connect");
    }

    #[tokio::test]
    async fn connect_tool_plumbs_the_health_gate_before_touching_memories() {
        let (_tmp, store, assoc, tracker) = parts();
        let mut mem1 = Memory::new(Galaxy::Codex, "Rust algorithm data structure".into());
        mem1.metadata.tags = vec!["rust".into(), "algorithm".into()];
        store.put_semantic(Galaxy::Codex, &mut mem1).unwrap();
        let mut mem2 = Memory::new(Galaxy::Codex, "Rust algorithm data method".into());
        mem2.metadata.tags = vec!["rust".into(), "algorithm".into()];
        store.put_semantic(Galaxy::Codex, &mut mem2).unwrap();

        let tool = ConsolidationConnectTool::new(store, assoc, tracker);
        let gated = tool
            .call(&mut Context::default(), json!({"health_score": 0.1}))
            .await
            .unwrap();
        assert_eq!(gated["cycle_status"], "SkippedHealth");
        assert_eq!(gated["memories_scanned"], 0);
        assert_eq!(gated["connections"].as_array().unwrap().len(), 0);
        assert_eq!(gated["requires_human_review"], true);

        let ran = tool
            .call(&mut Context::default(), json!({"health_score": 0.9}))
            .await
            .unwrap();
        assert_eq!(ran["cycle_status"], "Completed");
        assert!(!ran["connections"].as_array().unwrap().is_empty());
        assert_eq!(ran["requires_human_review"], true);
    }

    #[tokio::test]
    async fn compress_tool_reports_primary_by_importance() {
        let (_tmp, store, assoc, tracker) = parts();
        let mut mem1 = Memory::new(Galaxy::Codex, "algorithm data structure rust".into());
        mem1.metadata.importance = 0.8;
        mem1.metadata.tags = vec!["rust".into(), "algorithm".into()];
        store.put_semantic(Galaxy::Codex, &mut mem1).unwrap();
        let mut mem2 = Memory::new(Galaxy::Codex, "algorithm data method rust".into());
        mem2.metadata.importance = 0.3;
        mem2.metadata.tags = vec!["rust".into(), "algorithm".into()];
        store.put_semantic(Galaxy::Codex, &mut mem2).unwrap();

        let result = ConsolidationCompressTool::new(store, assoc, tracker)
            .call(&mut Context::default(), json!({"health_score": 0.9}))
            .await
            .unwrap();
        assert_eq!(result["cycle_status"], "Completed");
        assert_eq!(result["requires_human_review"], true);
        assert_eq!(
            result["compressions"][0]["primary_id"].as_str().unwrap(),
            mem1.metadata.id.to_string()
        );
    }

    #[tokio::test]
    async fn emergence_tool_reports_frequent_tags_without_review() {
        let (_tmp, store, assoc, tracker) = parts();
        for i in 0..5 {
            let mut mem = Memory::new(Galaxy::Codex, format!("rust memory item {i}"));
            mem.metadata.tags = vec!["rust".into(), "memory".into()];
            store.put_semantic(Galaxy::Codex, &mut mem).unwrap();
        }

        let result = EmergenceScanTool::new(store, assoc, tracker)
            .call(&mut Context::default(), json!({"health_score": 0.9}))
            .await
            .unwrap();
        assert_eq!(result["cycle_status"], "Completed");
        assert_eq!(result["requires_human_review"], false);
        let rust = result["emergences"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["tag"] == "rust")
            .expect("rust emergence expected");
        assert!(rust["frequency"].as_u64().unwrap() >= 3);
    }

    #[tokio::test]
    async fn prune_tool_marks_low_retention_and_skips_protected() {
        let (_tmp, store, assoc, tracker) = parts();
        let mut low = Memory::new(Galaxy::Codex, "unimportant old memory".into())
            .with_importance(0.05)
            .with_neuro_score(0.05);
        low.metadata.accessed_at = chrono::Utc::now() - chrono::Duration::days(365);
        store.put(Galaxy::Codex, &low).unwrap();
        let mut protected = Memory::new(Galaxy::Codex, "protected old memory".into())
            .with_importance(0.05)
            .with_neuro_score(0.05)
            .with_protection(true);
        protected.metadata.accessed_at = chrono::Utc::now() - chrono::Duration::days(365);
        store.put(Galaxy::Codex, &protected).unwrap();

        let result = RetentionPruneTool::new(store, assoc, tracker)
            .call(&mut Context::default(), json!({"health_score": 0.9}))
            .await
            .unwrap();
        assert_eq!(result["cycle_status"], "Completed");
        let prunes = result["prunes"].as_array().unwrap();
        let ids: Vec<&str> = prunes
            .iter()
            .map(|p| p["memory_id"].as_str().unwrap())
            .collect();
        let low_id = low.metadata.id.to_string();
        let protected_id = protected.metadata.id.to_string();
        assert!(ids.contains(&low_id.as_str()), "low-retention id expected");
        assert!(
            !ids.contains(&protected_id.as_str()),
            "protected memory must not be pruned"
        );
    }

    #[tokio::test]
    async fn sensorimotor_tool_fails_closed_without_an_actuation_mask() {
        use wm_substrate::sensorimotor::{
            ActuatorKind, ReflexRule, SensorKind, SensorimotorBus, StubActuator, StubSensor,
        };

        let (_tmp, store, assoc, tracker) = parts();
        let mut bus = SensorimotorBus::new(100);
        bus.register_sensor(Box::new(StubSensor::new(
            "test_temp",
            SensorKind::Temperature,
            80.0,
        )));
        bus.register_actuator(Box::new(StubActuator::new("fan0", ActuatorKind::Motor)));
        let bus = Arc::new(std::sync::Mutex::new(bus));
        let reflex = Arc::new(std::sync::Mutex::new(
            wm_substrate::sensorimotor::ReflexLoop::new(),
        ));
        reflex.lock().unwrap().add_rule(ReflexRule::above(
            "test_temp",
            "fan0",
            ActuatorKind::Motor,
            50.0,
            1.0,
            0.0,
        ));

        let result = SensorimotorScanTool::new(store, assoc, tracker, bus, reflex)
            .call(&mut Context::default(), json!({"health_score": 0.9}))
            .await
            .unwrap();
        assert_eq!(result["cycle_status"], "Completed");
        assert_eq!(result["requires_human_review"], false);
        assert!(
            result["notes"]
                .as_str()
                .unwrap()
                .contains("actuation denied"),
            "fail-closed refusal must be visible: {}",
            result["notes"]
        );
        // The proposal is recorded but no command executed: the denied path
        // must not claim a triggered reflex.
        assert_eq!(result["proposals_generated"], 1);
        assert_eq!(result["sensorimotor"][0]["reflex_triggered"], false);
    }
}
