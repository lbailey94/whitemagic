//! Bayesian optimization for adaptive sampling in high-dimensional spaces.
//!
//! Implements:
//! - Gaussian Process surrogate with squared exponential kernel
//! - Hyperparameter optimization via marginal likelihood maximization
//! - Expected Improvement (EI) acquisition function
//! - Bayesian optimization loop with parallel candidate evaluation

use rand::{RngCore, SeedableRng};
use rand_xoshiro::Xoshiro256PlusPlus;
use rayon::prelude::*;

/// Standard normal PDF.
fn normal_pdf(x: f64) -> f64 {
    (-0.5 * x * x).exp() / (2.0 * std::f64::consts::PI).sqrt()
}

/// Standard normal CDF via error function approximation.
fn normal_cdf(x: f64) -> f64 {
    0.5 * (1.0 + erf(x / std::f64::consts::SQRT_2))
}

/// Abramowitz & Stegun error function approximation (max error ~1.5e-7).
fn erf(x: f64) -> f64 {
    let sign = if x < 0.0 { -1.0 } else { 1.0 };
    let x = x.abs();
    let a1 = 0.254829592;
    let a2 = -0.284496736;
    let a3 = 1.421413741;
    let a4 = -1.453152027;
    let a5 = 1.061405429;
    let p = 0.3275911;
    let t = 1.0 / (1.0 + p * x);
    let y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * (-x * x).exp();
    sign * y
}

/// Gaussian Process with squared exponential kernel.
///
/// k(x, x') = sigma_f^2 * exp(-||x - x'||^2 / (2 * length_scale^2))
///
/// Supports multi-dimensional inputs with a single shared length scale.
/// Noise variance sigma_n^2 accounts for observation noise.
#[derive(Debug, Clone)]
pub struct GaussianProcess {
    /// Training inputs (each is a d-dimensional vector)
    pub x_train: Vec<Vec<f64>>,
    /// Training outputs
    pub y_train: Vec<f64>,
    /// Length scale (l)
    pub length_scale: f64,
    /// Signal variance (sigma_f^2)
    pub sigma_f: f64,
    /// Noise variance (sigma_n^2)
    pub sigma_n: f64,
    /// Cholesky factor of K + sigma_n^2 * I
    pub l_chol: Vec<Vec<f64>>,
    /// alpha = K^{-1} * y (used for posterior mean)
    pub alpha: Vec<f64>,
    /// y_mean (for centering)
    pub y_mean: f64,
}

impl GaussianProcess {
    /// Fit a GP to training data with given hyperparameters.
    pub fn fit(
        x_train: Vec<Vec<f64>>,
        y_train: Vec<f64>,
        length_scale: f64,
        sigma_f: f64,
        sigma_n: f64,
    ) -> Self {
        let n = x_train.len();
        let y_mean = if y_train.is_empty() {
            0.0
        } else {
            y_train.iter().sum::<f64>() / n as f64
        };
        let y_centered: Vec<f64> = y_train.iter().map(|y| y - y_mean).collect();

        // Build kernel matrix K + sigma_n^2 * I
        let mut k_mat = vec![vec![0.0f64; n]; n];
        for i in 0..n {
            for j in 0..n {
                let dist_sq = squared_dist(&x_train[i], &x_train[j]);
                k_mat[i][j] = sigma_f * sigma_f * (-dist_sq / (2.0 * length_scale * length_scale)).exp();
            }
            k_mat[i][i] += sigma_n * sigma_n;
        }

        let l_chol = cholesky_2d(&k_mat, n);

        // Solve K^{-1} * y via forward/back substitution
        let alpha = solve_triangular(&l_chol, &y_centered, n);

        GaussianProcess {
            x_train,
            y_train,
            length_scale,
            sigma_f,
            sigma_n,
            l_chol,
            alpha,
            y_mean,
        }
    }

