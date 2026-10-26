//! Present-Belief State, Temporal Validity Windows, and PACMI Cascading Invalidation
//! (`EvoBelief` `arXiv:2610.12789`, `PACMI`, `TIDER`, `Memento 3` `arXiv:2610.11794`, Spec `W1_B4`).
//!
//! Enforces Part 1 Constitutional Invariant 9 (`belief != evidence`):
//! - An observation about yesterday does not establish the present.
//! - Claims carry explicit `domain_scope`, `raw_confidence` (fail-closed in `[0.0, 1.0]`),
//!   effective-time windows (`valid_from_epoch`, `valid_until_epoch`), `supporting_evidence_ids`,
//!   and explicit `falsification_criteria`.
//! - Raw reported confidences are immutable once recorded (`W1_B4` §1.3); empirical-Bayes
//!   recalibrated values (`w = n / (n + 20)`) and Wilson 95% intervals are computed alongside.
//! - When supporting evidence is superseded, quarantined, or erased, PACMI validity propagation
//!   transitively marks dependent beliefs and derived records as `StaleByCascade`.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

/// Statutory empirical-Bayes prior sample weight (`W1_B4` §1.3: `w = n / (n + 20)`).
pub const STATUTORY_EB_PRIOR_K: f64 = 20.0;

/// Current epistemic validity state of a [`BeliefClaim`].
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "state", rename_all = "snake_case")]
pub enum BeliefValidityState {
    /// Unresolved falsifiable hypothesis (`EvoBelief`).
    ActiveHypothesis,
    /// Validated against an observed evidence record within its effective-time window.
    VerifiedPresentFact {
        validation_event: String,
        validation_date: String,
        evidence_record_id: u64,
    },
    /// Falsified by counter-evidence (`Memento 3` / `EvoBelief`).
    Falsified {
        resolution_event: String,
        resolution_date: String,
        counter_evidence_id: u64,
    },
    /// Upstream supporting evidence or causal ancestor was superseded, quarantined, or erased (`PACMI`).
    StaleByCascade {
        invalidated_by_record_id: u64,
        reason: String,
    },
    /// Effective-time window (`valid_until_epoch`) has elapsed (`TIDER`).
    Expired { expired_at_epoch: u64 },
}

impl BeliefValidityState {
    /// True if this belief is currently usable as present-state truth or active hypothesis
    /// (neither falsified, stale by cascade, nor expired).
    #[must_use]
    pub fn is_presently_valid(&self) -> bool {
        matches!(
            self,
            Self::ActiveHypothesis | Self::VerifiedPresentFact { .. }
        )
    }
}

/// A structured belief-class claim distinct from raw historical evidence (`W1_B4` §1.1).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BeliefClaim {
    pub claim_id: u64,
    pub statement: String,
    pub domain_scope: String,
    pub source_date: String,
    pub predicted_outcome: String,
    /// Raw reported confidence in `[0.0, 1.0]`. Never mutated retroactively (`W1_B4` §1.3).
    pub raw_confidence: f32,
    pub falsification_criteria: String,
    pub supporting_evidence_ids: Vec<u64>,
    pub valid_from_epoch: u64,
    pub valid_until_epoch: Option<u64>,
    pub validity: BeliefValidityState,
}

impl BeliefClaim {
    /// Validate required fields and fail-closed confidence bounds (`W1_B4` §1.1).
    #[allow(clippy::too_many_arguments)]
    pub fn new_checked(
        claim_id: u64,
        statement: impl Into<String>,
        domain_scope: impl Into<String>,
        source_date: impl Into<String>,
        predicted_outcome: impl Into<String>,
        raw_confidence: f32,
        falsification_criteria: impl Into<String>,
        supporting_evidence_ids: Vec<u64>,
        valid_from_epoch: u64,
        valid_until_epoch: Option<u64>,
    ) -> Result<Self, String> {
        let statement = statement.into();
        let domain_scope = domain_scope.into();
        let source_date = source_date.into();
        let predicted_outcome = predicted_outcome.into();
        let falsification_criteria = falsification_criteria.into();

        if statement.trim().is_empty() {
            return Err("belief claim statement must not be empty (fail-closed)".into());
        }
        if domain_scope.trim().is_empty() {
            return Err("belief claim domain_scope must not be empty (fail-closed)".into());
        }
        if source_date.trim().is_empty() {
            return Err("belief claim source_date must not be empty (fail-closed)".into());
        }
        if predicted_outcome.trim().is_empty() {
            return Err("belief claim predicted_outcome must not be empty (fail-closed)".into());
        }
        if falsification_criteria.trim().is_empty() {
            return Err(
                "belief claim falsification_criteria must not be empty (fail-closed)".into(),
            );
        }
        if !raw_confidence.is_finite() || !(0.0..=1.0).contains(&raw_confidence) {
            return Err(format!(
                "belief claim confidence {raw_confidence} out of [0.0, 1.0] bounds (fail-closed)"
            ));
        }
        if let Some(until) = valid_until_epoch
            && until < valid_from_epoch
        {
            return Err(format!(
                "belief claim valid_until_epoch ({until}) < valid_from_epoch ({valid_from_epoch})"
            ));
        }

        Ok(Self {
            claim_id,
            statement,
            domain_scope,
            source_date,
            predicted_outcome,
            raw_confidence,
            falsification_criteria,
            supporting_evidence_ids,
            valid_from_epoch,
            valid_until_epoch,
            validity: BeliefValidityState::ActiveHypothesis,
        })
    }

