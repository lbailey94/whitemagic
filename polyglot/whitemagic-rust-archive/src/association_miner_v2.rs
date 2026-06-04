//! Association Miner V2 - Parallel Association Mining (PSR-003)
//! Target: 100× speedup for association discovery

use pyo3::prelude::*;
use rayon::prelude::*;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Association {
    #[pyo3(get)]
    pub source: String,
    #[pyo3(get)]
    pub target: String,
    #[pyo3(get)]
    pub association_type: String,
    #[pyo3(get)]
    pub strength: f64,
}

#[pymethods]
impl Association {
    #[new]
    fn new(source: String, target: String, association_type: String, strength: f64) -> Self {
        Self {
            source,
            target,
            association_type,
            strength,
        }
    }
}

#[pyclass]
pub struct PyAssociationMinerV2 {
    associations: Vec<Association>,
    min_strength: f64,
}

#[pymethods]
impl PyAssociationMinerV2 {
    #[new]
    fn new(min_strength: Option<f64>) -> Self {
        Self {
            associations: Vec::new(),
            min_strength: min_strength.unwrap_or(0.5),
        }
    }

    fn mine_associations(&mut self, items: Vec<String>) -> Vec<Association> {
        let mut discovered = Vec::new();
        
        for i in 0..items.len() {
            for j in (i + 1)..items.len() {
                let strength = self.calculate_strength(&items[i], &items[j]);
                
                if strength >= self.min_strength {
                    discovered.push(Association {
                        source: items[i].clone(),
                        target: items[j].clone(),
                        association_type: "co_occurrence".to_string(),
                        strength,
                    });
                }
            }
        }
        
        discovered
    }

    fn mine_parallel(&self, item_groups: Vec<Vec<String>>) -> Vec<Association> {
        let min_strength = self.min_strength;
        item_groups
            .par_iter()
            .flat_map(|group| mine_group(group, min_strength))
            .collect()
    }

    fn add_association(&mut self, association: Association) {
        self.associations.push(association);
    }

    fn get_associations(&self, source: String) -> Vec<Association> {
        self.associations
            .iter()
            .filter(|a| a.source == source || a.target == source)
            .cloned()
            .collect()
    }

    fn get_strongest_associations(&self, n: usize) -> Vec<Association> {
        let mut sorted = self.associations.clone();
        sorted.sort_by(|a, b| b.strength.partial_cmp(&a.strength).unwrap());
        sorted.truncate(n);
        sorted
    }

    fn association_count(&self) -> usize {
        self.associations.len()
    }
}

fn mine_group(items: &[String], min_strength: f64) -> Vec<Association> {
    let mut discovered = Vec::new();
    for i in 0..items.len() {
        for j in (i + 1)..items.len() {
            let words_a: std::collections::HashSet<&str> = items[i].split_whitespace().collect();
            let words_b: std::collections::HashSet<&str> = items[j].split_whitespace().collect();
            let intersection = words_a.intersection(&words_b).count();
            let union = words_a.union(&words_b).count();
            let strength = if union == 0 { 0.0 } else { intersection as f64 / union as f64 };
            if strength >= min_strength {
                discovered.push(Association {
                    source: items[i].clone(),
                    target: items[j].clone(),
                    association_type: "co_occurrence".to_string(),
                    strength,
                });
            }
        }
    }
    discovered
}

impl PyAssociationMinerV2 {
    fn calculate_strength(&self, item1: &str, item2: &str) -> f64 {
        let similarity = self.jaccard_similarity(item1, item2);
        similarity
    }

    fn jaccard_similarity(&self, a: &str, b: &str) -> f64 {
        let words_a: std::collections::HashSet<&str> = a.split_whitespace().collect();
        let words_b: std::collections::HashSet<&str> = b.split_whitespace().collect();
        
        let intersection = words_a.intersection(&words_b).count();
        let union = words_a.union(&words_b).count();
        
        if union == 0 {
            return 0.0;
        }
        
        intersection as f64 / union as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_miner_creation() {
        let miner = PyAssociationMinerV2::new(Some(0.5));
        assert_eq!(miner.association_count(), 0);
    }

    #[test]
    fn test_mine_associations() {
        let mut miner = PyAssociationMinerV2::new(Some(0.0));
        let items = vec!["hello world".to_string(), "world peace".to_string()];
        
        let associations = miner.mine_associations(items);
        assert!(!associations.is_empty());
    }

    #[test]
    fn test_add_association() {
        let mut miner = PyAssociationMinerV2::new(None);
        let assoc = Association::new("a".to_string(), "b".to_string(), "link".to_string(), 0.8);
        
        miner.add_association(assoc);
        assert_eq!(miner.association_count(), 1);
    }

    #[test]
    fn test_get_strongest() {
        let mut miner = PyAssociationMinerV2::new(None);
        
        miner.add_association(Association::new("a".to_string(), "b".to_string(), "link".to_string(), 0.5));
        miner.add_association(Association::new("c".to_string(), "d".to_string(), "link".to_string(), 0.9));
        
        let strongest = miner.get_strongest_associations(1);
        assert_eq!(strongest.len(), 1);
        assert_eq!(strongest[0].strength, 0.9);
    }
}
