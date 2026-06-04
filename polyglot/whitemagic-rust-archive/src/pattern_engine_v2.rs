//! Pattern Engine V2 - Pattern Matching and Extraction (PSR-004)
//! Target: 100× speedup for pattern operations
//! Note: pattern_engine.rs exists, this is an extended version

use pyo3::prelude::*;
use std::collections::HashMap;
use rayon::prerev::*;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Pattern {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub pattern_type: String,
    #[pyo3(get)]
    pub content: String,
    #[pyo3(get)]
    pub frequency: usize,
    #[pyo3(get)]
    pub confidence: f64,
}

#[pymethods]
impl Pattern {
    #[new]
    fn new(id: String, pattern_type: String, content: String, frequency: usize, confidence: f64) -> Self {
        Self {
            id,
            pattern_type,
            content,
            frequency,
            confidence,
        }
    }
}

#[pyclass]
pub struct PyPatternEngineV2 {
    patterns: HashMap<String, Pattern>,
    pattern_index: HashMap<String, Vec<String>>,
}

#[pymethods]
impl PyPatternEngineV2 {
    #[new]
    fn new() -> Self {
        Self {
            patterns: HashMap::new(),
            pattern_index: HashMap::new(),
        }
    }

    fn add_pattern(&mut self, pattern: Pattern) {
        let id = pattern.id.clone();
        let pattern_type = pattern.pattern_type.clone();
        
        self.patterns.insert(id.clone(), pattern);
        
        self.pattern_index
            .entry(pattern_type)
            .or_insert_with(Vec::new)
            .push(id);
    }

    fn extract_patterns(&self, text: String, min_frequency: usize) -> Vec<Pattern> {
        let words: Vec<String> = text
            .split_whitespace()
            .map(|s| s.to_lowercase())
            .collect();
        
        let mut frequency_map: HashMap<String, usize> = HashMap::new();
        
        for word in &words {
            if word.len() > 3 {
                *frequency_map.entry(word.clone()).or_insert(0) += 1;
            }
        }
        
        frequency_map
            .into_iter()
            .filter(|(_, freq)| *freq >= min_frequency)
            .map(|(word, freq)| Pattern {
                id: format!("pattern_{}", word),
                pattern_type: "word".to_string(),
                content: word,
                frequency: freq,
                confidence: (freq as f64 / words.len() as f64).min(1.0),
            })
            .collect()
    }

    fn match_pattern(&self, text: String, pattern_id: String) -> bool {
        if let Some(pattern) = self.patterns.get(&pattern_id) {
            text.to_lowercase().contains(&pattern.content.to_lowercase())
        } else {
            false
        }
    }

    fn find_similar_patterns(&self, pattern_id: String, threshold: f64) -> Vec<Pattern> {
        if let Some(target) = self.patterns.get(&pattern_id) {
            self.patterns
                .values()
                .filter(|p| {
                    p.id != target.id && self.similarity(&target.content, &p.content) >= threshold
                })
                .cloned()
                .collect()
        } else {
            Vec::new()
        }
    }

    fn get_patterns_by_type(&self, pattern_type: String) -> Vec<Pattern> {
        if let Some(ids) = self.pattern_index.get(&pattern_type) {
            ids.iter()
                .filter_map(|id| self.patterns.get(id).cloned())
                .collect()
        } else {
            Vec::new()
        }
    }

    fn get_top_patterns(&self, n: usize) -> Vec<Pattern> {
        let mut patterns: Vec<Pattern> = self.patterns.values().cloned().collect();
        patterns.sort_by(|a, b| b.frequency.cmp(&a.frequency));
        patterns.truncate(n);
        patterns
    }

    fn pattern_count(&self) -> usize {
        self.patterns.len()
    }

    fn clear(&mut self) {
        self.patterns.clear();
        self.pattern_index.clear();
    }
}

impl PyPatternEngineV2 {
    fn similarity(&self, a: &str, b: &str) -> f64 {
        let words_a: std::collections::HashSet<String> = 
            a.split_whitespace().map(|s| s.to_lowercase()).collect();
        let words_b: std::collections::HashSet<String> = 
            b.split_whitespace().map(|s| s.to_lowercase()).collect();
        
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
    fn test_engine_creation() {
        let engine = PyPatternEngineV2::new();
        assert_eq!(engine.pattern_count(), 0);
    }

    #[test]
    fn test_add_pattern() {
        let mut engine = PyPatternEngineV2::new();
        let pattern = Pattern::new(
            "p1".to_string(),
            "test".to_string(),
            "content".to_string(),
            5,
            0.8,
        );
        
        engine.add_pattern(pattern);
        assert_eq!(engine.pattern_count(), 1);
    }

    #[test]
    fn test_extract_patterns() {
        let engine = PyPatternEngineV2::new();
        let text = "hello world hello world hello".to_string();
        
        let patterns = engine.extract_patterns(text, 2);
        assert!(!patterns.is_empty());
    }

    #[test]
    fn test_match_pattern() {
        let mut engine = PyPatternEngineV2::new();
        let pattern = Pattern::new(
            "p1".to_string(),
            "test".to_string(),
            "hello".to_string(),
            1,
            1.0,
        );
        
        engine.add_pattern(pattern);
        
        assert!(engine.match_pattern("hello world".to_string(), "p1".to_string()));
    }
}
