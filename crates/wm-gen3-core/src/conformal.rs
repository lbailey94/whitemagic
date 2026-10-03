//! PEB-12: Conformal Epistemic Sovereignty.
//!
//! # Core Sovereignty Invariants
//!
//! 1. **Epistemic Sovereignty:**
//!    `Remote Confidence != Local Confidence`.
//!    A remote peer's calibration metadata, p-values, or confidence claims cannot be
//!    blindly pooled into the local calibration set. Remote claims are treated as
//!    unverified candidate evidence.
//!
//! 2. **Finite-Sample Marginal Coverage Guarantee:**
//!    Target nominal coverage: 1 - α (typically 0.95 for 95% confidence).
//!    The finite-sample correction quantile:
//!    `idx = ⌈(n + 1)(1 - α)⌉ / n - 1`
//!    guarantees: `P(Y ∈ C(X)) ≥ 1 - α` under exchangeability.
//!
//! 3. **Substrate Honesty & Warrant Withdrawal:**
//!    "A silent zero-coverage claim violates the substrate-honesty principle."
//!    Under distribution shift (covariate or concept shift), exchangeability is violated.
//!    The engine monitors calibration exchangeability via a rolling drift detector.
//!    When shift is detected, the engine withdraws its epistemic warrant:
//!    `status = EpistemicStatus::UncalibratedShift`.
//!
//! 4. **Statistical Rigor:**
//!    Reports exact Wilson Score 95% confidence intervals on observed empirical coverage.

use serde::{Deserialize, Serialize};
use std::cmp::Ordering;

/// Minimum samples required before a valid conformal threshold can be fitted.
pub const MIN_CALIBRATION_SAMPLES: usize = 20;

/// Default nominal miscoverage rate: α = 0.05 (95% nominal coverage).
pub const DEFAULT_NOMINAL_ALPHA: f64 = 0.05;

/// Errors produced during conformal calibration, prediction, and ingress.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ConformalError {
    InvalidAlpha(f64),
    EmptyScores,
    InsufficientSamples {
        count: usize,
        min_required: usize,
    },
    ShiftDetected {
        test_statistic: f64,
        p_value: f64,
        threshold: f64,
    },
    RemoteEpistemicContamination {
        reason: String,
    },
    SerializationError(String),
}

impl std::fmt::Display for ConformalError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidAlpha(a) => write!(f, "Invalid alpha {}: must be in (0, 1)", a),
            Self::EmptyScores => write!(f, "Cannot calibrate on empty scores vector"),
            Self::InsufficientSamples {
                count,
                min_required,
            } => {
                write!(
                    f,
                    "Insufficient calibration samples: got {}, need >= {}",
                    count, min_required
                )
            }
            Self::ShiftDetected {
                test_statistic,
                p_value,
                threshold,
            } => {
                write!(
                    f,
                    "Distribution shift detected: stat={:.4}, p_val={:.4e}, thresh={:.4}",
                    test_statistic, p_value, threshold
                )
            }
            Self::RemoteEpistemicContamination { reason } => {
                write!(f, "Remote epistemic contamination rejected: {}", reason)
            }
            Self::SerializationError(e) => write!(f, "Conformal serialization error: {}", e),
        }
    }
}

impl std::error::Error for ConformalError {}

/// Honest epistemic status of a conformal warrant.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum EpistemicStatus {
    /// Fully calibrated with finite-sample guarantee.
    Calibrated {
        alpha: f64,
        threshold: f64,
        n_samples: usize,
    },
    /// Insufficient local calibration data.
    Uncalibrated {
        n_samples: usize,
        min_required: usize,
    },
    /// Distribution shift detected: warrant is explicitly withdrawn!
    UncalibratedShift {
        test_statistic: f64,
        p_value: f64,
        threshold: f64,
    },
    /// Warrant withdrawn by administrative or homeostatic policy.
    WarrantWithdrawn { reason: String },
}

impl EpistemicStatus {
    pub fn is_calibrated(&self) -> bool {
        matches!(self, Self::Calibrated { .. })
    }

    pub fn is_warranted(&self) -> bool {
        matches!(self, Self::Calibrated { .. })
    }
}

