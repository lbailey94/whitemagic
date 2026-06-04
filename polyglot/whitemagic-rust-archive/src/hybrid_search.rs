//! Hybrid Search - Lexical + Semantic Fusion (PSR-002)
//! Target: 30× speedup over Python hybrid search

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
#[pyclass]
pub struct SearchResult {
    #[pyo3(get)]
    pub doc_id: String,
    #[pyo3(get)]
    pub score: f64,
    #[pyo3(get)]
    pub lexical_score: f64,
    #[pyo3(get)]
    pub semantic_score: f64,
}

#[pymethods]
impl SearchResult {
    #[new]
    fn new(doc_id: String, score: f64, lexical_score: f64, semantic_score: f64) -> Self {
        Self {
            doc_id,
            score,
            lexical_score,
            semantic_score,
        }
    }
}

#[pyclass]
pub struct PyHybridSearch {
    lexical_weight: f64,
    semantic_weight: f64,
}

#[pymethods]
impl PyHybridSearch {
    #[new]
    fn new(lexical_weight: Option<f64>, semantic_weight: Option<f64>) -> Self {
        Self {
            lexical_weight: lexical_weight.unwrap_or(0.5),
            semantic_weight: semantic_weight.unwrap_or(0.5),
        }
    }

    fn fuse_results(
        &self,
        lexical_results: Vec<(String, f64)>,
        semantic_results: Vec<(String, f64)>,
    ) -> Vec<SearchResult> {
        let mut scores: HashMap<String, (f64, f64)> = HashMap::new();

        // Normalize and weight lexical scores
        let max_lex = lexical_results.iter().map(|(_, s)| s).fold(0.0f64, |a, &b| a.max(b));
        for (doc_id, score) in lexical_results {
            let norm_score = if max_lex > 0.0 { score / max_lex } else { 0.0 };
            scores.entry(doc_id).or_insert((0.0, 0.0)).0 = norm_score;
        }

        // Normalize and weight semantic scores
        let max_sem = semantic_results.iter().map(|(_, s)| s).fold(0.0f64, |a, &b| a.max(b));
        for (doc_id, score) in semantic_results {
            let norm_score = if max_sem > 0.0 { score / max_sem } else { 0.0 };
            scores.entry(doc_id).or_insert((0.0, 0.0)).1 = norm_score;
        }

        // Combine scores
        let mut results: Vec<SearchResult> = scores
            .into_iter()
            .map(|(doc_id, (lex, sem))| {
                let combined = lex * self.lexical_weight + sem * self.semantic_weight;
                SearchResult {
                    doc_id,
                    score: combined,
                    lexical_score: lex,
                    semantic_score: sem,
                }
            })
            .collect();

        // Sort by combined score descending
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
        results
    }

    fn rrf_fusion(
        &self,
        lexical_results: Vec<(String, f64)>,
        semantic_results: Vec<(String, f64)>,
        k: Option<f64>,
    ) -> Vec<SearchResult> {
        let k_val = k.unwrap_or(60.0);
        let mut rrf_scores: HashMap<String, f64> = HashMap::new();
        let mut lex_scores: HashMap<String, f64> = HashMap::new();
        let mut sem_scores: HashMap<String, f64> = HashMap::new();

        // RRF for lexical results
        for (rank, (doc_id, score)) in lexical_results.iter().enumerate() {
            let rrf = 1.0 / (k_val + (rank + 1) as f64);
            *rrf_scores.entry(doc_id.clone()).or_insert(0.0) += rrf * self.lexical_weight;
            lex_scores.insert(doc_id.clone(), *score);
        }

        // RRF for semantic results
        for (rank, (doc_id, score)) in semantic_results.iter().enumerate() {
            let rrf = 1.0 / (k_val + (rank + 1) as f64);
            *rrf_scores.entry(doc_id.clone()).or_insert(0.0) += rrf * self.semantic_weight;
            sem_scores.insert(doc_id.clone(), *score);
        }

        // Convert to results
        let mut results: Vec<SearchResult> = rrf_scores
            .into_iter()
            .map(|(doc_id, score)| SearchResult {
                doc_id: doc_id.clone(),
                score,
                lexical_score: *lex_scores.get(&doc_id).unwrap_or(&0.0),
                semantic_score: *sem_scores.get(&doc_id).unwrap_or(&0.0),
            })
            .collect();

        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
        results
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fuse_results() {
        let searcher = PyHybridSearch::new(Some(0.5), Some(0.5));
        
        let lexical = vec![
            ("doc1".to_string(), 10.0),
            ("doc2".to_string(), 5.0),
        ];
        
        let semantic = vec![
            ("doc1".to_string(), 0.9),
            ("doc3".to_string(), 0.8),
        ];
        
        let results = searcher.fuse_results(lexical, semantic);
        
        assert!(results.len() >= 2);
        assert_eq!(results[0].doc_id, "doc1"); // Should rank highest
    }

    #[test]
    fn test_rrf_fusion() {
        let searcher = PyHybridSearch::new(Some(0.5), Some(0.5));
        
        let lexical = vec![
            ("doc1".to_string(), 10.0),
            ("doc2".to_string(), 5.0),
        ];
        
        let semantic = vec![
            ("doc2".to_string(), 0.9),
            ("doc1".to_string(), 0.8),
        ];
        
        let results = searcher.rrf_fusion(lexical, semantic, Some(60.0));
        
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_weights() {
        let searcher = PyHybridSearch::new(Some(0.8), Some(0.2));
        
        assert_eq!(searcher.lexical_weight, 0.8);
        assert_eq!(searcher.semantic_weight, 0.2);
    }

    #[test]
    fn test_empty_results() {
        let searcher = PyHybridSearch::new(None, None);
        
        let results = searcher.fuse_results(vec![], vec![]);
        
        assert_eq!(results.len(), 0);
    }
}
