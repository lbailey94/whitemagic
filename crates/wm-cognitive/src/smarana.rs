//! Autonomous Smarana — Continuous Spaced-Repetition, Hebbian Synaptic
//! Consolidation, and Gist Distillation (WhiteMagic v9.2).
//!
//! # Architecture & Cognitive Foundations
//!
//! **Smarana** (Sanskrit: *स्मरण*, "memory, mindfulness, recollection") is the
//! self-governing memory consolidation and active-recall subsystem of WhiteMagic.
//! While v9.1 implemented an embryonic recall/miss counter tied to tool call
//! outcomes, v9.2 elevates Smarana to an autonomous cognitive engine operating
//! along four primary axes:
//!
//! 1. **Continuous Ebbinghaus Spaced-Repetition (DSR Model)**:
//!    Models memory retrievability via exponential forgetting curves:
//!    $$R(t, S) = \exp\left(-\frac{\ln(10/9) \cdot t}{S}\right)$$
//!    where $S$ is memory stability (half-life in days to reach 90% retrievability),
//!    $t$ is elapsed time, and $D \in [0.0, 1.0]$ is intrinsic difficulty.
//!    Upon active testing, stability updates adhere to the *Spacing Effect*
//!    (Bjork's "Desirable Difficulties"): successfully retrieving a memory when
//!    its retrievability is low yields an exponential stability boost:
//!    $$\Delta S = S \cdot c_1 \cdot (1 - 0.5 D) \cdot \exp(c_2 (1 - R))$$
//!
//! 2. **Hebbian Synaptic Consolidation**:
//!    "Concepts that fire together, wire together." Memories co-retrieved or
//!    co-activated in reasoning contexts undergo synaptic link reinforcement
//!    governed by soft-saturation plasticity (Oja / BCM rule):
//!    $$\Delta w = \eta \cdot \text{salience} \cdot (1 - w)$$
//!    Unlinked memories that co-activate across multiple turns trigger autonomous
//!    *de-novo* association formation. Idle synapses undergo exponential half-life
//!    decay and pruning.
//!
//! 3. **Alchemical Dream Cycle Phase Integration**:
//!    Ties Ebbinghaus retention and Hebbian connectivity directly to the four
//!    alchemical transmutations across the 12 DreamPhases:
//!    - **Nigredo (Decay)**: Dissolution of decaying ephemera with $R < R_{\text{decay}}$
//!      and low stability (DreamPhase::Decay, DreamPhase::Triage).
//!    - **Albedo (Sublimation)**: Stripping raw formatting/timestamp noise and
//!      purifying core semantic invariants into 5D/16D spaces (DreamPhase::Kaizen,
//!      DreamPhase::Serendipity).
//!    - **Citrinitas (Compression)**: Distilling strongly connected Hebbian clusters
//!      into compact Gist representations (DreamPhase::Consolidation, DreamPhase::Constellation).
//!    - **Rubedo (Crystallization)**: Solidifying hyper-stable ($S \ge 14\text{d}$),
//!      high-repetition invariants into protected Codex memory with indelible
//!      minimum association strengths (DreamPhase::Governance, DreamPhase::Harmonize).
//!
//! 4. **Gist Vector Distillation (Fuzzy-Trace Theory)**:
//!    Distills clusters of episodic memories into dual representations:
//!    - *Verbatim trace*: detailed, concrete, rapidly decaying.
//!    - *Gist trace*: abstract semantic invariant, topological 5D centroid,
//!      16D Citta resonance imprint, and relational predicates. Gist stability
//!      substantially outlasts individual verbatim memories.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use uuid::Uuid;
use wm_core::{Coordinate5D, Galaxy, Result};
use wm_memory::{Association, AssociationStore, LinkType, Memory, MemoryStore, MemoryType, Tier};

use crate::citta::CittaVector;

/// Constant for Ebbinghaus exponential decay: ln(10/9) ≈ 0.10536051565.
/// Ensures R(S, S) = exp(-0.10536) = 0.90 (90% retrievability at t = Stability).
pub const EBBINGHAUS_DECAY_CONSTANT: f32 = 0.105_360_52;

// ── Configuration ─────────────────────────────────────────────────────────

/// Configuration parameters for the Autonomous Smarana engine.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SmaranaConfig {
    /// Target retrievability threshold for scheduled reviews (default: 0.85).
    pub target_retrievability: f32,
    /// Default initial stability for newly observed memories in days (default: 1.0).
    pub default_stability_days: f32,
    /// Default difficulty in [0.0, 1.0] (default: 0.3).
    pub default_difficulty: f32,
    /// Minimum stability clamp in days (default: 0.1).
    pub min_stability_days: f32,
    /// Maximum stability clamp in days (default: 3650.0 = 10 years).
    pub max_stability_days: f32,
    /// Multiplier applied to stability upon recall lapse/failure (default: 0.3).
    pub lapse_multiplier: f32,
    /// Spacing effect exponential coefficient c2 (default: 1.5).
    pub spacing_bonus_factor: f32,
    /// Hebbian synaptic learning rate eta (default: 0.10).
    pub hebbian_learning_rate: f32,
    /// Minimum co-activation count to synthesize a new association (default: 2).
    pub coactivation_threshold: u32,
    /// Half-life in days for synaptic association decay (default: 90.0).
    pub association_half_life_days: f32,
    /// Synaptic pruning weight threshold (default: 0.08).
    pub synaptic_prune_threshold: f32,
    /// Ebbinghaus retrievability threshold below which Nigredo decay triggers (default: 0.35).
    pub nigredo_decay_threshold: f32,
    /// Crystallization minimum stability in days (default: 14.0).
    pub crystallization_min_stability_days: f32,
    /// Crystallization minimum repetition count (default: 3).
    pub crystallization_min_reps: u32,
    /// Crystallization minimum retrievability (default: 0.80).
    pub crystallization_min_retrievability: f32,
    /// Maximum cluster size for gist distillation (default: 8).
    pub max_gist_cluster_size: usize,
}

impl Default for SmaranaConfig {
    fn default() -> Self {
        Self {
            target_retrievability: 0.85,
            default_stability_days: 1.0,
            default_difficulty: 0.3,
            min_stability_days: 0.1,
            max_stability_days: 3650.0,
            lapse_multiplier: 0.3,
            spacing_bonus_factor: 1.5,
            hebbian_learning_rate: 0.10,
            coactivation_threshold: 2,
            association_half_life_days: 90.0,
            synaptic_prune_threshold: 0.08,
            nigredo_decay_threshold: 0.35,
            crystallization_min_stability_days: 14.0,
            crystallization_min_reps: 3,
            crystallization_min_retrievability: 0.80,
            max_gist_cluster_size: 8,
        }
    }
}

