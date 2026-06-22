//! System Coordinator - System-Wide Coordination (PSR-009)
//! Target: 30× speedup for coordination

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct SystemEvent {
    #[pyo3(get)]
    pub event_type: String,
    #[pyo3(get)]
    pub source: String,
    #[pyo3(get)]
    pub data: HashMap<String, String>,
}

#[pymethods]
impl SystemEvent {
    #[new]
    fn new(event_type: String, source: String) -> Self {
        Self {
            event_type,
            source,
            data: HashMap::new(),
        }
    }

    fn add_data(&mut self, key: String, value: String) {
        self.data.insert(key, value);
    }
}

#[pyclass]
pub struct PySystemCoordinator {
    events: Arc<RwLock<Vec<SystemEvent>>>,
    subscribers: Arc<RwLock<HashMap<String, Vec<String>>>>,
}

#[pymethods]
impl PySystemCoordinator {
    #[new]
    fn new() -> Self {
        Self {
            events: Arc::new(RwLock::new(Vec::new())),
            subscribers: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn publish_event(&self, event: SystemEvent) {
        self.events.write().push(event);
    }

    fn subscribe(&self, event_type: String, subscriber: String) {
        self.subscribers
            .write()
            .entry(event_type)
            .or_insert_with(Vec::new)
            .push(subscriber);
    }

    fn get_events(&self, event_type: Option<String>) -> Vec<SystemEvent> {
        let events = self.events.read();
        
        if let Some(et) = event_type {
            events.iter().filter(|e| e.event_type == et).cloned().collect()
        } else {
            events.clone()
        }
    }

    fn get_subscribers(&self, event_type: String) -> Vec<String> {
        self.subscribers
            .read()
            .get(&event_type)
            .cloned()
            .unwrap_or_default()
    }

    fn event_count(&self) -> usize {
        self.events.read().len()
    }

    fn subscriber_count(&self) -> usize {
        self.subscribers.read().values().map(|v| v.len()).sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_coordinator_creation() {
        let coordinator = PySystemCoordinator::new();
        assert_eq!(coordinator.event_count(), 0);
    }

    #[test]
    fn test_publish_event() {
        let coordinator = PySystemCoordinator::new();
        let event = SystemEvent::new("test".to_string(), "source1".to_string());
        
        coordinator.publish_event(event);
        assert_eq!(coordinator.event_count(), 1);
    }

    #[test]
    fn test_subscribe() {
        let coordinator = PySystemCoordinator::new();
        
        coordinator.subscribe("test".to_string(), "sub1".to_string());
        assert_eq!(coordinator.subscriber_count(), 1);
    }

    #[test]
    fn test_get_events() {
        let coordinator = PySystemCoordinator::new();
        
        coordinator.publish_event(SystemEvent::new("type1".to_string(), "s1".to_string()));
        coordinator.publish_event(SystemEvent::new("type2".to_string(), "s2".to_string()));
        
        let events = coordinator.get_events(Some("type1".to_string()));
        assert_eq!(events.len(), 1);
    }
}
