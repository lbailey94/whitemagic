//! Invented fixture for retrieval-level abstention: a query with no qualifying
//! evidence returns an explicit `insufficient_evidence` status; answer-level
//! false-answer measurement is a separate concern and is not claimed here.
use serde_json::json;
use std::sync::Arc;
use wm_core::episodic::{EpisodicKind, EpisodicRecord, Provenance, ProvenanceSource};
use wm_core::{Context, Galaxy, Tool};
use wm_memory::{Memory, MemoryStore};
use wm_tools::expansion::MemoryHybridRecallTool;

#[tokio::test]
async fn absent_evidence_abstains_explicitly_and_present_evidence_does_not() {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    let tool = MemoryHybridRecallTool::as_search(store.clone(), None, None);

    let absent = tool
        .call(
            &mut Context::default(),
            json!({"query": "zxqabsentcontract", "limit": 5}),
        )
        .await
        .unwrap();
    assert_eq!(absent["count"], 0, "{absent}");
    assert_eq!(absent["abstention"]["status"], "insufficient_evidence");
    assert_eq!(absent["abstention"]["scope"], "retrieval");
    assert_eq!(absent["abstention"]["reason"], "no_results_above_floors");

    let mut memory = Memory::new(Galaxy::Research, "zxqpresentcontract body".to_string());
    memory.metadata.id = uuid::Uuid::from_u128(0x7e1);
    memory.metadata.importance = 0.9;
    store.put(Galaxy::Research, &memory).unwrap();
    let mut record = EpisodicRecord::new(
        Some(uuid::Uuid::from_u128(0x7e0)),
        1,
        EpisodicKind::UserStatement,
        "zxqpresentcontract body".to_string(),
        Provenance::new(ProvenanceSource::User),
    );
    record.id = memory.metadata.id;
    store.episodic().append(&record).unwrap();

    let present = tool
        .call(
            &mut Context::default(),
            json!({"query": "zxqpresentcontract", "limit": 5}),
        )
        .await
        .unwrap();
    assert_eq!(present["count"], 1, "{present}");
    assert!(
        present.get("abstention").is_none(),
        "present evidence must not abstain: {present}"
    );
}
