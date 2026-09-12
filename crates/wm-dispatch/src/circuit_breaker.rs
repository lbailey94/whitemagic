//! Circuit Breaker — Stoic resilience for tool dispatch.
//!
//! When a tool fails N times within M seconds, the breaker "opens" and
//! subsequent calls fast-fail immediately. After a cooldown, the breaker
//! enters "half-open" and allows a single probe call. If the probe succeeds,
//! the breaker closes and normal flow resumes.
//!
//! States:
//!   CLOSED   → Normal operation; failures are counted.
//!   OPEN     → Fast-fail; returns immediately without calling the tool.
//!   HALF_OPEN → One probe call allowed; success → CLOSED, failure → OPEN.
//!
//! Inspired by v2's circuit_breaker.py and the Koka algebraic effect handler,
//! but implemented as a pure Rust state machine with monotonic clock.

use std::collections::HashMap;
use std::sync::RwLock;
use std::time::{Duration, Instant};

/// Circuit breaker state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BreakerState {
    /// Normal operation; failures are counted.
    Closed,
    /// Fast-fail; calls return immediately.
    Open,
    /// One probe call allowed; success → Closed, failure → Open.
    HalfOpen,
}

/// Configuration for a single circuit breaker.
#[derive(Debug, Clone)]
pub struct BreakerConfig {
    /// Number of failures within the window before opening.
    pub failure_threshold: u32,
    /// Time window for counting failures.
    pub window: Duration,
    /// How long to stay open before transitioning to half-open.
    pub cooldown: Duration,
}

impl Default for BreakerConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 5,
            window: Duration::from_secs(10),
            cooldown: Duration::from_secs(30),
        }
    }
}

impl BreakerConfig {
    /// Parse configuration from the environment:
    /// `WM_BREAKER_THRESHOLD` (u32), `WM_BREAKER_WINDOW_MS` (u64),
    /// `WM_BREAKER_COOLDOWN_MS` (u64). Unset or invalid fields keep the
    /// default (invalid values warn, never fail startup), so the
    /// no-variables path is byte-identical to [`BreakerConfig::default`].
    #[must_use]
    pub fn from_env() -> Self {
        Self::from_opt(
            std::env::var("WM_BREAKER_THRESHOLD").ok().as_deref(),
            std::env::var("WM_BREAKER_WINDOW_MS").ok().as_deref(),
            std::env::var("WM_BREAKER_COOLDOWN_MS").ok().as_deref(),
        )
    }

    /// Testable core of [`BreakerConfig::from_env`] — no environment reads.
    #[must_use]
    fn from_opt(
        threshold: Option<&str>,
        window_ms: Option<&str>,
        cooldown_ms: Option<&str>,
    ) -> Self {
        let default = Self::default();
        Self {
            failure_threshold: parse_env(
                "WM_BREAKER_THRESHOLD",
                threshold,
                default.failure_threshold,
            ),
            window: Duration::from_millis(parse_env(
                "WM_BREAKER_WINDOW_MS",
                window_ms,
                default.window.as_millis() as u64,
            )),
            cooldown: Duration::from_millis(parse_env(
                "WM_BREAKER_COOLDOWN_MS",
                cooldown_ms,
                default.cooldown.as_millis() as u64,
            )),
        }
    }
}

/// Parse one env value, falling back to `default` on absence or parse error
/// (warn-only: a typo must not take the fleet down).
fn parse_env<T>(key: &str, raw: Option<&str>, default: T) -> T
where
    T: std::str::FromStr,
    T::Err: std::fmt::Debug,
{
    match raw {
        None => default,
        Some(value) => match value.parse::<T>() {
            Ok(parsed) => parsed,
            Err(error) => {
                tracing::warn!(
                    variable = key,
                    value = value,
                    error = ?error,
                    "circuit-breaker env value invalid — using default"
                );
                default
            }
        },
    }
}

/// A circuit breaker for a single tool.
pub struct CircuitBreaker {
    tool_name: String,
    config: BreakerConfig,
    state: BreakerState,
    failure_timestamps: Vec<Instant>,
    opened_at: Instant,
    total_trips: u64,
    /// Half-open single-probe guard: true while one probe call is out.
    /// Prevents a burst of concurrent callers from all "probing" a
    /// recovering tool (module doc promises a single probe).
    probe_in_flight: bool,
    /// When the in-flight probe started; a probe older than `cooldown` is
    /// treated as dead (caller never recorded) so the breaker cannot wedge.
    probe_started_at: Instant,
}

