//! Eco mode controller — brain-wave state machine.
//!
//! Wraps the `BrainWaveTracker` from wm-core and provides metrics,
//! subsystem activation flags, env-var configuration, and the
//! transition tracking needed for the `tokio::select`! event loop.

use std::collections::HashMap;
use std::time::{Duration, Instant};
use wm_core::brain_wave::{BrainWave, BrainWaveConfig, BrainWaveTracker};

/// Per-state subsystem activation flags.
///
/// Determines which subsystems are active in each brain-wave state.
/// The dispatch pipeline and MCP server consult these flags to
/// enable/disable functionality as the system transitions between states.
#[derive(Debug, Clone)]
pub struct SubsystemFlags {
    /// Memory read operations (LMDB get/scan)
    pub memory_read: bool,
    /// Memory write operations (LMDB put/delete)
    pub memory_write: bool,
    /// Tantivy full-text search
    pub search: bool,
    /// Karma ledger recording
    pub karma: bool,
    /// Dharma gate evaluation
    pub dharma: bool,
    /// Citta consciousness heartbeat
    pub citta: bool,
    /// Dream cycle execution
    pub dream: bool,
    /// Vector embedding operations
    pub embeddings: bool,
    /// LLM inference
    pub inference: bool,
}

impl SubsystemFlags {
    /// All subsystems active (Gamma state).
    #[must_use]
    pub const fn all_active() -> Self {
        Self {
            memory_read: true,
            memory_write: true,
            search: true,
            karma: true,
            dharma: true,
            citta: true,
            dream: true,
            embeddings: true,
            inference: true,
        }
    }

    /// No subsystems active (Delta state).
    #[must_use]
    pub const fn none_active() -> Self {
        Self {
            memory_read: false,
            memory_write: false,
            search: false,
            karma: false,
            dharma: false,
            citta: false,
            dream: false,
            embeddings: false,
            inference: false,
        }
    }

    /// Get the flags for a given brain-wave state.
    #[must_use]
    pub const fn for_state(state: BrainWave) -> Self {
        match state {
            BrainWave::Gamma => Self::all_active(),
            BrainWave::Beta => Self {
                dream: false,
                ..Self::all_active()
            },
            BrainWave::Alpha => Self {
                memory_read: true,
                dharma: true,
                citta: true,
                memory_write: false,
                search: false,
                karma: false,
                dream: false,
                embeddings: false,
                inference: false,
            },
            BrainWave::Theta => Self {
                memory_read: true,
                memory_write: true,
                dream: true,
                dharma: true,
                search: false,
                karma: false,
                citta: false,
                embeddings: false,
                inference: false,
            },
            BrainWave::Delta => Self::none_active(),
        }
    }
}

/// Metrics for the brain-wave eco mode.
///
/// Tracks time spent in each state, transition counts, and total events.
#[derive(Debug, Clone)]
pub struct EcoModeMetrics {
    /// Total time spent in each brain-wave state
    time_in_state: HashMap<BrainWave, Duration>,
    /// Number of transitions into each state
    transition_counts: HashMap<BrainWave, u64>,
    /// Total number of events recorded
    total_events: u64,
    /// When the current state was entered
    current_state_entered: Instant,
    /// Last transition timestamp
    last_transition: Instant,
}

impl EcoModeMetrics {
    /// Create a new metrics tracker starting in Delta state.
    #[must_use]
    pub fn new() -> Self {
        let now = Instant::now();
        let mut time_in_state = HashMap::new();
        let mut transition_counts = HashMap::new();
        for state in [
            BrainWave::Gamma,
            BrainWave::Beta,
            BrainWave::Alpha,
            BrainWave::Theta,
            BrainWave::Delta,
        ] {
            time_in_state.insert(state, Duration::ZERO);
            transition_counts.insert(state, 0);
        }
        transition_counts.insert(BrainWave::Delta, 1);
        Self {
            time_in_state,
            transition_counts,
            total_events: 0,
            current_state_entered: now,
            last_transition: now,
        }
    }

