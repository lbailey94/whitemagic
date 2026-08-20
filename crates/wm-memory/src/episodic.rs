//! LMDB persistence for the v6 lossless episodic memory lane.

use lmdb::{Cursor, Database, Environment, Transaction, WriteFlags};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use wm_core::{
    CoreError, EpisodicCapturePolicy, EpisodicId, EpisodicKind, EpisodicRecord, MemoryTransition,
    Result, ValidityState,
};

use crate::embedder::Embedder;
use crate::enrichment::VocabularyEnrichment;
use crate::episodic_keys::{AdaptiveAliases, key_index_terms_with_aliases};
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
    embedder: Option<Arc<dyn Embedder + Send + Sync>>,
    aliases: Option<AdaptiveAliases>,
    enrichment: Option<VocabularyEnrichment>,
}

impl<'a> EpisodicStore<'a> {
    pub(crate) fn new(
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
            embedder: None,
            aliases: None,
            enrichment: None,
        }
    }

    /// Attach adaptive aliases for query and ingest-time key expansion.
    #[must_use]
    pub fn with_adaptive_aliases(mut self, aliases: AdaptiveAliases) -> Self {
        if !aliases.is_empty() {
            self.aliases = Some(aliases);
        }
        self
    }

    /// Attach vocabulary enrichment for index-time term expansion.
    #[must_use]
    pub fn with_enrichment(mut self, enrichment: VocabularyEnrichment) -> Self {
        if !enrichment.is_empty() {
            self.enrichment = Some(enrichment);
        }
        self
    }

    /// Attach an embedder for vector reranking.
    #[must_use]
    pub fn with_embedder(mut self, embedder: Arc<dyn Embedder + Send + Sync>) -> Self {
        self.embedder = Some(embedder);
        self
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
            let base_terms = index_terms_with_aliases(&record.content, self.aliases.as_ref());
            let enriched: Vec<String> = if let Some(ref enrichment) = self.enrichment {
                let mut all = base_terms.clone();
                let extra = enrichment.enrich(&base_terms);
                all.extend(extra);
                all.sort();
                all.dedup();
                all
            } else {
                base_terms
            };
            for term in enriched {
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
    ///
    /// When the query asks for the current/latest value of something
    /// (see [`is_current_query`]), the topic cluster is reordered by
    /// deterministic chronology so the most recent statement outranks older
    /// ones — post-retrieval temporal resolution, not a scoring change.
    pub fn search(
        &self,
        query: &str,
        limit: usize,
        include_historical: bool,
    ) -> Result<Vec<EpisodicSearchResult>> {
        self.search_with_limits(query, limit, limit.saturating_mul(2), include_historical)
    }

    /// Search with an explicit candidate budget before selective reranking.
    ///
    /// Uses multi-query pool widening: the original query plus sub-queries
    /// focused on key content words generate candidate IDs. All candidates are
    /// then scored with the primary query's deterministic scoring. This helps
    /// answer turns that match few original query terms but match the key
    /// entity strongly enter the candidate pool.
    pub fn search_with_limits(
        &self,
        query: &str,
        limit: usize,
        candidate_limit: usize,
        include_historical: bool,
    ) -> Result<Vec<EpisodicSearchResult>> {
        if limit == 0 {
            return Ok(Vec::new());
        }
        let mut results = self.search_scored(query, limit, candidate_limit, include_historical)?;
        if is_current_query(query) {
            self.resolve_current(&mut results);
        }
        results.truncate(limit);
        Ok(results)
    }

    /// Deterministic scoring pipeline without temporal resolution or
    /// truncation: candidates → scoring → boosts → score sort. `limit` is
    /// used only for query-class planning (candidate budgets); the caller
    /// truncates.
    fn search_scored(
        &self,
        query: &str,
        limit: usize,
        candidate_limit: usize,
        include_historical: bool,
    ) -> Result<Vec<EpisodicSearchResult>> {
        let plan = QueryPlan::plan(query, limit);
        let candidate_limit = candidate_limit.max(plan.candidate_limit);
        let query_terms = tokenize(query);
        let query_keys = key_index_terms_with_aliases(query, self.aliases.as_ref());
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
            ranked_candidates.truncate(candidate_limit);
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
            let content_keys = key_index_terms_with_aliases(&record.content, self.aliases.as_ref());
            // For UserStatement records, also count reverse-enrichment matches:
            // if the query has "play" and the content has "production", count
            // it as a match. This bridges the vocabulary gap for answer turns
            // without boosting competing Assistant turns.
            let reverse_map: HashMap<&String, Vec<String>> =
                if let Some(ref enrichment) = self.enrichment {
                    if matches!(record.kind, EpisodicKind::UserStatement) {
                        query_terms
                            .iter()
                            .map(|qt| (qt, enrichment.reverse_enrich(qt)))
                            .collect()
                    } else {
                        HashMap::new()
                    }
                } else {
                    HashMap::new()
                };
            let mut reverse_match_count = 0usize;
            let matched_terms = query_terms
                .iter()
                .filter(|term| {
                    if content_terms.iter().any(|candidate| candidate == *term)
                        || content_keys.iter().any(|candidate| candidate == *term)
                    {
                        return true;
                    }
                    // Check reverse enrichment: does the content have any term
                    // that maps to this query term?
                    if let Some(reverse_terms) = reverse_map.get(term) {
                        let found = reverse_terms.iter().any(|rt| {
                            content_terms.iter().any(|candidate| candidate == rt)
                                || content_keys.iter().any(|candidate| candidate == rt)
                        });
                        if found {
                            reverse_match_count += 1;
                        }
                        return found;
                    }
                    false
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
            let key_bonus = if query_keys.is_empty() {
                0.0
            } else {
                matched_keys as f32 / query_keys.len() as f32 * plan.key_weight
            };
            let role_boost = match record.kind {
                EpisodicKind::UserStatement => 0.12,
                _ => 0.0,
            };
            let effective_matched = if matches!(record.kind, EpisodicKind::UserStatement) {
                (matched_terms + 2).min(query_terms.len())
            } else {
                matched_terms
            };
            let coverage = if query_terms.is_empty() {
                0.0
            } else {
                effective_matched as f32 / query_terms.len() as f32
            };
            let number_bonus = if plan.number_query {
                let has_digit = content_terms
                    .iter()
                    .any(|term| term.chars().any(|c| c.is_ascii_digit()));
                if has_digit || contains_number_word(&record.content) {
                    0.03
                } else {
                    0.0
                }
            } else {
                0.0
            };
            let density = matched_terms as f32 / content_terms.len().max(1) as f32;
            results.push(EpisodicSearchResult {
                record,
                score: coverage
                    + key_bonus
                    + role_boost
                    + number_bonus
                    + (reverse_match_count as f32).mul_add(0.05, density * 0.03),
                matched_terms: matched_terms.max(matched_keys),
            });
        }
        // Session-aware RRF boost: turns from sessions with multiple matching
        // turns get a small score boost. This is a simplified RRF that preserves
        // the deterministic score scale for the reranking pipeline.
        let mut session_counts: HashMap<Option<uuid::Uuid>, usize> = HashMap::new();
        for r in &results {
            *session_counts.entry(r.record.session_id).or_default() += 1;
        }
        for r in &mut results {
            let count = session_counts
                .get(&r.record.session_id)
                .copied()
                .unwrap_or(1);
            if count > 1 {
                r.score += 0.02 * (count - 1).min(3) as f32;
            }
        }
        // Content-frequency boost (consolidation): if the same content hash
        // appears multiple times in the result set, boost all instances. This
        // simulates consolidation — facts mentioned repeatedly are more
        // important. The boost is small (0.03 per duplicate, max 0.09) to
        // avoid distorting the score scale.
        let mut hash_counts: HashMap<&str, usize> = HashMap::new();
        for r in &results {
            *hash_counts
                .entry(r.record.content_hash.as_str())
                .or_default() += 1;
        }
        let hash_boosts: HashMap<String, f32> = results
            .iter()
            .map(|r| {
                let count = hash_counts
                    .get(r.record.content_hash.as_str())
                    .copied()
                    .unwrap_or(1);
                let boost = if count > 1 {
                    0.03 * (count - 1).min(3) as f32
                } else {
                    0.0
                };
                (r.record.id.to_string(), boost)
            })
            .collect();
        for r in &mut results {
            if let Some(boost) = hash_boosts.get(&r.record.id.to_string()) {
                r.score += boost;
            }
        }
        results.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| b.matched_terms.cmp(&a.matched_terms))
                .then_with(|| a.record.content.len().cmp(&b.record.content.len()))
                .then_with(|| a.record.sequence.cmp(&b.record.sequence))
                .then_with(|| a.record.id.cmp(&b.record.id))
        });
        Ok(results)
    }

    /// Search with vector reranking on top of deterministic scoring.
    ///
    /// Pipeline: deterministic scoring → top-N candidates → embed query +
    /// candidates → tiebreaker reranking → top-K.
    ///
    /// When `alpha < 1.0`, uses hybrid blending: score = α·det_norm + (1-α)·cosine.
    /// When `alpha >= 1.0`, uses tiebreaker mode: only reorders adjacent
    /// candidates whose deterministic scores are within δ=0.05, using cosine
    /// as the tiebreaker. This preserves correct rankings and only uses
    /// semantic similarity to break near-ties.
    ///
    /// Falls back to `search_with_limits()` when no embedder is attached.
    pub fn search_with_rerank(
        &self,
        query: &str,
        limit: usize,
        candidate_limit: usize,
        include_historical: bool,
        alpha: f32,
    ) -> Result<Vec<EpisodicSearchResult>> {
        let Some(ref embedder) = self.embedder else {
            return self.search_with_limits(query, limit, candidate_limit, include_historical);
        };
        if !embedder.is_available() || limit == 0 {
            return self.search_with_limits(query, limit, candidate_limit, include_historical);
        }

        // Over-fetch deterministic candidates for reranking.
        let rerank_pool = limit.max(candidate_limit).min(50);
        let deterministic =
            self.search_scored(query, rerank_pool, rerank_pool, include_historical)?;
        if deterministic.is_empty() {
            return Ok(Vec::new());
        }

        // Batch-embed query + all candidate contents in one call.
        let contents: Vec<&str> = std::iter::once(query)
            .chain(deterministic.iter().map(|r| r.record.content.as_str()))
            .collect();
        let embeddings = embedder.embed_batch(&contents)?;
        if embeddings.len() != deterministic.len() + 1 {
            return Err(CoreError::Memory(format!(
                "embedder returned {} vectors, expected {}",
                embeddings.len(),
                deterministic.len() + 1
            )));
        }
        let query_vec = &embeddings[0];
        let candidate_vecs = &embeddings[1..];

        if alpha >= 1.0 {
            // Tiebreaker mode: only reorder adjacent candidates with close det scores.
            let delta = 0.05;
            let mut reranked = deterministic;
            let cosines: Vec<f32> = candidate_vecs
                .iter()
                .map(|v| cosine_sim(query_vec, v))
                .collect();
            // Bubble-sort adjacent swaps only when det scores are within delta.
            let n = reranked.len();
            for _ in 0..n {
                let mut swapped = false;
                for i in 0..n.saturating_sub(1) {
                    let det_gap = (reranked[i].score - reranked[i + 1].score).abs();
                    if det_gap < delta && cosines[i + 1] > cosines[i] {
                        reranked.swap(i, i + 1);
                        swapped = true;
                    }
                }
                if !swapped {
                    break;
                }
            }
            if is_current_query(query) {
                self.resolve_current(&mut reranked);
            }
            reranked.truncate(limit);
            Ok(reranked)
        } else {
            // Hybrid blending mode.
            let max_det = deterministic
                .iter()
                .map(|r| r.score)
                .fold(0.0f32, f32::max)
                .max(1e-9);

            let mut reranked: Vec<EpisodicSearchResult> = deterministic
                .into_iter()
                .enumerate()
                .map(|(i, mut r)| {
                    let cosine = cosine_sim(query_vec, &candidate_vecs[i]);
                    let det_norm = r.score / max_det;
                    r.score = alpha.mul_add(det_norm, (1.0 - alpha) * cosine);
                    r
                })
                .collect();

            reranked.sort_by(|a, b| {
                b.score
                    .partial_cmp(&a.score)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then_with(|| b.matched_terms.cmp(&a.matched_terms))
                    .then_with(|| a.record.content.len().cmp(&b.record.content.len()))
                    .then_with(|| a.record.sequence.cmp(&b.record.sequence))
                    .then_with(|| a.record.id.cmp(&b.record.id))
            });
            if is_current_query(query) {
                self.resolve_current(&mut reranked);
            }
            reranked.truncate(limit);
            Ok(reranked)
        }
    }

    /// Post-retrieval temporal resolution for "current value" queries.
    ///
    /// When the user asks "What's my current favorite X?", the current-value
    /// statement often matches *fewer* query terms than an older statement
    /// ("my favorite coffee is dark roast" matches favorite+coffee, while
    /// "I switched to cold brew for coffee" matches only coffee), so pure
    /// score order prefers the stale fact. This layer instead promotes the
    /// currency signal directly:
    ///
    /// 1. Anchor set: `UserStatement` records containing a change marker
    ///    ("switched to", "changed my", "now prefer", "used to", ...) — the
    ///    user's own words that a value moved. Only user statements anchor:
    ///    the user's own statement is the authority for their current state,
    ///    and assistant echoes must not hijack chronology.
    /// 2. Anchors are ordered by deterministic chronology — `(created_at,
    ///    sequence)` descending — so the most recent change outranks earlier
    ///    ones (v1→v2→v3 chains resolve to v3).
    /// 3. Remaining results keep their deterministic score order behind the
    ///    anchors.
    ///
    /// Scoring is untouched and non-current queries take the identical path,
    /// so behavior for historical questions is unchanged by construction
    /// (see `docs/notes/research-2026-08-20-agent-memory.md`: the
    /// Post-Retrieval Assembly paper found the LongMemEval effect of
    /// temporal machinery insignificant, p=0.45 — the gain is on
    /// current-value questions, which is exactly what this targets).
    fn resolve_current(&self, results: &mut Vec<EpisodicSearchResult>) {
        if results.len() < 2 {
            return;
        }
        let mut anchors: Vec<EpisodicSearchResult> = Vec::new();
        let mut rest: Vec<EpisodicSearchResult> = Vec::new();
        for result in results.drain(..) {
            let is_anchor = matches!(result.record.kind, EpisodicKind::UserStatement)
                && contains_change_marker(&result.record.content);
            if is_anchor {
                anchors.push(result);
            } else {
                rest.push(result);
            }
        }
        if anchors.is_empty() {
            // No currency signal — keep the deterministic score order.
            *results = rest;
            return;
        }
        anchors.sort_by(|a, b| {
            b.record
                .created_at
                .cmp(&a.record.created_at)
                .then_with(|| b.record.sequence.cmp(&a.record.sequence))
                .then_with(|| a.record.id.cmp(&b.record.id))
        });
        anchors.extend(rest);
        *results = anchors;
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

fn index_terms_with_aliases(text: &str, aliases: Option<&AdaptiveAliases>) -> Vec<String> {
    tokenize(text)
        .into_iter()
        .chain(key_index_terms_with_aliases(text, aliases))
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

/// Single-word cues that ask for the current value of something.
const CURRENT_QUERY_WORD_CUES: &[&str] = &["current", "currently", "latest", "nowadays"];

/// Multi-word cues that ask for the current value of something.
const CURRENT_QUERY_PHRASE_CUES: &[&str] = &["these days", "right now", "at the moment"];

/// True when the query asks for the current/latest value of something,
/// e.g. "What's my current favorite coffee?".
///
/// Only such queries trigger post-retrieval temporal resolution
/// ([`EpisodicStore::resolve_current`]); all other queries take the
/// deterministic score order unchanged.
#[must_use]
pub fn is_current_query(query: &str) -> bool {
    let lowered = query.to_ascii_lowercase();
    let has_word = lowered
        .split(|c: char| !c.is_alphanumeric())
        .any(|token| CURRENT_QUERY_WORD_CUES.contains(&token));
    has_word
        || CURRENT_QUERY_PHRASE_CUES
            .iter()
            .any(|cue| lowered.contains(cue))
}

/// Phrase markers that a stated value has changed — the currency signal
/// used by [`EpisodicStore::resolve_current`]. Kept deliberately specific:
/// these phrases indicate a *transition*, not merely a preference
/// statement, so plain "my favorite X is Y" statements never anchor.
const CHANGE_MARKERS: &[&str] = &[
    "switched to",
    "switch to",
    "switching to",
    "changed my",
    "change my",
    "changed from",
    "now prefer",
    "now i prefer",
    "now i'm",
    "now im",
    "no longer",
    "used to",
    "moved to",
    "not anymore",
    "instead of",
    "replaced",
    "gave up",
];

/// True when the content contains a phrase marking a value transition.
fn contains_change_marker(content: &str) -> bool {
    let lowered = content.to_ascii_lowercase();
    CHANGE_MARKERS.iter().any(|marker| lowered.contains(marker))
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

fn cosine_sim(a: &[f32], b: &[f32]) -> f32 {
    let dot = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum::<f32>();
    let norm_a = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm_a < 1e-9 || norm_b < 1e-9 {
        0.0
    } else {
        dot / (norm_a * norm_b)
    }
}

fn contains_number_word(text: &str) -> bool {
    const NUMBER_WORDS: &[&str] = &[
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
        "twenty",
        "thirty",
        "forty",
        "fifty",
        "sixty",
        "seventy",
        "eighty",
        "ninety",
        "hundred",
        "thousand",
        "million",
        "billion",
        "dozen",
        "couple",
        "half",
        "quarter",
        "double",
        "triple",
        "twice",
    ];
    for word in text.split(|c: char| !c.is_alphanumeric()) {
        if word.len() >= 3 && NUMBER_WORDS.iter().any(|nw| word.eq_ignore_ascii_case(nw)) {
            return true;
        }
    }
    false
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

    fn user_statement(sequence: u64, content: &str) -> EpisodicRecord {
        EpisodicRecord::new(
            None,
            sequence,
            EpisodicKind::UserStatement,
            content,
            Provenance::new(ProvenanceSource::User),
        )
    }

    fn assistant_response(sequence: u64, content: &str) -> EpisodicRecord {
        EpisodicRecord::new(
            None,
            sequence,
            EpisodicKind::AssistantResponse,
            content,
            Provenance::new(ProvenanceSource::Agent),
        )
    }

    #[test]
    fn current_query_detection() {
        assert!(is_current_query("What's my current favorite coffee?"));
        assert!(is_current_query("What am I currently reading these days?"));
        assert!(is_current_query("What's the latest book I mentioned?"));
        assert!(is_current_query("What's my job right now?"));
        assert!(is_current_query("What am I eating at the moment?"));
        assert!(!is_current_query("What's my favorite coffee?"));
        assert!(!is_current_query("Where did I volunteer in February?"));
        assert!(!is_current_query("What did I say about the trip?"));
        // Word-boundary match: "current" inside another word must not fire.
        assert!(!is_current_query("What currency did I use in Japan?"));
    }

    #[test]
    fn current_query_resolution_prefers_latest_statement() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let episodic = store.episodic();
        // Old-value statements match MORE query terms (favorite + coffee)
        // than the change statement (coffee only), so pure score order
        // prefers the stale fact — the exact T1 failure mode.
        episodic
            .append(&user_statement(1, "My favorite coffee is dark roast."))
            .unwrap();
        episodic
            .append(&user_statement(
                2,
                "I really love dark roast when it comes to coffee.",
            ))
            .unwrap();
        episodic
            .append(&user_statement(3, "I've been jogging lately."))
            .unwrap();
        episodic
            .append(&user_statement(4, "I've switched to cold brew for coffee."))
            .unwrap();

        let results = episodic
            .search("What's my current favorite coffee?", 5, false)
            .unwrap();
        assert!(!results.is_empty());
        assert!(
            results[0].record.content.contains("cold brew"),
            "current query must rank the latest statement first, got: {}",
            results[0].record.content
        );
    }

    #[test]
    fn non_current_query_keeps_score_order() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let episodic = store.episodic();
        episodic
            .append(&user_statement(1, "My favorite coffee is dark roast."))
            .unwrap();
        episodic
            .append(&user_statement(2, "I've switched to cold brew for coffee."))
            .unwrap();

        // Without a current-value cue the deterministic score order holds:
        // the statement matching more query terms (favorite + coffee) wins.
        let results = episodic
            .search("What's my favorite coffee?", 5, false)
            .unwrap();
        assert!(!results.is_empty());
        assert!(
            results[0].record.content.contains("dark roast"),
            "non-current query must keep score order, got: {}",
            results[0].record.content
        );
    }

    #[test]
    fn current_resolution_anchors_on_user_statements_only() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let episodic = store.episodic();
        episodic
            .append(&user_statement(1, "My favorite coffee is dark roast."))
            .unwrap();
        // An assistant echo created LATER must not hijack the anchor set.
        episodic
            .append(&assistant_response(
                2,
                "Got it, dark roast is your favorite coffee!",
            ))
            .unwrap();
        episodic
            .append(&user_statement(3, "I've switched to cold brew for coffee."))
            .unwrap();

        let results = episodic
            .search("What's my current favorite coffee?", 5, false)
            .unwrap();
        assert!(
            results[0].record.content.contains("cold brew"),
            "user statements anchor chronology, got: {}",
            results[0].record.content
        );
        assert_eq!(results[0].record.kind, EpisodicKind::UserStatement);
    }

    #[test]
    fn current_query_without_change_markers_keeps_score_order() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let episodic = store.episodic();
        // No change markers anywhere: resolution must not reorder anything.
        episodic
            .append(&user_statement(
                1,
                "My favorite hiking trail is Eagle Ridge.",
            ))
            .unwrap();
        episodic
            .append(&user_statement(2, "I go hiking every weekend."))
            .unwrap();

        let results = episodic
            .search("What's my current favorite hiking trail?", 5, false)
            .unwrap();
        assert!(!results.is_empty());
        assert!(
            results[0].record.content.contains("Eagle Ridge"),
            "no change markers → deterministic score order, got: {}",
            results[0].record.content
        );
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

    #[test]
    fn enrichment_bridges_vocabulary_gap_for_theater() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        store.set_episodic_enrichment(crate::enrichment::VocabularyEnrichment::with_defaults());
        // Answer turn says "production" not "play" — enrichment bridges this
        let answer = sample_record(1, "The production I attended was The Glass Menagerie");
        let competing = sample_record(2, "I went to a play at the local community theater");
        let answer_id = answer.id;
        store.episodic().append_batch(&[answer, competing]).unwrap();
        let hits = store
            .episodic()
            .search(
                "What play did I attend at the local community theater?",
                5,
                false,
            )
            .unwrap();
        // With enrichment, "production" in the answer turn gets postings for
        // "play", "theater", "performance" — so it should now match more terms
        assert!(hits.iter().any(|h| h.record.id == answer_id));
    }

    #[test]
    fn enrichment_bridges_vocabulary_gap_for_shelter() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        store.set_episodic_enrichment(crate::enrichment::VocabularyEnrichment::with_defaults());
        let answer = sample_record(1, "I rescued a dog from the humane society last week");
        let other = sample_record(2, "I bought groceries at the store");
        let answer_id = answer.id;
        store.episodic().append_batch(&[answer, other]).unwrap();
        let hits = store
            .episodic()
            .search("When did I volunteer at the animal shelter?", 5, false)
            .unwrap();
        assert!(hits.iter().any(|h| h.record.id == answer_id));
    }

    #[test]
    fn session_boost_favors_sessions_with_multiple_matches() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let session_a = uuid::Uuid::new_v4();
        let session_b = uuid::Uuid::new_v4();
        // Session A has two matching turns (same kind to isolate session boost)
        let a1 = EpisodicRecord::new(
            Some(session_a),
            1,
            EpisodicKind::Observation,
            "I love hiking in the mountains",
            Provenance::new(ProvenanceSource::User),
        );
        let a2 = EpisodicRecord::new(
            Some(session_a),
            2,
            EpisodicKind::Observation,
            "Hiking in the mountains is great exercise",
            Provenance::new(ProvenanceSource::User),
        );
        // Session B has one matching turn with same kind
        let b1 = EpisodicRecord::new(
            Some(session_b),
            1,
            EpisodicKind::Observation,
            "Hiking is fun",
            Provenance::new(ProvenanceSource::User),
        );
        store.episodic().append_batch(&[a1, a2, b1]).unwrap();
        let hits = store
            .episodic()
            .search("hiking mountains", 10, false)
            .unwrap();
        // Session A turns should be boosted over session B turn because
        // session A has 2 matching turns vs 1 for session B
        let a_ranks: Vec<usize> = hits
            .iter()
            .enumerate()
            .filter(|(_, h)| h.record.session_id == Some(session_a))
            .map(|(i, _)| i)
            .collect();
        let b_rank = hits
            .iter()
            .position(|h| h.record.session_id == Some(session_b));
        if let Some(br) = b_rank {
            assert!(a_ranks.iter().all(|&ar| ar < br));
        }
    }
}
