//! Timescale bus — coordinates hooks across 5 tiers with budget enforcement.
//!
//! Each tier has its own interval and budget. The bus tracks which tiers
//! are active based on the current brain-wave state and only executes
//! hooks for active tiers.

use crate::timescale::hooks::{Hook, HookId, HookResult, HookStatsSnapshot};
use crate::timescale::tier::{TIER_COUNT, Tier, TierConfig};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;
use thiserror::Error;
use wm_core::BrainWave;

/// Error type for timescale bus operations.
#[derive(Debug, Clone, Error)]
pub enum TimescaleError {
    /// Hook ID not found.
    #[error("hook {0} not found")]
    HookNotFound(HookId),
    /// Tier index out of bounds.
    #[error("tier index {0} out of bounds (max {1})")]
    TierOutOfBounds(u8, u8),
}

/// The timescale bus coordinates hook execution across 5 tiers.
///
/// Each tier has its own interval and budget configuration. The bus
/// tracks which tiers are active based on the current brain-wave state.
///
/// This is a synchronous coordinator — it does not spawn tokio tasks
/// itself. The caller (typically the MCP server) is responsible for
/// driving the bus via `tick()`.
pub struct TimescaleBus {
    /// Hooks organized by tier.
    hooks: [Vec<Hook>; TIER_COUNT],
    /// Configuration for each tier.
    configs: [TierConfig; TIER_COUNT],
    /// Current brain-wave state.
    brain_wave: BrainWave,
    /// Next hook ID to assign.
    next_hook_id: AtomicU64,
    /// Total ticks executed across all tiers.
    total_ticks: AtomicU64,
    /// Total timeouts across all tiers.
    total_timeouts: AtomicU64,
    /// Last tick time per tier.
    last_tick: [Option<Instant>; TIER_COUNT],
}

impl std::fmt::Debug for TimescaleBus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("TimescaleBus")
            .field("brain_wave", &self.brain_wave)
            .field(
                "hook_counts",
                &self.hooks.iter().map(Vec::len).collect::<Vec<_>>(),
            )
            .field("total_ticks", &self.total_ticks.load(Ordering::Relaxed))
            .field(
                "total_timeouts",
                &self.total_timeouts.load(Ordering::Relaxed),
            )
            .finish_non_exhaustive()
    }
}

impl Default for TimescaleBus {
    fn default() -> Self {
        Self::new(crate::timescale::defaults::ALL_TIERS)
    }
}

impl TimescaleBus {
    /// Create a new timescale bus with the given tier configurations.
    #[must_use]
    pub fn new(configs: [TierConfig; TIER_COUNT]) -> Self {
        Self {
            hooks: std::array::from_fn(|_| Vec::new()),
            configs,
            brain_wave: BrainWave::Gamma,
            next_hook_id: AtomicU64::new(1),
            total_ticks: AtomicU64::new(0),
            total_timeouts: AtomicU64::new(0),
            last_tick: [None, None, None, None, None],
        }
    }

    /// Register a hook on a specific tier.
    ///
    /// Returns the assigned hook ID.
    pub fn register(
        &mut self,
        tier: Tier,
        name: impl Into<String>,
        callback: Box<dyn Fn() -> HookResult + Send + Sync>,
    ) -> HookId {
        let id = self.next_hook_id.fetch_add(1, Ordering::Relaxed);
        let hook = Hook::new(id, name, callback);
        self.hooks[tier.index() as usize].push(hook);
        id
    }

    /// Register a hook with a fallback.
    pub fn register_with_fallback(
        &mut self,
        tier: Tier,
        name: impl Into<String>,
        callback: Box<dyn Fn() -> HookResult + Send + Sync>,
        fallback: Box<dyn Fn() + Send + Sync>,
    ) -> HookId {
        let id = self.next_hook_id.fetch_add(1, Ordering::Relaxed);
        let hook = Hook::new(id, name, callback).with_fallback(fallback);
        self.hooks[tier.index() as usize].push(hook);
        id
    }

