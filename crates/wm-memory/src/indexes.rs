//! Secondary LMDB indexes for O(log n) lookups.
//!
//! Four index sub-databases:
//! - `idx_content_hash`: `{galaxy}:{hash}` → UUID (O(1) dedup)
//! - `idx_tags`: `{galaxy}:{tag}` → UUID (DUP_SORT, tag-based queries)
//! - `idx_importance`: `{galaxy}:{f32_be}` → UUID (DUP_SORT, range queries)
//! - `idx_temporal`: `{galaxy}:{i64_be}` → UUID (DUP_SORT, time-range queries)
//!
//! Keys are raw bytes: `galaxy_db_name + 0x00 + value_bytes`.
//! The null separator ensures galaxy-scoped sorting.

use lmdb::{
    Cursor, Database, DatabaseFlags, Environment, RoTransaction, RwTransaction, Transaction,
    WriteFlags,
};
use lmdb_sys::{MDB_NEXT, MDB_NEXT_DUP, MDB_SET_RANGE};
use uuid::Uuid;
use wm_core::{CoreError, Galaxy, Result};

use crate::Memory;

/// Index sub-database names.
pub const IDX_CONTENT_HASH: &str = "idx_content_hash";
pub const IDX_TAGS: &str = "idx_tags";
pub const IDX_IMPORTANCE: &str = "idx_importance";
pub const IDX_TEMPORAL: &str = "idx_temporal";

/// All index DBs with their flags — used at environment creation.
pub const INDEX_DBS: &[(&str, DatabaseFlags)] = &[
    (IDX_CONTENT_HASH, DatabaseFlags::empty()),
    (IDX_TAGS, DatabaseFlags::DUP_SORT),
    (IDX_IMPORTANCE, DatabaseFlags::DUP_SORT),
    (IDX_TEMPORAL, DatabaseFlags::DUP_SORT),
];

/// Cached handles to the four index sub-databases.
#[derive(Clone, Copy)]
pub struct IndexDbs {
    content_hash: Database,
    tags: Database,
    importance: Database,
    temporal: Database,
}

impl IndexDbs {
    /// Open handles to all four index DBs. Call after `create_db` at startup.
    pub fn open(env: &Environment) -> Result<Self> {
        Ok(Self {
            content_hash: open_db(env, IDX_CONTENT_HASH)?,
            tags: open_db(env, IDX_TAGS)?,
            importance: open_db(env, IDX_IMPORTANCE)?,
            temporal: open_db(env, IDX_TEMPORAL)?,
        })
    }

    /// Add a memory's index entries within an existing write transaction.
    pub fn add(&self, tx: &mut RwTransaction, galaxy: Galaxy, memory: &Memory) -> Result<()> {
        let id_bytes = memory.metadata.id.as_bytes();

        // content_hash → UUID
        let key = index_key(galaxy, memory.metadata.content_hash.as_bytes());
        tx.put(self.content_hash, &key, id_bytes, WriteFlags::default())
            .map_err(|e| CoreError::Memory(format!("idx_content_hash put: {e}")))?;

        // tag → UUID (DUP_SORT)
        for tag in &memory.metadata.tags {
            let key = index_key(galaxy, tag.as_bytes());
            tx.put(self.tags, &key, id_bytes, WriteFlags::default())
                .map_err(|e| CoreError::Memory(format!("idx_tags put: {e}")))?;
        }

        // importance → UUID (DUP_SORT, sorted by big-endian f32 bits)
        let imp_bytes = encode_f32(memory.metadata.importance);
        let key = index_key(galaxy, &imp_bytes);
        tx.put(self.importance, &key, id_bytes, WriteFlags::default())
            .map_err(|e| CoreError::Memory(format!("idx_importance put: {e}")))?;

        // timestamp → UUID (DUP_SORT, sorted by big-endian i64)
        let ts_bytes = encode_timestamp(memory.metadata.created_at);
        let key = index_key(galaxy, &ts_bytes);
        tx.put(self.temporal, &key, id_bytes, WriteFlags::default())
            .map_err(|e| CoreError::Memory(format!("idx_temporal put: {e}")))?;

        Ok(())
    }

