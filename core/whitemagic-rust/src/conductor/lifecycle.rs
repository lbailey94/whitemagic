//! Lifecycle management

use crate::conductor::{EventType, OrchestrationEvent, Priority};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;

/// System operational states
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SystemState {
    Dormant = 0,
    Awakening = 1,
    Resonant = 2,
    Transcendent = 3,
}

impl SystemState {
    /// Convert from u8
    pub fn from_u8(value: u8) -> Self {
        match value {
            1 => Self::Awakening,
            2 => Self::Resonant,
            3 => Self::Transcendent,
            _ => Self::Dormant,
        }
    }

    /// Convert to string
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Dormant => "dormant",
            Self::Awakening => "awakening",
            Self::Resonant => "resonant",
            Self::Transcendent => "transcendent",
        }
    }

    /// Check if can transition to target state
    pub fn can_transition_to(&self, target: SystemState) -> bool {
        match (self, target) {
            (SystemState::Dormant, SystemState::Awakening) => true,
            (SystemState::Awakening, SystemState::Resonant) => true,
            (SystemState::Resonant, SystemState::Transcendent) => true,
            (SystemState::Resonant, SystemState::Dormant) => true, // Shutdown
            (SystemState::Transcendent, SystemState::Dormant) => true,
            (SystemState::Awakening, SystemState::Dormant) => true, // Abort
            _ => false,
        }
    }
}

/// Lifecycle manager with event bus integration
pub struct LifecycleManager {
    /// Registry reference
    registry: Arc<crate::conductor::SubsystemRegistry>,

    /// Event bus for lifecycle event emission
    event_bus: Arc<crate::conductor::EventBus>,

    /// Current system state
    current_state: std::sync::RwLock<SystemState>,

    /// Sequence counter for events
    sequence: std::sync::atomic::AtomicU64,
}

impl LifecycleManager {
    /// Create new lifecycle manager
    pub fn new(
        registry: Arc<crate::conductor::SubsystemRegistry>,
        event_bus: Arc<crate::conductor::EventBus>,
    ) -> Self {
        Self {
            registry,
            event_bus,
            current_state: std::sync::RwLock::new(SystemState::Dormant),
            sequence: std::sync::atomic::AtomicU64::new(1),
        }
    }

    /// Get current system state
    pub fn current_state(&self) -> SystemState {
        if let Ok(state) = self.current_state.read() {
            *state
        } else {
            SystemState::Dormant
        }
    }

    /// Emit a lifecycle event via the event bus
    fn emit_event(&self, event_type: EventType, message: &str) {
        let seq = self
            .sequence
            .fetch_add(1, std::sync::atomic::Ordering::SeqCst);

        let mut payload = HashMap::new();
        payload.insert("message".to_string(), serde_json::json!(message));

        let event = OrchestrationEvent {
            sequence: seq,
            event_type,
            source: 0,    // System source
            target: None, // Broadcast
            priority: Priority::Normal,
            timestamp: std::time::Instant::now(),
            payload,
        };

        self.event_bus.publish(event);
    }

    /// Transition to a new state
    pub fn transition_to(&self, target: SystemState) -> Result<(), String> {
        let current = self.current_state();

        if !current.can_transition_to(target) {
            return Err(format!(
                "Invalid transition from {:?} to {:?}",
                current, target
            ));
        }

        // Update state
        if let Ok(mut state) = self.current_state.write() {
            *state = target;
        }

        // Emit state change event
        self.emit_event(
            EventType::PhaseTransition,
            &format!("state_transition:{}->{}", current.as_str(), target.as_str()),
        );

        Ok(())
    }

