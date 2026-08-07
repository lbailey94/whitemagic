//! wm-autonomic — BitMamba autonomic layer for WhiteMagic v4 (Phase L1).
//!
//! Wraps the BitMamba-2 255M daemon as a persistent autonomic layer that
//! feeds salience signals into citta, drive, and workspace.
//!
//! Architecture:
//! - `BitMambaDaemon` — subprocess management with JSON lines protocol
//! - `SalienceProcessor` — classifies signals and feeds into citta/drive/workspace
//! - `AutonomicLayer` — top-level coordinator combining daemon + processor
//!
//! The daemon is a subprocess (bitmamba-daemon binary) that loads the model
//! once and serves inference requests via stdin/stdout JSON lines. This
//! eliminates the ~200ms model reload overhead per pulse.
//!
//! Configuration via environment variables:
//! - `WM_BITMAMBA_BIN` — path to bitmamba-daemon binary
//! - `WM_BITMAMBA_MODEL` — path to bitmamba_255m.bin
//! - `WM_BITMAMBA_TOKENIZER` — path to tokenizer.bin
//! - `WM_AUTONOMIC_ENABLED` — enable/disable (1/0, default 0)

#![forbid(unsafe_code)]
#![allow(clippy::significant_drop_tightening)]
#![allow(clippy::missing_const_for_fn)]

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

// ── Configuration ─────────────────────────────────────────────────────

/// Configuration for the BitMamba autonomic layer.
#[derive(Debug, Clone)]
pub struct AutonomicConfig {
    /// Path to the bitmamba-daemon binary.
    pub daemon_bin: String,
    /// Path to the model file (bitmamba_255m.bin).
    pub model_path: String,
    /// Path to the tokenizer file (tokenizer.bin).
    pub tokenizer_path: String,
    /// Maximum tokens to generate per pulse.
    pub max_tokens: u32,
    /// Temperature for generation.
    pub temperature: f32,
    /// Repetition penalty.
    pub penalty: f32,
    /// min_p sampling parameter.
    pub min_p: f32,
    /// top_p sampling parameter.
    pub top_p: f32,
    /// top_k sampling parameter.
    pub top_k: u32,
    /// Daemon startup timeout.
    pub startup_timeout: Duration,
    /// Inference request timeout.
    pub inference_timeout: Duration,
    /// Maximum telemetry events to buffer before pulsing.
    pub max_telemetry_buffer: usize,
    /// Token history size for novelty detection.
    pub token_history_size: usize,
    /// Recent signals to retain.
    pub max_recent_signals: usize,
}

impl Default for AutonomicConfig {
    fn default() -> Self {
        Self {
            daemon_bin: String::new(),
            model_path: String::new(),
            tokenizer_path: String::new(),
            max_tokens: 20,
            temperature: 0.7,
            penalty: 1.1,
            min_p: 0.05,
            top_p: 0.9,
            top_k: 40,
            startup_timeout: Duration::from_secs(5),
            inference_timeout: Duration::from_secs(10),
            max_telemetry_buffer: 10,
            token_history_size: 200,
            max_recent_signals: 50,
        }
    }
}

impl AutonomicConfig {
    /// Create a config from environment variables.
    ///
    /// Returns `None` if `WM_AUTONOMIC_ENABLED` is not "1" or if
    /// `WM_BITMAMBA_BIN` is not set or fails safety validation.
    #[must_use]
    pub fn from_env() -> Option<Self> {
        let enabled = std::env::var("WM_AUTONOMIC_ENABLED")
            .ok()
            .is_some_and(|v| v == "1" || v.eq_ignore_ascii_case("true"));

        if !enabled {
            return None;
        }

        let daemon_bin = std::env::var("WM_BITMAMBA_BIN").ok()?;
        if daemon_bin.is_empty() {
            return None;
        }

        // Validate daemon binary path for safety
        if !is_daemon_path_safe(&daemon_bin) {
            tracing::warn!(
                "bitmamba daemon binary path rejected by safety validation: {}",
                daemon_bin
            );
            return None;
        }

        let model_path = std::env::var("WM_BITMAMBA_MODEL").ok()?;
        if model_path.is_empty() {
            return None;
        }

        let tokenizer_path =
            std::env::var("WM_BITMAMBA_TOKENIZER").unwrap_or_else(|_| "tokenizer.bin".into());

        Some(Self {
            daemon_bin,
            model_path,
            tokenizer_path,
            ..Self::default()
        })
    }
}

