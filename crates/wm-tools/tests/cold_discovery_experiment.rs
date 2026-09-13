//! Synthetic diagnosis, not a production cold-search correction or benchmark.
use serde_json::json;
use std::sync::Arc;
use wm_core::{Context, Galaxy, Tool};
use wm_memory::{Memory, MemoryStore, PhagicConfig, PhagicDigester, SearchEngine};
use wm_tools::{MemoryReadTool, MemorySearchTool};

#[tokio::test]
async fn public_cold_fact_search_to_read_is_measured_before_and_after_digest() {
    let dir = tempfile::tempdir().unwrap();
    let store_path = dir.path().join("lmdb");
    let index_path = dir.path().join("tantivy");
    let store = Arc::new(MemoryStore::open_default(&store_path).unwrap());
    std::fs::create_dir_all(&index_path).unwrap();
    let search = Arc::new(SearchEngine::open(&index_path).unwrap());
    let fact = "zxquniquecoldfact741";
    let mut target = Memory::new(Galaxy::Codex, format!("{} {fact}", "prefix ".repeat(80)));
    target.metadata.id = uuid::Uuid::from_u128(741);
    target.metadata.tags = vec!["synthetic-public".into()];
    let target_id = target.metadata.id;
    let target_bytes = target.content.clone();
    assert!(
        !target
            .content
            .chars()
            .take(300)
            .collect::<String>()
            .contains(fact)
    );
    let mut decoy = Memory::new(Galaxy::Codex, "prefix only decoy".into());
    decoy.metadata.id = uuid::Uuid::from_u128(742);
    let mut private = Memory::new(Galaxy::Codex, format!("private {fact}"));
    private.metadata.id = uuid::Uuid::from_u128(743);
    private.metadata.is_private = true;
    let mut excluded = Memory::new(Galaxy::Codex, format!("excluded {fact}"));
    excluded.metadata.id = uuid::Uuid::from_u128(744);
    excluded.metadata.model_exclude = true;
    let mut correction = Memory::new(
        Galaxy::Codex,
        "Synthetic correction: earlier unrelated value was wrong".into(),
    );
    correction.metadata.id = uuid::Uuid::from_u128(745);
    correction.metadata.is_protected = true;
    let fixtures = [
        target,
        decoy,
        private.clone(),
        excluded.clone(),
        correction.clone(),
    ];
    store.put_batch(Galaxy::Codex, &fixtures).unwrap();
    let mut writer = search.writer().unwrap();
    for memory in &fixtures {
        search.index_memory(&mut writer, memory).unwrap();
    }
    search.commit(&mut writer).unwrap();
    drop(writer);
    let search_tool = MemorySearchTool::new(search.clone(), store.clone());
    let read_tool = MemoryReadTool::new(store.clone());
    let args = json!({"query":fact,"galaxy":"codex","limit":20});
    let clock = std::time::Instant::now();
    let baseline = search_tool
        .call(&mut Context::default(), args.clone())
        .await
        .unwrap();
    let baseline_us = clock.elapsed().as_micros();
    // Ordinary MCP visibility excludes private, not model_exclude. No model
    // receives these responses in this experiment; model context is separate.
    assert_eq!(baseline["total"], 2);
    assert!(
        baseline["results"]
            .as_array()
            .unwrap()
            .iter()
            .any(|r| r["memory_id"] == target_id.to_string())
    );
    assert!(
        !baseline
            .to_string()
            .contains(&private.metadata.id.to_string())
    );
    assert!(
        baseline
            .to_string()
            .contains(&excluded.metadata.id.to_string())
    );
    let read = read_tool
        .call(
            &mut Context::default(),
            json!({"id":target_id,"galaxy":"codex"}),
        )
        .await
        .unwrap();
    assert_eq!(
        read["content"].as_str().unwrap().as_bytes(),
        target_bytes.as_bytes()
    );
    eprintln!("BASELINE query={fact} limit=20 latency_us={baseline_us} result={baseline}");
    let digester = PhagicDigester::new(PhagicConfig {
        outer_rim_threshold: 0.0,
        ..Default::default()
    });
    let report = digester
        .digest_galaxy(&store, Some(&search), Galaxy::Codex)
        .unwrap();
    assert_eq!(report.memories_digested, 2);
    assert!(store.get(Galaxy::Codex, target_id).unwrap().is_none());
    assert_eq!(
        store
            .get_cold_record(target_id)
            .unwrap()
            .unwrap()
            .decompress()
            .unwrap()
            .content
            .as_bytes(),
        target_bytes.as_bytes()
    );
    let digest_id = report.digest_memory_id.unwrap();
    assert!(
        !store
            .get(Galaxy::Codex, digest_id)
            .unwrap()
            .unwrap()
            .content
            .contains(fact)
    );
    for memory in [&private, &excluded, &correction] {
        assert_eq!(
            serde_json::to_value(
                store
                    .get(Galaxy::Codex, memory.metadata.id)
                    .unwrap()
                    .unwrap()
            )
            .unwrap(),
            serde_json::to_value(memory).unwrap()
        );
        assert!(store.get_cold_record(memory.metadata.id).unwrap().is_none());
    }
    eprintln!("DIGEST config_outer_rim_threshold=0.0 report={report:?}");
    drop(read_tool);
    drop(search_tool);
    drop(search);
    drop(store);
    let store = Arc::new(MemoryStore::open_default(&store_path).unwrap());
    let search = Arc::new(SearchEngine::open(&index_path).unwrap());
    let search_tool = MemorySearchTool::new(search.clone(), store.clone());
    let clock = std::time::Instant::now();
    let after = search_tool
        .call(&mut Context::default(), args)
        .await
        .unwrap();
    let after_us = clock.elapsed().as_micros();
    // The retained model-excluded hot twin remains an ordinary-MCP candidate.
    // It is not discovery of the target original and must not mask that gap.
    assert_eq!(after["total"], 1);
    assert_eq!(
        after["results"][0]["memory_id"],
        excluded.metadata.id.to_string()
    );
    assert!(!after.to_string().contains(&target_id.to_string()));
    assert!(!after.to_string().contains(&private.metadata.id.to_string()));
    let read_tool = MemoryReadTool::new(store.clone());
    let clock = std::time::Instant::now();
    let control = read_tool
        .call(
            &mut Context::default(),
            json!({"id":target_id,"galaxy":"codex"}),
        )
        .await
        .unwrap();
    let control_us = clock.elapsed().as_micros();
    assert_eq!(control["status"], "success");
    assert_eq!(
        control["content"].as_str().unwrap().as_bytes(),
        target_bytes.as_bytes()
    );
    assert!(store.get(Galaxy::Codex, target_id).unwrap().is_none());
    for memory in [&private, &excluded, &correction] {
        assert_eq!(
            serde_json::to_value(
                store
                    .get(Galaxy::Codex, memory.metadata.id)
                    .unwrap()
                    .unwrap()
            )
            .unwrap(),
            serde_json::to_value(memory).unwrap()
        );
    }
    eprintln!("REOPEN query={fact} limit=20 latency_us={after_us} result={after}");
    eprintln!(
        "KNOWN_ID_CONTROL id={target_id} read_latency_us={control_us} exact_bytes={} no_thaw=true discovery=false",
        target_bytes.len()
    );

    // ── Opt-in cold discovery on the live retrieval verb (the accepted seam
    // from the 2026-09-13 lossless cycle): the digested original is now
    // discoverable by query — hydrated and integrity-verified from the cold
    // payload, explicitly disclosed, still no thaw. Private originals stay
    // absent; the legacy-tool observations above are unchanged.
    let live = wm_tools::expansion::MemoryHybridRecallTool::as_search(
        store.clone(),
        Some(search.clone()),
        None,
    );
    let clock = std::time::Instant::now();
    let discovered = live
        .call(
            &mut Context::default(),
            json!({"query":fact,"galaxy":"codex","limit":20,"include_cold":true}),
        )
        .await
        .unwrap();
    let discovered_us = clock.elapsed().as_micros();
    assert_eq!(
        discovered["cold_discovery"]["no_thaw"], true,
        "{discovered}"
    );
    assert!(
        discovered["results"].as_array().unwrap().iter().any(|r| {
            r["id"].as_str() == Some(target_id.to_string().as_str())
                && r["source"] == "cold"
                && r["integrity"] == "verified"
        }),
        "{discovered}"
    );
    assert!(
        !discovered
            .to_string()
            .contains(&private.metadata.id.to_string()),
        "{discovered}"
    );
    eprintln!(
        "OPT_IN_COLD_DISCOVERY query={fact} latency_us={discovered_us} no_thaw=true result={discovered}"
    );
}
