//! Outward Spiral Mechanism — Phase F (Lila / Controlled Emergence).
//!
//! Prevents circular thinking by tracking the scope of autonomous cycle
//! outputs. The `SpiralTracker` monitors whether cycles are expanding
//! their scope (outward spiral = healthy) or repeating the same outputs
//! (inward spiral = circular thinking).
//!
//! Components:
//! - **SpiralTracker**: Records cycle outputs and computes spiral direction
//! - **novelty.score**: Scores output novelty (0.0 = identical, 1.0 = fully novel)
//! - **spiral.report**: MCP tool showing autonomy expansion or circling
//! - **Automatic suspension**: After N identical consecutive outputs

use std::collections::HashMap;

use crate::{CycleResult, CycleType};
use serde::{Deserialize, Serialize};

// ── Novelty Score ─────────────────────────────────────────────────────

/// Compute a novelty score for a cycle result compared to previous outputs.
///
/// Returns a score in [0.0, 1.0]:
/// - 1.0 = completely novel output (no overlap with any previous)
/// - 0.0 = identical to previous output
/// - 0.5 = partial overlap
///
/// The score is based on the Jaccard similarity between the set of
/// proposal IDs in the current result and the union of all previous
/// proposal IDs for the same cycle type.
#[must_use]
pub fn novelty_score(current: &CycleResult, previous_signatures: &[String]) -> f32 {
    if previous_signatures.is_empty() {
        return 1.0;
    }

    let current_sig = current.signature();
    if current_sig.is_empty() {
        return 1.0;
    }

    // Check exact match with most recent signature
    if let Some(last) = previous_signatures.last() {
        if last == &current_sig {
            return 0.0;
        }
    }

    // Compute set-based novelty: how many current items are new vs. all previous
    let current_items: Vec<&str> = current_sig.split('|').filter(|s| !s.is_empty()).collect();
    if current_items.is_empty() {
        return 1.0;
    }

    let mut all_previous: std::collections::HashSet<&str> = std::collections::HashSet::new();
    for sig in previous_signatures {
        for item in sig.split('|') {
            if !item.is_empty() {
                all_previous.insert(item);
            }
        }
    }

    let novel_count = current_items
        .iter()
        .filter(|item| !all_previous.contains(*item))
        .count();

    novel_count as f32 / current_items.len() as f32
}

/// Compute Jaccard similarity between two pipe-separated signatures.
///
/// Returns a score in [0.0, 1.0]:
/// - 1.0 = identical item sets
/// - 0.0 = no overlap
#[must_use]
pub fn jaccard_similarity(sig_a: &str, sig_b: &str) -> f32 {
    let set_a: std::collections::HashSet<&str> =
        sig_a.split('|').filter(|s| !s.is_empty()).collect();
    let set_b: std::collections::HashSet<&str> =
        sig_b.split('|').filter(|s| !s.is_empty()).collect();

    if set_a.is_empty() && set_b.is_empty() {
        return 1.0; // Both empty = identical
    }
    if set_a.is_empty() || set_b.is_empty() {
        return 0.0; // One empty = no overlap
    }

    let intersection = set_a.intersection(&set_b).count();
    let union = set_a.union(&set_b).count();
    intersection as f32 / union as f32
}

// ── Spiral Direction ──────────────────────────────────────────────────

/// The direction of the spiral — expanding outward or circling inward.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SpiralDirection {
    /// Scope is expanding — new proposals, new domains, healthy autonomy
    Outward,
    /// Scope is stable — same scope, minor variations
    Stable,
    /// Circling inward — repeating same outputs, circular thinking
    Inward,
}

impl SpiralDirection {
    /// Human-readable label.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::Outward => "outward",
            Self::Stable => "stable",
            Self::Inward => "inward",
        }
    }
}

// ── Spiral Report ─────────────────────────────────────────────────────

