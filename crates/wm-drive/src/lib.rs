//! wm-drive — Emotion & Drive Core for WhiteMagic v4 (Phase R7).
//!
//! Intrinsic motivation signals that bias exploration and tool selection.
//!
//! Drives:
//! - **Curiosity**: novelty-seeking, exploration bias
//! - **Satisfaction**: reward from successful tool execution
//! - **Caution**: risk aversion from errors and low confidence
//! - **Energy**: resource availability (CPU, memory headroom)
//! - **Social**: cooperation and communication tendency
//!
//! Drives are updated by events (tool success, novel input, errors) and
//! decay over time toward baseline levels. They can bias tool selection
//! by weighting exploration vs conservative tools.

#![forbid(unsafe_code)]
#![allow(clippy::significant_drop_tightening)]

pub mod bias;
pub mod cross_pollination;
pub mod drive;
pub mod event;

pub use bias::{BiasConfig, DriveBias, ToolBias};
pub use cross_pollination::{CascadeRule, CrossPollinationMatrix, ResonanceEvent};
pub use drive::{BASELINE, Baseline, DriveConfig, DriveState};
pub use event::{DriveEvent, DriveEventKind, DriveEventSource};

/// The core emotion & drive engine.
///
/// Maintains drive state, processes events that update drives,
/// and provides bias signals for tool selection.
pub struct DriveCore {
    state: DriveState,
    config: DriveConfig,
    event_count: u64,
}

impl DriveCore {
    /// Create a new drive core with default configuration.
    #[must_use]
    pub fn new() -> Self {
        Self {
            state: DriveState::default(),
            config: DriveConfig::default(),
            event_count: 0,
        }
    }

    /// Create a new drive core with custom configuration.
    #[must_use]
    #[allow(clippy::missing_const_for_fn)]
    pub fn with_config(config: DriveConfig) -> Self {
        Self {
            state: DriveState::with_baseline(config.baseline),
            config,
            event_count: 0,
        }
    }

    /// Process a drive event, updating drive state accordingly.
    pub fn process_event(&mut self, event: &DriveEvent) {
        self.event_count += 1;

        match event.kind {
            DriveEventKind::ToolSuccess => {
                self.state.satisfaction =
                    (self.state.satisfaction + self.config.success_boost).min(1.0);
                self.state.curiosity =
                    (self.state.curiosity + self.config.success_curiosity_boost).min(1.0);
            }
            DriveEventKind::ToolError => {
                self.state.satisfaction =
                    (self.state.satisfaction - self.config.error_penalty).max(0.0);
                self.state.caution =
                    (self.state.caution + self.config.error_caution_boost).min(1.0);
            }
            DriveEventKind::NovelInput => {
                self.state.curiosity = (self.state.curiosity + self.config.novelty_boost).min(1.0);
            }
            DriveEventKind::LowConfidence => {
                self.state.caution =
                    (self.state.caution + self.config.low_confidence_caution).min(1.0);
            }
            DriveEventKind::HighConfidence => {
                self.state.caution =
                    (self.state.caution - self.config.high_confidence_relief).max(0.0);
            }
            DriveEventKind::ResourcePressure => {
                self.state.energy = (self.state.energy - self.config.resource_drain).max(0.0);
            }
            DriveEventKind::ResourceRelief => {
                self.state.energy = (self.state.energy + self.config.resource_recover).min(1.0);
            }
            DriveEventKind::SocialInteraction => {
                self.state.social = (self.state.social + self.config.social_boost).min(1.0);
            }
            DriveEventKind::Decay => {
                self.decay();
            }
        }
    }

    /// Apply time-based decay — all drives move toward baseline.
    pub fn decay(&mut self) {
        let rate = self.config.decay_rate;
        self.state.curiosity =
            decay_toward(self.state.curiosity, self.config.baseline.curiosity, rate);
        self.state.satisfaction = decay_toward(
            self.state.satisfaction,
            self.config.baseline.satisfaction,
            rate,
        );
        self.state.caution = decay_toward(self.state.caution, self.config.baseline.caution, rate);
        self.state.energy = decay_toward(self.state.energy, self.config.baseline.energy, rate);
        self.state.social = decay_toward(self.state.social, self.config.baseline.social, rate);
    }

    /// Get the current drive state.
    #[must_use]
    pub const fn state(&self) -> &DriveState {
        &self.state
    }

    /// Get the drive configuration.
    #[must_use]
    pub const fn config(&self) -> &DriveConfig {
        &self.config
    }

    /// Get total event count.
    #[must_use]
    pub const fn event_count(&self) -> u64 {
        self.event_count
    }

    /// Compute a tool selection bias based on current drives.
    #[must_use]
    pub fn bias(&self) -> DriveBias {
        DriveBias::from_state(&self.state)
    }

    /// Get a snapshot of the drive state as JSON.
    #[must_use]
    pub fn snapshot(&self) -> serde_json::Value {
        serde_json::json!({
            "drives": {
                "curiosity": self.state.curiosity,
                "satisfaction": self.state.satisfaction,
                "caution": self.state.caution,
                "energy": self.state.energy,
                "social": self.state.social,
            },
            "event_count": self.event_count,
            "config": {
                "decay_rate": self.config.decay_rate,
                "baseline": {
                    "curiosity": self.config.baseline.curiosity,
                    "satisfaction": self.config.baseline.satisfaction,
                    "caution": self.config.baseline.caution,
                    "energy": self.config.baseline.energy,
                    "social": self.config.baseline.social,
                },
            },
        })
    }
}

