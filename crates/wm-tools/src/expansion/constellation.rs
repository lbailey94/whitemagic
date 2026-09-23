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
        let spatial = args.get("spatial").and_then(Value::as_bool).unwrap_or(true);
        if spatial {
            let mut detector = wm_cognitive::constellation::ConstellationDetector::default();
            if let Ok(report) = detector.detect(&self.store) {
                if !report.constellations.is_empty() {
                    let clusters: Vec<Value> = report
                        .constellations
                        .into_iter()
                        .map(|c| {
                            json!({
                                "name": c.name,
                                "count": c.size,
                                "centroid": [c.centroid.0, c.centroid.1, c.centroid.2],
                                "dominant_tags": c.dominant_tags,
                                "galaxies": c.galaxies.iter().map(|g| g.db_name()).collect::<Vec<_>>(),
                                "sample_memory_ids": c.memory_ids.into_iter().take(5).map(|id| id.to_string()).collect::<Vec<_>>()
                            })
                        })
                        .collect();

                    return Ok(json!({
                        "status": "success",
                        "mode": "spatial_density_clustering_5d",
                        "memories_analyzed": report.memories_analyzed,
                        "dense_cells": report.dense_cells,
                        "constellations": clusters.len(),
                        "clusters": clusters
                    }));
                }
            }
        }

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
            "mode": "tag_frequency_clustering",
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

#[cfg(test)]
mod tests {
    use super::*;
    use wm_memory::Memory;

    fn open_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        (tmp, store)
    }

    fn put_tagged(store: &MemoryStore, tag: &str, count: usize) {
        for i in 0..count {
            let mut memory = Memory::new(Galaxy::Codex, format!("{tag} fixture {i}"));
            memory.metadata.tags = vec![tag.to_string()];
            store.put(Galaxy::Codex, &memory).unwrap();
        }
    }

    #[tokio::test]
    async fn constellation_detect_groups_tags_above_min_cluster_size() {
        let (_tmp, store) = open_store();
        put_tagged(&store, "alpha", 3);
        put_tagged(&store, "beta", 1);

        // `spatial: false` pins the documented tag-frequency fallback: the
        // min_cluster_size argument is ignored on the spatial path.
        let result = ConstellationDetectTool::new(store)
            .call(
                &mut Context::default(),
                json!({"spatial": false, "min_cluster_size": 3}),
            )
            .await
            .unwrap();
        assert_eq!(result["mode"], "tag_frequency_clustering");
        assert_eq!(result["constellations"], 1);
        let clusters = result["clusters"].as_array().unwrap();
        assert_eq!(clusters.len(), 1);
        assert_eq!(clusters[0]["tag"], "alpha");
        assert_eq!(clusters[0]["count"], 3);
    }

    #[tokio::test]
    async fn constellation_list_uses_the_fixed_three_memory_threshold() {
        let (_tmp, store) = open_store();
        put_tagged(&store, "alpha", 3);
        put_tagged(&store, "beta", 2);

        let result = ConstellationListTool::new(store)
            .call(&mut Context::default(), json!({}))
            .await
            .unwrap();
        let clusters = result["constellations"].as_array().unwrap();
        let tags: Vec<&str> = clusters
            .iter()
            .map(|c| c["tag"].as_str().unwrap())
            .collect();
        assert!(
            tags.contains(&"alpha"),
            "alpha (3) must be listed: {tags:?}"
        );
        assert!(
            !tags.contains(&"beta"),
            "beta (2) must not be listed: {tags:?}"
        );
        // `total_tags` is the constellation count, not a raw tag total.
        assert_eq!(
            result["total_tags"].as_u64().unwrap() as usize,
            clusters.len()
        );
    }
}
