//! Inference Tuner — hardware-aware auto-configuration for local LLMs.
//!
//! Detects hardware capabilities at startup and recommends optimal inference
//! parameters (context size, thread count, KV cache type, parallel slots,
//! speculative decoding settings). This is the N8 phase — the last piece
//! for full v2 local-AI parity.
//!
//! The tuner reads from `/proc/cpuinfo`, `/proc/meminfo`, and
//! `std::thread::available_parallelism()` to build a `HardwareProfile`,
//! then maps it to a `TunedConfig` that can override `LlamaConfig` defaults.
//!
//! Ported from v2 `inference/inference_tuner.py` (382 lines) and
//! `inference/auto_optimizer.py` (496 lines).
//!
//! ## Activation
//!
//! Set `WM_AUTO_TUNE=1` to enable auto-tuning at startup. The tuner will:
//! 1. Detect hardware → `HardwareProfile`
//! 2. Recommend config → `TunedConfig`
//! 3. Optionally benchmark → `BenchmarkResult`
//! 4. Persist to `WM_TUNER_CACHE_PATH` (default: `~/.local/share/whitemagic/tuner.json`)

#![allow(clippy::significant_drop_tightening)]

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

// ── Hardware Profile ──────────────────────────────────────────────────

/// SIMD support level detected from CPU info.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SimdLevel {
    /// No SIMD detected.
    None,
    /// SSE/SSE2 only (older x86).
    Sse,
    /// AVX/AVX2 (modern x86).
    Avx,
    /// AVX-512 (high-end x86).
    Avx512,
    /// NEON (ARM).
    Neon,
    /// Unknown architecture.
    Unknown,
}

impl SimdLevel {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Sse => "sse",
            Self::Avx => "avx",
            Self::Avx512 => "avx512",
            Self::Neon => "neon",
            Self::Unknown => "unknown",
        }
    }

    /// Performance multiplier for inference (higher = faster matrix ops).
    #[must_use]
    pub const fn perf_multiplier(self) -> f32 {
        match self {
            Self::None => 0.5,
            Self::Sse => 0.8,
            Self::Avx => 1.0,
            Self::Avx512 => 1.3,
            Self::Neon => 0.9,
            Self::Unknown => 0.7,
        }
    }
}

/// Hardware capability profile detected at startup.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HardwareProfile {
    /// CPU model name (e.g. "Intel i7-12700K", "ARM Cortex-A78").
    pub cpu_model: String,
    /// Number of physical/logical cores available.
    pub cores: usize,
    /// Total system RAM in GB.
    pub ram_gb: f32,
    /// Available RAM in GB (total - estimated in-use).
    pub available_ram_gb: f32,
    /// SIMD support level.
    pub simd: SimdLevel,
    /// Whether this is a constrained device (low RAM or few cores).
    pub is_constrained: bool,
    /// Whether this is a high-end device (lots of RAM + cores).
    pub is_high_end: bool,
    /// Architecture (e.g. "x86_64", "aarch64").
    pub arch: String,
}

impl HardwareProfile {
    /// Constrained threshold: less than 8 GB RAM or fewer than 4 cores.
    pub const CONSTRAINED_RAM_GB: f32 = 8.0;
    /// Constrained threshold: fewer than 4 cores.
    pub const CONSTRAINED_CORES: usize = 4;
    /// High-end threshold: 32+ GB RAM and 8+ cores.
    pub const HIGH_END_RAM_GB: f32 = 32.0;
    /// High-end threshold: 8+ cores.
    pub const HIGH_END_CORES: usize = 8;

    /// Human-readable summary.
    #[must_use]
    pub fn summary(&self) -> String {
        let class = if self.is_constrained {
            "constrained"
        } else if self.is_high_end {
            "high-end"
        } else {
            "standard"
        };
        format!(
            "{} ({} cores, {:.1}GB RAM, SIMD: {}, {})",
            self.cpu_model,
            self.cores,
            self.ram_gb,
            self.simd.as_str(),
            class,
        )
    }

    /// Convert to JSON for MCP tool responses.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "cpu_model": self.cpu_model,
            "cores": self.cores,
            "ram_gb": self.ram_gb,
            "available_ram_gb": self.available_ram_gb,
            "simd": self.simd.as_str(),
            "is_constrained": self.is_constrained,
            "is_high_end": self.is_high_end,
            "arch": self.arch,
            "summary": self.summary(),
        })
    }
}

impl Default for HardwareProfile {
    fn default() -> Self {
        Self {
            cpu_model: "Unknown".into(),
            cores: 1,
            ram_gb: 0.0,
            available_ram_gb: 0.0,
            simd: SimdLevel::Unknown,
            is_constrained: true,
            is_high_end: false,
            arch: std::env::consts::ARCH.into(),
        }
    }
}

// ── Tuned Config ──────────────────────────────────────────────────────

/// KV cache quantization type.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CacheType {
    /// 4-bit quantized (minimal RAM, slight quality loss).
    Q4_0,
    /// 8-bit quantized (balanced).
    Q8_0,
    /// 16-bit float (full precision, most RAM).
    F16,
}

impl CacheType {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Q4_0 => "q4_0",
            Self::Q8_0 => "q8_0",
            Self::F16 => "f16",
        }
    }

    /// Estimated RAM per 1K context tokens (in MB).
    #[must_use]
    pub const fn ram_per_1k_tokens(self) -> f32 {
        match self {
            Self::Q4_0 => 8.0,
            Self::Q8_0 => 16.0,
            Self::F16 => 32.0,
        }
    }
}

