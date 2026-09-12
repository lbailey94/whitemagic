//! Integration tests for Non-Destructive Phagic Digestive Cold-Storage.
//!
//! Verifies:
//! - Zero data loss: cold-stored memories can be queried or thawed back into hot storage.
//! - Outer rim identification: correct sorting by resonance distance.
//! - Thematic condensation: distilled thematic node synthesis in hot tier.
//! - Full Tantivy search integration: deindexing cold memories and indexing thematic digests.
//! - the project's sacred rule: Phagic systems must NEVER delete anything.

use chrono::Utc;
use tempfile::tempdir;
use wm_core::Galaxy;
use wm_memory::cold_storage::{
    ColdQuery, CompressionCodec, PhagicConfig, PhagicDigester, calculate_outer_rim_distance,
};
use wm_memory::{Memory, MemoryStore, MemoryType, SearchEngine, Tier};

fn setup_store_and_search() -> (tempfile::TempDir, MemoryStore, SearchEngine) {
    let tmp = tempdir().unwrap();
    let store_dir = tmp.path().join("store");
    let search_dir = tmp.path().join("search");
    std::fs::create_dir_all(&search_dir).unwrap();
    let store = MemoryStore::open_default(&store_dir).unwrap();
    let search = SearchEngine::open(&search_dir).unwrap();
    (tmp, store, search)
}

#[test]
fn zero_data_loss_freeze_thaw_exact_fidelity() {
    let (_tmp, store, _) = setup_store_and_search();
    let galaxy = Galaxy::Codex;

    let content = "The sacred texts of WhiteMagic non-destructive storage architecture v9.2";
    let now = Utc::now();
    let mut mem = Memory::new(galaxy, content.to_string())
        .with_tags(vec!["sacred".into(), "v9".into(), "phagic".into()])
        .with_importance(0.25)
        .with_neuro_score(0.2)
        .with_novelty_score(0.8)
        .with_emotional_valence(0.5, 0.4)
        .with_source("lucas_user".into(), 0.95);
    mem.metadata.title = Some("Architectural Blueprint".into());
    mem.metadata.topic = Some("Storage".into());
    mem.metadata.version = 42;
    mem.metadata.access_count = 3;
    mem.metadata.recall_count = 2;
    mem.metadata.corroborated_by = vec![uuid::Uuid::new_v4(), uuid::Uuid::new_v4()];
    let id = mem.metadata.id;

    store.put(galaxy, &mem).unwrap();
    assert!(store.get(galaxy, id).unwrap().is_some());

    // Freeze to cold storage with Gzip
    let config = PhagicConfig::default();
    let factors = calculate_outer_rim_distance(&mem, &config, now);
    let cold_rec = store
        .freeze_to_cold(
            None,
            id,
            factors.distance,
            factors,
            None,
            Some("sacred preservation test".into()),
            CompressionCodec::Gzip,
        )
        .unwrap();

    assert_eq!(cold_rec.id, id);
    assert_eq!(cold_rec.galaxy, galaxy);
    assert_eq!(cold_rec.title, Some("Architectural Blueprint".into()));

    // Memory is gone from hot galaxy...
    assert!(store.get(galaxy, id).unwrap().is_none());

    // ...but present in cold storage
    let cold_found = store
        .get_cold_record(id)
        .unwrap()
        .expect("Cold record must exist");
    assert_eq!(cold_found.content_hash, mem.metadata.content_hash);
    assert_eq!(cold_found.tags, vec!["sacred", "v9", "phagic"]);
    assert_eq!(cold_found.version, 42);

    // find_anywhere returns it with is_cold = true
    let (found_galaxy, found_mem, is_cold) =
        store.find_anywhere(id).unwrap().expect("Found in cold");
    assert_eq!(found_galaxy, galaxy);
    assert_eq!(found_mem.content, content);
    assert_eq!(
        found_mem.metadata.title,
        Some("Architectural Blueprint".into())
    );
    assert_eq!(found_mem.metadata.version, 42);
    assert_eq!(found_mem.metadata.corroborated_by.len(), 2);
    assert!(is_cold);

    // Thaw back into hot storage
    let thawed = store.thaw_from_cold(None, id).unwrap();
    assert_eq!(thawed.metadata.id, id);
    assert_eq!(thawed.content, content);
    assert_eq!(
        thawed.metadata.title,
        Some("Architectural Blueprint".into())
    );
    assert_eq!(thawed.metadata.version, 42);
    assert_eq!(thawed.metadata.corroborated_by.len(), 2);
    assert_eq!(thawed.metadata.tier, Tier::Episodic);
    assert!(thawed.metadata.tags.contains(&"thawed:phagic".to_string()));

    // Memory is back in hot galaxy
    assert!(store.get(galaxy, id).unwrap().is_some());
    // And removed from cold archive
    assert!(store.get_cold_record(id).unwrap().is_none());
}

