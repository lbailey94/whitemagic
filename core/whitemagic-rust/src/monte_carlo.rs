//! Monte Carlo Forecasting Calibration Engine — Sprint F
//!
//! Runs N parallel Rayon trials sampling from Beta distributions fitted over
//! each claim's confidence value, producing calibration confidence intervals
//! and expected lead-time distributions for the `TemporalForecastDB`.
//!
//! The old 28-line similarity stub is preserved as `MonteCarloEngine` for
//! backward compatibility; the new engine is `MonteCarloForecast`.
//!
//! Python API:
//!   `run_mc_forecast_calibration(claims_json, n_trials) -> str` (JSON result)
//!   `MonteCarloForecast`  (class with `.run(claims_json, n_trials)`)

use pyo3::prelude::*;
use rayon::prelude::*;
use rand::rngs::SmallRng;
use rand::{Rng, SeedableRng};
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// Backward-compat stub (kept for any existing callers)
// ---------------------------------------------------------------------------

pub struct MonteCarloEngine {
    dimensions: usize,
    sample_size: usize,
}

impl MonteCarloEngine {
    pub fn new(dimensions: usize, sample_size: usize) -> Self {
        MonteCarloEngine { dimensions, sample_size }
    }

    pub fn approximate_similarity(&self, v1: &[f32], v2: &[f32]) -> f32 {
        let step = (self.dimensions / self.sample_size).max(1);
        let mut sim = 0.0f32;
        let mut i = 0;
        while i < self.dimensions && i < v1.len() && i < v2.len() {
            sim += v1[i] * v2[i];
            i += step;
        }
        sim
    }
}

// ---------------------------------------------------------------------------
// Input / output types
// ---------------------------------------------------------------------------

/// A single forecast claim as passed from TemporalForecastDB.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ForecastClaim {
    /// Claim identifier.
    pub id: String,
    /// Forecasted probability in [0, 1].
    pub confidence: f64,
    /// Observed outcome: 1.0 = validated, 0.0 = falsified, None = pending.
    pub outcome: Option<f64>,
    /// Observed lead time in weeks (None if still pending).
    pub lead_weeks: Option<f64>,
}

/// Percentile summary over N Monte Carlo trials.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct PercentileSummary {
    #[pyo3(get)] pub mean: f64,
    #[pyo3(get)] pub p5: f64,
    #[pyo3(get)] pub p25: f64,
    #[pyo3(get)] pub p50: f64,
    #[pyo3(get)] pub p75: f64,
    #[pyo3(get)] pub p95: f64,
    #[pyo3(get)] pub std_dev: f64,
}

/// Full result of a Monte Carlo calibration run.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct MonteCarloResult {
    /// Number of trials run.
    #[pyo3(get)] pub n_trials: usize,
    /// Number of claims fed in.
    #[pyo3(get)] pub n_claims: usize,
    /// Brier score distribution across trials.
    #[pyo3(get)] pub brier_score: PercentileSummary,
    /// Brier Skill Score distribution (vs 0.25 uninformed baseline).
    #[pyo3(get)] pub brier_skill_score: PercentileSummary,
    /// Expected lead time in weeks distribution (validated claims only).
    #[pyo3(get)] pub lead_weeks: PercentileSummary,
    /// Fraction of trials where BSS > 0 (i.e. better than random).
    #[pyo3(get)] pub prob_better_than_random: f64,
    /// Fraction of trials where BSS > 0.5 (i.e. strongly calibrated).
    #[pyo3(get)] pub prob_strongly_calibrated: f64,
}

#[pymethods]
impl MonteCarloResult {
    fn __repr__(&self) -> String {
        format!(
            "MonteCarloResult(trials={}, claims={}, brier_mean={:.4}, bss_mean={:.4}, \
             p_better_than_random={:.3})",
            self.n_trials, self.n_claims,
            self.brier_score.mean, self.brier_skill_score.mean,
            self.prob_better_than_random
        )
    }
}

// ---------------------------------------------------------------------------
// Beta distribution sampling
// ---------------------------------------------------------------------------

