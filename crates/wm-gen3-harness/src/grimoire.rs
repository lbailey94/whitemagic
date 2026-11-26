//! `wm grimoire` — Adaptive first-run orchestration, capability synthesis, and suite wiring.
//!
//! Wires host hardware/kernel capability probing, Mandala confinement tier selection,
//! WhiteMagic Suite inventory, LMDB substrate provisioning, starter guide galaxy seeding,
//! unified coding-agent client detection (single-writer LMDB safe), model-family adaptive
//! tuning (`grimoire_profile.json`), telemetry feedback self-tuning, and sub-microsecond
//! retrieval verification into one seamless pass:
//!
//! ```text
//! host → confinement → suite_inventory → substrate → starter_galaxy
//!   → agent_clients → model_adaptation → telemetry_tune → verification → readiness
//! ```

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Instant;
use wm_gen3_core::constitution::default_view;
use wm_gen3_core::ops::Substrate;

use crate::setup::{self, ClientSpec};
use crate::starter_galaxy::{GalaxySummary, list_galaxies, seed_starter_guide_if_empty};

/// Step execution status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum StepStatus {
    Ok,
    Warn,
    Skip,
    Fail,
}

/// One grimoire diagnostic step.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GrimoireStep {
    pub name: &'static str,
    pub status: StepStatus,
    pub summary: String,
    pub detail: String,
    pub elapsed_ms: u128,
}

/// Hardware compute tier used to adapt local Tricameral / embedding / MCP defaults.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HardwareTier {
    Micro,
    Standard,
    Sovereign,
}

impl HardwareTier {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Micro => "micro",
            Self::Standard => "standard",
            Self::Sovereign => "sovereign",
        }
    }

    #[must_use]
    pub const fn recommended_tricameral_profile(self) -> &'static str {
        match self {
            Self::Micro => "none",
            Self::Standard => "ravens",
            Self::Sovereign => "tricameral",
        }
    }
}

/// Probed host hardware, kernel security, and runtime capabilities.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HostCapabilities {
    pub os: String,
    pub arch: String,
    pub kernel_release: String,
    pub cores: usize,
    pub ram_gb: u64,
    pub has_avx2: bool,
    pub has_neon: bool,
    pub landlock_active: bool,
    pub landlock_abi_est: Option<u32>,
    pub has_bwrap: bool,
    pub has_wm_sandbox: bool,
    pub has_kvm: bool,
    pub has_firecracker: bool,
    pub has_podman: bool,
    pub has_node: bool,
    pub has_python3: bool,
    pub has_cargo: bool,
    pub local_runtimes: Vec<String>,
}

/// Auto-selected Mandala confinement tier.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ConfinementTier {
    BwrapLandlock,
    LandlockDirect,
    Bwrap,
    Firecracker,
    Podman,
    PreCommandVfsOnly,
}

impl ConfinementTier {
    #[must_use]
    pub const fn runner_profile_id(self) -> &'static str {
        match self {
            Self::BwrapLandlock => "bwrap-landlock-v1",
            Self::LandlockDirect => "landlock-wm-direct-v1",
            Self::Bwrap => "bwrap-v1",
            Self::Firecracker => "firecracker-snap-v1",
            Self::Podman => "podman-v1",
            Self::PreCommandVfsOnly => "pre-command-vfs",
        }
    }
}

/// Selected confinement recommendation and optional degraded notice.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfinementPlan {
    pub tier: ConfinementTier,
    pub runner_profile: String,
    pub burst_runner_profile: Option<String>,
    pub mandala_guard_mode: String,
    pub degraded_reason: Option<String>,
}

/// Target model family for context/cache/clamping adaptation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum ModelFamily {
    Auto,
    Gemini4,
    Claude4,
    OpenAiCodex,
    Grok4,
    LocalSmall,
}

impl ModelFamily {
    #[must_use]
    pub fn parse(raw: &str) -> Option<Self> {
        match raw.trim().to_ascii_lowercase().as_str() {
            "" | "auto" => Some(Self::Auto),
            "gemini" | "gemini4" | "gemini-4" | "hydrogen" | "neon" => Some(Self::Gemini4),
            "claude" | "claude4" | "claude-4" | "opus" | "sonnet" => Some(Self::Claude4),
            "openai" | "codex" | "openai-codex" | "gpt" | "gpt5" => Some(Self::OpenAiCodex),
            "grok" | "grok4" | "grok-4" | "grok-4.7" => Some(Self::Grok4),
            "local" | "local-small" | "ollama" | "tricameral" | "small" => Some(Self::LocalSmall),
            _ => None,
        }
    }

    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Auto => "auto",
            Self::Gemini4 => "gemini4",
            Self::Claude4 => "claude4",
            Self::OpenAiCodex => "openai-codex",
            Self::Grok4 => "grok4",
            Self::LocalSmall => "local-small",
        }
    }
}

const fn default_neon_warn_tokens() -> u64 {
    100_000
}

const fn default_neon_rollover_tokens() -> u64 {
    120_000
}

/// Model-family adaptive tuning parameters consumed by `wm-squeeze`, hooks, and handoffs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdaptiveModelTuning {
    pub requested_family: ModelFamily,
    pub resolved_family: ModelFamily,
    pub detection_source: String,
    pub max_unbounded_read_lines: usize,
    pub clamp_read_lines: usize,
    pub wide_jsonl_lines: usize,
    pub context_warn_tokens: u64,
    pub context_cliff_tokens: u64,
    #[serde(default = "default_neon_warn_tokens")]
    pub neon_warn_tokens: u64,
    #[serde(default = "default_neon_rollover_tokens")]
    pub neon_rollover_tokens: u64,
    pub turn0_brief_max_bytes: usize,
    pub enable_flip_guard: bool,
    pub recommended_mcp_profile: String,
    pub notes: String,
}

/// Inventory of installed WhiteMagic Suite components on this machine.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuiteInventory {
    pub wm_squeeze: Option<String>,
    pub wm_codegraph: Option<String>,
    pub wm_sandbox: Option<String>,
    pub muninn_engine: Option<String>,
    pub wm3_tui: Option<String>,
    pub wm4_mcp: Option<String>,
    pub wm_fast_mcp: Option<String>,
    pub wm_handoff: Option<String>,
    pub wm_cpr_bridge: Option<String>,
    pub wm_sim: Option<String>,
    pub wm_models: Option<String>,
    pub agy_kit_installer: Option<String>,
    pub mandala_gate_lite: Option<String>,
    pub tricameral_spores: Vec<String>,
}

/// Bounded summary of local telemetry & SIM logs for self-tuning.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TelemetryTuningSummary {
    pub squeezed_cmds: u64,
    pub squeeze_raw_bytes: u64,
    pub squeeze_out_bytes: u64,
    pub squeeze_saved_pct: f64,
    pub recent_spills: usize,
    pub recent_cursor_events: usize,
    pub recent_tool_failures: usize,
    pub last_observed_model: Option<String>,
    pub recommendations: Vec<String>,
}

/// Resumable chapter progression tracked in `<data_dir>/grimoire_state.json`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChapterState {
    pub id: &'static str,
    pub roman: &'static str,
    pub title: &'static str,
    pub status: StepStatus,
    pub detail: String,
}

/// Declarative per-machine or per-repo overrides loaded from `.wm-grimoire.toml` or `--apply`.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct GrimoireSpec {
    pub profile: Option<String>,
    pub model: Option<String>,
    pub mandala_guard: Option<String>,
    pub confinement: Option<String>,
    pub clients: Option<Vec<String>>,
    pub readonly_clients: Option<Vec<String>>,
    pub mcp_profile: Option<String>,
    pub clamp_read_lines: Option<usize>,
    pub max_unbounded_read_lines: Option<usize>,
    pub wide_jsonl_lines: Option<usize>,
    pub galaxy: Option<String>,
}

/// Full adaptive profile persisted to `<data_dir>/grimoire_profile.json` (when not `--plan`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GrimoireProfile {
    pub schema: &'static str,
    pub grimoire_version: &'static str,
    pub capabilities: HostCapabilities,
    pub hardware_tier: HardwareTier,
    pub recommended_tricameral_profile: String,
    pub confinement: ConfinementPlan,
    pub model_tuning: AdaptiveModelTuning,
    pub host_profiles: BTreeMap<String, AdaptiveModelTuning>,
    pub suite: SuiteInventory,
    pub primary_writer_client: Option<String>,
    pub secondary_readonly_clients: Vec<String>,
    pub turbo_hosts: Vec<String>,
    pub telemetry: TelemetryTuningSummary,
}

/// Options controlling `wm grimoire` execution.
#[derive(Debug, Clone)]
pub struct GrimoireOptions {
    pub json_mode: bool,
    pub plan_configs: bool,
    pub model_family: ModelFamily,
    pub tune_mode: bool,
    pub suite_mode: bool,
    pub write_mode: bool,
    pub apply_spec: Option<PathBuf>,
    pub guard_mode: Option<String>,
}

impl Default for GrimoireOptions {
    fn default() -> Self {
        Self {
            json_mode: false,
            plan_configs: false,
            model_family: ModelFamily::Auto,
            tune_mode: false,
            suite_mode: false,
            write_mode: false,
            apply_spec: None,
            guard_mode: None,
        }
    }
}

/// Full grimoire run report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GrimoireReport {
    pub version: &'static str,
    pub ready: bool,
    pub store_path: String,
    pub active_galaxies: Vec<GalaxySummary>,
    pub detected_clients: Vec<String>,
    pub planned_clients: Vec<String>,
    pub profile_path: Option<String>,
    pub state_path: Option<String>,
    pub spec_source: Option<String>,
    pub profile: GrimoireProfile,
    pub chapters: Vec<ChapterState>,
    pub steps: Vec<GrimoireStep>,
    pub total_ms: u128,
}

fn read_meminfo_gb() -> Option<u64> {
    let text = std::fs::read_to_string("/proc/meminfo").ok()?;
    let kb: u64 = text
        .lines()
        .find(|l| l.starts_with("MemTotal:"))?
        .split_whitespace()
        .nth(1)?
        .parse()
        .ok()?;
    Some((kb + 524_288) / 1024 / 1024)
}

fn read_kernel_release() -> String {
    std::fs::read_to_string("/proc/sys/kernel/osrelease")
        .map(|s| s.trim().to_string())
        .unwrap_or_else(|_| std::env::consts::OS.to_string())
}

fn estimate_landlock_abi(os: &str, kernel_release: &str, landlock_active: bool) -> Option<u32> {
    if os != "linux" || !landlock_active {
        return None;
    }
    let mut parts = kernel_release.split('.');
    let major: u32 = parts.next()?.parse().ok()?;
    let minor_str = parts.next()?.split(|c: char| !c.is_ascii_digit()).next()?;
    let minor: u32 = minor_str.parse().ok()?;
    let abi = match (major, minor) {
        (7.., _) => 8,
        (6, 15..) => 7,
        (6, 12..=14) => 6,
        (6, 10..=11) => 5,
        (6, 7..=9) => 4,
        (6, 2..=6) => 3,
        (5, 19..) | (6, 0..=1) => 2,
        (5, 13..=18) => 1,
        _ => 0,
    };
    (abi > 0).then_some(abi)
}