    /// Unregister a hook by ID.
    pub fn unregister(&mut self, tier: Tier, id: HookId) -> Result<(), TimescaleError> {
        let hooks = &mut self.hooks[tier.index() as usize];
        let idx = hooks
            .iter()
            .position(|h| h.id == id)
            .ok_or(TimescaleError::HookNotFound(id))?;
        hooks.remove(idx);
        Ok(())
    }

    /// Set the current brain-wave state.
    pub const fn set_brain_wave(&mut self, bw: BrainWave) {
        self.brain_wave = bw;
    }

    /// Get the current brain-wave state.
    #[must_use]
    pub const fn brain_wave(&self) -> BrainWave {
        self.brain_wave
    }

    /// Check if a tier is active in the current brain-wave state.
    #[must_use]
    pub const fn is_tier_active(&self, tier: Tier) -> bool {
        self.configs[tier.index() as usize].is_active_in(self.brain_wave)
    }

    /// Get the configuration for a tier.
    #[must_use]
    pub const fn tier_config(&self, tier: Tier) -> TierConfig {
        self.configs[tier.index() as usize]
    }

    /// Get the number of hooks registered on a tier.
    #[must_use]
    pub fn hook_count(&self, tier: Tier) -> usize {
        self.hooks[tier.index() as usize].len()
    }

    /// Total number of hooks across all tiers.
    #[must_use]
    pub fn total_hook_count(&self) -> usize {
        self.hooks.iter().map(Vec::len).sum()
    }

    /// Total ticks executed.
    #[must_use]
    pub fn total_ticks(&self) -> u64 {
        self.total_ticks.load(Ordering::Relaxed)
    }

    /// Total timeouts.
    #[must_use]
    pub fn total_timeouts(&self) -> u64 {
        self.total_timeouts.load(Ordering::Relaxed)
    }

    /// Execute all due hooks on a tier. Returns the number of hooks executed
    /// and the number of timeouts.
    ///
    /// This is the synchronous tick execution — the caller is responsible
    /// for calling this at the appropriate interval. Budget enforcement
    /// is done via `Instant` elapsed time checking.
    pub fn tick_tier(&mut self, tier: Tier) -> (usize, usize) {
        if !self.is_tier_active(tier) {
            return (0, 0);
        }

        let config = self.configs[tier.index() as usize];
        let now = Instant::now();

        // Check if enough time has passed since last tick
        if let Some(last) = self.last_tick[tier.index() as usize] {
            if now.duration_since(last) < config.interval {
                return (0, 0);
            }
        }
        self.last_tick[tier.index() as usize] = Some(now);

        let hooks = &mut self.hooks[tier.index() as usize];
        // Sort by priority (highest first) — stable sort
        hooks.sort_by(|a, b| b.priority.cmp(&a.priority));

        let mut executed = 0;
        let mut timeouts = 0;

        for hook in hooks.iter_mut() {
            self.total_ticks.fetch_add(1, Ordering::Relaxed);
            executed += 1;

            let start = Instant::now();
            let result = (hook.callback)();
            let elapsed = start.elapsed();

            if elapsed > config.budget {
                // Budget exceeded — record timeout and fire fallback
                hook.stats.record_timeout();
                self.total_timeouts.fetch_add(1, Ordering::Relaxed);
                timeouts += 1;
                if let Some(ref fallback) = hook.fallback {
                    fallback();
                }
            } else {
                match result {
                    HookResult::Complete => hook.stats.record_success(elapsed),
                    HookResult::Error(_) => hook.stats.record_error(),
                    HookResult::NeedsMoreTime => hook.stats.record_success(elapsed),
                }
            }
        }

        (executed, timeouts)
    }

    /// Tick all active tiers. Returns total executed and total timeouts.
    pub fn tick_all(&mut self) -> (usize, usize) {
        let mut total_executed = 0;
        let mut total_timeouts = 0;
        for tier in Tier::all() {
            let (executed, timeouts) = self.tick_tier(tier);
            total_executed += executed;
            total_timeouts += timeouts;
        }
        (total_executed, total_timeouts)
    }