/// Sample from Beta(α, β) using the Johnk method.
/// α = confidence * precision, β = (1 - confidence) * precision
/// precision = 10 (moderate; higher = tighter posterior)
fn sample_beta(rng: &mut SmallRng, mean: f64, precision: f64) -> f64 {
    let alpha = (mean * precision).max(0.5);
    let beta = ((1.0 - mean) * precision).max(0.5);

    // Use the Gamma approximation: Beta(a,b) = Ga / (Ga + Gb)
    // We approximate via the Wilson-Hilferty cube-root normal transform
    // for speed (exact enough for calibration purposes).
    let ga = sample_gamma(rng, alpha);
    let gb = sample_gamma(rng, beta);
    if ga + gb < f64::EPSILON { return mean; }
    (ga / (ga + gb)).clamp(0.0, 1.0)
}

/// Marsaglia-Tsang fast Gamma sampler (shape k, scale 1).
fn sample_gamma(rng: &mut SmallRng, shape: f64) -> f64 {
    if shape < 1.0 {
        return sample_gamma(rng, shape + 1.0) * rng.gen::<f64>().powf(1.0 / shape);
    }
    let d = shape - 1.0 / 3.0;
    let c = 1.0 / (9.0 * d).sqrt();
    loop {
        let x: f64 = loop {
            let u: f64 = rng.gen();
            // Box-Muller normal
            let v: f64 = rng.gen();
            let z = (-2.0 * u.ln()).sqrt() * (2.0 * std::f64::consts::PI * v).cos();
            if z > -1.0 / c { break z; }
        };
        let v = (1.0 + c * x).powi(3);
        let u: f64 = rng.gen();
        if u < 1.0 - 0.0331 * x.powi(4) {
            return d * v;
        }
        if u.ln() < 0.5 * x * x + d * (1.0 - v + v.ln()) {
            return d * v;
        }
    }
}

// ---------------------------------------------------------------------------
// Brier score helpers
// ---------------------------------------------------------------------------

fn brier_score_from_pairs(pairs: &[(f64, f64)]) -> f64 {
    if pairs.is_empty() { return 0.25; }
    pairs.iter().map(|(p, o)| (p - o).powi(2)).sum::<f64>() / pairs.len() as f64
}

fn brier_skill_score(bs: f64) -> f64 {
    1.0 - bs / 0.25
}

// ---------------------------------------------------------------------------
// Percentile computation
// ---------------------------------------------------------------------------

fn percentile_summary(mut values: Vec<f64>) -> PercentileSummary {
    if values.is_empty() {
        return PercentileSummary { mean: 0.0, p5: 0.0, p25: 0.0, p50: 0.0, p75: 0.0, p95: 0.0, std_dev: 0.0 };
    }
    values.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let n = values.len();
    let mean = values.iter().sum::<f64>() / n as f64;
    let variance: f64 = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n as f64;

    let pct = |p: f64| -> f64 {
        let idx = ((p / 100.0) * (n - 1) as f64) as usize;
        values[idx.min(n - 1)]
    };

    PercentileSummary {
        mean,
        p5: pct(5.0),
        p25: pct(25.0),
        p50: pct(50.0),
        p75: pct(75.0),
        p95: pct(95.0),
        std_dev: variance.sqrt(),
    }
}

// ---------------------------------------------------------------------------
// Core engine
// ---------------------------------------------------------------------------