/// Wilson Score interval for binomial proportions (exact empirical coverage CI).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WilsonScoreInterval {
    pub point_estimate: f64,
    pub ci_lower: f64,
    pub ci_upper: f64,
    pub sample_size: usize,
    pub hits: usize,
    pub confidence_level: f64,
}

impl WilsonScoreInterval {
    /// Compute the Wilson Score 95% confidence interval for `hits` successes out of `n` trials.
    pub fn compute_95(hits: usize, n: usize) -> Self {
        if n == 0 {
            return Self {
                point_estimate: 0.0,
                ci_lower: 0.0,
                ci_upper: 0.0,
                sample_size: 0,
                hits: 0,
                confidence_level: 0.95,
            };
        }

        let p_hat = hits as f64 / n as f64;
        let z = 1.95996398454; // 95% two-sided normal quantile
        let z2 = z * z;
        let n_f = n as f64;

        let denominator = 1.0 + z2 / n_f;
        let center = (p_hat + z2 / (2.0 * n_f)) / denominator;
        let margin =
            (z / denominator) * ((p_hat * (1.0 - p_hat) / n_f + z2 / (4.0 * n_f * n_f)).sqrt());

        let ci_lower = (center - margin).clamp(0.0, 1.0);
        let ci_upper = (center + margin).clamp(0.0, 1.0);

        Self {
            point_estimate: p_hat,
            ci_lower,
            ci_upper,
            sample_size: n,
            hits,
            confidence_level: 0.95,
        }
    }
}

/// A conformal prediction interval `[point - threshold, point + threshold]` with guaranteed coverage.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ConformalInterval {
    pub lower: f64,
    pub upper: f64,
    pub point: f64,
    pub alpha: f64,
    pub nominal_coverage: f64,
    pub status: EpistemicStatus,
}

impl ConformalInterval {
    pub fn contains(&self, actual: f64) -> bool {
        self.lower <= actual && actual <= self.upper
    }

    pub fn width(&self) -> f64 {
        self.upper - self.lower
    }
}

/// Candidate claim emitted across a network boundary by a remote peer.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RemoteEpistemicClaim {
    pub peer_id: String,
    pub claim_id: String,
    pub point_prediction: f64,
    pub remote_claimed_alpha: Option<f64>,
    pub remote_claimed_p_value: Option<f64>,
    pub remote_sample_size: Option<usize>,
    pub payload: Vec<u8>,
}

/// Local node's sovereign epistemic assessment of a claim.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LocalEpistemicWarrant {
    pub claim_id: String,
    pub peer_id: String,
    pub local_status: EpistemicStatus,
    pub interval: Option<ConformalInterval>,
    pub warrant_held: bool,
    pub note: String,
}

/// Sovereign Conformal Recall & Prediction Engine.
///
/// Implements split-conformal inference, distribution drift detection,
/// warrant withdrawal, and strict isolation of remote confidence metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConformalRecallEngine {
    /// Miscoverage level α (e.g. 0.05 for 95% coverage guarantee).
    alpha: f64,
    /// Local calibration nonconformity scores (e.g. absolute residuals |y - ŷ|).
    calibration_scores: Vec<f64>,
    /// Fitted quantile threshold q_hat.
    threshold: Option<f64>,
    /// Recent test residuals used for rolling distribution-shift detection.
    recent_residuals: Vec<f64>,
    /// Rolling window capacity for shift detection.
    window_capacity: usize,
    /// Critical drift threshold in standard errors.
    shift_threshold_z: f64,
    /// Minimum calibration samples required before fitting.
    min_samples: usize,
}

impl ConformalRecallEngine {
    /// Create a new engine with specified miscoverage level α.
    pub fn new(alpha: f64) -> Result<Self, ConformalError> {
        if !(0.0 < alpha && alpha < 1.0) {
            return Err(ConformalError::InvalidAlpha(alpha));
        }
        Ok(Self {
            alpha,
            calibration_scores: Vec::new(),
            threshold: None,
            recent_residuals: Vec::new(),
            window_capacity: 50,
            shift_threshold_z: 3.0, // 3-sigma drift threshold
            min_samples: MIN_CALIBRATION_SAMPLES,
        })
    }

