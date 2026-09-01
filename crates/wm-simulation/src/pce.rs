//! Superforecaster pipeline — LHS sampling → polynomial chaos expansion
//! (PCE) → Sobol' sensitivity indices → Bayesian optimization.
//!
//! Mirrors v26's `mc.superforecaster`: cheaply explore the parameter box
//! with Latin Hypercube Sampling, build a polynomial surrogate (PCE) for
//! variance-based sensitivity analysis, then refine the optimum with the
//! GP/EI optimizer from [`crate::bayesian`].
//!
//! The PCE uses probabilists' Hermite polynomials (the orthogonal basis of
//! the standard normal), so Sobol' indices are analytic in the coefficients:
//! `S_i = Σ_{α: αᵢ>0} c_α² / Σ_α c_α²`.

use crate::bayesian::{BayesianOptimizer, rand_u01};

/// Latin Hypercube Sampling over a box.
///
/// Divides each dimension into `n` equal-probability strata and draws one
/// point per stratum (stratified random sampling — far better coverage
/// than plain random for small n).
#[must_use]
pub fn latin_hypercube(bounds: &[(f64, f64)], n: usize, seed: u64) -> Vec<Vec<f64>> {
    let dim = bounds.len();
    let mut rng = seed;
    let mut points = Vec::with_capacity(n);
    // Per-dimension stratum permutations: each stratum hit exactly once
    let mut perms = Vec::with_capacity(dim);
    for _ in 0..dim {
        let mut perm: Vec<usize> = (0..n).collect();
        // Fisher–Yates shuffle with the SplitMix64 PRNG
        for i in (1..n).rev() {
            let j = (rand_u01(&mut rng) * (i + 1) as f64).floor() as usize;
            perm.swap(i, j);
        }
        perms.push(perm);
    }
    for (i, _) in (0..n).enumerate() {
        let mut row = Vec::with_capacity(dim);
        for (d, &(lo, hi)) in bounds.iter().enumerate() {
            let stratum = perms[d][i];
            let pos = rand_u01(&mut rng).clamp(1e-12, 1.0 - 1e-12);
            let v = (stratum as f64 + pos) / n as f64;
            row.push((hi - lo).mul_add(v, lo));
        }
        points.push(row);
    }
    points
}

/// Probabilists' Hermite polynomial H_n(x) evaluated at x.
///
/// H_0 = 1, H_1 = x, H_n = x·H_{n−1} − (n−1)·H_{n−2}.
fn hermite(n: usize, x: f64) -> f64 {
    if n == 0 {
        return 1.0;
    }
    if n == 1 {
        return x;
    }
    let mut h_prev2 = 1.0;
    let mut h_prev1 = x;
    let mut h = 0.0;
    for k in 2..=n {
        h = x.mul_add(h_prev1, -((k as f64 - 1.0) * h_prev2));
        h_prev2 = h_prev1;
        h_prev1 = h;
    }
    h
}

/// Multi-index of a PCE term: the Hermite degree per dimension.
type MultiIndex = Vec<usize>;

/// Generate all multi-indices with total degree ≤ `max_degree` in `dim`
/// dimensions (lexicographic, truncated).
fn multi_indices(dim: usize, max_degree: usize) -> Vec<MultiIndex> {
    let mut out = Vec::new();
    let mut idx = vec![0usize; dim];
    loop {
        if idx.iter().sum::<usize>() <= max_degree {
            out.push(idx.clone());
        }
        // increment mixed-radix counter
        let mut i = 0;
        while i < dim {
            idx[i] += 1;
            if idx[i] <= max_degree {
                break;
            }
            idx[i] = 0;
            i += 1;
        }
        if i == dim {
            break;
        }
    }
    out
}

/// Polynomial chaos expansion — a Hermite-polynomial surrogate with
/// analytic Sobol' sensitivity indices.
pub struct Pce {
    /// Multi-indices of the retained basis terms.
    pub indices: Vec<MultiIndex>,
    /// Regression coefficients per term.
    pub coefficients: Vec<f64>,
    /// Total variance of the surrogate (Σ c²).
    pub total_variance: f64,
    /// Sobol' main-effect indices per input dimension (first-order).
    pub sobol_first_order: Vec<f64>,
    /// Sobol' total-effect indices per input dimension.
    pub sobol_total: Vec<f64>,
    /// R² of the surrogate fit (determination coefficient).
    pub r_squared: f64,
}

