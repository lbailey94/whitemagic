//! HNSW (Hierarchical Navigable Small World) Index for Approximate Nearest Neighbor Search
//! S026 VC3 - Target: 100x speedup for similarity search
//!
//! Implements the HNSW algorithm for sub-millisecond similarity search
//! on large embedding corpora (100K+ vectors).

#![allow(dead_code)]

use pyo3::prelude::*;
use rand::Rng;
use std::cmp::Ordering;
use std::collections::{BTreeSet, HashMap, HashSet};

/// Node in the HNSW graph
#[derive(Clone, Debug)]
struct Node {
    vector: Vec<f32>,
    level: usize,
    neighbors: HashMap<usize, Vec<String>>, // level -> neighbor IDs
}

/// Priority queue entry for search
#[derive(Clone, Debug)]
struct PQEntry {
    distance: f64,
    node_id: String,
}

impl PartialEq for PQEntry {
    fn eq(&self, other: &Self) -> bool {
        self.distance == other.distance
    }
}

impl Eq for PQEntry {}

impl PartialOrd for PQEntry {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for PQEntry {
    fn cmp(&self, other: &Self) -> Ordering {
        // Reverse order for min-heap behavior
        other
            .distance
            .partial_cmp(&self.distance)
            .unwrap_or(Ordering::Equal)
    }
}

#[pyclass]
pub struct HNSWIndex {
    dim: usize,
    m: usize,               // Max neighbors per layer
    ef_construction: usize, // Search width during construction
    max_level: usize,
    nodes: HashMap<String, Node>,
    entry_point: Option<String>,
    level_mult: f64, // Level multiplier (1/ln(M))
}

#[pymethods]
impl HNSWIndex {
    /// Create a new HNSW index
    #[new]
    fn new(dim: usize, m: Option<usize>, ef_construction: Option<usize>) -> Self {
        let m = m.unwrap_or(16);
        Self {
            dim,
            m,
            ef_construction: ef_construction.unwrap_or(200),
            max_level: 0,
            nodes: HashMap::new(),
            entry_point: None,
            level_mult: 1.0 / (m as f64).ln(),
        }
    }

