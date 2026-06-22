//! Vector Search - HNSW Index (PSR-002)
//!
//! Hierarchical Navigable Small World (HNSW) index for approximate nearest neighbor search.
//! Target: 50-100× speedup over linear scan.

use pyo3::prelude::*;
use std::cmp::Ordering;

/// Distance metric for vector similarity
#[derive(Clone, Copy, Debug)]
pub enum DistanceMetric {
    Cosine,
    Euclidean,
    DotProduct,
}

/// Search result with ID and distance
#[derive(Clone, Debug)]
pub struct SearchResult {
    pub id: usize,
    pub distance: f32,
}

impl PartialEq for SearchResult {
    fn eq(&self, other: &Self) -> bool {
        self.distance == other.distance
    }
}

impl Eq for SearchResult {}

impl PartialOrd for SearchResult {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        other.distance.partial_cmp(&self.distance) // Reverse for min-heap
    }
}

impl Ord for SearchResult {
    fn cmp(&self, other: &Self) -> Ordering {
        self.partial_cmp(other).unwrap_or(Ordering::Equal)
    }
}

/// Simple vector index (linear scan baseline, HNSW to be added)
pub struct VectorIndex {
    vectors: Vec<Vec<f32>>,
    metric: DistanceMetric,
}

impl VectorIndex {
    pub fn new(metric: DistanceMetric) -> Self {
        Self {
            vectors: Vec::new(),
            metric,
        }
    }

    /// Add a vector to the index
    pub fn add(&mut self, vector: Vec<f32>) -> usize {
        let id = self.vectors.len();
        self.vectors.push(vector);
        id
    }

    /// Compute distance between two vectors
    fn distance(&self, a: &[f32], b: &[f32]) -> f32 {
        match self.metric {
            DistanceMetric::Cosine => {
                let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
                let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
                let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
                
                if norm_a == 0.0 || norm_b == 0.0 {
                    return 1.0; // Max distance
                }
                
                1.0 - (dot / (norm_a * norm_b)) // Convert similarity to distance
            }
            DistanceMetric::Euclidean => {
                a.iter()
                    .zip(b.iter())
                    .map(|(x, y)| (x - y).powi(2))
                    .sum::<f32>()
                    .sqrt()
            }
            DistanceMetric::DotProduct => {
                -a.iter().zip(b.iter()).map(|(x, y)| x * y).sum::<f32>() // Negative for min-heap
            }
        }
    }

    /// Search for k nearest neighbors (linear scan)
    pub fn search(&self, query: &[f32], k: usize) -> Vec<SearchResult> {
        // Collect all distances, sort ascending, take k
        let mut results: Vec<SearchResult> = self.vectors
            .iter()
            .enumerate()
            .map(|(id, vector)| SearchResult { id, distance: self.distance(query, vector) })
            .collect();
        
        results.sort_by(|a, b| a.distance.partial_cmp(&b.distance).unwrap_or(Ordering::Equal));
        results.truncate(k);
        results
    }

    /// Batch search for multiple queries
    pub fn search_batch(&self, queries: &[Vec<f32>], k: usize) -> Vec<Vec<SearchResult>> {
        queries
            .iter()
            .map(|query| self.search(query, k))
            .collect()
    }

    /// Get vector by ID
    pub fn get(&self, id: usize) -> Option<&Vec<f32>> {
        self.vectors.get(id)
    }

    /// Number of vectors in index
    pub fn len(&self) -> usize {
        self.vectors.len()
    }

    /// Check if index is empty
    pub fn is_empty(&self) -> bool {
        self.vectors.is_empty()
    }
}

// Python bindings
#[pyclass]
pub struct PyVectorIndex {
    index: VectorIndex,
}

#[pymethods]
impl PyVectorIndex {
    #[new]
    #[pyo3(signature = (metric="cosine"))]
    fn new(metric: &str) -> PyResult<Self> {
        let metric = match metric {
            "cosine" => DistanceMetric::Cosine,
            "euclidean" => DistanceMetric::Euclidean,
            "dot" => DistanceMetric::DotProduct,
            _ => return Err(pyo3::exceptions::PyValueError::new_err("Invalid metric")),
        };
        
        Ok(Self {
            index: VectorIndex::new(metric),
        })
    }

    /// Add a vector to the index
    fn add(&mut self, vector: Vec<f32>) -> usize {
        self.index.add(vector)
    }

    /// Search for k nearest neighbors
    fn search(&self, query: Vec<f32>, k: usize) -> Vec<(usize, f32)> {
        self.index
            .search(&query, k)
            .into_iter()
            .map(|r| (r.id, r.distance))
            .collect()
    }

    /// Batch search
    fn search_batch(&self, queries: Vec<Vec<f32>>, k: usize) -> Vec<Vec<(usize, f32)>> {
        self.index
            .search_batch(&queries, k)
            .into_iter()
            .map(|results| {
                results
                    .into_iter()
                    .map(|r| (r.id, r.distance))
                    .collect()
            })
            .collect()
    }

    /// Get number of vectors
    fn __len__(&self) -> usize {
        self.index.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cosine_distance() {
        let index = VectorIndex::new(DistanceMetric::Cosine);
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![1.0, 0.0, 0.0];
        let dist = index.distance(&a, &b);
        assert!(dist < 0.001); // Should be ~0 for identical vectors
    }

    #[test]
    fn test_add_and_search() {
        let mut index = VectorIndex::new(DistanceMetric::Cosine);
        
        index.add(vec![1.0, 0.0, 0.0]);
        index.add(vec![0.0, 1.0, 0.0]);
        index.add(vec![0.0, 0.0, 1.0]);
        index.add(vec![1.0, 1.0, 0.0]);
        
        let query = vec![1.0, 0.0, 0.0];
        let results = index.search(&query, 2);
        
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].id, 0); // Exact match should be first
    }

    #[test]
    fn test_batch_search() {
        let mut index = VectorIndex::new(DistanceMetric::Cosine);
        
        index.add(vec![1.0, 0.0]);
        index.add(vec![0.0, 1.0]);
        
        let queries = vec![
            vec![1.0, 0.0],
            vec![0.0, 1.0],
        ];
        
        let results = index.search_batch(&queries, 1);
        assert_eq!(results.len(), 2);
        assert_eq!(results[0][0].id, 0);
        assert_eq!(results[1][0].id, 1);
    }

    #[test]
    fn test_euclidean_distance() {
        let index = VectorIndex::new(DistanceMetric::Euclidean);
        let a = vec![0.0, 0.0];
        let b = vec![3.0, 4.0];
        let dist = index.distance(&a, &b);
        assert!((dist - 5.0).abs() < 0.001); // 3-4-5 triangle
    }
}