fn has_avx2() -> bool {
    #[cfg(target_arch = "x86_64")]
    {
        is_x86_feature_detected!("avx2")
    }
    #[cfg(not(target_arch = "x86_64"))]
    {
        false
    }
}

fn find_executable(name: &str, home: Option<&Path>) -> Option<PathBuf> {
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

fn data_dir_in(home: Option<&Path>) -> Option<PathBuf> {
    if home.is_none() {
        if let Some(xdg) = std::env::var_os("XDG_DATA_HOME") {
            if !xdg.is_empty() {
                return Some(PathBuf::from(xdg).join("whitemagic"));
            }
        }
    }
    home.map(|h| h.join(".local/share/whitemagic"))
}

fn has_tricameral_spores(home: Option<&Path>) -> bool {
    let models_dir = std::env::var_os("WM_MODELS_DIR")
        .map(PathBuf::from)
        .or_else(|| data_dir_in(home).map(|d| d.join("models")));
    let Some(dir) = models_dir else {
        return false;
    };
    let Ok(entries) = std::fs::read_dir(dir) else {
        return false;
    };
    entries
        .flatten()
        .any(|e| e.path().extension().and_then(|s| s.to_str()) == Some("tm7b"))
}

fn probe_wm_sandbox_abi(bin: &Path) -> Option<(bool, u32)> {
    let out = Command::new(bin).arg("--probe").output().ok()?;
    if !out.status.success() {
        return None;
    }
    let val: serde_json::Value = serde_json::from_slice(&out.stdout).ok()?;
    let supported = val
        .get("landlock_supported")
        .and_then(serde_json::Value::as_bool)
        .unwrap_or(false);
    let abi = val
        .get("kernel_landlock_abi")
        .and_then(serde_json::Value::as_u64)
        .and_then(|n| u32::try_from(n).ok())
        .unwrap_or(0);
    Some((supported, abi))
}

/// Probe host capabilities without unsafe syscalls or side effects.
#[must_use]
pub fn probe_host_capabilities(home: Option<&Path>) -> HostCapabilities {
    let os = std::env::consts::OS.to_string();
    let arch = std::env::consts::ARCH.to_string();
    let kernel_release = read_kernel_release();
    let cores = std::thread::available_parallelism().map_or(1, std::num::NonZero::get);
    let ram_gb = read_meminfo_gb().unwrap_or(8);
    let avx2 = has_avx2();
    let neon = arch == "aarch64";
    let lsm_raw = std::fs::read_to_string("/sys/kernel/security/lsm").unwrap_or_default();
    let mut landlock_active = os == "linux" && lsm_raw.split(',').any(|s| s.trim() == "landlock");
    let mut landlock_abi_est = estimate_landlock_abi(&os, &kernel_release, landlock_active);

    let wm_sandbox_bin = find_executable("wm-sandbox", home);
    if os == "linux" {
        if let Some(ref sb) = wm_sandbox_bin {
            if let Some((supported, abi)) = probe_wm_sandbox_abi(sb) {
                landlock_active = supported;
                if supported && abi > 0 {
                    landlock_abi_est = Some(abi);
                }
            }
        }
    }

    let mut local_runtimes = Vec::new();
    for rt in ["ollama", "llama-server", "vllm", "lmstudio"] {
        if find_executable(rt, home).is_some() {
            local_runtimes.push(rt.to_string());
        }
    }
    if find_executable("muninn-engine", home).is_some() || has_tricameral_spores(home) {
        local_runtimes.push("muninn-engine".to_string());
    }

    HostCapabilities {
        os,
        arch,
        kernel_release,
        cores,
        ram_gb,
        has_avx2: avx2,
        has_neon: neon,
        landlock_active,
        landlock_abi_est,
        has_bwrap: find_executable("bwrap", home).is_some(),
        has_wm_sandbox: wm_sandbox_bin.is_some(),
        has_kvm: Path::new("/dev/kvm").exists(),
        has_firecracker: find_executable("firecracker", home).is_some(),
        has_podman: find_executable("podman", home).is_some(),
        has_node: find_executable("node", home).is_some(),
        has_python3: find_executable("python3", home).is_some(),
        has_cargo: find_executable("cargo", home).is_some(),
        local_runtimes,
    }
}

/// Classify hardware tier from probed capabilities.
#[must_use]
pub fn classify_hardware_tier(caps: &HostCapabilities) -> HardwareTier {
    let has_simd = caps.has_avx2 || caps.has_neon;
    if caps.ram_gb < 8 || !has_simd {
        HardwareTier::Micro
    } else if caps.ram_gb >= 24 || (caps.os == "macos" && caps.has_neon && caps.ram_gb >= 16) {
        HardwareTier::Sovereign
    } else {
        HardwareTier::Standard
    }
}

/// Auto-select the strongest qualified Mandala confinement tier for the probed host.
#[must_use]
pub fn select_confinement_plan(caps: &HostCapabilities) -> ConfinementPlan {
    let landlock_ready =
        caps.landlock_active && caps.landlock_abi_est.unwrap_or(0) >= 4 && caps.has_wm_sandbox;

    if landlock_ready && caps.has_bwrap {
        ConfinementPlan {
            tier: ConfinementTier::BwrapLandlock,
            runner_profile: ConfinementTier::BwrapLandlock
                .runner_profile_id()
                .to_string(),
            burst_runner_profile: Some(
                ConfinementTier::LandlockDirect
                    .runner_profile_id()
                    .to_string(),
            ),
            mandala_guard_mode: "advisory".to_string(),
            degraded_reason: None,
        }
    } else if landlock_ready {
        ConfinementPlan {
            tier: ConfinementTier::LandlockDirect,
            runner_profile: ConfinementTier::LandlockDirect
                .runner_profile_id()
                .to_string(),
            burst_runner_profile: None,
            mandala_guard_mode: "advisory".to_string(),
            degraded_reason: Some(
                "bubblewrap (`bwrap`) not installed; `/tmp` scratch remains shared under standalone wm-sandbox"
                    .to_string(),
            ),
        }
    } else if caps.has_bwrap {
        ConfinementPlan {
            tier: ConfinementTier::Bwrap,
            runner_profile: ConfinementTier::Bwrap.runner_profile_id().to_string(),
            burst_runner_profile: None,
            mandala_guard_mode: "advisory".to_string(),
            degraded_reason: Some(
                "Landlock + wm-sandbox unavailable; using namespace-only Bubblewrap profile"
                    .to_string(),
            ),
        }
    } else if caps.has_kvm && caps.has_firecracker {
        ConfinementPlan {
            tier: ConfinementTier::Firecracker,
            runner_profile: ConfinementTier::Firecracker.runner_profile_id().to_string(),
            burst_runner_profile: None,
            mandala_guard_mode: "advisory".to_string(),
            degraded_reason: None,
        }
    } else if caps.has_podman {
        ConfinementPlan {
            tier: ConfinementTier::Podman,
            runner_profile: ConfinementTier::Podman.runner_profile_id().to_string(),
            burst_runner_profile: None,
            mandala_guard_mode: "advisory".to_string(),
            degraded_reason: None,
        }
    } else {
        ConfinementPlan {
            tier: ConfinementTier::PreCommandVfsOnly,
            runner_profile: ConfinementTier::PreCommandVfsOnly
                .runner_profile_id()
                .to_string(),
            burst_runner_profile: None,
            mandala_guard_mode: "advisory".to_string(),
            degraded_reason: Some(format!(
                "No kernel sandbox runner found on {} (install `bwrap` and/or `wm-sandbox` on Linux for kernel-enforced isolation; pre-command + VFS policy gate active only)",
                caps.os
            )),
        }
    }
}

fn manifest_path_field(manifest: Option<&serde_json::Value>, key: &str) -> Option<PathBuf> {
    manifest?
        .get(key)
        .and_then(serde_json::Value::as_str)
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(PathBuf::from)
}

/// Probe installed WhiteMagic Suite components under `home`, `suite_manifest.json`, and `$PATH`.
#[must_use]
pub fn probe_suite_inventory(home: Option<&Path>) -> SuiteInventory {
    let data_dir = data_dir_in(home);
    let manifest: Option<serde_json::Value> = data_dir
        .as_ref()
        .and_then(|d| std::fs::read_to_string(d.join("suite_manifest.json")).ok())
        .and_then(|s| serde_json::from_str(&s).ok());

    let find_str = |bin: &str, manifest_key: Option<&str>| {
        manifest_key
            .and_then(|k| manifest_path_field(manifest.as_ref(), k))
            .filter(|p| p.is_file())
            .or_else(|| find_executable(bin, home))
            .map(|p| p.display().to_string())
    };

    let wm_fast_mcp = manifest_path_field(manifest.as_ref(), "wm_fast_mcp")
        .filter(|p| p.is_file())
        .or_else(|| {
            data_dir
                .as_ref()
                .map(|d| d.join("wm-fast-mcp/mcp-server.mjs"))
                .filter(|p| p.is_file())
        })
        .map(|p| p.display().to_string());

    let mut spores = Vec::new();
    let models_dir = std::env::var_os("WM_MODELS_DIR")
        .map(PathBuf::from)
        .or_else(|| data_dir.as_ref().map(|d| d.join("models")));
    if let Some(dir) = models_dir {
        if let Ok(entries) = std::fs::read_dir(&dir) {
            for ent in entries.flatten() {
                let p = ent.path();
                if p.extension().and_then(|e| e.to_str()) == Some("tm7b") {
                    if let Some(stem) = p.file_stem().and_then(|s| s.to_str()) {
                        spores.push(stem.to_string());
                    }
                }
            }
            spores.sort();
        }
    }

    let agy_kit_installer = manifest_path_field(manifest.as_ref(), "agy_kit_dir")
        .map(|d| d.join("install.sh"))
        .filter(|p| p.is_file())
        .or_else(|| {
            std::env::var_os("WM_AGY_KIT_DIR")
                .map(|d| PathBuf::from(d).join("install.sh"))
                .filter(|p| p.is_file())
        })
        .or_else(|| {
            data_dir
                .as_ref()
                .map(|d| d.join("suite/agy-kit/install.sh"))
                .filter(|p| p.is_file())
        })
        .or_else(|| {
            data_dir
                .as_ref()
                .map(|d| d.join("agy-kit/install.sh"))
                .filter(|p| p.is_file())
        })
        .map(|p| p.display().to_string());

    let mandala_gate_lite = manifest_path_field(manifest.as_ref(), "mandala_dir")
        .and_then(|d| {
            let direct = d.join("gate_lite/ctl.py");
            if direct.is_file() {
                Some(direct)
            } else {
                let nested = d.join("gate-lite/gate_lite/ctl.py");
                nested.is_file().then_some(nested)
            }
        })
        .or_else(|| {
            std::env::var_os("WM_MANDALA_DIR").and_then(|d| {
                let base = PathBuf::from(d);
                let direct = base.join("gate_lite/ctl.py");
                let nested = base.join("gate-lite/gate_lite/ctl.py");
                if direct.is_file() {
                    Some(direct)
                } else if nested.is_file() {
                    Some(nested)
                } else {
                    None
                }
            })
        })
        .or_else(|| {
            data_dir.as_ref().and_then(|d| {
                for rel in [
                    "suite/mandala-gate-lite/gate_lite/ctl.py",
                    "suite/mandala/gate-lite/gate_lite/ctl.py",
                    "mandala-gate-lite/gate_lite/ctl.py",
                ] {
                    let cand = d.join(rel);
                    if cand.is_file() {
                        return Some(cand);
                    }
                }
                None
            })
        })
        .map(|p| p.display().to_string());

    SuiteInventory {
        wm_squeeze: find_str("wm-squeeze", None),
        wm_codegraph: find_str("wm-codegraph", None),
        wm_sandbox: find_str("wm-sandbox", None),
        muninn_engine: find_str("muninn-engine", None),
        wm3_tui: find_str("wm3-tui", Some("wm3_tui_bin")),
        wm4_mcp: find_str("wm4-mcp", Some("wm4_mcp_bin")),
        wm_fast_mcp,
        wm_handoff: find_str("wm-handoff", None),
        wm_cpr_bridge: find_str("wm-cpr-bridge", None),
        wm_sim: find_str("wm-sim", None),
        wm_models: find_str("wm-models", None),
        agy_kit_installer,
        mandala_gate_lite,
        tricameral_spores: spores,
    }
}

fn read_tail_text(path: &Path, max_bytes: u64) -> Option<String> {
    let mut f = std::fs::File::open(path).ok()?;
    let sz = f.metadata().ok()?.len();
    if sz > max_bytes {
        let _ = f.seek(SeekFrom::Start(sz - max_bytes));
    }
    let mut buf = Vec::new();
    f.read_to_end(&mut buf).ok()?;
    Some(String::from_utf8_lossy(&buf).into_owned())
}

/// Inspect local WhiteMagic telemetry & SIM ledgers to produce actionable self-tuning advice.
#[must_use]
pub fn analyze_telemetry_and_tune(
    home: Option<&Path>,
    tier: HardwareTier,
    suite: &SuiteInventory,
    confinement: &ConfinementPlan,
) -> TelemetryTuningSummary {
    let mut summary = TelemetryTuningSummary::default();
    let Some(h) = home else {
        return summary;
    };
    let data_dir = h.join(".local/share/whitemagic");

    // 1. wm_squeeze_stats.jsonl
    let sq_path = std::env::var_os("WM_SQUEEZE_STATS")
        .map(PathBuf::from)
        .unwrap_or_else(|| data_dir.join("wm_squeeze_stats.jsonl"));
    if let Some(txt) = read_tail_text(&sq_path, 65_536) {
        for line in txt.lines() {
            if !line.starts_with('{') {
                continue;
            }
            if let Ok(v) = serde_json::from_str::<serde_json::Value>(line) {
                summary.squeezed_cmds += 1;
                summary.squeeze_raw_bytes += v
                    .get("raw")
                    .and_then(serde_json::Value::as_u64)
                    .unwrap_or(0);
                summary.squeeze_out_bytes += v
                    .get("out")
                    .and_then(serde_json::Value::as_u64)
                    .unwrap_or(0);
            }
        }
        if summary.squeeze_raw_bytes > 0 {
            let saved = summary
                .squeeze_raw_bytes
                .saturating_sub(summary.squeeze_out_bytes);
            summary.squeeze_saved_pct = (saved as f64 * 100.0) / (summary.squeeze_raw_bytes as f64);
        }
    }

    // 2. agy_telemetry.jsonl (spills, host activity, last observed model)
    let tel_path = std::env::var_os("WM_AGY_TELEMETRY")
        .map(PathBuf::from)
        .unwrap_or_else(|| data_dir.join("agy_telemetry.jsonl"));
    if let Some(txt) = read_tail_text(&tel_path, 65_536) {
        for line in txt.lines() {
            if !line.starts_with('{') {
                continue;
            }
            if let Ok(v) = serde_json::from_str::<serde_json::Value>(line) {
                if v.get("event").and_then(serde_json::Value::as_str) == Some("tool_spill") {
                    summary.recent_spills += 1;
                }
                if v.get("host").and_then(serde_json::Value::as_str) == Some("cursor") {
                    summary.recent_cursor_events += 1;
                }
                if let Some(m) = v.get("model").and_then(serde_json::Value::as_str) {
                    if !m.is_empty() {
                        summary.last_observed_model = Some(m.to_string());
                    }
                }
            }
        }
    }

    // 3. sim_ledger.jsonl (recent auto-captured tool failures)
    let sim_path = std::env::var_os("WM_SIM_LEDGER")
        .map(PathBuf::from)
        .unwrap_or_else(|| data_dir.join("sim_ledger.jsonl"));
    if let Some(txt) = read_tail_text(&sim_path, 65_536) {
        for line in txt.lines() {
            if !line.starts_with('{') {
                continue;
            }
            if let Ok(v) = serde_json::from_str::<serde_json::Value>(line) {
                if v.get("event").and_then(serde_json::Value::as_str) == Some("tool_failure") {
                    summary.recent_tool_failures += 1;
                }
            }
        }
    }

    // Concrete tuning recommendations
    if summary.recent_spills >= 3 {
        summary.recommendations.push(format!(
            "Observed {} recent >16KB output spills; prefer `user-wm_fast` `run_checks` (compact) and bounded `read_slices`",
            summary.recent_spills
        ));
    }
    if suite.wm_squeeze.is_none() || suite.wm_fast_mcp.is_none() {
        summary.recommendations.push(
            "Install WhiteMagic Turbo suite (`wm-squeeze` + `wm_fast` MCP) for 50%+ shell/read token reduction"
                .to_string(),
        );
    }
    if tier != HardwareTier::Micro
        && suite.tricameral_spores.is_empty()
        && suite.wm_models.is_some()
    {
        summary.recommendations.push(format!(
            "Host qualifies for {} tier; run `wm-models pull {}` for $0 local routing & Kekkai gates",
            tier.as_str(),
            tier.recommended_tricameral_profile()
        ));
    }
    if let Some(ref reason) = confinement.degraded_reason {
        summary
            .recommendations
            .push(format!("Confinement advisory: {reason}"));
    }
    if summary.recent_tool_failures >= 10 {
        summary.recommendations.push(format!(
            "{} recent tool failures recorded in SIM ledger; run `wm-sim query --include-failures` or `wm-dream` to consolidate patterns",
            summary.recent_tool_failures
        ));
    }

    summary
}

fn classify_model_name(raw: &str) -> ModelFamily {
    let low = raw.to_ascii_lowercase();
    if low.contains("gemini")
        || low.contains("hydrogen")
        || low.contains("neon")
        || low.contains("carbon")
    {
        ModelFamily::Gemini4
    } else if low.contains("claude")
        || low.contains("opus")
        || low.contains("sonnet")
        || low.contains("haiku")
    {
        ModelFamily::Claude4
    } else if low.contains("grok") {
        ModelFamily::Grok4
    } else if low.contains("gpt")
        || low.contains("codex")
        || low.contains("o3")
        || low.contains("o4")
        || low.contains("o1")
    {
        ModelFamily::OpenAiCodex
    } else {
        ModelFamily::LocalSmall
    }
}

fn build_tuning_for_resolved(
    requested: ModelFamily,
    resolved: ModelFamily,
    source: String,
    telemetry: &TelemetryTuningSummary,
) -> AdaptiveModelTuning {
    // Tighten unbounded read clamp automatically if recent spills are elevated
    let spill_tighten = telemetry.recent_spills >= 3;
    let is_neon = source.to_ascii_lowercase().contains("neon");

    match resolved {
        ModelFamily::Gemini4 | ModelFamily::Auto => AdaptiveModelTuning {
            requested_family: requested,
            resolved_family: ModelFamily::Gemini4,
            detection_source: source,
            max_unbounded_read_lines: if spill_tighten { 300 } else { 400 },
            clamp_read_lines: if spill_tighten { 200 } else { 250 },
            wide_jsonl_lines: 50,
            context_warn_tokens: if is_neon { 100_000 } else { 120_000 },
            context_cliff_tokens: if is_neon { 120_000 } else { 200_000 },
            neon_warn_tokens: 100_000,
            neon_rollover_tokens: 120_000,
            turn0_brief_max_bytes: 2_550,
            enable_flip_guard: true,
            recommended_mcp_profile: "cyberbrain".to_string(),
            notes: if is_neon {
                "Neon-only discipline: 100k warn / 120k rollover target, <30s KV TTL cadence, immutable Turn-0, never fork >=80k.".to_string()
            } else {
                "Immutable Turn-0 prefix cache discipline, ping-pong flip guard (>=2 flips), never fork >=80k.".to_string()
            },
        },
        ModelFamily::Claude4 => AdaptiveModelTuning {
            requested_family: requested,
            resolved_family: ModelFamily::Claude4,
            detection_source: source,
            max_unbounded_read_lines: if spill_tighten { 300 } else { 400 },
            clamp_read_lines: 250,
            wide_jsonl_lines: 50,
            context_warn_tokens: 100_000,
            context_cliff_tokens: 170_000,
            neon_warn_tokens: 100_000,
            neon_rollover_tokens: 120_000,
            turn0_brief_max_bytes: 2_550,
            enable_flip_guard: false,
            recommended_mcp_profile: "cyberbrain".to_string(),
            notes: "5-minute prompt-cache TTL awareness; batch reads/searches via wm_fast to maximize cache hits.".to_string(),
        },
        ModelFamily::OpenAiCodex => AdaptiveModelTuning {
            requested_family: requested,
            resolved_family: ModelFamily::OpenAiCodex,
            detection_source: source,
            max_unbounded_read_lines: if spill_tighten { 280 } else { 350 },
            clamp_read_lines: 220,
            wide_jsonl_lines: 50,
            context_warn_tokens: 100_000,
            context_cliff_tokens: 180_000,
            neon_warn_tokens: 100_000,
            neon_rollover_tokens: 120_000,
            turn0_brief_max_bytes: 2_200,
            enable_flip_guard: false,
            recommended_mcp_profile: "cyberbrain".to_string(),
            notes: "Compact diff/apply_patch .env guard, wm-squeeze CoACT shell compression, minimal MCP surface.".to_string(),
        },
        ModelFamily::Grok4 => AdaptiveModelTuning {
            requested_family: requested,
            resolved_family: ModelFamily::Grok4,
            detection_source: source,
            max_unbounded_read_lines: 500,
            clamp_read_lines: 300,
            wide_jsonl_lines: 60,
            context_warn_tokens: 250_000,
            context_cliff_tokens: 400_000,
            neon_warn_tokens: 100_000,
            neon_rollover_tokens: 120_000,
            turn0_brief_max_bytes: 2_550,
            enable_flip_guard: false,
            recommended_mcp_profile: "cyberbrain".to_string(),
            notes: "500K leaf worker profile; isolated git-worktree parallelism with zero local wm3 store contention.".to_string(),
        },
        ModelFamily::LocalSmall => AdaptiveModelTuning {
            requested_family: requested,
            resolved_family: ModelFamily::LocalSmall,
            detection_source: source,
            max_unbounded_read_lines: 180,
            clamp_read_lines: 120,
            wide_jsonl_lines: 30,
            context_warn_tokens: 24_000,
            context_cliff_tokens: 48_000,
            neon_warn_tokens: 100_000,
            neon_rollover_tokens: 120_000,
            turn0_brief_max_bytes: 1_450,
            enable_flip_guard: false,
            recommended_mcp_profile: "minimal".to_string(),
            notes: "Tight context profile: skeleton-first code_graph, <=120L slices, aggressive wm-squeeze compression.".to_string(),
        },
    }
}

/// Resolve adaptive model tuning parameters for a requested model family (or auto-detect).
#[must_use]
pub fn synthesize_model_tuning(
    requested: ModelFamily,
    tier: HardwareTier,
    telemetry: &TelemetryTuningSummary,
) -> AdaptiveModelTuning {
    let (resolved, source) = if requested != ModelFamily::Auto {
        (requested, "explicit --model flag".to_string())
    } else if let Some(ref obs) = telemetry.last_observed_model {
        (
            classify_model_name(obs),
            format!("telemetry last_observed_model ({obs})"),
        )
    } else if tier == HardwareTier::Micro {
        (
            ModelFamily::LocalSmall,
            "hardware tier fallback (micro)".to_string(),
        )
    } else {
        (ModelFamily::Gemini4, "default frontier profile".to_string())
    };
    build_tuning_for_resolved(requested, resolved, source, telemetry)
}

fn read_json_model_field(path: &Path) -> Option<String> {
    let raw = std::fs::read_to_string(path).ok()?;
    let val: serde_json::Value = serde_json::from_str(&raw).ok()?;
    for ptr in ["/model", "/defaultModel", "/agent/model"] {
        if let Some(s) = val.pointer(ptr).and_then(serde_json::Value::as_str) {
            let t = s.trim();
            if !t.is_empty() {
                return Some(t.to_string());
            }
        }
    }
    None
}

fn read_toml_top_model_field(path: &Path) -> Option<String> {
    let raw = std::fs::read_to_string(path).ok()?;
    let mut in_section = false;
    for line in raw.lines() {
        let trimmed = line.split('#').next().unwrap_or("").trim();
        if trimmed.is_empty() {
            continue;
        }
        if trimmed.starts_with('[') && trimmed.ends_with(']') {
            in_section = true;
            continue;
        }
        if !in_section {
            if let Some(rest) = trimmed.strip_prefix("model") {
                let rest = rest.trim_start();
                if let Some(val) = rest.strip_prefix('=') {
                    let unquoted = val.trim().trim_matches('"').trim_matches('\'').trim();
                    if !unquoted.is_empty() {
                        return Some(unquoted.to_string());
                    }
                }
            }
        }
    }
    None
}

fn read_jsonc_model_field(path: &Path) -> Option<String> {
    let raw = std::fs::read_to_string(path).ok()?;
    for line in raw.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("//") {
            continue;
        }
        if let Some(idx) = trimmed.find("\"model\"") {
            let after = &trimmed[idx + 7..];
            if let Some(colon) = after.find(':') {
                let val = after[colon + 1..].trim().trim_end_matches(',').trim();
                let unquoted = val.trim_matches('"');
                if !unquoted.is_empty() && !unquoted.starts_with('{') {
                    return Some(unquoted.to_string());
                }
            }
        }
    }
    None
}

