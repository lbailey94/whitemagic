//! Tokio Clone Army & Galactic Triage Engine (PSR-005 / Operation Legion Heir).
//!
//! Multi-core parallel execution engine using Rayon and Tokio to deploy specialized
//! computational clone armies for sub-millisecond codebase scanning and memory triage.

#![forbid(unsafe_code)]

use async_trait::async_trait;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Instant;

use uuid::Uuid;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{AssociationStore, Memory, MemoryStore, SearchEngine};

// ── 1. The 12 Clone Army Types (from wm2_clone_army.rs) ───────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ArmyType {
    FileSearch,
    GalacticTriage,
    ShadowConsensus,
    GeneseedMiner,
    BatchPipeline,
    ThoughtPulse,
}

impl ArmyType {
    #[must_use]
    pub const fn name(&self) -> &'static str {
        match self {
            Self::FileSearch => "file_search",
            Self::GalacticTriage => "galactic_triage",
            Self::ShadowConsensus => "shadow_consensus",
            Self::GeneseedMiner => "geneseed_miner",
            Self::BatchPipeline => "batch_pipeline",
            Self::ThoughtPulse => "thought_pulse",
        }
    }

    /// Parse a caller-supplied army type. Unknown names are rejected rather
    /// than acknowledged — a completion receipt must never be issued for
    /// work that did not happen.
    #[must_use]
    pub fn parse(raw: &str) -> Option<Self> {
        match raw.trim().to_ascii_lowercase().as_str() {
            "file_search" => Some(Self::FileSearch),
            "galactic_triage" => Some(Self::GalacticTriage),
            "shadow_consensus" => Some(Self::ShadowConsensus),
            "geneseed_miner" => Some(Self::GeneseedMiner),
            "batch_pipeline" => Some(Self::BatchPipeline),
            "thought_pulse" => Some(Self::ThoughtPulse),
            _ => None,
        }
    }

    /// Redirect for reserved names that have a real tool behind them.
    /// Names without any execution engine must be rejected, not simulated.
    #[must_use]
    pub const fn redirect(&self) -> Option<&'static str> {
        match self {
            Self::FileSearch => None,
            Self::GalacticTriage => Some("galaxy.triage_sweep"),
            Self::ShadowConsensus => None,
            Self::GeneseedMiner => Some("geneseed.mine"),
            Self::BatchPipeline => None,
            Self::ThoughtPulse => None,
        }
    }
}

// ── 2. Army Deploy Tool ───────────────────────────────────────────────

pub struct ArmyDeployTool {
    _store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ArmyDeployTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            _store: store,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Filesystem],
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for ArmyDeployTool {
    fn name(&self) -> &str {
        "army.deploy"
    }

    fn gana(&self) -> Gana {
        Gana::TurtleBeak
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Deploy a parallel Rayon file-search swarm for rapid codebase scanning and pattern detection. Only army_type=file_search has an execution engine; all other army-type names are rejected rather than simulated."
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let objective = args
            .get("objective")
            .and_then(|v| v.as_str())
            .unwrap_or("general_sweep");
        let army_type_str = args
            .get("army_type")
            .and_then(|v| v.as_str())
            .unwrap_or("file_search");
        let query = args.get("query").and_then(|v| v.as_str()).unwrap_or("");
        let target_path = args
            .get("target_path")
            .and_then(|v| v.as_str())
            .unwrap_or(".");
        let clone_count = args
            .get("clone_count")
            .and_then(Value::as_u64)
            .unwrap_or(10_000) as usize;

        let start = Instant::now();

        let army_type = ArmyType::parse(army_type_str).ok_or_else(|| {
            wm_core::CoreError::InvalidArgs(format!(
                "unknown army_type '{army_type_str}'. Valid: file_search (the only type with an execution engine). Reserved names without engines: galactic_triage (use galaxy.triage_sweep), geneseed_miner (use geneseed.mine), shadow_consensus, batch_pipeline, thought_pulse."
            ))
        })?;
        if army_type != ArmyType::FileSearch {
            let hint = match army_type.redirect() {
                Some(tool) => format!(" Use {tool} instead — it is the real tool behind that name."),
                None => " No execution engine exists behind that name; nothing was evaluated and no consensus was reached.".to_string(),
            };
            return Err(wm_core::CoreError::InvalidArgs(format!(
                "army_type '{}' names a reserved formation with no execution engine behind it.{hint} Only file_search executes.",
                army_type.name()
            )));
        }

        match army_type {
            ArmyType::FileSearch => {
                let root = PathBuf::from(target_path);
                let results = scan_directory_parallel(&root, query, clone_count);
                let duration_ms = start.elapsed().as_millis() as u64;
                let files_scanned = results.files_scanned;
                let matches_found = results.matches.len();
                let throughput = if duration_ms > 0 {
                    (files_scanned as f64 / duration_ms as f64) * 1000.0
                } else {
                    files_scanned as f64 * 1000.0
                };

                Ok(json!({
                    "status": "completed",
                    "army_type": "file_search",
                    "objective": objective,
                    "target_path": target_path,
                    "files_scanned": files_scanned,
                    "matches_found": matches_found,
                    "duration_ms": duration_ms,
                    "throughput_files_per_sec": throughput,
                    "top_matches": results.matches.into_iter().take(20).collect::<Vec<_>>()
                }))
            }
            // Unreachable: every non-FileSearch variant is rejected above so
            // that no completion receipt can ever be issued for simulated work.
            _ => Err(wm_core::CoreError::InvalidArgs(format!(
                "army_type '{}' has no execution engine. Only file_search executes.",
                army_type.name()
            ))),
        }
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── 3. Parallel File Scanning Engine ──────────────────────────────────

struct FileScanReport {
    files_scanned: usize,
    matches: Vec<FileMatch>,
}

#[derive(Serialize)]
struct FileMatch {
    path: String,
    line_number: usize,
    line_snippet: String,
}

fn scan_directory_parallel(root: &Path, query: &str, max_files: usize) -> FileScanReport {
    let mut files = Vec::new();
    collect_files_recursive(root, &mut files, max_files);

    let query_lower = query.to_lowercase();
    let files_scanned = files.len();

    let matches: Vec<FileMatch> = files
        .par_iter()
        .flat_map(|path| {
            let mut file_matches = Vec::new();
            if let Ok(content) = std::fs::read_to_string(path) {
                for (idx, line) in content.lines().enumerate() {
                    if query.is_empty() || line.to_lowercase().contains(&query_lower) {
                        file_matches.push(FileMatch {
                            path: path.to_string_lossy().to_string(),
                            line_number: idx + 1,
                            line_snippet: line.trim().chars().take(120).collect(),
                        });
                        if file_matches.len() >= 5 {
                            break;
                        }
                    }
                }
            }
            file_matches
        })
        .collect();

    FileScanReport {
        files_scanned,
        matches,
    }
}

fn collect_files_recursive(dir: &Path, files: &mut Vec<PathBuf>, limit: usize) {
    if files.len() >= limit {
        return;
    }
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            if files.len() >= limit {
                break;
            }
            let path = entry.path();
            let file_name = entry.file_name().to_string_lossy().to_string();

            // Skip common build and VCS noise
            if file_name.starts_with('.')
                || file_name == "target"
                || file_name == "node_modules"
                || file_name == "venv"
            {
                continue;
            }

            if path.is_dir() {
                collect_files_recursive(&path, files, limit);
            } else if path.is_file() {
                files.push(path);
            }
        }
    }
}

