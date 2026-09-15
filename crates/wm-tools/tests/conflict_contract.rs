//! Invented fixture: contradictory statements stay distinguishable, and the
//! evidence bundle surfaces the conflict pair instead of silently ranking one
//! of them away.
use serde_json::json;
use std::sync::Arc;
use wm_core::episodic::{EpisodicKind, EpisodicRecord, Provenance, ProvenanceSource};
use wm_core::{Context, Galaxy, Tool};
use wm_memory::{Memory, MemoryStore};
use wm_tools::expansion::MemoryHybridRecallTool;

fn put_statement(store: &MemoryStore, id: u128, content: &str, sequence: u64) {
    let mut memory = Memory::new(Galaxy::Research, content.to_string());
    memory.metadata.id = uuid::Uuid::from_u128(id);
    memory.metadata.importance = 0.9;
    store.put(Galaxy::Research, &memory).unwrap();
    let mut record = EpisodicRecord::new(
        Some(uuid::Uuid::from_u128(0x810)),
        sequence,
        EpisodicKind::UserStatement,
        content.to_string(),
        Provenance::new(ProvenanceSource::User),
    );
    record.id = memory.metadata.id;
    store.episodic().append(&record).unwrap();
}

#[tokio::test]
async fn conflicting_statements_stay_distinguishable_and_are_disclosed() {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    put_statement(
        &store,
        0x811,
        "zxqconflictcontract drink preference is espresso",
        1,
    );
    put_statement(
        &store,
        0x812,
        "zxqconflictcontract drink preference is no longer espresso",
        2,
    );

    let response = MemoryHybridRecallTool::as_search(store.clone(), None, None)
        .call(
            &mut Context::default(),
            json!({"query": "zxqconflictcontract", "limit": 10}),
        )
        .await
        .unwrap();
    assert_eq!(response["count"], 2, "{response}");
    let conflicts = &response["evidence_bundle"]["conflicts"];
    assert_eq!(conflicts["count"], 1, "{response}");
    let pair = &conflicts["pairs"][0];
    let ids: std::collections::HashSet<String> = [
        pair["later"].as_str().unwrap(),
        pair["earlier"].as_str().unwrap(),
    ]
    .into_iter()
    .map(str::to_string)
    .collect();
    assert!(ids.contains(&uuid::Uuid::from_u128(0x811).to_string()));
    assert!(ids.contains(&uuid::Uuid::from_u128(0x812).to_string()));
    assert!(!pair["marker"].as_str().unwrap().is_empty());
    assert!(!pair["shared_terms"].as_array().unwrap().is_empty());
}
