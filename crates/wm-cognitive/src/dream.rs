//! Dream cycle — 12-phase memory consolidation.
//!
//! Implements the dream cycle as a sequential runner triggered by
//! Theta brain-wave state. Each phase processes memories and
//! produces a result. Sleep consolidation writes important turns
//! to the codex galaxy.

use std::collections::HashMap;
use std::fmt::Write as _;
use std::time::{Duration, Instant};
use wm_core::{BrainWave, Galaxy, Result};
use wm_memory::{AssociationStore, Memory, MemoryStore, MemoryType};

use wm_bicameral::ScenarioEngine;

use crate::constellation::ConstellationDetector;
use crate::miner::AssociationMiner;
use crate::neural::{Neuromodulator, RippleReport, RippleTagger, SpreadingActivation};
use crate::retention::RetentionEngine;
use crate::strategy::StrategySynthesizer;

// ── Tier-ladder policy constants (S5 phase 2, MEMORY_TYPOLOGY_V8.md §6) ──
/// Days after which a `Working` memory is no longer the current-session
/// working set and the dream cycle ages it out to `Episodic`.
const WORKING_TTL_DAYS: f32 = 1.0;
/// Minimum combined reads (access_count + recall_count) before an
/// `Episodic` memory is promotion-eligible to `Semantic`.
const SEMANTIC_MIN_READS: u64 = 5;
/// Minimum importance for `Episodic → Semantic` promotion.
const SEMANTIC_MIN_IMPORTANCE: f32 = 0.7;
/// Maximum importance for decay-out to `Archival` (must also be past the
/// memory's own `half_life_days`).
const ARCHIVAL_MAX_IMPORTANCE: f32 = 0.3;

/// Validity-sweep knob (V8 Slice B, D1+D2). Off by default: true only on
/// exact `WM_VALIDITY_SWEEP=1` — the same exact-match shape as
/// `wm_memory::memory::validity_enforced`, so sleep stays byte-identical
/// until a session deliberately opts in.
#[must_use]
fn validity_sweep_enabled() -> bool {
    matches!(std::env::var("WM_VALIDITY_SWEEP"), Ok(v) if v == "1")
}

/// The 12 phases of the dream cycle.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DreamPhase {
    /// Triage — classify memories by importance and urgency
    Triage,
    /// Consolidation — merge related memories and resolve duplicates
    Consolidation,
    /// Serendipity — discover unexpected cross-galaxy associations
    Serendipity,
    /// Governance — apply Dharma rules and karma reconciliation
    Governance,
    /// Narrative — weave memories into coherent story arcs
    Narrative,
    /// Kaizen — incremental improvement of memory quality
    Kaizen,
    /// Oracle — generate predictions from consolidated patterns
    Oracle,
    /// Decay — apply mindful forgetting to low-significance memories
    Decay,
    /// Constellation — detect and form memory clusters
    Constellation,
    /// Prediction — forecast future memory needs
    Prediction,
    /// Enrichment — augment memories with external context
    Enrichment,
    /// Harmonize — balance galaxy weights and associations
    Harmonize,
}

impl DreamPhase {
    /// All 12 phases in order.
    #[must_use]
    pub const fn all() -> [Self; 12] {
        [
            Self::Triage,
            Self::Consolidation,
            Self::Serendipity,
            Self::Governance,
            Self::Narrative,
            Self::Kaizen,
            Self::Oracle,
            Self::Decay,
            Self::Constellation,
            Self::Prediction,
            Self::Enrichment,
            Self::Harmonize,
        ]
    }

    /// Human-readable name.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Triage => "triage",
            Self::Consolidation => "consolidation",
            Self::Serendipity => "serendipity",
            Self::Governance => "governance",
            Self::Narrative => "narrative",
            Self::Kaizen => "kaizen",
            Self::Oracle => "oracle",
            Self::Decay => "decay",
            Self::Constellation => "constellation",
            Self::Prediction => "prediction",
            Self::Enrichment => "enrichment",
            Self::Harmonize => "harmonize",
        }
    }

    /// Description of what the phase does.
    #[must_use]
    pub const fn description(self) -> &'static str {
        match self {
            Self::Triage => "Classify memories by importance and urgency",
            Self::Consolidation => "Merge related memories and resolve duplicates",
            Self::Serendipity => "Discover unexpected cross-galaxy associations",
            Self::Governance => "Apply Dharma rules and karma reconciliation",
            Self::Narrative => "Weave memories into coherent story arcs",
            Self::Kaizen => "Incremental improvement of memory quality",
            Self::Oracle => "Generate predictions from consolidated patterns",
            Self::Decay => "Apply mindful forgetting to low-significance memories",
            Self::Constellation => "Detect and form memory clusters",
            Self::Prediction => "Forecast future memory needs",
            Self::Enrichment => "Augment memories with external context",
            Self::Harmonize => "Balance galaxy weights and associations",
        }
    }
}

/// Result of a single dream phase execution.
#[derive(Debug, Clone)]
pub struct PhaseResult {
    /// Which phase produced this result
    pub phase: DreamPhase,
    /// Number of memories processed
    pub memories_processed: usize,
    /// Number of memories created/modified
    pub memories_modified: usize,
    /// Number of associations discovered/created
    pub associations: usize,
    /// Duration of the phase
    pub duration: Duration,
    /// Whether the phase completed successfully
    pub success: bool,
    /// Optional notes or metadata
    pub notes: String,
}

/// Result of a complete dream cycle.
#[derive(Debug, Clone)]
pub struct DreamResult {
    /// Results from each phase
    pub phases: Vec<PhaseResult>,
    /// Total duration of the dream cycle
    pub total_duration: Duration,
    /// Whether the entire cycle completed successfully
    pub success: bool,
    /// When the dream cycle started
    pub started: Instant,
    /// Total memories processed across all phases
    pub total_memories_processed: usize,
    /// Total memories modified across all phases
    pub total_memories_modified: usize,
    /// Total associations discovered
    pub total_associations: usize,
}

impl DreamResult {
    /// Convert to a JSON status snapshot.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        let phases: Vec<serde_json::Value> = self
            .phases
            .iter()
            .map(|p| {
                serde_json::json!({
                    "phase": p.phase.name(),
                    "memories_processed": p.memories_processed,
                    "memories_modified": p.memories_modified,
                    "associations": p.associations,
                    "duration_ms": p.duration.as_millis() as u64,
                    "success": p.success,
                })
            })
            .collect();

        serde_json::json!({
            "phases": phases,
            "total_duration_ms": self.total_duration.as_millis() as u64,
            "success": self.success,
            "total_memories_processed": self.total_memories_processed,
            "total_memories_modified": self.total_memories_modified,
            "total_associations": self.total_associations,
        })
    }
}

/// Sleep consolidation — important turns → codex galaxy.
///
/// During the dream cycle, significant interactions are consolidated
/// into the codex galaxy for long-term storage. This tracks which
/// turns were selected for consolidation.
#[derive(Debug, Clone)]
pub struct SleepConsolidation {
    /// Number of turns consolidated
    turns_consolidated: u64,
    /// Number of turns considered but skipped (low significance)
    turns_skipped: u64,
    /// IDs of consolidated memories (for verification)
    consolidated_ids: Vec<String>,
    /// When the last consolidation ran
    last_run: Option<Instant>,
}

impl SleepConsolidation {
    /// Create a new sleep consolidation tracker.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            turns_consolidated: 0,
            turns_skipped: 0,
            consolidated_ids: Vec::new(),
            last_run: None,
        }
    }

    /// Record a consolidated turn.
    pub fn consolidate(&mut self, memory_id: String) {
        self.turns_consolidated += 1;
        self.consolidated_ids.push(memory_id);
        self.last_run = Some(Instant::now());
    }

    /// Record a skipped turn (below significance threshold).
    pub const fn skip(&mut self) {
        self.turns_skipped += 1;
    }

    /// Number of turns consolidated.
    #[must_use]
    pub const fn consolidated(&self) -> u64 {
        self.turns_consolidated
    }

    /// Number of turns skipped.
    #[must_use]
    pub const fn skipped(&self) -> u64 {
        self.turns_skipped
    }

    /// IDs of consolidated memories.
    #[must_use]
    pub fn ids(&self) -> &[String] {
        &self.consolidated_ids
    }

    /// When the last consolidation ran.
    #[must_use]
    pub const fn last_run(&self) -> Option<Instant> {
        self.last_run
    }
}

impl Default for SleepConsolidation {
    fn default() -> Self {
        Self::new()
    }
}

/// Context provided to each dream phase — holds references to the
/// memory store and association store so phases can read/write memories.
pub struct DreamContext<'a> {
    /// LMDB memory store
    pub store: &'a MemoryStore,
    /// Association store for cross-galaxy links
    pub associations: &'a AssociationStore,
    /// Optional imagination engine for counterfactual replay during Oracle phase
    pub imagination: Option<&'a ScenarioEngine>,
    /// Optional Yama gate (ResourceRules) — the same instance the dispatch
    /// pipeline evaluates on the tool path. **S7 finding:** dream phases
    /// historically bypassed Yama entirely (they write via `store.put`
    /// directly, and no hook existed). Phases that perform bulk
    /// synthesized writes (the S7 distillation in `phase_narrative`) admit
    /// each write through [`DreamContext::yama_admit`], sharing the live
    /// write budget with the tool path — the simplest honest form of
    /// Yama rate-limiting for sleep.
    pub yama: Option<&'a wm_governance::ResourceRules>,
    /// Homeostasis snapshot for Yama health scaling (taken when Yama is
    /// attached; falls back to `Default` when absent).
    pub homeostasis: Option<wm_governance::Homeostasis>,
    /// Current brain wave for Yama state scaling (Theta quarters the
    /// write budget — sleep writes get sleep-budget discipline).
    pub brain_wave: BrainWave,
    /// Cached scan results (galaxy, memories) — populated on first scan, reused across phases
    scan_cache: std::cell::RefCell<Option<GalaxyScanCache>>,
}

/// Outcome of a Yama admission request from a dream phase.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum YamaDecision {
    /// Write may proceed (budget consumed where applicable).
    Allow,
    /// Non-blocking flag (novelty) — proceed, but disclose in the notes.
    Flag(String),
    /// Blocking verdict (budget exceeded, human review, no purpose).
    Block(String),
}

/// Cached galaxy scan results shared across dream phases.
type GalaxyScanCache = Vec<(Galaxy, Vec<Memory>)>;

