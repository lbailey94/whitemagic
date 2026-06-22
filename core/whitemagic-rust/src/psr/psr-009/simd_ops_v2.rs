//! SIMD Operations - Vectorized computations

use pyo3::prelude::*;

#[pyclass]
pub struct SimdOps;

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl SimdOps {
    #[new]
    fn new() -> Self {
        Self
    }
    
    fn dot_product(&self, a: Vec<f64>, b: Vec<f64>) -> PyResult<f64> {
        if a.len() != b.len() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Vectors must have same length"
            ));
        }
        
        let result: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        
        Ok(result)
    }
    
    fn cosine_similarity(&self, a: Vec<f64>, b: Vec<f64>) -> PyResult<f64> {
        let dot = self.dot_product(a.clone(), b.clone())?;
        let norm_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
        
        if norm_a == 0.0 || norm_b == 0.0 {
            Ok(0.0)
        } else {
            Ok(dot / (norm_a * norm_b))
        }
    }
}
