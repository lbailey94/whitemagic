//! Self-model integration tools — predictive introspection MCP tools.
//!
//! Tools:
//! - `selfmodel.forecast` — forecast a metric or all metrics
//! - `selfmodel.alerts` — check active alerts
//! - `selfmodel.snapshot` — full self-model state snapshot
//! - `selfmodel.gnosis` — compact holistic system introspection

#![forbid(unsafe_code)]
#![allow(clippy::significant_drop_tightening)]

use async_trait::async_trait;

use std::sync::{Arc, Mutex};

use serde_json::{Value, json};
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};
use wm_selfmodel::{AlertLevel, MetricKind, SelfModel};

// ── Helper: parse MetricKind from string ──────────────────────────────

fn parse_metric_kind(s: &str) -> Result<MetricKind, wm_core::CoreError> {
    match s.to_lowercase().as_str() {
        "cpu_load" | "cpu" | "load" => Ok(MetricKind::CpuLoad),
        "memory_pressure" | "memory" | "mem" => Ok(MetricKind::MemoryPressure),
        "latency" | "lat" => Ok(MetricKind::Latency),
        "coherence" | "coh" => Ok(MetricKind::Coherence),
        "error_rate" | "errors" | "error" => Ok(MetricKind::ErrorRate),
        "disk_io" | "disk" | "io" => Ok(MetricKind::DiskIo),
        "swap_usage" | "swap" => Ok(MetricKind::SwapUsage),
        _ => Err(wm_core::CoreError::InvalidArgs(format!(
            "unknown metric kind: {s}"
        ))),
    }
}

const fn alert_level_as_str(level: AlertLevel) -> &'static str {
    match level {
        AlertLevel::Info => "info",
        AlertLevel::Warning => "warning",
        AlertLevel::Critical => "critical",
    }
}

fn forecast_to_json(forecast: &wm_selfmodel::Forecast) -> Value {
    json!({
        "predicted_value": forecast.predicted_value,
        "slope": forecast.slope,
        "ewma": forecast.ewma,
        "confidence": forecast.confidence,
        "horizon": forecast.horizon,
    })
}

fn metric_snapshot_to_json(snap: &wm_selfmodel::MetricSnapshot) -> Value {
    json!({
        "kind": snap.kind.as_str(),
        "current": snap.current,
        "min": snap.min,
        "max": snap.max,
        "avg": snap.avg,
        "sample_count": snap.sample_count,
    })
}

// ── selfmodel.forecast ────────────────────────────────────────────────

/// `selfmodel.forecast` — forecast a metric or all metrics.
pub struct SelfModelForecastTool {
    model: Arc<Mutex<SelfModel>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SelfModelForecastTool {
    #[must_use]
    pub fn new(model: Arc<Mutex<SelfModel>>) -> Self {
        Self {
            model,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for SelfModelForecastTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(SelfModel::new())))
    }
}

#[async_trait]
#[async_trait]
impl Tool for SelfModelForecastTool {
    fn name(&self) -> &str {
        "selfmodel.forecast"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let model = self
            .model
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("self-model lock: {e}")))?;

        let horizon = args.get("horizon").and_then(Value::as_u64).unwrap_or(5) as usize;

        if let Some(metric_str) = args.get("metric").and_then(|m| m.as_str()) {
            let kind = parse_metric_kind(metric_str)?;
            match model.forecast(kind, horizon) {
                Some(forecast) => Ok(json!({
                    "metric": kind.as_str(),
                    "forecast": forecast_to_json(&forecast),
                })),
                None => Ok(json!({
                    "metric": kind.as_str(),
                    "forecast": null,
                    "message": "insufficient data for forecast (need at least 2 samples)",
                })),
            }
        } else {
            let forecasts = model.forecast_all(horizon);
            if forecasts.is_empty() {
                return Ok(json!({
                    "forecasts": [],
                    "message": "no metrics tracked yet",
                }));
            }
            let result: Vec<Value> = forecasts
                .iter()
                .map(|(kind, f)| {
                    json!({
                        "metric": kind.as_str(),
                        "forecast": forecast_to_json(f),
                    })
                })
                .collect();
            Ok(json!({
                "forecasts": result,
                "count": result.len(),
            }))
        }
    }
}

// ── selfmodel.alerts ──────────────────────────────────────────────────

