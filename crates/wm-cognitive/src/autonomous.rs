//! Grounded Autonomous Cycles — Phase E (Lila / Controlled Emergence).
//!
//! Four governed cognitive cycles that operate on memory:
//! - **connect**: Propose typed associations for disconnected memories
//! - **compress**: Propose merging semantically overlapping memories
//! - **emergence**: Detect tag/topic emergence patterns
//! - **prune**: Identify memories ready for forgetting
//!
//! All cycles:
//! - Declare a purpose
//! - Check Harmony Vector (health-score gate)
//! - Have time and memory budgets
//! - Produce actionable output (proposals, not direct mutations)
//! - Log to Gnosis (Substrate galaxy)
//! - Suspend on non-novel output (same signature as last run)

use std::collections::{HashMap, HashSet};
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};
use wm_bicameral::ScenarioEngine;
use wm_core::{DynamicGalaxyRegistry, Galaxy, Result};
use wm_memory::{AssociationStore, LinkType, Memory, MemoryStore, MemoryType};
use wm_substrate::sensorimotor::{ReflexLoop, SensorimotorBus};

// ── Cycle Types ───────────────────────────────────────────────────────

/// Which autonomous cycle to run.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CycleType {
    /// Propose typed associations for disconnected memories
    Connect,
    /// Propose merging semantically overlapping memories
    Compress,
    /// Detect tag/topic emergence patterns
    Emergence,
    /// Identify memories ready for forgetting
    Prune,
    /// RSI Phase 2: Analyze friction entries and propose concrete improvements
    Improve,
    /// RSI Phase 3: Generate adversarial test proposals against v4's own systems
    Redteam,
    /// Poll sensors, evaluate reflex rules, and execute triggered actuator commands
    Sensorimotor,
    /// Imagination Engine: generate and evaluate hypotheses for open problems
    Research,
}

impl CycleType {
    /// All cycle types in canonical order.
    #[must_use]
    pub const fn all() -> [Self; 8] {
        [
            Self::Connect,
            Self::Compress,
            Self::Emergence,
            Self::Prune,
            Self::Improve,
            Self::Redteam,
            Self::Sensorimotor,
            Self::Research,
        ]
    }

    /// Human-readable name.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Connect => "consolidation.connect",
            Self::Compress => "consolidation.compress",
            Self::Emergence => "emergence.scan",
            Self::Prune => "retention.prune",
            Self::Improve => "improve.scan",
            Self::Redteam => "redteam.scan",
            Self::Sensorimotor => "sensorimotor.scan",
            Self::Research => "research.scan",
        }
    }

    /// Purpose declaration for governance.
    #[must_use]
    pub const fn purpose(self) -> &'static str {
        match self {
            Self::Connect => "Connect isolated memories by proposing typed associations",
            Self::Compress => "Reduce redundancy by proposing merges of overlapping memories",
            Self::Emergence => "Detect emerging tag and topic patterns across memories",
            Self::Prune => "Identify low-value memories ready for mindful forgetting",
            Self::Improve => "Analyze friction entries and propose concrete system improvements",
            Self::Redteam => {
                "Generate adversarial test proposals against v4 governance, karma, and isolation systems"
            }
            Self::Sensorimotor => {
                "Poll sensors, evaluate reflex rules, and execute triggered actuator commands"
            }
            Self::Research => {
                "Generate and evaluate hypotheses for open problems using the Imagination Engine"
            }
        }
    }

    /// Whether this cycle requires human review for its proposals.
    #[must_use]
    pub const fn requires_human_review(self) -> bool {
        match self {
            Self::Emergence | Self::Sensorimotor | Self::Research => false, // logged but no destructive action
            Self::Connect | Self::Compress | Self::Prune | Self::Improve | Self::Redteam => true,
        }
    }
}

// ── Configuration ─────────────────────────────────────────────────────

/// Configuration for the autonomous cycle runner.
#[derive(Debug, Clone)]
pub struct CycleConfig {
    /// Minimum health score (0.0–1.0) required to run any cycle.
    pub min_health_score: f32,
    /// Maximum time budget per cycle.
    pub time_budget: Duration,
    /// Maximum memories to scan per cycle.
    pub memory_budget: usize,
    /// Maximum proposals to generate per cycle.
    pub max_proposals: usize,
    /// Semantic similarity threshold for connect/compress (0.0–1.0).
    pub similarity_threshold: f32,
    /// Minimum importance for human-review gate in prune.
    pub prune_human_review_importance: f32,
    /// Composite retention score below which a memory is a prune candidate.
    pub prune_retention_threshold: f32,
    /// Minimum tag frequency for emergence detection.
    pub emergence_min_frequency: usize,
    /// Number of consecutive identical outputs before suspension.
    pub max_identical_outputs: usize,
}

impl Default for CycleConfig {
    fn default() -> Self {
        Self {
            min_health_score: 0.3,
            time_budget: Duration::from_secs(10),
            memory_budget: 5_000,
            max_proposals: 50,
            similarity_threshold: 0.7,
            prune_human_review_importance: 0.7,
            prune_retention_threshold: 0.2,
            emergence_min_frequency: 3,
            max_identical_outputs: 3,
        }
    }
}

// ── Proposal Types ────────────────────────────────────────────────────

/// A proposed system improvement derived from friction analysis.
/// RSI Phase 2: Grounded in real friction entries, not abstract parameters.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImprovementProposal {
    /// Friction entry IDs that informed this proposal
    pub source_friction_ids: Vec<String>,
    /// Category of friction (ux, performance, error, missing_feature, confusing)
    pub category: String,
    /// Severity level (low, medium, high)
    pub severity: String,
    /// Tool or subsystem name
    pub target: String,
    /// Human-readable description of the problem
    pub problem: String,
    /// Concrete recommended action
    pub recommended_action: String,
    /// Number of friction entries that match this pattern
    pub pattern_count: usize,
}

/// A proposed adversarial test against v4's own systems.
/// RSI Phase 3: The system tries to break itself and proposes fixes.
/// Bounded by SpiralTracker to prevent infinite adversarial loops.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RedteamProposal {
    /// Target system being tested (governance, karma, mandala, dispatch, spiral)
    pub target_system: String,
    /// Attack vector description
    pub attack_vector: String,
    /// Expected (safe) behavior
    pub expected_behavior: String,
    /// Proposed test code (pseudocode)
    pub test_pseudocode: String,
    /// Risk level if the attack succeeds (low, medium, high, critical)
    pub risk_level: String,
    /// Whether existing tests cover this vector
    pub existing_coverage: bool,
    /// Recommended fix if the test fails
    pub recommended_fix: String,
}

/// Result of a sensorimotor cycle — sensor readings and triggered reflex actions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorimotorProposal {
    /// Sensor ID that was polled
    pub sensor_id: String,
    /// Sensor kind (temperature, load, etc.)
    pub sensor_kind: String,
    /// Sensor reading value
    pub value: f64,
    /// Whether a reflex was triggered by this sensor
    pub reflex_triggered: bool,
    /// Actuator ID that was commanded (if reflex triggered)
    pub actuator_id: Option<String>,
    /// Command value sent to actuator (if reflex triggered)
    pub command_value: Option<f64>,
}

/// A research hypothesis generated by the Imagination Engine.
/// Phase II: The Research cycle imagines solutions to open problems.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResearchProposal {
    /// The open problem or question being addressed
    pub problem: String,
    /// Source memory IDs that informed this hypothesis
    pub source_memory_ids: Vec<String>,
    /// The imagined hypothesis / proposed solution
    pub hypothesis: String,
    /// Predicted outcome description
    pub predicted_outcome: String,
    /// Confidence in the hypothesis (0.0–1.0)
    pub confidence: f32,
    /// Novelty score (0.0–1.0)
    pub novelty: f32,
    /// Evaluation score from multi-criteria scoring (0.0–1.0)
    pub score: f32,
    /// Whether this hypothesis was stored as a Hypothesis memory
    pub stored: bool,
}

/// A proposed association between two disconnected memories.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConnectionProposal {
    /// Source memory ID
    pub source_id: String,
    /// Target memory ID
    pub target_id: String,
    /// Proposed link type
    pub link_type: String,
    /// Semantic similarity score (0.0–1.0)
    pub similarity: f32,
    /// Source galaxy
    pub source_galaxy: String,
    /// Target galaxy
    pub target_galaxy: String,
    /// Human-readable reason
    pub reason: String,
}

/// A proposed merge of two semantically overlapping memories.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompressionProposal {
    /// Primary memory ID (the one to keep)
    pub primary_id: String,
    /// Secondary memory ID (the one to merge into primary)
    pub secondary_id: String,
    /// Galaxy where both memories reside
    pub galaxy: String,
    /// Semantic similarity score (0.0–1.0)
    pub similarity: f32,
    /// Content overlap ratio (0.0–1.0)
    pub content_overlap: f32,
    /// Human-readable reason
    pub reason: String,
}

/// An emerging tag or topic pattern.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmergencePattern {
    /// Tag or topic name
    pub tag: String,
    /// Number of memories with this tag
    pub frequency: usize,
    /// Growth rate compared to historical baseline (if available)
    pub growth_rate: f32,
    /// Average importance of memories with this tag
    pub avg_importance: f32,
    /// Galaxies where this tag appears
    pub galaxies: Vec<String>,
}

/// A memory identified as a candidate for forgetting.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PruneCandidate {
    /// Memory ID
    pub memory_id: String,
    /// Galaxy
    pub galaxy: String,
    /// Current importance
    pub importance: f32,
    /// Current neuro_score
    pub neuro_score: f32,
    /// Composite retention score
    pub retention_score: f32,
    /// Whether human review is required (high-importance memories)
    pub requires_human_review: bool,
    /// Recommended action
    pub recommended_action: String,
    /// Human-readable reason
    pub reason: String,
}

// ── Cycle Result ──────────────────────────────────────────────────────

/// Status of a cycle execution.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum CycleStatus {
    /// Cycle ran successfully and produced output
    Completed,
    /// Cycle was skipped due to low health score
    SkippedHealth,
    /// Cycle exceeded its time budget
    SkippedTimeBudget,
    /// Cycle was suspended due to non-novel output
    Suspended,
    /// Cycle ran but produced no proposals
    NoProposals,
    /// Cycle encountered an error
    Error,
}

/// Result of a single autonomous cycle execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CycleResult {
    /// Which cycle ran
    pub cycle: CycleType,
    /// Execution status
    pub status: CycleStatus,
    /// Number of memories scanned
    pub memories_scanned: usize,
    /// Number of proposals generated
    pub proposals_generated: usize,
    /// Duration of the cycle
    pub duration_ms: u64,
    /// Purpose declaration
    pub purpose: String,
    /// Human-readable notes
    pub notes: String,
    /// Connection proposals (if Connect cycle)
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub connections: Vec<ConnectionProposal>,
    /// Compression proposals (if Compress cycle)
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub compressions: Vec<CompressionProposal>,
    /// Emergence patterns (if Emergence cycle)
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub emergences: Vec<EmergencePattern>,
    /// Prune candidates (if Prune cycle)
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub prunes: Vec<PruneCandidate>,
    /// Improvement proposals (if Improve cycle)
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub improvements: Vec<ImprovementProposal>,
    /// Red-team proposals (if Redteam cycle)
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub redteam: Vec<RedteamProposal>,
    /// Sensorimotor proposals (if Sensorimotor cycle)
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub sensorimotor: Vec<SensorimotorProposal>,
    /// Research hypotheses (if Research cycle)
    #[serde(skip_serializing_if = "Vec::is_empty", default)]
    pub hypotheses: Vec<ResearchProposal>,
}

impl CycleResult {
    /// Create a result with the given cycle and status.
    #[must_use]
    pub fn new(cycle: CycleType, status: CycleStatus) -> Self {
        Self {
            cycle,
            status,
            memories_scanned: 0,
            proposals_generated: 0,
            duration_ms: 0,
            purpose: cycle.purpose().to_string(),
            notes: String::new(),
            connections: Vec::new(),
            compressions: Vec::new(),
            emergences: Vec::new(),
            prunes: Vec::new(),
            improvements: Vec::new(),
            redteam: Vec::new(),
            sensorimotor: Vec::new(),
            hypotheses: Vec::new(),
        }
    }

    /// Convert to JSON for Gnosis logging.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "cycle": self.cycle.name(),
            "status": format!("{:?}", self.status),
            "memories_scanned": self.memories_scanned,
            "proposals_generated": self.proposals_generated,
            "duration_ms": self.duration_ms,
            "purpose": self.purpose,
            "notes": self.notes,
            "requires_human_review": self.cycle.requires_human_review(),
        })
    }

    /// Compute a signature for novelty detection.
    /// Returns a hash-like string that captures the essence of the output.
    #[must_use]
    pub fn signature(&self) -> String {
        let mut parts: Vec<String> = Vec::new();
        for c in &self.connections {
            parts.push(format!("{}:{}", c.source_id, c.target_id));
        }
        for c in &self.compressions {
            parts.push(format!("{}:{}", c.primary_id, c.secondary_id));
        }
        for e in &self.emergences {
            parts.push(format!("{}:{}", e.tag, e.frequency));
        }
        for p in &self.prunes {
            parts.push(p.memory_id.clone());
        }
        for i in &self.improvements {
            parts.push(format!("{}:{}:{}", i.target, i.category, i.pattern_count));
        }
        for r in &self.redteam {
            parts.push(format!("{}:{}", r.target_system, r.attack_vector));
        }
        for s in &self.sensorimotor {
            parts.push(format!("{}:{}", s.sensor_id, s.reflex_triggered));
        }
        for h in &self.hypotheses {
            parts.push(format!("{}:{}", h.problem, h.confidence));
        }
        parts.sort();
        parts.join("|")
    }
}

// ── Autonomous Cycle Runner ───────────────────────────────────────────

