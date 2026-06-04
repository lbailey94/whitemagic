//! Causal Net V2 - Causal Inference Engine (PSR-004)
//! Target: 30× speedup for causal inference
//! Note: causal_net.rs exists in Python, this is Rust implementation

use pyo3::prelude::*;
use std::collections::HashSet;

#[derive(Clone, Debug)]
#[pyclass]
pub struct CausalEdge {
    #[pyo3(get)]
    pub cause: String,
    #[pyo3(get)]
    pub effect: String,
    #[pyo3(get)]
    pub strength: f64,
    #[pyo3(get)]
    pub confidence: f64,
}

#[pymethods]
impl CausalEdge {
    #[new]
    fn new(cause: String, effect: String, strength: f64, confidence: f64) -> Self {
        Self {
            cause,
            effect,
            strength,
            confidence,
        }
    }
}

#[pyclass]
pub struct PyCausalNetV2 {
    edges: Vec<CausalEdge>,
    nodes: HashSet<String>,
}

#[pymethods]
impl PyCausalNetV2 {
    #[new]
    fn new() -> Self {
        Self {
            edges: Vec::new(),
            nodes: HashSet::new(),
        }
    }

    fn add_edge(&mut self, edge: CausalEdge) {
        self.nodes.insert(edge.cause.clone());
        self.nodes.insert(edge.effect.clone());
        self.edges.push(edge);
    }

    fn get_causes(&self, effect: String) -> Vec<CausalEdge> {
        self.edges
            .iter()
            .filter(|e| e.effect == effect)
            .cloned()
            .collect()
    }

    fn get_effects(&self, cause: String) -> Vec<CausalEdge> {
        self.edges
            .iter()
            .filter(|e| e.cause == cause)
            .cloned()
            .collect()
    }

    fn find_causal_path(&self, start: String, end: String, max_depth: usize) -> Vec<Vec<String>> {
        let mut paths = Vec::new();
        let mut current_path = vec![start.clone()];
        let mut visited = HashSet::new();
        
        self.dfs_paths(&start, &end, &mut current_path, &mut visited, &mut paths, 0, max_depth);
        
        paths
    }

    fn calculate_total_effect(&self, cause: String, effect: String) -> f64 {
        let paths = self.find_causal_path(cause, effect, 5);
        
        let mut total_effect = 0.0;
        
        for path in paths {
            let mut path_strength = 1.0;
            
            for i in 0..path.len() - 1 {
                if let Some(edge) = self.edges.iter().find(|e| e.cause == path[i] && e.effect == path[i + 1]) {
                    path_strength *= edge.strength;
                }
            }
            
            total_effect += path_strength;
        }
        
        total_effect
    }

    fn get_root_causes(&self) -> Vec<String> {
        let effects: HashSet<String> = self.edges.iter().map(|e| e.effect.clone()).collect();
        
        self.nodes
            .iter()
            .filter(|node| !effects.contains(*node))
            .cloned()
            .collect()
    }

    fn node_count(&self) -> usize {
        self.nodes.len()
    }

    fn edge_count(&self) -> usize {
        self.edges.len()
    }
}

impl PyCausalNetV2 {
    fn dfs_paths(
        &self,
        current: &str,
        target: &str,
        path: &mut Vec<String>,
        visited: &mut HashSet<String>,
        paths: &mut Vec<Vec<String>>,
        depth: usize,
        max_depth: usize,
    ) {
        if depth > max_depth {
            return;
        }
        
        if current == target {
            paths.push(path.clone());
            return;
        }
        
        visited.insert(current.to_string());
        
        for edge in &self.edges {
            if edge.cause == current && !visited.contains(&edge.effect) {
                path.push(edge.effect.clone());
                self.dfs_paths(&edge.effect, target, path, visited, paths, depth + 1, max_depth);
                path.pop();
            }
        }
        
        visited.remove(current);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_net_creation() {
        let net = PyCausalNetV2::new();
        assert_eq!(net.node_count(), 0);
    }

    #[test]
    fn test_add_edge() {
        let mut net = PyCausalNetV2::new();
        let edge = CausalEdge::new("a".to_string(), "b".to_string(), 0.8, 0.9);
        
        net.add_edge(edge);
        assert_eq!(net.edge_count(), 1);
        assert_eq!(net.node_count(), 2);
    }

    #[test]
    fn test_get_causes() {
        let mut net = PyCausalNetV2::new();
        
        net.add_edge(CausalEdge::new("a".to_string(), "c".to_string(), 0.8, 0.9));
        net.add_edge(CausalEdge::new("b".to_string(), "c".to_string(), 0.7, 0.8));
        
        let causes = net.get_causes("c".to_string());
        assert_eq!(causes.len(), 2);
    }

    #[test]
    fn test_find_causal_path() {
        let mut net = PyCausalNetV2::new();
        
        net.add_edge(CausalEdge::new("a".to_string(), "b".to_string(), 0.8, 0.9));
        net.add_edge(CausalEdge::new("b".to_string(), "c".to_string(), 0.7, 0.8));
        
        let paths = net.find_causal_path("a".to_string(), "c".to_string(), 5);
        assert!(!paths.is_empty());
    }

    #[test]
    fn test_root_causes() {
        let mut net = PyCausalNetV2::new();
        
        net.add_edge(CausalEdge::new("a".to_string(), "b".to_string(), 0.8, 0.9));
        net.add_edge(CausalEdge::new("b".to_string(), "c".to_string(), 0.7, 0.8));
        
        let roots = net.get_root_causes();
        assert_eq!(roots.len(), 1);
        assert!(roots.contains(&"a".to_string()));
    }
}
