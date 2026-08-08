//! Advanced neural features — neuroscience-inspired memory dynamics.
//!
//! Phase 6.7: Ports v2's neuroscience-inspired memory dynamics:
//! 1. Spreading activation — activation spreads through association graph
//! 2. Surprise gate — novelty detection gates memory encoding
//! 3. Ripple tagging — marks memories for consolidation during dream cycle
//! 4. Neuromodulation — dopamine/serotonin analogs modulate retention
//! 5. Metaplasticity — learning rate adapts based on prior activation
//!
//! Pre-N Batch A: Ports v2's wm-neuro crate:
//! 6. Momentum dynamics — temporal continuity for spreading activation
//! 7. Thalamic gating — context-dependent galaxy access masks
//! 8. Predictive coding — JEPA-style surprise for memory prioritization

use std::collections::{HashMap, HashSet};
use uuid::Uuid;
use wm_core::{Galaxy, Result};
use wm_memory::{AssociationStore, Memory, MemoryStore};

#[cfg(test)]
use wm_memory::Association;

// ── 1. Spreading Activation ───────────────────────────────────────────

/// Spreading activation engine — propagates activation through the
/// association graph. Recalling one memory activates connected ones,
/// with decaying activation along edges.
pub struct SpreadingActivation {
    /// Decay factor per hop (0.0 = no spread, 1.0 = no decay)
    pub decay: f32,
    /// Maximum hops to spread
    pub max_hops: usize,
    /// Minimum activation threshold to include in results
    pub min_activation: f32,
}

impl Default for SpreadingActivation {
    fn default() -> Self {
        Self {
            decay: 0.7,
            max_hops: 3,
            min_activation: 0.1,
        }
    }
}

/// Result of a spreading activation run.
#[derive(Debug, Clone)]
pub struct ActivationResult {
    /// Memory ID → activation level (0.0 to 1.0)
    pub activations: HashMap<Uuid, f32>,
    /// Number of hops reached
    pub hops_reached: usize,
}

impl SpreadingActivation {
    /// Create a new spreading activation engine.
    #[must_use]
    pub const fn new(decay: f32, max_hops: usize, min_activation: f32) -> Self {
        Self {
            decay: decay.clamp(0.0, 1.0),
            max_hops,
            min_activation,
        }
    }

    /// Spread activation from a seed memory through the association graph.
    ///
    /// Starting with the seed at activation 1.0, activation spreads
    /// along association edges, multiplied by edge weight and decay factor.
    pub fn spread(
        &self,
        seed: Uuid,
        associations: &AssociationStore,
        env: &lmdb::Environment,
    ) -> Result<ActivationResult> {
        let mut activations: HashMap<Uuid, f32> = HashMap::new();
        activations.insert(seed, 1.0);

        let mut frontier: HashSet<Uuid> = HashSet::new();
        frontier.insert(seed);

        for hop in 0..self.max_hops {
            if frontier.is_empty() {
                break;
            }
            let mut next_frontier: HashSet<Uuid> = HashSet::new();

            for &node in &frontier {
                let current_activation = activations[&node];

                // Get all associations from this node
                let neighbors = associations.find_from(env, node).unwrap_or_default();

                for assoc in &neighbors {
                    let edge_weight = assoc.weight;
                    let spread_activation = current_activation * self.decay * edge_weight;

                    if spread_activation >= self.min_activation {
                        let entry = activations.entry(assoc.target).or_insert(0.0);
                        // Take max activation (not sum, to avoid runaway)
                        if spread_activation > *entry {
                            *entry = spread_activation;
                        }
                        next_frontier.insert(assoc.target);
                    }
                }

                // Also check incoming associations (bidirectional spread)
                let incoming = associations.find_to(env, node).unwrap_or_default();
                for assoc in &incoming {
                    let edge_weight = assoc.weight;
                    let spread_activation = current_activation * self.decay * edge_weight;

                    if spread_activation >= self.min_activation {
                        let entry = activations.entry(assoc.source).or_insert(0.0);
                        if spread_activation > *entry {
                            *entry = spread_activation;
                        }
                        next_frontier.insert(assoc.source);
                    }
                }
            }

            // Only continue with nodes that weren't already in the frontier
            next_frontier.retain(|id| {
                !frontier.contains(id)
                    && *activations.get(id).unwrap_or(&0.0) >= self.min_activation
            });
            frontier = next_frontier;

            if frontier.is_empty() {
                return Ok(ActivationResult {
                    activations,
                    hops_reached: hop + 1,
                });
            }
        }

        Ok(ActivationResult {
            activations,
            hops_reached: self.max_hops,
        })
    }

    /// Get the top-N most activated memories (excluding the seed).
    #[must_use]
    pub fn top_n(&self, result: &ActivationResult, seed: Uuid, n: usize) -> Vec<(Uuid, f32)> {
        let mut sorted: Vec<(Uuid, f32)> = result
            .activations
            .iter()
            .filter(|(id, _)| **id != seed)
            .map(|(id, &act)| (*id, act))
            .collect();
        sorted.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        sorted.truncate(n);
        sorted
    }
}

// ── 2. Surprise Gate ──────────────────────────────────────────────────

/// Surprise gate — novelty detection gates memory encoding.
///
/// Memories with high novelty scores are more likely to be encoded
/// (stored with higher importance). Low-novelty memories may be
/// skipped or stored with reduced importance.
pub struct SurpriseGate {
    /// Novelty threshold above which memory is always encoded
    pub encode_threshold: f32,
    /// Novelty threshold below which memory is skipped
    pub skip_threshold: f32,
    /// Importance boost for surprising memories
    pub surprise_boost: f32,
}

impl Default for SurpriseGate {
    fn default() -> Self {
        Self {
            encode_threshold: 0.6,
            skip_threshold: 0.1,
            surprise_boost: 0.2,
        }
    }
}

/// Decision from the surprise gate.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GateDecision {
    /// Encode with boosted importance (high novelty)
    Encode,
    /// Encode normally (moderate novelty)
    EncodeNormal,
    /// Skip encoding (low novelty)
    Skip,
}

impl SurpriseGate {
    /// Create a new surprise gate.
    #[must_use]
    pub const fn new(encode_threshold: f32, skip_threshold: f32, surprise_boost: f32) -> Self {
        Self {
            encode_threshold,
            skip_threshold,
            surprise_boost,
        }
    }

    /// Evaluate whether a memory should be encoded based on novelty.
    #[must_use]
    pub fn evaluate(&self, novelty_score: f32) -> GateDecision {
        if novelty_score >= self.encode_threshold {
            GateDecision::Encode
        } else if novelty_score >= self.skip_threshold {
            GateDecision::EncodeNormal
        } else {
            GateDecision::Skip
        }
    }

