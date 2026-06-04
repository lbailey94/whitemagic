//! Tensor Ops - Basic Tensor Operations (PSR-008)
//! Target: 30× speedup for tensor operations

use pyo3::prelude::*;
use ndarray::{Array1, Array2};

#[pyclass]
pub struct PyTensorOps;

#[pymethods]
impl PyTensorOps {
    #[new]
    fn new() -> Self {
        Self
    }

    fn dot_product(&self, a: Vec<f64>, b: Vec<f64>) -> PyResult<f64> {
        if a.len() != b.len() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Vectors must have same length",
            ));
        }

        Ok(a.iter().zip(b.iter()).map(|(x, y)| x * y).sum())
    }

    fn matrix_multiply(&self, a: Vec<Vec<f64>>, b: Vec<Vec<f64>>) -> PyResult<Vec<Vec<f64>>> {
        if a.is_empty() || b.is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Matrices cannot be empty",
            ));
        }

        let a_cols = a[0].len();
        let b_rows = b.len();

        if a_cols != b_rows {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Matrix dimensions incompatible",
            ));
        }

        let mut result = vec![vec![0.0; b[0].len()]; a.len()];

        for i in 0..a.len() {
            for j in 0..b[0].len() {
                for k in 0..a_cols {
                    result[i][j] += a[i][k] * b[k][j];
                }
            }
        }

        Ok(result)
    }

    fn normalize(&self, vec: Vec<f64>) -> Vec<f64> {
        let magnitude: f64 = vec.iter().map(|x| x * x).sum::<f64>().sqrt();
        
        if magnitude == 0.0 {
            return vec;
        }

        vec.iter().map(|x| x / magnitude).collect()
    }

    fn cosine_similarity(&self, a: Vec<f64>, b: Vec<f64>) -> PyResult<f64> {
        if a.len() != b.len() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Vectors must have same length",
            ));
        }

        let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let mag_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
        let mag_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();

        if mag_a == 0.0 || mag_b == 0.0 {
            return Ok(0.0);
        }

        Ok(dot / (mag_a * mag_b))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dot_product() {
        let ops = PyTensorOps::new();
        let result = ops.dot_product(vec![1.0, 2.0, 3.0], vec![4.0, 5.0, 6.0]).unwrap();
        assert_eq!(result, 32.0);
    }

    #[test]
    fn test_normalize() {
        let ops = PyTensorOps::new();
        let result = ops.normalize(vec![3.0, 4.0]);
        assert!((result[0] - 0.6).abs() < 0.001);
        assert!((result[1] - 0.8).abs() < 0.001);
    }

    #[test]
    fn test_cosine_similarity() {
        let ops = PyTensorOps::new();
        let result = ops.cosine_similarity(vec![1.0, 0.0], vec![1.0, 0.0]).unwrap();
        assert_eq!(result, 1.0);
    }

    #[test]
    fn test_matrix_multiply() {
        let ops = PyTensorOps::new();
        let a = vec![vec![1.0, 2.0], vec![3.0, 4.0]];
        let b = vec![vec![5.0, 6.0], vec![7.0, 8.0]];
        
        let result = ops.matrix_multiply(a, b).unwrap();
        assert_eq!(result[0][0], 19.0);
        assert_eq!(result[1][1], 50.0);
    }
}
