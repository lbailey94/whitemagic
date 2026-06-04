//! Community Detector - Community Detection (PSR-003)
//! Target: 30× speedup for community detection

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};
use rayon::prelude::*;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Community {
    #[pyo3(get)]
    pub id: usize,
    #[pyo3(get)]
    pub members: Vec<String>,
    #[pyo3(get)]
    pub density: f64,
}

#[pymethods]
impl Community {
    #[new]
    fn new(id: usize, members: Vec<String>, density: f64) -> Self {
        Self {
            id,
            members,
            density,
        }
    }
}

#[pyclass]
pub struct PyCommunityDetector {
    graph: HashMap<String, Vec<String>>,
}

#[pymethods]
impl PyCommunityDetector {
    #[new]
    fn new() -> Self {
        Self {
            graph: HashMap::new(),
        }
    }

    fn add_edge(&mut self, source: String, target: String) {
        self.graph
            .entry(source.clone())
            .or_insert_with(Vec::new)
            .push(target.clone());
        
        self.graph
            .entry(target)
            .or_insert_with(Vec::new)
            .push(source);
    }

    fn detect_communities(&self, min_size: usize) -> Vec<Community> {
        let mut visited = HashSet::new();
        let mut communities = Vec::new();
        let mut community_id = 0;
        
        for node in self.graph.keys() {
            if visited.contains(node) {
                continue;
            }
            
            let component = self.get_component(node.clone(), &mut visited);
            
            if component.len() >= min_size {
                let density = self.calculate_density(&component);
                communities.push(Community {
                    id: community_id,
                    members: component,
                    density,
                });
                community_id += 1;
            }
        }
        
        communities
    }

    fn get_modularity(&self, communities: Vec<Community>) -> f64 {
        let total_edges = self.edge_count() as f64;
        if total_edges == 0.0 {
            return 0.0;
        }
        
        let mut modularity = 0.0;
        
        for community in &communities {
            let internal_edges = self.count_internal_edges(&community.members);
            let degree_sum: usize = community
                .members
                .iter()
                .map(|node| self.graph.get(node).map(|v| v.len()).unwrap_or(0))
                .sum();
            
            modularity += (internal_edges as f64 / total_edges) 
                - ((degree_sum as f64 / (2.0 * total_edges)).powi(2));
        }
        
        modularity
    }

    fn parallel_detect(&self, min_size: usize) -> Vec<Community> {
        let nodes: Vec<String> = self.graph.keys().cloned().collect();
        let mut visited = HashSet::new();
        let mut communities = Vec::new();
        
        for node in nodes {
            if visited.contains(&node) {
                continue;
            }
            
            let component = self.get_component(node, &mut visited);
            
            if component.len() >= min_size {
                let density = self.calculate_density(&component);
                communities.push(Community {
                    id: communities.len(),
                    members: component,
                    density,
                });
            }
        }
        
        communities
    }

    fn node_count(&self) -> usize {
        self.graph.len()
    }

    fn edge_count(&self) -> usize {
        self.graph.values().map(|v| v.len()).sum::<usize>() / 2
    }
}

impl PyCommunityDetector {
    fn get_component(&self, start: String, visited: &mut HashSet<String>) -> Vec<String> {
        let mut component = Vec::new();
        let mut stack = vec![start];
        
        while let Some(node) = stack.pop() {
            if visited.contains(&node) {
                continue;
            }
            
            visited.insert(node.clone());
            component.push(node.clone());
            
            if let Some(neighbors) = self.graph.get(&node) {
                for neighbor in neighbors {
                    if !visited.contains(neighbor) {
                        stack.push(neighbor.clone());
                    }
                }
            }
        }
        
        component
    }

    fn calculate_density(&self, nodes: &[String]) -> f64 {
        if nodes.len() < 2 {
            return 0.0;
        }
        
        let node_set: HashSet<&String> = nodes.iter().collect();
        let mut internal_edges = 0;
        
        for node in nodes {
            if let Some(neighbors) = self.graph.get(node) {
                for neighbor in neighbors {
                    if node_set.contains(neighbor) {
                        internal_edges += 1;
                    }
                }
            }
        }
        
        let max_edges = nodes.len() * (nodes.len() - 1);
        if max_edges == 0 {
            return 0.0;
        }
        
        internal_edges as f64 / max_edges as f64
    }

    fn count_internal_edges(&self, nodes: &[String]) -> usize {
        let node_set: HashSet<&String> = nodes.iter().collect();
        let mut count = 0;
        
        for node in nodes {
            if let Some(neighbors) = self.graph.get(node) {
                for neighbor in neighbors {
                    if node_set.contains(neighbor) {
                        count += 1;
                    }
                }
            }
        }
        
        count / 2
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detector_creation() {
        let detector = PyCommunityDetector::new();
        assert_eq!(detector.node_count(), 0);
    }

    #[test]
    fn test_add_edge() {
        let mut detector = PyCommunityDetector::new();
        detector.add_edge("a".to_string(), "b".to_string());
        
        assert_eq!(detector.node_count(), 2);
    }

    #[test]
    fn test_detect_communities() {
        let mut detector = PyCommunityDetector::new();
        
        detector.add_edge("a".to_string(), "b".to_string());
        detector.add_edge("b".to_string(), "c".to_string());
        detector.add_edge("d".to_string(), "e".to_string());
        
        let communities = detector.detect_communities(2);
        assert_eq!(communities.len(), 2);
    }

    #[test]
    fn test_modularity() {
        let mut detector = PyCommunityDetector::new();
        
        detector.add_edge("a".to_string(), "b".to_string());
        detector.add_edge("b".to_string(), "c".to_string());
        
        let communities = detector.detect_communities(1);
        let modularity = detector.get_modularity(communities);
        
        assert!(modularity >= 0.0);
    }
}
