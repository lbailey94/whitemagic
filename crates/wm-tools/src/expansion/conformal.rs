//! Conformal prediction tools — distribution-free uncertainty
//! quantification for the agent.
//!
//! Unlike heuristic confidence scores, conformal prediction produces
//! prediction *sets* (classification) or *intervals* (regression) with a
//! finite-sample, distribution-free coverage guarantee: the true outcome
//! is included with probability ≥ 1 − α, regardless of the model.
//!
//! Tools:
//! - `conformal.fit_classifier` — calibrate a label prediction-set model
//! - `conformal.fit_regressor` — calibrate a regression interval model
//! - `conformal.predict_set` — predict a label set (with guarantee)
//! - `conformal.predict_interval` — predict a value interval (with guarantee)
//! - `conformal.status` — current calibration state and coverage report
//! - `conformal.export` / `conformal.import` — JSON persistence

#![forbid(unsafe_code)]
#![allow(clippy::significant_drop_tightening)]

use async_trait::async_trait;

use std::sync::{Arc, Mutex};

use serde_json::{Value, json};
use wm_conformal::{AdaptivePredictionSets, SplitConformalClassifier, SplitConformalRegressor};
use wm_core::{Context, EffectRow, Gana, Tool, ToolStats};

/// Shared conformal state — one per MCP server instance.
///
/// Holds fitted classifiers/regressors plus the raw calibration samples,
/// so the store can be re-fit and exported/imported across restarts.
#[derive(Default)]
pub struct ConformalStore {
    /// Fitted classifier (label sets).
    pub classifier: Option<SplitConformalClassifier>,
    /// Fitted regressor (value intervals).
    pub regressor: Option<SplitConformalRegressor>,
    /// APS classifier (smaller sets for calibrated models).
    pub aps: Option<AdaptivePredictionSets>,
    /// Raw calibration samples (scores, true_label) for re-fitting.
    pub class_samples: Vec<(Vec<f64>, usize)>,
    /// Raw calibration samples (predicted, actual) for re-fitting.
    pub reg_samples: Vec<(f64, f64)>,
}

impl ConformalStore {
    /// Create an empty store.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Fit the classifier from accumulated samples. Returns the number of
    /// samples; fitting is skipped (without error) if fewer than 2 samples
    /// are available, so callers can add samples incrementally.
    pub fn fit_classifier(&mut self, alpha: f64) -> Result<usize, String> {
        let n = self.class_samples.len();
        if n >= 2 {
            let mut cp = SplitConformalClassifier::new(alpha).map_err(|e| e.to_string())?;
            for (scores, label) in &self.class_samples {
                cp.add_sample(scores, *label).map_err(|e| e.to_string())?;
            }
            cp.fit().map_err(|e| e.to_string())?;
            self.classifier = Some(cp);

            // Also fit the APS variant on the same samples.
            let mut aps = AdaptivePredictionSets::new(alpha).map_err(|e| e.to_string())?;
            for (scores, label) in &self.class_samples {
                aps.add_sample(scores, *label).map_err(|e| e.to_string())?;
            }
            aps.fit().map_err(|e| e.to_string())?;
            self.aps = Some(aps);
        }
        Ok(n)
    }

    /// Fit the regressor from accumulated samples. Returns the number of
    /// samples; fitting is skipped (without error) if fewer than 2 samples
    /// are available.
    pub fn fit_regressor(&mut self, alpha: f64) -> Result<usize, String> {
        let n = self.reg_samples.len();
        if n >= 2 {
            let mut r = SplitConformalRegressor::new(alpha).map_err(|e| e.to_string())?;
            for (pred, actual) in &self.reg_samples {
                r.add_sample(*pred, *actual);
            }
            r.fit().map_err(|e| e.to_string())?;
            self.regressor = Some(r);
        }
        Ok(n)
    }

    /// Number of classifier calibration samples.
    #[must_use]
    pub fn classifier_samples(&self) -> usize {
        self.class_samples.len()
    }

    /// Number of regressor calibration samples.
    #[must_use]
    pub fn regressor_samples(&self) -> usize {
        self.reg_samples.len()
    }

