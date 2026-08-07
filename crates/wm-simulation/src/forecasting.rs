//! Time series forecasting with confidence intervals.
//!
//! Supports multiple methods: moving average, exponential smoothing,
//! and linear trend projection.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

// ── Forecast Method ───────────────────────────────────────────────────

/// Forecasting method.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ForecastMethod {
    /// Simple moving average.
    MovingAverage,
    /// Exponential smoothing (single).
    ExponentialSmoothing,
    /// Linear trend projection.
    LinearTrend,
}

impl ForecastMethod {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::MovingAverage => "moving_average",
            Self::ExponentialSmoothing => "exponential_smoothing",
            Self::LinearTrend => "linear_trend",
        }
    }
}

// ── Forecast Result ───────────────────────────────────────────────────

/// Result of a forecast.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ForecastResult {
    /// Forecasted values.
    pub forecast: Vec<f64>,
    /// Method used.
    pub method: ForecastMethod,
    /// 95% CI lower bounds.
    pub ci_lower: Vec<f64>,
    /// 95% CI upper bounds.
    pub ci_upper: Vec<f64>,
    /// Mean absolute error of the fit.
    pub mae: f64,
    /// Root mean squared error of the fit.
    pub rmse: f64,
    /// Number of data points used.
    pub n_points: usize,
}

impl ForecastResult {
    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "forecast": self.forecast,
            "method": self.method.as_str(),
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "mae": self.mae,
            "rmse": self.rmse,
            "n_points": self.n_points,
        })
    }
}

// ── Forecaster ────────────────────────────────────────────────────────

/// Time series forecaster.
pub struct Forecaster {
    /// Smoothing parameter for exponential smoothing.
    alpha: f64,
    /// Window size for moving average.
    window: usize,
}

impl Default for Forecaster {
    fn default() -> Self {
        Self {
            alpha: 0.3,
            window: 5,
        }
    }
}

impl std::fmt::Debug for Forecaster {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Forecaster")
            .field("alpha", &self.alpha)
            .field("window", &self.window)
            .finish()
    }
}

impl Forecaster {
    /// Create a new forecaster.
    #[must_use]
    pub const fn new(alpha: f64, window: usize) -> Self {
        Self { alpha, window }
    }

    /// Forecast using the specified method.
    #[must_use]
    pub fn forecast(&self, data: &[f64], horizon: usize, method: ForecastMethod) -> ForecastResult {
        if data.is_empty() {
            return ForecastResult {
                forecast: vec![0.0; horizon],
                method,
                ci_lower: vec![0.0; horizon],
                ci_upper: vec![0.0; horizon],
                mae: 0.0,
                rmse: 0.0,
                n_points: 0,
            };
        }

        let (forecast, fit_errors) = match method {
            ForecastMethod::MovingAverage => self.moving_average_forecast(data, horizon),
            ForecastMethod::ExponentialSmoothing => self.exp_smoothing_forecast(data, horizon),
            ForecastMethod::LinearTrend => self.linear_trend_forecast(data, horizon),
        };

        let mae = if fit_errors.is_empty() {
            0.0
        } else {
            fit_errors.iter().sum::<f64>().abs() / fit_errors.len() as f64
        };
        let rmse = if fit_errors.is_empty() {
            0.0
        } else {
            (fit_errors.iter().map(|e| e * e).sum::<f64>() / fit_errors.len() as f64).sqrt()
        };

        // CI based on RMSE
        let ci_width = 1.96 * rmse;
        let ci_lower: Vec<f64> = forecast.iter().map(|f| f - ci_width).collect();
        let ci_upper: Vec<f64> = forecast.iter().map(|f| f + ci_width).collect();

        ForecastResult {
            forecast,
            method,
            ci_lower,
            ci_upper,
            mae,
            rmse,
            n_points: data.len(),
        }
    }

    /// Moving average forecast.
    fn moving_average_forecast(&self, data: &[f64], horizon: usize) -> (Vec<f64>, Vec<f64>) {
        let window = self.window.min(data.len());
        if window == 0 {
            return (vec![data[0]; horizon], Vec::new());
        }

        // Compute moving averages
        let mut mas = Vec::new();
        for i in window..=data.len() {
            let ma = data[i - window..i].iter().sum::<f64>() / window as f64;
            mas.push(ma);
        }

        // Forecast = last moving average
        let last_ma = *mas.last().unwrap_or(&data[data.len() - 1]);
        let forecast = vec![last_ma; horizon];

        // Fit errors (actual - MA)
        let errors: Vec<f64> = mas
            .iter()
            .zip(data[window..].iter())
            .map(|(ma, actual)| actual - ma)
            .collect();

        (forecast, errors)
    }

    /// Exponential smoothing forecast.
    fn exp_smoothing_forecast(&self, data: &[f64], horizon: usize) -> (Vec<f64>, Vec<f64>) {
        let mut level = data[0];
        let mut fitted = vec![level];

        for &val in &data[1..] {
            let prev_level = level;
            level = self.alpha.mul_add(val, (1.0 - self.alpha) * level);
            fitted.push(prev_level);
        }

        let forecast = vec![level; horizon];
        let errors: Vec<f64> = data.iter().zip(fitted.iter()).map(|(a, f)| a - f).collect();

        (forecast, errors)
    }

