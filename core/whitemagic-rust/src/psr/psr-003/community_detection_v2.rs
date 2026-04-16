//! Community detection in graphs
//! Label propagation algorithm

use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
pub struct CommunityDetector {
    max_iterations: usize,
}

#[derive(Clone, Debug)]
#[allow(dead_code)]
struct Edge {
    target: String,
    weight: f64,
    #[allow(dead_code)]
    relation_type: String,
}

#[pymethods]
impl CommunityDetector {
    #[new]
    fn new(max_iterations: Option<usize>) -> Self {
        Self {
            max_iterations: max_iterations.unwrap_or(100),
        }
    }
    
    fn detect_communities(
        &self,
        edges: Vec<(String, String)>
    ) -> PyResult<HashMap<String, usize>> {
        let mut labels: HashMap<String, usize> = HashMap::new();
        let mut neighbors: HashMap<String, Vec<String>> = HashMap::new();
        
        // Build adjacency list and initialize labels
        let mut label_counter = 0;
        for (src, dst) in &edges {
            if !labels.contains_key(src) {
                labels.insert(src.clone(), label_counter);
                label_counter += 1;
            }
            if !labels.contains_key(dst) {
                labels.insert(dst.clone(), label_counter);
                label_counter += 1;
            }
            
            neighbors.entry(src.clone()).or_insert_with(Vec::new).push(dst.clone());
            neighbors.entry(dst.clone()).or_insert_with(Vec::new).push(src.clone());
        }
        
        // Label propagation
        let _rng = rand::thread_rng();
        for _ in 0..self.max_iterations {
            let mut changed = false;
            let nodes: Vec<String> = labels.keys().cloned().collect();
            
            for node in nodes {
                if let Some(neighs) = neighbors.get(&node) {
                    let mut label_counts: HashMap<usize, usize> = HashMap::new();
                    
                    for neigh in neighs {
                        if let Some(&label) = labels.get(neigh) {
                            *label_counts.entry(label).or_insert(0) += 1;
                        }
                    }
                    
                    if let Some((&new_label, _)) = label_counts.iter().max_by_key(|(_, &count)| count) {
                        if labels.get(&node) != Some(&new_label) {
                            labels.insert(node.clone(), new_label);
                            changed = true;
                        }
                    }
                }
            }
            
            if !changed {
                break;
            }
        }
        
        Ok(labels)
    }
}
