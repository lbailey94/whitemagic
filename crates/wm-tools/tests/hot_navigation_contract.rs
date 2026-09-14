//! Invented fixture for the hot-path navigation disclosure contract: search
//! excerpts declare their representation and bounds, and `memory.read`
//! remains the exact, complete-read path.
use serde_json::json;
use std::sync::Arc;
use wm_core::episodic::{EpisodicKind, EpisodicRecord, Provenance, ProvenanceSource};
use wm_core::{Context, Galaxy, Tool};
use wm_memory::{Memory, MemoryStore};
use wm_tools::{MemoryReadTool, expansion::MemoryHybridRecallTool};

const LONG_TOKEN: &str = "zxqnavlongcontract";
const SHORT_TOKEN: &str = "zxqnavshortcontract";

fn put_mirrored(store: &MemoryStore, id: u128, content: String) -> Memory {
    let mut memory = Memory::new(Galaxy::Research, content.clone());
    memory.metadata.id = uuid::Uuid::from_u128(id);
    memory.metadata.importance = 0.9;
    store.put(Galaxy::Research, &memory).unwrap();
    let mut record = EpisodicRecord::new(
        Some(uuid::Uuid::from_u128(0x7b0)),
        1,
        EpisodicKind::UserStatement,
        content,
        Provenance::new(ProvenanceSource::User),
    );
    record.id = memory.metadata.id;
    store.episodic().append(&record).unwrap();
    memory
}

#[tokio::test]
async fn hot_navigation_discloses_scrubbing_and_exact_read_stays_complete() {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    let long = format!(
        "{LONG_TOKEN}\u{0007} {}",
        "lorem ipsum dolor sit amet ".repeat(400)
    );
    let long_memory = put_mirrored(&store, 0x7a1, long.clone());
    let short = format!("{SHORT_TOKEN} short clean body");
    let short_memory = put_mirrored(&store, 0x7a2, short.clone());

    let search = MemoryHybridRecallTool::as_search(store.clone(), None, None);

    let long_response = search
        .call(
            &mut Context::default(),
            json!({"query": LONG_TOKEN, "limit": 5}),
        )
        .await
        .unwrap();
    let hit = &long_response["results"][0];
    assert_eq!(
        hit["id"],
        long_memory.metadata.id.to_string(),
        "{long_response}"
    );
    assert_eq!(hit["source"], "episodic");
    assert_eq!(hit["content_representation"], "scrubbed_navigation");
    assert_eq!(hit["content_character_limit"], 8192);
    assert_eq!(hit["content_truncated"], true);
    assert_eq!(hit["content_scrubbed"], true);
    assert_eq!(hit["exact_read_available"], true);
    let navigation = hit["content"].as_str().unwrap();
    assert_eq!(navigation.chars().count(), 8192);
    assert!(!navigation.contains('\u{0007}'));

    let read = MemoryReadTool::new(store.clone())
        .call(
            &mut Context::default(),
            json!({"id": hit["id"], "galaxy": hit["galaxy"]}),
        )
        .await
        .unwrap();
    assert_eq!(
        read["content"].as_str().unwrap().as_bytes(),
        long.as_bytes()
    );

    let short_response = search
        .call(
            &mut Context::default(),
            json!({"query": SHORT_TOKEN, "limit": 5}),
        )
        .await
        .unwrap();
    let hit = &short_response["results"][0];
    assert_eq!(
        hit["id"],
        short_memory.metadata.id.to_string(),
        "{short_response}"
    );
    assert_eq!(hit["content_representation"], "scrubbed_navigation");
    assert_eq!(hit["content_truncated"], false);
    assert_eq!(hit["content_scrubbed"], false);
    assert_eq!(hit["content"].as_str().unwrap(), short.as_str());

    let browse = search
        .call(
            &mut Context::default(),
            json!({"limit": 5, "galaxy": "research"}),
        )
        .await
        .unwrap();
    let first = &browse["results"][0];
    assert_eq!(first["content_representation"], "verbatim");
    assert_eq!(first["content_truncated"], false);
    assert_eq!(first["content_scrubbed"], false);
    assert_eq!(first["exact_read_available"], true);
}
