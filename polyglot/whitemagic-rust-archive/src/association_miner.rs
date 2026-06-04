//! Association rule mining for discovering patterns in memory data
//!
//! This module implements Apriori-like frequent itemset mining and
//! association rule extraction for memory relationship discovery.

use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

/// Configuration for association mining
#[derive(Debug, Clone)]
pub struct MiningConfig {
    /// Minimum support threshold (0.0 - 1.0)
    pub min_support: f64,
    /// Minimum confidence threshold (0.0 - 1.0)
    pub min_confidence: f64,
    /// Maximum itemset size to consider
    pub max_itemset_size: usize,
    /// Minimum lift for interesting rules
    pub min_lift: f64,
}

impl Default for MiningConfig {
    fn default() -> Self {
        Self {
            min_support: 0.1,
            min_confidence: 0.5,
            max_itemset_size: 5,
            min_lift: 1.0,
        }
    }
}

/// Association rule with metrics
#[derive(Debug, Clone)]
#[pyclass]
pub struct AssociationRule {
    /// Antecedent items (IF part)
    #[pyo3(get)]
    pub antecedent: Vec<String>,
    /// Consequent items (THEN part)
    #[pyo3(get)]
    pub consequent: Vec<String>,
    /// Support count
    #[pyo3(get)]
    pub support: f64,
    /// Confidence of the rule
    #[pyo3(get)]
    pub confidence: f64,
    /// Lift ratio
    #[pyo3(get)]
    pub lift: f64,
}

/// Association miner for discovering frequent patterns
#[pyclass]
pub struct AssociationMiner {
    /// Minimum support threshold
    min_support: f64,
    /// Mining configuration
    config: MiningConfig,
    /// Frequent itemsets discovered
    frequent_itemsets: HashMap<Vec<String>, usize>,
    /// Association rules extracted
    rules: Vec<AssociationRule>,
}

#[pymethods]
impl AssociationMiner {
    /// Create a new association miner with minimum support threshold
    #[new]
    fn new(min_support: f64) -> Self {
        let config = MiningConfig {
            min_support,
            ..MiningConfig::default()
        };
        Self {
            min_support,
            config,
            frequent_itemsets: HashMap::new(),
            rules: Vec::new(),
        }
    }

    /// Create miner with full configuration
    #[staticmethod]
    fn with_config(min_support: f64, min_confidence: f64, min_lift: f64) -> Self {
        let config = MiningConfig {
            min_support,
            min_confidence,
            min_lift,
            ..MiningConfig::default()
        };
        Self {
            min_support,
            config,
            frequent_itemsets: HashMap::new(),
            rules: Vec::new(),
        }
    }

    /// Mine frequent itemsets from transactions
    /// Each transaction is a set of items (tags, entities, etc.)
    fn mine_frequent_itemsets(&mut self, transactions: Vec<Vec<String>>) -> Vec<Vec<String>> {
        self.frequent_itemsets.clear();
        let n_transactions = transactions.len() as f64;
        let min_count = (self.config.min_support * n_transactions).ceil() as usize;

        if transactions.is_empty() || min_count == 0 {
            return vec![];
        }

        // Count individual items
        let mut item_counts: HashMap<String, usize> = HashMap::new();
        for tx in &transactions {
            for item in tx {
                *item_counts.entry(item.clone()).or_default() += 1;
            }
        }

        // Filter by minimum support
        let frequent_1: HashSet<String> = item_counts
            .iter()
            .filter(|(_, &count)| count >= min_count)
            .map(|(item, _)| item.clone())
            .collect();

        // Store 1-itemsets
        for item in &frequent_1 {
            self.frequent_itemsets
                .insert(vec![item.clone()], item_counts[item]);
        }

        // Generate k-itemsets
        let mut k = 2;
        let mut prev_frequent: Vec<Vec<String>> =
            frequent_1.iter().map(|s| vec![s.clone()]).collect();

        while !prev_frequent.is_empty() && k <= self.config.max_itemset_size {
            // Generate candidates
            let candidates = generate_candidates_impl(&prev_frequent);

            // Count candidates
            let mut candidate_counts: HashMap<Vec<String>, usize> = HashMap::new();
            for tx in &transactions {
                let tx_set: HashSet<&String> = tx.iter().collect();
                for candidate in &candidates {
                    if candidate.iter().all(|item| tx_set.contains(item)) {
                        *candidate_counts.entry(candidate.clone()).or_default() += 1;
                    }
                }
            }

            // Filter by minimum support
            prev_frequent = candidate_counts
                .iter()
                .filter(|(_, &count)| count >= min_count)
                .map(|(itemset, &count)| {
                    self.frequent_itemsets.insert(itemset.clone(), count);
                    itemset.clone()
                })
                .collect();

            k += 1;
        }

        self.frequent_itemsets.keys().cloned().collect()
    }

