//! Subsystem registry

use crate::conductor::{EventBus, OrchestrationEvent};
use std::collections::HashMap;
use std::sync::{
    atomic::{AtomicU32, Ordering},
    Arc, RwLock,
};

/// Subsystem identifier
pub type SubsystemId = u32;

/// Subsystem configuration
#[derive(Debug, Clone)]
pub struct SubsystemConfig {
    pub name: String,
    pub description: String,
    pub dependencies: Vec<SubsystemId>,
}

/// Subsystem handle for interaction
#[derive(Debug, Clone)]
pub struct SubsystemHandle {
    id: SubsystemId,
    config: SubsystemConfig,
    active: Arc<RwLock<bool>>,
}

impl SubsystemHandle {
    /// Create new handle
    pub fn new(id: SubsystemId, config: SubsystemConfig) -> Self {
        Self {
            id,
            config,
            active: Arc::new(RwLock::new(false)),
        }
    }

    /// Get subsystem ID
    pub fn id(&self) -> SubsystemId {
        self.id
    }

    /// Get subsystem name
    pub fn name(&self) -> &str {
        &self.config.name
    }

    /// Get subsystem description
    pub fn description(&self) -> &str {
        &self.config.description
    }

    /// Get dependencies
    pub fn dependencies(&self) -> &[SubsystemId] {
        &self.config.dependencies
    }

    /// Check if active
    pub fn is_active(&self) -> bool {
        if let Ok(active) = self.active.read() {
            *active
        } else {
            false
        }
    }

    /// Set active state
    pub fn set_active(&self, active: bool) {
        if let Ok(mut a) = self.active.write() {
            *a = active;
        }
    }

    /// Initialize the subsystem
    pub fn initialize(&self) -> Result<(), String> {
        // Base implementation - subsystems can override
        self.set_active(true);
        Ok(())
    }

    /// Shutdown the subsystem
    pub fn shutdown(&self) -> Result<(), String> {
        self.set_active(false);
        Ok(())
    }

    /// Health check
    pub fn health_check(&self) -> Result<(), String> {
        if self.is_active() {
            Ok(())
        } else {
            Err("Subsystem not active".to_string())
        }
    }
}

/// Subsystem registry
pub struct SubsystemRegistry {
    /// Subsystems by ID
    subsystems: RwLock<HashMap<SubsystemId, SubsystemHandle>>,

    /// Name to ID mapping
    name_to_id: RwLock<HashMap<String, SubsystemId>>,

    /// ID counter
    next_id: AtomicU32,

    /// Event bus for notifications
    event_bus: Arc<EventBus>,
}

impl SubsystemRegistry {
    /// Create new registry
    pub fn new(event_bus: Arc<EventBus>) -> Self {
        Self {
            subsystems: RwLock::new(HashMap::new()),
            name_to_id: RwLock::new(HashMap::new()),
            next_id: AtomicU32::new(1),
            event_bus,
        }
    }

    /// Register a subsystem
    pub fn register(&self, config: SubsystemConfig) -> SubsystemId {
        let id = self.next_id.fetch_add(1, Ordering::SeqCst);

        let handle = SubsystemHandle::new(id, config.clone());

        if let Ok(mut subsystems) = self.subsystems.write() {
            subsystems.insert(id, handle);
        }

        if let Ok(mut name_map) = self.name_to_id.write() {
            name_map.insert(config.name, id);
        }

        id
    }

    /// Unregister a subsystem
    pub fn unregister(&self, id: SubsystemId) -> bool {
        if let Ok(mut subsystems) = self.subsystems.write() {
            if let Some(handle) = subsystems.remove(&id) {
                // Remove from name mapping
                if let Ok(mut name_map) = self.name_to_id.write() {
                    name_map.remove(&handle.config.name);
                }
                return true;
            }
        }
        false
    }

    /// Get subsystem by ID
    pub fn get(&self, id: SubsystemId) -> Option<SubsystemHandle> {
        if let Ok(subsystems) = self.subsystems.read() {
            subsystems.get(&id).cloned()
        } else {
            None
        }
    }

    /// Get subsystem by name
    pub fn get_by_name(&self, name: &str) -> Option<SubsystemHandle> {
        if let Ok(name_map) = self.name_to_id.read() {
            name_map.get(name).and_then(|&id| self.get(id))
        } else {
            None
        }
    }

    /// Set active state
    pub fn set_active(&self, id: SubsystemId, active: bool) -> bool {
        if let Some(handle) = self.get(id) {
            handle.set_active(active);
            true
        } else {
            false
        }
    }

