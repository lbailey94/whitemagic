//! Markov Chain Monte Carlo (MCMC) samplers.
//!
//! Implements:
//! - Metropolis-Hastings (random walk)
//! - Hamiltonian Monte Carlo (HMC)
//!
//! Both support Gaussian and Rosenbrock target distributions.
//! Custom targets can be added by extending the `log_target` function.

use rand::{RngCore, SeedableRng};
use rand_xoshiro::Xoshiro256PlusPlus;
use rand_distr::{Distribution, Normal};

/// Target distribution types for MCMC sampling.
#[derive(Clone, Copy)]
enum TargetType {
    Gaussian,
    Rosenbrock,
}

fn parse_target(s: &str) -> TargetType {
    match s {
        "rosenbrock" => TargetType::Rosenbrock,
        _ => TargetType::Gaussian,
    }
}

/// Log-density of the target distribution.
fn log_target(x: &[f64], target: TargetType, mean: &[f64], cov: &[f64]) -> f64 {
    match target {
        TargetType::Gaussian => {
            let d = mean.len();
            if d == 0 || x.len() != d {
                return f64::NEG_INFINITY;
            }
            // log N(x | mean, cov) — cov is diagonal (length d)
            let mut logp = -0.5 * d as f64 * (2.0 * std::f64::consts::PI).ln();
            for i in 0..d {
                let var = if i < cov.len() { cov[i].abs().max(1e-10) } else { 1.0 };
                let diff = x[i] - mean[i];
                logp -= 0.5 * diff * diff / var;
                logp -= 0.5 * var.ln();
            }
            logp
        }
        TargetType::Rosenbrock => {
            // 2D Rosenbrock: -((1-x)^2 + 100(y-x^2)^2)
            if x.len() < 2 {
                return f64::NEG_INFINITY;
            }
            -((1.0 - x[0]).powi(2) + 100.0 * (x[1] - x[0].powi(2)).powi(2))
        }
    }
}

/// Gradient of log-target for HMC.
fn grad_log_target(x: &[f64], target: TargetType, mean: &[f64], cov: &[f64]) -> Vec<f64> {
    let d = x.len();
    match target {
        TargetType::Gaussian => {
            (0..d)
                .map(|i| {
                    let var = if i < cov.len() { cov[i].abs().max(1e-10) } else { 1.0 };
                    -(x[i] - mean[i]) / var
                })
                .collect()
        }
        TargetType::Rosenbrock => {
            if d < 2 {
                return vec![0.0; d];
            }
            // d/dx[-((1-x)^2 + 100(y-x^2)^2)] = 2(1-x) + 400x(y-x^2)
            // d/dy = -200(y-x^2)
            let mut g = vec![0.0; d];
            g[0] = 2.0 * (1.0 - x[0]) + 400.0 * x[0] * (x[1] - x[0].powi(2));
            g[1] = -200.0 * (x[1] - x[0].powi(2));
            g
        }
    }
}

/// Metropolis-Hastings sampler with Gaussian random-walk proposals.
///
/// Returns (samples, acceptance_rate) where samples is n_samples × d.
pub fn metropolis_hastings(
    n_samples: usize,
    n_burn: usize,
    x0: &[f64],
    proposal_std: f64,
    seed: u64,
    target_type: &str,
    target_mean: &[f64],
    target_cov: &[f64],
) -> (Vec<Vec<f64>>, f64) {
    let d = x0.len();
    if d == 0 {
        return (Vec::new(), 0.0);
    }

    let target = parse_target(target_type);
    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);
    let normal = Normal::new(0.0, proposal_std).unwrap();

    let mut current = x0.to_vec();
    let mut current_logp = log_target(&current, target, target_mean, target_cov);

    let mut samples = Vec::with_capacity(n_samples);
    let mut n_accepted = 0u32;
    let total = (n_samples + n_burn) as u32;

    for iter in 0..total as usize {
        // Propose: x' = x + N(0, proposal_std^2)
        let mut proposed = current.clone();
        for val in proposed.iter_mut() {
            *val += normal.sample(&mut rng);
        }

        let proposed_logp = log_target(&proposed, target, target_mean, target_cov);

        // Accept/reject
        let log_alpha = proposed_logp - current_logp;
        let u: f64 = (rng.next_u64() as f64) / (u64::MAX as f64);
        if u.ln() < log_alpha {
            current = proposed;
            current_logp = proposed_logp;
            if iter >= n_burn {
                n_accepted += 1;
            }
        }

        if iter >= n_burn {
            samples.push(current.clone());
        }
    }

    let acceptance_rate = if n_samples > 0 {
        n_accepted as f64 / n_samples as f64
    } else {
        0.0
    };

    (samples, acceptance_rate)
}