/// Speculative decoding method.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SpecMethod {
    /// No speculative decoding.
    None,
    /// ngram-mod (no draft model needed, built into llama.cpp).
    NgramMod,
    /// Draft model (requires a small model running alongside).
    DraftModel,
}

impl SpecMethod {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::NgramMod => "ngram-mod",
            Self::DraftModel => "draft-model",
        }
    }
}

/// Hardware-tuned inference configuration.
///
/// These values override `LlamaConfig` defaults when auto-tuning is enabled.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TunedConfig {
    /// Context window size.
    pub n_ctx: usize,
    /// Number of threads for inference.
    pub n_threads: usize,
    /// KV cache quantization.
    pub cache_type: CacheType,
    /// Number of parallel slots.
    pub parallel: usize,
    /// Speculative decoding method.
    pub spec_method: SpecMethod,
    /// Speculative decoding draft size (number of tokens to draft).
    pub spec_draft_size: usize,
    /// Maximum tokens for response.
    pub max_tokens: u32,
    /// Whether flash attention is enabled.
    pub flash_attn: bool,
    /// Recommended idle timeout in seconds.
    pub idle_timeout_secs: u64,
    /// The hardware profile this was tuned for.
    pub profile_summary: String,
}

impl TunedConfig {
    /// Convert to JSON for MCP tool responses.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "n_ctx": self.n_ctx,
            "n_threads": self.n_threads,
            "cache_type": self.cache_type.as_str(),
            "parallel": self.parallel,
            "spec_method": self.spec_method.as_str(),
            "spec_draft_size": self.spec_draft_size,
            "max_tokens": self.max_tokens,
            "flash_attn": self.flash_attn,
            "idle_timeout_secs": self.idle_timeout_secs,
            "profile_summary": self.profile_summary,
        })
    }
}

// ── Benchmark Result ──────────────────────────────────────────────────

/// Result of a quick inference benchmark.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkResult {
    /// Tokens generated per second.
    pub tokens_per_sec: f32,
    /// Time to first token in milliseconds.
    pub ttft_ms: f32,
    /// Peak memory usage during benchmark in MB.
    pub peak_mem_mb: f32,
    /// Whether the benchmark completed successfully.
    pub success: bool,
    /// Error message if failed.
    pub error: Option<String>,
}

impl BenchmarkResult {
    /// Composite fitness score: speed / memory (higher is better).
    #[must_use]
    pub fn fitness(&self) -> f32 {
        if !self.success || self.peak_mem_mb <= 0.0 {
            return 0.0;
        }
        self.tokens_per_sec / (self.peak_mem_mb / 100.0)
    }
}

// ── Tuning Decision ───────────────────────────────────────────────────

/// Record of a tuning decision for audit trail.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TuningDecision {
    /// Hardware profile detected.
    pub profile: HardwareProfile,
    /// Config recommended.
    pub config: TunedConfig,
    /// Human-readable reasoning for each parameter choice.
    pub reasoning: Vec<String>,
    /// Whether this was loaded from cache or freshly computed.
    pub from_cache: bool,
    /// Timestamp of tuning.
    pub timestamp: String,
}

// ── Inference Tuner ───────────────────────────────────────────────────

/// Inference tuner — detects hardware and recommends optimal config.
///
/// ## Usage
///
/// ```no_run
/// use wm_bicameral::InferenceTuner;
/// let tuner = InferenceTuner::new();
/// let decision = tuner.tune();
/// println!("{}", decision.config.to_json());
/// ```
pub struct InferenceTuner {
    cache_path: Option<PathBuf>,
}

impl InferenceTuner {
    /// Create a new tuner with default cache path.
    #[must_use]
    pub fn new() -> Self {
        let cache_path = std::env::var("WM_TUNER_CACHE_PATH")
            .ok()
            .map(PathBuf::from)
            .or_else(default_cache_path);
        Self { cache_path }
    }

    /// Create a tuner with no caching (always re-detect).
    #[must_use]
    pub const fn no_cache() -> Self {
        Self { cache_path: None }
    }

    /// Create a tuner with an explicit cache path.
    #[must_use]
    pub const fn with_cache(path: PathBuf) -> Self {
        Self {
            cache_path: Some(path),
        }
    }

    /// Whether auto-tuning is enabled via `WM_AUTO_TUNE` env var.
    #[must_use]
    pub fn is_enabled() -> bool {
        std::env::var("WM_AUTO_TUNE").is_ok_and(|v| v == "1" || v.eq_ignore_ascii_case("true"))
    }

    /// Run the full tuning pipeline: detect → recommend → persist.
    ///
    /// If a valid cache exists, returns cached result. Otherwise detects
    /// hardware, computes config, and persists.
    #[must_use]
    pub fn tune(&self) -> TuningDecision {
        // Try cache first
        if let Some(path) = &self.cache_path {
            if let Some(cached) = self.load_cache(path) {
                return cached;
            }
        }

        // Fresh detection
        let profile = detect_hardware();
        let (config, reasoning) = recommend_config(&profile);

        let decision = TuningDecision {
            profile,
            config,
            reasoning,
            from_cache: false,
            timestamp: chrono::Utc::now().to_rfc3339(),
        };

        // Persist
        if let Some(path) = &self.cache_path {
            self.save_cache(path, &decision);
        }

        decision
    }

    /// Detect hardware only (no config recommendation).
    #[must_use]
    pub fn detect(&self) -> HardwareProfile {
        detect_hardware()
    }

    /// Load cached tuning decision from a file.
    fn load_cache(&self, path: &PathBuf) -> Option<TuningDecision> {
        let data = fs::read_to_string(path).ok()?;
        let mut decision: TuningDecision = serde_json::from_str(&data).ok()?;
        decision.from_cache = true;
        tracing::info!("tuner cache loaded from {}", path.display());
        Some(decision)
    }

