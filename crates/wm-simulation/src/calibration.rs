//! Prediction calibration — Brier scorecard with the Murphy decomposition.
//!
//! Tracks recorded predictions, resolves them against reality, and produces
//! an honest calibration scorecard:
//!
//! - **Brier score**: mean squared error `(p − o)²` over resolved forecasts
//! - **Reliability**: how well predicted probabilities match observed rates
//! - **Resolution**: how much predictions separate positive from negative outcomes
//! - **Uncertainty**: base rate `ō(1 − ō)` — the difficulty of the problem
//! - **Brier skill score (BSS)**: `1 − Brier/Uncertainty` vs. climatology
//!
//! The calibration gap feeds a small adjustment back into future predictions,
//! matching the v26 `simulation.calibrate` bridge but with the full
//! decomposition the v26 version lacked.

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

/// A single recorded prediction, resolved or pending.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationPrediction {
    /// Stable identifier for the prediction.
    pub id: String,
    /// The prediction statement.
    pub statement: String,
    /// Predicted probability in [0, 1].
    pub probability: f64,
    /// Self-reported confidence in [0, 1] (informational).
    pub confidence: f64,
    /// Scenario / context label.
    pub scenario: String,
    /// Observed outcome (None until resolved).
    pub outcome: Option<bool>,
    /// Brier score once resolved: (p − o)².
    pub brier_score: Option<f64>,
    /// Probability after the historical calibration adjustment.
    pub adjusted_probability: Option<f64>,
}

impl CalibrationPrediction {
    /// Resolve against reality and compute the Brier score.
    pub fn resolve(&mut self, outcome: bool) -> f64 {
        self.outcome = Some(outcome);
        let brier = (self.probability - f64::from(outcome)).powi(2);
        self.brier_score = Some(brier);
        brier
    }
}

/// A single calibration bin: predicted-probability range vs. observed rate.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationBin {
    /// Bin label, e.g. "0.3-0.4".
    pub label: String,
    /// Number of resolved predictions in this bin.
    pub count: usize,
    /// Observed positive rate within the bin.
    pub actual_rate: f64,
}

/// Full Brier scorecard with the Murphy decomposition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrierScorecard {
    /// Total predictions ever recorded.
    pub total_predictions: usize,
    /// Predictions resolved against reality.
    pub resolved: usize,
    /// Predictions still awaiting resolution.
    pub unresolved: usize,
    /// Average Brier score over resolved predictions (lower is better).
    pub avg_brier_score: f64,
    /// Reliability term — mean squared gap between predicted probability
    /// and observed rate within bins. 0 = perfectly calibrated.
    pub reliability: f64,
    /// Resolution term — how well predictions separate outcomes. Higher
    /// is better (upper bounded by uncertainty).
    pub resolution: f64,
    /// Uncertainty — base-rate variance ō(1 − ō). The difficulty ceiling.
    pub uncertainty: f64,
    /// Brier skill score vs. climatology (1 = perfect, 0 = no better than
    /// always predicting the base rate, negative = worse).
    pub skill_score: f64,
    /// Decile calibration bins (predicted probability → observed rate).
    pub calibration_bins: Vec<CalibrationBin>,
    /// Historical rolling calibration gap used for adjustments.
    pub calibration_gap: f64,
    /// Whether the model is essentially perfectly calibrated.
    pub perfect_calibration: bool,
    /// Whether calibration is good (Brier < 0.15).
    pub good_calibration: bool,
}

