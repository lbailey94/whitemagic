//! Tool Trait — The Fractal Meta-Tool Foundation
//!
//! Every tool in `WhiteMagic` implements this trait. Each tool self-tracks
//! its call count, success rate, latency, and resource usage via atomic
//! counters. The dispatch pipeline uses these stats to retire ineffective
//! tools and promote hot ones.

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

/// Tool arguments — deserialized from JSON-RPC params.
pub type Args = serde_json::Value;

/// Tool output — serialized to JSON-RPC result.
pub type Output = serde_json::Value;

/// Atomic statistics tracked per-tool.
///
/// All fields are atomic, enabling lock-free updates from any thread.
/// Update overhead is ~10ns per field (relaxed atomic store).
#[derive(Debug, Default)]
pub struct ToolStats {
    /// Total number of calls
    pub call_count: AtomicU64,
    /// Number of successful calls
    pub success_count: AtomicU64,
    /// Central latency estimate in nanoseconds (exponential moving average
    /// of recent call latencies — not an exact median).
    pub p50_latency_ns: AtomicU64,
    /// Highest latency seen in nanoseconds. The high-latency anomaly path
    /// compares new calls against this peak.
    pub peak_latency_ns: AtomicU64,
    /// Total CPU time consumed in nanoseconds
    pub cpu_time_ns: AtomicU64,
    /// Total LMDB pages touched
    pub lmdb_pages_touched: AtomicU64,
    /// Unix timestamp of last use
    pub last_used_unix: AtomicU64,
    /// Karma-weighted effectiveness score (0.0 = useless, 1.0 = perfect)
    pub effectiveness: std::sync::atomic::AtomicU32,
}

