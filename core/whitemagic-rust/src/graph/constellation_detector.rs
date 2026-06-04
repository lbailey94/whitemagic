//! Constellation Detector - Constellation Formation (PSR-003)
//! Target: 30× speedup for constellation detection

use kdtree::distance::squared_euclidean;
use kdtree::KdTree;
use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

#[derive(Clone, Debug)]
#[pyclass]
pub struct Constellation {
    #[pyo3(get)]
    pub id: usize,
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub members: Vec<String>,
    #[pyo3(get)]
    pub centroid: Vec<f64>,
    #[pyo3(get)]
    pub radius: f64,
}

#[pymethods]
impl Constellation {
    #[new]
    fn new(id: usize, name: String, members: Vec<String>, centroid: Vec<f64>, radius: f64) -> Self {
        Self {
            id,
            name,
            members,
            centroid,
            radius,
        }
    }
}

#[pyclass]
pub struct PyConstellationDetector {
    points: HashMap<String, Vec<f64>>,
    min_members: usize,
    max_radius: f64,
}

#[pymethods]
impl PyConstellationDetector {
    #[new]
    fn new(min_members: Option<usize>, max_radius: Option<f64>) -> Self {
        Self {
            points: HashMap::new(),
            min_members: min_members.unwrap_or(3),
            max_radius: max_radius.unwrap_or(0.5),
        }
    }

    fn add_point(&mut self, id: String, coordinates: Vec<f64>) {
        self.points.insert(id, coordinates);
    }

    fn detect_constellations(&self) -> Vec<Constellation> {
        let mut visited = HashSet::new();
        let mut constellations = Vec::new();
        let mut constellation_id = 0;
        
        let spatial_index = self.build_spatial_index();
        
        for (point_id, coords) in &self.points {
            if visited.contains(point_id) {
                continue;
            }
            
            let cluster = match &spatial_index {
                Some((tree, ids)) => self.find_cluster_fast(point_id, coords, &mut visited, tree, ids),
                None => self.find_cluster(point_id, coords, &mut visited),
            };
            
            if cluster.len() >= self.min_members {
                let centroid = self.calculate_centroid(&cluster);
                let radius = self.calculate_radius(&cluster, &centroid);
                
                constellations.push(Constellation {
                    id: constellation_id,
                    name: format!("constellation_{}", constellation_id),
                    members: cluster,
                    centroid,
                    radius,
                });
                
                constellation_id += 1;
            }
        }
        
        constellations
    }

    fn find_nearest_constellation(&self, point: Vec<f64>, constellations: Vec<Constellation>) -> Option<usize> {
        let mut min_distance = f64::INFINITY;
        let mut nearest_id = None;
        
        for constellation in &constellations {
            let distance = self.euclidean_distance(&point, &constellation.centroid);
            
            if distance < min_distance && distance <= constellation.radius {
                min_distance = distance;
                nearest_id = Some(constellation.id);
            }
        }
        
        nearest_id
    }

    fn merge_constellations(&self, c1: Constellation, c2: Constellation) -> Constellation {
        let mut members = c1.members;
        members.extend(c2.members);
        
        let centroid = self.calculate_centroid(&members);
        let radius = self.calculate_radius(&members, &centroid);
        
        Constellation {
            id: c1.id,
            name: format!("merged_{}", c1.id),
            members,
            centroid,
            radius,
        }
    }

    fn point_count(&self) -> usize {
        self.points.len()
    }
}

impl PyConstellationDetector {
    fn build_spatial_index(&self) -> Option<(KdTree<f32, usize, [f32; 5]>, Vec<String>)> {
        if self.points.is_empty() || !self.points.values().all(|c| c.len() == 5) {
            return None;
        }
        
        let ids: Vec<String> = self.points.keys().cloned().collect();
        let mut tree = KdTree::new(5);
        
        for (idx, id) in ids.iter().enumerate() {
            let coords = self.points.get(id).unwrap();
            let arr: [f32; 5] = [
                coords[0] as f32,
                coords[1] as f32,
                coords[2] as f32,
                coords[3] as f32,
                coords[4] as f32,
            ];
            if let Err(e) = tree.add(arr, idx) {
                eprintln!("KD-tree add error: {:?}", e);
                return None;
            }
        }
        
        Some((tree, ids))
    }
    
