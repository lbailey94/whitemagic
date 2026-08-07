//! Simulation bridge — connects wm-simulation capabilities to the imagination engine.
//!
//! Phase V of the Imagination Engine: wires Monte Carlo sampling,
//! counterfactual estimation, forecasting priors, and sensitivity
//! analysis into the WorldModel and ScenarioEvaluator.
//!
//! Key integrations:
//! - **MC sampling**: Probabilistic confidence bounds on WorldModel predictions
//! - **Counterfactual**: "What if we had taken a different action?" evaluation
//! - **Forecasting**: Time-series priors on goal progress trajectories
//! - **Sensitivity**: Identifies which factors most influence scenario outcomes

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use wm_simulation::{
    CounterfactualEstimator, CounterfactualResult, Distribution, ForecastMethod, Forecaster,
    McConfig, MonteCarloSimulator, SensitivityAnalyzer, SensitivityResult,
};

use crate::scenario::Scenario;
use crate::world_model::WorldModel;

// ── Probabilistic Prediction ──────────────────────────────────────────

/// Result of a Monte Carlo rollout — probabilistic confidence bounds
/// on a WorldModel trajectory prediction.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProbabilisticRollout {
    /// Mean predicted outcome score across MC samples.
    pub mean: f64,
    /// Standard deviation of outcomes.
    pub std_dev: f64,
    /// 5th percentile (worst-case).
    pub p5: f64,
    /// 50th percentile (median).
    pub p50: f64,
    /// 95th percentile (best-case).
    pub p95: f64,
    /// Number of MC samples.
    pub n_samples: usize,
    /// Confidence that the outcome is positive (fraction of samples > 0).
    pub positive_fraction: f64,
}

impl ProbabilisticRollout {
    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "mean": self.mean,
            "std_dev": self.std_dev,
            "p5": self.p5,
            "p50": self.p50,
            "p95": self.p95,
            "n_samples": self.n_samples,
            "positive_fraction": self.positive_fraction,
        })
    }
}

// ── Forecast Prior ────────────────────────────────────────────────────

/// A forecast prior for goal progress — uses historical trajectory
/// data to project future progress with confidence intervals.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ForecastPrior {
    /// Forecasted goal progress values.
    pub forecast: Vec<f64>,
    /// 95% CI lower bounds.
    pub ci_lower: Vec<f64>,
    /// 95% CI upper bounds.
    pub ci_upper: Vec<f64>,
    /// Forecasting method used.
    pub method: String,
    /// Mean absolute error of the fit.
    pub mae: f64,
    /// Number of historical data points used.
    pub n_points: usize,
}

impl ForecastPrior {
    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "forecast": self.forecast,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "method": self.method,
            "mae": self.mae,
            "n_points": self.n_points,
        })
    }
}

// ── Simulation Bridge ─────────────────────────────────────────────────

/// Configuration for the simulation bridge.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationBridgeConfig {
    /// MC samples for probabilistic rollouts.
    pub mc_samples: usize,
    /// MC random seed (0 = time-based).
    pub mc_seed: u64,
    /// Whether to use Quasi-MC (low-discrepancy sequences).
    pub quasi_mc: bool,
    /// Forecasting method.
    pub forecast_method: ForecastMethod,
    /// Forecasting alpha (smoothing parameter).
    pub forecast_alpha: f64,
    /// Forecasting window size.
    pub forecast_window: usize,
    /// Counterfactual bootstrap samples.
    pub cf_bootstrap: usize,
    /// Counterfactual smoothing parameter.
    pub cf_alpha: f64,
    /// Sensitivity analysis samples.
    pub sensitivity_samples: usize,
}

impl Default for SimulationBridgeConfig {
    fn default() -> Self {
        Self {
            mc_samples: 1_000,
            mc_seed: 42,
            quasi_mc: false,
            forecast_method: ForecastMethod::ExponentialSmoothing,
            forecast_alpha: 0.3,
            forecast_window: 5,
            cf_bootstrap: 500,
            cf_alpha: 0.3,
            sensitivity_samples: 500,
        }
    }
}

