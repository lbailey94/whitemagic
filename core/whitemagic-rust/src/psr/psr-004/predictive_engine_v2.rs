//! Predictive Engine
//! Predicts future states based on patterns

use pyo3::prelude::*;
use std::collections::VecDeque;

#[pyclass]
pub struct PredictiveEngine {
    history: VecDeque<f64>,
    max_history: usize,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl PredictiveEngine {
    #[new]
    fn new(max_history: Option<usize>) -> Self {
        Self {
            history: VecDeque::new(),
            max_history: max_history.unwrap_or(100),
        }
    }
    
    fn add_observation(&mut self, value: f64) -> PyResult<()> {
        if self.history.len() >= self.max_history {
            self.history.pop_front();
        }
        self.history.push_back(value);
        Ok(())
    }
    
    fn predict_next(&self) -> PyResult<f64> {
        if self.history.is_empty() {
            return Ok(0.0);
        }
        
        // Simple moving average prediction
        let sum: f64 = self.history.iter().sum();
        let avg = sum / self.history.len() as f64;
        
        Ok(avg)
    }
    
    fn predict_trend(&self) -> PyResult<String> {
        if self.history.len() < 2 {
            return Ok("unknown".to_string());
        }
        
        let recent: Vec<f64> = self.history.iter().rev().take(5).cloned().collect();
        let first = recent.last().unwrap();
        let last = recent.first().unwrap();
        
        if last > first {
            Ok("increasing".to_string())
        } else if last < first {
            Ok("decreasing".to_string())
        } else {
            Ok("stable".to_string())
        }
    }
}
