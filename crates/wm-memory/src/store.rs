//! LMDB-backed memory store.
//!
//! Each galaxy is an LMDB named database (sub-DB within the same file).
//! Reads are zero-copy (mmap'd). Writes are batched.

use lmdb::{Cursor, Database, DatabaseFlags, Environment, Transaction, WriteFlags};
use std::collections::HashMap;
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, RwLock};
use wm_core::{CoreError, Galaxy, Result};

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;

use crate::episodic::EpisodicStore;
use crate::indexes::IndexDbs;
use crate::memory::{Memory, decode_embedding, encode_embedding};
use crate::semantic::SemanticEncoder;

/// Query filter for memories.
#[derive(Debug, Clone, Default)]
pub struct MemoryQuery {
    /// Filter by tags (memory must contain ALL specified tags).
    pub tags: Vec<String>,
    /// Minimum importance (inclusive).
    pub min_importance: Option<f32>,
    /// Maximum importance (inclusive).
    pub max_importance: Option<f32>,
    /// Only memories created after this timestamp.
    pub created_after: Option<chrono::DateTime<chrono::Utc>>,
    /// Only memories created before this timestamp.
    pub created_before: Option<chrono::DateTime<chrono::Utc>>,
    /// Case-insensitive substring filter over content (literal match —
    /// not tokenized or ranked; that is what the search engine is for).
    pub content_substring: Option<String>,
    /// Maximum number of results.
    pub limit: usize,
}

impl MemoryQuery {
    /// Create an empty query (matches all, limit 100).
    #[must_use]
    pub fn new() -> Self {
        Self {
            limit: 100,
            ..Default::default()
        }
    }

    /// Set tag filter.
    #[must_use]
    pub fn with_tags(mut self, tags: Vec<String>) -> Self {
        self.tags = tags;
        self
    }

    /// Set importance range.
    #[must_use]
    pub const fn with_importance_range(mut self, min: f32, max: f32) -> Self {
        self.min_importance = Some(min);
        self.max_importance = Some(max);
        self
    }

    /// Set temporal range.
    #[must_use]
    pub const fn with_time_range(
        mut self,
        after: chrono::DateTime<chrono::Utc>,
        before: chrono::DateTime<chrono::Utc>,
    ) -> Self {
        self.created_after = Some(after);
        self.created_before = Some(before);
        self
    }

    /// One-sided temporal bound: only memories created at or after this
    /// timestamp (`created_after` API passthrough).
    #[must_use]
    pub const fn with_created_after(mut self, after: chrono::DateTime<chrono::Utc>) -> Self {
        self.created_after = Some(after);
        self
    }

    /// One-sided temporal bound: only memories created at or before this
    /// timestamp (`created_before` API passthrough).
    #[must_use]
    pub const fn with_created_before(mut self, before: chrono::DateTime<chrono::Utc>) -> Self {
        self.created_before = Some(before);
        self
    }

    /// Set limit.
    #[must_use]
    pub const fn with_limit(mut self, limit: usize) -> Self {
        self.limit = limit;
        self
    }

    /// Set a case-insensitive substring filter over content.
    #[must_use]
    pub fn with_content_substring(mut self, substring: impl Into<String>) -> Self {
        self.content_substring = Some(substring.into().to_lowercase());
        self
    }

    /// Check if a memory matches this query.
    #[must_use]
    pub fn matches(&self, mem: &Memory) -> bool {
        // Tag filter: memory must contain all specified tags
        if !self.tags.is_empty() {
            for tag in &self.tags {
                if !mem.metadata.tags.iter().any(|t| t == tag) {
                    return false;
                }
            }
        }

        // Importance filter
        if let Some(min) = self.min_importance {
            if mem.metadata.importance < min {
                return false;
            }
        }
        if let Some(max) = self.max_importance {
            if mem.metadata.importance > max {
                return false;
            }
        }

        // Temporal filter
        if let Some(after) = self.created_after {
            if mem.metadata.created_at < after {
                return false;
            }
        }
        if let Some(before) = self.created_before {
            if mem.metadata.created_at > before {
                return false;
            }
        }

        // Substring filter (literal, case-insensitive — never ranked).
        if let Some(sub) = &self.content_substring {
            if !mem.content.to_lowercase().contains(sub) {
                return false;
            }
        }

        true
    }
}

/// The LMDB environment containing all 14 galaxy sub-databases plus 4 index DBs.
pub struct MemoryStore {
    /// Path to the LMDB file
    path: std::path::PathBuf,
    /// LMDB environment (opened once, shared across threads)
    env: Environment,
    /// Cached handles to the 4 secondary index sub-databases
    index_dbs: IndexDbs,
    /// Semantic encoder for content-derived coordinates
    semantic_encoder: SemanticEncoder,
    /// Optional per-galaxy entry limit (DoS prevention)
    max_entries_per_galaxy: Option<usize>,
    /// Monotonic counter of successful mutations since this handle was
    /// opened. Lets the dispatch pipeline cheaply detect actual store
    /// writes (write-audit journal) without scanning galaxies.
    mutation_count: AtomicU64,
    /// Dedicated database for lossless v6 episodic records.
    episodic_db: Database,
    /// DUP_SORT term→id postings for bounded episodic search (v2 sidecar).
    episodic_terms_v2_db: Database,
    /// Content-hash → vector cache (v26 "Tier 2" idea, finally wired):
    /// warm-start for re-ingest and re-runs. Keyed by the embedder
    /// namespace + content hash, so switching models never serves stale
    /// vectors.
    embedding_cache_db: Database,
    /// Warm term-posting cache shared by episodic search views.
    episodic_term_cache: std::sync::Arc<RwLock<HashMap<String, Vec<uuid::Uuid>>>>,
    /// Optional embedder for episodic vector reranking.
    episodic_embedder:
        std::sync::OnceLock<Option<Arc<dyn crate::embedder::Embedder + Send + Sync>>>,
    /// One-shot guard: rebuild the v2 episodic sidecar once per process.
    episodic_sidecar_ensured: std::sync::OnceLock<()>,
    /// Optional adaptive aliases for episodic key expansion.
    episodic_aliases: std::sync::OnceLock<Option<crate::episodic_keys::AdaptiveAliases>>,
    /// Optional vocabulary enrichment for episodic index-time term expansion.
    episodic_enrichment: std::sync::OnceLock<Option<crate::enrichment::VocabularyEnrichment>>,
}