    /// Check whether this claim is effective at `query_epoch` and matches optional `scope_filter`.
    #[must_use]
    pub fn is_effective_at(&self, query_epoch: u64, scope_filter: Option<&str>) -> bool {
        if !self.validity.is_presently_valid() {
            return false;
        }
        if query_epoch < self.valid_from_epoch {
            return false;
        }
        if let Some(until) = self.valid_until_epoch
            && query_epoch > until
        {
            return false;
        }
        if let Some(scope) = scope_filter
            && self.domain_scope != scope
        {
            return false;
        }
        true
    }
}

/// Report returned by PACMI cascading validity propagation when an upstream record is
/// superseded, quarantined, or erased.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PacmiCascadeReport {
    pub root_record_id: u64,
    pub reason: String,
    pub invalidated_descendant_records: Vec<u64>,
    pub invalidated_belief_claims: Vec<u64>,
}

/// Statutory calibration summary over the resolved claims universe (`W1_B4` §1.3).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct BeliefCalibrationReport {
    pub universe: &'static str,
    pub total_claims: usize,
    pub resolved_count: usize,
    pub validated_count: usize,
    pub falsified_count: usize,
    pub stale_cascade_count: usize,
    pub expired_count: usize,
    pub insufficient_data: bool,
    pub degenerate_single_class: bool,
    pub mean_raw_confidence: f64,
    pub empirical_hit_rate: f64,
    pub brier_score: f64,
    pub signed_calibration_gap: f64,
    pub wilson_95_ci: (f64, f64),
    pub shrinkage_weight_w: f64,
    pub mean_recalibrated_confidence: f64,
}

/// Compute Wilson 95% confidence interval for `k` successes out of `n` trials.
#[must_use]
pub fn wilson_95_interval(k: usize, n: usize) -> (f64, f64) {
    if n == 0 {
        return (0.0, 1.0);
    }
    let z = 1.959_964_f64;
    let nf = n as f64;
    let p = k as f64 / nf;
    let denom = 1.0 + (z * z) / nf;
    let center = (p + (z * z) / (2.0 * nf)) / denom;
    let rad = (p * (1.0 - p) / nf + (z * z) / (4.0 * nf * nf))
        .max(0.0)
        .sqrt();
    let margin = z * rad / denom;
    (
        (center - margin).clamp(0.0, 1.0),
        (center + margin).clamp(0.0, 1.0),
    )
}

/// Empirical-Bayes shrinkage recalibration (`w = n / (n + k)`).
/// Raw confidence is never mutated; recalibrated value is returned alongside (`W1_B4` §1.3).
#[must_use]
pub fn empirical_bayes_recalibrate(raw_confidence: f64, hit_rate: f64, n: usize, k: f64) -> f64 {
    if n == 0 {
        return raw_confidence;
    }
    let nf = n as f64;
    let denom = nf + k.max(0.0);
    let w = if denom > 0.0 { nf / denom } else { 1.0 };
    (raw_confidence + w * (hit_rate - raw_confidence)).clamp(0.0, 1.0)
}

