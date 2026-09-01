//! Tool surface profiles — curated release surfaces for the tool registry.
//!
//! 229 tools is an archive, not a v1 product. Profiles curate which tools the
//! `wm` meta-tool can route to (and which are registered at the boundary) so
//! `wm serve --profile curated` presents the differentiated surface — the
//! learned memory hierarchy — instead of everything.
//!
//! The full registry is always built first (internal subsystems like the
//! karma ledger, friction logging and the governance pipeline need their
//! tools regardless), then filtered before the meta-tools are layered on.

#![forbid(unsafe_code)]

use wm_dispatch::{ToolRegistry, ToolRegistryBuilder};

/// A named tool surface. `prefixes` are tool-name prefixes; a tool matches
/// if its name starts with any prefix. `["*"]` means no filtering.
#[derive(Debug, Clone, Copy)]
pub struct ToolProfile {
    /// Profile name (`full`, `curated`, `minimal`, or `allowlist`).
    pub name: &'static str,
    /// Matching prefixes, or `["*"]` for the full surface.
    pub prefixes: &'static [&'static str],
}

/// The full surface — every tool registered. Library/daemon default.
pub static PROFILE_FULL: ToolProfile = ToolProfile {
    name: "full",
    prefixes: &["*"],
};

/// The memory-hierarchy product surface: memory, sessions, transactions,
/// the claims ledger, and read-only galaxy/observability helpers.
///
/// `tools.list` and `gnosis` need no prefix here: `tools.list` is layered
/// on with the meta-tools *after* filtering, and `gnosis` matches its own
/// base tool. (The contract check flags a stale `tools.list` prefix as a
/// dead route — that is how it was found, 2026-08-29.)
///
/// Deliberately excludes: destructive galaxy operations (purge/transfer/
/// restore), the RSI friction/redteam/improve loop, sangha mesh, self-play,
/// imagination, and polyglot/cyberbrain internals — those stay reachable
/// under `--profile full`.
pub static PROFILE_CURATED: ToolProfile = ToolProfile {
    name: "curated",
    prefixes: &["memory", "session", "claims", "transaction", "gnosis"],
};

/// The tightest surface: create/read/list/query/search/chat + discovery.
pub static PROFILE_MINIMAL: ToolProfile = ToolProfile {
    name: "minimal",
    prefixes: &[
        "memory.create",
        "memory.read",
        "memory.list",
        "memory.query",
        "memory.search",
        "memory.chat",
        "memory.associate",
        "memory.associations",
        "gnosis",
    ],
};

/// Look up a profile by name (`full`, `curated`, `minimal`).
#[must_use]
pub fn profile_from_name(name: &str) -> Option<&'static ToolProfile> {
    match name.trim().to_ascii_lowercase().as_str() {
        "full" => Some(&PROFILE_FULL),
        "curated" => Some(&PROFILE_CURATED),
        "minimal" => Some(&PROFILE_MINIMAL),
        _ => None,
    }
}

/// Resolve the active tool profile with explicit precedence:
///
/// 1. `WM_TOOL_ALLOWLIST` — an explicit prefix allowlist always wins.
/// 2. CLI `--profile` flag.
/// 3. `WM_TOOL_PROFILE` environment variable.
/// 4. Default: `full` (library / `wm daemon`). `wm serve` overlays
///    curated when flag and env are both absent.
///
/// Unknown profile names log a warning and fall back to the full surface.
#[must_use]
pub fn resolve_tool_profile(
    cli_profile: Option<&str>,
    env_profile: Option<&str>,
    env_allowlist: Option<&str>,
) -> &'static ToolProfile {
    if let Some(allow) = env_allowlist {
        if let Some(profile) = allowlist_from_env(allow) {
            tracing::info!(
                allowlist = %allow,
                "WM_TOOL_ALLOWLIST tool surface in effect"
            );
            return Box::leak(Box::new(profile));
        }
    }
    match cli_profile.or(env_profile) {
        Some(name) => profile_from_name(name).unwrap_or_else(|| {
            tracing::warn!(
                profile = name,
                "unknown tool surface profile — using full tool surface"
            );
            &PROFILE_FULL
        }),
        None => &PROFILE_FULL,
    }
}

