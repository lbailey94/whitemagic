//! Advanced Scheduler - Work-Stealing Task Scheduler (PSR-005)
//! Target: 100× throughput improvement

use pyo3::prelude::*;
use rayon::prelude::*;
use std::sync::{Arc, Mutex};
use std::collections::VecDeque;

#[derive(Clone, Debug)]
#[pyclass]
pub struct AdvancedScheduler {
    #[pyo3(get)]
    pub worker_count: usize,
    task_queue: Arc<Mutex<VecDeque<Task>>>,
    results: Arc<Mutex<Vec<TaskResult>>>,
}

#[derive(Clone, Debug)]
struct Task {
    id: String,
    _priority: i32,
    payload: String,
}

#[derive(Clone, Debug)]
struct TaskResult {
    task_id: String,
    result: String,
    duration_ms: f64,
}

#[pymethods]
impl AdvancedScheduler {
    #[new]
    fn new(worker_count: Option<usize>) -> Self {
        let workers = worker_count.unwrap_or_else(|| rayon::current_num_threads());
        
        Self {
            worker_count: workers,
            task_queue: Arc::new(Mutex::new(VecDeque::new())),
            results: Arc::new(Mutex::new(Vec::new())),
        }
    }

    fn submit_task(&mut self, task_id: String, priority: i32, payload: String) -> PyResult<()> {
        let mut queue = self.task_queue.lock().unwrap();
        queue.push_back(Task {
            id: task_id,
            _priority: priority,
            payload,
        });
        Ok(())
    }

    fn submit_batch(&mut self, tasks: Vec<(String, i32, String)>) -> PyResult<usize> {
        let mut queue = self.task_queue.lock().unwrap();
        for (id, priority, payload) in tasks {
            queue.push_back(Task {
                id,
                _priority: priority,
                payload,
            });
        }
        Ok(queue.len())
    }

    fn execute_parallel(&mut self) -> PyResult<usize> {
        let tasks: Vec<Task> = {
            let mut queue = self.task_queue.lock().unwrap();
            queue.drain(..).collect()
        };

        let results: Vec<TaskResult> = tasks
            .par_iter()
            .map(|task| {
                let start = std::time::Instant::now();
                let result = format!("processed: {}", task.payload);
                let duration = start.elapsed().as_secs_f64() * 1000.0;
                
                TaskResult {
                    task_id: task.id.clone(),
                    result,
                    duration_ms: duration,
                }
            })
            .collect();

        let count = results.len();
        self.results.lock().unwrap().extend(results);
        Ok(count)
    }

    fn get_results(&self) -> PyResult<Vec<(String, String, f64)>> {
        let results = self.results.lock().unwrap();
        Ok(results
            .iter()
            .map(|r| (r.task_id.clone(), r.result.clone(), r.duration_ms))
            .collect())
    }

    fn clear_results(&mut self) -> PyResult<usize> {
        let mut results = self.results.lock().unwrap();
        let count = results.len();
        results.clear();
        Ok(count)
    }

    fn pending_count(&self) -> PyResult<usize> {
        Ok(self.task_queue.lock().unwrap().len())
    }

    fn completed_count(&self) -> PyResult<usize> {
        Ok(self.results.lock().unwrap().len())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scheduler_creation() {
        let scheduler = AdvancedScheduler::new(Some(4));
        assert_eq!(scheduler.worker_count, 4);
    }

    #[test]
    fn test_task_submission() {
        let mut scheduler = AdvancedScheduler::new(Some(4));
        scheduler.submit_task("task1".to_string(), 5, "data".to_string()).unwrap();
        assert_eq!(scheduler.pending_count().unwrap(), 1);
    }

    #[test]
    fn test_parallel_execution() {
        let mut scheduler = AdvancedScheduler::new(Some(4));
        let tasks = vec![
            ("task1".to_string(), 5, "data1".to_string()),
            ("task2".to_string(), 3, "data2".to_string()),
        ];
        scheduler.submit_batch(tasks).unwrap();
        
        let executed = scheduler.execute_parallel().unwrap();
        assert_eq!(executed, 2);
        assert_eq!(scheduler.completed_count().unwrap(), 2);
    }
}
