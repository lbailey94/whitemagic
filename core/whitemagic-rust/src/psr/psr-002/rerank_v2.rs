//! Result reranking with multiple signals
//! Cross-encoder style reranking

use pyo3::prelude::*;

#[pyclass]
pub struct Reranker {
    importance_weight: f64,
    recency_weight: f64,
    relevance_weight: f64,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl Reranker {
    #[new]
    fn new() -> Self {
        Self {
            importance_weight: 0.3,
            recency_weight: 0.2,
            relevance_weight: 0.5,
        }
    }
    
    fn rerank(
        &self,
        results: Vec<String>,
        importance_scores: Vec<f64>,
        recency_scores: Vec<f64>,
        relevance_scores: Vec<f64>
    ) -> PyResult<Vec<String>> {
        let mut scored: Vec<(String, f64)> = results
            .into_iter()
            .zip(importance_scores.iter())
            .zip(recency_scores.iter())
            .zip(relevance_scores.iter())
            .map(|(((id, imp), rec), rel)| {
                let score = imp * self.importance_weight
                    + rec * self.recency_weight
                    + rel * self.relevance_weight;
                (id, score)
            })
            .collect();
        
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        
        Ok(scored.into_iter().map(|(id, _)| id).collect())
    }
}
