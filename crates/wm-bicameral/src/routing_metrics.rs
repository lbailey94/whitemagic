//! Routing Observability — rolling-window metrics for inference routing.
//!
//! Ported from v2's inference/routing_metrics.py.
//! Tracks per-tier request counts, latency percentiles (p50/p95/p99),
//! escalation rates, confidence distributions, and routing decision reasons.
//! Provides drift detection and adaptive threshold recommendations.

use std::collections::{HashMap, VecDeque};
use std::time::Instant;

use crate::router::InferenceTier;

const WINDOW_SIZE: usize = 1000;

/// Statistics for a single inference tier.
#[derive(Debug)]
pub struct TierStats {
    pub total_requests: u64,
    pub successful: u64,
    pub failed: u64,
    pub escalated: u64,
    latencies: VecDeque<f64>,
    confidences: VecDeque<f64>,
    decision_reasons: HashMap<String, u64>,
}

impl TierStats {
    /// Create empty tier stats.
    #[must_use]
    pub fn new() -> Self {
        Self {
            total_requests: 0,
            successful: 0,
            failed: 0,
            escalated: 0,
            latencies: VecDeque::with_capacity(WINDOW_SIZE),
            confidences: VecDeque::with_capacity(WINDOW_SIZE),
            decision_reasons: HashMap::new(),
        }
    }

    /// Success rate (0.0–1.0).
    #[must_use]
    pub fn success_rate(&self) -> f64 {
        if self.total_requests == 0 {
            0.0
        } else {
            self.successful as f64 / self.total_requests as f64
        }
    }

    /// Escalation rate (0.0–1.0).
    #[must_use]
    pub fn escalation_rate(&self) -> f64 {
        if self.total_requests == 0 {
            0.0
        } else {
            self.escalated as f64 / self.total_requests as f64
        }
    }

    /// Record a routing outcome.
    pub fn record(&mut self, latency_ms: f64, confidence: f64, success: bool, reason: &str) {
        self.total_requests += 1;
        if self.latencies.len() >= WINDOW_SIZE {
            self.latencies.pop_front();
        }
        self.latencies.push_back(latency_ms);
        if self.confidences.len() >= WINDOW_SIZE {
            self.confidences.pop_front();
        }
        self.confidences.push_back(confidence);
        if success {
            self.successful += 1;
        } else {
            self.failed += 1;
        }
        if !reason.is_empty() {
            *self.decision_reasons.entry(reason.to_string()).or_insert(0) += 1;
        }
    }

    /// Record an escalation from this tier.
    pub const fn record_escalation(&mut self) {
        self.escalated += 1;
    }

    /// 50th percentile latency in ms.
    #[must_use]
    pub fn p50(&self) -> f64 {
        self.percentile(50)
    }

    /// 95th percentile latency in ms.
    #[must_use]
    pub fn p95(&self) -> f64 {
        self.percentile(95)
    }

    /// 99th percentile latency in ms.
    #[must_use]
    pub fn p99(&self) -> f64 {
        self.percentile(99)
    }

    /// Average confidence (0.0–1.0).
    #[must_use]
    pub fn avg_confidence(&self) -> f64 {
        if self.confidences.is_empty() {
            0.0
        } else {
            self.confidences.iter().sum::<f64>() / self.confidences.len() as f64
        }
    }

    fn percentile(&self, p: u32) -> f64 {
        if self.latencies.is_empty() {
            return 0.0;
        }
        let mut sorted: Vec<f64> = self.latencies.iter().copied().collect();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let idx = (sorted.len() * p as usize) / 100;
        sorted[idx.min(sorted.len() - 1)]
    }

    /// Top N decision reasons by count.
    #[must_use]
    pub fn top_reasons(&self, n: usize) -> Vec<(String, u64)> {
        let mut reasons: Vec<(String, u64)> = self
            .decision_reasons
            .iter()
            .map(|(k, &v)| (k.clone(), v))
            .collect();
        reasons.sort_by_key(|x| std::cmp::Reverse(x.1));
        reasons.truncate(n);
        reasons
    }
}

impl Default for TierStats {
    fn default() -> Self {
        Self::new()
    }
}

/// Rolling-window metrics for inference routing decisions.
///
/// All operations are O(1) except percentile calculations which are
/// O(n log n) on a bounded window (max 1000 samples).
pub struct RoutingMetrics {
    tier_stats: HashMap<InferenceTier, TierStats>,
    total_routed: u64,
    total_escalations: u64,
    start_time: Instant,
}

impl Default for RoutingMetrics {
    fn default() -> Self {
        Self::new()
    }
}

impl RoutingMetrics {
    /// Create a new routing metrics collector.
    #[must_use]
    pub fn new() -> Self {
        let mut tier_stats = HashMap::new();
        for tier in InferenceTier::all() {
            tier_stats.insert(tier, TierStats::new());
        }
        Self {
            tier_stats,
            total_routed: 0,
            total_escalations: 0,
            start_time: Instant::now(),
        }
    }

