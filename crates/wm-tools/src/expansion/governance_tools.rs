//! Governance tools — Hermit Crab defense and 12-Sentinel Zodiac Council.
//!
//! Tools:
//! - `hermit.status`: Get current defense posture, active mediation, and history
//! - `hermit.withdraw`: Trigger emergency memory lockdown into Withdrawn mode
//! - `hermit.mediate`: Request mediation ticket from Withdrawn state
//! - `hermit.resolve`: Approve or deny an active mediation ticket
//! - `council.deliberate`: Deliberate a proposal across the 12 Zodiac Sentinels

#![forbid(unsafe_code)]

use std::sync::{Arc, RwLock};
use async_trait::async_trait;
use serde_json::{Value, json};

use wm_cognitive::{
    CouncilProposal, ProposalCategory, ZodiacCouncil,
};
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_governance::HermitProtection;

// ── 1. hermit.status ─────────────────────────────────────────────────

pub struct HermitStatusTool {
    hermit: Arc<RwLock<HermitProtection>>,
    effects: EffectRow,
    stats: ToolStats,
}

impl HermitStatusTool {
    #[must_use]
    pub fn new(hermit: Arc<RwLock<HermitProtection>>) -> Self {
        Self {
            hermit,
            effects: EffectRow::read_only(vec![Resource::Galaxy("security".into())]),
            stats: ToolStats::default(),
        }
    }
}

#[async_trait]
impl Tool for HermitStatusTool {
    fn name(&self) -> &str {
        "hermit.status"
    }

    fn gana(&self) -> Gana {
        Gana::Room
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }

    fn description(&self) -> &str {
        "Get current hermit crab protection status, active mediation, and transition history"
    }

    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let guard = self.hermit.read().map_err(|e| {
            CoreError::Tool(format!("Failed to acquire read lock on hermit protection: {e}"))
        })?;

        let history_summary: Vec<_> = guard.history().iter().map(|h| {
            json!({
                "from": h.from.label(),
                "to": h.to.label(),
                "reason": h.reason,
                "triggered_by": h.triggered_by,
                "timestamp": h.timestamp,
            })
        }).collect();

        Ok(json!({
            "status": "success",
            "state": guard.state().label(),
            "active_seal_session": guard.active_seal_session(),
            "active_mediation": guard.active_mediation().map(|m| {
                json!({
                    "ticket_id": m.ticket_id,
                    "requested_by": m.requested_by,
                    "explanation": m.explanation,
                    "created_at": m.created_at,
                    "prior_state": m.prior_state.label(),
                })
            }),
            "history_count": guard.history().len(),
            "recent_history": history_summary,
        }))
    }
}

// ── 2. hermit.withdraw ───────────────────────────────────────────────

pub struct HermitWithdrawTool {
    hermit: Arc<RwLock<HermitProtection>>,
    effects: EffectRow,
    stats: ToolStats,
}

impl HermitWithdrawTool {
    #[must_use]
    pub fn new(hermit: Arc<RwLock<HermitProtection>>) -> Self {
        Self {
            hermit,
            effects: EffectRow {
                writes: vec![Resource::Galaxy("security".into())],
                ..Default::default()
            },
            stats: ToolStats::default(),
        }
    }
}

#[async_trait]
impl Tool for HermitWithdrawTool {
    fn name(&self) -> &str {
        "hermit.withdraw"
    }

    fn gana(&self) -> Gana {
        Gana::Room
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }

    fn description(&self) -> &str {
        "Trigger manual hermit crab withdrawal to encrypt and quarantine sensitive memories"
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let reason = args
            .get("reason")
            .and_then(Value::as_str)
            .unwrap_or("Manual operator lockdown");

        let triggered_by = args
            .get("triggered_by")
            .and_then(Value::as_str)
            .unwrap_or("operator");

        let now = chrono::Utc::now().timestamp();

        let mut guard = self.hermit.write().map_err(|e| {
            CoreError::Tool(format!("Failed to acquire write lock on hermit protection: {e}"))
        })?;

        guard.withdraw(reason, triggered_by, now);

        Ok(json!({
            "status": "success",
            "state": guard.state().label(),
            "reason": reason,
            "timestamp": now,
        }))
    }
}

// ── 3. hermit.mediate ────────────────────────────────────────────────

pub struct HermitMediateTool {
    hermit: Arc<RwLock<HermitProtection>>,
    effects: EffectRow,
    stats: ToolStats,
}

impl HermitMediateTool {
    #[must_use]
    pub fn new(hermit: Arc<RwLock<HermitProtection>>) -> Self {
        Self {
            hermit,
            effects: EffectRow {
                writes: vec![Resource::Galaxy("security".into())],
                ..Default::default()
            },
            stats: ToolStats::default(),
        }
    }
}

#[async_trait]
impl Tool for HermitMediateTool {
    fn name(&self) -> &str {
        "hermit.mediate"
    }

    fn gana(&self) -> Gana {
        Gana::Room
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }

