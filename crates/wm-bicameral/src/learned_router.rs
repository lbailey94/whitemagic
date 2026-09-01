//! Learned Inference Router — replaces 20 regex complexity patterns with
//! embedding + k-NN + conformal calibration.
//!
//! # Architecture
//!
//! ```text
//! Prompt → Embed → k-NN search in RoutingHistory → Weighted vote on tier
//!         → ConformalCalibrator.calibrate() → InferenceTier
//! ```
//!
//! # Migration Path
//!
//! 1. Shadow mode: run both learned + regex, log disagreements
//! 2. Learned router as primary, regex as fallback for cold-start
//! 3. Remove regex patterns once accuracy matches/exceeds
//!
//! # Research Basis
//!
//! - **EvoRoute** (ACL 2026): Experience-driven self-routing, 80% cost reduction
//! - **Conformal calibration** (already in v4): Warm-started with 24 samples

use ahash::AHashMap;
use serde::{Deserialize, Serialize};
use std::sync::RwLock;
use wm_memory::Embedder;

use crate::edge_rules::{CompiledRule, EdgeRuleEngine};
use crate::router::{ComplexityClassifier, ConformalCalibrator, InferenceTier};

/// Number of nearest neighbors to consider in k-NN lookup.
const K_NEIGHBORS: usize = 5;

/// Minimum history size before the learned router is used (cold-start threshold).
const MIN_HISTORY: usize = 10;

/// Minimum frequency for an edge rule candidate to be promoted.
const EDGE_RULE_MIN_FREQUENCY: usize = 5;

/// A routing decision record stored in history.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingRecord {
    /// The original prompt.
    pub prompt: String,
    /// The embedding of the prompt.
    pub embedding: Vec<f32>,
    /// The tier that was selected.
    pub tier: InferenceTier,
    /// The task type label (from regex classifier or learned).
    pub task_type: String,
    /// Whether the routing was correct (tool succeeded, no escalation needed).
    pub correct: bool,
    /// Timestamp (Unix epoch seconds).
    pub timestamp: u64,
}

/// k-NN search result.
struct Neighbor {
    index: usize,
    distance: f32,
}

/// Routing history with k-NN lookup capability.
///
/// Stores routing records with their embeddings. When the history is large
/// enough (≥ `MIN_HISTORY`), the learned router uses k-NN to find similar
/// historical prompts and votes on the appropriate tier.
pub struct RoutingHistory {
    records: Vec<RoutingRecord>,
    /// Index from prompt hash to record index (for deduplication / frequency).
    prompt_frequency: AHashMap<String, usize>,
}

impl RoutingHistory {
    /// Create a new empty routing history.
    #[must_use]
    pub fn new() -> Self {
        Self {
            records: Vec::new(),
            prompt_frequency: AHashMap::new(),
        }
    }

    /// Add a routing record to history.
    pub fn add(&mut self, record: RoutingRecord) {
        *self
            .prompt_frequency
            .entry(record.prompt.clone())
            .or_insert(0) += 1;
        self.records.push(record);
    }

    /// Number of records in history.
    #[must_use]
    pub fn len(&self) -> usize {
        self.records.len()
    }

