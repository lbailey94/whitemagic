//! Alert engine — threshold rules checked against forecasts.

use serde::{Deserialize, Serialize};

use crate::forecast::Forecast;
use crate::metrics::MetricKind;

/// Alert severity level.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AlertLevel {
    /// Informational — metric approaching threshold.
    Info,
    /// Warning — metric will likely cross threshold soon.
    Warning,
    /// Critical — metric predicted to cross danger threshold.
    Critical,
}

impl AlertLevel {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Info => "info",
            Self::Warning => "warning",
            Self::Critical => "critical",
        }
    }
}

/// Comparison operator for threshold rules.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Comparison {
    /// Predicted value > threshold.
    GreaterThan,
    /// Predicted value < threshold.
    LessThan,
}

/// An alert rule — when a metric's forecast crosses a threshold, fire an alert.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertRule {
    /// Which metric to watch.
    pub metric: MetricKind,
    /// Threshold value.
    pub threshold: f32,
    /// Comparison direction.
    pub comparison: Comparison,
    /// How many samples ahead to forecast.
    pub horizon: usize,
    /// Alert level when triggered.
    pub level: AlertLevel,
}

/// An active alert — a rule that has been triggered.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alert {
    /// Which metric triggered the alert.
    pub metric: MetricKind,
    /// Alert level.
    pub level: AlertLevel,
    /// The forecasted value that triggered the alert.
    pub predicted_value: f32,
    /// The threshold that was crossed.
    pub threshold: f32,
    /// Human-readable message.
    pub message: String,
    /// Forecast confidence (0.0–1.0).
    pub confidence: f32,
}

/// Alert engine — holds rules and evaluates forecasts against them.
pub struct AlertEngine {
    rules: Vec<AlertRule>,
}

impl AlertEngine {
    /// Create an alert engine with default rules for all metrics.
    #[must_use]
    pub fn with_default_rules() -> Self {
        let mut rules = Vec::new();

        for kind in MetricKind::all() {
            // Warning rule
            rules.push(AlertRule {
                metric: *kind,
                threshold: kind.default_warning(),
                comparison: if kind.higher_is_better() {
                    Comparison::LessThan
                } else {
                    Comparison::GreaterThan
                },
                horizon: 5,
                level: AlertLevel::Warning,
            });

            // Critical rule
            rules.push(AlertRule {
                metric: *kind,
                threshold: kind.default_critical(),
                comparison: if kind.higher_is_better() {
                    Comparison::LessThan
                } else {
                    Comparison::GreaterThan
                },
                horizon: 5,
                level: AlertLevel::Critical,
            });
        }

        Self { rules }
    }

    /// Create an empty alert engine (no rules).
    #[must_use]
    pub const fn new() -> Self {
        Self { rules: Vec::new() }
    }

    /// Add a custom alert rule.
    pub fn add_rule(&mut self, rule: AlertRule) {
        self.rules.push(rule);
    }

    /// Get all rules.
    #[must_use]
    pub fn rules(&self) -> &[AlertRule] {
        &self.rules
    }

    /// Evaluate a forecast against a rule. Returns an alert if triggered.
    /// Static version that doesn't require &self (for use after releasing locks).
    #[must_use]
    pub fn evaluate_rule(rule: &AlertRule, forecast: &Forecast) -> Option<Alert> {
        Self::new().evaluate(rule, forecast)
    }

    /// Evaluate a forecast against a rule. Returns an alert if triggered.
    #[must_use]
    pub fn evaluate(&self, rule: &AlertRule, forecast: &Forecast) -> Option<Alert> {
        let triggered = match rule.comparison {
            Comparison::GreaterThan => forecast.predicted_value > rule.threshold,
            Comparison::LessThan => forecast.predicted_value < rule.threshold,
        };

        if !triggered {
            return None;
        }

        let direction = match rule.comparison {
            Comparison::GreaterThan => "exceed",
            Comparison::LessThan => "drops below",
        };

        let message = format!(
            "{} predicted to {} {:.3} within {} samples (threshold: {:.3}, confidence: {:.2})",
            rule.metric.as_str(),
            direction,
            forecast.predicted_value,
            rule.horizon,
            rule.threshold,
            forecast.confidence,
        );

        Some(Alert {
            metric: rule.metric,
            level: rule.level,
            predicted_value: forecast.predicted_value,
            threshold: rule.threshold,
            message,
            confidence: forecast.confidence,
        })
    }
}

