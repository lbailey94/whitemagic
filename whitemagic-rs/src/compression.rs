//! Fast compression using LZ4
//! 
//! LZ4 provides extremely fast compression:
//! - 10x faster than gzip
//! - Good compression ratio
//! - Ideal for memory archives

use pyo3::prelude::*;
use std::fs::File;
use std::io::{Read, Write};
use std::path::Path;

/// Compress a file using LZ4
pub fn compress_file(input: &Path, output: &Path) -> PyResult<u64> {
    let mut input_file = File::open(input)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    let mut input_data = Vec::new();
    input_file
        .read_to_end(&mut input_data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    // Use LZ4 compression
    let compressed = lz4::block::compress(&input_data, None, false)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    
    let mut output_file = File::create(output)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    output_file
        .write_all(&compressed)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    Ok(compressed.len() as u64)
}

/// Decompress an LZ4 file
pub fn decompress_file(input: &Path, output: &Path) -> PyResult<u64> {
    let mut input_file = File::open(input)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    let mut compressed_data = Vec::new();
    input_file
        .read_to_end(&mut compressed_data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    // Decompress with LZ4
    let decompressed = lz4::block::decompress(&compressed_data, None)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    
    let mut output_file = File::create(output)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    output_file
        .write_all(&decompressed)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    Ok(decompressed.len() as u64)
}
