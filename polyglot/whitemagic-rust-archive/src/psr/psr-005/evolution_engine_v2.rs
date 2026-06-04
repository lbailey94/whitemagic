//! Evolution Engine - Autonomous code evolution
//! Applies mutations and selects fittest implementations

use pyo3::prelude::*;
use rand::Rng;

#[pyclass]
pub struct EvolutionEngine {
    population_size: usize,
    mutation_rate: f64,
    generation: usize,
}

#[pymethods]
impl EvolutionEngine {
    #[new]
    fn new(population_size: Option<usize>, mutation_rate: Option<f64>) -> Self {
        Self {
            population_size: population_size.unwrap_or(100),
            mutation_rate: mutation_rate.unwrap_or(0.1),
            generation: 0,
        }
    }
    
    fn evolve_population(
        &mut self,
        population: Vec<String>,
        fitness_scores: Vec<f64>
    ) -> PyResult<Vec<String>> {
        // Selection - keep top 50%
        let mut scored: Vec<_> = population.into_iter().zip(fitness_scores.iter()).collect();
        scored.sort_by(|a, b| b.1.partial_cmp(a.1).unwrap());
        
        let survivors: Vec<String> = scored
            .into_iter()
            .take(self.population_size / 2)
            .map(|(code, _)| code)
            .collect();
        
        // Crossover and mutation
        let mut new_population = survivors.clone();
        let mut rng = rand::thread_rng();
        
        while new_population.len() < self.population_size {
            let parent1 = &survivors[rng.gen_range(0..survivors.len())];
            let parent2 = &survivors[rng.gen_range(0..survivors.len())];
            
            let child = self.crossover(parent1, parent2);
            let mutated = if rng.gen::<f64>() < self.mutation_rate {
                self.mutate(&child)
            } else {
                child
            };
            
            new_population.push(mutated);
        }
        
        self.generation += 1;
        
        Ok(new_population)
    }
    
    fn crossover(&self, parent1: &str, parent2: &str) -> String {
        let lines1: Vec<&str> = parent1.lines().collect();
        let lines2: Vec<&str> = parent2.lines().collect();
        
        let split = lines1.len() / 2;
        
        let mut child_lines = lines1[..split].to_vec();
        child_lines.extend_from_slice(&lines2[split..]);
        
        child_lines.join("
")
    }
    
    fn mutate(&self, code: &str) -> String {
        // Simple mutation: add optimization comment
        format!("// Evolved generation {}
{}", self.generation, code)
    }
    
    fn get_generation(&self) -> PyResult<usize> {
        Ok(self.generation)
    }
}
