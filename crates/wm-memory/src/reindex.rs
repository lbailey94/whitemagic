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
    /// Index documents deleted — LMDB rows that no longer exist (orphans
    /// from failed deletes or interrupted runs). Nonzero only on the
    /// incremental heal path; a full rebuild deletes by galaxy instead.
    pub deleted: usize,
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
    /// Index documents deleted as orphans (incremental heal only).
    pub deleted: usize,
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

/// Per-galaxy drift classification — the truthfulness layer over
/// [`check_consistency`].
///
/// A count mismatch is not automatically healable drift: docs the index
/// gate refuses (null bytes / printable ratio < [`MIN_PRINTABLE_RATIO`])
/// are **never indexable as-is** and survive every rebuild by design. This
/// classification separates that documented reserve from real drift —
/// `healable_gap != 0` means the index differs from what a rebuild would
/// actually produce.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct GalaxyDriftClass {
    /// Galaxy database name.
    pub galaxy: String,
    /// Memories in LMDB.
    pub lmdb_count: usize,
    /// Documents in Tantivy.
    pub tantivy_count: usize,
    /// LMDB docs that fail the index gate — the documented reserve, never
    /// indexable as-is. Counted only in the LMDB > Tantivy direction (a
    /// gate-failing doc cannot exist in the index).
    pub skip_reserve: usize,
    /// Signed gap between what a rebuild WOULD index (`lmdb - skip_reserve`)
    /// and what the index holds. `0` = the index is exactly rebuild output;
    /// positive = missing indexable docs; negative = orphan documents.
    pub healable_gap: i64,
}

/// Classification report across all memory galaxies.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct DriftClassification {
    /// Per-galaxy classification.
    pub galaxies: Vec<GalaxyDriftClass>,
    /// Σ skip-reserve docs across galaxies.
    pub skip_reserve_total: usize,
    /// Σ |healable_gap| across galaxies — the docs a rebuild would change.
    pub healable_total: usize,
}

