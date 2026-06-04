//! Dispatch Table - Tool Routing Table (PSR-006)
//! Target: 50× speedup for dispatch table lookups

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Clone, Debug)]
#[pyclass]
pub struct ToolEntry {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub gana: String,
    #[pyo3(get)]
    pub handler: String,
    #[pyo3(get)]
    pub enabled: bool,
}

#[pymethods]
impl ToolEntry {
    #[new]
    fn new(name: String, gana: String, handler: String) -> Self {
        Self {
            name,
            gana,
            handler,
            enabled: true,
        }
    }
}

#[pyclass]
pub struct PyDispatchTable {
    entries: Arc<RwLock<HashMap<String, ToolEntry>>>,
    gana_index: Arc<RwLock<HashMap<String, Vec<String>>>>,
}

#[pymethods]
impl PyDispatchTable {
    #[new]
    fn new() -> Self {
        Self {
            entries: Arc::new(RwLock::new(HashMap::new())),
            gana_index: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn register(&self, entry: ToolEntry) {
        let name = entry.name.clone();
        let gana = entry.gana.clone();
        
        self.entries.write().insert(name.clone(), entry);
        
        self.gana_index
            .write()
            .entry(gana)
            .or_insert_with(Vec::new)
            .push(name);
    }

    fn lookup(&self, tool_name: String) -> Option<ToolEntry> {
        self.entries.read().get(&tool_name).cloned()
    }

    fn lookup_by_gana(&self, gana: String) -> Vec<ToolEntry> {
        let gana_index = self.gana_index.read();
        let entries = self.entries.read();
        
        if let Some(tool_names) = gana_index.get(&gana) {
            tool_names
                .iter()
                .filter_map(|name| entries.get(name).cloned())
                .collect()
        } else {
            Vec::new()
        }
    }

    fn enable(&self, tool_name: String) -> bool {
        if let Some(entry) = self.entries.write().get_mut(&tool_name) {
            entry.enabled = true;
            true
        } else {
            false
        }
    }

    fn disable(&self, tool_name: String) -> bool {
        if let Some(entry) = self.entries.write().get_mut(&tool_name) {
            entry.enabled = false;
            true
        } else {
            false
        }
    }

    fn get_enabled_tools(&self) -> Vec<ToolEntry> {
        self.entries
            .read()
            .values()
            .filter(|e| e.enabled)
            .cloned()
            .collect()
    }

    fn tool_count(&self) -> usize {
        self.entries.read().len()
    }

    fn enabled_count(&self) -> usize {
        self.entries.read().values().filter(|e| e.enabled).count()
    }

    fn gana_count(&self) -> usize {
        self.gana_index.read().len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_table_creation() {
        let table = PyDispatchTable::new();
        assert_eq!(table.tool_count(), 0);
    }

    #[test]
    fn test_register() {
        let table = PyDispatchTable::new();
        let entry = ToolEntry::new("tool1".to_string(), "gana1".to_string(), "handler1".to_string());
        
        table.register(entry);
        assert_eq!(table.tool_count(), 1);
    }

    #[test]
    fn test_lookup() {
        let table = PyDispatchTable::new();
        let entry = ToolEntry::new("tool1".to_string(), "gana1".to_string(), "handler1".to_string());
        
        table.register(entry);
        
        let result = table.lookup("tool1".to_string());
        assert!(result.is_some());
    }

    #[test]
    fn test_enable_disable() {
        let table = PyDispatchTable::new();
        let entry = ToolEntry::new("tool1".to_string(), "gana1".to_string(), "handler1".to_string());
        
        table.register(entry);
        
        assert!(table.disable("tool1".to_string()));
        assert_eq!(table.enabled_count(), 0);
        
        assert!(table.enable("tool1".to_string()));
        assert_eq!(table.enabled_count(), 1);
    }

    #[test]
    fn test_lookup_by_gana() {
        let table = PyDispatchTable::new();
        
        table.register(ToolEntry::new("tool1".to_string(), "gana1".to_string(), "h1".to_string()));
        table.register(ToolEntry::new("tool2".to_string(), "gana1".to_string(), "h2".to_string()));
        
        let tools = table.lookup_by_gana("gana1".to_string());
        assert_eq!(tools.len(), 2);
    }
}
