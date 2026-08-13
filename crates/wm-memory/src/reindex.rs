//! Index rebuild — reconstruct the Tantivy full-text index from LMDB.
//!
//! The Tantivy index can drift from the LMDB store (stale entries survive
//! deletes, binary migration artifacts pollute results). `rebuild_index`
//! rebuilds it from scratch: every memory in every galaxy is re-indexed
//! through the same sanitization gate used at write time, so garbage content
//! is skipped and deleted memories disappear.
//!
//! The caller is responsible for backing up the existing index directory
//! before rebuilding (the `wm reindex` CLI does this automatically).

use serde::{Deserialize, Serialize};
use wm_core::{CoreError, Galaxy, Result};

use crate::memory::Memory;
use crate::search::{SearchEngine, sanitize_content_for_index};
use crate::store::MemoryStore;

/// Batch size for scanning galaxies during rebuild (unused by `scan_all`
/// today; kept for callers that stream batches).
pub const REINDEX_BATCH: usize = 2_000;

/// Per-galaxy statistics for an index rebuild.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct GalaxyRebuildStats {
    /// Galaxy database name.
    pub galaxy: String,
    /// Memories scanned from LMDB.
    pub scanned: usize,
    /// Documents added to the index.
    pub indexed: usize,
    /// Memories skipped (failed content sanitization).
    pub skipped: usize,
}

/// Report of a full index rebuild.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexRebuildReport {
    /// Memories scanned from LMDB across all galaxies.
    pub scanned: usize,
    /// Documents added to the index.
    pub indexed: usize,
    /// Memories skipped because content failed sanitization.
    pub skipped: usize,
    /// Per-galaxy breakdown.
    pub galaxies: Vec<GalaxyRebuildStats>,
}

/// Per-galaxy consistency check result.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct GalaxyConsistency {
    /// Galaxy database name.
    pub galaxy: String,
    /// Memories in LMDB.
    pub lmdb_count: usize,
    /// Documents in Tantivy.
    pub tantivy_count: usize,
    /// True when counts differ (index is stale or has orphan documents).
    pub drift: bool,
}

/// Consistency check report comparing LMDB to Tantivy.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ConsistencyReport {
    /// Per-galaxy comparison.
    pub galaxies: Vec<GalaxyConsistency>,
    /// Total LMDB memories across all galaxies.
    pub total_lmdb: usize,
    /// Total Tantivy documents across all galaxies.
    pub total_tantivy: usize,
    /// True if any galaxy has drift.
    pub has_drift: bool,
}

/// Check consistency between LMDB store and Tantivy index.
///
/// Compares memory counts in LMDB to document counts in Tantivy for each
/// galaxy. A mismatch indicates the index is stale (LMDB has memories that
/// Tantivy doesn't) or has orphan documents (Tantivy has documents that
/// LMDB doesn't — e.g. from a failed delete).
///
/// Note: content that fails sanitization is intentionally not indexed, so
/// a small drift is expected when memories contain binary/garbage content.
/// The caller should use `IndexHealth::failures` to distinguish best-effort
/// skips from actual indexing failures.
#[must_use]
pub fn check_consistency(store: &MemoryStore, search: &SearchEngine) -> ConsistencyReport {
    let mut report = ConsistencyReport::default();
    for galaxy in Galaxy::memory_galaxies() {
        let lmdb_count = store.count(galaxy).unwrap_or(0);
        let tantivy_count = search.count_docs_in_galaxy(galaxy.db_name()).unwrap_or(0);
        let drift = lmdb_count != tantivy_count;
        report.total_lmdb += lmdb_count;
        report.total_tantivy += tantivy_count;
        if drift {
            report.has_drift = true;
        }
        report.galaxies.push(GalaxyConsistency {
            galaxy: galaxy.db_name().to_string(),
            lmdb_count,
            tantivy_count,
            drift,
        });
    }
    report
}

