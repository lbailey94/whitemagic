//! Pattern tools — pattern.search, salience.spotlight, serendipity.surface.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{AssociationStore, MemoryStore};

use super::common::{galaxy_name, parse_galaxy};

pub struct PatternSearchTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl PatternSearchTool {
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
impl Tool for PatternSearchTool {
    fn name(&self) -> &str {
        "pattern.search"
    }
    fn gana(&self) -> Gana {
        Gana::Ox
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Search for patterns in memory content across galaxies"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let pattern = args.get("pattern").and_then(|v| v.as_str()).unwrap_or("");
        let galaxies = args.get("galaxies").and_then(|v| v.as_array());
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(20) as usize;
        let galaxies_to_search: Vec<Galaxy> = match galaxies {
            Some(arr) => {
                let mut parsed = Vec::new();
                for g in arr {
                    if let Some(name) = g.as_str() {
                        parsed.push(parse_galaxy(name)?);
                    }
                }
                parsed
            }
            None => Galaxy::memory_galaxies().to_vec(),
        };
        let mut matches = Vec::new();
        for galaxy in &galaxies_to_search {
            let memories = self.store.scan(*galaxy, 500)?;
            for mem in memories {
                if mem.content.to_lowercase().contains(&pattern.to_lowercase()) {
                    matches.push(json!({
                        "galaxy": galaxy_name(*galaxy),
                        "id": mem.metadata.id,
                        "content_preview": mem.content.chars().take(100).collect::<String>(),
                    }));
                    if matches.len() >= limit {
                        break;
                    }
                }
            }
            if matches.len() >= limit {
                break;
            }
        }
        Ok(json!({
            "status": "success",
            "pattern": pattern,
            "matches": matches.len(),
            "results": matches,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `salience.spotlight` — find high-importance memories across galaxies.
pub struct SalienceSpotlightTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SalienceSpotlightTool {
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
impl Tool for SalienceSpotlightTool {
    fn name(&self) -> &str {
        "salience.spotlight"
    }
    fn gana(&self) -> Gana {
        Gana::Ox
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Find high-importance memories across all galaxies"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let min_importance = args
            .get("min_importance")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.8) as f32;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(20) as usize;
        let mut spotlighted = Vec::new();
        for galaxy in Galaxy::memory_galaxies() {
            let memories = self.store.scan(galaxy, 200)?;
            for mem in memories {
                if mem.metadata.importance >= min_importance {
                    spotlighted.push(json!({
                        "galaxy": galaxy_name(galaxy),
                        "id": mem.metadata.id,
                        "importance": mem.metadata.importance,
                        "content_preview": mem.content.chars().take(80).collect::<String>(),
                    }));
                }
            }
        }
        spotlighted.sort_by(|a, b| {
            b["importance"]
                .as_f64()
                .unwrap_or(0.0)
                .partial_cmp(&a["importance"].as_f64().unwrap_or(0.0))
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        spotlighted.truncate(limit);
        Ok(json!({
            "status": "success",
            "min_importance": min_importance,
            "count": spotlighted.len(),
            "spotlight": spotlighted,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `serendipity.surface` — surface unexpected cross-galaxy connections.
pub struct SerendipitySurfaceTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SerendipitySurfaceTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("associations".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SerendipitySurfaceTool {
    fn name(&self) -> &str {
        "serendipity.surface"
    }
    fn gana(&self) -> Gana {
        Gana::Star
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Surface unexpected cross-galaxy connections from associations"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;
        let total = assoc_store.count(env)?;

        // Sample memories from each galaxy to find cross-galaxy associations
        let mut cross_galaxy: Vec<Value> = Vec::new();
        for galaxy in Galaxy::memory_galaxies() {
            let memories = self.store.scan(galaxy, 50)?;
            for mem in &memories {
                let assocs = assoc_store.find_from(env, mem.metadata.id)?;
                for assoc in &assocs {
                    // Check if target is in a different galaxy
                    for other_galaxy in Galaxy::memory_galaxies() {
                        if other_galaxy != galaxy {
                            if let Ok(Some(_)) = self.store.get(other_galaxy, assoc.target) {
                                cross_galaxy.push(json!({
                                    "source_galaxy": galaxy_name(galaxy),
                                    "target_galaxy": galaxy_name(other_galaxy),
                                    "weight": assoc.weight,
                                    "link_type": assoc.link_type.as_str(),
                                    "association_type": assoc.association_type,
                                }));
                            }
                        }
                    }
                }
            }
        }

        Ok(json!({
            "status": "success",
            "total_associations": total,
            "cross_galaxy_links": cross_galaxy.len(),
            "serendipities": cross_galaxy.into_iter().take(20).collect::<Vec<_>>(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}
