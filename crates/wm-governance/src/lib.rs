//! `WhiteMagic` v4 wm-governance — Dharma gate and karma ledger.
//!
//! Ethical governance for tool dispatch: evaluates actions against
//! Dharma principles and tracks karma debt via a SHA-256 hash chain
//! persisted to LMDB.

#![forbid(unsafe_code)]

pub mod acs;
pub mod dharma_gate;
pub mod karma_ledger;
pub mod policy;
pub mod resource_rules;

pub use acs::{AcsAction, AcsCheckpoint, AcsComplianceReport, AcsExport, AcsRule};
pub use dharma_gate::{ActionVerdict, DharmaGate, Homeostasis};
pub use karma_ledger::{ChainVerificationResult, Guna, KarmaEntry, KarmaLedger, MerkleCheckpoint};
pub use policy::{
    DharmaPolicy, OwaspAgentic, OwaspComplianceReport, PolicyCheckResult, PolicyEngine, PolicyRule,
    PolicyUpdateError,
};
pub use resource_rules::{BudgetUsage, ResourceRules, ResourceRulesConfig, ResourceVerdict};
