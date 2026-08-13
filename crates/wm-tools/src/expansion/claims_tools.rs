//! Claims tools — claims.add, claims.resolve, claims.status, claims.list.
//!
//! Gana::Mound — the prescience track record as a first-class store.
//!
//! The claims ledger ports the v26 temporal_db semantics (1 week of verified
//! lead = 1 point; timestamped source + public validation event required).
//! The falsified count is always reported alongside the score — the honesty
//! infrastructure is part of the store.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use std::sync::{Arc, Mutex};

use serde_json::{Value, json};
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_simulation::{ClaimStatus, ClaimsLedger};

/// Epoch day for a date string "YYYY-MM-DD".
///
/// Days since 1970-01-01 (proleptic Gregorian), matching the ledger's
/// semantics. Uses `chrono` — the earlier hand-rolled JDN arithmetic had
/// a constant offset of 1,721,451 days (it computed days since year 1),
/// which shifted every recorded date by ~4,713 years.
fn epoch_day_from_str(date: &str) -> i64 {
    chrono::NaiveDate::parse_from_str(date, "%Y-%m-%d")
        .ok()
        .map_or(0, |d| {
            (d - chrono::NaiveDate::from_ymd_opt(1970, 1, 1).unwrap()).num_days()
        })
}

/// `claims.*` — record, resolve, and report on the prescience track record.
pub struct ClaimsTool {
    ledger: Arc<Mutex<ClaimsLedger>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ClaimsTool {
    #[must_use]
    pub fn new(ledger: Arc<Mutex<ClaimsLedger>>) -> Self {
        Self {
            ledger,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("simulation".into())]),
        }
    }
}

impl Default for ClaimsTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(ClaimsLedger::new())))
    }
}

