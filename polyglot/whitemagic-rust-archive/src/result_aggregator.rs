//! Result Aggregator - Lock-Free Results (PSR-005)
//! Target: 50× speedup for result collection

use pyo3::prelude::*;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct AggregatedResult {
    #[pyo3(get)]
    pub total_count: usize,
    #[pyo3(get)]
    pub success_count: usize,
    #[pyo3(get)]
    pub failure_count: usize,
    #[pyo3(get)]
    pub results: Vec<String>,
}

#[pymethods]
impl AggregatedResult {
    #[new]
    fn new() -> Self {
        Self {
            total_count: 0,
            success_count: 0,
            failure_count: 0,
            results: Vec::new(),
        }
    }
    
    fn success_rate(&self) -> f64 {
        if self.total_count == 0 {
            return 0.0;
        }
        self.success_count as f64 / self.total_count as f64
    }
}

#[pyclass]
pub struct PyResultAggregator {
    total: Arc<AtomicUsize>,
    success: Arc<AtomicUsize>,
    failure: Arc<AtomicUsize>,
    results: Arc<RwLock<Vec<String>>>,
}

#[pymethods]
impl PyResultAggregator {
    #[new]
    fn new() -> Self {
        Self {
            total: Arc::new(AtomicUsize::new(0)),
            success: Arc::new(AtomicUsize::new(0)),
            failure: Arc::new(AtomicUsize::new(0)),
            results: Arc::new(RwLock::new(Vec::new())),
        }
    }

    fn add_success(&self, result: String) {
        self.total.fetch_add(1, Ordering::Relaxed);
        self.success.fetch_add(1, Ordering::Relaxed);
        self.results.write().push(result);
    }

    fn add_failure(&self, error: String) {
        self.total.fetch_add(1, Ordering::Relaxed);
        self.failure.fetch_add(1, Ordering::Relaxed);
        self.results.write().push(format!("ERROR: {}", error));
    }

    fn get_stats(&self) -> AggregatedResult {
        AggregatedResult {
            total_count: self.total.load(Ordering::Relaxed),
            success_count: self.success.load(Ordering::Relaxed),
            failure_count: self.failure.load(Ordering::Relaxed),
            results: self.results.read().clone(),
        }
    }

    fn reset(&self) {
        self.total.store(0, Ordering::Relaxed);
        self.success.store(0, Ordering::Relaxed);
        self.failure.store(0, Ordering::Relaxed);
        self.results.write().clear();
    }

    fn get_total(&self) -> usize {
        self.total.load(Ordering::Relaxed)
    }

    fn get_success_count(&self) -> usize {
        self.success.load(Ordering::Relaxed)
    }

    fn get_failure_count(&self) -> usize {
        self.failure.load(Ordering::Relaxed)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::thread;

    #[test]
    fn test_aggregator_creation() {
        let agg = PyResultAggregator::new();
        assert_eq!(agg.get_total(), 0);
        assert_eq!(agg.get_success_count(), 0);
        assert_eq!(agg.get_failure_count(), 0);
    }

    #[test]
    fn test_add_results() {
        let agg = PyResultAggregator::new();
        agg.add_success("test1".to_string());
        agg.add_success("test2".to_string());
        agg.add_failure("error1".to_string());
        
        assert_eq!(agg.get_total(), 3);
        assert_eq!(agg.get_success_count(), 2);
        assert_eq!(agg.get_failure_count(), 1);
    }

    #[test]
    fn test_concurrent_aggregation() {
        let agg = Arc::new(PyResultAggregator::new());
        let mut handles = vec![];
        
        for i in 0..10 {
            let agg_clone = Arc::clone(&agg);
            let handle = thread::spawn(move || {
                for j in 0..100 {
                    if (i + j) % 2 == 0 {
                        agg_clone.add_success(format!("success-{}-{}", i, j));
                    } else {
                        agg_clone.add_failure(format!("failure-{}-{}", i, j));
                    }
                }
            });
            handles.push(handle);
        }
        
        for handle in handles {
            handle.join().unwrap();
        }
        
        assert_eq!(agg.get_total(), 1000);
        assert_eq!(agg.get_success_count() + agg.get_failure_count(), 1000);
    }

    #[test]
    fn test_reset() {
        let agg = PyResultAggregator::new();
        agg.add_success("test".to_string());
        agg.add_failure("error".to_string());
        
        assert_eq!(agg.get_total(), 2);
        
        agg.reset();
        
        assert_eq!(agg.get_total(), 0);
        assert_eq!(agg.get_success_count(), 0);
        assert_eq!(agg.get_failure_count(), 0);
    }
}
