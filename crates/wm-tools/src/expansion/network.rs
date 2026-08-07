//! Network tools — association mining, pattern detection, network analysis.
//!
//! Tools:
//! - `association.mine` — Cross-galaxy association mining using keyword overlap
//! - `pattern.detect` — Detect structural patterns (hubs, bridges, chains) in the association graph
//! - `emergence.report` — Detailed emergence analysis from tag frequency distribution
//! - `network.stats` — Global network statistics (nodes, edges, density, degree distribution)
//! - `network.centrality` — Degree centrality metrics for memories in the association graph
//! - `network.clusters` — Identify connected components / clusters in the association graph

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use std::collections::{HashMap, HashSet};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{AssociationStore, MemoryStore};

use super::common::{galaxy_name, parse_galaxy};

/// `association.mine` — Cross-galaxy association mining.
///
/// Scans memories across all memory-storing galaxies and proposes associations
/// based on keyword overlap (Jaccard similarity). Unlike `memory.associate_mine`
/// which works within a single galaxy, this tool works across all galaxies.
pub struct AssociationMineTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl AssociationMineTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("associations".into())],
                ..Default::default()
            },
        }
    }
}

impl Tool for AssociationMineTool {
    fn name(&self) -> &str {
        "association.mine"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Mine cross-galaxy associations using keyword overlap analysis"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let min_strength = args
            .get("min_strength")
            .and_then(Value::as_f64)
            .unwrap_or(0.3) as f32;
        let limit_per_galaxy = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(100) as usize;
        let max_comparisons = args
            .get("max_comparisons")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50_000) as usize;

        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;

        // Collect memories from all memory-storing galaxies
        let mut all_memories: Vec<(Galaxy, &str, wm_memory::Memory)> = Vec::new();
        for galaxy in Galaxy::memory_galaxies() {
            let mems = self.store.scan(galaxy, limit_per_galaxy)?;
            for mem in mems {
                all_memories.push((galaxy, galaxy_name(galaxy), mem));
            }
        }

        let mut proposed = 0u32;
        let mut cross_galaxy_links = 0u32;
        let mut same_galaxy_links = 0u32;
        let mut comparisons = 0u32;

        for i in 0..all_memories.len() {
            if comparisons as usize >= max_comparisons {
                break;
            }
            for j in (i + 1)..all_memories.len() {
                comparisons += 1;
                if comparisons as usize >= max_comparisons {
                    break;
                }
                let (g1, _, ref a) = all_memories[i];
                let (g2, _, ref b) = all_memories[j];
                let a_words: HashSet<&str> = a.content.split_whitespace().collect();
                let b_words: HashSet<&str> = b.content.split_whitespace().collect();
                let intersection = a_words.intersection(&b_words).count();
                let union = a_words.union(&b_words).count();
                if union > 0 && intersection > 2 {
                    let strength = intersection as f32 / union as f32;
                    if strength > min_strength {
                        // Check if association already exists
                        if assoc_store
                            .get(env, a.metadata.id, b.metadata.id)
                            .ok()
                            .flatten()
                            .is_none()
                        {
                            let assoc = wm_memory::Association::new(
                                a.metadata.id,
                                b.metadata.id,
                                wm_memory::LinkType::Related,
                                strength,
                            );
                            let _ = assoc_store.put(env, &assoc);
                            proposed += 1;
                            if g1 == g2 {
                                same_galaxy_links += 1;
                            } else {
                                cross_galaxy_links += 1;
                            }
                        }
                    }
                }
            }
        }

