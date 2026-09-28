//! V9.3 E2E: pin → as-of → fold provenance → continuity briefing, one pass.
//!
//! Each piece is unit-tested beside its implementation; this file proves the
//! three surfaces compose: a pinned keeper survives, a folded record
//! discloses where it came from and when it happened, and the continuity
//! briefing renders a stable, hash-addressed block over the session tail.

use serde_json::json;
use std::sync::Arc;
use wm_core::{Context, Galaxy, Tool};
use wm_memory::{FoldLevel, Memory, MemoryStore};
use wm_tools::MemoryReadTool;
use wm_tools::expansion::{
    MemoryPinTool, SessionContinuityTool, SessionRecordTool, SessionStartTool,
};

#[tokio::test]
async fn pin_asof_fold_and_continuity_compose() {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    let mut ctx = Context::default();

    // 1. Pin: a keeper the fold/deletion paths must never take.
    let keeper = Memory::new(Galaxy::Codex, "keeper detail".to_string());
    let keeper_id = keeper.metadata.id;
    store.put(Galaxy::Codex, &keeper).unwrap();
    let pinned = MemoryPinTool::new(store.clone())
        .call(&mut ctx, json!({"id": keeper_id.to_string()}))
        .await
        .unwrap();
    assert_eq!(pinned["pinned"], true);
    assert_eq!(pinned["changed"], true);
    assert!(
        store
            .get(Galaxy::Codex, keeper_id)
            .unwrap()
            .unwrap()
            .metadata
            .is_protected
    );

    // 2. As-of + fold provenance: a folded record with a declared event time.
    let when = chrono::DateTime::parse_from_rfc3339("2026-09-01T09:00:00Z")
        .unwrap()
        .with_timezone(&chrono::Utc);
    let folded = Memory::new(Galaxy::Codex, "folded digest of keeper".to_string())
        .with_event_time(when)
        .with_fold(FoldLevel::L1, vec![keeper_id]);
    let folded_id = folded.metadata.id;
    store.put(Galaxy::Codex, &folded).unwrap();
    let read = MemoryReadTool::new(store.clone())
        .call(&mut ctx, json!({"id": folded_id, "galaxy": "codex"}))
        .await
        .unwrap();
    assert_eq!(read["fold_level"], "l1");
    assert_eq!(read["derived_from"][0], keeper_id.to_string());
    assert!(
        read["event_time"]
            .as_str()
            .unwrap()
            .starts_with("2026-09-01T09:00:00")
    );

    // 3. Continuity: the delivered tail renders a stable briefing.
    let start = SessionStartTool::new(store.clone());
    let sid1 = start
        .call(&mut ctx, json!({"title": "fold e2e"}))
        .await
        .unwrap()["session_id"]
        .as_str()
        .unwrap()
        .to_string();
    let record = SessionRecordTool::new(store.clone());
    for i in 0..3 {
        record
            .call(
                &mut ctx,
                json!({"role": "ai", "content": format!("step {i}"), "session_id": sid1}),
            )
            .await
            .unwrap();
    }
    let sid2 = start
        .call(&mut ctx, json!({"title": "next session"}))
        .await
        .unwrap()["session_id"]
        .as_str()
        .unwrap()
        .to_string();
    let continuity = SessionContinuityTool::new(store.clone());
    let c = continuity
        .call(
            &mut ctx,
            json!({"current_session_id": sid2, "n": 10, "include_briefing_text": true}),
        )
        .await
        .unwrap();
    assert_eq!(c["briefing"]["format_version"], "wm-briefing/1");
    assert_eq!(c["briefing"]["recent_verbatim"], true);
    let text = c["briefing"]["text"].as_str().unwrap();
    assert!(text.contains("[1|ai|message] step 0"), "{text}");
    assert_eq!(c["briefing"]["turn_hashes"].as_array().unwrap().len(), 3);

    // Same stored state → identical briefing (the cache contract).
    let again = continuity
        .call(
            &mut ctx,
            json!({"current_session_id": sid2, "n": 10, "include_briefing_text": true}),
        )
        .await
        .unwrap();
    assert_eq!(c["briefing"], again["briefing"]);
}
