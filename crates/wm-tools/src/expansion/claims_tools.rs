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

/// Epoch day for a date string "YYYY-MM-DD" (approximate, for tool input).
fn epoch_day_from_str(date: &str) -> i64 {
    let parts: Vec<&str> = date.split('-').collect();
    if parts.len() != 3 {
        return 0;
    }
    let y: i64 = parts[0].parse().unwrap_or(1970);
    let m: i64 = parts[1].parse().unwrap_or(1);
    let d: i64 = parts[2].parse().unwrap_or(1);
    // Days since 1970-01-01 (proleptic Gregorian).
    let (y, m) = if m <= 2 { (y - 1, m + 12) } else { (y, m) };
    let a = y / 100;
    let b = 2 - a + a / 4;
    (365 * (y + 4716) + (y + 4716) / 4 - b + (153 * (m + 1)) / 5 + d - 1524) - 719_163
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
        "Prescience claims ledger (actions: add, resolve, status, list). add requires statement, domain, source_date (YYYY-MM-DD), predicted_outcome, confidence, falsification_criteria. resolve requires claim_id, validated (bool), event, event_date (YYYY-MM-DD)."
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

/// Register the claims tool against the ledger.
#[must_use]
pub fn register_claims(
    registry: &wm_dispatch::ToolRegistry,
    ledger: Option<Arc<Mutex<ClaimsLedger>>>,
) -> wm_dispatch::ToolRegistry {
    let tool = match ledger {
        Some(ledger) => ClaimsTool::new(ledger),
        None => ClaimsTool::default(),
    };
    registry.register(Arc::new(tool))
}

#[cfg(test)]
mod tests {
    use super::*;

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
}
