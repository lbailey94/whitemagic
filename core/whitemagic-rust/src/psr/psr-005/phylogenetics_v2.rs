//! Phylogenetics - Code lineage tracking
//! Tracks evolution of code patterns across generations

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
struct CodeLineage {
    id: String,
    #[allow(dead_code)]
    parent_id: Option<String>,
    generation: usize,
    fitness_score: f64,
    #[allow(dead_code)]
    mutations: Vec<String>,
}

#[pyclass]
pub struct Phylogenetics {
    lineages: HashMap<String, CodeLineage>,
    generation_count: usize,
}

#[pymethods]
impl Phylogenetics {
    #[new]
    fn new() -> Self {
        Self {
            lineages: HashMap::new(),
            generation_count: 0,
        }
    }
    
    #[pyo3(signature = (code_id, parent_id=None, fitness=0.0, mutations=vec![]))]
    fn track_lineage(
        &mut self,
        code_id: String,
        parent_id: Option<String>,
        fitness: f64,
        mutations: Vec<String>
    ) -> PyResult<()> {
        let generation = if let Some(ref pid) = parent_id {
            self.lineages.get(pid).map(|p| p.generation + 1).unwrap_or(0)
        } else {
            0
        };
        
        self.generation_count = self.generation_count.max(generation + 1);
        
        let lineage = CodeLineage {
            id: code_id.clone(),
            parent_id,
            generation,
            fitness_score: fitness,
            mutations,
        };
        
        self.lineages.insert(code_id, lineage);
        
        Ok(())
    }
    
    fn get_best_lineage(&self) -> PyResult<Option<String>> {
        let best = self.lineages
            .values()
            .max_by(|a, b| a.fitness_score.partial_cmp(&b.fitness_score).unwrap());
        
        Ok(best.map(|l| l.id.clone()))
    }
    
    fn get_generation_stats(&self, generation: usize) -> PyResult<(usize, f64)> {
        let gen_lineages: Vec<_> = self.lineages
            .values()
            .filter(|l| l.generation == generation)
            .collect();
        
        let count = gen_lineages.len();
        let avg_fitness = if count > 0 {
            gen_lineages.iter().map(|l| l.fitness_score).sum::<f64>() / count as f64
        } else {
            0.0
        };
        
        Ok((count, avg_fitness))
    }
}
