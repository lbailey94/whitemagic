//! Split conformal prediction.
//!
//! The core idea: on a calibration set, compute a *nonconformity score*
//! for each example (how much the model "disagrees" with the true
//! outcome). The `⌈(n+1)(1−α)⌉`-th smallest score becomes the quantile
//! threshold `q`. At inference, a candidate outcome is included in the
//! prediction set iff its nonconformity score ≤ `q`.
//!
//! Because the calibration scores are exchangeable with future test
//! scores (i.i.d. assumption), the coverage guarantee holds
//! distribution-free:
//!
//! ```text
//! P(y_test ∈ C(x_test)) ≥ 1 − α
//! ```
//!
//! (Mondrian / class-conditional variants tighten this to per-class
//! guarantees; APS reduces set size for calibrated models.)

use crate::ConformalError;
use serde::{Deserialize, Serialize};

/// Split conformal classifier — label prediction sets with guaranteed
/// marginal coverage.
///
/// # Example
///
/// ```
/// use wm_conformal::SplitConformalClassifier;
///
/// let mut cp = SplitConformalClassifier::new(0.1).unwrap(); // 90% coverage
/// // Calibrate with (model_scores, true_label) pairs
/// cp.add_sample(&[0.9, 0.05, 0.05], 0).unwrap();
/// cp.add_sample(&[0.1, 0.85, 0.05], 1).unwrap();
/// cp.add_sample(&[0.2, 0.3, 0.5], 2).unwrap();
/// cp.fit().unwrap();
///
/// let set = cp.predict_set(&[0.8, 0.1, 0.1]).unwrap();
/// assert_eq!(set.classes, vec![0]);
/// ```
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SplitConformalClassifier {
    /// Target miscoverage level α (coverage ≥ 1−α).
    alpha: f64,
    /// Nonconformity scores from the calibration set (1 − score).
    scores: Vec<f64>,
    /// Fitted quantile threshold q.
    threshold: Option<f64>,
    /// Number of classes seen during calibration.
    n_classes: usize,
}

impl SplitConformalClassifier {
    /// Create a classifier with miscoverage level `alpha` (e.g. `0.1` for
    /// 90% coverage). `alpha` must be in `(0, 1)`.
    pub fn new(alpha: f64) -> Result<Self, ConformalError> {
        if !(0.0 < alpha && alpha < 1.0) {
            return Err(ConformalError::InvalidAlpha(alpha));
        }
        Ok(Self {
            alpha,
            scores: Vec::new(),
            threshold: None,
            n_classes: 0,
        })
    }

    /// Record a calibration sample: `scores[i]` is the model's probability
    /// for class `i`, `true_label` is the observed class.
    pub fn add_sample(&mut self, scores: &[f64], true_label: usize) -> Result<(), ConformalError> {
        if scores.is_empty() {
            return Err(ConformalError::EmptyScores);
        }
        if true_label >= scores.len() {
            return Err(ConformalError::ClassIndexOutOfRange(
                true_label,
                scores.len(),
            ));
        }
        self.n_classes = self.n_classes.max(scores.len());
        // Nonconformity = 1 − model score for the true class.
        let score = 1.0 - scores[true_label];
        self.scores.push(score.clamp(0.0, 1.0));
        Ok(())
    }

    /// Fit the quantile threshold from calibration scores. Must be called
    /// after collecting samples and before `predict_set`.
    pub fn fit(&mut self) -> Result<(), ConformalError> {
        let n = self.scores.len();
        if n < 2 {
            return Err(ConformalError::InsufficientSamples(n));
        }
        let mut sorted = self.scores.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        // Quantile index: ⌈(n+1)(1−α)⌉ / n (0-based indexing → subtract 1).
        let idx = ((n as f64 + 1.0) * (1.0 - self.alpha)).ceil() as usize - 1;
        let idx = idx.min(n - 1);
        self.threshold = Some(sorted[idx]);
        Ok(())
    }

