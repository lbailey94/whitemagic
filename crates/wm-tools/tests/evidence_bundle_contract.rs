//! Invented fixture for the v0 evidence bundle: exact identity, retrieval
//! reason, source time, integrity, visibility, and coverage per result.
use serde_json::json;
use std::sync::Arc;
use wm_core::episodic::{EpisodicKind, EpisodicRecord, Provenance, ProvenanceSource};
use wm_core::{Context, Galaxy, Tool};
use wm_memory::{Memory, MemoryStore};
use wm_tools::expansion::MemoryHybridRecallTool;

#[tokio::test]
async fn evidence_bundle_binds_each_result_to_its_source() {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    let mut memory = Memory::new(Galaxy::Research, "zxqbundlecontract body".to_string());
    memory.metadata.id = uuid::Uuid::from_u128(0x7f1);
    memory.metadata.importance = 0.9;
    store.put(Galaxy::Research, &memory).unwrap();
    let mut record = EpisodicRecord::new(
        Some(uuid::Uuid::from_u128(0x7f0)),
        1,
        EpisodicKind::UserStatement,
        "zxqbundlecontract body".to_string(),
        Provenance::new(ProvenanceSource::User),
    );
    record.id = memory.metadata.id;
    store.episodic().append(&record).unwrap();

    let response = MemoryHybridRecallTool::as_search(store.clone(), None, None)
        .call(
            &mut Context::default(),
            json!({"query": "zxqbundlecontract", "limit": 5}),
        )
        .await
        .unwrap();
    assert_eq!(response["count"], 1, "{response}");
    let bundle = &response["evidence_bundle"];
    assert_eq!(bundle["version"], "v0");
    assert_eq!(bundle["count"], 1);
    let entry = &bundle["entries"][0];
    assert_eq!(entry["id"], memory.metadata.id.to_string());
    assert_eq!(entry["galaxy"], "research");
    assert_eq!(entry["retrieval"]["route"], "episodic");
    assert!(entry["retrieval"]["score"].as_f64().is_some());
    assert_eq!(entry["source_time"]["basis"], "recorded_at");
    assert!(!entry["source_time"]["created_at"].is_null());
    assert_eq!(entry["integrity"], "source_read");
    assert_eq!(entry["visibility"]["private"], false);
    assert_eq!(entry["visibility"]["model_exclude"], false);
    assert_eq!(entry["coverage"]["representation"], "scrubbed_navigation");
    assert_eq!(entry["coverage"]["exact_read_available"], true);
}