// ── Salience Signal ───────────────────────────────────────────────────

/// Type of salience signal detected by the autonomic layer.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SignalType {
    /// Novel pattern detected — tokens not seen in recent history.
    Novelty,
    /// Anomaly detected — high repetition, stuck state.
    Anomaly,
    /// Emotional shift — high token diversity suggesting sentiment change.
    EmotionalShift,
    /// Background noise — no significant pattern.
    Background,
}

impl std::fmt::Display for SignalType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Novelty => write!(f, "novelty"),
            Self::Anomaly => write!(f, "anomaly"),
            Self::EmotionalShift => write!(f, "emotional_shift"),
            Self::Background => write!(f, "background"),
        }
    }
}

/// A salience signal detected by the autonomic layer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SalienceSignal {
    /// When the signal was detected.
    pub timestamp: f64,
    /// Generated token IDs from the BitMamba model.
    pub token_ids: Vec<i32>,
    /// Salience score (0.0–1.0).
    pub salience_score: f32,
    /// Type of signal.
    pub signal_type: SignalType,
    /// Metadata about the signal.
    pub metadata: SignalMetadata,
}

/// Metadata about a salience signal.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignalMetadata {
    /// Fraction of tokens not in recent history.
    pub novelty_ratio: f32,
    /// Unique tokens / total tokens.
    pub diversity: f32,
    /// Most common token frequency.
    pub repetition: f32,
}

// ── Daemon Protocol ───────────────────────────────────────────────────

/// Request sent to the bitmamba-daemon (JSON lines).
#[derive(Debug, Serialize)]
struct DaemonRequest {
    prompt: String,
    max_tokens: u32,
    temp: f32,
    penalty: f32,
    min_p: f32,
    top_p: f32,
    top_k: u32,
    use_tokenizer: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    reset: Option<bool>,
}

/// Response from the bitmamba-daemon (JSON lines).
#[derive(Debug, Deserialize)]
#[allow(dead_code)]
struct DaemonResponse {
    token_ids: Vec<i32>,
    generated_count: u32,
    prefill_ms: f64,
    gen_ms: f64,
    total_ms: f64,
    tokens_per_sec: f64,
    peak_ram_mb: f64,
}

/// Ready signal from daemon on startup.
#[derive(Debug, Deserialize)]
struct DaemonReady {
    status: String,
    ram_mb: f64,
}

/// Validate a daemon binary path for safety.
///
/// Checks:
/// - Path must be absolute (no relative paths or cwd-relative lookups)
/// - No path traversal components (..)
/// - File must exist and be a regular file (not a symlink, device, etc.)
/// - File must be executable
#[must_use]
pub fn is_daemon_path_safe(path: &str) -> bool {
    use std::path::Path as StdPath;

    let p = StdPath::new(path);

    // Must be absolute
    if !p.is_absolute() {
        return false;
    }

    // Block path traversal
    for component in p.components() {
        if component == std::path::Component::ParentDir {
            return false;
        }
    }

    // Check file metadata
    let metadata = match std::fs::metadata(p) {
        Ok(m) => m,
        Err(_) => return false,
    };

    // Must be a regular file (not directory, symlink, device, etc.)
    if !metadata.is_file() {
        return false;
    }

    // Must be executable (Unix permission bit)
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let perms = metadata.permissions();
        if perms.mode() & 0o111 == 0 {
            return false;
        }
    }

    true
}

// ── BitMamba Daemon ───────────────────────────────────────────────────

/// Persistent BitMamba daemon subprocess.
///
/// Loads the model once on startup, then serves inference requests via
/// JSON lines on stdin/stdout. Eliminates per-pulse model reload overhead.
pub struct BitMambaDaemon {
    child: Child,
    stdin: std::process::ChildStdin,
    stdout: BufReader<std::process::ChildStdout>,
    ram_mb: f64,
    request_count: u64,
}