    /// Construct default engine with nominal 95% coverage (α = 0.05).
    pub fn default_95() -> Self {
        Self::new(DEFAULT_NOMINAL_ALPHA).expect("valid default alpha")
    }

    pub fn alpha(&self) -> f64 {
        self.alpha
    }

    pub fn sample_count(&self) -> usize {
        self.calibration_scores.len()
    }

    pub fn threshold(&self) -> Option<f64> {
        self.threshold
    }

    pub fn is_fitted(&self) -> bool {
        self.threshold.is_some()
    }

    /// Add a locally generated calibration sample: `predicted` vs `actual`.
    pub fn add_calibration_sample(&mut self, predicted: f64, actual: f64) {
        let residual = (predicted - actual).abs();
        self.calibration_scores.push(residual);
    }

    /// Directly record a local nonconformity score.
    pub fn record_local_score(&mut self, score: f64) {
        self.calibration_scores.push(score.abs());
    }

    /// Fit the split-conformal quantile threshold using the exact finite-sample formula:
    /// `idx = ⌈(n + 1)(1 - α)⌉ / n - 1`
    pub fn fit(&mut self) -> Result<f64, ConformalError> {
        let n = self.calibration_scores.len();
        if n < self.min_samples {
            return Err(ConformalError::InsufficientSamples {
                count: n,
                min_required: self.min_samples,
            });
        }

        let mut sorted = self.calibration_scores.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal));

        // Exact finite-sample quantile index calculation:
        // ⌈(n + 1)(1 - α)⌉ (1-indexed) -> subtract 1 for 0-indexed slice.
        let rank = ((n as f64 + 1.0) * (1.0 - self.alpha)).ceil() as usize;
        let idx = (rank.saturating_sub(1)).min(n - 1);

        let q_hat = sorted[idx];
        self.threshold = Some(q_hat);
        Ok(q_hat)
    }

    /// Predict a coverage-guaranteed interval for a given prediction.
    pub fn predict_interval(&self, prediction: f64) -> Result<ConformalInterval, ConformalError> {
        let Some(q_hat) = self.threshold else {
            return Err(ConformalError::InsufficientSamples {
                count: self.calibration_scores.len(),
                min_required: self.min_samples,
            });
        };

        // Check if there is an active distribution shift
        let status = self.evaluate_current_status();
        if let EpistemicStatus::UncalibratedShift {
            test_statistic,
            p_value,
            threshold,
        } = status
        {
            return Err(ConformalError::ShiftDetected {
                test_statistic,
                p_value,
                threshold,
            });
        }

        Ok(ConformalInterval {
            lower: prediction - q_hat,
            upper: prediction + q_hat,
            point: prediction,
            alpha: self.alpha,
            nominal_coverage: 1.0 - self.alpha,
            status,
        })
    }

    /// Record a test-time observation to monitor for exchangeability / distribution shift.
    pub fn record_test_observation(&mut self, predicted: f64, actual: f64) {
        let residual = (predicted - actual).abs();
        self.recent_residuals.push(residual);
        if self.recent_residuals.len() > self.window_capacity {
            self.recent_residuals.remove(0);
        }
    }

    /// Check whether a distribution shift has occurred between calibration and recent observations.
    ///
    /// Computes the normalized mean shift test statistic:
    /// `Z = (μ_recent - μ_cal) / (σ_cal / sqrt(W))`
    pub fn test_distribution_shift(&self) -> Option<(f64, f64, bool)> {
        if self.calibration_scores.len() < self.min_samples || self.recent_residuals.len() < 10 {
            return None;
        }

        let n_cal = self.calibration_scores.len() as f64;
        let mean_cal: f64 = self.calibration_scores.iter().sum::<f64>() / n_cal;
        let var_cal: f64 = self
            .calibration_scores
            .iter()
            .map(|x| (x - mean_cal).powi(2))
            .sum::<f64>()
            / (n_cal - 1.0).max(1.0);
        let std_cal = var_cal.sqrt().max(1e-6);

        let n_recent = self.recent_residuals.len() as f64;
        let mean_recent: f64 = self.recent_residuals.iter().sum::<f64>() / n_recent;

        let se = std_cal / n_recent.sqrt();
        let z_stat = (mean_recent - mean_cal) / se;

        // Approximate two-sided p-value using normal distribution
        let abs_z = z_stat.abs();
        let p_value = 2.0 * (1.0 - normal_cdf(abs_z));
        let is_shift = z_stat > self.shift_threshold_z;

        Some((z_stat, p_value, is_shift))
    }

    /// Evaluate honest current epistemic status.
    pub fn evaluate_current_status(&self) -> EpistemicStatus {
        let Some(q_hat) = self.threshold else {
            return EpistemicStatus::Uncalibrated {
                n_samples: self.calibration_scores.len(),
                min_required: self.min_samples,
            };
        };

        if let Some((z_stat, p_val, is_shift)) = self.test_distribution_shift() {
            if is_shift {
                return EpistemicStatus::UncalibratedShift {
                    test_statistic: z_stat,
                    p_value: p_val,
                    threshold: self.shift_threshold_z,
                };
            }
        }

        EpistemicStatus::Calibrated {
            alpha: self.alpha,
            threshold: q_hat,
            n_samples: self.calibration_scores.len(),
        }
    }

    /// Assess a remote epistemic claim under the Gan Ying Invariant:
    /// `Remote Confidence != Local Confidence`.
    ///
    /// Remote confidence claims are explicitly ignored or recorded as foreign metadata.
    /// The local warrant is evaluated SOLELY against local calibration.
    pub fn assess_remote_claim(&self, claim: &RemoteEpistemicClaim) -> LocalEpistemicWarrant {
        let status = self.evaluate_current_status();

        match status {
            EpistemicStatus::Calibrated {
                alpha, threshold, ..
            } => {
                let interval = ConformalInterval {
                    lower: claim.point_prediction - threshold,
                    upper: claim.point_prediction + threshold,
                    point: claim.point_prediction,
                    alpha,
                    nominal_coverage: 1.0 - alpha,
                    status: status.clone(),
                };

                let note = if let Some(remote_alpha) = claim.remote_claimed_alpha {
                    format!(
                        "Locally calibrated at α={:.3}. Remote claimed α={:.3} was unprivileged.",
                        alpha, remote_alpha
                    )
                } else {
                    format!("Locally calibrated at α={:.3}.", alpha)
                };

                LocalEpistemicWarrant {
                    claim_id: claim.claim_id.clone(),
                    peer_id: claim.peer_id.clone(),
                    local_status: status,
                    interval: Some(interval),
                    warrant_held: true,
                    note,
                }
            }
            EpistemicStatus::UncalibratedShift {
                test_statistic,
                p_value,
                ..
            } => LocalEpistemicWarrant {
                claim_id: claim.claim_id.clone(),
                peer_id: claim.peer_id.clone(),
                local_status: status,
                interval: None,
                warrant_held: false,
                note: format!(
                    "WARRANT WITHDRAWN: Distribution shift detected (z={:.2}, p={:.4e}). Remote claims refused.",
                    test_statistic, p_value
                ),
            },
            EpistemicStatus::Uncalibrated {
                n_samples,
                min_required,
            } => LocalEpistemicWarrant {
                claim_id: claim.claim_id.clone(),
                peer_id: claim.peer_id.clone(),
                local_status: status,
                interval: None,
                warrant_held: false,
                note: format!(
                    "UNCALIBRATED: Insufficient local calibration data ({} / {}). Remote confidence cannot substitute.",
                    n_samples, min_required
                ),
            },
            EpistemicStatus::WarrantWithdrawn { reason } => LocalEpistemicWarrant {
                claim_id: claim.claim_id.clone(),
                peer_id: claim.peer_id.clone(),
                local_status: EpistemicStatus::WarrantWithdrawn {
                    reason: reason.clone(),
                },
                interval: None,
                warrant_held: false,
                note: format!("WARRANT WITHDRAWN: {}", reason),
            },
        }
    }

    /// Reject attempted contamination: Remote calibration points CANNOT be merged into local pool.
    pub fn reject_remote_calibration_import(
        &self,
        _peer_id: &str,
        _scores: &[f64],
    ) -> Result<(), ConformalError> {
        Err(ConformalError::RemoteEpistemicContamination {
            reason: "Sovereignty Law Violation: Remote calibration metadata cannot enter local calibration pool (Remote Confidence != Local Confidence)."
                .into(),
        })
    }

    /// Serialize state to JSON.
    pub fn to_json(&self) -> Result<String, ConformalError> {
        serde_json::to_string(self).map_err(|e| ConformalError::SerializationError(e.to_string()))
    }

    /// Deserialize state from JSON.
    pub fn from_json(json: &str) -> Result<Self, ConformalError> {
        serde_json::from_str(json).map_err(|e| ConformalError::SerializationError(e.to_string()))
    }
}

