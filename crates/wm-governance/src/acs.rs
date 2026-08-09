//! ACS bridge — Microsoft Agent Control Specification (ACS) interoperability.
//!
//! Maps WhiteMagic's governance model onto the ACS five-checkpoint model
//! (Input / LLM / State / Tool execution / Output) with policy YAML
//! import/export. ACS (announced at Microsoft Build 2026-06-02) is the
//! industry specification for deterministic safety controls in agentic
//! workflows — "the MCP or A2A of agent safety."
//!
//! This module provides:
//!
//! - **Import**: parse ACS policy YAML into [`AcsRule`]s, convertible to
//!   v5 [`PolicyRule`]s so ACS-compliant policies run on v5 unchanged
//! - **Export**: render a [`DharmaPolicy`] as ACS policy YAML so
//!   v5-deployed governance is inspectable by ACS tooling
//! - **Report**: per-checkpoint coverage table, mirroring the existing
//!   OWASP coverage surface
//!
//! The YAML surface is feature-gated behind `acs-yaml`; the checkpoint and
//! action models are always available.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
#[cfg(feature = "acs-yaml")]
use serde_json::{Value, json};

use crate::policy::{DharmaPolicy, OwaspAgentic, PolicyRule};

/// ACS validation checkpoints.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AcsCheckpoint {
    /// Before the agent consumes external data.
    Input,
    /// Around model inference.
    Llm,
    /// Memory and context integrity.
    State,
    /// Before/after tool calls.
    ToolExecution,
    /// Before results leave the agent.
    Output,
}

impl AcsCheckpoint {
    /// All checkpoints in canonical order.
    #[must_use]
    pub const fn all() -> [Self; 5] {
        [
            Self::Input,
            Self::Llm,
            Self::State,
            Self::ToolExecution,
            Self::Output,
        ]
    }

    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Input => "input",
            Self::Llm => "llm",
            Self::State => "state",
            Self::ToolExecution => "tool_execution",
            Self::Output => "output",
        }
    }
}

/// ACS policy actions — the severity ladder.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AcsAction {
    /// Allow unconditionally.
    Allow,
    /// Allow, record to the audit log.
    Log,
    /// Allow, record a warning.
    Warn,
    /// Allow with throttled rate.
    Throttle,
    /// Deny the action.
    Block,
}

impl AcsAction {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Allow => "allow",
            Self::Log => "log",
            Self::Warn => "warn",
            Self::Throttle => "throttle",
            Self::Block => "block",
        }
    }

    /// Whether this action denies the operation.
    #[must_use]
    pub const fn blocks(self) -> bool {
        matches!(self, Self::Block)
    }
}

/// A single ACS rule as expressed in policy YAML.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AcsRule {
    /// Unique rule identifier.
    pub id: String,
    /// Which checkpoint this rule guards.
    pub checkpoint: AcsCheckpoint,
    /// Action to take when the condition matches.
    pub action: AcsAction,
    /// Policy condition (free-form expression, e.g. "effect == network_write && scope != trusted").
    pub condition: String,
    /// Optional scope (agent / tool / galaxy compartment).
    pub scope: Option<String>,
}

impl AcsRule {
    /// Convert to a v5 [`PolicyRule`].
    ///
    /// Checkpoint and action map onto the sutra/OWASP model:
    /// blocking rules surface as Ahimsa (non-harm) enforcement,
    /// logging/warning rules as Satya (truth) transparency.
    #[must_use]
    pub fn to_dharma_rule(&self) -> PolicyRule {
        let (sutra, owasp) = match self.checkpoint {
            AcsCheckpoint::Input => ("Satya", OwaspAgentic::PromptInjection),
            AcsCheckpoint::Llm => ("Satya", OwaspAgentic::Misinformation),
            AcsCheckpoint::State => ("Ahimsa", OwaspAgentic::DataModelPoisoning),
            AcsCheckpoint::ToolExecution => ("Ahimsa", OwaspAgentic::ExcessiveAgency),
            AcsCheckpoint::Output => ("Ahimsa", OwaspAgentic::ImproperOutputHandling),
        };
        PolicyRule {
            id: format!("acs_{}", self.id),
            description: format!(
                "ACS rule {} at checkpoint {}: {}",
                self.id,
                self.checkpoint.as_str(),
                self.condition
            ),
            enabled: true,
            owasp_mappings: vec![owasp],
            sutra: sutra.to_string(),
        }
    }
}