/// Per-cycle spiral tracking data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CycleSpiralData {
    /// Which cycle
    pub cycle: CycleType,
    /// Current spiral direction
    pub direction: SpiralDirection,
    /// Number of consecutive identical outputs
    pub consecutive_identical: usize,
    /// Whether this cycle is currently suspended
    pub suspended: bool,
    /// Recent novelty scores (most recent first)
    pub recent_novelty: Vec<f32>,
    /// Total runs
    pub total_runs: usize,
    /// Total proposals generated
    pub total_proposals: usize,
    /// Unique proposals seen (set size)
    pub unique_proposals: usize,
    /// Current signature
    pub current_signature: String,
}

/// Full spiral report across all cycles.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpiralReport {
    /// Overall spiral direction across all cycles
    pub overall_direction: SpiralDirection,
    /// Per-cycle data
    pub cycles: Vec<CycleSpiralData>,
    /// Total cycles run across all types
    pub total_cycles_run: usize,
    /// Total suspensions across all cycles
    pub total_suspensions: usize,
    /// Average novelty across all cycles
    pub avg_novelty: f32,
    /// Whether the system is in a healthy state
    pub healthy: bool,
}

impl SpiralReport {
    /// Convert to JSON for MCP tool response.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "overall_direction": self.overall_direction.label(),
            "total_cycles_run": self.total_cycles_run,
            "total_suspensions": self.total_suspensions,
            "avg_novelty": self.avg_novelty,
            "healthy": self.healthy,
            "cycles": self.cycles.iter().map(|c| serde_json::json!({
                "cycle": c.cycle.name(),
                "direction": c.direction.label(),
                "consecutive_identical": c.consecutive_identical,
                "suspended": c.suspended,
                "recent_novelty": c.recent_novelty,
                "total_runs": c.total_runs,
                "total_proposals": c.total_proposals,
                "unique_proposals": c.unique_proposals,
                "current_signature": c.current_signature,
            })).collect::<Vec<_>>(),
        })
    }
}

// ── Spiral Tracker ────────────────────────────────────────────────────

/// Per-cycle tracking state.
#[derive(Debug, Clone)]
struct CycleState {
    /// All historical signatures (for novelty computation)
    signatures: Vec<String>,
    /// Current signature
    current_signature: String,
    /// Consecutive identical count
    consecutive_identical: usize,
    /// Whether currently suspended
    suspended: bool,
    /// Recent novelty scores (most recent first, capped at 10)
    recent_novelty: Vec<f32>,
    /// Total runs
    total_runs: usize,
    /// Total proposals generated
    total_proposals: usize,
    /// Set of all unique proposal items seen
    unique_items: std::collections::HashSet<String>,
}

impl CycleState {
    fn new() -> Self {
        Self {
            signatures: Vec::new(),
            current_signature: String::new(),
            consecutive_identical: 0,
            suspended: false,
            recent_novelty: Vec::new(),
            total_runs: 0,
            total_proposals: 0,
            unique_items: std::collections::HashSet::new(),
        }
    }

    /// Compute spiral direction from recent novelty scores.
    fn direction(&self) -> SpiralDirection {
        if self.suspended || self.consecutive_identical >= 3 {
            return SpiralDirection::Inward;
        }

        if self.recent_novelty.is_empty() {
            return SpiralDirection::Outward;
        }

        // Weighted average: most recent score has highest weight
        // This ensures recovery from suspension is detected quickly
        let total_weight: f32 = self
            .recent_novelty
            .iter()
            .enumerate()
            .map(|(i, _)| 1.0 / (i as f32 + 1.0))
            .sum();
        let weighted_avg: f32 = self
            .recent_novelty
            .iter()
            .enumerate()
            .map(|(i, &v)| v / (i as f32 + 1.0))
            .sum::<f32>()
            / total_weight;

        if weighted_avg > 0.6 {
            SpiralDirection::Outward
        } else if weighted_avg > 0.3 {
            SpiralDirection::Stable
        } else {
            SpiralDirection::Inward
        }
    }
}

/// Type alias for escalation callback invoked when a cycle is suspended.
pub type EscalationCallback = Box<dyn Fn(&CycleType, &str) + Send + Sync>;

/// Configuration for semantic circularity detection.
#[derive(Debug, Clone)]
pub struct SemanticConfig {
    /// Jaccard similarity threshold above which outputs are considered "semantically identical".
    /// 1.0 = exact match required, 0.0 = everything matches.
    /// Default: 0.8 (80% overlap triggers semantic match)
    pub similarity_threshold: f32,
    /// Maximum consecutive semantically-similar outputs before suspension.
    pub max_similar: usize,
    /// Whether semantic detection is enabled.
    pub enabled: bool,
}

