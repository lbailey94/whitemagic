//! Sensitivity analysis and surrogate modeling for high-dimensional MC.
//!
//! Implements:
//! - Polynomial Chaos Expansion (PCE) via ordinary least squares
//! - Sobol sensitivity indices (first-order and total-order) via Saltelli's method
//! - Surrogate evaluation for fast response surface queries
//! - Linear regression for sensitivity analysis

use rand::{RngCore, SeedableRng};
use rand_xoshiro::Xoshiro256PlusPlus;
use rayon::prelude::*;

/// A fitted Polynomial Chaos Expansion surrogate model.
///
/// Uses multivariate orthogonal polynomials (Hermite for Gaussian inputs,
/// Legendre for uniform inputs) up to a given total order.
#[derive(Debug, Clone)]
pub struct PCESurrogate {
    /// Number of input dimensions
    pub dim: usize,
    /// Maximum total polynomial order
    pub max_order: usize,
    /// Distribution type: "uniform" or "gaussian"
    pub dist_type: String,
    /// Fitted coefficients (one per basis term)
    pub coefficients: Vec<f64>,
    /// Multi-indices for each basis term (each is a Vec of length dim)
    pub multi_indices: Vec<Vec<usize>>,
}

impl PCESurrogate {
    /// Fit a PCE surrogate to (X, Y) data using ordinary least squares.
    ///
    /// `x_data` is an n×d matrix (n samples, d dimensions).
    /// `y_data` is a length-n vector of responses.
    /// `max_order` is the maximum total polynomial order.
    /// `dist_type` is "uniform" or "gaussian".
    pub fn fit(
        x_data: &[Vec<f64>],
        y_data: &[f64],
        max_order: usize,
        dist_type: &str,
    ) -> Self {
        let n = x_data.len();
        let d = if n > 0 { x_data[0].len() } else { 0 };

        // Generate multi-indices up to max_order (total order truncation)
        let multi_indices = generate_multi_indices(d, max_order);
        let n_basis = multi_indices.len();

        // Build the design matrix: Psi[i][j] = prod_k phi_jk(x_i_k)
        let mut psi = vec![vec![0.0f64; n_basis]; n];
        for i in 0..n {
            for j in 0..n_basis {
                psi[i][j] = eval_basis(&x_data[i], &multi_indices[j], dist_type);
            }
        }

        // Solve least squares: beta = (Psi^T Psi)^-1 Psi^T y
        let coefficients = solve_least_squares(&psi, y_data, n_basis);

        Self {
            dim: d,
            max_order,
            dist_type: dist_type.to_string(),
            coefficients,
            multi_indices,
        }
    }

    /// Evaluate the surrogate at a new point.
    pub fn evaluate(&self, x: &[f64]) -> f64 {
        let mut result = 0.0;
        for (j, idx) in self.multi_indices.iter().enumerate() {
            result += self.coefficients[j] * eval_basis(x, idx, &self.dist_type);
        }
        result
    }

    /// Evaluate the surrogate at multiple points (parallel).
    pub fn evaluate_batch(&self, x_data: &[Vec<f64>]) -> Vec<f64> {
        x_data.par_iter().map(|x| self.evaluate(x)).collect()
    }

    /// Get the number of basis terms.
    pub fn n_terms(&self) -> usize {
        self.multi_indices.len()
    }

    /// Compute the coefficient of determination (R²) on training data.
    pub fn r_squared(&self, x_data: &[Vec<f64>], y_data: &[f64]) -> f64 {
        if y_data.is_empty() {
            return 0.0;
        }
        let y_mean = y_data.iter().sum::<f64>() / y_data.len() as f64;
        let predictions: Vec<f64> = self.evaluate_batch(x_data);
        let ss_res: f64 = y_data
            .iter()
            .zip(predictions.iter())
            .map(|(y, p)| (y - p).powi(2))
            .sum();
        let ss_tot: f64 = y_data.iter().map(|y| (y - y_mean).powi(2)).sum();
        if ss_tot < 1e-15 {
            return 1.0;
        }
        1.0 - ss_res / ss_tot
    }
}

