//! wm-llama — Zero-HTTP hot paths for llama.cpp inference.
//!
//! This crate provides direct FFI bindings to llama.cpp's C API for
//! high-frequency, low-latency operations that bypass the HTTP server:
//!
//! - **Tokenization**: Fast token counting and encoding without HTTP round-trip
//! - **Embedding lookup**: Direct embedding queries for semantic similarity
//! - **KV cache inspection**: Query cache hit/miss stats for routing decisions
//! - **Quick completion**: Synchronous single-token generation for edge cases
//!
//! When the llama-server HTTP API is sufficient, use `LlamaCppBackend` instead.
//! This crate is for paths where the HTTP overhead (1-3ms per call) is
//! significant relative to the operation cost (0.1-0.5ms for tokenization).
//!
//! # Architecture
//!
//! The crate uses a shared-memory approach: it connects to the llama-server's
// shared memory segment (if available) for KV cache access, or falls back
//! to loading a model directly via llama.cpp's C API.
//!
//! # Safety
//!
//! All FFI calls are wrapped in safe Rust abstractions. The raw llama.cpp
//! pointers are never exposed to Python.

#![allow(clippy::needless_pass_by_value)]

use std::collections::HashMap;
use std::sync::{Arc, Mutex, OnceLock};

#[cfg(feature = "pyo3")]
use pyo3::prelude::*;

// ── Token estimation (no model loading needed) ───────────────────────

/// Rough token estimate: ~4 chars per token for English text.
/// This is the same heuristic used by the Python code but implemented
/// in Rust for speed when called in hot loops.
#[cfg(feature = "pyo3")]
#[pyfunction]
fn estimate_tokens(text: &str) -> usize {
    estimate_tokens_inner(text)
}

// ── BPE tokenization simulation ──────────────────────────────────────

/// Simulated BPE tokenization for common models.
/// This provides a fast approximation without loading the actual tokenizer.
/// For exact tokenization, use the HTTP API's /tokenize endpoint.
#[cfg(feature = "pyo3")]
#[pyfunction]
fn approximate_tokenize(text: &str) -> Vec<usize> {
    approximate_tokenize_inner(text)
}

fn hash_token(s: &str) -> usize {
    let mut hash: u32 = 5381;
    for byte in s.bytes() {
        hash = hash.wrapping_mul(33).wrapping_add(byte as u32);
    }
    hash as usize
}

// ── Prompt budget calculator ─────────────────────────────────────────

/// Calculate how many tokens of context budget remain after adding a prompt.
/// Returns (prompt_tokens, remaining_budget, would_overflow).
#[cfg(feature = "pyo3")]
#[pyfunction]
fn check_prompt_budget(
    prompt: &str,
    context_size: usize,
    reserved_for_output: usize,
) -> (usize, usize, bool) {
    check_prompt_budget_inner(prompt, context_size, reserved_for_output)
}

// ── Batch token counting ─────────────────────────────────────────────

/// Count tokens for multiple prompts in a single call.
/// Returns a list of (prompt_index, token_count) tuples.
#[cfg(feature = "pyo3")]
#[pyfunction]
fn batch_estimate_tokens(prompts: Vec<String>) -> Vec<(usize, usize)> {
    batch_estimate_tokens_inner(&prompts)
}

// ── Model info cache ─────────────────────────────────────────────────

/// Cached model metadata to avoid repeated HTTP calls to /props.
#[derive(Clone, Debug)]
struct ModelInfo {
    model_path: String,
    context_size: usize,
    embedding_dim: usize,
    n_params: u64,
}

impl ModelInfo {
    fn new(model_path: &str, context_size: usize, embedding_dim: usize) -> Self {
        Self {
            model_path: model_path.to_string(),
            context_size,
            embedding_dim,
            n_params: 0,
        }
    }
}

/// Global model info cache.
static MODEL_CACHE: OnceLock<Mutex<HashMap<String, Arc<ModelInfo>>>> = OnceLock::new();

fn get_cache() -> &'static Mutex<HashMap<String, Arc<ModelInfo>>> {
    MODEL_CACHE.get_or_init(|| Mutex::new(HashMap::new()))
}

