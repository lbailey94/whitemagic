//! Dream Cycle Integration
//! Integrates with dream cycle for memory processing

use pyo3::prelude::*;
use std::collections::VecDeque;

#[pyclass]
pub struct DreamCycleIntegration {
    dream_queue: VecDeque<String>,
    processed_count: usize,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl DreamCycleIntegration {
    #[new]
    fn new() -> Self {
        Self {
            dream_queue: VecDeque::new(),
            processed_count: 0,
        }
    }
    
    fn queue_for_dreaming(&mut self, memory_id: String) -> PyResult<()> {
        self.dream_queue.push_back(memory_id);
        Ok(())
    }
    
    fn process_dream_batch(&mut self, batch_size: usize) -> PyResult<Vec<String>> {
        let mut processed = Vec::new();
        
        for _ in 0..batch_size {
            if let Some(memory_id) = self.dream_queue.pop_front() {
                processed.push(memory_id);
                self.processed_count += 1;
            } else {
                break;
            }
        }
        
        Ok(processed)
    }
    
    fn get_queue_size(&self) -> PyResult<usize> {
        Ok(self.dream_queue.len())
    }
    
    fn get_processed_count(&self) -> PyResult<usize> {
        Ok(self.processed_count)
    }
}