impl<'a> DreamContext<'a> {
    /// Create a new dream context.
    #[allow(clippy::missing_const_for_fn)]
    pub fn new(store: &'a MemoryStore, associations: &'a AssociationStore) -> Self {
        Self {
            store,
            associations,
            imagination: None,
            yama: None,
            homeostasis: None,
            brain_wave: BrainWave::Theta,
            scan_cache: std::cell::RefCell::new(None),
        }
    }

    /// Attach an imagination engine for counterfactual replay during the Oracle phase.
    #[must_use]
    pub const fn with_imagination(mut self, engine: &'a ScenarioEngine) -> Self {
        self.imagination = Some(engine);
        self
    }

    /// Attach the Yama gate for dream-phase writes (S7).
    ///
    /// `homeostasis` should be a snapshot taken by the scheduler right
    /// before the dream cycle; `brain_wave` is the state sleep runs in
    /// (the dream cycle is entered from Theta).
    #[must_use]
    pub const fn with_yama(
        mut self,
        rules: &'a wm_governance::ResourceRules,
        homeostasis: wm_governance::Homeostasis,
        brain_wave: BrainWave,
    ) -> Self {
        self.yama = Some(rules);
        self.homeostasis = Some(homeostasis);
        self.brain_wave = brain_wave;
        self
    }

    /// Ask Yama whether one dream-phase write may proceed.
    ///
    /// Mirrors the dispatch pipeline's semantics (`wm-dispatch`
    /// `pipeline.rs` step 2b): write budget is consumed and scaled by
    /// health + brain wave; blocking verdicts (`BudgetExceeded`,
    /// `RequiresHumanReview`, `NoPurpose`) stop the phase; novelty is a
    /// non-blocking flag, exactly as on the tool path. The write declares
    /// its purpose (`has_purpose = true`) — autonomous synthesis is
    /// always purposeful here, and the human-review gate still applies
    /// when the operator has flagged the session autonomous without
    /// approval.
    pub fn yama_admit(&self, action: &str, key: &str) -> YamaDecision {
        let Some(rules) = self.yama else {
            return YamaDecision::Allow;
        };
        let homeostasis = self.homeostasis.clone().unwrap_or_default();
        // args_hash: FNV-1a over the identity key so novelty distinguishes
        // distinct writes (same behavior as the pipeline's arg hashing).
        let args_hash = key.bytes().fold(0xcbf2_9ce4_8422_2325u64, |acc, b| {
            (acc ^ u64::from(b)).wrapping_mul(0x0000_0100_0000_01b3)
        });
        let verdict = rules.evaluate(
            action,
            args_hash,
            true,  // is_write — every admitted call consumes write budget
            false, // is_spawn
            false, // is_network
            true,  // has_purpose — distillation declares its purpose
            &homeostasis,
            self.brain_wave,
        );
        match verdict {
            wm_governance::ResourceVerdict::Allow => YamaDecision::Allow,
            wm_governance::ResourceVerdict::NotNovel { .. } => YamaDecision::Flag(verdict.reason()),
            _ => YamaDecision::Block(verdict.reason()),
        }
    }

    /// Get cached scan results, scanning once and reusing across phases.
    /// This avoids 8+ redundant full-galaxy scans per dream cycle.
    fn cached_scan_all_galaxies(&self, limit: usize) -> Result<Vec<(Galaxy, Vec<Memory>)>> {
        if self.scan_cache.borrow().is_some() {
            return Ok(self.scan_cache.borrow().as_ref().unwrap().clone());
        }
        let result = self.scan_all_galaxies(limit)?;
        *self.scan_cache.borrow_mut() = Some(result.clone());
        Ok(result)
    }

    /// Invalidate the scan cache — call after phases that modify memories
    /// (like decay) so subsequent phases re-scan and see fresh data.
    fn invalidate_cache(&self) {
        *self.scan_cache.borrow_mut() = None;
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
}

/// Dream cycle runner — executes all 12 phases sequentially.
///
/// Triggered by Theta brain-wave state. Runs a single complete cycle,
/// then transitions to Delta. The runner is synchronous — it executes
/// each phase in order and collects results. Each phase interacts with
/// the memory store via `DreamContext` to perform real consolidation,
/// association mining, decay, and other memory operations.
pub struct DreamCycle {
    /// Sleep consolidation tracker
    pub consolidation: SleepConsolidation,
    /// Whether the dream cycle is currently running
    running: bool,
    /// Number of completed dream cycles
    cycles_completed: u64,
    /// Last dream result
    last_result: Option<DreamResult>,
    /// Optional learned dream cycle for adaptive phase selection (Phase 6)
    learned: Option<wm_core::LearnedDreamCycle>,
    /// S7 distillation: per-topic evidence fingerprints from the last
    /// Narrative run — topics whose evidence is unchanged skip rewriting.
    /// In-memory only: after a daemon restart one redundant pass may run,
    /// which `put_dedup` absorbs.
    distill_fingerprints: HashMap<String, u64>,
}

impl DreamCycle {
    /// Create a new dream cycle runner.
    #[must_use]
    pub fn new() -> Self {
        Self {
            consolidation: SleepConsolidation::new(),
            running: false,
            cycles_completed: 0,
            last_result: None,
            learned: None,
            distill_fingerprints: HashMap::new(),
        }
    }

    /// Attach a LearnedDreamCycle for adaptive phase selection (Phase 6).
    #[must_use]
    pub fn with_learned(mut self, learned: wm_core::LearnedDreamCycle) -> Self {
        self.learned = Some(learned);
        self
    }

    /// Get a reference to the LearnedDreamCycle, if attached.
    #[must_use]
    pub const fn learned(&self) -> Option<&wm_core::LearnedDreamCycle> {
        self.learned.as_ref()
    }

    /// Get a mutable reference to the LearnedDreamCycle, if attached.
    pub const fn learned_mut(&mut self) -> Option<&mut wm_core::LearnedDreamCycle> {
        self.learned.as_mut()
    }

    /// Replace the LearnedDreamCycle (used for persistence load).
    pub fn set_learned(&mut self, learned: wm_core::LearnedDreamCycle) {
        self.learned = Some(learned);
    }

    /// Whether the dream cycle is currently running.
    #[must_use]
    pub const fn is_running(&self) -> bool {
        self.running
    }

    /// Number of completed dream cycles.
    #[must_use]
    pub const fn cycles_completed(&self) -> u64 {
        self.cycles_completed
    }

    /// Last dream result (if any).
    #[must_use]
    pub const fn last_result(&self) -> Option<&DreamResult> {
        self.last_result.as_ref()
    }

    /// Check if the dream cycle should run.
    /// Only runs in Theta state, not already running.
    #[must_use]
    pub fn should_run(&self, brain_wave: BrainWave) -> bool {
        brain_wave == BrainWave::Theta && !self.running
    }

    /// Run the complete 12-phase dream cycle with a memory store context.
    ///
    /// Each phase is executed sequentially. The runner collects
    /// results and tracks timing. Sleep consolidation is performed
    /// during the Consolidation phase.
    pub fn run(&mut self, ctx: &DreamContext) -> DreamResult {
        self.running = true;
        let start = Instant::now();
        let mut phases = Vec::with_capacity(12);
        let mut all_success = true;

        // Determine which phases to run and in what order
        let phases_to_run: Vec<DreamPhase> = if let Some(ref learned) = self.learned {
            let indices = learned.phases_to_run();
            indices
                .iter()
                .filter_map(|&idx| DreamPhase::all().get(idx as usize).copied())
                .collect()
        } else {
            DreamPhase::all().to_vec()
        };

        for phase in &phases_to_run {
            let phase_start = Instant::now();
            let result = self.run_phase(*phase, ctx);
            let duration = phase_start.elapsed();

            // Record phase effectiveness if learned cycle is attached
            if let Some(ref mut learned) = self.learned {
                let useful = result.0 > 0 || result.2 > 0;
                let improvement = if result.0 > 0 {
                    result.1 as f32 / result.0 as f32
                } else {
                    0.0
                };
                let phase_idx = DreamPhase::all()
                    .iter()
                    .position(|p| p == phase)
                    .unwrap_or(0) as u8;
                learned.record_phase(phase_idx, useful, improvement, duration.as_millis() as u64);
            }

            phases.push(PhaseResult {
                phase: *phase,
                memories_processed: result.0,
                memories_modified: result.1,
                associations: result.2,
                duration,
                success: result.3,
                notes: result.4,
            });

            if !result.3 {
                all_success = false;
            }
        }

        let total_duration = start.elapsed();
        self.cycles_completed += 1;
        self.running = false;

        let total_memories_processed: usize = phases.iter().map(|p| p.memories_processed).sum();
        let total_memories_modified: usize = phases.iter().map(|p| p.memories_modified).sum();
        let total_associations: usize = phases.iter().map(|p| p.associations).sum();

        let result = DreamResult {
            phases,
            total_duration,
            success: all_success,
            started: start,
            total_memories_processed,
            total_memories_modified,
            total_associations,
        };

        self.last_result = Some(result.clone());
        result
    }

    /// Run a single phase with memory store context.
    /// Returns (processed, modified, associations, success, notes).
    fn run_phase(
        &mut self,
        phase: DreamPhase,
        ctx: &DreamContext,
    ) -> (usize, usize, usize, bool, String) {
        let result = match phase {
            DreamPhase::Triage => self.phase_triage(ctx),
            DreamPhase::Consolidation => self.phase_consolidation(ctx),
            DreamPhase::Serendipity => self.phase_serendipity(ctx),
            DreamPhase::Governance => self.phase_governance(ctx),
            DreamPhase::Narrative => self.phase_narrative(ctx),
            DreamPhase::Kaizen => self.phase_kaizen(ctx),
            DreamPhase::Oracle => self.phase_oracle(ctx),
            DreamPhase::Decay => self.phase_decay(ctx),
            DreamPhase::Constellation => self.phase_constellation(ctx),
            DreamPhase::Prediction => self.phase_prediction(ctx),
            DreamPhase::Enrichment => self.phase_enrichment(ctx),
            DreamPhase::Harmonize => self.phase_harmonize(ctx),
        };

        // Invalidate scan cache after phases that modify memories
        // so subsequent phases re-scan and see fresh data
        if matches!(
            phase,
            DreamPhase::Consolidation
                | DreamPhase::Governance
                | DreamPhase::Kaizen
                | DreamPhase::Decay
                | DreamPhase::Enrichment
                | DreamPhase::Harmonize
                | DreamPhase::Oracle
                | DreamPhase::Narrative
        ) && result.1 > 0
        {
            ctx.invalidate_cache();
        }

        result
    }

