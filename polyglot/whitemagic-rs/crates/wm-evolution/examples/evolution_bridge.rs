//! WhiteMagic Evolution JSON stdio bridge
//!
//! Reads JSON requests from stdin, writes JSON responses to stdout.
//! Usage: cargo run --example evolution_bridge --release
//!
//! Supported methods:
//!   - ping
//!   - shannon_entropy: {"p": 0.5}
//!   - kl_divergence: {"p": 0.5, "q": 0.3}
//!   - information_gain: {"p_success": 0.7, "n_prior": 10}
//!   - system_uncertainty: {"confidences": [0.5, 0.7, 0.3]}
//!   - adapt_weights: {"system_entropy": 0.8, "max_entropy": 1.0}
//!   - exploration_score: {"predicted_impact": 0.8, "p_success": 0.7, "novelty": 0.5, "n_prior": 10}
//!   - thermo_cool: {"temperature": 1.0, "cooling_rate": 0.95, "min_temperature": 0.01}
//!   - thermo_reheat: {"temperature": 0.1, "reheat_amount": 0.3, "emergence_signal": 1.0, "max_temperature": 2.0}
//!   - thermo_adapt: {state..., "discovery_rate": 0.5, "emergence_signal": 0.3}
//!   - boltzmann_probabilities: {"energies": [0.1, 0.2, 0.3], "temperature": 1.0}
//!   - boltzmann_select: {"energies": [0.1, 0.2, 0.3], "temperature": 0.5, "k": 2, "seed": 42}
//!   - hrr_encode: {"description": "fix untitled", "dim": 384, "impact": 0.5}
//!   - hrr_bind: {"a": [...], "b": [...]}
//!   - hrr_unbind: {"composite": [...], "component": [...]}
//!   - hrr_superposition: {"vectors": [[...], [...], ...]}
//!   - hrr_synergy: {"composite": [...], "impacts": [0.5, 0.3]}
//!   - hrr_similarity: {"a": [...], "b": [...]}
//!   - mc_run_trials: {"n_trials": 5000, "prior_mean": 0.5, "prior_variance": 0.1, "seed": 42}
//!   - mc_importance_sampling: {"n_trials": 5000, ..., "proposal_variance": 0.3}
//!   - mc_control_variates: {"n_trials": 5000, ..., "control_mean": 0.5, "control_variance": 0.05}
//!   - mc_antithetic_variates: {"n_trials": 5000, ...}
//!   - cf_project_forward: {"pre_values": [1.0, 2.0, ...], "smoothing_alpha": 0.3, "n_steps": 5}
//!   - cf_bootstrap_ci: {"pre_values": [...], "n_steps": 5, "n_bootstrap": 500, "confidence": 0.95}
//!   - cf_estimate_impact: {"pre_values": [...], "post_values": [...], "n_bootstrap": 500}

use std::io::{self, BufRead, Write};
use wm_evolution::{
    counterfactual,
    hrr_composition,
    info_theory::{shannon_entropy, kl_divergence, information_gain, system_uncertainty, AdaptiveWeights},
    mc_advanced,
    mc_bayesian,
    mc_integration,
    mc_rare_event,
    mc_sde,
    mc_sensitivity,
    thermodynamic::{boltzmann_probabilities, boltzmann_select, ThermodynamicState},
};

fn main() {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut stdout_lock = stdout.lock();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) if l.trim().is_empty() => continue,
            Ok(l) => l,
            Err(_) => break,
        };

        let response = match serde_json::from_str::<serde_json::Value>(&line) {
            Ok(req) => handle_request(req),
            Err(e) => json_error(&format!("Invalid JSON: {}", e)),
        };

        if writeln!(stdout_lock, "{}", response).is_err() {
            break;
        }
        let _ = stdout_lock.flush();
    }
}

