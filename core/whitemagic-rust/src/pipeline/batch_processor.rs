//! Batch Processor - Batch Processing (PSR-005)
//! Target: 100× throughput for batch operations

use pyo3::prelude::*;
use rayon::prelude::*;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};

#[derive(Clone, Debug)]
#[pyclass]
pub struct BatchResult {
    #[pyo3(get)]
    pub batch_id: usize,
    #[pyo3(get)]
    pub processed: usize,
    #[pyo3(get)]
    pub succeeded: usize,
    #[pyo3(get)]
    pub failed: usize,
}

#[pymethods]
impl BatchResult {
    #[new]
    fn new(batch_id: usize, processed: usize, succeeded: usize, failed: usize) -> Self {
        Self {
            batch_id,
            processed,
            succeeded,
            failed,
        }
    }
}

#[pyclass]
pub struct PyBatchProcessor {
    batch_size: usize,
    total_processed: Arc<AtomicUsize>,
}

#[pymethods]
impl PyBatchProcessor {
    #[new]
    fn new(batch_size: Option<usize>) -> Self {
        Self {
            batch_size: batch_size.unwrap_or(1000),
            total_processed: Arc::new(AtomicUsize::new(0)),
        }
    }

    fn process_batches(&self, items: Vec<String>) -> Vec<BatchResult> {
        let total = self.total_processed.clone();
        
        items
            .par_chunks(self.batch_size)
            .enumerate()
            .map(|(batch_id, chunk)| {
                let processed = chunk.len();
                let succeeded = chunk.iter().filter(|s| !s.is_empty()).count();
                let failed = processed - succeeded;
                
                total.fetch_add(processed, Ordering::Relaxed);
                
                BatchResult {
                    batch_id,
                    processed,
                    succeeded,
                    failed,
                }
            })
            .collect()
    }

    fn process_with_transform(&self, items: Vec<i64>, multiplier: i64) -> Vec<i64> {
        items
            .par_iter()
            .map(|&x| {
                self.total_processed.fetch_add(1, Ordering::Relaxed);
                x * multiplier
            })
            .collect()
    }

    fn process_with_filter(&self, items: Vec<i64>, threshold: i64) -> Vec<i64> {
        items
            .par_iter()
            .filter(|&&x| {
                self.total_processed.fetch_add(1, Ordering::Relaxed);
                x > threshold
            })
            .copied()
            .collect()
    }

    fn get_total_processed(&self) -> usize {
        self.total_processed.load(Ordering::Relaxed)
    }

    fn reset_counter(&self) {
        self.total_processed.store(0, Ordering::Relaxed);
    }

    fn get_batch_size(&self) -> usize {
        self.batch_size
    }

    fn set_batch_size(&mut self, size: usize) {
        self.batch_size = size;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_processor_creation() {
        let processor = PyBatchProcessor::new(Some(500));
        assert_eq!(processor.get_batch_size(), 500);
    }

    #[test]
    fn test_process_batches() {
        let processor = PyBatchProcessor::new(Some(100));
        let items: Vec<String> = (0..250).map(|i| format!("item{}", i)).collect();
        
        let results = processor.process_batches(items);
        
        assert_eq!(results.len(), 3);
        assert_eq!(processor.get_total_processed(), 250);
    }

    #[test]
    fn test_process_with_transform() {
        let processor = PyBatchProcessor::new(None);
        let items = vec![1, 2, 3, 4, 5];
        
        let results = processor.process_with_transform(items, 2);
        
        assert_eq!(results, vec![2, 4, 6, 8, 10]);
    }

    #[test]
    fn test_process_with_filter() {
        let processor = PyBatchProcessor::new(None);
        let items = vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
        
        let results = processor.process_with_filter(items, 5);
        
        assert_eq!(results, vec![6, 7, 8, 9, 10]);
    }

    #[test]
    fn test_reset_counter() {
        let processor = PyBatchProcessor::new(None);
        
        processor.process_with_transform(vec![1, 2, 3], 2);
        assert_eq!(processor.get_total_processed(), 3);
        
        processor.reset_counter();
        assert_eq!(processor.get_total_processed(), 0);
    }
}
