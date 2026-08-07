//! Resource Governor — hardware-aware adaptive inference control.
//!
//! Dynamically adjusts inference resource usage based on physical system
//! metrics (CPU temp, memory pressure, swap). When the hardware is
//! stressed, the governor switches to ECO mode (shorter idle timeouts,
//! smaller context, fewer parallel slots). When comfortable, it unlocks
//! PERFORMANCE mode (larger context, more parallelism, longer timeouts).
//!
//! Ported from v2 `inference/resource_governor.py` (358 lines).
//! In v4, the governor is a pure Rust struct that accepts `HardwareMetrics`
//! and returns mode transitions. It does not directly control backends —
//! instead it provides `ModeProfile` values that the `TriModelManager` (N1)
//! and `InferenceTuner` (N8) can apply.
//!
//! Modes:
//! - **ECO**: minimal footprint, aggressive idle shutdown
//! - **NORMAL**: balanced (default)
//! - **PERFORMANCE**: maximum capability, relaxed idle timeouts

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Governor mode — the current resource profile level.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum GovernorMode {
    /// Minimal footprint, aggressive idle shutdown.
    Eco,
    /// Balanced (default).
    Normal,
    /// Maximum capability, relaxed idle timeouts.
    Performance,
}

impl GovernorMode {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Eco => "eco",
            Self::Normal => "normal",
            Self::Performance => "performance",
        }
    }

    /// All modes in order from most constrained to least.
    #[must_use]
    pub const fn all() -> [Self; 3] {
        [Self::Eco, Self::Normal, Self::Performance]
    }

    /// Whether this mode is more constrained than the other.
    #[must_use]
    pub const fn is_more_constrained_than(self, other: Self) -> bool {
        matches!(
            (self, other),
            (Self::Eco, Self::Normal | Self::Performance) | (Self::Normal, Self::Performance)
        )
    }
}

/// Resource profile for a governor mode.
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct ModeProfile {
    /// Seconds before idle shutdown.
    pub idle_timeout: u64,
    /// Max context size.
    pub max_ctx: usize,
    /// Max parallel slots.
    pub parallel: usize,
    /// Whether to stop foreground model.
    pub stop_foreground: bool,
    /// Whether to stop draft model.
    pub stop_draft: bool,
    /// Whether on-demand server starts are allowed.
    pub allow_new_servers: bool,
}

impl ModeProfile {
    /// ECO profile — minimal footprint.
    pub const ECO: Self = Self {
        idle_timeout: 60,
        max_ctx: 2048,
        parallel: 1,
        stop_foreground: true,
        stop_draft: true,
        allow_new_servers: false,
    };

    /// NORMAL profile — balanced.
    pub const NORMAL: Self = Self {
        idle_timeout: 300,
        max_ctx: 4096,
        parallel: 2,
        stop_foreground: false,
        stop_draft: false,
        allow_new_servers: true,
    };

    /// PERFORMANCE profile — maximum capability.
    pub const PERFORMANCE: Self = Self {
        idle_timeout: 600,
        max_ctx: 8192,
        parallel: 4,
        stop_foreground: false,
        stop_draft: false,
        allow_new_servers: true,
    };

    /// Get the profile for a given mode.
    #[must_use]
    pub const fn for_mode(mode: GovernorMode) -> Self {
        match mode {
            GovernorMode::Eco => Self::ECO,
            GovernorMode::Normal => Self::NORMAL,
            GovernorMode::Performance => Self::PERFORMANCE,
        }
    }
}

/// Hardware metrics snapshot fed to the governor.
#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize)]
pub struct HardwareMetrics {
    /// CPU temperature in Celsius (if available).
    pub cpu_temp: Option<f32>,
    /// Memory usage fraction (0.0 = empty, 1.0 = full).
    pub memory_pressure: Option<f32>,
    /// Swap usage fraction (0.0 = none, 1.0 = full).
    pub swap_usage: Option<f32>,
    /// Battery charge fraction (0.0 = empty, 1.0 = full).
    pub battery_percent: Option<f32>,
}

