//! Conversational Memory Search (Phase N5).
//!
//! User-facing sub-50ms hybrid search path built on top of [`RecallEngine`].
//!
//! Features:
//! - **Query complexity classification**: detects sensitive queries, tool-call
//!   intent, and multi-turn patterns to adjust search behavior
//! - **LRU query cache**: caches recent query results for instant re-query
//! - **Performance metrics**: tracks latency percentiles and cache hit rates
//! - **Galaxy filtering**: restrict search to specific memory galaxies
//! - **Snippet extraction**: returns truncated content snippets for UI display
//!
//! # Architecture
//!
//! ```text
//! User Query
//!     │
//!     ▼
//! ┌──────────────────┐     ┌─────────────────┐
//! │ QueryClassifier  │────▶│  Cache Lookup   │
//! └──────────────────┘     └────────┬────────┘
//!                                   │ miss
//!                                   ▼
//!                          ┌─────────────────┐
//!                          │  RecallEngine   │
//!                          │  hybrid_search  │
//!                          └────────┬────────┘
//!                                   │
//!                                   ▼
//!                          ┌─────────────────┐
//!                          │  Result Builder │
//!                          │  + Snippets     │
//!                          └────────┬────────┘
//!                                   │
//!                                   ▼
//!                          ┌─────────────────┐
//!                          │  Cache Store    │
//!                          └─────────────────┘
//! ```
//!
//! # Environment Variables
//!
//! | Variable | Default | Description |
//! |----------|---------|-------------|
//! | `WM_CONVERSATIONAL_CACHE_SIZE` | `128` | Max cached queries |
//! | `WM_CONVERSATIONAL_SNIPPET_LEN` | `200` | Max snippet length (chars) |
//! | `WM_CONVERSATIONAL_DEFAULT_LIMIT` | `10` | Default result limit |

#![allow(clippy::significant_drop_tightening)]

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Instant;
use uuid::Uuid;
use wm_core::{Galaxy, Result};

use crate::recall::{RecallEngine, RecallResult};

// ── Query Classification ──────────────────────────────────────────────

/// Classification of a conversational search query.
#[derive(Debug, Clone)]
pub struct QueryClassification {
    /// Whether the query contains sensitive data patterns.
    pub is_sensitive: bool,
    /// Whether the query looks like a tool-call request.
    pub needs_tool_calls: bool,
    /// Whether the query is multi-turn/sequential.
    pub is_multi_turn: bool,
    /// Estimated complexity (0.0 = simple, 1.0 = complex).
    pub complexity: f32,
    /// Detected task type label.
    pub task_type: String,
}

impl QueryClassification {
    /// Classify a query using lightweight pattern matching.
    #[must_use]
    pub fn classify(query: &str) -> Self {
        let is_sensitive = SENSITIVITY_PATTERNS
            .iter()
            .any(|p| query.to_lowercase().contains(p));

        let needs_tool_calls = TOOL_CALL_PATTERNS
            .iter()
            .any(|p| query.to_lowercase().contains(p));

        let is_multi_turn = MULTI_TURN_PATTERNS
            .iter()
            .any(|p| query.to_lowercase().contains(p));

        let word_count = query.split_whitespace().count();
        let complexity = match word_count {
            0..=5 => 0.1,
            6..=15 => 0.3,
            16..=30 => 0.5,
            31..=60 => 0.7,
            _ => 0.9,
        };

        let task_type = if is_sensitive {
            "sensitive_query".to_string()
        } else if needs_tool_calls {
            "tool_call".to_string()
        } else if is_multi_turn {
            "multi_turn".to_string()
        } else if word_count < 10 {
            "short_query".to_string()
        } else if word_count < 30 {
            "medium_query".to_string()
        } else {
            "long_query".to_string()
        };

        Self {
            is_sensitive,
            needs_tool_calls,
            is_multi_turn,
            complexity,
            task_type,
        }
    }
}

static SENSITIVITY_PATTERNS: &[&str] = &[
    "ssn",
    "social security",
    "passport",
    "password",
    "api key",
    "secret",
    "token",
    "credential",
    "credit card",
    "bank account",
    "diagnosis",
    "prescription",
    "medical record",
    "confidential",
    "classified",
];

