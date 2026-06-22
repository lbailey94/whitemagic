//! MinHash implementation for fast duplicate detection
//! Decoupled from Python/OS bindings for WASM compatibility.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

pub type MinHashSignature = Vec<u64>;

const NUM_HASHES: usize = 128;
const LARGE_PRIME: u64 = 4294967311;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DuplicateCandidate {
    pub idx_a: usize,
    pub idx_b: usize,
    pub similarity: f64,
}

fn hash_params(seed: usize) -> (u64, u64) {
    let a = (seed as u64 * 2654435761) % LARGE_PRIME;
    let b = (seed as u64 * 2246822519) % LARGE_PRIME;
    (a, b)
}

pub fn compute_signature(terms: &HashSet<String>) -> MinHashSignature {
    let mut min_values = vec![u64::MAX; NUM_HASHES];
    for term in terms {
        let h = {
            use std::collections::hash_map::DefaultHasher;
            use std::hash::{Hash, Hasher};
            let mut hasher = DefaultHasher::new();
            term.hash(&mut hasher);
            hasher.finish()
        };
        for i in 0..NUM_HASHES {
            let (a, b) = hash_params(i);
            let val = (a.wrapping_mul(h) + b) % LARGE_PRIME;
            if val < min_values[i] {
                min_values[i] = val;
            }
        }
    }
    min_values
}

pub fn jaccard_similarity(a: &MinHashSignature, b: &MinHashSignature) -> f64 {
    let matches = a.iter().zip(b.iter()).filter(|(x, y)| x == y).count();
    matches as f64 / NUM_HASHES as f64
}

pub fn find_near_duplicates(
    keyword_sets: &[HashSet<String>],
    threshold: f64,
    _max_results: usize,
) -> Vec<DuplicateCandidate> {
    let n = keyword_sets.len();
    if n < 2 {
        return Vec::new();
    }

    let signatures: Vec<MinHashSignature> = keyword_sets.iter().map(|s| compute_signature(s)).collect();

    let mut candidates: Vec<DuplicateCandidate> = (0..n)
        .into_iter()
        .flat_map(|i| {
            let mut local = Vec::new();
            for j in (i + 1)..n {
                let sim = jaccard_similarity(&signatures[i], &signatures[j]);
                if sim >= threshold {
                    local.push(DuplicateCandidate {
                        idx_a: i,
                        idx_b: j,
                        similarity: sim,
                    });
                }
            }
            local
        })
        .collect();

    candidates.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap());
    candidates
}

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn minhash_find_duplicates(
    keywords_json: &str,
    threshold: f64,
    max_results: usize,
) -> Result<String, JsValue> {
    let keyword_lists: Vec<Vec<String>> = serde_json::from_str(keywords_json).map_err(|e| {
        JsValue::from_str(&format!("JSON parse: {}", e))
    })?;

    let sets: Vec<HashSet<String>> = keyword_lists
        .into_iter()
        .map(|kws| kws.into_iter().collect())
        .collect();

    let candidates = find_near_duplicates(&sets, threshold, max_results);

    serde_json::to_string(&candidates).map_err(|e| {
        JsValue::from_str(&format!("JSON serialize: {}", e))
    })
}

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn minhash_signatures(keywords_json: &str) -> Result<String, JsValue> {
    let keyword_lists: Vec<Vec<String>> = serde_json::from_str(keywords_json).map_err(|e| {
        JsValue::from_str(&format!("JSON parse: {}", e))
    })?;

    let signatures: Vec<MinHashSignature> = keyword_lists
        .iter()
        .map(|kws| {
            let set: HashSet<String> = kws.iter().cloned().collect();
            compute_signature(&set)
        })
        .collect();

    serde_json::to_string(&signatures).map_err(|e| {
        JsValue::from_str(&format!("JSON serialize: {}", e))
    })
}
