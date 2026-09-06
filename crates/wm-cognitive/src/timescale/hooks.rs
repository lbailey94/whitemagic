//! Hook registration and execution for the timescale bus.

use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

/// Unique hook identifier.
pub type HookId = u64;

/// Result of a hook execution.
#[derive(Debug, Clone)]
pub enum HookResult {
    /// Hook completed successfully.
    Complete,
    /// Hook needs more time (will be retried next tick).
    NeedsMoreTime,
    /// Hook returned an error.
    Error(String),
}

impl HookResult {
    /// Check if the hook completed successfully.
    #[must_use]
    pub const fn is_complete(&self) -> bool {
        matches!(self, Self::Complete)
    }

    /// Check if the hook errored.
    #[must_use]
    pub const fn is_error(&self) -> bool {
        matches!(self, Self::Error(_))
    }
}

/// A hook registered on a timescale tier.
pub struct Hook {
    /// Unique ID.
    pub id: HookId,
    /// Human-readable name.
    pub name: String,
    /// The callback to execute on each tick.
    pub callback: Box<dyn Fn() -> HookResult + Send + Sync>,
    /// Optional fallback to execute if the callback exceeds its budget.
    pub fallback: Option<Box<dyn Fn() + Send + Sync>>,
    /// Priority (0=lowest, 255=highest). Higher priority hooks execute first.
    pub priority: u8,
    /// Statistics for this hook.
    pub stats: HookStats,
}

impl std::fmt::Debug for Hook {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Hook")
            .field("id", &self.id)
            .field("name", &self.name)
            .field("priority", &self.priority)
            .field("stats", &self.stats)
            .finish_non_exhaustive()
    }
}

/// Atomic statistics tracked per-hook.
#[derive(Debug, Default)]
pub struct HookStats {
    /// Total number of ticks executed.
    pub tick_count: AtomicU64,
    /// Number of successful completions.
    pub success_count: AtomicU64,
    /// Number of timeouts (budget exceeded).
    pub timeout_count: AtomicU64,
    /// Number of errors.
    pub error_count: AtomicU64,
    /// Last execution duration in microseconds.
    pub last_duration_us: AtomicU64,
    /// Average execution duration in microseconds (rolling).
    pub avg_duration_us: AtomicU64,
}

impl Clone for HookStats {
    fn clone(&self) -> Self {
        Self {
            tick_count: AtomicU64::new(self.tick_count.load(Ordering::Relaxed)),
            success_count: AtomicU64::new(self.success_count.load(Ordering::Relaxed)),
            timeout_count: AtomicU64::new(self.timeout_count.load(Ordering::Relaxed)),
            error_count: AtomicU64::new(self.error_count.load(Ordering::Relaxed)),
            last_duration_us: AtomicU64::new(self.last_duration_us.load(Ordering::Relaxed)),
            avg_duration_us: AtomicU64::new(self.avg_duration_us.load(Ordering::Relaxed)),
        }
    }
}

/// Serializable snapshot of hook statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HookStatsSnapshot {
    /// Total number of ticks executed.
    pub tick_count: u64,
    /// Number of successful completions.
    pub success_count: u64,
    /// Number of timeouts (budget exceeded).
    pub timeout_count: u64,
    /// Number of errors.
    pub error_count: u64,
    /// Last execution duration in microseconds.
    pub last_duration_us: u64,
    /// Average execution duration in microseconds.
    pub avg_duration_us: u64,
}

impl HookStats {
    /// Record a successful execution.
    pub fn record_success(&self, duration: Duration) {
        self.tick_count.fetch_add(1, Ordering::Relaxed);
        self.success_count.fetch_add(1, Ordering::Relaxed);
        let us = duration.as_micros() as u64;
        self.last_duration_us.store(us, Ordering::Relaxed);
        // Simple rolling average
        let prev_avg = self.avg_duration_us.load(Ordering::Relaxed);
        let count = self.success_count.load(Ordering::Relaxed);
        if count > 0 {
            let new_avg = prev_avg + us.saturating_sub(prev_avg).checked_div(count).unwrap_or(0);
            self.avg_duration_us.store(new_avg, Ordering::Relaxed);
        }
    }

    /// Record a timeout.
    pub fn record_timeout(&self) {
        self.tick_count.fetch_add(1, Ordering::Relaxed);
        self.timeout_count.fetch_add(1, Ordering::Relaxed);
    }

    /// Record an error.
    pub fn record_error(&self) {
        self.tick_count.fetch_add(1, Ordering::Relaxed);
        self.error_count.fetch_add(1, Ordering::Relaxed);
    }