impl CircuitBreaker {
    /// Create a new breaker for the given tool name.
    pub fn new(tool_name: impl Into<String>, config: BreakerConfig) -> Self {
        Self {
            tool_name: tool_name.into(),
            config,
            state: BreakerState::Closed,
            failure_timestamps: Vec::new(),
            opened_at: Instant::now(),
            total_trips: 0,
            probe_in_flight: false,
            probe_started_at: Instant::now(),
        }
    }

    /// Tool name this breaker protects.
    #[must_use]
    pub fn tool_name(&self) -> &str {
        &self.tool_name
    }

    /// Current breaker state.
    #[must_use]
    pub const fn state(&self) -> BreakerState {
        self.state
    }

    /// Total number of times this breaker has tripped from Closed to Open.
    #[must_use]
    pub const fn total_trips(&self) -> u64 {
        self.total_trips
    }

    /// Check if the breaker is open (should fast-fail).
    ///
    /// Returns `true` if calls should be rejected, `false` if a call may proceed.
    /// If the breaker is Open and the cooldown has elapsed, transitions to HalfOpen
    /// and returns `false` (allowing one probe call).
    pub fn is_open(&mut self) -> bool {
        match self.state {
            BreakerState::Closed => false,
            BreakerState::Open => {
                let elapsed = Instant::now().saturating_duration_since(self.opened_at);
                if elapsed >= self.config.cooldown {
                    self.state = BreakerState::HalfOpen;
                    // This caller becomes the single probe.
                    self.probe_in_flight = true;
                    self.probe_started_at = Instant::now();
                    tracing::info!(
                        tool = %self.tool_name,
                        "Circuit breaker: OPEN → HALF_OPEN (cooldown elapsed)"
                    );
                    false // Allow the probe call
                } else {
                    true
                }
            }
            BreakerState::HalfOpen => {
                // Exactly one probe at a time. A probe older than the
                // cooldown is presumed dead (its caller never recorded)
                // and may be replaced.
                let probe_stale = self.probe_in_flight
                    && Instant::now().saturating_duration_since(self.probe_started_at)
                        >= self.config.cooldown;
                if self.probe_in_flight && !probe_stale {
                    true // A probe is already out — fast-fail the rest
                } else {
                    self.probe_in_flight = true;
                    self.probe_started_at = Instant::now();
                    false
                }
            }
        }
    }

    /// Record a successful tool call.
    pub fn record_success(&mut self) {
        if self.state == BreakerState::HalfOpen {
            self.state = BreakerState::Closed;
            self.failure_timestamps.clear();
            self.probe_in_flight = false;
            tracing::info!(
                tool = %self.tool_name,
                "Circuit breaker: HALF_OPEN → CLOSED (probe succeeded)"
            );
        }
        // In Closed state, successes don't clear the failure window —
        // they'll naturally expire.
    }

    /// Record a tool failure.
    pub fn record_failure(&mut self) {
        let now = Instant::now();

        if self.state == BreakerState::HalfOpen {
            // Probe failed → reopen (a fresh trip: the tool tried to
            // recover and failed, so the trip count must reflect it).
            self.state = BreakerState::Open;
            self.opened_at = now;
            self.probe_in_flight = false;
            self.total_trips += 1;
            tracing::warn!(
                tool = %self.tool_name,
                trip_count = self.total_trips,
                "Circuit breaker: HALF_OPEN → OPEN (probe failed)"
            );
            return;
        }

        // Prune old failures outside the window
        // Use checked_sub to avoid panic if window > elapsed (e.g. very large window config)
        if let Some(cutoff) = now.checked_sub(self.config.window) {
            self.failure_timestamps.retain(|t| *t >= cutoff);
        }
        self.failure_timestamps.push(now);

        if self.failure_timestamps.len() >= self.config.failure_threshold as usize {
            self.state = BreakerState::Open;
            self.opened_at = now;
            self.probe_in_flight = false;
            self.total_trips += 1;
            tracing::warn!(
                tool = %self.tool_name,
                failures = self.failure_timestamps.len(),
                window_secs = self.config.window.as_secs(),
                trip_count = self.total_trips,
                "Circuit breaker: CLOSED → OPEN"
            );
        }
    }

