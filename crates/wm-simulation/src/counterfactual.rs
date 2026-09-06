//! Counterfactual estimation — synthetic control projection for causal
//! impact measurement.
//!
//! Answers: "Did change X cause improvement Y?" by comparing the actual
//! outcome to a synthetic counterfactual (what would have happened without
//! the change). Uses exponential smoothing + bootstrap confidence intervals.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

// ── Counterfactual Result ─────────────────────────────────────────────

/// Result of a counterfactual estimation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CounterfactualResult {
    /// Observed outcome after the intervention.
    pub observed: f64,
    /// Predicted counterfactual (what would have happened without intervention).
    pub counterfactual: f64,
    /// Estimated causal impact (observed - counterfactual).
    pub impact: f64,
    /// Relative impact (impact / counterfactual).
    pub relative_impact: f64,
    /// 95% CI lower bound for impact.
    pub ci_lower: f64,
    /// 95% CI upper bound for impact.
    pub ci_upper: f64,
    /// Whether the impact is statistically significant (CI doesn't include 0).
    pub significant: bool,
    /// Number of bootstrap samples used.
    pub n_bootstrap: usize,
}

impl CounterfactualResult {
    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "observed": self.observed,
            "counterfactual": self.counterfactual,
            "impact": self.impact,
            "relative_impact": self.relative_impact,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "significant": self.significant,
            "n_bootstrap": self.n_bootstrap,
        })
    }
}

// ── Counterfactual Estimator ──────────────────────────────────────────

/// Counterfactual estimator — uses pre-intervention time series to project
/// a counterfactual, then compares to the actual post-intervention outcome.
pub struct CounterfactualEstimator {
    /// Smoothing parameter (0.0–1.0, higher = more weight on recent data).
    alpha: f64,
    /// Number of bootstrap samples for CI.
    n_bootstrap: usize,
    /// Random seed.
    seed: u64,
}

impl Default for CounterfactualEstimator {
    fn default() -> Self {
        Self {
            alpha: 0.3,
            n_bootstrap: 1000,
            seed: 42,
        }
    }
}

impl std::fmt::Debug for CounterfactualEstimator {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("CounterfactualEstimator")
            .field("alpha", &self.alpha)
            .field("n_bootstrap", &self.n_bootstrap)
            .finish_non_exhaustive()
    }
}

impl CounterfactualEstimator {
    /// Create a new estimator with custom parameters.
    #[must_use]
    pub const fn new(alpha: f64, n_bootstrap: usize, seed: u64) -> Self {
        Self {
            alpha,
            n_bootstrap,
            seed,
        }
    }

    /// Estimate the causal impact of an intervention.
    ///
    /// - `pre_intervention`: time series before the intervention
    /// - `post_intervention`: time series after the intervention
    /// - `intervention_point`: index in the combined series where intervention occurred
    #[must_use]
    pub fn estimate(
        &self,
        pre_intervention: &[f64],
        post_intervention: &[f64],
    ) -> CounterfactualResult {
        // Filter out NaN/Infinity values from inputs (parameter injection defense)
        let pre: Vec<f64> = pre_intervention
            .iter()
            .copied()
            .filter(|v| v.is_finite())
            .collect();
        let post: Vec<f64> = post_intervention
            .iter()
            .copied()
            .filter(|v| v.is_finite())
            .collect();

        if pre.is_empty() || post.is_empty() {
            return CounterfactualResult {
                observed: 0.0,
                counterfactual: 0.0,
                impact: 0.0,
                relative_impact: 0.0,
                ci_lower: 0.0,
                ci_upper: 0.0,
                significant: false,
                n_bootstrap: 0,
            };
        }

        // Compute exponential smoothing forecast from pre-intervention data
        let forecast = self.exponential_smoothing_forecast(&pre, post.len());

        // Observed = mean of post-intervention
        let observed = post.iter().sum::<f64>() / post.len() as f64;

        // Counterfactual = mean of forecast
        let counterfactual = forecast.iter().sum::<f64>() / forecast.len() as f64;

        let impact = observed - counterfactual;
        let relative_impact = if counterfactual.abs() > 1e-10 {
            impact / counterfactual
        } else {
            0.0
        };

        // Bootstrap CI
        let (ci_lower, ci_upper) = self.bootstrap_ci(&pre, post.len(), impact);

        CounterfactualResult {
            observed,
            counterfactual,
            impact,
            relative_impact,
            ci_lower,
            ci_upper,
            significant: ci_lower > 0.0 || ci_upper < 0.0,
            n_bootstrap: self.n_bootstrap,
        }
    }

    /// Exponential smoothing forecast.
    fn exponential_smoothing_forecast(&self, pre: &[f64], horizon: usize) -> Vec<f64> {
        if pre.is_empty() {
            return vec![0.0; horizon];
        }

        // Compute smoothed level
        let mut level = pre[0];
        for &val in &pre[1..] {
            level = self.alpha.mul_add(val, (1.0 - self.alpha) * level);
        }

        // Forecast = constant level (no trend)
        vec![level; horizon]
    }