impl ToolStats {
    /// Record a successful call.
    pub fn record_success(&self, latency: Duration, cpu_time: Duration) {
        self.call_count.fetch_add(1, Ordering::Relaxed);
        self.success_count.fetch_add(1, Ordering::Relaxed);
        let latency_ns = latency.as_nanos() as u64;
        // Exponential moving average (alpha = 0.5) of recent latencies —
        // an honest approximation of the central value without a histogram.
        self.p50_latency_ns
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |old| {
                Some(old / 2 + latency_ns / 2)
            })
            .ok();
        // Peak latency: the high-latency anomaly path compares new calls
        // against the worst latency ever seen.
        self.peak_latency_ns
            .fetch_max(latency_ns, Ordering::Relaxed);
        self.cpu_time_ns
            .fetch_add(cpu_time.as_nanos() as u64, Ordering::Relaxed);
        self.last_used_unix.store(
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
            Ordering::Relaxed,
        );
        // Auto-update effectiveness from success rate
        self.update_effectiveness();
    }

    /// Record a failed call.
    pub fn record_failure(&self, latency: Duration) {
        self.call_count.fetch_add(1, Ordering::Relaxed);
        let latency_ns = latency.as_nanos() as u64;
        self.p50_latency_ns
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |old| {
                Some(old / 2 + latency_ns / 2)
            })
            .ok();
        self.peak_latency_ns
            .fetch_max(latency_ns, Ordering::Relaxed);
        self.last_used_unix.store(
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
            Ordering::Relaxed,
        );
        // Auto-update effectiveness from success rate
        self.update_effectiveness();
    }

    /// Get the success rate (0.0 to 1.0).
    pub fn success_rate(&self) -> f64 {
        let calls = self.call_count.load(Ordering::Relaxed);
        if calls == 0 {
            return 1.0;
        }
        let successes = self.success_count.load(Ordering::Relaxed);
        successes as f64 / calls as f64
    }

    /// Get the effectiveness score as a float (0.0 to 1.0).
    pub fn effectiveness_f32(&self) -> f32 {
        f32::from_bits(self.effectiveness.load(Ordering::Relaxed))
    }

    /// Set the effectiveness score.
    pub fn set_effectiveness(&self, score: f32) {
        self.effectiveness.store(score.to_bits(), Ordering::Relaxed);
    }

    /// Auto-update effectiveness from the current success rate.
    ///
    /// Effectiveness = success_count / call_count, clamped to [0, 1].
    /// This ensures the anomaly detector has accurate data without
    /// requiring external code to call `set_effectiveness`.
    fn update_effectiveness(&self) {
        let calls = self.call_count.load(Ordering::Relaxed);
        if calls == 0 {
            return;
        }
        let successes = self.success_count.load(Ordering::Relaxed);
        let rate = (successes as f32) / (calls as f32);
        self.effectiveness.store(rate.to_bits(), Ordering::Relaxed);
    }

    /// Whether this tool should be retired (low effectiveness after enough calls).
    pub fn should_retire(&self, min_calls: u64, threshold: f32) -> bool {
        let calls = self.call_count.load(Ordering::Relaxed);
        if calls < min_calls {
            return false;
        }
        self.effectiveness_f32() < threshold
    }

    /// Whether this tool is hot (high call count).
    pub fn is_hot(&self, threshold: u64) -> bool {
        self.call_count.load(Ordering::Relaxed) > threshold
    }

    /// Restore stats from a persisted snapshot.
    ///
    /// Used on startup to rehydrate cross-restart usage data so tools
    /// like `tools.usage_report` can rank on cumulative history instead
    /// of only the current process lifetime. Counters are overwritten,
    /// not merged — call this before any dispatches are recorded.
    pub fn restore(&self, snap: &ToolStatsSnapshot) {
        self.call_count.store(snap.call_count, Ordering::Relaxed);
        self.success_count
            .store(snap.success_count, Ordering::Relaxed);
        self.p50_latency_ns
            .store(snap.p50_latency_ns, Ordering::Relaxed);
        self.peak_latency_ns
            .store(snap.peak_latency_ns, Ordering::Relaxed);
        self.cpu_time_ns.store(snap.cpu_time_ns, Ordering::Relaxed);
        self.lmdb_pages_touched
            .store(snap.lmdb_pages_touched, Ordering::Relaxed);
        self.last_used_unix
            .store(snap.last_used_unix, Ordering::Relaxed);
        self.effectiveness
            .store(snap.effectiveness.to_bits(), Ordering::Relaxed);
    }

    /// Get a snapshot of all stats as a serializable struct.
    pub fn snapshot(&self) -> ToolStatsSnapshot {
        ToolStatsSnapshot {
            call_count: self.call_count.load(Ordering::Relaxed),
            success_count: self.success_count.load(Ordering::Relaxed),
            p50_latency_ns: self.p50_latency_ns.load(Ordering::Relaxed),
            peak_latency_ns: self.peak_latency_ns.load(Ordering::Relaxed),
            cpu_time_ns: self.cpu_time_ns.load(Ordering::Relaxed),
            lmdb_pages_touched: self.lmdb_pages_touched.load(Ordering::Relaxed),
            last_used_unix: self.last_used_unix.load(Ordering::Relaxed),
            effectiveness: self.effectiveness_f32(),
        }
    }
}

/// A serializable snapshot of tool statistics.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ToolStatsSnapshot {
    /// Total number of calls
    pub call_count: u64,
    /// Number of successful calls
    pub success_count: u64,
    /// Central latency estimate in nanoseconds (EWMA).
    pub p50_latency_ns: u64,
    /// Highest latency seen in nanoseconds.
    pub peak_latency_ns: u64,
    /// Total CPU time consumed in nanoseconds
    pub cpu_time_ns: u64,
    /// Total LMDB pages touched
    pub lmdb_pages_touched: u64,
    /// Unix timestamp of last use
    pub last_used_unix: u64,
    /// Karma-weighted effectiveness score (0.0 to 1.0)
    pub effectiveness: f32,
}

/// The core tool trait. Every `WhiteMagic` tool implements this.
///
/// Tools declare their Gana affiliation and effect row, then implement
/// the `call` method. The dispatch pipeline handles routing, governance,
/// and statistics tracking.
#[async_trait]
pub trait Tool: Send + Sync {
    /// Unique tool name (e.g., "memory.create", "search.hybrid")
    fn name(&self) -> &str;