static TOOL_CALL_PATTERNS: &[&str] = &[
    "search memory",
    "find memory",
    "lookup",
    "query memory",
    "recall",
    "use tool",
    "call function",
    "invoke api",
];

static MULTI_TURN_PATTERNS: &[&str] = &[
    "then",
    "after that",
    "next",
    "subsequently",
    "finally",
    "step 1",
    "step 2",
    "phase 1",
    "phase 2",
];

// ── Search Configuration ──────────────────────────────────────────────

/// Configuration for conversational memory search.
#[derive(Debug, Clone)]
pub struct ConversationalConfig {
    /// Maximum number of cached queries (LRU eviction).
    pub cache_size: usize,
    /// Maximum snippet length in characters.
    pub snippet_length: usize,
    /// Default number of results to return.
    pub default_limit: usize,
    /// Whether to enable query caching.
    pub enable_cache: bool,
    /// Whether to exclude `is_private` memories from results. Default on —
    /// MCP chat must not surface private memories.
    pub exclude_private: bool,
}

impl Default for ConversationalConfig {
    fn default() -> Self {
        Self {
            cache_size: 128,
            snippet_length: 200,
            default_limit: 10,
            enable_cache: true,
            exclude_private: true,
        }
    }
}

impl ConversationalConfig {
    /// Create config from environment variables.
    #[must_use]
    pub fn from_env() -> Self {
        let mut config = Self::default();
        if let Ok(v) = std::env::var("WM_CONVERSATIONAL_CACHE_SIZE") {
            if let Ok(n) = v.parse::<usize>() {
                config.cache_size = n;
            }
        }
        if let Ok(v) = std::env::var("WM_CONVERSATIONAL_SNIPPET_LEN") {
            if let Ok(n) = v.parse::<usize>() {
                config.snippet_length = n;
            }
        }
        if let Ok(v) = std::env::var("WM_CONVERSATIONAL_DEFAULT_LIMIT") {
            if let Ok(n) = v.parse::<usize>() {
                config.default_limit = n;
            }
        }
        config
    }
}

// ── Search Result ─────────────────────────────────────────────────────

/// A conversational search result with snippet and metadata.
#[derive(Debug, Clone)]
pub struct ConversationalResult {
    /// Memory UUID.
    pub memory_id: Uuid,
    /// Galaxy the memory belongs to.
    pub galaxy: Galaxy,
    /// Fused relevance score (0.0–1.0).
    pub score: f32,
    /// Content snippet (truncated to `snippet_length`).
    pub snippet: String,
    /// Memory tags.
    pub tags: Vec<String>,
    /// Whether this result came from cache.
    pub from_cache: bool,
    /// Query latency in microseconds.
    pub latency_us: u64,
}

// ── Cache Entry ───────────────────────────────────────────────────────

#[derive(Debug, Clone)]
struct CacheEntry {
    results: Vec<RecallResult>,
    timestamp: Instant,
    hit_count: u32,
}

// ── Performance Metrics ───────────────────────────────────────────────

/// Performance metrics for conversational search.
#[derive(Debug, Clone, Default)]
pub struct SearchMetrics {
    /// Total number of queries.
    pub total_queries: u64,
    /// Number of cache hits.
    pub cache_hits: u64,
    /// Number of cache misses.
    pub cache_misses: u64,
    /// Total query latency in microseconds.
    pub total_latency_us: u64,
    /// Minimum query latency in microseconds.
    pub min_latency_us: u64,
    /// Maximum query latency in microseconds.
    pub max_latency_us: u64,
}

impl SearchMetrics {
    /// Cache hit rate (0.0–1.0).
    #[must_use]
    pub fn cache_hit_rate(&self) -> f64 {
        let total = self.cache_hits + self.cache_misses;
        if total == 0 {
            0.0
        } else {
            self.cache_hits as f64 / total as f64
        }
    }

    /// Average latency in microseconds.
    #[must_use]
    pub fn avg_latency_us(&self) -> f64 {
        if self.total_queries == 0 {
            0.0
        } else {
            self.total_latency_us as f64 / self.total_queries as f64
        }
    }

