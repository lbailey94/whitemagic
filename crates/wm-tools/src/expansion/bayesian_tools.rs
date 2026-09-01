//! Bayesian tools — mc.surrogate (GP regression), mc.optimize (Bayesian
//! optimization), mc.rare_event, mc.sde, and mc.superforecaster.
//!
//! Gana::Mound — simulation, forecasting, and causal analysis.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use std::sync::Arc;

use serde_json::{Value, json};
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_simulation::{
    BayesianOptimizer, DriftType, Expr, GaussianProcess, SdeConfig, Solver, importance_sampling,
    solve, solve_mlmc, subset_simulation, superforecaster,
};

// ── mc.surrogate ─────────────────────────────────────────────────────

/// `mc.surrogate` — fit a Gaussian Process response surface and predict
/// at query points with uncertainty.
pub struct McSurrogateTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl McSurrogateTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("simulation".into())]),
        }
    }
}

impl Default for McSurrogateTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for McSurrogateTool {
    fn name(&self) -> &str {
        "mc.surrogate"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    fn description(&self) -> &str {
        "Fit a Gaussian process surrogate model to observations (args: x_train, y_train, length_scale, sigma_f, fit_hyperparameters) — Bayesian optimization of expensive functions"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let x_train = args
            .get("x_train")
            .and_then(Value::as_array)
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("x_train (array of arrays) is required".into())
            })?;
        let y_train = args
            .get("y_train")
            .and_then(Value::as_array)
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("y_train (array of numbers) is required".into())
            })?;
        if x_train.len() != y_train.len() {
            return Err(wm_core::CoreError::InvalidArgs(format!(
                "x_train ({}) and y_train ({}) length mismatch",
                x_train.len(),
                y_train.len()
            )));
        }

        let mut gp = GaussianProcess::new(
            args.get("length_scale")
                .and_then(Value::as_f64)
                .unwrap_or(1.0),
            args.get("sigma_f").and_then(Value::as_f64).unwrap_or(1.0),
            args.get("sigma_n").and_then(Value::as_f64).unwrap_or(0.01),
        );

        for (xi, yi) in x_train.iter().zip(y_train.iter()) {
            let row = xi
                .as_array()
                .ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("x_train rows must be arrays".into())
                })?
                .iter()
                .filter_map(Value::as_f64)
                .collect::<Vec<_>>();
            let y = yi
                .as_f64()
                .ok_or_else(|| wm_core::CoreError::InvalidArgs("y_train must be numbers".into()))?;
            gp.add_sample(row, y);
        }

        gp.fit().map_err(wm_core::CoreError::InvalidArgs)?;

        // Optional: optimize hyperparameters by maximizing the log marginal
        // likelihood (fixes the fixed-hyperparameter limitation)
        let fit_hp = args
            .get("fit_hyperparameters")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let hp_iterations = args
            .get("hp_iterations")
            .and_then(Value::as_u64)
            .unwrap_or(8) as usize;
        if fit_hp {
            gp.fit_hyperparameters(6, hp_iterations, 120, 42)
                .map_err(wm_core::CoreError::InvalidArgs)?;
        }

        let mut result = json!({
            "status": "success",
            "n_samples": gp.n_samples(),
            "length_scale": gp.length_scale,
            "signal_variance": gp.signal_variance,
            "noise_variance": gp.noise_variance,
            "min_eigenvalue": gp.min_eigenvalue(),
            "hyperparameters_fitted": fit_hp,
        });

        // Predict at query points if provided
        if let Some(queries) = args.get("x_predict").and_then(Value::as_array) {
            let predictions = queries
                .iter()
                .map(|q| {
                    let qv = q
                        .as_array()
                        .map(|a| a.iter().filter_map(Value::as_f64).collect::<Vec<_>>())
                        .ok_or_else(|| {
                            wm_core::CoreError::InvalidArgs("x_predict rows must be arrays".into())
                        })?;
                    let (mean, var) = gp.predict(&qv).map_err(wm_core::CoreError::InvalidArgs)?;
                    Ok(json!({
                        "input": qv,
                        "mean": mean,
                        "variance": var,
                        "std": var.sqrt(),
                    }))
                })
                .collect::<Result<Vec<_>, wm_core::CoreError>>()?;
            result["predictions"] = json!(predictions);
        }

        Ok(result)
    }
}

