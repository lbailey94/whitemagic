//! WhiteMagic v4 Multi-Timescale Event Bus — 5-tier hierarchical control loops.
//!
//! Each tier runs as a tokio task with `tokio::time::timeout` budget enforcement.
//! Hooks are registered per-tier and executed within the tier's time budget.
//! If a hook exceeds its budget, it's killed and a fallback fires.
//!
//! Tier activation is gated by brain-wave state:
//! - Gamma: all tiers active
//! - Beta: tiers 1–4 active, tier 0 on-demand
//! - Alpha: tiers 1–3 active
//! - Theta: tier 3 active (consolidation only)
//! - Delta: tier 4 heartbeat only (1hr interval)

#![forbid(unsafe_code)]

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

    /// Default config for tier 0 (Reflex): 1ms interval, 10ms budget.
    pub const TIER_0: TierConfig = TierConfig {
        interval: Duration::from_millis(1),
        budget: Duration::from_millis(10),
        active_in_gamma: true,
        active_in_beta: false,
        active_in_alpha: false,
        active_in_theta: false,
        active_in_delta: false,
    };

    /// Default config for tier 1 (Reactive): 100ms interval, 1s budget.
    pub const TIER_1: TierConfig = TierConfig {
        interval: Duration::from_millis(100),
        budget: Duration::from_secs(1),
        active_in_gamma: true,
        active_in_beta: true,
        active_in_alpha: false,
        active_in_theta: false,
        active_in_delta: false,
    };

    /// Default config for tier 2 (Planning): 5s interval, 30s budget.
    pub const TIER_2: TierConfig = TierConfig {
        interval: Duration::from_secs(5),
        budget: Duration::from_secs(30),
        active_in_gamma: true,
        active_in_beta: true,
        active_in_alpha: true,
        active_in_theta: false,
        active_in_delta: false,
    };

    /// Default config for tier 3 (Consolidation): 60s interval, 1hr budget.
    pub const TIER_3: TierConfig = TierConfig {
        interval: Duration::from_secs(60),
        budget: Duration::from_secs(3600),
        active_in_gamma: true,
        active_in_beta: true,
        active_in_alpha: true,
        active_in_theta: true,
        active_in_delta: false,
    };

    /// Default config for tier 4 (Evolutionary): 1hr interval, no budget limit.
    pub const TIER_4: TierConfig = TierConfig {
        interval: Duration::from_secs(3600),
        budget: Duration::from_secs(3600),
        active_in_gamma: true,
        active_in_beta: true,
        active_in_alpha: true,
        active_in_theta: true,
        active_in_delta: true,
    };

    /// All default tier configs in order.
    pub const ALL_TIERS: [TierConfig; 5] = [TIER_0, TIER_1, TIER_2, TIER_3, TIER_4];
}