    /// Average latency in milliseconds.
    #[must_use]
    pub fn avg_latency_ms(&self) -> f64 {
        self.avg_latency_us() / 1000.0
    }

    /// Whether the sub-50ms target is being met on average.
    ///
    /// Returns `false` when no queries have been recorded.
    #[must_use]
    pub fn meets_latency_target(&self) -> bool {
        self.total_queries > 0 && self.avg_latency_ms() < 50.0
    }
}

// ── Conversational Memory Search ──────────────────────────────────────

/// User-facing conversational memory search engine.
///
/// Wraps [`RecallEngine`] with query classification, LRU caching,
/// and performance metrics for sub-50ms search.
pub struct ConversationalSearch {
    recall: Arc<RecallEngine>,
    config: ConversationalConfig,
    cache: Mutex<HashMap<String, CacheEntry>>,
    cache_order: Mutex<Vec<String>>,
    metrics: Mutex<SearchMetrics>,
}

impl ConversationalSearch {
    /// Create a new conversational search engine.
    #[must_use]
    pub fn new(recall: Arc<RecallEngine>, config: ConversationalConfig) -> Self {
        Self {
            recall,
            config,
            cache: Mutex::new(HashMap::new()),
            cache_order: Mutex::new(Vec::new()),
            metrics: Mutex::new(SearchMetrics::default()),
        }
    }

    /// Create with default configuration.
    #[must_use]
    pub fn with_defaults(recall: Arc<RecallEngine>) -> Self {
        Self::new(recall, ConversationalConfig::default())
    }

    /// Search for memories matching the query.
    ///
    /// Returns ranked results with snippets. Uses cache when available.
    #[must_use]
    pub fn search(&self, query: &str, limit: Option<usize>) -> Vec<ConversationalResult> {
        self.search_in_galaxy(query, limit, None)
    }

    /// Search within a specific galaxy.
    #[must_use]
    pub fn search_in_galaxy(
        &self,
        query: &str,
        limit: Option<usize>,
        galaxy: Option<Galaxy>,
    ) -> Vec<ConversationalResult> {
        let start = Instant::now();
        let effective_limit = limit.unwrap_or(self.config.default_limit);

        // Build cache key
        let cache_key = format!("{query}|{galaxy:?}|{effective_limit}");

        // Check cache
        let from_cache = self.config.enable_cache && {
            let Ok(mut cache) = self.cache.lock() else {
                return Vec::new();
            };
            if let Some(entry) = cache.get_mut(&cache_key) {
                entry.hit_count += 1;
                entry.timestamp = Instant::now();
                true
            } else {
                false
            }
        };

        let results = if from_cache {
            let Ok(cache) = self.cache.lock() else {
                return Vec::new();
            };
            cache
                .get(&cache_key)
                .map(|e| e.results.clone())
                .unwrap_or_default()
        } else {
            // Cache miss — perform actual search
            let recall_results = self.recall.hybrid_search(query, effective_limit, galaxy);

            // Store in cache
            if self.config.enable_cache {
                let entry = CacheEntry {
                    results: recall_results.clone(),
                    timestamp: Instant::now(),
                    hit_count: 1,
                };
                {
                    let Ok(mut cache) = self.cache.lock() else {
                        return Vec::new();
                    };
                    let Ok(mut order) = self.cache_order.lock() else {
                        return Vec::new();
                    };

                    // Evict LRU if at capacity
                    while order.len() >= self.config.cache_size {
                        if let Some(oldest) = order.first() {
                            cache.remove(oldest);
                            order.remove(0);
                        } else {
                            break;
                        }
                    }

                    cache.insert(cache_key.clone(), entry);
                    order.push(cache_key);
                }
            }

            // Record cache miss
            if self.config.enable_cache {
                if let Ok(mut metrics) = self.metrics.lock() {
                    metrics.cache_misses += 1;
                }
            }

            recall_results
        };

        // Record cache hit
        if from_cache {
            if let Ok(mut metrics) = self.metrics.lock() {
                metrics.cache_hits += 1;
            }
        }

        let latency_us = start.elapsed().as_micros() as u64;

        // Update metrics
        {
            let Ok(mut metrics) = self.metrics.lock() else {
                return Vec::new();
            };
            metrics.total_queries += 1;
            metrics.total_latency_us += latency_us;
            if metrics.min_latency_us == 0 || latency_us < metrics.min_latency_us {
                metrics.min_latency_us = latency_us;
            }
            if latency_us > metrics.max_latency_us {
                metrics.max_latency_us = latency_us;
            }
        }

        // Convert to conversational results. Private memories are excluded
        // when `exclude_private` is set (default) — MCP chat must not surface
        // them.
        results
            .into_iter()
            .filter(|r| {
                !self.config.exclude_private || !self.recall.is_private(r.memory_id, r.galaxy)
            })
            .map(|r| {
                let snippet = if r.content.len() > self.config.snippet_length {
                    format!("{}...", &r.content[..self.config.snippet_length])
                } else {
                    r.content.clone()
                };

                ConversationalResult {
                    memory_id: r.memory_id,
                    galaxy: r.galaxy,
                    score: r.score,
                    snippet,
                    tags: Vec::new(),
                    from_cache,
                    latency_us,
                }
            })
            .collect()
    }

