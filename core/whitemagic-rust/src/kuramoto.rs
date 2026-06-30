//! Kuramoto Model — Coupled Dream Cycle Oscillators (Phase 3c)
//!
//! The Dream Cycle has 12 phases that should operate in coordinated rhythms.
//! The Kuramoto model describes synchronization of coupled oscillators:
//!
//!   dθ_i/dt = ω_i + (K/N) Σ_j sin(θ_j - θ_i)
//!
//! Where:
//! - θ_i is the phase of oscillator i
//! - ω_i is its natural frequency
//! - K is the coupling strength
//! - N is the number of oscillators
//!
//! When K > K_c (critical coupling), oscillators synchronize.
//! This models how dream phases entrain to each other over cycles.

use std::f64::consts::TAU;

/// Dream cycle phases (12, matching DreamPhase enum in Python).
pub const N_PHASES: usize = 12;

/// Kuramoto model state: phases and natural frequencies for N oscillators.
#[derive(Debug, Clone)]
pub struct KuramotoModel {
    /// Current phase of each oscillator (radians, [0, 2π))
    pub phases: Vec<f64>,
    /// Natural frequency of each oscillator (rad/s)
    pub frequencies: Vec<f64>,
    /// Coupling strength K
    pub coupling: f64,
    /// Number of oscillators
    pub n: usize,
}

/// Order parameter result: measures synchronization level.
#[derive(Debug, Clone, Copy)]
pub struct OrderParameter {
    /// |r| ∈ [0, 1]: 0 = incoherent, 1 = fully synchronized
    pub coherence: f64,
    /// ψ: mean phase angle
    pub mean_phase: f64,
}

impl KuramotoModel {
    /// Create a new Kuramoto model with N oscillators.
    /// Frequencies are set to the dream phase base frequencies.
    pub fn new(n: usize, coupling: f64) -> Self {
        let frequencies = dream_phase_frequencies(n);
        let phases: Vec<f64> = (0..n)
            .map(|i| (i as f64 / n as f64) * TAU)
            .collect();
        Self { phases, frequencies, coupling, n }
    }

    /// Create with custom frequencies.
    pub fn with_frequencies(frequencies: Vec<f64>, coupling: f64) -> Self {
        let n = frequencies.len();
        let phases: Vec<f64> = (0..n)
            .map(|i| (i as f64 / n as f64) * TAU)
            .collect();
        Self { phases, frequencies, coupling, n }
    }

    /// Step the model forward by dt seconds using Euler integration.
    pub fn step(&mut self, dt: f64) {
        let n = self.n;
        let k = self.coupling;
        let mut new_phases = vec![0.0; n];

        for i in 0..n {
            let mut coupling_sum = 0.0;
            for j in 0..n {
                if i != j {
                    coupling_sum += (self.phases[j] - self.phases[i]).sin();
                }
            }
            let dtheta = self.frequencies[i] + (k / n as f64) * coupling_sum;
            new_phases[i] = (self.phases[i] + dtheta * dt).rem_euclid(TAU);
        }

        self.phases = new_phases;
    }

    /// Run for a given duration, returning the final order parameter.
    pub fn run(&mut self, dt: f64, steps: usize) -> OrderParameter {
        for _ in 0..steps {
            self.step(dt);
        }
        self.order_parameter()
    }

    /// Compute the Kuramoto order parameter (coherence r and mean phase ψ).
    pub fn order_parameter(&self) -> OrderParameter {
        let n = self.n as f64;
        let sum_cos: f64 = self.phases.iter().map(|&p| p.cos()).sum();
        let sum_sin: f64 = self.phases.iter().map(|&p| p.sin()).sum();
        let r = ((sum_cos / n).powi(2) + (sum_sin / n).powi(2)).sqrt();
        let psi = sum_sin.atan2(sum_cos);
        OrderParameter { coherence: r, mean_phase: psi }
    }

    /// Get the current phase of a specific oscillator.
    pub fn phase(&self, i: usize) -> f64 {
        self.phases[i]
    }

    /// Check if the system is synchronized (coherence > threshold).
    pub fn is_synchronized(&self, threshold: f64) -> bool {
        self.order_parameter().coherence > threshold
    }
}

/// Default frequencies for the 12 dream phases.
/// Each phase has a characteristic rhythm based on its function:
/// - Triage/decay: fast (high frequency, urgent)
/// - Consolidation/serendipity: medium
/// - Governance/narrative: slow (deliberate)
/// - Oracle/harmonize: very slow (deep)
fn dream_phase_frequencies(n: usize) -> Vec<f64> {
    let base = [
        1.2,  // 0: Triage — fast, urgent
        0.8,  // 1: Consolidation — medium
        1.0,  // 2: Serendipity — medium-fast
        0.5,  // 3: Governance — slow, deliberate
        0.6,  // 4: Narrative — slow-medium
        1.1,  // 5: Kaizen — fast, iterative
        0.3,  // 6: Oracle — very slow, deep
        1.5,  // 7: Decay — fast, cleanup
        0.9,  // 8: Constellation — medium
        0.7,  // 9: Prediction — medium-slow
        1.0,  // 10: Enrichment — medium
        0.4,  // 11: Harmonize — slow, settling
    ];
    (0..n).map(|i| base[i % 12]).collect()
}

