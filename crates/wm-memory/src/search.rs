//! Search engine — Tantivy full-text search.
//!
//! Provides BM25-scored full-text search over memory content.
//! Index is stored alongside the LMDB store in a separate directory.
//!
//! Recall-quality hygiene (see `docs/TANTIVY_RECALL_QUALITY_FIX.md`):
//! - Queries are stripped of common stopwords before parsing.
//! - Terms are only quoted when they contain reserved query syntax
//!   (plain terms — including hyphenated compounds — pass through so the
//!   tokenizer can split them into phrase matches).
//! - Content is sanitized at index time (binary/garbage content is skipped).
//! - Results are filtered by optional absolute and/or relative score floors,
//!   and output content is scrubbed of control characters.

use crate::MemoryId;
use serde::{Deserialize, Serialize};
use wm_core::{CoreError, Galaxy, Result};

use std::path::Path;
use std::sync::Mutex;
use std::sync::atomic::{AtomicU64, Ordering};
use tantivy::{
    Index, IndexReader, IndexWriter, ReloadPolicy,
    collector::TopDocs,
    doc,
    query::QueryParser,
    schema::{
        Field, STORED, STRING, Schema, TantivyDocument, TextFieldIndexing, TextOptions, Value,
    },
};

/// Maximum content length (in chars) indexed into Tantivy.
pub const MAX_INDEX_CONTENT_LEN: usize = 8 * 1024;

/// Minimum printable-char ratio for content to be indexed (0.9 = max 10% garbage).
pub const MIN_PRINTABLE_RATIO: f32 = 0.9;

/// Common English stopwords stripped from queries before parsing.
///
/// Mirrors the client-side stopword list (Antigravity `wmMemory.ts`) so the
/// server and client agree on which tokens are meaningless for recall.
pub const STOPWORDS: &[&str] = &[
    "a",
    "about",
    "after",
    "again",
    "all",
    "also",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "before",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "might",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "shall",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "us",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
];

/// Search options controlling recall behavior.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct SearchOptions {
    /// Maximum number of results.
    pub limit: usize,
    /// Optional galaxy filter (matches the stored galaxy string).
    pub galaxy: Option<Galaxy>,
    /// Absolute BM25 score floor; hits scoring below are dropped.
    pub min_score: Option<f32>,
    /// Relative floor: hits scoring below `top_score * ratio` are dropped
    /// (e.g. `0.05` keeps only hits within 5% of the top result).
    pub relative_floor: Option<f32>,
    /// Use OR semantics instead of conjunction (deprecated — OR is now the
    /// default; this flag is kept for API compatibility but does not change
    /// behavior).
    pub relaxed: bool,
}

impl Default for SearchOptions {
    fn default() -> Self {
        Self {
            limit: 20,
            galaxy: None,
            min_score: None,
            relative_floor: None,
            relaxed: false,
        }
    }
}

/// Search result item.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SearchResult {
    /// Memory UUID (as string)
    pub memory_id: String,
    /// Galaxy name
    pub galaxy: String,
    /// Raw BM25 score
    pub score: f32,
    /// Score relative to the top hit (1.0 = top result, 0.0 = no results)
    pub normalized_score: f32,
    /// Content snippet (control characters scrubbed)
    pub content: String,
}

/// Tracked health of the Tantivy index relative to LMDB.
///
/// Because Tantivy indexing is best-effort (an indexing failure does not
/// roll back the LMDB write), the index can drift from the store. This
/// struct tracks successes and failures so `wm doctor` and `system.health`
/// can report degraded state instead of silently claiming healthy.
#[derive(Debug, Default)]
pub struct IndexHealth {
    /// Successful index/deindex operations since startup.
    pub successes: AtomicU64,
    /// Failed index/deindex operations since startup.
    pub failures: AtomicU64,
    /// Last error message (empty string if none).
    last_error: Mutex<String>,
}

impl IndexHealth {
    fn record_success(&self) {
        self.successes.fetch_add(1, Ordering::Relaxed);
    }

    fn record_failure(&self, err: &str) {
        self.failures.fetch_add(1, Ordering::Relaxed);
        if let Ok(mut guard) = self.last_error.lock() {
            *guard = err.to_string();
        }
    }

    /// Snapshot the health as a JSON value for tool output.
    #[must_use]
    pub fn snapshot(&self) -> serde_json::Value {
        let successes = self.successes.load(Ordering::Relaxed);
        let failures = self.failures.load(Ordering::Relaxed);
        let last_error = self
            .last_error
            .lock()
            .map(|g| g.clone())
            .unwrap_or_default();
        let degraded = failures > 0;
        serde_json::json!({
            "successes": successes,
            "failures": failures,
            "degraded": degraded,
            "last_error": if last_error.is_empty() { serde_json::Value::Null } else { serde_json::Value::String(last_error) },
        })
    }
}

/// The full-text search engine backed by Tantivy.
pub struct SearchEngine {
    index: Index,
    reader: IndexReader,
    writer: Mutex<Option<IndexWriter>>,
    field_id: Field,
    field_galaxy: Field,
    field_content: Field,
    field_tags: Field,
    field_timestamp: Field,
    /// Tracked index health — failures are recorded so callers can detect
    /// degraded state instead of silently reporting healthy.
    health: IndexHealth,
}

