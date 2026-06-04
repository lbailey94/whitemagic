//! Graph traversal with semantic projection
//! High-performance graph walking algorithms

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};
use rayon::prelude::*;

type NodeId = String;
type Score = f64;

#[derive(Clone, Debug)]
struct Edge {
    target: NodeId,
    weight: Score,
    #[allow(dead_code)]
    relation_type: String,
}

#[pyclass]
pub struct GraphWalker {
    graph: HashMap<NodeId, Vec<Edge>>,
}

#[pymethods]
impl GraphWalker {
    #[new]
    fn new() -> Self {
        Self {
            graph: HashMap::new(),
        }
    }
    
    /// Add edge to graph
    fn add_edge(
        &mut self,
        source: String,
        target: String,
        weight: f64,
        relation_type: String
    ) {
        self.graph
            .entry(source)
            .or_insert_with(Vec::new)
            .push(Edge {
                target,
                weight,
                relation_type,
            });
    }
    
    /// Walk graph from start node with depth limit
    /// 
    /// Uses breadth-first search with semantic scoring
    fn walk(
        &self,
        start: String,
        max_depth: usize,
        min_score: f64
    ) -> PyResult<Vec<(String, f64)>> {
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();
        let mut results = Vec::new();
        
        queue.push_back((start.clone(), 0, 1.0));
        visited.insert(start);
        
        while let Some((node, depth, score)) = queue.pop_front() {
            if depth >= max_depth || score < min_score {
                continue;
            }
            
            results.push((node.clone(), score));
            
            // Explore neighbors
            if let Some(edges) = self.graph.get(&node) {
                for edge in edges {
                    if !visited.contains(&edge.target) {
                        visited.insert(edge.target.clone());
                        let new_score = score * edge.weight;
                        queue.push_back((
                            edge.target.clone(),
                            depth + 1,
                            new_score
                        ));
                    }
                }
            }
        }
        
        // Sort by score descending
        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        
        Ok(results)
    }
    
    /// Parallel multi-start walk
    fn parallel_walk(
        &self,
        starts: Vec<String>,
        max_depth: usize,
        min_score: f64
    ) -> PyResult<Vec<Vec<(String, f64)>>> {
        let results: Vec<Vec<(String, f64)>> = starts
            .par_iter()
            .map(|start| {
                self.walk(start.clone(), max_depth, min_score)
                    .unwrap_or_default()
            })
            .collect();
        
        Ok(results)
    }
    
    /// Get graph statistics
    fn get_stats(&self) -> PyResult<(usize, usize)> {
        let node_count = self.graph.len();
        let edge_count: usize = self.graph.values().map(|v| v.len()).sum();
        
        Ok((node_count, edge_count))
    }
}