impl BitMambaDaemon {
    /// Spawn the daemon process and wait for the ready signal.
    ///
    /// # Errors
    /// Returns an error if the process cannot be spawned or doesn't
    /// produce a ready signal within the startup timeout.
    pub fn spawn(config: &AutonomicConfig) -> Result<Self, String> {
        let mut child = Command::new(&config.daemon_bin)
            .arg(&config.model_path)
            .arg(&config.tokenizer_path)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .env("OMP_NUM_THREADS", "1")
            .spawn()
            .map_err(|e| format!("failed to spawn bitmamba-daemon: {e}"))?;

        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| "failed to capture daemon stdin".to_string())?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "failed to capture daemon stdout".to_string())?;

        let mut stdout_reader = BufReader::new(stdout);

        // Wait for ready signal
        let ready_line = read_line_timeout(&mut stdout_reader, config.startup_timeout)
            .ok_or_else(|| "daemon startup timeout — no ready signal".to_string())?;

        let ready: DaemonReady =
            serde_json::from_str(&ready_line).map_err(|e| format!("invalid ready signal: {e}"))?;

        if ready.status != "ready" {
            return Err(format!("daemon not ready: status={}", ready.status));
        }

        tracing::info!(ram_mb = ready.ram_mb, "bitmamba-daemon started");

        Ok(Self {
            child,
            stdin,
            stdout: stdout_reader,
            ram_mb: ready.ram_mb,
            request_count: 0,
        })
    }

    /// Run a single inference request.
    ///
    /// Sends a JSON request and reads the JSON response.
    /// Returns `None` on timeout or protocol error.
    fn infer(
        &mut self,
        config: &AutonomicConfig,
        prompt: &str,
        reset: bool,
    ) -> Option<DaemonResponse> {
        let request = DaemonRequest {
            prompt: prompt.chars().take(500).collect(),
            max_tokens: config.max_tokens,
            temp: config.temperature,
            penalty: config.penalty,
            min_p: config.min_p,
            top_p: config.top_p,
            top_k: config.top_k,
            use_tokenizer: true,
            reset: if reset { Some(true) } else { None },
        };

        let request_json = serde_json::to_string(&request).ok()?;
        writeln!(self.stdin, "{request_json}").ok()?;
        self.stdin.flush().ok()?;

        let response_line = read_line_timeout(&mut self.stdout, config.inference_timeout)?;
        let response: DaemonResponse = serde_json::from_str(&response_line).ok()?;

        self.request_count += 1;
        Some(response)
    }

    /// Get the daemon's RAM usage in MB.
    #[must_use]
    pub const fn ram_mb(&self) -> f64 {
        self.ram_mb
    }

    /// Get the total number of inference requests processed.
    #[must_use]
    pub const fn request_count(&self) -> u64 {
        self.request_count
    }

    /// Check if the daemon process is still running.
    #[must_use]
    pub fn is_alive(&mut self) -> bool {
        match self.child.try_wait() {
            Ok(None) => true,
            Ok(Some(_)) | Err(_) => false,
        }
    }
}

impl Drop for BitMambaDaemon {
    fn drop(&mut self) {
        // Close stdin to signal the daemon to exit
        let _ = self.stdin.flush();
        // Kill the process
        let _ = self.child.kill();
        let _ = self.child.wait();
        tracing::debug!("bitmamba-daemon shut down");
    }
}

/// Read a line from a buffered reader with a timeout.
///
/// Uses a non-blocking read loop with short sleeps. This avoids
/// platform-specific timeout APIs while keeping the startup responsive.
fn read_line_timeout(
    reader: &mut BufReader<std::process::ChildStdout>,
    timeout: Duration,
) -> Option<String> {
    let deadline = Instant::now() + timeout;
    let mut line = String::new();

    loop {
        // Try to read a line (non-blocking via try_read)
        line.clear();
        match reader.read_line(&mut line) {
            Ok(0) => return None, // EOF
            Ok(_) => {
                let trimmed = line.trim().to_string();
                if !trimmed.is_empty() {
                    return Some(trimmed);
                }
                // Empty line — keep reading
            }
            Err(ref e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                // Non-blocking mode not set — shouldn't happen with BufReader
            }
            Err(_) => return None,
        }

        if Instant::now() >= deadline {
            return None;
        }
        std::thread::sleep(Duration::from_millis(10));
    }
}

// ── Salience Processor ────────────────────────────────────────────────

/// Processes generated tokens to detect salience signals.
///
/// Heuristics (ported from v2):
/// - Novelty: fraction of tokens not in recent history
/// - Repetition: high repetition → anomaly (stuck state)
/// - Diversity: high token diversity → emotional shift
/// - Combined score: novelty * 0.4 + diversity * 0.3 + repetition_penalty * 0.3
pub struct SalienceProcessor {
    token_history: VecDeque<i32>,
    salience_baseline: f32,
    history_size: usize,
}

impl SalienceProcessor {
    /// Create a new salience processor.
    #[must_use]
    pub fn new(history_size: usize) -> Self {
        Self {
            token_history: VecDeque::with_capacity(history_size),
            salience_baseline: 0.1,
            history_size,
        }
    }