impl MemoryStore {
    /// Open or create an LMDB store at the given path.
    ///
    /// On Unix, the store directory is created with mode 0o700 (owner-only
    /// access) if it does not already exist. Existing directories are
    /// left untouched.
    pub fn open(path: impl AsRef<Path>, map_size: usize) -> Result<Self> {
        let path = path.as_ref().to_path_buf();

        // Ensure the directory exists with restrictive permissions.
        std::fs::create_dir_all(&path)
            .map_err(|e| CoreError::Memory(format!("Cannot create store dir: {e}")))?;
        #[cfg(unix)]
        {
            std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o700))
                .map_err(|e| CoreError::Memory(format!("Cannot set store dir permissions: {e}")))?;
        }

        let env = Environment::new()
            .set_map_size(map_size)
            .set_max_dbs(32)
            .open(&path)
            .map_err(|e| CoreError::Memory(format!("LMDB open failed: {e}")))?;

        // Create all 14 galaxy sub-databases
        for galaxy in Galaxy::all() {
            let db = env
                .create_db(Some(galaxy.db_name()), DatabaseFlags::default())
                .map_err(|e| {
                    CoreError::Memory(format!(
                        "LMDB create_db failed for {}: {e}",
                        galaxy.db_name()
                    ))
                })?;
            let _ = db;
        }

        // Create 4 secondary index sub-databases
        for (name, flags) in crate::indexes::INDEX_DBS {
            let db = env
                .create_db(Some(name), *flags)
                .map_err(|e| CoreError::Memory(format!("LMDB create_db failed for {name}: {e}")))?;
            let _ = db;
        }

        let index_dbs = IndexDbs::open(&env)?;
        let episodic_db = env
            .create_db(Some("episodic_records"), DatabaseFlags::default())
            .map_err(|e| {
                CoreError::Memory(format!("LMDB create_db failed for episodic_records: {e}"))
            })?;
        // v2 sidecar: DUP_SORT postings (term -> set of record ids). Append of
        // a record touches only the (term, id) pairs it introduces instead of
        // rewriting whole posting lists, so ingest cost stays O(new records)
        // as the store grows. The v1 msgpack-Vec database is retained unused
        // on legacy stores; v2 is rebuilt from the authoritative records when
        // found empty.
        let episodic_terms_v2_db = env
            .create_db(Some("episodic_terms_v2"), DatabaseFlags::DUP_SORT)
            .map_err(|e| {
                CoreError::Memory(format!("LMDB create_db failed for episodic_terms_v2: {e}"))
            })?;
        let embedding_cache_db = env
            .create_db(Some("embedding_cache"), DatabaseFlags::default())
            .map_err(|e| {
                CoreError::Memory(format!("LMDB create_db failed for embedding_cache: {e}"))
            })?;
        Ok(Self {
            path,
            env,
            index_dbs,
            semantic_encoder: SemanticEncoder::new(),
            max_entries_per_galaxy: None,
            mutation_count: AtomicU64::new(0),
            episodic_db,
            episodic_terms_v2_db,
            embedding_cache_db,
            episodic_term_cache: std::sync::Arc::new(RwLock::new(HashMap::new())),
            episodic_embedder: std::sync::OnceLock::new(),
            episodic_sidecar_ensured: std::sync::OnceLock::new(),
            episodic_aliases: std::sync::OnceLock::new(),
            episodic_enrichment: std::sync::OnceLock::new(),
        })
    }

    /// Open with the default map size.
    ///
    /// 4 GB on Unix: LMDB truncates the data file sparsely (ftruncate), so
    /// reservation costs nothing until pages are written. On Windows NTFS
    /// materializes the file at full map size immediately — a 4 GB default
    /// would allocate 4 GB on disk per store the moment it opens — so the
    /// Windows default is smaller; pass an explicit size to `open()` for
    /// large stores. (Auto-grow on MapFull is a planned follow-up.)
    pub fn open_default(path: impl AsRef<Path>) -> Result<Self> {
        // Deployment knob: override the platform default explicitly (bytes).
        // CI uses this on Windows, where NTFS materializes the map file at
        // full size and hundreds of parallel test stores would exhaust the
        // runner disk even at the 256MB Windows default.
        let platform_default = if cfg!(windows) {
            256 * 1024 * 1024
        } else {
            4 * 1024 * 1024 * 1024
        };
        let size = std::env::var("WM_DEFAULT_MAP_SIZE")
            .ok()
            .and_then(|v| v.parse::<usize>().ok())
            .filter(|&v| v > 0)
            .unwrap_or(platform_default);
        Self::open(path, size)
    }

    /// Set a per-galaxy entry limit for DoS prevention.
    ///
    /// When set, `put` will reject writes that would exceed the limit.
    /// This prevents a single galaxy from exhausting the LMDB map.
    #[must_use]
    pub const fn with_entry_limit(mut self, limit: usize) -> Self {
        self.max_entries_per_galaxy = Some(limit);
        self
    }

    /// Path to the LMDB file.
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Get the LMDB environment handle.
    pub const fn env(&self) -> &Environment {
        &self.env
    }

    /// Monotonic counter of successful mutations since this handle was
    /// opened (puts, deletes, clears, raw writes). Used by the dispatch
    /// pipeline's write-audit journal to detect actual store writes.
    pub fn mutation_count(&self) -> u64 {
        self.mutation_count.load(Ordering::Relaxed)
    }

    /// Get the cached index database handles.
    pub const fn index_dbs(&self) -> &IndexDbs {
        &self.index_dbs
    }

    /// Get the semantic encoder.
    pub const fn semantic_encoder(&self) -> &SemanticEncoder {
        &self.semantic_encoder
    }

    /// Rebuild the episodic DUP_SORT sidecar once per process when it is
    /// empty while authoritative records exist (legacy v1 stores and
    /// lost-sidecar recovery). Raw records are never modified; a failed
    /// rebuild leaves search on its raw-scan fallback.
    fn ensure_episodic_sidecar(&self) {
        if self.episodic_sidecar_ensured.get().is_some() {
            return;
        }
        let _ = self.episodic_sidecar_ensured.set(());
        let view = EpisodicStore::new(
            &self.env,
            self.episodic_db,
            self.episodic_terms_v2_db,
            self.episodic_term_cache.clone(),
            &self.mutation_count,
        );
        let needs_rebuild = matches!(
            (view.sidecar_is_empty(), view.record_count()),
            (Ok(true), Ok(n)) if n > 0
        );
        if needs_rebuild {
            match view.rebuild_sidecar() {
                Ok(n) => tracing::info!("episodic sidecar rebuilt from {n} records"),
                Err(e) => {
                    tracing::warn!("episodic sidecar rebuild failed: {e}");
                }
            }
        }
    }

    /// Open the v6 lossless episodic record view.
    #[must_use]
    pub fn episodic(&self) -> EpisodicStore<'_> {
        self.ensure_episodic_sidecar();
        let mut store = EpisodicStore::new(
            &self.env,
            self.episodic_db,
            self.episodic_terms_v2_db,
            self.episodic_term_cache.clone(),
            &self.mutation_count,
        );
        if let Some(Some(embedder)) = self.episodic_embedder.get() {
            store = store.with_embedder(embedder.clone());
        }
        if let Some(Some(aliases)) = self.episodic_aliases.get() {
            store = store.with_adaptive_aliases(aliases.clone());
        }
        if let Some(Some(enrichment)) = self.episodic_enrichment.get() {
            store = store.with_enrichment(enrichment.clone());
        }
        store
    }

    /// Attach an embedder for episodic vector reranking.
    pub fn set_episodic_embedder(
        &self,
        embedder: Arc<dyn crate::embedder::Embedder + Send + Sync>,
    ) {
        let _ = self.episodic_embedder.set(Some(embedder));
    }

    /// Attach adaptive aliases for episodic key expansion.
    pub fn set_episodic_aliases(&self, aliases: crate::episodic_keys::AdaptiveAliases) {
        let _ = self.episodic_aliases.set(Some(aliases));
    }

    /// Attach vocabulary enrichment for episodic index-time term expansion.
    pub fn set_episodic_enrichment(&self, enrichment: crate::enrichment::VocabularyEnrichment) {
        let _ = self.episodic_enrichment.set(Some(enrichment));
    }

    /// Get a named database handle for a galaxy.
    pub fn galaxy_db(&self, galaxy: Galaxy) -> Result<Database> {
        self.env.open_db(Some(galaxy.db_name())).map_err(|e| {
            CoreError::Memory(format!("LMDB open_db failed for {}: {e}", galaxy.db_name()))
        })
    }

    // ── Memory CRUD ───────────────────────────────────────────────────

    /// Store a memory in the given galaxy. Keyed by memory.metadata.id.
    /// Also updates all secondary indexes.
    ///
    /// Returns a clear error if the per-galaxy entry limit is exceeded
    /// or if the LMDB map is full.
    pub fn put(&self, galaxy: Galaxy, memory: &Memory) -> Result<()> {
        // Check per-galaxy entry limit (DoS prevention)
        if let Some(limit) = self.max_entries_per_galaxy {
            let current = self.count(galaxy)?;
            if current >= limit {
                return Err(CoreError::Memory(format!(
                    "galaxy {} entry limit reached ({current}/{limit}), write rejected",
                    galaxy.db_name()
                )));
            }
        }

        let db = self.galaxy_db(galaxy)?;
        let key = memory.metadata.id.as_bytes();
        let val = rmp_serde::to_vec(memory)
            .map_err(|e| CoreError::Memory(format!("serialize failed: {e}")))?;

        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;

        // Overwrite semantics: capture the previous record (if any) so its
        // index entries can be removed before the new ones are added.
        // Otherwise stale tags, importance values, timestamps, and content
        // hashes stay queryable after updates.
        let existing = tx
            .get(db, key)
            .ok()
            .and_then(|bytes| rmp_serde::from_slice::<Memory>(bytes).ok());

        match tx.put(db, key, &val, lmdb::WriteFlags::default()) {
            Ok(()) => {}
            Err(lmdb::Error::MapFull) => {
                tx.abort();
                return Err(CoreError::Memory(format!(
                    "LMDB map full: galaxy {}, consider growing map size or pruning old memories",
                    galaxy.db_name()
                )));
            }
            Err(e) => {
                tx.abort();
                return Err(CoreError::Memory(format!("LMDB put failed: {e}")));
            }
        }
        if let Some(existing) = existing {
            self.index_dbs.remove(&mut tx, galaxy, &existing)?;
        }
        self.index_dbs.add(&mut tx, galaxy, memory)?;
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        self.mutation_count.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }

    /// Retrieve a memory by ID from the given galaxy.
    pub fn get(&self, galaxy: Galaxy, id: uuid::Uuid) -> Result<Option<Memory>> {
        let db = self.galaxy_db(galaxy)?;
        let key = id.as_bytes();

        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        let result = tx.get(db, key);
        match result {
            Ok(bytes) => {
                let memory: Memory = rmp_serde::from_slice(bytes)
                    .map_err(|e| CoreError::Memory(format!("deserialize failed: {e}")))?;
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
                Ok(Some(memory))
            }
            Err(lmdb::Error::NotFound) => {
                // ReadOnly transactions don't strictly need commit, but it's good practice
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
                Ok(None)
            }
            Err(e) => Err(CoreError::Memory(format!("LMDB get failed: {e}"))),
        }
    }

    /// Delete a memory by ID from the given galaxy. Returns true if a key was removed.
    /// Also removes all secondary index entries for the memory.
    pub fn delete(&self, galaxy: Galaxy, id: uuid::Uuid) -> Result<bool> {
        let db = self.galaxy_db(galaxy)?;
        let key = id.as_bytes();

        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;

        // Check if key exists and deserialize for index cleanup
        let exists = tx.get(db, key).is_ok();
        if exists {
            // Read memory to get index values for cleanup
            if let Ok(bytes) = tx.get(db, key) {
                if let Ok(memory) = rmp_serde::from_slice::<Memory>(bytes) {
                    let _ = self.index_dbs.remove(&mut tx, galaxy, &memory);
                }
            }
            tx.del(db, key, None)
                .map_err(|e| CoreError::Memory(format!("LMDB del failed: {e}")))?;
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        if exists {
            self.mutation_count.fetch_add(1, Ordering::Relaxed);
        }
        Ok(exists)
    }

    /// Scan up to `limit` memories from the given galaxy (unordered by LMDB page layout).
    pub fn scan(&self, galaxy: Galaxy, limit: usize) -> Result<Vec<Memory>> {
        let db = self.galaxy_db(galaxy)?;
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;

        let mut cursor = tx
            .open_ro_cursor(db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor failed: {e}")))?;

        let mut memories = Vec::with_capacity(limit.min(256));
        for (i, (_key, val)) in cursor.iter().enumerate() {
            if memories.len() >= limit {
                break;
            }
            match rmp_serde::from_slice::<Memory>(val) {
                Ok(memory) => memories.push(memory),
                Err(e) => {
                    tracing::warn!(
                        "Skipping corrupted entry at index {i} in galaxy {:?}: {e}",
                        galaxy
                    );
                }
            }
        }

        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        Ok(memories)
    }

    /// Scan every memory in the galaxy (unordered by LMDB page layout).
    ///
    /// Used by maintenance tooling (e.g. index rebuild). The full galaxy is
    /// materialized in memory — prefer [`Self::scan`] for bounded reads.
    pub fn scan_all(&self, galaxy: Galaxy) -> Result<Vec<Memory>> {
        let db = self.galaxy_db(galaxy)?;
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;

        let mut cursor = tx
            .open_ro_cursor(db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor failed: {e}")))?;

        let mut memories = Vec::new();
        for (i, (_key, val)) in cursor.iter().enumerate() {
            match rmp_serde::from_slice::<Memory>(val) {
                Ok(memory) => memories.push(memory),
                Err(e) => {
                    tracing::warn!(
                        "Skipping corrupted entry at index {i} in galaxy {:?}: {e}",
                        galaxy
                    );
                }
            }
        }

        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        Ok(memories)
    }

    /// Count entries in a galaxy.
    pub fn count(&self, galaxy: Galaxy) -> Result<usize> {
        let db = self.galaxy_db(galaxy)?;
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        let mut cursor = tx
            .open_ro_cursor(db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor failed: {e}")))?;
        let count = cursor.iter().count();
        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        Ok(count)
    }

    /// Clear all memories from a galaxy in a single transaction.
    /// Returns the number of entries cleared.
    /// Also removes all secondary index entries.
    pub fn clear_galaxy(&self, galaxy: Galaxy) -> Result<usize> {
        let db = self.galaxy_db(galaxy)?;

        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;

        let mut cursor = tx
            .open_ro_cursor(db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor failed: {e}")))?;

        let mut count = 0usize;
        let keys_to_delete: Vec<(Vec<u8>, Memory)> = cursor
            .iter()
            .filter_map(|(key, val)| {
                if let Ok(memory) = rmp_serde::from_slice::<Memory>(val) {
                    Some((key.to_vec(), memory))
                } else {
                    None
                }
            })
            .collect();

        drop(cursor);

        for (key, memory) in &keys_to_delete {
            let _ = self.index_dbs.remove(&mut tx, galaxy, memory);
            tx.del(db, &key, None)
                .map_err(|e| CoreError::Memory(format!("LMDB del failed: {e}")))?;
            count += 1;
        }

        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        self.mutation_count
            .fetch_add(count as u64, Ordering::Relaxed);
        Ok(count)
    }

    /// Put multiple memories into a galaxy in a single transaction.
    /// Returns the number of memories written.
    pub fn batch_put(&self, galaxy: Galaxy, memories: &[Memory]) -> Result<usize> {
        if memories.is_empty() {
            return Ok(0);
        }

        let db = self.galaxy_db(galaxy)?;

        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;

        let mut count = 0usize;
        for memory in memories {
            let key = memory.metadata.id.as_bytes();
            let val = rmp_serde::to_vec(memory)
                .map_err(|e| CoreError::Memory(format!("serialize failed: {e}")))?;
            match tx.put(db, key, &val, WriteFlags::default()) {
                Ok(()) => {}
                Err(lmdb::Error::MapFull) => {
                    tx.abort();
                    return Err(CoreError::Memory(format!(
                        "LMDB map full: galaxy {}, consider growing map size",
                        galaxy.db_name()
                    )));
                }
                Err(e) => {
                    tx.abort();
                    return Err(CoreError::Memory(format!("LMDB put failed: {e}")));
                }
            }
            self.index_dbs.add(&mut tx, galaxy, memory)?;
            count += 1;
        }

        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        self.mutation_count
            .fetch_add(count as u64, Ordering::Relaxed);
        Ok(count)
    }

    /// Get raw key-value bytes (for advanced use cases).
    pub fn get_raw(&self, galaxy: Galaxy, key: &[u8]) -> Result<Option<Vec<u8>>> {
        let db = self.galaxy_db(galaxy)?;
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        match tx.get(db, &key) {
            Ok(bytes) => {
                let data = bytes.to_vec();
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
                Ok(Some(data))
            }
            Err(lmdb::Error::NotFound) => {
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
                Ok(None)
            }
            Err(e) => Err(CoreError::Memory(format!("LMDB get_raw failed: {e}"))),
        }
    }

    /// Put raw key-value bytes (for advanced use cases).
    pub fn put_raw(&self, galaxy: Galaxy, key: &[u8], val: &[u8]) -> Result<()> {
        let db = self.galaxy_db(galaxy)?;
        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;
        tx.put(db, &key, &val, lmdb::WriteFlags::default())
            .map_err(|e| CoreError::Memory(format!("LMDB put_raw failed: {e}")))?;
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        self.mutation_count.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }

    /// Delete raw key-value bytes (for advanced use cases).
    /// Returns true if a key was removed.
    pub fn delete_raw(&self, galaxy: Galaxy, key: &[u8]) -> Result<bool> {
        let db = self.galaxy_db(galaxy)?;
        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;
        let deleted = tx.del(db, &key, None).is_ok();
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        if deleted {
            self.mutation_count.fetch_add(1, Ordering::Relaxed);
        }
        Ok(deleted)
    }

    /// Batch multiple raw key-value writes in a single LMDB transaction.
    /// All writes succeed or fail atomically.
    pub fn put_raw_batch(&self, galaxy: Galaxy, entries: &[(&[u8], &[u8])]) -> Result<()> {
        self.put_raw_batch_impl(galaxy, entries)?;
        self.mutation_count
            .fetch_add(entries.len() as u64, Ordering::Relaxed);
        Ok(())
    }

    /// Batch multiple raw key-value writes without advancing the mutation
    /// counter.
    ///
    /// For governance bookkeeping (karma chain, write-audit journal): these
    /// writes are metadata *about* dispatches, not memory mutations. Letting
    /// them tick the counter attributes a whole batch flush to whichever
    /// dispatch happens to be in flight when the threshold trips — the
    /// 2026-08-28 restore-drill false-positive class ("read-only" tools
    /// flagged with the previous batch's size as their write delta).
    pub fn put_raw_batch_untracked(
        &self,
        galaxy: Galaxy,
        entries: &[(&[u8], &[u8])],
    ) -> Result<()> {
        self.put_raw_batch_impl(galaxy, entries)
    }

    fn put_raw_batch_impl(&self, galaxy: Galaxy, entries: &[(&[u8], &[u8])]) -> Result<()> {
        let db = self.galaxy_db(galaxy)?;
        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;
        for (key, val) in entries {
            tx.put(db, key, val, WriteFlags::default())
                .map_err(|e| CoreError::Memory(format!("LMDB put_raw_batch failed: {e}")))?;
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        Ok(())
    }

    // ── Content-hash Deduplication ────────────────────────────────────

    /// Check if a memory with the same content hash already exists in the galaxy.
    /// Uses the content_hash index for O(1) lookup.
    /// Returns the existing memory's ID if found.
    pub fn find_by_content_hash(&self, galaxy: Galaxy, hash: &str) -> Result<Option<uuid::Uuid>> {
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        let result = self.index_dbs.find_by_content_hash(&tx, galaxy, hash)?;
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        Ok(result)
    }

    /// Scan-based content hash lookup (O(n) fallback, used for testing index correctness).
    pub fn find_by_content_hash_scan(
        &self,
        galaxy: Galaxy,
        hash: &str,
    ) -> Result<Option<uuid::Uuid>> {
        let memories = self.scan(galaxy, 10_000)?;
        for mem in memories {
            if mem.metadata.content_hash == hash {
                return Ok(Some(mem.metadata.id));
            }
        }
        Ok(None)
    }

    /// Store a memory with content-hash deduplication.
    /// If a memory with the same content already exists in the galaxy,
    /// returns the existing memory's ID without creating a duplicate.
    pub fn put_dedup(&self, galaxy: Galaxy, memory: &Memory) -> Result<uuid::Uuid> {
        if let Some(existing_id) =
            self.find_by_content_hash(galaxy, &memory.metadata.content_hash)?
        {
            return Ok(existing_id);
        }
        let id = memory.metadata.id;
        self.put(galaxy, memory)?;
        Ok(id)
    }

    // ── Write Batching ─────────────────────────────────────────────────

    /// Store multiple memories in a single LMDB transaction (batch write).
    /// All writes and index updates succeed or fail atomically.
    pub fn put_batch(&self, galaxy: Galaxy, memories: &[Memory]) -> Result<()> {
        let db = self.galaxy_db(galaxy)?;
        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;

        for memory in memories {
            let key = memory.metadata.id.as_bytes();
            let val = rmp_serde::to_vec(memory)
                .map_err(|e| CoreError::Memory(format!("serialize failed: {e}")))?;
            tx.put(db, key, &val, WriteFlags::default())
                .map_err(|e| CoreError::Memory(format!("LMDB put_batch failed: {e}")))?;
            self.index_dbs.add(&mut tx, galaxy, memory)?;
        }

        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        self.mutation_count
            .fetch_add(memories.len() as u64, Ordering::Relaxed);
        Ok(())
    }

    // ── Query API ──────────────────────────────────────────────────────

    /// Query memories in a galaxy with filtering.
    /// Uses secondary indexes when the query is a pure single-dimension filter
    /// (single tag, importance range, or time range with no other filters).
    /// Falls back to scan for complex multi-dimensional queries.
    pub fn query(&self, galaxy: Galaxy, query: &MemoryQuery) -> Result<Vec<Memory>> {
        // Try indexed fast paths for single-dimension queries. A substring
        // filter forces the full scan — the indexes cannot evaluate it.
        if query.content_substring.is_none()
            && query.tags.len() == 1
            && query.min_importance.is_none()
            && query.max_importance.is_none()
            && query.created_after.is_none()
            && query.created_before.is_none()
        {
            return self.query_by_tag_indexed(galaxy, &query.tags[0], query.limit);
        }

        if query.content_substring.is_none()
            && query.tags.is_empty()
            && let Some(min) = query.min_importance
            && let Some(max) = query.max_importance
            && query.created_after.is_none()
            && query.created_before.is_none()
        {
            return self.query_by_importance_indexed(galaxy, min, max, query.limit);
        }

        if query.content_substring.is_none()
            && query.tags.is_empty()
            && query.min_importance.is_none()
            && query.max_importance.is_none()
            && let Some(after) = query.created_after
            && let Some(before) = query.created_before
        {
            return self.query_by_time_indexed(galaxy, after, before, query.limit);
        }

        // Fallback: full scan with in-memory filter
        let memories = self.scan(galaxy, 10_000)?;
        let mut results = Vec::new();
        for mem in memories {
            if query.matches(&mem) {
                results.push(mem);
                if results.len() >= query.limit {
                    break;
                }
            }
        }
        Ok(results)
    }

    /// Tag-based indexed query → memories with the given tag.
    fn query_by_tag_indexed(&self, galaxy: Galaxy, tag: &str, limit: usize) -> Result<Vec<Memory>> {
        let db = self.galaxy_db(galaxy)?;
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        let ids = self.index_dbs.find_by_tag(&tx, galaxy, tag)?;
        let mut results = Vec::new();
        for id in &ids {
            if results.len() >= limit {
                break;
            }
            if let Ok(bytes) = tx.get(db, id.as_bytes()) {
                if let Ok(mem) = rmp_serde::from_slice::<Memory>(bytes) {
                    results.push(mem);
                }
            }
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        Ok(results)
    }

    /// Importance-range indexed query → memories with importance in [min, max].
    fn query_by_importance_indexed(
        &self,
        galaxy: Galaxy,
        min: f32,
        max: f32,
        limit: usize,
    ) -> Result<Vec<Memory>> {
        let db = self.galaxy_db(galaxy)?;
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        let ids = self
            .index_dbs
            .find_by_importance_range(&tx, galaxy, min, max)?;
        let mut results = Vec::new();
        for id in &ids {
            if results.len() >= limit {
                break;
            }
            if let Ok(bytes) = tx.get(db, id.as_bytes()) {
                if let Ok(mem) = rmp_serde::from_slice::<Memory>(bytes) {
                    results.push(mem);
                }
            }
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        Ok(results)
    }

    /// Time-range indexed query → memories created in [after, before].
    fn query_by_time_indexed(
        &self,
        galaxy: Galaxy,
        after: chrono::DateTime<chrono::Utc>,
        before: chrono::DateTime<chrono::Utc>,
        limit: usize,
    ) -> Result<Vec<Memory>> {
        let db = self.galaxy_db(galaxy)?;
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        let ids = self
            .index_dbs
            .find_by_time_range(&tx, galaxy, after, before)?;
        let mut results = Vec::new();
        for id in &ids {
            if results.len() >= limit {
                break;
            }
            if let Ok(bytes) = tx.get(db, id.as_bytes()) {
                if let Ok(mem) = rmp_serde::from_slice::<Memory>(bytes) {
                    results.push(mem);
                }
            }
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        Ok(results)
    }

    // ── Semantic Coordinate Encoding ─────────────────────────────────────

    /// Store a memory with semantically-derived 5D coordinates.
    ///
    /// Replaces the SHA-256 hash-based `Coordinate5D::encode()` with
    /// anchor-based TF projection. The memory's `coord5d` field is updated
    /// with semantically meaningful x/y/z values before storage.
    pub fn put_semantic(&self, galaxy: Galaxy, memory: &mut Memory) -> Result<()> {
        let temporal_weight = memory.metadata.coord5d.w;
        let importance = memory.metadata.importance;
        memory.metadata.coord5d =
            self.semantic_encoder
                .encode_coordinate(&memory.content, temporal_weight, importance);
        self.put(galaxy, memory)
    }

    /// Find memories in a galaxy with content semantically similar to the query text.
    ///
    /// Encodes the query text into a 5D coordinate and scans the galaxy,
    /// returning memories sorted by semantic distance (nearest first).
    pub fn find_similar(
        &self,
        galaxy: Galaxy,
        query_text: &str,
        limit: usize,
    ) -> Result<Vec<(Memory, f32)>> {
        let query_coord = self
            .semantic_encoder
            .encode_coordinate(query_text, 0.5, 0.5);
        let memories = self.scan(galaxy, 10_000)?;
        let mut results: Vec<(Memory, f32)> = memories
            .into_iter()
            .map(|m| {
                let dist = query_coord.semantic_distance_to(&m.metadata.coord5d);
                (m, dist)
            })
            .collect();
        results.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
        results.truncate(limit);
        Ok(results)
    }

    // ── Embedding Storage ──────────────────────────────────────────────

    /// Store an embedding vector for a memory in the Embeddings galaxy.
    /// Keyed by the memory's UUID.
    pub fn put_embedding(&self, memory_id: uuid::Uuid, embedding: &[f32]) -> Result<()> {
        let db = self.galaxy_db(Galaxy::Embeddings)?;
        let key = memory_id.as_bytes();
        let val = encode_embedding(embedding);

        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;
        tx.put(db, key, &val, WriteFlags::default())
            .map_err(|e| CoreError::Memory(format!("LMDB put_embedding failed: {e}")))?;
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        self.mutation_count.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }

    /// Retrieve an embedding vector for a memory from the Embeddings galaxy.
    pub fn get_embedding(&self, memory_id: uuid::Uuid) -> Result<Option<Vec<f32>>> {
        let db = self.galaxy_db(Galaxy::Embeddings)?;
        let key = memory_id.as_bytes();

        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        match tx.get(db, key) {
            Ok(bytes) => {
                let embedding = decode_embedding(bytes);
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
                Ok(Some(embedding))
            }
            Err(lmdb::Error::NotFound) => {
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
                Ok(None)
            }
            Err(e) => Err(CoreError::Memory(format!("LMDB get_embedding failed: {e}"))),
        }
    }

    /// Delete an embedding vector from the Embeddings galaxy.
    pub fn delete_embedding(&self, memory_id: uuid::Uuid) -> Result<bool> {
        let db = self.galaxy_db(Galaxy::Embeddings)?;
        let key = memory_id.as_bytes();

        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;
        let exists = tx.get(db, key).is_ok();
        if exists {
            tx.del(db, key, None)
                .map_err(|e| CoreError::Memory(format!("LMDB del_embedding failed: {e}")))?;
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        if exists {
            self.mutation_count.fetch_add(1, Ordering::Relaxed);
        }
        Ok(exists)
    }

    // ── Embedding cache (content-hash → vector) ────────────────────────

    /// Store a cached embedding under a caller-computed cache key
    /// (embedder namespace + content hash). Vectors for the same content
    /// differ across models, so the key must carry the namespace.
    pub fn put_embedding_cache(&self, cache_key: &str, embedding: &[f32]) -> Result<()> {
        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;
        tx.put(
            self.embedding_cache_db,
            &cache_key.as_bytes().to_vec(),
            &encode_embedding(embedding),
            WriteFlags::default(),
        )
        .map_err(|e| CoreError::Memory(format!("LMDB put_embedding_cache failed: {e}")))?;
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        self.mutation_count.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }

    /// Batched cache write: one transaction for the whole ingest chunk.
    pub fn put_embedding_cache_batch(&self, entries: &[(String, Vec<f32>)]) -> Result<()> {
        if entries.is_empty() {
            return Ok(());
        }
        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;
        for (key, embedding) in entries {
            tx.put(
                self.embedding_cache_db,
                &key.as_bytes().to_vec(),
                &encode_embedding(embedding),
                WriteFlags::default(),
            )
            .map_err(|e| CoreError::Memory(format!("LMDB put_embedding_cache failed: {e}")))?;
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        self.mutation_count
            .fetch_add(entries.len() as u64, Ordering::Relaxed);
        Ok(())
    }

    /// Look up a cached embedding. `Ok(None)` = miss; the caller embeds.
    pub fn get_embedding_cache(&self, cache_key: &str) -> Result<Option<Vec<f32>>> {
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        match tx.get(self.embedding_cache_db, &cache_key.as_bytes().to_vec()) {
            Ok(bytes) => {
                let embedding = decode_embedding(bytes);
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
                Ok(Some(embedding))
            }
            Err(lmdb::Error::NotFound) => {
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
                Ok(None)
            }
            Err(e) => Err(CoreError::Memory(format!(
                "LMDB get_embedding_cache failed: {e}"
            ))),
        }
    }

    /// Batched lookup: one read transaction for the whole ingest chunk.
    /// Result aligns 1:1 with `keys`.
    pub fn get_embedding_cache_batch(&self, keys: &[String]) -> Result<Vec<Option<Vec<f32>>>> {
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        let mut out = Vec::with_capacity(keys.len());
        for key in keys {
            out.push(
                tx.get(self.embedding_cache_db, &key.as_bytes().to_vec())
                    .ok()
                    .map(decode_embedding),
            );
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        Ok(out)
    }

    /// Number of cached vectors (doctor / honesty surfaces).
    pub fn embedding_cache_count(&self) -> Result<u64> {
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        let mut cursor = tx
            .open_ro_cursor(self.embedding_cache_db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor embedding_cache failed: {e}")))?;
        let mut count = 0u64;
        for _ in cursor.iter() {
            count += 1;
        }
        Ok(count)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::content_hash;

    #[test]
    fn open_and_create_galaxies() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        for galaxy in Galaxy::all() {
            let _db = store.galaxy_db(galaxy).unwrap();
        }
    }

    /// Substring filter (memory.query trap fix, 2026-08-29): literal
    /// case-insensitive content match, galaxy-wide — never an arbitrary
    /// page, never routed through the indexed fast paths.
    #[test]
    fn query_substring_filters_galaxy_wide() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        for (i, content) in [
            "the mesh joins at dawn",
            "unrelated content entirely",
            "MESH joins at dusk",
        ]
        .iter()
        .enumerate()
        {
            let mut m = Memory::new(Galaxy::Codex, content.to_string());
            m.metadata.importance = 0.5 + i as f32 / 10.0;
            store.put(Galaxy::Codex, &m).unwrap();
        }

        let hits = store
            .query(
                Galaxy::Codex,
                &MemoryQuery::new().with_content_substring("mesh joins"),
            )
            .unwrap();
        assert_eq!(hits.len(), 2, "CI substring must match both: {hits:?}");
        assert!(
            hits.iter()
                .all(|m| m.content.to_lowercase().contains("mesh joins"))
        );

        let none = store
            .query(
                Galaxy::Codex,
                &MemoryQuery::new().with_content_substring("quantum calendar"),
            )
            .unwrap();
        assert!(none.is_empty(), "no match must be an honest empty set");

        // Substring + tag combined still applies (no fast-path bypass).
        let mut tagged = Memory::new(Galaxy::Codex, "mesh joins again".to_string());
        tagged.metadata.tags = vec!["mesh".into()];
        store.put(Galaxy::Codex, &tagged).unwrap();
        let combined = store
            .query(
                Galaxy::Codex,
                &MemoryQuery::new()
                    .with_tags(vec!["mesh".into()])
                    .with_content_substring("again"),
            )
            .unwrap();
        assert_eq!(combined.len(), 1);
        assert_eq!(combined[0].content, "mesh joins again");
    }

    #[cfg(unix)]
    #[test]
    fn store_dir_has_restrictive_permissions() {
        let tmp = tempfile::tempdir().unwrap();
        let store_path = tmp.path().join("lmdb");
        let _store = MemoryStore::open_default(&store_path).unwrap();
        let perms = std::fs::metadata(&store_path).unwrap().permissions().mode();
        assert_eq!(
            perms & 0o777,
            0o700,
            "store directory should have 0700 permissions, got {:o}",
            perms & 0o777
        );
    }

    #[test]
    fn put_get_delete_memory() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mem = Memory::new(Galaxy::Codex, "Hello world".to_string());
        let id = mem.metadata.id;

        store.put(Galaxy::Codex, &mem).unwrap();
        let retrieved = store.get(Galaxy::Codex, id).unwrap();
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().content, "Hello world");

        let deleted = store.delete(Galaxy::Codex, id).unwrap();
        assert!(deleted);

        let gone = store.get(Galaxy::Codex, id).unwrap();
        assert!(gone.is_none());
    }

    #[test]
    fn scan_memories() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        for i in 0..5 {
            let mem = Memory::new(Galaxy::Codex, format!("memory-{i}"));
            store.put(Galaxy::Codex, &mem).unwrap();
        }

        let all = store.scan(Galaxy::Codex, 100).unwrap();
        assert_eq!(all.len(), 5);

        let limited = store.scan(Galaxy::Codex, 3).unwrap();
        assert_eq!(limited.len(), 3);
    }

    #[test]
    fn overwrite_removes_stale_index_entries() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        // Original record: tag "alpha", importance 0.9.
        let mut mem = Memory::new(Galaxy::Codex, "overwrite target".to_string());
        mem.metadata.tags = vec!["alpha".to_string()];
        mem.metadata.importance = 0.9;
        let id = mem.metadata.id;
        store.put(Galaxy::Codex, &mem).unwrap();

        // Overwrite with tag "beta", importance 0.1, new content hash.
        let mut updated = Memory::new(Galaxy::Codex, "overwritten content".to_string());
        updated.metadata.id = id;
        updated.metadata.tags = vec!["beta".to_string()];
        updated.metadata.importance = 0.1;
        store.put(Galaxy::Codex, &updated).unwrap();

        // Stale entries must be gone, new entries must be queryable.
        let tx = store.env().begin_ro_txn().unwrap();
        let by_alpha = store
            .index_dbs()
            .find_by_tag(&tx, Galaxy::Codex, "alpha")
            .unwrap();
        let by_beta = store
            .index_dbs()
            .find_by_tag(&tx, Galaxy::Codex, "beta")
            .unwrap();
        assert!(
            by_alpha.is_empty(),
            "stale tag index entries must be removed on overwrite"
        );
        assert_eq!(by_beta, vec![id]);

        let by_importance = store
            .index_dbs()
            .find_by_importance_range(&tx, Galaxy::Codex, 0.0, 0.2)
            .unwrap();
        assert!(
            by_importance.contains(&id),
            "new importance must be indexed"
        );
        let by_high = store
            .index_dbs()
            .find_by_importance_range(&tx, Galaxy::Codex, 0.8, 1.0)
            .unwrap();
        assert!(
            !by_high.contains(&id),
            "stale importance index entries must be removed on overwrite"
        );

        let old_hash = content_hash("overwrite target");
        let new_hash = content_hash("overwritten content");
        assert_eq!(
            store
                .index_dbs()
                .find_by_content_hash(&tx, Galaxy::Codex, &old_hash)
                .unwrap(),
            None,
            "stale content-hash index entry must be removed"
        );
        assert_eq!(
            store
                .index_dbs()
                .find_by_content_hash(&tx, Galaxy::Codex, &new_hash)
                .unwrap(),
            Some(id)
        );
    }

    #[test]
    fn count_memories() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        assert_eq!(store.count(Galaxy::Codex).unwrap(), 0);

        for i in 0..3 {
            let mem = Memory::new(Galaxy::Codex, format!("count-{i}"));
            store.put(Galaxy::Codex, &mem).unwrap();
        }

        assert_eq!(store.count(Galaxy::Codex).unwrap(), 3);
    }

    #[test]
    fn get_nonexistent_returns_none() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let result = store.get(Galaxy::Codex, uuid::Uuid::new_v4()).unwrap();
        assert!(result.is_none());
    }

    #[test]
    fn raw_put_get() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        store
            .put_raw(Galaxy::Substrate, b"config:key", b"value123")
            .unwrap();
        let val = store.get_raw(Galaxy::Substrate, b"config:key").unwrap();
        assert_eq!(val, Some(b"value123".to_vec()));
    }

    #[test]
    fn put_dedup_prevents_duplicates() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mem1 = Memory::new(Galaxy::Codex, "duplicate content".into());
        let id1 = store.put_dedup(Galaxy::Codex, &mem1).unwrap();

        let mem2 = Memory::new(Galaxy::Codex, "duplicate content".into());
        let id2 = store.put_dedup(Galaxy::Codex, &mem2).unwrap();

        assert_eq!(id1, id2, "dedup should return same ID for same content");
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 1);
    }

    #[test]
    fn put_dedup_allows_different_content() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mem1 = Memory::new(Galaxy::Codex, "content A".into());
        store.put_dedup(Galaxy::Codex, &mem1).unwrap();

        let mem2 = Memory::new(Galaxy::Codex, "content B".into());
        store.put_dedup(Galaxy::Codex, &mem2).unwrap();

        assert_eq!(store.count(Galaxy::Codex).unwrap(), 2);
    }

    #[test]
    fn put_batch_atomic_write() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let memories: Vec<Memory> = (0..10)
            .map(|i| Memory::new(Galaxy::Codex, format!("batch-{i}")))
            .collect();

        store.put_batch(Galaxy::Codex, &memories).unwrap();
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 10);
    }

    #[test]
    fn query_by_tags() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mem1 = Memory::new(Galaxy::Codex, "tagged memory".into())
            .with_tags(vec!["rust".into(), "memory".into()]);
        let mem2 =
            Memory::new(Galaxy::Codex, "other memory".into()).with_tags(vec!["python".into()]);
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Codex, &mem2).unwrap();

        let query = MemoryQuery::new().with_tags(vec!["rust".into()]);
        let results = store.query(Galaxy::Codex, &query).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].content, "tagged memory");
    }

    #[test]
    fn query_by_importance_range() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "low".into()).with_importance(0.1),
            )
            .unwrap();
        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "mid".into()).with_importance(0.5),
            )
            .unwrap();
        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "high".into()).with_importance(0.9),
            )
            .unwrap();

        let query = MemoryQuery::new().with_importance_range(0.4, 0.6);
        let results = store.query(Galaxy::Codex, &query).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].content, "mid");
    }

    #[test]
    fn memory_query_one_sided_time_bounds() {
        // `created_after` / `created_before` map onto the temporal filter
        // one side at a time (the API passthrough for memory.query).
        let old = Memory::new(Galaxy::Codex, "old".into());
        let mut recent = Memory::new(Galaxy::Codex, "recent".into());
        recent.metadata.created_at = old.metadata.created_at + chrono::Duration::days(30);

        let cutoff = old.metadata.created_at + chrono::Duration::days(10);
        let after = MemoryQuery::new().with_created_after(cutoff);
        assert!(!after.matches(&old), "pre-cutoff memory must not match");
        assert!(after.matches(&recent), "post-cutoff memory must match");

        let before = MemoryQuery::new().with_created_before(cutoff);
        assert!(before.matches(&old), "pre-cutoff memory must match");
        assert!(
            !before.matches(&recent),
            "post-cutoff memory must not match"
        );

        // Bounds are inclusive.
        let edge = MemoryQuery::new().with_created_after(cutoff);
        let mut at = Memory::new(Galaxy::Codex, "at cutoff".into());
        at.metadata.created_at = cutoff;
        assert!(edge.matches(&at), "created_at == after bound is inclusive");
    }

    #[test]
    fn embedding_put_get_delete() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let id = uuid::Uuid::new_v4();
        let embedding = vec![0.1, 0.2, 0.3, 0.4, 0.5];

        store.put_embedding(id, &embedding).unwrap();
        let retrieved = store.get_embedding(id).unwrap();
        assert!(retrieved.is_some());
        let retrieved = retrieved.unwrap();
        assert_eq!(retrieved.len(), 5);
        assert!((retrieved[0] - 0.1).abs() < f32::EPSILON);

        assert!(store.delete_embedding(id).unwrap());
        assert!(store.get_embedding(id).unwrap().is_none());
    }

    #[test]
    fn embedding_cache_roundtrip_batch_and_count() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let entries: Vec<(String, Vec<f32>)> = (0..5)
            .map(|i| (format!("ns:model:{i:016x}"), vec![i as f32; 8]))
            .collect();
        store.put_embedding_cache_batch(&entries).unwrap();
        assert_eq!(store.embedding_cache_count().unwrap(), 5);

        // Single read
        let hit = store
            .get_embedding_cache("ns:model:0000000000000003")
            .unwrap();
        assert_eq!(hit.unwrap(), vec![3.0f32; 8]);
        assert!(
            store
                .get_embedding_cache("ns:model:absent")
                .unwrap()
                .is_none()
        );

        // Batched read aligns 1:1, misses are None
        let keys: Vec<String> = (0..6).map(|i| format!("ns:model:{i:016x}")).collect();
        let batch = store.get_embedding_cache_batch(&keys).unwrap();
        assert_eq!(batch.len(), 6);
        assert!(batch[0..5].iter().all(Option::is_some));
        assert!(batch[5].is_none());

        // Overwrite is a put, not a duplicate
        store
            .put_embedding_cache("ns:model:0000000000000001", &[9.0; 8])
            .unwrap();
        assert_eq!(store.embedding_cache_count().unwrap(), 5);
        assert_eq!(
            store
                .get_embedding_cache("ns:model:0000000000000001")
                .unwrap()
                .unwrap(),
            vec![9.0f32; 8]
        );
    }

    #[test]
    fn embedding_cache_survives_store_reopen() {
        // V8 ship list #2 acceptance shape: vectors persist across restart.
        let tmp = tempfile::tempdir().unwrap();
        {
            let store = MemoryStore::open_default(tmp.path()).unwrap();
            store
                .put_embedding_cache("onnx:bge-small:abc", &[0.5; 384])
                .unwrap();
        }
        let reopened = MemoryStore::open_default(tmp.path()).unwrap();
        let cached = reopened.get_embedding_cache("onnx:bge-small:abc").unwrap();
        assert_eq!(cached.unwrap(), vec![0.5f32; 384]);
    }

    #[test]
    fn content_hash_is_sha256() {
        let hash1 = content_hash("test content");
        let hash2 = content_hash("test content");
        let hash3 = content_hash("different content");

        assert_eq!(hash1, hash2, "same content should produce same hash");
        assert_ne!(
            hash1, hash3,
            "different content should produce different hash"
        );
        assert_eq!(hash1.len(), 64, "SHA-256 hex should be 64 chars");
    }

    #[test]
    fn query_by_tag_uses_index() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mem1 = Memory::new(Galaxy::Codex, "tagged".into())
            .with_tags(vec!["rust".into(), "memory".into()]);
        let mem2 = Memory::new(Galaxy::Codex, "other".into()).with_tags(vec!["python".into()]);
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Codex, &mem2).unwrap();

        let query = MemoryQuery::new().with_tags(vec!["rust".into()]);
        let results = store.query(Galaxy::Codex, &query).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].content, "tagged");
    }

    #[test]
    fn query_by_importance_uses_index() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "low".into()).with_importance(0.1),
            )
            .unwrap();
        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "mid".into()).with_importance(0.5),
            )
            .unwrap();
        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "high".into()).with_importance(0.9),
            )
            .unwrap();

        let query = MemoryQuery::new().with_importance_range(0.4, 0.6);
        let results = store.query(Galaxy::Codex, &query).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].content, "mid");
    }

    #[test]
    fn query_by_time_uses_index() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let t0 = chrono::Utc::now();
        std::thread::sleep(std::time::Duration::from_millis(10));
        let mem = Memory::new(Galaxy::Codex, "timed".into());
        store.put(Galaxy::Codex, &mem).unwrap();
        std::thread::sleep(std::time::Duration::from_millis(10));
        let t2 = chrono::Utc::now();

        let query = MemoryQuery::new().with_time_range(t0, t2);
        let results = store.query(Galaxy::Codex, &query).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].content, "timed");
    }

    #[test]
    fn delete_removes_index_entries() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mem = Memory::new(Galaxy::Codex, "test".into())
            .with_tags(vec!["tag1".into()])
            .with_importance(0.7);
        let id = mem.metadata.id;
        let hash = mem.metadata.content_hash.clone();
        store.put(Galaxy::Codex, &mem).unwrap();

        // Verify index entries exist
        assert!(
            store
                .find_by_content_hash(Galaxy::Codex, &hash)
                .unwrap()
                .is_some()
        );

        // Delete
        store.delete(Galaxy::Codex, id).unwrap();

        // Verify index entries are gone
        assert!(
            store
                .find_by_content_hash(Galaxy::Codex, &hash)
                .unwrap()
                .is_none()
        );

        // Tag query should return 0
        let query = MemoryQuery::new().with_tags(vec!["tag1".into()]);
        let results = store.query(Galaxy::Codex, &query).unwrap();
        assert!(results.is_empty());
    }

    #[test]
    fn put_batch_updates_indexes() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let memories: Vec<Memory> = (0..5)
            .map(|i| {
                Memory::new(Galaxy::Codex, format!("batch-{i}"))
                    .with_tags(vec![format!("tag{i}")])
                    .with_importance(i as f32 * 0.2)
            })
            .collect();
        store.put_batch(Galaxy::Codex, &memories).unwrap();

        for i in 0..5 {
            let query = MemoryQuery::new().with_tags(vec![format!("tag{i}")]);
            let results = store.query(Galaxy::Codex, &query).unwrap();
            assert_eq!(results.len(), 1, "tag{i} should have 1 result");
        }
    }

    #[test]
    fn find_by_content_hash_indexed_matches_scan() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mem = Memory::new(Galaxy::Codex, "dedup test".into());
        let id = mem.metadata.id;
        let hash = mem.metadata.content_hash.clone();
        store.put(Galaxy::Codex, &mem).unwrap();

        let indexed = store.find_by_content_hash(Galaxy::Codex, &hash).unwrap();
        let scanned = store
            .find_by_content_hash_scan(Galaxy::Codex, &hash)
            .unwrap();

        assert_eq!(indexed, scanned);
        assert_eq!(indexed, Some(id));
    }

    #[test]
    fn put_dedup_uses_index() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mem1 = Memory::new(Galaxy::Codex, "duplicate content".into());
        let id1 = store.put_dedup(Galaxy::Codex, &mem1).unwrap();

        let mem2 = Memory::new(Galaxy::Codex, "duplicate content".into());
        let id2 = store.put_dedup(Galaxy::Codex, &mem2).unwrap();

        assert_eq!(id1, id2, "dedup should return same ID for same content");
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 1);
    }

    #[test]
    fn put_semantic_updates_coord5d() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mut mem = Memory::new(
            Galaxy::Codex,
            "The algorithm computes data using a systematic method".to_string(),
        );
        let original_coord = mem.metadata.coord5d.clone();
        store.put_semantic(Galaxy::Codex, &mut mem).unwrap();

        // coord5d should have changed from the SHA-256 hash-based encoding
        assert_ne!(
            mem.metadata.coord5d.x, original_coord.x,
            "semantic encoding should change x"
        );
        assert_ne!(
            mem.metadata.coord5d.y, original_coord.y,
            "semantic encoding should change y"
        );

        // Verify it was stored with the semantic coordinate
        let retrieved = store.get(Galaxy::Codex, mem.metadata.id).unwrap().unwrap();
        assert_eq!(retrieved.metadata.coord5d.x, mem.metadata.coord5d.x);
    }

    #[test]
    fn put_semantic_preserves_temporal_and_importance() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mut mem = Memory::new(Galaxy::Codex, "test content".into()).with_importance(0.8);
        mem.metadata.coord5d.w = 0.6;
        store.put_semantic(Galaxy::Codex, &mut mem).unwrap();

        assert!((mem.metadata.coord5d.w - 0.6).abs() < f32::EPSILON);
        assert!((mem.metadata.coord5d.v - 0.8).abs() < f32::EPSILON);
    }

    #[test]
    fn find_similar_returns_nearest_first() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let mut logic_mem = Memory::new(
            Galaxy::Codex,
            "The algorithm computes data using systematic logic and analysis".to_string(),
        );
        store.put_semantic(Galaxy::Codex, &mut logic_mem).unwrap();

        let mut emotion_mem = Memory::new(
            Galaxy::Codex,
            "I feel love and joy with deep passion and empathy in my heart".to_string(),
        );
        store.put_semantic(Galaxy::Codex, &mut emotion_mem).unwrap();

        // Query with logic-like text should find the logic memory first
        let results = store
            .find_similar(Galaxy::Codex, "algorithm data systematic method", 10)
            .unwrap();
        assert!(!results.is_empty());
        assert_eq!(results[0].0.metadata.id, logic_mem.metadata.id);

        // Query with emotion-like text should find the emotion memory first
        let results = store
            .find_similar(Galaxy::Codex, "love joy passion heart feeling", 10)
            .unwrap();
        assert!(!results.is_empty());
        assert_eq!(results[0].0.metadata.id, emotion_mem.metadata.id);
    }

    #[test]
    fn find_similar_empty_galaxy() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let results = store.find_similar(Galaxy::Codex, "anything", 10).unwrap();
        assert!(results.is_empty());
    }

    #[test]
    fn find_similar_respects_limit() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        for i in 0..5 {
            let mut mem = Memory::new(Galaxy::Codex, format!("algorithm data method {i}"));
            store.put_semantic(Galaxy::Codex, &mut mem).unwrap();
        }

        let results = store
            .find_similar(Galaxy::Codex, "algorithm data", 3)
            .unwrap();
        assert_eq!(results.len(), 3);
    }

    #[test]
    fn semantic_encoder_accessible() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let scores = store.semantic_encoder().encode("algorithm data logic");
        // Logic-heavy text → x < 0.5
        assert!(scores.x < 0.5);
    }

    #[test]
    fn put_raw_batch_writes_atomically() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        let entries: &[(&[u8], &[u8])] =
            &[(b"key1", b"val1"), (b"key2", b"val2"), (b"key3", b"val3")];
        store.put_raw_batch(Galaxy::Karma, entries).unwrap();

        assert_eq!(
            store.get_raw(Galaxy::Karma, b"key1").unwrap().unwrap(),
            b"val1"
        );
        assert_eq!(
            store.get_raw(Galaxy::Karma, b"key2").unwrap().unwrap(),
            b"val2"
        );
        assert_eq!(
            store.get_raw(Galaxy::Karma, b"key3").unwrap().unwrap(),
            b"val3"
        );
    }

    #[test]
    fn put_raw_batch_empty_is_noop() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        store.put_raw_batch(Galaxy::Karma, &[]).unwrap();
        assert_eq!(store.count(Galaxy::Karma).unwrap(), 0);
    }

    #[test]
    fn entry_limit_rejects_excess_writes() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path())
            .unwrap()
            .with_entry_limit(3);

        for i in 0..3 {
            let mem = Memory::new(Galaxy::Codex, format!("memory {i}"));
            store.put(Galaxy::Codex, &mem).unwrap();
        }

        // 4th write should be rejected
        let mem = Memory::new(Galaxy::Codex, "overflow memory".to_string());
        let result = store.put(Galaxy::Codex, &mem);
        assert!(result.is_err(), "write beyond limit should be rejected");
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("entry limit reached"),
            "error should mention entry limit: {err_msg}"
        );
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 3);
    }

    #[test]
    fn entry_limit_per_galaxy_independent() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path())
            .unwrap()
            .with_entry_limit(2);

        // Fill Codex to limit
        for i in 0..2 {
            let mem = Memory::new(Galaxy::Codex, format!("codex {i}"));
            store.put(Galaxy::Codex, &mem).unwrap();
        }

        // Writing to a different galaxy should still work
        let mem = Memory::new(Galaxy::Research, "science memory".to_string());
        let result = store.put(Galaxy::Research, &mem);
        assert!(
            result.is_ok(),
            "different galaxy should not be affected by limit"
        );
    }

    #[test]
    fn entry_limit_none_allows_unlimited() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        // No limit set — should allow many writes
        for i in 0..50 {
            let mem = Memory::new(Galaxy::Codex, format!("memory {i}"));
            store.put(Galaxy::Codex, &mem).unwrap();
        }
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 50);
    }

    #[test]
    fn map_full_error_is_graceful() {
        // Small map: opening succeeds (galaxy + sidecar databases fit), but
        // the padded write loop fills it and MapFull surfaces from put().
        // 64KB proved too tight for eager create_db on macOS/arm64.
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open(tmp.path(), 512 * 1024).unwrap();

        // Write memories until map is full
        let mut written = 0;
        let mut got_map_full = false;
        for i in 0..1000 {
            let mem = Memory::new(
                Galaxy::Codex,
                format!("memory content {i} {}", "with padding ".repeat(50)),
            );
            match store.put(Galaxy::Codex, &mem) {
                Ok(()) => written += 1,
                Err(e) => {
                    let msg = e.to_string();
                    if msg.contains("map full") {
                        got_map_full = true;
                        break;
                    }
                    // Other errors are fine too (e.g., serialize failed)
                    break;
                }
            }
        }

        assert!(
            got_map_full || written < 1000,
            "should eventually hit map full or error"
        );
        assert!(written > 0, "should have written at least some memories");
    }
}