    /// Apply the gate to a memory — may boost importance or skip.
    /// Returns `true` if the memory should be encoded.
    pub fn apply(&self, memory: &mut Memory) -> bool {
        match self.evaluate(memory.metadata.novelty_score) {
            GateDecision::Encode => {
                memory.metadata.importance =
                    (memory.metadata.importance + self.surprise_boost).clamp(0.0, 1.0);
                true
            }
            GateDecision::EncodeNormal => true,
            GateDecision::Skip => false,
        }
    }
}

// ── 3. Ripple Tagger ──────────────────────────────────────────────────

/// Ripple tagger — marks memories for consolidation during dream cycle.
///
/// Inspired by sharp-wave ripple events in the hippocampus, which
/// replay and tag recent memories for consolidation. Memories with
/// high recent access and high neuro_score are tagged for priority
/// consolidation.
pub struct RippleTagger {
    /// Minimum neuro_score for ripple tagging
    pub min_neuro_score: f32,
    /// Minimum access count for ripple tagging
    pub min_access_count: u64,
    /// Tag applied to ripple-tagged memories
    pub ripple_tag: String,
}

impl Default for RippleTagger {
    fn default() -> Self {
        Self {
            min_neuro_score: 0.5,
            min_access_count: 2,
            ripple_tag: "ripple_tagged".to_string(),
        }
    }
}

/// Result of ripple tagging.
#[derive(Debug, Clone)]
pub struct RippleReport {
    /// Number of memories tagged
    pub tagged: usize,
    /// Number of memories scanned
    pub scanned: usize,
    /// IDs of tagged memories
    pub tagged_ids: Vec<Uuid>,
}

impl RippleTagger {
    /// Create a new ripple tagger.
    #[must_use]
    pub fn new(min_neuro_score: f32, min_access_count: u64) -> Self {
        Self {
            min_neuro_score,
            min_access_count,
            ripple_tag: "ripple_tagged".to_string(),
        }
    }

    /// Tag memories that meet ripple criteria.
    ///
    /// Scans all non-system galaxies, adds the ripple tag to memories
    /// with high neuro_score and sufficient recent access.
    pub fn tag(&self, store: &MemoryStore) -> Result<RippleReport> {
        let mut report = RippleReport {
            tagged: 0,
            scanned: 0,
            tagged_ids: Vec::new(),
        };

        for galaxy in wm_core::Galaxy::all() {
            match galaxy {
                wm_core::Galaxy::Substrate
                | wm_core::Galaxy::Dharma
                | wm_core::Galaxy::Karma
                | wm_core::Galaxy::Embeddings
                | wm_core::Galaxy::Associations => continue,
                _ => {}
            }

            let mems = store.scan(galaxy, 10_000)?;
            for mem in mems {
                report.scanned += 1;

                if mem.metadata.neuro_score >= self.min_neuro_score
                    && mem.metadata.access_count >= self.min_access_count
                    && !mem.metadata.tags.contains(&self.ripple_tag)
                {
                    let mut updated = mem.clone();
                    updated.metadata.tags.push(self.ripple_tag.clone());
                    store.put(galaxy, &updated)?;
                    report.tagged += 1;
                    report.tagged_ids.push(updated.metadata.id);
                }
            }
        }

        Ok(report)
    }
}

// ── 4. Neuromodulation ────────────────────────────────────────────────

/// Neuromodulation — dopamine/serotonin analogs modulate retention.
///
/// Dopamine (reward signal) boosts importance and neuro_score.
/// Serotonin (mood stabilizer) dampens extreme values, pulling
/// toward equilibrium. These modulate how memories are retained
/// over time.
#[derive(Debug, Clone, Copy)]
pub struct Neuromodulator {
    /// Dopamine level (0.0 = low reward, 1.0 = high reward)
    pub dopamine: f32,
    /// Serotonin level (0.0 = low mood, 1.0 = stable mood)
    pub serotonin: f32,
}

impl Default for Neuromodulator {
    fn default() -> Self {
        Self {
            dopamine: 0.5,
            serotonin: 0.5,
        }
    }
}

impl Neuromodulator {
    /// Create a new neuromodulator state.
    #[must_use]
    pub const fn new(dopamine: f32, serotonin: f32) -> Self {
        Self {
            dopamine: dopamine.clamp(0.0, 1.0),
            serotonin: serotonin.clamp(0.0, 1.0),
        }
    }

    /// Apply dopamine boost to a memory.
    ///
    /// High dopamine increases importance and neuro_score (reward-enhanced memory).
    pub fn apply_dopamine(&self, memory: &mut Memory) {
        let boost = (self.dopamine - 0.5) * 0.2; // ±0.1 max
        memory.metadata.importance = (memory.metadata.importance + boost).clamp(0.0, 1.0);
        memory.metadata.neuro_score = (memory.metadata.neuro_score + boost * 0.5).clamp(0.0, 1.0);
    }

    /// Apply serotonin stabilization to a memory.
    ///
    /// High serotonin pulls importance toward 0.5 (equilibrium), reducing extremes.
    pub fn apply_serotonin(&self, memory: &mut Memory) {
        let stabilization = self.serotonin * 0.1;
        let target = 0.5;
        memory.metadata.importance = (target - memory.metadata.importance)
            .mul_add(stabilization, memory.metadata.importance);
    }

    /// Apply both dopamine and serotonin modulation.
    pub fn apply(&self, memory: &mut Memory) {
        self.apply_dopamine(memory);
        self.apply_serotonin(memory);
    }

    /// Apply neuromodulation to all memories in a store.
    ///
    /// Skips memories with importance below 0.1 to avoid interfering
    /// with the decay phase's intentional reduction of low-value memories.
    pub fn apply_to_store(&self, store: &MemoryStore) -> Result<usize> {
        let mut modified = 0;
        for galaxy in wm_core::Galaxy::all() {
            match galaxy {
                wm_core::Galaxy::Substrate
                | wm_core::Galaxy::Dharma
                | wm_core::Galaxy::Karma
                | wm_core::Galaxy::Embeddings
                | wm_core::Galaxy::Associations => continue,
                _ => {}
            }
            let mems = store.scan(galaxy, 10_000)?;
            let mut to_write: Vec<wm_memory::Memory> = Vec::new();
            for mem in mems {
                // Skip very low-importance memories (preserve decay results)
                if mem.metadata.importance < 0.1 {
                    continue;
                }
                let mut updated = mem.clone();
                self.apply(&mut updated);
                // Only write if something actually changed
                if (updated.metadata.importance - mem.metadata.importance).abs() > 0.001
                    || (updated.metadata.neuro_score - mem.metadata.neuro_score).abs() > 0.001
                {
                    to_write.push(updated);
                }
            }
            if !to_write.is_empty() {
                modified += to_write.len();
                store.put_batch(galaxy, &to_write)?;
            }
        }
        Ok(modified)
    }
}