/// Synthesize per-host adaptive model tuning across AGY, Codex, Cursor, OpenCode, Claude, and TUI.
#[must_use]
pub fn synthesize_host_profiles(
    home: Option<&Path>,
    requested: ModelFamily,
    caps: &HostCapabilities,
    tier: HardwareTier,
    telemetry: &TelemetryTuningSummary,
) -> BTreeMap<String, AdaptiveModelTuning> {
    let has_local = !caps.local_runtimes.is_empty();
    let hosts = ["agy", "codex", "cursor", "claude", "opencode", "tui"];
    let mut map = BTreeMap::new();

    for host in hosts {
        let (resolved, source) = if requested != ModelFamily::Auto {
            (requested, "explicit --model override".to_string())
        } else {
            match host {
                "agy" => {
                    if let Some(m) = home.and_then(|h| {
                        read_json_model_field(&h.join(".gemini/antigravity-cli/settings.json"))
                    }) {
                        (classify_model_name(&m), format!("agy settings.json ({m})"))
                    } else if let Some(ref obs) = telemetry.last_observed_model {
                        (classify_model_name(obs), format!("telemetry ({obs})"))
                    } else {
                        (ModelFamily::Gemini4, "agy host default".to_string())
                    }
                }
                "codex" => {
                    if let Some(m) =
                        home.and_then(|h| read_toml_top_model_field(&h.join(".codex/config.toml")))
                    {
                        (classify_model_name(&m), format!("codex config.toml ({m})"))
                    } else {
                        (ModelFamily::OpenAiCodex, "codex host default".to_string())
                    }
                }
                "cursor" => {
                    if let Some(m) =
                        home.and_then(|h| read_json_model_field(&h.join(".cursor/cli-config.json")))
                    {
                        (classify_model_name(&m), format!("cursor cli-config ({m})"))
                    } else if telemetry.recent_cursor_events > 0 {
                        if let Some(ref obs) = telemetry.last_observed_model {
                            (
                                classify_model_name(obs),
                                format!("cursor telemetry ({obs})"),
                            )
                        } else {
                            (ModelFamily::Claude4, "cursor host default".to_string())
                        }
                    } else {
                        (ModelFamily::Claude4, "cursor host default".to_string())
                    }
                }
                "claude" => {
                    if let Some(m) =
                        home.and_then(|h| read_json_model_field(&h.join(".claude/settings.json")))
                    {
                        (classify_model_name(&m), format!("claude settings ({m})"))
                    } else {
                        (ModelFamily::Claude4, "claude host default".to_string())
                    }
                }
                "opencode" => {
                    if let Some(m) = home.and_then(|h| {
                        read_jsonc_model_field(&h.join(".config/opencode/opencode.jsonc"))
                    }) {
                        (classify_model_name(&m), format!("opencode.jsonc ({m})"))
                    } else if has_local || tier == HardwareTier::Micro {
                        (
                            ModelFamily::LocalSmall,
                            "opencode local runtime fallback".to_string(),
                        )
                    } else {
                        (ModelFamily::Claude4, "opencode host default".to_string())
                    }
                }
                "tui" => {
                    if has_local {
                        (
                            ModelFamily::LocalSmall,
                            format!(
                                "local runtime detected ({})",
                                caps.local_runtimes.join(", ")
                            ),
                        )
                    } else {
                        (ModelFamily::Gemini4, "wm3-tui default".to_string())
                    }
                }
                _ => (ModelFamily::Gemini4, "default".to_string()),
            }
        };
        map.insert(
            host.to_string(),
            build_tuning_for_resolved(requested, resolved, source, telemetry),
        );
    }

    map
}

