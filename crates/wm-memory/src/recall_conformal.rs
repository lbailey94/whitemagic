//! Conformal prediction sets for retrieval (V8 S8).
//!
//! Wraps `RecallEngine` result truncation with split-conformal sets so
//! recall results can carry calibrated coverage — "these N results cover
//! at 90%" — instead of an uncalibrated ranked list. The math reuses
//! `wm_conformal::SplitConformalClassifier` with a binary relevance
//! encoding: a candidate's conformity for "relevant" is its fused score
//! `s`, for "not-relevant" it is `1 − s`, so set membership is
//! `s ≥ 1 − q̂` with `q̂` the calibrated quantile.
//!
//! Evidence-gated like every retrieval knob: `WM_RECALL_CONFORMAL_ALPHA`
//! unset (the default) leaves the engine byte-identical. When set but not
//! yet fitted, the disclosure says `uncalibrated` — a silent zero-coverage
//! claim would violate the substrate-honesty principle.
//!
//! Calibration labels come from explicit relevance feedback
//! (`record_feedback`); the engine persists the fitted classifier to
//! `<store_root>/recall_conformal.json` write-through so daemon restarts
//! keep their calibration.

use crate::store::MemoryStore;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Arc;
use wm_conformal::SplitConformalClassifier;

/// Where the calibrated state lives, relative to the store root.
const STATE_FILE: &str = "recall_conformal.json";

/// Minimum calibration samples before `fit` produces a threshold.
pub const MIN_SAMPLES: usize = 10;

/// Conformal state for one recall engine.
pub struct RecallConformal {
    alpha: f32,
    classifier: SplitConformalClassifier,
    store: Arc<MemoryStore>,
}

impl RecallConformal {
    /// Construct with a validated miscoverage level (0 < alpha < 1).
    pub fn new(alpha: f32, store: Arc<MemoryStore>) -> Option<Self> {
        if !alpha.is_finite() || alpha <= 0.0 || alpha >= 1.0 {
            return None;
        }
        // Load persisted state when present so a restarted daemon keeps
        // its calibration; a fresh store starts unfitted.
        let path = state_path(&store);
        let classifier = std::fs::read_to_string(&path)
            .ok()
            .and_then(|body| SplitConformalClassifier::from_json(&body).ok())
            .filter(|c| (c.alpha() - f64::from(alpha)).abs() < 1e-9)
            .unwrap_or_else(|| {
                SplitConformalClassifier::new(f64::from(alpha)).expect("alpha validated above")
            });
        Some(Self {
            alpha,
            classifier,
            store,
        })
    }

    /// The miscoverage level.
    #[must_use]
    pub const fn alpha(&self) -> f32 {
        self.alpha
    }

    /// Number of calibration samples recorded (across restarts).
    #[must_use]
    pub fn sample_count(&self) -> usize {
        self.classifier.sample_count()
    }

    /// Whether a calibrated threshold is in effect.
    #[must_use]
    pub const fn is_fitted(&self) -> bool {
        self.classifier.threshold().is_some()
    }

    /// Record one relevance-feedback sample and refit write-through.
    /// Returns the sample count after the update.
    ///
    /// The two-class encoding: conformity for "relevant" is the score,
    /// for "not-relevant" its complement — so a high fused score is strong
    /// evidence for membership in the relevant set.
    pub fn record_feedback(&mut self, score: f32, relevant: bool) -> usize {
        let s = f64::from(score.clamp(0.0, 1.0));
        let scores = [1.0 - s, s];
        let label = usize::from(relevant);
        // Duplicate near-identical scores are information-free — skip them
        // so the calibration set does not fill with one query's shape.
        if let Err(e) = self.classifier.add_sample(&scores, label) {
            tracing::debug!(error = %e, "recall conformal: sample rejected");
            return self.classifier.sample_count();
        }
        if self.classifier.sample_count() >= MIN_SAMPLES {
            if let Err(e) = self.classifier.fit() {
                tracing::debug!(error = %e, "recall conformal: fit failed");
            } else {
                self.persist();
            }
        }
        self.classifier.sample_count()
    }

    /// Is this fused score inside the calibrated prediction set?
    /// `None` when not yet fitted (callers must disclose that, not guess).
    #[must_use]
    pub fn membership(&self, score: f32) -> Option<bool> {
        let q = self.classifier.threshold()?;
        let s = f64::from(score.clamp(0.0, 1.0));
        // predict_set semantics: class i is in the set iff 1 − score_i ≤ q.
        // Class 1 is "relevant": membership iff s ≥ 1 − q.
        Some(1.0 - s <= q)
    }

    /// The calibrated threshold (fused-score floor for set membership).
    #[must_use]
    pub const fn threshold(&self) -> Option<f64> {
        self.classifier.threshold()
    }

    fn persist(&self) {
        let path = state_path(&self.store);
        match self.classifier.to_json() {
            Ok(body) => {
                if let Some(parent) = path.parent() {
                    let _ = std::fs::create_dir_all(parent);
                }
                if let Err(e) = std::fs::write(&path, body) {
                    tracing::warn!(error = %e, path = %path.display(), "recall conformal: persist failed");
                }
            }
            Err(e) => {
                tracing::warn!(error = %e, "recall conformal: serialize failed");
            }
        }
    }
}

