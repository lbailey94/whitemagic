//! Embedding engine with text processing and normalization
//!
//! This module provides embedding generation for text, with support for
//! batch processing, normalization, and similarity computations.

use numpy::PyArray1;
use pyo3::prelude::*;
use std::collections::HashMap;

/// Configuration for embedding generation
#[derive(Debug, Clone)]
pub struct EmbeddingConfig {
    /// Embedding dimension (384 for BGE-small-en-v1.5)
    pub dimension: usize,
    /// Whether to normalize embeddings
    pub normalize: bool,
    /// Maximum sequence length
    pub max_length: usize,
    /// Whether to lowercase text
    pub lowercase: bool,
}

impl Default for EmbeddingConfig {
    fn default() -> Self {
        Self {
            dimension: 768, // Standard dimension for base models
            normalize: true,
            max_length: 512,
            lowercase: true,
        }
    }
}

/// Rust embedding engine with PyO3
/// Target: 50x speedup on BGE embedding generation
#[pyclass]
pub struct EmbeddingEngine {
    /// Model path for loading weights
    model_path: String,
    /// Configuration
    config: EmbeddingConfig,
    /// Vocabulary for tokenization (simplified)
    vocab: HashMap<String, usize>,
    /// Token embeddings (simplified - in production would load from model)
    token_embeddings: Vec<Vec<f32>>,
}

#[pymethods]
impl EmbeddingEngine {
    /// Create a new embedding engine with the specified model path
    #[new]
    fn new(model_path: String) -> Self {
        Self {
            model_path,
            config: EmbeddingConfig::default(),
            vocab: Self::build_default_vocab(),
            token_embeddings: Self::init_default_embeddings(),
        }
    }

    /// Create engine with custom configuration
    #[staticmethod]
    fn with_config(model_path: String, dimension: usize, normalize: bool) -> Self {
        let config = EmbeddingConfig {
            dimension,
            normalize,
            ..EmbeddingConfig::default()
        };
        Self {
            model_path,
            config,
            vocab: Self::build_default_vocab(),
            token_embeddings: Self::init_default_embeddings(),
        }
    }

    /// Generate embedding for a single text
    fn generate_embedding<'py>(
        &self,
        py: Python<'py>,
        text: String,
    ) -> PyResult<Bound<'py, PyArray1<f32>>> {
        let embedding = self.compute_embedding(&text);
        Ok(PyArray1::from_vec_bound(py, embedding))
    }

    /// Generate embeddings for multiple texts (batch processing)
    /// Returns a flat vector with shape info (n_texts, dimension)
    fn generate_embeddings_flat(&self, texts: Vec<String>) -> (Vec<f32>, usize, usize) {
        let batch: Vec<Vec<f32>> = texts.iter().map(|t| self.compute_embedding(t)).collect();

        let n = batch.len();
        let d = self.config.dimension;
        let mut flat = vec![0.0f32; n * d];

        for (i, emb) in batch.iter().enumerate() {
            for (j, &v) in emb.iter().enumerate() {
                flat[i * d + j] = v;
            }
        }

        (flat, n, d)
    }

    /// Compute cosine similarity between two texts
    fn similarity(&self, text1: String, text2: String) -> f32 {
        let emb1 = self.compute_embedding(&text1);
        let emb2 = self.compute_embedding(&text2);
        cosine_similarity(&emb1, &emb2)
    }

    /// Compute similarity matrix for multiple texts
    fn similarity_matrix(&self, texts: Vec<String>) -> Vec<f32> {
        let embeddings: Vec<Vec<f32>> = texts.iter().map(|t| self.compute_embedding(t)).collect();

        let n = texts.len();
        let mut matrix = vec![0.0f32; n * n];

        for i in 0..n {
            for j in 0..n {
                matrix[i * n + j] = cosine_similarity(&embeddings[i], &embeddings[j]);
            }
        }

        matrix
    }

    /// Get model path
    fn get_model_path(&self) -> String {
        self.model_path.clone()
    }

    /// Get embedding dimension
    fn get_dimension(&self) -> usize {
        self.config.dimension
    }

    /// Get configuration
    fn get_config(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("dimension", self.config.dimension)?;
        dict.set_item("normalize", self.config.normalize)?;
        dict.set_item("max_length", self.config.max_length)?;
        dict.set_item("lowercase", self.config.lowercase)?;
        Ok(dict.into())
    }

    /// Tokenize text into tokens
    fn tokenize(&self, text: String) -> Vec<usize> {
        self.tokenize_text(&text)
    }

    /// Get vocabulary size
    fn vocab_size(&self) -> usize {
        self.vocab.len()
    }
}