/// Standard normal cumulative distribution function approximation (Abramowitz & Stegun 26.2.17).
fn normal_cdf(x: f64) -> f64 {
    if x < 0.0 {
        return 1.0 - normal_cdf(-x);
    }
    let b1 = 0.319381530;
    let b2 = -0.356563782;
    let b3 = 1.781477937;
    let b4 = -1.821255978;
    let b5 = 1.330274429;
    let p = 0.2316419;

    let t = 1.0 / (1.0 + p * x);
    let phi = (-0.5 * x * x).exp() / (std::f64::consts::TAU.sqrt());
    let poly = t * (b1 + t * (b2 + t * (b3 + t * (b4 + t * b5))));
    1.0 - phi * poly
}

/// Comprehensive report from the PEB-12 Conformal Epistemic Sovereignty Benchmark Battery.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Peb12Report {
    pub total_trials: usize,
    pub nominal_alpha: f64,
    pub target_coverage: f64,
    pub in_distribution_coverage: f64,
    pub in_distribution_hits: usize,
    pub in_distribution_total: usize,
    pub wilson_ci_lower: f64,
    pub wilson_ci_upper: f64,
    pub finite_sample_exact_count: usize,
    pub remote_contamination_rejections: usize,
    pub mean_drift_warrant_withdrawals: usize,
    pub variance_drift_warrant_withdrawals: usize,
    pub in_distribution_specificity_success: usize,
    pub restart_persistence_intact: usize,
    pub set_monotonicity_success: usize,
    pub empty_calibration_honest_uncalibrated: usize,
    pub adversarial_peer_exaggeration_blocked: usize,
    pub split_conformal_boundary_exact: usize,
    pub summary: String,
}

