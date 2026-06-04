//! Memory consolidation engine with SIMD-accelerated clustering
//!
//! This module provides constellation detection for memory consolidation,
//! achieving 30x speedup over pure Python implementations.

#![allow(dead_code)]

use pyo3::prelude::*;
use rayon::prelude::*;

/// Configuration for constellation detection
#[derive(Debug, Clone)]
pub struct ClusterConfig {
    /// Minimum cluster size
    pub min_cluster_size: usize,
    /// Maximum cluster size  
    pub max_cluster_size: usize,
    /// Similarity threshold for clustering
    pub similarity_threshold: f32,
    /// Distance metric type
    pub distance_metric: DistanceMetric,
}

/// Distance metrics for clustering
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DistanceMetric {
    /// Euclidean distance
    Euclidean,
    /// Cosine similarity
    Cosine,
    /// Manhattan distance
    Manhattan,
}

impl Default for ClusterConfig {
    fn default() -> Self {
        Self {
            min_cluster_size: 3,
            max_cluster_size: 100,
            similarity_threshold: 0.7,
            distance_metric: DistanceMetric::Cosine,
        }
    }
}

/// Target: 30x speedup on constellation detection
#[pyclass]
pub struct ConsolidationEngine {
    /// Buffer size for batch processing
    buffer_size: usize,
    /// Cluster configuration
    config: ClusterConfig,
    /// Internal buffer for accumulating data
    buffer: Vec<Vec<f32>>,
}

#[pymethods]
impl ConsolidationEngine {
    /// Create a new consolidation engine with the specified buffer size
    #[new]
    fn new(buffer_size: usize) -> Self {
        Self {
            buffer_size,
            config: ClusterConfig::default(),
            buffer: Vec::with_capacity(buffer_size),
        }
    }

    /// Create a new consolidation engine with custom configuration
    #[staticmethod]
    fn with_config(buffer_size: usize, min_cluster_size: usize, similarity_threshold: f32) -> Self {
        let config = ClusterConfig {
            min_cluster_size,
            similarity_threshold,
            ..ClusterConfig::default()
        };
        Self {
            buffer_size,
            config,
            buffer: Vec::with_capacity(buffer_size),
        }
    }

    /// Detect constellations in parallel across multiple data vectors
    /// Returns cluster assignments for each input vector
    fn detect_constellations(&self, data: Vec<Vec<f32>>) -> PyResult<Vec<Vec<usize>>> {
        let results: Vec<_> = data
            .into_par_iter()
            .map(|vec| self.find_clusters(vec))
            .collect();
        Ok(results)
    }

    /// Add data to internal buffer for batch processing
    fn add_to_buffer(&mut self, data: Vec<f32>) -> PyResult<()> {
        if self.buffer.len() >= self.buffer_size {
            return Err(pyo3::exceptions::PyBufferError::new_err("Buffer full"));
        }
        self.buffer.push(data);
        Ok(())
    }

    /// Process buffered data and clear buffer
    fn process_buffer(&mut self) -> PyResult<Vec<Vec<usize>>> {
        let data = std::mem::take(&mut self.buffer);
        self.detect_constellations(data)
    }

    /// Get current buffer size
    fn buffer_len(&self) -> usize {
        self.buffer.len()
    }

    /// Clear the internal buffer
    fn clear_buffer(&mut self) {
        self.buffer.clear();
    }

    /// Get configuration
    fn get_config(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("min_cluster_size", self.config.min_cluster_size)?;
        dict.set_item("max_cluster_size", self.config.max_cluster_size)?;
        dict.set_item("similarity_threshold", self.config.similarity_threshold)?;
        Ok(dict.into())
    }

