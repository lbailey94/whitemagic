//! Action Skeleton & Speculative AST Streaming.
//!
//! Replaces conversational text planning with structured, unpopulated Abstract Syntax Tree
//! skeletons. Enables concurrent syntax, typing, and invariant validation in microseconds
//! before an agent generates full code blocks or conversational chatter.

use serde::{Deserialize, Serialize};
use std::time::Instant;
use uuid::Uuid;

/// Target language for an action skeleton.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SkeletonLanguage {
    Rust,
    Python,
    TypeScript,
    Toml,
    Markdown,
}

/// The mutation operation type on the target AST node.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AstActionType {
    AddImport,
    AddFunction,
    ModifySignature,
    WrapBlock,
    ReplaceSymbol,
}

/// A discrete AST modification specification within an action skeleton.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AstDelta {
    /// Scope path inside the AST hierarchy (e.g. "class:WhiteboardHandler", "fn:do_GET").
    pub scope_path: String,
    /// Name of the symbol being modified or added.
    pub target_symbol: String,
    /// Type of AST mutation.
    pub action_type: AstActionType,
    /// Any new import statements required by this mutation.
    pub new_imports: Vec<String>,
    /// The structural signature delta (e.g. "def get_rooms(self) -> dict:").
    pub signature_delta: String,
    /// Pre-condition invariants that must hold before application.
    pub pre_invariants: Vec<String>,
    /// Post-condition invariants that must hold after application.
    pub post_invariants: Vec<String>,
}

/// Classification of action reversibility (`Revisable by Design` / `SafeActBench` / `STEPGATE`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "class", rename_all = "snake_case")]
pub enum ReversibilityClass {
    /// Purely observational / read-only; zero external state mutation.
    ReadOnly,
    /// Repeated execution yields the same state as single execution (`LIMBO`).
    Idempotent,
    /// Can be undone deterministically via a compensating skeleton or snapshot (`DeltaBox`).
    Reversible { compensating_action: String },
    /// External side effects can be mitigated but not byte-identically undone.
    Compensable { mitigation_plan: String },
    /// Cannot be undone once executed (e.g., external transmission, destructive overwrite).
    Irreversible,
}

impl Default for ReversibilityClass {
    fn default() -> Self {
        Self::Reversible {
            compensating_action: "git checkout -- <target_file>".into(),
        }
    }
}

impl ReversibilityClass {
    /// Minimum required calibrated confidence before executing an action of this class (`SafeActBench`).
    #[must_use]
    pub const fn required_confidence_floor(&self) -> f64 {
        match self {
            Self::ReadOnly => 0.50,
            Self::Idempotent => 0.65,
            Self::Reversible { .. } => 0.75,
            Self::Compensable { .. } => 0.85,
            Self::Irreversible => 0.95,
        }
    }

    /// True if this action class can be automatically rolled back without human intervention.
    #[must_use]
    pub const fn is_automatically_reversible(&self) -> bool {
        matches!(
            self,
            Self::ReadOnly | Self::Idempotent | Self::Reversible { .. }
        )
    }
}

/// Per-action escalation verdict (`STEPGATE`: escalate uncertain individual actions, not entire tasks).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StepGateEscalationDecision {
    pub task_id: Uuid,
    pub target_file: String,
    pub reversibility: ReversibilityClass,
    pub observed_confidence: f64,
    pub required_floor: f64,
    pub escalate_step: bool,
    pub reason: String,
}

/// A structured action skeleton transmitted between agents.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ActionSkeleton {
    /// Unique task identifier associated with this skeleton.
    pub task_id: Uuid,
    /// Target file path relative to workspace root.
    pub target_file: String,
    /// Target programming or markup language.
    pub language: SkeletonLanguage,
    /// Ordered list of AST mutation deltas.
    pub deltas: Vec<AstDelta>,
    /// Estimated token cost if this were expanded to full conversational prose.
    pub estimated_chat_token_cost: usize,
    /// Action reversibility classification (`Revisable by Design`).
    #[serde(default)]
    pub reversibility: ReversibilityClass,
}

