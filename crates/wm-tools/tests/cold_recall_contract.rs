//! Invented fixtures for the opt-in live cold recovery contract.
use serde_json::json;
use std::sync::Arc;
use wm_core::{Context, Galaxy, Tool};
use wm_memory::cold_storage::{ColdDiscoveryStop, ColdRecord, CompressionCodec, OuterRimFactors};
use wm_memory::{Memory, MemoryStore};
use wm_tools::{MemoryReadTool, expansion::MemoryHybridRecallTool};

fn cold(
    store: &MemoryStore,
    id: u128,
    galaxy: Galaxy,
    content: String,
    importance: f32,
    trust: f32,
) -> Memory {
    let mut memory = Memory::new(galaxy, content);
    memory.metadata.id = uuid::Uuid::from_u128(id);
    memory.metadata.importance = importance;
    memory.metadata.source_trust = trust;
    let factors = OuterRimFactors {
        age_factor: 0.9,
        access_factor: 0.9,
        resonance_factor: 0.9,
        emotional_factor: 0.9,
        importance_factor: 0.9,
        distance: 0.9,
    };
    let record =
        ColdRecord::new(&memory, 0.9, factors, None, None, CompressionCodec::Gzip).unwrap();
    store.put_cold_record(&record).unwrap();
    memory
}

#[tokio::test]
async fn cold_floors_do_not_starve_later_eligible_identity_and_exact_read() {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    cold(
        &store,
        1,
        Galaxy::Research,
        "zxqcoldcontract low importance".into(),
        0.1,
        0.9,
    );
    cold(
        &store,
        2,
        Galaxy::Research,
        "zxqcoldcontract low trust".into(),
        0.9,
        0.1,
    );
    let exact = format!("zxqcoldcontract\u{0007} {} end", "界".repeat(9_000));
    let target = cold(&store, 3, Galaxy::Research, exact, 0.9, 0.9);
    let live = MemoryHybridRecallTool::as_search(store.clone(), None, None);
    let normal = live
        .call(
            &mut Context::default(),
            json!({"query":"zxqcoldcontract","limit":1}),
        )
        .await
        .unwrap();
    assert!(normal["results"].as_array().unwrap().is_empty());
    let response = live.call(&mut Context::default(), json!({"query":"zxqcoldcontract","limit":1,"include_cold":true,"min_importance":0.8,"min_trust":0.8})).await.unwrap();
    let hit = &response["results"][0];
    assert_eq!(hit["id"], target.metadata.id.to_string(), "{response}");
    assert_eq!(hit["galaxy"], "research");
    assert!(hit["trust"].as_f64().unwrap() > 0.8);
    assert_eq!(hit["score"], serde_json::Value::Null);
    assert_eq!(hit["content_truncated"], true);
    assert_eq!(hit["content_scrubbed"], true);
    let navigation = hit["content"].as_str().unwrap();
    assert_eq!(navigation.chars().count(), 8192);
    assert!(navigation.len() > 8192, "character cap is not a byte cap");
    assert!(!navigation.contains('\u{0007}'));
    assert_eq!(response["cold_discovery"]["eligibility_skipped"], 2);
    assert_eq!(response["cold_discovery"]["stop_reason"], "result_limit");
    assert_eq!(response["cold_discovery"]["exhausted"], false);
    let read = MemoryReadTool::new(store.clone())
        .call(
            &mut Context::default(),
            json!({"id":hit["id"],"galaxy":hit["galaxy"]}),
        )
        .await
        .unwrap();
    assert_eq!(
        read["content"].as_str().unwrap().as_bytes(),
        target.content.as_bytes()
    );
    assert!(
        store
            .get(Galaxy::Research, target.metadata.id)
            .unwrap()
            .is_none(),
        "no thaw"
    );
    let wrong_galaxy = live
        .call(
            &mut Context::default(),
            json!({"query":"zxqcoldcontract","galaxy":"codex","include_cold":true}),
        )
        .await
        .unwrap();
    assert!(wrong_galaxy["results"].as_array().unwrap().is_empty());
}