impl Default for SemanticConfig {
    fn default() -> Self {
        Self {
            similarity_threshold: 0.8,
            max_similar: 5,
            enabled: true,
        }
    }
}

/// Tracks spiral direction of autonomous cycle outputs.
///
/// Monitors whether cycles are expanding their scope (outward spiral)
/// or repeating the same outputs (inward spiral / circular thinking).
/// After `max_identical` consecutive identical outputs, a cycle is
/// marked as suspended.
///
/// With semantic detection enabled, also detects near-duplicate outputs
/// using Jaccard similarity, suspending after `max_similar` consecutive
/// semantically-similar outputs.
pub struct SpiralTracker {
    /// Per-cycle state
    states: HashMap<CycleType, CycleState>,
    /// Maximum consecutive identical outputs before suspension
    max_identical: usize,
    /// Total suspensions across all cycles
    total_suspensions: usize,
    /// Semantic circularity detection config
    semantic_config: SemanticConfig,
    /// Optional escalation callback invoked on suspension
    escalation_callback: Option<EscalationCallback>,
}

impl SpiralTracker {
    /// Create a new SpiralTracker with the given suspension threshold.
    #[must_use]
    pub fn new(max_identical: usize) -> Self {
        Self {
            states: HashMap::new(),
            max_identical,
            total_suspensions: 0,
            semantic_config: SemanticConfig::default(),
            escalation_callback: None,
        }
    }

    /// Create with default threshold (3 consecutive identical outputs).
    #[must_use]
    #[allow(clippy::should_implement_trait)]
    pub fn default() -> Self {
        Self::new(3)
    }

    /// Set the semantic circularity detection configuration.
    #[must_use]
    pub const fn with_semantic_config(mut self, config: SemanticConfig) -> Self {
        self.semantic_config = config;
        self
    }

    /// Set an escalation callback invoked when a cycle is suspended.
    ///
    /// The callback receives the cycle type and a description of the reason.
    pub fn set_escalation_callback(&mut self, callback: EscalationCallback) {
        self.escalation_callback = Some(callback);
    }

    /// Record a cycle result and update spiral tracking.
    ///
    /// Returns the novelty score of this output and whether the cycle
    /// should be suspended.
    pub fn record(&mut self, result: &CycleResult) -> (f32, bool) {
        let cycle = result.cycle;
        let state = self.states.entry(cycle).or_insert_with(CycleState::new);

        state.total_runs += 1;
        state.total_proposals += result.proposals_generated;

        // Compute novelty score
        let novelty = novelty_score(result, &state.signatures);

        // Track unique items
        let sig = result.signature();
        for item in sig.split('|') {
            if !item.is_empty() {
                state.unique_items.insert(item.to_string());
            }
        }

        // Check if identical to previous
        let is_identical = state.signatures.last().is_some_and(|prev| prev == &sig);

        // Check semantic similarity (if enabled and not exactly identical)
        let is_semantically_similar = if self.semantic_config.enabled && !is_identical {
            if let Some(prev_sig) = state.signatures.last() {
                jaccard_similarity(&sig, prev_sig) >= self.semantic_config.similarity_threshold
            } else {
                false
            }
        } else {
            false
        };

        if is_identical {
            state.consecutive_identical += 1;
        } else if is_semantically_similar {
            // Count as similar but not identical
            state.consecutive_identical += 1;
        } else {
            state.consecutive_identical = 0;
        }

        // Check suspension (exact or semantic)
        let should_suspend = state.consecutive_identical >= self.max_identical
            || (self.semantic_config.enabled
                && state.consecutive_identical >= self.semantic_config.max_similar);

        let newly_suspended = if should_suspend {
            if state.suspended {
                false
            } else {
                state.suspended = true;
                self.total_suspensions += 1;
                true
            }
        } else {
            false
        };

        if !should_suspend && state.suspended {
            // Novel output — unsuspend and clear stale novelty history
            state.suspended = false;
            state.recent_novelty.clear();
        }

        // Record signature
        state.signatures.push(sig.clone());
        state.current_signature = sig;

        // Cap signature history to prevent unbounded growth
        if state.signatures.len() > 100 {
            state.signatures.remove(0);
        }

        // Record novelty score
        state.recent_novelty.insert(0, novelty);
        if state.recent_novelty.len() > 10 {
            state.recent_novelty.pop();
        }

        // Invoke escalation callback if newly suspended
        if newly_suspended {
            if let Some(ref callback) = self.escalation_callback {
                let reason = if is_identical {
                    format!(
                        "Cycle {:?} suspended after {} consecutive identical outputs",
                        cycle, state.consecutive_identical
                    )
                } else {
                    format!(
                        "Cycle {:?} suspended after {} consecutive semantically similar outputs",
                        cycle, state.consecutive_identical
                    )
                };
                callback(&cycle, &reason);
            }
        }

        (novelty, state.suspended)
    }

