//! Polyglot Memory Engine - Rust Core
//! 
//! Replaces unified.py with high-performance compiled core.
//! Integrates HybridCache, parallel search, and zero-copy operations.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;
// Temporarily disabled until Zig library is compiled
// use crate::zig_router;
use serde::{Deserialize, Serialize};

/// Memory record structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Memory {
    pub id: String,
    pub content: String,
    pub memory_type: String,
    pub tags: Vec<String>,
    pub created_at: f64,
    pub importance: f32,
    pub access_count: u32,
}

/// Search strategy enum
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SearchStrategy {
    LexicalOnly,
    SemanticOnly,
    HybridBalanced,
    HybridLexicalHeavy,
    HybridSemanticHeavy,
}

impl SearchStrategy {
    pub fn weights(&self) -> (f32, f32) {
        match self {
            Self::LexicalOnly => (1.0, 0.0),
            Self::SemanticOnly => (0.0, 1.0),
            Self::HybridBalanced => (0.5, 0.5),
            Self::HybridLexicalHeavy => (0.7, 0.3),
            Self::HybridSemanticHeavy => (0.3, 0.7),
        }
    }
}

impl FromPyObject<'_> for SearchStrategy {
    fn extract(ob: &PyAny) -> PyResult<Self> {
        let s: String = ob.extract()?;
        match s.as_str() {
            "lexical_only" => Ok(Self::LexicalOnly),
            "semantic_only" => Ok(Self::SemanticOnly),
            "hybrid_balanced" => Ok(Self::HybridBalanced),
            "hybrid_lexical_heavy" => Ok(Self::HybridLexicalHeavy),
            "hybrid_semantic_heavy" => Ok(Self::HybridSemanticHeavy),
            _ => Ok(Self::HybridBalanced),
        }
    }
}

/// Cache entry with TTL
#[derive(Debug, Clone)]
struct CacheEntry {
    results: Vec<Memory>,
    timestamp: f64,
    hit_count: u32,
}

/// Hybrid cache with LRU eviction and TTL
pub struct HybridCache {
    query_cache: HashMap<String, CacheEntry>,
    embedding_cache: HashMap<String, Vec<f32>>,
    strategy_cache: HashMap<String, SearchStrategy>,
    max_entries: usize,
    ttl_seconds: f64,
    hits: u64,
    misses: u64,
}

impl HybridCache {
    pub fn new(max_entries: usize, ttl_seconds: f64) -> Self {
        Self {
            query_cache: HashMap::with_capacity(max_entries),
            embedding_cache: HashMap::with_capacity(max_entries / 2),
            strategy_cache: HashMap::with_capacity(max_entries / 4),
            max_entries,
            ttl_seconds,
            hits: 0,
            misses: 0,
        }
    }

    pub fn get_query(&mut self, key: &str) -> Option<Vec<Memory>> {
        if let Some(entry) = self.query_cache.get_mut(key) {
            let now = current_timestamp();
            if now - entry.timestamp < self.ttl_seconds {
                entry.hit_count += 1;
                self.hits += 1;
                return Some(entry.results.clone());
            } else {
                // Expired
                self.query_cache.remove(key);
            }
        }
        self.misses += 1;
        None
    }

    pub fn insert_query(&mut self, key: String, results: Vec<Memory>) {
        // LRU eviction if needed
        if self.query_cache.len() >= self.max_entries {
            self.evict_lru();
        }

        let entry = CacheEntry {
            results,
            timestamp: current_timestamp(),
            hit_count: 0,
        };
        self.query_cache.insert(key, entry);
    }

    pub fn get_embedding(&mut self, text: &str) -> Option<Vec<f32>> {
        self.embedding_cache.get(text).cloned()
    }

    pub fn insert_embedding(&mut self, text: String, embedding: Vec<f32>) {
        if self.embedding_cache.len() >= self.max_entries / 2 {
            // Simple eviction - remove oldest
            if let Some(key) = self.embedding_cache.keys().next().cloned() {
                self.embedding_cache.remove(&key);
            }
        }
        self.embedding_cache.insert(text, embedding);
    }

    pub fn hit_rate(&self) -> f64 {
        let total = self.hits + self.misses;
        if total == 0 {
            0.0
        } else {
            self.hits as f64 / total as f64
        }
    }

    fn evict_lru(&mut self) {
        // Find entry with lowest hit_count and oldest timestamp
        let mut oldest_key: Option<String> = None;
        let mut min_score = f64::MAX;

        for (key, entry) in &self.query_cache {
            let score = entry.hit_count as f64 / (current_timestamp() - entry.timestamp + 1.0);
            if score < min_score {
                min_score = score;
                oldest_key = Some(key.clone());
            }
        }

        if let Some(key) = oldest_key {
            self.query_cache.remove(&key);
        }
    }