    /// Whether the history is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.records.is_empty()
    }

    /// Whether the history has enough data for k-NN routing.
    #[must_use]
    pub fn is_ready(&self) -> bool {
        self.records.len() >= MIN_HISTORY
    }

    /// Get the frequency of a prompt in history.
    #[must_use]
    pub fn frequency(&self, prompt: &str) -> usize {
        self.prompt_frequency.get(prompt).copied().unwrap_or(0)
    }

    /// Find the k nearest neighbors to a query embedding by cosine similarity.
    ///
    /// Returns up to `k` neighbors sorted by descending similarity (ascending distance).
    fn nearest(&self, query_emb: &[f32], k: usize) -> Vec<Neighbor> {
        if self.records.is_empty() || query_emb.is_empty() {
            return Vec::new();
        }

        let mut distances: Vec<Neighbor> = self
            .records
            .iter()
            .enumerate()
            .map(|(i, r)| Neighbor {
                index: i,
                distance: 1.0 - cosine_sim(query_emb, &r.embedding),
            })
            .collect();

        distances.sort_by(|a, b| {
            a.distance
                .partial_cmp(&b.distance)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        distances.into_iter().take(k).collect()
    }

    /// Get a snapshot of all records (for serialization/inspection).
    #[must_use]
    pub fn records(&self) -> &[RoutingRecord] {
        &self.records
    }
}

impl Default for RoutingHistory {
    fn default() -> Self {
        Self::new()
    }
}

/// The learned inference router.
///
/// Uses embedding-based k-NN search over routing history to classify prompts
/// into inference tiers. Falls back to the regex `ComplexityClassifier` when
/// history is insufficient (cold-start).
///
/// # OATS-style Outcome Refinement
///
/// After each routing decision, `record_outcome` is called with the result.
/// Incorrect routings are tagged, and the k-NN vote weights correct neighbors
/// more heavily than incorrect ones.
pub struct LearnedRouter {
    /// Embedder for query embedding.
    embedder: Box<dyn Embedder>,
    /// Routing history for k-NN lookup.
    history: RwLock<RoutingHistory>,
    /// Conformal calibrator (shared with InferenceRouter).
    calibrator: RwLock<ConformalCalibrator>,
    /// Regex classifier for cold-start fallback.
    regex_classifier: ComplexityClassifier,
    // Whether the learned router is ready (enough history).
    // Checked dynamically from history size.
}

impl LearnedRouter {
    /// Create a new learned router with the given embedder.
    ///
    /// The conformal calibrator is warm-started with known confidence patterns.
    #[must_use]
    pub fn new(embedder: Box<dyn Embedder>) -> Self {
        let mut calibrator = ConformalCalibrator::new(0.5);
        calibrator.warm_start();

        Self {
            embedder,
            history: RwLock::new(RoutingHistory::new()),
            calibrator: RwLock::new(calibrator),
            regex_classifier: ComplexityClassifier::new(),
        }
    }

    /// Create a learned router, returning `None` if the embedder is a stub.
    ///
    /// Stub embedders produce hash-based embeddings with no semantic meaning,
    /// so k-NN search would be random. Fall back to regex in that case.
    #[must_use]
    pub fn new_if_real(embedder: Box<dyn Embedder>) -> Option<Self> {
        if embedder.backend_name() == "stub" {
            tracing::info!(
                "learned router disabled — stub embedder has no semantic similarity, using regex fallback"
            );
            return None;
        }
        Some(Self::new(embedder))
    }

    /// Classify a prompt to determine the appropriate inference tier.
    ///
    /// Fall back to the deterministic regex classifier (cold start or
    /// learned-router failure — lock poisoning, embedding errors, no
    /// neighbors). Never panics.
    fn regex_fallback(
        &self,
        prompt: &str,
        max_output_tokens: Option<usize>,
        latency_budget_ms: Option<f64>,
        is_background: bool,
    ) -> LearnedAssessment {
        let regex_result = self.regex_classifier.classify(
            prompt,
            max_output_tokens,
            latency_budget_ms,
            is_background,
        );
        LearnedAssessment {
            tier: regex_result.tier,
            task_type: regex_result.task_type,
            confidence: regex_result.confidence,
            source: ClassificationSource::RegexFallback,
            neighbors_found: 0,
        }
    }

    /// When history is sufficient (≥ `MIN_HISTORY`), uses embedding k-NN with
    /// conformal calibration. Otherwise, falls back to the regex classifier.
    #[must_use]
    pub fn classify(
        &self,
        prompt: &str,
        max_output_tokens: Option<usize>,
        latency_budget_ms: Option<f64>,
        is_background: bool,
    ) -> LearnedAssessment {
        let Ok(history) = self.history.read() else {
            return self.regex_fallback(
                prompt,
                max_output_tokens,
                latency_budget_ms,
                is_background,
            );
        };

        if !history.is_ready() {
            // Cold-start: use regex classifier
            return self.regex_fallback(
                prompt,
                max_output_tokens,
                latency_budget_ms,
                is_background,
            );
        }

        // Embed the query
        let query_emb = match self.embedder.embed(prompt) {
            Ok(emb) => emb,
            Err(e) => {
                tracing::warn!(error = %e, "learned router: query embedding failed, falling back to regex");
                let regex_result = self.regex_classifier.classify(
                    prompt,
                    max_output_tokens,
                    latency_budget_ms,
                    is_background,
                );
                return LearnedAssessment {
                    tier: regex_result.tier,
                    task_type: regex_result.task_type,
                    confidence: regex_result.confidence,
                    source: ClassificationSource::RegexFallback,
                    neighbors_found: 0,
                };
            }
        };

        // k-NN search
        let neighbors = history.nearest(&query_emb, K_NEIGHBORS);
        drop(history);

        if neighbors.is_empty() {
            return self.regex_fallback(
                prompt,
                max_output_tokens,
                latency_budget_ms,
                is_background,
            );
        }

        // Weighted vote: neighbors weighted by similarity (closer = more weight)
        // and by correctness (correct neighbors weighted 2x).
        let mut tier_votes: AHashMap<InferenceTier, f32> = AHashMap::new();
        let mut task_type_votes: AHashMap<String, f32> = AHashMap::new();

        let Ok(history_read) = self.history.read() else {
            return self.regex_fallback(
                prompt,
                max_output_tokens,
                latency_budget_ms,
                is_background,
            );
        };

        for neighbor in &neighbors {
            let record = &history_read.records[neighbor.index];
            let similarity = 1.0 - neighbor.distance;
            let weight = similarity * if record.correct { 2.0 } else { 0.5 };

            *tier_votes.entry(record.tier).or_insert(0.0) += weight;
            *task_type_votes
                .entry(record.task_type.clone())
                .or_insert(0.0) += weight;
        }

        drop(history_read);

        // Find the tier with the highest weighted vote
        let (best_tier, tier_weight) = match tier_votes
            .iter()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
        {
            Some((t, w)) => (*t, *w),
            None => (InferenceTier::LocalLlamaCpp, 0.0),
        };

        let total_weight: f32 = tier_votes.values().sum();
        let raw_confidence = if total_weight > 0.0 {
            tier_weight / total_weight
        } else {
            0.5
        };

        // Calibrate confidence using conformal calibrator
        let calibrated_confidence = match self.calibrator.read() {
            Ok(cal) => cal.calibrate(raw_confidence),
            Err(_) => raw_confidence,
        };

        // Find the best task type
        let best_task_type = match task_type_votes
            .iter()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
        {
            Some((t, _)) => t.clone(),
            None => "learned".to_string(),
        };

        LearnedAssessment {
            tier: best_tier,
            task_type: best_task_type,
            confidence: calibrated_confidence,
            source: ClassificationSource::Learned,
            neighbors_found: neighbors.len(),
        }
    }

    /// Record a routing outcome for future k-NN classification.
    ///
    /// Call this after the inference is complete to track whether the routing
    /// was correct. `correct = true` means the tier was appropriate (no
    /// unnecessary escalation); `false` means it was wrong (too low or too high).
    pub fn record_outcome(
        &self,
        prompt: &str,
        tier: InferenceTier,
        task_type: &str,
        correct: bool,
    ) {
        let embedding = match self.embedder.embed(prompt) {
            Ok(emb) => emb,
            Err(_) => return,
        };

        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let record = RoutingRecord {
            prompt: prompt.to_string(),
            embedding,
            tier,
            task_type: task_type.to_string(),
            correct,
            timestamp,
        };

        let Ok(mut history) = self.history.write() else {
            return;
        };
        history.add(record);

        // Also add a calibration sample
        let raw_confidence = if correct { 0.85 } else { 0.3 };
        drop(history);

        let Ok(mut cal) = self.calibrator.write() else {
            return;
        };
        cal.add_sample(raw_confidence, correct);

        // Re-fit periodically
        if cal.sample_count() % 50 == 0 {
            cal.fit();
            tracing::info!(
                samples = cal.sample_count(),
                threshold = cal.threshold(),
                "learned router: conformal calibrator re-fitted"
            );
        }
    }

    /// History size (number of routing records).
    #[must_use]
    pub fn history_len(&self) -> usize {
        let Ok(guard) = self.history.read() else {
            return 0;
        };
        guard.len()
    }

    /// Whether the learned router has enough history to be used.
    #[must_use]
    pub fn is_ready(&self) -> bool {
        let Ok(guard) = self.history.read() else {
            return false;
        };
        guard.is_ready()
    }

    /// Embedder backend name.
    #[must_use]
    pub fn backend_name(&self) -> &str {
        self.embedder.backend_name()
    }

    /// Get a snapshot of routing records for inspection.
    #[must_use]
    pub fn history_records(&self) -> Vec<RoutingRecord> {
        let Ok(guard) = self.history.read() else {
            return Vec::new();
        };
        guard.records().to_vec()
    }

    /// Add a calibration sample to the conformal calibrator.
    pub fn add_calibration_sample(&self, raw_confidence: f32, correct: bool) {
        let Ok(mut cal) = self.calibrator.write() else {
            return;
        };
        cal.add_sample(raw_confidence, correct);
    }

    /// Fit the conformal calibrator.
    pub fn fit_calibrator(&self) {
        let Ok(mut cal) = self.calibrator.write() else {
            return;
        };
        cal.fit();
    }

    /// Whether the conformal calibrator has been fitted.
    #[must_use]
    pub fn is_calibrated(&self) -> bool {
        let Ok(guard) = self.calibrator.read() else {
            return false;
        };
        guard.is_fitted()
    }
}

/// Source of the classification decision.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ClassificationSource {
    /// Learned router (embedding k-NN).
    Learned,
    /// Regex classifier fallback (cold-start or embedding failure).
    RegexFallback,
}

