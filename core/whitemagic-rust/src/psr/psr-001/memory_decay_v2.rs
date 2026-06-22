//! Memory Decay
//! Manages memory decay and forgetting curves

use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
pub struct MemoryDecay {
    #[allow(dead_code)]
    decay_rates: HashMap<String, f64>,
    half_life_hours: f64,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl MemoryDecay {
    #[new]
    fn new(half_life: Option<f64>) -> Self {
        Self {
            decay_rates: HashMap::new(),
            half_life_hours: half_life.unwrap_or(168.0), // 1 week default
        }
    }
    
    fn calculate_decay(&self, age_hours: f64, initial_strength: f64) -> PyResult<f64> {
        // Exponential decay: strength = initial * e^(-λt)
        let decay_constant = 0.693 / self.half_life_hours;
        let current_strength = initial_strength * (-decay_constant * age_hours).exp();
        
        Ok(current_strength)
    }
    
    fn should_forget(&self, age_hours: f64, importance: f64) -> PyResult<bool> {
        let current_strength = self.calculate_decay(age_hours, importance)?;
        Ok(current_strength < 0.1) // Forget if below 10% strength
    }
    
    fn batch_decay(
        &self,
        memories: Vec<(f64, f64)> // (age_hours, importance)
    ) -> PyResult<Vec<f64>> {
        memories
            .into_iter()
            .map(|(age, importance)| self.calculate_decay(age, importance))
            .collect()
    }
}