impl Default for AlertEngine {
    fn default() -> Self {
        Self::with_default_rules()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_forecast(value: f32, confidence: f32) -> Forecast {
        Forecast {
            predicted_value: value,
            slope: 0.1,
            ewma: value - 0.05,
            confidence,
            horizon: 5,
        }
    }

    #[test]
    fn alert_level_as_str() {
        assert_eq!(AlertLevel::Info.as_str(), "info");
        assert_eq!(AlertLevel::Warning.as_str(), "warning");
        assert_eq!(AlertLevel::Critical.as_str(), "critical");
    }

    #[test]
    fn alert_engine_default_has_rules() {
        let engine = AlertEngine::with_default_rules();
        // 11 metrics * 2 rules (warning + critical) = 22
        assert_eq!(engine.rules().len(), 22);
    }

    #[test]
    fn alert_engine_empty() {
        let engine = AlertEngine::new();
        assert_eq!(engine.rules().len(), 0);
    }

    #[test]
    fn alert_engine_add_rule() {
        let mut engine = AlertEngine::new();
        engine.add_rule(AlertRule {
            metric: MetricKind::CpuLoad,
            threshold: 0.8,
            comparison: Comparison::GreaterThan,
            horizon: 3,
            level: AlertLevel::Warning,
        });
        assert_eq!(engine.rules().len(), 1);
    }

    #[test]
    fn alert_evaluate_greater_than_triggered() {
        let engine = AlertEngine::new();
        let rule = AlertRule {
            metric: MetricKind::CpuLoad,
            threshold: 0.7,
            comparison: Comparison::GreaterThan,
            horizon: 5,
            level: AlertLevel::Warning,
        };
        let forecast = make_forecast(0.85, 0.9);
        let alert = engine.evaluate(&rule, &forecast);
        assert!(alert.is_some());
        let alert = alert.unwrap();
        assert_eq!(alert.metric, MetricKind::CpuLoad);
        assert_eq!(alert.level, AlertLevel::Warning);
        assert!(alert.message.contains("cpu_load"));
    }

    #[test]
    fn alert_evaluate_greater_than_not_triggered() {
        let engine = AlertEngine::new();
        let rule = AlertRule {
            metric: MetricKind::CpuLoad,
            threshold: 0.9,
            comparison: Comparison::GreaterThan,
            horizon: 5,
            level: AlertLevel::Critical,
        };
        let forecast = make_forecast(0.5, 0.9);
        let alert = engine.evaluate(&rule, &forecast);
        assert!(alert.is_none());
    }

    #[test]
    fn alert_evaluate_less_than_triggered() {
        let engine = AlertEngine::new();
        let rule = AlertRule {
            metric: MetricKind::Coherence,
            threshold: 0.3,
            comparison: Comparison::LessThan,
            horizon: 5,
            level: AlertLevel::Warning,
        };
        let forecast = make_forecast(0.15, 0.8);
        let alert = engine.evaluate(&rule, &forecast);
        assert!(alert.is_some());
        let alert = alert.unwrap();
        assert_eq!(alert.metric, MetricKind::Coherence);
        assert!(alert.message.contains("coherence"));
        assert!(alert.message.contains("drops below"));
    }

    #[test]
    fn alert_evaluate_less_than_not_triggered() {
        let engine = AlertEngine::new();
        let rule = AlertRule {
            metric: MetricKind::Coherence,
            threshold: 0.3,
            comparison: Comparison::LessThan,
            horizon: 5,
            level: AlertLevel::Warning,
        };
        let forecast = make_forecast(0.8, 0.9);
        let alert = engine.evaluate(&rule, &forecast);
        assert!(alert.is_none());
    }

    #[test]
    fn alert_message_contains_direction() {
        let engine = AlertEngine::new();
        let rule = AlertRule {
            metric: MetricKind::CpuLoad,
            threshold: 0.7,
            comparison: Comparison::GreaterThan,
            horizon: 5,
            level: AlertLevel::Critical,
        };
        let forecast = make_forecast(0.95, 0.9);
        let alert = engine.evaluate(&rule, &forecast).unwrap();
        assert!(alert.message.contains("exceed"));
    }

    #[test]
    fn alert_serialization() {
        let alert = Alert {
            metric: MetricKind::CpuLoad,
            level: AlertLevel::Critical,
            predicted_value: 0.95,
            threshold: 0.9,
            message: "CPU load critical".to_string(),
            confidence: 0.9,
        };
        let json = serde_json::to_string(&alert).unwrap();
        let back: Alert = serde_json::from_str(&json).unwrap();
        assert_eq!(back.metric, MetricKind::CpuLoad);
        assert_eq!(back.level, AlertLevel::Critical);
        assert!((back.predicted_value - 0.95).abs() < 0.001);
    }

    #[test]
    fn alert_rule_serialization() {
        let rule = AlertRule {
            metric: MetricKind::ErrorRate,
            threshold: 0.1,
            comparison: Comparison::GreaterThan,
            horizon: 3,
            level: AlertLevel::Warning,
        };
        let json = serde_json::to_string(&rule).unwrap();
        let back: AlertRule = serde_json::from_str(&json).unwrap();
        assert_eq!(back.metric, MetricKind::ErrorRate);
        assert_eq!(back.comparison, Comparison::GreaterThan);
    }

    #[test]
    fn default_rules_cover_all_metrics() {
        let engine = AlertEngine::with_default_rules();
        for kind in MetricKind::all() {
            let has_rule = engine.rules().iter().any(|r| r.metric == *kind);
            assert!(has_rule, "No rule for {kind:?}");
        }
    }

    #[test]
    fn default_rules_coherence_uses_less_than() {
        let engine = AlertEngine::with_default_rules();
        let coherence_rules: Vec<_> = engine
            .rules()
            .iter()
            .filter(|r| r.metric == MetricKind::Coherence)
            .collect();
        assert_eq!(coherence_rules.len(), 2);
        assert!(
            coherence_rules
                .iter()
                .all(|r| r.comparison == Comparison::LessThan)
        );
    }

    #[test]
    fn default_rules_cpu_load_uses_greater_than() {
        let engine = AlertEngine::with_default_rules();
        let cpu_rules: Vec<_> = engine
            .rules()
            .iter()
            .filter(|r| r.metric == MetricKind::CpuLoad)
            .collect();
        assert_eq!(cpu_rules.len(), 2);
        assert!(
            cpu_rules
                .iter()
                .all(|r| r.comparison == Comparison::GreaterThan)
        );
    }
}