/// Assessment from the learned router.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LearnedAssessment {
    /// The recommended inference tier.
    pub tier: InferenceTier,
    /// Task type label.
    pub task_type: String,
    /// Calibrated confidence (0.0–1.0).
    pub confidence: f32,
    /// Whether this came from the learned router or regex fallback.
    pub source: ClassificationSource,
    /// Number of k-NN neighbors found (0 for regex fallback).
    pub neighbors_found: usize,
}

// ── Edge Rule Generator ──────────────────────────────────────────────

/// A candidate for edge rule promotion.
///
/// When a query escalates past `InferenceTier::EdgeRules` but gets a simple,
/// confident response, it's a candidate for an auto-generated edge rule.
/// After seeing the same (or similar) query enough times, it gets promoted
/// to a compiled rule in the `EdgeRuleEngine`.
#[derive(Debug, Clone)]
pub struct EdgeRuleCandidate {
    /// The original query.
    pub query: String,
    /// The response that was generated.
    pub response: String,
    /// The tier that handled it.
    pub tier: InferenceTier,
    /// Confidence of the response.
    pub confidence: f32,
    /// How many times this (similar) query has been seen.
    pub frequency: usize,
}

/// Auto-generates edge rules from successful escalations.
///
/// When a query is handled by a higher tier (above EdgeRules) but the response
/// is simple and confident, the `EdgeRuleGenerator` tracks it as a candidate.
/// After seeing similar queries enough times (≥ `EDGE_RULE_MIN_FREQUENCY`),
/// the candidate is promoted to a compiled rule in the `EdgeRuleEngine`.
///
/// This implements the strategy's "auto-generated edge rules" concept:
/// high-frequency, high-confidence, simple responses get cached as edge rules
/// so future identical queries resolve at Tier 0 with zero LLM cost.
pub struct EdgeRuleGenerator {
    candidates: Vec<EdgeRuleCandidate>,
    /// Total rules promoted.
    promoted_count: usize,
}