    /// Predict mean and variance at a new point.
    pub fn predict(&self, x_new: &[f64]) -> (f64, f64) {
        let n = self.x_train.len();
        if n == 0 {
            return (self.y_mean, self.sigma_f * self.sigma_f);
        }

        // k_* = kernel(x_new, X_train)
        let k_star: Vec<f64> = self
            .x_train
            .iter()
            .map(|xi| {
                let dist_sq = squared_dist(x_new, xi);
                self.sigma_f * self.sigma_f * (-dist_sq / (2.0 * self.length_scale * self.length_scale)).exp()
            })
            .collect();

        // mean = k_*^T * alpha + y_mean
        let mean: f64 = k_star.iter().zip(self.alpha.iter()).map(|(k, a)| k * a).sum::<f64>() + self.y_mean;

        // variance = k(x_new, x_new) - k_*^T * K^{-1} * k_*
        // K^{-1} * k_* = solve_triangular(L, k_star)
        let v = solve_triangular(&self.l_chol, &k_star, n);
        let k_xx = self.sigma_f * self.sigma_f; // kernel of x with itself
        let variance = k_xx - v.iter().map(|vi| vi * vi).sum::<f64>();

        (mean, variance.max(0.0))
    }

    /// Batch predict for multiple points (parallel via Rayon).
    pub fn predict_batch(&self, x_batch: &[Vec<f64>]) -> Vec<(f64, f64)> {
        x_batch.par_iter().map(|x| self.predict(x)).collect()
    }

    /// Log marginal likelihood (for hyperparameter optimization).
    pub fn log_marginal_likelihood(&self) -> f64 {
        let n = self.x_train.len();
        if n == 0 {
            return 0.0;
        }

        // log p(y|X) = -0.5 * y^T * K^{-1} * y - 0.5 * log|K| - n/2 * log(2pi)
        let y_centered: Vec<f64> = self.y_train.iter().map(|y| y - self.y_mean).collect();

        // y^T * K^{-1} * y = y^T * alpha (since alpha = K^{-1} * y)
        let quad: f64 = y_centered.iter().zip(self.alpha.iter()).map(|(y, a)| y * a).sum();

        // log|K| = 2 * sum(log(diag(L)))
        let log_det: f64 = (0..n).map(|i| self.l_chol[i][i].ln()).sum::<f64>() * 2.0;

        -0.5 * quad - 0.5 * log_det - (n as f64 / 2.0) * (2.0 * std::f64::consts::PI).ln()
    }

    /// Optimize hyperparameters via grid search over length_scale and sigma_f.
    /// Returns a new GP with optimized hyperparameters.
    pub fn optimize_hyperparameters(
        x_train: Vec<Vec<f64>>,
        y_train: Vec<f64>,
        sigma_n: f64,
        n_grid: usize,
    ) -> Self {
        let mut best_lml = f64::NEG_INFINITY;
        let mut best_gp = None;

        // Grid search over length_scale and sigma_f
        let l_range: Vec<f64> = (0..n_grid)
            .map(|i| 0.1 + 10.0 * (i as f64 / (n_grid - 1) as f64))
            .collect();
        let sf_range: Vec<f64> = (0..n_grid)
            .map(|i| 0.1 + 5.0 * (i as f64 / (n_grid - 1) as f64))
            .collect();

        for &l in &l_range {
            for &sf in &sf_range {
                let gp = GaussianProcess::fit(
                    x_train.clone(),
                    y_train.clone(),
                    l,
                    sf,
                    sigma_n,
                );
                let lml = gp.log_marginal_likelihood();
                if lml > best_lml {
                    best_lml = lml;
                    best_gp = Some(gp);
                }
            }
        }

        best_gp.unwrap_or_else(|| {
            GaussianProcess::fit(x_train, y_train, 1.0, 1.0, sigma_n)
        })
    }
}

/// Expected Improvement acquisition function.
///
/// EI(x) = (f_best - mu(x)) * Phi((f_best - mu(x)) / sigma(x))
///         + sigma(x) * phi((f_best - mu(x)) / sigma(x))
///
/// For maximization. Returns EI value and the predicted mean.
pub fn expected_improvement(
    gp: &GaussianProcess,
    x_candidate: &[f64],
    f_best: f64,
    xi: f64,
) -> (f64, f64) {
    let (mu, sigma) = gp.predict(x_candidate);
    let sigma = sigma.max(1e-10);

    let improvement = f_best - mu - xi;
    let z = improvement / sigma;

    let ei = improvement * normal_cdf(z) + sigma * normal_pdf(z);
    (ei.max(0.0), mu)
}

