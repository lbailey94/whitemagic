use std::path::PathBuf;
use std::time::Instant;
use wm_gen3_vault::cold_storage::ColdStorageEngine;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("═══════════════════════════════════════════════════════════════");
    println!("  WhiteMagic Gen3 — Holographic Cold-Storage Indexer (DIR-10)");
    println!("═══════════════════════════════════════════════════════════════");

    let catalog_dir = PathBuf::from("/home/lucas/.local/share/whitemagic/cold_catalog");
    std::fs::create_dir_all(&catalog_dir)?;
    let catalog_db_path = catalog_dir.join("cold_catalog.db");

    let default_archive = PathBuf::from("/media/lucas/SD_CARD1/whitemagic-archives/whitemagic-desktop-archives-20261003.tar.zst");
    let archive_path = std::env::args()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or(default_archive);

    if !archive_path.exists() {
        eprintln!("Error: Archive path not found: {}", archive_path.display());
        std::process::exit(1);
    }

    let max_entries = std::env::var("WM_COLD_LIMIT")
        .ok()
        .and_then(|s| s.parse::<usize>().ok())
        .or(Some(500));

    println!("Target Archive: {}", archive_path.display());
    println!("Catalog DB:     {}", catalog_db_path.display());
    println!("Max Entries:    {:?}", max_entries);
    println!("Constraint:     Zero NVMe extraction, stream via /dev/shm LRU cache");

    let engine = ColdStorageEngine::new(&catalog_db_path, None)
        .map_err(|e| format!("ColdStorageEngine init error: {e}"))?;

    println!("\nStreaming archive header & cognitive files into 6D holographic catalog...");
    let t0 = Instant::now();

    let count = engine.index_archive_stream(&archive_path, max_entries)
        .map_err(|e| format!("Stream indexing failed: {e}"))?;

    let elapsed = t0.elapsed();
    println!("✓ Stream index complete in {:.2}s!", elapsed.as_secs_f64());
    println!("  Entries indexed into catalog: {}", count);

    // Demonstrate instant holographic search query
    let query = std::env::var("WM_COLD_QUERY").unwrap_or_else(|_| "whitemagic".to_string());
    println!("\nTesting holographic FTS5 retrieval for query: '{}'...", query);
    let st0 = Instant::now();
    let results = engine.search_cognitive_text(&query, 5).unwrap_or_default();
    let query_time = st0.elapsed();

    println!("✓ Query completed in {:.3}ms (found {} results):", query_time.as_secs_f64() * 1000.0, results.len());
    for (i, res) in results.iter().enumerate() {
        println!("  [{}] {} (size: {} B, score: {:.2})", i + 1, res.path_in_archive, res.size_bytes, res.score);
        println!("      6D Coords: [x:{}, y:{}, z:{}, tau:{}, sigma:{}, omega:{}]",
            res.coords_6d[0], res.coords_6d[1], res.coords_6d[2],
            res.coords_6d[3], res.coords_6d[4], res.coords_6d[5]);
        if !res.snippet.is_empty() {
            println!("      Snippet: {}", res.snippet.lines().next().unwrap_or(""));
        }
    }

    println!("═══════════════════════════════════════════════════════════════\n");
    Ok(())
}
