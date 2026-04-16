//! Security Monitor - Threat detection

use pyo3::prelude::*;

#[pyclass]
pub struct SecurityMonitor {
    alert_count: usize,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl SecurityMonitor {
    #[new]
    fn new() -> Self {
        Self {
            alert_count: 0,
        }
    }
    
    fn check_threat(&mut self, action: String) -> PyResult<bool> {
        let is_threat = action.contains("delete") || action.contains("drop");
        
        if is_threat {
            self.alert_count += 1;
        }
        
        Ok(is_threat)
    }
    
    fn get_alert_count(&self) -> PyResult<usize> {
        Ok(self.alert_count)
    }
}