// ── Spaced Repetition (DSR Model) ─────────────────────────────────────────

/// Outcome of a spaced-repetition testing event.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ReviewOutcome {
    /// Memory ID evaluated.
    pub memory_id: Uuid,
    /// Recall success (grade >= 0.6).
    pub success: bool,
    /// Test grade in [0.0, 1.0].
    pub grade: f32,
    /// Retrievability immediately before review.
    pub prior_retrievability: f32,
    /// Previous stability in days.
    pub prior_stability: f32,
    /// Updated stability in days.
    pub new_stability: f32,
    /// Previous difficulty in [0.0, 1.0].
    pub prior_difficulty: f32,
    /// Updated difficulty in [0.0, 1.0].
    pub new_difficulty: f32,
    /// Total repetitions completed.
    pub reps: u32,
    /// Total lapses recorded.
    pub lapses: u32,
}

/// A tracked memory item within the continuous spaced-repetition registry.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RepetitionItem {
    /// Memory UUID.
    pub memory_id: Uuid,
    /// Stability S (days until retrievability decays to 0.90).
    pub stability: f32,
    /// Difficulty D in [0.0, 1.0].
    pub difficulty: f32,
    /// Successful active recall count.
    pub reps: u32,
    /// Recall lapse count.
    pub lapses: u32,
    /// Timestamp of the last review or initial registration.
    pub last_reviewed_at: DateTime<Utc>,
    /// Retrievability recorded at last review.
    pub last_retrievability: f32,
}

impl RepetitionItem {
    /// Create a new repetition item with initial parameters.
    #[must_use]
    pub fn new(memory_id: Uuid, initial_stability: f32, initial_difficulty: f32) -> Self {
        let now = Utc::now();
        Self {
            memory_id,
            stability: initial_stability.max(0.1),
            difficulty: initial_difficulty.clamp(0.05, 1.0),
            reps: 0,
            lapses: 0,
            last_reviewed_at: now,
            last_retrievability: 1.0,
        }
    }

    /// Compute current Ebbinghaus retrievability R(t, S) at a given timestamp.
    ///
    /// $$R(t, S) = \exp\left(-\frac{\ln(10/9) \cdot t}{S}\right)$$
    #[must_use]
    pub fn retrievability(&self, now: DateTime<Utc>) -> f32 {
        let elapsed_seconds = (now - self.last_reviewed_at).num_seconds() as f32;
        let elapsed_days = (elapsed_seconds / 86400.0).max(0.0);
        if elapsed_days <= 0.0 {
            return 1.0;
        }
        let exponent = EBBINGHAUS_DECAY_CONSTANT * (elapsed_days / self.stability.max(0.01));
        (-exponent).exp().clamp(0.0, 1.0)
    }

    /// Whether this memory is due for active spaced-repetition testing.
    #[must_use]
    pub fn is_due(&self, target_retrievability: f32, now: DateTime<Utc>) -> bool {
        self.retrievability(now) <= target_retrievability
    }

    /// Record an active review outcome and update stability & difficulty.
    pub fn record_review(
        &mut self,
        grade: f32,
        config: &SmaranaConfig,
        now: DateTime<Utc>,
    ) -> ReviewOutcome {
        let prior_retrievability = self.retrievability(now);
        let prior_stability = self.stability;
        let prior_difficulty = self.difficulty;
        let grade_clamped = grade.clamp(0.0, 1.0);
        let success = grade_clamped >= 0.60;

        if success {
            self.reps += 1;
            // Spacing effect: Desirable difficulties yield higher stability growth
            // when recall occurs at lower retrievability (high forgetting delay).
            let spacing_factor =
                (config.spacing_bonus_factor * (1.0 - prior_retrievability)).exp();
            let diff_factor = (1.0 - 0.5 * self.difficulty).max(0.1);
            let delta_stability =
                self.stability * 1.2 * diff_factor * spacing_factor * grade_clamped;

            self.stability = (self.stability + delta_stability)
                .clamp(config.min_stability_days, config.max_stability_days);
            self.difficulty = (self.difficulty - 0.10 * (grade_clamped - 0.60)).clamp(0.05, 1.0);
        } else {
            self.lapses += 1;
            // Penalty on lapse
            self.stability = (self.stability * config.lapse_multiplier)
                .clamp(config.min_stability_days, config.max_stability_days);
            self.difficulty = (self.difficulty + 0.20).clamp(0.05, 1.0);
        }

        self.last_reviewed_at = now;
        self.last_retrievability = self.retrievability(now);

        ReviewOutcome {
            memory_id: self.memory_id,
            success,
            grade: grade_clamped,
            prior_retrievability,
            prior_stability,
            new_stability: self.stability,
            prior_difficulty,
            new_difficulty: self.difficulty,
            reps: self.reps,
            lapses: self.lapses,
        }
    }
}

/// Registry managing spaced-repetition schedules across all memories.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SpacedRepetitionTracker {
    items: HashMap<Uuid, RepetitionItem>,
}

impl SpacedRepetitionTracker {
    /// Create an empty tracker.
    #[must_use]
    pub fn new() -> Self {
        Self {
            items: HashMap::new(),
        }
    }

    /// Register a memory if not present, or return existing item.
    pub fn register_or_get(
        &mut self,
        memory_id: Uuid,
        config: &SmaranaConfig,
    ) -> &mut RepetitionItem {
        self.items.entry(memory_id).or_insert_with(|| {
            RepetitionItem::new(
                memory_id,
                config.default_stability_days,
                config.default_difficulty,
            )
        })
    }

    /// Get repetition item by memory ID.
    #[must_use]
    pub fn get(&self, memory_id: &Uuid) -> Option<&RepetitionItem> {
        self.items.get(memory_id)
    }

    /// Get mutable repetition item by memory ID.
    pub fn get_mut(&mut self, memory_id: &Uuid) -> Option<&mut RepetitionItem> {
        self.items.get_mut(memory_id)
    }

    /// Compute current retrievability for a memory ID (returns 1.0 if untracked).
    #[must_use]
    pub fn retrievability(&self, memory_id: &Uuid, now: DateTime<Utc>) -> f32 {
        self.items.get(memory_id).map_or(1.0, |i| i.retrievability(now))
    }