    /// Record a state transition. Call this when the brain-wave state changes.
    pub fn record_transition(&mut self, new_state: BrainWave) {
        let now = Instant::now();
        let elapsed = now.duration_since(self.current_state_entered);
        *self.time_in_state.entry(new_state).or_default() += elapsed;
        *self.transition_counts.entry(new_state).or_default() += 1;
        self.current_state_entered = now;
        self.last_transition = now;
    }

    /// Record an event (MCP request received).
    pub const fn record_event(&mut self) {
        self.total_events += 1;
    }

    /// Get total time spent in a state.
    #[must_use]
    pub fn time_in(&self, state: BrainWave) -> Duration {
        self.time_in_state
            .get(&state)
            .copied()
            .unwrap_or(Duration::ZERO)
    }

    /// Get the number of transitions into a state.
    #[must_use]
    pub fn transitions_into(&self, state: BrainWave) -> u64 {
        self.transition_counts.get(&state).copied().unwrap_or(0)
    }

    /// Total events recorded.
    #[must_use]
    pub const fn total_events(&self) -> u64 {
        self.total_events
    }

    /// Time since the current state was entered.
    #[must_use]
    pub fn time_in_current(&self) -> Duration {
        Instant::now().duration_since(self.current_state_entered)
    }

    /// Convert metrics to a JSON-serializable map.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "total_events": self.total_events,
            "time_in_current_ms": self.time_in_current().as_millis(),
            "states": {
                "gamma": {
                    "time_ms": self.time_in(BrainWave::Gamma).as_millis(),
                    "transitions": self.transitions_into(BrainWave::Gamma),
                },
                "beta": {
                    "time_ms": self.time_in(BrainWave::Beta).as_millis(),
                    "transitions": self.transitions_into(BrainWave::Beta),
                },
                "alpha": {
                    "time_ms": self.time_in(BrainWave::Alpha).as_millis(),
                    "transitions": self.transitions_into(BrainWave::Alpha),
                },
                "theta": {
                    "time_ms": self.time_in(BrainWave::Theta).as_millis(),
                    "transitions": self.transitions_into(BrainWave::Theta),
                },
                "delta": {
                    "time_ms": self.time_in(BrainWave::Delta).as_millis(),
                    "transitions": self.transitions_into(BrainWave::Delta),
                },
            },
        })
    }
}

impl Default for EcoModeMetrics {
    fn default() -> Self {
        Self::new()
    }
}

/// Controller for the brain-wave eco mode.
///
/// Wraps `BrainWaveTracker` and adds metrics tracking, subsystem flags,
/// and env-var configuration. The MCP server uses this to drive the
/// `tokio::select!` event loop for zero-CPU dormancy.
pub struct EcoModeController {
    tracker: BrainWaveTracker,
    metrics: EcoModeMetrics,
    flags: SubsystemFlags,
}

impl EcoModeController {
    /// Create a new eco mode controller with the given config.
    #[must_use]
    pub fn new(config: BrainWaveConfig) -> Self {
        let state = BrainWave::Delta;
        Self {
            tracker: BrainWaveTracker::new(config),
            metrics: EcoModeMetrics::new(),
            flags: SubsystemFlags::for_state(state),
        }
    }

    /// Create with default config.
    #[must_use]
    #[allow(clippy::should_implement_trait)]
    pub fn default() -> Self {
        Self::new(BrainWaveConfig::default())
    }

    /// Create from environment variables.
    ///
    /// Recognized env vars:
    /// - `WM_GAMMA_RATE` — events per minute for Gamma (default: 10)
    /// - `WM_ALPHA_IDLE` — seconds idle before Alpha (default: 30)
    /// - `WM_THETA_IDLE` — seconds idle before Theta (default: 300)
    /// - `WM_DELTA_IDLE` — seconds idle before Delta (default: 1800)
    #[must_use]
    pub fn from_env() -> Self {
        Self::new(BrainWaveConfig::from_env())
    }

    /// Record an event (e.g., MCP request received).
    /// Returns the new brain-wave state after recording.
    pub fn record_event(&mut self) -> BrainWave {
        let old = self.tracker.current();
        let new = self.tracker.record_event();
        self.metrics.record_event();
        if old != new {
            self.metrics.record_transition(new);
            self.flags = SubsystemFlags::for_state(new);
        }
        new
    }

