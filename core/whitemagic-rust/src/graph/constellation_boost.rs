//! Constellation Boost - Graph-based Result Boosting (PSR-002)
//! Target: 30× speedup for constellation-aware search

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

#[derive(Clone, Debug)]
#[pyclass]
pub struct ConstellationMember {
    #[pyo3(get)]
    pub memory_id: String,
    #[pyo3(get)]
    pub constellation_id: usize,
    #[pyo3(get)]
    pub centrality: f64,
}

#[pymethods]
impl ConstellationMember {
    #[new]
    fn new(memory_id: String, constellation_id: usize, centrality: f64) -> Self {
        Self {
            memory_id,
            constellation_id,
            centrality,
        }
    }
}

#[pyclass]
pub struct PyConstellationBoost {
    constellations: HashMap<usize, Vec<String>>,
    member_map: HashMap<String, (usize, f64)>,
    boost_factor: f64,
}

#[pymethods]
impl PyConstellationBoost {
    #[new]
    fn new(boost_factor: Option<f64>) -> Self {
        Self {
            constellations: HashMap::new(),
            member_map: HashMap::new(),
            boost_factor: boost_factor.unwrap_or(1.5),
        }
    }

    fn add_constellation(&mut self, constellation_id: usize, members: Vec<ConstellationMember>) {
        let member_ids: Vec<String> = members.iter().map(|m| m.memory_id.clone()).collect();
        
        for member in members {
            self.member_map.insert(
                member.memory_id.clone(),
                (constellation_id, member.centrality),
            );
        }
        
        self.constellations.insert(constellation_id, member_ids);
    }

    fn boost_results(&self, results: Vec<(String, f64)>) -> Vec<(String, f64)> {
        let mut boosted = Vec::with_capacity(results.len());
        let mut seen_constellations: HashSet<usize> = HashSet::new();
        
        for (doc_id, score) in results {
            let mut final_score = score;
            
            if let Some((constellation_id, centrality)) = self.member_map.get(&doc_id) {
                // Boost if first member of constellation
                if !seen_constellations.contains(constellation_id) {
                    final_score *= self.boost_factor * (1.0 + centrality);
                    seen_constellations.insert(*constellation_id);
                } else {
                    // Smaller boost for additional members
                    final_score *= 1.0 + (centrality * 0.2);
                }
            }
            
            boosted.push((doc_id, final_score));
        }
        
        // Re-sort by boosted scores
        boosted.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        boosted
    }

    fn get_constellation_members(&self, constellation_id: usize) -> Option<Vec<String>> {
        self.constellations.get(&constellation_id).cloned()
    }

    fn get_member_constellation(&self, memory_id: String) -> Option<usize> {
        self.member_map.get(&memory_id).map(|(id, _)| *id)
    }

    fn constellation_count(&self) -> usize {
        self.constellations.len()
    }

    fn expand_with_constellation(&self, doc_id: String, limit: Option<usize>) -> Vec<String> {
        let mut results = vec![doc_id.clone()];
        
        if let Some((constellation_id, _)) = self.member_map.get(&doc_id) {
            if let Some(members) = self.constellations.get(constellation_id) {
                let max_results = limit.unwrap_or(10);
                
                for member in members {
                    if member != &doc_id && results.len() < max_results {
                        results.push(member.clone());
                    }
                }
            }
        }
        
        results
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_constellation() {
        let mut booster = PyConstellationBoost::new(Some(1.5));
        
        let members = vec![
            ConstellationMember::new("doc1".to_string(), 1, 0.9),
            ConstellationMember::new("doc2".to_string(), 1, 0.7),
        ];
        
        booster.add_constellation(1, members);
        
        assert_eq!(booster.constellation_count(), 1);
        assert_eq!(booster.get_member_constellation("doc1".to_string()), Some(1));
    }

    #[test]
    fn test_boost_results() {
        let mut booster = PyConstellationBoost::new(Some(2.0));
        
        let members = vec![
            ConstellationMember::new("doc1".to_string(), 1, 0.8),
            ConstellationMember::new("doc2".to_string(), 1, 0.6),
        ];
        
        booster.add_constellation(1, members);
        
        let results = vec![
            ("doc1".to_string(), 10.0),
            ("doc3".to_string(), 15.0),
        ];
        
        let boosted = booster.boost_results(results);
        
        // doc1 should be boosted significantly
        assert!(boosted[0].1 > 15.0);
    }

    #[test]
    fn test_expand_with_constellation() {
        let mut booster = PyConstellationBoost::new(None);
        
        let members = vec![
            ConstellationMember::new("doc1".to_string(), 1, 0.9),
            ConstellationMember::new("doc2".to_string(), 1, 0.8),
            ConstellationMember::new("doc3".to_string(), 1, 0.7),
        ];
        
        booster.add_constellation(1, members);
        
        let expanded = booster.expand_with_constellation("doc1".to_string(), Some(3));
        
        assert_eq!(expanded.len(), 3);
        assert_eq!(expanded[0], "doc1");
    }

    #[test]
    fn test_get_constellation_members() {
        let mut booster = PyConstellationBoost::new(None);
        
        let members = vec![
            ConstellationMember::new("doc1".to_string(), 1, 0.9),
            ConstellationMember::new("doc2".to_string(), 1, 0.8),
        ];
        
        booster.add_constellation(1, members);
        
        let retrieved = booster.get_constellation_members(1);
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().len(), 2);
    }
}
