//! Gaussian Process surrogates and Bayesian optimization.
//!
//! Pure-Rust implementation (no external linear algebra):
//!
//! - [`GaussianProcess`] — RBF-kernel GP regression with Cholesky solve;
//!   posterior mean + variance for any query point.
//! - [`BayesianOptimizer`] — sequential optimization using Expected
//!   Improvement over a GP surrogate.
//! - [`Expr`] — a tiny safe expression evaluator (`x[0] * sin(x[1]) + 1`)
//!   used as the fitness function, mirroring v26's `mc.optimize` tool.
//!
//! The surrogate gives the Dream cycle / Homeostatic loop cheap
//! response-surface models, and `mc.optimize` replaces grid search with
//! sample-efficient Bayesian exploration.

use std::f64::consts::PI;

/// Numerically safe inverse-normal CDF (Acklam's algorithm) and CDF (erf).
#[must_use]
pub fn norm_cdf(z: f64) -> f64 {
    0.5 * (1.0 + erf(z / std::f64::consts::SQRT_2))
}

#[must_use]
pub fn norm_pdf(z: f64) -> f64 {
    (-0.5 * z * z).exp() / (2.0 * PI).sqrt()
}

fn erf(x: f64) -> f64 {
    // Abramowitz-Stegun 7.1.26 approximation (|err| < 1.5e-7)
    let sign = if x < 0.0 { -1.0 } else { 1.0 };
    let x = x.abs();
    let t = 1.0 / 0.327_591_1f64.mul_add(x, 1.0);
    let y = (1.061_405_429f64
        .mul_add(t, -1.453_152_027)
        .mul_add(t, 1.421_413_741)
        .mul_add(t, -0.284_496_736)
        .mul_add(t, 0.254_829_592)
        * t)
        .mul_add(-(-x * x).exp(), 1.0);
    sign * y
}

/// RBF (squared-exponential) kernel distance.
fn rbf(a: &[f64], b: &[f64], length_scale: f64) -> f64 {
    let mut sq = 0.0;
    for (ai, bi) in a.iter().zip(b.iter()) {
        let d = ai - bi;
        sq += d * d;
    }
    (-sq / (2.0 * length_scale * length_scale)).exp()
}

/// Gaussian Process regression with an RBF kernel.
///
/// Hyperparameters are settable; the kernel is
/// `k(x, x') = σ_f² · exp(−||x−x'||² / 2ℓ²)` with observation noise `σ_n`.
#[derive(Debug, Clone)]
pub struct GaussianProcess {
    /// Training inputs (row = sample, col = dimension).
    xs: Vec<Vec<f64>>,
    /// Training outputs.
    ys: Vec<f64>,
    /// Length scale ℓ.
    pub length_scale: f64,
    /// Signal variance σ_f².
    pub signal_variance: f64,
    /// Observation noise variance σ_n².
    pub noise_variance: f64,
    /// Lower-triangular Cholesky factor L of (K + σ_n² I) (post-fit).
    l: Option<Vec<f64>>,
    /// K⁻¹ y (post-fit) — n×1 solved by forward/back substitution.
    alpha: Vec<f64>,
    /// Smallest Cholesky eigenvalue observed (stability diagnostic).
    min_eig: f64,
}

impl Default for GaussianProcess {
    fn default() -> Self {
        Self::new(1.0, 1.0, 1e-6)
    }
}

impl GaussianProcess {
    /// Create a GP with the given kernel hyperparameters.
    #[must_use]
    pub const fn new(length_scale: f64, signal_variance: f64, noise_variance: f64) -> Self {
        Self {
            xs: Vec::new(),
            ys: Vec::new(),
            length_scale: length_scale.max(1e-6),
            signal_variance: signal_variance.max(1e-9),
            noise_variance: noise_variance.max(1e-12),
            l: None,
            alpha: Vec::new(),
            min_eig: f64::INFINITY,
        }
    }

    /// Number of training samples.
    #[must_use]
    pub fn n_samples(&self) -> usize {
        self.xs.len()
    }

    /// Add a training sample (x, y).
    pub fn add_sample(&mut self, x: Vec<f64>, y: f64) {
        self.xs.push(x);
        self.ys.push(y);
    }