/// Context provided to autonomous cycles.
pub struct CycleContext<'a> {
    /// LMDB memory store
    pub store: &'a MemoryStore,
    /// Association store for cross-galaxy links
    pub associations: &'a AssociationStore,
    /// Current health score from Harmony Vector (0.0–1.0)
    pub health_score: f32,
    /// Optional sensorimotor bus for embodiment cycles
    pub sensorimotor_bus: Option<&'a std::sync::Mutex<SensorimotorBus>>,
    /// Optional reflex loop for embodiment cycles
    pub reflex_loop: Option<&'a std::sync::Mutex<ReflexLoop>>,
    /// Optional imagination engine (ScenarioEngine) for the Research cycle
    pub imagination: Option<&'a ScenarioEngine>,
    /// Optional DynamicGalaxyRegistry for creating dynamic galaxies from emergence clusters
    pub dynamic_galaxies: Option<&'a std::sync::Mutex<DynamicGalaxyRegistry>>,
}

impl<'a> CycleContext<'a> {
    /// Create a new cycle context.
    pub const fn new(
        store: &'a MemoryStore,
        associations: &'a AssociationStore,
        health_score: f32,
    ) -> Self {
        Self {
            store,
            associations,
            health_score,
            sensorimotor_bus: None,
            reflex_loop: None,
            imagination: None,
            dynamic_galaxies: None,
        }
    }

    /// Attach sensorimotor bus and reflex loop for embodiment cycles.
    #[must_use]
    pub const fn with_sensorimotor(
        mut self,
        bus: &'a std::sync::Mutex<SensorimotorBus>,
        reflex: &'a std::sync::Mutex<ReflexLoop>,
    ) -> Self {
        self.sensorimotor_bus = Some(bus);
        self.reflex_loop = Some(reflex);
        self
    }

    /// Attach an imagination engine (ScenarioEngine) for the Research cycle.
    #[must_use]
    pub const fn with_imagination(mut self, engine: &'a ScenarioEngine) -> Self {
        self.imagination = Some(engine);
        self
    }

    /// Attach a DynamicGalaxyRegistry for creating dynamic galaxies from emergence clusters.
    #[must_use]
    pub const fn with_dynamic_galaxies(
        mut self,
        registry: &'a std::sync::Mutex<DynamicGalaxyRegistry>,
    ) -> Self {
        self.dynamic_galaxies = Some(registry);
        self
    }

    /// Scan all non-system galaxies and return (galaxy, memories) pairs.
    fn scan_all_galaxies(&self, limit: usize) -> Result<Vec<(Galaxy, Vec<Memory>)>> {
        let mut result = Vec::new();
        for galaxy in Galaxy::all() {
            match galaxy {
                Galaxy::Substrate
                | Galaxy::Dharma
                | Galaxy::Karma
                | Galaxy::Embeddings
                | Galaxy::Associations => continue,
                _ => {}
            }
            let mems = self.store.scan(galaxy, limit)?;
            if !mems.is_empty() {
                result.push((galaxy, mems));
            }
        }
        Ok(result)
    }

    /// Check if a memory has any associations (incoming or outgoing).
    fn is_disconnected(&self, mem_id: uuid::Uuid) -> bool {
        let env = self.store.env();
        let outgoing = self.associations.find_from(env, mem_id).unwrap_or_default();
        let incoming = self.associations.find_to(env, mem_id).unwrap_or_default();
        outgoing.is_empty() && incoming.is_empty()
    }

    /// Log a cycle result to Gnosis (Substrate galaxy).
    fn log_to_gnosis(&self, result: &CycleResult) {
        let mut log_mem = Memory::new(
            Galaxy::Substrate,
            format!(
                "autonomous cycle '{}' {}: {}",
                result.cycle.name(),
                match result.status {
                    CycleStatus::Completed => "completed",
                    CycleStatus::Suspended => "suspended",
                    CycleStatus::SkippedHealth => "skipped (health)",
                    CycleStatus::SkippedTimeBudget => "skipped (time budget)",
                    CycleStatus::NoProposals => "no proposals",
                    CycleStatus::Error => "error",
                },
                result.notes,
            ),
        );
        log_mem.metadata.tags = vec![
            "autonomous".into(),
            "cycle".into(),
            result.cycle.name().into(),
        ];
        log_mem.metadata.importance = 0.3;
        let _ = self.store.put(Galaxy::Substrate, &log_mem);
    }
}

/// Tracks consecutive identical outputs for suspension.
struct NoveltyTracker {
    /// Last output signature per cycle type
    last_signatures: HashMap<CycleType, String>,
    /// Consecutive identical count per cycle type
    consecutive_identical: HashMap<CycleType, usize>,
    /// Max identical outputs before suspension
    max_identical: usize,
}

impl NoveltyTracker {
    fn new(max_identical: usize) -> Self {
        Self {
            last_signatures: HashMap::new(),
            consecutive_identical: HashMap::new(),
            max_identical,
        }
    }

    /// Check if the cycle should be suspended based on output novelty.
    /// Returns `true` if the output is novel (should proceed), `false` if suspended.
    fn check_and_update(&mut self, cycle: CycleType, result: &CycleResult) -> bool {
        let sig = result.signature();
        let prev = self.last_signatures.get(&cycle);
        let is_identical = prev.is_some_and(|p| p == &sig);

        let count = self.consecutive_identical.entry(cycle).or_insert(0);
        if is_identical {
            *count += 1;
        } else {
            *count = 0;
        }
        self.last_signatures.insert(cycle, sig);

        *count < self.max_identical
    }
}

/// Autonomous cycle runner — executes governed cognitive cycles.
///
/// Each cycle is gated by the Harmony Vector health score, bounded by
/// time and memory budgets, and produces actionable proposals (not
/// direct mutations). All outputs are logged to Gnosis for transparency.
/// Cycles that produce identical output consecutively are suspended.
pub struct AutonomousCycleRunner {
    config: CycleConfig,
    novelty: NoveltyTracker,
    /// Total cycles run
    cycles_run: u64,
    /// Total proposals generated
    proposals_generated: u64,
    /// Total cycles suspended
    cycles_suspended: u64,
    /// Optional learned cycle strategy for adaptive cycle selection (Phase 6)
    learned: Option<wm_core::LearnedCycleStrategy>,
}

impl AutonomousCycleRunner {
    /// Create a new runner with the given config.
    #[must_use]
    pub fn new(config: CycleConfig) -> Self {
        let max_identical = config.max_identical_outputs;
        Self {
            config,
            novelty: NoveltyTracker::new(max_identical),
            cycles_run: 0,
            proposals_generated: 0,
            cycles_suspended: 0,
            learned: None,
        }
    }

    /// Attach a LearnedCycleStrategy for adaptive cycle selection (Phase 6).
    #[must_use]
    pub fn with_learned(mut self, learned: wm_core::LearnedCycleStrategy) -> Self {
        self.learned = Some(learned);
        self
    }

    /// Get a reference to the LearnedCycleStrategy, if attached.
    #[must_use]
    pub const fn learned(&self) -> Option<&wm_core::LearnedCycleStrategy> {
        self.learned.as_ref()
    }

    /// Get a mutable reference to the LearnedCycleStrategy, if attached.
    pub const fn learned_mut(&mut self) -> Option<&mut wm_core::LearnedCycleStrategy> {
        self.learned.as_mut()
    }

    /// Replace the LearnedCycleStrategy (used for persistence load).
    pub fn set_learned(&mut self, learned: wm_core::LearnedCycleStrategy) {
        self.learned = Some(learned);
    }

    /// Create with default config.
    #[must_use]
    #[allow(clippy::should_implement_trait)]
    pub fn default() -> Self {
        Self::new(CycleConfig::default())
    }

    /// Total cycles run.
    #[must_use]
    pub const fn cycles_run(&self) -> u64 {
        self.cycles_run
    }

    /// Total proposals generated across all cycles.
    #[must_use]
    pub const fn proposals_generated(&self) -> u64 {
        self.proposals_generated
    }

    /// Total cycles suspended due to non-novel output.
    #[must_use]
    pub const fn cycles_suspended(&self) -> u64 {
        self.cycles_suspended
    }

    /// Run a single cycle.
    pub fn run_cycle(&mut self, cycle: CycleType, ctx: &CycleContext) -> CycleResult {
        self.cycles_run += 1;

        // Harmony Vector gate — check health score
        if ctx.health_score < self.config.min_health_score {
            let result = CycleResult::new(cycle, CycleStatus::SkippedHealth);
            ctx.log_to_gnosis(&result);
            return result;
        }

        let start = Instant::now();
        let mut result = match cycle {
            CycleType::Connect => self.run_connect(ctx),
            CycleType::Compress => self.run_compress(ctx),
            CycleType::Emergence => self.run_emergence(ctx),
            CycleType::Prune => self.run_prune(ctx),
            CycleType::Improve => self.run_improve(ctx),
            CycleType::Redteam => self.run_redteam(ctx),
            CycleType::Sensorimotor => self.run_sensorimotor(ctx),
            CycleType::Research => self.run_research(ctx),
        };

        result.duration_ms = start.elapsed().as_millis() as u64;

        // Check time budget
        if start.elapsed() > self.config.time_budget {
            result.status = CycleStatus::SkippedTimeBudget;
        }

        // Novelty check — suspend on repeated identical output
        if result.status == CycleStatus::Completed || result.status == CycleStatus::NoProposals {
            let is_novel = self.novelty.check_and_update(cycle, &result);
            if !is_novel {
                result.status = CycleStatus::Suspended;
                self.cycles_suspended += 1;
            }
        }

        self.proposals_generated += result.proposals_generated as u64;

        // Log to Gnosis
        ctx.log_to_gnosis(&result);

        result
    }

    /// Run all cycles in sequence, using learned strategy if attached.
    pub fn run_all(&mut self, ctx: &CycleContext) -> Vec<CycleResult> {
        let cycles: Vec<CycleType> = if let Some(ref learned) = self.learned {
            let indices = learned.cycles_to_run();
            indices
                .iter()
                .filter_map(|&idx| CycleType::all().get(idx as usize).copied())
                .collect()
        } else {
            CycleType::all().to_vec()
        };

        let mut results = Vec::with_capacity(cycles.len());
        for cycle in cycles {
            let result = self.run_cycle(cycle, ctx);
            // Record cycle effectiveness for learned strategy
            if let Some(ref mut learned) = self.learned {
                let cycle_idx = CycleType::all()
                    .iter()
                    .position(|c| *c == cycle)
                    .unwrap_or(0) as u8;
                let usefulness = if result.proposals_generated > 0 {
                    0.8
                } else {
                    0.2
                };
                learned.record_cycle(
                    cycle_idx,
                    result.proposals_generated as u64,
                    usefulness,
                    result.duration_ms,
                );
            }
            results.push(result);
        }
        results
    }

    // ── Connect Cycle ──────────────────────────────────────────────────

    /// Connect cycle: find disconnected memories and propose typed associations.
    ///
    /// Scans all galaxies for memories with no incoming or outgoing
    /// associations. For each disconnected memory, uses semantic similarity
    /// (`find_similar`) to find nearby memories and proposes typed
    /// associations. Proposals require human review.
    fn run_connect(&self, ctx: &CycleContext) -> CycleResult {
        let mut result = CycleResult::new(CycleType::Connect, CycleStatus::Completed);

        let galaxy_mems = match ctx.scan_all_galaxies(self.config.memory_budget) {
            Ok(gm) => gm,
            Err(e) => {
                result.status = CycleStatus::Error;
                result.notes = format!("scan error: {e}");
                return result;
            }
        };

        let mut scanned = 0usize;
        let mut proposals = Vec::new();

        for (galaxy, mems) in &galaxy_mems {
            for mem in mems {
                scanned += 1;
                if proposals.len() >= self.config.max_proposals {
                    break;
                }

                // Only process disconnected memories
                if !ctx.is_disconnected(mem.metadata.id) {
                    continue;
                }

                // Find semantically similar memories in the same galaxy
                let similar = match ctx.store.find_similar(*galaxy, &mem.content, 5) {
                    Ok(s) => s,
                    Err(_) => continue,
                };

                for (target, distance) in similar {
                    if target.metadata.id == mem.metadata.id {
                        continue;
                    }

                    // Convert distance to similarity (0.0 = identical, 1.0 = far)
                    let similarity = 1.0 - distance.min(1.0);
                    if similarity < self.config.similarity_threshold {
                        continue;
                    }

                    // Determine link type from tag overlap
                    let link_type = infer_link_type(&mem.metadata.tags, &target.metadata.tags);

                    proposals.push(ConnectionProposal {
                        source_id: mem.metadata.id.to_string(),
                        target_id: target.metadata.id.to_string(),
                        link_type: link_type.as_str().to_string(),
                        similarity,
                        source_galaxy: galaxy.db_name().to_string(),
                        target_galaxy: galaxy.db_name().to_string(),
                        reason: format!(
                            "Disconnected memory semantically similar to {} (sim={:.2})",
                            target.metadata.id, similarity
                        ),
                    });

                    if proposals.len() >= self.config.max_proposals {
                        break;
                    }
                }
            }
            if proposals.len() >= self.config.max_proposals {
                break;
            }
        }

        result.memories_scanned = scanned;
        result.proposals_generated = proposals.len();
        result.connections = proposals;
        if result.proposals_generated == 0 {
            result.status = CycleStatus::NoProposals;
            result.notes = "No disconnected memories found needing connections".into();
        } else {
            result.notes = format!(
                "Found {} connection proposals for disconnected memories",
                result.proposals_generated
            );
        }
        result
    }

    // ── Compress Cycle ─────────────────────────────────────────────────

