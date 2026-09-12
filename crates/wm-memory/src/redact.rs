//! Store-wide credential redaction retrofit.
//!
//! `wm ingest --redact` redacts at ingest time, but content written before
//! that flag existed (or by other write paths) can carry credential-shaped
//! spans. A ledger entry makes the source file "unchanged", so a re-ingest
//! cannot re-scrub it: the stored rows themselves must be rewritten.
//!
//! This pass mirrors [`crate::reindex::repair_content`]: matching rows are
//! rewritten under the SAME id (content + recomputed content_hash) through
//! `MemoryStore::put`, chained into the revision history as a content change,
//! and delete-then-add reindexed. `apply = false` reports without writing.
//!
//! The caller must hold the writer lock (no writable serve on the store);
//! a fresh `wm backup` before applying is the operator's responsibility.

// The writer must stay alive for the whole pass (one commit at the end);
// tightening its drop scope mid-scan is exactly what the lint suggests and
// exactly what would release the index lock early.
#![allow(clippy::significant_drop_tightening)]

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::credentials::redact_credential_content;
use crate::{MemoryStore, SearchEngine};
use wm_core::{Galaxy, Result};

/// Per-galaxy redaction outcome.
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct GalaxyRedactStats {
    pub galaxy: String,
    pub scanned: usize,
    pub redacted: usize,
    pub already_clean: usize,
    pub filtered_out: usize,
}

/// Aggregate redaction outcome.
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct RedactReport {
    pub scanned: usize,
    pub redacted: usize,
    pub already_clean: usize,
    pub filtered_out: usize,
    /// Credential kind → number of memories in which it fired.
    pub kinds: BTreeMap<String, usize>,
    pub galaxies: Vec<GalaxyRedactStats>,
}

