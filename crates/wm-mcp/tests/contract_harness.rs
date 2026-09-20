//! 9.2.2 contract harness — registry walker (slice 1).
//!
//! Three machine checks over the live in-process registry:
//!
//! A. **Input schema well-formedness** — every tool that declares an
//!    `input_schema` must declare an object schema whose `required` fields
//!    exist and whose properties are typed.
//! B. **Client/registry schema coherence** — the lifecycle schemas served by
//!    `tools/list` must not drift from the registry tool contract: no phantom
//!    properties, matching `required` sets, agreeing property types.
//! C. **Seam declaration completeness** — every on-seam tool
//!    ([`Firebreak::is_on_seam`]) is declared in
//!    [`wm_governance::firebreak::DECLARED_SEAM_TOOLS`], and every declaration
//!    still names a live seam tool.
//!
//! Follows the `dispatch_boundary_matrix.rs` pattern (in-process registry via
//! `McpServer::with_defaults`).

use serde_json::Value;
use std::collections::BTreeSet;
use std::sync::Arc;
use wm_core::Tool;
use wm_governance::firebreak::{DECLARED_SEAM_TOOLS, Firebreak};
use wm_mcp::McpServer;

const KNOWN_SCHEMA_TYPES: &[&str] = &["string", "number", "integer", "boolean", "array", "object"];

fn registry_for_test() -> (tempfile::TempDir, McpServer) {
    let tmp = tempfile::tempdir().expect("tempdir");
    let server = McpServer::with_defaults(tmp.path()).expect("McpServer::with_defaults");
    (tmp, server)
}

fn declared_schema(tool: &Arc<dyn Tool>) -> Option<Value> {
    let schema = tool.input_schema();
    let is_empty_object = schema.as_object().is_some_and(serde_json::Map::is_empty);
    if is_empty_object { None } else { Some(schema) }
}

fn required_set(schema: &Value) -> BTreeSet<String> {
    schema
        .get("required")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default()
}

/// A. Every declared input schema is well-formed.
#[test]
fn declared_input_schemas_are_well_formed() {
    let (_tmp, server) = registry_for_test();
    let mut checked = 0usize;
    let mut failures: Vec<String> = Vec::new();

    for tool in server.registry().all_ref() {
        let Some(schema) = declared_schema(tool) else {
            continue;
        };
        checked += 1;
        let name = tool.name();

        if schema.get("type").and_then(|v| v.as_str()) != Some("object") {
            failures.push(format!("{name}: schema type must be \"object\""));
            continue;
        }
        let Some(props) = schema.get("properties").and_then(|v| v.as_object()) else {
            failures.push(format!("{name}: object schema without a properties object"));
            continue;
        };
        for (prop, spec) in props {
            if prop.trim().is_empty() {
                failures.push(format!("{name}: blank property name"));
            }
            let type_name = spec.get("type").and_then(|v| v.as_str());
            let has_enum = spec.get("enum").and_then(|v| v.as_array()).is_some();
            if type_name.is_none() && !has_enum {
                failures.push(format!(
                    "{name}: property '{prop}' declares neither type nor enum"
                ));
            }
            if let Some(t) = type_name {
                if !KNOWN_SCHEMA_TYPES.contains(&t) {
                    failures.push(format!("{name}: property '{prop}' has unknown type '{t}'"));
                }
                if t == "array" && spec.get("items").is_none() {
                    failures.push(format!("{name}: array property '{prop}' has no items"));
                }
            }
        }
        match schema.get("required") {
            None => {}
            Some(Value::Array(req)) => {
                for entry in req {
                    match entry.as_str() {
                        Some(field) if props.contains_key(field) => {}
                        Some(field) => failures.push(format!(
                            "{name}: required field '{field}' is not declared in properties"
                        )),
                        None => {
                            failures.push(format!("{name}: required contains a non-string entry"));
                        }
                    }
                }
            }
            Some(_) => failures.push(format!("{name}: required must be an array")),
        }
    }

    assert!(
        checked >= 5,
        "expected a meaningful declared-schema surface; only {checked} tools declare one"
    );
    assert!(
        failures.is_empty(),
        "input-schema contract failures ({}):\n{}",
        failures.len(),
        failures.join("\n")
    );
}