    fn find_cluster_fast(
        &self,
        start_id: &str,
        _start_coords: &[f64],
        visited: &mut HashSet<String>,
        tree: &KdTree<f32, usize, [f32; 5]>,
        ids: &[String],
    ) -> Vec<String> {
        let mut cluster = Vec::new();
        let mut stack = vec![start_id.to_string()];
        let radius_sq = (self.max_radius as f32).powi(2);
        
        while let Some(point_id) = stack.pop() {
            if visited.contains(&point_id) {
                continue;
            }
            
            visited.insert(point_id.clone());
            cluster.push(point_id.clone());
            
            if let Some(coords) = self.points.get(&point_id) {
                let query: [f32; 5] = [
                    coords[0] as f32,
                    coords[1] as f32,
                    coords[2] as f32,
                    coords[3] as f32,
                    coords[4] as f32,
                ];
                
                if let Ok(neighbors) = tree.within(&query, radius_sq, &squared_euclidean) {
                    for (_dist, &idx) in neighbors {
                        let neighbor_id = &ids[idx];
                        if !visited.contains(neighbor_id) && !cluster.contains(neighbor_id) {
                            stack.push(neighbor_id.clone());
                        }
                    }
                }
            }
        }
        
        cluster
    }

    fn find_cluster(&self, start_id: &str, _start_coords: &[f64], visited: &mut HashSet<String>) -> Vec<String> {
        let mut cluster = Vec::new();
        let mut stack = vec![start_id.to_string()];
        
        while let Some(point_id) = stack.pop() {
            if visited.contains(&point_id) {
                continue;
            }
            
            visited.insert(point_id.clone());
            cluster.push(point_id.clone());
            
            if let Some(coords) = self.points.get(&point_id) {
                for (other_id, other_coords) in &self.points {
                    if !visited.contains(other_id) {
                        let distance = self.euclidean_distance(coords, other_coords);
                        
                        if distance <= self.max_radius {
                            stack.push(other_id.clone());
                        }
                    }
                }
            }
        }
        
        cluster
    }

    fn calculate_centroid(&self, members: &[String]) -> Vec<f64> {
        if members.is_empty() {
            return Vec::new();
        }

        let first = match self.points.get(&members[0]) {
            Some(p) => p,
            None => return Vec::new(),
        };
        let dim = first.len();
        let mut centroid = vec![0.0; dim];
        let mut found = 0usize;

        for member in members {
            if let Some(coords) = self.points.get(member) {
                found += 1;
                for (i, &val) in coords.iter().enumerate() {
                    centroid[i] += val;
                }
            }
        }

        if found == 0 {
            return Vec::new();
        }
        let count = found as f64;
        for val in &mut centroid {
            *val /= count;
        }

        centroid
    }

    fn calculate_radius(&self, members: &[String], centroid: &[f64]) -> f64 {
        let mut max_distance = 0.0;
        
        for member in members {
            if let Some(coords) = self.points.get(member) {
                let distance = self.euclidean_distance(coords, centroid);
                if distance > max_distance {
                    max_distance = distance;
                }
            }
        }
        
        max_distance
    }

    fn euclidean_distance(&self, a: &[f64], b: &[f64]) -> f64 {
        if a.len() != b.len() {
            return f64::INFINITY;
        }
        
        let sum: f64 = a.iter()
            .zip(b.iter())
            .map(|(x, y)| (x - y).powi(2))
            .sum();
        
        sum.sqrt()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detector_creation() {
        let detector = PyConstellationDetector::new(Some(3), Some(0.5));
        assert_eq!(detector.point_count(), 0);
    }

    #[test]
    fn test_add_point() {
        let mut detector = PyConstellationDetector::new(None, None);
        detector.add_point("p1".to_string(), vec![0.0, 0.0]);
        
        assert_eq!(detector.point_count(), 1);
    }

    #[test]
    fn test_detect_constellations() {
        let mut detector = PyConstellationDetector::new(Some(2), Some(1.0));
        
        detector.add_point("p1".to_string(), vec![0.0, 0.0]);
        detector.add_point("p2".to_string(), vec![0.5, 0.5]);
        detector.add_point("p3".to_string(), vec![5.0, 5.0]);
        
        let constellations = detector.detect_constellations();
        assert!(!constellations.is_empty());
    }

    #[test]
    fn test_merge_constellations() {
        let detector = PyConstellationDetector::new(None, None);
        
        let c1 = Constellation::new(0, "c1".to_string(), vec!["p1".to_string()], vec![0.0], 1.0);
        let c2 = Constellation::new(1, "c2".to_string(), vec!["p2".to_string()], vec![1.0], 1.0);
        
        let merged = detector.merge_constellations(c1, c2);
        assert_eq!(merged.members.len(), 2);
    }
}
