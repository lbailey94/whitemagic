//! Rare-event probability estimation.
//!
//! Standard Monte Carlo needs ~1/p samples to estimate a probability p —
//! hopeless for p < 10⁻⁴. Two variance-reduction methods:
//!
//! - **Subset simulation** (Au & Beck 2001): iteratively condition on
//!   intermediate thresholds, each with ~10% failure probability, and
//!   generate conditional samples with a Metropolis random walk.
//!   `P(fail) = p₀ᵐ · P(g > t | level m)`.
//! - **Importance sampling**: sample from a proposal shifted toward the
//!   failure region and re-weight with the likelihood ratio.
//!
//! The limit-state function `g(x)` (failure when `g(x) > threshold`) is
//! passed as a closure; inputs `x` are standard normal i.i.d. vectors of
//! dimension `dim`.

use crate::bayesian::rand_u01;

/// Draw a standard normal via Box–Muller from the SplitMix64 state.
fn randn(state: &mut u64) -> f64 {
    let u1 = rand_u01(state).max(1e-12);
    let u2 = rand_u01(state).max(1e-12);
    (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos()
}

/// Standard normal PDF.
fn phi(x: f64) -> f64 {
    (-0.5 * x * x).exp() / (2.0 * std::f64::consts::PI).sqrt()
}

/// Estimate a rare-event probability with subset simulation.
///
/// `n_per_level` samples per intermediate level, `n_levels` intermediate
/// levels, `seed` for the SplitMix64 PRNG. The Metropolis proposal uses a
/// Gaussian step with `proposal_std` (default 1.0 — in the same units as
/// the standard-normal inputs).
#[allow(clippy::too_many_arguments)]
pub fn subset_simulation<G>(
    dim: usize,
    n_per_level: usize,
    n_levels: usize,
    threshold: f64,
    g: G,
    seed: u64,
    proposal_std: f64,
) -> SubsetResult
where
    G: Fn(&[f64]) -> f64,
{
    let mut rng = seed;
    let p0 = 0.1_f64; // probability of staying in the next level

    let mut samples: Vec<Vec<f64>> = (0..n_per_level)
        .map(|_| (0..dim).map(|_| randn(&mut rng)).collect())
        .collect();
    let mut g_values: Vec<f64> = samples.iter().map(|s| g(s)).collect();

    let mut level = 0usize;

    while level < n_levels {
        // Current level threshold: the p0-quantile of g values
        let mut sorted = g_values.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let idx = ((n_per_level as f64) * (1.0 - p0)) as usize;
        let level_threshold = sorted[idx.min(n_per_level - 1)];

        if level_threshold >= threshold {
            // Already past the target — the current population is
            // conditional on the previous level
            break;
        }

        // Keep the top-p0 samples as seeds for the next level
        let mut seeds: Vec<(Vec<f64>, f64)> = Vec::with_capacity(n_per_level);
        for (s, gv) in samples.iter().zip(g_values.iter()) {
            if *gv >= level_threshold {
                seeds.push((s.clone(), *gv));
            }
        }
        // Seed with the largest values if quantile boundary is fuzzy
        if seeds.is_empty() {
            let mut pairs: Vec<(Vec<f64>, f64)> = samples.into_iter().zip(g_values).collect();
            pairs.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
            seeds = pairs.into_iter().take(n_per_level.max(1)).collect();
        }

        // Metropolis-Hastings: generate a fresh population conditional on
        // g >= level_threshold. Target ∝ φ(x)·1[g(x) ≥ b]; with a symmetric
        // Gaussian proposal the acceptance ratio is min(1, φ(x')/φ(x)) for
        // trials inside the level (trials below it are rejected).
        let mut next: Vec<Vec<f64>> = Vec::with_capacity(n_per_level);
        let mut next_g: Vec<f64> = Vec::with_capacity(n_per_level);
        let n_seeds = seeds.len();
        for i in 0..n_per_level {
            let seed_sample = seeds[i % n_seeds].0.clone();
            let mut candidate = seed_sample.clone();
            let mut candidate_density = density(candidate.iter().copied());
            let mut accepted = false;
            for _ in 0..500 {
                let mut trial = candidate.clone();
                for v in &mut trial {
                    *v += proposal_std * randn(&mut rng);
                }
                let g_trial = g(&trial);
                if g_trial < level_threshold {
                    continue;
                }
                let trial_density = density(trial.iter().copied());
                let ratio = (trial_density / candidate_density).min(1.0);
                if rand_u01(&mut rng) < ratio {
                    candidate = trial;
                    candidate_density = trial_density;
                    accepted = true;
                    break;
                }
            }
            let gv = if accepted {
                g(&candidate)
            } else {
                seeds[i % n_seeds].1
            };
            next_g.push(gv);
            next.push(candidate);
        }
        samples = next;
        g_values = next_g;
        level += 1;
    }

    // P(fail) = p0^level · P(g > threshold | current level)
    let fail = g_values.iter().filter(|&&v| v >= threshold).count();
    let conditional = fail as f64 / g_values.len().max(1) as f64;
    let probability = p0.powf(level as f64) * conditional;

    SubsetResult {
        probability,
        levels_used: level,
        n_samples_total: n_per_level * (level + 1),
        method: "subset".into(),
    }
}

/// Estimate a rare-event probability with importance sampling.
///
/// The proposal is `N(δ, I)` with `δ` proportional to the dimension and
/// threshold (a crude but robust shift); weights are the exact likelihood
/// ratio `φ(x)/φ(x − δ)`.
pub fn importance_sampling<G>(
    dim: usize,
    n_samples: usize,
    threshold: f64,
    g: G,
    seed: u64,
) -> ImportanceResult
where
    G: Fn(&[f64]) -> f64,
{
    let mut rng = seed;
    // Shift magnitude: ~threshold / sqrt(dim) toward the failure region.
    // For g(x) = ||x||² (chi-square) the failure region is a shell at
    // radius sqrt(threshold), so shifting the mean to radius
    // 0.5·sqrt(threshold) covers it well.
    let shift = 0.5 * threshold.sqrt().min(8.0) / dim.max(1) as f64;

    let mut count = 0usize;
    let mut weight_sum = 0.0_f64;
    for _ in 0..n_samples {
        let x: Vec<f64> = (0..dim).map(|_| randn(&mut rng) + shift).collect();
        let w = likelihood_ratio(&x, shift);
        if g(&x) >= threshold {
            count += 1;
            weight_sum += w;
        }
    }
    // Unbiased estimate: mean of 1[g≥t]·w, with coefficient of variation
    let mean = weight_sum / n_samples.max(1) as f64;
    let cv = if mean > 1e-300 {
        // approximate std via the indicator variance of the weighted mean
        (count as f64).sqrt() / n_samples.max(1) as f64 / mean.max(1e-300)
    } else {
        0.0
    };
    ImportanceResult {
        probability: mean,
        coefficient_of_variation: cv,
        hits: count,
        n_samples,
        method: "importance".into(),
    }
}

/// Likelihood ratio between N(0, I) and N(shift, I).
fn likelihood_ratio(x: &[f64], shift: f64) -> f64 {
    let mut lr = 1.0_f64;
    for &xi in x {
        // φ(x)/φ(x-δ) = exp(-0.5 x² + 0.5 (x-δ)²) = exp(-xδ + 0.5δ²)
        lr *= (-xi).mul_add(shift, 0.5 * shift * shift).exp();
    }
    lr
}

/// Standard normal density of a vector (log-form product of φ).
fn density(x: impl Iterator<Item = f64>) -> f64 {
    x.map(phi).product()
}

/// Result of a subset simulation run.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SubsetResult {
    /// Estimated failure probability P(g(X) > threshold).
    pub probability: f64,
    /// Intermediate levels actually used.
    pub levels_used: usize,
    /// Total samples consumed.
    pub n_samples_total: usize,
    /// Estimation method.
    pub method: String,
}

