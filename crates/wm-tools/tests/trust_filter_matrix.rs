//! Invented matrix: the explicit trust floor (`min_trust`) behaves identically
//! across both retrieval verbs and every result phase, and fails closed.
use serde_json::json;
use std::sync::Arc;
use wm_core::episodic::{EpisodicKind, EpisodicRecord, Provenance, ProvenanceSource};
use wm_core::{Context, Galaxy, Tool};
use wm_memory::{Association, AssociationStore, LinkType, Memory, MemoryStore};
use wm_tools::expansion::MemoryHybridRecallTool;

const HIGH: &str = "zxqtrusthighcontract";
const LOW: &str = "zxqtrustlowcontract";
const NEIGHBOR: &str = "zxqtrustneighborcontract";

fn put_mirrored(store: &MemoryStore, id: u128, content: &str, trust: f32) -> Memory {
    let mut memory = Memory::new(Galaxy::Research, content.to_string());
    memory.metadata.id = uuid::Uuid::from_u128(id);
    memory.metadata.importance = 0.9;
    memory.metadata.source_trust = trust;
    store.put(Galaxy::Research, &memory).unwrap();
    let mut record = EpisodicRecord::new(
        Some(uuid::Uuid::from_u128(0x7c0)),
        1,
        EpisodicKind::UserStatement,
        content.to_string(),
        Provenance::new(ProvenanceSource::User),
    );
    record.id = memory.metadata.id;
    store.episodic().append(&record).unwrap();
    memory
}

#[tokio::test]
async fn trust_floor_filters_consistently_across_verbs_and_phases() {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    let high = put_mirrored(&store, 0x7d1, HIGH, 0.9);
    put_mirrored(&store, 0x7d2, LOW, 0.1);
    let neighbor = put_mirrored(&store, 0x7d3, NEIGHBOR, 0.1);

    let associations = Arc::new(AssociationStore::open(store.env()).unwrap());
    associations
        .put(
            store.env(),
            &Association::new(
                high.metadata.id,
                neighbor.metadata.id,
                LinkType::Related,
                0.9,
            ),
        )
        .unwrap();

    let verbs = [
        MemoryHybridRecallTool::as_search(store.clone(), None, None)
            .with_associations(Some(associations.clone())),
        MemoryHybridRecallTool::new(store.clone(), None, None)
            .with_associations(Some(associations.clone())),
    ];
    for tool in &verbs {
        let all = tool
            .call(&mut Context::default(), json!({"query": HIGH, "limit": 10}))
            .await
            .unwrap();
        assert_eq!(all["count"], 2, "{all}");
        assert_eq!(all["results"][0]["id"], high.metadata.id.to_string());
        let neighbor_hit = all["results"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["id"] == neighbor.metadata.id.to_string())
            .expect("association neighbor must surface without a floor");
        let neighbor_trust = neighbor_hit["trust"].as_f64().unwrap();
        assert!((neighbor_trust - 0.1).abs() < 1e-6, "{neighbor_hit}");

        let floored = tool
            .call(
                &mut Context::default(),
                json!({"query": HIGH, "limit": 10, "min_trust": 0.5}),
            )
            .await
            .unwrap();
        assert_eq!(floored["count"], 1, "{floored}");
        assert_eq!(floored["min_trust_filtered"], 1, "{floored}");
        assert_eq!(floored["results"][0]["id"], high.metadata.id.to_string());

        let low_only = tool
            .call(
                &mut Context::default(),
                json!({"query": LOW, "limit": 10, "min_trust": 0.5}),
            )
            .await
            .unwrap();
        assert_eq!(low_only["count"], 0, "{low_only}");
        assert_eq!(low_only["min_trust_filtered"], 1, "{low_only}");
    }

    let browse = MemoryHybridRecallTool::as_search(store.clone(), None, None)
        .call(
            &mut Context::default(),
            json!({"limit": 10, "galaxy": "research", "min_trust": 0.5}),
        )
        .await
        .unwrap();
    assert_eq!(browse["count"], 1, "{browse}");
    assert_eq!(browse["min_trust_filtered"], 2, "{browse}");
    assert_eq!(browse["results"][0]["id"], high.metadata.id.to_string());
    for entry in browse["results"].as_array().unwrap() {
        assert!(entry.get("trust").is_some(), "unstamped result: {entry}");
    }
}