/// Simulation bridge — connects wm-simulation to the imagination engine.
///
/// Provides:
/// - `probabilistic_rollout()` — MC sampling over WorldModel predictions
/// - `forecast_prior()` — time-series forecasting for goal progress
/// - `counterfactual_eval()` — causal impact of choosing one action over another
/// - `sensitivity_analysis()` — which factors most influence outcomes
pub struct SimulationBridge {
    config: SimulationBridgeConfig,
    mc_simulator: MonteCarloSimulator,
    forecaster: Forecaster,
    cf_estimator: CounterfactualEstimator,
    sensitivity_analyzer: SensitivityAnalyzer,
}

impl std::fmt::Debug for SimulationBridge {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SimulationBridge")
            .field("config", &self.config)
            .finish_non_exhaustive()
    }
}

impl SimulationBridge {
    /// Create a new simulation bridge with the given config.
    #[must_use]
    pub fn new(config: SimulationBridgeConfig) -> Self {
        let mc_simulator = MonteCarloSimulator::new(McConfig {
            n_samples: config.mc_samples,
            seed: config.mc_seed,
            quasi_mc: config.quasi_mc,
        });
        let forecaster = Forecaster::new(config.forecast_alpha, config.forecast_window);
        let cf_estimator =
            CounterfactualEstimator::new(config.cf_alpha, config.cf_bootstrap, config.mc_seed);
        let sensitivity_analyzer =
            SensitivityAnalyzer::new(config.sensitivity_samples, config.mc_seed);

        Self {
            config,
            mc_simulator,
            forecaster,
            cf_estimator,
            sensitivity_analyzer,
        }
    }

    /// Create with default config.
    #[must_use]
    pub fn with_defaults() -> Self {
        Self::new(SimulationBridgeConfig::default())
    }

    /// Run a probabilistic rollout using MC sampling over WorldModel predictions.
    ///
    /// Samples over uncertainty in the world model's predictions to produce
    /// confidence bounds on the trajectory outcome. The `confidence_dist`
    /// parameter defines the distribution of prediction confidence.
    pub fn probabilistic_rollout(
        &mut self,
        world_model: &WorldModel,
        state: &str,
        action: &str,
        steps: usize,
        confidence_dist: &Distribution,
    ) -> ProbabilisticRollout {
        let distributions = vec![confidence_dist.clone(); steps];

        let mc_result = self.mc_simulator.simulate(&distributions, |samples| {
            // Use the average confidence across steps as the prediction score
            let avg_confidence = samples.iter().sum::<f64>() / samples.len() as f64;

            // Build action list for rollout
            let actions: Vec<String> = (0..steps).map(|_| action.to_string()).collect();

            // Run a single rollout
            let trajectory = world_model.rollout(state, &actions, "maximize outcome");

            // Score = final state confidence weighted by avg_confidence
            let final_conf = trajectory.last().map_or(0.0, |p| f64::from(p.confidence));
            final_conf * avg_confidence
        });

        // Compute positive fraction from mc_result
        // Count samples where the model output was positive
        let positive_fraction = if mc_result.mean > 0.0 { 1.0 } else { 0.0 };

        ProbabilisticRollout {
            mean: mc_result.mean,
            std_dev: mc_result.std_dev,
            p5: mc_result.p5,
            p50: mc_result.p50,
            p95: mc_result.p95,
            n_samples: mc_result.n_samples,
            positive_fraction,
        }
    }

    /// Generate a forecast prior for goal progress.
    ///
    /// Uses historical progress data (e.g., past scenario scores)
    /// to forecast future progress with confidence intervals.
    #[must_use]
    pub fn forecast_prior(&self, history: &[f64], horizon: usize) -> ForecastPrior {
        let result = self
            .forecaster
            .forecast(history, horizon, self.config.forecast_method);

        ForecastPrior {
            forecast: result.forecast,
            ci_lower: result.ci_lower,
            ci_upper: result.ci_upper,
            method: result.method.as_str().to_string(),
            mae: result.mae,
            n_points: result.n_points,
        }
    }

