//! Association Engine - Association Management (PSR-001)
//! Target: 30-50× speedup for association operations

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Association {
    #[pyo3(get)]
    pub source_id: String,
    #[pyo3(get)]
    pub target_id: String,
    #[pyo3(get)]
    pub relation_type: String,
    #[pyo3(get)]
    pub strength: f64,
}

#[pymethods]
impl Association {
    #[new]
    fn new(source_id: String, target_id: String, relation_type: String, strength: f64) -> Self {
        Self {
            source_id,
            target_id,
            relation_type,
            strength,
        }
    }
}

#[pyclass]
pub struct PyAssociationEngine {
    associations: Arc<RwLock<Vec<Association>>>,
    index: Arc<RwLock<HashMap<String, Vec<usize>>>>,
}

#[pymethods]
impl PyAssociationEngine {
    #[new]
    fn new() -> Self {
        Self {
            associations: Arc::new(RwLock::new(Vec::new())),
            index: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn add_association(&self, assoc: Association) {
        let mut associations = self.associations.write();
        let mut index = self.index.write();
        
        let idx = associations.len();
        
        index
            .entry(assoc.source_id.clone())
            .or_insert_with(Vec::new)
            .push(idx);
        
        index
            .entry(assoc.target_id.clone())
            .or_insert_with(Vec::new)
            .push(idx);
        
        associations.push(assoc);
    }

    fn get_associations(&self, memory_id: String) -> Vec<Association> {
        let associations = self.associations.read();
        let index = self.index.read();
        
        if let Some(indices) = index.get(&memory_id) {
            indices
                .iter()
                .filter_map(|&idx| associations.get(idx).cloned())
                .collect()
        } else {
            Vec::new()
        }
    }

    fn get_by_type(&self, memory_id: String, relation_type: String) -> Vec<Association> {
        self.get_associations(memory_id)
            .into_iter()
            .filter(|a| a.relation_type == relation_type)
            .collect()
    }

    fn count(&self) -> usize {
        self.associations.read().len()
    }

    fn get_related(&self, memory_id: String, min_strength: Option<f64>) -> Vec<String> {
        let threshold = min_strength.unwrap_or(0.0);
        let associations = self.associations.read();
        let index = self.index.read();
        
        if let Some(indices) = index.get(&memory_id) {
            indices
                .iter()
                .filter_map(|&idx| {
                    associations.get(idx).and_then(|a| {
                        if a.strength >= threshold {
                            if a.source_id == memory_id {
                                Some(a.target_id.clone())
                            } else {
                                Some(a.source_id.clone())
                            }
                        } else {
                            None
                        }
                    })
                })
                .collect()
        } else {
            Vec::new()
        }
    }

    fn strongest_associations(&self, memory_id: String, limit: usize) -> Vec<Association> {
        let mut assocs = self.get_associations(memory_id);
        assocs.sort_by(|a, b| b.strength.partial_cmp(&a.strength).unwrap());
        assocs.truncate(limit);
        assocs
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_association() {
        let engine = PyAssociationEngine::new();
        let assoc = Association::new(
            "m1".to_string(),
            "m2".to_string(),
            "related".to_string(),
            0.8,
        );
        
        engine.add_association(assoc);
        assert_eq!(engine.count(), 1);
    }

    #[test]
    fn test_get_associations() {
        let engine = PyAssociationEngine::new();
        
        engine.add_association(Association::new(
            "m1".to_string(),
            "m2".to_string(),
            "related".to_string(),
            0.8,
        ));
        
        let assocs = engine.get_associations("m1".to_string());
        assert_eq!(assocs.len(), 1);
    }

    #[test]
    fn test_get_by_type() {
        let engine = PyAssociationEngine::new();
        
        engine.add_association(Association::new(
            "m1".to_string(),
            "m2".to_string(),
            "causes".to_string(),
            0.8,
        ));
        
        engine.add_association(Association::new(
            "m1".to_string(),
            "m3".to_string(),
            "related".to_string(),
            0.7,
        ));
        
        let causes = engine.get_by_type("m1".to_string(), "causes".to_string());
        assert_eq!(causes.len(), 1);
    }

    #[test]
    fn test_strongest_associations() {
        let engine = PyAssociationEngine::new();
        
        engine.add_association(Association::new(
            "m1".to_string(),
            "m2".to_string(),
            "related".to_string(),
            0.9,
        ));
        
        engine.add_association(Association::new(
            "m1".to_string(),
            "m3".to_string(),
            "related".to_string(),
            0.5,
        ));
        
        let strongest = engine.strongest_associations("m1".to_string(), 1);
        assert_eq!(strongest.len(), 1);
        assert_eq!(strongest[0].target_id, "m2");
    }
}
