//! Stochastic differential equation solvers — Euler–Maruyama and Milstein.
//!
//! Supports two drift types:
//! - **GBM**: `dX = μ·X·dt + σ·X·dW` (geometric Brownian motion, e.g. prices)
//! - **OU**:   `dX = θ·(μ − X)·dt + σ·dW` (Ornstein–Uhlenbeck, mean reversion)
//!
//! Milstein adds the second-order correction `0.5·σ·σ'·X·(ΔW² − dt)`, which
//! is non-zero only for GBM (the OU diffusion is constant).
//!
//! Also provides a two-level multilevel Monte Carlo (MLMC) extrapolation:
//! `E ≈ E_fine + (E_fine − E_coarse)` — a cheap variance-reduction trick
//! for terminal-statistic estimates.

use crate::bayesian::rand_u01;

/// Draw a standard normal via Box–Muller from the SplitMix64 state.
fn randn(state: &mut u64) -> f64 {
    let u1 = rand_u01(state).max(1e-12);
    let u2 = rand_u01(state).max(1e-12);
    (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos()
}

/// SDE drift type.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum DriftType {
    /// Geometric Brownian motion: `dX = μX dt + σX dW`.
    Gbm,
    /// Ornstein–Uhlenbeck: `dX = θ(μ − X) dt + σ dW`.
    Ou,
}

impl DriftType {
    /// Parse from the v26 tool's string names.
    pub fn parse(s: &str) -> Result<Self, String> {
        match s.to_ascii_lowercase().as_str() {
            "gbm" | "geometric" => Ok(Self::Gbm),
            "ou" | "ornstein" | "ornstein_uhlenbeck" | "mean_reversion" => Ok(Self::Ou),
            other => Err(format!("unknown drift type '{other}' (expected gbm | ou)")),
        }
    }
}

/// Solver scheme.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum Solver {
    /// Euler–Maruyama (strong order 0.5).
    Euler,
    /// Milstein (strong order 1.0) — identical to Euler for OU.
    Milstein,
}

impl Solver {
    /// Parse from the v26 tool's string names.
    pub fn parse(s: &str) -> Result<Self, String> {
        match s.to_ascii_lowercase().as_str() {
            "euler" | "euler_maruyama" | "em" => Ok(Self::Euler),
            "milstein" => Ok(Self::Milstein),
            other => Err(format!(
                "unknown solver '{other}' (expected euler | milstein)"
            )),
        }
    }
}

/// SDE configuration.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SdeConfig {
    /// Initial value X(0).
    pub x0: f64,
    /// Terminal time T.
    pub t_end: f64,
    /// Number of time steps.
    pub n_steps: usize,
    /// Number of paths.
    pub n_paths: usize,
    /// Drift model.
    pub drift: DriftType,
    /// Drift coefficient μ (GBM) or mean-reversion level (OU).
    pub mu: f64,
    /// Mean-reversion strength θ (OU only).
    pub theta: f64,
    /// Diffusion coefficient σ.
    pub sigma: f64,
    /// Solver scheme.
    pub solver: Solver,
    /// PRNG seed.
    pub seed: u64,
}

impl Default for SdeConfig {
    fn default() -> Self {
        Self {
            x0: 100.0,
            t_end: 1.0,
            n_steps: 100,
            n_paths: 1000,
            drift: DriftType::Gbm,
            mu: 0.05,
            theta: 1.0,
            sigma: 0.2,
            solver: Solver::Euler,
            seed: 42,
        }
    }
}

/// Drift and diffusion terms for the current state.
fn drift_diffusion(x: f64, cfg: &SdeConfig) -> (f64, f64) {
    match cfg.drift {
        DriftType::Gbm => (cfg.mu * x, cfg.sigma * x),
        DriftType::Ou => (cfg.theta * (cfg.mu - x), cfg.sigma),
    }
}

/// Terminal statistics over all paths.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SdeResult {
    /// Mean terminal value.
    pub mean: f64,
    /// Standard deviation of terminal values.
    pub std: f64,
    /// 5th percentile of terminal values.
    pub p05: f64,
    /// Median (50th percentile).
    pub p50: f64,
    /// 95th percentile of terminal values.
    pub p95: f64,
    /// Min terminal value.
    pub min: f64,
    /// Max terminal value.
    pub max: f64,
    /// Number of paths simulated.
    pub n_paths: usize,
    /// Time step dt used.
    pub dt: f64,
}

