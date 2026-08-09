//! Bayesian tools — mc.surrogate (GP regression) and mc.optimize
//! (Bayesian optimization with Expected Improvement).
//!
//! Gana::Mound — simulation, forecasting, and causal analysis.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use std::sync::Arc;

use serde_json::{Value, json};
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_simulation::{BayesianOptimizer, Expr, GaussianProcess};

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

        let mut result = json!({
            "status": "success",
            "n_samples": gp.n_samples(),
            "length_scale": gp.length_scale,
            "signal_variance": gp.signal_variance,
            "noise_variance": gp.noise_variance,
            "min_eigenvalue": gp.min_eigenvalue(),
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

// ── Registration ──────────────────────────────────────────────────────

/// Register all Bayesian tools into a registry.
#[must_use]
pub fn register_bayesian(registry: &wm_dispatch::ToolRegistry) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(McSurrogateTool::new()))
        .register(Arc::new(McOptimizeTool::new()))
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
}