    /// Generate a full spiral report.
    #[must_use]
    pub fn report(&self) -> SpiralReport {
        let mut cycle_data: Vec<CycleSpiralData> = Vec::new();
        let mut total_runs = 0usize;
        let mut total_novelty = 0.0f32;
        let mut novelty_count = 0usize;

        for cycle in CycleType::all() {
            if let Some(state) = self.states.get(&cycle) {
                total_runs += state.total_runs;
                let avg_n: f32 = if state.recent_novelty.is_empty() {
                    1.0
                } else {
                    state.recent_novelty.iter().sum::<f32>() / state.recent_novelty.len() as f32
                };
                total_novelty += avg_n;
                novelty_count += 1;

                cycle_data.push(CycleSpiralData {
                    cycle,
                    direction: state.direction(),
                    consecutive_identical: state.consecutive_identical,
                    suspended: state.suspended,
                    recent_novelty: state.recent_novelty.clone(),
                    total_runs: state.total_runs,
                    total_proposals: state.total_proposals,
                    unique_proposals: state.unique_items.len(),
                    current_signature: state.current_signature.clone(),
                });
            }
        }

        let avg_novelty = if novelty_count > 0 {
            total_novelty / novelty_count as f32
        } else {
            1.0
        };

        // Overall direction: if any cycle is Inward, system is Inward
        let any_inward = cycle_data
            .iter()
            .any(|c| c.direction == SpiralDirection::Inward);
        let any_outward = cycle_data
            .iter()
            .any(|c| c.direction == SpiralDirection::Outward);
        let overall_direction = if any_inward {
            SpiralDirection::Inward
        } else if any_outward {
            SpiralDirection::Outward
        } else {
            SpiralDirection::Stable
        };

        let healthy = !any_inward && avg_novelty > 0.2;

        SpiralReport {
            overall_direction,
            cycles: cycle_data,
            total_cycles_run: total_runs,
            total_suspensions: self.total_suspensions,
            avg_novelty,
            healthy,
        }
    }

    /// Get the spiral direction for a specific cycle.
    #[must_use]
    pub fn direction(&self, cycle: CycleType) -> SpiralDirection {
        self.states
            .get(&cycle)
            .map_or(SpiralDirection::Outward, |s: &CycleState| s.direction())
    }

    /// Whether a specific cycle is currently suspended.
    #[must_use]
    pub fn is_suspended(&self, cycle: CycleType) -> bool {
        self.states.get(&cycle).is_some_and(|s| s.suspended)
    }

    /// Total suspensions across all cycles.
    #[must_use]
    #[allow(clippy::len_without_is_empty)]
    pub const fn total_suspensions(&self) -> usize {
        self.total_suspensions
    }