/// Generate all multi-indices with total order <= max_order in d dimensions.
/// E.g., for d=2, max_order=2: [0,0], [1,0], [0,1], [2,0], [1,1], [0,2]
fn generate_multi_indices(d: usize, max_order: usize) -> Vec<Vec<usize>> {
    if d == 0 {
        return vec![vec![]];
    }
    let mut result = Vec::new();
    let mut current = vec![0usize; d];
    loop {
        let total: usize = current.iter().sum();
        if total <= max_order {
            result.push(current.clone());
        }
        // Increment the multi-index (odometer)
        let mut carry = true;
        for i in 0..d {
            if carry {
                current[i] += 1;
                if current[i] > max_order {
                    current[i] = 0;
                    carry = true;
                } else {
                    carry = false;
                }
            }
        }
        if carry {
            break;
        }
    }
    // Sort by total order then lexicographically
    result.sort_by(|a, b| {
        let ta: usize = a.iter().sum();
        let tb: usize = b.iter().sum();
        ta.cmp(&tb).then_with(|| a.cmp(b))
    });
    result
}

/// Evaluate a single basis function: prod_k phi_k(x_k) where phi_k has order idx[k].
fn eval_basis(x: &[f64], idx: &[usize], dist_type: &str) -> f64 {
    let mut result = 1.0;
    for k in 0..x.len() {
        if k < idx.len() {
            result *= match dist_type {
                "gaussian" => hermite_poly(idx[k], x[k]),
                _ => legendre_poly(idx[k], x[k]),
            };
        }
    }
    result
}

/// Probabilist's Hermite polynomial He_n(x) (orthogonal w.r.t. N(0,1)).
/// He_0=1, He_1=x, He_2=x²-1, He_3=x³-3x, ...
fn hermite_poly(n: usize, x: f64) -> f64 {
    match n {
        0 => 1.0,
        1 => x,
        _ => {
            let mut h_prev = 1.0;
            let mut h_curr = x;
            for k in 1..n {
                let h_next = x * h_curr - k as f64 * h_prev;
                h_prev = h_curr;
                h_curr = h_next;
            }
            h_curr
        }
    }
}

/// Legendre polynomial P_n(x) (orthogonal w.r.t. Uniform[-1,1]).
/// P_0=1, P_1=x, P_2=(3x²-1)/2, ...
/// For uniform [0,1] inputs, we map x to 2x-1.
fn legendre_poly(n: usize, x: f64) -> f64 {
    // Map [0,1] to [-1,1]
    let t = 2.0 * x - 1.0;
    match n {
        0 => 1.0,
        1 => t,
        _ => {
            let mut p_prev = 1.0;
            let mut p_curr = t;
            for k in 1..n {
                let p_next = ((2 * k + 1) as f64 * t * p_curr - k as f64 * p_prev)
                    / (k + 1) as f64;
                p_prev = p_curr;
                p_curr = p_next;
            }
            p_curr
        }
    }
}

/// Solve least squares problem: beta = (A^T A)^-1 A^T b
/// Using normal equations with Gaussian elimination.
fn solve_least_squares(a: &[Vec<f64>], b: &[f64], n_params: usize) -> Vec<f64> {
    let n = a.len();
    if n == 0 || n_params == 0 {
        return vec![0.0; n_params];
    }

    // Compute A^T A (n_params × n_params)
    let mut ata = vec![vec![0.0f64; n_params]; n_params];
    let mut atb = vec![0.0f64; n_params];

    for i in 0..n {
        for j in 0..n_params {
            atb[j] += a[i][j] * b[i];
            for k in 0..n_params {
                ata[j][k] += a[i][j] * a[i][k];
            }
        }
    }

    // Regularize: add small diagonal for numerical stability
    let reg = 1e-10;
    for j in 0..n_params {
        ata[j][j] += reg;
    }

    // Gaussian elimination with partial pivoting
    for col in 0..n_params {
        // Find pivot
        let mut max_row = col;
        let mut max_val = ata[col][col].abs();
        for row in (col + 1)..n_params {
            if ata[row][col].abs() > max_val {
                max_val = ata[row][col].abs();
                max_row = row;
            }
        }
        if max_val < 1e-15 {
            continue;
        }
        if max_row != col {
            ata.swap(col, max_row);
            atb.swap(col, max_row);
        }

        // Eliminate
        for row in (col + 1)..n_params {
            let factor = ata[row][col] / ata[col][col];
            for k in col..n_params {
                ata[row][k] -= factor * ata[col][k];
            }
            atb[row] -= factor * atb[col];
        }
    }

    // Back substitution
    let mut beta = vec![0.0f64; n_params];
    for i in (0..n_params).rev() {
        let mut sum = atb[i];
        for j in (i + 1)..n_params {
            sum -= ata[i][j] * beta[j];
        }
        beta[i] = if ata[i][i].abs() > 1e-15 {
            sum / ata[i][i]
        } else {
            0.0
        };
    }

    beta
}