#[test]
fn outer_rim_identification_and_sorting() {
    let (_tmp, store, _) = setup_store_and_search();
    let galaxy = Galaxy::Research;
    let now = Utc::now();
    let digester = PhagicDigester::default_config();

    // 1. Deep Outer Rim: Ancient (180 days ago), 0 reads, 0 resonance, 0 emotion, 0.01 importance
    let mut mem_deep = Memory::new(galaxy, "Deep outer rim memory".into())
        .with_importance(0.01)
        .with_neuro_score(0.05)
        .with_emotional_valence(0.0, 0.0);
    mem_deep.metadata.accessed_at = now - chrono::Duration::days(180);
    mem_deep.metadata.access_count = 0;
    store.put(galaxy, &mem_deep).unwrap();

    // 2. Outer Rim: Old (90 days ago), 1 read, 0.2 resonance, 0.15 importance
    let mut mem_rim = Memory::new(galaxy, "Outer rim memory".into())
        .with_importance(0.15)
        .with_neuro_score(0.2)
        .with_emotional_valence(0.2, 0.2);
    mem_rim.metadata.accessed_at = now - chrono::Duration::days(90);
    mem_rim.metadata.access_count = 1;
    store.put(galaxy, &mem_rim).unwrap();

    // 3. Mid Disk: Recent (5 days ago), 5 reads, 0.6 resonance, 0.5 importance
    let mut mem_mid = Memory::new(galaxy, "Mid disk memory".into())
        .with_importance(0.5)
        .with_neuro_score(0.6)
        .with_emotional_valence(0.4, 0.5);
    mem_mid.metadata.accessed_at = now - chrono::Duration::days(5);
    mem_mid.metadata.access_count = 5;
    store.put(galaxy, &mem_mid).unwrap();

    // 4. Core: Today, 20 reads, 0.9 resonance, 0.9 importance, strong emotion
    let mut mem_core = Memory::new(galaxy, "Galactic core active memory".into())
        .with_importance(0.9)
        .with_neuro_score(0.9)
        .with_emotional_valence(0.9, 0.9);
    mem_core.metadata.accessed_at = now;
    mem_core.metadata.access_count = 20;
    store.put(galaxy, &mem_core).unwrap();

    // 5. Protected: Ancient (300 days ago), 0 reads, 0 importance, but is_protected = true!
    let mut mem_prot = Memory::new(galaxy, "Ancient protected sacred memory".into())
        .with_importance(0.01)
        .with_protection(true);
    mem_prot.metadata.accessed_at = now - chrono::Duration::days(300);
    mem_prot.metadata.access_count = 0;
    store.put(galaxy, &mem_prot).unwrap();

    let candidates = digester.scan_outer_rim(&store, galaxy).unwrap();

    // Candidates should only include mem_deep and mem_rim (distances >= threshold 0.70)
    assert_eq!(
        candidates.len(),
        2,
        "Only outer rim memories should qualify"
    );

    // First candidate must be mem_deep (strictly furthest)
    assert_eq!(candidates[0].0.metadata.id, mem_deep.metadata.id);
    assert_eq!(candidates[1].0.metadata.id, mem_rim.metadata.id);
    assert!(
        candidates[0].1.distance > candidates[1].1.distance,
        "Candidates must be sorted descending by distance"
    );

    // Verify individual distances
    let d_deep = digester.calculate_distance(&mem_deep, now).distance;
    let d_rim = digester.calculate_distance(&mem_rim, now).distance;
    let d_mid = digester.calculate_distance(&mem_mid, now).distance;
    let d_core = digester.calculate_distance(&mem_core, now).distance;
    let d_prot = digester.calculate_distance(&mem_prot, now).distance;

    assert!(d_deep > d_rim);
    assert!(d_rim > d_mid);
    assert!(d_mid > d_core);
    assert_eq!(d_prot, 0.0, "Protected memory must be 0.0 distance");
}

