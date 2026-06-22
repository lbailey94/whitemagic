//! Reconsolidation
//! Memory reconsolidation when recalled

use pyo3::prelude::*;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

#[pyclass]
pub struct Reconsolidation {
    reconsolidation_events: HashMap<String, Vec<u64>>,
    strength_boost: f64,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl Reconsolidation {
    #[new]
    fn new(boost: Option<f64>) -> Self {
        Self {
            reconsolidation_events: HashMap::new(),
            strength_boost: boost.unwrap_or(0.1),
        }
    }
    
    fn trigger_reconsolidation(&mut self, memory_id: String) -> PyResult<f64> {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        self.reconsolidation_events
            .entry(memory_id)
            .or_insert_with(Vec::new)
            .push(timestamp);
        
        Ok(self.strength_boost)
    }
    
    fn get_reconsolidation_count(&self, memory_id: String) -> PyResult<usize> {
        Ok(self.reconsolidation_events
            .get(&memory_id)
            .map(|v| v.len())
            .unwrap_or(0))
    }
    
    fn calculate_boosted_strength(
        &self,
        memory_id: String,
        base_strength: f64
    ) -> PyResult<f64> {
        let count = self.get_reconsolidation_count(memory_id)?;
        let boost = self.strength_boost * count as f64;
        
        Ok((base_strength + boost).min(1.0))
    }
}
