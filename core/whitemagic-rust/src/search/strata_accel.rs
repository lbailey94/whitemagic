use rayon::prelude::*;
use regex::Regex;
use pyo3::prelude::*;
use pyo3::types::{PyList, PyTuple, PyString, PyInt};
use std::sync::Arc;

/// Finding from a regex scan
pub struct RegexFinding {
    pub file_path: String,
    pub pattern_index: usize,
    pub line_number: usize,
    pub match_text: String,
}

/// Scan multiple files with multiple regex patterns in parallel.
/// Returns a list of (file_path, pattern_index, line_number, match_text) tuples.
#[pyfunction]
#[pyo3(signature = (file_paths, patterns))]
pub fn batch_regex_scan(
    file_paths: Vec<String>,
    patterns: Vec<String>,
) -> PyResult<PyObject> {
    // Compile all patterns once (shared via Arc)
    let compiled: Vec<Arc<Regex>> = patterns
        .iter()
        .map(|p| {
            Regex::new(p).map(|r| Arc::new(r)).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Invalid regex '{}': {}", p, e))
            })
        })
        .collect::<Result<Vec<_>, _>>()?;

    // Scan all files in parallel
    let results: Vec<RegexFinding> = file_paths
        .par_iter()
        .flat_map(|path| {
            let content = match std::fs::read_to_string(path) {
                Ok(c) => c,
                Err(_) => return Vec::new(),
            };

            let mut findings = Vec::new();
            for (pat_idx, regex) in compiled.iter().enumerate() {
                for mat in regex.find_iter(&content).into_iter() {
                    let line_num = content[..mat.start()].matches('\n').count() + 1;
                    findings.push(RegexFinding {
                        file_path: path.clone(),
                        pattern_index: pat_idx,
                        line_number: line_num,
                        match_text: mat.as_str().to_string(),
                    });
                }
            }
            findings
        })
        .collect();

    // Convert to Python list of tuples
    Python::with_gil(|py| {
        let py_list = PyList::empty_bound(py);
        for finding in results {
            let tuple = PyTuple::new_bound(
                py,
                &[
                    PyString::new_bound(py, &finding.file_path).into_any(),
                    finding.pattern_index.to_object(py).into_bound(py).into_any(),
                    finding.line_number.to_object(py).into_bound(py).into_any(),
                    PyString::new_bound(py, &finding.match_text).into_any(),
                ],
            );
            py_list.append(tuple)?;
        }
        Ok(py_list.into())
    })
}

/// Fast SHA256 content hash for a single string.
#[pyfunction]
pub fn fast_sha256(content: &str) -> String {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    format!("{:x}", hasher.finalize())
}

/// Batch SHA256 hashing of multiple strings in parallel.
/// Returns a list of hex digest strings.
#[pyfunction]
pub fn batch_sha256(contents: Vec<String>) -> Vec<String> {
    use sha2::{Sha256, Digest};
    contents
        .par_iter()
        .map(|content| {
            let mut hasher = Sha256::new();
            hasher.update(content.as_bytes());
            format!("{:x}", hasher.finalize())
        })
        .collect()
}
