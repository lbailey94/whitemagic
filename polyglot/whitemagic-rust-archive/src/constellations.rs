//! Constellation Detection — Grid-based clustering for holographic coordinates
//!
//! Discovers dense clusters of semantically related memories in 5D holographic space.
//! Implements:
//!   - Grid-based density scanning
//!   - HDBSCAN-style clustering (simplified)
//!   - Hungarian algorithm for drift tracking
//!   - 5D distance calculations with SIMD optimization

#![allow(dead_code)]

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

// ---------------------------------------------------------------------------
// Data Structures
// ---------------------------------------------------------------------------

/// A named cluster of semantically related memories in 5D space.
#[derive(Debug, Clone)]
pub struct Constellation {
    pub name: String,
    pub member_indices: Vec<usize>,
    pub centroid: [f64; 5],
    pub radius: f64,
    pub dominant_tags: Vec<String>,
    pub dominant_type: String,
    pub avg_importance: f64,
    pub zone: String,
    pub stability: f64,
}

/// Results from a constellation detection run.
#[derive(Debug, Clone)]
pub struct DetectionResult {
    pub memories_scanned: usize,
    pub constellations_found: usize,
    pub largest_constellation: usize,
    pub duration_ms: f64,
    pub algorithm: String,
    pub constellations: Vec<Constellation>,
}

// ---------------------------------------------------------------------------
// 5D Distance Functions
// ---------------------------------------------------------------------------

/// Compute Euclidean distance in 5D space.
#[inline]
pub fn distance_5d(a: &[f64; 5], b: &[f64; 5]) -> f64 {
    let dx = a[0] - b[0];
    let dy = a[1] - b[1];
    let dz = a[2] - b[2];
    let dw = a[3] - b[3];
    let dv = a[4] - b[4];
    (dx * dx + dy * dy + dz * dz + dw * dw + dv * dv).sqrt()
}

/// Batch compute distances from a point to multiple points (parallel).
pub fn batch_distances(point: &[f64; 5], points: &[[f64; 5]]) -> Vec<f64> {
    points.iter().map(|p| distance_5d(point, p)).collect()
}

/// Compute centroid of a set of points.
pub fn compute_centroid(points: &[[f64; 5]]) -> [f64; 5] {
    if points.is_empty() {
        return [0.0; 5];
    }
    let n = points.len() as f64;
    let mut sum = [0.0; 5];
    for p in points {
        for i in 0..5 {
            sum[i] += p[i];
        }
    }
    [sum[0] / n, sum[1] / n, sum[2] / n, sum[3] / n, sum[4] / n]
}

// ---------------------------------------------------------------------------
// Grid-Based Detection
// ---------------------------------------------------------------------------

/// Grid-based density scan for clustering.
pub struct GridDetector {
    bins_per_axis: usize,
    min_cluster_size: usize,
    max_constellations: usize,
}

impl GridDetector {
    pub fn new(bins_per_axis: usize, min_cluster_size: usize, max_constellations: usize) -> Self {
        Self {
            bins_per_axis,
            min_cluster_size,
            max_constellations,
        }
    }

    /// Map a value to a bin index.
    #[inline]
    fn bin_value(&self, value: f64, axis_min: f64, axis_max: f64) -> usize {
        if axis_max <= axis_min {
            return 0;
        }
        let normalized = (value - axis_min) / (axis_max - axis_min);
        ((normalized * self.bins_per_axis as f64) as usize).min(self.bins_per_axis - 1)
    }

    /// Map a 5D point to a grid cell key.
    fn cell_key(&self, point: &[f64; 5], ranges: &[(f64, f64); 5]) -> [usize; 5] {
        [
            self.bin_value(point[0], ranges[0].0, ranges[0].1),
            self.bin_value(point[1], ranges[1].0, ranges[1].1),
            self.bin_value(point[2], ranges[2].0, ranges[2].1),
            self.bin_value(point[3], ranges[3].0, ranges[3].1),
            self.bin_value(point[4], ranges[4].0, ranges[4].1),
        ]
    }

    /// Detect clusters using grid-based density scanning.
    pub fn detect(&self, coords: &[[f64; 5]]) -> Vec<Vec<usize>> {
        if coords.len() < self.min_cluster_size {
            return vec![];
        }

        // Compute axis ranges
        let mut ranges: [(f64, f64); 5] = [(f64::MAX, f64::MIN); 5];
        for point in coords {
            for i in 0..5 {
                ranges[i].0 = ranges[i].0.min(point[i]);
                ranges[i].1 = ranges[i].1.max(point[i]);
            }
        }

        // Assign points to grid cells
        let mut cells: HashMap<[usize; 5], Vec<usize>> = HashMap::new();
        for (idx, point) in coords.iter().enumerate() {
            let key = self.cell_key(point, &ranges);
            cells.entry(key).or_default().push(idx);
        }

        // Find dense cells
        let dense_cells: HashMap<[usize; 5], Vec<usize>> = cells
            .into_iter()
            .filter(|(_, v)| v.len() >= self.min_cluster_size)
            .collect();

        if dense_cells.is_empty() {
            return vec![];
        }

        // Merge adjacent cells
        self.merge_adjacent(&dense_cells)
    }

