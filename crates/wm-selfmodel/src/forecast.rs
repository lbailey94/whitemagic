//! Forecasting — linear extrapolation + EWMA prediction.

use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

use crate::metrics::MetricSample;

/// A forecast prediction for a metric.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Forecast {
    /// Predicted value `horizon` samples into the future.
    pub predicted_value: f32,
    /// Rate of change per sample (slope from linear regression).
    pub slope: f32,
    /// EWMA of recent values (smoothing out noise).
    pub ewma: f32,
    /// Confidence in the prediction (0.0–1.0).
    /// Based on variance of residuals — lower variance = higher confidence.
    pub confidence: f32,
    /// How many samples ahead the prediction is.
    pub horizon: usize,
}

/// Forecast engine — produces predictions from historical data.
///
/// Uses a hybrid approach:
/// 1. Linear extrapolation from the slope of recent samples
/// 2. EWMA smoothing to reduce noise sensitivity
/// 3. Confidence from residual variance (how well linear fit matches data)
pub struct ForecastEngine {
    /// EWMA smoothing factor (0.0–1.0). Higher = more weight on recent.
    ewma_alpha: f32,
}

impl ForecastEngine {
    /// Create a new forecast engine with default alpha (0.3).
    #[must_use]
    pub const fn new() -> Self {
        Self { ewma_alpha: 0.3 }
    }

    /// Create with a custom EWMA alpha.
    #[must_use]
    pub const fn with_alpha(alpha: f32) -> Self {
        Self {
            ewma_alpha: alpha.clamp(0.0, 1.0),
        }
    }

    /// Forecast from a history of samples.
    ///
    /// Combines linear extrapolation (for trend) with EWMA (for noise resistance).
    /// Confidence is derived from how well the linear model fits the data
    /// (R²-like measure from residual variance).
    ///
    /// Outlier values are clamped to ±3 standard deviations from the mean
    /// before fitting, preventing a single extreme spike from dominating
    /// the forecast.
    #[must_use]
    pub fn forecast(&self, history: &VecDeque<MetricSample>, horizon: usize) -> Forecast {
        let n = history.len();
        let raw_values: Vec<f32> = history.iter().map(|s| s.value).collect();

        // Clamp outliers to ±3σ from mean before fitting
        let values = clamp_outliers(&raw_values);

        // Compute linear regression (least squares)
        let (slope, intercept) = linear_regression(&values);
        let predicted_linear = slope.mul_add((n + horizon - 1) as f32, intercept);

        // Compute EWMA
        let ewma = compute_ewma(&values, self.ewma_alpha);

        // Compute confidence from R² (coefficient of determination)
        let r_squared = compute_r_squared(&values, slope, intercept);

        // Blend linear prediction with EWMA (weight by confidence)
        let blended = r_squared.mul_add(predicted_linear, (1.0 - r_squared) * ewma);

        Forecast {
            predicted_value: blended,
            slope,
            ewma,
            confidence: r_squared,
            horizon,
        }
    }
}

impl Default for ForecastEngine {
    fn default() -> Self {
        Self::new()
    }
}

/// Compute linear regression (slope, intercept) from a series of values.
/// x = index (0, 1, 2, ...), y = value.
fn linear_regression(values: &[f32]) -> (f32, f32) {
    let n = values.len() as f32;
    if n < 2.0 {
        return (0.0, values.first().copied().unwrap_or(0.0));
    }

    let sum_x: f32 = (0..values.len()).map(|i| i as f32).sum();
    let sum_y: f32 = values.iter().copied().sum();
    let sum_xy: f32 = values.iter().enumerate().map(|(i, &v)| i as f32 * v).sum();
    let sum_x_sq: f32 = (0..values.len()).map(|i| (i as f32).powi(2)).sum();

    let denominator = n.mul_add(sum_x_sq, -(sum_x * sum_x));
    if denominator.abs() < f32::EPSILON {
        return (0.0, sum_y / n);
    }

    let slope = n.mul_add(sum_xy, -(sum_x * sum_y)) / denominator;
    let intercept = slope.mul_add(-sum_x, sum_y) / n;
    (slope, intercept)
}

