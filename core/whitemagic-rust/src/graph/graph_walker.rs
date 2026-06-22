//! Graph traversal engine for memory graph walking
//!
//! This module provides graph traversal algorithms for exploring
//! memory associations and knowledge graphs.

#![allow(dead_code)]

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};

/// Edge in the memory graph
#[derive(Debug, Clone)]
pub struct GraphEdge {
    /// Source node ID
    pub source: u64,
    /// Target node ID
    pub target: u64,
    /// Edge weight/strength
    pub weight: f32,
    /// Edge type (e.g., "semantic", "causal", "temporal")
    pub edge_type: String,
}

/// Node in the memory graph
#[derive(Debug, Clone)]
pub struct GraphNode {
    /// Node ID
    pub id: u64,
    /// Node embedding (for similarity calculations)
    pub embedding: Vec<f32>,
    /// Node metadata
    pub metadata: HashMap<String, String>,
}

/// Result of a graph traversal
#[derive(Debug, Clone)]
pub struct TraversalResult {
    /// Visited node IDs in order
    pub path: Vec<u64>,
    /// Total traversal score
    pub score: f32,
    /// Number of edges traversed
    pub edges_traversed: usize,
}

#[pyclass]
pub struct GraphWalker {
    /// Maximum traversal depth
    max_depth: usize,
    /// Minimum edge weight to follow
    min_weight: f32,
    /// Whether to avoid revisiting nodes
    avoid_cycles: bool,
    /// BFS queue for breadth-first traversal
    queue: VecDeque<u64>,
    /// Visited nodes
    visited: HashSet<u64>,
}

#[pymethods]
impl GraphWalker {
    /// Create a new graph walker with specified max depth
    #[new]
    fn new(max_depth: usize) -> Self {
        Self {
            max_depth,
            min_weight: 0.0,
            avoid_cycles: true,
            queue: VecDeque::new(),
            visited: HashSet::new(),
        }
    }

    /// Create walker with custom settings
    #[staticmethod]
    fn with_settings(max_depth: usize, min_weight: f32, avoid_cycles: bool) -> Self {
        Self {
            max_depth,
            min_weight,
            avoid_cycles,
            queue: VecDeque::new(),
            visited: HashSet::new(),
        }
    }

    /// Get max depth
    fn get_max_depth(&self) -> usize {
        self.max_depth
    }

    /// Set minimum edge weight threshold
    fn set_min_weight(&mut self, weight: f32) {
        self.min_weight = weight;
    }

    /// Get min weight
    fn get_min_weight(&self) -> f32 {
        self.min_weight
    }

    /// Breadth-first traversal from a starting node
    /// Returns list of visited node IDs
    fn traverse_bfs(
        &mut self,
        start_node: u64,
        edges: Vec<(u64, u64, f32)>, // (source, target, weight)
    ) -> Vec<u64> {
        self.reset();
        let mut result = Vec::new();

        // Build adjacency list
        let mut adj: HashMap<u64, Vec<(u64, f32)>> = HashMap::new();
        for (source, target, weight) in edges {
            if weight >= self.min_weight {
                adj.entry(source).or_default().push((target, weight));
            }
        }

        // BFS traversal
        self.queue.push_back(start_node);
        self.visited.insert(start_node);

        let mut depth = 0;
        let mut level_size = 1;

        while !self.queue.is_empty() && depth < self.max_depth {
            let node = self.queue.pop_front().unwrap();
            result.push(node);
            level_size -= 1;

            if let Some(neighbors) = adj.get(&node) {
                for &(neighbor, _weight) in neighbors {
                    if !self.visited.contains(&neighbor) || !self.avoid_cycles {
                        self.visited.insert(neighbor);
                        self.queue.push_back(neighbor);
                    }
                }
            }

            if level_size == 0 {
                depth += 1;
                level_size = self.queue.len();
            }
        }

        result
    }

