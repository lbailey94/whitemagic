//! Multi-Timescale Event Bus — 5-tier hierarchical control loops.

pub mod bus;
pub mod hooks;
pub mod tier;

pub use bus::{TimescaleBus, TimescaleError};
pub use hooks::{Hook, HookId, HookResult, HookStats};
pub use tier::{TIER_COUNT, Tier, TierConfig};

/// Default configurations for all tiers.
pub mod defaults {
    use super::tier::TierConfig;
    use std::time::Duration;

    pub const TIER_0: TierConfig = TierConfig {
        interval: Duration::from_millis(1),
        budget: Duration::from_millis(10),
        active_in_gamma: true,
        active_in_beta: false,
        active_in_alpha: false,
        active_in_theta: false,
        active_in_delta: false,
    };

    pub const TIER_1: TierConfig = TierConfig {
        interval: Duration::from_millis(100),
        budget: Duration::from_secs(1),
        active_in_gamma: true,
        active_in_beta: true,
        active_in_alpha: false,
        active_in_theta: false,
        active_in_delta: false,
    };

    pub const TIER_2: TierConfig = TierConfig {
        interval: Duration::from_secs(5),
        budget: Duration::from_secs(30),
        active_in_gamma: true,
        active_in_beta: true,
        active_in_alpha: true,
        active_in_theta: false,
        active_in_delta: false,
    };

    pub const TIER_3: TierConfig = TierConfig {
        interval: Duration::from_secs(60),
        budget: Duration::from_secs(3600),
        active_in_gamma: true,
        active_in_beta: true,
        active_in_alpha: true,
        active_in_theta: true,
        active_in_delta: false,
    };

    pub const TIER_4: TierConfig = TierConfig {
        interval: Duration::from_secs(3600),
        budget: Duration::from_secs(3600),
        active_in_gamma: true,
        active_in_beta: true,
        active_in_alpha: true,
        active_in_theta: true,
        active_in_delta: true,
    };

    pub const ALL_TIERS: [TierConfig; 5] = [TIER_0, TIER_1, TIER_2, TIER_3, TIER_4];
}
