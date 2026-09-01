//! Scenario Evaluator — multi-criteria scoring for imagined scenarios.
//!
//! Scores predicted outcomes using weighted criteria:
//! - Goal progress: how much does this scenario advance the goal?
//! - Risk avoidance: how safe is this path?
//! - Novelty: does this scenario explore new territory?
//!
//! Inspired by MAP (Nature Communications 2025) state evaluation module.

use serde::{Deserialize, Serialize};

use crate::world_model::PredictedState;

/// Configuration for the scenario evaluator.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluatorConfig {
    /// Weight for goal progress (0.0–1.0).
    pub goal_weight: f32,
    /// Weight for risk avoidance (0.0–1.0).
    pub risk_weight: f32,
    /// Weight for novelty/exploration (0.0–1.0).
    pub novelty_weight: f32,
    /// Weight for confidence (0.0–1.0).
    pub confidence_weight: f32,
}

impl Default for EvaluatorConfig {
    fn default() -> Self {
        Self {
            goal_weight: 0.4,
            risk_weight: 0.25,
            novelty_weight: 0.2,
            confidence_weight: 0.15,
        }
    }
}

/// Multi-criteria scenario evaluator.
///
/// Scores a scenario's predicted trajectory by combining:
/// 1. **Goal progress** — average goal_progress across trajectory steps
/// 2. **Risk penalty** — fraction of steps with risk factors
/// 3. **Novelty** — assessed by comparing to historical context
/// 4. **Confidence** — average prediction confidence
pub struct ScenarioEvaluator {
    config: EvaluatorConfig,
    /// Historical success rate of similar actions (from memory, 0.0–1.0).
    success_rate: f32,
}

impl ScenarioEvaluator {
    /// Create a new evaluator with the given config.
    #[must_use]
    pub const fn new(config: EvaluatorConfig) -> Self {
        Self {
            config,
            success_rate: 0.5,
        }
    }

    /// Create an evaluator with default config.
    #[must_use]
    pub fn with_defaults() -> Self {
        Self::new(EvaluatorConfig::default())
    }

    /// Set the historical success rate.
    #[must_use]
    pub const fn with_success_rate(mut self, rate: f32) -> Self {
        self.success_rate = rate.clamp(0.0, 1.0);
        self
    }

    /// Score a scenario's predicted trajectory.
    ///
    /// Returns a score in [0.0, 1.0] where higher is better.
    #[must_use]
    pub fn score(&self, trajectory: &[PredictedState], goal: &str) -> f32 {
        if trajectory.is_empty() {
            return 0.0;
        }

        let goal_score = self.score_goal_progress(trajectory);
        let risk_score = self.score_risk(trajectory);
        let novelty_score = self.score_novelty(trajectory, goal);
        let confidence_score = self.score_confidence(trajectory);

        let total = self.config.confidence_weight.mul_add(
            confidence_score,
            self.config.novelty_weight.mul_add(
                novelty_score,
                self.config
                    .goal_weight
                    .mul_add(goal_score, self.config.risk_weight * risk_score),
            ),
        );

        // Blend with historical success rate (10% influence)
        let blended = total.mul_add(0.9, self.success_rate * 0.1);

        blended.clamp(0.0, 1.0)
    }

    /// Assess novelty by comparing to historical patterns.
    ///
    /// Returns 0.0 (completely familiar) to 1.0 (entirely novel).
    #[must_use]
    pub fn novelty(&self, action: &str, memory_context: &str) -> f32 {
        if memory_context.is_empty() {
            // No history → everything is novel
            return 1.0;
        }

        // Simple novelty: how much does the action overlap with memory context?
        let action_words: std::collections::HashSet<String> =
            action.split_whitespace().map(str::to_lowercase).collect();
        let context_words: std::collections::HashSet<String> = memory_context
            .split_whitespace()
            .map(str::to_lowercase)
            .collect();

        if action_words.is_empty() {
            return 0.0;
        }

        let overlap = action_words.intersection(&context_words).count();
        let novelty = 1.0 - (overlap as f32 / action_words.len() as f32);

        novelty.clamp(0.0, 1.0)
    }

    /// Get the evaluator configuration.
    #[must_use]
    pub const fn config(&self) -> &EvaluatorConfig {
        &self.config
    }

    /// Get the historical success rate.
    #[must_use]
    pub const fn success_rate(&self) -> f32 {
        self.success_rate
    }

    // ── Individual scoring functions ───────────────────────────────────

    fn score_goal_progress(&self, trajectory: &[PredictedState]) -> f32 {
        let avg: f32 =
            trajectory.iter().map(|p| p.goal_progress).sum::<f32>() / trajectory.len() as f32;
        // Bonus for improving across trajectory
        let first = trajectory.first().map_or(0.0, |p| p.goal_progress);
        let last = trajectory.last().map_or(0.0, |p| p.goal_progress);
        let improvement_bonus = ((last - first) * 0.2).max(0.0);
        (avg + improvement_bonus).clamp(0.0, 1.0)
    }