/// Hamiltonian Monte Carlo sampler.
///
/// Uses leapfrog integration for Hamiltonian dynamics.
/// Returns (samples, acceptance_rate).
pub fn hamiltonian_monte_carlo(
    n_samples: usize,
    n_burn: usize,
    x0: &[f64],
    step_size: f64,
    n_leapfrog: usize,
    seed: u64,
    target_type: &str,
    target_mean: &[f64],
    target_cov: &[f64],
) -> (Vec<Vec<f64>>, f64) {
    let d = x0.len();
    if d == 0 {
        return (Vec::new(), 0.0);
    }

    let target = parse_target(target_type);
    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);
    let normal = Normal::new(0.0, 1.0).unwrap();

    let mut current_q = x0.to_vec();
    let mut current_logp = log_target(&current_q, target, target_mean, target_cov);

    let mut samples = Vec::with_capacity(n_samples);
    let mut n_accepted = 0u32;
    let total = n_samples + n_burn;

    for iter in 0..total {
        // Sample momentum p ~ N(0, I)
        let mut p: Vec<f64> = (0..d).map(|_| normal.sample(&mut rng)).collect();

        let mut q = current_q.clone();
        let current_k = 0.5 * p.iter().map(|pi| pi * pi).sum::<f64>();

        // Leapfrog integration
        // Half step for momentum
        let grad = grad_log_target(&q, target, target_mean, target_cov);
        for i in 0..d {
            p[i] += 0.5 * step_size * grad[i];
        }

        for _ in 0..n_leapfrog {
            // Full step for position
            for i in 0..d {
                q[i] += step_size * p[i];
            }
            // Full step for momentum (except last)
            let grad = grad_log_target(&q, target, target_mean, target_cov);
            for i in 0..d {
                p[i] += step_size * grad[i];
            }
        }

        // Half step for momentum (last)
        let grad = grad_log_target(&q, target, target_mean, target_cov);
        for i in 0..d {
            p[i] += 0.5 * step_size * grad[i];
        }

        // Negate momentum (reversibility)
        for pi in p.iter_mut() {
            *pi = -*pi;
        }

        let proposed_logp = log_target(&q, target, target_mean, target_cov);
        let proposed_k = 0.5 * p.iter().map(|pi| pi * pi).sum::<f64>();

        // Metropolis acceptance
        let log_alpha = (proposed_logp - proposed_k) - (current_logp - current_k);
        let u: f64 = (rng.next_u64() as f64) / (u64::MAX as f64);

        if u.ln() < log_alpha {
            current_q = q;
            current_logp = proposed_logp;
            if iter >= n_burn {
                n_accepted += 1;
            }
        }

        if iter >= n_burn {
            samples.push(current_q.clone());
        }
    }

    let acceptance_rate = if n_samples > 0 {
        n_accepted as f64 / n_samples as f64
    } else {
        0.0
    };

    (samples, acceptance_rate)
}

// ── Tests ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mh_gaussian() {
        let (samples, ar) = metropolis_hastings(
            500, 100, &[0.0], 1.0, 42, "gaussian", &[2.0], &[1.0],
        );
        assert_eq!(samples.len(), 500);
        assert!(ar > 0.1 && ar < 0.9, "acceptance rate {} should be moderate", ar);
        // Mean should be close to 2.0
        let mean: f64 = samples.iter().map(|s| s[0]).sum::<f64>() / 500.0;
        assert!((mean - 2.0).abs() < 0.5, "MH mean {} should be close to 2.0", mean);
    }

    #[test]
    fn test_hmc_gaussian() {
        let (samples, ar) = hamiltonian_monte_carlo(
            300, 50, &[0.0, 0.0], 0.1, 10, 42, "gaussian", &[1.0, 2.0], &[1.0, 1.0],
        );
        assert_eq!(samples.len(), 300);
        assert!(ar > 0.1, "HMC acceptance rate {} should be reasonable", ar);
        // Check means
        let m0: f64 = samples.iter().map(|s| s[0]).sum::<f64>() / 300.0;
        let m1: f64 = samples.iter().map(|s| s[1]).sum::<f64>() / 300.0;
        assert!((m0 - 1.0).abs() < 0.5, "HMC mean[0] {} should be close to 1.0", m0);
        assert!((m1 - 2.0).abs() < 0.5, "HMC mean[1] {} should be close to 2.0", m1);
    }

    #[test]
    fn test_mh_empty() {
        let (samples, ar) = metropolis_hastings(10, 0, &[], 1.0, 42, "gaussian", &[], &[]);
        assert!(samples.is_empty());
        assert_eq!(ar, 0.0);
    }

    #[test]
    fn test_hmc_rosenbrock() {
        let (samples, ar) = hamiltonian_monte_carlo(
            200, 50, &[0.0, 0.0], 0.01, 20, 42, "rosenbrock", &[0.0, 0.0], &[1.0, 1.0],
        );
        assert_eq!(samples.len(), 200);
        assert!(ar >= 0.0 && ar <= 1.0);
    }
}
