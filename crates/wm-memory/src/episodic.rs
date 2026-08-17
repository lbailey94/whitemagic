//! LMDB persistence for the v6 lossless episodic memory lane.

use lmdb::{Cursor, Database, Environment, Transaction, WriteFlags};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use wm_core::{
    CoreError, EpisodicCapturePolicy, EpisodicId, EpisodicRecord, MemoryTransition, Result,
    ValidityState,
};

use crate::search::strip_stopwords;

/// Deterministic raw episodic search result.
#[derive(Debug, Clone)]
pub struct EpisodicSearchResult {
    pub record: EpisodicRecord,
    pub score: f32,
    pub matched_terms: usize,
}

/// Dedicated persistence view over the episodic-record LMDB database.
pub struct EpisodicStore<'a> {
    env: &'a Environment,
    db: Database,
    term_db: Database,
    term_cache: Arc<RwLock<HashMap<String, Vec<EpisodicId>>>>,
    mutation_count: &'a std::sync::atomic::AtomicU64,
}

impl<'a> EpisodicStore<'a> {
    pub(crate) const fn new(
        env: &'a Environment,
        db: Database,
        term_db: Database,
        term_cache: Arc<RwLock<HashMap<String, Vec<EpisodicId>>>>,
        mutation_count: &'a std::sync::atomic::AtomicU64,
    ) -> Self {
        Self {
            env,
            db,
            term_db,
            term_cache,
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
        // The raw record is authoritative. A projection failure is returned
        // after the raw commit so callers can rebuild the sidecar without
        // losing the source record.
        self.index_record(record)?;
        if let Ok(mut cache) = self.term_cache.write() {
            cache.clear();
        }
        Ok(())
    }

    fn term_postings(&self, term: &str) -> Result<Vec<EpisodicId>> {
        if let Ok(cache) = self.term_cache.read() {
            if let Some(ids) = cache.get(term) {
                return Ok(ids.clone());
            }
        }

        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("episodic index ro_txn failed: {e}")))?;
        let term_key = term.to_string();
        let ids = match tx.get(self.term_db, &term_key) {
            Ok(bytes) => rmp_serde::from_slice(bytes).map_err(|e| {
                CoreError::Memory(format!("episodic term index deserialize failed: {e}"))
            })?,
            Err(lmdb::Error::NotFound) => Vec::new(),
            Err(e) => {
                return Err(CoreError::Memory(format!(
                    "episodic term index read failed: {e}"
                )));
            }
        };
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("episodic index commit failed: {e}")))?;
        if let Ok(mut cache) = self.term_cache.write() {
            cache.insert(term_key, ids.clone());
        }
        Ok(ids)
    }

    fn index_record(&self, record: &EpisodicRecord) -> Result<()> {
        if record.is_private || record.model_exclude {
            return Ok(());
        }
        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("episodic index rw_txn failed: {e}")))?;
        for term in tokenize(&record.content) {
            let mut ids: Vec<EpisodicId> = match tx.get(self.term_db, &term) {
                Ok(bytes) => rmp_serde::from_slice(bytes).map_err(|e| {
                    CoreError::Memory(format!("episodic term index deserialize failed: {e}"))
                })?,
                Err(lmdb::Error::NotFound) => Vec::new(),
                Err(e) => {
                    tx.abort();
                    return Err(CoreError::Memory(format!(
                        "episodic term index read failed: {e}"
                    )));
                }
            };
            if !ids.contains(&record.id) {
                ids.push(record.id);
            }
            let value = rmp_serde::to_vec(&ids).map_err(|e| {
                CoreError::Memory(format!("episodic term index serialize failed: {e}"))
            })?;
            tx.put(self.term_db, &term, &value, WriteFlags::default())
                .map_err(|e| CoreError::Memory(format!("episodic term index write failed: {e}")))?;
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("episodic term index commit failed: {e}")))?;
        Ok(())
    }

    /// Append an explicit record according to the capture policy.
    pub fn append_explicit(
        &self,
        record: &EpisodicRecord,
        policy: EpisodicCapturePolicy,
    ) -> Result<bool> {
        let prepared = record
            .clone()
            .with_content(policy.prepare_content(&record.content));
        self.append(&prepared)?;
        Ok(true)
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

    /// Search current episodic records using deterministic token overlap.
    ///
    /// This is a v6 library path only. It does not alter the v5 MCP search
    /// route and keeps source records attached to every hit.
    pub fn search(
        &self,
        query: &str,
        limit: usize,
        include_historical: bool,
    ) -> Result<Vec<EpisodicSearchResult>> {
        self.search_with_limits(query, limit, limit.saturating_mul(2), include_historical)
    }

    /// Search with an explicit candidate budget before selective reranking.
    pub fn search_with_limits(
        &self,
        query: &str,
        limit: usize,
        candidate_limit: usize,
        include_historical: bool,
    ) -> Result<Vec<EpisodicSearchResult>> {
        let query_terms = tokenize(query);
        if query_terms.is_empty() || limit == 0 {
            return Ok(Vec::new());
        }
        let mut candidate_scores: HashMap<EpisodicId, usize> = HashMap::new();
        for term in &query_terms {
            for id in self.term_postings(term)? {
                *candidate_scores.entry(id).or_default() += 1;
            }
        }

        let records = if candidate_scores.is_empty() {
            // Existing stores or a degraded projection can still be searched.
            self.scan(None, usize::MAX)?
        } else {
            let mut ranked_candidates: Vec<(EpisodicId, usize)> =
                candidate_scores.into_iter().collect();
            ranked_candidates.sort_by(|(left_id, left_count), (right_id, right_count)| {
                right_count
                    .cmp(left_count)
                    .then_with(|| left_id.cmp(right_id))
            });
            ranked_candidates.truncate(candidate_limit.max(limit));
            self.load_records(
                &ranked_candidates
                    .into_iter()
                    .map(|(id, _)| id)
                    .collect::<Vec<_>>(),
            )?
        };
        let mut results = Vec::new();
        for record in records {
            if !include_historical && !matches!(record.validity, ValidityState::Active) {
                continue;
            }
            let content_terms = tokenize(&record.content);
            let matched_terms = query_terms
                .iter()
                .filter(|term| content_terms.iter().any(|candidate| candidate == *term))
                .count();
            if matched_terms == 0 {
                continue;
            }
            let coverage = matched_terms as f32 / query_terms.len() as f32;
            let density = matched_terms as f32 / content_terms.len().max(1) as f32;
            results.push(EpisodicSearchResult {
                record,
                score: coverage + density * 0.01,
                matched_terms,
            });
        }
        results.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| b.record.sequence.cmp(&a.record.sequence))
                .then_with(|| a.record.id.cmp(&b.record.id))
        });
        results.truncate(limit);
        Ok(results)
    }

    fn load_records(&self, ids: &[EpisodicId]) -> Result<Vec<EpisodicRecord>> {
        let tx = self
            .env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("episodic ro_txn failed: {e}")))?;
        let mut records = Vec::with_capacity(ids.len());
        for id in ids {
            match tx.get(self.db, id.as_bytes()) {
                Ok(bytes) => {
                    records.push(rmp_serde::from_slice(bytes).map_err(|e| {
                        CoreError::Memory(format!("episodic deserialize failed: {e}"))
                    })?);
                }
                Err(lmdb::Error::NotFound) => {}
                Err(e) => return Err(CoreError::Memory(format!("episodic get failed: {e}"))),
            }
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("episodic commit failed: {e}")))?;
        Ok(records)
    }
}