impl EdgeRuleGenerator {
    /// Create a new edge rule generator.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            candidates: Vec::new(),
            promoted_count: 0,
        }
    }

    /// Observe a dispatch result and track it as a candidate if appropriate.
    ///
    /// A query is a candidate if:
    /// - It was handled above `InferenceTier::EdgeRules` (it escalated)
    /// - Confidence > 0.9 (the response was confident)
    /// - Response length < 200 chars (the response is simple enough to cache)
    pub fn observe(&mut self, query: &str, response: &str, tier: InferenceTier, confidence: f32) {
        if tier > InferenceTier::EdgeRules && confidence > 0.9 && response.len() < 200 {
            // Check if we already have a similar candidate
            let lower_query = query.to_lowercase();
            if let Some(existing) = self
                .candidates
                .iter_mut()
                .find(|c| c.query.to_lowercase() == lower_query)
            {
                existing.frequency += 1;
                // Update with the latest response (might be slightly different)
                existing.response = response.to_string();
                existing.confidence = confidence;
            } else {
                self.candidates.push(EdgeRuleCandidate {
                    query: query.to_string(),
                    response: response.to_string(),
                    tier,
                    confidence,
                    frequency: 1,
                });
            }
        }
    }

    /// Promote high-frequency candidates to compiled rules in the edge rule engine.
    ///
    /// Returns the number of rules promoted.
    pub fn promote(&mut self, engine: &mut EdgeRuleEngine) -> usize {
        let mut promoted = 0;
        let mut next_id = engine.rule_count();

        self.candidates.retain(|c| {
            if c.frequency >= EDGE_RULE_MIN_FREQUENCY {
                // Extract keywords from the query for the pattern
                let keywords = extract_keywords(&c.query);
                if keywords.is_empty() {
                    true // Keep — can't extract keywords
                } else {
                    let pattern = keywords.join("|");
                    let rule = CompiledRule::new(
                        format!("auto_{next_id}"),
                        pattern,
                        c.response.clone(),
                        c.confidence,
                    );
                    engine.add_rule(rule);
                    next_id += 1;
                    promoted += 1;
                    false // Remove from candidates
                }
            } else {
                true // Keep observing
            }
        });

        self.promoted_count += promoted;
        promoted
    }

    /// Number of candidates currently being tracked.
    #[must_use]
    pub fn candidate_count(&self) -> usize {
        self.candidates.len()
    }

    /// Total number of rules promoted over the generator's lifetime.
    #[must_use]
    pub const fn total_promoted(&self) -> usize {
        self.promoted_count
    }

    /// Get a snapshot of current candidates.
    #[must_use]
    pub fn candidates(&self) -> &[EdgeRuleCandidate] {
        &self.candidates
    }
}

impl Default for EdgeRuleGenerator {
    fn default() -> Self {
        Self::new()
    }
}

// ── Helpers ──────────────────────────────────────────────────────────

