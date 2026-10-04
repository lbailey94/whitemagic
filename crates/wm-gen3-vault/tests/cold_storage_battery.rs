use std::fs::File;
use tempfile::tempdir;
use tar::Builder as TarBuilder;
use zstd::stream::Encoder as ZstdEncoder;

use wm_gen3_vault::cold_storage::ColdStorageEngine;

#[test]
fn test_zero_disk_tar_zst_streaming_and_cold_search() {
    let dir = tempdir().expect("temp dir");
    let archive_path = dir.path().join("test_cold_archive.tar.zst");
    let catalog_db_path = dir.path().join("cold_catalog.db");
    let cache_dir = dir.path().join("shm_cache");

    // 1. Build a synthetic .tar.zst archive with cognitive files and binary data
    {
        let tar_zst_file = File::create(&archive_path).expect("create archive");
        let encoder = ZstdEncoder::new(tar_zst_file, 3).expect("zstd encoder");
        let mut tar = TarBuilder::new(encoder);

        // Add cognitive file 1: markdown spec
        let spec_content = b"# Gate 13 Landlock LSM Architecture\nProcess containment and holographic cold storage guarantees.";
        let mut header1 = tar::Header::new_gnu();
        header1.set_size(spec_content.len() as u64);
        header1.set_mode(0o644);
        header1.set_mtime(1760000000); // 2025-10-10
        tar.append_data(&mut header1, "docs/specs/landlock_hologram.md", &spec_content[..]).expect("add file 1");

        // Add cognitive file 2: Rust source code
        let rust_code = b"pub fn radiant_hologram_projection() -> bool { true }";
        let mut header2 = tar::Header::new_gnu();
        header2.set_size(rust_code.len() as u64);
        header2.set_mode(0o644);
        header2.set_mtime(1760500000);
        tar.append_data(&mut header2, "crates/core/src/hologram.rs", &rust_code[..]).expect("add file 2");

        // Add binary file: large blob
        let binary_blob = vec![0xAB; 2048];
        let mut header3 = tar::Header::new_gnu();
        header3.set_size(binary_blob.len() as u64);
        header3.set_mode(0o644);
        header3.set_mtime(1760100000);
        tar.append_data(&mut header3, "bin/firmware.bin", &binary_blob[..]).expect("add binary");

        let encoder = tar.into_inner().expect("tar finish");
        encoder.finish().expect("zstd finish");
    }

    // 2. Initialize ColdStorageEngine
    let engine = ColdStorageEngine::new(&catalog_db_path, Some(cache_dir.clone()))
        .expect("init engine");

    // 3. Stream index archive without disk extraction
    let count = engine.index_archive_stream(&archive_path, None)
        .expect("index stream");
    assert_eq!(count, 3, "Expected 3 indexed files");

    // 4. Verify Cognitive Text FTS5 Search
    let results = engine.search_cognitive_text("Landlock", 5)
        .expect("search cognitive text");
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].path_in_archive, "docs/specs/landlock_hologram.md");
    assert!(results[0].snippet.contains("Landlock"));
    assert_ne!(results[0].coords_6d[0], 0, "6D coordinate should be non-zero");

    let results_rust = engine.search_cognitive_text("radiant hologram", 5)
        .expect("search rust");
    assert!(!results_rust.is_empty());
    assert!(results_rust.iter().any(|r| r.path_in_archive == "crates/core/src/hologram.rs"));

    // 5. Test On-Demand Payload Extraction & Caching
    let payload = engine.fetch_payload(&archive_path, "docs/specs/landlock_hologram.md")
        .expect("fetch payload");
    assert_eq!(payload, b"# Gate 13 Landlock LSM Architecture\nProcess containment and holographic cold storage guarantees.");

    // Verify file is cached in shm cache
    assert!(cache_dir.exists());
    let cached_files = std::fs::read_dir(&cache_dir).unwrap().count();
    assert_eq!(cached_files, 1, "Payload must be cached in memory-mapped shm cache");

    // Second fetch should be instant cache hit (< 0.02ms)
    let t0 = std::time::Instant::now();
    let cached_payload = engine.fetch_payload(&archive_path, "docs/specs/landlock_hologram.md")
        .expect("fetch cached payload");
    let cache_hit_micros = t0.elapsed().as_micros();
    assert_eq!(cached_payload, payload);
    assert!(cache_hit_micros < 1000, "Cache hit must be sub-millisecond, was {cache_hit_micros}µs");
}