    fn description(&self) -> &str {
        "Request mediation to unlock memory substrate from Withdrawn lockdown"
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let caller = args
            .get("caller")
            .and_then(Value::as_str)
            .unwrap_or("agent");

        let explanation = args
            .get("explanation")
            .and_then(Value::as_str)
            .unwrap_or("Requesting mediation review");

        let now = chrono::Utc::now().timestamp();

        let mut guard = self.hermit.write().map_err(|e| {
            CoreError::Tool(format!("Failed to acquire write lock on hermit protection: {e}"))
        })?;

        let (ticket_id, requested_by, exp, created_at) = match guard.request_mediation(caller, explanation, now) {
            Ok(ticket) => (
                ticket.ticket_id.clone(),
                ticket.requested_by.clone(),
                ticket.explanation.clone(),
                ticket.created_at,
            ),
            Err(err) => {
                return Ok(json!({
                    "status": "error",
                    "message": err.to_string(),
                    "current_state": guard.state().label(),
                }));
            }
        };

        Ok(json!({
            "status": "success",
            "state": guard.state().label(),
            "ticket_id": ticket_id,
            "requested_by": requested_by,
            "explanation": exp,
            "created_at": created_at,
        }))
    }
}

// ── 4. hermit.resolve ────────────────────────────────────────────────

pub struct HermitResolveTool {
    hermit: Arc<RwLock<HermitProtection>>,
    effects: EffectRow,
    stats: ToolStats,
}

impl HermitResolveTool {
    #[must_use]
    pub fn new(hermit: Arc<RwLock<HermitProtection>>) -> Self {
        Self {
            hermit,
            effects: EffectRow {
                writes: vec![Resource::Galaxy("security".into())],
                ..Default::default()
            },
            stats: ToolStats::default(),
        }
    }
}

#[async_trait]
impl Tool for HermitResolveTool {
    fn name(&self) -> &str {
        "hermit.resolve"
    }

    fn gana(&self) -> Gana {
        Gana::Room
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }

    fn description(&self) -> &str {
        "Resolve an active mediation ticket (approve or deny unlock from lockdown)"
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let ticket_id = args
            .get("ticket_id")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("Missing required 'ticket_id'".into()))?;

        let approved = args
            .get("approved")
            .and_then(Value::as_bool)
            .unwrap_or(true);

        let resolver = args
            .get("resolver")
            .and_then(Value::as_str)
            .unwrap_or("operator");

        let now = chrono::Utc::now().timestamp();

        let mut guard = self.hermit.write().map_err(|e| {
            CoreError::Tool(format!("Failed to acquire write lock on hermit protection: {e}"))
        })?;

        match guard.resolve_mediation(ticket_id, approved, resolver, now) {
            Ok(new_state) => Ok(json!({
                "status": "success",
                "state": new_state.label(),
                "approved": approved,
                "resolver": resolver,
                "timestamp": now,
            })),
            Err(err) => Ok(json!({
                "status": "error",
                "message": err.to_string(),
                "current_state": guard.state().label(),
            })),
        }
    }
}

// ── 5. council.deliberate ────────────────────────────────────────────

pub struct CouncilDeliberateTool {
    council: ZodiacCouncil,
    effects: EffectRow,
    stats: ToolStats,
}

impl Default for CouncilDeliberateTool {
    fn default() -> Self {
        Self::new()
    }
}

impl CouncilDeliberateTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            council: ZodiacCouncil::new(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("governance".into())]),
            stats: ToolStats::default(),
        }
    }
}