    /// Depth-first traversal from a starting node
    fn traverse_dfs(&mut self, start_node: u64, edges: Vec<(u64, u64, f32)>) -> Vec<u64> {
        self.reset();
        let mut result = Vec::new();

        // Build adjacency list
        let mut adj: HashMap<u64, Vec<(u64, f32)>> = HashMap::new();
        for (source, target, weight) in edges {
            if weight >= self.min_weight {
                adj.entry(source).or_default().push((target, weight));
            }
        }

        // DFS with explicit stack
        let mut stack = vec![start_node];

        while let Some(node) = stack.pop() {
            if self.visited.contains(&node) {
                continue;
            }

            if result.len() >= self.max_depth {
                break;
            }

            self.visited.insert(node);
            result.push(node);

            if let Some(neighbors) = adj.get(&node) {
                for &(neighbor, _weight) in neighbors {
                    if !self.visited.contains(&neighbor) {
                        stack.push(neighbor);
                    }
                }
            }
        }

        result
    }

    /// Find shortest path between two nodes using BFS
    fn find_path(&mut self, start: u64, end: u64, edges: Vec<(u64, u64, f32)>) -> Option<Vec<u64>> {
        self.reset();

        // Build adjacency list
        let mut adj: HashMap<u64, Vec<u64>> = HashMap::new();
        for (source, target, weight) in edges {
            if weight >= self.min_weight {
                adj.entry(source).or_default().push(target);
            }
        }

        // BFS with path tracking
        let mut parent: HashMap<u64, u64> = HashMap::new();
        self.queue.push_back(start);
        self.visited.insert(start);

        while !self.queue.is_empty() {
            let node = self.queue.pop_front().unwrap();

            if node == end {
                // Reconstruct path
                let mut path = vec![end];
                let mut current = end;
                while let Some(&p) = parent.get(&current) {
                    path.push(p);
                    current = p;
                }
                path.reverse();
                return Some(path);
            }

            if let Some(neighbors) = adj.get(&node) {
                for &neighbor in neighbors {
                    if !self.visited.contains(&neighbor) {
                        self.visited.insert(neighbor);
                        parent.insert(neighbor, node);
                        self.queue.push_back(neighbor);
                    }
                }
            }
        }

        None
    }

    /// Find all nodes within a certain depth
    fn get_neighborhood(&mut self, center: u64, edges: Vec<(u64, u64, f32)>) -> Vec<u64> {
        self.traverse_bfs(center, edges)
    }

    /// Reset walker state for new traversal
    fn reset(&mut self) {
        self.queue.clear();
        self.visited.clear();
    }

    /// Get number of visited nodes in current traversal
    fn visited_count(&self) -> usize {
        self.visited.len()
    }

    /// Check if a node has been visited
    fn is_visited(&self, node_id: u64) -> bool {
        self.visited.contains(&node_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_walker_creation() {
        let walker = GraphWalker::new(5);
        assert_eq!(walker.get_max_depth(), 5);
    }

    #[test]
    fn test_bfs_traversal() {
        let mut walker = GraphWalker::new(3);
        let edges = vec![(1, 2, 1.0), (1, 3, 1.0), (2, 4, 1.0), (3, 5, 1.0)];

        let result = walker.traverse_bfs(1, edges);
        assert!(result.contains(&1));
        assert!(result.contains(&2));
        assert!(result.contains(&3));
    }

    #[test]
    fn test_find_path() {
        let mut walker = GraphWalker::new(10);
        let edges = vec![(1, 2, 1.0), (2, 3, 1.0), (3, 4, 1.0)];

        let path = walker.find_path(1, 4, edges);
        assert_eq!(path, Some(vec![1, 2, 3, 4]));
    }

    #[test]
    fn test_dfs_traversal() {
        let mut walker = GraphWalker::new(5);
        let edges = vec![(1, 2, 1.0), (1, 3, 1.0), (2, 4, 1.0)];

        let result = walker.traverse_dfs(1, edges);
        assert!(result.contains(&1));
        assert!(result.len() <= 5);
    }
}
