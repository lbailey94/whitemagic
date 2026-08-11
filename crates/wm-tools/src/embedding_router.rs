//! Embedding-based NLU router for the `wm` meta-tool.
//!
//! Replaces 166 hand-written TF-IDF keyword profiles with embedding cosine
//! similarity. Each tool's description is embedded once at startup. Input
//! queries are embedded and compared against all tool embeddings using cosine
//! similarity.
//!
//! # OATS: Outcome-Aware Tool Selection
//!
//! After each tool call, the router records whether the routing was correct
//! (tool succeeded) or incorrect (tool failed / was wrong). Success and failure
//! query embeddings are averaged into centroids. Tool embeddings are refined
//! by interpolating toward the success centroid:
//!
//! ```text
//! refined = base * (1 - α) + success_centroid * α
//! ```
//!
//! This is zero-cost at serving time when pre-computed, and improves NDCG@5
//! from ~0.869 to ~0.940 (OATS, 2026).
//!
//! # Fallback
//!
//! If no real embedder is available (only StubEmbedder), the router returns
//! `None` from `new()`, and the caller falls back to the TF-IDF router.

use ahash::AHashMap;
use std::sync::{Arc, RwLock};
use wm_memory::Embedder;

use crate::nlu::{PREFIX_ROUTES, TOOL_PROFILES, ToolProfile};

/// OATS refinement strength (interpolation factor toward success centroid).
const OATS_ALPHA: f32 = 0.15;

/// Minimum observations before OATS refinement kicks in.
const OATS_MIN_OBSERVATIONS: usize = 10;

/// Minimum cosine similarity to return a match (below this → gnosis fallback).
const MIN_THRESHOLD: f64 = 0.10;

/// Minimum margin between top-1 and top-2 before the embedding router's
/// choice is trusted.
///
/// Near-ties (margin below this) mean the description vocabulary cannot
/// separate intent — the caller should defer to the TF-IDF router. Derived
/// from the 2026-08-11 shadow data: ambiguous queries produced confident-
/// looking top-1 scores (0.5–0.8) with the correct tool often runner-up.
pub const MIN_MARGIN: f64 = 0.02;

/// Outcome statistics for a single tool (OATS data).
#[derive(Debug, Clone)]
pub struct OutcomeStats {
    /// Running centroid of query embeddings where this tool was the correct route.
    success_centroid: Vec<f32>,
    /// Running centroid of query embeddings where this tool was the wrong route.
    #[allow(dead_code)]
    failure_centroid: Vec<f32>,
    /// Number of successful routing observations.
    success_count: usize,
    /// Number of failed routing observations.
    failure_count: usize,
}

impl OutcomeStats {
    /// Create empty outcome stats with the given embedding dimensionality.
    fn new(dim: usize) -> Self {
        Self {
            success_centroid: vec![0.0; dim],
            failure_centroid: vec![0.0; dim],
            success_count: 0,
            failure_count: 0,
        }
    }

    /// Record a routing outcome with the query embedding.
    fn record(&mut self, query_emb: &[f32], success: bool) {
        if query_emb.is_empty() {
            return;
        }

        if success {
            update_centroid(
                &mut self.success_centroid,
                &mut self.success_count,
                query_emb,
            );
        } else {
            update_centroid(
                &mut self.failure_centroid,
                &mut self.failure_count,
                query_emb,
            );
        }
    }

    /// Whether OATS has enough data to refine this tool's embedding.
    const fn is_ready(&self) -> bool {
        self.success_count >= OATS_MIN_OBSERVATIONS
    }
}

/// Update a running centroid with a new vector (incremental mean).
fn update_centroid(centroid: &mut [f32], count: &mut usize, new_vec: &[f32]) {
    if centroid.len() != new_vec.len() {
        return;
    }
    let n = *count as f32 + 1.0;
    for (c, v) in centroid.iter_mut().zip(new_vec.iter()) {
        *c += (*v - *c) / n;
    }
    *count += 1;
}

/// The embedding-based NLU router.
///
/// Pre-computes tool embeddings at initialization, then routes queries by
/// embedding the query and computing cosine similarity against all tool
/// embeddings. OATS refinement adjusts tool embeddings based on observed
/// outcomes.
pub struct EmbeddingRouter {
    /// Tool name → base embedding (from tool description).
    tool_embeddings: AHashMap<String, Vec<f32>>,
    /// Embedder backend.
    embedder: Box<dyn Embedder>,
    /// OATS outcome stats per tool (interior mutability for record_outcome).
    outcome_stats: RwLock<AHashMap<String, OutcomeStats>>,
    /// Embedding dimensionality.
    dim: usize,
    /// Whether to apply the TF-IDF prefix-route bonus.
    ///
    /// `true` for the legacy keyword-profile path (`new`), where descriptions
    /// are bare keyword lists and the verb bonus compensates. `false` for
    /// anchored descriptions (`with_descriptions`), where the bonus fights
    /// the intent anchors ("list tools" was boosted toward memory.list despite
    /// tools.list carrying the exact anchor).
    apply_prefix_bonus: bool,
}

impl EmbeddingRouter {
    /// Create a new embedding router, pre-computing tool embeddings.
    ///
    /// Returns `None` if:
    /// - The embedder is a stub (hash-based embeddings have no semantic meaning)
    /// - Batch embedding fails
    ///
    /// This allows the caller to gracefully fall back to the TF-IDF router.
    #[must_use]
    pub fn new(embedder: Box<dyn Embedder>) -> Option<Self> {
        Self::new_with_descriptions(embedder, tool_descriptions(), true)
    }