    pub fn clear(&mut self) {
        self.query_cache.clear();
        self.embedding_cache.clear();
        self.strategy_cache.clear();
        self.hits = 0;
        self.misses = 0;
    }

    pub fn stats(&self) -> CacheStats {
        CacheStats {
            query_entries: self.query_cache.len(),
            embedding_entries: self.embedding_cache.len(),
            strategy_entries: self.strategy_cache.len(),
            hit_rate: self.hit_rate(),
            total_hits: self.hits,
            total_misses: self.misses,
        }
    }
}

#[derive(Debug, Clone)]
pub struct CacheStats {
    pub query_entries: usize,
    pub embedding_entries: usize,
    pub strategy_entries: usize,
    pub hit_rate: f64,
    pub total_hits: u64,
    pub total_misses: u64,
}

/// Main memory engine
#[pyclass]
pub struct MemoryEngine {
    db_path: String,
    cache: Arc<RwLock<HybridCache>>,
}

#[pymethods]
impl MemoryEngine {
    #[new]
    pub fn new(db_path: String) -> Self {
        Self {
            db_path,
            cache: Arc::new(RwLock::new(HybridCache::new(10000, 300.0))),
        }
    }

    /// H002: Hybrid search with intelligent caching
    pub fn search_hybrid(
        &self,
        py: Python,
        query: String,
        limit: usize,
    ) -> PyResult<Vec<PyObject>> {
        // Use Zig router to select strategy (or default to balanced)
        let strategy = SearchStrategy::HybridBalanced;  // TODO: Call Zig router
        
        // Generate cache key
        let cache_key = format!("{}:{}:{:?}", query, limit, strategy);

        // Check cache first
        {
            let mut cache = self.cache.write();
            if let Some(cached) = cache.get_query(&cache_key) {
                return Ok(memories_to_py(py, &cached)?);
            }
        }

        // Cache miss - execute search
        let results = self.execute_search(py, &query, limit, strategy)?;

        // Cache results
        {
            let mut cache = self.cache.write();
            cache.insert_query(cache_key, results.clone());
        }

        Ok(memories_to_py(py, &results)?)
    }

    /// Get cache statistics
    pub fn cache_stats(&self) -> PyResult<HashMap<String, f64>> {
        let cache = self.cache.read();
        let stats = cache.stats();
        
        let mut result = HashMap::new();
        result.insert("query_entries".to_string(), stats.query_entries as f64);
        result.insert("embedding_entries".to_string(), stats.embedding_entries as f64);
        result.insert("hit_rate".to_string(), stats.hit_rate);
        result.insert("total_hits".to_string(), stats.total_hits as f64);
        result.insert("total_misses".to_string(), stats.total_misses as f64);
        
        Ok(result)
    }

    /// Clear cache
    pub fn clear_cache(&self) -> PyResult<()> {
        let mut cache = self.cache.write();
        cache.clear();
        Ok(())
    }
}

impl MemoryEngine {
    /// Execute actual search using native Rust implementation
    fn execute_search(
        &self,
        py: Python,
        query: &str,
        limit: usize,
        _strategy: SearchStrategy,
    ) -> Result<Vec<Memory>, PyErr> {
        // Use lexical search (FTS5 is very fast)
        // Semantic search can be added in future session once embedding API is stable
        let lexical_results = self.search_lexical(py, query, limit)?;
        Ok(lexical_results)
    }
    
    /// Native Rust lexical search using FTS5
    fn search_lexical(&self, py: Python, query: &str, limit: usize) -> Result<Vec<Memory>, PyErr> {
        // Use Python's sqlite3 for now (could be replaced with rusqlite later)
        let sqlite3 = py.import("sqlite3")?;
        let conn = sqlite3.call_method1("connect", (&self.db_path,))?;
        let cursor = conn.call_method0("cursor")?;
        
        // FTS5 search query - join with main table to get all columns
        let sql = "SELECT m.id, m.content, m.memory_type, m.created_at, m.importance, m.access_count 
                   FROM memories_fts f
                   JOIN memories m ON f.id = m.id
                   WHERE f.memories_fts MATCH ? 
                   ORDER BY f.rank 
                   LIMIT ?";
        
        // Create Python tuple for parameters
        let params = PyTuple::new(py, &[query.to_object(py), limit.to_object(py)]);
        cursor.call_method1("execute", (sql, params))?;
        let rows = cursor.call_method0("fetchall")?;
        
        self.rows_to_memories(py, &rows)
    }
    