// ── 4. Galactic Triage Sweep Tool ─────────────────────────────────────

pub struct GalacticTriageTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalacticTriageTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Galaxy("*".into())],
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[derive(Serialize, Default)]
struct GalaxyTriageStats {
    total: usize,
    signal_count: usize,
    noise_count: usize,
    signal_percentage: f32,
    cold_storage_candidate_ids: Vec<String>,
}

#[async_trait]
impl Tool for GalacticTriageTool {
    fn name(&self) -> &str {
        "galaxy.triage_sweep"
    }

    fn gana(&self) -> Gana {
        Gana::Room
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Deploy a parallel triage army across all memory galaxies to separate high-signal insights from telemetry noise and recommend cold-storage rotations."
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let sample_limit = args
            .get("sample_limit")
            .and_then(Value::as_u64)
            .unwrap_or(0) as usize;
        let start = Instant::now();

        let galaxies = Galaxy::memory_galaxies();
        let mut galaxy_reports = HashMap::new();
        let mut total_records = 0usize;
        let mut total_signal = 0usize;
        let mut total_noise = 0usize;
        let mut total_cold_candidates = Vec::new();

        for galaxy in galaxies {
            let limit = if sample_limit > 0 {
                sample_limit
            } else {
                50_000
            };
            let memories = self.store.scan(galaxy, limit).unwrap_or_default();
            if memories.is_empty() {
                continue;
            }

            // Rayon parallel classification across memories
            let classification: Vec<(bool, String)> = memories
                .par_iter()
                .map(|mem| {
                    let is_noise = classify_is_noise(mem);
                    (!is_noise, mem.metadata.id.to_string())
                })
                .collect();

            let count = classification.len();
            let signal = classification.iter().filter(|(sig, _)| *sig).count();
            let noise = count - signal;
            let signal_pct = if count > 0 {
                (signal as f32 / count as f32) * 100.0
            } else {
                100.0
            };

            let cold_candidates: Vec<String> = classification
                .into_iter()
                .filter(|(sig, _)| !*sig)
                .map(|(_, id)| id)
                .take(10)
                .collect();

            total_records += count;
            total_signal += signal;
            total_noise += noise;
            total_cold_candidates.extend(cold_candidates.clone());

            galaxy_reports.insert(
                galaxy.db_name().to_string(),
                GalaxyTriageStats {
                    total: count,
                    signal_count: signal,
                    noise_count: noise,
                    signal_percentage: signal_pct,
                    cold_storage_candidate_ids: cold_candidates,
                },
            );
        }

        let duration_ms = start.elapsed().as_millis() as u64;
        let overall_signal_pct = if total_records > 0 {
            (total_signal as f32 / total_records as f32) * 100.0
        } else {
            100.0
        };
        let throughput = if duration_ms > 0 {
            (total_records as f64 / duration_ms as f64) * 1000.0
        } else {
            total_records as f64 * 1000.0
        };

        Ok(json!({
            "status": "completed",
            "total_records_analyzed": total_records,
            "total_signal_insights": total_signal,
            "total_telemetry_noise": total_noise,
            "overall_signal_percentage": format!("{:.1}%", overall_signal_pct),
            "overall_noise_percentage": format!("{:.1}%", 100.0 - overall_signal_pct),
            "duration_ms": duration_ms,
            "records_per_second": throughput,
            "recommended_for_cold_storage_count": total_noise,
            "sample_cold_storage_ids": total_cold_candidates.into_iter().take(25).collect::<Vec<_>>(),
            "galaxies": galaxy_reports
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── 5. Galactic Cold Storage Rotation Tool ────────────────────────────

pub struct GalacticColdRotateTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    associations: Option<Arc<AssociationStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

/// Records per chunk: chunked two-phase archive → verify → delete.
const ROTATE_CHUNK_SIZE: usize = 1_000;

/// A rotation candidate: serialized form plus identity for verification.
struct RotateCandidate {
    galaxy: Galaxy,
    id: Uuid,
    json: String,
}

/// Keep archive filenames safe: only `[A-Za-z0-9._-]` survive.
fn sanitize_filename_component(raw: &str) -> String {
    raw.chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '-' || c == '_' || c == '.' {
                c
            } else {
                '_'
            }
        })
        .collect()
}

/// Verify a chunk archive before any source record is deleted: every line
/// must parse as JSON carrying a metadata id, and the id set must exactly
/// match the chunk that was written.
fn verify_chunk_archive(path: &Path, expected_ids: &[Uuid]) -> wm_core::Result<()> {
    let content = std::fs::read_to_string(path).map_err(|e| {
        wm_core::CoreError::Memory(format!(
            "failed to re-read cold archive {} for verification: {e}",
            path.display()
        ))
    })?;
    let mut seen = std::collections::HashSet::new();
    for (line_no, line) in content.lines().enumerate() {
        let value: Value = serde_json::from_str(line).map_err(|e| {
            wm_core::CoreError::Memory(format!(
                "cold archive {} line {} is not valid JSON ({e}); refusing to delete sources",
                path.display(),
                line_no + 1
            ))
        })?;
        let id = value
            .get("metadata")
            .and_then(|meta| meta.get("id"))
            .and_then(Value::as_str)
            .or_else(|| value.get("id").and_then(Value::as_str))
            .ok_or_else(|| {
                wm_core::CoreError::Memory(format!(
                    "cold archive {} line {} carries no memory id; refusing to delete sources",
                    path.display(),
                    line_no + 1
                ))
            })?;
        seen.insert(id.to_string());
    }
    let expected: std::collections::HashSet<String> =
        expected_ids.iter().map(Uuid::to_string).collect();
    if seen != expected {
        return Err(wm_core::CoreError::Memory(format!(
            "cold archive {} holds {} records but chunk had {}; refusing to delete sources",
            path.display(),
            seen.len(),
            expected.len()
        )));
    }
    Ok(())
}

impl GalacticColdRotateTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            search: None,
            associations: None,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Galaxy("*".into())],
                writes: vec![
                    Resource::Galaxy("*".into()),
                    Resource::Filesystem,
                    Resource::SearchIndex,
                ],
                destructive: true,
                ..Default::default()
            },
        }
    }

    /// Attach full-text de-indexing (mirrors `memory.deduplicate`).
    /// Without it, rotated records linger in search results; the run
    /// reports cleanup as skipped.
    #[must_use]
    pub fn with_search(mut self, search: Arc<SearchEngine>) -> Self {
        self.search = Some(search);
        self
    }

    /// Attach association cleanup for rotated memories. Without it, edges
    /// touching rotated records are left behind; the run reports it.
    #[must_use]
    pub fn with_associations(mut self, associations: Arc<AssociationStore>) -> Self {
        self.associations = Some(associations);
        self
    }
}

