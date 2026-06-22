//! Resource Manager - Resource Management (PSR-005)
//! Target: 50× speedup for resource tracking

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Resource {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub resource_type: String,
    #[pyo3(get)]
    pub allocated: bool,
    #[pyo3(get)]
    pub owner: Option<String>,
}

#[pymethods]
impl Resource {
    #[new]
    fn new(id: String, resource_type: String) -> Self {
        Self {
            id,
            resource_type,
            allocated: false,
            owner: None,
        }
    }
}

#[pyclass]
pub struct PyResourceManager {
    resources: Arc<RwLock<HashMap<String, Resource>>>,
    allocations: Arc<RwLock<HashMap<String, Vec<String>>>>,
}

#[pymethods]
impl PyResourceManager {
    #[new]
    fn new() -> Self {
        Self {
            resources: Arc::new(RwLock::new(HashMap::new())),
            allocations: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn register_resource(&self, resource: Resource) {
        self.resources.write().insert(resource.id.clone(), resource);
    }

    fn allocate(&self, resource_id: String, owner: String) -> bool {
        let mut resources = self.resources.write();
        
        if let Some(resource) = resources.get_mut(&resource_id) {
            if !resource.allocated {
                resource.allocated = true;
                resource.owner = Some(owner.clone());
                
                self.allocations
                    .write()
                    .entry(owner)
                    .or_insert_with(Vec::new)
                    .push(resource_id);
                
                return true;
            }
        }
        
        false
    }

    fn release(&self, resource_id: String) -> bool {
        let mut resources = self.resources.write();
        
        if let Some(resource) = resources.get_mut(&resource_id) {
            if resource.allocated {
                if let Some(owner) = &resource.owner {
                    if let Some(allocs) = self.allocations.write().get_mut(owner) {
                        allocs.retain(|id| id != &resource_id);
                    }
                }
                
                resource.allocated = false;
                resource.owner = None;
                return true;
            }
        }
        
        false
    }

    fn get_allocations(&self, owner: String) -> Vec<String> {
        self.allocations
            .read()
            .get(&owner)
            .cloned()
            .unwrap_or_default()
    }

    fn available_resources(&self, resource_type: Option<String>) -> Vec<String> {
        self.resources
            .read()
            .values()
            .filter(|r| {
                !r.allocated
                    && resource_type
                        .as_ref()
                        .map(|t| &r.resource_type == t)
                        .unwrap_or(true)
            })
            .map(|r| r.id.clone())
            .collect()
    }

    fn resource_count(&self) -> usize {
        self.resources.read().len()
    }

    fn allocated_count(&self) -> usize {
        self.resources.read().values().filter(|r| r.allocated).count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_register_resource() {
        let manager = PyResourceManager::new();
        let resource = Resource::new("r1".to_string(), "cpu".to_string());
        
        manager.register_resource(resource);
        assert_eq!(manager.resource_count(), 1);
    }

    #[test]
    fn test_allocate() {
        let manager = PyResourceManager::new();
        let resource = Resource::new("r1".to_string(), "cpu".to_string());
        
        manager.register_resource(resource);
        let allocated = manager.allocate("r1".to_string(), "task1".to_string());
        
        assert!(allocated);
        assert_eq!(manager.allocated_count(), 1);
    }

    #[test]
    fn test_release() {
        let manager = PyResourceManager::new();
        let resource = Resource::new("r1".to_string(), "cpu".to_string());
        
        manager.register_resource(resource);
        manager.allocate("r1".to_string(), "task1".to_string());
        
        let released = manager.release("r1".to_string());
        assert!(released);
        assert_eq!(manager.allocated_count(), 0);
    }

    #[test]
    fn test_available_resources() {
        let manager = PyResourceManager::new();
        
        manager.register_resource(Resource::new("r1".to_string(), "cpu".to_string()));
        manager.register_resource(Resource::new("r2".to_string(), "cpu".to_string()));
        
        manager.allocate("r1".to_string(), "task1".to_string());
        
        let available = manager.available_resources(Some("cpu".to_string()));
        assert_eq!(available.len(), 1);
    }
}
