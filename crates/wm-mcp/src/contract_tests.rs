//! Contract tests: the promises the public surface makes to clients.
//!
//! These exist because three separate first-run findings (2026-09-13) were
//! all the same bug class — two surfaces disagreeing with each other:
//! `memory_find` vs `memory.search`, a schema saying `query` was optional
//! while the runtime required it, and README platforms vs installer
//! platforms. Each check below pins one of those agreements in place.

#![cfg(test)]

use serde_json::Value;
use std::collections::HashSet;
use std::path::PathBuf;

fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("workspace root")
}

fn full_server() -> (tempfile::TempDir, crate::McpServer) {
    let tmp = tempfile::tempdir().expect("tempdir");
    // Scope: the curated product surface. The full profile is the legacy
    // archive; its schema coverage is tracked separately, not gated here.
    let server = crate::McpServer::with_defaults_mode_profile(
        tmp.path(),
        false,
        &wm_tools::profiles::PROFILE_CURATED,
    )
    .expect("curated server builds");
    (tmp, server)
}

/// Curated routes still missing an input schema (legacy surface). This is a
/// ratchet: it may only go down. Burn it to zero; never raise it.
const SCHEMA_GAP_BASELINE: usize = 0;

#[test]
fn every_route_has_a_wellformed_unique_schema() {
    let (_tmp, server) = full_server();
    let mut seen: HashSet<String> = HashSet::new();
    let mut gaps: Vec<String> = Vec::new();
    let mut problems: Vec<String> = Vec::new();
    for tool in server.registry().all() {
        let name = tool.name().to_string();
        if name.is_empty() {
            problems.push("route with empty name".to_string());
            continue;
        }
        if !seen.insert(name.clone()) {
            problems.push(format!("duplicate route '{name}'"));
            continue;
        }

        let schema = tool.input_schema();
        if schema["type"] != "object" {
            gaps.push(name);
            continue;
        }
        let props = schema["properties"]
            .as_object()
            .cloned()
            .unwrap_or_default();
        if let Some(required) = schema["required"].as_array() {
            for r in required {
                let Some(r) = r.as_str() else {
                    problems.push(format!("route '{name}' has a non-string required entry"));
                    continue;
                };
                if !props.contains_key(r) {
                    problems.push(format!("route '{name}' requires undeclared '{r}'"));
                }
            }
        }
        if tool.description().trim().is_empty() {
            problems.push(format!("route '{name}' has an empty description"));
        }
    }
    assert!(seen.len() > 20, "curated registry suspiciously small");
    assert!(
        problems.is_empty(),
        "schema contract violations ({}):\n  {}",
        problems.len(),
        problems.join("\n  ")
    );
    // black_box keeps the ratchet a runtime comparison (clippy would fold
    // `len() <= 0` into an absurd-extreme-comparison lint at baseline 0).
    let baseline = std::hint::black_box(SCHEMA_GAP_BASELINE);
    assert!(
        gaps.len() <= baseline,
        "schema coverage regressed: {} uncovered routes (baseline {baseline}):\n  {}\n\
         Burn the baseline down; never raise it.",
        gaps.len(),
        gaps.join("\n  ")
    );
    if !gaps.is_empty() {
        eprintln!(
            "curated routes without a schema ({} / baseline {}): {}",
            gaps.len(),
            SCHEMA_GAP_BASELINE,
            gaps.join(", ")
        );
    }
}

#[test]
fn meta_required_arg_table_matches_tool_schemas() {
    let (_tmp, server) = full_server();
    let mut problems: Vec<String> = Vec::new();
    for tool in server.registry().all() {
        let name = tool.name();
        let Some(required) = wm_tools::required_arg_for(name) else {
            continue;
        };
        let schema = tool.input_schema();
        let declared = schema["required"]
            .as_array()
            .is_some_and(|arr| arr.iter().filter_map(Value::as_str).any(|s| s == required));
        if !declared {
            problems.push(format!(
                "meta table demands '{required}' for '{name}' — schema does not declare it"
            ));
        }
    }
    assert!(
        problems.is_empty(),
        "required-arg drift ({}):\n  {}",
        problems.len(),
        problems.join("\n  ")
    );
}

/// The full registry: family-scoped declaration checks below are not gated by
/// the curated schema ratchet, so they read the full profile explicitly.
fn full_registry_server() -> (tempfile::TempDir, crate::McpServer) {
    let tmp = tempfile::tempdir().expect("tempdir");
    let server = crate::McpServer::with_defaults(tmp.path()).expect("full server builds");
    (tmp, server)
}

