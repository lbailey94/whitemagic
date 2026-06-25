//! WhiteMagic Evolution Acceleration (Rust)
//!
//! Accelerates the recursive improvement loop's hottest modules:
//! - `info_theory`: Shannon entropy, KL divergence, information gain
//! - `thermodynamic`: Boltzmann selection, temperature scheduling
//! - `hrr_composition`: HRR bind/unbind/superpose for hypothesis interaction

pub mod counterfactual;
pub mod hrr_composition;
pub mod info_theory;
pub mod mc_integration;
pub mod thermodynamic;

pub use info_theory::{shannon_entropy, kl_divergence, information_gain, system_uncertainty};
pub use thermodynamic::{boltzmann_probabilities, boltzmann_select, ThermodynamicState};
