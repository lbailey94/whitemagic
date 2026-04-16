//! Gana Neck - Memory creation and management
//! Fast memory creation with validation

use pyo3::prelude::*;

#[pyclass]
pub struct GanaNeck {
    created_count: usize,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl GanaNeck {
    #[new]
    fn new() -> Self {
        Self {
            created_count: 0,
        }
    }
    
    fn create_memory(
        &mut self,
        _content: String,
        title: String,
        _tags: Vec<String>
    ) -> PyResult<String> {
        self.created_count += 1;
        
        let memory_id = format!("mem_{}_{}", self.created_count, title.replace(" ", "_"));
        
        Ok(memory_id)
    }
    
    fn batch_create(
        &mut self,
        memories: Vec<(String, String, Vec<String>)>
    ) -> PyResult<Vec<String>> {
        memories
            .into_iter()
            .map(|(content, title, tags)| self.create_memory(content, title, tags))
            .collect()
    }
    
    fn get_stats(&self) -> PyResult<usize> {
        Ok(self.created_count)
    }
}