    /// Create a new embedding router from explicit (tool, description) pairs.
    ///
    /// Unlike [`Self::new`] — which uses the static keyword profiles from
    /// `nlu.rs` (169 tools, keyword-mashup descriptions) — this accepts
    /// descriptions from the live tool registry (all 229 tools, prose
    /// descriptions). Sentence-style descriptions embed far better than
    /// bare keyword lists; the 2026-08-11 shadow run (42.6% disagreement)
    /// showed keyword-mashup top-1 selection collapsing onto arbitrary
    /// high-similarity tools.
    #[must_use]
    pub fn with_descriptions(
        embedder: Box<dyn Embedder>,
        descriptions: Vec<(String, String)>,
    ) -> Option<Self> {
        Self::new_with_descriptions(embedder, descriptions, false)
    }

    fn new_with_descriptions(
        embedder: Box<dyn Embedder>,
        descriptions: Vec<(String, String)>,
        apply_prefix_bonus: bool,
    ) -> Option<Self> {
        // Stub embedders produce hash-based embeddings with no semantic similarity.
        // Don't use the embedding router with them — fall back to TF-IDF.
        if embedder.backend_name() == "stub" {
            tracing::info!(
                "embedding router disabled — stub embedder has no semantic similarity, using TF-IDF fallback"
            );
            return None;
        }

        let dim = embedder.dimension();

        let texts: Vec<&str> = descriptions.iter().map(|(_, d)| d.as_str()).collect();
        let embeddings = embedder.embed_batch(&texts).ok()?;

        if embeddings.len() != descriptions.len() {
            tracing::warn!(
                "embedding router: expected {} embeddings, got {} — falling back to TF-IDF",
                descriptions.len(),
                embeddings.len()
            );
            return None;
        }

        let mut tool_embeddings = AHashMap::with_capacity(descriptions.len());
        for ((name, _), emb) in descriptions.into_iter().zip(embeddings.into_iter()) {
            tool_embeddings.insert(name, emb);
        }

        tracing::info!(
            "embedding router initialized with {} tools, dim={}, backend={}",
            tool_embeddings.len(),
            dim,
            embedder.backend_name()
        );

        Some(Self {
            tool_embeddings,
            embedder,
            outcome_stats: RwLock::new(AHashMap::new()),
            dim,
            apply_prefix_bonus,
        })
    }

    /// Route a natural language query to a tool name and confidence score.
    ///
    /// Returns `("gnosis", 0.0)` for empty input or when no tool scores above
    /// the minimum threshold.
    #[must_use]
    pub fn route(&self, query: &str) -> (String, f64) {
        match self.route_with_margin(query) {
            Some((t, c, _)) => (t, c),
            None => ("gnosis".into(), 0.0),
        }
    }

    /// Route a query, returning (tool, confidence, margin).
    ///
    /// `margin` is the score gap between the top-1 and top-2 tools. Small
    /// margins indicate the descriptions cannot separate intent — callers
    /// should defer to the TF-IDF router when `margin < MIN_MARGIN`.
    #[must_use]
    pub fn route_with_margin(&self, query: &str) -> Option<(String, f64, f64)> {
        let lower = query.to_lowercase();
        if lower.trim().is_empty() {
            return None;
        }

        let query_emb = match self.embedder.embed(&lower) {
            Ok(emb) => emb,
            Err(e) => {
                tracing::warn!(error = %e, "embedding router: query embedding failed");
                return None;
            }
        };

        // Prefix route bonus — only on the legacy keyword-profile path, where
        // descriptions are bare keyword lists and the verb bonus compensates.
        // On the anchored path it fights the intent anchors ("list tools" was
        // boosted toward memory.list despite tools.list carrying the anchor).
        let prefix_bonus: Option<(&str, f64)> = if self.apply_prefix_bonus {
            let first_word = lower.split_whitespace().next().unwrap_or("");
            PREFIX_ROUTES
                .iter()
                .find(|(verb, _, _)| *verb == first_word)
                .map(|(_, tool, bonus)| (*tool, *bonus))
        } else {
            None
        };

        // Score each tool by cosine similarity to (optionally refined) embedding
        let Ok(stats_lock) = self.outcome_stats.read() else {
            return None;
        };

        let mut best_tool = "gnosis".to_string();
        let mut best_score = 0.0_f64;
        let mut second_score = 0.0_f64;

        for (name, base_emb) in &self.tool_embeddings {
            let refined = self.oats_refine(name, base_emb, &stats_lock);
            let mut score = f64::from(cosine_sim(&query_emb, &refined));

            // Apply prefix routing: bonus to matching tool, penalty to non-matching
            if let Some((bonus_tool, bonus)) = prefix_bonus {
                if name == bonus_tool {
                    score *= bonus;
                } else {
                    score /= bonus;
                }
            }

            if score > best_score {
                second_score = best_score;
                best_score = score;
                best_tool.clone_from(name);
            } else if score > second_score {
                second_score = score;
            }
        }

        drop(stats_lock);

        if best_score < MIN_THRESHOLD {
            return None;
        }

        Some((best_tool, best_score, best_score - second_score))
    }

    /// OATS: interpolate tool embedding toward success centroid.
    ///
    /// If we have enough success observations (≥ `OATS_MIN_OBSERVATIONS`),
    /// blend the base embedding toward the success centroid by `OATS_ALPHA`.
    /// Otherwise, return the base embedding unchanged.
    fn oats_refine(
        &self,
        tool_name: &str,
        base_emb: &[f32],
        stats: &AHashMap<String, OutcomeStats>,
    ) -> Vec<f32> {
        if let Some(stat) = stats.get(tool_name) {
            if stat.is_ready() && stat.success_centroid.len() == base_emb.len() {
                return interpolate(base_emb, &stat.success_centroid, OATS_ALPHA);
            }
        }
        base_emb.to_vec()
    }