    /// Extract association rules from frequent itemsets
    fn extract_rules(&mut self, transactions: Vec<Vec<String>>) -> Vec<PyObject> {
        self.rules.clear();
        let n_transactions = transactions.len() as f64;

        for (itemset, &support_count) in &self.frequent_itemsets {
            if itemset.len() < 2 {
                continue; // Need at least 2 items for a rule
            }

            // Generate all possible rules
            for i in 1..itemset.len() {
                for antecedent_indices in combinations_impl(itemset.len(), i) {
                    let mut antecedent: Vec<String> = antecedent_indices
                        .iter()
                        .map(|&idx| itemset[idx].clone())
                        .collect();
                    antecedent.sort();

                    let mut consequent: Vec<String> = (0..itemset.len())
                        .filter(|idx| !antecedent_indices.contains(idx))
                        .map(|idx| itemset[idx].clone())
                        .collect();
                    consequent.sort();

                    // Calculate confidence
                    let antecedent_support = self
                        .frequent_itemsets
                        .get(&antecedent)
                        .copied()
                        .unwrap_or(0);
                    if antecedent_support == 0 {
                        continue;
                    }

                    let confidence = support_count as f64 / antecedent_support as f64;

                    // Calculate lift
                    let consequent_support = self
                        .frequent_itemsets
                        .get(&consequent)
                        .copied()
                        .unwrap_or(0);
                    let expected_confidence = consequent_support as f64 / n_transactions;
                    let lift = if expected_confidence > 0.0 {
                        confidence / expected_confidence
                    } else {
                        0.0
                    };

                    // Filter by thresholds
                    if confidence >= self.config.min_confidence && lift >= self.config.min_lift {
                        self.rules.push(AssociationRule {
                            antecedent,
                            consequent,
                            support: support_count as f64 / n_transactions,
                            confidence,
                            lift,
                        });
                    }
                }
            }
        }

        // Sort by confidence descending
        self.rules
            .sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap());

        // Convert to PyObjects
        Python::with_gil(|py| {
            self.rules
                .iter()
                .map(|rule| {
                    let dict = pyo3::types::PyDict::new_bound(py);
                    dict.set_item("antecedent", rule.antecedent.clone())
                        .unwrap();
                    dict.set_item("consequent", rule.consequent.clone())
                        .unwrap();
                    dict.set_item("support", rule.support).unwrap();
                    dict.set_item("confidence", rule.confidence).unwrap();
                    dict.set_item("lift", rule.lift).unwrap();
                    dict.into()
                })
                .collect()
        })
    }

    /// Mine associations from transactions and return rules
    fn mine(&mut self, transactions: Vec<Vec<String>>) -> PyResult<Vec<PyObject>> {
        self.mine_frequent_itemsets(transactions.clone());
        let rules = self.extract_rules(transactions);
        Ok(rules)
    }

    /// Get number of frequent itemsets found
    fn itemset_count(&self) -> usize {
        self.frequent_itemsets.len()
    }

    /// Get number of rules extracted
    fn rule_count(&self) -> usize {
        self.rules.len()
    }

    /// Get minimum support threshold
    fn get_min_support(&self) -> f64 {
        self.min_support
    }

    /// Set minimum confidence threshold
    fn set_min_confidence(&mut self, confidence: f64) {
        self.config.min_confidence = confidence;
    }

    /// Get configuration
    fn get_config(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("min_support", self.config.min_support)?;
        dict.set_item("min_confidence", self.config.min_confidence)?;
        dict.set_item("max_itemset_size", self.config.max_itemset_size)?;
        dict.set_item("min_lift", self.config.min_lift)?;
        Ok(dict.into())
    }
}

/// Generate candidate itemsets of size k+1 from k-itemsets (internal helper)
fn generate_candidates_impl(itemsets: &[Vec<String>]) -> Vec<Vec<String>> {
    let mut candidates = Vec::new();
    let n = itemsets.len();

    for i in 0..n {
        for j in (i + 1)..n {
            let a = &itemsets[i];
            let b = &itemsets[j];

            if a.len() > 1 && b.len() > 1 {
                let prefix_match = a[..a.len() - 1] == b[..b.len() - 1];
                if prefix_match {
                    let mut candidate = a.clone();
                    candidate.push(b.last().unwrap().clone());
                    candidate.sort();
                    candidates.push(candidate);
                }
            } else if a.len() == 1 && b.len() == 1 {
                let mut candidate = vec![a[0].clone(), b[0].clone()];
                candidate.sort();
                candidates.push(candidate);
            }
        }
    }

    candidates
}

/// Get all combinations of k indices from n (internal helper)
fn combinations_impl(n: usize, k: usize) -> Vec<Vec<usize>> {
    if k == 0 || k > n {
        return vec![];
    }
    if k == 1 {
        return (0..n).map(|i| vec![i]).collect();
    }

    let mut result = Vec::new();
    let mut current = vec![0; k];
    combinations_helper_impl(n, k, &mut current, 0, 0, &mut result);
    result
}

fn combinations_helper_impl(
    n: usize,
    k: usize,
    current: &mut Vec<usize>,
    pos: usize,
    start: usize,
    result: &mut Vec<Vec<usize>>,
) {
    if pos == k {
        result.push(current.clone());
        return;
    }

    for i in start..n {
        current[pos] = i;
        combinations_helper_impl(n, k, current, pos + 1, i + 1, result);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_miner_creation() {
        let miner = AssociationMiner::new(0.1);
        assert_eq!(miner.get_min_support(), 0.1);
    }

    #[test]
    fn test_frequent_itemsets() {
        let mut miner = AssociationMiner::new(0.5);
        let transactions = vec![
            vec!["a".to_string(), "b".to_string()],
            vec!["a".to_string(), "c".to_string()],
            vec!["a".to_string(), "b".to_string()],
        ];

        let itemsets = miner.mine_frequent_itemsets(transactions);
        assert!(itemsets.iter().any(|i| i == &vec!["a".to_string()]));
    }

    #[test]
    fn test_combinations() {
        let combs = combinations_impl(3, 2);
        assert_eq!(combs.len(), 3); // C(3,2) = 3
    }
}
