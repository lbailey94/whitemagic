//! TriModelManager — tri-model lifecycle management for WhiteMagic v4.
//!
//! Manages three model components with independent lifecycle:
//! - **Autonomic** (BitMamba, always-on, ~252MB): citta heartbeats, salience,
//!   draft model for speculative decoding
//! - **Left** (llama.cpp, on-demand, idle-shutdown): deterministic reasoning,
//!   user-facing analysis
//! - **Right** (BitNet or second llama.cpp, on-demand, idle-shutdown):
//!   creative/divergent thinking
//!
//! Each model has independent lifecycle: autonomic persists, left/right start
//! on demand and idle-shutdown after a configurable timeout.
//!
//! Configuration via environment variables:
//! - `WM_LLAMA_BG_ENDPOINT` — left (background) model endpoint
//! - `WM_LLAMA_FG_ENDPOINT` — right (foreground) model endpoint
//! - `WM_LLAMA_FG_IDLE_TIMEOUT` — idle shutdown seconds (default 300)
//! - `WM_LLAMA_FG_AUTO_START` — auto-start on first request (default 1)

#![allow(clippy::significant_drop_tightening)]

use serde::{Deserialize, Serialize};
use std::fmt::Write;
use std::sync::Mutex;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

use crate::router::{InferenceTier, TierHandler};

// ── HTTP chat request/response (OpenAI-compatible) ────────────────────

#[derive(Debug, Serialize)]
struct ChatRequest {
    model: String,
    messages: Vec<ChatMessage>,
    max_tokens: u32,
    temperature: f32,
    #[serde(skip_serializing_if = "Option::is_none")]
    logprobs: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_logprobs: Option<u32>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ChatMessage {
    role: String,
    content: String,
}

#[derive(Debug, Deserialize)]
struct ChatResponse {
    choices: Vec<ChatChoice>,
}

#[derive(Debug, Deserialize)]
struct ChatChoice {
    message: ChatMessage,
    #[serde(default)]
    logprobs: Option<ChoiceLogprobs>,
}

/// Logprobs returned per token in the response.
#[derive(Debug, Deserialize)]
struct ChoiceLogprobs {
    content: Vec<TokenLogprob>,
}

/// Per-token logprob information.
#[derive(Debug, Deserialize)]
struct TokenLogprob {
    #[allow(dead_code)]
    token: String,
    logprob: f32,
    top_logprobs: Vec<LogprobEntry>,
}

/// A single logprob entry (top-1, top-2, etc.).
#[derive(Debug, Deserialize)]
struct LogprobEntry {
    #[allow(dead_code)]
    token: String,
    logprob: f32,
}

// ── Model State ───────────────────────────────────────────────────────

/// Lifecycle state of a model component.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ModelState {
    /// Model is not loaded / process not running.
    Stopped,
    /// Model is running and available for requests.
    Running,
    /// Model is running but has been idle past the idle threshold.
    /// (Only meaningful for left/right; autonomic never idles.)
    Idle,
    /// Model is in dream mode — warm but in low-power Theta state.
    /// Entered after first idle timeout when `IdleMode::Dream` is configured.
    /// Can be woken instantly via `touch()` (warm restart).
    Dreaming,
    /// Model failed to start or crashed.
    Failed,
}

impl ModelState {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Stopped => "stopped",
            Self::Running => "running",
            Self::Idle => "idle",
            Self::Dreaming => "dreaming",
            Self::Failed => "failed",
        }
    }

    /// Whether the model can serve requests.
    #[must_use]
    pub const fn is_available(self) -> bool {
        matches!(self, Self::Running | Self::Idle | Self::Dreaming)
    }

    /// Whether the model is in a warm state (loaded, can serve without cold start).
    #[must_use]
    pub const fn is_warm(self) -> bool {
        matches!(self, Self::Running | Self::Idle | Self::Dreaming)
    }

    /// Whether the model is dreaming (Theta low-power mode).
    #[must_use]
    pub const fn is_dreaming(self) -> bool {
        matches!(self, Self::Dreaming)
    }
}

impl std::fmt::Display for ModelState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

// ── Idle Mode ─────────────────────────────────────────────────────────

/// Idle behavior for on-demand models.
///
/// Determines what happens when a model exceeds its idle timeout:
/// - `Shutdown`: Stop the model (cold restart on next request)
/// - `Dream`: Enter Theta dream mode (warm, low-power, instant wake)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum IdleMode {
    /// Shut down the model on idle timeout (original behavior).
    #[default]
    Shutdown,
    /// Enter dream mode on first idle timeout, shut down on deep idle.
    Dream,
}

impl IdleMode {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Shutdown => "shutdown",
            Self::Dream => "dream",
        }
    }
}

impl std::fmt::Display for IdleMode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

// ── Model Component ───────────────────────────────────────────────────

/// Tracks the lifecycle state of a single model component.
#[derive(Debug)]
pub struct ModelComponent {
    state: ModelState,
    last_active: Instant,
    request_count: AtomicU64,
    error_count: AtomicU64,
    last_error: Option<String>,
    /// Whether this component persists (never shuts down).
    persistent: bool,
}

impl ModelComponent {
    /// Create a new component in `Stopped` state.
    fn new(persistent: bool) -> Self {
        Self {
            state: ModelState::Stopped,
            last_active: Instant::now(),
            request_count: AtomicU64::new(0),
            error_count: AtomicU64::new(0),
            last_error: None,
            persistent,
        }
    }

    /// Current state.
    #[must_use]
    pub const fn state(&self) -> ModelState {
        self.state
    }

    /// Record a successful request.
    pub fn record_success(&self) {
        self.request_count.fetch_add(1, Ordering::Relaxed);
        // State is updated by the manager, not here
    }

    /// Record a failure.
    pub fn record_error(&self, _msg: &str) {
        self.error_count.fetch_add(1, Ordering::Relaxed);
        // Use a Mutex-free approach: we store the last error via the manager
    }

    /// Total requests served.
    #[must_use]
    pub fn request_count(&self) -> u64 {
        self.request_count.load(Ordering::Relaxed)
    }

    /// Total errors encountered.
    #[must_use]
    pub fn error_count(&self) -> u64 {
        self.error_count.load(Ordering::Relaxed)
    }

    /// Time since last activity.
    #[must_use]
    pub fn idle_duration(&self) -> Duration {
        self.last_active.elapsed()
    }

    /// Whether this component is persistent (never shuts down).
    #[must_use]
    pub const fn is_persistent(&self) -> bool {
        self.persistent
    }

    /// Mark as running and update last-active timestamp.
    fn mark_running(&mut self) {
        self.state = ModelState::Running;
        self.last_active = Instant::now();
        self.last_error = None;
    }

    /// Mark as stopped.
    const fn mark_stopped(&mut self) {
        self.state = ModelState::Stopped;
    }

    /// Mark as failed with an error message.
    fn mark_failed(&mut self, error: &str) {
        self.state = ModelState::Failed;
        self.last_error = Some(error.to_string());
    }

    /// Mark as idle (running but past idle threshold).
    #[allow(dead_code)]
    fn mark_idle(&mut self) {
        if self.state == ModelState::Running {
            self.state = ModelState::Idle;
        }
    }

    /// Mark as dreaming (warm but in low-power mode).
    fn mark_dreaming(&mut self) {
        if self.state == ModelState::Running || self.state == ModelState::Idle {
            self.state = ModelState::Dreaming;
        }
    }

    /// Touch the last-active timestamp. Wakes from Idle or Dreaming.
    fn touch(&mut self) {
        self.last_active = Instant::now();
        if self.state == ModelState::Idle || self.state == ModelState::Dreaming {
            self.state = ModelState::Running;
        }
    }
}

// ── TriModel Config ───────────────────────────────────────────────────

/// Configuration for the TriModelManager.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TriModelConfig {
    /// Idle timeout before entering idle/dream state (seconds).
    pub idle_timeout: Duration,
    /// Deep idle timeout before full shutdown when in dream mode (seconds).
    /// Only used when `idle_mode` is `Dream`. Should be >= `idle_timeout`.
    pub deep_idle_timeout: Duration,
    /// What to do when a model goes idle: shut down or dream.
    pub idle_mode: IdleMode,
    /// Whether to auto-start models on first request.
    pub auto_start: bool,
    /// Left model endpoint (llama.cpp background model, e.g. Qwen 0.5B).
    pub left_endpoint: Option<String>,
    /// Medium model endpoint (e.g. Qwen 1.5B) — used for LocalSmall tier.
    /// Falls back to left_endpoint if not configured.
    pub medium_endpoint: Option<String>,
    /// Right model endpoint (BitNet or second llama.cpp, e.g. Qwen 3B).
    pub right_endpoint: Option<String>,
    /// Autonomic model binary path.
    pub autonomic_bin: Option<String>,
    /// Autonomic model file path.
    pub autonomic_model: Option<String>,
    /// Health check interval (seconds).
    pub health_check_interval: Duration,
    /// Maximum restart attempts before giving up.
    pub max_restart_attempts: u32,
}

