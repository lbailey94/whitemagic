//! Trust administration — survey and correct `source_trust` provenance.
//!
//! V8.1 groundwork (the trust-asymmetry watch item): `source_trust` exists
//! in the memory schema (default 1.0 = user-confirmed) but heritage ingests
//! were stamped with the defaults, so the corpus over-states trust — ~60k
//! ingested records read as user-confirmed. This module is the admin
//! surface: `survey` counts the corpus by provenance, `correct` re-stamps a
//! selected population (dry-run by default). The retrieval scorer consumes
//! the corrected values behind `WM_TRUST_WEIGHT` (evidence-gated: enable
//! after the recall benchmark re-run).
//!
//! Tantivy trust-field decision (V8 S8, closes the open question noted
//! here): **no indexed trust field.** `source_trust` stays LMDB metadata,
//! resolved per-candidate at fusion time via the store getter — one
//! source of truth, no index migration, and `wm trust correct` takes
//! effect on the next search without a reindex. A Tantivy field would
//! buy nothing at fleet scale and would silently split truth between
//! LMDB and the index after a correction. Revisit only if fusion ever
//! moves index-side.

use serde_json::{Value, json};
use wm_core::Galaxy;
use wm_memory::MemoryStore;

/// Per-galaxy, per-(source, trust) counts over the whole store.
///
/// LMDB-side and read-only; safe against a live server (the Tantivy index
/// is untouched — trust is not an indexed field).
pub fn survey(store: &MemoryStore) -> Value {
    let mut galaxies = Vec::new();
    let mut total = 0u64;
    for galaxy in Galaxy::memory_galaxies() {
        let memories = match store.scan_all(galaxy) {
            Ok(m) => m,
            Err(_) => continue,
        };
        if memories.is_empty() {
            continue;
        }
        let mut buckets: std::collections::BTreeMap<(String, String), u64> =
            std::collections::BTreeMap::new();
        for mem in &memories {
            let trust_bucket = format!("{:.1}", mem.metadata.source_trust);
            *buckets
                .entry((mem.metadata.source.clone(), trust_bucket))
                .or_insert(0) += 1;
        }
        total += memories.len() as u64;
        let rows: Vec<Value> = buckets
            .into_iter()
            .map(|((source, trust), count)| {
                json!({"source": source, "trust": trust, "count": count})
            })
            .collect();
        galaxies.push(json!({
            "galaxy": galaxy.db_name(),
            "memories": memories.len(),
            "by_source_trust": rows,
        }));
    }
    json!({
        "status": "success",
        "total_memories": total,
        "galaxies": galaxies,
        "note": "source_trust semantics: 1.0 user-confirmed, 0.7 tool-ingested neutral, lower = unverified. Correct heritage stamps before enabling WM_TRUST_WEIGHT."
    })
}

/// Selection criteria for a correction pass. Everything is optional; the
/// conjunction of provided filters selects the population.
#[derive(Debug, Clone, Default)]
pub struct CorrectionCriteria {
    /// Match memories whose `source` equals this value (e.g. "user").
    pub source: Option<String>,
    /// Restrict to one galaxy.
    pub galaxy: Option<Galaxy>,
    /// Only memories created before this RFC 3339 timestamp.
    pub created_before: Option<chrono::DateTime<chrono::Utc>>,
    /// Only memories carrying this tag.
    pub tag: Option<String>,
}

/// Report of a correction pass (dry-run or applied).
#[derive(Debug, Clone, serde::Serialize)]
pub struct CorrectionReport {
    pub dry_run: bool,
    pub set_trust: f32,
    pub matched: u64,
    pub updated: u64,
    /// First few affected ids so the operator can spot-check before applying.
    pub sample_ids: Vec<String>,
    pub per_galaxy: std::collections::BTreeMap<String, u64>,
}

