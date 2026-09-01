//! Read-only galactic memory audit: cross-galaxy id duplication, zombie
//! galaxies, and embedding orphans for one store.
//!
//! Usage: cargo run -p wm-memory --example galaxy_audit -- <store-path>

use std::collections::HashMap;
use wm_core::Galaxy;
use wm_memory::MemoryStore;

fn main() {
    let path = std::env::args().nth(1).expect("store path required");
    let store = MemoryStore::open_default(std::path::Path::new(&path)).expect("open store");

    let mut id_map: HashMap<uuid::Uuid, Vec<Galaxy>> = HashMap::new();
    let mut per_galaxy: Vec<(Galaxy, usize)> = Vec::new();

    for galaxy in Galaxy::memory_galaxies() {
        let mems = store.scan_all(galaxy).expect("scan failed");
        per_galaxy.push((galaxy, mems.len()));
        for m in &mems {
            id_map.entry(m.metadata.id).or_default().push(galaxy);
        }
    }

    println!("=== per-memory-galaxy counts ===");
    for (g, n) in &per_galaxy {
        let flag = if *n == 0 {
            "  <- zombie (no records)"
        } else {
            ""
        };
        println!("{:>12}: {:>6}{}", g.db_name(), n, flag);
    }

    let zombies: Vec<_> = Galaxy::all()
        .iter()
        .filter(|g| store.count(**g).unwrap_or(0) == 0)
        .map(|g| g.db_name().to_string())
        .collect();
    println!("\nzombie galaxies (0 records across all 14): {zombies:?}");

    let dupes: Vec<_> = id_map.iter().filter(|(_, v)| v.len() > 1).collect();
    println!("\n=== ids present in >1 memory galaxy: {} ===", dupes.len());
    let mut pair_counts: HashMap<String, usize> = HashMap::new();
    for (_, gs) in &dupes {
        let mut names: Vec<_> = gs.iter().map(|g| g.db_name().to_string()).collect();
        names.sort();
        *pair_counts.entry(names.join("+")).or_default() += 1;
    }
    let mut pairs: Vec<_> = pair_counts.into_iter().collect();
    pairs.sort_by_key(|entry| std::cmp::Reverse(entry.1));
    for (pair, n) in pairs {
        println!("{n:>6} ids: {pair}");
    }

    let emb_count = store.count(Galaxy::Embeddings).unwrap_or(0);
    let memory_total: usize = per_galaxy.iter().map(|(_, n)| n).sum();
    println!(
        "\nembeddings: {} records vs {} memories ({:.1}% coverage)",
        emb_count,
        memory_total,
        if memory_total > 0 {
            100.0 * emb_count as f64 / memory_total as f64
        } else {
            0.0
        }
    );

    let assoc = store.count(Galaxy::Associations).unwrap_or(0);
    let karma = store.count(Galaxy::Karma).unwrap_or(0);
    let dharma = store.count(Galaxy::Dharma).unwrap_or(0);
    println!("associations: {assoc} edges | karma entries: {karma} | dharma rules: {dharma}");
}