fn strip_toml_comment(line: &str) -> String {
    let mut out = String::new();
    let mut in_quotes = false;
    let mut escape = false;
    for ch in line.chars() {
        if escape {
            out.push(ch);
            escape = false;
            continue;
        }
        if ch == '\\' && in_quotes {
            out.push(ch);
            escape = true;
            continue;
        }
        if ch == '"' {
            in_quotes = !in_quotes;
            out.push(ch);
            continue;
        }
        if ch == '#' && !in_quotes {
            break;
        }
        out.push(ch);
    }
    out
}

fn parse_toml_string_array(raw: &str) -> Vec<String> {
    let inner = raw.trim().trim_start_matches('[').trim_end_matches(']');
    inner
        .split(',')
        .map(|part| part.trim().trim_matches('"').trim_matches('\'').trim())
        .filter(|s| !s.is_empty())
        .map(str::to_string)
        .collect()
}

/// Zero-dependency parser for `.wm-grimoire.toml` / `grimoire.toml` or `.json`.
pub fn parse_grimoire_spec_str(raw: &str, is_json: bool) -> Result<GrimoireSpec, String> {
    if is_json || raw.trim_start().starts_with('{') {
        return serde_json::from_str::<GrimoireSpec>(raw)
            .map_err(|e| format!("invalid Grimoire JSON spec: {e}"));
    }

    let mut spec = GrimoireSpec::default();
    let mut buf = String::new();
    for line in raw.lines() {
        let clean = strip_toml_comment(line);
        let trimmed = clean.trim();
        if trimmed.is_empty() {
            continue;
        }
        buf.push_str(trimmed);
        // Handle multi-line arrays like clients = [\n "cursor",\n]
        let open_brackets = buf.matches('[').count();
        let close_brackets = buf.matches(']').count();
        if buf.contains('=') && open_brackets > close_brackets {
            buf.push(' ');
            continue;
        }
        let stmt = buf.trim().to_string();
        buf.clear();

        if stmt.starts_with('[') && stmt.ends_with(']') {
            continue;
        }
        let Some((raw_k, raw_v)) = stmt.split_once('=') else {
            continue;
        };
        let key = raw_k.trim();
        let val = raw_v.trim();
        let unquoted = val.trim_matches('"').trim_matches('\'').trim();

        match key {
            "profile" => spec.profile = (!unquoted.is_empty()).then(|| unquoted.to_string()),
            "model" => spec.model = (!unquoted.is_empty()).then(|| unquoted.to_string()),
            "mandala_guard" => {
                spec.mandala_guard = (!unquoted.is_empty()).then(|| unquoted.to_string());
            }
            "confinement" => {
                spec.confinement = (!unquoted.is_empty()).then(|| unquoted.to_string())
            }
            "clients" => spec.clients = Some(parse_toml_string_array(val)),
            "readonly_clients" => spec.readonly_clients = Some(parse_toml_string_array(val)),
            "mcp_profile" => {
                spec.mcp_profile = (!unquoted.is_empty()).then(|| unquoted.to_string())
            }
            "clamp_read_lines" => spec.clamp_read_lines = unquoted.parse::<usize>().ok(),
            "max_unbounded_read_lines" => {
                spec.max_unbounded_read_lines = unquoted.parse::<usize>().ok();
            }
            "wide_jsonl_lines" => spec.wide_jsonl_lines = unquoted.parse::<usize>().ok(),
            "galaxy" => spec.galaxy = (!unquoted.is_empty()).then(|| unquoted.to_string()),
            _ => {}
        }
    }
    Ok(spec)
}

fn load_grimoire_spec_from_path(path: &Path) -> Result<GrimoireSpec, String> {
    let raw = std::fs::read_to_string(path)
        .map_err(|e| format!("failed reading Grimoire spec {}: {e}", path.display()))?;
    let is_json = path
        .extension()
        .and_then(|s| s.to_str())
        .is_some_and(|e| e.eq_ignore_ascii_case("json"));
    parse_grimoire_spec_str(&raw, is_json)
}

fn write_json_atomic<T: Serialize>(
    home: Option<&Path>,
    filename: &str,
    payload: &T,
) -> Result<PathBuf, String> {
    let dir = data_dir_in(home).ok_or_else(|| format!("cannot resolve data dir for {filename}"))?;
    std::fs::create_dir_all(&dir)
        .map_err(|e| format!("failed to create {}: {e}", dir.display()))?;
    let dst = dir.join(filename);
    let tmp = dir.join(format!("{filename}.tmp.{}", std::process::id()));
    let body =
        serde_json::to_string_pretty(payload).map_err(|e| format!("JSON serialize failed: {e}"))?;
    std::fs::write(&tmp, format!("{body}\n"))
        .map_err(|e| format!("failed writing {}: {e}", tmp.display()))?;
    std::fs::rename(&tmp, &dst).map_err(|e| format!("failed committing {}: {e}", dst.display()))?;
    Ok(dst)
}

