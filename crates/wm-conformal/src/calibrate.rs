//! Empirical coverage evaluation for conformal predictors.
//!
//! The conformal guarantee is *marginal*: it holds on average over the
//! data distribution, not per-sample. This module provides the standard
//! way to *verify* the guarantee on a held-out test set and to monitor
//! it in production (drift detection: if empirical coverage drops below
//! `1 − α`, the calibration is stale and should be refitted).

use serde::{Deserialize, Serialize};

/// Coverage report for a conformal predictor evaluated on test data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoverageReport {
    /// Number of test examples evaluated.
    pub n: usize,
    /// Number of examples where the prediction set contained the truth.
    pub covered: usize,
    /// Empirical coverage (covered / n).
    pub empirical_coverage: f64,
    /// Target coverage (1 − α).
    pub target_coverage: f64,
    /// Whether empirical coverage meets the target (with 5% slack).
    pub within_guarantee: bool,
}

impl CoverageReport {
    /// Evaluate a classifier's prediction sets against true labels.
    ///
    /// `predictor` is a closure returning the prediction set for a sample;
    /// `truths` are the true class labels.
    pub fn evaluate_classifier<F>(predictor: &F, truths: &[usize], alpha: f64) -> Self
    where
        F: Fn() -> Vec<usize>,
    {
        let n = truths.len();
        let covered = truths.iter().filter(|&&t| predictor().contains(&t)).count();
        Self::finish(n, covered, alpha)
    }

    /// Evaluate a list of prediction sets against true labels.
    ///
    /// `sets[i]` is the prediction set for sample `i`; `truths[i]` is the
    /// true label. Slices must have equal length (excess is ignored).
    #[must_use]
    pub fn evaluate_sets(sets: &[Vec<usize>], truths: &[usize], alpha: f64) -> Self {
        let n = sets.len().min(truths.len());
        let covered = sets
            .iter()
            .zip(truths.iter())
            .take(n)
            .filter(|(set, t)| set.contains(t))
            .count();
        Self::finish(n, covered, alpha)
    }

    /// Evaluate a regressor's intervals against true values.
    #[must_use]
    pub fn evaluate_regressor(
        intervals: &[crate::split::PredictionInterval],
        truths: &[f64],
        alpha: f64,
    ) -> Self {
        let n = truths.len().min(intervals.len());
        let covered = truths
            .iter()
            .zip(intervals.iter())
            .take(n)
            .filter(|(t, iv)| iv.contains(**t))
            .count();
        Self::finish(n, covered, alpha)
    }

    fn finish(n: usize, covered: usize, alpha: f64) -> Self {
        let empirical_coverage = if n > 0 {
            covered as f64 / n as f64
        } else {
            0.0
        };
        let target_coverage = 1.0 - alpha;
        // Small-sample slack: allow up to 5 percentage points below target
        // (finite-sample guarantees have variance ~ 1/√n).
        let within_guarantee = empirical_coverage + 0.05 >= target_coverage;
        Self {
            n,
            covered,
            empirical_coverage,
            target_coverage,
            within_guarantee,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn perfect_predictor_reports_full_coverage() {
        let truths = vec![0, 1, 2, 0, 1];
        let report = CoverageReport::evaluate_classifier(
            &(|| vec![0, 1, 2]), // always covers everything
            &truths,
            0.1,
        );
        assert_eq!(report.n, 5);
        assert_eq!(report.covered, 5);
        assert_eq!(report.empirical_coverage, 1.0);
        assert!(report.within_guarantee);
    }

    #[test]
    fn zero_coverage_reports_failure() {
        let truths = vec![0, 1];
        let report = CoverageReport::evaluate_classifier(
            &(|| vec![5]), // never contains the truth
            &truths,
            0.1,
        );
        assert_eq!(report.empirical_coverage, 0.0);
        assert!(!report.within_guarantee);
    }

    #[test]
    fn regressor_coverage() {
        use crate::PredictionInterval;
        let ivs = vec![
            PredictionInterval {
                lower: 0.0,
                upper: 2.0,
                point: 1.0,
                alpha: 0.1,
                guarantee: 0.9,
            },
            PredictionInterval {
                lower: 10.0,
                upper: 12.0,
                point: 11.0,
                alpha: 0.1,
                guarantee: 0.9,
            },
        ];
        let report = CoverageReport::evaluate_regressor(&ivs, &[1.0, 11.5], 0.1);
        assert_eq!(report.covered, 2);
        assert!(report.within_guarantee);
    }

    #[test]
    fn empty_input_does_not_panic() {
        let report = CoverageReport::evaluate_regressor(&[], &[], 0.1);
        assert_eq!(report.n, 0);
        assert_eq!(report.empirical_coverage, 0.0);
    }

    #[test]
    fn evaluate_sets_counts_coverage() {
        let sets = vec![vec![0, 1], vec![2], vec![0, 1, 2]];
        let truths = vec![0, 2, 5];
        let report = CoverageReport::evaluate_sets(&sets, &truths, 0.1);
        assert_eq!(report.n, 3);
        assert_eq!(report.covered, 2);
        assert!((report.empirical_coverage - 2.0 / 3.0).abs() < 1e-9);
        assert!(!report.within_guarantee);
    }

    #[test]
    fn evaluate_sets_truncates_to_shortest() {
        let sets = vec![vec![0]];
        let truths = vec![0, 1, 2];
        let report = CoverageReport::evaluate_sets(&sets, &truths, 0.1);
        assert_eq!(report.n, 1);
        assert_eq!(report.covered, 1);
    }

    #[test]
    fn evaluate_sets_empty() {
        let report = CoverageReport::evaluate_sets(&[], &[], 0.1);
        assert_eq!(report.n, 0);
        assert_eq!(report.empirical_coverage, 0.0);
        assert!(!report.within_guarantee);
    }
}
