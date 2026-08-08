//! Tier definitions and configuration.

use serde::{Deserialize, Serialize};
use std::time::Duration;
use wm_core::BrainWave;

/// Total number of timescale tiers.
pub const TIER_COUNT: usize = 5;

/// A timescale tier identifier (0–4).
///
/// - Tier 0: Reflex (100µs–10ms)
/// - Tier 1: Reactive (10ms–1s)
/// - Tier 2: Planning (1s–30s)
/// - Tier 3: Consolidation (30s–1hr)
/// - Tier 4: Evolutionary (1hr+)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum Tier {
    /// Reflex — sensor polling, motor commands, safety checks.
    Reflex = 0,
    /// Reactive — tool dispatch, memory reads, NLU routing.
    Reactive = 1,
    /// Planning — multi-step plans, bicameral reasoning, dream phases.
    Planning = 2,
    /// Consolidation — memory consolidation, forgetting, meta-learning.
    Consolidation = 3,
    /// Evolutionary — apotheosis, architecture review, value drift detection.
    Evolutionary = 4,
}

impl Tier {
    /// Convert from u8 index.
    #[must_use]
    pub const fn from_index(idx: u8) -> Option<Self> {
        match idx {
            0 => Some(Self::Reflex),
            1 => Some(Self::Reactive),
            2 => Some(Self::Planning),
            3 => Some(Self::Consolidation),
            4 => Some(Self::Evolutionary),
            _ => None,
        }
    }

    /// Convert to u8 index.
    #[must_use]
    pub const fn index(self) -> u8 {
        self as u8
    }

    /// Human-readable name.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Reflex => "Reflex",
            Self::Reactive => "Reactive",
            Self::Planning => "Planning",
            Self::Consolidation => "Consolidation",
            Self::Evolutionary => "Evolutionary",
        }
    }

    /// All tiers in order.
    #[must_use]
    pub const fn all() -> [Self; TIER_COUNT] {
        [
            Self::Reflex,
            Self::Reactive,
            Self::Planning,
            Self::Consolidation,
            Self::Evolutionary,
        ]
    }
}

impl std::fmt::Display for Tier {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.name())
    }
}

/// Configuration for a single timescale tier.
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct TierConfig {
    /// Interval between tick executions.
    pub interval: Duration,
    /// Maximum time budget per tick. If exceeded, the hook is killed
    /// and the fallback fires.
    pub budget: Duration,
    /// Whether this tier is active in Gamma brain-wave state.
    pub active_in_gamma: bool,
    /// Whether this tier is active in Beta brain-wave state.
    pub active_in_beta: bool,
    /// Whether this tier is active in Alpha brain-wave state.
    pub active_in_alpha: bool,
    /// Whether this tier is active in Theta brain-wave state.
    pub active_in_theta: bool,
    /// Whether this tier is active in Delta brain-wave state.
    pub active_in_delta: bool,
}

impl TierConfig {
    /// Check if this tier is active in the given brain-wave state.
    #[must_use]
    pub const fn is_active_in(self, brain_wave: BrainWave) -> bool {
        match brain_wave {
            BrainWave::Gamma => self.active_in_gamma,
            BrainWave::Beta => self.active_in_beta,
            BrainWave::Alpha => self.active_in_alpha,
            BrainWave::Theta => self.active_in_theta,
            BrainWave::Delta => self.active_in_delta,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tier_count_is_5() {
        assert_eq!(TIER_COUNT, 5);
        assert_eq!(Tier::all().len(), 5);
    }

    #[test]
    fn tier_from_index_roundtrip() {
        for i in 0..5 {
            let tier = Tier::from_index(i).unwrap();
            assert_eq!(tier.index(), i);
        }
        assert!(Tier::from_index(5).is_none());
    }

    #[test]
    fn tier_names() {
        assert_eq!(Tier::Reflex.name(), "Reflex");
        assert_eq!(Tier::Reactive.name(), "Reactive");
        assert_eq!(Tier::Planning.name(), "Planning");
        assert_eq!(Tier::Consolidation.name(), "Consolidation");
        assert_eq!(Tier::Evolutionary.name(), "Evolutionary");
    }

    #[test]
    fn tier_config_active_in_gamma() {
        let config = TierConfig {
            interval: Duration::from_millis(1),
            budget: Duration::from_millis(10),
            active_in_gamma: true,
            active_in_beta: false,
            active_in_alpha: false,
            active_in_theta: false,
            active_in_delta: false,
        };
        assert!(config.is_active_in(BrainWave::Gamma));
        assert!(!config.is_active_in(BrainWave::Beta));
        assert!(!config.is_active_in(BrainWave::Delta));
    }

    #[test]
    fn tier_config_active_in_delta() {
        let config = TierConfig {
            interval: Duration::from_secs(3600),
            budget: Duration::from_secs(3600),
            active_in_gamma: true,
            active_in_beta: true,
            active_in_alpha: true,
            active_in_theta: true,
            active_in_delta: true,
        };
        assert!(config.is_active_in(BrainWave::Delta));
        assert!(config.is_active_in(BrainWave::Gamma));
    }

    #[test]
    fn defaults_all_tiers_cover_all_states() {
        // Tier 4 should be active in all states including Delta
        assert!(crate::timescale::defaults::TIER_4.is_active_in(BrainWave::Delta));
        assert!(crate::timescale::defaults::TIER_4.is_active_in(BrainWave::Gamma));
    }

    #[test]
    fn defaults_tier_0_reflex_timing() {
        assert!(crate::timescale::defaults::TIER_0.interval <= Duration::from_millis(10));
        assert!(crate::timescale::defaults::TIER_0.budget <= Duration::from_millis(10));
    }

    #[test]
    fn defaults_tier_4_evolutionary_timing() {
        assert!(crate::timescale::defaults::TIER_4.interval >= Duration::from_secs(3600));
    }
}