    /// Check if subsystem is active
    pub fn is_active(&self, id: SubsystemId) -> bool {
        self.get(id).map(|h| h.is_active()).unwrap_or(false)
    }

    /// List all subsystems
    pub fn list_all(&self) -> Vec<(SubsystemId, SubsystemHandle)> {
        if let Ok(subsystems) = self.subsystems.read() {
            subsystems
                .iter()
                .map(|(&id, handle)| (id, handle.clone()))
                .collect()
        } else {
            Vec::new()
        }
    }

    /// Get count
    pub fn count(&self) -> usize {
        if let Ok(subsystems) = self.subsystems.read() {
            subsystems.len()
        } else {
            0
        }
    }

    /// Clear all subsystems
    pub fn clear(&self) {
        if let Ok(mut subsystems) = self.subsystems.write() {
            subsystems.clear();
        }
        if let Ok(mut name_map) = self.name_to_id.write() {
            name_map.clear();
        }
    }

    /// Check if all dependencies are satisfied
    pub fn check_dependencies(&self, id: SubsystemId) -> Result<(), Vec<SubsystemId>> {
        if let Some(handle) = self.get(id) {
            let missing: Vec<SubsystemId> = handle
                .dependencies()
                .iter()
                .filter(|&&dep_id| !self.is_active(dep_id))
                .cloned()
                .collect();

            if missing.is_empty() {
                Ok(())
            } else {
                Err(missing)
            }
        } else {
            Err(vec![])
        }
    }

    /// Emit event to all subsystems
    pub fn broadcast(&self, event: OrchestrationEvent) {
        self.event_bus.publish(event);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_registry_creation() {
        let registry = SubsystemRegistry::new(Arc::new(EventBus::new()));
        assert_eq!(registry.count(), 0);
    }

    #[test]
    fn test_register_subsystem() {
        let registry = SubsystemRegistry::new(Arc::new(EventBus::new()));

        let config = SubsystemConfig {
            name: "test".to_string(),
            description: "Test subsystem".to_string(),
            dependencies: vec![],
        };

        let id = registry.register(config);
        assert_eq!(id, 1);
        assert_eq!(registry.count(), 1);

        let handle = registry.get(id).unwrap();
        assert_eq!(handle.name(), "test");
    }

    #[test]
    fn test_unregister() {
        let registry = SubsystemRegistry::new(Arc::new(EventBus::new()));

        let config = SubsystemConfig {
            name: "test".to_string(),
            description: "Test".to_string(),
            dependencies: vec![],
        };

        let id = registry.register(config);
        assert!(registry.unregister(id));
        assert_eq!(registry.count(), 0);
        assert!(!registry.unregister(id));
    }

    #[test]
    fn test_get_by_name() {
        let registry = SubsystemRegistry::new(Arc::new(EventBus::new()));

        let config = SubsystemConfig {
            name: "test_garden".to_string(),
            description: "A test garden".to_string(),
            dependencies: vec![],
        };

        let id = registry.register(config);

        let handle = registry.get_by_name("test_garden").unwrap();
        assert_eq!(handle.id(), id);
    }

    #[test]
    fn test_active_state() {
        let registry = SubsystemRegistry::new(Arc::new(EventBus::new()));

        let config = SubsystemConfig {
            name: "test".to_string(),
            description: "Test".to_string(),
            dependencies: vec![],
        };

        let id = registry.register(config);

        assert!(!registry.is_active(id));

        registry.set_active(id, true);
        assert!(registry.is_active(id));

        registry.set_active(id, false);
        assert!(!registry.is_active(id));
    }

    #[test]
    fn test_dependencies() {
        let registry = SubsystemRegistry::new(Arc::new(EventBus::new()));

        // Register dependency first
        let dep_config = SubsystemConfig {
            name: "dependency".to_string(),
            description: "Dependency".to_string(),
            dependencies: vec![],
        };
        let dep_id = registry.register(dep_config);
        registry.set_active(dep_id, true);

        // Register subsystem with dependency
        let config = SubsystemConfig {
            name: "test".to_string(),
            description: "Test".to_string(),
            dependencies: vec![dep_id],
        };
        let id = registry.register(config);

        // Should be satisfied
        assert!(registry.check_dependencies(id).is_ok());

        // Deactivate dependency
        registry.set_active(dep_id, false);

        // Should fail
        let result = registry.check_dependencies(id);
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), vec![dep_id]);
    }
}
