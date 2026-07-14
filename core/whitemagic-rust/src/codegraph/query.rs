//! Path tracing, subgraph extraction, explain operations.
//! Requires the `codegraph` cargo feature.

use pyo3::prelude::*;
use serde_json::json;

#[pyfunction]
pub fn query_graph(query: String, limit: usize) -> PyResult<serde_json::Value> {
    Ok(json!({"status": "not_implemented", "query": query, "limit": limit}))
}

#[pyfunction]
pub fn path_trace(symbol_a: String, symbol_b: String, max_hops: usize) -> PyResult<serde_json::Value> {
    Ok(json!({"status": "not_implemented", "a": symbol_a, "b": symbol_b, "max_hops": max_hops}))
}

#[pyfunction]
pub fn explain_node(symbol: String) -> PyResult<serde_json::Value> {
    Ok(json!({"status": "not_implemented", "symbol": symbol}))
}
