//! Causal network inference
//! Bayesian-style causal reasoning

use pyo3::prelude::*;

#[pyclass]
pub struct CausalNet {
    edges: Vec<(String, String, f64)>,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl CausalNet {
    #[new]
    fn new() -> Self {
        Self {
            edges: Vec::new(),
        }
    }
    
    fn add_causal_link(&mut self, cause: String, effect: String, strength: f64) {
        self.edges.push((cause, effect, strength));
    }
    
    fn infer_causes(&self, effect: String) -> PyResult<Vec<(String, f64)>> {
        let causes: Vec<(String, f64)> = self.edges
            .iter()
            .filter(|(_, e, _)| e == &effect)
            .map(|(c, _, s)| (c.clone(), *s))
            .collect();
        
        Ok(causes)
    }
    
    fn infer_effects(&self, cause: String) -> PyResult<Vec<(String, f64)>> {
        let effects: Vec<(String, f64)> = self.edges
            .iter()
            .filter(|(c, _, _)| c == &cause)
            .map(|(_, e, s)| (e.clone(), *s))
            .collect();
        
        Ok(effects)
    }
}