impl SearchEngine {
    /// Build the Tantivy schema for memory indexing.
    fn build_schema() -> (Schema, Field, Field, Field, Field, Field) {
        let mut schema_builder = Schema::builder();
        let field_id = schema_builder.add_text_field("memory_id", STRING | STORED);
        let field_galaxy = schema_builder.add_text_field("galaxy", STRING | STORED);
        // Use en_stem tokenizer for content and tags so that morphological
        // variants match (e.g. "graduate" ↔ "graduated", "degree" ↔ "degrees").
        let stem_indexing = TextFieldIndexing::default()
            .set_tokenizer("en_stem")
            .set_index_option(tantivy::schema::IndexRecordOption::WithFreqsAndPositions);
        let stem_text = TextOptions::default()
            .set_indexing_options(stem_indexing.clone())
            .set_stored();
        let stem_tags = TextOptions::default().set_indexing_options(stem_indexing);
        let field_content = schema_builder.add_text_field("content", stem_text);
        let field_tags = schema_builder.add_text_field("tags", stem_tags);
        let field_timestamp = schema_builder.add_i64_field("timestamp", STORED);
        let schema = schema_builder.build();
        (
            schema,
            field_id,
            field_galaxy,
            field_content,
            field_tags,
            field_timestamp,
        )
    }

    /// Create or open a search engine index at the given path.
    pub fn open(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref();
        let (schema, field_id, field_galaxy, field_content, field_tags, field_timestamp) =
            Self::build_schema();

        let directory = tantivy::directory::MmapDirectory::open(path)
            .map_err(|e| CoreError::Memory(format!("Tantivy open directory: {e}")))?;
        let index = Index::open_or_create(directory, schema)
            .map_err(|e| CoreError::Memory(format!("Tantivy open_or_create: {e}")))?;

        let reader = index
            .reader_builder()
            .reload_policy(ReloadPolicy::OnCommitWithDelay)
            .try_into()
            .map_err(|e| CoreError::Memory(format!("Tantivy reader: {e}")))?;

        let writer = index
            .writer(50_000_000)
            .map_err(|e| CoreError::Memory(format!("Tantivy writer: {e}")))?;

        Ok(Self {
            index,
            reader,
            writer: Mutex::new(Some(writer)),
            field_id,
            field_galaxy,
            field_content,
            field_tags,
            field_timestamp,
            health: IndexHealth::default(),
        })
    }

    /// Open the index in read-only mode: no writer is created, so no
    /// exclusive tantivy lock is taken. Multiple processes (e.g. Antigravity's
    /// proxy and an opencode MCP client) can share the store for searches;
    /// writes through this engine fail with a clear error.
    pub fn open_readonly(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref();
        let (schema, field_id, field_galaxy, field_content, field_tags, field_timestamp) =
            Self::build_schema();
        let directory = tantivy::directory::MmapDirectory::open(path)
            .map_err(|e| CoreError::Memory(format!("Tantivy open directory: {e}")))?;
        let index = Index::open_or_create(directory, schema)
            .map_err(|e| CoreError::Memory(format!("Tantivy open_or_create: {e}")))?;
        let reader = index
            .reader_builder()
            .reload_policy(ReloadPolicy::OnCommitWithDelay)
            .try_into()
            .map_err(|e| CoreError::Memory(format!("Tantivy reader: {e}")))?;
        Ok(Self {
            index,
            reader,
            writer: Mutex::new(None),
            field_id,
            field_galaxy,
            field_content,
            field_tags,
            field_timestamp,
            health: IndexHealth::default(),
        })
    }

    /// Returns a snapshot of index health (success/failure counts, degraded
    /// flag, last error).
    #[must_use]
    pub const fn health(&self) -> &IndexHealth {
        &self.health
    }

    /// Count the number of indexed documents for a specific galaxy.
    ///
    /// Used by consistency checks to compare Tantivy doc counts against
    /// LMDB memory counts. Returns 0 if the index is empty or the galaxy
    /// has no documents.
    pub fn count_docs_in_galaxy(&self, galaxy: &str) -> Result<usize> {
        let searcher = self.reader.searcher();
        let term = tantivy::Term::from_field_text(self.field_galaxy, galaxy);
        let query = tantivy::query::TermQuery::new(term, tantivy::schema::IndexRecordOption::Basic);
        let count = searcher
            .search(&query, &tantivy::collector::Count)
            .map_err(|e| CoreError::Memory(format!("Tantivy count_docs: {e}")))?;
        Ok(count)
    }

    /// True when the engine was opened read-only (no tantivy writer).
    pub fn is_readonly(&self) -> bool {
        self.writer.lock().map(|g| g.is_none()).unwrap_or(true)
    }