    /// Record a review outcome for a memory.
    pub fn record_review(
        &mut self,
        memory_id: Uuid,
        grade: f32,
        config: &SmaranaConfig,
        now: DateTime<Utc>,
    ) -> ReviewOutcome {
        let item = self.register_or_get(memory_id, config);
        item.record_review(grade, config, now)
    }

    /// List all memory IDs due for active testing.
    #[must_use]
    pub fn due_items(&self, target_retrievability: f32, now: DateTime<Utc>) -> Vec<Uuid> {
        self.items
            .values()
            .filter(|i| i.is_due(target_retrievability, now))
            .map(|i| i.memory_id)
            .collect()
    }

    /// Compute mean retrievability across all tracked memories.
    #[must_use]
    pub fn mean_retrievability(&self, now: DateTime<Utc>) -> f32 {
        if self.items.is_empty() {
            return 1.0;
        }
        let sum: f32 = self.items.values().map(|i| i.retrievability(now)).sum();
        sum / (self.items.len() as f32)
    }

    /// Compute mean stability across all tracked memories (in days).
    #[must_use]
    pub fn mean_stability(&self) -> f32 {
        if self.items.is_empty() {
            return 1.0;
        }
        let sum: f32 = self.items.values().map(|i| i.stability).sum();
        sum / (self.items.len() as f32)
    }

    /// Total tracked memory count.
    #[must_use]
    pub fn len(&self) -> usize {
        self.items.len()
    }

    /// Whether registry is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }
}

// ── Hebbian Associative Reinforcement ─────────────────────────────────────

/// Metadata tracking co-activation history between a pair of memories.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoActivationRecord {
    /// Number of co-activation events.
    pub count: u32,
    /// Timestamp of most recent co-activation.
    pub last_coactivated_at: DateTime<Utc>,
    /// Accumulated context salience.
    pub cumulative_salience: f32,
}

/// Report summarizing synaptic consolidation actions.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HebbianConsolidationReport {
    /// Associations whose weights were strengthened.
    pub associations_reinforced: usize,
    /// New associations created de-novo from frequent co-activations.
    pub associations_created: usize,
    /// Total co-activation events processed.
    pub coactivations_processed: usize,
}

/// Report summarizing synaptic pruning and decay.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SynapticPruneReport {
    /// Number of associations pruned due to low weight.
    pub associations_pruned: usize,
    /// Number of associations decayed.
    pub associations_decayed: usize,
}

/// In-memory Hebbian plasticity engine.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HebbianReinforcer {
    /// Co-activation ledger for memory pairs: (min(u, v), max(u, v)) -> stats
    coactivations: HashMap<(Uuid, Uuid), CoActivationRecord>,
}

impl HebbianReinforcer {
    /// Create a new Hebbian reinforcer.
    #[must_use]
    pub fn new() -> Self {
        Self {
            coactivations: HashMap::new(),
        }
    }

    /// Canonical ordering for unordered pairs of UUIDs.
    pub const fn canonical_pair(u: Uuid, v: Uuid) -> (Uuid, Uuid) {
        if u.as_u128() <= v.as_u128() {
            (u, v)
        } else {
            (v, u)
        }
    }

    /// Record a batch of co-activated memories (e.g. retrieved together in context).
    pub fn record_coactivation_batch(
        &mut self,
        memory_ids: &[Uuid],
        salience: f32,
        now: DateTime<Utc>,
    ) {
        if memory_ids.len() < 2 {
            return;
        }
        let salience_clamped = salience.clamp(0.1, 1.0);
        for i in 0..memory_ids.len() {
            for j in (i + 1)..memory_ids.len() {
                let pair = Self::canonical_pair(memory_ids[i], memory_ids[j]);
                if pair.0 == pair.1 {
                    continue;
                }
                let record = self.coactivations.entry(pair).or_insert(CoActivationRecord {
                    count: 0,
                    last_coactivated_at: now,
                    cumulative_salience: 0.0,
                });
                record.count += 1;
                record.last_coactivated_at = now;
                record.cumulative_salience += salience_clamped;
            }
        }
    }

    /// Execute synaptic consolidation across the AssociationStore.
    pub fn consolidate_synapses(
        &mut self,
        store: &MemoryStore,
        assoc_store: &AssociationStore,
        config: &SmaranaConfig,
        now: DateTime<Utc>,
    ) -> Result<HebbianConsolidationReport> {
        let mut report = HebbianConsolidationReport::default();
        let env = store.env();
        let learning_rate = config.hebbian_learning_rate;

        // Drain pairs that have met the co-activation threshold
        let mut ready_pairs = Vec::new();
        for (&(u, v), record) in &self.coactivations {
            if record.count >= config.coactivation_threshold {
                ready_pairs.push((u, v, record.clone()));
            }
        }

        report.coactivations_processed = ready_pairs.len();

        for (u, v, record) in ready_pairs {
            let mean_salience = (record.cumulative_salience / (record.count as f32)).clamp(0.1, 1.0);

            // Check if association already exists in either direction
            let existing_uv = assoc_store.get(env, u, v)?;
            let existing_vu = assoc_store.get(env, v, u)?;

            if let Some(mut assoc) = existing_uv {
                // Hebbian soft saturation: delta_w = eta * salience * (1 - w)
                let boost = learning_rate * mean_salience * (1.0 - assoc.weight);
                assoc.weight = (assoc.weight + boost).clamp(0.0, 1.0);
                assoc.co_activation_count += record.count;
                assoc.last_activated_at = now;
                assoc_store.put(env, &assoc)?;
                report.associations_reinforced += 1;
            } else if let Some(mut assoc) = existing_vu {
                let boost = learning_rate * mean_salience * (1.0 - assoc.weight);
                assoc.weight = (assoc.weight + boost).clamp(0.0, 1.0);
                assoc.co_activation_count += record.count;
                assoc.last_activated_at = now;
                assoc_store.put(env, &assoc)?;
                report.associations_reinforced += 1;
            } else {
                // Synthesize de-novo association
                let initial_weight = (0.35 * learning_rate * mean_salience + 0.20).clamp(0.10, 0.60);
                let new_assoc = Association {
                    source: u,
                    target: v,
                    association_type: LinkType::Related.as_str().to_string(),
                    weight: initial_weight,
                    created_at: now,
                    link_type: LinkType::Related,
                    co_activation_count: record.count,
                    last_activated_at: now,
                    decay_half_life_days: config.association_half_life_days,
                };
                assoc_store.put(env, &new_assoc)?;
                report.associations_created += 1;
            }

            // Remove from staging after consolidation
            self.coactivations.remove(&(u, v));
        }

        Ok(report)
    }