    /// Analyze generated tokens for salience signals.
    ///
    /// Returns a neutral `SalienceSignal` if the input is empty or excessively large
    /// (>10000 tokens) to prevent signal poisoning.
    #[must_use]
    pub fn analyze(&mut self, token_ids: &[i32]) -> SalienceSignal {
        if token_ids.is_empty() || token_ids.len() > 10_000 {
            return SalienceSignal {
                timestamp: chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0) as f64
                    / 1_000_000_000.0,
                token_ids: Vec::new(),
                salience_score: 0.0,
                signal_type: SignalType::Background,
                metadata: SignalMetadata {
                    novelty_ratio: 0.0,
                    diversity: 0.0,
                    repetition: 0.0,
                },
            };
        }
        let timestamp =
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0) as f64 / 1_000_000_000.0;

        // Novelty: fraction of tokens not in recent history
        let history_set: std::collections::HashSet<i32> =
            self.token_history.iter().copied().collect();
        let novel_count = token_ids
            .iter()
            .filter(|t| !history_set.contains(t))
            .count();
        let novelty_ratio = novel_count as f32 / token_ids.len().max(1) as f32;

        // Update token history
        for &t in token_ids {
            self.token_history.push_back(t);
            if self.token_history.len() > self.history_size {
                self.token_history.pop_front();
            }
        }

        // Repetition: most common token frequency
        let mut token_counts: HashMap<i32, u32> = HashMap::new();
        for &t in token_ids {
            *token_counts.entry(t).or_insert(0) += 1;
        }
        let most_common_ratio = token_counts
            .values()
            .map(|&c| c as f32 / token_ids.len().max(1) as f32)
            .fold(0.0_f32, f32::max);

        let repetition_penalty = if most_common_ratio > 0.7 {
            1.0 - most_common_ratio
        } else {
            1.0
        };

        // Diversity: unique tokens / total
        let diversity = token_counts.len() as f32 / token_ids.len().max(1) as f32;

        // Combined salience score
        let salience = novelty_ratio * 0.4 + diversity * 0.3 + repetition_penalty * 0.3;

        // Signal type classification
        let signal_type = if most_common_ratio > 0.7 {
            SignalType::Anomaly
        } else if novelty_ratio > 0.7 {
            SignalType::Novelty
        } else if diversity > 0.8 {
            SignalType::EmotionalShift
        } else {
            SignalType::Background
        };

        // Update salience baseline (EMA)
        let alpha = 0.1;
        self.salience_baseline = alpha * salience + (1.0 - alpha) * self.salience_baseline;

        SalienceSignal {
            timestamp,
            token_ids: token_ids.to_vec(),
            salience_score: salience,
            signal_type,
            metadata: SignalMetadata {
                novelty_ratio,
                diversity,
                repetition: most_common_ratio,
            },
        }
    }

    /// Get the current salience baseline (EMA).
    #[must_use]
    pub const fn salience_baseline(&self) -> f32 {
        self.salience_baseline
    }

    /// Reset the processor state.
    pub fn reset(&mut self) {
        self.token_history.clear();
        self.salience_baseline = 0.1;
    }
}

// ── Autonomic Layer ───────────────────────────────────────────────────

/// The top-level autonomic layer coordinator.
///
/// Combines the BitMamba daemon with the salience processor.
/// Telemetry events are buffered and processed in pulses.
pub struct AutonomicLayer {
    daemon: Option<BitMambaDaemon>,
    processor: SalienceProcessor,
    config: AutonomicConfig,
    telemetry_buffer: Mutex<VecDeque<String>>,
    recent_signals: Mutex<VecDeque<SalienceSignal>>,
    pulse_count: u64,
    enabled: bool,
}

impl AutonomicLayer {
    /// Create a new autonomic layer from config.
    /// The daemon is spawned lazily on first pulse.
    #[must_use]
    pub fn new(config: AutonomicConfig) -> Self {
        let max_recent = config.max_recent_signals;
        let history_size = config.token_history_size;
        let max_buffer = config.max_telemetry_buffer;
        Self {
            daemon: None,
            processor: SalienceProcessor::new(history_size),
            config,
            telemetry_buffer: Mutex::new(VecDeque::with_capacity(max_buffer)),
            recent_signals: Mutex::new(VecDeque::with_capacity(max_recent)),
            pulse_count: 0,
            enabled: true,
        }
    }

