//! Search Cache - Multi-level Result Caching (PSR-002)
//! Target: 50× speedup for repeated queries

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug)]
struct CacheEntry {
    results: Vec<String>,
    timestamp: u64,
    hit_count: usize,
}

#[pyclass]
pub struct PySearchCache {
    cache: Arc<RwLock<HashMap<String, CacheEntry>>>,
    max_size: usize,
    ttl_seconds: u64,
}

#[pymethods]
impl PySearchCache {
    #[new]
    fn new(max_size: Option<usize>, ttl_seconds: Option<u64>) -> Self {
        Self {
            cache: Arc::new(RwLock::new(HashMap::new())),
            max_size: max_size.unwrap_or(1000),
            ttl_seconds: ttl_seconds.unwrap_or(3600),
        }
    }

    fn get(&self, query: String) -> Option<Vec<String>> {
        let mut cache = self.cache.write();
        
        if let Some(entry) = cache.get_mut(&query) {
            let now = Self::current_timestamp();
            
            // Check if entry is expired
            if now - entry.timestamp > self.ttl_seconds {
                cache.remove(&query);
                return None;
            }
            
            // Update hit count
            entry.hit_count += 1;
            return Some(entry.results.clone());
        }
        
        None
    }

    fn put(&self, query: String, results: Vec<String>) {
        let mut cache = self.cache.write();
        
        // Evict if at capacity
        if cache.len() >= self.max_size && !cache.contains_key(&query) {
            self.evict_lru(&mut cache);
        }
        
        let entry = CacheEntry {
            results,
            timestamp: Self::current_timestamp(),
            hit_count: 0,
        };
        
        cache.insert(query, entry);
    }

    fn invalidate(&self, query: String) -> bool {
        self.cache.write().remove(&query).is_some()
    }

    fn clear(&self) {
        self.cache.write().clear();
    }

    fn size(&self) -> usize {
        self.cache.read().len()
    }

    fn hit_rate(&self) -> f64 {
        let cache = self.cache.read();
        if cache.is_empty() {
            return 0.0;
        }
        
        let total_hits: usize = cache.values().map(|e| e.hit_count).sum();
        let total_entries = cache.len();
        
        total_hits as f64 / total_entries as f64
    }

    fn stats(&self) -> HashMap<String, usize> {
        let cache = self.cache.read();
        let mut stats = HashMap::new();
        
        stats.insert("size".to_string(), cache.len());
        stats.insert("max_size".to_string(), self.max_size);
        
        let total_hits: usize = cache.values().map(|e| e.hit_count).sum();
        stats.insert("total_hits".to_string(), total_hits);
        
        stats
    }
}

impl PySearchCache {
    fn current_timestamp() -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs()
    }

    fn evict_lru(&self, cache: &mut HashMap<String, CacheEntry>) {
        // Find entry with oldest timestamp and lowest hit count
        if let Some((key, _)) = cache
            .iter()
            .min_by_key(|(_, entry)| (entry.hit_count, entry.timestamp))
        {
            let key = key.clone();
            cache.remove(&key);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_put_get() {
        let cache = PySearchCache::new(Some(10), Some(3600));
        
        let results = vec!["doc1".to_string(), "doc2".to_string()];
        cache.put("test query".to_string(), results.clone());
        
        let retrieved = cache.get("test query".to_string());
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap(), results);
    }

    #[test]
    fn test_cache_miss() {
        let cache = PySearchCache::new(Some(10), Some(3600));
        
        let result = cache.get("nonexistent".to_string());
        assert!(result.is_none());
    }

    #[test]
    fn test_cache_invalidate() {
        let cache = PySearchCache::new(Some(10), Some(3600));
        
        cache.put("test".to_string(), vec!["doc1".to_string()]);
        assert_eq!(cache.size(), 1);
        
        cache.invalidate("test".to_string());
        assert_eq!(cache.size(), 0);
    }

    #[test]
    fn test_cache_eviction() {
        let cache = PySearchCache::new(Some(2), Some(3600));
        
        cache.put("query1".to_string(), vec!["doc1".to_string()]);
        cache.put("query2".to_string(), vec!["doc2".to_string()]);
        cache.put("query3".to_string(), vec!["doc3".to_string()]);
        
        assert_eq!(cache.size(), 2);
    }

    #[test]
    fn test_hit_count() {
        let cache = PySearchCache::new(Some(10), Some(3600));
        
        cache.put("test".to_string(), vec!["doc1".to_string()]);
        cache.get("test".to_string());
        cache.get("test".to_string());
        
        let stats = cache.stats();
        assert_eq!(*stats.get("total_hits").unwrap(), 2);
    }
}
