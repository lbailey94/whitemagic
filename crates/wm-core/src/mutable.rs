//! Mutable Structures — Phase 6
//!
//! Makes previously fixed structures learnable:
//! 1. `GanaRegistry` — Gana taxonomy drift based on co-usage patterns
//! 2. `DynamicGalaxyRegistry` — Dynamic galaxy creation from memory clustering
//! 3. `LearnedDreamCycle` — Learned dream cycle phase selection
//! 4. `LearnedCycleStrategy` — Learned autonomous cycle strategies
//! 5. Phase effectiveness measurement and feedback

#![allow(clippy::significant_drop_tightening)]

use crate::Gana;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ── 6.1: GanaRegistry with Drift ──────────────────────────────────────

/// Tracks co-usage patterns between Ganas and allows taxonomy drift.
///
/// When two Ganas are frequently used together (e.g., memory.create + memory.search),
/// the registry records the co-usage. Over time, if a Gana pair exceeds a threshold,
/// the registry can suggest merging or reorganizing the taxonomy.
///
/// This implements the "mutable structures" principle: the taxonomy itself
/// becomes a learnable structure rather than a fixed design decision.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GanaRegistry {
    /// Co-usage matrix: "a:b" → count (string key for JSON serialization)
    co_usage: HashMap<String, u64>,
    /// Co-usage pair lookup: (a, b) → string key (not serialized, rebuilt on load)
    #[serde(skip)]
    co_usage_pairs: HashMap<(u8, u8), String>,
    /// Per-Gana total usage count
    usage_counts: HashMap<u8, u64>,
    /// Per-Gana success rate (rolling average)
    success_rates: HashMap<u8, f32>,
    /// Drift threshold — when co-usage exceeds this, suggest reorganization
    drift_threshold: u64,
    /// Whether drift is enabled
    drift_enabled: bool,
    /// Suggested merges from drift analysis
    suggested_merges: Vec<GanaMerge>,
}

/// A suggested Gana merge from drift analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GanaMerge {
    /// First Gana index
    pub gana_a: u8,
    /// Second Gana index
    pub gana_b: u8,
    /// Co-usage count
    pub co_usage_count: u64,
    /// Confidence (0.0-1.0)
    pub confidence: f32,
}

impl GanaRegistry {
    /// Create a new GanaRegistry with default settings.
    #[must_use]
    pub fn new() -> Self {
        Self {
            co_usage: HashMap::new(),
            co_usage_pairs: HashMap::new(),
            usage_counts: HashMap::new(),
            success_rates: HashMap::new(),
            drift_threshold: 100,
            drift_enabled: true,
            suggested_merges: Vec::new(),
        }
    }

    /// Create a registry with a custom drift threshold.
    #[must_use]
    pub fn with_threshold(drift_threshold: u64) -> Self {
        Self {
            co_usage: HashMap::new(),
            co_usage_pairs: HashMap::new(),
            usage_counts: HashMap::new(),
            success_rates: HashMap::new(),
            drift_threshold,
            drift_enabled: true,
            suggested_merges: Vec::new(),
        }
    }

    /// Record a tool dispatch within a Gana.
    pub fn record_usage(&mut self, gana: Gana, success: bool) {
        let idx = gana as u8;
        *self.usage_counts.entry(idx).or_insert(0) += 1;

        // Update success rate (rolling average)
        let current = self.success_rates.get(&idx).copied().unwrap_or(0.5);
        let count = self.usage_counts[&idx];
        let new_rate = if success {
            current + (1.0 - current) / count as f32
        } else {
            current * (1.0 - 1.0 / count as f32)
        };
        self.success_rates.insert(idx, new_rate);
    }

    /// Record co-usage of two Ganas in the same session/context.
    pub fn record_co_usage(&mut self, gana_a: Gana, gana_b: Gana) {
        let (a, b) = if gana_a as u8 <= gana_b as u8 {
            (gana_a as u8, gana_b as u8)
        } else {
            (gana_b as u8, gana_a as u8)
        };
        let key = format!("{a}:{b}");
        self.co_usage_pairs.insert((a, b), key.clone());
        *self.co_usage.entry(key).or_insert(0) += 1;

        // Check for drift
        if self.drift_enabled {
            let count = self.co_usage[&format!("{a}:{b}")];
            if count == self.drift_threshold {
                self.suggested_merges.push(GanaMerge {
                    gana_a: a,
                    gana_b: b,
                    co_usage_count: count,
                    confidence: 0.5,
                });
            } else if count > self.drift_threshold && count % self.drift_threshold == 0 {
                // Increase confidence
                if let Some(merge) = self
                    .suggested_merges
                    .iter_mut()
                    .find(|m| m.gana_a == a && m.gana_b == b)
                {
                    merge.co_usage_count = count;
                    merge.confidence = (merge.confidence + 0.1).min(1.0);
                }
            }
        }
    }

