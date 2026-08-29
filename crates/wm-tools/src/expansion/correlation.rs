//! Correlation & god-node tools — correlation.analyze, god.nodes.
//!
//! Gana::HairyHead — "Graph traversal, correlation, hub detection"
//!
//! `correlation.analyze` finds statistical correlations between tags and
//! content keywords across galaxies. `god.nodes` identifies hub entities
//! that appear across many memories — the most connected nodes in the
//! knowledge graph.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::collections::HashMap;
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;

use super::common::{galaxy_name, parse_galaxy};

// ── correlation.analyze ──────────────────────────────────────────────

/// Analyze correlations between tags, keywords, and galaxies.
///
/// Computes Pearson-style co-occurrence correlations between tag pairs
/// and identifies which galaxies share the most overlapping content.
pub struct CorrelationAnalyzeTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl CorrelationAnalyzeTool {
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
impl Tool for CorrelationAnalyzeTool {
    fn name(&self) -> &str {
        "correlation.analyze"
    }
    fn gana(&self) -> Gana {
        Gana::HairyHead
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Analyze statistical correlations between tags, keywords, and galaxies"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_str = args.get("galaxy").and_then(|v| v.as_str());
        let top_n = args
            .get("top_n")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;
        let scan_limit = args
            .get("scan_limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(500) as usize;

        let galaxies: Vec<Galaxy> = match galaxy_str {
            Some(g) => vec![parse_galaxy(g)?],
            None => Galaxy::memory_galaxies().to_vec(),
        };

        // Collect tag presence vectors per memory
        let mut tag_memories: HashMap<String, Vec<bool>> = HashMap::new();
        let mut total_memories = 0usize;
        let mut galaxy_counts: HashMap<Galaxy, usize> = HashMap::new();

        // First pass: collect all tags and memory count
        let mut all_tags: Vec<String> = Vec::new();
        for galaxy in &galaxies {
            let mems = self.store.scan(*galaxy, scan_limit)?;
            for mem in &mems {
                total_memories += 1;
                *galaxy_counts.entry(*galaxy).or_default() += 1;
                for tag in &mem.metadata.tags {
                    if !all_tags.contains(tag) {
                        all_tags.push(tag.clone());
                    }
                }
            }
        }

        if total_memories == 0 || all_tags.is_empty() {
            return Ok(json!({
                "status": "success",
                "total_memories": 0,
                "correlations": [],
                "galaxy_distribution": {},
            }));
        }

        // Build tag presence vectors
        for tag in &all_tags {
            tag_memories.insert(tag.clone(), vec![false; total_memories]);
        }

        let mut mem_idx = 0;
        for galaxy in &galaxies {
            let mems = self.store.scan(*galaxy, scan_limit)?;
            for mem in &mems {
                for tag in &mem.metadata.tags {
                    if let Some(vec) = tag_memories.get_mut(tag) {
                        vec[mem_idx] = true;
                    }
                }
                mem_idx += 1;
            }
        }

        // Compute phi coefficient (binary correlation) for tag pairs
        let mut correlations: Vec<(String, String, f64)> = Vec::new();
        for i in 0..all_tags.len() {
            for j in (i + 1)..all_tags.len() {
                let vec_a = &tag_memories[&all_tags[i]];
                let vec_b = &tag_memories[&all_tags[j]];
                let n11 = vec_a
                    .iter()
                    .zip(vec_b.iter())
                    .filter(|(a, b)| **a && **b)
                    .count() as f64;
                let n10 = vec_a
                    .iter()
                    .zip(vec_b.iter())
                    .filter(|(a, b)| **a && !**b)
                    .count() as f64;
                let n01 = vec_a
                    .iter()
                    .zip(vec_b.iter())
                    .filter(|(a, b)| !**a && **b)
                    .count() as f64;
                let n00 = vec_a
                    .iter()
                    .zip(vec_b.iter())
                    .filter(|(a, b)| !**a && !**b)
                    .count() as f64;

                let n1_plus = n11 + n10;
                let n0_plus = n01 + n00;
                let nplus1 = n11 + n01;
                let nplus0 = n10 + n00;

                let denom = (n1_plus * n0_plus * nplus1 * nplus0).sqrt();
                let phi = if denom > 0.0 {
                    n11.mul_add(n00, -(n10 * n01)) / denom
                } else {
                    0.0
                };

                if phi.abs() > 0.1 {
                    correlations.push((all_tags[i].clone(), all_tags[j].clone(), phi));
                }
            }
        }

        correlations.sort_by(|a, b| {
            b.2.abs()
                .partial_cmp(&a.2.abs())
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        correlations.truncate(top_n);

        let correlation_results: Vec<Value> = correlations
            .into_iter()
            .map(|(t1, t2, phi)| {
                json!({
                    "tag_a": t1,
                    "tag_b": t2,
                    "phi_coefficient": (phi * 1000.0).round() / 1000.0,
                    "strength": if phi > 0.5 { "strong_positive" } else if phi > 0.0 { "weak_positive" } else if phi < -0.5 { "strong_negative" } else { "weak_negative" },
                })
            })
            .collect();

        // Galaxy distribution
        let galaxy_dist: Vec<Value> = galaxy_counts
            .iter()
            .map(|(g, count)| {
                json!({
                    "galaxy": galaxy_name(*g),
                    "count": count,
                    "percentage": ((*count as f64 / total_memories as f64) * 100.0).round() / 100.0,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "total_memories": total_memories,
            "unique_tags": all_tags.len(),
            "correlations": correlation_results,
            "galaxy_distribution": galaxy_dist,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── god.nodes ────────────────────────────────────────────────────────

/// Identify god nodes — entities that appear across many memories and
/// connect disparate knowledge areas.
///
/// Unlike `kg.top` (which uses the association graph), `god.nodes` works
/// directly on memory content, extracting capitalized entities and ranking
/// them by cross-galaxy presence and importance-weighted frequency.
pub struct GodNodesTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GodNodesTool {
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
impl Tool for GodNodesTool {
    fn name(&self) -> &str {
        "god.nodes"
    }
    fn gana(&self) -> Gana {
        Gana::HairyHead
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Identify hub entities (god nodes) that connect many memories across galaxies"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let top_n = args
            .get("top_n")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;
        let min_galaxies = args
            .get("min_galaxies")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(1) as usize;
        let scan_limit = args
            .get("scan_limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(500) as usize;

        // Track entity stats: (count, galaxies set, total_importance)
        let mut entity_stats: HashMap<String, (u32, std::collections::HashSet<Galaxy>, f32)> =
            HashMap::new();

        for galaxy in Galaxy::memory_galaxies() {
            let mems = self.store.scan(galaxy, scan_limit)?;
            for mem in &mems {
                // Extract capitalized entities (simple heuristic)
                for word in mem.content.split_whitespace() {
                    let cleaned: String = word.chars().filter(|c| c.is_alphanumeric()).collect();
                    if cleaned.len() > 2 && cleaned.chars().next().is_some_and(char::is_uppercase) {
                        let entry = entity_stats
                            .entry(cleaned)
                            .or_insert_with(|| (0, std::collections::HashSet::new(), 0.0));
                        entry.0 += 1;
                        entry.1.insert(galaxy);
                        entry.2 += mem.metadata.importance;
                    }
                }
            }
        }

        // Filter and rank by cross-galaxy presence, then by count
        let mut nodes: Vec<(String, u32, usize, f32)> = entity_stats
            .into_iter()
            .filter(|(_, (_, galaxies, _))| galaxies.len() >= min_galaxies)
            .map(|(entity, (count, galaxies, imp))| (entity, count, galaxies.len(), imp))
            .collect();

        // Sort by galaxy count (desc), then by memory count (desc), then by importance (desc)
        nodes.sort_by(|a, b| {
            b.2.cmp(&a.2)
                .then_with(|| b.1.cmp(&a.1))
                .then_with(|| b.3.partial_cmp(&a.3).unwrap_or(std::cmp::Ordering::Equal))
        });

        let total_entities = nodes.len();
        nodes.truncate(top_n);

        let god_nodes: Vec<Value> = nodes
            .into_iter()
            .map(|(entity, count, galaxy_count, total_imp)| {
                json!({
                    "entity": entity,
                    "memory_count": count,
                    "galaxy_count": galaxy_count,
                    "total_importance": (total_imp * 100.0).round() / 100.0,
                    "avg_importance": ((total_imp / count as f32) * 100.0).round() / 100.0,
                    "is_god_node": galaxy_count >= 3,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "total_entities": total_entities,
            "god_node_count": god_nodes.iter().filter(|n| n["is_god_node"].as_bool().unwrap_or(false)).count(),
            "min_galaxies": min_galaxies,
            "nodes": god_nodes,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn open_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, Arc::new(store))
    }

    fn seed_memories(store: &Arc<MemoryStore>) {
        let entries = [
            (
                Galaxy::Codex,
                "Rust programming with Rust ownership model",
                vec!["rust", "programming"],
                0.9,
            ),
            (
                Galaxy::Research,
                "Rust traits and Rust generics explained",
                vec!["rust", "traits"],
                0.8,
            ),
            (
                Galaxy::Tutorial,
                "Python basics and Python data structures",
                vec!["python", "basics"],
                0.5,
            ),
            (
                Galaxy::Codex,
                "Python async programming with Python asyncio",
                vec!["python", "async"],
                0.6,
            ),
            (
                Galaxy::Research,
                "Database design with Database indexing strategies",
                vec!["database", "design"],
                0.7,
            ),
        ];

        for (galaxy, content, tags, imp) in entries {
            let mut mem = wm_memory::Memory::new(galaxy, content.into());
            mem.metadata.tags = tags.iter().map(std::string::ToString::to_string).collect();
            mem.metadata.importance = imp;
            store.put(galaxy, &mem).unwrap();
        }
    }

    #[tokio::test]
    async fn correlation_analyze_finds_tag_correlations() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = CorrelationAnalyzeTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"top_n": 10}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["total_memories"].as_u64().unwrap() >= 5);
        assert!(obj["unique_tags"].as_u64().unwrap() >= 4);
        // Should have some correlations
        let correlations = obj["correlations"].as_array().unwrap();
        // "rust" and "programming" co-occur, "python" and "basics" co-occur
        assert!(!correlations.is_empty());
    }

    #[tokio::test]
    async fn correlation_analyze_empty_store() {
        let (_tmp, store) = open_store();
        let tool = CorrelationAnalyzeTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["total_memories"], 0);
        assert_eq!(obj["correlations"].as_array().unwrap().len(), 0);
    }

    #[tokio::test]
    async fn correlation_analyze_galaxy_distribution() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = CorrelationAnalyzeTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        let dist = obj["galaxy_distribution"].as_array().unwrap();
        assert!(!dist.is_empty());
    }

    #[tokio::test]
    async fn god_nodes_finds_entities() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = GodNodesTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"top_n": 5}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["total_entities"].as_u64().unwrap() > 0);
        let nodes = obj["nodes"].as_array().unwrap();
        assert!(!nodes.is_empty());
        // "Rust" appears in 2 galaxies (Codex, Research)
        let rust_node = nodes.iter().find(|n| n["entity"] == "Rust");
        assert!(rust_node.is_some(), "Expected 'Rust' in god nodes");
        assert!(rust_node.unwrap()["memory_count"].as_u64().unwrap() >= 2);
    }

    #[tokio::test]
    async fn god_nodes_min_galaxies_filter() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = GodNodesTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"top_n": 20, "min_galaxies": 2}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        let nodes = obj["nodes"].as_array().unwrap();
        // All nodes should have galaxy_count >= 2
        for node in nodes {
            assert!(
                node["galaxy_count"].as_u64().unwrap() >= 2,
                "All nodes should have galaxy_count >= 2"
            );
        }
    }

    #[tokio::test]
    async fn god_nodes_empty_store() {
        let (_tmp, store) = open_store();
        let tool = GodNodesTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["total_entities"], 0);
        assert_eq!(obj["nodes"].as_array().unwrap().len(), 0);
    }
}