// ── mc.optimize ──────────────────────────────────────────────────────

/// `mc.optimize` — Bayesian optimization over a parameter box using a GP
/// surrogate + Expected Improvement. Fitness is a safe expression string
/// (e.g. `"-(x[0] - 3)^2 + 5"`).
pub struct McOptimizeTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl McOptimizeTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("simulation".into())]),
        }
    }
}

impl Default for McOptimizeTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for McOptimizeTool {
    fn name(&self) -> &str {
        "mc.optimize"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let ranges = args
            .get("param_ranges")
            .and_then(Value::as_array)
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs(
                    "param_ranges (array of [min, max] pairs) is required".into(),
                )
            })?;
        let mut bounds = Vec::with_capacity(ranges.len());
        for r in ranges {
            let arr = r.as_array().ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("param_ranges entries must be [min, max]".into())
            })?;
            if arr.len() != 2 {
                return Err(wm_core::CoreError::InvalidArgs(
                    "param_ranges entries must be [min, max] pairs".into(),
                ));
            }
            let lo = arr[0]
                .as_f64()
                .ok_or_else(|| wm_core::CoreError::InvalidArgs("min must be a number".into()))?;
            let hi = arr[1]
                .as_f64()
                .ok_or_else(|| wm_core::CoreError::InvalidArgs("max must be a number".into()))?;
            bounds.push((lo, hi));
        }

        let expr_src = args
            .get("fitness_expr")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("fitness_expr is required".into()))?;
        let expr = Expr::parse(expr_src)
            .map_err(|e| wm_core::CoreError::InvalidArgs(format!("fitness_expr: {e}")))?;

        let n_initial = args
            .get("n_initial_samples")
            .and_then(Value::as_u64)
            .unwrap_or(5) as usize;
        let n_iterations = args
            .get("n_iterations")
            .and_then(Value::as_u64)
            .unwrap_or(20) as usize;
        let n_candidates = args
            .get("n_candidates")
            .and_then(Value::as_u64)
            .unwrap_or(100) as usize;
        let seed = args.get("seed").and_then(Value::as_u64).unwrap_or(42);
        let exploration = args
            .get("exploration")
            .and_then(Value::as_f64)
            .unwrap_or(0.01);

        // Sanity check: expression must evaluate at a probe point
        let probe = vec![0.5_f64; bounds.len()];
        expr.evaluate(&probe).map_err(|e| {
            wm_core::CoreError::InvalidArgs(format!("fitness_expr invalid at probe point: {e}"))
        })?;

        let mut opt = BayesianOptimizer::new(
            |x: &[f64]| expr.evaluate(x).unwrap_or(f64::NEG_INFINITY),
            seed,
        );
        let (steps, (best_params, best_fitness)) = opt
            .optimize(&bounds, n_initial, n_iterations, n_candidates, exploration)
            .map_err(wm_core::CoreError::InvalidArgs)?;

        let trace = steps
            .iter()
            .map(|s| {
                json!({
                    "iteration": s.iteration,
                    "params": s.params,
                    "fitness": s.fitness,
                    "surrogate_mean": s.surrogate_mean,
                    "surrogate_std": s.surrogate_std,
                })
            })
            .collect::<Vec<_>>();

        Ok(json!({
            "status": "success",
            "best_params": best_params,
            "best_fitness": best_fitness,
            "iterations": steps.len(),
            "fitness_expr": expr_src,
            "trace": trace,
        }))
    }
}

// ── mc.rare_event ────────────────────────────────────────────────────

/// `mc.rare_event` — estimate rare-event probabilities with subset
/// simulation or importance sampling.
///
/// The limit-state function `g` is a safe expression string over the
/// standard-normal inputs `x[0..dim]`; failure is `g(x) > threshold`.
pub struct McRareEventTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl McRareEventTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("simulation".into())]),
        }
    }
}

