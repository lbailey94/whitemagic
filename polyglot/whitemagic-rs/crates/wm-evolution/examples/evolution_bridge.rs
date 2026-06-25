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
    mc_integration,
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

        _ => json_error(&format!("Unknown method: {}", method)),
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