    /// Which Gana this tool belongs to.
    fn gana(&self) -> crate::Gana;

    /// Effect row — what this tool does to the world.
    fn effects(&self) -> &crate::EffectRow;

    /// Execute the tool.
    async fn call(&self, ctx: &mut crate::Context, args: Args) -> crate::Result<Output>;

    /// Access this tool's statistics.
    fn stats(&self) -> &ToolStats;

    /// Human-readable description.
    fn description(&self) -> &str {
        self.gana().description()
    }

    /// JSON-Schema-style description of the accepted arguments.
    ///
    /// Defaults to an empty object (no schema). Curated tools override this
    /// so `tools.list` can show clients the argument contract.
    fn input_schema(&self) -> serde_json::Value {
        serde_json::json!({})
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stats_record_success() {
        let stats = ToolStats::default();
        stats.record_success(Duration::from_millis(5), Duration::from_millis(3));
        assert_eq!(stats.call_count.load(Ordering::Relaxed), 1);
        assert_eq!(stats.success_count.load(Ordering::Relaxed), 1);
        assert_eq!(stats.success_rate(), 1.0);
    }

    #[test]
    fn stats_record_failure() {
        let stats = ToolStats::default();
        stats.record_success(Duration::from_millis(5), Duration::from_millis(3));
        stats.record_failure(Duration::from_millis(2));
        assert_eq!(stats.call_count.load(Ordering::Relaxed), 2);
        assert_eq!(stats.success_count.load(Ordering::Relaxed), 1);
        assert_eq!(stats.success_rate(), 0.5);
    }

    #[test]
    fn stats_should_retire() {
        let stats = ToolStats::default();
        // 2 successes + 13 failures = 0.125 effectiveness (< 0.2 threshold)
        for _ in 0..2 {
            stats.record_success(Duration::from_millis(1), Duration::from_millis(1));
        }
        for _ in 0..13 {
            stats.record_failure(Duration::from_millis(1));
        }
        assert!(stats.should_retire(10, 0.2));
    }

    #[test]
    fn stats_is_hot() {
        let stats = ToolStats::default();
        for _ in 0..1001 {
            stats.record_success(Duration::from_millis(1), Duration::from_millis(1));
        }
        assert!(stats.is_hot(1000));
    }

    #[test]
    fn stats_snapshot_restore_roundtrip() {
        let stats = ToolStats::default();
        stats.record_success(Duration::from_millis(5), Duration::from_millis(3));
        stats.record_failure(Duration::from_millis(2));
        let snap = stats.snapshot();

        let restored = ToolStats::default();
        restored.restore(&snap);
        assert_eq!(restored.call_count.load(Ordering::Relaxed), 2);
        assert_eq!(restored.success_count.load(Ordering::Relaxed), 1);
        assert_eq!(
            restored.peak_latency_ns.load(Ordering::Relaxed),
            snap.peak_latency_ns
        );
        assert!((restored.effectiveness_f32() - 0.5).abs() < f32::EPSILON);
    }

    #[test]
    fn stats_track_peak_latency() {
        // Regression: the peak (formerly mislabeled "p99") field was never
        // updated, so the high-latency anomaly path could never fire.
        let stats = ToolStats::default();
        stats.record_success(Duration::from_millis(10), Duration::from_millis(1));
        assert_eq!(stats.peak_latency_ns.load(Ordering::Relaxed), 10_000_000);
        stats.record_failure(Duration::from_millis(25));
        assert_eq!(stats.peak_latency_ns.load(Ordering::Relaxed), 25_000_000);
        stats.record_success(Duration::from_millis(5), Duration::from_millis(1));
        assert_eq!(
            stats.peak_latency_ns.load(Ordering::Relaxed),
            25_000_000,
            "peak latency must never decrease"
        );
    }
}