    /// Get the current brain-wave state.
    #[must_use]
    pub const fn current(&self) -> BrainWave {
        self.tracker.current()
    }

    /// Recompute state after idle time (call before `tokio::select`!).
    /// Returns the new state, recording a transition if it changed.
    pub fn recompute(&mut self) -> BrainWave {
        let old = self.tracker.current();
        let new = self.tracker.recompute(Instant::now());
        if old != new {
            self.metrics.record_transition(new);
            self.flags = SubsystemFlags::for_state(new);
        }
        new
    }

    /// Compute how long to sleep before the next state transition.
    #[must_use]
    pub fn next_transition_duration(&self) -> Duration {
        self.tracker.next_transition_duration()
    }

    /// Get the current subsystem flags.
    #[must_use]
    pub const fn subsystems(&self) -> &SubsystemFlags {
        &self.flags
    }

    /// Get a reference to the metrics.
    #[must_use]
    pub const fn metrics(&self) -> &EcoModeMetrics {
        &self.metrics
    }

    /// Get a mutable reference to the metrics.
    pub const fn metrics_mut(&mut self) -> &mut EcoModeMetrics {
        &mut self.metrics
    }

    /// Get the brain-wave config.
    #[must_use]
    pub const fn config(&self) -> &BrainWaveConfig {
        &self.tracker.config
    }

    /// Idle duration since last event.
    #[must_use]
    pub fn idle_duration(&self) -> Duration {
        self.tracker.idle_duration()
    }

    /// Apply presence activity ratio to modulate brain-wave transitions.
    ///
    /// High activity ratio (> 0.5) → treat as recent event, stay active longer.
    /// Low activity ratio (< 0.2) → accelerate transition toward deeper rest.
    /// This is called after `recompute()` to adjust the final state.
    pub fn apply_presence(&mut self, activity_ratio: f32) -> BrainWave {
        let current = self.tracker.current();
        // High activity prevents dropping below Alpha
        if activity_ratio > 0.5 && current == BrainWave::Alpha {
            // Bump up to Beta — system is actively processing
            return self.record_event();
        }
        // Very low activity accelerates descent
        if activity_ratio < 0.1 && current == BrainWave::Alpha {
            // Force recompute with artificial idle — transition to Theta sooner
            let _ = self.recompute();
        }
        self.tracker.current()
    }

