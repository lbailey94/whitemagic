//! Metrics Collector - Performance metrics tracking

use pyo3::prelude::*;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

#[pyclass]
pub struct MetricsCollector {
    metrics: HashMap<String, Vec<(u64, f64)>>,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl MetricsCollector {
    #[new]
    fn new() -> Self {
        Self {
            metrics: HashMap::new(),
        }
    }
    
    fn record_metric(&mut self, name: String, value: f64) -> PyResult<()> {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        self.metrics
            .entry(name)
            .or_insert_with(Vec::new)
            .push((timestamp, value));
        
        Ok(())
    }
    
    fn get_metric_stats(&self, name: String) -> PyResult<(f64, f64, f64)> {
        let values: Vec<f64> = self.metrics
            .get(&name)
            .map(|v| v.iter().map(|(_, val)| *val).collect())
            .unwrap_or_default();
        
        if values.is_empty() {
            return Ok((0.0, 0.0, 0.0));
        }
        
        let sum: f64 = values.iter().sum();
        let mean = sum / values.len() as f64;
        let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
        let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        
        Ok((mean, min, max))
    }
}
