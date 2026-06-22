//! Performance Monitor - Real-time performance tracking

use pyo3::prelude::*;
use std::time::Instant;

#[pyclass]
pub struct PerformanceMonitor {
    start_time: Option<Instant>,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl PerformanceMonitor {
    #[new]
    fn new() -> Self {
        Self {
            start_time: None,
        }
    }
    
    fn start_timer(&mut self) -> PyResult<()> {
        self.start_time = Some(Instant::now());
        Ok(())
    }
    
    fn stop_timer(&mut self) -> PyResult<f64> {
        if let Some(start) = self.start_time {
            let duration = start.elapsed();
            self.start_time = None;
            Ok(duration.as_secs_f64())
        } else {
            Ok(0.0)
        }
    }
}
