//! LanceDB-backed vector store — disk-based ANN similarity search.
//!
//! Provides scalable approximate nearest neighbor search using LanceDB's
//! IVF-PQ index. Suitable for datasets exceeding 100K vectors where the
//! in-memory `VectorStore` becomes too slow or memory-hungry.
//!
//! This module is feature-gated under the `lancedb` feature. Enable with:
//! ```toml
//! wm-memory = { features = ["lancedb"] }
//! ```
//!
//! # Architecture
//!
//! - Vectors stored in a LanceDB table on disk (columnar Lance format)
//! - Schema: `id` (Utf8), `galaxy` (Utf8), `vector` (FixedSizeList<f32, dim>)
//! - IVF-PQ index created automatically when the table has enough vectors
//! - Galaxy filtering via SQL-style `only_if` predicates
//! - Async LanceDB calls bridged to sync via `block_in_place` or dedicated runtime

#![allow(clippy::cast_possible_wrap)]

use std::sync::Arc;

use arrow_array::{
    Array, FixedSizeListArray, RecordBatch, RecordBatchIterator, StringArray, types::Float32Type,
};
use arrow_schema::{DataType, Field, Schema};
use futures::TryStreamExt;
use lancedb::{
    connect,
    index::Index,
    query::{ExecutableQuery, QueryBase},
    table::Table,
};
use uuid::Uuid;
use wm_core::{CoreError, Galaxy, Result};

use crate::MemoryStore;
use crate::vector::{VectorSearchEngine, VectorSearchResult};

/// LanceDB-backed vector store for scalable ANN similarity search.
///
/// Stores embedding vectors on disk in LanceDB's columnar format with
/// IVF-PQ indexing for sub-millisecond approximate nearest neighbor search
/// on datasets of 100K+ vectors.
pub struct LanceVectorStore {
    /// LanceDB connection
    db: lancedb::Connection,
    /// Table name (fixed: "embeddings")
    table_name: String,
    /// Vector dimensionality (must be consistent across all vectors)
    dim: usize,
    /// Path to the LanceDB directory on disk
    path: std::path::PathBuf,
    /// Whether the table has been created/loaded
    initialized: bool,
}

impl LanceVectorStore {
    /// Open or create a LanceDB vector store at the given path.
    ///
    /// The `dim` parameter specifies the dimensionality of vectors.
    /// All vectors added to this store must have the same dimension.
    ///
    /// # Errors
    /// Returns an error if the LanceDB connection cannot be established.
    pub fn open(path: impl AsRef<std::path::Path>, dim: usize) -> Result<Self> {
        let path = path.as_ref().to_path_buf();
        let path_str = path
            .to_str()
            .ok_or_else(|| CoreError::Memory("LanceDB path not valid UTF-8".into()))?;

        let db = block_on_async(connect(path_str).execute())
            .map_err(|e| CoreError::Memory(format!("LanceDB connect failed: {e}")))?;

        Ok(Self {
            db,
            table_name: "embeddings".to_string(),
            dim,
            path,
            initialized: false,
        })
    }

    /// Get the vector dimensionality.
    #[must_use]
    pub const fn dimension(&self) -> usize {
        self.dim
    }

    /// Get the LanceDB directory path.
    #[must_use]
    pub fn path(&self) -> &std::path::Path {
        &self.path
    }

    /// Open or create the LanceDB table if not already initialized.
    fn ensure_table(&mut self) -> Result<()> {
        if self.initialized {
            return Ok(());
        }

        let table_exists = block_on_async(self.db.table_names().execute())
            .map_err(|e| CoreError::Memory(format!("LanceDB table_names failed: {e}")))?
            .iter()
            .any(|name| name == &self.table_name);

        if table_exists {
            self.initialized = true;
            return Ok(());
        }

        // Create empty table with schema
        let schema = Arc::new(Schema::new(vec![
            Field::new("id", DataType::Utf8, false),
            Field::new("galaxy", DataType::Utf8, false),
            Field::new(
                "vector",
                DataType::FixedSizeList(
                    Arc::new(Field::new("item", DataType::Float32, true)),
                    self.dim as i32,
                ),
                true,
            ),
        ]));

        let empty_batch = RecordBatch::new_empty(schema.clone());
        let reader = RecordBatchIterator::new(vec![Ok(empty_batch)].into_iter(), schema);

        block_on_async(
            self.db
                .create_table(
                    &self.table_name,
                    Box::new(reader) as Box<dyn arrow_array::RecordBatchReader + Send>,
                )
                .execute(),
        )
        .map_err(|e| CoreError::Memory(format!("LanceDB create_table failed: {e}")))?;

        self.initialized = true;
        Ok(())
    }