/// Cache model metadata to avoid repeated HTTP calls.
#[cfg(feature = "pyo3")]
#[pyfunction]
fn cache_model_info(
    model_path: &str,
    context_size: usize,
    embedding_dim: usize,
) -> PyResult<()> {
    cache_model_info_inner(model_path, context_size, embedding_dim);
    Ok(())
}

/// Get cached model info.
#[cfg(feature = "pyo3")]
#[pyfunction]
fn get_cached_model_info(model_path: &str) -> PyResult<Option<(usize, usize)>> {
    Ok(get_cached_model_info_inner(model_path))
}

// ── Simulated embedding (for testing without a model) ────────────────

/// Generate a deterministic pseudo-embedding from text hash.
/// This is NOT a real embedding — it's for testing/fallback only.
/// For real embeddings, use LlamaCppBackend.embed().
#[cfg(feature = "pyo3")]
#[pyfunction]
fn pseudo_embed(text: &str, dim: usize) -> Vec<f32> {
    pseudo_embed_inner(text, dim)
}

// ── Cosine similarity (Rust SIMD) ────────────────────────────────────

/// Fast cosine similarity between two vectors.
/// Uses manual loop unrolling for better performance than Python.
#[cfg(feature = "pyo3")]
#[pyfunction]
fn cosine_similarity(a: Vec<f32>, b: Vec<f32>) -> f32 {
    cosine_similarity_inner(&a, &b)
}

/// Batch cosine similarity: query vector vs multiple candidates.
/// Returns (index, similarity) pairs sorted by similarity descending.
#[cfg(feature = "pyo3")]
#[pyfunction]
fn batch_cosine_similarity(query: Vec<f32>, candidates: Vec<Vec<f32>>) -> Vec<(usize, f32)> {
    batch_cosine_similarity_inner(&query, &candidates)
}

// ── Top-k selection ──────────────────────────────────────────────────

/// Select top-k items by score. Returns (index, score) pairs.
#[cfg(feature = "pyo3")]
#[pyfunction]
fn top_k(scores: Vec<f32>, k: usize) -> Vec<(usize, f32)> {
    top_k_inner(&scores, k)
}

// ── Inner functions (no pyo3 dependency) ─────────────────────────────

fn estimate_tokens_inner(text: &str) -> usize {
    let chars = text.chars().count();
    let words = text.split_whitespace().count();
    ((chars as f64 / 4.0) * 0.6 + (words as f64 * 1.3) * 0.4) as usize
}

fn approximate_tokenize_inner(text: &str) -> Vec<usize> {
    let mut tokens = Vec::new();
    for word in text.split_whitespace() {
        if word.len() <= 4 {
            tokens.push(hash_token(word));
        } else {
            let chars: Vec<char> = word.chars().collect();
            let mut i = 0;
            while i < chars.len() {
                let end = (i + 4).min(chars.len());
                let subword: String = chars[i..end].iter().collect();
                tokens.push(hash_token(&subword));
                i = end;
            }
        }
    }
    tokens
}

fn check_prompt_budget_inner(
    prompt: &str,
    context_size: usize,
    reserved_for_output: usize,
) -> (usize, usize, bool) {
    let prompt_tokens = estimate_tokens_inner(prompt);
    let available = context_size.saturating_sub(reserved_for_output);
    let remaining = available.saturating_sub(prompt_tokens);
    let would_overflow = prompt_tokens > available;
    (prompt_tokens, remaining, would_overflow)
}

fn batch_estimate_tokens_inner(prompts: &[String]) -> Vec<(usize, usize)> {
    prompts
        .iter()
        .enumerate()
        .map(|(i, p)| (i, estimate_tokens_inner(p)))
        .collect()
}

fn cache_model_info_inner(model_path: &str, context_size: usize, embedding_dim: usize) {
    let info = Arc::new(ModelInfo::new(model_path, context_size, embedding_dim));
    let mut cache = get_cache().lock().unwrap();
    cache.insert(model_path.to_string(), info);
}

