//! Clone Army - Army Deployment and Coordination (PSR-005)
//! Target: 100× throughput improvement

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

#[derive(Clone, Debug)]
#[pyclass]
pub struct CloneArmy {
    #[pyo3(get)]
    pub army_id: String,
    #[pyo3(get)]
    pub size: usize,
    active_clones: Arc<RwLock<HashMap<String, CloneStatus>>>,
}

#[derive(Clone, Debug)]
struct CloneStatus {
    _clone_id: String,
    _task_id: String,
    status: String,
    _started_at: f64,
}

#[pymethods]
impl CloneArmy {
    #[new]
    fn new(army_id: String, size: usize) -> Self {
        Self {
            army_id,
            size,
            active_clones: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn deploy(&mut self, tasks: Vec<String>) -> PyResult<Vec<String>> {
        let mut clone_ids = Vec::new();
        let mut clones = self.active_clones.write().unwrap();
        
        for (idx, task) in tasks.iter().enumerate() {
            let clone_id = format!("{}-clone-{}", self.army_id, idx);
            clones.insert(
                clone_id.clone(),
                CloneStatus {
                    _clone_id: clone_id.clone(),
                    _task_id: task.clone(),
                    status: "deployed".to_string(),
                    _started_at: std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap()
                        .as_secs_f64(),
                },
            );
            clone_ids.push(clone_id);
        }
        
        Ok(clone_ids)
    }

    fn complete_clone(&mut self, clone_id: String, result: String) -> PyResult<bool> {
        let mut clones = self.active_clones.write().unwrap();
        
        if let Some(status) = clones.get_mut(&clone_id) {
            status.status = format!("completed: {}", result);
            Ok(true)
        } else {
            Ok(false)
        }
    }

    fn get_active_count(&self) -> PyResult<usize> {
        let clones = self.active_clones.read().unwrap();
        Ok(clones.len())
    }

    fn get_status(&self, clone_id: String) -> PyResult<Option<String>> {
        let clones = self.active_clones.read().unwrap();
        Ok(clones.get(&clone_id).map(|s| s.status.clone()))
    }

    fn collect_results(&self) -> PyResult<Vec<(String, String)>> {
        let clones = self.active_clones.read().unwrap();
        Ok(clones
            .iter()
            .map(|(id, status)| (id.clone(), status.status.clone()))
            .collect())
    }

    fn clear_completed(&mut self) -> PyResult<usize> {
        let mut clones = self.active_clones.write().unwrap();
        let initial_count = clones.len();
        clones.retain(|_, status| !status.status.starts_with("completed"));
        Ok(initial_count - clones.len())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clone_army_deployment() {
        let mut army = CloneArmy::new("test-army".to_string(), 100);
        let tasks = vec!["task1".to_string(), "task2".to_string()];
        let clone_ids = army.deploy(tasks).unwrap();
        assert_eq!(clone_ids.len(), 2);
        assert_eq!(army.get_active_count().unwrap(), 2);
    }

    #[test]
    fn test_clone_completion() {
        let mut army = CloneArmy::new("test-army".to_string(), 100);
        let tasks = vec!["task1".to_string()];
        let clone_ids = army.deploy(tasks).unwrap();
        
        let completed = army.complete_clone(clone_ids[0].clone(), "success".to_string()).unwrap();
        assert!(completed);
        
        let status = army.get_status(clone_ids[0].clone()).unwrap();
        assert!(status.unwrap().contains("completed"));
    }

    #[test]
    fn test_result_collection() {
        let mut army = CloneArmy::new("test-army".to_string(), 100);
        let tasks = vec!["task1".to_string(), "task2".to_string()];
        let clone_ids = army.deploy(tasks).unwrap();
        
        army.complete_clone(clone_ids[0].clone(), "result1".to_string()).unwrap();
        
        let results = army.collect_results().unwrap();
        assert_eq!(results.len(), 2);
    }
}
