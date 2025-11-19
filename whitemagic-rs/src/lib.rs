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
pub mod memory_consolidation;
pub mod pattern_extraction;
pub mod search;
pub mod compression;
pub mod audit;

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
    m.add_function(wrap_pyfunction!(audit::audit_directory, m)?)?;
    m.add_function(wrap_pyfunction!(audit::read_files_fast, m)?)?;
    m.add_function(wrap_pyfunction!(audit::extract_summaries, m)?)?;
    m.add_function(wrap_pyfunction!(consolidate_memories, m)?)?;
    m.add_function(wrap_pyfunction!(extract_patterns, m)?)?;
    m.add_class::<audit::FileInfo>()?;
    Ok(())
}

/// Extract patterns from long-term memories (exposed to Python)
#[pyfunction]
fn extract_patterns(
    long_term_dir: String,
    min_confidence: f64
) -> PyResult<(usize, usize, Vec<String>, Vec<String>, Vec<String>, Vec<String>, f64)> {
    let path = PathBuf::from(long_term_dir);
    
    let report = pattern_extraction::extract_patterns(&path, min_confidence)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e))?;
    
    // Convert patterns to simple strings for Python
    let solutions: Vec<String> = report.solutions.iter()
        .map(|p| format!("{} (confidence: {:.2})", p.title, p.confidence))
        .collect();
    
    let anti_patterns: Vec<String> = report.anti_patterns.iter()
        .map(|p| format!("{} (confidence: {:.2})", p.title, p.confidence))
        .collect();
    
    let heuristics: Vec<String> = report.heuristics.iter()
        .map(|p| format!("{} (confidence: {:.2})", p.title, p.confidence))
        .collect();
    
    let optimizations: Vec<String> = report.optimizations.iter()
        .map(|p| format!("{} (confidence: {:.2})", p.title, p.confidence))
        .collect();
    
    Ok((
        report.total_memories,
        report.patterns_found,
        solutions,
        anti_patterns,
        heuristics,
        optimizations,
        report.duration_seconds
    ))
}

/// Auto-consolidate short-term memories (exposed to Python)
#[pyfunction]
fn consolidate_memories(
    short_term_dir: String,
    top_n: usize,
    similarity_threshold: f64
) -> PyResult<(usize, usize, usize, f64, Vec<String>)> {
    let path = PathBuf::from(short_term_dir);
    
    let report = memory_consolidation::auto_consolidate(&path, top_n, similarity_threshold)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e))?;
    
    Ok((
        report.short_term_count,
        report.long_term_created,
        report.clusters_found,
        report.duration_seconds,
        report.top_memories
    ))
}