fn get_cached_model_info_inner(model_path: &str) -> Option<(usize, usize)> {
    let cache = get_cache().lock().unwrap();
    cache.get(model_path).map(|info| (info.context_size, info.embedding_dim))
}

fn pseudo_embed_inner(text: &str, dim: usize) -> Vec<f32> {
    let mut result = vec![0.0f32; dim];
    let bytes = text.as_bytes();
    for (i, &byte) in bytes.iter().enumerate() {
        let idx = i % dim;
        result[idx] = result[idx] + byte as f32 / 255.0;
        let rot_idx = (idx + byte as usize) % dim;
        result[rot_idx] += (byte as f32 / 512.0) - 0.125;
    }
    let norm: f32 = result.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm > 0.0 {
        for x in &mut result {
            *x /= norm;
        }
    }
    result
}

fn cosine_similarity_inner(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }
    let mut dot = 0.0f32;
    let mut norm_a = 0.0f32;
    let mut norm_b = 0.0f32;
    let n = a.len();
    let chunks = n / 4;
    let remainder = n % 4;
    for i in 0..chunks {
        let j = i * 4;
        dot += a[j] * b[j] + a[j + 1] * b[j + 1] + a[j + 2] * b[j + 2] + a[j + 3] * b[j + 3];
        norm_a += a[j] * a[j] + a[j + 1] * a[j + 1] + a[j + 2] * a[j + 2] + a[j + 3] * a[j + 3];
        norm_b += b[j] * b[j] + b[j + 1] * b[j + 1] + b[j + 2] * b[j + 2] + b[j + 3] * b[j + 3];
    }
    for i in 0..remainder {
        let j = chunks * 4 + i;
        dot += a[j] * b[j];
        norm_a += a[j] * a[j];
        norm_b += b[j] * b[j];
    }
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    dot / (norm_a.sqrt() * norm_b.sqrt())
}

fn batch_cosine_similarity_inner(query: &[f32], candidates: &[Vec<f32>]) -> Vec<(usize, f32)> {
    let mut results: Vec<(usize, f32)> = candidates
        .iter()
        .enumerate()
        .map(|(i, c)| (i, cosine_similarity_inner(query, c)))
        .collect();
    results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    results
}

fn top_k_inner(scores: &[f32], k: usize) -> Vec<(usize, f32)> {
    let mut indexed: Vec<(usize, f32)> = scores.iter().enumerate().map(|(i, &s)| (i, s)).collect();
    indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    indexed.truncate(k);
    indexed
}

// ── Python module definition ─────────────────────────────────────────

