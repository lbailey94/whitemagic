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
        Self {
            task_id,
            target_file: target_file.into(),
            language,
            deltas,
            estimated_chat_token_cost,
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
                    if delta.action_type == AstActionType::AddFunction
                        || delta.action_type == AstActionType::ModifySignature
                    {
                        if !delta.signature_delta.contains("def ")
                            && !delta.signature_delta.contains("class ")
                        {
                            conflicts.push(format!(
                                "Python signature for '{}' must contain 'def' or 'class': '{}'",
                                delta.target_symbol, delta.signature_delta
                            ));
                        }
                    }
                }
                SkeletonLanguage::Rust => {
                    if delta.action_type == AstActionType::AddFunction
                        || delta.action_type == AstActionType::ModifySignature
                    {
                        if !delta.signature_delta.contains("fn ")
                            && !delta.signature_delta.contains("pub fn ")
                        {
                            conflicts.push(format!(
                                "Rust signature for '{}' must contain 'fn': '{}'",
                                delta.target_symbol, delta.signature_delta
                            ));
                        }
                    }
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
}
