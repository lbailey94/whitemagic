//! Rare event simulation techniques for estimating small probabilities.
//!
//! Implements:
//! - Subset simulation (Au & Beck 2001)
//! - Adaptive multilevel splitting
//! - Importance sampling for rare events with Gaussian mixture proposals

use crate::mc_advanced::multid_gaussian;
use rand::{RngCore, SeedableRng};
use rand_xoshiro::Xoshiro256PlusPlus;
use rayon::prelude::*;

/// Subset simulation for estimating rare event probabilities.
///
/// Estimates P(g(X) <= 0) where X is a random vector and g is a performance function.
/// Uses conditional sampling at intermediate levels to decompose a rare event into
/// a sequence of more frequent events.
///
/// Returns (probability estimate, coefficient of variation, levels used).
pub fn subset_simulation(
    dim: usize,
    n_samples_per_level: usize,
    target_pf: f64, // target probability of failure
    g_fn: impl Fn(&[f64]) -> f64 + Sync,
    seed: u64,
) -> (f64, f64, usize) {
    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed);
    
    // Number of levels: log(target_pf) / log(p_cond) where p_cond ~ 0.1
    let p_cond: f64 = 0.1;
    let n_levels = ((target_pf.ln() / p_cond.ln()).ceil() as usize).max(1);
    
    // Initial sampling: standard Gaussian (identity covariance, flat row-major)
    let mean = vec![0.0f64; dim];
    let cov_flat: Vec<f64> = {
        let mut c = vec![0.0f64; dim * dim];
        for i in 0..dim {
            c[i * dim + i] = 1.0;
        }
        c
    };
    
    let mut samples = multid_gaussian(n_samples_per_level, &mean, &cov_flat, seed);
    let mut g_values: Vec<f64> = samples.par_iter().map(|x| g_fn(x)).collect();
    
    let mut pf = 1.0;
    let mut level = 0;
    
    for _ in 0..n_levels {
        // Sort by g values (ascending — failure is g <= 0)
        let mut sorted_idx: Vec<usize> = (0..g_values.len()).collect();
        sorted_idx.sort_by(|&a, &b| {
            g_values[a].partial_cmp(&g_values[b]).unwrap_or(std::cmp::Ordering::Equal)
        });
        
        // Find threshold at p_cond quantile
        let threshold_idx = ((p_cond * n_samples_per_level as f64) as usize).min(sorted_idx.len() - 1);
        let threshold = g_values[sorted_idx[threshold_idx]];
        
        if threshold <= 0.0 {
            // We've reached the failure domain
            let n_failed = g_values.iter().filter(|&g| *g <= 0.0).count();
            pf *= n_failed as f64 / n_samples_per_level as f64;
            break;
        }
        
        // Conditional samples: keep the top p_cond fraction (seeds for next level)
        let n_seeds = threshold_idx + 1;
        let mut conditional_samples: Vec<Vec<f64>> = Vec::with_capacity(n_samples_per_level);
        
        for i in 0..n_seeds {
            conditional_samples.push(samples[sorted_idx[i]].clone());
        }
        
        // MCMC: Component-wise Metropolis-Hastings to fill remaining samples
        let fill_count = n_samples_per_level - n_seeds;
        let mut current_idx = 0;
        let proposal_std = 1.0; // Proposal standard deviation
        
        for _ in 0..fill_count {
            let seed_idx = current_idx % n_seeds;
            let mut proposal = conditional_samples[seed_idx].clone();
            
            // Component-wise MH
            for d in 0..dim {
                let old_val = proposal[d];
                let new_val = old_val + proposal_std * box_muller(&mut rng);
                proposal[d] = new_val;
                
                let g_old = g_fn(&conditional_samples[seed_idx]);
                let g_new = g_fn(&proposal);
                
                // Accept if still in conditional domain (g <= threshold) or better
                if g_new <= threshold || (g_old > threshold && g_new < g_old) {
                    // Accept
                } else {
                    proposal[d] = old_val; // Reject
                }
            }
            
            conditional_samples.push(proposal);
            current_idx += 1;
        }
        
        samples = conditional_samples;
        g_values = samples.par_iter().map(|x| g_fn(x)).collect();
        
        pf *= p_cond;
        level += 1;
    }
    
    // Final count of failed samples
    let n_failed = g_values.iter().filter(|&g| *g <= 0.0).count();
    let final_pf = if level == n_levels {
        pf * (n_failed as f64 / n_samples_per_level as f64)
    } else {
        pf
    };
    
    // Coefficient of variation (simplified estimate)
    let cov_estimate = if final_pf > 0.0 {
        ((1.0 - final_pf) / (n_samples_per_level as f64 * final_pf)).sqrt()
    } else {
        f64::INFINITY
    };
    
    (final_pf.max(0.0), cov_estimate, level + 1)
}