impl Pce {
    /// Fit a PCE to the given samples.
    ///
    /// `x` inputs must be normalized to the box `bounds` (each column in
    /// [lo, hi]); standardization to N(0,1) happens internally via
    /// `ξ = 2·(x − lo)/(hi − lo) − 1` (an affine map — acceptable for
    /// PCE on bounded boxes).
    #[must_use]
    pub fn fit(x: &[Vec<f64>], y: &[f64], bounds: &[(f64, f64)], max_degree: usize) -> Self {
        let dim = bounds.len();
        let indices = multi_indices(dim, max_degree.min(6));
        let n = x.len();

        // Design matrix: φ_j(x_i) = Π_d H_{α_jd}(ξ_d(x_i))
        let mut design = vec![0.0_f64; n * indices.len()];
        for (i, xi) in x.iter().enumerate() {
            for (j, idx) in indices.iter().enumerate() {
                let mut val = 1.0;
                for (d, &deg) in idx.iter().enumerate() {
                    let (lo, hi) = bounds[d];
                    let xi_d = ((xi[d] - lo) / (hi - lo).max(1e-12))
                        .mul_add(2.0, -1.0)
                        .clamp(-1.0, 1.0);
                    val *= hermite(deg, xi_d);
                }
                design[i * indices.len() + j] = val;
            }
        }

        // Least squares via normal equations: (ΦᵀΦ)c = Φᵀy
        let m = indices.len();
        let mut at_a = vec![0.0_f64; m * m];
        let mut at_y = vec![0.0_f64; m];
        for i in 0..n {
            for a in 0..m {
                at_y[a] = design[i * m + a].mul_add(y[i], at_y[a]);
                for b in 0..m {
                    at_a[a * m + b] = design[i * m + a].mul_add(design[i * m + b], at_a[a * m + b]);
                }
            }
        }
        // Gaussian elimination with partial pivoting
        let coeffs = solve_linear(&at_a, &at_y, m);

        // Variance decomposition
        let total_variance = coeffs.iter().skip(1).map(|c| c * c).sum::<f64>();
        let mut sobol_first = vec![0.0; dim];
        let mut sobol_total = vec![0.0; dim];
        for (j, idx) in indices.iter().enumerate() {
            let c2 = coeffs[j] * coeffs[j];
            for (d, &deg) in idx.iter().enumerate() {
                if deg > 0 {
                    sobol_total[d] += c2;
                    if idx.iter().filter(|&&k| k > 0).count() == 1 {
                        sobol_first[d] += c2;
                    }
                }
            }
        }
        let scale = |v: f64| {
            if total_variance > 1e-300 {
                v / total_variance
            } else {
                0.0
            }
        };
        let sobol_first_order = sobol_first.iter().map(|&v| scale(v)).collect();
        let sobol_total = sobol_total.iter().map(|&v| scale(v)).collect();

        // R²: 1 − SSE/SST
        let mean_y = y.iter().sum::<f64>() / n.max(1) as f64;
        let mut sst = 0.0;
        let mut sse = 0.0;
        for (i, yi) in y.iter().enumerate() {
            let mut pred = 0.0;
            for (j, c) in coeffs.iter().enumerate() {
                pred += c * design[i * m + j];
            }
            sst += (yi - mean_y).powi(2);
            sse += (yi - pred).powi(2);
        }
        let r_squared = if sst > 1e-300 { 1.0 - sse / sst } else { 1.0 };

        Self {
            indices,
            coefficients: coeffs,
            total_variance,
            sobol_first_order,
            sobol_total,
            r_squared,
        }
    }
}

