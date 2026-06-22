//! Unified Memory System v2
//! High-performance unified memory with hybrid recall

use pyo3::prelude::*;
use std::collections::HashMap;
#[pyclass]
pub struct UnifiedMemoryV2 {
    memories: HashMap<String, String>,
    vector_index: Vec<(String, Vec<f64>)>,
}

#[pymethods]
impl UnifiedMemoryV2 {
    #[new]
    fn new() -> Self {
        Self {
            memories: HashMap::new(),
            vector_index: Vec::new(),
        }
    }
    
    fn store(&mut self, id: String, content: String, embedding: Vec<f64>) -> PyResult<()> {
        self.memories.insert(id.clone(), content);
        self.vector_index.push((id, embedding));
        Ok(())
    }
    
    fn hybrid_recall(
        &self,
        _query: String,
        query_embedding: Vec<f64>,
        limit: usize
    ) -> PyResult<Vec<String>> {
        let mut scored: Vec<(String, f64)> = self.vector_index
            .iter()
            .map(|(id, emb)| {
                let score = Self::cosine_sim(&query_embedding, emb);
                (id.clone(), score)
            })
            .collect();
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        Ok(scored.into_iter().take(limit).map(|(id, _)| id).collect())
    }
}

impl UnifiedMemoryV2 {
    fn cosine_sim(a: &[f64], b: &[f64]) -> f64 {
        let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let norm_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm_a == 0.0 || norm_b == 0.0 { 0.0 } else { dot / (norm_a * norm_b) }
    }
}
