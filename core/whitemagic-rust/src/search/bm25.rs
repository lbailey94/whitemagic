//! BM25 Ranking - Advanced Lexical Search (PSR-002)
//!
//! Implements BM25 with field boosting, title weighting, and batch processing.
//! Target: 20-50× speedup over Python implementation.

use pyo3::prelude::*;
use std::collections::HashMap;

/// BM25 scorer with configurable parameters
pub struct BM25Scorer {
    k1: f32,
    b: f32,
    avg_doc_length: f32,
    idf_cache: HashMap<String, f32>,
}

impl BM25Scorer {
    pub fn new(k1: f32, b: f32, avg_doc_length: f32) -> Self {
        Self {
            k1,
            b,
            avg_doc_length,
            idf_cache: HashMap::new(),
        }
    }

    /// Compute IDF (Inverse Document Frequency)
    /// IDF(qi) = log((N - n(qi) + 0.5) / (n(qi) + 0.5))
    pub fn compute_idf(&mut self, term: &str, doc_count: usize, term_doc_count: usize) -> f32 {
        if let Some(&cached) = self.idf_cache.get(term) {
            return cached;
        }

        let n = doc_count as f32;
        let df = term_doc_count as f32;
        let idf = ((n - df + 0.5) / (df + 0.5)).ln();
        
        self.idf_cache.insert(term.to_string(), idf);
        idf
    }

    /// Score a single term in a document
    /// score = IDF(qi) * (f(qi, D) * (k1 + 1)) / (f(qi, D) + k1 * (1 - b + b * |D| / avgdl))
    pub fn score_term(
        &self,
        term_freq: f32,
        doc_length: f32,
        idf: f32,
    ) -> f32 {
        let norm_length = 1.0 - self.b + self.b * (doc_length / self.avg_doc_length);
        let numerator = term_freq * (self.k1 + 1.0);
        let denominator = term_freq + self.k1 * norm_length;
        
        idf * (numerator / denominator)
    }

    /// Score a document with field boosting
    /// Supports title boost, content boost, etc.
    pub fn score_document(
        &self,
        term_freqs: &HashMap<String, f32>,
        doc_length: f32,
        idfs: &HashMap<String, f32>,
        field_boost: f32,
    ) -> f32 {
        let mut score = 0.0;
        
        for (term, &freq) in term_freqs {
            if let Some(&idf) = idfs.get(term) {
                score += self.score_term(freq, doc_length, idf);
            }
        }
        
        score * field_boost
    }

    /// Batch score multiple documents
    pub fn score_batch(
        &self,
        documents: &[(HashMap<String, f32>, f32)], // (term_freqs, doc_length)
        idfs: &HashMap<String, f32>,
    ) -> Vec<f32> {
        documents
            .iter()
            .map(|(term_freqs, doc_length)| {
                self.score_document(term_freqs, *doc_length, idfs, 1.0)
            })
            .collect()
    }

    /// Multi-field BM25 with different boosts
    pub fn score_multifield(
        &self,
        title_terms: &HashMap<String, f32>,
        title_length: f32,
        content_terms: &HashMap<String, f32>,
        content_length: f32,
        idfs: &HashMap<String, f32>,
        title_boost: f32,
        content_boost: f32,
    ) -> f32 {
        let title_score = self.score_document(title_terms, title_length, idfs, title_boost);
        let content_score = self.score_document(content_terms, content_length, idfs, content_boost);
        title_score + content_score
    }
}

impl Default for BM25Scorer {
    fn default() -> Self {
        Self::new(1.5, 0.75, 150.0)
    }
}

// Python bindings
#[pyclass]
pub struct PyBM25Scorer {
    scorer: BM25Scorer,
}

#[pymethods]
impl PyBM25Scorer {
    #[new]
    #[pyo3(signature = (k1=1.5, b=0.75, avg_doc_length=150.0))]
    fn new(k1: f32, b: f32, avg_doc_length: f32) -> Self {
        Self {
            scorer: BM25Scorer::new(k1, b, avg_doc_length),
        }
    }

    /// Compute IDF for a term
    fn compute_idf(&mut self, term: String, doc_count: usize, term_doc_count: usize) -> f32 {
        self.scorer.compute_idf(&term, doc_count, term_doc_count)
    }

    /// Score a single term
    fn score_term(&self, term_freq: f32, doc_length: f32, idf: f32) -> f32 {
        self.scorer.score_term(term_freq, doc_length, idf)
    }

    /// Score a document
    fn score_document(
        &self,
        term_freqs: HashMap<String, f32>,
        doc_length: f32,
        idfs: HashMap<String, f32>,
        field_boost: f32,
    ) -> f32 {
        self.scorer.score_document(&term_freqs, doc_length, &idfs, field_boost)
    }

    /// Score multi-field document (title + content)
    fn score_multifield(
        &self,
        title_terms: HashMap<String, f32>,
        title_length: f32,
        content_terms: HashMap<String, f32>,
        content_length: f32,
        idfs: HashMap<String, f32>,
        title_boost: f32,
        content_boost: f32,
    ) -> f32 {
        self.scorer.score_multifield(
            &title_terms,
            title_length,
            &content_terms,
            content_length,
            &idfs,
            title_boost,
            content_boost,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_idf_computation() {
        let mut scorer = BM25Scorer::default();
        let idf = scorer.compute_idf("test", 1000, 10);
        assert!(idf > 0.0);
        
        // Should be cached
        let idf2 = scorer.compute_idf("test", 1000, 10);
        assert_eq!(idf, idf2);
    }

    #[test]
    fn test_term_scoring() {
        let scorer = BM25Scorer::default();
        let score = scorer.score_term(3.0, 100.0, 2.5);
        assert!(score > 0.0);
        assert!(score < 10.0);
    }

    #[test]
    fn test_document_scoring() {
        let scorer = BM25Scorer::default();
        let mut term_freqs = HashMap::new();
        term_freqs.insert("rust".to_string(), 3.0);
        term_freqs.insert("fast".to_string(), 2.0);
        
        let mut idfs = HashMap::new();
        idfs.insert("rust".to_string(), 2.5);
        idfs.insert("fast".to_string(), 2.0);
        
        let score = scorer.score_document(&term_freqs, 100.0, &idfs, 1.0);
        assert!(score > 0.0);
    }

    #[test]
    fn test_multifield_scoring() {
        let scorer = BM25Scorer::default();
        
        let mut title_terms = HashMap::new();
        title_terms.insert("rust".to_string(), 1.0);
        
        let mut content_terms = HashMap::new();
        content_terms.insert("rust".to_string(), 5.0);
        content_terms.insert("programming".to_string(), 3.0);
        
        let mut idfs = HashMap::new();
        idfs.insert("rust".to_string(), 2.5);
        idfs.insert("programming".to_string(), 2.0);
        
        let score = scorer.score_multifield(
            &title_terms, 5.0,
            &content_terms, 100.0,
            &idfs,
            5.0,  // Title boost
            1.0,  // Content boost
        );
        
        assert!(score > 0.0);
        // Title should contribute more due to boost
    }
}
