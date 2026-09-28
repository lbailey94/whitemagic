//! Invented fixture: a corrected fact keeps its history reconstructible and the
//! answer evidence discloses supersession and the absence of event-time tracking.
use serde_json::json;
use std::sync::Arc;
use wm_core::episodic::{EpisodicKind, EpisodicRecord, Provenance, ProvenanceSource};
use wm_core::{Context, Galaxy, Tool};
use wm_memory::revision::RevisionActor;
use wm_memory::{Memory, MemoryStore};
use wm_tools::{MemoryReadTool, expansion::MemoryHybridRecallTool};

#[tokio::test]
async fn corrected_fact_stays_reconstructible_and_disclosed() {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    let mut current = Memory::new(
        Galaxy::Research,
        "zxqtemporalcontract drink is tea".to_string(),
    );
    current.metadata.id = uuid::Uuid::from_u128(0x801);
    current.metadata.importance = 0.9;
    store.put(Galaxy::Research, &current).unwrap();
    let mut record = EpisodicRecord::new(
        Some(uuid::Uuid::from_u128(0x800)),
        1,
        EpisodicKind::UserStatement,
        "zxqtemporalcontract drink is tea".to_string(),
        Provenance::new(ProvenanceSource::User),
    );
    record.id = current.metadata.id;
    store.episodic().append(&record).unwrap();

    let original = Memory::new(
        Galaxy::Research,
        "zxqtemporalcontract drink is coffee".to_string(),
    );
    let intermediate = Memory::new(
        Galaxy::Research,
        "zxqtemporalcontract drink is matcha".to_string(),
    );
    for (old, new) in [
        (
            &original.metadata.content_hash,
            &intermediate.metadata.content_hash,
        ),
        (
            &intermediate.metadata.content_hash,
            &current.metadata.content_hash,
        ),
    ] {
        store
            .record_revision(
                Galaxy::Research,
                current.metadata.id,
                old,
                new,
                RevisionActor::default(),
            )
            .unwrap();
    }
    let chain = store
        .revisions(Galaxy::Research, current.metadata.id)
        .unwrap();
    assert_eq!(chain.len(), 2);
    assert!(wm_memory::revision::verify_chain(&chain, &current.metadata.content_hash).valid);

    let response = MemoryHybridRecallTool::as_search(store.clone(), None, None)
        .call(
            &mut Context::default(),
            json!({"query": "zxqtemporalcontract", "limit": 5}),
        )
        .await
        .unwrap();
    assert_eq!(response["count"], 1, "{response}");
    let entry = &response["evidence_bundle"]["entries"][0];
    assert_eq!(entry["history"]["revision_count"], 2);
    assert_eq!(entry["history"]["superseded"], true);
    assert_eq!(entry["history"]["chain_valid"], true);
    assert_eq!(entry["history"]["current"], true);
    assert!(entry["source_time"]["event_time"].is_null());
    assert_eq!(entry["source_time"]["event_time_basis"], "not_tracked");
    assert_eq!(entry["source_time"]["basis"], "recorded_at");

    assert_eq!(chain[0].old_hash, original.metadata.content_hash);
    assert_eq!(chain[1].old_hash, intermediate.metadata.content_hash);
    let read = MemoryReadTool::new(store.clone())
        .call(
            &mut Context::default(),
            json!({"id": current.metadata.id, "galaxy": "research"}),
        )
        .await
        .unwrap();
    assert_eq!(read["content"], "zxqtemporalcontract drink is tea");
}

/// V9.3: a declared event time and fold provenance are disclosed as
/// declared — never silently upgraded from `not_tracked`, never inferred.
#[tokio::test]
async fn declared_event_time_and_fold_provenance_are_disclosed() {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    let source = Memory::new(Galaxy::Research, "zxqfoldsource raw detail".to_string());
    let source_id = source.metadata.id;
    store.put(Galaxy::Research, &source).unwrap();
    let when = chrono::DateTime::parse_from_rfc3339("2026-09-27T10:00:00Z")
        .unwrap()
        .with_timezone(&chrono::Utc);
    let mut folded = Memory::new(Galaxy::Research, "zxqfoldsource folded summary".to_string())
        .with_event_time(when)
        .with_fold(wm_memory::FoldLevel::L2, vec![source_id]);
    folded.metadata.importance = 0.9;
    let folded_id = folded.metadata.id;
    store.put(Galaxy::Research, &folded).unwrap();
    // The episodic route (no embedder, no search engine) reads the raw
    // lane; mirror the folded record there like every write path does.
    let mut record = EpisodicRecord::new(
        None,
        1,
        EpisodicKind::Observation,
        "zxqfoldsource folded summary".to_string(),
        Provenance::new(ProvenanceSource::Agent),
    );
    record.id = folded_id;
    store.episodic().append(&record).unwrap();

    let response = MemoryHybridRecallTool::as_search(store.clone(), None, None)
        .call(
            &mut Context::default(),
            json!({"query": "zxqfoldsource", "limit": 5}),
        )
        .await
        .unwrap();
    let entries = response["evidence_bundle"]["entries"].as_array().unwrap();
    let entry = entries
        .iter()
        .find(|e| e["id"] == folded_id.to_string())
        .unwrap_or_else(|| panic!("folded hit missing from evidence: {response}"));
    assert_eq!(entry["source_time"]["event_time_basis"], "declared");
    assert!(
        entry["source_time"]["event_time"]
            .as_str()
            .unwrap()
            .starts_with("2026-09-27T10:00:00"),
        "{entry}"
    );
    assert_eq!(entry["fold"]["level"], "l2");
    assert_eq!(entry["fold"]["derived_from"][0], source_id.to_string());

    let read = MemoryReadTool::new(store.clone())
        .call(
            &mut Context::default(),
            json!({"id": folded_id, "galaxy": "research"}),
        )
        .await
        .unwrap();
    assert_eq!(read["fold_level"], "l2");
    assert_eq!(read["derived_from"][0], source_id.to_string());
}
