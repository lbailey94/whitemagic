//! Monte Carlo simulation — sampling-based estimation.
//!
//! Supports Bayesian MC (random sampling), Quasi-MC (low-discrepancy
//! sequences), and high-dimensional integration via sampling.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

// ── Distribution ──────────────────────────────────────────────────────

/// Probability distributions for MC sampling.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Distribution {
    /// Uniform distribution on [min, max].
    Uniform { min: f64, max: f64 },
    /// Normal distribution with mean and std_dev.
    Normal { mean: f64, std_dev: f64 },
    /// Exponential distribution with rate lambda.
    Exponential { lambda: f64 },
    /// Triangular distribution (min, mode, max).
    Triangular { min: f64, mode: f64, max: f64 },
    /// Constant value (degenerate distribution).
    Constant(f64),
}

impl Distribution {
    /// Sample from this distribution using a uniform random number in [0, 1).
    #[must_use]
    pub fn sample(&self, u: f64) -> f64 {
        match *self {
            Self::Uniform { min, max } => u.mul_add(max - min, min),
            Self::Normal { mean, std_dev } => {
                // Box-Muller transform
                let u1 = u.max(1e-10);
                let u2 = (u * 1.618033988749895).fract();
                let z = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();
                std_dev.mul_add(z, mean)
            }
            Self::Exponential { lambda } => {
                let u = u.max(1e-10);
                -u.ln() / lambda
            }
            Self::Triangular { min, mode, max } => {
                let fc = (mode - min) / (max - min);
                if u < fc {
                    min + (u * (max - min) * (mode - min)).sqrt()
                } else {
                    max - ((1.0 - u) * (max - min) * (max - mode)).sqrt()
                }
            }
            Self::Constant(v) => v,
        }
    }

    /// Mean of the distribution.
    #[must_use]
    pub const fn mean(&self) -> f64 {
        match *self {
            Self::Uniform { min, max } => f64::midpoint(min, max),
            Self::Normal { mean, .. } => mean,
            Self::Exponential { lambda } => 1.0 / lambda,
            Self::Triangular { min, mode, max } => (min + mode + max) / 3.0,
            Self::Constant(v) => v,
        }
    }

    /// Human-readable name.
    #[must_use]
    pub const fn name(&self) -> &'static str {
        match self {
            Self::Uniform { .. } => "uniform",
            Self::Normal { .. } => "normal",
            Self::Exponential { .. } => "exponential",
            Self::Triangular { .. } => "triangular",
            Self::Constant(_) => "constant",
        }
    }
}

// ── MC Config ─────────────────────────────────────────────────────────

/// Configuration for Monte Carlo simulation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McConfig {
    /// Number of samples.
    pub n_samples: usize,
    /// Random seed (0 = use time-based seed).
    pub seed: u64,
    /// Whether to use Quasi-MC (Sobol-like low-discrepancy sequence).
    pub quasi_mc: bool,
}

impl Default for McConfig {
    fn default() -> Self {
        Self {
            n_samples: 10_000,
            seed: 42,
            quasi_mc: false,
        }
    }
}

// ── MC Result ─────────────────────────────────────────────────────────

/// Result of a Monte Carlo simulation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McResult {
    /// Mean of the output.
    pub mean: f64,
    /// Standard deviation.
    pub std_dev: f64,
    /// Minimum value observed.
    pub min: f64,
    /// Maximum value observed.
    pub max: f64,
    /// 5th percentile.
    pub p5: f64,
    /// 25th percentile.
    pub p25: f64,
    /// 50th percentile (median).
    pub p50: f64,
    /// 75th percentile.
    pub p75: f64,
    /// 95th percentile.
    pub p95: f64,
    /// Number of samples.
    pub n_samples: usize,
}

impl McResult {
    /// 95% confidence interval half-width.
    #[must_use]
    pub fn ci95_half_width(&self) -> f64 {
        1.96 * self.std_dev / (self.n_samples as f64).sqrt()
    }

    /// Lower bound of 95% CI.
    #[must_use]
    pub fn ci95_lower(&self) -> f64 {
        self.mean - self.ci95_half_width()
    }

