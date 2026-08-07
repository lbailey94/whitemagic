//! wm-simulation — Monte Carlo simulation, counterfactual estimation, and forecasting.
//!
//! **N21**: Ports v2's `wm-evolution` MC suite capabilities for v4:
//!
//! - **Monte Carlo simulation** — Bayesian MC, Quasi-MC, sensitivity analysis
//! - **Counterfactual estimation** — synthetic control projection for causal impact
//! - **Forecasting** — time series forecasting with confidence intervals
//! - **Information-theoretic measures** — entropy, mutual information
//!
//! This enables the SelfModel to forecast outcomes, the Dream cycle to
//! simulate counterfactuals, and the Homeostatic loop to simulate action
//! consequences before executing them.

#![forbid(unsafe_code)]

pub mod counterfactual;
pub mod forecasting;
pub mod monte_carlo;
pub mod sensitivity;

pub use counterfactual::{CounterfactualEstimator, CounterfactualResult};
pub use forecasting::{ForecastMethod, ForecastResult, Forecaster};
pub use monte_carlo::{Distribution, McConfig, McResult, MonteCarloSimulator};
pub use sensitivity::{SensitivityAnalyzer, SensitivityIndex, SensitivityResult};