fn state_path(store: &MemoryStore) -> PathBuf {
    store
        .path()
        .parent()
        .map_or_else(|| PathBuf::from(STATE_FILE), |root| root.join(STATE_FILE))
}

/// Set-level disclosure attached to a hybrid search when conformal mode
/// is configured.
///
/// `status` is honest about what the coverage claim is backed by:
/// `active` (fitted), `uncalibrated` (alpha set, too few samples), or
/// `off` (knob unset — no claim is made at all).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ConformalSetInfo {
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub alpha: Option<f64>,
    /// `1 − alpha` — the coverage the guarantee targets when active.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coverage_target: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub calibration_samples: Option<usize>,
    /// Fused-score floor for set membership when active.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub threshold: Option<f64>,
    /// Results inside the set when active.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub set_size: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub hint: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_store() -> Arc<MemoryStore> {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("lmdb");
        std::fs::create_dir_all(&path).unwrap();
        // Leak-free temp store: the state file writes land in the tempdir.
        Arc::new(MemoryStore::open(path, 1024 * 1024).unwrap())
    }

    #[test]
    fn invalid_alpha_is_refused_not_silently_clamped() {
        let store = test_store();
        assert!(RecallConformal::new(0.0, store.clone()).is_none());
        assert!(RecallConformal::new(1.0, store.clone()).is_none());
        assert!(RecallConformal::new(f32::NAN, store).is_none());
    }

    #[test]
    fn unfitted_membership_is_none_not_a_guess() {
        let store = test_store();
        let rc = RecallConformal::new(0.1, store).unwrap();
        assert!(!rc.is_fitted());
        assert!(rc.membership(0.9).is_none());
    }

    #[test]
    fn feedback_below_min_samples_stays_uncalibrated() {
        let store = test_store();
        let mut rc = RecallConformal::new(0.1, store).unwrap();
        for i in 0..MIN_SAMPLES - 1 {
            let n = rc.record_feedback(0.5 + i as f32 / 100.0, true);
            assert_eq!(n, i + 1);
        }
        assert!(!rc.is_fitted(), "MIN_SAMPLES-1 must not fit");
    }

    #[test]
    fn calibration_reaches_fit_and_membership_follows_threshold() {
        let store = test_store();
        let mut rc = RecallConformal::new(0.1, store).unwrap();
        // Relevant samples score high; irrelevant low — the quantile of
        // the relevant nonconformities lands somewhere in (0, 0.25).
        for i in 0..MIN_SAMPLES {
            rc.record_feedback(0.90 - i as f32 / 100.0, true);
            rc.record_feedback(0.10 + i as f32 / 100.0, false);
        }
        assert!(rc.is_fitted());
        let q = rc.threshold().expect("fitted");
        assert!(
            q > 0.0 && q < 0.25,
            "threshold {q} should track relevant scores"
        );
        assert_eq!(rc.membership(0.95), Some(true), "high score in set");
        assert_eq!(rc.membership(0.05), Some(false), "low score out of set");
        // Status at the fence: 1 − q with q ∈ (0, 0.25) → fence in (0.75, 1.0).
        let fence = (1.0 - q) as f32;
        assert_eq!(rc.membership(fence), Some(true));
    }

    #[test]
    fn state_persists_across_reconstruction() {
        let store = test_store();
        {
            let mut rc = RecallConformal::new(0.2, store.clone()).unwrap();
            for i in 0..MIN_SAMPLES + 5 {
                rc.record_feedback(0.80 + (i % 7) as f32 / 100.0, i % 3 != 0);
            }
            assert!(rc.is_fitted());
        }
        // Reconstruct from the same store: calibration survives.
        let rc2 = RecallConformal::new(0.2, store).unwrap();
        assert!(rc2.is_fitted(), "persisted classifier reloads fitted");
        assert!(rc2.sample_count() >= MIN_SAMPLES);
    }

    #[test]
    fn disclosure_serializes_honest_statuses() {
        let off = ConformalSetInfo {
            status: "off".into(),
            alpha: None,
            coverage_target: None,
            calibration_samples: None,
            threshold: None,
            set_size: None,
            hint: None,
        };
        let json = serde_json::to_value(&off).unwrap();
        assert_eq!(json["status"], "off");
        assert!(json.get("alpha").is_none(), "off discloses no numbers");

        let uncal = ConformalSetInfo {
            status: "uncalibrated".into(),
            alpha: Some(0.1),
            coverage_target: Some(0.9),
            calibration_samples: Some(3),
            threshold: None,
            set_size: None,
            hint: Some("record ≥ 10 feedback samples to calibrate".into()),
        };
        let json = serde_json::to_value(&uncal).unwrap();
        assert_eq!(json["status"], "uncalibrated");
        assert_eq!(json["calibration_samples"], 3);
        assert!(json.get("threshold").is_none());
    }
}