/// Per-checkpoint coverage report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AcsComplianceReport {
    /// Total checkpoints (5).
    pub total_checkpoints: usize,
    /// Checkpoints with at least one matching policy rule.
    pub covered_count: usize,
    /// Covered checkpoints.
    pub covered: Vec<String>,
    /// Checkpoints with no explicit rule.
    pub missing: Vec<String>,
    /// Policy version reported.
    pub policy_version: String,
}

impl AcsComplianceReport {
    /// Coverage percentage.
    #[must_use]
    pub fn coverage_percent(&self) -> f32 {
        if self.total_checkpoints == 0 {
            0.0
        } else {
            self.covered_count as f32 / self.total_checkpoints as f32 * 100.0
        }
    }
}

/// Inference of the checkpoint a policy rule most plausibly guards, from its
/// sutra and OWASP mappings (first mapping decides).
fn checkpoint_for_rule(rule: &PolicyRule) -> AcsCheckpoint {
    if let Some(&o) = rule.owasp_mappings.first() {
        match o {
            OwaspAgentic::PromptInjection
            | OwaspAgentic::SystemPromptLeakage
            | OwaspAgentic::SensitiveInfoDisclosure => return AcsCheckpoint::Input,
            OwaspAgentic::Misinformation | OwaspAgentic::UnboundedConsumption => {
                return AcsCheckpoint::Llm;
            }
            OwaspAgentic::DataModelPoisoning | OwaspAgentic::VectorEmbeddingWeaknesses => {
                return AcsCheckpoint::State;
            }
            OwaspAgentic::ExcessiveAgency | OwaspAgentic::SupplyChain => {
                return AcsCheckpoint::ToolExecution;
            }
            OwaspAgentic::ImproperOutputHandling => return AcsCheckpoint::Output,
        }
    }
    AcsCheckpoint::ToolExecution
}

/// ACS export surface for a Dharma policy.
pub trait AcsExport {
    /// Render the policy as ACS policy YAML.
    #[must_use]
    fn to_acs_yaml(&self) -> String;
    /// Per-checkpoint coverage report.
    #[must_use]
    fn acs_report(&self) -> AcsComplianceReport;
}

impl AcsExport for DharmaPolicy {
    fn to_acs_yaml(&self) -> String {
        let mut rules = Vec::new();
        for rule in self.enabled_rules() {
            let checkpoint = checkpoint_for_rule(rule);
            let action = if rule.sutra == "Ahimsa" {
                AcsAction::Block
            } else {
                AcsAction::Warn
            };
            rules.push(AcsRule {
                id: rule.id.clone(),
                checkpoint,
                action,
                condition: format!("sutra == {:?}", rule.sutra),
                scope: Some("galaxy".to_string()),
            });
        }
        #[cfg(feature = "acs-yaml")]
        {
            serde_yaml::to_string(&rules).unwrap_or_else(|_| "[]\n".to_string())
        }
        #[cfg(not(feature = "acs-yaml"))]
        {
            let _ = rules;
            "# acs-yaml feature disabled — enable with --features acs-yaml\n".to_string()
        }
    }

    fn acs_report(&self) -> AcsComplianceReport {
        let all = AcsCheckpoint::all();
        let rules = self.enabled_rules();
        let mut covered: Vec<String> = Vec::new();
        for checkpoint in all {
            if rules.iter().any(|r| checkpoint_for_rule(r) == checkpoint) {
                covered.push(checkpoint.as_str().to_string());
            }
        }
        let missing: Vec<String> = all
            .iter()
            .map(|c| c.as_str().to_string())
            .filter(|c| !covered.contains(c))
            .collect();
        AcsComplianceReport {
            total_checkpoints: all.len(),
            covered_count: covered.len(),
            covered,
            missing,
            policy_version: "5.6.0".to_string(),
        }
    }
}

