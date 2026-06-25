//! 6D Holographic Galaxy Memory (v23.1)
//!
//! Extends 5D coordinates with a galaxy partition dimension (G).
//! Each galaxy has its own 5-zone lifecycle (Core -> Far Edge).
//! Galaxies can be shared between AI instances with user consent.
//!
//! 6D Coordinate: (X: temporal, Y: semantic, Z: emotional, W: relational, V: importance, G: galaxy)

use std::collections::HashMap;

use crate::holographic::{Coordinate5D, Zone};

/// 6D holographic coordinate — 5D plus galaxy partition.
#[derive(Debug, Clone, PartialEq)]
pub struct Coordinate6D {
    pub inner: Coordinate5D,
    pub galaxy: String,
}

impl Coordinate6D {
    /// Create a new 6D coordinate from a 5D coordinate and galaxy name.
    pub fn new(coord: Coordinate5D, galaxy: impl Into<String>) -> Self {
        Self {
            inner: coord,
            galaxy: galaxy.into(),
        }
    }

    /// Create a 6D coordinate in the default `universal` galaxy.
    pub fn universal(coord: Coordinate5D) -> Self {
        Self::new(coord, "universal")
    }

    /// Get the galactic zone for this coordinate.
    pub fn zone(&self) -> Zone {
        // Zone is based on the V (importance) dimension within the galaxy
        Zone::from_valence(self.inner.v)
    }

    /// Get the galaxy name.
    pub fn galaxy_name(&self) -> &str {
        &self.galaxy
    }
}

/// Galaxy metadata — describes a cognitive galaxy's properties.
#[derive(Debug, Clone)]
pub struct GalaxyInfo {
    pub name: String,
    pub description: String,
    pub color: String,
    pub decay_multiplier: f64,
}

impl Default for GalaxyInfo {
    fn default() -> Self {
        Self {
            name: "universal".to_string(),
            description: "General-purpose memories (default)".to_string(),
            color: "#6b7280".to_string(),
            decay_multiplier: 1.0,
        }
    }
}

/// Galaxy Router — routes memories to galaxies based on source subsystem.
///
/// Maintains a registry of galaxies and a mapping from cognitive
/// subsystems to default galaxies.
pub struct GalaxyRouter {
    galaxies: HashMap<String, GalaxyInfo>,
    subsystem_map: HashMap<String, String>,
    overrides: HashMap<String, String>,
}

impl Default for GalaxyRouter {
    fn default() -> Self {
        Self::new()
    }
}

impl GalaxyRouter {
    /// Create a new GalaxyRouter with default galaxies registered.
    pub fn new() -> Self {
        let mut router = Self {
            galaxies: HashMap::new(),
            subsystem_map: HashMap::new(),
            overrides: HashMap::new(),
        };
        router.init_defaults();
        router
    }

    fn init_defaults(&mut self) {
        let defaults = [
            ("universal", "General-purpose memories (default)", "#6b7280", 1.0),
            ("self_learning", "RIL outcomes, pattern applications", "#3b82f6", 0.8),
            ("self_discovery", "Emergence insights, creative tensions", "#8b5cf6", 0.7),
            ("insight", "Briefings, foresight, predictions", "#f59e0b", 0.9),
            ("creative_solutions", "HRR analogies, dream artifacts", "#ec4899", 0.85),
            ("oracle", "Calibration, oracle suggestions", "#10b981", 0.6),
        ];

        for (name, desc, color, decay) in defaults {
            self.galaxies.insert(
                name.to_string(),
                GalaxyInfo {
                    name: name.to_string(),
                    description: desc.to_string(),
                    color: color.to_string(),
                    decay_multiplier: decay,
                },
            );
        }

        // Subsystem → galaxy mappings
        let mappings = [
            ("recursive_improvement_loop", "self_learning"),
            ("pattern_miner", "self_learning"),
            ("kaizen_engine", "self_learning"),
            ("guideline_evolution", "self_learning"),
            ("emergence_engine", "self_discovery"),
            ("bicameral_reasoner", "self_discovery"),
            ("corpus_callosum", "self_discovery"),
            ("multi_spectral_reasoner", "self_discovery"),
            ("insight_pipeline", "insight"),
            ("foresight_engine", "insight"),
            ("serendipity_engine", "insight"),
            ("predictive_engine", "insight"),
            ("self_model", "insight"),
            ("dream_cycle", "creative_solutions"),
            ("dream_artifact_writer", "creative_solutions"),
            ("hrr_engine", "creative_solutions"),
            ("narrative_compressor", "creative_solutions"),
            ("oracle", "oracle"),
            ("temporal_forecast_db", "oracle"),
            ("brier_score", "oracle"),
            ("prescience", "oracle"),
            ("user", "universal"),
            ("external", "universal"),
            ("mcp_bridge", "universal"),
            ("researcher", "universal"),
            ("knowledge_graph", "universal"),
        ];

        for (subsystem, galaxy) in mappings {
            self.subsystem_map.insert(subsystem.to_string(), galaxy.to_string());
        }
    }

