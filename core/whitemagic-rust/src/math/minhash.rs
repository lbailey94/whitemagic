use pyo3::prelude::*;
use whitemagic_math::minhash;
use std::collections::HashSet;

#[pyfunction]
pub fn minhash_find_duplicates(
    keywords_json: &str,
    threshold: f64,
    max_results: usize,
) -> PyResult<String> {
    // We can call into the core logic if it was public in whitemagic-math
    // But whitemagic-math's minhash_find_duplicates returns Result<String, JsValue>
    // We should call the pure rust functions instead.
    
    let keyword_lists: Vec<Vec<String>> = serde_json::from_str(keywords_json).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON parse: {}", e))
    })?;

    let sets: Vec<HashSet<String>> = keyword_lists
        .into_iter()
        .map(|kws| kws.into_iter().collect())
        .collect();

    let candidates = minhash::find_near_duplicates(&sets, threshold, max_results);

    serde_json::to_string(&candidates).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON serialize: {}", e))
    })
}

#[pyfunction]
pub fn minhash_signatures(keywords_json: &str) -> PyResult<String> {
    let keyword_lists: Vec<Vec<String>> = serde_json::from_str(keywords_json).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON parse: {}", e))
    })?;

    let signatures: Vec<minhash::MinHashSignature> = keyword_lists
        .iter()
        .map(|kws| {
            let set: HashSet<String> = kws.iter().cloned().collect();
            minhash::compute_signature(&set)
        })
        .collect();

    serde_json::to_string(&signatures).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON serialize: {}", e))
    })
}