    /// Apply synaptic decay to unreinforced associations and prune weak links.
    pub fn decay_and_prune(
        &self,
        store: &MemoryStore,
        assoc_store: &AssociationStore,
        config: &SmaranaConfig,
        now: DateTime<Utc>,
    ) -> Result<SynapticPruneReport> {
        let mut report = SynapticPruneReport::default();
        let env = store.env();

        // Scan all associations by iterating across galaxies
        for galaxy in Galaxy::all() {
            let mems = match store.scan(galaxy, 5_000) {
                Ok(m) => m,
                Err(_) => continue,
            };
            for mem in mems {
                let outgoing = assoc_store.find_from(env, mem.metadata.id)?;
                for mut assoc in outgoing {
                    let prev_weight = assoc.weight;
                    assoc.decay(now);
                    if assoc.weight < prev_weight {
                        report.associations_decayed += 1;
                    }

                    if assoc.should_prune(config.synaptic_prune_threshold) {
                        assoc_store.delete(env, assoc.source, assoc.target)?;
                        report.associations_pruned += 1;
                    } else if (assoc.weight - prev_weight).abs() > 0.001 {
                        assoc_store.put(env, &assoc)?;
                    }
                }
            }
        }

        Ok(report)
    }

    /// Number of active un-consolidated co-activation pairs tracked.
    #[must_use]
    pub fn pending_pairs(&self) -> usize {
        self.coactivations.len()
    }
}

// ── Alchemical Dream Cycle Integration ────────────────────────────────────

/// The four grand alchemical stages of memory transmutation in WhiteMagic.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum AlchemicalStage {
    /// Nigredo: Dissolution & mindful decay of sub-retention ephemera.
    Decay,
    /// Albedo: Purification & sublimation of noise into pure invariants.
    Sublimation,
    /// Citrinitas: Distillation & compression of co-activated clusters into gists.
    Compression,
    /// Rubedo: Indelible crystallization of high-stability memories into Codex.
    Crystallization,
}

impl AlchemicalStage {
    /// Human-readable name.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Decay => "decay (nigredo)",
            Self::Sublimation => "sublimation (albedo)",
            Self::Compression => "compression (citrinitas)",
            Self::Crystallization => "crystallization (rubedo)",
        }
    }
}

/// Distribution of memories across the 4 alchemical stages.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct AlchemicalDistribution {
    /// Nigredo count
    pub decay: usize,
    /// Albedo count
    pub sublimation: usize,
    /// Citrinitas count
    pub compression: usize,
    /// Rubedo count
    pub crystallization: usize,
    /// Total categorized
    pub total: usize,
}

/// Bridge classifying memories and driving alchemical phase execution.
pub struct AlchemicalPhaseBridge;

impl AlchemicalPhaseBridge {
    /// Classify a memory into an alchemical stage based on retention and topological metrics.
    #[must_use]
    pub fn classify(
        mem: &Memory,
        rep: Option<&RepetitionItem>,
        assoc_count: usize,
        config: &SmaranaConfig,
        now: DateTime<Utc>,
    ) -> AlchemicalStage {
        // Hard-protected memories belong to Rubedo (Crystallization)
        if mem.metadata.is_protected {
            return AlchemicalStage::Crystallization;
        }

        let (retrievability, stability, reps) = if let Some(item) = rep {
            (item.retrievability(now), item.stability, item.reps)
        } else {
            let elapsed_days = (now - mem.metadata.accessed_at).num_seconds() as f32 / 86400.0;
            let s = mem.metadata.half_life_days.max(1.0);
            let r = (-EBBINGHAUS_DECAY_CONSTANT * elapsed_days / s).exp().clamp(0.0, 1.0);
            (r, s, mem.metadata.recall_count as u32)
        };

        // Rubedo (Crystallization): high stability, multiple successful reviews, high importance
        if stability >= config.crystallization_min_stability_days
            && reps >= config.crystallization_min_reps
            && retrievability >= config.crystallization_min_retrievability
            && mem.metadata.importance >= 0.70
        {
            return AlchemicalStage::Crystallization;
        }

        // Nigredo (Decay): low retrievability and low stability
        if retrievability < config.nigredo_decay_threshold && stability < 5.0 {
            return AlchemicalStage::Decay;
        }

        // Citrinitas (Compression): strong connectivity and acceptable retrievability
        if retrievability >= 0.50 && assoc_count >= 2 {
            return AlchemicalStage::Compression;
        }

        // Albedo (Sublimation): default purification state
        AlchemicalStage::Sublimation
    }
}

// ── Gist Vector Distillation ──────────────────────────────────────────────

/// High-density semantic invariant distilled from a cluster of memories.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GistVector {
    /// Unique identifier of the gist vector.
    pub id: Uuid,
    /// Source memory IDs consolidated into this gist.
    pub source_memory_ids: Vec<Uuid>,
    /// Holographic 5D coordinate centroid.
    pub centroid_5d: Coordinate5D,
    /// 16D Citta vector consciousness imprint.
    pub citta_imprint: [f32; 16],
    /// Key invariant keywords extracted from constituent memories.
    pub salient_keywords: Vec<String>,
    /// Core relational predicates / invariants.
    pub core_predicates: Vec<String>,
    /// Ultra-dense abstract summary text.
    pub abstract_summary: String,
    /// Stability score of the distilled gist in days (surpasses constituent items).
    pub stability_days: f32,
    /// Compression ratio (raw character length / gist character length).
    pub compression_ratio: f32,
    /// Timestamp when distillation occurred.
    pub created_at: DateTime<Utc>,
}

/// Distillation engine implementing Fuzzy-Trace Theory.
pub struct GistDistiller;

