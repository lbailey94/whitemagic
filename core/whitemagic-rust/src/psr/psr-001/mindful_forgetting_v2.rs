//! Mindful Forgetting
//! Intelligent forgetting based on relevance and importance

use pyo3::prelude::*;

#[pyclass]
pub struct MindfulForgetting {
    protected_ids: Vec<String>,
    forgetting_threshold: f64,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl MindfulForgetting {
    #[new]
    fn new(threshold: Option<f64>) -> Self {
        Self {
            protected_ids: Vec::new(),
            forgetting_threshold: threshold.unwrap_or(0.3),
        }
    }
    
    fn protect_memory(&mut self, memory_id: String) -> PyResult<()> {
        if !self.protected_ids.contains(&memory_id) {
            self.protected_ids.push(memory_id);
        }
        Ok(())
    }
    
    fn should_forget(
        &self,
        memory_id: String,
        relevance: f64,
        importance: f64,
        last_access_days: f64
    ) -> PyResult<bool> {
        // Never forget protected memories
        if self.protected_ids.contains(&memory_id) {
            return Ok(false);
        }
        
        // Calculate forgetting score
        let recency_penalty = (last_access_days / 30.0).min(1.0);
        let retention_score = (relevance * 0.4 + importance * 0.6) * (1.0 - recency_penalty * 0.5);
        
        Ok(retention_score < self.forgetting_threshold)
    }
    
    fn batch_evaluate(
        &self,
        memories: Vec<(String, f64, f64, f64)> // (id, relevance, importance, days)
    ) -> PyResult<Vec<String>> {
        let to_forget: Vec<String> = memories
            .into_iter()
            .filter_map(|(id, rel, imp, days)| {
                if self.should_forget(id.clone(), rel, imp, days).unwrap_or(false) {
                    Some(id)
                } else {
                    None
                }
            })
            .collect();
        
        Ok(to_forget)
    }
}
