//! Search engine — Tantivy full-text search.
//!
//! Provides BM25-scored full-text search over memory content.
//! Index is stored alongside the LMDB store in a separate directory.

use crate::MemoryId;
use wm_core::{CoreError, Galaxy, Result};

use std::path::Path;
use std::sync::Mutex;
use tantivy::{
    Index, IndexReader, IndexWriter, ReloadPolicy,
    collector::TopDocs,
    doc,
    query::QueryParser,
    schema::{Field, STORED, STRING, Schema, TEXT, TantivyDocument, Value},
};

/// Search result item.
#[derive(Debug, Clone)]
pub struct SearchResult {
    /// Memory UUID (as string)
    pub memory_id: String,
    /// Galaxy name
    pub galaxy: String,
    /// BM25 score
    pub score: f32,
    /// Content snippet
    pub content: String,
}

/// The full-text search engine backed by Tantivy.
pub struct SearchEngine {
    index: Index,
    reader: IndexReader,
    writer: Mutex<IndexWriter>,
    field_id: Field,
    field_galaxy: Field,
    field_content: Field,
    field_tags: Field,
    field_timestamp: Field,
}

impl SearchEngine {
    /// Build the Tantivy schema for memory indexing.
    fn build_schema() -> (Schema, Field, Field, Field, Field, Field) {
        let mut schema_builder = Schema::builder();
        let field_id = schema_builder.add_text_field("memory_id", STRING | STORED);
        let field_galaxy = schema_builder.add_text_field("galaxy", STRING | STORED);
        let field_content = schema_builder.add_text_field("content", TEXT | STORED);
        let field_tags = schema_builder.add_text_field("tags", TEXT);
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
            writer: Mutex::new(writer),
            field_id,
            field_galaxy,
            field_content,
            field_tags,
            field_timestamp,
        })
    }

    /// Lock the shared writer for adding/removing documents.
    ///
    /// The writer is created at `open()` time and shared across all callers
    /// via a `Mutex`, preventing lock contention with Tantivy's single-writer model.
    pub fn writer(&self) -> Result<std::sync::MutexGuard<'_, IndexWriter>> {
        self.writer
            .lock()
            .map_err(|_| CoreError::Memory("Tantivy writer mutex poisoned".into()))
    }

    /// Index a memory document.
    pub fn add_document(
        &self,
        writer: &mut IndexWriter,
        memory_id: &str,
        galaxy: &str,
        content: &str,
        tags: &[String],
        timestamp: i64,
    ) -> Result<()> {
        let tags_str = tags.join(" ");
        let doc = doc!(
            self.field_id => memory_id,
            self.field_galaxy => galaxy,
            self.field_content => content,
            self.field_tags => tags_str,
            self.field_timestamp => timestamp,
        );
        writer
            .add_document(doc)
            .map_err(|e| CoreError::Memory(format!("Tantivy add_document: {e}")))?;
        Ok(())
    }

    /// Delete documents by memory ID.
    pub fn delete_document(&self, writer: &mut IndexWriter, memory_id: &str) -> Result<()> {
        let term = tantivy::Term::from_field_text(self.field_id, memory_id);
        writer.delete_term(term);
        Ok(())
    }

    /// Commit pending index changes and reload the reader.
    pub fn commit(&self, writer: &mut IndexWriter) -> Result<()> {
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
    /// The query is sanitized to prevent Tantivy query syntax injection.
    pub fn search(&self, query: &str, limit: usize) -> Result<Vec<SearchResult>> {
        self.search_in_galaxy(query, None, limit)
    }

    /// Search for memories matching the query, optionally filtered by galaxy.
    ///
    /// The query is sanitized to escape Tantivy special characters (+, -, *, "",
    /// field syntax, boolean operators) that could be used for query injection.
    pub fn search_in_galaxy(
        &self,
        query: &str,
        galaxy: Option<Galaxy>,
        limit: usize,
    ) -> Result<Vec<SearchResult>> {
        let sanitized = sanitize_tantivy_query(query);
        if sanitized.trim().is_empty() {
            return Ok(Vec::new());
        }

        let searcher = self.reader.searcher();

        let mut query_parser =
            QueryParser::for_index(&self.index, vec![self.field_content, self.field_tags]);
        query_parser.set_conjunction_by_default();

        let parsed = query_parser
            .parse_query(&sanitized)
            .map_err(|e| CoreError::Memory(format!("Tantivy parse_query: {e}")))?;

        let collector = TopDocs::with_limit(limit);

        let top_docs = searcher
            .search(&parsed, &collector)
            .map_err(|e| CoreError::Memory(format!("Tantivy search: {e}")))?;

        let mut results = Vec::new();
        for (score, doc_address) in top_docs {
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

            if let Some(g) = galaxy {
                if doc_galaxy != g.db_name() {
                    continue;
                }
            }

            let content = doc
                .get_first(self.field_content)
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();

            results.push(SearchResult {
                memory_id,
                galaxy: doc_galaxy,
                score,
                content,
            });
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
/// This function escapes all special characters by wrapping each term in
/// double quotes, making Tantivy treat them as literal text.
#[must_use]
pub fn sanitize_tantivy_query(input: &str) -> String {
    // If empty, return as-is
    if input.trim().is_empty() {
        return String::new();
    }

    // Split into terms and wrap each in quotes to force literal matching
    let terms: Vec<String> = input
        .split_whitespace()
        .filter(|s| !s.is_empty())
        .map(|term| {
            // Escape any embedded double quotes
            let escaped = term.replace('"', "\\\"");
            format!("\"{escaped}\"")
        })
        .collect();

    terms.join(" ")
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
    fn sanitize_wraps_terms_in_quotes() {
        let result = sanitize_tantivy_query("hello world");
        assert_eq!(result, "\"hello\" \"world\"");
    }

    #[test]
    fn sanitize_escapes_wildcard() {
        let result = sanitize_tantivy_query("*");
        assert_eq!(result, "\"*\"");
        // Should not match all documents when parsed
    }

    #[test]
    fn sanitize_escapes_boolean_operators() {
        let result = sanitize_tantivy_query("NOT secret");
        assert_eq!(result, "\"NOT\" \"secret\"");
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
        assert_eq!(result, "\"rust\" \"programming\" \"2024\"");
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

        // Try NOT operator to exclude results
        let results = engine.search("NOT secret", 10).unwrap();
        // With sanitization, "NOT" is treated as literal text
        // So it should search for "NOT" AND "secret" (conjunction)
        // The document contains "secret" but not "NOT", so it should not match
        assert!(
            results.is_empty(),
            "boolean operator injection should not bypass search"
        );
    }
}
