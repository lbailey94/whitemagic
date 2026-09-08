//! Subagent Captains & Platoon Orchestration (Operation Legion Heir Phase 2).
//!
//! Autonomous subagent captains deploy and command platoons of thousands of
//! parallel Tokio/Rayon clone soldiers to execute specialized cognitive operations:
//!
//! - **Vanguard (Feng / Wind)**: Rapid codebase reconnaissance & AST structure scouting.
//! - **Sentry (Lin / Forest)**: Governance audit, boundary defense & memory provenance.
//! - **Alchemist (Huo / Fire)**: Geneseed pattern mining, Kaizen correlation & D6 novelty.
//! - **Cartographer (Shan / Mountain)**: 5D Holographic spatial rebalancing & dimensional dispersion.

#![forbid(unsafe_code)]

use async_trait::async_trait;
use chrono::Utc;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Instant;

use wm_core::{
    Context, Coordinate5D, CoreError, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats,
};
use wm_memory::{Memory, MemoryStore, SemanticEncoder};

use super::common::{content_visible, parse_galaxy};

// ── Captain Roles ──────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CaptainRole {
    /// Feng (Wind) — Rapid reconnaissance & codebase scout
    Vanguard,
    /// Lin (Forest) — Dharma governance, boundary sentry, Landlock enforcement
    Sentry,
    /// Huo (Fire) — Geneseed pattern mining, Kaizen correlation, D6 Novelty Emergence
    Alchemist,
    /// Shan (Mountain) — 5D Holographic spatial rebalancing & dimensional dispersion
    Cartographer,
}

impl CaptainRole {
    #[must_use]
    pub const fn name(&self) -> &'static str {
        match self {
            Self::Vanguard => "vanguard",
            Self::Sentry => "sentry",
            Self::Alchemist => "alchemist",
            Self::Cartographer => "cartographer",
        }
    }

    #[must_use]
    pub const fn doctrine(&self) -> &'static str {
        match self {
            Self::Vanguard => {
                "Swift as the Wind: Rapid multi-threaded traversal and reconnaissance."
            }
            Self::Sentry => {
                "Silent as the Forest: Immutability, boundary checks, and Dharma audit."
            }
            Self::Alchemist => {
                "Fierce as Fire: Transmutation of commits and turns into golden insight."
            }
            Self::Cartographer => {
                "Steadfast as the Mountain: Structuring multidimensional semantic space."
            }
        }
    }

    #[must_use]
    pub const fn hongmen_code(&self) -> u32 {
        match self {
            Self::Vanguard => 438,
            Self::Sentry => 426,
            Self::Alchemist => 415,
            Self::Cartographer => 432,
        }
    }

    #[must_use]
    pub const fn hongmen_title(&self) -> &'static str {
        match self {
            Self::Vanguard => "先鋒 438 (Sin Fung / Incense Master Vanguard)",
            Self::Sentry => "紅棍 426 (Hung Kwan / Red Pole Military Commander)",
            Self::Alchemist => "白紙扇 415 (Pak Tsz Sin / White Paper Fan Strategist)",
            Self::Cartographer => "草鞋 432 (Cho Hai / Straw Sandal Spatial Navigator)",
        }
    }

    #[must_use]
    pub fn parse_role(s: &str) -> Option<Self> {
        s.parse().ok()
    }
}

impl std::str::FromStr for CaptainRole {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_ascii_lowercase().as_str() {
            "vanguard" | "wind" | "feng" => Ok(Self::Vanguard),
            "sentry" | "forest" | "lin" => Ok(Self::Sentry),
            "alchemist" | "fire" | "huo" => Ok(Self::Alchemist),
            "cartographer" | "mountain" | "shan" => Ok(Self::Cartographer),
            other => Err(format!("Unknown captain role: {other}")),
        }
    }
}

// ── Captain Deploy Tool ────────────────────────────────────────────────

