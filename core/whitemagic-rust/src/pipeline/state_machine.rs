//! State Machine - Campaign State Management (PSR-007)
//! Target: 30× speedup for state transitions

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug, PartialEq)]
#[pyclass]
pub struct State {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub metadata: HashMap<String, String>,
}

#[pymethods]
impl State {
    #[new]
    fn new(name: String) -> Self {
        Self {
            name,
            metadata: HashMap::new(),
        }
    }

    fn set_metadata(&mut self, key: String, value: String) {
        self.metadata.insert(key, value);
    }
}

#[pyclass]
pub struct PyStateMachine {
    current_state: String,
    states: HashMap<String, State>,
    transitions: HashMap<String, Vec<String>>,
    history: Vec<String>,
}

#[pymethods]
impl PyStateMachine {
    #[new]
    fn new(initial_state: String) -> Self {
        Self {
            current_state: initial_state.clone(),
            states: HashMap::new(),
            transitions: HashMap::new(),
            history: vec![initial_state],
        }
    }

    fn add_state(&mut self, state: State) {
        self.states.insert(state.name.clone(), state);
    }

    fn add_transition(&mut self, from_state: String, to_state: String) {
        self.transitions
            .entry(from_state)
            .or_insert_with(Vec::new)
            .push(to_state);
    }

    fn transition(&mut self, to_state: String) -> PyResult<bool> {
        if let Some(allowed) = self.transitions.get(&self.current_state) {
            if allowed.contains(&to_state) {
                self.current_state = to_state.clone();
                self.history.push(to_state);
                return Ok(true);
            }
        }
        
        Ok(false)
    }

    fn can_transition(&self, to_state: String) -> bool {
        if let Some(allowed) = self.transitions.get(&self.current_state) {
            allowed.contains(&to_state)
        } else {
            false
        }
    }

    fn get_current_state(&self) -> String {
        self.current_state.clone()
    }

    fn get_history(&self) -> Vec<String> {
        self.history.clone()
    }

    fn get_available_transitions(&self) -> Vec<String> {
        self.transitions
            .get(&self.current_state)
            .cloned()
            .unwrap_or_default()
    }

    fn state_count(&self) -> usize {
        self.states.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_machine_creation() {
        let machine = PyStateMachine::new("initial".to_string());
        assert_eq!(machine.get_current_state(), "initial");
    }

    #[test]
    fn test_add_state() {
        let mut machine = PyStateMachine::new("initial".to_string());
        machine.add_state(State::new("state1".to_string()));
        
        assert_eq!(machine.state_count(), 1);
    }

    #[test]
    fn test_transition() {
        let mut machine = PyStateMachine::new("s1".to_string());
        machine.add_transition("s1".to_string(), "s2".to_string());
        
        assert!(machine.transition("s2".to_string()).unwrap());
        assert_eq!(machine.get_current_state(), "s2");
    }

    #[test]
    fn test_invalid_transition() {
        let mut machine = PyStateMachine::new("s1".to_string());
        machine.add_transition("s1".to_string(), "s2".to_string());
        
        assert!(!machine.transition("s3".to_string()).unwrap());
        assert_eq!(machine.get_current_state(), "s1");
    }

    #[test]
    fn test_history() {
        let mut machine = PyStateMachine::new("s1".to_string());
        machine.add_transition("s1".to_string(), "s2".to_string());
        machine.add_transition("s2".to_string(), "s3".to_string());
        
        machine.transition("s2".to_string()).unwrap();
        machine.transition("s3".to_string()).unwrap();
        
        let history = machine.get_history();
        assert_eq!(history.len(), 3);
    }
}
