//! Middleware Pipeline - Middleware Chain (PSR-006)
//! Target: 30× speedup for middleware execution

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Request {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub tool_name: String,
    #[pyo3(get)]
    pub params: HashMap<String, String>,
}

#[pymethods]
impl Request {
    #[new]
    fn new(id: String, tool_name: String) -> Self {
        Self {
            id,
            tool_name,
            params: HashMap::new(),
        }
    }

    fn add_param(&mut self, key: String, value: String) {
        self.params.insert(key, value);
    }
}

#[derive(Clone, Debug)]
#[pyclass]
pub struct Response {
    #[pyo3(get)]
    pub request_id: String,
    #[pyo3(get)]
    pub status: String,
    #[pyo3(get)]
    pub data: String,
    #[pyo3(get)]
    pub metadata: HashMap<String, String>,
}

#[pymethods]
impl Response {
    #[new]
    fn new(request_id: String, status: String, data: String) -> Self {
        Self {
            request_id,
            status,
            data,
            metadata: HashMap::new(),
        }
    }

    fn add_metadata(&mut self, key: String, value: String) {
        self.metadata.insert(key, value);
    }
}

#[derive(Clone, Debug)]
#[pyclass]
pub struct Middleware {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub enabled: bool,
}

#[pymethods]
impl Middleware {
    #[new]
    fn new(name: String, enabled: bool) -> Self {
        Self {
            name,
            enabled,
        }
    }
}

#[pyclass]
pub struct PyMiddlewarePipeline {
    middlewares: Vec<Middleware>,
    execution_count: usize,
}

#[pymethods]
impl PyMiddlewarePipeline {
    #[new]
    fn new() -> Self {
        Self {
            middlewares: Vec::new(),
            execution_count: 0,
        }
    }

    fn add_middleware(&mut self, middleware: Middleware) {
        self.middlewares.push(middleware);
    }

    fn execute(&mut self, request: Request) -> Response {
        self.execution_count += 1;
        
        let mut current_request = request.clone();
        
        for middleware in &self.middlewares {
            if middleware.enabled {
                current_request = self.apply_middleware(middleware, current_request);
            }
        }
        
        Response {
            request_id: request.id,
            status: "success".to_string(),
            data: format!("Processed by {} middlewares", self.active_middleware_count()),
            metadata: HashMap::new(),
        }
    }

    fn enable_middleware(&mut self, name: String) -> bool {
        for middleware in &mut self.middlewares {
            if middleware.name == name {
                middleware.enabled = true;
                return true;
            }
        }
        false
    }

    fn disable_middleware(&mut self, name: String) -> bool {
        for middleware in &mut self.middlewares {
            if middleware.name == name {
                middleware.enabled = false;
                return true;
            }
        }
        false
    }

    fn get_middlewares(&self) -> Vec<Middleware> {
        self.middlewares.clone()
    }

    fn middleware_count(&self) -> usize {
        self.middlewares.len()
    }

    fn active_middleware_count(&self) -> usize {
        self.middlewares.iter().filter(|m| m.enabled).count()
    }

    fn get_execution_count(&self) -> usize {
        self.execution_count
    }

    fn clear(&mut self) {
        self.middlewares.clear();
        self.execution_count = 0;
    }
}

impl PyMiddlewarePipeline {
    fn apply_middleware(&self, _middleware: &Middleware, request: Request) -> Request {
        request
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pipeline_creation() {
        let pipeline = PyMiddlewarePipeline::new();
        assert_eq!(pipeline.middleware_count(), 0);
    }

    #[test]
    fn test_add_middleware() {
        let mut pipeline = PyMiddlewarePipeline::new();
        let middleware = Middleware::new("test".to_string(), true);
        
        pipeline.add_middleware(middleware);
        assert_eq!(pipeline.middleware_count(), 1);
    }

    #[test]
    fn test_execute() {
        let mut pipeline = PyMiddlewarePipeline::new();
        pipeline.add_middleware(Middleware::new("m1".to_string(), true));
        
        let request = Request::new("req1".to_string(), "tool1".to_string());
        let response = pipeline.execute(request);
        
        assert_eq!(response.status, "success");
        assert_eq!(pipeline.get_execution_count(), 1);
    }

    #[test]
    fn test_enable_disable() {
        let mut pipeline = PyMiddlewarePipeline::new();
        pipeline.add_middleware(Middleware::new("m1".to_string(), true));
        
        assert!(pipeline.disable_middleware("m1".to_string()));
        assert_eq!(pipeline.active_middleware_count(), 0);
        
        assert!(pipeline.enable_middleware("m1".to_string()));
        assert_eq!(pipeline.active_middleware_count(), 1);
    }
}