/// Rebuild the Tantivy index from LMDB contents.
///
/// With no filter, all existing index documents are deleted and every memory
/// in every galaxy is re-indexed. With a filter, only the selected galaxies
/// are deleted and re-indexed — documents belonging to other galaxies are
/// left untouched. Content that fails [`sanitize_content_for_index`] is
/// skipped (counted in the report).
///
/// NOTE: the existing index directory must be backed up by the caller before
/// this runs — deletion is permanent once committed.
pub fn rebuild_index(
    store: &MemoryStore,
    search: &SearchEngine,
    galaxy_filter: &[String],
) -> Result<IndexRebuildReport> {
    let mut report = IndexRebuildReport::default();
    {
        let mut writer = search.writer()?;
        if galaxy_filter.is_empty() {
            writer
                .as_mut()
                .ok_or_else(|| {
                    CoreError::Memory("Tantivy writer unavailable: index opened read-only".into())
                })?
                .delete_all_documents()
                .map_err(|e| CoreError::Memory(format!("Tantivy delete_all_documents: {e}")))?;
        } else {
            // Filtered rebuild: remove only the selected galaxies' documents.
            // The old behavior deleted everything first, so `--galaxy codex`
            // silently wiped search documents for every other galaxy.
            for galaxy in Galaxy::all() {
                if galaxy_filter.iter().any(|g| g == galaxy.db_name()) {
                    search.delete_by_galaxy(&mut writer, galaxy.db_name())?;
                }
            }
        }

        for galaxy in Galaxy::all() {
            if !galaxy_filter.is_empty() && !galaxy_filter.iter().any(|g| g == galaxy.db_name()) {
                continue;
            }
            let memories = store.scan_all(galaxy)?;
            let mut stats = GalaxyRebuildStats {
                galaxy: galaxy.db_name().to_string(),
                ..GalaxyRebuildStats::default()
            };
            for mem in &memories {
                stats.scanned += 1;
                if index_memory(search, &mut writer, galaxy, mem)?.is_some() {
                    stats.indexed += 1;
                } else {
                    stats.skipped += 1;
                }
            }
            report.scanned += stats.scanned;
            report.indexed += stats.indexed;
            report.skipped += stats.skipped;
            report.galaxies.push(stats);
        }

        search.commit(&mut writer)?;
        drop(writer);
    }
    Ok(report)
}

/// Index a single memory, returning `Ok(Some(()))` when indexed and
/// `Ok(None)` when the content was skipped by sanitization.
fn index_memory(
    search: &SearchEngine,
    writer: &mut Option<tantivy::IndexWriter>,
    galaxy: Galaxy,
    mem: &Memory,
) -> Result<Option<()>> {
    let Some(content) = sanitize_content_for_index(&mem.content) else {
        return Ok(None);
    };
    let timestamp = mem.metadata.created_at.timestamp();
    let id = mem.metadata.id.to_string();
    search.add_document(
        writer,
        &id,
        galaxy.db_name(),
        &content,
        &mem.metadata.tags,
        timestamp,
    )?;
    Ok(Some(()))
}

/// Helper for the `wm reindex` CLI: validate that the tantivy index directory
/// exists next to the LMDB store.
#[must_use]
pub fn tantivy_path_for(store_path: &std::path::Path) -> std::path::PathBuf {
    store_path.join("tantivy")
}