/// Shared checker for family-scoped declaration ratchets: every route must be
/// registered with an object schema, non-empty properties, exactly the
/// expected required args, and no meta-tool pre-check may demand an arg the
/// schema omits.
fn family_schema_problems(
    registry: &wm_dispatch::ToolRegistry,
    expected: &[(&str, &[&str])],
) -> Vec<String> {
    let mut problems: Vec<String> = Vec::new();
    for (route, expected_required) in expected {
        let Some(tool) = registry.get(route) else {
            problems.push(format!("'{route}' is absent from the full registry"));
            continue;
        };
        let schema = tool.input_schema();
        if schema["type"] != "object" {
            problems.push(format!("'{route}' has no object schema"));
            continue;
        }
        if schema["properties"]
            .as_object()
            .is_none_or(serde_json::Map::is_empty)
        {
            problems.push(format!("'{route}' declares no properties"));
        }
        let mut required: Vec<&str> = schema["required"]
            .as_array()
            .map(|list| list.iter().filter_map(Value::as_str).collect())
            .unwrap_or_default();
        required.sort_unstable();
        let mut expected_required = expected_required.to_vec();
        expected_required.sort_unstable();
        if required != expected_required {
            problems.push(format!(
                "'{route}' declares required {required:?}, expected {expected_required:?}"
            ));
        }
        // The meta-tool pre-check must never demand an arg the schema omits.
        if let Some(meta) = wm_tools::required_arg_for(route) {
            if !required.contains(&meta) {
                problems.push(format!(
                    "meta table demands '{meta}' for '{route}' — schema does not declare it"
                ));
            }
        }
    }
    problems
}

/// Family-scoped declaration ratchet (`agent.*`, 2026-09-15): the agent
/// family's call bodies read these args unconditionally, so the declared
/// schemas must say so, and the meta-tool's hardcoded required-arg table must
/// agree with the schemas it pre-checks. The global full-profile coverage
/// ratchet is deliberately NOT flipped here — the remaining families
/// (galaxy.* et al.) land in later bounded batches.
#[test]
fn agent_family_schemas_match_their_calls_and_meta_table() {
    let (_tmp, server) = full_registry_server();
    // route -> required args the call body reads unconditionally.
    let expected: &[(&str, &[&str])] = &[
        ("agent.register", &["name"]),
        ("agent.list", &[]),
        ("agent.heartbeat", &[]),
        ("agent.trust", &["agent_id"]),
        ("agent.descriptions", &["agent_id"]),
        ("agent.capabilities", &["agent_id"]),
        ("agent.heartbeat.history", &["agent_id"]),
        ("agent.deregister", &["agent_id"]),
    ];
    let problems = family_schema_problems(server.registry(), expected);
    assert!(
        problems.is_empty(),
        "agent family schema drift ({}):\n  {}",
        problems.len(),
        problems.join("\n  ")
    );
}

/// Family-scoped declaration ratchet (`web.*` + `code.graph/query/affected_by`,
/// 2026-09-15): same method as the agent family — declare what the call
/// bodies read, one family per bounded batch.
#[test]
fn web_and_code_family_schemas_match_their_calls() {
    let (_tmp, server) = full_registry_server();
    let expected: &[(&str, &[&str])] = &[
        ("web.fetch", &["url"]),
        ("web.deep_fetch", &["url"]),
        ("web.search", &["query"]),
        ("web.search_and_read", &["query"]),
        ("code.graph", &["project_root"]),
        ("code.query", &["query"]),
        ("code.affected_by", &["symbol"]),
    ];
    let problems = family_schema_problems(server.registry(), expected);
    assert!(
        problems.is_empty(),
        "web/code family schema drift ({}):\n  {}",
        problems.len(),
        problems.join("\n  ")
    );
}

#[test]
fn curated_profile_tools_all_resolve() {
    let (_tmp, server) = full_server();
    let registry = server.registry();
    for name in [
        "memory.create",
        "memory.read",
        "memory.search",
        "memory.query",
        "session.start",
        "session.record",
        "session.continuity",
    ] {
        assert!(
            registry.get(name).is_some(),
            "curated contract route '{name}' missing from the registry"
        );
    }
    // Legacy spellings must resolve through the shared alias map (canonical
    // names are exposed; old agent habits keep working).
    for legacy in ["memory_find", "memory.find", "memory_search"] {
        assert_eq!(
            wm_tools::expansion::common::canonical_tool_alias(legacy),
            Some("memory.search"),
            "legacy alias '{legacy}' must resolve"
        );
    }
}

#[test]
fn docs_match_the_release_version() {
    let root = workspace_root();
    let version = env!("CARGO_PKG_VERSION");
    let readme = std::fs::read_to_string(root.join("README.md")).expect("README.md");
    assert!(
        readme.contains(&format!("# wm {version}")),
        "README verification example must show wm {version}"
    );
    let quickstart =
        std::fs::read_to_string(root.join("docs/QUICKSTART.md")).expect("QUICKSTART.md");
    assert!(
        quickstart.contains(&format!("**Version**: {version}")),
        "docs/QUICKSTART.md must carry version {version}"
    );
}

#[test]
fn platform_story_is_consistent_across_surfaces() {
    let root = workspace_root();
    let readme = std::fs::read_to_string(root.join("README.md")).expect("README.md");
    let quickstart =
        std::fs::read_to_string(root.join("docs/QUICKSTART.md")).expect("QUICKSTART.md");
    let installer = std::fs::read_to_string(root.join("scripts/install.sh")).expect("install.sh");

    assert!(
        readme.contains("Install path: Linux x86-64"),
        "README must state the Linux x86-64 install path"
    );
    assert!(
        quickstart.contains("**Install path**: Linux x86-64"),
        "QUICKSTART must state the Linux x86-64 install path"
    );
    assert!(
        installer.contains("alpha install gate covers Linux x86-64"),
        "install.sh refusal message must match the documented gate"
    );
}