    /// Serialize the whole store for persistence.
    #[must_use]
    pub fn to_json(&self) -> Value {
        json!({
            "classifier": self.classifier.as_ref().and_then(|c| c.to_json().ok()),
            "regressor": self.regressor.as_ref().and_then(|r| r.to_json().ok()),
            "aps": self.aps.as_ref().and_then(|a| a.to_json().ok()),
            "class_samples": self.class_samples.iter()
                .map(|(s, l)| json!({"scores": s, "label": l})).collect::<Vec<_>>(),
            "reg_samples": self.reg_samples.iter()
                .map(|(p, a)| json!({"predicted": p, "actual": a})).collect::<Vec<_>>(),
        })
    }

    /// Restore the store from JSON.
    pub fn from_json(&mut self, value: &Value) -> Result<(), String> {
        if let Some(c) = value.get("classifier").and_then(Value::as_str) {
            self.classifier =
                Some(SplitConformalClassifier::from_json(c).map_err(|e| e.to_string())?);
        }
        if let Some(r) = value.get("regressor").and_then(Value::as_str) {
            self.regressor =
                Some(SplitConformalRegressor::from_json(r).map_err(|e| e.to_string())?);
        }
        if let Some(a) = value.get("aps").and_then(Value::as_str) {
            self.aps = Some(AdaptivePredictionSets::from_json(a).map_err(|e| e.to_string())?);
        }
        if let Some(samples) = value.get("class_samples").and_then(Value::as_array) {
            self.class_samples = samples
                .iter()
                .filter_map(|s| {
                    let scores = s
                        .get("scores")?
                        .as_array()?
                        .iter()
                        .filter_map(serde_json::Value::as_f64)
                        .collect::<Vec<_>>();
                    let label = s.get("label")?.as_u64()? as usize;
                    Some((scores, label))
                })
                .collect();
        }
        if let Some(samples) = value.get("reg_samples").and_then(Value::as_array) {
            self.reg_samples = samples
                .iter()
                .filter_map(|s| {
                    let predicted = s.get("predicted")?.as_f64()?;
                    let actual = s.get("actual")?.as_f64()?;
                    Some((predicted, actual))
                })
                .collect();
        }
        Ok(())
    }
}

/// Parse a JSON array of scores into Vec<f64>.
fn parse_scores(args: &Value) -> Result<Vec<f64>, wm_core::CoreError> {
    args.get("scores")
        .and_then(Value::as_array)
        .map(|arr| {
            arr.iter()
                .map(|v| {
                    v.as_f64().ok_or_else(|| {
                        wm_core::CoreError::InvalidArgs("scores must be numeric".into())
                    })
                })
                .collect::<Result<Vec<_>, _>>()
        })
        .ok_or_else(|| wm_core::CoreError::InvalidArgs("missing required 'scores' array".into()))?
}

fn parse_alpha(args: &Value) -> Result<f64, wm_core::CoreError> {
    Ok(args.get("alpha").and_then(Value::as_f64).unwrap_or(0.1))
}

// ── conformal.fit_classifier ─────────────────────────────────────────

/// `conformal.fit_classifier` — calibrate a label prediction-set model
/// from (scores, true_label) samples.
pub struct ConformalFitClassifierTool {
    store: Arc<Mutex<ConformalStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConformalFitClassifierTool {
    #[must_use]
    pub fn new(store: Arc<Mutex<ConformalStore>>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for ConformalFitClassifierTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(ConformalStore::new())))
    }
}

#[async_trait]
#[async_trait]
impl Tool for ConformalFitClassifierTool {
    fn name(&self) -> &str {
        "conformal.fit_classifier"
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
        // Accept either a single sample {scores, label} or a batch.
        let alpha = parse_alpha(&args)?;
        let mut store = self
            .store
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("conformal store lock: {e}")))?;

        if let Some(batch) = args.get("samples").and_then(Value::as_array) {
            for sample in batch {
                let scores = parse_scores(sample)?;
                let label = sample.get("label").and_then(Value::as_u64).ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("each sample needs 'scores' and 'label'".into())
                })? as usize;
                store.class_samples.push((scores, label));
            }
        } else {
            let scores = parse_scores(&args)?;
            let label =
                args.get("label").and_then(Value::as_u64).ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("missing required 'label'".into())
                })? as usize;
            store.class_samples.push((scores, label));
        }

        let n = store
            .fit_classifier(alpha)
            .map_err(wm_core::CoreError::Tool)?;
        let fitted = n >= 2;

        Ok(json!({
            "status": "success",
            "samples": n,
            "fitted": fitted,
            "alpha": alpha,
            "guarantee": 1.0 - alpha,
        }))
    }
}

