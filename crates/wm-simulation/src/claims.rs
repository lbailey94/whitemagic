//! Claims ledger — the prescience track record as a first-class store.
//!
//! Ports the v26 `temporal_db` semantics (1 week of verified lead = 1 point,
//! timestamped source + public validation event required) onto the v5
//! substrate, alongside the existing [`CalibrationStore`] Brier machinery.
//!
//! A claim is a dated, falsifiable prediction. It is recorded with a source
//! date and a falsification criterion; it is resolved against a validation
//! event (validated or falsified). Validated claims earn points equal to the
//! verified lead time in weeks. The ledger always reports the falsified
//! count alongside the score — the honesty infrastructure is part of the
//! store, not an afterthought (v26's 0-falsified / overconfidence lesson).

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

/// Status of a claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ClaimStatus {
    /// Recorded, awaiting a validation event.
    Pending,
    /// Confirmed by a public, dated validation event.
    Validated,
    /// Explicitly falsified — the miss is part of the record.
    Falsified,
}

impl ClaimStatus {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Validated => "validated",
            Self::Falsified => "falsified",
        }
    }
}

/// A dated validation (or falsification) event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationEvent {
    /// What validated the claim (e.g. "Anthropic Claude Memory, Apr 23 2026").
    pub event: String,
    /// Epoch day (days since Unix epoch) of the validation event.
    pub date: i64,
    /// Optional source URL / identifier.
    pub source: Option<String>,
}

/// A single dated, falsifiable prediction.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Claim {
    /// Stable identifier (e.g. "claim-0001").
    pub id: String,
    /// The claim statement.
    pub statement: String,
    /// Domain / category label (e.g. "ai_governance", "agent_architecture").
    pub domain: String,
    /// Epoch day the claim was first documented.
    pub source_date: i64,
    /// What the claim predicts, resolved.
    pub predicted_outcome: String,
    /// Self-reported confidence in [0, 1].
    pub confidence: f64,
    /// Falsification criterion — the claim is WRONG if this does not happen.
    pub falsification_criteria: String,
    /// Resolution status.
    pub status: ClaimStatus,
    /// Validation event once resolved (None while pending).
    pub validation_event: Option<ValidationEvent>,
    /// Verified lead time in weeks once validated.
    pub lead_time_weeks: Option<f64>,
    /// Points earned: lead weeks for validated claims (1 week = 1 point).
    pub points: Option<f64>,
}

impl Claim {
    /// Verified lead time in weeks between two epoch days.
    #[must_use]
    pub fn lead_weeks(source_date: i64, validation_date: i64) -> f64 {
        (validation_date - source_date) as f64 / 7.0
    }
}

/// The claims ledger — persistable via [`to_json`](Self::to_json) /
/// [`from_json`](Self::from_json), like the calibration store.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ClaimsLedger {
    /// All claims (pending, validated, falsified).
    pub claims: Vec<Claim>,
    /// Sequence counter for claim IDs.
    next_id: u64,
}

/// Prior-strength constant for the empirical-Bayes confidence shrinkage.
///
/// Calibrated confidence = raw + w·(hit_rate − raw) with w = n/(n + k).
/// With n resolved claims and k = 20, a base rate estimated from 20 samples
/// carries half the weight of the raw confidence; fewer samples → weaker
/// shrinkage, more → stronger. Exposed in the calibration report so the
/// effective weight is always visible.
pub const CALIBRATION_PRIOR_SAMPLES: f64 = 20.0;

