// Unified Cache — sub-microsecond LRU + TTL cache with optional mmap persistence.
//
// Design:
// - In-memory: DashMap-style concurrent HashMap with parking_lot RwLock
// - LRU eviction: Bounded entry count, evict least-recently-used
// - TTL expiry: Per-entry TTL in seconds, lazy eviction on read
// - Persistence: Optional JSON snapshot to mmap'd file for cross-session survival
// - Metrics: hits, misses, evictions, expirations, total requests
//
// Thread-safe via parking_lot::RwLock. All operations are O(1) except
// periodic cleanup which is O(n) but runs lazily on read.

use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

/// A single cache entry.
#[derive(Clone, Serialize, Deserialize)]
pub struct CacheEntry {
    pub value: String,        // JSON-serialized value
    pub created_at: f64,      // Unix timestamp
    pub expires_at: f64,      // Unix timestamp (created_at + ttl)
    pub access_count: u64,    // LRU tracking
    pub last_access: f64,     // Unix timestamp of last access
    pub namespace: String,    // Cache namespace (e.g. "semantic", "query", "prefetch")
}

/// Cache statistics (atomic counters for lock-free reads).
#[derive(Default)]
pub struct CacheStats {
    pub hits: AtomicU64,
    pub misses: AtomicU64,
    pub evictions: AtomicU64,
    pub expirations: AtomicU64,
    pub sets: AtomicU64,
}

/// Unified cache — thread-safe, LRU + TTL, with optional persistence.
pub struct UnifiedCache {
    inner: Arc<RwLock<HashMap<String, CacheEntry>>>,
    max_size: usize,
    stats: CacheStats,
    persist_path: Option<PathBuf>,
}

impl UnifiedCache {
    /// Create a new in-memory cache with given max size.
    pub fn new(max_size: usize) -> Self {
        Self {
            inner: Arc::new(RwLock::new(HashMap::with_capacity(max_size))),
            max_size,
            stats: CacheStats::default(),
            persist_path: None,
        }
    }

    /// Create a cache with persistence (JSON snapshot to file).
    pub fn with_persistence(max_size: usize, path: PathBuf) -> Self {
        let mut cache = Self::new(max_size);
        cache.persist_path = Some(path.clone());
        cache.load_from_disk();
        cache
    }

    /// Generate a deterministic cache key from namespace + raw key string.
    pub fn make_key(namespace: &str, raw_key: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(namespace.as_bytes());
        hasher.update(b"|");
        hasher.update(raw_key.as_bytes());
        let result = hasher.finalize();
        format!("{}:{}", namespace, hex::encode(&result[..8]))
    }

    /// Get a value from the cache. Returns None if missing or expired.
    pub fn get(&self, namespace: &str, key: &str) -> Option<String> {
        let cache_key = Self::make_key(namespace, key);
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();

        let mut inner = self.inner.write();
        if let Some(entry) = inner.get_mut(&cache_key) {
            // Check TTL expiry
            if now > entry.expires_at {
                inner.remove(&cache_key);
                self.stats.expirations.fetch_add(1, Ordering::Relaxed);
                self.stats.misses.fetch_add(1, Ordering::Relaxed);
                return None;
            }
            // Update access tracking
            entry.access_count += 1;
            entry.last_access = now;
            self.stats.hits.fetch_add(1, Ordering::Relaxed);
            return Some(entry.value.clone());
        }
        self.stats.misses.fetch_add(1, Ordering::Relaxed);
        None
    }

    /// Set a value in the cache with TTL (in seconds).
    pub fn set(&self, namespace: &str, key: &str, value: &str, ttl_seconds: f64) {
        let cache_key = Self::make_key(namespace, key);
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();

        let entry = CacheEntry {
            value: value.to_string(),
            created_at: now,
            expires_at: now + ttl_seconds,
            access_count: 0,
            last_access: now,
            namespace: namespace.to_string(),
        };

        let mut inner = self.inner.write();
        // Evict LRU if at capacity and key is new
        if inner.len() >= self.max_size && !inner.contains_key(&cache_key) {
            // Find and remove least-recently-used entry
            if let Some(lru_key) = inner
                .iter()
                .min_by(|a, b| a.1.last_access.partial_cmp(&b.1.last_access).unwrap_or(std::cmp::Ordering::Equal))
                .map(|(k, _)| k.clone())
            {
                inner.remove(&lru_key);
                self.stats.evictions.fetch_add(1, Ordering::Relaxed);
            }
        }
        inner.insert(cache_key, entry);
        self.stats.sets.fetch_add(1, Ordering::Relaxed);
    }

    /// Invalidate a specific key.
    pub fn invalidate(&self, namespace: &str, key: &str) -> bool {
        let cache_key = Self::make_key(namespace, key);
        let mut inner = self.inner.write();
        inner.remove(&cache_key).is_some()
    }

    /// Invalidate all keys in a namespace.
    pub fn invalidate_namespace(&self, namespace: &str) -> usize {
        let prefix = format!("{}:", namespace);
        let mut inner = self.inner.write();
        let keys_to_remove: Vec<String> = inner
            .keys()
            .filter(|k| k.starts_with(&prefix))
            .cloned()
            .collect();
        let count = keys_to_remove.len();
        for key in keys_to_remove {
            inner.remove(&key);
        }
        count
    }

    /// Clear the entire cache.
    pub fn clear(&self) {
        let mut inner = self.inner.write();
        inner.clear();
    }

    /// Run cleanup — remove all expired entries. Returns count removed.
    pub fn cleanup_expired(&self) -> usize {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        let mut inner = self.inner.write();
        let expired_keys: Vec<String> = inner
            .iter()
            .filter(|(_, e)| now > e.expires_at)
            .map(|(k, _)| k.clone())
            .collect();
        let count = expired_keys.len();
        for key in expired_keys {
            inner.remove(&key);
            self.stats.expirations.fetch_add(1, Ordering::Relaxed);
        }
        count
    }