    /// Predict the conformal set for new model scores: all classes whose
    /// nonconformity (1 − score) ≤ threshold are included.
    pub fn predict_set(&self, scores: &[f64]) -> Result<PredictionSet, ConformalError> {
        if scores.is_empty() {
            return Err(ConformalError::EmptyScores);
        }
        let Some(q) = self.threshold else {
            return Err(ConformalError::InsufficientSamples(0));
        };
        let mut classes = Vec::new();
        let mut probs = Vec::new();
        for (i, s) in scores.iter().enumerate() {
            if 1.0 - s <= q {
                classes.push(i);
                probs.push(*s);
            }
        }
        Ok(PredictionSet {
            classes,
            probs,
            alpha: self.alpha,
            threshold: q,
            guarantee: 1.0 - self.alpha,
        })
    }

    /// The fitted quantile threshold, if any.
    #[must_use]
    pub const fn threshold(&self) -> Option<f64> {
        self.threshold
    }

    /// Number of calibration samples collected.
    #[must_use]
    pub fn sample_count(&self) -> usize {
        self.scores.len()
    }

    /// The miscoverage level.
    #[must_use]
    pub const fn alpha(&self) -> f64 {
        self.alpha
    }

    /// Serialize to JSON (for persistence across restarts).
    pub fn to_json(&self) -> Result<String, ConformalError> {
        Ok(serde_json::to_string(self)?)
    }

    /// Deserialize from JSON.
    pub fn from_json(json: &str) -> Result<Self, ConformalError> {
        Ok(serde_json::from_str(json)?)
    }
}

/// Split conformal regressor — prediction intervals with guaranteed
/// coverage. Nonconformity = absolute residual |y − ŷ|.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SplitConformalRegressor {
    alpha: f64,
    residuals: Vec<f64>,
    threshold: Option<f64>,
}

impl SplitConformalRegressor {
    /// Create with miscoverage level `alpha`.
    pub fn new(alpha: f64) -> Result<Self, ConformalError> {
        if !(0.0 < alpha && alpha < 1.0) {
            return Err(ConformalError::InvalidAlpha(alpha));
        }
        Ok(Self {
            alpha,
            residuals: Vec::new(),
            threshold: None,
        })
    }

    /// Record a calibration sample: model prediction and true value.
    pub fn add_sample(&mut self, predicted: f64, actual: f64) {
        self.residuals.push((predicted - actual).abs());
    }

    /// Fit the interval threshold from calibration residuals.
    pub fn fit(&mut self) -> Result<(), ConformalError> {
        let n = self.residuals.len();
        if n < 2 {
            return Err(ConformalError::InsufficientSamples(n));
        }
        let mut sorted = self.residuals.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let idx = ((n as f64 + 1.0) * (1.0 - self.alpha)).ceil() as usize - 1;
        let idx = idx.min(n - 1);
        self.threshold = Some(sorted[idx]);
        Ok(())
    }

    /// Predict a coverage-guaranteed interval `[ŷ − q, ŷ + q]`.
    pub fn predict_interval(&self, prediction: f64) -> Result<PredictionInterval, ConformalError> {
        let Some(q) = self.threshold else {
            return Err(ConformalError::InsufficientSamples(0));
        };
        Ok(PredictionInterval {
            lower: prediction - q,
            upper: prediction + q,
            point: prediction,
            alpha: self.alpha,
            guarantee: 1.0 - self.alpha,
        })
    }

    /// The fitted interval half-width.
    #[must_use]
    pub const fn threshold(&self) -> Option<f64> {
        self.threshold
    }

    /// Number of calibration residuals.
    #[must_use]
    pub fn sample_count(&self) -> usize {
        self.residuals.len()
    }

    /// The miscoverage level.
    #[must_use]
    pub const fn alpha(&self) -> f64 {
        self.alpha
    }

    /// Serialize to JSON.
    pub fn to_json(&self) -> Result<String, ConformalError> {
        Ok(serde_json::to_string(self)?)
    }

    /// Deserialize from JSON.
    pub fn from_json(json: &str) -> Result<Self, ConformalError> {
        Ok(serde_json::from_str(json)?)
    }
}

