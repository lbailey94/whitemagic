//! Mindful Forgetting - Decay Algorithms (PSR-001)
//! Target: 20-50× speedup for memory decay calculations

use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
pub struct PyDecayEngine {
    decay_rate: f64,
    min_importance: f64,
}

#[pymethods]
impl PyDecayEngine {
    #[new]
    fn new(decay_rate: Option<f64>, min_importance: Option<f64>) -> Self {
        Self {
            decay_rate: decay_rate.unwrap_or(0.95),
            min_importance: min_importance.unwrap_or(0.1),
        }
    }

    fn compute_decay(&self, importance: f64, age_days: f64) -> f64 {
        let decayed = importance * self.decay_rate.powf(age_days);
        decayed.max(self.min_importance)
    }

    fn batch_decay(&self, memories: Vec<(String, f64, f64)>) -> HashMap<String, f64> {
        memories
            .into_iter()
            .map(|(id, importance, age)| {
                (id, self.compute_decay(importance, age))
            })
            .collect()
    }

    fn should_forget(&self, importance: f64, age_days: f64, threshold: f64) -> bool {
        self.compute_decay(importance, age_days) < threshold
    }

    fn exponential_decay(&self, initial: f64, time: f64, half_life: f64) -> f64 {
        initial * 0.5_f64.powf(time / half_life)
    }

    fn ebbinghaus_curve(&self, initial: f64, time_hours: f64) -> f64 {
        initial / (1.0 + 1.25 * time_hours.ln())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compute_decay() {
        let engine = PyDecayEngine::new(Some(0.9), Some(0.1));
        let decayed = engine.compute_decay(1.0, 10.0);
        assert!(decayed < 1.0);
        assert!(decayed >= 0.1);
    }

    #[test]
    fn test_batch_decay() {
        let engine = PyDecayEngine::new(None, None);
        let memories = vec![
            ("m1".to_string(), 1.0, 5.0),
            ("m2".to_string(), 0.8, 10.0),
        ];
        
        let results = engine.batch_decay(memories);
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_should_forget() {
        let engine = PyDecayEngine::new(Some(0.8), Some(0.1));
        assert!(!engine.should_forget(1.0, 1.0, 0.5));
        assert!(engine.should_forget(0.5, 20.0, 0.5));
    }

    #[test]
    fn test_exponential_decay() {
        let engine = PyDecayEngine::new(None, None);
        let decayed = engine.exponential_decay(100.0, 10.0, 10.0);
        assert!((decayed - 50.0).abs() < 0.1);
    }
}