    /// Remove a memory's index entries within an existing write transaction.
    pub fn remove(&self, tx: &mut RwTransaction, galaxy: Galaxy, memory: &Memory) -> Result<()> {
        // content_hash
        let key = index_key(galaxy, memory.metadata.content_hash.as_bytes());
        let _ = tx.del(self.content_hash, &key, None);

        // tags
        for tag in &memory.metadata.tags {
            let key = index_key(galaxy, tag.as_bytes());
            let _ = tx.del(self.tags, &key, None);
        }

        // importance
        let imp_bytes = encode_f32(memory.metadata.importance);
        let key = index_key(galaxy, &imp_bytes);
        let _ = tx.del(self.importance, &key, None);

        // temporal
        let ts_bytes = encode_timestamp(memory.metadata.created_at);
        let key = index_key(galaxy, &ts_bytes);
        let _ = tx.del(self.temporal, &key, None);

        Ok(())
    }

    /// O(1) content-hash lookup → UUID.
    pub fn find_by_content_hash(
        &self,
        tx: &RoTransaction,
        galaxy: Galaxy,
        hash: &str,
    ) -> Result<Option<Uuid>> {
        let key = index_key(galaxy, hash.as_bytes());
        match tx.get(self.content_hash, &key) {
            Ok(bytes) => {
                let id = decode_uuid(bytes)?;
                Ok(Some(id))
            }
            Err(lmdb::Error::NotFound) => Ok(None),
            Err(e) => Err(CoreError::Memory(format!("idx_content_hash get: {e}"))),
        }
    }

    /// Tag lookup → all UUIDs with that tag in the galaxy.
    pub fn find_by_tag(&self, tx: &RoTransaction, galaxy: Galaxy, tag: &str) -> Result<Vec<Uuid>> {
        let start_key = index_key(galaxy, tag.as_bytes());
        let cursor = tx
            .open_ro_cursor(self.tags)
            .map_err(|e| CoreError::Memory(format!("idx_tags cursor: {e}")))?;

        let mut ids = Vec::new();
        // Position at first key >= start_key
        match cursor.get(Some(&start_key), None, MDB_SET_RANGE) {
            Ok((key_opt, val)) => {
                // For DUP_SORT, key_opt is Some when key changes, None for dups of same key
                let key_matches = key_opt.is_none_or(|k| k == start_key.as_slice());
                if key_matches {
                    if let Ok(id) = decode_uuid(val) {
                        ids.push(id);
                    }
                    // Advance through duplicates (MDB_NEXT_DUP stays within same key)
                    while let Ok((_, val)) = cursor.get(None, None, MDB_NEXT_DUP) {
                        if let Ok(id) = decode_uuid(val) {
                            ids.push(id);
                        }
                    }
                }
            }
            Err(lmdb::Error::NotFound) => {}
            Err(e) => return Err(CoreError::Memory(format!("idx_tags cursor get: {e}"))),
        }
        drop(cursor);
        Ok(ids)
    }

    /// Importance range query → all UUIDs with importance in [min, max].
    pub fn find_by_importance_range(
        &self,
        tx: &RoTransaction,
        galaxy: Galaxy,
        min: f32,
        max: f32,
    ) -> Result<Vec<Uuid>> {
        let prefix = galaxy_prefix(galaxy);
        let start_key = index_key(galaxy, &encode_f32(min));
        let max_bytes = encode_f32(max);

        let cursor = tx
            .open_ro_cursor(self.importance)
            .map_err(|e| CoreError::Memory(format!("idx_importance cursor: {e}")))?;

        let mut ids = Vec::new();
        let mut current = cursor.get(Some(&start_key), None, MDB_SET_RANGE).ok();
        while let Some((key_opt, val)) = current {
            let key = key_opt.unwrap_or(&start_key);
            if !key.starts_with(&prefix) {
                break;
            }
            let value_bytes = &key[prefix.len()..];
            if value_bytes > max_bytes.as_slice() {
                break;
            }
            if let Ok(id) = decode_uuid(val) {
                ids.push(id);
            }
            current = cursor.get(None, None, MDB_NEXT).ok();
        }
        drop(cursor);
        Ok(ids)
    }

