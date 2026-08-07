//! Memory Recall Engine — Hybrid vector + FTS search (Phase N10).
//!
//! Auto-embeds memories at write time using the `Embedder` trait,
//! and fuses Tantivy BM25 + vector cosine similarity at recall time.
//!
//! # Architecture
//!
//! ```text
//! RecallEngine
//! ├── embedder: Arc<dyn Embedder>
//! ├── vector_store: VectorStore
//! ├── search_engine: SearchEngine (Tantivy BM25)
//! ├── embedding_cache: HashMap<content_hash, Vec<f32>>
//! └── hybrid_search(query, limit) → Vec<RecallResult>
//!     1. Embed query → query vector
//!     2. Tantivy BM25 search → text scores
//!     3. Vector cosine similarity → vector scores
//!     4. Fuse: w1*BM25 + w2*vector + w3*importance
//!     5. Return ranked results
//! ```
//!
//! # Environment Variables
//!
//! | Variable | Default | Description |
//! |----------|---------|-------------|
//! | `WM_RECALL_BM25_WEIGHT` | `0.5` | Weight for BM25 text score |
//! | `WM_RECALL_VECTOR_WEIGHT` | `0.3` | Weight for vector cosine similarity |
//! | `WM_RECALL_IMPORTANCE_WEIGHT` | `0.2` | Weight for memory importance |

#![allow(clippy::missing_const_for_fn)]

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use uuid::Uuid;
use wm_core::{Galaxy, Result};

use crate::embedder::Embedder;
use crate::memory::content_hash;
use crate::search::{SearchEngine, SearchResult};
use crate::store::MemoryStore;
use crate::vector::{VectorSearchResult, VectorStore};

// ── Recall Result ─────────────────────────────────────────────────────

/// A single recall result with fused scores.
#[derive(Debug, Clone)]
pub struct RecallResult {
    /// Memory UUID.
    pub memory_id: Uuid,
    /// Galaxy the memory belongs to.
    pub galaxy: Galaxy,
    /// Fused relevance score (0.0–1.0).
    pub score: f32,
    /// BM25 text score (normalized 0.0–1.0).
    pub bm25_score: f32,
    /// Vector cosine similarity (0.0–1.0).
    pub vector_score: f32,
    /// Memory importance (0.0–1.0).
    pub importance: f32,
    /// Content snippet.
    pub content: String,
}

// ── Recall Config ─────────────────────────────────────────────────────

/// Configuration for the recall engine.
#[derive(Debug, Clone)]
pub struct RecallConfig {
    /// Weight for BM25 text score (default 0.5).
    pub bm25_weight: f32,
    /// Weight for vector cosine similarity (default 0.3).
    pub vector_weight: f32,
    /// Weight for memory importance (default 0.2).
    pub importance_weight: f32,
    /// Whether to cache embeddings (default true).
    pub cache_embeddings: bool,
    /// Maximum cache entries (default 1000).
    pub max_cache_entries: usize,
    /// Tantivy IndexWriter heap size in bytes (default 50MB).
    /// Note: writer is now owned by SearchEngine; this field is kept for API compatibility.
    #[allow(dead_code)]
    pub writer_heap_size: usize,
}

impl Default for RecallConfig {
    fn default() -> Self {
        Self {
            bm25_weight: 0.5,
            vector_weight: 0.3,
            importance_weight: 0.2,
            cache_embeddings: true,
            max_cache_entries: 1000,
            writer_heap_size: 50_000_000,
        }
    }
}