    /// Get a handle to the LanceDB table.
    fn table(&self) -> Result<Table> {
        block_on_async(self.db.open_table(&self.table_name).execute())
            .map_err(|e| CoreError::Memory(format!("LanceDB open_table failed: {e}")))
    }

    /// Create an IVF-PQ index on the vector column if one doesn't exist.
    ///
    /// This should be called after bulk-loading vectors for optimal search
    /// performance. LanceDB auto-creates indexes on `nearest_to` queries
    /// if an index exists, otherwise it falls back to brute-force scan.
    pub fn create_index(&mut self) -> Result<()> {
        self.ensure_table()?;
        let table = self.table()?;
        block_on_async(table.create_index(&["vector"], Index::Auto).execute())
            .map_err(|e| CoreError::Memory(format!("LanceDB create_index failed: {e}")))?;
        Ok(())
    }

    /// Build a RecordBatch from a batch of (id, galaxy, vector) tuples.
    fn build_batch(
        &self,
        rows: &[(String, String, Vec<f32>)],
    ) -> Result<(RecordBatch, Arc<Schema>)> {
        let schema = Arc::new(Schema::new(vec![
            Field::new("id", DataType::Utf8, false),
            Field::new("galaxy", DataType::Utf8, false),
            Field::new(
                "vector",
                DataType::FixedSizeList(
                    Arc::new(Field::new("item", DataType::Float32, true)),
                    self.dim as i32,
                ),
                true,
            ),
        ]));

        let ids: Vec<&str> = rows.iter().map(|(id, _, _)| id.as_str()).collect();
        let galaxies: Vec<&str> = rows.iter().map(|(_, g, _)| g.as_str()).collect();
        let vectors: Vec<Option<Vec<Option<f32>>>> = rows
            .iter()
            .map(|(_, _, v)| {
                if v.len() != self.dim {
                    return None;
                }
                Some(v.iter().map(|x| Some(*x)).collect())
            })
            .collect();

        let id_array = StringArray::from(ids);
        let galaxy_array = StringArray::from(galaxies);
        let vector_array =
            FixedSizeListArray::from_iter_primitive::<Float32Type, _, _>(vectors, self.dim as i32);

        let batch = RecordBatch::try_new(
            schema.clone(),
            vec![
                Arc::new(id_array),
                Arc::new(galaxy_array),
                Arc::new(vector_array),
            ],
        )
        .map_err(|e| CoreError::Memory(format!("Arrow RecordBatch failed: {e}")))?;
        Ok((batch, schema))
    }

    /// Parse search results from a LanceDB query stream.
    fn parse_results(batches: Vec<RecordBatch>) -> Vec<VectorSearchResult> {
        let mut results = Vec::new();
        for batch in batches {
            let num_rows = batch.num_rows();
            let id_col = batch
                .column_by_name("id")
                .and_then(|c| c.as_any().downcast_ref::<StringArray>());
            let galaxy_col = batch
                .column_by_name("galaxy")
                .and_then(|c| c.as_any().downcast_ref::<StringArray>());

            // The _distance column is 1 - cosine_similarity in LanceDB
            let dist_col = batch
                .column_by_name("_distance")
                .and_then(|c| c.as_any().downcast_ref::<arrow_array::Float32Array>());

            if let (Some(ids), Some(galaxies), Some(distances)) = (id_col, galaxy_col, dist_col) {
                for i in 0..num_rows {
                    let id_str = ids.value(i);
                    let galaxy_str = galaxies.value(i);
                    let distance = distances.value(i);

                    if let Ok(uuid) = Uuid::parse_str(id_str) {
                        if let Some(galaxy) = Galaxy::from_db_name(galaxy_str) {
                            // LanceDB returns distance (1 - similarity), convert back
                            let score = (1.0 - distance).max(0.0);
                            results.push(VectorSearchResult {
                                memory_id: uuid,
                                galaxy,
                                score,
                            });
                        }
                    }
                }
            }
        }
        // Sort by score descending
        results.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        results
    }
}

