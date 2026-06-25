//! Information-Theoretic Exploration (Objective P)
//!
//! Uses Shannon entropy and KL divergence to prioritize improvements
//! that maximize information gain — regardless of outcome.

use std::f64::consts::LOG2_E;

// log2(x) = ln(x) * log2(e) where log2(e) = 1/ln(2) ≈ 1.4427

/// Shannon entropy of a Bernoulli distribution with success probability p.
///
/// H(p) = -p·log2(p) - (1-p)·log2(1-p)
///
/// Returns 0 for p=0 or p=1 (no uncertainty).
pub fn shannon_entropy(p: f64) -> f64 {
    if p <= 0.0 || p >= 1.0 {
        return 0.0;
    }
    -p * (p.ln() * LOG2_E) - (1.0 - p) * ((1.0 - p).ln() * LOG2_E)
}

/// KL divergence D(P || Q) for Bernoulli distributions.
///
/// D(P||Q) = p·log(p/q) + (1-p)·log((1-p)/(1-q))
pub fn kl_divergence(p: f64, q: f64) -> f64 {
    let p = clamp_bernoulli(p);
    let q = clamp_bernoulli(q);
    p * (p / q).ln() + (1.0 - p) * ((1.0 - p) / (1.0 - q)).ln()
}

/// Expected information gain from observing an improvement outcome.
///
/// IG = H(P(success)) - [P(success) · H(P(success | observed_success))
///                       + P(failure) · H(P(success | observed_failure))]
///
/// Uses Beta(α, β) posterior update.
pub fn information_gain(p_success: f64, n_prior: i32) -> f64 {
    if p_success <= 0.0 || p_success >= 1.0 {
        return 0.0;
    }

    let n = n_prior as f64;
    let alpha = (p_success * n).max(0.5);
    let beta = ((1.0 - p_success) * n).max(0.5);

    // Posterior after success
    let p_after_success = (alpha + 1.0) / (alpha + beta + 1.0);
    // Posterior after failure
    let p_after_failure = alpha / (alpha + beta + 1.0);

    // Entropy before observation
    let h_prior = shannon_entropy(p_success);

    // Expected entropy after observation
    let h_after = p_success * shannon_entropy(p_after_success)
        + (1.0 - p_success) * shannon_entropy(p_after_failure);

    (h_prior - h_after).max(0.0)
}

/// Compute overall system uncertainty from a list of confidence values.
///
/// High variance in confidences → high uncertainty.
pub fn system_uncertainty(confidences: &[f64]) -> f64 {
    if confidences.is_empty() {
        return 0.0;
    }
    let total: f64 = confidences.iter().map(|&c| shannon_entropy(c)).sum();
    total / confidences.len() as f64
}

/// Adaptive exploration weights (α/β/γ) for scoring.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AdaptiveWeights {
    pub alpha: f64, // predicted_impact weight
    pub beta: f64,  // information_gain weight
    pub gamma: f64, // novelty weight
}

impl Default for AdaptiveWeights {
    fn default() -> Self {
        Self {
            alpha: 0.5,
            beta: 0.3,
            gamma: 0.2,
        }
    }
}

impl AdaptiveWeights {
    /// Adapt weights based on current system uncertainty.
    pub fn adapt(&mut self, system_entropy: f64, max_entropy: f64) {
        if max_entropy <= 0.0 {
            return;
        }
        let normalized = (system_entropy / max_entropy).min(1.0);
        self.alpha = 0.3 + 0.4 * (1.0 - normalized);
        self.beta = 0.1 + 0.5 * normalized;
        self.gamma = 0.2;
        let total = self.alpha + self.beta + self.gamma;
        if total > 0.0 {
            self.alpha /= total;
            self.beta /= total;
            self.gamma /= total;
        }
    }

    /// Compute exploration score: α·impact + β·IG + γ·novelty
    pub fn score(
        &self,
        predicted_impact: f64,
        p_success: f64,
        novelty: f64,
        n_prior: i32,
    ) -> f64 {
        let ig = information_gain(p_success, n_prior);
        self.alpha * predicted_impact + self.beta * ig + self.gamma * novelty
    }
}

fn clamp_bernoulli(p: f64) -> f64 {
    if p <= 0.0 {
        1e-10
    } else if p >= 1.0 {
        1.0 - 1e-10
    } else {
        p
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shannon_entropy_half() {
        let h = shannon_entropy(0.5);
        assert!((h - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_shannon_entropy_bounds() {
        assert_eq!(shannon_entropy(0.0), 0.0);
        assert_eq!(shannon_entropy(1.0), 0.0);
    }

    #[test]
    fn test_kl_divergence_same() {
        let d = kl_divergence(0.5, 0.5);
        assert!(d.abs() < 1e-9);
    }

    #[test]
    fn test_information_gain_positive() {
        let ig = information_gain(0.5, 10);
        assert!(ig > 0.0);
    }

    #[test]
    fn test_information_gain_bounds() {
        assert_eq!(information_gain(0.0, 10), 0.0);
        assert_eq!(information_gain(1.0, 10), 0.0);
    }

    #[test]
    fn test_system_uncertainty() {
        let u = system_uncertainty(&[0.5, 0.5, 0.5]);
        assert!((u - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_adaptive_weights() {
        let mut w = AdaptiveWeights::default();
        w.adapt(0.0, 1.0); // No uncertainty → exploit
        assert!(w.alpha > w.beta);
        w.adapt(1.0, 1.0); // Max uncertainty → explore
        assert!(w.beta > w.alpha);
    }

    #[test]
    fn test_score() {
        let w = AdaptiveWeights::default();
        let s = w.score(0.8, 0.7, 0.5, 10);
        assert!(s > 0.0);
    }
}