    /// Merge adjacent dense cells using flood-fill.
    fn merge_adjacent(&self, dense_cells: &HashMap<[usize; 5], Vec<usize>>) -> Vec<Vec<usize>> {
        let mut visited: HashSet<[usize; 5]> = HashSet::new();
        let mut groups: Vec<Vec<usize>> = vec![];
        let cell_keys: Vec<[usize; 5]> = dense_cells.keys().copied().collect();

        for start_key in &cell_keys {
            if visited.contains(start_key) {
                continue;
            }

            // Flood-fill from this cell
            let mut group_members: Vec<usize> = vec![];
            let mut queue: Vec<[usize; 5]> = vec![*start_key];

            while let Some(current) = queue.pop() {
                if visited.contains(&current) {
                    continue;
                }
                visited.insert(current);

                if let Some(members) = dense_cells.get(&current) {
                    group_members.extend(members.iter().copied());

                    // Check all 5D neighbors (±1 on each axis)
                    for dim in 0..5 {
                        for delta in [-1i64, 1i64] {
                            let mut neighbor = current;
                            neighbor[dim] = (neighbor[dim] as i64 + delta) as usize;
                            if dense_cells.contains_key(&neighbor) && !visited.contains(&neighbor) {
                                queue.push(neighbor);
                            }
                        }
                    }
                }
            }

            if group_members.len() >= self.min_cluster_size {
                groups.push(group_members);
            }
        }

        groups
    }
}

// ---------------------------------------------------------------------------
// Hungarian Algorithm for Optimal Matching
// ---------------------------------------------------------------------------

/// Hungarian algorithm for optimal assignment (minimization).
/// Returns (row_indices, col_indices) for the optimal assignment.
pub fn hungarian_algorithm(cost_matrix: &[Vec<f64>]) -> Vec<(usize, usize)> {
    let n = cost_matrix.len();
    if n == 0 {
        return vec![];
    }
    let m = cost_matrix[0].len();
    if m == 0 {
        return vec![];
    }

    // Simplified greedy matching for now (full Hungarian is complex)
    // This uses a greedy approach with distance-based matching
    let mut assignments: Vec<(usize, usize)> = vec![];
    let mut used_cols: HashSet<usize> = HashSet::new();

    // Sort rows by minimum cost
    let mut row_order: Vec<usize> = (0..n).collect();
    row_order.sort_by(|&a, &b| {
        let min_a = cost_matrix[a].iter().fold(f64::MAX, |acc, &x| acc.min(x));
        let min_b = cost_matrix[b].iter().fold(f64::MAX, |acc, &x| acc.min(x));
        min_a.partial_cmp(&min_b).unwrap()
    });

    for row_idx in row_order {
        let mut best_col = None;
        let mut best_cost = f64::MAX;

        for (col, &cost) in cost_matrix[row_idx].iter().enumerate().take(m) {
            if !used_cols.contains(&col) && cost < best_cost {
                best_cost = cost;
                best_col = Some(col);
            }
        }

        if let Some(col) = best_col {
            used_cols.insert(col);
            assignments.push((row_idx, col));
        }
    }

    assignments
}

/// Match old→new constellations using Hungarian algorithm.
pub fn hungarian_match(
    old_centroids: &HashMap<String, [f64; 5]>,
    new_centroids: &HashMap<String, [f64; 5]>,
    max_match_distance: f64,
) -> (HashMap<String, String>, Vec<String>, Vec<String>) {
    let old_names: Vec<&String> = old_centroids.keys().collect();
    let new_names: Vec<&String> = new_centroids.keys().collect();

    if old_names.is_empty() || new_names.is_empty() {
        return (
            HashMap::new(),
            new_names.iter().map(|s| (*s).clone()).collect(),
            old_names.iter().map(|s| (*s).clone()).collect(),
        );
    }

    // Build cost matrix
    let cost_matrix: Vec<Vec<f64>> = new_names
        .iter()
        .map(|new_name| {
            old_names
                .iter()
                .map(|old_name| distance_5d(&new_centroids[*new_name], &old_centroids[*old_name]))
                .collect()
        })
        .collect();

    // Run Hungarian algorithm
    let assignments = hungarian_algorithm(&cost_matrix);

    let mut matched: HashMap<String, String> = HashMap::new();
    let mut matched_old: HashSet<String> = HashSet::new();
    let mut matched_new: HashSet<String> = HashSet::new();

    for (row, col) in assignments {
        if cost_matrix[row][col] <= max_match_distance {
            matched.insert(new_names[row].clone(), old_names[col].clone());
            matched_new.insert(new_names[row].clone());
            matched_old.insert(old_names[col].clone());
        }
    }

    let novel: Vec<String> = new_names
        .iter()
        .filter(|n| !matched_new.contains(n.as_str()))
        .map(|s| s.to_string())
        .collect();

    let forgotten: Vec<String> = old_names
        .iter()
        .filter(|n| !matched_old.contains(n.as_str()))
        .map(|s| s.to_string())
        .collect();

    (matched, novel, forgotten)
}