    /// Add a vector to the index
    fn add_item(&mut self, memory_id: String, vector: Vec<f32>) -> PyResult<()> {
        if vector.len() != self.dim {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Vector dimension mismatch: expected {}, got {}",
                self.dim,
                vector.len()
            )));
        }

        let level = self.get_random_level();

        let node = Node {
            vector,
            level,
            neighbors: (0..=level).map(|l| (l, Vec::new())).collect(),
        };

        self.nodes.insert(memory_id.clone(), node);

        if self.entry_point.is_none() {
            self.entry_point = Some(memory_id.clone());
            self.max_level = level;
            return Ok(());
        }

        let entry = self.entry_point.clone().unwrap();

        // Find entry point at the same level
        let mut curr_node = entry.clone();
        let mut curr_dist = self.distance(
            &self.nodes.get(&curr_node).unwrap().vector,
            &self.nodes.get(&memory_id).unwrap().vector,
        );

        // Traverse from top level to the new node's level
        for l in (level + 1..=self.max_level).rev() {
            self.greedy_search(&memory_id, &mut curr_node, &mut curr_dist, l);
        }

        // For each level from new node's level down to 0
        for l in (0..=level.min(self.max_level)).rev() {
            let neighbors = self.search_layer(&memory_id, &curr_node, self.m * 2, l);

            // Connect to M nearest neighbors
            if let Some(node) = self.nodes.get_mut(&memory_id) {
                if let Some(neighbor_list) = node.neighbors.get_mut(&l) {
                    let m_max = if l == 0 { self.m * 2 } else { self.m };
                    *neighbor_list = neighbors.iter().take(m_max).cloned().collect();
                }
            }

            // Bidirectional connections - collect first to avoid borrow issues
            let neighbor_connections: Vec<(String, Vec<String>)> = self
                .nodes
                .get(&memory_id)
                .and_then(|n| n.neighbors.get(&l).cloned())
                .map(|neighbors| {
                    neighbors
                        .into_iter()
                        .map(|neighbor_id| {
                            let neighbor_list = self
                                .nodes
                                .get(&neighbor_id)
                                .and_then(|n| n.neighbors.get(&l).cloned())
                                .unwrap_or_default();
                            (neighbor_id, neighbor_list)
                        })
                        .collect()
                })
                .unwrap_or_default();

            for (neighbor_id, mut neighbor_list) in neighbor_connections {
                neighbor_list.push(memory_id.clone());
                let m_max = if l == 0 { self.m * 2 } else { self.m };
                if neighbor_list.len() > m_max {
                    // Prune to keep closest neighbors
                    let neighbor_vec = self.nodes.get(&neighbor_id).map(|n| n.vector.clone());
                    if let Some(neighbor_vec) = neighbor_vec {
                        let mut dists: Vec<(f64, String)> = neighbor_list
                            .iter()
                            .filter_map(|n| {
                                self.nodes.get(n).map(|node| {
                                    (self.distance(&neighbor_vec, &node.vector), n.clone())
                                })
                            })
                            .collect();
                        dists.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(Ordering::Equal));
                        neighbor_list = dists.into_iter().take(m_max).map(|(_, id)| id).collect();
                    }
                }
                if let Some(neighbor) = self.nodes.get_mut(&neighbor_id) {
                    if let Some(nl) = neighbor.neighbors.get_mut(&l) {
                        *nl = neighbor_list;
                    }
                }
            }
        }

        // Update entry point if new node has higher level
        if level > self.max_level {
            self.max_level = level;
            self.entry_point = Some(memory_id);
        }

        Ok(())
    }

    /// Search for k nearest neighbors
    fn search(&self, query: Vec<f32>, k: usize, ef: Option<usize>) -> PyResult<Vec<(String, f64)>> {
        let ef = ef.unwrap_or(50);

        if query.len() != self.dim {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Query dimension mismatch: expected {}, got {}",
                self.dim,
                query.len()
            )));
        }

        let entry = match &self.entry_point {
            Some(e) => e.clone(),
            None => return Ok(Vec::new()),
        };

        let mut curr_node = entry.clone();
        let mut curr_dist = self.distance(&query, &self.nodes.get(&curr_node).unwrap().vector);

        // Traverse from top level to level 1
        for l in (1..=self.max_level).rev() {
            self.greedy_search_query(&query, &mut curr_node, &mut curr_dist, l);
        }

        // Search at layer 0 with ef
        let results = self.search_layer_query(&query, &curr_node, ef, 0);

        // Return top k results as (id, similarity)
        let mut sorted_results: Vec<(String, f64)> = results
            .into_iter()
            .map(|(dist, id)| (id, 1.0 - dist)) // Convert distance to similarity
            .collect();
        sorted_results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal));
        sorted_results.truncate(k);

        Ok(sorted_results)
    }

    /// Get number of indexed vectors
    fn len(&self) -> usize {
        self.nodes.len()
    }

    /// Check if index is empty
    fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    /// Get dimension
    fn dimension(&self) -> usize {
        self.dim
    }

    /// Get max level
    fn max_level(&self) -> usize {
        self.max_level
    }

    /// Get all node IDs
    fn node_ids(&self) -> Vec<String> {
        self.nodes.keys().cloned().collect()
    }

    /// Get node vector
    fn get_vector(&self, node_id: String) -> Option<Vec<f32>> {
        self.nodes.get(&node_id).map(|n| n.vector.clone())
    }

    /// Get node neighbors at level
    fn get_neighbors(&self, node_id: String, level: usize) -> Vec<String> {
        self.nodes
            .get(&node_id)
            .and_then(|n| n.neighbors.get(&level))
            .cloned()
            .unwrap_or_default()
    }

    /// Batch cosine similarity calculation
    fn batch_cosine_similarity(
        &self,
        query: Vec<f32>,
        node_ids: Vec<String>,
    ) -> Vec<(String, f64)> {
        let mut results: Vec<(String, f64)> = node_ids
            .iter()
            .filter_map(|id| {
                self.nodes.get(id).map(|node| {
                    let dist = self.distance(&query, &node.vector);
                    (id.clone(), 1.0 - dist)
                })
            })
            .collect();
        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal));
        results
    }
}

impl HNSWIndex {
    /// Cosine distance (1 - cosine similarity)
    fn distance(&self, a: &[f32], b: &[f32]) -> f64 {
        let dot: f64 = a
            .iter()
            .zip(b.iter())
            .map(|(x, y)| (*x as f64) * (*y as f64))
            .sum();
        let norm_a: f64 = a.iter().map(|x| (*x as f64).powi(2)).sum::<f64>().sqrt();
        let norm_b: f64 = b.iter().map(|x| (*x as f64).powi(2)).sum::<f64>().sqrt();

        if norm_a > 0.0 && norm_b > 0.0 {
            1.0 - dot / (norm_a * norm_b)
        } else {
            1.0
        }
    }

    /// Generate random level with exponential decay
    fn get_random_level(&self) -> usize {
        let mut rng = rand::thread_rng();
        let mut level = 0;
        while rng.gen::<f64>() < 0.5 && level < 16 {
            level += 1;
        }
        level
    }

    /// Greedy search at a specific level
    fn greedy_search(
        &self,
        query_id: &str,
        curr_node: &mut String,
        curr_dist: &mut f64,
        level: usize,
    ) -> bool {
        let query = self.nodes.get(query_id).unwrap().vector.clone();
        self.greedy_search_query(&query, curr_node, curr_dist, level)
    }

