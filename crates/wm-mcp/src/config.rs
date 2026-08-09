//! Configuration management — TOML config file with env var overrides.
//!
//! WhiteMagic can be configured via:
//! 1. TOML config file (`config.toml` in the store dir, or `--config <path>`)
//! 2. Environment variables (override config file values)
//! 3. CLI flags (override everything)
//!
//! # Example config.toml
//!
//! ```toml
//! [store]
//! path = "~/.local/share/whitemagic"
//!
//! [llm]
//! llama_endpoint = "http://localhost:8080"
//! llama_model = "local"
//! llama_timeout_ms = 10000
//!
//! llm_api_key = ""
//! llm_endpoint = "https://api.openai.com/v1/chat/completions"
//! llm_model = "gpt-4o-mini"
//! llm_timeout_ms = 5000
//!
//! [embedder]
//! endpoint = "http://localhost:8080"
//! model = "local"
//! dimension = 384
//! timeout_ms = 30000
//!
//! [daemon]
//! cycle_interval_secs = 300
//! dream_interval_secs = 600
//! brain_wave_interval_secs = 30
//! homeostasis_interval_secs = 60
//! min_health_score = 0.3
//! codegen_interval_secs = 0
//! codegen_auto_apply = false
//! research_interval_secs = 0
//! selfplay_interval_secs = 0
//! ```

#![deny(unsafe_code)]

use std::path::PathBuf;
use std::time::Duration;

use serde::{Deserialize, Serialize};

/// Top-level WhiteMagic configuration.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[allow(clippy::unsafe_derive_deserialize)]
pub struct WmConfig {
    /// Store (LMDB) configuration.
    #[serde(default)]
    pub store: StoreConfig,

    /// LLM endpoint configuration (bicameral + imagination + self-play).
    #[serde(default)]
    pub llm: LlmConfig,

    /// Embedder configuration (NLU router + vector search).
    #[serde(default)]
    pub embedder: EmbedderConfig,

    /// Daemon schedule configuration.
    #[serde(default)]
    pub daemon: DaemonConfig,
}

/// LMDB store path configuration.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct StoreConfig {
    /// Path to the LMDB store directory.
    ///
    /// Default: `~/.local/share/whitemagic` (or `$XDG_DATA_HOME/whitemagic`).
    /// Set to override; env var `WM_STORE_PATH` takes precedence.
    #[serde(default)]
    pub path: Option<PathBuf>,
}

/// LLM endpoint configuration for bicameral reasoning, imagination engine,
/// and self-play training loop.
///
/// All fields are optional — when unset, the corresponding subsystem falls
/// back to heuristic/stub handlers.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct LlmConfig {
    /// Local llama.cpp server endpoint (left hemisphere + world model + self-play solver).
    ///
    /// Env var: `WM_LLAMA_ENDPOINT`
    #[serde(default)]
    pub llama_endpoint: Option<String>,

    /// Model name for the local llama.cpp server.
    ///
    /// Env var: `WM_LLAMA_MODEL` (default: `local`)
    #[serde(default)]
    pub llama_model: Option<String>,

    /// Request timeout for local llama.cpp (milliseconds).
    ///
    /// Env var: `WM_LLAMA_TIMEOUT_MS` (default: 10000)
    #[serde(default)]
    pub llama_timeout_ms: Option<u64>,

    /// Max tokens for local llama.cpp responses.
    ///
    /// Env var: `WM_LLAMA_MAX_TOKENS` (default: 512)
    #[serde(default)]
    pub llama_max_tokens: Option<u32>,

    /// Temperature for local llama.cpp (left hemisphere — low = deterministic).
    ///
    /// Env var: `WM_LLAMA_TEMP` (default: 0.2)
    #[serde(default)]
    pub llama_temp: Option<f32>,

    /// Cloud LLM API key (right hemisphere + self-play proposer).
    ///
    /// Env var: `WM_LLM_API_KEY`
    #[serde(default)]
    pub llm_api_key: Option<String>,

    /// Cloud LLM endpoint (OpenAI-compatible).
    ///
    /// Env var: `WM_LLM_ENDPOINT` (default: `https://api.openai.com/v1/chat/completions`)
    #[serde(default)]
    pub llm_endpoint: Option<String>,

    /// Cloud LLM model name.
    ///
    /// Env var: `WM_LLM_MODEL` (default: `gpt-4o-mini`)
    #[serde(default)]
    pub llm_model: Option<String>,

    /// Cloud LLM request timeout (milliseconds).
    ///
    /// Env var: `WM_LLM_TIMEOUT_MS` (default: 5000)
    #[serde(default)]
    pub llm_timeout_ms: Option<u64>,
}

