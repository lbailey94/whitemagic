//! LMDB persistence for the v6 lossless episodic memory lane.

use lmdb::{Cursor, Database, Environment, Transaction, WriteFlags};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use wm_core::{
    CoreError, EpisodicCapturePolicy, EpisodicId, EpisodicRecord, MemoryTransition, Result,
    ValidityState,
};

use crate::episodic_keys::key_index_terms;
use crate::query_planner::QueryPlan;
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
        self.append_batch(std::slice::from_ref(record))
    }

    /// Append many source records, then project them into the sidecar in one
    /// term-index transaction.
    pub fn append_batch(&self, records: &[EpisodicRecord]) -> Result<()> {
        if records.is_empty() {
            return Ok(());
        }
        let serialized = records
            .iter()
            .map(|record| {
                rmp_serde::to_vec(record)
                    .map(|value| (record, value))
                    .map_err(|e| CoreError::Memory(format!("episodic serialize failed: {e}")))
            })
            .collect::<Result<Vec<_>>>()?;
        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("episodic rw_txn failed: {e}")))?;
        for (record, value) in &serialized {
            match tx.put(
                self.db,
                record.id.as_bytes(),
                value,
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
        }
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("episodic commit failed: {e}")))?;
        self.mutation_count
            .fetch_add(records.len() as u64, std::sync::atomic::Ordering::Relaxed);
        // The raw record is authoritative. A projection failure is returned
        // after the raw commit so callers can rebuild the sidecar without
        // losing the source record.
        self.index_records(records)?;
        self.clear_term_cache();
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

    fn clear_term_cache(&self) {
        if let Ok(mut cache) = self.term_cache.write() {
            cache.clear();
        }
    }

    fn index_records(&self, records: &[EpisodicRecord]) -> Result<()> {
        let public: Vec<&EpisodicRecord> = records
            .iter()
            .filter(|record| !record.is_private && !record.model_exclude)
            .collect();
        if public.is_empty() {
            return Ok(());
        }
        let mut pending: HashMap<String, Vec<EpisodicId>> = HashMap::new();
        for record in public {
            for term in index_terms(&record.content) {
                let ids = pending.entry(term).or_default();
                if !ids.contains(&record.id) {
                    ids.push(record.id);
                }
            }
        }
        let mut tx = self
            .env
            .begin_rw_txn()
            .map_err(|e| CoreError::Memory(format!("episodic index rw_txn failed: {e}")))?;
        for (term, new_ids) in pending {
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
            for id in new_ids {
                if !ids.contains(&id) {
                    ids.push(id);
                }
            }
            let value = rmp_serde::to_vec(&ids).map_err(|e| {
                CoreError::Memory(format!("episodic term index serialize failed: {e}"))
            })?;
            if let Err(e) = tx.put(self.term_db, &term, &value, WriteFlags::default()) {
                tx.abort();
                return Err(CoreError::Memory(format!(
                    "episodic term index write failed: {e}"
                )));
            }
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

    /// Append many explicit records according to the capture policy.
    pub fn append_explicit_batch(
        &self,
        records: &[EpisodicRecord],
        policy: EpisodicCapturePolicy,
    ) -> Result<usize> {
        if records.is_empty() {
            return Ok(0);
        }
        let prepared: Vec<EpisodicRecord> = records
            .iter()
            .map(|record| {
                record
                    .clone()
                    .with_content(policy.prepare_content(&record.content))
            })
            .collect();
        self.append_batch(&prepared)?;
        Ok(prepared.len())
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
        let plan = QueryPlan::plan(query, limit);
        let candidate_limit = candidate_limit.max(plan.candidate_limit);
        let query_terms = tokenize(query);
        let query_keys = key_index_terms(query);
        if query_terms.is_empty() && query_keys.is_empty() || limit == 0 {
            return Ok(Vec::new());
        }
        let mut candidate_scores: HashMap<EpisodicId, usize> = HashMap::new();
        for term in query_terms.iter().chain(query_keys.iter()) {
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
            let content_keys = key_index_terms(&record.content);
            let matched_terms = query_terms
                .iter()
                .filter(|term| {
                    content_terms.iter().any(|candidate| candidate == *term)
                        || content_keys.iter().any(|candidate| candidate == *term)
                })
                .count();
            let matched_keys = query_keys
                .iter()
                .filter(|term| {
                    content_keys.iter().any(|candidate| candidate == *term)
                        || content_terms.iter().any(|candidate| candidate == *term)
                })
                .count();
            if matched_terms == 0 && matched_keys == 0 {
                continue;
            }
            let coverage = if query_terms.is_empty() {
                0.0
            } else {
                matched_terms as f32 / query_terms.len() as f32
            };
            let density = matched_terms as f32 / content_terms.len().max(1) as f32;
            let key_bonus = if query_keys.is_empty() {
                0.0
            } else {
                matched_keys as f32 / query_keys.len() as f32 * plan.key_weight
            };
            results.push(EpisodicSearchResult {
                record,
                score: coverage + density * 0.01 + key_bonus,
                matched_terms: matched_terms.max(matched_keys),
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

fn index_terms(text: &str) -> Vec<String> {
    tokenize(text)
        .into_iter()
        .chain(key_index_terms(text))
        .fold(Vec::new(), |mut terms, term| {
            if !terms.contains(&term) {
                terms.push(term);
            }
            terms
        })
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

    fn sample_record(sequence: u64, content: &str) -> EpisodicRecord {
        EpisodicRecord::new(
            None,
            sequence,
            EpisodicKind::Observation,
            content,
            Provenance::new(ProvenanceSource::User),
        )
    }

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
        let record = sample_record(1, "once");
        store.episodic().append(&record).unwrap();
        let error = store.episodic().append(&record).unwrap_err();
        assert!(error.to_string().contains("already exists"));
    }

    #[test]
    fn raw_search_returns_canonical_records_and_skips_revoked_by_default() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let active = sample_record(1, "Rust memory retrieval");
        let revoked = sample_record(2, "Rust memory retrieval old");
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

    #[test]
    fn append_batch_indexes_once_and_preserves_search() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let first = sample_record(1, "Dr. Patel scheduled a follow-up appointment");
        let second = sample_record(2, "unrelated grocery list");
        let first_id = first.id;
        store.episodic().append_batch(&[first, second]).unwrap();
        let hits = store
            .episodic()
            .search("patel appointment", 10, false)
            .unwrap();
        assert_eq!(hits.len(), 1);
        assert_eq!(hits[0].record.id, first_id);
    }

    #[test]
    fn append_explicit_batch_redacts_and_skips_private() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let public = sample_record(1, "api_key=supersecret rust retrieval");
        let private = sample_record(2, "private rust retrieval").with_visibility(true, false);
        let public_id = public.id;
        store
            .episodic()
            .append_explicit_batch(&[public, private], EpisodicCapturePolicy::explicit_only())
            .unwrap();
        let stored = store.episodic().get(public_id).unwrap().unwrap();
        assert!(stored.content.contains("<REDACTED>"));
        let hits = store
            .episodic()
            .search("rust retrieval", 10, false)
            .unwrap();
        assert_eq!(hits.len(), 1);
        assert_eq!(hits[0].record.id, public_id);
    }

    #[test]
    fn typed_keys_retrieve_vocabulary_mismatch() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let dog = sample_record(1, "My Golden Retriever loves the park");
        let other = sample_record(2, "I bought a yellow dress");
        let dog_id = dog.id;
        store.episodic().append_batch(&[dog, other]).unwrap();
        let hits = store
            .episodic()
            .search("What breed is my dog?", 5, false)
            .unwrap();
        assert_eq!(hits[0].record.id, dog_id);
    }

    #[test]
    fn planner_boosts_temporal_date_match() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let dated = sample_record(1, "I volunteered on February 14th at the animal shelter");
        let other = sample_record(2, "I volunteered at the community garden last summer");
        let dated_id = dated.id;
        store.episodic().append_batch(&[dated, other]).unwrap();
        let hits = store
            .episodic()
            .search("When did I volunteer at the animal shelter?", 5, false)
            .unwrap();
        assert_eq!(hits[0].record.id, dated_id);
    }

    #[test]
    #[ignore = "manual in-process latency profile"]
    fn profile_ingest_and_search_latency() {
        fn timed_ms(label: &str, repeats: u32, mut work: impl FnMut()) {
            let start = std::time::Instant::now();
            for _ in 0..repeats {
                work();
            }
            let elapsed = start.elapsed();
            println!(
                "{label}: {:.3} ms (n={repeats})",
                elapsed.as_secs_f64() * 1000.0 / f64::from(repeats)
            );
        }

        let search_records: Vec<EpisodicRecord> = (0..10_000)
            .map(|n| {
                sample_record(
                    n,
                    if n % 5 == 0 {
                        "Rust memory retrieval benchmark item"
                    } else {
                        "Unrelated episodic record"
                    },
                )
            })
            .collect();

        timed_ms("append_single_1000", 1, || {
            let tmp = tempdir().unwrap();
            let store = MemoryStore::open_default(tmp.path()).unwrap();
            for n in 0..1_000 {
                store.episodic().append(&sample_record(n, "once")).unwrap();
            }
        });
        timed_ms("append_batch_1000", 1, || {
            let tmp = tempdir().unwrap();
            let store = MemoryStore::open_default(tmp.path()).unwrap();
            let records: Vec<EpisodicRecord> =
                (0..1_000).map(|n| sample_record(n, "once")).collect();
            store.episodic().append_batch(&records).unwrap();
        });

        let tmp = tempdir().unwrap();
        {
            let store = MemoryStore::open_default(tmp.path()).unwrap();
            store.episodic().append_batch(&search_records).unwrap();
        }
        let cold = MemoryStore::open_default(tmp.path()).unwrap();
        timed_ms("cold_search_10000", 1, || {
            let hits = cold
                .episodic()
                .search("rust memory retrieval", 10, false)
                .unwrap();
            assert!(!hits.is_empty());
        });
        timed_ms("warm_search_10000", 50, || {
            let hits = cold
                .episodic()
                .search("rust memory retrieval", 10, false)
                .unwrap();
            assert!(!hits.is_empty());
        });
    }
}
