//! FFI Layer - Python bindings for ResonanceConductor

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;

use crate::conductor::nervous_system::{
    CoherenceMonitor, GardenRegistry, HarmonyVector, NervousSystem, NervousSystemConfig,
    ZodiacPhase, ZodiacalCycle,
};
use crate::conductor::{
    CircuitBreakerConfig, CircuitBreakerRegistry, CircuitState, EventType, ResonanceConductor,
    SubsystemConfig,
};

/// Python wrapper for ResonanceConductor
#[pyclass(name = "ResonanceConductor")]
pub struct PyResonanceConductor {
    inner: Arc<ResonanceConductor>,
}

#[pymethods]
impl PyResonanceConductor {
    /// Create new conductor
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(ResonanceConductor::new()),
        }
    }

    /// Get global singleton
    #[staticmethod]
    fn global() -> Self {
        Self {
            inner: ResonanceConductor::global(),
        }
    }

    /// Register a subsystem
    fn register_subsystem(&self, name: &str, description: &str, dependencies: Vec<u32>) -> u32 {
        let config = SubsystemConfig {
            name: name.to_string(),
            description: description.to_string(),
            dependencies,
        };
        self.inner.register_subsystem(config)
    }

    /// Unregister a subsystem
    fn unregister_subsystem(&self, id: u32) -> bool {
        self.inner.unregister_subsystem(id)
    }

    /// Start the conductor
    fn start(&self) -> PyResult<()> {
        self.inner
            .start()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    /// Shutdown the conductor
    fn shutdown(&self) -> PyResult<()> {
        self.inner
            .shutdown()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    /// Get system state
    fn get_state(&self) -> String {
        self.inner.get_state().as_str().to_string()
    }

    /// Check if resonant
    fn is_resonant(&self) -> bool {
        self.inner.is_resonant()
    }

    /// Get uptime in seconds
    fn uptime(&self) -> Option<f64> {
        self.inner.uptime().map(|d| d.as_secs_f64())
    }

    /// Get subsystem count
    fn get_subsystem_count(&self) -> usize {
        self.inner.list_subsystems().len()
    }

    /// List all subsystems
    fn list_subsystems(&self) -> Vec<(u32, String, bool)> {
        self.inner
            .list_subsystems()
            .into_iter()
            .map(|(id, handle)| (id, handle.name().to_string(), handle.is_active()))
            .collect()
    }

    /// Get health status
    fn get_health(&self) -> HashMap<u32, HashMap<String, PyObject>> {
        Python::with_gil(|py| {
            self.inner
                .get_health()
                .into_iter()
                .map(|(id, status)| {
                    let mut info = HashMap::new();
                    info.insert(
                        "state".to_string(),
                        match status.state {
                            crate::conductor::HealthState::Healthy => "healthy".to_object(py),
                            crate::conductor::HealthState::Degraded => "degraded".to_object(py),
                            crate::conductor::HealthState::Failed => "failed".to_object(py),
                            crate::conductor::HealthState::Unknown => "unknown".to_object(py),
                        },
                    );
                    info.insert("error_count".to_string(), status.error_count.to_object(py));
                    (id, info)
                })
                .collect()
        })
    }

    /// Emit event
    #[pyo3(signature = (event_type, source=None, target=None, payload=None))]
    fn emit_event(
        &self,
        event_type: u16,
        source: Option<u32>,
        target: Option<u32>,
        payload: Option<HashMap<String, String>>,
    ) -> u64 {
        let event_type = EventType::from_u16(event_type).unwrap_or(EventType::UserDefined);
        let payload = payload
            .unwrap_or_default()
            .into_iter()
            .map(|(k, v)| (k, serde_json::json!(v)))
            .collect();
        self.inner.emit_event(event_type, source, target, payload)
    }
}

/// Python wrapper for Circuit Breaker Registry
#[pyclass(name = "CircuitBreakerRegistry")]
pub struct PyCircuitBreakerRegistry {
    inner: Arc<CircuitBreakerRegistry>,
}

#[pymethods]
impl PyCircuitBreakerRegistry {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(CircuitBreakerRegistry::new()),
        }
    }

    /// Get or create circuit breaker
    fn get_or_create(
        &self,
        name: &str,
        failure_threshold: u32,
        success_threshold: u32,
        timeout_seconds: u64,
    ) -> PyCircuitBreaker {
        let config = CircuitBreakerConfig {
            failure_threshold,
            success_threshold,
            timeout_duration: std::time::Duration::from_secs(timeout_seconds),
        };

        PyCircuitBreaker {
            inner: self.inner.get_or_create(name, config),
        }
    }

    /// Get circuit breaker
    fn get(&self, name: &str) -> Option<PyCircuitBreaker> {
        self.inner.get(name).map(|inner| PyCircuitBreaker { inner })
    }

    /// Get all circuit breakers
    fn get_all(&self) -> Vec<PyCircuitBreaker> {
        self.inner
            .get_all()
            .into_iter()
            .map(|inner| PyCircuitBreaker { inner })
            .collect()
    }
}