    /// Get the success rate for a Gana.
    #[must_use]
    pub fn success_rate(&self, gana: Gana) -> f32 {
        self.success_rates
            .get(&(gana as u8))
            .copied()
            .unwrap_or(0.5)
    }

    /// Get the usage count for a Gana.
    #[must_use]
    pub fn usage_count(&self, gana: Gana) -> u64 {
        self.usage_counts.get(&(gana as u8)).copied().unwrap_or(0)
    }

    /// Get all usage counts (Gana index → count).
    #[must_use]
    pub const fn usage_counts(&self) -> &HashMap<u8, u64> {
        &self.usage_counts
    }

    /// Get all co-usage counts (string key "a:b" → count).
    #[must_use]
    pub const fn co_usage(&self) -> &HashMap<String, u64> {
        &self.co_usage
    }

    /// Get the co-usage count between two Ganas.
    #[must_use]
    pub fn co_usage_count(&self, gana_a: Gana, gana_b: Gana) -> u64 {
        let (a, b) = if gana_a as u8 <= gana_b as u8 {
            (gana_a as u8, gana_b as u8)
        } else {
            (gana_b as u8, gana_a as u8)
        };
        self.co_usage_pairs
            .get(&(a, b))
            .and_then(|key| self.co_usage.get(key))
            .copied()
            .unwrap_or(0)
    }

    /// Get all suggested merges from drift analysis.
    #[must_use]
    pub fn suggested_merges(&self) -> &[GanaMerge] {
        &self.suggested_merges
    }

    /// Analyze drift and return the top N suggested reorganizations.
    #[must_use]
    pub fn analyze_drift(&self, top_n: usize) -> Vec<GanaMerge> {
        let mut merges = self.suggested_merges.clone();
        merges.sort_by(|a, b| b.co_usage_count.cmp(&a.co_usage_count));
        merges.truncate(top_n);
        merges
    }

    /// Rebuild the co_usage_pairs lookup from co_usage data.
    ///
    /// Call this after deserializing a GanaRegistry, since `co_usage_pairs`
    /// is skipped during serialization.
    pub fn rebuild_pairs(&mut self) {
        self.co_usage_pairs.clear();
        for key in self.co_usage.keys() {
            let parts: Vec<&str> = key.split(':').collect();
            if parts.len() == 2 {
                if let (Ok(a), Ok(b)) = (parts[0].parse::<u8>(), parts[1].parse::<u8>()) {
                    self.co_usage_pairs.insert((a, b), key.clone());
                }
            }
        }
    }

    /// Clear all co-usage data (e.g., after applying a reorganization).
    pub fn clear(&mut self) {
        self.co_usage.clear();
        self.co_usage_pairs.clear();
        self.usage_counts.clear();
        self.success_rates.clear();
        self.suggested_merges.clear();
    }

    /// Get a snapshot of the registry as JSON.
    #[must_use]
    pub fn snapshot(&self) -> serde_json::Value {
        serde_json::json!({
            "total_ganas_tracked": self.usage_counts.len(),
            "total_co_usage_pairs": self.co_usage.len(),
            "suggested_merges": self.suggested_merges.len(),
            "drift_threshold": self.drift_threshold,
            "drift_enabled": self.drift_enabled,
        })
    }
}

impl Default for GanaRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// ── 6.2: Dynamic Galaxy Registry ──────────────────────────────────────

/// A dynamically created galaxy from memory clustering.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DynamicGalaxy {
    /// Unique ID for the dynamic galaxy
    pub id: String,
    /// Human-readable name
    pub name: String,
    /// Description of what this galaxy contains
    pub description: String,
    /// Tags that triggered the clustering
    pub cluster_tags: Vec<String>,
    /// Number of memories in this cluster
    pub memory_count: usize,
    /// When this galaxy was created (Unix timestamp)
    pub created_at: u64,
    /// Effectiveness score (how useful this cluster has been)
    pub effectiveness: f32,
}

/// Registry for dynamic galaxies created from memory clustering.
///
/// Instead of a fixed set of 14 galaxies, the system can create new
/// virtual galaxies when memory clustering reveals natural groupings
/// that don't fit the existing taxonomy.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DynamicGalaxyRegistry {
    /// Registered dynamic galaxies
    galaxies: HashMap<String, DynamicGalaxy>,
    /// Minimum cluster size to create a dynamic galaxy
    min_cluster_size: usize,
    /// Maximum number of dynamic galaxies
    max_galaxies: usize,
    /// Effectiveness threshold for pruning
    prune_threshold: f32,
}

impl DynamicGalaxyRegistry {
    /// Create a new dynamic galaxy registry.
    #[must_use]
    pub fn new() -> Self {
        Self {
            galaxies: HashMap::new(),
            min_cluster_size: 10,
            max_galaxies: 20,
            prune_threshold: 0.1,
        }
    }

