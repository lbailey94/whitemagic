//! wm_forensic — temporary recovery tool for deleted memories.
//!
//! LMDB frees pages on delete but does not zero them until reuse. This tool
//! scans the raw data.mdb for every occurrence of each target UUID and tries
//! to decode the bytes that follow as a msgpack `Memory`, validating that the
//! decoded metadata.id matches. Recovered memories are written as JSONL for
//! review, and can be restored with their original IDs + tantivy re-indexing.
//!
//! Usage:
//!   wm_forensic extract <data.mdb> <ids.txt> <out.jsonl>
//!   wm_forensic restore <store-dir> <in.jsonl>

use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader, BufWriter, Write};

use wm_core::Galaxy;
use wm_memory::memory::Memory;
use wm_memory::search::SearchEngine;
use wm_memory::store::MemoryStore;

const PAGE_SIZE: usize = 4096;
const MAX_OVERFLOW_PAGES: usize = 64;
const MAX_TRAIL: usize = 512 * 1024;

fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("extract") => extract(&args[2], &args[3], &args[4]),
        Some("restore") => restore(&args[2], &args[3]),
        _ => {
            eprintln!(
                "usage: wm_forensic extract <data.mdb> <ids.txt> <out.jsonl> | restore \
                 <store-dir> <in.jsonl>"
            );
            std::process::exit(2);
        }
    }
}

// ── Extract ───────────────────────────────────────────────────────────────

fn extract(data_path: &str, ids_path: &str, out_path: &str) -> anyhow::Result<()> {
    let targets = load_targets(ids_path)?;
    println!("targets: {}", targets.len());

    let data = std::fs::read(data_path)?;
    println!("file size: {} bytes", data.len());

    let mut recovered: HashMap<uuid::Uuid, Memory> = HashMap::new();

    for (&raw_key, id) in &targets {
        // Find every occurrence of the 16-byte key in the file.
        let mut start = 0usize;
        let mut occurrences = 0usize;
        while let Some(pos) = find(&data, &raw_key, start) {
            occurrences += 1;
            start = pos + 1;
            if let Some(mem) = try_decode_at(&data, pos, *id) {
                recovered.insert(*id, mem);
                break;
            }
            // Also try resolving as an overflow reference (8-byte pgno after key).
            if let Some(mem) = try_overflow_at(&data, pos, *id) {
                recovered.insert(*id, mem);
                break;
            }
        }
        println!(
            "  {}: {} occurrences -> {}",
            id,
            occurrences,
            if recovered.contains_key(id) {
                "RECOVERED"
            } else {
                "not found"
            }
        );
    }

    println!(
        "\nrecovered {} / {} memories",
        recovered.len(),
        targets.len()
    );
    let mut out = BufWriter::new(File::create(out_path)?);
    let mut ids: Vec<_> = recovered.keys().copied().collect();
    ids.sort();
    for id in &ids {
        let mem = &recovered[id];
        serde_json::to_writer(&mut out, mem)?;
        out.write_all(b"\n")?;
        let preview: String = mem.content.chars().take(120).collect();
        println!(
            "  {} [{:?}] {}",
            id,
            mem.metadata.galaxy,
            preview.replace('\n', " ")
        );
    }
    out.flush()?;
    println!("wrote {out_path}");
    Ok(())
}

fn load_targets(ids_path: &str) -> anyhow::Result<HashMap<[u8; 16], uuid::Uuid>> {
    let mut map = HashMap::new();
    for line in BufReader::new(File::open(ids_path)?).lines() {
        let line = line?.trim().to_string();
        if line.is_empty() {
            continue;
        }
        let id = uuid::Uuid::parse_str(&line)?;
        map.insert(*id.as_bytes(), id);
    }
    Ok(map)
}

/// Simple substring search.
fn find(data: &[u8], needle: &[u8; 16], start: usize) -> Option<usize> {
    if start + needle.len() > data.len() {
        return None;
    }
    data[start..]
        .windows(needle.len())
        .position(|w| w == needle)
        .map(|i| start + i)
}

/// Tries to decode a Memory from the bytes immediately following the key,
/// growing the window until decode succeeds (msgpack is self-delimiting).
fn try_decode_at(data: &[u8], key_pos: usize, expected: uuid::Uuid) -> Option<Memory> {
    let vstart = key_pos + 16;
    if vstart >= data.len() {
        return None;
    }
    let first = data[vstart];
    // Quick reject: msgpack Memory starts with fixarray(3) = 0x93.
    if first != 0x93 {
        return None;
    }
    let window = &data[vstart..(vstart + MAX_TRAIL).min(data.len())];
    for size in (2..=window.len().min(64 * 1024)).step_by(1) {
        if let Ok(mem) = rmp_serde::from_slice::<Memory>(&window[..size]) {
            if mem.metadata.id == expected {
                return Some(mem);
            }
            return None; // decoded a different value -> not our node
        }
    }
    None
}

/// If the 8 bytes after the key are an overflow page number, collect the
/// overflow pages and try decoding the concatenated data.
fn try_overflow_at(data: &[u8], key_pos: usize, expected: uuid::Uuid) -> Option<Memory> {
    let ref_pos = key_pos + 16;
    if ref_pos + 8 > data.len() {
        return None;
    }
    let pgno = u64::from_le_bytes(data[ref_pos..ref_pos + 8].try_into().ok()?);
    let base = pgno as usize * PAGE_SIZE;
    if base >= data.len() {
        return None;
    }
    let mut buf = Vec::new();
    for page_idx in 0..MAX_OVERFLOW_PAGES {
        let start = base + page_idx * PAGE_SIZE;
        if start + PAGE_SIZE > data.len() {
            break;
        }
        buf.extend_from_slice(&data[start + 8..start + PAGE_SIZE]);
        if let Ok(mem) = rmp_serde::from_slice::<Memory>(&buf) {
            if mem.metadata.id == expected {
                return Some(mem);
            }
        }
    }
    None
}

// ── Restore ───────────────────────────────────────────────────────────────

fn restore(store_dir: &str, jsonl_path: &str) -> anyhow::Result<()> {
    let store_dir = std::path::Path::new(store_dir);
    let store = MemoryStore::open(store_dir, 4 * 1024 * 1024 * 1024)?;
    let search_path = store_dir.join("tantivy");
    let search = SearchEngine::open(&search_path)?;

    let mut restored = 0u32;
    for (idx, line) in BufReader::new(File::open(jsonl_path)?).lines().enumerate() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let mem: Memory = serde_json::from_str(&line)
            .map_err(|e| anyhow::anyhow!("line {}: invalid JSON: {e}", idx + 1))?;
        let id = mem.metadata.id;
        let galaxy = mem.metadata.galaxy;
        if let Err(e) = store.put(galaxy, &mem) {
            println!("  SKIP {id}: put failed: {e}");
            continue;
        }
        let mut writer = search.writer()?;
        search.add_document(
            &mut writer,
            &id.to_string(),
            galaxy.db_name(),
            &mem.content,
            &mem.metadata.tags,
            mem.metadata.created_at.timestamp(),
        )?;
        search.commit(&mut writer)?;
        restored += 1;
        println!("  restored {id} [{galaxy:?}] tags={:?}", mem.metadata.tags);
    }
    println!("restored {restored} memories");
    Ok(())
}

#[allow(dead_code)]
const fn _galaxy_guard(_: Galaxy) {}