/// Re-stamp `source_trust` on the selected population.
///
/// Metadata-only: content, timestamps and the Tantivy index (which does not
/// store trust) are untouched. Dry-run by construction — `apply` must be
/// passed by the caller.
pub fn correct(
    store: &MemoryStore,
    criteria: &CorrectionCriteria,
    set_trust: f32,
    apply: bool,
) -> Result<CorrectionReport, wm_core::CoreError> {
    let set_trust = set_trust.clamp(0.0, 1.0);
    let galaxies: Vec<Galaxy> = match criteria.galaxy {
        Some(g) => vec![g],
        None => Galaxy::memory_galaxies().to_vec(),
    };
    let mut report = CorrectionReport {
        dry_run: !apply,
        set_trust,
        matched: 0,
        updated: 0,
        sample_ids: Vec::new(),
        per_galaxy: std::collections::BTreeMap::new(),
    };
    for galaxy in galaxies {
        let memories = store.scan_all(galaxy)?;
        for mut mem in memories {
            if let Some(ref want) = criteria.source {
                if &mem.metadata.source != want {
                    continue;
                }
            }
            if let Some(before) = criteria.created_before {
                if mem.metadata.created_at >= before {
                    continue;
                }
            }
            if let Some(ref tag) = criteria.tag {
                if !mem.metadata.tags.contains(tag) {
                    continue;
                }
            }
            report.matched += 1;
            *report
                .per_galaxy
                .entry(galaxy.db_name().to_string())
                .or_insert(0) += 1;
            if report.sample_ids.len() < 5 {
                report.sample_ids.push(mem.metadata.id.to_string());
            }
            if apply {
                mem.metadata.source_trust = set_trust;
                store.put(galaxy, &mem)?;
                report.updated += 1;
            }
        }
    }
    Ok(report)
}

