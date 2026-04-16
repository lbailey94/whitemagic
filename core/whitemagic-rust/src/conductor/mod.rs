//! ResonanceConductor - Unified Orchestration System for WhiteMagic
//!
//! This module implements the supreme conductor that unifies all WhiteMagic
//! subsystems into a single, high-performance orchestration layer.

use std::collections::HashMap;
use std::sync::{
    atomic::{AtomicU64, AtomicU8, Ordering},
    Arc, RwLock,
};
use std::time::{Duration, Instant};

pub mod dag;
pub mod event_bus;
pub mod health;
pub mod lifecycle;
pub mod nervous_system;
pub mod primitives;
pub mod registry;
#[cfg(feature = "zig")]
pub mod sangha_bridge;
pub mod spatial_index;
pub mod webhooks;
pub mod management;

#[cfg(test)]
pub mod stress_tests;

// FFI only available with Python feature
#[cfg(feature = "python")]
pub mod ffi;

pub use dag::{DagExecutor, DependencyGraph};
pub use event_bus::{EventBus, EventType, OrchestrationEvent, Priority};
pub use health::{HealthMonitor, HealthState, HealthStatus};
pub use lifecycle::{LifecycleManager, SystemState};
pub use primitives::{
    BackpressureConfig, BackpressureController, BackpressureError, BackpressureGuard,
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerError, CircuitBreakerRegistry,
    CircuitBreakerStats, CircuitState, LoadMetrics, RetryConfig, RetryError, RetryExecutor,
};
pub use registry::{SubsystemConfig, SubsystemHandle, SubsystemRegistry};

/// Unique identifier for subsystems (re-exported from registry)
pub use registry::SubsystemId;

/// The ResonanceConductor - unified orchestrator for all WhiteMagic subsystems
pub struct ResonanceConductor {
    /// Subsystem registry
    registry: Arc<SubsystemRegistry>,

    /// Event bus for inter-subsystem communication
    event_bus: Arc<EventBus>,

    /// Health monitoring system
    health_monitor: Arc<HealthMonitor>,

    /// Lifecycle manager
    #[allow(dead_code)] // Reserved for lifecycle orchestration
    lifecycle: Arc<LifecycleManager>,

    /// Dependency graph for orchestration
    dependency_graph: Arc<RwLock<DependencyGraph>>,

    /// Current system state
    state: AtomicU8,

    /// Conductor start time
    started_at: RwLock<Option<Instant>>,

    /// Global event sequence number
    event_sequence: AtomicU64,
}

impl ResonanceConductor {
    /// Create a new ResonanceConductor
    pub fn new() -> Self {
        let event_bus = Arc::new(EventBus::new());
        let registry = Arc::new(SubsystemRegistry::new(event_bus.clone()));
        let health_monitor = Arc::new(HealthMonitor::new(registry.clone()));
        let lifecycle = Arc::new(LifecycleManager::new(registry.clone(), event_bus.clone()));

        Self {
            registry,
            event_bus,
            health_monitor,
            lifecycle,
            dependency_graph: Arc::new(RwLock::new(DependencyGraph::new())),
            state: AtomicU8::new(SystemState::Dormant as u8),
            started_at: RwLock::new(None),
            event_sequence: AtomicU64::new(0),
        }
    }

    /// Get the global singleton instance
    pub fn global() -> Arc<Self> {
        use std::sync::OnceLock;
        static INSTANCE: OnceLock<Arc<ResonanceConductor>> = OnceLock::new();
        INSTANCE.get_or_init(|| Arc::new(Self::new())).clone()
    }

    /// Register a new subsystem
    pub fn register_subsystem(&self, config: SubsystemConfig) -> SubsystemId {
        let id = self.registry.register(config);

        // Emit registration event
        self.emit_event(
            EventType::SubsystemRegistered,
            Some(id),
            None,
            HashMap::new(),
        );

        // Add to dependency graph
        if let Ok(mut graph) = self.dependency_graph.write() {
            graph.add_node(id);
        }

        id
    }

    /// Unregister a subsystem
    pub fn unregister_subsystem(&self, id: SubsystemId) -> bool {
        let result = self.registry.unregister(id);

        if result {
            // Remove from dependency graph
            if let Ok(mut graph) = self.dependency_graph.write() {
                graph.remove_node(id);
            }
        }

        result
    }

