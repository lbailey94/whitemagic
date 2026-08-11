//! Atomic sliding-window rate limiter for tool dispatch.
//!
//! Provides O(1) per-check rate limiting using lock-free atomics.
//! Per-tool and global RPM enforcement with burst allowance.
//!
//! # Configuration
//!
//! Limits are configurable via `RateLimiterConfig` (defaults in
//! [`RateLimiterConfig::default`]) or the environment:
//!
//! | Variable | Default | Description |
//! |----------|---------|-------------|
//! | `WM_DISPATCH_GLOBAL_RPM` | 300 | Max total dispatches/min across all tools |
//! | `WM_DISPATCH_TOOL_RPM` | 60 | Default per-tool RPM limit |
//! | `WM_DISPATCH_BURST` | 10 | Extra burst capacity per tool |
//! | `WM_DISPATCH_TOOL_OVERRIDES` | — | `tool:rpm,tool2:rpm2` per-tool overrides |
//!
//! Ported from v2-reference/safety/rate_limiter.rs — PyO3 and lazy_static removed.

use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, RwLock};
use std::time::{SystemTime, UNIX_EPOCH};

/// Default limits — the values used by [`RateLimiter::default`].
pub const DEFAULT_GLOBAL_RPM: u64 = 300;
pub const DEFAULT_TOOL_RPM: u64 = 60;
pub const DEFAULT_BURST: u64 = 10;

/// Configuration for a [`RateLimiter`].
///
/// Built from `RateLimiterConfig::default()`, optionally overridden by
/// `WM_DISPATCH_*` environment variables (see module docs).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RateLimiterConfig {
    /// Max total dispatches per minute across all tools (0 = unlimited).
    pub global_rpm: u64,
    /// Default per-tool dispatches per minute (0 = unlimited).
    pub default_tool_rpm: u64,
    /// Extra burst capacity per tool window.
    pub burst_allowance: u64,
    /// Per-tool RPM overrides: tool name → RPM.
    pub tool_overrides: HashMap<String, u64>,
}

impl Default for RateLimiterConfig {
    fn default() -> Self {
        Self {
            global_rpm: DEFAULT_GLOBAL_RPM,
            default_tool_rpm: DEFAULT_TOOL_RPM,
            burst_allowance: DEFAULT_BURST,
            tool_overrides: HashMap::new(),
        }
    }
}

impl RateLimiterConfig {
    /// Build a config from `WM_DISPATCH_*` environment variables.
    ///
    /// Unset variables keep their defaults. Malformed values are ignored with
    /// a warning (a bad env var should not take the system down).
    #[must_use]
    pub fn from_env() -> Self {
        Self::from_env_impl(
            std::env::var("WM_DISPATCH_GLOBAL_RPM").ok(),
            std::env::var("WM_DISPATCH_TOOL_RPM").ok(),
            std::env::var("WM_DISPATCH_BURST").ok(),
            std::env::var("WM_DISPATCH_TOOL_OVERRIDES").ok(),
        )
    }

    /// Pure parsing used by [`Self::from_env`]; testable without touching
    /// process environment state.
    #[must_use]
    fn from_env_impl(
        global_rpm: Option<String>,
        tool_rpm: Option<String>,
        burst: Option<String>,
        overrides: Option<String>,
    ) -> Self {
        let mut config = Self::default();
        if let Some(v) = global_rpm {
            if let Ok(rpm) = v.parse::<u64>() {
                config.global_rpm = rpm;
            } else {
                tracing::warn!("WM_DISPATCH_GLOBAL_RPM invalid ({v}), keeping default");
            }
        }
        if let Some(v) = tool_rpm {
            if let Ok(rpm) = v.parse::<u64>() {
                config.default_tool_rpm = rpm;
            } else {
                tracing::warn!("WM_DISPATCH_TOOL_RPM invalid ({v}), keeping default");
            }
        }
        if let Some(v) = burst {
            if let Ok(burst) = v.parse::<u64>() {
                config.burst_allowance = burst;
            } else {
                tracing::warn!("WM_DISPATCH_BURST invalid ({v}), keeping default");
            }
        }
        if let Some(v) = overrides {
            for pair in v.split(',') {
                let pair = pair.trim();
                if pair.is_empty() {
                    continue;
                }
                let Some((tool, rpm)) = pair.split_once(':') else {
                    tracing::warn!("WM_DISPATCH_TOOL_OVERRIDES entry '{pair}' missing ':' — skipping");
                    continue;
                };
                if let Ok(rpm) = rpm.trim().parse::<u64>() {
                    config.tool_overrides.insert(tool.trim().to_string(), rpm);
                } else {
                    tracing::warn!(
                        "WM_DISPATCH_TOOL_OVERRIDES entry '{pair}' has invalid rpm — skipping"
                    );
                }
            }
        }
        config
    }
}