#[async_trait]
impl Tool for ClaimsTool {
    fn name(&self) -> &str {
        "claims"
    }
    fn gana(&self) -> Gana {
        Gana::Mound
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Prescience claims ledger (actions: add, resolve, status, list, calibration). add requires statement, domain, source_date (YYYY-MM-DD), predicted_outcome, confidence, falsification_criteria. resolve requires claim_id, validated (bool), event, event_date (YYYY-MM-DD). calibration reports the resolved track record: Brier, calibration gap, Wilson hit-rate interval, and recalibrated pending confidences."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let action = args
            .get("action")
            .and_then(Value::as_str)
            .unwrap_or("status");
        let mut ledger = self
            .ledger
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("claims ledger lock: {e}")))?;

        match action {
            "add" => {
                let statement = args
                    .get("statement")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        wm_core::CoreError::InvalidArgs("statement is required for add".into())
                    })?;
                let domain = args
                    .get("domain")
                    .and_then(Value::as_str)
                    .unwrap_or("general");
                let source_date = args
                    .get("source_date")
                    .and_then(Value::as_str)
                    .map(epoch_day_from_str)
                    .ok_or_else(|| {
                        wm_core::CoreError::InvalidArgs(
                            "source_date (YYYY-MM-DD) is required for add".into(),
                        )
                    })?;
                let predicted_outcome = args
                    .get("predicted_outcome")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        wm_core::CoreError::InvalidArgs(
                            "predicted_outcome is required for add".into(),
                        )
                    })?;
                let confidence = args
                    .get("confidence")
                    .and_then(Value::as_f64)
                    .unwrap_or(0.5)
                    .clamp(0.0, 1.0);
                let falsification_criteria = args
                    .get("falsification_criteria")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        wm_core::CoreError::InvalidArgs(
                            "falsification_criteria is required for add".into(),
                        )
                    })?;
                if falsification_criteria.is_empty() {
                    return Err(wm_core::CoreError::InvalidArgs(
                        "falsification_criteria must be non-empty — a claim that cannot be falsified is not a claim".into(),
                    ));
                }
                let claim = ledger.record(
                    statement,
                    domain,
                    source_date,
                    predicted_outcome,
                    confidence,
                    falsification_criteria,
                );
                Ok(json!({
                    "status": "success",
                    "claim_id": claim.id,
                    "claim_status": claim.status.as_str(),
                }))
            }
            "resolve" => {
                let claim_id = args
                    .get("claim_id")
                    .and_then(Value::as_str)
                    .ok_or_else(|| {
                        wm_core::CoreError::InvalidArgs("claim_id is required for resolve".into())
                    })?;
                let validated =
                    args.get("validated")
                        .and_then(Value::as_bool)
                        .ok_or_else(|| {
                            wm_core::CoreError::InvalidArgs(
                                "validated (boolean) is required for resolve".into(),
                            )
                        })?;
                let event = args.get("event").and_then(Value::as_str).ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("event is required for resolve".into())
                })?;
                let event_date = args
                    .get("event_date")
                    .and_then(Value::as_str)
                    .map(epoch_day_from_str)
                    .ok_or_else(|| {
                        wm_core::CoreError::InvalidArgs(
                            "event_date (YYYY-MM-DD) is required for resolve".into(),
                        )
                    })?;
                let source = args
                    .get("source")
                    .and_then(Value::as_str)
                    .map(str::to_string);
                let claim = ledger
                    .resolve(claim_id, validated, event, event_date, source)
                    .map_err(wm_core::CoreError::Tool)?;
                Ok(json!({
                    "status": "success",
                    "claim_id": claim.id,
                    "claim_status": claim.status.as_str(),
                    "lead_time_weeks": claim.lead_time_weeks,
                    "points": claim.points,
                }))
            }
            "status" => Ok(ledger.status()),
            "calibration" => {
                let cal = ledger.calibration();
                let interpretation = if cal.calibration_gap > 0.05 {
                    "overconfident"
                } else if cal.calibration_gap < -0.05 {
                    "underconfident"
                } else {
                    "calibrated"
                };
                // Pending claims get a recalibrated confidence alongside the
                // raw record — the raw value is history and is never edited.
                let pending: Vec<Value> = ledger
                    .claims
                    .iter()
                    .filter(|c| c.status == ClaimStatus::Pending)
                    .map(|c| {
                        json!({
                            "id": c.id,
                            "confidence": c.confidence,
                            "calibrated_confidence": ledger.calibrated_confidence(c.confidence),
                        })
                    })
                    .collect();
                Ok(json!({
                    "status": "success",
                    "resolved": cal.resolved,
                    "validated": cal.validated,
                    "falsified": cal.falsified,
                    "mean_confidence": cal.mean_confidence,
                    "hit_rate": cal.hit_rate,
                    "calibration_gap": cal.calibration_gap,
                    "interpretation": interpretation,
                    "brier": cal.brier,
                    "hit_rate_ci95_low": cal.hit_rate_ci95.0,
                    "hit_rate_ci95_high": cal.hit_rate_ci95.1,
                    "shrinkage": cal.shrinkage,
                    "pending_recalibrated": pending,
                }))
            }
            "list" => {
                let domain = args.get("domain").and_then(Value::as_str);
                let status = match args.get("status").and_then(Value::as_str) {
                    Some("validated") => Some(ClaimStatus::Validated),
                    Some("falsified") => Some(ClaimStatus::Falsified),
                    Some("pending") => Some(ClaimStatus::Pending),
                    _ => None,
                };
                let claims = ledger.list(domain, status);
                Ok(json!({
                    "status": "success",
                    "count": claims.len(),
                    "claims": claims,
                }))
            }
            other => Err(wm_core::CoreError::InvalidArgs(format!(
                "unknown claims action: {other}"
            ))),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the claims tool and its explicit single-action alias routes.