    /// Save tuning decision to a cache file.
    fn save_cache(&self, path: &PathBuf, decision: &TuningDecision) {
        if let Some(parent) = path.parent() {
            if fs::create_dir_all(parent).is_err() {
                tracing::warn!("tuner cache dir creation failed");
                return;
            }
        }
        match serde_json::to_string_pretty(decision) {
            Ok(json) => {
                if fs::write(path, json).is_err() {
                    tracing::warn!("tuner cache write failed");
                }
            }
            Err(e) => tracing::warn!("tuner cache serialize error: {e}"),
        }
    }

    /// Clear the cache file if it exists.
    pub fn clear_cache(&self) {
        if let Some(path) = &self.cache_path {
            let _ = fs::remove_file(path);
        }
    }
}

impl Default for InferenceTuner {
    fn default() -> Self {
        Self::new()
    }
}

// ── Hardware Detection ────────────────────────────────────────────────

/// Detect hardware profile from `/proc` and system info.
#[must_use]
pub fn detect_hardware() -> HardwareProfile {
    let cores = std::thread::available_parallelism().map_or(1, std::num::NonZero::get);

    let (cpu_model, simd) = read_cpu_info();
    let (ram_gb, available_ram_gb) = read_total_ram();

    let is_constrained =
        ram_gb < HardwareProfile::CONSTRAINED_RAM_GB || cores < HardwareProfile::CONSTRAINED_CORES;
    let is_high_end =
        ram_gb >= HardwareProfile::HIGH_END_RAM_GB && cores >= HardwareProfile::HIGH_END_CORES;

    HardwareProfile {
        cpu_model,
        cores,
        ram_gb,
        available_ram_gb,
        simd,
        is_constrained,
        is_high_end,
        arch: std::env::consts::ARCH.into(),
    }
}

/// Read CPU model name and SIMD level from `/proc/cpuinfo` (Linux).
fn read_cpu_info() -> (String, SimdLevel) {
    let cpuinfo = fs::read_to_string("/proc/cpuinfo").unwrap_or_default();
    let model = cpuinfo
        .lines()
        .find_map(|line| {
            let trimmed = line.trim();
            trimmed
                .strip_prefix("model name")
                .or_else(|| trimmed.strip_prefix("Hardware"))
                .and_then(|s| s.trim_start_matches([':', ' ']).parse::<String>().ok())
        })
        .unwrap_or_else(|| {
            // Fallback: use arch-specific default
            if std::env::consts::ARCH == "aarch64" {
                "ARM Processor".to_string()
            } else {
                "Unknown CPU".to_string()
            }
        });

    let simd = detect_simd(&cpuinfo);

    (model, simd)
}

/// Detect SIMD level from cpuinfo flags.
fn detect_simd(cpuinfo: &str) -> SimdLevel {
    // Collect all flags lines
    let flags_line: String = cpuinfo
        .lines()
        .find_map(|line| {
            let trimmed = line.trim();
            trimmed
                .strip_prefix("flags")
                .or_else(|| trimmed.strip_prefix("Features"))
                .map(|s| s.trim_start_matches([':', ' ']).to_string())
        })
        .unwrap_or_default();

    let flags: Vec<&str> = flags_line.split_whitespace().collect();

    if flags.iter().any(|f| *f == "avx512f" || *f == "avx512vl") {
        SimdLevel::Avx512
    } else if flags.iter().any(|f| *f == "avx" || *f == "avx2") {
        SimdLevel::Avx
    } else if flags.iter().any(|f| *f == "sse" || *f == "sse2") {
        SimdLevel::Sse
    } else if flags.iter().any(|f| *f == "neon" || *f == "asimd") {
        SimdLevel::Neon
    } else if flags_line.is_empty() {
        SimdLevel::Unknown
    } else {
        SimdLevel::None
    }
}

/// Read total and available RAM from `/proc/meminfo` (Linux).
fn read_total_ram() -> (f32, f32) {
    let meminfo = fs::read_to_string("/proc/meminfo").unwrap_or_default();

    let mut mem_total_kb: Option<u64> = None;
    let mut mem_available_kb: Option<u64> = None;

    for line in meminfo.lines() {
        if line.starts_with("MemTotal:") {
            mem_total_kb = parse_meminfo_kb(line);
        } else if line.starts_with("MemAvailable:") {
            mem_available_kb = parse_meminfo_kb(line);
        }
    }

    let total_gb = mem_total_kb.map_or(0.0, |kb| kb as f32 / 1_048_576.0);
    let avail_gb = mem_available_kb.map_or(total_gb * 0.7, |kb| kb as f32 / 1_048_576.0);

    (total_gb, avail_gb)
}

/// Parse a `/proc/meminfo` line like `MemTotal:       16384000 kB` → kB value.
fn parse_meminfo_kb(line: &str) -> Option<u64> {
    line.split(':')
        .nth(1)
        .and_then(|s| s.split_whitespace().next())
        .and_then(|s| s.parse::<u64>().ok())
}

/// Default cache path: `~/.local/share/whitemagic/tuner.json`
fn default_cache_path() -> Option<PathBuf> {
    std::env::var("HOME")
        .ok()
        .map(|home| PathBuf::from(home).join(".local/share/whitemagic/tuner.json"))
}

// ── Config Recommendation ─────────────────────────────────────────────

