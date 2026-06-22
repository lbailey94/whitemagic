//! Test Suite - Comprehensive testing framework

use pyo3::prelude::*;

#[pyclass]
pub struct TestSuite {
    tests_run: usize,
    tests_passed: usize,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl TestSuite {
    #[new]
    fn new() -> Self {
        Self {
            tests_run: 0,
            tests_passed: 0,
        }
    }
    
    fn run_test(&mut self, test_name: String, result: bool) -> PyResult<()> {
        self.tests_run += 1;
        
        if result {
            self.tests_passed += 1;
            println!("✅ {}", test_name);
        } else {
            println!("❌ {}", test_name);
        }
        
        Ok(())
    }
    
    fn get_results(&self) -> PyResult<(usize, usize, f64)> {
        let pass_rate = if self.tests_run > 0 {
            (self.tests_passed as f64 / self.tests_run as f64) * 100.0
        } else {
            0.0
        };
        
        Ok((self.tests_run, self.tests_passed, pass_rate))
    }
}