/// Calibration of the resolved claims — the prescience track record's
/// honesty statement. Computed over validated + falsified claims.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClaimCalibration {
    /// Number of resolved claims.
    pub resolved: usize,
    /// Validated / falsified counts.
    pub validated: usize,
    pub falsified: usize,
    /// Mean self-reported confidence over resolved claims.
    pub mean_confidence: f64,
    /// Observed validation rate (validated / resolved).
    pub hit_rate: f64,
    /// mean_confidence − hit_rate. Positive = overconfident,
    /// negative = underconfident (standard convention).
    pub calibration_gap: f64,
    /// Mean Brier score over resolved claims (lower is better).
    pub brier: f64,
    /// Wilson 95% confidence interval (lower, upper) for the hit rate.
    pub hit_rate_ci95: (f64, f64),
    /// Effective shrinkage weight w = n/(n + CALIBRATION_PRIOR_SAMPLES).
    pub shrinkage: f64,
}

/// Wilson score 95% confidence interval for a binomial rate.
#[must_use]
pub fn wilson95(successes: usize, n: usize) -> (f64, f64) {
    if n == 0 {
        return (0.0, 1.0);
    }
    let z = 1.959_964;
    let nf = n as f64;
    let p = successes as f64 / nf;
    let denom = 1.0 + z * z / nf;
    let center = (p + z * z / (2.0 * nf)) / denom;
    let margin = z * (p * (1.0 - p) / nf + z * z / (4.0 * nf * nf)).sqrt() / denom;
    ((center - margin).max(0.0), (center + margin).min(1.0))
}

impl ClaimsLedger {
    /// Create an empty ledger.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Record a new pending claim.
    ///
    /// Returns the stored claim. The falsification criterion is mandatory —
    /// a claim that cannot be falsified is not a claim.
    pub fn record(
        &mut self,
        statement: &str,
        domain: &str,
        source_date: i64,
        predicted_outcome: &str,
        confidence: f64,
        falsification_criteria: &str,
    ) -> Claim {
        let id = format!("claim-{:04}", self.next_id);
        self.next_id += 1;
        let claim = Claim {
            id,
            statement: statement.to_string(),
            domain: domain.to_string(),
            source_date,
            predicted_outcome: predicted_outcome.to_string(),
            confidence: confidence.clamp(0.0, 1.0),
            falsification_criteria: falsification_criteria.to_string(),
            status: ClaimStatus::Pending,
            validation_event: None,
            lead_time_weeks: None,
            points: None,
        };
        self.claims.push(claim.clone());
        claim
    }

    /// Resolve a claim against a validation event.
    ///
    /// `validated: true` marks the claim validated and credits points equal
    /// to the verified lead time in weeks. `validated: false` marks it
    /// falsified — recorded as a miss, which is part of the track record.
    pub fn resolve(
        &mut self,
        claim_id: &str,
        validated: bool,
        event: &str,
        event_date: i64,
        source: Option<String>,
    ) -> Result<Claim, String> {
        let claim = self
            .claims
            .iter_mut()
            .find(|c| c.id == claim_id)
            .ok_or_else(|| format!("unknown claim id: {claim_id}"))?;

        if claim.status != ClaimStatus::Pending {
            return Err(format!("claim {} already resolved", claim.id));
        }

        claim.validation_event = Some(ValidationEvent {
            event: event.to_string(),
            date: event_date,
            source,
        });

        if validated {
            claim.status = ClaimStatus::Validated;
            let lead = Claim::lead_weeks(claim.source_date, event_date);
            claim.lead_time_weeks = Some(lead);
            claim.points = Some(lead);
        } else {
            claim.status = ClaimStatus::Falsified;
            claim.lead_time_weeks = None;
            claim.points = Some(0.0);
        }

        Ok(claim.clone())
    }

