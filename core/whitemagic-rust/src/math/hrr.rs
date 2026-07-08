//! HRR Python bindings — re-exports core engine from whitemagic-math.
//!
//! The core HRREngine lives in whitemagic-math (WASM-compatible).
//! This module wraps it with pyo3 bindings for Python use.

#[cfg(feature = "python")]
use pyo3::prelude::*;

pub use whitemagic_math::hrr::HRREngine;

#[cfg(feature = "python")]
#[pyclass]
pub struct PyHRREngine {
    engine: HRREngine,
}

#[cfg(feature = "python")]
#[pymethods]
impl PyHRREngine {
    #[new]
    fn new(dim: usize) -> Self {
        Self {
            engine: HRREngine::new(dim),
        }
    }

    fn bind(&self, a: Vec<f32>, b: Vec<f32>) -> PyResult<Vec<f32>> {
        self.engine.bind(&a, &b)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))
    }

    fn unbind(&self, bound: Vec<f32>, b: Vec<f32>) -> PyResult<Vec<f32>> {
        self.engine.unbind(&bound, &b)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))
    }

    fn superpose(&self, vectors: Vec<Vec<f32>>) -> PyResult<Vec<f32>> {
        self.engine.superpose(&vectors)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))
    }

    fn similarity(&self, a: Vec<f32>, b: Vec<f32>) -> PyResult<f32> {
        self.engine.similarity(&a, &b)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))
    }

    fn project(&mut self, embedding: Vec<f32>, relation: String) -> PyResult<Vec<f32>> {
        self.engine.project(&embedding, &relation)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))
    }

    #[getter]
    fn dim(&self) -> usize {
        self.engine.dim
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bind_unbind() {
        let engine = HRREngine::new(64);
        let a = vec![1.0; 64];
        let b = vec![0.5; 64];

        let bound = engine.bind(&a, &b).unwrap();
        assert_eq!(bound.len(), 64);

        let recovered = engine.unbind(&bound, &b).unwrap();
        assert_eq!(recovered.len(), 64);

        let sim = engine.similarity(&a, &recovered).unwrap();
        assert!(sim > 0.5, "Similarity {} too low", sim);
    }

    #[test]
    fn test_superpose() {
        let engine = HRREngine::new(64);
        let vecs = vec![
            vec![1.0; 64],
            vec![0.5; 64],
            vec![0.25; 64],
        ];

        let result = engine.superpose(&vecs).unwrap();
        assert_eq!(result.len(), 64);

        let norm: f32 = result.iter().map(|x| x * x).sum::<f32>().sqrt();
        assert!((norm - 1.0).abs() < 0.01, "Not normalized: {}", norm);
    }
}