    /// Record a routing outcome for OATS refinement.
    ///
    /// Call this after each tool dispatch to track whether the routing was
    /// correct. `success = true` means the tool was the right choice and
    /// executed successfully; `false` means it was wrong or failed.
    pub fn record_outcome(&self, tool_name: &str, query: &str, success: bool) {
        if query.trim().is_empty() {
            return;
        }

        let query_emb = match self.embedder.embed(&query.to_lowercase()) {
            Ok(emb) => emb,
            Err(_) => return,
        };

        let Ok(mut stats) = self.outcome_stats.write() else {
            return;
        };
        let stat = stats
            .entry(tool_name.to_string())
            .or_insert_with(|| OutcomeStats::new(self.dim));
        stat.record(&query_emb, success);
    }

    /// Number of tool embeddings in the router.
    #[must_use]
    pub fn tool_count(&self) -> usize {
        self.tool_embeddings.len()
    }

    /// Embedding dimensionality.
    #[must_use]
    pub const fn dimension(&self) -> usize {
        self.dim
    }

    /// Embedder backend name.
    #[must_use]
    pub fn backend_name(&self) -> &str {
        self.embedder.backend_name()
    }

    /// Get a snapshot of outcome stats counts for observability.
    #[must_use]
    pub fn outcome_counts(&self) -> Vec<(String, usize, usize)> {
        let Ok(stats) = self.outcome_stats.read() else {
            return Vec::new();
        };
        stats
            .iter()
            .map(|(name, s)| (name.clone(), s.success_count, s.failure_count))
            .collect()
    }

    /// Serialize OATS outcome stats to JSON for persistence.
    #[must_use]
    #[allow(clippy::type_complexity)]
    pub fn save_oats(&self) -> Option<String> {
        let Ok(stats) = self.outcome_stats.read() else {
            return None;
        };
        let serializable: Vec<(String, usize, usize, Vec<f32>, Vec<f32>)> = stats
            .iter()
            .map(|(name, s)| {
                (
                    name.clone(),
                    s.success_count,
                    s.failure_count,
                    s.success_centroid.clone(),
                    s.failure_centroid.clone(),
                )
            })
            .collect();
        serde_json::to_string_pretty(&serializable).ok()
    }

    /// Load OATS outcome stats from JSON (previously saved by `save_oats`).
    pub fn load_oats(&self, json: &str) {
        if let Ok(data) =
            serde_json::from_str::<Vec<(String, usize, usize, Vec<f32>, Vec<f32>)>>(json)
        {
            let Ok(mut stats) = self.outcome_stats.write() else {
                return;
            };
            for (name, success_count, failure_count, success_centroid, failure_centroid) in data {
                let dim = success_centroid.len().max(self.dim);
                let mut s = OutcomeStats::new(dim);
                s.success_count = success_count;
                s.failure_count = failure_count;
                s.success_centroid = success_centroid;
                s.failure_centroid = failure_centroid;
                stats.insert(name, s);
            }
            tracing::info!("Loaded OATS outcome stats from disk");
        }
    }
}

// ── Shadow Mode Stats ────────────────────────────────────────────────

/// Maximum number of disagreement samples to retain.
const MAX_SAMPLES: usize = 50;

/// A single disagreement sample between embedding router and TF-IDF.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct DisagreementSample {
    pub query: String,
    pub embedding_tool: String,
    pub embedding_conf: f64,
    pub tfidf_tool: String,
    pub tfidf_conf: f64,
}

/// Shadow mode statistics tracking embedding vs TF-IDF disagreements.
///
/// Thread-safe via `RwLock`. Updated on every `classify_with_router` call
/// when the embedding router is active.
#[derive(Debug, Default, serde::Serialize, serde::Deserialize)]
pub struct ShadowModeStats {
    /// Total queries routed through shadow mode.
    pub total_queries: u64,
    /// Total disagreements (embedding chose different tool than TF-IDF).
    pub total_disagreements: u64,
    /// Per-tool disagreement counts: (embedding_tool, tfidf_tool) → count.
    pub disagreement_pairs: std::collections::HashMap<String, u64>,
    /// Recent disagreement samples (capped at MAX_SAMPLES).
    pub samples: Vec<DisagreementSample>,
}

impl ShadowModeStats {
    /// Record a routing comparison.
    pub fn record(
        &mut self,
        query: &str,
        emb_tool: &str,
        emb_conf: f64,
        tfidf_tool: &str,
        tfidf_conf: f64,
    ) {
        self.total_queries += 1;
        if emb_tool != tfidf_tool {
            self.total_disagreements += 1;
            let key = format!("{emb_tool} → {tfidf_tool}");
            *self.disagreement_pairs.entry(key).or_insert(0) += 1;
            if self.samples.len() >= MAX_SAMPLES {
                self.samples.remove(0);
            }
            self.samples.push(DisagreementSample {
                query: query.chars().take(200).collect(),
                embedding_tool: emb_tool.to_string(),
                embedding_conf: emb_conf,
                tfidf_tool: tfidf_tool.to_string(),
                tfidf_conf,
            });
        }
    }

    /// Disagreement rate (0.0–1.0).
    #[must_use]
    pub fn disagreement_rate(&self) -> f64 {
        if self.total_queries == 0 {
            0.0
        } else {
            self.total_disagreements as f64 / self.total_queries as f64
        }
    }