/// Batch EI evaluation (parallel via Rayon).
pub fn expected_improvement_batch(
    gp: &GaussianProcess,
    x_candidates: &[Vec<f64>],
    f_best: f64,
    xi: f64,
) -> Vec<(f64, f64)> {
    x_candidates
        .par_iter()
        .map(|x| expected_improvement(gp, x, f_best, xi))
        .collect()
}

/// Run Bayesian optimization loop.
///
/// Given an initial set of samples, iteratively:
/// 1. Fit a GP to current data
/// 2. Generate candidate points (via LHS or random sampling)
/// 3. Evaluate EI on all candidates
/// 4. Select the best EI point and evaluate the true fitness
/// 5. Add to training set and repeat
///
/// Returns the best point found and its fitness value.
pub fn bayesian_optimize(
    initial_x: Vec<Vec<f64>>,
    initial_y: Vec<f64>,
    param_ranges: &[(f64, f64)],
    fitness_fn: impl Fn(&[f64]) -> f64 + Sync,
    n_iterations: usize,
    n_candidates: usize,
    sigma_n: f64,
    xi: f64,
    seed: u64,
) -> (Vec<f64>, f64, Vec<f64>, Vec<Vec<f64>>, Vec<f64>) {
    let mut x_train = initial_x;
    let mut y_train = initial_y;
    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);
    let d = param_ranges.len();

    for _ in 0..n_iterations {
        // Fit GP with optimized hyperparameters
        let gp = GaussianProcess::optimize_hyperparameters(
            x_train.clone(),
            y_train.clone(),
            sigma_n,
            8,
        );

        // Current best (for maximization)
        let f_best = y_train.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

        // Generate candidates via random sampling
        let candidates: Vec<Vec<f64>> = (0..n_candidates)
            .map(|_| {
                (0..d)
                    .map(|j| {
                        let (lo, hi) = param_ranges[j];
                        lo + (rng.next_u64() as f64 / u64::MAX as f64) * (hi - lo)
                    })
                    .collect()
            })
            .collect();

        // Evaluate EI on all candidates (parallel)
        let ei_values = expected_improvement_batch(&gp, &candidates, f_best, xi);

        // Select best EI candidate
        let (best_idx, _) = ei_values
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| {
                a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal)
            })
            .unwrap_or((0, &(0.0, 0.0)));

        let best_candidate = candidates[best_idx].clone();
        let best_fitness = fitness_fn(&best_candidate);

        x_train.push(best_candidate);
        y_train.push(best_fitness);
    }

    // Find overall best
    let (best_idx, &best_y) = y_train
        .iter()
        .enumerate()
        .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
        .unwrap_or((0, &0.0));

    let best_x = x_train[best_idx].clone();

    // Return convergence history
    let convergence: Vec<f64> = y_train
        .iter()
        .scan(f64::NEG_INFINITY, |best, &y| {
            *best = best.max(y);
            Some(*best)
        })
        .collect();

    (best_x, best_y, convergence, x_train, y_train)
}

// ─── Utility functions ───

/// Cholesky decomposition of a 2D symmetric positive-definite matrix.
/// Returns lower-triangular L such that L * L^T = A.
fn cholesky_2d(a: &[Vec<f64>], d: usize) -> Vec<Vec<f64>> {
    let mut l = vec![vec![0.0f64; d]; d];
    for i in 0..d {
        for j in 0..=i {
            let mut sum = a[i][j];
            for k in 0..j {
                sum -= l[i][k] * l[j][k];
            }
            if i == j {
                l[i][j] = sum.sqrt();
            } else {
                l[i][j] = sum / l[j][j];
            }
        }
    }
    l
}

