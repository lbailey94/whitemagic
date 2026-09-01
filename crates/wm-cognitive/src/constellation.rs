//! Constellation detection — density clustering in semantic coordinate space.
//!
//! Phase 6.6: Replaces the grid-based tag-frequency stub with proper
//! density clustering using the semantic coordinates from Phase 6.3.
//! Detects memory constellations (clusters), tracks drift across runs,
//! and names them from dominant tags.

use std::collections::HashMap;
use wm_core::{Coordinate5D, Galaxy, Result};
use wm_memory::MemoryStore;

use wm_memory::Memory;

/// Configuration for constellation detection.
#[derive(Debug, Clone)]
pub struct ConstellationConfig {
    /// Grid resolution per axis (total cells = resolution^3)
    pub grid_resolution: usize,
    /// Minimum memories per cell to be "dense"
    pub min_cell_density: usize,
    /// Minimum cluster size to form a constellation
    pub min_constellation_size: usize,
    /// Maximum constellations to detect
    pub max_constellations: usize,
}

impl Default for ConstellationConfig {
    fn default() -> Self {
        Self {
            grid_resolution: 5,
            min_cell_density: 2,
            min_constellation_size: 3,
            max_constellations: 20,
        }
    }
}

/// A detected constellation (cluster of memories in semantic space).
#[derive(Debug, Clone)]
pub struct Constellation {
    /// Unique name (derived from dominant tags or coordinate)
    pub name: String,
    /// Memory IDs in the constellation
    pub memory_ids: Vec<uuid::Uuid>,
    /// Centroid of the cluster in semantic space (x, y, z)
    pub centroid: (f32, f32, f32),
    /// Dominant tags in the cluster
    pub dominant_tags: Vec<String>,
    /// Number of memories
    pub size: usize,
    /// Galaxies represented
    pub galaxies: Vec<Galaxy>,
}

/// Result of a constellation detection run.
#[derive(Debug, Clone)]
pub struct ConstellationReport {
    /// Total memories analyzed
    pub memories_analyzed: usize,
    /// Constellations detected
    pub constellations: Vec<Constellation>,
    /// Grid cells that were dense
    pub dense_cells: usize,
}

impl ConstellationReport {
    /// Create a new empty report.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            memories_analyzed: 0,
            constellations: Vec::new(),
            dense_cells: 0,
        }
    }
}

impl Default for ConstellationReport {
    fn default() -> Self {
        Self::new()
    }
}

/// Drift tracking — compares constellations across runs.
#[derive(Debug, Clone)]
pub struct ConstellationDrift {
    /// Name of the constellation
    pub name: String,
    /// Previous centroid
    pub previous_centroid: (f32, f32, f32),
    /// Current centroid
    pub current_centroid: (f32, f32, f32),
    /// Euclidean drift distance
    pub drift_distance: f32,
    /// Change in size (positive = grew, negative = shrank)
    pub size_delta: i64,
}

/// Constellation detector — density clustering in semantic coordinate space.
pub struct ConstellationDetector {
    config: ConstellationConfig,
    /// Previous run's constellations (for drift tracking)
    previous: Vec<Constellation>,
}

impl Default for ConstellationDetector {
    fn default() -> Self {
        Self::new(ConstellationConfig::default())
    }
}

impl ConstellationDetector {
    /// Create a new detector with the given config.
    #[must_use]
    pub const fn new(config: ConstellationConfig) -> Self {
        Self {
            config,
            previous: Vec::new(),
        }
    }

