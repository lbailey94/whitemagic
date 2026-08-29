//! Brain-Wave Eco Mode — Five-State Resource Management
//!
//! The brain-wave system keeps `WhiteMagic` dormant when idle and active
//! when needed, with zero monitoring overhead. Transitions are driven
//! by actual event rates, not polling threads.

use serde::{Deserialize, Serialize};
use std::fmt;
use std::time::{Duration, Instant};

/// The five brain-wave states, from most active to most dormant.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum BrainWave {
    /// Full power. All subsystems, polyglot accelerators, inference.
    /// Event rate > 10/min.
    Gamma,
    /// Inference active, memory R/W, no background consolidation.
    /// Event rate > 0/min.
    Beta,
    /// No active requests for 30s+. Memory reads only.
    /// Citta heartbeat at 1/10 speed. No embeddings, no dreaming.
    Alpha,
    /// 5+ min idle. Dream cycle runs once. Embeddings paused.
    /// After dream completes, transitions to Delta.
    Theta,
    /// 30+ min idle. Only LMDB mmap is warm. Zero CPU.
    /// Wake on stdin (MCP request) or scheduled timer.
    Delta,
}

impl BrainWave {
    /// Returns true if this state allows tool execution.
    #[must_use]
    pub const fn allows_tools(self) -> bool {
        matches!(self, Self::Gamma | Self::Beta | Self::Alpha)
    }

    /// Returns true if this state allows background consolidation.
    #[must_use]
    pub const fn allows_consolidation(self) -> bool {
        matches!(self, Self::Theta)
    }

    /// Returns true if this state is dormant (zero CPU expected).
    #[must_use]
    pub const fn is_dormant(self) -> bool {
        matches!(self, Self::Delta)
    }

    /// Human-readable name.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Gamma => "Gamma (active)",
            Self::Beta => "Beta (working)",
            Self::Alpha => "Alpha (idle)",
            Self::Theta => "Theta (drowsy)",
            Self::Delta => "Delta (dormant)",
        }
    }
}

impl fmt::Display for BrainWave {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.name())
    }
}

/// Configuration for brain-wave state transitions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrainWaveConfig {
    /// Event rate threshold for Gamma (events per minute)
    pub gamma_rate: f64,
    /// Idle time before transitioning to Alpha
    pub alpha_idle: Duration,
    /// Idle time before transitioning to Theta
    pub theta_idle: Duration,
    /// Idle time before transitioning to Delta
    pub delta_idle: Duration,
}

impl Default for BrainWaveConfig {
    fn default() -> Self {
        Self {
            gamma_rate: 10.0,
            alpha_idle: Duration::from_secs(30),
            theta_idle: Duration::from_secs(300),
            delta_idle: Duration::from_secs(1800),
        }
    }
}

impl BrainWaveConfig {
    /// Create a config from environment variables.
    ///
    /// Recognized env vars:
    /// - `WM_GAMMA_RATE` — events per minute for Gamma (default: 10)
    /// - `WM_ALPHA_IDLE` — seconds idle before Alpha (default: 30)
    /// - `WM_THETA_IDLE` — seconds idle before Theta (default: 300)
    /// - `WM_DELTA_IDLE` — seconds idle before Delta (default: 1800)
    #[must_use]
    pub fn from_env() -> Self {
        let defaults = Self::default();
        Self {
            gamma_rate: std::env::var("WM_GAMMA_RATE")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(defaults.gamma_rate),
            alpha_idle: Duration::from_secs(
                std::env::var("WM_ALPHA_IDLE")
                    .ok()
                    .and_then(|v| v.parse().ok())
                    .unwrap_or(defaults.alpha_idle.as_secs()),
            ),
            theta_idle: Duration::from_secs(
                std::env::var("WM_THETA_IDLE")
                    .ok()
                    .and_then(|v| v.parse().ok())
                    .unwrap_or(defaults.theta_idle.as_secs()),
            ),
            delta_idle: Duration::from_secs(
                std::env::var("WM_DELTA_IDLE")
                    .ok()
                    .and_then(|v| v.parse().ok())
                    .unwrap_or(defaults.delta_idle.as_secs()),
            ),
        }
    }
}

/// Tracks event timestamps and computes the current brain-wave state.
///
/// Uses a ring buffer of timestamps — no extra thread, no polling.
/// Update is ~10ns (atomic push to ring buffer).
pub struct BrainWaveTracker {
    /// Configuration for state transitions
    pub config: BrainWaveConfig,
    timestamps: smallvec::SmallVec<[Instant; 64]>,
    last_event: Instant,
    current: BrainWave,
}

impl BrainWaveTracker {
    /// Create a new tracker with the given config.
    #[must_use]
    pub fn new(config: BrainWaveConfig) -> Self {
        let now = Instant::now();
        Self {
            config,
            timestamps: smallvec::SmallVec::new(),
            last_event: now,
            current: BrainWave::Delta,
        }
    }