    /// Classify a query without performing search.
    #[must_use]
    pub fn classify(&self, query: &str) -> QueryClassification {
        QueryClassification::classify(query)
    }

    /// Get current performance metrics.
    #[must_use]
    pub fn metrics(&self) -> SearchMetrics {
        self.metrics.lock().map(|m| m.clone()).unwrap_or_default()
    }

    /// Clear the query cache.
    pub fn clear_cache(&self) {
        if let Ok(mut c) = self.cache.lock() {
            c.clear();
        }
        if let Ok(mut c) = self.cache_order.lock() {
            c.clear();
        }
    }

    /// Get the number of cached queries.
    #[must_use]
    pub fn cache_len(&self) -> usize {
        self.cache.lock().map_or(0, |c| c.len())
    }

    /// Get the underlying recall engine.
    #[must_use]
    pub fn recall(&self) -> &RecallEngine {
        &self.recall
    }

    /// Get the configuration.
    #[must_use]
    pub const fn config(&self) -> &ConversationalConfig {
        &self.config
    }

    /// Store a memory with auto-embedding (delegates to RecallEngine).
    pub fn store(&self, galaxy: Galaxy, memory: &crate::Memory) -> Result<()> {
        self.recall.store_with_embedding(galaxy, memory)
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::embedder::{Embedder, StubEmbedder};
    use crate::memory::Memory;
    use crate::recall::{RecallConfig, RecallEngine};
    use crate::search::SearchEngine;
    use crate::store::MemoryStore;
    use crate::vector::VectorStore;
    use std::sync::Arc;
    use tempfile::tempdir;

    fn setup() -> (tempfile::TempDir, ConversationalSearch) {
        let tmp = tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tantivy_path = tmp.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy_path).unwrap());
        let vector_store = VectorStore::new();
        let embedder: Arc<dyn Embedder> = Arc::new(StubEmbedder::new(384));
        let recall = RecallEngine::new(
            store,
            search,
            vector_store,
            embedder,
            RecallConfig::default(),
        )
        .unwrap();
        let conv = ConversationalSearch::with_defaults(Arc::new(recall));
        (tmp, conv)
    }

    // ── QueryClassification tests ──────────────────────────────────────

    #[test]
    fn classify_simple_query() {
        let c = QueryClassification::classify("hello world");
        assert!(!c.is_sensitive);
        assert!(!c.needs_tool_calls);
        assert!(!c.is_multi_turn);
        assert!(c.complexity < 0.5);
    }

    #[test]
    fn classify_sensitive_query() {
        let c = QueryClassification::classify("what is my password?");
        assert!(c.is_sensitive);
        assert_eq!(c.task_type, "sensitive_query");
    }

    #[test]
    fn classify_tool_call_query() {
        let c = QueryClassification::classify("search memory for rust patterns");
        assert!(c.needs_tool_calls);
    }

    #[test]
    fn classify_multi_turn_query() {
        let c = QueryClassification::classify("first do X then do Y and finally do Z");
        assert!(c.is_multi_turn);
    }

    #[test]
    fn classify_complex_query() {
        let c = QueryClassification::classify(
            "analyze the complex interdisciplinary trade-offs in this nuanced scenario \
             with multiple competing factors and conditional dependencies that require \
             careful consideration of various architectural patterns and their implications \
             for distributed systems design and implementation strategy",
        );
        assert!(c.complexity >= 0.5);
    }

    // ── ConversationalConfig tests ─────────────────────────────────────

    #[test]
    fn config_defaults() {
        let config = ConversationalConfig::default();
        assert_eq!(config.cache_size, 128);
        assert_eq!(config.snippet_length, 200);
        assert_eq!(config.default_limit, 10);
        assert!(config.enable_cache);
    }

    // ── SearchMetrics tests ────────────────────────────────────────────

    #[test]
    fn metrics_empty_defaults() {
        let metrics = SearchMetrics::default();
        assert_eq!(metrics.cache_hit_rate(), 0.0);
        assert_eq!(metrics.avg_latency_us(), 0.0);
        assert!(!metrics.meets_latency_target());
    }

    #[test]
    fn metrics_hit_rate_calculation() {
        let metrics = SearchMetrics {
            total_queries: 10,
            cache_hits: 7,
            cache_misses: 3,
            ..Default::default()
        };
        assert!((metrics.cache_hit_rate() - 0.7).abs() < 0.01);
    }

    #[test]
    fn metrics_avg_latency() {
        let metrics = SearchMetrics {
            total_queries: 5,
            total_latency_us: 250_000,
            ..Default::default()
        };
        assert_eq!(metrics.avg_latency_us(), 50_000.0);
        assert_eq!(metrics.avg_latency_ms(), 50.0);
    }

    // ── ConversationalSearch integration tests ─────────────────────────

    #[test]
    fn search_empty_returns_empty() {
        let (_tmp, conv) = setup();
        let results = conv.search("anything", None);
        assert!(results.is_empty());
    }

    #[test]
    fn search_after_store_finds_results() {
        let (_tmp, conv) = setup();

        let mem = Memory::new(
            Galaxy::Codex,
            "Rust programming language is fast and safe".into(),
        )
        .with_importance(0.8)
        .with_tags(vec!["rust".into(), "programming".into()]);
        conv.store(Galaxy::Codex, &mem).unwrap();

        let results = conv.search("rust", None);
        assert!(!results.is_empty());
        assert!(results[0].snippet.contains("Rust"));
    }

    #[test]
    fn search_snippet_truncation() {
        let (_tmp, conv) = setup();

        let long_content = "A".repeat(500);
        let mem = Memory::new(Galaxy::Codex, long_content);
        conv.store(Galaxy::Codex, &mem).unwrap();

        let results = conv.search(&"A".repeat(500), None);
        if !results.is_empty() {
            assert!(results[0].snippet.len() <= 203); // 200 + "..."
        }
    }

    #[test]
    fn search_cache_hit_on_repeat_query() {
        let (_tmp, conv) = setup();

        let mem = Memory::new(Galaxy::Codex, "rust programming basics".into());
        conv.store(Galaxy::Codex, &mem).unwrap();

        // First query — cache miss
        let results1 = conv.search("rust", None);
        assert!(!results1.is_empty());
        assert!(!results1[0].from_cache);

        // Second identical query — cache hit
        let results2 = conv.search("rust", None);
        assert!(!results2.is_empty());
        assert!(results2[0].from_cache);

        // Metrics should show 1 hit, 1 miss
        let metrics = conv.metrics();
        assert_eq!(metrics.cache_hits, 1);
        assert_eq!(metrics.cache_misses, 1);
    }

    #[test]
    fn search_galaxy_filter() {
        let (_tmp, conv) = setup();

        let mem_codex = Memory::new(Galaxy::Codex, "codex memory about rust".into());
        let mem_research = Memory::new(Galaxy::Research, "research memory about rust".into());

        conv.store(Galaxy::Codex, &mem_codex).unwrap();
        conv.store(Galaxy::Research, &mem_research).unwrap();

        let results = conv.search_in_galaxy("rust", None, Some(Galaxy::Codex));
        assert!(!results.is_empty());
        assert!(results.iter().all(|r| r.galaxy == Galaxy::Codex));
    }

    #[test]
    fn search_custom_limit() {
        let (_tmp, conv) = setup();

        for i in 0..5 {
            let mem = Memory::new(Galaxy::Codex, format!("rust memory number {i}"));
            conv.store(Galaxy::Codex, &mem).unwrap();
        }

        let results = conv.search("rust", Some(2));
        assert!(results.len() <= 2);
    }

    #[test]
    fn classify_without_search() {
        let (_tmp, conv) = setup();
        let classification = conv.classify("what is my password?");
        assert!(classification.is_sensitive);
    }

    #[test]
    fn cache_clear() {
        let (_tmp, conv) = setup();

        let mem = Memory::new(Galaxy::Codex, "rust memory".into());
        conv.store(Galaxy::Codex, &mem).unwrap();

        // Populate cache
        let _ = conv.search("rust", None);
        assert_eq!(conv.cache_len(), 1);

        // Clear cache
        conv.clear_cache();
        assert_eq!(conv.cache_len(), 0);
    }

    #[test]
    fn cache_lru_eviction() {
        let (_tmp, conv) = setup();

        // Use a small cache config
        let _recall = conv.recall();
        let small_config = ConversationalConfig {
            cache_size: 3,
            ..Default::default()
        };
        let conv_small = ConversationalSearch::new(
            Arc::new(
                RecallEngine::new(
                    Arc::new(
                        MemoryStore::open_default(tempfile::tempdir().unwrap().path()).unwrap(),
                    ),
                    Arc::new(SearchEngine::open(tempfile::tempdir().unwrap().path()).unwrap()),
                    VectorStore::new(),
                    Arc::new(StubEmbedder::new(384)),
                    RecallConfig::default(),
                )
                .unwrap(),
            ),
            small_config,
        );

        // Perform 5 different searches to trigger eviction
        for i in 0..5 {
            let _ = conv_small.search(&format!("query{i}"), None);
        }

        // Cache should not exceed size limit
        assert!(conv_small.cache_len() <= 3);
    }

    #[test]
    fn metrics_track_latency() {
        let (_tmp, conv) = setup();

        let mem = Memory::new(Galaxy::Codex, "rust memory".into());
        conv.store(Galaxy::Codex, &mem).unwrap();

        let _ = conv.search("rust", None);

        let metrics = conv.metrics();
        assert!(metrics.total_queries > 0);
        assert!(metrics.total_latency_us > 0);
        assert!(metrics.max_latency_us >= metrics.min_latency_us);
    }

    #[test]
    fn store_delegates_to_recall() {
        let (_tmp, conv) = setup();

        let mem = Memory::new(Galaxy::Codex, "test content for delegation".into());
        conv.store(Galaxy::Codex, &mem).unwrap();

        // Verify it was stored by searching
        let results = conv.search("test content for delegation", None);
        assert!(!results.is_empty());
    }

    #[test]
    fn search_with_disabled_cache() {
        let tmp = tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        let tantivy_path = tmp.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_path).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy_path).unwrap());
        let vector_store = VectorStore::new();
        let embedder: Arc<dyn Embedder> = Arc::new(StubEmbedder::new(384));
        let recall = RecallEngine::new(
            store,
            search,
            vector_store,
            embedder,
            RecallConfig::default(),
        )
        .unwrap();

        let config = ConversationalConfig {
            enable_cache: false,
            ..Default::default()
        };
        let conv = ConversationalSearch::new(Arc::new(recall), config);

        let mem = Memory::new(Galaxy::Codex, "rust memory".into());
        conv.store(Galaxy::Codex, &mem).unwrap();

        let _ = conv.search("rust", None);
        let _ = conv.search("rust", None);

        // Cache should be empty
        assert_eq!(conv.cache_len(), 0);

        let metrics = conv.metrics();
        assert_eq!(metrics.cache_hits, 0);
        assert_eq!(metrics.cache_misses, 0);
    }
}
