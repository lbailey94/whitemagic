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

#[tokio::test]
async fn copied_store_lifecycle_rehearsal_end_to_end() {
    use wm_cognitive::dream::{DreamContext, DreamCycle};
    use wm_memory::AssociationStore;

    // 1. Establish base store and copy to a disposable directory to rehearse
    // operational behavior without touching any real data.
    let base_dir = tempfile::tempdir().unwrap();
    let base_path = base_dir.path().join("lmdb");
    {
        let base_store = Arc::new(MemoryStore::open_default(&base_path).unwrap());
        let seed = Memory::new(Galaxy::Codex, "initial store seed".to_string());
        base_store.put(Galaxy::Codex, &seed).unwrap();
    }

    let copy_dir = tempfile::tempdir().unwrap();
    let copy_path = copy_dir.path().join("lmdb");
    std::fs::create_dir_all(&copy_path).unwrap();
    for entry in std::fs::read_dir(&base_path).unwrap() {
        let entry = entry.unwrap();
        if entry.file_type().unwrap().is_file() {
            std::fs::copy(entry.path(), copy_path.join(entry.file_name())).unwrap();
        }
    }

    let (keeper_id, event_time, old_sid, distillate_id) = {
        let store = Arc::new(MemoryStore::open_default(&copy_path).unwrap());
        let mut ctx = Context::default();

        // 2. Pin a keeper with declared event time
        let event_time = chrono::DateTime::parse_from_rfc3339("2026-09-01T12:00:00Z")
            .unwrap()
            .with_timezone(&chrono::Utc);
        let keeper = Memory::new(Galaxy::Codex, "critical operational keeper".to_string())
            .with_event_time(event_time);
        let keeper_id = keeper.metadata.id;
        store.put(Galaxy::Codex, &keeper).unwrap();

        let pin_tool = MemoryPinTool::new(store.clone());
        let pin_res = pin_tool
            .call(
                &mut ctx,
                json!({"id": keeper_id.to_string(), "galaxy": "codex"}),
            )
            .await
            .unwrap();
        assert_eq!(pin_res["pinned"], true);
        assert_eq!(pin_res["changed"], true);

        // 3. Seed an old session (48 hours ago, outside the 24h active edge)
        let old_ts_ms = chrono::Utc::now().timestamp_millis() - (48 * 3600 * 1000);
        let mut start_mem = Memory::new(
            Galaxy::Sessions,
            json!({
                "type": "session_start",
                "title": "historical architecture session",
                "user": "lucas",
            })
            .to_string(),
        );
        start_mem.metadata.tags = vec!["session".into(), "start".into()];
        start_mem.metadata.importance = 0.7;
        store.put(Galaxy::Sessions, &start_mem).unwrap();
        let old_sid = start_mem.metadata.id;

        for i in 0..3 {
            let mut turn_mem = Memory::new(
                Galaxy::Sessions,
                json!({
                    "type": "session_turn",
                    "session_id": old_sid.to_string(),
                    "sequence": i,
                    "role": if i % 2 == 0 { "user" } else { "ai" },
                    "turn_type": "message",
                    "importance": 0.7,
                    "content": format!("historical discussion step {i}"),
                    "timestamp": old_ts_ms + (i64::from(i) * 1000),
                })
                .to_string(),
            );
            turn_mem.metadata.tags = vec!["session".into(), "turn".into()];
            turn_mem.metadata.importance = 0.7;
            store.put(Galaxy::Sessions, &turn_mem).unwrap();
        }

        // 4. Run an end-to-end DreamCycle pass
        let assoc = AssociationStore::open(store.env()).unwrap();
        let dream_ctx = DreamContext::new(&store, &assoc);
        let mut dream = DreamCycle::new();
        let result = dream.run(&dream_ctx);
        assert!(result.success, "dream cycle must succeed");

        // 5. Confirm keeper survived decay/sweep with protection and event_time intact
        let keeper_mem = store
            .get(Galaxy::Codex, keeper_id)
            .unwrap()
            .expect("keeper survived");
        assert!(keeper_mem.metadata.is_protected, "keeper remains protected");
        assert_eq!(
            keeper_mem.metadata.event_time,
            Some(event_time),
            "event_time preserved"
        );

        // 6. Confirm old session was folded into Galaxy::Dreams with fold_level and derived_from
        let dreams = store.scan(Galaxy::Dreams, 100).unwrap();
        let distillate = dreams
            .iter()
            .find(|m| m.content.contains(&format!("## distill:session {old_sid}")))
            .expect("dream narrative created distillate for old session");
        assert_eq!(distillate.metadata.fold_level, Some(FoldLevel::L1));
        assert_eq!(distillate.metadata.derived_from, vec![old_sid]);
        let distillate_id = distillate.metadata.id;

        // 7. Verify disclosure via MemoryReadTool
        let read_tool = MemoryReadTool::new(store.clone());
        let read_res = read_tool
            .call(
                &mut ctx,
                json!({"id": distillate_id.to_string(), "galaxy": "dreams"}),
            )
            .await
            .unwrap();
        assert_eq!(read_res["fold_level"], "l1");
        assert_eq!(read_res["derived_from"][0], old_sid.to_string());

        // The tool handles are the only extra MemoryStore owners. The scoped
        // phase ensures they and the dream context are gone before reopen.
        drop(read_tool);
        drop(pin_tool);
        drop(dream_ctx);
        drop(dream);
        assert_eq!(Arc::strong_count(&store), 1, "all store clones are closed");

        (keeper_id, event_time, old_sid, distillate_id)
    };

    let reopened = Arc::new(MemoryStore::open_default(&copy_path).unwrap());
    let keeper_reopened = reopened
        .get(Galaxy::Codex, keeper_id)
        .unwrap()
        .expect("keeper exists on reopen");
    assert!(keeper_reopened.metadata.is_protected);
    assert_eq!(keeper_reopened.metadata.event_time, Some(event_time));

    let distillate_reopened = reopened
        .get(Galaxy::Dreams, distillate_id)
        .unwrap()
        .expect("distillate exists on reopen");
    assert_eq!(distillate_reopened.metadata.fold_level, Some(FoldLevel::L1));
    assert_eq!(distillate_reopened.metadata.derived_from, vec![old_sid]);
}

