//! Dependency Resolver - Task Dependency Resolution (PSR-007)
//! Target: 50× speedup for dependency resolution

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};

#[pyclass]
pub struct PyDependencyResolver {
    dependencies: HashMap<String, Vec<String>>,
}

#[pymethods]
impl PyDependencyResolver {
    #[new]
    fn new() -> Self {
        Self {
            dependencies: HashMap::new(),
        }
    }

    fn add_dependency(&mut self, task: String, depends_on: String) {
        self.dependencies
            .entry(task)
            .or_insert_with(Vec::new)
            .push(depends_on);
    }

    fn resolve(&self, task: String) -> PyResult<Vec<String>> {
        let mut resolved = Vec::new();
        let mut visited = HashSet::new();
        
        self.resolve_recursive(&task, &mut resolved, &mut visited)?;
        
        Ok(resolved)
    }

    fn topological_sort(&self) -> PyResult<Vec<String>> {
        let mut in_degree: HashMap<String, usize> = HashMap::new();
        let mut all_tasks: HashSet<String> = HashSet::new();
        
        for (task, deps) in &self.dependencies {
            all_tasks.insert(task.clone());
            in_degree.entry(task.clone()).or_insert(0);
            
            for dep in deps {
                all_tasks.insert(dep.clone());
                *in_degree.entry(dep.clone()).or_insert(0) += 0;
                *in_degree.entry(task.clone()).or_insert(0) += 1;
            }
        }
        
        let mut queue: VecDeque<String> = in_degree
            .iter()
            .filter(|(_, &deg)| deg == 0)
            .map(|(task, _)| task.clone())
            .collect();
        
        let mut result = Vec::new();
        
        while let Some(task) = queue.pop_front() {
            result.push(task.clone());
            
            for (dependent, deps) in &self.dependencies {
                if deps.contains(&task) {
                    let degree = in_degree.get_mut(dependent).unwrap();
                    *degree -= 1;
                    
                    if *degree == 0 {
                        queue.push_back(dependent.clone());
                    }
                }
            }
        }
        
        if result.len() != all_tasks.len() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Circular dependency detected",
            ));
        }
        
        Ok(result)
    }

    fn has_cycle(&self) -> bool {
        self.topological_sort().is_err()
    }

    fn dependency_count(&self) -> usize {
        self.dependencies.len()
    }
}

impl PyDependencyResolver {
    fn resolve_recursive(
        &self,
        task: &str,
        resolved: &mut Vec<String>,
        visited: &mut HashSet<String>,
    ) -> PyResult<()> {
        if visited.contains(task) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Circular dependency detected",
            ));
        }
        
        visited.insert(task.to_string());
        
        if let Some(deps) = self.dependencies.get(task) {
            for dep in deps {
                if !resolved.contains(dep) {
                    self.resolve_recursive(dep, resolved, visited)?;
                }
            }
        }
        
        if !resolved.contains(&task.to_string()) {
            resolved.push(task.to_string());
        }
        
        visited.remove(task);
        
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resolver_creation() {
        let resolver = PyDependencyResolver::new();
        assert_eq!(resolver.dependency_count(), 0);
    }

    #[test]
    fn test_add_dependency() {
        let mut resolver = PyDependencyResolver::new();
        resolver.add_dependency("task1".to_string(), "task0".to_string());
        
        assert_eq!(resolver.dependency_count(), 1);
    }

    #[test]
    fn test_resolve() {
        let mut resolver = PyDependencyResolver::new();
        resolver.add_dependency("task2".to_string(), "task1".to_string());
        resolver.add_dependency("task1".to_string(), "task0".to_string());
        
        let resolved = resolver.resolve("task2".to_string()).unwrap();
        assert_eq!(resolved.len(), 3);
    }

    #[test]
    fn test_topological_sort() {
        let mut resolver = PyDependencyResolver::new();
        resolver.add_dependency("task2".to_string(), "task1".to_string());
        resolver.add_dependency("task1".to_string(), "task0".to_string());
        
        let sorted = resolver.topological_sort().unwrap();
        assert!(!sorted.is_empty());
    }

    #[test]
    fn test_cycle_detection() {
        let mut resolver = PyDependencyResolver::new();
        resolver.add_dependency("task1".to_string(), "task2".to_string());
        resolver.add_dependency("task2".to_string(), "task1".to_string());
        
        assert!(resolver.has_cycle());
    }
}