/// Embedder configuration for NLU routing and vector search.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EmbedderConfig {
    /// Embedder endpoint URL (llama-server `/v1/embeddings`).
    ///
    /// Env var: `WM_EMBEDDER_ENDPOINT`
    #[serde(default)]
    pub endpoint: Option<String>,

    /// Embedder model name.
    ///
    /// Env var: `WM_EMBEDDER_MODEL` (default: `local`)
    #[serde(default)]
    pub model: Option<String>,

    /// Embedding dimensionality.
    ///
    /// Env var: `WM_EMBEDDER_DIM` (default: 384)
    #[serde(default)]
    pub dimension: Option<usize>,

    /// Request timeout (milliseconds).
    ///
    /// Env var: `WM_EMBEDDER_TIMEOUT_MS` (default: 30000)
    #[serde(default)]
    pub timeout_ms: Option<u64>,
}

/// Daemon schedule configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DaemonConfig {
    /// Interval between full cycle sweeps (seconds).
    #[serde(default = "default_cycle_interval")]
    pub cycle_interval_secs: u64,

    /// Interval between dream cycle runs (seconds).
    #[serde(default = "default_dream_interval")]
    pub dream_interval_secs: u64,

    /// Interval between brain-wave recompute ticks (seconds).
    #[serde(default = "default_brain_wave_interval")]
    pub brain_wave_interval_secs: u64,

    /// Interval between homeostasis refreshes (seconds).
    #[serde(default = "default_homeostasis_interval")]
    pub homeostasis_interval_secs: u64,

    /// Minimum health score to run cycles.
    #[serde(default = "default_min_health")]
    pub min_health_score: f32,

    /// Interval between RSI codegen cycles (seconds, 0 = disabled).
    #[serde(default)]
    pub codegen_interval_secs: u64,

    /// Auto-apply code patches that pass tests (dangerous).
    #[serde(default)]
    pub codegen_auto_apply: bool,

    /// Interval between dedicated Research cycles (seconds, 0 = with regular sweep).
    #[serde(default)]
    pub research_interval_secs: u64,

    /// Interval between self-play training cycles (seconds, 0 = disabled).
    #[serde(default)]
    pub selfplay_interval_secs: u64,

    /// Watchdog stall timeout (seconds, 0 = disabled).
    ///
    /// If the daemon main loop doesn't tick for this long, the watchdog
    /// forces a restart so a supervisor (Docker/systemd) brings it back.
    #[serde(default = "default_watchdog_timeout")]
    pub watchdog_timeout_secs: u64,
}

impl Default for DaemonConfig {
    fn default() -> Self {
        Self {
            cycle_interval_secs: 300,
            dream_interval_secs: 600,
            brain_wave_interval_secs: 30,
            homeostasis_interval_secs: 60,
            min_health_score: 0.3,
            codegen_interval_secs: 0,
            codegen_auto_apply: false,
            research_interval_secs: 0,
            selfplay_interval_secs: 0,
            watchdog_timeout_secs: 60,
        }
    }
}

const fn default_cycle_interval() -> u64 {
    300
}
const fn default_dream_interval() -> u64 {
    600
}
const fn default_brain_wave_interval() -> u64 {
    30
}
const fn default_homeostasis_interval() -> u64 {
    60
}
const fn default_min_health() -> f32 {
    0.3
}
const fn default_watchdog_timeout() -> u64 {
    60
}

impl WmConfig {
    /// Load configuration from a TOML file, then apply env var overrides.
    ///
    /// If the file doesn't exist, returns defaults with env overrides applied.
    /// If the file exists but is malformed, logs a warning and falls back to defaults.
    #[must_use]
    pub fn load(path: Option<&PathBuf>) -> Self {
        let mut config = if let Some(p) = path {
            Self::load_from_file(p)
        } else {
            // Try default config location: <store_dir>/config.toml
            let default_config = Self::default_config_path();
            if default_config.exists() {
                Self::load_from_file(&default_config)
            } else {
                Self::default()
            }
        };

        config.apply_env_overrides();
        config
    }