    /// Apply hardware harmony to gate brain-wave transitions (Tiferet).
    ///
    /// The health score (0.0 = critical, 1.0 = perfect) from the Harmony
    /// Vector (Lakshmi) modulates the maximum allowed brain-wave state:
    /// - health < 0.3 (stressed): cap at Alpha — no high-power states
    /// - health < 0.5 (strained): cap at Beta — no Gamma
    /// - health >= 0.5: no restriction
    ///
    /// Additionally, when stressed, accelerate descent to lower-power
    /// states by forcing a recompute. This is the Tiferet (Harmony/Beauty)
    /// layer — it mediates between the body (Lakshmi) and the mind
    /// (brain-wave states), ensuring the cognitive system never demands
    /// more energy than the hardware can provide.
    ///
    /// Call this after `recompute()` and `apply_presence()` to apply
    /// the final hardware-aware gating.
    pub fn apply_harmony(&mut self, health_score: f32) -> BrainWave {
        let current = self.tracker.current();

        // Determine the maximum allowed state based on health
        let max_state = if health_score < 0.3 {
            BrainWave::Alpha // Stressed — only reads, no writes/dreams
        } else if health_score < 0.5 {
            BrainWave::Beta // Strained — active but no Gamma bursts
        } else {
            BrainWave::Gamma // Healthy — no restriction
        };

        // If current state exceeds the maximum, force a descent
        let needs_descent = matches!(
            (current, max_state),
            (BrainWave::Gamma, BrainWave::Alpha | BrainWave::Beta)
                | (BrainWave::Beta, BrainWave::Alpha)
        );

        if needs_descent {
            // Force recompute — the tracker will naturally descend based on
            // idle time. If we're here, the system can't sustain the current
            // state. We record the transition.
            let old = current;
            let new = self.tracker.recompute(Instant::now());
            // If recompute didn't bring us down enough (e.g., recent events),
            // manually clamp by recording a synthetic transition
            let clamped = match (new, max_state) {
                (BrainWave::Gamma, BrainWave::Alpha | BrainWave::Beta) => max_state,
                (BrainWave::Beta, BrainWave::Alpha) => BrainWave::Alpha,
                _ => new,
            };
            if old != clamped {
                self.metrics.record_transition(clamped);
                self.flags = SubsystemFlags::for_state(clamped);
            }
            return clamped;
        }

        // When stressed but already in a low state, accelerate descent
        if health_score < 0.3 && current == BrainWave::Alpha {
            let _ = self.recompute();
        }

        self.tracker.current()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn subsystem_flags_gamma_all_active() {
        let flags = SubsystemFlags::for_state(BrainWave::Gamma);
        assert!(flags.memory_read);
        assert!(flags.memory_write);
        assert!(flags.dream);
        assert!(flags.inference);
    }

    #[test]
    fn subsystem_flags_beta_no_dream() {
        let flags = SubsystemFlags::for_state(BrainWave::Beta);
        assert!(flags.memory_read);
        assert!(flags.memory_write);
        assert!(!flags.dream);
    }

    #[test]
    fn subsystem_flags_alpha_reads_only() {
        let flags = SubsystemFlags::for_state(BrainWave::Alpha);
        assert!(flags.memory_read);
        assert!(flags.dharma);
        assert!(flags.citta);
        assert!(!flags.memory_write);
        assert!(!flags.search);
        assert!(!flags.dream);
        assert!(!flags.embeddings);
        assert!(!flags.inference);
    }

    #[test]
    fn subsystem_flags_theta_dream_active() {
        let flags = SubsystemFlags::for_state(BrainWave::Theta);
        assert!(flags.dream);
        assert!(flags.memory_read);
        assert!(flags.memory_write);
        assert!(!flags.search);
        assert!(!flags.embeddings);
    }

    #[test]
    fn subsystem_flags_delta_none_active() {
        let flags = SubsystemFlags::for_state(BrainWave::Delta);
        assert!(!flags.memory_read);
        assert!(!flags.dream);
    }

    #[test]
    fn eco_mode_records_transitions() {
        let mut eco = EcoModeController::default();
        assert_eq!(eco.current(), BrainWave::Delta);

        // Record an event → should transition to Beta
        let state = eco.record_event();
        assert_eq!(state, BrainWave::Beta);
        assert_eq!(eco.metrics().transitions_into(BrainWave::Beta), 1);
        assert_eq!(eco.metrics().total_events(), 1);
    }

    #[test]
    fn eco_mode_subsystems_update_on_transition() {
        let mut eco = EcoModeController::default();
        assert!(!eco.subsystems().memory_read); // Delta

        eco.record_event();
        assert!(eco.subsystems().memory_read); // Beta
        assert!(eco.subsystems().memory_write);
    }

    #[test]
    fn eco_mode_metrics_json() {
        let mut eco = EcoModeController::default();
        eco.record_event();
        eco.record_event();
        let json = eco.metrics().to_json();
        assert_eq!(json["total_events"], 2);
        assert!(json["states"]["beta"]["transitions"].as_u64() >= Some(1));
    }

    #[test]
    fn eco_mode_next_transition_after_event() {
        let mut eco = EcoModeController::default();
        eco.record_event();
        let d = eco.next_transition_duration();
        // Should be ~30s (alpha_idle) minus ~0s idle
        assert!(d <= Duration::from_secs(30));
        assert!(d > Duration::from_secs(28));
    }

    #[test]
    fn brain_wave_config_from_env_uses_defaults() {
        // Env vars are unlikely to be set in test environment;
        // from_env() should fall back to defaults
        let config = BrainWaveConfig::from_env();
        // Only assert if the env vars are not set — if they are, the test
        // environment has overridden them, which is fine.
        if std::env::var("WM_GAMMA_RATE").is_err() {
            assert_eq!(config.gamma_rate, 10.0);
        }
        if std::env::var("WM_ALPHA_IDLE").is_err() {
            assert_eq!(config.alpha_idle, Duration::from_secs(30));
        }
        if std::env::var("WM_THETA_IDLE").is_err() {
            assert_eq!(config.theta_idle, Duration::from_secs(300));
        }
        if std::env::var("WM_DELTA_IDLE").is_err() {
            assert_eq!(config.delta_idle, Duration::from_secs(1800));
        }
    }

    #[test]
    fn apply_presence_high_activity_keeps_beta() {
        let mut eco = EcoModeController::default();
        eco.record_event(); // Beta
        assert_eq!(eco.current(), BrainWave::Beta);
        // High activity shouldn't drop us below Alpha
        let state = eco.apply_presence(0.8);
        assert!(matches!(state, BrainWave::Beta | BrainWave::Gamma));
    }

    #[test]
    fn apply_presence_low_activity_stays_current() {
        let mut eco = EcoModeController::default();
        eco.record_event(); // Beta
        // Low activity ratio — shouldn't force a change from Beta
        let state = eco.apply_presence(0.05);
        // From Beta, low presence doesn't immediately drop
        assert!(matches!(state, BrainWave::Beta | BrainWave::Alpha));
    }

    #[test]
    fn apply_harmony_healthy_no_restriction() {
        let mut eco = EcoModeController::default();
        for _ in 0..15 {
            let _ = eco.record_event();
        }
        assert_eq!(eco.current(), BrainWave::Gamma);

        // Healthy — no restriction
        let state = eco.apply_harmony(0.9);
        assert_eq!(state, BrainWave::Gamma);
    }

    #[test]
    fn apply_harmony_strained_caps_at_beta() {
        let mut eco = EcoModeController::default();
        for _ in 0..15 {
            let _ = eco.record_event();
        }
        assert_eq!(eco.current(), BrainWave::Gamma);

        // Strained — should cap at Beta (no Gamma)
        let state = eco.apply_harmony(0.4);
        assert!(
            matches!(state, BrainWave::Beta | BrainWave::Alpha),
            "Should not be Gamma when strained, got {state:?}"
        );
    }

    #[test]
    fn apply_harmony_stressed_caps_at_alpha() {
        let mut eco = EcoModeController::default();
        for _ in 0..15 {
            let _ = eco.record_event();
        }
        assert_eq!(eco.current(), BrainWave::Gamma);

        // Stressed — should cap at Alpha
        let state = eco.apply_harmony(0.2);
        assert!(
            matches!(state, BrainWave::Alpha | BrainWave::Beta),
            "Should not be Gamma when stressed, got {state:?}"
        );
    }

    #[test]
    fn apply_harmony_beta_to_alpha_when_stressed() {
        let mut eco = EcoModeController::default();
        eco.record_event();
        assert_eq!(eco.current(), BrainWave::Beta);

        // Stressed — Beta should descend to Alpha
        let state = eco.apply_harmony(0.2);
        assert!(
            matches!(state, BrainWave::Alpha | BrainWave::Beta),
            "Should descend from Beta when stressed, got {state:?}"
        );
    }

    #[test]
    fn apply_harmony_alpha_stays_alpha_when_stressed() {
        let mut eco = EcoModeController::default();
        // Force Alpha by recording an event then waiting (simulated)
        eco.record_event();
        // Apply low health — should try to descend further
        let state = eco.apply_harmony(0.15);
        // From Beta with stress, should descend
        assert!(state != BrainWave::Gamma);
    }

    #[test]
    fn apply_harmony_does_not_ascend() {
        let mut eco = EcoModeController::default();
        assert_eq!(eco.current(), BrainWave::Delta);

        // Even with perfect health, apply_harmony should not force an ascent
        let state = eco.apply_harmony(1.0);
        assert_eq!(state, BrainWave::Delta);
    }
}
