//! Invented fixture: lossless session replay never surfaces private or
//! model-excluded records (Q07 residual — exclusion is by construction in the
//! replay scan, this pins it with a named test).
use serde_json::json;
use std::sync::Arc;
use wm_core::{Context, Galaxy, Tool};
use wm_memory::{Memory, MemoryStore};
use wm_tools::expansion::SessionReplayTool;

fn session_turn(session: uuid::Uuid, sequence: u64, content: &str) -> String {
    let sequence_i = i64::try_from(sequence).unwrap_or(0);
    json!({
        "type": "session_turn",
        "session_id": session.to_string(),
        "sequence": sequence,
        "timestamp": 1_700_000_000i64 + sequence_i,
        "content": content,
        "role": "user",
        "turn_type": "message",
        "importance": 0.5
    })
    .to_string()
}

#[tokio::test]
async fn lossless_replay_excludes_private_records() {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    let session = uuid::Uuid::from_u128(0x5E55_1000);

    // Start record: id == session_id with the "start" tag (the scan anchors on it).
    let mut start = Memory::new(Galaxy::Sessions, session_turn(session, 0, "session start"));
    start.metadata.id = session;
    start.metadata.tags = vec!["start".to_string(), format!("session:{session}")];
    store.put(Galaxy::Sessions, &start).unwrap();

    // Visible turn.
    let mut visible = Memory::new(
        Galaxy::Sessions,
        session_turn(session, 1, "visible turn content"),
    );
    visible.metadata.id = uuid::Uuid::from_u128(0x5E55_1001);
    visible.metadata.tags = vec!["turn".to_string(), format!("session:{session}")];
    store.put(Galaxy::Sessions, &visible).unwrap();

    // Private turn — must never surface in replay.
    let mut private = Memory::new(
        Galaxy::Sessions,
        session_turn(session, 2, "private turn content"),
    );
    private.metadata.id = uuid::Uuid::from_u128(0x5E55_1002);
    private.metadata.tags = vec!["turn".to_string(), format!("session:{session}")];
    private.metadata.is_private = true;
    store.put(Galaxy::Sessions, &private).unwrap();

    // Model-excluded turn — same exclusion.
    let mut excluded = Memory::new(
        Galaxy::Sessions,
        session_turn(session, 3, "excluded turn content"),
    );
    excluded.metadata.id = uuid::Uuid::from_u128(0x5E55_1003);
    excluded.metadata.tags = vec!["turn".to_string(), format!("session:{session}")];
    excluded.metadata.model_exclude = true;
    store.put(Galaxy::Sessions, &excluded).unwrap();

    let tool = SessionReplayTool::new(store.clone());
    let response = tool
        .call(
            &mut Context::default(),
            json!({"mode": "lossless", "session_id": session.to_string()}),
        )
        .await
        .unwrap();

    let text = response.to_string();
    assert!(text.contains("visible turn content"), "{response}");
    assert!(
        !text.contains("private turn content"),
        "private records must never surface in lossless replay: {response}"
    );
    assert!(
        !text.contains("excluded turn content"),
        "model-excluded records must never surface in lossless replay: {response}"
    );
    assert_eq!(
        response["records"].as_array().unwrap().len(),
        2,
        "only the start and visible turns are replayed: {response}"
    );
}
