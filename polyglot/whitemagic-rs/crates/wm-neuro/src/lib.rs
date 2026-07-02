//! WhiteMagic Neuro-Cognitive Hot-Path Modules
//!
//! Three sub-modules for sub-millisecond cognitive operations:
//! - `thalamic_gating`: Galaxy access mask computation (Python-only, PyO3 overhead > compute)
//! - `predictive_coding`: Prediction error computation for memory writes (Rust PyO3, 19x speedup)
//! - `momentum_dynamics`: Momentum term for spreading activation (Python-only, PyO3 overhead > compute)
//!
//! Benchmark data (2026-07-02):
//!   PredictiveCoder (dim=128): Rust 3.03µs vs Python 58.06µs = 19.2x speedup
//!   ThalamicGate (5 galaxies): Rust 1.92µs vs Python 1.25µs = 0.7x (Python wins)
//!   MomentumDynamics (50 nodes): Rust 9.57µs vs Python 6.01µs = 0.6x (Python wins)
//!
//! Crossover: PyO3 FFI costs ~1-2µs per call. For dict-lookup-heavy operations
//! where CPython is already C-level fast, the FFI overhead dominates. Rust wins
//! only for compute-bound vector math (dim >= ~32).

pub mod thalamic_gating;
pub mod predictive_coding;
pub mod momentum_dynamics;

pub use thalamic_gating::ThalamicGate;
pub use predictive_coding::PredictiveCoder;
pub use momentum_dynamics::MomentumDynamics;

// ── PyO3 module entry point ─────────────────────────────────────────────
//
// Only PredictiveCoder is exposed via PyO3. ThalamicGate and MomentumDynamics
// are Python-only because PyO3 FFI overhead exceeds the compute cost for
// dict-lookup operations that CPython already handles at C speed.

#[cfg(feature = "pyo3")]
use pyo3::prelude::*;

#[cfg(feature = "pyo3")]
use predictive_coding::PredictiveCoder as RsPredictiveCoder;

#[cfg(feature = "pyo3")]
#[pyclass(name = "PredictiveCoder")]
struct PyPredictiveCoder {
    inner: RsPredictiveCoder,
}

#[cfg(feature = "pyo3")]
#[pymethods]
impl PyPredictiveCoder {
    #[new]
    #[pyo3(signature = (window_size=5, dim=128))]
    fn new(window_size: usize, dim: usize) -> Self {
        Self { inner: RsPredictiveCoder::new(window_size, dim) }
    }

    fn observe(&mut self, embedding: Vec<f64>) {
        self.inner.observe(embedding);
    }

    fn predict(&self) -> Vec<f64> {
        self.inner.predict()
    }

    fn prediction_error(&mut self, actual: Vec<f64>) -> f64 {
        self.inner.prediction_error(&actual)
    }

    fn process(&mut self, embedding: Vec<f64>) -> f64 {
        self.inner.process(embedding)
    }

    fn novelty_score(&self, surprise: f64) -> f64 {
        self.inner.novelty_score(surprise)
    }

    #[getter]
    fn total_predictions(&self) -> u64 {
        self.inner.total_predictions
    }
}

#[cfg(feature = "pyo3")]
#[pymodule]
fn wm_neuro(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyPredictiveCoder>()?;
    Ok(())
}
