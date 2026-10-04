//! WhiteMagic Gen3 — Starter Guide Galaxy & Fluid Galaxy Management.
//!
//! Provides the foundational `guide` galaxy seeded on first initialization or
//! `wm grimoire`, plus zero-overhead galaxy branching, forking, and listing.

#![forbid(unsafe_code)]

use std::collections::{BTreeMap, BTreeSet};
use serde::{Deserialize, Serialize};
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::ops::{ImportKind, RememberItem, Substrate};

/// A summary of an active galaxy partition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GalaxySummary {
    pub name: String,
    pub record_count: usize,
    pub tags: Vec<String>,
    pub sample_preview: String,
    pub is_starter: bool,
}

/// The foundational records comprising the starter `guide` galaxy.
pub const STARTER_GUIDE_RECORDS: &[(&str, &str, ImportKind)] = &[
    (
        "Welcome to WhiteMagic Gen3: a sovereign, local-first memory and cognitive continuity substrate for AI agents. Memory lives where cognition lives—100% offline, pure Rust, zero telemetry, sub-microsecond retrieval via memory-mapped LMDB.",
        "corpus:guide:welcome,sovereignty,genesis",
        ImportKind::System,
    ),
    (
        "The 5D Holographic Coordinate Matrix: WhiteMagic organizes all thoughts across 5 dimensions: X (structural logic & truth), Y (creative abstraction & intuition), Z (epistemic domain context), T (temporal recency & decay), and V (verification & empirical grounding). Every memory is addressable in this continuous geometric space.",
        "corpus:guide:architecture,5d_coordinates",
        ImportKind::System,
    ),
    (
        "Galaxies & Sovereign Namespaces: In WhiteMagic, a galaxy is a partitioned universe of memories. You are currently in the 'guide' galaxy. You can fluidly fork or create new galaxies for projects, workflows, or personas (e.g. 'wm galaxy fork guide project-alpha' or MCP 'galaxy_fork') without modifying or polluting foundational knowledge.",
        "corpus:guide:galaxies,branching,fluidity",
        ImportKind::System,
    ),
    (
        "Cognitive Dual-Phase Incubation (Dreaming): Idle periods allow WhiteMagic to perform NREM compaction (pruning noise, strengthening associations) and REM synthesis (generating heuristic action skeletons). Run 'wm dream' or let the background cycle run during sleep for autonomous self-improvement.",
        "corpus:guide:rsi,dreaming,consolidation",
        ImportKind::System,
    ),
    (
        "Continuity & Handoffs: Session boundaries are not memory boundaries. WhiteMagic generates cryptographically signed continuity receipts (session_checkpoint) so you can resume tasks seamlessly across IDE restarts, context drops, and agent handoffs.",
        "corpus:guide:continuity,sessions,handoff",
        ImportKind::System,
    ),
    (
        "First-Run Practice: Create your first memory in a new galaxy now! For example, run: wm remember \"Initialized project plan\" --source \"corpus:workspace:plan\" or call the memory_remember MCP tool with galaxy=\"workspace\" to begin compounding your own universe.",
        "corpus:guide:quickstart,practice,getting_started",
        ImportKind::Reported,
    ),
];

/// Extracts the galaxy name from a record's source string.
///
/// Canonical source format: `corpus:<galaxy>:<tags>`
/// Fallback: if not prefixed with `corpus:`, returns `"codex"`.
#[must_use]
pub fn extract_galaxy_from_source(source: &str) -> String {
    if let Some(rest) = source.strip_prefix("corpus:") {
        if let Some(colon_idx) = rest.find(':') {
            let galaxy = &rest[..colon_idx];
            if !galaxy.trim().is_empty() {
                return galaxy.trim().to_string();
            }
        } else if !rest.trim().is_empty() {
            return rest.trim().to_string();
        }
    }
    "codex".to_string()
}

/// Extracts tags from a record's source string.
#[must_use]
pub fn extract_tags_from_source(source: &str) -> Vec<String> {
    if let Some(rest) = source.strip_prefix("corpus:") {
        if let Some(colon_idx) = rest.find(':') {
            return rest[colon_idx + 1..]
                .split(',')
                .map(|t| t.trim().to_string())
                .filter(|t| !t.is_empty())
                .collect();
        }
    }
    Vec::new()
}