// ── 5. Metaplasticity ─────────────────────────────────────────────────

/// Metaplasticity — learning rate adapts based on prior activation.
///
/// Memories that have been frequently activated have a lower learning
/// rate (harder to modify), while rarely-activated memories have a
/// higher learning rate (more plastic). This prevents well-established
/// memories from being easily overwritten.
pub struct Metaplasticity {
    /// Base learning rate
    pub base_rate: f32,
    /// Maximum learning rate (for rarely-activated memories)
    pub max_rate: f32,
    /// Minimum learning rate (for frequently-activated memories)
    pub min_rate: f32,
    /// Access count at which learning rate is halved
    pub plasticity_threshold: u64,
}

impl Default for Metaplasticity {
    fn default() -> Self {
        Self {
            base_rate: 0.1,
            max_rate: 0.3,
            min_rate: 0.01,
            plasticity_threshold: 10,
        }
    }
}

impl Metaplasticity {
    /// Create a new metaplasticity controller.
    #[must_use]
    pub const fn new(base_rate: f32, max_rate: f32, min_rate: f32, threshold: u64) -> Self {
        Self {
            base_rate,
            max_rate,
            min_rate,
            plasticity_threshold: threshold,
        }
    }

    /// Compute the learning rate for a memory based on its access count.
    ///
    /// `rate = base_rate * (threshold / (threshold + access_count))`
    /// Clamped to [min_rate, max_rate].
    #[must_use]
    pub fn learning_rate(&self, access_count: u64) -> f32 {
        let factor = self.plasticity_threshold as f32
            / (self.plasticity_threshold as f32 + access_count as f32);
        let rate = self.base_rate * factor;
        rate.clamp(self.min_rate, self.max_rate)
    }

    /// Apply metaplasticity-adjusted learning to a memory.
    ///
    /// Updates the memory's importance toward a target value, with
    /// the learning rate modulated by prior access count.
    pub fn learn(&self, memory: &mut Memory, target_importance: f32) {
        let rate = self.learning_rate(memory.metadata.access_count);
        memory.metadata.importance = (target_importance - memory.metadata.importance)
            .mul_add(rate, memory.metadata.importance);
        memory.metadata.importance = memory.metadata.importance.clamp(0.0, 1.0);
    }

    /// Apply metaplasticity-adjusted Hebbian boost to a memory's neuro_score.
    pub fn hebbian_boost(&self, memory: &mut Memory) {
        let rate = self.learning_rate(memory.metadata.access_count);
        let boost = rate * (1.0 - memory.metadata.neuro_score);
        memory.metadata.neuro_score = (memory.metadata.neuro_score + boost).clamp(0.0, 1.0);
    }
}

// ── 6. Momentum Dynamics ─────────────────────────────────────────────
//
// Ported from v2's wm-neuro/src/momentum_dynamics.rs.
// Based on RNN replay dynamics (arXiv, Feb 2026): hidden state momentum
// enables temporally compressed replay. Nodes that were recently activated
// get a boost, creating temporal continuity in the activation pattern.

/// Momentum dynamics — adds temporal continuity to spreading activation.
///
/// Tracks per-node momentum across `SpreadingActivation::spread()` calls.
/// Nodes activated recently get a boost on subsequent spreads, simulating
/// the temporal continuity of hippocampal replay.
pub struct MomentumDynamics {
    momentum: HashMap<Uuid, f32>,
    momentum_coeff: f32,
    decay_rate: f32,
    min_momentum: f32,
    /// Total number of `update()` calls
    pub total_updates: u64,
    /// Total number of `decay()` calls
    pub total_decays: u64,
}

impl Default for MomentumDynamics {
    fn default() -> Self {
        Self::new(0.9, 0.85)
    }
}

impl MomentumDynamics {
    /// Create a new momentum tracker.
    ///
    /// # Arguments
    /// * `momentum_coeff` - How much previous momentum carries forward (0.0–1.0)
    /// * `decay_rate` - Multiplicative decay applied per `decay()` call (0.0–1.0)
    #[must_use]
    pub fn new(momentum_coeff: f32, decay_rate: f32) -> Self {
        Self {
            momentum: HashMap::new(),
            momentum_coeff,
            decay_rate,
            min_momentum: 0.01,
            total_updates: 0,
            total_decays: 0,
        }
    }

    /// Update momentum from a spreading activation result.
    ///
    /// For each activated node, momentum accumulates:
    /// `new = old * coeff + activation`
    pub fn update(&mut self, activations: &HashMap<Uuid, f32>) {
        self.total_updates += 1;
        for (&node_id, &activation) in activations {
            let current = self.momentum.get(&node_id).copied().unwrap_or(0.0);
            let new_momentum = current * self.momentum_coeff + activation;
            self.momentum.insert(node_id, new_momentum);
        }
    }

    /// Update momentum directly from an `ActivationResult`.
    pub fn update_from_result(&mut self, result: &ActivationResult) {
        self.update(&result.activations);
    }

    /// Decay all momentum values, pruning those below `min_momentum`.
    pub fn decay(&mut self) {
        self.total_decays += 1;
        let decay = self.decay_rate;
        let min = self.min_momentum;
        self.momentum.retain(|_, m| {
            *m *= decay;
            *m > min
        });
    }

    /// Get momentum for a specific node.
    #[must_use]
    pub fn get(&self, node_id: &Uuid) -> f32 {
        self.momentum.get(node_id).copied().unwrap_or(0.0)
    }

    /// Apply momentum boost to a list of (node, score) pairs.
    ///
    /// Returns a new list where each score is boosted by
    /// `score + momentum * coeff`.
    #[must_use]
    pub fn apply_momentum(&self, scores: &[(Uuid, f32)]) -> Vec<(Uuid, f32)> {
        scores
            .iter()
            .map(|&(node_id, score)| {
                let mom = self.get(&node_id);
                (node_id, (mom * self.momentum_coeff).mul_add(1.0, score))
            })
            .collect()
    }

    /// Get all nodes with momentum above a threshold, sorted by momentum descending.
    #[must_use]
    pub fn active_nodes(&self, threshold: f32) -> Vec<(Uuid, f32)> {
        let mut nodes: Vec<_> = self
            .momentum
            .iter()
            .filter(|&(_, &m)| m > threshold)
            .map(|(&k, &v)| (k, v))
            .collect();
        nodes.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        nodes
    }

    /// Number of nodes currently tracked.
    #[must_use]
    pub fn len(&self) -> usize {
        self.momentum.len()
    }

