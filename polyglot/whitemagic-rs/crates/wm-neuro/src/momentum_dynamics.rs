//! Momentum Dynamics — momentum term for spreading activation.
//!
//! Based on RNN replay dynamics (arXiv, Feb 2026): hidden state momentum
//! enables temporally compressed replay. We add a momentum term to the
//! spreading activation engine: nodes that were recently activated get
//! a boost, creating temporal continuity in the activation pattern.

use std::collections::HashMap;

pub struct MomentumDynamics {
    /// Per-node momentum values
    momentum: HashMap<String, f64>,
    /// Momentum coefficient (how much previous momentum carries forward)
    momentum_coeff: f64,
    /// Decay rate per cycle
    decay_rate: f64,
    /// Minimum momentum to retain
    min_momentum: f64,
    /// Statistics
    pub total_updates: u64,
    total_decays: u64,
}

impl MomentumDynamics {
    pub fn new(momentum_coeff: f64, decay_rate: f64) -> Self {
        Self {
            momentum: HashMap::new(),
            momentum_coeff,
            decay_rate,
            min_momentum: 0.01,
            total_updates: 0,
            total_decays: 0,
        }
    }

    /// Update momentum for a set of activated nodes
    pub fn update(&mut self, activations: &HashMap<String, f64>) {
        self.total_updates += 1;
        for (node_id, &activation) in activations {
            let current = self.momentum.get(node_id).unwrap_or(&0.0);
            let new_momentum = *current * self.momentum_coeff + activation;
            self.momentum.insert(node_id.clone(), new_momentum);
        }
    }

    /// Decay all momentum values
    pub fn decay(&mut self) {
        self.total_decays += 1;
        let decay = self.decay_rate;
        let min = self.min_momentum;
        self.momentum.retain(|_, m| {
            *m *= decay;
            *m > min
        });
    }

    /// Get momentum for a specific node
    pub fn get(&self, node_id: &str) -> f64 {
        *self.momentum.get(node_id).unwrap_or(&0.0)
    }

    /// Apply momentum boost to activation scores
    pub fn apply_momentum(&self, scores: &[(String, f64)]) -> Vec<(String, f64)> {
        scores.iter().map(|(node_id, score)| {
            let mom = self.get(node_id);
            (node_id.clone(), score + mom * self.momentum_coeff)
        }).collect()
    }

    /// Get all nodes with momentum above threshold
    pub fn active_nodes(&self, threshold: f64) -> Vec<(String, f64)> {
        let mut nodes: Vec<_> = self.momentum.iter()
            .filter(|(_, &m)| m > threshold)
            .map(|(k, &v)| (k.clone(), v))
            .collect();
        nodes.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        nodes
    }

    pub fn stats(&self) -> HashMap<String, f64> {
        let mut s = HashMap::new();
        s.insert("total_updates".to_string(), self.total_updates as f64);
        s.insert("total_decays".to_string(), self.total_decays as f64);
        s.insert("active_nodes".to_string(), self.momentum.len() as f64);
        s.insert("momentum_coeff".to_string(), self.momentum_coeff);
        s.insert("decay_rate".to_string(), self.decay_rate);
        s
    }

    pub fn reset(&mut self) {
        self.momentum.clear();
        self.total_updates = 0;
        self.total_decays = 0;
    }
}

impl Default for MomentumDynamics {
    fn default() -> Self {
        Self::new(0.9, 0.85)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_momentum() {
        let md = MomentumDynamics::new(0.9, 0.85);
        assert_eq!(md.get("nonexistent"), 0.0);
    }

    #[test]
    fn test_update_and_get() {
        let mut md = MomentumDynamics::new(0.9, 0.85);
        let mut activations = HashMap::new();
        activations.insert("node1".to_string(), 0.8);
        md.update(&activations);
        assert!(md.get("node1") > 0.0);
    }

    #[test]
    fn test_momentum_accumulates() {
        let mut md = MomentumDynamics::new(0.9, 0.85);
        let mut activations = HashMap::new();
        activations.insert("n".to_string(), 0.5);
        md.update(&activations);
        let m1 = md.get("n");
        md.update(&activations);
        let m2 = md.get("n");
        assert!(m2 > m1);
    }

    #[test]
    fn test_decay_reduces_momentum() {
        let mut md = MomentumDynamics::new(0.9, 0.5); // fast decay
        let mut activations = HashMap::new();
        activations.insert("n".to_string(), 0.8);
        md.update(&activations);
        let m1 = md.get("n");
        md.decay();
        let m2 = md.get("n");
        assert!(m2 < m1);
    }

    #[test]
    fn test_decay_prunes_weak() {
        let mut md = MomentumDynamics::new(0.9, 0.1); // very fast decay
        let mut activations = HashMap::new();
        activations.insert("weak".to_string(), 0.01);
        md.update(&activations);
        md.decay();
        assert_eq!(md.get("weak"), 0.0); // pruned
    }

    #[test]
    fn test_apply_momentum() {
        let mut md = MomentumDynamics::new(0.9, 0.85);
        let mut activations = HashMap::new();
        activations.insert("a".to_string(), 1.0);
        md.update(&activations);
        let scores = vec![("a".to_string(), 0.5), ("b".to_string(), 0.5)];
        let boosted = md.apply_momentum(&scores);
        let a_score = boosted.iter().find(|(n, _)| n == "a").unwrap().1;
        let b_score = boosted.iter().find(|(n, _)| n == "b").unwrap().1;
        assert!(a_score > b_score);
    }

    #[test]
    fn test_active_nodes() {
        let mut md = MomentumDynamics::new(0.9, 0.85);
        let mut activations = HashMap::new();
        activations.insert("high".to_string(), 0.9);
        activations.insert("low".to_string(), 0.05);
        md.update(&activations);
        let active = md.active_nodes(0.1);
        assert_eq!(active.len(), 1);
        assert_eq!(active[0].0, "high");
    }
}
