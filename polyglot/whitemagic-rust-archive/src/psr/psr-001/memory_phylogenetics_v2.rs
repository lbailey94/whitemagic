//! Memory Phylogenetics
//! Tracks memory lineage and evolution

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
struct MemoryLineage {
    #[allow(dead_code)]
    memory_id: String,
    parent_id: Option<String>,
    children: Vec<String>,
    generation: usize,
    #[allow(dead_code)]
    mutations: Vec<String>,
}

#[pyclass]
pub struct MemoryPhylogenetics {
    lineages: HashMap<String, MemoryLineage>,
}

#[pymethods]
impl MemoryPhylogenetics {
    #[new]
    fn new() -> Self {
        Self {
            lineages: HashMap::new(),
        }
    }
    
    #[pyo3(signature = (memory_id, parent_id=None, mutations=vec![]))]
    fn track_memory(
        &mut self,
        memory_id: String,
        parent_id: Option<String>,
        mutations: Vec<String>
    ) -> PyResult<()> {
        let generation = if let Some(ref pid) = parent_id {
            self.lineages.get(pid).map(|p| p.generation + 1).unwrap_or(0)
        } else {
            0
        };
        
        let lineage = MemoryLineage {
            memory_id: memory_id.clone(),
            parent_id: parent_id.clone(),
            children: Vec::new(),
            generation,
            mutations,
        };
        
        // Update parent's children
        if let Some(ref pid) = parent_id {
            if let Some(parent) = self.lineages.get_mut(pid) {
                parent.children.push(memory_id.clone());
            }
        }
        
        self.lineages.insert(memory_id, lineage);
        
        Ok(())
    }
    
    fn get_lineage(&self, memory_id: String) -> PyResult<Vec<String>> {
        let mut lineage = Vec::new();
        let mut current_id = Some(memory_id);
        
        while let Some(id) = current_id {
            lineage.push(id.clone());
            current_id = self.lineages.get(&id).and_then(|l| l.parent_id.clone());
        }
        
        lineage.reverse();
        Ok(lineage)
    }
    
    fn get_descendants(&self, memory_id: String) -> PyResult<Vec<String>> {
        let mut descendants = Vec::new();
        
        if let Some(lineage) = self.lineages.get(&memory_id) {
            for child_id in &lineage.children {
                descendants.push(child_id.clone());
                descendants.extend(self.get_descendants(child_id.clone())?);
            }
        }
        
        Ok(descendants)
    }
}
