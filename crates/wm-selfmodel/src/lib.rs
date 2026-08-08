//! wm-selfmodel — Predictive introspection for WhiteMagic v5 (Phase R4).
//!
//! Tracks per-subsystem metrics over time, forecasts threshold crossings,
//! and feeds confidence signals back into the dispatch pipeline.
//!
//! Architecture:
//! - [`MetricTracker`] — per-metric ring buffer history with EWMA
//! - [`ForecastEngine`] — linear extrapolation + EWMA forecasting
//! - [`AlertEngine`] — threshold rules checked against forecasts
//! - [`ConfidenceCalibrator`] — overall system confidence from forecast accuracy
//! - [`SelfModel`] — top-level orchestrator
//!
//! The self-model is read-only from the dispatch pipeline (no feedback loops).
//! Confidence <0.5 triggers conservative dispatch (prefer cached results).

#![forbid(unsafe_code)]
#![allow(clippy::significant_drop_tightening)]

pub mod alert;
pub mod confidence;
pub mod forecast;
pub mod metrics;

pub use alert::{Alert, AlertEngine, AlertLevel, AlertRule, Comparison};
pub use confidence::ConfidenceCalibrator;
pub use forecast::{Forecast, ForecastEngine};
pub use metrics::{MetricKind, MetricSample, MetricTracker};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::sync::RwLock;

/// Cognitive metrics bundle — recorded after each imagination/research cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CognitiveMetrics {
    /// Imagination quality score (0.0–1.0).
    pub imagination_quality: f32,
    /// Research output rate (0.0–1.0).
    pub research_output: f32,
    /// Scenario confidence from MC rollout (0.0–1.0).
    pub scenario_confidence: f32,
    /// Simulation variance (0.0–1.0, lower is better).
    pub simulation_variance: f32,
}

/// Forecast for all cognitive metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CognitiveForecast {
    /// Forecast for imagination quality.
    pub imagination_quality: Option<Forecast>,
    /// Forecast for research output.
    pub research_output: Option<Forecast>,
    /// Forecast for scenario confidence.
    pub scenario_confidence: Option<Forecast>,
    /// Forecast for simulation variance.
    pub simulation_variance: Option<Forecast>,
}

impl CognitiveForecast {
    /// Whether all cognitive forecasts are available.
    #[must_use]
    pub const fn is_complete(&self) -> bool {
        self.imagination_quality.is_some()
            && self.research_output.is_some()
            && self.scenario_confidence.is_some()
            && self.simulation_variance.is_some()
    }

    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "imagination_quality": self.imagination_quality.as_ref().map(|f| f.predicted_value),
            "research_output": self.research_output.as_ref().map(|f| f.predicted_value),
            "scenario_confidence": self.scenario_confidence.as_ref().map(|f| f.predicted_value),
            "simulation_variance": self.simulation_variance.as_ref().map(|f| f.predicted_value),
        })
    }
}

/// Maximum number of historical samples kept per metric.
const DEFAULT_HISTORY_CAPACITY: usize = 256;

/// Top-level self-model — orchestrates metric tracking, forecasting,
/// alerting, and confidence calibration.
pub struct SelfModel {
    metrics: RwLock<MetricTracker>,
    forecast_engine: ForecastEngine,
    alert_engine: RwLock<AlertEngine>,
    calibrator: RwLock<ConfidenceCalibrator>,
}

impl SelfModel {
    /// Create a new self-model with default history capacity and alert rules.
    #[must_use]
    pub fn new() -> Self {
        Self::with_capacity(DEFAULT_HISTORY_CAPACITY)
    }