/// A sliding-window counter using two half-windows for smooth transitions.
///
/// This avoids the "boundary spike" problem of fixed-window counters
/// by weighting the previous and current window counts proportionally.
pub struct SlidingWindow {
    current_count: AtomicU64,
    previous_count: AtomicU64,
    current_window_start: AtomicU64,
    window_ms: u64,
    max_requests: u64,
    burst_allowance: u64,
    burst_tokens: AtomicU64,
    last_refill: AtomicU64,
}

impl SlidingWindow {
    /// Create a new sliding window with the given limits.
    ///
    /// - `max_requests`: Maximum requests per window before burst is consumed.
    /// - `window_ms`: Window duration in milliseconds (e.g. 60_000 for RPM).
    /// - `burst_allowance`: Extra capacity above `max_requests` for short bursts.
    #[must_use]
    pub fn new(max_requests: u64, window_ms: u64, burst_allowance: u64) -> Self {
        let now = current_time_ms();
        Self {
            current_count: AtomicU64::new(0),
            previous_count: AtomicU64::new(0),
            current_window_start: AtomicU64::new(now),
            window_ms,
            max_requests,
            burst_allowance,
            burst_tokens: AtomicU64::new(burst_allowance),
            last_refill: AtomicU64::new(now),
        }
    }

    /// Try to acquire a permit. Returns `true` if allowed, `false` if rate-limited.
    pub fn try_acquire(&self) -> bool {
        let now = current_time_ms();
        self.maybe_rotate(now);
        self.maybe_refill_burst(now);

        let window_start = self.current_window_start.load(Ordering::Relaxed);
        let elapsed = now.saturating_sub(window_start);
        let weight = if self.window_ms > 0 {
            (elapsed as f64 / self.window_ms as f64).min(1.0)
        } else {
            1.0
        };

        let prev = self.previous_count.load(Ordering::Relaxed) as f64;
        let curr = self.current_count.load(Ordering::Relaxed) as f64;
        let estimated = prev.mul_add(1.0 - weight, curr);

        if estimated < self.max_requests as f64 {
            self.current_count.fetch_add(1, Ordering::Relaxed);
            return true;
        }

        // Try burst tokens
        let tokens = self.burst_tokens.load(Ordering::Relaxed);
        if tokens > 0 {
            let prev_tokens = self.burst_tokens.fetch_sub(1, Ordering::Relaxed);
            if prev_tokens > 0 {
                self.current_count.fetch_add(1, Ordering::Relaxed);
                return true;
            }
            // Restore if we went negative
            self.burst_tokens.fetch_add(1, Ordering::Relaxed);
        }

        false
    }

    /// Get current estimated request count (weighted across windows).
    pub fn current_rate(&self) -> f64 {
        let now = current_time_ms();
        let window_start = self.current_window_start.load(Ordering::Relaxed);
        let elapsed = now.saturating_sub(window_start);
        let weight = if self.window_ms > 0 {
            (elapsed as f64 / self.window_ms as f64).min(1.0)
        } else {
            1.0
        };
        let prev = self.previous_count.load(Ordering::Relaxed) as f64;
        let curr = self.current_count.load(Ordering::Relaxed) as f64;
        prev.mul_add(1.0 - weight, curr)
    }

    fn maybe_rotate(&self, now: u64) {
        let window_start = self.current_window_start.load(Ordering::Relaxed);
        if now.saturating_sub(window_start) >= self.window_ms {
            let current = self.current_count.load(Ordering::Relaxed);
            self.previous_count.store(current, Ordering::Relaxed);
            self.current_count.store(0, Ordering::Relaxed);
            self.current_window_start.store(now, Ordering::Relaxed);
        }
    }

    fn maybe_refill_burst(&self, now: u64) {
        let last = self.last_refill.load(Ordering::Relaxed);
        if now.saturating_sub(last) >= self.window_ms {
            let current_tokens = self.burst_tokens.load(Ordering::Relaxed);
            if current_tokens < self.burst_allowance {
                self.burst_tokens.fetch_add(1, Ordering::Relaxed);
            }
            self.last_refill.store(now, Ordering::Relaxed);
        }
    }
}

fn current_time_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

/// Rate limiter managing per-tool and global windows.
pub struct RateLimiter {
    tool_windows: RwLock<HashMap<String, Arc<SlidingWindow>>>,
    global_window: SlidingWindow,
    default_tool_rpm: u64,
    window_ms: u64,
    burst_allowance: u64,
    overrides: RwLock<HashMap<String, u64>>,
}