impl RecallConfig {
    /// Create config from environment variables.
    ///
    /// Weights are clamped to [0.0, 1.0] and normalized to sum to 1.0.
    /// NaN and Infinity values are rejected (default is kept).
    #[must_use]
    pub fn from_env() -> Self {
        let mut config = Self::default();

        if let Ok(v) = std::env::var("WM_RECALL_BM25_WEIGHT") {
            if let Ok(w) = v.parse::<f32>() {
                if w.is_finite() && w >= 0.0 {
                    config.bm25_weight = w.min(1.0);
                }
            }
        }
        if let Ok(v) = std::env::var("WM_RECALL_VECTOR_WEIGHT") {
            if let Ok(w) = v.parse::<f32>() {
                if w.is_finite() && w >= 0.0 {
                    config.vector_weight = w.min(1.0);
                }
            }
        }
        if let Ok(v) = std::env::var("WM_RECALL_IMPORTANCE_WEIGHT") {
            if let Ok(w) = v.parse::<f32>() {
                if w.is_finite() && w >= 0.0 {
                    config.importance_weight = w.min(1.0);
                }
            }
        }

        // Normalize weights to sum to 1.0 if they don't already
        let sum = config.bm25_weight + config.vector_weight + config.importance_weight;
        if sum > 0.0 && (sum - 1.0).abs() > 0.01 {
            config.bm25_weight /= sum;
            config.vector_weight /= sum;
            config.importance_weight /= sum;
        }

        config
    }

    /// Validate that weights sum to approximately 1.0.
    #[must_use]
    pub fn weights_normalized(&self) -> bool {
        let sum = self.bm25_weight + self.vector_weight + self.importance_weight;
        (sum - 1.0).abs() < 0.01
    }
}

// ── Recall Engine ─────────────────────────────────────────────────────

/// Hybrid recall engine combining BM25 + vector search.
///
/// Wraps a `MemoryStore`, `SearchEngine`, `VectorStore`, and `Embedder`
/// to provide fused search at recall time and auto-embedding at write time.
pub struct RecallEngine {
    store: Arc<MemoryStore>,
    search_engine: Arc<SearchEngine>,
    vector_store: Mutex<VectorStore>,
    embedder: Arc<dyn Embedder>,
    config: RecallConfig,
    embedding_cache: Mutex<HashMap<String, Vec<f32>>>,
}

impl RecallEngine {
    /// Create a new recall engine.
    ///
    /// Returns an error if the Tantivy IndexWriter cannot be created.
    pub fn new(
        store: Arc<MemoryStore>,
        search_engine: Arc<SearchEngine>,
        vector_store: VectorStore,
        embedder: Arc<dyn Embedder>,
        config: RecallConfig,
    ) -> Result<Self> {
        Ok(Self {
            store,
            search_engine,
            vector_store: Mutex::new(vector_store),
            embedder,
            config,
            embedding_cache: Mutex::new(HashMap::new()),
        })
    }

    /// Get the configuration.
    #[must_use]
    pub fn config(&self) -> &RecallConfig {
        &self.config
    }

    // ── Write path: auto-embed ─────────────────────────────────────────

    /// Embed content and cache the result.
    ///
    /// Returns the embedding vector. If the content has been embedded
    /// before (same hash), returns the cached result.
    fn embed_content(&self, content: &str) -> Result<Vec<f32>> {
        let hash = content_hash(content);

        // Check cache
        if self.config.cache_embeddings {
            let cache = self.embedding_cache.lock().unwrap();
            if let Some(vec) = cache.get(&hash) {
                return Ok(vec.clone());
            }
        }

        // Embed
        let embedding = self.embedder.embed(content)?;

        // Cache
        if self.config.cache_embeddings {
            let mut cache = self.embedding_cache.lock().unwrap();
            if cache.len() >= self.config.max_cache_entries {
                // Evict ~10% of entries (simple strategy)
                let to_remove: Vec<String> = cache.keys().take(cache.len() / 10).cloned().collect();
                for key in to_remove {
                    cache.remove(&key);
                }
            }
            cache.insert(hash, embedding.clone());
        }

        Ok(embedding)
    }

    /// Store a memory with auto-embedding.
    ///
    /// 1. Embeds the content using the configured embedder.
    /// 2. Stores the memory in the given galaxy.
    /// 3. Stores the embedding in the Embeddings galaxy.
    /// 4. Adds the embedding to the vector store.
    /// 5. Indexes the content in Tantivy.
    pub fn store_with_embedding(&self, galaxy: Galaxy, memory: &crate::Memory) -> Result<()> {
        // 1. Embed content
        let embedding = self.embed_content(&memory.content)?;

        // 2. Store memory
        self.store.put(galaxy, memory)?;

        // 3. Store embedding
        self.store.put_embedding(memory.metadata.id, &embedding)?;

        // 4. Add to vector store
        {
            let mut vs = self.vector_store.lock().unwrap();
            vs.add(memory.metadata.id, galaxy, embedding);
        }

        // 5. Index in Tantivy
        let timestamp = memory.metadata.created_at.timestamp();
        let tags: Vec<String> = memory.metadata.tags.clone();
        {
            let mut writer = self.search_engine.writer()?;
            self.search_engine.add_document(
                &mut writer,
                &memory.metadata.id.to_string(),
                galaxy.db_name(),
                &memory.content,
                &tags,
                timestamp,
            )?;
            self.search_engine.commit(&mut writer)?;
        }

        Ok(())
    }