/// B. Lifecycle schemas served by `tools/list` match the registry contract.
#[test]
fn lifecycle_schemas_cohere_with_registry() {
    let rt = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .expect("tokio runtime");
    let (_tmp, mut server) = registry_for_test();

    let response = rt.block_on(async {
        let _ = server
            .handle_request(r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}"#)
            .await;
        server
            .handle_request(r#"{"jsonrpc":"2.0","id":2,"method":"tools/list"}"#)
            .await
    });
    let parsed: Value = serde_json::from_str(&response).expect("tools/list returns JSON");
    let served = parsed["result"]["tools"]
        .as_array()
        .expect("tools/list result.tools is an array");

    let mut compared = 0usize;
    let mut failures: Vec<String> = Vec::new();
    for entry in served {
        let name = entry["name"].as_str().unwrap_or_default();
        if name == "wm" {
            continue; // synthesized client schema; the passthrough contract is args
        }
        let Some(tool) = server.registry().get(name) else {
            failures.push(format!("{name}: served in tools/list but not registered"));
            continue;
        };
        compared += 1;
        let served_schema = &entry["inputSchema"];
        let registry_schema = tool.input_schema();

        let served_props = served_schema["properties"].as_object();
        let registry_props = registry_schema["properties"].as_object();
        if let Some(sp) = served_props {
            for key in sp.keys() {
                if !registry_props.is_some_and(|rp| rp.contains_key(key)) {
                    failures.push(format!(
                        "{name}: served property '{key}' is not in the registry schema"
                    ));
                }
            }
        }
        let served_required = required_set(served_schema);
        let registry_required = required_set(&registry_schema);
        if served_required != registry_required {
            failures.push(format!(
                "{name}: required drift — served {served_required:?} vs registry {registry_required:?}"
            ));
        }
        if let (Some(sp), Some(rp)) = (served_props, registry_props) {
            for (key, spec) in sp {
                if let (Some(served_type), Some(reg_type)) = (
                    spec.get("type"),
                    rp.get(key).and_then(|reg| reg.get("type")),
                ) {
                    if served_type != reg_type {
                        failures.push(format!(
                            "{name}: property '{key}' type drift — served {served_type} vs registry {reg_type}"
                        ));
                    }
                }
            }
        }
    }

    assert!(
        compared >= 8,
        "expected the discrete lifecycle catalog; compared only {compared} tools"
    );
    assert!(
        failures.is_empty(),
        "client/registry schema drift ({}):\n{}",
        failures.len(),
        failures.join("\n")
    );
}

/// C. Every on-seam tool is declared; every declaration is still live.
#[test]
fn every_on_seam_tool_is_declared() {
    let (_tmp, server) = registry_for_test();
    let declared: BTreeSet<&str> = DECLARED_SEAM_TOOLS.iter().copied().collect();

    let mut undeclared: Vec<String> = Vec::new();
    let mut live: BTreeSet<String> = BTreeSet::new();
    for tool in server.registry().all_ref() {
        if Firebreak::is_on_seam(tool.effects()) {
            live.insert(tool.name().to_string());
            if !declared.contains(tool.name()) {
                undeclared.push(tool.name().to_string());
            }
        }
    }
    undeclared.sort();
    let stale: Vec<&str> = declared
        .iter()
        .copied()
        .filter(|name| !live.contains(*name))
        .collect();

    assert!(
        undeclared.is_empty(),
        "on-seam tools missing from DECLARED_SEAM_TOOLS ({}):\n{}",
        undeclared.len(),
        undeclared.join("\n")
    );
    assert!(
        stale.is_empty(),
        "DECLARED_SEAM_TOOLS names non-seam or absent tools: {stale:?}"
    );
}
