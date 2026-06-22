//! Embedding-based MinHash for fast duplicate detection
//! Decoupled for WASM compatibility.

use serde::Serialize;
use std::collections::{hash_map::DefaultHasher, HashMap, HashSet};
use std::hash::{Hash, Hasher};

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

const NUM_HASHES: usize = 128;
const LARGE_PRIME: u64 = 4294967311;

#[derive(Debug, Clone, Serialize)]
pub struct EmbeddingSignature {
    pub values: Vec<u64>,
}

fn hash_params(seed: usize) -> (u64, u64) {
    let a = (seed as u64 * 2654435761) % LARGE_PRIME;
    let b = (seed as u64 * 2246822519) % LARGE_PRIME;
    (a, b)
}

fn hash_dimension(dim: usize, value: f32, a: u64, b: u64) -> u64 {
    let mut hasher = DefaultHasher::new();
    dim.hash(&mut hasher);
    let quantized = (value * 1000.0) as i32;
    quantized.hash(&mut hasher);
    let h = hasher.finish();
    (a.wrapping_mul(h) + b) % LARGE_PRIME
}

pub fn compute_embedding_signature(embedding: &[f32]) -> EmbeddingSignature {
    let mut min_values = vec![u64::MAX; NUM_HASHES];
    for hash_idx in 0..NUM_HASHES {
        let (a, b) = hash_params(hash_idx);
        for (dim, &value) in embedding.iter().enumerate() {
            if value.abs() > 0.01 {
                let h = hash_dimension(dim, value, a, b);
                if h < min_values[hash_idx] {
                    min_values[hash_idx] = h;
                }
            }
        }
    }
    EmbeddingSignature { values: min_values }
}

#[derive(Debug, Clone, Serialize)]
pub struct EmbeddingDuplicate {
    pub idx_a: usize,
    pub idx_b: usize,
    pub similarity: f64,
}

pub fn estimate_similarity(a: &EmbeddingSignature, b: &EmbeddingSignature) -> f64 {
    let matches = a.values.iter().zip(b.values.iter()).filter(|(x, y)| x == y).count();
    matches as f64 / NUM_HASHES as f64
}

pub fn find_embedding_duplicates(
    embeddings: &[Vec<f32>],
    threshold: f64,
    max_results: usize,
) -> Vec<EmbeddingDuplicate> {
    let n = embeddings.len();
    if n < 2 { return Vec::new(); }
    let signatures: Vec<EmbeddingSignature> = embeddings.iter().map(|emb| compute_embedding_signature(emb)).collect();
    let mut candidates: Vec<EmbeddingDuplicate> = (0..n)
        .into_iter()
        .flat_map(|i| {
            let mut local = Vec::new();
            for j in (i + 1)..n {
                let sim = estimate_similarity(&signatures[i], &signatures[j]);
                if sim >= threshold {
                    local.push(EmbeddingDuplicate { idx_a: i, idx_b: j, similarity: sim });
                }
            }
            local
        })
        .collect();
    candidates.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap());
    candidates.truncate(max_results);
    candidates
}

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn embedding_minhash_find_duplicates(
    embeddings_flat: Vec<f32>,
    embedding_dim: usize,
    threshold: f64,
    max_results: usize,
) -> Result<String, JsValue> {
    if embeddings_flat.len() % embedding_dim != 0 {
        return Err(JsValue::from_str("Invalid embedding dimension"));
    }
    let num_embeddings = embeddings_flat.len() / embedding_dim;
    let mut embeddings = Vec::with_capacity(num_embeddings);
    for i in 0..num_embeddings {
        embeddings.push(embeddings_flat[i*embedding_dim..(i+1)*embedding_dim].to_vec());
    }
    let candidates = find_embedding_duplicates(&embeddings, threshold, max_results);
    serde_json::to_string(&candidates).map_err(|e| JsValue::from_str(&format!("{}", e)))
}
