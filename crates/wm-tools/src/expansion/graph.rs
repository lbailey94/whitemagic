//! Living graph tools — graph.walk, graph.community, graph.propagate.
//!
//! These tools operate on the association graph, providing traversal,
//! community detection, and activation propagation capabilities.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::collections::{HashMap, HashSet, VecDeque};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_memory::{AssociationStore, MemoryStore};

/// `graph.walk` — BFS traversal from a starting memory through associations.
///
/// Starting from a memory UUID, walks the association graph breadth-first
/// up to a configurable depth. Returns the visited nodes and edges.
pub struct GraphWalkTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GraphWalkTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![
                Resource::Galaxy("associations".into()),
                Resource::Galaxy("codex".into()),
            ]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for GraphWalkTool {
    fn name(&self) -> &str {
        "graph.walk"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "BFS traversal through the association graph from a starting memory"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let start_id = args
            .get("start_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("Missing 'start_id' (UUID) parameter".into())
            })?;
        let start_uuid = uuid::Uuid::parse_str(start_id).map_err(|e| {
            wm_core::CoreError::InvalidArgs(format!("Invalid UUID '{start_id}': {e}"))
        })?;
        let max_depth = args
            .get("max_depth")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(3) as usize;
        let max_nodes = args
            .get("max_nodes")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(100) as usize;

        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;

        // BFS
        let mut visited: HashSet<uuid::Uuid> = HashSet::new();
        let mut edges: Vec<Value> = Vec::new();
        let mut queue: VecDeque<(uuid::Uuid, usize)> = VecDeque::new();
        queue.push_back((start_uuid, 0));
        visited.insert(start_uuid);

        while let Some((current, depth)) = queue.pop_front() {
            if depth >= max_depth || visited.len() >= max_nodes {
                break;
            }

            // Get outgoing edges
            let outgoing = assoc_store.find_from(env, current).unwrap_or_default();
            // Get incoming edges
            let incoming = assoc_store.find_to(env, current).unwrap_or_default();

            for assoc in outgoing {
                edges.push(json!({
                    "source": assoc.source,
                    "target": assoc.target,
                    "link_type": assoc.link_type.as_str(),
                    "weight": assoc.weight,
                    "depth": depth + 1,
                }));
                if visited.insert(assoc.target) {
                    queue.push_back((assoc.target, depth + 1));
                }
            }

            for assoc in incoming {
                edges.push(json!({
                    "source": assoc.source,
                    "target": assoc.target,
                    "link_type": assoc.link_type.as_str(),
                    "weight": assoc.weight,
                    "depth": depth + 1,
                }));
                if visited.insert(assoc.source) {
                    queue.push_back((assoc.source, depth + 1));
                }
            }
        }

        // Fetch memory content for visited nodes
        let nodes: Vec<Value> = visited
            .iter()
            .take(max_nodes)
            .filter_map(|&id| {
                // Try each galaxy to find the memory
                for galaxy in wm_core::Galaxy::memory_galaxies() {
                    if let Ok(Some(mem)) = self.store.get(galaxy, id) {
                        return Some(json!({
                            "id": mem.metadata.id,
                            "content_preview": mem.content.chars().take(200).collect::<String>(),
                            "tags": mem.metadata.tags,
                        }));
                    }
                }
                None
            })
            .collect();

        Ok(json!({
            "status": "success",
            "start_id": start_uuid,
            "max_depth": max_depth,
            "nodes_visited": visited.len(),
            "edges_traversed": edges.len(),
            "nodes": nodes,
            "edges": edges,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `graph.community` — detect communities using label propagation.
///
/// Runs label propagation on the association graph to detect clusters
/// of tightly connected memories. Each node adopts the label shared by
/// the majority of its neighbors. Iterates until convergence or max rounds.
pub struct GraphCommunityTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GraphCommunityTool {
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
impl Tool for GraphCommunityTool {
    fn name(&self) -> &str {
        "graph.community"
    }
    fn gana(&self) -> Gana {
        Gana::HairyHead
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Detect communities in the association graph using label propagation"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let max_rounds = args
            .get("max_rounds")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;
        let min_community_size = args
            .get("min_size")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(2) as usize;

        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;

        // Build adjacency list from all associations
        // We need to scan all associations — use find_from for each known node.
        // Since we don't have a "scan all" method, we'll scan all galaxies for
        // memory IDs and build the graph from there.
        let mut adjacency: HashMap<uuid::Uuid, Vec<uuid::Uuid>> = HashMap::new();
        let mut all_nodes: HashSet<uuid::Uuid> = HashSet::new();

        for galaxy in wm_core::Galaxy::memory_galaxies() {
            let memories = self.store.scan(galaxy, 1000)?;
            for mem in &memories {
                let from = assoc_store
                    .find_from(env, mem.metadata.id)
                    .unwrap_or_default();
                for assoc in &from {
                    adjacency
                        .entry(assoc.source)
                        .or_default()
                        .push(assoc.target);
                    adjacency
                        .entry(assoc.target)
                        .or_default()
                        .push(assoc.source);
                    all_nodes.insert(assoc.source);
                    all_nodes.insert(assoc.target);
                }
            }
        }

        if all_nodes.is_empty() {
            return Ok(json!({
                "status": "success",
                "total_nodes": 0,
                "communities": [],
                "rounds": 0,
            }));
        }

        // Initialize: each node has its own label
        let nodes: Vec<uuid::Uuid> = all_nodes.iter().copied().collect();
        let mut labels: HashMap<uuid::Uuid, usize> =
            nodes.iter().enumerate().map(|(i, &n)| (n, i)).collect();

        // Label propagation
        let mut rounds = 0;
        let mut changed = true;
        while changed && rounds < max_rounds {
            changed = false;
            rounds += 1;

            for &node in &nodes {
                let neighbors = adjacency.get(&node);
                if neighbors.is_none_or(std::vec::Vec::is_empty) {
                    continue;
                }

                // Count neighbor labels
                let mut label_counts: HashMap<usize, u32> = HashMap::new();
                for &neighbor in neighbors.unwrap() {
                    if let Some(&label) = labels.get(&neighbor) {
                        *label_counts.entry(label).or_default() += 1;
                    }
                }

                // Find majority label
                if let Some((&best_label, _)) = label_counts.iter().max_by_key(|&(_, &count)| count)
                {
                    if labels[&node] != best_label {
                        labels.insert(node, best_label);
                        changed = true;
                    }
                }
            }
        }

        // Group nodes by community
        let mut communities: HashMap<usize, Vec<uuid::Uuid>> = HashMap::new();
        for (&node, &label) in &labels {
            communities.entry(label).or_default().push(node);
        }

        // Filter by min size and sort by size descending
        let mut filtered: Vec<(usize, Vec<uuid::Uuid>)> = communities
            .into_iter()
            .filter(|(_, members)| members.len() >= min_community_size)
            .collect();
        filtered.sort_by_key(|entry| std::cmp::Reverse(entry.1.len()));

        let community_json: Vec<Value> = filtered
            .iter()
            .enumerate()
            .map(|(idx, (_, members))| {
                json!({
                    "community_id": idx,
                    "size": members.len(),
                    "member_ids": members.iter().take(20).map(std::string::ToString::to_string).collect::<Vec<_>>(),
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "total_nodes": all_nodes.len(),
            "total_edges": adjacency.values().map(std::vec::Vec::len).sum::<usize>() / 2,
            "rounds": rounds,
            "communities": community_json,
            "community_count": filtered.len(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `graph.propagate` — spread activation through the association graph.
///
/// Starting from a seed memory, propagates activation energy through
/// associated memories. Each hop decays the activation by a factor.
/// Returns the ranked list of activated memories.
pub struct GraphPropagateTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl GraphPropagateTool {
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
impl Tool for GraphPropagateTool {
    fn name(&self) -> &str {
        "graph.propagate"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Spread activation through the association graph from seed memories"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let seed_ids = args
            .get("seed_ids")
            .and_then(|v| v.as_array())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("Missing 'seed_ids' array parameter".into())
            })?;
        let max_hops = args
            .get("max_hops")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(3) as usize;
        let decay = args
            .get("decay")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.5) as f32;
        let min_activation = args
            .get("min_activation")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.05) as f32;

        // Parse seed UUIDs
        let mut seeds: Vec<(uuid::Uuid, f32)> = Vec::new();
        for seed in seed_ids {
            if let Some(id_str) = seed.as_str() {
                if let Ok(uuid) = uuid::Uuid::parse_str(id_str) {
                    seeds.push((uuid, 1.0));
                }
            }
        }
        if seeds.is_empty() {
            return Err(wm_core::CoreError::InvalidArgs(
                "No valid seed UUIDs provided".into(),
            ));
        }

        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;

        // Activation spreading (BFS with decay)
        let mut activation: HashMap<uuid::Uuid, f32> = HashMap::new();
        let mut visited: HashSet<uuid::Uuid> = HashSet::new();

        // Initialize seeds
        for (seed_id, initial_activation) in &seeds {
            activation.insert(*seed_id, *initial_activation);
        }

        let mut current_front: Vec<(uuid::Uuid, f32)> = seeds.clone();

        for hop in 0..max_hops {
            if current_front.is_empty() {
                break;
            }
            let mut next_front: Vec<(uuid::Uuid, f32)> = Vec::new();

            for (node, node_activation) in &current_front {
                if visited.contains(node) {
                    continue;
                }
                visited.insert(*node);

                // Get neighbors
                let outgoing = assoc_store.find_from(env, *node).unwrap_or_default();
                let incoming = assoc_store.find_to(env, *node).unwrap_or_default();

                let mut propagate = |neighbor_id: uuid::Uuid, weight: f32| {
                    if !visited.contains(&neighbor_id) {
                        let propagated = node_activation * weight * decay;
                        if propagated >= min_activation {
                            let entry = activation.entry(neighbor_id).or_insert(0.0);
                            // Take max activation (not sum, to avoid overflow)
                            if propagated > *entry {
                                *entry = propagated;
                            }
                            next_front.push((neighbor_id, propagated));
                        }
                    }
                };

                for assoc in &outgoing {
                    propagate(assoc.target, assoc.weight);
                }
                for assoc in &incoming {
                    propagate(assoc.source, assoc.weight);
                }
            }

            current_front = next_front;
            let _ = hop; // suppress unused warning
        }

        // Rank by activation (descending)
        let mut ranked: Vec<(uuid::Uuid, f32)> = activation
            .into_iter()
            .filter(|(_, a)| *a >= min_activation)
            .collect();
        ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        // Fetch memory content for top results
        let results: Vec<Value> = ranked
            .iter()
            .take(50)
            .map(|(id, activation)| {
                let content_preview = {
                    let mut found = None;
                    for galaxy in wm_core::Galaxy::memory_galaxies() {
                        if let Ok(Some(mem)) = self.store.get(galaxy, *id) {
                            found = Some(mem.content.chars().take(200).collect::<String>());
                            break;
                        }
                    }
                    found.unwrap_or_default()
                };
                json!({
                    "id": id,
                    "activation": (f64::from(*activation) * 10000.0).round() / 10000.0,
                    "content_preview": content_preview,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "seeds": seeds.len(),
            "max_hops": max_hops,
            "decay": decay,
            "activated_nodes": ranked.len(),
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
    use wm_memory::{Association, LinkType, Memory};

    fn open_store() -> (tempfile::TempDir, MemoryStore) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, store)
    }

    fn setup_graph(store: &MemoryStore) -> Vec<uuid::Uuid> {
        let env = store.env();
        let assoc_store = AssociationStore::open(env).unwrap();
        let galaxy = wm_core::Galaxy::Codex;

        // Create 5 memories: A -> B -> C -> D, A -> E
        let mut ids = Vec::new();
        for i in 0..5 {
            let mem = Memory::new(galaxy, format!("Memory {i}"));
            store.put(galaxy, &mem).unwrap();
            ids.push(mem.metadata.id);
        }

        // Create associations: A->B, B->C, C->D, A->E
        assoc_store
            .put(
                env,
                &Association::new(ids[0], ids[1], LinkType::Related, 0.8),
            )
            .unwrap();
        assoc_store
            .put(
                env,
                &Association::new(ids[1], ids[2], LinkType::Related, 0.7),
            )
            .unwrap();
        assoc_store
            .put(
                env,
                &Association::new(ids[2], ids[3], LinkType::Related, 0.6),
            )
            .unwrap();
        assoc_store
            .put(
                env,
                &Association::new(ids[0], ids[4], LinkType::Related, 0.5),
            )
            .unwrap();

        ids
    }

    #[tokio::test]
    async fn graph_walk_traverses_bfs() {
        let (_tmp, store) = open_store();
        let ids = setup_graph(&store);

        let tool = GraphWalkTool::new(Arc::new(store));
        let result = tool
            .call(
                &mut Context::default(),
                json!({"start_id": ids[0].to_string(), "max_depth": 3}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["nodes_visited"].as_u64().unwrap() >= 4);
        assert!(obj["edges_traversed"].as_u64().unwrap() >= 4);
    }

    #[tokio::test]
    async fn graph_walk_invalid_uuid_errors() {
        let (_tmp, store) = open_store();
        let tool = GraphWalkTool::new(Arc::new(store));
        let result = tool
            .call(&mut Context::default(), json!({"start_id": "not-a-uuid"}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn graph_walk_missing_start_id_errors() {
        let (_tmp, store) = open_store();
        let tool = GraphWalkTool::new(Arc::new(store));
        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn graph_walk_depth_limit_works() {
        let (_tmp, store) = open_store();
        let ids = setup_graph(&store);

        let tool = GraphWalkTool::new(Arc::new(store));
        let result = tool
            .call(
                &mut Context::default(),
                json!({"start_id": ids[0].to_string(), "max_depth": 1}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        // With depth 1, should visit A, B, E (direct neighbors)
        assert!(obj["nodes_visited"].as_u64().unwrap() >= 3);
        assert!(obj["nodes_visited"].as_u64().unwrap() <= 3);
    }

    #[tokio::test]
    async fn graph_community_detects_clusters() {
        let (_tmp, store) = open_store();
        let _ids = setup_graph(&store);

        let tool = GraphCommunityTool::new(Arc::new(store));
        let result = tool
            .call(
                &mut Context::default(),
                json!({"max_rounds": 20, "min_size": 2}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["total_nodes"], 5);
        // With this small graph, all 5 should converge to one community
        let communities = obj["communities"].as_array().unwrap();
        assert!(!communities.is_empty());
    }

    #[tokio::test]
    async fn graph_community_empty_graph() {
        let (_tmp, store) = open_store();
        let tool = GraphCommunityTool::new(Arc::new(store));
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["total_nodes"], 0);
        assert_eq!(obj["communities"].as_array().unwrap().len(), 0);
    }

    #[tokio::test]
    async fn graph_propagate_spreads_activation() {
        let (_tmp, store) = open_store();
        let ids = setup_graph(&store);

        let tool = GraphPropagateTool::new(Arc::new(store));
        let result = tool
            .call(
                &mut Context::default(),
                json!({
                    "seed_ids": [ids[0].to_string()],
                    "max_hops": 3,
                    "decay": 0.5,
                }),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["activated_nodes"].as_u64().unwrap() >= 4);
        // The seed should have highest activation
        let results = obj["results"].as_array().unwrap();
        assert_eq!(results[0]["id"], ids[0].to_string());
    }

    #[tokio::test]
    async fn graph_propagate_missing_seeds_errors() {
        let (_tmp, store) = open_store();
        let tool = GraphPropagateTool::new(Arc::new(store));
        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn graph_propagate_invalid_seed_errors() {
        let (_tmp, store) = open_store();
        let tool = GraphPropagateTool::new(Arc::new(store));
        let result = tool
            .call(&mut Context::default(), json!({"seed_ids": ["not-a-uuid"]}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn graph_tool_names_are_correct() {
        let store = Arc::new(open_store().1);
        assert_eq!(GraphWalkTool::new(store.clone()).name(), "graph.walk");
        assert_eq!(
            GraphCommunityTool::new(store.clone()).name(),
            "graph.community"
        );
        assert_eq!(GraphPropagateTool::new(store).name(), "graph.propagate");
    }

    #[tokio::test]
    async fn graph_tool_ganas_are_correct() {
        let store = Arc::new(open_store().1);
        assert_eq!(
            GraphWalkTool::new(store.clone()).gana(),
            Gana::WinnowingBasket
        );
        assert_eq!(
            GraphCommunityTool::new(store.clone()).gana(),
            Gana::HairyHead
        );
        assert_eq!(GraphPropagateTool::new(store).gana(), Gana::WinnowingBasket);
    }
}