fn handle_request(req: serde_json::Value) -> String {
    let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let params = req.get("params").cloned().unwrap_or(serde_json::json!({}));

    match method {
        "ping" => json_ok(serde_json::json!({"backend": "rust-evolution"})),

        "shannon_entropy" => {
            let p = params.get("p").and_then(|v| v.as_f64()).unwrap_or(0.5);
            json_ok(serde_json::json!({"entropy": shannon_entropy(p)}))
        }

        "kl_divergence" => {
            let p = params.get("p").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let q = params.get("q").and_then(|v| v.as_f64()).unwrap_or(0.5);
            json_ok(serde_json::json!({"divergence": kl_divergence(p, q)}))
        }

        "information_gain" => {
            let p_success = params.get("p_success").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let n_prior = params.get("n_prior").and_then(|v| v.as_i64()).unwrap_or(10) as i32;
            json_ok(serde_json::json!({"information_gain": information_gain(p_success, n_prior)}))
        }

        "system_uncertainty" => {
            let confidences: Vec<f64> = params
                .get("confidences")
                .and_then(|c| c.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_f64()).collect())
                .unwrap_or_default();
            json_ok(serde_json::json!({"uncertainty": system_uncertainty(&confidences)}))
        }

        "adapt_weights" => {
            let system_entropy = params.get("system_entropy").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let max_entropy = params.get("max_entropy").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let mut w = AdaptiveWeights::default();
            w.adapt(system_entropy, max_entropy);
            json_ok(serde_json::json!({
                "alpha": w.alpha,
                "beta": w.beta,
                "gamma": w.gamma,
            }))
        }

        "exploration_score" => {
            let predicted_impact = params.get("predicted_impact").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let p_success = params.get("p_success").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let novelty = params.get("novelty").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let n_prior = params.get("n_prior").and_then(|v| v.as_i64()).unwrap_or(10) as i32;
            let ig = information_gain(p_success, n_prior);
            let w = AdaptiveWeights::default();
            let score = w.score(predicted_impact, p_success, novelty, n_prior);
            json_ok(serde_json::json!({
                "score": score,
                "information_gain": ig,
                "alpha": w.alpha,
                "beta": w.beta,
                "gamma": w.gamma,
            }))
        }

        "thermo_cool" => {
            let mut state = parse_thermo_state(&params);
            state.cool();
            json_ok(serde_json::json!({
                "temperature": state.temperature,
                "cycle_count": state.cycle_count,
            }))
        }

        "thermo_reheat" => {
            let emergence = params.get("emergence_signal").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let mut state = parse_thermo_state(&params);
            state.reheat(emergence);
            json_ok(serde_json::json!({"temperature": state.temperature}))
        }

        "thermo_adapt" => {
            let discovery_rate = params.get("discovery_rate").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let emergence = params.get("emergence_signal").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let mut state = parse_thermo_state(&params);
            state.adapt(discovery_rate, emergence);
            json_ok(serde_json::json!({
                "temperature": state.temperature,
                "exploration_phase": state.exploration_phase(),
                "cycle_count": state.cycle_count,
            }))
        }

        "boltzmann_probabilities" => {
            let energies: Vec<f64> = params
                .get("energies")
                .and_then(|e| e.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_f64()).collect())
                .unwrap_or_default();
            let temperature = params.get("temperature").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let probs = boltzmann_probabilities(&energies, temperature);
            json_ok(serde_json::json!({"probabilities": probs}))
        }

        "boltzmann_select" => {
            let energies: Vec<f64> = params
                .get("energies")
                .and_then(|e| e.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_f64()).collect())
                .unwrap_or_default();
            let temperature = params.get("temperature").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let k = params.get("k").and_then(|v| v.as_u64()).unwrap_or(1) as usize;
            let seed = params.get("seed").and_then(|v| v.as_u64()).unwrap_or(42);
            let selected = boltzmann_select(&energies, temperature, k, seed);
            json_ok(serde_json::json!({"selected_indices": selected}))
        }

        "hrr_encode" => {
            let description = params.get("description").and_then(|v| v.as_str()).unwrap_or("");
            let dim = params.get("dim").and_then(|v| v.as_u64()).unwrap_or(384) as usize;
            let impact = params.get("impact").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let vec = hrr_composition::encode_hypothesis(description, dim, impact);
            json_ok(serde_json::json!({"vector": vec}))
        }

        "hrr_bind" => {
            let a: Vec<f64> = params
                .get("a")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let b: Vec<f64> = params
                .get("b")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            if a.is_empty() || b.is_empty() || a.len() != b.len() {
                json_error("hrr_bind requires equal-length non-empty 'a' and 'b' arrays")
            } else {
                let bound = hrr_composition::bind(&a, &b);
                json_ok(serde_json::json!({"vector": bound}))
            }
        }

        "hrr_unbind" => {
            let composite: Vec<f64> = params
                .get("composite")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let component: Vec<f64> = params
                .get("component")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            if composite.is_empty() || component.is_empty() || composite.len() != component.len() {
                json_error("hrr_unbind requires equal-length non-empty 'composite' and 'component' arrays")
            } else {
                let recovered = hrr_composition::unbind(&composite, &component);
                json_ok(serde_json::json!({"vector": recovered}))
            }
        }

        "hrr_superposition" => {
            let vectors: Vec<Vec<f64>> = params
                .get("vectors")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_array())
                        .map(|inner| inner.iter().filter_map(|x| x.as_f64()).collect())
                        .collect()
                })
                .unwrap_or_default();
            if vectors.len() < 2 {
                json_error("hrr_superposition requires at least 2 vectors")
            } else {
                let result = hrr_composition::superposition(&vectors);
                json_ok(serde_json::json!({"vector": result}))
            }
        }

        "hrr_synergy" => {
            let composite: Vec<f64> = params
                .get("composite")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let impacts: Vec<f64> = params
                .get("impacts")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let synergy = hrr_composition::compute_synergy(&composite, &impacts);
            json_ok(serde_json::json!({"synergy": synergy}))
        }

        "hrr_similarity" => {
            let a: Vec<f64> = params
                .get("a")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let b: Vec<f64> = params
                .get("b")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            if a.is_empty() || b.is_empty() || a.len() != b.len() {
                json_error("hrr_similarity requires equal-length non-empty 'a' and 'b' arrays")
            } else {
                let sim = hrr_composition::cosine_similarity(&a, &b);
                json_ok(serde_json::json!({"similarity": sim}))
            }
        }

        "mc_run_trials" => {
            let n_trials = params.get("n_trials").and_then(|v| v.as_i64()).unwrap_or(1000) as i32;
            let prior_mean = params.get("prior_mean").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let prior_variance = params.get("prior_variance").and_then(|v| v.as_f64()).unwrap_or(0.1);
            let seed = params.get("seed").and_then(|v| v.as_u64()).unwrap_or(42);
            let (mean, variance, n) = mc_integration::run_trials(n_trials, prior_mean, prior_variance, seed);
            let (ci_lo, ci_hi) = mc_integration::confidence_interval(mean, variance);
            json_ok(serde_json::json!({
                "mean": mean, "variance": variance, "n_completed": n,
                "ci_lower": ci_lo, "ci_upper": ci_hi
            }))
        }

        "mc_importance_sampling" => {
            let n_trials = params.get("n_trials").and_then(|v| v.as_i64()).unwrap_or(1000) as i32;
            let prior_mean = params.get("prior_mean").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let prior_variance = params.get("prior_variance").and_then(|v| v.as_f64()).unwrap_or(0.1);
            let proposal_variance = params.get("proposal_variance").and_then(|v| v.as_f64()).unwrap_or(0.3);
            let seed = params.get("seed").and_then(|v| v.as_u64()).unwrap_or(42);
            let (mean, variance, n) = mc_integration::importance_sampling(
                n_trials, prior_mean, prior_variance, proposal_variance, seed,
            );
            let (ci_lo, ci_hi) = mc_integration::confidence_interval(mean, variance);
            json_ok(serde_json::json!({
                "mean": mean, "variance": variance, "n_completed": n,
                "ci_lower": ci_lo, "ci_upper": ci_hi
            }))
        }

        "mc_control_variates" => {
            let n_trials = params.get("n_trials").and_then(|v| v.as_i64()).unwrap_or(1000) as i32;
            let prior_mean = params.get("prior_mean").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let prior_variance = params.get("prior_variance").and_then(|v| v.as_f64()).unwrap_or(0.1);
            let control_mean = params.get("control_mean").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let control_variance = params.get("control_variance").and_then(|v| v.as_f64()).unwrap_or(0.05);
            let seed = params.get("seed").and_then(|v| v.as_u64()).unwrap_or(42);
            let (mean, variance, n) = mc_integration::control_variates(
                n_trials, prior_mean, prior_variance, control_mean, control_variance, seed,
            );
            let (ci_lo, ci_hi) = mc_integration::confidence_interval(mean, variance);
            json_ok(serde_json::json!({
                "mean": mean, "variance": variance, "n_completed": n,
                "ci_lower": ci_lo, "ci_upper": ci_hi
            }))
        }

        "mc_antithetic_variates" => {
            let n_trials = params.get("n_trials").and_then(|v| v.as_i64()).unwrap_or(1000) as i32;
            let prior_mean = params.get("prior_mean").and_then(|v| v.as_f64()).unwrap_or(0.5);
            let prior_variance = params.get("prior_variance").and_then(|v| v.as_f64()).unwrap_or(0.1);
            let seed = params.get("seed").and_then(|v| v.as_u64()).unwrap_or(42);
            let (mean, variance, n) = mc_integration::antithetic_variates(
                n_trials, prior_mean, prior_variance, seed,
            );
            let (ci_lo, ci_hi) = mc_integration::confidence_interval(mean, variance);
            json_ok(serde_json::json!({
                "mean": mean, "variance": variance, "n_completed": n,
                "ci_lower": ci_lo, "ci_upper": ci_hi
            }))
        }

        "cf_project_forward" => {
            let pre_values: Vec<f64> = params
                .get("pre_values")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let alpha = params.get("smoothing_alpha").and_then(|v| v.as_f64()).unwrap_or(0.3);
            let n_steps = params.get("n_steps").and_then(|v| v.as_i64()).unwrap_or(1) as i32;
            let proj = counterfactual::project_forward(&pre_values, alpha, n_steps);
            json_ok(serde_json::json!({"projections": proj}))
        }

        "cf_bootstrap_ci" => {
            let pre_values: Vec<f64> = params
                .get("pre_values")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let alpha = params.get("smoothing_alpha").and_then(|v| v.as_f64()).unwrap_or(0.3);
            let n_steps = params.get("n_steps").and_then(|v| v.as_i64()).unwrap_or(1) as i32;
            let n_bootstrap = params.get("n_bootstrap").and_then(|v| v.as_i64()).unwrap_or(500) as i32;
            let confidence = params.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.95);
            let seed = params.get("seed").and_then(|v| v.as_u64()).unwrap_or(42);
            let (lower, upper) = counterfactual::bootstrap_ci(
                &pre_values, alpha, n_steps, n_bootstrap, confidence, seed,
            );
            json_ok(serde_json::json!({"ci_lower": lower, "ci_upper": upper}))
        }

        "cf_estimate_impact" => {
            let pre_values: Vec<f64> = params
                .get("pre_values")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let post_values: Vec<f64> = params
                .get("post_values")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let alpha = params.get("smoothing_alpha").and_then(|v| v.as_f64()).unwrap_or(0.3);
            let n_bootstrap = params.get("n_bootstrap").and_then(|v| v.as_i64()).unwrap_or(500) as i32;
            let confidence = params.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.95);
            let seed = params.get("seed").and_then(|v| v.as_u64()).unwrap_or(42);
            let (actual, control, impact, ci_lo, ci_hi) = counterfactual::estimate_impact(
                &pre_values, &post_values, alpha, n_bootstrap, confidence, seed,
            );
            let significant = counterfactual::is_significant(ci_lo, ci_hi);
            json_ok(serde_json::json!({
                "actual_post": actual,
                "synthetic_control": control,
                "causal_impact": impact,
                "ci_lower": ci_lo,
                "ci_upper": ci_hi,
                "significant": significant,
            }))
        }

        "mc_multid_gaussian" => {
            let n_samples = params.get("n_samples").and_then(|v| v.as_u64()).unwrap_or(1000) as usize;
            let mean: Vec<f64> = params.get("mean")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let cov: Vec<f64> = params.get("cov")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let seed = params.get("seed").and_then(|v| v.as_u64()).unwrap_or(42);
            if mean.is_empty() || cov.is_empty() {
                json_error("mc_multid_gaussian requires non-empty 'mean' and 'cov' arrays")
            } else {
                let samples = mc_advanced::multid_gaussian(n_samples, &mean, &cov, seed);
                json_ok(serde_json::json!({"samples": samples, "n_samples": samples.len()}))
            }
        }

        "mc_latin_hypercube" => {
            let n = params.get("n").and_then(|v| v.as_u64()).unwrap_or(100) as usize;
            let d = params.get("d").and_then(|v| v.as_u64()).unwrap_or(1) as usize;
            let seed = params.get("seed").and_then(|v| v.as_u64()).unwrap_or(42);
            let samples = mc_advanced::latin_hypercube(n, d, seed);
            json_ok(serde_json::json!({"samples": samples, "n": samples.len()}))
        }

        "mc_lhs_trials" => {
            // LHS sampling + parallel fitness evaluation
            // fitness_fn is passed as a JSON expression string (evaluated in Python)
            // Here we just generate the LHS samples; Python evaluates fitness
            let n = params.get("n").and_then(|v| v.as_u64()).unwrap_or(100) as usize;
            let ranges: Vec<(f64, f64)> = params.get("ranges")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter().filter_map(|r| {
                        let ra = r.as_array()?;
                        if ra.len() >= 2 {
                            Some((ra[0].as_f64()?, ra[1].as_f64()?))
                        } else {
                            None
                        }
                    }).collect()
                })
                .unwrap_or_default();
            let seed = params.get("seed").and_then(|v| v.as_u64()).unwrap_or(42);
            if ranges.is_empty() {
                json_error("mc_lhs_trials requires non-empty 'ranges' array of [lo, hi] pairs")
            } else {
                let unit = mc_advanced::latin_hypercube(n, ranges.len(), seed);
                let scaled: Vec<Vec<f64>> = unit.iter().map(|s| {
                    s.iter().enumerate().map(|(i, &v)| {
                        let (lo, hi) = ranges[i];
                        lo + v * (hi - lo)
                    }).collect()
                }).collect();
                json_ok(serde_json::json!({
                    "samples": scaled,
                    "n": scaled.len(),
                    "d": ranges.len()
                }))
            }
        }

        "mc_compute_statistics" => {
            let values: Vec<f64> = params.get("values")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            if values.is_empty() {
                json_error("mc_compute_statistics requires non-empty 'values' array")
            } else {
                let (mean, variance, min, max, p5, p25, p50, p75, p95) =
                    mc_advanced::compute_statistics(&values);
                let (ci_lo, ci_hi) = mc_advanced::confidence_interval(mean, variance);
                json_ok(serde_json::json!({
                    "mean": mean, "variance": variance,
                    "min": min, "max": max,
                    "percentiles": {"p5": p5, "p25": p25, "p50": p50, "p75": p75, "p95": p95},
                    "ci_95": {"lower": ci_lo, "upper": ci_hi}
                }))
            }
        }

        "mc_pce_fit" => {
            // Fit PCE surrogate to (X, Y) data
            let x_data: Vec<Vec<f64>> = params.get("x_data")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter().filter_map(|row| {
                        row.as_array().map(|r| r.iter().filter_map(|x| x.as_f64()).collect())
                    }).collect()
                })
                .unwrap_or_default();
            let y_data: Vec<f64> = params.get("y_data")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let max_order = params.get("max_order").and_then(|v| v.as_u64()).unwrap_or(3) as usize;
            let dist_type = params.get("dist_type").and_then(|v| v.as_str()).unwrap_or("uniform");
            if x_data.is_empty() || y_data.is_empty() {
                json_error("mc_pce_fit requires non-empty 'x_data' and 'y_data' arrays")
            } else if x_data.len() != y_data.len() {
                json_error("x_data and y_data must have the same length")
            } else {
                let pce = mc_sensitivity::PCESurrogate::fit(&x_data, &y_data, max_order, dist_type);
                let r2 = pce.r_squared(&x_data, &y_data);
                json_ok(serde_json::json!({
                    "dim": pce.dim,
                    "max_order": pce.max_order,
                    "n_terms": pce.n_terms(),
                    "coefficients": pce.coefficients,
                    "multi_indices": pce.multi_indices,
                    "dist_type": pce.dist_type,
                    "r_squared": r2
                }))
            }
        }

        "mc_pce_evaluate" => {
            // Evaluate a fitted PCE at new points
            let coefficients: Vec<f64> = params.get("coefficients")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let multi_indices: Vec<Vec<usize>> = params.get("multi_indices")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter().filter_map(|row| {
                        row.as_array().map(|r| r.iter().filter_map(|x| x.as_u64().map(|n| n as usize)).collect())
                    }).collect()
                })
                .unwrap_or_default();
            let dist_type = params.get("dist_type").and_then(|v| v.as_str()).unwrap_or("uniform");
            let x_data: Vec<Vec<f64>> = params.get("x_data")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter().filter_map(|row| {
                        row.as_array().map(|r| r.iter().filter_map(|x| x.as_f64()).collect())
                    }).collect()
                })
                .unwrap_or_default();
            let max_order = params.get("max_order").and_then(|v| v.as_u64()).unwrap_or(3) as usize;
            if coefficients.is_empty() || x_data.is_empty() {
                json_error("mc_pce_evaluate requires 'coefficients', 'multi_indices', and 'x_data'")
            } else {
                let pce = mc_sensitivity::PCESurrogate {
                    dim: if x_data.is_empty() { 0 } else { x_data[0].len() },
                    max_order,
                    dist_type: dist_type.to_string(),
                    coefficients,
                    multi_indices,
                };
                let predictions = pce.evaluate_batch(&x_data);
                json_ok(serde_json::json!({"predictions": predictions}))
            }
        }

        "mc_parameter_sensitivity" => {
            // Compute Pearson correlations for each parameter vs fitness
            let samples: Vec<Vec<f64>> = params.get("samples")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter().filter_map(|row| {
                        row.as_array().map(|r| r.iter().filter_map(|x| x.as_f64()).collect())
                    }).collect()
                })
                .unwrap_or_default();
            let fitness: Vec<f64> = params.get("fitness")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            if samples.is_empty() || fitness.is_empty() {
                json_error("mc_parameter_sensitivity requires 'samples' and 'fitness' arrays")
            } else {
                let sens = mc_sensitivity::parameter_sensitivity(&samples, &fitness);
                let result: Vec<serde_json::Value> = sens.iter().map(|(idx, corr)| {
                    serde_json::json!({"param_index": idx, "correlation": corr, "abs_correlation": corr.abs()})
                }).collect();
                json_ok(serde_json::json!({"sensitivities": result}))
            }
        }

        "mc_sobol_indices" => {
            // Compute Sobol sensitivity indices via Saltelli's method
            // fitness_fn is a JSON expression string evaluated in Python
            // Here we can't evaluate arbitrary Python, so we require pre-computed
            // fitness values for the Saltelli sample matrices
            let n_base = params.get("n_base").and_then(|v| v.as_u64()).unwrap_or(500) as usize;
            let d = params.get("d").and_then(|v| v.as_u64()).unwrap_or(1) as usize;
            let ranges: Vec<(f64, f64)> = params.get("ranges")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter().filter_map(|r| {
                        let ra = r.as_array()?;
                        if ra.len() >= 2 {
                            Some((ra[0].as_f64()?, ra[1].as_f64()?))
                        } else {
                            None
                        }
                    }).collect()
                })
                .unwrap_or_default();
            let seed = params.get("seed").and_then(|v| v.as_u64()).unwrap_or(42);
            if ranges.is_empty() {
                json_error("mc_sobol_indices requires 'ranges' array of [lo, hi] pairs")
            } else {
                // Generate Saltelli sample matrices A and B
                use rand::{RngCore, SeedableRng};
                use rand_xoshiro::Xoshiro256PlusPlus;
                let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);
                let scale = |u: f64, i: usize| -> f64 {
                    let (lo, hi) = ranges[i];
                    lo + u * (hi - lo)
                };
                let mut a_samples = vec![vec![0.0f64; d]; n_base];
                let mut b_samples = vec![vec![0.0f64; d]; n_base];
                for i in 0..n_base {
                    for j in 0..d {
                        a_samples[i][j] = scale(rng.next_u64() as f64 / u64::MAX as f64, j);
                        b_samples[i][j] = scale(rng.next_u64() as f64 / u64::MAX as f64, j);
                    }
                }
                // Generate AB_j matrices
                let mut ab_matrices = vec![vec![vec![0.0f64; d]; n_base]; d];
                for j in 0..d {
                    for i in 0..n_base {
                        ab_matrices[j][i] = a_samples[i].clone();
                        ab_matrices[j][i][j] = b_samples[i][j];
                    }
                }
                json_ok(serde_json::json!({
                    "a_samples": a_samples,
                    "b_samples": b_samples,
                    "ab_matrices": ab_matrices,
                    "n_base": n_base,
                    "d": d,
                    "instructions": "Evaluate fitness for a_samples, b_samples, and each ab_matrices[j]. Then call mc_sobol_compute with f_a, f_b, f_ab arrays."
                }))
            }
        }

        "mc_sobol_compute" => {
            // Compute Sobol indices from pre-evaluated fitness values
            let f_a: Vec<f64> = params.get("f_a")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let f_b: Vec<f64> = params.get("f_b")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default();
            let f_ab: Vec<Vec<f64>> = params.get("f_ab")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter().filter_map(|row| {
                        row.as_array().map(|r| r.iter().filter_map(|x| x.as_f64()).collect())
                    }).collect()
                })
                .unwrap_or_default();
            if f_a.is_empty() || f_b.is_empty() || f_ab.is_empty() {
                json_error("mc_sobol_compute requires 'f_a', 'f_b', and 'f_ab' arrays")
            } else {
                let n_base = f_a.len();
                let d = f_ab.len();
                let f_mean: f64 = f_a.iter().sum::<f64>() / n_base as f64;
                let f_var: f64 = f_a.iter().map(|f| (f - f_mean).powi(2)).sum::<f64>() / n_base as f64;
                if f_var < 1e-15 {
                    json_ok(serde_json::json!({
                        "first_order": vec![0.0; d],
                        "total_order": vec![0.0; d],
                        "f_mean": f_mean,
                        "f_var": 0.0
                    }))
                } else {
                    let mut first_order = vec![0.0f64; d];
                    let mut total_order = vec![0.0f64; d];
                    for j in 0..d {
                        let f_abj = &f_ab[j];
                        let v_j: f64 = f_a.iter().zip(f_abj.iter())
                            .map(|(fa, fab)| fa * fab)
                            .sum::<f64>() / n_base as f64 - f_mean * f_mean;
                        let s_tj: f64 = f_a.iter().zip(f_abj.iter())
                            .map(|(fa, fab)| (fa - fab).powi(2))
                            .sum::<f64>() / (2.0 * n_base as f64) / f_var;
                        first_order[j] = (v_j / f_var).max(0.0);
                        total_order[j] = s_tj.max(0.0);
                    }
                    json_ok(serde_json::json!({
                        "first_order": first_order,
                        "total_order": total_order,
                        "f_mean": f_mean,
                        "f_var": f_var
                    }))
                }
            }
        }

        // ── Tier 2: Bayesian Optimization ──

        "mc_gp_fit" => {
            let x_train: Vec<Vec<f64>> = params.get("x_train")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|row| row.as_array().map(|r| r.iter().filter_map(|v| v.as_f64()).collect())).collect())
                .unwrap_or_default();
            let y_train: Vec<f64> = params.get("y_train")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_f64()).collect())
                .unwrap_or_default();
            let length_scale = params.get("length_scale").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let sigma_f = params.get("sigma_f").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let sigma_n = params.get("sigma_n").and_then(|v| v.as_f64()).unwrap_or(1e-6);

            if x_train.is_empty() || y_train.is_empty() {
                json_error("x_train and y_train required")
            } else {
                let gp = mc_bayesian::GaussianProcess::fit(x_train, y_train, length_scale, sigma_f, sigma_n);
                let lml = gp.log_marginal_likelihood();
                json_ok(serde_json::json!({
                    "length_scale": gp.length_scale,
                    "sigma_f": gp.sigma_f,
                    "sigma_n": gp.sigma_n,
                    "log_marginal_likelihood": lml,
                    "n_train": gp.y_train.len()
                }))
            }
        }

        "mc_gp_predict" => {
            let x_train: Vec<Vec<f64>> = params.get("x_train")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|row| row.as_array().map(|r| r.iter().filter_map(|v| v.as_f64()).collect())).collect())
                .unwrap_or_default();
            let y_train: Vec<f64> = params.get("y_train")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_f64()).collect())
                .unwrap_or_default();
            let x_new: Vec<f64> = params.get("x_new")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_f64()).collect())
                .unwrap_or_default();
            let length_scale = params.get("length_scale").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let sigma_f = params.get("sigma_f").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let sigma_n = params.get("sigma_n").and_then(|v| v.as_f64()).unwrap_or(1e-6);

            if x_train.is_empty() || x_new.is_empty() {
                json_error("x_train, y_train, and x_new required")
            } else {
                let gp = mc_bayesian::GaussianProcess::fit(x_train, y_train, length_scale, sigma_f, sigma_n);
                let (mean, variance) = gp.predict(&x_new);
                json_ok(serde_json::json!({
                    "mean": mean,
                    "variance": variance,
                    "std_dev": variance.sqrt()
                }))
            }
        }

        "mc_bayesian_optimize" => {
            let initial_x: Vec<Vec<f64>> = params.get("initial_x")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|row| row.as_array().map(|r| r.iter().filter_map(|v| v.as_f64()).collect())).collect())
                .unwrap_or_default();
            let initial_y: Vec<f64> = params.get("initial_y")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|v| v.as_f64()).collect())
                .unwrap_or_default();
            let param_ranges: Vec<(f64, f64)> = params.get("param_ranges")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|r| {
                    let a = r.as_array()?;
                    Some((a.first()?.as_f64()?, a.get(1)?.as_f64()?))
                }).collect())
                .unwrap_or_default();
            let n_iterations = params.get("n_iterations").and_then(|v| v.as_i64()).unwrap_or(10) as usize;
            let n_candidates = params.get("n_candidates").and_then(|v| v.as_i64()).unwrap_or(50) as usize;
            let sigma_n = params.get("sigma_n").and_then(|v| v.as_f64()).unwrap_or(1e-4);
            let xi = params.get("xi").and_then(|v| v.as_f64()).unwrap_or(0.01);
            let seed = params.get("seed").and_then(|v| v.as_i64()).unwrap_or(42) as u64;
            let fitness_str = params.get("fitness_expr").and_then(|v| v.as_str()).unwrap_or("x[0]");

            if initial_x.is_empty() || param_ranges.is_empty() {
                json_error("initial_x, initial_y, param_ranges, and fitness_expr required")
            } else {
                // Parse fitness expression: supports "x[0]", "x[0]+x[1]", "x[0]*x[1]", etc.
                let fitness_fn = move |x: &[f64]| -> f64 {
                    match fitness_str {
                        "x[0]" => x[0],
                        "x[0]+x[1]" => x[0] + x[1],
                        "x[0]*x[1]" => x[0] * x[1],
                        "sphere" => -(x.iter().map(|xi| xi * xi).sum::<f64>()),
                        "rosenbrock" => {
                            let mut s = 0.0;
                            for i in 0..x.len()-1 {
                                s += (1.0 - x[i]).powi(2) + 100.0 * (x[i+1] - x[i].powi(2)).powi(2);
                            }
                            -s
                        }
                        _ => x[0],
                    }
                };

                let (best_x, best_y, convergence, all_x, all_y) = mc_bayesian::bayesian_optimize(
                    initial_x, initial_y, &param_ranges, fitness_fn,
                    n_iterations, n_candidates, sigma_n, xi, seed,
                );

                json_ok(serde_json::json!({
                    "best_x": best_x,
                    "best_y": best_y,
                    "convergence": convergence,
                    "n_evaluations": all_x.len(),
                    "all_x": all_x,
                    "all_y": all_y
                }))
            }
        }

        // ── Tier 3: Rare Event Simulation ──

        "mc_subset_simulation" => {
            let dim = params.get("dim").and_then(|v| v.as_i64()).unwrap_or(1) as usize;
            let n_samples = params.get("n_samples").and_then(|v| v.as_i64()).unwrap_or(500) as usize;
            let target_pf = params.get("target_pf").and_then(|v| v.as_f64()).unwrap_or(1e-4);
            let seed = params.get("seed").and_then(|v| v.as_i64()).unwrap_or(42) as u64;
            let threshold = params.get("threshold").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let g_expr = params.get("g_expr").and_then(|v| v.as_str()).unwrap_or("threshold - x[0]");

            let g_fn = move |x: &[f64]| -> f64 {
                match g_expr {
                    "threshold - x[0]" => threshold - x[0],
                    "threshold - sum_abs" => threshold - x.iter().map(|xi| xi.abs()).sum::<f64>(),
                    "threshold - sum_sq" => threshold - x.iter().map(|xi| xi * xi).sum::<f64>(),
                    _ => threshold - x[0],
                }
            };

            let (pf, cov, levels) = mc_rare_event::subset_simulation(dim, n_samples, target_pf, g_fn, seed);
            json_ok(serde_json::json!({
                "probability": pf,
                "coefficient_of_variation": cov,
                "levels": levels
            }))
        }

        "mc_multilevel_splitting" => {
            let dim = params.get("dim").and_then(|v| v.as_i64()).unwrap_or(1) as usize;
            let n_samples = params.get("n_samples").and_then(|v| v.as_i64()).unwrap_or(500) as usize;
            let survival_fraction = params.get("survival_fraction").and_then(|v| v.as_f64()).unwrap_or(0.1);
            let seed = params.get("seed").and_then(|v| v.as_i64()).unwrap_or(42) as u64;
            let threshold = params.get("threshold").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let g_expr = params.get("g_expr").and_then(|v| v.as_str()).unwrap_or("threshold - x[0]");

            let g_fn = move |x: &[f64]| -> f64 {
                match g_expr {
                    "threshold - x[0]" => threshold - x[0],
                    "threshold - sum_abs" => threshold - x.iter().map(|xi| xi.abs()).sum::<f64>(),
                    "threshold - sum_sq" => threshold - x.iter().map(|xi| xi * xi).sum::<f64>(),
                    _ => threshold - x[0],
                }
            };

            let (prob, thresholds, levels) = mc_rare_event::multilevel_splitting(dim, n_samples, survival_fraction, g_fn, seed);
            json_ok(serde_json::json!({
                "probability": prob,
                "thresholds": thresholds,
                "levels": levels
            }))
        }

        "mc_importance_sampling_rare" => {
            let dim = params.get("dim").and_then(|v| v.as_i64()).unwrap_or(1) as usize;
            let n_samples = params.get("n_samples").and_then(|v| v.as_i64()).unwrap_or(2000) as usize;
            let pilot_n = params.get("pilot_n").and_then(|v| v.as_i64()).unwrap_or(500) as usize;
            let seed = params.get("seed").and_then(|v| v.as_i64()).unwrap_or(42) as u64;
            let threshold = params.get("threshold").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let g_expr = params.get("g_expr").and_then(|v| v.as_str()).unwrap_or("threshold - x[0]");

            let g_fn = move |x: &[f64]| -> f64 {
                match g_expr {
                    "threshold - x[0]" => threshold - x[0],
                    "threshold - sum_abs" => threshold - x.iter().map(|xi| xi.abs()).sum::<f64>(),
                    "threshold - sum_sq" => threshold - x.iter().map(|xi| xi * xi).sum::<f64>(),
                    _ => threshold - x[0],
                }
            };

            let (pf, shifted_mean, ess) = mc_rare_event::importance_sampling_rare(dim, n_samples, g_fn, pilot_n, seed);
            json_ok(serde_json::json!({
                "probability": pf,
                "shifted_mean": shifted_mean,
                "effective_sample_size": ess
            }))
        }

        // ── Tier 4: SDE Solvers ──

        "mc_sde_euler" => {
            let x0 = params.get("x0").and_then(|v| v.as_f64()).unwrap_or(100.0);
            let t0 = params.get("t0").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let t_end = params.get("t_end").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let n_steps = params.get("n_steps").and_then(|v| v.as_i64()).unwrap_or(100) as usize;
            let seed = params.get("seed").and_then(|v| v.as_i64()).unwrap_or(42) as u64;
            let drift_type = params.get("drift_type").and_then(|v| v.as_str()).unwrap_or("gbm");
            let mu = params.get("mu").and_then(|v| v.as_f64()).unwrap_or(0.05);
            let sigma = params.get("sigma").and_then(|v| v.as_f64()).unwrap_or(0.2);

            let sde = build_sde(drift_type, mu, sigma);
            let path = mc_sde::euler_maruyama(&sde, x0, t0, t_end, n_steps, seed);
            let final_val = path.last().map(|(_, x)| *x).unwrap_or(x0);
            json_ok(serde_json::json!({
                "final_value": final_val,
                "n_steps": n_steps,
                "path_length": path.len()
            }))
        }

        "mc_sde_milstein" => {
            let x0 = params.get("x0").and_then(|v| v.as_f64()).unwrap_or(100.0);
            let t0 = params.get("t0").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let t_end = params.get("t_end").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let n_steps = params.get("n_steps").and_then(|v| v.as_i64()).unwrap_or(100) as usize;
            let seed = params.get("seed").and_then(|v| v.as_i64()).unwrap_or(42) as u64;
            let drift_type = params.get("drift_type").and_then(|v| v.as_str()).unwrap_or("gbm");
            let mu = params.get("mu").and_then(|v| v.as_f64()).unwrap_or(0.05);
            let sigma = params.get("sigma").and_then(|v| v.as_f64()).unwrap_or(0.2);

            let sde = build_sde(drift_type, mu, sigma);
            let path = mc_sde::milstein(&sde, x0, t0, t_end, n_steps, seed);
            let final_val = path.last().map(|(_, x)| *x).unwrap_or(x0);
            json_ok(serde_json::json!({
                "final_value": final_val,
                "n_steps": n_steps,
                "path_length": path.len()
            }))
        }

        "mc_sde_parallel_euler" => {
            let x0 = params.get("x0").and_then(|v| v.as_f64()).unwrap_or(100.0);
            let t0 = params.get("t0").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let t_end = params.get("t_end").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let n_steps = params.get("n_steps").and_then(|v| v.as_i64()).unwrap_or(100) as usize;
            let n_paths = params.get("n_paths").and_then(|v| v.as_i64()).unwrap_or(1000) as usize;
            let seed = params.get("seed").and_then(|v| v.as_i64()).unwrap_or(42) as u64;
            let drift_type = params.get("drift_type").and_then(|v| v.as_str()).unwrap_or("gbm");
            let mu = params.get("mu").and_then(|v| v.as_f64()).unwrap_or(0.05);
            let sigma = params.get("sigma").and_then(|v| v.as_f64()).unwrap_or(0.2);

            let sde = build_sde(drift_type, mu, sigma);
            let finals = mc_sde::parallel_euler_maruyama(&sde, x0, t0, t_end, n_steps, n_paths, seed);
            let (mean, var, std_dev, ci) = mc_sde::path_statistics(&finals);
            json_ok(serde_json::json!({
                "mean": mean,
                "variance": var,
                "std_dev": std_dev,
                "ci_95": ci,
                "n_paths": n_paths
            }))
        }

        "mc_sde_parallel_milstein" => {
            let x0 = params.get("x0").and_then(|v| v.as_f64()).unwrap_or(100.0);
            let t0 = params.get("t0").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let t_end = params.get("t_end").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let n_steps = params.get("n_steps").and_then(|v| v.as_i64()).unwrap_or(100) as usize;
            let n_paths = params.get("n_paths").and_then(|v| v.as_i64()).unwrap_or(1000) as usize;
            let seed = params.get("seed").and_then(|v| v.as_i64()).unwrap_or(42) as u64;
            let drift_type = params.get("drift_type").and_then(|v| v.as_str()).unwrap_or("gbm");
            let mu = params.get("mu").and_then(|v| v.as_f64()).unwrap_or(0.05);
            let sigma = params.get("sigma").and_then(|v| v.as_f64()).unwrap_or(0.2);

            let sde = build_sde(drift_type, mu, sigma);
            let finals = mc_sde::parallel_milstein(&sde, x0, t0, t_end, n_steps, n_paths, seed);
            let (mean, var, std_dev, ci) = mc_sde::path_statistics(&finals);
            json_ok(serde_json::json!({
                "mean": mean,
                "variance": var,
                "std_dev": std_dev,
                "ci_95": ci,
                "n_paths": n_paths
            }))
        }

        "mc_sde_mlmc" => {
            let x0 = params.get("x0").and_then(|v| v.as_f64()).unwrap_or(100.0);
            let t0 = params.get("t0").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let t_end = params.get("t_end").and_then(|v| v.as_f64()).unwrap_or(1.0);
            let n_levels = params.get("n_levels").and_then(|v| v.as_i64()).unwrap_or(3) as usize;
            let n_paths_fine = params.get("n_paths_fine").and_then(|v| v.as_i64()).unwrap_or(1000) as usize;
            let seed = params.get("seed").and_then(|v| v.as_i64()).unwrap_or(42) as u64;
            let drift_type = params.get("drift_type").and_then(|v| v.as_str()).unwrap_or("gbm");
            let mu = params.get("mu").and_then(|v| v.as_f64()).unwrap_or(0.05);
            let sigma = params.get("sigma").and_then(|v| v.as_f64()).unwrap_or(0.2);
            let payoff = params.get("payoff").and_then(|v| v.as_str()).unwrap_or("identity");

            let sde = build_sde(drift_type, mu, sigma);
            let payoff_fn = move |x: f64| -> f64 {
                match payoff {
                    "identity" => x,
                    "square" => x * x,
                    "heaviside" => if x > x0 { 1.0 } else { 0.0 },
                    _ => x,
                }
            };

            let (estimate, var, levels) = mc_sde::multilevel_monte_carlo(
                &sde, x0, t0, t_end, payoff_fn, n_levels, n_paths_fine, seed,
            );
            json_ok(serde_json::json!({
                "estimate": estimate,
                "variance": var,
                "levels": levels
            }))
        }

        _ => json_error(&format!("Unknown method: {}", method)),
    }
}