    /// Upper bound of 95% CI.
    #[must_use]
    pub fn ci95_upper(&self) -> f64 {
        self.mean + self.ci95_half_width()
    }

    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "mean": self.mean,
            "std_dev": self.std_dev,
            "min": self.min,
            "max": self.max,
            "p5": self.p5,
            "p25": self.p25,
            "p50": self.p50,
            "p75": self.p75,
            "p95": self.p95,
            "n_samples": self.n_samples,
            "ci95_lower": self.ci95_lower(),
            "ci95_upper": self.ci95_upper(),
        })
    }
}

// ── Monte Carlo Simulator ─────────────────────────────────────────────

/// Simple PRNG (xorshift64).
const fn xorshift64(state: &mut u64) -> u64 {
    let mut x = *state;
    if x == 0 {
        x = 0x9E37_79B9_7F4A_7C15;
    }
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    *state = x;
    x
}

/// Generate a uniform random number in [0, 1) from a PRNG state.
fn rand_u01(state: &mut u64) -> f64 {
    let r = xorshift64(state);
    (r >> 11) as f64 / (1u64 << 53) as f64
}

/// Generate a low-discrepancy Sobol-like sequence point.
fn sobol_point(index: usize, dim: usize) -> f64 {
    // Simple Van der Corput sequence in base 2 for 1D
    let _ = dim;
    let mut result = 0.0;
    let mut f = 0.5;
    let mut i = index + 1;
    while i > 0 {
        if i & 1 != 0 {
            result += f;
        }
        i >>= 1;
        f *= 0.5;
    }
    result
}

/// Monte Carlo simulator — runs sampling-based simulations.
pub struct MonteCarloSimulator {
    config: McConfig,
    rng_state: u64,
}

impl Default for MonteCarloSimulator {
    fn default() -> Self {
        Self::new(McConfig::default())
    }
}

impl std::fmt::Debug for MonteCarloSimulator {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MonteCarloSimulator")
            .field("config", &self.config)
            .finish_non_exhaustive()
    }
}

impl MonteCarloSimulator {
    /// Create a new simulator.
    #[must_use]
    pub fn new(config: McConfig) -> Self {
        Self {
            rng_state: if config.seed == 0 {
                chrono::Utc::now().timestamp_nanos_opt().unwrap_or(42) as u64
            } else {
                config.seed
            },
            config,
        }
    }

    /// Run a simulation with a model function.
    /// The model takes a vector of sampled inputs and returns an output.
    pub fn simulate<F>(&mut self, distributions: &[Distribution], model: F) -> McResult
    where
        F: Fn(&[f64]) -> f64,
    {
        let n = self.config.n_samples;
        let mut outputs = Vec::with_capacity(n);

        for i in 0..n {
            let inputs: Vec<f64> = distributions
                .iter()
                .enumerate()
                .map(|(d, dist)| {
                    if self.config.quasi_mc {
                        let u = sobol_point(i, d);
                        dist.sample(u)
                    } else {
                        let u = rand_u01(&mut self.rng_state);
                        dist.sample(u)
                    }
                })
                .collect();

            outputs.push(model(&inputs));
        }

        Self::compute_stats(&outputs)
    }

    /// Compute statistics from a vector of samples.
    #[must_use]
    pub fn compute_stats(samples: &[f64]) -> McResult {
        let n = samples.len();
        if n == 0 {
            return McResult {
                mean: 0.0,
                std_dev: 0.0,
                min: 0.0,
                max: 0.0,
                p5: 0.0,
                p25: 0.0,
                p50: 0.0,
                p75: 0.0,
                p95: 0.0,
                n_samples: 0,
            };
        }

        let mut sorted = samples.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

        let mean = sorted.iter().sum::<f64>() / n as f64;
        let variance = sorted
            .iter()
            .map(|x| {
                let d = x - mean;
                d * d
            })
            .sum::<f64>()
            / n as f64;
        let std_dev = variance.sqrt();

        let percentile = |p: f64| -> f64 {
            let idx = ((p / 100.0) * (n - 1) as f64).round() as usize;
            sorted[idx.min(n - 1)]
        };

        McResult {
            mean,
            std_dev,
            min: sorted[0],
            max: sorted[n - 1],
            p5: percentile(5.0),
            p25: percentile(25.0),
            p50: percentile(50.0),
            p75: percentile(75.0),
            p95: percentile(95.0),
            n_samples: n,
        }
    }