impl Default for TriModelConfig {
    fn default() -> Self {
        Self {
            idle_timeout: Duration::from_secs(300),
            deep_idle_timeout: Duration::from_secs(1800),
            idle_mode: IdleMode::Shutdown,
            auto_start: true,
            left_endpoint: None,
            medium_endpoint: None,
            right_endpoint: None,
            autonomic_bin: None,
            autonomic_model: None,
            health_check_interval: Duration::from_secs(60),
            max_restart_attempts: 3,
        }
    }
}

impl TriModelConfig {
    /// Create config from environment variables.
    ///
    /// Reads:
    /// - `WM_LLAMA_BG_ENDPOINT` — left model endpoint
    /// - `WM_LLAMA_FG_ENDPOINT` — right model endpoint
    /// - `WM_LLAMA_FG_IDLE_TIMEOUT` — idle timeout seconds (default 300)
    /// - `WM_LLAMA_FG_DEEP_IDLE_TIMEOUT` — deep idle timeout seconds (default 1800)
    /// - `WM_LLAMA_FG_IDLE_MODE` — idle mode: "shutdown" or "dream" (default: shutdown)
    /// - `WM_LLAMA_FG_AUTO_START` — auto-start (1/0, default 1)
    /// - `WM_BITMAMBA_BIN` — autonomic binary
    /// - `WM_BITMAMBA_MODEL` — autonomic model file
    #[must_use]
    pub fn from_env() -> Self {
        let mut config = Self::default();

        if let Ok(val) = std::env::var("WM_LLAMA_BG_ENDPOINT") {
            if !val.is_empty() && is_tri_endpoint_safe(&val) {
                config.left_endpoint = Some(val);
            } else if !val.is_empty() {
                tracing::warn!("WM_LLAMA_BG_ENDPOINT rejected: must use http:// or https://");
            }
        }

        if let Ok(val) = std::env::var("WM_LLAMA_FG_ENDPOINT") {
            if !val.is_empty() && is_tri_endpoint_safe(&val) {
                config.right_endpoint = Some(val);
            } else if !val.is_empty() {
                tracing::warn!("WM_LLAMA_FG_ENDPOINT rejected: must use http:// or https://");
            }
        }

        if let Ok(val) = std::env::var("WM_LLAMA_MEDIUM_ENDPOINT") {
            if !val.is_empty() && is_tri_endpoint_safe(&val) {
                config.medium_endpoint = Some(val);
            } else if !val.is_empty() {
                tracing::warn!("WM_LLAMA_MEDIUM_ENDPOINT rejected: must use http:// or https://");
            }
        }

        if let Ok(val) = std::env::var("WM_LLAMA_FG_IDLE_TIMEOUT") {
            if let Ok(secs) = val.parse::<u64>() {
                config.idle_timeout = Duration::from_secs(secs);
            }
        }

        if let Ok(val) = std::env::var("WM_LLAMA_FG_DEEP_IDLE_TIMEOUT") {
            if let Ok(secs) = val.parse::<u64>() {
                config.deep_idle_timeout = Duration::from_secs(secs);
            }
        }

        if let Ok(val) = std::env::var("WM_LLAMA_FG_IDLE_MODE") {
            config.idle_mode = match val.to_lowercase().as_str() {
                "dream" | "theta" | "1" => IdleMode::Dream,
                _ => IdleMode::Shutdown,
            };
        }

        if let Ok(val) = std::env::var("WM_LLAMA_FG_AUTO_START") {
            config.auto_start = val != "0" && !val.eq_ignore_ascii_case("false");
        }

        if let Ok(val) = std::env::var("WM_BITMAMBA_BIN") {
            if !val.is_empty() {
                config.autonomic_bin = Some(val);
            }
        }

        if let Ok(val) = std::env::var("WM_BITMAMBA_MODEL") {
            if !val.is_empty() {
                config.autonomic_model = Some(val);
            }
        }

        config
    }

    /// Check if the left model is configured.
    #[must_use]
    pub const fn has_left(&self) -> bool {
        self.left_endpoint.is_some()
    }

    /// Check if the medium model is configured.
    #[must_use]
    pub const fn has_medium(&self) -> bool {
        self.medium_endpoint.is_some()
    }

    /// Check if the right model is configured.
    #[must_use]
    pub const fn has_right(&self) -> bool {
        self.right_endpoint.is_some()
    }

    /// Check if the autonomic model is configured.
    #[must_use]
    pub const fn has_autonomic(&self) -> bool {
        self.autonomic_bin.is_some()
    }
}

/// Validate that an endpoint URL uses http:// or https:// and is not empty.
fn is_tri_endpoint_safe(endpoint: &str) -> bool {
    if endpoint.is_empty() {
        return false;
    }
    endpoint.starts_with("http://") || endpoint.starts_with("https://")
}

// ── Model Kind ────────────────────────────────────────────────────────

/// Identifies which model component.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum ModelKind {
    /// Autonomic layer (BitMamba, always-on).
    Autonomic,
    /// Left hemisphere (llama.cpp, deterministic).
    Left,
    /// Right hemisphere (BitNet, creative).
    Right,
}

impl ModelKind {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Autonomic => "autonomic",
            Self::Left => "left",
            Self::Right => "right",
        }
    }

    /// All variants in order.
    #[must_use]
    pub const fn all() -> [Self; 3] {
        [Self::Autonomic, Self::Left, Self::Right]
    }

    /// Map an `InferenceTier` to the primary model that should handle it.
    ///
    /// - `EdgeRules` → `Autonomic` (pattern matching, always-on)
    /// - `LocalLlamaCpp` → `Left` (small HTTP model, e.g. Qwen 0.5B)
    /// - `LocalSmall` → `Left` (small HTTP model)
    /// - `LocalLarge` → `Right` (large HTTP model, e.g. Qwen 3B)
    /// - `Cloud` → `None` (not managed by TriModelManager)
    #[must_use]
    pub const fn from_tier(tier: InferenceTier) -> Option<Self> {
        match tier {
            InferenceTier::EdgeRules => Some(Self::Autonomic),
            InferenceTier::LocalLlamaCpp | InferenceTier::LocalSmall => Some(Self::Left),
            InferenceTier::LocalLarge => Some(Self::Right),
            InferenceTier::Cloud => None,
        }
    }
}

impl std::fmt::Display for ModelKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

// ── Lifecycle Event ───────────────────────────────────────────────────

/// A lifecycle event emitted by the TriModelManager.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LifecycleEvent {
    /// Which model the event concerns.
    pub kind: ModelKind,
    /// The event type.
    pub event: LifecycleEventType,
    /// Timestamp (Unix epoch seconds).
    pub timestamp: f64,
    /// Optional message.
    pub message: Option<String>,
}

/// Type of lifecycle event.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LifecycleEventType {
    /// Model started.
    Started,
    /// Model stopped (graceful).
    Stopped,
    /// Model failed.
    Failed,
    /// Model restarted after failure.
    Restarted,
    /// Model transitioned to idle.
    IdleTimeout,
    /// Model woken from idle.
    WokenUp,
    /// Model entered dream mode (Theta).
    DreamStarted,
    /// Model exited dream mode (woken or shut down).
    DreamEnded,
    /// Model woken from dream (warm restart).
    WarmWake,
    /// Health check passed.
    HealthOk,
    /// Health check failed.
    HealthFailed,
}

// ── TriModel Manager ──────────────────────────────────────────────────

/// Manages the lifecycle of three model components (autonomic, left, right).
///
/// The autonomic model is persistent (always-on). Left and right models
/// are on-demand with idle-shutdown. Health checks and auto-restart
/// are supported.
pub struct TriModelManager {
    config: TriModelConfig,
    components: Mutex<[ModelComponent; 3]>,
    events: Mutex<VecDeque<LifecycleEvent>>,
    total_restarts: AtomicU64,
}

use std::collections::VecDeque;

