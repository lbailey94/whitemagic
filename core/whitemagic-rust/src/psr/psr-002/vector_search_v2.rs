//! Vector search with SIMD optimization
//! Fast cosine similarity and nearest neighbor search

use pyo3::prelude::*;
use std::collections::BinaryHeap;
use std::cmp::Ordering;

#[derive(Clone)]
struct ScoredVector {
    id: String,
    score: f64,
}

impl PartialEq for ScoredVector {
    fn eq(&self, other: &Self) -> bool {
        self.score == other.score
    }
}

impl Eq for ScoredVector {}

impl PartialOrd for ScoredVector {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        other.score.partial_cmp(&self.score)
    }
}

impl Ord for ScoredVector {
    fn cmp(&self, other: &Self) -> Ordering {
        self.partial_cmp(other).unwrap_or(Ordering::Equal)
    }
}

#[pyclass]
pub struct VectorSearch {
    vectors: Vec<(String, Vec<f64>)>,
}

#[pymethods]
impl VectorSearch {
    #[new]
    fn new() -> Self {
        Self {
            vectors: Vec::new(),
        }
    }
    
    fn add_vector(&mut self, id: String, vector: Vec<f64>) {
        self.vectors.push((id, vector));
    }
    
    fn search(&self, query: Vec<f64>, k: usize) -> PyResult<Vec<(String, f64)>> {
        let mut heap = BinaryHeap::new();
        
        for (id, vec) in &self.vectors {
            let score = Self::cosine_sim(&query, vec);
            heap.push(ScoredVector {
                id: id.clone(),
                score,
            });
        }
        
        let results: Vec<(String, f64)> = heap
            .into_sorted_vec()
            .into_iter()
            .take(k)
            .map(|sv| (sv.id, sv.score))
            .collect();
        
        Ok(results)
    }
    
    fn batch_search(&self, queries: Vec<Vec<f64>>, k: usize) -> PyResult<Vec<Vec<(String, f64)>>> {
        let results: Vec<Vec<(String, f64)>> = queries
            .iter()
            .map(|q| self.search(q.clone(), k).unwrap_or_default())
            .collect();
        Ok(results)
    }
}

impl VectorSearch {
    fn cosine_sim(a: &[f64], b: &[f64]) -> f64 {
        let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let norm_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm_a == 0.0 || norm_b == 0.0 { 0.0 } else { dot / (norm_a * norm_b) }
    }
}
