//! `WhiteMagic` v4 wm-governance — Dharma gate and karma ledger.
//!
//! Ethical governance for tool dispatch: evaluates actions against
//! Dharma principles and tracks karma debt via a SHA-256 hash chain
//! persisted to LMDB.

#![forbid(unsafe_code)]

pub mod acs;
pub mod dharma_gate;
pub mod economic_firewall;
pub mod escalation;
pub mod firebreak;
pub mod gratitude_ledger;
pub mod karma_ledger;
pub mod network_profile;
pub mod policy;
pub mod resource_rules;
pub mod write_audit;

pub use acs::{AcsAction, AcsCheckpoint, AcsComplianceReport, AcsExport, AcsRule};
pub use dharma_gate::{ActionVerdict, DharmaGate, Homeostasis};
pub use economic_firewall::{
    DharmaSignOff, ECONOMIC_TOOLS, EconomicFirewall, NoDharmaSignOff, NoRecipientTrust,
    RecipientTrustSource, SecurityEvent, TransactionPolicy, TransactionRequest, TransactionVerdict,
    VerdictReason, is_economic_tool,
};
pub use escalation::{EscalationQueue, ReviewItem, ReviewStatus};
pub use firebreak::{
    Firebreak, FirebreakOutcome, FirebreakStats, SCOPE_REGISTRY, ScopeRule, VetoClass, VetoFinding,
};
pub use gratitude_ledger::{
    Digest, GENESIS_GRATITUDE, GratitudeEntry, GratitudeLedger, GratitudeVerification,
    SupporterTier, tier_for,
};
pub use karma_ledger::{ChainVerificationResult, Guna, KarmaEntry, KarmaLedger, MerkleCheckpoint};
pub use network_profile::{
    AgentIdentity, AgentKeypair, NetworkStateProfile, ReputationEvent, ReputationRecord,
    WeightedVote, verify_signature,
};
pub use policy::{
    DharmaPolicy, OwaspAgentic, OwaspComplianceReport, PolicyCheckResult, PolicyEngine, PolicyRule,
    PolicyUpdateError,
};
pub use resource_rules::{BudgetUsage, ResourceRules, ResourceRulesConfig, ResourceVerdict};
pub use write_audit::{ActorIdentity, WriteAuditEntry, WriteAuditJournal, args_digest};