impl BrierScorecard {
    /// Compute the scorecard from resolved predictions.
    #[must_use]
    pub fn compute(resolved: &[CalibrationPrediction], gap: f64) -> Self {
        let n = resolved.len();
        let brier_scores = resolved
            .iter()
            .filter_map(|p| p.brier_score)
            .collect::<Vec<_>>();
        let avg_brier = if brier_scores.is_empty() {
            0.0
        } else {
            brier_scores.iter().sum::<f64>() / brier_scores.len() as f64
        };

        // Murphy decomposition over 10 decile bins
        let mut bins = Vec::with_capacity(10);
        let mut total_n = 0usize;
        let mut sum_outcome = 0.0_f64;
        for i in 0..10 {
            let lo = f64::from(i) / 10.0;
            let hi = f64::from(i + 1) / 10.0;
            let in_bin = resolved
                .iter()
                .filter(|p| {
                    let prob = p.probability.clamp(0.0, 0.999_999_9);
                    prob >= lo && prob < hi
                })
                .collect::<Vec<_>>();
            let count = in_bin.len();
            let actual_rate = if count > 0 {
                in_bin.iter().filter(|p| p.outcome == Some(true)).count() as f64 / count as f64
            } else {
                0.0
            };
            total_n += count;
            sum_outcome += actual_rate * count as f64;
            bins.push(CalibrationBin {
                label: format!("{lo:.1}-{hi:.1}"),
                count,
                actual_rate,
            });
        }

        let base_rate = if total_n > 0 {
            sum_outcome / total_n as f64
        } else {
            0.0
        };

        let mut reliability = 0.0;
        let mut resolution = 0.0;
        for bin in &bins {
            if bin.count == 0 {
                continue;
            }
            let weight = bin.count as f64 / total_n as f64;
            // Midpoint of the bin as the representative predicted probability
            let lo = bin
                .label
                .split('-')
                .next()
                .and_then(|s| s.parse::<f64>().ok())
                .unwrap_or(0.0);
            let predicted = lo + 0.05;
            reliability = weight.mul_add((predicted - bin.actual_rate).powi(2), reliability);
            resolution = weight.mul_add((bin.actual_rate - base_rate).powi(2), resolution);
        }
        let uncertainty = base_rate * (1.0 - base_rate);

        let skill_score = if uncertainty > 1e-12 {
            1.0 - avg_brier / uncertainty
        } else {
            0.0
        };

        Self {
            total_predictions: 0,
            resolved: n,
            unresolved: 0,
            avg_brier_score: avg_brier,
            reliability,
            resolution,
            uncertainty,
            skill_score,
            calibration_bins: bins,
            calibration_gap: gap,
            perfect_calibration: avg_brier < 0.05,
            good_calibration: avg_brier < 0.15,
        }
    }
}

/// In-memory calibration store — shared per MCP server instance.
///
/// Persistable via [`to_json`](Self::to_json) / [`from_json`](Self::from_json),
/// mirroring the conformal store pattern.
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct CalibrationStore {
    /// All recorded predictions (resolved and pending).
    pub predictions: Vec<CalibrationPrediction>,
    /// Historical Brier scores for the rolling calibration gap.
    calibration_history: Vec<f64>,
    /// Sequence counter for prediction IDs.
    next_id: u64,
}

impl CalibrationStore {
    /// Create an empty store.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Record a new prediction. Returns the stored prediction with its ID
    /// and the historical calibration adjustment applied.
    pub fn record(
        &mut self,
        statement: &str,
        probability: f64,
        confidence: f64,
        scenario: &str,
    ) -> CalibrationPrediction {
        let prob = probability.clamp(0.0, 1.0);
        let gap = self.calibration_gap();
        let adjusted = (prob - gap).clamp(0.0, 1.0);
        self.next_id += 1;
        let pred = CalibrationPrediction {
            id: format!("pred-{:06}", self.next_id),
            statement: statement.to_string(),
            probability: prob,
            confidence,
            scenario: scenario.to_string(),
            outcome: None,
            brier_score: None,
            adjusted_probability: Some(adjusted),
        };
        self.predictions.push(pred.clone());
        pred
    }

    /// Resolve a prediction against reality. Returns the Brier score and
    /// the updated calibration gap.
    pub fn resolve(&mut self, id: &str, outcome: bool) -> Result<(f64, f64), String> {
        let pred = self
            .predictions
            .iter_mut()
            .find(|p| p.id == id)
            .ok_or_else(|| format!("prediction '{id}' not found"))?;
        if pred.outcome.is_some() {
            return Err(format!("prediction '{id}' already resolved"));
        }
        let brier = pred.resolve(outcome);
        self.calibration_history.push(brier);
        if self.calibration_history.len() > 200 {
            self.calibration_history.remove(0);
        }
        let gap = self.calibration_gap();
        Ok((brier, gap))
    }

    /// Rolling average Brier score over the recent history (small
    /// adjustment term, mirroring v26's `gap = avg_brier * 0.1`).
    #[must_use]
    pub fn calibration_gap(&self) -> f64 {
        if self.calibration_history.is_empty() {
            0.0
        } else {
            let avg = self.calibration_history.iter().sum::<f64>()
                / self.calibration_history.len() as f64;
            avg * 0.1
        }
    }