    /// Temporal range query → all UUIDs created in [after, before].
    pub fn find_by_time_range(
        &self,
        tx: &RoTransaction,
        galaxy: Galaxy,
        after: chrono::DateTime<chrono::Utc>,
        before: chrono::DateTime<chrono::Utc>,
    ) -> Result<Vec<Uuid>> {
        let prefix = galaxy_prefix(galaxy);
        let start_key = index_key(galaxy, &encode_timestamp(after));
        let max_bytes = encode_timestamp(before);

        let cursor = tx
            .open_ro_cursor(self.temporal)
            .map_err(|e| CoreError::Memory(format!("idx_temporal cursor: {e}")))?;

        let mut ids = Vec::new();
        let mut current = cursor.get(Some(&start_key), None, MDB_SET_RANGE).ok();
        while let Some((key_opt, val)) = current {
            let key = key_opt.unwrap_or(&start_key);
            if !key.starts_with(&prefix) {
                break;
            }
            let value_bytes = &key[prefix.len()..];
            if value_bytes > max_bytes.as_slice() {
                break;
            }
            if let Ok(id) = decode_uuid(val) {
                ids.push(id);
            }
            current = cursor.get(None, None, MDB_NEXT).ok();
        }
        drop(cursor);
        Ok(ids)
    }
}

// ── Key encoding helpers ──────────────────────────────────────────────

fn open_db(env: &Environment, name: &str) -> Result<Database> {
    env.open_db(Some(name))
        .map_err(|e| CoreError::Memory(format!("LMDB open_db {name}: {e}")))
}

fn galaxy_prefix(galaxy: Galaxy) -> Vec<u8> {
    let name = galaxy.db_name();
    let mut key = Vec::with_capacity(name.len() + 1);
    key.extend_from_slice(name.as_bytes());
    key.push(0);
    key
}

fn index_key(galaxy: Galaxy, value_bytes: &[u8]) -> Vec<u8> {
    let mut key = galaxy_prefix(galaxy);
    key.extend_from_slice(value_bytes);
    key
}

/// Encode f32 as big-endian bits. Sorts correctly for positive values (0.0-1.0).
const fn encode_f32(value: f32) -> [u8; 4] {
    value.to_bits().to_be_bytes()
}

/// Encode timestamp as big-endian i64. Sorts correctly for positive values.
const fn encode_timestamp(ts: chrono::DateTime<chrono::Utc>) -> [u8; 8] {
    ts.timestamp().to_be_bytes()
}