    /// Register a new user-defined galaxy.
    pub fn register_galaxy(&mut self, name: &str, description: &str, color: &str, decay_multiplier: f64) {
        self.galaxies.insert(
            name.to_string(),
            GalaxyInfo {
                name: name.to_string(),
                description: description.to_string(),
                color: color.to_string(),
                decay_multiplier,
            },
        );
    }

    /// Override the default galaxy mapping for a subsystem.
    pub fn map_subsystem(&mut self, subsystem: &str, galaxy: &str) -> Result<(), String> {
        if !self.galaxies.contains_key(galaxy) {
            return Err(format!("Unknown galaxy: {}", galaxy));
        }
        self.overrides.insert(subsystem.to_string(), galaxy.to_string());
        Ok(())
    }

    /// Route a subsystem to its target galaxy.
    /// Metadata override takes highest priority, then runtime override, then default mapping.
    pub fn route(&self, subsystem: &str, metadata_galaxy: Option<&str>) -> String {
        // 1. Metadata override
        if let Some(g) = metadata_galaxy {
            if self.galaxies.contains_key(g) {
                return g.to_string();
            }
        }

        // 2. Runtime override
        if let Some(g) = self.overrides.get(subsystem) {
            return g.clone();
        }

        // 3. Default mapping
        if let Some(g) = self.subsystem_map.get(subsystem) {
            return g.clone();
        }

        // 4. Default to universal
        "universal".to_string()
    }

    /// Get info about a galaxy.
    pub fn get_galaxy(&self, name: &str) -> Option<&GalaxyInfo> {
        self.galaxies.get(name)
    }

    /// Get the decay multiplier for a galaxy.
    pub fn decay_multiplier(&self, galaxy: &str) -> f64 {
        self.galaxies.get(galaxy).map(|g| g.decay_multiplier).unwrap_or(1.0)
    }

    /// List all registered galaxy names.
    pub fn list_galaxies(&self) -> Vec<&str> {
        self.galaxies.keys().map(|s| s.as_str()).collect()
    }
}