    /// Create a registry with custom settings.
    #[must_use]
    pub fn with_config(min_cluster_size: usize, max_galaxies: usize, prune_threshold: f32) -> Self {
        Self {
            galaxies: HashMap::new(),
            min_cluster_size,
            max_galaxies,
            prune_threshold,
        }
    }

    /// Try to create a dynamic galaxy from a memory cluster.
    ///
    /// Returns the created galaxy, or `None` if the cluster is too small
    /// or the registry is full.
    pub fn try_create(
        &mut self,
        name: &str,
        description: &str,
        cluster_tags: Vec<String>,
        memory_count: usize,
    ) -> Option<&DynamicGalaxy> {
        if memory_count < self.min_cluster_size {
            return None;
        }

        if self.galaxies.len() >= self.max_galaxies {
            // Try to prune ineffective galaxies first
            self.prune();
            if self.galaxies.len() >= self.max_galaxies {
                return None;
            }
        }

        let id = format!("dyn_{}", name.to_lowercase().replace(' ', "_"));
        if self.galaxies.contains_key(&id) {
            // Update existing
            if let Some(g) = self.galaxies.get_mut(&id) {
                g.memory_count = memory_count;
            }
            return self.galaxies.get(&id);
        }

        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);

        let galaxy = DynamicGalaxy {
            id: id.clone(),
            name: name.to_string(),
            description: description.to_string(),
            cluster_tags,
            memory_count,
            created_at: timestamp,
            effectiveness: 0.5,
        };

        self.galaxies.insert(id.clone(), galaxy);
        self.galaxies.get(&id)
    }

    /// Get a dynamic galaxy by ID.
    #[must_use]
    pub fn get(&self, id: &str) -> Option<&DynamicGalaxy> {
        self.galaxies.get(id)
    }

    /// Get all dynamic galaxies.
    #[must_use]
    pub fn all(&self) -> Vec<&DynamicGalaxy> {
        self.galaxies.values().collect()
    }

    /// Update the effectiveness of a dynamic galaxy.
    pub fn update_effectiveness(&mut self, id: &str, effectiveness: f32) {
        if let Some(g) = self.galaxies.get_mut(id) {
            g.effectiveness = effectiveness;
        }
    }

    /// Prune galaxies below the effectiveness threshold.
    ///
    /// Returns the number of galaxies pruned.
    pub fn prune(&mut self) -> usize {
        let before = self.galaxies.len();
        self.galaxies
            .retain(|_, g| g.effectiveness >= self.prune_threshold);
        before - self.galaxies.len()
    }

    /// Number of dynamic galaxies.
    #[must_use]
    pub fn len(&self) -> usize {
        self.galaxies.len()
    }

    /// Number of dynamic galaxies (alias for `len()`).
    #[must_use]
    pub fn galaxy_count(&self) -> usize {
        self.galaxies.len()
    }

    /// Whether the registry is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.galaxies.is_empty()
    }
}

impl Default for DynamicGalaxyRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// ── 6.3: Learned Dream Cycle ──────────────────────────────────────────

/// Effectiveness record for a dream phase.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhaseEffectiveness {
    /// Number of times this phase has run
    pub runs: u64,
    /// Number of times this phase produced useful results
    pub useful_results: u64,
    /// Average improvement score (0.0-1.0)
    pub avg_improvement: f32,
    /// Average duration in ms
    pub avg_duration_ms: u64,
}

impl PhaseEffectiveness {
    /// Create a new effectiveness record.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            runs: 0,
            useful_results: 0,
            avg_improvement: 0.0,
            avg_duration_ms: 0,
        }
    }

    /// Effectiveness score (0.0-1.0).
    #[must_use]
    pub fn score(&self) -> f32 {
        if self.runs == 0 {
            return 0.5;
        }
        let success_rate = self.useful_results as f32 / self.runs as f32;
        success_rate.midpoint(self.avg_improvement)
    }

    /// Record a phase execution.
    pub fn record(&mut self, useful: bool, improvement: f32, duration_ms: u64) {
        let n = self.runs as f32;
        self.avg_improvement = self.avg_improvement.mul_add(n, improvement) / (n + 1.0);
        self.avg_duration_ms =
            ((self.avg_duration_ms as f32).mul_add(n, duration_ms as f32) / (n + 1.0)) as u64;
        self.runs += 1;
        if useful {
            self.useful_results += 1;
        }
    }
}

impl Default for PhaseEffectiveness {
    fn default() -> Self {
        Self::new()
    }
}

/// Learned dream cycle — selects dream phases based on historical effectiveness.
///
/// Instead of running all 12 phases in fixed order, the learned dream cycle
/// uses historical effectiveness data to:
/// 1. Prioritize phases that have been most useful
/// 2. Skip phases with consistently low effectiveness
/// 3. Adapt the phase order based on current memory state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LearnedDreamCycle {
    /// Effectiveness records per phase (indexed by phase ordinal)
    phase_effectiveness: HashMap<u8, PhaseEffectiveness>,
    /// Minimum effectiveness to keep a phase in the cycle
    min_effectiveness: f32,
    /// Minimum runs before making skip decisions
    min_runs: u64,
    /// Whether learning is enabled
    learning_enabled: bool,
    /// Current phase ordering (learned)
    phase_order: Vec<u8>,
}

