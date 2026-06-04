//! PageRank - Parallel PageRank Algorithm (PSR-003)
//! Target: 30× speedup for PageRank computation

use pyo3::prelude::*;
use std::collections::HashMap;
use rayon::prelude::*;

#[pyclass]
pub struct PyPageRank {
    graph: HashMap<String, Vec<String>>,
    damping_factor: f64,
    max_iterations: usize,
    tolerance: f64,
}

#[pymethods]
impl PyPageRank {
    #[new]
    fn new(damping_factor: Option<f64>, max_iterations: Option<usize>, tolerance: Option<f64>) -> Self {
        Self {
            graph: HashMap::new(),
            damping_factor: damping_factor.unwrap_or(0.85),
            max_iterations: max_iterations.unwrap_or(100),
            tolerance: tolerance.unwrap_or(1e-6),
        }
    }

    fn add_edge(&mut self, source: String, target: String) {
        self.graph
            .entry(source)
            .or_insert_with(Vec::new)
            .push(target);
    }

    fn compute(&self) -> HashMap<String, f64> {
        let nodes: Vec<String> = self.get_all_nodes();
        let n = nodes.len();
        
        if n == 0 {
            return HashMap::new();
        }
        
        let initial_rank = 1.0 / n as f64;
        let mut ranks: HashMap<String, f64> = nodes
            .iter()
            .map(|node| (node.clone(), initial_rank))
            .collect();
        
        for _ in 0..self.max_iterations {
            let new_ranks = self.compute_iteration(&nodes, &ranks);
            
            let diff: f64 = nodes
                .iter()
                .map(|node| {
                    let old = ranks.get(node).unwrap_or(&0.0);
                    let new = new_ranks.get(node).unwrap_or(&0.0);
                    (old - new).abs()
                })
                .sum();
            
            ranks = new_ranks;
            
            if diff < self.tolerance {
                break;
            }
        }
        
        ranks
    }

    fn compute_parallel(&self) -> HashMap<String, f64> {
        let nodes: Vec<String> = self.get_all_nodes();
        let n = nodes.len();
        
        if n == 0 {
            return HashMap::new();
        }
        
        let initial_rank = 1.0 / n as f64;
        let mut ranks: HashMap<String, f64> = nodes
            .iter()
            .map(|node| (node.clone(), initial_rank))
            .collect();
        
        for _ in 0..self.max_iterations {
            let new_ranks = self.compute_iteration_parallel(&nodes, &ranks);
            
            let diff: f64 = nodes
                .par_iter()
                .map(|node| {
                    let old = ranks.get(node).unwrap_or(&0.0);
                    let new = new_ranks.get(node).unwrap_or(&0.0);
                    (old - new).abs()
                })
                .sum();
            
            ranks = new_ranks;
            
            if diff < self.tolerance {
                break;
            }
        }
        
        ranks
    }

    fn get_top_nodes(&self, ranks: HashMap<String, f64>, k: usize) -> Vec<(String, f64)> {
        let mut sorted: Vec<(String, f64)> = ranks.into_iter().collect();
        sorted.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        sorted.truncate(k);
        sorted
    }

    fn node_count(&self) -> usize {
        self.get_all_nodes().len()
    }

    fn edge_count(&self) -> usize {
        self.graph.values().map(|v| v.len()).sum()
    }
}

impl PyPageRank {
    fn get_all_nodes(&self) -> Vec<String> {
        let mut nodes = std::collections::HashSet::new();
        
        for (source, targets) in &self.graph {
            nodes.insert(source.clone());
            for target in targets {
                nodes.insert(target.clone());
            }
        }
        
        nodes.into_iter().collect()
    }

    fn compute_iteration(&self, nodes: &[String], ranks: &HashMap<String, f64>) -> HashMap<String, f64> {
        let n = nodes.len() as f64;
        let base_rank = (1.0 - self.damping_factor) / n;
        
        let mut new_ranks = HashMap::new();
        
        for node in nodes {
            let mut rank = base_rank;
            
            for (source, targets) in &self.graph {
                if targets.contains(node) {
                    let source_rank = ranks.get(source).unwrap_or(&0.0);
                    let out_degree = targets.len() as f64;
                    rank += self.damping_factor * source_rank / out_degree;
                }
            }
            
            new_ranks.insert(node.clone(), rank);
        }
        
        new_ranks
    }

    fn compute_iteration_parallel(&self, nodes: &[String], ranks: &HashMap<String, f64>) -> HashMap<String, f64> {
        let n = nodes.len() as f64;
        let base_rank = (1.0 - self.damping_factor) / n;
        
        let new_ranks: Vec<(String, f64)> = nodes
            .par_iter()
            .map(|node| {
                let mut rank = base_rank;
                
                for (source, targets) in &self.graph {
                    if targets.contains(node) {
                        let source_rank = ranks.get(source).unwrap_or(&0.0);
                        let out_degree = targets.len() as f64;
                        rank += self.damping_factor * source_rank / out_degree;
                    }
                }
                
                (node.clone(), rank)
            })
            .collect();
        
        new_ranks.into_iter().collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pagerank_creation() {
        let pr = PyPageRank::new(Some(0.85), Some(100), Some(1e-6));
        assert_eq!(pr.node_count(), 0);
    }

    #[test]
    fn test_add_edge() {
        let mut pr = PyPageRank::new(None, None, None);
        pr.add_edge("a".to_string(), "b".to_string());
        
        assert_eq!(pr.edge_count(), 1);
    }

    #[test]
    fn test_compute() {
        let mut pr = PyPageRank::new(Some(0.85), Some(10), Some(1e-6));
        
        pr.add_edge("a".to_string(), "b".to_string());
        pr.add_edge("b".to_string(), "c".to_string());
        pr.add_edge("c".to_string(), "a".to_string());
        
        let ranks = pr.compute();
        
        assert_eq!(ranks.len(), 3);
        assert!(ranks.values().all(|&r| r > 0.0));
    }

    #[test]
    fn test_top_nodes() {
        let mut pr = PyPageRank::new(None, None, None);
        
        pr.add_edge("a".to_string(), "b".to_string());
        pr.add_edge("a".to_string(), "c".to_string());
        pr.add_edge("b".to_string(), "c".to_string());
        
        let ranks = pr.compute();
        let top = pr.get_top_nodes(ranks, 2);
        
        assert_eq!(top.len(), 2);
    }
}