fn append_tune_sim_record(
    home: Option<&Path>,
    clamp: usize,
    max_unbounded: usize,
    recent_spills: usize,
) {
    let sim_path = std::env::var_os("WM_SIM_LEDGER")
        .map(PathBuf::from)
        .or_else(|| data_dir_in(home).map(|d| d.join("sim_ledger.jsonl")));
    let Some(path) = sim_path else {
        return;
    };
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| d.as_secs());
    let entry = serde_json::json!({
        "ts": ts,
        "event": "grimoire_tune",
        "domain": "grimoire-self-tune",
        "status": "kept",
        "observed": format!("clamp_read_lines={clamp}, max_unbounded_read_lines={max_unbounded}, recent_spills={recent_spills}"),
    });
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
    {
        use std::io::Write as _;
        let _ = writeln!(f, "{entry}");
    }
}

/// Detects known AI coding agent configurations on the local machine using the canonical registry.
#[must_use]
pub fn detect_coding_agents() -> Vec<(&'static str, PathBuf)> {
    let home = std::env::var("HOME").ok().map(PathBuf::from);
    detect_coding_agents_in(home.as_deref())
}

/// Detects known AI coding agent configurations under an explicit home directory.
#[must_use]
pub fn detect_coding_agents_in(home: Option<&Path>) -> Vec<(&'static str, PathBuf)> {
    let Some(h) = home else {
        return Vec::new();
    };
    setup::specs_in(Some(h))
        .into_iter()
        .filter(|spec| setup::installed_in(Some(h), spec))
        .map(|spec| (spec.label, spec.config_path))
        .collect()
}

/// Computes single-writer assignment across detected client specs:
/// preserves an already-writable client if present, otherwise picks the first detected client
/// as primary writer and marks all remaining clients `--readonly`.
fn compute_single_writer_plan(specs: &[ClientSpec]) -> (Option<String>, Vec<String>, Vec<String>) {
    let mut primary: Option<String> = None;
    let mut secondaries = Vec::new();
    let mut turbo_hosts = Vec::new();

    for spec in specs {
        let host_key = match spec.id {
            "antigravity" => Some("agy"),
            "cursor" => Some("cursor"),
            "codex" => Some("codex"),
            _ => None,
        };
        if let Some(key) = host_key {
            if !turbo_hosts.iter().any(|h| h == key) {
                turbo_hosts.push(key.to_string());
            }
        }
        if primary.is_none() && setup::has_active_writable_whitemagic_server(spec) {
            primary = Some(spec.label.to_string());
        }
    }

    if primary.is_none() {
        if let Some(first) = specs.first() {
            primary = Some(first.label.to_string());
        }
    }

    for spec in specs {
        if primary.as_deref() != Some(spec.label) {
            secondaries.push(spec.label.to_string());
        }
    }

    (primary, secondaries, turbo_hosts)
}