impl VectorSearchEngine for LanceVectorStore {
    fn add_vector(&mut self, memory_id: Uuid, galaxy: Galaxy, embedding: Vec<f32>) {
        if embedding.len() != self.dim {
            tracing::warn!(
                "Vector dimension mismatch: expected {}, got {}",
                self.dim,
                embedding.len()
            );
            return;
        }

        if let Err(e) = self.ensure_table() {
            tracing::error!("LanceDB ensure_table failed: {e}");
            return;
        }

        let table = match self.table() {
            Ok(t) => t,
            Err(e) => {
                tracing::error!("LanceDB table open failed: {e}");
                return;
            }
        };

        let rows = vec![(
            memory_id.to_string(),
            galaxy.db_name().to_string(),
            embedding,
        )];

        let (batch, schema) = match self.build_batch(&rows) {
            Ok(bs) => bs,
            Err(e) => {
                tracing::error!("LanceDB batch build failed: {e}");
                return;
            }
        };

        let reader = RecordBatchIterator::new(vec![Ok(batch)].into_iter(), schema);

        if let Err(e) = block_on_async(
            table
                .add(Box::new(reader) as Box<dyn arrow_array::RecordBatchReader + Send>)
                .execute(),
        ) {
            tracing::error!("LanceDB add failed: {e}");
        }
    }

    fn remove_vector(&mut self, memory_id: Uuid) -> bool {
        let table = match self.table() {
            Ok(t) => t,
            Err(_) => return false,
        };

        let filter = format!("id = '{memory_id}'");
        block_on_async(table.delete(&filter)).is_ok()
    }

    fn search_vectors(
        &self,
        query: &[f32],
        limit: usize,
        galaxy_filter: Option<Galaxy>,
    ) -> Vec<VectorSearchResult> {
        if query.len() != self.dim || query.is_empty() {
            return Vec::new();
        }

        let table = match self.table() {
            Ok(t) => t,
            Err(_) => return Vec::new(),
        };

        let mut base_query = table.query();

        if let Some(galaxy) = galaxy_filter {
            let filter = format!("galaxy = '{}'", galaxy.db_name());
            base_query = base_query.only_if(filter);
        }

        let query_builder = match base_query.nearest_to(query) {
            Ok(qb) => qb.limit(limit),
            Err(e) => {
                tracing::error!("LanceDB nearest_to failed: {e}");
                return Vec::new();
            }
        };

        // Combine execute + collect in a single async block to avoid
        // cross-runtime task cancellation
        let result = block_on_async(async {
            let stream = query_builder.execute().await?;
            stream.try_collect::<Vec<RecordBatch>>().await
        });

        let batches = match result {
            Ok(b) => b,
            Err(e) => {
                tracing::error!("LanceDB search failed: {e}");
                return Vec::new();
            }
        };

        Self::parse_results(batches)
    }

    fn search_similar_vectors(&self, memory_id: Uuid, limit: usize) -> Vec<VectorSearchResult> {
        let table = match self.table() {
            Ok(t) => t,
            Err(_) => return Vec::new(),
        };

        // First, retrieve the memory's own vector
        let filter = format!("id = '{memory_id}'");
        let result = block_on_async(async {
            let stream = table.query().only_if(filter).limit(1).execute().await?;
            stream.try_collect::<Vec<RecordBatch>>().await
        });

        let batches: Vec<RecordBatch> = match result {
            Ok(b) => b,
            Err(_) => return Vec::new(),
        };

        if batches.is_empty() {
            return Vec::new();
        }

        // Extract the vector from the first row
        let batch = &batches[0];
        let vector_col = batch.column_by_name("vector");
        let query_vec: Vec<f32> = match vector_col {
            Some(col) => {
                if let Some(fsl) = col.as_any().downcast_ref::<FixedSizeListArray>() {
                    if fsl.len() > 0 {
                        let row = fsl.value(0);
                        if let Some(floats) =
                            row.as_any().downcast_ref::<arrow_array::Float32Array>()
                        {
                            (0..floats.len()).map(|i| floats.value(i)).collect()
                        } else {
                            return Vec::new();
                        }
                    } else {
                        return Vec::new();
                    }
                } else {
                    return Vec::new();
                }
            }
            None => return Vec::new(),
        };

        // Now search for similar vectors, excluding the source memory
        let results = self.search_vectors(&query_vec, limit + 1, None);
        results
            .into_iter()
            .filter(|r| r.memory_id != memory_id)
            .take(limit)
            .collect()
    }