///
/// Aliases: `claims.add`, `claims.resolve`, `claims.status`, `claims.list`,
/// `claims.calibration` — dotted routes instead of the action-argument form.
#[must_use]
pub fn register_claims(
    registry: &wm_dispatch::ToolRegistry,
    ledger: Option<Arc<Mutex<ClaimsLedger>>>,
) -> wm_dispatch::ToolRegistry {
    let ledger = ledger.unwrap_or_else(|| Arc::new(Mutex::new(ClaimsLedger::new())));
    let mut reg = registry.register(Arc::new(ClaimsTool::new(Arc::clone(&ledger))));
    for (name, action) in CLAIMS_ALIASES {
        reg = reg.register(Arc::new(ClaimsAliasTool::new(
            name,
            action,
            Arc::clone(&ledger),
        )));
    }
    reg
}

/// Explicit single-action claims routes: `(tool_name, action)`.
const CLAIMS_ALIASES: &[(&str, &str)] = &[
    ("claims.add", "add"),
    ("claims.resolve", "resolve"),
    ("claims.status", "status"),
    ("claims.list", "list"),
    ("claims.calibration", "calibration"),
];

/// A dotted alias for one `claims` action, sharing the same ledger.
pub struct ClaimsAliasTool {
    name: &'static str,
    action: &'static str,
    inner: ClaimsTool,
}

impl ClaimsAliasTool {
    pub fn new(name: &'static str, action: &'static str, ledger: Arc<Mutex<ClaimsLedger>>) -> Self {
        Self {
            name,
            action,
            inner: ClaimsTool::new(ledger),
        }
    }
}

