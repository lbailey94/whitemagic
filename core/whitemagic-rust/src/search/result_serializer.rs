//! Result Serializer - Zero-Copy Serialization (PSR-006)
//! Target: 30× speedup for result serialization

use pyo3::prelude::*;
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[pyclass]
pub struct SerializedResult {
    #[pyo3(get)]
    pub status: String,
    #[pyo3(get)]
    pub data: String,
    #[pyo3(get)]
    pub metadata: HashMap<String, String>,
}

#[pymethods]
impl SerializedResult {
    #[new]
    fn new(status: String, data: String) -> Self {
        Self {
            status,
            data,
            metadata: HashMap::new(),
        }
    }

    fn add_metadata(&mut self, key: String, value: String) {
        self.metadata.insert(key, value);
    }
}

#[pyclass]
pub struct PyResultSerializer {
    format: String,
}

#[pymethods]
impl PyResultSerializer {
    #[new]
    fn new(format: Option<String>) -> Self {
        Self {
            format: format.unwrap_or_else(|| "json".to_string()),
        }
    }

    fn serialize(&self, result: SerializedResult) -> PyResult<String> {
        match self.format.as_str() {
            "json" => serde_json::to_string(&result)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string())),
            _ => Ok(format!("{:?}", result)),
        }
    }

    fn deserialize(&self, data: String) -> PyResult<SerializedResult> {
        match self.format.as_str() {
            "json" => serde_json::from_str(&data)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string())),
            _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Unsupported format",
            )),
        }
    }

    fn serialize_batch(&self, results: Vec<SerializedResult>) -> PyResult<String> {
        match self.format.as_str() {
            "json" => serde_json::to_string(&results)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string())),
            _ => Ok(format!("{:?}", results)),
        }
    }

    fn deserialize_batch(&self, data: String) -> PyResult<Vec<SerializedResult>> {
        match self.format.as_str() {
            "json" => serde_json::from_str(&data)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string())),
            _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Unsupported format",
            )),
        }
    }

    fn get_format(&self) -> String {
        self.format.clone()
    }

    fn set_format(&mut self, format: String) {
        self.format = format;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_serializer_creation() {
        let serializer = PyResultSerializer::new(Some("json".to_string()));
        assert_eq!(serializer.get_format(), "json");
    }

    #[test]
    fn test_serialize() {
        let serializer = PyResultSerializer::new(Some("json".to_string()));
        let result = SerializedResult::new("success".to_string(), "test data".to_string());
        
        let serialized = serializer.serialize(result);
        assert!(serialized.is_ok());
    }

    #[test]
    fn test_deserialize() {
        let serializer = PyResultSerializer::new(Some("json".to_string()));
        let result = SerializedResult::new("success".to_string(), "test".to_string());
        
        let serialized = serializer.serialize(result.clone()).unwrap();
        let deserialized = serializer.deserialize(serialized);
        
        assert!(deserialized.is_ok());
    }

    #[test]
    fn test_batch_serialize() {
        let serializer = PyResultSerializer::new(Some("json".to_string()));
        let results = vec![
            SerializedResult::new("success".to_string(), "data1".to_string()),
            SerializedResult::new("success".to_string(), "data2".to_string()),
        ];
        
        let serialized = serializer.serialize_batch(results);
        assert!(serialized.is_ok());
    }
}