    /// Get a subsystem handle
    pub fn get_subsystem(&self, id: SubsystemId) -> Option<SubsystemHandle> {
        self.registry.get(id)
    }

    /// Emit an orchestration event
    pub fn emit_event(
        &self,
        event_type: EventType,
        source: Option<SubsystemId>,
        target: Option<SubsystemId>,
        payload: HashMap<String, serde_json::Value>,
    ) -> u64 {
        let sequence = self.event_sequence.fetch_add(1, Ordering::SeqCst);

        let event = OrchestrationEvent {
            sequence,
            event_type,
            source: source.unwrap_or(0),
            target,
            priority: Priority::Normal,
            timestamp: Instant::now(),
            payload,
        };

        self.event_bus.publish(event);
        sequence
    }

    /// Subscribe to events
    pub fn subscribe<F>(&self, event_types: Vec<EventType>, handler: F) -> u64
    where
        F: Fn(&OrchestrationEvent) + Send + Sync + 'static,
    {
        self.event_bus.subscribe(event_types, handler)
    }

    /// Unsubscribe from events
    pub fn unsubscribe(&self, subscription_id: u64) -> bool {
        self.event_bus.unsubscribe(subscription_id)
    }

    /// Start the conductor (bootstrap all subsystems)
    pub fn start(&self) -> Result<(), ConductorError> {
        // Check if already started
        let current = self.state.load(Ordering::SeqCst);
        if current != SystemState::Dormant as u8 {
            return Err(ConductorError::AlreadyStarted);
        }

        // Transition to awakening
        self.state
            .store(SystemState::Awakening as u8, Ordering::SeqCst);

        // Record start time
        if let Ok(mut started) = self.started_at.write() {
            *started = Some(Instant::now());
        }

        // Start health monitoring
        self.health_monitor.start();

        // Execute bootstrap sequence based on dependency graph
        self.execute_bootstrap_sequence()?;

        // Transition to resonant
        self.state
            .store(SystemState::Resonant as u8, Ordering::SeqCst);

        // Emit system awakened event
        self.emit_event(
            EventType::Bootstrap,
            None,
            None,
            HashMap::from([
                ("status".to_string(), serde_json::json!("awakened")),
                (
                    "subsystems".to_string(),
                    serde_json::json!(self.registry.count()),
                ),
            ]),
        );

        Ok(())
    }

    /// Graceful shutdown
    pub fn shutdown(&self) -> Result<(), ConductorError> {
        let current = self.state.load(Ordering::SeqCst);
        if current == SystemState::Dormant as u8 {
            return Err(ConductorError::NotStarted);
        }

        // Emit shutdown event
        self.emit_event(EventType::GracefulShutdown, None, None, HashMap::new());

        // Stop health monitoring
        self.health_monitor.stop();

        // Execute shutdown sequence in reverse dependency order
        self.execute_shutdown_sequence()?;

        // Clear registry
        self.registry.clear();

        // Transition to dormant
        self.state
            .store(SystemState::Dormant as u8, Ordering::SeqCst);

        // Clear start time
        if let Ok(mut started) = self.started_at.write() {
            *started = None;
        }

        Ok(())
    }

    /// Get current system state
    pub fn get_state(&self) -> SystemState {
        SystemState::from_u8(self.state.load(Ordering::SeqCst))
    }

    /// Check if system is resonant
    pub fn is_resonant(&self) -> bool {
        self.get_state() == SystemState::Resonant
    }

    /// Get uptime
    pub fn uptime(&self) -> Option<Duration> {
        if let Ok(started) = self.started_at.read() {
            started.map(|s| Instant::now().duration_since(s))
        } else {
            None
        }
    }

    /// Get health status for all subsystems
    pub fn get_health(&self) -> HashMap<SubsystemId, HealthStatus> {
        self.health_monitor.get_all_status()
    }

    /// Get health for a specific subsystem
    pub fn get_subsystem_health(&self, id: SubsystemId) -> Option<HealthStatus> {
        self.health_monitor.get_status(id)
    }

    /// Check if subsystem is healthy
    pub fn is_healthy(&self, id: SubsystemId) -> bool {
        self.health_monitor.is_healthy(id)
    }

    /// Get all registered subsystems
    pub fn list_subsystems(&self) -> Vec<(SubsystemId, SubsystemHandle)> {
        self.registry.list_all()
    }

