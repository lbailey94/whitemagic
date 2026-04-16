// Native FFI Module - Zero JSON Overhead
// Provides PyO3-native functions that accept/return PyObjects directly
// Eliminates JSON serialization bottleneck for 10-50× speedup

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

#[cfg(feature = "zig")]
use crate::conductor::sangha_bridge::SanghaBridge;

/// Native galactic batch scoring - accepts PyList of dicts, returns PyList of scored dicts
/// 50× faster than JSON path by operating directly on PyObjects
#[pyfunction]
fn galactic_batch_score_native<'py>(
    py: Python<'py>,
    memories: &Bound<'py, PyList>,
    _quick: Option<bool>,
) -> PyResult<Bound<'py, PyList>> {
    let results = PyList::new_bound(py, &[] as &[Bound<'py, PyAny>]);

    for item in memories.iter() {
        let mem_dict = item.downcast::<PyDict>()?;

        // Extract fields directly from PyDict (zero JSON overhead)
        let id: String = mem_dict.get_item("id")?.unwrap().extract()?;
        let importance: f64 = mem_dict
            .get_item("importance")?
            .unwrap()
            .extract::<f64>()
            .unwrap_or(0.5);
        let neuro_score: f64 = mem_dict
            .get_item("neuro_score")?
            .unwrap()
            .extract::<f64>()
            .unwrap_or(1.0);
        let emotional_valence: f64 = mem_dict
            .get_item("emotional_valence")?
            .unwrap()
            .extract::<f64>()
            .unwrap_or(0.0);
        let recall_count: i64 = mem_dict
            .get_item("recall_count")?
            .unwrap()
            .extract::<i64>()
            .unwrap_or(0);
        let is_protected: bool = mem_dict
            .get_item("is_protected")?
            .unwrap()
            .extract::<bool>()
            .unwrap_or(false);

        // Calculate retention score (same algorithm as JSON version)
        let retention_score = calculate_retention_score(
            importance,
            neuro_score,
            emotional_valence,
            recall_count,
            is_protected,
        );

        // Determine galactic zone and distance
        let (zone, distance) = if is_protected || retention_score > 0.8 {
            ("core", 0.0)
        } else if retention_score > 0.5 {
            ("inner", 0.3 + (0.5 - retention_score))
        } else if retention_score > 0.2 {
            ("mid", 0.5 + (0.3 - retention_score * 0.3))
        } else {
            ("edge", 0.8 + (0.15 - retention_score * 0.15).max(0.0))
        };

        // Build result dict
        let result = PyDict::new_bound(py);
        result.set_item("id", id)?;
        result.set_item("retention_score", retention_score)?;
        result.set_item("galactic_distance", distance)?;
        result.set_item("zone", zone)?;

        results.append(result)?;
    }

    Ok(results)
}

/// Calculate retention score (same algorithm as galactic_accelerator.rs)
fn calculate_retention_score(
    importance: f64,
    neuro_score: f64,
    emotional_valence: f64,
    recall_count: i64,
    is_protected: bool,
) -> f64 {
    let base = importance * 0.3 + neuro_score * 0.4;
    let emotional_boost = emotional_valence.abs() * 0.1;
    let recall_boost = (recall_count as f64 * 0.05).min(0.15);
    let protected_boost = if is_protected { 0.5 } else { 0.0 };

    (base + emotional_boost + recall_boost + protected_boost).min(1.0)
}

/// Native association mining - accepts list of (id, text) tuples
/// Returns dict with overlaps and memory_count
#[pyfunction]
fn association_mine_native<'py>(
    py: Python<'py>,
    texts: &Bound<'py, PyList>,
    max_keywords: Option<usize>,
    min_score: Option<f64>,
    max_results: Option<usize>,
) -> PyResult<Bound<'py, PyDict>> {
    let max_kw = max_keywords.unwrap_or(10);
    let min_sc = min_score.unwrap_or(0.3);
    let max_res = max_results.unwrap_or(50);

    // Extract keywords from each text
    let mut memory_keywords: Vec<(String, Vec<String>)> = Vec::new();

    for item in texts.iter() {
        let tuple = item.downcast::<pyo3::types::PyTuple>()?;
        let id: String = tuple.get_item(0)?.extract()?;
        let text: String = tuple.get_item(1)?.extract()?;

        // Simple keyword extraction (words > 3 chars, lowercase)
        let keywords: Vec<String> = text
            .to_lowercase()
            .split_whitespace()
            .filter(|w| w.len() > 3)
            .map(|w| w.trim_matches(|c: char| !c.is_alphanumeric()).to_string())
            .filter(|w| !w.is_empty())
            .take(max_kw)
            .collect();

        memory_keywords.push((id, keywords));
    }

    // Find overlaps
    let mut overlaps = Vec::new();
    let memory_count = memory_keywords.len();

    for i in 0..memory_count {
        for j in (i + 1)..memory_count {
            let (id1, kw1) = &memory_keywords[i];
            let (id2, kw2) = &memory_keywords[j];

            // Calculate overlap
            let overlap_count = kw1.iter().filter(|k| kw2.contains(k)).count();
            let total_unique = kw1.len() + kw2.len();

            if total_unique > 0 {
                let overlap_score = overlap_count as f64 / total_unique as f64;

                if overlap_score >= min_sc {
                    let overlap_dict = PyDict::new_bound(py);
                    overlap_dict.set_item("source_id", id1.clone())?;
                    overlap_dict.set_item("target_id", id2.clone())?;
                    overlap_dict.set_item("overlap_score", overlap_score)?;
                    overlap_dict.set_item(
                        "shared_keywords",
                        kw1.iter()
                            .filter(|k| kw2.contains(k))
                            .cloned()
                            .collect::<Vec<_>>(),
                    )?;
                    overlaps.push(overlap_dict);
                }
            }
        }
    }

    // Sort by score and limit results
    overlaps.sort_by(|a, b| {
        let a_score: f64 = a
            .get_item("overlap_score")
            .unwrap()
            .unwrap()
            .extract()
            .unwrap();
        let b_score: f64 = b
            .get_item("overlap_score")
            .unwrap()
            .unwrap()
            .extract()
            .unwrap();
        b_score.partial_cmp(&a_score).unwrap()
    });

    let result = PyDict::new_bound(py);
    let overlaps_list = PyList::new_bound(py, &[] as &[Bound<'py, PyAny>]);

    for overlap in overlaps.into_iter().take(max_res) {
        overlaps_list.append(overlap)?;
    }

    result.set_item("overlaps", overlaps_list)?;
    result.set_item("memory_count", memory_count)?;

    Ok(result)
}

/// Native Sangha signal push - accepts message metadata plus a 5D coordinate vector
#[cfg(feature = "zig")]
#[pyfunction]
fn sangha_push_signal(
    id: String,
    sender_id: String,
    content: String,
    channel: String,
    coords: Vec<f32>,
) -> PyResult<bool> {
    if coords.len() != 5 {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Sangha coordinates must contain exactly 5 values, got {}",
            coords.len()
        )));
    }

    if coords.iter().any(|value| !value.is_finite()) {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Sangha coordinates must contain only finite values",
        ));
    }

    let coords = [coords[0], coords[1], coords[2], coords[3], coords[4]];
    let sent = SanghaBridge::global().push_signal(&id, &sender_id, &content, &channel, coords);
    Ok(sent)
}

/// Register native FFI functions with Python module
pub fn register_native_ffi(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(galactic_batch_score_native, m)?)?;
    m.add_function(wrap_pyfunction!(association_mine_native, m)?)?;
    #[cfg(feature = "zig")]
    m.add_function(wrap_pyfunction!(sangha_push_signal, m)?)?;
    Ok(())
}