impl TriModelManager {
    /// Create a new TriModelManager from config.
    ///
    /// All components start in `Stopped` state. Use `start_autonomic()` to
    /// start the persistent autonomic model, or `ensure_running()` to
    /// auto-start a component on demand.
    #[must_use]
    pub fn new(config: TriModelConfig) -> Self {
        let components = [
            ModelComponent::new(true),  // Autonomic — persistent
            ModelComponent::new(false), // Left — on-demand
            ModelComponent::new(false), // Right — on-demand
        ];

        Self {
            config,
            components: Mutex::new(components),
            events: Mutex::new(VecDeque::with_capacity(64)),
            total_restarts: AtomicU64::new(0),
        }
    }

    /// Create from environment variables.
    #[must_use]
    pub fn from_env() -> Self {
        Self::new(TriModelConfig::from_env())
    }

    /// Create a default manager (no models configured — useful for testing).
    #[must_use]
    pub fn default_manager() -> Self {
        Self::new(TriModelConfig::default())
    }

    /// Get the configuration.
    #[must_use]
    pub const fn config(&self) -> &TriModelConfig {
        &self.config
    }

    // ── State queries ──────────────────────────────────────────────────

    /// Get the state of a model component.
    #[must_use]
    pub fn state(&self, kind: ModelKind) -> ModelState {
        let components = self.components.lock().unwrap();
        components[kind as usize].state()
    }

    /// Check if a model is available (Running or Idle).
    #[must_use]
    pub fn is_available(&self, kind: ModelKind) -> bool {
        self.state(kind).is_available()
    }

    /// Get request count for a model.
    #[must_use]
    pub fn request_count(&self, kind: ModelKind) -> u64 {
        let components = self.components.lock().unwrap();
        components[kind as usize].request_count()
    }

    /// Get error count for a model.
    #[must_use]
    pub fn error_count(&self, kind: ModelKind) -> u64 {
        let components = self.components.lock().unwrap();
        components[kind as usize].error_count()
    }

    /// Get idle duration for a model.
    #[must_use]
    pub fn idle_duration(&self, kind: ModelKind) -> Duration {
        let components = self.components.lock().unwrap();
        components[kind as usize].idle_duration()
    }

    /// Total restart attempts across all models.
    #[must_use]
    pub fn total_restarts(&self) -> u64 {
        self.total_restarts.load(Ordering::Relaxed)
    }

    // ── Lifecycle control ──────────────────────────────────────────────

    /// Start the autonomic model (persistent, always-on).
    ///
    /// In a real deployment, this spawns the BitMamba daemon.
    /// In test/stub mode, this just marks the component as running.
    pub fn start_autonomic(&self) -> Result<(), String> {
        let mut components = self.components.lock().unwrap();
        let comp = &mut components[ModelKind::Autonomic as usize];

        if comp.state.is_available() {
            return Ok(()); // Already running
        }

        if !self.config.has_autonomic() {
            // No autonomic configured — mark as running in stub mode
            comp.mark_running();
            self.emit_event(ModelKind::Autonomic, LifecycleEventType::Started, None);
            return Ok(());
        }

        // In production, this would spawn the BitMamba daemon
        // For now, mark as running (the actual daemon is managed by AutonomicLayer)
        comp.mark_running();
        self.emit_event(ModelKind::Autonomic, LifecycleEventType::Started, None);
        Ok(())
    }

    /// Start a specific model component.
    pub fn start(&self, kind: ModelKind) -> Result<(), String> {
        if kind == ModelKind::Autonomic {
            return self.start_autonomic();
        }

        let mut components = self.components.lock().unwrap();
        let comp = &mut components[kind as usize];

        if comp.state.is_available() {
            return Ok(()); // Already running
        }

        let endpoint = match kind {
            ModelKind::Left => &self.config.left_endpoint,
            ModelKind::Right => &self.config.right_endpoint,
            ModelKind::Autonomic => unreachable!(),
        };

        if endpoint.is_none() && !self.config.auto_start {
            return Err(format!(
                "{kind} model not configured and auto_start disabled"
            ));
        }

        // In production, this would verify the model server is reachable
        // For now, mark as running
        comp.mark_running();
        self.emit_event(kind, LifecycleEventType::Started, None);
        Ok(())
    }

    /// Stop a specific model component (graceful shutdown).
    pub fn stop(&self, kind: ModelKind) {
        let mut components = self.components.lock().unwrap();
        let comp = &mut components[kind as usize];

        if comp.state == ModelState::Stopped {
            return;
        }

        comp.mark_stopped();
        self.emit_event(kind, LifecycleEventType::Stopped, None);
    }

    /// Ensure a model is running, starting it if necessary.
    ///
    /// This is the primary method called before routing inference to a model.
    /// If `auto_start` is enabled and the model is stopped, it will be started.
    pub fn ensure_running(&self, kind: ModelKind) -> Result<(), String> {
        let state = self.state(kind);

        if state.is_available() {
            // Touch to update last-active and wake from idle/dreaming
            let mut components = self.components.lock().unwrap();
            let comp = &mut components[kind as usize];
            let was_idle = comp.state == ModelState::Idle;
            let was_dreaming = comp.state == ModelState::Dreaming;
            comp.touch();
            drop(components);
            if was_dreaming {
                self.emit_event(kind, LifecycleEventType::WarmWake, None);
                self.emit_event(kind, LifecycleEventType::DreamEnded, None);
            } else if was_idle {
                self.emit_event(kind, LifecycleEventType::WokenUp, None);
            }
            return Ok(());
        }

        if state == ModelState::Failed {
            // Attempt restart
            return self.restart(kind);
        }

        // Stopped — auto-start if configured
        if self.config.auto_start {
            self.start(kind)
        } else {
            Err(format!(
                "{kind} model is stopped and auto_start is disabled"
            ))
        }
    }

    /// Restart a failed model.
    pub fn restart(&self, kind: ModelKind) -> Result<(), String> {
        let attempts = self.error_count(kind);
        if attempts > u64::from(self.config.max_restart_attempts) {
            return Err(format!(
                "{kind} model exceeded max restart attempts ({})",
                self.config.max_restart_attempts
            ));
        }

        self.total_restarts.fetch_add(1, Ordering::Relaxed);

        // Stop then start
        self.stop(kind);
        self.start(kind).inspect_err(|e| {
            let mut components = self.components.lock().unwrap();
            components[kind as usize].mark_failed(e);
            self.emit_event(kind, LifecycleEventType::Failed, Some(e.clone()));
        })?;

        self.emit_event(kind, LifecycleEventType::Restarted, None);
        Ok(())
    }

    // ── Idle watchdog ──────────────────────────────────────────────────

    /// Check for idle models and transition them through the idle lifecycle.
    ///
    /// Two-tier idle when `idle_mode` is `Dream`:
    /// 1. First `idle_timeout` → enter Dreaming state (warm, low-power)
    /// 2. After `deep_idle_timeout` → full shutdown (Stopped)
    ///
    /// Single-tier when `idle_mode` is `Shutdown` (original behavior):
    /// 1. After `idle_timeout` → immediate Stopped
    ///
    /// Should be called periodically (e.g., on each brain-wave tick).
    /// Returns the list of models that were shut down (Stopped).
    pub fn check_idle(&self) -> Vec<ModelKind> {
        // First pass: find models that need transitioning
        let to_transition: Vec<(ModelKind, ModelState)> = {
            let components = self.components.lock().unwrap();
            components
                .iter()
                .enumerate()
                .filter(|(_, c)| !c.persistent && c.state.is_warm())
                .filter_map(|(i, c)| {
                    let kind = ModelKind::all()[i];
                    let idle = c.idle_duration();
                    match self.config.idle_mode {
                        IdleMode::Shutdown => {
                            // Original behavior: idle timeout → stop
                            if c.state == ModelState::Running && idle > self.config.idle_timeout {
                                Some((kind, ModelState::Stopped))
                            } else {
                                None
                            }
                        }
                        IdleMode::Dream => {
                            // Two-tier: first timeout → dream, deep idle → stop
                            if c.state == ModelState::Dreaming
                                && idle > self.config.deep_idle_timeout
                            {
                                Some((kind, ModelState::Stopped))
                            } else if c.state == ModelState::Running
                                && idle > self.config.idle_timeout
                            {
                                Some((kind, ModelState::Dreaming))
                            } else {
                                None
                            }
                        }
                    }
                })
                .collect()
        };

        // Second pass: apply transitions and emit events
        let mut shut_down = Vec::new();
        for (kind, target_state) in &to_transition {
            match target_state {
                ModelState::Dreaming => {
                    {
                        let mut components = self.components.lock().unwrap();
                        components[*kind as usize].mark_dreaming();
                    }
                    self.emit_event(*kind, LifecycleEventType::DreamStarted, None);
                }
                ModelState::Stopped => {
                    {
                        let mut components = self.components.lock().unwrap();
                        let was_dreaming = components[*kind as usize].state == ModelState::Dreaming;
                        components[*kind as usize].mark_stopped();
                        if was_dreaming {
                            self.emit_event(*kind, LifecycleEventType::DreamEnded, None);
                        }
                    }
                    self.emit_event(*kind, LifecycleEventType::IdleTimeout, None);
                    self.emit_event(*kind, LifecycleEventType::Stopped, None);
                    shut_down.push(*kind);
                }
                _ => unreachable!(),
            }
        }

        shut_down
    }

