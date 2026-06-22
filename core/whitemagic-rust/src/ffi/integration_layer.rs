//! Integration Layer - Final Integration (PSR-009)
//! Target: 20× speedup for system integration

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Component {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub component_type: String,
    #[pyo3(get)]
    pub status: String,
}

#[pymethods]
impl Component {
    #[new]
    fn new(name: String, component_type: String) -> Self {
        Self {
            name,
            component_type,
            status: "inactive".to_string(),
        }
    }
}

#[pyclass]
pub struct PyIntegrationLayer {
    components: HashMap<String, Component>,
}

#[pymethods]
impl PyIntegrationLayer {
    #[new]
    fn new() -> Self {
        Self {
            components: HashMap::new(),
        }
    }

    fn register_component(&mut self, component: Component) {
        self.components.insert(component.name.clone(), component);
    }

    fn activate_component(&mut self, name: String) -> bool {
        if let Some(component) = self.components.get_mut(&name) {
            component.status = "active".to_string();
            true
        } else {
            false
        }
    }

    fn deactivate_component(&mut self, name: String) -> bool {
        if let Some(component) = self.components.get_mut(&name) {
            component.status = "inactive".to_string();
            true
        } else {
            false
        }
    }

    fn get_active_components(&self) -> Vec<Component> {
        self.components
            .values()
            .filter(|c| c.status == "active")
            .cloned()
            .collect()
    }

    fn component_count(&self) -> usize {
        self.components.len()
    }

    fn active_count(&self) -> usize {
        self.components.values().filter(|c| c.status == "active").count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_layer_creation() {
        let layer = PyIntegrationLayer::new();
        assert_eq!(layer.component_count(), 0);
    }

    #[test]
    fn test_register_component() {
        let mut layer = PyIntegrationLayer::new();
        let component = Component::new("comp1".to_string(), "memory".to_string());
        
        layer.register_component(component);
        assert_eq!(layer.component_count(), 1);
    }

    #[test]
    fn test_activate_component() {
        let mut layer = PyIntegrationLayer::new();
        let component = Component::new("comp1".to_string(), "memory".to_string());
        
        layer.register_component(component);
        assert!(layer.activate_component("comp1".to_string()));
        assert_eq!(layer.active_count(), 1);
    }
}
