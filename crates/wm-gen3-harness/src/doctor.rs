//! `wm doctor` — Read-only environment, client config, store, and contract diagnostics.
//!
//! Catches the real-world operational footguns before they break an agent session:
//! - unexpanded literal `$HOME` or `~/` inside IDE MCP configurations,
//! - multiple writable `wm serve` / `wm3 serve` client entries missing `--readonly`,
//! - unmigrated legacy Gen 2 LMDB stores,
//! - missing fastembed model cache vs minimal zero-DLL build profile,
//! - live CLI/MCP route contract drift against `build_contract_manifest`.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::time::Instant;
use wm_gen3_core::compat::Gen2Reader;
use wm_gen3_core::constitution::default_view;
use wm_gen3_core::ops::Substrate;

use crate::bridge::{McpProfile, build_contract_manifest, get_tools_list_for_profile};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum DoctorStatus {
    Ok,
    Warn,
    Fail,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DoctorCheck {
    pub name: &'static str,
    pub status: DoctorStatus,
    pub summary: String,
    pub detail: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub hint: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DoctorReport {
    pub version: &'static str,
    pub healthy: bool,
    pub store_path: String,
    pub fastembed_compiled: bool,
    pub checks: Vec<DoctorCheck>,
    pub total_ms: u128,
}

fn client_config_candidates(home: &Path) -> Vec<(&'static str, PathBuf)> {
    vec![
        ("Claude Code", home.join(".claude.json")),
        (
            "Claude Desktop",
            home.join(".config/Claude/claude_desktop_config.json"),
        ),
        ("Cursor", home.join(".cursor/mcp.json")),
        ("Windsurf", home.join(".codeium/windsurf/mcp_config.json")),
        ("OpenCode", home.join(".config/opencode/opencode.jsonc")),
        ("Codex CLI", home.join(".codex/config.toml")),
        (
            "Antigravity CLI",
            home.join(".gemini/antigravity-cli/settings.json"),
        ),
        (
            "Antigravity",
            home.join(".gemini/antigravity/mcp_config.json"),
        ),
    ]
}

fn extract_whitemagic_fragment(raw: &str, path: &Path) -> Option<String> {
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
    if ext == "json" {
        if let Ok(doc) = serde_json::from_str::<serde_json::Value>(raw) {
            if let Some(entry) = doc
                .get("mcpServers")
                .and_then(|m| m.get("whitemagic"))
                .or_else(|| doc.get("mcp").and_then(|m| m.get("whitemagic")))
            {
                return serde_json::to_string(entry).ok();
            }
            return None;
        }
    }
    // Line-oriented extraction for TOML and JSONC (which may contain comments).
    let lower = raw.to_ascii_lowercase();
    if !lower.contains("whitemagic") {
        return None;
    }
    let lines: Vec<&str> = raw.lines().collect();
    let mut kept = Vec::new();
    for (idx, line) in lines.iter().enumerate() {
        let l = line.to_ascii_lowercase();
        if l.contains("whitemagic") || l.contains("wm3") || l.contains("gen3") {
            let start = idx.saturating_sub(1);
            let end = (idx + 6).min(lines.len());
            kept.extend_from_slice(&lines[start..end]);
        }
    }
    if kept.is_empty() {
        None
    } else {
        Some(kept.join("\n"))
    }
}

fn inspect_client_configs(home: Option<&Path>) -> DoctorCheck {
    let Some(home_dir) = home else {
        return DoctorCheck {
            name: "client_configs",
            status: DoctorStatus::Warn,
            summary: "HOME environment variable unset".to_string(),
            detail: "Skipped client MCP config scan because HOME could not be resolved."
                .to_string(),
            hint: Some("Set HOME or pass explicit --store when invoking wm.".to_string()),
        };
    };

    let mut configured = Vec::new();
    let mut writable_servers = Vec::new();
    let mut unexpanded_home = Vec::new();

    for (label, cfg_path) in client_config_candidates(home_dir) {
        let Ok(raw) = std::fs::read_to_string(&cfg_path) else {
            continue;
        };
        let Some(fragment) = extract_whitemagic_fragment(&raw, &cfg_path) else {
            continue;
        };
        configured.push(format!("{label} ({})", cfg_path.display()));
        if fragment.contains("$HOME") || fragment.contains("${HOME}") || fragment.contains("~/") {
            unexpanded_home.push(format!("{label}: {}", cfg_path.display()));
        }
        let has_serve = fragment.contains("serve");
        let is_readonly = fragment.contains("--readonly");
        let is_disabled = fragment.contains("\"enabled\":false")
            || fragment.contains("\"enabled\": false")
            || fragment.contains("enabled = false");
        if has_serve && !is_readonly && !is_disabled {
            writable_servers.push(label);
        }
    }

    if !unexpanded_home.is_empty() {
        return DoctorCheck {
            name: "client_configs",
            status: DoctorStatus::Warn,
            summary: format!(
                "{} client config(s) contain unexpanded $HOME or ~/",
                unexpanded_home.len()
            ),
            detail: format!("Affected configs: {}", unexpanded_home.join("; ")),
            hint: Some(
                "MCP launchers often do not run a shell; replace literal `$HOME` or `~/` with an absolute path."
                    .to_string(),
            ),
        };
    }

    if writable_servers.len() > 1 {
        return DoctorCheck {
            name: "client_configs",
            status: DoctorStatus::Warn,
            summary: format!(
                "{} writable wm serve configs point at local stores without --readonly",
                writable_servers.len()
            ),
            detail: format!(
                "Writable configs: {} (all detected: {})",
                writable_servers.join(", "),
                configured.join("; ")
            ),
            hint: Some(
                "Keep one primary writable `wm serve` and pass `--readonly` on secondary IDE clients to respect the single-writer LMDB law."
                    .to_string(),
            ),
        };
    }

    DoctorCheck {
        name: "client_configs",
        status: DoctorStatus::Ok,
        summary: format!(
            "{} configured MCP client(s) checked; no literal $HOME or multi-writer hazards",
            configured.len()
        ),
        detail: if configured.is_empty() {
            "No client configs with WhiteMagic entries found yet.".to_string()
        } else {
            configured.join("; ")
        },
        hint: None,
    }
}

/// Run a non-mutating diagnostic pass across store, embedding backend, client configs, and contract parity.
pub fn run_doctor(store_path: &Path, json_mode: bool) -> Result<DoctorReport, String> {
    let home = std::env::var_os("HOME").map(PathBuf::from);
    let cache_dir = wm_gen3_core::embed_cache_dir();
    run_doctor_with_home(store_path, json_mode, home.as_deref(), Some(&cache_dir))
}

/// Testable core accepting explicit `home` and optional `embed_cache` directory.
pub fn run_doctor_with_home(
    store_path: &Path,
    json_mode: bool,
    home: Option<&Path>,
    embed_cache: Option<&Path>,
) -> Result<DoctorReport, String> {
    let t_start = Instant::now();
    let mut checks = Vec::new();

    // 1. Store health & legacy detection (strictly read-only).
    let store_check = if !store_path.exists() {
        DoctorCheck {
            name: "store",
            status: DoctorStatus::Warn,
            summary: "Store directory does not exist yet".to_string(),
            detail: format!("Path: {}", store_path.display()),
            hint: Some("Run `wm init` or `wm grimoire` to initialize the Gen3 store.".to_string()),
        }
    } else if Gen2Reader::open(store_path).is_ok() && !store_path.join("data.mdb").exists() {
        DoctorCheck {
            name: "store",
            status: DoctorStatus::Warn,
            summary: "Legacy Gen2 SQLite store detected at target path".to_string(),
            detail: format!("Path: {}", store_path.display()),
            hint: Some(
                "Run `wm migrate --source <gen2_dir>` into a Gen3 store path before serving."
                    .to_string(),
            ),
        }
    } else {
        let journal = store_path.join("journal.jsonl");
        match Substrate::open_readonly(store_path, Some(&journal), default_view()) {
            Ok(sub) => {
                let records = sub.store().record_count().unwrap_or(0);
                let epoch = sub.store().epoch().unwrap_or(0);
                DoctorCheck {
                    name: "store",
                    status: DoctorStatus::Ok,
                    summary: format!("Gen3 LMDB store readable ({records} records, epoch {epoch})"),
                    detail: format!("Path: {}", store_path.display()),
                    hint: None,
                }
            }
            Err(err) => DoctorCheck {
                name: "store",
                status: DoctorStatus::Fail,
                summary: "Failed opening Gen3 store read-only".to_string(),
                detail: format!("Path: {} ({err})", store_path.display()),
                hint: Some(
                    "Verify directory permissions and ensure no incompatible store lock or corruption exists."
                        .to_string(),
                ),
            },
        }
    };
    checks.push(store_check);

    // 2. Embedding backend & offline cache readiness.
    let fastembed_on = wm_gen3_core::projection::fastembed_compiled();
    let embed_check = if !fastembed_on {
        DoctorCheck {
            name: "embeddings",
            status: DoctorStatus::Ok,
            summary: "Minimal zero-DLL build (fastembed/ONNX disabled)".to_string(),
            detail: "Pure-Rust BM25, System 0.5, and 32B qFHRR similarity active without ONNX Runtime DLLs."
                .to_string(),
            hint: None,
        }
    } else if let Some(cache) = embed_cache {
        let has_model = cache
            .join("models--Qdrant--bge-small-en-v1.5-onnx-Q")
            .exists()
            || cache.join("models--Xenova--bge-small-en-v1.5").exists();
        if has_model {
            DoctorCheck {
                name: "embeddings",
                status: DoctorStatus::Ok,
                summary: "Offline fastembed BGE-small model cache verified".to_string(),
                detail: format!("Cache dir: {}", cache.display()),
                hint: None,
            }
        } else {
            DoctorCheck {
                name: "embeddings",
                status: DoctorStatus::Warn,
                summary: "fastembed model cache missing; lexical + System 0.5 recall remains active"
                    .to_string(),
                detail: format!("Checked: {}", cache.display()),
                hint: Some(
                    "Set `WM_GEN3_EMBED_CACHE` to a pre-warmed cache if dense ONNX projection is needed."
                        .to_string(),
                ),
            }
        }
    } else {
        DoctorCheck {
            name: "embeddings",
            status: DoctorStatus::Warn,
            summary: "No embedding cache path supplied".to_string(),
            detail: "Skipped offline ONNX model check.".to_string(),
            hint: None,
        }
    };
    checks.push(embed_check);

    // 3. Client MCP configuration hygiene.
    checks.push(inspect_client_configs(home));

    // 4. Hybrid CLI/MCP route contract parity.
    let manifest = build_contract_manifest(env!("CARGO_PKG_VERSION"));
    let manifest_routes = manifest["counts"]["routes"].as_u64().unwrap_or(0) as usize;
    let live_tools_val = get_tools_list_for_profile(McpProfile::Full, false);
    let live_tools = live_tools_val.as_array();
    let live_full = live_tools.map_or(0, Vec::len);
    let valid_schemas = live_tools.is_some_and(|arr| {
        arr.iter()
            .all(|t| t["inputSchema"]["type"].as_str() == Some("object"))
    });
    let contract_check = if manifest_routes > 0 && manifest_routes == live_full && valid_schemas {
        DoctorCheck {
            name: "contract",
            status: DoctorStatus::Ok,
            summary: format!("Route contract verified ({live_full} tools, schemas valid)"),
            detail: "Live MCP Full profile matches build_contract_manifest.".to_string(),
            hint: None,
        }
    } else {
        DoctorCheck {
            name: "contract",
            status: DoctorStatus::Fail,
            summary: "Route contract drift detected".to_string(),
            detail: format!(
                "manifest_routes={manifest_routes}, live_full={live_full}, valid_schemas={valid_schemas}"
            ),
            hint: Some("Align bridge.rs contract manifest counts and tools/list.".to_string()),
        }
    };
    checks.push(contract_check);

    let healthy = checks.iter().all(|c| c.status != DoctorStatus::Fail);
    let report = DoctorReport {
        version: env!("CARGO_PKG_VERSION"),
        healthy,
        store_path: store_path.display().to_string(),
        fastembed_compiled: fastembed_on,
        checks,
        total_ms: t_start.elapsed().as_millis(),
    };

    if json_mode {
        let out = serde_json::to_string_pretty(&report)
            .map_err(|e| format!("doctor JSON serialization failed: {e}"))?;
        println!("{out}");
    } else {
        println!("==================================================");
        println!("      WhiteMagic Gen3 Doctor (v{})", report.version);
        println!("==================================================");
        println!("Store Path:       {}", report.store_path);
        println!(
            "Fastembed/ONNX:   {}",
            if report.fastembed_compiled {
                "compiled"
            } else {
                "disabled (zero-DLL pure-Rust mode)"
            }
        );
        println!("--------------------------------------------------");
        for c in &report.checks {
            let tag = match c.status {
                DoctorStatus::Ok => "[OK]  ",
                DoctorStatus::Warn => "[WARN]",
                DoctorStatus::Fail => "[FAIL]",
            };
            println!("{tag} {:<15} : {}", c.name, c.summary);
            println!("       Detail: {}", c.detail);
            if let Some(ref hint) = c.hint {
                println!("       Hint:   {hint}");
            }
        }
        println!("==================================================");
    }

    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn doctor_flags_literal_home_and_multi_writer_without_touching_store() {
        let root = std::env::temp_dir().join(format!("wm-doctor-test-{}", uuid::Uuid::new_v4()));
        let home = root.join("home");
        let store = root.join("missing-store");
        std::fs::create_dir_all(home.join(".cursor")).expect("mkdir cursor");
        std::fs::create_dir_all(home.join(".codex")).expect("mkdir codex");

        // 1. Literal $HOME hazard detected
        std::fs::write(
            home.join(".cursor/mcp.json"),
            r#"{"mcpServers":{"whitemagic":{"command":"$HOME/.local/bin/wm3","args":["serve"]}}}"#,
        )
        .expect("write cursor");
        let r1 = run_doctor_with_home(&store, false, Some(&home), None).expect("doctor run 1");
        assert!(!store.exists(), "doctor must never create a missing store");
        let cfg1 = r1
            .checks
            .iter()
            .find(|c| c.name == "client_configs")
            .expect("client_configs check");
        assert_eq!(cfg1.status, DoctorStatus::Warn);
        assert!(cfg1.summary.contains("$HOME"));

        // 2. Expanded paths, but two writable servers without --readonly -> Warn
        std::fs::write(
            home.join(".cursor/mcp.json"),
            r#"{"mcpServers":{"whitemagic":{"command":"/usr/local/bin/wm3","args":["serve"]}}}"#,
        )
        .expect("rewrite cursor");
        std::fs::write(
            home.join(".codex/config.toml"),
            "[mcp_servers.whitemagic]\ncommand = \"/usr/local/bin/wm3\"\nargs = [\"serve\"]\n",
        )
        .expect("write codex");
        let r2 = run_doctor_with_home(&store, false, Some(&home), None).expect("doctor run 2");
        let cfg2 = r2
            .checks
            .iter()
            .find(|c| c.name == "client_configs")
            .expect("client_configs check");
        assert_eq!(cfg2.status, DoctorStatus::Warn);
        assert!(cfg2.summary.contains("--readonly"));

        // 3. Secondary server switched to --readonly (or disabled) -> Ok
        std::fs::write(
            home.join(".codex/config.toml"),
            "[mcp_servers.whitemagic]\ncommand = \"/usr/local/bin/wm3\"\nargs = [\"serve\", \"--readonly\"]\n",
        )
        .expect("rewrite codex readonly");
        let r3 = run_doctor_with_home(&store, false, Some(&home), None).expect("doctor run 3");
        let cfg3 = r3
            .checks
            .iter()
            .find(|c| c.name == "client_configs")
            .expect("client_configs check");
        assert_eq!(cfg3.status, DoctorStatus::Ok);
        let contract = r3
            .checks
            .iter()
            .find(|c| c.name == "contract")
            .expect("contract check");
        assert_eq!(contract.status, DoctorStatus::Ok);

        std::fs::remove_dir_all(root).ok();
    }
}