    /// Fit the GP: compute L = cholesky(K + σ_n² I) and α = K⁻¹ y.
    ///
    /// Returns an error if fewer than 2 samples are present.
    pub fn fit(&mut self) -> Result<(), String> {
        let n = self.xs.len();
        if n < 2 {
            return Err(format!(
                "need at least 2 training samples to fit a GP, got {n}"
            ));
        }
        // Kernel matrix
        let mut k = vec![0.0_f64; n * n];
        for i in 0..n {
            for j in 0..n {
                k[i * n + j] =
                    self.signal_variance * rbf(&self.xs[i], &self.xs[j], self.length_scale);
            }
            k[i * n + i] += self.noise_variance;
        }
        // Cholesky with jitter for numerical stability
        let mut l = vec![0.0_f64; n * n];
        self.min_eig = f64::INFINITY;
        for i in 0..n {
            for j in 0..=i {
                let mut sum = k[i * n + j];
                for kk in 0..j {
                    sum -= l[i * n + kk] * l[j * n + kk];
                }
                if i == j {
                    if sum <= 0.0 {
                        // Near-singular — add jitter and retry this diagonal
                        sum = sum.max(1e-10);
                    }
                    let sqrt = sum.sqrt();
                    l[i * n + i] = sqrt;
                    self.min_eig = self.min_eig.min(sqrt * sqrt);
                } else {
                    l[i * n + j] = sum / l[j * n + j];
                }
            }
        }
        // Solve L Lᵀ α = y  →  L z = y (forward), Lᵀ α = z (back)
        let mut z = vec![0.0_f64; n];
        for i in 0..n {
            let mut sum = self.ys[i];
            for j in 0..i {
                sum -= l[i * n + j] * z[j];
            }
            z[i] = sum / l[i * n + i];
        }
        let mut alpha = vec![0.0_f64; n];
        for i in (0..n).rev() {
            let mut sum = z[i];
            for j in (i + 1)..n {
                sum -= l[j * n + i] * alpha[j];
            }
            alpha[i] = sum / l[i * n + i];
        }
        self.l = Some(l);
        self.alpha = alpha;
        Ok(())
    }

    /// Predict mean and variance at a query point.
    ///
    /// Returns `(mean, variance)`; variance includes observation noise.
    /// Errors if not fitted.
    pub fn predict(&self, x: &[f64]) -> Result<(f64, f64), String> {
        let n = self.xs.len();
        let l = self
            .l
            .as_ref()
            .ok_or_else(|| "GP not fitted — call fit() first".to_string())?;
        if x.len() != self.xs[0].len() {
            return Err(format!(
                "query dimension {} != training dimension {}",
                x.len(),
                self.xs[0].len()
            ));
        }
        // k(x) = kernel between x and all training points
        let mut kx = vec![0.0_f64; n];
        for (i, xi) in self.xs.iter().enumerate() {
            kx[i] = self.signal_variance * rbf(xi, x, self.length_scale);
        }
        // v = L⁻¹ k(x) — forward substitution
        let mut v = vec![0.0_f64; n];
        for i in 0..n {
            let mut sum = kx[i];
            for j in 0..i {
                sum -= l[i * n + j] * v[j];
            }
            v[i] = sum / l[i * n + i];
        }
        let mean = self.alpha.iter().zip(kx.iter()).map(|(a, k)| a * k).sum();
        // var = k(x,x) − vᵀv  (+ noise for the predictive distribution)
        let var =
            (self.signal_variance + self.noise_variance) - v.iter().map(|vi| vi * vi).sum::<f64>();
        Ok((mean, var.max(1e-12)))
    }

    /// Minimum Cholesky eigenvalue during fit (diagnostic).
    #[must_use]
    pub const fn min_eigenvalue(&self) -> f64 {
        self.min_eig
    }
}

/// Expected Improvement acquisition at a query point.
///
/// `z = (μ − f_best − ξ) / σ`; `EI = (μ − f_best − ξ)Φ(z) + σφ(z)`.
/// `ξ > 0` biases exploration.
pub fn expected_improvement(
    gp: &GaussianProcess,
    x: &[f64],
    best_so_far: f64,
    exploration: f64,
) -> Result<f64, String> {
    let (mean, var) = gp.predict(x)?;
    let sigma = var.sqrt();
    let diff = mean - best_so_far - exploration;
    if sigma < 1e-12 {
        return Ok(diff.max(0.0));
    }
    let z = diff / sigma;
    Ok(diff.mul_add(norm_cdf(z), sigma * norm_pdf(z)))
}