/// Cross-galaxy Reciprocal Rank Fusion (RRF).
///
/// Fuses ranked results from multiple galaxies into a single ranking.
/// Each galaxy contributes its top-k results, and RRF combines them
/// with a galaxy weight factor.
pub fn cross_galaxy_rrf(
    galaxy_results: &[(String, Vec<(String, f64)>)],
    k: f64,
    galaxy_weights: &HashMap<String, f64>,
) -> Vec<(String, f64)> {
    let mut scores: HashMap<String, f64> = HashMap::new();

    for (galaxy, results) in galaxy_results {
        let weight = galaxy_weights.get(galaxy).copied().unwrap_or(1.0);
        for (rank, (id, score)) in results.iter().enumerate() {
            let rrf_score = weight * (1.0 / (k + (rank + 1) as f64));
            *scores.entry(id.clone()).or_insert(0.0) += rrf_score + score * 0.01;
        }
    }

    let mut fused: Vec<(String, f64)> = scores.into_iter().collect();
    fused.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    fused
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::holographic::Coordinate5D;

    #[test]
    fn test_coordinate_6d_default_galaxy() {
        let coord = Coordinate5D::new(0.5, 0.5, 0.5, 0.5, 0.5);
        let coord6d = Coordinate6D::universal(coord);
        assert_eq!(coord6d.galaxy, "universal");
    }

    #[test]
    fn test_coordinate_6d_custom_galaxy() {
        let coord = Coordinate5D::new(0.5, 0.5, 0.5, 0.5, 0.5);
        let coord6d = Coordinate6D::new(coord, "oracle");
        assert_eq!(coord6d.galaxy, "oracle");
    }

    #[test]
    fn test_galaxy_router_default_galaxies() {
        let router = GalaxyRouter::new();
        assert!(router.get_galaxy("universal").is_some());
        assert!(router.get_galaxy("oracle").is_some());
        assert!(router.get_galaxy("self_learning").is_some());
        assert!(router.get_galaxy("nonexistent").is_none());
    }

    #[test]
    fn test_galaxy_router_route_known_subsystem() {
        let router = GalaxyRouter::new();
        assert_eq!(router.route("dream_cycle", None), "creative_solutions");
        assert_eq!(router.route("oracle", None), "oracle");
        assert_eq!(router.route("emergence_engine", None), "self_discovery");
    }

    #[test]
    fn test_galaxy_router_route_unknown_subsystem() {
        let router = GalaxyRouter::new();
        assert_eq!(router.route("unknown_xyz", None), "universal");
    }

    #[test]
    fn test_galaxy_router_metadata_override() {
        let router = GalaxyRouter::new();
        assert_eq!(router.route("dream_cycle", Some("oracle")), "oracle");
    }

    #[test]
    fn test_galaxy_router_metadata_unknown_falls_back() {
        let router = GalaxyRouter::new();
        assert_eq!(router.route("dream_cycle", Some("nonexistent")), "creative_solutions");
    }

    #[test]
    fn test_galaxy_router_register_custom() {
        let mut router = GalaxyRouter::new();
        router.register_galaxy("custom", "My galaxy", "#ff0000", 0.5);
        assert!(router.get_galaxy("custom").is_some());
        assert_eq!(router.decay_multiplier("custom"), 0.5);
    }

    #[test]
    fn test_galaxy_router_map_subsystem() {
        let mut router = GalaxyRouter::new();
        router.register_galaxy("test_galaxy", "Test", "#000000", 1.0);
        router.map_subsystem("dream_cycle", "test_galaxy").unwrap();
        assert_eq!(router.route("dream_cycle", None), "test_galaxy");
    }

    #[test]
    fn test_galaxy_router_map_subsystem_unknown_galaxy() {
        let mut router = GalaxyRouter::new();
        assert!(router.map_subsystem("dream_cycle", "nonexistent").is_err());
    }

    #[test]
    fn test_decay_multiplier_oracle_slower_than_universal() {
        let router = GalaxyRouter::new();
        let oracle = router.decay_multiplier("oracle");
        let universal = router.decay_multiplier("universal");
        assert!(oracle < universal);
    }

    #[test]
    fn test_cross_galaxy_rrf() {
        let results = vec![
            ("universal".to_string(), vec![
                ("mem-1".to_string(), 0.9),
                ("mem-2".to_string(), 0.8),
            ]),
            ("oracle".to_string(), vec![
                ("mem-2".to_string(), 0.95),
                ("mem-3".to_string(), 0.7),
            ]),
        ];
        let mut weights = HashMap::new();
        weights.insert("universal".to_string(), 1.0);
        weights.insert("oracle".to_string(), 1.5);

        let fused = cross_galaxy_rrf(&results, 60.0, &weights);

        // mem-2 appears in both galaxies, should rank highest
        assert_eq!(fused[0].0, "mem-2");
        assert!(fused.len() == 3);
    }
}
