//! Dharma tools — rules, audit, profiles.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;

pub struct DharmaRulesTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl DharmaRulesTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for DharmaRulesTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for DharmaRulesTool {
    fn name(&self) -> &str {
        "dharma.rules"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List active dharma rules and governance policies"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        Ok(json!({
            "status": "success",
            "rules": [
                { "name": "brain_wave_filter", "description": "Tools filtered by brain-wave state" },
                { "name": "coherence_gate", "description": "Writes blocked when citta coherence < 0.3" },
                { "name": "dharma_eval", "description": "Ethical governance verdict on every dispatch" },
                { "name": "rate_limit", "description": "Sliding window per-tool + global rate limiting" },
                { "name": "circuit_breaker", "description": "Fast-fail on repeated tool failures" },
            ],
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `dharma.audit` — audit recent dispatches for governance violations.
pub struct DharmaAuditTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DharmaAuditTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("dharma".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for DharmaAuditTool {
    fn name(&self) -> &str {
        "dharma.audit"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Audit recent dispatches for governance violations"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;
        let memories = self.store.scan(Galaxy::Dharma, limit)?;
        let audits: Vec<Value> = memories
            .iter()
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "content": m.content,
                    "importance": m.metadata.importance,
                })
            })
            .collect();
        Ok(json!({
            "status": "success",
            "audited": audits.len(),
            "entries": audits,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `dharma.acs` — Microsoft Agent Control Specification (ACS) compliance
/// surface: per-checkpoint coverage report, policy export/import as
/// standard policy YAML. Mirrors the OWASP coverage surface.
pub struct DharmaAcsTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl DharmaAcsTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for DharmaAcsTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Tool for DharmaAcsTool {
    fn name(&self) -> &str {
        "dharma.acs"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "ACS compliance (actions: report, export, import, egress). report: per-checkpoint coverage table (input/llm/state/tool_execution/output); export: current dharma policy as ACS policy YAML; import: parse ACS policy YAML into dharma rules; egress: check a host against tier2_deny_unknown_egress."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        use wm_governance::acs::AcsExport;
        let action = args
            .get("action")
            .and_then(Value::as_str)
            .unwrap_or("report");
        let policy = wm_governance::DharmaPolicy::default();
        match action {
            "report" => {
                let report = policy.acs_report();
                Ok(json!({
                    "status": "success",
                    "total_checkpoints": report.total_checkpoints,
                    "covered_count": report.covered_count,
                    "coverage_percent": report.coverage_percent(),
                    "covered": report.covered,
                    "missing": report.missing,
                    "policy_version": report.policy_version,
                }))
            }
            "export" => Ok(json!({
                "status": "success",
                "format": "acs-policy-yaml",
                "yaml": policy.to_acs_yaml(),
            })),
            "import" => {
                #[cfg(feature = "acs-yaml")]
                {
                    let yaml = args.get("yaml").and_then(Value::as_str).ok_or_else(|| {
                        wm_core::CoreError::InvalidArgs("yaml is required for import".into())
                    })?;
                    let summary = wm_governance::acs::import_acs_yaml(yaml)
                        .map_err(wm_core::CoreError::Tool)?;
                    Ok(json!({
                        "status": "success",
                        "summary": summary,
                    }))
                }
                #[cfg(not(feature = "acs-yaml"))]
                {
                    let _ = args;
                    Err(wm_core::CoreError::Tool(
                        "acs-yaml feature disabled — build with --features wm-tools/acs-yaml"
                            .into(),
                    ))
                }
            }
            "egress" => {
                let host = args.get("host").and_then(Value::as_str).unwrap_or("");
                let denied = policy.check_egress(host);
                Ok(json!({
                    "status": "success",
                    "action": "egress",
                    "tier2_deny_unknown_egress": policy.tier2_deny_unknown_egress,
                    "egress_allowlist": policy.egress_allowlist,
                    "tier3_output_validation": policy.tier3_output_validation,
                    "output_max_bytes": policy.output_max_bytes,
                    "host": host,
                    "allowed": denied.is_none(),
                    "reason": denied,
                }))
            }
            other => Err(wm_core::CoreError::InvalidArgs(format!(
                "unknown dharma.acs action: {other}"
            ))),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
#[allow(clippy::items_after_test_module)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn acs_report_lists_five_checkpoints() {
        let tool = DharmaAcsTool::new();
        let mut ctx = Context::default();
        let result = tool
            .call(&mut ctx, json!({"action": "report"}))
            .await
            .unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_checkpoints"], 5);
        assert!(result["coverage_percent"].as_f64().unwrap() >= 0.0);
        assert!(!result["covered"].as_array().unwrap().is_empty());
        assert!(result["missing"].is_array());
    }

    #[tokio::test]
    async fn acs_report_is_default_action() {
        let tool = DharmaAcsTool::new();
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["total_checkpoints"], 5);
    }

    #[tokio::test]
    async fn acs_export_returns_yaml_or_disabled_notice() {
        let tool = DharmaAcsTool::new();
        let mut ctx = Context::default();
        let result = tool
            .call(&mut ctx, json!({"action": "export"}))
            .await
            .unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["format"], "acs-policy-yaml");
        let yaml = result["yaml"].as_str().unwrap();
        #[cfg(feature = "acs-yaml")]
        assert!(yaml.contains("checkpoint"));
        #[cfg(not(feature = "acs-yaml"))]
        assert!(yaml.contains("acs-yaml feature disabled"));
    }

    #[cfg(feature = "acs-yaml")]
    #[tokio::test]
    async fn acs_import_parses_yaml_rules() {
        let tool = DharmaAcsTool::new();
        let mut ctx = Context::default();
        let yaml = r#"
- id: egress_block
  checkpoint: tool_execution
  action: block
  condition: "effect == network_write"
"#;
        let result = tool
            .call(&mut ctx, json!({"action": "import", "yaml": yaml}))
            .await
            .unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["summary"]["imported_rules"], 1);
        assert_eq!(result["summary"]["blocking_rules"], 1);
    }

    #[cfg(not(feature = "acs-yaml"))]
    #[tokio::test]
    async fn acs_import_errors_without_feature() {
        let tool = DharmaAcsTool::new();
        let mut ctx = Context::default();
        let result = tool
            .call(
                &mut ctx,
                json!({"action": "import", "yaml": "- id: x\n  checkpoint: input\n  action: allow\n  condition: \"true\"\n"}),
            )
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn acs_unknown_action_errors() {
        let tool = DharmaAcsTool::new();
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({"action": "bogus"})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn acs_egress_reports_policy_and_checks_host() {
        let tool = DharmaAcsTool::new();
        let mut ctx = Context::default();
        let result = tool
            .call(
                &mut ctx,
                json!({"action": "egress", "host": "api.example.com"}),
            )
            .await
            .unwrap();
        assert_eq!(result["action"], "egress");
        assert!(result["allowed"].is_boolean());
        assert!(result["tier2_deny_unknown_egress"].is_boolean());
        // Default policy: deny_unknown_egress is off → every host allowed.
        assert_eq!(result["allowed"], true);
    }

    #[tokio::test]
    async fn acs_egress_strict_policy_denies_unknown_hosts() {
        use wm_governance::policy::DharmaPolicy;
        let policy = DharmaPolicy::strict();
        assert!(policy.tier2_deny_unknown_egress);
        assert!(policy.check_egress("unknown-host.io").is_some());
        // Subdomain of an allowlisted domain passes once allowlisted.
        let mut with_allow = DharmaPolicy::strict();
        with_allow.egress_allowlist = vec!["api.whitemagic.dev".into()];
        assert!(with_allow.check_egress("api.whitemagic.dev").is_none());
        assert!(with_allow.check_egress("sub.api.whitemagic.dev").is_none());
        assert!(with_allow.check_egress("evil.com").is_some());
    }
}

// ── Dharma escalation (v26 `dharma.escalate` / `review_queue` / `resolve_review`) ──

/// `dharma.escalate` — run the escalation pipeline on an action and queue
/// ambiguous verdicts for human review.
pub struct DharmaEscalateTool {
    gate: Arc<wm_governance::DharmaGate>,
    queue: Arc<std::sync::Mutex<wm_governance::EscalationQueue>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DharmaEscalateTool {
    pub fn new(
        gate: Arc<wm_governance::DharmaGate>,
        queue: Arc<std::sync::Mutex<wm_governance::EscalationQueue>>,
    ) -> Self {
        Self {
            gate,
            queue,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
impl Tool for DharmaEscalateTool {
    fn name(&self) -> &str {
        "dharma.escalate"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Evaluate an action against the Dharma gate and escalate ambiguous verdicts to the human review queue. Args: tool (required), action (description), purpose (optional)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let tool = args
            .get("tool")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("tool is required".into()))?;
        let action = args.get("action").and_then(Value::as_str).unwrap_or(tool);
        let purpose = args.get("purpose").and_then(Value::as_str).unwrap_or("");

        // Policy tier: evaluate the declared effects (if any) with the gate.
        let effects = args
            .get("effects")
            .and_then(Value::as_str)
            .map(|e| match e {
                "write" => EffectRow {
                    writes: vec![Resource::Galaxy("unknown".into())],
                    ..Default::default()
                },
                "network" => EffectRow::read_only(vec![Resource::Network]),
                "destructive" => EffectRow {
                    writes: vec![Resource::Galaxy("unknown".into())],
                    destructive: true,
                    ..Default::default()
                },
                _ => EffectRow::pure(),
            })
            .unwrap_or_default();
        let verdict = self.gate.evaluate(&effects, &Context::default());

        // Heuristic tier: an ambiguous verdict (warn ladder) or a missing
        // purpose on an unknown action escalates to human review.
        let ambiguous = matches!(
            verdict,
            wm_governance::ActionVerdict::Advise(_) | wm_governance::ActionVerdict::Correct(_)
        );
        let escalate = ambiguous || (purpose.is_empty() && !effects.writes.is_empty());

        let mut result = json!({
            "status": "success",
            "tool": tool,
            "action": action,
            "verdict": format!("{verdict:?}"),
            "blocks": verdict.blocks(),
            "escalated": escalate,
        });
        if escalate {
            let mut queue = self
                .queue
                .lock()
                .map_err(|e| wm_core::CoreError::Tool(format!("escalation queue lock: {e}")))?;
            let item = queue.escalate(
                tool,
                action,
                &format!("{verdict:?}"),
                if ambiguous {
                    "ambiguous policy verdict — human review requested"
                } else {
                    "action without declared purpose"
                },
            );
            result["review_id"] = json!(item.id);
            result["queue_status"] = queue.status();
        }
        Ok(result)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `dharma.review_queue` — list pending human review items.
pub struct DharmaReviewQueueTool {
    queue: Arc<std::sync::Mutex<wm_governance::EscalationQueue>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DharmaReviewQueueTool {
    pub fn new(queue: Arc<std::sync::Mutex<wm_governance::EscalationQueue>>) -> Self {
        Self {
            queue,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("dharma".into())]),
        }
    }
}

#[async_trait]
impl Tool for DharmaReviewQueueTool {
    fn name(&self) -> &str {
        "dharma.review_queue"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List pending human review items from the escalation pipeline"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let include_resolved = args
            .get("include_resolved")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let queue = self
            .queue
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("escalation queue lock: {e}")))?;
        let pending = queue.pending();
        let reviews: Vec<Value> = if include_resolved {
            queue.all().iter().map(review_json).collect()
        } else {
            pending.iter().map(review_json).collect()
        };
        Ok(json!({
            "status": "success",
            "pending_count": pending.len(),
            "total_count": queue.items.len(),
            "reviews": reviews,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

fn review_json(item: &wm_governance::ReviewItem) -> Value {
    json!({
        "id": item.id,
        "tool": item.tool,
        "action": item.action,
        "verdict": item.verdict,
        "reason": item.reason,
        "created_at": item.created_at,
        "status": item.status.as_str(),
        "decision": item.decision,
        "score": item.score,
    })
}

/// `dharma.resolve_review` — resolve a human review item.
pub struct DharmaResolveReviewTool {
    queue: Arc<std::sync::Mutex<wm_governance::EscalationQueue>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl DharmaResolveReviewTool {
    pub fn new(queue: Arc<std::sync::Mutex<wm_governance::EscalationQueue>>) -> Self {
        Self {
            queue,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("dharma".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for DharmaResolveReviewTool {
    fn name(&self) -> &str {
        "dharma.resolve_review"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Resolve a human review item from the escalation pipeline. Args: review_id (required), decision (allow|warn|block, default warn), score (0.0-1.0, default 0.5)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let review_id = args
            .get("review_id")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("review_id is required".into()))?;
        let decision = args
            .get("decision")
            .and_then(Value::as_str)
            .unwrap_or("warn");
        let score = args.get("score").and_then(Value::as_f64).unwrap_or(0.5);
        let mut queue = self
            .queue
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("escalation queue lock: {e}")))?;
        let resolved = queue
            .resolve(review_id, decision, score)
            .map_err(wm_core::CoreError::Tool)?;
        Ok(json!({
            "status": "success",
            "review_id": resolved.id,
            "decision": resolved.decision,
            "score": resolved.score,
            "message": format!("Review {} resolved as {decision}", resolved.id),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}