impl LearnedDreamCycle {
    /// Create a new learned dream cycle with all phases in default order.
    #[must_use]
    pub fn new() -> Self {
        let default_order: Vec<u8> = (0..12u8).collect();
        Self {
            phase_effectiveness: HashMap::new(),
            min_effectiveness: 0.2,
            min_runs: 5,
            learning_enabled: true,
            phase_order: default_order,
        }
    }

    /// Create with custom settings.
    #[must_use]
    pub fn with_config(min_effectiveness: f32, min_runs: u64, learning_enabled: bool) -> Self {
        Self {
            phase_effectiveness: HashMap::new(),
            min_effectiveness,
            min_runs,
            learning_enabled,
            phase_order: (0..12u8).collect(),
        }
    }

    /// Record a phase execution result.
    pub fn record_phase(
        &mut self,
        phase_idx: u8,
        useful: bool,
        improvement: f32,
        duration_ms: u64,
    ) {
        let record = self.phase_effectiveness.entry(phase_idx).or_default();
        record.record(useful, improvement, duration_ms);

        // Reorder phases if learning is enabled
        if self.learning_enabled {
            self.update_phase_order();
        }
    }

    /// Get the learned phase order (phases sorted by effectiveness, descending).
    #[must_use]
    pub fn phase_order(&self) -> &[u8] {
        &self.phase_order
    }

    /// Get the phases to run (filtering out ineffective ones).
    #[must_use]
    pub fn phases_to_run(&self) -> Vec<u8> {
        self.phase_order
            .iter()
            .filter(|&&idx| {
                if let Some(eff) = self.phase_effectiveness.get(&idx) {
                    if eff.runs >= self.min_runs {
                        return eff.score() >= self.min_effectiveness;
                    }
                }
                true // Keep phases without enough data
            })
            .copied()
            .collect()
    }

    /// Get effectiveness data for a phase.
    #[must_use]
    pub fn effectiveness(&self, phase_idx: u8) -> Option<&PhaseEffectiveness> {
        self.phase_effectiveness.get(&phase_idx)
    }

    /// Update the phase order based on effectiveness scores.
    fn update_phase_order(&mut self) {
        let mut scored: Vec<(u8, f32)> = (0..12u8)
            .map(|idx| {
                let score = self
                    .phase_effectiveness
                    .get(&idx)
                    .map_or(0.5, PhaseEffectiveness::score);
                (idx, score)
            })
            .collect();
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        self.phase_order = scored.into_iter().map(|(idx, _)| idx).collect();
    }

    /// Get a snapshot of all phase effectiveness data.
    #[must_use]
    pub fn snapshot(&self) -> serde_json::Value {
        let phases: Vec<serde_json::Value> = (0..12u8)
            .map(|idx| {
                if let Some(eff) = self.phase_effectiveness.get(&idx) {
                    serde_json::json!({
                        "phase": idx,
                        "runs": eff.runs,
                        "useful": eff.useful_results,
                        "score": eff.score(),
                        "avg_improvement": eff.avg_improvement,
                        "avg_duration_ms": eff.avg_duration_ms,
                    })
                } else {
                    serde_json::json!({"phase": idx, "runs": 0})
                }
            })
            .collect();

        serde_json::json!({
            "phases": phases,
            "phase_order": self.phase_order,
            "phases_to_run": self.phases_to_run(),
            "min_effectiveness": self.min_effectiveness,
            "learning_enabled": self.learning_enabled,
        })
    }
}

impl Default for LearnedDreamCycle {
    fn default() -> Self {
        Self::new()
    }
}

// ── 6.4: Learned Cycle Strategy ───────────────────────────────────────

/// Strategy for autonomous cycle selection.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CycleStrategy {
    /// Run all cycles in fixed order (default)
    FixedOrder,
    /// Run cycles based on priority learned from effectiveness
    PriorityBased,
    /// Run only the most effective cycle type
    BestOnly,
    /// Adaptive: use priority-based with exploration
    Adaptive,
}

/// Effectiveness record for an autonomous cycle type.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CycleEffectiveness {
    /// Number of times this cycle type has run
    pub runs: u64,
    /// Number of useful proposals generated
    pub proposals_generated: u64,
    /// Average usefulness score (0.0-1.0)
    pub avg_usefulness: f32,
    /// Average duration in ms
    pub avg_duration_ms: u64,
}

