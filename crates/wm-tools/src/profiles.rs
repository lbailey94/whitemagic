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
/// Deliberately excludes: destructive galaxy operations (purge/transfer/
/// restore), the RSI friction/redteam/improve loop, sangha mesh, self-play,
/// imagination, and polyglot/cyberbrain internals — those stay reachable
/// under `--profile full`.
pub static PROFILE_CURATED: ToolProfile = ToolProfile {
    name: "curated",
    prefixes: &[
        "memory",
        "session",
        "claims",
        "transaction",
        "gnosis",
        "tools.list",
    ],
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
        "tools.list",
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
        let name = tool.name();
        if profile.prefixes.iter().any(|p| name.starts_with(p)) {
            builder.register(tool);
        }
    }
    builder.build()
}

#[cfg(test)]
mod tests {
    use super::*;

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
            &[
                "memory",
                "session",
                "claims",
                "transaction",
                "gnosis",
                "tools.list",
            ]
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
}
