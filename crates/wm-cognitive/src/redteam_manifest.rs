//! Redteam manifest — dynamic attack surface tracking.
//!
//! Reads a TOML manifest file (`redteam_manifest.toml`) that declares all
//! crates and their attack surfaces. The redteam cycle uses this to generate
//! proposals for untested attack surfaces dynamically, without requiring
//! manual catalog expansion.
//!
//! See `docs/REDTEAM_STRATEGY.md` Section 3 for the architecture proposal.

use crate::RedteamProposal;
use std::path::Path;

// ── Test Coverage Checker (D3) ────────────────────────────────────────

/// Check whether a crate's source directory contains test functions
/// related to a given attack surface name.
///
/// This is a lightweight heuristic that scans source files for `#[test]`
/// attributes and function names containing the surface name. It avoids
/// the cost of running `cargo test --no-run`.
///
/// Returns `true` if at least one test function name contains the surface
/// name as a substring.
#[must_use]
pub fn has_test_coverage(crate_src_dir: &Path, surface_name: &str) -> bool {
    let Ok(entries) = std::fs::read_dir(crate_src_dir) else {
        return false;
    };

    let surface_lower = surface_name.to_lowercase();

    for entry in entries.flatten() {
        let path = entry.path();
        if let Some(ext) = path.extension() {
            if ext != "rs" {
                continue;
            }
        } else {
            continue;
        }

        let Ok(contents) = std::fs::read_to_string(&path) else {
            continue;
        };

        // Must have a test module
        if !contents.contains("#[cfg(test)]") {
            continue;
        }

        // Check if the file name matches the surface name
        let file_name = path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("")
            .to_lowercase();

        if file_name == surface_lower || file_name.contains(&surface_lower) {
            // File is named after the surface and has tests — covered
            return true;
        }

        // Also check for test function names containing the surface name
        for line in contents.lines() {
            let trimmed = line.trim();
            if trimmed.starts_with("fn ")
                && trimmed.contains(&surface_lower)
                && (trimmed.contains("test")
                    || trimmed.contains("_doesnt_")
                    || trimmed.contains("_rejects_")
                    || trimmed.contains("_accepts_")
                    || trimmed.contains("_handles_")
                    || trimmed.contains("_clamped_")
                    || trimmed.contains("_safe_")
                    || trimmed.contains("_enforced_"))
            {
                return true;
            }
        }
    }

    false
}

/// Update manifest entries with actual test coverage by scanning source files.
///
/// For each attack surface, checks if the crate's source directory contains
/// test functions matching the surface name. Updates the `tested` field
/// accordingly.
#[must_use]
pub fn enrich_with_coverage(mut manifest: ManifestFile) -> ManifestFile {
    let workspace_dir = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent() // crates/
        .and_then(|p| p.parent()); // workspace root

    for crate_entry in &mut manifest.crates {
        let crate_src = match workspace_dir {
            Some(ws) => ws.join("crates").join(&crate_entry.name).join("src"),
            None => continue,
        };

        for surface in &mut crate_entry.attack_surfaces {
            if has_test_coverage(&crate_src, &surface.name) {
                surface.tested = true;
            }
        }
    }

    manifest
}

// ── Manifest Types ────────────────────────────────────────────────────

/// Root manifest file.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ManifestFile {
    /// Manifest format version
    pub manifest: ManifestMeta,
    /// Crates with attack surfaces
    pub crates: Vec<CrateEntry>,
}

/// Manifest metadata.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ManifestMeta {
    /// Format version
    pub version: u32,
    /// Human-readable description
    pub description: String,
}

/// A crate entry in the manifest.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CrateEntry {
    /// Crate name (e.g., "wm-core")
    pub name: String,
    /// Attack surfaces for this crate
    pub attack_surfaces: Vec<AttackSurface>,
}

/// An attack surface declaration.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AttackSurface {
    /// Module or file name (e.g., "security", "store")
    pub name: String,
    /// Attack kind (e.g., "ssrf", "path_traversal", "query_injection")
    pub kind: String,
    /// Whether this surface has test coverage
    pub tested: bool,
}

// ── Manifest Reader ───────────────────────────────────────────────────

/// Read and parse the redteam manifest from a TOML file.
///
/// Returns `None` if the file doesn't exist or fails to parse.
/// This is intentional — the manifest is optional, and the redteam cycle
/// falls back to the static catalog when no manifest is present.
#[must_use]
pub fn read_manifest(path: &Path) -> Option<ManifestFile> {
    let contents = std::fs::read_to_string(path).ok()?;
    toml::from_str(&contents).ok()
}