impl CycleEffectiveness {
    /// Create a new cycle effectiveness record.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            runs: 0,
            proposals_generated: 0,
            avg_usefulness: 0.0,
            avg_duration_ms: 0,
        }
    }

    /// Effectiveness score (0.0-1.0).
    #[must_use]
    pub fn score(&self) -> f32 {
        if self.runs == 0 {
            return 0.5;
        }
        let proposal_rate = self.proposals_generated as f32 / self.runs as f32;
        proposal_rate.midpoint(self.avg_usefulness)
    }

    /// Record a cycle execution.
    pub fn record(&mut self, proposals: u64, usefulness: f32, duration_ms: u64) {
        let n = self.runs as f32;
        self.avg_usefulness = self.avg_usefulness.mul_add(n, usefulness) / (n + 1.0);
        self.avg_duration_ms =
            ((self.avg_duration_ms as f32).mul_add(n, duration_ms as f32) / (n + 1.0)) as u64;
        self.runs += 1;
        self.proposals_generated += proposals;
    }
}

impl Default for CycleEffectiveness {
    fn default() -> Self {
        Self::new()
    }
}

/// Learned autonomous cycle strategy.
///
/// Instead of hardcoded cycle ordering, the bicameral system learns
/// which cycle types are most effective and adapts the strategy.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LearnedCycleStrategy {
    /// Effectiveness per cycle type (indexed by CycleType ordinal)
    cycle_effectiveness: HashMap<u8, CycleEffectiveness>,
    /// Current strategy
    strategy: CycleStrategy,
    /// Exploration rate (for Adaptive strategy)
    exploration_rate: f32,
    /// Minimum runs before switching from FixedOrder
    min_runs: u64,
    /// Learned priority order (cycle type ordinals, highest priority first)
    priority_order: Vec<u8>,
}

impl LearnedCycleStrategy {
    /// Create a new learned cycle strategy with default settings.
    #[must_use]
    pub fn new() -> Self {
        Self {
            cycle_effectiveness: HashMap::new(),
            strategy: CycleStrategy::FixedOrder,
            exploration_rate: 0.1,
            min_runs: 10,
            priority_order: (0..8u8).collect(),
        }
    }

    /// Create with a specific strategy.
    #[must_use]
    pub fn with_strategy(strategy: CycleStrategy) -> Self {
        Self {
            cycle_effectiveness: HashMap::new(),
            strategy,
            exploration_rate: 0.1,
            min_runs: 10,
            priority_order: (0..8u8).collect(),
        }
    }

    /// Record a cycle execution.
    pub fn record_cycle(
        &mut self,
        cycle_type_idx: u8,
        proposals: u64,
        usefulness: f32,
        duration_ms: u64,
    ) {
        let record = self.cycle_effectiveness.entry(cycle_type_idx).or_default();
        record.record(proposals, usefulness, duration_ms);

        // Update strategy based on data
        if self.strategy == CycleStrategy::FixedOrder {
            let total_runs: u64 = self.cycle_effectiveness.values().map(|e| e.runs).sum();
            if total_runs >= self.min_runs {
                self.strategy = CycleStrategy::PriorityBased;
                self.update_priority_order();
            }
        } else if matches!(
            self.strategy,
            CycleStrategy::PriorityBased | CycleStrategy::Adaptive
        ) {
            self.update_priority_order();
        }
    }

    /// Get the current strategy.
    #[must_use]
    pub const fn strategy(&self) -> CycleStrategy {
        self.strategy
    }

    /// Get the priority order for cycle execution.
    #[must_use]
    pub fn priority_order(&self) -> &[u8] {
        &self.priority_order
    }

    /// Get the cycle types to run, in order.
    ///
    /// For `FixedOrder`, returns all types in default order.
    /// For `PriorityBased`, returns types sorted by effectiveness.
    /// For `BestOnly`, returns only the top type.
    /// For `Adaptive`, returns priority order with occasional exploration.
    #[must_use]
    pub fn cycles_to_run(&self) -> Vec<u8> {
        match self.strategy {
            CycleStrategy::FixedOrder => (0..8u8).collect(),
            CycleStrategy::PriorityBased | CycleStrategy::Adaptive => {
                if self.strategy == CycleStrategy::Adaptive {
                    // With probability exploration_rate, include a random cycle
                    // (simplified: just return full priority order)
                }
                self.priority_order.clone()
            }
            CycleStrategy::BestOnly => self.priority_order.first().copied().into_iter().collect(),
        }
    }

    /// Get effectiveness data for a cycle type.
    #[must_use]
    pub fn effectiveness(&self, cycle_type_idx: u8) -> Option<&CycleEffectiveness> {
        self.cycle_effectiveness.get(&cycle_type_idx)
    }

    /// Set the strategy manually.
    pub fn set_strategy(&mut self, strategy: CycleStrategy) {
        self.strategy = strategy;
        if matches!(
            strategy,
            CycleStrategy::PriorityBased | CycleStrategy::Adaptive
        ) {
            self.update_priority_order();
        }
    }