    // ── Phase Implementations ──────────────────────────────────────────

    /// Triage — scan recent memories, classify by importance/urgency.
    fn phase_triage(&self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        let galaxy_mems = match ctx.cached_scan_all_galaxies(10_000) {
            Ok(gm) => gm,
            Err(e) => return (0, 0, 0, false, format!("triage error: {e}")),
        };

        let mut total = 0;
        let mut high = 0;
        let mut medium = 0;
        let mut low = 0;

        for (_galaxy, mems) in &galaxy_mems {
            for mem in mems {
                total += 1;
                match mem.metadata.importance {
                    x if x >= 0.7 => high += 1,
                    x if x >= 0.3 => medium += 1,
                    _ => low += 1,
                }
            }
        }

        (
            total,
            0,
            0,
            true,
            format!("triaged {total} memories: {high} high, {medium} medium, {low} low"),
        )
    }

    /// Consolidation — strategy synthesis + sleep consolidation + dedup.
    ///
    /// Phase 6.5 upgrade: now runs strategy synthesis (clustering + meta-insight
    /// generation) alongside the existing sleep consolidation transfer routes
    /// and within-galaxy deduplication.
    fn phase_consolidation(&mut self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        let galaxy_mems = match ctx.cached_scan_all_galaxies(10_000) {
            Ok(gm) => gm,
            Err(e) => return (0, 0, 0, false, format!("consolidation error: {e}")),
        };

        let mut processed = 0;
        let mut modified = 0;

        // Phase 6.5: Strategy synthesis (clustering + meta-insight generation)
        let synth = StrategySynthesizer::default();
        let strategies_created = match synth.synthesize(ctx.store, ctx.associations) {
            Ok(report) => {
                processed += report.memories_analyzed;
                report.strategies_synthesized
            }
            Err(_) => 0,
        };

        // Sleep consolidation pathways: source → target
        let pathways = [
            (Galaxy::Sessions, Galaxy::Codex, 0.6),
            (Galaxy::Citta, Galaxy::Aria, 0.6),
            (Galaxy::Dreams, Galaxy::Research, 0.5),
            (Galaxy::Universal, Galaxy::Codex, 0.6),
        ];

        for (source, target, min_importance) in pathways {
            let source_mems = match ctx.store.scan(source, 10_000) {
                Ok(m) => m,
                Err(_) => continue,
            };

            for mem in &source_mems {
                processed += 1;
                if mem.metadata.importance >= min_importance {
                    // Check if already exists in target (by content hash)
                    let exists = ctx
                        .store
                        .find_by_content_hash(target, &mem.metadata.content_hash)
                        .unwrap_or(None)
                        .is_some();

                    if exists {
                        self.consolidation.skip();
                    } else {
                        // Transfer: write to target galaxy
                        let mut transfer_mem = mem.clone();
                        transfer_mem.metadata.galaxy = target;
                        if ctx.store.put_dedup(target, &transfer_mem).is_ok() {
                            modified += 1;
                            self.consolidation.consolidate(mem.metadata.id.to_string());
                        }
                    }
                } else {
                    self.consolidation.skip();
                }
            }
        }

        // Also deduplicate within each galaxy (remove content_hash duplicates)
        for (galaxy, mems) in &galaxy_mems {
            let mut seen_hashes: HashMap<String, uuid::Uuid> = HashMap::new();
            for mem in mems {
                processed += 1;
                if let Some(&existing_id) = seen_hashes.get(&mem.metadata.content_hash) {
                    // Duplicate found — delete the newer one
                    if mem.metadata.id != existing_id {
                        let _ = ctx.store.delete(*galaxy, mem.metadata.id);
                        modified += 1;
                    }
                } else {
                    seen_hashes.insert(mem.metadata.content_hash.clone(), mem.metadata.id);
                }
            }
        }

        // S5 phase 2: the tier ladder moves ONLY here (§6). Fold the sweep
        // counts into the consolidation report so every tier move is visible
        // in the dream result.
        let (tier_inspected, tier_moved) = self.tier_sweep(ctx);
        processed += tier_inspected;
        modified += tier_moved;

        // Slice B: validity derivation moves ONLY here (D1+D2). Off by
        // default — knob-off the sweep is a (0, 0) no-op and the only
        // report change is the zeroed validity tail.
        let (validity_inspected, validity_moved) = self.validity_sweep(ctx);
        processed += validity_inspected;
        modified += validity_moved;

        (
            processed,
            modified + strategies_created,
            0,
            true,
            format!(
                "consolidated {} memories, {} transferred/deduplicated, {} strategies synthesized, {} turns consolidated, {} tier moves over {} inspected, {} validity moves over {} inspected",
                processed,
                modified,
                strategies_created,
                self.consolidation.consolidated(),
                tier_moved,
                tier_inspected,
                validity_moved,
                validity_inspected
            ),
        )
    }

    /// Tier sweep — the ONLY tier-transition path in the system
    /// (`MEMORY_TYPOLOGY_V8.md` §6). Fresh writes land in
    /// [`wm_memory::Tier::Working`]; sleep ages them out to Episodic,
    /// promotes read-worn survivors to Semantic, and decays stale
    /// low-importance memories out to Archival.
    ///
    /// Policy (one move per memory per dream cycle — the ladder is paced
    /// in sleep, never on the request path):
    /// - `Working → Episodic`: older than [`WORKING_TTL_DAYS`] (no longer
    ///   the current-session working set)
    /// - `Episodic → Semantic`: consolidated survivor — at least
    ///   [`SEMANTIC_MIN_READS`] reads (access + recall) with importance
    ///   at or above [`SEMANTIC_MIN_IMPORTANCE`]
    /// - `→ Archival` (decay-out): past the memory's own
    ///   `half_life_days` AND importance below [`ARCHIVAL_MAX_IMPORTANCE`]
    ///   — skipped for `is_protected` memories (hard protection from
    ///   forgetting)
    ///
    /// All moves go through `Memory::transition_tier`, which refuses
    /// anything off the ladder, so a bug here cannot fabricate illegal
    /// states.
    fn tier_sweep(&self, ctx: &DreamContext) -> (usize, usize) {
        let Ok(galaxy_mems) = ctx.cached_scan_all_galaxies(10_000) else {
            return (0, 0);
        };
        let now = chrono::Utc::now();
        let mut inspected = 0usize;
        let mut moved = 0usize;

        for (galaxy, mems) in &galaxy_mems {
            for mem in mems {
                inspected += 1;
                let age_days = (now - mem.metadata.created_at).num_days() as f32;
                let reads = mem
                    .metadata
                    .access_count
                    .saturating_add(mem.metadata.recall_count);
                let target = match mem.metadata.tier {
                    wm_memory::Tier::Working if age_days >= WORKING_TTL_DAYS => {
                        Some(wm_memory::Tier::Episodic)
                    }
                    wm_memory::Tier::Episodic
                        if reads >= SEMANTIC_MIN_READS
                            && mem.metadata.importance >= SEMANTIC_MIN_IMPORTANCE =>
                    {
                        Some(wm_memory::Tier::Semantic)
                    }
                    tier if tier != wm_memory::Tier::Archival
                        && !mem.metadata.is_protected
                        && age_days >= mem.metadata.half_life_days
                        && mem.metadata.importance < ARCHIVAL_MAX_IMPORTANCE =>
                    {
                        Some(wm_memory::Tier::Archival)
                    }
                    _ => None,
                };
                if let Some(to) = target {
                    let mut staged = mem.clone();
                    if staged.transition_tier(to).is_ok() && ctx.store.put(*galaxy, &staged).is_ok()
                    {
                        moved += 1;
                    }
                }
            }
        }
        (inspected, moved)
    }

    /// Validity sweep — the ONLY validity-transition path in the system
    /// (V8 Slice B, D1+D2). Corrections arrive as notes: a correction is a
    /// new memory plus a `Supersedes` edge (`memory.relate` — target
    /// supersedes source); this sweep derives the validity stamp from the
    /// edge, so the graph is the claim and sleep is the adjudication.
    ///
    /// Policy (one move per memory per dream cycle, same pacing as the
    /// tier ladder):
    /// - outgoing `Supersedes` edge `M → T`: `M` transitions to
    ///   `Superseded { by: T }` via `Memory::transition_validity` (which
    ///   enforces the `ValidityState` legality matrix — e.g. revoked or
    ///   erased records refuse, and the move is skipped, never forced).
    /// - non-`Active` records are left untouched (no revival of old
    ///   evidence through this path).
    /// - `Contradicts` edges are NOT adjudicated here (TANGLE semantics:
    ///   both sides stay visible; a future adjudication step decides).
    ///
    /// Gated by `WM_VALIDITY_SWEEP=1` (exact match — anything else,
    /// including unset, stays off). Knob-off this returns `(0, 0)` without
    /// scanning, so sleep is byte-identical to pre-Slice-B.
    fn validity_sweep(&self, ctx: &DreamContext) -> (usize, usize) {
        self.validity_sweep_inner(ctx, validity_sweep_enabled())
    }

    /// Sweep core with the gate as a parameter, so tests can exercise the
    /// derivation without mutating process env (which is `unsafe` under
    /// edition-2024 `forbid(unsafe)`).
    fn validity_sweep_inner(&self, ctx: &DreamContext, enabled: bool) -> (usize, usize) {
        if !enabled {
            return (0, 0);
        }
        let Ok(galaxy_mems) = ctx.cached_scan_all_galaxies(10_000) else {
            return (0, 0);
        };
        let env = ctx.store.env();
        let mut inspected = 0usize;
        let mut moved = 0usize;

        for (galaxy, mems) in &galaxy_mems {
            for mem in mems {
                if !mem.metadata.validity.is_current() {
                    continue;
                }
                inspected += 1;
                let outgoing = ctx
                    .associations
                    .find_from(env, mem.metadata.id)
                    .unwrap_or_default();
                let superseded_by = outgoing.iter().find_map(|edge| {
                    if edge.link_type == wm_memory::LinkType::Supersedes {
                        Some(edge.target)
                    } else {
                        None
                    }
                });
                if let Some(replacement) = superseded_by {
                    let mut staged = mem.clone();
                    let transition = wm_core::MemoryTransition::Supersede { replacement };
                    if staged.transition_validity(transition).is_ok()
                        && ctx.store.put(*galaxy, &staged).is_ok()
                    {
                        moved += 1;
                    }
                }
            }
        }
        (inspected, moved)
    }

