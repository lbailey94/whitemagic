//! Drive state — the five intrinsic motivation signals.

use serde::{Deserialize, Serialize};

/// The five drive kinds.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum DriveKind {
    /// Novelty-seeking, exploration bias.
    Curiosity,
    /// Reward from successful operations.
    Satisfaction,
    /// Risk aversion from errors and uncertainty.
    Caution,
    /// Resource availability (CPU, memory headroom).
    Energy,
    /// Cooperation and communication tendency.
    Social,
}

/// Baseline drive levels — the resting state drives decay toward.
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct Baseline {
    /// Baseline curiosity (default: 0.5).
    pub curiosity: f32,
    /// Baseline satisfaction (default: 0.5).
    pub satisfaction: f32,
    /// Baseline caution (default: 0.3).
    pub caution: f32,
    /// Baseline energy (default: 0.8).
    pub energy: f32,
    /// Baseline social (default: 0.4).
    pub social: f32,
}

impl Default for Baseline {
    fn default() -> Self {
        BASELINE
    }
}

/// Default baseline drive levels.
pub const BASELINE: Baseline = Baseline {
    curiosity: 0.5,
    satisfaction: 0.5,
    caution: 0.3,
    energy: 0.8,
    social: 0.4,
};

/// Current state of all five drives. Each value is in [0.0, 1.0].
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct DriveState {
    /// Curiosity drive (0.0 = no interest, 1.0 = highly curious).
    pub curiosity: f32,
    /// Satisfaction drive (0.0 = frustrated, 1.0 = very satisfied).
    pub satisfaction: f32,
    /// Caution drive (0.0 = reckless, 1.0 = very cautious).
    pub caution: f32,
    /// Energy drive (0.0 = depleted, 1.0 = full energy).
    pub energy: f32,
    /// Social drive (0.0 = solitary, 1.0 = highly social).
    pub social: f32,
}

impl Default for DriveState {
    fn default() -> Self {
        Self::with_baseline(BASELINE)
    }
}

impl DriveState {
    /// Create a drive state initialized at the given baseline.
    #[must_use]
    pub const fn with_baseline(baseline: Baseline) -> Self {
        Self {
            curiosity: baseline.curiosity,
            satisfaction: baseline.satisfaction,
            caution: baseline.caution,
            energy: baseline.energy,
            social: baseline.social,
        }
    }

    /// Get a drive value by kind.
    #[must_use]
    pub const fn get(&self, kind: DriveKind) -> f32 {
        match kind {
            DriveKind::Curiosity => self.curiosity,
            DriveKind::Satisfaction => self.satisfaction,
            DriveKind::Caution => self.caution,
            DriveKind::Energy => self.energy,
            DriveKind::Social => self.social,
        }
    }

    /// Get the dominant drive — the one with the highest value.
    #[must_use]
    pub fn dominant(&self) -> DriveKind {
        let mut max_kind = DriveKind::Curiosity;
        let mut max_val = self.curiosity;
        if self.satisfaction > max_val {
            max_val = self.satisfaction;
            max_kind = DriveKind::Satisfaction;
        }
        if self.caution > max_val {
            max_val = self.caution;
            max_kind = DriveKind::Caution;
        }
        if self.energy > max_val {
            max_val = self.energy;
            max_kind = DriveKind::Energy;
        }
        if self.social > max_val {
            max_kind = DriveKind::Social;
        }
        max_kind
    }
}

/// Configuration for drive dynamics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DriveConfig {
    /// How fast drives decay toward baseline per decay tick.
    pub decay_rate: f32,
    /// Baseline drive levels.
    pub baseline: Baseline,
    /// Satisfaction boost from tool success.
    pub success_boost: f32,
    /// Curiosity boost from tool success (exploring more after success).
    pub success_curiosity_boost: f32,
    /// Satisfaction penalty from tool error.
    pub error_penalty: f32,
    /// Caution boost from tool error.
    pub error_caution_boost: f32,
    /// Curiosity boost from novel input.
    pub novelty_boost: f32,
    /// Caution boost from low self-model confidence.
    pub low_confidence_caution: f32,
    /// Caution relief from high self-model confidence.
    pub high_confidence_relief: f32,
    /// Energy drain from resource pressure.
    pub resource_drain: f32,
    /// Energy recovery from resource relief.
    pub resource_recover: f32,
    /// Social boost from social interaction.
    pub social_boost: f32,
}

impl Default for DriveConfig {
    fn default() -> Self {
        Self {
            decay_rate: 0.01,
            baseline: BASELINE,
            success_boost: 0.05,
            success_curiosity_boost: 0.02,
            error_penalty: 0.08,
            error_caution_boost: 0.1,
            novelty_boost: 0.1,
            low_confidence_caution: 0.08,
            high_confidence_relief: 0.05,
            resource_drain: 0.1,
            resource_recover: 0.05,
            social_boost: 0.05,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn drive_state_default_matches_baseline() {
        let state = DriveState::default();
        assert!((state.curiosity - BASELINE.curiosity).abs() < 0.001);
        assert!((state.energy - BASELINE.energy).abs() < 0.001);
    }

    #[test]
    fn drive_state_get_by_kind() {
        let state = DriveState {
            curiosity: 0.7,
            satisfaction: 0.3,
            caution: 0.5,
            energy: 0.9,
            social: 0.2,
        };
        assert!((state.get(DriveKind::Curiosity) - 0.7).abs() < 0.001);
        assert!((state.get(DriveKind::Satisfaction) - 0.3).abs() < 0.001);
        assert!((state.get(DriveKind::Caution) - 0.5).abs() < 0.001);
        assert!((state.get(DriveKind::Energy) - 0.9).abs() < 0.001);
        assert!((state.get(DriveKind::Social) - 0.2).abs() < 0.001);
    }

    #[test]
    fn drive_state_dominant() {
        let state = DriveState {
            curiosity: 0.3,
            satisfaction: 0.4,
            caution: 0.5,
            energy: 0.9,
            social: 0.2,
        };
        assert_eq!(state.dominant(), DriveKind::Energy);
    }

    #[test]
    fn drive_config_default() {
        let config = DriveConfig::default();
        assert!(config.decay_rate > 0.0);
        assert!(config.success_boost > 0.0);
        assert!(config.error_penalty > 0.0);
    }
}