#[async_trait]
impl Tool for GalacticColdRotateTool {
    fn name(&self) -> &str {
        "galaxy.cold_rotate"
    }

    fn gana(&self) -> Gana {
        Gana::Room
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Rotate operational telemetry noise and raw friction logs out of active LMDB storage into persistent cold-storage JSONL archives. Chunked two-phase commit (archive, verify, then delete) that fails closed on any archive error. The destructive apply path requires confirm:true through dispatch; dry_run defaults to true."
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let dry_run = args.get("dry_run").and_then(Value::as_bool).unwrap_or(true);
        let default_output = if let Ok(p) = std::env::var("WM_COLD_STORAGE") {
            PathBuf::from(p)
        } else if let Ok(h) = std::env::var("HOME") {
            PathBuf::from(h).join(".whitemagic").join("cold_storage")
        } else {
            PathBuf::from("./cold_storage")
        };
        let output_dir = match args.get("output_dir").and_then(Value::as_str) {
            Some(p) => PathBuf::from(p),
            None => default_output,
        };
        let start = Instant::now();
        let project_name = args
            .get("project_name")
            .and_then(Value::as_str)
            .map(sanitize_filename_component);

        let target_galaxy_str = args.get("galaxy").and_then(Value::as_str);
        let galaxies: Vec<Galaxy> = if let Some(g_str) = target_galaxy_str {
            if g_str == "all" {
                Galaxy::memory_galaxies().to_vec()
            } else {
                vec![super::common::parse_galaxy(g_str)?]
            }
        } else {
            Galaxy::memory_galaxies().to_vec()
        };
        let scan_limit = args.get("limit").and_then(Value::as_u64).unwrap_or(250_000) as usize;

        // Phase 0 — collect candidates. No writes of any kind happen here;
        // serialization failures abort before anything is touched.
        let mut total_scanned = 0usize;
        let mut candidates: Vec<RotateCandidate> = Vec::new();
        for galaxy in &galaxies {
            let memories = self.store.scan(*galaxy, scan_limit).unwrap_or_default();
            if memories.is_empty() {
                continue;
            }
            total_scanned += memories.len();
            for mem in &memories {
                if mem.is_telemetry_or_noise() && !mem.metadata.is_protected {
                    let serialized = serde_json::to_string(mem).map_err(|e| {
                        wm_core::CoreError::Memory(format!(
                            "failed to serialize {} for cold archive: {e}; nothing was deleted",
                            mem.metadata.id
                        ))
                    })?;
                    candidates.push(RotateCandidate {
                        galaxy: *galaxy,
                        id: mem.metadata.id,
                        json: serialized,
                    });
                }
            }
        }

        let sample_pruned_ids: Vec<String> = candidates
            .iter()
            .take(25)
            .map(|c| c.id.to_string())
            .collect();

        if dry_run {
            return Ok(json!({
                "status": "dry_run_completed",
                "dry_run": true,
                "total_records_scanned": total_scanned,
                "total_records_rotated": candidates.len(),
                "search_cleanup_skipped": self.search.is_none(),
                "assoc_cleanup_skipped": self.associations.is_none(),
                "sample_pruned_ids": sample_pruned_ids,
                "duration_ms": start.elapsed().as_millis() as u64
            }));
        }

        if candidates.is_empty() {
            return Ok(json!({
                "status": "rotation_completed",
                "dry_run": false,
                "total_records_scanned": total_scanned,
                "total_records_rotated": 0,
                "archived_confirmed": 0,
                "deleted_confirmed": 0,
                "deindex_failed": 0,
                "assoc_cleanup_failed": 0,
                "search_cleanup_skipped": self.search.is_none(),
                "assoc_cleanup_skipped": self.associations.is_none(),
                "archive_files": [],
                "manifest_path": Value::Null,
                "sample_pruned_ids": sample_pruned_ids,
                "duration_ms": start.elapsed().as_millis() as u64
            }));
        }

        if let Err(e) = std::fs::create_dir_all(&output_dir) {
            return Err(wm_core::CoreError::Memory(format!(
                "failed to create cold storage directory {}: {e}; nothing was deleted",
                output_dir.display()
            )));
        }

        // Unique stem per run (timestamp + nanos + pid). Every archive file
        // is created with `create_new`, so a repeated run can never truncate
        // an earlier archive — a collision is an error, not data loss.
        let now = chrono::Utc::now();
        let stem = match &project_name {
            Some(name) => format!(
                "cold_rotation_{name}_{}_{:09}_{}",
                now.format("%Y%m%d_%H%M%S"),
                now.timestamp_subsec_nanos(),
                std::process::id()
            ),
            None => format!(
                "cold_rotation_{}_{:09}_{}",
                now.format("%Y%m%d_%H%M%S"),
                now.timestamp_subsec_nanos(),
                std::process::id()
            ),
        };

        let mut archived_confirmed = 0usize;
        let mut deleted_confirmed = 0usize;
        let mut deindex_failed = 0usize;
        let mut assoc_failed = 0usize;
        let mut per_galaxy_deleted = HashMap::new();
        let mut archive_files: Vec<String> = Vec::new();
        let mut chunk_reports: Vec<Value> = Vec::new();

        for (chunk_idx, chunk) in candidates.chunks(ROTATE_CHUNK_SIZE).enumerate() {
            let part_name = format!("{stem}.part{chunk_idx:04}.jsonl");
            let part_path = output_dir.join(&part_name);
            let expected_ids: Vec<Uuid> = chunk.iter().map(|c| c.id).collect();

            // Phase 1 — archive this chunk. Exclusive creation plus
            // flush + sync before anything is deleted.
            {
                use std::io::Write;
                let file = std::fs::OpenOptions::new()
                    .create_new(true)
                    .write(true)
                    .open(&part_path)
                    .map_err(|e| {
                        wm_core::CoreError::Memory(format!(
                            "failed to create cold archive {}: {e}; nothing was deleted",
                            part_path.display()
                        ))
                    })?;
                let mut writer = std::io::BufWriter::new(file);
                for candidate in chunk {
                    writeln!(writer, "{}", candidate.json).map_err(|e| {
                        wm_core::CoreError::Memory(format!(
                            "failed to write cold archive {}: {e}; run aborted with {deleted_confirmed} records already rotated (their archives verified)",
                            part_path.display()
                        ))
                    })?;
                }
                writer.flush().map_err(|e| {
                    wm_core::CoreError::Memory(format!(
                        "failed to flush cold archive {}: {e}; run aborted with {deleted_confirmed} records already rotated (their archives verified)",
                        part_path.display()
                    ))
                })?;
                writer.get_ref().sync_all().map_err(|e| {
                    wm_core::CoreError::Memory(format!(
                        "failed to sync cold archive {}: {e}; run aborted with {deleted_confirmed} records already rotated (their archives verified)",
                        part_path.display()
                    ))
                })?;
            }

            // Phase 2 — verify the archive before touching sources.
            verify_chunk_archive(&part_path, &expected_ids)?;

            // Phase 3 — delete verified sources, then clean indexes.
            // An absent row counts as resolved (idempotent re-runs).
            for candidate in chunk {
                self.store
                    .delete(candidate.galaxy, candidate.id)
                    .map_err(|e| {
                        wm_core::CoreError::Memory(format!(
                            "failed to delete {} from {:?}: {e}; run aborted ({} deleted so far; archive {} is durable)",
                            candidate.id,
                            candidate.galaxy,
                            deleted_confirmed,
                            part_path.display()
                        ))
                    })?;
                deleted_confirmed += 1;
                *per_galaxy_deleted
                    .entry(candidate.galaxy.db_name().to_string())
                    .or_insert(0) += 1;
            }
            if let Some(search) = &self.search {
                let id_strings: Vec<String> = expected_ids.iter().map(Uuid::to_string).collect();
                if let Err(e) = (|| {
                    let mut writer = search.writer()?;
                    for id_str in &id_strings {
                        search.delete_document(&mut writer, id_str)?;
                    }
                    search.commit(&mut writer)?;
                    Ok::<(), wm_core::CoreError>(())
                })() {
                    tracing::warn!(
                        "cold rotation: Tantivy de-indexing failed for chunk {chunk_idx}: {e}"
                    );
                    deindex_failed += chunk.len();
                }
            }
            if let Some(assoc_store) = &self.associations {
                let env = self.store.env();
                for candidate in chunk {
                    let edges = assoc_store
                        .find_from(env, candidate.id)
                        .unwrap_or_default()
                        .into_iter()
                        .chain(assoc_store.find_to(env, candidate.id).unwrap_or_default());
                    for edge in edges {
                        if let Err(e) = assoc_store.delete(env, edge.source, edge.target) {
                            tracing::warn!(
                                "cold rotation: association cleanup failed for {}: {e}",
                                candidate.id
                            );
                            assoc_failed += 1;
                        }
                    }
                }
            }
            archived_confirmed += chunk.len();
            archive_files.push(part_path.to_string_lossy().to_string());
            chunk_reports.push(json!({"file": part_name, "records": chunk.len()}));
        }

        // Recovery manifest. Best-effort: a missing manifest never
        // endangers data, so it warns instead of failing the run.
        let manifest = json!({
            "tool": "galaxy.cold_rotate",
            "created_at": chrono::Utc::now().to_rfc3339(),
            "project": project_name,
            "total_scanned": total_scanned,
            "archived_confirmed": archived_confirmed,
            "deleted_confirmed": deleted_confirmed,
            "deindex_failed": deindex_failed,
            "assoc_cleanup_failed": assoc_failed,
            "chunks": chunk_reports,
        });
        let manifest_path = output_dir.join(format!("{stem}.manifest.json"));
        let manifest_written = (|| -> wm_core::Result<()> {
            let file = std::fs::OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(&manifest_path)
                .map_err(|e| wm_core::CoreError::Memory(format!("manifest create failed: {e}")))?;
            serde_json::to_writer_pretty(file, &manifest)
                .map_err(|e| wm_core::CoreError::Memory(format!("manifest write failed: {e}")))?;
            Ok(())
        })();
        let manifest_written_ok = manifest_written.is_ok();
        if let Err(e) = manifest_written {
            tracing::warn!("cold rotation: {e}; archives and deletions stand, manifest missing");
        }

        let duration_ms = start.elapsed().as_millis() as u64;

        Ok(json!({
            "status": "rotation_completed",
            "dry_run": false,
            "total_records_scanned": total_scanned,
            "total_records_rotated": deleted_confirmed,
            "archived_confirmed": archived_confirmed,
            "deleted_confirmed": deleted_confirmed,
            "deindex_failed": deindex_failed,
            "assoc_cleanup_failed": assoc_failed,
            "search_cleanup_skipped": self.search.is_none(),
            "assoc_cleanup_skipped": self.associations.is_none(),
            "archive_files": archive_files,
            "manifest_path": if manifest_written_ok { Some(manifest_path.to_string_lossy().to_string()) } else { None },
            "manifest_written": manifest_written_ok,
            "chunks": chunk_reports,
            "per_galaxy_rotated": per_galaxy_deleted,
            "sample_pruned_ids": sample_pruned_ids,
            "duration_ms": duration_ms
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Classifies whether a memory is operational telemetry/noise or high-signal knowledge.
#[inline]
fn classify_is_noise(mem: &Memory) -> bool {
    mem.is_telemetry_or_noise()
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn open_store() -> (tempfile::TempDir, MemoryStore) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, store)
    }

    fn hybrid_rotate_fixture() -> (
        tempfile::TempDir,
        MemoryStore,
        Arc<SearchEngine>,
        Arc<AssociationStore>,
    ) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let tantivy_dir = tmp.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_dir).unwrap();
        let search = Arc::new(SearchEngine::open(&tantivy_dir).unwrap());
        let assoc_store = Arc::new(AssociationStore::open(store.env()).expect("association store"));
        (tmp, store, search, assoc_store)
    }

    fn index_for_rotate(search: &Arc<SearchEngine>, mem: &Memory) {
        let mut writer = search.writer().unwrap();
        search
            .add_document(
                &mut writer,
                &mem.metadata.id.to_string(),
                mem.metadata.galaxy.db_name(),
                &mem.content,
                &mem.metadata.tags,
                mem.metadata.created_at.timestamp(),
            )
            .unwrap();
        search.commit(&mut writer).unwrap();
    }

    #[test]
    fn test_classify_is_noise_logic() {
        // Protected memory is never noise
        let mut mem1 = Memory::new(Galaxy::Codex, "some brief log".into());
        mem1.metadata.is_protected = true;
        assert!(!classify_is_noise(&mem1));

        // Decision or architecture tag is never noise
        let mut mem2 = Memory::new(Galaxy::Codex, "some info".into());
        mem2.metadata.tags = vec!["architecture".into(), "v9".into()];
        assert!(!classify_is_noise(&mem2));

        // Telemetry tag is noise
        let mut mem3 = Memory::new(Galaxy::Substrate, "some heartbeat log".into());
        mem3.metadata.tags = vec!["telemetry".into(), "probe".into()];
        assert!(classify_is_noise(&mem3));

        // Raw json turn_type is noise
        let mem4 = Memory::new(
            Galaxy::Sessions,
            "{\"turn_type\": \"user\", \"latency_ms\": 42}".into(),
        );
        assert!(classify_is_noise(&mem4));

        // Low importance short snippet is noise
        let mut mem5 = Memory::new(Galaxy::Universal, "ok".into());
        mem5.metadata.importance = 0.1;
        assert!(classify_is_noise(&mem5));
    }

    #[tokio::test]
    async fn test_army_deploy_file_search() {
        let (_tmp_store, store) = open_store();
        let tool = ArmyDeployTool::new(Arc::new(store));

        let tmp_dir = tempdir().unwrap();
        let file1 = tmp_dir.path().join("target_file.rs");
        std::fs::write(&file1, "fn shadow_consensus_vector() {}\nlet x = 42;\n").unwrap();

        let result = tool
            .call(
                &mut Context::default(),
                json!({
                    "army_type": "file_search",
                    "target_path": tmp_dir.path().to_str().unwrap(),
                    "query": "shadow_consensus"
                }),
            )
            .await
            .unwrap();

        assert_eq!(result["status"], "completed");
        assert_eq!(result["army_type"], "file_search");
        assert!(result["files_scanned"].as_u64().unwrap() >= 1);
        assert_eq!(result["matches_found"], 1);
    }

    #[tokio::test]
    async fn shadow_consensus_is_rejected_not_simulated() {
        let (_tmp_store, store) = open_store();
        let tool = ArmyDeployTool::new(Arc::new(store));
        let mut ctx = Context::default();

        // The fabricated-consensus path must be gone: requesting it is an
        // error, never a favorable evaluation.
        let err = tool
            .call(
                &mut ctx,
                json!({"army_type": "shadow_consensus", "clone_count": 10_000}),
            )
            .await
            .expect_err("shadow_consensus must be rejected");
        let msg = err.to_string();
        assert!(
            msg.contains("no execution engine"),
            "rejection must say plainly that nothing executes: {msg}"
        );

        // Every other reserved-but-unimplemented name is rejected too, with
        // redirects where a real tool exists.
        for (name, redirect) in [
            ("galactic_triage", Some("galaxy.triage_sweep")),
            ("geneseed_miner", Some("geneseed.mine")),
            ("batch_pipeline", None),
            ("thought_pulse", None),
        ] {
            let err = tool
                .call(&mut ctx, json!({"army_type": name}))
                .await
                .expect_err(&format!("{name} must be rejected"));
            let msg = err.to_string();
            match redirect {
                Some(tool) => assert!(
                    msg.contains(tool),
                    "{name} rejection must redirect to {tool}: {msg}"
                ),
                None => assert!(
                    msg.contains("no execution engine"),
                    "{name} rejection must admit nothing executes: {msg}"
                ),
            }
        }

        // Unknown names are rejected, never acknowledged as completed.
        let err = tool
            .call(&mut ctx, json!({"army_type": "death_star_legion"}))
            .await
            .expect_err("unknown army_type must be rejected");
        assert!(err.to_string().contains("unknown army_type"));
    }

    #[tokio::test]
    async fn test_galactic_triage_sweep() {
        let (_tmp_store, store) = open_store();

        // 1 Signal Memory
        let mut sig_mem = Memory::new(Galaxy::Codex, "Rubedo v9 architecture breakthrough".into());
        sig_mem.metadata.tags = vec!["architecture".into(), "decision".into()];
        sig_mem.metadata.importance = 0.95;
        store.put(Galaxy::Codex, &sig_mem).unwrap();

        // 1 Noise Memory
        let mut noise_mem = Memory::new(
            Galaxy::Codex,
            "{\"turn_type\": \"ping\", \"latency_ms\": 12}".into(),
        );
        noise_mem.metadata.tags = vec!["telemetry".into(), "turn_type".into()];
        noise_mem.metadata.importance = 0.1;
        store.put(Galaxy::Codex, &noise_mem).unwrap();

        let tool = GalacticTriageTool::new(Arc::new(store));
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();

        assert_eq!(result["status"], "completed");
        assert_eq!(result["total_records_analyzed"], 2);
        assert_eq!(result["total_signal_insights"], 1);
        assert_eq!(result["total_telemetry_noise"], 1);
        assert_eq!(result["overall_signal_percentage"], "50.0%");
        assert_eq!(result["recommended_for_cold_storage_count"], 1);
        let cold_ids = result["sample_cold_storage_ids"].as_array().unwrap();
        assert_eq!(cold_ids.len(), 1);
        assert_eq!(
            cold_ids[0].as_str().unwrap(),
            noise_mem.metadata.id.to_string()
        );
    }

    #[tokio::test]
    async fn test_galactic_cold_rotate_tool() {
        let (_tmp, store, search, assoc_store) = hybrid_rotate_fixture();
        let store = Arc::new(store);

        // 1 Signal Memory
        let sig_mem = Memory::new(Galaxy::Codex, "Core architectural insight".into());
        let sig_id = sig_mem.metadata.id;
        store.put(Galaxy::Codex, &sig_mem).unwrap();

        // 1 Noise Memory
        let mut noise_mem = Memory::new(
            Galaxy::Codex,
            "{\"turn_type\": \"ping\", \"friction\": \"low\"}".into(),
        );
        noise_mem.metadata.tags = vec!["telemetry".into(), "raw-archive".into()];
        let noise_id = noise_mem.metadata.id;
        store.put(Galaxy::Codex, &noise_mem).unwrap();
        index_for_rotate(&search, &noise_mem);

        let rotate_tool = GalacticColdRotateTool::new(store.clone())
            .with_search(search.clone())
            .with_associations(assoc_store);
        let cold_dir = tempfile::tempdir().unwrap();
        let cold_dir_str = cold_dir.path().to_str().unwrap();

        // 1. Dry run: doesn't delete anything, writes no files
        let dry_res = rotate_tool
            .call(
                &mut Context::default(),
                json!({
                    "dry_run": true,
                    "output_dir": cold_dir_str
                }),
            )
            .await
            .unwrap();

        assert_eq!(dry_res["status"], "dry_run_completed");
        assert_eq!(dry_res["total_records_rotated"], 1);
        assert!(store.get(Galaxy::Codex, noise_id).unwrap().is_some());
        assert_eq!(
            std::fs::read_dir(cold_dir.path()).unwrap().count(),
            0,
            "dry run must not write archives"
        );

        // 2. Real rotation: verified archive, pruned noise, clean index
        let real_res = rotate_tool
            .call(
                &mut Context::default(),
                json!({
                    "dry_run": false,
                    "output_dir": cold_dir_str
                }),
            )
            .await
            .unwrap();

        assert_eq!(real_res["status"], "rotation_completed");
        assert_eq!(real_res["archived_confirmed"], 1);
        assert_eq!(real_res["deleted_confirmed"], 1);
        assert_eq!(real_res["deindex_failed"], 0);
        let files = real_res["archive_files"].as_array().unwrap();
        assert_eq!(files.len(), 1);
        assert!(std::path::Path::new(files[0].as_str().unwrap()).exists());
        assert!(std::path::Path::new(real_res["manifest_path"].as_str().unwrap()).exists());

        // Signal memory retained, noise memory pruned from store AND index.
        assert!(store.get(Galaxy::Codex, sig_id).unwrap().is_some());
        assert!(store.get(Galaxy::Codex, noise_id).unwrap().is_none());
        assert!(
            search.search_ids("friction", 100).unwrap().is_empty(),
            "rotated records must not linger in search results"
        );
    }

    #[tokio::test]
    async fn cold_rotate_fails_closed_on_unwritable_dir() {
        let (_tmp, store, search, assoc_store) = hybrid_rotate_fixture();
        let store = Arc::new(store);

        let mut noise_mem = Memory::new(Galaxy::Codex, "{\"turn_type\": \"ping\"}".into());
        noise_mem.metadata.tags = vec!["telemetry".into()];
        let noise_id = noise_mem.metadata.id;
        store.put(Galaxy::Codex, &noise_mem).unwrap();

        // Point output_dir at an existing *file* so directory creation fails.
        let blocker = tempfile::NamedTempFile::new().unwrap();
        let blocker_str = blocker.path().to_str().unwrap().to_string();

        let tool = GalacticColdRotateTool::new(store.clone())
            .with_search(search)
            .with_associations(assoc_store);
        let err = tool
            .call(
                &mut Context::default(),
                json!({
                    "dry_run": false,
                    "output_dir": blocker_str,
                }),
            )
            .await
            .expect_err("unwritable archive dir must fail the run");
        assert!(err.to_string().contains("nothing was deleted"));
        assert!(
            store.get(Galaxy::Codex, noise_id).unwrap().is_some(),
            "failed run must not delete sources"
        );
    }

    #[tokio::test]
    async fn cold_rotate_runs_never_truncate_archives() {
        let (_tmp, store, _, _) = hybrid_rotate_fixture();
        let store = Arc::new(store);

        let add_noise = |content: String| {
            let mut mem = Memory::new(Galaxy::Codex, content);
            mem.metadata.tags = vec!["telemetry".into()];
            store.put(Galaxy::Codex, &mem).unwrap();
        };
        add_noise("{\"turn_type\": \"ping-1\"}".into());
        add_noise("{\"turn_type\": \"ping-2\"}".into());

        let tool = GalacticColdRotateTool::new(store.clone());
        let cold_dir = tempfile::tempdir().unwrap();
        let cold_args = |dir: &str| {
            json!({
                "dry_run": false,
                "output_dir": dir,
                "project_name": "same-second",
            })
        };

        // Run 1 rotates two records; run 2 (after new noise arrives)
        // rotates one more. With second-resolution names the old code
        // truncated run 1's archive; every run must keep its own file.
        tool.call(
            &mut Context::default(),
            cold_args(cold_dir.path().to_str().unwrap()),
        )
        .await
        .unwrap();
        add_noise("{\"turn_type\": \"ping-3\"}".into());
        tool.call(
            &mut Context::default(),
            cold_args(cold_dir.path().to_str().unwrap()),
        )
        .await
        .unwrap();

        let mut parts: Vec<_> = std::fs::read_dir(cold_dir.path())
            .unwrap()
            .filter_map(std::result::Result::ok)
            .map(|e| e.path())
            .filter(|p| p.extension().is_some_and(|x| x == "jsonl"))
            .collect();
        parts.sort();
        assert_eq!(parts.len(), 2, "each run must create its own archive file");
        let total_lines: usize = parts
            .iter()
            .map(|p| std::fs::read_to_string(p).unwrap().lines().count())
            .sum();
        assert_eq!(
            total_lines, 3,
            "no archived record may be lost to truncation"
        );
    }

    #[test]
    fn verify_chunk_archive_rejects_corruption() {
        let dir = tempfile::tempdir().unwrap();
        let good = dir.path().join("good.part0000.jsonl");
        let id = uuid::Uuid::new_v4();
        std::fs::write(
            &good,
            format!("{{\"metadata\":{{\"id\":\"{id}\"}},\"content\":\"x\"}}\n"),
        )
        .unwrap();
        assert!(verify_chunk_archive(&good, &[id]).is_ok());

        let bad_json = dir.path().join("bad.part0000.jsonl");
        std::fs::write(&bad_json, "{\"metadata\": {oops}\n").unwrap();
        assert!(verify_chunk_archive(&bad_json, &[id]).is_err());

        let wrong_ids = dir.path().join("wrong.part0000.jsonl");
        std::fs::write(
            &wrong_ids,
            format!(
                "{{\"metadata\":{{\"id\":\"{}\"}},\"content\":\"x\"}}\n",
                uuid::Uuid::new_v4()
            ),
        )
        .unwrap();
        assert!(verify_chunk_archive(&wrong_ids, &[id]).is_err());
    }

    #[tokio::test]
    async fn cold_rotate_cleans_associations() {
        let (_tmp, store, _, assoc_store) = hybrid_rotate_fixture();
        let store = Arc::new(store);

        let mut mem_a = Memory::new(Galaxy::Codex, "{\"turn_type\": \"ping-a\"}".into());
        mem_a.metadata.tags = vec!["telemetry".into()];
        let mut mem_b = Memory::new(Galaxy::Codex, "{\"turn_type\": \"ping-b\"}".into());
        mem_b.metadata.tags = vec!["telemetry".into()];
        let id_a = mem_a.metadata.id;
        let id_b = mem_b.metadata.id;
        store.put(Galaxy::Codex, &mem_a).unwrap();
        store.put(Galaxy::Codex, &mem_b).unwrap();

        let env = store.env();
        assoc_store
            .put(
                env,
                &wm_memory::Association {
                    source: id_a,
                    target: id_b,
                    association_type: "related".into(),
                    weight: 0.5,
                    created_at: chrono::Utc::now(),
                    link_type: wm_memory::LinkType::Related,
                    co_activation_count: 1,
                    last_activated_at: chrono::Utc::now(),
                    decay_half_life_days: 90.0,
                },
            )
            .unwrap();
        assert_eq!(assoc_store.find_from(env, id_a).unwrap().len(), 1);

        let tool =
            GalacticColdRotateTool::new(store.clone()).with_associations(assoc_store.clone());
        let cold_dir = tempfile::tempdir().unwrap();
        let res = tool
            .call(
                &mut Context::default(),
                json!({
                    "dry_run": false,
                    "output_dir": cold_dir.path().to_str().unwrap(),
                }),
            )
            .await
            .unwrap();
        assert_eq!(res["assoc_cleanup_failed"], 0);
        assert!(
            assoc_store.find_from(env, id_a).unwrap().is_empty()
                && assoc_store.find_to(env, id_b).unwrap().is_empty(),
            "edges touching rotated records must be removed"
        );
    }
}