/// The diagnostic result of speculative AST validation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SkeletonValidationResult {
    /// Whether the skeleton is structurally valid and non-conflicting.
    pub is_valid: bool,
    /// Identified symbol or invariant conflicts.
    pub conflicts: Vec<String>,
    /// Diagnostic warnings (e.g. duplicate imports, missing pre-conditions).
    pub warnings: Vec<String>,
    /// Microseconds taken to execute speculative validation.
    pub validation_duration_micros: u64,
}

impl ActionSkeleton {
    /// Creates a new action skeleton.
    pub fn new(
        task_id: Uuid,
        target_file: impl Into<String>,
        language: SkeletonLanguage,
        deltas: Vec<AstDelta>,
    ) -> Self {
        // Roughly 150 tokens per delta if described in conversational prose
        let estimated_chat_token_cost = deltas.len() * 150 + 200;
        let target_file = target_file.into();
        let reversibility = ReversibilityClass::Reversible {
            compensating_action: format!("git checkout -- {target_file}"),
        };
        Self {
            task_id,
            target_file,
            language,
            deltas,
            estimated_chat_token_cost,
            reversibility,
        }
    }

    /// Builder helper to attach an explicit [`ReversibilityClass`].
    #[must_use]
    pub fn with_reversibility(mut self, reversibility: ReversibilityClass) -> Self {
        self.reversibility = reversibility;
        self
    }

    /// Mint an AST action skeleton for dynamically binding a hostile subnet to the Citadel cognitive tarpit (`skel-defend-tarpit`).
    #[must_use]
    pub fn defend_tarpit(task_id: Uuid, hostile_cidr: &str) -> Self {
        let clean_subnet = hostile_cidr.replace(['.', '/', ':'], "_");
        let delta = AstDelta {
            scope_path: "module:citadel_tarpit".into(),
            target_symbol: format!("throttle_{clean_subnet}"),
            action_type: AstActionType::AddFunction,
            new_imports: vec!["from citadel import ActiveDefenseTarpit".into()],
            signature_delta: format!("def throttle_{clean_subnet}(client_socket) -> None:"),
            pre_invariants: vec!["ActiveDefenseTarpit".into()],
            post_invariants: vec!["tarpit_bound = True".into()],
        };
        Self::new(
            task_id,
            "security/citadel_defense.py",
            SkeletonLanguage::Python,
            vec![delta],
        )
        .with_reversibility(ReversibilityClass::Reversible {
            compensating_action: format!("unbind_subnet('{hostile_cidr}')"),
        })
    }

    /// Mint an AST action skeleton for rate limiting an API route under heavy scan (`skel-envoy-rate-limit`).
    #[must_use]
    pub fn envoy_rate_limit(task_id: Uuid, route_pattern: &str, _rps: u32) -> Self {
        let clean_route = route_pattern.replace('/', "_").trim_start_matches('_').to_string();
        let delta = AstDelta {
            scope_path: "router:ingress_limiter".into(),
            target_symbol: format!("limit_{clean_route}"),
            action_type: AstActionType::AddFunction,
            new_imports: vec!["use wm_gen3_core::mesh::TokenBucket;".into()],
            signature_delta: format!("pub fn limit_{clean_route}(rps: u32) -> bool"),
            pre_invariants: vec!["pub fn limit_".into()],
            post_invariants: vec!["rps_enforced".into()],
        };
        Self::new(
            task_id,
            "crates/wm-gen3-core/src/mesh.rs",
            SkeletonLanguage::Rust,
            vec![delta],
        )
        .with_reversibility(ReversibilityClass::Idempotent)
    }

