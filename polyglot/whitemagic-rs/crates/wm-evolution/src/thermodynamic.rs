//! Thermodynamic Resource Allocation (Objective Q)
//!
//! Models improvement selection as a thermodynamic system with simulated annealing.
//!
//! - Temperature = exploration rate
//! - Energy = predicted impact (lower energy = better improvement)
//! - Selection probability: P(select i) ∝ exp(-E_i / T) (Boltzmann distribution)

use serde::{Deserialize, Serialize};

/// State of the thermodynamic selection system.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThermodynamicState {
    pub temperature: f64,
    pub cooling_rate: f64,
    pub reheat_amount: f64,
    pub min_temperature: f64,
    pub max_temperature: f64,
    pub cycle_count: i32,
    pub discovery_rate_history: Vec<f64>,
}

impl Default for ThermodynamicState {
    fn default() -> Self {
        Self {
            temperature: 1.0,
            cooling_rate: 0.95,
            reheat_amount: 0.3,
            min_temperature: 0.01,
            max_temperature: 2.0,
            cycle_count: 0,
            discovery_rate_history: Vec::new(),
        }
    }
}

impl ThermodynamicState {
    /// Apply one step of the cooling schedule.
    pub fn cool(&mut self) {
        self.temperature = (self.temperature * self.cooling_rate).max(self.min_temperature);
        self.cycle_count += 1;
    }

    /// Reheat based on emergence signal.
    pub fn reheat(&mut self, emergence_signal: f64) {
        self.temperature = (self.temperature + self.reheat_amount * emergence_signal)
            .min(self.max_temperature);
    }

    /// Adapt temperature based on discovery rate and emergence signal.
    pub fn adapt(&mut self, discovery_rate: f64, emergence_signal: f64) {
        self.discovery_rate_history.push(discovery_rate);

        let rate = if self.discovery_rate_history.len() >= 2 {
            let n = self.discovery_rate_history.len();
            let recent = self.discovery_rate_history[n - 1];
            let previous = self.discovery_rate_history[n - 2];
            if recent < previous {
                self.cooling_rate * self.cooling_rate // cool faster
            } else {
                self.cooling_rate
            }
        } else {
            self.cooling_rate
        };

        self.temperature = (self.temperature * rate).max(self.min_temperature);

        if emergence_signal > 0.0 {
            self.reheat(emergence_signal);
        }

        self.cycle_count += 1;
    }

    /// Classify current phase: "hot", "warm", or "cold".
    pub fn exploration_phase(&self) -> &'static str {
        if self.temperature > 0.7 {
            "hot"
        } else if self.temperature > 0.2 {
            "warm"
        } else {
            "cold"
        }
    }
}

/// Compute Boltzmann probabilities for a set of energies.
///
/// P(select i) ∝ exp(-E_i / T)
pub fn boltzmann_probabilities(energies: &[f64], temperature: f64) -> Vec<f64> {
    if energies.is_empty() {
        return vec![];
    }

    let max_e = energies.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let t = temperature.max(1e-10);
    let weights: Vec<f64> = energies.iter().map(|&e| (-(e - max_e) / t).exp()).collect();
    let total: f64 = weights.iter().sum();

    if total <= 0.0 {
        return vec![1.0 / energies.len() as f64; energies.len()];
    }

    weights.iter().map(|&w| w / total).collect()
}

/// Select k items using Boltzmann (softmax) distribution.
///
/// Uses a simple weighted random selection without replacement.
/// `indices` maps energies to item indices for the result.
pub fn boltzmann_select(energies: &[f64], temperature: f64, k: usize, seed: u64) -> Vec<usize> {
    if energies.is_empty() {
        return vec![];
    }
    if energies.len() == 1 {
        return vec![0];
    }

    let k = k.min(energies.len());
    let probs = boltzmann_probabilities(energies, temperature);

    let mut remaining_indices: Vec<usize> = (0..energies.len()).collect();
    let mut remaining_probs = probs.clone();
    let mut selected = Vec::with_capacity(k);
    let mut rng_state = seed;

    for _ in 0..k {
        let prob_sum: f64 = remaining_probs.iter().sum();
        if prob_sum <= 0.0 {
            break;
        }

        // Normalize
        let normalized: Vec<f64> = remaining_probs.iter().map(|p| p / prob_sum).collect();

        // Weighted random choice using LCG
        rng_state = lcg_next(rng_state);
        let r = (rng_state % 2147483647) as f64 / 2147483647.0;

        let mut cumulative = 0.0;
        let mut chosen_idx = 0;
        for (i, &p) in normalized.iter().enumerate() {
            cumulative += p;
            if r <= cumulative {
                chosen_idx = i;
                break;
            }
        }

        selected.push(remaining_indices[chosen_idx]);
        remaining_indices.remove(chosen_idx);
        remaining_probs.remove(chosen_idx);
    }

    selected
}

fn lcg_next(state: u64) -> u64 {
    state.wrapping_mul(1103515245).wrapping_add(12345)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cool() {
        let mut s = ThermodynamicState::default();
        let initial = s.temperature;
        s.cool();
        assert!(s.temperature < initial);
    }

    #[test]
    fn test_reheat() {
        let mut s = ThermodynamicState::default();
        s.temperature = 0.1;
        s.reheat(1.0);
        assert!(s.temperature > 0.1);
    }

    #[test]
    fn test_adapt_discovery_dropping() {
        let mut s = ThermodynamicState::default();
        s.adapt(0.8, 0.0); // High discovery
        let temp_after_high = s.temperature;
        s.adapt(0.2, 0.0); // Low discovery → cool faster
        assert!(s.temperature < temp_after_high);
    }

    #[test]
    fn test_exploration_phase() {
        let mut s = ThermodynamicState::default();
        s.temperature = 0.9;
        assert_eq!(s.exploration_phase(), "hot");
        s.temperature = 0.5;
        assert_eq!(s.exploration_phase(), "warm");
        s.temperature = 0.1;
        assert_eq!(s.exploration_phase(), "cold");
    }

    #[test]
    fn test_boltzmann_probabilities() {
        let probs = boltzmann_probabilities(&[0.1, 0.2, 0.3], 1.0);
        let total: f64 = probs.iter().sum();
        assert!((total - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_boltzmann_select() {
        let selected = boltzmann_select(&[0.1, 0.2, 0.3, 0.4], 0.5, 2, 42);
        assert_eq!(selected.len(), 2);
        assert!(selected.iter().all(|&i| i < 4));
    }

    #[test]
    fn test_boltzmann_low_temp_favors_low_energy() {
        // At very low temperature, lowest energy should dominate
        let probs = boltzmann_probabilities(&[0.0, 1.0, 2.0], 0.01);
        assert!(probs[0] > probs[1]);
        assert!(probs[1] > probs[2]);
    }
}
