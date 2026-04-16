//! Reasoning Engine - Logical Reasoning (PSR-004)
//! Target: 30× speedup for reasoning operations

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

#[derive(Clone, Debug)]
#[pyclass]
pub struct Fact {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub predicate: String,
    #[pyo3(get)]
    pub subject: String,
    #[pyo3(get)]
    pub object: String,
    #[pyo3(get)]
    pub confidence: f64,
}

#[pymethods]
impl Fact {
    #[new]
    fn new(id: String, predicate: String, subject: String, object: String, confidence: f64) -> Self {
        Self {
            id,
            predicate,
            subject,
            object,
            confidence,
        }
    }
}

#[derive(Clone, Debug)]
#[pyclass]
pub struct Rule {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub conditions: Vec<String>,
    #[pyo3(get)]
    pub conclusion: String,
}

#[pymethods]
impl Rule {
    #[new]
    fn new(id: String, conditions: Vec<String>, conclusion: String) -> Self {
        Self {
            id,
            conditions,
            conclusion,
        }
    }
}

#[pyclass]
pub struct PyReasoningEngine {
    facts: HashMap<String, Fact>,
    rules: HashMap<String, Rule>,
}

#[pymethods]
impl PyReasoningEngine {
    #[new]
    fn new() -> Self {
        Self {
            facts: HashMap::new(),
            rules: HashMap::new(),
        }
    }

    fn add_fact(&mut self, fact: Fact) {
        self.facts.insert(fact.id.clone(), fact);
    }

    fn add_rule(&mut self, rule: Rule) {
        self.rules.insert(rule.id.clone(), rule);
    }

    fn query(&self, predicate: String, subject: Option<String>, object: Option<String>) -> Vec<Fact> {
        self.facts
            .values()
            .filter(|fact| {
                fact.predicate == predicate
                    && subject.as_ref().map_or(true, |s| &fact.subject == s)
                    && object.as_ref().map_or(true, |o| &fact.object == o)
            })
            .cloned()
            .collect()
    }

    fn infer(&self, max_iterations: Option<usize>) -> Vec<Fact> {
        let mut inferred = Vec::new();
        let mut current_facts = self.facts.clone();
        let iterations = max_iterations.unwrap_or(10);
        
        for _ in 0..iterations {
            let mut new_facts = Vec::new();
            
            for rule in self.rules.values() {
                if self.check_conditions(&rule.conditions, &current_facts) {
                    if let Some(fact) = self.apply_rule(rule, &current_facts) {
                        if !current_facts.contains_key(&fact.id) {
                            new_facts.push(fact);
                        }
                    }
                }
            }
            
            if new_facts.is_empty() {
                break;
            }
            
            for fact in new_facts {
                current_facts.insert(fact.id.clone(), fact.clone());
                inferred.push(fact);
            }
        }
        
        inferred
    }

    fn explain(&self, fact_id: String) -> Vec<String> {
        let mut explanation = Vec::new();
        let mut visited = HashSet::new();
        
        self.explain_recursive(&fact_id, &mut explanation, &mut visited);
        
        explanation
    }

    fn get_related_facts(&self, fact_id: String, max_depth: Option<usize>) -> Vec<Fact> {
        let depth_limit = max_depth.unwrap_or(2);
        let mut related = Vec::new();
        let mut visited = HashSet::new();
        
        if let Some(fact) = self.facts.get(&fact_id) {
            self.find_related(fact, 0, depth_limit, &mut related, &mut visited);
        }
        
        related
    }

    fn fact_count(&self) -> usize {
        self.facts.len()
    }

    fn rule_count(&self) -> usize {
        self.rules.len()
    }
}

impl PyReasoningEngine {
    fn check_conditions(&self, conditions: &[String], facts: &HashMap<String, Fact>) -> bool {
        conditions.iter().all(|cond| facts.contains_key(cond))
    }

    fn apply_rule(&self, rule: &Rule, facts: &HashMap<String, Fact>) -> Option<Fact> {
        let confidence = rule.conditions
            .iter()
            .filter_map(|cond_id| facts.get(cond_id))
            .map(|fact| fact.confidence)
            .fold(1.0, |acc, conf| acc * conf);
        
        Some(Fact {
            id: format!("inferred_{}", rule.id),
            predicate: "inferred".to_string(),
            subject: rule.conclusion.clone(),
            object: "true".to_string(),
            confidence,
        })
    }

    fn explain_recursive(&self, fact_id: &str, explanation: &mut Vec<String>, visited: &mut HashSet<String>) {
        if visited.contains(fact_id) {
            return;
        }
        
        visited.insert(fact_id.to_string());
        
        if let Some(fact) = self.facts.get(fact_id) {
            explanation.push(format!("{} {} {}", fact.subject, fact.predicate, fact.object));
            
            for rule in self.rules.values() {
                if rule.conclusion == fact.subject {
                    for condition in &rule.conditions {
                        self.explain_recursive(condition, explanation, visited);
                    }
                }
            }
        }
    }

    fn find_related(&self, fact: &Fact, depth: usize, max_depth: usize, related: &mut Vec<Fact>, visited: &mut HashSet<String>) {
        if depth >= max_depth || visited.contains(&fact.id) {
            return;
        }
        
        visited.insert(fact.id.clone());
        related.push(fact.clone());
        
        for other_fact in self.facts.values() {
            if other_fact.subject == fact.object || other_fact.object == fact.subject {
                self.find_related(other_fact, depth + 1, max_depth, related, visited);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_creation() {
        let engine = PyReasoningEngine::new();
        assert_eq!(engine.fact_count(), 0);
    }

    #[test]
    fn test_add_fact() {
        let mut engine = PyReasoningEngine::new();
        let fact = Fact::new("f1".to_string(), "is".to_string(), "sky".to_string(), "blue".to_string(), 1.0);
        
        engine.add_fact(fact);
        assert_eq!(engine.fact_count(), 1);
    }

    #[test]
    fn test_query() {
        let mut engine = PyReasoningEngine::new();
        let fact = Fact::new("f1".to_string(), "is".to_string(), "sky".to_string(), "blue".to_string(), 1.0);
        
        engine.add_fact(fact);
        
        let results = engine.query("is".to_string(), Some("sky".to_string()), None);
        assert_eq!(results.len(), 1);
    }

    #[test]
    fn test_add_rule() {
        let mut engine = PyReasoningEngine::new();
        let rule = Rule::new("r1".to_string(), vec!["f1".to_string()], "conclusion".to_string());
        
        engine.add_rule(rule);
        assert_eq!(engine.rule_count(), 1);
    }
}
