//! Metric tracking — per-subsystem performance metrics with ring buffer history.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

/// Kinds of metrics tracked by the self-model.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MetricKind {
    /// CPU load fraction (0.0 = idle, 1.0 = saturated).
    CpuLoad,
    /// Memory pressure fraction (0.0 = plenty, 1.0 = critical).
    MemoryPressure,
    /// Dispatch latency in milliseconds.
    Latency,
    /// Citta coherence score (0.0–1.0).
    Coherence,
    /// Tool error rate fraction (0.0 = no errors, 1.0 = all errors).
    ErrorRate,
    /// Disk I/O rate fraction (0.0 = idle, 1.0 = saturated).
    DiskIo,
    /// Swap usage fraction (0.0 = none, 1.0 = full).
    SwapUsage,
    // ── Cognitive metrics (Imagination Engine) ──
    /// Imagination quality score (0.0–1.0) — scenario evaluation score.
    ImaginationQuality,
    /// Research output rate (0.0–1.0) — hypotheses generated per cycle.
    ResearchOutput,
    /// Scenario confidence (0.0–1.0) — MC rollout positive fraction.
    ScenarioConfidence,
    /// Simulation variance (0.0–1.0) — MC std dev (lower is better).
    SimulationVariance,
}

impl MetricKind {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::CpuLoad => "cpu_load",
            Self::MemoryPressure => "memory_pressure",
            Self::Latency => "latency",
            Self::Coherence => "coherence",
            Self::ErrorRate => "error_rate",
            Self::DiskIo => "disk_io",
            Self::SwapUsage => "swap_usage",
            Self::ImaginationQuality => "imagination_quality",
            Self::ResearchOutput => "research_output",
            Self::ScenarioConfidence => "scenario_confidence",
            Self::SimulationVariance => "simulation_variance",
        }
    }

    /// All metric kinds.
    #[must_use]
    pub const fn all() -> &'static [Self] {
        &[
            Self::CpuLoad,
            Self::MemoryPressure,
            Self::Latency,
            Self::Coherence,
            Self::ErrorRate,
            Self::DiskIo,
            Self::SwapUsage,
            Self::ImaginationQuality,
            Self::ResearchOutput,
            Self::ScenarioConfidence,
            Self::SimulationVariance,
        ]
    }

    /// Whether higher values are better (true) or worse (false).
    #[must_use]
    pub const fn higher_is_better(self) -> bool {
        matches!(
            self,
            Self::Coherence
                | Self::ImaginationQuality
                | Self::ResearchOutput
                | Self::ScenarioConfidence
        )
    }

    /// Default warning threshold for this metric.
    #[must_use]
    pub const fn default_warning(self) -> f32 {
        match self {
            Self::CpuLoad | Self::MemoryPressure | Self::SwapUsage | Self::DiskIo => 0.7,
            Self::Latency => 10.0,
            Self::Coherence => 0.3, // Below this is bad
            Self::ErrorRate => 0.1,
            Self::ImaginationQuality => 0.4,
            Self::ResearchOutput => 0.3,
            Self::ScenarioConfidence => 0.4,
            Self::SimulationVariance => 0.3, // Above this is bad
        }
    }

    /// Default critical threshold for this metric.
    #[must_use]
    pub const fn default_critical(self) -> f32 {
        match self {
            Self::CpuLoad | Self::MemoryPressure | Self::SwapUsage | Self::DiskIo => 0.9,
            Self::Latency => 50.0,
            Self::Coherence => 0.1,
            Self::ErrorRate => 0.3,
            Self::ImaginationQuality => 0.2,
            Self::ResearchOutput => 0.1,
            Self::ScenarioConfidence => 0.2,
            Self::SimulationVariance => 0.5,
        }
    }
}

/// A single metric sample at a point in time.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricSample {
    /// Which metric.
    pub kind: MetricKind,
    /// Sampled value.
    pub value: f32,
    /// When the sample was taken.
    pub timestamp: DateTime<Utc>,
}

/// Per-metric ring buffer history tracker.
pub struct MetricTracker {
    /// Per-metric history (ring buffer).
    history: Vec<VecDeque<MetricSample>>,
    /// Maximum samples per metric.
    capacity: usize,
}

impl MetricTracker {
    /// Create a new metric tracker with the given capacity per metric.
    #[must_use]
    pub fn new(capacity: usize) -> Self {
        let mut history = Vec::with_capacity(MetricKind::all().len());
        for _ in MetricKind::all() {
            history.push(VecDeque::with_capacity(capacity));
        }
        Self { history, capacity }
    }

    /// Get the index for a metric kind.
    fn index(kind: MetricKind) -> usize {
        MetricKind::all()
            .iter()
            .position(|k| *k == kind)
            .unwrap_or(0)
    }