/// Solve `A·c = b` for a symmetric positive-semidefinite matrix by Gaussian
/// elimination with partial pivoting. Returns `c`.
fn solve_linear(a: &[f64], b: &[f64], m: usize) -> Vec<f64> {
    let mut aug = a.to_vec();
    let mut rhs = b.to_vec();
    for col in 0..m {
        // partial pivot
        let mut pivot = col;
        let mut max_val = aug[col * m + col].abs();
        for row in (col + 1)..m {
            let v = aug[row * m + col].abs();
            if v > max_val {
                max_val = v;
                pivot = row;
            }
        }
        if max_val < 1e-12 {
            // rank deficient — leave zeros (surrogate stays usable)
            continue;
        }
        if pivot != col {
            for k in 0..m {
                aug.swap(col * m + k, pivot * m + k);
            }
            rhs.swap(col, pivot);
        }
        let pivot_val = aug[col * m + col];
        for row in (col + 1)..m {
            let factor = aug[row * m + col] / pivot_val;
            if factor == 0.0 {
                continue;
            }
            for k in col..m {
                aug[row * m + k] = factor.mul_add(-aug[col * m + k], aug[row * m + k]);
            }
            rhs[row] = factor.mul_add(-rhs[col], rhs[row]);
        }
    }
    // back substitution
    let mut c = vec![0.0_f64; m];
    for row in (0..m).rev() {
        let mut sum = rhs[row];
        for k in (row + 1)..m {
            sum = aug[row * m + k].mul_add(-c[k], sum);
        }
        let diag = aug[row * m + row];
        c[row] = if diag.abs() > 1e-300 { sum / diag } else { 0.0 };
    }
    c
}

/// Result of a superforecaster run.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SuperforecasterResult {
    /// Best parameters found.
    pub best_params: Vec<f64>,
    /// Best fitness value.
    pub best_fitness: f64,
    /// PCE surrogate diagnostics.
    pub pce_r_squared: f64,
    /// Sobol' first-order indices per dimension.
    pub sobol_first_order: Vec<f64>,
    /// Sobol' total-effect indices per dimension.
    pub sobol_total: Vec<f64>,
    /// Number of LHS initial samples.
    pub n_initial: usize,
    /// Number of BO iterations.
    pub n_bo_iterations: usize,
}

/// Run the full superforecaster pipeline.
///
/// 1. LHS sample `n_initial` points in the box and evaluate the fitness.
/// 2. Fit a PCE (degree `pce_degree`) → Sobol' indices (sensitivity).
/// 3. Warm-start Bayesian optimization with the LHS evaluations and refine
///    for `n_bo_iterations` iterations.
pub fn superforecaster<F>(
    bounds: &[(f64, f64)],
    fitness: F,
    n_initial: usize,
    n_bo_iterations: usize,
    pce_degree: usize,
    seed: u64,
) -> SuperforecasterResult
where
    F: Fn(&[f64]) -> f64 + Clone,
{
    // Phase 1: LHS exploration
    let lhs = latin_hypercube(bounds, n_initial.max(2), seed);
    let mut xs = Vec::with_capacity(n_initial + n_bo_iterations);
    let mut ys = Vec::with_capacity(n_initial + n_bo_iterations);
    for x in &lhs {
        xs.push(x.clone());
        ys.push(fitness(x));
    }

    // Phase 2: PCE surrogate + Sobol' indices
    let pce = Pce::fit(&xs, &ys, bounds, pce_degree);

    // Phase 3: Bayesian optimization from a fresh seed family (the LHS
    // evaluations above are included in the best-point comparison)
    let mut opt = BayesianOptimizer::new(fitness, seed.wrapping_add(1));
    let (_, (best_params, best_fitness)) = opt
        .optimize(bounds, n_initial, n_bo_iterations, 100, 0.01)
        .unwrap_or_else(|_| {
            // Fallback: best LHS point only
            let mut best_idx = 0;
            for (i, y) in ys.iter().enumerate() {
                if y > &ys[best_idx] {
                    best_idx = i;
                }
            }
            (Vec::new(), (xs[best_idx].clone(), ys[best_idx]))
        });

    // Combine: the optimizer's best already covers the LHS phase (same
    // n_initial random-init count), but prefer the LHS point if better.
    let (best_params, best_fitness) = {
        let (mut bp, mut bf) = (best_params, best_fitness);
        for (x, y) in xs.iter().zip(ys.iter()) {
            if *y > bf {
                bp.clone_from(x);
                bf = *y;
            }
        }
        (bp, bf)
    };

    SuperforecasterResult {
        best_params,
        best_fitness,
        pce_r_squared: pce.r_squared,
        sobol_first_order: pce.sobol_first_order,
        sobol_total: pce.sobol_total,
        n_initial: n_initial.max(2),
        n_bo_iterations,
    }
}