/// Critical coupling strength K_c for synchronization.
/// For uniform frequencies with spread Δω, K_c ≈ 2Δω/π.
pub fn critical_coupling(frequencies: &[f64]) -> f64 {
    let n = frequencies.len() as f64;
    let mean = frequencies.iter().sum::<f64>() / n;
    let spread: f64 = frequencies.iter().map(|&f| (f - mean).abs()).sum::<f64>() / n;
    2.0 * spread / std::f64::consts::PI
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kuramoto_creation() {
        let model = KuramotoModel::new(12, 1.0);
        assert_eq!(model.n, 12);
        assert_eq!(model.phases.len(), 12);
        assert_eq!(model.frequencies.len(), 12);
        assert_eq!(model.coupling, 1.0);
    }

    #[test]
    fn test_phases_in_range() {
        let model = KuramotoModel::new(12, 1.0);
        for &p in &model.phases {
            assert!(p >= 0.0 && p < TAU, "Phase out of range: {}", p);
        }
    }

    #[test]
    fn test_step_preserves_count() {
        let mut model = KuramotoModel::new(12, 1.0);
        model.step(0.1);
        assert_eq!(model.phases.len(), 12);
    }

    #[test]
    fn test_step_phases_in_range() {
        let mut model = KuramotoModel::new(12, 1.0);
        for _ in 0..100 {
            model.step(0.1);
            for &p in &model.phases {
                assert!(p >= 0.0 && p < TAU, "Phase out of range after step: {}", p);
            }
        }
    }

    #[test]
    fn test_order_parameter_incoherent() {
        // With zero coupling and different frequencies, should be incoherent
        let model = KuramotoModel::new(12, 0.0);
        let op = model.order_parameter();
        // Initial phases are evenly spaced → coherence should be near 0
        assert!(op.coherence < 0.1, "Expected incoherent, got {}", op.coherence);
    }

    #[test]
    fn test_order_parameter_synchronized() {
        // All same phase → coherence = 1
        let model = KuramotoModel::with_frequencies(vec![1.0; 12], 10.0);
        let mut sync_model = model;
        sync_model.phases = vec![0.5; 12];
        let op = sync_model.order_parameter();
        assert!(op.coherence > 0.99, "Expected synchronized, got {}", op.coherence);
    }

    #[test]
    fn test_high_coupling_synchronizes() {
        let mut model = KuramotoModel::new(12, 5.0);
        // Run for many steps
        let op = model.run(0.1, 1000);
        assert!(op.coherence > 0.5, "High coupling should synchronize, got coherence {}", op.coherence);
    }

    #[test]
    fn test_zero_coupling_stays_incoherent() {
        let mut model = KuramotoModel::new(12, 0.0);
        let op = model.run(0.1, 1000);
        assert!(op.coherence < 0.5, "Zero coupling should stay mostly incoherent, got {}", op.coherence);
    }

    #[test]
    fn test_critical_coupling_positive() {
        let freqs = dream_phase_frequencies(12);
        let kc = critical_coupling(&freqs);
        assert!(kc > 0.0, "Critical coupling should be positive, got {}", kc);
    }

    #[test]
    fn test_is_synchronized() {
        let mut model = KuramotoModel::with_frequencies(vec![1.0; 6], 10.0);
        model.phases = vec![1.0; 6];
        assert!(model.is_synchronized(0.9));
        assert!(model.is_synchronized(0.99)); // all same phase → coherence = 1.0
    }

    #[test]
    fn test_dream_phase_frequencies_count() {
        let freqs = dream_phase_frequencies(12);
        assert_eq!(freqs.len(), 12);
        // Triage should be faster than Oracle
        assert!(freqs[0] > freqs[6]);
    }

    #[test]
    fn test_custom_frequencies() {
        let model = KuramotoModel::with_frequencies(vec![0.5, 1.0, 1.5], 2.0);
        assert_eq!(model.n, 3);
        assert_eq!(model.frequencies, vec![0.5, 1.0, 1.5]);
    }

    #[test]
    fn test_run_returns_order_parameter() {
        let mut model = KuramotoModel::new(12, 1.0);
        let op = model.run(0.1, 100);
        assert!(op.coherence >= 0.0 && op.coherence <= 1.0);
        assert!(op.mean_phase >= -std::f64::consts::PI && op.mean_phase <= std::f64::consts::PI);
    }
}