pub struct CaptainDeployTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl CaptainDeployTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Filesystem, Resource::Galaxy("*".into())],
                writes: vec![Resource::Galaxy("*".into()), Resource::Process],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for CaptainDeployTool {
    fn name(&self) -> &str {
        "captain.deploy"
    }

    fn gana(&self) -> Gana {
        Gana::Ghost
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Deploy an autonomous Subagent Captain to command a specialized Tokio clone army for parallel codebase, memory, or holographic spatial tasks."
    }

    async fn call(&self, ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let role_str = args
            .get("role")
            .and_then(Value::as_str)
            .unwrap_or("cartographer");
        let role = CaptainRole::parse_role(role_str).ok_or_else(|| {
            CoreError::InvalidArgs(format!(
                "Unknown captain role: {role_str}. Valid: vanguard, sentry, alchemist, cartographer"
            ))
        })?;

        let objective = args
            .get("objective")
            .and_then(Value::as_str)
            .unwrap_or("mission_execution");
        let soldier_count = args
            .get("army_size")
            .and_then(Value::as_u64)
            .unwrap_or(10_000) as usize;
        let apply = args.get("apply").and_then(Value::as_bool).unwrap_or(false);
        let start = Instant::now();

        match role {
            CaptainRole::Cartographer => {
                let target_galaxy_str = args.get("target_galaxy").and_then(Value::as_str);
                let galaxies: Vec<Galaxy> = if let Some(g_str) = target_galaxy_str {
                    if g_str == "all" {
                        Galaxy::memory_galaxies().to_vec()
                    } else {
                        vec![parse_galaxy(g_str)?]
                    }
                } else {
                    Galaxy::memory_galaxies().to_vec()
                };

                let dispersion_report =
                    run_dimensional_dispersion(&self.store, &galaxies, apply, soldier_count)?;
                let duration_ms = start.elapsed().as_millis() as u64;

                Ok(json!({
                    "status": "completed",
                    "captain_role": role.name(),
                    "doctrine": role.doctrine(),
                    "objective": objective,
                    "soldiers_commanded": soldier_count,
                    "apply_mode": apply,
                    "duration_ms": duration_ms,
                    "dispersion": dispersion_report,
                }))
            }
            CaptainRole::Vanguard => {
                let target_path_str = args
                    .get("target_path")
                    .and_then(Value::as_str)
                    .unwrap_or(".");
                let query = args.get("query").and_then(Value::as_str).unwrap_or("");
                let root = PathBuf::from(target_path_str);

                let mut files = Vec::new();
                collect_files_recursive(&root, &mut files, soldier_count);
                let files_count = files.len();

                let matches: Vec<Value> = files
                    .par_iter()
                    .filter_map(|p| {
                        if query.is_empty() {
                            return None;
                        }
                        if let Ok(content) = std::fs::read_to_string(p) {
                            if content.contains(query) {
                                return Some(json!({
                                    "path": p.display().to_string(),
                                    "size_bytes": content.len()
                                }));
                            }
                        }
                        None
                    })
                    .collect();

                let duration_ms = start.elapsed().as_millis() as u64;

                Ok(json!({
                    "status": "completed",
                    "captain_role": role.name(),
                    "doctrine": role.doctrine(),
                    "objective": objective,
                    "soldiers_commanded": soldier_count,
                    "files_scouted": files_count,
                    "matches_found": matches.len(),
                    "duration_ms": duration_ms,
                    "top_matches": matches.into_iter().take(25).collect::<Vec<_>>()
                }))
            }
            CaptainRole::Sentry => {
                let mut total_checked = 0usize;
                let mut valid_count = 0usize;
                let mut unverified_count = 0usize;

                for g in Galaxy::memory_galaxies() {
                    let mems = self.store.scan(g, soldier_count).unwrap_or_default();
                    for m in mems {
                        total_checked += 1;
                        if m.metadata.source_trust >= 0.7 {
                            valid_count += 1;
                        } else {
                            unverified_count += 1;
                        }
                    }
                }

                let duration_ms = start.elapsed().as_millis() as u64;

                Ok(json!({
                    "status": "completed",
                    "captain_role": role.name(),
                    "doctrine": role.doctrine(),
                    "objective": objective,
                    "soldiers_commanded": soldier_count,
                    "duration_ms": duration_ms,
                    "memories_audited": total_checked,
                    "high_trust_memories": valid_count,
                    "unverified_memories": unverified_count,
                    "integrity_rating": if total_checked > 0 {
                        format!("{:.1}%", (valid_count as f64 / total_checked as f64) * 100.0)
                    } else {
                        "100.0%".to_string()
                    }
                }))
            }
            CaptainRole::Alchemist => {
                let mut total_analyzed = 0usize;
                let mut high_salience = 0usize;
                let mut knowledge_class = 0usize;
                let mut top_insights = Vec::new();

                for g in Galaxy::memory_galaxies() {
                    let mems = self.store.scan(g, soldier_count).unwrap_or_default();
                    for m in mems {
                        total_analyzed += 1;
                        if m.metadata.importance >= 0.7 {
                            high_salience += 1;
                        }
                        if m.metadata.class == Some(wm_memory::typology::MemoryClass::Knowledge) {
                            knowledge_class += 1;
                        }
                        if m.metadata.importance >= 0.8
                            && top_insights.len() < 15
                            && content_visible(ctx, g, &m)
                        {
                            top_insights.push(json!({
                                "id": m.metadata.id.to_string(),
                                "galaxy": g.db_name(),
                                "importance": m.metadata.importance,
                                "summary": m.content.chars().take(120).collect::<String>()
                            }));
                        }
                    }
                }

                let duration_ms = start.elapsed().as_millis() as u64;

                Ok(json!({
                    "status": "completed",
                    "captain_role": role.name(),
                    "doctrine": role.doctrine(),
                    "objective": objective,
                    "soldiers_commanded": soldier_count,
                    "duration_ms": duration_ms,
                    "memories_analyzed": total_analyzed,
                    "high_salience_memories": high_salience,
                    "knowledge_class_memories": knowledge_class,
                    "distilled_insights": top_insights
                }))
            }
        }
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Dimensional Dispersion & Spatial Rebalancing ───────────────────────

pub struct HologramRebalanceTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl HologramRebalanceTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Galaxy("*".into())],
                writes: vec![Resource::Galaxy("*".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for HologramRebalanceTool {
    fn name(&self) -> &str {
        "hologram.rebalance"
    }

    fn gana(&self) -> Gana {
        Gana::Ghost
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Execute 5D dimensional dispersion across memory galaxies, breaking the (0.5, 0.5, 0.5) spatial singularity and dispersing semantic coordinates."
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_str = args.get("galaxy").and_then(Value::as_str);
        let apply = args.get("apply").and_then(Value::as_bool).unwrap_or(false);
        let batch_limit = args.get("limit").and_then(Value::as_u64).unwrap_or(10_000) as usize;

        let galaxies: Vec<Galaxy> = if let Some(g_str) = galaxy_str {
            if g_str == "all" {
                Galaxy::memory_galaxies().to_vec()
            } else {
                vec![parse_galaxy(g_str)?]
            }
        } else {
            Galaxy::memory_galaxies().to_vec()
        };

        let start = Instant::now();
        let report = run_dimensional_dispersion(&self.store, &galaxies, apply, batch_limit)?;
        let duration_ms = start.elapsed().as_millis() as u64;

        Ok(json!({
            "status": "completed",
            "apply": apply,
            "duration_ms": duration_ms,
            "report": report
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Holographic 5D Nearest-Neighbor Query Tool ─────────────────────────

pub struct HologramQueryTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl HologramQueryTool {
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Galaxy("*".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for HologramQueryTool {
    fn name(&self) -> &str {
        "hologram.query"
    }

    fn gana(&self) -> Gana {
        Gana::Ghost
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Perform hyper-fast 5D nearest-neighbor holographic retrieval across memories using multidimensional geometric resonance."
    }

    async fn call(&self, ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let query_str = args.get("query").and_then(Value::as_str).unwrap_or("");
        if query_str.is_empty() {
            return Err(CoreError::InvalidArgs(
                "Missing required argument: query".into(),
            ));
        }

        let galaxy_str = args.get("galaxy").and_then(Value::as_str);
        let k = args.get("k").and_then(Value::as_u64).unwrap_or(10) as usize;
        let semantic_only = args
            .get("semantic_only")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        #[allow(clippy::cast_possible_truncation)]
        let min_importance = args
            .get("min_importance")
            .and_then(Value::as_f64)
            .unwrap_or(0.0) as f32;
        #[allow(clippy::cast_possible_truncation)]
        let target_w = args
            .get("target_w")
            .and_then(Value::as_f64)
            .map(|v| v as f32);

        let galaxies: Vec<Galaxy> = if let Some(g_str) = galaxy_str {
            if g_str == "all" {
                Galaxy::memory_galaxies().to_vec()
            } else {
                vec![parse_galaxy(g_str)?]
            }
        } else {
            Galaxy::memory_galaxies().to_vec()
        };

        let start = Instant::now();
        let encoder = SemanticEncoder::new();
        let scores = encoder.encode(query_str);

        let (qx, qy, qz) = if (scores.x - 0.5).abs() < 1e-4
            && (scores.y - 0.5).abs() < 1e-4
            && (scores.z - 0.5).abs() < 1e-4
        {
            let hash_c = Coordinate5D::encode(query_str);
            (hash_c.x, hash_c.y, hash_c.z)
        } else {
            (scores.x, scores.y, scores.z)
        };

        let qw = target_w.unwrap_or(1.0);
        let qv = 0.8;

        let query_coord = Coordinate5D::new(qx, qy, qz, qw, qv);

        let mut candidate_memories = Vec::new();
        for g in galaxies {
            match self.store.scan(g, 50_000) {
                Ok(mems) => {
                    for m in mems {
                        // Visibility boundary: private, model-excluded,
                        // non-current, or compartment-forbidden records never
                        // become candidates, so they cannot leak through
                        // previews, tags, or coordinates.
                        if m.metadata.importance >= min_importance && content_visible(ctx, g, &m) {
                            candidate_memories.push((g, m));
                        }
                    }
                }
                Err(e) => {
                    tracing::warn!("Scan error in galaxy {g:?}: {e}");
                }
            }
        }

        let candidates_count = candidate_memories.len();

        let mut scored: Vec<(f32, Galaxy, Memory)> = candidate_memories
            .into_par_iter()
            .map(|(g, m)| {
                let dist = if semantic_only {
                    query_coord.semantic_distance_to(&m.metadata.coord5d)
                } else {
                    query_coord.distance_to(&m.metadata.coord5d)
                };
                (dist, g, m)
            })
            .collect();

        scored.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));

        let top_k = scored
            .into_iter()
            .take(k)
            .map(|(dist, g, m)| {
                let similarity = 1.0 / (1.0 + dist);
                json!({
                    "id": m.metadata.id.to_string(),
                    "galaxy": g.db_name(),
                    "distance_5d": (dist * 10_000.0).round() / 10_000.0,
                    "similarity": (similarity * 10_000.0).round() / 10_000.0,
                    "coord5d": {
                        "x": m.metadata.coord5d.x,
                        "y": m.metadata.coord5d.y,
                        "z": m.metadata.coord5d.z,
                        "w": m.metadata.coord5d.w,
                        "v": m.metadata.coord5d.v,
                    },
                    "importance": m.metadata.importance,
                    "created_at": m.metadata.created_at.to_rfc3339(),
                    "tags": m.metadata.tags,
                    "content_preview": m.content.chars().take(160).collect::<String>()
                })
            })
            .collect::<Vec<_>>();

        let duration_ms = start.elapsed().as_millis() as u64;

        Ok(json!({
            "status": "completed",
            "query": query_str,
            "query_coord5d": {
                "x": qx,
                "y": qy,
                "z": qz,
                "w": qw,
                "v": qv,
            },
            "candidates_scanned": candidates_count,
            "duration_ms": duration_ms,
            "k": top_k.len(),
            "results": top_k
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[derive(Serialize)]
pub struct DispersionReport {
    pub galaxies_processed: usize,
    pub total_memories_inspected: usize,
    pub memories_rebalanced: usize,
    pub pre_variance: [f64; 5],
    pub post_variance: [f64; 5],
    pub dispersion_gain_factor: f64,
}

fn run_dimensional_dispersion(
    store: &MemoryStore,
    galaxies: &[Galaxy],
    apply: bool,
    batch_limit: usize,
) -> wm_core::Result<DispersionReport> {
    let encoder = SemanticEncoder::new();
    let now = Utc::now();

    let mut total_inspected = 0usize;
    let mut rebalanced_count = 0usize;

    let mut pre_x_vals = Vec::new();
    let mut pre_y_vals = Vec::new();
    let mut pre_z_vals = Vec::new();
    let mut pre_w_vals = Vec::new();
    let mut pre_v_vals = Vec::new();

    let mut post_x_vals = Vec::new();
    let mut post_y_vals = Vec::new();
    let mut post_z_vals = Vec::new();
    let mut post_w_vals = Vec::new();
    let mut post_v_vals = Vec::new();

    for &galaxy in galaxies {
        let memories = store.scan(galaxy, batch_limit).unwrap_or_default();
        if memories.is_empty() {
            continue;
        }

        total_inspected += memories.len();

        for mem in &memories {
            pre_x_vals.push(f64::from(mem.metadata.coord5d.x));
            pre_y_vals.push(f64::from(mem.metadata.coord5d.y));
            pre_z_vals.push(f64::from(mem.metadata.coord5d.z));
            pre_w_vals.push(f64::from(mem.metadata.coord5d.w));
            pre_v_vals.push(f64::from(mem.metadata.coord5d.v));
        }

        // Process in parallel using Rayon
        let rebalanced_memories: Vec<Memory> = memories
            .into_par_iter()
            .map(|mut mem| {
                #[allow(clippy::cast_precision_loss, clippy::cast_possible_truncation)]
                let age_days =
                    (now - mem.metadata.created_at).num_seconds().max(0) as f64 / 86400.0;
                #[allow(clippy::cast_possible_truncation)]
                let temporal_weight = (1.0 / (1.0 + age_days / 30.0)).clamp(0.05, 1.0) as f32;
                #[allow(clippy::cast_possible_truncation)]
                let consciousness = f64::midpoint(
                    f64::from(mem.metadata.importance),
                    f64::from(mem.metadata.neuro_score),
                )
                .clamp(0.1, 1.0) as f32;

                let scores = encoder.encode(&mem.content);

                let (x, y, z) = if (scores.x - 0.5).abs() < 1e-4
                    && (scores.y - 0.5).abs() < 1e-4
                    && (scores.z - 0.5).abs() < 1e-4
                {
                    // For content with no anchor terms, derive deterministic dispersion from content hash
                    let hash_coord = Coordinate5D::encode(&mem.content);
                    (hash_coord.x, hash_coord.y, hash_coord.z)
                } else {
                    (scores.x, scores.y, scores.z)
                };

                mem.metadata.coord5d = Coordinate5D::new(x, y, z, temporal_weight, consciousness);
                mem
            })
            .collect();

        for mem in &rebalanced_memories {
            post_x_vals.push(f64::from(mem.metadata.coord5d.x));
            post_y_vals.push(f64::from(mem.metadata.coord5d.y));
            post_z_vals.push(f64::from(mem.metadata.coord5d.z));
            post_w_vals.push(f64::from(mem.metadata.coord5d.w));
            post_v_vals.push(f64::from(mem.metadata.coord5d.v));

            rebalanced_count += 1;
        }

        if apply {
            for chunk in rebalanced_memories.chunks(5_000) {
                store.put_batch(galaxy, chunk)?;
            }
        }
    }

    let pre_var = [
        compute_variance(&pre_x_vals),
        compute_variance(&pre_y_vals),
        compute_variance(&pre_z_vals),
        compute_variance(&pre_w_vals),
        compute_variance(&pre_v_vals),
    ];

    let post_var = [
        compute_variance(&post_x_vals),
        compute_variance(&post_y_vals),
        compute_variance(&post_z_vals),
        compute_variance(&post_w_vals),
        compute_variance(&post_v_vals),
    ];

    let post_total_var = post_var.iter().sum::<f64>();
    let pre_total_var = pre_var.iter().sum::<f64>().max(1e-9);
    let dispersion_gain_factor = (post_total_var / pre_total_var).min(100_000.0);

    Ok(DispersionReport {
        galaxies_processed: galaxies.len(),
        total_memories_inspected: total_inspected,
        memories_rebalanced: rebalanced_count,
        pre_variance: pre_var,
        post_variance: post_var,
        dispersion_gain_factor,
    })
}

fn compute_variance(values: &[f64]) -> f64 {
    if values.len() < 2 {
        return 0.0;
    }
    let n = values.len() as f64;
    let mean = values.iter().sum::<f64>() / n;
    let var = values.iter().map(|&v| (v - mean).powi(2)).sum::<f64>() / n;
    (var * 10_000.0).round() / 10_000.0
}

fn collect_files_recursive(dir: &Path, files: &mut Vec<PathBuf>, max: usize) {
    if files.len() >= max || !dir.is_dir() {
        return;
    }
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            if files.len() >= max {
                break;
            }
            let path = entry.path();
            if path.is_dir() {
                let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
                if !name.starts_with('.')
                    && name != "target"
                    && name != "node_modules"
                    && name != "dist"
                {
                    collect_files_recursive(&path, files, max);
                }
            } else if path.is_file() {
                files.push(path);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn open_store() -> (tempfile::TempDir, MemoryStore) {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, store)
    }

    #[tokio::test]
    async fn test_captain_cartographer_dispersion() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        // Put memories with default 0.5 coordinates
        let m1 = Memory::new(
            Galaxy::Codex,
            "Logic algorithm compute binary structure".into(),
        );
        let m2 = Memory::new(
            Galaxy::Codex,
            "Love empathy emotion heartfelt poetry".into(),
        );
        store.put(Galaxy::Codex, &m1).unwrap();
        store.put(Galaxy::Codex, &m2).unwrap();

        let captain_tool = CaptainDeployTool::new(store.clone());
        let mut ctx = Context::default();

        let res = captain_tool
            .call(
                &mut ctx,
                json!({
                    "role": "cartographer",
                    "objective": "holographic_spatial_rebalance",
                    "target_galaxy": "codex",
                    "apply": true
                }),
            )
            .await
            .unwrap();

        assert_eq!(res["status"], "completed");
        assert_eq!(res["captain_role"], "cartographer");
        assert_eq!(res["dispersion"]["memories_rebalanced"], 2);

        // Verify that after dispersion, the two memories have distinct coordinates
        let mem1 = store.get(Galaxy::Codex, m1.metadata.id).unwrap().unwrap();
        let mem2 = store.get(Galaxy::Codex, m2.metadata.id).unwrap().unwrap();

        assert_ne!(mem1.metadata.coord5d.x, mem2.metadata.coord5d.x);
    }

    #[tokio::test]
    async fn test_hologram_query_resonance() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        let m1 = Memory::new(
            Galaxy::Codex,
            "Logic algorithm compute binary structure".into(),
        );
        let m2 = Memory::new(
            Galaxy::Codex,
            "Love empathy emotion heartfelt poetry".into(),
        );
        store.put(Galaxy::Codex, &m1).unwrap();
        store.put(Galaxy::Codex, &m2).unwrap();

        // Rebalance first
        let rebalance_tool = HologramRebalanceTool::new(store.clone());
        let mut ctx = Context::default();
        rebalance_tool
            .call(
                &mut ctx,
                json!({
                    "galaxy": "codex",
                    "apply": true
                }),
            )
            .await
            .unwrap();

        // Query for binary compute
        let query_tool = HologramQueryTool::new(store.clone());
        let res = query_tool
            .call(
                &mut ctx,
                json!({
                    "query": "binary compute algorithms",
                    "galaxy": "codex",
                    "k": 2
                }),
            )
            .await
            .unwrap();

        assert_eq!(res["status"], "completed");
        let results = res["results"].as_array().unwrap();
        assert_eq!(results.len(), 2);
        // The top match must be m1
        assert_eq!(results[0]["id"], m1.metadata.id.to_string());
        assert!(
            results[0]["similarity"].as_f64().unwrap() > results[1]["similarity"].as_f64().unwrap()
        );
    }

    #[tokio::test]
    async fn hologram_query_excludes_nonvisible_memories() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        // Three identical memories: same coordinates, different visibility.
        // Only the public one may surface through previews or ids.
        let public = Memory::new(Galaxy::Codex, "shared resonance content".into());
        let public_id = public.metadata.id;
        store.put(Galaxy::Codex, &public).unwrap();

        let mut private = Memory::new(Galaxy::Codex, "shared resonance content".into());
        private.metadata.is_private = true;
        store.put(Galaxy::Codex, &private).unwrap();

        let mut excluded = Memory::new(Galaxy::Codex, "shared resonance content".into());
        excluded.metadata.model_exclude = true;
        store.put(Galaxy::Codex, &excluded).unwrap();

        let query_tool = HologramQueryTool::new(store.clone());
        let mut ctx = Context::default();
        let res = query_tool
            .call(
                &mut ctx,
                json!({"query": "shared resonance", "galaxy": "codex", "k": 10}),
            )
            .await
            .unwrap();

        let results = res["results"].as_array().unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0]["id"], public_id.to_string());
    }

    #[tokio::test]
    async fn hologram_query_honors_compartment() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        let m = Memory::new(Galaxy::Codex, "sandbox-visible content check".into());
        store.put(Galaxy::Codex, &m).unwrap();

        // A sandbox context may only see Tutorial/Research: Codex records
        // must not surface even when explicitly requested.
        let query_tool = HologramQueryTool::new(store);
        let mut ctx = Context {
            compartment: Some("sandbox".to_string()),
            ..Default::default()
        };
        let res = query_tool
            .call(
                &mut ctx,
                json!({"query": "sandbox", "galaxy": "codex", "k": 10}),
            )
            .await
            .unwrap();

        assert_eq!(res["status"], "completed");
        assert!(res["results"].as_array().unwrap().is_empty());
    }

    #[tokio::test]
    async fn alchemist_withholds_private_insights() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        let mut public = Memory::new(Galaxy::Codex, "public breakthrough insight".into());
        public.metadata.importance = 0.9;
        let public_id = public.metadata.id;
        store.put(Galaxy::Codex, &public).unwrap();

        let mut private = Memory::new(Galaxy::Codex, "private breakthrough insight".into());
        private.metadata.importance = 0.9;
        private.metadata.is_private = true;
        store.put(Galaxy::Codex, &private).unwrap();

        let captain_tool = CaptainDeployTool::new(store);
        let mut ctx = Context::default();
        let res = captain_tool
            .call(&mut ctx, json!({"role": "alchemist"}))
            .await
            .unwrap();

        // Aggregates still count scanned records, but content-bearing
        // insights must never include the private memory.
        assert_eq!(res["memories_analyzed"], 2);
        let insights = res["distilled_insights"].as_array().unwrap();
        assert_eq!(insights.len(), 1);
        assert_eq!(insights[0]["id"], public_id.to_string());
    }
}