/// Result of an importance sampling run.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ImportanceResult {
    /// Estimated failure probability.
    pub probability: f64,
    /// Approximate coefficient of variation of the estimate.
    pub coefficient_of_variation: f64,
    /// Raw hits of the indicator.
    pub hits: usize,
    /// Samples consumed.
    pub n_samples: usize,
    /// Estimation method.
    pub method: String,
}

#[cfg(test)]
mod tests {
    #![allow(clippy::suboptimal_flops)] // test data expressions, not hot paths
    use super::*;

    /// Analytic test: P(||X||² > 9) for X ~ N(0, I) in dim 2.
    /// Chi-square(2): P(χ²₂ > 9) = exp(-9/2) ≈ 0.0111.
    #[test]
    fn subset_matches_chi_square_tail() {
        let result = subset_simulation(
            2,
            2000,
            3,
            9.0,
            |x: &[f64]| x[0] * x[0] + x[1] * x[1],
            42,
            1.0,
        );
        assert!(
            (result.probability - 0.0111).abs() < 0.01,
            "subset: {} (expected ~0.0111)",
            result.probability
        );
        assert!(result.levels_used >= 1);
    }

    #[test]
    fn importance_matches_chi_square_tail() {
        let result = importance_sampling(2, 50_000, 9.0, |x: &[f64]| x[0] * x[0] + x[1] * x[1], 7);
        assert!(
            (result.probability - 0.0111).abs() < 0.01,
            "importance: {} (expected ~0.0111)",
            result.probability
        );
    }

    #[test]
    fn subset_common_event_is_close() {
        // P(χ²₂ > 4) = exp(-2) ≈ 0.135
        let result = subset_simulation(
            2,
            2000,
            2,
            4.0,
            |x: &[f64]| x[0] * x[0] + x[1] * x[1],
            123,
            1.0,
        );
        assert!(
            (result.probability - 0.1353).abs() < 0.05,
            "subset: {} (expected ~0.135)",
            result.probability
        );
    }

    #[test]
    fn importance_rejects_no_hits_gracefully() {
        // Threshold far beyond reach — estimate ~0, no panic
        let result = importance_sampling(2, 1000, 1e9, |x: &[f64]| x[0] * x[0] + x[1] * x[1], 1);
        assert!(result.probability < 1e-3);
        assert_eq!(result.hits, 0);
    }

    #[test]
    fn subset_always_exceeded_is_one() {
        // g = ||x||² ≥ 0 always → threshold below 0 → P = 1
        let result = subset_simulation(
            2,
            500,
            1,
            -1.0,
            |x: &[f64]| x[0] * x[0] + x[1] * x[1],
            9,
            1.0,
        );
        assert!(result.probability > 0.99);
    }
}