impl Default for McRareEventTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for McRareEventTool {
    fn name(&self) -> &str {
        "mc.rare_event"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    fn description(&self) -> &str {
        "Estimate the probability of rare events with subset simulation or importance sampling (args: method, dim, n_samples, threshold, g_expr, seed)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let method = args
            .get("method")
            .and_then(Value::as_str)
            .unwrap_or("subset")
            .to_ascii_lowercase();
        let dim = args.get("dim").and_then(Value::as_u64).unwrap_or(2) as usize;
        if dim == 0 {
            return Err(wm_core::CoreError::InvalidArgs("dim must be ≥ 1".into()));
        }
        let n_samples = args
            .get("n_samples")
            .and_then(Value::as_u64)
            .unwrap_or(1000) as usize;
        let threshold = args.get("threshold").and_then(Value::as_f64).unwrap_or(2.0);
        let seed = args.get("seed").and_then(Value::as_u64).unwrap_or(42);
        let expr_src = args
            .get("g_expr")
            .and_then(Value::as_str)
            .unwrap_or("threshold - (x[0]^2 + x[1]^2)");
        // v26 default was "threshold - sum_sq"; rewrite into the safe form
        let expr_src = if expr_src.trim() == "threshold - sum_sq" {
            "threshold - (x[0]^2 + x[1]^2)"
        } else {
            expr_src
        };
        let expr = Expr::parse(expr_src)
            .map_err(|e| wm_core::CoreError::InvalidArgs(format!("g_expr: {e}")))?;

        let g = |x: &[f64]| expr.evaluate(x).unwrap_or(f64::NEG_INFINITY);

        match method.as_str() {
            "subset" => {
                let n_levels = args.get("n_levels").and_then(Value::as_u64).unwrap_or(5) as usize;
                let proposal_std = args
                    .get("proposal_std")
                    .and_then(Value::as_f64)
                    .unwrap_or(1.0);
                let r =
                    subset_simulation(dim, n_samples, n_levels, threshold, g, seed, proposal_std);
                Ok(json!({
                    "status": "success",
                    "method": "subset",
                    "probability": r.probability,
                    "levels_used": r.levels_used,
                    "n_samples_total": r.n_samples_total,
                }))
            }
            "importance" => {
                let r = importance_sampling(dim, n_samples, threshold, g, seed);
                Ok(json!({
                    "status": "success",
                    "method": "importance",
                    "probability": r.probability,
                    "coefficient_of_variation": r.coefficient_of_variation,
                    "hits": r.hits,
                    "n_samples": r.n_samples,
                }))
            }
            other => Err(wm_core::CoreError::InvalidArgs(format!(
                "unknown method '{other}' (expected subset | importance)"
            ))),
        }
    }
}

// ── mc.sde ───────────────────────────────────────────────────────────

/// `mc.sde` — solve stochastic differential equations with Euler–Maruyama
/// or Milstein, with optional two-level MLMC variance reduction.
pub struct McSdeTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl McSdeTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("simulation".into())]),
        }
    }
}

impl Default for McSdeTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for McSdeTool {
    fn name(&self) -> &str {
        "mc.sde"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    fn description(&self) -> &str {
        "Simulate stochastic differential equations with Euler or Milstein solvers (args: drift_type, solver, x0, t_end, n_steps, n_paths, mu, sigma)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let drift = DriftType::parse(
            args.get("drift_type")
                .and_then(Value::as_str)
                .unwrap_or("gbm"),
        )
        .map_err(wm_core::CoreError::InvalidArgs)?;
        let solver = Solver::parse(
            args.get("solver")
                .and_then(Value::as_str)
                .unwrap_or("euler"),
        )
        .map_err(wm_core::CoreError::InvalidArgs)?;

        let cfg = SdeConfig {
            x0: args.get("x0").and_then(Value::as_f64).unwrap_or(100.0),
            t_end: args.get("t_end").and_then(Value::as_f64).unwrap_or(1.0),
            n_steps: args.get("n_steps").and_then(Value::as_u64).unwrap_or(100) as usize,
            n_paths: args.get("n_paths").and_then(Value::as_u64).unwrap_or(1000) as usize,
            drift,
            mu: args.get("mu").and_then(Value::as_f64).unwrap_or(0.05),
            theta: args.get("theta").and_then(Value::as_f64).unwrap_or(1.0),
            sigma: args.get("sigma").and_then(Value::as_f64).unwrap_or(0.2),
            solver,
            seed: args.get("seed").and_then(Value::as_u64).unwrap_or(42),
        };

        let r = solve(&cfg);
        let mut result = json!({
            "status": "success",
            "mean": r.mean,
            "std": r.std,
            "p05": r.p05,
            "p50": r.p50,
            "p95": r.p95,
            "min": r.min,
            "max": r.max,
            "n_paths": r.n_paths,
            "dt": r.dt,
            "solver": format!("{solver:?}").to_ascii_lowercase(),
            "drift_type": match drift { DriftType::Gbm => "gbm", DriftType::Ou => "ou" },
        });

        if args.get("mlmc").and_then(Value::as_bool).unwrap_or(false) {
            let mlmc = solve_mlmc(&cfg);
            result["mlmc"] = json!({
                "mean": mlmc.mlmc_mean,
                "fine_mean": mlmc.fine_mean,
                "coarse_mean": mlmc.coarse_mean,
                "fine_std": mlmc.fine_std,
            });
        }

        Ok(result)
    }
}

