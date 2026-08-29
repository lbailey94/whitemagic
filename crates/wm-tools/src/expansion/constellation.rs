//! Constellation tools — detect, list.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use super::common::galaxy_name;
use serde_json::{Value, json};
use std::collections::HashMap;
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;

pub struct ConstellationDetectTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConstellationDetectTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("universal".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ConstellationDetectTool {
    fn name(&self) -> &str {
        "constellation.detect"
    }
    fn gana(&self) -> Gana {
        Gana::Star
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Detect tag clusters (constellations) across galaxies"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let min_cluster = args
            .get("min_cluster_size")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(3) as usize;
        let mut tag_locations: HashMap<String, Vec<(String, uuid::Uuid)>> = HashMap::new();
        for galaxy in Galaxy::memory_galaxies() {
            let memories = self.store.scan(galaxy, 500)?;
            for mem in memories {
                for tag in &mem.metadata.tags {
                    tag_locations
                        .entry(tag.clone())
                        .or_default()
                        .push((galaxy_name(galaxy).to_string(), mem.metadata.id));
                }
            }
        }
        let constellations: Vec<Value> = tag_locations.iter()
            .filter(|(_, locs)| locs.len() >= min_cluster)
            .map(|(tag, locs)| json!({
                "tag": tag,
                "count": locs.len(),
                "galaxies": locs.iter().map(|(g, _)| g.clone()).collect::<std::collections::HashSet<_>>().len(),
            }))
            .collect();
        Ok(json!({
            "status": "success",
            "min_cluster_size": min_cluster,
            "constellations": constellations.len(),
            "clusters": constellations,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `constellation.list` — list all detected constellations.
pub struct ConstellationListTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ConstellationListTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("universal".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ConstellationListTool {
    fn name(&self) -> &str {
        "constellation.list"
    }
    fn gana(&self) -> Gana {
        Gana::Star
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List all tag constellations (clusters with 3+ memories)"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut tag_counts: HashMap<String, usize> = HashMap::new();
        for galaxy in Galaxy::memory_galaxies() {
            let memories = self.store.scan(galaxy, 500)?;
            for mem in memories {
                for tag in &mem.metadata.tags {
                    *tag_counts.entry(tag.clone()).or_insert(0) += 1;
                }
            }
        }
        let constellations: Vec<(String, usize)> =
            tag_counts.into_iter().filter(|(_, c)| *c >= 3).collect();
        Ok(json!({
            "status": "success",
            "total_tags": constellations.len(),
            "constellations": constellations.into_iter().map(|(tag, count)| json!({
                "tag": tag,
                "count": count,
            })).collect::<Vec<_>>(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}
