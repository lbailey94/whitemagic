//! Unified memory system for consolidated memory storage and retrieval
//!
//! This module provides a unified memory interface with capacity management,
//! LRU eviction, and efficient lookup operations.

#![allow(dead_code)]

use pyo3::prelude::*;
use std::collections::{HashMap, VecDeque};
use std::time::Instant;

/// Memory entry with metadata
#[derive(Debug, Clone)]
pub struct MemoryEntry {
    /// Unique identifier
    pub id: u64,
    /// Memory content
    pub content: String,
    /// Embedding vector (for similarity search)
    pub embedding: Option<Vec<f32>>,
    /// Access count
    pub access_count: u64,
    /// Last access time
    pub last_access: Instant,
    /// Creation time
    pub created: Instant,
    /// Tags
    pub tags: Vec<String>,
}

/// Unified memory system with capacity management
#[pyclass]
pub struct UnifiedMemory {
    /// Maximum capacity
    capacity: usize,
    /// Memory entries
    memories: HashMap<u64, MemoryEntry>,
    /// LRU queue for eviction
    lru_queue: VecDeque<u64>,
    /// Next ID counter
    next_id: u64,
    /// Total stored count
    total_stored: u64,
    /// Total evicted count
    total_evicted: u64,
}

#[pymethods]
impl UnifiedMemory {
    /// Create a new unified memory system with specified capacity
    #[new]
    fn new(capacity: usize) -> Self {
        Self {
            capacity,
            memories: HashMap::with_capacity(capacity),
            lru_queue: VecDeque::with_capacity(capacity),
            next_id: 1,
            total_stored: 0,
            total_evicted: 0,
        }
    }

    /// Store a new memory
    fn store(&mut self, content: String, tags: Vec<String>) -> u64 {
        // Evict if at capacity
        while self.memories.len() >= self.capacity {
            self.evict_lru();
        }

        let id = self.next_id;
        self.next_id += 1;
        self.total_stored += 1;

        let entry = MemoryEntry {
            id,
            content,
            embedding: None,
            access_count: 0,
            last_access: Instant::now(),
            created: Instant::now(),
            tags,
        };

        self.memories.insert(id, entry);
        self.lru_queue.push_back(id);

        id
    }

    /// Store with embedding
    fn store_with_embedding(
        &mut self,
        content: String,
        tags: Vec<String>,
        embedding: Vec<f32>,
    ) -> u64 {
        // Evict if at capacity
        while self.memories.len() >= self.capacity {
            self.evict_lru();
        }

        let id = self.next_id;
        self.next_id += 1;
        self.total_stored += 1;

        let entry = MemoryEntry {
            id,
            content,
            embedding: Some(embedding),
            access_count: 0,
            last_access: Instant::now(),
            created: Instant::now(),
            tags,
        };

        self.memories.insert(id, entry);
        self.lru_queue.push_back(id);

        id
    }

    /// Retrieve a memory by ID
    fn retrieve(&mut self, id: u64) -> Option<String> {
        if let Some(entry) = self.memories.get_mut(&id) {
            entry.access_count += 1;
            entry.last_access = Instant::now();

            // Move to end of LRU queue (most recently used)
            self.lru_queue.retain(|&x| x != id);
            self.lru_queue.push_back(id);

            Some(entry.content.clone())
        } else {
            None
        }
    }

    /// Get memory with full metadata
    fn get_entry(&mut self, id: u64) -> Option<PyObject> {
        Python::with_gil(|py| {
            if let Some(entry) = self.memories.get_mut(&id) {
                entry.access_count += 1;
                entry.last_access = Instant::now();

                let dict = pyo3::types::PyDict::new_bound(py);
                dict.set_item("id", entry.id).unwrap();
                dict.set_item("content", entry.content.clone()).unwrap();
                dict.set_item("access_count", entry.access_count).unwrap();
                dict.set_item("tags", entry.tags.clone()).unwrap();

                if let Some(ref emb) = entry.embedding {
                    dict.set_item("has_embedding", true).unwrap();
                    dict.set_item("embedding_dim", emb.len()).unwrap();
                } else {
                    dict.set_item("has_embedding", false).unwrap();
                }

                Some(dict.into())
            } else {
                None
            }
        })
    }

    /// Search memories by content (simple substring match)
    fn search(&self, query: String, limit: usize) -> Vec<u64> {
        let mut results: Vec<(u64, u64)> = self
            .memories
            .iter()
            .filter_map(|(id, entry)| {
                if entry.content.contains(&query) {
                    Some((*id, entry.access_count))
                } else {
                    None
                }
            })
            .collect();

        // Sort by access count (most accessed first)
        results.sort_by(|a, b| b.1.cmp(&a.1));
        results.truncate(limit);
        results.into_iter().map(|(id, _)| id).collect()
    }