/// Compute the statutory calibration report over a slice of [`BeliefClaim`]s.
/// Expired claims are excluded from the resolved Brier denominator and counted separately (`W1_B4` §1.3).
#[must_use]
pub fn compute_statutory_calibration(
    claims: &[BeliefClaim],
    domain_filter: Option<&str>,
) -> BeliefCalibrationReport {
    let filtered: Vec<&BeliefClaim> = claims
        .iter()
        .filter(|c| domain_filter.is_none_or(|d| c.domain_scope == d))
        .collect();

    let total_claims = filtered.len();
    let mut validated_count = 0usize;
    let mut falsified_count = 0usize;
    let mut stale_cascade_count = 0usize;
    let mut expired_count = 0usize;
    let mut sum_raw = 0.0_f64;
    let mut sum_brier = 0.0_f64;

    for claim in &filtered {
        match &claim.validity {
            BeliefValidityState::VerifiedPresentFact { .. } => {
                validated_count += 1;
                let p = f64::from(claim.raw_confidence);
                sum_raw += p;
                sum_brier += (p - 1.0) * (p - 1.0);
            }
            BeliefValidityState::Falsified { .. } => {
                falsified_count += 1;
                let p = f64::from(claim.raw_confidence);
                sum_raw += p;
                sum_brier += p * p;
            }
            BeliefValidityState::StaleByCascade { .. } => {
                stale_cascade_count += 1;
            }
            BeliefValidityState::Expired { .. } => {
                expired_count += 1;
            }
            BeliefValidityState::ActiveHypothesis => {}
        }
    }

    let resolved_count = validated_count + falsified_count;
    if resolved_count == 0 {
        return BeliefCalibrationReport {
            universe: "claims_ledger_resolved_set",
            total_claims,
            resolved_count: 0,
            validated_count: 0,
            falsified_count: 0,
            stale_cascade_count,
            expired_count,
            insufficient_data: true,
            degenerate_single_class: false,
            mean_raw_confidence: 0.0,
            empirical_hit_rate: 0.0,
            brier_score: 0.0,
            signed_calibration_gap: 0.0,
            wilson_95_ci: (0.0, 1.0),
            shrinkage_weight_w: 0.0,
            mean_recalibrated_confidence: 0.0,
        };
    }

    let nf = resolved_count as f64;
    let mean_raw = sum_raw / nf;
    let hit_rate = validated_count as f64 / nf;
    let brier = sum_brier / nf;
    let gap = mean_raw - hit_rate;
    let ci = wilson_95_interval(validated_count, resolved_count);
    let w = nf / (nf + STATUTORY_EB_PRIOR_K);
    let recalibrated =
        empirical_bayes_recalibrate(mean_raw, hit_rate, resolved_count, STATUTORY_EB_PRIOR_K);
    let degenerate_single_class = validated_count == 0 || falsified_count == 0;

    BeliefCalibrationReport {
        universe: "claims_ledger_resolved_set",
        total_claims,
        resolved_count,
        validated_count,
        falsified_count,
        stale_cascade_count,
        expired_count,
        insufficient_data: false,
        degenerate_single_class,
        mean_raw_confidence: mean_raw,
        empirical_hit_rate: hit_rate,
        brier_score: brier,
        signed_calibration_gap: gap,
        wilson_95_ci: ci,
        shrinkage_weight_w: w,
        mean_recalibrated_confidence: recalibrated,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fail_closed_confidence_and_required_fields() {
        assert!(
            BeliefClaim::new_checked(
                1,
                " hypothesis ",
                "gen3:auth",
                "2026-10-26",
                "latency < 1ms",
                1.01,
                "latency >= 1ms",
                vec![1],
                0,
                None,
            )
            .is_err()
        );

        assert!(
            BeliefClaim::new_checked(
                1,
                "",
                "gen3:auth",
                "2026-10-26",
                "latency < 1ms",
                0.8,
                "latency >= 1ms",
                vec![1],
                0,
                None,
            )
            .is_err()
        );
    }

    #[test]
    fn statutory_calibration_discloses_degeneracy_and_preserves_raw() {
        let mut c1 = BeliefClaim::new_checked(
            1,
            "claim 1",
            "arch",
            "2026-10-26",
            "pass",
            0.90,
            "fail",
            vec![10],
            1,
            Some(10),
        )
        .unwrap();
        c1.validity = BeliefValidityState::VerifiedPresentFact {
            validation_event: "test passed".into(),
            validation_date: "2026-10-26".into(),
            evidence_record_id: 11,
        };
        let report_degen = compute_statutory_calibration(&[c1.clone()], None);
        assert!(report_degen.degenerate_single_class);
        assert!((c1.raw_confidence - 0.90).abs() < 1e-6);

        let mut c2 = BeliefClaim::new_checked(
            2,
            "claim 2",
            "arch",
            "2026-10-26",
            "pass",
            0.90,
            "fail",
            vec![12],
            1,
            None,
        )
        .unwrap();
        c2.validity = BeliefValidityState::Falsified {
            resolution_event: "test failed".into(),
            resolution_date: "2026-10-26".into(),
            counter_evidence_id: 13,
        };
        let report = compute_statutory_calibration(&[c1, c2], Some("arch"));
        assert!(!report.degenerate_single_class);
        assert_eq!(report.resolved_count, 2);
        assert!((report.empirical_hit_rate - 0.5).abs() < 1e-6);
        assert!((report.signed_calibration_gap - 0.4).abs() < 1e-6);
    }
}
