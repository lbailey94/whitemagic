//! Unified Search Engine - PSR-002 (30-100× speedup)
//!
//! Consolidates lexical (BM25), semantic (vector), and hybrid search
//! into a single high-performance Rust engine.

use pyo3::prelude::*;
use std::collections::HashMap;

/// Search result with score and metadata
#[derive(Clone, Debug)]
pub struct SearchResult {
    pub memory_id: String,
    pub score: f32,
    pub rank: usize,
    pub source: SearchSource,
}

/// Search source indicator
#[derive(Clone, Debug, PartialEq)]
pub enum SearchSource {
    Lexical,   // BM25/FTS
    Semantic,  // Vector similarity
    Hybrid,    // RRF fusion
    Graph,     // Graph walk
}

/// Unified search engine
pub struct SearchEngine {
    bm25_k1: f32,
    bm25_b: f32,
    rrf_k: f32,
}

impl SearchEngine {
    pub fn new() -> Self {
        Self {
            bm25_k1: 1.5,
            bm25_b: 0.75,
            rrf_k: 60.0,
        }
    }

    /// BM25 scoring formula
    /// score = IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D| / avgdl))
    pub fn bm25_score(
        &self,
        term_freq: f32,
        doc_length: f32,
        avg_doc_length: f32,
        idf: f32,
    ) -> f32 {
        let k1 = self.bm25_k1;
        let b = self.bm25_b;
        
        let norm_length = 1.0 - b + b * (doc_length / avg_doc_length);
        let numerator = term_freq * (k1 + 1.0);
        let denominator = term_freq + k1 * norm_length;
        
        idf * (numerator / denominator)
    }

    /// Reciprocal Rank Fusion (RRF) for combining multiple rankings
    /// score(d) = Σ 1 / (k + rank(d))
    pub fn rrf_fusion(&self, rankings: &[Vec<String>]) -> Vec<(String, f32)> {
        let mut scores: HashMap<String, f32> = HashMap::new();
        
        for ranking in rankings {
            for (rank, doc_id) in ranking.iter().enumerate() {
                let score = 1.0 / (self.rrf_k + (rank as f32 + 1.0));
                *scores.entry(doc_id.clone()).or_insert(0.0) += score;
            }
        }
        
        let mut results: Vec<(String, f32)> = scores.into_iter().collect();
        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        results
    }

    /// Cosine similarity between two vectors
    pub fn cosine_similarity(&self, a: &[f32], b: &[f32]) -> f32 {
        if a.len() != b.len() {
            return 0.0;
        }
        
        let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
        let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
        
        if norm_a == 0.0 || norm_b == 0.0 {
            return 0.0;
        }
        
        dot / (norm_a * norm_b)
    }

    /// Batch cosine similarity (SIMD-friendly)
    pub fn cosine_similarity_batch(&self, query: &[f32], documents: &[Vec<f32>]) -> Vec<f32> {
        documents
            .iter()
            .map(|doc| self.cosine_similarity(query, doc))
            .collect()
    }
}

impl Default for SearchEngine {
    fn default() -> Self {
        Self::new()
    }
}

// Python bindings
#[pyclass]
pub struct PySearchEngine {
    engine: SearchEngine,
}

#[pymethods]
impl PySearchEngine {
    #[new]
    fn new() -> Self {
        Self {
            engine: SearchEngine::new(),
        }
    }

    /// Compute BM25 score
    fn bm25_score(
        &self,
        term_freq: f32,
        doc_length: f32,
        avg_doc_length: f32,
        idf: f32,
    ) -> f32 {
        self.engine.bm25_score(term_freq, doc_length, avg_doc_length, idf)
    }

    /// Fuse multiple rankings with RRF
    fn rrf_fusion(&self, rankings: Vec<Vec<String>>) -> Vec<(String, f32)> {
        self.engine.rrf_fusion(&rankings)
    }

    /// Cosine similarity between two vectors
    fn cosine_similarity(&self, a: Vec<f32>, b: Vec<f32>) -> f32 {
        self.engine.cosine_similarity(&a, &b)
    }

    /// Batch cosine similarity
    fn cosine_similarity_batch(&self, query: Vec<f32>, documents: Vec<Vec<f32>>) -> Vec<f32> {
        self.engine.cosine_similarity_batch(&query, &documents)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bm25_score() {
        let engine = SearchEngine::new();
        let score = engine.bm25_score(
            3.0,   // term appears 3 times
            100.0, // document has 100 terms
            150.0, // average document has 150 terms
            2.5,   // IDF value
        );
        assert!(score > 0.0);
        assert!(score < 10.0);
    }

    #[test]
    fn test_rrf_fusion() {
        let engine = SearchEngine::new();
        let rankings = vec![
            vec!["doc1".to_string(), "doc2".to_string(), "doc3".to_string()],
            vec!["doc2".to_string(), "doc1".to_string(), "doc4".to_string()],
            vec!["doc1".to_string(), "doc3".to_string(), "doc2".to_string()],
        ];
        
        let fused = engine.rrf_fusion(&rankings);
        
        // doc1 appears in all 3 rankings highly, should be top
        assert_eq!(fused[0].0, "doc1");
        assert!(fused[0].1 > fused[1].1);
    }

    #[test]
    fn test_cosine_similarity() {
        let engine = SearchEngine::new();
        
        // Identical vectors
        let a = vec![1.0, 2.0, 3.0];
        let b = vec![1.0, 2.0, 3.0];
        let sim = engine.cosine_similarity(&a, &b);
        assert!((sim - 1.0).abs() < 0.001);
        
        // Orthogonal vectors
        let c = vec![1.0, 0.0];
        let d = vec![0.0, 1.0];
        let sim2 = engine.cosine_similarity(&c, &d);
        assert!(sim2.abs() < 0.001);
    }

    #[test]
    fn test_cosine_batch() {
        let engine = SearchEngine::new();
        let query = vec![1.0, 2.0, 3.0];
        let docs = vec![
            vec![1.0, 2.0, 3.0],
            vec![2.0, 4.0, 6.0],
            vec![0.0, 0.0, 0.0],
        ];
        
        let sims = engine.cosine_similarity_batch(&query, &docs);
        assert_eq!(sims.len(), 3);
        assert!((sims[0] - 1.0).abs() < 0.001); // Identical
        assert!(sims[1] > 0.9); // Similar direction
        assert_eq!(sims[2], 0.0); // Zero vector
    }
}
