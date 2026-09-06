//! Vector store — cosine similarity search over memory embeddings.
//!
//! Provides true vector similarity search using embeddings stored in the
//! Embeddings galaxy (LMDB). Builds an in-memory index from all stored
//! embeddings for fast cosine similarity lookups.
//!
//! For small-to-medium datasets (<100K memories), brute-force cosine
//! similarity is fast enough (sub-millisecond for 10K vectors at 384 dims).
//! For larger datasets, LanceDB can be added as an optional backend.

use ahash::AHashMap;
use lmdb::{Cursor, Transaction};
use uuid::Uuid;
use wm_core::{CoreError, Galaxy, Result};

use crate::MemoryStore;

/// A vector search result.
#[derive(Debug, Clone)]
pub struct VectorSearchResult {
    /// Memory UUID
    pub memory_id: Uuid,
    /// Galaxy the memory belongs to
    pub galaxy: Galaxy,
    /// Cosine similarity score (0.0 to 1.0, higher = more similar)
    pub score: f32,
}

/// Trait for pluggable vector search backends.
///
/// Implemented by:
/// - `VectorStore` — in-memory brute-force cosine similarity (default)
/// - `LanceVectorStore` — LanceDB-backed ANN search (feature-gated under `lancedb`)
pub trait VectorSearchEngine: Send + Sync {
    /// Add a vector to the index.
    fn add_vector(&mut self, memory_id: Uuid, galaxy: Galaxy, embedding: Vec<f32>);

    /// Remove a vector from the index.
    fn remove_vector(&mut self, memory_id: Uuid) -> bool;

    /// Search for the most similar vectors to a query embedding.
    ///
    /// Returns results sorted by similarity (highest first).
    /// Optionally filter by galaxy.
    fn search_vectors(
        &self,
        query: &[f32],
        limit: usize,
        galaxy_filter: Option<Galaxy>,
    ) -> Vec<VectorSearchResult>;

    /// Search for similar vectors to a memory's own embedding.
    ///
    /// Excludes the memory itself from results.
    fn search_similar_vectors(&self, memory_id: Uuid, limit: usize) -> Vec<VectorSearchResult>;

    /// Get the number of indexed vectors.
    fn vector_count(&self) -> usize;

    /// Whether the index is empty.
    fn is_index_empty(&self) -> bool {
        self.vector_count() == 0
    }

    /// Load all embeddings from the LMDB Embeddings galaxy.
    fn load_vectors(&mut self, store: &MemoryStore) -> Result<()>;

    /// Clear the index.
    fn clear_vectors(&mut self);
}

/// In-memory vector index for fast cosine similarity search.
///
/// Loads all embeddings from the Embeddings galaxy into memory on first access.
/// Supports incremental updates (add/remove vectors without full rebuild).
pub struct VectorStore {
    /// Indexed vectors: (memory_id, galaxy, embedding)
    vectors: AHashMap<Uuid, (Galaxy, Vec<f32>)>,
    /// Whether the index has been loaded from LMDB
    loaded: bool,
}

impl VectorStore {
    /// Create a new empty vector store.
    #[must_use]
    pub fn new() -> Self {
        Self {
            vectors: AHashMap::new(),
            loaded: false,
        }
    }

    /// Load all embeddings from the LMDB Embeddings galaxy into memory.
    ///
    /// This scans the Embeddings galaxy and loads all stored embedding vectors.
    /// Must be called before `search` if vectors were stored directly via
    /// `MemoryStore::put_embedding` without going through `add`.
    pub fn load(&mut self, store: &MemoryStore) -> Result<()> {
        let db = store.galaxy_db(Galaxy::Embeddings)?;

        // Pass 1: Collect all embeddings from LMDB within a single read txn
        let mut entries: Vec<(Uuid, Vec<f32>)> = Vec::new();
        {
            let tx = store
                .env()
                .begin_ro_txn()
                .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;

            let mut cursor = tx
                .open_ro_cursor(db)
                .map_err(|e| CoreError::Memory(format!("LMDB cursor failed: {e}")))?;

            for (key, val) in cursor.iter() {
                if key.len() == 16 {
                    let bytes: [u8; 16] = key.try_into().unwrap_or([0u8; 16]);
                    let id = Uuid::from_bytes(bytes);
                    let embedding = crate::memory::decode_embedding(val);
                    entries.push((id, embedding));
                }
            }

            drop(cursor);
            tx.commit()
                .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        }

        // Pass 2: Look up galaxy for each embedding (separate txn per lookup)
        let mut count = 0;
        for (id, embedding) in entries {
            match self.find_memory_galaxy(store, id) {
                Some(galaxy) => {
                    self.vectors.insert(id, (galaxy, embedding));
                    count += 1;
                }
                None => {
                    tracing::warn!(
                        "Skipping orphaned embedding (memory not found in any galaxy, id={})",
                        id
                    );
                }
            }
        }

        self.loaded = true;
        tracing::info!("Loaded {count} embedding vectors into VectorStore");
        Ok(())
    }

