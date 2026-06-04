//! ML Bridge - Python ML Integration (PSR-008)
//! Target: 20× speedup for ML model integration

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
#[pyclass]
pub struct ModelConfig {
    #[pyo3(get)]
    pub model_name: String,
    #[pyo3(get)]
    pub model_type: String,
    #[pyo3(get)]
    pub parameters: HashMap<String, String>,
}

#[pymethods]
impl ModelConfig {
    #[new]
    fn new(model_name: String, model_type: String) -> Self {
        Self {
            model_name,
            model_type,
            parameters: HashMap::new(),
        }
    }

    fn set_parameter(&mut self, key: String, value: String) {
        self.parameters.insert(key, value);
    }
}

#[pyclass]
pub struct PyMLBridge {
    models: HashMap<String, ModelConfig>,
}

#[pymethods]
impl PyMLBridge {
    #[new]
    fn new() -> Self {
        Self {
            models: HashMap::new(),
        }
    }

    fn register_model(&mut self, config: ModelConfig) {
        self.models.insert(config.model_name.clone(), config);
    }

    fn get_model(&self, model_name: String) -> Option<ModelConfig> {
        self.models.get(&model_name).cloned()
    }

    fn list_models(&self) -> Vec<String> {
        self.models.keys().cloned().collect()
    }

    fn model_count(&self) -> usize {
        self.models.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bridge_creation() {
        let bridge = PyMLBridge::new();
        assert_eq!(bridge.model_count(), 0);
    }

    #[test]
    fn test_register_model() {
        let mut bridge = PyMLBridge::new();
        let config = ModelConfig::new("model1".to_string(), "transformer".to_string());
        
        bridge.register_model(config);
        assert_eq!(bridge.model_count(), 1);
    }

    #[test]
    fn test_get_model() {
        let mut bridge = PyMLBridge::new();
        let config = ModelConfig::new("model1".to_string(), "transformer".to_string());
        
        bridge.register_model(config);
        
        let retrieved = bridge.get_model("model1".to_string());
        assert!(retrieved.is_some());
    }
}