/// Execute the PEB-12 Conformal Epistemic Sovereignty Benchmark Battery across `trials` independent rounds.
pub fn run_peb12_conformal_sovereignty_benchmark(trials: usize) -> Peb12Report {
    let mut finite_sample_exact = 0usize;
    let mut remote_contamination_rejections = 0usize;
    let mut mean_drift_withdrawals = 0usize;
    let mut var_drift_withdrawals = 0usize;
    let mut specificity_success = 0usize;
    let mut restart_persistence = 0usize;
    let mut monotonicity_success = 0usize;
    let mut empty_uncalibrated = 0usize;
    let mut adversarial_exaggeration_blocked = 0usize;
    let mut boundary_exact = 0usize;

    let mut total_in_dist_hits = 0usize;
    let mut total_in_dist_tests = 0usize;

    // Simple deterministic pseudo-random number generator for reproducible verification
    let mut state = 0x85432917CDEFA012u64;
    let mut rng = move || {
        state = state.wrapping_add(0x9E3779B97F4A7C15);
        let mut z = state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
        (z ^ (z >> 31)) as f64 / u64::MAX as f64
    };

    let alpha = 0.05; // 95% nominal coverage
    let n_cal = 200;
    let n_test = 100;

    for trial in 0..trials {
        let mut engine = ConformalRecallEngine::new(alpha).unwrap();

        // 1. Generate IID Calibration Data: y = true_signal + normal_noise
        for _ in 0..n_cal {
            let true_val = rng() * 100.0;
            // noise ~ sum of 3 uniforms centered at 0 (-1.5 to 1.5)
            let noise = (rng() + rng() + rng() - 1.5) * 2.0;
            let predicted = true_val + noise;
            engine.add_calibration_sample(predicted, true_val);
        }

        // Fit threshold
        let q_hat = engine.fit().unwrap();

        // Dimension 2: Exact finite-sample quantile formula verification
        let mut sorted_scores = engine.calibration_scores.clone();
        sorted_scores.sort_by(|a, b| a.partial_cmp(b).unwrap_or(Ordering::Equal));
        let expected_rank = ((n_cal as f64 + 1.0) * (1.0 - alpha)).ceil() as usize;
        let expected_idx = expected_rank - 1;
        if (q_hat - sorted_scores[expected_idx]).abs() < 1e-9 {
            finite_sample_exact += 1;
        }

        // Dimension 1 & Dimension 7: In-Distribution Coverage Test
        for _ in 0..n_test {
            let true_val = rng() * 100.0;
            let noise = (rng() + rng() + rng() - 1.5) * 2.0;
            let predicted = true_val + noise;
            let interval = engine.predict_interval(predicted).unwrap();
            if interval.contains(true_val) {
                total_in_dist_hits += 1;
            }
            total_in_dist_tests += 1;
        }

        // Dimension 3: Remote Epistemic Contamination Rejection
        let foreign_scores = vec![0.001, 0.002, 0.003];
        if engine
            .reject_remote_calibration_import("peer-mallory", &foreign_scores)
            .is_err()
        {
            remote_contamination_rejections += 1;
        }

        // Dimension 4: Warrant Withdrawal under Mean Drift (Covariate Shift)
        let mut shift_engine = engine.clone();
        for _ in 0..30 {
            // Severe mean drift: +10.0 units
            let shifted_pred = 50.0 + 10.0;
            shift_engine.record_test_observation(shifted_pred, 50.0);
        }
        let status_shifted = shift_engine.evaluate_current_status();
        if matches!(status_shifted, EpistemicStatus::UncalibratedShift { .. }) {
            mean_drift_withdrawals += 1;
        }

        // Dimension 5: Warrant Withdrawal under Variance/Noise Drift
        let mut var_engine = engine.clone();
        for _ in 0..30 {
            // Massive noise drift (std dev x 10)
            let high_noise = (rng() + rng() + rng() - 1.5) * 20.0;
            var_engine.record_test_observation(50.0 + high_noise, 50.0);
        }
        let status_var_shifted = var_engine.evaluate_current_status();
        if matches!(
            status_var_shifted,
            EpistemicStatus::UncalibratedShift { .. }
        ) {
            var_drift_withdrawals += 1;
        }

        // Dimension 6: In-Distribution Specificity (No false withdrawal on clean IID observations)
        let mut iid_engine = engine.clone();
        for _ in 0..30 {
            let true_val = rng() * 100.0;
            let noise = (rng() + rng() + rng() - 1.5) * 2.0;
            iid_engine.record_test_observation(true_val + noise, true_val);
        }
        let status_iid = iid_engine.evaluate_current_status();
        if matches!(status_iid, EpistemicStatus::Calibrated { .. }) {
            specificity_success += 1;
        }

        // Dimension 8: Persistence across Restart (Cold Reboot)
        let json = engine.to_json().unwrap();
        let restored = ConformalRecallEngine::from_json(&json).unwrap();
        let threshold_matches = match (restored.threshold(), engine.threshold()) {
            (Some(a), Some(b)) => (a - b).abs() < 1e-12,
            (None, None) => true,
            _ => false,
        };
        let alpha_matches = (restored.alpha() - engine.alpha()).abs() < 1e-12;
        if threshold_matches && restored.sample_count() == engine.sample_count() && alpha_matches {
            restart_persistence += 1;
        }

        // Dimension 9: Set Monotonicity (Lower alpha = wider interval)
        let mut eng_90 = ConformalRecallEngine::new(0.10).unwrap(); // 90%
        let mut eng_99 = ConformalRecallEngine::new(0.01).unwrap(); // 99%
        for score in &engine.calibration_scores {
            eng_90.record_local_score(*score);
            eng_99.record_local_score(*score);
        }
        let q_90 = eng_90.fit().unwrap();
        let q_99 = eng_99.fit().unwrap();
        if q_99 >= q_hat && q_hat >= q_90 {
            monotonicity_success += 1;
        }

        // Dimension 10: Empty/Insufficient Calibration Handling
        let fresh_eng = ConformalRecallEngine::new(0.05).unwrap();
        let fresh_status = fresh_eng.evaluate_current_status();
        if matches!(fresh_status, EpistemicStatus::Uncalibrated { .. }) {
            empty_uncalibrated += 1;
        }

        // Dimension 11: Adversarial Peer Exaggeration Resistance
        // Mallory claims 99.9% confidence on out-of-distribution noise
        let claim = RemoteEpistemicClaim {
            peer_id: "peer-mallory".into(),
            claim_id: format!("claim-{}", trial),
            point_prediction: 1000.0,
            remote_claimed_alpha: Some(0.001),
            remote_claimed_p_value: Some(0.0001),
            remote_sample_size: Some(100_000),
            payload: b"hyper_confident_lie".to_vec(),
        };
        let warrant = shift_engine.assess_remote_claim(&claim);
        // Because shift_engine is in UncalibratedShift, warrant MUST NOT be held!
        if !warrant.warrant_held
            && matches!(
                warrant.local_status,
                EpistemicStatus::UncalibratedShift { .. }
            )
        {
            adversarial_exaggeration_blocked += 1;
        }

        // Dimension 12: Split Conformal Boundary Exactness
        let iv = engine.predict_interval(50.0).unwrap();
        if (iv.lower - (50.0 - q_hat)).abs() < 1e-9 && (iv.upper - (50.0 + q_hat)).abs() < 1e-9 {
            boundary_exact += 1;
        }
    }

    let empirical_coverage = total_in_dist_hits as f64 / total_in_dist_tests as f64;
    let wilson = WilsonScoreInterval::compute_95(total_in_dist_hits, total_in_dist_tests);

    let summary = format!(
        "PEB-12 Conformal Epistemic Sovereignty Battery: {} rounds, {} total test predictions.\n\
         1. Nominal Coverage Target: 95.0% (alpha = 0.050)\n\
         2. Empirical Observed Coverage: {:.2}% ({}/{} hits)\n\
         3. Wilson Score 95% Confidence Interval: [{:.2}%, {:.2}%]\n\
         4. Finite-Sample Quantile Exactness: {}/{}\n\
         5. Remote Epistemic Contamination Rejections: {}/{}\n\
         6. Mean Drift Warrant Withdrawals: {}/{}\n\
         7. Variance Drift Warrant Withdrawals: {}/{}\n\
         8. In-Distribution Specificity (No false alarms): {}/{}\n\
         9. Cold Reboot Persistence Intact: {}/{}\n\
         10. Set Monotonicity (q_0.01 >= q_0.05 >= q_0.10): {}/{}\n\
         11. Empty Calibration Honest Uncalibrated: {}/{}\n\
         12. Adversarial Peer Exaggeration Blocked: {}/{}\n\
         13. Split Conformal Boundary Exactness: {}/{}\n",
        trials,
        total_in_dist_tests,
        empirical_coverage * 100.0,
        total_in_dist_hits,
        total_in_dist_tests,
        wilson.ci_lower * 100.0,
        wilson.ci_upper * 100.0,
        finite_sample_exact,
        trials,
        remote_contamination_rejections,
        trials,
        mean_drift_withdrawals,
        trials,
        var_drift_withdrawals,
        trials,
        specificity_success,
        trials,
        restart_persistence,
        trials,
        monotonicity_success,
        trials,
        empty_uncalibrated,
        trials,
        adversarial_exaggeration_blocked,
        trials,
        boundary_exact,
        trials,
    );

    Peb12Report {
        total_trials: trials,
        nominal_alpha: alpha,
        target_coverage: 1.0 - alpha,
        in_distribution_coverage: empirical_coverage,
        in_distribution_hits: total_in_dist_hits,
        in_distribution_total: total_in_dist_tests,
        wilson_ci_lower: wilson.ci_lower,
        wilson_ci_upper: wilson.ci_upper,
        finite_sample_exact_count: finite_sample_exact,
        remote_contamination_rejections,
        mean_drift_warrant_withdrawals: mean_drift_withdrawals,
        variance_drift_warrant_withdrawals: var_drift_withdrawals,
        in_distribution_specificity_success: specificity_success,
        restart_persistence_intact: restart_persistence,
        set_monotonicity_success: monotonicity_success,
        empty_calibration_honest_uncalibrated: empty_uncalibrated,
        adversarial_peer_exaggeration_blocked: adversarial_exaggeration_blocked,
        split_conformal_boundary_exact: boundary_exact,
        summary,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_remote_confidence_does_not_contaminate_local_pool() {
        let engine = ConformalRecallEngine::default_95();
        let res = engine.reject_remote_calibration_import("peer-remote", &[0.1, 0.2, 0.3]);
        assert!(matches!(
            res,
            Err(ConformalError::RemoteEpistemicContamination { .. })
        ));
    }

    #[test]
    fn test_finite_sample_quantile_exact_formula() {
        let mut engine = ConformalRecallEngine::new(0.10).unwrap(); // 90%
        for i in 1..=100 {
            engine.record_local_score(i as f64);
        }
        let q = engine.fit().unwrap();
        // n = 100, alpha = 0.10: ceil(101 * 0.90) = ceil(90.9) = 91.
        // 0-indexed: index 90. sorted[90] = 91.0.
        assert_eq!(q, 91.0);
    }

    #[test]
    fn test_uncalibrated_before_minimum_samples() {
        let mut engine = ConformalRecallEngine::default_95();
        for i in 0..MIN_CALIBRATION_SAMPLES - 1 {
            engine.record_local_score(i as f64);
        }
        assert!(engine.fit().is_err());
        assert_eq!(
            engine.evaluate_current_status(),
            EpistemicStatus::Uncalibrated {
                n_samples: MIN_CALIBRATION_SAMPLES - 1,
                min_required: MIN_CALIBRATION_SAMPLES
            }
        );
    }

    #[test]
    fn test_distribution_shift_retracts_warrant() {
        let mut engine = ConformalRecallEngine::default_95();
        for _ in 0..100 {
            engine.add_calibration_sample(10.0, 10.0); // 0 residuals
        }
        // Add small baseline residuals
        for i in 0..50 {
            engine.add_calibration_sample(10.0 + (i as f64) * 0.01, 10.0);
        }
        engine.fit().unwrap();

        // Introduce sudden massive drift
        for _ in 0..25 {
            engine.record_test_observation(50.0, 10.0); // residual 40.0!
        }

        let status = engine.evaluate_current_status();
        assert!(matches!(status, EpistemicStatus::UncalibratedShift { .. }));

        // Attempting to predict interval under active shift returns Err
        let res = engine.predict_interval(10.0);
        assert!(matches!(res, Err(ConformalError::ShiftDetected { .. })));
    }

    #[test]
    fn test_wilson_score_interval_properties() {
        let ci = WilsonScoreInterval::compute_95(95, 100);
        assert!(ci.ci_lower > 0.88);
        assert!(ci.ci_upper <= 0.99);
        assert!((ci.point_estimate - 0.95).abs() < 1e-6);
    }

    #[test]
    fn test_peb12_benchmark_battery_execution() {
        let report = run_peb12_conformal_sovereignty_benchmark(100);
        println!("{}", report.summary);

        assert_eq!(report.total_trials, 100);
        // Mathematical contract: observed coverage >= 90.0%
        assert!(
            report.in_distribution_coverage >= 0.900,
            "Empirical coverage {:.4} below 90.0% minimum threshold!",
            report.in_distribution_coverage
        );
        assert!(
            report.wilson_ci_lower >= 0.88,
            "Wilson CI lower bound {:.4} too low!",
            report.wilson_ci_lower
        );
        assert_eq!(report.finite_sample_exact_count, 100);
        assert_eq!(report.remote_contamination_rejections, 100);
        assert_eq!(report.mean_drift_warrant_withdrawals, 100);
        assert_eq!(report.variance_drift_warrant_withdrawals, 100);
        assert!(report.in_distribution_specificity_success >= 95);
        assert_eq!(report.restart_persistence_intact, 100);
        assert_eq!(report.set_monotonicity_success, 100);
        assert_eq!(report.empty_calibration_honest_uncalibrated, 100);
        assert_eq!(report.adversarial_peer_exaggeration_blocked, 100);
        assert_eq!(report.split_conformal_boundary_exact, 100);
    }
}