    /// Whether no nodes are tracked.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.momentum.is_empty()
    }

    /// Reset all momentum and stats.
    pub fn reset(&mut self) {
        self.momentum.clear();
        self.total_updates = 0;
        self.total_decays = 0;
    }
}

// ── 7. Thalamic Gating ───────────────────────────────────────────────
//
// Ported from v2's wm-neuro/src/thalamic_gating.rs.
// Based on GATE (PLOS Comp Bio, 2026): EC3→CA1→EC5→EC3 self-gating loop
// for selective memory maintenance. Computes per-galaxy weight multipliers
// based on cognitive context.

/// Cognitive context for thalamic gating.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub enum CognitiveContext {
    /// Default — all galaxies weighted equally
    #[default]
    Default,
    /// Coding — boost Codex + Sessions, suppress Dreams + Journals
    Coding,
    /// Research — boost Research + Journals, suppress Citta + Dreams
    Research,
    /// Introspection — boost Citta + Aria + Journals, suppress Codex
    Introspection,
    /// Creative — boost Dreams + Aria + Citta, suppress Codex + Substrate
    Creative,
    /// Session — boost Sessions + Codex, suppress Dreams + Journals
    Session,
}

impl CognitiveContext {
    /// All known contexts.
    #[must_use]
    pub const fn all() -> [Self; 6] {
        [
            Self::Default,
            Self::Coding,
            Self::Research,
            Self::Introspection,
            Self::Creative,
            Self::Session,
        ]
    }

    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Default => "default",
            Self::Coding => "coding",
            Self::Research => "research",
            Self::Introspection => "introspection",
            Self::Creative => "creative",
            Self::Session => "session",
        }
    }
}

/// Thalamic gate — context-dependent galaxy weight multipliers.
///
/// The thalamus gates sensory input to the cortex; this gates which memory
/// galaxies are most relevant for the current cognitive context. Sub-ms
/// computation via a simple lookup table.
pub struct ThalamicGate {
    context: CognitiveContext,
    /// Cross-galaxy boost factor for galaxies not in the current mask
    cross_galaxy_factor: f32,
    /// Total number of weight computations
    pub total_calls: u64,
}

impl Default for ThalamicGate {
    fn default() -> Self {
        Self::new()
    }
}

impl ThalamicGate {
    /// Create a new thalamic gate with default context.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            context: CognitiveContext::Default,
            cross_galaxy_factor: 0.5,
            total_calls: 0,
        }
    }

    /// Set the current cognitive context.
    pub const fn set_context(&mut self, context: CognitiveContext) {
        self.context = context;
    }

    /// Get the current cognitive context.
    #[must_use]
    #[allow(clippy::missing_const_for_fn)]
    pub fn context(&self) -> CognitiveContext {
        self.context
    }

    /// Get the weight multiplier for a galaxy in the current context.
    #[must_use]
    pub const fn galaxy_weight(&self, galaxy: Galaxy) -> f32 {
        match self.context {
            CognitiveContext::Default => 1.0,
            CognitiveContext::Coding => match galaxy {
                Galaxy::Codex => 1.5,
                Galaxy::Sessions => 1.2,
                Galaxy::Universal => 0.8,
                Galaxy::Citta => 0.6,
                Galaxy::Dreams => 0.3,
                Galaxy::Research => 0.7,
                Galaxy::Aria => 0.5,
                Galaxy::Journals => 0.4,
                Galaxy::Substrate => 0.5,
                Galaxy::Tutorial => 0.6,
                _ => self.cross_galaxy_factor,
            },
            CognitiveContext::Research => match galaxy {
                Galaxy::Research => 1.6,
                Galaxy::Codex => 1.0,
                Galaxy::Universal => 0.9,
                Galaxy::Citta => 0.5,
                Galaxy::Dreams => 0.4,
                Galaxy::Sessions => 0.6,
                Galaxy::Aria => 0.7,
                Galaxy::Journals => 1.1,
                Galaxy::Substrate => 0.5,
                Galaxy::Tutorial => 0.8,
                _ => self.cross_galaxy_factor,
            },
            CognitiveContext::Introspection => match galaxy {
                Galaxy::Citta => 1.8,
                Galaxy::Aria => 1.5,
                Galaxy::Journals => 1.3,
                Galaxy::Dreams => 1.2,
                Galaxy::Universal => 0.7,
                Galaxy::Codex => 0.5,
                Galaxy::Sessions => 0.6,
                Galaxy::Research => 0.6,
                Galaxy::Substrate => 0.5,
                Galaxy::Tutorial => 0.7,
                _ => self.cross_galaxy_factor,
            },
            CognitiveContext::Creative => match galaxy {
                Galaxy::Dreams => 1.6,
                Galaxy::Aria => 1.4,
                Galaxy::Citta => 1.2,
                Galaxy::Universal => 1.0,
                Galaxy::Codex => 0.7,
                Galaxy::Sessions => 0.6,
                Galaxy::Research => 0.8,
                Galaxy::Journals => 0.9,
                Galaxy::Substrate => 0.5,
                Galaxy::Tutorial => 0.6,
                _ => self.cross_galaxy_factor,
            },
            CognitiveContext::Session => match galaxy {
                Galaxy::Sessions => 1.7,
                Galaxy::Codex => 1.0,
                Galaxy::Citta => 0.8,
                Galaxy::Universal => 0.9,
                Galaxy::Dreams => 0.4,
                Galaxy::Research => 0.6,
                Galaxy::Aria => 0.7,
                Galaxy::Journals => 0.5,
                Galaxy::Substrate => 0.5,
                Galaxy::Tutorial => 0.6,
                _ => self.cross_galaxy_factor,
            },
        }
    }

    /// Compute weight multipliers for all memory galaxies.
    pub fn compute_weights(&mut self) -> HashMap<Galaxy, f32> {
        self.total_calls += 1;
        Galaxy::memory_galaxies()
            .iter()
            .map(|&g| (g, self.galaxy_weight(g)))
            .collect()
    }

    /// Apply context weights to a list of (galaxy, score) pairs.
    pub fn apply_to_scores(&mut self, scores: &[(Galaxy, f32)]) -> Vec<(Galaxy, f32)> {
        self.total_calls += 1;
        scores
            .iter()
            .map(|&(g, score)| (g, score * self.galaxy_weight(g)))
            .collect()
    }

    /// Set the cross-galaxy factor for galaxies not in the current mask.
    pub const fn set_cross_galaxy_factor(&mut self, factor: f32) {
        self.cross_galaxy_factor = factor;
    }
}

