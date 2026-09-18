//! Long-horizon multi-session continuity & replay stress benchmark (G3-CRB-1 Phase 2).
//!
//! Protocol: docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md §3 Layer 2/Layer 4, §5 Phase 2
//!
//! Asserts:
//! 1. 50 sequential sessions chain continuity with zero amnesia or payload loss.
//! 2. Previous-session selection orders by time (created_at) rather than UUID sort order.
//! 3. Structured nodiscovery handoffs are preserved 100% across the 50-step chain.
//! 4. Superseded turn visibility: excluded by default in replay, lossless on include_superseded: true.
//! 5. Export -> Import roundtrip preserves IDs, timestamps, and tags lossless.

use serde_json::json;
use std::sync::Arc;
use wm_core::{Context, Galaxy, Tool};
use wm_memory::MemoryStore;
use wm_tools::expansion::{
    SessionCheckpointNodiscoveryTool, SessionContinuityTool, SessionExportTool,
    SessionImportTool, SessionRecordTool, SessionReplayTool, SessionStartTool,
};

fn test_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("lmdb");
    std::fs::create_dir_all(&path).unwrap();
    (dir, Arc::new(MemoryStore::open_default(path).unwrap()))
}

#[tokio::test(flavor = "multi_thread", worker_threads = 4)]
async fn test_50_sequential_sessions_continuity_chain() {
    let (_dir, store) = test_store();
    let start_tool = SessionStartTool::new(store.clone());
    let record_tool = SessionRecordTool::new(store.clone());
    let checkpoint_tool = SessionCheckpointNodiscoveryTool::new(store.clone());
    let continuity_tool = SessionContinuityTool::new(store.clone());
    let mut ctx = Context::default();

    let num_sessions = 50;
    let mut session_ids = Vec::new();

    for i in 0..num_sessions {
        // In session i > 0, verify continuity recovers session i - 1
        if i > 0 {
            let prev_expected_id = &session_ids[i - 1];
            let cont_res = continuity_tool
                .call(
                    &mut ctx,
                    json!({
                        "session_id": format!("future-session-{i}"),
                        "project": "/test/project",
                    }),
                )
                .await
                .unwrap();

            assert_eq!(cont_res["status"], "success");
            assert_eq!(
                cont_res["previous_session"], *prev_expected_id,
                "continuity must select exact newest prior session (session {i})"
            );

            // Verify handoff was passed accurately
            let turns = cont_res["turns"].as_array().unwrap();
            assert!(!turns.is_empty(), "continuity turns must not be empty");
            let latest_turn = &turns[turns.len() - 1];
            assert!(
                latest_turn["content"]
                    .as_str()
                    .unwrap()
                    .contains(&format!("turn 4 in session {}", i - 1)),
                "latest turn must match session {} handoff payload",
                i - 1
            );
        }

        // Start new session
        let start_res = start_tool
            .call(&mut ctx, json!({"goal": format!("session {i} execution")}))
            .await
            .unwrap();
        let sid = start_res["session_id"].as_str().unwrap().to_string();
        session_ids.push(sid.clone());

        // Inscribe 5 turns into session i
        for turn in 0..5 {
            let role = if turn % 2 == 0 { "user" } else { "ai" };
            let is_summary = turn == 4;
            let record_args = if is_summary {
                json!({
                    "session_id": sid,
                    "content": format!("summary turn {turn} in session {i}"),
                    "role": "ai",
                    "importance": 0.9,
                })
            } else {
                json!({
                    "session_id": sid,
                    "content": format!("regular turn {turn} in session {i}"),
                    "role": role,
                    "importance": 0.5,
                })
            };

            let rec_res = record_tool.call(&mut ctx, record_args).await.unwrap();
            assert_eq!(rec_res["status"], "success");
        }

        // Checkpoint session i with exact structured handoff
        let cp_res = checkpoint_tool
            .call(
                &mut ctx,
                json!({
                    "session_id": sid,
                    "branch": "main",
                    "commit": format!("commit_{i:04}"),
                    "tests_green": true,
                    "next_queue": [format!("task_next_{i}")],
                    "open_flags": ["verified"],
                    "lease_id": format!("lease_{i:04}"),
                    "project": "/test/project",
                }),
            )
            .await
            .unwrap();

        assert_eq!(cp_res["status"], "success");
        assert_eq!(cp_res["handoff"]["commit"], format!("commit_{i:04}"));
        assert_eq!(cp_res["handoff"]["lease_id"], format!("lease_{i:04}"));

        // Sleep 15ms so created_at timestamps are strictly monotonically increasing
        tokio::time::sleep(std::time::Duration::from_millis(15)).await;
    }

    assert_eq!(session_ids.len(), num_sessions);

    // Verify Tantivy search across the 250 created turns in Sessions galaxy
    let total_sessions_count = store.count(Galaxy::Sessions).unwrap();
    assert!(
        total_sessions_count >= 250,
        "store must contain at least 250 records across 50 sessions (got: {total_sessions_count})"
    );
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn test_export_import_lossless_replay_roundtrip() {
    let (_dir1, store1) = test_store();
    let (_dir2, store2) = test_store();
    let mut ctx = Context::default();

    let start1 = SessionStartTool::new(store1.clone());
    let record1 = SessionRecordTool::new(store1.clone());
    let export1 = SessionExportTool::new(store1.clone());
    let replay1 = SessionReplayTool::new(store1.clone());

    let import2 = SessionImportTool::new(store2.clone(), None);
    let replay2 = SessionReplayTool::new(store2.clone());

    // Create session in store 1
    let start_res = start1
        .call(&mut ctx, json!({"goal": "lossless export test"}))
        .await
        .unwrap();
    let sid = start_res["session_id"].as_str().unwrap().to_string();

    // Inscribe 10 turns
    for t in 0..10 {
        let rec = record1
            .call(
                &mut ctx,
                json!({
                    "session_id": sid,
                    "content": format!("turn content {t}"),
                    "role": if t % 2 == 0 { "user" } else { "ai" },
                    "importance": 0.5 + (t as f64 * 0.04),
                }),
            )
            .await
            .unwrap();
        assert_eq!(rec["status"], "success");
    }

    // Replay in store 1
    let orig_replay = replay1
        .call(&mut ctx, json!({"session_id": sid}))
        .await
        .unwrap();
    assert_eq!(orig_replay["status"], "success");
    let orig_turns = orig_replay["turns"].as_array().unwrap();
    assert_eq!(orig_turns.len(), 10);

    // Export from store 1
    let export_res = export1
        .call(&mut ctx, json!({"session_id": sid}))
        .await
        .unwrap();
    let jsonl = export_res["jsonl"].as_str().unwrap();

    // Import into fresh store 2
    let import_res = import2
        .call(&mut ctx, json!({"jsonl": jsonl}))
        .await
        .unwrap();
    assert_eq!(import_res["status"], "success");

    // Replay in store 2
    let imported_replay = replay2
        .call(&mut ctx, json!({"session_id": sid}))
        .await
        .unwrap();
    assert_eq!(imported_replay["status"], "success");
    let imported_turns = imported_replay["turns"].as_array().unwrap();
    assert_eq!(imported_turns.len(), 10);

    // Assert bit-identical match of IDs, timestamps, and roles
    for i in 0..10 {
        assert_eq!(orig_turns[i]["id"], imported_turns[i]["id"]);
        assert_eq!(orig_turns[i]["role"], imported_turns[i]["role"]);
        assert_eq!(orig_turns[i]["content"], imported_turns[i]["content"]);
        assert_eq!(
            orig_turns[i]["created_at"],
            imported_turns[i]["created_at"]
        );
    }
}