/// Sobol sensitivity indices via Saltelli's sampling strategy.
///
/// Given a fitness function and parameter ranges, computes first-order (S_i)
/// and total-order (S_Ti) Sobol indices.
///
/// Uses N(2d+2) function evaluations: N base samples, N for each first-order,
/// N for each total-order.
///
/// Returns (first_order: Vec<f64>, total_order: Vec<f64>).
pub fn sobol_indices(
    n_base: usize,
    param_ranges: &[(f64, f64)],
    seed: u64,
    fitness_fn: impl Fn(&[f64]) -> f64 + Sync,
) -> (Vec<f64>, Vec<f64>) {
    let d = param_ranges.len();
    if d == 0 || n_base == 0 {
        return (Vec::new(), Vec::new());
    }

    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);

    // Generate two independent sample matrices A and B
    let scale = |u: f64, i: usize| -> f64 {
        let (lo, hi) = param_ranges[i];
        lo + u * (hi - lo)
    };

    let mut a_samples = vec![vec![0.0f64; d]; n_base];
    let mut b_samples = vec![vec![0.0f64; d]; n_base];

    for i in 0..n_base {
        for j in 0..d {
            let ua = rng.next_u64() as f64 / u64::MAX as f64;
            let ub = rng.next_u64() as f64 / u64::MAX as f64;
            a_samples[i][j] = scale(ua, j);
            b_samples[i][j] = scale(ub, j);
        }
    }

    // Evaluate f(A) and f(B)
    let f_a: Vec<f64> = a_samples.par_iter().map(|x| fitness_fn(x)).collect();
    let f_b: Vec<f64> = b_samples.par_iter().map(|x| fitness_fn(x)).collect();

    // For each dimension j, create mixed matrix AB_j (A with column j from B)
    // and compute f(AB_j)
    let mut first_order = vec![0.0f64; d];
    let mut total_order = vec![0.0f64; d];

    let f_mean: f64 = f_a.iter().sum::<f64>() / n_base as f64;
    let f_var: f64 = f_a
        .iter()
        .map(|f| (*f - f_mean).powi(2))
        .sum::<f64>()
        / n_base as f64;

    if f_var < 1e-15 {
        return (first_order, total_order);
    }

    for j in 0..d {
        // AB_j: take A, replace column j with B's column j
        let ab_j: Vec<Vec<f64>> = a_samples
            .iter()
            .zip(b_samples.iter())
            .map(|(a, b)| {
                let mut mixed = a.clone();
                mixed[j] = b[j];
                mixed
            })
            .collect();

        let f_ab: Vec<f64> = ab_j.par_iter().map(|x| fitness_fn(x)).collect();

        // First-order (Saltelli 2010): S_j = V_j / V
        // V_j ≈ (1/N) * sum(f_B * f_AB_j) - f_mean^2
        let v_j: f64 = f_b
            .iter()
            .zip(f_ab.iter())
            .map(|(fb, fab)| fb * fab)
            .sum::<f64>()
            / n_base as f64
            - f_mean * f_mean;

        // Total-order: S_Tj = E[f_B * f_AB_j] - f_mean^2 ... actually
        // S_Tj = (1/(2N)) * sum((f_A - f_AB_j)^2) / V
        let s_tj: f64 = f_a
            .iter()
            .zip(f_ab.iter())
            .map(|(fa, fab)| (fa - fab).powi(2))
            .sum::<f64>()
            / (2.0 * n_base as f64)
            / f_var;

        first_order[j] = (v_j / f_var).max(0.0);
        total_order[j] = s_tj.max(0.0);
    }

    (first_order, total_order)
}

