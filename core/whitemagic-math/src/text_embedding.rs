//! Lightweight text embedding via feature hashing.
//!
//! Generates fixed-dimensional embeddings suitable for semantic similarity
//! in the browser via WASM. No ML model required — uses normalized
//! feature hashing over token n-grams.
//!
//! Dimension: 384 (matches MiniLM-L6 output dim for potential future compatibility).

#![allow(dead_code)]

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

use sha2::{Digest, Sha256};

/// Default embedding dimension (matches all-MiniLM-L6-v2).
pub const EMBED_DIM: usize = 384;

/// Generate a text embedding via feature hashing over token unigrams + bigrams.
///
/// Each token/bigram is hashed to a dimension, with sign hashing to reduce
/// collision bias. The final vector is L2-normalized.
pub fn embed_text(text: &str, dim: usize) -> Vec<f32> {
    let tokens = tokenize(text);
    if tokens.is_empty() {
        return vec![0.0; dim];
    }

    let mut vec = vec![0.0f32; dim];

    // Unigram features
    for token in &tokens {
        let (idx, sign) = hash_feature(token, dim);
        vec[idx] += sign * 1.0;
    }

    // Bigram features (captures word order)
    for window in tokens.windows(2) {
        let bigram = format!("{}~{}", window[0], window[1]);
        let (idx, sign) = hash_feature(&bigram, dim);
        vec[idx] += sign * 0.7; // bigrams weighted slightly less
    }

    // L2 normalize
    let norm: f32 = vec.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm > 0.0 {
        for x in vec.iter_mut() {
            *x /= norm;
        }
    }

    vec
}

/// Tokenize text into lowercase alphanumeric tokens.
fn tokenize(text: &str) -> Vec<String> {
    text.to_lowercase()
        .split(|c: char| !c.is_alphanumeric())
        .filter(|s| !s.is_empty() && s.len() > 1)
        .map(|s| s.to_string())
        .collect()
}

/// Hash a feature string to (index, sign) using SHA256.
fn hash_feature(feature: &str, dim: usize) -> (usize, f32) {
    let mut hasher = Sha256::new();
    hasher.update(feature.as_bytes());
    let bytes = hasher.finalize();

    // First 8 bytes for index, next byte for sign
    let idx_bytes: [u8; 8] = bytes[..8].try_into().unwrap();
    let idx = u64::from_le_bytes(idx_bytes) as usize % dim;
    let sign = if bytes[8] & 1 == 0 { 1.0 } else { -1.0 };

    (idx, sign)
}

/// Cosine similarity between two vectors.
pub fn cosine_sim(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
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

/// Batch embed multiple texts and return as a flat vector (row-major).
pub fn embed_batch(texts: &[&str], dim: usize) -> Vec<Vec<f32>> {
    texts.iter().map(|t| embed_text(t, dim)).collect()
}

/// Find top-k most similar texts to a query.
pub fn top_k_similar(
    query: &[f32],
    candidates: &[Vec<f32>],
    k: usize,
) -> Vec<(usize, f32)> {
    let mut scores: Vec<(usize, f32)> = candidates
        .iter()
        .enumerate()
        .map(|(i, c)| (i, cosine_sim(query, c)))
        .collect();

    scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scores.truncate(k);
    scores
}

// ── WASM bindings ───────────────────────────────────────────────────────

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn embed_text_wasm(text: &str, dim: usize) -> String {
    let vec = embed_text(text, dim);
    serde_json::to_string(&vec).unwrap_or_else(|_| "[]".to_string())
}

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn embed_batch_wasm(texts_json: &str, dim: usize) -> String {
    let texts: Vec<String> = serde_json::from_str(texts_json).unwrap_or_default();
    let refs: Vec<&str> = texts.iter().map(|s| s.as_str()).collect();
    let vecs = embed_batch(&refs, dim);
    serde_json::to_string(&vecs).unwrap_or_else(|_| "[]".to_string())
}

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn cosine_sim_wasm(a_json: &str, b_json: &str) -> f32 {
    let a: Vec<f32> = serde_json::from_str(a_json).unwrap_or_default();
    let b: Vec<f32> = serde_json::from_str(b_json).unwrap_or_default();
    cosine_sim(&a, &b)
}

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn top_k_similar_wasm(query_json: &str, candidates_json: &str, k: usize) -> String {
    let query: Vec<f32> = serde_json::from_str(query_json).unwrap_or_default();
    let candidates: Vec<Vec<f32>> = serde_json::from_str(candidates_json).unwrap_or_default();
    let results = top_k_similar(&query, &candidates, k);
    serde_json::to_string(
        &results.iter().map(|(i, s)| serde_json::json!({"index": i, "score": s})).collect::<Vec<_>>(),
    )
    .unwrap_or_else(|_| "[]".to_string())
}

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn embed_dim() -> usize {
    EMBED_DIM
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_embed_basic() {
        let vec = embed_text("hello world", 384);
        assert_eq!(vec.len(), 384);
        // Should be normalized
        let norm: f32 = vec.iter().map(|x| x * x).sum::<f32>().sqrt();
        assert!((norm - 1.0).abs() < 0.01, "Not normalized: {}", norm);
    }

    #[test]
    fn test_embed_empty() {
        let vec = embed_text("", 384);
        assert_eq!(vec.len(), 384);
        assert!(vec.iter().all(|x| *x == 0.0));
    }

    #[test]
    fn test_embed_similarity_same() {
        let a = embed_text("rust programming language", 384);
        let b = embed_text("rust programming language", 384);
        let sim = cosine_sim(&a, &b);
        assert!((sim - 1.0).abs() < 0.01, "Same text sim: {}", sim);
    }

    #[test]
    fn test_embed_similarity_related() {
        let a = embed_text("rust programming language", 384);
        let b = embed_text("rust coding language", 384);
        let sim = cosine_sim(&a, &b);
        assert!(sim > 0.5, "Related texts sim too low: {}", sim);
    }

    #[test]
    fn test_embed_similarity_unrelated() {
        let a = embed_text("rust programming language", 384);
        let b = embed_text("cooking pasta recipe italian", 384);
        let sim = cosine_sim(&a, &b);
        assert!(sim < 0.3, "Unrelated texts sim too high: {}", sim);
    }

    #[test]
    fn test_top_k_similar() {
        let query = embed_text("machine learning model", 384);
        let candidates = vec![
            embed_text("machine learning AI", 384),
            embed_text("cooking pasta recipe", 384),
            embed_text("deep learning neural network", 384),
        ];
        let results = top_k_similar(&query, &candidates, 2);
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].0, 0); // "machine learning AI" should be best
    }

    #[test]
    fn test_batch_embed() {
        let texts = ["hello world", "foo bar"];
        let refs: Vec<&str> = texts.iter().copied().collect();
        let vecs = embed_batch(&refs, 128);
        assert_eq!(vecs.len(), 2);
        assert_eq!(vecs[0].len(), 128);
    }
}