// ── conformal.fit_regressor ──────────────────────────────────────────

/// `conformal.fit_regressor` — calibrate a regression interval model from
/// (predicted, actual) samples.
pub struct ConformalFitRegressorTool {
    store: Arc<Mutex<ConformalStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConformalFitRegressorTool {
    #[must_use]
    pub fn new(store: Arc<Mutex<ConformalStore>>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for ConformalFitRegressorTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(ConformalStore::new())))
    }
}

#[async_trait]
#[async_trait]
impl Tool for ConformalFitRegressorTool {
    fn name(&self) -> &str {
        "conformal.fit_regressor"
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
        let alpha = parse_alpha(&args)?;
        let mut store = self
            .store
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("conformal store lock: {e}")))?;

        if let Some(batch) = args.get("samples").and_then(Value::as_array) {
            for sample in batch {
                let predicted =
                    sample
                        .get("predicted")
                        .and_then(Value::as_f64)
                        .ok_or_else(|| {
                            wm_core::CoreError::InvalidArgs("sample needs 'predicted'".into())
                        })?;
                let actual = sample
                    .get("actual")
                    .and_then(Value::as_f64)
                    .ok_or_else(|| {
                        wm_core::CoreError::InvalidArgs("sample needs 'actual'".into())
                    })?;
                store.reg_samples.push((predicted, actual));
            }
        } else {
            let predicted = args
                .get("predicted")
                .and_then(Value::as_f64)
                .ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("missing required 'predicted'".into())
                })?;
            let actual = args.get("actual").and_then(Value::as_f64).ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("missing required 'actual'".into())
            })?;
            store.reg_samples.push((predicted, actual));
        }

        let n = store
            .fit_regressor(alpha)
            .map_err(wm_core::CoreError::Tool)?;
        let fitted = n >= 2;

        Ok(json!({
            "status": "success",
            "samples": n,
            "fitted": fitted,
            "alpha": alpha,
            "guarantee": 1.0 - alpha,
        }))
    }
}

// ── conformal.predict_set ────────────────────────────────────────────

/// `conformal.predict_set` — predict a label set with a coverage
/// guarantee. Optional `mode`: "plain" (default) or "aps" (adaptive,
/// smaller sets for calibrated models).
pub struct ConformalPredictSetTool {
    store: Arc<Mutex<ConformalStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConformalPredictSetTool {
    #[must_use]
    pub fn new(store: Arc<Mutex<ConformalStore>>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for ConformalPredictSetTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(ConformalStore::new())))
    }
}

#[async_trait]
#[async_trait]
impl Tool for ConformalPredictSetTool {
    fn name(&self) -> &str {
        "conformal.predict_set"
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
        let scores = parse_scores(&args)?;
        let mode = args.get("mode").and_then(Value::as_str).unwrap_or("plain");
        let mut store = self
            .store
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("conformal store lock: {e}")))?;

        if mode == "aps" {
            let aps = store.aps.as_mut().ok_or_else(|| {
                wm_core::CoreError::Tool(
                    "APS not calibrated — run conformal.fit_classifier first".into(),
                )
            })?;
            let set = aps
                .predict_set(&scores)
                .map_err(|e| wm_core::CoreError::Tool(e.to_string()))?;
            Ok(json!({
                "classes": set.classes,
                "probs": set.probs,
                "coverage_guarantee": set.guarantee,
                "mode": "aps",
            }))
        } else {
            let cp = store.classifier.as_ref().ok_or_else(|| {
                wm_core::CoreError::Tool(
                    "classifier not calibrated — run conformal.fit_classifier first".into(),
                )
            })?;
            let set = cp
                .predict_set(&scores)
                .map_err(|e| wm_core::CoreError::Tool(e.to_string()))?;
            Ok(json!({
                "classes": set.classes,
                "probs": set.probs,
                "coverage_guarantee": set.guarantee,
                "threshold": set.threshold,
                "mode": "plain",
            }))
        }
    }
}

// ── conformal.predict_interval ───────────────────────────────────────

/// `conformal.predict_interval` — predict a value interval with a
/// coverage guarantee.
pub struct ConformalPredictIntervalTool {
    store: Arc<Mutex<ConformalStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConformalPredictIntervalTool {
    #[must_use]
    pub fn new(store: Arc<Mutex<ConformalStore>>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for ConformalPredictIntervalTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(ConformalStore::new())))
    }
}