/// `selfmodel.alerts` — check active alerts from forecast threshold crossings.
pub struct SelfModelAlertsTool {
    model: Arc<Mutex<SelfModel>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SelfModelAlertsTool {
    #[must_use]
    pub fn new(model: Arc<Mutex<SelfModel>>) -> Self {
        Self {
            model,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for SelfModelAlertsTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(SelfModel::new())))
    }
}

#[async_trait]
#[async_trait]
impl Tool for SelfModelAlertsTool {
    fn name(&self) -> &str {
        "selfmodel.alerts"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let model = self
            .model
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("self-model lock: {e}")))?;

        let alerts = model.check_alerts();
        let critical_count = alerts
            .iter()
            .filter(|a| a.level == AlertLevel::Critical)
            .count();
        let warning_count = alerts
            .iter()
            .filter(|a| a.level == AlertLevel::Warning)
            .count();

        let alerts_json: Vec<Value> = alerts
            .iter()
            .map(|a| {
                json!({
                    "metric": a.metric.as_str(),
                    "level": alert_level_as_str(a.level),
                    "predicted_value": a.predicted_value,
                    "threshold": a.threshold,
                    "message": a.message,
                    "confidence": a.confidence,
                })
            })
            .collect();

        Ok(json!({
            "alerts": alerts_json,
            "total": alerts.len(),
            "critical_count": critical_count,
            "warning_count": warning_count,
        }))
    }
}

// ── selfmodel.snapshot ────────────────────────────────────────────────

/// `selfmodel.snapshot` — full self-model state snapshot.
pub struct SelfModelSnapshotTool {
    model: Arc<Mutex<SelfModel>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SelfModelSnapshotTool {
    #[must_use]
    pub fn new(model: Arc<Mutex<SelfModel>>) -> Self {
        Self {
            model,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for SelfModelSnapshotTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(SelfModel::new())))
    }
}

#[async_trait]
#[async_trait]
impl Tool for SelfModelSnapshotTool {
    fn name(&self) -> &str {
        "selfmodel.snapshot"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let model = self
            .model
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("self-model lock: {e}")))?;

        let snap = model.snapshot();

        let metrics_json: Vec<Value> = snap.metrics.iter().map(metric_snapshot_to_json).collect();

        let alerts_json: Vec<Value> = snap
            .alerts
            .iter()
            .map(|a| {
                json!({
                    "metric": a.metric.as_str(),
                    "level": alert_level_as_str(a.level),
                    "predicted_value": a.predicted_value,
                    "threshold": a.threshold,
                    "message": a.message,
                })
            })
            .collect();

        let forecasts_json: Vec<Value> = snap
            .forecasts
            .iter()
            .map(|(kind, f)| {
                json!({
                    "metric": kind.as_str(),
                    "forecast": forecast_to_json(f),
                })
            })
            .collect();

        Ok(json!({
            "timestamp": snap.timestamp.to_rfc3339(),
            "confidence": snap.confidence,
            "conservative_mode": snap.confidence < 0.5,
            "metrics": metrics_json,
            "metric_count": snap.metrics.len(),
            "alerts": alerts_json,
            "alert_count": snap.alerts.len(),
            "forecasts": forecasts_json,
            "forecast_count": snap.forecasts.len(),
        }))
    }
}

// ── selfmodel.gnosis ──────────────────────────────────────────────────

/// `selfmodel.gnosis` — compact holistic system introspection.
///
/// Mirrors the legacy v26 `gnosis` tool: one call returns the system's
/// self-knowledge — confidence, tracked metrics, active alerts, and a
/// per-metric health summary — without flooding the context window.
pub struct SelfModelGnosisTool {
    model: Arc<Mutex<SelfModel>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SelfModelGnosisTool {
    #[must_use]
    pub fn new(model: Arc<Mutex<SelfModel>>) -> Self {
        Self {
            model,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for SelfModelGnosisTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(SelfModel::new())))
    }
}

