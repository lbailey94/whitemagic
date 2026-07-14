//! Code Structure Graph — tree-sitter AST extraction with PyO3 bindings.
//!
//! When tree-sitter dependencies are available (feature `codegraph`),
//! this module provides native Rust parsing of 36+ languages.
//! When the feature is disabled, the Python layer handles extraction
//! via `ast` module + regex fallback.

#[cfg(feature = "codegraph")]
pub mod parser;
#[cfg(feature = "codegraph")]
pub mod extractors;
#[cfg(feature = "codegraph")]
pub mod graph_store;
#[cfg(feature = "codegraph")]
pub mod incremental;
#[cfg(feature = "codegraph")]
pub mod query;
#[cfg(feature = "codegraph")]
pub mod import_export;

use pyo3::prelude::*;

/// Register the codegraph sub-module.
/// When the `codegraph` feature is disabled, this registers a stub
/// that signals unavailability to the Python layer.
#[cfg(feature = "python")]
pub fn codegraph(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    #[cfg(feature = "codegraph")]
    {
        m.add_function(wrap_pyfunction!(parser::build_graph, m)?)?;
        m.add_function(wrap_pyfunction!(query::query_graph, m)?)?;
        m.add_function(wrap_pyfunction!(query::path_trace, m)?)?;
        m.add_function(wrap_pyfunction!(query::explain_node, m)?)?;
        m.add_function(wrap_pyfunction!(import_export::export_json, m)?)?;
        m.add_function(wrap_pyfunction!(import_export::import_json, m)?)?;
        m.add("__version__", "1.0")?;
        m.add("available", true)?;
    }
    #[cfg(not(feature = "codegraph"))]
    {
        m.add("__version__", "1.0-stub")?;
        m.add("available", false)?;
    }
    Ok(())
}