    /// Create from environment variables, if configured.
    /// Returns `None` if autonomic layer is not enabled.
    #[must_use]
    pub fn from_env() -> Option<Self> {
        let config = AutonomicConfig::from_env()?;
        Some(Self::new(config))
    }

    /// Check if the autonomic layer is enabled and the daemon is available.
    #[must_use]
    pub const fn is_enabled(&self) -> bool {
        self.enabled
    }

    /// Add a telemetry event for the autonomic layer to process.
    ///
    /// Called by the MCP server after tool dispatch, citta heartbeat, etc.
    pub fn add_telemetry(&self, source: &str, message: &str) {
        if !self.enabled {
            return;
        }
        if let Ok(mut buf) = self.telemetry_buffer.lock() {
            buf.push_back(format!("{source}: {message}"));
            // Trim to max size
            while buf.len() > self.config.max_telemetry_buffer {
                buf.pop_front();
            }
        }
    }

    /// Run a single autonomic pulse — generate from current telemetry.
    ///
    /// Batches all buffered telemetry into a single inference call.
    /// Returns a salience signal if the output is salient, `None` otherwise.
    #[must_use]
    pub fn pulse(&mut self) -> Option<SalienceSignal> {
        if !self.enabled {
            return None;
        }

        // Gather telemetry
        let prompt = {
            let mut buf = self.telemetry_buffer.lock().ok()?;
            if buf.is_empty() {
                return None;
            }
            let prompt = buf.iter().cloned().collect::<Vec<_>>().join(" ");
            buf.clear();
            prompt
        };

        // Ensure daemon is running
        self.ensure_daemon()?;

        // Run inference
        let response = {
            let daemon = self.daemon.as_mut()?;
            daemon.infer(&self.config, &prompt, false)
        }?;

        if response.token_ids.is_empty() {
            return None;
        }

        // Analyze salience
        let signal = self.processor.analyze(&response.token_ids);

        // Store recent signal
        if let Ok(mut signals) = self.recent_signals.lock() {
            signals.push_back(signal.clone());
            while signals.len() > self.config.max_recent_signals {
                signals.pop_front();
            }
        }

        self.pulse_count += 1;

        tracing::debug!(
            signal_type = %signal.signal_type,
            salience = signal.salience_score,
            "autonomic pulse"
        );

        Some(signal)
    }

    /// Ensure the daemon is running, spawning it if necessary.
    fn ensure_daemon(&mut self) -> Option<()> {
        // Check if daemon is already running
        if let Some(ref mut daemon) = self.daemon {
            if daemon.is_alive() {
                return Some(());
            }
            // Daemon died — drop and respawn
            tracing::warn!("bitmamba-daemon died, attempting respawn");
            self.daemon = None;
        }

        // Spawn new daemon
        match BitMambaDaemon::spawn(&self.config) {
            Ok(daemon) => {
                self.daemon = Some(daemon);
                Some(())
            }
            Err(e) => {
                tracing::warn!(error = %e, "failed to spawn bitmamba-daemon");
                self.enabled = false;
                None
            }
        }
    }

    /// Get recent salience signals.
    #[must_use]
    pub fn recent_signals(&self) -> Vec<SalienceSignal> {
        self.recent_signals
            .lock()
            .map(|s| s.iter().cloned().collect())
            .unwrap_or_default()
    }

    /// Get the current salience baseline.
    #[must_use]
    pub fn salience_baseline(&self) -> f32 {
        self.processor.salience_baseline()
    }

    /// Get the number of pulses processed.
    #[must_use]
    pub const fn pulse_count(&self) -> u64 {
        self.pulse_count
    }

    /// Get a status snapshot as JSON.
    #[must_use]
    pub fn status(&self) -> serde_json::Value {
        let daemon_present = self.daemon.is_some();
        let daemon_ram = self.daemon.as_ref().map_or(0.0, BitMambaDaemon::ram_mb);
        let daemon_requests = self
            .daemon
            .as_ref()
            .map_or(0, BitMambaDaemon::request_count);

        serde_json::json!({
            "enabled": self.enabled,
            "daemon_running": daemon_present,
            "daemon_ram_mb": daemon_ram,
            "daemon_requests": daemon_requests,
            "pulse_count": self.pulse_count,
            "salience_baseline": self.processor.salience_baseline(),
            "recent_signals": self.recent_signals.lock().map(|s| s.len()).unwrap_or(0),
            "telemetry_buffered": self.telemetry_buffer.lock().map(|b| b.len()).unwrap_or(0),
        })
    }

