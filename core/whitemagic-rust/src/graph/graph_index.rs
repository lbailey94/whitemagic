//! Graph Index - Efficient Adjacency Structures (PSR-003)
//! Target: 30× speedup for graph indexing

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};
use rayon::prelude::*;

#[pyclass]
pub struct PyGraphIndex {
    forward: HashMap<String, HashSet<String>>,
    reverse: HashMap<String, HashSet<String>>,
    edge_weights: HashMap<(String, String), f64>,
}

#[pymethods]
impl PyGraphIndex {
    #[new]
    fn new() -> Self {
        Self {
            forward: HashMap::new(),
            reverse: HashMap::new(),
            edge_weights: HashMap::new(),
        }
    }

    fn add_edge(&mut self, source: String, target: String, weight: f64) {
        self.forward
            .entry(source.clone())
            .or_insert_with(HashSet::new)
            .insert(target.clone());
        
        self.reverse
            .entry(target.clone())
            .or_insert_with(HashSet::new)
            .insert(source.clone());
        
        self.edge_weights.insert((source, target), weight);
    }

    fn get_neighbors(&self, node: String) -> Vec<String> {
        self.forward
            .get(&node)
            .map(|set| set.iter().cloned().collect())
            .unwrap_or_default()
    }

    fn get_predecessors(&self, node: String) -> Vec<String> {
        self.reverse
            .get(&node)
            .map(|set| set.iter().cloned().collect())
            .unwrap_or_default()
    }

    fn get_edge_weight(&self, source: String, target: String) -> Option<f64> {
        self.edge_weights.get(&(source, target)).copied()
    }

    fn has_edge(&self, source: String, target: String) -> bool {
        self.forward
            .get(&source)
            .map(|set| set.contains(&target))
            .unwrap_or(false)
    }

    fn out_degree(&self, node: String) -> usize {
        self.forward.get(&node).map(|set| set.len()).unwrap_or(0)
    }

    fn in_degree(&self, node: String) -> usize {
        self.reverse.get(&node).map(|set| set.len()).unwrap_or(0)
    }

    fn node_count(&self) -> usize {
        let mut nodes = HashSet::new();
        nodes.extend(self.forward.keys().cloned());
        nodes.extend(self.reverse.keys().cloned());
        nodes.len()
    }

    fn edge_count(&self) -> usize {
        self.edge_weights.len()
    }

    fn get_all_nodes(&self) -> Vec<String> {
        let mut nodes = HashSet::new();
        nodes.extend(self.forward.keys().cloned());
        nodes.extend(self.reverse.keys().cloned());
        nodes.into_iter().collect()
    }

    fn parallel_neighbors(&self, nodes: Vec<String>) -> Vec<Vec<String>> {
        nodes
            .par_iter()
            .map(|node| self.get_neighbors(node.clone()))
            .collect()
    }

    fn clear(&mut self) {
        self.forward.clear();
        self.reverse.clear();
        self.edge_weights.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_index_creation() {
        let index = PyGraphIndex::new();
        assert_eq!(index.node_count(), 0);
    }

    #[test]
    fn test_add_edge() {
        let mut index = PyGraphIndex::new();
        index.add_edge("a".to_string(), "b".to_string(), 1.0);
        
        assert_eq!(index.edge_count(), 1);
        assert!(index.has_edge("a".to_string(), "b".to_string()));
    }

    #[test]
    fn test_degrees() {
        let mut index = PyGraphIndex::new();
        index.add_edge("a".to_string(), "b".to_string(), 1.0);
        index.add_edge("a".to_string(), "c".to_string(), 1.0);
        
        assert_eq!(index.out_degree("a".to_string()), 2);
        assert_eq!(index.in_degree("b".to_string()), 1);
    }

    #[test]
    fn test_get_neighbors() {
        let mut index = PyGraphIndex::new();
        index.add_edge("a".to_string(), "b".to_string(), 1.0);
        index.add_edge("a".to_string(), "c".to_string(), 1.0);
        
        let neighbors = index.get_neighbors("a".to_string());
        assert_eq!(neighbors.len(), 2);
    }
}
