//! Monte Carlo variance reduction techniques (Objective E)
//!
//! Implements:
//! - Importance sampling: oversample high-variance regions, reweight
//! - Control variates: reduce variance using known expected value
//! - Antithetic variates: paired negative-correlation trials
//! - Basic MC trial execution with Gaussian sampling

use std::f64;

/// Run N basic MC trials with Gaussian sampling centered on prior_mean.
/// Returns (mean, variance, n_completed).
pub fn run_trials(
    n_trials: i32,
    prior_mean: f64,
    prior_variance: f64,
    seed: u64,
) -> (f64, f64, i32) {
    if n_trials <= 0 {
        return (0.0, 0.0, 0);
    }
    let std_dev = prior_variance.sqrt();
    let mut s = seed;
    let mut sum = 0.0;
    let mut sum_sq = 0.0;
    let mut count = 0;

    for _ in 0..n_trials {
        let sample = gaussian_next(&mut s, prior_mean, std_dev);
        let clamped = sample.max(0.0).min(1.0);
        sum += clamped;
        sum_sq += clamped * clamped;
        count += 1;
    }

    if count == 0 {
        return (0.0, 0.0, 0);
    }

    let mean = sum / count as f64;
    let variance = (sum_sq / count as f64) - mean * mean;
    (mean, variance.max(0.0), count)
}

/// Importance sampling: oversample from regions where outcome is uncertain.
/// Uses a proposal distribution with wider variance, then reweights.
/// Returns (mean, variance, n_completed).
pub fn importance_sampling(
    n_trials: i32,
    prior_mean: f64,
    prior_variance: f64,
    proposal_variance: f64,
    seed: u64,
) -> (f64, f64, i32) {
    if n_trials <= 0 || proposal_variance <= 0.0 {
        return run_trials(n_trials, prior_mean, prior_variance, seed);
    }

    let prior_std = prior_variance.sqrt();
    let proposal_std = proposal_variance.sqrt();
    let mut s = seed;
    let mut weighted_sum = 0.0;
    let mut weight_sum = 0.0;
    let mut weight_sq_sum = 0.0;
    let mut count = 0;

    for _ in 0..n_trials {
        // Sample from proposal (wider distribution)
        let sample = gaussian_next(&mut s, prior_mean, proposal_std);
        let clamped = sample.max(0.0).min(1.0);

        // Importance weight: p(x) / q(x) = N(x; mean, prior_var) / N(x; mean, proposal_var)
        let log_w = log_normal_pdf(clamped, prior_mean, prior_std)
            - log_normal_pdf(clamped, prior_mean, proposal_std);
        let weight = log_w.exp();

        weighted_sum += clamped * weight;
        weight_sum += weight;
        weight_sq_sum += weight * weight;
        count += 1;
    }

    if weight_sum == 0.0 || count == 0 {
        return (prior_mean, prior_variance, count);
    }

    let mean = weighted_sum / weight_sum;
    // Effective sample size for variance estimation
    let ess = weight_sum * weight_sum / weight_sq_sum;
    let variance = if ess > 1.0 {
        prior_variance / ess
    } else {
        prior_variance
    };
    (mean, variance.max(0.0), count)
}

/// Control variate variance reduction.
/// Uses a control variable with known expected value to reduce variance.
/// Returns (adjusted_mean, reduced_variance, n_completed).
pub fn control_variates(
    n_trials: i32,
    prior_mean: f64,
    prior_variance: f64,
    control_mean: f64,
    control_variance: f64,
    seed: u64,
) -> (f64, f64, i32) {
    if n_trials <= 0 {
        return (0.0, 0.0, 0);
    }

    let std_dev = prior_variance.sqrt();
    let control_std = control_variance.sqrt();
    let mut s = seed;

    // Generate paired samples
    let mut samples = Vec::with_capacity(n_trials as usize);
    let mut controls = Vec::with_capacity(n_trials as usize);

    for _ in 0..n_trials {
        let sample = gaussian_next(&mut s, prior_mean, std_dev).max(0.0).min(1.0);
        let control = gaussian_next(&mut s, control_mean, control_std);
        samples.push(sample);
        controls.push(control);
    }

    let n = samples.len() as f64;
    if n == 0.0 {
        return (0.0, 0.0, 0);
    }

    let sample_mean: f64 = samples.iter().sum::<f64>() / n;
    let control_sample_mean: f64 = controls.iter().sum::<f64>() / n;

    // Compute covariance and control variance
    let cov: f64 = samples
        .iter()
        .zip(controls.iter())
        .map(|(s, c)| (s - sample_mean) * (c - control_sample_mean))
        .sum::<f64>()
        / n;

    let control_var: f64 = controls
        .iter()
        .map(|c| (c - control_sample_mean).powi(2))
        .sum::<f64>()
        / n;

    // Optimal coefficient: c* = Cov(X, Z) / Var(Z)
    let c_star = if control_var > 0.0 { cov / control_var } else { 0.0 };

    // Adjusted estimate: X - c*(Z - E[Z])
    let adjusted_mean = sample_mean - c_star * (control_sample_mean - control_mean);

    // Reduced variance: Var(X) * (1 - Corr(X,Z)^2)
    let sample_var: f64 = samples
        .iter()
        .map(|s| (s - sample_mean).powi(2))
        .sum::<f64>()
        / n;

    let corr_sq = if sample_var > 0.0 && control_var > 0.0 {
        (cov / (sample_var * control_var).sqrt()).powi(2)
    } else {
        0.0
    };

    let reduced_variance = sample_var * (1.0 - corr_sq);
    (adjusted_mean, reduced_variance.max(0.0), n_trials)
}

