//! Advanced Monte Carlo methods for high-dimensional possibility space exploration.
//!
//! Implements:
//! - Xoshiro256** PRNG (passes Big Crush, designed for MC)
//! - Multi-dimensional Gaussian sampling via Cholesky decomposition
//! - Latin Hypercube Sampling (LHS) for space-filling designs
//! - Parallel trial execution via Rayon
//! - Sobol QMC extended beyond 8 dimensions

use rand::{RngCore, SeedableRng};
use rand_xoshiro::Xoshiro256PlusPlus;
use rayon::prelude::*;

/// Sample from a multivariate Gaussian N(mean, cov) using Cholesky decomposition.
///
/// `mean` is a length-d vector, `cov` is a d×d covariance matrix (row-major).
/// Returns n_samples rows of d-dimensional samples.
pub fn multid_gaussian(
    n_samples: usize,
    mean: &[f64],
    cov: &[f64],
    seed: u64,
) -> Vec<Vec<f64>> {
    let d = mean.len();
    if d == 0 || n_samples == 0 {
        return Vec::new();
    }
    assert_eq!(cov.len(), d * d, "cov must be d×d (row-major)");

    // Cholesky decomposition: L such that L*L^T = cov
    let l = cholesky(cov, d);

    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);
    let mut samples = Vec::with_capacity(n_samples);

    for _ in 0..n_samples {
        // Generate d independent standard normals via Box-Muller
        let mut z = vec![0.0f64; d];
        for i in (0..d).step_by(2) {
            let u1: f64 = rng.next_u64() as f64 / u64::MAX as f64;
            let u2: f64 = rng.next_u64() as f64 / u64::MAX as f64;
            let u1 = u1.max(1e-15);
            let r = (-2.0_f64 * u1.ln()).sqrt();
            let theta = 2.0 * std::f64::consts::PI * u2;
            z[i] = r * theta.cos();
            if i + 1 < d {
                z[i + 1] = r * theta.sin();
            }
        }

        // x = mean + L * z
        let mut x = vec![0.0f64; d];
        for i in 0..d {
            x[i] = mean[i];
            for j in 0..=i {
                x[i] += l[i * d + j] * z[j];
            }
        }
        samples.push(x);
    }

    samples
}

/// Cholesky decomposition of a symmetric positive-definite matrix.
/// Returns lower-triangular L such that L * L^T = A.
fn cholesky(a: &[f64], d: usize) -> Vec<f64> {
    let mut l = vec![0.0f64; d * d];
    for i in 0..d {
        for j in 0..=i {
            let mut sum = 0.0;
            for k in 0..j {
                sum += l[i * d + k] * l[j * d + k];
            }
            if i == j {
                let diag = a[i * d + i] - sum;
                l[i * d + j] = if diag > 0.0 { diag.sqrt() } else { 0.0 };
            } else {
                let denom = l[j * d + j];
                l[i * d + j] = if denom.abs() > 1e-15 {
                    (a[i * d + j] - sum) / denom
                } else {
                    0.0
                };
            }
        }
    }
    l
}

/// Generate a Latin Hypercube Sample of n points in d dimensions.
///
/// Each dimension is stratified into n equal-probability intervals,
/// and one sample is drawn from each interval per dimension.
/// The samples are then randomly permuted across dimensions to
/// ensure space-filling properties.
///
/// Returns an n×d matrix with values in [0, 1).
pub fn latin_hypercube(n: usize, d: usize, seed: u64) -> Vec<Vec<f64>> {
    if n == 0 || d == 0 {
        return Vec::new();
    }

    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);

    // For each dimension, generate n stratified values and permute
    let mut samples = vec![vec![0.0f64; d]; n];

    for dim in 0..d {
        // Generate stratified values: one in each interval [k/n, (k+1)/n)
        let mut strata: Vec<f64> = (0..n)
            .map(|k| {
                let u = rng.next_u64() as f64 / u64::MAX as f64;
                (k as f64 + u) / n as f64
            })
            .collect();

        // Shuffle the strata
        for i in (1..n).rev() {
            let j = (rng.next_u64() % (i as u64 + 1)) as usize;
            strata.swap(i, j);
        }

        for i in 0..n {
            samples[i][dim] = strata[i];
        }
    }

    samples
}

