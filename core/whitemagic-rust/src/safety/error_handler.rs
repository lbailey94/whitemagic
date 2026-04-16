//! Error Handler - Structured Error Handling (PSR-006)
//! Target: 30× speedup for error handling

use pyo3::prelude::*;
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug)]
#[pyclass]
pub struct ErrorRecord {
    #[pyo3(get)]
    pub error_type: String,
    #[pyo3(get)]
    pub message: String,
    #[pyo3(get)]
    pub context: HashMap<String, String>,
    #[pyo3(get)]
    pub timestamp: u64,
    #[pyo3(get)]
    pub severity: String,
}

#[pymethods]
impl ErrorRecord {
    #[new]
    fn new(error_type: String, message: String, severity: String) -> Self {
        Self {
            error_type,
            message,
            context: HashMap::new(),
            timestamp: current_timestamp(),
            severity,
        }
    }

    fn add_context(&mut self, key: String, value: String) {
        self.context.insert(key, value);
    }
}

#[pyclass]
pub struct PyErrorHandler {
    errors: Vec<ErrorRecord>,
    max_errors: usize,
    error_counts: HashMap<String, usize>,
}

#[pymethods]
impl PyErrorHandler {
    #[new]
    fn new(max_errors: Option<usize>) -> Self {
        Self {
            errors: Vec::new(),
            max_errors: max_errors.unwrap_or(1000),
            error_counts: HashMap::new(),
        }
    }

    fn record_error(&mut self, error: ErrorRecord) {
        *self.error_counts.entry(error.error_type.clone()).or_insert(0) += 1;
        
        self.errors.push(error);
        
        if self.errors.len() > self.max_errors {
            self.errors.remove(0);
        }
    }

    fn get_errors(&self, error_type: Option<String>, severity: Option<String>) -> Vec<ErrorRecord> {
        self.errors
            .iter()
            .filter(|e| {
                error_type.as_ref().map_or(true, |t| &e.error_type == t)
                    && severity.as_ref().map_or(true, |s| &e.severity == s)
            })
            .cloned()
            .collect()
    }

    fn get_recent_errors(&self, count: usize) -> Vec<ErrorRecord> {
        self.errors
            .iter()
            .rev()
            .take(count)
            .cloned()
            .collect()
    }

    fn get_error_counts(&self) -> HashMap<String, usize> {
        self.error_counts.clone()
    }

    fn get_error_rate(&self, window_seconds: u64) -> f64 {
        let now = current_timestamp();
        let cutoff = now.saturating_sub(window_seconds);
        
        let recent_count = self.errors
            .iter()
            .filter(|e| e.timestamp >= cutoff)
            .count();
        
        if window_seconds == 0 {
            return 0.0;
        }
        
        recent_count as f64 / window_seconds as f64
    }

    fn clear_errors(&mut self) {
        self.errors.clear();
        self.error_counts.clear();
    }

    fn error_count(&self) -> usize {
        self.errors.len()
    }

    fn total_errors(&self) -> usize {
        self.error_counts.values().sum()
    }
}

fn current_timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_handler_creation() {
        let handler = PyErrorHandler::new(Some(100));
        assert_eq!(handler.error_count(), 0);
    }

    #[test]
    fn test_record_error() {
        let mut handler = PyErrorHandler::new(None);
        let error = ErrorRecord::new("test".to_string(), "msg".to_string(), "low".to_string());
        
        handler.record_error(error);
        assert_eq!(handler.error_count(), 1);
    }

    #[test]
    fn test_get_errors_by_type() {
        let mut handler = PyErrorHandler::new(None);
        
        handler.record_error(ErrorRecord::new("type1".to_string(), "msg1".to_string(), "low".to_string()));
        handler.record_error(ErrorRecord::new("type2".to_string(), "msg2".to_string(), "high".to_string()));
        
        let errors = handler.get_errors(Some("type1".to_string()), None);
        assert_eq!(errors.len(), 1);
    }

    #[test]
    fn test_error_counts() {
        let mut handler = PyErrorHandler::new(None);
        
        handler.record_error(ErrorRecord::new("type1".to_string(), "msg".to_string(), "low".to_string()));
        handler.record_error(ErrorRecord::new("type1".to_string(), "msg".to_string(), "low".to_string()));
        
        let counts = handler.get_error_counts();
        assert_eq!(counts.get("type1"), Some(&2));
    }
}