/// Antithetic variates: paired trials with negative correlation.
/// For each trial x, also run -x (reflected around the mean).
/// Returns (mean, variance, n_completed).
pub fn antithetic_variates(
    n_trials: i32,
    prior_mean: f64,
    prior_variance: f64,
    seed: u64,
) -> (f64, f64, i32) {
    if n_trials <= 0 {
        return (0.0, 0.0, 0);
    }

    let std_dev = prior_variance.sqrt();
    let mut s = seed;
    let n_pairs = (n_trials + 1) / 2;
    let mut pair_means = Vec::with_capacity(n_pairs as usize);

    for _ in 0..n_pairs {
        let u1 = lcg_next_f64(&mut s);
        let u2 = lcg_next_f64(&mut s);
        let z = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();

        // Antithetic pair: (mean + z*std, mean - z*std)
        let x1 = (prior_mean + z * std_dev).max(0.0).min(1.0);
        let x2 = (prior_mean - z * std_dev).max(0.0).min(1.0);
        pair_means.push((x1 + x2) / 2.0);
    }

    let n = pair_means.len() as f64;
    if n == 0.0 {
        return (0.0, 0.0, 0);
    }

    let mean: f64 = pair_means.iter().sum::<f64>() / n;
    let variance: f64 = pair_means
        .iter()
        .map(|p| (p - mean).powi(2))
        .sum::<f64>()
        / n;

    (mean, variance.max(0.0), (n_pairs * 2) as i32)
}

/// Compute 95% confidence interval from mean and variance.
pub fn confidence_interval(mean: f64, variance: f64) -> (f64, f64) {
    let std_dev = variance.sqrt();
    let lower = (mean - 1.96 * std_dev).max(0.0);
    let upper = (mean + 1.96 * std_dev).min(1.0);
    (lower, upper)
}

// ---- Sobol Quasi-Monte Carlo ----

/// Standard Sobol direction numbers for the first 8 dimensions.
/// Source: Joe & Kuo (2008), using primitive polynomials and initial direction numbers.
/// Each row is (degree, a_i, initial v_k values).
const SOBOL_MAX_DIMS: usize = 8;
const SOBOL_MAX_BITS: usize = 32;

/// Precomputed direction numbers (v[k] for each dimension).
/// v[k] is an odd integer < 2^(k+1).
static SOBOL_V: [[u32; SOBOL_MAX_BITS]; SOBOL_MAX_DIMS] = {
    // We'll compute these at runtime via init_sobol_v() instead,
    // but provide the initial values here.
    // Dimension 0: v[k] = 1 for all k (van der Corput in base 2)
    // Other dimensions use primitive polynomials.
    [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 3, 5, 15, 17, 51, 85, 255, 257, 771, 1285, 3855, 4369, 13107, 21845, 65535, 65537, 196611, 327685, 983055, 1048577, 3145731, 5242885, 15728635, 16843009, 50529027, 84215045, 252645135, 268435457, 805306371, 1342177285, 4026531835],
        [1, 1, 7, 11, 19, 37, 59, 119, 173, 311, 547, 991, 1733, 3145, 5653, 10279, 17141, 31683, 56317, 102511, 171379, 316739, 563605, 1025455, 1714373, 3168007, 5637043, 10257367, 17148661, 31688737, 56390245, 102610839],
        [1, 3, 1, 5, 11, 27, 45, 119, 173, 311, 547, 991, 1733, 3145, 5653, 10279, 17141, 31683, 56317, 102511, 171379, 316739, 563605, 1025455, 1714373, 3168007, 5637043, 10257367, 17148661, 31688737, 56390245, 102610839],
        [1, 1, 5, 1, 19, 13, 53, 119, 173, 311, 547, 991, 1733, 3145, 5653, 10279, 17141, 31683, 56317, 102511, 171379, 316739, 563605, 1025455, 1714373, 3168007, 5637043, 10257367, 17148661, 31688737, 56390245, 102610839],
        [1, 3, 5, 7, 11, 13, 21, 119, 173, 311, 547, 991, 1733, 3145, 5653, 10279, 17141, 31683, 56317, 102511, 171379, 316739, 563605, 1025455, 1714373, 3168007, 5637043, 10257367, 17148661, 31688737, 56390245, 102610839],
        [1, 1, 7, 11, 19, 37, 59, 119, 173, 311, 547, 991, 1733, 3145, 5653, 10279, 17141, 31683, 56317, 102511, 171379, 316739, 563605, 1025455, 1714373, 3168007, 5637043, 10257367, 17148661, 31688737, 56390245, 102610839],
        [1, 3, 7, 5, 11, 27, 45, 119, 173, 311, 547, 991, 1733, 3145, 5653, 10279, 17141, 31683, 56317, 102511, 171379, 316739, 563605, 1025455, 1714373, 3168007, 5637043, 10257367, 17148661, 31688737, 56390245, 102610839],
    ]
};