#[test]
fn bounded_scan_reports_only_observed_exhaustion() {
    let dir = tempfile::tempdir().unwrap();
    let store = MemoryStore::open_default(dir.path().join("lmdb")).unwrap();
    cold(&store, 1, Galaxy::Codex, "zxqcoldcontract".into(), 0.9, 0.9);
    cold(&store, 2, Galaxy::Codex, "zxqcoldcontract".into(), 0.9, 0.9);
    let terms = vec!["zxqcoldcontract".into()];
    let limited = store.find_cold_matching(&terms, None, 10, 1).unwrap();
    assert_eq!(limited.scanned, 1);
    assert_eq!(limited.stop_reason, ColdDiscoveryStop::ScanLimit);
    let exact_budget = store.find_cold_matching(&terms, None, 10, 2).unwrap();
    assert_eq!(exact_budget.stop_reason, ColdDiscoveryStop::ScanLimit);
    let exhausted = store.find_cold_matching(&terms, None, 10, 3).unwrap();
    assert_eq!(exhausted.scanned, 2);
    assert_eq!(exhausted.stop_reason, ColdDiscoveryStop::Exhausted);
    let filled = store.find_cold_matching(&terms, None, 1, 3).unwrap();
    assert_eq!(filled.stop_reason, ColdDiscoveryStop::ResultLimit);
    let simultaneous = store.find_cold_matching(&terms, None, 1, 1).unwrap();
    assert_eq!(simultaneous.stop_reason, ColdDiscoveryStop::ScanLimit);
    let rejected = store
        .find_cold_matching_eligible(&terms, None, 1, 3, |_| false)
        .unwrap();
    assert_eq!(rejected.eligibility_skipped, 2);
    assert!(rejected.records.is_empty());
    assert_eq!(rejected.stop_reason, ColdDiscoveryStop::Exhausted);
}

#[tokio::test]
async fn full_hot_page_does_not_scan_cold() {
    let dir = tempfile::tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(dir.path().join("lmdb")).unwrap());
    let hot = Memory::new(Galaxy::Codex, "zxqcoldcontract hot".into());
    store.put(Galaxy::Codex, &hot).unwrap();
    cold(
        &store,
        1,
        Galaxy::Codex,
        "zxqcoldcontract cold".into(),
        0.9,
        0.9,
    );
    let index = Arc::new(wm_memory::SearchEngine::open(dir.path().join("tantivy")).unwrap());
    {
        let mut writer = index.writer().unwrap();
        index.index_memory(&mut writer, &hot).unwrap();
        index.commit(&mut writer).unwrap();
    }
    let live = MemoryHybridRecallTool::as_search(store, Some(index), None);
    let response = live
        .call(
            &mut Context::default(),
            json!({"query":"zxqcoldcontract","limit":1,"include_cold":true}),
        )
        .await
        .unwrap();
    assert_eq!(response["results"].as_array().unwrap().len(), 1);
    assert_eq!(response["results"][0]["id"], hot.metadata.id.to_string());
    assert_eq!(response["cold_discovery"]["scanned"], 0);
    assert_eq!(response["cold_discovery"]["appended"], 0);
    assert_eq!(response["cold_discovery"]["stop_reason"], "no_headroom");
    assert_eq!(response["cold_discovery"]["exhausted"], false);
}

#[test]
fn cold_integrity_and_private_visibility_remain_fail_closed() {
    let dir = tempfile::tempdir().unwrap();
    let store = MemoryStore::open_default(dir.path().join("lmdb")).unwrap();
    let mut private = cold(
        &store,
        1,
        Galaxy::Codex,
        "zxqcoldcontract private".into(),
        0.9,
        0.9,
    );
    private.metadata.is_private = true;
    let factors = OuterRimFactors {
        age_factor: 0.9,
        access_factor: 0.9,
        resonance_factor: 0.9,
        emotional_factor: 0.9,
        importance_factor: 0.9,
        distance: 0.9,
    };
    store
        .put_cold_record(
            &ColdRecord::new(&private, 0.9, factors, None, None, CompressionCodec::Gzip).unwrap(),
        )
        .unwrap();
    let tampered = cold(
        &store,
        2,
        Galaxy::Codex,
        "zxqcoldcontract tampered".into(),
        0.9,
        0.9,
    );
    let mut record = store
        .get_cold_record(tampered.metadata.id)
        .unwrap()
        .unwrap();
    record.content_hash = "not-the-payload-hash".into();
    store.put_cold_record(&record).unwrap();
    let good = cold(
        &store,
        3,
        Galaxy::Codex,
        "zxqcoldcontract visible".into(),
        0.9,
        0.9,
    );
    let outcome = store
        .find_cold_matching(&["zxqcoldcontract".into()], None, 10, 10)
        .unwrap();
    assert_eq!(outcome.private_skipped, 1);
    assert_eq!(outcome.integrity_rejected, 1);
    assert_eq!(outcome.records.len(), 1);
    assert_eq!(outcome.records[0].id, good.metadata.id);
}