/// Compute R² (coefficient of determination) — how well the linear model fits.
/// Returns 0.0–1.0. Higher = better fit = more confidence in extrapolation.
fn compute_r_squared(values: &[f32], slope: f32, intercept: f32) -> f32 {
    let n = values.len();
    if n < 3 {
        // Not enough points to assess fit
        return 0.5;
    }

    let mean_y: f32 = values.iter().copied().sum::<f32>() / n as f32;

    let mut ss_res = 0.0_f32; // Residual sum of squares
    let mut ss_tot = 0.0_f32; // Total sum of squares

    for (i, &y) in values.iter().enumerate() {
        let predicted = slope.mul_add(i as f32, intercept);
        ss_res += (y - predicted).powi(2);
        ss_tot += (y - mean_y).powi(2);
    }

    if ss_tot < f32::EPSILON {
        // All values are the same — perfect fit, but no trend
        return 0.9;
    }

    let r_squared = 1.0 - ss_res / ss_tot;
    r_squared.clamp(0.0, 1.0)
}

/// Compute EWMA (exponentially weighted moving average).
fn compute_ewma(values: &[f32], alpha: f32) -> f32 {
    if values.is_empty() {
        return 0.0;
    }
    let alpha = alpha.clamp(0.0, 1.0);
    let mut ewma = values[0];
    for &v in &values[1..] {
        ewma = alpha.mul_add(v, (1.0 - alpha) * ewma);
    }
    ewma
}

