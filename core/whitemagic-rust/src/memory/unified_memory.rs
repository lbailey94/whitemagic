//! Unified Memory Manager (PSR-001)
//! Target: 20-50× speedup over Python unified.py

use pyo3::prelude::*;
use std::sync::Arc;
use parking_lot::RwLock;
use std::collections::HashMap;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Memory {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub content: String,
    #[pyo3(get, set)]
    pub importance: f64,
    #[pyo3(get, set)]
    pub access_count: usize,
    #[pyo3(get, set)]
    pub is_protected: bool,
}

#[pymethods]
impl Memory {
    #[new]
    fn new(id: String, content: String) -> Self {
        Self {
            id,
            content,
            importance: 0.5,
            access_count: 0,
            is_protected: false,
        }
    }
}

#[pyclass]
pub struct PyUnifiedMemory {
    memories: Arc<RwLock<HashMap<String, Memory>>>,
    access_log: Arc<RwLock<Vec<String>>>,
}

#[pymethods]
impl PyUnifiedMemory {
    #[new]
    fn new() -> Self {
        Self {
            memories: Arc::new(RwLock::new(HashMap::new())),
            access_log: Arc::new(RwLock::new(Vec::new())),
        }
    }

    fn store(&self, memory: Memory) -> PyResult<()> {
        let mut memories = self.memories.write();
        memories.insert(memory.id.clone(), memory);
        Ok(())
    }

    fn retrieve(&self, id: String) -> PyResult<Option<Memory>> {
        let mut memories = self.memories.write();
        
        if let Some(mem) = memories.get_mut(&id) {
            mem.access_count += 1;
            self.access_log.write().push(id.clone());
            Ok(Some(mem.clone()))
        } else {
            Ok(None)
        }
    }

    fn batch_retrieve(&self, ids: Vec<String>) -> Vec<Option<Memory>> {
        let mut memories = self.memories.write();
        let mut results = Vec::with_capacity(ids.len());
        
        for id in ids {
            if let Some(mem) = memories.get_mut(&id) {
                mem.access_count += 1;
                self.access_log.write().push(id.clone());
                results.push(Some(mem.clone()));
            } else {
                results.push(None);
            }
        }
        
        results
    }

    fn delete(&self, id: String) -> PyResult<bool> {
        let mut memories = self.memories.write();
        Ok(memories.remove(&id).is_some())
    }

    fn count(&self) -> usize {
        self.memories.read().len()
    }

    fn get_all_ids(&self) -> Vec<String> {
        self.memories.read().keys().cloned().collect()
    }

    fn update_importance(&self, id: String, importance: f64) -> PyResult<bool> {
        let mut memories = self.memories.write();
        if let Some(mem) = memories.get_mut(&id) {
            mem.importance = importance;
            Ok(true)
        } else {
            Ok(false)
        }
    }

    fn get_access_log(&self, limit: Option<usize>) -> Vec<String> {
        let log = self.access_log.read();
        if let Some(n) = limit {
            log.iter().rev().take(n).cloned().collect()
        } else {
            log.clone()
        }
    }

    fn clear_access_log(&self) {
        self.access_log.write().clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_store_and_retrieve() {
        let um = PyUnifiedMemory::new();
        let mem = Memory::new("test1".to_string(), "content".to_string());
        
        um.store(mem.clone()).unwrap();
        let retrieved = um.retrieve("test1".to_string()).unwrap();
        
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().id, "test1");
    }

    #[test]
    fn test_access_count() {
        let um = PyUnifiedMemory::new();
        let mem = Memory::new("test1".to_string(), "content".to_string());
        
        um.store(mem).unwrap();
        um.retrieve("test1".to_string()).unwrap();
        um.retrieve("test1".to_string()).unwrap();
        
        let retrieved = um.retrieve("test1".to_string()).unwrap().unwrap();
        assert_eq!(retrieved.access_count, 3);
    }

    #[test]
    fn test_batch_retrieve() {
        let um = PyUnifiedMemory::new();
        
        for i in 0..5 {
            let mem = Memory::new(format!("test{}", i), format!("content{}", i));
            um.store(mem).unwrap();
        }
        
        let ids = vec!["test0".to_string(), "test2".to_string(), "test4".to_string()];
        let results = um.batch_retrieve(ids);
        
        assert_eq!(results.len(), 3);
        assert!(results[0].is_some());
        assert!(results[1].is_some());
        assert!(results[2].is_some());
    }

    #[test]
    fn test_delete() {
        let um = PyUnifiedMemory::new();
        let mem = Memory::new("test1".to_string(), "content".to_string());
        
        um.store(mem).unwrap();
        assert_eq!(um.count(), 1);
        
        um.delete("test1".to_string()).unwrap();
        assert_eq!(um.count(), 0);
    }
}