impl GistDistiller {
    /// Distill a cluster of episodic memories into a unified GistVector.
    #[must_use]
    pub fn distill_cluster(
        memories: &[Memory],
        reps: &[Option<&RepetitionItem>],
        citta: &CittaVector,
    ) -> Option<GistVector> {
        if memories.is_empty() {
            return None;
        }

        let now = Utc::now();
        let n = memories.len() as f32;

        // 1. Calculate 5D Holographic Centroid
        let avg_x = memories.iter().map(|m| m.metadata.coord5d.x).sum::<f32>() / n;
        let avg_y = memories.iter().map(|m| m.metadata.coord5d.y).sum::<f32>() / n;
        let avg_z = memories.iter().map(|m| m.metadata.coord5d.z).sum::<f32>() / n;
        let avg_w = memories.iter().map(|m| m.metadata.coord5d.w).sum::<f32>() / n;
        let avg_v = memories.iter().map(|m| m.metadata.coord5d.v).sum::<f32>() / n;
        let centroid_5d = Coordinate5D::new(avg_x, avg_y, avg_z, avg_w, avg_v);

        // 2. Extract 16D Citta Imprint
        let mut citta_imprint = [0.5f32; 16];
        for i in 0..16 {
            citta_imprint[i] = citta.get(i);
        }

        // 3. Extract Salient Keywords (term frequency across cluster)
        let mut word_counts: HashMap<String, usize> = HashMap::new();
        let stop_words: HashSet<&'static str> = [
            "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by", "from",
            "is", "are", "was", "were", "this", "that", "it", "of", "as", "be", "have", "has",
        ]
        .into_iter()
        .collect();

        let mut total_raw_chars = 0;
        for mem in memories {
            total_raw_chars += mem.content.len();
            for word in mem.content.split_whitespace() {
                let clean: String = word
                    .to_lowercase()
                    .chars()
                    .filter(|c| c.is_alphanumeric())
                    .collect();
                if clean.len() >= 4 && !stop_words.contains(clean.as_str()) {
                    *word_counts.entry(clean).or_insert(0) += 1;
                }
            }
        }

        let mut sorted_words: Vec<(String, usize)> = word_counts.into_iter().collect();
        sorted_words.sort_by(|a, b| b.1.cmp(&a.1));
        let salient_keywords: Vec<String> = sorted_words
            .into_iter()
            .take(6)
            .map(|(w, _)| w)
            .collect();

        // 4. Extract Core Predicates / Sentences
        let mut core_predicates = Vec::new();
        for mem in memories {
            for sentence in mem.content.split(['.', '\n', ';']) {
                let trimmed = sentence.trim();
                if trimmed.len() >= 15 && trimmed.len() <= 120 {
                    let has_keyword = salient_keywords.iter().any(|k| trimmed.to_lowercase().contains(k));
                    if has_keyword && !core_predicates.contains(&trimmed.to_string()) {
                        core_predicates.push(trimmed.to_string());
                        if core_predicates.len() >= 3 {
                            break;
                        }
                    }
                }
            }
            if core_predicates.len() >= 3 {
                break;
            }
        }

        // 5. Synthesize Abstract Summary
        let summary_body = if core_predicates.is_empty() {
            format!("Distilled cluster of {} memories around concepts: {}", memories.len(), salient_keywords.join(", "))
        } else {
            core_predicates.join(". ")
        };
        let abstract_summary = format!("[Gist Distillation]: {}", summary_body);

        // 6. Compute Stability (Gist stability exceeds constituent episodic items)
        let max_constituent_stability = reps
            .iter()
            .flatten()
            .map(|r| r.stability)
            .fold(1.0f32, f32::max);
        let stability_days = (max_constituent_stability * (1.0 + 0.25 * (n + 1.0).ln())).clamp(1.0, 3650.0);

        // 7. Compression Ratio
        let gist_len = abstract_summary.len().max(1);
        let compression_ratio = (total_raw_chars as f32 / gist_len as f32).max(1.0);

        Some(GistVector {
            id: Uuid::new_v4(),
            source_memory_ids: memories.iter().map(|m| m.metadata.id).collect(),
            centroid_5d,
            citta_imprint,
            salient_keywords,
            core_predicates,
            abstract_summary,
            stability_days,
            compression_ratio,
            created_at: now,
        })
    }

    /// Convert a GistVector into a stored Memory entity.
    #[must_use]
    pub fn to_memory(gist: &GistVector, target_galaxy: Galaxy) -> Memory {
        let mut mem = Memory::new(target_galaxy, gist.abstract_summary.clone());
        mem.metadata.memory_type = MemoryType::Symbolic;
        mem.metadata.tier = Tier::Semantic;
        mem.metadata.importance = 0.85;
        mem.metadata.half_life_days = gist.stability_days;
        mem.metadata.coord5d = gist.centroid_5d.clone();
        mem.metadata.tags = vec![
            "gist".to_string(),
            "distillation".to_string(),
            "alchemical:citrinitas".to_string(),
        ];
        for kw in &gist.salient_keywords {
            mem.metadata.tags.push(format!("kw:{}", kw));
        }
        mem
    }
}

// ── Active Recall Probing Engine ──────────────────────────────────────────

/// Types of active recall probes executed by Smarana.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ProbeKind {
    /// Cloze / Associative Probe: Predict target memory given source and link type.
    AssociativeCloze {
        source_id: Uuid,
        target_id: Uuid,
        link_type: LinkType,
    },
    /// Gist Verification Probe: Retrieve target memory given distilled gist cues.
    GistVerification {
        memory_id: Uuid,
        query_cue: String,
    },
    /// Retention Check Probe: Spaced-repetition probe testing due item.
    RetentionCheck {
        memory_id: Uuid,
        predicted_retrievability: f32,
    },
}

/// An active recall probe generated by Autonomous Smarana.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SmaranaProbe {
    /// Probe UUID.
    pub id: Uuid,
    /// Kind of probe.
    pub kind: ProbeKind,
    /// Primary memory ID under test.
    pub memory_id: Uuid,
    /// Timestamp when probe was generated.
    pub created_at: DateTime<Utc>,
    /// Expected max retrieval latency in ms.
    pub expected_latency_ms: u64,
}

/// Result of evaluating an active recall probe.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProbeResult {
    /// Probe UUID.
    pub probe_id: Uuid,
    /// Memory ID evaluated.
    pub memory_id: Uuid,
    /// Whether recall succeeded.
    pub success: bool,
    /// Recall accuracy grade in [0.0, 1.0].
    pub grade: f32,
    /// Actual latency in milliseconds.
    pub latency_ms: u64,
    /// Calibration error |R_predicted - grade|.
    pub calibration_error: f32,
}

// ── Autonomous Smarana Orchestrator ───────────────────────────────────────

/// Report summarizing an alchemical decay pass.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AlchemicalDecayReport {
    /// Total memories evaluated.
    pub evaluated: usize,
    /// Memories decayed via Ebbinghaus curve.
    pub decayed: usize,
    /// Memories preserved.
    pub preserved: usize,
}