#[async_trait]
#[async_trait]
impl Tool for ConformalPredictIntervalTool {
    fn name(&self) -> &str {
        "conformal.predict_interval"
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
        let prediction = args.get("value").and_then(Value::as_f64).ok_or_else(|| {
            wm_core::CoreError::InvalidArgs(
                "missing required 'value' (the point prediction)".into(),
            )
        })?;
        let store = self
            .store
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("conformal store lock: {e}")))?;

        let reg = store.regressor.as_ref().ok_or_else(|| {
            wm_core::CoreError::Tool(
                "regressor not calibrated — run conformal.fit_regressor first".into(),
            )
        })?;
        let iv = reg
            .predict_interval(prediction)
            .map_err(|e| wm_core::CoreError::Tool(e.to_string()))?;

        Ok(json!({
            "point": iv.point,
            "lower": iv.lower,
            "upper": iv.upper,
            "width": iv.width(),
            "coverage_guarantee": iv.guarantee,
        }))
    }
}

// ── conformal.status ─────────────────────────────────────────────────

/// `conformal.status` — current calibration state and sample counts.
pub struct ConformalStatusTool {
    store: Arc<Mutex<ConformalStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConformalStatusTool {
    #[must_use]
    pub fn new(store: Arc<Mutex<ConformalStore>>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for ConformalStatusTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(ConformalStore::new())))
    }
}

#[async_trait]
#[async_trait]
impl Tool for ConformalStatusTool {
    fn name(&self) -> &str {
        "conformal.status"
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
        let store = self
            .store
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("conformal store lock: {e}")))?;
        Ok(json!({
            "classifier_fitted": store.classifier.is_some(),
            "regressor_fitted": store.regressor.is_some(),
            "aps_fitted": store.aps.is_some(),
            "classifier_samples": store.classifier_samples(),
            "regressor_samples": store.regressor_samples(),
            "classifier_alpha": store.classifier.as_ref().map(wm_conformal::SplitConformalClassifier::alpha),
            "regressor_alpha": store.regressor.as_ref().map(wm_conformal::SplitConformalRegressor::alpha),
        }))
    }
}

// ── conformal.export / conformal.import ──────────────────────────────

/// `conformal.export` — serialize the conformal store for persistence.
pub struct ConformalExportTool {
    store: Arc<Mutex<ConformalStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConformalExportTool {
    #[must_use]
    pub fn new(store: Arc<Mutex<ConformalStore>>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for ConformalExportTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(ConformalStore::new())))
    }
}

#[async_trait]
#[async_trait]
impl Tool for ConformalExportTool {
    fn name(&self) -> &str {
        "conformal.export"
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
        let store = self
            .store
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("conformal store lock: {e}")))?;
        Ok(store.to_json())
    }
}

/// `conformal.import` — restore the conformal store from exported JSON.
pub struct ConformalImportTool {
    store: Arc<Mutex<ConformalStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConformalImportTool {
    #[must_use]
    pub fn new(store: Arc<Mutex<ConformalStore>>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for ConformalImportTool {
    fn default() -> Self {
        Self::new(Arc::new(Mutex::new(ConformalStore::new())))
    }
}

#[async_trait]
#[async_trait]
impl Tool for ConformalImportTool {
    fn name(&self) -> &str {
        "conformal.import"
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
        let mut store = self
            .store
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("conformal store lock: {e}")))?;
        store.from_json(&args).map_err(wm_core::CoreError::Tool)?;
        Ok(json!({
            "status": "success",
            "classifier_samples": store.classifier_samples(),
            "regressor_samples": store.regressor_samples(),
        }))
    }
}

// ── Registration ─────────────────────────────────────────────────────

/// Register all conformal tools into a registry.
pub fn register_conformal(
    registry: &wm_dispatch::ToolRegistry,
    store: Arc<Mutex<ConformalStore>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(ConformalFitClassifierTool::new(Arc::clone(
            &store,
        ))))
        .register(Arc::new(ConformalFitRegressorTool::new(Arc::clone(&store))))
        .register(Arc::new(ConformalPredictSetTool::new(Arc::clone(&store))))
        .register(Arc::new(ConformalPredictIntervalTool::new(Arc::clone(
            &store,
        ))))
        .register(Arc::new(ConformalStatusTool::new(Arc::clone(&store))))
        .register(Arc::new(ConformalExportTool::new(Arc::clone(&store))))
        .register(Arc::new(ConformalImportTool::new(store)))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_store() -> Arc<Mutex<ConformalStore>> {
        Arc::new(Mutex::new(ConformalStore::new()))
    }