    /// Lock the shared writer for adding/removing documents.
    ///
    /// The writer is created at `open()` time and shared across all callers
    /// via a `Mutex`, preventing lock contention with Tantivy's single-writer model.
    /// In read-only mode this errors.
    pub fn writer(&self) -> Result<std::sync::MutexGuard<'_, Option<IndexWriter>>> {
        let guard = self
            .writer
            .lock()
            .map_err(|_| CoreError::Memory("Tantivy writer mutex poisoned".into()))?;
        if guard.is_none() {
            return Err(CoreError::Memory(
                "Tantivy writer unavailable: index opened read-only".into(),
            ));
        }
        Ok(guard)
    }

    /// Index a memory document.
    ///
    /// Content that is not clean text (binary garbage, low printable-char
    /// ratio, null bytes) is **skipped** at index time — no document is added
    /// and `Ok(())` is returned so callers can proceed. See
    /// [`sanitize_content_for_index`].
    pub fn add_document(
        &self,
        writer: &mut Option<IndexWriter>,
        memory_id: &str,
        galaxy: &str,
        content: &str,
        tags: &[String],
        timestamp: i64,
    ) -> Result<()> {
        let writer = writer.as_mut().ok_or_else(|| {
            CoreError::Memory("Tantivy writer unavailable: index opened read-only".into())
        })?;
        let Some(clean_content) = sanitize_content_for_index(content) else {
            tracing::debug!("Skipping index of memory {memory_id}: content failed sanitization");
            return Ok(());
        };
        let tags_str = tags.join(" ");
        let doc = doc!(
            self.field_id => memory_id,
            self.field_galaxy => galaxy,
            self.field_content => clean_content,
            self.field_tags => tags_str,
            self.field_timestamp => timestamp,
        );
        match writer.add_document(doc) {
            Ok(_) => {
                self.health.record_success();
                Ok(())
            }
            Err(e) => {
                let msg = format!("Tantivy add_document: {e}");
                self.health.record_failure(&msg);
                Err(CoreError::Memory(msg))
            }
        }
    }

    /// Delete documents by memory ID.
    pub fn delete_document(&self, writer: &mut Option<IndexWriter>, memory_id: &str) -> Result<()> {
        let writer = writer.as_mut().ok_or_else(|| {
            CoreError::Memory("Tantivy writer unavailable: index opened read-only".into())
        })?;
        let term = tantivy::Term::from_field_text(self.field_id, memory_id);
        writer.delete_term(term);
        Ok(())
    }

    /// Delete every document belonging to a galaxy.
    ///
    /// Used by filtered reindexing so `--galaxy codex` removes only codex
    /// documents instead of wiping the entire index.
    pub fn delete_by_galaxy(&self, writer: &mut Option<IndexWriter>, galaxy: &str) -> Result<()> {
        let writer = writer.as_mut().ok_or_else(|| {
            CoreError::Memory("Tantivy writer unavailable: index opened read-only".into())
        })?;
        let term = tantivy::Term::from_field_text(self.field_galaxy, galaxy);
        writer.delete_term(term);
        Ok(())
    }

    /// Commit pending index changes and reload the reader.
    pub fn commit(&self, writer: &mut Option<IndexWriter>) -> Result<()> {
        let writer = writer.as_mut().ok_or_else(|| {
            CoreError::Memory("Tantivy writer unavailable: index opened read-only".into())
        })?;
        writer
            .commit()
            .map_err(|e| CoreError::Memory(format!("Tantivy commit: {e}")))?;
        self.reader
            .reload()
            .map_err(|e| CoreError::Memory(format!("Tantivy reload: {e}")))?;
        Ok(())
    }

    /// Search for memories matching the query text.
    /// Returns results sorted by BM25 score (descending).
    ///
    /// The query is stripped of stopwords and sanitized to prevent Tantivy
    /// query syntax injection.
    pub fn search(&self, query: &str, limit: usize) -> Result<Vec<SearchResult>> {
        let opts = SearchOptions {
            limit,
            ..SearchOptions::default()
        };
        self.search_opt(query, &opts)
    }

    /// Search for memories matching the query, optionally filtered by galaxy.
    ///
    /// The query is stripped of stopwords and sanitized to escape Tantivy
    /// special characters (+, -, *, "", field syntax, boolean operators) that
    /// could be used for query injection.
    pub fn search_in_galaxy(
        &self,
        query: &str,
        galaxy: Option<Galaxy>,
        limit: usize,
    ) -> Result<Vec<SearchResult>> {
        let opts = SearchOptions {
            limit,
            galaxy,
            ..SearchOptions::default()
        };
        self.search_opt(query, &opts)
    }

    /// Search with full recall-quality options (stopword stripping, score
    /// thresholds, token-coverage filtering, galaxy filter).
    ///
    /// Pipeline:
    /// 1. `strip_stopwords` — common English stopwords are removed.
    /// 2. `sanitize_tantivy_query` — reserved query syntax is neutralized;
    ///    plain terms (incl. hyphenated compounds) pass through so the
    ///    tokenizer can split them into phrase matches.
    /// 3. OR query across `content` + `tags` (broader recall than
    ///    conjunction, filtered by token-coverage in step 5).
    /// 4. Hits below `min_score` (absolute) or `relative_floor * top_score`
    ///    are dropped.
    /// 5. Token-coverage floor: for queries with ≥ 3 terms, at least 2
    ///    must appear in the content (stemming-aware).  Documents that
    ///    pass the floor receive a coverage-ratio score boost.
    /// 6. Output content is scrubbed of control characters.
    pub fn search_opt(&self, query: &str, opts: &SearchOptions) -> Result<Vec<SearchResult>> {
        let stripped = strip_stopwords(query);
        let sanitized = sanitize_tantivy_query(&stripped);
        if sanitized.trim().is_empty() {
            return Ok(Vec::new());
        }

        let searcher = self.reader.searcher();

        // Always use OR semantics.  The token-coverage floor below filters
        // single-term noise that OR would otherwise let through.
        let query_parser =
            QueryParser::for_index(&self.index, vec![self.field_content, self.field_tags]);

        let parsed = query_parser
            .parse_query(&sanitized)
            .map_err(|e| CoreError::Memory(format!("Tantivy parse_query: {e}")))?;

        let collector = TopDocs::with_limit(opts.limit).order_by_score();

        let top_docs = searcher
            .search(&parsed, &collector)
            .map_err(|e| CoreError::Memory(format!("Tantivy search: {e}")))?;

        let top_score = top_docs.first().map_or(0.0, |(score, _)| *score);
        let absolute_floor = opts.min_score.unwrap_or(f32::MIN);
        let relative_floor = opts
            .relative_floor
            .map_or(f32::MIN, |ratio| top_score * ratio);

        // Token-coverage floor: with OR semantics a document matching any
        // single common term would otherwise qualify.  For queries with
        // ≥ 3 terms, require at least 2 to appear in the content.
        let query_tokens = query_stem_tokens(&stripped);
        let coverage_floor = if query_tokens.len() >= 3 { 2 } else { 1 };

        let mut results = Vec::new();
        for (score, doc_address) in top_docs {
            // Score floors: reject weak matches before touching the document.
            if score < absolute_floor || score < relative_floor {
                continue;
            }

            let doc: TantivyDocument = searcher
                .doc(doc_address)
                .map_err(|e| CoreError::Memory(format!("Tantivy get doc: {e}")))?;

            let memory_id = doc
                .get_first(self.field_id)
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();

            let doc_galaxy = doc
                .get_first(self.field_galaxy)
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();

            if let Some(g) = opts.galaxy {
                if doc_galaxy != g.db_name() {
                    continue;
                }
            }

            let content = doc
                .get_first(self.field_content)
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();

            if coverage_floor > 1 {
                let hits = count_token_hits(&content, &stripped);
                if hits < coverage_floor {
                    continue;
                }
            }

            // Coverage-ratio boost: documents covering more query tokens
            // are more relevant.  Boost = 1 + 0.1 * (hits / total).
            let boosted_score = if query_tokens.is_empty() {
                score
            } else {
                let hits = count_token_hits(&content, &stripped);
                let ratio = hits as f32 / query_tokens.len() as f32;
                score * 0.1f32.mul_add(ratio, 1.0)
            };

            results.push(SearchResult {
                memory_id,
                galaxy: doc_galaxy,
                score: boosted_score,
                normalized_score: 0.0, // set after re-sort
                content: scrub_text(&content),
            });
        }

        // Re-sort by boosted score (coverage boost may have re-ordered).
        results.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        // Normalize relative to the top boosted score.
        let top_boosted = results.first().map_or(0.0, |r| r.score);
        for r in &mut results {
            r.normalized_score = if top_boosted > 0.0 {
                r.score / top_boosted
            } else {
                0.0
            };
        }

        Ok(results)
    }

    /// Search and return memory IDs only (for integration with `MemoryStore`).
    pub fn search_ids(&self, query: &str, limit: usize) -> Result<Vec<MemoryId>> {
        let results = self.search(query, limit)?;
        Ok(results
            .into_iter()
            .filter_map(|r| uuid::Uuid::parse_str(&r.memory_id).ok())
            .collect())
    }
}