    fn vector_count(&self) -> usize {
        let table = match self.table() {
            Ok(t) => t,
            Err(_) => return 0,
        };

        block_on_async(table.count_rows(None)).unwrap_or(0)
    }

    fn load_vectors(&mut self, store: &MemoryStore) -> Result<()> {
        self.ensure_table()?;

        // Read all embeddings from LMDB
        use lmdb::{Cursor, Transaction};
        let db = store.galaxy_db(Galaxy::Embeddings)?;

        // Pass 1: Collect all embeddings within a single read txn
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

                    if embedding.len() != self.dim {
                        tracing::warn!(
                            "Skipping embedding with wrong dim: expected {}, got {}",
                            self.dim,
                            embedding.len()
                        );
                        continue;
                    }
                    entries.push((id, embedding));
                }
            }

            drop(cursor);
            let _ = tx.commit();
        }

        // Pass 2: Look up galaxy for each embedding (separate txn per lookup)
        let mut rows: Vec<(String, String, Vec<f32>)> = Vec::new();
        for (id, embedding) in entries {
            let galaxy = Galaxy::all()
                .into_iter()
                .filter(|g| *g != Galaxy::Embeddings)
                .find(|&g| store.get(g, id).ok().flatten().is_some());

            match galaxy {
                Some(g) => {
                    rows.push((id.to_string(), g.db_name().to_string(), embedding));
                }
                None => {
                    tracing::warn!(
                        "Skipping orphaned embedding (memory not found in any galaxy, id={})",
                        id
                    );
                }
            }
        }

        if rows.is_empty() {
            tracing::info!("No embeddings found in LMDB to load into LanceDB");
            return Ok(());
        }

        // Bulk insert into LanceDB
        let table = self.table()?;
        let (batch, schema) = self.build_batch(&rows)?;
        let reader = RecordBatchIterator::new(vec![Ok(batch)].into_iter(), schema);

        block_on_async(
            table
                .add(Box::new(reader) as Box<dyn arrow_array::RecordBatchReader + Send>)
                .execute(),
        )
        .map_err(|e| CoreError::Memory(format!("LanceDB bulk load failed: {e}")))?;

        tracing::info!("Loaded {} embeddings into LanceDB", rows.len());
        Ok(())
    }

    fn clear_vectors(&mut self) {
        // Drop and recreate the table
        let _ = block_on_async(self.db.drop_table(&self.table_name, &[]));
        self.initialized = false;
    }
}

