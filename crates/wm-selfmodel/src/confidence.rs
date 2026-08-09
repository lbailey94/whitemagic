//! Confidence calibration — overall system confidence from metrics and forecast accuracy.

use crate::metrics::MetricKind;

/// Confidence calibrator — computes overall system confidence (0.0–1.0)
/// from current metric values and forecast accuracy.
///
/// Confidence is used by the dispatch pipeline:
/// - <0.5 → conservative mode (prefer cached results, avoid risky operations)
/// - ≥0.5 → normal mode
///
/// The calibrator weights metrics by importance:
/// - Error rate (30%) — high weight, directly impacts reliability
/// - Coherence (20%) — cognitive stability
/// - CPU load (15%) — resource headroom
/// - Memory pressure (15%) — resource headroom
/// - Latency (10%) — responsiveness
/// - Swap/disk I/O (10%) — I/O health
pub struct ConfidenceCalibrator {
    /// Last computed confidence.
    last_confidence: f32,
    /// Smoothing factor for confidence (0.0–1.0).
    /// Higher = faster adaptation to new values.
    smoothing: f32,
}

impl ConfidenceCalibrator {
    /// Create a new calibrator with default smoothing (0.2).
    #[must_use]
    pub const fn new() -> Self {
        Self {
            last_confidence: 0.5,
            smoothing: 0.2,
        }
    }

    /// Create with custom smoothing factor.
    #[must_use]
    pub const fn with_smoothing(smoothing: f32) -> Self {
        Self {
            last_confidence: 0.5,
            smoothing: smoothing.clamp(0.0, 1.0),
        }
    }

    /// Update the calibrator with current metric values and forecast accuracy.
    pub fn update(&mut self, metrics: &[(MetricKind, f32)], forecast_accuracy: f32) {
        let raw = Self::compute_raw(metrics, forecast_accuracy);
        // Exponential smoothing to avoid sudden jumps
        self.last_confidence = self
            .smoothing
            .mul_add(raw, (1.0 - self.smoothing) * self.last_confidence);
    }

    /// Get the current confidence value (0.0–1.0).
    #[must_use]
    pub const fn confidence(&self) -> f32 {
        self.last_confidence.clamp(0.0, 1.0)
    }

    /// Compute raw confidence from metrics and forecast accuracy.
    /// This is the instantaneous value before smoothing.
    fn compute_raw(metrics: &[(MetricKind, f32)], forecast_accuracy: f32) -> f32 {
        let mut weighted_sum = 0.0_f32;
        let mut total_weight = 0.0_f32;

        for &(kind, value) in metrics {
            let (score, weight) = Self::metric_score(kind, value);
            weighted_sum += score * weight;
            total_weight += weight;
        }

        // Include forecast accuracy (20% weight)
        weighted_sum += forecast_accuracy * 0.2;
        total_weight += 0.2;

        if total_weight < f32::EPSILON {
            return 0.5;
        }

        (weighted_sum / total_weight).clamp(0.0, 1.0)
    }

    /// Score a single metric (0.0–1.0) and return its weight.
    fn metric_score(kind: MetricKind, value: f32) -> (f32, f32) {
        match kind {
            MetricKind::ErrorRate => {
                // 0.0 errors = 1.0 confidence, 0.3+ errors = 0.0
                let score = (1.0 - value / 0.3).clamp(0.0, 1.0);
                (score, 0.30)
            }
            MetricKind::Coherence => {
                // Coherence is already 0.0–1.0, higher is better
                (value.clamp(0.0, 1.0), 0.20)
            }
            MetricKind::CpuLoad => {
                // 0.0 load = 1.0, 1.0 load = 0.0
                (1.0 - value.clamp(0.0, 1.0), 0.15)
            }
            MetricKind::MemoryPressure => (1.0 - value.clamp(0.0, 1.0), 0.15),
            MetricKind::Latency => {
                // 0ms = 1.0, 50ms+ = 0.0
                let score = (1.0 - value / 50.0).clamp(0.0, 1.0);
                (score, 0.10)
            }
            MetricKind::SwapUsage => (1.0 - value.clamp(0.0, 1.0), 0.05),
            MetricKind::DiskIo => (1.0 - value.clamp(0.0, 1.0), 0.05),
            // Cognitive metrics — higher is better (except variance)
            MetricKind::ImaginationQuality => (value.clamp(0.0, 1.0), 0.10),
            MetricKind::ResearchOutput => (value.clamp(0.0, 1.0), 0.08),
            MetricKind::ScenarioConfidence => (value.clamp(0.0, 1.0), 0.10),
            MetricKind::SimulationVariance => (1.0 - value.clamp(0.0, 1.0), 0.05),
            MetricKind::ConformalCoverage => (value.clamp(0.0, 1.0), 0.05),
        }
    }

    /// Whether the system is in conservative mode (confidence < 0.5).
    #[must_use]
    pub fn is_conservative(&self) -> bool {
        self.last_confidence < 0.5
    }
}