    /// Create a new self-model with the given history capacity per metric.
    #[must_use]
    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            metrics: RwLock::new(MetricTracker::new(capacity)),
            forecast_engine: ForecastEngine::new(),
            alert_engine: RwLock::new(AlertEngine::with_default_rules()),
            calibrator: RwLock::new(ConfidenceCalibrator::new()),
        }
    }

    /// Record a metric sample.
    pub fn record(&self, kind: MetricKind, value: f32) {
        let sample = MetricSample {
            kind,
            value,
            timestamp: Utc::now(),
        };
        if let Ok(mut metrics) = self.metrics.write() {
            metrics.record(sample);
        }
    }

    /// Record a metric sample with an explicit timestamp (for testing/replay).
    pub fn record_at(&self, kind: MetricKind, value: f32, timestamp: DateTime<Utc>) {
        let sample = MetricSample {
            kind,
            value,
            timestamp,
        };
        if let Ok(mut metrics) = self.metrics.write() {
            metrics.record(sample);
        }
    }

    /// Forecast a metric `horizon` samples into the future.
    #[must_use]
    pub fn forecast(&self, kind: MetricKind, horizon: usize) -> Option<Forecast> {
        let history = {
            let metrics = self.metrics.read().ok()?;
            let history = metrics.history(kind)?;
            if history.len() < 2 {
                return None;
            }
            history.clone()
        };
        Some(self.forecast_engine.forecast(&history, horizon))
    }

    /// Forecast all tracked metrics.
    #[must_use]
    pub fn forecast_all(&self, horizon: usize) -> Vec<(MetricKind, Forecast)> {
        let histories: Vec<(MetricKind, VecDeque<MetricSample>)> = {
            let metrics = self.metrics.read();
            let Ok(metrics) = metrics else {
                return Vec::new();
            };
            metrics
                .tracked_kinds()
                .filter_map(|kind| {
                    let history = metrics.history(kind)?;
                    if history.len() < 2 {
                        return None;
                    }
                    Some((kind, history.clone()))
                })
                .collect()
        };
        histories
            .into_iter()
            .map(|(kind, history)| (kind, self.forecast_engine.forecast(&history, horizon)))
            .collect()
    }

    /// Check all alert rules against current forecasts.
    #[must_use]
    pub fn check_alerts(&self) -> Vec<Alert> {
        // Extract histories and rules while holding locks, then release
        let histories: Vec<(MetricKind, VecDeque<MetricSample>)> = {
            let metrics = self.metrics.read();
            let Ok(metrics) = metrics else {
                return Vec::new();
            };
            metrics
                .tracked_kinds()
                .filter_map(|kind| {
                    let history = metrics.history(kind)?;
                    if history.len() < 2 {
                        return None;
                    }
                    Some((kind, history.clone()))
                })
                .collect()
        };

        let rules: Vec<AlertRule> = {
            let alert_engine = self.alert_engine.read();
            let Ok(alert_engine) = alert_engine else {
                return Vec::new();
            };
            alert_engine.rules().to_vec()
        };

        let mut alerts = Vec::new();
        for rule in &rules {
            if let Some((_, history)) = histories.iter().find(|(k, _)| *k == rule.metric) {
                let forecast = self.forecast_engine.forecast(history, rule.horizon);
                if let Some(alert) = AlertEngine::evaluate_rule(rule, &forecast) {
                    alerts.push(alert);
                }
            }
        }
        alerts
    }

    /// Get the overall system confidence (0.0–1.0).
    /// Confidence <0.5 triggers conservative dispatch.
    #[must_use]
    pub fn confidence(&self) -> f32 {
        let (current, accuracy) = {
            let metrics = self.metrics.read();
            let Ok(metrics) = metrics else {
                return 0.5;
            };

            // Get current values for all tracked metrics
            let current: Vec<(MetricKind, f32)> = metrics
                .tracked_kinds()
                .filter_map(|kind| metrics.latest(kind).map(|s| (kind, s.value)))
                .collect();

            if current.is_empty() {
                return 0.5;
            }

            let accuracy = self.compute_forecast_accuracy(&metrics);
            (current, accuracy)
        };

        if let Ok(mut calibrator) = self.calibrator.write() {
            calibrator.update(&current, accuracy);
            calibrator.confidence()
        } else {
            0.5
        }
    }

    /// Compute forecast accuracy by comparing past forecasts to actual values.
    fn compute_forecast_accuracy(&self, metrics: &MetricTracker) -> f32 {
        let mut total_error = 0.0_f32;
        let mut count = 0_u32;

        for kind in metrics.tracked_kinds() {
            let history = match metrics.history(kind) {
                Some(h) if h.len() >= 4 => h,
                _ => continue,
            };

            // Compare forecast from t-2 to actual at t-1
            let past: VecDeque<MetricSample> =
                history.iter().take(history.len() - 1).cloned().collect();
            let actual = history.back().unwrap().value;

            let forecast = self.forecast_engine.forecast(&past, 1);
            let error = (forecast.predicted_value - actual).abs() / actual.max(0.001);
            total_error += error.min(1.0);
            count += 1;
        }

        if count == 0 {
            return 0.5; // Unknown accuracy
        }

        let avg_error = total_error / count as f32;
        (1.0 - avg_error).clamp(0.0, 1.0)
    }

    /// Take a snapshot of the entire self-model state.
    #[must_use]
    pub fn snapshot(&self) -> SelfModelSnapshot {
        // Extract all data from metrics lock first
        let (metric_snapshots, histories): (
            Vec<MetricSnapshot>,
            Vec<(MetricKind, VecDeque<MetricSample>)>,
        ) = {
            let metrics = self.metrics.read();
            let Ok(metrics) = metrics else {
                return SelfModelSnapshot {
                    timestamp: Utc::now(),
                    confidence: 0.5,
                    metrics: Vec::new(),
                    alerts: Vec::new(),
                    forecasts: Vec::new(),
                };
            };

            let histories: Vec<(MetricKind, VecDeque<MetricSample>)> = metrics
                .tracked_kinds()
                .filter_map(|kind| {
                    let history = metrics.history(kind)?;
                    if history.len() < 2 {
                        return None;
                    }
                    Some((kind, history.clone()))
                })
                .collect();

            let metric_snapshots: Vec<MetricSnapshot> = metrics
                .tracked_kinds()
                .filter_map(|kind| {
                    let latest = metrics.latest(kind)?;
                    let hist = metrics.history(kind)?;
                    let values: Vec<f32> = hist.iter().map(|s| s.value).collect();
                    Some(MetricSnapshot {
                        kind,
                        current: latest.value,
                        min: values.iter().copied().fold(f32::INFINITY, f32::min),
                        max: values.iter().copied().fold(f32::NEG_INFINITY, f32::max),
                        avg: values.iter().copied().sum::<f32>() / values.len() as f32,
                        sample_count: values.len(),
                    })
                })
                .collect();

            (metric_snapshots, histories)
        };

        // Now compute forecasts without holding the lock
        let forecasts: Vec<(MetricKind, Forecast)> = histories
            .iter()
            .map(|(kind, history)| (*kind, self.forecast_engine.forecast(history, 5)))
            .collect();

        let confidence = self.confidence();
        let alerts = self.check_alerts();

        SelfModelSnapshot {
            timestamp: Utc::now(),
            confidence,
            metrics: metric_snapshots,
            alerts,
            forecasts,
        }
    }

    /// Add a custom alert rule.
    pub fn add_alert_rule(&self, rule: AlertRule) {
        if let Ok(mut engine) = self.alert_engine.write() {
            engine.add_rule(rule);
        }
    }

    /// Get the number of tracked metrics.
    #[must_use]
    pub fn tracked_count(&self) -> usize {
        self.metrics.read().map(|m| m.tracked_count()).unwrap_or(0)
    }

    /// Get the number of samples for a specific metric.
    #[must_use]
    pub fn sample_count(&self, kind: MetricKind) -> usize {
        self.metrics
            .read()
            .map(|m| m.sample_count(kind))
            .unwrap_or(0)
    }

    /// Record cognitive metrics from an imagination/research cycle.
    ///
    /// Convenience method that records all four cognitive metrics at once.
    pub fn record_cognitive(&self, metrics: &CognitiveMetrics) {
        self.record(MetricKind::ImaginationQuality, metrics.imagination_quality);
        self.record(MetricKind::ResearchOutput, metrics.research_output);
        self.record(MetricKind::ScenarioConfidence, metrics.scenario_confidence);
        self.record(MetricKind::SimulationVariance, metrics.simulation_variance);
    }

    /// Record cognitive metrics with an explicit timestamp (for testing/replay).
    pub fn record_cognitive_at(&self, metrics: &CognitiveMetrics, timestamp: DateTime<Utc>) {
        self.record_at(
            MetricKind::ImaginationQuality,
            metrics.imagination_quality,
            timestamp,
        );
        self.record_at(
            MetricKind::ResearchOutput,
            metrics.research_output,
            timestamp,
        );
        self.record_at(
            MetricKind::ScenarioConfidence,
            metrics.scenario_confidence,
            timestamp,
        );
        self.record_at(
            MetricKind::SimulationVariance,
            metrics.simulation_variance,
            timestamp,
        );
    }

    /// Forecast cognitive metrics `horizon` samples ahead.
    ///
    /// Returns forecasts for all four cognitive metrics that have enough history.
    #[must_use]
    pub fn forecast_cognitive(&self, horizon: usize) -> CognitiveForecast {
        CognitiveForecast {
            imagination_quality: self.forecast(MetricKind::ImaginationQuality, horizon),
            research_output: self.forecast(MetricKind::ResearchOutput, horizon),
            scenario_confidence: self.forecast(MetricKind::ScenarioConfidence, horizon),
            simulation_variance: self.forecast(MetricKind::SimulationVariance, horizon),
        }
    }

    /// Check cognitive-specific alert rules.
    ///
    /// Returns alerts for cognitive metrics only (imagination quality,
    /// research output, scenario confidence, simulation variance).
    #[must_use]
    pub fn check_cognitive_alerts(&self) -> Vec<Alert> {
        self.check_alerts()
            .into_iter()
            .filter(|a| {
                matches!(
                    a.metric,
                    MetricKind::ImaginationQuality
                        | MetricKind::ResearchOutput
                        | MetricKind::ScenarioConfidence
                        | MetricKind::SimulationVariance
                )
            })
            .collect()
    }
}

