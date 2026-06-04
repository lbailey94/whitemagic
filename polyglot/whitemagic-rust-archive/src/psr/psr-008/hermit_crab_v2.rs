//! Hermit Crab - Privacy and access control

use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
pub struct HermitCrab {
    access_rules: HashMap<String, Vec<String>>,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl HermitCrab {
    #[new]
    fn new() -> Self {
        Self {
            access_rules: HashMap::new(),
        }
    }
    
    fn check_access(&self, resource: String, requester: String) -> PyResult<bool> {
        if let Some(allowed) = self.access_rules.get(&resource) {
            Ok(allowed.contains(&requester))
        } else {
            Ok(true)  // Default allow
        }
    }
    
    fn grant_access(&mut self, resource: String, requester: String) -> PyResult<()> {
        self.access_rules
            .entry(resource)
            .or_insert_with(Vec::new)
            .push(requester);
        
        Ok(())
    }
}