/// Adaptive Prediction Sets (APS) — smaller sets for calibrated models.
///
/// Includes classes in descending score order until the cumulative mass
/// crosses the calibrated quantile at the true-class rank, producing
/// smaller sets than the plain quantile approach.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdaptivePredictionSets {
    alpha: f64,
    /// Raw APS nonconformity scores (cumulative mass at the true class
    /// minus a uniform tie-breaking term), one per calibration sample.
    scores: Vec<f64>,
    /// Fitted cutoff: the `⌈(n+1)(1−α)⌉`-th smallest score.
    cutoff: Option<f64>,
    n_classes: usize,
    /// SplitMix64 state for the uniform tie-breaking term U ~ U(0,1).
    rng_state: u64,
}

impl AdaptivePredictionSets {
    /// Create with miscoverage level `alpha`.
    pub fn new(alpha: f64) -> Result<Self, ConformalError> {
        if !(0.0 < alpha && alpha < 1.0) {
            return Err(ConformalError::InvalidAlpha(alpha));
        }
        Ok(Self {
            alpha,
            scores: Vec::new(),
            cutoff: None,
            n_classes: 0,
            rng_state: 0x9E3779B97F4A7C15,
        })
    }

    /// Record a calibration sample: model scores + true label.
    pub fn add_sample(&mut self, scores: &[f64], true_label: usize) -> Result<(), ConformalError> {
        if scores.is_empty() {
            return Err(ConformalError::EmptyScores);
        }
        if true_label >= scores.len() {
            return Err(ConformalError::ClassIndexOutOfRange(
                true_label,
                scores.len(),
            ));
        }
        self.n_classes = self.n_classes.max(scores.len());

        // Cumulative probability up to and including the true class,
        // when classes are sorted by descending score.
        let mut order: Vec<usize> = (0..scores.len()).collect();
        order.sort_by(|a, b| {
            scores[*b]
                .partial_cmp(&scores[*a])
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        let mut cum = 0.0;
        let mut rank = 0;
        for (i, &cls) in order.iter().enumerate() {
            cum += scores[cls];
            if cls == true_label {
                rank = i + 1;
                break;
            }
        }
        // APS nonconformity: cumulative mass up to and including the true
        // class, minus a uniform tie-breaking term U * p_true (Romano et
        // al., 2020). The U term is essential for the coverage guarantee
        // when scores are discrete/rounded.
        let u = self.next_uniform();
        let p_true = scores[true_label];
        let aps_score = u.mul_add(-p_true, cum).clamp(0.0, 1.0);
        let _ = rank;
        self.scores.push(aps_score);
        Ok(())
    }

    /// Fit the APS cutoff as the `⌈(n+1)(1−α)⌉`-th smallest cumulative mass.
    pub fn fit(&mut self) -> Result<(), ConformalError> {
        let n = self.scores.len();
        if n < 2 {
            return Err(ConformalError::InsufficientSamples(n));
        }
        let mut sorted = self.scores.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let idx = ((n as f64 + 1.0) * (1.0 - self.alpha)).ceil() as usize - 1;
        let idx = idx.min(n - 1);
        self.cutoff = Some(sorted[idx]);
        Ok(())
    }

    /// Predict the APS set: include classes in descending score order
    /// until cumulative mass exceeds the calibrated cutoff for that rank.
    pub fn predict_set(&mut self, scores: &[f64]) -> Result<PredictionSet, ConformalError> {
        if scores.is_empty() {
            return Err(ConformalError::EmptyScores);
        }
        let mut order: Vec<usize> = (0..scores.len()).collect();
        order.sort_by(|a, b| {
            scores[*b]
                .partial_cmp(&scores[*a])
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        let Some(cutoff) = self.cutoff else {
            return Err(ConformalError::InsufficientSamples(0));
        };
        // Draw the tie-breaking uniform for this prediction.
        let u = self.next_uniform();
        let mut classes = Vec::new();
        let mut probs = Vec::new();
        let mut cum = 0.0;
        for &cls in &order {
            let p = scores[cls];
            classes.push(cls);
            probs.push(p);
            cum += p;
            // Adjusted cumulative mass: subtract the uniform tie-break
            // weighted by the last included class's probability.
            if u.mul_add(-p, cum) >= cutoff {
                break;
            }
        }
        Ok(PredictionSet {
            classes,
            probs,
            alpha: self.alpha,
            threshold: cutoff,
            guarantee: 1.0 - self.alpha,
        })
    }

    /// SplitMix64 uniform in [0, 1) for the APS tie-breaking term.
    fn next_uniform(&mut self) -> f64 {
        self.rng_state = self.rng_state.wrapping_add(0x9E3779B97F4A7C15);
        let mut z = self.rng_state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
        (z ^ (z >> 31)) as f64 / u64::MAX as f64
    }

    /// Serialize to JSON.
    pub fn to_json(&self) -> Result<String, ConformalError> {
        Ok(serde_json::to_string(self)?)
    }

    /// Deserialize from JSON.
    pub fn from_json(json: &str) -> Result<Self, ConformalError> {
        Ok(serde_json::from_str(json)?)
    }
}

/// A conformal prediction set for classification.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictionSet {
    /// Included class indices (ordered by descending model score).
    pub classes: Vec<usize>,
    /// Corresponding model scores.
    pub probs: Vec<f64>,
    /// Miscoverage level.
    pub alpha: f64,
    /// Fitted threshold used for the set.
    pub threshold: f64,
    /// The coverage guarantee (1 − α).
    pub guarantee: f64,
}

impl PredictionSet {
    /// Whether the set contains the given class.
    #[must_use]
    pub fn contains(&self, class: usize) -> bool {
        self.classes.contains(&class)
    }

    /// Whether the set is a singleton (high confidence prediction).
    #[must_use]
    pub fn is_singleton(&self) -> bool {
        self.classes.len() == 1
    }

    /// Whether the set is empty (no class meets the threshold).
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.classes.is_empty()
    }
}

/// A conformal prediction interval for regression.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictionInterval {
    /// Interval lower bound.
    pub lower: f64,
    /// Interval upper bound.
    pub upper: f64,
    /// Point prediction.
    pub point: f64,
    /// Miscoverage level.
    pub alpha: f64,
    /// The coverage guarantee (1 − α).
    pub guarantee: f64,
}

impl PredictionInterval {
    /// Whether the interval contains the value.
    #[must_use]
    pub fn contains(&self, value: f64) -> bool {
        self.lower <= value && value <= self.upper
    }