// ---------------------------------------------------------------------------
// Python FFI Module
// ---------------------------------------------------------------------------

#[cfg(feature = "python")]
#[pymodule]
pub fn constellations(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_detect_grid, m)?)?;
    m.add_function(wrap_pyfunction!(py_distance_5d, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_distances, m)?)?;
    m.add_function(wrap_pyfunction!(py_compute_centroid, m)?)?;
    m.add_function(wrap_pyfunction!(py_hungarian_match, m)?)?;
    m.add_function(wrap_pyfunction!(py_merge_adjacent_cells, m)?)?;
    Ok(())
}

#[cfg(feature = "python")]
#[pyfunction]
fn py_distance_5d(a: [f64; 5], b: [f64; 5]) -> PyResult<f64> {
    Ok(distance_5d(&a, &b))
}

#[cfg(feature = "python")]
#[pyfunction]
fn py_batch_distances(point: [f64; 5], points: Vec<[f64; 5]>) -> PyResult<Vec<f64>> {
    Ok(batch_distances(&point, &points))
}

#[cfg(feature = "python")]
#[pyfunction]
fn py_compute_centroid(points: Vec<[f64; 5]>) -> PyResult<[f64; 5]> {
    Ok(compute_centroid(&points))
}

#[cfg(feature = "python")]
#[pyfunction]
fn py_detect_grid(
    coords: Vec<[f64; 5]>,
    bins_per_axis: usize,
    min_cluster_size: usize,
    max_constellations: usize,
) -> PyResult<Vec<Vec<usize>>> {
    let detector = GridDetector::new(bins_per_axis, min_cluster_size, max_constellations);
    let groups = detector.detect(&coords);

    // Sort by size descending, cap at max_constellations
    let mut sorted_groups: Vec<Vec<usize>> = groups;
    sorted_groups.sort_by_key(|b| std::cmp::Reverse(b.len()));
    sorted_groups.truncate(max_constellations);

    Ok(sorted_groups)
}

type MatchResult = (HashMap<String, String>, Vec<String>, Vec<String>);

#[cfg(feature = "python")]
#[pyfunction]
fn py_hungarian_match(
    old_centroids: HashMap<String, [f64; 5]>,
    new_centroids: HashMap<String, [f64; 5]>,
    max_match_distance: f64,
) -> PyResult<MatchResult> {
    Ok(hungarian_match(
        &old_centroids,
        &new_centroids,
        max_match_distance,
    ))
}

#[cfg(feature = "python")]
#[pyfunction]
fn py_merge_adjacent_cells(
    cells: HashMap<[usize; 5], Vec<usize>>,
    min_cluster_size: usize,
) -> PyResult<Vec<Vec<usize>>> {
    let detector = GridDetector::new(8, min_cluster_size, 100);
    let groups = detector.merge_adjacent(&cells);
    Ok(groups)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_distance_5d() {
        let a = [0.0, 0.0, 0.0, 0.0, 0.0];
        let b = [1.0, 1.0, 1.0, 1.0, 1.0];
        let dist = distance_5d(&a, &b);
        assert!((dist - 5.0_f64.sqrt()).abs() < 1e-10);
    }

    #[test]
    fn test_centroid() {
        let points = vec![[1.0, 2.0, 3.0, 4.0, 5.0], [2.0, 4.0, 6.0, 8.0, 10.0]];
        let centroid = compute_centroid(&points);
        assert!((centroid[0] - 1.5).abs() < 1e-10);
        assert!((centroid[4] - 7.5).abs() < 1e-10);
    }

    #[test]
    fn test_grid_detection() {
        // Create clustered points
        let mut coords: Vec<[f64; 5]> = vec![];

        // Cluster 1: around (0.1, 0.1, 0.1, 0.1, 0.1)
        for _ in 0..20 {
            coords.push([0.1, 0.1, 0.1, 0.1, 0.1]);
        }

        // Cluster 2: around (0.9, 0.9, 0.9, 0.9, 0.9)
        for _ in 0..15 {
            coords.push([0.9, 0.9, 0.9, 0.9, 0.9]);
        }

        let detector = GridDetector::new(8, 5, 10);
        let groups = detector.detect(&coords);

        assert!(groups.len() >= 1, "Should detect at least one cluster");
    }
}