/// Cosine similarity between two f32 vectors.
fn cosine_sim(a: &[f32], b: &[f32]) -> f32 {
    if a.is_empty() || b.is_empty() || a.len() != b.len() {
        return 0.0;
    }

    let mut dot = 0.0_f32;
    let mut norm_a = 0.0_f32;
    let mut norm_b = 0.0_f32;

    for (x, y) in a.iter().zip(b.iter()) {
        dot += x * y;
        norm_a += x * x;
        norm_b += y * y;
    }

    let denom = norm_a.sqrt() * norm_b.sqrt();
    if denom == 0.0 { 0.0 } else { dot / denom }
}

/// Extract meaningful keywords from a query for edge rule patterns.
///
/// Filters out common stopwords and returns unique words.
fn extract_keywords(query: &str) -> Vec<String> {
    const STOPWORDS: &[&str] = &[
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can",
        "need", "to", "of", "in", "for", "on", "at", "by", "with", "from", "as", "into", "about",
        "what", "who", "when", "where", "why", "how", "which", "that", "this", "these", "those",
        "i", "you", "he", "she", "it", "we", "they", "and", "or", "but", "not", "no", "yes", "me",
        "my", "your",
    ];

    query
        .split(|c: char| !c.is_alphanumeric())
        .filter(|s| !s.is_empty())
        .map(str::to_lowercase)
        .filter(|s| s.len() > 2 && !STOPWORDS.contains(&s.as_str()))
        .collect::<std::collections::HashSet<_>>()
        .into_iter()
        .collect()
}