/// Build a profile from a comma-separated allowlist of tool-name prefixes
/// (e.g. `memory,session,claims`). Empty segments are ignored.
#[must_use]
pub fn allowlist_from_env(spec: &str) -> Option<ToolProfile> {
    let prefixes: Vec<&'static str> = spec
        .split(',')
        .map(str::trim)
        .filter(|p| !p.is_empty())
        .collect::<Vec<_>>()
        .into_iter()
        .map(|p| Box::leak(p.to_string().into_boxed_str()) as &'static str)
        .collect();
    if prefixes.is_empty() {
        return None;
    }
    Some(ToolProfile {
        name: "allowlist",
        prefixes: Box::leak(prefixes.into_boxed_slice()),
    })
}

/// Filter a registry to a profile. `["*"]` profiles pass the registry
/// through untouched (zero-copy — the registry is Arc-backed).
#[must_use]
pub fn apply_profile(registry: ToolRegistry, profile: &ToolProfile) -> ToolRegistry {
    if profile.prefixes.contains(&"*") {
        return registry;
    }
    let mut builder = ToolRegistryBuilder::new();
    for tool in registry.all() {
        if matches_prefixes(tool.name(), profile.prefixes) {
            builder.register(tool);
        }
    }
    builder.build()
}

/// Whether a tool name matches any of a profile's prefixes.
#[must_use]
pub fn matches_prefixes(name: &str, prefixes: &[&str]) -> bool {
    prefixes.iter().any(|p| name.starts_with(p))
}

/// The profile contract — proof that the advertised surface is the
/// declared surface.
///
/// Computed at server startup from the pre-filter ("full") registry and
/// the post-filter (registered) registry. `ok == false` means surface
/// drift: the boundary is advertising or routing something the declared
/// profile does not cover, or declares prefixes that match nothing (the
/// dead-route class the curated `galaxy.list` regression came from).
/// Persisted as `profile_contract.json` in the store root so `wm doctor`
/// can grade the last server start against it.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProfileContract {
    /// Declared profile name (`full`, `curated`, `minimal`, `allowlist`).
    pub profile: String,
    /// Declared prefixes (`["*"]` for full).
    pub prefixes: Vec<String>,
    /// Tools the declared profile should register.
    pub expected_count: usize,
    /// Tools actually registered post-filter.
    pub registered_count: usize,
    /// Declared prefixes matching zero tools (dead routes).
    pub dead_prefixes: Vec<String>,
    /// Registered tools the declared profile does not cover (drift).
    pub unexpected_tools: Vec<String>,
    /// Destructive tools on the registered surface. Informational —
    /// destructive effects are confirm-gated in the dispatch pipeline;
    /// curated deliberately includes `memory.delete` and friends.
    pub destructive_tools: Vec<String>,
    /// RFC 3339 timestamp of the check (`wm_core::time`).
    pub verified_at: String,
    /// `true` iff the registered surface is exactly the declared one.
    pub ok: bool,
}

/// Compute the profile contract for a server start.
#[must_use]
pub fn profile_contract(
    full: &ToolRegistry,
    filtered: &ToolRegistry,
    profile: &ToolProfile,
) -> ProfileContract {
    let full_names: Vec<&str> = full.all_ref().iter().map(|t| t.name()).collect();
    let registered: Vec<&str> = filtered.all_ref().iter().map(|t| t.name()).collect();

    let star = profile.prefixes.contains(&"*");
    let matches = |name: &str| star || profile.prefixes.iter().any(|p| name.starts_with(p));
    let expected_count = full_names.iter().filter(|n| matches(n)).count();
    let unexpected_tools: Vec<String> = registered
        .iter()
        .filter(|n| !matches(n))
        .map(|n| (*n).to_string())
        .collect();
    let dead_prefixes: Vec<String> = profile
        .prefixes
        .iter()
        .filter(|p| **p != "*" && !full_names.iter().any(|n| n.starts_with(**p)))
        .map(|p| (*p).to_string())
        .collect();
    let destructive_tools: Vec<String> = filtered
        .all_ref()
        .iter()
        .filter(|t| t.effects().destructive)
        .map(|t| t.name().to_string())
        .collect();

    let ok = expected_count == registered.len()
        && unexpected_tools.is_empty()
        && dead_prefixes.is_empty();

    ProfileContract {
        profile: profile.name.to_string(),
        prefixes: profile.prefixes.iter().map(|p| (*p).to_string()).collect(),
        expected_count,
        registered_count: registered.len(),
        dead_prefixes,
        unexpected_tools,
        destructive_tools,
        verified_at: wm_core::time::now_rfc3339(),
        ok,
    }
}