#[async_trait]
#[async_trait]
impl Tool for SelfModelGnosisTool {
    fn name(&self) -> &str {
        "selfmodel.gnosis"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let model = self
            .model
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("self-model lock: {e}")))?;

        let snap = model.snapshot();
        let confidence = model.confidence();

        let metrics_json: Vec<Value> = snap
            .metrics
            .iter()
            .map(|m| {
                json!({
                    "metric": m.kind.as_str(),
                    "samples": m.sample_count,
                    "current": m.current,
                    "min": m.min,
                    "max": m.max,
                    "avg": m.avg,
                })
            })
            .collect();

        let alerts_json: Vec<Value> = snap
            .alerts
            .iter()
            .map(|a| {
                json!({
                    "metric": a.metric.as_str(),
                    "level": alert_level_as_str(a.level),
                    "message": a.message,
                })
            })
            .collect();

        // Health verdict per metric: healthy if no alert and enough samples.
        let mut healthy = 0usize;
        let mut degraded = 0usize;
        for m in &snap.metrics {
            let has_alert = snap.alerts.iter().any(|a| a.metric == m.kind);
            if has_alert {
                degraded += 1;
            } else {
                healthy += 1;
            }
        }

        let overall = if snap.alerts.is_empty() {
            "healthy"
        } else {
            "degraded"
        };

        Ok(json!({
            "timestamp": snap.timestamp.to_rfc3339(),
            "overall_health": overall,
            "confidence": confidence,
            "tracked_metrics": healthy + degraded,
            "healthy_metrics": healthy,
            "degraded_metrics": degraded,
            "alert_count": snap.alerts.len(),
            "metrics": metrics_json,
            "alerts": alerts_json,
        }))
    }
}

// ── Registration ──────────────────────────────────────────────────────