    /// Reset the breaker to Closed state (e.g. for manual recovery).
    pub fn reset(&mut self) {
        self.state = BreakerState::Closed;
        self.failure_timestamps.clear();
        self.probe_in_flight = false;
        self.total_trips = 0;
    }

    /// Remaining cooldown duration if Open, otherwise zero.
    #[must_use]
    pub fn remaining_cooldown(&self) -> Duration {
        if self.state == BreakerState::Open {
            let elapsed = Instant::now().saturating_duration_since(self.opened_at);
            self.config.cooldown.saturating_sub(elapsed)
        } else {
            Duration::ZERO
        }
    }
}

/// Registry of circuit breakers, one per tool.
pub struct CircuitBreakerRegistry {
    breakers: RwLock<HashMap<String, CircuitBreaker>>,
    default_config: BreakerConfig,
}

impl CircuitBreakerRegistry {
    /// Create a new registry with the given default config.
    #[must_use]
    pub fn new(default_config: BreakerConfig) -> Self {
        Self {
            breakers: RwLock::new(HashMap::new()),
            default_config,
        }
    }

    /// Check if a tool's circuit breaker is open.
    ///
    /// Returns `true` if the call should be fast-failed.
    pub fn is_open(&self, tool_name: &str) -> bool {
        if let Ok(mut guard) = self.breakers.write() {
            let breaker = guard
                .entry(tool_name.to_string())
                .or_insert_with(|| CircuitBreaker::new(tool_name, self.default_config.clone()));
            breaker.is_open()
        } else {
            false // Poisoned lock — fail open (allow the call)
        }
    }

    /// Record a successful call for the given tool.
    pub fn record_success(&self, tool_name: &str) {
        if let Ok(mut guard) = self.breakers.write() {
            if let Some(breaker) = guard.get_mut(tool_name) {
                breaker.record_success();
            }
        }
    }

    /// Record a failure for the given tool.
    pub fn record_failure(&self, tool_name: &str) {
        if let Ok(mut guard) = self.breakers.write() {
            let breaker = guard
                .entry(tool_name.to_string())
                .or_insert_with(|| CircuitBreaker::new(tool_name, self.default_config.clone()));
            breaker.record_failure();
        }
    }

    /// Get the state of a tool's breaker (defaults to Closed if not tracked).
    pub fn state(&self, tool_name: &str) -> BreakerState {
        if let Ok(guard) = self.breakers.read() {
            guard
                .get(tool_name)
                .map_or(BreakerState::Closed, CircuitBreaker::state)
        } else {
            BreakerState::Closed
        }
    }

    /// Reset a specific tool's breaker.
    pub fn reset(&self, tool_name: &str) {
        if let Ok(mut guard) = self.breakers.write() {
            if let Some(breaker) = guard.get_mut(tool_name) {
                breaker.reset();
            }
        }
    }

    /// Reset every tracked breaker (operator recovery). Returns how many
    /// breakers were reset.
    pub fn reset_all(&self) -> usize {
        if let Ok(mut guard) = self.breakers.write() {
            let count = guard.len();
            for breaker in guard.values_mut() {
                breaker.reset();
            }
            count
        } else {
            0
        }
    }

    /// Get total trip count for a tool.
    pub fn total_trips(&self, tool_name: &str) -> u64 {
        if let Ok(guard) = self.breakers.read() {
            guard.get(tool_name).map_or(0, CircuitBreaker::total_trips)
        } else {
            0
        }
    }

    /// Create a registry from `WM_BREAKER_*` env configuration
    /// (defaults when unset — see [`BreakerConfig::from_env`]).
    #[must_use]
    pub fn from_env() -> Self {
        Self::new(BreakerConfig::from_env())
    }

    /// Read-only operator snapshot for `/status`: open + half-open tool
    /// names and non-zero trip counts. Closed tools with zero trips are
    /// omitted; no mutation, safe to call on any request path.
    #[must_use]
    pub fn snapshot(&self) -> serde_json::Value {
        let Ok(guard) = self.breakers.read() else {
            return serde_json::json!({"error": "breaker registry lock poisoned"});
        };
        let mut open = Vec::new();
        let mut half_open = Vec::new();
        let mut trips = serde_json::Map::new();
        for (name, breaker) in guard.iter() {
            match breaker.state() {
                BreakerState::Open => open.push(name.clone()),
                BreakerState::HalfOpen => half_open.push(name.clone()),
                BreakerState::Closed => {}
            }
            if breaker.total_trips() > 0 {
                trips.insert(name.clone(), serde_json::json!(breaker.total_trips()));
            }
        }
        open.sort();
        half_open.sort();
        serde_json::json!({
            "open": open,
            "half_open": half_open,
            "trips": trips,
        })
    }
}

