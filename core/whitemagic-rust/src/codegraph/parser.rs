//! Tree-sitter parsing orchestration.
//! Requires the `codegraph` cargo feature.

use pyo3::prelude::*;
use serde_json::json;

/// Build a code structure graph for a project.
#[pyfunction]
#[pyo3(signature = (project_path, db_path, incremental, max_files))]
pub fn build_graph(
    project_path: String,
    db_path: String,
    incremental: bool,
    max_files: usize,
) -> PyResult<serde_json::Value> {
    // TODO: Implement tree-sitter parsing when feature is enabled
    Ok(json!({
        "status": "not_implemented",
        "message": "tree-sitter codegraph feature not yet compiled",
        "project_path": project_path,
        "db_path": db_path,
        "incremental": incremental,
        "max_files": max_files,
    }))
}
