//! LMDB persistence for the v6 lossless episodic memory lane.

use lmdb::{Cursor, Database, Environment, Transaction, WriteFlags};
use wm_core::{CoreError, EpisodicId, EpisodicRecord, MemoryTransition, Result};

/// Dedicated persistence view over the episodic-record LMDB database.
pub struct EpisodicStore<'a> {
    env: &'a Environment,
    db: Database,
    mutation_count: &'a std::sync::atomic::AtomicU64,
}

impl<'a> EpisodicStore<'a> {
    pub(crate) const fn new(
        env: &'a Environment,
        db: Database,
        mutation_count: &'a std::sync::atomic::AtomicU64,
    ) -> Self {
        Self {
            env,
            db,
            mutation_count,
        }
    }

    /// Append a source record without allowing an existing raw ID to be overwritten.
    pub fn append(&self, record: &EpisodicRecord) -> Result<()> {
        let value = rmp_serde::to_vec(record)
            .map_err(|e| CoreError::Memory(format!("episodic serialize failed: {e}")))?;
        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("episodic rw_txn failed: {e}")))?;
        match tx.put(
            self.db,
            record.id.as_bytes(),
            &value,
            WriteFlags::NO_OVERWRITE,
        ) {
            Ok(()) => {}
            Err(lmdb::Error::KeyExist) => {
                tx.abort();
                return Err(CoreError::InvalidArgs(format!(
                    "episodic record {} already exists",
                    record.id
                )));
            }
            Err(e) => {
                tx.abort();
                return Err(CoreError::Memory(format!("episodic append failed: {e}")));
            }
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("episodic commit failed: {e}")))?;
        self.mutation_count
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        Ok(())
    }

    /// Read an episodic record by its canonical ID.
    pub fn get(&self, id: EpisodicId) -> Result<Option<EpisodicRecord>> {
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("episodic ro_txn failed: {e}")))?;
        let result = tx.get(self.db, id.as_bytes());
        match result {
            Ok(bytes) => {
                let record: EpisodicRecord = rmp_serde::from_slice(bytes)
                    .map_err(|e| CoreError::Memory(format!("episodic deserialize failed: {e}")))?;
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("episodic commit failed: {e}")))?;
                Ok(Some(record))
            }
            Err(lmdb::Error::NotFound) => {
                tx.commit()
                    .map_err(|e| CoreError::Memory(format!("episodic commit failed: {e}")))?;
                Ok(None)
            }
            Err(e) => Err(CoreError::Memory(format!("episodic get failed: {e}"))),
        }
    }

    /// Apply an explicit lifecycle transition to a persisted record.
    pub fn transition(&self, id: EpisodicId, transition: MemoryTransition) -> Result<()> {
        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("episodic rw_txn failed: {e}")))?;
        let bytes = match tx.get(self.db, id.as_bytes()) {
            Ok(bytes) => bytes,
            Err(lmdb::Error::NotFound) => {
                tx.abort();
                return Err(CoreError::InvalidArgs(format!(
                    "episodic record {id} does not exist"
                )));
            }
            Err(e) => {
                tx.abort();
                return Err(CoreError::Memory(format!("episodic get failed: {e}")));
            }
        };
        let mut record: EpisodicRecord = rmp_serde::from_slice(bytes)
            .map_err(|e| CoreError::Memory(format!("episodic deserialize failed: {e}")))?;
        record
            .transition(transition)
            .map_err(|e| CoreError::InvalidArgs(format!("episodic transition rejected: {e}")))?;
        let value = rmp_serde::to_vec(&record)
            .map_err(|e| CoreError::Memory(format!("episodic serialize failed: {e}")))?;
        tx.put(self.db, id.as_bytes(), &value, WriteFlags::default())
            .map_err(|e| CoreError::Memory(format!("episodic transition write failed: {e}")))?;
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("episodic commit failed: {e}")))?;
        self.mutation_count
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        Ok(())
    }

    /// Return records in sequence order, optionally restricted to a session.
    pub fn scan(
        &self,
        session_id: Option<uuid::Uuid>,
        limit: usize,
    ) -> Result<Vec<EpisodicRecord>> {
        if limit == 0 {
            return Ok(Vec::new());
        }
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("episodic ro_txn failed: {e}")))?;
        let mut cursor = tx
            .open_ro_cursor(self.db)
            .map_err(|e| CoreError::Memory(format!("episodic cursor failed: {e}")))?;
        let mut records = Vec::new();
        for item in cursor.iter() {
            let (_, bytes) = item;
            let record: EpisodicRecord = rmp_serde::from_slice(bytes)
                .map_err(|e| CoreError::Memory(format!("episodic deserialize failed: {e}")))?;
            if session_id.is_none_or(|id| record.session_id == Some(id)) {
                records.push(record);
            }
        }
        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("episodic commit failed: {e}")))?;
        records.sort_by_key(|record| (record.sequence, record.created_at, record.id));
        records.truncate(limit);
        Ok(records)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::MemoryStore;
    use tempfile::tempdir;
    use wm_core::{EpisodicKind, Provenance, ProvenanceSource, ValidityState};

    #[test]
    fn append_get_transition_and_reopen_roundtrip() {
        let tmp = tempdir().unwrap();
        let session = uuid::Uuid::new_v4();
        let record = EpisodicRecord::new(
            Some(session),
            2,
            EpisodicKind::Decision,
            "use the raw episodic lane",
            Provenance::new(ProvenanceSource::User).with_actor("test"),
        );
        let id = record.id;
        {
            let store = MemoryStore::open_default(tmp.path()).unwrap();
            let episodic = store.episodic();
            episodic.append(&record).unwrap();
            assert_eq!(episodic.get(id).unwrap().unwrap(), record);
            episodic
                .transition(
                    id,
                    MemoryTransition::Supersede {
                        replacement: uuid::Uuid::new_v4(),
                    },
                )
                .unwrap();
            assert!(matches!(
                episodic.get(id).unwrap().unwrap().validity,
                ValidityState::Superseded { .. }
            ));
        }
        let reopened = MemoryStore::open_default(tmp.path()).unwrap();
        let records = reopened.episodic().scan(Some(session), 10).unwrap();
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].id, id);
    }

    #[test]
    fn duplicate_append_is_rejected() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let record = EpisodicRecord::new(
            None,
            1,
            EpisodicKind::Observation,
            "once",
            Provenance::new(ProvenanceSource::System),
        );
        store.episodic().append(&record).unwrap();
        let error = store.episodic().append(&record).unwrap_err();
        assert!(error.to_string().contains("already exists"));
    }
}