    /// Update the priority order based on effectiveness scores.
    fn update_priority_order(&mut self) {
        let mut scored: Vec<(u8, f32)> = (0..8u8)
            .map(|idx| {
                let score = self
                    .cycle_effectiveness
                    .get(&idx)
                    .map_or(0.5, CycleEffectiveness::score);
                (idx, score)
            })
            .collect();
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        self.priority_order = scored.into_iter().map(|(idx, _)| idx).collect();
    }

    /// Get a snapshot of the strategy state.
    #[must_use]
    pub fn snapshot(&self) -> serde_json::Value {
        let cycles: Vec<serde_json::Value> = (0..8u8)
            .map(|idx| {
                if let Some(eff) = self.cycle_effectiveness.get(&idx) {
                    serde_json::json!({
                        "cycle_type": idx,
                        "runs": eff.runs,
                        "proposals": eff.proposals_generated,
                        "score": eff.score(),
                        "avg_usefulness": eff.avg_usefulness,
                    })
                } else {
                    serde_json::json!({"cycle_type": idx, "runs": 0})
                }
            })
            .collect();

        serde_json::json!({
            "strategy": format!("{:?}", self.strategy),
            "cycles": cycles,
            "priority_order": self.priority_order,
            "cycles_to_run": self.cycles_to_run(),
            "exploration_rate": self.exploration_rate,
        })
    }
}

