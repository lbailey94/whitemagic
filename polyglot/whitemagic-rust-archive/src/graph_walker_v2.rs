//! Graph Walker V2 - Parallel Graph Walking (PSR-003)
//! Target: 50× speedup for graph traversal

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};
use rayon::prelude::*;

#[derive(Clone, Debug)]
#[pyclass]
pub struct WalkResult {
    #[pyo3(get)]
    pub node_id: String,
    #[pyo3(get)]
    pub depth: usize,
    #[pyo3(get)]
    pub score: f64,
}

#[pymethods]
impl WalkResult {
    #[new]
    fn new(node_id: String, depth: usize, score: f64) -> Self {
        Self {
            node_id,
            depth,
            score,
        }
    }
}

#[pyclass]
pub struct PyGraphWalkerV2 {
    graph: HashMap<String, Vec<String>>,
}

#[pymethods]
impl PyGraphWalkerV2 {
    #[new]
    fn new() -> Self {
        Self {
            graph: HashMap::new(),
        }
    }

    fn add_edge(&mut self, source: String, target: String) {
        self.graph
            .entry(source)
            .or_insert_with(Vec::new)
            .push(target);
    }

    fn walk(&self, start: String, max_depth: usize) -> Vec<WalkResult> {
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();
        let mut results = Vec::new();
        
        queue.push_back((start.clone(), 0));
        visited.insert(start);
        
        while let Some((node, depth)) = queue.pop_front() {
            if depth > max_depth {
                break;
            }
            
            results.push(WalkResult {
                node_id: node.clone(),
                depth,
                score: 1.0 / (depth + 1) as f64,
            });
            
            if let Some(neighbors) = self.graph.get(&node) {
                for neighbor in neighbors {
                    if !visited.contains(neighbor) {
                        visited.insert(neighbor.clone());
                        queue.push_back((neighbor.clone(), depth + 1));
                    }
                }
            }
        }
        
        results
    }

    fn parallel_walk(&self, starts: Vec<String>, max_depth: usize) -> Vec<Vec<WalkResult>> {
        starts
            .par_iter()
            .map(|start| self.walk(start.clone(), max_depth))
            .collect()
    }

    fn random_walk(&self, start: String, steps: usize) -> Vec<String> {
        let mut path = vec![start.clone()];
        let mut current = start;
        
        for _ in 0..steps {
            if let Some(neighbors) = self.graph.get(&current) {
                if neighbors.is_empty() {
                    break;
                }
                
                let next_idx = 0;
                current = neighbors[next_idx].clone();
                path.push(current.clone());
            } else {
                break;
            }
        }
        
        path
    }

    fn node_count(&self) -> usize {
        self.graph.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_walker_creation() {
        let walker = PyGraphWalkerV2::new();
        assert_eq!(walker.node_count(), 0);
    }

    #[test]
    fn test_add_edge() {
        let mut walker = PyGraphWalkerV2::new();
        walker.add_edge("a".to_string(), "b".to_string());
        
        assert_eq!(walker.node_count(), 1);
    }

    #[test]
    fn test_walk() {
        let mut walker = PyGraphWalkerV2::new();
        walker.add_edge("a".to_string(), "b".to_string());
        walker.add_edge("b".to_string(), "c".to_string());
        
        let results = walker.walk("a".to_string(), 5);
        assert!(results.len() >= 2);
    }

    #[test]
    fn test_random_walk() {
        let mut walker = PyGraphWalkerV2::new();
        walker.add_edge("a".to_string(), "b".to_string());
        walker.add_edge("b".to_string(), "c".to_string());
        
        let path = walker.random_walk("a".to_string(), 5);
        assert!(!path.is_empty());
    }

    #[test]
    fn test_parallel_walk() {
        let mut walker = PyGraphWalkerV2::new();
        walker.add_edge("a".to_string(), "b".to_string());
        walker.add_edge("c".to_string(), "d".to_string());
        
        let results = walker.parallel_walk(vec!["a".to_string(), "c".to_string()], 2);
        assert_eq!(results.len(), 2);
    }
}