    /// Mint an AST action skeleton for isolating a compromised workspace into quarantine (`skel-sentinel-isolate`).
    #[must_use]
    pub fn sentinel_isolate(task_id: Uuid, workspace_path: &str) -> Self {
        let delta = AstDelta {
            scope_path: "sentinel:airlock".into(),
            target_symbol: "quarantine_workspace".into(),
            action_type: AstActionType::AddFunction,
            new_imports: vec!["from sentinel.airlock import isolate_path".into()],
            signature_delta: "def execute_quarantine(target_dir: str) -> bool:".into(),
            pre_invariants: vec!["isolate_path".into()],
            post_invariants: vec!["quarantine_locked = True".into()],
        };
        Self::new(
            task_id,
            "scripts/vps_sentinel.py",
            SkeletonLanguage::Python,
            vec![delta],
        )
        .with_reversibility(ReversibilityClass::Compensable {
            mitigation_plan: format!("restore_from_backup('{workspace_path}')"),
        })
    }

    /// Evaluate whether this individual action step must be escalated (`STEPGATE` + `SafeActBench`).
    #[must_use]
    pub fn evaluate_stepgate(&self, observed_confidence: f64) -> StepGateEscalationDecision {
        let required_floor = self.reversibility.required_confidence_floor();
        let escalate_step =
            !observed_confidence.is_finite() || observed_confidence < required_floor;
        let reason = if escalate_step {
            format!(
                "STEPGATE escalation: observed confidence ({observed_confidence:.3}) < required floor ({required_floor:.2}) for {:?}",
                self.reversibility
            )
        } else {
            format!(
                "STEPGATE admitted: observed confidence ({observed_confidence:.3}) >= required floor ({required_floor:.2})"
            )
        };
        StepGateEscalationDecision {
            task_id: self.task_id,
            target_file: self.target_file.clone(),
            reversibility: self.reversibility.clone(),
            observed_confidence,
            required_floor,
            escalate_step,
            reason,
        }
    }