/// Classify per-galaxy count mismatches into healable drift vs the
/// sanitization-skip reserve.
///
/// The skip-reserve count requires one LMDB scan + gate evaluation per
/// galaxy in the `lmdb > tantivy` direction only (galaxies whose counts
/// match, or that have orphans, cannot contain gate-failing docs — those
/// are never indexed). Cheap when consistent, one scan pass when drifted.
#[must_use]
pub fn classify_drift(store: &MemoryStore, search: &SearchEngine) -> DriftClassification {
    let mut out = DriftClassification::default();
    for galaxy in Galaxy::memory_galaxies() {
        let lmdb_count = store.count(galaxy).unwrap_or(0);
        let tantivy_count = search.count_docs_in_galaxy(galaxy.db_name()).unwrap_or(0);
        let mut skip_reserve = 0usize;
        if lmdb_count > tantivy_count {
            for mem in store.scan(galaxy, lmdb_count).unwrap_or_default() {
                if sanitize_content_for_index(&mem.content).is_none() {
                    skip_reserve += 1;
                }
            }
        }
        let indexable = usize::try_into(lmdb_count - skip_reserve).unwrap_or(i64::MAX);
        let indexed = usize::try_into(tantivy_count).unwrap_or(i64::MAX);
        let healable_gap = indexable - indexed;
        out.skip_reserve_total += skip_reserve;
        out.healable_total += healable_gap.unsigned_abs() as usize;
        out.galaxies.push(GalaxyDriftClass {
            galaxy: galaxy.db_name().to_string(),
            lmdb_count,
            tantivy_count,
            skip_reserve,
            healable_gap,
        });
    }
    out
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
    // Decode every selected source before queuing any index deletion. Keep
    // these snapshots for the write phase, so no second tolerant scan can
    // silently drop records. Callers must still quiesce concurrent writers.
    let mut snapshots = Vec::new();
    for galaxy in Galaxy::memory_galaxies() {
        if galaxy_filter.is_empty() || galaxy_filter.iter().any(|g| g == galaxy.db_name()) {
            snapshots.push((galaxy, store.scan_all_strict(galaxy)?));
        }
    }
    if galaxy_filter.iter().any(|name| {
        !Galaxy::memory_galaxies()
            .iter()
            .any(|g| g.db_name() == name)
    }) {
        return Err(CoreError::Memory(
            "reindex filter must name a memory galaxy".into(),
        ));
    }
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

        for (galaxy, memories) in snapshots {
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

/// Heal index drift by indexing only what the index is actually missing.
///
/// Whole-galaxy drift is systematic, not exceptional: session tools, dream
/// consolidation, and research cycles write to LMDB without a search engine,
/// and best-effort indexing failures are swallowed at the tool layer. Call
/// this on writable server startup (and periodically in the daemon) so search
/// stays complete without manual `wm reindex` runs.
///
/// Incremental by design (2026-09-10, daemon crash-loop fix): the previous
/// implementation delegated to [`rebuild_index`], deleting and re-indexing
/// every document of every drifted galaxy. On the live store that meant
/// ~58k docs (~5 min) per 5-minute checkpoint cycle, synchronously inside
/// the daemon's watchdogged main loop — the 120s watchdog killed the heal
/// mid-run every cycle, the index never caught up, and the daemon
/// crash-looped forever (35 failures in two days). The incremental path
/// diffs indexed IDs against LMDB IDs and touches only the difference, so
/// a steady-state cycle indexes a handful of docs in well under a second.
/// Full rebuilds stay available via [`rebuild_index`] for manual
/// `wm reindex` runs and the server-shutdown path.
///
/// Returns `Ok(None)` when nothing is healable — either the index matches
/// LMDB, or the only gap is the documented sanitization-skip reserve
/// (gate-failing content that every rebuild re-skips; healing those
/// galaxies would be pure churn). Use [`repair_content`] to shrink the
/// reserve itself.
pub fn heal_index_drift(
    store: &MemoryStore,
    search: &SearchEngine,
) -> Result<Option<IndexRebuildReport>> {
    // Classify, don't just count: galaxies whose entire gap is the
    // documented sanitization-skip reserve reproduce the same index on
    // every rebuild — re-healing them each startup is pure churn. Only a
    // nonzero healable gap (missing indexable docs, or orphans) triggers.
    let class = classify_drift(store, search);
    let drifted: Vec<String> = class
        .galaxies
        .iter()
        .filter(|g| g.healable_gap != 0)
        .map(|g| g.galaxy.clone())
        .collect();
    if drifted.is_empty() {
        return Ok(None);
    }

    let mut report = IndexRebuildReport::default();
    let mut writer = search.writer()?;
    for name in &drifted {
        let Some(galaxy) = Galaxy::from_db_name(name) else {
            return Err(CoreError::Memory(format!(
                "drift classification named a non-memory galaxy: {name}"
            )));
        };
        let mut stats = GalaxyRebuildStats {
            galaxy: name.clone(),
            ..GalaxyRebuildStats::default()
        };

        let indexed_ids = search.indexed_ids_in_galaxy(name)?;
        let mut lmdb_ids: std::collections::HashSet<String> =
            std::collections::HashSet::with_capacity(indexed_ids.len());
        for mem in store.scan_all(galaxy)? {
            let id = mem.metadata.id.to_string();
            lmdb_ids.insert(id.clone());
            if !indexed_ids.contains(&id) {
                stats.scanned += 1;
                if index_memory(search, &mut writer, galaxy, &mem)?.is_some() {
                    stats.indexed += 1;
                } else {
                    // Gate-failing content: counted as the documented
                    // skip-reserve, never indexed. `classify_drift` moves it
                    // out of the healable gap on the next pass, so this is
                    // not churn.
                    stats.skipped += 1;
                }
            }
        }
        // Orphans: indexed docs whose LMDB twin is gone (failed delete,
        // interrupted run). Remove them so counts converge.
        for id in &indexed_ids {
            if !lmdb_ids.contains(id) {
                search.delete_document(&mut writer, id)?;
                stats.deleted += 1;
            }
        }

        report.scanned += stats.scanned;
        report.indexed += stats.indexed;
        report.skipped += stats.skipped;
        report.deleted += stats.deleted;
        report.galaxies.push(stats);
    }

    search.commit(&mut writer)?;
    drop(writer);
    Ok(Some(report))
}

// ── Content repair ─────────────────────────────────────────────────────

/// Per-galaxy content-repair stats.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct GalaxyContentRepairStats {
    /// Galaxy database name.
    pub galaxy: String,
    /// Memories scanned.
    pub scanned: usize,
    /// Rows rewritten in place with gate-passing content and indexed.
    pub repaired: usize,
    /// Majority-binary content left untouched (scrubbing would only
    /// manufacture searchable noise).
    pub unrepairable: usize,
    /// Memories that already passed the gate — untouched.
    pub already_clean: usize,
}

/// Content-repair report.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ContentRepairReport {
    /// Memories scanned across all targeted galaxies.
    pub scanned: usize,
    /// Rows rewritten in place and indexed.
    pub repaired: usize,
    /// True-binary rows left as-is (the permanent reserve).
    pub unrepairable: usize,
    /// Rows that already passed the gate.
    pub already_clean: usize,
    /// Per-galaxy breakdown.
    pub galaxies: Vec<GalaxyContentRepairStats>,
}

