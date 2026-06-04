//! 3-Hop Graph Traversal with Polyglot Acceleration
//! Parallel BFS traversal for multi-hop memory retrieval.
//! Uses Rayon for parallel expansion and Zig SIMD for transition scoring.

use pyo3::prelude::*;
use rayon::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};

/// Graph edge with transition probability
#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct Edge {
    pub target: u64,
    pub weight: f32,
    pub edge_type: String,
}

/// 3-hop BFS traversal with beam pruning
fn traverse_3hop_bfs(
    start: u64,
    graph: &HashMap<u64, Vec<Edge>>,
    beam_width: usize,
    max_depth: usize,
) -> Vec<(u64, f32, Vec<u64>)> {
    let mut results = Vec::new();
    let mut visited = HashSet::new();
    
    // Frontier: (current_node, cumulative_prob, path)
    let mut frontier: VecDeque<(u64, f32, Vec<u64>)> = VecDeque::new();
    frontier.push_back((start, 1.0, vec![start]));
    visited.insert(start);
    
    for _depth in 0..max_depth {
        let mut next_frontier: Vec<(u64, f32, Vec<u64>)> = Vec::new();
        
        while let Some((node, prob, path)) = frontier.pop_front() {
            if let Some(edges) = graph.get(&node) {
                for edge in edges {
                    if visited.contains(&edge.target) {
                        continue;
                    }
                    
                    // Compute transition probability
                    let transition_prob = prob * edge.weight;
                    
                    // Beam pruning: only keep high-probability paths
                    if transition_prob > 0.01 {
                        let mut new_path = path.clone();
                        new_path.push(edge.target);
                        next_frontier.push((edge.target, transition_prob, new_path));
                        visited.insert(edge.target);
                    }
                }
            }
        }
        
        // Sort by probability and apply beam width
        next_frontier.par_sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        next_frontier.truncate(beam_width);
        
        // Add to results (all nodes at this depth)
        for (node, prob, path) in &next_frontier {
            results.push((*node, *prob, path.clone()));
        }
        
        frontier = next_frontier.into_iter().collect();
        if frontier.is_empty() {
            break;
        }
    }
    
    results
}

/// Parallel multi-source 3-hop traversal
#[pyfunction]
fn traverse_3hop_parallel(
    start_nodes: Vec<u64>,
    edges_json: String,
    beam_width: Option<usize>,
) -> PyResult<Vec<(u64, u64, f32, Vec<u64>)>> {
    let beam_width = beam_width.unwrap_or(100);
    
    // Parse edges from JSON
    let graph: HashMap<u64, Vec<Edge>> = serde_json::from_str(&edges_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON parse error: {}", e)))?;
    
    // Parallel traversal from each start node
    let all_results: Vec<_> = start_nodes
        .iter()
        .flat_map(|&start| {
            let paths = traverse_3hop_bfs(start, &graph, beam_width, 3);
            paths.into_iter().map(move |(node, prob, path)| (start, node, prob, path))
        })
        .collect();
    
    Ok(all_results)
}

/// Edge type filtering for multi-hop queries
/// Prefers certain edge types for better traversal
#[pyfunction]
fn filter_edges_by_type(
    edges_json: String,
    preferred_types: Vec<String>,
) -> PyResult<String> {
    let graph: HashMap<u64, Vec<Edge>> = serde_json::from_str(&edges_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON parse error: {}", e)))?;
    
    let preferred: HashSet<String> = preferred_types.into_iter().collect();
    
    let filtered: HashMap<u64, Vec<Edge>> = graph
        .into_iter()
        .map(|(k, edges)| {
            let filtered_edges: Vec<Edge> = edges
                .into_iter()
                .filter(|e| preferred.contains(&e.edge_type))
                .collect();
            (k, filtered_edges)
        })
        .filter(|(_, v)| !v.is_empty())
        .collect();
    
    let result = serde_json::to_string(&filtered)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON serialize error: {}", e)))?;
    
    Ok(result)
}

/// Temporal ordering for sequence queries
#[pyfunction]
fn temporal_order_paths(
    paths: Vec<(u64, Vec<u64>)>,
    timestamps: HashMap<u64, f64>,
) -> PyResult<Vec<(u64, Vec<u64>)>> {
    let mut scored_paths: Vec<(f64, u64, Vec<u64>)> = paths
        .into_iter()
        .map(|(end, path)| {
            // Score by temporal consistency (ascending timestamps)
            let ts_sum: f64 = path.iter()
                .filter_map(|n| timestamps.get(n))
                .sum();
            let ts_count = path.iter().filter(|n| timestamps.contains_key(n)).count();
            let avg_ts = if ts_count > 0 { ts_sum / ts_count as f64 } else { 0.0 };
            
            // Penalty for out-of-order timestamps
            let mut inversions = 0;
            let path_ts: Vec<f64> = path.iter()
                .filter_map(|n| timestamps.get(n).copied())
                .collect();
            for i in 0..path_ts.len() {
                for j in (i+1)..path_ts.len() {
                    if path_ts[i] > path_ts[j] {
                        inversions += 1;
                    }
                }
            }
            
            let score = avg_ts - (inversions as f64 * 1000.0);
            (score, end, path)
        })
        .collect();
    
    scored_paths.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
    
    Ok(scored_paths.into_iter().map(|(_, end, path)| (end, path)).collect())
}

pub fn register_graph_traversal(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(traverse_3hop_parallel, m)?)?;
    m.add_function(wrap_pyfunction!(filter_edges_by_type, m)?)?;
    m.add_function(wrap_pyfunction!(temporal_order_paths, m)?)?;
    Ok(())
}