impl RateLimiter {
    /// Create a new rate limiter.
    ///
    /// - `global_rpm`: Maximum total requests per minute across all tools.
    /// - `default_tool_rpm`: Default per-tool RPM limit.
    /// - `burst_allowance`: Extra burst capacity per tool.
    #[must_use]
    pub fn new(global_rpm: u64, default_tool_rpm: u64, burst_allowance: u64) -> Self {
        Self {
            tool_windows: RwLock::new(HashMap::new()),
            global_window: SlidingWindow::new(
                global_rpm,
                60_000,
                burst_allowance.saturating_mul(2),
            ),
            default_tool_rpm,
            window_ms: 60_000,
            burst_allowance,
            overrides: RwLock::new(HashMap::new()),
        }
    }

    /// Create a rate limiter from a [`RateLimiterConfig`].
    ///
    /// Per-tool overrides from the config are applied immediately.
    #[must_use]
    pub fn from_config(config: &RateLimiterConfig) -> Self {
        let limiter = Self::new(
            config.global_rpm,
            config.default_tool_rpm,
            config.burst_allowance,
        );
        for (tool, rpm) in &config.tool_overrides {
            limiter.set_override(tool, *rpm);
        }
        limiter
    }

    /// Set a per-tool RPM override.
    pub fn set_override(&self, tool: &str, rpm: u64) {
        if let Ok(mut guard) = self.overrides.write() {
            guard.insert(tool.to_string(), rpm);
        }
    }

    /// Try to acquire a permit for a tool invocation.
    ///
    /// Returns `Ok(())` if allowed, `Err(retry_after_ms)` if rate-limited.
    pub fn try_acquire(&self, tool: &str) -> Result<(), u64> {
        // Check global limit first
        if !self.global_window.try_acquire() {
            return Err(self.window_ms / 2);
        }

        // Get or create per-tool window
        let window = {
            let read_guard = self
                .tool_windows
                .read()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            if let Some(w) = read_guard.get(tool) {
                Arc::clone(w)
            } else {
                drop(read_guard);
                let rpm = self
                    .overrides
                    .read()
                    .unwrap_or_else(std::sync::PoisonError::into_inner)
                    .get(tool)
                    .copied()
                    .unwrap_or(self.default_tool_rpm);
                let new_window = Arc::new(SlidingWindow::new(
                    rpm,
                    self.window_ms,
                    self.burst_allowance,
                ));
                if let Ok(mut write_guard) = self.tool_windows.write() {
                    write_guard.insert(tool.to_string(), Arc::clone(&new_window));
                }
                new_window
            }
        };

        if window.try_acquire() {
            Ok(())
        } else {
            Err(self.window_ms / 4)
        }
    }

    /// Get statistics for all tracked tools.
    pub fn stats(&self) -> HashMap<String, f64> {
        let mut result = HashMap::new();
        result.insert("global_rate".to_string(), self.global_window.current_rate());
        if let Ok(guard) = self.tool_windows.read() {
            for (tool, window) in guard.iter() {
                result.insert(format!("tool:{tool}"), window.current_rate());
            }
        }
        result
    }
}