    /// Record a metric sample.
    pub fn record(&mut self, sample: MetricSample) {
        let idx = Self::index(sample.kind);
        let buf = &mut self.history[idx];
        if buf.len() >= self.capacity {
            buf.pop_front();
        }
        buf.push_back(sample);
    }

    /// Get the history for a metric kind (oldest first).
    #[must_use]
    pub fn history(&self, kind: MetricKind) -> Option<&VecDeque<MetricSample>> {
        let buf = &self.history[Self::index(kind)];
        if buf.is_empty() { None } else { Some(buf) }
    }

    /// Get the most recent sample for a metric kind.
    #[must_use]
    pub fn latest(&self, kind: MetricKind) -> Option<&MetricSample> {
        self.history(kind).and_then(|h| h.back())
    }

    /// Get the number of samples for a metric kind.
    #[must_use]
    pub fn sample_count(&self, kind: MetricKind) -> usize {
        self.history(kind)
            .map_or(0, std::collections::VecDeque::len)
    }

    /// Iterate over metric kinds that have at least one sample.
    pub fn tracked_kinds(&self) -> impl Iterator<Item = MetricKind> + '_ {
        MetricKind::all()
            .iter()
            .copied()
            .filter(|kind| self.sample_count(*kind) > 0)
    }

    /// Number of metrics with at least one sample.
    #[must_use]
    pub fn tracked_count(&self) -> usize {
        self.tracked_kinds().count()
    }

    /// Compute the EWMA (exponentially weighted moving average) for a metric.
    #[must_use]
    pub fn ewma(&self, kind: MetricKind, alpha: f32) -> Option<f32> {
        let history = self.history(kind)?;
        if history.is_empty() {
            return None;
        }

        let alpha = alpha.clamp(0.0, 1.0);
        let mut ewma = history.front().unwrap().value;
        for sample in history.iter().skip(1) {
            ewma = alpha.mul_add(sample.value, (1.0 - alpha) * ewma);
        }
        Some(ewma)
    }

    /// Compute the linear slope (rate of change) for a metric.
    /// Returns the slope per sample (positive = increasing).
    #[must_use]
    pub fn slope(&self, kind: MetricKind) -> Option<f32> {
        let history = self.history(kind)?;
        let n = history.len();
        if n < 2 {
            return None;
        }

        // Simple linear regression: slope = (y_n - y_1) / (n - 1)
        let first = history.front().unwrap().value;
        let last = history.back().unwrap().value;
        Some((last - first) / (n as f32 - 1.0))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn metric_kind_as_str() {
        assert_eq!(MetricKind::CpuLoad.as_str(), "cpu_load");
        assert_eq!(MetricKind::Coherence.as_str(), "coherence");
        assert_eq!(MetricKind::ErrorRate.as_str(), "error_rate");
    }

    #[test]
    fn metric_kind_higher_is_better() {
        assert!(MetricKind::Coherence.higher_is_better());
        assert!(!MetricKind::CpuLoad.higher_is_better());
        assert!(!MetricKind::ErrorRate.higher_is_better());
    }

    #[test]
    fn metric_kind_default_thresholds() {
        assert_eq!(MetricKind::CpuLoad.default_warning(), 0.7);
        assert_eq!(MetricKind::CpuLoad.default_critical(), 0.9);
        assert_eq!(MetricKind::Coherence.default_warning(), 0.3);
        assert_eq!(MetricKind::Coherence.default_critical(), 0.1);
    }

    #[test]
    fn metric_tracker_record_and_history() {
        let mut tracker = MetricTracker::new(100);
        tracker.record(MetricSample {
            kind: MetricKind::CpuLoad,
            value: 0.3,
            timestamp: Utc::now(),
        });
        tracker.record(MetricSample {
            kind: MetricKind::CpuLoad,
            value: 0.5,
            timestamp: Utc::now(),
        });

        let hist = tracker.history(MetricKind::CpuLoad).unwrap();
        assert_eq!(hist.len(), 2);
        assert_eq!(tracker.sample_count(MetricKind::CpuLoad), 2);
    }

    #[test]
    fn metric_tracker_empty_returns_none() {
        let tracker = MetricTracker::new(100);
        assert!(tracker.history(MetricKind::CpuLoad).is_none());
        assert!(tracker.latest(MetricKind::CpuLoad).is_none());
    }

    #[test]
    fn metric_tracker_latest() {
        let mut tracker = MetricTracker::new(100);
        tracker.record(MetricSample {
            kind: MetricKind::CpuLoad,
            value: 0.3,
            timestamp: Utc::now(),
        });
        tracker.record(MetricSample {
            kind: MetricKind::CpuLoad,
            value: 0.7,
            timestamp: Utc::now(),
        });
        let latest = tracker.latest(MetricKind::CpuLoad).unwrap();
        assert!((latest.value - 0.7).abs() < 0.001);
    }

    #[test]
    fn metric_tracker_ring_buffer_capacity() {
        let mut tracker = MetricTracker::new(3);
        for v in [0.1, 0.2, 0.3, 0.4, 0.5] {
            tracker.record(MetricSample {
                kind: MetricKind::CpuLoad,
                value: v,
                timestamp: Utc::now(),
            });
        }
        let hist = tracker.history(MetricKind::CpuLoad).unwrap();
        assert_eq!(hist.len(), 3);
        // Oldest should be 0.3 (first two evicted)
        assert!((hist.front().unwrap().value - 0.3).abs() < 0.001);
        // Newest should be 0.5
        assert!((hist.back().unwrap().value - 0.5).abs() < 0.001);
    }

    #[test]
    fn metric_tracker_tracked_kinds() {
        let mut tracker = MetricTracker::new(100);
        tracker.record(MetricSample {
            kind: MetricKind::CpuLoad,
            value: 0.3,
            timestamp: Utc::now(),
        });
        tracker.record(MetricSample {
            kind: MetricKind::MemoryPressure,
            value: 0.2,
            timestamp: Utc::now(),
        });

        let kinds: Vec<_> = tracker.tracked_kinds().collect();
        assert_eq!(kinds.len(), 2);
        assert!(kinds.contains(&MetricKind::CpuLoad));
        assert!(kinds.contains(&MetricKind::MemoryPressure));
        assert_eq!(tracker.tracked_count(), 2);
    }

    #[test]
    fn metric_tracker_ewma() {
        let mut tracker = MetricTracker::new(100);
        for v in [0.1, 0.2, 0.3, 0.4, 0.5] {
            tracker.record(MetricSample {
                kind: MetricKind::CpuLoad,
                value: v,
                timestamp: Utc::now(),
            });
        }
        let ewma = tracker.ewma(MetricKind::CpuLoad, 0.3).unwrap();
        // EWMA should be between first and last
        assert!(ewma > 0.1 && ewma < 0.5);
    }

    #[test]
    fn metric_tracker_ewma_alpha_clamped() {
        let mut tracker = MetricTracker::new(100);
        tracker.record(MetricSample {
            kind: MetricKind::CpuLoad,
            value: 0.5,
            timestamp: Utc::now(),
        });
        tracker.record(MetricSample {
            kind: MetricKind::CpuLoad,
            value: 0.9,
            timestamp: Utc::now(),
        });
        // Alpha > 1.0 should be clamped to 1.0 (just take latest)
        let ewma = tracker.ewma(MetricKind::CpuLoad, 2.0).unwrap();
        assert!((ewma - 0.9).abs() < 0.001);
    }

    #[test]
    fn metric_tracker_ewma_empty() {
        let tracker = MetricTracker::new(100);
        assert!(tracker.ewma(MetricKind::CpuLoad, 0.3).is_none());
    }

    #[test]
    fn metric_tracker_slope_increasing() {
        let mut tracker = MetricTracker::new(100);
        for v in [0.1, 0.2, 0.3, 0.4, 0.5] {
            tracker.record(MetricSample {
                kind: MetricKind::CpuLoad,
                value: v,
                timestamp: Utc::now(),
            });
        }
        let slope = tracker.slope(MetricKind::CpuLoad).unwrap();
        assert!(slope > 0.0);
        assert!((slope - 0.1).abs() < 0.001);
    }

    #[test]
    fn metric_tracker_slope_decreasing() {
        let mut tracker = MetricTracker::new(100);
        for v in [0.5, 0.4, 0.3, 0.2, 0.1] {
            tracker.record(MetricSample {
                kind: MetricKind::CpuLoad,
                value: v,
                timestamp: Utc::now(),
            });
        }
        let slope = tracker.slope(MetricKind::CpuLoad).unwrap();
        assert!(slope < 0.0);
    }

    #[test]
    fn metric_tracker_slope_insufficient_data() {
        let mut tracker = MetricTracker::new(100);
        tracker.record(MetricSample {
            kind: MetricKind::CpuLoad,
            value: 0.3,
            timestamp: Utc::now(),
        });
        assert!(tracker.slope(MetricKind::CpuLoad).is_none());
    }

    #[test]
    fn metric_sample_serialization() {
        let sample = MetricSample {
            kind: MetricKind::CpuLoad,
            value: 0.42,
            timestamp: Utc::now(),
        };
        let json = serde_json::to_string(&sample).unwrap();
        let back: MetricSample = serde_json::from_str(&json).unwrap();
        assert_eq!(back.kind, MetricKind::CpuLoad);
        assert!((back.value - 0.42).abs() < 0.001);
    }

    #[test]
    fn metric_kind_all_count() {
        assert_eq!(MetricKind::all().len(), 11);
    }
}