fn tokenize(text: &str) -> Vec<String> {
    strip_stopwords(text)
        .split(|c: char| !c.is_alphanumeric())
        .filter(|term| term.len() > 1)
        .map(|term| simple_stem(&term.to_ascii_lowercase()))
        .fold(Vec::new(), |mut terms, term| {
            if !terms.contains(&term) {
                terms.push(term);
            }
            terms
        })
}

fn simple_stem(word: &str) -> String {
    if word.len() <= 3 {
        return word.to_string();
    }
    for suffix in ["ies", "ied", "ing", "edly", "ed", "ly", "es", "s"] {
        if let Some(stem) = word.strip_suffix(suffix) {
            if suffix == "ies" || suffix == "ied" {
                return format!("{stem}y");
            }
            if stem.len() >= 2 {
                return stem.to_string();
            }
        }
    }
    word.to_string()
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

    #[test]
    fn raw_search_returns_canonical_records_and_skips_revoked_by_default() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let active = EpisodicRecord::new(
            None,
            1,
            EpisodicKind::Observation,
            "Rust memory retrieval",
            Provenance::new(ProvenanceSource::User),
        );
        let revoked = EpisodicRecord::new(
            None,
            2,
            EpisodicKind::Observation,
            "Rust memory retrieval old",
            Provenance::new(ProvenanceSource::User),
        );
        let revoked_id = revoked.id;
        store.episodic().append(&active).unwrap();
        store.episodic().append(&revoked).unwrap();
        store
            .episodic()
            .transition(
                revoked_id,
                MemoryTransition::Revoke {
                    reason: "stale".into(),
                },
            )
            .unwrap();

        let current = store
            .episodic()
            .search("memory retrieval", 10, false)
            .unwrap();
        assert_eq!(current.len(), 1);
        assert_eq!(current[0].record.id, active.id);

        let all = store
            .episodic()
            .search("memory retrieval", 10, true)
            .unwrap();
        assert_eq!(all.len(), 2);
    }
}