    /// Estimate the integral of a function over a hyper-rectangle.
    pub fn integrate<F>(&mut self, bounds: &[(f64, f64)], f: F) -> McResult
    where
        F: Fn(&[f64]) -> f64,
    {
        let distributions: Vec<Distribution> = bounds
            .iter()
            .map(|(min, max)| Distribution::Uniform {
                min: *min,
                max: *max,
            })
            .collect();

        let volume: f64 = bounds.iter().map(|(min, max)| max - min).product();

        self.simulate(&distributions, |inputs| f(inputs) * volume)
    }

    /// Get the config.
    #[must_use]
    pub const fn config(&self) -> &McConfig {
        &self.config
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn distribution_uniform_sample() {
        let d = Distribution::Uniform {
            min: 0.0,
            max: 10.0,
        };
        let s = d.sample(0.5);
        assert!((s - 5.0).abs() < 0.001);
    }

    #[test]
    fn distribution_normal_sample() {
        let d = Distribution::Normal {
            mean: 0.0,
            std_dev: 1.0,
        };
        let s = d.sample(0.5);
        // Just check it's a finite number
        assert!(s.is_finite());
    }

    #[test]
    fn distribution_exponential_sample() {
        let d = Distribution::Exponential { lambda: 1.0 };
        let s = d.sample(0.5);
        assert!(s > 0.0);
    }

    #[test]
    fn distribution_triangular_sample() {
        let d = Distribution::Triangular {
            min: 0.0,
            mode: 0.5,
            max: 1.0,
        };
        let s = d.sample(0.5);
        assert!((0.0..=1.0).contains(&s));
    }

    #[test]
    fn distribution_constant_sample() {
        let d = Distribution::Constant(42.0);
        assert!((d.sample(0.5) - 42.0).abs() < 0.001);
    }

    #[test]
    fn distribution_mean() {
        assert!(
            (Distribution::Uniform {
                min: 0.0,
                max: 10.0
            }
            .mean()
                - 5.0)
                .abs()
                < 0.001
        );
        assert!(
            (Distribution::Normal {
                mean: 3.0,
                std_dev: 1.0
            }
            .mean()
                - 3.0)
                .abs()
                < 0.001
        );
        assert!((Distribution::Constant(42.0).mean() - 42.0).abs() < 0.001);
    }

    #[test]
    fn distribution_name() {
        assert_eq!(
            Distribution::Uniform { min: 0.0, max: 1.0 }.name(),
            "uniform"
        );
        assert_eq!(
            Distribution::Normal {
                mean: 0.0,
                std_dev: 1.0
            }
            .name(),
            "normal"
        );
        assert_eq!(Distribution::Constant(0.0).name(), "constant");
    }

    #[test]
    fn mc_simulate_constant_model() {
        let mut sim = MonteCarloSimulator::new(McConfig {
            n_samples: 1000,
            seed: 42,
            quasi_mc: false,
        });
        let dists = vec![Distribution::Uniform { min: 0.0, max: 1.0 }];
        let result = sim.simulate(&dists, |_| 42.0);
        assert!((result.mean - 42.0).abs() < 0.001);
        assert!((result.std_dev - 0.0).abs() < 0.001);
    }

    #[test]
    fn mc_simulate_identity_model() {
        let mut sim = MonteCarloSimulator::new(McConfig {
            n_samples: 10_000,
            seed: 42,
            quasi_mc: false,
        });
        let dists = vec![Distribution::Uniform {
            min: 0.0,
            max: 10.0,
        }];
        let result = sim.simulate(&dists, |inputs| inputs[0]);
        // Mean of Uniform[0,10] = 5
        assert!((result.mean - 5.0).abs() < 0.5);
    }

    #[test]
    fn mc_simulate_sum_model() {
        let mut sim = MonteCarloSimulator::new(McConfig {
            n_samples: 10_000,
            seed: 42,
            quasi_mc: false,
        });
        let dists = vec![
            Distribution::Uniform { min: 0.0, max: 1.0 },
            Distribution::Uniform { min: 0.0, max: 1.0 },
        ];
        let result = sim.simulate(&dists, |inputs| inputs[0] + inputs[1]);
        // Mean of sum of two Uniform[0,1] = 1.0
        assert!((result.mean - 1.0).abs() < 0.2);
    }

    #[test]
    fn mc_quasi_mc_mode() {
        let mut sim = MonteCarloSimulator::new(McConfig {
            n_samples: 1000,
            seed: 42,
            quasi_mc: true,
        });
        let dists = vec![Distribution::Uniform { min: 0.0, max: 1.0 }];
        let result = sim.simulate(&dists, |inputs| inputs[0]);
        // Quasi-MC should converge faster
        assert!((result.mean - 0.5).abs() < 0.1);
    }

    #[test]
    fn mc_result_percentiles() {
        let samples: Vec<f64> = (0..100).map(f64::from).collect();
        let result = MonteCarloSimulator::compute_stats(&samples);
        assert!((result.mean - 49.5).abs() < 0.001);
        assert!((result.min - 0.0).abs() < 0.001);
        assert!((result.max - 99.0).abs() < 0.001);
        assert!((result.p50 - 49.0).abs() <= 2.0);
    }

    #[test]
    fn mc_result_ci95() {
        let samples: Vec<f64> = vec![1.0; 100];
        let result = MonteCarloSimulator::compute_stats(&samples);
        assert!((result.ci95_half_width() - 0.0).abs() < 0.001);
    }

    #[test]
    fn mc_result_to_json() {
        let result = McResult {
            mean: 5.0,
            std_dev: 1.0,
            min: 0.0,
            max: 10.0,
            p5: 1.0,
            p25: 3.0,
            p50: 5.0,
            p75: 7.0,
            p95: 9.0,
            n_samples: 100,
        };
        let json = result.to_json();
        assert_eq!(json["mean"], 5.0);
        assert_eq!(json["n_samples"], 100);
    }

    #[test]
    fn mc_integrate_constant() {
        let mut sim = MonteCarloSimulator::new(McConfig {
            n_samples: 10_000,
            seed: 42,
            quasi_mc: false,
        });
        // Integral of 1.0 over [0, 2] = 2.0
        let result = sim.integrate(&[(0.0, 2.0)], |_| 1.0);
        assert!((result.mean - 2.0).abs() < 0.2);
    }

    #[test]
    fn mc_integrate_identity() {
        let mut sim = MonteCarloSimulator::new(McConfig {
            n_samples: 10_000,
            seed: 42,
            quasi_mc: false,
        });
        // Integral of x over [0, 1] = 0.5
        let result = sim.integrate(&[(0.0, 1.0)], |inputs| inputs[0]);
        assert!((result.mean - 0.5).abs() < 0.1);
    }

    #[test]
    fn mc_compute_stats_empty() {
        let result = MonteCarloSimulator::compute_stats(&[]);
        assert_eq!(result.n_samples, 0);
        assert!((result.mean - 0.0).abs() < 0.001);
    }

    #[test]
    fn mc_simulate_with_normal() {
        let mut sim = MonteCarloSimulator::new(McConfig {
            n_samples: 50_000,
            seed: 42,
            quasi_mc: false,
        });
        let dists = vec![Distribution::Normal {
            mean: 10.0,
            std_dev: 2.0,
        }];
        let result = sim.simulate(&dists, |inputs| inputs[0]);
        // Mean should be close to 10
        assert!((result.mean - 10.0).abs() < 1.0);
        // Std dev should be close to 2
        assert!((result.std_dev - 2.0).abs() < 1.0);
    }

    #[test]
    fn mc_config_default() {
        let config = McConfig::default();
        assert_eq!(config.n_samples, 10_000);
        assert_eq!(config.seed, 42);
        assert!(!config.quasi_mc);
    }
}