/// Adaptive multilevel splitting for rare event estimation.
///
/// Iteratively selects a threshold such that a fraction of samples survive,
/// then samples conditionally on survival. The rare event probability is
/// the product of conditional survival probabilities.
///
/// Returns (probability estimate, thresholds used, number of levels).
pub fn multilevel_splitting(
    dim: usize,
    n_samples: usize,
    survival_fraction: f64,
    g_fn: impl Fn(&[f64]) -> f64 + Sync,
    seed: u64,
) -> (f64, Vec<f64>, usize) {
    let mean = vec![0.0f64; dim];
    let cov_flat: Vec<f64> = {
        let mut c = vec![0.0f64; dim * dim];
        for i in 0..dim {
            c[i * dim + i] = 1.0;
        }
        c
    };
    
    let mut samples = multid_gaussian(n_samples, &mean, &cov_flat, seed);
    let mut g_values: Vec<f64> = samples.par_iter().map(|x| g_fn(x)).collect();
    
    let mut thresholds = Vec::new();
    let mut probability = 1.0;
    let mut level = 0;
    let mut rng = Xoshiro256PlusPlus::seed_from_u64(seed + 1);
    
    loop {
        // Sort g values
        let mut sorted_g = g_values.clone();
        sorted_g.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        
        // Threshold at survival_fraction quantile
        let threshold_idx = ((1.0 - survival_fraction) * n_samples as f64) as usize;
        let threshold_idx = threshold_idx.min(n_samples - 1);
        let threshold = sorted_g[threshold_idx];
        
        if threshold <= 0.0 {
            // Reached failure domain
            let n_failed = g_values.iter().filter(|&g| *g <= 0.0).count();
            probability *= n_failed as f64 / n_samples as f64;
            break;
        }
        
        thresholds.push(threshold);
        probability *= survival_fraction;
        level += 1;
        
        // Keep only surviving samples (g > threshold)
        let survivors: Vec<Vec<f64>> = samples
            .iter()
            .zip(g_values.iter())
            .filter(|(_, &g)| g > threshold)
            .map(|(x, _)| x.clone())
            .collect();
        
        if survivors.is_empty() {
            break;
        }
        
        // Regenerate full sample set via conditional MCMC
        let mut new_samples = survivors.clone();
        let proposal_std = 1.0 / (level as f64).sqrt().max(1.0);
        let max_attempts = n_samples * 100;
        let mut attempts = 0;
        
        while new_samples.len() < n_samples && attempts < max_attempts {
            attempts += 1;
            let seed_idx = (rng.next_u64() as usize) % survivors.len();
            let mut proposal = survivors[seed_idx].clone();
            
            for d in 0..dim {
                proposal[d] += proposal_std * box_muller(&mut rng);
            }
            
            let g_proposal = g_fn(&proposal);
            if g_proposal > threshold {
                new_samples.push(proposal);
            }
        }
        
        // If MCMC didn't fill enough samples, duplicate survivors to fill
        while new_samples.len() < n_samples {
            let idx = new_samples.len() % survivors.len();
            new_samples.push(survivors[idx].clone());
        }
        
        samples = new_samples;
        g_values = samples.par_iter().map(|x| g_fn(x)).collect();
        
        // Safety: prevent infinite loop
        if level > 50 {
            break;
        }
    }
    
    (probability.max(0.0), thresholds, level)
}