/// Run parallel MC trials with a user-provided fitness function.
///
/// Each trial samples from the multivariate Gaussian and applies the fitness
/// function. Trials are parallelized via Rayon.
///
/// Returns (mean, variance, n_completed, best_params, best_fitness).
pub fn parallel_trials(
    n_trials: usize,
    mean: &[f64],
    cov: &[f64],
    seed: u64,
    fitness_fn: impl Fn(&[f64]) -> f64 + Sync,
) -> (f64, f64, usize, Vec<f64>, f64) {
    if n_trials == 0 || mean.is_empty() {
        return (0.0, 0.0, 0, Vec::new(), f64::NEG_INFINITY);
    }

    // Generate all samples upfront (needed for reproducibility)
    let samples = multid_gaussian(n_trials, mean, cov, seed);

    // Evaluate fitness in parallel
    let results: Vec<(f64, Vec<f64>)> = samples
        .into_par_iter()
        .map(|s| {
            let f = fitness_fn(&s);
            (f, s)
        })
        .collect();

    let n = results.len();
    let sum: f64 = results.iter().map(|(f, _)| *f).sum();
    let mean_val = sum / n as f64;
    let variance = results
        .iter()
        .map(|(f, _)| (*f - mean_val).powi(2))
        .sum::<f64>()
        / n as f64;

    // Find best
    let (best_fitness, best_params) = results
        .into_iter()
        .max_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal))
        .unwrap_or((f64::NEG_INFINITY, Vec::new()));

    (mean_val, variance.max(0.0), n, best_params, best_fitness)
}

/// Run parallel MC trials with LHS sampling and a fitness function.
///
/// Uses Latin Hypercube Sampling for better space coverage, then evaluates
/// fitness in parallel. The parameter ranges are given as pairs of (lo, hi).
///
/// Returns (mean, variance, n_completed, best_params, best_fitness, all_samples, all_fitness).
pub fn lhs_parallel_trials(
    n_trials: usize,
    param_ranges: &[(f64, f64)],
    seed: u64,
    fitness_fn: impl Fn(&[f64]) -> f64 + Sync,
) -> LHSResult {
    let d = param_ranges.len();
    if n_trials == 0 || d == 0 {
        return LHSResult::default();
    }

    // Generate LHS samples in [0, 1)
    let unit_samples = latin_hypercube(n_trials, d, seed);

    // Scale to parameter ranges
    let scaled: Vec<Vec<f64>> = unit_samples
        .iter()
        .map(|s| {
            s.iter()
                .enumerate()
                .map(|(i, &v)| {
                    let (lo, hi) = param_ranges[i];
                    lo + v * (hi - lo)
                })
                .collect()
        })
        .collect();

    // Evaluate fitness in parallel
    let fitness: Vec<f64> = scaled
        .par_iter()
        .map(|s| fitness_fn(s))
        .collect();

    let n = fitness.len();
    let sum: f64 = fitness.iter().sum();
    let mean_val = sum / n as f64;
    let variance = fitness
        .iter()
        .map(|f| (*f - mean_val).powi(2))
        .sum::<f64>()
        / n as f64;

    // Find best
    let mut best_idx = 0;
    let mut best_fitness = fitness[0];
    for (i, &f) in fitness.iter().enumerate() {
        if f > best_fitness {
            best_fitness = f;
            best_idx = i;
        }
    }

    LHSResult {
        mean: mean_val,
        variance: variance.max(0.0),
        n_completed: n,
        best_params: scaled[best_idx].clone(),
        best_fitness,
        samples: scaled,
        fitness_values: fitness,
    }
}

/// Result of an LHS parallel trial run.
#[derive(Debug, Clone, Default)]
pub struct LHSResult {
    pub mean: f64,
    pub variance: f64,
    pub n_completed: usize,
    pub best_params: Vec<f64>,
    pub best_fitness: f64,
    pub samples: Vec<Vec<f64>>,
    pub fitness_values: Vec<f64>,
}

