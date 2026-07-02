//! Spreading Activation Engine — Cross-Galaxy Memory Priming (Rust acceleration)
//!
//! Implements biologically-inspired spreading activation using a priority queue
//! with exponential decay. Designed for parallel execution across galaxy DBs.
//!
//! Activation model:
//!   new_activation = current * decay * edge_strength * galaxy_factor
//!
//! Where galaxy_factor = 1.0 for same-galaxy, cross_galaxy_factor for cross-galaxy.

use std::collections::{BinaryHeap, HashMap, HashSet};
use std::cmp::Ordering;

/// A node in the activation spreading graph.
#[derive(Debug, Clone)]
pub struct ActivationNode {
    pub memory_id: String,
    pub activation: f64,
    pub hop: usize,
    pub galaxy: String,
    pub title: String,
}

impl PartialEq for ActivationNode {
    fn eq(&self, other: &Self) -> bool {
        self.memory_id == other.memory_id
    }
}

impl Eq for ActivationNode {}

impl Ord for ActivationNode {
    fn cmp(&self, other: &Self) -> Ordering {
        // Higher activation = higher priority (max-heap)
        other.activation.partial_cmp(&self.activation).unwrap_or(Ordering::Equal)
    }
}

impl PartialOrd for ActivationNode {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// Result of a spreading activation pass.
#[derive(Debug, Clone)]
pub struct SpreadResult {
    pub seed_ids: Vec<String>,
    pub primed: Vec<ActivationNode>,
    pub total_activated: usize,
    pub cross_galaxy_links: usize,
    pub galaxies_reached: HashSet<String>,
}

/// Edge in the association graph.
#[derive(Debug, Clone)]
pub struct AssociationEdge {
    pub source_id: String,
    pub target_id: String,
    pub strength: f64,
    pub source_galaxy: String,
    pub target_galaxy: String,
}

/// Run spreading activation from seed nodes through a pre-loaded edge list.
///
/// This is the pure computation core — the caller is responsible for loading
/// edges from SQLite. This separation allows the Rust engine to be tested
/// without database dependencies and called via JSON stdio bridge.
pub fn spread_activation(
    seed_ids: &[String],
    edges: &[AssociationEdge],
    decay: f64,
    cross_galaxy_factor: f64,
    min_activation: f64,
    max_hops: usize,
    max_nodes: usize,
) -> SpreadResult {
    let mut queue: BinaryHeap<ActivationNode> = BinaryHeap::new();
    let mut visited: HashMap<String, f64> = HashMap::new();
    let mut primed: Vec<ActivationNode> = Vec::new();
    let mut galaxies_reached: HashSet<String> = HashSet::new();
    let mut cross_galaxy_links = 0usize;

    // Build adjacency list
    let mut adj: HashMap<String, Vec<(String, f64, String, String)>> = HashMap::new();
    for edge in edges {
        // Forward edge
        adj.entry(edge.source_id.clone())
            .or_default()
            .push((
                edge.target_id.clone(),
                edge.strength,
                edge.target_galaxy.clone(),
                edge.source_galaxy.clone(),
            ));
        // Reverse edge (associations are bidirectional)
        adj.entry(edge.target_id.clone())
            .or_default()
            .push((
                edge.source_id.clone(),
                edge.strength,
                edge.source_galaxy.clone(),
                edge.target_galaxy.clone(),
            ));
    }

    // Initialize seeds — resolve galaxy from edges
    for sid in seed_ids {
        // Find the seed's galaxy from edge metadata
        let galaxy = edges.iter()
            .find(|e| &e.source_id == sid)
            .map(|e| e.source_galaxy.clone())
            .or_else(|| edges.iter().find(|e| &e.target_id == sid).map(|e| e.target_galaxy.clone()))
            .unwrap_or_default();
        galaxies_reached.insert(galaxy.clone());
        visited.insert(sid.clone(), 1.0);
        queue.push(ActivationNode {
            memory_id: sid.clone(),
            activation: 1.0,
            hop: 0,
            galaxy,
            title: String::new(),
        });
    }

    // Best-first spreading
    while let Some(node) = queue.pop() {
        if node.activation < min_activation {
            continue;
        }

        if node.hop > 0 {
            primed.push(node.clone());
        }

        if primed.len() >= max_nodes || node.hop >= max_hops {
            continue;
        }

        // Get neighbors
        if let Some(neighbors) = adj.get(&node.memory_id) {
            for (nid, strength, n_galaxy, _source_galaxy) in neighbors {
                let galaxy_factor = if n_galaxy == &node.galaxy {
                    1.0
                } else {
                    cross_galaxy_factor
                };

                let new_activation = node.activation * decay * strength * galaxy_factor;

                if new_activation < min_activation {
                    continue;
                }

                // Check if already visited with higher activation
                if let Some(&existing) = visited.get(nid) {
                    if existing >= new_activation {
                        continue;
                    }
                }

                visited.insert(nid.clone(), new_activation);
                galaxies_reached.insert(n_galaxy.clone());

                if n_galaxy != &node.galaxy {
                    cross_galaxy_links += 1;
                }

                queue.push(ActivationNode {
                    memory_id: nid.clone(),
                    activation: new_activation,
                    hop: node.hop + 1,
                    galaxy: n_galaxy.clone(),
                    title: String::new(),
                });
            }
        }
    }

    // Sort by activation descending
    primed.sort_by(|a, b| {
        b.activation.partial_cmp(&a.activation).unwrap_or(Ordering::Equal)
    });

    let total_activated = primed.len();

    SpreadResult {
        seed_ids: seed_ids.to_vec(),
        primed,
        total_activated,
        cross_galaxy_links,
        galaxies_reached,
    }
}

/// Galaxy activation mask — weights for context-dependent gating.
#[derive(Debug, Clone)]
pub struct GalaxyMask {
    pub context: String,
    pub weights: HashMap<String, f64>,
}

impl GalaxyMask {
    pub fn get_weight(&self, galaxy: &str) -> f64 {
        self.weights.get(galaxy).copied().unwrap_or(1.0)
    }
}

/// Apply galaxy activation mask to search results.
///
/// Modifies importance scores by multiplying with galaxy-specific weights.
/// Returns results sorted by weighted importance (descending).
pub fn apply_galaxy_mask(
    results: &mut [(String, f64, String)],  // (memory_id, importance, galaxy)
    mask: &GalaxyMask,
) {
    for item in results.iter_mut() {
        let weight = mask.get_weight(&item.2);
        item.1 *= weight;
    }
    results.sort_by(|a, b| {
        b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal)
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_spread_basic() {
        let edges = vec![
            AssociationEdge {
                source_id: "a".into(),
                target_id: "b".into(),
                strength: 0.8,
                source_galaxy: "aria".into(),
                target_galaxy: "aria".into(),
            },
            AssociationEdge {
                source_id: "b".into(),
                target_id: "c".into(),
                strength: 0.6,
                source_galaxy: "aria".into(),
                target_galaxy: "aria".into(),
            },
        ];

        let result = spread_activation(
            &["a".to_string()],
            &edges,
            0.7,
            0.5,
            0.05,
            3,
            100,
        );

        assert!(result.total_activated > 0);
        assert!(result.galaxies_reached.contains("aria"));
    }

    #[test]
    fn test_spread_cross_galaxy() {
        let edges = vec![
            AssociationEdge {
                source_id: "a".into(),
                target_id: "b".into(),
                strength: 0.8,
                source_galaxy: "aria".into(),
                target_galaxy: "citta".into(),
            },
        ];

        let result = spread_activation(
            &["a".to_string()],
            &edges,
            0.7,
            0.5,
            0.05,
            2,
            100,
        );

        assert!(result.galaxies_reached.contains("citta"));
        assert!(result.cross_galaxy_links > 0);
    }

    #[test]
    fn test_spread_decay_reduces_activation() {
        let edges = vec![
            AssociationEdge {
                source_id: "a".into(),
                target_id: "b".into(),
                strength: 0.5,
                source_galaxy: "aria".into(),
                target_galaxy: "aria".into(),
            },
            AssociationEdge {
                source_id: "b".into(),
                target_id: "c".into(),
                strength: 0.5,
                source_galaxy: "aria".into(),
                target_galaxy: "aria".into(),
            },
        ];

        let result = spread_activation(
            &["a".to_string()],
            &edges,
            0.5,
            0.5,
            0.01,
            3,
            100,
        );

        // Hop 1 should have higher activation than hop 2
        let hop1: Vec<_> = result.primed.iter().filter(|n| n.hop == 1).collect();
        let hop2: Vec<_> = result.primed.iter().filter(|n| n.hop == 2).collect();

        if !hop1.is_empty() && !hop2.is_empty() {
            assert!(hop1[0].activation > hop2[0].activation);
        }
    }

    #[test]
    fn test_spread_min_activation_threshold() {
        let edges = vec![
            AssociationEdge {
                source_id: "a".into(),
                target_id: "b".into(),
                strength: 0.1,
                source_galaxy: "aria".into(),
                target_galaxy: "aria".into(),
            },
        ];

        let result = spread_activation(
            &["a".to_string()],
            &edges,
            0.3,
            0.5,
            0.5, // High threshold
            2,
            100,
        );

        // 1.0 * 0.3 * 0.1 = 0.03 < 0.5 threshold, should not activate
        assert_eq!(result.total_activated, 0);
    }

    #[test]
    fn test_spread_empty_seeds() {
        let result = spread_activation(
            &[],
            &[],
            0.7,
            0.5,
            0.05,
            3,
            100,
        );

        assert_eq!(result.total_activated, 0);
    }

    #[test]
    fn test_apply_galaxy_mask() {
        let mut results = vec![
            ("mem-1".to_string(), 0.5, "citta".to_string()),
            ("mem-2".to_string(), 0.9, "codex".to_string()),
        ];

        let mut weights = HashMap::new();
        weights.insert("citta".to_string(), 1.5);
        weights.insert("codex".to_string(), 0.3);

        let mask = GalaxyMask {
            context: "introspection".to_string(),
            weights,
        };

        apply_galaxy_mask(&mut results, &mask);

        // citta (0.5 * 1.5 = 0.75) should now rank above codex (0.9 * 0.3 = 0.27)
        assert_eq!(results[0].0, "mem-1");
        assert_eq!(results[0].1, 0.75);
    }

    #[test]
    fn test_apply_galaxy_mask_default_weight() {
        let mut results = vec![
            ("mem-1".to_string(), 0.5, "unknown_galaxy".to_string()),
        ];

        let mask = GalaxyMask {
            context: "test".to_string(),
            weights: HashMap::new(),
        };

        apply_galaxy_mask(&mut results, &mask);

        // Unknown galaxy should get default weight of 1.0
        assert_eq!(results[0].1, 0.5);
    }
}