/// Python wrapper for Circuit Breaker
#[pyclass(name = "CircuitBreaker")]
pub struct PyCircuitBreaker {
    inner: Arc<crate::conductor::CircuitBreaker>,
}

#[pymethods]
impl PyCircuitBreaker {
    /// Get state
    fn get_state(&self) -> String {
        match self.inner.get_state() {
            CircuitState::Closed => "closed".to_string(),
            CircuitState::Open => "open".to_string(),
            CircuitState::HalfOpen => "half_open".to_string(),
        }
    }

    /// Check if can execute
    fn can_execute(&self) -> bool {
        self.inner.can_execute()
    }

    /// Record success
    fn record_success(&self) {
        self.inner.record_success();
    }

    /// Record failure
    fn record_failure(&self) {
        self.inner.record_failure();
    }

    /// Get statistics
    fn get_stats(&self, py: Python<'_>) -> PyResult<PyObject> {
        let stats = self.inner.get_stats();
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("name", stats.name)?;
        dict.set_item("state", format!("{:?}", stats.state))?;
        dict.set_item("failure_count", stats.failure_count)?;
        dict.set_item("success_count", stats.success_count)?;
        dict.set_item("total_requests", stats.total_requests)?;
        dict.set_item("total_failures", stats.total_failures)?;
        dict.set_item("total_successes", stats.total_successes)?;
        Ok(dict.into())
    }
}

/// Python wrapper for Nervous System
#[pyclass(name = "NervousSystem")]
pub struct PyNervousSystem {
    inner: Arc<NervousSystem>,
}

#[pymethods]
impl PyNervousSystem {
    #[new]
    fn new(conductor: &PyResonanceConductor) -> Self {
        let config = NervousSystemConfig::default();
        Self {
            inner: Arc::new(NervousSystem::new(
                config,
                conductor.inner.event_bus.clone(),
                conductor.inner.clone(),
            )),
        }
    }

    /// Bootstrap biological subsystems
    fn bootstrap(&self) -> PyResult<()> {
        self.inner
            .bootstrap()
            .map_err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>)
    }

    /// Get subsystem status
    fn get_subsystem_status(&self, py: Python<'_>) -> PyResult<PyObject> {
        let status = self.inner.get_subsystem_status();
        let outer = pyo3::types::PyDict::new_bound(py);
        for (key, inner_map) in status {
            let inner_dict = pyo3::types::PyDict::new_bound(py);
            for (k, v) in inner_map {
                inner_dict.set_item(k, v.to_string())?;
            }
            outer.set_item(key, inner_dict)?;
        }
        Ok(outer.into())
    }

    /// Update coherence
    fn update_coherence(&self, coherence: f64) {
        self.inner.update_coherence(coherence);
    }

    /// Get current coherence
    fn get_coherence(&self) -> f64 {
        self.inner.get_coherence()
    }

    /// Health check
    fn health_check(&self) -> bool {
        self.inner.health_check()
    }

    /// Shutdown
    fn shutdown(&self) {
        self.inner.shutdown();
    }
}

/// Python wrapper for Zodiacal Cycle
#[pyclass(name = "ZodiacalCycle")]
pub struct PyZodiacalCycle {
    inner: Arc<ZodiacalCycle>,
}

#[pymethods]
impl PyZodiacalCycle {
    #[new]
    fn new(conductor: &PyResonanceConductor) -> Self {
        Self {
            inner: Arc::new(ZodiacalCycle::new(conductor.inner.event_bus.clone())),
        }
    }

    /// Get current phase
    fn get_phase(&self) -> String {
        match self.inner.get_phase() {
            ZodiacPhase::Yang => "yang".to_string(),
            ZodiacPhase::Yin => "yin".to_string(),
        }
    }

    /// Transition phase
    fn transition(&self) {
        self.inner.transition();
    }

    /// Get cycle count
    fn get_cycle_count(&self) -> u32 {
        self.inner.get_cycle_count()
    }
}