/// Clean content for a repair attempt: control characters → spaces
/// (mirroring `scrub_text`'s keep-set) WITHOUT the index length cap — the
/// stored content stays full-length; only the index caps.
fn clean_for_repair(content: &str) -> String {
    content
        .chars()
        .map(|c| {
            if c.is_control() && c != '\n' && c != '\t' && c != '\r' {
                ' '
            } else {
                c
            }
        })
        .collect()
}

/// Repair gate-failing memory content **in place** (V8 drift fix, part 2).
///
/// For every memory whose content fails [`sanitize_content_for_index`], the
/// cleaner replaces control characters with spaces and re-runs the gate;
/// rows that pass are rewritten under the SAME id (content + recomputed
/// content_hash — `store.put` refreshes the secondary indexes) and indexed.
/// In-place is deliberate: the B5 recovery's alongside-copies are what
/// created the standing reserve, and the raw originals remain recoverable
/// from the upstream heritage sources.
///
/// Majority-binary content (printable ratio < 0.5 before cleaning) is left
/// untouched: scrubbing it would only manufacture searchable noise. These
/// are the documented true-binary docs — the permanent reserve.
///
/// Indexing uses one writer and a single commit at the end; the caller
/// must hold the writer lock (no writable serve on the store). The report
/// gives exact per-galaxy counts; a fresh `wm backup` before applying is
/// the operator's responsibility.
///
/// # Errors
/// Propagates store/index errors; a mid-run failure leaves earlier
/// repairs committed only at the end (single transaction on the index;
/// LMDB rows are committed per-put — take a backup first).
pub fn repair_content(
    store: &MemoryStore,
    search: &SearchEngine,
    galaxies: &[Galaxy],
) -> Result<ContentRepairReport> {
    let mut report = ContentRepairReport::default();
    let mut writer = search.writer()?;
    for galaxy in galaxies {
        let mut stats = GalaxyContentRepairStats {
            galaxy: galaxy.db_name().to_string(),
            ..Default::default()
        };
        for mem in store.scan_all(*galaxy)? {
            stats.scanned += 1;
            if sanitize_content_for_index(&mem.content).is_some() {
                stats.already_clean += 1;
                continue;
            }
            // Majority-text rule: control-char scrubbing must not manufacture
            // searchable noise out of binary garbage.
            let total = mem.content.chars().count();
            let printable = mem.content.chars().filter(|c| !c.is_control()).count();
            let cleaned = clean_for_repair(&mem.content);
            if total == 0
                || (printable as f32 / total as f32) < 0.5
                || sanitize_content_for_index(&cleaned).is_none()
            {
                stats.unrepairable += 1;
                continue;
            }
            let mut repaired_mem = mem;
            let old_hash = repaired_mem.metadata.content_hash.clone();
            repaired_mem.content = cleaned;
            repaired_mem.metadata.content_hash = crate::content_hash(&repaired_mem.content);
            repaired_mem.metadata.revision_count =
                repaired_mem.metadata.revision_count.saturating_add(1);
            store.put(*galaxy, &repaired_mem)?;
            // V8 S11c: an operator repair IS a content change — chain it
            // like any update so `memory.revisions verify` stays truthful
            // afterwards instead of crying tamper on repaired docs.
            store.record_revision(
                *galaxy,
                repaired_mem.metadata.id,
                &old_hash,
                &repaired_mem.metadata.content_hash,
                crate::revision::RevisionActor {
                    session: None,
                    user: Some("wm-repair-content".to_string()),
                    compartment: None,
                },
            )?;
            let id_str = repaired_mem.metadata.id.to_string();
            // Defensive delete-then-add: gate-failing docs have no index
            // doc, but a prior partial repair could have left one.
            search.delete_document(&mut writer, &id_str)?;
            search.add_document(
                &mut writer,
                &id_str,
                galaxy.db_name(),
                &repaired_mem.content,
                &repaired_mem.metadata.tags,
                repaired_mem.metadata.created_at.timestamp(),
            )?;
            stats.repaired += 1;
        }
        report.scanned += stats.scanned;
        report.repaired += stats.repaired;
        report.unrepairable += stats.unrepairable;
        report.already_clean += stats.already_clean;
        report.galaxies.push(stats);
    }
    search.commit(&mut writer)?;
    Ok(report)
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
        assert_eq!(report.galaxies.len(), Galaxy::memory_galaxies().len());

        let ghost = search.search("ghost", 10).unwrap();
        assert!(ghost.is_empty(), "stale index entry must be purged");

        let rust = search.search("rust memory one", 10).unwrap();
        assert_eq!(rust.len(), 1);
        assert_eq!(rust[0].content, "rust memory one");
    }

    #[test]
    fn rebuild_refuses_undecodable_sources_before_touching_index() {
        let (_tmp, store, search) = setup();
        put_and_index(
            &store,
            &search,
            Galaxy::Codex,
            "preserved searchable evidence",
        );
        let id = uuid::Uuid::new_v4();
        store
            .put_raw(Galaxy::Sessions, id.as_bytes(), b"invalid messagepack")
            .unwrap();
        let before = search.count_docs_in_galaxy("codex").unwrap();
        assert!(rebuild_index(&store, &search, &[]).is_err());
        // Committing afterward also proves no deletion was left pending.
        let mut writer = search.writer().unwrap();
        search.commit(&mut writer).unwrap();
        assert_eq!(search.count_docs_in_galaxy("codex").unwrap(), before);
        assert_eq!(search.search("preserved", 10).unwrap().len(), 1);
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
        // Use galaxy-scoped search since OR semantics returns partial matches
        // for 2-term queries (both docs contain "memory").
        let codex = search
            .search_in_galaxy("codex memory", Some(Galaxy::Codex), 10)
            .unwrap();
        assert_eq!(codex.len(), 1);
        let research = search
            .search_in_galaxy("research memory", Some(Galaxy::Research), 10)
            .unwrap();
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
    fn heal_repairs_only_drifted_galaxies() {
        let (_tmp, store, search) = setup();

        // LMDB-only writes (the session-tool pattern) — never touch the index.
        store
            .put(
                Galaxy::Sessions,
                &Memory::new(Galaxy::Sessions, "session needle".into()),
            )
            .unwrap();
        store
            .put(
                Galaxy::Research,
                &Memory::new(Galaxy::Research, "research needle".into()),
            )
            .unwrap();
        // A healthy galaxy that must not be rebuilt.
        put_and_index(&store, &search, Galaxy::Codex, "healthy codex entry");

        let report = heal_index_drift(&store, &search)
            .unwrap()
            .expect("drift expected before heal");
        let healed: Vec<_> = report.galaxies.iter().map(|g| g.galaxy.as_str()).collect();
        assert!(healed.contains(&"sessions"));
        assert!(healed.contains(&"research"));
        assert!(
            !healed.contains(&"codex"),
            "healthy galaxy must be untouched"
        );
        assert_eq!(report.indexed, 2);

        assert!(
            heal_index_drift(&store, &search).unwrap().is_none(),
            "second heal must be a no-op once consistent"
        );
        assert_eq!(
            search
                .search_in_galaxy("session needle", Some(Galaxy::Sessions), 10)
                .unwrap()
                .len(),
            1
        );
        assert_eq!(
            search
                .search_in_galaxy("healthy codex", Some(Galaxy::Codex), 10)
                .unwrap()
                .len(),
            1
        );
    }

    #[test]
    fn heal_noop_when_consistent() {
        let (_tmp, store, search) = setup();
        put_and_index(&store, &search, Galaxy::Codex, "indexed entry");
        put_and_index(&store, &search, Galaxy::Dreams, "dream entry");

        assert!(heal_index_drift(&store, &search).unwrap().is_none());
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
    // ── Drift classification + content repair (V8 truthfulness fix) ────────

    #[test]
    fn classify_separates_skip_reserve_from_healable_drift() {
        let (tmp, store, search) = setup();
        // 2 clean docs indexed + 1 gate-failing doc NOT indexed.
        put_and_index(&store, &search, Galaxy::Codex, "clean doc one");
        put_and_index(&store, &search, Galaxy::Codex, "clean doc two");
        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "bad \u{1}\u{2} doc".into()),
            )
            .unwrap();
        search.commit(&mut search.writer().unwrap()).unwrap();

        let class = classify_drift(&store, &search);
        let codex = class.galaxies.iter().find(|g| g.galaxy == "codex").unwrap();
        assert_eq!(codex.lmdb_count, 3);
        assert_eq!(codex.tantivy_count, 2);
        assert_eq!(codex.skip_reserve, 1);
        assert_eq!(codex.healable_gap, 0, "skip reserve fully explains the gap");
        assert_eq!(class.healable_total, 0);
        drop(tmp);
    }

    #[test]
    fn classify_flags_missing_indexable_docs_as_healable() {
        let (tmp, store, search) = setup();
        put_and_index(&store, &search, Galaxy::Codex, "indexed doc");
        // A second clean doc that never reached the index — real drift.
        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "unindexed clean doc".into()),
            )
            .unwrap();
        search.commit(&mut search.writer().unwrap()).unwrap();

        let class = classify_drift(&store, &search);
        let codex = class.galaxies.iter().find(|g| g.galaxy == "codex").unwrap();
        assert_eq!(codex.skip_reserve, 0);
        assert_eq!(codex.healable_gap, 1);
        assert_eq!(class.healable_total, 1);
        drop(tmp);
    }

    #[test]
    fn heal_ignores_pure_skip_reserve_and_heals_real_gaps() {
        let (tmp, store, search) = setup();
        put_and_index(&store, &search, Galaxy::Codex, "clean doc");
        // Only a skip-reserve gap: heal must be a no-op (no churn).
        // The \0 makes this genuinely gate-failing (null byte → immediate refuse).
        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "gate\u{0} fails".into()),
            )
            .unwrap();
        search.commit(&mut search.writer().unwrap()).unwrap();
        let healed = heal_index_drift(&store, &search).unwrap();
        assert!(
            healed.is_none(),
            "skip-reserve-only drift must not trigger a rebuild"
        );

        // Now a real gap: an unindexed clean doc — heal must rebuild.
        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "genuinely missing doc".into()),
            )
            .unwrap();
        let healed = heal_index_drift(&store, &search).unwrap();
        assert!(healed.is_some(), "healable drift must trigger a heal");
        // Incremental heal touches only the delta: the already-indexed clean
        // doc is left alone, the missing doc is added, the \0 doc is in the
        // id diff, gets attempted, fails the gate and is counted skipped —
        // that is the whole point of the classification.
        let healed = healed.unwrap();
        assert_eq!(healed.indexed, 1);
        assert_eq!(healed.skipped, 1);
        assert_eq!(healed.deleted, 0);
        drop(tmp);
    }

    #[test]
    fn heal_indexes_only_the_missing_delta() {
        let (_tmp, store, search) = setup();
        // Two memories written straight to LMDB (the session-tool pattern).
        let a = Memory::new(Galaxy::Sessions, "alpha missing doc".into());
        let b = Memory::new(Galaxy::Sessions, "beta missing doc".into());
        store.put(Galaxy::Sessions, &a).unwrap();
        store.put(Galaxy::Sessions, &b).unwrap();

        // Heal once: both are missing, both get indexed.
        let report = heal_index_drift(&store, &search).unwrap().unwrap();
        assert_eq!(report.indexed, 2);
        assert_eq!(report.deleted, 0);
        assert_eq!(
            search
                .search_in_galaxy("alpha", Some(Galaxy::Sessions), 10)
                .unwrap()
                .len(),
            1
        );

        // One more LMDB-only write; the heal must index exactly the new one.
        store
            .put(
                Galaxy::Sessions,
                &Memory::new(Galaxy::Sessions, "gamma missing doc".into()),
            )
            .unwrap();
        let report = heal_index_drift(&store, &search).unwrap().unwrap();
        assert_eq!(report.indexed, 1, "only the delta is indexed");
        assert_eq!(
            search
                .search_in_galaxy("gamma", Some(Galaxy::Sessions), 10)
                .unwrap()
                .len(),
            1
        );
        // Prior docs still present exactly once.
        assert_eq!(
            search
                .search_in_galaxy("alpha", Some(Galaxy::Sessions), 10)
                .unwrap()
                .len(),
            1
        );
    }

    #[test]
    fn heal_deletes_orphan_index_docs() {
        let (_tmp, store, search) = setup();
        put_and_index(&store, &search, Galaxy::Codex, "legit doc");
        // Index an entry whose LMDB row is then removed outright (the
        // failed-delete / interrupted-run shape). NOTE: `store.delete` keeps
        // the key as a validity-state row, which count-based classification
        // deliberately ignores (a rebuild would re-index that row anyway);
        // only a raw key removal makes the index doc a true orphan.
        let orphan = Memory::new(Galaxy::Codex, "orphan doc".into());
        let orphan_id = orphan.metadata.id;
        store.put(Galaxy::Codex, &orphan).unwrap();
        {
            let mut writer = search.writer().unwrap();
            search
                .add_document(
                    &mut writer,
                    &orphan_id.to_string(),
                    "codex",
                    "orphan doc",
                    &orphan.metadata.tags,
                    orphan.metadata.created_at.timestamp(),
                )
                .unwrap();
            search.commit(&mut writer).unwrap();
        }
        store
            .delete_raw(Galaxy::Codex, orphan_id.as_bytes())
            .unwrap();
        assert_eq!(search.count_docs_in_galaxy("codex").unwrap(), 2);

        let report = heal_index_drift(&store, &search).unwrap().unwrap();
        assert_eq!(report.deleted, 1, "the orphan must be deleted");
        assert_eq!(report.indexed, 0);
        assert_eq!(search.count_docs_in_galaxy("codex").unwrap(), 1);
        // `search()` uses the delayed-reload reader (OnCommitWithDelay) —
        // count/enum reload eagerly, the text-search path does not by design.
        // Poll briefly instead of forcing a reload into the hot path.
        let mut gone = false;
        for _ in 0..40 {
            // "orphan" alone: an OR query with "doc" would match the legit
            // doc too (single-term coverage floor).
            if search.search("orphan", 10).unwrap().is_empty() {
                gone = true;
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
        assert!(gone, "orphan doc must be gone from search");
        assert!(heal_index_drift(&store, &search).unwrap().is_none());
    }

    #[test]
    fn repair_rewrites_in_place_and_indexes_clean_content() {
        let (tmp, store, search) = setup();
        // Repairable: majority text with a null byte (immediate gate refuse)
        // plus a control char — printable ratio ≥ 0.5.
        let mut repairable = Memory::new(
            Galaxy::Codex,
            "kumquat\u{0} ratchet \u{1} repair end".into(),
        );
        // True-binary: majority control chars — must be left untouched.
        let mut binary = Memory::new(Galaxy::Codex, "\u{1}\u{2}\u{3}\u{4}\u{5}\u{6}".into());
        // Already clean.
        let mut clean = Memory::new(Galaxy::Codex, "perfectly fine prose".into());
        let (id_r, id_b, id_c) = (
            repairable.metadata.id,
            binary.metadata.id,
            clean.metadata.id,
        );
        for m in [&mut repairable, &mut binary, &mut clean] {
            store.put(Galaxy::Codex, m).unwrap();
        }

        let report = repair_content(&store, &search, &[Galaxy::Codex]).unwrap();
        assert_eq!(report.scanned, 3);
        assert_eq!(report.repaired, 1, "{report:?}");
        assert_eq!(report.unrepairable, 1, "{report:?}");
        assert_eq!(report.already_clean, 1);

        // The repaired row kept its id, got clean content + fresh hash, and is
        // now gate-passing.
        let row = store.get(Galaxy::Codex, id_r).unwrap().unwrap();
        assert_eq!(row.content, "kumquat  ratchet   repair end");
        assert_eq!(row.metadata.content_hash, crate::content_hash(&row.content));
        assert!(sanitize_content_for_index(&row.content).is_some());
        assert_eq!(row.metadata.revision_count, 1);

        // V8 S11c: the repair chained itself — old hash preserved, operator
        // actor labeled, head verifies against the repaired content.
        let chain = store.revisions(Galaxy::Codex, id_r).unwrap();
        assert_eq!(chain.len(), 1);
        assert_eq!(
            chain[0].old_hash,
            crate::content_hash("kumquat\u{0} ratchet \u{1} repair end")
        );
        assert_eq!(chain[0].new_hash, row.metadata.content_hash);
        assert_eq!(chain[0].actor_user.as_deref(), Some("wm-repair-content"));
        assert_eq!(chain[0].actor_session, None);
        let verdict = store
            .verify_revision_chain(Galaxy::Codex, id_r, &row.metadata.content_hash)
            .unwrap();
        assert!(verdict.valid, "{:?}", verdict.breaks);

        // Untouched rows chained nothing.
        assert!(store.revisions(Galaxy::Codex, id_b).unwrap().is_empty());
        assert!(store.revisions(Galaxy::Codex, id_c).unwrap().is_empty());

        // True-binary row untouched.
        let untouched = store.get(Galaxy::Codex, id_b).unwrap().unwrap();
        assert_eq!(untouched.content, "\u{1}\u{2}\u{3}\u{4}\u{5}\u{6}");

        // Clean row untouched.
        let kept = store.get(Galaxy::Codex, id_c).unwrap().unwrap();
        assert_eq!(kept.content, "perfectly fine prose");

        // The repaired doc is now findable through the index.
        let hits = search.search("kumquat ratchet repair", 10).unwrap();
        assert!(
            hits.iter().any(|h| h.memory_id == id_r.to_string()),
            "repaired doc must be indexed: {hits:?}"
        );

        // Re-run: the repaired doc is already clean; nothing new happens.
        let again = repair_content(&store, &search, &[Galaxy::Codex]).unwrap();
        assert_eq!(again.repaired, 0);
        assert_eq!(again.already_clean, 2);
        assert_eq!(
            store.revisions(Galaxy::Codex, id_r).unwrap().len(),
            1,
            "idempotent re-run must not append"
        );
        drop(tmp);
    }
}