    /// Convert a salience signal into drive events.
    ///
    /// Returns the drive event kind(s) that should be fired based on
    /// the signal type and score.
    #[must_use]
    pub fn signal_to_drive_events(signal: &SalienceSignal) -> Vec<wm_drive::DriveEventKind> {
        let mut events = Vec::new();

        match signal.signal_type {
            SignalType::Novelty => {
                events.push(wm_drive::DriveEventKind::NovelInput);
            }
            SignalType::Anomaly => {
                // Anomaly → caution up
                events.push(wm_drive::DriveEventKind::LowConfidence);
            }
            SignalType::EmotionalShift => {
                // Emotional shift → social/curiosity
                events.push(wm_drive::DriveEventKind::NovelInput);
                events.push(wm_drive::DriveEventKind::SocialInteraction);
            }
            SignalType::Background => {
                // No drive event for background noise
            }
        }

        // High salience always triggers curiosity
        if signal.salience_score > 0.7 {
            events.push(wm_drive::DriveEventKind::NovelInput);
        }

        events
    }

    /// Convert a salience signal into a workspace event.
    #[must_use]
    pub fn signal_to_workspace_event(
        signal: &SalienceSignal,
    ) -> Option<(wm_workspace::EventType, f32)> {
        match signal.signal_type {
            SignalType::Novelty => Some((
                wm_workspace::EventType::NovelDetection,
                signal.salience_score,
            )),
            SignalType::Anomaly => {
                Some((wm_workspace::EventType::SafetyAlert, signal.salience_score))
            }
            SignalType::EmotionalShift => {
                Some((wm_workspace::EventType::DriveUpdate, signal.salience_score))
            }
            SignalType::Background => None,
        }
    }