    /// Aggregate ledger status: totals, score, average lead, falsified count.
    #[must_use]
    pub fn status(&self) -> Value {
        let total = self.claims.len();
        let validated = self
            .claims
            .iter()
            .filter(|c| c.status == ClaimStatus::Validated)
            .count();
        let falsified = self
            .claims
            .iter()
            .filter(|c| c.status == ClaimStatus::Falsified)
            .count();
        let pending = self
            .claims
            .iter()
            .filter(|c| c.status == ClaimStatus::Pending)
            .count();
        let points: f64 = self.claims.iter().filter_map(|c| c.points).sum();
        let leads: Vec<f64> = self
            .claims
            .iter()
            .filter_map(|c| c.lead_time_weeks)
            .collect();
        let avg_lead = if leads.is_empty() {
            0.0
        } else {
            leads.iter().sum::<f64>() / leads.len() as f64
        };

        // Per-domain breakdown.
        let mut domains: Vec<Value> = Vec::new();
        let mut seen: Vec<String> = Vec::new();
        for claim in &self.claims {
            if seen.contains(&claim.domain) {
                continue;
            }
            seen.push(claim.domain.clone());
            let d_validated = self
                .claims
                .iter()
                .filter(|c| c.domain == claim.domain && c.status == ClaimStatus::Validated)
                .count();
            let d_falsified = self
                .claims
                .iter()
                .filter(|c| c.domain == claim.domain && c.status == ClaimStatus::Falsified)
                .count();
            let d_points: f64 = self
                .claims
                .iter()
                .filter(|c| c.domain == claim.domain)
                .filter_map(|c| c.points)
                .sum();
            domains.push(json!({
                "domain": claim.domain,
                "validated": d_validated,
                "falsified": d_falsified,
                "points": d_points,
            }));
        }

        json!({
            "status": "success",
            "total_claims": total,
            "validated": validated,
            "falsified": falsified,
            "pending": pending,
            "total_points": points,
            "avg_lead_weeks": avg_lead,
            "domains": domains,
        })
    }

    /// List claims, optionally filtered by domain and status.
    #[must_use]
    pub fn list(&self, domain: Option<&str>, status: Option<ClaimStatus>) -> Vec<Claim> {
        self.claims
            .iter()
            .filter(|c| domain.is_none_or(|d| c.domain == d))
            .filter(|c| status.is_none_or(|s| c.status == s))
            .cloned()
            .collect()
    }

    /// Calibration report over resolved (validated + falsified) claims.
    #[must_use]
    pub fn calibration(&self) -> ClaimCalibration {
        let resolved: Vec<&Claim> = self
            .claims
            .iter()
            .filter(|c| c.status != ClaimStatus::Pending)
            .collect();
        let n = resolved.len();
        let validated = resolved
            .iter()
            .filter(|c| c.status == ClaimStatus::Validated)
            .count();
        let falsified = n - validated;

        if n == 0 {
            return ClaimCalibration {
                resolved: 0,
                validated: 0,
                falsified: 0,
                mean_confidence: 0.0,
                hit_rate: 0.0,
                calibration_gap: 0.0,
                brier: 0.0,
                hit_rate_ci95: (0.0, 1.0),
                shrinkage: 0.0,
            };
        }

        let nf = n as f64;
        let mean_confidence = resolved.iter().map(|c| c.confidence).sum::<f64>() / nf;
        let hit_rate = validated as f64 / nf;
        let brier = resolved
            .iter()
            .map(|c| {
                let y = if c.status == ClaimStatus::Validated {
                    1.0
                } else {
                    0.0
                };
                (c.confidence - y).powi(2)
            })
            .sum::<f64>()
            / nf;

        ClaimCalibration {
            resolved: n,
            validated,
            falsified,
            mean_confidence,
            hit_rate,
            calibration_gap: mean_confidence - hit_rate,
            brier,
            hit_rate_ci95: wilson95(validated, n),
            shrinkage: nf / (nf + CALIBRATION_PRIOR_SAMPLES),
        }
    }

