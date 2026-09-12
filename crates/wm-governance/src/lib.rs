//! `WhiteMagic` v4 wm-governance — Dharma gate and karma ledger.
//!
//! Ethical governance for tool dispatch: evaluates actions against
//! Dharma principles and tracks karma debt via a SHA-256 hash chain
//! persisted to LMDB.

#![forbid(unsafe_code)]

pub mod acs;
pub mod canary_tokens;
pub mod capabilities;
pub mod decoy_shell;
pub mod deobfuscator;
pub mod dharma_gate;
pub mod economic_firewall;
pub mod engagement_tokens;
pub mod escalation;
pub mod firebreak;
pub mod gratitude_ledger;
pub mod hermit_crab;
pub mod karma_ledger;
pub mod model_signing;
pub mod network_profile;
pub mod pattern_immunity;
pub mod policy;
pub mod resource_rules;
pub mod security_events;
pub mod trust_stack;
pub mod write_audit;

pub use acs::{AcsAction, AcsCheckpoint, AcsComplianceReport, AcsExport, AcsRule};
pub use canary_tokens::{
    CanaryHit, CanaryId, CanaryRegistry, CanaryStats, CanaryStatus, CanaryToken, CanaryType,
    DECOY_TAG, aws_key_id_checksum_valid, fake_api_key, fake_aws_key_id, fake_credential,
    fake_memory_entry, fake_path, fake_private_key_block,
};
pub use capabilities::{
    Capability, CapabilityError, CapabilityGrant, CapabilitySet,
    assert_engagement_token_capabilities, capabilities_for_engagement,
};
pub use decoy_shell::{DecoyEnvironment, InteractionEntry, InteractionLog, NOTHING_REAL_MARKER};
pub use deobfuscator::{
    DeobfuscationError, DeobfuscationLayer, LayerFinding, ScanReport, decode_layers, scan,
};
pub use dharma_gate::{ActionVerdict, DharmaGate, Homeostasis};
pub use economic_firewall::{
    DharmaSignOff, ECONOMIC_TOOLS, EconomicFirewall, NoDharmaSignOff, NoRecipientTrust,
    RecipientTrustSource, SecurityEvent, TransactionPolicy, TransactionRequest, TransactionVerdict,
    VerdictReason, is_economic_tool,
};
pub use engagement_tokens::{
    EngagementIssuer, EngagementScope, EngagementToken, EngagementTokenError, TokenVerdict,
};
pub use escalation::{EscalationQueue, ReviewItem, ReviewStatus};
pub use firebreak::{
    Firebreak, FirebreakOutcome, FirebreakStats, SCOPE_REGISTRY, ScopeRule, VetoClass, VetoFinding,
};
pub use gratitude_ledger::{
    Digest, GENESIS_GRATITUDE, GratitudeEntry, GratitudeLedger, GratitudeVerification,
    SupporterTier, tier_for,
};
pub use hermit_crab::{
    AccessVerdict, HermitError, HermitProtection, HermitState, MediationTicket, MemoryOperation,
    ThreatSignals, TransitionRecord,
};
pub use karma_ledger::{ChainVerificationResult, Guna, KarmaEntry, KarmaLedger, MerkleCheckpoint};
pub use model_signing::{
    ModelSignature, ModelSigner, ModelVerdict, verify_model, verify_model_hash,
};
pub use network_profile::{
    AgentIdentity, AgentKeypair, NetworkStateProfile, ReputationEvent, ReputationRecord,
    WeightedVote, verify_signature,
};
pub use pattern_immunity::{PATTERN_THRESHOLD, PatternImmunity, ThreatPattern};
pub use policy::{
    DharmaPolicy, OwaspAgentic, OwaspComplianceReport, PolicyCheckResult, PolicyEngine, PolicyRule,
    PolicyUpdateError,
};
pub use resource_rules::{BudgetUsage, ResourceRules, ResourceRulesConfig, ResourceVerdict};
pub use security_events::{
    BusStats, RING_CAPACITY, SecurityEvent as BusSecurityEvent, SecurityEventBus,
    SecurityEventType, Severity,
};
pub use trust_stack::TrustStack;
pub use write_audit::{ActorIdentity, WriteAuditEntry, WriteAuditJournal, args_digest};