    /// Interval width.
    #[must_use]
    pub fn width(&self) -> f64 {
        self.upper - self.lower
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scores_for(true_class: usize) -> Vec<f64> {
        let mut s = vec![0.1; 4];
        s[true_class] = 0.7;
        s
    }

    #[test]
    fn classifier_covers_calibrated_examples() {
        let mut cp = SplitConformalClassifier::new(0.1).unwrap();
        for c in 0..4 {
            for _ in 0..25 {
                cp.add_sample(&scores_for(c), c).unwrap();
            }
        }
        cp.fit().unwrap();

        for c in 0..4 {
            let set = cp.predict_set(&scores_for(c)).unwrap();
            assert!(set.contains(c), "calibrated class should be covered");
        }
    }

    #[test]
    fn classifier_rejects_insufficient_samples() {
        let mut cp = SplitConformalClassifier::new(0.1).unwrap();
        cp.add_sample(&scores_for(0), 0).unwrap();
        assert!(cp.fit().is_err());
        assert!(matches!(
            cp.fit(),
            Err(ConformalError::InsufficientSamples(1))
        ));
    }

    #[test]
    fn classifier_alpha_validation() {
        assert!(SplitConformalClassifier::new(0.0).is_err());
        assert!(SplitConformalClassifier::new(1.0).is_err());
        assert!(SplitConformalClassifier::new(0.05).is_ok());
    }

    #[test]
    fn classifier_rejects_bad_label() {
        let mut cp = SplitConformalClassifier::new(0.1).unwrap();
        assert!(cp.add_sample(&scores_for(0), 7).is_err());
        assert!(cp.add_sample(&[], 0).is_err());
    }

    #[test]
    fn regressor_interval_covers_calibrated() {
        let mut r = SplitConformalRegressor::new(0.1).unwrap();
        for i in 0..50 {
            let truth = f64::from(i);
            r.add_sample(truth + 0.1, truth); // small residuals
        }
        r.fit().unwrap();
        let iv = r.predict_interval(25.0).unwrap();
        assert!(iv.contains(25.0));
        assert!(iv.width() > 0.0);
        assert_eq!(iv.guarantee, 0.9);
    }

    #[test]
    fn regressor_threshold_reflects_residual_magnitude() {
        let mut r = SplitConformalRegressor::new(0.1).unwrap();
        for i in 0..20 {
            r.add_sample(f64::from(i), f64::from(i) + 2.0); // constant offset 2
        }
        r.fit().unwrap();
        // q should be at least the typical residual (2.0)
        assert!(r.threshold().unwrap() >= 2.0);
    }

    #[test]
    fn aps_includes_true_class_for_confident_model() {
        let mut aps = AdaptivePredictionSets::new(0.1).unwrap();
        for _ in 0..100 {
            aps.add_sample(&scores_for(0), 0).unwrap();
        }
        aps.fit().unwrap();
        let set = aps.predict_set(&[0.95, 0.02, 0.02, 0.01]).unwrap();
        // The calibrated cutoff is the 90th percentile of cumulative
        // masses, so a confident prediction may include 1–2 classes, but
        // the true (highest-probability) class must be in the set.
        assert!(set.contains(0));
        assert!(set.classes.len() <= 2);
    }

    #[test]
    fn json_roundtrip_preserves_state() {
        let mut cp = SplitConformalClassifier::new(0.1).unwrap();
        for c in 0..3 {
            for _ in 0..10 {
                cp.add_sample(&scores_for(c), c).unwrap();
            }
        }
        cp.fit().unwrap();
        let json = cp.to_json().unwrap();
        let restored = SplitConformalClassifier::from_json(&json).unwrap();
        assert_eq!(restored.sample_count(), cp.sample_count());
        assert_eq!(restored.threshold(), cp.threshold());
        assert_eq!(restored.alpha(), cp.alpha());
        let s1 = cp.predict_set(&scores_for(0)).unwrap();
        let s2 = restored.predict_set(&scores_for(0)).unwrap();
        assert_eq!(s1.classes, s2.classes);
    }
}

#[cfg(test)]
mod coverage_tests {
    use super::*;

