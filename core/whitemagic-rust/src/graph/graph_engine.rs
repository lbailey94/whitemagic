//! Graph Engine - Core Graph Operations (PSR-003, S026 VC2)
//! Target: 30× speedup for graph operations
//!
//! Hot paths for graph topology analysis:
//! - Bridging centrality calculation
//! - Echo chamber z-score analysis
//! - Community internal edge counting

use pyo3::prelude::*;
use rayon::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};

#[derive(Clone, Debug)]
#[pyclass]
pub struct GraphEdge {
    #[pyo3(get)]
    pub source: String,
    #[pyo3(get)]
    pub target: String,
    #[pyo3(get)]
    pub weight: f64,
    #[pyo3(get)]
    pub edge_type: String,
}

#[pymethods]
impl GraphEdge {
    #[new]
    fn new(source: String, target: String, weight: f64, edge_type: String) -> Self {
        Self {
            source,
            target,
            weight,
            edge_type,
        }
    }
}

#[pyclass]
pub struct PyGraphEngine {
    adjacency: HashMap<String, Vec<GraphEdge>>,
    reverse_adjacency: HashMap<String, Vec<GraphEdge>>,
}

#[pymethods]
impl PyGraphEngine {
    #[new]
    fn new() -> Self {
        Self {
            adjacency: HashMap::new(),
            reverse_adjacency: HashMap::new(),
        }
    }

    fn add_edge(&mut self, edge: GraphEdge) {
        self.adjacency
            .entry(edge.source.clone())
            .or_default()
            .push(edge.clone());

        self.reverse_adjacency
            .entry(edge.target.clone())
            .or_default()
            .push(edge);
    }

    fn get_neighbors(&self, node: String) -> Vec<GraphEdge> {
        self.adjacency.get(&node).cloned().unwrap_or_default()
    }

    fn get_predecessors(&self, node: String) -> Vec<GraphEdge> {
        self.reverse_adjacency
            .get(&node)
            .cloned()
            .unwrap_or_default()
    }

    fn bfs(&self, start: String, max_depth: Option<usize>) -> Vec<String> {
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();
        let mut result = Vec::new();

        queue.push_back((start.clone(), 0));
        visited.insert(start);

        let depth_limit = max_depth.unwrap_or(usize::MAX);

        while let Some((node, depth)) = queue.pop_front() {
            if depth > depth_limit {
                break;
            }

            result.push(node.clone());

            if let Some(edges) = self.adjacency.get(&node) {
                for edge in edges {
                    if !visited.contains(&edge.target) {
                        visited.insert(edge.target.clone());
                        queue.push_back((edge.target.clone(), depth + 1));
                    }
                }
            }
        }

        result
    }

    fn dfs(&self, start: String, max_depth: Option<usize>) -> Vec<String> {
        let mut visited = HashSet::new();
        let mut stack = Vec::new();
        let mut result = Vec::new();

        stack.push((start.clone(), 0));

        let depth_limit = max_depth.unwrap_or(usize::MAX);

        while let Some((node, depth)) = stack.pop() {
            if depth > depth_limit || visited.contains(&node) {
                continue;
            }

            visited.insert(node.clone());
            result.push(node.clone());

            if let Some(edges) = self.adjacency.get(&node) {
                for edge in edges.iter().rev() {
                    if !visited.contains(&edge.target) {
                        stack.push((edge.target.clone(), depth + 1));
                    }
                }
            }
        }

        result
    }

    fn shortest_path(&self, start: String, end: String) -> Option<Vec<String>> {
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();
        let mut parent: HashMap<String, String> = HashMap::new();

        queue.push_back(start.clone());
        visited.insert(start.clone());

        while let Some(node) = queue.pop_front() {
            if node == end {
                let mut path = vec![end.clone()];
                let mut current = end;

                while let Some(p) = parent.get(&current) {
                    path.push(p.clone());
                    current = p.clone();
                }

                path.reverse();
                return Some(path);
            }

            if let Some(edges) = self.adjacency.get(&node) {
                for edge in edges {
                    if !visited.contains(&edge.target) {
                        visited.insert(edge.target.clone());
                        parent.insert(edge.target.clone(), node.clone());
                        queue.push_back(edge.target.clone());
                    }
                }
            }
        }

        None
    }

    fn node_count(&self) -> usize {
        let mut nodes = HashSet::new();
        for node in self.adjacency.keys() {
            nodes.insert(node);
        }
        for node in self.reverse_adjacency.keys() {
            nodes.insert(node);
        }
        nodes.len()
    }

    fn edge_count(&self) -> usize {
        self.adjacency.values().map(|v| v.len()).sum()
    }

