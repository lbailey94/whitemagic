//! Thalamic Gating — sub-ms galaxy access mask computation.
//!
//! Based on GATE (PLOS Comp Bio, 2026): EC3→CA1→EC5→EC3 self-gating loop
//! for selective memory maintenance. We implement a lightweight version
//! that computes per-galaxy weight multipliers based on cognitive context.

use std::collections::HashMap;

/// Predefined context masks (galaxy → weight multiplier)
fn default_masks() -> HashMap<&'static str, HashMap<&'static str, f64>> {
    let mut masks = HashMap::new();

    let mut default_mask = HashMap::new();
    for g in ["universal", "codex", "sessions", "citta", "dreams", "research", "aria", "journals", "substrate", "tutorial"] {
        default_mask.insert(g, 1.0);
    }
    masks.insert("default", default_mask);

    let mut coding = HashMap::new();
    coding.insert("codex", 1.5);
    coding.insert("sessions", 1.2);
    coding.insert("universal", 0.8);
    coding.insert("citta", 0.6);
    coding.insert("dreams", 0.3);
    coding.insert("research", 0.7);
    coding.insert("aria", 0.5);
    coding.insert("journals", 0.4);
    coding.insert("substrate", 0.5);
    coding.insert("tutorial", 0.6);
    masks.insert("coding", coding);

    let mut research = HashMap::new();
    research.insert("research", 1.6);
    research.insert("codex", 1.0);
    research.insert("universal", 0.9);
    research.insert("citta", 0.5);
    research.insert("dreams", 0.4);
    research.insert("sessions", 0.6);
    research.insert("aria", 0.7);
    research.insert("journals", 1.1);
    research.insert("substrate", 0.5);
    research.insert("tutorial", 0.8);
    masks.insert("research", research);

    let mut introspection = HashMap::new();
    introspection.insert("citta", 1.8);
    introspection.insert("aria", 1.5);
    introspection.insert("journals", 1.3);
    introspection.insert("dreams", 1.2);
    introspection.insert("universal", 0.7);
    introspection.insert("codex", 0.5);
    introspection.insert("sessions", 0.6);
    introspection.insert("research", 0.6);
    introspection.insert("substrate", 0.5);
    introspection.insert("tutorial", 0.7);
    masks.insert("introspection", introspection);

    let mut creative = HashMap::new();
    creative.insert("dreams", 1.6);
    creative.insert("aria", 1.4);
    creative.insert("citta", 1.2);
    creative.insert("universal", 1.0);
    creative.insert("codex", 0.7);
    creative.insert("sessions", 0.6);
    creative.insert("research", 0.8);
    creative.insert("journals", 0.9);
    creative.insert("substrate", 0.5);
    creative.insert("tutorial", 0.6);
    masks.insert("creative", creative);

    let mut session = HashMap::new();
    session.insert("sessions", 1.7);
    session.insert("codex", 1.0);
    session.insert("citta", 0.8);
    session.insert("universal", 0.9);
    session.insert("dreams", 0.4);
    session.insert("research", 0.6);
    session.insert("aria", 0.7);
    session.insert("journals", 0.5);
    session.insert("substrate", 0.5);
    session.insert("tutorial", 0.6);
    masks.insert("session", session);

    masks
}

pub struct ThalamicGate {
    masks: HashMap<&'static str, HashMap<&'static str, f64>>,
    current_context: String,
    cross_galaxy_factor: f64,
    pub total_calls: u64,  // kept pub for potential future use
}

impl ThalamicGate {
    pub fn new() -> Self {
        Self {
            masks: default_masks(),
            current_context: "default".to_string(),
            cross_galaxy_factor: 0.5,
            total_calls: 0,
        }
    }

    pub fn set_context(&mut self, context: &str) {
        if self.masks.contains_key(context) {
            self.current_context = context.to_string();
        } else {
            self.current_context = "default".to_string();
        }
    }

    pub fn get_context(&self) -> &str {
        &self.current_context
    }

    pub fn get_mask(&self, context: Option<&str>) -> &HashMap<&'static str, f64> {
        let ctx = context.unwrap_or(&self.current_context);
        self.masks.get(ctx).unwrap_or(self.masks.get("default").unwrap())
    }

    pub fn compute_weights(&mut self, galaxies: &[&str]) -> HashMap<String, f64> {
        self.total_calls += 1;
        let mask = self.get_mask(None);
        let mut weights = HashMap::new();
        for g in galaxies {
            let w = *mask.get(*g).unwrap_or(&1.0);
            weights.insert(g.to_string(), w);
        }
        weights
    }

    pub fn apply_to_scores(&mut self, galaxies: &[(&str, f64)]) -> Vec<(String, f64)> {
        self.total_calls += 1;
        let mask = self.get_mask(None);
        galaxies.iter().map(|(g, score)| {
            let w = *mask.get(*g).unwrap_or(&1.0);
            (g.to_string(), score * w)
        }).collect()
    }

    pub fn set_cross_galaxy_factor(&mut self, factor: f64) {
        self.cross_galaxy_factor = factor;
    }

    pub fn stats(&self) -> HashMap<String, f64> {
        let mut s = HashMap::new();
        s.insert("total_calls".to_string(), self.total_calls as f64);
        s.insert("cross_galaxy_factor".to_string(), self.cross_galaxy_factor);
        s.insert("context_count".to_string(), self.masks.len() as f64);
        s
    }
}

impl Default for ThalamicGate {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_context() {
        let gate = ThalamicGate::new();
        assert_eq!(gate.get_context(), "default");
    }

    #[test]
    fn test_set_context() {
        let mut gate = ThalamicGate::new();
        gate.set_context("coding");
        assert_eq!(gate.get_context(), "coding");
    }

    #[test]
    fn test_unknown_context_falls_back() {
        let mut gate = ThalamicGate::new();
        gate.set_context("nonexistent");
        assert_eq!(gate.get_context(), "default");
    }

    #[test]
    fn test_compute_weights() {
        let mut gate = ThalamicGate::new();
        gate.set_context("coding");
        let weights = gate.compute_weights(&["codex", "citta", "universal"]);
        assert!(weights["codex"] > weights["citta"]);
        assert!(weights["codex"] > weights["universal"]);
    }

    #[test]
    fn test_apply_to_scores() {
        let mut gate = ThalamicGate::new();
        gate.set_context("introspection");
        let scores = vec![("citta", 1.0), ("codex", 1.0)];
        let result = gate.apply_to_scores(&scores);
        let citta_score = result.iter().find(|(g, _)| g == "citta").unwrap().1;
        let codex_score = result.iter().find(|(g, _)| g == "codex").unwrap().1;
        assert!(citta_score > codex_score);
    }
}