    /// Compress cycle: find semantically overlapping memories and propose merges.
    ///
    /// Scans each galaxy for pairs of memories with high semantic similarity
    /// and significant content overlap. Proposes merging the lower-importance
    /// memory into the higher-importance one. Requires human review.
    fn run_compress(&self, ctx: &CycleContext) -> CycleResult {
        let mut result = CycleResult::new(CycleType::Compress, CycleStatus::Completed);

        let galaxy_mems = match ctx.scan_all_galaxies(self.config.memory_budget) {
            Ok(gm) => gm,
            Err(e) => {
                result.status = CycleStatus::Error;
                result.notes = format!("scan error: {e}");
                return result;
            }
        };

        let mut scanned = 0usize;
        let mut proposals = Vec::new();
        let mut seen_pairs: HashSet<(uuid::Uuid, uuid::Uuid)> = HashSet::new();

        for (galaxy, mems) in &galaxy_mems {
            // Compare each memory with its semantic neighbors
            for mem in mems {
                scanned += 1;
                if proposals.len() >= self.config.max_proposals {
                    break;
                }

                let similar = match ctx.store.find_similar(*galaxy, &mem.content, 5) {
                    Ok(s) => s,
                    Err(_) => continue,
                };

                for (target, distance) in similar {
                    if target.metadata.id == mem.metadata.id {
                        continue;
                    }

                    let similarity = 1.0 - distance.min(1.0);
                    if similarity < self.config.similarity_threshold {
                        continue;
                    }

                    // Avoid duplicate pairs (A→B and B→A)
                    let pair = if mem.metadata.id < target.metadata.id {
                        (mem.metadata.id, target.metadata.id)
                    } else {
                        (target.metadata.id, mem.metadata.id)
                    };
                    if !seen_pairs.insert(pair) {
                        continue;
                    }

                    // Content overlap via tag Jaccard
                    let content_overlap = tag_jaccard(&mem.metadata.tags, &target.metadata.tags);

                    // Primary = higher importance
                    let (primary, secondary) =
                        if mem.metadata.importance >= target.metadata.importance {
                            (mem, &target)
                        } else {
                            (&target, mem)
                        };

                    proposals.push(CompressionProposal {
                        primary_id: primary.metadata.id.to_string(),
                        secondary_id: secondary.metadata.id.to_string(),
                        galaxy: galaxy.db_name().to_string(),
                        similarity,
                        content_overlap,
                        reason: format!(
                            "High semantic overlap (sim={similarity:.2}, tag_overlap={content_overlap:.2}) — merge lower-importance into higher",
                        ),
                    });

                    if proposals.len() >= self.config.max_proposals {
                        break;
                    }
                }
            }
            if proposals.len() >= self.config.max_proposals {
                break;
            }
        }

        result.memories_scanned = scanned;
        result.proposals_generated = proposals.len();
        result.compressions = proposals;
        if result.proposals_generated == 0 {
            result.status = CycleStatus::NoProposals;
            result.notes = "No semantically overlapping memory pairs found".into();
        } else {
            result.notes = format!("Found {} compression proposals", result.proposals_generated);
        }
        result
    }

    // ── Emergence Cycle ────────────────────────────────────────────────

    /// Emergence cycle: detect tag/topic emergence patterns across memories.
    ///
    /// Scans all galaxies and aggregates tag frequencies. Tags that appear
    /// with frequency above the threshold are reported as emergence patterns.
    /// This cycle is logged but does not require human review (no destructive action).
    fn run_emergence(&self, ctx: &CycleContext) -> CycleResult {
        let mut result = CycleResult::new(CycleType::Emergence, CycleStatus::Completed);

        let galaxy_mems = match ctx.scan_all_galaxies(self.config.memory_budget) {
            Ok(gm) => gm,
            Err(e) => {
                result.status = CycleStatus::Error;
                result.notes = format!("scan error: {e}");
                return result;
            }
        };

        // Aggregate tag stats: tag → (count, total_importance, galaxies)
        let mut tag_stats: HashMap<String, (usize, f32, HashSet<String>)> = HashMap::new();
        let mut scanned = 0usize;

        for (galaxy, mems) in &galaxy_mems {
            for mem in mems {
                scanned += 1;
                for tag in &mem.metadata.tags {
                    let entry = tag_stats
                        .entry(tag.clone())
                        .or_insert_with(|| (0, 0.0, HashSet::new()));
                    entry.0 += 1;
                    entry.1 += mem.metadata.importance;
                    entry.2.insert(galaxy.db_name().to_string());
                }
            }
        }

        // Filter by minimum frequency and build patterns
        let mut patterns: Vec<EmergencePattern> = tag_stats
            .into_iter()
            .filter(|(_, (count, _, _))| *count >= self.config.emergence_min_frequency)
            .map(|(tag, (count, total_imp, galaxies))| EmergencePattern {
                tag,
                frequency: count,
                growth_rate: 0.0, // No historical baseline in this run
                avg_importance: if count > 0 {
                    total_imp / count as f32
                } else {
                    0.0
                },
                galaxies: galaxies.into_iter().collect(),
            })
            .collect();

        // Sort by frequency descending
        patterns.sort_by_key(|x| std::cmp::Reverse(x.frequency));
        patterns.truncate(self.config.max_proposals);

        // Create dynamic galaxies from top emergence patterns (Phase 6)
        let mut galaxies_created = 0u64;
        if let Some(registry) = ctx.dynamic_galaxies {
            if let Ok(mut dg) = registry.lock() {
                for pattern in &patterns {
                    let name = format!("Cluster: {}", pattern.tag);
                    let description = format!(
                        "Auto-created from emergence detection (freq={}, galaxies={})",
                        pattern.frequency,
                        pattern.galaxies.join(",")
                    );
                    let cluster_tags = vec![pattern.tag.clone()];
                    if dg
                        .try_create(&name, &description, cluster_tags, pattern.frequency)
                        .is_some()
                    {
                        galaxies_created += 1;
                    }
                }
            }
        }

        result.memories_scanned = scanned;
        result.proposals_generated = patterns.len();
        result.emergences = patterns;
        if result.proposals_generated == 0 {
            result.status = CycleStatus::NoProposals;
            result.notes = "No emerging tag patterns detected".into();
        } else if galaxies_created > 0 {
            result.notes = format!(
                "Detected {} emerging tag patterns, created {} dynamic galaxies",
                result.proposals_generated, galaxies_created
            );
        } else {
            result.notes = format!(
                "Detected {} emerging tag patterns",
                result.proposals_generated
            );
        }
        result
    }

    // ── Prune Cycle ────────────────────────────────────────────────────

    /// Prune cycle: identify memories ready for forgetting.
    ///
    /// Computes a composite retention score from importance, neuro_score,
    /// and access recency. Memories below the retention threshold are
    /// identified as prune candidates. High-importance memories require
    /// human review before any action is taken.
    fn run_prune(&self, ctx: &CycleContext) -> CycleResult {
        let mut result = CycleResult::new(CycleType::Prune, CycleStatus::Completed);

        let galaxy_mems = match ctx.scan_all_galaxies(self.config.memory_budget) {
            Ok(gm) => gm,
            Err(e) => {
                result.status = CycleStatus::Error;
                result.notes = format!("scan error: {e}");
                return result;
            }
        };

        let now = chrono::Utc::now();
        let mut scanned = 0usize;
        let mut candidates = Vec::new();

        for (galaxy, mems) in &galaxy_mems {
            for mem in mems {
                scanned += 1;
                if candidates.len() >= self.config.max_proposals {
                    break;
                }

                // Skip protected memories
                if mem.metadata.is_protected {
                    continue;
                }

                // Compute composite retention score
                let days_since_access =
                    ((now - mem.metadata.accessed_at).num_seconds() as f32) / 86_400.0;
                let recency_factor = 0.5_f32.powf(days_since_access / mem.metadata.half_life_days);
                let retention = mem.metadata.importance.mul_add(
                    0.4,
                    mem.metadata.neuro_score.mul_add(0.3, recency_factor * 0.3),
                );

                if retention < self.config.prune_retention_threshold {
                    let requires_review =
                        mem.metadata.importance >= self.config.prune_human_review_importance;

                    let action = if requires_review {
                        "human_review"
                    } else if retention < self.config.prune_retention_threshold * 0.5 {
                        "decay_aggressive"
                    } else {
                        "decay"
                    };

                    candidates.push(PruneCandidate {
                        memory_id: mem.metadata.id.to_string(),
                        galaxy: galaxy.db_name().to_string(),
                        importance: mem.metadata.importance,
                        neuro_score: mem.metadata.neuro_score,
                        retention_score: retention,
                        requires_human_review: requires_review,
                        recommended_action: action.into(),
                        reason: format!(
                            "Low retention score ({retention:.3}): importance={:.2}, neuro={:.2}, recency_factor={:.2}",
                            mem.metadata.importance,
                            mem.metadata.neuro_score,
                            recency_factor,
                        ),
                    });

                    if candidates.len() >= self.config.max_proposals {
                        break;
                    }
                }
            }
            if candidates.len() >= self.config.max_proposals {
                break;
            }
        }

        result.memories_scanned = scanned;
        result.proposals_generated = candidates.len();
        result.prunes = candidates;
        if result.proposals_generated == 0 {
            result.status = CycleStatus::NoProposals;
            result.notes = "No memories ready for pruning".into();
        } else {
            result.notes = format!("Identified {} prune candidates", result.proposals_generated);
        }
        result
    }

    // ── Improve Cycle (RSI Phase 2) ───────────────────────────────────

    /// Improve cycle: analyze friction entries and propose concrete improvements.
    ///
    /// Scans the Codex galaxy for memories tagged `rsi:friction`, groups them
    /// by category + target, and generates `ImprovementProposal`s for clusters
    /// with 2+ entries. This is the analysis phase of RSI — it proposes, humans
    /// dispose.
    ///
    /// Anti-circular-thinking: The signature includes target + category +
    /// pattern_count, so if the same friction pattern is reported repeatedly
    /// without new entries, the SpiralTracker suspends the cycle.
    fn run_improve(&self, ctx: &CycleContext) -> CycleResult {
        let mut result = CycleResult::new(CycleType::Improve, CycleStatus::Completed);

        // Scan Codex for friction entries
        let memories = match ctx.store.scan(Galaxy::Codex, self.config.memory_budget) {
            Ok(m) => m,
            Err(e) => {
                result.status = CycleStatus::Error;
                result.notes = format!("scan error: {e}");
                return result;
            }
        };

        // Filter to friction entries and extract metadata
        #[derive(Debug)]
        struct FrictionEntry {
            id: String,
            category: String,
            severity: String,
            target: String,
            content: String,
            brain_wave: String,
            confidence_band: String,
            effectiveness_quartile: String,
            duplicate_count: u64,
        }

        let mut friction_entries: Vec<FrictionEntry> = Vec::new();
        for mem in &memories {
            if !mem.metadata.tags.iter().any(|t| t == "rsi:friction") {
                continue;
            }
            let category = mem
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:category:"))
                .unwrap_or("unknown")
                .to_string();
            let severity = mem
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:severity:"))
                .unwrap_or("medium")
                .to_string();
            let target = mem
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:tool:"))
                .unwrap_or("system")
                .to_string();

            // Parse telemetry from JSON block in content (WS-1)
            let (brain_wave, confidence_band, effectiveness_quartile) = {
                let content = &mem.content;
                let json_start = content.find("```json\n");
                let json_end = content.rfind("\n```");
                if let (Some(start), Some(end)) = (json_start, json_end) {
                    let json_str = &content[start + 8..end];
                    match serde_json::from_str::<serde_json::Value>(json_str) {
                        Ok(v) => {
                            let bw = v
                                .get("brain_wave")
                                .and_then(|v| v.as_str())
                                .unwrap_or("Unknown")
                                .to_string();
                            let smc = v
                                .get("self_model_confidence")
                                .and_then(serde_json::Value::as_f64)
                                .unwrap_or(0.5);
                            let eff = v
                                .get("effectiveness")
                                .and_then(serde_json::Value::as_f64)
                                .unwrap_or(0.5);
                            let cb = if smc < 0.3 {
                                "low"
                            } else if smc < 0.7 {
                                "medium"
                            } else {
                                "high"
                            }
                            .to_string();
                            let eq = if eff < 0.25 {
                                "q1"
                            } else if eff < 0.5 {
                                "q2"
                            } else if eff < 0.75 {
                                "q3"
                            } else {
                                "q4"
                            }
                            .to_string();
                            (bw, cb, eq)
                        }
                        Err(_) => (
                            "Unknown".to_string(),
                            "unknown".to_string(),
                            "unknown".to_string(),
                        ),
                    }
                } else {
                    (
                        "Unknown".to_string(),
                        "unknown".to_string(),
                        "unknown".to_string(),
                    )
                }
            };

            // WS-2: Extract duplicate_count from tags
            let duplicate_count = mem
                .metadata
                .tags
                .iter()
                .find_map(|t| t.strip_prefix("rsi:dup:"))
                .and_then(|v| v.parse::<u64>().ok())
                .unwrap_or(1);

            friction_entries.push(FrictionEntry {
                id: mem.metadata.id.to_string(),
                category,
                severity,
                target,
                content: mem.content.clone(),
                brain_wave,
                confidence_band,
                effectiveness_quartile,
                duplicate_count,
            });
        }

        let scanned = friction_entries.len();
        if scanned == 0 {
            result.memories_scanned = 0;
            result.status = CycleStatus::NoProposals;
            result.notes = "No friction entries found. Use friction.log to record issues.".into();
            return result;
        }

        // Group by (category, target) to find patterns
        let mut groups: HashMap<(String, String), Vec<&FrictionEntry>> = HashMap::new();
        for entry in &friction_entries {
            groups
                .entry((entry.category.clone(), entry.target.clone()))
                .or_default()
                .push(entry);
        }

        // Group by telemetry dimensions (WS-1: brain_wave, confidence_band, effectiveness_quartile)
        let mut by_brain_wave: HashMap<String, usize> = HashMap::new();
        let mut by_confidence_band: HashMap<String, usize> = HashMap::new();
        let mut by_effectiveness_quartile: HashMap<String, usize> = HashMap::new();
        for entry in &friction_entries {
            *by_brain_wave.entry(entry.brain_wave.clone()).or_default() += 1;
            *by_confidence_band
                .entry(entry.confidence_band.clone())
                .or_default() += 1;
            *by_effectiveness_quartile
                .entry(entry.effectiveness_quartile.clone())
                .or_default() += 1;
        }

        // Generate proposals for groups with 2+ entries (pattern detected)
        // WS-2: Weight by duplicate_count — higher dup count = higher pattern strength
        // WS-4: Skip proposals with signatures matching existing active proposals
        let existing_signatures: std::collections::HashSet<String> = {
            let mut sigs = std::collections::HashSet::new();
            for mem in &memories {
                if mem.metadata.tags.iter().any(|t| t == "rsi:proposal:active") {
                    if let Some(sig) = mem
                        .metadata
                        .tags
                        .iter()
                        .find_map(|t| t.strip_prefix("rsi:proposal:sig:"))
                    {
                        sigs.insert(sig.to_string());
                    }
                }
            }
            sigs
        };

        let mut proposals = Vec::new();
        for ((category, target), entries) in &groups {
            let weighted_count: u64 = entries.iter().map(|e| e.duplicate_count).sum();
            if entries.len() < 2 && weighted_count < 3 {
                continue;
            }
            if proposals.len() >= self.config.max_proposals {
                break;
            }

            // Determine highest severity in the group
            let max_severity = entries
                .iter()
                .map(|e| match e.severity.as_str() {
                    "high" => 3,
                    "medium" => 2,
                    _ => 1,
                })
                .max()
                .unwrap_or(2);
            let severity_str = match max_severity {
                3 => "high",
                2 => "medium",
                _ => "low",
            };

            // Build problem description from first entry's content
            let problem = entries
                .first()
                .map(|e| e.content.chars().take(200).collect::<String>())
                .unwrap_or_default();

            // Generate recommended action based on category
            let action = match category.as_str() {
                "error" => format!(
                    "Fix error handling in {}: {} entries report failures. Add error recovery or improve input validation.",
                    target,
                    entries.len()
                ),
                "performance" => format!(
                    "Optimize {}: {} entries report slowness. Profile and optimize hot paths or add caching.",
                    target,
                    entries.len()
                ),
                "ux" => format!(
                    "Improve UX of {}: {} entries report confusion. Add better error messages, documentation, or simplify the interface.",
                    target,
                    entries.len()
                ),
                "missing_feature" => format!(
                    "Add missing feature to {}: {} entries request functionality not currently available.",
                    target,
                    entries.len()
                ),
                "confusing" => format!(
                    "Clarify {}: {} entries report confusing behavior. Add documentation or improve output format.",
                    target,
                    entries.len()
                ),
                _ => format!(
                    "Investigate {}: {} friction entries in category '{}'.",
                    target,
                    entries.len(),
                    category
                ),
            };

            // WS-4: Skip if an active proposal with the same signature already exists
            let signature = format!("{category}:{target}:{severity_str}");
            if existing_signatures.contains(&signature) {
                continue;
            }

            proposals.push(ImprovementProposal {
                source_friction_ids: entries.iter().map(|e| e.id.clone()).collect(),
                category: category.clone(),
                severity: severity_str.to_string(),
                target: target.clone(),
                problem,
                recommended_action: action,
                pattern_count: weighted_count as usize,
            });
        }

        // If no patterns (2+), generate single-entry proposals for high-severity items
        if proposals.is_empty() {
            for entry in &friction_entries {
                if proposals.len() >= self.config.max_proposals {
                    break;
                }
                if entry.severity != "high" {
                    continue;
                }
                proposals.push(ImprovementProposal {
                    source_friction_ids: vec![entry.id.clone()],
                    category: entry.category.clone(),
                    severity: entry.severity.clone(),
                    target: entry.target.clone(),
                    problem: entry.content.chars().take(200).collect(),
                    recommended_action: format!(
                        "Address high-severity friction in {} ({}): investigate and fix.",
                        entry.target, entry.category
                    ),
                    pattern_count: 1,
                });
            }
        }

        result.memories_scanned = scanned;
        result.proposals_generated = proposals.len();
        result.improvements = proposals;
        if result.proposals_generated == 0 {
            result.status = CycleStatus::NoProposals;
            result.notes = format!(
                "Scanned {scanned} friction entries but no patterns (2+) or high-severity items found. \
                 Dimensions — brain_wave: {by_brain_wave:?}, confidence: {by_confidence_band:?}, effectiveness: {by_effectiveness_quartile:?}"
            );
        } else {
            result.notes = format!(
                "Generated {} improvement proposals from {scanned} friction entries. \
                 Dimensions — brain_wave: {by_brain_wave:?}, confidence: {by_confidence_band:?}, effectiveness: {by_effectiveness_quartile:?}",
                result.proposals_generated,
            );
        }
        result
    }

