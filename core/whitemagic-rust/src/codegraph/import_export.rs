//! Graphify graph.json compatibility.
//! Requires the `codegraph` cargo feature.

use pyo3::prelude::*;
use serde_json::json;

#[pyfunction]
pub fn export_json(path: String) -> PyResult<serde_json::Value> {
    Ok(json!({"status": "not_implemented", "path": path}))
}

#[pyfunction]
pub fn import_json(path: String) -> PyResult<serde_json::Value> {
    Ok(json!({"status": "not_implemented", "path": path}))
}