#[test]
#[cfg_attr(
    windows,
    ignore = "Tantivy index commit hits Windows file locking (os error 5); tracked"
)]
fn phagic_thematic_condensation_and_digestion() {
    let (_tmp, store, search) = setup_store_and_search();
    let galaxy = Galaxy::Codex;
    let now = Utc::now();
    let digester = PhagicDigester::default_config();

    // Insert 4 outer-rim memories
    let mut ids = Vec::new();
    for i in 1..=4 {
        let content = format!("Historical log #{i}: experimental simulation results in orbit");
        let mut mem = Memory::new(galaxy, content)
            .with_tags(vec![
                "simulation".into(),
                "orbit".into(),
                "telemetry".into(),
            ])
            .with_importance(0.05);
        mem.metadata.accessed_at = now - chrono::Duration::days(140);
        mem.metadata.access_count = 0;
        store.put(galaxy, &mem).unwrap();

        // Index in Tantivy
        let mut writer = search.writer().unwrap();
        search
            .add_document(
                &mut writer,
                &mem.metadata.id.to_string(),
                galaxy.db_name(),
                &mem.content,
                &mem.metadata.tags,
                mem.metadata.created_at.timestamp(),
            )
            .unwrap();
        search.commit(&mut writer).unwrap();
        ids.push(mem.metadata.id);
    }

    // Tantivy search initially finds them
    let initial_hits = search
        .search_in_galaxy("experimental simulation", Some(galaxy), 10)
        .unwrap();
    assert_eq!(initial_hits.len(), 4);

    // Run Phagic Digestion with Tantivy integration
    let report = digester
        .digest_galaxy(&store, Some(&search), galaxy)
        .unwrap();

    assert_eq!(report.memories_digested, 4);
    assert!(report.digest_memory_id.is_some());
    let digest_id = report.digest_memory_id.unwrap();

    // Hot store now has 1 memory: the distilled thematic digest node
    assert_eq!(store.count(galaxy).unwrap(), 1);
    let digest_mem = store
        .get(galaxy, digest_id)
        .unwrap()
        .expect("Digest node in hot store");
    assert_eq!(digest_mem.metadata.tier, Tier::Semantic);
    assert_eq!(digest_mem.metadata.memory_type, MemoryType::Symbolic);
    assert!(digest_mem.content.contains("Phagic Thematic Digest"));
    assert!(
        digest_mem
            .metadata
            .tags
            .contains(&"phagic:digest".to_string())
    );

    // Cold store now has all 4 original memories
    assert_eq!(store.count_cold(Some(galaxy)).unwrap(), 4);
    for id in &ids {
        assert!(
            store.get(galaxy, *id).unwrap().is_none(),
            "Original memory removed from hot"
        );
        let cold = store
            .get_cold_record(*id)
            .unwrap()
            .expect("Original memory in cold storage");
        assert_eq!(
            cold.digest_id,
            Some(digest_id),
            "Cold record links to digest node"
        );
    }

    // Tantivy search now:
    // 1. Original memories are deindexed (not returned for their individual IDs)
    // 2. Thematic digest node IS indexed and found!
    let hits_after = search
        .search_in_galaxy("experimental simulation", Some(galaxy), 10)
        .unwrap();
    assert_eq!(
        hits_after.len(),
        1,
        "Only the thematic digest node is found in active search"
    );
    assert_eq!(hits_after[0].memory_id, digest_id.to_string());

    // Thaw the first memory back to hot
    let thawed = digester.thaw(&store, Some(&search), ids[0]).unwrap();
    assert_eq!(thawed.metadata.id, ids[0]);
    assert_eq!(store.count(galaxy).unwrap(), 2); // digest node + thawed memory
    assert_eq!(store.count_cold(Some(galaxy)).unwrap(), 3); // 3 remaining in cold

    // Tantivy search now finds both the thawed memory and the digest node!
    let hits_thawed = search
        .search_in_galaxy("simulation", Some(galaxy), 10)
        .unwrap();
    assert!(
        hits_thawed
            .iter()
            .any(|h| h.memory_id == ids[0].to_string())
    );
    assert!(
        hits_thawed
            .iter()
            .any(|h| h.memory_id == digest_id.to_string())
    );
}

