use pyo3::prelude::*;
use whitemagic_math::holographic_encoder_5d::{self, MemoryInput};

#[pyfunction]
pub fn holographic_encode_batch(memories_json: &str) -> PyResult<String> {
    let memories: Vec<MemoryInput> = serde_json::from_str(memories_json).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON parse: {}", e))
    })?;

    let coords = holographic_encoder_5d::encode_batch(&memories);

    serde_json::to_string(&coords).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON serialize: {}", e))
    })
}

#[pyfunction]
pub fn holographic_encode_single(memory_json: &str) -> PyResult<String> {
    let mem: MemoryInput = serde_json::from_str(memory_json).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON parse: {}", e))
    })?;

    let coord = holographic_encoder_5d::encode_memory(&mem);

    serde_json::to_string(&coord).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON serialize: {}", e))
    })
}

#[pyfunction]
pub fn holographic_nearest_5d(
    query_json: &str,
    coords_json: &str,
    k: usize,
    weights_json: Option<&str>,
) -> PyResult<String> {
    let query: holographic_encoder_5d::Coordinate5D = serde_json::from_str(query_json).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON parse query: {}", e))
    })?;
    let coords: Vec<holographic_encoder_5d::Coordinate5D> = serde_json::from_str(coords_json).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON parse coords: {}", e))
    })?;

    let weights: [f64; 5] = if let Some(wj) = weights_json {
        serde_json::from_str(wj).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON parse weights: {}", e))
        })?
    } else {
        [1.0, 1.0, 1.0, 1.0, 1.0]
    };

    let mut distances: Vec<(String, f64)> = coords
        .iter()
        .map(|c| (c.id.clone(), holographic_encoder_5d::distance_5d(&query, c, &weights)))
        .collect();

    distances.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
    distances.truncate(k);

    serde_json::to_string(&distances).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON serialize: {}", e))
    })
}

#[cfg(feature = "python")]
pub fn register_holographic_encoder(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(holographic_encode_batch, m)?)?;
    m.add_function(wrap_pyfunction!(holographic_encode_single, m)?)?;
    m.add_function(wrap_pyfunction!(holographic_nearest_5d, m)?)?;
    Ok(())
}
