//! Memory Lifecycle
//! Tracks memory through its lifecycle stages

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug, PartialEq)]
#[allow(dead_code)]
enum LifecycleStage {
    ShortTerm,
    WorkingMemory,
    LongTerm,
    Archived,
    Forgotten,
}

#[pyclass]
pub struct MemoryLifecycle {
    stages: HashMap<String, String>,
    transitions: Vec<(String, String, String)>, // (memory_id, from, to)
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl MemoryLifecycle {
    #[new]
    fn new() -> Self {
        Self {
            stages: HashMap::new(),
            transitions: Vec::new(),
        }
    }
    
    fn set_stage(&mut self, memory_id: String, stage: String) -> PyResult<()> {
        if let Some(old_stage) = self.stages.get(&memory_id) {
            self.transitions.push((
                memory_id.clone(),
                old_stage.clone(),
                stage.clone()
            ));
        }
        
        self.stages.insert(memory_id, stage);
        Ok(())
    }
    
    fn get_stage(&self, memory_id: String) -> PyResult<Option<String>> {
        Ok(self.stages.get(&memory_id).cloned())
    }
    
    fn get_transitions(&self, memory_id: String) -> PyResult<Vec<(String, String)>> {
        let transitions: Vec<(String, String)> = self.transitions
            .iter()
            .filter(|(id, _, _)| id == &memory_id)
            .map(|(_, from, to)| (from.clone(), to.clone()))
            .collect();
        
        Ok(transitions)
    }
    
    fn get_stage_counts(&self) -> PyResult<Vec<(String, usize)>> {
        let mut counts: HashMap<String, usize> = HashMap::new();
        
        for stage in self.stages.values() {
            *counts.entry(stage.clone()).or_insert(0) += 1;
        }
        
        Ok(counts.into_iter().collect())
    }
}
