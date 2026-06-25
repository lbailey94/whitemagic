//! PyO3 bindings for WhiteMagic cascade acceleration.
//!
//! Exposes `match_cascades`, `detect_cycles`, and `is_safe` as Python functions.
//! This eliminates JSON stdio IPC overhead — calls are direct native function
//! invocations with ~microsecond overhead.

use pyo3::prelude::*;
use wm_core::cascade::{match_cascades as rs_match_cascades, detect_cycles as rs_detect_cycles, is_safe as rs_is_safe, CascadeEvent, CascadeTriggerDef, CascadedEvent};

/// Python-facing trigger definition
#[pyclass]
#[derive(Clone)]
struct PyCascadeTrigger {
    trigger_event: String,
    target_events: Vec<String>,
    amplification: f64,
    max_cascade_depth: u8,
}

#[pymethods]
impl PyCascadeTrigger {
    #[new]
    #[pyo3(signature = (trigger_event, target_events, amplification=1.0, max_cascade_depth=3))]
    fn new(
        trigger_event: String,
        target_events: Vec<String>,
        amplification: f64,
        max_cascade_depth: u8,
    ) -> Self {
        Self { trigger_event, target_events, amplification, max_cascade_depth }
    }
}

impl From<&PyCascadeTrigger> for CascadeTriggerDef {
    fn from(t: &PyCascadeTrigger) -> Self {
        CascadeTriggerDef {
            trigger_event: t.trigger_event.clone(),
            target_events: t.target_events.clone(),
            amplification: t.amplification,
            max_cascade_depth: t.max_cascade_depth,
        }
    }
}

/// Python-facing cascaded event result
#[pyclass]
#[derive(Clone)]
struct PyCascadedEvent {
    event_type: String,
    confidence: f64,
    cascade_depth: u8,
    origin: String,
}

#[pymethods]
impl PyCascadedEvent {
    #[getter]
    fn event_type(&self) -> &str { &self.event_type }
    #[getter]
    fn confidence(&self) -> f64 { self.confidence }
    #[getter]
    fn cascade_depth(&self) -> u8 { self.cascade_depth }
    #[getter]
    fn origin(&self) -> &str { &self.origin }

    fn __repr__(&self) -> String {
        format!("CascadedEvent(event_type={}, confidence={:.3}, cascade_depth={}, origin={})",
                self.event_type, self.confidence, self.cascade_depth, self.origin)
    }
}

impl From<CascadedEvent> for PyCascadedEvent {
    fn from(e: CascadedEvent) -> Self {
        Self {
            event_type: e.event_type,
            confidence: e.confidence,
            cascade_depth: e.cascade_depth,
            origin: e.origin,
        }
    }
}

/// Match an event against a trigger table and return cascaded events.
///
/// Args:
///     event_type: The event type string to match
///     confidence: The confidence of the incoming event (0.0-1.0)
///     cascade_depth: Current cascade depth of the event
///     triggers: List of PyCascadeTrigger objects
///
/// Returns:
///     List of PyCascadedEvent objects to emit
#[pyfunction]
#[pyo3(signature = (event_type, confidence, cascade_depth, triggers))]
fn match_cascades(
    event_type: String,
    confidence: f64,
    cascade_depth: u8,
    triggers: Vec<PyCascadeTrigger>,
) -> Vec<PyCascadedEvent> {
    let event = CascadeEvent { event_type, confidence, cascade_depth };
    let rs_triggers: Vec<CascadeTriggerDef> = triggers.iter().map(Into::into).collect();
    rs_match_cascades(&event, &rs_triggers)
        .into_iter()
        .map(Into::into)
        .collect()
}

/// Detect cycles in a cascade trigger table.
///
/// Returns a list of cycles, where each cycle is a list of event type names.
#[pyfunction]
#[pyo3(signature = (triggers))]
fn detect_cycles(triggers: Vec<PyCascadeTrigger>) -> Vec<Vec<String>> {
    let rs_triggers: Vec<CascadeTriggerDef> = triggers.iter().map(Into::into).collect();
    rs_detect_cycles(&rs_triggers)
}

/// Check if a cascade trigger table is safe (no cycles).
#[pyfunction]
#[pyo3(signature = (triggers))]
fn is_safe(triggers: Vec<PyCascadeTrigger>) -> bool {
    let rs_triggers: Vec<CascadeTriggerDef> = triggers.iter().map(Into::into).collect();
    rs_is_safe(&rs_triggers)
}

#[pymodule]
fn wm_cascade(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(match_cascades, m)?)?;
    m.add_function(wrap_pyfunction!(detect_cycles, m)?)?;
    m.add_function(wrap_pyfunction!(is_safe, m)?)?;
    m.add_class::<PyCascadeTrigger>()?;
    m.add_class::<PyCascadedEvent>()?;
    Ok(())
}
