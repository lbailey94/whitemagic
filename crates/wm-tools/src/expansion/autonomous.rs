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