impl Default for DriveCore {
    fn default() -> Self {
        Self::new()
    }
}

/// Decay a value toward a target by a given rate.
fn decay_toward(current: f32, target: f32, rate: f32) -> f32 {
    if current > target {
        (current - rate).max(target)
    } else {
        (current + rate).min(target)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn drive_core_default_state() {
        let core = DriveCore::new();
        let state = core.state();
        // Default baselines
        assert!((state.curiosity - 0.5).abs() < 0.01);
        assert!((state.satisfaction - 0.5).abs() < 0.01);
        assert!((state.caution - 0.3).abs() < 0.01);
        assert!((state.energy - 0.8).abs() < 0.01);
        assert!((state.social - 0.4).abs() < 0.01);
    }

    #[test]
    fn tool_success_increases_satisfaction() {
        let mut core = DriveCore::new();
        let initial = core.state().satisfaction;
        core.process_event(&DriveEvent::new(DriveEventKind::ToolSuccess));
        assert!(core.state().satisfaction > initial);
    }

    #[test]
    fn tool_error_decreases_satisfaction() {
        let mut core = DriveCore::new();
        let initial = core.state().satisfaction;
        core.process_event(&DriveEvent::new(DriveEventKind::ToolError));
        assert!(core.state().satisfaction < initial);
    }

    #[test]
    fn tool_error_increases_caution() {
        let mut core = DriveCore::new();
        let initial = core.state().caution;
        core.process_event(&DriveEvent::new(DriveEventKind::ToolError));
        assert!(core.state().caution > initial);
    }

    #[test]
    fn novel_input_increases_curiosity() {
        let mut core = DriveCore::new();
        let initial = core.state().curiosity;
        core.process_event(&DriveEvent::new(DriveEventKind::NovelInput));
        assert!(core.state().curiosity > initial);
    }

    #[test]
    fn decay_moves_toward_baseline() {
        let mut core = DriveCore::new();
        // Boost curiosity above baseline
        for _ in 0..5 {
            core.process_event(&DriveEvent::new(DriveEventKind::NovelInput));
        }
        let boosted = core.state().curiosity;
        assert!(boosted > 0.5);
        // Decay
        core.decay();
        assert!(core.state().curiosity < boosted);
    }

    #[test]
    fn resource_pressure_decreases_energy() {
        let mut core = DriveCore::new();
        let initial = core.state().energy;
        core.process_event(&DriveEvent::new(DriveEventKind::ResourcePressure));
        assert!(core.state().energy < initial);
    }

    #[test]
    fn resource_relief_increases_energy() {
        let mut core = DriveCore::new();
        // First drain energy
        core.process_event(&DriveEvent::new(DriveEventKind::ResourcePressure));
        let drained = core.state().energy;
        core.process_event(&DriveEvent::new(DriveEventKind::ResourceRelief));
        assert!(core.state().energy > drained);
    }

    #[test]
    fn social_interaction_increases_social() {
        let mut core = DriveCore::new();
        let initial = core.state().social;
        core.process_event(&DriveEvent::new(DriveEventKind::SocialInteraction));
        assert!(core.state().social > initial);
    }

    #[test]
    fn low_confidence_increases_caution() {
        let mut core = DriveCore::new();
        let initial = core.state().caution;
        core.process_event(&DriveEvent::new(DriveEventKind::LowConfidence));
        assert!(core.state().caution > initial);
    }

    #[test]
    fn high_confidence_decreases_caution() {
        let mut core = DriveCore::new();
        // First increase caution
        core.process_event(&DriveEvent::new(DriveEventKind::LowConfidence));
        let increased = core.state().caution;
        core.process_event(&DriveEvent::new(DriveEventKind::HighConfidence));
        assert!(core.state().caution < increased);
    }

    #[test]
    fn drive_snapshot_returns_json() {
        let core = DriveCore::new();
        let snap = core.snapshot();
        assert!(snap["drives"]["curiosity"].as_f64().is_some());
        assert!(snap["event_count"].as_u64().is_some());
    }

    #[test]
    fn drive_bias_reflects_state() {
        let mut core = DriveCore::new();
        // High curiosity → exploration bias
        for _ in 0..5 {
            core.process_event(&DriveEvent::new(DriveEventKind::NovelInput));
        }
        let bias = core.bias();
        assert!(bias.exploration_weight > 0.5);
    }

    #[test]
    fn event_count_tracks() {
        let mut core = DriveCore::new();
        assert_eq!(core.event_count(), 0);
        core.process_event(&DriveEvent::new(DriveEventKind::ToolSuccess));
        core.process_event(&DriveEvent::new(DriveEventKind::ToolError));
        assert_eq!(core.event_count(), 2);
    }

    #[test]
    fn drives_clamp_to_0_1() {
        let mut core = DriveCore::new();
        // Many successes should not exceed 1.0
        for _ in 0..20 {
            core.process_event(&DriveEvent::new(DriveEventKind::ToolSuccess));
        }
        assert!(core.state().satisfaction <= 1.0);
        // Many errors should not go below 0.0
        for _ in 0..20 {
            core.process_event(&DriveEvent::new(DriveEventKind::ToolError));
        }
        assert!(core.state().satisfaction >= 0.0);
    }
}