/// Report summarizing crystallization into Codex.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CrystallizationReport {
    /// Memories promoted to permanent tier.
    pub crystallized: usize,
}

/// Report summarizing Gist Distillation pass.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct GistDistillationReport {
    /// Clusters processed.
    pub clusters_distilled: usize,
    /// Gist memories created.
    pub gists_created: usize,
    /// Average compression ratio achieved.
    pub avg_compression_ratio: f32,
}

/// Autonomous Smarana Engine (WhiteMagic v9.2).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutonomousSmarana {
    /// Configuration settings.
    pub config: SmaranaConfig,
    /// Spaced repetition tracker.
    pub tracker: SpacedRepetitionTracker,
    /// Hebbian synaptic reinforcer.
    pub hebbian: HebbianReinforcer,
    /// Total active probes executed.
    pub probes_executed: u64,
    /// Successful active probes count.
    pub successful_probes: u64,
    /// Cached composite retention score.
    pub last_composite_score: f32,
    /// Timestamp of last evaluation.
    pub last_eval_time: DateTime<Utc>,
    /// Distribution across alchemical stages.
    pub alchemical_stats: AlchemicalDistribution,
}

impl AutonomousSmarana {
    /// Create a new Autonomous Smarana engine with custom config.
    #[must_use]
    pub fn new(config: SmaranaConfig) -> Self {
        Self {
            config,
            tracker: SpacedRepetitionTracker::new(),
            hebbian: HebbianReinforcer::new(),
            probes_executed: 0,
            successful_probes: 0,
            last_composite_score: 1.0,
            last_eval_time: Utc::now(),
            alchemical_stats: AlchemicalDistribution::default(),
        }
    }

    /// Record a legacy tool call outcome (adapter for backward compatibility with CittaHeartbeat).
    pub fn record_tool_outcome(&mut self, success: bool, effectiveness: f32) {
        self.probes_executed += 1;
        if success {
            self.successful_probes += 1;
        }
        let probe_accuracy = self.successful_probes as f32 / self.probes_executed as f32;
        let now = Utc::now();
        let mean_r = self.tracker.mean_retrievability(now);
        let stability_factor = (self.tracker.mean_stability() / 30.0).clamp(0.0, 1.0);

        // Composite retention score: retrievability + stability + probe accuracy + effectiveness
        self.last_composite_score = (0.40 * mean_r
            + 0.30 * stability_factor
            + 0.20 * probe_accuracy
            + 0.10 * effectiveness.clamp(0.0, 1.0))
        .clamp(0.0, 1.0);
        self.last_eval_time = now;
    }

    /// Record an active retrieval event on a specific memory.
    pub fn record_retrieval(
        &mut self,
        memory_id: Uuid,
        success: bool,
        grade: f32,
        now: DateTime<Utc>,
    ) -> ReviewOutcome {
        self.probes_executed += 1;
        if success {
            self.successful_probes += 1;
        }
        self.tracker.record_review(memory_id, grade, &self.config, now)
    }

    /// Record co-activations of memories during reasoning or context injection.
    pub fn record_coactivation_batch(
        &mut self,
        memory_ids: &[Uuid],
        salience: f32,
        now: DateTime<Utc>,
    ) {
        self.hebbian.record_coactivation_batch(memory_ids, salience, now);
    }

    /// Get current composite Smarana retention score for ApotheosisEngine.
    #[must_use]
    pub fn composite_score(&self, now: DateTime<Utc>) -> f32 {
        if self.probes_executed == 0 && self.tracker.is_empty() {
            return self.last_composite_score;
        }
        let mean_r = self.tracker.mean_retrievability(now);
        let stability_factor = (self.tracker.mean_stability() / 30.0).clamp(0.0, 1.0);
        let probe_accuracy = if self.probes_executed > 0 {
            self.successful_probes as f32 / self.probes_executed as f32
        } else {
            1.0
        };

        let crystallization_ratio = if self.alchemical_stats.total > 0 {
            self.alchemical_stats.crystallization as f32 / self.alchemical_stats.total as f32
        } else {
            0.0
        };

        (0.40 * mean_r + 0.30 * stability_factor + 0.20 * probe_accuracy + 0.10 * crystallization_ratio)
            .clamp(0.0, 1.0)
    }

    /// Generate due spaced-repetition probes for active testing.
    #[must_use]
    pub fn generate_due_probes(&self, limit: usize, now: DateTime<Utc>) -> Vec<SmaranaProbe> {
        let due_ids = self.tracker.due_items(self.config.target_retrievability, now);
        due_ids
            .into_iter()
            .take(limit)
            .map(|memory_id| {
                let predicted_r = self.tracker.retrievability(&memory_id, now);
                SmaranaProbe {
                    id: Uuid::new_v4(),
                    kind: ProbeKind::RetentionCheck {
                        memory_id,
                        predicted_retrievability: predicted_r,
                    },
                    memory_id,
                    created_at: now,
                    expected_latency_ms: 50,
                }
            })
            .collect()
    }

    /// Process the result of an executed probe.
    pub fn process_probe_result(&mut self, result: &ProbeResult, now: DateTime<Utc>) -> ReviewOutcome {
        self.record_retrieval(result.memory_id, result.success, result.grade, now)
    }

    /// Execute Alchemical Decay (Nigredo) sweep across a galaxy.
    pub fn run_decay_step(
        &mut self,
        store: &MemoryStore,
        assoc_store: &AssociationStore,
        galaxy: Galaxy,
        now: DateTime<Utc>,
    ) -> Result<AlchemicalDecayReport> {
        let mut report = AlchemicalDecayReport::default();
        let memories = store.scan(galaxy, 5_000)?;
        let env = store.env();
        let mut to_update = Vec::new();

        for mem in memories {
            report.evaluated += 1;
            let rep_item = self.tracker.get(&mem.metadata.id);
            let from_count = assoc_store.find_from(env, mem.metadata.id).map_or(0, |v| v.len());
            let to_count = assoc_store.find_to(env, mem.metadata.id).map_or(0, |v| v.len());
            let stage = AlchemicalPhaseBridge::classify(
                &mem,
                rep_item,
                from_count + to_count,
                &self.config,
                now,
            );

            match stage {
                AlchemicalStage::Decay => {
                    report.decayed += 1;
                    let mut decayed = mem.clone();
                    // Decay importance and neuro score proportionally to retrievability
                    let r = rep_item.map_or(0.5, |i| i.retrievability(now));
                    let factor = (0.5 + 0.4 * r).clamp(0.4, 0.9);
                    decayed.decay_importance(factor);
                    decayed.metadata.neuro_score = (decayed.metadata.neuro_score * factor).clamp(0.0, 1.0);
                    to_update.push(decayed);
                }
                _ => {
                    report.preserved += 1;
                }
            }
        }

        if !to_update.is_empty() {
            store.put_batch(galaxy, &to_update)?;
        }

        Ok(report)
    }