    /// Get a serializable snapshot.
    pub fn snapshot(&self) -> HookStatsSnapshot {
        HookStatsSnapshot {
            tick_count: self.tick_count.load(Ordering::Relaxed),
            success_count: self.success_count.load(Ordering::Relaxed),
            timeout_count: self.timeout_count.load(Ordering::Relaxed),
            error_count: self.error_count.load(Ordering::Relaxed),
            last_duration_us: self.last_duration_us.load(Ordering::Relaxed),
            avg_duration_us: self.avg_duration_us.load(Ordering::Relaxed),
        }
    }

    /// Success rate (0.0 to 1.0).
    pub fn success_rate(&self) -> f64 {
        let ticks = self.tick_count.load(Ordering::Relaxed);
        if ticks == 0 {
            return 1.0;
        }
        self.success_count.load(Ordering::Relaxed) as f64 / ticks as f64
    }
}

impl Hook {
    /// Create a new hook with the given name and callback.
    pub fn new(
        id: HookId,
        name: impl Into<String>,
        callback: Box<dyn Fn() -> HookResult + Send + Sync>,
    ) -> Self {
        Self {
            id,
            name: name.into(),
            callback,
            fallback: None,
            priority: 0,
            stats: HookStats::default(),
        }
    }

    /// Set the fallback function.
    #[must_use]
    pub fn with_fallback(mut self, fallback: Box<dyn Fn() + Send + Sync>) -> Self {
        self.fallback = Some(fallback);
        self
    }

    /// Set the priority.
    #[must_use]
    pub const fn with_priority(mut self, priority: u8) -> Self {
        self.priority = priority;
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hook_result_is_complete() {
        assert!(HookResult::Complete.is_complete());
        assert!(!HookResult::Error("fail".to_string()).is_complete());
        assert!(!HookResult::NeedsMoreTime.is_complete());
    }

    #[test]
    fn hook_result_is_error() {
        assert!(HookResult::Error("fail".to_string()).is_error());
        assert!(!HookResult::Complete.is_error());
    }

    #[test]
    fn hook_stats_record_success() {
        let stats = HookStats::default();
        stats.record_success(Duration::from_micros(50));
        assert_eq!(stats.tick_count.load(Ordering::Relaxed), 1);
        assert_eq!(stats.success_count.load(Ordering::Relaxed), 1);
        assert_eq!(stats.last_duration_us.load(Ordering::Relaxed), 50);
    }

    #[test]
    fn hook_stats_record_timeout() {
        let stats = HookStats::default();
        stats.record_timeout();
        assert_eq!(stats.timeout_count.load(Ordering::Relaxed), 1);
    }

    #[test]
    fn hook_stats_record_error() {
        let stats = HookStats::default();
        stats.record_error();
        assert_eq!(stats.error_count.load(Ordering::Relaxed), 1);
    }

    #[test]
    fn hook_stats_success_rate() {
        let stats = HookStats::default();
        stats.record_success(Duration::from_micros(10));
        stats.record_error();
        assert_eq!(stats.success_rate(), 0.5);
    }

    #[test]
    fn hook_stats_success_rate_no_ticks() {
        let stats = HookStats::default();
        assert_eq!(stats.success_rate(), 1.0);
    }

    #[test]
    fn hook_stats_snapshot() {
        let stats = HookStats::default();
        stats.record_success(Duration::from_micros(100));
        let snap = stats.snapshot();
        assert_eq!(snap.tick_count, 1);
        assert_eq!(snap.success_count, 1);
        assert_eq!(snap.last_duration_us, 100);
    }

    #[test]
    fn hook_new_basic() {
        let hook = Hook::new(1, "test_hook", Box::new(|| HookResult::Complete));
        assert_eq!(hook.id, 1);
        assert_eq!(hook.name, "test_hook");
        assert_eq!(hook.priority, 0);
        assert!(hook.fallback.is_none());
    }

    #[test]
    fn hook_with_fallback_and_priority() {
        let hook = Hook::new(2, "prioritized", Box::new(|| HookResult::Complete))
            .with_fallback(Box::new(|| {}))
            .with_priority(128);
        assert_eq!(hook.priority, 128);
        assert!(hook.fallback.is_some());
    }

    #[test]
    fn hook_callback_executes() {
        let hook = Hook::new(0, "exec", Box::new(|| HookResult::Complete));
        let result = (hook.callback)();
        assert!(result.is_complete());
    }
}