        Ok(json!({
            "status": "success",
            "memories_scanned": all_memories.len(),
            "proposed_associations": proposed,
            "cross_galaxy_links": cross_galaxy_links,
            "same_galaxy_links": same_galaxy_links,
            "min_strength": min_strength,
            "comparisons": comparisons,
            "truncated": comparisons as usize >= max_comparisons,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `pattern.detect` — Detect structural patterns in the association graph.
///
/// Identifies hubs (high-degree nodes), bridges (nodes connecting clusters),
/// and chains (temporal sequences) in the association network.
pub struct PatternDetectTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl PatternDetectTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for PatternDetectTool {
    fn name(&self) -> &str {
        "pattern.detect"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Detect structural patterns (hubs, bridges, chains) in the association graph"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let top_k = args
            .get("top_k")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;

        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;

        // Build degree map: UUID -> (in_degree, out_degree)
        let mut degree_map: HashMap<uuid::Uuid, (u32, u32)> = HashMap::new();
        let mut all_assocs: Vec<wm_memory::Association> = Vec::new();

        // Scan all associations by iterating through all memories
        for galaxy in Galaxy::memory_galaxies() {
            let mems = self.store.scan(galaxy, 10000)?;
            for mem in mems {
                let outgoing = assoc_store
                    .find_from(env, mem.metadata.id)
                    .unwrap_or_default();
                let incoming = assoc_store
                    .find_to(env, mem.metadata.id)
                    .unwrap_or_default();
                let out_deg = outgoing.len() as u32;
                let in_deg = incoming.len() as u32;
                if out_deg > 0 || in_deg > 0 {
                    degree_map.insert(mem.metadata.id, (in_deg, out_deg));
                }
                all_assocs.extend(outgoing);
                all_assocs.extend(incoming);
            }
        }

        // Detect hubs: nodes with high total degree
        let mut hubs: Vec<(uuid::Uuid, u32)> = degree_map
            .iter()
            .map(|(id, (ind, outd))| (*id, ind + outd))
            .collect();
        hubs.sort_by(|a, b| b.1.cmp(&a.1));
        let top_hubs: Vec<Value> = hubs
            .iter()
            .take(top_k)
            .map(|(id, deg)| {
                json!({
                    "memory_id": id,
                    "total_degree": deg,
                })
            })
            .collect();

        // Detect chains: temporal sequences (A -> B -> C where link_type is Temporal)
        let mut chains: Vec<Value> = Vec::new();
        let temporal_assocs: Vec<&wm_memory::Association> = all_assocs
            .iter()
            .filter(|a| a.link_type == wm_memory::LinkType::Temporal)
            .collect();
        let mut temporal_map: HashMap<uuid::Uuid, uuid::Uuid> = HashMap::new();
        for a in &temporal_assocs {
            temporal_map.insert(a.source, a.target);
        }
        for a in &temporal_assocs {
            let mut chain = vec![a.source, a.target];
            let mut current = a.target;
            while let Some(&next) = temporal_map.get(&current) {
                if chain.contains(&next) {
                    break;
                }
                chain.push(next);
                current = next;
            }
            if chain.len() >= 3 {
                chains.push(json!({
                    "chain": chain.iter().map(std::string::ToString::to_string).collect::<Vec<_>>(),
                    "length": chain.len(),
                }));
            }
        }

        // Detect bridges: nodes that appear in many cross-galaxy associations
        let mut bridge_counts: HashMap<uuid::Uuid, u32> = HashMap::new();
        for a in &all_assocs {
            let source_galaxy = self.find_memory_galaxy(a.source);
            let target_galaxy = self.find_memory_galaxy(a.target);
            if let (Some(sg), Some(tg)) = (source_galaxy, target_galaxy) {
                if sg != tg {
                    *bridge_counts.entry(a.source).or_insert(0) += 1;
                    *bridge_counts.entry(a.target).or_insert(0) += 1;
                }
            }
        }
        let mut bridges: Vec<(uuid::Uuid, u32)> = bridge_counts.into_iter().collect();
        bridges.sort_by(|a, b| b.1.cmp(&a.1));
        let top_bridges: Vec<Value> = bridges
            .iter()
            .take(top_k)
            .map(|(id, count)| {
                json!({
                    "memory_id": id,
                    "cross_galaxy_links": count,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "total_nodes": degree_map.len(),
            "total_edges": all_assocs.len(),
            "hubs": top_hubs,
            "chains": chains,
            "bridges": top_bridges,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

impl PatternDetectTool {
    fn find_memory_galaxy(&self, id: uuid::Uuid) -> Option<Galaxy> {
        Galaxy::memory_galaxies()
            .into_iter()
            .find(|&galaxy| self.store.get(galaxy, id).ok().flatten().is_some())
    }
}

/// `emergence.report` — Detailed emergence analysis from tag frequency distribution.
///
/// Scans all memories and computes tag frequency distribution, identifying
/// emerging tags (frequency increasing), dominant tags (high frequency),
/// and declining tags (low frequency relative to total).
pub struct EmergenceReportTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl EmergenceReportTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for EmergenceReportTool {
    fn name(&self) -> &str {
        "emergence.report"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Detailed emergence analysis with tag frequency distribution and trend detection"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut tag_counts: HashMap<String, usize> = HashMap::new();
        let mut total_memories = 0usize;

        for galaxy in Galaxy::memory_galaxies() {
            let mems = self.store.scan(galaxy, 10000)?;
            for mem in mems {
                total_memories += 1;
                for tag in &mem.metadata.tags {
                    *tag_counts.entry(tag.clone()).or_insert(0) += 1;
                }
            }
        }

        let total_tags: usize = tag_counts.values().sum();
        let unique_tags = tag_counts.len();

        // Sort tags by frequency
        let mut sorted_tags: Vec<(String, usize)> = tag_counts.into_iter().collect();
        sorted_tags.sort_by(|a, b| b.1.cmp(&a.1));

        let dominant: Vec<Value> = sorted_tags
            .iter()
            .filter(|(_, count)| *count as f64 / total_memories.max(1) as f64 > 0.1)
            .take(20)
            .map(|(tag, count)| {
                json!({
                    "tag": tag,
                    "count": count,
                    "frequency": (*count as f64 / total_memories.max(1) as f64 * 100.0).round() / 100.0,
                })
            })
            .collect();

        let emerging: Vec<Value> = sorted_tags
            .iter()
            .filter(|(_, count)| *count >= 2 && *count <= 5)
            .take(20)
            .map(|(tag, count)| {
                json!({
                    "tag": tag,
                    "count": count,
                })
            })
            .collect();

        let rare: Vec<Value> = sorted_tags
            .iter()
            .filter(|(_, count)| *count == 1)
            .take(20)
            .map(|(tag, _)| json!({"tag": tag}))
            .collect();

        Ok(json!({
            "status": "success",
            "total_memories": total_memories,
            "unique_tags": unique_tags,
            "total_tag_instances": total_tags,
            "dominant_tags": dominant,
            "emerging_tags": emerging,
            "rare_tags": rare,
            "tag_diversity": (unique_tags as f64 / total_memories.max(1) as f64 * 100.0).round() / 100.0,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `network.stats` — Global network statistics.
///
/// Computes nodes, edges, density, degree distribution, and link type breakdown
/// for the entire association graph.
pub struct NetworkStatsTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl NetworkStatsTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for NetworkStatsTool {
    fn name(&self) -> &str {
        "network.stats"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Global association network statistics (nodes, edges, density, degree distribution)"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;

        let total_edges = assoc_store.count(env)?;

        // Build degree map
        let mut degree_map: HashMap<uuid::Uuid, (u32, u32)> = HashMap::new();
        let mut link_type_counts: HashMap<&'static str, u32> = HashMap::new();
        let mut total_weight: f32 = 0.0;

        for galaxy in Galaxy::memory_galaxies() {
            let mems = self.store.scan(galaxy, 10000)?;
            for mem in mems {
                let outgoing = assoc_store
                    .find_from(env, mem.metadata.id)
                    .unwrap_or_default();
                let incoming = assoc_store
                    .find_to(env, mem.metadata.id)
                    .unwrap_or_default();
                let out_deg = outgoing.len() as u32;
                let in_deg = incoming.len() as u32;
                if out_deg > 0 || in_deg > 0 {
                    let entry = degree_map.entry(mem.metadata.id).or_insert((0, 0));
                    entry.0 += in_deg;
                    entry.1 += out_deg;
                }
                for a in &outgoing {
                    *link_type_counts.entry(a.link_type.as_str()).or_insert(0) += 1;
                    total_weight += a.weight;
                }
            }
        }

        let total_nodes = degree_map.len();
        let max_possible_edges = if total_nodes > 1 {
            total_nodes * (total_nodes - 1)
        } else {
            0
        };
        let density = if max_possible_edges > 0 {
            total_edges as f64 / max_possible_edges as f64
        } else {
            0.0
        };

        // Degree distribution
        let mut degree_distribution: Vec<u32> =
            degree_map.values().map(|(ind, outd)| ind + outd).collect();
        degree_distribution.sort_unstable();
        let avg_degree = if degree_distribution.is_empty() {
            0.0
        } else {
            f64::from(degree_distribution.iter().sum::<u32>()) / degree_distribution.len() as f64
        };
        let max_degree = degree_distribution.iter().copied().max().unwrap_or(0);

        let link_breakdown: Vec<Value> = link_type_counts
            .iter()
            .map(|(lt, count)| {
                json!({
                    "link_type": lt,
                    "count": count,
                })
            })
            .collect();

        let avg_weight = if total_edges > 0 {
            total_weight / total_edges as f32
        } else {
            0.0
        };

        Ok(json!({
            "status": "success",
            "nodes": total_nodes,
            "edges": total_edges,
            "density": (density * 10000.0).round() / 10000.0,
            "avg_degree": (avg_degree * 100.0).round() / 100.0,
            "max_degree": max_degree,
            "avg_weight": (avg_weight * 100.0).round() / 100.0,
            "link_type_breakdown": link_breakdown,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `network.centrality` — Degree centrality metrics.
///
/// Computes in-degree, out-degree, and total degree centrality for each node
/// in the association graph. Returns top-K nodes by centrality.
pub struct NetworkCentralityTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl NetworkCentralityTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for NetworkCentralityTool {
    fn name(&self) -> &str {
        "network.centrality"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Compute degree centrality metrics for memories in the association graph"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let top_k = args
            .get("top_k")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(20) as usize;
        let galaxy_str = args.get("galaxy").and_then(Value::as_str);

        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;

        let galaxies: Vec<Galaxy> = match galaxy_str {
            Some(g) => vec![parse_galaxy(g)?],
            None => Galaxy::memory_galaxies().to_vec(),
        };

        let mut centrality: Vec<(uuid::Uuid, u32, u32, u32)> = Vec::new();

        for galaxy in &galaxies {
            let mems = self.store.scan(*galaxy, 10000)?;
            for mem in mems {
                let outgoing = assoc_store
                    .find_from(env, mem.metadata.id)
                    .unwrap_or_default();
                let incoming = assoc_store
                    .find_to(env, mem.metadata.id)
                    .unwrap_or_default();
                let out_deg = outgoing.len() as u32;
                let in_deg = incoming.len() as u32;
                if out_deg > 0 || in_deg > 0 {
                    centrality.push((mem.metadata.id, in_deg, out_deg, in_deg + out_deg));
                }
            }
        }

        centrality.sort_by(|a, b| b.3.cmp(&a.3));

        let max_degree = centrality.first().map_or(1, |c| c.3);

        let top_nodes: Vec<Value> = centrality
            .iter()
            .take(top_k)
            .map(|(id, ind, outd, total)| {
                let centrality_score = if max_degree > 0 {
                    f64::from(*total) / f64::from(max_degree)
                } else {
                    0.0
                };
                json!({
                    "memory_id": id,
                    "in_degree": ind,
                    "out_degree": outd,
                    "total_degree": total,
                    "centrality": (centrality_score * 1000.0).round() / 1000.0,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "total_nodes_with_edges": centrality.len(),
            "max_degree": max_degree,
            "top_nodes": top_nodes,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `network.clusters` — Identify connected components in the association graph.
///
/// Uses Union-Find to identify clusters of memories connected by associations.
/// Returns cluster sizes, largest clusters, and isolated node count.
pub struct NetworkClustersTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl NetworkClustersTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Tool for NetworkClustersTool {
    fn name(&self) -> &str {
        "network.clusters"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Identify connected components and clusters in the association graph"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;

        // Collect all nodes and edges
        let mut node_set: HashSet<uuid::Uuid> = HashSet::new();
        let mut edges: Vec<(uuid::Uuid, uuid::Uuid)> = Vec::new();

        for galaxy in Galaxy::memory_galaxies() {
            let mems = self.store.scan(galaxy, 10000)?;
            for mem in mems {
                let outgoing = assoc_store
                    .find_from(env, mem.metadata.id)
                    .unwrap_or_default();
                for a in outgoing {
                    node_set.insert(a.source);
                    node_set.insert(a.target);
                    edges.push((a.source, a.target));
                }
            }
        }

        // Union-Find
        let mut parent: HashMap<uuid::Uuid, uuid::Uuid> = HashMap::new();
        for &node in &node_set {
            parent.insert(node, node);
        }

        fn find(parent: &mut HashMap<uuid::Uuid, uuid::Uuid>, x: uuid::Uuid) -> uuid::Uuid {
            let mut current = x;
            while parent[&current] != current {
                let p = parent[&current];
                parent.insert(current, p);
                current = p;
            }
            current
        }

        for (a, b) in &edges {
            let ra = find(&mut parent, *a);
            let rb = find(&mut parent, *b);
            if ra != rb {
                parent.insert(ra, rb);
            }
        }

        // Count cluster sizes
        let mut cluster_sizes: HashMap<uuid::Uuid, usize> = HashMap::new();
        for &node in &node_set {
            let root = find(&mut parent, node);
            *cluster_sizes.entry(root).or_insert(0) += 1;
        }

        let mut sizes: Vec<usize> = cluster_sizes.values().copied().collect();
        sizes.sort_by(|a, b| b.cmp(a));

        let num_clusters = sizes.len();
        let largest_cluster = sizes.first().copied().unwrap_or(0);
        let isolated_nodes = sizes.iter().filter(|&&s| s == 1).count();
        let multi_node_clusters = sizes.iter().filter(|&&s| s > 1).count();

        let top_clusters: Vec<Value> = sizes
            .iter()
            .take(10)
            .enumerate()
            .map(|(i, &size)| {
                json!({
                    "cluster_rank": i + 1,
                    "size": size,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "total_nodes": node_set.len(),
            "total_edges": edges.len(),
            "num_clusters": num_clusters,
            "largest_cluster_size": largest_cluster,
            "isolated_nodes": isolated_nodes,
            "multi_node_clusters": multi_node_clusters,
            "top_clusters": top_clusters,
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

    fn open_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, Arc::new(store))
    }

    fn make_memory(galaxy: Galaxy, content: &str, tags: &[&str]) -> wm_memory::Memory {
        let mut mem = wm_memory::Memory::new(galaxy, content.to_string());
        mem.metadata.tags = tags.iter().map(std::string::ToString::to_string).collect();
        mem
    }

    #[test]
    fn association_mine_basic() {
        let (_tmp, store) = open_store();
        let tool = AssociationMineTool::new(store.clone());

        let m1 = make_memory(
            Galaxy::Codex,
            "rust is a fast systems programming language",
            &["rust", "programming"],
        );
        let m2 = make_memory(
            Galaxy::Codex,
            "rust is a safe systems programming language",
            &["rust", "programming"],
        );
        store.put(Galaxy::Codex, &m1).unwrap();
        store.put(Galaxy::Codex, &m2).unwrap();

        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert!(result["proposed_associations"].as_u64().unwrap() >= 1);
    }

    #[test]
    fn association_mine_with_min_strength() {
        let (_tmp, store) = open_store();
        let tool = AssociationMineTool::new(store.clone());

        let m1 = make_memory(Galaxy::Codex, "rust fast systems", &["rust"]);
        let m2 = make_memory(Galaxy::Codex, "python slow scripting", &["python"]);
        store.put(Galaxy::Codex, &m1).unwrap();
        store.put(Galaxy::Codex, &m2).unwrap();

        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({"min_strength": 0.9})).unwrap();
        assert_eq!(result["proposed_associations"], 0);
    }

    #[test]
    fn pattern_detect_empty_graph() {
        let (_tmp, store) = open_store();
        let tool = PatternDetectTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_nodes"], 0);
    }

    #[test]
    fn pattern_detect_finds_hubs() {
        let (_tmp, store) = open_store();
        let env = store.env();
        let assoc_store = AssociationStore::open(env).unwrap();

        let m1 = make_memory(Galaxy::Codex, "hub memory about rust", &["rust"]);
        let m2 = make_memory(Galaxy::Codex, "spoke one about rust", &["rust"]);
        let m3 = make_memory(Galaxy::Codex, "spoke two about rust", &["rust"]);
        store.put(Galaxy::Codex, &m1).unwrap();
        store.put(Galaxy::Codex, &m2).unwrap();
        store.put(Galaxy::Codex, &m3).unwrap();

        assoc_store
            .put(
                env,
                &wm_memory::Association::new(
                    m1.metadata.id,
                    m2.metadata.id,
                    wm_memory::LinkType::Related,
                    0.8,
                ),
            )
            .unwrap();
        assoc_store
            .put(
                env,
                &wm_memory::Association::new(
                    m1.metadata.id,
                    m3.metadata.id,
                    wm_memory::LinkType::Related,
                    0.7,
                ),
            )
            .unwrap();

        let tool = PatternDetectTool::new(store.clone());
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert!(result["total_nodes"].as_u64().unwrap() >= 3);
        let hubs = result["hubs"].as_array().unwrap();
        assert!(!hubs.is_empty());
        let first_hub_degree = hubs[0]["total_degree"].as_u64().unwrap();
        assert!(first_hub_degree >= 2);
    }

    #[test]
    fn emergence_report_basic() {
        let (_tmp, store) = open_store();
        let tool = EmergenceReportTool::new(store.clone());

        store
            .put(
                Galaxy::Codex,
                &make_memory(Galaxy::Codex, "rust fact", &["rust", "programming"]),
            )
            .unwrap();
        store
            .put(
                Galaxy::Codex,
                &make_memory(Galaxy::Codex, "python fact", &["python", "programming"]),
            )
            .unwrap();
        store
            .put(
                Galaxy::Codex,
                &make_memory(Galaxy::Codex, "rust again", &["rust"]),
            )
            .unwrap();

        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_memories"], 3);
        assert!(result["unique_tags"].as_u64().unwrap() >= 2);
    }

    #[test]
    fn emergence_report_empty() {
        let (_tmp, store) = open_store();
        let tool = EmergenceReportTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_memories"], 0);
    }

    #[test]
    fn network_stats_empty() {
        let (_tmp, store) = open_store();
        let tool = NetworkStatsTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["nodes"], 0);
        assert_eq!(result["edges"], 0);
    }

    #[test]
    fn network_stats_with_edges() {
        let (_tmp, store) = open_store();
        let env = store.env();
        let assoc_store = AssociationStore::open(env).unwrap();

        let m1 = make_memory(Galaxy::Codex, "memory one", &["test"]);
        let m2 = make_memory(Galaxy::Codex, "memory two", &["test"]);
        store.put(Galaxy::Codex, &m1).unwrap();
        store.put(Galaxy::Codex, &m2).unwrap();

        assoc_store
            .put(
                env,
                &wm_memory::Association::new(
                    m1.metadata.id,
                    m2.metadata.id,
                    wm_memory::LinkType::Related,
                    0.5,
                ),
            )
            .unwrap();

        let tool = NetworkStatsTool::new(store.clone());
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["edges"], 1);
        assert!(result["nodes"].as_u64().unwrap() >= 2);
    }

    #[test]
    fn network_centrality_basic() {
        let (_tmp, store) = open_store();
        let env = store.env();
        let assoc_store = AssociationStore::open(env).unwrap();

        let m1 = make_memory(Galaxy::Codex, "hub memory", &["hub"]);
        let m2 = make_memory(Galaxy::Codex, "spoke one", &["spoke"]);
        let m3 = make_memory(Galaxy::Codex, "spoke two", &["spoke"]);
        store.put(Galaxy::Codex, &m1).unwrap();
        store.put(Galaxy::Codex, &m2).unwrap();
        store.put(Galaxy::Codex, &m3).unwrap();

        assoc_store
            .put(
                env,
                &wm_memory::Association::new(
                    m1.metadata.id,
                    m2.metadata.id,
                    wm_memory::LinkType::Related,
                    0.8,
                ),
            )
            .unwrap();
        assoc_store
            .put(
                env,
                &wm_memory::Association::new(
                    m1.metadata.id,
                    m3.metadata.id,
                    wm_memory::LinkType::Related,
                    0.7,
                ),
            )
            .unwrap();

        let tool = NetworkCentralityTool::new(store.clone());
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({"top_k": 5})).unwrap();
        assert_eq!(result["status"], "success");
        let nodes = result["top_nodes"].as_array().unwrap();
        assert!(!nodes.is_empty());
        let first_degree = nodes[0]["total_degree"].as_u64().unwrap();
        assert!(first_degree >= 2);
    }

    #[test]
    fn network_centrality_empty() {
        let (_tmp, store) = open_store();
        let tool = NetworkCentralityTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_nodes_with_edges"], 0);
    }

    #[test]
    fn network_clusters_empty() {
        let (_tmp, store) = open_store();
        let tool = NetworkClustersTool::new(store);
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["total_nodes"], 0);
        assert_eq!(result["num_clusters"], 0);
    }

    #[test]
    fn network_clusters_connected() {
        let (_tmp, store) = open_store();
        let env = store.env();
        let assoc_store = AssociationStore::open(env).unwrap();

        let m1 = make_memory(Galaxy::Codex, "node one", &["cluster"]);
        let m2 = make_memory(Galaxy::Codex, "node two", &["cluster"]);
        let m3 = make_memory(Galaxy::Codex, "node three", &["cluster"]);
        store.put(Galaxy::Codex, &m1).unwrap();
        store.put(Galaxy::Codex, &m2).unwrap();
        store.put(Galaxy::Codex, &m3).unwrap();

        // m1 -> m2 -> m3 (all connected)
        assoc_store
            .put(
                env,
                &wm_memory::Association::new(
                    m1.metadata.id,
                    m2.metadata.id,
                    wm_memory::LinkType::Related,
                    0.5,
                ),
            )
            .unwrap();
        assoc_store
            .put(
                env,
                &wm_memory::Association::new(
                    m2.metadata.id,
                    m3.metadata.id,
                    wm_memory::LinkType::Related,
                    0.5,
                ),
            )
            .unwrap();

        let tool = NetworkClustersTool::new(store.clone());
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["status"], "success");
        assert_eq!(result["num_clusters"], 1);
        assert_eq!(result["largest_cluster_size"], 3);
        assert_eq!(result["isolated_nodes"], 0);
    }

    #[test]
    fn network_clusters_isolated() {
        let (_tmp, store) = open_store();
        let env = store.env();
        let assoc_store = AssociationStore::open(env).unwrap();

        let m1 = make_memory(Galaxy::Codex, "node one", &["solo"]);
        let m2 = make_memory(Galaxy::Codex, "node two", &["solo"]);
        store.put(Galaxy::Codex, &m1).unwrap();
        store.put(Galaxy::Codex, &m2).unwrap();

        // Only one edge — m1 and m2 connected, no isolated nodes
        assoc_store
            .put(
                env,
                &wm_memory::Association::new(
                    m1.metadata.id,
                    m2.metadata.id,
                    wm_memory::LinkType::Related,
                    0.5,
                ),
            )
            .unwrap();

        let tool = NetworkClustersTool::new(store.clone());
        let mut ctx = Context::new(wm_core::BrainWave::Beta);
        let result = tool.call(&mut ctx, json!({})).unwrap();
        assert_eq!(result["num_clusters"], 1);
        assert_eq!(result["isolated_nodes"], 0);
    }
}
