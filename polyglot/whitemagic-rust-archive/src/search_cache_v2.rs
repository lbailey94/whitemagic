//! Search Cache V2 - Enhanced Search Caching (PSR-002)
//! Target: 30× speedup for cached searches

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug)]
#[pyclass]
pub struct PySearchCacheV2 {
    cache: Arc<RwLock<HashMap<String, CacheEntry>>>,
    max_size: usize,
    ttl_seconds: u64,
}

#[derive(Clone, Debug)]
struct CacheEntry {
    results: Vec<String>,
    timestamp: f64,
    hit_count: usize,
}

#[pymethods]
impl PySearchCacheV2 {
    #[new]
    fn new(max_size: Option<usize>, ttl_seconds: Option<u64>) -> Self {
        Self {
            cache: Arc::new(RwLock::new(HashMap::new())),
            max_size: max_size.unwrap_or(1000),
            ttl_seconds: ttl_seconds.unwrap_or(3600),
        }
    }

    fn get(&mut self, query: String) -> PyResult<Option<Vec<String>>> {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();
        
        let mut cache = self.cache.write().unwrap();
        
        if let Some(entry) = cache.get_mut(&query) {
            if now - entry.timestamp < self.ttl_seconds as f64 {
                entry.hit_count += 1;
                return Ok(Some(entry.results.clone()));
            } else {
                cache.remove(&query);
            }
        }
        
        Ok(None)
    }

    fn set(&mut self, query: String, results: Vec<String>) -> PyResult<()> {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();
        
        let mut cache = self.cache.write().unwrap();
        
        if cache.len() >= self.max_size && !cache.contains_key(&query) {
            if let Some(lru_key) = self.find_lru_key(&cache) {
                cache.remove(&lru_key);
            }
        }
        
        cache.insert(query, CacheEntry {
            results,
            timestamp: now,
            hit_count: 0,
        });
        
        Ok(())
    }

    fn invalidate(&mut self, query: String) -> PyResult<bool> {
        let mut cache = self.cache.write().unwrap();
        Ok(cache.remove(&query).is_some())
    }

    fn clear(&mut self) -> PyResult<usize> {
        let mut cache = self.cache.write().unwrap();
        let count = cache.len();
        cache.clear();
        Ok(count)
    }

    fn get_stats(&self) -> PyResult<(usize, usize)> {
        let cache = self.cache.read().unwrap();
        let total_hits: usize = cache.values().map(|e| e.hit_count).sum();
        Ok((cache.len(), total_hits))
    }
}

impl PySearchCacheV2 {
    fn find_lru_key(&self, cache: &HashMap<String, CacheEntry>) -> Option<String> {
        cache.iter()
            .min_by_key(|(_, entry)| (entry.hit_count, entry.timestamp as u64))
            .map(|(key, _)| key.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_set_get() {
        let mut cache = PySearchCacheV2::new(None, None);
        let results = vec!["result1".to_string(), "result2".to_string()];
        
        cache.set("query".to_string(), results.clone()).unwrap();
        let cached = cache.get("query".to_string()).unwrap();
        
        assert_eq!(cached, Some(results));
    }

    #[test]
    fn test_cache_invalidate() {
        let mut cache = PySearchCacheV2::new(None, None);
        cache.set("query".to_string(), vec!["result".to_string()]).unwrap();
        
        assert!(cache.invalidate("query".to_string()).unwrap());
        assert_eq!(cache.get("query".to_string()).unwrap(), None);
    }
}