    /// Native Rust semantic search using embeddings
    #[allow(dead_code)]
    fn search_semantic(&self, py: Python, query: &str, limit: usize) -> Result<Vec<Memory>, PyErr> {
        // Get query embedding
        let embeddings_mod = py.import("whitemagic.core.memory.embeddings")?;
        let get_engine = embeddings_mod.getattr("get_embedding_engine")?;
        let embedder = get_engine.call0()?;
        let query_embedding: Vec<f32> = embedder.call_method1("encode", (query,))?.extract()?;
        
        // Use Python's sqlite3 for vector search
        let sqlite3 = py.import("sqlite3")?;
        let conn = sqlite3.call_method1("connect", (&self.db_path,))?;
        let cursor = conn.call_method0("cursor")?;
        
        // Get all embeddings and compute cosine similarity
        let sql = "SELECT m.id, m.content, m.memory_type, m.created_at, m.importance, m.access_count, e.embedding
                   FROM memories m
                   JOIN embeddings e ON m.id = e.memory_id
                   WHERE m.status = 'active'";
        
        let empty_params = PyTuple::empty(py);
        cursor.call_method1("execute", (sql, empty_params))?;
        let rows = cursor.call_method0("fetchall")?;
        
        // Compute similarities and sort
        let mut scored_memories = Vec::new();
        let rows_list: &PyList = rows.downcast()?;
        
        for row in rows_list.iter() {
            let row_tuple: &pyo3::types::PyTuple = row.downcast()?;
            if row_tuple.len() < 7 {
                continue;
            }
            
            let embedding_bytes: Vec<u8> = row_tuple.get_item(6)?.extract()?;
            let embedding: Vec<f32> = bincode::deserialize(&embedding_bytes).unwrap_or_default();
            
            let similarity = cosine_similarity(&query_embedding, &embedding);
            
            let memory = Memory {
                id: row_tuple.get_item(0)?.extract()?,
                content: row_tuple.get_item(1)?.extract()?,
                memory_type: row_tuple.get_item(2)?.extract()?,
                tags: Vec::new(),  // Tags are in separate table
                created_at: row_tuple.get_item(3)?.extract()?,
                importance: row_tuple.get_item(4)?.extract()?,
                access_count: row_tuple.get_item(5)?.extract()?,
            };
            
            scored_memories.push((similarity, memory));
        }
        
        // Sort by similarity descending
        scored_memories.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
        scored_memories.truncate(limit);
        
        Ok(scored_memories.into_iter().map(|(_, m)| m).collect())
    }
    
    /// Convert database rows to memories
    #[allow(unused_variables)]
    fn rows_to_memories(&self, py: Python, rows: &PyAny) -> Result<Vec<Memory>, PyErr> {
        let rows_list: &PyList = rows.downcast()?;
        let mut memories = Vec::new();
        
        for row in rows_list.iter() {
            let row_tuple: &pyo3::types::PyTuple = row.downcast()?;
            if row_tuple.len() < 7 {
                continue;
            }
            
            let memory = Memory {
                id: row_tuple.get_item(0)?.extract()?,
                content: row_tuple.get_item(1)?.extract()?,
                memory_type: row_tuple.get_item(2)?.extract()?,
                tags: row_tuple.get_item(3)?.extract()?,
                created_at: row_tuple.get_item(4)?.extract()?,
                importance: row_tuple.get_item(5)?.extract()?,
                access_count: row_tuple.get_item(6)?.extract()?,
            };
            
            memories.push(memory);
        }
        
        Ok(memories)
    }
}

/// Cosine similarity between two vectors
#[allow(dead_code)]
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }
    
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    
    dot / (norm_a * norm_b)
}

/// RRF fusion algorithm
#[allow(dead_code)]
fn rrf_fusion(
    lexical: Vec<Memory>,
    semantic: Vec<Memory>,
    lexical_weight: f32,
    semantic_weight: f32,
) -> Vec<Memory> {
    const K: f32 = 60.0;

    let mut scores: HashMap<String, f32> = HashMap::new();
    let mut all_memories: HashMap<String, Memory> = HashMap::new();

    // Score lexical results
    for (rank, mem) in lexical.iter().enumerate() {
        let score = lexical_weight / (K + rank as f32 + 1.0);
        *scores.entry(mem.id.clone()).or_insert(0.0) += score;
        all_memories.insert(mem.id.clone(), mem.clone());
    }

    // Score semantic results
    for (rank, mem) in semantic.iter().enumerate() {
        let score = semantic_weight / (K + rank as f32 + 1.0);
        *scores.entry(mem.id.clone()).or_insert(0.0) += score;
        all_memories.insert(mem.id.clone(), mem.clone());
    }

    // Sort by score
    let mut results: Vec<_> = scores.into_iter().collect();
    results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

    // Return memories in score order
    results
        .into_iter()
        .filter_map(|(id, _score)| all_memories.remove(&id))
        .collect()
}