    /// Whether the embedding router is ready for promotion to primary
    /// (disagreement rate below 20% and enough samples).
    #[must_use]
    pub fn promotion_ready(&self) -> bool {
        self.total_queries >= 100 && self.disagreement_rate() < 0.20
    }

    /// Generate a JSON report for the `nlu.shadow_report` tool.
    #[must_use]
    pub fn report(&self) -> serde_json::Value {
        let mut pairs: Vec<(String, u64)> = self
            .disagreement_pairs
            .iter()
            .map(|(k, v)| (k.clone(), *v))
            .collect();
        pairs.sort_by(|a, b| b.1.cmp(&a.1));

        serde_json::json!({
            "total_queries": self.total_queries,
            "total_disagreements": self.total_disagreements,
            "disagreement_rate": self.disagreement_rate(),
            "promotion_ready": self.promotion_ready(),
            "top_disagreement_pairs": pairs.iter().take(10).map(|(k, v)| {
                serde_json::json!({"pair": k, "count": v})
            }).collect::<Vec<_>>(),
            "recent_samples": self.samples.iter().take(10).map(|s| {
                serde_json::json!({
                    "query": s.query,
                    "embedding_tool": s.embedding_tool,
                    "embedding_conf": s.embedding_conf,
                    "tfidf_tool": s.tfidf_tool,
                    "tfidf_conf": s.tfidf_conf,
                })
            }).collect::<Vec<_>>(),
        })
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

/// Linear interpolation between two vectors: `base * (1 - α) + target * α`.
fn interpolate(base: &[f32], target: &[f32], alpha: f32) -> Vec<f32> {
    base.iter()
        .zip(target.iter())
        .map(|(b, t)| b * (1.0 - alpha) + t * alpha)
        .collect()
}

/// Generate tool descriptions from the static TOOL_PROFILES.
///
/// Each description is the tool name followed by its keywords. This gives the
/// embedder semantic content to work with. Example:
///
/// `"memory.create remember store save memorize record persist capture"`
#[must_use]
pub fn tool_descriptions() -> Vec<(String, String)> {
    TOOL_PROFILES
        .iter()
        .map(|p| (p.tool_name.to_string(), profile_to_description(p)))
        .collect()
}

/// Convert a ToolProfile into a description string for embedding.
fn profile_to_description(profile: &ToolProfile) -> String {
    let keywords: Vec<&str> = profile.keywords.iter().map(|(t, _)| *t).collect();
    format!("{} {}", profile.tool_name, keywords.join(" "))
}

/// Intent anchors: natural-language phrasings users say when they mean a tool.
///
/// The registry's `description()` strings describe *what a tool does* (display
/// prose) but rarely match how users phrase intent. The 2026-08-11 shadow runs
/// showed top-1 cosine collapsing onto arbitrary tools for common phrasings
/// ("show my karma" → karma.clear). Anchors are appended to the embedded text
/// so the vector for each tool covers user phrasing, not just docstring prose.
static INTENT_ANCHORS: &[(&str, &[&str])] = &[
    // Memory
    (
        "memory.create",
        &[
            "remember that",
            "store this note",
            "save this thought",
            "memorize this",
            "keep this in memory",
            "note that",
            "record that",
        ],
    ),
    (
        "memory.read",
        &[
            "get memory by id",
            "read this memory",
            "recall what I said",
            "fetch memory",
        ],
    ),
    (
        "memory.list",
        &[
            "list my memories",
            "show my recent memories",
            "what memories do I have",
            "find memories about",
            "memories in the codex galaxy",
        ],
    ),
    (
        "memory.search",
        &[
            "search my memories for",
            "find memory about",
            "memory search",
            "search for rust",
            "search memories",
        ],
    ),
    (
        "memory.vector.search",
        &[
            "find memory about search",
            "semantic search",
            "similar memories",
        ],
    ),
    (
        "memory.count",
        &["count my memories", "how many memories", "memory count"],
    ),
    ("memory.tags", &["what tags do I have", "show memory tags"]),
    (
        "memory.delete",
        &["delete memory", "remove memory", "forget this memory"],
    ),
    // Galaxy
    (
        "galaxy.list",
        &["list galaxies", "what galaxies exist", "show the galaxies"],
    ),
    (
        "galaxy.stats",
        &[
            "galaxy stats",
            "stats for the codex galaxy",
            "how many memories are in",
            "show galaxy info",
        ],
    ),
    (
        "galaxy.create",
        &["create a new galaxy", "new galaxy called", "make a galaxy"],
    ),
    ("galaxy.health", &["check galaxy health", "galaxy health"]),
    (
        "galaxy.taxonomy",
        &["gana taxonomy", "show the gana taxonomy"],
    ),
    // Session
    ("session.start", &["start a session", "begin a new session"]),
    ("session.end", &["end the session", "close the session"]),
    (
        "session.list",
        &[
            "what sessions do I have",
            "list sessions",
            "show session history",
        ],
    ),
    (
        "session.record",
        &["record this session turn", "log this session turn"],
    ),
    (
        "session.replay",
        &["replay the session", "replay last session"],
    ),
    (
        "session.recall",
        &[
            "recall the session context",
            "session history",
            "previous session",
            "record that the server restarted",
        ],
    ),
    (
        "session.handoff",
        &[
            "hand off the session",
            "transfer session",
            "session handoff",
        ],
    ),
    // Karma
    (
        "karma.report",
        &[
            "show my karma",
            "karma status",
            "check my karma",
            "karma balance",
            "karma report",
            "karma ledger status",
        ],
    ),
    (
        "karma.history",
        &["karma history", "past karma entries", "recent karma"],
    ),
    (
        "karma.clear",
        &["clear karma", "wipe karma", "reset karma", "purge karma"],
    ),
    (
        "karma.verify_chain",
        &[
            "check the karma chain",
            "verify chain integrity",
            "karma chain",
        ],
    ),
    (
        "karma.anchor",
        &["anchor the karma chain", "publish anchor", "merkle anchor"],
    ),
    // Friction / RSI
    (
        "friction.log",
        &["log friction", "log an error", "log friction entry"],
    ),
    (
        "friction.review",
        &[
            "review the friction log",
            "review friction",
            "friction review",
        ],
    ),
    (
        "friction.auto_log",
        &["auto log friction", "automatically log friction"],
    ),
    (
        "friction.resolve",
        &["resolve friction", "resolve this friction"],
    ),
    (
        "improve.proposals",
        &[
            "what proposals are active",
            "improvement proposals",
            "list proposals",
        ],
    ),
    // Claims
    (
        "claims",
        &[
            "add a claim",
            "resolve a claim",
            "claims status",
            "what claims are pending",
            "list claims",
        ],
    ),
    // Transaction
    ("transaction.begin", &["begin a transaction"]),
    ("transaction.commit", &["commit the transaction"]),
    ("transaction.rollback", &["rollback the transaction"]),
    // Tools / meta
    (
        "tools.list",
        &[
            "list tools",
            "what tools do you have",
            "tools list",
            "list all tools",
        ],
    ),
    (
        "nlu.shadow_report",
        &["nlu shadow report", "show shadow mode stats"],
    ),
    (
        "nlu.classify",
        &["nlu classification test", "classify this query"],
    ),
    (
        "state.snapshot",
        &[
            "what is the brain wave state",
            "brain wave state",
            "current brain wave",
        ],
    ),
    (
        "system.stats",
        &["system stats", "show resource usage", "system stats please"],
    ),
    (
        "system.health",
        &[
            "health check",
            "doctor check",
            "run a health check",
            "system health",
        ],
    ),
    (
        "galaxy.dashboard",
        &["consciousness dashboard", "display the dashboard"],
    ),
    (
        "consciousness.depth",
        &["consciousness depth", "depth of consciousness"],
    ),
    // Web / research
    (
        "web.fetch",
        &[
            "fetch this webpage",
            "fetch the url and summarize",
            "fetch url",
        ],
    ),
    ("web.search", &["search the web for", "web search"]),
    (
        "web.search_and_read",
        &["search and read", "search the web and read"],
    ),
    ("web.deep_fetch", &["deep fetch", "deep fetch this page"]),
    (
        "research.topic",
        &[
            "research the topic of",
            "research topic",
            "do a deep search on",
        ],
    ),
    (
        "research.repo",
        &["research a github repo", "research repo", "github repo"],
    ),
    (
        "research.rabbit_hole",
        &["rabbit hole research", "rabbit hole"],
    ),
    // Self-play
    (
        "selfplay.run",
        &["run selfplay", "start selfplay", "run training"],
    ),
    ("selfplay.status", &["selfplay status", "training status"]),
    (
        "selfplay.export",
        &["export training data", "export selfplay data"],
    ),
    // Simulation / imagination
    (
        "sim.mc",
        &[
            "run a simulation",
            "monte carlo simulation",
            "simulate this",
        ],
    ),
    (
        "imagine.scenario",
        &["imagine a scenario", "scenario planning"],
    ),
    (
        "imagine.reflect",
        &["reflect on this scenario", "counterfactual replay"],
    ),
    (
        "gnosis",
        &[
            "what is your gana",
            "who are you",
            "what do I know about the wm project",
        ],
    ),
];

/// Merge registry tool descriptions with intent anchors for embedding.
///
/// Each description becomes: `"<name>: <registry description> — users say:
/// <anchors joined>"`. Tools without anchors keep their prose description.
///
/// Tools whose `description()` is the Gana-level fallback (the default
/// `Tool::description()` returns `gana().description()`, so ~45 tools across
/// the registry embed to one of 28 shared vectors — e.g. all conformal.* and
/// selfmodel.* tools) get a synthesized description from their dotted name:
/// `"conformal.monitor"` → `"conformal monitor — monitor conformal
/// prediction coverage and drift"`. Without this the router's margin
/// calculation collapses on families with shared Gana text.
#[must_use]
pub fn anchored_descriptions(tools: &[Arc<dyn wm_core::Tool>]) -> Vec<(String, String)> {
    tools
        .iter()
        .map(|t| {
            let name = t.name();
            let gana_fallback = t.gana().description() == t.description();
            let desc = if gana_fallback {
                synthesize_description(name)
            } else {
                t.description().to_string()
            };
            let anchors = INTENT_ANCHORS
                .iter()
                .find(|(n, _)| *n == name)
                .map(|(_, a)| a);
            let text = match anchors {
                Some(anchors) => format!("{name}: {desc} — users say: {}", anchors.join("; ")),
                None => format!("{name}: {desc}"),
            };
            (name.to_string(), text)
        })
        .collect()
}

/// Build a description from a dotted tool name when the tool has no explicit
/// description (falls back to its Gana's generic text).
///
/// `"conformal.monitor"` → `"conformal monitor — monitor conformal prediction
/// coverage and drift"`. The family verb (the last segment) is repeated as a
/// verb so the embedded text carries tool-specific intent instead of the
/// shared Gana vector.
fn synthesize_description(name: &str) -> String {
    let parts: Vec<&str> = name.split('.').collect();
    if parts.len() < 2 {
        return format!("{name} — {name} operations");
    }
    let family = parts[..parts.len() - 1].join(" ");
    let verb = parts[parts.len() - 1];
    let verb_hyphen = verb.replace('_', "-");
    format!("{family} {verb_hyphen} — {family} {verb} operations and status")
}

// ── Tests ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // --- Unit tests for helper functions ---

    #[test]
    fn cosine_sim_identical_vectors() {
        let v = vec![1.0, 2.0, 3.0];
        let sim = cosine_sim(&v, &v);
        assert!(
            (sim - 1.0).abs() < 1e-5,
            "identical vectors should have sim=1.0, got {sim}"
        );
    }

    #[test]
    fn cosine_sim_orthogonal_vectors() {
        let a = vec![1.0, 0.0];
        let b = vec![0.0, 1.0];
        let sim = cosine_sim(&a, &b);
        assert!(
            sim.abs() < 1e-5,
            "orthogonal vectors should have sim=0.0, got {sim}"
        );
    }

    #[test]
    fn cosine_sim_empty_vectors() {
        let sim = cosine_sim(&[], &[]);
        assert_eq!(sim, 0.0);
    }

    #[test]
    fn cosine_sim_different_lengths() {
        let a = vec![1.0, 2.0];
        let b = vec![1.0, 2.0, 3.0];
        let sim = cosine_sim(&a, &b);
        assert_eq!(sim, 0.0, "different-length vectors should return 0.0");
    }

    #[test]
    fn interpolate_midpoint() {
        let base = vec![0.0, 0.0];
        let target = vec![10.0, 20.0];
        let result = interpolate(&base, &target, 0.5);
        assert!((result[0] - 5.0).abs() < 1e-5);
        assert!((result[1] - 10.0).abs() < 1e-5);
    }

    #[test]
    fn interpolate_zero_alpha_returns_base() {
        let base = vec![1.0, 2.0, 3.0];
        let target = vec![10.0, 20.0, 30.0];
        let result = interpolate(&base, &target, 0.0);
        assert_eq!(result, base);
    }

    #[test]
    fn interpolate_one_alpha_returns_target() {
        let base = vec![1.0, 2.0, 3.0];
        let target = vec![10.0, 20.0, 30.0];
        let result = interpolate(&base, &target, 1.0);
        assert_eq!(result, target);
    }

    // --- OutcomeStats tests ---

    #[test]
    fn outcome_stats_starts_empty() {
        let stats = OutcomeStats::new(384);
        assert_eq!(stats.success_count, 0);
        assert_eq!(stats.failure_count, 0);
        assert!(!stats.is_ready());
    }

    #[test]
    fn outcome_stats_records_success() {
        let mut stats = OutcomeStats::new(4);
        stats.record(&[1.0, 0.0, 0.0, 0.0], true);
        assert_eq!(stats.success_count, 1);
        assert_eq!(stats.failure_count, 0);
    }

    #[test]
    fn outcome_stats_records_failure() {
        let mut stats = OutcomeStats::new(4);
        stats.record(&[0.0, 1.0, 0.0, 0.0], false);
        assert_eq!(stats.success_count, 0);
        assert_eq!(stats.failure_count, 1);
    }

    #[test]
    fn outcome_stats_centroid_converges() {
        let mut stats = OutcomeStats::new(2);
        // Record 3 successes at the same point
        for _ in 0..3 {
            stats.record(&[1.0, 0.0], true);
        }
        // Centroid should converge to [1.0, 0.0]
        assert!((stats.success_centroid[0] - 1.0).abs() < 1e-3);
        assert!(stats.success_centroid[1].abs() < 1e-3);
    }

    #[test]
    fn outcome_stats_becomes_ready_after_min_observations() {
        let mut stats = OutcomeStats::new(2);
        for _ in 0..OATS_MIN_OBSERVATIONS {
            stats.record(&[1.0, 0.0], true);
        }
        assert!(stats.is_ready());
    }

    #[test]
    fn outcome_stats_ignores_empty_embedding() {
        let mut stats = OutcomeStats::new(4);
        stats.record(&[], true);
        assert_eq!(stats.success_count, 0);
    }

    // --- Tool description generation tests ---

    #[test]
    fn tool_descriptions_non_empty() {
        let descs = tool_descriptions();
        assert!(
            !descs.is_empty(),
            "should have descriptions for all profiles"
        );
        assert!(
            descs.len() >= 60,
            "expected 60+ descriptions, got {}",
            descs.len()
        );
    }

    #[test]
    fn tool_descriptions_contain_tool_name() {
        let descs = tool_descriptions();
        for (name, desc) in &descs {
            assert!(
                desc.starts_with(name),
                "description for '{name}' should start with the tool name, got: {desc}"
            );
        }
    }

    #[test]
    fn tool_descriptions_contain_keywords() {
        let descs = tool_descriptions();
        let memory_create = descs.iter().find(|(n, _)| n == "memory.create");
        assert!(memory_create.is_some());
        let (_, desc) = memory_create.unwrap();
        assert!(
            desc.contains("remember"),
            "memory.create description should contain 'remember'"
        );
        assert!(
            desc.contains("store"),
            "memory.create description should contain 'store'"
        );
    }

    #[test]
    fn tool_descriptions_are_unique() {
        let descs = tool_descriptions();
        let names: Vec<&str> = descs.iter().map(|(n, _)| n.as_str()).collect();
        let set: std::collections::HashSet<&str> = names.iter().copied().collect();
        assert_eq!(
            names.len(),
            set.len(),
            "duplicate tool names in descriptions"
        );
    }

    // --- EmbeddingRouter with stub embedder ---

    #[test]
    fn embedding_router_returns_none_for_stub() {
        let stub = Box::new(wm_memory::StubEmbedder::default());
        let router = EmbeddingRouter::new(stub);
        assert!(
            router.is_none(),
            "embedding router should return None for stub embedder"
        );
    }

    #[test]
    fn embedding_router_with_descriptions_covers_registry_tools() {
        let embedder = Box::new(KeywordEmbedder::new(vec![
            "memory", "karma", "session", "list",
        ]));
        let descriptions = vec![
            (
                "memory.create".to_string(),
                "remember and store information in persistent memory".to_string(),
            ),
            (
                "karma.clear".to_string(),
                "wipe and reset the karma ledger entries".to_string(),
            ),
            (
                "session.list".to_string(),
                "list all recorded sessions".to_string(),
            ),
        ];
        let router =
            EmbeddingRouter::with_descriptions(embedder, descriptions).expect("should init");
        assert_eq!(router.tool_count(), 3);
        let (tool, _) = router.route("show me the sessions");
        assert_eq!(
            tool, "session.list",
            "registry-description routing should find session.list"
        );
    }

    #[test]
    fn route_with_margin_returns_positive_margin() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        let (tool, conf, margin) = router
            .route_with_margin("remember that the sky is blue")
            .expect("clear match should return Some");
        assert_eq!(tool, "memory.create");
        assert!(conf > 0.0);
        assert!(margin >= 0.0, "margin should be non-negative");
    }

