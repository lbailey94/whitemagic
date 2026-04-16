//! Parameter Validator - Type-Safe Validation (PSR-006)
//! Target: 100× speedup for parameter validation

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug, PartialEq)]
pub enum ParamType {
    String,
    Integer,
    Float,
    Boolean,
    Array,
    Object,
}

#[derive(Clone, Debug)]
#[pyclass]
pub struct ParamSchema {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub required: bool,
    param_type: ParamType,
}

#[pymethods]
impl ParamSchema {
    #[new]
    fn new(name: String, param_type: String, required: bool) -> Self {
        let ptype = match param_type.as_str() {
            "string" => ParamType::String,
            "integer" => ParamType::Integer,
            "float" => ParamType::Float,
            "boolean" => ParamType::Boolean,
            "array" => ParamType::Array,
            "object" => ParamType::Object,
            _ => ParamType::String,
        };
        
        Self {
            name,
            required,
            param_type: ptype,
        }
    }

    fn get_type(&self) -> String {
        match self.param_type {
            ParamType::String => "string".to_string(),
            ParamType::Integer => "integer".to_string(),
            ParamType::Float => "float".to_string(),
            ParamType::Boolean => "boolean".to_string(),
            ParamType::Array => "array".to_string(),
            ParamType::Object => "object".to_string(),
        }
    }
}

#[derive(Clone, Debug)]
#[pyclass]
pub struct ValidationError {
    #[pyo3(get)]
    pub param_name: String,
    #[pyo3(get)]
    pub error_type: String,
    #[pyo3(get)]
    pub message: String,
}

#[pymethods]
impl ValidationError {
    #[new]
    fn new(param_name: String, error_type: String, message: String) -> Self {
        Self {
            param_name,
            error_type,
            message,
        }
    }
}

#[pyclass]
pub struct PyParamValidator {
    schemas: HashMap<String, Vec<ParamSchema>>,
}

#[pymethods]
impl PyParamValidator {
    #[new]
    fn new() -> Self {
        Self {
            schemas: HashMap::new(),
        }
    }

    fn register_schema(&mut self, tool_name: String, schema: Vec<ParamSchema>) {
        self.schemas.insert(tool_name, schema);
    }

    fn validate(&self, tool_name: String, params: HashMap<String, String>) -> Vec<ValidationError> {
        let mut errors = Vec::new();
        
        if let Some(schema) = self.schemas.get(&tool_name) {
            for param_schema in schema {
                if param_schema.required && !params.contains_key(&param_schema.name) {
                    errors.push(ValidationError {
                        param_name: param_schema.name.clone(),
                        error_type: "missing".to_string(),
                        message: format!("Required parameter '{}' is missing", param_schema.name),
                    });
                }
                
                if let Some(value) = params.get(&param_schema.name) {
                    if !self.validate_type(value, &param_schema.param_type) {
                        errors.push(ValidationError {
                            param_name: param_schema.name.clone(),
                            error_type: "type_mismatch".to_string(),
                            message: format!(
                                "Parameter '{}' has wrong type, expected {:?}",
                                param_schema.name, param_schema.param_type
                            ),
                        });
                    }
                }
            }
        }
        
        errors
    }

    fn validate_fast(&self, tool_name: String, params: HashMap<String, String>) -> bool {
        self.validate(tool_name, params).is_empty()
    }

    fn get_required_params(&self, tool_name: String) -> Vec<String> {
        if let Some(schema) = self.schemas.get(&tool_name) {
            schema
                .iter()
                .filter(|p| p.required)
                .map(|p| p.name.clone())
                .collect()
        } else {
            Vec::new()
        }
    }

    fn get_optional_params(&self, tool_name: String) -> Vec<String> {
        if let Some(schema) = self.schemas.get(&tool_name) {
            schema
                .iter()
                .filter(|p| !p.required)
                .map(|p| p.name.clone())
                .collect()
        } else {
            Vec::new()
        }
    }

    fn schema_count(&self) -> usize {
        self.schemas.len()
    }
}

impl PyParamValidator {
    fn validate_type(&self, value: &str, param_type: &ParamType) -> bool {
        match param_type {
            ParamType::String => true,
            ParamType::Integer => value.parse::<i64>().is_ok(),
            ParamType::Float => value.parse::<f64>().is_ok(),
            ParamType::Boolean => value == "true" || value == "false",
            ParamType::Array => value.starts_with('[') && value.ends_with(']'),
            ParamType::Object => value.starts_with('{') && value.ends_with('}'),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validator_creation() {
        let validator = PyParamValidator::new();
        assert_eq!(validator.schema_count(), 0);
    }

    #[test]
    fn test_register_schema() {
        let mut validator = PyParamValidator::new();
        let schema = vec![
            ParamSchema::new("param1".to_string(), "string".to_string(), true),
        ];
        
        validator.register_schema("tool1".to_string(), schema);
        assert_eq!(validator.schema_count(), 1);
    }

    #[test]
    fn test_validate_missing_required() {
        let mut validator = PyParamValidator::new();
        let schema = vec![
            ParamSchema::new("param1".to_string(), "string".to_string(), true),
        ];
        
        validator.register_schema("tool1".to_string(), schema);
        
        let params = HashMap::new();
        let errors = validator.validate("tool1".to_string(), params);
        
        assert_eq!(errors.len(), 1);
        assert_eq!(errors[0].error_type, "missing");
    }

    #[test]
    fn test_validate_type_mismatch() {
        let mut validator = PyParamValidator::new();
        let schema = vec![
            ParamSchema::new("param1".to_string(), "integer".to_string(), true),
        ];
        
        validator.register_schema("tool1".to_string(), schema);
        
        let mut params = HashMap::new();
        params.insert("param1".to_string(), "not_a_number".to_string());
        
        let errors = validator.validate("tool1".to_string(), params);
        
        assert_eq!(errors.len(), 1);
        assert_eq!(errors[0].error_type, "type_mismatch");
    }

    #[test]
    fn test_validate_success() {
        let mut validator = PyParamValidator::new();
        let schema = vec![
            ParamSchema::new("param1".to_string(), "string".to_string(), true),
        ];
        
        validator.register_schema("tool1".to_string(), schema);
        
        let mut params = HashMap::new();
        params.insert("param1".to_string(), "value".to_string());
        
        assert!(validator.validate_fast("tool1".to_string(), params));
    }
}
