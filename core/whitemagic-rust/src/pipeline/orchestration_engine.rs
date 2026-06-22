//! Orchestration Engine - Campaign Orchestration (PSR-007)
//! Target: 30× speedup for orchestration

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Task {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub task_type: String,
    #[pyo3(get)]
    pub priority: i32,
    #[pyo3(get)]
    pub status: String,
}

#[pymethods]
impl Task {
    #[new]
    fn new(id: String, task_type: String, priority: i32) -> Self {
        Self {
            id,
            task_type,
            priority,
            status: "pending".to_string(),
        }
    }
}

#[pyclass]
pub struct PyOrchestrationEngine {
    tasks: Arc<RwLock<HashMap<String, Task>>>,
    execution_order: Arc<RwLock<Vec<String>>>,
}

#[pymethods]
impl PyOrchestrationEngine {
    #[new]
    fn new() -> Self {
        Self {
            tasks: Arc::new(RwLock::new(HashMap::new())),
            execution_order: Arc::new(RwLock::new(Vec::new())),
        }
    }

    fn add_task(&self, task: Task) {
        let id = task.id.clone();
        self.tasks.write().insert(id.clone(), task);
        self.execution_order.write().push(id);
    }

    fn get_task(&self, task_id: String) -> Option<Task> {
        self.tasks.read().get(&task_id).cloned()
    }

    fn update_status(&self, task_id: String, status: String) -> bool {
        if let Some(task) = self.tasks.write().get_mut(&task_id) {
            task.status = status;
            true
        } else {
            false
        }
    }

    fn get_pending_tasks(&self) -> Vec<Task> {
        self.tasks
            .read()
            .values()
            .filter(|t| t.status == "pending")
            .cloned()
            .collect()
    }

    fn get_next_task(&self) -> Option<Task> {
        let tasks = self.tasks.read();
        
        self.execution_order
            .read()
            .iter()
            .filter_map(|id| tasks.get(id))
            .find(|t| t.status == "pending")
            .cloned()
    }

    fn task_count(&self) -> usize {
        self.tasks.read().len()
    }

    fn completed_count(&self) -> usize {
        self.tasks
            .read()
            .values()
            .filter(|t| t.status == "completed")
            .count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_creation() {
        let engine = PyOrchestrationEngine::new();
        assert_eq!(engine.task_count(), 0);
    }

    #[test]
    fn test_add_task() {
        let engine = PyOrchestrationEngine::new();
        let task = Task::new("t1".to_string(), "test".to_string(), 1);
        
        engine.add_task(task);
        assert_eq!(engine.task_count(), 1);
    }

    #[test]
    fn test_update_status() {
        let engine = PyOrchestrationEngine::new();
        let task = Task::new("t1".to_string(), "test".to_string(), 1);
        
        engine.add_task(task);
        assert!(engine.update_status("t1".to_string(), "completed".to_string()));
        assert_eq!(engine.completed_count(), 1);
    }

    #[test]
    fn test_get_next_task() {
        let engine = PyOrchestrationEngine::new();
        
        engine.add_task(Task::new("t1".to_string(), "test".to_string(), 1));
        engine.add_task(Task::new("t2".to_string(), "test".to_string(), 2));
        
        let next = engine.get_next_task();
        assert!(next.is_some());
    }
}
