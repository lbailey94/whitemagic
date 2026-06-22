//! Hybrid recall combining FTS, vector, and graph search
//! Reciprocal Rank Fusion for result merging

use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
pub struct HybridRecall {
    fts_weight: f64,
    vector_weight: f64,
    graph_weight: f64,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl HybridRecall {
    #[new]
    fn new(fts_weight: Option<f64>, vector_weight: Option<f64>, graph_weight: Option<f64>) -> Self {
        Self {
            fts_weight: fts_weight.unwrap_or(0.4),
            vector_weight: vector_weight.unwrap_or(0.4),
            graph_weight: graph_weight.unwrap_or(0.2),
        }
    }
    
    fn reciprocal_rank_fusion(
        &self,
        fts_results: Vec<String>,
        vector_results: Vec<String>,
        graph_results: Vec<String>,
        k: Option<usize>
    ) -> PyResult<Vec<String>> {
        let mut scores: HashMap<String, f64> = HashMap::new();
        let k_val = k.unwrap_or(60) as f64;
        
        // FTS scores
        for (rank, id) in fts_results.iter().enumerate() {
            let score = self.fts_weight / (k_val + (rank + 1) as f64);
            *scores.entry(id.clone()).or_insert(0.0) += score;
        }
        
        // Vector scores
        for (rank, id) in vector_results.iter().enumerate() {
            let score = self.vector_weight / (k_val + (rank + 1) as f64);
            *scores.entry(id.clone()).or_insert(0.0) += score;
        }
        
        // Graph scores
        for (rank, id) in graph_results.iter().enumerate() {
            let score = self.graph_weight / (k_val + (rank + 1) as f64);
            *scores.entry(id.clone()).or_insert(0.0) += score;
        }
        
        // Sort by score descending
        let mut results: Vec<(String, f64)> = scores.into_iter().collect();
        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        
        Ok(results.into_iter().map(|(id, _)| id).collect())
    }
}