    /// Execute Alchemical Consolidation & Hebbian Reinforcement.
    pub fn run_consolidation_step(
        &mut self,
        store: &MemoryStore,
        assoc_store: &AssociationStore,
        now: DateTime<Utc>,
    ) -> Result<HebbianConsolidationReport> {
        self.hebbian.consolidate_synapses(store, assoc_store, &self.config, now)
    }

    /// Execute Alchemical Crystallization (Rubedo): Solidify hyper-stable memories.
    pub fn run_crystallization_step(
        &mut self,
        store: &MemoryStore,
        assoc_store: &AssociationStore,
        galaxy: Galaxy,
        now: DateTime<Utc>,
    ) -> Result<CrystallizationReport> {
        let mut report = CrystallizationReport::default();
        let memories = store.scan(galaxy, 5_000)?;
        let env = store.env();
        let mut crystallized_memories = Vec::new();

        for mem in memories {
            if mem.metadata.is_protected {
                continue;
            }
            let rep_item = self.tracker.get(&mem.metadata.id);
            let from_count = assoc_store.find_from(env, mem.metadata.id).map_or(0, |v| v.len());
            let to_count = assoc_store.find_to(env, mem.metadata.id).map_or(0, |v| v.len());
            let stage = AlchemicalPhaseBridge::classify(
                &mem,
                rep_item,
                from_count + to_count,
                &self.config,
                now,
            );

            if stage == AlchemicalStage::Crystallization {
                let mut crystallized = mem.clone();
                crystallized.metadata.is_protected = true;
                crystallized.metadata.tier = Tier::Semantic;
                crystallized.metadata.tags.push("crystallized:rubedo".to_string());
                crystallized_memories.push(crystallized);
                report.crystallized += 1;
            }
        }

        if !crystallized_memories.is_empty() {
            store.put_batch(galaxy, &crystallized_memories)?;
        }

        Ok(report)
    }

    /// Execute Gist Distillation (Citrinitas) on clusters of connected memories.
    pub fn run_distillation_step(
        &mut self,
        store: &MemoryStore,
        assoc_store: &AssociationStore,
        citta: &CittaVector,
        source_galaxy: Galaxy,
        target_galaxy: Galaxy,
    ) -> Result<GistDistillationReport> {
        let mut report = GistDistillationReport::default();
        let memories = store.scan(source_galaxy, 1_000)?;
        let env = store.env();
        let mut visited: HashSet<Uuid> = HashSet::new();

        let mut total_compression = 0.0f32;

        for mem in &memories {
            if visited.contains(&mem.metadata.id) || mem.is_telemetry_or_noise() {
                continue;
            }

            // Find neighbors connected by association
            let outgoing = assoc_store.find_from(env, mem.metadata.id)?;
            let mut cluster = vec![mem.clone()];
            visited.insert(mem.metadata.id);

            for edge in outgoing {
                if edge.weight >= 0.45 && cluster.len() < self.config.max_gist_cluster_size {
                    if let Some((_, neighbor)) = store.find_across_galaxies(edge.target)? {
                        if !visited.contains(&neighbor.metadata.id) && !neighbor.is_telemetry_or_noise() {
                            visited.insert(neighbor.metadata.id);
                            cluster.push(neighbor);
                        }
                    }
                }
            }

            if cluster.len() >= 2 {
                let reps: Vec<Option<&RepetitionItem>> = cluster
                    .iter()
                    .map(|m| self.tracker.get(&m.metadata.id))
                    .collect();

                if let Some(gist) = GistDistiller::distill_cluster(&cluster, &reps, citta) {
                    let gist_mem = GistDistiller::to_memory(&gist, target_galaxy);
                    store.put_dedup(target_galaxy, &gist_mem)?;
                    report.clusters_distilled += 1;
                    report.gists_created += 1;
                    total_compression += gist.compression_ratio;
                }
            }
        }

        if report.gists_created > 0 {
            report.avg_compression_ratio = total_compression / (report.gists_created as f32);
        }

        Ok(report)
    }

    /// Refresh distribution statistics across all tracked items.
    pub fn refresh_alchemical_distribution(
        &mut self,
        store: &MemoryStore,
        assoc_store: &AssociationStore,
        now: DateTime<Utc>,
    ) -> Result<AlchemicalDistribution> {
        let mut dist = AlchemicalDistribution::default();
        let env = store.env();

        for galaxy in Galaxy::all() {
            let memories = match store.scan(galaxy, 2_000) {
                Ok(m) => m,
                Err(_) => continue,
            };
            for mem in memories {
                dist.total += 1;
                let rep = self.tracker.get(&mem.metadata.id);
                let from_count = assoc_store.find_from(env, mem.metadata.id).map_or(0, |v| v.len());
                let to_count = assoc_store.find_to(env, mem.metadata.id).map_or(0, |v| v.len());
                let stage = AlchemicalPhaseBridge::classify(
                    &mem,
                    rep,
                    from_count + to_count,
                    &self.config,
                    now,
                );
                match stage {
                    AlchemicalStage::Decay => dist.decay += 1,
                    AlchemicalStage::Sublimation => dist.sublimation += 1,
                    AlchemicalStage::Compression => dist.compression += 1,
                    AlchemicalStage::Crystallization => dist.crystallization += 1,
                }
            }
        }

        self.alchemical_stats = dist.clone();
        Ok(dist)
    }
}

