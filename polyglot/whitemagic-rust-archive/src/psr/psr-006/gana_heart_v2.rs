//! Gana Heart - Session context management
//! Maintains working memory and context

use pyo3::prelude::*;
use std::collections::VecDeque;

#[pyclass]
pub struct GanaHeart {
    context: VecDeque<String>,
    max_context_size: usize,
}

#[pymethods]

/// # Example
/// ```
/// use whitemagic::*;
/// // Example usage here
/// ```
impl GanaHeart {
    #[new]
    fn new(max_size: Option<usize>) -> Self {
        Self {
            context: VecDeque::new(),
            max_context_size: max_size.unwrap_or(100),
        }
    }
    
    fn add_to_context(&mut self, item: String) -> PyResult<()> {
        if self.context.len() >= self.max_context_size {
            self.context.pop_front();
        }
        
        self.context.push_back(item);
        
        Ok(())
    }
    
    fn get_context(&self, limit: Option<usize>) -> PyResult<Vec<String>> {
        let lim = limit.unwrap_or(10);
        
        Ok(self.context
            .iter()
            .rev()
            .take(lim)
            .cloned()
            .collect())
    }
    
    fn clear_context(&mut self) -> PyResult<()> {
        self.context.clear();
        Ok(())
    }
}
