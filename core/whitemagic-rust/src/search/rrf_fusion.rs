//! RRF Fusion - Reciprocal Rank Fusion (PSR-002)
//! Target: 30× speedup for hybrid search fusion
//! Note: hybrid_rrf.rs already exists, this extends it

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
#[pyclass]
pub struct FusionResult {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub score: f64,
    #[pyo3(get)]
    pub rank: usize,
    #[pyo3(get)]
    pub source_scores: Vec<f64>,
}

#[pymethods]
impl FusionResult {
    #[new]
    fn new(id: String, score: f64, rank: usize, source_scores: Vec<f64>) -> Self {
        Self {
            id,
            score,
            rank,
            source_scores,
        }
    }
}

#[pyclass]
pub struct PyRRFFusion {
    k: f64,
}

#[pymethods]
impl PyRRFFusion {
    #[new]
    fn new(k: Option<f64>) -> Self {
        Self {
            k: k.unwrap_or(60.0),
        }
    }

    fn fuse(&self, result_lists: Vec<Vec<String>>) -> Vec<FusionResult> {
        let mut scores: HashMap<String, f64> = HashMap::new();
        let mut source_scores_map: HashMap<String, Vec<f64>> = HashMap::new();
        
        for (list_idx, results) in result_lists.iter().enumerate() {
            for (rank, id) in results.iter().enumerate() {
                let rrf_score = 1.0 / (self.k + (rank + 1) as f64);
                
                *scores.entry(id.clone()).or_insert(0.0) += rrf_score;
                
                source_scores_map
                    .entry(id.clone())
                    .or_insert_with(|| vec![0.0; result_lists.len()])[list_idx] = rrf_score;
            }
        }
        
        let mut results: Vec<FusionResult> = scores
            .into_iter()
            .map(|(id, score)| {
                let source_scores = source_scores_map.get(&id).cloned().unwrap_or_default();
                FusionResult {
                    id,
                    score,
                    rank: 0,
                    source_scores,
                }
            })
            .collect();
        
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
        
        for (rank, result) in results.iter_mut().enumerate() {
            result.rank = rank + 1;
        }
        
        results
    }

    fn fuse_with_weights(&self, result_lists: Vec<Vec<String>>, weights: Vec<f64>) -> Vec<FusionResult> {
        let mut scores: HashMap<String, f64> = HashMap::new();
        let mut source_scores_map: HashMap<String, Vec<f64>> = HashMap::new();
        
        for (list_idx, results) in result_lists.iter().enumerate() {
            let weight = weights.get(list_idx).copied().unwrap_or(1.0);
            
            for (rank, id) in results.iter().enumerate() {
                let rrf_score = weight / (self.k + (rank + 1) as f64);
                
                *scores.entry(id.clone()).or_insert(0.0) += rrf_score;
                
                source_scores_map
                    .entry(id.clone())
                    .or_insert_with(|| vec![0.0; result_lists.len()])[list_idx] = rrf_score;
            }
        }
        
        let mut results: Vec<FusionResult> = scores
            .into_iter()
            .map(|(id, score)| {
                let source_scores = source_scores_map.get(&id).cloned().unwrap_or_default();
                FusionResult {
                    id,
                    score,
                    rank: 0,
                    source_scores,
                }
            })
            .collect();
        
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
        
        for (rank, result) in results.iter_mut().enumerate() {
            result.rank = rank + 1;
        }
        
        results
    }

    fn get_k(&self) -> f64 {
        self.k
    }

    fn set_k(&mut self, k: f64) {
        self.k = k;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fusion_creation() {
        let fusion = PyRRFFusion::new(Some(60.0));
        assert_eq!(fusion.get_k(), 60.0);
    }

    #[test]
    fn test_basic_fusion() {
        let fusion = PyRRFFusion::new(Some(60.0));
        
        let list1 = vec!["a".to_string(), "b".to_string(), "c".to_string()];
        let list2 = vec!["b".to_string(), "c".to_string(), "a".to_string()];
        
        let results = fusion.fuse(vec![list1, list2]);
        
        assert!(!results.is_empty());
        assert!(results[0].score > 0.0);
    }

    #[test]
    fn test_weighted_fusion() {
        let fusion = PyRRFFusion::new(Some(60.0));
        
        let list1 = vec!["a".to_string(), "b".to_string()];
        let list2 = vec!["b".to_string(), "a".to_string()];
        
        let results = fusion.fuse_with_weights(vec![list1, list2], vec![2.0, 1.0]);
        
        assert!(!results.is_empty());
    }

    #[test]
    fn test_ranking() {
        let fusion = PyRRFFusion::new(Some(60.0));
        
        let list1 = vec!["a".to_string(), "b".to_string(), "c".to_string()];
        let results = fusion.fuse(vec![list1]);
        
        assert_eq!(results[0].rank, 1);
        assert_eq!(results[1].rank, 2);
        assert_eq!(results[2].rank, 3);
    }
}