#[test]
fn cold_query_filtering() {
    let (_tmp, store, _) = setup_store_and_search();
    let now = Utc::now();

    // Freeze one in Codex, one in Journals
    let mut m1 = Memory::new(Galaxy::Codex, "Ancient quantum algorithm derivation".into())
        .with_tags(vec!["quantum".into(), "math".into()])
        .with_importance(0.05);
    m1.metadata.accessed_at = now - chrono::Duration::days(120);
    let id1 = m1.metadata.id;
    store.put(Galaxy::Codex, &m1).unwrap();

    let mut m2 = Memory::new(
        Galaxy::Journals,
        "Day 42 observation of celestial bodies".into(),
    )
    .with_tags(vec!["astronomy".into(), "journal".into()])
    .with_importance(0.04);
    m2.metadata.accessed_at = now - chrono::Duration::days(150);
    let id2 = m2.metadata.id;
    store.put(Galaxy::Journals, &m2).unwrap();

    let digester = PhagicDigester::default_config();
    let f1 = digester.calculate_distance(&m1, now);
    let f2 = digester.calculate_distance(&m2, now);

    store
        .freeze_to_cold(
            None,
            id1,
            f1.distance,
            f1,
            None,
            None,
            CompressionCodec::Gzip,
        )
        .unwrap();
    store
        .freeze_to_cold(
            None,
            id2,
            f2.distance,
            f2,
            None,
            None,
            CompressionCodec::Deflate,
        )
        .unwrap();

    assert_eq!(store.count_cold(None).unwrap(), 2);
    assert_eq!(store.count_cold(Some(Galaxy::Codex)).unwrap(), 1);
    assert_eq!(store.count_cold(Some(Galaxy::Journals)).unwrap(), 1);

    // Query by galaxy
    let codex_cold = store
        .query_cold_records(&ColdQuery::new().with_galaxy(Galaxy::Codex))
        .unwrap();
    assert_eq!(codex_cold.len(), 1);
    assert_eq!(codex_cold[0].id, id1);

    // Query by tag
    let astronomy_cold = store
        .query_cold_records(&ColdQuery::new().with_tags(vec!["astronomy".into()]))
        .unwrap();
    assert_eq!(astronomy_cold.len(), 1);
    assert_eq!(astronomy_cold[0].id, id2);

    // Query by substring
    let quantum_cold = store
        .query_cold_records(&ColdQuery::new().with_content_substring("quantum"))
        .unwrap();
    assert_eq!(quantum_cold.len(), 1);
    assert_eq!(quantum_cold[0].id, id1);
}