/// Pearson correlation between a parameter and fitness values.
/// Useful for quick linear sensitivity assessment.
pub fn pearson_correlation(x: &[f64], y: &[f64]) -> f64 {
    let n = x.len() as f64;
    if n == 0.0 {
        return 0.0;
    }
    let x_mean = x.iter().sum::<f64>() / n;
    let y_mean = y.iter().sum::<f64>() / n;

    let mut cov = 0.0;
    let mut var_x = 0.0;
    let mut var_y = 0.0;

    for i in 0..x.len() {
        let dx = x[i] - x_mean;
        let dy = y[i] - y_mean;
        cov += dx * dy;
        var_x += dx * dx;
        var_y += dy * dy;
    }

    let denom = (var_x * var_y).sqrt();
    if denom < 1e-15 {
        0.0
    } else {
        cov / denom
    }
}

/// Compute Pearson correlations for all parameters vs fitness.
/// Returns a Vec of (param_index, correlation) sorted by absolute correlation descending.
pub fn parameter_sensitivity(
    samples: &[Vec<f64>],
    fitness: &[f64],
) -> Vec<(usize, f64)> {
    if samples.is_empty() || fitness.is_empty() {
        return Vec::new();
    }
    let d = samples[0].len();
    let mut correlations: Vec<(usize, f64)> = Vec::with_capacity(d);

    for j in 0..d {
        let col: Vec<f64> = samples.iter().map(|s| s[j]).collect();
        correlations.push((j, pearson_correlation(&col, fitness)));
    }

    correlations.sort_by(|a, b| {
        b.1.abs()
            .partial_cmp(&a.1.abs())
            .unwrap_or(std::cmp::Ordering::Equal)
    });

    correlations
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hermite_poly() {
        assert!((hermite_poly(0, 1.5) - 1.0).abs() < 1e-10);
        assert!((hermite_poly(1, 1.5) - 1.5).abs() < 1e-10);
        assert!((hermite_poly(2, 1.5) - (1.5 * 1.5 - 1.0)).abs() < 1e-10);
        assert!((hermite_poly(3, 1.5) - (1.5 * 1.5 * 1.5 - 3.0 * 1.5)).abs() < 1e-10);
    }

    #[test]
    fn test_legendre_poly() {
        assert!((legendre_poly(0, 0.5) - 1.0).abs() < 1e-10);
        assert!((legendre_poly(1, 0.5) - 0.0).abs() < 1e-10); // 2*0.5-1 = 0
        assert!((legendre_poly(2, 1.0) - 1.0).abs() < 1e-10); // (3*1-1)/2 = 1
    }

    #[test]
    fn test_generate_multi_indices() {
        let idx = generate_multi_indices(2, 2);
        assert_eq!(idx.len(), 6); // (0,0), (1,0), (0,1), (2,0), (1,1), (0,2)
        assert_eq!(idx[0], vec![0, 0]);
        // After sorting by total order then lexicographically: [1,0] and [0,1] both have total=1
        // [0,1] < [1,0] lexicographically
        assert_eq!(idx[1], vec![0, 1]);
        assert_eq!(idx[2], vec![1, 0]);
    }

    #[test]
    fn test_pce_fit_linear() {
        // y = 2*x1 + 3*x2 (linear in uniform inputs)
        let x_data: Vec<Vec<f64>> = (0..200)
            .map(|i| {
                vec![
                    ((i * 7) % 100) as f64 / 100.0,
                    ((i * 13) % 100) as f64 / 100.0,
                ]
            })
            .collect();
        let y_data: Vec<f64> = x_data
            .iter()
            .map(|x| 2.0 * x[0] + 3.0 * x[1])
            .collect();

        let pce = PCESurrogate::fit(&x_data, &y_data, 1, "uniform");
        let r2 = pce.r_squared(&x_data, &y_data);
        assert!(r2 > 0.95, "R² should be high for linear model, got {}", r2);

        // Evaluate at a new point
        let pred = pce.evaluate(&[0.5, 0.5]);
        let expected = 2.0 * 0.5 + 3.0 * 0.5;
        assert!(
            (pred - expected).abs() < 0.1,
            "PCE prediction should be close, got {} vs expected {}",
            pred,
            expected
        );
    }

    #[test]
    fn test_pce_fit_quadratic() {
        // y = x1^2 + x2^2
        let x_data: Vec<Vec<f64>> = (0..300)
            .map(|i| {
                vec![
                    ((i * 17) % 100) as f64 / 100.0,
                    ((i * 23) % 100) as f64 / 100.0,
                ]
            })
            .collect();
        let y_data: Vec<f64> = x_data.iter().map(|x| x[0] * x[0] + x[1] * x[1]).collect();

        let pce = PCESurrogate::fit(&x_data, &y_data, 2, "uniform");
        let r2 = pce.r_squared(&x_data, &y_data);
        assert!(r2 > 0.95, "R² should be high for quadratic, got {}", r2);
    }

    #[test]
    fn test_pce_evaluate_batch() {
        let x_data: Vec<Vec<f64>> = (0..100)
            .map(|i| vec![(i as f64) / 100.0, (i as f64) / 200.0])
            .collect();
        let y_data: Vec<f64> = x_data.iter().map(|x| x[0] + 2.0 * x[1]).collect();

        let pce = PCESurrogate::fit(&x_data, &y_data, 1, "uniform");
        let test_points = vec![vec![0.3, 0.4], vec![0.7, 0.1]];
        let preds = pce.evaluate_batch(&test_points);
        assert_eq!(preds.len(), 2);
    }

    #[test]
    fn test_sobol_indices_linear() {
        // For y = x1 (only x1 matters), S_1 should be ~1, S_2 should be ~0
        let ranges = vec![(0.0, 1.0), (0.0, 1.0)];
        let (first, total) = sobol_indices(1000, &ranges, 42, |x| x[0]);

        assert!(
            first[0] > 0.8,
            "S_1 should be near 1 for y=x1, got {}",
            first[0]
        );
        assert!(
            first[1] < 0.1,
            "S_2 should be near 0 for y=x1, got {}",
            first[1]
        );
        assert!(
            total[0] > 0.8,
            "S_T1 should be near 1, got {}",
            total[0]
        );
    }

    #[test]
    fn test_sobol_indices_equal() {
        // For y = x1 + x2, both should have ~equal sensitivity
        let ranges = vec![(0.0, 1.0), (0.0, 1.0)];
        let (first, _total) = sobol_indices(2000, &ranges, 42, |x| x[0] + x[1]);

        // Both should be roughly 0.5 (Saltelli estimator has finite-sample noise)
        assert!(
            (first[0] - 0.5).abs() < 0.2,
            "S_1 should be near 0.5, got {}",
            first[0]
        );
        assert!(
            (first[1] - 0.5).abs() < 0.2,
            "S_2 should be near 0.5, got {}",
            first[1]
        );
    }

    #[test]
    fn test_pearson_correlation() {
        let x = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let y = vec![2.0, 4.0, 6.0, 8.0, 10.0];
        let r = pearson_correlation(&x, &y);
        assert!((r - 1.0).abs() < 1e-10, "perfect correlation should be 1, got {}", r);
    }

    #[test]
    fn test_pearson_correlation_negative() {
        let x = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let y = vec![5.0, 4.0, 3.0, 2.0, 1.0];
        let r = pearson_correlation(&x, &y);
        assert!((r + 1.0).abs() < 1e-10, "perfect negative correlation should be -1, got {}", r);
    }

    #[test]
    fn test_parameter_sensitivity() {
        let samples = vec![
            vec![0.1, 0.9],
            vec![0.5, 0.5],
            vec![0.9, 0.1],
            vec![0.3, 0.7],
            vec![0.7, 0.3],
        ];
        let fitness = vec![0.1, 0.5, 0.9, 0.3, 0.7]; // y = x[0]
        let sens = parameter_sensitivity(&samples, &fitness);
        // x[0] should have highest abs correlation (1.0)
        // x[1] has perfect negative correlation (-1.0), same abs
        // so x[0] should be first (stable sort preserves order for ties)
        assert_eq!(sens[0].0, 0);
        assert!(sens[0].1.abs() >= sens[1].1.abs());
    }

    #[test]
    fn test_solve_least_squares_simple() {
        // y = 2 + 3x
        let a = vec![
            vec![1.0, 0.0],
            vec![1.0, 1.0],
            vec![1.0, 2.0],
            vec![1.0, 3.0],
        ];
        let b = vec![2.0, 5.0, 8.0, 11.0];
        let beta = solve_least_squares(&a, &b, 2);
        assert!((beta[0] - 2.0).abs() < 1e-6, "intercept should be 2, got {}", beta[0]);
        assert!((beta[1] - 3.0).abs() < 1e-6, "slope should be 3, got {}", beta[1]);
    }
}