/// Sanitize a user-provided query string for Tantivy's query parser.
///
/// Tantivy's query parser supports special syntax that could be abused:
/// - `*` wildcard matches all terms (DoS)
/// - `+`, `-`, `NOT`, `OR`, `AND` boolean operators
/// - `"phrase"` exact phrase queries
/// - `field:value` field-scoped queries
/// - `(`, `)` grouping
/// - `\` escape character
/// - `:` field separator
///
/// Terms are only wrapped in double quotes when they contain reserved syntax
/// (or are uppercase boolean operators). Plain terms — including hyphenated
/// compounds like `antigravity-project-test` — pass through unquoted so the
/// tokenizer can split them into phrase matches. Terms without any
/// alphanumeric characters are dropped entirely.
#[must_use]
pub fn sanitize_tantivy_query(input: &str) -> String {
    // If empty, return as-is
    if input.trim().is_empty() {
        return String::new();
    }

    input
        .split_whitespace()
        .filter(|term| term.chars().any(char::is_alphanumeric))
        .map(|term| {
            if term_needs_quoting(term) {
                // Escape any embedded double quotes
                let escaped = term.replace('"', "\\\"");
                format!("\"{escaped}\"")
            } else {
                term.to_string()
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

/// Whether a query term needs quoting to neutralize Tantivy query syntax.
#[must_use]
fn term_needs_quoting(term: &str) -> bool {
    if term.starts_with('+') || term.starts_with('-') || term.starts_with('!') {
        return true;
    }
    if term == "AND" || term == "OR" || term == "NOT" {
        return true;
    }
    if term.contains("&&") || term.contains("||") {
        return true;
    }
    term.chars().any(|c| {
        matches!(
            c,
            '(' | ')' | '{' | '}' | '[' | ']' | '^' | '"' | '~' | '*' | '?' | ':' | '\\' | '/'
        )
    })
}

/// Strip common English stopwords from a query string.
///
/// Tokens are compared case-insensitively against [`STOPWORDS`].
#[must_use]
pub fn strip_stopwords(query: &str) -> String {
    query
        .split_whitespace()
        .filter(|term| !STOPWORDS.contains(&term.to_lowercase().as_str()))
        .collect::<Vec<_>>()
        .join(" ")
}

/// Unique lowercase stemmed tokens of a stopword-stripped query.
/// Uses [`simple_stem`] so that coverage matching aligns with the en_stem
/// tokenizer used at index time.
#[must_use]
fn query_stem_tokens(stripped_query: &str) -> Vec<String> {
    stem_tokens(stripped_query)
}

/// Normalize text into the same punctuation-delimited tokens on both sides
/// of the coverage comparison. This keeps possessives and hyphenated terms
/// from becoming query-only tokens or standalone one-character fragments.
#[must_use]
fn stem_tokens(text: &str) -> Vec<String> {
    let mut tokens: Vec<String> = Vec::new();
    for term in text
        .split(|c: char| !c.is_alphanumeric())
        .filter(|term| term.len() > 1)
    {
        let stemmed = simple_stem(&term.to_lowercase());
        if !tokens.contains(&stemmed) {
            tokens.push(stemmed);
        }
    }
    tokens
}

/// Lightweight suffix-stripping stemmer that approximates the Porter stemmer
/// used by Tantivy's `en_stem` tokenizer.  Handles the common English
/// inflections (-s, -es, -ed, -ing, -ly, -ies, -ied) without pulling in a
/// full stemming crate.  This is intentionally conservative — false
/// negatives (under-stemming) only make coverage stricter, never looser.
#[must_use]
fn simple_stem(word: &str) -> String {
    if word.len() <= 3 {
        return word.to_string();
    }
    // Order matters: check longer suffixes first.
    for suffix in ["ies", "ied", "ing", "edly", "ed", "ly", "es", "s"] {
        if let Some(stem) = word.strip_suffix(suffix) {
            // "ies" / "ied" → restore "y" (stories → story, carried → carry)
            if suffix == "ies" || suffix == "ied" {
                return format!("{stem}y");
            }
            // Don't produce a 1-char stem ("is" → "i")
            if stem.len() >= 2 {
                return stem.to_string();
            }
        }
    }
    word.to_string()
}

/// Count how many query tokens (after stemming) appear as whole words in the
/// content.  Uses [`simple_stem`] on both sides so that "graduate" matches
/// "graduated", mirroring the en_stem tokenizer used at index time.
#[must_use]
fn count_token_hits(content: &str, stripped_query: &str) -> usize {
    let query_tokens = query_stem_tokens(stripped_query);
    if query_tokens.is_empty() {
        return 0;
    }
    let content_stems: std::collections::HashSet<String> =
        stem_tokens(content).into_iter().collect();
    query_tokens
        .iter()
        .filter(|t| content_stems.contains(*t))
        .count()
}

/// Prepare content for indexing.
///
/// Returns `None` when the content is not clean text and must be skipped:
/// - empty / whitespace-only content
/// - contains a null byte (binary serialization artifact)
/// - printable-char ratio below [`MIN_PRINTABLE_RATIO`]
///
/// Otherwise returns the content scrubbed of control characters and capped
/// at [`MAX_INDEX_CONTENT_LEN`] chars.
#[must_use]
pub fn sanitize_content_for_index(content: &str) -> Option<String> {
    if content.trim().is_empty() {
        return None;
    }
    if content.as_bytes().contains(&0) {
        return None;
    }

    let total = content.chars().count();
    if total == 0 {
        return None;
    }
    let printable = content.chars().filter(|c| !c.is_control()).count();
    if (printable as f32 / total as f32) < MIN_PRINTABLE_RATIO {
        return None;
    }

    let cleaned = scrub_text(content);
    let capped: String = cleaned.chars().take(MAX_INDEX_CONTENT_LEN).collect();
    if capped.trim().is_empty() {
        None
    } else {
        Some(capped)
    }
}

/// Scrub text for output: replace control characters (except newline, tab,
/// carriage return) with a space, and cap the length at
/// [`MAX_INDEX_CONTENT_LEN`].
#[must_use]
pub fn scrub_text(content: &str) -> String {
    let mut out = String::with_capacity(content.len().min(MAX_INDEX_CONTENT_LEN));
    for c in content.chars().take(MAX_INDEX_CONTENT_LEN) {
        if c.is_control() && c != '\n' && c != '\t' && c != '\r' {
            out.push(' ');
        } else {
            out.push(c);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn open_engine() -> (tempfile::TempDir, SearchEngine) {
        let tmp = tempdir().unwrap();
        let engine = SearchEngine::open(tmp.path()).unwrap();
        (tmp, engine)
    }

    #[test]
    fn index_and_search_basic() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "The Rust programming language is fast and safe",
                &["rust".into(), "programming".into()],
                1700000000,
            )
            .unwrap();
        engine
            .add_document(
                &mut writer,
                "22222222-2222-2222-2222-222222222222",
                "codex",
                "Python is great for data science",
                &["python".into(), "data".into()],
                1700000001,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        let results = engine.search("rust", 10).unwrap();
        assert!(!results.is_empty());
        assert_eq!(results[0].memory_id, "11111111-1111-1111-1111-111111111111");
    }

    #[test]
    fn search_by_tag() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "memory about systems",
                &["rust".into()],
                1700000000,
            )
            .unwrap();
        engine
            .add_document(
                &mut writer,
                "22222222-2222-2222-2222-222222222222",
                "codex",
                "memory about cooking",
                &["food".into()],
                1700000001,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        let results = engine.search("rust", 10).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].memory_id, "11111111-1111-1111-1111-111111111111");
    }

    #[test]
    fn search_filtered_by_galaxy() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "important knowledge",
                &[],
                1700000000,
            )
            .unwrap();
        engine
            .add_document(
                &mut writer,
                "22222222-2222-2222-2222-222222222222",
                "research",
                "important findings",
                &[],
                1700000001,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        let results = engine
            .search_in_galaxy("important", Some(Galaxy::Codex), 10)
            .unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].galaxy, "codex");
    }

    #[test]
    fn delete_document_from_index() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "deletable content",
                &[],
                1700000000,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        let results = engine.search("deletable", 10).unwrap();
        assert_eq!(results.len(), 1);

        engine
            .delete_document(&mut writer, "11111111-1111-1111-1111-111111111111")
            .unwrap();
        engine.commit(&mut writer).unwrap();

        let results = engine.search("deletable", 10).unwrap();
        assert_eq!(results.len(), 0);
    }

    #[test]
    fn search_empty_index() {
        let (_tmp, engine) = open_engine();
        let results = engine.search("anything", 10).unwrap();
        assert!(results.is_empty());
    }

    #[test]
    fn search_ids_returns_uuids() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "unique content about rust",
                &[],
                1700000000,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        let ids = engine.search_ids("rust", 10).unwrap();
        assert_eq!(ids.len(), 1);
        assert_eq!(
            ids[0],
            uuid::Uuid::parse_str("11111111-1111-1111-1111-111111111111").unwrap()
        );
    }

    // ── Tantivy query injection tests ───────────────────────────────

    #[test]
    fn sanitize_leaves_plain_terms_unquoted() {
        let result = sanitize_tantivy_query("hello world");
        assert_eq!(result, "hello world");
    }

    #[test]
    fn sanitize_drops_punct_only_terms() {
        let result = sanitize_tantivy_query("*");
        assert_eq!(result, "");
        // Should not match all documents when parsed
    }

    #[test]
    fn sanitize_escapes_boolean_operators() {
        let result = sanitize_tantivy_query("NOT secret");
        assert_eq!(result, "\"NOT\" secret");
    }

    #[test]
    fn sanitize_escapes_field_syntax() {
        let result = sanitize_tantivy_query("content:secret");
        assert_eq!(result, "\"content:secret\"");
    }

    #[test]
    fn sanitize_escapes_quotes() {
        let result = sanitize_tantivy_query("test\"injection");
        assert!(
            result.contains("\\\""),
            "embedded quotes should be escaped: {result}"
        );
    }

    #[test]
    fn sanitize_empty_returns_empty() {
        assert_eq!(sanitize_tantivy_query(""), "");
        assert_eq!(sanitize_tantivy_query("   "), "");
    }

    #[test]
    fn sanitize_preserves_alphanumeric() {
        let result = sanitize_tantivy_query("rust programming 2024");
        assert_eq!(result, "rust programming 2024");
    }

    #[test]
    fn sanitize_preserves_hyphenated_compounds() {
        let result = sanitize_tantivy_query("antigravity antigravity-project-test");
        assert_eq!(result, "antigravity antigravity-project-test");
    }

    // ── Stopword tests ──────────────────────────────────────────────

    #[test]
    fn strip_stopwords_removes_common_words() {
        assert_eq!(
            strip_stopwords("smoke test from wmClient"),
            "smoke test wmClient"
        );
        assert_eq!(strip_stopwords("the from and or"), "");
        assert_eq!(strip_stopwords("Rust ownership"), "Rust ownership");
        assert_eq!(strip_stopwords(""), "");
    }

    #[test]
    fn strip_stopwords_is_case_insensitive() {
        assert_eq!(strip_stopwords("FROM The And"), "");
    }

    // ── Index-time sanitization tests ───────────────────────────────

    #[test]
    fn sanitize_content_skips_null_bytes() {
        let content = "binary\x00garbage\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00";
        assert!(sanitize_content_for_index(content).is_none());
    }

    #[test]
    fn sanitize_content_skips_low_printable_ratio() {
        // 5 control chars out of 11 → ratio 0.55 < 0.9 → skip
        let content = "\u{01}\u{02}\u{03}\u{04}\u{05}hello";
        assert!(sanitize_content_for_index(content).is_none());
    }

    #[test]
    fn sanitize_content_scrubs_and_caps() {
        // A stray control char does not disqualify clean text — it is scrubbed.
        let content = "clean text\u{01}with one control char";
        let cleaned = sanitize_content_for_index(content).unwrap();
        assert!(!cleaned.contains('\u{01}'));
        assert!(cleaned.starts_with("clean text with one control char"));

        let long = "a".repeat(MAX_INDEX_CONTENT_LEN + 1000);
        let capped = sanitize_content_for_index(&long).unwrap();
        assert_eq!(capped.chars().count(), MAX_INDEX_CONTENT_LEN);
    }

    #[test]
    fn sanitize_content_skips_empty() {
        assert!(sanitize_content_for_index("").is_none());
        assert!(sanitize_content_for_index("   ").is_none());
    }

    #[test]
    fn scrub_text_replaces_control_chars() {
        let result = scrub_text("a\u{01}b\nc\td\u{7f}e");
        assert_eq!(result, "a b\nc\td e");
    }

    #[test]
    fn add_document_skips_binary_content() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "\u{00}\u{01}\u{02}raw serialized bytes",
                &[],
                1700000000,
            )
            .unwrap();
        engine
            .add_document(
                &mut writer,
                "22222222-2222-2222-2222-222222222222",
                "codex",
                "clean searchable text",
                &[],
                1700000001,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        // The binary doc must not be searchable; the clean one must be.
        let results = engine.search("serialized", 10).unwrap();
        assert!(results.is_empty(), "binary content must not be indexed");

        let results = engine.search("clean", 10).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].memory_id, "22222222-2222-2222-2222-222222222222");
    }

    // ── Score-threshold tests ───────────────────────────────────────

    fn index_alpha_pair(engine: &SearchEngine) {
        let mut writer = engine.writer().unwrap();
        // Two docs both containing "alpha"; the short one scores higher
        // (BM25 length normalization).
        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "alpha",
                &[],
                1700000000,
            )
            .unwrap();
        let filler = format!("alpha {}", "zzz ".repeat(400));
        engine
            .add_document(
                &mut writer,
                "22222222-2222-2222-2222-222222222222",
                "codex",
                &filler,
                &[],
                1700000001,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();
    }

    #[test]
    fn search_absolute_min_score_filters_weak_matches() {
        let (_tmp, engine) = open_engine();
        index_alpha_pair(&engine);

        let base = engine.search("alpha", 10).unwrap();
        assert_eq!(base.len(), 2);
        let (hi, lo) = if base[0].score >= base[1].score {
            (base[0].score, base[1].score)
        } else {
            (base[1].score, base[0].score)
        };
        assert!(
            hi > lo,
            "short doc should outscore long doc (hi={hi}, lo={lo})"
        );
        let mid = f32::midpoint(hi, lo);

        let opts = SearchOptions {
            limit: 10,
            min_score: Some(mid),
            ..SearchOptions::default()
        };
        let filtered = engine.search_opt("alpha", &opts).unwrap();
        assert_eq!(filtered.len(), 1);
        assert!((filtered[0].score - hi).abs() < 1e-3);
    }

    #[test]
    fn search_relative_floor_filters_weak_matches() {
        let (_tmp, engine) = open_engine();
        index_alpha_pair(&engine);

        let opts = SearchOptions {
            limit: 10,
            relative_floor: Some(0.5),
            ..SearchOptions::default()
        };
        let filtered = engine.search_opt("alpha", &opts).unwrap();
        assert_eq!(filtered.len(), 1, "weak match must fall below 50% of top");
        assert_eq!(
            filtered[0].memory_id,
            "11111111-1111-1111-1111-111111111111"
        );
        assert!((filtered[0].normalized_score - 1.0).abs() < 1e-3);
    }

    #[test]
    fn search_all_results_normalized() {
        let (_tmp, engine) = open_engine();
        index_alpha_pair(&engine);

        let results = engine.search("alpha", 10).unwrap();
        assert_eq!(results.len(), 2);
        assert!((results[0].normalized_score - 1.0).abs() < 1e-3);
        for r in &results[1..] {
            assert!(r.normalized_score <= 1.0);
            assert!(r.normalized_score > 0.0);
        }
    }

    #[test]
    fn search_stemming_matches_morphological_variants() {
        // The en_stem tokenizer should match morphological variants:
        // "graduate" (query) ↔ "graduated" (indexed content).
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "I graduated with a degree in Business Administration",
                &[],
                1700000000,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        // Query with present tense "graduate" should match past tense "graduated"
        let results = engine.search("graduate", 10).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].memory_id, "11111111-1111-1111-1111-111111111111");

        // Query with "degrees" should match "degree"
        let results = engine.search("degrees", 10).unwrap();
        assert_eq!(results.len(), 1);
    }

    #[test]
    fn search_incident_query_returns_only_relevant() {
        // Mirrors the 2026-08-11 incident: `memory.hybrid_recall`
        // query "smoke test from wmClient" must NOT return unrelated memories.
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        let smoke_id = "11111111-1111-1111-1111-111111111111";
        engine
            .add_document(
                &mut writer,
                smoke_id,
                "codex",
                "smoke test from wmClient: verify recall works",
                &[],
                1700000000,
            )
            .unwrap();
        let unrelated = [
            "NES Evolution and Impact: a history of the console wars",
            "Insights on The Gateless Gate: koans and zen practice",
            "What the tweet is really saying: a thread analysis",
        ];
        for (i, content) in (1i64..).zip(unrelated.iter()) {
            engine
                .add_document(
                    &mut writer,
                    &format!("22222222-2222-2222-2222-2222222222{i:02}"),
                    "codex",
                    content,
                    &[],
                    1700000000 + i,
                )
                .unwrap();
        }
        engine.commit(&mut writer).unwrap();

        let results = engine.search("smoke test from wmClient", 20).unwrap();
        assert_eq!(
            results.len(),
            1,
            "only the smoke memory should match: {results:?}"
        );
        assert_eq!(results[0].memory_id, smoke_id);
        assert!(results[0].content.contains("smoke test"));
    }

    #[test]
    fn search_project_compound_query() {
        // "antigravity antigravity-project-test" must find the project memory.
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "[antigravity:antigravity-project-test]\nQ: how does it work?\nA: details here",
                &["project_antigravity-project-test".into()],
                1700000000,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        let results = engine
            .search("antigravity antigravity-project-test", 10)
            .unwrap();
        assert!(
            !results.is_empty(),
            "project compound query must match the antigravity memory"
        );
        assert_eq!(results[0].memory_id, "11111111-1111-1111-1111-111111111111");
    }

    #[test]
    fn or_default_filters_partial_matches_via_coverage() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "alpha beta gamma delta",
                &[],
                1700000000,
            )
            .unwrap();
        engine
            .add_document(
                &mut writer,
                "22222222-2222-2222-2222-222222222222",
                "codex",
                "alpha only here",
                &[],
                1700000001,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        // OR is now the default.  A 3-term query requires 2/3 token coverage,
        // so the "alpha only here" doc (1/3) is filtered out.
        let results = engine.search("alpha beta gamma", 10).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].memory_id, "11111111-1111-1111-1111-111111111111");

        // With a 2-term query the floor is 1/2, so partial matches return.
        let results = engine.search("alpha beta", 10).unwrap();
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn coverage_is_case_insensitive() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();
        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "Smoke Test for wmClient integration",
                &[],
                1700000000,
            )
            .unwrap();
        engine
            .add_document(
                &mut writer,
                "22222222-2222-2222-2222-222222222222",
                "codex",
                "test only here",
                &[],
                1700000001,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        // 3 tokens: smoke + test + wmclient (case-insensitive stemming-aware
        // whole-word matching) — only the first doc covers 2/3; the "test
        // only" doc covers 1/3 and must be dropped even though it matched
        // via OR.
        let results = engine.search("Smoke Test from wmClient", 10).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].memory_id, "11111111-1111-1111-1111-111111111111");
    }

    #[test]
    fn coverage_matches_stemmed_variants() {
        // Stemming-aware coverage: "graduate" should match "graduated",
        // "classes" should match "class", mirroring the en_stem tokenizer.
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();
        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "I graduated with a degree in Business Administration",
                &[],
                1700000000,
            )
            .unwrap();
        engine
            .add_document(
                &mut writer,
                "22222222-2222-2222-2222-222222222222",
                "codex",
                "degree only here",
                &[],
                1700000001,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        // 2-term query "graduate degree" → coverage floor 1/2.
        // Doc 1: "graduated" stems to "graduat", "degree" stems to "degre" → 2/2.
        // Doc 2: "degree" → 1/2.
        // Both pass the 1/2 floor, but doc 1 should rank higher due to
        // the coverage-ratio boost (2/2 > 1/2).
        let results = engine.search("graduate degree", 10).unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].memory_id, "11111111-1111-1111-1111-111111111111");
    }

    #[test]
    fn coverage_normalizes_possessives_and_punctuation() {
        let query = "buy sister's birthday gift";
        assert_eq!(
            query_stem_tokens(query),
            ["buy", "sister", "birthday", "gift"]
        );
        assert_eq!(
            count_token_hits("I bought a dress for my sister birthday", query),
            2
        );
    }

    #[test]
    fn search_stopword_only_query_returns_nothing() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();
        engine
            .add_document(
                &mut writer,
                "11111111-1111-1111-1111-111111111111",
                "codex",
                "some ordinary text",
                &[],
                1700000000,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        let results = engine.search("the from and or", 10).unwrap();
        assert!(results.is_empty());
    }

    #[test]
    fn wildcard_query_doesnt_match_all() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        engine
            .add_document(&mut writer, "uuid-1", "codex", "first document", &[], 1000)
            .unwrap();
        engine
            .add_document(&mut writer, "uuid-2", "codex", "second document", &[], 2000)
            .unwrap();
        engine.commit(&mut writer).unwrap();

        // Wildcard should not match all documents
        let results = engine.search("*", 10).unwrap();
        // With sanitization, "*" is treated as literal text, not wildcard
        // So it should match 0 documents (no content contains literal "*")
        assert!(
            results.is_empty(),
            "wildcard query should not match all documents after sanitization"
        );
    }

    #[test]
    fn field_syntax_query_doesnt_access_other_fields() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        // Add a doc with "secret" in galaxy field but not content
        engine
            .add_document(&mut writer, "uuid-1", "secret", "public content", &[], 1000)
            .unwrap();
        engine.commit(&mut writer).unwrap();

        // Try to use field syntax to access galaxy field
        let results = engine.search("galaxy:secret", 10).unwrap();
        // With sanitization, "galaxy:secret" is treated as literal text
        // So it should not match the galaxy field
        assert!(
            results.is_empty(),
            "field syntax injection should not access non-searchable fields"
        );
    }

    #[test]
    fn boolean_operator_doesnt_bypass_search() {
        let (_tmp, engine) = open_engine();
        let mut writer = engine.writer().unwrap();

        engine
            .add_document(
                &mut writer,
                "uuid-1",
                "codex",
                "important secret data",
                &[],
                1000,
            )
            .unwrap();
        engine.commit(&mut writer).unwrap();

        // Uppercase operator words are quoted (and stripped as stopwords), so
        // they cannot be used to exclude or require terms: "AND secret"
        // reduces to a plain search for "secret" and must still match.
        let results = engine.search("AND secret", 10).unwrap();
        assert_eq!(results.len(), 1);

        // A query made only of operators/stopwords has no terms and matches
        // nothing — it cannot match the whole corpus.
        let results = engine.search("AND OR NOT", 10).unwrap();
        assert!(
            results.is_empty(),
            "operator-only query must not bypass search"
        );
    }
}