#[async_trait]
impl Tool for CouncilDeliberateTool {
    fn name(&self) -> &str {
        "council.deliberate"
    }

    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }

    fn description(&self) -> &str {
        "Deliberate on an architectural refactor, SEAL adaptation, or security policy proposal across the 12 Zodiac Sentinels"
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let id = args
            .get("id")
            .and_then(Value::as_str)
            .unwrap_or("prop_default")
            .to_string();

        let title = args
            .get("title")
            .and_then(Value::as_str)
            .unwrap_or("Untitled Proposal")
            .to_string();

        let description = args
            .get("description")
            .and_then(Value::as_str)
            .unwrap_or("No description provided")
            .to_string();

        let category_str = args
            .get("category")
            .and_then(Value::as_str)
            .unwrap_or("architecture");

        let category = match category_str {
            "memory" => ProposalCategory::MemoryMutation,
            "security" => ProposalCategory::SecurityPolicy,
            "adaptation" | "seal" => ProposalCategory::ModelAdaptation,
            "integration" => ProposalCategory::ExternalIntegration,
            "ecosystem" => ProposalCategory::EcosystemExpansion,
            _ => ProposalCategory::ArchitectureRefactor,
        };

        let target_subsystem = args
            .get("target_subsystem")
            .and_then(Value::as_str)
            .unwrap_or("wm-core")
            .to_string();

        let required_capabilities = args
            .get("required_capabilities")
            .and_then(Value::as_array)
            .map(|arr| {
                arr.iter()
                    .filter_map(Value::as_str)
                    .map(ToString::to_string)
                    .collect()
            })
            .unwrap_or_default();

        let risk_score = args
            .get("risk_score")
            .and_then(Value::as_f64)
            .unwrap_or(0.2)
            .clamp(0.0, 1.0);

        let complexity = args
            .get("complexity")
            .and_then(Value::as_f64)
            .unwrap_or(0.3)
            .clamp(0.0, 1.0);

        let proposal = CouncilProposal {
            id,
            title,
            description,
            category,
            target_subsystem,
            required_capabilities,
            risk_score,
            complexity,
        };

        let consensus = self.council.deliberate(&proposal);

        let verdicts_json: Vec<_> = consensus.verdicts.iter().map(|v| {
            json!({
                "sentinel": v.sentinel_name,
                "stance": format!("{:?}", v.stance),
                "confidence": v.confidence,
                "weight": v.weight,
                "hard_veto": v.hard_veto,
                "rationale": v.rationale,
                "stipulations": v.stipulations,
            })
        }).collect();

        Ok(json!({
            "status": "success",
            "proposal_id": consensus.proposal_id,
            "consensus_verdict": format!("{:?}", consensus.verdict),
            "composite_score": consensus.composite_score,
            "support_count": consensus.support_count,
            "oppose_count": consensus.oppose_count,
            "conditional_count": consensus.conditional_count,
            "abstain_count": consensus.abstain_count,
            "required_stipulations": consensus.required_stipulations,
            "consensus_digest": consensus.consensus_digest,
            "sentinel_verdicts": verdicts_json,
        }))
    }
}

/// Helper to register all governance & hermit tools into a tool registry.
#[must_use]
pub fn register_governance_tools(
    registry: &wm_dispatch::ToolRegistry,
    hermit: Arc<RwLock<HermitProtection>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(HermitStatusTool::new(hermit.clone())))
        .register(Arc::new(HermitWithdrawTool::new(hermit.clone())))
        .register(Arc::new(HermitMediateTool::new(hermit.clone())))
        .register(Arc::new(HermitResolveTool::new(hermit)))
        .register(Arc::new(CouncilDeliberateTool::new()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_hermit_lifecycle_tools() {
        let hermit = Arc::new(RwLock::new(HermitProtection::new()));
        let mut ctx = Context::default();

        let status_tool = HermitStatusTool::new(hermit.clone());
        let withdraw_tool = HermitWithdrawTool::new(hermit.clone());
        let mediate_tool = HermitMediateTool::new(hermit.clone());
        let resolve_tool = HermitResolveTool::new(hermit.clone());

        // 1. Initial status is Open
        let res = status_tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(res["status"], "success");
        assert_eq!(res["state"], "open");

        // 2. Withdraw
        let res = withdraw_tool
            .call(
                &mut ctx,
                json!({
                    "reason": "Test quarantine",
                    "triggered_by": "test_suite"
                }),
            )
            .await
            .unwrap();
        assert_eq!(res["status"], "success");
        assert_eq!(res["state"], "withdrawn");

        // 3. Status confirms Withdrawn
        let res = status_tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(res["state"], "withdrawn");

        // 4. Request mediation
        let res = mediate_tool
            .call(
                &mut ctx,
                json!({
                    "caller": "agent_worker",
                    "explanation": "Need to resume normal pipeline operations"
                }),
            )
            .await
            .unwrap();
        assert_eq!(res["status"], "success");
        assert_eq!(res["state"], "mediating");
        let ticket_id = res["ticket_id"].as_str().unwrap().to_string();

        // 5. Resolve mediation (approve)
        let res = resolve_tool
            .call(
                &mut ctx,
                json!({
                    "ticket_id": ticket_id,
                    "approved": true,
                    "resolver": "operator"
                }),
            )
            .await
            .unwrap();
        assert_eq!(res["status"], "success");
        assert_eq!(res["state"], "open");

        // 6. Status confirms Open
        let res = status_tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(res["state"], "open");
        assert_eq!(res["history_count"], 3);
    }

    #[tokio::test]
    async fn test_council_deliberate_tool() {
        let council_tool = CouncilDeliberateTool::new();
        let mut ctx = Context::default();

        let proposal = json!({
            "id": "prop_test_01",
            "title": "Add LoRa Mesh Transport",
            "description": "Integrate SX1262 LoRa physical transport into sangha mesh",
            "category": "ecosystem",
            "target_subsystem": "wm-sangha",
            "risk_score": 0.25,
            "complexity": 0.4
        });

        let res = council_tool.call(&mut ctx, proposal).await.unwrap();
        assert_eq!(res["status"], "success");
        assert_eq!(res["proposal_id"], "prop_test_01");
        assert_eq!(res["sentinel_verdicts"].as_array().unwrap().len(), 12);
        assert!(res["composite_score"].as_f64().unwrap() > 0.0);
    }
}