impl EmbeddingEngine {
    /// Build a default vocabulary for basic tokenization
    fn build_default_vocab() -> HashMap<String, usize> {
        // Basic vocabulary with common tokens
        let mut vocab = HashMap::new();
        vocab.insert("[PAD]".to_string(), 0);
        vocab.insert("[UNK]".to_string(), 1);
        vocab.insert("[CLS]".to_string(), 2);
        vocab.insert("[SEP]".to_string(), 3);

        // Add some basic word tokens
        for (i, word) in [
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has",
            "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must",
            "shall", "can", "need", "dare", "ought", "used", "to", "of", "in", "for", "on", "with",
            "at", "by", "from", "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "under", "and", "but", "or", "nor", "so", "yet", "both", "either",
            "neither", "not", "memory", "system", "data", "process", "function", "method", "class",
            "object",
        ]
        .iter()
        .enumerate()
        {
            vocab.insert(word.to_string(), i + 4);
        }

        vocab
    }

    /// Initialize default token embeddings
    fn init_default_embeddings() -> Vec<Vec<f32>> {
        // Initialize with small random-like values (deterministic for consistency)
        // Use 384 for BGE-small-en-v1.5
        let dim = 384;
        let vocab_size = 100;

        (0..vocab_size)
            .map(|i| {
                (0..dim)
                    .map(|j| {
                        // Deterministic pseudo-random based on indices

                        ((i * 1337 + j * 7919) as f64 / 10000.0).sin() as f32 * 0.1
                    })
                    .collect()
            })
            .collect()
    }

    /// Tokenize text into token IDs
    fn tokenize_text(&self, text: &str) -> Vec<usize> {
        let text = if self.config.lowercase {
            text.to_lowercase()
        } else {
            text.to_string()
        };

        // Simple whitespace tokenization
        let words: Vec<&str> = text
            .split_whitespace()
            .take(self.config.max_length)
            .collect();

        let mut tokens = vec![2]; // [CLS]

        for word in words {
            let token_id = self.vocab.get(word).copied().unwrap_or(1); // [UNK] if not found
            tokens.push(token_id);
        }

        tokens.push(3); // [SEP]
        tokens
    }

    /// Compute embedding from text
    fn compute_embedding(&self, text: &str) -> Vec<f32> {
        let tokens = self.tokenize_text(text);
        let dim = self.config.dimension;

        // Average pooling of token embeddings
        let mut embedding = vec![0.0f32; dim];
        let mut count = 0;

        for &token_id in &tokens {
            if token_id < self.token_embeddings.len() {
                for (i, &v) in self.token_embeddings[token_id].iter().enumerate() {
                    embedding[i] += v;
                }
                count += 1;
            }
        }

        if count > 0 {
            for v in embedding.iter_mut() {
                *v /= count as f32;
            }
        }

        // Normalize if configured
        if self.config.normalize {
            normalize_vector(&mut embedding);
        }

        embedding
    }
}

/// Normalize a vector to unit length
fn normalize_vector(v: &mut [f32]) {
    let norm: f32 = v.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm > 0.0 {
        for x in v.iter_mut() {
            *x /= norm;
        }
    }
}

/// Compute cosine similarity between two vectors
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }

    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();

    let denom = norm_a * norm_b;
    if denom > 0.0 {
        dot / denom
    } else {
        0.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_creation() {
        let engine = EmbeddingEngine::new("test_model".to_string());
        assert_eq!(engine.get_dimension(), 768);
    }

    #[test]
    fn test_embedding_generation() {
        let engine = EmbeddingEngine::new("test_model".to_string());
        let emb = engine.compute_embedding("hello world");
        assert_eq!(emb.len(), 768);

        // Check normalization
        let norm: f32 = emb.iter().map(|x| x * x).sum::<f32>().sqrt();
        assert!((norm - 1.0).abs() < 1e-5);
    }

    #[test]
    fn test_similarity() {
        let engine = EmbeddingEngine::new("test_model".to_string());

        // Same text should have similarity 1.0
        let sim = engine.similarity("test".to_string(), "test".to_string());
        assert!((sim - 1.0).abs() < 1e-5);
    }

    #[test]
    fn test_tokenization() {
        let engine = EmbeddingEngine::new("test_model".to_string());
        let tokens = engine.tokenize("the memory system".to_string());

        // Should have [CLS], tokens, [SEP]
        assert!(tokens.len() >= 2);
        assert_eq!(tokens[0], 2); // [CLS]
        assert_eq!(*tokens.last().unwrap(), 3); // [SEP]
    }
}