/// Redact credential-shaped spans across `galaxies`.
///
/// When `tag_filter` is set, only memories carrying that exact tag are
/// considered (all others count as `filtered_out`). When `apply` is false,
/// the pass classifies and reports without writing or reindexing anything.
///
/// # Errors
/// Propagates store/index errors; LMDB rows commit per-put and the index
/// commits once at the end (take a backup before applying).
pub fn redact_store_content(
    store: &MemoryStore,
    search: &SearchEngine,
    galaxies: &[Galaxy],
    tag_filter: Option<&str>,
    apply: bool,
) -> Result<RedactReport> {
    let mut report = RedactReport::default();
    let mut writer = if apply { Some(search.writer()?) } else { None };

    for galaxy in galaxies {
        let mut stats = GalaxyRedactStats {
            galaxy: galaxy.db_name().to_string(),
            ..Default::default()
        };

        for mut mem in store.scan_all(*galaxy)? {
            stats.scanned += 1;

            if let Some(tag) = tag_filter {
                if !mem.metadata.tags.iter().any(|t| t == tag) {
                    stats.filtered_out += 1;
                    continue;
                }
            }

            let (scrubbed, kinds) = redact_credential_content(&mem.content);
            if kinds.is_empty() {
                stats.already_clean += 1;
                continue;
            }

            stats.redacted += 1;
            for kind in kinds {
                *report.kinds.entry(kind.to_string()).or_default() += 1;
            }

            let Some(writer) = writer.as_mut() else {
                continue;
            };

            let old_hash = mem.metadata.content_hash.clone();
            mem.content = scrubbed;
            mem.metadata.content_hash = crate::content_hash(&mem.content);
            mem.metadata.revision_count = mem.metadata.revision_count.saturating_add(1);
            store.put(*galaxy, &mem)?;
            store.record_revision(
                *galaxy,
                mem.metadata.id,
                &old_hash,
                &mem.metadata.content_hash,
                crate::revision::RevisionActor {
                    session: None,
                    user: Some("wm-redact-content".to_string()),
                    compartment: None,
                },
            )?;
            let id_str = mem.metadata.id.to_string();
            search.delete_document(writer, &id_str)?;
            search.add_document(
                writer,
                &id_str,
                galaxy.db_name(),
                &mem.content,
                &mem.metadata.tags,
                mem.metadata.created_at.timestamp(),
            )?;
        }

        report.scanned += stats.scanned;
        report.redacted += stats.redacted;
        report.already_clean += stats.already_clean;
        report.filtered_out += stats.filtered_out;
        report.galaxies.push(stats);
    }

    if let Some(mut writer) = writer {
        search.commit(&mut writer)?;
    }

    Ok(report)
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

    fn put_tagged(
        store: &MemoryStore,
        search: &SearchEngine,
        galaxy: Galaxy,
        content: &str,
        tags: &[&str],
    ) -> uuid::Uuid {
        let mut mem = Memory::new(galaxy, content.to_string());
        mem.metadata.tags = tags.iter().map(std::string::ToString::to_string).collect();
        mem.metadata.content_hash = crate::content_hash(content);
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
        id
    }

    #[test]
    fn dry_run_reports_without_writing() {
        let (_tmp, store, search) = setup();
        let secret = "db password=correct-horse-battery-staple";
        let id = put_tagged(&store, &search, Galaxy::Research, secret, &["source:test"]);

        let report =
            redact_store_content(&store, &search, &[Galaxy::Research], None, false).unwrap();
        assert_eq!(report.redacted, 1);
        assert_eq!(report.already_clean, 0);
        assert!(report.kinds.contains_key("credential_assignment"));

        let mem = store.get(Galaxy::Research, id).unwrap().unwrap();
        assert_eq!(mem.content, secret, "dry run must not write");
        assert_eq!(mem.metadata.revision_count, 0);
    }

    #[test]
    fn apply_redacts_in_place_reindexes_and_is_idempotent() {
        let (_tmp, store, search) = setup();
        put_tagged(
            &store,
            &search,
            Galaxy::Research,
            "db password=correct-horse-battery-staple",
            &["source:test"],
        );
        put_tagged(
            &store,
            &search,
            Galaxy::Research,
            "harmless notes about password rotation policy",
            &["source:test"],
        );

        let report =
            redact_store_content(&store, &search, &[Galaxy::Research], None, true).unwrap();
        assert_eq!(report.redacted, 1);
        assert_eq!(report.already_clean, 1);

        let mems = store.scan_all(Galaxy::Research).unwrap();
        let redacted = mems
            .iter()
            .find(|m| m.content.contains("[REDACTED:credential_assignment]"))
            .expect("redacted memory must exist");
        assert!(!redacted.content.contains("correct-horse-battery-staple"));
        assert_eq!(redacted.metadata.revision_count, 1);
        let clean = mems
            .iter()
            .find(|m| m.content.contains("harmless notes"))
            .expect("clean memory must survive untouched");
        assert_eq!(clean.metadata.revision_count, 0);

        let hits = search.search("REDACTED", 5).unwrap();
        assert!(!hits.is_empty(), "reindex must expose the redacted marker");

        // Second pass is a no-op.
        let second =
            redact_store_content(&store, &search, &[Galaxy::Research], None, true).unwrap();
        assert_eq!(second.redacted, 0);
        assert_eq!(second.already_clean, 2);
    }

    #[test]
    fn tag_filter_scopes_the_retrofit() {
        let (_tmp, store, search) = setup();
        put_tagged(
            &store,
            &search,
            Galaxy::Sessions,
            "token sk-proj0123456789abcdefghijklmnopqrstuv",
            &["source:harvest-a"],
        );
        put_tagged(
            &store,
            &search,
            Galaxy::Sessions,
            "token sk-projabcdefghijklmnopqrstuv0123456789",
            &["source:harvest-b"],
        );

        let report = redact_store_content(
            &store,
            &search,
            &[Galaxy::Sessions],
            Some("source:harvest-a"),
            true,
        )
        .unwrap();
        assert_eq!(report.scanned, 2);
        assert_eq!(report.filtered_out, 1);
        assert_eq!(report.redacted, 1);

        let mems = store.scan_all(Galaxy::Sessions).unwrap();
        let untouched = mems
            .iter()
            .find(|m| m.metadata.tags.iter().any(|t| t == "source:harvest-b"))
            .expect("untagged memory must survive");
        assert!(
            untouched
                .content
                .contains("sk-projabcdefghijklmnopqrstuv0123456789")
        );
    }
}