    /// Find which galaxy a memory belongs to by scanning all galaxies.
    fn find_memory_galaxy(&self, store: &MemoryStore, id: Uuid) -> Option<Galaxy> {
        for galaxy in Galaxy::all() {
            if galaxy == Galaxy::Embeddings {
                continue;
            }
            if store.get(galaxy, id).ok().flatten().is_some() {
                return Some(galaxy);
            }
        }
        None
    }

    /// Add a vector to the index.
    pub fn add(&mut self, memory_id: Uuid, galaxy: Galaxy, embedding: Vec<f32>) {
        self.vectors.insert(memory_id, (galaxy, embedding));
    }

    /// Remove a vector from the index.
    pub fn remove(&mut self, memory_id: Uuid) -> bool {
        self.vectors.remove(&memory_id).is_some()
    }

    /// Get the number of indexed vectors.
    #[must_use]
    pub fn len(&self) -> usize {
        self.vectors.len()
    }

    /// Check if the index is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.vectors.is_empty()
    }

    /// Whether the index has been loaded from LMDB.
    #[must_use]
    pub const fn is_loaded(&self) -> bool {
        self.loaded
    }

    /// Search for the most similar vectors to a query embedding.
    ///
    /// Returns results sorted by cosine similarity (highest first).
    /// Optionally filter by galaxy.
    #[must_use]
    pub fn search(
        &self,
        query: &[f32],
        limit: usize,
        galaxy_filter: Option<Galaxy>,
    ) -> Vec<VectorSearchResult> {
        if self.vectors.is_empty() || query.is_empty() {
            return Vec::new();
        }

        let query_norm = vector_norm(query);
        if query_norm == 0.0 {
            return Vec::new();
        }

        let mut results: Vec<VectorSearchResult> = self
            .vectors
            .iter()
            .filter(|(_, (galaxy, _))| galaxy_filter.is_none_or(|g| g == *galaxy))
            .filter_map(|(id, (galaxy, embedding))| {
                let score = cosine_similarity(query, embedding, query_norm);
                if score > 0.0 {
                    Some(VectorSearchResult {
                        memory_id: *id,
                        galaxy: *galaxy,
                        score,
                    })
                } else {
                    None
                }
            })
            .collect();

        results.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        results.truncate(limit);
        results
    }

    /// Search for similar vectors to a memory's own embedding.
    ///
    /// Excludes the memory itself from results.
    #[must_use]
    pub fn search_similar_to(&self, memory_id: Uuid, limit: usize) -> Vec<VectorSearchResult> {
        let (galaxy, embedding) = match self.vectors.get(&memory_id) {
            Some(v) => v,
            None => return Vec::new(),
        };

        let query_norm = vector_norm(embedding);
        if query_norm == 0.0 {
            return Vec::new();
        }

        let mut results: Vec<VectorSearchResult> = self
            .vectors
            .iter()
            .filter(|(id, _)| **id != memory_id)
            .filter_map(|(id, (g, emb))| {
                let score = cosine_similarity(embedding, emb, query_norm);
                if score > 0.0 {
                    Some(VectorSearchResult {
                        memory_id: *id,
                        galaxy: *g,
                        score,
                    })
                } else {
                    None
                }
            })
            .collect();

        let _ = galaxy; // galaxy filter not applied for similar-to
        results.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        results.truncate(limit);
        results
    }

    /// Clear the index.
    pub fn clear(&mut self) {
        self.vectors.clear();
        self.loaded = false;
    }
}