/// Import ACS policy YAML into v5 [`PolicyRule`]s.
///
/// Requires the `acs-yaml` feature. Returns the rules converted for the
/// Dharma policy, plus a coverage summary.
#[cfg(feature = "acs-yaml")]
pub fn import_acs_yaml(yaml: &str) -> Result<Value, String> {
    let rules: Vec<AcsRule> = serde_yaml::from_str(yaml).map_err(|e| e.to_string())?;
    let dharma_rules: Vec<PolicyRule> = rules.iter().map(AcsRule::to_dharma_rule).collect();
    Ok(json!({
        "status": "success",
        "imported_rules": rules.len(),
        "checkpoints": {
            "input": rules.iter().filter(|r| r.checkpoint == AcsCheckpoint::Input).count(),
            "llm": rules.iter().filter(|r| r.checkpoint == AcsCheckpoint::Llm).count(),
            "state": rules.iter().filter(|r| r.checkpoint == AcsCheckpoint::State).count(),
            "tool_execution": rules.iter().filter(|r| r.checkpoint == AcsCheckpoint::ToolExecution).count(),
            "output": rules.iter().filter(|r| r.checkpoint == AcsCheckpoint::Output).count(),
        },
        "blocking_rules": rules.iter().filter(|r| r.action.blocks()).count(),
        "rules": dharma_rules,
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_policy() -> DharmaPolicy {
        let mut policy = DharmaPolicy::default();
        policy.custom_rules.push(PolicyRule {
            id: "acs_import_test".to_string(),
            description: "Block untrusted network egress".to_string(),
            enabled: true,
            owasp_mappings: vec![OwaspAgentic::ExcessiveAgency],
            sutra: "Ahimsa".to_string(),
        });
        policy
    }

    #[test]
    fn checkpoint_ladder_matches_dharma_verdicts() {
        // ACS block == Dharma Intervene/Panic (blocking); warn == Advise/Correct.
        assert!(AcsAction::Block.blocks());
        assert!(!AcsAction::Warn.blocks());
        assert_eq!(AcsCheckpoint::all().len(), 5);
        assert_eq!(AcsCheckpoint::ToolExecution.as_str(), "tool_execution");
    }

    #[test]
    fn acs_rule_converts_to_dharma_rule() {
        let rule = AcsRule {
            id: "egress_block".to_string(),
            checkpoint: AcsCheckpoint::ToolExecution,
            action: AcsAction::Block,
            condition: "effect == network_write && scope != trusted".to_string(),
            scope: Some("production".to_string()),
        };
        let dharma = rule.to_dharma_rule();
        assert_eq!(dharma.id, "acs_egress_block");
        assert_eq!(dharma.sutra, "Ahimsa");
        assert!(
            dharma
                .owasp_mappings
                .contains(&OwaspAgentic::ExcessiveAgency)
        );
        assert!(dharma.enabled);
    }

    #[test]
    fn report_covers_checkpoints_from_rules() {
        let policy = sample_policy();
        let report = policy.acs_report();
        assert_eq!(report.total_checkpoints, 5);
        assert!(report.covered_count >= 1);
        assert!(report.covered.contains(&"tool_execution".to_string()));
        assert!(report.coverage_percent() > 0.0);
    }

    #[test]
    fn export_yaml_with_feature() {
        let policy = sample_policy();
        let yaml = policy.to_acs_yaml();
        #[cfg(feature = "acs-yaml")]
        {
            assert!(yaml.contains("tool_execution") || yaml.contains("acs_import_test"));
        }
        #[cfg(not(feature = "acs-yaml"))]
        {
            assert!(yaml.contains("acs-yaml feature disabled"));
        }
    }

    #[cfg(feature = "acs-yaml")]
    #[test]
    fn import_yaml_roundtrip() {
        let policy = sample_policy();
        let yaml = policy.to_acs_yaml();
        let imported = import_acs_yaml(&yaml).unwrap();
        assert_eq!(imported["status"], "success");
        assert!(imported["imported_rules"].as_u64().unwrap() >= 1);
    }
}