impl Default for SelfModel {
    fn default() -> Self {
        Self::new()
    }
}

/// A point-in-time snapshot of the self-model state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SelfModelSnapshot {
    /// When the snapshot was taken.
    pub timestamp: DateTime<Utc>,
    /// Overall system confidence (0.0–1.0).
    pub confidence: f32,
    /// Per-metric summaries.
    pub metrics: Vec<MetricSnapshot>,
    /// Active alerts.
    pub alerts: Vec<Alert>,
    /// Forecasts for all tracked metrics (5 samples ahead).
    pub forecasts: Vec<(MetricKind, Forecast)>,
}

/// Summary of a single metric's state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricSnapshot {
    /// Which metric.
    pub kind: MetricKind,
    /// Current (most recent) value.
    pub current: f32,
    /// Minimum value in history.
    pub min: f32,
    /// Maximum value in history.
    pub max: f32,
    /// Average value across all samples.
    pub avg: f32,
    /// Number of samples.
    pub sample_count: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn self_model_record_and_forecast() {
        let model = SelfModel::new();
        model.record(MetricKind::CpuLoad, 0.3);
        model.record(MetricKind::CpuLoad, 0.4);
        model.record(MetricKind::CpuLoad, 0.5);

        let forecast = model.forecast(MetricKind::CpuLoad, 3);
        assert!(forecast.is_some());
        let f = forecast.unwrap();
        assert!(f.predicted_value > 0.4);
        assert!(f.confidence > 0.0);
    }

    #[test]
    fn self_model_insufficient_data_returns_none() {
        let model = SelfModel::new();
        model.record(MetricKind::CpuLoad, 0.3);

        assert!(model.forecast(MetricKind::CpuLoad, 3).is_none());
    }

    #[test]
    fn self_model_confidence_no_data() {
        let model = SelfModel::new();
        let conf = model.confidence();
        assert_eq!(conf, 0.5);
    }

    #[test]
    fn self_model_confidence_with_data() {
        let model = SelfModel::new();
        for v in [0.1, 0.15, 0.12, 0.13, 0.11, 0.14] {
            model.record(MetricKind::CpuLoad, v);
        }
        let conf = model.confidence();
        assert!(conf > 0.0 && conf <= 1.0);
    }

    #[test]
    fn self_model_snapshot_empty() {
        let model = SelfModel::new();
        let snap = model.snapshot();
        assert_eq!(snap.metrics.len(), 0);
        assert_eq!(snap.alerts.len(), 0);
        assert_eq!(snap.forecasts.len(), 0);
    }

    #[test]
    fn self_model_snapshot_with_data() {
        let model = SelfModel::new();
        model.record(MetricKind::CpuLoad, 0.3);
        model.record(MetricKind::CpuLoad, 0.5);
        model.record(MetricKind::CpuLoad, 0.7);
        model.record(MetricKind::MemoryPressure, 0.2);
        model.record(MetricKind::MemoryPressure, 0.3);

        let snap = model.snapshot();
        assert_eq!(snap.metrics.len(), 2);
        assert!(snap.metrics.iter().any(|m| m.kind == MetricKind::CpuLoad));
        assert!(
            snap.metrics
                .iter()
                .any(|m| m.kind == MetricKind::MemoryPressure)
        );
        assert_eq!(snap.forecasts.len(), 2);
    }

    #[test]
    fn self_model_check_alerts_clear() {
        let model = SelfModel::new();
        for v in [0.1, 0.12, 0.11, 0.13, 0.12] {
            model.record(MetricKind::CpuLoad, v);
        }
        let alerts = model.check_alerts();
        // CPU load trending up slightly but shouldn't trigger critical alert
        assert!(!alerts.iter().any(|a| a.level == AlertLevel::Critical));
    }

    #[test]
    fn self_model_check_alerts_triggered() {
        let model = SelfModel::new();
        // CPU load trending toward 1.0 — should trigger warning/critical
        for v in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95] {
            model.record(MetricKind::CpuLoad, v);
        }
        let alerts = model.check_alerts();
        assert!(!alerts.is_empty());
        assert!(alerts.iter().any(|a| a.metric == MetricKind::CpuLoad));
    }

    #[test]
    fn self_model_tracked_count() {
        let model = SelfModel::new();
        model.record(MetricKind::CpuLoad, 0.3);
        model.record(MetricKind::MemoryPressure, 0.2);
        assert_eq!(model.tracked_count(), 2);
    }

    #[test]
    fn self_model_sample_count() {
        let model = SelfModel::new();
        model.record(MetricKind::CpuLoad, 0.3);
        model.record(MetricKind::CpuLoad, 0.4);
        model.record(MetricKind::CpuLoad, 0.5);
        assert_eq!(model.sample_count(MetricKind::CpuLoad), 3);
        assert_eq!(model.sample_count(MetricKind::MemoryPressure), 0);
    }

    #[test]
    fn self_model_add_custom_alert_rule() {
        let model = SelfModel::new();
        model.add_alert_rule(AlertRule {
            metric: MetricKind::ErrorRate,
            threshold: 0.1,
            comparison: Comparison::GreaterThan,
            horizon: 3,
            level: AlertLevel::Critical,
        });
        for v in [0.01, 0.02, 0.01, 0.02] {
            model.record(MetricKind::ErrorRate, v);
        }
        // Error rate is low, should not trigger
        let alerts = model.check_alerts();
        assert!(!alerts.iter().any(|a| a.metric == MetricKind::ErrorRate));
    }

    #[test]
    fn self_model_forecast_all() {
        let model = SelfModel::new();
        model.record(MetricKind::CpuLoad, 0.3);
        model.record(MetricKind::CpuLoad, 0.4);
        model.record(MetricKind::MemoryPressure, 0.2);
        model.record(MetricKind::MemoryPressure, 0.25);

        let forecasts = model.forecast_all(5);
        assert_eq!(forecasts.len(), 2);
    }

    #[test]
    fn self_model_default_impl() {
        let model = SelfModel::default();
        assert_eq!(model.tracked_count(), 0);
    }

    #[test]
    fn self_model_snapshot_serialization() {
        let model = SelfModel::new();
        model.record(MetricKind::CpuLoad, 0.3);
        model.record(MetricKind::CpuLoad, 0.5);
        let snap = model.snapshot();
        let json = serde_json::to_string(&snap).unwrap();
        let back: SelfModelSnapshot = serde_json::from_str(&json).unwrap();
        assert!((back.confidence - snap.confidence).abs() < 0.01);
    }

    // ── Cognitive metrics tests ──

    #[test]
    fn record_cognitive_records_all_four_metrics() {
        let model = SelfModel::new();
        let cm = CognitiveMetrics {
            imagination_quality: 0.7,
            research_output: 0.5,
            scenario_confidence: 0.8,
            simulation_variance: 0.1,
        };
        model.record_cognitive(&cm);
        assert_eq!(model.sample_count(MetricKind::ImaginationQuality), 1);
        assert_eq!(model.sample_count(MetricKind::ResearchOutput), 1);
        assert_eq!(model.sample_count(MetricKind::ScenarioConfidence), 1);
        assert_eq!(model.sample_count(MetricKind::SimulationVariance), 1);
    }

    #[test]
    fn forecast_cognitive_returns_forecasts() {
        let model = SelfModel::new();
        for i in 0..5 {
            let cm = CognitiveMetrics {
                imagination_quality: 0.5_f32.mul_add(i as f32 * 0.05, 0.0),
                research_output: 0.3_f32.mul_add(i as f32 * 0.02, 0.0),
                scenario_confidence: 0.6,
                simulation_variance: 0.15,
            };
            model.record_cognitive(&cm);
        }
        let forecast = model.forecast_cognitive(3);
        assert!(forecast.imagination_quality.is_some());
        assert!(forecast.research_output.is_some());
        assert!(forecast.scenario_confidence.is_some());
        assert!(forecast.simulation_variance.is_some());
        assert!(forecast.is_complete());
    }

    #[test]
    fn forecast_cognitive_insufficient_data() {
        let model = SelfModel::new();
        let cm = CognitiveMetrics {
            imagination_quality: 0.5,
            research_output: 0.3,
            scenario_confidence: 0.6,
            simulation_variance: 0.15,
        };
        model.record_cognitive(&cm);
        let forecast = model.forecast_cognitive(3);
        // Only 1 sample — not enough for forecast
        assert!(!forecast.is_complete());
    }

    #[test]
    fn check_cognitive_alerts_filters_cognitive_only() {
        let model = SelfModel::new();
        // Record declining imagination quality (should trigger warning)
        for v in [0.7, 0.6, 0.5, 0.4, 0.3, 0.2] {
            model.record(MetricKind::ImaginationQuality, v);
        }
        // Also record CPU load (should not appear in cognitive alerts)
        for v in [0.1, 0.12, 0.11, 0.13, 0.12] {
            model.record(MetricKind::CpuLoad, v);
        }
        let cognitive_alerts = model.check_cognitive_alerts();
        assert!(!cognitive_alerts.is_empty());
        // All alerts should be for cognitive metrics only
        assert!(cognitive_alerts.iter().all(|a| {
            matches!(
                a.metric,
                MetricKind::ImaginationQuality
                    | MetricKind::ResearchOutput
                    | MetricKind::ScenarioConfidence
                    | MetricKind::SimulationVariance
            )
        }));
    }

    #[test]
    fn cognitive_metrics_serialization() {
        let cm = CognitiveMetrics {
            imagination_quality: 0.7,
            research_output: 0.5,
            scenario_confidence: 0.8,
            simulation_variance: 0.1,
        };
        let json = serde_json::to_string(&cm).unwrap();
        let back: CognitiveMetrics = serde_json::from_str(&json).unwrap();
        assert!((back.imagination_quality - 0.7).abs() < 0.001);
        assert!((back.research_output - 0.5).abs() < 0.001);
    }

    #[test]
    fn cognitive_forecast_to_json() {
        let model = SelfModel::new();
        for i in 0..3 {
            let cm = CognitiveMetrics {
                imagination_quality: 0.5_f32.mul_add(i as f32 * 0.1, 0.0),
                research_output: 0.3,
                scenario_confidence: 0.6,
                simulation_variance: 0.15,
            };
            model.record_cognitive(&cm);
        }
        let forecast = model.forecast_cognitive(2);
        let json = forecast.to_json();
        assert!(json["imagination_quality"].as_f64().is_some());
    }

    #[test]
    fn simulation_variance_higher_is_better_false() {
        assert!(!MetricKind::SimulationVariance.higher_is_better());
    }

    #[test]
    fn imagination_quality_higher_is_better_true() {
        assert!(MetricKind::ImaginationQuality.higher_is_better());
        assert!(MetricKind::ResearchOutput.higher_is_better());
        assert!(MetricKind::ScenarioConfidence.higher_is_better());
    }

    #[test]
    fn cognitive_metric_thresholds() {
        assert_eq!(MetricKind::ImaginationQuality.default_warning(), 0.4);
        assert_eq!(MetricKind::ImaginationQuality.default_critical(), 0.2);
        assert_eq!(MetricKind::SimulationVariance.default_warning(), 0.3);
        assert_eq!(MetricKind::SimulationVariance.default_critical(), 0.5);
    }

    #[test]
    fn record_cognitive_at_with_timestamp() {
        let model = SelfModel::new();
        let ts = Utc::now();
        let cm = CognitiveMetrics {
            imagination_quality: 0.7,
            research_output: 0.5,
            scenario_confidence: 0.8,
            simulation_variance: 0.1,
        };
        model.record_cognitive_at(&cm, ts);
        assert_eq!(model.sample_count(MetricKind::ImaginationQuality), 1);
    }
}