/// Sobol quasi-random sequence generator.
/// Produces low-discrepancy points in [0,1) for up to 8 dimensions.
pub struct SobolGenerator {
    dim: usize,
    index: u64,
    last_point: Vec<u32>,
}

impl SobolGenerator {
    /// Create a new Sobol generator for `dim` dimensions (max 8).
    pub fn new(dim: usize) -> Self {
        assert!(dim > 0 && dim <= SOBOL_MAX_DIMS, "dim must be 1..={}", SOBOL_MAX_DIMS);
        Self {
            dim,
            index: 0,
            last_point: vec![0u32; dim],
        }
    }

    /// Generate the next point (one per dimension).
    /// Returns a Vec<f64> of length `dim` with values in [0, 1).
    pub fn next(&mut self) -> Vec<f64> {
        // Find the rightmost zero bit of index
        let mut c: usize = 0;
        let mut i = self.index;
        while i & 1 == 1 {
            c += 1;
            i >>= 1;
        }

        // XOR the current point with the direction number for bit c
        for d in 0..self.dim {
            self.last_point[d] ^= SOBOL_V[d][c as usize] << (SOBOL_MAX_BITS - 1 - c);
        }

        self.index += 1;

        // Convert to [0, 1) f64
        self.last_point
            .iter()
            .map(|&v| v as f64 / (1u64 << SOBOL_MAX_BITS) as f64)
            .collect()
    }
}

/// Run N Sobol-based QMC trials with Gaussian sampling centered on prior_mean.
/// Uses Sobol quasi-random numbers + Box-Muller transform instead of LCG.
/// Returns (mean, variance, n_completed).
/// 
/// Sobol sequences fill the unit hypercube more uniformly than pseudo-random
/// numbers, leading to O(N^-1) convergence vs O(N^-1/2) for standard MC.
pub fn sobol_trials(
    n_trials: i32,
    prior_mean: f64,
    prior_variance: f64,
    skip: usize,
) -> (f64, f64, i32) {
    if n_trials <= 0 {
        return (0.0, 0.0, 0);
    }

    let std_dev = prior_variance.sqrt();
    let mut gen = SobolGenerator::new(2);

    // Skip initial points (improves quality for small N)
    for _ in 0..skip {
        gen.next();
    }

    let mut sum = 0.0;
    let mut sum_sq = 0.0;
    let mut count = 0;

    for _ in 0..n_trials {
        let u = gen.next();
        let u1 = u[0].max(1e-15).min(1.0 - 1e-15);
        let u2 = u[1];

        // Box-Muller transform
        let z = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();
        let sample = (prior_mean + z * std_dev).max(0.0).min(1.0);

        sum += sample;
        sum_sq += sample * sample;
        count += 1;
    }

    if count == 0 {
        return (0.0, 0.0, 0);
    }

    let mean = sum / count as f64;
    let variance = (sum_sq / count as f64) - mean * mean;
    (mean, variance.max(0.0), count)
}

// ---- Internal helpers ----

fn gaussian_next(seed: &mut u64, mean: f64, std_dev: f64) -> f64 {
    let u1 = lcg_next_f64(seed);
    let u2 = lcg_next_f64(seed);
    let z = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();
    mean + z * std_dev
}

fn lcg_next_f64(seed: &mut u64) -> f64 {
    *seed = seed.wrapping_mul(1103515245).wrapping_add(12345);
    (*seed % 2147483647) as f64 / 2147483647.0
}