    #[tokio::test]
    async fn fit_and_predict_set_roundtrip() {
        let store = test_store();
        let fit = ConformalFitClassifierTool::new(Arc::clone(&store));
        let predict = ConformalPredictSetTool::new(Arc::clone(&store));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);

        let mut samples = Vec::new();
        for c in 0..3u64 {
            for _ in 0..20 {
                let mut scores = vec![0.1, 0.1, 0.1];
                scores[c as usize] = 0.8;
                samples.push(json!({"scores": scores, "label": c}));
            }
        }
        let result = fit
            .call(&mut ctx, json!({"alpha": 0.1, "samples": samples}))
            .await
            .unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["samples"], 60);

        let result = predict
            .call(&mut ctx, json!({"scores": [0.8, 0.1, 0.1]}))
            .await
            .unwrap();
        assert_eq!(result["classes"][0], 0);
        assert!(result["coverage_guarantee"].as_f64().unwrap() > 0.89);
    }

    #[tokio::test]
    async fn predict_before_fit_returns_error() {
        let store = test_store();
        let predict = ConformalPredictSetTool::new(Arc::clone(&store));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);
        let result = predict.call(&mut ctx, json!({"scores": [0.5, 0.5]})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn regressor_fit_and_interval() {
        let store = test_store();
        let fit = ConformalFitRegressorTool::new(Arc::clone(&store));
        let predict = ConformalPredictIntervalTool::new(Arc::clone(&store));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);

        let samples: Vec<Value> = (0..30)
            .map(|i| json!({"predicted": f64::from(i), "actual": f64::from(i) + 1.0}))
            .collect();
        fit.call(&mut ctx, json!({"alpha": 0.1, "samples": samples}))
            .await
            .unwrap();

        let result = predict
            .call(&mut ctx, json!({"value": 15.0}))
            .await
            .unwrap();
        assert!(result["lower"].as_f64().unwrap() <= 15.0);
        assert!(result["upper"].as_f64().unwrap() >= 16.0);
    }

    #[tokio::test]
    async fn export_import_roundtrip() {
        let store = test_store();
        let fit = ConformalFitClassifierTool::new(Arc::clone(&store));
        let export = ConformalExportTool::new(Arc::clone(&store));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);

        for c in 0..2u64 {
            for _ in 0..10 {
                let scores = if c == 0 {
                    vec![0.9, 0.1]
                } else {
                    vec![0.1, 0.9]
                };
                fit.call(&mut ctx, json!({"scores": scores, "label": c}))
                    .await
                    .unwrap();
            }
        }

        let exported = export.call(&mut ctx, json!({})).await.unwrap();

        let store2 = test_store();
        let import = ConformalImportTool::new(Arc::clone(&store2));
        let status = ConformalStatusTool::new(Arc::clone(&store2));
        import.call(&mut ctx, exported).await.unwrap();
        let st = status.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(st["classifier_samples"], 20);
        assert_eq!(st["classifier_fitted"], true);
    }

    #[tokio::test]
    async fn aps_mode_produces_singleton() {
        let store = test_store();
        let fit = ConformalFitClassifierTool::new(Arc::clone(&store));
        let predict = ConformalPredictSetTool::new(Arc::clone(&store));
        let mut ctx = Context::new(wm_core::BrainWave::Gamma);

        for _ in 0..50 {
            fit.call(&mut ctx, json!({"scores": [0.95, 0.03, 0.02], "label": 0}))
                .await
                .unwrap();
        }
        let result = predict
            .call(
                &mut ctx,
                json!({"scores": [0.95, 0.03, 0.02], "mode": "aps"}),
            )
            .await
            .unwrap();
        // APS may include 1–2 classes for a confident model; the true
        // (highest-probability) class must always be present.
        let classes = result["classes"].as_array().unwrap();
        assert!(classes.len() <= 2);
        assert_eq!(classes[0], 0);
    }
}
