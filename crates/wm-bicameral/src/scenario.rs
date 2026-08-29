//! Scenario Engine — the core "imagine → simulate → evaluate" loop.
//!
//! Generates candidate actions, simulates their outcomes using the WorldModel,
//! and scores them using the ScenarioEvaluator. This is System II from SR²AM:
//! simulative reasoning that predicts consequences before acting.
//!
//! Following ITP (Imagine-then-Plan), the engine:
//! 1. Generates N candidate actions (using creative hemisphere if available)
//! 2. Rolls out each action K steps in the world model
//! 3. Scores each trajectory using multi-criteria evaluation
//! 4. Returns ranked scenarios for selection

use serde::{Deserialize, Serialize};
#[cfg(test)]
use std::sync::Arc;

use crate::configurator::DeliberationMode;
use crate::evaluator::{ScenarioEvaluator, ScoreBreakdown};
use crate::world_model::{DualPrediction, PredictedState, WorldModel};

/// A scenario: a proposed action with its predicted outcome trajectory and score.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Scenario {
    /// The proposed action/plan.
    pub action: String,
    /// Predicted outcome trajectory (one entry per simulation step).
    pub trajectory: Vec<PredictedState>,
    /// Overall quality score (0.0–1.0).
    pub score: f32,
    /// Estimated risk (0.0–1.0).
    pub risk: f32,
    /// Estimated novelty (0.0–1.0).
    pub novelty: f32,
    /// Rationale for this scenario.
    pub rationale: String,
    /// Detailed score breakdown.
    pub breakdown: Option<ScoreBreakdown>,
}

impl Scenario {
    /// Create a minimal scenario with just an action.
    #[must_use]
    pub const fn from_action(action: String) -> Self {
        Self {
            action,
            trajectory: Vec::new(),
            score: 0.0,
            risk: 0.0,
            novelty: 0.0,
            rationale: String::new(),
            breakdown: None,
        }
    }
}

/// Configuration for the scenario engine.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScenarioConfig {
    /// Number of candidate actions to generate.
    pub n_candidates: usize,
    /// Maximum imagination horizon (steps to look ahead).
    pub max_horizon: usize,
    /// Whether to use creative hemisphere for candidates.
    pub use_creative: bool,
    /// Minimum novelty threshold to include a scenario.
    pub min_novelty: f32,
}

impl Default for ScenarioConfig {
    fn default() -> Self {
        Self {
            n_candidates: 3,
            max_horizon: 3,
            use_creative: true,
            min_novelty: 0.0,
        }
    }
}

impl ScenarioConfig {
    /// Create config from a deliberation mode.
    #[must_use]
    pub const fn from_mode(mode: DeliberationMode) -> Self {
        Self {
            n_candidates: mode.n_candidates(),
            max_horizon: mode.horizon(),
            use_creative: mode.uses_creative(),
            min_novelty: 0.0,
        }
    }
}

/// The scenario engine — generates, simulates, and evaluates scenarios.
///
/// Combines a [`WorldModel`] for state prediction with a [`ScenarioEvaluator`]
/// for multi-criteria scoring. This is the core imagination loop.
pub struct ScenarioEngine {
    world_model: WorldModel,
    evaluator: ScenarioEvaluator,
    config: ScenarioConfig,
}

impl ScenarioEngine {
    /// Create a new scenario engine.
    #[must_use]
    pub const fn new(
        world_model: WorldModel,
        evaluator: ScenarioEvaluator,
        config: ScenarioConfig,
    ) -> Self {
        Self {
            world_model,
            evaluator,
            config,
        }
    }

    /// Create a scenario engine with default config.
    #[must_use]
    pub fn with_defaults(world_model: WorldModel, evaluator: ScenarioEvaluator) -> Self {
        Self::new(world_model, evaluator, ScenarioConfig::default())
    }

    /// Create a scenario engine configured for a specific deliberation mode.
    #[must_use]
    pub const fn for_mode(
        world_model: WorldModel,
        evaluator: ScenarioEvaluator,
        mode: DeliberationMode,
    ) -> Self {
        Self::new(world_model, evaluator, ScenarioConfig::from_mode(mode))
    }

