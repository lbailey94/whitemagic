//! Graph Algorithms - Core Graph Operations (PSR-001)
//! Target: 30-50× speedup for graph operations

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};

#[derive(Clone, Debug)]
#[pyclass]
pub struct Edge {
    #[pyo3(get)]
    pub source: String,
    #[pyo3(get)]
    pub target: String,
    #[pyo3(get)]
    pub weight: f64,
}

#[pymethods]
impl Edge {
    #[new]
    fn new(source: String, target: String, weight: f64) -> Self {
        Self { source, target, weight }
    }
}

#[pyclass]
pub struct PyGraph {
    adjacency: HashMap<String, Vec<(String, f64)>>,
}

#[pymethods]
impl PyGraph {
    #[new]
    fn new() -> Self {
        Self {
            adjacency: HashMap::new(),
        }
    }

    fn add_edge(&mut self, source: String, target: String, weight: f64) {
        self.adjacency
            .entry(source.clone())
            .or_insert_with(Vec::new)
            .push((target.clone(), weight));
    }

    fn get_neighbors(&self, node: String) -> Vec<String> {
        self.adjacency
            .get(&node)
            .map(|edges| edges.iter().map(|(t, _)| t.clone()).collect())
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
            
            if let Some(neighbors) = self.adjacency.get(&node) {
                for (neighbor, _) in neighbors {
                    if !visited.contains(neighbor) {
                        visited.insert(neighbor.clone());
                        queue.push_back((neighbor.clone(), depth + 1));
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
            
            if let Some(neighbors) = self.adjacency.get(&node) {
                for (neighbor, _) in neighbors {
                    if !visited.contains(neighbor) {
                        visited.insert(neighbor.clone());
                        parent.insert(neighbor.clone(), node.clone());
                        queue.push_back(neighbor.clone());
                    }
                }
            }
        }
        
        None
    }

    fn node_count(&self) -> usize {
        self.adjacency.len()
    }

    fn edge_count(&self) -> usize {
        self.adjacency.values().map(|v| v.len()).sum()
    }

    fn degree(&self, node: String) -> usize {
        self.adjacency.get(&node).map(|v| v.len()).unwrap_or(0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_edge() {
        let mut graph = PyGraph::new();
        graph.add_edge("a".to_string(), "b".to_string(), 1.0);
        
        assert_eq!(graph.node_count(), 1);
        assert_eq!(graph.edge_count(), 1);
    }

    #[test]
    fn test_bfs() {
        let mut graph = PyGraph::new();
        graph.add_edge("a".to_string(), "b".to_string(), 1.0);
        graph.add_edge("b".to_string(), "c".to_string(), 1.0);
        graph.add_edge("a".to_string(), "d".to_string(), 1.0);
        
        let visited = graph.bfs("a".to_string(), None);
        assert!(visited.len() >= 3);
    }

    #[test]
    fn test_shortest_path() {
        let mut graph = PyGraph::new();
        graph.add_edge("a".to_string(), "b".to_string(), 1.0);
        graph.add_edge("b".to_string(), "c".to_string(), 1.0);
        
        let path = graph.shortest_path("a".to_string(), "c".to_string());
        assert!(path.is_some());
        assert_eq!(path.unwrap().len(), 3);
    }

    #[test]
    fn test_degree() {
        let mut graph = PyGraph::new();
        graph.add_edge("a".to_string(), "b".to_string(), 1.0);
        graph.add_edge("a".to_string(), "c".to_string(), 1.0);
        
        assert_eq!(graph.degree("a".to_string()), 2);
    }
}