    /// Speculatively validates the action skeleton against existing file contents in microseconds.
    #[must_use]
    pub fn validate_speculative(&self, existing_content: Option<&str>) -> SkeletonValidationResult {
        let start = Instant::now();
        let mut conflicts = Vec::new();
        let mut warnings = Vec::new();

        if self.deltas.is_empty() {
            warnings.push("Action skeleton has no AST deltas".into());
        }

        let existing = existing_content.unwrap_or("");

        for delta in &self.deltas {
            // 1. Basic signature check
            if delta.signature_delta.trim().is_empty()
                && delta.action_type != AstActionType::AddImport
            {
                conflicts.push(format!(
                    "Delta for symbol '{}' has empty signature",
                    delta.target_symbol
                ));
            }

            // 2. Pre-invariant verification against existing source
            for pre in &delta.pre_invariants {
                if !existing.is_empty() && !existing.contains(pre) {
                    conflicts.push(format!(
                        "Pre-invariant check failed for symbol '{}': '{}' not found in source",
                        delta.target_symbol, pre
                    ));
                }
            }

            // 3. Import duplication warnings
            for import_stmt in &delta.new_imports {
                if existing.contains(import_stmt) {
                    warnings.push(format!(
                        "Import '{}' already present in target file",
                        import_stmt
                    ));
                }
            }

            // 4. Language-specific signature heuristics
            match self.language {
                SkeletonLanguage::Python => {
                    if (delta.action_type == AstActionType::AddFunction
                        || delta.action_type == AstActionType::ModifySignature)
                        && !delta.signature_delta.contains("def ")
                        && !delta.signature_delta.contains("class ")
                    {
                        conflicts.push(format!(
                            "Python signature for '{}' must contain 'def' or 'class': '{}'",
                            delta.target_symbol, delta.signature_delta
                        ));
                    }
                }
                SkeletonLanguage::Rust
                    if (delta.action_type == AstActionType::AddFunction
                        || delta.action_type == AstActionType::ModifySignature)
                        && !delta.signature_delta.contains("fn ")
                        && !delta.signature_delta.contains("pub fn ") =>
                {
                    conflicts.push(format!(
                        "Rust signature for '{}' must contain 'fn': '{}'",
                        delta.target_symbol, delta.signature_delta
                    ));
                }
                _ => {}
            }
        }

        let is_valid = conflicts.is_empty();
        let validation_duration_micros = start.elapsed().as_micros() as u64;

        SkeletonValidationResult {
            is_valid,
            conflicts,
            warnings,
            validation_duration_micros,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_speculative_ast_validation_success() {
        let existing_source = r#"
class WhiteboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/posts":
            return self.send_json(self.get_posts())
"#;

        let delta = AstDelta {
            scope_path: "class:WhiteboardHandler".into(),
            target_symbol: "get_rooms".into(),
            action_type: AstActionType::AddFunction,
            new_imports: vec!["import re".into()],
            signature_delta: "def get_rooms(self) -> dict:".into(),
            pre_invariants: vec!["class WhiteboardHandler".into()],
            post_invariants: vec!["/api/rooms".into()],
        };

        let skeleton = ActionSkeleton::new(
            Uuid::new_v4(),
            "SharedWorkspace/bridge.py",
            SkeletonLanguage::Python,
            vec![delta],
        );

        let result = skeleton.validate_speculative(Some(existing_source));
        assert!(result.is_valid);
        assert!(result.conflicts.is_empty());
        assert!(result.validation_duration_micros < 500_000); // executed in microseconds/milliseconds under test load
    }

    #[test]
    fn test_speculative_ast_validation_conflict() {
        let existing_source = "fn main() {}";

        let delta = AstDelta {
            scope_path: "root".into(),
            target_symbol: "calculate_jev".into(),
            action_type: AstActionType::AddFunction,
            new_imports: vec![],
            signature_delta: "let x = 42;".into(), // Invalid: doesn't have 'fn'
            pre_invariants: vec!["nonexistent_anchor".into()], // Missing invariant
            post_invariants: vec![],
        };

        let skeleton = ActionSkeleton::new(
            Uuid::new_v4(),
            "crates/wm-gen3-core/src/bicameral.rs",
            SkeletonLanguage::Rust,
            vec![delta],
        );

        let result = skeleton.validate_speculative(Some(existing_source));
        assert!(!result.is_valid);
        assert_eq!(result.conflicts.len(), 2);
    }

    #[test]
    fn test_defensive_action_skeletons() {
        let task_id = Uuid::new_v4();

        // 1. Defend Tarpit
        let tarpit_skel = ActionSkeleton::defend_tarpit(task_id, "192.168.1.0/24");
        assert_eq!(tarpit_skel.language, SkeletonLanguage::Python);
        assert!(tarpit_skel.reversibility.is_automatically_reversible());
        let tarpit_valid = tarpit_skel.validate_speculative(Some("from citadel import ActiveDefenseTarpit\n"));
        assert!(tarpit_valid.is_valid);

        // 2. Envoy Rate Limit
        let envoy_skel = ActionSkeleton::envoy_rate_limit(task_id, "api/v1/auth", 100);
        assert_eq!(envoy_skel.language, SkeletonLanguage::Rust);
        assert_eq!(envoy_skel.reversibility, ReversibilityClass::Idempotent);
        let envoy_valid = envoy_skel.validate_speculative(Some("pub fn limit_init() {}\n"));
        assert!(envoy_valid.is_valid);

        // 3. Sentinel Isolate
        let isolate_skel = ActionSkeleton::sentinel_isolate(task_id, "/tmp/compromised_repo");
        assert_eq!(isolate_skel.language, SkeletonLanguage::Python);
        assert!(!isolate_skel.reversibility.is_automatically_reversible());
        let isolate_valid = isolate_skel.validate_speculative(Some("from sentinel.airlock import isolate_path\n"));
        assert!(isolate_valid.is_valid);
    }
}