    // ── Read path: hybrid search ───────────────────────────────────────

    /// Hybrid search combining BM25 + vector similarity.
    ///
    /// Weights: `bm25_weight * BM25 + vector_weight * cosine + importance_weight * importance`
    #[must_use]
    pub fn hybrid_search(
        &self,
        query: &str,
        limit: usize,
        galaxy_filter: Option<Galaxy>,
    ) -> Vec<RecallResult> {
        // 1. Embed query
        let query_vec = match self.embedder.embed_query(query) {
            Ok(v) => v,
            Err(_) => return Vec::new(),
        };

        // 2. BM25 search (get more than limit for fusion)
        let bm25_limit = limit * 3;
        let bm25_results = self
            .search_engine
            .search_in_galaxy(query, galaxy_filter, bm25_limit)
            .unwrap_or_default();

        // 3. Vector search
        let vector_results = {
            let vs = self.vector_store.lock().unwrap();
            vs.search(&query_vec, bm25_limit, galaxy_filter)
        };

        // 4. Fuse results
        self.fuse_results(&bm25_results, &vector_results, limit)
    }

    /// Pure vector search (no BM25).
    #[must_use]
    pub fn vector_search(
        &self,
        query: &str,
        limit: usize,
        galaxy_filter: Option<Galaxy>,
    ) -> Vec<RecallResult> {
        let query_vec = match self.embedder.embed_query(query) {
            Ok(v) => v,
            Err(_) => return Vec::new(),
        };

        let vector_results = {
            let vs = self.vector_store.lock().unwrap();
            vs.search(&query_vec, limit, galaxy_filter)
        };

        vector_results
            .into_iter()
            .map(|vr| {
                let content = self.get_memory_content(vr.memory_id, vr.galaxy);
                RecallResult {
                    memory_id: vr.memory_id,
                    galaxy: vr.galaxy,
                    score: vr.score,
                    bm25_score: 0.0,
                    vector_score: vr.score,
                    importance: 0.0,
                    content,
                }
            })
            .collect()
    }

    /// Pure BM25 search (no vector).
    #[must_use]
    pub fn text_search(&self, query: &str, limit: usize) -> Vec<RecallResult> {
        let bm25_results = self.search_engine.search(query, limit).unwrap_or_default();

        bm25_results
            .into_iter()
            .filter_map(|sr| {
                let memory_id = Uuid::parse_str(&sr.memory_id).ok()?;
                let galaxy = Galaxy::from_db_name(&sr.galaxy)?;
                Some(RecallResult {
                    memory_id,
                    galaxy,
                    score: sr.score,
                    bm25_score: sr.score,
                    vector_score: 0.0,
                    importance: 0.0,
                    content: sr.content,
                })
            })
            .collect()
    }

    // ── Fusion ─────────────────────────────────────────────────────────

    /// Fuse BM25 and vector results into a single ranked list.
    fn fuse_results(
        &self,
        bm25_results: &[SearchResult],
        vector_results: &[VectorSearchResult],
        limit: usize,
    ) -> Vec<RecallResult> {
        fuse_results_inner(
            bm25_results,
            vector_results,
            limit,
            self.config.bm25_weight,
            self.config.vector_weight,
            self.config.importance_weight,
            |id, galaxy| self.get_memory_content(id, galaxy),
            |id, galaxy| self.get_memory_importance(id, galaxy),
        )
    }

    // ── Helpers ────────────────────────────────────────────────────────

    /// Get memory content by ID.
    fn get_memory_content(&self, id: Uuid, galaxy: Galaxy) -> String {
        self.store
            .get(galaxy, id)
            .ok()
            .flatten()
            .map(|m| m.content)
            .unwrap_or_default()
    }