// ── mc.superforecaster ───────────────────────────────────────────────

/// `mc.superforecaster` — the full pipeline: LHS exploration → PCE
/// surrogate with Sobol' sensitivity indices → Bayesian optimization.
pub struct McSuperforecasterTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl McSuperforecasterTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("simulation".into())]),
        }
    }
}

impl Default for McSuperforecasterTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for McSuperforecasterTool {
    fn name(&self) -> &str {
        "mc.superforecaster"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    fn description(&self) -> &str {
        "Run a superforecaster pipeline: Latin hypercube sampling, polynomial chaos expansion, Sobol sensitivity, then Bayesian optimization (args: param_ranges, budget, seed)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let ranges = args
            .get("param_ranges")
            .and_then(Value::as_array)
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs(
                    "param_ranges (array of [min, max] pairs) is required".into(),
                )
            })?;
        let mut bounds = Vec::with_capacity(ranges.len());
        for r in ranges {
            let arr = r.as_array().ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("param_ranges entries must be [min, max]".into())
            })?;
            if arr.len() != 2 {
                return Err(wm_core::CoreError::InvalidArgs(
                    "param_ranges entries must be [min, max] pairs".into(),
                ));
            }
            bounds.push((
                arr[0].as_f64().ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("min must be a number".into())
                })?,
                arr[1].as_f64().ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("max must be a number".into())
                })?,
            ));
        }

        let expr_src = args
            .get("fitness_expr")
            .and_then(Value::as_str)
            .unwrap_or("x[0]");
        let expr = Expr::parse(expr_src)
            .map_err(|e| wm_core::CoreError::InvalidArgs(format!("fitness_expr: {e}")))?;

        let n_initial = args
            .get("n_initial_samples")
            .and_then(Value::as_u64)
            .unwrap_or(20) as usize;
        let n_bo = args
            .get("n_bo_iterations")
            .and_then(Value::as_u64)
            .unwrap_or(15) as usize;
        let pce_degree = args.get("pce_degree").and_then(Value::as_u64).unwrap_or(3) as usize;
        let seed = args.get("seed").and_then(Value::as_u64).unwrap_or(42);

        let probe = vec![0.5_f64; bounds.len()];
        expr.evaluate(&probe).map_err(|e| {
            wm_core::CoreError::InvalidArgs(format!("fitness_expr invalid at probe point: {e}"))
        })?;

        let r = superforecaster(
            &bounds,
            |x: &[f64]| expr.evaluate(x).unwrap_or(f64::NEG_INFINITY),
            n_initial,
            n_bo,
            pce_degree,
            seed,
        );

        Ok(json!({
            "status": "success",
            "best_params": r.best_params,
            "best_fitness": r.best_fitness,
            "pce_r_squared": r.pce_r_squared,
            "sobol_first_order": r.sobol_first_order,
            "sobol_total": r.sobol_total,
            "n_initial": r.n_initial,
            "n_bo_iterations": r.n_bo_iterations,
        }))
    }
}

// ── Registration ──────────────────────────────────────────────────────