/// Seeds the starter guide galaxy into the substrate if the store is empty.
///
/// Returns the number of seeded records (0 if store already contains records).
pub fn seed_starter_guide_if_empty(substrate: &mut Substrate) -> Result<usize, String> {
    let count = substrate.store().record_count().unwrap_or(0);
    if count > 0 {
        return Ok(0);
    }
    seed_starter_guide_force(substrate)
}

/// Seeds the starter guide galaxy unconditionally (e.g. for `wm init` or initial setup).
pub fn seed_starter_guide_force(substrate: &mut Substrate) -> Result<usize, String> {
    let authority = RatifiedChannel::mint("wm-genesis-guide");
    substrate.set_intake_authority(authority);

    let items: Vec<RememberItem> = STARTER_GUIDE_RECORDS
        .iter()
        .map(|(content, source, kind)| RememberItem {
            content: (*content).to_string(),
            source: (*source).to_string(),
            kind: *kind,
        })
        .collect();

    let results = substrate.remember_batch(&items);
    let mut committed = 0;
    for res in results {
        match res {
            Ok(_) => committed += 1,
            Err(e) => return Err(format!("Failed to seed guide memory: {e}")),
        }
    }
    Ok(committed)
}

/// Lists all active galaxies present in the substrate.
pub fn list_galaxies(substrate: &Substrate) -> Result<Vec<GalaxySummary>, String> {
    let store = substrate.store();
    let total_count = store.record_count().unwrap_or(0);

    if total_count == 0 {
        return Ok(vec![GalaxySummary {
            name: "guide".to_string(),
            record_count: 0,
            tags: vec!["starter".to_string()],
            sample_preview: "Empty substrate. Run 'wm grimoire' to seed.".to_string(),
            is_starter: true,
        }]);
    }

    let mut map: BTreeMap<String, (usize, BTreeSet<String>, String)> = BTreeMap::new();

    if total_count > 2000 {
        // Fast-path for large databases (e.g. 400k+ records):
        // Custom galaxies are prefixed with 'corpus:<name>:...'.
        // Use postings index to rapidly locate custom galaxy records in microseconds,
        // without scanning and allocating gigabytes of data into RAM.
        let mut scanned_ids = BTreeSet::new();

        if let Ok(corpus_ids) = store.postings("corpus") {
            for id in corpus_ids {
                scanned_ids.insert(id);
            }
        }
        if let Ok(guide_ids) = store.postings("guide") {
            for id in guide_ids {
                scanned_ids.insert(id);
            }
        }

        let mut custom_count = 0;
        for id in scanned_ids {
            if let Ok(Some(rec)) = store.get_record(id) {
                let gal = extract_galaxy_from_source(rec.source());
                if gal != "codex" {
                    custom_count += 1;
                    let tags = extract_tags_from_source(rec.source());
                    let preview = if rec.content().len() > 80 {
                        let mut end = 80;
                        while end > 0 && !rec.content().is_char_boundary(end) {
                            end -= 1;
                        }
                        format!("{}...", &rec.content()[..end])
                    } else {
                        rec.content().to_string()
                    };

                    let entry = map.entry(gal).or_insert((0, BTreeSet::new(), preview));
                    entry.0 += 1;
                    for t in tags {
                        entry.1.insert(t);
                    }
                }
            }
        }

        // Default 'codex' galaxy gets the remainder
        let codex_count = total_count.saturating_sub(custom_count);
        if codex_count > 0 {
            let sample_preview = if let Ok(Some(rec)) = store.get_record(total_count as u64) {
                if rec.content().len() > 80 {
                    let mut end = 80;
                    while end > 0 && !rec.content().is_char_boundary(end) {
                        end -= 1;
                    }
                    format!("{}...", &rec.content()[..end])
                } else {
                    rec.content().to_string()
                }
            } else {
                "Canonical codex memory space.".to_string()
            };
            let mut codex_tags = BTreeSet::new();
            codex_tags.insert("codex".to_string());
            codex_tags.insert("primary".to_string());
            map.insert("codex".to_string(), (codex_count, codex_tags, sample_preview));
        }
    } else {
        // Small/starter database: direct sequential iteration
        let records = store
            .iter_records()
            .map_err(|e| format!("Store read error: {e}"))?;

        for rec in records {
            let gal = extract_galaxy_from_source(rec.source());
            let tags = extract_tags_from_source(rec.source());
            let preview = if rec.content().len() > 80 {
                let mut end = 80;
                while end > 0 && !rec.content().is_char_boundary(end) {
                    end -= 1;
                }
                format!("{}...", &rec.content()[..end])
            } else {
                rec.content().to_string()
            };

            let entry = map.entry(gal).or_insert((0, BTreeSet::new(), preview));
            entry.0 += 1;
            for t in tags {
                entry.1.insert(t);
            }
        }
    }

    let mut summaries = Vec::new();
    for (name, (count, tag_set, preview)) in map {
        let is_starter = name == "guide";
        summaries.push(GalaxySummary {
            is_starter,
            name,
            record_count: count,
            tags: tag_set.into_iter().take(8).collect(),
            sample_preview: preview,
        });
    }

    Ok(summaries)
}

