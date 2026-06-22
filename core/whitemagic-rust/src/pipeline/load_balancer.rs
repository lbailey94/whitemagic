//! Load Balancer - Work Load Balancing (PSR-005)
//! Target: 100× throughput with optimal load distribution

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Worker {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub capacity: usize,
    #[pyo3(get)]
    pub current_load: usize,
}

#[pymethods]
impl Worker {
    #[new]
    fn new(id: String, capacity: usize) -> Self {
        Self {
            id,
            capacity,
            current_load: 0,
        }
    }

    fn available_capacity(&self) -> usize {
        self.capacity.saturating_sub(self.current_load)
    }

    fn load_percentage(&self) -> f64 {
        if self.capacity == 0 {
            return 100.0;
        }
        (self.current_load as f64 / self.capacity as f64) * 100.0
    }
}

#[pyclass]
pub struct PyLoadBalancer {
    workers: Arc<RwLock<HashMap<String, Worker>>>,
    round_robin_index: Arc<RwLock<usize>>,
}

#[pymethods]
impl PyLoadBalancer {
    #[new]
    fn new() -> Self {
        Self {
            workers: Arc::new(RwLock::new(HashMap::new())),
            round_robin_index: Arc::new(RwLock::new(0)),
        }
    }

    fn register_worker(&self, worker: Worker) {
        self.workers.write().insert(worker.id.clone(), worker);
    }

    fn assign_work(&self, work_size: usize) -> Option<String> {
        let mut workers = self.workers.write();
        
        // Find worker with most available capacity
        let best_worker = workers
            .values_mut()
            .filter(|w| w.available_capacity() >= work_size)
            .max_by_key(|w| w.available_capacity());
        
        if let Some(worker) = best_worker {
            worker.current_load += work_size;
            Some(worker.id.clone())
        } else {
            None
        }
    }

    fn assign_round_robin(&self, work_size: usize) -> Option<String> {
        let mut workers = self.workers.write();
        let mut index = self.round_robin_index.write();
        
        if workers.is_empty() {
            return None;
        }
        
        let worker_ids: Vec<String> = workers.keys().cloned().collect();
        let start_index = *index;
        
        loop {
            let worker_id = &worker_ids[*index % worker_ids.len()];
            
            if let Some(worker) = workers.get_mut(worker_id) {
                if worker.available_capacity() >= work_size {
                    worker.current_load += work_size;
                    *index = (*index + 1) % worker_ids.len();
                    return Some(worker.id.clone());
                }
            }
            
            *index = (*index + 1) % worker_ids.len();
            
            if *index == start_index {
                break;
            }
        }
        
        None
    }

    fn complete_work(&self, worker_id: String, work_size: usize) -> bool {
        if let Some(worker) = self.workers.write().get_mut(&worker_id) {
            worker.current_load = worker.current_load.saturating_sub(work_size);
            true
        } else {
            false
        }
    }

    fn get_worker_load(&self, worker_id: String) -> Option<usize> {
        self.workers.read().get(&worker_id).map(|w| w.current_load)
    }

    fn get_total_capacity(&self) -> usize {
        self.workers.read().values().map(|w| w.capacity).sum()
    }

    fn get_total_load(&self) -> usize {
        self.workers.read().values().map(|w| w.current_load).sum()
    }

    fn get_average_load_percentage(&self) -> f64 {
        let workers = self.workers.read();
        if workers.is_empty() {
            return 0.0;
        }
        
        let total: f64 = workers.values().map(|w| w.load_percentage()).sum();
        total / workers.len() as f64
    }

    fn worker_count(&self) -> usize {
        self.workers.read().len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_balancer_creation() {
        let balancer = PyLoadBalancer::new();
        assert_eq!(balancer.worker_count(), 0);
    }

    #[test]
    fn test_register_worker() {
        let balancer = PyLoadBalancer::new();
        let worker = Worker::new("w1".to_string(), 100);
        
        balancer.register_worker(worker);
        assert_eq!(balancer.worker_count(), 1);
    }

    #[test]
    fn test_assign_work() {
        let balancer = PyLoadBalancer::new();
        
        balancer.register_worker(Worker::new("w1".to_string(), 100));
        balancer.register_worker(Worker::new("w2".to_string(), 200));
        
        let assigned = balancer.assign_work(50);
        assert!(assigned.is_some());
        assert_eq!(assigned.unwrap(), "w2");
    }

    #[test]
    fn test_complete_work() {
        let balancer = PyLoadBalancer::new();
        
        balancer.register_worker(Worker::new("w1".to_string(), 100));
        balancer.assign_work(50);
        
        assert_eq!(balancer.get_worker_load("w1".to_string()), Some(50));
        
        balancer.complete_work("w1".to_string(), 30);
        assert_eq!(balancer.get_worker_load("w1".to_string()), Some(20));
    }

    #[test]
    fn test_total_capacity() {
        let balancer = PyLoadBalancer::new();
        
        balancer.register_worker(Worker::new("w1".to_string(), 100));
        balancer.register_worker(Worker::new("w2".to_string(), 200));
        
        assert_eq!(balancer.get_total_capacity(), 300);
    }
}