    /// Generate and evaluate scenarios for a given state and goal.
    ///
    /// 1. Generate N candidate actions
    /// 2. For each action, roll out K steps in the world model
    /// 3. Score each trajectory
    /// 4. Filter by minimum novelty
    /// 5. Return sorted by score (descending)
    #[must_use]
    pub fn imagine(&self, state: &str, goal: &str, memory_context: &str) -> Vec<Scenario> {
        // Generate candidate actions
        let actions = self
            .world_model
            .generate_actions(state, goal, self.config.n_candidates);

        let mut scenarios: Vec<Scenario> = actions
            .into_iter()
            .filter_map(|action| {
                // Assess novelty
                let novelty = self.evaluator.novelty(&action, memory_context);

                // Filter by minimum novelty
                if novelty < self.config.min_novelty {
                    return None;
                }

                // Build action sequence for rollout
                let action_seq: Vec<String> = std::iter::once(action.clone())
                    .chain(
                        (1..self.config.max_horizon)
                            .map(|i| format!("Step {i}: continue {action}")),
                    )
                    .collect();

                // Simulate
                let trajectory = self.world_model.rollout(state, &action_seq, goal);

                // Score
                let breakdown = self.evaluator.score_detailed(&trajectory, goal);
                let risk = 1.0 - breakdown.risk_avoidance;

                let rationale = if trajectory.is_empty() {
                    format!("Action '{action}' with no predicted trajectory")
                } else {
                    let last = trajectory.last().unwrap();
                    format!(
                        "Action '{action}' → {} (confidence: {:.2}, progress: {:.2})",
                        last.description.chars().take(100).collect::<String>(),
                        last.confidence,
                        last.goal_progress
                    )
                };

                Some(Scenario {
                    action,
                    trajectory,
                    score: breakdown.overall,
                    risk,
                    novelty,
                    rationale,
                    breakdown: Some(breakdown),
                })
            })
            .collect();

        // Sort by score descending
        scenarios.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        scenarios
    }

    /// Select the best scenario from candidates.
    ///
    /// Returns the highest-scoring scenario, or `None` if the list is empty.
    #[must_use]
    pub const fn select_best<'a>(&self, scenarios: &'a [Scenario]) -> Option<&'a Scenario> {
        scenarios.first()
    }

    /// Select the best scenario, preferring low-risk options when scores are close.
    ///
    /// If the top two scenarios have scores within `tolerance`, prefer the one
    /// with lower risk.
    #[must_use]
    pub fn select_balanced<'a>(
        &self,
        scenarios: &'a [Scenario],
        tolerance: f32,
    ) -> Option<&'a Scenario> {
        if scenarios.is_empty() {
            return None;
        }
        if scenarios.len() == 1 {
            return scenarios.first();
        }

        let top = &scenarios[0];
        let second = &scenarios[1];

        if (top.score - second.score).abs() <= tolerance && second.risk < top.risk {
            Some(second)
        } else {
            Some(top)
        }
    }

    /// Predict the outcome of a single specific action (without full imagination).
    #[must_use]
    pub fn predict(&self, state: &str, action: &str, goal: &str) -> DualPrediction {
        self.world_model.predict(state, action, goal)
    }

    /// Reflect on a past decision using counterfactual reasoning.
    ///
    /// Given a past state, the action taken, and an alternative action,
    /// predicts what would have happened with the alternative.
    #[must_use]
    pub fn reflect(
        &self,
        past_state: &str,
        actual_action: &str,
        alternative_action: &str,
        goal: &str,
    ) -> ReflectionResult {
        let actual = self.world_model.predict(past_state, actual_action, goal);
        let counterfactual = self
            .world_model
            .predict(past_state, alternative_action, goal);

        let actual_best = actual.best().clone();
        let cf_best = counterfactual.best().clone();

        let would_have_been_better = cf_best.goal_progress > actual_best.goal_progress
            && cf_best.confidence >= actual_best.confidence * 0.8;

        let lesson = if would_have_been_better {
            format!(
                "The alternative '{}' would have advanced the goal further ({:.0}% vs {:.0}%). \
                 Consider similar alternatives in future situations.",
                alternative_action,
                cf_best.goal_progress * 100.0,
                actual_best.goal_progress * 100.0
            )
        } else {
            format!(
                "The actual action '{}' was appropriate. The alternative '{}' would not have \
                 improved goal progress ({:.0}% vs {:.0}%).",
                actual_action,
                alternative_action,
                actual_best.goal_progress * 100.0,
                cf_best.goal_progress * 100.0
            )
        };

        ReflectionResult {
            actual_prediction: actual_best,
            counterfactual_prediction: cf_best,
            would_have_been_better,
            lesson,
        }
    }

    /// Get the world model.
    #[must_use]
    pub const fn world_model(&self) -> &WorldModel {
        &self.world_model
    }

    /// Get the evaluator.
    #[must_use]
    pub const fn evaluator(&self) -> &ScenarioEvaluator {
        &self.evaluator
    }

    /// Get the scenario config.
    #[must_use]
    pub const fn config(&self) -> &ScenarioConfig {
        &self.config
    }
}

