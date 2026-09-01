//! wm-conformal — distribution-free uncertainty quantification.
//!
//! Implements **split conformal prediction** for classification and
//! regression. Unlike heuristic confidence calibration, conformal
//! prediction provides a *finite-sample, distribution-free coverage
//! guarantee*: given a calibration set, the produced prediction sets
//! contain the true outcome with probability at least `1 − α`, without
//! any assumptions about the underlying model or data distribution.
//!
//! ## Components
//!
//! - [`split::SplitConformalClassifier`] — label prediction sets with
//!   guaranteed marginal coverage (nonconformity = `1 − score`).
//! - [`split::SplitConformalRegressor`] — prediction intervals with
//!   guaranteed coverage (nonconformity = absolute residual).
//! - [`split::AdaptivePredictionSets`] — APS variant: more efficient
//!   (smaller) sets for well-calibrated models while preserving coverage.
//! - [`calibrate::coverage_report`] — empirical coverage evaluation on a
//!   held-out test set, for monitoring guarantees in production.

#![forbid(unsafe_code)]

pub mod calibrate;
pub mod split;

pub use calibrate::CoverageReport;
pub use split::{
    AdaptivePredictionSets, PredictionInterval, PredictionSet, SplitConformalClassifier,
    SplitConformalRegressor,
};

/// Error type for conformal operations.
#[derive(Debug, thiserror::Error)]
pub enum ConformalError {
    /// Not enough calibration samples to fit (need ≥ 2).
    #[error("insufficient calibration samples: need at least 2, got {0}")]
    InsufficientSamples(usize),

    /// No class scores provided for prediction.
    #[error("empty class scores for conformal prediction")]
    EmptyScores,

    /// Alpha must be in (0, 1).
    #[error("miscoverage level alpha must be in (0, 1), got {0}")]
    InvalidAlpha(f64),

    /// Class index out of range.
    #[error("class index {0} out of range (0..{1})")]
    ClassIndexOutOfRange(usize, usize),

    /// Serialization error.
    #[error("serde error: {0}")]
    Serde(#[from] serde_json::Error),
}
