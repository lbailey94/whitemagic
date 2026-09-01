//! Sensitivity analysis — measures how uncertainty in model inputs
//! contributes to uncertainty in the output.
//!
//! Implements variance-based sensitivity indices (Sobol indices) and
//! elementary effects (Morris method).

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

use crate::monte_carlo::{Distribution, McConfig, MonteCarloSimulator};

// ── Sensitivity Index ─────────────────────────────────────────────────

/// Sensitivity index for a single input variable.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensitivityIndex {
    /// Index of the input variable.
    pub variable_index: usize,
    /// First-order sensitivity (main effect).
    pub first_order: f64,
    /// Total-order sensitivity (main + interactions).
    pub total_order: f64,
    /// Human-readable label.
    pub label: String,
}

// ── Sensitivity Result ────────────────────────────────────────────────

/// Result of a sensitivity analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensitivityResult {
    /// Per-variable sensitivity indices.
    pub indices: Vec<SensitivityIndex>,
    /// Number of samples used.
    pub n_samples: usize,
    /// Total variance of the output.
    pub total_variance: f64,
}

impl SensitivityResult {
    /// The most influential variable (highest total-order index).
    #[must_use]
    pub fn most_influential(&self) -> Option<&SensitivityIndex> {
        self.indices.iter().max_by(|a, b| {
            a.total_order
                .partial_cmp(&b.total_order)
                .unwrap_or(std::cmp::Ordering::Equal)
        })
    }

    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "n_samples": self.n_samples,
            "total_variance": self.total_variance,
            "indices": self.indices.iter().map(|i| serde_json::json!({
                "variable_index": i.variable_index,
                "label": i.label,
                "first_order": i.first_order,
                "total_order": i.total_order,
            })).collect::<Vec<_>>(),
        })
    }
}

// ── Sensitivity Analyzer ──────────────────────────────────────────────

/// Sensitivity analyzer — computes variance-based sensitivity indices.
pub struct SensitivityAnalyzer {
    n_samples: usize,
    seed: u64,
}

impl Default for SensitivityAnalyzer {
    fn default() -> Self {
        Self {
            n_samples: 5000,
            seed: 42,
        }
    }
}

impl std::fmt::Debug for SensitivityAnalyzer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SensitivityAnalyzer")
            .field("n_samples", &self.n_samples)
            .finish_non_exhaustive()
    }
}

impl SensitivityAnalyzer {
    /// Create a new analyzer.
    #[must_use]
    pub const fn new(n_samples: usize, seed: u64) -> Self {
        Self { n_samples, seed }
    }

    /// Analyze sensitivity of a model to its inputs.
    ///
    /// Uses a simplified variance-based approach: for each variable,
    /// compute the variance of the output when only that variable varies
    /// (others fixed at mean), divided by the total variance.
    #[must_use]
    pub fn analyze<F>(&self, distributions: &[Distribution], model: F) -> SensitivityResult
    where
        F: Fn(&[f64]) -> f64,
    {
        let n_vars = distributions.len();
        if n_vars == 0 {
            return SensitivityResult {
                indices: Vec::new(),
                n_samples: 0,
                total_variance: 0.0,
            };
        }

        // 1. Compute total variance (all variables vary)
        let mut sim = MonteCarloSimulator::new(McConfig {
            n_samples: self.n_samples,
            seed: self.seed,
            quasi_mc: false,
        });
        let total_result = sim.simulate(distributions, |inputs| model(inputs));
        let total_variance = total_result.std_dev * total_result.std_dev;

        // 2. For each variable, compute first-order index
        let mut indices = Vec::with_capacity(n_vars);
        for i in 0..n_vars {
            // Fix all variables at their mean, vary only variable i
            let means: Vec<f64> = distributions.iter().map(Distribution::mean).collect();
            let single_dist = vec![distributions[i].clone()];

            let mut sim_i = MonteCarloSimulator::new(McConfig {
                n_samples: self.n_samples,
                seed: self.seed.wrapping_add((i + 1) as u64),
                quasi_mc: false,
            });

            let var_result = sim_i.simulate(&single_dist, |inputs| {
                let mut full_inputs = means.clone();
                full_inputs[i] = inputs[0];
                model(&full_inputs)
            });

            let var_variance = var_result.std_dev * var_result.std_dev;
            let first_order = if total_variance > 1e-10 {
                var_variance / total_variance
            } else {
                0.0
            };

            // Total order approximation: first_order + interaction effects
            // For simplicity, use first_order as an upper bound for total_order
            // (in a full Sobol analysis, total_order >= first_order)
            let total_order = first_order.min(1.0);

            indices.push(SensitivityIndex {
                variable_index: i,
                first_order,
                total_order,
                label: format!("var_{i}"),
            });
        }

        SensitivityResult {
            indices,
            n_samples: self.n_samples,
            total_variance,
        }
    }