impl HardwareMetrics {
    /// Create metrics from raw values.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            cpu_temp: None,
            memory_pressure: None,
            swap_usage: None,
            battery_percent: None,
        }
    }

    /// Set CPU temperature.
    #[must_use]
    pub const fn with_cpu_temp(mut self, temp: f32) -> Self {
        self.cpu_temp = Some(temp);
        self
    }

    /// Set memory pressure (0.0–1.0).
    #[must_use]
    pub const fn with_memory(mut self, pressure: f32) -> Self {
        self.memory_pressure = Some(pressure);
        self
    }

    /// Set swap usage (0.0–1.0).
    #[must_use]
    pub const fn with_swap(mut self, usage: f32) -> Self {
        self.swap_usage = Some(usage);
        self
    }

    /// Set battery percent (0.0–1.0).
    #[must_use]
    pub const fn with_battery(mut self, percent: f32) -> Self {
        self.battery_percent = Some(percent);
        self
    }

    /// Whether any metrics are available.
    #[must_use]
    pub const fn is_available(&self) -> bool {
        self.cpu_temp.is_some() || self.memory_pressure.is_some() || self.swap_usage.is_some()
    }
}

/// Record of a mode transition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GovernorTransition {
    /// Previous mode.
    pub from_mode: GovernorMode,
    /// New mode.
    pub to_mode: GovernorMode,
    /// Human-readable reason for the transition.
    pub reason: String,
    /// CPU temp at time of transition.
    pub cpu_temp: Option<f32>,
    /// Memory pressure at time of transition.
    pub memory_pressure: Option<f32>,
    /// Actions taken during transition.
    pub actions_taken: Vec<String>,
}

/// Resource Governor — hardware-aware adaptive inference controller.
///
/// Monitors hardware metrics and dynamically adjusts inference resource
/// profiles. Designed to be called periodically (e.g., by a homeostatic
/// loop). The governor classifies current metrics into a mode and
/// transitions if the mode has changed.
///
/// The governor does not directly control model backends — it provides
/// `ModeProfile` values that callers can apply. This keeps it decoupled
/// from specific backend implementations.
pub struct ResourceGovernor {
    mode: GovernorMode,
    transitions: Vec<GovernorTransition>,
    last_metrics: HardwareMetrics,
    enabled: bool,
    /// Registered backend names (for status reporting).
    backends: HashMap<String, GovernorMode>,
}

impl ResourceGovernor {
    /// Create a new governor in NORMAL mode.
    #[must_use]
    pub fn new() -> Self {
        Self {
            mode: GovernorMode::Normal,
            transitions: Vec::new(),
            last_metrics: HardwareMetrics::new(),
            enabled: true,
            backends: HashMap::new(),
        }
    }

    /// Current governor mode.
    #[must_use]
    pub const fn mode(&self) -> GovernorMode {
        self.mode
    }

    /// Current mode profile.
    #[must_use]
    pub const fn profile(&self) -> ModeProfile {
        ModeProfile::for_mode(self.mode)
    }

    /// Whether the governor is enabled.
    #[must_use]
    pub const fn enabled(&self) -> bool {
        self.enabled
    }

    /// Enable or disable the governor.
    pub const fn set_enabled(&mut self, enabled: bool) {
        self.enabled = enabled;
    }

    /// Register a backend name for status tracking.
    pub fn register_backend(&mut self, name: impl Into<String>) {
        self.backends.insert(name.into(), self.mode);
    }

    /// Unregister a backend.
    pub fn unregister_backend(&mut self, name: &str) {
        self.backends.remove(name);
    }

    /// Check if the governor allows starting a new server.
    #[must_use]
    pub const fn can_start_server(&self) -> bool {
        if !self.enabled {
            return true;
        }
        self.profile().allow_new_servers
    }

    /// Classify hardware metrics into a governor mode.
    fn classify(metrics: &HardwareMetrics) -> GovernorMode {
        // ECO: any critical stress signal
        if let Some(temp) = metrics.cpu_temp {
            if temp >= 80.0 {
                return GovernorMode::Eco;
            }
        }
        if let Some(mem) = metrics.memory_pressure {
            if mem >= 0.85 {
                return GovernorMode::Eco;
            }
        }
        if let Some(swap) = metrics.swap_usage {
            if swap >= 0.80 {
                return GovernorMode::Eco;
            }
        }

        // NORMAL: moderate stress
        if let Some(temp) = metrics.cpu_temp {
            if temp >= 65.0 {
                return GovernorMode::Normal;
            }
        }
        if let Some(mem) = metrics.memory_pressure {
            if mem >= 0.75 {
                return GovernorMode::Normal;
            }
        }
        if let Some(swap) = metrics.swap_usage {
            if swap >= 0.50 {
                return GovernorMode::Normal;
            }
        }

        // PERFORMANCE: everything comfortable
        let temp_ok = metrics.cpu_temp.is_none_or(|t| t < 60.0);
        let mem_ok = metrics.memory_pressure.is_none_or(|m| m < 0.65);
        if temp_ok && mem_ok {
            return GovernorMode::Performance;
        }

        // Default to NORMAL if we can't confirm comfortable
        GovernorMode::Normal
    }

