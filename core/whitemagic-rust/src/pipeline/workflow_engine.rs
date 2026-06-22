//! Workflow Engine - Workflow Execution (PSR-007)
//! Target: 30× speedup for workflow execution

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
#[pyclass]
pub struct WorkflowStep {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub action: String,
    #[pyo3(get)]
    pub dependencies: Vec<String>,
}

#[pymethods]
impl WorkflowStep {
    #[new]
    fn new(name: String, action: String, dependencies: Vec<String>) -> Self {
        Self {
            name,
            action,
            dependencies,
        }
    }
}

#[pyclass]
pub struct PyWorkflowEngine {
    workflows: HashMap<String, Vec<WorkflowStep>>,
    execution_state: HashMap<String, HashMap<String, bool>>,
}

#[pymethods]
impl PyWorkflowEngine {
    #[new]
    fn new() -> Self {
        Self {
            workflows: HashMap::new(),
            execution_state: HashMap::new(),
        }
    }

    fn register_workflow(&mut self, workflow_id: String, steps: Vec<WorkflowStep>) {
        self.workflows.insert(workflow_id.clone(), steps);
        self.execution_state.insert(workflow_id, HashMap::new());
    }

    fn execute_step(&mut self, workflow_id: String, step_name: String) -> bool {
        if let Some(workflow) = self.workflows.get(&workflow_id) {
            if let Some(step) = workflow.iter().find(|s| s.name == step_name) {
                let state = self.execution_state.get(&workflow_id).unwrap();
                
                for dep in &step.dependencies {
                    if !state.get(dep).unwrap_or(&false) {
                        return false;
                    }
                }
                
                self.execution_state
                    .get_mut(&workflow_id)
                    .unwrap()
                    .insert(step_name, true);
                
                return true;
            }
        }
        false
    }

    fn get_ready_steps(&self, workflow_id: String) -> Vec<String> {
        if let Some(workflow) = self.workflows.get(&workflow_id) {
            let state = self.execution_state.get(&workflow_id).unwrap();
            
            workflow
                .iter()
                .filter(|step| {
                    !state.get(&step.name).unwrap_or(&false)
                        && step.dependencies.iter().all(|d| state.get(d).unwrap_or(&false))
                })
                .map(|s| s.name.clone())
                .collect()
        } else {
            Vec::new()
        }
    }

    fn is_complete(&self, workflow_id: String) -> bool {
        if let Some(workflow) = self.workflows.get(&workflow_id) {
            let state = self.execution_state.get(&workflow_id).unwrap();
            workflow.iter().all(|s| state.get(&s.name).unwrap_or(&false))
        } else {
            false
        }
    }

    fn workflow_count(&self) -> usize {
        self.workflows.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_creation() {
        let engine = PyWorkflowEngine::new();
        assert_eq!(engine.workflow_count(), 0);
    }

    #[test]
    fn test_register_workflow() {
        let mut engine = PyWorkflowEngine::new();
        let steps = vec![
            WorkflowStep::new("step1".to_string(), "action1".to_string(), vec![]),
        ];
        
        engine.register_workflow("wf1".to_string(), steps);
        assert_eq!(engine.workflow_count(), 1);
    }

    #[test]
    fn test_execute_step() {
        let mut engine = PyWorkflowEngine::new();
        let steps = vec![
            WorkflowStep::new("step1".to_string(), "action1".to_string(), vec![]),
        ];
        
        engine.register_workflow("wf1".to_string(), steps);
        assert!(engine.execute_step("wf1".to_string(), "step1".to_string()));
    }

    #[test]
    fn test_dependencies() {
        let mut engine = PyWorkflowEngine::new();
        let steps = vec![
            WorkflowStep::new("step1".to_string(), "action1".to_string(), vec![]),
            WorkflowStep::new("step2".to_string(), "action2".to_string(), vec!["step1".to_string()]),
        ];
        
        engine.register_workflow("wf1".to_string(), steps);
        
        assert!(!engine.execute_step("wf1".to_string(), "step2".to_string()));
        assert!(engine.execute_step("wf1".to_string(), "step1".to_string()));
        assert!(engine.execute_step("wf1".to_string(), "step2".to_string()));
    }
}
