//! Reasoning engine with parallel inference
//! Pattern matching and hypothesis generation

use pyo3::prelude::*;
use rayon::prelude::*;

#[pyclass]
pub struct ReasoningEngine {
    confidence_threshold: f64,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl ReasoningEngine {
    #[new]
    fn new(confidence_threshold: Option<f64>) -> Self {
        Self {
            confidence_threshold: confidence_threshold.unwrap_or(0.7),
        }
    }
    
    fn infer(
        &self,
        premises: Vec<String>,
        rules: Vec<(Vec<String>, String, f64)>
    ) -> PyResult<Vec<(String, f64)>> {
        let conclusions: Vec<(String, f64)> = rules
            .par_iter()
            .filter_map(|(conditions, conclusion, confidence)| {
                if conditions.iter().all(|c| premises.contains(c)) && *confidence >= self.confidence_threshold {
                    Some((conclusion.clone(), *confidence))
                } else {
                    None
                }
            })
            .collect();
        
        Ok(conclusions)
    }
    
    fn generate_hypotheses(
        &self,
        observations: Vec<String>,
        patterns: Vec<Vec<String>>
    ) -> PyResult<Vec<(Vec<String>, f64)>> {
        let hypotheses: Vec<(Vec<String>, f64)> = patterns
            .par_iter()
            .map(|pattern| {
                let overlap = pattern.iter().filter(|p| observations.contains(p)).count();
                let score = overlap as f64 / pattern.len() as f64;
                (pattern.clone(), score)
            })
            .filter(|(_, score)| *score >= self.confidence_threshold)
            .collect();
        
        Ok(hypotheses)
    }
}