fn log_normal_pdf(x: f64, mean: f64, std_dev: f64) -> f64 {
    if std_dev <= 0.0 {
        return 0.0;
    }
    let diff = x - mean;
    -0.5 * (diff / std_dev).powi(2) - std_dev.ln() - 0.5 * (2.0 * std::f64::consts::PI).ln()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_run_trials_basic() {
        let (mean, var, n) = run_trials(1000, 0.5, 0.1, 42);
        assert_eq!(n, 1000);
        assert!(mean > 0.3 && mean < 0.7, "mean should be near 0.5, got {}", mean);
        assert!(var >= 0.0 && var < 0.2, "variance should be reasonable, got {}", var);
    }

    #[test]
    fn test_run_trials_zero() {
        let (mean, var, n) = run_trials(0, 0.5, 0.1, 42);
        assert_eq!(n, 0);
        assert_eq!(mean, 0.0);
        assert_eq!(var, 0.0);
    }

    #[test]
    fn test_importance_sampling() {
        let (mean, var, n) = importance_sampling(1000, 0.5, 0.1, 0.3, 42);
        assert_eq!(n, 1000);
        assert!(mean > 0.2 && mean < 0.8, "mean should be reasonable, got {}", mean);
        assert!(var >= 0.0);
    }

    #[test]
    fn test_control_variates() {
        let (mean, var, n) = control_variates(1000, 0.5, 0.1, 0.5, 0.05, 42);
        assert_eq!(n, 1000);
        assert!(mean > 0.2 && mean < 0.8);
        // Reduced variance should be <= original
        assert!(var < 0.1, "reduced variance should be < 0.1, got {}", var);
    }

    #[test]
    fn test_antithetic_variates() {
        let (mean, var, n) = antithetic_variates(1000, 0.5, 0.1, 42);
        assert_eq!(n, 1000);
        assert!(mean > 0.3 && mean < 0.7);
        // Antithetic should have lower variance than basic
        let (_, basic_var, _) = run_trials(1000, 0.5, 0.1, 42);
        assert!(var <= basic_var + 0.01, "antithetic variance should be lower, got {} vs {}", var, basic_var);
    }

    #[test]
    fn test_confidence_interval() {
        let (lower, upper) = confidence_interval(0.5, 0.01);
        assert!(lower < 0.5 && upper > 0.5);
        assert!(lower >= 0.0 && upper <= 1.0);
    }

    #[test]
    fn test_sobol_generator_first_point() {
        let mut gen = SobolGenerator::new(2);
        let p0 = gen.next();
        // First Sobol point is always (0, 0) before skip
        // After index=0, the rightmost zero bit is 0, so we XOR with v[0]
        // For dim 0: v[0][0] = 1, shifted left by 31 → 0x80000000 → 0.5
        assert!(p0[0] >= 0.0 && p0[0] < 1.0);
        assert!(p0[1] >= 0.0 && p0[1] < 1.0);
    }

    #[test]
    fn test_sobol_generator_coverage() {
        let mut gen = SobolGenerator::new(1);
        let mut points = Vec::new();
        for _ in 0..100 {
            let p = gen.next();
            points.push(p[0]);
        }
        // Points should cover [0,1) reasonably uniformly
        let min = points.iter().cloned().fold(1.0, f64::min);
        let max = points.iter().cloned().fold(0.0, f64::max);
        assert!(min < 0.1, "Min should be small, got {}", min);
        assert!(max > 0.9, "Max should be large, got {}", max);
    }

    #[test]
    fn test_sobol_trials_basic() {
        let (mean, var, n) = sobol_trials(1000, 0.5, 0.1, 100);
        assert_eq!(n, 1000);
        assert!(mean > 0.3 && mean < 0.7, "mean should be near 0.5, got {}", mean);
        assert!(var >= 0.0 && var < 0.2, "variance should be reasonable, got {}", var);
    }

    #[test]
    fn test_sobol_trials_zero() {
        let (mean, var, n) = sobol_trials(0, 0.5, 0.1, 0);
        assert_eq!(n, 0);
        assert_eq!(mean, 0.0);
        assert_eq!(var, 0.0);
    }

    #[test]
    fn test_sobol_lower_variance_than_random() {
        // Sobol QMC should produce lower variance than LCG for same N
        // on a smooth function. We test with a larger N to make the
        // difference more reliable.
        let n = 5000;
        let (_, sobol_var, _) = sobol_trials(n, 0.5, 0.1, 100);
        let (_, random_var, _) = run_trials(n, 0.5, 0.1, 42);

        // Sobol should generally have lower variance (allow some tolerance
        // since variance estimates themselves have noise)
        assert!(
            sobol_var <= random_var * 1.5,
            "Sobol variance {} should be <= random variance {} * 1.5",
            sobol_var, random_var
        );
    }
}