impl Default for CircuitBreakerRegistry {
    fn default() -> Self {
        Self::new(BreakerConfig::default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;

    #[test]
    fn breaker_starts_closed() {
        let mut b = CircuitBreaker::new("test_tool", BreakerConfig::default());
        assert_eq!(b.state(), BreakerState::Closed);
        assert!(!b.is_open());
    }

    #[test]
    fn breaker_opens_after_threshold() {
        let config = BreakerConfig {
            failure_threshold: 3,
            window: Duration::from_secs(10),
            cooldown: Duration::from_secs(30),
        };
        let mut b = CircuitBreaker::new("test_tool", config);

        b.record_failure();
        b.record_failure();
        assert_eq!(b.state(), BreakerState::Closed);

        b.record_failure();
        assert_eq!(b.state(), BreakerState::Open);
        assert_eq!(b.total_trips(), 1);
        assert!(b.is_open());
    }

    #[test]
    fn breaker_half_open_after_cooldown() {
        let config = BreakerConfig {
            failure_threshold: 1,
            window: Duration::from_secs(10),
            cooldown: Duration::from_millis(50),
        };
        let mut b = CircuitBreaker::new("test_tool", config);

        b.record_failure();
        assert_eq!(b.state(), BreakerState::Open);

        // Wait for cooldown
        thread::sleep(Duration::from_millis(60));
        assert!(!b.is_open()); // Transitions to HalfOpen, allows probe
        assert_eq!(b.state(), BreakerState::HalfOpen);
    }

    #[test]
    fn half_open_success_closes() {
        let config = BreakerConfig {
            failure_threshold: 1,
            window: Duration::from_secs(10),
            cooldown: Duration::from_millis(50),
        };
        let mut b = CircuitBreaker::new("test_tool", config);

        b.record_failure();
        thread::sleep(Duration::from_millis(60));
        b.is_open(); // → HalfOpen
        b.record_success();
        assert_eq!(b.state(), BreakerState::Closed);
    }

    #[test]
    fn half_open_failure_reopens() {
        let config = BreakerConfig {
            failure_threshold: 1,
            window: Duration::from_secs(10),
            cooldown: Duration::from_millis(50),
        };
        let mut b = CircuitBreaker::new("test_tool", config);

        b.record_failure();
        thread::sleep(Duration::from_millis(60));
        b.is_open(); // → HalfOpen
        b.record_failure();
        assert_eq!(b.state(), BreakerState::Open);
    }

    #[test]
    fn failures_expire_outside_window() {
        let config = BreakerConfig {
            failure_threshold: 3,
            window: Duration::from_millis(50),
            cooldown: Duration::from_secs(30),
        };
        let mut b = CircuitBreaker::new("test_tool", config);

        b.record_failure();
        b.record_failure();
        thread::sleep(Duration::from_millis(60));
        b.record_failure();
        // Only 1 failure in the current window — should still be closed
        assert_eq!(b.state(), BreakerState::Closed);
    }

    #[test]
    fn registry_tracks_per_tool() {
        let registry = CircuitBreakerRegistry::new(BreakerConfig {
            failure_threshold: 2,
            window: Duration::from_secs(10),
            cooldown: Duration::from_secs(30),
        });

        // Tool A fails twice → opens
        registry.record_failure("tool_a");
        registry.record_failure("tool_a");
        assert_eq!(registry.state("tool_a"), BreakerState::Open);
        assert!(registry.is_open("tool_a"));

        // Tool B is still closed
        assert_eq!(registry.state("tool_b"), BreakerState::Closed);
        assert!(!registry.is_open("tool_b"));
    }

    #[test]
    fn registry_reset() {
        let registry = CircuitBreakerRegistry::new(BreakerConfig {
            failure_threshold: 1,
            window: Duration::from_secs(10),
            cooldown: Duration::from_secs(30),
        });

        registry.record_failure("tool_x");
        assert_eq!(registry.state("tool_x"), BreakerState::Open);
        registry.reset("tool_x");
        assert_eq!(registry.state("tool_x"), BreakerState::Closed);
    }

    #[test]
    fn remaining_cooldown_decreases() {
        let config = BreakerConfig {
            failure_threshold: 1,
            window: Duration::from_secs(10),
            cooldown: Duration::from_millis(100),
        };
        let mut b = CircuitBreaker::new("test_tool", config);

        b.record_failure();
        let remaining = b.remaining_cooldown();
        assert!(remaining > Duration::ZERO);
        assert!(remaining <= Duration::from_millis(100));

        thread::sleep(Duration::from_millis(60));
        let remaining2 = b.remaining_cooldown();
        assert!(remaining2 < remaining);
    }

    #[test]
    fn large_window_doesnt_panic() {
        // Very large window could cause checked_sub to return None
        // (if window > elapsed since Instant epoch)
        let config = BreakerConfig {
            failure_threshold: 1,
            window: Duration::from_secs(u64::MAX / 1_000_000_000),
            cooldown: Duration::from_secs(30),
        };
        let mut b = CircuitBreaker::new("test_tool", config);

        // Should not panic
        b.record_failure();
        assert_eq!(b.state(), BreakerState::Open);
    }

    #[test]
    fn half_open_admits_single_probe() {
        let config = BreakerConfig {
            failure_threshold: 1,
            window: Duration::from_secs(10),
            cooldown: Duration::from_millis(20),
        };
        let mut b = CircuitBreaker::new("test_tool", config);
        b.record_failure();
        assert!(b.is_open());

        thread::sleep(Duration::from_millis(30));
        assert!(!b.is_open(), "first caller after cooldown is the probe");
        assert!(
            b.is_open(),
            "concurrent callers must fast-fail while the probe is out"
        );

        b.record_success();
        assert_eq!(b.state(), BreakerState::Closed);
        assert!(!b.is_open());
    }

    #[test]
    fn half_open_failure_counts_new_trip() {
        let config = BreakerConfig {
            failure_threshold: 1,
            window: Duration::from_secs(10),
            cooldown: Duration::from_millis(20),
        };
        let mut b = CircuitBreaker::new("test_tool", config);
        b.record_failure();
        assert_eq!(b.total_trips(), 1);

        thread::sleep(Duration::from_millis(30));
        assert!(!b.is_open()); // probe admitted
        b.record_failure(); // probe failed

        assert_eq!(b.state(), BreakerState::Open);
        assert_eq!(b.total_trips(), 2, "half-open re-open is a fresh trip");
    }

    #[test]
    fn stale_probe_does_not_wedge_half_open() {
        let config = BreakerConfig {
            failure_threshold: 1,
            window: Duration::from_secs(10),
            cooldown: Duration::from_millis(20),
        };
        let mut b = CircuitBreaker::new("test_tool", config);
        b.record_failure();

        thread::sleep(Duration::from_millis(30));
        assert!(!b.is_open()); // probe #1 admitted, never records

        thread::sleep(Duration::from_millis(30));
        assert!(
            !b.is_open(),
            "a dead probe older than cooldown must be replaceable, not wedged"
        );
        assert_eq!(b.state(), BreakerState::HalfOpen);
    }

    #[test]
    fn config_from_opt_parses_and_defaults_invalid_values() {
        let parsed = BreakerConfig::from_opt(Some("3"), Some("2500"), Some("100"));
        assert_eq!(parsed.failure_threshold, 3);
        assert_eq!(parsed.window, Duration::from_millis(2500));
        assert_eq!(parsed.cooldown, Duration::from_millis(100));

        let defaults = BreakerConfig::from_opt(None, Some("not-a-number"), None);
        assert_eq!(defaults.failure_threshold, 5);
        assert_eq!(defaults.window, Duration::from_secs(10));
        assert_eq!(defaults.cooldown, Duration::from_secs(30));
    }

    #[test]
    fn snapshot_reports_open_and_trips() {
        let registry = CircuitBreakerRegistry::new(BreakerConfig {
            failure_threshold: 1,
            window: Duration::from_secs(10),
            cooldown: Duration::from_secs(30),
        });
        registry.record_failure("tool_a");
        let snap = registry.snapshot();
        assert_eq!(snap["open"], serde_json::json!(["tool_a"]));
        assert_eq!(snap["half_open"], serde_json::json!([]));
        assert_eq!(snap["trips"]["tool_a"], 1);
        assert_eq!(
            registry.snapshot()["open"].as_array().map(Vec::len),
            Some(1)
        );
    }
}