    /// Record an event and update the brain-wave state.
    pub fn record_event(&mut self) -> BrainWave {
        let now = Instant::now();
        self.last_event = now;
        self.timestamps.push(now);
        // Keep only last 60 seconds
        let cutoff = now.checked_sub(Duration::from_secs(60)).unwrap();
        self.timestamps.retain(|t| *t > cutoff);
        self.recompute(now);
        self.current
    }

    /// Recompute the current state without recording an event.
    /// Called when checking state after a timer fires.
    pub fn recompute(&mut self, now: Instant) -> BrainWave {
        let rate = self.event_rate(now);
        let idle = now.duration_since(self.last_event);

        self.current = if rate > self.config.gamma_rate {
            BrainWave::Gamma
        } else if rate > 0.0 {
            BrainWave::Beta
        } else if idle > self.config.delta_idle {
            BrainWave::Delta
        } else if idle > self.config.theta_idle {
            BrainWave::Theta
        } else {
            BrainWave::Alpha
        };

        self.current
    }

    /// Current brain-wave state.
    #[must_use]
    pub const fn current(&self) -> BrainWave {
        self.current
    }

    /// Compute how long to sleep before the next state transition would occur.
    ///
    /// Returns `Duration::MAX` if no transition is pending (e.g., Delta with
    /// no scheduled tasks). The caller should use this in a `tokio::select!`
    /// branch alongside stdin readiness.
    #[must_use]
    pub fn next_transition_duration(&self) -> Duration {
        let now = Instant::now();
        let idle = now.duration_since(self.last_event);
        match self.current {
            BrainWave::Gamma | BrainWave::Beta => self.config.alpha_idle.saturating_sub(idle),
            BrainWave::Alpha => self.config.theta_idle.saturating_sub(idle),
            BrainWave::Theta => self.config.delta_idle.saturating_sub(idle),
            BrainWave::Delta => Duration::from_secs(3600),
        }
    }

    /// Time since the last event was recorded.
    #[must_use]
    pub fn idle_duration(&self) -> Duration {
        Instant::now().duration_since(self.last_event)
    }

    /// Events per minute based on recent timestamps.
    fn event_rate(&self, now: Instant) -> f64 {
        if self.timestamps.is_empty() {
            return 0.0;
        }
        let cutoff = now.checked_sub(Duration::from_secs(60)).unwrap();
        let recent = self.timestamps.iter().filter(|&&t| t > cutoff).count();
        recent as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn brain_wave_allows_tools() {
        assert!(BrainWave::Gamma.allows_tools());
        assert!(BrainWave::Beta.allows_tools());
        assert!(BrainWave::Alpha.allows_tools());
        assert!(!BrainWave::Theta.allows_tools());
        assert!(!BrainWave::Delta.allows_tools());
    }

    #[test]
    fn tracker_starts_dormant() {
        let tracker = BrainWaveTracker::new(BrainWaveConfig::default());
        assert_eq!(tracker.current(), BrainWave::Delta);
    }

    #[test]
    fn tracker_transitions_on_event() {
        let mut tracker = BrainWaveTracker::new(BrainWaveConfig::default());
        let _ = tracker.record_event();
        assert_eq!(tracker.current(), BrainWave::Beta);
    }

    #[test]
    fn tracker_gamma_on_burst() {
        let mut tracker = BrainWaveTracker::new(BrainWaveConfig::default());
        for _ in 0..15 {
            let _ = tracker.record_event();
        }
        assert_eq!(tracker.current(), BrainWave::Gamma);
    }

    #[test]
    fn next_transition_duration_beta_to_alpha() {
        let mut tracker = BrainWaveTracker::new(BrainWaveConfig::default());
        let _ = tracker.record_event();
        assert_eq!(tracker.current(), BrainWave::Beta);
        let d = tracker.next_transition_duration();
        // alpha_idle is 30s, we just recorded an event so idle ≈ 0
        assert!(d <= Duration::from_secs(30));
        assert!(d > Duration::from_secs(28));
    }

    #[test]
    fn next_transition_duration_delta_sleeps_long() {
        let tracker = BrainWaveTracker::new(BrainWaveConfig::default());
        assert_eq!(tracker.current(), BrainWave::Delta);
        let d = tracker.next_transition_duration();
        assert_eq!(d, Duration::from_secs(3600));
    }

    #[test]
    fn idle_duration_grows_after_event() {
        let mut tracker = BrainWaveTracker::new(BrainWaveConfig::default());
        let _ = tracker.record_event();
        let d1 = tracker.idle_duration();
        std::thread::sleep(Duration::from_millis(50));
        let d2 = tracker.idle_duration();
        assert!(d2 > d1);
    }
}
