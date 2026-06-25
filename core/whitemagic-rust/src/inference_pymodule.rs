// PyO3 module exposing inference acceleration functions to Python.
//
// Exposes:
//   - ternary_gemv: multiplication-free GEMV with packed ternary weights
//   - ternary_dot: ternary dot product (scalar fallback)
//   - pack_ternary_matrix: pack a flat ternary weight matrix per-row
//   - pack_ternary: pack a flat ternary vector
//   - unpack_ternary: unpack u32 words back to ternary values
//
// Usage from Python:
//   import whitemagic_rust.inference as inference
//   packed = inference.pack_ternary_matrix(weights, m, k)
//   result = inference.ternary_gemv(packed, activations, m, k)

use pyo3::prelude::*;
use pyo3::types::PyList;

use crate::inference::ternary_kernel::{
    self, pack_ternary, pack_ternary_matrix, ternary_dot, ternary_gemv, ternary_gemv_batch,
    unpack_ternary, Ternary,
};

/// Convert a Python list of ints (-1, 0, 1) to Rust Ternary slice
fn py_to_ternary(values: &Bound<'_, PyList>) -> PyResult<Vec<Ternary>> {
    values
        .iter()
        .map(|v| {
            let val: i32 = v.extract()?;
            match val {
                0 => Ok(Ternary::Zero),
                1 => Ok(Ternary::PosOne),
                -1 => Ok(Ternary::NegOne),
                _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "Ternary values must be -1, 0, or 1, got {}",
                    val
                ))),
            }
        })
        .collect()
}

/// Pack 16 ternary values into each 32-bit word.
///
/// Args:
///   values: List of ints (-1, 0, 1)
///
/// Returns:
///   List of u32 packed words
#[pyfunction]
fn py_pack_ternary(py: Python<'_>, values: &Bound<'_, PyList>) -> PyResult<PyObject> {
    let ternary_values = py_to_ternary(values)?;
    let packed = pack_ternary(&ternary_values);
    Ok(PyList::new_bound(py, packed.iter().copied()).to_object(py))
}

/// Pack a ternary weight matrix per-row.
///
/// Args:
///   weights: Flat list of ints (-1, 0, 1), length m * k
///   m: Number of rows
///   k: Number of columns
///
/// Returns:
///   List of u32 packed words, length m * ((k + 15) / 16)
#[pyfunction]
fn py_pack_ternary_matrix(
    py: Python<'_>,
    weights: &Bound<'_, PyList>,
    m: usize,
    k: usize,
) -> PyResult<PyObject> {
    let ternary_values = py_to_ternary(weights)?;
    let packed = pack_ternary_matrix(&ternary_values, m, k);
    Ok(PyList::new_bound(py, packed.iter().copied()).to_object(py))
}

/// Unpack u32 words back to ternary values.
///
/// Args:
///   packed: List of u32 words
///   count: Number of ternary values to unpack
///
/// Returns:
///   List of ints (-1, 0, 1)
#[pyfunction]
fn py_unpack_ternary(
    py: Python<'_>,
    packed: &Bound<'_, PyList>,
    count: usize,
) -> PyResult<PyObject> {
    let words: Vec<u32> = packed.extract()?;
    let values = unpack_ternary(&words, count);
    let result: Vec<i32> = values.iter().map(|t| match t {
        Ternary::Zero => 0,
        Ternary::PosOne => 1,
        Ternary::NegOne => -1,
    }).collect();
    Ok(PyList::new_bound(py, result).to_object(py))
}

/// Ternary GEMV: Compute y = W * x where W is ternary and x is fp32.
///
/// Uses AVX2 masked add/sub for multiplication-free inference.
/// Falls back to scalar on non-x86_64 platforms.
///
/// Args:
///   weights_packed: Packed ternary weights (from pack_ternary_matrix)
///   activations: Input vector x, length k
///   m: Number of output rows
///   k: Number of input columns
///
/// Returns:
///   Output vector y, length m
#[pyfunction]
fn py_ternary_gemv(
    py: Python<'_>,
    weights_packed: &Bound<'_, PyList>,
    activations: Vec<f32>,
    m: usize,
    k: usize,
) -> PyResult<PyObject> {
    let weights: Vec<u32> = weights_packed.extract()?;
    let result = ternary_gemv(&weights, &activations, m, k);
    Ok(PyList::new_bound(py, result).to_object(py))
}

/// Ternary dot product: sum(w[i] * x[i]) where w is ternary.
///
/// Args:
///   weights: List of ints (-1, 0, 1)
///   activations: List of floats, same length
///
/// Returns:
///   Float result
#[pyfunction]
fn py_ternary_dot(
    weights: &Bound<'_, PyList>,
    activations: Vec<f32>,
) -> PyResult<f32> {
    let ternary_values = py_to_ternary(weights)?;
    if ternary_values.len() != activations.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Length mismatch: weights={} activations={}",
            ternary_values.len(),
            activations.len()
        )));
    }
    Ok(ternary_dot(&ternary_values, &activations))
}

/// Batch ternary GEMV: Compute y[i] = W * x[i] for multiple input vectors.
///
/// Args:
///   weights_packed: Packed ternary weights (from pack_ternary_matrix)
///   activations_batch: List of input vectors, each length k
///   m: Number of output rows
///   k: Number of input columns
///
/// Returns:
///   List of output vectors, each length m
#[pyfunction]
fn py_ternary_gemv_batch(
    py: Python<'_>,
    weights_packed: &Bound<'_, PyList>,
    activations_batch: &Bound<'_, PyList>,
    m: usize,
    k: usize,
) -> PyResult<PyObject> {
    let weights: Vec<u32> = weights_packed.extract()?;
    let batch: Vec<Vec<f32>> = activations_batch.extract()?;
    let slices: Vec<&[f32]> = batch.iter().map(|v| v.as_slice()).collect();
    let results = ternary_gemv_batch(&weights, &slices, m, k);

    let py_results: Vec<PyObject> = results
        .into_iter()
        .map(|v| PyList::new_bound(py, v).to_object(py))
        .collect();
    Ok(PyList::new_bound(py, py_results).to_object(py))
}

/// Get the backend type (avx2, scalar)
#[pyfunction]
fn py_ternary_backend() -> String {
    #[cfg(target_arch = "x86_64")]
    {
        if std::is_x86_feature_detected!("avx2") {
            "avx2".to_string()
        } else {
            "scalar".to_string()
        }
    }
    #[cfg(not(target_arch = "x86_64"))]
    {
        "scalar".to_string()
    }
}

#[pymodule]
pub fn inference(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_pack_ternary, m)?)?;
    m.add_function(wrap_pyfunction!(py_pack_ternary_matrix, m)?)?;
    m.add_function(wrap_pyfunction!(py_unpack_ternary, m)?)?;
    m.add_function(wrap_pyfunction!(py_ternary_gemv, m)?)?;
    m.add_function(wrap_pyfunction!(py_ternary_dot, m)?)?;
    m.add_function(wrap_pyfunction!(py_ternary_gemv_batch, m)?)?;
    m.add_function(wrap_pyfunction!(py_ternary_backend, m)?)?;
    m.add("__doc__", "WhiteMagic inference acceleration — ternary SIMD kernels")?;
    Ok(())
}