/// Run N Monte Carlo trials over `claims`, sampling each confidence from its
/// Beta posterior.  Returns a `MonteCarloResult` with percentile distributions.
///
/// Phase 1d: Claim-specific Beta precision — claims with more evidence (higher
/// confidence, resolved outcome) get tighter posteriors; speculative claims
/// get wider posteriors.
/// Phase 1e: Stratified lead-time noise — sigma scales with lead weeks.
fn run_trials(claims: &[ForecastClaim], n_trials: usize) -> MonteCarloResult {
    // For each trial we need an independent RNG seed
    let seeds: Vec<u64> = (0..n_trials as u64).collect();

    // Each trial returns (brier_score, bss, mean_lead_weeks)
    let trial_results: Vec<(f64, f64, Option<f64>)> = seeds
        .par_iter()
        .map(|&seed| {
            let mut rng = SmallRng::seed_from_u64(seed ^ 0xDEAD_BEEF_1234_5678);

            // Build sampled (probability, outcome) pairs for resolved claims
            let pairs: Vec<(f64, f64)> = claims
                .iter()
                .filter_map(|c| {
                    c.outcome.map(|o| {
                        // Phase 1d: Claim-specific precision
                        // Resolved claims with high confidence → tighter (higher precision)
                        // Speculative claims (low confidence) → wider (lower precision)
                        let precision = claim_precision(c);
                        (sample_beta(&mut rng, c.confidence, precision), o)
                    })
                })
                .collect();

            let bs = brier_score_from_pairs(&pairs);
            let bss = brier_skill_score(bs);

            // Lead weeks: sample from Normal(μ, σ) where σ scales with lead weeks
            let lead: Option<f64> = {
                let lead_values: Vec<f64> = claims
                    .iter()
                    .filter_map(|c| c.lead_weeks)
                    .map(|lw| {
                        // Phase 1e: Stratified lead-time noise
                        // sigma = max(1.0, lead_weeks * 0.15)
                        // Short predictions (5 weeks) → σ=1.0 (tight)
                        // Long predictions (50 weeks) → σ=7.5 (wide)
                        let sigma = (1.0_f64).max(lw * 0.15);
                        let noise: f64 = rng.gen_range(-sigma..sigma);
                        (lw + noise).max(0.0)
                    })
                    .collect();
                if lead_values.is_empty() {
                    None
                } else {
                    Some(lead_values.iter().sum::<f64>() / lead_values.len() as f64)
                }
            };

            (bs, bss, lead)
        })
        .collect();

    let brier_scores: Vec<f64> = trial_results.iter().map(|r| r.0).collect();
    let bss_scores: Vec<f64> = trial_results.iter().map(|r| r.1).collect();
    let lead_vals: Vec<f64> = trial_results.iter().filter_map(|r| r.2).collect();

    let prob_better = bss_scores.iter().filter(|&&s| s > 0.0).count() as f64 / n_trials as f64;
    let prob_strong = bss_scores.iter().filter(|&&s| s > 0.5).count() as f64 / n_trials as f64;

    MonteCarloResult {
        n_trials,
        n_claims: claims.len(),
        brier_score: percentile_summary(brier_scores),
        brier_skill_score: percentile_summary(bss_scores),
        lead_weeks: percentile_summary(lead_vals),
        prob_better_than_random: prob_better,
        prob_strongly_calibrated: prob_strong,
    }
}

/// Phase 1d: Compute claim-specific Beta precision.
///
/// Resolved claims with high confidence get high precision (tight posteriors).
/// Pending/speculative claims get lower precision (wide posteriors).
///
/// - Resolved + confidence >= 0.8: precision = 20.0 (tight)
/// - Resolved + confidence >= 0.5: precision = 12.0 (moderate)
/// - Resolved + confidence < 0.5:  precision = 8.0  (wide)
/// - Pending (no outcome):         precision = 5.0  (widest)
fn claim_precision(claim: &ForecastClaim) -> f64 {
    match claim.outcome {
        Some(_) => {
            if claim.confidence >= 0.8 {
                20.0
            } else if claim.confidence >= 0.5 {
                12.0
            } else {
                8.0
            }
        }
        None => 5.0,
    }
}

// ---------------------------------------------------------------------------
// Python-facing class
// ---------------------------------------------------------------------------

/// Monte Carlo forecasting calibration engine.
///
/// Example:
///     from whitemagic_rust import MonteCarloForecast
///     mc = MonteCarloForecast(n_trials=10000)
///     result = mc.run(claims_json)
///     print(result.brier_skill_score.mean)
#[pyclass]
pub struct MonteCarloForecast {
    n_trials: usize,
}

#[pymethods]
impl MonteCarloForecast {
    #[new]
    #[pyo3(signature = (n_trials=10000))]
    fn new(n_trials: usize) -> Self {
        Self { n_trials }
    }

    /// Run calibration trials.
    ///
    /// Args:
    ///     claims_json: JSON array of claim objects with fields:
    ///                  id, confidence, outcome (0.0|1.0|null), lead_weeks (float|null)
    ///
    /// Returns:
    ///     MonteCarloResult with brier_score, brier_skill_score, lead_weeks distributions.
    fn run(&self, claims_json: &str) -> PyResult<MonteCarloResult> {
        let claims: Vec<ForecastClaim> = serde_json::from_str(claims_json).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON: {}", e))
        })?;
        Ok(run_trials(&claims, self.n_trials))
    }

    fn __repr__(&self) -> String {
        format!("MonteCarloForecast(n_trials={})", self.n_trials)
    }
}

