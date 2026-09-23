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
    let declared: BTreeSet<&str> = DECLARED_SEAM_TOOLS.iter().map(|d| d.tool).collect();
    assert_eq!(
        DECLARED_SEAM_TOOLS.len(),
        declared.len(),
        "DECLARED_SEAM_TOOLS contains duplicate tool entries"
    );

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

/// D. Declared prose fields are real input-schema properties (stale/typo
/// guard). Everything not declared prose is command-bearing by construction,
/// so an exemption that no longer exists in the schema is declaration drift.
#[test]
fn declared_seam_fields_exist_in_tool_schemas() {
    let (_tmp, server) = registry_for_test();
    let mut checked = 0usize;
    let mut failures: Vec<String> = Vec::new();

    for decl in DECLARED_SEAM_TOOLS {
        if decl.prose_fields.is_empty() {
            continue;
        }
        let Some(tool) = server.registry().get(decl.tool) else {
            failures.push(format!("{}: declared but not registered", decl.tool));
            continue;
        };
        let schema = tool.input_schema();
        let props = schema.get("properties").and_then(|v| v.as_object());
        for field in decl.prose_fields {
            checked += 1;
            if !props.is_some_and(|p| p.contains_key(*field)) {
                failures.push(format!(
                    "{}: prose field '{field}' is not an input-schema property",
                    decl.tool
                ));
            }
        }
    }

    assert!(
        checked >= 1,
        "expected at least one declared prose field to check; found none"
    );
    assert!(
        failures.is_empty(),
        "seam field declaration drift ({}):\n{}",
        failures.len(),
        failures.join("\n")
    );
}

/// E. Declared bounds, enums, and required-lists are internally coherent
/// (the schema-only half of "one input contract per tool"; parser-agreement
/// at boundary values remains the next iteration).
#[test]
fn declared_schema_bounds_and_enums_are_coherent() {
    let (_tmp, server) = registry_for_test();
    let mut checked = 0usize;
    let mut failures: Vec<String> = Vec::new();

    for tool in server.registry().all_ref() {
        let Some(schema) = declared_schema(tool) else {
            continue;
        };
        let name = tool.name();
        let Some(props) = schema.get("properties").and_then(|v| v.as_object()) else {
            continue;
        };
        for (prop, spec) in props {
            let type_name = spec.get("type").and_then(|v| v.as_str());
            let min = spec.get("minimum").and_then(serde_json::Value::as_f64);
            let max = spec.get("maximum").and_then(serde_json::Value::as_f64);

            if let Some(lo) = min {
                checked += 1;
                if !lo.is_finite() {
                    failures.push(format!("{name}.{prop}: minimum is not finite"));
                }
            }
            if let Some(hi) = max {
                checked += 1;
                if !hi.is_finite() {
                    failures.push(format!("{name}.{prop}: maximum is not finite"));
                }
            }
            if let (Some(lo), Some(hi)) = (min, max) {
                if lo > hi {
                    failures.push(format!("{name}.{prop}: minimum {lo} > maximum {hi}"));
                }
            }
            if type_name == Some("integer") {
                if let Some(lo) = min {
                    if lo.fract() != 0.0 {
                        failures.push(format!("{name}.{prop}: integer minimum {lo} is fractional"));
                    }
                }
                if let Some(hi) = max {
                    if hi.fract() != 0.0 {
                        failures.push(format!("{name}.{prop}: integer maximum {hi} is fractional"));
                    }
                }
            }

            if let Some(values) = spec.get("enum").and_then(|v| v.as_array()) {
                checked += 1;
                if values.is_empty() {
                    failures.push(format!("{name}.{prop}: empty enum"));
                }
                let mut seen = BTreeSet::new();
                for value in values {
                    if !seen.insert(value.to_string()) {
                        failures.push(format!("{name}.{prop}: duplicate enum value {value}"));
                    }
                    let type_matches = match type_name {
                        Some("string") => value.is_string(),
                        Some("number" | "integer") => value.is_number(),
                        Some("boolean") => value.is_boolean(),
                        _ => true,
                    };
                    if !type_matches {
                        failures.push(format!(
                            "{name}.{prop}: enum value {value} does not match type {type_name:?}"
                        ));
                    }
                }
            }
        }

        if let Some(required) = schema.get("required").and_then(|v| v.as_array()) {
            let mut seen = BTreeSet::new();
            for entry in required {
                if let Some(field) = entry.as_str() {
                    if !seen.insert(field) {
                        failures.push(format!("{name}: duplicate required field '{field}'"));
                    }
                }
            }
        }
    }

    assert!(
        checked >= 5,
        "expected bound/enum declarations to check; found only {checked}"
    );
    assert!(
        failures.is_empty(),
        "schema bound/enum incoherence ({}):\n{}",
        failures.len(),
        failures.join("\n")
    );
}