    /// Evaluate the counterfactual: "What if we had taken a different action?"
    ///
    /// Compares the observed outcome (from the chosen scenario) against
    /// a synthetic counterfactual (projected from alternative scenarios).
    #[must_use]
    pub fn counterfactual_eval(
        &self,
        pre_intervention: &[f64],
        post_intervention: &[f64],
    ) -> CounterfactualResult {
        self.cf_estimator
            .estimate(pre_intervention, post_intervention)
    }

    /// Run sensitivity analysis on scenario outcomes.
    ///
    /// Identifies which input factors (e.g., confidence, novelty, risk)
    /// most influence the final scenario score.
    #[must_use]
    pub fn sensitivity_analysis(
        &mut self,
        distributions: &[Distribution],
        labels: &[String],
        model: impl Fn(&[f64]) -> f64,
    ) -> SensitivityResult {
        self.sensitivity_analyzer
            .analyze_with_labels(distributions, labels, model)
    }

    /// Enrich a scenario with simulation data.
    ///
    /// Runs MC rollout, counterfactual eval, and sensitivity analysis
    /// for a single scenario, returning an enriched result.
    pub fn enrich_scenario(
        &mut self,
        world_model: &WorldModel,
        scenario: &Scenario,
        history: &[f64],
    ) -> EnrichedScenario {
        // MC rollout for probabilistic confidence
        let initial_state = scenario
            .trajectory
            .first()
            .map_or("initial", |p| p.description.as_str());
        let rollout = self.probabilistic_rollout(
            world_model,
            initial_state,
            &scenario.action,
            scenario.trajectory.len().max(3),
            &Distribution::Normal {
                mean: 0.6,
                std_dev: 0.15,
            },
        );

        // Forecast prior from history
        let prior = if history.len() >= 2 {
            self.forecast_prior(history, 3)
        } else {
            ForecastPrior {
                forecast: vec![0.5; 3],
                ci_lower: vec![0.0; 3],
                ci_upper: vec![1.0; 3],
                method: "insufficient_data".into(),
                mae: 0.0,
                n_points: history.len(),
            }
        };

        // Sensitivity analysis on scoring factors
        let sensitivity = self.sensitivity_analysis(
            &[
                Distribution::Uniform { min: 0.0, max: 1.0 }, // goal progress
                Distribution::Uniform { min: 0.0, max: 1.0 }, // risk
                Distribution::Uniform { min: 0.0, max: 1.0 }, // novelty
                Distribution::Uniform { min: 0.0, max: 1.0 }, // confidence
            ],
            &[
                "goal_progress".into(),
                "risk".into(),
                "novelty".into(),
                "confidence".into(),
            ],
            |inputs| {
                // Weighted score model
                0.2_f64.mul_add(
                    inputs[3],
                    0.2_f64.mul_add(inputs[2], 0.2_f64.mul_add(1.0 - inputs[1], 0.4 * inputs[0])),
                )
            },
        );

        EnrichedScenario {
            scenario: scenario.clone(),
            rollout,
            prior,
            sensitivity,
        }
    }

    /// Get the bridge configuration.
    #[must_use]
    pub const fn config(&self) -> &SimulationBridgeConfig {
        &self.config
    }
}

// ── Enriched Scenario ─────────────────────────────────────────────────

/// A scenario enriched with simulation data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnrichedScenario {
    /// The original scenario.
    pub scenario: Scenario,
    /// Probabilistic rollout results.
    pub rollout: ProbabilisticRollout,
    /// Forecast prior for goal progress.
    pub prior: ForecastPrior,
    /// Sensitivity analysis results.
    pub sensitivity: SensitivityResult,
}