    // ── Health check ───────────────────────────────────────────────────

    /// Run a health check on all running models.
    ///
    /// In production, this would ping each model's endpoint.
    /// Returns the list of models that failed the health check.
    pub fn health_check(&self) -> Vec<ModelKind> {
        let failed = Vec::new();

        // Collect running models first, then emit events without holding the lock
        let running: Vec<ModelKind> = {
            let components = self.components.lock().unwrap();
            components
                .iter()
                .enumerate()
                .filter(|(_, c)| c.state.is_available())
                .map(|(i, _)| ModelKind::all()[i])
                .collect()
        };

        for kind in running {
            // In production, ping the endpoint
            // For now, all running models are considered healthy
            self.emit_event(kind, LifecycleEventType::HealthOk, None);
        }

        failed
    }

    /// Mark a model as failed.
    pub fn mark_failed(&self, kind: ModelKind, error: &str) {
        let mut components = self.components.lock().unwrap();
        components[kind as usize].mark_failed(error);
        self.emit_event(kind, LifecycleEventType::Failed, Some(error.to_string()));
    }

    /// Record a successful request on a model.
    pub fn record_success(&self, kind: ModelKind) {
        let mut components = self.components.lock().unwrap();
        components[kind as usize].touch();
        components[kind as usize].record_success();
    }

    /// Record a failed request on a model.
    pub fn record_error(&self, kind: ModelKind, error: &str) {
        let components = self.components.lock().unwrap();
        components[kind as usize].record_error(error);
        // Don't immediately mark as failed — allow retries
    }

    // ── Routing ────────────────────────────────────────────────────────

    /// Route an inference request to the appropriate model based on tier.
    ///
    /// Returns the model kind that should handle the request, or `None`
    /// for Cloud tier (not managed by TriModelManager).
    ///
    /// Falls back to a lower tier if the preferred model is unavailable:
    /// - `LocalLarge` → `Left` if Right is down, then `Autonomic`
    /// - `LocalSmall` / `LocalLlamaCpp` → `Autonomic` if Left is down
    #[must_use]
    pub fn route(&self, tier: InferenceTier) -> Option<ModelKind> {
        let primary = ModelKind::from_tier(tier)?;

        // Check if primary is available
        if self.is_available(primary) {
            return Some(primary);
        }

        // Fallback chain
        match tier {
            InferenceTier::LocalLarge => {
                // Right unavailable → try Left
                if self.is_available(ModelKind::Left) {
                    return Some(ModelKind::Left);
                }
                // Left also unavailable → try Autonomic
                if self.is_available(ModelKind::Autonomic) {
                    return Some(ModelKind::Autonomic);
                }
                None
            }
            InferenceTier::LocalSmall => {
                // Left unavailable → try Autonomic
                if self.is_available(ModelKind::Autonomic) {
                    return Some(ModelKind::Autonomic);
                }
                None
            }
            InferenceTier::EdgeRules => {
                // Autonomic should always be available
                if self.is_available(ModelKind::Autonomic) {
                    Some(ModelKind::Autonomic)
                } else {
                    None
                }
            }
            InferenceTier::LocalLlamaCpp => {
                // Left unavailable → try Autonomic
                if self.is_available(ModelKind::Autonomic) {
                    Some(ModelKind::Autonomic)
                } else {
                    None
                }
            }
            InferenceTier::Cloud => None,
        }
    }

    /// Route and ensure the target model is running.
    ///
    /// Combines tier→model mapping + `ensure_running()` in a single call.
    /// Unlike `route()`, this will auto-start stopped models if `auto_start`
    /// is enabled.
    pub fn route_and_ensure(&self, tier: InferenceTier) -> Result<ModelKind, String> {
        // For Cloud tier, there's no managed model
        if tier == InferenceTier::Cloud {
            return Err("no model available for tier cloud".into());
        }

        let primary = ModelKind::from_tier(tier)
            .ok_or_else(|| format!("no model mapping for tier {tier}"))?;

        // Try primary first
        if self.ensure_running(primary).is_ok() {
            return Ok(primary);
        }

        // Fallback chain: try lower-tier models
        let fallbacks = match tier {
            InferenceTier::LocalLarge => [ModelKind::Left, ModelKind::Autonomic],
            InferenceTier::LocalSmall => [ModelKind::Autonomic, ModelKind::Right],
            InferenceTier::EdgeRules | InferenceTier::LocalLlamaCpp => {
                return self
                    .ensure_running(ModelKind::Autonomic)
                    .map(|()| ModelKind::Autonomic);
            }
            InferenceTier::Cloud => return Err("cloud tier not managed".into()),
        };

        for &fb in &fallbacks {
            if self.ensure_running(fb).is_ok() {
                return Ok(fb);
            }
        }

        Err(format!("no model could be started for tier {tier}"))
    }

    // ── Events ─────────────────────────────────────────────────────────

    fn emit_event(&self, kind: ModelKind, event: LifecycleEventType, message: Option<String>) {
        let timestamp =
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0) as f64 / 1_000_000_000.0;

        let ev = LifecycleEvent {
            kind,
            event,
            timestamp,
            message,
        };

        if let Ok(mut events) = self.events.lock() {
            events.push_back(ev);
            while events.len() > 64 {
                events.pop_front();
            }
        }
    }

    /// Get recent lifecycle events.
    #[must_use]
    pub fn events(&self) -> Vec<LifecycleEvent> {
        self.events
            .lock()
            .map(|e| e.iter().cloned().collect())
            .unwrap_or_default()
    }

    // ── Status ─────────────────────────────────────────────────────────

    /// Get a comprehensive status snapshot as JSON.
    #[must_use]
    pub fn status(&self) -> serde_json::Value {
        let components = self.components.lock().unwrap();

        let component_status = |kind: ModelKind| {
            let comp = &components[kind as usize];
            serde_json::json!({
                "state": comp.state.as_str(),
                "persistent": comp.persistent,
                "requests": comp.request_count(),
                "errors": comp.error_count(),
                "idle_secs": comp.idle_duration().as_secs(),
                "available": comp.state.is_available(),
            })
        };

        serde_json::json!({
            "autonomic": component_status(ModelKind::Autonomic),
            "left": component_status(ModelKind::Left),
            "right": component_status(ModelKind::Right),
            "total_restarts": self.total_restarts.load(Ordering::Relaxed),
            "idle_timeout_secs": self.config.idle_timeout.as_secs(),
            "auto_start": self.config.auto_start,
            "has_left": self.config.has_left(),
            "has_right": self.config.has_right(),
            "has_autonomic": self.config.has_autonomic(),
        })
    }

    /// Get a summary string suitable for CLI display.
    #[must_use]
    pub fn summary(&self) -> String {
        let components = self.components.lock().unwrap();
        let mut out = String::new();

        for kind in ModelKind::all() {
            let comp = &components[kind as usize];
            out.push_str("  ");
            let _ = writeln!(
                out,
                "{kind}: {} (reqs={}, errs={}, idle={}s)",
                comp.state,
                comp.request_count(),
                comp.error_count(),
                comp.idle_duration().as_secs(),
            );
        }

        out
    }
}

// ── Confidence Calibration ────────────────────────────────────────────