impl Default for ConfidenceCalibrator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn calibrator_default_confidence() {
        let cal = ConfidenceCalibrator::new();
        assert_eq!(cal.confidence(), 0.5);
        assert!(!cal.is_conservative());
    }

    #[test]
    fn calibrator_perfect_metrics() {
        let mut cal = ConfidenceCalibrator::with_smoothing(1.0);
        let metrics = vec![
            (MetricKind::ErrorRate, 0.0),
            (MetricKind::Coherence, 1.0),
            (MetricKind::CpuLoad, 0.0),
            (MetricKind::MemoryPressure, 0.0),
            (MetricKind::Latency, 0.0),
        ];
        cal.update(&metrics, 1.0);
        assert!(cal.confidence() > 0.7);
        assert!(!cal.is_conservative());
    }

    #[test]
    fn calibrator_terrible_metrics() {
        let mut cal = ConfidenceCalibrator::new();
        let metrics = vec![
            (MetricKind::ErrorRate, 0.5),
            (MetricKind::Coherence, 0.1),
            (MetricKind::CpuLoad, 0.95),
            (MetricKind::MemoryPressure, 0.9),
            (MetricKind::Latency, 60.0),
        ];
        cal.update(&metrics, 0.1);
        // With smoothing=0.2, first update won't drop to 0 immediately
        assert!(cal.confidence() < 0.5);
        assert!(cal.is_conservative());
    }

    #[test]
    fn calibrator_smoothing_prevents_jumps() {
        let mut cal = ConfidenceCalibrator::with_smoothing(0.2);
        // Start at 0.5, update with perfect metrics
        let good = vec![
            (MetricKind::ErrorRate, 0.0),
            (MetricKind::Coherence, 1.0),
            (MetricKind::CpuLoad, 0.0),
        ];
        cal.update(&good, 1.0);
        let after_one = cal.confidence();
        // Should have moved up but not to 1.0
        assert!(after_one > 0.5 && after_one < 0.95);

        // Second update should move further
        cal.update(&good, 1.0);
        let after_two = cal.confidence();
        assert!(after_two > after_one);
    }

    #[test]
    fn calibrator_no_smoothing() {
        let mut cal = ConfidenceCalibrator::with_smoothing(1.0);
        let metrics = vec![
            (MetricKind::ErrorRate, 0.0),
            (MetricKind::Coherence, 1.0),
            (MetricKind::CpuLoad, 0.0),
        ];
        cal.update(&metrics, 1.0);
        // With smoothing=1.0, should jump directly to raw value
        assert!(cal.confidence() > 0.8);
    }

    #[test]
    fn calibrator_empty_metrics() {
        let mut cal = ConfidenceCalibrator::new();
        cal.update(&[], 0.5);
        // Only forecast accuracy contributes (0.5 * 0.2 / 0.2 = 0.5)
        assert!((cal.confidence() - 0.5).abs() < 0.1);
    }

    #[test]
    fn calibrator_error_rate_dominates() {
        let mut cal = ConfidenceCalibrator::with_smoothing(1.0);
        // High error rate with good everything else
        let metrics = vec![
            (MetricKind::ErrorRate, 0.5),
            (MetricKind::Coherence, 1.0),
            (MetricKind::CpuLoad, 0.0),
            (MetricKind::MemoryPressure, 0.0),
            (MetricKind::Latency, 0.0),
        ];
        cal.update(&metrics, 1.0);
        // Error rate has 30% weight — 0.5 error rate → score 0.0 for that 30%
        // This should pull confidence down significantly
        assert!(cal.confidence() < 0.8);
    }

    #[test]
    fn calibrator_is_conservative_threshold() {
        let mut cal = ConfidenceCalibrator::with_smoothing(1.0);
        let metrics = vec![
            (MetricKind::ErrorRate, 0.3),
            (MetricKind::Coherence, 0.2),
            (MetricKind::CpuLoad, 0.8),
        ];
        cal.update(&metrics, 0.3);
        assert!(cal.is_conservative());
    }

    #[test]
    fn calibrator_clamps_to_valid_range() {
        let mut cal = ConfidenceCalibrator::with_smoothing(1.0);
        // Extreme values shouldn't produce out-of-range confidence
        let metrics = vec![
            (MetricKind::ErrorRate, 100.0), // Way above normal range
            (MetricKind::CpuLoad, 10.0),    // Way above 1.0
        ];
        cal.update(&metrics, 0.0);
        assert!(cal.confidence() >= 0.0 && cal.confidence() <= 1.0);
    }

    #[test]
    fn calibrator_with_smoothing_clamped() {
        let cal = ConfidenceCalibrator::with_smoothing(5.0);
        // Smoothing should be clamped to 1.0
        // With smoothing=1.0, first update jumps to raw value
        assert_eq!(cal.confidence(), 0.5); // Initial value
    }

    #[test]
    fn calibrator_latency_scoring() {
        // 0ms → 1.0, 25ms → 0.5, 50ms+ → 0.0
        let mut cal = ConfidenceCalibrator::with_smoothing(1.0);
        cal.update(&[(MetricKind::Latency, 0.0)], 1.0);
        // Only latency (0.10) + forecast_accuracy (0.20) = 0.30 total weight
        // latency score = 1.0, accuracy = 1.0 → 1.0
        assert!(cal.confidence() > 0.9);

        cal.update(&[(MetricKind::Latency, 50.0)], 1.0);
        // latency score = 0.0, accuracy = 1.0 → (0*0.1 + 1.0*0.2) / 0.3 = 0.667
        assert!(cal.confidence() < 0.9 && cal.confidence() > 0.5);
    }
}