#[async_trait]
impl Tool for ClaimsAliasTool {
    fn name(&self) -> &str {
        self.name
    }
    fn gana(&self) -> Gana {
        self.inner.gana()
    }
    fn effects(&self) -> &EffectRow {
        self.inner.effects()
    }
    fn description(&self) -> &str {
        match self.action {
            "add" => {
                "Record a new prescience claim (statement, domain, source_date, predicted_outcome, confidence, falsification_criteria required)"
            }
            "resolve" => "Resolve a claim (claim_id, validated, event, event_date required)",
            "status" => "Prescience claims ledger summary — counts by status and points earned",
            "list" => "List claims, optionally filtered by domain or status",
            "calibration" => {
                "Claims calibration scorecard — Brier, signed calibration gap, Wilson 95% hit-rate interval, and recalibrated pending confidences"
            }
            _ => "Prescience claims ledger action",
        }
    }
    async fn call(&self, ctx: &mut Context, mut args: Value) -> wm_core::Result<Value> {
        args["action"] = Value::String(self.action.to_string());
        self.inner.call(ctx, args).await
    }
    fn stats(&self) -> &ToolStats {
        self.inner.stats()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn epoch_day_matches_unix_epoch_days() {
        // Regression: the old JDN arithmetic had a constant +1,721,451
        // offset (days since year 1, not 1970).
        assert_eq!(epoch_day_from_str("1970-01-01"), 0);
        assert_eq!(epoch_day_from_str("2026-08-05"), 20_670);
        assert_eq!(epoch_day_from_str("2025-05-26"), 20_234);
        assert_eq!(epoch_day_from_str("2026-04-23"), 20_566);
        // The canonical 332-day lead used throughout the tests.
        assert_eq!(
            epoch_day_from_str("2026-04-23") - epoch_day_from_str("2025-05-26"),
            332
        );
        // Malformed input degrades to 0, never panics.
        assert_eq!(epoch_day_from_str("garbage"), 0);
        assert_eq!(epoch_day_from_str(""), 0);
    }

    #[tokio::test]
    async fn claims_add_resolve_status_flow() {
        let ledger = Arc::new(Mutex::new(ClaimsLedger::new()));
        let tool = ClaimsTool::new(ledger);
        let mut ctx = Context::default();

        let add = tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": "Append-only side-effect audit ships in a major lab",
                    "domain": "ai_governance",
                    "source_date": "2025-05-26",
                    "predicted_outcome": "Anthropic ships an audit log",
                    "confidence": 0.8,
                    "falsification_criteria": "No major lab ships it by 2026-12-31"
                }),
            )
            .await
            .unwrap();
        assert_eq!(add["status"], "success");
        let claim_id = add["claim_id"].as_str().unwrap().to_string();

        let resolve = tool
            .call(
                &mut ctx,
                json!({
                    "action": "resolve",
                    "claim_id": claim_id,
                    "validated": true,
                    "event": "Anthropic Claude Memory audit log",
                    "event_date": "2026-04-23",
                    "source": "anthropic.com"
                }),
            )
            .await
            .unwrap();
        assert_eq!(resolve["claim_status"], "validated");
        let weeks = resolve["lead_time_weeks"].as_f64().unwrap();
        assert!((weeks - 332.0 / 7.0).abs() < 0.01, "lead {weeks}");

        let status = tool
            .call(&mut ctx, json!({"action": "status"}))
            .await
            .unwrap();
        assert_eq!(status["validated"], 1);
        assert_eq!(status["falsified"], 0);
        assert_eq!(status["total_points"].as_f64().unwrap(), 332.0 / 7.0);
    }

    #[tokio::test]
    async fn claims_add_requires_falsification_criteria() {
        let ledger = Arc::new(Mutex::new(ClaimsLedger::new()));
        let tool = ClaimsTool::new(ledger);
        let mut ctx = Context::default();
        let result = tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": "Vague claim",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "X",
                    "confidence": 0.5,
                    "falsification_criteria": ""
                }),
            )
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn claims_list_filters() {
        let ledger = Arc::new(Mutex::new(ClaimsLedger::new()));
        let tool = ClaimsTool::new(ledger);
        let mut ctx = Context::default();
        tool.call(
            &mut ctx,
            json!({
                "action": "add",
                "statement": "A",
                "domain": "energy",
                "source_date": "2026-01-01",
                "predicted_outcome": "X",
                "confidence": 0.5,
                "falsification_criteria": "not X"
            }),
        )
        .await
        .unwrap();
        let list = tool
            .call(
                &mut ctx,
                json!({"action": "list", "domain": "energy", "status": "pending"}),
            )
            .await
            .unwrap();
        assert_eq!(list["count"], 1);
        let list_all = tool
            .call(&mut ctx, json!({"action": "list"}))
            .await
            .unwrap();
        assert_eq!(list_all["count"], 1);
    }

    #[tokio::test]
    async fn claims_resolve_falsified_reports_miss() {
        let ledger = Arc::new(Mutex::new(ClaimsLedger::new()));
        let tool = ClaimsTool::new(ledger);
        let mut ctx = Context::default();
        let add = tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": "Miss",
                    "domain": "test",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "X",
                    "confidence": 0.5,
                    "falsification_criteria": "not X"
                }),
            )
            .await
            .unwrap();
        let claim_id = add["claim_id"].as_str().unwrap().to_string();
        let resolve = tool
            .call(
                &mut ctx,
                json!({
                    "action": "resolve",
                    "claim_id": claim_id,
                    "validated": false,
                    "event": "Nothing happened",
                    "event_date": "2026-07-01"
                }),
            )
            .await
            .unwrap();
        assert_eq!(resolve["claim_status"], "falsified");
        let status = tool
            .call(&mut ctx, json!({"action": "status"}))
            .await
            .unwrap();
        assert_eq!(status["falsified"], 1);
    }

    #[tokio::test]
    async fn claims_calibration_action_reports_and_recalibrates() {
        let ledger = Arc::new(Mutex::new(ClaimsLedger::new()));
        let tool = ClaimsTool::new(ledger);
        let mut ctx = Context::default();

        // One validated (0.6) and one falsified (0.4) claim — mean confidence
        // 0.5 equals the hit rate, so the ledger reads as calibrated — plus
        // one pending (0.9).
        let a = tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": "A",
                    "domain": "test",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "X",
                    "confidence": 0.6,
                    "falsification_criteria": "not X"
                }),
            )
            .await
            .unwrap();
        let a_id = a["claim_id"].as_str().unwrap().to_string();
        let b = tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": "B",
                    "domain": "test",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "Y",
                    "confidence": 0.4,
                    "falsification_criteria": "not Y"
                }),
            )
            .await
            .unwrap();
        let b_id = b["claim_id"].as_str().unwrap().to_string();
        tool.call(
            &mut ctx,
            json!({
                "action": "add",
                "statement": "C",
                "domain": "test",
                "source_date": "2026-01-01",
                "predicted_outcome": "Z",
                "confidence": 0.9,
                "falsification_criteria": "not Z"
            }),
        )
        .await
        .unwrap();
        tool.call(
            &mut ctx,
            json!({"action": "resolve", "claim_id": a_id, "validated": true, "event": "e", "event_date": "2026-01-08"}),
        )
        .await
        .unwrap();
        tool.call(
            &mut ctx,
            json!({"action": "resolve", "claim_id": b_id, "validated": false, "event": "e", "event_date": "2026-01-08"}),
        )
        .await
        .unwrap();

        let cal = tool
            .call(&mut ctx, json!({"action": "calibration"}))
            .await
            .unwrap();
        assert_eq!(cal["status"], "success");
        assert_eq!(cal["resolved"], 2);
        assert_eq!(cal["validated"], 1);
        assert_eq!(cal["falsified"], 1);
        assert_eq!(cal["interpretation"], "calibrated");
        assert_eq!(cal["pending_recalibrated"].as_array().unwrap().len(), 1);
        let pending = &cal["pending_recalibrated"][0];
        assert!((pending["confidence"].as_f64().unwrap() - 0.9).abs() < 1e-12);
        // n=2, w=2/22, hit_rate=0.5 → 0.9 + w*(0.5-0.9) < 0.9.
        let recal = pending["calibrated_confidence"].as_f64().unwrap();
        assert!(
            recal < 0.9 && recal > 0.8,
            "pending 0.9 must shrink toward 0.5 hit rate, got {recal}"
        );
    }

    #[tokio::test]
    async fn claims_alias_routes_delegate_to_actions() {
        let ledger = Arc::new(Mutex::new(ClaimsLedger::new()));
        let aliases: Vec<ClaimsAliasTool> = CLAIMS_ALIASES
            .iter()
            .map(|(name, action)| ClaimsAliasTool::new(name, action, Arc::clone(&ledger)))
            .collect();
        let names: Vec<&str> = aliases.iter().map(wm_core::Tool::name).collect();
        assert_eq!(
            names,
            vec![
                "claims.add",
                "claims.resolve",
                "claims.status",
                "claims.list",
                "claims.calibration"
            ]
        );

        // claims.calibration works without an action argument.
        let calibration = aliases
            .iter()
            .find(|t| t.name() == "claims.calibration")
            .unwrap();
        let result = calibration
            .call(&mut Context::default(), json!({}))
            .await
            .unwrap();
        assert_eq!(result["status"], "success");
        assert!(result.get("brier").is_some());

        // claims.add without an action argument records a claim.
        let add = aliases.iter().find(|t| t.name() == "claims.add").unwrap();
        let recorded = add
            .call(
                &mut Context::default(),
                json!({
                    "statement": "Alias route test claim",
                    "domain": "test",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "Y",
                    "confidence": 0.7,
                    "falsification_criteria": "not Y"
                }),
            )
            .await
            .unwrap();
        assert_eq!(recorded["status"], "success");
        assert!(recorded.get("claim_id").is_some());

        let status = aliases
            .iter()
            .find(|t| t.name() == "claims.status")
            .unwrap();
        let summary = status
            .call(&mut Context::default(), json!({}))
            .await
            .unwrap();
        assert_eq!(summary["pending"], 1);
    }
}