fn decode_uuid(bytes: &[u8]) -> Result<Uuid> {
    Uuid::from_slice(bytes).map_err(|e| CoreError::Memory(format!("UUID decode: {e}")))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Memory, MemoryStore};
    use tempfile::tempdir;
    use wm_core::Galaxy;

    fn setup() -> (tempfile::TempDir, MemoryStore) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, store)
    }

    #[test]
    fn content_hash_index_o1_lookup() {
        let (_tmp, store) = setup();
        let mem = Memory::new(Galaxy::Codex, "hello world".into());
        let id = mem.metadata.id;
        let hash = mem.metadata.content_hash.clone();
        store.put(Galaxy::Codex, &mem).unwrap();

        let tx = store.env().begin_ro_txn().unwrap();
        let found = store
            .index_dbs()
            .find_by_content_hash(&tx, Galaxy::Codex, &hash)
            .unwrap();
        tx.commit().unwrap();
        assert_eq!(found, Some(id));
    }

    #[test]
    fn content_hash_index_miss() {
        let (_tmp, store) = setup();
        let tx = store.env().begin_ro_txn().unwrap();
        let found = store
            .index_dbs()
            .find_by_content_hash(&tx, Galaxy::Codex, "nonexistent")
            .unwrap();
        tx.commit().unwrap();
        assert!(found.is_none());
    }

    #[test]
    fn tag_index_returns_all_tagged() {
        let (_tmp, store) = setup();
        let mem1 = Memory::new(Galaxy::Codex, "a".into()).with_tags(vec!["rust".into()]);
        let mem2 = Memory::new(Galaxy::Codex, "b".into()).with_tags(vec!["rust".into()]);
        let mem3 = Memory::new(Galaxy::Codex, "c".into()).with_tags(vec!["python".into()]);
        let id1 = mem1.metadata.id;
        let id2 = mem2.metadata.id;
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Codex, &mem2).unwrap();
        store.put(Galaxy::Codex, &mem3).unwrap();

        let tx = store.env().begin_ro_txn().unwrap();
        let rust_ids = store
            .index_dbs()
            .find_by_tag(&tx, Galaxy::Codex, "rust")
            .unwrap();
        tx.commit().unwrap();

        assert_eq!(rust_ids.len(), 2);
        assert!(rust_ids.contains(&id1));
        assert!(rust_ids.contains(&id2));
    }

    #[test]
    fn tag_index_galaxy_scoped() {
        let (_tmp, store) = setup();
        let mem1 = Memory::new(Galaxy::Codex, "a".into()).with_tags(vec!["shared".into()]);
        let mem2 = Memory::new(Galaxy::Research, "b".into()).with_tags(vec!["shared".into()]);
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Research, &mem2).unwrap();

        let tx = store.env().begin_ro_txn().unwrap();
        let codex_ids = store
            .index_dbs()
            .find_by_tag(&tx, Galaxy::Codex, "shared")
            .unwrap();
        let research_ids = store
            .index_dbs()
            .find_by_tag(&tx, Galaxy::Research, "shared")
            .unwrap();
        tx.commit().unwrap();

        assert_eq!(codex_ids.len(), 1);
        assert_eq!(research_ids.len(), 1);
    }

    #[test]
    fn importance_range_query() {
        let (_tmp, store) = setup();
        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "low".into()).with_importance(0.1),
            )
            .unwrap();
        let mid = Memory::new(Galaxy::Codex, "mid".into()).with_importance(0.5);
        let mid_id = mid.metadata.id;
        store.put(Galaxy::Codex, &mid).unwrap();
        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "high".into()).with_importance(0.9),
            )
            .unwrap();

        let tx = store.env().begin_ro_txn().unwrap();
        let ids = store
            .index_dbs()
            .find_by_importance_range(&tx, Galaxy::Codex, 0.4, 0.6)
            .unwrap();
        tx.commit().unwrap();

        assert_eq!(ids.len(), 1);
        assert_eq!(ids[0], mid_id);
    }

    #[test]
    fn importance_range_query_full_range() {
        let (_tmp, store) = setup();
        for i in 0..10 {
            let imp = i as f32 * 0.1;
            store
                .put(
                    Galaxy::Codex,
                    &Memory::new(Galaxy::Codex, format!("m{i}")).with_importance(imp),
                )
                .unwrap();
        }
        let tx = store.env().begin_ro_txn().unwrap();
        let ids = store
            .index_dbs()
            .find_by_importance_range(&tx, Galaxy::Codex, 0.0, 1.0)
            .unwrap();
        tx.commit().unwrap();
        assert_eq!(ids.len(), 10);
    }

    #[test]
    fn temporal_range_query() {
        let (_tmp, store) = setup();
        let t0 = chrono::Utc::now();
        std::thread::sleep(std::time::Duration::from_millis(10));
        let mid = Memory::new(Galaxy::Codex, "mid".into());
        let mid_id = mid.metadata.id;
        store.put(Galaxy::Codex, &mid).unwrap();
        std::thread::sleep(std::time::Duration::from_millis(10));
        let t2 = chrono::Utc::now();

        let tx = store.env().begin_ro_txn().unwrap();
        let ids = store
            .index_dbs()
            .find_by_time_range(&tx, Galaxy::Codex, t0, t2)
            .unwrap();
        tx.commit().unwrap();

        assert_eq!(ids.len(), 1);
        assert_eq!(ids[0], mid_id);
    }

    #[test]
    fn delete_removes_index_entries() {
        let (_tmp, store) = setup();
        let mem = Memory::new(Galaxy::Codex, "test".into())
            .with_tags(vec!["tag1".into()])
            .with_importance(0.7);
        let id = mem.metadata.id;
        let hash = mem.metadata.content_hash.clone();
        store.put(Galaxy::Codex, &mem).unwrap();

        // Verify index entries exist
        let tx = store.env().begin_ro_txn().unwrap();
        assert!(
            store
                .index_dbs()
                .find_by_content_hash(&tx, Galaxy::Codex, &hash)
                .unwrap()
                .is_some()
        );
        assert_eq!(
            store
                .index_dbs()
                .find_by_tag(&tx, Galaxy::Codex, "tag1")
                .unwrap()
                .len(),
            1
        );
        tx.commit().unwrap();

        // Delete
        store.delete(Galaxy::Codex, id).unwrap();

        // Verify index entries are gone
        let tx = store.env().begin_ro_txn().unwrap();
        assert!(
            store
                .index_dbs()
                .find_by_content_hash(&tx, Galaxy::Codex, &hash)
                .unwrap()
                .is_none()
        );
        assert_eq!(
            store
                .index_dbs()
                .find_by_tag(&tx, Galaxy::Codex, "tag1")
                .unwrap()
                .len(),
            0
        );
        tx.commit().unwrap();
    }

    #[test]
    fn put_batch_updates_indexes() {
        let (_tmp, store) = setup();
        let memories: Vec<Memory> = (0..5)
            .map(|i| {
                Memory::new(Galaxy::Codex, format!("batch-{i}"))
                    .with_tags(vec![format!("tag{i}")])
                    .with_importance(i as f32 * 0.2)
            })
            .collect();
        store.put_batch(Galaxy::Codex, &memories).unwrap();

        let tx = store.env().begin_ro_txn().unwrap();
        for i in 0..5 {
            let ids = store
                .index_dbs()
                .find_by_tag(&tx, Galaxy::Codex, &format!("tag{i}"))
                .unwrap();
            assert_eq!(ids.len(), 1, "tag{i} should have 1 entry");
        }
        tx.commit().unwrap();
    }

    #[test]
    fn find_by_content_hash_indexed_matches_scan() {
        let (_tmp, store) = setup();
        let mem = Memory::new(Galaxy::Codex, "dedup test".into());
        let id = mem.metadata.id;
        let hash = mem.metadata.content_hash.clone();
        store.put(Galaxy::Codex, &mem).unwrap();

        // Indexed lookup
        let tx = store.env().begin_ro_txn().unwrap();
        let indexed = store
            .index_dbs()
            .find_by_content_hash(&tx, Galaxy::Codex, &hash)
            .unwrap();
        tx.commit().unwrap();

        // Scan-based lookup (old method)
        let scanned = store
            .find_by_content_hash_scan(Galaxy::Codex, &hash)
            .unwrap();

        assert_eq!(indexed, scanned);
        assert_eq!(indexed, Some(id));
    }

    #[test]
    fn key_encoding_sorts_correctly() {
        // Verify that encoded f32 values sort in the same order as the floats
        let values = [0.0_f32, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0];
        let encoded: Vec<[u8; 4]> = values.map(encode_f32).to_vec();
        for i in 0..encoded.len() - 1 {
            assert!(
                encoded[i] < encoded[i + 1],
                "f32 sort order broken: {:?} >= {:?}",
                values[i],
                values[i + 1]
            );
        }
    }
}