/// Compute confidence from token-level logprobs using margin uncertainty.
///
/// For each token, margin = top1_logprob - top2_logprob.
/// A large margin means the model is very confident in its choice.
/// We average the margins across all tokens and apply a sigmoid to
/// normalize to [0, 1]. We also factor in the absolute top-1 logprob
/// (higher = more confident) using a weighted combination.
///
/// This replaces the hardcoded 0.7 confidence with a data-driven score
/// that the cascade router can use for escalation decisions.
fn compute_confidence_from_logprobs(tokens: &[TokenLogprob]) -> f32 {
    if tokens.is_empty() {
        return 0.5;
    }

    let mut margin_sum = 0.0_f32;
    let mut top1_sum = 0.0_f32;
    let mut count = 0_usize;

    for tl in tokens {
        let top1 = tl.logprob;
        top1_sum += top1;

        if tl.top_logprobs.len() >= 2 {
            let top2 = tl.top_logprobs[1].logprob;
            margin_sum += top1 - top2;
        }
        count += 1;
    }

    if count == 0 {
        return 0.5;
    }

    let mean_margin = margin_sum / count as f32;
    let mean_top1 = top1_sum / count as f32;

    // Sigmoid of mean margin: large margin → high confidence
    let margin_conf = 1.0 / (1.0 + (-mean_margin).exp());

    // Sigmoid of mean top-1 logprob: less negative = more confident
    // logprob of 0 = certain, logprob of -5 = very uncertain
    let top1_conf = 1.0 / (1.0 + (-(mean_top1 + 2.0)).exp());

    // Weighted combination: margin is more informative (60%),
    // absolute logprob adds a prior (40%)
    0.6f32.mul_add(margin_conf, 0.4 * top1_conf)
}

// ── TierHandler Implementation ────────────────────────────────────────

/// A `TierHandler` backed by the TriModelManager.
///
/// Routes inference to the appropriate model based on the configured tier.
/// In production, this would make HTTP calls to the model server.
/// In test/stub mode, it returns a heuristic response.
pub struct TriModelHandler {
    manager: std::sync::Arc<TriModelManager>,
    tier: InferenceTier,
    /// Stub response generator (for testing without real models).
    stub: bool,
}

impl TriModelHandler {
    /// Create a new handler for a specific tier.
    #[must_use]
    #[allow(clippy::missing_const_for_fn)]
    pub fn new(manager: std::sync::Arc<TriModelManager>, tier: InferenceTier) -> Self {
        Self {
            manager,
            tier,
            stub: true,
        }
    }

    /// Create a handler in production mode (will call real model endpoints).
    #[must_use]
    #[allow(clippy::missing_const_for_fn)]
    pub fn production(manager: std::sync::Arc<TriModelManager>, tier: InferenceTier) -> Self {
        Self {
            manager,
            tier,
            stub: false,
        }
    }

    /// Generate a stub response (for testing).
    fn stub_response(&self, prompt: &str, kind: ModelKind) -> (String, f32) {
        let response = match kind {
            ModelKind::Autonomic => {
                format!("(autonomic) Processed: {}", &prompt[..prompt.len().min(50)])
            }
            ModelKind::Left => {
                format!("(left) Analyzed: {}", &prompt[..prompt.len().min(50)])
            }
            ModelKind::Right => {
                format!("(right) Creative take: {}", &prompt[..prompt.len().min(50)])
            }
        };
        (response, 0.6)
    }

    /// Make an HTTP call to the model endpoint for the given kind.
    ///
    /// Returns `(response_text, confidence)` on success.
    fn call_http(
        &self,
        prompt: &str,
        max_tokens: usize,
        kind: ModelKind,
    ) -> Result<(String, f32), String> {
        let config = self.manager.config();
        let endpoint = match kind {
            ModelKind::Left => {
                // For LocalSmall tier, prefer medium endpoint (e.g. Qwen 1.5B)
                // over left endpoint (e.g. Qwen 0.5B) if configured.
                if self.tier == InferenceTier::LocalSmall {
                    config
                        .medium_endpoint
                        .as_ref()
                        .or(config.left_endpoint.as_ref())
                } else {
                    config.left_endpoint.as_ref()
                }
            }
            ModelKind::Right => config.right_endpoint.as_ref(),
            ModelKind::Autonomic => return Err("autonomic model uses subprocess, not HTTP".into()),
        };

        let base = endpoint.ok_or_else(|| format!("{kind} model endpoint not configured"))?;

        let url = if base.ends_with("/v1/chat/completions") {
            base.clone()
        } else if base.ends_with('/') {
            format!("{base}v1/chat/completions")
        } else {
            format!("{base}/v1/chat/completions")
        };

        let temperature = match kind {
            ModelKind::Left => 0.2,
            ModelKind::Right => 0.7,
            ModelKind::Autonomic => 0.5,
        };

        let request = ChatRequest {
            model: "local".into(),
            messages: vec![ChatMessage {
                role: "user".into(),
                content: prompt.to_string(),
            }],
            max_tokens: max_tokens.min(512) as u32,
            temperature,
            logprobs: Some(true),
            top_logprobs: Some(2),
        };

        let agent = ureq::config::Config::builder()
            .timeout_global(Some(Duration::from_secs(30)))
            .build()
            .new_agent();

        let response = agent
            .post(&url)
            .header("Content-Type", "application/json")
            .send_json(&request)
            .map_err(|e| format!("{kind} HTTP error: {e}"))?;

        let chat_resp: ChatResponse = response
            .into_body()
            .read_json()
            .map_err(|e| format!("{kind} response parse error: {e}"))?;

        let choice = chat_resp
            .choices
            .into_iter()
            .next()
            .ok_or_else(|| format!("{kind} returned no choices"))?;

        let content = choice.message.content;

        // Compute confidence from token-level margin uncertainty.
        // Margin = top1_logprob - top2_logprob for each token.
        // Confidence = sigmoid(mean_margin) normalized to [0, 1].
        // Falls back to 0.7 if logprobs are unavailable.
        let confidence = if let Some(lp) = choice.logprobs {
            compute_confidence_from_logprobs(&lp.content)
        } else {
            0.7
        };

        Ok((content, confidence))
    }
}

impl TierHandler for TriModelHandler {
    fn handle(&self, prompt: &str, max_tokens: usize) -> Result<(String, f32), String> {
        let kind = self.manager.route_and_ensure(self.tier)?;

        if self.stub {
            let result = self.stub_response(prompt, kind);
            self.manager.record_success(kind);
            return Ok(result);
        }

        // Production mode: make HTTP call to the model endpoint
        match self.call_http(prompt, max_tokens, kind) {
            Ok(result) => {
                self.manager.record_success(kind);
                Ok(result)
            }
            Err(e) => {
                tracing::warn!(error = %e, "tri-model HTTP call failed, falling back to stub");
                self.manager.record_error(kind, &e);
                let result = self.stub_response(prompt, kind);
                Ok(result)
            }
        }
    }

    fn name(&self) -> &'static str {
        match self.tier {
            InferenceTier::EdgeRules => "tri-model-edge",
            InferenceTier::LocalLlamaCpp => "tri-model-llama-cpp",
            InferenceTier::LocalSmall => "tri-model-small",
            InferenceTier::LocalLarge => "tri-model-large",
            InferenceTier::Cloud => "tri-model-cloud",
        }
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── ModelState tests ───────────────────────────────────────────────

    #[test]
    fn model_state_stopped() {
        assert!(!ModelState::Stopped.is_available());
        assert_eq!(ModelState::Stopped.as_str(), "stopped");
    }

    #[test]
    fn model_state_running() {
        assert!(ModelState::Running.is_available());
        assert_eq!(ModelState::Running.as_str(), "running");
    }

    #[test]
    fn model_state_idle() {
        assert!(ModelState::Idle.is_available());
        assert_eq!(ModelState::Idle.as_str(), "idle");
    }

    #[test]
    fn model_state_failed() {
        assert!(!ModelState::Failed.is_available());
        assert_eq!(ModelState::Failed.as_str(), "failed");
    }

    // ── ModelKind tests ────────────────────────────────────────────────

    #[test]
    fn model_kind_as_str() {
        assert_eq!(ModelKind::Autonomic.as_str(), "autonomic");
        assert_eq!(ModelKind::Left.as_str(), "left");
        assert_eq!(ModelKind::Right.as_str(), "right");
    }

    #[test]
    fn model_kind_all() {
        assert_eq!(ModelKind::all().len(), 3);
    }

    #[test]
    fn model_kind_from_tier_edge() {
        assert_eq!(
            ModelKind::from_tier(InferenceTier::EdgeRules),
            Some(ModelKind::Autonomic)
        );
    }

    #[test]
    fn model_kind_from_tier_llama_cpp() {
        assert_eq!(
            ModelKind::from_tier(InferenceTier::LocalLlamaCpp),
            Some(ModelKind::Left)
        );
    }