    /// Linear trend forecast.
    fn linear_trend_forecast(&self, data: &[f64], horizon: usize) -> (Vec<f64>, Vec<f64>) {
        let n = data.len() as f64;
        let sum_x: f64 = (0..data.len()).map(|i| i as f64).sum();
        let sum_y: f64 = data.iter().sum();
        let sum_xy: f64 = (0..data.len()).map(|i| i as f64 * data[i]).sum();
        let sum_x2: f64 = (0..data.len()).map(|i| (i as f64).powi(2)).sum();

        let slope = n.mul_add(sum_xy, -(sum_x * sum_y)) / n.mul_add(sum_x2, -(sum_x * sum_x));
        let intercept = slope.mul_add(-sum_x, sum_y) / n;

        // Fitted values
        let fitted: Vec<f64> = (0..data.len())
            .map(|i| slope.mul_add(i as f64, intercept))
            .collect();
        let errors: Vec<f64> = data.iter().zip(fitted.iter()).map(|(a, f)| a - f).collect();

        // Forecast
        let forecast: Vec<f64> = (0..horizon)
            .map(|i| slope.mul_add((data.len() + i) as f64, intercept))
            .collect();

        (forecast, errors)
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn forecast_method_as_str() {
        assert_eq!(ForecastMethod::MovingAverage.as_str(), "moving_average");
        assert_eq!(
            ForecastMethod::ExponentialSmoothing.as_str(),
            "exponential_smoothing"
        );
        assert_eq!(ForecastMethod::LinearTrend.as_str(), "linear_trend");
    }

    #[test]
    fn moving_average_forecast() {
        let forecaster = Forecaster::new(0.3, 3);
        let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let result = forecaster.forecast(&data, 3, ForecastMethod::MovingAverage);
        assert_eq!(result.forecast.len(), 3);
        // Last MA of [3,4,5] = 4
        assert!((result.forecast[0] - 4.0).abs() < 0.001);
    }

    #[test]
    fn exp_smoothing_forecast() {
        let forecaster = Forecaster::new(0.5, 3);
        let data = vec![10.0, 12.0, 14.0, 16.0];
        let result = forecaster.forecast(&data, 2, ForecastMethod::ExponentialSmoothing);
        assert_eq!(result.forecast.len(), 2);
        // Should be between 10 and 16
        assert!(result.forecast[0] > 10.0 && result.forecast[0] < 16.0);
    }

    #[test]
    fn linear_trend_forecast() {
        let forecaster = Forecaster::default();
        let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let result = forecaster.forecast(&data, 3, ForecastMethod::LinearTrend);
        assert_eq!(result.forecast.len(), 3);
        // Linear trend: y = 1 + 1*x, so forecast[0] = 1 + 5 = 6
        assert!((result.forecast[0] - 6.0).abs() < 0.001);
        assert!((result.forecast[1] - 7.0).abs() < 0.001);
        assert!((result.forecast[2] - 8.0).abs() < 0.001);
    }

    #[test]
    fn forecast_empty_data() {
        let forecaster = Forecaster::default();
        let result = forecaster.forecast(&[], 3, ForecastMethod::MovingAverage);
        assert_eq!(result.n_points, 0);
        assert_eq!(result.forecast.len(), 3);
    }

    #[test]
    fn forecast_ci_bands() {
        let forecaster = Forecaster::default();
        let data = vec![1.0, 3.0, 2.0, 4.0, 3.0, 5.0];
        let result = forecaster.forecast(&data, 3, ForecastMethod::MovingAverage);
        assert_eq!(result.ci_lower.len(), 3);
        assert_eq!(result.ci_upper.len(), 3);
        // CI lower < forecast < CI upper
        for i in 0..3 {
            assert!(result.ci_lower[i] <= result.forecast[i]);
            assert!(result.ci_upper[i] >= result.forecast[i]);
        }
    }

    #[test]
    fn forecast_rmse_computed() {
        let forecaster = Forecaster::default();
        let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let result = forecaster.forecast(&data, 2, ForecastMethod::LinearTrend);
        // Perfect linear fit → RMSE ≈ 0
        assert!(result.rmse < 0.001);
    }

    #[test]
    fn forecast_mae_computed() {
        let forecaster = Forecaster::default();
        let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let result = forecaster.forecast(&data, 2, ForecastMethod::LinearTrend);
        // Perfect linear fit → MAE ≈ 0
        assert!(result.mae < 0.001);
    }

    #[test]
    fn forecast_result_to_json() {
        let result = ForecastResult {
            forecast: vec![5.0, 6.0],
            method: ForecastMethod::MovingAverage,
            ci_lower: vec![3.0, 4.0],
            ci_upper: vec![7.0, 8.0],
            mae: 0.5,
            rmse: 0.7,
            n_points: 10,
        };
        let json = result.to_json();
        assert_eq!(json["method"], "moving_average");
        assert_eq!(json["n_points"], 10);
    }

    #[test]
    fn linear_trend_negative_slope() {
        let forecaster = Forecaster::default();
        let data = vec![5.0, 4.0, 3.0, 2.0, 1.0];
        let result = forecaster.forecast(&data, 3, ForecastMethod::LinearTrend);
        // y = 6 - 1*x, forecast[0] = 6 - 5 = 0
        assert!((result.forecast[0] - 0.0).abs() < 0.001);
    }
}