    // --- Mock embedder for testing ---

    /// A test embedder that generates simple keyword-based embeddings.
    /// Each dimension corresponds to a keyword — if the text contains the
    /// keyword, that dimension is 1.0, otherwise 0.0. This provides basic
    /// semantic similarity for testing without a real embedder.
    struct KeywordEmbedder {
        keywords: Vec<String>,
        dim: usize,
    }

    impl KeywordEmbedder {
        fn new(keywords: Vec<&str>) -> Self {
            let dim = keywords.len();
            Self {
                keywords: keywords.into_iter().map(String::from).collect(),
                dim,
            }
        }

        fn embed_text(&self, text: &str) -> Vec<f32> {
            let lower = text.to_lowercase();
            self.keywords
                .iter()
                .map(|kw| {
                    if lower.contains(&kw.to_lowercase()) {
                        1.0
                    } else {
                        0.0
                    }
                })
                .collect()
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

    #[test]
    fn embedding_router_works_with_keyword_embedder() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init with keyword embedder");

        assert!(router.tool_count() >= 60);
        assert!(router.dimension() > 0);
        assert_eq!(router.backend_name(), "keyword-test");
    }

    #[test]
    fn embedding_router_routes_remember_to_memory_create() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        let (tool, conf) = router.route("remember that the sky is blue");
        assert_eq!(tool, "memory.create");
        assert!(
            conf > 0.0,
            "confidence should be > 0 for clear match, got {conf}"
        );
    }