    /// Resolved predictions.
    #[must_use]
    pub fn resolved(&self) -> Vec<&CalibrationPrediction> {
        self.predictions
            .iter()
            .filter(|p| p.outcome.is_some())
            .collect()
    }

    /// The full scorecard.
    #[must_use]
    pub fn scorecard(&self) -> BrierScorecard {
        let resolved = self.resolved();
        let unresolved = self.predictions.len() - resolved.len();
        let mut card = BrierScorecard::compute(
            &resolved.iter().map(|p| (*p).clone()).collect::<Vec<_>>(),
            self.calibration_gap(),
        );
        card.total_predictions = self.predictions.len();
        card.unresolved = unresolved;
        card
    }

    /// Serialize for persistence.
    #[must_use]
    pub fn to_json(&self) -> Value {
        serde_json::to_value(self).unwrap_or_else(|_| json!({}))
    }

    /// Restore from JSON.
    pub fn from_json(&mut self, value: &Value) -> Result<(), String> {
        let restored: Self = serde_json::from_value(value.clone()).map_err(|e| e.to_string())?;
        *self = restored;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn record_assigns_ids_and_adjusts() {
        let mut store = CalibrationStore::new();
        let p = store.record("It will rain", 0.8, 0.6, "weather");
        assert_eq!(p.id, "pred-000001");
        assert!((p.probability - 0.8).abs() < 1e-9);
        assert_eq!(store.predictions.len(), 1);
    }

    #[test]
    fn resolve_computes_brier() {
        let mut store = CalibrationStore::new();
        let p = store.record("It will rain", 0.8, 0.6, "weather");
        let (brier, _) = store.resolve(&p.id, true).unwrap();
        assert!((brier - 0.04).abs() < 1e-9);
        // Resolving twice is an error
        assert!(store.resolve(&p.id, false).is_err());
    }

    #[test]
    fn resolve_missing_errors() {
        let mut store = CalibrationStore::new();
        assert!(store.resolve("nope", true).is_err());
    }

    #[test]
    fn scorecard_perfect_calibration() {
        let mut store = CalibrationStore::new();
        // Perfect predictions: p = o for every resolved forecast
        for (p, o) in [
            (0.9, true),
            (0.9, true),
            (0.9, true),
            (0.1, false),
            (0.1, false),
            (0.1, false),
        ] {
            let pred = store.record("s", p, 0.5, "sc");
            store.resolve(&pred.id, o).unwrap();
        }
        let card = store.scorecard();
        assert_eq!(card.resolved, 6);
        assert!(
            card.avg_brier_score < 0.02,
            "perfect calibration: {}",
            card.avg_brier_score
        );
        assert!(card.perfect_calibration);
        assert!(card.skill_score > 0.9, "skill: {}", card.skill_score);
        assert!(card.reliability < 0.02, "reliability: {}", card.reliability);
    }

    #[test]
    fn scorecard_inverted_predictions_are_bad() {
        let mut store = CalibrationStore::new();
        // Anti-calibrated: predict 0.9 when outcomes are mostly false
        for o in [false, false, false, false, false, true] {
            let pred = store.record("s", 0.9, 0.5, "sc");
            store.resolve(&pred.id, o).unwrap();
        }
        let card = store.scorecard();
        assert!(
            card.avg_brier_score > 0.6,
            "anti-calibrated Brier: {}",
            card.avg_brier_score
        );
        assert!(!card.perfect_calibration);
        assert!(
            card.skill_score < 0.0,
            "negative skill (vs climatology): {}",
            card.skill_score
        );
        assert!(
            card.reliability > 0.3,
            "high reliability term: {}",
            card.reliability
        );
    }

    #[test]
    fn empty_scorecard_does_not_panic() {
        let store = CalibrationStore::new();
        let card = store.scorecard();
        assert_eq!(card.resolved, 0);
        assert_eq!(card.total_predictions, 0);
        assert_eq!(card.calibration_bins.len(), 10);
    }

    #[test]
    fn json_roundtrip() {
        let mut store = CalibrationStore::new();
        let p = store.record("s", 0.7, 0.5, "sc");
        store.resolve(&p.id, true).unwrap();
        let json = store.to_json();
        let mut restored = CalibrationStore::new();
        restored.from_json(&json).unwrap();
        assert_eq!(restored.predictions.len(), 1);
        assert_eq!(restored.predictions[0].id, "pred-000001");
        let card = restored.scorecard();
        assert_eq!(card.resolved, 1);
    }
}
