//! PyO3 bridge — exposes the WhiteMagic v5 MCP server to Python.
//!
//! When the `python` feature is enabled, this module provides a `whitemagic_v5`
//! Python extension module that can be imported from Python:
//!
//! ```python
//! import whitemagic_v5
//! server = whitemagic_v5.Server("/path/to/lmdb")
//! response = server.handle_request('{"jsonrpc":"2.0","id":1,"method":"tools/list"}')
//! ```
//!
//! The Python shell then uses this to implement the MCP protocol over stdio,
//! adding ONNX embedding fallback and HuggingFace tokenizer access.

// PyO3's procedural macros generate unsafe code internally.
// The crate-level `#![forbid(unsafe_code)]` is relaxed here because
// we do not write any unsafe code ourselves — all unsafe is in PyO3 macros.
#![allow(unsafe_code)]
#![allow(clippy::missing_const_for_fn, clippy::useless_conversion)]

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;

use crate::McpServer;

/// Python-facing wrapper around the Rust `McpServer`.
#[pyclass(name = "Server")]
pub struct PyServer {
    inner: McpServer,
}

#[pymethods]
impl PyServer {
    /// Create a new server with default tools and governance pipeline.
    ///
    /// Args:
    ///     store_path: Path to the LMDB store directory.
    #[new]
    #[pyo3(signature = (store_path))]
    fn new(store_path: &str) -> PyResult<Self> {
        let path = std::path::Path::new(store_path);
        let server = McpServer::with_defaults(path)
            .map_err(|e| PyRuntimeError::new_err(format!("Failed to create server: {e}")))?;
        Ok(Self { inner: server })
    }

    /// Handle a single JSON-RPC request string.
    ///
    /// Args:
    ///     json_request: A JSON-RPC 2.0 request string.
    ///
    /// Returns:
    ///     A JSON-RPC 2.0 response string.
    fn handle_request(&mut self, json_request: &str) -> String {
        let rt = tokio::runtime::Runtime::new().expect("failed to create tokio runtime");
        rt.block_on(self.inner.handle_request(json_request))
    }

    /// Get the current brain-wave state as a string.
    fn brain_wave(&self) -> String {
        format!("{}", self.inner.eco_mode().current())
    }

    /// Get the idle duration in seconds.
    fn idle_seconds(&self) -> f64 {
        self.inner.eco_mode().idle_duration().as_secs_f64()
    }

    /// Get the number of registered tools.
    fn tool_count(&self) -> usize {
        self.inner.tool_count()
    }

    /// Get memory counts per galaxy as a dict.
    fn galaxy_counts(&self) -> String {
        serde_json::to_string(&self.inner.galaxy_counts()).unwrap_or_else(|_| "{}".into())
    }

    /// Get citta coherence (0.0 to 1.0).
    fn coherence(&self) -> f32 {
        self.inner.citta().vector.coherence()
    }

    /// Get citta valence (-1.0 to 1.0).
    fn valence(&self) -> f32 {
        self.inner.citta().vector.valence()
    }

    /// Get the number of citta heartbeats.
    fn heartbeats(&self) -> u64 {
        self.inner.citta().heartbeats()
    }

    /// Get the number of completed dream cycles.
    fn dream_cycles(&self) -> u64 {
        self.inner.dream().cycles_completed()
    }

    /// Get a status summary as a JSON string.
    fn status(&self) -> String {
        let eco = self.inner.eco_mode();
        let citta = self.inner.citta();
        let dream = self.inner.dream();
        serde_json::to_string(&serde_json::json!({
            "brain_wave": format!("{}", eco.current()),
            "idle_seconds": eco.idle_duration().as_secs_f64(),
            "total_events": eco.metrics().total_events(),
            "tool_count": self.inner.tool_count(),
            "citta": {
                "coherence": citta.vector.coherence(),
                "valence": citta.vector.valence(),
                "heartbeats": citta.heartbeats(),
            },
            "dream": {
                "cycles_completed": dream.cycles_completed(),
                "consolidated": dream.consolidation.consolidated(),
                "skipped": dream.consolidation.skipped(),
            },
            "galaxies": self.inner.galaxy_counts(),
        }))
        .unwrap_or_else(|_| "{}".into())
    }

    /// Refresh homeostasis from hardware sampling.
    fn refresh_homeostasis(&self) {
        self.inner.refresh_homeostasis();
    }

    /// Run the server synchronously (blocking, reads stdin / writes stdout).
    ///
    /// This is the pure-Rust event loop. Python shells that want custom
    /// I/O handling should use `handle_request` in a loop instead.
    fn run(&mut self) -> PyResult<()> {
        self.inner
            .run()
            .map_err(|e| PyRuntimeError::new_err(format!("Server error: {e}")))
    }
}

/// Python module initialization.
#[pymodule]
pub fn whitemagic_v5(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyServer>()?;

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    m.add(
        "__doc__",
        "WhiteMagic v5 — Cognitive OS MCP server (PyO3 bridge)",
    )?;

    Ok(())
}