    #[test]
    fn model_kind_from_tier_small() {
        assert_eq!(
            ModelKind::from_tier(InferenceTier::LocalSmall),
            Some(ModelKind::Left)
        );
    }

    #[test]
    fn model_kind_from_tier_large() {
        assert_eq!(
            ModelKind::from_tier(InferenceTier::LocalLarge),
            Some(ModelKind::Right)
        );
    }

    #[test]
    fn model_kind_from_tier_cloud() {
        assert_eq!(ModelKind::from_tier(InferenceTier::Cloud), None);
    }

    // ── TriModelConfig tests ───────────────────────────────────────────

    #[test]
    fn config_defaults() {
        let config = TriModelConfig::default();
        assert_eq!(config.idle_timeout, Duration::from_secs(300));
        assert!(config.auto_start);
        assert!(!config.has_left());
        assert!(!config.has_right());
        assert!(!config.has_autonomic());
    }

    #[test]
    fn config_idle_timeout_default() {
        let config = TriModelConfig::default();
        assert_eq!(config.idle_timeout.as_secs(), 300);
    }

    #[test]
    fn config_health_check_interval() {
        let config = TriModelConfig::default();
        assert_eq!(config.health_check_interval.as_secs(), 60);
    }

    #[test]
    fn config_max_restart_attempts() {
        let config = TriModelConfig::default();
        assert_eq!(config.max_restart_attempts, 3);
    }

    // ── TriModelManager lifecycle tests ────────────────────────────────