    fn score_risk(&self, trajectory: &[PredictedState]) -> f32 {
        // Risk score: 1.0 = no risks, 0.0 = all steps have risks
        let risky_steps = trajectory.iter().filter(|p| p.has_risk()).count();
        let risk_fraction = risky_steps as f32 / trajectory.len() as f32;
        1.0 - risk_fraction
    }

    fn score_novelty(&self, trajectory: &[PredictedState], goal: &str) -> f32 {
        // Novelty from diversity of changes across trajectory
        let mut all_changes: std::collections::HashSet<&str> = std::collections::HashSet::new();
        for p in trajectory {
            for c in &p.changes {
                all_changes.insert(c.as_str());
            }
        }
        // More unique changes = more novel exploration
        let change_diversity = all_changes.len() as f32 / (trajectory.len() * 3).max(1) as f32;
        // Also factor in goal-relevance: if changes mention goal words, slightly lower novelty
        let goal_words: std::collections::HashSet<String> =
            goal.split_whitespace().map(str::to_lowercase).collect();
        let goal_relevant = all_changes
            .iter()
            .filter(|c| {
                c.split_whitespace()
                    .any(|w| goal_words.contains(&w.to_lowercase()))
            })
            .count();
        let relevance_penalty = goal_relevant as f32 * 0.05;

        (change_diversity - relevance_penalty).clamp(0.0, 1.0)
    }

    fn score_confidence(&self, trajectory: &[PredictedState]) -> f32 {
        trajectory.iter().map(|p| p.confidence).sum::<f32>() / trajectory.len() as f32
    }
}

/// Detailed score breakdown for a scenario.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoreBreakdown {
    /// Overall score (weighted combination).
    pub overall: f32,
    /// Goal progress component.
    pub goal_progress: f32,
    /// Risk avoidance component.
    pub risk_avoidance: f32,
    /// Novelty component.
    pub novelty: f32,
    /// Confidence component.
    pub confidence: f32,
}