/// Builds a dry-run plan for detected client config targets. Never writes files.
#[must_use]
pub fn plan_client_configs(agents: &[(&'static str, PathBuf)]) -> Vec<String> {
    agents
        .iter()
        .map(|(name, path)| format!("{name} -> {} (plan only; no file modified)", path.display()))
        .collect()
}

fn write_profile_atomic(home: Option<&Path>, profile: &GrimoireProfile) -> Result<PathBuf, String> {
    write_json_atomic(home, "grimoire_profile.json", profile)
}

/// Optional dispatch of `whitemagic-agy-kit/install.sh --hosts <detected>` when `--write --suite` is used.
pub fn dispatch_suite_wiring(profile: &GrimoireProfile, plan_only: bool) -> Result<String, String> {
    if profile.turbo_hosts.is_empty() {
        return Ok("No turbo-supported IDE hosts (agy/cursor/codex) detected.".to_string());
    }
    let hosts_csv = profile.turbo_hosts.join(",");
    let Some(ref installer) = profile.suite.agy_kit_installer else {
        return Ok(format!(
            "Turbo installer not found locally (set WM_AGY_KIT_DIR or install whitemagic-suite to wire --hosts {hosts_csv})."
        ));
    };
    if plan_only {
        return Ok(format!(
            "Planned suite command: WM_SKIP_CARGO=1 bash \"{installer}\" --hosts {hosts_csv}"
        ));
    }
    let out = Command::new("bash")
        .arg(installer)
        .arg("--hosts")
        .arg(&hosts_csv)
        .env("WM_SKIP_CARGO", "1")
        .output()
        .map_err(|e| format!("failed invoking suite installer {installer}: {e}"))?;
    if !out.status.success() {
        let stderr = String::from_utf8_lossy(&out.stderr);
        return Err(format!(
            "suite installer failed (status={}): {}",
            out.status,
            stderr.trim()
        ));
    }
    Ok(format!(
        "Wired WhiteMagic Turbo suite for hosts={hosts_csv} via {installer}"
    ))
}

/// Executes the complete `wm grimoire` pass (backwards-compatible entry point).
pub fn run_grimoire(
    store_path: &Path,
    json_mode: bool,
    plan_configs: bool,
) -> Result<GrimoireReport, String> {
    let opts = GrimoireOptions {
        json_mode,
        plan_configs,
        ..GrimoireOptions::default()
    };
    run_grimoire_with_options(store_path, &opts)
}

/// Executes `wm grimoire` with explicit adaptive options.
pub fn run_grimoire_with_options(
    store_path: &Path,
    opts: &GrimoireOptions,
) -> Result<GrimoireReport, String> {
    let home = std::env::var("HOME").ok().map(PathBuf::from);
    run_grimoire_with_home_and_options(store_path, home.as_deref(), opts)
}

/// Executes the grimoire pass against an explicit home directory (backwards-compatible testable core).
pub fn run_grimoire_with_home(
    store_path: &Path,
    json_mode: bool,
    plan_configs: bool,
    home: Option<&Path>,
) -> Result<GrimoireReport, String> {
    let opts = GrimoireOptions {
        json_mode,
        plan_configs,
        ..GrimoireOptions::default()
    };
    run_grimoire_with_home_and_options(store_path, home, &opts)
}

/// Full testable adaptive grimoire engine with explicit home and options.
pub fn run_grimoire_with_home_and_options(
    store_path: &Path,
    home: Option<&Path>,
    opts: &GrimoireOptions,
) -> Result<GrimoireReport, String> {
    let start_all = Instant::now();
    let mut steps = Vec::new();
    let mut ready = true;

    // ----------------------------------------------------
    // Step 1: Host Environment & Hardware Tier
    // ----------------------------------------------------
    let t0 = Instant::now();
    let caps = probe_host_capabilities(home);
    let hw_tier = classify_hardware_tier(&caps);
    let simd_desc = if caps.has_neon {
        "NEON: true"
    } else if caps.has_avx2 {
        "AVX2: true"
    } else {
        "SIMD: basic"
    };
    let host_detail = format!(
        "{} {} (kernel {}) · {} cores · {} GB RAM · {} · Tier: {}",
        caps.os,
        caps.arch,
        caps.kernel_release,
        caps.cores,
        caps.ram_gb,
        simd_desc,
        hw_tier.as_str()
    );
    steps.push(GrimoireStep {
        name: "host",
        status: StepStatus::Ok,
        summary: format!("Host supported ({} tier)", hw_tier.as_str()),
        detail: host_detail,
        elapsed_ms: t0.elapsed().as_millis(),
    });

    // ----------------------------------------------------
    // Step 2: Mandala Confinement Capability Selection
    // ----------------------------------------------------
    let t_conf = Instant::now();
    let mut confinement = select_confinement_plan(&caps);
    let spec_opt = if let Some(ref spec_path) = opts.apply_spec {
        Some((
            spec_path.display().to_string(),
            load_grimoire_spec_from_path(spec_path)?,
        ))
    } else {
        None
    };

    if let Some(ref gmode) = opts.guard_mode {
        let gm = gmode.trim().to_ascii_lowercase();
        if matches!(gm.as_str(), "advisory" | "strict" | "off") {
            confinement.mandala_guard_mode = gm;
        }
    } else if let Some((_, ref spec)) = spec_opt {
        if let Some(ref gm) = spec.mandala_guard {
            let low = gm.trim().to_ascii_lowercase();
            if matches!(low.as_str(), "advisory" | "strict" | "off") {
                confinement.mandala_guard_mode = low;
            }
        }
    }
    if let Some((_, ref spec)) = spec_opt {
        if let Some(ref conf) = spec.confinement {
            let c = conf.trim();
            if !c.is_empty() {
                confinement.runner_profile = c.to_string();
            }
        }
    }
    let (conf_status, conf_summary, conf_detail) =
        if let Some(ref deg) = confinement.degraded_reason {
            (
                StepStatus::Warn,
                format!(
                    "Confinement profile: {} (degraded)",
                    confinement.runner_profile
                ),
                deg.clone(),
            )
        } else {
            let burst = confinement
                .burst_runner_profile
                .as_deref()
                .map(|b| format!(" · burst fast-path: {b}"))
                .unwrap_or_default();
            (
                StepStatus::Ok,
                format!("Confinement profile: {}", confinement.runner_profile),
                format!(
                    "Landlock={} (ABI≈{}) · bwrap={} · wm-sandbox={} · kvm={}{}",
                    caps.landlock_active,
                    caps.landlock_abi_est.unwrap_or(0),
                    caps.has_bwrap,
                    caps.has_wm_sandbox,
                    caps.has_kvm,
                    burst
                ),
            )
        };
    steps.push(GrimoireStep {
        name: "confinement",
        status: conf_status,
        summary: conf_summary,
        detail: conf_detail,
        elapsed_ms: t_conf.elapsed().as_millis(),
    });

    // ----------------------------------------------------
    // Step 3: WhiteMagic Suite Inventory
    // ----------------------------------------------------
    let t_suite = Instant::now();
    let suite = probe_suite_inventory(home);
    let present_count = [
        suite.wm_squeeze.is_some(),
        suite.wm_codegraph.is_some(),
        suite.wm_sandbox.is_some(),
        suite.muninn_engine.is_some(),
        suite.wm3_tui.is_some(),
        suite.wm_fast_mcp.is_some(),
        suite.wm_handoff.is_some(),
        suite.wm_cpr_bridge.is_some(),
        suite.wm_sim.is_some(),
    ]
    .into_iter()
    .filter(|&b| b)
    .count();
    let suite_detail = format!(
        "squeeze={} · codegraph={} · sandbox={} · muninn={} · tui={} · wm_fast={} · spores={}",
        suite.wm_squeeze.is_some(),
        suite.wm_codegraph.is_some(),
        suite.wm_sandbox.is_some(),
        suite.muninn_engine.is_some(),
        suite.wm3_tui.is_some(),
        suite.wm_fast_mcp.is_some(),
        suite.tricameral_spores.len()
    );
    steps.push(GrimoireStep {
        name: "suite_inventory",
        status: if present_count >= 4 {
            StepStatus::Ok
        } else {
            StepStatus::Warn
        },
        summary: format!(
            "Suite components detected: {present_count}/9 (recommended Tricameral: {})",
            hw_tier.recommended_tricameral_profile()
        ),
        detail: suite_detail,
        elapsed_ms: t_suite.elapsed().as_millis(),
    });

    // ----------------------------------------------------
    // Step 4: Substrate Store Provisioning
    // ----------------------------------------------------
    let t1 = Instant::now();
    let store_existed = store_path.exists();
    if !store_existed && !opts.plan_configs {
        std::fs::create_dir_all(store_path)
            .map_err(|e| format!("Failed to create store dir: {e}"))?;
    }

    let journal_path = store_path.join("journal.jsonl");
    let (mut substrate_opt, was_readonly) = if opts.plan_configs {
        if store_existed && store_path.join("data.mdb").exists() {
            match Substrate::open_readonly(store_path, Some(&journal_path), default_view()) {
                Ok(ro_sub) => (Some(ro_sub), true),
                Err(_) => (None, true),
            }
        } else {
            (None, true)
        }
    } else if store_existed {
        match Substrate::open_readonly(store_path, Some(&journal_path), default_view()) {
            Ok(ro_sub) => {
                let cnt = ro_sub.store().record_count().unwrap_or(0);
                if cnt > 0 {
                    (Some(ro_sub), true)
                } else {
                    drop(ro_sub);
                    let rw = Substrate::open(store_path, Some(&journal_path), default_view())
                        .map_err(|e| {
                            format!("Failed to open substrate store for initialization: {e}")
                        })?;
                    (Some(rw), false)
                }
            }
            Err(_) => {
                let rw = Substrate::open(store_path, Some(&journal_path), default_view())
                    .map_err(|e| format!("Failed to open substrate store: {e}"))?;
                (Some(rw), false)
            }
        }
    } else {
        let rw = Substrate::open(store_path, Some(&journal_path), default_view())
            .map_err(|e| format!("Failed to open new substrate store: {e}"))?;
        (Some(rw), false)
    };

    let initial_count = substrate_opt
        .as_ref()
        .and_then(|s| s.store().record_count().ok())
        .unwrap_or(0);
    let current_epoch = substrate_opt
        .as_ref()
        .and_then(|s| s.store().epoch().ok())
        .unwrap_or(0);
    steps.push(GrimoireStep {
        name: "substrate",
        status: StepStatus::Ok,
        summary: if opts.plan_configs && substrate_opt.is_none() {
            "Sovereign LMDB substrate planned (read-only dry run)".to_string()
        } else {
            "Sovereign LMDB substrate active".to_string()
        },
        detail: format!(
            "Path: {} (Epoch {}, Records: {}, Mode: {})",
            store_path.display(),
            current_epoch,
            initial_count,
            if opts.plan_configs {
                "PlanOnly/ReadOnly"
            } else if was_readonly {
                "ReadOnly/Shared"
            } else {
                "ReadWrite"
            }
        ),
        elapsed_ms: t1.elapsed().as_millis(),
    });

    // ----------------------------------------------------
    // Step 5: Starter Guide Galaxy Seeding & Surface
    // ----------------------------------------------------
    let t2 = Instant::now();
    let mut seeded = 0;
    if !opts.plan_configs && !was_readonly && initial_count == 0 {
        if let Some(ref mut substrate) = substrate_opt {
            seeded = seed_starter_guide_if_empty(substrate)
                .map_err(|e| format!("Failed seeding starter guide: {e}"))?;
        }
    }

    let galaxies = substrate_opt
        .as_ref()
        .and_then(|s| list_galaxies(s).ok())
        .unwrap_or_default();
    let guide_galaxy = galaxies.iter().find(|g| g.name == "guide");

    let (guide_status, guide_summary, guide_detail) = if let Some(g) = guide_galaxy {
        (
            StepStatus::Ok,
            format!("Starter 'guide' galaxy active ({} records)", g.record_count),
            if seeded > 0 {
                format!("Genesis seed initialized with {seeded} foundational guide records.")
            } else {
                format!(
                    "Existing guide galaxy verified with {} records.",
                    g.record_count
                )
            },
        )
    } else if opts.plan_configs {
        (
            StepStatus::Skip,
            "Starter 'guide' galaxy planned (skipped in --plan mode)".to_string(),
            "Run 'wm grimoire' without --plan to seed starter guide records.".to_string(),
        )
    } else {
        (
            StepStatus::Warn,
            "Starter 'guide' galaxy not present".to_string(),
            "Run 'wm galaxy create guide' to establish the starter namespace.".to_string(),
        )
    };

    steps.push(GrimoireStep {
        name: "starter_galaxy",
        status: guide_status,
        summary: guide_summary,
        detail: guide_detail,
        elapsed_ms: t2.elapsed().as_millis(),
    });

    // ----------------------------------------------------
    // Step 6: Unified Coding Agent Detection & Single-Writer Plan
    // ----------------------------------------------------
    let t3 = Instant::now();
    let installed_specs: Vec<ClientSpec> = home.map_or_else(Vec::new, |h| {
        setup::specs_in(Some(h))
            .into_iter()
            .filter(|s| setup::installed_in(Some(h), s))
            .collect()
    });
    let agents: Vec<(&'static str, PathBuf)> = installed_specs
        .iter()
        .map(|s| (s.label, s.config_path.clone()))
        .collect();
    let detected_names: Vec<String> = agents.iter().map(|(n, _)| (*n).to_string()).collect();
    let (primary_writer, secondary_readonly, turbo_hosts) =
        compute_single_writer_plan(&installed_specs);
    let planned_clients = if opts.plan_configs {
        plan_client_configs(&agents)
    } else {
        Vec::new()
    };

    let agent_detail = if detected_names.is_empty() {
        "No standard AI agent IDE directories detected in user home.".to_string()
    } else {
        format!(
            "Detected {} clients: {} · primary writer: {} · readonly secondaries: [{}] · turbo hosts: [{}]",
            detected_names.len(),
            detected_names.join(", "),
            primary_writer.as_deref().unwrap_or("none"),
            secondary_readonly.join(", "),
            turbo_hosts.join(", ")
        )
    };

    steps.push(GrimoireStep {
        name: "agent_clients",
        status: StepStatus::Ok,
        summary: format!(
            "Agent detection: {} environments found",
            detected_names.len()
        ),
        detail: agent_detail,
        elapsed_ms: t3.elapsed().as_millis(),
    });

    // ----------------------------------------------------
    // Step 7 & 8: Telemetry Self-Tuning & Adaptive Model Profile
    // ----------------------------------------------------
    let t_adapt = Instant::now();
    let telemetry = analyze_telemetry_and_tune(home, hw_tier, &suite, &confinement);
    let effective_requested = if opts.model_family != ModelFamily::Auto {
        opts.model_family
    } else if let Some((_, ref spec)) = spec_opt {
        spec.model
            .as_deref()
            .and_then(ModelFamily::parse)
            .unwrap_or(ModelFamily::Auto)
    } else {
        ModelFamily::Auto
    };
    let mut model_tuning = synthesize_model_tuning(effective_requested, hw_tier, &telemetry);
    let mut host_profiles =
        synthesize_host_profiles(home, effective_requested, &caps, hw_tier, &telemetry);

    if let Some((_, ref spec)) = spec_opt {
        let apply_overrides = |t: &mut AdaptiveModelTuning| {
            if let Some(v) = spec.clamp_read_lines {
                t.clamp_read_lines = v.clamp(20, 1000);
            }
            if let Some(v) = spec.max_unbounded_read_lines {
                t.max_unbounded_read_lines = v.clamp(50, 2000);
            }
            if let Some(v) = spec.wide_jsonl_lines {
                t.wide_jsonl_lines = v.clamp(10, 500);
            }
            if let Some(ref p) = spec.mcp_profile {
                t.recommended_mcp_profile = p.clone();
            }
        };
        apply_overrides(&mut model_tuning);
        for val in host_profiles.values_mut() {
            apply_overrides(val);
        }
    }

    if opts.tune_mode && opts.write_mode && !opts.plan_configs && telemetry.recent_spills >= 3 {
        let tighten = |t: &mut AdaptiveModelTuning| {
            t.clamp_read_lines = t
                .clamp_read_lines
                .saturating_mul(3)
                .saturating_div(4)
                .max(80);
            t.max_unbounded_read_lines = t
                .max_unbounded_read_lines
                .saturating_mul(4)
                .saturating_div(5)
                .max(150);
        };
        tighten(&mut model_tuning);
        for val in host_profiles.values_mut() {
            tighten(val);
        }
        append_tune_sim_record(
            home,
            model_tuning.clamp_read_lines,
            model_tuning.max_unbounded_read_lines,
            telemetry.recent_spills,
        );
    }

    let profile = GrimoireProfile {
        schema: "wm-grimoire-profile/1.1",
        grimoire_version: env!("CARGO_PKG_VERSION"),
        capabilities: caps,
        hardware_tier: hw_tier,
        recommended_tricameral_profile: hw_tier.recommended_tricameral_profile().to_string(),
        confinement,
        model_tuning: model_tuning.clone(),
        host_profiles,
        suite,
        primary_writer_client: primary_writer,
        secondary_readonly_clients: secondary_readonly,
        turbo_hosts,
        telemetry: telemetry.clone(),
    };

    let profile_path = if opts.plan_configs {
        None
    } else {
        write_profile_atomic(home, &profile)
            .ok()
            .map(|p| p.display().to_string())
    };

    steps.push(GrimoireStep {
        name: "model_adaptation",
        status: StepStatus::Ok,
        summary: format!(
            "Model profile: {} (unbounded read >{}L → {}L, wide JSONL → {}L)",
            model_tuning.resolved_family.as_str(),
            model_tuning.max_unbounded_read_lines,
            model_tuning.clamp_read_lines,
            model_tuning.wide_jsonl_lines
        ),
        detail: format!(
            "Source: {} · MCP profile: {} · Profile file: {}",
            model_tuning.detection_source,
            model_tuning.recommended_mcp_profile,
            profile_path.as_deref().unwrap_or("not written (--plan)")
        ),
        elapsed_ms: t_adapt.elapsed().as_millis(),
    });

    let t_tune = Instant::now();
    let tune_summary = if telemetry.squeezed_cmds > 0 {
        format!(
            "Squeezed {} cmds ({:.1}% saved) · {} spills · {} failures · {} advice item(s)",
            telemetry.squeezed_cmds,
            telemetry.squeeze_saved_pct,
            telemetry.recent_spills,
            telemetry.recent_tool_failures,
            telemetry.recommendations.len()
        )
    } else {
        format!(
            "Telemetry ready (0 squeezed cmds logged yet; {} advice item(s))",
            telemetry.recommendations.len()
        )
    };
    let tune_detail = if telemetry.recommendations.is_empty() {
        "All monitored efficiency signals are within healthy thresholds.".to_string()
    } else {
        telemetry.recommendations.join(" | ")
    };
    steps.push(GrimoireStep {
        name: "telemetry_tune",
        status: if telemetry.recent_spills >= 3 {
            StepStatus::Warn
        } else {
            StepStatus::Ok
        },
        summary: tune_summary,
        detail: tune_detail,
        elapsed_ms: t_tune.elapsed().as_millis(),
    });

    // ----------------------------------------------------
    // Step 9: Sub-Microsecond Retrieval Verification
    // ----------------------------------------------------
    let t4 = Instant::now();
    let q = wm_gen3_core::ops::RecallQuery {
        query: "WhiteMagic".to_string(),
        limit: 3,
        candidate_limit: 10,
        include_historical: false,
        min_score: 0.0,
        min_coverage: 0.0,
        scope: None,
        adaptive: false,
        resonance: false,
        resonance_hops: 2,
    };

    let verify_start = Instant::now();
    let hits = substrate_opt
        .as_mut()
        .and_then(|s| s.recall(&q).ok())
        .unwrap_or_default();
    let verify_us = verify_start.elapsed().as_micros();

    let (verif_status, verif_summary, verif_detail) = if !hits.is_empty() {
        (
            StepStatus::Ok,
            format!("Retrieval hot-path verified in {verify_us} µs"),
            format!(
                "Query 'WhiteMagic' yielded {} hits; top rank: '{}'",
                hits.len(),
                hits[0].source
            ),
        )
    } else if initial_count > 0 || seeded > 0 {
        (
            StepStatus::Warn,
            format!("Query returned 0 hits in {verify_us} µs"),
            "Store indexed but query term did not match candidate pool.".to_string(),
        )
    } else {
        (
            StepStatus::Ok,
            "Fresh store ready for first intake".to_string(),
            "Run 'wm remember' or talk to your agent to record your first memory.".to_string(),
        )
    };

    steps.push(GrimoireStep {
        name: "verification",
        status: verif_status,
        summary: verif_summary.clone(),
        detail: verif_detail,
        elapsed_ms: t4.elapsed().as_millis(),
    });

    for s in &steps {
        if s.status == StepStatus::Fail {
            ready = false;
        }
    }

    let chapters = vec![
        ChapterState {
            id: "awakening",
            roman: "I",
            title: "Awakening",
            status: if present_count >= 4 {
                StepStatus::Ok
            } else {
                StepStatus::Warn
            },
            detail: format!(
                "{} {} ({} suite components detected)",
                profile.capabilities.os, profile.capabilities.arch, present_count
            ),
        },
        ChapterState {
            id: "binding",
            roman: "II",
            title: "Binding",
            status: if detected_names.is_empty() {
                StepStatus::Skip
            } else {
                StepStatus::Ok
            },
            detail: if detected_names.is_empty() {
                "No client configs found yet".to_string()
            } else {
                format!(
                    "{} client(s) detected; turbo={:?}",
                    detected_names.len(),
                    profile.turbo_hosts
                )
            },
        },
        ChapterState {
            id: "memory",
            roman: "III",
            title: "Memory",
            status: verif_status,
            detail: verif_summary.clone(),
        },
        ChapterState {
            id: "library",
            roman: "IV",
            title: "Library",
            status: if initial_count > 0 || seeded > 0 || guide_galaxy.is_some() {
                StepStatus::Ok
            } else {
                guide_status
            },
            detail: format!(
                "{} records across {} galaxy/galaxies",
                initial_count.max(seeded),
                galaxies.len()
            ),
        },
        ChapterState {
            id: "ward",
            roman: "V",
            title: "Ward",
            status: conf_status,
            detail: format!(
                "{} (guard={})",
                profile.confinement.runner_profile, profile.confinement.mandala_guard_mode
            ),
        },
        ChapterState {
            id: "mirror",
            roman: "VI",
            title: "Mirror",
            status: if profile.suite.wm_cpr_bridge.is_some() {
                StepStatus::Ok
            } else {
                StepStatus::Warn
            },
            detail: if profile.suite.wm_cpr_bridge.is_some() {
                "wm-cpr-bridge + atomic setup backups ready".to_string()
            } else {
                "wm-cpr-bridge not installed yet".to_string()
            },
        },
        ChapterState {
            id: "pulse",
            roman: "VII",
            title: "Pulse",
            status: if telemetry.recent_spills >= 3 {
                StepStatus::Warn
            } else {
                StepStatus::Ok
            },
            detail: format!(
                "{} squeezed cmds ({:.1}% saved), {} spills",
                telemetry.squeezed_cmds, telemetry.squeeze_saved_pct, telemetry.recent_spills
            ),
        },
        ChapterState {
            id: "renewal",
            roman: "VIII",
            title: "Renewal",
            status: if profile_path.is_some() {
                StepStatus::Ok
            } else {
                StepStatus::Skip
            },
            detail: profile_path
                .clone()
                .unwrap_or_else(|| "Preview (--plan)".to_string()),
        },
    ];

    let state_path = if opts.plan_configs {
        None
    } else {
        write_json_atomic(home, "grimoire_state.json", &chapters)
            .ok()
            .map(|p| p.display().to_string())
    };

    let report = GrimoireReport {
        version: env!("CARGO_PKG_VERSION"),
        ready,
        store_path: store_path.display().to_string(),
        active_galaxies: galaxies,
        detected_clients: detected_names,
        planned_clients,
        profile_path,
        state_path,
        spec_source: spec_opt.map(|(p, _)| p),
        profile,
        chapters,
        steps,
        total_ms: start_all.elapsed().as_millis(),
    };

    if opts.json_mode {
        let json_str = serde_json::to_string_pretty(&report)
            .map_err(|e| format!("Serialization error: {e}"))?;
        println!("{json_str}");
    } else {
        print_grimoire_terminal(&report, opts);
    }

    Ok(report)
}

fn print_grimoire_terminal(report: &GrimoireReport, opts: &GrimoireOptions) {
    println!("==================================================");
    println!("    WhiteMagic Adaptive Grimoire Setup Pass       ");
    println!("==================================================");
    println!("Kernel Version:   v{}", report.version);
    println!("Store Path:       {}", report.store_path);
    println!(
        "Hardware Tier:    {} (Tricameral rec: {})",
        report.profile.hardware_tier.as_str(),
        report.profile.recommended_tricameral_profile
    );
    println!(
        "Confinement:      {} (mandala guard: {})",
        report.profile.confinement.runner_profile, report.profile.confinement.mandala_guard_mode
    );
    if !report.profile.capabilities.local_runtimes.is_empty() {
        println!(
            "Local Runtimes:   {}",
            report.profile.capabilities.local_runtimes.join(", ")
        );
    }
    if let Some(ref src) = report.spec_source {
        println!("Declarative Spec: {src}");
    }
    println!(
        "Model Profile:    {} (read clamp >{}L -> {}L)",
        report.profile.model_tuning.resolved_family.as_str(),
        report.profile.model_tuning.max_unbounded_read_lines,
        report.profile.model_tuning.clamp_read_lines
    );
    println!("Total Elapsed:    {} ms", report.total_ms);
    println!(
        "Readiness:        {}",
        if report.ready {
            "READY (All systems verified)"
        } else {
            "DEGRADED"
        }
    );
    println!("--------------------------------------------------");

    for s in &report.steps {
        let mark = match s.status {
            StepStatus::Ok => "\x1b[32m[PASS]\x1b[0m",
            StepStatus::Warn => "\x1b[33m[WARN]\x1b[0m",
            StepStatus::Skip => "\x1b[34m[SKIP]\x1b[0m",
            StepStatus::Fail => "\x1b[31m[FAIL]\x1b[0m",
        };
        println!("{mark} {:<16} : {}", s.name, s.summary);
        println!("       Detail: {}", s.detail);
    }

    println!("--------------------------------------------------");
    println!("Active Galaxies ({}):", report.active_galaxies.len());
    for g in &report.active_galaxies {
        let marker = if g.is_starter { " (Starter Guide)" } else { "" };
        println!("  * {:<14} : {} memories{}", g.name, g.record_count, marker);
        println!("    Tags: {}", g.tags.join(", "));
    }

    if !report.planned_clients.is_empty() {
        println!("--------------------------------------------------");
        println!("Planned MCP client configuration targets (no files written):");
        for planned in &report.planned_clients {
            println!("  * {planned}");
        }
    }

    if opts.tune_mode && !report.profile.telemetry.recommendations.is_empty() {
        println!("--------------------------------------------------");
        println!("Telemetry Self-Tuning Recommendations:");
        for rec in &report.profile.telemetry.recommendations {
            println!("  * {rec}");
        }
    }

    println!("==================================================");
    println!("Next Steps:");
    println!("  1. Preview full config changes: wm grimoire --plan --suite");
    println!("  2. Apply single-writer MCP + adaptive profile: wm grimoire --write --suite");
    println!("  3. Verify health anytime: wm doctor");
    println!("==================================================");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn plan_mode_reports_targets_without_modifying_files() {
        let root = std::env::temp_dir().join(format!("wm-grimoire-test-{}", uuid::Uuid::new_v4()));
        let home = root.join("home");
        let store = root.join("store");
        std::fs::create_dir_all(home.join(".cursor")).expect("create cursor dir");
        std::fs::create_dir_all(home.join(".gemini/config")).expect("create agy dir");
        let cursor_cfg = home.join(".cursor").join("mcp.json");
        let original = br#"{"mcpServers":{"other":{"command":"other"}}}"#;
        std::fs::write(&cursor_cfg, original).expect("seed cursor config");

        let report =
            run_grimoire_with_home(&store, false, true, Some(&home)).expect("grimoire plan run");
        assert!(
            report.planned_clients.iter().any(|p| p.contains("Cursor")),
            "plan should name detected Cursor config: {:?}",
            report.planned_clients
        );
        assert!(
            report
                .planned_clients
                .iter()
                .any(|p| p.contains("Antigravity")),
            "plan should detect Antigravity 2.0 config dir: {:?}",
            report.planned_clients
        );
        assert!(
            report
                .planned_clients
                .iter()
                .all(|p| p.contains("no file modified"))
        );
        assert!(
            report.profile_path.is_none(),
            "plan mode must not write grimoire_profile.json"
        );
        assert!(
            !home
                .join(".local/share/whitemagic/grimoire_profile.json")
                .exists(),
            "plan mode must not create profile file on disk"
        );
        assert_eq!(
            std::fs::read(&cursor_cfg).expect("read cursor config"),
            original,
            "plan mode must not modify existing client configs"
        );
        assert!(
            !store.exists(),
            "plan mode must not create missing store directory"
        );
        assert!(!store.join("galaxy.html").exists());

        let no_plan =
            run_grimoire_with_home(&store, false, false, Some(&home)).expect("grimoire plain run");
        assert!(no_plan.planned_clients.is_empty());
        assert!(store.exists(), "non-plan mode creates and seeds the store");
        assert!(
            home.join(".local/share/whitemagic/grimoire_profile.json")
                .is_file(),
            "non-plan mode persists grimoire_profile.json"
        );

        std::fs::remove_dir_all(root).ok();
    }

    #[test]
    fn detect_agents_without_home_reports_nothing() {
        assert!(detect_coding_agents_in(None).is_empty());
    }

    #[test]
    fn adaptive_profile_selects_confinement_hardware_and_model_tuning() {
        let base_caps = HostCapabilities {
            os: "linux".to_string(),
            arch: "x86_64".to_string(),
            kernel_release: "7.0.0-43-generic".to_string(),
            cores: 8,
            ram_gb: 16,
            has_avx2: true,
            has_neon: false,
            landlock_active: true,
            landlock_abi_est: Some(8),
            has_bwrap: true,
            has_wm_sandbox: true,
            has_kvm: true,
            has_firecracker: false,
            has_podman: false,
            has_node: true,
            has_python3: true,
            has_cargo: true,
            local_runtimes: Vec::new(),
        };
        assert_eq!(classify_hardware_tier(&base_caps), HardwareTier::Standard);
        let c1 = select_confinement_plan(&base_caps);
        assert_eq!(c1.tier, ConfinementTier::BwrapLandlock);
        assert_eq!(
            c1.burst_runner_profile.as_deref(),
            Some("landlock-wm-direct-v1")
        );
        assert!(c1.degraded_reason.is_none());

        let mut no_bwrap = base_caps.clone();
        no_bwrap.has_bwrap = false;
        let c2 = select_confinement_plan(&no_bwrap);
        assert_eq!(c2.tier, ConfinementTier::LandlockDirect);
        assert!(c2.degraded_reason.is_some());

        let mut mac_micro = base_caps.clone();
        mac_micro.os = "macos".to_string();
        mac_micro.ram_gb = 4;
        mac_micro.has_avx2 = false;
        mac_micro.landlock_active = false;
        mac_micro.has_bwrap = false;
        mac_micro.has_wm_sandbox = false;
        mac_micro.has_kvm = false;
        assert_eq!(classify_hardware_tier(&mac_micro), HardwareTier::Micro);
        let c3 = select_confinement_plan(&mac_micro);
        assert_eq!(c3.tier, ConfinementTier::PreCommandVfsOnly);
        assert!(c3.degraded_reason.is_some());

        let empty_tel = TelemetryTuningSummary::default();
        let t_local =
            synthesize_model_tuning(ModelFamily::LocalSmall, HardwareTier::Micro, &empty_tel);
        assert_eq!(t_local.clamp_read_lines, 120);
        assert_eq!(t_local.recommended_mcp_profile, "minimal");

        let t_grok =
            synthesize_model_tuning(ModelFamily::Grok4, HardwareTier::Sovereign, &empty_tel);
        assert_eq!(t_grok.context_warn_tokens, 250_000);
    }

    #[test]
    fn telemetry_tuning_parses_squeeze_spills_and_sim_failures() {
        let root = std::env::temp_dir().join(format!("wm-grimoire-tel-{}", uuid::Uuid::new_v4()));
        let home = root.join("home");
        let data = home.join(".local/share/whitemagic");
        std::fs::create_dir_all(&data).expect("mkdir data");

        std::fs::write(
            data.join("wm_squeeze_stats.jsonl"),
            "{\"raw\":10000,\"out\":2000}\n{\"raw\":10000,\"out\":3000}\n",
        )
        .expect("write squeeze stats");
        std::fs::write(
            data.join("agy_telemetry.jsonl"),
            concat!(
                "{\"event\":\"tool_spill\",\"host\":\"cursor\",\"bytes\":20000}\n",
                "{\"event\":\"tool_spill\",\"host\":\"cursor\",\"bytes\":21000}\n",
                "{\"event\":\"tool_spill\",\"host\":\"cursor\",\"bytes\":22000}\n",
                "{\"host\":\"cursor\",\"model\":\"claude-4-sonnet\",\"status\":\"completed\"}\n"
            ),
        )
        .expect("write telemetry");
        std::fs::write(
            data.join("sim_ledger.jsonl"),
            "{\"event\":\"tool_failure\",\"host\":\"cursor\",\"tool\":\"Shell\"}\n",
        )
        .expect("write sim");

        let suite = probe_suite_inventory(Some(&home));
        let caps = probe_host_capabilities(Some(&home));
        let conf = select_confinement_plan(&caps);
        let tel = analyze_telemetry_and_tune(Some(&home), HardwareTier::Standard, &suite, &conf);

        assert_eq!(tel.squeezed_cmds, 2);
        assert!((tel.squeeze_saved_pct - 75.0).abs() < 0.1);
        assert_eq!(tel.recent_spills, 3);
        assert_eq!(tel.recent_cursor_events, 4);
        assert_eq!(tel.recent_tool_failures, 1);
        assert_eq!(tel.last_observed_model.as_deref(), Some("claude-4-sonnet"));

        // Auto-detection picks Claude4 and tightens unbounded read threshold due to >=3 spills
        let tuning = synthesize_model_tuning(ModelFamily::Auto, HardwareTier::Standard, &tel);
        assert_eq!(tuning.resolved_family, ModelFamily::Claude4);
        assert_eq!(tuning.max_unbounded_read_lines, 300);

        std::fs::remove_dir_all(root).ok();
    }

    #[test]
    fn single_writer_assignment_respects_existing_writable_client() {
        let root = std::env::temp_dir().join(format!("wm-grimoire-sw-{}", uuid::Uuid::new_v4()));
        let home = root.join("home");
        std::fs::create_dir_all(home.join(".cursor")).expect("mkdir cursor");
        std::fs::create_dir_all(home.join(".codex")).expect("mkdir codex");
        std::fs::create_dir_all(home.join(".gemini/config")).expect("mkdir agy");
        std::fs::write(
            home.join(".cursor/mcp.json"),
            r#"{"mcpServers":{"whitemagic":{"command":"/usr/local/bin/wm3","args":["serve"]}}}"#,
        )
        .expect("write cursor");

        let specs: Vec<ClientSpec> = setup::specs_in(Some(&home))
            .into_iter()
            .filter(|s| setup::installed_in(Some(&home), s))
            .collect();
        let (primary, secondaries, turbo) = compute_single_writer_plan(&specs);
        assert_eq!(primary.as_deref(), Some("Cursor"));
        assert!(secondaries.iter().any(|s| s == "Codex CLI"));
        assert!(secondaries.iter().any(|s| s == "Antigravity"));
        assert!(turbo.contains(&"cursor".to_string()));
        assert!(turbo.contains(&"codex".to_string()));
        assert!(turbo.contains(&"agy".to_string()));

        std::fs::remove_dir_all(root).ok();
    }

    #[test]
    fn grimoire_toml_spec_parses_and_overrides_profile() {
        let toml = r#"
# Project Grimoire declaration
profile = "developer"
model = "claude4"
mandala_guard = "strict"
confinement = "landlock-wm-direct-v1"
clients = ["cursor", "codex"]
readonly_clients = ["codex"]
mcp_profile = "minimal"
clamp_read_lines = 160
max_unbounded_read_lines = 260
wide_jsonl_lines = 40
"#;
        let spec = parse_grimoire_spec_str(toml, false).expect("parse toml spec");
        assert_eq!(spec.model.as_deref(), Some("claude4"));
        assert_eq!(spec.mandala_guard.as_deref(), Some("strict"));
        assert_eq!(spec.clamp_read_lines, Some(160));
        assert_eq!(
            spec.clients.as_deref(),
            Some(&["cursor".to_string(), "codex".to_string()][..])
        );

        let root = std::env::temp_dir().join(format!("wm-grimoire-spec-{}", uuid::Uuid::new_v4()));
        let home = root.join("home");
        let store = root.join("store");
        std::fs::create_dir_all(&home).expect("mkdir home");
        let spec_file = root.join(".wm-grimoire.toml");
        std::fs::write(&spec_file, toml).expect("write spec");

        let opts = GrimoireOptions {
            apply_spec: Some(spec_file),
            ..Default::default()
        };
        let report =
            run_grimoire_with_home_and_options(&store, Some(&home), &opts).expect("run with spec");
        assert_eq!(report.profile.confinement.mandala_guard_mode, "strict");
        assert_eq!(
            report.profile.confinement.runner_profile,
            "landlock-wm-direct-v1"
        );
        assert_eq!(
            report.profile.model_tuning.resolved_family,
            ModelFamily::Claude4
        );
        assert_eq!(report.profile.model_tuning.clamp_read_lines, 160);
        assert_eq!(report.chapters.len(), 8);
        assert!(
            home.join(".local/share/whitemagic/grimoire_state.json")
                .is_file()
        );

        std::fs::remove_dir_all(root).ok();
    }

    #[test]
    fn per_host_profiles_and_suite_manifest_and_tune_write_work() {
        let root = std::env::temp_dir().join(format!("wm-grimoire-hosts-{}", uuid::Uuid::new_v4()));
        let home = root.join("home");
        let store = root.join("store");
        let data = home.join(".local/share/whitemagic");
        let suite_dir = data.join("suite");
        std::fs::create_dir_all(suite_dir.join("agy-kit")).expect("mkdir agy");
        std::fs::create_dir_all(suite_dir.join("mandala-gate-lite/gate_lite"))
            .expect("mkdir mandala");
        std::fs::write(suite_dir.join("agy-kit/install.sh"), "#!/bin/sh\n").expect("write install");
        std::fs::write(
            suite_dir.join("mandala-gate-lite/gate_lite/ctl.py"),
            "# ctl\n",
        )
        .expect("write ctl");
        std::fs::write(
            data.join("suite_manifest.json"),
            serde_json::json!({
                "agy_kit_dir": suite_dir.join("agy-kit"),
                "mandala_dir": suite_dir.join("mandala-gate-lite"),
            })
            .to_string(),
        )
        .expect("write suite_manifest");

        std::fs::create_dir_all(home.join(".codex")).expect("mkdir codex");
        std::fs::write(
            home.join(".codex/config.toml"),
            "model = \"gpt-5.4-codex\"\n",
        )
        .expect("write codex");
        std::fs::create_dir_all(home.join(".gemini/antigravity-cli")).expect("mkdir agy cli");
        std::fs::write(
            home.join(".gemini/antigravity-cli/settings.json"),
            r#"{"model":"gemini-4-neon"}"#,
        )
        .expect("write agy settings");
        std::fs::write(
            data.join("agy_telemetry.jsonl"),
            "{\"event\":\"tool_spill\"}\n{\"event\":\"tool_spill\"}\n{\"event\":\"tool_spill\"}\n",
        )
        .expect("write spills");

        let opts = GrimoireOptions {
            tune_mode: true,
            write_mode: true,
            ..Default::default()
        };
        let report =
            run_grimoire_with_home_and_options(&store, Some(&home), &opts).expect("run tune write");
        assert!(report.profile.suite.agy_kit_installer.is_some());
        assert!(report.profile.suite.mandala_gate_lite.is_some());
        assert_eq!(
            report.profile.host_profiles["codex"].resolved_family,
            ModelFamily::OpenAiCodex
        );
        assert_eq!(
            report.profile.host_profiles["agy"].resolved_family,
            ModelFamily::Gemini4
        );
        assert_eq!(
            report.profile.host_profiles["agy"].context_warn_tokens,
            100_000
        );
        assert_eq!(
            report.profile.host_profiles["agy"].context_cliff_tokens,
            120_000
        );
        assert_eq!(
            report.profile.host_profiles["agy"].neon_warn_tokens,
            100_000
        );
        assert_eq!(
            report.profile.host_profiles["agy"].neon_rollover_tokens,
            120_000
        );
        // 3 spills -> 200L -> tightened by 25% under --tune --write => 150L
        assert_eq!(report.profile.model_tuning.clamp_read_lines, 150);

        std::fs::remove_dir_all(root).ok();
    }
}