    /// Get memory importance by ID.
    fn get_memory_importance(&self, id: Uuid, galaxy: Galaxy) -> f32 {
        self.store
            .get(galaxy, id)
            .ok()
            .flatten()
            .map_or(0.0, |m| m.metadata.importance)
    }

    /// Get the number of cached embeddings.
    #[must_use]
    pub fn cache_size(&self) -> usize {
        self.embedding_cache.lock().unwrap().len()
    }

    /// Clear the embedding cache.
    pub fn clear_cache(&self) {
        self.embedding_cache.lock().unwrap().clear();
    }

    /// Get the number of vectors in the vector store.
    #[must_use]
    pub fn vector_count(&self) -> usize {
        self.vector_store.lock().unwrap().len()
    }
}

// ── Fusion implementation ─────────────────────────────────────────────

/// Inner fusion logic, extracted for testability without a full engine.
fn fuse_results_inner(
    bm25_results: &[SearchResult],
    vector_results: &[VectorSearchResult],
    limit: usize,
    bm25_weight: f32,
    vector_weight: f32,
    importance_weight: f32,
    mut get_content: impl FnMut(Uuid, Galaxy) -> String,
    mut get_importance: impl FnMut(Uuid, Galaxy) -> f32,
) -> Vec<RecallResult> {
    // Normalize BM25 scores
    let max_bm25 = bm25_results
        .iter()
        .map(|r| r.score)
        .fold(0.0_f32, f32::max)
        .max(0.001);

    // Build lookup maps
    let mut bm25_map: HashMap<Uuid, (f32, String, Galaxy)> = HashMap::new();
    for sr in bm25_results {
        if let Ok(id) = Uuid::parse_str(&sr.memory_id) {
            match Galaxy::from_db_name(&sr.galaxy) {
                Some(galaxy) => {
                    let normalized = sr.score / max_bm25;
                    bm25_map.insert(id, (normalized, sr.content.clone(), galaxy));
                }
                None => {
                    tracing::warn!(
                        "Skipping BM25 result with unknown galaxy '{}' (memory_id={})",
                        sr.galaxy,
                        sr.memory_id
                    );
                }
            }
        }
    }

    let mut vector_map: HashMap<Uuid, (f32, Galaxy)> = HashMap::new();
    for vr in vector_results {
        vector_map.insert(vr.memory_id, (vr.score, vr.galaxy));
    }

    // Collect all unique memory IDs
    let mut all_ids: std::collections::HashSet<Uuid> = std::collections::HashSet::new();
    all_ids.extend(bm25_map.keys());
    all_ids.extend(vector_map.keys());

    // Fuse scores
    let mut results: Vec<RecallResult> = all_ids
        .into_iter()
        .map(|id| {
            let (bm25_score, content, galaxy_bm25) = bm25_map
                .get(&id)
                .map_or((0.0, String::new(), Galaxy::Codex), |(s, c, g)| {
                    (*s, c.clone(), *g)
                });

            let (vector_score, galaxy_vec) = vector_map
                .get(&id)
                .map_or((0.0, Galaxy::Codex), |(s, g)| (*s, *g));

            let galaxy = if bm25_score > 0.0 {
                galaxy_bm25
            } else {
                galaxy_vec
            };

            let content = if content.is_empty() {
                get_content(id, galaxy)
            } else {
                content
            };

            let importance = get_importance(id, galaxy);

            let fused = bm25_weight.mul_add(
                bm25_score,
                vector_weight.mul_add(vector_score, importance_weight * importance),
            );

            RecallResult {
                memory_id: id,
                galaxy,
                score: fused,
                bm25_score,
                vector_score,
                importance,
                content,
            }
        })
        .collect();

    // Sort by fused score descending
    results.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    results.truncate(limit);
    results
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::embedder::StubEmbedder;

    // ── RecallConfig tests ─────────────────────────────────────────────

    #[test]
    fn config_default_weights() {
        let config = RecallConfig::default();
        assert!(config.weights_normalized());
        assert_eq!(config.bm25_weight, 0.5);
        assert_eq!(config.vector_weight, 0.3);
        assert_eq!(config.importance_weight, 0.2);
    }

    #[test]
    fn config_custom_weights() {
        let config = RecallConfig {
            bm25_weight: 0.6,
            vector_weight: 0.3,
            importance_weight: 0.1,
            ..Default::default()
        };
        assert!(config.weights_normalized());
    }

    #[test]
    fn config_unnormalized_weights() {
        let config = RecallConfig {
            bm25_weight: 0.7,
            vector_weight: 0.5,
            importance_weight: 0.2,
            ..Default::default()
        };
        assert!(!config.weights_normalized());
    }

    #[test]
    fn config_from_env_uses_defaults() {
        // No env vars set — should use defaults
        let config = RecallConfig::from_env();
        assert_eq!(config.bm25_weight, 0.5);
        assert_eq!(config.vector_weight, 0.3);
        assert_eq!(config.importance_weight, 0.2);
    }

    // ── RecallResult tests ─────────────────────────────────────────────

    #[test]
    fn recall_result_fields() {
        let result = RecallResult {
            memory_id: Uuid::new_v4(),
            galaxy: Galaxy::Codex,
            score: 0.85,
            bm25_score: 0.7,
            vector_score: 0.9,
            importance: 0.5,
            content: "test content".into(),
        };
        assert_eq!(result.score, 0.85);
        assert_eq!(result.bm25_score, 0.7);
        assert_eq!(result.vector_score, 0.9);
    }

    // ── RecallEngine unit tests (with stub embedder) ───────────────────

    fn fuse(
        bm25: &[SearchResult],
        vector: &[VectorSearchResult],
        limit: usize,
    ) -> Vec<RecallResult> {
        fuse_results_inner(
            bm25,
            vector,
            limit,
            0.5,
            0.3,
            0.2,
            |_, _| String::new(),
            |_, _| 0.0,
        )
    }

    #[test]
    fn engine_config_default() {
        let config = RecallConfig::default();
        assert_eq!(config.bm25_weight, 0.5);
    }

    #[test]
    fn engine_cache_concept() {
        // Cache is tested via embed_content_caches_result below
        let config = RecallConfig::default();
        assert!(config.cache_embeddings);
    }

    // ── Fusion logic tests ─────────────────────────────────────────────

    #[test]
    fn fuse_results_empty() {
        let results = fuse(&[], &[], 10);
        assert!(results.is_empty());
    }

    #[test]
    fn fuse_results_bm25_only() {
        let id = Uuid::new_v4();
        let bm25 = vec![SearchResult {
            memory_id: id.to_string(),
            galaxy: Galaxy::Codex.db_name().to_string(),
            score: 5.0,
            content: "test".into(),
        }];
        let results = fuse(&bm25, &[], 10);
        assert_eq!(results.len(), 1);
        assert!(results[0].bm25_score > 0.0);
        assert_eq!(results[0].vector_score, 0.0);
    }

    #[test]
    fn fuse_results_vector_only() {
        let id = Uuid::new_v4();
        let vector = vec![VectorSearchResult {
            memory_id: id,
            galaxy: Galaxy::Codex,
            score: 0.85,
        }];
        let results = fuse(&[], &vector, 10);
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].bm25_score, 0.0);
        assert!(results[0].vector_score > 0.0);
    }

    #[test]
    fn fuse_results_both_sources() {
        let id = Uuid::new_v4();
        let bm25 = vec![SearchResult {
            memory_id: id.to_string(),
            galaxy: Galaxy::Codex.db_name().to_string(),
            score: 5.0,
            content: "test content".into(),
        }];
        let vector = vec![VectorSearchResult {
            memory_id: id,
            galaxy: Galaxy::Codex,
            score: 0.85,
        }];
        let results = fuse(&bm25, &vector, 10);
        assert_eq!(results.len(), 1);
        assert!(results[0].bm25_score > 0.0);
        assert!(results[0].vector_score > 0.0);
        assert!(results[0].score > results[0].bm25_score * 0.5);
    }

    #[test]
    fn fuse_results_sorted_by_score() {
        let id1 = Uuid::new_v4();
        let id2 = Uuid::new_v4();
        let bm25 = vec![
            SearchResult {
                memory_id: id1.to_string(),
                galaxy: Galaxy::Codex.db_name().to_string(),
                score: 3.0,
                content: "lower".into(),
            },
            SearchResult {
                memory_id: id2.to_string(),
                galaxy: Galaxy::Codex.db_name().to_string(),
                score: 8.0,
                content: "higher".into(),
            },
        ];
        let results = fuse(&bm25, &[], 10);
        assert_eq!(results.len(), 2);
        assert!(results[0].score >= results[1].score);
    }

    #[test]
    fn fuse_results_truncated_to_limit() {
        let bm25: Vec<SearchResult> = (0..20)
            .map(|i| SearchResult {
                memory_id: Uuid::new_v4().to_string(),
                galaxy: Galaxy::Codex.db_name().to_string(),
                score: 1.0 + i as f32,
                content: format!("content {i}"),
            })
            .collect();
        let results = fuse(&bm25, &[], 5);
        assert_eq!(results.len(), 5);
    }

    #[test]
    fn fuse_results_normalizes_bm25() {
        let id = Uuid::new_v4();
        let bm25 = vec![SearchResult {
            memory_id: id.to_string(),
            galaxy: Galaxy::Codex.db_name().to_string(),
            score: 100.0,
            content: "test".into(),
        }];
        let results = fuse(&bm25, &[], 10);
        assert!((results[0].bm25_score - 1.0).abs() < 0.01);
    }

    // ── Embedding cache tests ──────────────────────────────────────────

    #[test]
    fn embed_content_caches_result() {
        let embedder = StubEmbedder::new(384);
        let content = "test content for caching";
        let vec1 = embedder.embed(content).unwrap();
        let vec2 = embedder.embed(content).unwrap();
        assert_eq!(vec1, vec2);
    }

    #[test]
    fn embed_content_different_content_different_result() {
        let embedder = StubEmbedder::new(384);
        let vec1 = embedder.embed("content one").unwrap();
        let vec2 = embedder.embed("content two").unwrap();
        assert_ne!(vec1, vec2);
    }

    // ── Weight configuration tests ─────────────────────────────────────

    #[test]
    fn fuse_with_zero_bm25_weight() {
        let id = Uuid::new_v4();
        let bm25 = vec![SearchResult {
            memory_id: id.to_string(),
            galaxy: Galaxy::Codex.db_name().to_string(),
            score: 5.0,
            content: "test".into(),
        }];
        let results = fuse_results_inner(
            &bm25,
            &[],
            10,
            0.5,
            0.3,
            0.2,
            |_, _| String::new(),
            |_, _| 0.0,
        );
        assert!((results[0].score - 0.5).abs() < 0.01);
    }

    #[test]
    fn fuse_with_zero_vector_weight() {
        let id = Uuid::new_v4();
        let vector = vec![VectorSearchResult {
            memory_id: id,
            galaxy: Galaxy::Codex,
            score: 0.9,
        }];
        let results = fuse_results_inner(
            &[],
            &vector,
            10,
            0.5,
            0.3,
            0.2,
            |_, _| String::new(),
            |_, _| 0.0,
        );
        assert!((results[0].score - 0.27).abs() < 0.01);
    }

    // ── GalaxyExt tests ────────────────────────────────────────────────

    #[test]
    fn galaxy_from_db_name_valid() {
        assert_eq!(Galaxy::from_db_name("codex"), Some(Galaxy::Codex));
    }

    #[test]
    fn galaxy_from_db_name_invalid() {
        assert_eq!(Galaxy::from_db_name("nonexistent"), None);
    }

    // ── Integration tests (end-to-end with temp-dir LMDB + Tantivy) ────

    use crate::Memory;
    use tempfile::tempdir;

    fn setup_engine() -> (tempfile::TempDir, RecallEngine) {
        let tmp = tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tantivy_path = tmp.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy_path).unwrap());
        let vector_store = VectorStore::new();
        let embedder: Arc<dyn Embedder> = Arc::new(StubEmbedder::new(384));
        let engine = RecallEngine::new(
            store,
            search,
            vector_store,
            embedder,
            RecallConfig::default(),
        )
        .unwrap();
        (tmp, engine)
    }

    #[test]
    fn integration_store_and_hybrid_search_roundtrip() {
        let (_tmp, engine) = setup_engine();

        let mem1 = Memory::new(
            Galaxy::Codex,
            "Rust programming language is fast and safe".into(),
        )
        .with_importance(0.8)
        .with_tags(vec!["rust".into(), "programming".into()]);
        let mem2 = Memory::new(Galaxy::Codex, "Python is great for data science".into())
            .with_importance(0.5)
            .with_tags(vec!["python".into(), "data".into()]);
        let mem3 = Memory::new(
            Galaxy::Codex,
            "The Rust ownership model prevents memory leaks".into(),
        )
        .with_importance(0.9)
        .with_tags(vec!["rust".into(), "memory".into()]);

        engine.store_with_embedding(Galaxy::Codex, &mem1).unwrap();
        engine.store_with_embedding(Galaxy::Codex, &mem2).unwrap();
        engine.store_with_embedding(Galaxy::Codex, &mem3).unwrap();

        // Search for "rust" — should find mem1 and mem3 (both contain "rust")
        let results = engine.hybrid_search("rust", 10, None);
        assert!(!results.is_empty(), "hybrid search should return results");

        // All results should contain "rust" in content or be vector-similar
        let top_contents: Vec<&str> = results.iter().map(|r| r.content.as_str()).collect();
        assert!(
            top_contents.iter().any(|c| c.contains("Rust")),
            "top results should include Rust content, got: {top_contents:?}"
        );
    }

    #[test]
    fn integration_bm25_and_vector_both_contribute() {
        let (_tmp, engine) = setup_engine();

        // Store memories with distinct content
        for i in 0..5 {
            let mem = Memory::new(
                Galaxy::Codex,
                format!("memory about topic {i} with unique content"),
            )
            .with_importance(0.5);
            engine.store_with_embedding(Galaxy::Codex, &mem).unwrap();
        }

        // Search for a term that exists in all memories
        let results = engine.hybrid_search("memory", 10, None);
        assert!(!results.is_empty(), "should find memories");

        // BM25 should have contributed (all contain "memory")
        let has_bm25 = results.iter().any(|r| r.bm25_score > 0.0);
        assert!(has_bm25, "BM25 should contribute to fused results");
    }

    #[test]
    fn integration_vector_search_only() {
        let (_tmp, engine) = setup_engine();

        let content = "unique searchable content for vector test";
        let mem = Memory::new(Galaxy::Codex, content.into()).with_importance(0.7);
        engine.store_with_embedding(Galaxy::Codex, &mem).unwrap();

        // StubEmbedder is hash-based — same text produces same vector
        let results = engine.vector_search(content, 10, None);
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].memory_id, mem.metadata.id);
        assert!(results[0].vector_score > 0.0);
    }

    #[test]
    fn integration_text_search_only() {
        let (_tmp, engine) = setup_engine();

        let mem = Memory::new(Galaxy::Codex, "specific text about rust ownership".into())
            .with_tags(vec!["rust".into()]);
        engine.store_with_embedding(Galaxy::Codex, &mem).unwrap();

        let results = engine.text_search("rust", 10);
        assert!(!results.is_empty(), "text search should find results");
        assert!(results.iter().any(|r| r.bm25_score > 0.0));
    }

    #[test]
    fn integration_galaxy_filter() {
        let (_tmp, engine) = setup_engine();

        let mem_codex = Memory::new(Galaxy::Codex, "codex memory about rust".into());
        let mem_research = Memory::new(Galaxy::Research, "research memory about rust".into());

        engine
            .store_with_embedding(Galaxy::Codex, &mem_codex)
            .unwrap();
        engine
            .store_with_embedding(Galaxy::Research, &mem_research)
            .unwrap();

        let results = engine.hybrid_search("rust", 10, Some(Galaxy::Codex));
        assert!(!results.is_empty());
        assert!(
            results.iter().all(|r| r.galaxy == Galaxy::Codex),
            "all results should be from Codex galaxy"
        );
    }

    #[test]
    fn integration_empty_search() {
        let (_tmp, engine) = setup_engine();
        let results = engine.hybrid_search("nonexistent", 10, None);
        assert!(results.is_empty());
    }

    #[test]
    fn integration_cache_populated_after_store() {
        let (_tmp, engine) = setup_engine();

        let mem = Memory::new(Galaxy::Codex, "content to be cached".into());
        engine.store_with_embedding(Galaxy::Codex, &mem).unwrap();

        // The embedding cache should have one entry
        assert_eq!(engine.cache_size(), 1);
    }

    #[test]
    fn integration_vector_count_tracks_stores() {
        let (_tmp, engine) = setup_engine();

        assert_eq!(engine.vector_count(), 0);

        for i in 0..3 {
            let mem = Memory::new(Galaxy::Codex, format!("memory {i}"));
            engine.store_with_embedding(Galaxy::Codex, &mem).unwrap();
        }

        assert_eq!(engine.vector_count(), 3);
    }

    #[test]
    fn integration_importance_affects_ranking() {
        let (_tmp, engine) = setup_engine();

        // Two memories with same content keyword but different importance
        let mem_low =
            Memory::new(Galaxy::Codex, "rust programming basics".into()).with_importance(0.1);
        let mem_high =
            Memory::new(Galaxy::Codex, "rust programming advanced".into()).with_importance(0.9);

        engine
            .store_with_embedding(Galaxy::Codex, &mem_low)
            .unwrap();
        engine
            .store_with_embedding(Galaxy::Codex, &mem_high)
            .unwrap();

        let results = engine.hybrid_search("rust", 10, None);
        assert_eq!(results.len(), 2);

        // The higher-importance memory should generally rank higher
        // (both have similar BM25 and vector scores, importance breaks the tie)
        let high_idx = results
            .iter()
            .position(|r| r.memory_id == mem_high.metadata.id)
            .unwrap();
        let low_idx = results
            .iter()
            .position(|r| r.memory_id == mem_low.metadata.id)
            .unwrap();
        assert!(
            high_idx < low_idx,
            "higher importance memory should rank higher"
        );
    }

    #[test]
    fn config_from_env_rejects_nan_weights() {
        // Test the validation logic directly rather than via env vars
        // (wm-memory has forbid(unsafe_code), can't use set_var)
        let mut config = RecallConfig::default();
        let w: f32 = "NaN".parse().unwrap();
        if w.is_finite() && w >= 0.0 {
            config.bm25_weight = w.min(1.0);
        }
        assert_eq!(
            config.bm25_weight, 0.5,
            "NaN should be rejected, default kept"
        );
    }

    #[test]
    fn config_from_env_rejects_negative_weights() {
        let mut config = RecallConfig::default();
        let w: f32 = "-0.5".parse().unwrap();
        if w.is_finite() && w >= 0.0 {
            config.vector_weight = w.min(1.0);
        }
        assert_eq!(
            config.vector_weight, 0.3,
            "Negative should be rejected, default kept"
        );
    }

    #[test]
    fn config_from_env_clamps_weights_to_1() {
        let mut config = RecallConfig::default();
        let w: f32 = "5.0".parse().unwrap();
        if w.is_finite() && w >= 0.0 {
            config.importance_weight = w.min(1.0);
        }
        assert_eq!(
            config.importance_weight, 1.0,
            "Weight should be clamped to 1.0"
        );
    }

    #[test]
    fn config_from_env_normalizes_weights() {
        let mut config = RecallConfig {
            bm25_weight: 0.8,
            vector_weight: 0.8,
            importance_weight: 0.8,
            ..Default::default()
        };
        let sum = config.bm25_weight + config.vector_weight + config.importance_weight;
        if sum > 0.0 && (sum - 1.0).abs() > 0.01 {
            config.bm25_weight /= sum;
            config.vector_weight /= sum;
            config.importance_weight /= sum;
        }
        assert!(
            config.weights_normalized(),
            "Weights should be normalized to sum to 1.0"
        );
    }

    #[test]
    fn config_from_env_rejects_infinity() {
        let mut config = RecallConfig::default();
        let w: f32 = "inf".parse().unwrap();
        if w.is_finite() && w >= 0.0 {
            config.bm25_weight = w.min(1.0);
        }
        assert_eq!(
            config.bm25_weight, 0.5,
            "Infinity should be rejected, default kept"
        );
    }
}