    fn degree(&self, node: String) -> usize {
        self.adjacency.get(&node).map(|v| v.len()).unwrap_or(0)
    }

    fn in_degree(&self, node: String) -> usize {
        self.reverse_adjacency
            .get(&node)
            .map(|v| v.len())
            .unwrap_or(0)
    }

    fn get_connected_component(&self, start: String) -> Vec<String> {
        self.bfs(start, None)
    }

    fn parallel_bfs(&self, starts: Vec<String>, max_depth: Option<usize>) -> Vec<Vec<String>> {
        starts
            .par_iter()
            .map(|start| self.bfs(start.clone(), max_depth))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_creation() {
        let engine = PyGraphEngine::new();
        assert_eq!(engine.node_count(), 0);
    }

    #[test]
    fn test_add_edge() {
        let mut engine = PyGraphEngine::new();
        let edge = GraphEdge::new("a".to_string(), "b".to_string(), 1.0, "link".to_string());

        engine.add_edge(edge);
        assert_eq!(engine.edge_count(), 1);
    }

    #[test]
    fn test_bfs() {
        let mut engine = PyGraphEngine::new();
        engine.add_edge(GraphEdge::new(
            "a".to_string(),
            "b".to_string(),
            1.0,
            "link".to_string(),
        ));
        engine.add_edge(GraphEdge::new(
            "b".to_string(),
            "c".to_string(),
            1.0,
            "link".to_string(),
        ));

        let visited = engine.bfs("a".to_string(), None);
        assert!(visited.len() >= 2);
    }

    #[test]
    fn test_shortest_path() {
        let mut engine = PyGraphEngine::new();
        engine.add_edge(GraphEdge::new(
            "a".to_string(),
            "b".to_string(),
            1.0,
            "link".to_string(),
        ));
        engine.add_edge(GraphEdge::new(
            "b".to_string(),
            "c".to_string(),
            1.0,
            "link".to_string(),
        ));

        let path = engine.shortest_path("a".to_string(), "c".to_string());
        assert!(path.is_some());
        assert_eq!(path.unwrap().len(), 3);
    }

    #[test]
    fn test_degree() {
        let mut engine = PyGraphEngine::new();
        engine.add_edge(GraphEdge::new(
            "a".to_string(),
            "b".to_string(),
            1.0,
            "link".to_string(),
        ));
        engine.add_edge(GraphEdge::new(
            "a".to_string(),
            "c".to_string(),
            1.0,
            "link".to_string(),
        ));

        assert_eq!(engine.degree("a".to_string()), 2);
        assert_eq!(engine.in_degree("b".to_string()), 1);
    }
}

// ---------------------------------------------------------------------------
// S026 VC2: Additional hot path functions
// ---------------------------------------------------------------------------

/// Calculate bridging centrality for nodes
///
/// bridging_centrality(v) = betweenness(v) * bridging_coefficient(v)
/// where bridging_coefficient(v) = 1/degree(v) / Σ(1/degree(u)) for u ∈ N(v)
#[pyfunction]
pub fn py_bridging_centrality(
    betweenness: HashMap<String, f64>,
    adjacencies: HashMap<String, Vec<String>>,
    top_n: usize,
) -> Vec<(String, f64, f64, f64, usize)> {
    let mut results: Vec<(String, f64, f64, f64, usize)> = Vec::new();

    for (node_id, bc) in &betweenness {
        // Get neighbors from adjacency list
        let neighbors = match adjacencies.get(node_id) {
            Some(n) => n,
            None => continue,
        };

        let degree = neighbors.len();
        if degree < 2 {
            continue;
        }

        // Calculate bridging coefficient
        let inv_degree = 1.0 / degree as f64;
        let sum_inv: f64 = neighbors
            .iter()
            .map(|neighbor| {
                let neighbor_degree = adjacencies.get(neighbor).map(|n| n.len()).unwrap_or(1);
                1.0 / neighbor_degree.max(1) as f64
            })
            .sum();

        if sum_inv <= 0.0 {
            continue;
        }

        let bridging_coeff = inv_degree / sum_inv;
        let bridging_score = bc * bridging_coeff;

        results.push((node_id.clone(), bridging_score, *bc, bridging_coeff, degree));
    }

    // Sort by bridging centrality descending
    results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    results.truncate(top_n);
    results
}

/// Calculate echo chamber z-scores for centrality deltas
///
/// Returns nodes with z-score above threshold that have no new data
#[pyfunction]
pub fn py_detect_echo_chambers(
    prev_centrality: HashMap<String, f64>,
    curr_centrality: HashMap<String, f64>,
    nodes_with_new_edges: HashSet<String>,
    sigma_threshold: f64,
) -> Vec<(String, f64, f64, f64, bool)> {
    // Find common nodes
    let common_nodes: Vec<&String> = prev_centrality
        .keys()
        .filter(|k| curr_centrality.contains_key(*k))
        .collect();

    if common_nodes.len() < 10 {
        return Vec::new();
    }

    // Compute deltas
    let deltas: Vec<f64> = common_nodes
        .iter()
        .map(|n| curr_centrality[*n] - prev_centrality[*n])
        .collect();

    // Mean and std
    let n = deltas.len() as f64;
    let mean_delta: f64 = deltas.iter().sum::<f64>() / n;
    let variance: f64 = deltas.iter().map(|d| (d - mean_delta).powi(2)).sum::<f64>() / n;
    let std_delta = variance.sqrt();

    if std_delta < 1e-10 {
        return Vec::new();
    }

    // Find spikes
    let mut echo_chambers: Vec<(String, f64, f64, f64, bool)> = Vec::new();

    for node_id in common_nodes {
        let delta = curr_centrality[node_id] - prev_centrality[node_id];
        let z_score = (delta - mean_delta) / std_delta;

        if z_score > sigma_threshold {
            let has_new_data = nodes_with_new_edges.contains(node_id);
            if !has_new_data {
                echo_chambers.push((
                    node_id.clone(),
                    curr_centrality[node_id],
                    prev_centrality[node_id],
                    z_score,
                    false,
                ));
            }
        }
    }

    // Sort by z-score descending
    echo_chambers.sort_by(|a, b| b.3.partial_cmp(&a.3).unwrap_or(std::cmp::Ordering::Equal));
    echo_chambers
}

/// Count internal edges for communities
///
/// For each community, count edges between members and compute average strength
#[pyfunction]
pub fn py_count_community_edges(
    adjacencies: HashMap<String, Vec<String>>,
    edge_weights: HashMap<(String, String), f64>,
    communities: Vec<Vec<String>>,
) -> Vec<(usize, usize, f64)> {
    let mut results: Vec<(usize, usize, f64)> = Vec::new();

    for members in communities {
        if members.len() < 2 {
            continue;
        }

        let member_set: HashSet<&String> = members.iter().collect();
        let mut internal_edges = 0usize;
        let mut total_strength = 0.0f64;

        for u in &members {
            if let Some(neighbors) = adjacencies.get(u) {
                for v in neighbors {
                    if member_set.contains(v) {
                        internal_edges += 1;
                        // Look up edge weight (try both directions for undirected)
                        let weight = edge_weights
                            .get(&(u.clone(), v.clone()))
                            .or_else(|| edge_weights.get(&(v.clone(), u.clone())))
                            .copied()
                            .unwrap_or(0.5);
                        total_strength += weight;
                    }
                }
            }
        }

        // Undirected: each edge counted twice
        internal_edges /= 2;
        let avg_strength = if internal_edges > 0 {
            total_strength / (internal_edges * 2) as f64
        } else {
            0.0
        };

        results.push((members.len(), internal_edges, avg_strength));
    }

    results
}

/// Batch distance calculation for graph nodes (for similarity-based edge weighting)
#[pyfunction]
pub fn py_batch_node_distances(
    node_embeddings: HashMap<String, Vec<f32>>,
    query_node: String,
    limit: usize,
) -> Vec<(String, f64)> {
    let query_emb = match node_embeddings.get(&query_node) {
        Some(e) => e,
        None => return Vec::new(),
    };

    let mut distances: Vec<(String, f64)> = node_embeddings
        .iter()
        .filter(|(id, _)| *id != &query_node)
        .map(|(id, emb)| {
            // Cosine similarity
            let dot: f32 = query_emb.iter().zip(emb.iter()).map(|(a, b)| a * b).sum();
            let norm_q: f32 = query_emb.iter().map(|x| x * x).sum::<f32>().sqrt();
            let norm_e: f32 = emb.iter().map(|x| x * x).sum::<f32>().sqrt();
            let similarity = if norm_q > 0.0 && norm_e > 0.0 {
                dot as f64 / (norm_q as f64 * norm_e as f64)
            } else {
                0.0
            };
            (id.clone(), similarity)
        })
        .collect();

    distances.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    distances.truncate(limit);
    distances
}

// ---------------------------------------------------------------------------
// Python module registration
// ---------------------------------------------------------------------------

#[cfg(feature = "python")]
pub fn graph_engine(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<GraphEdge>()?;
    m.add_class::<PyGraphEngine>()?;
    m.add_function(wrap_pyfunction!(py_bridging_centrality, m)?)?;
    m.add_function(wrap_pyfunction!(py_detect_echo_chambers, m)?)?;
    m.add_function(wrap_pyfunction!(py_count_community_edges, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_node_distances, m)?)?;
    Ok(())
}
