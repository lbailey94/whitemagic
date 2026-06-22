//! Emergence detection in patterns
//! Identifies novel emergent behaviors

use pyo3::prelude::*;

#[pyclass]
pub struct EmergenceDetector {
    novelty_threshold: f64,
}

#[pymethods]
impl EmergenceDetector {
    #[new]
    fn new(novelty_threshold: Option<f64>) -> Self {
        Self {
            novelty_threshold: novelty_threshold.unwrap_or(0.8),
        }
    }
    
    fn detect_emergence(
        &self,
        current_patterns: Vec<Vec<String>>,
        historical_patterns: Vec<Vec<String>>
    ) -> PyResult<Vec<Vec<String>>> {
        let emergent: Vec<Vec<String>> = current_patterns
            .into_iter()
            .filter(|pattern| {
                let similarity = Self::max_sim(pattern, &historical_patterns);
                similarity < self.novelty_threshold
            })
            .collect();
        Ok(emergent)
    }
}

impl EmergenceDetector {
    fn jaccard(a: &[String], b: &[String]) -> f64 {
        let set_a: std::collections::HashSet<_> = a.iter().collect();
        let set_b: std::collections::HashSet<_> = b.iter().collect();
        let intersection = set_a.intersection(&set_b).count();
        let union = set_a.union(&set_b).count();
        if union == 0 { 0.0 } else { intersection as f64 / union as f64 }
    }
    
    fn max_sim(pattern: &[String], historical: &[Vec<String>]) -> f64 {
        historical.iter().map(|h| Self::jaccard(pattern, h)).fold(0.0, f64::max)
    }
}