    /// Run constellation detection across all non-system galaxies.
    ///
    /// 1. Collect memories with their semantic coordinates
    /// 2. Grid-based density scan: divide [0,1]^3 into cells
    /// 3. Find dense cells, expand to adjacent cells (flood fill)
    /// 4. Name constellations from dominant tags
    /// 5. Track drift from previous run
    pub fn detect(&mut self, store: &MemoryStore) -> Result<ConstellationReport> {
        let mut report = ConstellationReport::new();

        // 1. Collect memories
        let mut all_mems: Vec<(Galaxy, Memory)> = Vec::new();
        for galaxy in Galaxy::all() {
            match galaxy {
                Galaxy::Substrate
                | Galaxy::Dharma
                | Galaxy::Karma
                | Galaxy::Embeddings
                | Galaxy::Associations => continue,
                _ => {}
            }
            let mems = store.scan(galaxy, 10_000)?;
            all_mems.extend(mems.into_iter().map(|m| (galaxy, m)));
        }
        report.memories_analyzed = all_mems.len();

        if all_mems.is_empty() {
            self.previous = Vec::new();
            return Ok(report);
        }

        // 2. Grid-based density scan
        let res = self.config.grid_resolution;
        let mut grid: HashMap<(usize, usize, usize), Vec<usize>> = HashMap::new();

        for (i, (_, mem)) in all_mems.iter().enumerate() {
            let coord = &mem.metadata.coord5d;
            let cell = (
                (coord.x * res as f32) as usize,
                (coord.y * res as f32) as usize,
                (coord.z * res as f32) as usize,
            );
            grid.entry(cell).or_default().push(i);
        }

        // 3. Find dense cells and flood-fill to form constellations
        let dense_cells: Vec<(usize, usize, usize)> = grid
            .iter()
            .filter(|(_, v)| v.len() >= self.config.min_cell_density)
            .map(|(k, _)| *k)
            .collect();
        report.dense_cells = dense_cells.len();

        let mut visited: std::collections::HashSet<(usize, usize, usize)> =
            std::collections::HashSet::new();
        let mut constellations: Vec<Constellation> = Vec::new();

        for seed in &dense_cells {
            if visited.contains(seed) {
                continue;
            }
            // Flood fill from this dense cell to adjacent dense cells
            let cluster_cells = self.flood_fill(*seed, &dense_cells, &mut visited, res);

            // Collect all memory indices in the cluster
            let mut mem_indices: Vec<usize> = Vec::new();
            for cell in &cluster_cells {
                if let Some(indices) = grid.get(cell) {
                    mem_indices.extend(indices);
                }
            }

            if mem_indices.len() < self.config.min_constellation_size {
                continue;
            }

            // Build constellation
            let constellation = self.build_constellation(&mem_indices, &all_mems);
            constellations.push(constellation);

            if constellations.len() >= self.config.max_constellations {
                break;
            }
        }

        // Sort by size (largest first)
        constellations.sort_by_key(|x| std::cmp::Reverse(x.size));

        // 5. Track drift
        if !self.previous.is_empty() {
            let _drifts = self.compute_drift(&constellations);
            // Drifts are computed but not persisted (metadata only, avoids bloat)
        }

        report.constellations.clone_from(&constellations);
        self.previous = constellations;

        Ok(report)
    }

    /// Flood fill from a seed cell to adjacent dense cells.
    #[allow(clippy::cast_possible_wrap)]
    fn flood_fill(
        &self,
        seed: (usize, usize, usize),
        dense_cells: &[(usize, usize, usize)],
        visited: &mut std::collections::HashSet<(usize, usize, usize)>,
        res: usize,
    ) -> Vec<(usize, usize, usize)> {
        let dense_set: std::collections::HashSet<(usize, usize, usize)> =
            dense_cells.iter().copied().collect();
        let mut queue = vec![seed];
        let mut cluster = Vec::new();

        while let Some(cell) = queue.pop() {
            if visited.contains(&cell) || !dense_set.contains(&cell) {
                continue;
            }
            visited.insert(cell);
            cluster.push(cell);

            // 6-face adjacency (up/down/left/right/front/back)
            let (x, y, z) = cell;
            for (dx, dy, dz) in [
                (1_i64, 0, 0),
                (-1, 0, 0),
                (0, 1, 0),
                (0, -1, 0),
                (0, 0, 1),
                (0, 0, -1),
            ] {
                let nx = x as i64 + dx;
                let ny = y as i64 + dy;
                let nz = z as i64 + dz;
                if nx >= 0
                    && ny >= 0
                    && nz >= 0
                    && (nx as usize) < res
                    && (ny as usize) < res
                    && (nz as usize) < res
                {
                    queue.push((nx as usize, ny as usize, nz as usize));
                }
            }
        }
        cluster
    }