    /// Execute bootstrap sequence based on dependency graph
    fn execute_bootstrap_sequence(&self) -> Result<(), ConductorError> {
        let graph = self
            .dependency_graph
            .read()
            .map_err(|_| ConductorError::LockError)?;

        let executor = DagExecutor::new(&graph);
        let sequence = executor
            .topological_sort()
            .map_err(|e| ConductorError::DependencyError(e.to_string()))?;

        for id in sequence {
            if let Some(handle) = self.registry.get(id) {
                // Initialize the subsystem
                if let Err(e) = handle.initialize() {
                    return Err(ConductorError::BootstrapFailed(id, e.to_string()));
                }

                // Mark as active
                self.registry.set_active(id, true);

                // Start health monitoring for this subsystem
                self.health_monitor.start_monitoring(id);
            }
        }

        Ok(())
    }

    /// Execute shutdown sequence in reverse order
    fn execute_shutdown_sequence(&self) -> Result<(), ConductorError> {
        let graph = self
            .dependency_graph
            .read()
            .map_err(|_| ConductorError::LockError)?;

        let executor = DagExecutor::new(&graph);
        let mut sequence = executor
            .topological_sort()
            .map_err(|e| ConductorError::DependencyError(e.to_string()))?;

        // Reverse for shutdown (dependents first)
        sequence.reverse();

        for id in sequence {
            if let Some(handle) = self.registry.get(id) {
                // Stop health monitoring
                self.health_monitor.stop_monitoring(id);

                // Shutdown the subsystem
                if let Err(e) = handle.shutdown() {
                    eprintln!("Subsystem {} shutdown error: {}", id, e);
                }

                // Mark as inactive
                self.registry.set_active(id, false);
            }
        }

        Ok(())
    }
}

impl Default for ResonanceConductor {
    fn default() -> Self {
        Self::new()
    }
}

/// Conductor errors
#[derive(Debug, Clone, PartialEq)]
pub enum ConductorError {
    AlreadyStarted,
    NotStarted,
    BootstrapFailed(SubsystemId, String),
    ShutdownFailed(SubsystemId, String),
    SubsystemNotFound(SubsystemId),
    DependencyError(String),
    LockError,
    EventBusError(String),
}

impl std::fmt::Display for ConductorError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::AlreadyStarted => write!(f, "Conductor already started"),
            Self::NotStarted => write!(f, "Conductor not started"),
            Self::BootstrapFailed(id, e) => {
                write!(f, "Bootstrap failed for subsystem {}: {}", id, e)
            }
            Self::ShutdownFailed(id, e) => write!(f, "Shutdown failed for subsystem {}: {}", id, e),
            Self::SubsystemNotFound(id) => write!(f, "Subsystem {} not found", id),
            Self::DependencyError(e) => write!(f, "Dependency error: {}", e),
            Self::LockError => write!(f, "Failed to acquire lock"),
            Self::EventBusError(e) => write!(f, "Event bus error: {}", e),
        }
    }
}

impl std::error::Error for ConductorError {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_conductor_creation() {
        let conductor = ResonanceConductor::new();
        assert_eq!(conductor.get_state(), SystemState::Dormant);
        assert_eq!(conductor.registry.count(), 0);
    }

    #[test]
    fn test_subsystem_registration() {
        let conductor = ResonanceConductor::new();

        let config = SubsystemConfig {
            name: "test".to_string(),
            description: "Test subsystem".to_string(),
            dependencies: vec![],
        };

        let id = conductor.register_subsystem(config);
        assert!(id > 0);
        assert_eq!(conductor.registry.count(), 1);

        let handle = conductor.get_subsystem(id);
        assert!(handle.is_some());
    }

    #[test]
    fn test_event_emission() {
        let conductor = ResonanceConductor::new();

        let sequence = conductor.emit_event(EventType::Bootstrap, None, None, HashMap::new());

        assert_eq!(sequence, 0);

        let sequence2 = conductor.emit_event(EventType::HealthCheck, None, None, HashMap::new());

        assert_eq!(sequence2, 1);
    }

    #[test]
    fn test_global_singleton() {
        let global1 = ResonanceConductor::global();
        let global2 = ResonanceConductor::global();

        // Both should point to the same instance
        assert!(Arc::ptr_eq(&global1, &global2));
    }
}