    /// Evaluate hardware metrics and transition modes if needed.
    ///
    /// Returns a `GovernorTransition` if a mode change occurred, else `None`.
    pub fn evaluate(&mut self, metrics: HardwareMetrics) -> Option<GovernorTransition> {
        if !self.enabled {
            return None;
        }

        if !metrics.is_available() {
            return None;
        }

        self.last_metrics = metrics;

        let new_mode = Self::classify(&metrics);
        if new_mode == self.mode {
            return None;
        }

        Some(self.transition(new_mode))
    }

    /// Execute a mode transition.
    fn transition(&mut self, new_mode: GovernorMode) -> GovernorTransition {
        let old_mode = self.mode;
        let profile = ModeProfile::for_mode(new_mode);

        let mut actions = Vec::new();

        // Update registered backends
        for (name, backend_mode) in &mut self.backends {
            if *backend_mode != new_mode {
                actions.push(format!(
                    "{}: idle_timeout→{}s, max_ctx→{}, parallel→{}",
                    name, profile.idle_timeout, profile.max_ctx, profile.parallel
                ));
                *backend_mode = new_mode;
            }
        }

        // ECO mode: stop foreground and draft
        if profile.stop_foreground && self.backends.contains_key("foreground") {
            actions.push("foreground: stopped (ECO mode)".to_string());
        }
        if profile.stop_draft && self.backends.contains_key("draft") {
            actions.push("draft: stopped (ECO mode)".to_string());
        }

        let reason = self.transition_reason(old_mode, new_mode);

        let transition = GovernorTransition {
            from_mode: old_mode,
            to_mode: new_mode,
            reason,
            cpu_temp: self.last_metrics.cpu_temp,
            memory_pressure: self.last_metrics.memory_pressure,
            actions_taken: actions,
        };

        self.mode = new_mode;
        self.transitions.push(transition.clone());

        // Keep transition history bounded
        if self.transitions.len() > 100 {
            self.transitions.drain(0..50);
        }

        transition
    }

    /// Generate a human-readable transition reason.
    fn transition_reason(&self, old: GovernorMode, new: GovernorMode) -> String {
        let direction = if new.is_more_constrained_than(old) {
            "downgrade"
        } else {
            "upgrade"
        };

        let mut parts = Vec::new();
        if let Some(temp) = self.last_metrics.cpu_temp {
            parts.push(format!("cpu={temp:.0}°C"));
        }
        if let Some(mem) = self.last_metrics.memory_pressure {
            parts.push(format!("mem={:.0}%", mem * 100.0));
        }

        format!("{direction} ({})", parts.join(", "))
    }

    /// Number of transitions recorded.
    #[must_use]
    pub fn transition_count(&self) -> usize {
        self.transitions.len()
    }

    /// Last transition (if any).
    #[must_use]
    pub fn last_transition(&self) -> Option<&GovernorTransition> {
        self.transitions.last()
    }

    /// All transitions.
    #[must_use]
    pub fn transitions(&self) -> &[GovernorTransition] {
        &self.transitions
    }

    /// Last metrics seen.
    #[must_use]
    pub const fn last_metrics(&self) -> HardwareMetrics {
        self.last_metrics
    }

    /// Get governor status as JSON.
    #[must_use]
    pub fn status(&self) -> serde_json::Value {
        let profile = self.profile();
        serde_json::json!({
            "enabled": self.enabled,
            "mode": self.mode.as_str(),
            "profile": {
                "idle_timeout": profile.idle_timeout,
                "max_ctx": profile.max_ctx,
                "parallel": profile.parallel,
                "stop_foreground": profile.stop_foreground,
                "stop_draft": profile.stop_draft,
                "allow_new_servers": profile.allow_new_servers,
            },
            "registered_backends": self.backends.keys().collect::<Vec<_>>(),
            "last_metrics": {
                "cpu_temp": self.last_metrics.cpu_temp,
                "memory_pressure": self.last_metrics.memory_pressure,
                "swap_usage": self.last_metrics.swap_usage,
                "battery_percent": self.last_metrics.battery_percent,
            },
            "transition_count": self.transitions.len(),
        })
    }
}