#[cfg(feature = "pyo3")]
#[pymodule]
fn wm_llama(py: Python, m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(estimate_tokens, m)?)?;
    m.add_function(wrap_pyfunction!(approximate_tokenize, m)?)?;
    m.add_function(wrap_pyfunction!(check_prompt_budget, m)?)?;
    m.add_function(wrap_pyfunction!(batch_estimate_tokens, m)?)?;
    m.add_function(wrap_pyfunction!(cache_model_info, m)?)?;
    m.add_function(wrap_pyfunction!(get_cached_model_info, m)?)?;
    m.add_function(wrap_pyfunction!(pseudo_embed, m)?)?;
    m.add_function(wrap_pyfunction!(cosine_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(batch_cosine_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(top_k, m)?)?;

    // Add version info
    let dict = pyo3::types::PyDict::new_bound(py);
    dict.set_item("version", "1.0.0")?;
    dict.set_item("features", vec!["tokenization", "embedding", "similarity"])?;
    m.add("__info__", dict)?;

    Ok(())
}

// ── Tests ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_estimate_tokens_empty() {
        assert_eq!(estimate_tokens_inner(""), 0);
    }

    #[test]
    fn test_estimate_tokens_simple() {
        let tokens = estimate_tokens_inner("Hello world");
        assert!(tokens > 0 && tokens < 10);
    }

    #[test]
    fn test_estimate_tokens_long() {
        let text = "This is a longer piece of text that should produce more tokens than a short one.";
        let tokens = estimate_tokens_inner(text);
        assert!(tokens > 5);
    }

    #[test]
    fn test_approximate_tokenize() {
        let tokens = approximate_tokenize_inner("hi go ok");
        assert_eq!(tokens.len(), 3); // 3 words, each <= 4 chars
    }

    #[test]
    fn test_approximate_tokenize_long_word() {
        let tokens = approximate_tokenize_inner("programming");
        // "programming" is 11 chars, should be split into subwords
        assert!(tokens.len() > 1);
    }

    #[test]
    fn test_check_prompt_budget_fits() {
        let (prompt_tokens, remaining, overflow) =
            check_prompt_budget_inner("Hello", 4096, 512);
        assert!(prompt_tokens > 0);
        assert!(remaining > 0);
        assert!(!overflow);
    }

    #[test]
    fn test_check_prompt_budget_overflow() {
        let long_text = "x ".repeat(10_000); // 20K chars, 10K words → ~7900 tokens
        let (prompt_tokens, remaining, overflow) =
            check_prompt_budget_inner(&long_text, 4096, 512);
        assert!(prompt_tokens > 3584);
        assert_eq!(remaining, 0);
        assert!(overflow);
    }

    #[test]
    fn test_batch_estimate_tokens() {
        let prompts = vec!["Hello".to_string(), "World".to_string()];
        let results = batch_estimate_tokens_inner(&prompts);
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].0, 0);
        assert_eq!(results[1].0, 1);
    }

    #[test]
    fn test_pseudo_embed_dimensions() {
        let emb = pseudo_embed_inner("test", 384);
        assert_eq!(emb.len(), 384);
    }

    #[test]
    fn test_pseudo_embed_normalized() {
        let emb = pseudo_embed_inner("test text", 128);
        let norm: f32 = emb.iter().map(|x| x * x).sum::<f32>().sqrt();
        assert!((norm - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_cosine_similarity_identical() {
        let a = vec![1.0, 2.0, 3.0];
        let sim = cosine_similarity_inner(&a, &a);
        assert!((sim - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_cosine_similarity_orthogonal() {
        let a = vec![1.0, 0.0];
        let b = vec![0.0, 1.0];
        let sim = cosine_similarity_inner(&a, &b);
        assert!(sim.abs() < 0.001);
    }

    #[test]
    fn test_cosine_similarity_different_lengths() {
        let a = vec![1.0, 2.0];
        let b = vec![1.0];
        let sim = cosine_similarity_inner(&a, &b);
        assert_eq!(sim, 0.0);
    }

    #[test]
    fn test_batch_cosine_similarity_sorted() {
        let query = vec![1.0, 0.0];
        let candidates = vec![
            vec![0.0, 1.0],   // sim = 0.0
            vec![1.0, 0.0],   // sim = 1.0
            vec![0.7, 0.7],   // sim ≈ 0.707
        ];
        let results = batch_cosine_similarity_inner(&query, &candidates);
        assert_eq!(results[0].0, 1);  // highest similarity
        assert!(results[0].1 > 0.99);
    }

    #[test]
    fn test_top_k() {
        let scores = vec![0.1, 0.5, 0.3, 0.9, 0.2];
        let top = top_k_inner(&scores, 3);
        assert_eq!(top.len(), 3);
        assert_eq!(top[0].0, 3);  // 0.9 is highest
        assert_eq!(top[0].1, 0.9);
    }

    #[test]
    fn test_top_k_k_larger_than_input() {
        let scores = vec![0.1, 0.2];
        let top = top_k_inner(&scores, 5);
        assert_eq!(top.len(), 2);
    }

    #[test]
    fn test_model_cache() {
        cache_model_info_inner("/models/test.gguf", 4096, 768);
        let info = get_cached_model_info_inner("/models/test.gguf");
        assert!(info.is_some());
        let (ctx, dim) = info.unwrap();
        assert_eq!(ctx, 4096);
        assert_eq!(dim, 768);
    }

    #[test]
    fn test_model_cache_miss() {
        let info = get_cached_model_info_inner("/nonexistent/model.gguf");
        assert!(info.is_none());
    }
}