#[tokio::test]
async fn karma_report_recent_entries_and_debt_survive_reopen() {
    use wm_governance::KarmaLedger;

    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    let ledger = Arc::new(KarmaLedger::new(store.clone()).unwrap());

    // Record 2,000 entries across multiple tools
    for i in 0..2_000 {
        let tool = match i % 3 {
            0 => "memory.search",
            1 => "session.record",
            _ => "memory.pin",
        };
        // A declared write that performed no writes accrues deterministic debt.
        ledger.record(tool, true, 0, true).unwrap();
    }
    // Tombstone 1,500 oldest entries, keeping the newest 500
    assert_eq!(ledger.clear_old(500).unwrap(), 1_500);

    let mut ctx = Context::default();
    let report_tool = wm_tools::KarmaReportTool::new(ledger.clone());

    let report = report_tool
        .call(&mut ctx, json!({"limit": 10}))
        .await
        .unwrap();
    assert_eq!(report["status"], "success");
    assert_eq!(report["entry_count"], 2_000);
    assert!((report["total_debt"].as_f64().unwrap() - 400.0).abs() < 0.01);
    let recent = report["recent_entries"].as_array().unwrap();
    assert_eq!(recent.len(), 10);
    assert_eq!(
        recent
            .iter()
            .map(|entry| entry["id"].as_u64().unwrap())
            .collect::<Vec<_>>(),
        (1_990..2_000).collect::<Vec<_>>(),
        "recent report is bounded to the newest live records"
    );

    let per_tool = report["per_tool_debt"].as_array().unwrap();
    let debt_by_tool = per_tool
        .iter()
        .map(|entry| {
            (
                entry["tool"].as_str().unwrap(),
                entry["debt"].as_f64().unwrap(),
            )
        })
        .collect::<std::collections::HashMap<_, _>>();
    assert_eq!(debt_by_tool.len(), 3);
    assert!((debt_by_tool["memory.search"] - 33.4).abs() < 0.01);
    assert!((debt_by_tool["session.record"] - 33.4).abs() < 0.01);
    assert!((debt_by_tool["memory.pin"] - 33.2).abs() < 0.01);

    // The aggregate and recent-entry view must survive a real ledger reopen.
    drop(report_tool);
    drop(ledger);
    drop(store);
    let reopened_store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    let reopened_ledger = Arc::new(KarmaLedger::new(reopened_store.clone()).unwrap());
    let reopened_report = wm_tools::KarmaReportTool::new(reopened_ledger.clone())
        .call(&mut ctx, json!({"limit": 10}))
        .await
        .unwrap();
    assert_eq!(reopened_report["entry_count"], 2_000);
    assert!((reopened_report["total_debt"].as_f64().unwrap() - 400.0).abs() < 0.01);
    assert_eq!(
        reopened_report["recent_entries"]
            .as_array()
            .unwrap()
            .iter()
            .map(|entry| entry["id"].as_u64().unwrap())
            .collect::<Vec<_>>(),
        (1_990..2_000).collect::<Vec<_>>()
    );
    let reopened_tool_debt = reopened_report["per_tool_debt"].as_array().unwrap();
    assert_eq!(reopened_tool_debt.len(), 3);
    for entry in reopened_tool_debt {
        let tool = entry["tool"].as_str().unwrap();
        assert!((entry["debt"].as_f64().unwrap() - debt_by_tool[tool]).abs() < 0.01);
    }
}

