//! Emergence Detector - Emergence Pattern Detection (PSR-004)
//! Target: 30× speedup for emergence detection

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
#[pyclass]
pub struct EmergencePattern {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub pattern_type: String,
    #[pyo3(get)]
    pub components: Vec<String>,
    #[pyo3(get)]
    pub strength: f64,
    #[pyo3(get)]
    pub timestamp: u64,
}

#[pymethods]
impl EmergencePattern {
    #[new]
    fn new(id: String, pattern_type: String, components: Vec<String>, strength: f64, timestamp: u64) -> Self {
        Self {
            id,
            pattern_type,
            components,
            strength,
            timestamp,
        }
    }
}

#[pyclass]
pub struct PyEmergenceDetector {
    observations: Vec<HashMap<String, f64>>,
    min_strength: f64,
    window_size: usize,
}

#[pymethods]
impl PyEmergenceDetector {
    #[new]
    fn new(min_strength: Option<f64>, window_size: Option<usize>) -> Self {
        Self {
            observations: Vec::new(),
            min_strength: min_strength.unwrap_or(0.5),
            window_size: window_size.unwrap_or(10),
        }
    }

    fn add_observation(&mut self, observation: HashMap<String, f64>) {
        self.observations.push(observation);
        
        if self.observations.len() > self.window_size * 2 {
            self.observations.remove(0);
        }
    }

    fn detect_patterns(&self) -> Vec<EmergencePattern> {
        let mut patterns = Vec::new();
        
        if self.observations.len() < self.window_size {
            return patterns;
        }
        
        let recent = &self.observations[self.observations.len() - self.window_size..];
        
        let correlations = self.calculate_correlations(recent);
        
        for ((comp1, comp2), strength) in correlations {
            if strength >= self.min_strength {
                patterns.push(EmergencePattern {
                    id: format!("{}_{}", comp1, comp2),
                    pattern_type: "correlation".to_string(),
                    components: vec![comp1, comp2],
                    strength,
                    timestamp: self.current_timestamp(),
                });
            }
        }
        
        patterns
    }

    fn detect_phase_transitions(&self) -> Vec<EmergencePattern> {
        let mut transitions = Vec::new();
        
        if self.observations.len() < 2 {
            return transitions;
        }
        
        for i in 1..self.observations.len() {
            let prev = &self.observations[i - 1];
            let curr = &self.observations[i];
            
            for (key, &curr_val) in curr {
                if let Some(&prev_val) = prev.get(key) {
                    let change = (curr_val - prev_val).abs();
                    
                    if change > 0.5 {
                        transitions.push(EmergencePattern {
                            id: format!("transition_{}", key),
                            pattern_type: "phase_transition".to_string(),
                            components: vec![key.clone()],
                            strength: change,
                            timestamp: i as u64,
                        });
                    }
                }
            }
        }
        
        transitions
    }

    fn detect_synchronization(&self) -> Vec<EmergencePattern> {
        let mut sync_patterns = Vec::new();
        
        if self.observations.len() < self.window_size {
            return sync_patterns;
        }
        
        let recent = &self.observations[self.observations.len() - self.window_size..];
        
        let all_keys: Vec<String> = recent
            .iter()
            .flat_map(|obs| obs.keys().cloned())
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        
        for i in 0..all_keys.len() {
            for j in (i + 1)..all_keys.len() {
                let sync_score = self.calculate_synchronization(&all_keys[i], &all_keys[j], recent);
                
                if sync_score >= self.min_strength {
                    sync_patterns.push(EmergencePattern {
                        id: format!("sync_{}_{}", all_keys[i], all_keys[j]),
                        pattern_type: "synchronization".to_string(),
                        components: vec![all_keys[i].clone(), all_keys[j].clone()],
                        strength: sync_score,
                        timestamp: self.current_timestamp(),
                    });
                }
            }
        }
        
        sync_patterns
    }

    fn observation_count(&self) -> usize {
        self.observations.len()
    }

    fn clear_observations(&mut self) {
        self.observations.clear();
    }
}

impl PyEmergenceDetector {
    fn calculate_correlations(&self, observations: &[HashMap<String, f64>]) -> HashMap<(String, String), f64> {
        let mut correlations = HashMap::new();
        
        let all_keys: Vec<String> = observations
            .iter()
            .flat_map(|obs| obs.keys().cloned())
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        
        for i in 0..all_keys.len() {
            for j in (i + 1)..all_keys.len() {
                let corr = self.pearson_correlation(&all_keys[i], &all_keys[j], observations);
                correlations.insert((all_keys[i].clone(), all_keys[j].clone()), corr);
            }
        }
        
        correlations
    }

    fn pearson_correlation(&self, key1: &str, key2: &str, observations: &[HashMap<String, f64>]) -> f64 {
        let values1: Vec<f64> = observations
            .iter()
            .filter_map(|obs| obs.get(key1).copied())
            .collect();
        
        let values2: Vec<f64> = observations
            .iter()
            .filter_map(|obs| obs.get(key2).copied())
            .collect();
        
        if values1.len() < 2 || values2.len() < 2 || values1.len() != values2.len() {
            return 0.0;
        }
        
        let mean1: f64 = values1.iter().sum::<f64>() / values1.len() as f64;
        let mean2: f64 = values2.iter().sum::<f64>() / values2.len() as f64;
        
        let mut numerator = 0.0;
        let mut sum1 = 0.0;
        let mut sum2 = 0.0;
        
        for i in 0..values1.len() {
            let diff1 = values1[i] - mean1;
            let diff2 = values2[i] - mean2;
            numerator += diff1 * diff2;
            sum1 += diff1 * diff1;
            sum2 += diff2 * diff2;
        }
        
        let denominator = (sum1 * sum2).sqrt();
        
        if denominator == 0.0 {
            return 0.0;
        }
        
        numerator / denominator
    }

    fn calculate_synchronization(&self, key1: &str, key2: &str, observations: &[HashMap<String, f64>]) -> f64 {
        let corr = self.pearson_correlation(key1, key2, observations);
        corr.abs()
    }

    fn current_timestamp(&self) -> u64 {
        self.observations.len() as u64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detector_creation() {
        let detector = PyEmergenceDetector::new(Some(0.5), Some(10));
        assert_eq!(detector.observation_count(), 0);
    }

    #[test]
    fn test_add_observation() {
        let mut detector = PyEmergenceDetector::new(None, None);
        let mut obs = HashMap::new();
        obs.insert("a".to_string(), 1.0);
        
        detector.add_observation(obs);
        assert_eq!(detector.observation_count(), 1);
    }

    #[test]
    fn test_detect_patterns() {
        let mut detector = PyEmergenceDetector::new(Some(0.0), Some(5));
        
        for i in 0..10 {
            let mut obs = HashMap::new();
            obs.insert("a".to_string(), i as f64);
            obs.insert("b".to_string(), i as f64 * 2.0);
            detector.add_observation(obs);
        }
        
        let patterns = detector.detect_patterns();
        assert!(!patterns.is_empty());
    }

    #[test]
    fn test_clear_observations() {
        let mut detector = PyEmergenceDetector::new(None, None);
        
        detector.add_observation(HashMap::new());
        detector.clear_observations();
        
        assert_eq!(detector.observation_count(), 0);
    }
}