/// F. Command-bearing seam fields are actually veto-scanned (the complement
/// of the prose exemption): for every on-seam tool, a forbidden pattern in
/// any non-prose property must block, while the same payload in a declared
/// prose field must not. This keeps `prose_fields` from hiding a command
/// field behind a prose label.
#[test]
fn command_bearing_seam_fields_are_veto_scanned() {
    use serde_json::json;
    use wm_governance::firebreak::{
        FirebreakOutcome, SCOPE_REGISTRY, ScopeRule, SeamToolDeclaration,
    };

    let (_tmp, server) = registry_for_test();
    let firebreak = Firebreak::with_armed(true);

    let mut checked = 0usize;
    let mut failures: Vec<String> = Vec::new();

    for tool in server.registry().all_ref() {
        let effects = tool.effects();
        if !Firebreak::is_on_seam(effects) {
            continue;
        }
        let name = tool.name();
        let schema = tool.input_schema();
        let Some(props) = schema.get("properties").and_then(|v| v.as_object()) else {
            continue;
        };
        let prose = SeamToolDeclaration::prose_fields_for(name);

        // Satisfy the bulk-scope law so the only block under test is the
        // pattern veto (destructive tools with named scope fields).
        let scope_fill = if effects.destructive {
            match SCOPE_REGISTRY
                .iter()
                .find(|(n, _)| *n == name)
                .map(|(_, rule)| rule)
            {
                Some(ScopeRule::ArgFields(fields)) => fields.first().copied(),
                _ => None,
            }
        } else {
            None
        };

        for prop in props.keys() {
            let mut args = serde_json::Map::new();
            if let Some(field) = scope_fill {
                args.insert(field.to_string(), json!("scope-under-test"));
            }
            args.insert(prop.clone(), json!("rm -rf /"));
            let outcome = firebreak.enforce(name, effects, &Value::Object(args));
            if prose.contains(&prop.as_str()) {
                if let FirebreakOutcome::Blocked(reason) = &outcome {
                    failures.push(format!(
                        "{name}.{prop}: declared prose field blocked a forbidden-quoting \
                         payload: {reason}"
                    ));
                }
            } else {
                checked += 1;
                match &outcome {
                    FirebreakOutcome::Blocked(reason) if reason.contains("FORBIDDEN") => {}
                    FirebreakOutcome::Blocked(reason) => failures.push(format!(
                        "{name}.{prop}: expected a FORBIDDEN veto, got another block: {reason}"
                    )),
                    FirebreakOutcome::Proceed { .. } => failures.push(format!(
                        "{name}.{prop}: forbidden pattern not vetoed — command-bearing field is \
                         not scanned"
                    )),
                }
            }
        }
    }

    assert!(
        checked >= 5,
        "expected command-bearing seam fields to check; found only {checked}"
    );
    assert!(
        failures.is_empty(),
        "seam scan coverage failures ({}):\n{}",
        failures.len(),
        failures.join("\n")
    );
}
