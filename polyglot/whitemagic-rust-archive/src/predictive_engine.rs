//! Predictive Engine - Time-Series Forecasting (PSR-004)
//! Target: 30× speedup for prediction operations

use pyo3::prelude::*;
use std::collections::VecDeque;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Prediction {
    #[pyo3(get)]
    pub timestamp: u64,
    #[pyo3(get)]
    pub value: f64,
    #[pyo3(get)]
    pub confidence: f64,
}

#[pymethods]
impl Prediction {
    #[new]
    fn new(timestamp: u64, value: f64, confidence: f64) -> Self {
        Self {
            timestamp,
            value,
            confidence,
        }
    }
}

#[pyclass]
pub struct PyPredictiveEngine {
    history: VecDeque<(u64, f64)>,
    window_size: usize,
}

#[pymethods]
impl PyPredictiveEngine {
    #[new]
    fn new(window_size: Option<usize>) -> Self {
        Self {
            history: VecDeque::new(),
            window_size: window_size.unwrap_or(10),
        }
    }

    fn add_observation(&mut self, timestamp: u64, value: f64) {
        self.history.push_back((timestamp, value));
        
        if self.history.len() > self.window_size * 2 {
            self.history.pop_front();
        }
    }

    fn predict_next(&self) -> Option<Prediction> {
        if self.history.len() < 2 {
            return None;
        }
        
        let recent: Vec<f64> = self.history
            .iter()
            .rev()
            .take(self.window_size)
            .map(|(_, v)| *v)
            .collect();
        
        let mean = recent.iter().sum::<f64>() / recent.len() as f64;
        
        let trend = if recent.len() >= 2 {
            (recent[0] - recent[recent.len() - 1]) / (recent.len() - 1) as f64
        } else {
            0.0
        };
        
        let next_value = mean + trend;
        
        let variance = recent
            .iter()
            .map(|v| (v - mean).powi(2))
            .sum::<f64>() / recent.len() as f64;
        
        let confidence = 1.0 / (1.0 + variance.sqrt());
        
        let last_timestamp = self.history.back().map(|(t, _)| *t).unwrap_or(0);
        
        Some(Prediction {
            timestamp: last_timestamp + 1,
            value: next_value,
            confidence,
        })
    }

    fn predict_multiple(&self, steps: usize) -> Vec<Prediction> {
        let mut predictions = Vec::new();
        let mut temp_engine = self.clone();
        
        for _i in 0..steps {
            if let Some(pred) = temp_engine.predict_next() {
                predictions.push(pred.clone());
                temp_engine.add_observation(pred.timestamp, pred.value);
            } else {
                break;
            }
        }
        
        predictions
    }

    fn calculate_trend(&self) -> f64 {
        if self.history.len() < 2 {
            return 0.0;
        }
        
        let values: Vec<f64> = self.history.iter().map(|(_, v)| *v).collect();
        
        let n = values.len() as f64;
        let sum_x: f64 = (0..values.len()).map(|i| i as f64).sum();
        let sum_y: f64 = values.iter().sum();
        let sum_xy: f64 = values.iter().enumerate().map(|(i, &y)| i as f64 * y).sum();
        let sum_x2: f64 = (0..values.len()).map(|i| (i as f64).powi(2)).sum();
        
        let slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x.powi(2));
        
        slope
    }

    fn detect_anomaly(&self, value: f64, threshold: f64) -> bool {
        if self.history.is_empty() {
            return false;
        }
        
        let values: Vec<f64> = self.history.iter().map(|(_, v)| *v).collect();
        let mean = values.iter().sum::<f64>() / values.len() as f64;
        let std_dev = (values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / values.len() as f64).sqrt();
        
        // Use 5% of mean as minimum std_dev to avoid false positives on constant series
        let std_dev_floor = std_dev.max(mean.abs() * 0.05).max(1.0);
        (value - mean).abs() > threshold * std_dev_floor
    }

    fn observation_count(&self) -> usize {
        self.history.len()
    }

    fn clear(&mut self) {
        self.history.clear();
    }
}

impl Clone for PyPredictiveEngine {
    fn clone(&self) -> Self {
        Self {
            history: self.history.clone(),
            window_size: self.window_size,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_creation() {
        let engine = PyPredictiveEngine::new(Some(10));
        assert_eq!(engine.observation_count(), 0);
    }

    #[test]
    fn test_add_observation() {
        let mut engine = PyPredictiveEngine::new(None);
        engine.add_observation(1, 10.0);
        
        assert_eq!(engine.observation_count(), 1);
    }

    #[test]
    fn test_predict_next() {
        let mut engine = PyPredictiveEngine::new(Some(5));
        
        for i in 0..10 {
            engine.add_observation(i, i as f64);
        }
        
        let prediction = engine.predict_next();
        assert!(prediction.is_some());
    }

    #[test]
    fn test_calculate_trend() {
        let mut engine = PyPredictiveEngine::new(None);
        
        for i in 0..5 {
            engine.add_observation(i, i as f64 * 2.0);
        }
        
        let trend = engine.calculate_trend();
        assert!(trend > 0.0);
    }

    #[test]
    fn test_detect_anomaly() {
        let mut engine = PyPredictiveEngine::new(None);
        
        for i in 0..10 {
            engine.add_observation(i, 10.0);
        }
        
        assert!(engine.detect_anomaly(100.0, 2.0));
        assert!(!engine.detect_anomaly(10.5, 2.0));
    }
}