    /// Greedy search with query vector
    fn greedy_search_query(
        &self,
        query: &[f32],
        curr_node: &mut String,
        curr_dist: &mut f64,
        level: usize,
    ) -> bool {
        let mut changed = true;
        while changed {
            changed = false;
            if let Some(node) = self.nodes.get(curr_node) {
                if let Some(neighbors) = node.neighbors.get(&level) {
                    for neighbor_id in neighbors {
                        if let Some(neighbor) = self.nodes.get(neighbor_id) {
                            let dist = self.distance(query, &neighbor.vector);
                            if dist < *curr_dist {
                                *curr_dist = dist;
                                *curr_node = neighbor_id.clone();
                                changed = true;
                            }
                        }
                    }
                }
            }
        }
        changed
    }

    /// Search layer for nearest neighbors
    fn search_layer(&self, query_id: &str, entry: &str, ef: usize, level: usize) -> Vec<String> {
        let query = self.nodes.get(query_id).unwrap().vector.clone();
        let entry_dist = self.distance(&query, &self.nodes.get(entry).unwrap().vector);

        let mut visited: HashSet<String> = HashSet::new();
        visited.insert(entry.to_string());

        let mut candidates: BTreeSet<PQEntry> = BTreeSet::new();
        candidates.insert(PQEntry {
            distance: entry_dist,
            node_id: entry.to_string(),
        });

        let mut results: Vec<PQEntry> = vec![PQEntry {
            distance: entry_dist,
            node_id: entry.to_string(),
        }];

        while !candidates.is_empty() {
            let candidate = candidates.iter().next().unwrap().clone();
            candidates.remove(&candidate);

            let furthest = results.last().map(|e| e.distance).unwrap_or(f64::MAX);

            if candidate.distance > furthest && results.len() >= ef {
                break;
            }

            if let Some(node) = self.nodes.get(&candidate.node_id) {
                if let Some(neighbors) = node.neighbors.get(&level) {
                    for neighbor_id in neighbors {
                        if visited.contains(neighbor_id) {
                            continue;
                        }
                        visited.insert(neighbor_id.clone());

                        if let Some(neighbor) = self.nodes.get(neighbor_id) {
                            let dist = self.distance(&query, &neighbor.vector);

                            if dist < furthest || results.len() < ef {
                                candidates.insert(PQEntry {
                                    distance: dist,
                                    node_id: neighbor_id.clone(),
                                });
                                results.push(PQEntry {
                                    distance: dist,
                                    node_id: neighbor_id.clone(),
                                });
                                results.sort_by(|a, b| {
                                    a.distance
                                        .partial_cmp(&b.distance)
                                        .unwrap_or(Ordering::Equal)
                                });

                                if results.len() > ef {
                                    results.pop(); // Remove furthest (last after sort)
                                }
                            }
                        }
                    }
                }
            }
        }

        results.into_iter().map(|e| e.node_id).collect()
    }

    /// Search layer with query vector
    fn search_layer_query(
        &self,
        query: &[f32],
        entry: &str,
        ef: usize,
        level: usize,
    ) -> Vec<(f64, String)> {
        let entry_dist = self.distance(query, &self.nodes.get(entry).unwrap().vector);

        let mut visited: HashSet<String> = HashSet::new();
        visited.insert(entry.to_string());

        let mut candidates: BTreeSet<PQEntry> = BTreeSet::new();
        candidates.insert(PQEntry {
            distance: entry_dist,
            node_id: entry.to_string(),
        });

        let mut results: Vec<PQEntry> = vec![PQEntry {
            distance: entry_dist,
            node_id: entry.to_string(),
        }];

        while !candidates.is_empty() {
            let candidate = candidates.iter().next().unwrap().clone();
            candidates.remove(&candidate);

            let furthest = results.last().map(|e| e.distance).unwrap_or(f64::MAX);

            if candidate.distance > furthest && results.len() >= ef {
                break;
            }

            if let Some(node) = self.nodes.get(&candidate.node_id) {
                if let Some(neighbors) = node.neighbors.get(&level) {
                    for neighbor_id in neighbors {
                        if visited.contains(neighbor_id) {
                            continue;
                        }
                        visited.insert(neighbor_id.clone());

                        if let Some(neighbor) = self.nodes.get(neighbor_id) {
                            let dist = self.distance(query, &neighbor.vector);

                            if dist < furthest || results.len() < ef {
                                candidates.insert(PQEntry {
                                    distance: dist,
                                    node_id: neighbor_id.clone(),
                                });
                                results.push(PQEntry {
                                    distance: dist,
                                    node_id: neighbor_id.clone(),
                                });
                                results.sort_by(|a, b| {
                                    a.distance
                                        .partial_cmp(&b.distance)
                                        .unwrap_or(Ordering::Equal)
                                });

                                if results.len() > ef {
                                    results.pop(); // Remove furthest (last after sort)
                                }
                            }
                        }
                    }
                }
            }
        }

        results
            .into_iter()
            .map(|e| (e.distance, e.node_id))
            .collect()
    }
}

// ---------------------------------------------------------------------------
// Python module registration
// ---------------------------------------------------------------------------

#[cfg(feature = "python")]
pub fn hnsw_index(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<HNSWIndex>()?;
    Ok(())
}