/// Register all Bayesian tools into a registry.
#[must_use]
pub fn register_bayesian(registry: &wm_dispatch::ToolRegistry) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(McSurrogateTool::new()))
        .register(Arc::new(McOptimizeTool::new()))
        .register(Arc::new(McRareEventTool::new()))
        .register(Arc::new(McSdeTool::new()))
        .register(Arc::new(McSuperforecasterTool::new()))
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn surrogate_fits_and_predicts() {
        let tool = McSurrogateTool::new();
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "x_train": [[0.0], [1.0], [2.0], [3.0], [4.0]],
                    "y_train": [1.0, 3.0, 5.0, 7.0, 9.0],
                    "x_predict": [[2.0], [10.0]],
                    "length_scale": 1.0,
                    "sigma_f": 1.0,
                    "sigma_n": 0.01,
                }),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["n_samples"], 5);
        let preds = v["predictions"].as_array().unwrap();
        assert!((preds[0]["mean"].as_f64().unwrap() - 5.0).abs() < 1.5);
        // Far query should have higher uncertainty
        assert!(preds[1]["variance"].as_f64().unwrap() > preds[0]["variance"].as_f64().unwrap());
    }

    #[tokio::test]
    async fn surrogate_requires_matching_lengths() {
        let tool = McSurrogateTool::new();
        let mut ctx = Context::default();
        let err = tool
            .call(
                &mut ctx,
                json!({"x_train": [[0.0], [1.0]], "y_train": [1.0]}),
            )
            .await;
        assert!(err.is_err());
        let err = tool
            .call(&mut ctx, json!({"x_train": [[0.0]], "y_train": [1.0, 2.0]}))
            .await;
        assert!(err.is_err());
    }

    #[tokio::test]
    async fn surrogate_fits_hyperparameters() {
        let tool = McSurrogateTool::new();
        let mut ctx = Context::default();
        // High-frequency data — a fixed long length scale would be wrong
        let xs: Vec<Vec<f64>> = (0..25).map(|i| vec![f64::from(i) * 0.15]).collect();
        let ys: Vec<f64> = (0..25)
            .map(|i| (2.5_f64 * (f64::from(i) * 0.15)).sin())
            .collect();
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "x_train": xs,
                    "y_train": ys,
                    "fit_hyperparameters": true,
                    "hp_iterations": 8,
                    "x_predict": [[1.8]],
                }),
            )
            .await
            .unwrap();
        assert_eq!(v["hyperparameters_fitted"], true);
        assert!(
            v["length_scale"].as_f64().unwrap() < 3.0,
            "ℓ = {}",
            v["length_scale"]
        );
        // Prediction near the fitted surface
        let truth = (2.5_f64 * 1.8).sin();
        assert!(
            (v["predictions"][0]["mean"].as_f64().unwrap() - truth).abs() < 0.2,
            "pred {} vs truth {truth}",
            v["predictions"][0]["mean"]
        );
    }

    #[tokio::test]
    async fn optimize_finds_parabola_peak() {
        let tool = McOptimizeTool::new();
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "param_ranges": [[0.0, 10.0]],
                    "fitness_expr": "-(x[0] - 3)^2 + 5",
                    "n_initial_samples": 5,
                    "n_iterations": 10,
                    "n_candidates": 200,
                    "seed": 42,
                }),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");
        assert!((v["best_params"][0].as_f64().unwrap() - 3.0).abs() < 0.5);
        assert!((v["best_fitness"].as_f64().unwrap() - 5.0).abs() < 0.5);
        let trace = v["trace"].as_array().unwrap();
        assert!(!trace.is_empty());
    }

    #[tokio::test]
    async fn optimize_rejects_bad_input() {
        let tool = McOptimizeTool::new();
        let mut ctx = Context::default();
        // Missing ranges
        assert!(
            tool.call(&mut ctx, json!({"fitness_expr": "x[0]"}))
                .await
                .is_err()
        );
        // Bad expression
        assert!(
            tool.call(
                &mut ctx,
                json!({"param_ranges": [[0.0, 1.0]], "fitness_expr": "foo(x[0])"})
            )
            .await
            .is_err()
        );
        // Expression referencing out-of-range dim
        assert!(
            tool.call(
                &mut ctx,
                json!({"param_ranges": [[0.0, 1.0]], "fitness_expr": "x[3]"})
            )
            .await
            .is_err()
        );
    }

    #[tokio::test]
    async fn rare_event_subset_matches_chi_square() {
        let tool = McRareEventTool::new();
        let mut ctx = Context::default();
        // P(χ²₂ > 9) = exp(-4.5) ≈ 0.0111
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "method": "subset",
                    "dim": 2,
                    "n_samples": 2000,
                    "n_levels": 3,
                    "threshold": 9.0,
                    "g_expr": "x[0]^2 + x[1]^2",
                    "seed": 42,
                }),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");
        let p = v["probability"].as_f64().unwrap();
        assert!((p - 0.0111).abs() < 0.01, "p = {p}");
    }

    #[tokio::test]
    async fn rare_event_importance_and_errors() {
        let tool = McRareEventTool::new();
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"method": "importance", "dim": 2, "n_samples": 20000, "threshold": 9.0, "g_expr": "x[0]^2 + x[1]^2"}),
            )
            .await
            .unwrap();
        assert!((v["probability"].as_f64().unwrap() - 0.0111).abs() < 0.01);
        // Bad method / bad expr / dim 0
        assert!(
            tool.call(&mut ctx, json!({"method": "bogus"}))
                .await
                .is_err()
        );
        assert!(
            tool.call(&mut ctx, json!({"g_expr": "foo(1)"}))
                .await
                .is_err()
        );
        assert!(tool.call(&mut ctx, json!({"dim": 0})).await.is_err());
    }

    #[tokio::test]
    async fn sde_gbm_matches_analytic_mean() {
        let tool = McSdeTool::new();
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "x0": 100.0, "t_end": 1.0, "n_steps": 200, "n_paths": 20000,
                    "drift_type": "gbm", "mu": 0.05, "sigma": 0.3, "solver": "euler", "seed": 42
                }),
            )
            .await
            .unwrap();
        let analytic = 100.0 * (0.05_f64).exp();
        assert!((v["mean"].as_f64().unwrap() - analytic).abs() / analytic < 0.02);
        assert!(v["p05"].as_f64().unwrap() < v["p95"].as_f64().unwrap());
        // Milstein
        let v2 = tool
            .call(
                &mut ctx,
                json!({"solver": "milstein", "drift_type": "gbm", "n_paths": 5000, "n_steps": 200}),
            )
            .await
            .unwrap();
        assert!(v2["min"].as_f64().unwrap() > 0.0);
    }

    #[tokio::test]
    async fn sde_mlmc_and_errors() {
        let tool = McSdeTool::new();
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"mlmc": true, "n_paths": 5000, "n_steps": 100, "drift_type": "gbm"}),
            )
            .await
            .unwrap();
        assert!(v["mlmc"]["mean"].as_f64().is_some());
        // Bad drift type / solver
        assert!(
            tool.call(&mut ctx, json!({"drift_type": "bogus"}))
                .await
                .is_err()
        );
        assert!(
            tool.call(&mut ctx, json!({"solver": "bogus"}))
                .await
                .is_err()
        );
    }

    #[tokio::test]
    async fn superforecaster_full_pipeline() {
        let tool = McSuperforecasterTool::new();
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({
                    "param_ranges": [[0.0, 10.0], [0.0, 10.0]],
                    "fitness_expr": "-(x[0] - 3)^2 - (x[1] - 7)^2 + 10",
                    "n_initial_samples": 10,
                    "n_bo_iterations": 10,
                    "pce_degree": 3,
                    "seed": 42,
                }),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");
        assert!((v["best_params"][0].as_f64().unwrap() - 3.0).abs() < 1.0);
        assert!((v["best_params"][1].as_f64().unwrap() - 7.0).abs() < 1.0);
        assert!((v["best_fitness"].as_f64().unwrap() - 10.0).abs() < 1.5);
        assert_eq!(v["sobol_first_order"].as_array().unwrap().len(), 2);
        assert!(v["pce_r_squared"].as_f64().is_some());
    }
}