impl ScenarioEvaluator {
    /// Score a trajectory with detailed breakdown.
    #[must_use]
    pub fn score_detailed(&self, trajectory: &[PredictedState], goal: &str) -> ScoreBreakdown {
        if trajectory.is_empty() {
            return ScoreBreakdown {
                overall: 0.0,
                goal_progress: 0.0,
                risk_avoidance: 0.0,
                novelty: 0.0,
                confidence: 0.0,
            };
        }

        let goal_progress = self.score_goal_progress(trajectory);
        let risk_avoidance = self.score_risk(trajectory);
        let novelty = self.score_novelty(trajectory, goal);
        let confidence = self.score_confidence(trajectory);

        let overall = self
            .config
            .confidence_weight
            .mul_add(
                confidence,
                self.config.novelty_weight.mul_add(
                    novelty,
                    self.config
                        .goal_weight
                        .mul_add(goal_progress, self.config.risk_weight * risk_avoidance),
                ),
            )
            .clamp(0.0, 1.0);

        ScoreBreakdown {
            overall,
            goal_progress,
            risk_avoidance,
            novelty,
            confidence,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::world_model::PredictedState;

    fn make_trajectory(
        progress: &[f32],
        confidence: &[f32],
        risks: &[bool],
    ) -> Vec<PredictedState> {
        progress
            .iter()
            .zip(confidence.iter())
            .zip(risks.iter())
            .map(|((&p, &c), &r)| PredictedState {
                description: format!("step p={p} c={c}"),
                confidence: c,
                changes: vec!["change_a".into()],
                risks: if r { vec!["risk".into()] } else { vec![] },
                goal_progress: p,
            })
            .collect()
    }

    // ── Basic scoring tests ────────────────────────────────────────────

    #[test]
    fn empty_trajectory_scores_zero() {
        let evaluator = ScenarioEvaluator::with_defaults();
        assert_eq!(evaluator.score(&[], "goal"), 0.0);
    }

    #[test]
    fn perfect_trajectory_scores_high() {
        let evaluator = ScenarioEvaluator::with_defaults();
        let traj = make_trajectory(&[0.8, 0.9, 1.0], &[0.9, 0.9, 0.9], &[false, false, false]);
        let score = evaluator.score(&traj, "goal");
        assert!(
            score > 0.7,
            "perfect trajectory should score high, got {score}"
        );
    }

    #[test]
    fn risky_trajectory_scores_lower() {
        let evaluator = ScenarioEvaluator::with_defaults();
        let safe = make_trajectory(&[0.5, 0.6], &[0.8, 0.8], &[false, false]);
        let risky = make_trajectory(&[0.5, 0.6], &[0.8, 0.8], &[true, true]);
        let safe_score = evaluator.score(&safe, "goal");
        let risky_score = evaluator.score(&risky, "goal");
        assert!(
            safe_score > risky_score,
            "safe ({safe_score}) should beat risky ({risky_score})"
        );
    }

    #[test]
    fn improving_trajectory_gets_bonus() {
        let evaluator = ScenarioEvaluator::with_defaults();
        let flat = make_trajectory(&[0.5, 0.5], &[0.7, 0.7], &[false, false]);
        let improving = make_trajectory(&[0.3, 0.8], &[0.7, 0.7], &[false, false]);
        let flat_score = evaluator.score(&flat, "goal");
        let improving_score = evaluator.score(&improving, "goal");
        assert!(
            improving_score >= flat_score,
            "improving ({improving_score}) should >= flat ({flat_score})"
        );
    }

    // ── Novelty tests ──────────────────────────────────────────────────

    #[test]
    fn novelty_empty_context_is_one() {
        let evaluator = ScenarioEvaluator::with_defaults();
        assert_eq!(evaluator.novelty("new action", ""), 1.0);
    }

    #[test]
    fn novelty_identical_to_context_is_zero() {
        let evaluator = ScenarioEvaluator::with_defaults();
        assert!((evaluator.novelty("run task", "run task") - 0.0).abs() < 0.01);
    }

    #[test]
    fn novelty_partial_overlap() {
        let evaluator = ScenarioEvaluator::with_defaults();
        let n = evaluator.novelty("run new task", "run old task");
        // "run" overlaps, "new" and "task" — "task" overlaps too
        // 2/3 overlap → 1/3 novelty
        assert!(n > 0.0 && n < 1.0, "partial overlap novelty: {n}");
    }

    #[test]
    fn novelty_empty_action_is_zero() {
        let evaluator = ScenarioEvaluator::with_defaults();
        assert_eq!(evaluator.novelty("", "some context"), 0.0);
    }

    // ── Config tests ───────────────────────────────────────────────────

    #[test]
    fn default_config_weights_sum_to_one() {
        let config = EvaluatorConfig::default();
        let sum = config.goal_weight
            + config.risk_weight
            + config.novelty_weight
            + config.confidence_weight;
        assert!(
            (sum - 1.0).abs() < 0.01,
            "weights should sum to 1.0, got {sum}"
        );
    }

    #[test]
    fn custom_config() {
        let config = EvaluatorConfig {
            goal_weight: 0.5,
            risk_weight: 0.3,
            novelty_weight: 0.1,
            confidence_weight: 0.1,
        };
        let evaluator = ScenarioEvaluator::new(config);
        let traj = make_trajectory(&[0.8], &[0.9], &[false]);
        let score = evaluator.score(&traj, "goal");
        assert!(score > 0.5);
    }

    // ── Success rate tests ─────────────────────────────────────────────

    #[test]
    fn success_rate_influences_score() {
        let low = ScenarioEvaluator::with_defaults().with_success_rate(0.1);
        let high = ScenarioEvaluator::with_defaults().with_success_rate(0.9);
        let traj = make_trajectory(&[0.5], &[0.5], &[false]);
        let low_score = low.score(&traj, "goal");
        let high_score = high.score(&traj, "goal");
        assert!(
            high_score > low_score,
            "high success rate should score higher"
        );
    }

    #[test]
    fn success_rate_clamped() {
        let evaluator = ScenarioEvaluator::with_defaults().with_success_rate(2.0);
        assert_eq!(evaluator.success_rate(), 1.0);
    }

    // ── Detailed breakdown tests ───────────────────────────────────────

    #[test]
    fn detailed_breakdown_components() {
        let evaluator = ScenarioEvaluator::with_defaults();
        let traj = make_trajectory(&[0.6, 0.7], &[0.8, 0.8], &[false, true]);
        let bd = evaluator.score_detailed(&traj, "goal");
        assert!(bd.goal_progress > 0.0);
        assert!(bd.risk_avoidance < 1.0); // has one risky step
        assert!(bd.confidence > 0.0);
        assert!(bd.overall > 0.0);
    }

    #[test]
    fn detailed_empty_trajectory() {
        let evaluator = ScenarioEvaluator::with_defaults();
        let bd = evaluator.score_detailed(&[], "goal");
        assert_eq!(bd.overall, 0.0);
        assert_eq!(bd.goal_progress, 0.0);
    }

    // ── Edge cases ─────────────────────────────────────────────────────

    #[test]
    fn single_step_trajectory() {
        let evaluator = ScenarioEvaluator::with_defaults();
        let traj = make_trajectory(&[0.5], &[0.7], &[false]);
        let score = evaluator.score(&traj, "goal");
        assert!(score > 0.0 && score <= 1.0);
    }

    #[test]
    fn score_always_in_range() {
        let evaluator = ScenarioEvaluator::with_defaults();
        let traj = make_trajectory(&[1.0, 1.0], &[1.0, 1.0], &[false, false]);
        let score = evaluator.score(&traj, "goal");
        assert!(score <= 1.0);
    }
}