/// Read the default manifest bundled with the crate.
///
/// Looks for `redteam_manifest.toml` in the crate's source directory.
/// In production, this path is set at compile time via `env!("CARGO_MANIFEST_DIR")`.
#[must_use]
pub fn read_default_manifest() -> Option<ManifestFile> {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("redteam_manifest.toml");
    read_manifest(&path)
}

// ── Dynamic Vector Generation ─────────────────────────────────────────

/// Template for generating attack vector descriptions from manifest entries.
fn attack_vector_template(kind: &str) -> &'static str {
    match kind {
        "ssrf" => "SSRF via attacker-controlled endpoint URL",
        "path_traversal" => "Path traversal via crafted input",
        "query_injection" => "Query injection via special syntax characters",
        "map_size_exhaustion" => "Resource exhaustion via unbounded writes",
        "env_var_validation" => "Malformed environment variable causes panic or traversal",
        "metric_poisoning" => "Metric poisoning via out-of-bounds values",
        "routing_manipulation" => "Routing manipulation via crafted input text",
        "subprocess_injection" => "Subprocess injection via path manipulation",
        "ffi_path_traversal" => "FFI library path traversal",
        "ffi_oversized_args" => "FFI oversized arguments causing memory exhaustion",
        "ffi_oversized_result" => "FFI oversized result causing memory exhaustion",
        "ffi_null_pointer" => "FFI null pointer dereference",
        "prompt_padding" => "Prompt padding to force cloud tier escalation",
        "endpoint_injection" => "Endpoint injection via environment variable",
        "unwrap_panic" => "unwrap() panic on unexpected state",
        "large_window_panic" => "Panic from arithmetic overflow on large config",
        "bypass_via_name_change" => "Rate limiter bypass via rapid name changes",
        "circular_thinking" => "Circular thinking loop not detected",
        "redteam_self_circular" => "Redteam cycle itself becomes circular",
        "ahimsa_bypass" => "Policy update bypasses Ahimsa (non-harm) constraints",
        "false_effects" => "Tool declares false effects (Satya violation)",
        "destructive_in_strict_mode" => "Destructive tool allowed in strict Ahimsa mode",
        "cycle_poisoning" => "Circular links to inflate importance",
        "low_trust_injection" => "Memory poisoning via high-trust source injection",
        "bus_spam_cascade" => "Bus spam causing cascade amplification",
        "tier_priority_inversion" => "Hook on wrong tier causing priority inversion",
        "per_peer_dos" => "Resource lock DoS via greedy peer",
        "outlier_poisoning" => "Forecast manipulation via poisoned historical data",
        "prefix_route_bypass" => "Prefix route bypass via keyword embedding",
        "hmac_forgery" => "HMAC signature forgery on tool attestation",
        "invalid_galaxy_name" => "Invalid galaxy name causes panic or data corruption",
        "weight_manipulation" => "Recall weight manipulation via env vars",
        "unbounded_generation" => "Unbounded dream generation causing resource exhaustion",
        "vector_manipulation" => "Harmony vector manipulation via poisoned metrics",
        "duplicate_registration" => "Duplicate tool registration causing shadowing",
        "malformed_jsonrpc" => "Malformed JSON-RPC causing panic or hang",
        "rule_injection" => "Reflex rule injection via crafted input",
        "unauthorized_access" => "Unauthorized workspace access",
        "drive_manipulation" => "Drive manipulation via crafted events",
        "signal_poisoning" => "Salience signal poisoning via crafted tokens",
        "message_injection" => "Sangha chat message injection",
        "parameter_injection" => "Counterfactual parameter injection",
        _ => "Unknown attack vector",
    }
}

/// Generate a test pseudocode template for a manifest entry.
fn pseudocode_template(crate_name: &str, surface_name: &str, kind: &str) -> String {
    format!(
        "// TODO: Write test for {crate_name}/{surface_name} ({kind})\n\
         // Identify the public API entry point, craft adversarial input,\n\
         // and verify the system handles it gracefully (no panic, correct rejection)."
    )
}

/// Generate a recommended fix description for a manifest entry.
fn fix_template(crate_name: &str, surface_name: &str, kind: &str) -> String {
    format!(
        "Add validation and tests for {kind} in {crate_name}/src/{surface_name}.rs. \
         Ensure adversarial inputs are rejected gracefully without panics."
    )
}