/// Squared Euclidean distance between two vectors.
fn squared_dist(a: &[f64], b: &[f64]) -> f64 {
    a.iter()
        .zip(b.iter())
        .map(|(ai, bi)| (ai - bi) * (ai - bi))
        .sum()
}

/// Solve L * y = b (forward substitution) then L^T * x = y (back substitution).
/// Returns x such that (L * L^T) * x = b, i.e., K^{-1} * b.
fn solve_triangular(l: &[Vec<f64>], b: &[f64], n: usize) -> Vec<f64> {
    // Forward: L * y = b
    let mut y = vec![0.0f64; n];
    for i in 0..n {
        let mut sum = b[i];
        for j in 0..i {
            sum -= l[i][j] * y[j];
        }
        y[i] = sum / l[i][i];
    }

    // Back: L^T * x = y
    let mut x = vec![0.0f64; n];
    for i in (0..n).rev() {
        let mut sum = y[i];
        for j in (i + 1)..n {
            sum -= l[j][i] * x[j];
        }
        x[i] = sum / l[i][i];
    }

    x
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normal_cdf_bounds() {
        assert!(normal_cdf(-3.0) < 0.01);
        // Abramowitz & Stegun erf has ~1.5e-7 precision
        assert!((normal_cdf(0.0) - 0.5).abs() < 1e-6);
        assert!(normal_cdf(3.0) > 0.99);
    }

    #[test]
    fn test_normal_pdf_symmetry() {
        assert!((normal_pdf(1.0) - normal_pdf(-1.0)).abs() < 1e-15);
    }

    #[test]
    fn test_erf_known_values() {
        // A&S 7.1.26 has max error ~1.5e-7
        assert!((erf(0.0) - 0.0).abs() < 1e-6);
        assert!((erf(1.0) - 0.8427007929497149).abs() < 1e-6);
        assert!((erf(-1.0) + 0.8427007929497149).abs() < 1e-6);
    }

    #[test]
    fn test_gp_fit_predict() {
        // Simple 1D: y = x^2, sample at a few points
        let x_train = vec![vec![-1.0], vec![-0.5], vec![0.0], vec![0.5], vec![1.0]];
        let y_train = vec![1.0, 0.25, 0.0, 0.25, 1.0];

        let gp = GaussianProcess::fit(x_train, y_train, 0.5, 1.0, 1e-6);

        // Predict at x=0.0 (should be near 0)
        let (mu, var) = gp.predict(&[0.0]);
        assert!(mu.abs() < 0.1, "GP mean at x=0 should be near 0, got {}", mu);
        assert!(var >= 0.0, "Variance should be non-negative");

        // Predict at x=0.7 (should be between 0.25 and 1.0)
        let (mu2, _) = gp.predict(&[0.7]);
        assert!(mu2 > 0.2 && mu2 < 1.1, "GP mean at x=0.7 should be between 0.2 and 1.1, got {}", mu2);
    }

    #[test]
    fn test_gp_predict_batch() {
        let x_train = vec![vec![0.0], vec![1.0], vec![2.0]];
        let y_train = vec![0.0, 1.0, 4.0];
        let gp = GaussianProcess::fit(x_train, y_train, 1.0, 1.0, 1e-6);

        let x_test = vec![vec![0.5], vec![1.5], vec![3.0]];
        let results = gp.predict_batch(&x_test);
        assert_eq!(results.len(), 3);
        for (mu, var) in &results {
            assert!(var.is_finite());
            assert!(mu.is_finite());
        }
    }

    #[test]
    fn test_gp_log_marginal_likelihood() {
        let x_train = vec![vec![0.0], vec![1.0], vec![2.0]];
        let y_train = vec![0.0, 1.0, 4.0];
        let gp = GaussianProcess::fit(x_train, y_train, 1.0, 1.0, 1e-6);
        let lml = gp.log_marginal_likelihood();
        assert!(lml.is_finite(), "LML should be finite, got {}", lml);
    }

    #[test]
    fn test_expected_improvement() {
        let x_train = vec![vec![0.0], vec![1.0], vec![2.0]];
        let y_train = vec![0.0, 1.0, 4.0];
        let gp = GaussianProcess::fit(x_train, y_train, 1.0, 1.0, 1e-6);

        // f_best = 4.0 (max), evaluate EI at a new point
        let (ei, mu) = expected_improvement(&gp, &[1.5], 4.0, 0.01);
        assert!(ei >= 0.0, "EI should be non-negative, got {}", ei);
        assert!(mu.is_finite());
    }

    #[test]
    fn test_expected_improvement_batch() {
        let x_train = vec![vec![0.0], vec![1.0]];
        let y_train = vec![0.0, 1.0];
        let gp = GaussianProcess::fit(x_train, y_train, 0.5, 1.0, 1e-6);

        let candidates = vec![vec![0.5], vec![1.5], vec![2.0]];
        let results = expected_improvement_batch(&gp, &candidates, 1.0, 0.01);
        assert_eq!(results.len(), 3);
        for (ei, _) in &results {
            assert!(*ei >= 0.0);
        }
    }

    #[test]
    fn test_bayesian_optimize_simple() {
        // Maximize y = -(x-2)^2 + 5 in [0, 4], optimum at x=2, y=5
        let fitness = |x: &[f64]| -(x[0] - 2.0).powi(2) + 5.0;
        let initial_x = vec![vec![0.0], vec![4.0]];
        let initial_y = vec![fitness(&[0.0]), fitness(&[4.0])];

        let (best_x, best_y, convergence, all_x, all_y) = bayesian_optimize(
            initial_x,
            initial_y,
            &[(0.0, 4.0)],
            fitness,
            20,
            100,
            1e-4,
            0.01,
            42,
        );

        assert!(best_y > 3.0, "BO should find near-optimal value, got {}", best_y);
        assert!((best_x[0] - 2.0).abs() < 1.5, "Best x should be near 2, got {}", best_x[0]);
        assert_eq!(convergence.len(), all_y.len());
        assert_eq!(all_x.len(), all_y.len());
        // Convergence should be non-decreasing
        for i in 1..convergence.len() {
            assert!(convergence[i] >= convergence[i - 1] - 1e-10);
        }
    }

    #[test]
    fn test_gp_optimize_hyperparameters() {
        let x_train = vec![vec![0.0], vec![0.5], vec![1.0], vec![1.5], vec![2.0]];
        let y_train = vec![0.0, 0.25, 1.0, 2.25, 4.0];
        let gp = GaussianProcess::optimize_hyperparameters(x_train, y_train, 1e-4, 8);
        // Should produce a valid GP
        let (mu, var) = gp.predict(&[1.0]);
        assert!(mu.is_finite());
        assert!(var >= 0.0);
    }

    #[test]
    fn test_gp_multidimensional() {
        // 2D: y = x1 + x2
        let x_train = vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![0.0, 1.0],
            vec![1.0, 1.0],
            vec![0.5, 0.5],
        ];
        let y_train = vec![0.0, 1.0, 1.0, 2.0, 1.0];
        let gp = GaussianProcess::fit(x_train, y_train, 0.7, 1.0, 1e-6);

        let (mu, var) = gp.predict(&[0.5, 0.5]);
        assert!((mu - 1.0).abs() < 0.2, "GP at [0.5, 0.5] should be near 1.0, got {}", mu);
        assert!(var >= 0.0);
    }

    #[test]
    fn test_solve_triangular_identity() {
        // L = I (identity), b = [1, 2, 3] => x = [1, 2, 3]
        let l = vec![vec![1.0, 0.0, 0.0], vec![0.0, 1.0, 0.0], vec![0.0, 0.0, 1.0]];
        let b = vec![1.0, 2.0, 3.0];
        let x = solve_triangular(&l, &b, 3);
        for i in 0..3 {
            assert!((x[i] - b[i]).abs() < 1e-10);
        }
    }

    #[test]
    fn test_squared_dist() {
        assert!((squared_dist(&[0.0, 0.0], &[3.0, 4.0]) - 25.0).abs() < 1e-10);
        assert!((squared_dist(&[1.0], &[1.0]) - 0.0).abs() < 1e-10);
    }
}