    /// Serendipity — keyword overlap analysis, propose associations.
    fn phase_serendipity(&self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        let miner = AssociationMiner::default_config();
        let report = match miner.mine(ctx.store, ctx.associations) {
            Ok(r) => r,
            Err(e) => return (0, 0, 0, false, format!("serendipity error: {e}")),
        };

        (
            report.memories_sampled,
            0,
            report.links_created,
            true,
            format!(
                "sampled {} memories, evaluated {} pairs, created {} associations",
                report.memories_sampled, report.pairs_evaluated, report.links_created
            ),
        )
    }

    /// Governance — check memories for anomalies (importance out of bounds, etc).
    fn phase_governance(&self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        let galaxy_mems = match ctx.cached_scan_all_galaxies(10_000) {
            Ok(gm) => gm,
            Err(e) => return (0, 0, 0, false, format!("governance error: {e}")),
        };

        let mut processed = 0;
        let mut modified = 0;
        let mut anomalies = 0;

        for (galaxy, mems) in &galaxy_mems {
            let mut to_fix: Vec<Memory> = Vec::new();
            for mem in mems {
                processed += 1;
                let needs_fix = mem.metadata.importance < 0.0
                    || mem.metadata.importance > 1.0
                    || mem.content.is_empty()
                    || mem.metadata.accessed_at < mem.metadata.created_at;

                if needs_fix {
                    anomalies += 1;
                    let mut fixed = mem.clone();
                    // Clamp importance
                    fixed.metadata.importance = fixed.metadata.importance.clamp(0.0, 1.0);
                    // Fix accessed_at if invalid
                    if fixed.metadata.accessed_at < fixed.metadata.created_at {
                        fixed.metadata.accessed_at = fixed.metadata.created_at;
                    }
                    // Skip empty content (can't fix, just flag)
                    if !fixed.content.is_empty() {
                        to_fix.push(fixed);
                    }
                }
            }
            if !to_fix.is_empty() {
                modified += to_fix.len();
                let _ = ctx.store.put_batch(*galaxy, &to_fix);
            }
        }

        (
            processed,
            modified,
            0,
            true,
            format!(
                "governance checked {processed} memories, {anomalies} anomalies found, {modified} fixed"
            ),
        )
    }

    /// Narrative — S7 distillation: deterministic session-file layer +
    /// question-addressed cross-session topic summaries.
    ///
    /// Generalizes the embryonic topic summarizer ("Dream summary"
    /// records) into the `V8_DISTILLATION_DESIGN` §2 funnel, natively:
    ///
    /// 1. **Session-file layer (deterministic, LLM-free):** every session
    ///    in the Sessions galaxy becomes a digest in Dreams whose
    ///    provenance header carries session id, date span, workspace,
    ///    token/cost counts *or an explicit not-tracked disclosure*, and
    ///    a statement of what was dropped.
    /// 2. **Topic layer:** cross-session topic summaries per project/
    ///    entity, each anchored to the question it answers, evidence
    ///    lines citing source sessions. Topics derive from turn `topic`
    ///    metadata (envelope v2), non-structural tags, and extracted
    ///    entities. Importance is an evidence prior with cost/token mass
    ///    as a capped nudge — never the sole signal.
    /// 3. **LLM synthesis only above:** when an LLM is configured
    ///    (`WM_LLM_API_KEY`, bounded by `MAX_LLM_SYNTH_PER_CYCLE`), a
    ///    disclosed synthesis section is added; without one the
    ///    deterministic layer alone is fully functional (`llm: none`).
    ///
    /// Every synthesized write is admitted through Yama
    /// ([`DreamContext::yama_admit`]) — the same `ResourceRules` the
    /// dispatch pipeline evaluates, so dream writes share the live write
    /// budget (Theta scaling = quarter budget). A blocking verdict stops
    /// the phase with the reason disclosed in the notes; writes are
    /// `put_dedup`-ed so unchanged evidence never duplicates.
    fn phase_narrative(&mut self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        let session_mems = match ctx.store.scan(Galaxy::Sessions, 10_000) {
            Ok(m) => m,
            Err(e) => return (0, 0, 0, false, format!("narrative error: {e}")),
        };

        // ── 1. Assemble deterministic session files ────────────────────
        let mut files: Vec<crate::distill::SessionFile> = Vec::new();
        let mut file_index: HashMap<String, usize> = HashMap::new();
        let processed = session_mems.len();

        for mem in &session_mems {
            if mem.metadata.tags.iter().any(|t| t == "start") {
                if let Some(sf) = crate::distill::session_file_from_start(mem) {
                    file_index.insert(sf.session_id.clone(), files.len());
                    files.push(sf);
                }
            }
        }

        let mut turns: Vec<crate::distill::TurnRecord> = session_mems
            .iter()
            .filter(|m| {
                !m.metadata
                    .tags
                    .iter()
                    .any(|t| t.starts_with("superseded-by:"))
            })
            .filter_map(crate::distill::turn_record_from_memory)
            .collect();
        // Deterministic transcript order: timestamp, then id tiebreak.
        turns.sort_by(|a, b| {
            a.timestamp_ms
                .cmp(&b.timestamp_ms)
                .then_with(|| a.memory_id.cmp(&b.memory_id))
        });
        for tr in turns {
            if let Some(&i) = file_index.get(&tr.session_id) {
                let f = &mut files[i];
                if f.span_start_ms == 0 || tr.timestamp_ms < f.span_start_ms {
                    f.span_start_ms = tr.timestamp_ms;
                }
                if tr.timestamp_ms > f.span_end_ms {
                    f.span_end_ms = tr.timestamp_ms;
                }
                f.turns.push(tr);
            }
        }

        let digested: Vec<&crate::distill::SessionFile> = files
            .iter()
            .filter(|f| f.turns.len() >= crate::distill::MIN_TURNS_PER_SESSION)
            .collect();

        // ── 2. Write session digests (Yama-gated, deduped) ─────────────
        let mut written = 0usize;
        let mut novelty_flags: Vec<String> = Vec::new();
        let mut yama_block: Option<String> = None;
        let mut blocked_sessions = 0usize;

        for f in &digested {
            match ctx.yama_admit("dream.distill.session", &f.session_id) {
                YamaDecision::Block(reason) => {
                    yama_block = Some(reason);
                    blocked_sessions += 1;
                    continue;
                }
                YamaDecision::Flag(reason) => novelty_flags.push(reason),
                YamaDecision::Allow => {}
            }
            let avg_importance: f32 =
                f.turns.iter().map(|t| t.importance).sum::<f32>() / f.turns.len() as f32;
            // Evidence prior: turn count + mean importance; the header's
            // token/cost disclosure is informational, not a rank signal
            // at the per-session level. Deterministic-scorer convention:
            // mul_add would change the float rounding of the prior.
            #[allow(clippy::suboptimal_flops)]
            let importance =
                (0.4 + 0.03 * f.turns.len().min(10) as f32 + 0.2 * avg_importance).clamp(0.0, 1.0);
            let mem = crate::distill::distill_memory(
                f.to_markdown(),
                format!("Distill: session {}", f.session_id),
                f.title.clone(),
                "distill:session",
                std::slice::from_ref(&f.session_id),
                importance,
            );
            if ctx.store.put_dedup(Galaxy::Dreams, &mem).is_ok() {
                written += 1;
            }
        }

        // ── 3. Question-addressed topic summaries ──────────────────────
        let digested_owned: Vec<crate::distill::SessionFile> =
            digested.into_iter().cloned().collect();
        let topics = crate::distill::derive_topics(&digested_owned);
        let llm = wm_bicameral::LlmTierHandler::right_from_env();
        let mut topics_written = 0usize;
        let mut llm_syntheses = 0usize;

        for topic in &topics {
            let fingerprint = topic.fingerprint();
            if self.distill_fingerprints.get(&topic.topic) == Some(&fingerprint) {
                continue; // evidence unchanged — no rewrite churn
            }
            match ctx.yama_admit("dream.distill.topic", &fingerprint.to_string()) {
                YamaDecision::Block(reason) => {
                    yama_block = Some(reason);
                    break;
                }
                YamaDecision::Flag(reason) => novelty_flags.push(reason),
                YamaDecision::Allow => {}
            }
            let synthesis = if llm_syntheses < crate::distill::MAX_LLM_SYNTH_PER_CYCLE {
                llm.as_ref()
                    .and_then(|h| crate::distill::synthesize_with_llm(h, topic))
            } else {
                None
            };
            if synthesis.is_some() {
                llm_syntheses += 1;
            }
            let mem = crate::distill::distill_memory(
                topic.to_markdown(synthesis.as_deref()),
                format!("Distill: {}", topic.topic),
                topic.topic.clone(),
                &format!("distill:topic:{}", crate::distill::slug(&topic.topic)),
                &topic.sessions,
                topic.importance_prior(),
            );
            if ctx.store.put_dedup(Galaxy::Dreams, &mem).is_ok() {
                written += 1;
                topics_written += 1;
            }
            self.distill_fingerprints
                .insert(topic.topic.clone(), fingerprint);
        }

        // ── 4. Distillation index (the index.json analog) ───────────────
        if !digested_owned.is_empty() || !topics.is_empty() {
            let index_mem = crate::distill::distill_memory(
                crate::distill::index_markdown(&digested_owned, &topics),
                "Distill: index".to_string(),
                "distillation index".to_string(),
                "distill:index",
                &[],
                0.5,
            );
            match ctx.yama_admit("dream.distill.index", &index_mem.metadata.content_hash) {
                YamaDecision::Block(reason) => yama_block = Some(reason),
                YamaDecision::Flag(reason) => novelty_flags.push(reason),
                YamaDecision::Allow => {
                    if ctx.store.put_dedup(Galaxy::Dreams, &index_mem).is_ok() {
                        written += 1;
                    }
                }
            }
        }

        let mut notes = format!(
            "distilled {} session files, {topics_written} topic summaries over {} sessions, index written; {written} memories written",
            digested_owned.len(),
            topics.len(),
        );
        if llm.is_some() && llm_syntheses > 0 {
            write!(notes, ", {llm_syntheses} llm syntheses")
                .expect("writing to a String cannot fail");
        } else if llm.is_none() {
            notes.push_str(", llm: none configured (deterministic layer only)");
        }
        if let Some(reason) = &yama_block {
            write!(
                notes,
                "; yama blocked remaining writes ({reason}) — {blocked_sessions} session digests skipped"
            )
            .expect("writing to a String cannot fail");
        }
        if !novelty_flags.is_empty() {
            write!(notes, "; yama novelty flags: {}", novelty_flags.join(" | "))
                .expect("writing to a String cannot fail");
        }

        (processed, written, 0, true, notes)
    }

