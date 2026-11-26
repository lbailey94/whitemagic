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
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{Duration, Instant};
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
        ("Antigravity", home.join(".gemini/config/mcp_config.json")),
        (
            "Antigravity CLI (legacy)",
            home.join(".gemini/antigravity-cli/settings.json"),
        ),
        (
            "Antigravity (legacy)",
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

/// Run diagnostics across store, LMDB reader table (optionally reclaiming stale slots),
/// embedding backend, client configs, and contract parity.
pub fn run_doctor_with_options(
    store_path: &Path,
    json_mode: bool,
    fix_readers: bool,
) -> Result<DoctorReport, String> {
    run_doctor_with_suite(store_path, json_mode, fix_readers, false)
}
pub fn run_doctor(store_path: &Path, json_mode: bool) -> Result<DoctorReport, String> {
    run_doctor_with_options(store_path, json_mode, false)
}

/// Run diagnostics across store, LMDB reader table, embedding backend, client configs,
/// contract parity, and optionally the WhiteMagic Suite (`--suite`).
pub fn run_doctor_with_suite(
    store_path: &Path,
    json_mode: bool,
    fix_readers: bool,
    suite_mode: bool,
) -> Result<DoctorReport, String> {
    let home = std::env::var_os("HOME").map(PathBuf::from);
    let cache_dir = wm_gen3_core::embed_cache_dir();
    run_doctor_with_home_and_suite(
        store_path,
        json_mode,
        home.as_deref(),
        Some(&cache_dir),
        fix_readers,
        suite_mode,
    )
}

/// Testable core accepting explicit `home`, optional `embed_cache`, `fix_readers`, and `suite_mode`.
pub fn run_doctor_with_home(
    store_path: &Path,
    json_mode: bool,
    home: Option<&Path>,
    embed_cache: Option<&Path>,
) -> Result<DoctorReport, String> {
    run_doctor_with_home_and_suite(store_path, json_mode, home, embed_cache, false, false)
}

/// Testable core supporting optional `--suite` checks.
pub fn run_doctor_with_home_and_suite(
    store_path: &Path,
    json_mode: bool,
    home: Option<&Path>,
    embed_cache: Option<&Path>,
    fix_readers: bool,
    suite_mode: bool,
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

    // 1b. LMDB reader-lock table health & optional stale-slot reclamation.
    let mut reclaimed_readers = 0usize;
    let mut reclaim_err: Option<String> = None;
    if fix_readers && store_path.join("lock.mdb").is_file() {
        match wm_gen3_core::store::Store::reclaim_stale_readers_at_path(store_path) {
            Ok(n) => reclaimed_readers = n,
            Err(err) => reclaim_err = Some(err.to_string()),
        }
    }
    let reader_check = if let Some(err) = reclaim_err {
        DoctorCheck {
            name: "reader_table",
            status: DoctorStatus::Fail,
            summary: "Failed reclaiming stale LMDB reader slots".to_string(),
            detail: format!("Path: {} ({err})", store_path.display()),
            hint: Some("Verify lock.mdb permissions and check active wm processes.".to_string()),
        }
    } else {
        match wm_gen3_core::store::Store::inspect_reader_table(store_path) {
            Ok(None) => DoctorCheck {
                name: "reader_table",
                status: DoctorStatus::Ok,
                summary: "No LMDB lock table present yet".to_string(),
                detail: format!("Path: {}", store_path.display()),
                hint: None,
            },
            Ok(Some(snap)) => {
                let reclaimed_note = if fix_readers {
                    format!(", reclaimed {reclaimed_readers} stale slot(s)")
                } else {
                    String::new()
                };
                if snap.free == 0 {
                    DoctorCheck {
                        name: "reader_table",
                        status: DoctorStatus::Fail,
                        summary: format!(
                            "LMDB reader table FULL ({}/{}, {} dead, 0 free)",
                            snap.occupied, snap.max_readers, snap.dead
                        ),
                        detail: format!(
                            "Path: {} (live={}, dead={}, max={}{reclaimed_note})",
                            store_path.display(),
                            snap.live,
                            snap.dead,
                            snap.max_readers
                        ),
                        hint: Some(
                            "Run `wm doctor --fix-readers` to reclaim stale reader slots safely without stopping live servers."
                                .to_string(),
                        ),
                    }
                } else if snap.dead > 0
                    || snap.occupied.saturating_mul(5)
                        >= (snap.max_readers as usize).saturating_mul(4)
                {
                    DoctorCheck {
                        name: "reader_table",
                        status: DoctorStatus::Warn,
                        summary: format!(
                            "LMDB reader table pressure ({} live, {} dead, {}/{} free)",
                            snap.live, snap.dead, snap.free, snap.max_readers
                        ),
                        detail: format!(
                            "Path: {} (occupied={}/{}{reclaimed_note})",
                            store_path.display(),
                            snap.occupied,
                            snap.max_readers
                        ),
                        hint: if snap.dead > 0 {
                            Some(format!(
                                "Run `wm doctor --fix-readers` to reclaim {} stale reader slot(s).",
                                snap.dead
                            ))
                        } else {
                            Some(
                                "Raise WM_MAX_READERS (default 1024) or trim concurrent idle MCP servers."
                                    .to_string(),
                            )
                        },
                    }
                } else {
                    DoctorCheck {
                        name: "reader_table",
                        status: DoctorStatus::Ok,
                        summary: format!(
                            "LMDB reader table healthy ({} live, 0 dead, {}/{} free)",
                            snap.live, snap.free, snap.max_readers
                        ),
                        detail: format!(
                            "Path: {} (occupied={}/{}{reclaimed_note})",
                            store_path.display(),
                            snap.occupied,
                            snap.max_readers
                        ),
                        hint: None,
                    }
                }
            }
            Err(err) => DoctorCheck {
                name: "reader_table",
                status: DoctorStatus::Warn,
                summary: "Could not inspect LMDB reader table".to_string(),
                detail: format!("Path: {} ({err})", store_path.display()),
                hint: Some(
                    "Check lock.mdb permissions or run `wm doctor --fix-readers`.".to_string(),
                ),
            },
        }
    };
    checks.push(reader_check);

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

    if suite_mode {
        run_suite_checks(home, &mut checks);
    }

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

fn find_suite_bin(name: &str, home: Option<&Path>) -> Option<PathBuf> {
    if let Some(h) = home {
        let local = h.join(".local/bin").join(name);
        if local.is_file() {
            return Some(local);
        }
    }
    if let Some(paths) = std::env::var_os("PATH") {
        for dir in std::env::split_paths(&paths) {
            let cand = dir.join(name);
            if cand.is_file() {
                return Some(cand);
            }
        }
    }
    None
}

fn check_loopback_sidecar_health(disc_path: &Path) -> Option<(bool, String)> {
    let raw = std::fs::read_to_string(disc_path).ok()?;
    let val: serde_json::Value = serde_json::from_str(&raw).ok()?;
    let port = val.get("port").and_then(serde_json::Value::as_u64)?;
    if !(1..=65535).contains(&port) {
        return None;
    }
    let addr: SocketAddr = format!("127.0.0.1:{port}").parse().ok()?;
    let timeout = Duration::from_millis(250);
    let mut stream = TcpStream::connect_timeout(&addr, timeout).ok()?;
    let _ = stream.set_read_timeout(Some(timeout));
    let _ = stream.set_write_timeout(Some(timeout));
    let req = "GET /healthz HTTP/1.0\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
    stream.write_all(req.as_bytes()).ok()?;
    let _ = stream.flush();
    let mut buf = Vec::new();
    let _ = stream.take(16_384).read_to_end(&mut buf);
    let text = String::from_utf8_lossy(&buf);
    let first_line = text.lines().next().unwrap_or("");
    Some((
        first_line.contains(" 200 "),
        format!("http://127.0.0.1:{port}"),
    ))
}

fn run_suite_checks(home: Option<&Path>, checks: &mut Vec<DoctorCheck>) {
    // S1: Hook configs across AGY, Codex, Cursor
    let mut hook_ok = Vec::new();
    let mut hook_warn = Vec::new();
    let mut hook_fail = Vec::new();
    if let Some(h) = home {
        let targets = [
            (
                "AGY plugin",
                h.join(".gemini"),
                h.join(".gemini/config/plugins/whitemagic-agy-kit/plugin.json"),
            ),
            ("Codex hooks", h.join(".codex"), h.join(".codex/hooks.json")),
            (
                "Cursor hooks",
                h.join(".cursor"),
                h.join(".cursor/hooks.json"),
            ),
        ];
        for (label, host_dir, file_path) in targets {
            if !host_dir.exists() {
                continue;
            }
            if !file_path.is_file() {
                hook_warn.push(format!("{label}: missing {}", file_path.display()));
                continue;
            }
            match std::fs::read_to_string(&file_path)
                .ok()
                .and_then(|s| serde_json::from_str::<serde_json::Value>(&s).ok())
            {
                Some(_) => hook_ok.push(label.to_string()),
                None => hook_fail.push(format!(
                    "{label}: malformed JSON at {}",
                    file_path.display()
                )),
            }
        }
    }
    checks.push(if !hook_fail.is_empty() {
        DoctorCheck {
            name: "suite_hooks",
            status: DoctorStatus::Fail,
            summary: format!(
                "{} host hook config(s) contain malformed JSON",
                hook_fail.len()
            ),
            detail: hook_fail.join("; "),
            hint: Some(
                "Re-run `install-suite.sh` or `whitemagic-agy-kit/install.sh` to repair host JSON."
                    .to_string(),
            ),
        }
    } else if !hook_warn.is_empty() {
        DoctorCheck {
            name: "suite_hooks",
            status: DoctorStatus::Warn,
            summary: format!("{} detected host(s) missing suite hooks", hook_warn.len()),
            detail: hook_warn.join("; "),
            hint: Some("Run `wm grimoire --suite --write` to wire detected hosts.".to_string()),
        }
    } else {
        DoctorCheck {
            name: "suite_hooks",
            status: DoctorStatus::Ok,
            summary: if hook_ok.is_empty() {
                "No AGY/Codex/Cursor host directories detected".to_string()
            } else {
                format!("Suite hooks verified ({})", hook_ok.join(", "))
            },
            detail: "Checked detected host plugin & hook JSON files.".to_string(),
            hint: None,
        }
    });

    // S2: Live wm-sandbox --probe
    checks.push(if let Some(sb_bin) = find_suite_bin("wm-sandbox", home) {
        match Command::new(&sb_bin).arg("--probe").output() {
            Ok(out) if out.status.success() => {
                match serde_json::from_slice::<serde_json::Value>(&out.stdout) {
                    Ok(v) => {
                        let supported = v
                            .get("landlock_supported")
                            .and_then(serde_json::Value::as_bool)
                            .unwrap_or(false);
                        let abi = v
                            .get("kernel_landlock_abi")
                            .and_then(serde_json::Value::as_u64)
                            .unwrap_or(0);
                        let zero_egress = v
                            .get("zero_egress_capable")
                            .and_then(serde_json::Value::as_bool)
                            .unwrap_or(false);
                        if supported && abi >= 4 {
                            DoctorCheck {
                                name: "sandbox_probe",
                                status: DoctorStatus::Ok,
                                summary: format!("Landlock ABI {abi} active (zero_egress={zero_egress})"),
                                detail: format!("Binary: {}", sb_bin.display()),
                                hint: None,
                            }
                        } else {
                            DoctorCheck {
                                name: "sandbox_probe",
                                status: DoctorStatus::Warn,
                                summary: format!("Kernel Landlock limited/unsupported (supported={supported}, abi={abi})"),
                                detail: format!("Binary: {}", sb_bin.display()),
                                hint: Some("On non-Linux or older kernels, policy/VFS preflight remains active.".to_string()),
                            }
                        }
                    }
                    Err(e) => DoctorCheck {
                        name: "sandbox_probe",
                        status: DoctorStatus::Warn,
                        summary: "wm-sandbox --probe returned invalid JSON".to_string(),
                        detail: e.to_string(),
                        hint: None,
                    },
                }
            }
            _ => DoctorCheck {
                name: "sandbox_probe",
                status: DoctorStatus::Warn,
                summary: "wm-sandbox --probe failed to execute cleanly".to_string(),
                detail: format!("Binary: {}", sb_bin.display()),
                hint: Some("Rebuild wm3-tui (`cargo build --release`) to refresh wm-sandbox.".to_string()),
            },
        }
    } else {
        DoctorCheck {
            name: "sandbox_probe",
            status: DoctorStatus::Warn,
            summary: "wm-sandbox binary not found on ~/.local/bin or PATH".to_string(),
            detail: "Kernel Landlock probe skipped.".to_string(),
            hint: Some("Install wm3-tui / whitemagic-suite to provide wm-sandbox.".to_string()),
        }
    });

    // S3: Sidecar loopback /healthz
    let cache_dir = std::env::var_os("WM_HANDOFF_CACHE_DIR")
        .map(PathBuf::from)
        .or_else(|| home.map(|h| h.join(".cache/wm-handoff")));
    let disc_path = cache_dir.map(|d| d.join("sidecar.json"));
    checks.push(match disc_path {
        Some(ref p) if p.is_file() => match check_loopback_sidecar_health(p) {
            Some((true, url)) => DoctorCheck {
                name: "sidecar_bus",
                status: DoctorStatus::Ok,
                summary: format!("Sidecar loopback online ({url}/healthz)"),
                detail: format!("Discovery: {}", p.display()),
                hint: None,
            },
            _ => DoctorCheck {
                name: "sidecar_bus",
                status: DoctorStatus::Warn,
                summary: "Sidecar discovery file present but /healthz unreachable".to_string(),
                detail: format!("Discovery: {}", p.display()),
                hint: Some(
                    "Start sidecar via AGY or `python3 -S -B .../wm-sidecar/server.py`."
                        .to_string(),
                ),
            },
        },
        _ => DoctorCheck {
            name: "sidecar_bus",
            status: DoctorStatus::Warn,
            summary: "Sidecar offline (no active sidecar.json)".to_string(),
            detail: "Local JSONL/crystal cache fallback remains operational for wm3-tui."
                .to_string(),
            hint: None,
        },
    });

    // S4: Mandala gate-lite preflight
    let inv = crate::grimoire::probe_suite_inventory(home);
    checks.push(if let Some(ref ctl) = inv.mandala_gate_lite {
        DoctorCheck {
            name: "mandala_preflight",
            status: DoctorStatus::Ok,
            summary: "Mandala gate-lite controller present".to_string(),
            detail: format!("Path: {ctl}"),
            hint: None,
        }
    } else {
        DoctorCheck {
            name: "mandala_preflight",
            status: DoctorStatus::Warn,
            summary: "Mandala gate-lite controller not found".to_string(),
            detail: "Checked suite_manifest.json, WM_MANDALA_DIR, and ~/.local/share/whitemagic/suite/.".to_string(),
            hint: Some("Install whitemagic-suite or set WM_MANDALA_DIR to enable --mandala-guard confinement.".to_string()),
        }
    });

    // S5: wm_fast MCP availability
    let has_node = find_suite_bin("node", home).is_some();
    checks.push(match (inv.wm_fast_mcp.as_ref(), has_node) {
        (Some(p), true) => DoctorCheck {
            name: "wm_fast_mcp",
            status: DoctorStatus::Ok,
            summary: "wm_fast MCP server & Node runtime ready".to_string(),
            detail: format!("Script: {p}"),
            hint: None,
        },
        (Some(p), false) => DoctorCheck {
            name: "wm_fast_mcp",
            status: DoctorStatus::Warn,
            summary: "wm_fast script installed but `node` runtime not found".to_string(),
            detail: format!("Script: {p}"),
            hint: Some("Install Node.js to execute mcp-server.mjs.".to_string()),
        },
        (None, _) => DoctorCheck {
            name: "wm_fast_mcp",
            status: DoctorStatus::Warn,
            summary: "wm_fast MCP server script not installed".to_string(),
            detail: "Checked ~/.local/share/whitemagic/wm-fast-mcp/mcp-server.mjs.".to_string(),
            hint: Some("Run `install-suite.sh` to deploy wm_fast MCP.".to_string()),
        },
    });

    // S6: Key & secret file permission hygiene (<= 0o600 on Unix)
    let mut insecure_keys = Vec::new();
    if let Some(h) = home {
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;
            for dir in [
                h.join(".config/whitemagic"),
                h.join(".local/share/whitemagic"),
            ] {
                let Ok(entries) = std::fs::read_dir(&dir) else {
                    continue;
                };
                for ent in entries.flatten() {
                    let p = ent.path();
                    if !p.is_file() {
                        continue;
                    }
                    let name = p
                        .file_name()
                        .and_then(|s| s.to_str())
                        .unwrap_or("")
                        .to_ascii_lowercase();
                    if name.ends_with(".key")
                        || name.ends_with(".pem")
                        || name.contains("signing")
                        || name.contains("hmac")
                    {
                        if let Ok(meta) = p.metadata() {
                            let mode = meta.permissions().mode() & 0o777;
                            if mode & 0o077 != 0 {
                                insecure_keys.push(format!("{} (mode {:03o})", p.display(), mode));
                            }
                        }
                    }
                }
            }
        }
    }
    checks.push(if insecure_keys.is_empty() {
        DoctorCheck {
            name: "key_permissions",
            status: DoctorStatus::Ok,
            summary: "Signing/key file permissions clean (no group/world access)".to_string(),
            detail: "Checked ~/.config/whitemagic and ~/.local/share/whitemagic.".to_string(),
            hint: None,
        }
    } else {
        DoctorCheck {
            name: "key_permissions",
            status: DoctorStatus::Warn,
            summary: format!(
                "{} key file(s) overly permissive (> 0600)",
                insecure_keys.len()
            ),
            detail: insecure_keys.join("; "),
            hint: Some("Restrict key files with `chmod 600 <path>`.".to_string()),
        }
    });
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
        let rt1 = r1
            .checks
            .iter()
            .find(|c| c.name == "reader_table")
            .expect("reader_table check");
        assert_eq!(rt1.status, DoctorStatus::Ok);
        assert!(
            !store.exists(),
            "reader_table check must not create missing store"
        );

        std::fs::remove_dir_all(root).ok();
    }

    #[test]
    fn doctor_reports_healthy_reader_table_on_initialized_store() {
        let root = std::env::temp_dir().join(format!("wm-doctor-rt-{}", uuid::Uuid::new_v4()));
        let home = root.join("home");
        let store_dir = root.join("store");
        std::fs::create_dir_all(&home).expect("mkdir home");
        let store = wm_gen3_core::store::Store::open(&store_dir).expect("open fresh store");
        drop(store);

        let report = run_doctor_with_home(&store_dir, false, Some(&home), None)
            .expect("doctor on initialized store");
        let rt = report
            .checks
            .iter()
            .find(|c| c.name == "reader_table")
            .expect("reader_table check");
        assert_eq!(rt.status, DoctorStatus::Ok);
        assert!(rt.summary.contains("0 dead"));

        std::fs::remove_dir_all(root).ok();
    }

    #[test]
    fn doctor_suite_checks_verify_hooks_mandala_wm_fast_and_key_perms() {
        let root = std::env::temp_dir().join(format!("wm-doctor-suite-{}", uuid::Uuid::new_v4()));
        let home = root.join("home");
        let store = root.join("missing-store");
        let data = home.join(".local/share/whitemagic");
        std::fs::create_dir_all(home.join(".codex")).expect("mkdir codex");
        std::fs::create_dir_all(home.join(".cursor")).expect("mkdir cursor");
        std::fs::create_dir_all(data.join("wm-fast-mcp")).expect("mkdir wm_fast");
        std::fs::create_dir_all(data.join("suite/mandala-gate-lite/gate_lite"))
            .expect("mkdir mandala");
        std::fs::write(home.join(".codex/hooks.json"), "{\"hooks\":{}}")
            .expect("write codex hooks");
        std::fs::write(home.join(".cursor/hooks.json"), "{\"version\":1}")
            .expect("write cursor hooks");
        std::fs::write(data.join("wm-fast-mcp/mcp-server.mjs"), "// ok\n").expect("write wm_fast");
        std::fs::write(
            data.join("suite/mandala-gate-lite/gate_lite/ctl.py"),
            "# ctl\n",
        )
        .expect("write ctl");
        let key_path = data.join("test_signing.key");
        std::fs::write(&key_path, "secret").expect("write key");
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;
            std::fs::set_permissions(&key_path, std::fs::Permissions::from_mode(0o644))
                .expect("chmod 644");
        }

        let report = run_doctor_with_home_and_suite(&store, false, Some(&home), None, false, true)
            .expect("doctor suite run");
        let find = |n: &str| report.checks.iter().find(|c| c.name == n).unwrap();
        assert_eq!(find("suite_hooks").status, DoctorStatus::Ok);
        assert_eq!(find("mandala_preflight").status, DoctorStatus::Ok);
        assert_eq!(find("key_permissions").status, DoctorStatus::Warn);

        std::fs::remove_dir_all(root).ok();
    }
}