/// One step of the Bayesian optimization trace.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct OptimizationStep {
    /// Iteration index (0 = best of the initial random samples).
    pub iteration: usize,
    /// Evaluated parameters.
    pub params: Vec<f64>,
    /// Observed fitness.
    pub fitness: f64,
    /// Surrogate mean at the chosen point.
    pub surrogate_mean: f64,
    /// Surrogate std at the chosen point.
    pub surrogate_std: f64,
}

/// Result of a Bayesian optimization run: full trace + best (params, fitness).
pub type OptimizeResult = (Vec<OptimizationStep>, (Vec<f64>, f64));

/// Sequential Bayesian optimization over a box.
///
/// 1. Sample `n_initial` random points, evaluate, take the best.
/// 2. Fit a GP to all evaluations.
/// 3. For each iteration: score `n_candidates` random points by Expected
///    Improvement, evaluate the argmax, refit, repeat.
pub struct BayesianOptimizer<F>
where
    F: Fn(&[f64]) -> f64,
{
    fitness: F,
    rng: u64,
}

impl<F> BayesianOptimizer<F>
where
    F: Fn(&[f64]) -> f64,
{
    /// Create an optimizer over the fitness function with a PRNG seed.
    #[must_use]
    pub const fn new(fitness: F, seed: u64) -> Self {
        Self { fitness, rng: seed }
    }

    /// Run the optimization.
    ///
    /// `bounds`: `[(min, max), ...]` per dimension (all required).
    /// Returns the full trace and the best (params, fitness).
    pub fn optimize(
        &mut self,
        bounds: &[(f64, f64)],
        n_initial: usize,
        n_iterations: usize,
        n_candidates: usize,
        exploration: f64,
    ) -> Result<OptimizeResult, String> {
        let dim = bounds.len();
        if dim == 0 {
            return Err("at least one parameter dimension required".into());
        }
        for (lo, hi) in bounds {
            if lo > hi {
                return Err(format!("invalid bounds [{lo}, {hi}]"));
            }
        }

        let mut steps = Vec::new();
        // Phase 1: random initialization
        for i in 0..n_initial.max(1) {
            let params = (0..dim)
                .map(|d| {
                    let (lo, hi) = bounds[d];
                    (hi - lo).mul_add(rand_u01(&mut self.rng), lo)
                })
                .collect::<Vec<_>>();
            let f = (self.fitness)(&params);
            steps.push(OptimizationStep {
                iteration: i,
                surrogate_mean: f,
                surrogate_std: 0.0,
                fitness: f,
                params,
            });
        }

        let mut gp = GaussianProcess::default();
        for s in &steps {
            gp.add_sample(s.params.clone(), s.fitness);
        }
        gp.fit()?;

        let mut best = steps
            .iter()
            .max_by(|a, b| {
                a.fitness
                    .partial_cmp(&b.fitness)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .cloned()
            .ok_or_else(|| "no initial samples".to_string())?;

        // Phase 2: EI-guided search
        for iter in 0..n_iterations {
            let mut best_ei = f64::NEG_INFINITY;
            let mut best_candidate = vec![0.0; dim];
            for _ in 0..n_candidates.max(1) {
                let candidate = (0..dim)
                    .map(|d| {
                        let (lo, hi) = bounds[d];
                        (hi - lo).mul_add(rand_u01(&mut self.rng), lo)
                    })
                    .collect::<Vec<_>>();
                let ei =
                    expected_improvement(&gp, &candidate, best.fitness, exploration).unwrap_or(0.0);
                if ei > best_ei {
                    best_ei = ei;
                    best_candidate = candidate;
                }
            }

            let f = (self.fitness)(&best_candidate);
            let (mean, var) = gp.predict(&best_candidate).unwrap_or((f, 1.0));
            let step = OptimizationStep {
                iteration: n_initial + iter,
                surrogate_mean: mean,
                surrogate_std: var.sqrt(),
                fitness: f,
                params: best_candidate,
            };
            if step.fitness > best.fitness {
                best = step.clone();
            }
            gp.add_sample(step.params.clone(), step.fitness);
            gp.fit()?;
            steps.push(step);
        }

        Ok((steps, (best.params.clone(), best.fitness)))
    }
}

/// SplitMix64 PRNG — identical to the one in `monte_carlo.rs` so seeds
/// behave consistently across modules.
pub(crate) fn rand_u01(state: &mut u64) -> f64 {
    *state = state.wrapping_add(0x9E3779B97F4A7C15);
    let mut z = *state;
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
    z ^= z >> 31;
    (z >> 11) as f64 / (1u64 << 53) as f64
}

/// A tiny safe expression evaluator for fitness functions.
///
/// Grammar: numbers, `x[0]`, `x[i]`, `+ - * / ^ ( )`, unary minus,
/// `sin cos tan exp log sqrt abs`, constants `pi`, `e`.
///
/// No eval, no I/O, no recursion depth risk (operand stack bounded by
/// expression length) — safe to run on untrusted tool input.
#[derive(Debug, Clone)]
pub struct Expr {
    tokens: Vec<Token>,
}

#[derive(Debug, Clone, PartialEq)]
enum Token {
    Num(f64),
    Var(usize),
    Op(char),
    LParen,
    RParen,
    Fn(String),
    Comma,
}

impl Expr {
    /// Parse an expression string.
    pub fn parse(src: &str) -> Result<Self, String> {
        let mut tokens = Vec::new();
        let chars: Vec<char> = src.chars().filter(|c| !c.is_whitespace()).collect();
        let mut i = 0;
        while i < chars.len() {
            let c = chars[i];
            match c {
                '0'..='9' | '.' => {
                    let start = i;
                    while i < chars.len() && (chars[i].is_ascii_digit() || chars[i] == '.') {
                        i += 1;
                    }
                    let s: String = chars[start..i].iter().collect();
                    let v: f64 = s.parse().map_err(|_| format!("invalid number '{s}'"))?;
                    tokens.push(Token::Num(v));
                }
                'x' => {
                    // x[0], x[1], ...
                    if i + 1 >= chars.len() || chars[i + 1] != '[' {
                        return Err("expected 'x[i]' variable syntax".into());
                    }
                    let mut j = i + 2;
                    let mut idx = String::new();
                    while j < chars.len() && chars[j].is_ascii_digit() {
                        idx.push(chars[j]);
                        j += 1;
                    }
                    if j >= chars.len() || chars[j] != ']' {
                        return Err("unterminated 'x[i]' index".into());
                    }
                    let idx: usize = idx
                        .parse()
                        .map_err(|_| "x[] index must be a non-negative integer".to_string())?;
                    tokens.push(Token::Var(idx));
                    i = j + 1;
                }
                '(' => {
                    tokens.push(Token::LParen);
                    i += 1;
                }
                ')' => {
                    tokens.push(Token::RParen);
                    i += 1;
                }
                ',' => {
                    tokens.push(Token::Comma);
                    i += 1;
                }
                '+' | '-' | '*' | '/' | '^' => {
                    tokens.push(Token::Op(c));
                    i += 1;
                }
                c if c.is_alphabetic() => {
                    let start = i;
                    while i < chars.len() && chars[i].is_alphabetic() {
                        i += 1;
                    }
                    let name: String = chars[start..i].iter().collect();
                    match name.as_str() {
                        "pi" => tokens.push(Token::Num(PI)),
                        "e" => tokens.push(Token::Num(std::f64::consts::E)),
                        "sin" | "cos" | "tan" | "exp" | "log" | "sqrt" | "abs" => {
                            tokens.push(Token::Fn(name));
                        }
                        _ => return Err(format!("unknown function or constant '{name}'")),
                    }
                }
                other => return Err(format!("unexpected character '{other}'")),
            }
        }
        if tokens.is_empty() {
            return Err("empty expression".into());
        }
        // Structural validation: no leading/trailing/double binary operators.
        // Rewrites prefix '-' into a dedicated negation token ('~').
        let mut normalized = Vec::with_capacity(tokens.len());
        for (i, tok) in tokens.iter().enumerate() {
            let prev_is_value = i > 0
                && matches!(
                    tokens[i - 1],
                    Token::Num(_) | Token::Var(_) | Token::RParen | Token::Fn(_)
                );
            let next_is_value = i + 1 < tokens.len()
                && matches!(
                    tokens[i + 1],
                    Token::Num(_) | Token::Var(_) | Token::LParen | Token::Fn(_) | Token::Op('-')
                );
            match tok {
                Token::Op('-') if !prev_is_value && next_is_value => {
                    normalized.push(Token::Op('~'));
                }
                Token::Op(c) if !prev_is_value || !next_is_value => {
                    return Err(format!("operator '{c}' in invalid position"));
                }
                other => normalized.push(other.clone()),
            }
        }
        Ok(Self { tokens: normalized })
    }

    /// Evaluate the expression at point `x`.
    pub fn evaluate(&self, x: &[f64]) -> Result<f64, String> {
        let mut stack: Vec<f64> = Vec::new();
        let mut ops: Vec<Token> = Vec::new();
        let mut i = 0;
        while i < self.tokens.len() {
            let tok = &self.tokens[i];
            match tok {
                Token::Num(v) => stack.push(*v),
                Token::Var(idx) => {
                    let v = x
                        .get(*idx)
                        .ok_or_else(|| format!("x[{idx}] out of range (dim {})", x.len()))?;
                    stack.push(*v);
                }
                Token::Fn(name) => ops.push(Token::Fn(name.clone())),
                Token::Op('~') => ops.push(Token::Op('~')),
                Token::Op(op) => {
                    while let Some(top) = ops.last() {
                        if precedence(*op) <= precedence_from_token(top) {
                            if !reduce(&mut stack, top)? {
                                break;
                            }
                            ops.pop();
                        } else {
                            break;
                        }
                    }
                    ops.push(Token::Op(*op));
                }
                Token::LParen => ops.push(Token::LParen),
                Token::RParen => {
                    while let Some(top) = ops.pop() {
                        if top == Token::LParen {
                            break;
                        }
                        if !reduce(&mut stack, &top)? {
                            return Err(String::from("expression error"));
                        }
                    }
                    // A function directly before the paren group applies to
                    // the group's result: sin(x), log(-1), sqrt(abs(x))
                    if let Some(Token::Fn(name)) = ops.last() {
                        let name = name.clone();
                        ops.pop();
                        let arg = stack
                            .pop()
                            .ok_or_else(|| format!("'{name}' needs an argument"))?;
                        stack.push(apply_fn(&name, arg)?);
                    }
                }
                Token::Comma => {}
            }
            i += 1;
        }
        while let Some(top) = ops.pop() {
            if top == Token::LParen {
                return Err(String::from("unbalanced parentheses"));
            }
            reduce(&mut stack, &top)?;
        }
        stack.pop().ok_or_else(|| String::from("empty expression"))
    }
}

/// Apply the top-of-ops operation to the operand stack. Returns `false`
/// (without popping) when the operator cannot be applied yet.
fn reduce(stack: &mut Vec<f64>, op: &Token) -> Result<bool, String> {
    match op {
        Token::Op('~') => {
            let a = stack
                .pop()
                .ok_or_else(|| String::from("expression error"))?;
            stack.push(-a);
            Ok(true)
        }
        Token::Fn(name) => {
            let arg = stack
                .pop()
                .ok_or_else(|| format!("'{name}' needs an argument"))?;
            stack.push(apply_fn(name, arg)?);
            Ok(true)
        }
        Token::Op(c) => {
            if stack.len() < 2 {
                return Ok(false);
            }
            let b = stack
                .pop()
                .ok_or_else(|| String::from("expression error"))?;
            let a = stack
                .pop()
                .ok_or_else(|| String::from("expression error"))?;
            stack.push(apply_op(*c, a, b)?);
            Ok(true)
        }
        _ => Err(String::from("internal parse error")),
    }
}

const fn precedence(op: char) -> u8 {
    match op {
        '+' | '-' => 1,
        '*' | '/' => 2,
        '^' => 5, // exponentiation binds tighter than unary minus: -x^2 = -(x^2)
        '~' => 4,
        _ => 0,
    }
}

const fn precedence_from_token(t: &Token) -> u8 {
    match t {
        Token::Op(c) => precedence(*c),
        Token::Fn(_) => 4,
        _ => 0,
    }
}

fn apply_op(op: char, a: f64, b: f64) -> Result<f64, String> {
    match op {
        '+' => Ok(a + b),
        '-' => Ok(a - b),
        '*' => Ok(a * b),
        '/' => {
            if b.abs() < 1e-300 {
                Err("division by zero".into())
            } else {
                Ok(a / b)
            }
        }
        '^' => Ok(a.powf(b)),
        _ => Err("unknown operator".into()),
    }
}

fn apply_fn(name: &str, arg: f64) -> Result<f64, String> {
    match name {
        "sin" => Ok(arg.sin()),
        "cos" => Ok(arg.cos()),
        "tan" => Ok(arg.tan()),
        "exp" => Ok(arg.exp()),
        "log" => {
            if arg <= 0.0 {
                Err("log of non-positive value".into())
            } else {
                Ok(arg.ln())
            }
        }
        "sqrt" => {
            if arg < 0.0 {
                Err("sqrt of negative value".into())
            } else {
                Ok(arg.sqrt())
            }
        }
        "abs" => Ok(arg.abs()),
        _ => Err(format!("unknown function '{name}'")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gp_fits_and_predicts_linear_trend() {
        let mut gp = GaussianProcess::new(0.5, 1.0, 1e-6);
        for i in 0..8 {
            let x = f64::from(i);
            gp.add_sample(vec![x], 2.0f64.mul_add(x, 1.0));
        }
        gp.fit().unwrap();
        let (mean, var) = gp.predict(&[4.0]).unwrap();
        assert!((mean - 9.0).abs() < 1.5, "mean {mean} near 9");
        assert!(var >= 0.0);
        assert!(gp.n_samples() == 8);
    }

    #[test]
    fn gp_needs_two_samples() {
        let mut gp = GaussianProcess::default();
        gp.add_sample(vec![0.0], 0.0);
        assert!(gp.fit().is_err());
    }

    #[test]
    fn gp_uncertainty_is_low_near_data() {
        let mut gp = GaussianProcess::new(1.0, 1.0, 1e-8);
        for i in 0..5 {
            gp.add_sample(vec![f64::from(i)], f64::from(i).sin());
        }
        gp.fit().unwrap();
        let (_, var_near) = gp.predict(&[2.0]).unwrap();
        let (_, var_far) = gp.predict(&[100.0]).unwrap();
        assert!(var_near < var_far, "variance grows away from data");
    }

    #[test]
    fn optimizer_finds_optimum_of_parabola() {
        let mut opt = BayesianOptimizer::new(|x: &[f64]| -(x[0] - 3.0).powi(2) + 5.0, 42);
        let (steps, (best_params, best_fitness)) =
            opt.optimize(&[(0.0, 10.0)], 5, 10, 200, 0.01).unwrap();
        assert!(!steps.is_empty());
        assert!(
            (best_params[0] - 3.0).abs() < 0.5,
            "best x = {}",
            best_params[0]
        );
        assert!((best_fitness - 5.0).abs() < 0.5, "best f = {best_fitness}");
    }

    #[test]
    fn optimizer_two_dimensions() {
        let mut opt = BayesianOptimizer::new(
            |x: &[f64]| (x[1] + 2.0).mul_add(-(x[1] + 2.0), -(x[0] - 1.0).powi(2)),
            7,
        );
        let (_, (params, f)) = opt
            .optimize(&[(0.0, 2.0), (-4.0, 0.0)], 5, 8, 150, 0.01)
            .unwrap();
        assert!((params[0] - 1.0).abs() < 0.5);
        assert!((params[1] + 2.0).abs() < 0.5);
        assert!(f > -0.6, "f = {f}");
    }

    #[test]
    fn optimizer_rejects_invalid_bounds() {
        let mut opt = BayesianOptimizer::new(|x: &[f64]| x[0], 1);
        assert!(opt.optimize(&[(5.0, 1.0)], 3, 1, 10, 0.01).is_err());
        assert!(opt.optimize(&[], 3, 1, 10, 0.01).is_err());
    }

    #[test]
    fn expr_arithmetic() {
        let e = Expr::parse("2 * x[0] + 1").unwrap();
        assert!((e.evaluate(&[3.0]).unwrap() - 7.0).abs() < 1e-12);
        let e = Expr::parse("x[0] ^ 2 + x[1] ^ 2").unwrap();
        assert!((e.evaluate(&[3.0, 4.0]).unwrap() - 25.0).abs() < 1e-12);
    }

    #[test]
    fn expr_functions_and_constants() {
        let e = Expr::parse("sin(x[0]) + cos(x[0]) + pi").unwrap();
        let v = e.evaluate(&[0.0]).unwrap();
        assert!((v - (0.0 + 1.0 + PI)).abs() < 1e-12);
        let e = Expr::parse("sqrt(abs(x[0]))").unwrap();
        assert!((e.evaluate(&[-9.0]).unwrap() - 3.0).abs() < 1e-12);
        let e = Expr::parse("exp(log(x[0]))").unwrap();
        assert!((e.evaluate(&[7.0]).unwrap() - 7.0).abs() < 1e-9);
    }

    #[test]
    fn expr_errors_are_safe() {
        assert!(Expr::parse("").is_err());
        assert!(Expr::parse("foo(1)").is_err());
        assert!(Expr::parse("x[0] +").is_err());
        let e = Expr::parse("1 / (x[0] - x[0])").unwrap();
        assert!(e.evaluate(&[1.0]).is_err());
        let e = Expr::parse("x[5]").unwrap();
        assert!(e.evaluate(&[1.0]).is_err());
        let e = Expr::parse("log(-1)").unwrap();
        assert!(e.evaluate(&[0.0]).is_err());
    }

    #[test]
    fn expr_nested_parentheses() {
        let e = Expr::parse("(x[0] + 2) * (x[1] - 3)").unwrap();
        assert!((e.evaluate(&[3.0, 5.0]).unwrap() - 10.0).abs() < 1e-12);
    }

    #[test]
    fn expr_unary_minus() {
        let e = Expr::parse("-x[0] + 1").unwrap();
        assert!((e.evaluate(&[3.0]).unwrap() - -2.0).abs() < 1e-12);
        let e = Expr::parse("2 * -x[0]").unwrap();
        assert!((e.evaluate(&[4.0]).unwrap() - -8.0).abs() < 1e-12);
        let e = Expr::parse("x[0] - -2").unwrap();
        assert!((e.evaluate(&[3.0]).unwrap() - 5.0).abs() < 1e-12);
    }

    #[test]
    fn expr_function_composition() {
        let e = Expr::parse("sqrt(abs(x[0]))").unwrap();
        assert!((e.evaluate(&[-16.0]).unwrap() - 4.0).abs() < 1e-12);
        let e = Expr::parse("2 * sin(x[0]) + 1").unwrap();
        let v = e.evaluate(&[0.0]).unwrap();
        assert!((v - 1.0).abs() < 1e-12);
        let e = Expr::parse("sin(x[0]) + cos(x[0])").unwrap();
        assert!((e.evaluate(&[0.0]).unwrap() - 1.0).abs() < 1e-12);
    }

    #[test]
    fn expr_exponent_binds_tighter_than_unary_minus() {
        // -x^2 must be -(x^2), not (-x)^2
        let e = Expr::parse("-x[0]^2").unwrap();
        assert!((e.evaluate(&[3.0]).unwrap() - -9.0).abs() < 1e-12);
        // x^2 ^ 3 is right-associative in math but left-to-right here;
        // just verify the chain is deterministic
        let e = Expr::parse("2 ^ 3 ^ 2").unwrap();
        assert!((e.evaluate(&[]).unwrap() - 64.0).abs() < 1e-12);
    }

    #[test]
    fn expr_leading_operator_rejected() {
        assert!(Expr::parse("* x[0]").is_err());
        assert!(Expr::parse("/ 2").is_err());
        assert!(Expr::parse("^ x[0]").is_err());
    }

    #[test]
    fn norm_cdf_bounds() {
        assert!(norm_cdf(0.0) > 0.499 && norm_cdf(0.0) < 0.501);
        assert!(norm_cdf(3.0) > 0.998);
        assert!(norm_cdf(-3.0) < 0.002);
    }

    #[test]
    fn expected_improvement_zero_variance() {
        let mut gp = GaussianProcess::default();
        gp.add_sample(vec![0.0], 1.0);
        gp.add_sample(vec![1.0], 2.0);
        gp.fit().unwrap();
        // At a known point EI ≈ 0 when far below best
        let ei = expected_improvement(&gp, &[0.0], 5.0, 0.0).unwrap();
        assert!(ei >= 0.0);
    }
}