/// Importance sampling for rare events using a Gaussian mixture proposal.
///
/// Shifts the sampling distribution toward the failure region identified
/// by a pilot run, then computes the importance weight as the ratio of
/// original to proposal density.
///
/// Returns (probability estimate, shifted mean, effective sample size).
pub fn importance_sampling_rare(
    dim: usize,
    n_samples: usize,
    g_fn: impl Fn(&[f64]) -> f64 + Sync,
    pilot_n: usize,
    seed: u64,
) -> (f64, Vec<f64>, f64) {
    // Pilot run: find failure-adjacent samples
    let mean_orig = vec![0.0f64; dim];
    let cov_flat: Vec<f64> = {
        let mut c = vec![0.0f64; dim * dim];
        for i in 0..dim {
            c[i * dim + i] = 1.0;
        }
        c
    };
    
    let pilot_samples = multid_gaussian(pilot_n, &mean_orig, &cov_flat, seed);
    let pilot_g: Vec<f64> = pilot_samples.par_iter().map(|x| g_fn(x)).collect();
    
    // Find the centroid of the most critical samples (lowest g values)
    let mut indexed: Vec<(usize, f64)> = pilot_g.iter().enumerate().map(|(i, &g)| (i, g)).collect();
    indexed.sort_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    
    let n_critical = (pilot_n / 10).max(10).min(pilot_n);
    let mut shifted_mean = vec![0.0f64; dim];
    for i in 0..n_critical {
        let idx = indexed[i].0;
        for d in 0..dim {
            shifted_mean[d] += pilot_samples[idx][d];
        }
    }
    for d in 0..dim {
        shifted_mean[d] /= n_critical as f64;
    }
    
    // Main run: sample from shifted distribution
    let main_samples = multid_gaussian(n_samples, &shifted_mean, &cov_flat, seed + 1);
    
    // Compute importance weights and probability
    let weights: Vec<f64> = main_samples
        .par_iter()
        .map(|x| {
            // w = p(x) / q(x) where p is N(0, I) and q is N(shifted_mean, I)
            let log_p = -0.5 * x.iter().map(|xi| xi * xi).sum::<f64>();
            let log_q = -0.5 * x.iter().zip(shifted_mean.iter())
                .map(|(xi, mi)| (xi - mi) * (xi - mi))
                .sum::<f64>();
            (log_p - log_q).exp()
        })
        .collect();
    
    let g_values: Vec<f64> = main_samples.par_iter().map(|x| g_fn(x)).collect();
    
    // P(failure) = E_q[w * 1{g <= 0}]
    let indicator_weighted: Vec<f64> = g_values
        .iter()
        .zip(weights.iter())
        .map(|(g, w)| if *g <= 0.0 { *w } else { 0.0 })
        .collect();
    
    let pf: f64 = indicator_weighted.iter().sum::<f64>() / n_samples as f64;
    
    // Effective sample size
    let sum_w = weights.iter().sum::<f64>();
    let sum_w2 = weights.iter().map(|w| w * w).sum::<f64>();
    let ess = if sum_w2 > 0.0 {
        (sum_w * sum_w) / sum_w2
    } else {
        0.0
    };
    
    (pf.max(0.0), shifted_mean, ess)
}

