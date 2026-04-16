//! Memory Consolidation
//! Consolidates short-term memories into long-term storage

use pyo3::prelude::*;
use rayon::prelude::*;

#[derive(Clone, Debug)]
struct MemoryCandidate {
    id: String,
    importance: f64,
    access_count: usize,
    age_hours: f64,
}

#[pyclass]
pub struct MemoryConsolidation {
    candidates: Vec<MemoryCandidate>,
    consolidation_threshold: f64,
}

#[pymethods]
impl MemoryConsolidation {
    #[new]
    fn new(threshold: Option<f64>) -> Self {
        Self {
            candidates: Vec::new(),
            consolidation_threshold: threshold.unwrap_or(0.7),
        }
    }
    
    fn add_candidate(
        &mut self,
        id: String,
        importance: f64,
        access_count: usize,
        age_hours: f64
    ) -> PyResult<()> {
        self.candidates.push(MemoryCandidate {
            id,
            importance,
            access_count,
            age_hours,
        });
        Ok(())
    }
    
    fn consolidate(&self) -> PyResult<Vec<String>> {
        let consolidated: Vec<String> = self.candidates
            .par_iter()
            .filter_map(|candidate| {
                let score = Self::score(candidate);
                if score >= self.consolidation_threshold {
                    Some(candidate.id.clone())
                } else {
                    None
                }
            })
            .collect();
        Ok(consolidated)
    }
    
    fn get_candidate_count(&self) -> PyResult<usize> {
        Ok(self.candidates.len())
    }
}

impl MemoryConsolidation {
    fn score(candidate: &MemoryCandidate) -> f64 {
        let access_score = (candidate.access_count as f64).min(10.0) / 10.0;
        let age_score = (candidate.age_hours / 24.0).min(1.0);
        candidate.importance * 0.4 + access_score * 0.3 + age_score * 0.3
    }
}