/// Error message used when the index directory is missing.
#[must_use]
pub fn missing_index_error(store_path: &std::path::Path) -> CoreError {
    CoreError::Memory(format!(
        "Tantivy index not found at {} — run 'wm serve' once to create it",
        tantivy_path_for(store_path).display()
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Memory;
    use tempfile::tempdir;

    fn setup() -> (tempfile::TempDir, MemoryStore, SearchEngine) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let tantivy_dir = tmp.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_dir).unwrap();
        let search = SearchEngine::open(&tantivy_dir).unwrap();
        (tmp, store, search)
    }

    fn put_and_index(store: &MemoryStore, search: &SearchEngine, galaxy: Galaxy, content: &str) {
        let mem = Memory::new(galaxy, content.to_string());
        let id = mem.metadata.id;
        store.put(galaxy, &mem).unwrap();
        let mut writer = search.writer().unwrap();
        search
            .add_document(
                &mut writer,
                &id.to_string(),
                galaxy.db_name(),
                content,
                &mem.metadata.tags,
                mem.metadata.created_at.timestamp(),
            )
            .unwrap();
        search.commit(&mut writer).unwrap();
    }

    #[test]
    fn rebuild_repopulates_index_from_lmdb() {
        let (_tmp, store, search) = setup();
        put_and_index(&store, &search, Galaxy::Codex, "rust memory one");
        put_and_index(&store, &search, Galaxy::Codex, "python memory two");
        put_and_index(&store, &search, Galaxy::Research, "research notes");

        // Inject a stale document that exists in the index but not in LMDB —
        // the rebuild must remove it.
        {
            let mut writer = search.writer().unwrap();
            search
                .add_document(
                    &mut writer,
                    "99999999-9999-9999-9999-999999999999",
                    "codex",
                    "stale ghost document",
                    &[],
                    1000,
                )
                .unwrap();
            search.commit(&mut writer).unwrap();
        }
        let ghost = search.search("ghost", 10).unwrap();
        assert_eq!(ghost.len(), 1);

        let report = rebuild_index(&store, &search, &[]).unwrap();
        assert_eq!(report.indexed, 3);
        assert_eq!(report.scanned, 3);
        assert_eq!(report.galaxies.len(), Galaxy::COUNT);

        let ghost = search.search("ghost", 10).unwrap();
        assert!(ghost.is_empty(), "stale index entry must be purged");

        let rust = search.search("rust memory one", 10).unwrap();
        assert_eq!(rust.len(), 1);
        assert_eq!(rust[0].content, "rust memory one");
    }

    #[test]
    fn rebuild_skips_binary_garbage() {
        let (_tmp, store, search) = setup();
        put_and_index(&store, &search, Galaxy::Codex, "clean text entry");
        let mem = Memory::new(Galaxy::Codex, "\u{00}\u{01}\u{02}raw bytes".to_string());
        store.put(Galaxy::Codex, &mem).unwrap();

        let report = rebuild_index(&store, &search, &[]).unwrap();
        assert_eq!(report.indexed, 1, "garbage content must be skipped");
        assert_eq!(report.skipped, 1);

        let results = search.search("raw", 10).unwrap();
        assert!(results.is_empty());
    }

    #[test]
    fn rebuild_respects_galaxy_filter() {
        let (_tmp, store, search) = setup();
        put_and_index(&store, &search, Galaxy::Codex, "codex memory");
        put_and_index(&store, &search, Galaxy::Research, "research memory");

        let report = rebuild_index(&store, &search, &["codex".to_string()]).unwrap();
        assert_eq!(report.indexed, 1);
        assert_eq!(report.galaxies.len(), 1);
        assert_eq!(report.galaxies[0].galaxy, "codex");

        // Regression: the filtered rebuild used to delete ALL documents first,
        // so documents from unselected galaxies vanished from the index.
        let codex = search.search("codex memory", 10).unwrap();
        assert_eq!(codex.len(), 1);
        let research = search.search("research memory", 10).unwrap();
        assert_eq!(
            research.len(),
            1,
            "filtered rebuild must preserve documents in unselected galaxies"
        );
    }

    #[test]
    fn consistency_check_no_drift_when_indexed() {
        let (_tmp, store, search) = setup();
        put_and_index(&store, &search, Galaxy::Codex, "hello world");
        put_and_index(&store, &search, Galaxy::Codex, "another memory");

        let report = check_consistency(&store, &search);
        assert!(!report.has_drift, "no drift expected when all indexed");
        let codex = report
            .galaxies
            .iter()
            .find(|g| g.galaxy == "codex")
            .unwrap();
        assert_eq!(codex.lmdb_count, 2);
        assert_eq!(codex.tantivy_count, 2);
    }

    #[test]
    fn consistency_check_detects_drift() {
        let (_tmp, store, search) = setup();
        // Write to LMDB without indexing → drift.
        let mem = Memory::new(Galaxy::Codex, "unindexed".to_string());
        store.put(Galaxy::Codex, &mem).unwrap();

        let report = check_consistency(&store, &search);
        assert!(
            report.has_drift,
            "drift expected when LMDB has unindexed memory"
        );
        let codex = report
            .galaxies
            .iter()
            .find(|g| g.galaxy == "codex")
            .unwrap();
        assert_eq!(codex.lmdb_count, 1);
        assert_eq!(codex.tantivy_count, 0);
    }

    #[test]
    fn index_health_tracks_successes() {
        let (_tmp, store, search) = setup();
        put_and_index(&store, &search, Galaxy::Codex, "test content");

        let health = search.health().snapshot();
        let successes = health
            .get("successes")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(0);
        assert!(successes > 0, "expected at least one success");
        let failures = health
            .get("failures")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(0);
        assert_eq!(failures, 0);
        assert_eq!(
            health.get("degraded").and_then(serde_json::Value::as_bool),
            Some(false)
        );
    }

    #[test]
    fn consistency_check_ignores_non_memory_galaxies() {
        let (_tmp, store, search) = setup();
        put_and_index(&store, &search, Galaxy::Codex, "indexed memory");

        // Write raw bytes into the Karma galaxy (non-memory data).
        // Karma is not a memory galaxy and is intentionally not indexed in Tantivy.
        store.put_raw(Galaxy::Karma, b"key1", b"value1").unwrap();

        let report = check_consistency(&store, &search);
        assert!(
            !report.has_drift,
            "karma entries should not cause drift — non-memory galaxies are excluded"
        );
        // Only memory galaxies should appear in the report.
        let galaxy_names: Vec<_> = report.galaxies.iter().map(|g| g.galaxy.as_str()).collect();
        assert!(
            !galaxy_names.contains(&"karma"),
            "karma should not appear in consistency report"
        );
        assert!(
            !galaxy_names.contains(&"dharma"),
            "dharma should not appear in consistency report"
        );
    }
}