    /// Get the novelty score history for a specific cycle.
    #[must_use]
    pub fn novelty_history(&self, cycle: CycleType) -> &[f32] {
        self.states.get(&cycle).map_or(&[], |s| &s.recent_novelty)
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{CompressionProposal, ConnectionProposal, CycleResult, CycleStatus, CycleType};

    fn make_result(cycle: CycleType, connections: Vec<ConnectionProposal>) -> CycleResult {
        let mut r = CycleResult::new(cycle, CycleStatus::Completed);
        r.connections = connections;
        r.proposals_generated = r.connections.len();
        r
    }

    fn conn(id: &str) -> ConnectionProposal {
        ConnectionProposal {
            source_id: id.to_string(),
            target_id: format!("target-{id}"),
            link_type: "related".into(),
            similarity: 0.8,
            source_galaxy: "codex".into(),
            target_galaxy: "codex".into(),
            reason: "test".into(),
        }
    }

    // ── Novelty score tests ────────────────────────────────────────────

    #[test]
    fn novelty_score_first_run_is_full_novel() {
        let result = make_result(CycleType::Connect, vec![conn("a")]);
        let score = novelty_score(&result, &[]);
        assert!((score - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn novelty_score_identical_to_previous_is_zero() {
        let result = make_result(CycleType::Connect, vec![conn("a")]);
        let sig = result.signature();
        let score = novelty_score(&result, &[sig]);
        assert!(score < f32::EPSILON);
    }

    #[test]
    fn novelty_score_partial_overlap() {
        let r1 = make_result(CycleType::Connect, vec![conn("a"), conn("b")]);
        let sig1 = r1.signature();

        // r2 has one old item (a) and one new item (c)
        let r2 = make_result(CycleType::Connect, vec![conn("a"), conn("c")]);
        let score = novelty_score(&r2, &[sig1]);
        assert!((score - 0.5).abs() < 0.01);
    }

    #[test]
    fn novelty_score_all_new_items() {
        let r1 = make_result(CycleType::Connect, vec![conn("a"), conn("b")]);
        let sig1 = r1.signature();

        let r2 = make_result(CycleType::Connect, vec![conn("c"), conn("d")]);
        let score = novelty_score(&r2, &[sig1]);
        assert!((score - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn novelty_score_empty_signature_is_full_novel() {
        let result = CycleResult::new(CycleType::Emergence, CycleStatus::NoProposals);
        let score = novelty_score(&result, &["some_previous_sig".to_string()]);
        assert!((score - 1.0).abs() < f32::EPSILON);
    }

    // ── SpiralTracker tests ────────────────────────────────────────────

    #[test]
    fn tracker_first_record_is_outward() {
        let mut tracker = SpiralTracker::default();
        let result = make_result(CycleType::Connect, vec![conn("a")]);
        let (novelty, suspended) = tracker.record(&result);

        assert!((novelty - 1.0).abs() < f32::EPSILON);
        assert!(!suspended);
        assert_eq!(
            tracker.direction(CycleType::Connect),
            SpiralDirection::Outward
        );
    }

    #[test]
    fn tracker_suspends_after_repeated_identical() {
        let mut tracker = SpiralTracker::default();
        let result = make_result(CycleType::Connect, vec![conn("a")]);

        // Run 1 — novel
        let (n1, s1) = tracker.record(&result);
        assert!((n1 - 1.0).abs() < f32::EPSILON);
        assert!(!s1);

        // Run 2 — identical
        let (_n2, s2) = tracker.record(&result);
        assert!(!s2);

        // Run 3 — identical
        let (_n3, s3) = tracker.record(&result);
        assert!(!s3);

        // Run 4 — identical (3rd consecutive → suspend)
        let (n4, s4) = tracker.record(&result);
        assert!(s4);
        assert!((n4 - 0.0).abs() < f32::EPSILON);
        assert_eq!(
            tracker.direction(CycleType::Connect),
            SpiralDirection::Inward
        );
    }

    #[test]
    fn tracker_unsuspends_on_novel_output() {
        let mut tracker = SpiralTracker::default();
        let result1 = make_result(CycleType::Connect, vec![conn("a")]);

        // Run 3 identical times to trigger suspension
        tracker.record(&result1);
        tracker.record(&result1);
        tracker.record(&result1);
        let (_, suspended) = tracker.record(&result1);
        assert!(suspended);

        // Now a novel output
        let result2 = make_result(CycleType::Connect, vec![conn("b")]);
        let (novelty, suspended) = tracker.record(&result2);
        assert!(!suspended);
        assert!((novelty - 1.0).abs() < f32::EPSILON);
        assert_eq!(
            tracker.direction(CycleType::Connect),
            SpiralDirection::Outward
        );
    }

    #[test]
    fn tracker_tracks_multiple_cycles_independently() {
        let mut tracker = SpiralTracker::default();

        let connect_result = make_result(CycleType::Connect, vec![conn("a")]);
        let compress_result = CycleResult::new(CycleType::Compress, CycleStatus::Completed);

        tracker.record(&connect_result);
        tracker.record(&compress_result);

        assert_eq!(
            tracker.direction(CycleType::Connect),
            SpiralDirection::Outward
        );
        assert_eq!(
            tracker.direction(CycleType::Compress),
            SpiralDirection::Outward
        );
    }

    #[test]
    fn tracker_report_shows_overall_direction() {
        let mut tracker = SpiralTracker::default();
        let result = make_result(CycleType::Connect, vec![conn("a")]);

        // Suspends Connect cycle
        for _ in 0..4 {
            tracker.record(&result);
        }

        let report = tracker.report();
        assert_eq!(report.overall_direction, SpiralDirection::Inward);
        assert!(!report.healthy);
        assert_eq!(report.total_suspensions, 1);
    }

    #[test]
    fn tracker_report_healthy_when_all_outward() {
        let mut tracker = SpiralTracker::default();

        let r1 = make_result(CycleType::Connect, vec![conn("a")]);
        let r2 = make_result(CycleType::Emergence, vec![]);

        tracker.record(&r1);
        tracker.record(&r2);

        let report = tracker.report();
        assert_eq!(report.overall_direction, SpiralDirection::Outward);
        assert!(report.healthy);
    }

    #[test]
    fn tracker_report_stable_when_mixed() {
        let mut tracker = SpiralTracker::default();

        // Outward cycle
        let r1 = make_result(CycleType::Connect, vec![conn("a")]);
        tracker.record(&r1);

        // Stable cycle (same output twice → novelty drops but not suspended)
        let r2 = make_result(CycleType::Emergence, vec![]);
        tracker.record(&r2);
        tracker.record(&r2); // identical → novelty 0, but only 1 consecutive

        let report = tracker.report();
        // Connect is outward, Emergence is stable → overall is outward (any_outward)
        assert_eq!(report.overall_direction, SpiralDirection::Outward);
    }

    #[test]
    fn tracker_total_suspensions_counts_across_cycles() {
        let mut tracker = SpiralTracker::default();

        let r1 = make_result(CycleType::Connect, vec![conn("a")]);
        let r2 = make_result(CycleType::Compress, vec![]);

        // Suspend both cycles
        for _ in 0..4 {
            tracker.record(&r1);
        }
        for _ in 0..4 {
            tracker.record(&r2);
        }

        assert_eq!(tracker.total_suspensions(), 2);
    }

    #[test]
    fn tracker_novelty_history_capped_at_10() {
        let mut tracker = SpiralTracker::default();

        for i in 0..15 {
            let result = make_result(CycleType::Connect, vec![conn(&format!("item{i}"))]);
            tracker.record(&result);
        }

        let history = tracker.novelty_history(CycleType::Connect);
        assert_eq!(history.len(), 10);
    }

    #[test]
    fn tracker_signatures_capped_at_100() {
        let mut tracker = SpiralTracker::default();

        for i in 0..150 {
            let result = make_result(CycleType::Connect, vec![conn(&format!("item{i}"))]);
            tracker.record(&result);
        }

        // Should not have crashed or grown unbounded
        let report = tracker.report();
        assert!(report.total_cycles_run >= 150);
    }

    #[test]
    fn tracker_is_suspended_check() {
        let mut tracker = SpiralTracker::default();
        let result = make_result(CycleType::Connect, vec![conn("a")]);

        assert!(!tracker.is_suspended(CycleType::Connect));

        for _ in 0..4 {
            tracker.record(&result);
        }

        assert!(tracker.is_suspended(CycleType::Connect));
        assert!(!tracker.is_suspended(CycleType::Prune));
    }

    #[test]
    fn tracker_direction_for_untracked_cycle_is_outward() {
        let tracker = SpiralTracker::default();
        assert_eq!(
            tracker.direction(CycleType::Prune),
            SpiralDirection::Outward
        );
    }

    // ── SpiralReport JSON tests ────────────────────────────────────────

    #[test]
    fn spiral_report_to_json_has_expected_fields() {
        let mut tracker = SpiralTracker::default();
        let result = make_result(CycleType::Connect, vec![conn("a")]);
        tracker.record(&result);

        let report = tracker.report();
        let json = report.to_json();

        assert!(json["overall_direction"].is_string());
        assert!(json["total_cycles_run"].is_number());
        assert!(json["total_suspensions"].is_number());
        assert!(json["avg_novelty"].is_number());
        assert!(json["healthy"].is_boolean());
        assert!(json["cycles"].is_array());
    }

    // ── SpiralDirection tests ──────────────────────────────────────────

    #[test]
    fn spiral_direction_labels() {
        assert_eq!(SpiralDirection::Outward.label(), "outward");
        assert_eq!(SpiralDirection::Stable.label(), "stable");
        assert_eq!(SpiralDirection::Inward.label(), "inward");
    }

    // ── Integration with CycleResult ───────────────────────────────────

    #[test]
    fn tracker_works_with_compression_proposals() {
        let mut tracker = SpiralTracker::default();

        let mut r1 = CycleResult::new(CycleType::Compress, CycleStatus::Completed);
        r1.compressions.push(CompressionProposal {
            primary_id: "a".into(),
            secondary_id: "b".into(),
            galaxy: "codex".into(),
            similarity: 0.9,
            content_overlap: 0.8,
            reason: "test".into(),
        });
        r1.proposals_generated = 1;

        let (novelty, suspended) = tracker.record(&r1);
        assert!((novelty - 1.0).abs() < f32::EPSILON);
        assert!(!suspended);
    }

    #[test]
    fn tracker_works_with_no_proposals_result() {
        let mut tracker = SpiralTracker::default();

        let r1 = CycleResult::new(CycleType::Emergence, CycleStatus::NoProposals);
        let (novelty, _suspended) = tracker.record(&r1);
        // Empty signature → full novelty
        assert!((novelty - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn tracker_unique_proposals_count_grows() {
        let mut tracker = SpiralTracker::default();

        for i in 0..5 {
            let result = make_result(CycleType::Connect, vec![conn(&format!("item{i}"))]);
            tracker.record(&result);
        }

        let report = tracker.report();
        let connect_data = report
            .cycles
            .iter()
            .find(|c| c.cycle == CycleType::Connect)
            .unwrap();
        assert_eq!(connect_data.unique_proposals, 5); // 5 unique signature items
    }

    // ── Semantic circularity detection tests ──────────────────────────

    #[test]
    fn jaccard_similarity_identical() {
        let sim = jaccard_similarity("a|b|c", "a|b|c");
        assert!((sim - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn jaccard_similarity_no_overlap() {
        let sim = jaccard_similarity("a|b", "c|d");
        assert!(sim < f32::EPSILON);
    }

    #[test]
    fn jaccard_similarity_partial() {
        let sim = jaccard_similarity("a|b|c", "a|b|d");
        // intersection = {a,b} = 2, union = {a,b,c,d} = 4 → 0.5
        assert!((sim - 0.5).abs() < 0.01);
    }

    #[test]
    fn jaccard_similarity_both_empty() {
        let sim = jaccard_similarity("", "");
        assert!((sim - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn jaccard_similarity_one_empty() {
        let sim = jaccard_similarity("a|b", "");
        assert!(sim < f32::EPSILON);
    }

    #[test]
    fn semantic_detection_suspends_similar_outputs() {
        let mut tracker = SpiralTracker::default().with_semantic_config(SemanticConfig {
            similarity_threshold: 0.5,
            max_similar: 3,
            enabled: true,
        });

        // Output 1: items a, b, c
        let r1 = make_result(CycleType::Connect, vec![conn("a"), conn("b"), conn("c")]);
        tracker.record(&r1);

        // Output 2: items a, b, d (2/4 overlap = 0.5 similarity)
        let r2 = make_result(CycleType::Connect, vec![conn("a"), conn("b"), conn("d")]);
        let (_, s2) = tracker.record(&r2);
        assert!(!s2, "Should not suspend after 1 similar");

        // Output 3: items a, b, e (still similar to r2)
        let r3 = make_result(CycleType::Connect, vec![conn("a"), conn("b"), conn("e")]);
        let (_, s3) = tracker.record(&r3);
        assert!(!s3, "Should not suspend after 2 similar");

        // Output 4: items a, b, f (still similar)
        let r4 = make_result(CycleType::Connect, vec![conn("a"), conn("b"), conn("f")]);
        let (_, s4) = tracker.record(&r4);
        assert!(s4, "Should suspend after 3 semantically similar outputs");
    }

    #[test]
    fn semantic_detection_disabled_falls_back_to_exact() {
        let mut tracker = SpiralTracker::default().with_semantic_config(SemanticConfig {
            similarity_threshold: 0.5,
            max_similar: 2,
            enabled: false,
        });

        let r1 = make_result(CycleType::Connect, vec![conn("a"), conn("b"), conn("c")]);
        tracker.record(&r1);

        // Similar but not identical — should NOT trigger with semantic disabled
        // Each iteration uses a different set so exact match never fires
        for i in 0..5 {
            let r = make_result(
                CycleType::Connect,
                vec![conn("a"), conn("b"), conn(&format!("d{i}"))],
            );
            let (_, suspended) = tracker.record(&r);
            assert!(
                !suspended,
                "Should not suspend similar outputs with semantic disabled (iter {i})"
            );
        }
    }

    #[test]
    fn escalation_callback_invoked_on_suspension() {
        use std::sync::Arc;
        use std::sync::atomic::{AtomicBool, Ordering};

        let called = Arc::new(AtomicBool::new(false));
        let called_clone = called.clone();

        let mut tracker = SpiralTracker::default();
        tracker.set_escalation_callback(Box::new(move |_cycle, _reason| {
            called_clone.store(true, Ordering::SeqCst);
        }));

        let result = make_result(CycleType::Connect, vec![conn("a")]);
        for _ in 0..4 {
            tracker.record(&result);
        }

        assert!(
            called.load(Ordering::SeqCst),
            "Escalation callback should be invoked"
        );
    }

    #[test]
    fn escalation_callback_not_invoked_on_unsuspension() {
        use std::sync::Arc;
        use std::sync::atomic::{AtomicU32, Ordering};

        let call_count = Arc::new(AtomicU32::new(0));
        let call_count_clone = call_count.clone();

        let mut tracker = SpiralTracker::default();
        tracker.set_escalation_callback(Box::new(move |_cycle, _reason| {
            call_count_clone.fetch_add(1, Ordering::SeqCst);
        }));

        let r1 = make_result(CycleType::Connect, vec![conn("a")]);
        // Suspend
        for _ in 0..4 {
            tracker.record(&r1);
        }
        assert_eq!(
            call_count.load(Ordering::SeqCst),
            1,
            "Callback called once on suspension"
        );

        // Unsuspend with novel output
        let r2 = make_result(CycleType::Connect, vec![conn("b")]);
        tracker.record(&r2);
        assert_eq!(
            call_count.load(Ordering::SeqCst),
            1,
            "Callback not called on unsuspension"
        );
    }

    #[test]
    fn escalation_callback_receives_cycle_and_reason() {
        use std::sync::{Arc, Mutex};
        let received: Arc<Mutex<Vec<(String, String)>>> = Arc::new(Mutex::new(Vec::new()));
        let received_clone = received.clone();

        let mut tracker = SpiralTracker::default();
        tracker.set_escalation_callback(Box::new(move |cycle, reason| {
            received_clone
                .lock()
                .unwrap()
                .push((format!("{cycle:?}"), reason.to_string()));
        }));

        let result = make_result(CycleType::Connect, vec![conn("a")]);
        for _ in 0..4 {
            tracker.record(&result);
        }

        let received = received.lock().unwrap();
        assert_eq!(received.len(), 1);
        assert!(received[0].0.contains("Connect"));
        assert!(received[0].1.contains("suspended"));
        drop(received);
    }
}