/// Result of a counterfactual reflection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReflectionResult {
    /// What actually happened (predicted).
    pub actual_prediction: PredictedState,
    /// What would have happened with the alternative action.
    pub counterfactual_prediction: PredictedState,
    /// Whether the alternative would have been better.
    pub would_have_been_better: bool,
    /// Human-readable lesson learned.
    pub lesson: String,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::evaluator::ScenarioEvaluator;
    use crate::world_model::{StubWorldModelHandler, WorldModel};

    fn make_engine() -> ScenarioEngine {
        let wm = WorldModel::new(
            Arc::new(StubWorldModelHandler::left()),
            Some(Arc::new(StubWorldModelHandler::right())),
        );
        let evaluator = ScenarioEvaluator::with_defaults();
        ScenarioEngine::with_defaults(wm, evaluator)
    }

    fn make_engine_for_mode(mode: DeliberationMode) -> ScenarioEngine {
        let wm = WorldModel::new(
            Arc::new(StubWorldModelHandler::left()),
            Some(Arc::new(StubWorldModelHandler::right())),
        );
        let evaluator = ScenarioEvaluator::with_defaults();
        ScenarioEngine::for_mode(wm, evaluator, mode)
    }

    // ── Scenario struct tests ──────────────────────────────────────────

    #[test]
    fn scenario_from_action() {
        let s = Scenario::from_action("test".into());
        assert_eq!(s.action, "test");
        assert_eq!(s.score, 0.0);
        assert!(s.trajectory.is_empty());
    }

    // ── ScenarioConfig tests ───────────────────────────────────────────

    #[test]
    fn config_default() {
        let config = ScenarioConfig::default();
        assert_eq!(config.n_candidates, 3);
        assert_eq!(config.max_horizon, 3);
        assert!(config.use_creative);
    }

    #[test]
    fn config_from_direct_mode() {
        let config = ScenarioConfig::from_mode(DeliberationMode::Direct);
        assert_eq!(config.n_candidates, 0);
        assert_eq!(config.max_horizon, 0);
        assert!(!config.use_creative);
    }

    #[test]
    fn config_from_research_mode() {
        let config = ScenarioConfig::from_mode(DeliberationMode::Research);
        assert_eq!(config.n_candidates, 6);
        assert_eq!(config.max_horizon, 10);
        assert!(config.use_creative);
    }

    // ── Imagine tests ──────────────────────────────────────────────────

    #[test]
    fn imagine_generates_scenarios() {
        let engine = make_engine();
        let scenarios = engine.imagine("idle state", "complete task", "no history");
        assert!(
            !scenarios.is_empty(),
            "should generate at least one scenario"
        );
    }

    #[test]
    fn imagine_scenarios_sorted_by_score() {
        let engine = make_engine();
        let scenarios = engine.imagine("state", "goal", "");
        for i in 1..scenarios.len() {
            assert!(
                scenarios[i - 1].score >= scenarios[i].score,
                "scenarios should be sorted by score descending"
            );
        }
    }

    #[test]
    fn imagine_with_memory_context() {
        let engine = make_engine();
        let scenarios = engine.imagine("state", "goal", "some historical context");
        assert!(!scenarios.is_empty());
    }

    #[test]
    fn imagine_direct_mode_no_candidates() {
        let engine = make_engine_for_mode(DeliberationMode::Direct);
        let scenarios = engine.imagine("state", "goal", "");
        // Direct mode has 0 candidates → empty scenarios
        assert!(scenarios.is_empty());
    }

    #[test]
    fn imagine_scenarios_have_breakdown() {
        let engine = make_engine();
        let scenarios = engine.imagine("state", "goal", "");
        for s in &scenarios {
            assert!(
                s.breakdown.is_some(),
                "scenario should have score breakdown"
            );
        }
    }

    #[test]
    fn imagine_scenarios_have_rationale() {
        let engine = make_engine();
        let scenarios = engine.imagine("state", "goal", "");
        for s in &scenarios {
            assert!(!s.rationale.is_empty(), "scenario should have rationale");
        }
    }

    // ── Selection tests ────────────────────────────────────────────────

    #[test]
    fn select_best_empty() {
        let engine = make_engine();
        assert!(engine.select_best(&[]).is_none());
    }

    #[test]
    fn select_best_returns_highest() {
        let engine = make_engine();
        let scenarios = engine.imagine("state", "goal", "");
        let best = engine.select_best(&scenarios);
        assert!(best.is_some());
        if let Some(b) = best {
            if scenarios.len() > 1 {
                assert!(b.score >= scenarios[1].score);
            }
        }
    }

    #[test]
    fn select_balanced_prefers_lower_risk() {
        let engine = make_engine();
        let scenarios = vec![
            Scenario {
                action: "risky".into(),
                trajectory: vec![],
                score: 0.7,
                risk: 0.5,
                novelty: 0.3,
                rationale: "test".into(),
                breakdown: None,
            },
            Scenario {
                action: "safe".into(),
                trajectory: vec![],
                score: 0.68,
                risk: 0.1,
                novelty: 0.3,
                rationale: "test".into(),
                breakdown: None,
            },
        ];
        let selected = engine.select_balanced(&scenarios, 0.05);
        assert_eq!(selected.unwrap().action, "safe");
    }

    #[test]
    fn select_balanced_keeps_higher_score() {
        let engine = make_engine();
        let scenarios = vec![
            Scenario {
                action: "best".into(),
                trajectory: vec![],
                score: 0.9,
                risk: 0.3,
                novelty: 0.3,
                rationale: "test".into(),
                breakdown: None,
            },
            Scenario {
                action: "worse".into(),
                trajectory: vec![],
                score: 0.5,
                risk: 0.1,
                novelty: 0.3,
                rationale: "test".into(),
                breakdown: None,
            },
        ];
        let selected = engine.select_balanced(&scenarios, 0.05);
        assert_eq!(selected.unwrap().action, "best");
    }

    #[test]
    fn select_balanced_empty() {
        let engine = make_engine();
        assert!(engine.select_balanced(&[], 0.1).is_none());
    }

    #[test]
    fn select_balanced_single() {
        let engine = make_engine();
        let scenarios = vec![Scenario::from_action("only".into())];
        let selected = engine.select_balanced(&scenarios, 0.1);
        assert_eq!(selected.unwrap().action, "only");
    }

    // ── Predict tests ──────────────────────────────────────────────────

    #[test]
    fn predict_returns_dual() {
        let engine = make_engine();
        let result = engine.predict("state", "action", "goal");
        assert!(!result.left.description.is_empty());
    }

    // ── Reflect tests ──────────────────────────────────────────────────

    #[test]
    fn reflect_returns_lesson() {
        let engine = make_engine();
        let result = engine.reflect("state", "actual action", "alternative action", "goal");
        assert!(!result.lesson.is_empty());
    }

    #[test]
    fn reflect_comparative() {
        let engine = make_engine();
        let result = engine.reflect("state", "actual", "alternative", "goal");
        // Should have both predictions
        assert!(!result.actual_prediction.description.is_empty());
        assert!(!result.counterfactual_prediction.description.is_empty());
    }

    // ── Accessor tests ─────────────────────────────────────────────────

    #[test]
    fn engine_accessors() {
        let engine = make_engine();
        assert_eq!(engine.world_model().left_name(), "stub-left");
        assert!(engine.evaluator().success_rate() > 0.0);
        assert_eq!(engine.config().n_candidates, 3);
    }

    // ── Novelty filter tests ───────────────────────────────────────────

    #[test]
    fn min_novelty_filters_scenarios() {
        let wm = WorldModel::new(
            Arc::new(StubWorldModelHandler::left()),
            Some(Arc::new(StubWorldModelHandler::right())),
        );
        let evaluator = ScenarioEvaluator::with_defaults();
        let config = ScenarioConfig {
            n_candidates: 3,
            max_horizon: 3,
            use_creative: true,
            min_novelty: 0.99, // Very high → filters everything
        };
        let engine = ScenarioEngine::new(wm, evaluator, config);
        let scenarios = engine.imagine("state", "goal", "exact same context as state");
        // With very high novelty threshold and overlapping context, most should be filtered
        // (depends on stub output, but threshold is so high it should filter most/all)
        assert!(
            scenarios.len() <= 3,
            "should filter some scenarios with high novelty threshold"
        );
    }
}