impl Default for RateLimiter {
    fn default() -> Self {
        Self::from_config(&RateLimiterConfig::default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sliding_window_allows_under_limit() {
        let w = SlidingWindow::new(10, 60_000, 0);
        for _ in 0..10 {
            assert!(w.try_acquire());
        }
    }

    #[test]
    fn sliding_window_blocks_over_limit() {
        let w = SlidingWindow::new(5, 60_000, 0);
        for _ in 0..5 {
            assert!(w.try_acquire());
        }
        assert!(!w.try_acquire());
    }

    #[test]
    fn burst_allowance_allows_extra() {
        let w = SlidingWindow::new(5, 60_000, 3);
        for _ in 0..5 {
            assert!(w.try_acquire());
        }
        // Burst should allow 3 more
        assert!(w.try_acquire());
        assert!(w.try_acquire());
        assert!(w.try_acquire());
        // Now truly blocked
        assert!(!w.try_acquire());
    }

    #[test]
    fn rate_limiter_per_tool() {
        let limiter = RateLimiter::new(1000, 5, 0);
        for _ in 0..5 {
            assert!(limiter.try_acquire("test_tool").is_ok());
        }
        // Per-tool limit hit
        assert!(limiter.try_acquire("test_tool").is_err());
        // Different tool still works
        assert!(limiter.try_acquire("other_tool").is_ok());
    }

    #[test]
    fn rate_limiter_override() {
        let limiter = RateLimiter::new(1000, 5, 0);
        limiter.set_override("special_tool", 2);
        assert!(limiter.try_acquire("special_tool").is_ok());
        assert!(limiter.try_acquire("special_tool").is_ok());
        assert!(limiter.try_acquire("special_tool").is_err());
    }

    #[test]
    fn current_rate_tracks_acquires() {
        let w = SlidingWindow::new(100, 60_000, 0);
        assert!(w.current_rate() < 0.01);
        w.try_acquire();
        w.try_acquire();
        w.try_acquire();
        assert!(w.current_rate() >= 3.0);
    }

    #[test]
    fn default_rate_limiter() {
        let limiter = RateLimiter::default();
        assert!(limiter.try_acquire("any_tool").is_ok());
    }

    // ── RateLimiterConfig tests ─────────────────────────────────────

    #[test]
    fn config_defaults_match_legacy_values() {
        let config = RateLimiterConfig::default();
        assert_eq!(config.global_rpm, 300);
        assert_eq!(config.default_tool_rpm, 60);
        assert_eq!(config.burst_allowance, 10);
        assert!(config.tool_overrides.is_empty());
    }

    #[test]
    fn config_from_env_applies_overrides() {
        let config = RateLimiterConfig::from_env_impl(
            Some("5000".to_string()),
            Some("250".to_string()),
            Some("40".to_string()),
            Some("wm:2000, memory.search: 120 ,badtool:xyz".to_string()),
        );
        assert_eq!(config.global_rpm, 5000);
        assert_eq!(config.default_tool_rpm, 250);
        assert_eq!(config.burst_allowance, 40);
        assert_eq!(config.tool_overrides.get("wm"), Some(&2000));
        assert_eq!(config.tool_overrides.get("memory.search"), Some(&120));
        assert!(!config.tool_overrides.contains_key("badtool"));
    }

    #[test]
    fn config_from_env_ignores_invalid_values() {
        let config = RateLimiterConfig::from_env_impl(
            Some("not-a-number".to_string()),
            Some("0".to_string()),
            None,
            None,
        );
        assert_eq!(config.global_rpm, DEFAULT_GLOBAL_RPM, "invalid rpm keeps default");
        assert_eq!(config.default_tool_rpm, 0, "valid 0 means unlimited");
        assert_eq!(config.burst_allowance, DEFAULT_BURST);
    }

    #[test]
    fn config_from_env_empty_overrides_ignored() {
        let config = RateLimiterConfig::from_env_impl(None, None, None, Some(String::new()));
        assert!(config.tool_overrides.is_empty());
    }

    #[test]
    fn rate_limiter_from_config_applies_overrides() {
        let config = RateLimiterConfig {
            global_rpm: 100_000,
            default_tool_rpm: 5,
            burst_allowance: 0,
            tool_overrides: std::collections::HashMap::from([("wm".to_string(), 5000)]),
        };
        let limiter = RateLimiter::from_config(&config);
        // Other tools stay at the default cap...
        for _ in 0..5 {
            assert!(limiter.try_acquire("other_tool").is_ok());
        }
        assert!(
            limiter.try_acquire("other_tool").is_err(),
            "default cap (5) enforced for non-overridden tools"
        );
        // ...while the overridden tool gets its higher cap.
        for _ in 0..5000 {
            assert!(limiter.try_acquire("wm").is_ok());
        }
        assert!(
            limiter.try_acquire("wm").is_err(),
            "override cap (5000) should be enforced after burst"
        );
    }

    // ── Property-based tests (proptest) ─────────────────────────────

    use proptest::prelude::*;

    #[test]
    fn try_acquire_empty_string() {
        let limiter = RateLimiter::new(100_000, 10_000, 1_000);
        let _ = limiter.try_acquire("");
    }

    #[test]
    fn zero_max_blocks() {
        let w = SlidingWindow::new(0, 60_000, 0);
        assert!(!w.try_acquire());
    }

    proptest! {
        /// try_acquire() must never panic with arbitrary tool names.
        #[test]
        fn try_acquire_never_panics(tool_name in ".*") {
            let limiter = RateLimiter::new(100_000, 10_000, 1_000);
            let _ = limiter.try_acquire(&tool_name);
        }

        /// try_acquire() with very long tool name must not panic.
        #[test]
        fn try_acquire_long_name(n in 1usize..1000) {
            let limiter = RateLimiter::new(100_000, 10_000, 1_000);
            let name = "x".repeat(n);
            let _ = limiter.try_acquire(&name);
        }

        /// try_acquire() with non-ASCII tool names must not panic.
        #[test]
        fn try_acquire_non_ascii(tool_name in r"[^\x00-\x7F]*") {
            let limiter = RateLimiter::new(100_000, 10_000, 1_000);
            let _ = limiter.try_acquire(&tool_name);
        }

        /// current_rate is always non-negative.
        #[test]
        fn current_rate_non_negative(max in 1u64..1000, burst in 0u64..100) {
            let w = SlidingWindow::new(max, 60_000, burst);
            w.try_acquire();
            let rate = w.current_rate();
            prop_assert!(rate >= 0.0, "current_rate must be >= 0, got {rate}");
        }
    }
}