// ---------------------------------------------------------------------------
// Standalone pyfunction (convenience wrapper)
// ---------------------------------------------------------------------------

/// Run Monte Carlo forecasting calibration from Python.
///
/// Args:
///     claims_json: JSON array of {id, confidence, outcome, lead_weeks}.
///     n_trials:    Number of parallel trials (default 10_000).
///
/// Returns:
///     JSON string with MonteCarloResult fields.
#[pyfunction]
#[pyo3(signature = (claims_json, n_trials=10000))]
pub fn run_mc_forecast_calibration(claims_json: &str, n_trials: usize) -> PyResult<String> {
    let claims: Vec<ForecastClaim> = serde_json::from_str(claims_json).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON: {}", e))
    })?;
    let result = run_trials(&claims, n_trials);
    serde_json::to_string(&result)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn well_calibrated_claims() -> Vec<ForecastClaim> {
        vec![
            ForecastClaim { id: "c1".into(), confidence: 0.9, outcome: Some(1.0), lead_weeks: Some(24.0) },
            ForecastClaim { id: "c2".into(), confidence: 0.8, outcome: Some(1.0), lead_weeks: Some(18.0) },
            ForecastClaim { id: "c3".into(), confidence: 0.7, outcome: Some(1.0), lead_weeks: Some(15.0) },
            ForecastClaim { id: "c4".into(), confidence: 0.6, outcome: Some(0.0), lead_weeks: None },
            ForecastClaim { id: "c5".into(), confidence: 0.5, outcome: Some(1.0), lead_weeks: Some(10.0) },
            ForecastClaim { id: "c6".into(), confidence: 0.85, outcome: Some(1.0), lead_weeks: Some(22.0) },
            ForecastClaim { id: "p1".into(), confidence: 0.7, outcome: None,      lead_weeks: None },
        ]
    }

    #[test]
    fn test_basic_run() {
        let claims = well_calibrated_claims();
        let result = run_trials(&claims, 500);
        assert_eq!(result.n_trials, 500);
        assert_eq!(result.n_claims, 7);
        assert!(result.brier_score.mean > 0.0);
        assert!(result.brier_score.mean < 1.0);
    }

    #[test]
    fn test_well_calibrated_positive_bss() {
        let claims = well_calibrated_claims();
        let result = run_trials(&claims, 1000);
        assert!(
            result.brier_skill_score.mean > 0.0,
            "Well-calibrated claims should have positive BSS, got {}",
            result.brier_skill_score.mean
        );
    }

    #[test]
    fn test_prob_better_than_random() {
        let claims = well_calibrated_claims();
        let result = run_trials(&claims, 1000);
        assert!(
            result.prob_better_than_random > 0.8,
            "Expected >80% of trials to beat random, got {}",
            result.prob_better_than_random
        );
    }

    #[test]
    fn test_lead_weeks_populated() {
        let claims = well_calibrated_claims();
        let result = run_trials(&claims, 500);
        assert!(result.lead_weeks.mean > 0.0, "Expected non-zero lead weeks mean");
        assert!(result.lead_weeks.p5 <= result.lead_weeks.p95);
    }

    #[test]
    fn test_poor_calibration_lower_bss() {
        let poor_claims = vec![
            ForecastClaim { id: "p1".into(), confidence: 0.9, outcome: Some(0.0), lead_weeks: None },
            ForecastClaim { id: "p2".into(), confidence: 0.8, outcome: Some(0.0), lead_weeks: None },
            ForecastClaim { id: "p3".into(), confidence: 0.7, outcome: Some(0.0), lead_weeks: None },
        ];
        let good_claims = well_calibrated_claims();
        let poor = run_trials(&poor_claims, 500);
        let good = run_trials(&good_claims, 500);
        assert!(
            good.brier_skill_score.mean > poor.brier_skill_score.mean,
            "Good calibration should beat poor: {} vs {}",
            good.brier_skill_score.mean,
            poor.brier_skill_score.mean
        );
    }

    #[test]
    fn test_empty_claims() {
        let result = run_trials(&[], 100);
        assert_eq!(result.n_claims, 0);
    }

    #[test]
    fn test_sample_beta_range() {
        let mut rng = SmallRng::seed_from_u64(42);
        for _ in 0..1000 {
            let s = sample_beta(&mut rng, 0.7, 10.0);
            assert!((0.0..=1.0).contains(&s), "Beta sample out of range: {}", s);
        }
    }

    #[test]
    fn test_percentile_ordering() {
        let values: Vec<f64> = (1..=100).map(|x| x as f64).collect();
        let s = percentile_summary(values);
        assert!(s.p5 <= s.p25);
        assert!(s.p25 <= s.p50);
        assert!(s.p50 <= s.p75);
        assert!(s.p75 <= s.p95);
    }

    #[test]
    fn test_claim_precision_resolved_high_confidence() {
        let claim = ForecastClaim {
            id: "c1".into(),
            confidence: 0.9,
            outcome: Some(1.0),
            lead_weeks: Some(10.0),
        };
        assert_eq!(claim_precision(&claim), 20.0);
    }

    #[test]
    fn test_claim_precision_resolved_moderate_confidence() {
        let claim = ForecastClaim {
            id: "c2".into(),
            confidence: 0.6,
            outcome: Some(1.0),
            lead_weeks: None,
        };
        assert_eq!(claim_precision(&claim), 12.0);
    }

    #[test]
    fn test_claim_precision_resolved_low_confidence() {
        let claim = ForecastClaim {
            id: "c3".into(),
            confidence: 0.3,
            outcome: Some(0.0),
            lead_weeks: None,
        };
        assert_eq!(claim_precision(&claim), 8.0);
    }

    #[test]
    fn test_claim_precision_pending() {
        let claim = ForecastClaim {
            id: "p1".into(),
            confidence: 0.7,
            outcome: None,
            lead_weeks: None,
        };
        assert_eq!(claim_precision(&claim), 5.0);
    }

    #[test]
    fn test_high_precision_tighter_distribution() {
        // High precision should produce tighter Beta distribution (lower variance)
        let mut rng = SmallRng::seed_from_u64(42);
        let mut high_prec_samples = Vec::new();
        let mut low_prec_samples = Vec::new();
        for _ in 0..2000 {
            high_prec_samples.push(sample_beta(&mut rng, 0.7, 20.0));
            low_prec_samples.push(sample_beta(&mut rng, 0.7, 5.0));
        }
        let hp_mean = high_prec_samples.iter().sum::<f64>() / high_prec_samples.len() as f64;
        let lp_mean = low_prec_samples.iter().sum::<f64>() / low_prec_samples.len() as f64;
        let hp_var = high_prec_samples.iter().map(|x| (x - hp_mean).powi(2)).sum::<f64>() / high_prec_samples.len() as f64;
        let lp_var = low_prec_samples.iter().map(|x| (x - lp_mean).powi(2)).sum::<f64>() / low_prec_samples.len() as f64;
        assert!(hp_var < lp_var, "High precision should have lower variance: {} vs {}", hp_var, lp_var);
    }

    #[test]
    fn test_stratified_lead_time_noise() {
        // Long lead times should produce wider lead_weeks distribution
        let short_claims = vec![
            ForecastClaim { id: "s1".into(), confidence: 0.8, outcome: Some(1.0), lead_weeks: Some(5.0) },
            ForecastClaim { id: "s2".into(), confidence: 0.8, outcome: Some(1.0), lead_weeks: Some(5.0) },
        ];
        let long_claims = vec![
            ForecastClaim { id: "l1".into(), confidence: 0.8, outcome: Some(1.0), lead_weeks: Some(50.0) },
            ForecastClaim { id: "l2".into(), confidence: 0.8, outcome: Some(1.0), lead_weeks: Some(50.0) },
        ];
        let short_result = run_trials(&short_claims, 1000);
        let long_result = run_trials(&long_claims, 1000);
        // Long lead times should have wider spread (p95 - p5)
        let short_spread = short_result.lead_weeks.p95 - short_result.lead_weeks.p5;
        let long_spread = long_result.lead_weeks.p95 - long_result.lead_weeks.p5;
        assert!(
            long_spread > short_spread,
            "Long lead times should have wider spread: {} vs {}",
            long_spread, short_spread
        );
    }
}