/// Generate redteam proposals from the manifest.
///
/// For each attack surface marked as `tested = false`, generates a proposal
/// with `existing_coverage = false`. Tested surfaces are included with
/// `existing_coverage = true` for completeness.
///
/// The manifest hash is included in each proposal's signature to ensure
/// that manifest changes unsuspend the redteam cycle.
#[must_use]
pub fn manifest_to_proposals(manifest: &ManifestFile) -> Vec<RedteamProposal> {
    let mut proposals = Vec::new();

    for crate_entry in &manifest.crates {
        for surface in &crate_entry.attack_surfaces {
            let attack_vector = attack_vector_template(&surface.kind);
            proposals.push(RedteamProposal {
                target_system: crate_entry.name.clone(),
                attack_vector: format!(
                    "{surface_name}: {attack_vector}",
                    surface_name = surface.name
                ),
                expected_behavior: if surface.tested {
                    format!(
                        "Existing tests cover {} {} in {}",
                        surface.name, surface.kind, crate_entry.name
                    )
                } else {
                    format!(
                        "{} should validate {} inputs and reject adversarial payloads",
                        crate_entry.name, surface.kind
                    )
                },
                test_pseudocode: pseudocode_template(
                    &crate_entry.name,
                    &surface.name,
                    &surface.kind,
                ),
                risk_level: if surface.tested { "covered" } else { "medium" }.to_string(),
                existing_coverage: surface.tested,
                recommended_fix: fix_template(&crate_entry.name, &surface.name, &surface.kind),
            });
        }
    }

    proposals
}

/// Compute a simple hash of the manifest content for signature evolution.
///
/// This hash changes when manifest entries are added, removed, or modified,
/// ensuring the SpiralTracker unsuspends the redteam cycle.
#[must_use]
pub fn manifest_hash(manifest: &ManifestFile) -> u64 {
    let mut hash: u64 = 0;
    for crate_entry in &manifest.crates {
        for surface in &crate_entry.attack_surfaces {
            hash = hash
                .wrapping_mul(31)
                .wrapping_add(crate_entry.name.len() as u64)
                .wrapping_add(surface.name.len() as u64)
                .wrapping_add(surface.kind.len() as u64)
                .wrapping_add(u64::from(surface.tested));
        }
    }
    hash
}

// ── Friction-Based Dynamic Vectors (D4) ───────────────────────────────