// ── Tests ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::router::ComplexityClassifier;

    // --- Cosine similarity tests ---

    #[test]
    fn cosine_sim_identical() {
        let v = vec![1.0, 2.0, 3.0];
        assert!((cosine_sim(&v, &v) - 1.0).abs() < 1e-5);
    }

    #[test]
    fn cosine_sim_orthogonal() {
        let a = vec![1.0, 0.0];
        let b = vec![0.0, 1.0];
        assert!(cosine_sim(&a, &b).abs() < 1e-5);
    }

    #[test]
    fn cosine_sim_empty() {
        assert_eq!(cosine_sim(&[], &[]), 0.0);
    }

    // --- RoutingHistory tests ---

    #[test]
    fn history_starts_empty() {
        let h = RoutingHistory::new();
        assert!(h.is_empty());
        assert!(!h.is_ready());
        assert_eq!(h.len(), 0);
    }

    #[test]
    fn history_add_records() {
        let mut h = RoutingHistory::new();
        h.add(RoutingRecord {
            prompt: "hello".into(),
            embedding: vec![1.0, 0.0],
            tier: InferenceTier::EdgeRules,
            task_type: "greeting".into(),
            correct: true,
            timestamp: 0,
        });
        assert_eq!(h.len(), 1);
        assert!(!h.is_ready()); // Need MIN_HISTORY (10)
    }

    #[test]
    fn history_becomes_ready() {
        let mut h = RoutingHistory::new();
        for i in 0..MIN_HISTORY {
            h.add(RoutingRecord {
                prompt: format!("prompt_{i}"),
                embedding: vec![i as f32, 0.0],
                tier: InferenceTier::LocalLlamaCpp,
                task_type: "test".into(),
                correct: true,
                timestamp: i as u64,
            });
        }
        assert!(h.is_ready());
    }

    #[test]
    fn history_frequency_tracking() {
        let mut h = RoutingHistory::new();
        h.add(RoutingRecord {
            prompt: "hello world".into(),
            embedding: vec![1.0],
            tier: InferenceTier::EdgeRules,
            task_type: "greeting".into(),
            correct: true,
            timestamp: 0,
        });
        h.add(RoutingRecord {
            prompt: "hello world".into(),
            embedding: vec![1.0],
            tier: InferenceTier::EdgeRules,
            task_type: "greeting".into(),
            correct: true,
            timestamp: 1,
        });
        assert_eq!(h.frequency("hello world"), 2);
        assert_eq!(h.frequency("unknown"), 0);
    }

    #[test]
    fn history_nearest_finds_similar() {
        let mut h = RoutingHistory::new();
        // Record at [1, 0]
        h.add(RoutingRecord {
            prompt: "close".into(),
            embedding: vec![1.0, 0.0],
            tier: InferenceTier::EdgeRules,
            task_type: "test".into(),
            correct: true,
            timestamp: 0,
        });
        // Record at [0, 1] (orthogonal)
        h.add(RoutingRecord {
            prompt: "far".into(),
            embedding: vec![0.0, 1.0],
            tier: InferenceTier::LocalSmall,
            task_type: "test".into(),
            correct: true,
            timestamp: 1,
        });

        let neighbors = h.nearest(&[1.0, 0.0], 2);
        assert_eq!(neighbors.len(), 2);
        // The closest should be "close" (index 0)
        assert_eq!(neighbors[0].index, 0);
        // Distance should be ~0 (identical)
        assert!(neighbors[0].distance < 1e-5);
    }

    // --- Keyword extraction tests ---

    #[test]
    fn extract_keywords_basic() {
        let kws = extract_keywords("what is the capital of france");
        assert!(kws.contains(&"capital".to_string()));
        assert!(kws.contains(&"france".to_string()));
        // Stopwords should be filtered
        assert!(!kws.contains(&"what".to_string()));
        assert!(!kws.contains(&"the".to_string()));
        assert!(!kws.contains(&"is".to_string()));
    }

    #[test]
    fn extract_keywords_filters_short_words() {
        let kws = extract_keywords("to be or not to be");
        // All words are ≤2 chars or stopwords
        assert!(kws.is_empty() || kws.iter().all(|k| k.len() > 2));
    }

    #[test]
    fn extract_keywords_deduplicates() {
        let kws = extract_keywords("rust rust rust programming programming");
        let unique: std::collections::HashSet<_> = kws.iter().collect();
        assert_eq!(kws.len(), unique.len());
    }

    // --- LearnedRouter with stub embedder ---

    #[test]
    fn learned_router_returns_none_for_stub() {
        let stub = Box::new(wm_memory::StubEmbedder::default());
        let router = LearnedRouter::new_if_real(stub);
        assert!(router.is_none());
    }

    // --- Mock embedder for testing ---

    /// A test embedder that maps known keywords to specific dimensions.
    struct KeywordEmbedder {
        keyword_map: AHashMap<String, usize>,
        dim: usize,
    }

    impl KeywordEmbedder {
        fn new(keywords: &[&str]) -> Self {
            let dim = keywords.len();
            let mut keyword_map = AHashMap::new();
            for (i, kw) in keywords.iter().enumerate() {
                keyword_map.insert((*kw).to_string(), i);
            }
            Self { keyword_map, dim }
        }

        fn embed_text(&self, text: &str) -> Vec<f32> {
            let lower = text.to_lowercase();
            let mut emb = vec![0.0_f32; self.dim];
            for (kw, idx) in &self.keyword_map {
                if lower.contains(kw) {
                    emb[*idx] = 1.0;
                }
            }
            // Normalize
            let norm: f32 = emb.iter().map(|x| x * x).sum::<f32>().sqrt();
            if norm > 0.0 {
                for x in &mut emb {
                    *x /= norm;
                }
            }
            emb
        }
    }

    impl Embedder for KeywordEmbedder {
        fn embed_batch(&self, texts: &[&str]) -> wm_core::Result<Vec<Vec<f32>>> {
            Ok(texts.iter().map(|t| self.embed_text(t)).collect())
        }

        fn dimension(&self) -> usize {
            self.dim
        }

        fn is_available(&self) -> bool {
            true
        }

        fn backend_name(&self) -> &'static str {
            "keyword-test"
        }
    }

    fn make_test_embedder() -> KeywordEmbedder {
        KeywordEmbedder::new(&[
            "hello",
            "hi",
            "hey", // greeting → EdgeRules
            "what",
            "who",
            "where", // factual QA → LocalLlamaCpp
            "code",
            "function",
            "debug", // coding → LocalLarge
            "analyze",
            "evaluate", // analysis → LocalLarge
            "creative",
            "story", // creative → Cloud
            "research",
            "survey", // research → Cloud
            "classify",
            "categorize", // classification → LocalSmall
            "summarize",
            "condense", // summarization → LocalSmall
        ])
    }

    // --- LearnedRouter classification tests ---

    #[test]
    fn learned_router_cold_start_uses_regex() {
        let embedder = make_test_embedder();
        let router = LearnedRouter::new(Box::new(embedder));

        // No history → should use regex fallback
        let assessment = router.classify("hello there", None, None, false);
        assert_eq!(assessment.source, ClassificationSource::RegexFallback);
        assert_eq!(assessment.neighbors_found, 0);
    }

    #[test]
    fn learned_router_uses_knn_after_warmup() {
        let embedder = make_test_embedder();
        let router = LearnedRouter::new(Box::new(embedder));

        // Seed history with known routing decisions
        router.record_outcome("hello there", InferenceTier::EdgeRules, "greeting", true);
        router.record_outcome("hi friend", InferenceTier::EdgeRules, "greeting", true);
        router.record_outcome("hey buddy", InferenceTier::EdgeRules, "greeting", true);
        router.record_outcome(
            "what is rust",
            InferenceTier::LocalLlamaCpp,
            "factual_qa",
            true,
        );
        router.record_outcome(
            "who is alan turing",
            InferenceTier::LocalLlamaCpp,
            "factual_qa",
            true,
        );
        router.record_outcome("code a function", InferenceTier::LocalLarge, "coding", true);
        router.record_outcome("debug this code", InferenceTier::LocalLarge, "coding", true);
        router.record_outcome(
            "analyze the data",
            InferenceTier::LocalLarge,
            "analysis",
            true,
        );
        router.record_outcome(
            "evaluate the results",
            InferenceTier::LocalLarge,
            "analysis",
            true,
        );
        router.record_outcome(
            "classify these items",
            InferenceTier::LocalSmall,
            "classification",
            true,
        );

        assert!(router.is_ready());

        // Now classify a greeting — should route to EdgeRules via k-NN
        let assessment = router.classify("hello world", None, None, false);
        assert_eq!(assessment.source, ClassificationSource::Learned);
        assert!(assessment.neighbors_found > 0);
        assert_eq!(assessment.tier, InferenceTier::EdgeRules);
    }

    #[test]
    fn learned_router_knn_routes_coding() {
        let embedder = make_test_embedder();
        let router = LearnedRouter::new(Box::new(embedder));

        // Seed history
        router.record_outcome("hello", InferenceTier::EdgeRules, "greeting", true);
        router.record_outcome("hi", InferenceTier::EdgeRules, "greeting", true);
        router.record_outcome("hey", InferenceTier::EdgeRules, "greeting", true);
        router.record_outcome(
            "what is rust",
            InferenceTier::LocalLlamaCpp,
            "factual_qa",
            true,
        );
        router.record_outcome(
            "who is turing",
            InferenceTier::LocalLlamaCpp,
            "factual_qa",
            true,
        );
        router.record_outcome("code a function", InferenceTier::LocalLarge, "coding", true);
        router.record_outcome("debug this code", InferenceTier::LocalLarge, "coding", true);
        router.record_outcome("analyze data", InferenceTier::LocalLarge, "analysis", true);
        router.record_outcome(
            "evaluate results",
            InferenceTier::LocalLarge,
            "analysis",
            true,
        );
        router.record_outcome(
            "classify items",
            InferenceTier::LocalSmall,
            "classification",
            true,
        );

        // "write code for me" should match coding neighbors
        let assessment = router.classify("write code for me", None, None, false);
        assert_eq!(assessment.source, ClassificationSource::Learned);
        assert_eq!(assessment.tier, InferenceTier::LocalLarge);
    }

    #[test]
    fn learned_router_record_outcome_increments_history() {
        let embedder = make_test_embedder();
        let router = LearnedRouter::new(Box::new(embedder));

        assert_eq!(router.history_len(), 0);
        router.record_outcome("test prompt", InferenceTier::LocalLlamaCpp, "test", true);
        assert_eq!(router.history_len(), 1);
    }

    #[test]
    fn learned_router_calibrator_warm_started() {
        let embedder = make_test_embedder();
        let router = LearnedRouter::new(Box::new(embedder));
        assert!(router.is_calibrated());
    }

    // --- A/B comparison: learned router vs regex classifier ---

    #[test]
    fn ab_comparison_greeting() {
        let embedder = make_test_embedder();
        let router = LearnedRouter::new(Box::new(embedder));
        let regex = ComplexityClassifier::new();

        // Seed history
        for _ in 0..5 {
            router.record_outcome("hello there", InferenceTier::EdgeRules, "greeting", true);
            router.record_outcome("hi friend", InferenceTier::EdgeRules, "greeting", true);
        }

        let query = "hello world";
        let learned = router.classify(query, None, None, false);
        let regex_result = regex.classify(query, None, None, false);

        // Both should agree on EdgeRules for greetings
        assert_eq!(learned.tier, regex_result.tier);
        assert_eq!(learned.tier, InferenceTier::EdgeRules);
    }

    #[test]
    fn ab_comparison_coding() {
        let embedder = make_test_embedder();
        let router = LearnedRouter::new(Box::new(embedder));
        let regex = ComplexityClassifier::new();

        // Seed history
        for _ in 0..5 {
            router.record_outcome("code a function", InferenceTier::LocalLarge, "coding", true);
            router.record_outcome("debug this code", InferenceTier::LocalLarge, "coding", true);
        }

        let query = "code a sorting algorithm";
        let learned = router.classify(query, None, None, false);
        let regex_result = regex.classify(query, None, None, false);

        // Both should agree on LocalLarge for coding
        assert_eq!(learned.tier, regex_result.tier);
        assert_eq!(learned.tier, InferenceTier::LocalLarge);
    }

    // --- EdgeRuleGenerator tests ---

    #[test]
    fn edge_rule_generator_starts_empty() {
        let generator = EdgeRuleGenerator::new();
        assert_eq!(generator.candidate_count(), 0);
        assert_eq!(generator.total_promoted(), 0);
    }

    #[test]
    fn edge_rule_generator_ignores_edge_rules_tier() {
        let mut generator = EdgeRuleGenerator::new();
        generator.observe("hello", "hi there", InferenceTier::EdgeRules, 1.0);
        assert_eq!(generator.candidate_count(), 0);
    }

    #[test]
    fn edge_rule_generator_ignores_low_confidence() {
        let mut generator = EdgeRuleGenerator::new();
        generator.observe("complex query", "response", InferenceTier::LocalLarge, 0.5);
        assert_eq!(generator.candidate_count(), 0);
    }

    #[test]
    fn edge_rule_generator_ignores_long_responses() {
        let mut generator = EdgeRuleGenerator::new();
        let long_response = "x".repeat(250);
        generator.observe("query", &long_response, InferenceTier::LocalLarge, 0.95);
        assert_eq!(generator.candidate_count(), 0);
    }

    #[test]
    fn edge_rule_generator_tracks_candidates() {
        let mut generator = EdgeRuleGenerator::new();
        generator.observe("what version", "v5.2.1", InferenceTier::LocalLlamaCpp, 0.95);
        assert_eq!(generator.candidate_count(), 1);
    }

    #[test]
    fn edge_rule_generator_increments_frequency() {
        let mut generator = EdgeRuleGenerator::new();
        generator.observe("what version", "v5.2.1", InferenceTier::LocalLlamaCpp, 0.95);
        generator.observe("what version", "v4.0.1", InferenceTier::LocalLlamaCpp, 0.95);
        generator.observe("what version", "v4.0.2", InferenceTier::LocalLlamaCpp, 0.95);

        let candidates = generator.candidates();
        assert_eq!(candidates.len(), 1);
        assert_eq!(candidates[0].frequency, 3);
    }

    #[test]
    fn edge_rule_generator_promotes_high_frequency() {
        let mut generator = EdgeRuleGenerator::new();
        let mut engine = EdgeRuleEngine::empty();

        // Add candidate with high frequency
        for _ in 0..EDGE_RULE_MIN_FREQUENCY {
            generator.observe("what version", "v5.2.1", InferenceTier::LocalLlamaCpp, 0.95);
        }

        assert_eq!(generator.candidate_count(), 1);
        let promoted = generator.promote(&mut engine);
        assert_eq!(promoted, 1);
        assert_eq!(generator.candidate_count(), 0);
        assert!(engine.rule_count() > 0);
    }

    #[test]
    fn edge_rule_generator_does_not_promote_low_frequency() {
        let mut generator = EdgeRuleGenerator::new();
        let mut engine = EdgeRuleEngine::empty();

        generator.observe("what version", "v5.2.1", InferenceTier::LocalLlamaCpp, 0.95);
        generator.observe("what version", "v5.2.1", InferenceTier::LocalLlamaCpp, 0.95);

        let promoted = generator.promote(&mut engine);
        assert_eq!(promoted, 0);
        assert_eq!(generator.candidate_count(), 1);
        assert_eq!(engine.rule_count(), 0);
    }

    #[test]
    fn edge_rule_generator_promoted_rule_matches_original_query() {
        let mut generator = EdgeRuleGenerator::new();
        let mut engine = EdgeRuleEngine::empty();

        for _ in 0..EDGE_RULE_MIN_FREQUENCY {
            generator.observe(
                "what version are you",
                "v5.2.1",
                InferenceTier::LocalLlamaCpp,
                0.95,
            );
        }

        generator.promote(&mut engine);

        // The promoted rule should match the original query
        let result = engine.infer("what version are you");
        assert!(result.confidence > 0.0);
        assert_eq!(result.answer, "v5.2.1");
    }

    #[test]
    fn edge_rule_generator_total_promoted_tracking() {
        let mut generator = EdgeRuleGenerator::new();
        let mut engine = EdgeRuleEngine::empty();

        // First promotion
        for _ in 0..EDGE_RULE_MIN_FREQUENCY {
            generator.observe(
                "query one",
                "response one",
                InferenceTier::LocalLlamaCpp,
                0.95,
            );
        }
        generator.promote(&mut engine);
        assert_eq!(generator.total_promoted(), 1);

        // Second promotion
        for _ in 0..EDGE_RULE_MIN_FREQUENCY {
            generator.observe(
                "query two",
                "response two",
                InferenceTier::LocalLlamaCpp,
                0.95,
            );
        }
        generator.promote(&mut engine);
        assert_eq!(generator.total_promoted(), 2);
    }
}