impl Default for VectorStore {
    fn default() -> Self {
        Self::new()
    }
}

impl VectorSearchEngine for VectorStore {
    fn add_vector(&mut self, memory_id: Uuid, galaxy: Galaxy, embedding: Vec<f32>) {
        self.add(memory_id, galaxy, embedding);
    }

    fn remove_vector(&mut self, memory_id: Uuid) -> bool {
        self.remove(memory_id)
    }

    fn search_vectors(
        &self,
        query: &[f32],
        limit: usize,
        galaxy_filter: Option<Galaxy>,
    ) -> Vec<VectorSearchResult> {
        self.search(query, limit, galaxy_filter)
    }

    fn search_similar_vectors(&self, memory_id: Uuid, limit: usize) -> Vec<VectorSearchResult> {
        self.search_similar_to(memory_id, limit)
    }

    fn vector_count(&self) -> usize {
        self.len()
    }

    fn load_vectors(&mut self, store: &MemoryStore) -> Result<()> {
        self.load(store)
    }

    fn clear_vectors(&mut self) {
        self.clear();
    }
}

/// Compute the L2 norm of a vector.
fn vector_norm(v: &[f32]) -> f32 {
    v.iter().map(|x| x * x).sum::<f32>().sqrt()
}

/// Compute cosine similarity between two vectors.
///
/// `query_norm` is pre-computed for the query vector to avoid redundant
/// calculations when searching against many vectors.
fn cosine_similarity(query: &[f32], target: &[f32], query_norm: f32) -> f32 {
    if query.len() != target.len() {
        return 0.0;
    }

    let dot: f32 = query.iter().zip(target.iter()).map(|(a, b)| a * b).sum();

    let target_norm = vector_norm(target);
    if target_norm == 0.0 {
        return 0.0;
    }

    dot / (query_norm * target_norm)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Memory;

    #[test]
    fn vector_store_empty_search() {
        let vs = VectorStore::new();
        let results = vs.search(&[1.0, 0.0, 0.0], 10, None);
        assert!(results.is_empty());
    }

    #[test]
    fn vector_store_add_and_search() {
        let mut vs = VectorStore::new();
        let id1 = Uuid::new_v4();
        let id2 = Uuid::new_v4();
        let id3 = Uuid::new_v4();

        vs.add(id1, Galaxy::Codex, vec![1.0, 0.0, 0.0]);
        vs.add(id2, Galaxy::Codex, vec![0.0, 1.0, 0.0]);
        vs.add(id3, Galaxy::Codex, vec![1.0, 1.0, 0.0]);

        let results = vs.search(&[1.0, 0.0, 0.0], 10, None);
        assert_eq!(results.len(), 2); // id1 and id3 have positive similarity
        assert_eq!(results[0].memory_id, id1);
        assert!((results[0].score - 1.0).abs() < 0.001); // exact match
    }

    #[test]
    fn vector_store_search_with_limit() {
        let mut vs = VectorStore::new();
        for _ in 0..10 {
            vs.add(Uuid::new_v4(), Galaxy::Codex, vec![1.0, 0.0, 0.0]);
        }
        let results = vs.search(&[1.0, 0.0, 0.0], 3, None);
        assert_eq!(results.len(), 3);
    }

    #[test]
    fn vector_store_galaxy_filter() {
        let mut vs = VectorStore::new();
        vs.add(Uuid::new_v4(), Galaxy::Codex, vec![1.0, 0.0]);
        vs.add(Uuid::new_v4(), Galaxy::Research, vec![1.0, 0.0]);
        vs.add(Uuid::new_v4(), Galaxy::Codex, vec![0.9, 0.1]);

        let results = vs.search(&[1.0, 0.0], 10, Some(Galaxy::Codex));
        assert_eq!(results.len(), 2);
        assert!(results.iter().all(|r| r.galaxy == Galaxy::Codex));
    }

    #[test]
    fn vector_store_search_similar_to() {
        let mut vs = VectorStore::new();
        let id1 = Uuid::new_v4();
        let id2 = Uuid::new_v4();
        let id3 = Uuid::new_v4();

        vs.add(id1, Galaxy::Codex, vec![1.0, 0.0, 0.0]);
        vs.add(id2, Galaxy::Codex, vec![0.95, 0.05, 0.0]);
        vs.add(id3, Galaxy::Codex, vec![0.0, 1.0, 0.0]);

        let results = vs.search_similar_to(id1, 10);
        // id3 is orthogonal (cosine sim = 0.0), so only id2 has positive similarity
        assert_eq!(results.len(), 1);
        assert!(results.iter().all(|r| r.memory_id != id1));
        assert_eq!(results[0].memory_id, id2); // most similar
    }

    #[test]
    fn vector_store_remove() {
        let mut vs = VectorStore::new();
        let id = Uuid::new_v4();
        vs.add(id, Galaxy::Codex, vec![1.0, 0.0]);
        assert_eq!(vs.len(), 1);
        assert!(vs.remove(id));
        assert_eq!(vs.len(), 0);
        assert!(!vs.remove(id));
    }

    #[test]
    fn vector_store_clear() {
        let mut vs = VectorStore::new();
        vs.add(Uuid::new_v4(), Galaxy::Codex, vec![1.0]);
        vs.add(Uuid::new_v4(), Galaxy::Codex, vec![1.0]);
        assert_eq!(vs.len(), 2);
        vs.clear();
        assert_eq!(vs.len(), 0);
        assert!(!vs.is_loaded());
    }

    #[test]
    fn vector_store_zero_query_returns_empty() {
        let mut vs = VectorStore::new();
        vs.add(Uuid::new_v4(), Galaxy::Codex, vec![1.0, 0.0]);
        let results = vs.search(&[0.0, 0.0], 10, None);
        assert!(results.is_empty());
    }

    #[test]
    fn vector_store_mismatched_dimensions() {
        let mut vs = VectorStore::new();
        vs.add(Uuid::new_v4(), Galaxy::Codex, vec![1.0, 0.0, 0.0]);
        let results = vs.search(&[1.0, 0.0], 10, None);
        assert!(results.is_empty()); // dimension mismatch → score 0.0
    }

    #[test]
    fn cosine_similarity_exact_match() {
        let sim = cosine_similarity(&[1.0, 0.0, 0.0], &[1.0, 0.0, 0.0], 1.0);
        assert!((sim - 1.0).abs() < 0.001);
    }

    #[test]
    fn cosine_similarity_orthogonal() {
        let sim = cosine_similarity(&[1.0, 0.0], &[0.0, 1.0], 1.0);
        assert!(sim.abs() < 0.001);
    }

    #[test]
    fn cosine_similarity_45_degrees() {
        let sim = cosine_similarity(&[1.0, 0.0], &[1.0, 1.0], 1.0);
        assert!((sim - std::f32::consts::FRAC_1_SQRT_2).abs() < 0.01);
    }

    #[test]
    fn vector_store_load_from_lmdb() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        // Create a memory and store its embedding
        let mem = Memory::new(Galaxy::Codex, "test content".into());
        store.put(Galaxy::Codex, &mem).unwrap();
        store
            .put_embedding(mem.metadata.id, &[0.1, 0.2, 0.3])
            .unwrap();

        // Load the vector store
        let mut vs = VectorStore::new();
        vs.load(&store).unwrap();
        assert_eq!(vs.len(), 1);
        assert!(vs.is_loaded());

        // Search should find it
        let results = vs.search(&[0.1, 0.2, 0.3], 10, None);
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].memory_id, mem.metadata.id);
    }

    #[test]
    fn vector_store_load_multiple_embeddings() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        // Store multiple memories with embeddings
        for i in 0..5 {
            let mem = Memory::new(Galaxy::Codex, format!("content {i}"));
            store.put(Galaxy::Codex, &mem).unwrap();
            let embedding = vec![i as f32 * 0.1, (i as f32).mul_add(-0.1, 1.0), 0.5];
            store.put_embedding(mem.metadata.id, &embedding).unwrap();
        }

        let mut vs = VectorStore::new();
        vs.load(&store).unwrap();
        assert_eq!(vs.len(), 5);
    }

    #[test]
    fn vector_store_load_empty() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mut vs = VectorStore::new();
        vs.load(&store).unwrap();
        assert_eq!(vs.len(), 0);
        assert!(vs.is_loaded());
    }
}