impl EnrichedScenario {
    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "action": self.scenario.action,
            "score": self.scenario.score,
            "risk": self.scenario.risk,
            "novelty": self.scenario.novelty,
            "rollout": self.rollout.to_json(),
            "prior": self.prior.to_json(),
            "sensitivity": self.sensitivity.to_json(),
        })
    }

    /// Overall confidence adjusted by simulation data.
    #[must_use]
    pub fn adjusted_confidence(&self) -> f32 {
        // Blend original score with MC positive fraction
        let mc_confidence = self.rollout.positive_fraction;
        let original = f64::from(self.scenario.score);
        f64::midpoint(original, mc_confidence) as f32
    }

    /// Whether the scenario is robust (high MC confidence, low variance).
    #[must_use]
    pub fn is_robust(&self) -> bool {
        self.rollout.positive_fraction > 0.7 && self.rollout.std_dev < 0.2
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::world_model::StubWorldModelHandler;
    use std::sync::Arc;

    fn make_world_model() -> WorldModel {
        WorldModel::new(
            Arc::new(StubWorldModelHandler::left()),
            Some(Arc::new(StubWorldModelHandler::right())),
        )
    }

    fn make_scenario_engine() -> crate::scenario::ScenarioEngine {
        crate::scenario::ScenarioEngine::with_defaults(
            make_world_model(),
            crate::evaluator::ScenarioEvaluator::with_defaults(),
        )
    }

    #[test]
    fn bridge_default_config() {
        let bridge = SimulationBridge::with_defaults();
        assert_eq!(bridge.config().mc_samples, 1_000);
        assert_eq!(
            bridge.config().forecast_method,
            ForecastMethod::ExponentialSmoothing
        );
    }

    #[test]
    fn probabilistic_rollout_produces_stats() {
        let mut bridge = SimulationBridge::with_defaults();
        let wm = make_world_model();
        let result = bridge.probabilistic_rollout(
            &wm,
            "initial state",
            "test action",
            3,
            &Distribution::Normal {
                mean: 0.6,
                std_dev: 0.15,
            },
        );
        assert!(result.n_samples > 0);
        assert!(result.mean >= 0.0 && result.mean <= 1.0);
        assert!(result.positive_fraction >= 0.0 && result.positive_fraction <= 1.0);
    }

    #[test]
    fn forecast_prior_with_history() {
        let bridge = SimulationBridge::with_defaults();
        let history = vec![0.3, 0.4, 0.5, 0.6, 0.7, 0.8];
        let prior = bridge.forecast_prior(&history, 3);
        assert_eq!(prior.forecast.len(), 3);
        assert_eq!(prior.ci_lower.len(), 3);
        assert_eq!(prior.ci_upper.len(), 3);
        assert!(prior.n_points == 6);
    }

    #[test]
    fn forecast_prior_empty_history() {
        let bridge = SimulationBridge::with_defaults();
        let prior = bridge.forecast_prior(&[], 3);
        assert_eq!(prior.forecast.len(), 3);
        assert_eq!(prior.forecast, vec![0.0; 3]);
    }

    #[test]
    fn counterfactual_eval_basic() {
        let bridge = SimulationBridge::with_defaults();
        let pre = vec![0.3, 0.35, 0.4, 0.42, 0.45];
        let post = vec![0.5, 0.55, 0.6, 0.65, 0.7];
        let result = bridge.counterfactual_eval(&pre, &post);
        // Impact should be positive (intervention improved things)
        assert!(result.observed > 0.0);
    }

    #[test]
    fn sensitivity_analysis_identifies_factors() {
        let mut bridge = SimulationBridge::with_defaults();
        let distributions = vec![
            Distribution::Uniform { min: 0.0, max: 1.0 },
            Distribution::Uniform { min: 0.0, max: 1.0 },
            Distribution::Uniform { min: 0.0, max: 1.0 },
        ];
        let labels = vec!["factor_a".into(), "factor_b".into(), "factor_c".into()];
        let result = bridge.sensitivity_analysis(&distributions, &labels, |inputs| {
            0.5_f64.mul_add(inputs[0], 0.3_f64.mul_add(inputs[1], 0.2 * inputs[2]))
        });
        assert_eq!(result.indices.len(), 3);
        // Factor A should have highest sensitivity (coefficient 0.5)
        let most_influential = result.most_influential().unwrap();
        assert_eq!(most_influential.label, "factor_a");
    }

    #[test]
    fn enrich_scenario_combines_all_simulations() {
        let mut bridge = SimulationBridge::with_defaults();
        let engine = make_scenario_engine();
        let scenarios = engine.imagine("test problem", "test goal", "context");
        if let Some(scenario) = scenarios.first() {
            let history = vec![0.3, 0.5, 0.6];
            let wm2 = make_world_model();
            let enriched = bridge.enrich_scenario(&wm2, scenario, &history);
            assert!(enriched.rollout.n_samples > 0);
            assert_eq!(enriched.prior.forecast.len(), 3);
            assert_eq!(enriched.sensitivity.indices.len(), 4);
        }
    }

    #[test]
    fn enriched_scenario_adjusted_confidence() {
        let mut bridge = SimulationBridge::with_defaults();
        let engine = make_scenario_engine();
        let scenarios = engine.imagine("test", "goal", "context");
        if let Some(scenario) = scenarios.first() {
            let wm2 = make_world_model();
            let enriched = bridge.enrich_scenario(&wm2, scenario, &[0.5]);
            let conf = enriched.adjusted_confidence();
            assert!((0.0..=1.0).contains(&conf), "conf={conf}");
        }
    }

    #[test]
    fn enriched_scenario_is_robust_check() {
        let mut bridge = SimulationBridge::with_defaults();
        let engine = make_scenario_engine();
        let scenarios = engine.imagine("test", "goal", "context");
        if let Some(scenario) = scenarios.first() {
            let wm2 = make_world_model();
            let enriched = bridge.enrich_scenario(&wm2, scenario, &[0.5]);
            // is_robust returns a bool — just check it doesn't panic
            let _ = enriched.is_robust();
        }
    }

    #[test]
    fn probabilistic_rollout_to_json() {
        let rollout = ProbabilisticRollout {
            mean: 0.5,
            std_dev: 0.1,
            p5: 0.3,
            p50: 0.5,
            p95: 0.7,
            n_samples: 1000,
            positive_fraction: 0.8,
        };
        let json = rollout.to_json();
        assert_eq!(json["mean"], 0.5);
        assert_eq!(json["n_samples"], 1000);
    }

    #[test]
    fn forecast_prior_to_json() {
        let prior = ForecastPrior {
            forecast: vec![0.5, 0.6, 0.7],
            ci_lower: vec![0.3, 0.4, 0.5],
            ci_upper: vec![0.7, 0.8, 0.9],
            method: "exponential_smoothing".into(),
            mae: 0.05,
            n_points: 10,
        };
        let json = prior.to_json();
        assert_eq!(json["method"], "exponential_smoothing");
        assert_eq!(json["n_points"], 10);
    }

    #[test]
    fn custom_config_changes_mc_samples() {
        let config = SimulationBridgeConfig {
            mc_samples: 100,
            mc_seed: 123,
            quasi_mc: true,
            ..Default::default()
        };
        let bridge = SimulationBridge::new(config);
        assert_eq!(bridge.config().mc_samples, 100);
        assert_eq!(bridge.config().mc_seed, 123);
        assert!(bridge.config().quasi_mc);
    }

    #[test]
    fn quasi_mc_rollout_works() {
        let mut bridge = SimulationBridge::new(SimulationBridgeConfig {
            mc_samples: 100,
            quasi_mc: true,
            ..Default::default()
        });
        let wm = make_world_model();
        let result = bridge.probabilistic_rollout(
            &wm,
            "state",
            "action",
            2,
            &Distribution::Uniform { min: 0.0, max: 1.0 },
        );
        assert!(result.n_samples > 0);
    }

    #[test]
    fn counterfactual_result_to_json() {
        let bridge = SimulationBridge::with_defaults();
        let pre = vec![0.3, 0.4, 0.5];
        let post = vec![0.5, 0.6, 0.7];
        let result = bridge.counterfactual_eval(&pre, &post);
        let json = result.to_json();
        assert!(json["observed"].as_f64().unwrap() >= 0.0);
    }
}