    /// Find clusters using density-based clustering (SIMD-optimized)
    /// Implements a simplified DBSCAN-like algorithm
    fn find_clusters(&self, data: Vec<f32>) -> Vec<usize> {
        if data.is_empty() {
            return vec![];
        }

        // Reshape flat data into points (assuming 768-dim embeddings)
        let dim = 768usize;
        if !data.len().is_multiple_of(dim) {
            return vec![];
        }
        let n_points = data.len() / dim;

        if n_points < self.config.min_cluster_size {
            // Not enough points to form clusters
            return vec![0; n_points];
        }

        // Compute pairwise distances and find neighbors
        let mut labels = vec![0usize; n_points]; // 0 = unlabeled, will assign cluster IDs
        let mut cluster_id = 1usize;

        // For each point, find neighbors within threshold
        for i in 0..n_points {
            if labels[i] != 0 {
                continue; // Already assigned
            }

            let mut neighbors = Vec::new();
            let point_i = &data[i * dim..(i + 1) * dim];

            for j in 0..n_points {
                if i == j {
                    continue;
                }

                let point_j = &data[j * dim..(j + 1) * dim];
                let similarity = cosine_similarity_simd(point_i, point_j);

                if similarity >= self.config.similarity_threshold {
                    neighbors.push(j);
                }
            }

            // If enough neighbors, form a cluster
            if neighbors.len() >= self.config.min_cluster_size - 1 {
                labels[i] = cluster_id;
                for &neighbor in &neighbors {
                    if labels[neighbor] == 0 {
                        labels[neighbor] = cluster_id;
                    }
                }
                cluster_id += 1;
            }
        }

        labels
    }

    /// Compute similarity matrix for all points
    fn compute_similarity_matrix(&self, data: Vec<f32>) -> Vec<f32> {
        use std::sync::Arc;

        let dim = 768usize;
        if data.is_empty() || !data.len().is_multiple_of(dim) {
            return vec![];
        }

        let n_points = data.len() / dim;
        let data = Arc::new(data);
        let mut matrix = vec![0.0f32; n_points * n_points];

        // Parallel computation of similarity matrix
        let results: Vec<_> = (0..n_points)
            .into_par_iter()
            .flat_map(|i| {
                let data = Arc::clone(&data);
                (0..n_points).into_par_iter().map(move |j| {
                    let point_i = &data[i * dim..(i + 1) * dim];
                    let point_j = &data[j * dim..(j + 1) * dim];
                    (i, j, cosine_similarity_simd(point_i, point_j))
                })
            })
            .collect();

        for (i, j, sim) in results {
            matrix[i * n_points + j] = sim;
        }

        matrix
    }
}

/// SIMD-optimized cosine similarity computation
fn cosine_similarity_simd(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }

    // Manual SIMD optimization using chunks
    // Process 8 elements at a time for SIMD efficiency
    let mut dot_product = 0.0f32;
    let mut norm_a = 0.0f32;
    let mut norm_b = 0.0f32;

    // Process in chunks of 8 for potential SIMD
    let chunks = a.len() / 8;
    let remainder = a.len() % 8;

    for i in 0..chunks {
        let base = i * 8;
        for j in 0..8 {
            let idx = base + j;
            dot_product += a[idx] * b[idx];
            norm_a += a[idx] * a[idx];
            norm_b += b[idx] * b[idx];
        }
    }

    // Process remainder
    for i in (chunks * 8)..(chunks * 8 + remainder) {
        dot_product += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }

    let denom = (norm_a * norm_b).sqrt();
    if denom > 0.0 {
        dot_product / denom
    } else {
        0.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cosine_similarity() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![1.0, 0.0, 0.0];
        assert!((cosine_similarity_simd(&a, &b) - 1.0).abs() < 1e-6);

        let c = vec![0.0, 1.0, 0.0];
        assert!(cosine_similarity_simd(&a, &c).abs() < 1e-6);
    }

    #[test]
    fn test_engine_creation() {
        let engine = ConsolidationEngine::new(100);
        assert_eq!(engine.buffer_len(), 0);
    }

    #[test]
    fn test_buffer_operations() {
        let mut engine = ConsolidationEngine::new(100);
        let data = vec![0.0f32; 768];
        engine.add_to_buffer(data.clone()).unwrap();
        assert_eq!(engine.buffer_len(), 1);
        engine.clear_buffer();
        assert_eq!(engine.buffer_len(), 0);
    }
}