    /// Record a routing decision and its outcome.
    pub fn record_routing(
        &mut self,
        tier: InferenceTier,
        latency_ms: f64,
        confidence: f64,
        success: bool,
        reason: &str,
    ) {
        self.total_routed += 1;
        if let Some(stats) = self.tier_stats.get_mut(&tier) {
            stats.record(latency_ms, confidence, success, reason);
        }
    }

    /// Record an escalation from one tier to a higher one.
    pub fn record_escalation(
        &mut self,
        from_tier: InferenceTier,
        _to_tier: InferenceTier,
        _reason: &str,
    ) {
        self.total_escalations += 1;
        if let Some(stats) = self.tier_stats.get_mut(&from_tier) {
            stats.record_escalation();
        }
    }

    /// Get stats for a specific tier.
    #[must_use]
    pub fn tier_stats(&self, tier: InferenceTier) -> Option<&TierStats> {
        self.tier_stats.get(&tier)
    }

    /// Total number of routed requests.
    #[must_use]
    pub const fn total_routed(&self) -> u64 {
        self.total_routed
    }

    /// Total number of escalations.
    #[must_use]
    pub const fn total_escalations(&self) -> u64 {
        self.total_escalations
    }

    /// Overall escalation rate (0.0–1.0).
    #[must_use]
    pub fn overall_escalation_rate(&self) -> f64 {
        if self.total_routed == 0 {
            0.0
        } else {
            self.total_escalations as f64 / self.total_routed as f64
        }
    }

    /// Uptime in seconds.
    #[must_use]
    pub fn uptime_seconds(&self) -> f64 {
        self.start_time.elapsed().as_secs_f64()
    }

    /// Detect routing threshold drift.
    ///
    /// Checks if escalation rates have shifted significantly from the
    /// historical baseline, which may indicate routing thresholds need
    /// retuning.
    #[must_use]
    pub fn detect_drift(&self, window: u64) -> DriftReport {
        let mut recommendations = Vec::new();

        for tier in InferenceTier::all() {
            if let Some(stats) = self.tier_stats.get(&tier) {
                if stats.total_requests < window * 2 {
                    continue;
                }

                let historical_rate = stats.escalation_rate();
                // Approximate recent rate: compare escalated in recent window
                let recent_escalations = stats.escalated.min(window);
                let recent_rate = recent_escalations as f64 / window as f64;

                if historical_rate > 0.0 && (recent_rate - historical_rate).abs() > 0.15 {
                    recommendations.push(DriftRecommendation {
                        tier,
                        historical_rate,
                        recent_rate,
                    });
                }
            }
        }

        let status = if recommendations.is_empty() {
            DriftStatus::Ok
        } else {
            DriftStatus::DriftDetected
        };

        DriftReport {
            status,
            recommendations,
        }
    }

    /// Compute adaptive confidence thresholds based on observed performance.
    ///
    /// If a tier has high success rate and low escalation, lower the threshold
    /// (keep more requests at that tier). If escalation rate is high, raise the
    /// threshold (send fewer requests to that tier).
    #[must_use]
    pub fn adaptive_thresholds(&self) -> HashMap<InferenceTier, f32> {
        let base_threshold = 0.85_f32;
        let mut result = HashMap::new();

        for tier in InferenceTier::all() {
            if let Some(stats) = self.tier_stats.get(&tier) {
                if stats.total_requests < 20 {
                    result.insert(tier, base_threshold);
                    continue;
                }

                let esc_rate = stats.escalation_rate();
                let succ_rate = stats.success_rate();

                let adjustment = if esc_rate > 0.3 {
                    0.05 // Raise threshold
                } else if esc_rate < 0.05 && succ_rate > 0.9 {
                    -0.05 // Lower threshold
                } else {
                    0.0
                };

                let recommended = (base_threshold + adjustment).clamp(0.5, 0.99);
                result.insert(tier, recommended);
            } else {
                result.insert(tier, base_threshold);
            }
        }

        result
    }
}

/// Drift detection status.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DriftStatus {
    /// No drift detected
    Ok,
    /// Drift detected — thresholds may need retuning
    DriftDetected,
}

/// A single drift recommendation.
#[derive(Debug, Clone)]
pub struct DriftRecommendation {
    /// Tier with detected drift
    pub tier: InferenceTier,
    /// Historical escalation rate
    pub historical_rate: f64,
    /// Recent escalation rate
    pub recent_rate: f64,
}

