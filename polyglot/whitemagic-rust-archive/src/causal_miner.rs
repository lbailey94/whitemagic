//! Causal Miner - Causal Inference (PSR-001)
//! Target: 50-100× speedup for causal mining

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
#[pyclass]
pub struct CausalRelation {
    #[pyo3(get)]
    pub cause: String,
    #[pyo3(get)]
    pub effect: String,
    #[pyo3(get)]
    pub strength: f64,
    #[pyo3(get)]
    pub confidence: f64,
}

#[pymethods]
impl CausalRelation {
    #[new]
    fn new(cause: String, effect: String, strength: f64, confidence: f64) -> Self {
        Self {
            cause,
            effect,
            strength,
            confidence,
        }
    }
}

#[pyclass]
pub struct PyCausalMiner {
    relations: Vec<CausalRelation>,
    temporal_window: f64,
}

#[pymethods]
impl PyCausalMiner {
    #[new]
    fn new(temporal_window: Option<f64>) -> Self {
        Self {
            relations: Vec::new(),
            temporal_window: temporal_window.unwrap_or(3600.0),
        }
    }

    fn add_relation(&mut self, relation: CausalRelation) {
        self.relations.push(relation);
    }

    fn mine_from_events(&mut self, events: Vec<(String, f64)>) -> Vec<CausalRelation> {
        let mut discovered = Vec::new();
        
        for i in 0..events.len() {
            for j in (i + 1)..events.len() {
                let (event_a, time_a) = &events[i];
                let (event_b, time_b) = &events[j];
                
                let time_diff = time_b - time_a;
                
                if time_diff > 0.0 && time_diff < self.temporal_window {
                    let strength = 1.0 / (1.0 + time_diff);
                    let confidence = 0.8;
                    
                    discovered.push(CausalRelation {
                        cause: event_a.clone(),
                        effect: event_b.clone(),
                        strength,
                        confidence,
                    });
                }
            }
        }
        
        discovered
    }

    fn get_causes(&self, effect: String) -> Vec<CausalRelation> {
        self.relations
            .iter()
            .filter(|r| r.effect == effect)
            .cloned()
            .collect()
    }

    fn get_effects(&self, cause: String) -> Vec<CausalRelation> {
        self.relations
            .iter()
            .filter(|r| r.cause == cause)
            .cloned()
            .collect()
    }

    fn get_strongest_cause(&self, effect: String) -> Option<CausalRelation> {
        self.relations
            .iter()
            .filter(|r| r.effect == effect)
            .max_by(|a, b| a.strength.partial_cmp(&b.strength).unwrap())
            .cloned()
    }

    fn relation_count(&self) -> usize {
        self.relations.len()
    }

    fn get_causal_chain(&self, start: String, max_depth: usize) -> Vec<Vec<String>> {
        let mut chains = Vec::new();
        let mut current_chain = vec![start.clone()];
        
        self.build_chain(&start, &mut current_chain, &mut chains, max_depth, 0);
        
        chains
    }
}

impl PyCausalMiner {
    fn build_chain(
        &self,
        current: &str,
        chain: &mut Vec<String>,
        chains: &mut Vec<Vec<String>>,
        max_depth: usize,
        depth: usize,
    ) {
        if depth >= max_depth {
            chains.push(chain.clone());
            return;
        }
        
        let effects = self.get_effects(current.to_string());
        
        if effects.is_empty() {
            chains.push(chain.clone());
            return;
        }
        
        for effect in effects {
            chain.push(effect.effect.clone());
            self.build_chain(&effect.effect, chain, chains, max_depth, depth + 1);
            chain.pop();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_miner_creation() {
        let miner = PyCausalMiner::new(Some(3600.0));
        assert_eq!(miner.relation_count(), 0);
    }

    #[test]
    fn test_add_relation() {
        let mut miner = PyCausalMiner::new(None);
        let relation = CausalRelation::new(
            "a".to_string(),
            "b".to_string(),
            0.8,
            0.9,
        );
        
        miner.add_relation(relation);
        assert_eq!(miner.relation_count(), 1);
    }

    #[test]
    fn test_mine_from_events() {
        let mut miner = PyCausalMiner::new(Some(100.0));
        
        let events = vec![
            ("event1".to_string(), 0.0),
            ("event2".to_string(), 50.0),
            ("event3".to_string(), 200.0),
        ];
        
        let discovered = miner.mine_from_events(events);
        
        assert_eq!(discovered.len(), 1);
        assert_eq!(discovered[0].cause, "event1");
        assert_eq!(discovered[0].effect, "event2");
    }

    #[test]
    fn test_get_causes() {
        let mut miner = PyCausalMiner::new(None);
        
        miner.add_relation(CausalRelation::new(
            "a".to_string(),
            "b".to_string(),
            0.8,
            0.9,
        ));
        
        miner.add_relation(CausalRelation::new(
            "c".to_string(),
            "b".to_string(),
            0.7,
            0.8,
        ));
        
        let causes = miner.get_causes("b".to_string());
        assert_eq!(causes.len(), 2);
    }

    #[test]
    fn test_get_strongest_cause() {
        let mut miner = PyCausalMiner::new(None);
        
        miner.add_relation(CausalRelation::new(
            "a".to_string(),
            "b".to_string(),
            0.8,
            0.9,
        ));
        
        miner.add_relation(CausalRelation::new(
            "c".to_string(),
            "b".to_string(),
            0.9,
            0.8,
        ));
        
        let strongest = miner.get_strongest_cause("b".to_string());
        assert!(strongest.is_some());
        assert_eq!(strongest.unwrap().cause, "c");
    }
}