/// Recommend a tuned config from a hardware profile.
///
/// Returns the config and a list of human-readable reasoning strings
/// explaining each parameter choice.
#[must_use]
pub fn recommend_config(profile: &HardwareProfile) -> (TunedConfig, Vec<String>) {
    let mut reasoning = Vec::new();

    // ── Context size ──
    let n_ctx = if profile.is_constrained {
        reasoning.push(format!(
            "n_ctx=2048: constrained device ({:.1}GB RAM, {} cores)",
            profile.ram_gb, profile.cores
        ));
        2048
    } else if profile.is_high_end {
        reasoning.push(format!(
            "n_ctx=8192: high-end device ({:.1}GB RAM, {} cores)",
            profile.ram_gb, profile.cores
        ));
        8192
    } else {
        reasoning.push(format!(
            "n_ctx=4096: standard device ({:.1}GB RAM, {} cores)",
            profile.ram_gb, profile.cores
        ));
        4096
    };

    // ── Threads ──
    // Use physical cores (assume hyperthreading: logical/2), but at least 2
    let n_threads = if profile.cores <= 2 {
        reasoning.push(format!(
            "n_threads={}: limited cores, use all available",
            profile.cores
        ));
        profile.cores
    } else {
        let physical = profile.cores / 2;
        let threads = physical.clamp(2, 8);
        reasoning.push(format!(
            "n_threads={}: {} logical cores → {} physical, capped at 8",
            threads, profile.cores, physical
        ));
        threads
    };

    // ── KV cache type ──
    let cache_type = if profile.is_constrained {
        reasoning.push("cache_type=q4_0: constrained RAM, use 4-bit KV cache".into());
        CacheType::Q4_0
    } else if profile.available_ram_gb > 16.0 {
        reasoning.push(format!(
            "cache_type=q8_0: {:.1}GB available RAM supports 8-bit KV cache",
            profile.available_ram_gb
        ));
        CacheType::Q8_0
    } else {
        reasoning.push("cache_type=q8_0: standard 8-bit KV cache".into());
        CacheType::Q8_0
    };

    // ── Parallel slots ──
    let parallel = if profile.is_constrained {
        reasoning.push("parallel=1: constrained device, single slot".into());
        1
    } else if profile.is_high_end {
        reasoning.push("parallel=4: high-end device, 4 parallel slots".into());
        4
    } else {
        reasoning.push("parallel=2: standard device, 2 parallel slots".into());
        2
    };

    // ── Speculative decoding ──
    // ngram-mod is always available (built into llama.cpp, no draft model needed)
    let (spec_method, spec_draft_size) = if profile.is_constrained {
        reasoning.push("spec=ngram-mod (draft=4): constrained, small draft for speed".into());
        (SpecMethod::NgramMod, 4)
    } else {
        reasoning.push("spec=ngram-mod (draft=8): good hardware, larger draft window".into());
        (SpecMethod::NgramMod, 8)
    };

    // ── Max tokens ──
    let max_tokens = if profile.is_constrained {
        reasoning.push("max_tokens=256: constrained, limit response length".into());
        256
    } else if profile.is_high_end {
        reasoning.push("max_tokens=1024: high-end, allow longer responses".into());
        1024
    } else {
        reasoning.push("max_tokens=512: standard response length".into());
        512
    };

    // ── Flash attention ──
    // Enable on x86_64 with AVX+ or aarch64 with NEON
    let flash_attn = matches!(
        profile.simd,
        SimdLevel::Avx | SimdLevel::Avx512 | SimdLevel::Neon
    );
    if flash_attn {
        reasoning.push(format!(
            "flash_attn=true: {} SIMD supports flash attention",
            profile.simd.as_str()
        ));
    } else {
        reasoning.push(format!(
            "flash_attn=false: {} SIMD insufficient for flash attention",
            profile.simd.as_str()
        ));
    }

    // ── Idle timeout ──
    let idle_timeout_secs = if profile.is_constrained {
        reasoning.push("idle_timeout=60s: constrained, aggressive shutdown".into());
        60
    } else if profile.is_high_end {
        reasoning.push("idle_timeout=600s: high-end, keep models warm longer".into());
        600
    } else {
        reasoning.push("idle_timeout=300s: standard idle timeout".into());
        300
    };

    let config = TunedConfig {
        n_ctx,
        n_threads,
        cache_type,
        parallel,
        spec_method,
        spec_draft_size,
        max_tokens,
        flash_attn,
        idle_timeout_secs,
        profile_summary: profile.summary(),
    };

    (config, reasoning)
}

// ── Apply to LlamaConfig ──────────────────────────────────────────────

/// Apply tuned config to an existing `LlamaConfig`, returning a new one.
///
/// Only overrides fields that the tuner controls. The endpoint and model
/// name are preserved from the original config.
#[must_use]
pub fn apply_to_llama_config(
    base: &crate::local_llm::LlamaConfig,
    tuned: &TunedConfig,
) -> crate::local_llm::LlamaConfig {
    crate::local_llm::LlamaConfig {
        endpoint: base.endpoint.clone(),
        model: base.model.clone(),
        temperature: base.temperature,
        timeout: base.timeout,
        max_tokens: tuned.max_tokens,
    }
}

// ── Apply to TriModelConfig ───────────────────────────────────────────

/// Apply tuned idle timeout to a `TriModelConfig` idle timeout value.
#[must_use]
pub const fn apply_idle_timeout(tuned: &TunedConfig) -> u64 {
    tuned.idle_timeout_secs
}

// ── Resource Governor Integration ─────────────────────────────────────