    /// Load from a specific TOML file path.
    fn load_from_file(path: &PathBuf) -> Self {
        match std::fs::read_to_string(path) {
            Ok(contents) => match toml::from_str::<Self>(&contents) {
                Ok(cfg) => {
                    tracing::info!("Loaded config from {}", path.display());
                    cfg
                }
                Err(e) => {
                    tracing::warn!("Failed to parse config at {}: {e}", path.display());
                    Self::default()
                }
            },
            Err(_) => Self::default(),
        }
    }

    /// Default config file path: `<store_dir>/config.toml`.
    fn default_config_path() -> PathBuf {
        Self::default_store_dir().join("config.toml")
    }

    /// Default store directory: `$XDG_DATA_HOME/whitemagic` or `~/.local/share/whitemagic`.
    fn default_store_dir() -> PathBuf {
        std::env::var("XDG_DATA_HOME").map_or_else(
            |_| {
                std::env::var("HOME").map_or_else(
                    |_| PathBuf::from(".whitemagic"),
                    |home| {
                        PathBuf::from(home)
                            .join(".local")
                            .join("share")
                            .join("whitemagic")
                    },
                )
            },
            |xdg| PathBuf::from(xdg).join("whitemagic"),
        )
    }

    /// Apply environment variable overrides on top of config file values.
    ///
    /// Env vars always take precedence over config file settings.
    fn apply_env_overrides(&mut self) {
        // Store
        if let Ok(path) = std::env::var("WM_STORE_PATH") {
            self.store.path = Some(PathBuf::from(path));
        }

        // LLM — local llama.cpp
        if let Ok(v) = std::env::var("WM_LLAMA_ENDPOINT") {
            if !v.is_empty() {
                self.llm.llama_endpoint = Some(v);
            }
        }
        if let Ok(v) = std::env::var("WM_LLAMA_MODEL") {
            self.llm.llama_model = Some(v);
        }
        if let Ok(v) = std::env::var("WM_LLAMA_TIMEOUT_MS") {
            if let Ok(ms) = v.parse::<u64>() {
                self.llm.llama_timeout_ms = Some(ms);
            }
        }
        if let Ok(v) = std::env::var("WM_LLAMA_MAX_TOKENS") {
            if let Ok(t) = v.parse::<u32>() {
                self.llm.llama_max_tokens = Some(t);
            }
        }
        if let Ok(v) = std::env::var("WM_LLAMA_TEMP") {
            if let Ok(t) = v.parse::<f32>() {
                self.llm.llama_temp = Some(t);
            }
        }

        // LLM — cloud
        if let Ok(v) = std::env::var("WM_LLM_API_KEY") {
            if !v.is_empty() {
                self.llm.llm_api_key = Some(v);
            }
        }
        if let Ok(v) = std::env::var("WM_LLM_ENDPOINT") {
            if !v.is_empty() {
                self.llm.llm_endpoint = Some(v);
            }
        }
        if let Ok(v) = std::env::var("WM_LLM_MODEL") {
            self.llm.llm_model = Some(v);
        }
        if let Ok(v) = std::env::var("WM_LLM_TIMEOUT_MS") {
            if let Ok(ms) = v.parse::<u64>() {
                self.llm.llm_timeout_ms = Some(ms);
            }
        }

        // Embedder
        if let Ok(v) = std::env::var("WM_EMBEDDER_ENDPOINT") {
            if !v.is_empty() {
                self.embedder.endpoint = Some(v);
            }
        }
        if let Ok(v) = std::env::var("WM_EMBEDDER_MODEL") {
            self.embedder.model = Some(v);
        }
        if let Ok(v) = std::env::var("WM_EMBEDDER_DIM") {
            if let Ok(d) = v.parse::<usize>() {
                self.embedder.dimension = Some(d);
            }
        }
        if let Ok(v) = std::env::var("WM_EMBEDDER_TIMEOUT_MS") {
            if let Ok(ms) = v.parse::<u64>() {
                self.embedder.timeout_ms = Some(ms);
            }
        }
    }

    /// Get the effective store path (config or default).
    #[must_use]
    pub fn store_path(&self) -> PathBuf {
        self.store
            .path
            .clone()
            .unwrap_or_else(Self::default_store_dir)
    }