/// Register all self-model tools into a registry.
pub fn register_selfmodel(
    registry: &wm_dispatch::ToolRegistry,
    model: Arc<Mutex<SelfModel>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(SelfModelForecastTool::new(Arc::clone(&model))))
        .register(Arc::new(SelfModelAlertsTool::new(Arc::clone(&model))))
        .register(Arc::new(SelfModelSnapshotTool::new(Arc::clone(&model))))
        .register(Arc::new(SelfModelGnosisTool::new(model)))
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn test_model() -> Arc<Mutex<SelfModel>> {
        let model = SelfModel::new();
        for v in [0.1, 0.2, 0.3, 0.4, 0.5] {
            model.record(MetricKind::CpuLoad, v);
        }
        model.record(MetricKind::MemoryPressure, 0.2);
        model.record(MetricKind::MemoryPressure, 0.3);
        Arc::new(Mutex::new(model))
    }

    #[tokio::test]
    async fn parse_metric_kind_all_variants() {
        assert_eq!(parse_metric_kind("cpu_load").unwrap(), MetricKind::CpuLoad);
        assert_eq!(parse_metric_kind("CPU").unwrap(), MetricKind::CpuLoad);
        assert_eq!(
            parse_metric_kind("memory_pressure").unwrap(),
            MetricKind::MemoryPressure
        );
        assert_eq!(
            parse_metric_kind("mem").unwrap(),
            MetricKind::MemoryPressure
        );
        assert_eq!(parse_metric_kind("latency").unwrap(), MetricKind::Latency);
        assert_eq!(
            parse_metric_kind("coherence").unwrap(),
            MetricKind::Coherence
        );
        assert_eq!(
            parse_metric_kind("error_rate").unwrap(),
            MetricKind::ErrorRate
        );
        assert_eq!(parse_metric_kind("disk_io").unwrap(), MetricKind::DiskIo);
        assert_eq!(parse_metric_kind("swap").unwrap(), MetricKind::SwapUsage);
    }

    #[tokio::test]
    async fn parse_metric_kind_invalid() {
        assert!(parse_metric_kind("nonexistent").is_err());
    }

    #[tokio::test]
    async fn forecast_single_metric() {
        let model = test_model();
        let tool = SelfModelForecastTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool
            .call(&mut ctx, json!({"metric": "cpu_load", "horizon": 5}))
            .await
            .unwrap();
        assert_eq!(result["metric"], "cpu_load");
        assert!(result["forecast"]["predicted_value"].is_number());
        assert!(result["forecast"]["confidence"].is_number());
    }

    #[tokio::test]
    async fn forecast_all_metrics() {
        let model = test_model();
        let tool = SelfModelForecastTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({"horizon": 3})).await.unwrap();
        let forecasts = result["forecasts"].as_array().unwrap();
        assert_eq!(forecasts.len(), 2);
        assert_eq!(result["count"], 2);
    }

    #[tokio::test]
    async fn forecast_empty_model() {
        let model = Arc::new(Mutex::new(SelfModel::new()));
        let tool = SelfModelForecastTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["forecasts"].as_array().unwrap().len(), 0);
    }

    #[tokio::test]
    async fn forecast_insufficient_data() {
        let model = Arc::new(Mutex::new(SelfModel::new()));
        {
            let m = model.lock().unwrap();
            m.record(MetricKind::CpuLoad, 0.3);
        }
        let tool = SelfModelForecastTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool
            .call(&mut ctx, json!({"metric": "cpu_load"}))
            .await
            .unwrap();
        assert!(result["forecast"].is_null());
        assert!(result["message"].as_str().unwrap().contains("insufficient"));
    }

    #[tokio::test]
    async fn forecast_invalid_metric() {
        let model = test_model();
        let tool = SelfModelForecastTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let err = tool
            .call(&mut ctx, json!({"metric": "nonexistent"}))
            .await
            .unwrap_err();
        assert!(err.to_string().contains("unknown metric"));
    }

    #[tokio::test]
    async fn alerts_clear() {
        let model = Arc::new(Mutex::new(SelfModel::new()));
        {
            let m = model.lock().unwrap();
            for v in [0.1, 0.12, 0.11, 0.13] {
                m.record(MetricKind::CpuLoad, v);
            }
        }
        let tool = SelfModelAlertsTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["total"], 0);
        assert_eq!(result["critical_count"], 0);
    }

    #[tokio::test]
    async fn alerts_triggered() {
        let model = Arc::new(Mutex::new(SelfModel::new()));
        {
            let m = model.lock().unwrap();
            for v in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95] {
                m.record(MetricKind::CpuLoad, v);
            }
        }
        let tool = SelfModelAlertsTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert!(result["total"].as_u64().unwrap() > 0);
        let alerts = result["alerts"].as_array().unwrap();
        assert!(alerts.iter().any(|a| a["metric"] == "cpu_load"));
    }

    #[tokio::test]
    async fn snapshot_with_data() {
        let model = test_model();
        let tool = SelfModelSnapshotTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert!(result["confidence"].is_number());
        assert!(result["metric_count"].as_u64().unwrap() > 0);
        assert!(result["forecast_count"].as_u64().unwrap() > 0);
        assert!(result["timestamp"].is_string());
        assert!(result["conservative_mode"].is_boolean());
    }

    #[tokio::test]
    async fn snapshot_empty_model() {
        let model = Arc::new(Mutex::new(SelfModel::new()));
        let tool = SelfModelSnapshotTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["metric_count"], 0);
        assert_eq!(result["alert_count"], 0);
        assert_eq!(result["forecast_count"], 0);
    }

    #[tokio::test]
    async fn register_selfmodel_registers_three_tools() {
        let model = test_model();
        let registry = wm_dispatch::ToolRegistry::new();
        let registry = register_selfmodel(&registry, model);
        assert!(registry.get("selfmodel.forecast").is_some());
        assert!(registry.get("selfmodel.alerts").is_some());
        assert!(registry.get("selfmodel.snapshot").is_some());
    }

    #[tokio::test]
    async fn forecast_default_horizon() {
        let model = test_model();
        let tool = SelfModelForecastTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool
            .call(&mut ctx, json!({"metric": "cpu_load"}))
            .await
            .unwrap();
        assert_eq!(result["forecast"]["horizon"], 5);
    }

    #[tokio::test]
    async fn snapshot_conservative_mode_flag() {
        let model = Arc::new(Mutex::new(SelfModel::new()));
        // Empty model → confidence 0.5 → not conservative
        let tool = SelfModelSnapshotTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["conservative_mode"], false);
    }

    #[tokio::test]
    async fn gnosis_reports_health_and_metrics() {
        let model = test_model();
        let tool = SelfModelGnosisTool::new(Arc::clone(&model));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = tool.call(&mut ctx, json!({})).await.unwrap();

        // Rising CPU load (0.1 → 0.5) crosses default warning AND critical
        // thresholds → degraded (2 alerts, one per rule level).
        assert_eq!(result["overall_health"], "degraded");
        assert_eq!(result["tracked_metrics"], 2);
        assert_eq!(result["healthy_metrics"], 1);
        assert_eq!(result["degraded_metrics"], 1);
        assert_eq!(result["alert_count"], 2);
        assert_eq!(result["metrics"].as_array().unwrap().len(), 2);
        assert!(result["confidence"].as_f64().unwrap() > 0.0);
    }
}