// ── 8. Predictive Coding ─────────────────────────────────────────────
//
// Ported from v2's wm-neuro/src/predictive_coding.rs.
// Based on PAM (arXiv, Feb 2026): JEPA-style predictor trained on temporal
// co-occurrence. When a new memory arrives, the system predicts what it
// should contain based on recent context. The prediction error (surprise)
// determines whether the memory is worth storing and how much consolidation
// priority it receives.

/// Predictive coder — JEPA-style surprise computation for memory writes.
///
/// Maintains a context window of recent memory embeddings and predicts
/// what the next embedding should be. The prediction error (RMSE) between
/// predicted and actual embedding is the "surprise" — high surprise means
/// the memory is novel and worth storing.
pub struct PredictiveCoder {
    context_window: Vec<Vec<f32>>,
    window_size: usize,
    dim: usize,
    /// Total number of predictions made
    pub total_predictions: u64,
    total_surprise: f64,
}

impl Default for PredictiveCoder {
    fn default() -> Self {
        Self::new(5, 128)
    }
}

impl PredictiveCoder {
    /// Create a new predictive coder.
    ///
    /// # Arguments
    /// * `window_size` - Number of recent embeddings to use as context
    /// * `dim` - Embedding dimensionality
    #[must_use]
    pub const fn new(window_size: usize, dim: usize) -> Self {
        Self {
            context_window: Vec::new(),
            window_size,
            dim,
            total_predictions: 0,
            total_surprise: 0.0,
        }
    }

    /// Add a memory embedding to the context window.
    pub fn observe(&mut self, embedding: Vec<f32>) {
        if self.context_window.len() >= self.window_size {
            self.context_window.remove(0);
        }
        self.context_window.push(embedding);
    }

    /// Predict the next embedding from context (moving average).
    #[must_use]
    pub fn predict(&self) -> Vec<f32> {
        if self.context_window.is_empty() {
            return vec![0.0; self.dim];
        }
        let n = self.context_window.len() as f32;
        let mut predicted = vec![0.0; self.dim];
        for emb in &self.context_window {
            for (i, &v) in emb.iter().enumerate() {
                if i < self.dim {
                    predicted[i] += v / n;
                }
            }
        }
        predicted
    }

    /// Compute prediction error (RMSE) between prediction and actual embedding.
    ///
    /// Also updates running statistics.
    pub fn prediction_error(&mut self, actual: &[f32]) -> f32 {
        self.total_predictions += 1;
        let predicted = self.predict();
        let mut error = 0.0_f32;
        for i in 0..actual.len().min(predicted.len()) {
            let diff = actual[i] - predicted[i];
            error += diff * diff;
        }
        let rmse = error.sqrt();
        self.total_surprise += f64::from(rmse);
        rmse
    }

    /// Process a new memory: compute surprise, then observe.
    ///
    /// Returns the surprise (prediction error) for this embedding.
    pub fn process(&mut self, embedding: Vec<f32>) -> f32 {
        let surprise = self.prediction_error(&embedding);
        self.observe(embedding);
        surprise
    }

    /// Get normalized novelty score (0.0–1.0) from a raw surprise value.
    ///
    /// Compares the surprise to the running average:
    /// - 0.5 = average surprise
    /// - >0.5 = more surprising than average
    /// - <0.5 = less surprising than average
    #[must_use]
    pub fn novelty_score(&self, surprise: f32) -> f32 {
        if self.total_predictions == 0 {
            return 0.5;
        }
        let avg_surprise = self.total_surprise / self.total_predictions as f64;
        if avg_surprise < 1e-10 {
            return 0.5;
        }
        let ratio = f64::from(surprise) / avg_surprise;
        let adjusted = (ratio - 1.0) / (1.0 + (ratio - 1.0).abs());
        (0.5_f64).mul_add(adjusted, 0.5) as f32
    }

    /// Average surprise across all predictions.
    #[must_use]
    pub fn avg_surprise(&self) -> f64 {
        if self.total_predictions == 0 {
            0.0
        } else {
            self.total_surprise / self.total_predictions as f64
        }
    }

    /// Number of embeddings currently in the context window.
    #[must_use]
    pub fn context_len(&self) -> usize {
        self.context_window.len()
    }

    /// Reset all state.
    pub fn reset(&mut self) {
        self.context_window.clear();
        self.total_predictions = 0;
        self.total_surprise = 0.0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    use wm_core::Galaxy;

    fn test_store() -> (tempfile::TempDir, MemoryStore, AssociationStore) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let assoc = AssociationStore::open(store.env()).unwrap();
        (tmp, store, assoc)
    }

    // ── Spreading Activation Tests ─────────────────────────────────────

