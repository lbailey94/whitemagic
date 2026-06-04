//! Phylogenetics - Genome Tracking (PSR-001)
//! Target: 20-50× speedup for evolutionary tracking

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Genome {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub generation: usize,
    #[pyo3(get)]
    pub parent_id: Option<String>,
    #[pyo3(get)]
    pub fitness: f64,
}

#[pymethods]
impl Genome {
    #[new]
    fn new(id: String, generation: usize, parent_id: Option<String>, fitness: f64) -> Self {
        Self {
            id,
            generation,
            parent_id,
            fitness,
        }
    }
}

#[pyclass]
pub struct PyPhylogeneticsTracker {
    genomes: Arc<RwLock<HashMap<String, Genome>>>,
    generation_count: Arc<RwLock<usize>>,
}

#[pymethods]
impl PyPhylogeneticsTracker {
    #[new]
    fn new() -> Self {
        Self {
            genomes: Arc::new(RwLock::new(HashMap::new())),
            generation_count: Arc::new(RwLock::new(0)),
        }
    }

    fn add_genome(&self, genome: Genome) {
        let mut genomes = self.genomes.write();
        let mut gen_count = self.generation_count.write();
        
        if genome.generation > *gen_count {
            *gen_count = genome.generation;
        }
        
        genomes.insert(genome.id.clone(), genome);
    }

    fn get_genome(&self, id: String) -> Option<Genome> {
        self.genomes.read().get(&id).cloned()
    }

    fn get_lineage(&self, id: String) -> Vec<Genome> {
        let genomes = self.genomes.read();
        let mut lineage = Vec::new();
        let mut current_id = Some(id);
        
        while let Some(id) = current_id {
            if let Some(genome) = genomes.get(&id) {
                lineage.push(genome.clone());
                current_id = genome.parent_id.clone();
            } else {
                break;
            }
        }
        
        lineage
    }

    fn get_generation(&self, generation: usize) -> Vec<Genome> {
        self.genomes
            .read()
            .values()
            .filter(|g| g.generation == generation)
            .cloned()
            .collect()
    }

    fn current_generation(&self) -> usize {
        *self.generation_count.read()
    }

    fn genome_count(&self) -> usize {
        self.genomes.read().len()
    }

    fn average_fitness(&self, generation: Option<usize>) -> f64 {
        let genomes = self.genomes.read();
        
        let filtered: Vec<&Genome> = if let Some(gen) = generation {
            genomes.values().filter(|g| g.generation == gen).collect()
        } else {
            genomes.values().collect()
        };
        
        if filtered.is_empty() {
            return 0.0;
        }
        
        let sum: f64 = filtered.iter().map(|g| g.fitness).sum();
        sum / filtered.len() as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_genome() {
        let tracker = PyPhylogeneticsTracker::new();
        let genome = Genome::new("g1".to_string(), 0, None, 0.8);
        
        tracker.add_genome(genome);
        assert_eq!(tracker.genome_count(), 1);
    }

    #[test]
    fn test_lineage() {
        let tracker = PyPhylogeneticsTracker::new();
        
        let g1 = Genome::new("g1".to_string(), 0, None, 0.8);
        let g2 = Genome::new("g2".to_string(), 1, Some("g1".to_string()), 0.85);
        let g3 = Genome::new("g3".to_string(), 2, Some("g2".to_string()), 0.9);
        
        tracker.add_genome(g1);
        tracker.add_genome(g2);
        tracker.add_genome(g3);
        
        let lineage = tracker.get_lineage("g3".to_string());
        assert_eq!(lineage.len(), 3);
    }

    #[test]
    fn test_generation() {
        let tracker = PyPhylogeneticsTracker::new();
        
        tracker.add_genome(Genome::new("g1".to_string(), 0, None, 0.8));
        tracker.add_genome(Genome::new("g2".to_string(), 1, None, 0.85));
        tracker.add_genome(Genome::new("g3".to_string(), 1, None, 0.9));
        
        let gen1 = tracker.get_generation(1);
        assert_eq!(gen1.len(), 2);
    }

    #[test]
    fn test_average_fitness() {
        let tracker = PyPhylogeneticsTracker::new();
        
        tracker.add_genome(Genome::new("g1".to_string(), 0, None, 0.8));
        tracker.add_genome(Genome::new("g2".to_string(), 0, None, 0.6));
        
        let avg = tracker.average_fitness(Some(0));
        assert!((avg - 0.7).abs() < 0.01);
    }
}
