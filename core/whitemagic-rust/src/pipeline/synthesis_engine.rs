use numpy::{PyArray1, PyArrayMethods};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use std::collections::HashMap;

/// Infer DAG dependencies from 4D holographic coordinates
/// Fast-path for causal_net.py::infer_dependencies()
#[pyfunction]
fn infer_dag_from_coords<'py>(
    py: Python<'py>,
    cluster_data: &Bound<'py, PyDict>,
    dist_threshold: f64,
    w_threshold: f64,
) -> PyResult<Bound<'py, PyList>> {
    let edges = PyList::empty_bound(py);
    let keys: Vec<String> = cluster_data.keys().extract()?;

    // Extract centroids into a vec
    let mut centroids: Vec<(String, [f64; 4])> = Vec::new();
    for key in &keys {
        let cluster: Bound<'_, PyDict> = cluster_data.get_item(key)?.unwrap().downcast_into()?;
        let centroid: Bound<'_, PyArray1<f64>> =
            cluster.get_item("centroid")?.unwrap().downcast_into()?;
        let arr = centroid.readonly();
        let slice = arr.as_slice()?;
        if slice.len() >= 4 {
            centroids.push((key.clone(), [slice[0], slice[1], slice[2], slice[3]]));
        }
    }

    // Build edges based on proximity and w-coordinate flow
    for i in 0..centroids.len() {
        for j in (i + 1)..centroids.len() {
            let (k1, c1) = &centroids[i];
            let (k2, c2) = &centroids[j];

            // XYZ distance
            let dist_xyz =
                ((c1[0] - c2[0]).powi(2) + (c1[1] - c2[1]).powi(2) + (c1[2] - c2[2]).powi(2))
                    .sqrt();
            let w_diff = c2[3] - c1[3];

            if dist_xyz < dist_threshold && w_diff.abs() > w_threshold {
                let edge = if w_diff > 0.0 {
                    PyTuple::new_bound(py, [k1.as_str(), k2.as_str()])
                } else {
                    PyTuple::new_bound(py, [k2.as_str(), k1.as_str()])
                };
                edges.append(edge)?;
            }
        }
    }

    Ok(edges)
}

/// Fast kaizen metrics gathering
/// Batch SQL-like aggregations in Rust
#[pyfunction]
fn fast_kaizen_metrics<'py>(
    py: Python<'py>,
    memory_titles: Vec<String>,
    holographic_coords: Vec<Vec<f64>>, // [x, y, z, w] for each memory
) -> PyResult<Bound<'py, PyDict>> {
    let result = PyDict::new_bound(py);

    // Count untitled (empty or starts with "Untitled")
    let untitled_count = memory_titles
        .iter()
        .filter(|t| t.is_empty() || t.starts_with("Untitled"))
        .count();
    result.set_item("untitled_count", untitled_count)?;

    // Quadrant analysis
    let mut quadrants: HashMap<String, usize> = HashMap::new();
    for coords in &holographic_coords {
        if coords.len() >= 2 {
            let x_reg = if coords[0] < 0.0 {
                "logical"
            } else {
                "emotional"
            };
            let y_reg = if coords[1] < 0.0 {
                "detail"
            } else {
                "strategic"
            };
            let key = format!("{}_{}", x_reg, y_reg);
            *quadrants.entry(key).or_insert(0) += 1;
        }
    }

    let quad_dict = PyDict::new_bound(py);
    for (k, v) in quadrants {
        quad_dict.set_item(k, v)?;
    }
    result.set_item("quadrant_counts", quad_dict)?;

    // W-coordinate (gravity) stats
    let w_values: Vec<f64> = holographic_coords
        .iter()
        .filter_map(|c| c.get(3).copied())
        .collect();

    if !w_values.is_empty() {
        let sum_w: f64 = w_values.iter().sum();
        let avg_w = sum_w / w_values.len() as f64;
        let max_w = w_values.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
        let min_w = w_values.iter().fold(f64::INFINITY, |a, &b| a.min(b));

        result.set_item("avg_gravity", avg_w)?;
        result.set_item("max_gravity", max_w)?;
        result.set_item("min_gravity", min_w)?;
        result.set_item(
            "high_gravity_count",
            w_values.iter().filter(|&&w| w > 0.6).count(),
        )?;
    }

    Ok(result)
}

pub fn synthesis_engine(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(infer_dag_from_coords, m)?)?;
    m.add_function(wrap_pyfunction!(fast_kaizen_metrics, m)?)?;
    Ok(())
}