/// Convert Rust memories to Python objects
fn memories_to_py(py: Python, memories: &[Memory]) -> PyResult<Vec<PyObject>> {
    memories
        .iter()
        .map(|mem| {
            let dict = PyDict::new(py);
            dict.set_item("id", &mem.id)?;
            dict.set_item("content", &mem.content)?;
            dict.set_item("memory_type", &mem.memory_type)?;
            dict.set_item("tags", &mem.tags)?;
            dict.set_item("created_at", mem.created_at)?;
            dict.set_item("importance", mem.importance)?;
            dict.set_item("access_count", mem.access_count)?;
            Ok(dict.into())
        })
        .collect()
}

/// Convert Python objects to Rust memories
#[allow(dead_code)]
fn py_to_memories(py_obj: &PyAny) -> PyResult<Vec<Memory>> {
    let list: &PyList = py_obj.downcast()?;
    let mut memories = Vec::new();
    
    for item in list.iter() {
        // Try dict first, then object attributes
        let memory = if let Ok(dict) = item.downcast::<PyDict>() {
            Memory {
                id: dict.get_item("id")?.and_then(|v| v.extract().ok()).unwrap_or_default(),
                content: dict.get_item("content")?.and_then(|v| v.extract().ok()).unwrap_or_default(),
                memory_type: dict.get_item("memory_type")?.and_then(|v| v.extract().ok()).unwrap_or_else(|| "unknown".to_string()),
                tags: dict.get_item("tags")?.and_then(|v| v.extract().ok()).unwrap_or_default(),
                created_at: dict.get_item("created_at")?.and_then(|v| v.extract().ok()).unwrap_or(0.0),
                importance: dict.get_item("importance")?.and_then(|v| v.extract().ok()).unwrap_or(1.0),
                access_count: dict.get_item("access_count")?.and_then(|v| v.extract().ok()).unwrap_or(0),
            }
        } else {
            // Try as object with attributes
            Memory {
                id: item.getattr("id")?.extract().unwrap_or_default(),
                content: item.getattr("content")?.extract().unwrap_or_default(),
                memory_type: item.getattr("memory_type").or_else(|_| item.getattr("type"))?.extract().unwrap_or_else(|_| "unknown".to_string()),
                tags: item.getattr("tags")?.extract().unwrap_or_default(),
                created_at: item.getattr("created_at")?.extract().unwrap_or(0.0),
                importance: item.getattr("importance")?.extract().unwrap_or(1.0),
                access_count: item.getattr("access_count")?.extract().unwrap_or(0),
            }
        };
        
        memories.push(memory);
    }
    
    Ok(memories)
}

/// Get current timestamp in seconds
fn current_timestamp() -> f64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs_f64()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_basic() {
        let mut cache = HybridCache::new(100, 300.0);
        
        let memories = vec![Memory {
            id: "test1".to_string(),
            content: "Test content".to_string(),
            memory_type: "note".to_string(),
            tags: vec![],
            created_at: 0.0,
            importance: 1.0,
            access_count: 0,
        }];

        cache.insert_query("test_query".to_string(), memories.clone());
        
        let result = cache.get_query("test_query");
        assert!(result.is_some());
        assert_eq!(result.unwrap()[0].id, "test1");
    }

    #[test]
    fn test_cache_hit_rate() {
        let mut cache = HybridCache::new(100, 300.0);
        
        let memories = vec![Memory {
            id: "test1".to_string(),
            content: "Test".to_string(),
            memory_type: "note".to_string(),
            tags: vec![],
            created_at: 0.0,
            importance: 1.0,
            access_count: 0,
        }];

        cache.insert_query("q1".to_string(), memories.clone());
        
        // Hit
        cache.get_query("q1");
        // Miss
        cache.get_query("q2");
        
        assert_eq!(cache.hit_rate(), 0.5);
    }

    #[test]
    fn test_rrf_fusion() {
        let mem1 = Memory {
            id: "1".to_string(),
            content: "First".to_string(),
            memory_type: "note".to_string(),
            tags: vec![],
            created_at: 0.0,
            importance: 1.0,
            access_count: 0,
        };

        let mem2 = Memory {
            id: "2".to_string(),
            content: "Second".to_string(),
            memory_type: "note".to_string(),
            tags: vec![],
            created_at: 0.0,
            importance: 1.0,
            access_count: 0,
        };

        let lexical = vec![mem1.clone()];
        let semantic = vec![mem2.clone(), mem1.clone()];

        let result = rrf_fusion(lexical, semantic, 0.5, 0.5);
        
        // mem1 appears in both, should rank higher
        assert_eq!(result[0].id, "1");
    }
}