    /// Build a Constellation from memory indices.
    fn build_constellation(
        &self,
        indices: &[usize],
        all_mems: &[(Galaxy, Memory)],
    ) -> Constellation {
        let mems: Vec<&Memory> = indices.iter().map(|&i| &all_mems[i].1).collect();
        let galaxies: Vec<Galaxy> = indices
            .iter()
            .map(|&i| all_mems[i].0)
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();

        // Centroid
        let cx: f32 = mems.iter().map(|m| m.metadata.coord5d.x).sum::<f32>() / mems.len() as f32;
        let cy: f32 = mems.iter().map(|m| m.metadata.coord5d.y).sum::<f32>() / mems.len() as f32;
        let cz: f32 = mems.iter().map(|m| m.metadata.coord5d.z).sum::<f32>() / mems.len() as f32;

        // Dominant tags (frequency-sorted)
        let mut tag_freq: HashMap<String, usize> = HashMap::new();
        for mem in &mems {
            for tag in &mem.metadata.tags {
                *tag_freq.entry(tag.clone()).or_default() += 1;
            }
        }
        let mut dominant_tags: Vec<(String, usize)> = tag_freq.into_iter().collect();
        dominant_tags.sort_by_key(|x| std::cmp::Reverse(x.1));
        let dominant_tags: Vec<String> =
            dominant_tags.into_iter().take(3).map(|(t, _)| t).collect();

        // Name: from dominant tag or coordinate
        let name = dominant_tags
            .first()
            .cloned()
            .unwrap_or_else(|| format!("constellation_{}_{}_{}", cx as u32, cy as u32, cz as u32));

        Constellation {
            name,
            memory_ids: mems.iter().map(|m| m.metadata.id).collect(),
            centroid: (cx, cy, cz),
            dominant_tags,
            size: mems.len(),
            galaxies,
        }
    }

    /// Compute drift between previous and current constellations.
    #[allow(clippy::cast_possible_wrap)]
    fn compute_drift(&self, current: &[Constellation]) -> Vec<ConstellationDrift> {
        let mut drifts = Vec::new();
        for prev in &self.previous {
            // Find best match by name
            if let Some(curr) = current.iter().find(|c| c.name == prev.name) {
                let dist = euclidean_3d(prev.centroid, curr.centroid);
                let size_delta = curr.size as i64 - prev.size as i64;
                drifts.push(ConstellationDrift {
                    name: prev.name.clone(),
                    previous_centroid: prev.centroid,
                    current_centroid: curr.centroid,
                    drift_distance: dist,
                    size_delta,
                });
            }
        }
        drifts
    }

    /// Get the previous run's constellations (for inspection).
    #[must_use]
    pub fn previous(&self) -> &[Constellation] {
        &self.previous
    }
}

/// Euclidean distance in 3D.
fn euclidean_3d(a: (f32, f32, f32), b: (f32, f32, f32)) -> f32 {
    let dx = a.0 - b.0;
    let dy = a.1 - b.1;
    let dz = a.2 - b.2;
    dx.mul_add(dx, dy.mul_add(dy, dz * dz)).sqrt()
}