    // ── Redteam Cycle (RSI Phase 3) ───────────────────────────────────

    /// Redteam cycle: generate adversarial test proposals against v4's own systems.
    ///
    /// This cycle produces a static set of adversarial test proposals targeting
    /// v4's governance, karma, mandala, dispatch, and spiral tracker systems.
    /// The proposals are generated deterministically from a catalog of known
    /// attack vectors, ensuring the SpiralTracker can detect when no new
    /// vectors are found and suspend the cycle.
    ///
    /// Anti-circular-thinking: The signature includes target_system + attack_vector,
    /// so the cycle suspends when the same vectors are proposed repeatedly.
    /// New vectors must be added to the catalog for the cycle to produce novel output.
    fn run_redteam(&self, ctx: &CycleContext) -> CycleResult {
        let mut result = CycleResult::new(CycleType::Redteam, CycleStatus::Completed);

        // Check for friction entries that inform red-team targets
        let memories = match ctx.store.scan(Galaxy::Codex, self.config.memory_budget) {
            Ok(m) => m,
            Err(e) => {
                result.status = CycleStatus::Error;
                result.notes = format!("scan error: {e}");
                return result;
            }
        };

        let friction_count = memories
            .iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "rsi:friction"))
            .count();

        // Static catalog of adversarial test vectors
        // Each entry: (target_system, attack_vector, expected_behavior, test_pseudocode, risk_level, existing_coverage, recommended_fix)
        let catalog: &[(&str, &str, &str, &str, &str, bool, &str)] = &[
            (
                "governance",
                "Tool declares false effects (Satya violation)",
                "DharmaGate should detect mismatch and record karma debt",
                "let tool = LyingTool::new().await; let result = pipeline.dispatch(tool); assert!(result.karma_debt > 0);",
                "high",
                true,
                "Existing redteam tests cover this. Monitor for regressions.",
            ),
            (
                "governance",
                "Destructive tool in strict Ahimsa mode",
                "DharmaGate should block the action entirely",
                "let tool = DestructiveTool::new().await; let result = pipeline.dispatch(tool); assert!(result.blocked);",
                "critical",
                true,
                "Existing redteam tests cover this. Monitor for regressions.",
            ),
            (
                "karma",
                "Direct chain tamper — modify chain head without recording",
                "KarmaLedger should detect hash mismatch on next record",
                "tamper_chain_head(&ledger); let result = ledger.record(...); assert!(result.is_err());",
                "critical",
                true,
                "Existing redteam tests cover this. Monitor for regressions.",
            ),
            (
                "karma",
                "Concurrent record insertion race condition",
                "Chain should maintain integrity under concurrent access",
                "let handles: Vec<_> = (0..8).map(|i| thread::spawn(move || ledger.record(...))).collect(); verify_chain_integrity(&ledger);",
                "high",
                true,
                "Fixed in audit: single Mutex<ChainState>. Monitor for regressions.",
            ),
            (
                "mandala",
                "Cross-compartment memory access without authorization",
                "MandalaManager should deny access between compartments",
                "let mandala = MandalaManager::new(); mandala.open_compartment(Research); mandala.open_compartment(Production); research.store.put(mem); assert!(production.store.get(mem.id).is_none());",
                "high",
                true,
                "Covered by compartments_are_isolated test in wm-memory/src/mandala.rs. Monitor for regressions.",
            ),
            (
                "dispatch",
                "Rate limiter bypass via rapid tool name changes",
                "RateLimiter should track by tool name independently",
                "let tool1 = Tool::new(\"a\"); let tool2 = Tool::new(\"b\"); dispatch_rapidly(tool1, tool2); verify_both_rate_limited();",
                "medium",
                true,
                "Existing redteam tests cover per-tool rate limiting.",
            ),
            (
                "dispatch",
                "Circuit breaker does not trip under sustained failures",
                "CircuitBreaker should open after threshold failures",
                "let tool = FailingTool::new(); for _ in 0..threshold+1 { dispatch(tool); } assert!(breaker.is_open(\"failing\"));",
                "medium",
                true,
                "Existing tests cover circuit breaker tracking.",
            ),
            (
                "spiral",
                "Circular thinking loop not detected",
                "SpiralTracker should suspend after max_identical_outputs",
                "let tracker = SpiralTracker::default(); for _ in 0..max+1 { tracker.check_and_update(cycle, &same_result); } assert!(tracker.should_suspend(cycle));",
                "high",
                true,
                "Existing redteam tests cover circular thinking detection.",
            ),
            (
                "spiral",
                "Redteam cycle itself becomes circular",
                "SpiralTracker should suspend redteam.scan on repeated identical output",
                "run redteam.scan twice with same catalog; assert second run returns Suspended",
                "medium",
                true,
                "Covered by redteam_cycle_suspends_on_repeated_output test in wm-consciousness/src/autonomous.rs.",
            ),
            (
                "memory",
                "Memory poisoning via high-trust source injection",
                "Memories from untrusted sources should have low source_trust and be rejected by validator",
                "let mem = Memory::new(galaxy, content).with_source(\"attacker\", 0.3); let verdict = validator.validate(&mem); assert!(matches!(verdict, RejectLowTrust));",
                "medium",
                true,
                "Covered by reject_low_trust test in wm-memory/src/validator.rs. Monitor for regressions.",
            ),
            (
                "mcp",
                "Malicious tool name with path traversal characters bypasses validation",
                "validate_tool_call_params should reject tool names with ../ or special chars",
                "let params = json!({\"name\": \"../../etc/passwd\", \"arguments\": {}}); let result = validate_tool_call_params(&params); assert!(matches!(result, Invalid(_)));",
                "high",
                true,
                "Covered by is_tool_name_valid in wm-core/src/security.rs and input_validation.rs tests.",
            ),
            (
                "mcp",
                "Oversized params object causes memory exhaustion",
                "validate_request should reject params exceeding MAX_PARAMS_SIZE (64KB)",
                "let huge = \"x\".repeat(100_000); let params = json!({\"data\": huge}); let result = validate_request(&json!({\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":params})); assert!(matches!(result, Invalid(_)));",
                "medium",
                true,
                "Covered by validate_request size check in wm-mcp/src/input_validation.rs.",
            ),
            (
                "association",
                "Association graph poisoning — create circular links to inflate importance",
                "AssociationStore should detect or limit circular reference chains",
                "let a = Memory::new(galaxy, \"a\"); let b = Memory::new(galaxy, \"b\"); assoc.put(env, &Association::new(a.id, b.id, Related, 1.0)); assoc.put(env, &Association::new(b.id, a.id, Related, 1.0)); // circular",
                "medium",
                true,
                "Covered by find_cycles tests in wm-memory/src/associations.rs. AssociationStore::find_cycles detects bidirectional links.",
            ),
            (
                "bicameral",
                "Complexity classifier gamed by prompt padding to force cloud tier",
                "InferenceRouter should detect token-padding attacks and cap tier escalation",
                "let prompt = \"simple question \".repeat(500); let assessment = classifier.classify(&prompt, None, false, false); assert!(!assessment.requires_cloud(), \"padded prompt should not force cloud\");",
                "medium",
                true,
                "Covered by classify_padding_does_not_force_cloud test in wm-bicameral/src/router.rs. ComplexityClassifier detects low unique-to-total word ratio and caps effective word count.",
            ),
            (
                "resonance",
                "Bus spam — rapid event emission causes cascade amplification",
                "GanYingBus should rate-limit emissions and cap cascade depth",
                "let mut bus = GanYingBus::default(); for _ in 0..1000 { bus.emit(ToolDispatchStart, \"attacker\", json!({})); } assert!(bus.events_emitted() < 1000 || bus.cascade_events() < MAX_CASCADE_DEPTH as u64 * 1000);",
                "medium",
                true,
                "MAX_CASCADE_DEPTH=5 and cascade events have cascade:false. Covered by cascade_depth_capped test.",
            ),
            (
                "timescale",
                "Hook registration on wrong tier causes priority inversion",
                "TimescaleBus should enforce tier ordering and reject hooks on inactive tiers",
                "let mut bus = TimescaleBus::default(); bus.register(Tier::Delta, \"fast_hook\", || {}); // Delta only runs heartbeat, fast hook shouldn't execute assert_eq!(bus.tick_tier(Tier::Delta).0, 0); // or hook should be rejected",
                "low",
                true,
                "Covered by inactive_tier_hooks_skipped_in_tick_all and delta_brain_wave_only_evolutionary_active tests in wm-timescale/src/bus.rs. Brain-wave gating prevents hooks on inactive tiers from executing.",
            ),
            (
                "sangha",
                "Resource lock DoS — peer acquires all locks and never releases",
                "ResourceLockManager should enforce per-peer lock limits and auto-expire",
                "let mut mgr = ResourceLockManager::new(60); for i in 0..100 { mgr.acquire(&format(\"resource-{i}\"), \"greedy-peer\"); } assert!(mgr.locks_by_peer(\"greedy-peer\").len() < 100, \"should enforce per-peer limit\");",
                "medium",
                true,
                "Covered by per_peer_lock_limit_enforced and related tests in wm-sangha/src/lock.rs. ResourceLockManager::with_peer_limit enforces max_locks_per_peer.",
            ),
            (
                "governance",
                "Policy engine runtime update bypasses Dharma rules",
                "PolicyEngine should validate new rules against existing Dharma constraints",
                "let mut policy = PolicyEngine::default(); policy.add_rule(\"allow_all_destructive\", Rule { effect: Allow, .. }); assert!(policy.validate().is_err(), \"rule contradicting Ahimsa should be rejected\");",
                "high",
                true,
                "Covered by policy_rejects_ahimsa_contradiction and related tests in wm-governance/src/policy.rs. PolicyEngine::update and add_rule validate against Ahimsa constraints via PolicyUpdateError.",
            ),
            (
                "homeostasis",
                "Anomaly detector threshold manipulation via poisoned metrics",
                "AnomalyDetector should validate metric ranges and reject out-of-bounds values",
                "let mut detector = AnomalyDetector::new(); detector.record(\"cpu\", -100.0); // impossible value detector.record(\"cpu\", f32::MAX); // extreme value assert!(detector.z_score(\"cpu\").abs() < 10.0, \"should clamp or reject impossible metrics\");",
                "medium",
                true,
                "Covered by impossible_metrics_clamped_* tests in wm-substrate/src/anomaly.rs. AnomalyDetector::check clamps metric values to valid ranges via clamp_metric function before computing z-scores.",
            ),
            (
                "selfmodel",
                "Forecast manipulation via poisoned historical data",
                "SelfModel forecast should detect and reject statistically impossible inputs",
                "let mut model = SelfModel::default(); for _ in 0..100 { model.record_confidence(1.0); } // all max model.record_confidence(0.0); // sudden drop let forecast = model.forecast(); assert!(forecast.confidence > 0.0, \"should smooth over single anomaly\");",
                "low",
                true,
                "Covered by forecast_outlier_does_not_dominate and forecast_extreme_outlier_clamped tests in wm-selfmodel/src/forecast.rs. ForecastEngine::forecast uses clamp_outliers (median+MAD) to prevent extreme spikes from dominating predictions.",
            ),
            (
                "memory",
                "Embedder SSRF — WM_EMBEDDER_ENDPOINT points to internal metadata service",
                "EmbedderConfig::from_env should validate endpoint URL and reject non-HTTP schemes and cloud metadata endpoints",
                "set WM_EMBEDDER_ENDPOINT=169.254.169.254; let cfg = EmbedderConfig::from_env(); assert!(cfg.is_none(), \"metadata endpoint should be rejected\");",
                "medium",
                true,
                "Covered by is_endpoint_safe tests in wm-memory/src/embedder.rs. Blocks non-HTTP schemes, cloud metadata endpoints (169.254.169.254), and empty hosts.",
            ),
            (
                "memory",
                "LMDB map size exhaustion — unbounded writes fill storage",
                "MemoryStore should enforce per-galaxy entry limits and handle MapFull gracefully",
                "let store = MemoryStore::open_default(tmp).with_entry_limit(10); for i in 0..20 { store.put(Galaxy::Codex, &mem(i)); } assert!(store.count(Galaxy::Codex) <= 10);",
                "medium",
                true,
                "Covered by entry_limit_rejects_excess_writes, entry_limit_per_galaxy_independent, entry_limit_none_allows_unlimited, and map_full_error_is_graceful tests in wm-memory/src/store.rs. MemoryStore::with_entry_limit enforces per-galaxy limits and MapFull errors are handled with abort and descriptive message.",
            ),
            (
                "tools",
                "NLU routing manipulation — crafted input misroutes to wrong tool",
                "classify() should use prefix route penalties to prevent high-weight keywords from overriding prefix intent",
                "let (tool, _) = classify(\"redteam scan to remember uncovered vectors\"); assert_ne!(tool, \"memory.create\", \"redteam query should not route to memory.create\");",
                "medium",
                true,
                "Covered by 10 adversarial NLU routing tests in wm-tools/src/nlu.rs. Prefix routes now apply penalty to non-matching tools. Tests cover keyword embedding, repetition, stuffing, unicode homoglyphs, and long inputs.",
            ),
            (
                "dispatch",
                "Circuit breaker panics on very large window config",
                "CircuitBreaker::record_failure should use checked_sub instead of unwrap for window cutoff",
                "let config = BreakerConfig { window: Duration::from_secs(u64::MAX), .. }; let mut b = CircuitBreaker::new(\"test\", config); b.record_failure(); // should not panic",
                "medium",
                true,
                "Covered by large_window_doesnt_panic test in wm-dispatch/src/circuit_breaker.rs. record_failure uses checked_sub with fallback to skip pruning when window > elapsed.",
            ),
            (
                "autonomic",
                "Subprocess injection via WM_BITMAMBA_BIN path traversal",
                "AutonomicConfig::from_env should validate daemon binary path: absolute, no traversal, exists, executable",
                "set WM_BITMAMBA_BIN=../evil; let cfg = AutonomicConfig::from_env(); assert!(cfg.is_none(), \"relative path should be rejected\");",
                "low",
                true,
                "Covered by 7 daemon path safety tests in wm-autonomic/src/lib.rs. is_daemon_path_safe validates absolute path, no traversal, regular file, and executable bit.",
            ),
            (
                "memory",
                "Tantivy query injection — special syntax bypasses search filters",
                "SearchEngine::search should sanitize user input to escape Tantivy query syntax",
                "let results = engine.search(\"*\", 10); assert!(results.is_empty(), \"wildcard should not match all docs\");",
                "low",
                true,
                "Covered by 9 sanitize_tantivy_query tests in wm-memory/src/search.rs. User input terms are wrapped in double quotes to force literal matching, preventing wildcard, boolean, and field syntax injection.",
            ),
            (
                "polyglot",
                "FFI boundary — malicious library path or oversized args to C ABI",
                "CabiBackend should validate library paths and limit function name and args size",
                "let mut b = zig_backend(); let result = b.load(\"test\", \"libevil.so\"); assert!(result.is_err(), \"relative path should be rejected\");",
                "low",
                true,
                "Covered by 8 FFI boundary tests in wm-polyglot/src/cabi.rs. is_library_path_safe validates paths, function names are length-checked, args JSON limited to 1MB, results limited to 10MB.",
            ),
            (
                "core",
                "Env var injection — malformed numeric or path env vars cause panics or traversal",
                "Security utilities should parse and clamp numeric env vars, and validate path env vars",
                "assert_eq!(parse_clamped_f32(\"NaN\", 0.0, 1.0, 0.5), Some(0.5)); assert!(!is_env_path_safe(\"../etc/passwd\"));",
                "low",
                true,
                "Covered by 13 env var validation tests in wm-core/src/security.rs. parse_clamped_f32 handles NaN/Infinity/invalid, parse_clamped_usize clamps to range, is_env_path_safe blocks traversal.",
            ),
        ];

        // Build proposals from catalog — include all vectors, but sort
        // uncovered and friction-matched ones first for prioritization.
        let friction_memories: Vec<_> = memories
            .iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "rsi:friction"))
            .collect();

        let mut proposals: Vec<(usize, RedteamProposal)> = Vec::new();
        for &(target_system, attack_vector, expected, pseudocode, risk, covered, fix) in catalog {
            // Priority: 0 = uncovered (highest), 1 = friction-matched, 2 = covered & no friction match
            let friction_matched = friction_memories
                .iter()
                .any(|m| m.content.to_lowercase().contains(target_system));
            let priority = if !covered {
                0
            } else if friction_matched {
                1
            } else {
                2
            };

            proposals.push((
                priority,
                RedteamProposal {
                    target_system: target_system.to_string(),
                    attack_vector: attack_vector.to_string(),
                    expected_behavior: expected.to_string(),
                    test_pseudocode: pseudocode.to_string(),
                    risk_level: risk.to_string(),
                    existing_coverage: covered,
                    recommended_fix: fix.to_string(),
                },
            ));
        }

        // Sort by priority (uncovered first, then friction-matched, then rest)
        proposals.sort_by_key(|(p, _)| *p);

        // ── D2: Merge manifest-derived proposals ──────────────────────
        // Read the redteam manifest and generate proposals for untested
        // attack surfaces. This keeps the redteam cycle useful without
        // manual catalog expansion.
        // ── D3: Enrich with actual test coverage by scanning source files ──
        if let Some(manifest) = crate::redteam_manifest::read_default_manifest() {
            let manifest = crate::redteam_manifest::enrich_with_coverage(manifest);
            let manifest_proposals = crate::redteam_manifest::manifest_to_proposals(&manifest);
            for mp in manifest_proposals {
                // Skip if the static catalog already covers this target+vector
                let already_present = proposals.iter().any(|(_, p)| {
                    p.target_system == mp.target_system && p.attack_vector == mp.attack_vector
                });
                if !already_present {
                    let priority = if mp.existing_coverage { 2 } else { 0 };
                    proposals.push((priority, mp));
                }
            }
        }

        // ── D4: Generate friction-based dynamic vectors ───────────────
        // Analyze friction entry contents and generate proposals for
        // crates that have reported issues.
        let friction_contents: Vec<String> = friction_memories
            .iter()
            .map(|m| m.content.clone())
            .collect();
        if let Some(manifest) = crate::redteam_manifest::read_default_manifest() {
            let friction_proposals =
                crate::redteam_manifest::friction_to_proposals(&friction_contents, Some(&manifest));
            for fp in friction_proposals {
                let already_present = proposals.iter().any(|(_, p)| {
                    p.target_system == fp.target_system && p.attack_vector == fp.attack_vector
                });
                if !already_present {
                    proposals.push((0, fp)); // Friction-discovered = highest priority
                }
            }
        }

        // Re-sort after merging manifest and friction proposals
        proposals.sort_by_key(|(p, _)| *p);
        let proposals: Vec<RedteamProposal> = proposals
            .into_iter()
            .take(self.config.max_proposals)
            .map(|(_, p)| p)
            .collect();

        result.memories_scanned = friction_count;
        result.proposals_generated = proposals.len();
        result.redteam = proposals;
        if result.proposals_generated == 0 {
            result.status = CycleStatus::NoProposals;
            result.notes = "No adversarial test vectors to propose.".into();
        } else {
            let uncovered = result
                .redteam
                .iter()
                .filter(|p| !p.existing_coverage)
                .count();
            result.notes = format!(
                "Generated {} adversarial test proposals ({} uncovered). {} friction entries analyzed.",
                result.proposals_generated, uncovered, friction_count
            );
        }
        result
    }

    // ── Sensorimotor Cycle (Embodiment) ────────────────────────────────

    /// Sensorimotor cycle: poll sensors, evaluate reflex rules, execute triggered
    /// actuator commands, and produce proposals documenting what was observed and
    /// what actions were taken.
    ///
    /// This cycle does not require human review — it logs sensor readings and
    /// reflex actions for observability but does not perform destructive operations
    /// beyond what the reflex rules themselves dictate (which are configured by the
    /// user via `reflex.add`).
    ///
    /// If no sensorimotor bus or reflex loop is attached to the context, the cycle
    /// returns `NoProposals` with an explanatory note.
    fn run_sensorimotor(&self, ctx: &CycleContext) -> CycleResult {
        let mut result = CycleResult::new(CycleType::Sensorimotor, CycleStatus::Completed);

        let (bus_ref, reflex_ref) = if let (Some(b), Some(r)) =
            (ctx.sensorimotor_bus, ctx.reflex_loop)
        {
            (b, r)
        } else {
            result.status = CycleStatus::NoProposals;
            result.notes = "No sensorimotor bus or reflex loop attached to cycle context".into();
            return result;
        };

        // Poll all sensors
        let readings = {
            let Ok(mut bus) = bus_ref.lock() else {
                result.status = CycleStatus::Error;
                result.notes = "Sensorimotor bus mutex poisoned".into();
                return result;
            };
            bus.poll_all()
        };

        let sensor_count = readings.len();
        if sensor_count == 0 {
            result.status = CycleStatus::NoProposals;
            result.notes = "No sensors registered on the sensorimotor bus".into();
            return result;
        }

        // Evaluate reflex rules against current readings
        let commands = {
            let Ok(mut reflex) = reflex_ref.lock() else {
                result.status = CycleStatus::Error;
                result.notes = "Reflex loop mutex poisoned".into();
                return result;
            };
            reflex.evaluate(&readings)
        };

        let reflex_count = commands.len();

        // Execute triggered commands
        let mut executed = 0usize;
        let mut errors = Vec::new();
        if !commands.is_empty() {
            let Ok(mut bus) = bus_ref.lock() else {
                result.status = CycleStatus::Error;
                result.notes = "Sensorimotor bus mutex poisoned during command execution".into();
                return result;
            };
            for cmd in &commands {
                match bus.send_command(cmd) {
                    Ok(()) => executed += 1,
                    Err(e) => errors.push(e),
                }
            }
        }

        // Build proposals: one per sensor reading, noting if a reflex was triggered
        let mut proposals = Vec::new();
        for reading in &readings {
            // Check if any command targets this sensor's associated actuator
            let triggered_cmd = commands.iter().find(|c| {
                // Reflex rules map sensor_id → actuator_id, so we check if any
                // command was triggered by this sensor's reading
                c.actuator_id.contains(&reading.sensor_id)
                    || reading.sensor_id.contains(&c.actuator_id)
            });

            proposals.push(SensorimotorProposal {
                sensor_id: reading.sensor_id.clone(),
                sensor_kind: reading.kind.as_str().to_string(),
                value: reading.value,
                reflex_triggered: triggered_cmd.is_some(),
                actuator_id: triggered_cmd.map(|c| c.actuator_id.clone()),
                command_value: triggered_cmd.map(|c| c.value),
            });
        }

        result.memories_scanned = sensor_count;
        result.proposals_generated = proposals.len();
        result.sensorimotor = proposals;
        result.notes = format!(
            "Polled {sensor_count} sensors, {reflex_count} reflexes triggered, {executed} commands executed{}",
            if errors.is_empty() {
                String::new()
            } else {
                format!(", {} errors", errors.len())
            }
        );
        result
    }

    // ── Research Cycle (Imagination Engine) ────────────────────────────

    /// Research cycle: identify open problems and generate hypotheses.
    ///
    /// Scans Codex and Research galaxies for:
    /// - Unresolved friction entries (tags containing "rsi:friction")
    /// - Questions (content containing "?")
    /// - Low-confidence memories (neuro_score < 0.3)
    ///
    /// For each open problem, uses the imagination engine (if attached) to
    /// generate candidate scenarios. Top hypotheses are stored as
    /// `MemoryType::Hypothesis` memories in the Research galaxy.
    ///
    /// If no imagination engine is attached, generates simple hypotheses
    /// from memory patterns alone (degraded mode).
    fn run_research(&self, ctx: &CycleContext) -> CycleResult {
        let mut result = CycleResult::new(CycleType::Research, CycleStatus::Completed);

        // Scan Codex and Research galaxies for open problems
        let codex_mems = ctx
            .store
            .scan(Galaxy::Codex, self.config.memory_budget)
            .unwrap_or_default();
        let research_mems = ctx
            .store
            .scan(Galaxy::Research, self.config.memory_budget)
            .unwrap_or_default();

        let mut scanned = 0usize;
        let mut open_problems: Vec<(String, Vec<String>)> = Vec::new();

        // Find friction entries (unresolved)
        for mem in &codex_mems {
            scanned += 1;
            if mem.metadata.tags.iter().any(|t| t.contains("rsi:friction")) {
                let is_resolved = mem.metadata.tags.iter().any(|t| t.contains("resolved"));
                if !is_resolved {
                    open_problems.push((
                        format!(
                            "Friction: {}",
                            mem.content.chars().take(200).collect::<String>()
                        ),
                        vec![mem.metadata.id.to_string()],
                    ));
                }
            }
        }

        // Find questions in research galaxy
        for mem in &research_mems {
            scanned += 1;
            if mem.content.contains('?') {
                open_problems.push((
                    format!(
                        "Question: {}",
                        mem.content.chars().take(200).collect::<String>()
                    ),
                    vec![mem.metadata.id.to_string()],
                ));
            }
        }

        // Find low-confidence memories
        for mem in &codex_mems {
            if mem.metadata.neuro_score < 0.3 && mem.metadata.importance > 0.5 {
                open_problems.push((
                    format!(
                        "Low-confidence important memory: {}",
                        mem.content.chars().take(200).collect::<String>()
                    ),
                    vec![mem.metadata.id.to_string()],
                ));
            }
        }

        if open_problems.is_empty() {
            result.status = CycleStatus::NoProposals;
            result.notes = "No open problems found for research".into();
            return result;
        }

        // Limit to max_proposals problems
        open_problems.truncate(self.config.max_proposals);

        let mut proposals = Vec::new();

        if let Some(engine) = ctx.imagination {
            // Full imagination mode: use ScenarioEngine to generate hypotheses
            for (problem, source_ids) in &open_problems {
                // Build a memory context from recent codex memories
                let memory_context: String = codex_mems
                    .iter()
                    .rev()
                    .take(10)
                    .map(|m| m.content.as_str())
                    .collect::<Vec<_>>()
                    .join(" ");

                let goal = "Resolve the open problem with a novel solution";
                let scenarios = engine.imagine(problem, goal, &memory_context);

                for scenario in scenarios.iter().take(3) {
                    let predicted_outcome = scenario.trajectory.last().map_or_else(
                        || "Outcome uncertain".to_string(),
                        |p| p.description.clone(),
                    );

                    let mut proposal = ResearchProposal {
                        problem: problem.clone(),
                        source_memory_ids: source_ids.clone(),
                        hypothesis: scenario.action.clone(),
                        predicted_outcome,
                        confidence: scenario.breakdown.as_ref().map_or(0.5, |b| b.confidence),
                        novelty: scenario.novelty,
                        score: scenario.score,
                        stored: false,
                    };

                    // Store top hypotheses as Hypothesis memories
                    if proposal.score > 0.5 {
                        let mut hyp_mem = Memory::new(
                            Galaxy::Research,
                            format!(
                                "Hypothesis: {} → Predicted: {} (score: {:.2}, confidence: {:.2})",
                                proposal.hypothesis,
                                proposal.predicted_outcome,
                                proposal.score,
                                proposal.confidence
                            ),
                        );
                        hyp_mem.metadata.memory_type = MemoryType::Hypothesis;
                        hyp_mem.metadata.tags =
                            vec!["hypothesis".into(), "research".into(), "imagination".into()];
                        hyp_mem.metadata.importance = proposal.score;
                        hyp_mem.metadata.novelty_score = proposal.novelty;
                        if ctx.store.put(Galaxy::Research, &hyp_mem).is_ok() {
                            proposal.stored = true;
                        }
                    }

                    proposals.push(proposal);
                }
            }
        } else {
            // Degraded mode: generate simple hypotheses from patterns
            for (problem, source_ids) in &open_problems {
                let hypothesis = format!(
                    "Investigate alternative approaches to: {}",
                    problem.chars().take(100).collect::<String>()
                );
                proposals.push(ResearchProposal {
                    problem: problem.clone(),
                    source_memory_ids: source_ids.clone(),
                    hypothesis,
                    predicted_outcome: "Further investigation needed".into(),
                    confidence: 0.3,
                    novelty: 0.5,
                    score: 0.3,
                    stored: false,
                });
            }
        }

        result.memories_scanned = scanned;
        result.proposals_generated = proposals.len();
        result.hypotheses = proposals;
        result.notes = format!(
            "Scanned {} memories, found {} open problems, generated {} hypotheses{}",
            scanned,
            open_problems.len(),
            result.hypotheses.len(),
            if ctx.imagination.is_some() {
                " (imagination engine active)"
            } else {
                " (degraded mode — no imagination engine)"
            }
        );
        result
    }
}

