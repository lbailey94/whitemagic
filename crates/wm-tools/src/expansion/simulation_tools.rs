//! Simulation tools — sim.mc, sim.forecast, sim.counterfactual.
//!
//! Gana::Mound — simulation, forecasting, and causal analysis.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use std::sync::Arc;

use serde_json::{Value, json};
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_simulation::{
    CounterfactualEstimator, Distribution, ForecastMethod, Forecaster, McConfig,
    MonteCarloSimulator,
};

// ── sim.mc ────────────────────────────────────────────────────────────

/// `sim.mc` — Run a Monte Carlo simulation.
pub struct SimMcTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl SimMcTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("simulation".into())]),
        }
    }
}

impl Default for SimMcTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for SimMcTool {
    fn name(&self) -> &str {
        "sim.mc"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Run a Monte Carlo simulation (args: n_samples, seed, quasi_mc, distributions, model)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let n_samples = args
            .get("n_samples")
            .and_then(Value::as_u64)
            .unwrap_or(5000) as usize;

        let seed = args.get("seed").and_then(Value::as_u64).unwrap_or(42);

        let quasi_mc = args
            .get("quasi_mc")
            .and_then(Value::as_bool)
            .unwrap_or(false);

        let dists_json = args
            .get("distributions")
            .and_then(Value::as_array)
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("distributions array required".into())
            })?;

        let distributions: Vec<Distribution> = dists_json
            .iter()
            .map(parse_distribution)
            .collect::<Result<_, _>>()?;

        // The model is a simple expression: "sum", "product", "mean", or "identity:index"
        let model_str = args.get("model").and_then(Value::as_str).unwrap_or("sum");

        let mut sim = MonteCarloSimulator::new(McConfig {
            n_samples,
            seed,
            quasi_mc,
        });

        let result = sim.simulate(&distributions, |inputs| match model_str {
            "sum" => inputs.iter().sum(),
            "product" => inputs.iter().product(),
            "mean" => inputs.iter().sum::<f64>() / inputs.len() as f64,
            s if s.starts_with("identity:") => {
                let idx: usize = s[9..].parse().unwrap_or(0);
                inputs.get(idx).copied().unwrap_or(0.0)
            }
            _ => inputs.iter().sum(),
        });

        Ok(json!({
            "status": "success",
            "result": result.to_json(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sim.forecast ──────────────────────────────────────────────────────

/// `sim.forecast` — Forecast a time series.
pub struct SimForecastTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl SimForecastTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("simulation".into())]),
        }
    }
}

impl Default for SimForecastTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for SimForecastTool {
    fn name(&self) -> &str {
        "sim.forecast"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Forecast a time series (args: data, horizon, method=moving_average|exponential_smoothing|linear_trend)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let data: Vec<f64> = args
            .get("data")
            .and_then(Value::as_array)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("data array required".into()))?
            .iter()
            .map(|v| v.as_f64().unwrap_or(0.0))
            .collect();

        if data.is_empty() {
            return Err(wm_core::CoreError::InvalidArgs(
                "data must not be empty".into(),
            ));
        }

        let horizon = args.get("horizon").and_then(Value::as_u64).unwrap_or(5) as usize;

        let method_str = args
            .get("method")
            .and_then(Value::as_str)
            .unwrap_or("exponential_smoothing");

        let method = match method_str {
            "moving_average" => ForecastMethod::MovingAverage,
            "exponential_smoothing" => ForecastMethod::ExponentialSmoothing,
            "linear_trend" => ForecastMethod::LinearTrend,
            _ => {
                return Err(wm_core::CoreError::InvalidArgs(format!(
                    "unknown method: {method_str}"
                )));
            }
        };

        let forecaster = Forecaster::default();
        let result = forecaster.forecast(&data, horizon, method);

        Ok(json!({
            "status": "success",
            "result": result.to_json(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sim.counterfactual ────────────────────────────────────────────────

/// `sim.counterfactual` — Estimate causal impact of an intervention.
pub struct SimCounterfactualTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl SimCounterfactualTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("simulation".into())]),
        }
    }
}

impl Default for SimCounterfactualTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for SimCounterfactualTool {
    fn name(&self) -> &str {
        "sim.counterfactual"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Estimate causal impact of an intervention (args: pre, post)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let pre: Vec<f64> = args
            .get("pre")
            .and_then(Value::as_array)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("pre array required".into()))?
            .iter()
            .map(|v| v.as_f64().unwrap_or(0.0))
            .collect();