    /// Kaizen — boost importance of frequently-accessed but undervalued memories.
    fn phase_kaizen(&self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        let galaxy_mems = match ctx.cached_scan_all_galaxies(10_000) {
            Ok(gm) => gm,
            Err(e) => return (0, 0, 0, false, format!("kaizen error: {e}")),
        };

        let mut processed = 0;
        let mut modified = 0;

        for (galaxy, mems) in &galaxy_mems {
            let mut to_boost: Vec<Memory> = Vec::new();
            for mem in mems {
                processed += 1;
                // If access_count is high but importance is low, boost it
                if mem.metadata.access_count >= 3 && mem.metadata.importance < 0.5 {
                    let mut updated = mem.clone();
                    let boost = 0.05 * mem.metadata.access_count as f32;
                    updated.metadata.importance =
                        (updated.metadata.importance + boost).clamp(0.0, 1.0);
                    to_boost.push(updated);
                }
            }
            if !to_boost.is_empty() {
                modified += to_boost.len();
                let _ = ctx.store.put_batch(*galaxy, &to_boost);
            }
        }

        (
            processed,
            modified,
            0,
            true,
            format!("kaizen processed {processed} memories, boosted {modified} undervalued"),
        )
    }

    /// Oracle — pattern detection from association graph (count hubs).
    ///
    /// Phase 6.7 upgrade: uses spreading activation to identify hub memories
    /// that activate large neighborhoods in the association graph.
    ///
    /// Phase 4.6 upgrade: when an imagination engine is attached, uses
    /// counterfactual replay on hub memories — "what if we had consolidated
    /// this hub differently?" — and generates richer hypotheses via the
    /// scenario engine.
    fn phase_oracle(&self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        let galaxy_mems = match ctx.cached_scan_all_galaxies(10_000) {
            Ok(gm) => gm,
            Err(e) => return (0, 0, 0, false, format!("oracle error: {e}")),
        };

        let mut processed = 0;
        let mut hubs = 0;
        let mut hypotheses_stored = 0;
        let mut counterfactuals = 0;
        let sa = SpreadingActivation::new(0.6, 2, 0.1);

        for (_galaxy, mems) in &galaxy_mems {
            for mem in mems {
                processed += 1;
                // Use spreading activation to measure reach
                let reach = sa
                    .spread(mem.metadata.id, ctx.associations, ctx.store.env())
                    .map_or(1, |r| r.activations.len());

                // Memories that activate 5+ others are "hubs"
                if reach >= 5 {
                    hubs += 1;

                    // Store a hypothesis about this hub pattern
                    if mem.metadata.importance > 0.5 {
                        // Phase 4.6: Use imagination engine for counterfactual replay
                        if let Some(engine) = ctx.imagination {
                            let mem_desc = mem.content.chars().take(120).collect::<String>();
                            let state = format!("Memory hub with reach={reach}: {mem_desc}");
                            let goal = "Improve memory consolidation strategy";
                            let actual = "Current: hub detected and tagged";
                            let alternative = "Alternative: split hub into smaller clusters";

                            let reflection = engine.reflect(&state, actual, alternative, goal);

                            let hyp_content = if reflection.would_have_been_better {
                                counterfactuals += 1;
                                format!(
                                    "Hypothesis (counterfactual): Hub memory '{}' (reach={}) — \
                                     alternative clustering may improve consolidation. Lesson: {}",
                                    mem.content.chars().take(60).collect::<String>(),
                                    reach,
                                    reflection.lesson,
                                )
                            } else {
                                format!(
                                    "Hypothesis: Hub memory '{}' (reach={}) confirmed as \
                                     cross-cutting pattern — current consolidation is appropriate.",
                                    mem.content.chars().take(60).collect::<String>(),
                                    reach,
                                )
                            };

                            let mut hyp = Memory::new(Galaxy::Research, hyp_content);
                            hyp.metadata.memory_type = MemoryType::Hypothesis;
                            hyp.metadata.tags = vec![
                                "hypothesis".into(),
                                "oracle".into(),
                                "hub".into(),
                                "counterfactual".into(),
                            ];
                            hyp.metadata.importance = 0.5;
                            if ctx.store.put(Galaxy::Research, &hyp).is_ok() {
                                hypotheses_stored += 1;
                            }
                        } else {
                            // No imagination engine — degraded mode (original behavior)
                            let mut hyp = Memory::new(
                                Galaxy::Research,
                                format!(
                                    "Hypothesis: Hub memory '{}' (reach={}) may benefit from \
                                     targeted consolidation — its high connectivity suggests \
                                     it encodes a cross-cutting pattern.",
                                    mem.content.chars().take(80).collect::<String>(),
                                    reach
                                ),
                            );
                            hyp.metadata.memory_type = MemoryType::Hypothesis;
                            hyp.metadata.tags =
                                vec!["hypothesis".into(), "oracle".into(), "hub".into()];
                            hyp.metadata.importance = 0.4;
                            if ctx.store.put(Galaxy::Research, &hyp).is_ok() {
                                hypotheses_stored += 1;
                            }
                        }
                    }
                }
            }
        }

        let cf_note = if counterfactuals > 0 {
            format!(", {counterfactuals} counterfactual replays")
        } else {
            String::new()
        };

        (
            processed,
            hypotheses_stored,
            0,
            true,
            format!(
                "oracle scanned {processed} memories, found {hubs} hubs, stored {hypotheses_stored} hypotheses{cf_note}"
            ),
        )
    }

    /// Decay — apply mindful forgetting via `RetentionEngine`.
    fn phase_decay(&self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        let engine = RetentionEngine::default_config();
        let mut total_processed = 0;
        let mut total_decayed = 0;

        for galaxy in Galaxy::all() {
            match galaxy {
                Galaxy::Substrate
                | Galaxy::Dharma
                | Galaxy::Karma
                | Galaxy::Embeddings
                | Galaxy::Associations => continue,
                _ => {}
            }
            let count = ctx.store.count(galaxy).unwrap_or(0);
            if count == 0 {
                continue;
            }

            if let Ok(report) = engine.sweep(ctx.store, ctx.associations, galaxy) {
                total_processed += report.total_evaluated;
                total_decayed += report.decayed;
            }
        }

        (
            total_processed,
            total_decayed,
            0,
            true,
            format!(
                "decay processed {total_processed} memories, decayed {total_decayed} (never deleted)"
            ),
        )
    }

    /// Constellation — density clustering in semantic coordinate space.
    ///
    /// Phase 6.6 upgrade: replaces grid-based tag-frequency stub with proper
    /// density clustering using semantic coordinates from Phase 6.3.
    fn phase_constellation(&self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        let mut detector = ConstellationDetector::default();
        let report = match detector.detect(ctx.store) {
            Ok(r) => r,
            Err(e) => return (0, 0, 0, false, format!("constellation error: {e}")),
        };

        (
            report.memories_analyzed,
            0,
            0,
            true,
            format!(
                "constellation found {} clusters ({} dense cells) across {} memories",
                report.constellations.len(),
                report.dense_cells,
                report.memories_analyzed
            ),
        )
    }

    /// Prediction — temporal drift detection on memory access patterns.
    fn phase_prediction(&self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        let galaxy_mems = match ctx.cached_scan_all_galaxies(10_000) {
            Ok(gm) => gm,
            Err(e) => return (0, 0, 0, false, format!("prediction error: {e}")),
        };

        let mut processed = 0;
        let mut stale_count = 0;
        let now = chrono::Utc::now();

        for (_galaxy, mems) in &galaxy_mems {
            for mem in mems {
                processed += 1;
                // Memories not accessed in 7+ days are "drifting"
                let days_since = (now - mem.metadata.accessed_at).num_days();
                if days_since > 7 {
                    stale_count += 1;
                }
            }
        }

        (
            processed,
            0,
            0,
            true,
            format!(
                "prediction: {stale_count} of {processed} memories drifting (7+ days since access)"
            ),
        )
    }

    /// Enrichment — extract entities (frequent keywords) from content, add as tags.
    ///
    /// Phase 6.7 upgrade: also runs ripple tagging to mark high-activity memories
    /// for priority consolidation.
    fn phase_enrichment(&self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        let galaxy_mems = match ctx.cached_scan_all_galaxies(10_000) {
            Ok(gm) => gm,
            Err(e) => return (0, 0, 0, false, format!("enrichment error: {e}")),
        };

        let mut processed = 0;
        let mut enriched = 0;

        for (galaxy, mems) in &galaxy_mems {
            let mut to_tag: Vec<Memory> = Vec::new();
            for mem in mems {
                processed += 1;
                // Only enrich memories with no tags
                if !mem.metadata.tags.is_empty() {
                    continue;
                }

                let keywords = AssociationMiner::extract_keywords(&mem.content, 5);
                if keywords.is_empty() {
                    continue;
                }

                let mut updated = mem.clone();
                updated.metadata.tags = keywords.into_iter().take(3).collect();
                to_tag.push(updated);
            }
            if !to_tag.is_empty() {
                enriched += to_tag.len();
                let _ = ctx.store.put_batch(*galaxy, &to_tag);
            }
        }

        // Phase 6.7: Ripple tagging — mark high-activity memories for consolidation
        let tagger = RippleTagger::default();
        let ripple_report = match tagger.tag(ctx.store) {
            Ok(r) => r,
            Err(_) => RippleReport {
                tagged: 0,
                scanned: 0,
                tagged_ids: vec![],
            },
        };

        (
            processed + ripple_report.scanned,
            enriched + ripple_report.tagged,
            0,
            true,
            format!(
                "enrichment processed {processed} memories, tagged {enriched} untagged, ripple-tagged {}",
                ripple_report.tagged
            ),
        )
    }