/// Python wrapper for Garden Registry
#[pyclass(name = "GardenRegistry")]
pub struct PyGardenRegistry {
    inner: Arc<GardenRegistry>,
}

#[pymethods]
impl PyGardenRegistry {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(GardenRegistry::new()),
        }
    }

    /// Activate a garden
    fn activate(&self, name: &str) -> bool {
        self.inner.activate(name)
    }

    /// Get active gardens
    fn get_active_gardens(&self) -> Vec<String> {
        self.inner.get_active_gardens()
    }

    /// Get all gardens
    fn get_all_gardens(&self) -> Vec<String> {
        self.inner.get_all_gardens()
    }

    /// Activate all gardens
    fn activate_all(&self) -> usize {
        self.inner.activate_all()
    }
}

/// Python wrapper for Harmony Vector
#[pyclass(name = "HarmonyVector")]
#[derive(Clone)]
pub struct PyHarmonyVector {
    #[pyo3(get, set)]
    pub coherence: f64,
    #[pyo3(get, set)]
    pub resonance: f64,
    #[pyo3(get, set)]
    pub emergence: f64,
    #[pyo3(get, set)]
    pub metabolism: f64,
    #[pyo3(get, set)]
    pub consciousness: f64,
    #[pyo3(get, set)]
    pub immune: f64,
    #[pyo3(get, set)]
    pub genetic: f64,
}

#[pymethods]
impl PyHarmonyVector {
    #[new]
    fn new() -> Self {
        Self {
            coherence: 1.0,
            resonance: 1.0,
            emergence: 1.0,
            metabolism: 1.0,
            consciousness: 1.0,
            immune: 1.0,
            genetic: 1.0,
        }
    }

    /// Calculate composite score
    fn composite(&self) -> f64 {
        (self.coherence
            + self.resonance
            + self.emergence
            + self.metabolism
            + self.consciousness
            + self.immune
            + self.genetic)
            / 7.0
    }

    /// Check if healthy
    fn is_healthy(&self, threshold: f64) -> bool {
        self.coherence >= threshold
            && self.resonance >= threshold
            && self.emergence >= threshold
            && self.metabolism >= threshold
            && self.consciousness >= threshold
            && self.immune >= threshold
            && self.genetic >= threshold
    }
}

/// Python wrapper for Coherence Monitor
#[pyclass(name = "CoherenceMonitor")]
pub struct PyCoherenceMonitor {
    inner: Arc<CoherenceMonitor>,
}

#[pymethods]
impl PyCoherenceMonitor {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(CoherenceMonitor::new()),
        }
    }

    /// Update harmony vector
    fn update(&self, vector: &PyHarmonyVector) {
        let hv = HarmonyVector {
            coherence: vector.coherence,
            resonance: vector.resonance,
            emergence: vector.emergence,
            metabolism: vector.metabolism,
            consciousness: vector.consciousness,
            immune: vector.immune,
            genetic: vector.genetic,
        };
        self.inner.update(hv);
    }

    /// Get current vector
    fn get_vector(&self) -> PyHarmonyVector {
        let hv = self.inner.get_vector();
        PyHarmonyVector {
            coherence: hv.coherence,
            resonance: hv.resonance,
            emergence: hv.emergence,
            metabolism: hv.metabolism,
            consciousness: hv.consciousness,
            immune: hv.immune,
            genetic: hv.genetic,
        }
    }
}

/// Initialize the conductor module
#[pymodule]
pub fn conductor(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyResonanceConductor>()?;
    m.add_class::<PyCircuitBreakerRegistry>()?;
    m.add_class::<PyCircuitBreaker>()?;
    m.add_class::<PyNervousSystem>()?;
    m.add_class::<PyZodiacalCycle>()?;
    m.add_class::<PyGardenRegistry>()?;
    m.add_class::<PyHarmonyVector>()?;
    m.add_class::<PyCoherenceMonitor>()?;

    // Add constants for event types
    m.add("EVENT_BOOTSTRAP", 1u16)?;
    m.add("EVENT_HEALTH_CHECK", 2u16)?;
    m.add("EVENT_GRACEFUL_SHUTDOWN", 3u16)?;
    m.add("EVENT_SUBSYSTEM_REGISTERED", 4u16)?;
    m.add("EVENT_COHERENCE_CRITICAL", 10u16)?;
    m.add("EVENT_COHERENCE_RESTORE", 11u16)?;
    m.add("EVENT_PHASE_TRANSITION", 60u16)?;
    m.add("EVENT_TRANSCENDENCE", 100u16)?;

    Ok(())
}