/// Compute statistics for a batch of fitness values.
/// Returns (mean, variance, min, max, p5, p25, p50, p75, p95).
pub fn compute_statistics(values: &[f64]) -> (f64, f64, f64, f64, f64, f64, f64, f64, f64) {
    if values.is_empty() {
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0);
    }

    let n = values.len() as f64;
    let mean = values.iter().sum::<f64>() / n;
    let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n;

    let mut sorted = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let min = sorted[0];
    let max = sorted[sorted.len() - 1];
    let p = |q: f64| -> f64 {
        let idx = ((q * (sorted.len() - 1) as f64).round() as usize).min(sorted.len() - 1);
        sorted[idx]
    };

    (mean, variance.max(0.0), min, max, p(0.05), p(0.25), p(0.50), p(0.75), p(0.95))
}

/// Compute 95% confidence interval from mean and variance.
pub fn confidence_interval(mean: f64, variance: f64) -> (f64, f64) {
    let std_dev = variance.sqrt();
    (mean - 1.96 * std_dev, mean + 1.96 * std_dev)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_multid_gaussian_basic() {
        let mean = vec![0.0, 0.0];
        let cov = vec![1.0, 0.0, 0.0, 1.0]; // identity
        let samples = multid_gaussian(1000, &mean, &cov, 42);
        assert_eq!(samples.len(), 1000);
        assert_eq!(samples[0].len(), 2);

        // Mean should be near 0
        let m0: f64 = samples.iter().map(|s| s[0]).sum::<f64>() / 1000.0;
        let m1: f64 = samples.iter().map(|s| s[1]).sum::<f64>() / 1000.0;
        assert!(m0.abs() < 0.15, "mean[0] should be near 0, got {}", m0);
        assert!(m1.abs() < 0.15, "mean[1] should be near 0, got {}", m1);
    }

    #[test]
    fn test_multid_gaussian_covariance() {
        let mean = vec![1.0, 2.0];
        let cov = vec![4.0, 0.0, 0.0, 9.0]; // diag(4, 9)
        let samples = multid_gaussian(10000, &mean, &cov, 42);

        let m0: f64 = samples.iter().map(|s| s[0]).sum::<f64>() / 10000.0;
        let m1: f64 = samples.iter().map(|s| s[1]).sum::<f64>() / 10000.0;
        assert!((m0 - 1.0).abs() < 0.15, "mean[0] should be near 1, got {}", m0);
        assert!((m1 - 2.0).abs() < 0.15, "mean[1] should be near 2, got {}", m1);

        // Variance should be near 4 and 9
        let v0: f64 = samples.iter().map(|s| (s[0] - m0).powi(2)).sum::<f64>() / 10000.0;
        let v1: f64 = samples.iter().map(|s| (s[1] - m1).powi(2)).sum::<f64>() / 10000.0;
        assert!((v0 - 4.0).abs() < 1.0, "var[0] should be near 4, got {}", v0);
        assert!((v1 - 9.0).abs() < 2.0, "var[1] should be near 9, got {}", v1);
    }

    #[test]
    fn test_cholesky_identity() {
        let a = vec![1.0, 0.0, 0.0, 1.0];
        let l = cholesky(&a, 2);
        assert!((l[0] - 1.0).abs() < 1e-10);
        assert!((l[1]).abs() < 1e-10);
        assert!((l[2]).abs() < 1e-10);
        assert!((l[3] - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_cholesky_spd() {
        // [[4, 2], [2, 3]]
        let a = vec![4.0, 2.0, 2.0, 3.0];
        let l = cholesky(&a, 2);
        // L * L^T should equal A
        let llt00 = l[0] * l[0];
        let llt01 = l[0] * l[2];
        let llt11 = l[2] * l[2] + l[3] * l[3];
        assert!((llt00 - 4.0).abs() < 1e-10, "llt[0][0] = {}", llt00);
        assert!((llt01 - 2.0).abs() < 1e-10, "llt[0][1] = {}", llt01);
        assert!((llt11 - 3.0).abs() < 1e-10, "llt[1][1] = {}", llt11);
    }

    #[test]
    fn test_latin_hypercube_basic() {
        let samples = latin_hypercube(100, 3, 42);
        assert_eq!(samples.len(), 100);
        assert_eq!(samples[0].len(), 3);

        // Each dimension should have values in [0, 1)
        for s in &samples {
            for &v in s {
                assert!(v >= 0.0 && v < 1.0, "LHS value out of range: {}", v);
            }
        }
    }

    #[test]
    fn test_latin_hypercube_stratification() {
        // With n=10, each dimension should have exactly one sample per stratum
        let n = 10;
        let samples = latin_hypercube(n, 1, 42);

        for dim in 0..1 {
            let mut strata = vec![false; n];
            for s in &samples {
                let stratum = (s[dim] * n as f64) as usize;
                assert!(stratum < n, "stratum {} >= n", stratum);
                strata[stratum] = true;
            }
            // Every stratum should be covered
            for (i, &covered) in strata.iter().enumerate() {
                assert!(covered, "stratum {} not covered in dim {}", i, dim);
            }
        }
    }

    #[test]
    fn test_parallel_trials_basic() {
        let mean = vec![0.5, 0.5];
        let cov = vec![0.01, 0.0, 0.0, 0.01];
        let (mean_v, var_v, n, best, best_f) = parallel_trials(
            1000,
            &mean,
            &cov,
            42,
            |x| x[0] + x[1], // simple linear fitness
        );
        assert_eq!(n, 1000);
        assert!((mean_v - 1.0).abs() < 0.1, "mean should be near 1.0, got {}", mean_v);
        assert!(var_v > 0.0);
        assert_eq!(best.len(), 2);
        assert!(best_f > mean_v, "best fitness should exceed mean");
    }

    #[test]
    fn test_lhs_parallel_trials() {
        let ranges = vec![(0.0, 1.0), (0.0, 1.0)];
        let result = lhs_parallel_trials(
            500,
            &ranges,
            42,
            |x| x[0] * x[1], // maximize product
        );
        assert_eq!(result.n_completed, 500);
        assert!(result.mean > 0.0);
        assert!(result.best_fitness > result.mean);
        assert_eq!(result.samples.len(), 500);
        assert_eq!(result.fitness_values.len(), 500);
    }

    #[test]
    fn test_compute_statistics() {
        let values: Vec<f64> = (0..100).map(|i| i as f64).collect();
        let (mean, var, min, max, p5, p25, p50, p75, p95) = compute_statistics(&values);
        assert!((mean - 49.5).abs() < 0.1);
        assert!(var > 0.0);
        assert!((min - 0.0).abs() < 0.1);
        assert!((max - 99.0).abs() < 0.1);
        assert!(p5 < p25);
        assert!(p25 < p50);
        assert!(p50 < p75);
        assert!(p75 < p95);
    }

    #[test]
    fn test_compute_statistics_empty() {
        let (mean, var, min, max, p5, p25, p50, p75, p95) = compute_statistics(&[]);
        assert_eq!(mean, 0.0);
        assert_eq!(var, 0.0);
        assert_eq!(min, 0.0);
        assert_eq!(max, 0.0);
        assert_eq!(p5, 0.0);
        assert_eq!(p25, 0.0);
        assert_eq!(p50, 0.0);
        assert_eq!(p75, 0.0);
        assert_eq!(p95, 0.0);
    }

    #[test]
    fn test_confidence_interval() {
        let (lo, hi) = confidence_interval(0.5, 0.01);
        assert!(lo < 0.5 && hi > 0.5);
    }

    #[test]
    fn test_xoshiro_reproducibility() {
        let mean = vec![0.0];
        let cov = vec![1.0];
        let s1 = multid_gaussian(10, &mean, &cov, 42);
        let s2 = multid_gaussian(10, &mean, &cov, 42);
        // Same seed should produce same samples
        for i in 0..10 {
            assert!((s1[i][0] - s2[i][0]).abs() < 1e-10);
        }
    }
}
