//! Validation Engine - System Validation (PSR-009)
//! Target: 40× speedup for validation

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
#[pyclass]
pub struct ValidationRule {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub rule_type: String,
    #[pyo3(get)]
    pub severity: String,
}

#[pymethods]
impl ValidationRule {
    #[new]
    fn new(name: String, rule_type: String, severity: String) -> Self {
        Self {
            name,
            rule_type,
            severity,
        }
    }
}

#[derive(Clone, Debug)]
#[pyclass]
pub struct ValidationResult {
    #[pyo3(get)]
    pub rule_name: String,
    #[pyo3(get)]
    pub passed: bool,
    #[pyo3(get)]
    pub message: String,
}

#[pymethods]
impl ValidationResult {
    #[new]
    fn new(rule_name: String, passed: bool, message: String) -> Self {
        Self {
            rule_name,
            passed,
            message,
        }
    }
}

#[pyclass]
pub struct PyValidationEngine {
    rules: HashMap<String, ValidationRule>,
    results: Vec<ValidationResult>,
}

#[pymethods]
impl PyValidationEngine {
    #[new]
    fn new() -> Self {
        Self {
            rules: HashMap::new(),
            results: Vec::new(),
        }
    }

    fn add_rule(&mut self, rule: ValidationRule) {
        self.rules.insert(rule.name.clone(), rule);
    }

    fn validate(&mut self, rule_name: String, data: HashMap<String, String>) -> bool {
        if let Some(_rule) = self.rules.get(&rule_name) {
            let passed = !data.is_empty();
            
            self.results.push(ValidationResult {
                rule_name: rule_name.clone(),
                passed,
                message: if passed {
                    "Validation passed".to_string()
                } else {
                    "Validation failed".to_string()
                },
            });
            
            passed
        } else {
            false
        }
    }

    fn get_results(&self) -> Vec<ValidationResult> {
        self.results.clone()
    }

    fn get_failures(&self) -> Vec<ValidationResult> {
        self.results
            .iter()
            .filter(|r| !r.passed)
            .cloned()
            .collect()
    }

    fn clear_results(&mut self) {
        self.results.clear();
    }

    fn rule_count(&self) -> usize {
        self.rules.len()
    }

    fn result_count(&self) -> usize {
        self.results.len()
    }

    fn failure_count(&self) -> usize {
        self.results.iter().filter(|r| !r.passed).count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_creation() {
        let engine = PyValidationEngine::new();
        assert_eq!(engine.rule_count(), 0);
    }

    #[test]
    fn test_add_rule() {
        let mut engine = PyValidationEngine::new();
        let rule = ValidationRule::new("rule1".to_string(), "required".to_string(), "error".to_string());
        
        engine.add_rule(rule);
        assert_eq!(engine.rule_count(), 1);
    }

    #[test]
    fn test_validate() {
        let mut engine = PyValidationEngine::new();
        let rule = ValidationRule::new("rule1".to_string(), "required".to_string(), "error".to_string());
        
        engine.add_rule(rule);
        
        let mut data = HashMap::new();
        data.insert("key".to_string(), "value".to_string());
        
        assert!(engine.validate("rule1".to_string(), data));
        assert_eq!(engine.result_count(), 1);
    }

    #[test]
    fn test_get_failures() {
        let mut engine = PyValidationEngine::new();
        let rule = ValidationRule::new("rule1".to_string(), "required".to_string(), "error".to_string());
        
        engine.add_rule(rule);
        
        engine.validate("rule1".to_string(), HashMap::new());
        
        let failures = engine.get_failures();
        assert_eq!(failures.len(), 1);
    }
}