    /// Empirical-Bayes calibrated confidence for a raw confidence.
    ///
    /// Shrinks the raw confidence toward the observed hit rate, weighted by
    /// resolved sample size (w = n/(n + k)). Identity when nothing is
    /// resolved — the record is never edited, only re-read through the lens
    /// of its own track record.
    #[must_use]
    pub fn calibrated_confidence(&self, raw: f64) -> f64 {
        let validated = self
            .claims
            .iter()
            .filter(|c| c.status == ClaimStatus::Validated)
            .count();
        let resolved = self
            .claims
            .iter()
            .filter(|c| c.status != ClaimStatus::Pending)
            .count();
        if resolved == 0 {
            return raw.clamp(0.0, 1.0);
        }
        let hit_rate = validated as f64 / resolved as f64;
        let w = resolved as f64 / (resolved as f64 + CALIBRATION_PRIOR_SAMPLES);
        w.mul_add(hit_rate - raw, raw).clamp(0.0, 1.0)
    }

    /// Serialize to JSON for persistence.
    #[must_use]
    pub fn to_json(&self) -> Value {
        serde_json::to_value(self).unwrap_or_else(|_| json!({}))
    }

    /// Restore from persisted JSON.
    pub fn from_json(&mut self, value: &Value) -> Result<(), String> {
        let restored: Self = serde_json::from_value(value.clone()).map_err(|e| e.to_string())?;
        *self = restored;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn epoch_day(y: i64, m: i64, d: i64) -> i64 {
        // Days since 1970-01-01 for the given calendar date (proleptic).
        let (y, m) = if m <= 2 { (y - 1, m + 12) } else { (y, m) };
        let a = y / 100;
        let b = 2 - a + a / 4;
        (365 * (y + 4716) + (y + 4716) / 4 - b + (153 * (m + 1)) / 5 + d - 1524) - 719_163
    }

    fn days_between(start: (i64, i64, i64), end: (i64, i64, i64)) -> i64 {
        epoch_day(end.0, end.1, end.2) - epoch_day(start.0, start.1, start.2)
    }

    #[test]
    fn record_creates_pending_claim() {
        let mut ledger = ClaimsLedger::new();
        let claim = ledger.record(
            "Karma-style audit ledger ships in a major lab",
            "ai_governance",
            epoch_day(2025, 5, 26),
            "Anthropic ships an append-only audit log",
            0.7,
            "No major lab ships an append-only agent audit log by 2026-12-31",
        );
        assert_eq!(claim.id, "claim-0000");
        assert_eq!(claim.status, ClaimStatus::Pending);
        assert!(claim.points.is_none());
        assert_eq!(ledger.claims.len(), 1);
    }

    #[test]
    fn resolve_validated_credits_lead_weeks() {
        let mut ledger = ClaimsLedger::new();
        let claim = ledger.record(
            "Declared-vs-actual side-effect audit",
            "ai_governance",
            epoch_day(2025, 5, 26),
            "Append-only audit with side-effect tracking ships publicly",
            0.8,
            "No public audit substrate by 2026-12-31",
        );
        let lead = days_between((2025, 5, 26), (2026, 4, 23)); // 332 days
        let resolved = ledger
            .resolve(
                &claim.id,
                true,
                "Anthropic Claude Memory audit log",
                epoch_day(2025, 5, 26) + lead,
                Some("anthropic.com".into()),
            )
            .unwrap();
        assert_eq!(resolved.status, ClaimStatus::Validated);
        assert_eq!(resolved.points.unwrap(), 332.0 / 7.0);
        assert_eq!(resolved.lead_time_weeks.unwrap(), 332.0 / 7.0);
    }

    #[test]
    fn resolve_falsified_is_recorded_as_miss() {
        let mut ledger = ClaimsLedger::new();
        let claim = ledger.record(
            "Speculative claim that fails",
            "test",
            epoch_day(2026, 1, 1),
            "Something happens",
            0.5,
            "It does not happen by 2026-06-30",
        );
        let resolved = ledger
            .resolve(
                &claim.id,
                false,
                "Nothing happened",
                epoch_day(2026, 7, 1),
                None,
            )
            .unwrap();
        assert_eq!(resolved.status, ClaimStatus::Falsified);
        assert_eq!(resolved.points, Some(0.0));
        let status = ledger.status();
        assert_eq!(status["falsified"], 1);
    }

    #[test]
    fn cannot_resolve_twice() {
        let mut ledger = ClaimsLedger::new();
        let claim = ledger.record("Once", "test", epoch_day(2026, 1, 1), "X", 0.5, "Not X");
        ledger
            .resolve(&claim.id, true, "event", epoch_day(2026, 1, 8), None)
            .unwrap();
        let second = ledger.resolve(&claim.id, true, "again", epoch_day(2026, 1, 15), None);
        assert!(second.is_err());
    }

    #[test]
    fn status_totals_and_domains() {
        let mut ledger = ClaimsLedger::new();
        let a = ledger.record(
            "A",
            "ai_governance",
            epoch_day(2026, 1, 1),
            "X",
            0.6,
            "not X",
        );
        let b = ledger.record("B", "energy", epoch_day(2026, 1, 1), "Y", 0.5, "not Y");
        ledger
            .resolve(&a.id, true, "ev", epoch_day(2026, 1, 15), None)
            .unwrap();
        ledger
            .resolve(&b.id, false, "miss", epoch_day(2026, 2, 1), None)
            .unwrap();
        let status = ledger.status();
        assert_eq!(status["total_claims"], 2);
        assert_eq!(status["validated"], 1);
        assert_eq!(status["falsified"], 1);
        assert_eq!(status["pending"], 0);
        assert_eq!(status["total_points"], 2.0); // 14 days / 7
        assert_eq!(status["domains"].as_array().unwrap().len(), 2);
    }

    #[test]
    fn json_roundtrip() {
        let mut ledger = ClaimsLedger::new();
        let claim = ledger.record("R", "test", epoch_day(2026, 1, 1), "X", 0.5, "not X");
        ledger
            .resolve(&claim.id, true, "ev", epoch_day(2026, 1, 8), None)
            .unwrap();
        let json = ledger.to_json();
        let mut restored = ClaimsLedger::new();
        restored.from_json(&json).unwrap();
        assert_eq!(restored.claims.len(), 1);
        assert_eq!(restored.claims[0].status, ClaimStatus::Validated);
        assert_eq!(restored.claims[0].points, Some(1.0));
    }

    #[test]
    fn list_filters_by_domain_and_status() {
        let mut ledger = ClaimsLedger::new();
        let a = ledger.record(
            "A",
            "ai_governance",
            epoch_day(2026, 1, 1),
            "X",
            0.5,
            "not X",
        );
        let b = ledger.record("B", "energy", epoch_day(2026, 1, 1), "Y", 0.5, "not Y");
        ledger
            .resolve(&a.id, true, "ev", epoch_day(2026, 1, 8), None)
            .unwrap();
        assert_eq!(ledger.list(Some("ai_governance"), None).len(), 1);
        assert_eq!(ledger.list(None, Some(ClaimStatus::Pending)).len(), 1);
        assert_eq!(
            ledger
                .list(Some("energy"), Some(ClaimStatus::Pending))
                .len(),
            1
        );
        assert_eq!(
            ledger
                .list(Some("energy"), Some(ClaimStatus::Validated))
                .len(),
            0
        );
        assert_eq!(ledger.list(None, None).len(), 2);
        assert_eq!(b.id, "claim-0001");
    }

    #[test]
    fn missing_falsification_criteria_still_recorded_but_flagged() {
        // The tool layer enforces a non-empty criterion; the ledger stores as-is.
        let mut ledger = ClaimsLedger::new();
        let claim = ledger.record("Vague", "test", epoch_day(2026, 1, 1), "X", 0.5, "");
        assert!(claim.falsification_criteria.is_empty());
    }

    #[test]
    fn calibration_empty_ledger_is_identity() {
        let ledger = ClaimsLedger::new();
        let cal = ledger.calibration();
        assert_eq!(cal.resolved, 0);
        assert_eq!(cal.calibration_gap, 0.0);
        assert_eq!(cal.hit_rate_ci95, (0.0, 1.0));
        assert_eq!(ledger.calibrated_confidence(0.8), 0.8);
    }

    #[test]
    fn calibration_reports_gap_brier_and_shrinkage() {
        let mut ledger = ClaimsLedger::new();
        // 3 validated at 0.6/0.7/0.8, 1 falsified at 0.5.
        let ids: Vec<String> = [0.6, 0.7, 0.8, 0.5]
            .iter()
            .map(|c| {
                let claim = ledger.record("C", "test", epoch_day(2026, 1, 1), "X", *c, "not X");
                claim.id
            })
            .collect();
        for (i, id) in ids.iter().enumerate() {
            ledger
                .resolve(id, i < 3, "ev", epoch_day(2026, 1, 15), None)
                .unwrap();
        }

        let cal = ledger.calibration();
        assert_eq!(cal.resolved, 4);
        assert_eq!(cal.validated, 3);
        assert_eq!(cal.falsified, 1);
        assert!((cal.mean_confidence - 0.65).abs() < 1e-12);
        assert!((cal.hit_rate - 0.75).abs() < 1e-12);
        // Underconfident: stated confidences run BELOW the realized hit rate.
        assert!((cal.calibration_gap - (0.65 - 0.75)).abs() < 1e-12);
        assert!(cal.calibration_gap < 0.0);
        // Brier: (0.4^2 + 0.3^2 + 0.2^2 + 0.5^2) / 4 = (0.16+0.09+0.04+0.25)/4.
        assert!((cal.brier - 0.135).abs() < 1e-12);
        // Shrinkage weight n/(n+k) = 4/24 = 1/6.
        assert!((cal.shrinkage - 1.0 / 6.0).abs() < 1e-12);
    }

    #[test]
    fn calibrated_confidence_shrinks_toward_hit_rate() {
        let mut ledger = ClaimsLedger::new();
        let ok = ledger.record("A", "test", epoch_day(2026, 1, 1), "X", 0.7, "not X");
        let miss = ledger.record("B", "test", epoch_day(2026, 1, 1), "Y", 0.5, "not Y");
        ledger
            .resolve(&ok.id, true, "ev", epoch_day(2026, 1, 8), None)
            .unwrap();
        ledger
            .resolve(&miss.id, false, "ev", epoch_day(2026, 1, 8), None)
            .unwrap();

        // n=2, k=20 → w=2/22. hit_rate=0.5. raw 0.8 → 0.8 + w*(0.5-0.8).
        let w = 2.0_f64 / 22.0;
        let expected = w.mul_add(0.5_f64 - 0.8, 0.8);
        let got = ledger.calibrated_confidence(0.8);
        assert!((got - expected).abs() < 1e-12);
        assert!(
            got < 0.8,
            "overconfident raw confidences must be pulled down"
        );
        // Underconfident raw confidences are pulled up.
        assert!(ledger.calibrated_confidence(0.2) > 0.2);
        // Clamped to [0, 1] even with extreme inputs.
        assert_eq!(ledger.calibrated_confidence(1.5), 1.0);
    }

    #[test]
    fn wilson_interval_matches_known_values() {
        // 19/20 successes: p̂ = 0.95 → CI ≈ [0.764, 0.991].
        let (lo, hi) = wilson95(19, 20);
        assert!(lo > 0.75 && lo < 0.78, "lo {lo}");
        assert!(hi > 0.98 && hi < 1.0, "hi {hi}");
        // 0/0 → full range.
        assert_eq!(wilson95(0, 0), (0.0, 1.0));
        // 0/10 → [0, ~0.28].
        let (lo, hi) = wilson95(0, 10);
        assert_eq!(lo, 0.0);
        assert!(hi < 0.35);
    }
}