/// Persist the contract to `<store-root>/profile_contract.json` (atomic
/// rename, same discipline as the other root state files). Best-effort:
/// a persistence failure warns and never blocks the server start.
pub fn save_contract(root: &std::path::Path, contract: &ProfileContract) {
    let path = root.join("profile_contract.json");
    let tmp = root.join(".profile_contract.json.tmp");
    let write = serde_json::to_string_pretty(contract)
        .map(|body| std::fs::write(&tmp, body).and_then(|()| std::fs::rename(&tmp, &path)));
    if let Err(e) = write {
        tracing::warn!(
            path = %path.display(),
            error = %e,
            "could not persist profile contract"
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use wm_core::Tool;

    #[test]
    fn profile_names_resolve() {
        assert_eq!(profile_from_name("full").map(|p| p.name), Some("full"));
        assert_eq!(
            profile_from_name("CURATED").map(|p| p.name),
            Some("curated")
        );
        assert_eq!(
            profile_from_name("minimal").map(|p| p.name),
            Some("minimal")
        );
        assert!(profile_from_name("bogus").is_none());
    }

    #[test]
    fn curated_has_no_dead_routes() {
        // Regression: the curated profile once contained a `galaxy.list`
        // prefix that matched no registered tool.
        assert!(
            !PROFILE_CURATED
                .prefixes
                .iter()
                .any(|p| p.starts_with("galaxy")),
            "curated profile must not include galaxy prefixes"
        );
    }

    #[test]
    fn curated_is_the_product_surface() {
        assert_eq!(
            PROFILE_CURATED.prefixes,
            &["memory", "session", "claims", "transaction", "gnosis"]
        );
        assert!(
            !PROFILE_CURATED
                .prefixes
                .iter()
                .any(|p| *p == "nlu.shadow_report" || *p == "tools.usage_report"),
            "observability tools belong on the full surface"
        );
    }

    #[test]
    fn allowlist_parses_and_rejects_empty() {
        assert!(allowlist_from_env("").is_none());
        assert!(allowlist_from_env(" , ").is_none());
        let profile = allowlist_from_env("memory, claims , session").unwrap();
        assert_eq!(profile.name, "allowlist");
        assert_eq!(profile.prefixes, &["memory", "claims", "session"]);
    }

    #[test]
    fn full_profile_is_passthrough() {
        let registry = ToolRegistry::new();
        let out = apply_profile(registry, &PROFILE_FULL);
        assert_eq!(out.len(), 0);
    }

    #[test]
    fn resolve_profile_precedence() {
        // CLI flag wins over the environment variable.
        assert_eq!(
            resolve_tool_profile(Some("curated"), Some("minimal"), None).name,
            "curated"
        );
        // Environment is used when the CLI flag is absent.
        assert_eq!(
            resolve_tool_profile(None, Some("minimal"), None).name,
            "minimal"
        );
        // An explicit allowlist wins over both.
        let resolved =
            resolve_tool_profile(Some("curated"), Some("minimal"), Some("memory,session"));
        assert_eq!(resolved.name, "allowlist");
        assert_eq!(resolved.prefixes, &["memory", "session"]);
        // All absent → full surface.
        assert_eq!(resolve_tool_profile(None, None, None).name, "full");
        // Unknown names fall back to full.
        assert_eq!(resolve_tool_profile(Some("bogus"), None, None).name, "full");
        assert_eq!(resolve_tool_profile(None, Some("bogus"), None).name, "full");
    }

    struct ContractMock {
        name: String,
        effects: wm_core::EffectRow,
        stats: wm_core::ToolStats,
    }

    #[async_trait::async_trait]
    impl wm_core::Tool for ContractMock {
        fn name(&self) -> &str {
            &self.name
        }
        fn gana(&self) -> wm_core::Gana {
            wm_core::Gana::Horn
        }
        fn effects(&self) -> &wm_core::EffectRow {
            &self.effects
        }
        fn stats(&self) -> &wm_core::ToolStats {
            &self.stats
        }
        async fn call(
            &self,
            _ctx: &mut wm_core::Context,
            _args: wm_core::Args,
        ) -> wm_core::Result<wm_core::Output> {
            Ok(serde_json::json!({"ok": true}))
        }
    }

    fn contract_tool(name: &str, destructive: bool) -> Arc<dyn Tool> {
        let effects = if destructive {
            wm_core::EffectRow {
                destructive: true,
                ..wm_core::EffectRow::default()
            }
        } else {
            wm_core::EffectRow::default()
        };
        Arc::new(ContractMock {
            name: name.into(),
            effects,
            stats: wm_core::ToolStats::default(),
        })
    }

    fn contract_registry(tools: &[Arc<dyn Tool>]) -> ToolRegistry {
        let mut builder = ToolRegistryBuilder::new();
        for tool in tools {
            builder.register(Arc::clone(tool));
        }
        builder.build()
    }

    /// Build a registry covering every `PROFILE_MINIMAL` prefix so the
    /// dead-prefix check has nothing to flag.
    fn minimal_registry(tools: &[Arc<dyn Tool>]) -> ToolRegistry {
        let prefix_tools: Vec<Arc<dyn Tool>> = [
            "memory.create",
            "memory.read",
            "memory.list",
            "memory.query",
            "memory.search",
            "memory.chat",
            "memory.associate",
            "memory.associations",
            "gnosis",
        ]
        .iter()
        .map(|n| contract_tool(n, false) as Arc<dyn Tool>)
        .collect();
        let mut all = prefix_tools;
        all.extend(tools.iter().cloned());
        contract_registry(&all)
    }

    #[test]
    fn contract_ok_when_surface_is_exact() {
        let full = minimal_registry(&[]);
        let filtered = contract_registry(&full.all());
        let c = profile_contract(&full, &filtered, &PROFILE_MINIMAL);
        assert!(c.ok);
        assert_eq!(c.expected_count, 9);
        assert_eq!(c.registered_count, 9);
        assert!(c.dead_prefixes.is_empty());
        assert!(c.unexpected_tools.is_empty());
    }

    #[test]
    fn contract_detects_dead_prefixes_and_unexpected_tools() {
        let alpha = contract_tool("alpha.one", false);
        let sneaky = contract_tool("sneaky.tool", false);
        let full = contract_registry(std::slice::from_ref(&alpha));
        // Post-filter registry carries a tool the profile does not declare.
        let filtered = contract_registry(&[alpha, sneaky]);
        let c = profile_contract(
            &full,
            &filtered,
            &allowlist_from_env("alpha,gamma").unwrap(),
        );
        assert!(!c.ok);
        assert_eq!(c.dead_prefixes, vec!["gamma".to_string()]);
        assert_eq!(c.unexpected_tools, vec!["sneaky.tool".to_string()]);
        assert_eq!(c.expected_count, 1);
        assert_eq!(c.registered_count, 2);
    }

    #[test]
    fn contract_reports_destructive_tools_informationally() {
        let full = minimal_registry(&[]);
        let filtered = contract_registry(&full.all());
        let c = profile_contract(&full, &filtered, &PROFILE_MINIMAL);
        assert!(
            c.ok,
            "destructive presence is informational, not a violation"
        );
        assert!(c.destructive_tools.is_empty());

        // Curated-style surface, computed through the real filter path:
        // memory.delete rides the `memory` prefix by design — it must be
        // listed, and must not fail the contract; galaxy.purge must not.
        let curated_tools: Vec<Arc<dyn Tool>> = [
            "memory.create",
            "session.start",
            "claims.list",
            "transaction.begin",
            "gnosis",
            "tools.list",
            "memory.delete",
            "galaxy.purge",
        ]
        .iter()
        .map(|n| contract_tool(n, *n == "memory.delete" || *n == "galaxy.purge") as Arc<dyn Tool>)
        .collect();
        let full2 = contract_registry(&curated_tools);
        let filtered2 = apply_profile(full2.clone(), &PROFILE_CURATED);
        let c2 = profile_contract(&full2, &filtered2, &PROFILE_CURATED);
        assert_eq!(c2.destructive_tools, vec!["memory.delete".to_string()]);
        assert!(c2.ok);
        assert_eq!(c2.expected_count, 6);
        assert_eq!(c2.registered_count, 6);
    }

    #[test]
    fn full_profile_contract_counts_everything() {
        let tools: Vec<Arc<dyn Tool>> = vec![
            contract_tool("memory.create", false),
            contract_tool("galaxy.purge", true),
        ];
        let full = contract_registry(&tools);
        let filtered = contract_registry(&full.all().iter().map(Arc::clone).collect::<Vec<_>>());
        let c = profile_contract(&full, &filtered, &PROFILE_FULL);
        assert!(c.ok);
        assert_eq!(c.expected_count, 2);
        assert_eq!(c.registered_count, 2);
        assert!(c.dead_prefixes.is_empty());
    }
}