impl Default for LearnedCycleStrategy {
    fn default() -> Self {
        Self::new()
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── GanaRegistry Tests ──

    #[test]
    fn gana_registry_record_usage() {
        let mut registry = GanaRegistry::new();
        registry.record_usage(Gana::Horn, true);
        registry.record_usage(Gana::Horn, true);
        registry.record_usage(Gana::Horn, false);

        assert_eq!(registry.usage_count(Gana::Horn), 3);
        let rate = registry.success_rate(Gana::Horn);
        assert!(rate > 0.5); // 2/3 success
    }

    #[test]
    fn gana_registry_co_usage() {
        let mut registry = GanaRegistry::new();
        registry.record_co_usage(Gana::Horn, Gana::Encampment);
        registry.record_co_usage(Gana::Horn, Gana::Encampment);
        registry.record_co_usage(Gana::Horn, Gana::Encampment);

        assert_eq!(registry.co_usage_count(Gana::Horn, Gana::Encampment), 3);
        // Order shouldn't matter
        assert_eq!(registry.co_usage_count(Gana::Encampment, Gana::Horn), 3);
    }

    #[test]
    fn gana_registry_drift_suggestion() {
        let mut registry = GanaRegistry::with_threshold(5);
        for _ in 0..5 {
            registry.record_co_usage(Gana::Horn, Gana::WinnowingBasket);
        }

        let merges = registry.suggested_merges();
        assert_eq!(merges.len(), 1);
        assert_eq!(merges[0].gana_a, Gana::Horn as u8);
        assert_eq!(merges[0].gana_b, Gana::WinnowingBasket as u8);
    }

    #[test]
    fn gana_registry_drift_confidence_increases() {
        let mut registry = GanaRegistry::with_threshold(5);
        for _ in 0..10 {
            registry.record_co_usage(Gana::Horn, Gana::WinnowingBasket);
        }

        let merges = registry.suggested_merges();
        assert_eq!(merges.len(), 1);
        assert!(merges[0].confidence > 0.5);
    }

    #[test]
    fn gana_registry_analyze_drift() {
        let mut registry = GanaRegistry::with_threshold(3);
        for _ in 0..5 {
            registry.record_co_usage(Gana::Horn, Gana::WinnowingBasket);
        }
        for _ in 0..3 {
            registry.record_co_usage(Gana::Ghost, Gana::Star);
        }

        let top = registry.analyze_drift(2);
        assert_eq!(top.len(), 2);
        // Horn-WinnowingBasket has more co-usage (5 > 3)
        assert!(top[0].co_usage_count >= top[1].co_usage_count);
    }

    #[test]
    fn gana_registry_clear() {
        let mut registry = GanaRegistry::new();
        registry.record_usage(Gana::Horn, true);
        registry.record_co_usage(Gana::Horn, Gana::Neck);
        registry.clear();

        assert_eq!(registry.usage_count(Gana::Horn), 0);
        assert_eq!(registry.co_usage_count(Gana::Horn, Gana::Neck), 0);
    }

    #[test]
    fn gana_registry_snapshot() {
        let mut registry = GanaRegistry::new();
        registry.record_usage(Gana::Horn, true);
        let snap = registry.snapshot();
        assert!(snap.get("total_ganas_tracked").is_some());
    }

    // ── DynamicGalaxyRegistry Tests ──

    #[test]
    fn dynamic_galaxy_create() {
        let mut registry = DynamicGalaxyRegistry::with_config(5, 10, 0.1);
        let galaxy = registry.try_create(
            "Rust Patterns",
            "Memories about Rust design patterns",
            vec!["rust".to_string(), "patterns".to_string()],
            15,
        );
        assert!(galaxy.is_some());
        assert_eq!(galaxy.unwrap().name, "Rust Patterns");
        assert_eq!(registry.len(), 1);
    }

    #[test]
    fn dynamic_galaxy_too_small() {
        let mut registry = DynamicGalaxyRegistry::with_config(10, 5, 0.1);
        let galaxy = registry.try_create("Small", "Too small", vec![], 3);
        assert!(galaxy.is_none());
        assert!(registry.is_empty());
    }

    #[test]
    fn dynamic_galaxy_max_limit() {
        let mut registry = DynamicGalaxyRegistry::with_config(1, 2, 0.0);
        registry.try_create("G1", "desc", vec![], 5);
        registry.try_create("G2", "desc", vec![], 5);
        registry.try_create("G3", "desc", vec![], 5);
        assert_eq!(registry.len(), 2); // Max 2
    }

    #[test]
    fn dynamic_galaxy_prune() {
        let mut registry = DynamicGalaxyRegistry::with_config(1, 10, 0.5);
        registry.try_create("G1", "desc", vec![], 5);
        registry.try_create("G2", "desc", vec![], 5);
        registry.update_effectiveness("dyn_g1", 0.1); // Below threshold
        registry.update_effectiveness("dyn_g2", 0.8); // Above threshold

        let pruned = registry.prune();
        assert_eq!(pruned, 1);
        assert_eq!(registry.len(), 1);
        assert!(registry.get("dyn_g2").is_some());
    }

    #[test]
    fn dynamic_galaxy_update_existing() {
        let mut registry = DynamicGalaxyRegistry::with_config(1, 10, 0.0);
        registry.try_create("Test", "desc", vec![], 5);
        registry.try_create("Test", "desc", vec![], 10);
        let g = registry.get("dyn_test").unwrap();
        assert_eq!(g.memory_count, 10);
        assert_eq!(registry.len(), 1);
    }

    // ── LearnedDreamCycle Tests ──

    #[test]
    fn learned_dream_default_order() {
        let cycle = LearnedDreamCycle::new();
        assert_eq!(cycle.phase_order(), &[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
    }

    #[test]
    fn learned_dream_record_phase() {
        let mut cycle = LearnedDreamCycle::new();
        cycle.record_phase(0, true, 0.8, 100);
        cycle.record_phase(0, true, 0.9, 120);

        let eff = cycle.effectiveness(0).unwrap();
        assert_eq!(eff.runs, 2);
        assert_eq!(eff.useful_results, 2);
        assert!((eff.avg_improvement - 0.85).abs() < 0.01);
    }

    #[test]
    fn learned_dream_reorders_by_effectiveness() {
        let mut cycle = LearnedDreamCycle::new();

        // Phase 5 has high effectiveness
        for _ in 0..10 {
            cycle.record_phase(5, true, 0.9, 50);
        }

        // Phase 0 has low effectiveness
        for _ in 0..10 {
            cycle.record_phase(0, false, 0.1, 200);
        }

        let order = cycle.phase_order();
        // Phase 5 should come before phase 0
        let pos5 = order.iter().position(|&x| x == 5).unwrap();
        let pos0 = order.iter().position(|&x| x == 0).unwrap();
        assert!(pos5 < pos0);
    }

    #[test]
    fn learned_dream_filters_ineffective() {
        let mut cycle = LearnedDreamCycle::with_config(0.5, 5, true);

        // Phase 3 is consistently bad
        for _ in 0..10 {
            cycle.record_phase(3, false, 0.1, 200);
        }

        let to_run = cycle.phases_to_run();
        // Phase 3 should be filtered out
        assert!(!to_run.contains(&3));
    }

    #[test]
    fn learned_dream_keeps_phases_without_data() {
        let cycle = LearnedDreamCycle::new();
        let to_run = cycle.phases_to_run();
        // All phases should be included when there's no data
        assert_eq!(to_run.len(), 12);
    }

    #[test]
    fn learned_dream_snapshot() {
        let mut cycle = LearnedDreamCycle::new();
        cycle.record_phase(0, true, 0.8, 100);
        let snap = cycle.snapshot();
        assert!(snap.get("phases").is_some());
    }

    // ── PhaseEffectiveness Tests ──

    #[test]
    fn phase_effectiveness_score() {
        let mut eff = PhaseEffectiveness::new();
        assert!((eff.score() - 0.5).abs() < 0.01); // Default for 0 runs

        eff.record(true, 0.8, 100);
        eff.record(true, 0.9, 120);
        eff.record(false, 0.1, 50);

        // score = (success_rate + avg_improvement) / 2
        // success_rate = 2/3, avg_improvement = (0.8+0.9+0.1)/3 ≈ 0.6
        let score = eff.score();
        assert!(score > 0.5);
    }

    // ── LearnedCycleStrategy Tests ──

    #[test]
    fn cycle_strategy_default_is_fixed() {
        let strategy = LearnedCycleStrategy::new();
        assert_eq!(strategy.strategy(), CycleStrategy::FixedOrder);
        assert_eq!(strategy.priority_order().len(), 8);
    }

    #[test]
    fn cycle_strategy_transitions_to_priority() {
        let mut strategy = LearnedCycleStrategy::new();
        // Record enough cycles to trigger transition
        for _ in 0..15 {
            strategy.record_cycle(0, 2, 0.8, 100);
        }
        assert_eq!(strategy.strategy(), CycleStrategy::PriorityBased);
    }

    #[test]
    fn cycle_strategy_priority_order() {
        let mut strategy = LearnedCycleStrategy::with_strategy(CycleStrategy::PriorityBased);

        // Cycle type 3 is most effective
        for _ in 0..10 {
            strategy.record_cycle(3, 5, 0.9, 100);
        }
        // Cycle type 0 is least effective
        for _ in 0..10 {
            strategy.record_cycle(0, 0, 0.1, 200);
        }

        let order = strategy.priority_order();
        assert_eq!(order[0], 3); // Best cycle first
    }

    #[test]
    fn cycle_strategy_best_only() {
        let mut strategy = LearnedCycleStrategy::with_strategy(CycleStrategy::BestOnly);

        for _ in 0..5 {
            strategy.record_cycle(2, 3, 0.8, 100);
        }
        for _ in 0..5 {
            strategy.record_cycle(5, 1, 0.3, 100);
        }

        // record_cycle updates priority_order when strategy is PriorityBased or Adaptive
        // but BestOnly doesn't auto-update. Set to Adaptive first, then back.
        strategy.set_strategy(CycleStrategy::Adaptive);
        strategy.set_strategy(CycleStrategy::BestOnly);

        let to_run = strategy.cycles_to_run();
        assert_eq!(to_run.len(), 1);
        assert_eq!(to_run[0], 2); // Best cycle
    }

    #[test]
    fn cycle_strategy_fixed_order_returns_all() {
        let strategy = LearnedCycleStrategy::with_strategy(CycleStrategy::FixedOrder);
        let to_run = strategy.cycles_to_run();
        assert_eq!(to_run.len(), 8);
    }

    #[test]
    fn cycle_strategy_set_strategy() {
        let mut strategy = LearnedCycleStrategy::new();
        strategy.set_strategy(CycleStrategy::Adaptive);
        assert_eq!(strategy.strategy(), CycleStrategy::Adaptive);
    }

    #[test]
    fn cycle_strategy_snapshot() {
        let mut strategy = LearnedCycleStrategy::new();
        strategy.record_cycle(0, 2, 0.8, 100);
        let snap = strategy.snapshot();
        assert!(snap.get("strategy").is_some());
    }

    #[test]
    fn cycle_effectiveness_score() {
        let mut eff = CycleEffectiveness::new();
        assert!((eff.score() - 0.5).abs() < 0.01);

        eff.record(3, 0.8, 100);
        eff.record(0, 0.2, 200);

        let score = eff.score();
        // proposal_rate = 3/2 = 1.5, avg_usefulness = 0.5
        // score = (1.5 + 0.5) / 2 = 1.0 (capped conceptually)
        assert!(score > 0.5);
    }

    // ── Serialization Tests ──

    #[test]
    fn gana_registry_serialization() {
        let mut registry = GanaRegistry::new();
        registry.record_usage(Gana::Horn, true);
        registry.record_co_usage(Gana::Horn, Gana::Neck);

        let json = serde_json::to_string(&registry).unwrap();
        let mut back: GanaRegistry = serde_json::from_str(&json).unwrap();
        back.rebuild_pairs();
        assert_eq!(back.usage_count(Gana::Horn), 1);
        assert_eq!(back.co_usage_count(Gana::Horn, Gana::Neck), 1);
    }

    #[test]
    fn dynamic_galaxy_registry_serialization() {
        let mut registry = DynamicGalaxyRegistry::new();
        registry.try_create("Test", "desc", vec!["tag".to_string()], 15);

        let json = serde_json::to_string(&registry).unwrap();
        let back: DynamicGalaxyRegistry = serde_json::from_str(&json).unwrap();
        assert_eq!(back.len(), 1);
    }

    #[test]
    fn learned_dream_cycle_serialization() {
        let mut cycle = LearnedDreamCycle::new();
        cycle.record_phase(0, true, 0.8, 100);

        let json = serde_json::to_string(&cycle).unwrap();
        let back: LearnedDreamCycle = serde_json::from_str(&json).unwrap();
        assert_eq!(back.effectiveness(0).unwrap().runs, 1);
    }

    #[test]
    fn learned_cycle_strategy_serialization() {
        let mut strategy = LearnedCycleStrategy::new();
        strategy.record_cycle(0, 2, 0.8, 100);

        let json = serde_json::to_string(&strategy).unwrap();
        let back: LearnedCycleStrategy = serde_json::from_str(&json).unwrap();
        assert_eq!(back.effectiveness(0).unwrap().runs, 1);
    }
}