impl Default for AutonomousSmarana {
    fn default() -> Self {
        Self::new(SmaranaConfig::default())
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Duration;
    use tempfile::TempDir;
    use wm_core::Galaxy;
    use wm_memory::{AssociationStore, MemoryStore};

    fn open_test_stores() -> (TempDir, MemoryStore, AssociationStore) {
        let dir = TempDir::new().unwrap();
        let store = MemoryStore::open_default(dir.path()).unwrap();
        let assoc = AssociationStore::open(store.env()).unwrap();
        (dir, store, assoc)
    }

    #[test]
    fn test_ebbinghaus_decay_curve() {
        let memory_id = Uuid::new_v4();
        let item = RepetitionItem::new(memory_id, 10.0, 0.3);
        let start = item.last_reviewed_at;

        // At t = 0, R = 1.0
        assert!((item.retrievability(start) - 1.0).abs() < 1e-4);

        // At t = S (10 days), R should equal 0.90
        let at_s = start + Duration::days(10);
        let r_at_s = item.retrievability(at_s);
        assert!((r_at_s - 0.90).abs() < 0.01, "Expected ~0.90 at t=S, got {}", r_at_s);

        // At t = 20 days, R should be 0.90^2 = 0.81
        let at_2s = start + Duration::days(20);
        let r_at_2s = item.retrievability(at_2s);
        assert!((r_at_2s - 0.81).abs() < 0.02, "Expected ~0.81 at t=2S, got {}", r_at_2s);
    }

    #[test]
    fn test_spacing_effect_greater_stability_on_delayed_recall() {
        let config = SmaranaConfig::default();
        let now = Utc::now();

        // Case A: Immediate review (R is high ~ 0.98)
        let mut item_immediate = RepetitionItem::new(Uuid::new_v4(), 5.0, 0.3);
        item_immediate.last_reviewed_at = now - Duration::hours(2);
        let outcome_immediate = item_immediate.record_review(1.0, &config, now);

        // Case B: Spaced review (R has dropped to ~0.70)
        let mut item_spaced = RepetitionItem::new(Uuid::new_v4(), 5.0, 0.3);
        item_spaced.last_reviewed_at = now - Duration::days(17);
        let outcome_spaced = item_spaced.record_review(1.0, &config, now);

        // The spacing effect guarantees greater absolute stability gain on delayed recall!
        assert!(
            outcome_spaced.new_stability > outcome_immediate.new_stability,
            "Spaced review should produce higher stability ({} vs {})",
            outcome_spaced.new_stability,
            outcome_immediate.new_stability
        );
    }

    #[test]
    fn test_lapse_penalty_reduces_stability() {
        let config = SmaranaConfig::default();
        let now = Utc::now();
        let mut item = RepetitionItem::new(Uuid::new_v4(), 20.0, 0.3);
        let outcome = item.record_review(0.2, &config, now);

        assert!(!outcome.success);
        assert_eq!(outcome.lapses, 1);
        assert!(outcome.new_stability < 20.0);
        assert!((outcome.new_stability - (20.0 * config.lapse_multiplier)).abs() < 0.1);
        assert!(outcome.new_difficulty > 0.3);
    }

    #[test]
    fn test_hebbian_reinforcement_and_de_novo_creation() {
        let (_dir, store, assoc) = open_test_stores();
        let mut reinforcer = HebbianReinforcer::new();
        let config = SmaranaConfig::default();
        let now = Utc::now();

        let id1 = Uuid::new_v4();
        let id2 = Uuid::new_v4();

        // 1st coactivation (below threshold 2)
        reinforcer.record_coactivation_batch(&[id1, id2], 0.8, now);
        assert_eq!(reinforcer.pending_pairs(), 1);

        let report1 = reinforcer.consolidate_synapses(&store, &assoc, &config, now).unwrap();
        assert_eq!(report1.associations_created, 0);

        // 2nd coactivation reaches threshold 2
        reinforcer.record_coactivation_batch(&[id1, id2], 0.9, now);
        let report2 = reinforcer.consolidate_synapses(&store, &assoc, &config, now).unwrap();
        assert_eq!(report2.associations_created, 1);

        // Verify association exists in store
        let pair = HebbianReinforcer::canonical_pair(id1, id2);
        let stored = assoc.get(store.env(), pair.0, pair.1).unwrap().expect("association must exist");
        assert!(stored.weight > 0.0);

        // Further coactivation reinforces existing association
        reinforcer.record_coactivation_batch(&[id1, id2], 1.0, now);
        reinforcer.record_coactivation_batch(&[id1, id2], 1.0, now);
        let report3 = reinforcer.consolidate_synapses(&store, &assoc, &config, now).unwrap();
        assert_eq!(report3.associations_reinforced, 1);

        let updated = assoc.get(store.env(), pair.0, pair.1).unwrap().unwrap();
        assert!(updated.weight > stored.weight, "Weight should increase via Hebbian plasticity");
    }

    #[test]
    fn test_alchemical_stage_classification() {
        let config = SmaranaConfig::default();
        let now = Utc::now();
        let mut mem = Memory::new(Galaxy::Codex, "Aria foundational invariant".to_string());
        mem.metadata.importance = 0.90;

        // Fresh item with high stability and multiple reps -> Crystallization
        let mut rep_high = RepetitionItem::new(mem.metadata.id, 20.0, 0.2);
        rep_high.reps = 5;
        let stage_high = AlchemicalPhaseBridge::classify(&mem, Some(&rep_high), 4, &config, now);
        assert_eq!(stage_high, AlchemicalStage::Crystallization);

        // Decayed item -> Decay
        let mut rep_decay = RepetitionItem::new(mem.metadata.id, 1.0, 0.8);
        rep_decay.last_reviewed_at = now - Duration::days(30);
        let stage_decay = AlchemicalPhaseBridge::classify(&mem, Some(&rep_decay), 0, &config, now);
        assert_eq!(stage_decay, AlchemicalStage::Decay);
    }

    #[test]
    fn test_gist_distillation() {
        let mem1 = Memory::new(
            Galaxy::Sessions,
            "Autonomous Smarana continuously measures retention decay curves and reinforces neural links.".to_string(),
        );
        let mem2 = Memory::new(
            Galaxy::Sessions,
            "Smarana applies Ebbinghaus spaced-repetition testing to ensure memories resist forgetting decay.".to_string(),
        );

        let cluster = vec![mem1, mem2];
        let reps = vec![None, None];
        let citta = CittaVector::neutral();

        let gist = GistDistiller::distill_cluster(&cluster, &reps, &citta).expect("gist distillation must succeed");
        assert_eq!(gist.source_memory_ids.len(), 2);
        assert!(!gist.salient_keywords.is_empty());
        assert!(gist.abstract_summary.contains("[Gist Distillation]"));
        assert!(gist.compression_ratio >= 1.0);

        let memory = GistDistiller::to_memory(&gist, Galaxy::Aria);
        assert_eq!(memory.metadata.memory_type, MemoryType::Symbolic);
        assert_eq!(memory.metadata.tier, Tier::Semantic);
        assert!(memory.metadata.tags.contains(&"gist".to_string()));
    }
}