/// Forks an existing galaxy into a new galaxy partition.
///
/// Clones all records from `source_galaxy` into `target_galaxy` with updated
/// provenance tags and fresh record IDs.
pub fn fork_galaxy(
    substrate: &mut Substrate,
    source_galaxy: &str,
    target_galaxy: &str,
) -> Result<usize, String> {
    if source_galaxy == target_galaxy {
        return Err("Source and target galaxies must be distinct".to_string());
    }

    let records = substrate
        .store()
        .iter_records()
        .map_err(|e| format!("Store read error: {e}"))?;

    let mut candidates: Vec<RememberItem> = Vec::new();

    for rec in records {
        let gal = extract_galaxy_from_source(rec.source());
        if gal == source_galaxy {
            let tags = extract_tags_from_source(rec.source());
            let tag_str = if tags.is_empty() {
                format!("forked_from_{source_galaxy}")
            } else {
                format!("{},forked_from_{source_galaxy}", tags.join(","))
            };
            let new_source = format!("corpus:{target_galaxy}:{tag_str}");

            candidates.push(RememberItem {
                content: rec.content().to_string(),
                source: new_source,
                kind: ImportKind::Reported,
            });
        }
    }

    if candidates.is_empty() {
        return Err(format!("Source galaxy '{source_galaxy}' has no records to fork."));
    }

    let authority = RatifiedChannel::mint(&format!("wm-fork-{target_galaxy}"));
    substrate.set_intake_authority(authority);

    let _count_to_fork = candidates.len();
    let results = substrate.remember_batch(&candidates);
    let mut successful = 0;
    for res in results {
        if res.is_ok() {
            successful += 1;
        }
    }

    if successful == 0 {
        return Err("Failed to commit any records during galaxy fork".to_string());
    }

    Ok(successful)
}

/// Creates a new galaxy with an initial genesis beacon.
pub fn create_galaxy(
    substrate: &mut Substrate,
    name: &str,
    description: Option<&str>,
) -> Result<u64, String> {
    let clean_name = name.trim().to_lowercase();
    if clean_name.is_empty() || clean_name.contains(':') || clean_name.contains(' ') {
        return Err("Galaxy name must be non-empty and cannot contain colons or spaces".to_string());
    }

    let desc = description.unwrap_or("Galaxy genesis anchor.");
    let source = format!("corpus:{clean_name}:genesis,beacon");

    let item = RememberItem {
        content: format!("Galaxy '{clean_name}' established. {desc}"),
        source,
        kind: ImportKind::System,
    };

    let authority = RatifiedChannel::mint(&format!("wm-genesis-{clean_name}"));
    substrate.set_intake_authority(authority);

    let results = substrate.remember_batch(&[item]);
    match results.into_iter().next() {
        Some(Ok(id)) => Ok(id),
        Some(Err(e)) => Err(format!("Failed to create galaxy: {e}")),
        None => Err("Substrate intake produced no output".to_string()),
    }
}