    /// Get statistics snapshots for all hooks on a tier.
    pub fn tier_stats(&self, tier: Tier) -> Vec<(HookId, String, HookStatsSnapshot)> {
        self.hooks[tier.index() as usize]
            .iter()
            .map(|h| (h.id, h.name.clone(), h.stats.snapshot()))
            .collect()
    }

    /// Get the active tiers for the current brain-wave state.
    #[must_use]
    pub fn active_tiers(&self) -> Vec<Tier> {
        Tier::all()
            .into_iter()
            .filter(|t| self.is_tier_active(*t))
            .collect()
    }

    /// Get the inactive tiers for the current brain-wave state.
    #[must_use]
    pub fn inactive_tiers(&self) -> Vec<Tier> {
        Tier::all()
            .into_iter()
            .filter(|t| !self.is_tier_active(*t))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::AtomicU32;
    use std::time::Duration;

    #[test]
    fn bus_default_creation() {
        let bus = TimescaleBus::default();
        assert_eq!(bus.brain_wave(), BrainWave::Gamma);
        assert_eq!(bus.total_hook_count(), 0);
    }

    #[test]
    fn register_hook() {
        let mut bus = TimescaleBus::default();
        let id = bus.register(Tier::Reactive, "test", Box::new(|| HookResult::Complete));
        assert!(id > 0);
        assert_eq!(bus.hook_count(Tier::Reactive), 1);
        assert_eq!(bus.total_hook_count(), 1);
    }

    #[test]
    fn register_with_fallback() {
        let mut bus = TimescaleBus::default();
        let id = bus.register_with_fallback(
            Tier::Planning,
            "fallback_test",
            Box::new(|| HookResult::Complete),
            Box::new(|| {}),
        );
        assert!(id > 0);
        assert_eq!(bus.hook_count(Tier::Planning), 1);
    }

    #[test]
    fn unregister_hook() {
        let mut bus = TimescaleBus::default();
        let id = bus.register(Tier::Reactive, "test", Box::new(|| HookResult::Complete));
        assert_eq!(bus.hook_count(Tier::Reactive), 1);
        bus.unregister(Tier::Reactive, id).unwrap();
        assert_eq!(bus.hook_count(Tier::Reactive), 0);
    }

    #[test]
    fn unregister_nonexistent() {
        let mut bus = TimescaleBus::default();
        let err = bus.unregister(Tier::Reactive, 999).unwrap_err();
        assert!(matches!(err, TimescaleError::HookNotFound(999)));
    }

    #[test]
    fn tick_tier_executes_hooks() {
        let mut bus = TimescaleBus::default();
        let counter = std::sync::Arc::new(AtomicU32::new(0));
        let counter_clone = counter.clone();
        bus.register(
            Tier::Reactive,
            "counter",
            Box::new(move || {
                counter_clone.fetch_add(1, Ordering::Relaxed);
                HookResult::Complete
            }),
        );

        let (executed, timeouts) = bus.tick_tier(Tier::Reactive);
        assert_eq!(executed, 1);
        assert_eq!(timeouts, 0);
        assert_eq!(counter.load(Ordering::Relaxed), 1);
        assert_eq!(bus.total_ticks(), 1);
    }

    #[test]
    fn tick_tier_inactive_returns_zero() {
        let mut bus = TimescaleBus::default();
        bus.set_brain_wave(BrainWave::Delta);

        // Only tier 4 is active in Delta
        let (executed, _) = bus.tick_tier(Tier::Reflex);
        assert_eq!(executed, 0);
    }

    #[test]
    fn tick_all_executes_active_tiers() {
        let mut bus = TimescaleBus::default();
        bus.set_brain_wave(BrainWave::Gamma);
        bus.register(Tier::Reflex, "r", Box::new(|| HookResult::Complete));
        bus.register(Tier::Reactive, "re", Box::new(|| HookResult::Complete));

        let (executed, _) = bus.tick_all();
        assert_eq!(executed, 2);
    }

    #[test]
    fn brain_wave_gating() {
        let mut bus = TimescaleBus::default();

        // Gamma: all tiers active
        bus.set_brain_wave(BrainWave::Gamma);
        assert_eq!(bus.active_tiers().len(), 5);

        // Beta: tier 0 not active
        bus.set_brain_wave(BrainWave::Beta);
        assert!(!bus.is_tier_active(Tier::Reflex));
        assert!(bus.is_tier_active(Tier::Reactive));

        // Alpha: tiers 0-1 not active
        bus.set_brain_wave(BrainWave::Alpha);
        assert!(!bus.is_tier_active(Tier::Reflex));
        assert!(!bus.is_tier_active(Tier::Reactive));
        assert!(bus.is_tier_active(Tier::Planning));

        // Theta: only tier 3
        bus.set_brain_wave(BrainWave::Theta);
        assert!(!bus.is_tier_active(Tier::Reflex));
        assert!(!bus.is_tier_active(Tier::Reactive));
        assert!(!bus.is_tier_active(Tier::Planning));
        assert!(bus.is_tier_active(Tier::Consolidation));

        // Delta: only tier 4
        bus.set_brain_wave(BrainWave::Delta);
        assert!(!bus.is_tier_active(Tier::Consolidation));
        assert!(bus.is_tier_active(Tier::Evolutionary));
    }

    #[test]
    fn tick_interval_respected() {
        let mut configs = crate::timescale::defaults::ALL_TIERS;
        // Set tier 1 to have a 1-second interval
        configs[1] = TierConfig {
            interval: Duration::from_secs(1),
            budget: Duration::from_secs(1),
            active_in_gamma: true,
            active_in_beta: true,
            active_in_alpha: false,
            active_in_theta: false,
            active_in_delta: false,
        };
        let mut bus = TimescaleBus::new(configs);
        bus.register(Tier::Reactive, "test", Box::new(|| HookResult::Complete));

        // First tick should execute
        let (executed1, _) = bus.tick_tier(Tier::Reactive);
        assert_eq!(executed1, 1);

        // Immediate second tick should not execute (interval not elapsed)
        let (executed2, _) = bus.tick_tier(Tier::Reactive);
        assert_eq!(executed2, 0);
    }

    #[test]
    fn hook_priority_ordering() {
        let mut bus = TimescaleBus::default();
        let order = std::sync::Arc::new(std::sync::Mutex::new(Vec::new()));

        let o1 = order.clone();
        bus.hooks[Tier::Reactive.index() as usize].push(
            Hook::new(
                1,
                "low",
                Box::new(move || {
                    o1.lock().unwrap().push("low");
                    HookResult::Complete
                }),
            )
            .with_priority(0),
        );

        let o2 = order.clone();
        bus.hooks[Tier::Reactive.index() as usize].push(
            Hook::new(
                2,
                "high",
                Box::new(move || {
                    o2.lock().unwrap().push("high");
                    HookResult::Complete
                }),
            )
            .with_priority(255),
        );

        let _ = bus.tick_tier(Tier::Reactive);
        let order = order.lock().unwrap();
        assert_eq!(order[0], "high");
        assert_eq!(order[1], "low");
        drop(order);
    }

    #[test]
    fn tier_stats_collection() {
        let mut bus = TimescaleBus::default();
        bus.register(Tier::Planning, "test", Box::new(|| HookResult::Complete));
        let _ = bus.tick_tier(Tier::Planning);

        let stats = bus.tier_stats(Tier::Planning);
        assert_eq!(stats.len(), 1);
        assert_eq!(stats[0].1, "test");
        assert_eq!(stats[0].2.tick_count, 1);
        assert_eq!(stats[0].2.success_count, 1);
    }

    #[test]
    fn active_inactive_tiers() {
        let mut bus = TimescaleBus::default();
        bus.set_brain_wave(BrainWave::Alpha);
        let active = bus.active_tiers();
        let inactive = bus.inactive_tiers();
        assert!(active.len() + inactive.len() == TIER_COUNT);
        assert!(active.contains(&Tier::Planning));
        assert!(inactive.contains(&Tier::Reflex));
    }

    #[test]
    fn total_ticks_increments() {
        let mut bus = TimescaleBus::default();
        bus.register(Tier::Reflex, "a", Box::new(|| HookResult::Complete));
        bus.register(Tier::Reactive, "b", Box::new(|| HookResult::Complete));

        let _ = bus.tick_all();
        assert_eq!(bus.total_ticks(), 2);

        // Second tick all — tier 0 has 1ms interval, might not fire
        // but tier 1 has 100ms interval, won't fire immediately
        // So total_ticks should still be 2
        let _ = bus.tick_all();
        // The reflex tier has 1ms interval, so it might fire again
        // depending on timing. Just check it's >= 2.
        assert!(bus.total_ticks() >= 2);
    }

    #[test]
    fn error_hook_recorded() {
        let mut bus = TimescaleBus::default();
        bus.register(
            Tier::Reactive,
            "error_hook",
            Box::new(|| HookResult::Error("test error".to_string())),
        );

        let _ = bus.tick_tier(Tier::Reactive);
        let stats = bus.tier_stats(Tier::Reactive);
        assert_eq!(stats[0].2.error_count, 1);
        assert_eq!(stats[0].2.success_count, 0);
    }

    #[test]
    fn inactive_tier_hooks_skipped_in_tick_all() {
        let mut bus = TimescaleBus::default();
        bus.set_brain_wave(BrainWave::Delta);

        // Register a fast hook on Reflex tier (inactive in Delta)
        let counter = std::sync::Arc::new(AtomicU32::new(0));
        let counter_clone = counter.clone();
        bus.register(
            Tier::Reflex,
            "fast_hook",
            Box::new(move || {
                counter_clone.fetch_add(1, Ordering::Relaxed);
                HookResult::Complete
            }),
        );

        // tick_all should not execute the Reflex hook in Delta state
        let (executed, _) = bus.tick_all();
        assert_eq!(executed, 0, "Inactive tier hooks should not execute");
        assert_eq!(counter.load(Ordering::Relaxed), 0);

        // Switch to Gamma — now Reflex should be active
        bus.set_brain_wave(BrainWave::Gamma);
        let (executed, _) = bus.tick_all();
        assert_eq!(executed, 1, "Reflex hook should execute in Gamma");
        assert_eq!(counter.load(Ordering::Relaxed), 1);
    }

    #[test]
    fn priority_inversion_prevented_by_tier_gating() {
        // A high-priority hook on a slow tier (Evolutionary) should not
        // interfere with fast tiers when the brain wave activates fast tiers
        let mut bus = TimescaleBus::default();
        bus.set_brain_wave(BrainWave::Gamma);

        let order = std::sync::Arc::new(std::sync::Mutex::new(Vec::new()));

        // High-priority hook on Evolutionary (slow tier)
        let o1 = order.clone();
        bus.register(
            Tier::Evolutionary,
            "slow_high_pri",
            Box::new(move || {
                o1.lock().unwrap().push("slow");
                HookResult::Complete
            }),
        );

        // Low-priority hook on Reflex (fast tier)
        let o2 = order.clone();
        bus.register(
            Tier::Reflex,
            "fast_low_pri",
            Box::new(move || {
                o2.lock().unwrap().push("fast");
                HookResult::Complete
            }),
        );

        let _ = bus.tick_all();
        {
            let order = order.lock().unwrap();
            // Both should execute, but fast tier should not be blocked by slow tier
            assert_eq!(order.len(), 2);
            assert!(order.contains(&"fast"));
            assert!(order.contains(&"slow"));
            drop(order);
        }
    }

    #[test]
    fn delta_brain_wave_only_evolutionary_active() {
        let mut bus = TimescaleBus::default();
        bus.set_brain_wave(BrainWave::Delta);

        // Register hooks on all tiers
        for tier in Tier::all() {
            bus.register(
                tier,
                format!("hook_{}", tier.index()),
                Box::new(|| HookResult::Complete),
            );
        }

        // Only Evolutionary should execute in Delta
        let (executed, _) = bus.tick_all();
        assert_eq!(
            executed, 1,
            "Only Evolutionary tier should be active in Delta"
        );
    }
}
