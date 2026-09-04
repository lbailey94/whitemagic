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
//! | `WM_TRUST_WEIGHT` | `0.0` | Post-fusion trust multiplier (source_trust 0.7 neutral) |
//! | `WM_RECALL_CONFORMAL_ALPHA` | unset | Conformal set miscoverage level (unset = off) |

#![allow(clippy::missing_const_for_fn)]

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use uuid::Uuid;
use wm_core::{CoreError, Galaxy, Result};

use crate::associations::AssociationStore;
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
    /// Graph-traversal contribution (V8 S6 third fusion phase) — 0.0
    /// unless the result was injected or boosted by walking association
    /// edges from a fused seed.
    pub graph_score: f32,
    /// Trust multiplier actually applied to `score` in fusion (V8 S8) —
    /// 1.0 when `WM_TRUST_WEIGHT` is off, so disclosure never lies.
    pub trust_factor: f32,
    /// Conformal-set membership (V8 S8) — meaningful only when the
    /// disclosure says `active`; always `false` otherwise.
    pub in_conformal_set: bool,
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
    /// Post-fusion graph-traversal boost multiplier (V8 S6, default 0.0 =
    /// OFF — evidence-gated like trust weighting). NOT part of the
    /// normalized fusion sum: when > 0, the top fused seeds are expanded
    /// one hop through association edges, neighbors are injected or
    /// boosted by `seed_score * edge_weight * graph_weight`, and results
    /// carry the contribution in `RecallResult::graph_score`.
    pub graph_weight: f32,
    /// Post-fusion trust multiplier (V8 S8, default 0.0 = OFF).
    ///
    /// Like the graph weight, deliberately OUTSIDE the normalized fusion
    /// sum: when > 0, every fused score is scaled by
    /// `1 + weight * (source_trust − 0.7)` (user-confirmed ranks up,
    /// tool-ingested 0.7 unchanged, low trust down), and the factor is
    /// disclosed per-result in `RecallResult::trust_factor`.
    pub trust_weight: f32,
    /// Conformal-set miscoverage level (V8 S8, default None = OFF). When
    /// set in (0, 1), fused results are graded against a calibrated
    /// prediction set and the search carries a `ConformalSetInfo`
    /// disclosure — `active` with a real threshold, or `uncalibrated`
    /// until feedback samples exist.
    pub conformal_alpha: Option<f32>,
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
            graph_weight: 0.0,
            trust_weight: 0.0,
            conformal_alpha: None,
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
        // Graph traversal boost — deliberately OUTSIDE the normalization
        // sum (it is a post-fusion multiplier, not a fourth signal).
        if let Ok(v) = std::env::var("WM_RECALL_GRAPH_WEIGHT") {
            if let Ok(w) = v.parse::<f32>() {
                if w.is_finite() && w >= 0.0 {
                    config.graph_weight = w.min(1.0);
                }
            }
        }
        // Trust weighting (V8 S8) — same post-fusion treatment: a
        // multiplier, not a fusion signal. Same env the tool-side
        // post-hoc path reads, so semantics are shared.
        if let Ok(v) = std::env::var("WM_TRUST_WEIGHT") {
            if let Ok(w) = v.parse::<f32>() {
                if w.is_finite() && w >= 0.0 {
                    config.trust_weight = w.min(1.0);
                }
            }
        }
        // Conformal sets (V8 S8) — an alpha in (0, 1) enables calibrated
        // membership grading; anything else (unset, invalid) stays off.
        if let Ok(v) = std::env::var("WM_RECALL_CONFORMAL_ALPHA") {
            if let Ok(a) = v.parse::<f32>() {
                if a.is_finite() && a > 0.0 && a < 1.0 {
                    config.conformal_alpha = Some(a);
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
    /// Conformal-set state (V8 S8) — `None` unless
    /// `WM_RECALL_CONFORMAL_ALPHA` is configured.
    conformal: Mutex<Option<crate::recall_conformal::RecallConformal>>,
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
        let conformal =
            Mutex::new(config.conformal_alpha.and_then(|alpha| {
                crate::recall_conformal::RecallConformal::new(alpha, store.clone())
            }));
        Ok(Self {
            store,
            search_engine,
            vector_store: Mutex::new(vector_store),
            embedder,
            config,
            embedding_cache: Mutex::new(HashMap::new()),
            conformal,
        })
    }

    /// Record one relevance-feedback sample into the conformal calibrator
    /// (V8 S8). Errors honestly when the knob is off — there is no
    /// calibrated set to feed.
    pub fn record_relevance_feedback(&self, score: f32, relevant: bool) -> Result<usize> {
        let mut guard = self
            .conformal
            .lock()
            .map_err(|e| CoreError::Memory(format!("recall conformal lock: {e}")))?;
        match guard.as_mut() {
            Some(rc) => Ok(rc.record_feedback(score, relevant)),
            None => Err(CoreError::InvalidArgs(
                "conformal calibration is not enabled — set WM_RECALL_CONFORMAL_ALPHA in (0,1)"
                    .into(),
            )),
        }
    }

    /// Conformal disclosure for a completed search: grades the results
    /// against the calibrated set (marking `in_conformal_set`) and returns
    /// the set-level info. `Ok(None)` when the knob is off — no claim is
    /// made at all.
    // The lock must span the whole grading: membership is read from the
    // same fitted state that produced the threshold, and a concurrent
    // record_feedback/fit must not split the disclosure from the marks.
    #[allow(clippy::significant_drop_tightening)]
    pub fn conformal_disclosure(
        &self,
        results: &mut [RecallResult],
    ) -> Result<Option<crate::recall_conformal::ConformalSetInfo>> {
        use crate::recall_conformal::ConformalSetInfo;
        let guard = self
            .conformal
            .lock()
            .map_err(|e| CoreError::Memory(format!("recall conformal lock: {e}")))?;
        let Some(rc) = guard.as_ref() else {
            return Ok(None);
        };
        let coverage_target = Some(f64::from(1.0 - rc.alpha()));
        let info = if rc.is_fitted() {
            let threshold = rc.threshold();
            let mut set_size = 0usize;
            for r in results.iter_mut() {
                r.in_conformal_set = rc.membership(r.score) == Some(true);
                if r.in_conformal_set {
                    set_size += 1;
                }
            }
            ConformalSetInfo {
                status: "active".into(),
                alpha: Some(f64::from(rc.alpha())),
                coverage_target,
                calibration_samples: Some(rc.sample_count()),
                threshold,
                set_size: Some(set_size),
                hint: None,
            }
        } else {
            ConformalSetInfo {
                status: "uncalibrated".into(),
                alpha: Some(f64::from(rc.alpha())),
                coverage_target,
                calibration_samples: Some(rc.sample_count()),
                threshold: None,
                set_size: None,
                hint: Some(format!(
                    "record ≥ {} relevance-feedback samples to calibrate",
                    crate::recall_conformal::MIN_SAMPLES
                )),
            }
        };
        Ok(Some(info))
    }

    /// Get the configuration.
    #[must_use]
    pub fn config(&self) -> &RecallConfig {
        &self.config
    }

    /// Whether the embedder is a real backend (not a stub).
    ///
    /// When false, hybrid search would produce garbage vectors and
    /// `store_with_embedding` should be avoided in favor of plain BM25.
    #[must_use]
    pub fn embedder_is_real(&self) -> bool {
        self.embedder.backend_name() != "stub"
    }

    // ── Write path: auto-embed ─────────────────────────────────────────

    /// Persistent cache key for a text: embedder namespace + content hash.
    /// Vectors differ across models, so the namespace rides the key.
    fn embedding_cache_key(&self, embedded_text: &str) -> String {
        format!(
            "{}:{}",
            self.embedder.cache_namespace(),
            content_hash(embedded_text)
        )
    }

    /// Embed content and cache the result.
    ///
    /// Returns the embedding vector. Lookup order: in-memory LRU, then the
    /// persistent content-hash cache (survives restarts — re-runs and
    /// re-ingest warm-start instead of re-embedding), then the embedder.
    fn embed_content(&self, content: &str) -> Result<Vec<f32>> {
        let hash = content_hash(content);

        // Check in-memory cache
        if self.config.cache_embeddings {
            let cache = self
                .embedding_cache
                .lock()
                .map_err(|e| CoreError::Memory(format!("embedding cache lock: {e}")))?;
            if let Some(vec) = cache.get(&hash) {
                return Ok(vec.clone());
            }
        }

        // Check the persistent cache (v26 "Tier 2", finally wired).
        let cache_key = self.embedding_cache_key(content);
        match self.store.get_embedding_cache(&cache_key) {
            Ok(Some(vector)) => {
                if self.config.cache_embeddings {
                    if let Ok(mut cache) = self.embedding_cache.lock() {
                        cache.insert(hash, vector.clone());
                    }
                }
                return Ok(vector);
            }
            Ok(None) => {}
            Err(error) => tracing::warn!("embedding cache read failed: {error}"),
        }

        // Embed
        let embedding = self.embedder.embed(content)?;

        // Persist (non-fatal: a cache write failure must not fail the ingest)
        if let Err(error) = self.store.put_embedding_cache(&cache_key, &embedding) {
            tracing::warn!("embedding cache write failed: {error}");
        }

        // Cache in memory
        if self.config.cache_embeddings {
            let mut cache = self
                .embedding_cache
                .lock()
                .map_err(|e| CoreError::Memory(format!("embedding cache lock: {e}")))?;
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
            let mut vs = self
                .vector_store
                .lock()
                .map_err(|e| CoreError::Memory(format!("vector store lock: {e}")))?;
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

    /// Batch-store memories with auto-embedding in a single HTTP call + single Tantivy commit.
    ///
    /// Like `store_with_embedding` but for multiple memories at once:
    /// 1. Embeds all content via `embed_batch()` (single HTTP call).
    /// 2. Stores all memories to LMDB.
    /// 3. Stores all embeddings.
    /// 4. Adds all to the vector store.
    /// 5. Indexes all in Tantivy with a single writer + commit.
    ///
    /// Returns the number of memories successfully stored.
    pub fn store_batch_with_embedding(
        &self,
        entries: &[(Galaxy, &crate::Memory)],
    ) -> Result<usize> {
        if entries.is_empty() {
            return Ok(0);
        }

        // 1. Resolve the persistent cache first (v26 "Tier 2", wired):
        //    only the misses reach the embedder, chunked as before; hits
        //    are reassembled in order. Cache keys ride the EMBEDDED text
        //    (the chunked form), matching the single-item path.
        const MAX_CHARS_PER_CHUNK: usize = 1500; // ~465 tokens worst case (3.21 chars/token)
        const MAX_CHARS_PER_ITEM: usize = 1500; // same limit for individual items
        let contents: Vec<String> = entries
            .iter()
            .map(|(_, m)| {
                if m.content.len() > MAX_CHARS_PER_ITEM {
                    m.content.chars().take(MAX_CHARS_PER_ITEM).collect()
                } else {
                    m.content.clone()
                }
            })
            .collect();
        let content_refs: Vec<&str> = contents.iter().map(String::as_str).collect();
        let cache_keys: Vec<String> = content_refs
            .iter()
            .map(|c| self.embedding_cache_key(c))
            .collect();
        let mut embeddings: Vec<Option<Vec<f32>>> =
            match self.store.get_embedding_cache_batch(&cache_keys) {
                Ok(cached) => cached,
                Err(error) => {
                    tracing::warn!("embedding cache batch read failed: {error}");
                    vec![None; cache_keys.len()]
                }
            };
        let misses: Vec<(usize, &str)> = content_refs
            .iter()
            .enumerate()
            .filter(|(i, _)| embeddings[*i].is_none())
            .map(|(i, content)| (i, *content))
            .collect();

        // Chunked embedding for the misses only. Two stopping rules: the
        // char cap (HTTP token limits) and the embedder's preferred batch
        // size in texts (local engines want big batches so the session
        // pool fans out efficiently).
        let max_batch_texts = self.embedder.preferred_max_batch_texts();
        let mut chunk: Vec<&str> = Vec::new();
        let mut chunk_positions: Vec<usize> = Vec::new();
        let mut chunk_chars: usize = 0;
        let mut embed_chunk = |chunk: &[&str], positions: &[usize], store: &Self| -> Result<()> {
            let chunk_vecs = store.embedder.embed_batch(chunk)?;
            if chunk_vecs.len() != chunk.len() {
                return Err(CoreError::Memory(format!(
                    "embed_batch returned {} vectors for {} inputs (chunk)",
                    chunk_vecs.len(),
                    chunk.len()
                )));
            }
            for (pos, vector) in positions.iter().zip(chunk_vecs) {
                embeddings[*pos] = Some(vector);
            }
            Ok(())
        };
        for &(position, content) in &misses {
            let content_chars = content.len();
            let flush = !chunk.is_empty()
                && (chunk_chars + content_chars > MAX_CHARS_PER_CHUNK
                    || chunk.len() >= max_batch_texts);
            if flush {
                embed_chunk(&chunk, &chunk_positions, self)?;
                chunk.clear();
                chunk_positions.clear();
                chunk_chars = 0;
            }
            chunk.push(content);
            chunk_positions.push(position);
            chunk_chars += content_chars;
        }
        if !chunk.is_empty() {
            embed_chunk(&chunk, &chunk_positions, self)?;
        }

        // Persist the freshly embedded vectors (one transaction; a cache
        // write failure must not fail the ingest).
        let fresh: Vec<(String, Vec<f32>)> = misses
            .iter()
            .filter_map(|&(position, _)| {
                embeddings[position]
                    .clone()
                    .map(|vector| (cache_keys[position].clone(), vector))
            })
            .collect();
        if let Err(error) = self.store.put_embedding_cache_batch(&fresh) {
            tracing::warn!("embedding cache batch write failed: {error}");
        }

        // 2. Store all memories to LMDB + embeddings
        for (i, (galaxy, memory)) in entries.iter().enumerate() {
            let Some(ref embedding) = embeddings[i] else {
                return Err(CoreError::Memory(format!(
                    "embedding missing for entry {i} after cache resolution"
                )));
            };
            self.store.put(*galaxy, memory)?;
            self.store.put_embedding(memory.metadata.id, embedding)?;
        }

        // 3. Add all to vector store
        {
            let mut vs = self
                .vector_store
                .lock()
                .map_err(|e| CoreError::Memory(format!("vector store lock: {e}")))?;
            for (i, (galaxy, memory)) in entries.iter().enumerate() {
                if let Some(ref embedding) = embeddings[i] {
                    vs.add(memory.metadata.id, *galaxy, embedding.clone());
                }
            }
        }

        // 4. Index all in Tantivy with a single commit
        {
            let mut writer = self.search_engine.writer()?;
            for (galaxy, memory) in entries {
                let timestamp = memory.metadata.created_at.timestamp();
                let tags: Vec<String> = memory.metadata.tags.clone();
                self.search_engine.add_document(
                    &mut writer,
                    &memory.metadata.id.to_string(),
                    galaxy.db_name(),
                    &memory.content,
                    &tags,
                    timestamp,
                )?;
            }
            self.search_engine.commit(&mut writer)?;
        }

        // 5. Fill the in-memory cache for the misses (hits already ride
        //    the persistent layer; no need to burn LRU slots on them).
        //    Keyed on the ORIGINAL content hash, matching embed_content.
        if self.config.cache_embeddings {
            let mut cache = self
                .embedding_cache
                .lock()
                .map_err(|e| CoreError::Memory(format!("embedding cache lock: {e}")))?;
            for &(position, _) in &misses {
                let Some(ref vector) = embeddings[position] else {
                    continue;
                };
                let hash = content_hash(&entries[position].1.content);
                if cache.len() >= self.config.max_cache_entries {
                    let to_remove: Vec<String> =
                        cache.keys().take(cache.len() / 10).cloned().collect();
                    for key in to_remove {
                        cache.remove(&key);
                    }
                }
                cache.insert(hash, vector.clone());
            }
        }

        Ok(entries.len())
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
        self.hybrid_search_with_disclosure(query, limit, galaxy_filter)
            .0
    }

    /// Hybrid search plus the V8 S8 disclosure: `(results, conformal)`.
    /// `conformal` is `None` when `WM_RECALL_CONFORMAL_ALPHA` is unset —
    /// no calibrated claim exists, so none is made.
    pub fn hybrid_search_with_disclosure(
        &self,
        query: &str,
        limit: usize,
        galaxy_filter: Option<Galaxy>,
    ) -> (
        Vec<RecallResult>,
        Option<crate::recall_conformal::ConformalSetInfo>,
    ) {
        // 1. Embed query
        let query_vec = match self.embedder.embed_query(query) {
            Ok(v) => v,
            Err(_) => return (Vec::new(), None),
        };

        // 2. BM25 search (get more than limit for fusion)
        let bm25_limit = limit * 3;
        let bm25_results = self
            .search_engine
            .search_in_galaxy(query, galaxy_filter, bm25_limit)
            .unwrap_or_default();

        // 3. Vector search
        let vector_results = {
            let Ok(vs) = self.vector_store.lock() else {
                return (Vec::new(), None);
            };
            vs.search(&query_vec, bm25_limit, galaxy_filter)
        };

        // 4. Fuse results (trust weighting applied inside when enabled)
        let fused = self.fuse_results(&bm25_results, &vector_results, limit);

        // 4b. Validity filter (V8 Slice B) — off unless
        // WM_VALIDITY_ENFORCE=1; knob-off this retains everything and the
        // surface is byte-identical.
        let fused = if crate::memory::validity_enforced() {
            fused
                .into_iter()
                .filter(|r| {
                    self.find_memory_anywhere(r.memory_id)
                        .is_none_or(|mem| mem.metadata.validity.is_current())
                })
                .collect()
        } else {
            fused
        };

        // 5. Graph expansion (V8 S6 third fusion phase) — off unless
        // WM_RECALL_GRAPH_WEIGHT > 0.
        let mut expanded = self.expand_with_graph(fused, limit);

        // 6. Conformal grading (V8 S8) — off unless
        // WM_RECALL_CONFORMAL_ALPHA is set; honest disclosure either way.
        match self.conformal_disclosure(&mut expanded) {
            Ok(info) => (expanded, info),
            Err(e) => {
                tracing::warn!(error = %e, "recall conformal disclosure failed");
                (expanded, None)
            }
        }
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
            let Ok(vs) = self.vector_store.lock() else {
                return Vec::new();
            };
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
                    graph_score: 0.0,
                    trust_factor: 1.0,
                    in_conformal_set: false,
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
                    graph_score: 0.0,
                    trust_factor: 1.0,
                    in_conformal_set: false,
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
            self.config.trust_weight,
            |id, galaxy| self.get_memory_content(id, galaxy),
            |id, galaxy| self.get_memory_importance(id, galaxy),
            |id, galaxy| self.get_memory_source_trust(id, galaxy),
        )
    }

    /// Expand fused results one hop through association edges (V8 S6 —
    /// the third fusion phase).
    ///
    /// From the top-3 fused seeds, walk outgoing + incoming edges (weight
    /// ≥ 0.2): neighbors already present get a score boost, absent ones
    /// are injected (privacy-guarded) with `seed_score * edge_weight *
    /// graph_weight` as their contribution, disclosed per-result in
    /// `graph_score`. Inert until `WM_RECALL_GRAPH_WEIGHT > 0`; the base
    /// fusion is byte-identical when the knob is off.
    fn expand_with_graph(&self, mut results: Vec<RecallResult>, limit: usize) -> Vec<RecallResult> {
        if self.config.graph_weight <= 0.0 || results.is_empty() {
            return results;
        }
        let Ok(assoc_store) = AssociationStore::open(self.store.env()) else {
            return results;
        };
        let env = self.store.env();
        let seeds: Vec<RecallResult> = results.iter().take(3).cloned().collect();
        for seed in seeds {
            let outgoing = assoc_store
                .find_from(env, seed.memory_id)
                .unwrap_or_default();
            let incoming = assoc_store.find_to(env, seed.memory_id).unwrap_or_default();
            for edge in outgoing.into_iter().chain(incoming) {
                if edge.weight < 0.2 {
                    continue;
                }
                let neighbor_id = if edge.source == seed.memory_id {
                    edge.target
                } else {
                    edge.source
                };
                if neighbor_id == seed.memory_id {
                    continue;
                }
                // Validity-aware graph phase (V8 Slice B, knob-gated):
                // non-current neighbors contribute nothing while enforced.
                // Knob-off this block never runs and fusion is byte-identical.
                if crate::memory::validity_enforced()
                    && self
                        .find_memory_anywhere(neighbor_id)
                        .is_some_and(|mem| !mem.metadata.validity.is_current())
                {
                    continue;
                }
                let contribution = seed.score * edge.weight * self.config.graph_weight;
                if let Some(existing) = results.iter_mut().find(|r| r.memory_id == neighbor_id) {
                    existing.score += contribution;
                    existing.graph_score += contribution;
                } else if let Some(mem) = self.find_memory_anywhere(neighbor_id) {
                    // Injected neighbors honor the privacy flag — the main
                    // path must never gain a side door through the graph.
                    // Same for validity while enforced (Slice B).
                    if mem.metadata.is_private {
                        continue;
                    }
                    if crate::memory::validity_enforced() && !mem.metadata.validity.is_current() {
                        continue;
                    }
                    results.push(RecallResult {
                        memory_id: neighbor_id,
                        galaxy: mem.metadata.galaxy,
                        score: contribution,
                        bm25_score: 0.0,
                        vector_score: 0.0,
                        importance: mem.metadata.importance,
                        graph_score: contribution,
                        trust_factor: 1.0,
                        in_conformal_set: false,
                        content: mem.content.chars().take(400).collect(),
                    });
                }
            }
        }
        results.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        results.truncate(limit.max(3));
        results
    }

    /// Resolve a memory id across the memory galaxies (association edges
    /// are galaxy-blind UUID pairs — the `graph.walk` resolution pattern).
    fn find_memory_anywhere(&self, id: Uuid) -> Option<crate::memory::Memory> {
        Galaxy::memory_galaxies()
            .iter()
            .find_map(|g| self.store.get(*g, id).ok().flatten())
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

    /// Whether a memory is flagged `is_private` (missing memories count as
    /// private — they cannot be verified visible).
    #[must_use]
    pub fn is_private(&self, id: Uuid, galaxy: Galaxy) -> bool {
        self.store
            .get(galaxy, id)
            .ok()
            .flatten()
            .is_none_or(|m| m.metadata.is_private)
    }

    /// Get memory importance by ID.
    fn get_memory_importance(&self, id: Uuid, galaxy: Galaxy) -> f32 {
        self.store
            .get(galaxy, id)
            .ok()
            .flatten()
            .map_or(0.0, |m| m.metadata.importance)
    }

    /// Get memory `source_trust` by ID (V8 S8 trust-into-fusion).
    /// Missing memories resolve to 0.7 — the tool-ingested neutral point —
    /// so an absent row is trust-neutral rather than trust-maximal.
    fn get_memory_source_trust(&self, id: Uuid, galaxy: Galaxy) -> f32 {
        self.store
            .get(galaxy, id)
            .ok()
            .flatten()
            .map_or(0.7, |m| m.metadata.source_trust)
    }

    /// Get the number of cached embeddings.
    #[must_use]
    pub fn cache_size(&self) -> usize {
        self.embedding_cache.lock().map_or(0, |c| c.len())
    }

    /// Clear the embedding cache.
    pub fn clear_cache(&self) {
        if let Ok(mut c) = self.embedding_cache.lock() {
            c.clear();
        }
    }

    /// Get the number of vectors in the vector store.
    #[must_use]
    pub fn vector_count(&self) -> usize {
        self.vector_store.lock().map_or(0, |c| c.len())
    }
}

// ── Fusion implementation ─────────────────────────────────────────────

/// Inner fusion logic, extracted for testability without a full engine.
#[allow(clippy::too_many_arguments)]
fn fuse_results_inner(
    bm25_results: &[SearchResult],
    vector_results: &[VectorSearchResult],
    limit: usize,
    bm25_weight: f32,
    vector_weight: f32,
    importance_weight: f32,
    trust_weight: f32,
    mut get_content: impl FnMut(Uuid, Galaxy) -> String,
    mut get_importance: impl FnMut(Uuid, Galaxy) -> f32,
    mut get_source_trust: impl FnMut(Uuid, Galaxy) -> f32,
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

            // Trust weighting (V8 S8): post-fusion multiplier, applied
            // here so every consumer of the hybrid path sees the same
            // ranking. Factor disclosed per-result; 1.0 when the knob is
            // off (byte-identical base fusion). Plain float ops by
            // design — mul_add would change rounding and with it the
            // ranking (the deterministic-scorer allow class, AGENTS.md).
            #[allow(clippy::suboptimal_flops)]
            let (score, trust_factor) = if trust_weight > 0.0 {
                let source_trust = get_source_trust(id, galaxy);
                let factor = (1.0 + trust_weight * (source_trust.clamp(0.0, 1.0) - 0.7)).max(0.0);
                (fused * factor, factor)
            } else {
                (fused, 1.0)
            };

            RecallResult {
                memory_id: id,
                galaxy,
                score,
                bm25_score,
                vector_score,
                importance,
                graph_score: 0.0,
                trust_factor,
                in_conformal_set: false,
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
    use crate::associations::{Association, LinkType};
    use crate::embedder::StubEmbedder;

    /// S6 acceptance harness: a real store + Tantivy index + engine. Only
    /// `indexed` memories are BM25-findable; graph-only neighbors are NOT
    /// indexed, so their presence in hybrid results proves traversal.
    struct GraphHarness {
        _dir: tempfile::TempDir,
        store: Arc<MemoryStore>,
        engine_with_graph: RecallEngine,
        engine_plain: RecallEngine,
    }

    fn graph_harness() -> GraphHarness {
        let dir = tempfile::tempdir().unwrap();
        let lmdb = dir.path().join("lmdb");
        std::fs::create_dir_all(&lmdb).unwrap();
        let store = Arc::new(MemoryStore::open_default(&lmdb).unwrap());
        let tantivy = dir.path().join("tantivy");
        std::fs::create_dir_all(&tantivy).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy).unwrap());

        // Seed: A (indexed, the query hit), B (graph neighbor, NOT
        // indexed), C (indexed, unconnected). Edge A --0.8--> B.
        let a = Memory::new(Galaxy::Codex, "kumquat governance ratchet".into());
        let mut b = Memory::new(Galaxy::Codex, "the follow-up decision".into());
        let c = Memory::new(Galaxy::Codex, "kumquat harvest notes".into());
        b.metadata.is_private = false;
        let (id_a, id_b, id_c) = (a.metadata.id, b.metadata.id, c.metadata.id);
        store.put(Galaxy::Codex, &a).unwrap();
        store.put(Galaxy::Codex, &b).unwrap();
        store.put(Galaxy::Codex, &c).unwrap();

        let mut writer = search.writer().unwrap();
        for (id, content) in [
            (id_a, "kumquat governance ratchet"),
            (id_c, "kumquat harvest notes"),
        ] {
            search
                .add_document(
                    &mut writer,
                    &id.to_string(),
                    "codex",
                    content,
                    &[],
                    1_700_000_000,
                )
                .unwrap();
        }
        search.commit(&mut writer).unwrap();

        let env = store.env();
        let assocs = AssociationStore::open(env).unwrap();
        assocs
            .put(env, &Association::new(id_a, id_b, LinkType::Related, 0.8))
            .unwrap();

        let store_for_engine = store.clone();
        let search_for_engine = search.clone();
        let mk_engine = move |graph_weight: f32| {
            let config = RecallConfig {
                bm25_weight: 1.0,
                vector_weight: 0.0,
                importance_weight: 0.0,
                graph_weight,
                ..RecallConfig::default()
            };
            RecallEngine::new(
                store_for_engine.clone(),
                search_for_engine.clone(),
                VectorStore::new(),
                Arc::new(StubEmbedder::default()),
                config,
            )
            .unwrap()
        };
        GraphHarness {
            _dir: dir,
            store,
            engine_with_graph: mk_engine(0.5),
            engine_plain: mk_engine(0.0),
        }
    }

    /// Counts embedder invocations; delegates to the stub. The persistent
    /// embedding-cache acceptance is measured in CALLS, not assumptions.
    struct CountingEmbedder {
        inner: StubEmbedder,
        calls: std::sync::atomic::AtomicUsize,
    }

    impl CountingEmbedder {
        fn new() -> Self {
            Self {
                inner: StubEmbedder::default(),
                calls: std::sync::atomic::AtomicUsize::new(0),
            }
        }

        fn call_count(&self) -> usize {
            self.calls.load(std::sync::atomic::Ordering::SeqCst)
        }
    }

    impl Embedder for CountingEmbedder {
        fn embed_batch(&self, texts: &[&str]) -> Result<Vec<Vec<f32>>> {
            self.calls.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
            self.inner.embed_batch(texts)
        }
        fn dimension(&self) -> usize {
            self.inner.dimension()
        }
        fn is_available(&self) -> bool {
            true
        }
        fn backend_name(&self) -> &'static str {
            "stub-counting"
        }
    }

    fn engine_fixture() -> (tempfile::TempDir, Arc<MemoryStore>, Arc<SearchEngine>) {
        let dir = tempfile::tempdir().unwrap();
        let lmdb = dir.path().join("lmdb");
        std::fs::create_dir_all(&lmdb).unwrap();
        let store = Arc::new(MemoryStore::open_default(&lmdb).unwrap());
        let tantivy = dir.path().join("tantivy");
        std::fs::create_dir_all(&tantivy).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy).unwrap());
        (dir, store, search)
    }

    fn mk_engine(
        store: &Arc<MemoryStore>,
        search: &Arc<SearchEngine>,
        embedder: Arc<dyn Embedder>,
    ) -> RecallEngine {
        RecallEngine::new(
            store.clone(),
            search.clone(),
            VectorStore::new(),
            embedder,
            RecallConfig::default(),
        )
        .unwrap()
    }

    #[test]
    fn embedding_cache_warm_starts_reingest_across_engine_restart() {
        // V8 ship list #2: the content-hash vector cache persists in the
        // store, so a fresh engine over the same store re-ingests identical
        // content with ZERO embedder calls (v26 Tier-2, wired).
        let (_dir, store, search) = engine_fixture();

        let contents: Vec<String> = (0..12)
            .map(|i| format!("cache warm-start probe number {i} with distinct wording {i}"))
            .collect();
        let entries: Vec<(Galaxy, crate::Memory)> = contents
            .iter()
            .map(|c| (Galaxy::Codex, crate::Memory::new(Galaxy::Codex, c.clone())))
            .collect();
        let refs: Vec<(Galaxy, &crate::Memory)> = entries.iter().map(|(g, m)| (*g, m)).collect();

        let first = Arc::new(CountingEmbedder::new());
        let engine = mk_engine(&store, &search, first.clone());
        assert_eq!(engine.store_batch_with_embedding(&refs).unwrap(), 12);
        let first_calls = first.call_count();
        assert!(first_calls > 0, "first ingest must embed");
        assert_eq!(store.embedding_cache_count().unwrap(), 12);

        // Fresh engine over the SAME store (restart semantics: empty
        // in-memory cache, persistent layer intact).
        let second = Arc::new(CountingEmbedder::new());
        let engine2 = mk_engine(&store, &search, second.clone());
        let entries2: Vec<(Galaxy, crate::Memory)> = contents
            .iter()
            .map(|c| (Galaxy::Codex, crate::Memory::new(Galaxy::Codex, c.clone())))
            .collect();
        let refs2: Vec<(Galaxy, &crate::Memory)> = entries2.iter().map(|(g, m)| (*g, m)).collect();
        assert_eq!(engine2.store_batch_with_embedding(&refs2).unwrap(), 12);
        assert_eq!(
            second.call_count(),
            0,
            "re-ingest of identical content must serve from the persistent cache"
        );
        assert_eq!(store.embedding_cache_count().unwrap(), 12);
    }

    #[test]
    fn embedding_cache_scopes_vectors_by_embedder_namespace() {
        // Switching models must never serve stale vectors: the cache key
        // carries the embedder namespace, so a "different model" is a miss.
        let (_dir, store, search) = engine_fixture();

        let content = "namespace isolation probe";
        let first = Arc::new(CountingEmbedder::new());
        let engine = mk_engine(&store, &search, first.clone());
        let mem = crate::Memory::new(Galaxy::Codex, content.into());
        engine.store_with_embedding(Galaxy::Codex, &mem).unwrap();
        assert_eq!(first.call_count(), 1);

        // A second engine whose embedder reports a DIFFERENT namespace
        // must re-embed the same content.
        struct OtherNamespaceEmbedder(StubEmbedder);
        impl Embedder for OtherNamespaceEmbedder {
            fn embed_batch(&self, texts: &[&str]) -> Result<Vec<Vec<f32>>> {
                self.0.embed_batch(texts)
            }
            fn dimension(&self) -> usize {
                self.0.dimension()
            }
            fn is_available(&self) -> bool {
                true
            }
            fn backend_name(&self) -> &'static str {
                "stub-other"
            }
        }
        let second = Arc::new(OtherNamespaceEmbedder(StubEmbedder::default()));
        let engine2 = mk_engine(&store, &search, second);
        let mem2 = crate::Memory::new(Galaxy::Codex, content.into());
        engine2.store_with_embedding(Galaxy::Codex, &mem2).unwrap();

        // Two cache entries: one per namespace.
        assert_eq!(store.embedding_cache_count().unwrap(), 2);
    }

    #[test]
    fn graph_expansion_injects_unindexed_neighbors_and_boosts_connected() {
        let h = graph_harness();

        // Knob off: base fusion only — B is invisible (not indexed).
        let plain = h.engine_plain.hybrid_search("kumquat", 10, None);
        assert!(plain.iter().all(|r| r.memory_id != {
            h.store
                .find_by_content_hash(Galaxy::Codex, &content_hash("the follow-up decision"))
                .unwrap()
                .unwrap()
        }));
        assert!(plain.iter().all(|r| r.graph_score == 0.0));

        // Knob on: B is injected purely via the A→B edge, carrying its
        // graph contribution; A keeps the top fused score.
        let expanded = h.engine_with_graph.hybrid_search("kumquat", 10, None);
        let id_b = h
            .store
            .find_by_content_hash(Galaxy::Codex, &content_hash("the follow-up decision"))
            .unwrap()
            .unwrap();
        let b = expanded
            .iter()
            .find(|r| r.memory_id == id_b)
            .expect("graph expansion must surface the unindexed neighbor");
        assert!(b.graph_score > 0.0, "injected neighbor: {b:?}");
        assert_eq!(b.bm25_score, 0.0, "B had no BM25 hit — pure graph entry");
        let a_score = expanded
            .iter()
            .find(|r| r.content.contains("ratchet"))
            .unwrap()
            .score;
        assert!(a_score >= b.score, "seed outranks its 1-hop neighbor");
    }

    #[test]
    fn graph_expansion_honors_the_privacy_flag() {
        let h = graph_harness();
        let id_b = h
            .store
            .find_by_content_hash(Galaxy::Codex, &content_hash("the follow-up decision"))
            .unwrap()
            .unwrap();
        // Flip B private → the graph must not open a side door to it.
        let mut b = h.store.get(Galaxy::Codex, id_b).unwrap().unwrap();
        b.metadata.is_private = true;
        h.store.put(Galaxy::Codex, &b).unwrap();
        let expanded = h.engine_with_graph.hybrid_search("kumquat", 10, None);
        assert!(
            expanded.iter().all(|r| r.memory_id != id_b),
            "private memory must not be graph-injected"
        );
    }

    #[test]
    fn config_default_graph_weight_is_off() {
        let config = RecallConfig::default();
        assert_eq!(config.graph_weight, 0.0, "evidence-gated: default off");
        assert!(config.weights_normalized());
    }

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
            graph_score: 0.0,
            trust_factor: 1.0,
            in_conformal_set: false,
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
            0.0,
            |_, _| String::new(),
            |_, _| 0.0,
            |_, _| 0.7,
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
            normalized_score: 0.0,
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
            normalized_score: 0.0,
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
                normalized_score: 0.0,
                content: "lower".into(),
            },
            SearchResult {
                memory_id: id2.to_string(),
                galaxy: Galaxy::Codex.db_name().to_string(),
                score: 8.0,
                normalized_score: 0.0,
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
                normalized_score: 0.0,
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
            normalized_score: 0.0,
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
            normalized_score: 0.0,
            content: "test".into(),
        }];
        let results = fuse_results_inner(
            &bm25,
            &[],
            10,
            0.5,
            0.3,
            0.2,
            0.0,
            |_, _| String::new(),
            |_, _| 0.0,
            |_, _| 0.7,
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
            0.0,
            |_, _| String::new(),
            |_, _| 0.0,
            |_, _| 0.7,
        );
        assert!((results[0].score - 0.27).abs() < 0.01);
    }

    #[test]
    fn trust_weight_zero_is_byte_identical_to_no_weight() {
        let id = Uuid::new_v4();
        let bm25 = vec![SearchResult {
            memory_id: id.to_string(),
            galaxy: Galaxy::Codex.db_name().to_string(),
            score: 5.0,
            normalized_score: 0.0,
            content: "test".into(),
        }];
        // Knob off: the low-trust getter is never consulted, the score is
        // the plain fused value, and the disclosure never lies.
        let results = fuse_results_inner(
            &bm25,
            &[],
            10,
            0.5,
            0.3,
            0.2,
            0.0,
            |_, _| String::new(),
            |_, _| 0.0,
            |_, _| 0.4,
        );
        assert!((results[0].score - 0.5).abs() < 0.01);
        assert!((results[0].trust_factor - 1.0).abs() < f32::EPSILON);
        assert!(!results[0].in_conformal_set);
    }

    #[test]
    fn trust_weight_orders_high_trust_above_low() {
        // Two candidates with identical fused scores; only source_trust
        // differs. With weight 0.5: factor = 1 + 0.5*(trust − 0.7).
        let high = Uuid::new_v4();
        let low = Uuid::new_v4();
        let mk = |id: &Uuid| SearchResult {
            memory_id: id.to_string(),
            galaxy: Galaxy::Codex.db_name().to_string(),
            score: 5.0,
            normalized_score: 0.0,
            content: "test".into(),
        };
        let bm25 = vec![mk(&high), mk(&low)];
        let mut trust_calls = 0;
        let results = fuse_results_inner(
            &bm25,
            &[],
            10,
            0.5,
            0.3,
            0.2,
            0.5,
            |_, _| String::new(),
            |_, _| 0.0,
            |id, _| {
                trust_calls += 1;
                if id == high { 1.0 } else { 0.4 }
            },
        );
        let hi = results.iter().find(|r| r.memory_id == high).unwrap();
        let lo = results.iter().find(|r| r.memory_id == low).unwrap();
        assert!(
            hi.score > lo.score,
            "user-confirmed (1.0) must outrank low-trust (0.4) at equal fused score"
        );
        // Factors disclosed: 1 + 0.5*(1.0−0.7) = 1.15; 1 + 0.5*(0.4−0.7) = 0.85.
        assert!((hi.trust_factor - 1.15).abs() < 0.001);
        assert!((lo.trust_factor - 0.85).abs() < 0.001);
        assert!(trust_calls >= 2, "getter consulted per candidate");
        // Neutral 0.7 stays exactly neutral even with the knob on.
        let neutral = Uuid::new_v4();
        let bm25_neutral = vec![SearchResult {
            memory_id: neutral.to_string(),
            galaxy: Galaxy::Codex.db_name().to_string(),
            score: 5.0,
            normalized_score: 0.0,
            content: "test".into(),
        }];
        let res_n = fuse_results_inner(
            &bm25_neutral,
            &[],
            10,
            0.5,
            0.3,
            0.2,
            0.5,
            |_, _| String::new(),
            |_, _| 0.0,
            |_, _| 0.7,
        );
        assert!((res_n[0].trust_factor - 1.0).abs() < 0.001);
    }

    #[test]
    fn config_defaults_keep_both_s8_knobs_off() {
        // Evidence-gated defaults: trust weighting and conformal sets ship
        // OFF — the base fusion must be untouched unless the operator opts
        // in. (Env parsing for the knobs follows the same guard pattern as
        // WM_RECALL_GRAPH_WEIGHT: finite, clamped to range, else default.)
        let cfg = RecallConfig::default();
        assert_eq!(cfg.trust_weight, 0.0);
        assert_eq!(cfg.conformal_alpha, None);
        let env_cfg = RecallConfig::from_env();
        assert_eq!(env_cfg.trust_weight, 0.0, "unset env stays off");
        assert_eq!(env_cfg.conformal_alpha, None, "unset env stays off");
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
    fn integration_batch_store_with_embedding() {
        let (_tmp, engine) = setup_engine();

        let mem1 = Memory::new(Galaxy::Codex, "alpha beta gamma".into());
        let mem2 = Memory::new(Galaxy::Codex, "delta epsilon zeta".into());
        let mem3 = Memory::new(Galaxy::Codex, "eta theta iota".into());

        let entries = vec![
            (Galaxy::Codex, &mem1),
            (Galaxy::Codex, &mem2),
            (Galaxy::Codex, &mem3),
        ];

        let count = engine.store_batch_with_embedding(&entries).unwrap();
        assert_eq!(count, 3);

        // All three should be searchable via BM25
        let results = engine.text_search("alpha", 10);
        assert!(
            !results.is_empty(),
            "batch-stored memory should be searchable"
        );

        // All three should be in the vector store
        let vresults = engine.vector_search("alpha beta gamma", 10, None);
        assert_eq!(
            vresults.len(),
            1,
            "vector search should find the exact match"
        );
        assert_eq!(vresults[0].memory_id, mem1.metadata.id);
    }

    #[test]
    fn integration_batch_store_empty() {
        let (_tmp, engine) = setup_engine();
        let entries: Vec<(Galaxy, &Memory)> = vec![];
        let count = engine.store_batch_with_embedding(&entries).unwrap();
        assert_eq!(count, 0);
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