/// Sessions-galaxy archaeology probe (Phase 4.5): authorship and turn-shape
/// distribution over a store's session turns.
///
/// Feeds the provenance-truthfulness finding (agent turns stamped
/// `source="user"`) and the V9 attribution base layer.
pub fn sessions_profile(store: &MemoryStore) -> Value {
    use std::collections::BTreeMap;

    let mut by_author_type: BTreeMap<(String, String), u64> = BTreeMap::new();
    let mut by_type: BTreeMap<String, u64> = BTreeMap::new();
    let mut by_source: BTreeMap<String, u64> = BTreeMap::new();
    let mut by_agent: BTreeMap<String, u64> = BTreeMap::new();
    let mut json_turns = 0u64;
    let mut plain_turns = 0u64;
    let mut min_ts: Option<chrono::DateTime<chrono::Utc>> = None;
    let mut max_ts: Option<chrono::DateTime<chrono::Utc>> = None;
    let mut scanned = 0u64;

    let Ok(memories) = store.scan_all(Galaxy::Sessions) else {
        return json!({"status": "error", "message": "sessions galaxy unreadable"});
    };

    for mem in &memories {
        scanned += 1;
        *by_source.entry(mem.metadata.source.clone()).or_insert(0) += 1;
        *by_agent.entry(mem.metadata.agent_id.clone()).or_insert(0) += 1;
        min_ts = Some(match min_ts {
            None => mem.metadata.created_at,
            Some(t) => t.min(mem.metadata.created_at),
        });
        max_ts = Some(match max_ts {
            None => mem.metadata.created_at,
            Some(t) => t.max(mem.metadata.created_at),
        });

        let shape = serde_json::from_str::<Value>(&mem.content).ok();
        let turn_type = match &shape {
            Some(j) => j
                .get("turn_type")
                .or_else(|| j.get("type"))
                .and_then(Value::as_str)
                .unwrap_or("unlabeled_json")
                .to_string(),
            None => "plain".to_string(),
        };
        if shape.is_some() {
            json_turns += 1;
        } else {
            plain_turns += 1;
        }
        *by_type.entry(turn_type.clone()).or_insert(0) += 1;
        *by_author_type
            .entry((mem.metadata.agent_id.clone(), turn_type))
            .or_insert(0) += 1;
    }

    let author_rows: Vec<Value> = by_author_type
        .iter()
        .map(|((agent, turn_type), count)| {
            json!({"agent_id": agent, "turn_type": turn_type, "count": count})
        })
        .collect();
    let source_rows: Vec<Value> = by_source
        .iter()
        .map(|(s, c)| json!({"source": s, "count": c}))
        .collect();
    let type_rows: Vec<Value> = by_type
        .iter()
        .map(|(t, c)| json!({"turn_type": t, "count": c}))
        .collect();
    let agent_rows: Vec<Value> = by_agent
        .iter()
        .map(|(a, c)| json!({"agent_id": a, "count": c}))
        .collect();

    json!({
        "status": "success",
        "turns": scanned,
        "date_range": {
            "first": min_ts.map(|t| t.to_rfc3339()),
            "last": max_ts.map(|t| t.to_rfc3339()),
        },
        "content_shape": {"json_turns": json_turns, "plain_turns": plain_turns},
        "by_source": source_rows,
        "by_turn_type": type_rows,
        "by_agent": agent_rows,
        "by_agent_and_type": author_rows,
        "note": "Provenance finding: agent-authored turns carry source=user. Phase 4.5 proposes source=agent semantics for V9 lineage."
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_memory::Memory;

    fn test_store() -> (tempfile::TempDir, MemoryStore) {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, store)
    }

    fn put_mem(store: &MemoryStore, galaxy: Galaxy, content: &str, source: &str, trust: f32) {
        let mut mem = Memory::new(galaxy, content.to_string());
        mem.metadata.source = source.to_string();
        mem.metadata.source_trust = trust;
        store.put(galaxy, &mem).unwrap();
    }

    #[test]
    fn survey_counts_by_source_and_trust() {
        let (_dir, store) = test_store();
        put_mem(&store, Galaxy::Codex, "a", "user", 1.0);
        put_mem(&store, Galaxy::Codex, "b", "user", 1.0);
        put_mem(&store, Galaxy::Sessions, "c", "tool", 0.7);
        let report = survey(&store);
        assert_eq!(report["total_memories"], 3);
        let galaxies = report["galaxies"].as_array().unwrap();
        assert_eq!(galaxies.len(), 2, "only populated galaxies listed");
    }

    #[test]
    fn correct_dry_run_writes_nothing() {
        let (_dir, store) = test_store();
        put_mem(&store, Galaxy::Codex, "a", "user", 1.0);
        put_mem(&store, Galaxy::Codex, "b", "tool", 1.0);
        let criteria = CorrectionCriteria {
            source: Some("user".into()),
            galaxy: Some(Galaxy::Codex),
            ..Default::default()
        };
        let report = correct(&store, &criteria, 0.7, false).unwrap();
        assert_eq!(report.matched, 1);
        assert_eq!(report.updated, 0);
        assert!(report.dry_run);
        // The matched memory keeps its old trust.
        let mem = store.scan_all(Galaxy::Codex).unwrap();
        let a = mem.iter().find(|m| m.content == "a").unwrap();
        assert!((a.metadata.source_trust - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn correct_apply_restamps_only_selection() {
        let (_dir, store) = test_store();
        put_mem(&store, Galaxy::Codex, "heritage one", "user", 1.0);
        put_mem(&store, Galaxy::Codex, "heritage two", "user", 1.0);
        put_mem(&store, Galaxy::Codex, "real user note", "user", 1.0);
        put_mem(&store, Galaxy::Sessions, "session turn", "user", 1.0);
        let criteria = CorrectionCriteria {
            source: Some("user".into()),
            galaxy: Some(Galaxy::Codex),
            tag: Some("heritage".into()),
            ..Default::default()
        };
        // Tag the two heritage memories for selection.
        for content in ["heritage one", "heritage two"] {
            let mut all = store.scan_all(Galaxy::Codex).unwrap();
            let mut mem = all.remove(all.iter().position(|m| m.content == content).unwrap());
            mem.metadata.tags.push("heritage".into());
            store.put(Galaxy::Codex, &mem).unwrap();
        }
        let report = correct(&store, &criteria, 0.7, true).unwrap();
        assert_eq!(report.matched, 2);
        assert_eq!(report.updated, 2);
        let mems = store.scan_all(Galaxy::Codex).unwrap();
        for m in &mems {
            let expected = if m.content.starts_with("heritage") {
                0.7
            } else {
                1.0
            };
            assert!(
                (m.metadata.source_trust - expected).abs() < 1e-5,
                "{} should be {}",
                m.content,
                expected
            );
        }
        // Sessions galaxy untouched.
        let sessions = store.scan_all(Galaxy::Sessions).unwrap();
        assert!((sessions[0].metadata.source_trust - 1.0).abs() < 1e-5);
    }

    #[test]
    fn correct_clamps_trust() {
        let (_dir, store) = test_store();
        put_mem(&store, Galaxy::Codex, "x", "user", 1.0);
        let criteria = CorrectionCriteria {
            galaxy: Some(Galaxy::Codex),
            ..Default::default()
        };
        let report = correct(&store, &criteria, 5.0, true).unwrap();
        assert_eq!(report.updated, 1);
        let mems = store.scan_all(Galaxy::Codex).unwrap();
        assert!((mems[0].metadata.source_trust - 1.0).abs() < 1e-5);
    }
}
