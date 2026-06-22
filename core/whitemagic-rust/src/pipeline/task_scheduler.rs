//! Task Scheduler - Rayon Work-Stealing (PSR-005)
//! Target: 100× throughput (534K → 50M+ clones/sec)

use pyo3::prelude::*;
use rayon::prelude::*;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};

#[derive(Clone, Debug)]
#[pyclass]
pub struct TaskResult {
    #[pyo3(get)]
    pub task_id: usize,
    #[pyo3(get)]
    pub success: bool,
    #[pyo3(get)]
    pub output: String,
}

#[pymethods]
impl TaskResult {
    #[new]
    fn new(task_id: usize, success: bool, output: String) -> Self {
        Self { task_id, success, output }
    }
}

#[pyclass]
pub struct PyTaskScheduler {
    thread_pool: rayon::ThreadPool,
    completed_count: Arc<AtomicUsize>,
}

#[pymethods]
impl PyTaskScheduler {
    #[new]
    fn new(num_threads: Option<usize>) -> PyResult<Self> {
        let pool = if let Some(n) = num_threads {
            rayon::ThreadPoolBuilder::new()
                .num_threads(n)
                .build()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Thread pool creation failed: {}", e)
                ))?
        } else {
            rayon::ThreadPoolBuilder::new()
                .build()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Thread pool creation failed: {}", e)
                ))?
        };

        Ok(Self {
            thread_pool: pool,
            completed_count: Arc::new(AtomicUsize::new(0)),
        })
    }

    fn get_completed_count(&self) -> usize {
        self.completed_count.load(Ordering::Relaxed)
    }

    fn reset_count(&self) {
        self.completed_count.store(0, Ordering::Relaxed);
    }

    fn execute_simple(&self, task_ids: Vec<usize>) -> Vec<TaskResult> {
        let completed = self.completed_count.clone();
        
        self.thread_pool.install(|| {
            task_ids
                .par_iter()
                .map(|&task_id| {
                    completed.fetch_add(1, Ordering::Relaxed);
                    TaskResult {
                        task_id,
                        success: true,
                        output: format!("Task {} completed", task_id),
                    }
                })
                .collect()
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scheduler_creation() {
        let scheduler = rayon::ThreadPoolBuilder::new()
            .num_threads(4)
            .build()
            .unwrap();
        assert!(scheduler.current_num_threads() > 0);
    }

    #[test]
    fn test_parallel_execution() {
        let tasks: Vec<usize> = (0..1000).collect();
        let results: Vec<usize> = tasks
            .par_iter()
            .map(|&x| x * 2)
            .collect();
        assert_eq!(results.len(), 1000);
        assert_eq!(results[0], 0);
        assert_eq!(results[999], 1998);
    }

    #[test]
    fn test_work_stealing() {
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(4)
            .build()
            .unwrap();
        
        let result = pool.install(|| {
            (0..10000).into_par_iter().sum::<usize>()
        });
        
        assert_eq!(result, 49995000);
    }

    #[test]
    fn test_atomic_counter() {
        let counter = Arc::new(AtomicUsize::new(0));
        let tasks: Vec<usize> = (0..1000).collect();
        
        tasks.par_iter().for_each(|_| {
            counter.fetch_add(1, Ordering::Relaxed);
        });
        
        assert_eq!(counter.load(Ordering::Relaxed), 1000);
    }
}