fn infer_link_type(tags_a: &[String], tags_b: &[String]) -> LinkType {
    let set_a: HashSet<&str> = tags_a.iter().map(String::as_str).collect();
    let set_b: HashSet<&str> = tags_b.iter().map(String::as_str).collect();
    let overlap = set_a.intersection(&set_b).count();
    let union = set_a.union(&set_b).count();
    let jaccard = if union > 0 {
        overlap as f32 / union as f32
    } else {
        0.0
    };

    if jaccard > 0.7 {
        LinkType::Extends
    } else {
        LinkType::Related
    }
}

/// Compute Jaccard similarity between two tag sets.
fn tag_jaccard(tags_a: &[String], tags_b: &[String]) -> f32 {
    let set_a: HashSet<&str> = tags_a.iter().map(String::as_str).collect();
    let set_b: HashSet<&str> = tags_b.iter().map(String::as_str).collect();
    let intersection = set_a.intersection(&set_b).count();
    let union = set_a.union(&set_b).count();
    if union > 0 {
        intersection as f32 / union as f32
    } else {
        0.0
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    use wm_memory::Association;

    fn setup() -> (tempfile::TempDir, MemoryStore, AssociationStore) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let assoc = AssociationStore::open(store.env()).unwrap();
        (tmp, store, assoc)
    }

    // ── CycleType tests ────────────────────────────────────────────────

    #[test]
    fn cycle_type_all_has_8() {
        assert_eq!(CycleType::all().len(), 8);
    }

    #[test]
    fn cycle_type_names() {
        assert_eq!(CycleType::Connect.name(), "consolidation.connect");
        assert_eq!(CycleType::Compress.name(), "consolidation.compress");
        assert_eq!(CycleType::Emergence.name(), "emergence.scan");
        assert_eq!(CycleType::Prune.name(), "retention.prune");
        assert_eq!(CycleType::Improve.name(), "improve.scan");
        assert_eq!(CycleType::Redteam.name(), "redteam.scan");
        assert_eq!(CycleType::Sensorimotor.name(), "sensorimotor.scan");
        assert_eq!(CycleType::Research.name(), "research.scan");
    }

    #[test]
    fn cycle_type_purposes_are_nonempty() {
        for c in CycleType::all() {
            assert!(!c.purpose().is_empty());
        }
    }

    #[test]
    fn emergence_does_not_require_human_review() {
        assert!(!CycleType::Emergence.requires_human_review());
        assert!(!CycleType::Sensorimotor.requires_human_review());
        assert!(CycleType::Connect.requires_human_review());
        assert!(CycleType::Compress.requires_human_review());
        assert!(CycleType::Prune.requires_human_review());
    }

    // ── Sensorimotor Cycle tests ──────────────────────────────────────

    #[test]
    fn sensorimotor_cycle_without_bus_returns_no_proposals() {
        let (_tmp, store, assoc) = setup();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Sensorimotor, &ctx);
        assert_eq!(result.status, CycleStatus::NoProposals);
        assert!(result.notes.contains("No sensorimotor bus"));
    }

    #[test]
    fn sensorimotor_cycle_with_bus_polls_sensors() {
        use wm_substrate::sensorimotor::{SensorKind, SensorimotorBus, StubSensor};

        let (_tmp, store, assoc) = setup();
        let mut bus = SensorimotorBus::new(100);
        bus.register_sensor(Box::new(StubSensor::new(
            "test_temp",
            SensorKind::Temperature,
            42.0,
        )));
        let bus = std::sync::Mutex::new(bus);
        let reflex = std::sync::Mutex::new(wm_substrate::sensorimotor::ReflexLoop::new());

        let ctx = CycleContext::new(&store, &assoc, 1.0).with_sensorimotor(&bus, &reflex);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Sensorimotor, &ctx);
        assert_eq!(result.status, CycleStatus::Completed);
        assert_eq!(result.memories_scanned, 1);
        assert_eq!(result.proposals_generated, 1);
        assert_eq!(result.sensorimotor[0].sensor_id, "test_temp");
        assert!(!result.sensorimotor[0].reflex_triggered);
    }

    // ── Config tests ───────────────────────────────────────────────────

    #[test]
    fn default_config_has_sensible_values() {
        let cfg = CycleConfig::default();
        assert!(cfg.min_health_score > 0.0 && cfg.min_health_score < 1.0);
        assert!(cfg.memory_budget > 0);
        assert!(cfg.max_proposals > 0);
        assert!(cfg.similarity_threshold > 0.5);
    }

    // ── Connect cycle tests ────────────────────────────────────────────

    #[test]
    fn connect_finds_disconnected_memories() {
        let (_tmp, store, assoc) = setup();

        // Create two semantically similar memories with no associations
        let mut mem1 = Memory::new(Galaxy::Codex, "Rust algorithm data structure".into());
        mem1.metadata.tags = vec!["rust".into(), "algorithm".into()];
        store.put_semantic(Galaxy::Codex, &mut mem1).unwrap();

        let mut mem2 = Memory::new(Galaxy::Codex, "Rust algorithm data method".into());
        mem2.metadata.tags = vec!["rust".into(), "algorithm".into()];
        store.put_semantic(Galaxy::Codex, &mut mem2).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Connect, &ctx);

        assert_eq!(result.cycle, CycleType::Connect);
        assert_eq!(result.status, CycleStatus::Completed);
        assert!(!result.connections.is_empty());
        assert!(result.connections[0].similarity > 0.0);
    }

    #[test]
    fn connect_skips_connected_memories() {
        let (_tmp, store, assoc) = setup();

        let mut mem1 = Memory::new(Galaxy::Codex, "Rust algorithm data".into());
        store.put_semantic(Galaxy::Codex, &mut mem1).unwrap();

        let mut mem2 = Memory::new(Galaxy::Codex, "Rust algorithm method".into());
        store.put_semantic(Galaxy::Codex, &mut mem2).unwrap();

        // Create an association so they're not disconnected
        let a = Association::new(mem1.metadata.id, mem2.metadata.id, LinkType::Related, 0.8);
        assoc.put(store.env(), &a).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Connect, &ctx);

        // Should not propose connections for already-connected memories
        assert_eq!(
            result.status,
            CycleStatus::NoProposals,
            "connected memories should not get proposals"
        );
    }

    #[test]
    fn connect_skips_on_low_health() {
        let (_tmp, store, assoc) = setup();

        let mut mem = Memory::new(Galaxy::Codex, "test memory".into());
        store.put_semantic(Galaxy::Codex, &mut mem).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.1); // Low health
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Connect, &ctx);

        assert_eq!(result.status, CycleStatus::SkippedHealth);
    }

    // ── Compress cycle tests ───────────────────────────────────────────

    #[test]
    fn compress_finds_overlapping_pairs() {
        let (_tmp, store, assoc) = setup();

        let mut mem1 = Memory::new(Galaxy::Codex, "algorithm data structure rust".into());
        mem1.metadata.importance = 0.8;
        mem1.metadata.tags = vec!["rust".into(), "algorithm".into()];
        store.put_semantic(Galaxy::Codex, &mut mem1).unwrap();

        let mut mem2 = Memory::new(Galaxy::Codex, "algorithm data method rust".into());
        mem2.metadata.importance = 0.3;
        mem2.metadata.tags = vec!["rust".into(), "algorithm".into()];
        store.put_semantic(Galaxy::Codex, &mut mem2).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Compress, &ctx);

        assert_eq!(result.status, CycleStatus::Completed);
        assert!(!result.compressions.is_empty());
        // Primary should be the higher-importance memory
        assert_eq!(
            result.compressions[0].primary_id,
            mem1.metadata.id.to_string()
        );
    }

    #[test]
    fn compress_empty_galaxy_returns_no_proposals() {
        let (_tmp, store, assoc) = setup();

        // No memories at all — compress should return no proposals
        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Compress, &ctx);

        assert_eq!(result.status, CycleStatus::NoProposals);
    }

    // ── Emergence cycle tests ──────────────────────────────────────────

    #[test]
    fn emergence_detects_frequent_tags() {
        let (_tmp, store, assoc) = setup();

        for i in 0..5 {
            let mut mem = Memory::new(Galaxy::Codex, format!("rust memory item {i}"));
            mem.metadata.tags = vec!["rust".into(), "memory".into()];
            store.put_semantic(Galaxy::Codex, &mut mem).unwrap();
        }

        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Emergence, &ctx);

        assert_eq!(result.status, CycleStatus::Completed);
        assert!(!result.emergences.is_empty());
        let rust_pattern = result.emergences.iter().find(|e| e.tag == "rust");
        assert!(rust_pattern.is_some());
        assert!(rust_pattern.unwrap().frequency >= 3);
    }

    #[test]
    fn emergence_filters_low_frequency_tags() {
        let (_tmp, store, assoc) = setup();

        let mut mem = Memory::new(Galaxy::Codex, "single tag memory".into());
        mem.metadata.tags = vec!["rare".into()];
        store.put_semantic(Galaxy::Codex, &mut mem).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Emergence, &ctx);

        // "rare" appears only once, below min_frequency=3
        assert_eq!(result.status, CycleStatus::NoProposals);
    }

    #[test]
    #[allow(clippy::significant_drop_tightening)]
    fn emergence_creates_dynamic_galaxies() {
        let (_tmp, store, assoc) = setup();

        for i in 0..15 {
            let mut mem = Memory::new(Galaxy::Codex, format!("rust memory item {i}"));
            mem.metadata.tags = vec!["rust".into(), "memory".into()];
            store.put_semantic(Galaxy::Codex, &mut mem).unwrap();
        }

        let dg_registry = std::sync::Mutex::new(DynamicGalaxyRegistry::with_config(5, 20, 0.1));
        let ctx = CycleContext::new(&store, &assoc, 0.9).with_dynamic_galaxies(&dg_registry);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Emergence, &ctx);

        assert_eq!(result.status, CycleStatus::Completed);
        assert!(!result.emergences.is_empty());

        // Dynamic galaxy should have been created for "rust" tag
        let (galaxy_count, rust_mem_count) = {
            let dg = dg_registry.lock().unwrap();
            let count = dg.galaxy_count();
            let all = dg.all();
            let rust_galaxy = all
                .iter()
                .find(|g| g.cluster_tags.contains(&"rust".to_string()));
            (count, rust_galaxy.map(|g| g.memory_count))
        };
        assert!(
            galaxy_count > 0,
            "DynamicGalaxyRegistry should have galaxies"
        );
        assert!(
            rust_mem_count.is_some(),
            "Should have a dynamic galaxy for 'rust' tag"
        );
        assert!(rust_mem_count.unwrap() >= 15);
    }

    #[test]
    fn emergence_without_dynamic_galaxies_works() {
        let (_tmp, store, assoc) = setup();

        for i in 0..5 {
            let mut mem = Memory::new(Galaxy::Codex, format!("test memory {i}"));
            mem.metadata.tags = vec!["test".into()];
            store.put_semantic(Galaxy::Codex, &mut mem).unwrap();
        }

        // No dynamic_galaxies attached — should still work fine
        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Emergence, &ctx);

        assert_eq!(result.status, CycleStatus::Completed);
        assert!(!result.emergences.is_empty());
    }

    // ── Prune cycle tests ──────────────────────────────────────────────

    #[test]
    fn prune_identifies_low_retention_memories() {
        let (_tmp, store, assoc) = setup();

        // Low importance, low neuro_score, old access time
        let mut low_mem = Memory::new(Galaxy::Codex, "unimportant old memory".into())
            .with_importance(0.05)
            .with_neuro_score(0.05);
        low_mem.metadata.accessed_at = chrono::Utc::now() - chrono::Duration::days(365);
        store.put(Galaxy::Codex, &low_mem).unwrap();

        // High importance — should not be a candidate
        let high_mem = Memory::new(Galaxy::Codex, "important recent memory".into())
            .with_importance(0.9)
            .with_neuro_score(0.8);
        store.put(Galaxy::Codex, &high_mem).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Prune, &ctx);

        assert_eq!(result.status, CycleStatus::Completed);
        assert!(!result.prunes.is_empty());
        let candidate = &result.prunes[0];
        assert!(candidate.retention_score < 0.2);
    }

    #[test]
    fn prune_skips_protected_memories() {
        let (_tmp, store, assoc) = setup();

        let mut mem = Memory::new(Galaxy::Codex, "protected memory".into())
            .with_importance(0.05)
            .with_neuro_score(0.05)
            .with_protection(true);
        mem.metadata.accessed_at = chrono::Utc::now() - chrono::Duration::days(365);
        store.put(Galaxy::Codex, &mem).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Prune, &ctx);

        assert_eq!(result.status, CycleStatus::NoProposals);
    }

    #[test]
    fn prune_high_importance_requires_human_review() {
        let (_tmp, store, assoc) = setup();

        // High importance but very old — retention might be low
        let mut mem = Memory::new(Galaxy::Codex, "important but old".into())
            .with_importance(0.75)
            .with_neuro_score(0.1);
        mem.metadata.accessed_at = chrono::Utc::now() - chrono::Duration::days(365);
        store.put(Galaxy::Codex, &mem).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Prune, &ctx);

        if !result.prunes.is_empty() {
            let candidate = &result.prunes[0];
            if candidate.importance >= 0.7 {
                assert!(candidate.requires_human_review);
            }
        }
    }

    // ── Novelty / suspension tests ─────────────────────────────────────

    #[test]
    fn suspension_after_repeated_identical_output() {
        let (_tmp, store, assoc) = setup();

        // Create memories so emergence has something to find
        for i in 0..5 {
            let mut mem = Memory::new(Galaxy::Codex, format!("rust test {i}"));
            mem.metadata.tags = vec!["rust".into()];
            store.put_semantic(Galaxy::Codex, &mut mem).unwrap();
        }

        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();

        // First run — should complete
        let r1 = runner.run_cycle(CycleType::Emergence, &ctx);
        assert_eq!(r1.status, CycleStatus::Completed);

        // Second run — same output, should still complete (count=1)
        let r2 = runner.run_cycle(CycleType::Emergence, &ctx);
        assert_eq!(r2.status, CycleStatus::Completed);

        // Third run — same output (count=2), still completes
        let r3 = runner.run_cycle(CycleType::Emergence, &ctx);
        assert_eq!(r3.status, CycleStatus::Completed);

        // Fourth run — count=3, should be suspended
        let r4 = runner.run_cycle(CycleType::Emergence, &ctx);
        assert_eq!(r4.status, CycleStatus::Suspended);
        assert_eq!(runner.cycles_suspended(), 1);
    }

    // ── Run all tests ──────────────────────────────────────────────────

    #[test]
    fn run_all_executes_all_eight_cycles() {
        let (_tmp, store, assoc) = setup();

        let mut mem = Memory::new(Galaxy::Codex, "test memory".into());
        mem.metadata.tags = vec!["test".into()];
        store.put_semantic(Galaxy::Codex, &mut mem).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let results = runner.run_all(&ctx);

        assert_eq!(results.len(), 8);
        assert_eq!(results[0].cycle, CycleType::Connect);
        assert_eq!(results[1].cycle, CycleType::Compress);
        assert_eq!(results[2].cycle, CycleType::Emergence);
        assert_eq!(results[3].cycle, CycleType::Prune);
        assert_eq!(results[4].cycle, CycleType::Improve);
        assert_eq!(results[5].cycle, CycleType::Redteam);
        assert_eq!(results[6].cycle, CycleType::Sensorimotor);
        assert_eq!(results[7].cycle, CycleType::Research);
    }

    // ── Gnosis logging test ────────────────────────────────────────────

    #[test]
    fn gnosis_log_written_to_substrate() {
        let (_tmp, store, assoc) = setup();

        let ctx = CycleContext::new(&store, &assoc, 0.9);
        let mut runner = AutonomousCycleRunner::default();
        let _ = runner.run_cycle(CycleType::Emergence, &ctx);

        // Check that a log entry was written to Substrate
        let logs = store.scan(Galaxy::Substrate, 100).unwrap();
        assert!(
            logs.iter()
                .any(|m| { m.metadata.tags.contains(&"autonomous".to_string()) }),
            "Gnosis log should be written to Substrate galaxy"
        );
    }

    // ── Helper function tests ──────────────────────────────────────────

    #[test]
    fn infer_link_type_high_overlap_returns_extends() {
        let tags_a = vec!["rust".into(), "memory".into(), "algorithm".into()];
        let tags_b = vec!["rust".into(), "memory".into(), "algorithm".into()];
        assert_eq!(infer_link_type(&tags_a, &tags_b), LinkType::Extends);
    }

    #[test]
    fn infer_link_type_low_overlap_returns_related() {
        let tags_a = vec!["rust".into()];
        let tags_b = vec!["python".into()];
        assert_eq!(infer_link_type(&tags_a, &tags_b), LinkType::Related);
    }

    #[test]
    fn tag_jaccard_identical_sets() {
        let tags = vec!["a".into(), "b".into(), "c".into()];
        assert!((tag_jaccard(&tags, &tags) - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn tag_jaccard_disjoint_sets() {
        let tags_a = vec!["a".into(), "b".into()];
        let tags_b = vec!["c".into(), "d".into()];
        assert!(tag_jaccard(&tags_a, &tags_b) < f32::EPSILON);
    }

    #[test]
    fn tag_jaccard_partial_overlap() {
        let tags_a = vec!["a".into(), "b".into()];
        let tags_b = vec!["b".into(), "c".into()];
        let j = tag_jaccard(&tags_a, &tags_b);
        assert!((j - 1.0 / 3.0).abs() < 0.01);
    }

    // ── Signature test ─────────────────────────────────────────────────

    #[test]
    fn signature_is_deterministic() {
        let r1 = CycleResult::new(CycleType::Connect, CycleStatus::Completed);
        let r2 = CycleResult::new(CycleType::Connect, CycleStatus::Completed);
        assert_eq!(r1.signature(), r2.signature());
    }

    #[test]
    fn signature_differs_for_different_proposals() {
        let mut r1 = CycleResult::new(CycleType::Connect, CycleStatus::Completed);
        r1.connections.push(ConnectionProposal {
            source_id: "a".into(),
            target_id: "b".into(),
            link_type: "related".into(),
            similarity: 0.9,
            source_galaxy: "codex".into(),
            target_galaxy: "codex".into(),
            reason: "test".into(),
        });

        let r2 = CycleResult::new(CycleType::Connect, CycleStatus::Completed);
        assert_ne!(r1.signature(), r2.signature());
    }

    // ── Improve Cycle (RSI Phase 2) tests ──────────────────────────────

    fn add_friction_entry(
        store: &MemoryStore,
        content: &str,
        severity: &str,
        category: &str,
        tool: &str,
    ) {
        let mut mem = Memory::new(Galaxy::Codex, content.to_string());
        mem.metadata.tags = vec![
            "rsi:friction".into(),
            format!("rsi:severity:{severity}"),
            format!("rsi:category:{category}"),
            format!("rsi:tool:{tool}"),
        ];
        store.put(Galaxy::Codex, &mem).unwrap();
    }

    #[test]
    fn improve_cycle_no_friction_returns_no_proposals() {
        let (_tmp, store, assoc) = setup();
        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Improve, &ctx);
        assert_eq!(result.status, CycleStatus::NoProposals);
        assert_eq!(result.proposals_generated, 0);
    }

    #[test]
    fn improve_cycle_detects_patterns() {
        let (_tmp, store, assoc) = setup();
        // Add 3 friction entries for the same tool/category (pattern)
        add_friction_entry(
            &store,
            "Tool A failed with error X",
            "high",
            "error",
            "tool_a",
        );
        add_friction_entry(
            &store,
            "Tool A failed with error Y",
            "medium",
            "error",
            "tool_a",
        );
        add_friction_entry(
            &store,
            "Tool A failed with error Z",
            "low",
            "error",
            "tool_a",
        );

        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Improve, &ctx);
        assert_eq!(result.status, CycleStatus::Completed);
        assert_eq!(result.proposals_generated, 1);
        assert_eq!(result.improvements[0].pattern_count, 3);
        assert_eq!(result.improvements[0].category, "error");
        assert_eq!(result.improvements[0].target, "tool_a");
        assert_eq!(result.improvements[0].severity, "high");
        assert!(!result.improvements[0].recommended_action.is_empty());
    }

    #[test]
    fn improve_cycle_single_high_severity_gets_proposal() {
        let (_tmp, store, assoc) = setup();
        add_friction_entry(&store, "Critical failure", "high", "error", "tool_b");

        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Improve, &ctx);
        assert_eq!(result.status, CycleStatus::Completed);
        assert_eq!(result.proposals_generated, 1);
        assert_eq!(result.improvements[0].pattern_count, 1);
        assert_eq!(result.improvements[0].severity, "high");
    }

    #[test]
    fn improve_cycle_single_low_severity_no_proposal() {
        let (_tmp, store, assoc) = setup();
        add_friction_entry(&store, "Minor issue", "low", "ux", "tool_c");

        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Improve, &ctx);
        assert_eq!(result.status, CycleStatus::NoProposals);
    }

    #[test]
    fn improve_cycle_groups_by_category_and_target() {
        let (_tmp, store, assoc) = setup();
        add_friction_entry(&store, "Error 1", "high", "error", "tool_a");
        add_friction_entry(&store, "Error 2", "medium", "error", "tool_a");
        add_friction_entry(&store, "Slow 1", "medium", "performance", "tool_a");
        add_friction_entry(&store, "Slow 2", "low", "performance", "tool_a");

        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Improve, &ctx);
        assert_eq!(result.status, CycleStatus::Completed);
        assert_eq!(result.proposals_generated, 2);
    }

    #[test]
    fn improve_cycle_signature_includes_target_and_count() {
        let mut r1 = CycleResult::new(CycleType::Improve, CycleStatus::Completed);
        r1.improvements.push(ImprovementProposal {
            source_friction_ids: vec!["a".into()],
            category: "error".into(),
            severity: "high".into(),
            target: "tool_a".into(),
            problem: "test".into(),
            recommended_action: "fix".into(),
            pattern_count: 3,
        });

        let mut r2 = CycleResult::new(CycleType::Improve, CycleStatus::Completed);
        r2.improvements.push(ImprovementProposal {
            source_friction_ids: vec!["b".into()],
            category: "error".into(),
            severity: "high".into(),
            target: "tool_b".into(),
            problem: "test".into(),
            recommended_action: "fix".into(),
            pattern_count: 3,
        });

        assert_ne!(r1.signature(), r2.signature());
    }

    #[test]
    fn improve_cycle_requires_human_review() {
        assert!(CycleType::Improve.requires_human_review());
    }

    #[test]
    fn improve_cycle_health_gate_works() {
        let (_tmp, store, assoc) = setup();
        add_friction_entry(&store, "Error", "high", "error", "tool_a");

        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 0.1); // Low health
        let result = runner.run_cycle(CycleType::Improve, &ctx);
        assert_eq!(result.status, CycleStatus::SkippedHealth);
    }

    #[test]
    fn improve_cycle_run_all_includes_improve() {
        let (_tmp, store, assoc) = setup();
        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let results = runner.run_all(&ctx);
        assert_eq!(results.len(), 8);
        assert_eq!(results[4].cycle, CycleType::Improve);
        assert_eq!(results[5].cycle, CycleType::Redteam);
        assert_eq!(results[6].cycle, CycleType::Sensorimotor);
        assert_eq!(results[7].cycle, CycleType::Research);
    }

    // ── Redteam Cycle (RSI Phase 3) tests ──────────────────────────────

    #[test]
    fn redteam_cycle_generates_proposals() {
        let (_tmp, store, assoc) = setup();
        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Redteam, &ctx);
        assert_eq!(result.status, CycleStatus::Completed);
        assert!(result.proposals_generated > 0);
        assert!(!result.redteam.is_empty());
    }

    #[test]
    fn redteam_cycle_includes_governance_vectors() {
        let (_tmp, store, assoc) = setup();
        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Redteam, &ctx);
        let governance_count = result
            .redteam
            .iter()
            .filter(|p| p.target_system == "governance")
            .count();
        assert!(governance_count >= 2);
    }

    #[test]
    fn redteam_cycle_includes_karma_vectors() {
        let (_tmp, store, assoc) = setup();
        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Redteam, &ctx);
        let karma_count = result
            .redteam
            .iter()
            .filter(|p| p.target_system == "karma")
            .count();
        assert!(karma_count >= 2);
    }

    #[test]
    fn redteam_cycle_identifies_uncovered_vectors() {
        let (_tmp, store, assoc) = setup();
        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Redteam, &ctx);
        // All 28 static catalog vectors are covered after the redteam hardening passes.
        // The manifest (D2) may add additional proposals for untested surfaces,
        // so we only verify that the static catalog vectors are all covered.
        assert!(!result.redteam.is_empty(), "Should produce proposals");

        // The static catalog vectors should all have existing_coverage=true.
        // Manifest-derived proposals for untested surfaces will have existing_coverage=false,
        // which is the intended behavior — the cycle surfaces untested attack surfaces.
        let covered = result
            .redteam
            .iter()
            .filter(|p| p.existing_coverage)
            .count();
        assert!(
            covered >= 28,
            "All 28 static catalog vectors should be covered (got {covered} covered)"
        );
    }

    #[test]
    fn redteam_cycle_requires_human_review() {
        assert!(CycleType::Redteam.requires_human_review());
    }

    #[test]
    fn redteam_cycle_health_gate_works() {
        let (_tmp, store, assoc) = setup();
        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 0.1);
        let result = runner.run_cycle(CycleType::Redteam, &ctx);
        assert_eq!(result.status, CycleStatus::SkippedHealth);
    }

    #[test]
    fn redteam_cycle_signature_is_deterministic() {
        let (_tmp, store, assoc) = setup();
        let runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let mut r1 = runner;
        let result1 = r1.run_cycle(CycleType::Redteam, &ctx);

        let runner2 = AutonomousCycleRunner::default();
        let ctx2 = CycleContext::new(&store, &assoc, 1.0);
        let mut r2 = runner2;
        let result2 = r2.run_cycle(CycleType::Redteam, &ctx2);

        assert_eq!(result1.signature(), result2.signature());
    }

    #[test]
    fn redteam_cycle_proposals_have_pseudocode() {
        let (_tmp, store, assoc) = setup();
        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Redteam, &ctx);
        for p in &result.redteam {
            assert!(!p.test_pseudocode.is_empty());
            assert!(!p.expected_behavior.is_empty());
            assert!(!p.recommended_fix.is_empty());
        }
    }

    #[test]
    fn redteam_cycle_prioritizes_friction_targets() {
        let (_tmp, store, assoc) = setup();
        // Add friction entry mentioning "mandala"
        add_friction_entry(
            &store,
            "Mandala isolation failed",
            "high",
            "error",
            "mandala",
        );

        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Redteam, &ctx);
        // Should include mandala vector since friction mentions it
        let has_mandala = result.redteam.iter().any(|p| p.target_system == "mandala");
        assert!(has_mandala);
    }

    #[test]
    fn redteam_cycle_suspends_on_repeated_output() {
        use crate::spiral::SpiralTracker;
        let (_tmp, store, assoc) = setup();
        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);

        // First run — should complete
        let result1 = runner.run_cycle(CycleType::Redteam, &ctx);
        let sig1 = result1.signature();
        assert_eq!(result1.status, CycleStatus::Completed);

        // Track with SpiralTracker
        let mut tracker = SpiralTracker::default();
        let (_, suspended1) = tracker.record(&result1);
        assert!(!suspended1, "First run should not be suspended");

        // Second run — same catalog, same friction → identical signature
        let result2 = runner.run_cycle(CycleType::Redteam, &ctx);
        let sig2 = result2.signature();
        assert_eq!(
            sig1, sig2,
            "Repeated runs should produce identical signatures"
        );

        let (_, suspended2) = tracker.record(&result2);
        assert!(
            !suspended2,
            "Second run should not yet be suspended (count=2)"
        );

        // Third run — still identical
        let result3 = runner.run_cycle(CycleType::Redteam, &ctx);
        let (_, suspended3) = tracker.record(&result3);
        assert!(
            !suspended3,
            "Third run should not yet be suspended (count=3)"
        );

        // Fourth run — should now be suspended (max_identical=3)
        let result4 = runner.run_cycle(CycleType::Redteam, &ctx);
        let (_, suspended4) = tracker.record(&result4);
        assert!(
            suspended4,
            "Fourth identical run should be suspended by SpiralTracker"
        );
        assert!(tracker.is_suspended(CycleType::Redteam));
    }

    #[test]
    fn redteam_cycle_marks_covered_vectors() {
        let (_tmp, store, assoc) = setup();
        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Redteam, &ctx);

        // Mandala and memory poisoning should be marked as covered
        let mandala = result.redteam.iter().find(|p| p.target_system == "mandala");
        assert!(mandala.is_some(), "Mandala vector should be in proposals");
        assert!(
            mandala.unwrap().existing_coverage,
            "Mandala should be marked as covered"
        );

        let memory = result.redteam.iter().find(|p| p.target_system == "memory");
        assert!(
            memory.is_some(),
            "Memory poisoning vector should be in proposals"
        );
        assert!(
            memory.unwrap().existing_coverage,
            "Memory poisoning should be marked as covered"
        );
    }

    #[test]
    fn redteam_cycle_includes_new_attack_vectors() {
        let (_tmp, store, assoc) = setup();
        let mut runner = AutonomousCycleRunner::default();
        let ctx = CycleContext::new(&store, &assoc, 1.0);
        let result = runner.run_cycle(CycleType::Redteam, &ctx);

        // Verify new vectors from expanded catalog are present
        let target_systems: Vec<&str> = result
            .redteam
            .iter()
            .map(|p| p.target_system.as_str())
            .collect();
        assert!(
            target_systems.contains(&"mcp"),
            "Should include MCP validation bypass vector"
        );
        assert!(
            target_systems.contains(&"association"),
            "Should include association poisoning vector"
        );
        assert!(
            target_systems.contains(&"bicameral"),
            "Should include bicameral desync vector"
        );
        assert!(
            target_systems.contains(&"resonance"),
            "Should include resonance bus spam vector"
        );
        assert!(
            target_systems.contains(&"timescale"),
            "Should include timescale hook injection vector"
        );
        assert!(
            target_systems.contains(&"sangha"),
            "Should include resource lock DoS vector"
        );
        assert!(
            target_systems.contains(&"homeostasis"),
            "Should include homeostasis hijack vector"
        );
        assert!(
            target_systems.contains(&"selfmodel"),
            "Should include selfmodel forecast manipulation vector"
        );
        assert!(
            target_systems.contains(&"autonomic"),
            "Should include autonomic subprocess injection vector"
        );
        assert!(
            target_systems.contains(&"polyglot"),
            "Should include polyglot FFI boundary vector"
        );
        assert!(
            target_systems.contains(&"tools"),
            "Should include NLU routing manipulation vector"
        );

        // Total should be at least 28 static catalog vectors.
        // The manifest (D2) adds additional proposals for untested attack surfaces,
        // so the total may exceed 28.
        assert!(
            result.redteam.len() >= 28,
            "Should have at least 28 static catalog vectors, got {}",
            result.redteam.len()
        );
    }

    // ── Research cycle tests ───────────────────────────────────────────

    #[test]
    fn research_cycle_no_open_problems() {
        let (tmp, store, assoc) = setup();
        let ctx = CycleContext::new(&store, &assoc, 0.8);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Research, &ctx);
        assert_eq!(result.status, CycleStatus::NoProposals);
        assert!(result.notes.contains("No open problems"));
        drop(tmp);
    }

    #[test]
    fn research_cycle_finds_friction_entries() {
        let (tmp, store, assoc) = setup();
        let mut mem = Memory::new(Galaxy::Codex, "Tool dispatch failed unexpectedly".into());
        mem.metadata.tags = vec!["rsi:friction".into(), "error".into()];
        mem.metadata.importance = 0.7;
        store.put(Galaxy::Codex, &mem).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.8);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Research, &ctx);
        assert_eq!(result.status, CycleStatus::Completed);
        assert!(!result.hypotheses.is_empty(), "should generate hypotheses");
        assert!(result.notes.contains("degraded mode"));
        drop(tmp);
    }

    #[test]
    fn research_cycle_finds_questions() {
        let (tmp, store, assoc) = setup();
        let mut mem = Memory::new(Galaxy::Research, "How can we optimize dispatch?".into());
        mem.metadata.tags = vec!["question".into()];
        store.put(Galaxy::Research, &mem).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.8);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Research, &ctx);
        assert_eq!(result.status, CycleStatus::Completed);
        assert!(!result.hypotheses.is_empty());
        assert!(result.hypotheses[0].problem.contains("Question"));
        drop(tmp);
    }

    #[test]
    fn research_cycle_skips_resolved_friction() {
        let (tmp, store, assoc) = setup();
        let mut mem = Memory::new(Galaxy::Codex, "Fixed issue".into());
        mem.metadata.tags = vec!["rsi:friction".into(), "resolved".into()];
        store.put(Galaxy::Codex, &mem).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.8);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Research, &ctx);
        assert_eq!(result.status, CycleStatus::NoProposals);
        drop(tmp);
    }

    #[test]
    fn research_cycle_with_imagination_engine() {
        let (tmp, store, assoc) = setup();
        let mut mem = Memory::new(Galaxy::Codex, "How to improve routing?".into());
        mem.metadata.tags = vec!["rsi:friction".into()];
        mem.metadata.importance = 0.6;
        store.put(Galaxy::Codex, &mem).unwrap();

        use std::sync::Arc;
        use wm_bicameral::{ScenarioEngine, ScenarioEvaluator, StubWorldModelHandler, WorldModel};
        let wm = WorldModel::new(
            Arc::new(StubWorldModelHandler::left()),
            Some(Arc::new(StubWorldModelHandler::right())),
        );
        let evaluator = ScenarioEvaluator::with_defaults();
        let engine = ScenarioEngine::with_defaults(wm, evaluator);

        let ctx = CycleContext::new(&store, &assoc, 0.8).with_imagination(&engine);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Research, &ctx);
        assert_eq!(result.status, CycleStatus::Completed);
        assert!(!result.hypotheses.is_empty());
        assert!(result.notes.contains("imagination engine active"));
        drop(tmp);
    }

    #[test]
    fn research_cycle_stores_high_score_hypotheses() {
        let (tmp, store, assoc) = setup();
        let mut mem = Memory::new(Galaxy::Codex, "Complex problem needing solution?".into());
        mem.metadata.tags = vec!["rsi:friction".into()];
        mem.metadata.importance = 0.8;
        store.put(Galaxy::Codex, &mem).unwrap();

        use std::sync::Arc;
        use wm_bicameral::{ScenarioEngine, ScenarioEvaluator, StubWorldModelHandler, WorldModel};
        let wm = WorldModel::new(
            Arc::new(StubWorldModelHandler::left()),
            Some(Arc::new(StubWorldModelHandler::right())),
        );
        let evaluator = ScenarioEvaluator::with_defaults();
        let engine = ScenarioEngine::with_defaults(wm, evaluator);

        let ctx = CycleContext::new(&store, &assoc, 0.8).with_imagination(&engine);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Research, &ctx);

        // Check if any hypotheses were stored
        let research_mems = store.scan(Galaxy::Research, 100).unwrap();
        let hyp_count = research_mems
            .iter()
            .filter(|m| m.metadata.memory_type == MemoryType::Hypothesis)
            .count();
        // Stub handlers produce moderate scores, so some may be stored
        if result.hypotheses.iter().any(|h| h.stored) {
            assert!(
                hyp_count > 0,
                "stored hypotheses should be in Research galaxy"
            );
        }
        drop(tmp);
    }

    #[test]
    fn research_cycle_low_health_skipped() {
        let (tmp, store, assoc) = setup();
        let ctx = CycleContext::new(&store, &assoc, 0.1); // Below min_health_score
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Research, &ctx);
        assert_eq!(result.status, CycleStatus::SkippedHealth);
        drop(tmp);
    }

    #[test]
    fn research_cycle_finds_low_confidence_memories() {
        let (tmp, store, assoc) = setup();
        let mut mem = Memory::new(Galaxy::Codex, "Important but uncertain data".into());
        mem.metadata.importance = 0.8;
        mem.metadata.neuro_score = 0.1;
        store.put(Galaxy::Codex, &mem).unwrap();

        let ctx = CycleContext::new(&store, &assoc, 0.8);
        let mut runner = AutonomousCycleRunner::default();
        let result = runner.run_cycle(CycleType::Research, &ctx);
        assert_eq!(result.status, CycleStatus::Completed);
        assert!(!result.hypotheses.is_empty());
        assert!(result.hypotheses[0].problem.contains("Low-confidence"));
        drop(tmp);
    }

    #[test]
    fn research_cycle_does_not_require_human_review() {
        assert!(!CycleType::Research.requires_human_review());
    }

    #[test]
    fn research_cycle_purpose_is_set() {
        let result = CycleResult::new(CycleType::Research, CycleStatus::Completed);
        assert!(result.purpose.contains("Imagination Engine"));
    }

    #[test]
    fn research_cycle_signature_includes_hypotheses() {
        let mut result = CycleResult::new(CycleType::Research, CycleStatus::Completed);
        result.hypotheses.push(ResearchProposal {
            problem: "test problem".into(),
            source_memory_ids: vec![],
            hypothesis: "test hypothesis".into(),
            predicted_outcome: "test outcome".into(),
            confidence: 0.7,
            novelty: 0.5,
            score: 0.6,
            stored: false,
        });
        let sig = result.signature();
        assert!(sig.contains("test problem"));
    }
}