    /// Convert daemon config to the `Duration`-based struct used by `run_daemon`.
    #[must_use]
    pub const fn daemon_durations(&self) -> crate::daemon::DaemonConfig {
        crate::daemon::DaemonConfig {
            cycle_interval: Duration::from_secs(self.daemon.cycle_interval_secs),
            dream_interval: Duration::from_secs(self.daemon.dream_interval_secs),
            brain_wave_interval: Duration::from_secs(self.daemon.brain_wave_interval_secs),
            homeostasis_interval: Duration::from_secs(self.daemon.homeostasis_interval_secs),
            min_health_score: self.daemon.min_health_score,
            serve_mcp: false,
            codegen_interval: Duration::from_secs(self.daemon.codegen_interval_secs),
            codegen_auto_apply: self.daemon.codegen_auto_apply,
            research_interval: Duration::from_secs(self.daemon.research_interval_secs),
            selfplay_interval: Duration::from_secs(self.daemon.selfplay_interval_secs),
            watchdog_timeout: Duration::from_secs(self.daemon.watchdog_timeout_secs),
        }
    }

    /// Set env vars from config so that `from_env()` calls in subsystems
    /// pick up the configured values.
    ///
    /// This bridges the gap between the config file and the existing
    /// env-var-based initialization in `LlamaLeftHemisphere::from_env()`,
    /// `LlmRightHemisphere::from_env()`, `HttpEmbedder`, etc.
    ///
    /// # Safety
    ///
    /// `std::env::set_var` is unsafe in Rust 2024 because it's not thread-safe.
    /// This method is safe to call because it's invoked in `main()` before
    /// any threads or async runtimes are spawned.
    #[allow(unsafe_code)]
    pub fn export_to_env(&self) {
        // SAFETY: This is called in main() before any threads or async runtime
        // are spawned, so there are no concurrent readers of env vars.
        unsafe {
            // LLM — local llama.cpp
            if let Some(ref v) = self.llm.llama_endpoint {
                if std::env::var("WM_LLAMA_ENDPOINT").is_err() {
                    std::env::set_var("WM_LLAMA_ENDPOINT", v);
                }
            }
            if let Some(ref v) = self.llm.llama_model {
                if std::env::var("WM_LLAMA_MODEL").is_err() {
                    std::env::set_var("WM_LLAMA_MODEL", v);
                }
            }
            if let Some(v) = self.llm.llama_timeout_ms {
                if std::env::var("WM_LLAMA_TIMEOUT_MS").is_err() {
                    std::env::set_var("WM_LLAMA_TIMEOUT_MS", v.to_string());
                }
            }
            if let Some(v) = self.llm.llama_max_tokens {
                if std::env::var("WM_LLAMA_MAX_TOKENS").is_err() {
                    std::env::set_var("WM_LLAMA_MAX_TOKENS", v.to_string());
                }
            }
            if let Some(v) = self.llm.llama_temp {
                if std::env::var("WM_LLAMA_TEMP").is_err() {
                    std::env::set_var("WM_LLAMA_TEMP", v.to_string());
                }
            }

            // LLM — cloud
            if let Some(ref v) = self.llm.llm_api_key {
                if std::env::var("WM_LLM_API_KEY").is_err() {
                    std::env::set_var("WM_LLM_API_KEY", v);
                }
            }
            if let Some(ref v) = self.llm.llm_endpoint {
                if std::env::var("WM_LLM_ENDPOINT").is_err() {
                    std::env::set_var("WM_LLM_ENDPOINT", v);
                }
            }
            if let Some(ref v) = self.llm.llm_model {
                if std::env::var("WM_LLM_MODEL").is_err() {
                    std::env::set_var("WM_LLM_MODEL", v);
                }
            }
            if let Some(v) = self.llm.llm_timeout_ms {
                if std::env::var("WM_LLM_TIMEOUT_MS").is_err() {
                    std::env::set_var("WM_LLM_TIMEOUT_MS", v.to_string());
                }
            }

            // Embedder
            if let Some(ref v) = self.embedder.endpoint {
                if std::env::var("WM_EMBEDDER_ENDPOINT").is_err() {
                    std::env::set_var("WM_EMBEDDER_ENDPOINT", v);
                }
            }
            if let Some(ref v) = self.embedder.model {
                if std::env::var("WM_EMBEDDER_MODEL").is_err() {
                    std::env::set_var("WM_EMBEDDER_MODEL", v);
                }
            }
            if let Some(v) = self.embedder.dimension {
                if std::env::var("WM_EMBEDDER_DIM").is_err() {
                    std::env::set_var("WM_EMBEDDER_DIM", v.to_string());
                }
            }
            if let Some(v) = self.embedder.timeout_ms {
                if std::env::var("WM_EMBEDDER_TIMEOUT_MS").is_err() {
                    std::env::set_var("WM_EMBEDDER_TIMEOUT_MS", v.to_string());
                }
            }
        }
    }

