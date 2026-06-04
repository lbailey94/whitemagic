//! unified - Rust Migration
//! Unified memory interface with safety guarantees
//! Target: 20-50× speedup + memory safety

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

#[pyclass]
pub struct UnifiedMemory {
    memories: Arc<RwLock<HashMap<String, String>>>,
    stats: Arc<RwLock<MemoryStats>>,
}

#[pyclass]
#[derive(Clone)]
pub struct MemoryStats {
    #[pyo3(get)]
    pub total_memories: usize,
    #[pyo3(get)]
    pub total_size: usize,
}

#[pymethods]
impl UnifiedMemory {
    #[new]
    fn new() -> Self {
        Self {
            memories: Arc::new(RwLock::new(HashMap::new())),
            stats: Arc::new(RwLock::new(MemoryStats {
                total_memories: 0,
                total_size: 0,
            })),
        }
    }
    
    fn store(&mut self, key: String, value: String) -> PyResult<()> {
        let mut memories = self.memories.write().unwrap();
        let mut stats = self.stats.write().unwrap();
        
        stats.total_size += value.len();
        memories.insert(key, value);
        stats.total_memories = memories.len();
        
        Ok(())
    }
    
    fn retrieve(&self, key: String) -> PyResult<Option<String>> {
        let memories = self.memories.read().unwrap();
        Ok(memories.get(&key).cloned())
    }
    
    fn get_stats(&self) -> PyResult<MemoryStats> {
        let stats = self.stats.read().unwrap();
        Ok(stats.clone())
    }
}