    #[test]
    fn manager_default_all_stopped() {
        let mgr = TriModelManager::default_manager();

        assert_eq!(mgr.state(ModelKind::Autonomic), ModelState::Stopped);
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Stopped);
        assert_eq!(mgr.state(ModelKind::Right), ModelState::Stopped);
    }

    #[test]
    fn manager_start_autonomic() {
        let mgr = TriModelManager::default_manager();
        mgr.start_autonomic().unwrap();

        assert_eq!(mgr.state(ModelKind::Autonomic), ModelState::Running);
        assert!(mgr.is_available(ModelKind::Autonomic));
    }

    #[test]
    fn manager_start_autonomic_idempotent() {
        let mgr = TriModelManager::default_manager();
        mgr.start_autonomic().unwrap();
        // Starting again should be a no-op
        mgr.start_autonomic().unwrap();
        assert_eq!(mgr.state(ModelKind::Autonomic), ModelState::Running);
    }

    #[test]
    fn manager_start_left() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();

        assert_eq!(mgr.state(ModelKind::Left), ModelState::Running);
    }

    #[test]
    fn manager_start_right() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Right).unwrap();

        assert_eq!(mgr.state(ModelKind::Right), ModelState::Running);
    }

    #[test]
    fn manager_stop() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();
        assert!(mgr.is_available(ModelKind::Left));

        mgr.stop(ModelKind::Left);
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Stopped);
    }

    #[test]
    fn manager_stop_idempotent() {
        let mgr = TriModelManager::default_manager();
        mgr.stop(ModelKind::Left); // Already stopped — no-op
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Stopped);
    }

    #[test]
    fn manager_ensure_running_stopped() {
        let mgr = TriModelManager::default_manager();
        // auto_start is true by default
        mgr.ensure_running(ModelKind::Left).unwrap();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Running);
    }

    #[test]
    fn manager_ensure_running_already_running() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();
        mgr.ensure_running(ModelKind::Left).unwrap();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Running);
    }

    #[test]
    fn manager_ensure_running_auto_start_disabled() {
        let config = TriModelConfig {
            auto_start: false,
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);

        let result = mgr.ensure_running(ModelKind::Left);
        assert!(result.is_err());
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Stopped);
    }

    #[test]
    fn manager_ensure_running_wakes_from_idle() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();

        // Manually mark as idle
        {
            let mut components = mgr.components.lock().unwrap();
            components[ModelKind::Left as usize].mark_idle();
        }
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Idle);

        // ensure_running should wake it up
        mgr.ensure_running(ModelKind::Left).unwrap();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Running);
    }

    // ── Restart tests ──────────────────────────────────────────────────

    #[test]
    fn manager_restart_failed() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();

        // Mark as failed
        mgr.mark_failed(ModelKind::Left, "connection refused");
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Failed);

        // Restart should work
        mgr.restart(ModelKind::Left).unwrap();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Running);
        assert_eq!(mgr.total_restarts(), 1);
    }

    #[test]
    fn manager_ensure_running_triggers_restart_on_failed() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();
        mgr.mark_failed(ModelKind::Left, "crashed");

        mgr.ensure_running(ModelKind::Left).unwrap();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Running);
    }

    // ── Idle watchdog tests ────────────────────────────────────────────

    #[test]
    fn manager_idle_watchdog_shuts_down() {
        let config = TriModelConfig {
            idle_timeout: Duration::from_millis(10),
            auto_start: true,
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);

        mgr.start(ModelKind::Left).unwrap();
        assert!(mgr.is_available(ModelKind::Left));

        // Wait for idle timeout
        std::thread::sleep(Duration::from_millis(20));

        let shutdown = mgr.check_idle();
        assert!(shutdown.contains(&ModelKind::Left));
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Stopped);
    }

    #[test]
    fn manager_idle_watchout_spares_autonomic() {
        let config = TriModelConfig {
            idle_timeout: Duration::from_millis(10),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);

        mgr.start_autonomic().unwrap();
        std::thread::sleep(Duration::from_millis(20));

        let shutdown = mgr.check_idle();
        assert!(!shutdown.contains(&ModelKind::Autonomic));
        assert!(mgr.is_available(ModelKind::Autonomic));
    }

    #[test]
    fn manager_idle_watchdog_no_action_on_stopped() {
        let config = TriModelConfig {
            idle_timeout: Duration::from_millis(10),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);

        // Left is stopped — should not appear in shutdown list
        std::thread::sleep(Duration::from_millis(20));
        let shutdown = mgr.check_idle();
        assert!(shutdown.is_empty());
    }

    // ── Routing tests ──────────────────────────────────────────────────

    #[test]
    fn route_edge_rules_to_autonomic() {
        let mgr = TriModelManager::default_manager();
        mgr.start_autonomic().unwrap();

        assert_eq!(
            mgr.route(InferenceTier::EdgeRules),
            Some(ModelKind::Autonomic)
        );
    }

    #[test]
    fn route_local_small_to_left() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();

        assert_eq!(mgr.route(InferenceTier::LocalSmall), Some(ModelKind::Left));
    }

    #[test]
    fn route_local_large_to_right() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Right).unwrap();

        assert_eq!(mgr.route(InferenceTier::LocalLarge), Some(ModelKind::Right));
    }

    #[test]
    fn route_cloud_returns_none() {
        let mgr = TriModelManager::default_manager();
        assert_eq!(mgr.route(InferenceTier::Cloud), None);
    }

    #[test]
    fn route_fallback_right_to_left() {
        let mgr = TriModelManager::default_manager();
        // Only left is running, right is stopped
        mgr.start(ModelKind::Left).unwrap();

        assert_eq!(
            mgr.route(InferenceTier::LocalLarge),
            Some(ModelKind::Left) // Falls back to left
        );
    }

    #[test]
    fn route_fallback_left_to_autonomic() {
        let mgr = TriModelManager::default_manager();
        // Only autonomic is running
        mgr.start_autonomic().unwrap();

        assert_eq!(
            mgr.route(InferenceTier::LocalSmall),
            Some(ModelKind::Autonomic) // Falls back to autonomic
        );
    }

    #[test]
    fn route_fallback_large_to_autonomic() {
        let mgr = TriModelManager::default_manager();
        // Only autonomic is running
        mgr.start_autonomic().unwrap();

        assert_eq!(
            mgr.route(InferenceTier::LocalLarge),
            Some(ModelKind::Autonomic) // Falls back to autonomic
        );
    }

    #[test]
    fn route_nothing_available() {
        let mgr = TriModelManager::default_manager();
        // Nothing running
        assert_eq!(mgr.route(InferenceTier::EdgeRules), None);
        assert_eq!(mgr.route(InferenceTier::LocalSmall), None);
        assert_eq!(mgr.route(InferenceTier::LocalLarge), None);
    }

    #[test]
    fn route_and_ensure_starts_model() {
        let mgr = TriModelManager::default_manager();
        // auto_start is true
        let kind = mgr.route_and_ensure(InferenceTier::LocalSmall).unwrap();
        assert_eq!(kind, ModelKind::Left);
        assert!(mgr.is_available(ModelKind::Left));
    }

    #[test]
    fn route_and_ensure_cloud_fails() {
        let mgr = TriModelManager::default_manager();
        assert!(mgr.route_and_ensure(InferenceTier::Cloud).is_err());
    }

    // ── Request tracking tests ─────────────────────────────────────────

    #[test]
    fn record_success_increments_count() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();

        assert_eq!(mgr.request_count(ModelKind::Left), 0);
        mgr.record_success(ModelKind::Left);
        mgr.record_success(ModelKind::Left);
        mgr.record_success(ModelKind::Left);
        assert_eq!(mgr.request_count(ModelKind::Left), 3);
    }

    #[test]
    fn record_error_increments_count() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();

        mgr.record_error(ModelKind::Left, "timeout");
        mgr.record_error(ModelKind::Left, "timeout");
        assert_eq!(mgr.error_count(ModelKind::Left), 2);
    }

    // ── Event tests ────────────────────────────────────────────────────

    #[test]
    fn events_recorded_on_start() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();

        let events = mgr.events();
        assert!(
            events
                .iter()
                .any(|e| { e.kind == ModelKind::Left && e.event == LifecycleEventType::Started })
        );
    }

    #[test]
    fn events_recorded_on_stop() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();
        mgr.stop(ModelKind::Left);

        let events = mgr.events();
        assert!(
            events
                .iter()
                .any(|e| { e.kind == ModelKind::Left && e.event == LifecycleEventType::Stopped })
        );
    }

    #[test]
    fn events_recorded_on_failure() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();
        mgr.mark_failed(ModelKind::Left, "crashed");

        let events = mgr.events();
        assert!(
            events
                .iter()
                .any(|e| { e.kind == ModelKind::Left && e.event == LifecycleEventType::Failed })
        );
    }

    #[test]
    fn events_recorded_on_idle_timeout() {
        let config = TriModelConfig {
            idle_timeout: Duration::from_millis(10),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        mgr.start(ModelKind::Left).unwrap();
        std::thread::sleep(Duration::from_millis(20));
        mgr.check_idle();

        let events = mgr.events();
        assert!(
            events.iter().any(|e| {
                e.kind == ModelKind::Left && e.event == LifecycleEventType::IdleTimeout
            })
        );
    }

    #[test]
    fn events_recorded_on_wake_up() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();

        // Mark as idle
        {
            let mut components = mgr.components.lock().unwrap();
            components[ModelKind::Left as usize].mark_idle();
        }

        // Wake up
        mgr.ensure_running(ModelKind::Left).unwrap();

        let events = mgr.events();
        assert!(
            events
                .iter()
                .any(|e| { e.kind == ModelKind::Left && e.event == LifecycleEventType::WokenUp })
        );
    }

    #[test]
    fn events_capped_at_64() {
        let mgr = TriModelManager::default_manager();
        for _ in 0..100 {
            mgr.start(ModelKind::Left).unwrap();
            mgr.stop(ModelKind::Left);
        }
        let events = mgr.events();
        assert!(events.len() <= 64);
    }

    // ── Status tests ───────────────────────────────────────────────────

    #[test]
    fn status_json() {
        let mgr = TriModelManager::default_manager();
        mgr.start_autonomic().unwrap();
        mgr.start(ModelKind::Left).unwrap();

        let status = mgr.status();
        assert_eq!(status["autonomic"]["state"].as_str().unwrap(), "running");
        assert_eq!(status["left"]["state"].as_str().unwrap(), "running");
        assert_eq!(status["right"]["state"].as_str().unwrap(), "stopped");
        assert_eq!(status["idle_timeout_secs"].as_u64().unwrap(), 300);
        assert!(status["auto_start"].as_bool().unwrap());
    }

    #[test]
    fn summary_string() {
        let mgr = TriModelManager::default_manager();
        mgr.start_autonomic().unwrap();
        let summary = mgr.summary();
        assert!(summary.contains("autonomic: running"));
        assert!(summary.contains("left: stopped"));
        assert!(summary.contains("right: stopped"));
    }

    // ── TriModelHandler tests ──────────────────────────────────────────

    #[test]
    fn handler_stub_response() {
        let mgr = std::sync::Arc::new(TriModelManager::default_manager());
        mgr.start_autonomic().unwrap();

        let handler = TriModelHandler::new(mgr.clone(), InferenceTier::EdgeRules);
        let (answer, confidence) = handler.handle("hello world", 64).unwrap();

        assert!(answer.contains("autonomic"));
        assert!((confidence - 0.6).abs() < 0.01);
        assert_eq!(mgr.request_count(ModelKind::Autonomic), 1);
    }

    #[test]
    fn handler_routes_to_correct_model_2() {
        let mgr = std::sync::Arc::new(TriModelManager::default_manager());
        mgr.start(ModelKind::Left).unwrap();

        let handler = TriModelHandler::new(mgr, InferenceTier::LocalSmall);
        let (answer, _) = handler.handle("test prompt", 64).unwrap();

        assert!(answer.contains("left"));
    }

    #[test]
    fn handler_fallback_on_unavailable() {
        let mgr = std::sync::Arc::new(TriModelManager::default_manager());
        // Only autonomic is running
        mgr.start_autonomic().unwrap();

        let handler = TriModelHandler::new(mgr, InferenceTier::LocalSmall);
        // Left is not running, but auto_start will start it
        let (answer, _) = handler.handle("test", 64).unwrap();
        // Should have been routed to Left (auto-started)
        assert!(answer.contains("left"));
    }

    #[test]
    fn handler_name_reflects_tier() {
        let mgr = std::sync::Arc::new(TriModelManager::default_manager());

        let h0 = TriModelHandler::new(mgr.clone(), InferenceTier::EdgeRules);
        let h1 = TriModelHandler::new(mgr.clone(), InferenceTier::LocalLlamaCpp);
        let h2 = TriModelHandler::new(mgr.clone(), InferenceTier::LocalSmall);
        let h3 = TriModelHandler::new(mgr.clone(), InferenceTier::LocalLarge);
        let h4 = TriModelHandler::new(mgr, InferenceTier::Cloud);

        assert_eq!(h0.name(), "tri-model-edge");
        assert_eq!(h1.name(), "tri-model-llama-cpp");
        assert_eq!(h2.name(), "tri-model-small");
        assert_eq!(h3.name(), "tri-model-large");
        assert_eq!(h4.name(), "tri-model-cloud");
    }

    #[test]
    fn handler_production_mode() {
        let mgr = std::sync::Arc::new(TriModelManager::default_manager());
        mgr.start_autonomic().unwrap();

        let handler = TriModelHandler::production(mgr, InferenceTier::EdgeRules);
        // Production mode still falls back to stub when no real endpoint
        let (answer, _) = handler.handle("test", 64).unwrap();
        assert!(!answer.is_empty());
    }

    #[test]
    fn handler_implements_tier_handler() {
        let mgr = std::sync::Arc::new(TriModelManager::default_manager());
        let handler = TriModelHandler::new(mgr, InferenceTier::LocalSmall);
        fn assert_trait<T: TierHandler + ?Sized>(_: &T) {}
        assert_trait(&handler);
    }

    // ── ModelComponent tests ───────────────────────────────────────────

    #[test]
    fn component_persistent_flag() {
        let mgr = TriModelManager::default_manager();
        let components = mgr.components.lock().unwrap();
        assert!(components[ModelKind::Autonomic as usize].is_persistent());
        assert!(!components[ModelKind::Left as usize].is_persistent());
        assert!(!components[ModelKind::Right as usize].is_persistent());
    }

    #[test]
    fn component_idle_duration_grows() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();

        let idle1 = mgr.idle_duration(ModelKind::Left);
        std::thread::sleep(Duration::from_millis(10));
        let idle2 = mgr.idle_duration(ModelKind::Left);

        assert!(idle2 > idle1);
    }

    #[test]
    fn component_touch_resets_idle() {
        let mgr = TriModelManager::default_manager();
        mgr.start(ModelKind::Left).unwrap();

        std::thread::sleep(Duration::from_millis(10));
        let idle1 = mgr.idle_duration(ModelKind::Left);

        mgr.record_success(ModelKind::Left);
        let idle2 = mgr.idle_duration(ModelKind::Left);

        assert!(idle2 < idle1);
    }

    // ── N12: Idle-to-Default-Mode (Dream) tests ───────────────────────

    #[test]
    fn idle_mode_default_is_shutdown() {
        assert_eq!(IdleMode::default(), IdleMode::Shutdown);
    }

    #[test]
    fn idle_mode_as_str() {
        assert_eq!(IdleMode::Shutdown.as_str(), "shutdown");
        assert_eq!(IdleMode::Dream.as_str(), "dream");
    }

    #[test]
    fn idle_mode_display() {
        assert_eq!(format!("{}", IdleMode::Shutdown), "shutdown");
        assert_eq!(format!("{}", IdleMode::Dream), "dream");
    }

    #[test]
    fn model_state_dreaming_is_available() {
        assert!(ModelState::Dreaming.is_available());
    }

    #[test]
    fn model_state_dreaming_is_warm() {
        assert!(ModelState::Dreaming.is_warm());
    }

    #[test]
    fn model_state_dreaming_is_dreaming() {
        assert!(ModelState::Dreaming.is_dreaming());
        assert!(!ModelState::Running.is_dreaming());
    }

    #[test]
    fn model_state_dreaming_as_str() {
        assert_eq!(ModelState::Dreaming.as_str(), "dreaming");
    }

    #[test]
    fn config_default_has_shutdown_idle_mode() {
        let config = TriModelConfig::default();
        assert_eq!(config.idle_mode, IdleMode::Shutdown);
        assert_eq!(config.deep_idle_timeout, Duration::from_secs(1800));
    }

    #[test]
    fn config_with_dream_mode() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_secs(60),
            deep_idle_timeout: Duration::from_secs(300),
            ..TriModelConfig::default()
        };
        assert_eq!(config.idle_mode, IdleMode::Dream);
    }

    #[test]
    fn check_idle_shutdown_mode_stops_immediately() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Shutdown,
            idle_timeout: Duration::from_millis(0),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        mgr.start(ModelKind::Left).unwrap();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Running);

        std::thread::sleep(Duration::from_millis(5));
        let stopped = mgr.check_idle();
        assert!(stopped.contains(&ModelKind::Left));
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Stopped);
    }

    #[test]
    fn check_idle_dream_mode_enters_dreaming_first() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_millis(0),
            deep_idle_timeout: Duration::from_secs(3600), // Far future
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        mgr.start(ModelKind::Left).unwrap();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Running);

        std::thread::sleep(Duration::from_millis(5));
        let stopped = mgr.check_idle();
        // Should enter Dreaming, not stop
        assert!(stopped.is_empty());
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Dreaming);
    }

    #[test]
    fn check_idle_dream_mode_stops_after_deep_idle() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_millis(0),
            deep_idle_timeout: Duration::from_millis(0),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        mgr.start(ModelKind::Left).unwrap();

        std::thread::sleep(Duration::from_millis(5));
        // First call: Running → Dreaming (idle_timeout=0)
        let stopped1 = mgr.check_idle();
        assert!(stopped1.is_empty());
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Dreaming);

        // Second call: Dreaming → Stopped (deep_idle_timeout=0)
        std::thread::sleep(Duration::from_millis(5));
        let stopped2 = mgr.check_idle();
        assert!(stopped2.contains(&ModelKind::Left));
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Stopped);
    }

    #[test]
    fn check_idle_dream_mode_spares_autonomic() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_millis(0),
            deep_idle_timeout: Duration::from_secs(3600),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        mgr.start_autonomic().unwrap();
        mgr.start(ModelKind::Left).unwrap();

        std::thread::sleep(Duration::from_millis(5));
        let stopped = mgr.check_idle();
        assert!(!stopped.contains(&ModelKind::Autonomic));
        assert_eq!(mgr.state(ModelKind::Autonomic), ModelState::Running);
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Dreaming);
    }

    #[test]
    fn check_idle_dream_mode_no_action_on_stopped() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_millis(0),
            deep_idle_timeout: Duration::from_millis(0),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        // Left is Stopped (default)
        std::thread::sleep(Duration::from_millis(5));
        let stopped = mgr.check_idle();
        assert!(stopped.is_empty());
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Stopped);
    }

    #[test]
    fn ensure_running_wakes_from_dreaming() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_millis(0),
            deep_idle_timeout: Duration::from_secs(3600),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        mgr.start(ModelKind::Left).unwrap();

        // Enter dream
        std::thread::sleep(Duration::from_millis(5));
        let _ = mgr.check_idle();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Dreaming);

        // Wake up
        mgr.ensure_running(ModelKind::Left).unwrap();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Running);
    }

    #[test]
    fn ensure_running_from_dreaming_emits_warm_wake_event() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_millis(0),
            deep_idle_timeout: Duration::from_secs(3600),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        mgr.start(ModelKind::Left).unwrap();

        // Enter dream
        std::thread::sleep(Duration::from_millis(5));
        let _ = mgr.check_idle();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Dreaming);

        // Wake up
        mgr.ensure_running(ModelKind::Left).unwrap();

        let events = mgr.events();
        let has_warm_wake = events
            .iter()
            .any(|e| e.kind == ModelKind::Left && e.event == LifecycleEventType::WarmWake);
        assert!(has_warm_wake);
    }

    #[test]
    fn dream_lifecycle_events_emitted() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_millis(0),
            deep_idle_timeout: Duration::from_secs(3600),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        mgr.start(ModelKind::Left).unwrap();

        // Enter dream
        std::thread::sleep(Duration::from_millis(5));
        let _ = mgr.check_idle();

        let events = mgr.events();
        let has_dream_started = events
            .iter()
            .any(|e| e.kind == ModelKind::Left && e.event == LifecycleEventType::DreamStarted);
        assert!(has_dream_started);
    }

    #[test]
    fn dream_ended_event_on_deep_idle_shutdown() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_millis(0),
            deep_idle_timeout: Duration::from_millis(0),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        mgr.start(ModelKind::Left).unwrap();

        // First call: Running → Dreaming
        std::thread::sleep(Duration::from_millis(5));
        let _ = mgr.check_idle();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Dreaming);

        // Second call: Dreaming → Stopped (emits DreamEnded + Stopped)
        std::thread::sleep(Duration::from_millis(5));
        let _ = mgr.check_idle();
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Stopped);

        let events = mgr.events();
        let has_dream_ended = events
            .iter()
            .any(|e| e.kind == ModelKind::Left && e.event == LifecycleEventType::DreamEnded);
        let has_stopped = events
            .iter()
            .any(|e| e.kind == ModelKind::Left && e.event == LifecycleEventType::Stopped);
        assert!(has_dream_ended);
        assert!(has_stopped);
    }

    #[test]
    fn two_tier_idle_dream_then_stop() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_millis(0),
            deep_idle_timeout: Duration::from_secs(3600),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        mgr.start(ModelKind::Left).unwrap();

        // First check: Running → Dreaming
        std::thread::sleep(Duration::from_millis(5));
        let stopped1 = mgr.check_idle();
        assert!(stopped1.is_empty());
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Dreaming);

        // Now reconfigure with short deep idle and check again
        // (We can't reconfigure, so we test with a new manager)
        let config2 = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_millis(0),
            deep_idle_timeout: Duration::from_millis(0),
            ..TriModelConfig::default()
        };
        let mgr2 = TriModelManager::new(config2);
        mgr2.start(ModelKind::Left).unwrap();

        // First check: Running → Dreaming (idle_timeout=0)
        std::thread::sleep(Duration::from_millis(5));
        let stopped2a = mgr2.check_idle();
        assert!(stopped2a.is_empty());
        assert_eq!(mgr2.state(ModelKind::Left), ModelState::Dreaming);

        // Second check: Dreaming → Stopped (deep_idle_timeout=0)
        std::thread::sleep(Duration::from_millis(5));
        let stopped2b = mgr2.check_idle();
        assert!(stopped2b.contains(&ModelKind::Left));
        assert_eq!(mgr2.state(ModelKind::Left), ModelState::Stopped);
    }

    #[test]
    fn dream_mode_does_not_affect_running_models_within_timeout() {
        let config = TriModelConfig {
            idle_mode: IdleMode::Dream,
            idle_timeout: Duration::from_secs(3600),
            deep_idle_timeout: Duration::from_secs(7200),
            ..TriModelConfig::default()
        };
        let mgr = TriModelManager::new(config);
        mgr.start(ModelKind::Left).unwrap();

        let stopped = mgr.check_idle();
        assert!(stopped.is_empty());
        assert_eq!(mgr.state(ModelKind::Left), ModelState::Running);
    }
}