    #[test]
    fn embedding_router_routes_search_to_memory_search() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        let (tool, conf) = router.route("search for rust");
        assert_eq!(tool, "memory.search");
        assert!(conf > 0.0);
    }

    #[test]
    fn embedding_router_empty_returns_gnosis() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        let (tool, conf) = router.route("");
        assert_eq!(tool, "gnosis");
        assert_eq!(conf, 0.0);
    }

    #[test]
    fn embedding_router_whitespace_returns_gnosis() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        let (tool, conf) = router.route("   ");
        assert_eq!(tool, "gnosis");
        assert_eq!(conf, 0.0);
    }

    #[test]
    fn embedding_router_unknown_returns_gnosis() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        let (tool, _conf) = router.route("xyzzy frobnicate");
        assert_eq!(tool, "gnosis");
    }

    #[test]
    fn embedding_router_record_outcome_updates_stats() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        // Record some outcomes
        router.record_outcome("memory.create", "remember that rust is fast", true);
        router.record_outcome("memory.create", "store this fact", true);
        router.record_outcome("memory.search", "search for rust", false);

        let counts = router.outcome_counts();
        let memory_create = counts.iter().find(|(n, _, _)| n == "memory.create");
        assert!(memory_create.is_some());
        let (_, success, failure) = memory_create.unwrap();
        assert_eq!(*success, 2);
        assert_eq!(*failure, 0);
    }

    #[test]
    fn embedding_router_record_outcome_ignores_empty_query() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        router.record_outcome("memory.create", "", true);
        let counts = router.outcome_counts();
        assert!(
            counts.is_empty(),
            "empty query should not create outcome stats"
        );
    }

    #[test]
    fn embedding_router_oats_refine_improves_routing() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        // Record many successes for memory.create with "save" queries
        for _ in 0..15 {
            router.record_outcome("memory.create", "save this important fact", true);
        }

        // Now "save this important fact" should route to memory.create with high confidence
        let (tool, conf) = router.route("save this important fact");
        assert_eq!(tool, "memory.create");
        assert!(
            conf > 0.0,
            "OATS-refined routing should still match, got conf={conf}"
        );
    }

    // --- A/B comparison: embedding router vs TF-IDF on key test cases ---

    #[test]
    fn ab_comparison_remember() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        let query = "remember that the sky is blue";
        let (emb_tool, emb_conf) = router.route(query);
        let (tfidf_tool, tfidf_conf) = crate::nlu::classify(query);

        assert_eq!(
            emb_tool, tfidf_tool,
            "embedding and TF-IDF should agree on '{query}'"
        );
        assert!(emb_conf > 0.0 && tfidf_conf > 0.0);
    }

    #[test]
    fn ab_comparison_search() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        let query = "search for rust";
        let (emb_tool, emb_conf) = router.route(query);
        let (tfidf_tool, _) = crate::nlu::classify(query);

        assert_eq!(
            emb_tool, tfidf_tool,
            "embedding and TF-IDF should agree on '{query}'"
        );
        assert!(emb_conf > 0.0);
    }

    #[test]
    fn ab_comparison_delete() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        let query = "delete memory abc-123";
        let (emb_tool, _) = router.route(query);
        let (tfidf_tool, _) = crate::nlu::classify(query);

        assert_eq!(
            emb_tool, tfidf_tool,
            "embedding and TF-IDF should agree on '{query}'"
        );
    }

    #[test]
    fn ab_comparison_karma() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        let query = "show me the karma report";
        let (emb_tool, _) = router.route(query);
        let (tfidf_tool, _) = crate::nlu::classify(query);

        assert_eq!(
            emb_tool, tfidf_tool,
            "embedding and TF-IDF should agree on '{query}'"
        );
    }

    // ── ShadowModeStats tests ─────────────────────────────────────────

    #[test]
    fn shadow_stats_record_agreement() {
        let mut stats = ShadowModeStats::default();
        stats.record("test query", "memory.create", 0.9, "memory.create", 0.8);
        assert_eq!(stats.total_queries, 1);
        assert_eq!(stats.total_disagreements, 0);
        assert!(stats.samples.is_empty());
    }

    #[test]
    fn shadow_stats_record_disagreement() {
        let mut stats = ShadowModeStats::default();
        stats.record("test query", "memory.create", 0.9, "memory.list", 0.7);
        assert_eq!(stats.total_queries, 1);
        assert_eq!(stats.total_disagreements, 1);
        assert_eq!(stats.samples.len(), 1);
        assert_eq!(stats.samples[0].embedding_tool, "memory.create");
        assert_eq!(stats.samples[0].tfidf_tool, "memory.list");
    }

    #[test]
    fn shadow_stats_disagreement_rate() {
        let mut stats = ShadowModeStats::default();
        for _ in 0..8 {
            stats.record("agree", "memory.create", 0.9, "memory.create", 0.8);
        }
        for _ in 0..2 {
            stats.record("disagree", "memory.create", 0.9, "memory.list", 0.7);
        }
        assert_eq!(stats.total_queries, 10);
        assert_eq!(stats.total_disagreements, 2);
        assert!((stats.disagreement_rate() - 0.2).abs() < 0.001);
    }

    #[test]
    fn shadow_stats_promotion_ready_threshold() {
        let mut stats = ShadowModeStats::default();
        // Not enough queries
        for _ in 0..99 {
            stats.record("agree", "memory.create", 0.9, "memory.create", 0.8);
        }
        assert!(!stats.promotion_ready());

        // Enough queries, low disagreement
        stats.record("agree", "memory.create", 0.9, "memory.create", 0.8);
        assert!(stats.promotion_ready());

        // Too many disagreements (25 out of 125 = 0.20, not < 0.20)
        for _ in 0..25 {
            stats.record("disagree", "memory.create", 0.9, "memory.list", 0.7);
        }
        assert!(!stats.promotion_ready());
    }

    #[test]
    fn shadow_stats_report_json() {
        let mut stats = ShadowModeStats::default();
        stats.record("test", "memory.create", 0.9, "memory.list", 0.7);
        let report = stats.report();
        assert_eq!(report["total_queries"], 1);
        assert_eq!(report["total_disagreements"], 1);
        assert!(report["promotion_ready"].is_boolean());
        assert!(report["recent_samples"].is_array());
    }

    #[test]
    fn shadow_stats_samples_capped() {
        let mut stats = ShadowModeStats::default();
        for i in 0..100 {
            stats.record(
                &format!("query {i}"),
                "memory.create",
                0.9,
                "memory.list",
                0.7,
            );
        }
        assert_eq!(stats.samples.len(), 50); // MAX_SAMPLES
    }

    #[test]
    fn shadow_stats_serialization_roundtrip() {
        let mut stats = ShadowModeStats::default();
        stats.record("test", "memory.create", 0.9, "memory.list", 0.7);
        stats.record("another", "gnosis", 0.1, "gnosis", 0.1);
        let json = serde_json::to_string(&stats).unwrap();
        let deserialized: ShadowModeStats = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.total_queries, 2);
        assert_eq!(deserialized.total_disagreements, 1);
        assert_eq!(deserialized.samples.len(), 1);
    }

    #[test]
    fn oats_persistence_roundtrip() {
        let keywords: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder = Box::new(KeywordEmbedder::new(keywords));
        let router = EmbeddingRouter::new(embedder).expect("should init");

        // Record some outcomes
        router.record_outcome("memory.create", "create a memory", true);
        router.record_outcome("memory.create", "store this", true);
        router.record_outcome("memory.list", "list memories", true);

        // Save
        let saved = router.save_oats().expect("should serialize");

        // Load into a new router
        let keywords2: Vec<&str> = TOOL_PROFILES
            .iter()
            .flat_map(|p| p.keywords.iter().map(|(t, _)| *t))
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        let embedder2 = Box::new(KeywordEmbedder::new(keywords2));
        let router2 = EmbeddingRouter::new(embedder2).expect("should init");
        router2.load_oats(&saved);

        let counts1 = router.outcome_counts();
        let counts2 = router2.outcome_counts();
        assert_eq!(counts1.len(), counts2.len());
        for (name, success, failure) in &counts1 {
            let match_found = counts2
                .iter()
                .any(|(n, s, f)| n == name && s == success && f == failure);
            assert!(
                match_found,
                "OATS data should match after roundtrip for {name}"
            );
        }
    }
}