    /// Execute bootstrap sequence
    pub fn bootstrap(&self) -> BootstrapResult {
        // Emit bootstrap start event
        self.emit_event(EventType::Bootstrap, "bootstrap_start");

        // Transition to awakening
        let _ = self.transition_to(SystemState::Awakening);

        let subsystems = self.registry.list_all();
        let mut initialized = 0;
        let mut failed = 0;
        let mut failures: Vec<(u32, String)> = Vec::new();
        let total = subsystems.len();

        for (id, handle) in subsystems {
            match handle.initialize() {
                Ok(_) => {
                    initialized += 1;
                    self.registry.set_active(id, true);

                    // Emit subsystem registered event
                    self.emit_event(
                        EventType::SubsystemRegistered,
                        &format!("subsystem_initialized:{}", id),
                    );
                }
                Err(e) => {
                    failed += 1;
                    failures.push((id, e.clone()));

                    // Emit subsystem failure event
                    self.emit_event(
                        EventType::SubsystemFailed,
                        &format!("subsystem_init_failed:{}:{}", id, e),
                    );
                }
            }
        }

        // Transition to resonant if all initialized successfully
        if failed == 0 {
            let _ = self.transition_to(SystemState::Resonant);
        }

        // Emit bootstrap complete event
        self.emit_event(
            EventType::Bootstrap,
            &format!(
                "bootstrap_complete:initialized={},failed={}",
                initialized, failed
            ),
        );

        BootstrapResult {
            total,
            initialized,
            failed,
            failures,
        }
    }

    /// Execute shutdown sequence
    pub fn shutdown(&self) -> ShutdownResult {
        // Emit shutdown start event
        self.emit_event(EventType::GracefulShutdown, "shutdown_start");

        let subsystems = self.registry.list_all();
        let mut shutdown_ok = 0;
        let mut failed = 0;
        let mut failures: Vec<(u32, String)> = Vec::new();

        // Shutdown in reverse order
        for (id, handle) in subsystems.iter().rev() {
            match handle.shutdown() {
                Ok(_) => {
                    shutdown_ok += 1;
                    self.registry.set_active(*id, false);

                    // Emit subsystem shutdown event
                    self.emit_event(
                        EventType::GracefulShutdown,
                        &format!("subsystem_shutdown:{}", id),
                    );
                }
                Err(e) => {
                    failed += 1;
                    failures.push((*id, e.clone()));

                    // Emit subsystem failure event
                    self.emit_event(
                        EventType::SubsystemFailed,
                        &format!("subsystem_shutdown_failed:{}:{}", id, e),
                    );
                }
            }
        }

        // Transition to dormant
        let _ = self.transition_to(SystemState::Dormant);

        // Emit shutdown complete event
        self.emit_event(
            EventType::GracefulShutdown,
            &format!("shutdown_complete:ok={},failed={}", shutdown_ok, failed),
        );

        ShutdownResult {
            total: subsystems.len(),
            shutdown_ok,
            failed,
            failures,
        }
    }
}

/// Bootstrap result
#[derive(Debug, Clone)]
pub struct BootstrapResult {
    pub total: usize,
    pub initialized: usize,
    pub failed: usize,
    pub failures: Vec<(u32, String)>,
}

/// Shutdown result
#[derive(Debug, Clone)]
pub struct ShutdownResult {
    pub total: usize,
    pub shutdown_ok: usize,
    pub failed: usize,
    pub failures: Vec<(u32, String)>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_state_transitions() {
        assert!(SystemState::Dormant.can_transition_to(SystemState::Awakening));
        assert!(SystemState::Awakening.can_transition_to(SystemState::Resonant));
        assert!(SystemState::Resonant.can_transition_to(SystemState::Transcendent));
        assert!(SystemState::Resonant.can_transition_to(SystemState::Dormant));

        assert!(!SystemState::Dormant.can_transition_to(SystemState::Resonant));
        assert!(!SystemState::Transcendent.can_transition_to(SystemState::Awakening));
    }

    #[test]
    fn test_state_conversion() {
        assert_eq!(SystemState::from_u8(0), SystemState::Dormant);
        assert_eq!(SystemState::from_u8(1), SystemState::Awakening);
        assert_eq!(SystemState::from_u8(2), SystemState::Resonant);
        assert_eq!(SystemState::from_u8(3), SystemState::Transcendent);
    }
}