    /// Search by tags
    fn search_by_tags(&self, tags: Vec<String>, limit: usize) -> Vec<u64> {
        let tag_set: std::collections::HashSet<&str> = tags.iter().map(|s| s.as_str()).collect();

        let mut results: Vec<(u64, usize)> = self
            .memories
            .iter()
            .filter_map(|(id, entry)| {
                let match_count = entry
                    .tags
                    .iter()
                    .filter(|t| tag_set.contains(t.as_str()))
                    .count();
                if match_count > 0 {
                    Some((*id, match_count))
                } else {
                    None
                }
            })
            .collect();

        // Sort by number of matching tags
        results.sort_by(|a, b| b.1.cmp(&a.1));
        results.truncate(limit);
        results.into_iter().map(|(id, _)| id).collect()
    }

    /// Find similar memories by embedding
    fn find_similar(&self, embedding: Vec<f32>, limit: usize) -> Vec<(u64, f32)> {
        let mut results: Vec<(u64, f32)> = self
            .memories
            .iter()
            .filter_map(|(id, entry)| {
                if let Some(ref entry_emb) = entry.embedding {
                    let sim = cosine_similarity(&embedding, entry_emb);
                    if sim > 0.0 {
                        Some((*id, sim))
                    } else {
                        None
                    }
                } else {
                    None
                }
            })
            .collect();

        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        results.truncate(limit);
        results
    }

    /// Delete a memory by ID
    fn delete(&mut self, id: u64) -> bool {
        if self.memories.remove(&id).is_some() {
            self.lru_queue.retain(|&x| x != id);
            true
        } else {
            false
        }
    }

    /// Clear all memories
    fn clear(&mut self) {
        self.memories.clear();
        self.lru_queue.clear();
    }

    /// Get current memory count
    fn len(&self) -> usize {
        self.memories.len()
    }

    /// Check if empty
    fn is_empty(&self) -> bool {
        self.memories.is_empty()
    }

    /// Get capacity
    fn get_capacity(&self) -> usize {
        self.capacity
    }

    /// Set capacity (may trigger eviction)
    fn set_capacity(&mut self, new_capacity: usize) {
        self.capacity = new_capacity;
        while self.memories.len() > self.capacity {
            self.evict_lru();
        }
    }

    /// Get statistics
    fn get_stats(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("capacity", self.capacity)?;
        dict.set_item("current_size", self.memories.len())?;
        dict.set_item("total_stored", self.total_stored)?;
        dict.set_item("total_evicted", self.total_evicted)?;
        dict.set_item(
            "utilization",
            self.memories.len() as f64 / self.capacity as f64,
        )?;
        Ok(dict.into())
    }

    /// Get all IDs
    fn get_all_ids(&self) -> Vec<u64> {
        self.memories.keys().copied().collect()
    }

    /// Get utilization percentage
    fn utilization(&self) -> f64 {
        self.memories.len() as f64 / self.capacity as f64
    }
}

impl UnifiedMemory {
    /// Evict least recently used memory
    fn evict_lru(&mut self) {
        if let Some(id) = self.lru_queue.pop_front() {
            self.memories.remove(&id);
            self.total_evicted += 1;
        }
    }
}

/// Compute cosine similarity between two vectors
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }

    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();

    let denom = norm_a * norm_b;
    if denom > 0.0 {
        dot / denom
    } else {
        0.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_memory_creation() {
        let memory = UnifiedMemory::new(100);
        assert_eq!(memory.get_capacity(), 100);
        assert!(memory.is_empty());
    }

    #[test]
    fn test_store_and_retrieve() {
        let mut memory = UnifiedMemory::new(100);
        let id = memory.store("test content".to_string(), vec!["test".to_string()]);

        let content = memory.retrieve(id);
        assert_eq!(content, Some("test content".to_string()));
    }

    #[test]
    fn test_eviction() {
        let mut memory = UnifiedMemory::new(3);

        memory.store("a".to_string(), vec![]);
        memory.store("b".to_string(), vec![]);
        memory.store("c".to_string(), vec![]);
        memory.store("d".to_string(), vec![]); // Should evict "a"

        assert_eq!(memory.len(), 3);
        assert_eq!(memory.total_evicted, 1);
    }

    #[test]
    fn test_search() {
        let mut memory = UnifiedMemory::new(100);
        memory.store("hello world".to_string(), vec!["greeting".to_string()]);
        memory.store("hello there".to_string(), vec!["greeting".to_string()]);
        memory.store("goodbye".to_string(), vec!["farewell".to_string()]);

        let results = memory.search("hello".to_string(), 10);
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_tag_search() {
        let mut memory = UnifiedMemory::new(100);
        memory.store(
            "doc1".to_string(),
            vec!["rust".to_string(), "code".to_string()],
        );
        memory.store(
            "doc2".to_string(),
            vec!["python".to_string(), "code".to_string()],
        );
        memory.store("doc3".to_string(), vec!["rust".to_string()]);

        let results = memory.search_by_tags(vec!["rust".to_string()], 10);
        assert_eq!(results.len(), 2);
    }
}