    /// Empirically verify the marginal coverage guarantee.
    ///
    /// The conformal guarantee holds *on average over calibration draws*;
    /// a single fixed calibration set has O(1/√n) sampling noise. So we
    /// average coverage across many independent calibration draws, which
    /// converges tightly to 1 − α and tests the actual guarantee.
    #[test]
    fn marginal_coverage_holds_in_simulation() {
        let alpha = 0.1;
        let n_cal = 400;
        let n_test = 2000;
        let n_classes = 5;
        let n_draws = 40;

        // SplitMix64 — proper 64-bit RNG, outputs in [0, 1).
        let mut state = 0x9E3779B97F4A7C15u64;
        let mut next = move || {
            state = state.wrapping_add(0x9E3779B97F4A7C15);
            let mut z = state;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
            (z ^ (z >> 31)) as f64 / u64::MAX as f64
        };

        let mut total_covered = 0usize;
        let mut total_test = 0usize;

        for _ in 0..n_draws {
            let mut cp = SplitConformalClassifier::new(alpha).unwrap();
            for _ in 0..n_cal {
                let truth = (next() * n_classes as f64) as usize;
                let mut scores = vec![0.1; n_classes];
                scores[truth] = 0.6;
                for s in &mut scores {
                    *s = (*s + next() * 0.2).clamp(0.01, 0.99);
                }
                cp.add_sample(&scores, truth).unwrap();
            }
            cp.fit().unwrap();

            for _ in 0..n_test {
                let truth = (next() * n_classes as f64) as usize;
                let mut scores = vec![0.1; n_classes];
                scores[truth] = 0.6;
                for s in &mut scores {
                    *s = (*s + next() * 0.2).clamp(0.01, 0.99);
                }
                let set = cp.predict_set(&scores).unwrap();
                if set.contains(truth) {
                    total_covered += 1;
                }
                total_test += 1;
            }
        }

        let empirical = total_covered as f64 / total_test as f64;
        // 1 − α = 0.9; across 80,000 test points the std error is ~0.0011,
        // so bounds of ±0.008 catch real bugs without flaky failures.
        assert!(
            empirical >= 0.892,
            "empirical coverage {empirical:.4} below expected ~0.90"
        );
        assert!(
            empirical <= 0.908,
            "empirical coverage {empirical:.4} far above expected ~0.90 (overcoverage)"
        );
    }

