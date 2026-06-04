//! Kaizen - Continuous improvement system
//! Analyzes code and suggests incremental improvements

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
struct Improvement {
    description: String,
    #[allow(dead_code)]
    impact: f64,
    #[allow(dead_code)]
    effort: f64,
    priority: f64,
}

#[pyclass]
pub struct Kaizen {
    improvements: HashMap<String, Vec<Improvement>>,
}

#[pymethods]
impl Kaizen {
    #[new]
    fn new() -> Self {
        Self {
            improvements: HashMap::new(),
        }
    }
    
    fn analyze_code(&mut self, file_path: String, code: String) -> PyResult<Vec<String>> {
        let mut suggestions = Vec::new();
        
        // Check for missing error handling
        if !code.contains("Result<") && !code.contains("PyResult") {
            suggestions.push("Add error handling with Result types".to_string());
            self.add_improvement(&file_path, "Add error handling", 0.8, 0.3);
        }
        
        // Check for missing parallelization
        if code.contains("iter()") && !code.contains("par_iter()") {
            suggestions.push("Consider parallel processing with Rayon".to_string());
            self.add_improvement(&file_path, "Add parallelization", 0.9, 0.4);
        }
        
        // Check for missing documentation
        if !code.contains("///") && !code.contains("//!") {
            suggestions.push("Add documentation comments".to_string());
            self.add_improvement(&file_path, "Add documentation", 0.6, 0.2);
        }
        
        Ok(suggestions)
    }
    
    fn add_improvement(&mut self, file_path: &str, description: &str, impact: f64, effort: f64) {
        let priority = impact / effort;
        
        let improvement = Improvement {
            description: description.to_string(),
            impact,
            effort,
            priority,
        };
        
        self.improvements
            .entry(file_path.to_string())
            .or_insert_with(Vec::new)
            .push(improvement);
    }
    
    fn get_top_improvements(&self, limit: usize) -> PyResult<Vec<(String, String, f64)>> {
        let mut all_improvements: Vec<_> = self.improvements
            .iter()
            .flat_map(|(file, imps)| {
                imps.iter().map(move |imp| (file.clone(), imp.description.clone(), imp.priority))
            })
            .collect();
        
        all_improvements.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap());
        all_improvements.truncate(limit);
        
        Ok(all_improvements)
    }
}