/// Map a hardware profile to a `GovernorMode`.
///
/// Constrained → Eco, High-end → Performance, else Normal.
#[must_use]
pub const fn profile_to_governor_mode(
    profile: &HardwareProfile,
) -> crate::resource_governor::GovernorMode {
    if profile.is_constrained {
        crate::resource_governor::GovernorMode::Eco
    } else if profile.is_high_end {
        crate::resource_governor::GovernorMode::Performance
    } else {
        crate::resource_governor::GovernorMode::Normal
    }
}

/// Convert `HardwareProfile` to `HardwareMetrics` for the resource governor.
#[must_use]
pub fn profile_to_hardware_metrics(
    profile: &HardwareProfile,
) -> crate::resource_governor::HardwareMetrics {
    let used_ratio = if profile.ram_gb > 0.0 {
        1.0 - (profile.available_ram_gb / profile.ram_gb).min(1.0)
    } else {
        0.0
    };
    crate::resource_governor::HardwareMetrics::new()
        .with_memory(used_ratio)
        .with_battery(1.0) // Assume plugged in unless overridden
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── SimdLevel tests ──

    #[test]
    fn simd_as_str() {
        assert_eq!(SimdLevel::None.as_str(), "none");
        assert_eq!(SimdLevel::Sse.as_str(), "sse");
        assert_eq!(SimdLevel::Avx.as_str(), "avx");
        assert_eq!(SimdLevel::Avx512.as_str(), "avx512");
        assert_eq!(SimdLevel::Neon.as_str(), "neon");
        assert_eq!(SimdLevel::Unknown.as_str(), "unknown");
    }

    #[test]
    fn simd_perf_multiplier() {
        assert!(SimdLevel::Avx512.perf_multiplier() > SimdLevel::Avx.perf_multiplier());
        assert!(SimdLevel::Avx.perf_multiplier() > SimdLevel::Sse.perf_multiplier());
        assert!(SimdLevel::Sse.perf_multiplier() > SimdLevel::None.perf_multiplier());
    }

    // ── CacheType tests ──

    #[test]
    fn cache_type_as_str() {
        assert_eq!(CacheType::Q4_0.as_str(), "q4_0");
        assert_eq!(CacheType::Q8_0.as_str(), "q8_0");
        assert_eq!(CacheType::F16.as_str(), "f16");
    }

    #[test]
    fn cache_type_ram_per_1k() {
        assert!(CacheType::Q4_0.ram_per_1k_tokens() < CacheType::Q8_0.ram_per_1k_tokens());
        assert!(CacheType::Q8_0.ram_per_1k_tokens() < CacheType::F16.ram_per_1k_tokens());
    }

    // ── SpecMethod tests ──

    #[test]
    fn spec_method_as_str() {
        assert_eq!(SpecMethod::None.as_str(), "none");
        assert_eq!(SpecMethod::NgramMod.as_str(), "ngram-mod");
        assert_eq!(SpecMethod::DraftModel.as_str(), "draft-model");
    }

    // ── HardwareProfile tests ──

    #[test]
    fn hardware_profile_default_is_constrained() {
        let p = HardwareProfile::default();
        assert!(p.is_constrained);
        assert!(!p.is_high_end);
        assert_eq!(p.cores, 1);
    }

    #[test]
    fn hardware_profile_summary_constrained() {
        let p = HardwareProfile {
            cpu_model: "ARM Cortex-A72".into(),
            cores: 4,
            ram_gb: 4.0,
            available_ram_gb: 2.0,
            simd: SimdLevel::Neon,
            is_constrained: true,
            is_high_end: false,
            arch: "aarch64".into(),
        };
        let s = p.summary();
        assert!(s.contains("constrained"));
        assert!(s.contains("ARM Cortex-A72"));
        assert!(s.contains("neon"));
    }

    #[test]
    fn hardware_profile_summary_high_end() {
        let p = HardwareProfile {
            cpu_model: "AMD Ryzen 9 7950X".into(),
            cores: 32,
            ram_gb: 64.0,
            available_ram_gb: 48.0,
            simd: SimdLevel::Avx512,
            is_constrained: false,
            is_high_end: true,
            arch: "x86_64".into(),
        };
        let s = p.summary();
        assert!(s.contains("high-end"));
        assert!(s.contains("avx512"));
    }

    #[test]
    fn hardware_profile_summary_standard() {
        let p = HardwareProfile {
            cpu_model: "Intel i5-12400".into(),
            cores: 12,
            ram_gb: 16.0,
            available_ram_gb: 10.0,
            simd: SimdLevel::Avx,
            is_constrained: false,
            is_high_end: false,
            arch: "x86_64".into(),
        };
        let s = p.summary();
        assert!(s.contains("standard"));
    }

    #[test]
    fn hardware_profile_to_json() {
        let p = HardwareProfile {
            cpu_model: "Test CPU".into(),
            cores: 8,
            ram_gb: 16.0,
            available_ram_gb: 8.0,
            simd: SimdLevel::Avx,
            is_constrained: false,
            is_high_end: false,
            arch: "x86_64".into(),
        };
        let json = p.to_json();
        assert_eq!(json["cpu_model"], "Test CPU");
        assert_eq!(json["cores"], 8);
        assert_eq!(json["simd"], "avx");
        assert_eq!(json["is_constrained"], false);
    }

    // ── detect_hardware tests ──

    #[test]
    fn detect_hardware_returns_valid_profile() {
        let p = detect_hardware();
        // On any system, these should be valid
        assert!(p.cores >= 1);
        assert!(!p.cpu_model.is_empty());
        // RAM might be 0 on non-Linux, but the struct should be valid
        let _ = p.summary();
    }

    // ── detect_simd tests ──

    #[test]
    fn detect_simd_avx512() {
        let cpuinfo = "flags\t\t: fpu vme de apic sep avx512f avx512vl\n";
        assert_eq!(detect_simd(cpuinfo), SimdLevel::Avx512);
    }

    #[test]
    fn detect_simd_avx2() {
        let cpuinfo = "flags\t\t: fpu vme de apic sep avx avx2\n";
        assert_eq!(detect_simd(cpuinfo), SimdLevel::Avx);
    }

    #[test]
    fn detect_simd_sse() {
        let cpuinfo = "flags\t\t: fpu vme de apic sep sse sse2\n";
        assert_eq!(detect_simd(cpuinfo), SimdLevel::Sse);
    }

    #[test]
    fn detect_simd_neon() {
        let cpuinfo = "Features\t: fp asimd evtstrm aes pmull sha1 sha2 crc32 neon\n";
        assert_eq!(detect_simd(cpuinfo), SimdLevel::Neon);
    }

    #[test]
    fn detect_simd_empty() {
        let cpuinfo = "";
        assert_eq!(detect_simd(cpuinfo), SimdLevel::Unknown);
    }

    #[test]
    fn detect_simd_no_simd_flags() {
        let cpuinfo = "flags\t\t: fpu vme de apic sep tsc\n";
        assert_eq!(detect_simd(cpuinfo), SimdLevel::None);
    }

    // ── parse_meminfo_kb tests ──

    #[test]
    fn parse_meminfo_kb_extracts_value() {
        assert_eq!(
            parse_meminfo_kb("MemTotal:       16384000 kB"),
            Some(16_384_000)
        );
        assert_eq!(
            parse_meminfo_kb("MemAvailable:   8192000 kB"),
            Some(8_192_000)
        );
        assert_eq!(parse_meminfo_kb("garbage"), None);
    }

    // ── read_total_ram tests ──

    #[test]
    fn read_total_ram_returns_values() {
        let (total, avail) = read_total_ram();
        // On Linux, total should be > 0. On other platforms, may be 0.
        if total > 0.0 {
            assert!(avail >= 0.0 && avail <= total);
        }
    }

    // ── recommend_config tests ──

    #[test]
    fn recommend_config_constrained() {
        let p = HardwareProfile {
            cpu_model: "ARM Cortex-A72".into(),
            cores: 4,
            ram_gb: 4.0,
            available_ram_gb: 2.0,
            simd: SimdLevel::Neon,
            is_constrained: true,
            is_high_end: false,
            arch: "aarch64".into(),
        };
        let (config, reasoning) = recommend_config(&p);

        assert_eq!(config.n_ctx, 2048);
        assert_eq!(config.cache_type, CacheType::Q4_0);
        assert_eq!(config.parallel, 1);
        assert_eq!(config.spec_draft_size, 4);
        assert_eq!(config.max_tokens, 256);
        assert_eq!(config.idle_timeout_secs, 60);
        assert!(config.flash_attn); // NEON supports flash attention
        assert!(!reasoning.is_empty());
    }

    #[test]
    fn recommend_config_high_end() {
        let p = HardwareProfile {
            cpu_model: "AMD Ryzen 9 7950X".into(),
            cores: 32,
            ram_gb: 64.0,
            available_ram_gb: 48.0,
            simd: SimdLevel::Avx512,
            is_constrained: false,
            is_high_end: true,
            arch: "x86_64".into(),
        };
        let (config, reasoning) = recommend_config(&p);

        assert_eq!(config.n_ctx, 8192);
        assert_eq!(config.cache_type, CacheType::Q8_0);
        assert_eq!(config.parallel, 4);
        assert_eq!(config.spec_draft_size, 8);
        assert_eq!(config.max_tokens, 1024);
        assert_eq!(config.idle_timeout_secs, 600);
        assert!(config.flash_attn);
        assert!(!reasoning.is_empty());
    }

    #[test]
    fn recommend_config_standard() {
        let p = HardwareProfile {
            cpu_model: "Intel i5-12400".into(),
            cores: 12,
            ram_gb: 16.0,
            available_ram_gb: 10.0,
            simd: SimdLevel::Avx,
            is_constrained: false,
            is_high_end: false,
            arch: "x86_64".into(),
        };
        let (config, reasoning) = recommend_config(&p);

        assert_eq!(config.n_ctx, 4096);
        assert_eq!(config.cache_type, CacheType::Q8_0);
        assert_eq!(config.parallel, 2);
        assert_eq!(config.spec_draft_size, 8);
        assert_eq!(config.max_tokens, 512);
        assert_eq!(config.idle_timeout_secs, 300);
        assert!(config.flash_attn);
        assert!(!reasoning.is_empty());
    }

    #[test]
    fn recommend_config_no_flash_attn_for_sse() {
        let p = HardwareProfile {
            cpu_model: "Intel Core2 Duo".into(),
            cores: 2,
            ram_gb: 4.0,
            available_ram_gb: 2.0,
            simd: SimdLevel::Sse,
            is_constrained: true,
            is_high_end: false,
            arch: "x86_64".into(),
        };
        let (config, _) = recommend_config(&p);
        assert!(!config.flash_attn);
    }

    #[test]
    fn recommend_config_no_flash_attn_for_no_simd() {
        let p = HardwareProfile {
            cpu_model: "Unknown".into(),
            cores: 2,
            ram_gb: 4.0,
            available_ram_gb: 2.0,
            simd: SimdLevel::None,
            is_constrained: true,
            is_high_end: false,
            arch: "x86_64".into(),
        };
        let (config, _) = recommend_config(&p);
        assert!(!config.flash_attn);
    }

    #[test]
    fn recommend_config_thread_capping() {
        // 32 logical cores → 16 physical → capped at 8
        let p = HardwareProfile {
            cpu_model: "High Core Count".into(),
            cores: 32,
            ram_gb: 32.0,
            available_ram_gb: 24.0,
            simd: SimdLevel::Avx,
            is_constrained: false,
            is_high_end: true,
            arch: "x86_64".into(),
        };
        let (config, _) = recommend_config(&p);
        assert_eq!(config.n_threads, 8);
    }

    #[test]
    fn recommend_config_2_cores_uses_all() {
        let p = HardwareProfile {
            cpu_model: "Dual Core".into(),
            cores: 2,
            ram_gb: 4.0,
            available_ram_gb: 2.0,
            simd: SimdLevel::Sse,
            is_constrained: true,
            is_high_end: false,
            arch: "x86_64".into(),
        };
        let (config, _) = recommend_config(&p);
        assert_eq!(config.n_threads, 2);
    }

    // ── TunedConfig tests ──

    #[test]
    fn tuned_config_to_json() {
        let config = TunedConfig {
            n_ctx: 4096,
            n_threads: 4,
            cache_type: CacheType::Q8_0,
            parallel: 2,
            spec_method: SpecMethod::NgramMod,
            spec_draft_size: 8,
            max_tokens: 512,
            flash_attn: true,
            idle_timeout_secs: 300,
            profile_summary: "Test (4 cores, 16.0GB RAM, avx, standard)".into(),
        };
        let json = config.to_json();
        assert_eq!(json["n_ctx"], 4096);
        assert_eq!(json["cache_type"], "q8_0");
        assert_eq!(json["spec_method"], "ngram-mod");
        assert_eq!(json["flash_attn"], true);
    }

    // ── BenchmarkResult tests ──

    #[test]
    fn benchmark_result_fitness() {
        let r = BenchmarkResult {
            tokens_per_sec: 10.0,
            ttft_ms: 100.0,
            peak_mem_mb: 500.0,
            success: true,
            error: None,
        };
        let f = r.fitness();
        assert!(f > 0.0);
    }

    #[test]
    fn benchmark_result_fitness_zero_on_failure() {
        let r = BenchmarkResult {
            tokens_per_sec: 10.0,
            ttft_ms: 100.0,
            peak_mem_mb: 500.0,
            success: false,
            error: Some("crashed".into()),
        };
        assert_eq!(r.fitness(), 0.0);
    }

    // ── InferenceTuner tests ──

    #[test]
    fn tuner_no_cache_always_detects() {
        let tuner = InferenceTuner::no_cache();
        let decision = tuner.tune();
        assert!(!decision.from_cache);
        assert!(!decision.profile.cpu_model.is_empty());
        assert!(!decision.reasoning.is_empty());
    }

    #[test]
    fn tuner_detect_returns_valid_profile() {
        let tuner = InferenceTuner::no_cache();
        let p = tuner.detect();
        assert!(p.cores >= 1);
    }

    #[test]
    fn tuner_cache_roundtrip() {
        let dir = std::env::temp_dir();
        let path = dir.join(format!("wm_tuner_test_{}.json", std::process::id()));
        // Clean up before and after
        let _ = fs::remove_file(&path);

        let tuner = InferenceTuner::with_cache(path.clone());
        let decision1 = tuner.tune();
        assert!(!decision1.from_cache);

        // Second call should load from cache
        let tuner2 = InferenceTuner::with_cache(path.clone());
        let decision2 = tuner2.tune();
        assert!(decision2.from_cache);
        assert_eq!(decision1.profile.cpu_model, decision2.profile.cpu_model);

        // Clean up
        let _ = fs::remove_file(&path);
    }

    #[test]
    fn tuner_clear_cache() {
        let dir = std::env::temp_dir();
        let path = dir.join(format!("wm_tuner_clear_test_{}.json", std::process::id()));
        let _ = fs::remove_file(&path);

        let tuner = InferenceTuner::with_cache(path.clone());
        let _ = tuner.tune();
        assert!(path.exists());

        tuner.clear_cache();
        assert!(!path.exists());
    }

    #[test]
    fn tuner_is_enabled_checks_env() {
        // Should be false by default (env var not set in tests)
        // Note: We can't set env vars in parallel tests safely, so just check
        // that the function doesn't panic.
        let _ = InferenceTuner::is_enabled();
    }

    // ── apply_to_llama_config tests ──

    #[test]
    fn apply_to_llama_config_preserves_endpoint() {
        let base = crate::local_llm::LlamaConfig {
            endpoint: "http://localhost:8080/v1/chat/completions".into(),
            model: "qwen2.5-7b".into(),
            temperature: 0.2,
            timeout: std::time::Duration::from_secs(10),
            max_tokens: 512,
        };
        let tuned = TunedConfig {
            n_ctx: 4096,
            n_threads: 4,
            cache_type: CacheType::Q8_0,
            parallel: 2,
            spec_method: SpecMethod::NgramMod,
            spec_draft_size: 8,
            max_tokens: 256,
            flash_attn: true,
            idle_timeout_secs: 300,
            profile_summary: "Test".into(),
        };
        let applied = apply_to_llama_config(&base, &tuned);
        assert_eq!(applied.endpoint, base.endpoint);
        assert_eq!(applied.model, base.model);
        assert_eq!(applied.max_tokens, 256);
        assert_eq!(applied.temperature, base.temperature);
    }

    // ── apply_idle_timeout tests ──

    #[test]
    fn apply_idle_timeout_returns_value() {
        let tuned = TunedConfig {
            n_ctx: 2048,
            n_threads: 2,
            cache_type: CacheType::Q4_0,
            parallel: 1,
            spec_method: SpecMethod::NgramMod,
            spec_draft_size: 4,
            max_tokens: 256,
            flash_attn: false,
            idle_timeout_secs: 120,
            profile_summary: "Test".into(),
        };
        assert_eq!(apply_idle_timeout(&tuned), 120);
    }

    // ── Governor integration tests ──

    #[test]
    fn profile_to_governor_mode_constrained() {
        let p = HardwareProfile {
            cpu_model: "Low-end".into(),
            cores: 2,
            ram_gb: 4.0,
            available_ram_gb: 2.0,
            simd: SimdLevel::None,
            is_constrained: true,
            is_high_end: false,
            arch: "x86_64".into(),
        };
        assert_eq!(
            profile_to_governor_mode(&p),
            crate::resource_governor::GovernorMode::Eco
        );
    }

    #[test]
    fn profile_to_governor_mode_high_end() {
        let p = HardwareProfile {
            cpu_model: "High-end".into(),
            cores: 16,
            ram_gb: 64.0,
            available_ram_gb: 48.0,
            simd: SimdLevel::Avx512,
            is_constrained: false,
            is_high_end: true,
            arch: "x86_64".into(),
        };
        assert_eq!(
            profile_to_governor_mode(&p),
            crate::resource_governor::GovernorMode::Performance
        );
    }

    #[test]
    fn profile_to_governor_mode_standard() {
        let p = HardwareProfile {
            cpu_model: "Standard".into(),
            cores: 8,
            ram_gb: 16.0,
            available_ram_gb: 10.0,
            simd: SimdLevel::Avx,
            is_constrained: false,
            is_high_end: false,
            arch: "x86_64".into(),
        };
        assert_eq!(
            profile_to_governor_mode(&p),
            crate::resource_governor::GovernorMode::Normal
        );
    }

    #[test]
    fn profile_to_hardware_metrics_calculates_pressure() {
        let p = HardwareProfile {
            cpu_model: "Test".into(),
            cores: 8,
            ram_gb: 16.0,
            available_ram_gb: 8.0,
            simd: SimdLevel::Avx,
            is_constrained: false,
            is_high_end: false,
            arch: "x86_64".into(),
        };
        let m = profile_to_hardware_metrics(&p);
        let pressure = m.memory_pressure.expect("should have memory pressure");
        assert!((pressure - 0.5).abs() < 0.01); // 8GB used out of 16GB = 0.5
    }

    #[test]
    fn profile_to_hardware_metrics_zero_ram() {
        let p = HardwareProfile {
            cpu_model: "Test".into(),
            cores: 4,
            ram_gb: 0.0,
            available_ram_gb: 0.0,
            simd: SimdLevel::Unknown,
            is_constrained: true,
            is_high_end: false,
            arch: "x86_64".into(),
        };
        let m = profile_to_hardware_metrics(&p);
        assert_eq!(m.memory_pressure, Some(0.0));
    }

    // ── TuningDecision serialization ──

    #[test]
    fn tuning_decision_serialization() {
        let decision = TuningDecision {
            profile: HardwareProfile {
                cpu_model: "Test CPU".into(),
                cores: 8,
                ram_gb: 16.0,
                available_ram_gb: 10.0,
                simd: SimdLevel::Avx,
                is_constrained: false,
                is_high_end: false,
                arch: "x86_64".into(),
            },
            config: TunedConfig {
                n_ctx: 4096,
                n_threads: 4,
                cache_type: CacheType::Q8_0,
                parallel: 2,
                spec_method: SpecMethod::NgramMod,
                spec_draft_size: 8,
                max_tokens: 512,
                flash_attn: true,
                idle_timeout_secs: 300,
                profile_summary: "Test CPU (8 cores, 16.0GB RAM, avx, standard)".into(),
            },
            reasoning: vec!["n_ctx=4096: standard device".into()],
            from_cache: false,
            timestamp: "2026-08-04T19:00:00Z".into(),
        };
        let json = serde_json::to_string(&decision).unwrap();
        let back: TuningDecision = serde_json::from_str(&json).unwrap();
        assert_eq!(back.profile.cpu_model, "Test CPU");
        assert_eq!(back.config.n_ctx, 4096);
        assert_eq!(back.reasoning.len(), 1);
        assert!(!back.from_cache);
    }

    // ── Full pipeline integration test ──

    #[test]
    fn full_tune_pipeline_produces_valid_config() {
        let tuner = InferenceTuner::no_cache();
        let decision = tuner.tune();

        // Config should be internally consistent
        let c = &decision.config;
        assert!(c.n_ctx >= 2048 && c.n_ctx <= 8192);
        assert!(c.n_threads >= 1 && c.n_threads <= 8);
        assert!(c.parallel >= 1 && c.parallel <= 4);
        assert!(c.max_tokens >= 256 && c.max_tokens <= 1024);
        assert!(c.idle_timeout_secs >= 60 && c.idle_timeout_secs <= 600);

        // Reasoning should explain each parameter
        assert!(decision.reasoning.len() >= 7); // n_ctx, n_threads, cache, parallel, spec, max_tokens, idle

        // Profile and config should agree on constrained/high-end
        if decision.profile.is_constrained {
            assert_eq!(c.n_ctx, 2048);
            assert_eq!(c.parallel, 1);
        } else if decision.profile.is_high_end {
            assert_eq!(c.n_ctx, 8192);
            assert_eq!(c.parallel, 4);
        }
    }
}