    /// Regressor interval coverage holds in simulation (averaged over
    /// many calibration draws, per the marginal guarantee).
    #[test]
    fn regressor_interval_coverage_holds_in_simulation() {
        let alpha = 0.05;
        let n_cal = 500;
        let n_test = 2000;
        let n_draws = 40;

        let mut state = 0xD1B54A32D192ED03u64;
        let mut next = move || {
            state = state.wrapping_add(0x9E3779B97F4A7C15);
            let mut z = state;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
            (z ^ (z >> 31)) as f64 / u64::MAX as f64
        };

        let mut total_covered = 0usize;
        let mut total_test = 0usize;

        for _ in 0..n_draws {
            let mut r = SplitConformalRegressor::new(alpha).unwrap();
            for _ in 0..n_cal {
                let truth = next() * 10.0;
                // Prediction with noise ~ triangular(±1.5)
                let pred = truth + (next() + next() + next() - 1.5);
                r.add_sample(pred, truth);
            }
            r.fit().unwrap();

            for _ in 0..n_test {
                let truth = next() * 10.0;
                let pred = truth + (next() + next() + next() - 1.5);
                let iv = r.predict_interval(pred).unwrap();
                if iv.contains(truth) {
                    total_covered += 1;
                }
                total_test += 1;
            }
        }

        let empirical = total_covered as f64 / total_test as f64;
        // 1 − α = 0.95; across 80,000 test points the std error is ~0.0008,
        // so ±0.008 bounds catch real bugs without flaky failures.
        assert!(
            empirical >= 0.942,
            "empirical coverage {empirical:.4} below expected ~0.95"
        );
        assert!(
            empirical <= 0.958,
            "empirical coverage {empirical:.4} far above expected ~0.95 (overcoverage)"
        );
    }
    /// APS also satisfies the marginal coverage guarantee (averaged over
    /// calibration draws).
    #[test]
    fn aps_coverage_holds_in_simulation() {
        let alpha = 0.1;
        let n_cal = 400;
        let n_test = 2000;
        let n_draws = 40;
        let n_classes = 5;

        let mut state = 0xABCDEF0123456789u64;
        let mut next = move || {
            state = state.wrapping_add(0x9E3779B97F4A7C15);
            let mut z = state;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
            (z ^ (z >> 31)) as f64 / u64::MAX as f64
        };

        let mut total_covered = 0usize;
        let mut total_test = 0usize;

        for _ in 0..n_draws {
            let mut aps = AdaptivePredictionSets::new(alpha).unwrap();
            for _ in 0..n_cal {
                let truth = (next() * n_classes as f64) as usize;
                let mut scores = vec![0.17; n_classes];
                scores[truth] = 0.20;
                for s in &mut scores {
                    *s = (*s + next() * 0.10).clamp(0.01, 0.99);
                }
                aps.add_sample(&scores, truth).unwrap();
            }
            aps.fit().unwrap();

            for _ in 0..n_test {
                let truth = (next() * n_classes as f64) as usize;
                let mut scores = vec![0.17; n_classes];
                scores[truth] = 0.20;
                for s in &mut scores {
                    *s = (*s + next() * 0.10).clamp(0.01, 0.99);
                }
                let set = aps.predict_set(&scores).unwrap();
                if set.contains(truth) {
                    total_covered += 1;
                }
                total_test += 1;
            }
        }

        let empirical = total_covered as f64 / total_test as f64;
        // The conformal guarantee is a LOWER bound: coverage must be at
        // least 1 − α. APS may over-cover (larger sets) for poorly
        // calibrated models — that is valid but less efficient. So we
        // assert the guarantee holds and that coverage is not trivially
        // perfect for the near-uniform model (which would indicate the
        // cutoff is broken).
        assert!(
            empirical >= 0.89,
            "APS empirical coverage {empirical:.4} below guaranteed ~0.90"
        );
        assert!(
            empirical <= 0.995,
            "APS empirical coverage {empirical:.4} suspiciously high (cutoff broken?)"
        );
    }
}
