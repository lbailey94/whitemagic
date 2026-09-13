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
    assert!(
        gaps.len() <= SCHEMA_GAP_BASELINE,
        "schema coverage regressed: {} uncovered routes (baseline {}):\n  {}\n\
         Burn the baseline down; never raise it.",
        gaps.len(),
        SCHEMA_GAP_BASELINE,
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
