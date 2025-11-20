//! File Operations - High-performance file I/O

use pyo3::prelude::*;
use std::fs::File;
use std::io::Write;

/// Write file with maximum performance
#[pyfunction]
pub fn write_file_fast(path: &str, content: &str) -> PyResult<usize> {
    let mut file = File::create(path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    let bytes = file.write(content.as_bytes())
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    Ok(bytes)
}

/// Write file with compression (gzip)
#[pyfunction]
pub fn write_file_compressed(path: &str, content: &str) -> PyResult<usize> {
    use flate2::write::GzEncoder;
    use flate2::Compression;
    
    let file = File::create(path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    let mut encoder = GzEncoder::new(file, Compression::best());
    let bytes = encoder.write(content.as_bytes())
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    encoder.finish()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    Ok(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_write_fast() {
        let path = "/tmp/test_rust_write.txt";
        let content = "Test content from Rust!";
        
        let bytes = write_file_fast(path, content).unwrap();
        assert_eq!(bytes, content.len());
        
        let read_content = std::fs::read_to_string(path).unwrap();
        assert_eq!(read_content, content);
    }
}