impl Default for ResourceGovernor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_governor_starts_in_normal_mode() {
        let gov = ResourceGovernor::new();
        assert_eq!(gov.mode(), GovernorMode::Normal);
    }

    #[test]
    fn mode_as_str() {
        assert_eq!(GovernorMode::Eco.as_str(), "eco");
        assert_eq!(GovernorMode::Normal.as_str(), "normal");
        assert_eq!(GovernorMode::Performance.as_str(), "performance");
    }

    #[test]
    fn mode_all_returns_three_modes() {
        assert_eq!(GovernorMode::all().len(), 3);
    }

    #[test]
    fn is_more_constrained_than() {
        assert!(GovernorMode::Eco.is_more_constrained_than(GovernorMode::Normal));
        assert!(GovernorMode::Eco.is_more_constrained_than(GovernorMode::Performance));
        assert!(GovernorMode::Normal.is_more_constrained_than(GovernorMode::Performance));
        assert!(!GovernorMode::Performance.is_more_constrained_than(GovernorMode::Normal));
    }

    #[test]
    fn profile_for_mode() {
        assert_eq!(ModeProfile::for_mode(GovernorMode::Eco).max_ctx, 2048);
        assert_eq!(ModeProfile::for_mode(GovernorMode::Normal).max_ctx, 4096);
        assert_eq!(
            ModeProfile::for_mode(GovernorMode::Performance).max_ctx,
            8192
        );
    }

    #[test]
    fn profile_eco_stops_foreground_and_draft() {
        let profile = ModeProfile::for_mode(GovernorMode::Eco);
        assert!(profile.stop_foreground);
        assert!(profile.stop_draft);
        assert!(!profile.allow_new_servers);
        // Sanity: ECO is more constrained than NORMAL
        assert!(GovernorMode::Eco.is_more_constrained_than(GovernorMode::Normal));
    }

    #[test]
    fn profile_performance_allows_new_servers() {
        let profile = ModeProfile::for_mode(GovernorMode::Performance);
        assert!(profile.allow_new_servers);
    }

    #[test]
    fn profile_idle_timeouts() {
        assert_eq!(ModeProfile::ECO.idle_timeout, 60);
        assert_eq!(ModeProfile::NORMAL.idle_timeout, 300);
        assert_eq!(ModeProfile::PERFORMANCE.idle_timeout, 600);
    }

    #[test]
    fn hardware_metrics_default_empty() {
        let m = HardwareMetrics::new();
        assert!(!m.is_available());
    }

    #[test]
    fn hardware_metrics_with_values() {
        let m = HardwareMetrics::new()
            .with_cpu_temp(75.0)
            .with_memory(0.8)
            .with_swap(0.3)
            .with_battery(0.5);
        assert!(m.is_available());
        assert_eq!(m.cpu_temp, Some(75.0));
        assert_eq!(m.memory_pressure, Some(0.8));
    }

    #[test]
    fn evaluate_no_metrics_returns_none() {
        let mut gov = ResourceGovernor::new();
        let result = gov.evaluate(HardwareMetrics::new());
        assert!(result.is_none());
    }

    #[test]
    fn evaluate_disabled_returns_none() {
        let mut gov = ResourceGovernor::new();
        gov.set_enabled(false);
        let metrics = HardwareMetrics::new().with_cpu_temp(50.0);
        let result = gov.evaluate(metrics);
        assert!(result.is_none());
    }

    #[test]
    fn evaluate_same_mode_returns_none() {
        let mut gov = ResourceGovernor::new();
        // NORMAL mode with comfortable metrics → should classify as Performance
        // but let's use metrics that classify as Normal
        let metrics = HardwareMetrics::new().with_cpu_temp(70.0);
        let result = gov.evaluate(metrics);
        // 70°C → NORMAL (already in NORMAL)
        assert!(result.is_none());
    }

    #[test]
    fn high_temp_triggers_eco() {
        let mut gov = ResourceGovernor::new();
        let metrics = HardwareMetrics::new().with_cpu_temp(85.0);
        let transition = gov.evaluate(metrics);
        assert!(transition.is_some());
        let t = transition.unwrap();
        assert_eq!(t.from_mode, GovernorMode::Normal);
        assert_eq!(t.to_mode, GovernorMode::Eco);
        assert_eq!(gov.mode(), GovernorMode::Eco);
    }

    #[test]
    fn high_memory_triggers_eco() {
        let mut gov = ResourceGovernor::new();
        let metrics = HardwareMetrics::new().with_memory(0.90);
        let transition = gov.evaluate(metrics);
        assert!(transition.is_some());
        assert_eq!(transition.unwrap().to_mode, GovernorMode::Eco);
    }

    #[test]
    fn high_swap_triggers_eco() {
        let mut gov = ResourceGovernor::new();
        let metrics = HardwareMetrics::new().with_swap(0.85);
        let transition = gov.evaluate(metrics);
        assert!(transition.is_some());
        assert_eq!(transition.unwrap().to_mode, GovernorMode::Eco);
    }

    #[test]
    fn moderate_temp_triggers_normal() {
        let mut gov = ResourceGovernor::new();
        // Start in Performance first
        let cool = HardwareMetrics::new().with_cpu_temp(50.0).with_memory(0.3);
        gov.evaluate(cool);
        assert_eq!(gov.mode(), GovernorMode::Performance);

        // Moderate temp → Normal
        let moderate = HardwareMetrics::new().with_cpu_temp(68.0).with_memory(0.3);
        let transition = gov.evaluate(moderate);
        assert!(transition.is_some());
        assert_eq!(transition.unwrap().to_mode, GovernorMode::Normal);
    }

    #[test]
    fn comfortable_metrics_trigger_performance() {
        let mut gov = ResourceGovernor::new();
        let metrics = HardwareMetrics::new()
            .with_cpu_temp(45.0)
            .with_memory(0.3)
            .with_swap(0.1);
        let transition = gov.evaluate(metrics);
        assert!(transition.is_some());
        assert_eq!(transition.unwrap().to_mode, GovernorMode::Performance);
    }

    #[test]
    fn transition_records_reason() {
        let mut gov = ResourceGovernor::new();
        let metrics = HardwareMetrics::new().with_cpu_temp(85.0).with_memory(0.9);
        let transition = gov.evaluate(metrics).unwrap();
        assert!(transition.reason.contains("downgrade"));
        assert!(transition.reason.contains("cpu="));
        assert!(transition.reason.contains("mem="));
    }

    #[test]
    fn transition_records_upgrade() {
        let mut gov = ResourceGovernor::new();
        // First go to ECO
        gov.evaluate(HardwareMetrics::new().with_cpu_temp(90.0));
        assert_eq!(gov.mode(), GovernorMode::Eco);

        // Then recover to Performance
        let transition = gov.evaluate(HardwareMetrics::new().with_cpu_temp(40.0).with_memory(0.3));
        assert!(transition.is_some());
        let t = transition.unwrap();
        assert!(t.reason.contains("upgrade"));
        assert_eq!(t.from_mode, GovernorMode::Eco);
        assert_eq!(t.to_mode, GovernorMode::Performance);
    }

    #[test]
    fn transition_count_accumulates() {
        let mut gov = ResourceGovernor::new();
        assert_eq!(gov.transition_count(), 0);

        gov.evaluate(HardwareMetrics::new().with_cpu_temp(90.0));
        assert_eq!(gov.transition_count(), 1);

        gov.evaluate(HardwareMetrics::new().with_cpu_temp(40.0).with_memory(0.3));
        assert_eq!(gov.transition_count(), 2);
    }

    #[test]
    fn last_transition_returns_most_recent() {
        let mut gov = ResourceGovernor::new();
        gov.evaluate(HardwareMetrics::new().with_cpu_temp(90.0));
        gov.evaluate(HardwareMetrics::new().with_cpu_temp(40.0).with_memory(0.3));

        let last = gov.last_transition().unwrap();
        assert_eq!(last.to_mode, GovernorMode::Performance);
    }

    #[test]
    fn can_start_server_eco_returns_false() {
        let mut gov = ResourceGovernor::new();
        gov.evaluate(HardwareMetrics::new().with_cpu_temp(90.0));
        assert_eq!(gov.mode(), GovernorMode::Eco);
        assert!(!gov.can_start_server());
    }

    #[test]
    fn can_start_server_normal_returns_true() {
        let gov = ResourceGovernor::new();
        assert_eq!(gov.mode(), GovernorMode::Normal);
        assert!(gov.can_start_server());
    }

    #[test]
    fn can_start_server_disabled_returns_true() {
        let mut gov = ResourceGovernor::new();
        gov.set_enabled(false);
        assert!(gov.can_start_server());
    }

    #[test]
    fn register_and_unregister_backend() {
        let mut gov = ResourceGovernor::new();
        gov.register_backend("foreground");
        gov.register_backend("draft");
        assert_eq!(gov.backends.len(), 2);

        gov.unregister_backend("draft");
        assert_eq!(gov.backends.len(), 1);
    }

    #[test]
    fn transition_with_backends_records_actions() {
        let mut gov = ResourceGovernor::new();
        gov.register_backend("foreground");
        gov.register_backend("draft");

        let transition = gov.evaluate(HardwareMetrics::new().with_cpu_temp(90.0));
        assert!(transition.is_some());
        let t = transition.unwrap();
        assert!(!t.actions_taken.is_empty());
        // ECO mode stops foreground and draft
        assert!(t.actions_taken.iter().any(|a| a.contains("foreground")));
        assert!(t.actions_taken.iter().any(|a| a.contains("draft")));
    }

    #[test]
    fn status_returns_json() {
        let mut gov = ResourceGovernor::new();
        gov.register_backend("small");
        let status = gov.status();
        assert_eq!(status["mode"], "normal");
        assert!(status["enabled"].as_bool().is_some());
        assert!(status["profile"]["max_ctx"].as_u64().is_some());
        assert!(status["transition_count"].as_u64().is_some());
    }

    #[test]
    fn last_metrics_stored_after_evaluate() {
        let mut gov = ResourceGovernor::new();
        let metrics = HardwareMetrics::new().with_cpu_temp(72.0).with_memory(0.6);
        gov.evaluate(metrics);
        let stored = gov.last_metrics();
        assert_eq!(stored.cpu_temp, Some(72.0));
        assert_eq!(stored.memory_pressure, Some(0.6));
    }

    #[test]
    fn transition_history_bounded() {
        let mut gov = ResourceGovernor::new();
        // Generate 150 transitions
        for i in 0..150 {
            let temp = if i % 2 == 0 { 90.0 } else { 40.0 };
            let mem = if i % 2 == 0 { 0.9 } else { 0.3 };
            gov.evaluate(HardwareMetrics::new().with_cpu_temp(temp).with_memory(mem));
        }
        // Should be bounded (drained at 100 to 50)
        assert!(gov.transition_count() <= 100);
    }

    #[test]
    fn partial_metrics_still_classify() {
        let mut gov = ResourceGovernor::new();
        // Only temp available, comfortable
        let metrics = HardwareMetrics::new().with_cpu_temp(50.0);
        let transition = gov.evaluate(metrics);
        // temp < 60, no mem data → can't confirm Performance (mem_ok is true via None)
        // Actually: temp_ok = true (50 < 60), mem_ok = true (None → is_none_or)
        assert!(transition.is_some());
        assert_eq!(transition.unwrap().to_mode, GovernorMode::Performance);
    }

    #[test]
    fn partial_metrics_temp_only_moderate() {
        let mut gov = ResourceGovernor::new();
        // First go to Performance
        gov.evaluate(HardwareMetrics::new().with_cpu_temp(40.0).with_memory(0.3));
        assert_eq!(gov.mode(), GovernorMode::Performance);

        // Only temp, moderate → Normal
        let metrics = HardwareMetrics::new().with_cpu_temp(68.0);
        let transition = gov.evaluate(metrics);
        assert!(transition.is_some());
        assert_eq!(transition.unwrap().to_mode, GovernorMode::Normal);
    }

    #[test]
    fn set_enabled_toggles() {
        let mut gov = ResourceGovernor::new();
        assert!(gov.enabled());
        gov.set_enabled(false);
        assert!(!gov.enabled());
        gov.set_enabled(true);
        assert!(gov.enabled());
    }

    #[test]
    fn transitions_returns_full_history() {
        let mut gov = ResourceGovernor::new();
        gov.evaluate(HardwareMetrics::new().with_cpu_temp(90.0));
        gov.evaluate(HardwareMetrics::new().with_cpu_temp(40.0).with_memory(0.3));
        let history = gov.transitions();
        assert_eq!(history.len(), 2);
        assert_eq!(history[0].to_mode, GovernorMode::Eco);
        assert_eq!(history[1].to_mode, GovernorMode::Performance);
    }
}