    /// Harmonize — balance galaxy weights (normalize importance distributions).
    ///
    /// Phase 6.7 upgrade: applies neuromodulation (dopamine/serotonin) to
    /// modulate retention across all memories before harmonizing.
    fn phase_harmonize(&self, ctx: &DreamContext) -> (usize, usize, usize, bool, String) {
        // Phase 6.7: Apply neuromodulation before harmonizing
        let neuro = Neuromodulator::default();
        let neuro_modified = neuro.apply_to_store(ctx.store).unwrap_or(0);

        let mut galaxy_counts: Vec<(Galaxy, usize, f32)> = Vec::new();

        for galaxy in Galaxy::all() {
            match galaxy {
                Galaxy::Substrate
                | Galaxy::Dharma
                | Galaxy::Karma
                | Galaxy::Embeddings
                | Galaxy::Associations => continue,
                _ => {}
            }
            let mems = ctx.store.scan(galaxy, 10_000).unwrap_or_default();
            if mems.is_empty() {
                continue;
            }
            let avg_importance: f32 =
                mems.iter().map(|m| m.metadata.importance).sum::<f32>() / mems.len() as f32;
            galaxy_counts.push((galaxy, mems.len(), avg_importance));
        }

        let total_memories: usize = galaxy_counts.iter().map(|(_, c, _)| *c).sum();
        let global_avg: f32 = if galaxy_counts.is_empty() {
            0.5
        } else {
            galaxy_counts.iter().map(|(_, _, avg)| *avg).sum::<f32>() / galaxy_counts.len() as f32
        };

        let mut modified = 0;
        for (galaxy, _count, galaxy_avg) in &galaxy_counts {
            // If a galaxy's average importance is far from global average,
            // nudge memories toward the global average
            let drift = (galaxy_avg - global_avg).abs();
            if drift > 0.15 {
                let mems = ctx.store.scan(*galaxy, 10_000).unwrap_or_default();
                let mut to_nudge: Vec<Memory> = Vec::new();
                for mem in mems {
                    // Skip very low-importance memories — they were intentionally
                    // decayed and shouldn't be nudged back up
                    if mem.metadata.importance < 0.1 {
                        continue;
                    }
                    let mut updated = mem.clone();
                    // Nudge toward global average by 10%
                    updated.metadata.importance = updated
                        .metadata
                        .importance
                        .mul_add(0.9, global_avg * 0.1)
                        .clamp(0.0, 1.0);
                    to_nudge.push(updated);
                }
                if !to_nudge.is_empty() {
                    modified += to_nudge.len();
                    let _ = ctx.store.put_batch(*galaxy, &to_nudge);
                }
            }
        }

        (
            total_memories,
            modified + neuro_modified,
            0,
            true,
            format!(
                "harmonized {} memories across {} galaxies, adjusted {} + {} neuromodulated (global avg: {:.2})",
                total_memories,
                galaxy_counts.len(),
                modified,
                neuro_modified,
                global_avg
            ),
        )
    }

    /// Convert to a JSON status snapshot.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "running": self.running,
            "cycles_completed": self.cycles_completed,
            "consolidation": {
                "consolidated": self.consolidation.consolidated(),
                "skipped": self.consolidation.skipped(),
            },
            "last_result": self.last_result.as_ref().map(DreamResult::to_json),
        })
    }
}

impl Default for DreamCycle {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    use wm_memory::AssociationStore;