#[cfg(test)]
mod tests {
    #![allow(clippy::suboptimal_flops)] // test data expressions, not hot paths
    use super::*;

    #[test]
    fn lhs_has_stratified_coverage() {
        let bounds = [(0.0, 10.0), (0.0, 10.0)];
        let points = latin_hypercube(&bounds, 10, 1);
        assert_eq!(points.len(), 10);
        // Every stratum of dimension 0 must be hit exactly once
        let mut strata: Vec<usize> = points
            .iter()
            .map(|p| ((p[0] / 10.0) * 10.0).floor() as usize)
            .collect();
        strata.sort_unstable();
        assert_eq!(strata, vec![0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
    }

    #[test]
    fn pce_recovers_linear_surface() {
        // y = 2x0 + 3x1 over [0,1]² — PCE should be near-perfect
        let bounds = [(0.0, 1.0), (0.0, 1.0)];
        let xs: Vec<Vec<f64>> = (0..50)
            .map(|i| vec![f64::from(i % 10) / 9.0, f64::from(i / 10) / 4.0])
            .collect();
        let ys: Vec<f64> = xs.iter().map(|x| 2.0 * x[0] + 3.0 * x[1]).collect();
        let pce = Pce::fit(&xs, &ys, &bounds, 2);
        assert!(pce.r_squared > 0.99, "R² = {}", pce.r_squared);
        // Sensitivity: both variables matter, similar magnitude
        assert!(pce.sobol_first_order[0] > 0.1);
        assert!(pce.sobol_first_order[1] > 0.1);
    }

    #[test]
    fn pce_detects_dominant_variable() {
        // y = 5x0 + tiny noise in x1 → Sobol should rank x0 first
        let bounds = [(0.0, 1.0), (0.0, 1.0)];
        let xs: Vec<Vec<f64>> = (0..40)
            .map(|i| vec![f64::from(i % 8) / 7.0, f64::from(i / 8) / 4.0])
            .collect();
        let ys: Vec<f64> = xs.iter().map(|x| 5.0 * x[0] + 0.1 * x[1]).collect();
        let pce = Pce::fit(&xs, &ys, &bounds, 2);
        assert!(
            pce.sobol_first_order[0] > pce.sobol_first_order[1],
            "S0 = {}, S1 = {}",
            pce.sobol_first_order[0],
            pce.sobol_first_order[1]
        );
    }

    #[test]
    fn multi_indices_total_degree() {
        let idx = multi_indices(2, 2);
        // 1 + 2 + 3 = 6 terms for dim=2, degree ≤ 2
        assert_eq!(idx.len(), 6);
        assert!(idx.iter().all(|m| m.iter().sum::<usize>() <= 2));
    }

    #[test]
    fn superforecaster_finds_optimum_and_sensitivities() {
        let bounds = [(0.0, 10.0)];
        let result = superforecaster(
            &bounds,
            |x: &[f64]| -(x[0] - 3.0).powi(2) + 5.0,
            8,
            10,
            3,
            42,
        );
        assert!(
            (result.best_params[0] - 3.0).abs() < 0.5,
            "best x = {}",
            result.best_params[0]
        );
        assert!((result.best_fitness - 5.0).abs() < 0.5);
        assert!(
            result.sobol_first_order[0] > 0.9,
            "S = {}",
            result.sobol_first_order[0]
        );
        assert!(result.pce_r_squared > 0.9, "R² = {}", result.pce_r_squared);
    }
}