        let post: Vec<f64> = args
            .get("post")
            .and_then(Value::as_array)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("post array required".into()))?
            .iter()
            .map(|v| v.as_f64().unwrap_or(0.0))
            .collect();

        if pre.is_empty() || post.is_empty() {
            return Err(wm_core::CoreError::InvalidArgs(
                "pre and post must not be empty".into(),
            ));
        }

        let estimator = CounterfactualEstimator::default();
        let result = estimator.estimate(&pre, &post);

        Ok(json!({
            "status": "success",
            "result": result.to_json(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Helpers ───────────────────────────────────────────────────────────

fn parse_distribution(v: &Value) -> Result<Distribution, wm_core::CoreError> {
    let kind = v
        .get("kind")
        .and_then(Value::as_str)
        .ok_or_else(|| wm_core::CoreError::InvalidArgs("distribution kind required".into()))?;

    match kind {
        "uniform" => {
            let min = v.get("min").and_then(Value::as_f64).unwrap_or(0.0);
            let max = v.get("max").and_then(Value::as_f64).unwrap_or(1.0);
            Ok(Distribution::Uniform { min, max })
        }
        "normal" => {
            let mean = v.get("mean").and_then(Value::as_f64).unwrap_or(0.0);
            let std_dev = v.get("std_dev").and_then(Value::as_f64).unwrap_or(1.0);
            Ok(Distribution::Normal { mean, std_dev })
        }
        "exponential" => {
            let lambda = v.get("lambda").and_then(Value::as_f64).unwrap_or(1.0);
            Ok(Distribution::Exponential { lambda })
        }
        "triangular" => {
            let min = v.get("min").and_then(Value::as_f64).unwrap_or(0.0);
            let mode = v.get("mode").and_then(Value::as_f64).unwrap_or(0.5);
            let max = v.get("max").and_then(Value::as_f64).unwrap_or(1.0);
            Ok(Distribution::Triangular { min, mode, max })
        }
        "constant" => {
            let val = v.get("value").and_then(Value::as_f64).unwrap_or(0.0);
            Ok(Distribution::Constant(val))
        }
        _ => Err(wm_core::CoreError::InvalidArgs(format!(
            "unknown distribution kind: {kind}"
        ))),
    }
}

// ── Registration ──────────────────────────────────────────────────────

/// Register all simulation tools into a registry.
#[must_use]
pub fn register_simulation(registry: &wm_dispatch::ToolRegistry) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(SimMcTool::new()))
        .register(Arc::new(SimForecastTool::new()))
        .register(Arc::new(SimCounterfactualTool::new()))
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn sim_mc_runs_simulation() {
        let tool = SimMcTool::new();
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "n_samples": 1000,
                    "distributions": [{"kind": "uniform", "min": 0.0, "max": 10.0}],
                    "model": "sum"
                }),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");
        assert!(v["result"]["mean"].is_number());
    }

    #[tokio::test]
    async fn sim_mc_missing_distributions_errors() {
        let tool = SimMcTool::new();
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn sim_forecast_runs() {
        let tool = SimForecastTool::new();
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "data": [1.0, 2.0, 3.0, 4.0, 5.0],
                    "horizon": 3,
                    "method": "linear_trend"
                }),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");
        assert!(v["result"]["forecast"].is_array());
    }

    #[tokio::test]
    async fn sim_forecast_empty_data_errors() {
        let tool = SimForecastTool::new();
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({"data": []})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn sim_counterfactual_runs() {
        let tool = SimCounterfactualTool::new();
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "pre": [10.0, 10.0, 10.0, 10.0, 10.0],
                    "post": [15.0, 15.0, 15.0, 15.0, 15.0]
                }),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");
        assert!(v["result"]["impact"].is_number());
    }

    #[tokio::test]
    async fn sim_counterfactual_missing_pre_errors() {
        let tool = SimCounterfactualTool::new();
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({"post": [1.0]})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn sim_tools_are_mound_gana() {
        assert_eq!(SimMcTool::new().gana(), Gana::Mound);
        assert_eq!(SimForecastTool::new().gana(), Gana::Mound);
        assert_eq!(SimCounterfactualTool::new().gana(), Gana::Mound);
    }

    #[tokio::test]
    async fn parse_distribution_uniform() {
        let d = parse_distribution(&json!({"kind": "uniform", "min": 0.0, "max": 10.0})).unwrap();
        assert!(matches!(
            d,
            Distribution::Uniform {
                min: 0.0,
                max: 10.0
            }
        ));
    }

    #[tokio::test]
    async fn parse_distribution_normal() {
        let d =
            parse_distribution(&json!({"kind": "normal", "mean": 5.0, "std_dev": 2.0})).unwrap();
        assert!(matches!(
            d,
            Distribution::Normal {
                mean: 5.0,
                std_dev: 2.0
            }
        ));
    }

    #[tokio::test]
    async fn parse_distribution_unknown_errors() {
        let result = parse_distribution(&json!({"kind": "unknown"}));
        assert!(result.is_err());
    }
}