/// Result of drift detection.
#[derive(Debug, Clone)]
pub struct DriftReport {
    /// Overall drift status
    pub status: DriftStatus,
    /// Per-tier drift recommendations
    pub recommendations: Vec<DriftRecommendation>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tier_stats_empty() {
        let stats = TierStats::new();
        assert_eq!(stats.total_requests, 0);
        assert_eq!(stats.success_rate(), 0.0);
        assert_eq!(stats.escalation_rate(), 0.0);
        assert_eq!(stats.p50(), 0.0);
        assert_eq!(stats.avg_confidence(), 0.0);
    }

    #[test]
    fn tier_stats_record() {
        let mut stats = TierStats::new();
        stats.record(50.0, 0.9, true, "low_complexity");
        stats.record(100.0, 0.7, true, "low_complexity");
        stats.record(200.0, 0.5, false, "timeout");

        assert_eq!(stats.total_requests, 3);
        assert_eq!(stats.successful, 2);
        assert_eq!(stats.failed, 1);
        assert!((stats.success_rate() - 2.0 / 3.0).abs() < 0.01);
    }

    #[test]
    fn tier_stats_percentiles() {
        let mut stats = TierStats::new();
        for i in 1..=100 {
            stats.record(f64::from(i), 0.8, true, "");
        }
        assert!(stats.p50() > 0.0);
        assert!(stats.p95() >= stats.p50());
        assert!(stats.p99() >= stats.p95());
    }

    #[test]
    fn tier_stats_escalation() {
        let mut stats = TierStats::new();
        stats.record(50.0, 0.9, true, "");
        stats.record(100.0, 0.5, true, "");
        stats.record_escalation();

        assert_eq!(stats.escalated, 1);
        assert!((stats.escalation_rate() - 0.5).abs() < 0.01);
    }

    #[test]
    fn tier_stats_top_reasons() {
        let mut stats = TierStats::new();
        stats.record(50.0, 0.9, true, "fast");
        stats.record(50.0, 0.9, true, "fast");
        stats.record(50.0, 0.9, true, "slow");

        let top = stats.top_reasons(5);
        assert_eq!(top.len(), 2);
        assert_eq!(top[0].0, "fast");
        assert_eq!(top[0].1, 2);
    }

    #[test]
    fn routing_metrics_record() {
        let mut metrics = RoutingMetrics::new();
        metrics.record_routing(InferenceTier::EdgeRules, 0.5, 0.95, true, "pattern_match");
        metrics.record_routing(InferenceTier::LocalSmall, 100.0, 0.8, true, "moderate");

        assert_eq!(metrics.total_routed(), 2);
        assert_eq!(metrics.total_escalations(), 0);
    }

    #[test]
    fn routing_metrics_escalation() {
        let mut metrics = RoutingMetrics::new();
        metrics.record_routing(InferenceTier::EdgeRules, 0.5, 0.3, false, "low_confidence");
        metrics.record_escalation(
            InferenceTier::EdgeRules,
            InferenceTier::LocalSmall,
            "low_confidence",
        );

        assert_eq!(metrics.total_escalations(), 1);
        assert!((metrics.overall_escalation_rate() - 1.0).abs() < f64::from(f32::EPSILON));
    }

    #[test]
    fn routing_metrics_adaptive_thresholds() {
        let mut metrics = RoutingMetrics::new();

        // Record many successful low-escalation requests
        for _ in 0..30 {
            metrics.record_routing(InferenceTier::EdgeRules, 0.5, 0.95, true, "");
        }

        let thresholds = metrics.adaptive_thresholds();
        let edge_threshold = thresholds[&InferenceTier::EdgeRules];
        // High success, low escalation → threshold should be lowered
        assert!(edge_threshold < 0.85);
    }

    #[test]
    fn routing_metrics_adaptive_thresholds_high_escalation() {
        let mut metrics = RoutingMetrics::new();

        // Record requests with high escalation
        for _ in 0..30 {
            metrics.record_routing(InferenceTier::LocalSmall, 100.0, 0.5, true, "");
            metrics.record_escalation(InferenceTier::LocalSmall, InferenceTier::LocalLarge, "");
        }

        let thresholds = metrics.adaptive_thresholds();
        let threshold = thresholds[&InferenceTier::LocalSmall];
        // High escalation → threshold should be raised
        assert!(threshold > 0.85);
    }

    #[test]
    fn routing_metrics_drift_ok() {
        let mut metrics = RoutingMetrics::new();
        for _ in 0..200 {
            metrics.record_routing(InferenceTier::EdgeRules, 0.5, 0.9, true, "");
        }
        let report = metrics.detect_drift(100);
        assert_eq!(report.status, DriftStatus::Ok);
    }

    #[test]
    fn routing_metrics_tier_stats_access() {
        let mut metrics = RoutingMetrics::new();
        metrics.record_routing(InferenceTier::Cloud, 5000.0, 0.99, true, "complex");
        let stats = metrics.tier_stats(InferenceTier::Cloud).unwrap();
        assert_eq!(stats.total_requests, 1);
    }
}