    #[test]
    fn spreading_activation_seed_only() {
        let (_tmp, store, assoc) = test_store();
        let mem = Memory::new(Galaxy::Codex, "test content".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        let sa = SpreadingActivation::default();
        let result = sa.spread(mem.metadata.id, &assoc, store.env()).unwrap();

        assert_eq!(result.activations.len(), 1);
        assert!((result.activations[&mem.metadata.id] - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn spreading_activation_propagates() {
        let (_tmp, store, assoc) = test_store();

        let mem1 = Memory::new(Galaxy::Codex, "first memory".into());
        let mem2 = Memory::new(Galaxy::Codex, "second memory".into());
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Codex, &mem2).unwrap();

        // Create association mem1 → mem2
        let link = Association::new(
            mem1.metadata.id,
            mem2.metadata.id,
            wm_memory::LinkType::Related,
            0.8,
        );
        assoc.put(store.env(), &link).unwrap();

        let sa = SpreadingActivation::default();
        let result = sa.spread(mem1.metadata.id, &assoc, store.env()).unwrap();

        // Both should be activated
        assert!(result.activations.contains_key(&mem2.metadata.id));
        let mem2_activation = result.activations[&mem2.metadata.id];
        assert!(
            mem2_activation > 0.0 && mem2_activation < 1.0,
            "mem2 should have partial activation, got {mem2_activation}"
        );
    }

    #[test]
    fn spreading_activation_top_n() {
        let (_tmp, store, assoc) = test_store();

        let mem1 = Memory::new(Galaxy::Codex, "first".into());
        let mem2 = Memory::new(Galaxy::Codex, "second".into());
        let mem3 = Memory::new(Galaxy::Codex, "third".into());
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Codex, &mem2).unwrap();
        store.put(Galaxy::Codex, &mem3).unwrap();

        // mem1 → mem2 (strong), mem1 → mem3 (weak)
        let link1 = Association::new(
            mem1.metadata.id,
            mem2.metadata.id,
            wm_memory::LinkType::Related,
            0.9,
        );
        let link2 = Association::new(
            mem1.metadata.id,
            mem3.metadata.id,
            wm_memory::LinkType::Related,
            0.3,
        );
        assoc.put(store.env(), &link1).unwrap();
        assoc.put(store.env(), &link2).unwrap();

        let sa = SpreadingActivation::default();
        let result = sa.spread(mem1.metadata.id, &assoc, store.env()).unwrap();

        let top = sa.top_n(&result, mem1.metadata.id, 2);
        assert_eq!(top.len(), 2);
        // mem2 should be more activated than mem3
        assert_eq!(top[0].0, mem2.metadata.id);
    }

    #[test]
    fn spreading_activation_respects_max_hops() {
        let (_tmp, store, assoc) = test_store();

        let mems: Vec<Memory> = (0..5)
            .map(|i| Memory::new(Galaxy::Codex, format!("mem {i}")))
            .collect();
        for mem in &mems {
            store.put(Galaxy::Codex, mem).unwrap();
        }

        // Chain: mem0 → mem1 → mem2 → mem3 → mem4
        for i in 0..4 {
            let link = Association::new(
                mems[i].metadata.id,
                mems[i + 1].metadata.id,
                wm_memory::LinkType::Related,
                0.8,
            );
            assoc.put(store.env(), &link).unwrap();
        }

        let sa = SpreadingActivation::new(0.7, 2, 0.05);
        let result = sa.spread(mems[0].metadata.id, &assoc, store.env()).unwrap();

        // With max_hops=2, should reach mem0, mem1, mem2 but not mem3/mem4
        assert!(result.activations.contains_key(&mems[1].metadata.id));
        assert!(result.activations.contains_key(&mems[2].metadata.id));
        assert!(
            !result.activations.contains_key(&mems[3].metadata.id),
            "should not reach 3 hops away"
        );
    }

    // ── Surprise Gate Tests ────────────────────────────────────────────

    #[test]
    fn surprise_gate_encodes_high_novelty() {
        let gate = SurpriseGate::default();
        assert_eq!(gate.evaluate(0.8), GateDecision::Encode);
        assert_eq!(gate.evaluate(0.6), GateDecision::Encode);
    }

    #[test]
    fn surprise_gate_skips_low_novelty() {
        let gate = SurpriseGate::default();
        assert_eq!(gate.evaluate(0.05), GateDecision::Skip);
    }

    #[test]
    fn surprise_gate_normal_for_moderate() {
        let gate = SurpriseGate::default();
        assert_eq!(gate.evaluate(0.3), GateDecision::EncodeNormal);
    }

    #[test]
    fn surprise_gate_apply_boosts_importance() {
        let gate = SurpriseGate::default();
        let mut mem = Memory::new(Galaxy::Codex, "surprising content".into())
            .with_importance(0.5)
            .with_novelty_score(0.8);
        let original = mem.metadata.importance;
        assert!(gate.apply(&mut mem));
        assert!(
            mem.metadata.importance > original,
            "high novelty should boost importance"
        );
    }

    #[test]
    fn surprise_gate_apply_skips_low_novelty() {
        let gate = SurpriseGate::default();
        let mut mem = Memory::new(Galaxy::Codex, "boring content".into())
            .with_importance(0.5)
            .with_novelty_score(0.05);
        assert!(!gate.apply(&mut mem));
    }

    // ── Ripple Tagger Tests ────────────────────────────────────────────

    #[test]
    fn ripple_tagger_tags_active_memories() {
        let (_tmp, store, _assoc) = test_store();

        let mut mem = Memory::new(Galaxy::Codex, "frequently accessed".into())
            .with_importance(0.7)
            .with_neuro_score(0.8);
        mem.metadata.access_count = 5;
        store.put(Galaxy::Codex, &mem).unwrap();

        let tagger = RippleTagger::default();
        let report = tagger.tag(&store).unwrap();

        assert!(report.tagged > 0, "should tag active memory");
        assert!(!report.tagged_ids.is_empty());

        // Verify tag was applied
        let updated = store.get(Galaxy::Codex, mem.metadata.id).unwrap().unwrap();
        assert!(
            updated.metadata.tags.contains(&"ripple_tagged".to_string()),
            "should have ripple_tagged tag"
        );
    }

    #[test]
    fn ripple_tagger_skips_inactive_memories() {
        let (_tmp, store, _assoc) = test_store();

        let mem = Memory::new(Galaxy::Codex, "rarely accessed".into())
            .with_importance(0.3)
            .with_neuro_score(0.2);
        store.put(Galaxy::Codex, &mem).unwrap();

        let tagger = RippleTagger::default();
        let report = tagger.tag(&store).unwrap();

        assert_eq!(report.tagged, 0, "should not tag inactive memory");
    }

    #[test]
    fn ripple_tagger_does_not_retag() {
        let (_tmp, store, _assoc) = test_store();

        let mut mem = Memory::new(Galaxy::Codex, "already tagged".into())
            .with_importance(0.7)
            .with_neuro_score(0.8)
            .with_tags(vec!["ripple_tagged".into()]);
        mem.metadata.access_count = 5;
        store.put(Galaxy::Codex, &mem).unwrap();

        let tagger = RippleTagger::default();
        let report = tagger.tag(&store).unwrap();

        assert_eq!(report.tagged, 0, "should not re-tag already tagged memory");
    }

    // ── Neuromodulation Tests ──────────────────────────────────────────

    #[test]
    fn dopamine_boosts_importance() {
        let neuro = Neuromodulator::new(0.9, 0.5); // high dopamine
        let mut mem = Memory::new(Galaxy::Codex, "reward".into()).with_importance(0.5);
        neuro.apply_dopamine(&mut mem);
        assert!(
            mem.metadata.importance > 0.5,
            "high dopamine should boost importance"
        );
    }

    #[test]
    fn dopamine_penalizes_low_reward() {
        let neuro = Neuromodulator::new(0.1, 0.5); // low dopamine
        let mut mem = Memory::new(Galaxy::Codex, "no reward".into()).with_importance(0.5);
        neuro.apply_dopamine(&mut mem);
        assert!(
            mem.metadata.importance < 0.5,
            "low dopamine should reduce importance"
        );
    }

    #[test]
    fn serotonin_stabilizes() {
        let neuro = Neuromodulator::new(0.5, 0.9); // high serotonin
        let mut mem = Memory::new(Galaxy::Codex, "extreme".into()).with_importance(0.9);
        neuro.apply_serotonin(&mut mem);
        assert!(
            mem.metadata.importance < 0.9,
            "serotonin should pull toward 0.5"
        );
    }

    #[test]
    fn neuromodulation_apply_to_store() {
        let (_tmp, store, _assoc) = test_store();

        let mem = Memory::new(Galaxy::Codex, "test".into()).with_importance(0.3);
        store.put(Galaxy::Codex, &mem).unwrap();

        let neuro = Neuromodulator::new(0.9, 0.1); // high dopamine, low serotonin
        let modified = neuro.apply_to_store(&store).unwrap();
        assert!(modified > 0, "should modify memories");
    }

    // ── Metaplasticity Tests ───────────────────────────────────────────

    #[test]
    fn metaplasticity_high_for_new_memories() {
        let meta = Metaplasticity::default();
        let rate = meta.learning_rate(0);
        assert!(
            rate >= meta.base_rate,
            "new memories should have high learning rate"
        );
    }

    #[test]
    fn metaplasticity_low_for_frequently_accessed() {
        let meta = Metaplasticity::default();
        let rate = meta.learning_rate(100);
        assert!(
            rate < meta.base_rate,
            "frequently accessed memories should have low learning rate"
        );
    }

    #[test]
    fn metaplasticity_clamped() {
        let meta = Metaplasticity::default();
        let rate_low = meta.learning_rate(0);
        let rate_high = meta.learning_rate(10000);
        assert!(rate_low <= meta.max_rate);
        assert!(rate_high >= meta.min_rate);
    }

    #[test]
    fn metaplasticity_learn_moves_toward_target() {
        let meta = Metaplasticity::default();
        let mut mem = Memory::new(Galaxy::Codex, "test".into()).with_importance(0.3);
        meta.learn(&mut mem, 0.9);
        assert!(mem.metadata.importance > 0.3, "should move toward target");
        assert!(
            mem.metadata.importance < 0.9,
            "should not fully reach target in one step"
        );
    }

    #[test]
    fn metaplasticity_hebbian_boost() {
        let meta = Metaplasticity::default();
        let mut mem = Memory::new(Galaxy::Codex, "test".into()).with_neuro_score(0.5);
        let original = mem.metadata.neuro_score;
        meta.hebbian_boost(&mut mem);
        assert!(
            mem.metadata.neuro_score > original,
            "Hebbian boost should increase neuro_score"
        );
    }

    // ── Momentum Dynamics Tests ───────────────────────────────────────

    #[test]
    fn momentum_empty_returns_zero() {
        let md = MomentumDynamics::default();
        let id = Uuid::new_v4();
        assert_eq!(md.get(&id), 0.0);
        assert!(md.is_empty());
    }

    #[test]
    fn momentum_update_and_get() {
        let mut md = MomentumDynamics::default();
        let id = Uuid::new_v4();
        let mut activations = HashMap::new();
        activations.insert(id, 0.8);
        md.update(&activations);
        assert!(md.get(&id) > 0.0);
        assert_eq!(md.len(), 1);
    }

    #[test]
    fn momentum_accumulates() {
        let mut md = MomentumDynamics::default();
        let id = Uuid::new_v4();
        let mut activations = HashMap::new();
        activations.insert(id, 0.5);
        md.update(&activations);
        let m1 = md.get(&id);
        md.update(&activations);
        let m2 = md.get(&id);
        assert!(m2 > m1, "momentum should accumulate");
    }

    #[test]
    fn momentum_decay_reduces() {
        let mut md = MomentumDynamics::new(0.9, 0.5); // fast decay
        let id = Uuid::new_v4();
        let mut activations = HashMap::new();
        activations.insert(id, 0.8);
        md.update(&activations);
        let m1 = md.get(&id);
        md.decay();
        let m2 = md.get(&id);
        assert!(m2 < m1, "decay should reduce momentum");
    }

    #[test]
    fn momentum_decay_prunes_weak() {
        let mut md = MomentumDynamics::new(0.9, 0.1); // very fast decay
        let id = Uuid::new_v4();
        let mut activations = HashMap::new();
        activations.insert(id, 0.01);
        md.update(&activations);
        md.decay();
        assert_eq!(md.get(&id), 0.0, "weak momentum should be pruned");
        assert!(md.is_empty());
    }

    #[test]
    fn momentum_apply_momentum_boosts_recent() {
        let mut md = MomentumDynamics::default();
        let id_a = Uuid::new_v4();
        let id_b = Uuid::new_v4();
        let mut activations = HashMap::new();
        activations.insert(id_a, 1.0);
        md.update(&activations);

        let scores = vec![(id_a, 0.5), (id_b, 0.5)];
        let boosted = md.apply_momentum(&scores);
        let a_score = boosted.iter().find(|(id, _)| *id == id_a).unwrap().1;
        let b_score = boosted.iter().find(|(id, _)| *id == id_b).unwrap().1;
        assert!(
            a_score > b_score,
            "recently activated node should be boosted"
        );
    }

    #[test]
    fn momentum_active_nodes_filtered() {
        let mut md = MomentumDynamics::default();
        let high = Uuid::new_v4();
        let low = Uuid::new_v4();
        let mut activations = HashMap::new();
        activations.insert(high, 0.9);
        activations.insert(low, 0.05);
        md.update(&activations);
        let active = md.active_nodes(0.1);
        assert_eq!(active.len(), 1);
        assert_eq!(active[0].0, high);
    }

    #[test]
    fn momentum_update_from_result() {
        let mut md = MomentumDynamics::default();
        let id = Uuid::new_v4();
        let result = ActivationResult {
            activations: {
                let mut m = HashMap::new();
                m.insert(id, 0.7);
                m
            },
            hops_reached: 2,
        };
        md.update_from_result(&result);
        assert!(md.get(&id) > 0.0);
        assert_eq!(md.total_updates, 1);
    }

    #[test]
    fn momentum_reset() {
        let mut md = MomentumDynamics::default();
        let id = Uuid::new_v4();
        let mut activations = HashMap::new();
        activations.insert(id, 0.8);
        md.update(&activations);
        md.reset();
        assert_eq!(md.get(&id), 0.0);
        assert_eq!(md.total_updates, 0);
        assert_eq!(md.total_decays, 0);
        assert!(md.is_empty());
    }

    // ── Thalamic Gate Tests ───────────────────────────────────────────

    #[test]
    fn thalamic_default_context() {
        let gate = ThalamicGate::default();
        assert_eq!(gate.context(), CognitiveContext::Default);
    }

    #[test]
    fn thalamic_set_context() {
        let mut gate = ThalamicGate::default();
        gate.set_context(CognitiveContext::Coding);
        assert_eq!(gate.context(), CognitiveContext::Coding);
    }

    #[test]
    fn thalamic_coding_boosts_codex() {
        let mut gate = ThalamicGate::default();
        gate.set_context(CognitiveContext::Coding);
        let codex_w = gate.galaxy_weight(Galaxy::Codex);
        let dreams_w = gate.galaxy_weight(Galaxy::Dreams);
        assert!(codex_w > dreams_w, "coding should boost codex over dreams");
        assert!(codex_w > 1.0, "codex should be boosted above 1.0");
        assert!(dreams_w < 1.0, "dreams should be suppressed below 1.0");
    }

    #[test]
    fn thalamic_introspection_boosts_citta() {
        let mut gate = ThalamicGate::default();
        gate.set_context(CognitiveContext::Introspection);
        let citta_w = gate.galaxy_weight(Galaxy::Citta);
        let codex_w = gate.galaxy_weight(Galaxy::Codex);
        assert!(
            citta_w > codex_w,
            "introspection should boost citta over codex"
        );
        assert!(citta_w > 1.5, "citta should be strongly boosted");
    }

    #[test]
    fn thalamic_default_all_equal() {
        let gate = ThalamicGate::default();
        for g in Galaxy::memory_galaxies() {
            assert_eq!(
                gate.galaxy_weight(g),
                1.0,
                "default should weight all equally"
            );
        }
    }

    #[test]
    fn thalamic_compute_weights() {
        let mut gate = ThalamicGate::default();
        gate.set_context(CognitiveContext::Research);
        let weights = gate.compute_weights();
        assert_eq!(
            weights.len(),
            10,
            "should return weights for all memory galaxies"
        );
        assert!(weights[&Galaxy::Research] > weights[&Galaxy::Dreams]);
        assert_eq!(gate.total_calls, 1);
    }

    #[test]
    fn thalamic_apply_to_scores() {
        let mut gate = ThalamicGate::default();
        gate.set_context(CognitiveContext::Creative);
        let scores = vec![(Galaxy::Dreams, 1.0), (Galaxy::Codex, 1.0)];
        let result = gate.apply_to_scores(&scores);
        let dreams_score = result.iter().find(|(g, _)| *g == Galaxy::Dreams).unwrap().1;
        let codex_score = result.iter().find(|(g, _)| *g == Galaxy::Codex).unwrap().1;
        assert!(
            dreams_score > codex_score,
            "creative should boost dreams over codex"
        );
    }

    #[test]
    fn thalamic_context_all_variants() {
        for ctx in CognitiveContext::all() {
            let mut gate = ThalamicGate::new();
            gate.set_context(ctx);
            assert_eq!(gate.context(), ctx);
            let _ = gate.compute_weights();
        }
    }

    #[test]
    fn thalamic_cross_galaxy_factor() {
        let mut gate = ThalamicGate::default();
        gate.set_context(CognitiveContext::Coding);
        gate.set_cross_galaxy_factor(0.3);
        // Karma is not a memory galaxy, should use cross_galaxy_factor
        let w = gate.galaxy_weight(Galaxy::Karma);
        assert!((w - 0.3).abs() < f32::EPSILON);
    }

    // ── Predictive Coding Tests ───────────────────────────────────────

    #[test]
    fn predictive_empty_predict_returns_zeros() {
        let coder = PredictiveCoder::new(5, 4);
        let pred = coder.predict();
        assert_eq!(pred, vec![0.0; 4]);
    }

    #[test]
    fn predictive_observe_and_predict() {
        let mut coder = PredictiveCoder::new(5, 3);
        coder.observe(vec![1.0, 0.0, 0.0]);
        coder.observe(vec![0.0, 1.0, 0.0]);
        let pred = coder.predict();
        assert!((pred[0] - 0.5).abs() < 0.01);
        assert!((pred[1] - 0.5).abs() < 0.01);
    }

    #[test]
    fn predictive_error_zero_for_matching() {
        let mut coder = PredictiveCoder::new(5, 3);
        coder.observe(vec![1.0, 1.0, 1.0]);
        let error = coder.prediction_error(&[1.0, 1.0, 1.0]);
        assert!(
            error < 0.01,
            "matching embedding should have near-zero error"
        );
    }

    #[test]
    fn predictive_error_nonzero_for_different() {
        let mut coder = PredictiveCoder::new(5, 3);
        coder.observe(vec![1.0, 0.0, 0.0]);
        let error = coder.prediction_error(&[0.0, 1.0, 0.0]);
        assert!(error > 0.5, "different embedding should have high error");
    }

    #[test]
    fn predictive_window_eviction() {
        let mut coder = PredictiveCoder::new(2, 2);
        coder.observe(vec![1.0, 0.0]);
        coder.observe(vec![0.0, 1.0]);
        coder.observe(vec![1.0, 1.0]);
        // Window should only have last 2
        let pred = coder.predict();
        assert!((pred[0] - 0.5).abs() < 0.01);
        assert!((pred[1] - 1.0).abs() < 0.01);
    }

    #[test]
    fn predictive_process_returns_surprise_then_observes() {
        let mut coder = PredictiveCoder::new(3, 2);
        let s1 = coder.process(vec![1.0, 0.0]);
        // First prediction is zeros, so surprise should be high
        assert!(s1 > 0.5);
        assert_eq!(coder.context_len(), 1);
    }

    #[test]
    fn predictive_novelty_score_in_range() {
        let mut coder = PredictiveCoder::new(5, 3);
        coder.observe(vec![1.0, 0.0, 0.0]);
        let e = coder.prediction_error(&[1.0, 0.0, 0.0]);
        let n = coder.novelty_score(e);
        assert!(
            (0.0..=1.0).contains(&n),
            "novelty score should be in [0, 1]"
        );
    }

    #[test]
    fn predictive_novelty_higher_for_surprising() {
        let mut coder = PredictiveCoder::new(5, 3);
        // Train on consistent pattern
        coder.observe(vec![1.0, 0.0, 0.0]);
        coder.observe(vec![1.0, 0.0, 0.0]);
        let low_surprise = coder.prediction_error(&[1.0, 0.0, 0.0]);
        let high_surprise = coder.prediction_error(&[0.0, 0.0, 1.0]);
        let n_low = coder.novelty_score(low_surprise);
        let n_high = coder.novelty_score(high_surprise);
        assert!(
            n_high > n_low,
            "surprising embedding should have higher novelty"
        );
    }

    #[test]
    fn predictive_reset() {
        let mut coder = PredictiveCoder::new(5, 3);
        coder.observe(vec![1.0, 0.0, 0.0]);
        coder.prediction_error(&[1.0, 0.0, 0.0]);
        coder.reset();
        assert_eq!(coder.context_len(), 0);
        assert_eq!(coder.total_predictions, 0);
        assert_eq!(coder.avg_surprise(), 0.0);
    }

    #[test]
    fn predictive_avg_surprise() {
        let mut coder = PredictiveCoder::new(5, 2);
        coder.observe(vec![1.0, 0.0]);
        coder.prediction_error(&[1.0, 0.0]); // low error
        coder.prediction_error(&[0.0, 1.0]); // higher error
        let avg = coder.avg_surprise();
        assert!(avg > 0.0, "avg surprise should be positive");
    }
}