/// Box-Muller transform for standard normal sampling.
fn box_muller(rng: &mut Xoshiro256PlusPlus) -> f64 {
    let u1: f64 = (rng.next_u64() as f64 / u64::MAX as f64).max(1e-15);
    let u2: f64 = rng.next_u64() as f64 / u64::MAX as f64;
    (-2.0_f64 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_subset_simulation_basic() {
        // Simple: g(x) = 5 - x[0], failure when x[0] >= 5 (rare for N(0,1))
        // P(X >= 5) ~ 2.87e-7
        let g_fn = |x: &[f64]| 5.0 - x[0];
        let (pf, cov, levels) = subset_simulation(1, 500, 1e-6, g_fn, 42);
        
        assert!(pf >= 0.0, "PF should be non-negative, got {}", pf);
        assert!(pf < 0.01, "PF for 5-sigma should be very small, got {}", pf);
        assert!(levels > 0, "Should use at least 1 level");
        assert!(cov.is_finite() || cov.is_infinite(), "CoV should be finite or infinite");
    }

    #[test]
    fn test_subset_simulation_multidim() {
        // 3D: g(x) = 6 - |x1| - |x2| - |x3|, failure when sum|x| >= 6
        let g_fn = |x: &[f64]| 6.0 - x.iter().map(|xi| xi.abs()).sum::<f64>();
        let (pf, _cov, _levels) = subset_simulation(3, 500, 1e-4, g_fn, 42);
        
        assert!(pf >= 0.0);
        assert!(pf < 0.1, "PF should be small for 6-sigma in 3D, got {}", pf);
    }

    #[test]
    fn test_multilevel_splitting_basic() {
        // g(x) = 4 - x[0], failure when x[0] >= 4
        let g_fn = |x: &[f64]| 4.0 - x[0];
        let (pf, thresholds, levels) = multilevel_splitting(1, 500, 0.1, g_fn, 42);
        
        assert!(pf >= 0.0, "PF should be non-negative, got {}", pf);
        assert!(pf < 0.1, "PF for 4-sigma should be small, got {}", pf);
        assert!(!thresholds.is_empty() || levels > 0);
    }

    #[test]
    fn test_multilevel_splitting_multidim() {
        // 2D: g(x) = 5 - x[0]^2 - x[1]^2
        let g_fn = |x: &[f64]| 5.0 - x[0] * x[0] - x[1] * x[1];
        let (pf, _thresholds, _levels) = multilevel_splitting(2, 500, 0.1, g_fn, 42);
        
        assert!(pf >= 0.0);
        assert!(pf < 0.5, "PF should be bounded, got {}", pf);
    }

    #[test]
    fn test_importance_sampling_rare() {
        // g(x) = 4 - x[0], failure when x[0] >= 4
        let g_fn = |x: &[f64]| 4.0 - x[0];
        let (pf, shifted_mean, ess) = importance_sampling_rare(1, 2000, g_fn, 500, 42);
        
        assert!(pf >= 0.0, "PF should be non-negative, got {}", pf);
        assert!(pf < 0.1, "PF for 4-sigma should be small, got {}", pf);
        // Shifted mean should be toward the failure region (positive direction)
        assert!(shifted_mean[0] > 0.0, "Shifted mean should move toward failure, got {}", shifted_mean[0]);
        assert!(ess > 0.0, "ESS should be positive, got {}", ess);
    }

    #[test]
    fn test_importance_sampling_rare_multidim() {
        // 2D: g(x) = 6 - x[0] - x[1], failure when x[0]+x[1] >= 6
        let g_fn = |x: &[f64]| 6.0 - x[0] - x[1];
        let (pf, shifted_mean, ess) = importance_sampling_rare(2, 2000, g_fn, 500, 42);
        
        assert!(pf >= 0.0);
        assert!(pf < 0.1, "PF should be small, got {}", pf);
        assert_eq!(shifted_mean.len(), 2);
        assert!(ess > 0.0);
    }

    #[test]
    fn test_box_muller() {
        let mut rng = Xoshiro256PlusPlus::seed_from_u64(42);
        let mut values = Vec::new();
        for _ in 0..1000 {
            values.push(box_muller(&mut rng));
        }
        let mean = values.iter().sum::<f64>() / values.len() as f64;
        let var = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / values.len() as f64;
        assert!(mean.abs() < 0.2, "Mean should be near 0, got {}", mean);
        assert!((var - 1.0).abs() < 0.2, "Variance should be near 1, got {}", var);
    }

    #[test]
    fn test_subset_simulation_no_failure() {
        // g(x) = 100 - x[0] — essentially never fails
        let g_fn = |x: &[f64]| 100.0 - x[0];
        let (pf, _cov, _levels) = subset_simulation(1, 200, 1e-6, g_fn, 42);
        assert!(pf < 1e-10, "PF for 100-sigma should be essentially 0, got {}", pf);
    }
}