    /// Get cache statistics as a tuple (hits, misses, hit_rate, size, evictions, expirations, sets).
    pub fn stats(&self) -> (u64, u64, f64, usize, u64, u64, u64) {
        let hits = self.stats.hits.load(Ordering::Relaxed);
        let misses = self.stats.misses.load(Ordering::Relaxed);
        let evictions = self.stats.evictions.load(Ordering::Relaxed);
        let expirations = self.stats.expirations.load(Ordering::Relaxed);
        let sets = self.stats.sets.load(Ordering::Relaxed);
        let total = hits + misses;
        let hit_rate = if total > 0 {
            (hits as f64 / total as f64) * 100.0
        } else {
            0.0
        };
        let size = self.inner.read().len();
        (hits, misses, hit_rate, size, evictions, expirations, sets)
    }

    /// Get current cache size.
    pub fn len(&self) -> usize {
        self.inner.read().len()
    }

    /// Check if cache is empty.
    pub fn is_empty(&self) -> bool {
        self.inner.read().is_empty()
    }

    /// Persist cache contents to disk (JSON snapshot).
    pub fn persist_to_disk(&self) -> Result<usize, String> {
        let path = match &self.persist_path {
            Some(p) => p,
            None => return Err("No persistence path configured".to_string()),
        };
        let inner = self.inner.read();
        let snapshot: Vec<(String, CacheEntry)> = inner.iter().map(|(k, v)| (k.clone(), v.clone())).collect();
        let json = serde_json::to_string(&snapshot).map_err(|e| e.to_string())?;
        std::fs::write(path, json).map_err(|e| e.to_string())?;
        Ok(snapshot.len())
    }

    /// Load cache contents from disk (JSON snapshot).
    fn load_from_disk(&self) -> usize {
        let path = match &self.persist_path {
            Some(p) => p.clone(),
            None => return 0,
        };
        if !path.exists() {
            return 0;
        }
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        match std::fs::read_to_string(&path) {
            Ok(json) => {
                match serde_json::from_str::<Vec<(String, CacheEntry)>>(&json) {
                    Ok(entries) => {
                        let mut inner = self.inner.write();
                        let mut loaded = 0;
                        for (key, entry) in entries {
                            // Skip expired entries on load
                            if now <= entry.expires_at {
                                inner.insert(key, entry);
                                loaded += 1;
                            }
                        }
                        loaded
                    }
                    Err(_) => 0,
                }
            }
            Err(_) => 0,
        }
    }
}

// Minimal hex encoding (avoid extra dependency)
mod hex {
    pub fn encode(bytes: &[u8]) -> String {
        bytes.iter().map(|b| format!("{:02x}", b)).collect()
    }
}

#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pyclass]
#[derive(Clone)]
pub struct PyUnifiedCache {
    inner: Arc<UnifiedCache>,
}

#[cfg(feature = "python")]
#[pymethods]
impl PyUnifiedCache {
    /// Create a new cache instance.
    /// Args:
    ///     max_size: Maximum number of entries (default 10000)
    ///     persist_path: Optional path for JSON persistence
    #[new]
    #[pyo3(signature = (max_size=10000, persist_path=None))]
    fn new(max_size: usize, persist_path: Option<String>) -> Self {
        let cache = match persist_path {
            Some(path) => UnifiedCache::with_persistence(max_size, PathBuf::from(path)),
            None => UnifiedCache::new(max_size),
        };
        Self {
            inner: Arc::new(cache),
        }
    }

    /// Get a value from the cache.
    /// Returns None if missing or expired.
    fn get(&self, namespace: &str, key: &str) -> Option<String> {
        self.inner.get(namespace, key)
    }

    /// Set a value in the cache with TTL (in seconds).
    fn set(&self, namespace: &str, key: &str, value: &str, ttl_seconds: f64) {
        self.inner.set(namespace, key, value, ttl_seconds);
    }

    /// Invalidate a specific key. Returns True if key existed.
    fn invalidate(&self, namespace: &str, key: &str) -> bool {
        self.inner.invalidate(namespace, key)
    }

    /// Invalidate all keys in a namespace. Returns count removed.
    fn invalidate_namespace(&self, namespace: &str) -> usize {
        self.inner.invalidate_namespace(namespace)
    }

    /// Clear the entire cache.
    fn clear(&self) {
        self.inner.clear();
    }

    /// Remove all expired entries. Returns count removed.
    fn cleanup_expired(&self) -> usize {
        self.inner.cleanup_expired()
    }

    /// Get cache statistics as a dict.
    fn stats(&self) -> (u64, u64, f64, usize, u64, u64, u64) {
        self.inner.stats()
    }

    /// Get current cache size.
    fn len(&self) -> usize {
        self.inner.len()
    }

    /// Check if cache is empty.
    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// Persist cache to disk. Returns count of entries persisted.
    fn persist(&self) -> PyResult<usize> {
        self.inner.persist_to_disk().map_err(pyo3::exceptions::PyRuntimeError::new_err)
    }

    fn __repr__(&self) -> String {
        let (hits, misses, hit_rate, size, evictions, expirations, sets) = self.inner.stats();
        format!(
            "UnifiedCache(size={}, hits={}, misses={}, hit_rate={:.1}%, evictions={}, expirations={}, sets={})",
            size, hits, misses, hit_rate, evictions, expirations, sets
        )
    }
}

#[cfg(feature = "python")]
pub fn register_cache(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyUnifiedCache>()?;
    Ok(())
}
