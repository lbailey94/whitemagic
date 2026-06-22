//! Memory Deduplication
//! Detects and removes duplicate memories

use pyo3::prelude::*;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::collections::hash_map::DefaultHasher;

#[pyclass]
pub struct MemoryDeduplication {
    content_hashes: HashMap<u64, String>,
    duplicates_found: usize,
}

#[pymethods]
impl MemoryDeduplication {
    #[new]
    fn new() -> Self {
        Self {
            content_hashes: HashMap::new(),
            duplicates_found: 0,
        }
    }
    
    fn calculate_hash(&self, content: &str) -> u64 {
        let mut hasher = DefaultHasher::new();
        content.hash(&mut hasher);
        hasher.finish()
    }
    
    fn check_duplicate(&mut self, memory_id: String, content: String) -> PyResult<bool> {
        let hash = self.calculate_hash(&content);
        
        if self.content_hashes.contains_key(&hash) {
            self.duplicates_found += 1;
            Ok(true)
        } else {
            self.content_hashes.insert(hash, memory_id);
            Ok(false)
        }
    }
    
    fn batch_deduplicate(
        &mut self,
        memories: Vec<(String, String)> // (id, content)
    ) -> PyResult<Vec<String>> {
        let mut unique_ids = Vec::new();
        
        for (id, content) in memories {
            if !self.check_duplicate(id.clone(), content)? {
                unique_ids.push(id);
            }
        }
        
        Ok(unique_ids)
    }
    
    fn find_similar(&self, content: String, threshold: f64) -> PyResult<Vec<String>> {
        // Simple similarity check based on length
        let target_len = content.len() as f64;
        
        let similar: Vec<String> = self.content_hashes
            .values()
            .filter(|id| {
                // Placeholder similarity - in real implementation use proper algorithm
                let similarity = 1.0 - (target_len - id.len() as f64).abs() / target_len.max(1.0);
                similarity >= threshold
            })
            .cloned()
            .collect();
        
        Ok(similar)
    }
    
    fn get_stats(&self) -> PyResult<(usize, usize)> {
        Ok((self.content_hashes.len(), self.duplicates_found))
    }
    
    fn clear(&mut self) -> PyResult<()> {
        self.content_hashes.clear();
        self.duplicates_found = 0;
        Ok(())
    }
}
