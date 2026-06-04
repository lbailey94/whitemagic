//! Association mining for memory patterns
//! Discovers frequent co-occurrence patterns

use pyo3::prelude::*;
use std::collections::HashMap;
#[pyclass]
pub struct AssociationMiner {
    min_support: f64,
    min_confidence: f64,
}

#[pymethods]
impl AssociationMiner {
    #[new]
    fn new(min_support: Option<f64>, min_confidence: Option<f64>) -> Self {
        Self {
            min_support: min_support.unwrap_or(0.1),
            min_confidence: min_confidence.unwrap_or(0.5),
        }
    }
    
    fn mine_patterns(
        &self,
        transactions: Vec<Vec<String>>
    ) -> PyResult<Vec<(Vec<String>, Vec<String>, f64)>> {
        let mut patterns = Vec::new();
        let total = transactions.len() as f64;
        
        // Count item frequencies
        let mut item_counts: HashMap<String, usize> = HashMap::new();
        for transaction in &transactions {
            for item in transaction {
                *item_counts.entry(item.clone()).or_insert(0) += 1;
            }
        }
        
        // Find frequent items
        let frequent: Vec<String> = item_counts
            .iter()
            .filter(|(_, &count)| (count as f64 / total) >= self.min_support)
            .map(|(item, _)| item.clone())
            .collect();
        
        // Generate association rules
        for antecedent in &frequent {
            for consequent in &frequent {
                if antecedent != consequent {
                    let items = vec![antecedent.clone(), consequent.clone()];
                    let support = Self::calc_support(&transactions, &items);
                    
                    if support >= self.min_support {
                        let confidence = Self::calc_confidence(
                            &transactions,
                            antecedent,
                            consequent
                        );
                        
                        if confidence >= self.min_confidence {
                            patterns.push((
                                vec![antecedent.clone()],
                                vec![consequent.clone()],
                                confidence
                            ));
                        }
                    }
                }
            }
        }
        
        Ok(patterns)
    }
    
}

impl AssociationMiner {
    fn calc_support(transactions: &[Vec<String>], items: &[String]) -> f64 {
        let count = transactions
            .iter()
            .filter(|t| items.iter().all(|item| t.contains(item)))
            .count();
        count as f64 / transactions.len().max(1) as f64
    }
    
    fn calc_confidence(transactions: &[Vec<String>], ante: &str, cons: &str) -> f64 {
        let ante_count = transactions.iter().filter(|t| t.contains(&ante.to_string())).count();
        let both_count = transactions
            .iter()
            .filter(|t| t.contains(&ante.to_string()) && t.contains(&cons.to_string()))
            .count();
        if ante_count == 0 { 0.0 } else { both_count as f64 / ante_count as f64 }
    }
}
