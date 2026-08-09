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
        "ACS compliance (actions: report, export, import). report: per-checkpoint coverage table (input/llm/state/tool_execution/output); export: current dharma policy as ACS policy YAML; import: parse ACS policy YAML into dharma rules."
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
}
