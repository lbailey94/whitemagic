//! Galaxy tools — stats, export, import, transfer, merge, snapshot, restore.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore, SearchEngine};

use super::common::{galaxy_name, parse_galaxy, parse_galaxy_or};

pub struct GalaxyStatsTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxyStatsTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxyStatsTool {
    fn name(&self) -> &str {
        "galaxy.stats"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Statistics for all galaxies (count per galaxy)"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut galaxy_counts = serde_json::Map::new();
        let mut total = 0usize;
        for galaxy in Galaxy::all() {
            let count = self.store.count(galaxy).unwrap_or(0);
            if count > 0 {
                galaxy_counts.insert(galaxy_name(galaxy).to_string(), json!(count));
                total += count;
            }
        }
        Ok(json!({
            "status": "success",
            "total_memories": total,
            "galaxies_with_data": galaxy_counts.len(),
            "galaxy_counts": galaxy_counts,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `galaxy.export` — export all memories from a galaxy as JSON.
pub struct GalaxyExportTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxyExportTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxyExportTool {
    fn name(&self) -> &str {
        "galaxy.export"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Export all memories from a galaxy as JSON"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(1000) as usize;
        let memories = self.store.scan(galaxy, limit)?;
        let exported: Vec<Value> = memories
            .iter()
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "content": m.content,
                    "tags": m.metadata.tags,
                    "importance": m.metadata.importance,
                    "created_at": m.metadata.created_at.to_rfc3339(),
                })
            })
            .collect();
        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "count": exported.len(),
            "memories": exported,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `galaxy.import` — import memories into a galaxy from JSON.
pub struct GalaxyImportTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxyImportTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxyImportTool {
    fn name(&self) -> &str {
        "galaxy.import"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Import memories into a galaxy from JSON array"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let memories = args
            .get("memories")
            .and_then(|v| v.as_array())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("Missing 'memories' array".into()))?;
        let mut imported = 0u32;
        for mem_val in memories {
            let content = mem_val
                .get("content")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let mut mem = Memory::new(galaxy, content.to_string());
            if let Some(tags) = mem_val.get("tags").and_then(|v| v.as_array()) {
                mem.metadata.tags = tags
                    .iter()
                    .filter_map(|t| t.as_str().map(String::from))
                    .collect();
            }
            if let Some(imp) = mem_val
                .get("importance")
                .and_then(serde_json::Value::as_f64)
            {
                mem.metadata.importance = imp as f32;
            }
            self.store.put(galaxy, &mem)?;
            imported += 1;
        }
        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "imported": imported,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `galaxy.transfer` — move memories from one galaxy to another.
///
/// Reads memories from the source galaxy, writes them to the destination
/// galaxy, then deletes them from the source. Optionally filters by tags.
pub struct GalaxyTransferTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxyTransferTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![
                    Resource::Galaxy("codex".into()),
                    Resource::Galaxy("research".into()),
                ],
                reads: vec![Resource::Galaxy("codex".into())],
                destructive: true,
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxyTransferTool {
    fn name(&self) -> &str {
        "galaxy.transfer"
    }
    fn gana(&self) -> Gana {
        Gana::Neck
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Transfer memories from one galaxy to another (move, not copy)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let from_galaxy = parse_galaxy(
            args.get("from_galaxy")
                .and_then(|v| v.as_str())
                .ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("Missing 'from_galaxy' parameter".into())
                })?,
        )?;
        let to_galaxy = parse_galaxy(args.get("to_galaxy").and_then(|v| v.as_str()).ok_or_else(
            || wm_core::CoreError::InvalidArgs("Missing 'to_galaxy' parameter".into()),
        )?)?;
        if from_galaxy == to_galaxy {
            return Err(wm_core::CoreError::InvalidArgs(
                "from_galaxy and to_galaxy must be different".into(),
            ));
        }
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10_000) as usize;
        let tag_filter: Option<Vec<String>> =
            args.get("tags").and_then(|v| v.as_array()).map(|arr| {
                arr.iter()
                    .filter_map(|t| t.as_str().map(String::from))
                    .collect()
            });

        let memories = self.store.scan(from_galaxy, limit)?;
        let mut transferred = 0u32;
        let mut skipped = 0u32;

        for mem in &memories {
            if let Some(ref tags) = tag_filter {
                if !tags.iter().all(|t| mem.metadata.tags.contains(t)) {
                    skipped += 1;
                    continue;
                }
            }

            let mut new_mem = Memory::new(to_galaxy, mem.content.clone());
            new_mem.metadata.tags.clone_from(&mem.metadata.tags);
            new_mem.metadata.importance = mem.metadata.importance;
            self.store.put(to_galaxy, &new_mem)?;

            self.store.delete(from_galaxy, mem.metadata.id)?;
            super::common::deindex(self.search.as_deref(), &mem.metadata.id.to_string());
            transferred += 1;
        }

        Ok(json!({
            "status": "success",
            "from_galaxy": galaxy_name(from_galaxy),
            "to_galaxy": galaxy_name(to_galaxy),
            "scanned": memories.len(),
            "transferred": transferred,
            "skipped": skipped,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `galaxy.merge` — merge memories from a source galaxy into a destination.
///
/// Copies all memories from the source galaxy into the destination galaxy.
/// Does not delete from the source. Deduplicates by content_hash.
pub struct GalaxyMergeTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxyMergeTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("codex".into())],
                reads: vec![Resource::Galaxy("research".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxyMergeTool {
    fn name(&self) -> &str {
        "galaxy.merge"
    }
    fn gana(&self) -> Gana {
        Gana::Neck
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Merge memories from a source galaxy into a destination (copy + dedup)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let from_galaxy = parse_galaxy(
            args.get("from_galaxy")
                .and_then(|v| v.as_str())
                .ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("Missing 'from_galaxy' parameter".into())
                })?,
        )?;
        let to_galaxy = parse_galaxy(args.get("to_galaxy").and_then(|v| v.as_str()).ok_or_else(
            || wm_core::CoreError::InvalidArgs("Missing 'to_galaxy' parameter".into()),
        )?)?;
        if from_galaxy == to_galaxy {
            return Err(wm_core::CoreError::InvalidArgs(
                "from_galaxy and to_galaxy must be different".into(),
            ));
        }
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10_000) as usize;

        let dest_mems = self.store.scan(to_galaxy, 10_000)?;
        let existing_hashes: std::collections::HashSet<String> = dest_mems
            .iter()
            .map(|m| m.metadata.content_hash.clone())
            .collect();

        let source_mems = self.store.scan(from_galaxy, limit)?;
        let mut merged = 0u32;
        let mut duplicates = 0u32;

        for mem in &source_mems {
            if existing_hashes.contains(&mem.metadata.content_hash) {
                duplicates += 1;
                continue;
            }

            let mut new_mem = Memory::new(to_galaxy, mem.content.clone());
            new_mem.metadata.tags.clone_from(&mem.metadata.tags);
            new_mem.metadata.importance = mem.metadata.importance;
            self.store.put(to_galaxy, &new_mem)?;
            merged += 1;
        }

        Ok(json!({
            "status": "success",
            "from_galaxy": galaxy_name(from_galaxy),
            "to_galaxy": galaxy_name(to_galaxy),
            "source_count": source_mems.len(),
            "merged": merged,
            "duplicates_skipped": duplicates,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `galaxy.snapshot` — capture a snapshot of a galaxy's state.
///
/// Exports all memories from a galaxy into a JSON-serializable snapshot
/// stored in the Journals galaxy. Returns the snapshot ID.
pub struct GalaxySnapshotTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxySnapshotTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("journals".into())],
                reads: vec![Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxySnapshotTool {
    fn name(&self) -> &str {
        "galaxy.snapshot"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Capture a snapshot of a galaxy's state (stored in Journals galaxy)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10_000) as usize;

        let memories = self.store.scan(galaxy, limit)?;

        let snapshot_data: Vec<Value> = memories
            .iter()
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "content": m.content,
                    "tags": m.metadata.tags,
                    "importance": m.metadata.importance,
                    "created_at": m.metadata.created_at.to_rfc3339(),
                    "content_hash": m.metadata.content_hash,
                })
            })
            .collect();

        let snapshot_id = uuid::Uuid::new_v4();
        let snapshot_content = json!({
            "type": "galaxy_snapshot",
            "snapshot_id": snapshot_id,
            "galaxy": galaxy_name(galaxy),
            "timestamp": chrono::Utc::now().to_rfc3339(),
            "memory_count": memories.len(),
            "memories": snapshot_data,
        })
        .to_string();

        let mut snapshot_mem = Memory::new(Galaxy::Journals, snapshot_content);
        snapshot_mem.metadata.tags = vec!["snapshot".to_string(), galaxy_name(galaxy).to_string()];
        self.store.put(Galaxy::Journals, &snapshot_mem)?;

        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "snapshot_id": snapshot_id,
            "memory_count": memories.len(),
            "stored_in": "journals",
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `galaxy.restore` — restore a galaxy from a stored snapshot.
///
/// Reads a snapshot from the Journals galaxy and restores the memories
/// into the target galaxy. Optionally clears the target first.
pub struct GalaxyRestoreTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxyRestoreTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("codex".into())],
                reads: vec![Resource::Galaxy("journals".into())],
                destructive: true,
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxyRestoreTool {
    fn name(&self) -> &str {
        "galaxy.restore"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Restore a galaxy from a stored snapshot in the Journals galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let snapshot_id = args
            .get("snapshot_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("Missing 'snapshot_id' parameter".into())
            })?;
        let target_galaxy =
            parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let clear_first = args
            .get("clear_first")
            .and_then(serde_json::Value::as_bool)
            .unwrap_or(false);

        let journals = self.store.scan(Galaxy::Journals, 10_000)?;
        let snapshot = journals.iter().find(|m| {
            m.metadata.tags.contains(&"snapshot".to_string()) && m.content.contains(snapshot_id)
        });

        let snapshot_mem = snapshot.ok_or_else(|| {
            wm_core::CoreError::NotFound(format!(
                "Snapshot {snapshot_id} not found in Journals galaxy"
            ))
        })?;

        let snapshot_data: Value = serde_json::from_str(&snapshot_mem.content)
            .map_err(|e| wm_core::CoreError::Memory(format!("Failed to parse snapshot: {e}")))?;

        let memories = snapshot_data
            .get("memories")
            .and_then(|v| v.as_array())
            .ok_or_else(|| wm_core::CoreError::Memory("Snapshot has no 'memories' array".into()))?;

        if clear_first {
            let existing = self.store.scan(target_galaxy, 10_000)?;
            for mem in &existing {
                self.store.delete(target_galaxy, mem.metadata.id)?;
                super::common::deindex(self.search.as_deref(), &mem.metadata.id.to_string());
            }
        }

        let mut restored = 0u32;
        for mem_val in memories {
            let content = mem_val
                .get("content")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let mut mem = Memory::new(target_galaxy, content.to_string());
            if let Some(tags) = mem_val.get("tags").and_then(|v| v.as_array()) {
                mem.metadata.tags = tags
                    .iter()
                    .filter_map(|t| t.as_str().map(String::from))
                    .collect();
            }
            if let Some(imp) = mem_val
                .get("importance")
                .and_then(serde_json::Value::as_f64)
            {
                mem.metadata.importance = imp as f32;
            }
            self.store.put(target_galaxy, &mem)?;
            super::common::index_memory(self.search.as_deref(), &mem);
            restored += 1;
        }

        Ok(json!({
            "status": "success",
            "snapshot_id": snapshot_id,
            "galaxy": galaxy_name(target_galaxy),
            "restored": restored,
            "cleared_first": clear_first,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `galaxy.dashboard` — comprehensive overview of all galaxies with counts,
/// tags, importance stats, and recent activity.
pub struct GalaxyDashboardTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxyDashboardTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxyDashboardTool {
    fn name(&self) -> &str {
        "galaxy.dashboard"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Comprehensive dashboard overview of all galaxies"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut galaxy_details = serde_json::Map::new();
        let mut total_memories = 0usize;
        let mut total_tags: std::collections::HashSet<String> = std::collections::HashSet::new();

        for galaxy in Galaxy::memory_galaxies() {
            let count = self.store.count(galaxy).unwrap_or(0);
            total_memories += count;
            if count == 0 {
                galaxy_details.insert(
                    galaxy_name(galaxy).to_string(),
                    json!({
                        "count": 0,
                        "avg_importance": 0.0,
                        "top_tags": [],
                    }),
                );
                continue;
            }

            let memories = self.store.scan(galaxy, 10_000)?;
            let mut tag_counts: std::collections::HashMap<String, u32> =
                std::collections::HashMap::new();
            let mut importance_sum = 0.0f64;
            for mem in &memories {
                for tag in &mem.metadata.tags {
                    *tag_counts.entry(tag.clone()).or_insert(0) += 1;
                    total_tags.insert(tag.clone());
                }
                importance_sum += f64::from(mem.metadata.importance);
            }
            let avg_importance = if memories.is_empty() {
                0.0
            } else {
                importance_sum / memories.len() as f64
            };
            let mut top_tags: Vec<(String, u32)> = tag_counts.into_iter().collect();
            top_tags.sort_by(|a, b| b.1.cmp(&a.1));
            top_tags.truncate(5);

            galaxy_details.insert(galaxy_name(galaxy).to_string(), json!({
                "count": count,
                "avg_importance": (avg_importance * 100.0).round() / 100.0,
                "top_tags": top_tags.into_iter().map(|(t, c)| json!({"tag": t, "count": c})).collect::<Vec<_>>(),
            }));
        }

        Ok(json!({
            "status": "success",
            "total_memories": total_memories,
            "total_galaxies_with_data": galaxy_details.len(),
            "unique_tags": total_tags.len(),
            "galaxies": galaxy_details,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `galaxy.backup` — back up all memory galaxies into a single snapshot
/// stored in the Journals galaxy. Returns the backup ID.
pub struct GalaxyBackupTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxyBackupTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("journals".into())],
                reads: vec![],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxyBackupTool {
    fn name(&self) -> &str {
        "galaxy.backup"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Back up all memory galaxies into a single snapshot in Journals"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let backup_id = uuid::Uuid::new_v4();
        let mut galaxy_data = serde_json::Map::new();
        let mut total_backed_up = 0usize;

        for galaxy in Galaxy::memory_galaxies() {
            let memories = self.store.scan(galaxy, 10_000)?;
            let count = memories.len();
            total_backed_up += count;
            galaxy_data.insert(
                galaxy_name(galaxy).to_string(),
                json!({
                    "count": count,
                    "memories": memories.iter().map(|m| {
                        json!({
                            "id": m.metadata.id,
                            "content": m.content,
                            "tags": m.metadata.tags,
                            "importance": m.metadata.importance,
                            "created_at": m.metadata.created_at.to_rfc3339(),
                            "content_hash": m.metadata.content_hash,
                        })
                    }).collect::<Vec<_>>(),
                }),
            );
        }

        let backup_content = json!({
            "type": "galaxy_backup",
            "backup_id": backup_id,
            "timestamp": chrono::Utc::now().to_rfc3339(),
            "total_memories": total_backed_up,
            "galaxies": galaxy_data,
        })
        .to_string();

        let mut backup_mem = Memory::new(Galaxy::Journals, backup_content);
        backup_mem.metadata.tags = vec!["backup".to_string()];
        backup_mem.metadata.importance = 1.0;
        self.store.put(Galaxy::Journals, &backup_mem)?;

        Ok(json!({
            "status": "success",
            "backup_id": backup_id,
            "total_memories": total_backed_up,
            "galaxies_backed_up": Galaxy::memory_galaxies().len(),
            "stored_in": "journals",
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `galaxy.taxonomy` — list all galaxies with descriptions and counts.
pub struct GalaxyTaxonomyTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxyTaxonomyTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxyTaxonomyTool {
    fn name(&self) -> &str {
        "galaxy.taxonomy"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List all galaxies with descriptions and memory counts"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let galaxies: Vec<Value> = Galaxy::all()
            .iter()
            .map(|g| {
                let count = self.store.count(*g).unwrap_or(0);
                json!({
                    "name": galaxy_name(*g),
                    "description": g.description(),
                    "count": count,
                    "is_memory_galaxy": Galaxy::memory_galaxies().contains(g),
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "total_galaxies": Galaxy::all().len(),
            "memory_galaxies": Galaxy::memory_galaxies().len(),
            "galaxies": galaxies,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `galaxy.purge` — delete all memories from a specific galaxy.
pub struct GalaxyPurgeTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxyPurgeTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("codex".into())],
                destructive: true,
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxyPurgeTool {
    fn name(&self) -> &str {
        "galaxy.purge"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Delete all memories from a specific galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy =
            parse_galaxy(args.get("galaxy").and_then(|v| v.as_str()).ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("Missing 'galaxy' parameter".into())
            })?)?;

        let memories = self.store.scan(galaxy, 10_000)?;
        let count = memories.len();
        for mem in &memories {
            self.store.delete(galaxy, mem.metadata.id)?;
            super::common::deindex(self.search.as_deref(), &mem.metadata.id.to_string());
        }

        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "purged": count,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `galaxy.health` — check the health of a specific galaxy or all galaxies.
pub struct GalaxyHealthTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GalaxyHealthTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GalaxyHealthTool {
    fn name(&self) -> &str {
        "galaxy.health"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Check health of a specific galaxy or all galaxies"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let target_galaxy = args.get("galaxy").and_then(|v| v.as_str());

        let galaxies_to_check: Vec<Galaxy> = if let Some(name) = target_galaxy {
            vec![parse_galaxy(name)?]
        } else {
            Galaxy::memory_galaxies().to_vec()
        };

        let mut results = serde_json::Map::new();
        let mut all_healthy = true;

        for galaxy in &galaxies_to_check {
            let count = self.store.count(*galaxy).unwrap_or(0);
            let scan_result = self.store.scan(*galaxy, 100);
            let accessible = scan_result.is_ok();
            if !accessible {
                all_healthy = false;
            }

            let mut avg_importance = 0.0;
            let mut tag_coverage = 0usize;
            if let Ok(mems) = &scan_result {
                if !mems.is_empty() {
                    let sum: f64 = mems.iter().map(|m| f64::from(m.metadata.importance)).sum();
                    avg_importance = sum / mems.len() as f64;
                    let tags: std::collections::HashSet<&String> =
                        mems.iter().flat_map(|m| m.metadata.tags.iter()).collect();
                    tag_coverage = tags.len();
                }
            }

            let health = if !accessible {
                "inaccessible"
            } else if count == 0 {
                "empty"
            } else {
                "healthy"
            };

            results.insert(
                galaxy_name(*galaxy).to_string(),
                json!({
                    "count": count,
                    "accessible": accessible,
                    "health": health,
                    "avg_importance": (avg_importance * 100.0).round() / 100.0,
                    "tag_coverage": tag_coverage,
                }),
            );
        }

        Ok(json!({
            "status": "success",
            "all_healthy": all_healthy,
            "galaxies_checked": galaxies_to_check.len(),
            "results": results,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
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

    #[tokio::test]
    async fn galaxy_transfer_moves_memories() {
        let (_tmp, store) = open_store();
        let mem = Memory::new(Galaxy::Codex, "test content".into());
        store.put(Galaxy::Codex, &mem).unwrap();
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 1);
        assert_eq!(store.count(Galaxy::Research).unwrap(), 0);

        let tool = GalaxyTransferTool::new(Arc::new(store), None);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"from_galaxy": "codex", "to_galaxy": "research"}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["transferred"], 1);
    }

    #[tokio::test]
    async fn galaxy_transfer_same_galaxy_errors() {
        let (_tmp, store) = open_store();
        let tool = GalaxyTransferTool::new(Arc::new(store), None);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"from_galaxy": "codex", "to_galaxy": "codex"}),
            )
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn galaxy_transfer_missing_params_errors() {
        let (_tmp, store) = open_store();
        let tool = GalaxyTransferTool::new(Arc::new(store), None);
        assert!(
            tool.call(&mut Context::default(), json!({"from_galaxy": "codex"}))
                .await
                .is_err()
        );
        assert!(
            tool.call(&mut Context::default(), json!({"to_galaxy": "codex"}))
                .await
                .is_err()
        );
    }

    #[tokio::test]
    async fn galaxy_transfer_with_tag_filter() {
        let (_tmp, store) = open_store();
        let mut mem1 = Memory::new(Galaxy::Codex, "tagged content".into());
        mem1.metadata.tags = vec!["important".to_string()];
        let mem2 = Memory::new(Galaxy::Codex, "untagged content".into());
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Codex, &mem2).unwrap();

        let tool = GalaxyTransferTool::new(Arc::new(store), None);
        let result = tool
            .call(
                &mut Context::default(),
                json!({
                    "from_galaxy": "codex",
                    "to_galaxy": "research",
                    "tags": ["important"],
                }),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["transferred"], 1);
        assert_eq!(obj["skipped"], 1);
    }

    #[tokio::test]
    async fn galaxy_merge_copies_and_dedups() {
        let (_tmp, store) = open_store();
        let mem1 = Memory::new(Galaxy::Codex, "shared content".into());
        let mem2 = Memory::new(Galaxy::Codex, "unique to codex".into());
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Codex, &mem2).unwrap();

        let mem1_copy = Memory::new(Galaxy::Research, "shared content".into());
        store.put(Galaxy::Research, &mem1_copy).unwrap();

        let tool = GalaxyMergeTool::new(Arc::new(store));
        let result = tool
            .call(
                &mut Context::default(),
                json!({"from_galaxy": "codex", "to_galaxy": "research"}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["merged"], 1);
        assert_eq!(obj["duplicates_skipped"], 1);
    }

    #[tokio::test]
    async fn galaxy_merge_same_galaxy_errors() {
        let (_tmp, store) = open_store();
        let tool = GalaxyMergeTool::new(Arc::new(store));
        let result = tool
            .call(
                &mut Context::default(),
                json!({"from_galaxy": "codex", "to_galaxy": "codex"}),
            )
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn galaxy_snapshot_and_restore_roundtrip() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        let mem1 = Memory::new(Galaxy::Codex, "first memory".into());
        let mem2 = Memory::new(Galaxy::Codex, "second memory".into());
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Codex, &mem2).unwrap();

        let snap_tool = GalaxySnapshotTool::new(store.clone());
        let snap_result = snap_tool
            .call(&mut Context::default(), json!({"galaxy": "codex"}))
            .await
            .unwrap();
        let snap_obj = snap_result.as_object().unwrap();
        assert_eq!(snap_obj["status"], "success");
        assert_eq!(snap_obj["memory_count"], 2);
        let snapshot_id = snap_obj["snapshot_id"].as_str().unwrap();

        let _ = store.delete(Galaxy::Codex, mem1.metadata.id);
        let _ = store.delete(Galaxy::Codex, mem2.metadata.id);
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 0);

        let restore_tool = GalaxyRestoreTool::new(store.clone(), None);
        let restore_result = restore_tool
            .call(
                &mut Context::default(),
                json!({
                    "snapshot_id": snapshot_id,
                    "galaxy": "codex",
                    "clear_first": false,
                }),
            )
            .await
            .unwrap();
        let restore_obj = restore_result.as_object().unwrap();
        assert_eq!(restore_obj["status"], "success");
        assert_eq!(restore_obj["restored"], 2);

        assert_eq!(store.count(Galaxy::Codex).unwrap(), 2);
    }

    #[tokio::test]
    async fn galaxy_restore_not_found_errors() {
        let (_tmp, store) = open_store();
        let tool = GalaxyRestoreTool::new(Arc::new(store), None);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"snapshot_id": "nonexistent-id"}),
            )
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn galaxy_restore_missing_snapshot_id_errors() {
        let (_tmp, store) = open_store();
        let tool = GalaxyRestoreTool::new(Arc::new(store), None);
        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn galaxy_tool_names_are_correct() {
        let store = Arc::new(open_store().1);
        assert_eq!(
            GalaxyTransferTool::new(store.clone(), None).name(),
            "galaxy.transfer"
        );
        assert_eq!(GalaxyMergeTool::new(store.clone()).name(), "galaxy.merge");
        assert_eq!(
            GalaxySnapshotTool::new(store.clone()).name(),
            "galaxy.snapshot"
        );
        assert_eq!(GalaxyRestoreTool::new(store, None).name(), "galaxy.restore");
    }

    #[tokio::test]
    async fn galaxy_tool_ganas_are_correct() {
        let store = Arc::new(open_store().1);
        assert_eq!(
            GalaxyTransferTool::new(store.clone(), None).gana(),
            Gana::Neck
        );
        assert_eq!(GalaxyMergeTool::new(store.clone()).gana(), Gana::Neck);
        assert_eq!(GalaxySnapshotTool::new(store.clone()).gana(), Gana::Void);
        assert_eq!(GalaxyRestoreTool::new(store, None).gana(), Gana::Void);
    }

    #[tokio::test]
    async fn galaxy_dashboard_shows_counts() {
        let store = Arc::new(open_store().1);
        let mem = Memory::new(Galaxy::Codex, "test".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        let tool = GalaxyDashboardTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_memories"], 1);
        assert!(result["galaxies"]["codex"]["count"].as_u64() >= Some(1));
    }

    #[tokio::test]
    async fn galaxy_backup_creates_snapshot() {
        let store = Arc::new(open_store().1);
        let mem = Memory::new(Galaxy::Codex, "backup test".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        let tool = GalaxyBackupTool::new(store.clone());
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_memories"], 1);
        assert!(result["backup_id"].as_str().is_some());

        let journals = store.scan(Galaxy::Journals, 100).unwrap();
        assert!(
            journals
                .iter()
                .any(|m| m.metadata.tags.contains(&"backup".to_string()))
        );
    }

    #[tokio::test]
    async fn galaxy_taxonomy_lists_all() {
        let store = Arc::new(open_store().1);
        let tool = GalaxyTaxonomyTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_galaxies"], 14);
        assert_eq!(result["memory_galaxies"], 10);
        let galaxies = result["galaxies"].as_array().unwrap();
        assert_eq!(galaxies.len(), 14);
    }

    #[tokio::test]
    async fn galaxy_purge_clears_galaxy() {
        let store = Arc::new(open_store().1);
        let mem1 = Memory::new(Galaxy::Codex, "first".into());
        let mem2 = Memory::new(Galaxy::Codex, "second".into());
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Codex, &mem2).unwrap();
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 2);

        let tool = GalaxyPurgeTool::new(store, None);
        let result = tool
            .call(&mut Context::default(), json!({"galaxy": "codex"}))
            .await
            .unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["purged"], 2);
    }

    #[tokio::test]
    async fn galaxy_purge_missing_param_errors() {
        let store = Arc::new(open_store().1);
        let tool = GalaxyPurgeTool::new(store, None);
        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn galaxy_health_all_galaxies() {
        let store = Arc::new(open_store().1);
        let mem = Memory::new(Galaxy::Codex, "healthy".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        let tool = GalaxyHealthTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["all_healthy"], true);
        assert_eq!(result["galaxies_checked"], 10);
    }

    #[tokio::test]
    async fn galaxy_health_single_galaxy() {
        let store = Arc::new(open_store().1);
        let tool = GalaxyHealthTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"galaxy": "codex"}))
            .await
            .unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["galaxies_checked"], 1);
        assert_eq!(result["results"]["codex"]["health"], "empty");
    }

    #[tokio::test]
    async fn galaxy_new_tool_names_are_correct() {
        let store = Arc::new(open_store().1);
        assert_eq!(
            GalaxyDashboardTool::new(store.clone()).name(),
            "galaxy.dashboard"
        );
        assert_eq!(GalaxyBackupTool::new(store.clone()).name(), "galaxy.backup");
        assert_eq!(
            GalaxyTaxonomyTool::new(store.clone()).name(),
            "galaxy.taxonomy"
        );
        assert_eq!(
            GalaxyPurgeTool::new(store.clone(), None).name(),
            "galaxy.purge"
        );
        assert_eq!(GalaxyHealthTool::new(store).name(), "galaxy.health");
    }

    #[tokio::test]
    async fn galaxy_new_tool_ganas_are_void() {
        let store = Arc::new(open_store().1);
        assert_eq!(GalaxyDashboardTool::new(store.clone()).gana(), Gana::Void);
        assert_eq!(GalaxyBackupTool::new(store.clone()).gana(), Gana::Void);
        assert_eq!(GalaxyTaxonomyTool::new(store.clone()).gana(), Gana::Void);
        assert_eq!(GalaxyPurgeTool::new(store.clone(), None).gana(), Gana::Void);
        assert_eq!(GalaxyHealthTool::new(store).gana(), Gana::Void);
    }
}
