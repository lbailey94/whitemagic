//! Unified Memory V2 - Unified Interface (PSR-001)
//! Target: 20-50× speedup for unified memory operations

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct MemoryV2 {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub content: String,
    #[pyo3(get)]
    pub importance: f64,
    #[pyo3(get)]
    pub access_count: usize,
    #[pyo3(get)]
    pub tags: Vec<String>,
}

#[pymethods]
impl MemoryV2 {
    #[new]
    fn new(id: String, content: String, tags: Vec<String>) -> Self {
        Self {
            id,
            content,
            importance: 0.5,
            access_count: 0,
            tags,
        }
    }
}

#[pyclass]
pub struct PyUnifiedMemoryV2 {
    memories: Arc<RwLock<HashMap<String, MemoryV2>>>,
    tag_index: Arc<RwLock<HashMap<String, Vec<String>>>>,
}

#[pymethods]
impl PyUnifiedMemoryV2 {
    #[new]
    fn new() -> Self {
        Self {
            memories: Arc::new(RwLock::new(HashMap::new())),
            tag_index: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn store(&self, memory: MemoryV2) {
        let mut memories = self.memories.write();
        let mut tag_index = self.tag_index.write();
        
        for tag in &memory.tags {
            tag_index
                .entry(tag.clone())
                .or_insert_with(Vec::new)
                .push(memory.id.clone());
        }
        
        memories.insert(memory.id.clone(), memory);
    }

    fn retrieve(&self, id: String) -> Option<MemoryV2> {
        let mut memories = self.memories.write();
        
        if let Some(mem) = memories.get_mut(&id) {
            mem.access_count += 1;
            Some(mem.clone())
        } else {
            None
        }
    }

    fn search_by_tag(&self, tag: String) -> Vec<MemoryV2> {
        let tag_index = self.tag_index.read();
        let memories = self.memories.read();
        
        if let Some(ids) = tag_index.get(&tag) {
            ids.iter()
                .filter_map(|id| memories.get(id).cloned())
                .collect()
        } else {
            Vec::new()
        }
    }

    fn search_by_content(&self, query: String) -> Vec<MemoryV2> {
        self.memories
            .read()
            .values()
            .filter(|m| m.content.contains(&query))
            .cloned()
            .collect()
    }

    fn update_importance(&self, id: String, importance: f64) -> bool {
        if let Some(mem) = self.memories.write().get_mut(&id) {
            mem.importance = importance;
            true
        } else {
            false
        }
    }

    fn delete(&self, id: String) -> bool {
        let mut memories = self.memories.write();
        let mut tag_index = self.tag_index.write();
        
        if let Some(memory) = memories.remove(&id) {
            for tag in &memory.tags {
                if let Some(ids) = tag_index.get_mut(tag) {
                    ids.retain(|i| i != &id);
                }
            }
            true
        } else {
            false
        }
    }

    fn count(&self) -> usize {
        self.memories.read().len()
    }

    fn get_all_tags(&self) -> Vec<String> {
        self.tag_index.read().keys().cloned().collect()
    }

    fn get_top_by_importance(&self, limit: usize) -> Vec<MemoryV2> {
        let mut memories: Vec<MemoryV2> = self.memories.read().values().cloned().collect();
        memories.sort_by(|a, b| b.importance.partial_cmp(&a.importance).unwrap());
        memories.truncate(limit);
        memories
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_store_and_retrieve() {
        let um = PyUnifiedMemoryV2::new();
        let mem = MemoryV2::new(
            "test1".to_string(),
            "content".to_string(),
            vec!["tag1".to_string()],
        );
        
        um.store(mem);
        let retrieved = um.retrieve("test1".to_string());
        
        assert!(retrieved.is_some());
    }

    #[test]
    fn test_search_by_tag() {
        let um = PyUnifiedMemoryV2::new();
        
        um.store(MemoryV2::new(
            "m1".to_string(),
            "content1".to_string(),
            vec!["tag1".to_string()],
        ));
        
        um.store(MemoryV2::new(
            "m2".to_string(),
            "content2".to_string(),
            vec!["tag1".to_string(), "tag2".to_string()],
        ));
        
        let results = um.search_by_tag("tag1".to_string());
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_delete() {
        let um = PyUnifiedMemoryV2::new();
        
        um.store(MemoryV2::new(
            "m1".to_string(),
            "content".to_string(),
            vec!["tag1".to_string()],
        ));
        
        assert_eq!(um.count(), 1);
        
        um.delete("m1".to_string());
        assert_eq!(um.count(), 0);
    }

    #[test]
    fn test_get_top_by_importance() {
        let um = PyUnifiedMemoryV2::new();
        
        let mut m1 = MemoryV2::new("m1".to_string(), "c1".to_string(), vec![]);
        m1.importance = 0.9;
        
        let mut m2 = MemoryV2::new("m2".to_string(), "c2".to_string(), vec![]);
        m2.importance = 0.5;
        
        um.store(m1);
        um.store(m2);
        
        let top = um.get_top_by_importance(1);
        assert_eq!(top.len(), 1);
        assert_eq!(top[0].id, "m1");
    }
}