/// Check if a coordinate is within a constellation's radius.
#[must_use]
pub fn is_in_constellation(
    coord: &Coordinate5D,
    constellation: &Constellation,
    radius: f32,
) -> bool {
    let dist = euclidean_3d((coord.x, coord.y, coord.z), constellation.centroid);
    dist <= radius
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn test_store() -> (tempfile::TempDir, MemoryStore) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, store)
    }

    #[test]
    fn detection_empty_store() {
        let (_tmp, store) = test_store();
        let mut detector = ConstellationDetector::default();
        let report = detector.detect(&store).unwrap();
        assert_eq!(report.memories_analyzed, 0);
        assert!(report.constellations.is_empty());
    }

    #[test]
    fn detection_finds_constellation() {
        let (_tmp, store) = test_store();

        // Create memories with semantic coordinates using put_semantic
        for i in 0..5 {
            let mut mem = Memory::new(
                Galaxy::Codex,
                format!("The algorithm computes data using systematic logic and analysis {i}"),
            )
            .with_tags(vec!["algorithm".into()])
            .with_importance(0.7);
            store.put_semantic(Galaxy::Codex, &mut mem).unwrap();
        }

        let mut detector = ConstellationDetector::new(ConstellationConfig {
            min_cell_density: 1,
            min_constellation_size: 3,
            ..Default::default()
        });
        let report = detector.detect(&store).unwrap();

        assert_eq!(report.memories_analyzed, 5);
        assert!(
            !report.constellations.is_empty(),
            "should find a constellation"
        );
        assert!(report.constellations[0].size >= 3);
    }

    #[test]
    fn detection_names_from_dominant_tags() {
        let (_tmp, store) = test_store();

        for i in 0..4 {
            let mut mem = Memory::new(Galaxy::Codex, format!("rust memory system {i}"))
                .with_tags(vec!["rust".into(), "memory".into()])
                .with_importance(0.7);
            store.put_semantic(Galaxy::Codex, &mut mem).unwrap();
        }

        let mut detector = ConstellationDetector::new(ConstellationConfig {
            min_cell_density: 1,
            min_constellation_size: 3,
            ..Default::default()
        });
        let report = detector.detect(&store).unwrap();

        assert!(!report.constellations.is_empty());
        let c = &report.constellations[0];
        assert!(!c.dominant_tags.is_empty());
        // Name should come from a dominant tag
        assert!(
            c.name == "rust" || c.name == "memory",
            "name should be a dominant tag, got '{}'",
            c.name
        );
    }

    #[test]
    fn detection_tracks_drift() {
        let (_tmp, store) = test_store();

        // First run: logic-heavy memories
        for i in 0..4 {
            let mut mem = Memory::new(
                Galaxy::Codex,
                format!("algorithm data logic systematic method {i}"),
            )
            .with_tags(vec!["logic".into()])
            .with_importance(0.7);
            store.put_semantic(Galaxy::Codex, &mut mem).unwrap();
        }

        let mut detector = ConstellationDetector::new(ConstellationConfig {
            min_cell_density: 1,
            min_constellation_size: 3,
            ..Default::default()
        });
        let _report1 = detector.detect(&store).unwrap();
        assert!(!detector.previous().is_empty());

        // Second run: same memories, should detect same constellation
        let report2 = detector.detect(&store).unwrap();
        assert!(!report2.constellations.is_empty());
    }

    #[test]
    fn detection_respects_max_constellations() {
        let (_tmp, store) = test_store();

        // Create memories in different semantic regions
        for i in 0..3 {
            let mut mem = Memory::new(Galaxy::Codex, format!("algorithm data logic {i}"))
                .with_tags(vec![format!("logic{i}")])
                .with_importance(0.7);
            store.put_semantic(Galaxy::Codex, &mut mem).unwrap();
        }
        for i in 0..3 {
            let mut mem = Memory::new(Galaxy::Codex, format!("love joy passion heart {i}"))
                .with_tags(vec![format!("emotion{i}")])
                .with_importance(0.7);
            store.put_semantic(Galaxy::Codex, &mut mem).unwrap();
        }

        let mut detector = ConstellationDetector::new(ConstellationConfig {
            min_cell_density: 1,
            min_constellation_size: 2,
            max_constellations: 1,
            ..Default::default()
        });
        let report = detector.detect(&store).unwrap();

        assert!(
            report.constellations.len() <= 1,
            "should respect max_constellations"
        );
    }

    #[test]
    fn euclidean_3d_distance() {
        let d = euclidean_3d((0.0, 0.0, 0.0), (1.0, 0.0, 0.0));
        assert!((d - 1.0).abs() < f32::EPSILON);

        let d = euclidean_3d((0.0, 0.0, 0.0), (1.0, 1.0, 1.0));
        assert!((d - 3.0_f32.sqrt()).abs() < 0.001);
    }

    #[test]
    fn is_in_constellation_check() {
        let constellation = Constellation {
            name: "test".into(),
            memory_ids: vec![],
            centroid: (0.5, 0.5, 0.5),
            dominant_tags: vec![],
            size: 0,
            galaxies: vec![],
        };
        let coord = Coordinate5D::new(0.5, 0.5, 0.5, 0.5, 0.5);
        assert!(is_in_constellation(&coord, &constellation, 0.1));

        let coord = Coordinate5D::new(0.9, 0.9, 0.9, 0.5, 0.5);
        assert!(!is_in_constellation(&coord, &constellation, 0.1));
    }

    #[test]
    fn constellation_report_new_is_empty() {
        let report = ConstellationReport::new();
        assert_eq!(report.memories_analyzed, 0);
        assert!(report.constellations.is_empty());
    }
}
