//! Lieutenant - Sub-Agent Management (PSR-005)
//! Target: 100× throughput for sub-agent coordination

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Lieutenant {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub specialty: String,
    #[pyo3(get)]
    pub assigned_clones: usize,
}

#[pymethods]
impl Lieutenant {
    #[new]
    fn new(id: String, name: String, specialty: String) -> Self {
        Self {
            id,
            name,
            specialty,
            assigned_clones: 0,
        }
    }
}

#[pyclass]
pub struct PyLieutenantManager {
    lieutenants: Arc<RwLock<HashMap<String, Lieutenant>>>,
    assignments: Arc<RwLock<HashMap<String, Vec<String>>>>,
}

#[pymethods]
impl PyLieutenantManager {
    #[new]
    fn new() -> Self {
        Self {
            lieutenants: Arc::new(RwLock::new(HashMap::new())),
            assignments: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn register_lieutenant(&self, lieutenant: Lieutenant) {
        self.lieutenants.write().insert(lieutenant.id.clone(), lieutenant);
        self.assignments.write().insert(lieutenant.id.clone(), Vec::new());
    }

    fn assign_clone(&self, lieutenant_id: String, clone_id: String) -> bool {
        let mut lieutenants = self.lieutenants.write();
        let mut assignments = self.assignments.write();
        
        if let Some(lt) = lieutenants.get_mut(&lieutenant_id) {
            if let Some(clones) = assignments.get_mut(&lieutenant_id) {
                clones.push(clone_id);
                lt.assigned_clones = clones.len();
                return true;
            }
        }
        
        false
    }

    fn unassign_clone(&self, lieutenant_id: String, clone_id: String) -> bool {
        let mut lieutenants = self.lieutenants.write();
        let mut assignments = self.assignments.write();
        
        if let Some(lt) = lieutenants.get_mut(&lieutenant_id) {
            if let Some(clones) = assignments.get_mut(&lieutenant_id) {
                clones.retain(|id| id != &clone_id);
                lt.assigned_clones = clones.len();
                return true;
            }
        }
        
        false
    }

    fn get_lieutenant(&self, lieutenant_id: String) -> Option<Lieutenant> {
        self.lieutenants.read().get(&lieutenant_id).cloned()
    }

    fn get_assignments(&self, lieutenant_id: String) -> Vec<String> {
        self.assignments
            .read()
            .get(&lieutenant_id)
            .cloned()
            .unwrap_or_default()
    }

    fn get_all_lieutenants(&self) -> Vec<Lieutenant> {
        self.lieutenants.read().values().cloned().collect()
    }

    fn get_load_balance(&self) -> Vec<(String, usize)> {
        self.lieutenants
            .read()
            .values()
            .map(|lt| (lt.name.clone(), lt.assigned_clones))
            .collect()
    }

    fn lieutenant_count(&self) -> usize {
        self.lieutenants.read().len()
    }

    fn total_assigned_clones(&self) -> usize {
        self.lieutenants.read().values().map(|lt| lt.assigned_clones).sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_manager_creation() {
        let manager = PyLieutenantManager::new();
        assert_eq!(manager.lieutenant_count(), 0);
    }

    #[test]
    fn test_register_lieutenant() {
        let manager = PyLieutenantManager::new();
        let lt = Lieutenant::new("lt1".to_string(), "Alpha".to_string(), "recon".to_string());
        
        manager.register_lieutenant(lt);
        assert_eq!(manager.lieutenant_count(), 1);
    }

    #[test]
    fn test_assign_clone() {
        let manager = PyLieutenantManager::new();
        let lt = Lieutenant::new("lt1".to_string(), "Alpha".to_string(), "recon".to_string());
        
        manager.register_lieutenant(lt);
        assert!(manager.assign_clone("lt1".to_string(), "clone1".to_string()));
        
        let assignments = manager.get_assignments("lt1".to_string());
        assert_eq!(assignments.len(), 1);
    }

    #[test]
    fn test_load_balance() {
        let manager = PyLieutenantManager::new();
        
        manager.register_lieutenant(Lieutenant::new("lt1".to_string(), "Alpha".to_string(), "recon".to_string()));
        manager.register_lieutenant(Lieutenant::new("lt2".to_string(), "Beta".to_string(), "attack".to_string()));
        
        manager.assign_clone("lt1".to_string(), "c1".to_string());
        manager.assign_clone("lt1".to_string(), "c2".to_string());
        manager.assign_clone("lt2".to_string(), "c3".to_string());
        
        let balance = manager.get_load_balance();
        assert_eq!(balance.len(), 2);
    }

    #[test]
    fn test_unassign_clone() {
        let manager = PyLieutenantManager::new();
        let lt = Lieutenant::new("lt1".to_string(), "Alpha".to_string(), "recon".to_string());
        
        manager.register_lieutenant(lt);
        manager.assign_clone("lt1".to_string(), "clone1".to_string());
        
        assert!(manager.unassign_clone("lt1".to_string(), "clone1".to_string()));
        assert_eq!(manager.get_assignments("lt1".to_string()).len(), 0);
    }
}
