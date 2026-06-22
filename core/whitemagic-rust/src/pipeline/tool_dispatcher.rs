//! Tool Dispatcher - Fast Routing (PSR-006)
//! Target: 50× speedup for tool dispatch (<100μs)

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Tool {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub gana: String,
    #[pyo3(get)]
    pub category: String,
    #[pyo3(get)]
    pub call_count: usize,
}

#[pymethods]
impl Tool {
    #[new]
    fn new(name: String, gana: String, category: String) -> Self {
        Self {
            name,
            gana,
            category,
            call_count: 0,
        }
    }
}

#[pyclass]
pub struct PyToolDispatcher {
    tools: Arc<RwLock<HashMap<String, Tool>>>,
    gana_index: Arc<RwLock<HashMap<String, Vec<String>>>>,
}

#[pymethods]
impl PyToolDispatcher {
    #[new]
    fn new() -> Self {
        Self {
            tools: Arc::new(RwLock::new(HashMap::new())),
            gana_index: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn register_tool(&self, tool: Tool) {
        let tool_name = tool.name.clone();
        let gana = tool.gana.clone();
        
        self.tools.write().insert(tool_name.clone(), tool);
        
        self.gana_index
            .write()
            .entry(gana)
            .or_insert_with(Vec::new)
            .push(tool_name);
    }

    fn dispatch(&self, tool_name: String) -> Option<Tool> {
        let mut tools = self.tools.write();
        
        if let Some(tool) = tools.get_mut(&tool_name) {
            tool.call_count += 1;
            Some(tool.clone())
        } else {
            None
        }
    }

    fn get_tools_by_gana(&self, gana: String) -> Vec<Tool> {
        let gana_index = self.gana_index.read();
        let tools = self.tools.read();
        
        if let Some(tool_names) = gana_index.get(&gana) {
            tool_names
                .iter()
                .filter_map(|name| tools.get(name).cloned())
                .collect()
        } else {
            Vec::new()
        }
    }

    fn get_tools_by_category(&self, category: String) -> Vec<Tool> {
        self.tools
            .read()
            .values()
            .filter(|tool| tool.category == category)
            .cloned()
            .collect()
    }

    fn get_hot_tools(&self, top_n: usize) -> Vec<Tool> {
        let mut tools: Vec<Tool> = self.tools.read().values().cloned().collect();
        tools.sort_by(|a, b| b.call_count.cmp(&a.call_count));
        tools.truncate(top_n);
        tools
    }

    fn get_tool_stats(&self) -> HashMap<String, usize> {
        self.tools
            .read()
            .iter()
            .map(|(name, tool)| (name.clone(), tool.call_count))
            .collect()
    }

    fn tool_count(&self) -> usize {
        self.tools.read().len()
    }

    fn gana_count(&self) -> usize {
        self.gana_index.read().len()
    }

    fn total_calls(&self) -> usize {
        self.tools.read().values().map(|t| t.call_count).sum()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dispatcher_creation() {
        let dispatcher = PyToolDispatcher::new();
        assert_eq!(dispatcher.tool_count(), 0);
    }

    #[test]
    fn test_register_tool() {
        let dispatcher = PyToolDispatcher::new();
        let tool = Tool::new("test_tool".to_string(), "gana_test".to_string(), "test".to_string());
        
        dispatcher.register_tool(tool);
        assert_eq!(dispatcher.tool_count(), 1);
    }

    #[test]
    fn test_dispatch() {
        let dispatcher = PyToolDispatcher::new();
        let tool = Tool::new("test_tool".to_string(), "gana_test".to_string(), "test".to_string());
        
        dispatcher.register_tool(tool);
        
        let result = dispatcher.dispatch("test_tool".to_string());
        assert!(result.is_some());
        assert_eq!(result.unwrap().call_count, 1);
    }

    #[test]
    fn test_get_tools_by_gana() {
        let dispatcher = PyToolDispatcher::new();
        
        dispatcher.register_tool(Tool::new("tool1".to_string(), "gana_a".to_string(), "test".to_string()));
        dispatcher.register_tool(Tool::new("tool2".to_string(), "gana_a".to_string(), "test".to_string()));
        
        let tools = dispatcher.get_tools_by_gana("gana_a".to_string());
        assert_eq!(tools.len(), 2);
    }

    #[test]
    fn test_hot_tools() {
        let dispatcher = PyToolDispatcher::new();
        
        dispatcher.register_tool(Tool::new("tool1".to_string(), "gana_a".to_string(), "test".to_string()));
        dispatcher.dispatch("tool1".to_string());
        dispatcher.dispatch("tool1".to_string());
        
        let hot = dispatcher.get_hot_tools(1);
        assert_eq!(hot.len(), 1);
        assert_eq!(hot[0].call_count, 2);
    }
}