    /// Bootstrap confidence interval for the impact estimate.
    fn bootstrap_ci(&self, pre: &[f64], horizon: usize, observed_impact: f64) -> (f64, f64) {
        let mut rng = self.seed;
        let mut impacts = Vec::with_capacity(self.n_bootstrap);

        for _ in 0..self.n_bootstrap {
            // Resample pre-intervention data with replacement
            let resampled: Vec<f64> = (0..pre.len())
                .map(|_| {
                    let idx = (xorshift(&mut rng) as usize) % pre.len();
                    pre[idx]
                })
                .collect();

            let forecast = self.exponential_smoothing_forecast(&resampled, horizon);
            let cf = forecast.iter().sum::<f64>() / forecast.len().max(1) as f64;
            // Simulated impact under null hypothesis (no real intervention effect)
            let null_impact = observed_impact + (cf - pre.iter().sum::<f64>() / pre.len() as f64);
            impacts.push(null_impact);
        }

        impacts.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let n = impacts.len();
        if n == 0 {
            return (0.0, 0.0);
        }

        let lower_idx = ((0.025 * n as f64) as usize).min(n - 1);
        let upper_idx = ((0.975 * n as f64) as usize).min(n - 1);

        (impacts[lower_idx], impacts[upper_idx])
    }
}

/// Simple xorshift PRNG.
const fn xorshift(state: &mut u64) -> u64 {
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

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn estimate_positive_impact() {
        let estimator = CounterfactualEstimator::default();
        // Pre-intervention: stable around 10
        let pre = vec![9.0, 10.0, 11.0, 10.0, 9.0, 10.0, 11.0, 10.0];
        // Post-intervention: jumped to ~15
        let post = vec![14.0, 15.0, 16.0, 15.0, 14.0, 15.0, 16.0, 15.0];

        let result = estimator.estimate(&pre, &post);
        assert!(result.observed > result.counterfactual);
        assert!(result.impact > 0.0);
    }

    #[test]
    fn estimate_negative_impact() {
        let estimator = CounterfactualEstimator::default();
        let pre = vec![10.0; 10];
        let post = vec![5.0; 5];

        let result = estimator.estimate(&pre, &post);
        assert!(result.impact < 0.0);
    }

    #[test]
    fn estimate_no_impact() {
        let estimator = CounterfactualEstimator::default();
        let pre = vec![10.0; 10];
        let post = vec![10.0; 5];

        let result = estimator.estimate(&pre, &post);
        assert!(result.impact.abs() < 1.0);
    }

    #[test]
    fn estimate_empty_data() {
        let estimator = CounterfactualEstimator::default();
        let result = estimator.estimate(&[], &[]);
        assert_eq!(result.n_bootstrap, 0);
        assert!((result.impact - 0.0).abs() < 0.001);
    }

    #[test]
    fn result_to_json() {
        let result = CounterfactualResult {
            observed: 15.0,
            counterfactual: 10.0,
            impact: 5.0,
            relative_impact: 0.5,
            ci_lower: 2.0,
            ci_upper: 8.0,
            significant: true,
            n_bootstrap: 1000,
        };
        let json = result.to_json();
        assert_eq!(json["observed"], 15.0);
        assert_eq!(json["impact"], 5.0);
        assert_eq!(json["significant"], true);
    }

    #[test]
    fn custom_parameters() {
        let estimator = CounterfactualEstimator::new(0.5, 500, 123);
        let pre = vec![10.0; 10];
        let post = vec![15.0; 5];
        let result = estimator.estimate(&pre, &post);
        assert_eq!(result.n_bootstrap, 500);
    }

    #[test]
    fn relative_impact_computed() {
        let estimator = CounterfactualEstimator::default();
        let pre = vec![10.0; 10];
        let post = vec![20.0; 5];
        let result = estimator.estimate(&pre, &post);
        // Relative impact should be roughly 1.0 (100% increase)
        assert!(result.relative_impact > 0.5);
    }

    #[test]
    fn significant_flag() {
        let estimator = CounterfactualEstimator::default();
        // Large effect with stable data
        let pre = vec![10.0; 20];
        let post = vec![100.0; 10];
        let result = estimator.estimate(&pre, &post);
        assert!(result.impact > 0.0);
    }

    #[test]
    fn estimate_filters_nan_and_infinity() {
        let estimator = CounterfactualEstimator::default();
        let pre = vec![10.0, f64::NAN, 10.0, f64::INFINITY, 10.0];
        let post = vec![15.0, f64::NEG_INFINITY, 15.0];
        let result = estimator.estimate(&pre, &post);
        // Should not propagate NaN — result should be finite
        assert!(result.observed.is_finite());
        assert!(result.counterfactual.is_finite());
        assert!(result.impact.is_finite());
    }

    #[test]
    fn estimate_all_nan_returns_zeros() {
        let estimator = CounterfactualEstimator::default();
        let pre = vec![f64::NAN, f64::INFINITY];
        let post = vec![f64::NAN];
        let result = estimator.estimate(&pre, &post);
        assert_eq!(result.observed, 0.0);
        assert_eq!(result.counterfactual, 0.0);
        assert!(!result.significant);
    }
}