fn build_sde(drift_type: &str, _mu: f64, _sigma: f64) -> mc_sde::SDE {
    match drift_type {
        "ou" => mc_sde::SDE {
            drift: |_t, x: &[f64]| 1.0 * (0.0 - x[0]),
            diffusion: |_t, _x: &[f64]| 0.3,
            diffusion_deriv: |_t, _x: &[f64]| 0.0,
        },
        _ => mc_sde::SDE {
            // GBM with default mu=0.05, sigma=0.2
            drift: |_t, x: &[f64]| 0.05 * x[0],
            diffusion: |_t, x: &[f64]| 0.2 * x[0],
            diffusion_deriv: |_t, _x: &[f64]| 0.2,
        },
    }
}

fn parse_thermo_state(params: &serde_json::Value) -> ThermodynamicState {
    let mut state = ThermodynamicState::default();
    if let Some(t) = params.get("temperature").and_then(|v| v.as_f64()) {
        state.temperature = t;
    }
    if let Some(c) = params.get("cooling_rate").and_then(|v| v.as_f64()) {
        state.cooling_rate = c;
    }
    if let Some(r) = params.get("reheat_amount").and_then(|v| v.as_f64()) {
        state.reheat_amount = r;
    }
    if let Some(m) = params.get("min_temperature").and_then(|v| v.as_f64()) {
        state.min_temperature = m;
    }
    if let Some(m) = params.get("max_temperature").and_then(|v| v.as_f64()) {
        state.max_temperature = m;
    }
    if let Some(c) = params.get("cycle_count").and_then(|v| v.as_i64()) {
        state.cycle_count = c as i32;
    }
    state
}

fn json_ok(data: serde_json::Value) -> String {
    serde_json::json!({"status": "ok", "result": data}).to_string()
}

fn json_error(msg: &str) -> String {
    serde_json::json!({"status": "error", "error": msg}).to_string()
}