/// Bridge async LanceDB calls to sync context.
///
/// Uses `tokio::task::block_in_place` when inside a multi-threaded tokio
/// runtime (e.g., the MCP server's event loop), or creates a dedicated
/// runtime when called from a sync context.
fn block_on_async<F: std::future::Future>(fut: F) -> F::Output {
    if let Ok(handle) = tokio::runtime::Handle::try_current() {
        // We're inside a tokio runtime — use block_in_place
        tokio::task::block_in_place(|| handle.block_on(fut))
    } else {
        // Not in a runtime — create a temporary one
        let rt =
            tokio::runtime::Runtime::new().expect("Failed to create tokio runtime for LanceDB");
        rt.block_on(fut)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Memory;

    #[test]
    fn lance_vector_open_and_search() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = LanceVectorStore::open(tmp.path().join("lancedb"), 3).unwrap();

        let id1 = Uuid::new_v4();
        let id2 = Uuid::new_v4();
        let id3 = Uuid::new_v4();

        store.add_vector(id1, Galaxy::Codex, vec![1.0, 0.0, 0.0]);
        store.add_vector(id2, Galaxy::Codex, vec![0.0, 1.0, 0.0]);
        store.add_vector(id3, Galaxy::Codex, vec![1.0, 1.0, 0.0]);

        let results = store.search_vectors(&[1.0, 0.0, 0.0], 10, None);
        assert!(!results.is_empty());
        // id1 should be most similar (exact match)
        assert_eq!(results[0].memory_id, id1);
        assert!((results[0].score - 1.0).abs() < 0.01);
    }

    #[test]
    fn lance_vector_galaxy_filter() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = LanceVectorStore::open(tmp.path().join("lancedb"), 2).unwrap();

        store.add_vector(Uuid::new_v4(), Galaxy::Codex, vec![1.0, 0.0]);
        store.add_vector(Uuid::new_v4(), Galaxy::Research, vec![1.0, 0.0]);
        store.add_vector(Uuid::new_v4(), Galaxy::Codex, vec![0.9, 0.1]);

        let results = store.search_vectors(&[1.0, 0.0], 10, Some(Galaxy::Codex));
        assert!(results.iter().all(|r| r.galaxy == Galaxy::Codex));
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn lance_vector_empty_search() {
        let tmp = tempfile::tempdir().unwrap();
        let store = LanceVectorStore::open(tmp.path().join("lancedb"), 3).unwrap();
        let results = store.search_vectors(&[1.0, 0.0, 0.0], 10, None);
        assert!(results.is_empty());
    }

    #[test]
    fn lance_vector_dimension_mismatch() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = LanceVectorStore::open(tmp.path().join("lancedb"), 3).unwrap();
        store.add_vector(Uuid::new_v4(), Galaxy::Codex, vec![1.0, 0.0]); // wrong dim
        let results = store.search_vectors(&[1.0, 0.0, 0.0], 10, None);
        assert!(results.is_empty());
    }

    #[test]
    fn lance_vector_remove() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = LanceVectorStore::open(tmp.path().join("lancedb"), 2).unwrap();
        let id = Uuid::new_v4();
        store.add_vector(id, Galaxy::Codex, vec![1.0, 0.0]);
        assert!(!store.is_index_empty());
        assert!(store.remove_vector(id));
    }

    #[test]
    fn lance_vector_search_similar() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = LanceVectorStore::open(tmp.path().join("lancedb"), 3).unwrap();

        let id1 = Uuid::new_v4();
        let id2 = Uuid::new_v4();
        let id3 = Uuid::new_v4();

        store.add_vector(id1, Galaxy::Codex, vec![1.0, 0.0, 0.0]);
        store.add_vector(id2, Galaxy::Codex, vec![0.95, 0.05, 0.0]);
        store.add_vector(id3, Galaxy::Codex, vec![0.0, 1.0, 0.0]);

        let results = store.search_similar_vectors(id1, 10);
        assert!(!results.is_empty());
        assert!(results.iter().all(|r| r.memory_id != id1));
        // id2 should be most similar to id1
        assert_eq!(results[0].memory_id, id2);
    }

    #[test]
    fn lance_vector_load_from_lmdb() {
        let tmp = tempfile::tempdir().unwrap();
        let mem_store = MemoryStore::open_default(tmp.path()).unwrap();

        // Create memories with embeddings
        for i in 0..5 {
            let mem = Memory::new(Galaxy::Codex, format!("content {i}"));
            mem_store.put(Galaxy::Codex, &mem).unwrap();
            let embedding = vec![i as f32 * 0.1, (i as f32).mul_add(-0.1, 1.0), 0.5];
            mem_store
                .put_embedding(mem.metadata.id, &embedding)
                .unwrap();
        }

        let mut lance = LanceVectorStore::open(tmp.path().join("lancedb"), 3).unwrap();
        lance.load_vectors(&mem_store).unwrap();

        let results = lance.search_vectors(&[0.0, 1.0, 0.5], 10, None);
        assert!(!results.is_empty());
    }

    #[test]
    fn lance_vector_clear() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = LanceVectorStore::open(tmp.path().join("lancedb"), 2).unwrap();
        store.add_vector(Uuid::new_v4(), Galaxy::Codex, vec![1.0, 0.0]);
        store.add_vector(Uuid::new_v4(), Galaxy::Codex, vec![0.0, 1.0]);
        assert!(!store.is_index_empty());

        store.clear_vectors();
        let results = store.search_vectors(&[1.0, 0.0], 10, None);
        assert!(results.is_empty());
    }

    #[test]
    fn lance_vector_create_index() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = LanceVectorStore::open(tmp.path().join("lancedb"), 4).unwrap();

        // Add enough vectors for PQ training (requires 256+ rows)
        for i in 0..260 {
            let v = vec![
                (i as f32 * 0.1).sin(),
                (i as f32 * 0.1).cos(),
                i as f32 * 0.05,
                1.0 - (i as f32).mul_add(0.003, 0.0),
            ];
            store.add_vector(Uuid::new_v4(), Galaxy::Codex, v);
        }

        // Create index — should not error with enough rows
        store.create_index().unwrap();

        // Search should still work
        let results = store.search_vectors(&[0.5, 0.5, 0.5, 0.5], 5, None);
        assert!(!results.is_empty());
        assert!(results.len() <= 5);
    }
}