    /// Generate a sample `config.toml` string.
    #[must_use]
    pub fn sample_toml() -> String {
        r#"# WhiteMagic Configuration File
#
# Place this file at:
#   ~/.local/share/whitemagic/config.toml
# Or specify with: wm daemon --config /path/to/config.toml
#
# Environment variables override these values.
# CLI flags override everything.

[store]
# Path to the LMDB store directory.
# Default: ~/.local/share/whitemagic
# Env: WM_STORE_PATH
# path = "~/.local/share/whitemagic"

[llm]
# ── Local llama.cpp server (left hemisphere + world model + self-play solver) ──
# Start llama-server with: llama-server -m model.gguf --port 8080
# Env: WM_LLAMA_ENDPOINT
llama_endpoint = "http://localhost:8080"
# Env: WM_LLAMA_MODEL
llama_model = "local"
# Env: WM_LLAMA_TIMEOUT_MS (default: 10000)
llama_timeout_ms = 10000
# Env: WM_LLAMA_MAX_TOKENS (default: 512)
llama_max_tokens = 512
# Env: WM_LLAMA_TEMP (default: 0.2 — low for deterministic left hemisphere)
llama_temp = 0.2

# ── Cloud LLM (right hemisphere + self-play proposer) ──
# Leave api_key empty to use local llama.cpp for both hemispheres.
# Env: WM_LLM_API_KEY
llm_api_key = ""
# Env: WM_LLM_ENDPOINT (default: OpenAI)
llm_endpoint = "https://api.openai.com/v1/chat/completions"
# Env: WM_LLM_MODEL
llm_model = "gpt-4o-mini"
# Env: WM_LLM_TIMEOUT_MS (default: 5000)
llm_timeout_ms = 5000

[embedder]
# Embedder endpoint (llama-server /v1/embeddings).
# Usually same as llama_endpoint above.
# Env: WM_EMBEDDER_ENDPOINT
endpoint = "http://localhost:8080"
# Env: WM_EMBEDDER_MODEL
model = "local"
# Env: WM_EMBEDDER_DIM (default: 384)
dimension = 384
# Env: WM_EMBEDDER_TIMEOUT_MS (default: 30000)
timeout_ms = 30000

[daemon]
# Interval between full cycle sweeps (seconds)
cycle_interval_secs = 300
# Interval between dream cycle runs (seconds)
dream_interval_secs = 600
# Interval between brain-wave recompute ticks (seconds)
brain_wave_interval_secs = 30
# Interval between homeostasis refreshes (seconds)
homeostasis_interval_secs = 60
# Minimum health score to run cycles (0.0–1.0)
min_health_score = 0.3
# RSI codegen cycle interval (seconds, 0 = disabled)
codegen_interval_secs = 0
# Auto-apply code patches that pass tests (dangerous!)
codegen_auto_apply = false
# Dedicated Research cycle interval (seconds, 0 = with regular sweep)
research_interval_secs = 0
# Self-play training cycle interval (seconds, 0 = disabled)
selfplay_interval_secs = 0
# Watchdog stall timeout (seconds, 0 = disabled) — force-restart on daemon hang
watchdog_timeout_secs = 60
"#
        .to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_config_has_sensible_defaults() {
        let cfg = WmConfig::default();
        assert_eq!(cfg.daemon.cycle_interval_secs, 300);
        assert_eq!(cfg.daemon.dream_interval_secs, 600);
        assert_eq!(cfg.daemon.min_health_score, 0.3);
        assert_eq!(cfg.daemon.watchdog_timeout_secs, 60);
        assert!(!cfg.daemon.codegen_auto_apply);
    }

    #[test]
    fn load_from_nonexistent_file_returns_defaults() {
        let cfg = WmConfig::load_from_file(&PathBuf::from("/nonexistent/path/config.toml"));
        assert_eq!(cfg.daemon.cycle_interval_secs, 300);
    }

    #[test]
    fn parse_full_config_toml() {
        let toml_str = r#"
[store]
path = "/tmp/wm-test"

[llm]
llama_endpoint = "http://localhost:8080"
llama_model = "qwen2.5-3b"
llm_api_key = "sk-test"

[embedder]
endpoint = "http://localhost:8080"
dimension = 768

[daemon]
cycle_interval_secs = 120
dream_interval_secs = 300
selfplay_interval_secs = 600
"#;
        let cfg: WmConfig = toml::from_str(toml_str).unwrap();
        assert_eq!(cfg.store.path, Some(PathBuf::from("/tmp/wm-test")));
        assert_eq!(
            cfg.llm.llama_endpoint.as_deref(),
            Some("http://localhost:8080")
        );
        assert_eq!(cfg.llm.llama_model.as_deref(), Some("qwen2.5-3b"));
        assert_eq!(cfg.llm.llm_api_key.as_deref(), Some("sk-test"));
        assert_eq!(cfg.embedder.dimension, Some(768));
        assert_eq!(cfg.daemon.cycle_interval_secs, 120);
        assert_eq!(cfg.daemon.dream_interval_secs, 300);
        assert_eq!(cfg.daemon.selfplay_interval_secs, 600);
    }

    #[test]
    fn parse_partial_config_uses_defaults_for_missing() {
        let toml_str = r#"
[llm]
llama_endpoint = "http://localhost:8080"
"#;
        let cfg: WmConfig = toml::from_str(toml_str).unwrap();
        assert_eq!(
            cfg.llm.llama_endpoint.as_deref(),
            Some("http://localhost:8080")
        );
        // Missing fields use defaults
        assert_eq!(cfg.daemon.cycle_interval_secs, 300);
        assert_eq!(cfg.daemon.dream_interval_secs, 600);
    }

    #[test]
    fn daemon_durations_conversion() {
        let cfg = WmConfig {
            daemon: DaemonConfig {
                cycle_interval_secs: 120,
                dream_interval_secs: 240,
                brain_wave_interval_secs: 15,
                homeostasis_interval_secs: 30,
                min_health_score: 0.5,
                codegen_interval_secs: 600,
                codegen_auto_apply: true,
                research_interval_secs: 300,
                selfplay_interval_secs: 900,
                watchdog_timeout_secs: 120,
            },
            ..Default::default()
        };
        let d = cfg.daemon_durations();
        assert_eq!(d.cycle_interval, Duration::from_secs(120));
        assert_eq!(d.dream_interval, Duration::from_secs(240));
        assert_eq!(d.brain_wave_interval, Duration::from_secs(15));
        assert_eq!(d.homeostasis_interval, Duration::from_secs(30));
        assert_eq!(d.min_health_score, 0.5);
        assert_eq!(d.codegen_interval, Duration::from_secs(600));
        assert!(d.codegen_auto_apply);
        assert_eq!(d.research_interval, Duration::from_secs(300));
        assert_eq!(d.selfplay_interval, Duration::from_secs(900));
        assert_eq!(d.watchdog_timeout, Duration::from_secs(120));
    }

    #[test]
    fn sample_toml_is_valid() {
        let sample = WmConfig::sample_toml();
        let cfg: WmConfig = toml::from_str(&sample).unwrap();
        assert!(cfg.llm.llama_endpoint.is_some());
        assert!(cfg.embedder.endpoint.is_some());
        assert_eq!(cfg.daemon.cycle_interval_secs, 300);
    }

    #[test]
    fn store_path_uses_config_when_set() {
        let cfg = WmConfig {
            store: StoreConfig {
                path: Some(PathBuf::from("/custom/path")),
            },
            ..Default::default()
        };
        assert_eq!(cfg.store_path(), PathBuf::from("/custom/path"));
    }

    #[test]
    fn store_path_uses_default_when_unset() {
        let cfg = WmConfig::default();
        let path = cfg.store_path();
        // Should end with "whitemagic"
        assert!(
            path.ends_with("whitemagic"),
            "expected path ending with 'whitemagic', got {}",
            path.display()
        );
    }

    #[test]
    fn config_serialization_roundtrip() {
        let cfg = WmConfig {
            llm: LlmConfig {
                llama_endpoint: Some("http://localhost:8080".into()),
                llama_model: Some("test-model".into()),
                llm_api_key: Some("test-key".into()),
                ..Default::default()
            },
            daemon: DaemonConfig {
                cycle_interval_secs: 42,
                ..Default::default()
            },
            ..Default::default()
        };
        let toml_str = toml::to_string(&cfg).unwrap();
        let parsed: WmConfig = toml::from_str(&toml_str).unwrap();
        assert_eq!(
            parsed.llm.llama_endpoint.as_deref(),
            Some("http://localhost:8080")
        );
        assert_eq!(parsed.daemon.cycle_interval_secs, 42);
    }
}
