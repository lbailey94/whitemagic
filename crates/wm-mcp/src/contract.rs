//! `wm contract` — machine-checked route/schema contract catalog (P1 v0).
//!
//! Deferred from 9.1.6 (see `V9_1_7_FULL_PROFILE_CONTRACT_BACKLOG.md`): the
//! 297-route catalog needs a deterministic, versioned manifest of each
//! route's declared input schema so discovery cannot disagree with runtime
//! argument checks. v0 emits the manifest from ONE exact source revision
//! (the running binary's registry) and checks a curated list of
//! unconditionally-read arguments that must be declared. The full static
//! classification (unconditional / action / state / optional) and the
//! family-scoped remediation queue remain the bounded backlog method.

use serde_json::{Value, json};
use wm_dispatch::ToolRegistry;

/// Arguments read unconditionally by `call` that MUST appear in the declared
/// schema. Grows one family-scoped commit at a time — never a bulk rewrite.
pub const KNOWN_UNCONDITIONAL_READS: &[(&str, &str)] = &[("kg.query", "entity")];

/// The declared contract of one tool, normalized for the manifest.
#[must_use]
pub fn tool_contract(tool: &dyn wm_core::Tool) -> Value {
    let schema = tool.input_schema();
    let properties = schema
        .get("properties")
        .cloned()
        .unwrap_or_else(|| json!({}));
    let required: Vec<String> = schema
        .get("required")
        .and_then(Value::as_array)
        .map(|list| {
            list.iter()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default();
    let declared = properties
        .as_object()
        .is_some_and(|props| !props.is_empty());
    json!({
        "route": tool.name(),
        "declared": declared,
        "required": required,
        "properties": properties,
    })
}

/// Build the deterministic manifest for a registry (sorted by route name).
#[must_use]
pub fn build_manifest(registry: &ToolRegistry, version: &str) -> Value {
    let mut tools: Vec<Value> = registry
        .all_ref()
        .iter()
        .map(|tool| tool_contract(tool.as_ref()))
        .collect();
    tools.sort_by(|a, b| a["route"].as_str().cmp(&b["route"].as_str()));
    let declared = tools
        .iter()
        .filter(|t| t["declared"].as_bool().unwrap_or(false))
        .count();
    json!({
        "kind": "whitemagic-route-schema-manifest",
        "format_version": 1,
        "generated_by": "wm contract --json",
        "version": version,
        "source": "running binary registry (one exact revision)",
        "counts": {
            "routes": tools.len(),
            "declared": declared,
            "undeclared": tools.len() - declared,
        },
        "known_unconditional_reads": KNOWN_UNCONDITIONAL_READS
            .iter()
            .map(|(route, arg)| json!({"route": route, "arg": arg}))
            .collect::<Vec<_>>(),
        "tools": tools,
    })
}

/// Check the curated unconditional-read list against the manifest.
///
/// Returns human-readable violations (empty = contract holds for the
/// checked set).
#[must_use]
pub fn check_known_unconditional_reads(manifest: &Value) -> Vec<String> {
    let mut violations = Vec::new();
    let empty = Vec::new();
    let tools = manifest["tools"].as_array().unwrap_or(&empty);
    for (route, arg) in KNOWN_UNCONDITIONAL_READS {
        let Some(tool) = tools.iter().find(|t| t["route"].as_str() == Some(route)) else {
            // The CLI builds the FULL registry, so a missing route means the
            // contract was renamed or removed — that is a violation, not a
            // silent pass (2026-09-15 review).
            violations.push(format!(
                "{route} is absent from the manifest (renamed or removed?)"
            ));
            continue;
        };
        let required = tool["required"]
            .as_array()
            .is_some_and(|list| list.iter().any(|v| v.as_str() == Some(arg)));
        if !required {
            violations.push(format!(
                "{route} reads '{arg}' unconditionally but does not declare it as required"
            ));
        }
    }
    violations
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn manifest_declares_kg_query_entity() {
        let tmp = tempfile::tempdir().unwrap();
        let lmdb = tmp.path().join("lmdb");
        let server = crate::McpServer::with_defaults(&lmdb).unwrap();
        let manifest = build_manifest(server.registry(), "test");
        assert!(
            manifest["counts"]["routes"].as_u64().unwrap_or(0) > 100,
            "full registry manifest: {manifest}"
        );
        let kg = manifest["tools"]
            .as_array()
            .unwrap()
            .iter()
            .find(|t| t["route"] == "kg.query")
            .expect("kg.query is registered");
        assert_eq!(kg["required"], json!(["entity"]));
        assert!(
            kg["properties"]["entity"].is_object(),
            "entity property described: {kg}"
        );
        assert!(check_known_unconditional_reads(&manifest).is_empty());
    }

    #[test]
    fn check_reports_a_missing_declaration() {
        let manifest = json!({
            "tools": [
                {"route": "kg.query", "declared": true, "required": [], "properties": {"entity": {}}}
            ]
        });
        let violations = check_known_unconditional_reads(&manifest);
        assert_eq!(violations.len(), 1);
        assert!(violations[0].contains("kg.query"));
        assert!(violations[0].contains("entity"));
    }
}
