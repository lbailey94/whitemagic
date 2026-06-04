//! Model Cache - ML Model Caching (PSR-008)
//! Target: 50× speedup for model loading

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct CachedModel {
    #[pyo3(get)]
    pub model_id: String,
    #[pyo3(get)]
    pub model_type: String,
    #[pyo3(get)]
    pub size_bytes: usize,
    #[pyo3(get)]
    pub access_count: usize,
}

#[pymethods]
impl CachedModel {
    #[new]
    fn new(model_id: String, model_type: String, size_bytes: usize) -> Self {
        Self {
            model_id,
            model_type,
            size_bytes,
            access_count: 0,
        }
    }
}

#[pyclass]
pub struct PyModelCache {
    cache: Arc<RwLock<HashMap<String, CachedModel>>>,
    max_size_bytes: usize,
    current_size: Arc<RwLock<usize>>,
}

#[pymethods]
impl PyModelCache {
    #[new]
    fn new(max_size_mb: usize) -> Self {
        Self {
            cache: Arc::new(RwLock::new(HashMap::new())),
            max_size_bytes: max_size_mb * 1024 * 1024,
            current_size: Arc::new(RwLock::new(0)),
        }
    }

    fn cache_model(&self, model: CachedModel) -> bool {
        let mut cache = self.cache.write();
        let mut current_size = self.current_size.write();

        if *current_size + model.size_bytes > self.max_size_bytes {
            self.evict_lru(&mut cache, &mut current_size, model.size_bytes);
        }

        if *current_size + model.size_bytes <= self.max_size_bytes {
            *current_size += model.size_bytes;
            cache.insert(model.model_id.clone(), model);
            true
        } else {
            false
        }
    }

    fn get_model(&self, model_id: String) -> Option<CachedModel> {
        let mut cache = self.cache.write();
        
        if let Some(model) = cache.get_mut(&model_id) {
            model.access_count += 1;
            Some(model.clone())
        } else {
            None
        }
    }

    fn remove_model(&self, model_id: String) -> bool {
        let mut cache = self.cache.write();
        let mut current_size = self.current_size.write();

        if let Some(model) = cache.remove(&model_id) {
            *current_size -= model.size_bytes;
            true
        } else {
            false
        }
    }

    fn clear(&self) {
        self.cache.write().clear();
        *self.current_size.write() = 0;
    }

    fn cache_size(&self) -> usize {
        self.cache.read().len()
    }

    fn current_size_mb(&self) -> f64 {
        *self.current_size.read() as f64 / (1024.0 * 1024.0)
    }
}

impl PyModelCache {
    fn evict_lru(&self, cache: &mut HashMap<String, CachedModel>, current_size: &mut usize, needed: usize) {
        while *current_size + needed > self.max_size_bytes && !cache.is_empty() {
            if let Some((id, model)) = cache
                .iter()
                .min_by_key(|(_, m)| m.access_count)
                .map(|(id, m)| (id.clone(), m.clone()))
            {
                *current_size -= model.size_bytes;
                cache.remove(&id);
            } else {
                break;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_creation() {
        let cache = PyModelCache::new(100);
        assert_eq!(cache.cache_size(), 0);
    }

    #[test]
    fn test_cache_model() {
        let cache = PyModelCache::new(100);
        let model = CachedModel::new("m1".to_string(), "bert".to_string(), 10 * 1024 * 1024);
        
        assert!(cache.cache_model(model));
        assert_eq!(cache.cache_size(), 1);
    }

    #[test]
    fn test_get_model() {
        let cache = PyModelCache::new(100);
        let model = CachedModel::new("m1".to_string(), "bert".to_string(), 10 * 1024 * 1024);
        
        cache.cache_model(model);
        
        let retrieved = cache.get_model("m1".to_string());
        assert!(retrieved.is_some());
    }

    #[test]
    fn test_eviction() {
        let cache = PyModelCache::new(20);
        
        cache.cache_model(CachedModel::new("m1".to_string(), "bert".to_string(), 15 * 1024 * 1024));
        cache.cache_model(CachedModel::new("m2".to_string(), "gpt".to_string(), 15 * 1024 * 1024));
        
        assert_eq!(cache.cache_size(), 1);
    }
}