/// Solve the SDE and return terminal-value statistics.
#[must_use]
pub fn solve(cfg: &SdeConfig) -> SdeResult {
    let dt = cfg.t_end / cfg.n_steps.max(1) as f64;
    let sqrt_dt = dt.sqrt();
    let mut rng = cfg.seed;
    let mut terminals = Vec::with_capacity(cfg.n_paths);

    for _ in 0..cfg.n_paths {
        let mut x = cfg.x0;
        for _ in 0..cfg.n_steps {
            let (drift, diff) = drift_diffusion(x, cfg);
            let dw = sqrt_dt * randn(&mut rng);
            if cfg.solver == Solver::Milstein {
                // Milstein correction: 0.5 · σ·σ' · (ΔW² − dt)
                let (_, diff) = drift_diffusion(x, cfg);
                let sigma_prime = match cfg.drift {
                    DriftType::Gbm => cfg.sigma, // σ(x) = σx → σ' = σ
                    DriftType::Ou => 0.0,        // σ(x) = σ → σ' = 0
                };
                let correction = 0.5 * diff * sigma_prime * (dw * dw - dt);
                x += drift.mul_add(dt, diff * dw) + correction;
            } else {
                x += drift.mul_add(dt, diff * dw);
            }
        }
        terminals.push(x);
    }

    stats(&terminals, cfg.n_paths, dt)
}

/// Two-level multilevel Monte Carlo estimate of the mean terminal value.
///
/// Uses the same seed for both levels so the coarse/fine paths share
/// randomness (coupling), which makes the variance-reduction effective.
#[must_use]
pub fn solve_mlmc(cfg: &SdeConfig) -> MlMcResult {
    let fine_steps = cfg.n_steps.max(2);
    let coarse_steps = fine_steps / 2;

    let fine = solve(&SdeConfig {
        n_steps: fine_steps,
        ..cfg.clone()
    });
    let coarse = solve(&SdeConfig {
        n_steps: coarse_steps,
        ..cfg.clone()
    });

    // E ≈ E_fine + (E_fine − E_coarse) — Richardson-style extrapolation
    let mlmc_mean = fine.mean + (fine.mean - coarse.mean);
    MlMcResult {
        mlmc_mean,
        fine_mean: fine.mean,
        coarse_mean: coarse.mean,
        fine_std: fine.std,
        n_paths: cfg.n_paths,
        fine_steps,
        coarse_steps,
    }
}

/// Result of a multilevel Monte Carlo run.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct MlMcResult {
    /// MLMC-estimated mean terminal value.
    pub mlmc_mean: f64,
    /// Fine-level mean.
    pub fine_mean: f64,
    /// Coarse-level mean.
    pub coarse_mean: f64,
    /// Fine-level std.
    pub fine_std: f64,
    /// Paths per level.
    pub n_paths: usize,
    /// Fine steps.
    pub fine_steps: usize,
    /// Coarse steps.
    pub coarse_steps: usize,
}

/// Percentile helper (nearest-rank).
fn percentile(sorted: &[f64], q: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let idx = ((q * sorted.len() as f64).ceil() as usize)
        .saturating_sub(1)
        .min(sorted.len() - 1);
    sorted[idx]
}

fn stats(terminals: &[f64], n_paths: usize, dt: f64) -> SdeResult {
    let mean = terminals.iter().sum::<f64>() / terminals.len().max(1) as f64;
    let var =
        terminals.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / terminals.len().max(1) as f64;
    let mut sorted = terminals.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    SdeResult {
        mean,
        std: var.sqrt(),
        p05: percentile(&sorted, 0.05),
        p50: percentile(&sorted, 0.5),
        p95: percentile(&sorted, 0.95),
        min: sorted.first().copied().unwrap_or(0.0),
        max: sorted.last().copied().unwrap_or(0.0),
        n_paths,
        dt,
    }
}

#[cfg(test)]
mod tests {
    #![allow(clippy::suboptimal_flops)] // test data expressions, not hot paths
    use super::*;

    #[test]
    fn gbm_euler_matches_analytic_mean() {
        // GBM: E[X_t] = X0 · e^(μt) — independent of σ
        let cfg = SdeConfig {
            x0: 100.0,
            t_end: 1.0,
            n_steps: 200,
            n_paths: 20_000,
            drift: DriftType::Gbm,
            mu: 0.05,
            sigma: 0.3,
            solver: Solver::Euler,
            seed: 42,
            ..Default::default()
        };
        let r = solve(&cfg);
        let analytic = 100.0 * (0.05_f64).exp();
        assert!(
            (r.mean - analytic).abs() / analytic < 0.02,
            "euler mean {} vs analytic {}",
            r.mean,
            analytic
        );
        assert!(r.std > 0.0);
    }