/// Clamp outlier values using median and MAD (median absolute deviation).
///
/// Uses the median (robust to outliers) and MAD scaled by 1.4826 (to make
/// it comparable to std dev) with a 3.5 threshold. This prevents a single
/// extreme spike (e.g., f32::MAX, sensor glitch) from dominating the linear
/// regression and EWMA computations.
fn clamp_outliers(values: &[f32]) -> Vec<f32> {
    if values.len() < 4 {
        return values.to_vec();
    }

    // Compute median
    let mut sorted: Vec<f32> = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let mid = sorted.len() / 2;
    let median = if sorted.len() % 2 == 0 {
        f32::midpoint(sorted[mid - 1], sorted[mid])
    } else {
        sorted[mid]
    };

    // Compute MAD (median absolute deviation)
    let abs_devs: Vec<f32> = values.iter().map(|&v| (v - median).abs()).collect();
    let mut sorted_devs = abs_devs.clone();
    sorted_devs.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let mad = if sorted_devs.len() % 2 == 0 {
        f32::midpoint(sorted_devs[mid - 1], sorted_devs[mid])
    } else {
        sorted_devs[mid]
    };

    // Scale MAD to be comparable to std dev: σ ≈ 1.4826 * MAD
    let scaled_mad = 1.4826 * mad;
    if scaled_mad < f32::EPSILON {
        // MAD is 0 — more than half the values are identical (at the median).
        // Use the median magnitude as a fallback scale, since any deviation
        // from the majority value is suspicious.
        let has_non_zero_dev = abs_devs.iter().any(|&d| d > f32::EPSILON);
        if !has_non_zero_dev {
            // All values are identical — no outliers
            return values.to_vec();
        }
        // Use median magnitude as scale (100% of |median|, min 0.01)
        let fallback_scale = median.abs().max(0.01);
        let threshold = 3.0 * fallback_scale;
        let lower = median - threshold;
        let upper = median + threshold;
        return values.iter().map(|&v| v.clamp(lower, upper)).collect();
    }

    // Clamp at ±3.5 scaled MAD from median (3.5 is a common robust threshold)
    let threshold = 3.5 * scaled_mad;
    let lower = median - threshold;
    let upper = median + threshold;

    values.iter().map(|&v| v.clamp(lower, upper)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;

    fn make_history(values: &[f32]) -> VecDeque<MetricSample> {
        values
            .iter()
            .map(|&v| MetricSample {
                kind: crate::metrics::MetricKind::CpuLoad,
                value: v,
                timestamp: Utc::now(),
            })
            .collect()
    }

    #[test]
    fn forecast_linear_trend() {
        let history = make_history(&[0.1, 0.2, 0.3, 0.4, 0.5]);
        let engine = ForecastEngine::new();
        let f = engine.forecast(&history, 3);
        assert!(f.predicted_value > 0.5);
        assert!(f.slope > 0.0);
        assert!((f.slope - 0.1).abs() < 0.01);
        assert!(f.confidence > 0.9); // Perfect linear fit
    }

    #[test]
    fn forecast_decreasing_trend() {
        let history = make_history(&[0.5, 0.4, 0.3, 0.2, 0.1]);
        let engine = ForecastEngine::new();
        let f = engine.forecast(&history, 2);
        assert!(f.predicted_value < 0.1);
        assert!(f.slope < 0.0);
    }

    #[test]
    fn forecast_noisy_data_lower_confidence() {
        let history = make_history(&[0.3, 0.7, 0.2, 0.6, 0.3]);
        let engine = ForecastEngine::new();
        let f = engine.forecast(&history, 3);
        assert!(f.confidence < 0.8); // Noisy data = lower confidence
    }

    #[test]
    fn forecast_constant_data() {
        let history = make_history(&[0.5, 0.5, 0.5, 0.5]);
        let engine = ForecastEngine::new();
        let f = engine.forecast(&history, 5);
        assert!((f.predicted_value - 0.5).abs() < 0.1);
        assert!((f.slope - 0.0).abs() < 0.01);
        assert!(f.confidence > 0.8);
    }

    #[test]
    fn forecast_two_points() {
        let history = make_history(&[0.3, 0.5]);
        let engine = ForecastEngine::new();
        let f = engine.forecast(&history, 2);
        assert!(f.predicted_value > 0.5);
        assert!(f.slope > 0.0);
    }

    #[test]
    fn forecast_ewma_blends_with_linear() {
        let history = make_history(&[0.1, 0.9, 0.1, 0.9, 0.1]);
        let engine = ForecastEngine::new();
        let f = engine.forecast(&history, 3);
        // With oscillating data, prediction should be somewhere in the middle
        assert!(f.predicted_value > 0.0 && f.predicted_value < 1.0);
    }

    #[test]
    fn forecast_horizon_affects_prediction() {
        let history = make_history(&[0.1, 0.2, 0.3, 0.4, 0.5]);
        let engine = ForecastEngine::new();
        let f1 = engine.forecast(&history, 1);
        let f10 = engine.forecast(&history, 10);
        assert!(f10.predicted_value > f1.predicted_value);
    }

    #[test]
    fn forecast_engine_default() {
        let engine = ForecastEngine::default();
        let history = make_history(&[0.1, 0.2, 0.3]);
        let f = engine.forecast(&history, 1);
        assert!(f.predicted_value > 0.2);
    }

    #[test]
    fn forecast_engine_custom_alpha() {
        let engine = ForecastEngine::with_alpha(0.8);
        let history = make_history(&[0.1, 0.5, 0.9]);
        let f = engine.forecast(&history, 1);
        // High alpha = more weight on recent = prediction closer to 0.9
        assert!(f.ewma > 0.5);
    }

    #[test]
    fn forecast_serialization() {
        let f = Forecast {
            predicted_value: 0.5,
            slope: 0.1,
            ewma: 0.4,
            confidence: 0.9,
            horizon: 5,
        };
        let json = serde_json::to_string(&f).unwrap();
        let back: Forecast = serde_json::from_str(&json).unwrap();
        assert!((back.predicted_value - 0.5).abs() < 0.001);
        assert_eq!(back.horizon, 5);
    }

    #[test]
    fn linear_regression_perfect_fit() {
        let values = [1.0, 2.0, 3.0, 4.0, 5.0];
        let (slope, intercept) = linear_regression(&values);
        assert!((slope - 1.0).abs() < 0.001);
        assert!((intercept - 1.0).abs() < 0.001);
    }

    #[test]
    fn linear_regression_flat() {
        let values = [0.5, 0.5, 0.5, 0.5];
        let (slope, intercept) = linear_regression(&values);
        assert!((slope - 0.0).abs() < 0.001);
        assert!((intercept - 0.5).abs() < 0.001);
    }

    #[test]
    fn r_squared_perfect_linear() {
        let values = [1.0, 2.0, 3.0, 4.0, 5.0];
        let r2 = compute_r_squared(&values, 1.0, 1.0);
        assert!((r2 - 1.0).abs() < 0.001);
    }

    #[test]
    fn r_squared_noisy() {
        let values = [0.3, 0.7, 0.2, 0.6, 0.3];
        let (slope, intercept) = linear_regression(&values);
        let r2 = compute_r_squared(&values, slope, intercept);
        assert!(r2 < 0.5);
    }

    #[test]
    fn r_squared_constant() {
        let values = [0.5, 0.5, 0.5, 0.5];
        let r2 = compute_r_squared(&values, 0.0, 0.5);
        assert!(r2 > 0.8);
    }

    #[test]
    fn ewma_computation() {
        let values = [0.1, 0.2, 0.3, 0.4, 0.5];
        let ewma = compute_ewma(&values, 0.3);
        assert!(ewma > 0.1 && ewma < 0.5);
    }

    #[test]
    fn ewma_empty() {
        let ewma = compute_ewma(&[], 0.3);
        assert_eq!(ewma, 0.0);
    }

    #[test]
    fn ewma_single_value() {
        let ewma = compute_ewma(&[0.42], 0.3);
        assert!((ewma - 0.42).abs() < 0.001);
    }

    #[test]
    fn forecast_outlier_does_not_dominate() {
        // Stable history with one extreme spike
        let history = make_history(&[0.3, 0.3, 0.3, 0.3, 100.0, 0.3, 0.3, 0.3, 0.3]);
        let engine = ForecastEngine::new();
        let f = engine.forecast(&history, 3);
        // Without clamping, the 100.0 spike would dominate the forecast.
        // With clamping, the prediction should stay reasonable.
        assert!(
            f.predicted_value < 10.0,
            "outlier should not dominate forecast: got {}",
            f.predicted_value
        );
        assert!(
            f.slope.abs() < 5.0,
            "slope should not be dominated by outlier: got {}",
            f.slope
        );
    }

    #[test]
    fn forecast_extreme_outlier_clamped() {
        // f32::MAX in history should not produce NaN or infinite forecast
        let history = make_history(&[0.3, 0.3, 0.3, 0.3, f32::MAX, 0.3, 0.3, 0.3, 0.3]);
        let engine = ForecastEngine::new();
        let f = engine.forecast(&history, 3);
        assert!(!f.predicted_value.is_nan(), "forecast should not be NaN");
        assert!(
            !f.predicted_value.is_infinite(),
            "forecast should not be infinite"
        );
        assert!(
            f.predicted_value < 10.0,
            "extreme outlier should be clamped: got {}",
            f.predicted_value
        );
    }

    #[test]
    fn forecast_negative_outlier_clamped() {
        // Extreme negative outlier
        let history = make_history(&[0.5, 0.5, 0.5, 0.5, -1000.0, 0.5, 0.5, 0.5, 0.5]);
        let engine = ForecastEngine::new();
        let f = engine.forecast(&history, 3);
        assert!(!f.predicted_value.is_nan(), "forecast should not be NaN");
        assert!(
            f.predicted_value > -10.0,
            "negative outlier should be clamped: got {}",
            f.predicted_value
        );
    }

    #[test]
    fn clamp_outliers_preserves_normal_values() {
        let values = vec![0.1, 0.2, 0.3, 0.4, 0.5];
        let clamped = clamp_outliers(&values);
        for (orig, clamped_val) in values.iter().zip(clamped.iter()) {
            assert!((orig - clamped_val).abs() < 0.001);
        }
    }

    #[test]
    fn clamp_outliers_clamps_extreme() {
        let values = vec![0.3_f32, 0.3, 0.3, 0.3, 100.0, 0.3, 0.3, 0.3, 0.3];
        let clamped = clamp_outliers(&values);
        // The 100.0 should be clamped down significantly
        assert!(
            clamped[4] < 10.0,
            "outlier should be clamped: got {}",
            clamped[4]
        );
        // Normal values should be unchanged
        for i in [0, 1, 2, 3, 5, 6, 7, 8] {
            assert!((clamped[i] - 0.3).abs() < 0.001);
        }
    }

    #[test]
    fn clamp_outliers_short_input_unchanged() {
        let values = vec![0.1, 0.2, 0.3];
        let clamped = clamp_outliers(&values);
        assert_eq!(clamped, values);
    }
}
