//! Cache Manager - High-performance caching

use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
pub struct CacheManager {
    cache: HashMap<String, String>,
    max_size: usize,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl CacheManager {
    #[new]
    fn new(max_size: Option<usize>) -> Self {
        Self {
            cache: HashMap::new(),
            max_size: max_size.unwrap_or(1000),
        }
    }
    
    fn get(&self, key: String) -> PyResult<Option<String>> {
        Ok(self.cache.get(&key).cloned())
    }
    
    fn set(&mut self, key: String, value: String) -> PyResult<()> {
        if self.cache.len() >= self.max_size {
            // Simple eviction: remove first key
            if let Some(first_key) = self.cache.keys().next().cloned() {
                self.cache.remove(&first_key);
            }
        }
        
        self.cache.insert(key, value);
        
        Ok(())
    }
    
    fn clear(&mut self) -> PyResult<()> {
        self.cache.clear();
        Ok(())
    }
}