#[tokio::test]
async fn http_embedder_dense_payload_bounded_retry() {
    use std::io::{Read, Write};
    use std::net::TcpListener;
    use std::sync::Mutex;
    use std::time::Duration;
    use wm_memory::{Embedder, EmbedderConfig, HttpEmbedder};

    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let seen: Arc<Mutex<Vec<usize>>> = Arc::new(Mutex::new(Vec::new()));
    let seen_server = Arc::clone(&seen);

    let server = std::thread::spawn(move || {
        let mut served = 0usize;
        let deadline = std::time::Instant::now() + Duration::from_secs(5);
        while served < 2 && std::time::Instant::now() < deadline {
            listener.set_nonblocking(true).unwrap();
            let Ok((mut stream, _)) = listener.accept() else {
                std::thread::sleep(Duration::from_millis(5));
                continue;
            };
            stream.set_nonblocking(false).unwrap();
            stream
                .set_read_timeout(Some(Duration::from_secs(2)))
                .unwrap();
            let mut buf = Vec::new();
            let mut tmp = [0u8; 2048];
            let header_end = loop {
                let n = stream.read(&mut tmp).unwrap();
                buf.extend_from_slice(&tmp[..n]);
                if let Some(pos) = buf.windows(4).position(|w| w == b"\r\n\r\n") {
                    break pos + 4;
                }
            };
            let headers = String::from_utf8_lossy(&buf[..header_end]).to_ascii_lowercase();
            let content_length: usize = headers
                .lines()
                .find_map(|l| l.strip_prefix("content-length:"))
                .and_then(|v| v.trim().parse().ok())
                .unwrap_or(0);
            while buf.len() < header_end + content_length {
                let n = stream.read(&mut tmp).unwrap();
                buf.extend_from_slice(&tmp[..n]);
            }
            let req: serde_json::Value =
                serde_json::from_slice(&buf[header_end..header_end + content_length]).unwrap();
            let inputs = req["input"].as_array().unwrap();
            seen_server
                .lock()
                .unwrap()
                .push(inputs[0].as_str().unwrap().len());

            let response = if served == 0 {
                let body = "{\"error\":\"input too long: http status: 400\"}";
                format!(
                    "HTTP/1.1 400 Bad Request\r\ncontent-type: application/json\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{}",
                    body.len(),
                    body
                )
            } else {
                let data: Vec<_> = inputs
                    .iter()
                    .map(|_| json!({"embedding": [0.5, 0.5]}))
                    .collect();
                let body = json!({"data": data}).to_string();
                format!(
                    "HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{}",
                    body.len(),
                    body
                )
            };
            stream.write_all(response.as_bytes()).unwrap();
            served += 1;
        }
        served
    });

    let embedder = HttpEmbedder::new(EmbedderConfig {
        endpoint: format!("http://{addr}"),
        model: "mock".into(),
        dimension: 2,
        timeout: Duration::from_secs(5),
    });

    // Punctuation-dense string simulating JSON telemetry outlier
    let dense_payload = "{\"metric\":{\"values\":[1,2,3,4,5],\"sub\":{\"k\":\"v\"}}};".repeat(30);
    assert!(dense_payload.len() > 1000);

    let vectors = embedder.embed_batch(&[dense_payload.as_str()]).unwrap();
    assert_eq!(vectors, vec![vec![0.5, 0.5]]);
    assert_eq!(
        server.join().unwrap(),
        2,
        "initial 400 followed by halved-budget retry"
    );

    let recorded_lens = seen.lock().unwrap().clone();
    assert_eq!(recorded_lens.len(), 2);
    assert!(recorded_lens[0] <= 768, "first attempt <= 768");
    assert!(recorded_lens[1] <= 384, "retry halved <= 384");
}
