//! WhiteMagic Rust Core
//! 
//! High-performance implementations of memory operations:
//! - Fast consolidation (10-100x faster than Python)
//! - Full-text search with Tantivy
//! - Parallel memory processing
//! - Compression with LZ4
//! 
//! Philosophy: Use Rust where performance matters, 
//! Python where flexibility matters.

use pyo3::prelude::*;
// use rayon::prelude::*;  // Reserved for future parallel operations
use std::collections::HashMap;
use std::path::PathBuf;

pub mod consolidation;
pub mod search;
pub mod compression;

/// Fast memory consolidation using Rust's parallel processing
#[pyfunction]
fn fast_consolidate(
    memory_dir: String,
    threshold_days: u64,
    similarity_threshold: f64,
) -> PyResult<HashMap<String, usize>> {
    let dir = PathBuf::from(memory_dir);
    
    // Use Rust's parallel processing
    let result = consolidation::consolidate_parallel(
        &dir,
        threshold_days,
        similarity_threshold,
    )?;
    
    Ok(result)
}

/// Fast full-text search using Tantivy
#[pyfunction]
fn fast_search(
    index_dir: String,
    query: String,
    limit: usize,
) -> PyResult<Vec<(String, f32)>> {
    let dir = PathBuf::from(index_dir);
    
    let results = search::search_memories(
        &dir,
        &query,
        limit,
    )?;
    
    Ok(results)
}

/// Compress memory file with LZ4
#[pyfunction]
fn fast_compress(input_path: String, output_path: String) -> PyResult<u64> {
    let input = PathBuf::from(input_path);
    let output = PathBuf::from(output_path);
    
    let compressed_size = compression::compress_file(&input, &output)?;
    
    Ok(compressed_size)
}

/// Decompress LZ4 memory file
#[pyfunction]
fn fast_decompress(input_path: String, output_path: String) -> PyResult<u64> {
    let input = PathBuf::from(input_path);
    let output = PathBuf::from(output_path);
    
    let decompressed_size = compression::decompress_file(&input, &output)?;
    
    Ok(decompressed_size)
}

/// Calculate similarity between two memory contents (fast Rust implementation)
#[pyfunction]
fn fast_similarity(text1: String, text2: String) -> PyResult<f64> {
    let similarity = consolidation::calculate_similarity(&text1, &text2);
    Ok(similarity)
}

/// Python module definition
#[pymodule]
fn whitemagic_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fast_consolidate, m)?)?;
    m.add_function(wrap_pyfunction!(fast_search, m)?)?;
    m.add_function(wrap_pyfunction!(fast_compress, m)?)?;
    m.add_function(wrap_pyfunction!(fast_decompress, m)?)?;
    m.add_function(wrap_pyfunction!(fast_similarity, m)?)?;
    Ok(())
}