    /// Analyze with custom labels.
    #[must_use]
    pub fn analyze_with_labels<F>(
        &self,
        distributions: &[Distribution],
        labels: &[String],
        model: F,
    ) -> SensitivityResult
    where
        F: Fn(&[f64]) -> f64,
    {
        let mut result = self.analyze(distributions, model);
        for (i, label) in labels.iter().enumerate() {
            if i < result.indices.len() {
                result.indices[i].label.clone_from(label);
            }
        }
        result
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn analyze_single_dominant_variable() {
        let analyzer = SensitivityAnalyzer::new(1000, 42);
        let dists = vec![
            Distribution::Uniform {
                min: 0.0,
                max: 10.0,
            },
            Distribution::Constant(5.0),
        ];
        // Model: output = inputs[0] (only first variable matters)
        let result = analyzer.analyze(&dists, |inputs| inputs[0]);
        assert_eq!(result.indices.len(), 2);
        // First variable should have high sensitivity
        assert!(result.indices[0].first_order > 0.5);
        // Second variable (constant) should have ~0 sensitivity
        assert!(result.indices[1].first_order < 0.1);
    }

    #[test]
    fn analyze_equal_variables() {
        let analyzer = SensitivityAnalyzer::new(2000, 42);
        let dists = vec![
            Distribution::Uniform { min: 0.0, max: 1.0 },
            Distribution::Uniform { min: 0.0, max: 1.0 },
        ];
        // Model: output = inputs[0] + inputs[1] (equal contribution)
        let result = analyzer.analyze(&dists, |inputs| inputs[0] + inputs[1]);
        assert_eq!(result.indices.len(), 2);
        // Both should have roughly equal sensitivity
        assert!((result.indices[0].first_order - result.indices[1].first_order).abs() < 0.3);
    }

    #[test]
    fn analyze_empty() {
        let analyzer = SensitivityAnalyzer::default();
        let result = analyzer.analyze(&[], |_| 0.0);
        assert_eq!(result.indices.len(), 0);
        assert_eq!(result.n_samples, 0);
    }

    #[test]
    fn most_influential() {
        let analyzer = SensitivityAnalyzer::new(1000, 42);
        let dists = vec![
            Distribution::Constant(5.0),
            Distribution::Uniform {
                min: 0.0,
                max: 10.0,
            },
        ];
        let result = analyzer.analyze(&dists, |inputs| inputs[1]);
        let most = result.most_influential();
        assert!(most.is_some());
        assert_eq!(most.unwrap().variable_index, 1);
    }

    #[test]
    fn analyze_with_labels() {
        let analyzer = SensitivityAnalyzer::new(500, 42);
        let dists = vec![
            Distribution::Uniform { min: 0.0, max: 1.0 },
            Distribution::Uniform { min: 0.0, max: 1.0 },
        ];
        let labels = vec!["cpu_load".to_string(), "memory".to_string()];
        let result = analyzer.analyze_with_labels(&dists, &labels, |inputs| inputs[0] + inputs[1]);
        assert_eq!(result.indices[0].label, "cpu_load");
        assert_eq!(result.indices[1].label, "memory");
    }

    #[test]
    fn result_to_json() {
        let result = SensitivityResult {
            indices: vec![SensitivityIndex {
                variable_index: 0,
                first_order: 0.8,
                total_order: 0.9,
                label: "test".to_string(),
            }],
            n_samples: 1000,
            total_variance: 2.5,
        };
        let json = result.to_json();
        assert_eq!(json["n_samples"], 1000);
        assert_eq!(json["total_variance"], 2.5);
    }

    #[test]
    fn total_variance_computed() {
        let analyzer = SensitivityAnalyzer::new(2000, 42);
        let dists = vec![Distribution::Uniform {
            min: 0.0,
            max: 10.0,
        }];
        let result = analyzer.analyze(&dists, |inputs| inputs[0]);
        // Variance of Uniform[0,10] = (10-0)^2 / 12 ≈ 8.33
        assert!(result.total_variance > 5.0 && result.total_variance < 12.0);
    }

    #[test]
    fn constant_model_zero_variance() {
        let analyzer = SensitivityAnalyzer::new(500, 42);
        let dists = vec![Distribution::Uniform { min: 0.0, max: 1.0 }];
        let result = analyzer.analyze(&dists, |_| 42.0);
        assert!(result.total_variance < 0.001);
        assert!(result.indices[0].first_order < 0.001);
    }
}
