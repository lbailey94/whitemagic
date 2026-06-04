//! Clone Lifecycle - Clone Lifecycle Management (PSR-005)
//! Target: 100× throughput for clone management

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug, PartialEq)]
pub enum CloneState {
    Created,
    Running,
    Completed,
    Failed,
    Terminated,
}

#[derive(Clone, Debug)]
#[pyclass]
pub struct Clone {
    #[pyo3(get)]
    pub id: usize,
    #[pyo3(get)]
    pub task_id: String,
    #[pyo3(get)]
    pub created_at: u64,
    #[pyo3(get)]
    pub completed_at: Option<u64>,
    state: CloneState,
}

#[pymethods]
impl Clone {
    #[new]
    fn new(id: usize, task_id: String) -> Self {
        Self {
            id,
            task_id,
            created_at: current_timestamp(),
            completed_at: None,
            state: CloneState::Created,
        }
    }

    fn get_state(&self) -> String {
        match self.state {
            CloneState::Created => "created".to_string(),
            CloneState::Running => "running".to_string(),
            CloneState::Completed => "completed".to_string(),
            CloneState::Failed => "failed".to_string(),
            CloneState::Terminated => "terminated".to_string(),
        }
    }
}

#[pyclass]
pub struct PyCloneLifecycleManager {
    clones: Arc<RwLock<HashMap<usize, Clone>>>,
    next_id: Arc<RwLock<usize>>,
}

#[pymethods]
impl PyCloneLifecycleManager {
    #[new]
    fn new() -> Self {
        Self {
            clones: Arc::new(RwLock::new(HashMap::new())),
            next_id: Arc::new(RwLock::new(0)),
        }
    }

    fn create_clone(&self, task_id: String) -> usize {
        let mut next_id = self.next_id.write();
        let id = *next_id;
        *next_id += 1;
        
        let clone = Clone::new(id, task_id);
        self.clones.write().insert(id, clone);
        
        id
    }

    fn start_clone(&self, id: usize) -> bool {
        if let Some(clone) = self.clones.write().get_mut(&id) {
            if clone.state == CloneState::Created {
                clone.state = CloneState::Running;
                return true;
            }
        }
        false
    }

    fn complete_clone(&self, id: usize) -> bool {
        if let Some(clone) = self.clones.write().get_mut(&id) {
            if clone.state == CloneState::Running {
                clone.state = CloneState::Completed;
                clone.completed_at = Some(current_timestamp());
                return true;
            }
        }
        false
    }

    fn fail_clone(&self, id: usize) -> bool {
        if let Some(clone) = self.clones.write().get_mut(&id) {
            clone.state = CloneState::Failed;
            clone.completed_at = Some(current_timestamp());
            return true;
        }
        false
    }

    fn terminate_clone(&self, id: usize) -> bool {
        if let Some(clone) = self.clones.write().get_mut(&id) {
            clone.state = CloneState::Terminated;
            clone.completed_at = Some(current_timestamp());
            return true;
        }
        false
    }

    fn get_clone(&self, id: usize) -> Option<Clone> {
        self.clones.read().get(&id).cloned()
    }

    fn get_clones_by_state(&self, state: String) -> Vec<Clone> {
        let target_state = match state.as_str() {
            "created" => CloneState::Created,
            "running" => CloneState::Running,
            "completed" => CloneState::Completed,
            "failed" => CloneState::Failed,
            "terminated" => CloneState::Terminated,
            _ => return Vec::new(),
        };
        
        self.clones
            .read()
            .values()
            .filter(|c| c.state == target_state)
            .cloned()
            .collect()
    }

    fn total_clones(&self) -> usize {
        self.clones.read().len()
    }

    fn active_clones(&self) -> usize {
        self.clones
            .read()
            .values()
            .filter(|c| c.state == CloneState::Running)
            .count()
    }

    fn cleanup_completed(&self, max_age_seconds: u64) -> usize {
        let now = current_timestamp();
        let mut clones = self.clones.write();
        let initial_count = clones.len();
        
        clones.retain(|_, clone| {
            if clone.state == CloneState::Completed {
                if let Some(completed_at) = clone.completed_at {
                    return now - completed_at < max_age_seconds;
                }
            }
            true
        });
        
        initial_count - clones.len()
    }
}

fn current_timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_clone() {
        let manager = PyCloneLifecycleManager::new();
        let id = manager.create_clone("task1".to_string());
        
        assert_eq!(id, 0);
        assert_eq!(manager.total_clones(), 1);
    }

    #[test]
    fn test_clone_lifecycle() {
        let manager = PyCloneLifecycleManager::new();
        let id = manager.create_clone("task1".to_string());
        
        assert!(manager.start_clone(id));
        assert_eq!(manager.active_clones(), 1);
        
        assert!(manager.complete_clone(id));
        assert_eq!(manager.active_clones(), 0);
    }

    #[test]
    fn test_get_clones_by_state() {
        let manager = PyCloneLifecycleManager::new();
        
        let id1 = manager.create_clone("task1".to_string());
        let id2 = manager.create_clone("task2".to_string());
        
        manager.start_clone(id1);
        
        let running = manager.get_clones_by_state("running".to_string());
        assert_eq!(running.len(), 1);
        
        let created = manager.get_clones_by_state("created".to_string());
        assert_eq!(created.len(), 1);
    }

    #[test]
    fn test_cleanup_completed() {
        let manager = PyCloneLifecycleManager::new();
        
        let id = manager.create_clone("task1".to_string());
        manager.start_clone(id);
        manager.complete_clone(id);
        
        let cleaned = manager.cleanup_completed(0);
        assert_eq!(cleaned, 1);
        assert_eq!(manager.total_clones(), 0);
    }
}