    #[test]
    fn milstein_reduces_pathwise_error() {
        // Strong convergence: simulate one GBM path with both schemes using
        // the SAME Brownian increments and compare to the exact solution
        // X_t = X0·exp((μ − σ²/2)t + σ·W_t). Milstein (order 1.0) should be
        // closer than Euler (order 0.5) on a coarse grid.
        let cfg = SdeConfig {
            x0: 100.0,
            t_end: 1.0,
            n_steps: 8,
            n_paths: 1,
            drift: DriftType::Gbm,
            mu: 0.05,
            sigma: 0.4,
            seed: 7,
            ..Default::default()
        };
        let dt = cfg.t_end / cfg.n_steps as f64;
        let sqrt_dt = dt.sqrt();
        let mut rng = cfg.seed;

        let mut euler_x = cfg.x0;
        let mut mil_x = cfg.x0;
        let mut w = 0.0_f64;
        for _ in 0..cfg.n_steps {
            let dw = sqrt_dt * randn(&mut rng);
            w += dw;
            // Euler
            euler_x += cfg.mu * euler_x * dt + cfg.sigma * euler_x * dw;
            // Milstein
            mil_x += cfg.mu * mil_x * dt
                + cfg.sigma * mil_x * dw
                + 0.5 * cfg.sigma * cfg.sigma * mil_x * (dw * dw - dt);
        }
        let exact =
            cfg.x0 * ((cfg.mu - 0.5 * cfg.sigma * cfg.sigma) * cfg.t_end + cfg.sigma * w).exp();
        let euler_err = (euler_x - exact).abs();
        let mil_err = (mil_x - exact).abs();
        assert!(
            mil_err < euler_err,
            "Milstein pathwise err {mil_err} should be smaller than Euler's {euler_err}"
        );
    }

    #[test]
    fn ou_reverts_to_mean() {
        // OU: E[X_t] → μ as t → ∞. With θ=1, t=3, E ≈ μ + (x0−μ)e^(−3)
        let cfg = SdeConfig {
            x0: 0.0,
            t_end: 3.0,
            n_steps: 300,
            n_paths: 20_000,
            drift: DriftType::Ou,
            mu: 5.0,
            theta: 1.0,
            sigma: 0.5,
            solver: Solver::Euler,
            seed: 3,
        };
        let r = solve(&cfg);
        let analytic = 5.0 + (0.0 - 5.0) * (-3.0_f64).exp();
        assert!(
            (r.mean - analytic).abs() < 0.05,
            "ou mean {} vs analytic {}",
            r.mean,
            analytic
        );
    }

    #[test]
    fn gbm_paths_never_negative_in_milstein_small_step() {
        // Milstein with a small step on GBM should stay positive
        let cfg = SdeConfig {
            x0: 100.0,
            t_end: 1.0,
            n_steps: 500,
            n_paths: 5000,
            drift: DriftType::Gbm,
            mu: 0.05,
            sigma: 0.2,
            solver: Solver::Milstein,
            seed: 99,
            ..Default::default()
        };
        let r = solve(&cfg);
        assert!(
            r.min > 0.0,
            "GBM Milstein min should stay positive, got {}",
            r.min
        );
    }

    #[test]
    fn mlmc_improves_estimate_on_coarse_grid() {
        let base = SdeConfig {
            x0: 100.0,
            t_end: 1.0,
            n_steps: 8, // coarse — big bias
            n_paths: 10_000,
            drift: DriftType::Gbm,
            mu: 0.05,
            sigma: 0.4,
            seed: 11,
            ..Default::default()
        };
        let analytic = 100.0 * (0.05_f64).exp();
        let fine = solve(&SdeConfig { n_steps: 8, ..base });
        let mlmc = solve_mlmc(&base);
        let fine_err = (fine.mean - analytic).abs();
        let mlmc_err = (mlmc.mlmc_mean - analytic).abs();
        assert!(
            mlmc_err <= fine_err + 1e-9,
            "mlmc err {mlmc_err} should be <= fine err {fine_err}"
        );
    }

    #[test]
    fn drift_type_parsing() {
        assert_eq!(DriftType::parse("gbm").unwrap(), DriftType::Gbm);
        assert_eq!(DriftType::parse("ou").unwrap(), DriftType::Ou);
        assert!(DriftType::parse("bogus").is_err());
        assert_eq!(Solver::parse("euler").unwrap(), Solver::Euler);
        assert_eq!(Solver::parse("milstein").unwrap(), Solver::Milstein);
        assert!(Solver::parse("bogus").is_err());
    }
}