/// Generate redteam proposals from friction entries.
///
/// Friction entries are memories tagged `rsi:friction` that record dispatch
/// errors, panics, or unexpected behavior. Each friction entry's content
/// is analyzed for patterns (target system keywords) and a proposal is
/// generated.
///
/// Returns proposals with `existing_coverage = false` since friction
/// entries represent newly discovered issues.
#[must_use]
pub fn friction_to_proposals(
    friction_contents: &[String],
    manifest: Option<&ManifestFile>,
) -> Vec<RedteamProposal> {
    let mut proposals = Vec::new();
    let mut seen = std::collections::HashSet::new();

    // Build a set of known crate names from the manifest for matching
    let crate_names: Vec<&str> = manifest
        .map(|m| m.crates.iter().map(|c| c.name.as_str()).collect())
        .unwrap_or_default();

    for content in friction_contents {
        let lower = content.to_lowercase();

        // Match against known crate names
        for &crate_name in &crate_names {
            if lower.contains(crate_name) {
                let key = format!("{crate_name}:friction");
                if seen.insert(key.clone()) {
                    proposals.push(RedteamProposal {
                        target_system: crate_name.to_string(),
                        attack_vector: format!("Friction-discovered issue: {content}"),
                        expected_behavior: format!(
                            "{crate_name} should handle the reported scenario gracefully"
                        ),
                        test_pseudocode: format!(
                            "// Reproduce friction scenario from: {content}\n\
                             // Write a test that verifies the fix."
                        ),
                        risk_level: "high".to_string(),
                        existing_coverage: false,
                        recommended_fix: format!(
                            "Investigate friction entry in {crate_name} and add regression test."
                        ),
                    });
                }
            }
        }
    }

    proposals
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn read_default_manifest_succeeds() {
        let manifest = read_default_manifest();
        assert!(manifest.is_some(), "Default manifest should be readable");
        let m = manifest.unwrap();
        assert!(
            m.crates.len() >= 14,
            "Should have at least 14 crates, got {}",
            m.crates.len()
        );
    }

    #[test]
    fn manifest_has_attack_surfaces() {
        let manifest = read_default_manifest().unwrap();
        let total_surfaces: usize = manifest
            .crates
            .iter()
            .map(|c| c.attack_surfaces.len())
            .sum();
        assert!(
            total_surfaces >= 30,
            "Should have at least 30 attack surfaces, got {total_surfaces}"
        );
    }

    #[test]
    fn manifest_to_proposals_generates_all() {
        let manifest = read_default_manifest().unwrap();
        let proposals = manifest_to_proposals(&manifest);
        let total_surfaces: usize = manifest
            .crates
            .iter()
            .map(|c| c.attack_surfaces.len())
            .sum();
        assert_eq!(
            proposals.len(),
            total_surfaces,
            "Should generate one proposal per attack surface"
        );
    }

    #[test]
    fn manifest_to_proposals_marks_untested_as_uncovered() {
        let manifest = read_default_manifest().unwrap();
        let proposals = manifest_to_proposals(&manifest);
        let uncovered = proposals.iter().filter(|p| !p.existing_coverage).count();
        // All 33 manifest attack surfaces are now tested
        assert_eq!(
            uncovered, 0,
            "All manifest surfaces should have coverage, got {uncovered} uncovered"
        );
    }

    #[test]
    fn manifest_hash_is_deterministic() {
        let manifest = read_default_manifest().unwrap();
        let h1 = manifest_hash(&manifest);
        let h2 = manifest_hash(&manifest);
        assert_eq!(h1, h2, "Hash should be deterministic");
    }

    #[test]
    fn manifest_hash_changes_on_modification() {
        let manifest = read_default_manifest().unwrap();
        let h1 = manifest_hash(&manifest);

        let mut modified = manifest;
        modified.crates[0].attack_surfaces[0].tested =
            !modified.crates[0].attack_surfaces[0].tested;
        let h2 = manifest_hash(&modified);
        assert_ne!(h1, h2, "Hash should change when manifest is modified");
    }

    #[test]
    fn read_nonexistent_manifest_returns_none() {
        let result = read_manifest(Path::new("/nonexistent/manifest.toml"));
        assert!(result.is_none());
    }

    #[test]
    fn friction_to_proposals_matches_crate_names() {
        let manifest = read_default_manifest().unwrap();
        let friction = vec![
            "wm-core security module panicked on input".to_string(),
            "wm-memory store hit MapFull error".to_string(),
        ];
        let proposals = friction_to_proposals(&friction, Some(&manifest));
        assert!(
            proposals.len() >= 2,
            "Should generate proposals for matched friction entries"
        );
        assert!(proposals.iter().any(|p| p.target_system == "wm-core"));
        assert!(proposals.iter().any(|p| p.target_system == "wm-memory"));
    }

    #[test]
    fn friction_to_proposals_deduplicates() {
        let manifest = read_default_manifest().unwrap();
        let friction = vec!["wm-core error 1".to_string(), "wm-core error 2".to_string()];
        let proposals = friction_to_proposals(&friction, Some(&manifest));
        let core_count = proposals
            .iter()
            .filter(|p| p.target_system == "wm-core")
            .count();
        assert_eq!(core_count, 1, "Should deduplicate by crate name");
    }

    #[test]
    fn friction_to_proposals_no_manifest_still_works() {
        let friction = vec!["some error".to_string()];
        let proposals = friction_to_proposals(&friction, None);
        assert!(
            proposals.is_empty(),
            "Without manifest, no crate matching occurs"
        );
    }

    // ── D3: Test coverage checker tests ─────────────────────────────

    #[test]
    fn has_test_coverage_finds_security_tests() {
        // wm-core/src/security.rs has tests for "security" surface
        let ws = Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .and_then(|p| p.parent());
        let core_src = ws.unwrap().join("crates").join("wm-core").join("src");
        assert!(
            has_test_coverage(&core_src, "security"),
            "Should find security test coverage in wm-core"
        );
    }

    #[test]
    fn has_test_coverage_finds_store_tests() {
        let ws = Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .and_then(|p| p.parent());
        let mem_src = ws.unwrap().join("crates").join("wm-memory").join("src");
        assert!(
            has_test_coverage(&mem_src, "store"),
            "Should find store test coverage in wm-memory"
        );
    }

    #[test]
    fn has_test_coverage_returns_false_for_nonexistent() {
        let ws = Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .and_then(|p| p.parent());
        let core_src = ws.unwrap().join("crates").join("wm-core").join("src");
        assert!(
            !has_test_coverage(&core_src, "nonexistent_surface_12345"),
            "Should not find coverage for nonexistent surface"
        );
    }

    #[test]
    fn has_test_coverage_returns_false_for_missing_dir() {
        assert!(
            !has_test_coverage(Path::new("/nonexistent/path"), "anything"),
            "Should return false for nonexistent directory"
        );
    }

    #[test]
    fn enrich_with_coverage_updates_manifest() {
        let manifest = read_default_manifest().unwrap();
        let enriched = enrich_with_coverage(manifest);

        // wm-core security should be detected as tested
        let core = enriched
            .crates
            .iter()
            .find(|c| c.name == "wm-core")
            .unwrap();
        let security = core
            .attack_surfaces
            .iter()
            .find(|s| s.name == "security")
            .unwrap();
        assert!(
            security.tested,
            "enrich_with_coverage should detect security tests in wm-core"
        );
    }
}