    /// Test helper: create a `DreamContext` with a temp LMDB store.
    fn test_ctx() -> (tempfile::TempDir, MemoryStore, AssociationStore) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let assoc = AssociationStore::open(store.env()).unwrap();
        (tmp, store, assoc)
    }

    #[test]
    fn dream_phase_all_has_12() {
        assert_eq!(DreamPhase::all().len(), 12);
    }

    /// S5 phase 2: the dream cycle is the ONLY tier-transition path. The
    /// consolidation sweep must age Working out, promote read-worn
    /// survivors, decay the stale out to Archival, move each memory at
    /// most ONE step per cycle, and leave protected memories warm.
    #[test]
    fn dream_cycle_sweep_transitions_tiers() {
        let (_tmp, store, assoc) = test_ctx();
        let now = chrono::Utc::now();

        // 1. Old Working → ages out to Episodic.
        let mut aged = Memory::new(Galaxy::Codex, "aged working note".into());
        aged.metadata.created_at = now - chrono::Duration::hours(30);
        store.put(Galaxy::Codex, &aged).unwrap();
        let aged_id = aged.metadata.id;

        // 2. Read-worn Episodic survivor → Semantic.
        let mut worn = Memory::new(Galaxy::Codex, "worn survivor note".into());
        worn.metadata.created_at = now - chrono::Duration::days(3);
        worn.metadata.tier = wm_memory::Tier::Episodic;
        worn.metadata.access_count = 6;
        worn.metadata.importance = 0.8;
        store.put(Galaxy::Codex, &worn).unwrap();
        let worn_id = worn.metadata.id;

        // 3. Old low-importance Episodic → decayed out to Archival.
        let mut stale = Memory::new(Galaxy::Codex, "stale forgotten note".into());
        stale.metadata.created_at = now - chrono::Duration::days(60);
        stale.metadata.tier = wm_memory::Tier::Episodic;
        stale.metadata.importance = 0.2;
        store.put(Galaxy::Codex, &stale).unwrap();
        let stale_id = stale.metadata.id;

        // 4. Fresh Working memory stays in the working set.
        let fresh = Memory::new(Galaxy::Codex, "fresh note".into());
        store.put(Galaxy::Codex, &fresh).unwrap();
        let fresh_id = fresh.metadata.id;

        // 5. Ladder pacing: an old low-importance Working memory moves ONE
        //    step (age-out wins) — never straight to Archival in one cycle.
        let mut paced = Memory::new(Galaxy::Codex, "paced note".into());
        paced.metadata.created_at = now - chrono::Duration::days(60);
        paced.metadata.importance = 0.2;
        store.put(Galaxy::Codex, &paced).unwrap();
        let paced_id = paced.metadata.id;

        // 6. Protection shields from decay-out: old, low-importance,
        //    Episodic — but is_protected stays warm.
        let mut guarded = Memory::new(Galaxy::Codex, "guarded note".into());
        guarded.metadata.created_at = now - chrono::Duration::days(60);
        guarded.metadata.tier = wm_memory::Tier::Episodic;
        guarded.metadata.importance = 0.2;
        guarded.metadata.is_protected = true;
        store.put(Galaxy::Codex, &guarded).unwrap();
        let guarded_id = guarded.metadata.id;

        let ctx = DreamContext::new(&store, &assoc);
        let mut cycle = DreamCycle::new();
        let result = cycle.run(&ctx);
        assert!(result.success);

        let tier_of = |id: uuid::Uuid| store.get(Galaxy::Codex, id).unwrap().unwrap().metadata.tier;
        assert_eq!(tier_of(aged_id), wm_memory::Tier::Episodic);
        assert_eq!(tier_of(worn_id), wm_memory::Tier::Semantic);
        assert_eq!(tier_of(stale_id), wm_memory::Tier::Archival);
        assert_eq!(tier_of(fresh_id), wm_memory::Tier::Working);
        assert_eq!(
            tier_of(paced_id),
            wm_memory::Tier::Episodic,
            "one move per cycle: Working ages out before decay-out"
        );
        assert_eq!(
            tier_of(guarded_id),
            wm_memory::Tier::Episodic,
            "protection must shield from decay-out"
        );
    }

    /// Slice B: validity derives from the graph in sleep, never on the
    /// request path. Corrections are notes (a new memory + a Supersedes
    /// edge); the sweep stamps the source Superseded. Knob-off the sweep
    /// is a (0, 0) no-op even with edges present.
    #[test]
    fn validity_sweep_derives_superseded_from_edges() {
        let (_tmp, store, assoc) = test_ctx();
        let env = store.env();

        let old = Memory::new(Galaxy::Codex, "old claim".into());
        let old_id = old.metadata.id;
        store.put(Galaxy::Codex, &old).unwrap();
        let new = Memory::new(Galaxy::Codex, "corrected claim".into());
        let new_id = new.metadata.id;
        store.put(Galaxy::Codex, &new).unwrap();

        // Correction-as-note: target supersedes source.
        let edge =
            wm_memory::Association::new(old_id, new_id, wm_memory::LinkType::Supersedes, 0.9);
        assoc.put(env, &edge).unwrap();

        let ctx = DreamContext::new(&store, &assoc);
        let cycle = DreamCycle::new();

        // Knob-off: no-op, source stays current.
        let (inspected_off, moved_off) = cycle.validity_sweep(&ctx);
        assert_eq!((inspected_off, moved_off), (0, 0));
        let validity_of = |id: uuid::Uuid| {
            store
                .get(Galaxy::Codex, id)
                .unwrap()
                .unwrap()
                .metadata
                .validity
        };
        assert!(validity_of(old_id).is_current());

        // Enabled: source derives Superseded{by: new}, target untouched.
        let (inspected_on, moved_on) = cycle.validity_sweep_inner(&ctx, true);
        assert_eq!(inspected_on, 2);
        assert_eq!(moved_on, 1);
        assert_eq!(
            validity_of(old_id),
            wm_core::episodic::ValidityState::Superseded { by: new_id }
        );
        assert!(validity_of(new_id).is_current());
    }

    /// Slice B: revoked records refuse re-derivation, and non-Supersedes
    /// edges (e.g. Contradicts) are surfaced, never adjudicated, by the
    /// sweep (TANGLE semantics).
    #[test]
    fn validity_sweep_leaves_revoked_and_contradicted_alone() {
        let (_tmp, store, assoc) = test_ctx();
        let env = store.env();

        let mut revoked = Memory::new(Galaxy::Codex, "revoked claim".into());
        revoked
            .transition_validity(wm_core::MemoryTransition::Revoke {
                reason: "test".into(),
            })
            .unwrap();
        let revoked_id = revoked.metadata.id;
        store.put(Galaxy::Codex, &revoked).unwrap();
        let replacement = Memory::new(Galaxy::Codex, "replacement".into());
        let replacement_id = replacement.metadata.id;
        store.put(Galaxy::Codex, &replacement).unwrap();
        assoc
            .put(
                env,
                &wm_memory::Association::new(
                    revoked_id,
                    replacement_id,
                    wm_memory::LinkType::Supersedes,
                    0.9,
                ),
            )
            .unwrap();

        let a = Memory::new(Galaxy::Codex, "claim A".into());
        let a_id = a.metadata.id;
        store.put(Galaxy::Codex, &a).unwrap();
        let b = Memory::new(Galaxy::Codex, "claim B".into());
        let b_id = b.metadata.id;
        store.put(Galaxy::Codex, &b).unwrap();
        assoc
            .put(
                env,
                &wm_memory::Association::new(a_id, b_id, wm_memory::LinkType::Contradicts, 0.9),
            )
            .unwrap();

        let ctx = DreamContext::new(&store, &assoc);
        let cycle = DreamCycle::new();
        let (inspected, moved) = cycle.validity_sweep_inner(&ctx, true);
        // Only Active memories are inspected (revoked is skipped); the
        // Contradicts edge adjudicates nothing, and the revoked record
        // refuses the Supersede transition — so nothing moves.
        assert_eq!(inspected, 3);
        assert_eq!(moved, 0);
        let validity_of = |id: uuid::Uuid| {
            store
                .get(Galaxy::Codex, id)
                .unwrap()
                .unwrap()
                .metadata
                .validity
        };
        assert!(matches!(
            validity_of(revoked_id),
            wm_core::episodic::ValidityState::Revoked { .. }
        ));
        assert!(validity_of(a_id).is_current());
        assert!(validity_of(b_id).is_current());
    }

    #[test]
    fn dream_phase_names_unique() {
        let phases = DreamPhase::all();
        let names: Vec<&str> = phases.iter().map(|p| p.name()).collect();
        let unique: std::collections::HashSet<_> = names.iter().collect();
        assert_eq!(unique.len(), 12);
    }

    #[test]
    fn dream_phase_has_description() {
        for phase in DreamPhase::all() {
            assert!(!phase.description().is_empty());
        }
    }

    #[test]
    fn dream_cycle_run_completes_all_phases() {
        let (_tmp, store, assoc) = test_ctx();
        let ctx = DreamContext::new(&store, &assoc);
        let mut cycle = DreamCycle::new();
        let result = cycle.run(&ctx);
        assert_eq!(result.phases.len(), 12);
        assert!(result.success);
        assert_eq!(cycle.cycles_completed(), 1);
    }

    #[test]
    fn dream_cycle_should_run_in_theta() {
        let cycle = DreamCycle::new();
        assert!(cycle.should_run(BrainWave::Theta));
    }

    #[test]
    fn dream_cycle_should_not_run_in_gamma() {
        let cycle = DreamCycle::new();
        assert!(!cycle.should_run(BrainWave::Gamma));
    }

    #[test]
    fn dream_cycle_should_not_run_when_already_running() {
        let mut cycle = DreamCycle::new();
        cycle.running = true;
        assert!(!cycle.should_run(BrainWave::Theta));
    }

    #[test]
    fn dream_cycle_last_result_available() {
        let (_tmp, store, assoc) = test_ctx();
        let ctx = DreamContext::new(&store, &assoc);
        let mut cycle = DreamCycle::new();
        cycle.run(&ctx);
        assert!(cycle.last_result().is_some());
        let result = cycle.last_result().unwrap();
        assert_eq!(result.phases.len(), 12);
    }

    #[test]
    fn dream_result_to_json() {
        let (_tmp, store, assoc) = test_ctx();
        let ctx = DreamContext::new(&store, &assoc);
        let mut cycle = DreamCycle::new();
        let result = cycle.run(&ctx);
        let json = result.to_json();
        assert_eq!(json["phases"].as_array().unwrap().len(), 12);
        assert_eq!(json["success"], true);
    }

    #[test]
    fn sleep_consolidation_tracks_turns() {
        let mut sc = SleepConsolidation::new();
        sc.consolidate("uuid-1".into());
        sc.consolidate("uuid-2".into());
        sc.skip();
        assert_eq!(sc.consolidated(), 2);
        assert_eq!(sc.skipped(), 1);
        assert_eq!(sc.ids().len(), 2);
    }

    #[test]
    fn dream_cycle_to_json() {
        let (_tmp, store, assoc) = test_ctx();
        let ctx = DreamContext::new(&store, &assoc);
        let mut cycle = DreamCycle::new();
        cycle.run(&ctx);
        let json = cycle.to_json();
        assert_eq!(json["cycles_completed"], 1);
        assert_eq!(json["running"], false);
    }

    #[test]
    fn dream_cycle_processes_real_memories() {
        let (_tmp, store, assoc) = test_ctx();
        let ctx = DreamContext::new(&store, &assoc);

        // Seed memories across galaxies
        let mem1 = Memory::new(Galaxy::Codex, "Rust memory system with LMDB".into())
            .with_importance(0.8)
            .with_tags(vec!["rust".into(), "memory".into()]);
        let mem2 = Memory::new(Galaxy::Research, "Rust memory LMDB benchmarks".into())
            .with_importance(0.6)
            .with_tags(vec!["rust".into(), "benchmark".into()]);
        let mem3 = Memory::new(Galaxy::Codex, "trivial note".into()).with_importance(0.05);
        let mem4 =
            Memory::new(Galaxy::Sessions, "session handoff important".into()).with_importance(0.7);

        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Research, &mem2).unwrap();
        store.put(Galaxy::Codex, &mem3).unwrap();
        store.put(Galaxy::Sessions, &mem4).unwrap();

        let mut cycle = DreamCycle::new();
        let result = cycle.run(&ctx);

        // All phases should succeed
        assert!(result.success);

        // Triage should have processed memories
        let triage = result
            .phases
            .iter()
            .find(|p| p.phase == DreamPhase::Triage)
            .unwrap();
        assert!(triage.memories_processed >= 4);

        // Consolidation should have transferred the session memory to Codex
        let consol = result
            .phases
            .iter()
            .find(|p| p.phase == DreamPhase::Consolidation)
            .unwrap();
        assert!(
            consol.memories_modified >= 1,
            "consolidation should transfer high-importance memories"
        );

        // Serendipity should have found associations between mem1 and mem2
        let serendipity = result
            .phases
            .iter()
            .find(|p| p.phase == DreamPhase::Serendipity)
            .unwrap();
        assert!(
            serendipity.associations > 0,
            "serendipity should create associations"
        );

        // Decay should have processed and decayed the low-importance memory
        let decay = result
            .phases
            .iter()
            .find(|p| p.phase == DreamPhase::Decay)
            .unwrap();
        assert!(decay.memories_processed >= 4);
        assert!(
            decay.memories_modified >= 1,
            "decay should lower importance of low-score memories"
        );

        // Verify the low-importance memory was decayed (but NOT deleted)
        let still_there = store.get(Galaxy::Codex, mem3.metadata.id).unwrap();
        assert!(still_there.is_some(), "decay must never delete memories");
        let updated = still_there.unwrap();
        assert!(
            updated.metadata.importance < 0.05,
            "importance should have been decayed"
        );
    }

    #[test]
    fn dream_cycle_decay_never_deletes() {
        let (_tmp, store, assoc) = test_ctx();
        let ctx = DreamContext::new(&store, &assoc);

        let mem = Memory::new(Galaxy::Codex, "should not be deleted".into()).with_importance(0.01);
        store.put(Galaxy::Codex, &mem).unwrap();

        let mut cycle = DreamCycle::new();
        cycle.run(&ctx);

        // Memory must still exist
        let still_there = store.get(Galaxy::Codex, mem.metadata.id).unwrap();
        assert!(still_there.is_some());
    }

    #[test]
    fn dream_cycle_consolidation_transfers_to_codex() {
        let (_tmp, store, assoc) = test_ctx();
        let ctx = DreamContext::new(&store, &assoc);

        let session_mem =
            Memory::new(Galaxy::Sessions, "important session handoff".into()).with_importance(0.8);
        store.put(Galaxy::Sessions, &session_mem).unwrap();

        let mut cycle = DreamCycle::new();
        cycle.run(&ctx);

        // The memory should now exist in Codex (via content hash dedup)
        let codex_mems = store.scan(Galaxy::Codex, 100).unwrap();
        let found = codex_mems
            .iter()
            .any(|m| m.content == "important session handoff");
        assert!(
            found,
            "high-importance session memory should be transferred to Codex"
        );
    }

    #[test]
    fn dream_cycle_enrichment_tags_untagged() {
        let (_tmp, store, assoc) = test_ctx();
        let ctx = DreamContext::new(&store, &assoc);

        let mem = Memory::new(Galaxy::Codex, "Rust LMDB memory storage system".into())
            .with_importance(0.5);
        store.put(Galaxy::Codex, &mem).unwrap();

        let mut cycle = DreamCycle::new();
        cycle.run(&ctx);

        // The memory should now have tags
        let updated = store.get(Galaxy::Codex, mem.metadata.id).unwrap().unwrap();
        assert!(
            !updated.metadata.tags.is_empty(),
            "enrichment should add tags to untagged memories"
        );
    }

    #[test]
    fn dream_context_with_imagination() {
        let (_tmp, store, assoc) = test_ctx();
        let wm = wm_bicameral::world_model_from_env();
        let evaluator = wm_bicameral::ScenarioEvaluator::with_defaults();
        let engine = wm_bicameral::ScenarioEngine::with_defaults(wm, evaluator);

        let ctx = DreamContext::new(&store, &assoc).with_imagination(&engine);
        assert!(ctx.imagination.is_some());
    }

    #[test]
    fn dream_cycle_oracle_with_imagination() {
        let (_tmp, store, assoc) = test_ctx();

        // Seed enough memories to create hub patterns
        // We need 5+ memories linked to a central one for spreading activation
        let hub = Memory::new(Galaxy::Codex, "central concept about Rust memory".into())
            .with_importance(0.8);
        store.put(Galaxy::Codex, &hub).unwrap();

        for i in 0..6 {
            let mem = Memory::new(
                Galaxy::Codex,
                format!("related memory {i} about Rust memory management"),
            )
            .with_importance(0.6);
            store.put(Galaxy::Codex, &mem).unwrap();
            // Link to hub
            let assoc_link = wm_memory::Association::new(
                hub.metadata.id,
                mem.metadata.id,
                wm_memory::LinkType::Related,
                0.8,
            );
            assoc.put(store.env(), &assoc_link).unwrap();
        }

        let wm = wm_bicameral::world_model_from_env();
        let evaluator = wm_bicameral::ScenarioEvaluator::with_defaults();
        let engine = wm_bicameral::ScenarioEngine::with_defaults(wm, evaluator);

        let ctx = DreamContext::new(&store, &assoc).with_imagination(&engine);
        let mut cycle = DreamCycle::new();
        let result = cycle.run(&ctx);

        assert!(result.success);
        // Oracle phase should have run with imagination engine
        let oracle_phase = result
            .phases
            .iter()
            .find(|p| p.phase == DreamPhase::Oracle)
            .unwrap();
        assert!(oracle_phase.success);
    }

    // ── S7 distillation (dream-side) ───────────────────────────────────

    /// Seed one session (start + turns) and return the session id.
    fn seed_session(
        store: &MemoryStore,
        title: &str,
        topic: Option<&str>,
        turns: &[(&str, &str, &str)],
    ) -> String {
        let mut start = Memory::new(
            Galaxy::Sessions,
            serde_json::json!({"type": "session_start", "title": title, "user": "lucas"})
                .to_string(),
        );
        start.metadata.tags = vec!["session".into(), "start".into()];
        start.metadata.importance = 0.7;
        store.put(Galaxy::Sessions, &start).unwrap();
        let session_id = start.metadata.id.to_string();
        let mut timestamp = 1_700_000_000_000i64;
        for (role, turn_type, text) in turns {
            let mut tm = Memory::new(
                Galaxy::Sessions,
                serde_json::json!({
                    "type": "session_turn",
                    "session_id": session_id,
                    "sequence": 0,
                    "role": role,
                    "turn_type": turn_type,
                    "importance": 0.7,
                    "content": text,
                    "timestamp": timestamp
                })
                .to_string(),
            );
            timestamp += 1_000;
            tm.metadata.tags = vec![
                "session".into(),
                "turn".into(),
                (*role).into(),
                (*turn_type).into(),
            ];
            if let Some(t) = topic {
                tm.metadata.topic = Some(t.to_string());
            }
            tm.metadata.importance = 0.7;
            store.put(Galaxy::Sessions, &tm).unwrap();
        }
        session_id
    }

    /// ACCEPTANCE (S7): a cross-session topic summary for a real corpus
    /// question is produced by the dream cycle with provenance intact.
    #[test]
    fn s7_distill_cross_session_topic_summary_with_provenance() {
        let (_tmp, store, assoc) = test_ctx();
        let s1 = seed_session(
            &store,
            "distillation pipeline design",
            Some("distillation pipeline"),
            &[
                ("user", "question", "how do we distill across sessions?"),
                ("ai", "decision", "deterministic session-file layer first"),
            ],
        );
        let s2 = seed_session(
            &store,
            "distillation pipeline follow-up",
            Some("distillation pipeline"),
            &[
                ("user", "message", "continue the distillation pipeline work"),
                ("ai", "breakthrough", "yama gates the distillation writes"),
            ],
        );

        let ctx = DreamContext::new(&store, &assoc);
        let mut cycle = DreamCycle::new();
        let result = cycle.run(&ctx);
        assert!(result.success);

        let narrative = result
            .phases
            .iter()
            .find(|p| p.phase == DreamPhase::Narrative)
            .unwrap();
        assert!(narrative.success);
        assert!(
            narrative.memories_modified >= 1,
            "narrative wrote distillates"
        );

        let dreams = store.scan(Galaxy::Dreams, 1_000).unwrap();
        let topic_mem = dreams
            .iter()
            .find(|m| {
                m.content.contains("## distill:topic distillation pipeline")
                    && m.content.contains("Q: What do the sessions say about")
            })
            .expect("cross-session topic summary produced by the dream cycle");

        // Provenance intact: tags bind BOTH source sessions; metadata names
        // the dream as authorship; class is stamped Knowledge; the corpus
        // question anchors the summary.
        assert!(
            topic_mem
                .metadata
                .tags
                .contains(&format!("distill:session:{s1}"))
        );
        assert!(
            topic_mem
                .metadata
                .tags
                .contains(&format!("distill:session:{s2}"))
        );
        assert_eq!(topic_mem.metadata.source, "dream:distill");
        assert_eq!(topic_mem.metadata.agent_id, "dream-cycle");
        assert_eq!(
            topic_mem.metadata.class,
            Some(wm_memory::typology::MemoryClass::Knowledge)
        );
        assert_eq!(
            topic_mem.metadata.topic.as_deref(),
            Some("distillation pipeline")
        );
        assert!(topic_mem.content.contains(&s1) && topic_mem.content.contains(&s2));
        assert!(topic_mem.content.contains("Synthesis (LLM)"));
    }

    /// The deterministic session-file layer: the digest carries the §2
    /// provenance header — id, span, turn counts, tokens/cost (or an
    /// explicit not-tracked disclosure), the dropped-statement, sources.
    #[test]
    fn s7_distill_session_digest_has_provenance_header() {
        let (_tmp, store, assoc) = test_ctx();
        let s1 = seed_session(
            &store,
            "costly work",
            None,
            &[
                ("user", "message", "look into the archive"),
                ("ai", "summary", "found the heritage pattern"),
            ],
        );

        let ctx = DreamContext::new(&store, &assoc);
        let mut cycle = DreamCycle::new();
        let result = cycle.run(&ctx);
        assert!(result.success);

        let dreams = store.scan(Galaxy::Dreams, 1_000).unwrap();
        let digest = dreams
            .iter()
            .find(|m| m.content.contains(&format!("## distill:session {s1}")))
            .expect("session digest written by the dream cycle");
        assert!(digest.content.contains("- title: costly work"));
        assert!(digest.content.contains("- span: "));
        assert!(digest.content.contains("- turns: 2 (user 1, ai 1)"));
        assert!(
            digest
                .content
                .contains("- tokens: not tracked in source records")
        );
        assert!(digest.content.contains("what was dropped: tool payloads"));
        assert!(digest.content.contains("- sources: "));
        assert!(digest.content.contains("found the heritage pattern"));
    }

    /// Idempotency: unchanged evidence must not churn — the second run
    /// skips topics (fingerprint) and dedups digests/index (content hash).
    #[test]
    fn s7_narrative_second_run_skips_unchanged_evidence() {
        let (_tmp, store, assoc) = test_ctx();
        seed_session(
            &store,
            "distill it",
            Some("distillation"),
            &[
                ("user", "message", "distillation question one"),
                ("ai", "answer", "distillation answer one"),
            ],
        );
        seed_session(
            &store,
            "distill it more",
            Some("distillation"),
            &[
                ("user", "message", "distillation question two"),
                ("ai", "decision", "distillation answer two"),
            ],
        );

        let ctx = DreamContext::new(&store, &assoc);
        let mut cycle = DreamCycle::new();
        cycle.run(&ctx);
        let count = |store: &MemoryStore| {
            store
                .scan(Galaxy::Dreams, 1_000)
                .unwrap()
                .iter()
                .filter(|m| m.content.starts_with("## distill:"))
                .count()
        };
        let after_first = count(&store);
        assert!(after_first >= 4, "2 digests + topic + index: {after_first}");

        cycle.run(&ctx);
        assert_eq!(
            count(&store),
            after_first,
            "second run with unchanged evidence writes nothing new"
        );
    }

    /// Yama rate-limiting (the honest form): dream-phase writes consume
    /// the shared write budget; a blocking verdict stops the phase with
    /// the reason disclosed — and a governance stop is not a phase failure.
    #[test]
    fn s7_yama_budget_blocks_distillation_disclosed() {
        let (_tmp, store, assoc) = test_ctx();
        seed_session(
            &store,
            "one",
            Some("shared"),
            &[("user", "message", "a"), ("ai", "message", "b")],
        );
        seed_session(
            &store,
            "two",
            Some("shared"),
            &[("user", "message", "c"), ("ai", "message", "d")],
        );
        seed_session(
            &store,
            "three",
            Some("shared"),
            &[("user", "message", "e"), ("ai", "message", "f")],
        );

        // Theta quarters the write budget: 4/min * 1.0 health / 4 = 1.
        let rules = wm_governance::ResourceRules::new(wm_governance::ResourceRulesConfig {
            max_writes_per_minute: 4,
            ..wm_governance::ResourceRulesConfig::default()
        });
        let ctx = DreamContext::new(&store, &assoc).with_yama(
            &rules,
            wm_governance::Homeostasis::default(),
            BrainWave::Theta,
        );
        let mut cycle = DreamCycle::new();
        let result = cycle.run(&ctx);
        assert!(result.success);

        let narrative = result
            .phases
            .iter()
            .find(|p| p.phase == DreamPhase::Narrative)
            .unwrap();
        assert!(narrative.success);
        assert_eq!(
            narrative.memories_modified, 1,
            "one write through the budget, then Yama blocks"
        );
        assert!(
            narrative.notes.contains("yama blocked"),
            "blocking verdict disclosed: {}",
            narrative.notes
        );
    }

    /// Yama admission semantics on the dream context: allow → novelty
    /// flag (non-blocking) on repeats; no Yama attached → always allow.
    #[test]
    fn s7_yama_admit_allow_flag_and_unhooked() {
        let (_tmp, store, assoc) = test_ctx();
        let rules = wm_governance::ResourceRules::new(wm_governance::ResourceRulesConfig {
            max_repeats: 1,
            novelty_window: 10,
            ..wm_governance::ResourceRulesConfig::default()
        });
        let ctx = DreamContext::new(&store, &assoc).with_yama(
            &rules,
            wm_governance::Homeostasis::default(),
            BrainWave::Theta,
        );
        assert_eq!(
            ctx.yama_admit("dream.distill.topic", "key-1"),
            YamaDecision::Allow
        );
        assert!(
            matches!(
                ctx.yama_admit("dream.distill.topic", "key-1"),
                YamaDecision::Flag(_)
            ),
            "repeat is a novelty flag, not a block"
        );

        let plain = DreamContext::new(&store, &assoc);
        assert_eq!(plain.yama_admit("any", "thing"), YamaDecision::Allow);
    }

    /// ACCEPTANCE (S7): LearnedDreamCycle records phase effectiveness for
    /// the Narrative distillation the same way it does for every phase.
    #[test]
    fn s7_learned_dream_cycle_records_narrative_effectiveness() {
        let (_tmp, store, assoc) = test_ctx();
        seed_session(
            &store,
            "learned effectiveness",
            Some("learning"),
            &[("user", "message", "question"), ("ai", "answer", "answer")],
        );
        seed_session(
            &store,
            "learned effectiveness two",
            Some("learning"),
            &[
                ("user", "message", "question two"),
                ("ai", "answer", "answer two"),
            ],
        );

        let ctx = DreamContext::new(&store, &assoc);
        let mut cycle = DreamCycle::new().with_learned(wm_core::LearnedDreamCycle::new());
        cycle.run(&ctx);

        let narrative_idx = DreamPhase::all()
            .iter()
            .position(|p| *p == DreamPhase::Narrative)
            .unwrap() as u8;
        let eff = cycle
            .learned()
            .unwrap()
            .effectiveness(narrative_idx)
            .expect("narrative effectiveness recorded");
        assert!(eff.runs >= 1);
        assert!(eff.useful_results >= 1, "distillation produced memories");
    }
}