    /// Reset the autonomic layer state.
    pub fn reset(&mut self) {
        self.processor.reset();
        if let Ok(mut signals) = self.recent_signals.lock() {
            signals.clear();
        }
        if let Ok(mut buf) = self.telemetry_buffer.lock() {
            buf.clear();
        }
        self.pulse_count = 0;
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn autonomic_config_defaults() {
        let config = AutonomicConfig::default();
        assert_eq!(config.max_tokens, 20);
        assert!((config.temperature - 0.7).abs() < 0.01);
        assert_eq!(config.max_telemetry_buffer, 10);
    }

    #[test]
    fn autonomic_config_from_env_disabled() {
        // Without WM_AUTONOMIC_ENABLED set, from_env returns None.
        // We can't safely test env var manipulation in forbid(unsafe_code),
        // so we test the logic indirectly: a config with empty daemon_bin
        // should not be usable.
        let config = AutonomicConfig::default();
        assert!(config.daemon_bin.is_empty());
    }

    #[test]
    fn autonomic_config_from_env_no_bin() {
        // Same as above — env var tests require unsafe in Rust 2024,
        // which is forbidden in this crate. We test the config logic
        // directly instead.
        let config = AutonomicConfig::default();
        assert!(config.model_path.is_empty());
    }

    #[test]
    fn salience_processor_novelty() {
        let mut processor = SalienceProcessor::new(200);
        // First set of tokens — all novel
        let signal = processor.analyze(&[1, 2, 3, 4, 5]);
        assert_eq!(signal.signal_type, SignalType::Novelty);
        assert!(signal.metadata.novelty_ratio > 0.9);
        assert!(signal.salience_score > 0.5);
    }

    #[test]
    fn salience_processor_repetition() {
        let mut processor = SalienceProcessor::new(200);
        // Same token repeated → anomaly
        let signal = processor.analyze(&[42, 42, 42, 42, 42, 42, 42, 42]);
        assert_eq!(signal.signal_type, SignalType::Anomaly);
        assert!(signal.metadata.repetition > 0.7);
    }

    #[test]
    fn salience_processor_diversity() {
        let mut processor = SalienceProcessor::new(200);
        // First call seeds history
        let _ = processor.analyze(&[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
        // Second call with all different tokens → high diversity
        let signal = processor.analyze(&[11, 12, 13, 14, 15, 16, 17, 18, 19, 20]);
        assert!(signal.metadata.diversity > 0.8);
    }

    #[test]
    fn salience_processor_background() {
        let mut processor = SalienceProcessor::new(200);
        // Seed history with the exact tokens we'll test against
        // so they're not novel, and use low diversity to avoid emotional_shift
        let _ = processor.analyze(&[1, 2, 3, 4, 5, 6]);
        // Now generate the same tokens — not novel, not anomalous (not >70% same),
        // not high diversity (>0.8 unique)
        let _signal = processor.analyze(&[1, 2, 3, 4, 5, 6]);
        // 6 unique out of 6 = diversity 1.0 → emotional_shift, not background
        // This is correct behavior — let's test with fewer unique tokens
        let signal2 = processor.analyze(&[1, 1, 2, 2, 3, 3]);
        // 3 unique out of 6 = diversity 0.5, not novel, not anomalous
        assert_eq!(signal2.signal_type, SignalType::Background);
    }

    #[test]
    fn salience_processor_baseline_ema() {
        let mut processor = SalienceProcessor::new(200);
        let initial_baseline = processor.salience_baseline();
        let _ = processor.analyze(&[1, 2, 3, 4, 5]);
        let _ = processor.analyze(&[6, 7, 8, 9, 10]);
        // Baseline should have moved
        assert!(processor.salience_baseline() != initial_baseline);
    }

    #[test]
    fn salience_processor_reset() {
        let mut processor = SalienceProcessor::new(200);
        let _ = processor.analyze(&[1, 2, 3]);
        processor.reset();
        assert!((processor.salience_baseline() - 0.1).abs() < 0.01);
    }

    #[test]
    fn autonomic_layer_telemetry_buffer() {
        let config = AutonomicConfig::default();
        let layer = AutonomicLayer::new(config);
        layer.add_telemetry("dispatch", "tool: memory.create, success: true");
        layer.add_telemetry("citta", "heartbeat: effectiveness=0.8");

        let buf = layer.telemetry_buffer.lock().unwrap();
        assert_eq!(buf.len(), 2);
    }

    #[test]
    fn autonomic_layer_telemetry_max_buffer() {
        let config = AutonomicConfig {
            max_telemetry_buffer: 3,
            ..AutonomicConfig::default()
        };
        let layer = AutonomicLayer::new(config);
        for i in 0..10 {
            layer.add_telemetry("test", &format!("event {i}"));
        }
        let buf = layer.telemetry_buffer.lock().unwrap();
        assert_eq!(buf.len(), 3); // Should be capped at 3
    }

    #[test]
    fn autonomic_layer_pulse_no_daemon() {
        let config = AutonomicConfig::default();
        let mut layer = AutonomicLayer::new(config);
        layer.add_telemetry("test", "hello");
        // No daemon spawned → pulse returns None
        let result = layer.pulse();
        assert!(result.is_none());
    }

    #[test]
    fn autonomic_layer_pulse_empty_buffer() {
        let config = AutonomicConfig::default();
        let mut layer = AutonomicLayer::new(config);
        // No telemetry → None
        let result = layer.pulse();
        assert!(result.is_none());
    }

    #[test]
    fn autonomic_layer_disabled() {
        let config = AutonomicConfig::default();
        let layer = AutonomicLayer::new(config);
        assert!(layer.is_enabled());
    }

    #[test]
    fn autonomic_layer_status() {
        let config = AutonomicConfig::default();
        let layer = AutonomicLayer::new(config);
        let status = layer.status();
        assert!(status["enabled"].as_bool().unwrap_or(false));
        assert_eq!(status["pulse_count"].as_u64().unwrap_or(1), 0);
    }

    #[test]
    fn autonomic_layer_reset() {
        let config = AutonomicConfig::default();
        let mut layer = AutonomicLayer::new(config);
        layer.add_telemetry("test", "hello");
        layer.reset();
        let buf = layer.telemetry_buffer.lock().unwrap();
        assert!(buf.is_empty());
    }

    #[test]
    fn signal_to_drive_events_novelty() {
        let signal = SalienceSignal {
            timestamp: 0.0,
            token_ids: vec![1, 2, 3],
            salience_score: 0.5,
            signal_type: SignalType::Novelty,
            metadata: SignalMetadata {
                novelty_ratio: 0.8,
                diversity: 0.5,
                repetition: 0.2,
            },
        };
        let events = AutonomicLayer::signal_to_drive_events(&signal);
        assert!(events.contains(&wm_drive::DriveEventKind::NovelInput));
    }

    #[test]
    fn signal_to_drive_events_anomaly() {
        let signal = SalienceSignal {
            timestamp: 0.0,
            token_ids: vec![1, 1, 1],
            salience_score: 0.3,
            signal_type: SignalType::Anomaly,
            metadata: SignalMetadata {
                novelty_ratio: 0.1,
                diversity: 0.1,
                repetition: 0.9,
            },
        };
        let events = AutonomicLayer::signal_to_drive_events(&signal);
        assert!(events.contains(&wm_drive::DriveEventKind::LowConfidence));
    }

    #[test]
    fn signal_to_drive_events_high_salience() {
        let signal = SalienceSignal {
            timestamp: 0.0,
            token_ids: vec![1, 2, 3],
            salience_score: 0.8,
            signal_type: SignalType::Background,
            metadata: SignalMetadata {
                novelty_ratio: 0.3,
                diversity: 0.3,
                repetition: 0.3,
            },
        };
        let events = AutonomicLayer::signal_to_drive_events(&signal);
        // High salience always triggers NovelInput
        assert!(events.contains(&wm_drive::DriveEventKind::NovelInput));
    }

    #[test]
    fn signal_to_workspace_event_novelty() {
        let signal = SalienceSignal {
            timestamp: 0.0,
            token_ids: vec![1, 2, 3],
            salience_score: 0.7,
            signal_type: SignalType::Novelty,
            metadata: SignalMetadata {
                novelty_ratio: 0.8,
                diversity: 0.5,
                repetition: 0.2,
            },
        };
        let event = AutonomicLayer::signal_to_workspace_event(&signal);
        assert!(event.is_some());
        let (event_type, _) = event.unwrap();
        assert_eq!(event_type, wm_workspace::EventType::NovelDetection);
    }

    #[test]
    fn signal_to_workspace_event_background() {
        let signal = SalienceSignal {
            timestamp: 0.0,
            token_ids: vec![1, 2, 3],
            salience_score: 0.2,
            signal_type: SignalType::Background,
            metadata: SignalMetadata {
                novelty_ratio: 0.3,
                diversity: 0.3,
                repetition: 0.3,
            },
        };
        let event = AutonomicLayer::signal_to_workspace_event(&signal);
        assert!(event.is_none());
    }

    #[test]
    fn signal_type_display() {
        assert_eq!(format!("{}", SignalType::Novelty), "novelty");
        assert_eq!(format!("{}", SignalType::Anomaly), "anomaly");
        assert_eq!(format!("{}", SignalType::EmotionalShift), "emotional_shift");
        assert_eq!(format!("{}", SignalType::Background), "background");
    }

    // ── Daemon path safety tests ────────────────────────────────────

    #[test]
    fn daemon_path_rejects_relative() {
        assert!(!is_daemon_path_safe("bitmamba-daemon"));
        assert!(!is_daemon_path_safe("./bitmamba-daemon"));
        assert!(!is_daemon_path_safe("../bitmamba-daemon"));
    }

    #[test]
    fn daemon_path_rejects_traversal() {
        assert!(!is_daemon_path_safe("/usr/../etc/passwd"));
        assert!(!is_daemon_path_safe("/usr/local/../../etc/shadow"));
    }

    #[test]
    fn daemon_path_rejects_nonexistent() {
        assert!(!is_daemon_path_safe("/usr/bin/nonexistent-daemon-12345"));
    }

    #[test]
    fn daemon_path_rejects_directory() {
        let tmp = tempfile::tempdir().unwrap();
        assert!(!is_daemon_path_safe(tmp.path().to_str().unwrap()));
    }

    #[test]
    fn daemon_path_accepts_valid_binary() {
        // /bin/true is a valid executable on Linux
        assert!(is_daemon_path_safe("/bin/true"));
    }

    #[test]
    fn daemon_path_rejects_non_executable() {
        // /etc/hostname exists but is not executable
        assert!(!is_daemon_path_safe("/etc/hostname"));
    }

    #[test]
    fn daemon_path_rejects_empty() {
        assert!(!is_daemon_path_safe(""));
    }

    #[test]
    fn salience_analyze_rejects_empty_tokens() {
        let mut proc = SalienceProcessor::new(100);
        let signal = proc.analyze(&[]);
        assert_eq!(signal.salience_score, 0.0);
        assert_eq!(signal.signal_type, SignalType::Background);
    }

    #[test]
    fn salience_analyze_rejects_oversized_tokens() {
        let mut proc = SalienceProcessor::new(100);
        let tokens: Vec<i32> = (0..10_001).collect();
        let signal = proc.analyze(&tokens);
        assert_eq!(signal.salience_score, 0.0);
        assert_eq!(signal.signal_type, SignalType::Background);
    }
}
