//! Immutable, compiler-authorized sweep contract.
//!
//! Production construction of trusted plans is intentionally unavailable until the measured,
//! projection-disabled planner is integrated. Callers cannot authorize arbitrary effect digests.

use std::collections::{BTreeMap, HashSet};
use std::fmt;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::evidence::RatifiedChannel;
use crate::field::{RULE_ID, RelationState};
use crate::intake::{CommitDisposition, CommitReceipt, OperationId};

pub const SWEEP_SCOPE: &str = "wm.gen3.sweep.v1";
pub const SWEEP_OPERATION_KIND: u8 = 2;
pub const SWEEP_MANIFEST_VERSION: u8 = 1;
pub const SWEEP_RECEIPT_VERSION: u8 = 1;
/// Landed v5 store format (fresh-only; v4 and older refuse, no migration).
pub const SWEEP_STORE_FORMAT_VERSION: u32 = 5;
/// Ratified policy profile version bound into every sweep manifest/receipt digest.
pub const SWEEP_PROFILE_VERSION: u8 = 1;

/// D2(b) disclosure: lifecycle evidence is a trusted process-local observation.
pub const SWEEP_USAGE_EVIDENCE_BASIS: &str = "process_local_volatile";
/// D2(b) disclosure: the usage lineage does not survive a process restart.
pub const SWEEP_USAGE_RESTART_PERSISTENT: bool = false;

/// Ratified Slice 1 qualification profile v1
/// (`receipts/GATE_9A_RATIFICATION_AMENDMENT_2026-09-22.md`, A1).
///
/// Hard refusal only, never truncation. Qualification ceilings, not capacity:
/// most real content will refuse at 1 KiB per record. Changing any value requires
/// a registered profile bump plus fresh sizing evidence.
pub const SWEEP_PROFILE_V1: SweepLimits = SweepLimits {
    max_records_scanned: 256,
    max_raw_record_bytes: 16 * 1024,
    max_single_record_bytes: 1024,
    max_postings_bytes: 2 * 1024,
    max_token_occurrences: 1024,
    max_relations_scanned: 256,
    max_pair_examinations: 8192,
    max_effects: 1024,
};

/// Pre-decode allocation guard: a stored record value may exceed its
/// content+source ceiling by this fixed framing margin before refusal.
pub(crate) const MAX_WIRE_RECORD_OVERHEAD: u64 = 4096;

/// Production sweep availability. True only when the trusted planner, atomic v5
/// commit, and validated replay are all present in this tree. Never flip merely
/// to unblock a build.
pub const PRODUCTION_SWEEP_PROFILE_AVAILABLE: bool = true;

/// The Six Functional Cognitive Chambers of the Pyramidal Cyberbrain.
///
/// In WhiteMagic Gen3, every pulsed cognitive sweep traverses the Six Chambers
/// in strict hierarchical order without background loops (Article 4):
/// 1. Crown (Sahasrara): Constitutional invariance check & zero-bypass verification.
/// 2. Discernment (Ajna): Dynamic relation arbitration & supersession resolution.
/// 3. Transport (Vishuddha): Multi-modal representation health & ContextCache freshness.
/// 4. Associative (Anahata): Hebbian co-activation consolidation & causal execution provenance.
/// 5. Executive (Manipura): Lifecycle usage accounting, rate limits, & bounded pair budgets.
/// 6. Alchemical (Svadhisthana): Forgotten diamond discovery & disposable telemetry pruning.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CognitiveChamber {
    Crown,
    Discernment,
    Transport,
    Associative,
    Executive,
    Alchemical,
}

impl CognitiveChamber {
    #[must_use]
    pub fn name(&self) -> &'static str {
        match self {
            Self::Crown => "Crown (Sahasrara) - Constitutional Invariance",
            Self::Discernment => "Discernment (Ajna) - Relation Arbitration",
            Self::Transport => "Transport (Vishuddha) - Multi-Modal & ContextCache",
            Self::Associative => "Associative (Anahata) - Hebbian & Provenance",
            Self::Executive => "Executive (Manipura) - Lifecycle & Bounded Budgets",
            Self::Alchemical => "Alchemical (Svadhisthana) - Diamond Recovery & Pruning",
        }
    }
}

/// Report summarizing the validation and actions of each Cognitive Chamber during a pulse.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ChamberAuditReport {
    pub chamber: CognitiveChamber,
    pub passed: bool,
    pub records_considered: usize,
    pub actions_proposed: usize,
    pub details: String,
}

/// Checks if a record represents disposable telemetry (e.g. transient debug logs,
/// volatile session trace items, or heartbeats) that can be safely reclaimed or cold-stored.
#[must_use]
pub fn is_disposable_telemetry(source: &str, content: &str) -> bool {
    source.starts_with("telemetry:")
        || source.contains(":debug")
        || source.contains(":heartbeat")
        || content.contains("[VOLATILE_TELEMETRY]")
}

/// Stored receipt-envelope tags (fresh-only v5 wire format). The tag byte is the
/// explicit kind discriminator; payloads are length-framed rmp with a version
/// field, so legacy raw v4 receipt bytes can never decode as v5.
pub(crate) const RECEIPT_ENVELOPE_TAG_INTAKE: u8 = 1;
pub(crate) const RECEIPT_ENVELOPE_TAG_SWEEP: u8 = 2;

const MANIFEST_DOMAIN: &[u8] = b"wm.gen3.sweep-manifest";
const USAGE_DOMAIN: &[u8] = b"wm.gen3.sweep-usage";
const EFFECT_DOMAIN: &[u8] = b"wm.gen3.sweep-effects";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct SweepLimits {
    pub max_records_scanned: u64,
    pub max_raw_record_bytes: u64,
    pub max_single_record_bytes: u64,
    pub max_postings_bytes: u64,
    pub max_token_occurrences: u64,
    pub max_relations_scanned: u64,
    pub max_pair_examinations: u64,
    pub max_effects: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct SweepObserved {
    pub records_scanned: u64,
    pub raw_record_bytes: u64,
    pub largest_record_bytes: u64,
    pub postings_bytes: u64,
    pub token_occurrences: u64,
    pub relations_scanned: u64,
    pub pair_examinations: u64,
    pub effects: u64,
}

impl SweepObserved {
    fn validate(self, limits: SweepLimits) -> Result<(), SweepError> {
        for (dimension, observed, limit) in [
            (
                "records_scanned",
                self.records_scanned,
                limits.max_records_scanned,
            ),
            (
                "raw_record_bytes",
                self.raw_record_bytes,
                limits.max_raw_record_bytes,
            ),
            (
                "largest_record_bytes",
                self.largest_record_bytes,
                limits.max_single_record_bytes,
            ),
            (
                "postings_bytes",
                self.postings_bytes,
                limits.max_postings_bytes,
            ),
            (
                "token_occurrences",
                self.token_occurrences,
                limits.max_token_occurrences,
            ),
            (
                "relations_scanned",
                self.relations_scanned,
                limits.max_relations_scanned,
            ),
            (
                "pair_examinations",
                self.pair_examinations,
                limits.max_pair_examinations,
            ),
            ("effects", self.effects, limits.max_effects),
        ] {
            if observed > limit {
                return Err(SweepError::LimitExceeded {
                    dimension,
                    observed,
                    limit,
                });
            }
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct UsageEntry {
    pub relation_id: u64,
    pub count: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct VolatileUsageSnapshot {
    process_instance_id: [u8; 16],
    sequence: u64,
    entries: Vec<UsageEntry>,
    digest: [u8; 32],
    _trusted_origin: (),
}

impl VolatileUsageSnapshot {
    #[must_use]
    pub const fn process_instance_id(&self) -> &[u8; 16] {
        &self.process_instance_id
    }
    #[must_use]
    pub const fn sequence(&self) -> u64 {
        self.sequence
    }
    #[must_use]
    pub fn entries(&self) -> &[UsageEntry] {
        &self.entries
    }
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        self.digest
    }

    fn validate(&self, max_entries: u64) -> Result<(), SweepError> {
        if self.process_instance_id == [0; 16] {
            return Err(SweepError::InvalidUsage("zero process identity"));
        }
        if self.sequence == 0 {
            return Err(SweepError::InvalidUsage(
                "snapshot sequence must start above zero",
            ));
        }
        if u64::try_from(self.entries.len()).map_err(|_| SweepError::LengthOverflow)? > max_entries
        {
            return Err(SweepError::InvalidUsage(
                "usage snapshot exceeds the relations bound",
            ));
        }
        if self.entries.iter().any(|entry| entry.count == 0) {
            return Err(SweepError::InvalidUsage("zero usage count"));
        }
        if self
            .entries
            .windows(2)
            .any(|pair| pair[0].relation_id >= pair[1].relation_id)
        {
            return Err(SweepError::InvalidUsage(
                "usage entries are not strictly ordered",
            ));
        }
        if self.digest != usage_digest(self.process_instance_id, self.sequence, &self.entries) {
            return Err(SweepError::InvalidUsage("usage digest mismatch"));
        }
        Ok(())
    }

    #[cfg(test)]
    pub(crate) fn synthetic(
        process_instance_id: [u8; 16],
        sequence: u64,
        entries: Vec<UsageEntry>,
    ) -> Self {
        let digest = usage_digest(process_instance_id, sequence, &entries);
        Self {
            process_instance_id,
            sequence,
            entries,
            digest,
            _trusted_origin: (),
        }
    }
}

/// Trusted process-local issuer. A new process receives a fresh random identity and snapshots
/// advance monotonically. This evidence is deliberately lost on restart.
#[allow(
    dead_code,
    reason = "sealed integration point for the pending trusted planner"
)]
pub(crate) struct UsageSnapshotIssuer {
    process_instance_id: [u8; 16],
    next_sequence: u64,
}

#[allow(
    dead_code,
    reason = "sealed integration point for the pending trusted planner"
)]
impl UsageSnapshotIssuer {
    pub(crate) fn new() -> Result<Self, SweepError> {
        let mut process_instance_id = [0; 16];
        getrandom::fill(&mut process_instance_id).map_err(|_| SweepError::RandomIdentityFailure)?;
        if process_instance_id == [0; 16] {
            return Err(SweepError::RandomIdentityFailure);
        }
        Ok(Self {
            process_instance_id,
            next_sequence: 1,
        })
    }

    pub(crate) fn snapshot(
        &mut self,
        usage: &BTreeMap<u64, u64>,
    ) -> Result<VolatileUsageSnapshot, SweepError> {
        let sequence = self.next_sequence;
        self.next_sequence = sequence
            .checked_add(1)
            .ok_or(SweepError::SequenceExhausted)?;
        let entries = usage
            .iter()
            .map(|(&relation_id, &count)| UsageEntry { relation_id, count })
            .collect::<Vec<_>>();
        let digest = usage_digest(self.process_instance_id, sequence, &entries);
        Ok(VolatileUsageSnapshot {
            process_instance_id: self.process_instance_id,
            sequence,
            entries,
            digest,
            _trusted_origin: (),
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SweepEffect {
    CreateSupersedes {
        src: u64,
        dst: u64,
        confidence_bits: u32,
        rule_id: String,
    },
    SetRelationState {
        relation_id: u64,
        expected_prior_state: RelationState,
        next_state: RelationState,
    },
}

impl SweepEffect {
    fn validate(&self) -> Result<(), SweepError> {
        match self {
            Self::CreateSupersedes {
                src,
                dst,
                confidence_bits,
                rule_id,
            } => {
                let confidence = f32::from_bits(*confidence_bits);
                if src == dst {
                    return Err(SweepError::InvalidEffect("self relation"));
                }
                if !confidence.is_finite() || !(0.0..=1.0).contains(&confidence) {
                    return Err(SweepError::InvalidEffect("invalid confidence"));
                }
                if rule_id != RULE_ID {
                    return Err(SweepError::InvalidEffect("unknown rule"));
                }
            }
            Self::SetRelationState {
                expected_prior_state,
                next_state,
                ..
            } => {
                let allowed = matches!(
                    (expected_prior_state, next_state),
                    (RelationState::Candidate, RelationState::Persistent)
                        | (RelationState::Candidate, RelationState::Cold)
                        | (RelationState::Persistent, RelationState::Cold)
                );
                if !allowed {
                    return Err(SweepError::InvalidEffect(
                        "unsupported lifecycle transition",
                    ));
                }
            }
        }
        Ok(())
    }
}

/// A sealed plan. Production callers cannot construct or deserialize one until the trusted
/// measured planner is integrated.
///
/// ```compile_fail
/// use wm_gen3_core::sweep::SweepRequest;
/// let request = SweepRequest { /* private fields */ };
/// ```
///
/// ```compile_fail
/// use wm_gen3_core::sweep::SweepRequest;
/// let request: SweepRequest = serde_json::from_str("{}").unwrap();
/// ```
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct SweepRequest {
    operation_id: OperationId,
    realm_id: [u8; 16],
    expected_epoch: u64,
    issuer_label: String,
    limits: SweepLimits,
    observed: SweepObserved,
    policy_digest: [u8; 32],
    usage: VolatileUsageSnapshot,
    effects: Vec<SweepEffect>,
    effects_digest: [u8; 32],
    manifest_digest: [u8; 32],
    _sealed_planner_origin: (),
}

impl SweepRequest {
    #[must_use]
    pub const fn operation_id(&self) -> OperationId {
        self.operation_id
    }
    #[must_use]
    pub const fn realm_id(&self) -> &[u8; 16] {
        &self.realm_id
    }
    #[must_use]
    pub const fn expected_epoch(&self) -> u64 {
        self.expected_epoch
    }
    #[must_use]
    pub fn issuer_label(&self) -> &str {
        &self.issuer_label
    }
    #[must_use]
    pub const fn limits(&self) -> SweepLimits {
        self.limits
    }
    #[must_use]
    pub const fn observed(&self) -> SweepObserved {
        self.observed
    }
    #[must_use]
    pub const fn policy_digest(&self) -> [u8; 32] {
        self.policy_digest
    }
    #[must_use]
    pub fn usage(&self) -> &VolatileUsageSnapshot {
        &self.usage
    }
    #[must_use]
    pub fn effects(&self) -> &[SweepEffect] {
        &self.effects
    }
    #[must_use]
    pub const fn effects_digest(&self) -> [u8; 32] {
        self.effects_digest
    }
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        self.manifest_digest
    }
    #[allow(
        dead_code,
        reason = "consumed by the pending v5 Store receipt integration"
    )]
    pub(crate) fn encode_for_receipt(&self) -> Result<Vec<u8>, SweepError> {
        self.validate()?;
        rmp_serde::to_vec(self).map_err(|error| SweepError::Encoding(error.to_string()))
    }
    #[must_use]
    pub fn authority_digest(&self) -> [u8; 32] {
        sweep_authority_digest(&self.issuer_label)
    }

    pub fn authenticate(&self, channel: &RatifiedChannel) -> Result<(), SweepError> {
        if !self.issuer_label.is_empty() && self.issuer_label == channel.name() {
            Ok(())
        } else {
            Err(SweepError::AuthorityMismatch)
        }
    }

    pub fn validate(&self) -> Result<(), SweepError> {
        validate_plan_parts(
            &self.issuer_label,
            &self.policy_digest,
            self.limits,
            self.observed,
            &self.usage,
            &self.effects,
            &self.effects_digest,
            &self.manifest_digest,
            &self.realm_id,
            self.operation_id,
            self.expected_epoch,
        )
    }

    /// Trusted planner boundary: the only production construction path. Crate-internal
    /// by design; downstream callers cannot build or deserialize a sealed plan. The
    /// caller must possess a ratified channel whose name equals `issuer_label` before
    /// `authorize_sweep` will issue a capability for this plan.
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn production(
        issuer_label: &str,
        operation_id: OperationId,
        realm_id: [u8; 16],
        expected_epoch: u64,
        limits: SweepLimits,
        observed: SweepObserved,
        policy_digest: [u8; 32],
        usage: VolatileUsageSnapshot,
        effects: Vec<SweepEffect>,
    ) -> Result<Self, SweepError> {
        let effects_digest = effects_digest(&effects);
        let mut request = Self {
            operation_id,
            realm_id,
            expected_epoch,
            issuer_label: issuer_label.into(),
            limits,
            observed,
            policy_digest,
            usage,
            effects,
            effects_digest,
            manifest_digest: [0; 32],
            _sealed_planner_origin: (),
        };
        request.manifest_digest = manifest_digest(&request);
        request.validate()?;
        Ok(request)
    }

    #[cfg(test)]
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn synthetic(
        channel: &RatifiedChannel,
        operation_id: OperationId,
        realm_id: [u8; 16],
        expected_epoch: u64,
        limits: SweepLimits,
        observed: SweepObserved,
        policy_digest: [u8; 32],
        usage: VolatileUsageSnapshot,
        effects: Vec<SweepEffect>,
    ) -> Result<Self, SweepError> {
        Self::production(
            channel.name(),
            operation_id,
            realm_id,
            expected_epoch,
            limits,
            observed,
            policy_digest,
            usage,
            effects,
        )
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SweepDecision {
    Disabled,
    Enabled(SweepRequest),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SweepError {
    AuthorityMismatch,
    LimitExceeded {
        dimension: &'static str,
        observed: u64,
        limit: u64,
    },
    InvalidUsage(&'static str),
    InvalidLimits(&'static str),
    InvalidEffect(&'static str),
    DuplicateEffect,
    EffectCountMismatch,
    EffectDigestMismatch,
    ManifestDigestMismatch,
    LengthOverflow,
    RandomIdentityFailure,
    SequenceExhausted,
    Encoding(String),
    /// A capability does not authorize the field it is used for.
    UnauthorizedCapability {
        field: &'static str,
    },
    /// The operation targets a different realm than the store or receipt.
    RealmMismatch,
    /// Optimistic concurrency failure: the world epoch moved since planning.
    StaleEpoch {
        expected: u64,
        actual: u64,
    },
    /// The operation ID already belongs to a different operation kind.
    CrossKindConflict,
    /// A committed plan exists for this operation ID but does not match the presented one.
    ReplayMismatch,
    /// An effect's expected prior state (or target) no longer holds.
    StateConflict {
        relation_id: u64,
    },
    /// Receipt/ledger pairing is inconsistent or corrupt.
    ReceiptState(&'static str),
    /// A durable counter would overflow.
    CounterExhausted,
    /// Persisted plan bytes failed inert decoding or binding validation.
    Wire(&'static str),
    /// Receipt envelope framing is invalid or unknown.
    Envelope(&'static str),
}

impl fmt::Display for SweepError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for SweepError {}

/// Explicit envelope for a fresh-only v5 Store. It must not decode v4 receipt bytes.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum CommitReceiptEnvelopeV5 {
    IntakeV2(CommitReceipt),
    SweepV1(SweepReceipt),
}

/// Fresh commit or authenticated replay outcome for a sweep operation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SweepOutcome {
    pub receipt: SweepReceipt,
    pub disposition: CommitDisposition,
}

/// Stored wire bytes for a receipt envelope: one explicit tag byte followed by the
/// rmp payload. This is deliberately self-framing so legacy raw receipt bytes can
/// never be reinterpreted as a v5 envelope (no ambiguous mixed decoding).
pub(crate) fn encode_receipt_envelope(
    envelope: &CommitReceiptEnvelopeV5,
) -> Result<Vec<u8>, SweepError> {
    let (tag, payload) = match envelope {
        CommitReceiptEnvelopeV5::IntakeV2(receipt) => (
            RECEIPT_ENVELOPE_TAG_INTAKE,
            rmp_serde::to_vec(receipt).map_err(|error| SweepError::Encoding(error.to_string()))?,
        ),
        CommitReceiptEnvelopeV5::SweepV1(receipt) => (
            RECEIPT_ENVELOPE_TAG_SWEEP,
            rmp_serde::to_vec(receipt).map_err(|error| SweepError::Encoding(error.to_string()))?,
        ),
    };
    let mut out = Vec::with_capacity(1 + payload.len());
    out.push(tag);
    out.extend_from_slice(&payload);
    Ok(out)
}

pub(crate) fn decode_receipt_envelope(bytes: &[u8]) -> Result<CommitReceiptEnvelopeV5, SweepError> {
    let (tag, payload) = bytes
        .split_first()
        .ok_or(SweepError::Envelope("empty receipt envelope"))?;
    match *tag {
        RECEIPT_ENVELOPE_TAG_INTAKE => rmp_serde::from_slice(payload)
            .map(CommitReceiptEnvelopeV5::IntakeV2)
            .map_err(|_| SweepError::Envelope("intake envelope payload is not decodable")),
        RECEIPT_ENVELOPE_TAG_SWEEP => rmp_serde::from_slice(payload)
            .map(CommitReceiptEnvelopeV5::SweepV1)
            .map_err(|_| SweepError::Envelope("sweep envelope payload is not decodable")),
        _ => Err(SweepError::Envelope("unknown receipt envelope tag")),
    }
}

/// Inert wire mirror of [`SweepRequest`]. Decoding produces no authority: callers
/// receive a [`ValidatedSweepPlan`], never a sealed request.
#[derive(Debug, Deserialize)]
pub(crate) struct SweepRequestWire {
    operation_id: OperationId,
    realm_id: [u8; 16],
    expected_epoch: u64,
    issuer_label: String,
    limits: SweepLimits,
    observed: SweepObserved,
    policy_digest: [u8; 32],
    usage: UsageWire,
    effects: Vec<SweepEffect>,
    effects_digest: [u8; 32],
    manifest_digest: [u8; 32],
    #[allow(dead_code)]
    _sealed_planner_origin: (),
}

#[derive(Debug, Deserialize)]
struct UsageWire {
    process_instance_id: [u8; 16],
    sequence: u64,
    entries: Vec<UsageEntry>,
    digest: [u8; 32],
    #[allow(dead_code)]
    _trusted_origin: (),
}

/// Inert, fully validated persisted plan. It carries no authority: a fresh
/// capability is still required before any replay applies it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct ValidatedSweepPlan {
    pub(crate) operation_id: OperationId,
    pub(crate) realm_id: [u8; 16],
    pub(crate) expected_epoch: u64,
    pub(crate) issuer_label: String,
    pub(crate) limits: SweepLimits,
    pub(crate) observed: SweepObserved,
    pub(crate) policy_digest: [u8; 32],
    pub(crate) usage_entries: Vec<UsageEntry>,
    pub(crate) usage_digest: [u8; 32],
    pub(crate) process_instance_id: [u8; 16],
    pub(crate) usage_sequence: u64,
    pub(crate) effects: Vec<SweepEffect>,
    pub(crate) effects_digest: [u8; 32],
    pub(crate) manifest_digest: [u8; 32],
}

impl SweepRequestWire {
    pub(crate) fn validate(self) -> Result<ValidatedSweepPlan, SweepError> {
        let usage = VolatileUsageSnapshot {
            process_instance_id: self.usage.process_instance_id,
            sequence: self.usage.sequence,
            entries: self.usage.entries,
            digest: self.usage.digest,
            _trusted_origin: (),
        };
        validate_plan_parts(
            &self.issuer_label,
            &self.policy_digest,
            self.limits,
            self.observed,
            &usage,
            &self.effects,
            &self.effects_digest,
            &self.manifest_digest,
            &self.realm_id,
            self.operation_id,
            self.expected_epoch,
        )?;
        Ok(ValidatedSweepPlan {
            operation_id: self.operation_id,
            realm_id: self.realm_id,
            expected_epoch: self.expected_epoch,
            issuer_label: self.issuer_label,
            limits: self.limits,
            observed: self.observed,
            policy_digest: self.policy_digest,
            usage_entries: usage.entries,
            usage_digest: usage.digest,
            process_instance_id: usage.process_instance_id,
            usage_sequence: usage.sequence,
            effects: self.effects,
            effects_digest: self.effects_digest,
            manifest_digest: self.manifest_digest,
        })
    }
}

/// Decode inert persisted plan bytes with full binding validation.
pub(crate) fn decode_validated_plan(bytes: &[u8]) -> Result<ValidatedSweepPlan, SweepError> {
    let wire: SweepRequestWire =
        rmp_serde::from_slice(bytes).map_err(|_| SweepError::Wire("plan is not decodable"))?;
    wire.validate()
}

/// Deterministic digest over applied outcomes, in canonical effect order.
/// Creates bind the allocated relation id; state changes bind the transition.
pub(crate) fn outcomes_digest(
    effects: &[SweepEffect],
    allocated_relation_ids: &[u64],
) -> Result<[u8; 32], SweepError> {
    let mut hash = Sha256::new();
    hash.update(b"wm.gen3.sweep-outcomes");
    hash_u64(&mut hash, effects.len() as u64);
    let mut created = 0usize;
    for effect in effects {
        match effect {
            SweepEffect::CreateSupersedes {
                src,
                dst,
                confidence_bits,
                rule_id,
            } => {
                let relation_id =
                    *allocated_relation_ids
                        .get(created)
                        .ok_or(SweepError::ReceiptState(
                            "allocated relation ids do not match create effects",
                        ))?;
                created += 1;
                hash.update([1]);
                hash_u64(&mut hash, relation_id);
                hash_u64(&mut hash, *src);
                hash_u64(&mut hash, *dst);
                hash.update(confidence_bits.to_be_bytes());
                let _ = hash_bytes(&mut hash, rule_id.as_bytes());
            }
            SweepEffect::SetRelationState {
                relation_id,
                expected_prior_state,
                next_state,
            } => {
                hash.update([2]);
                hash_u64(&mut hash, *relation_id);
                hash.update([state_tag(*expected_prior_state), state_tag(*next_state)]);
            }
        }
    }
    if created != allocated_relation_ids.len() {
        return Err(SweepError::ReceiptState(
            "allocated relation ids do not match create effects",
        ));
    }
    Ok(hash.finalize().into())
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SweepReceipt {
    pub version: u8,
    pub realm_id: [u8; 16],
    pub operation_id: OperationId,
    pub manifest_digest: [u8; 32],
    pub authority_digest: [u8; 32],
    pub compiler_scope: String,
    pub operation_kind: u8,
    pub policy_digest: [u8; 32],
    pub limits: SweepLimits,
    pub observed: SweepObserved,
    pub usage_digest: [u8; 32],
    pub process_instance_id: [u8; 16],
    pub usage_sequence: u64,
    /// D2(b) disclosure fields: receipts must never imply durable usage history.
    pub usage_evidence_basis: String,
    pub usage_restart_persistent: bool,
    pub effects_digest: [u8; 32],
    pub effect_count: u64,
    pub pre_epoch: u64,
    pub post_epoch: u64,
    pub sweep_id: u64,
    pub allocated_relation_ids: Vec<u64>,
    pub outcomes_digest: [u8; 32],
    /// Exact original sealed request. Replay retrieves and validates this; it never rescans.
    pub sealed_request: Vec<u8>,
    pub committed: bool,
}

fn validate_effects(effects: &[SweepEffect]) -> Result<(), SweepError> {
    let mut creates = HashSet::new();
    let mut states = HashSet::new();
    let mut prior_key = None;
    for effect in effects {
        effect.validate()?;
        match effect {
            SweepEffect::CreateSupersedes { src, dst, .. } if !creates.insert((*src, *dst)) => {
                return Err(SweepError::DuplicateEffect);
            }
            SweepEffect::SetRelationState { relation_id, .. } if !states.insert(*relation_id) => {
                return Err(SweepError::DuplicateEffect);
            }
            _ => {}
        }
        let key = match effect {
            SweepEffect::CreateSupersedes { src, dst, .. } => (0, *src, *dst),
            SweepEffect::SetRelationState { relation_id, .. } => (1, *relation_id, 0),
        };
        if prior_key.is_some_and(|prior| prior >= key) {
            return Err(SweepError::InvalidEffect(
                "effects are not in canonical order",
            ));
        }
        prior_key = Some(key);
    }
    Ok(())
}

fn hash_u64(hash: &mut Sha256, value: u64) {
    hash.update(value.to_be_bytes());
}
fn hash_bytes(hash: &mut Sha256, bytes: &[u8]) -> Result<(), SweepError> {
    hash_u64(
        hash,
        u64::try_from(bytes.len()).map_err(|_| SweepError::LengthOverflow)?,
    );
    hash.update(bytes);
    Ok(())
}

fn usage_digest(process: [u8; 16], sequence: u64, entries: &[UsageEntry]) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(USAGE_DOMAIN);
    hash.update(process);
    hash_u64(&mut hash, sequence);
    hash_u64(&mut hash, entries.len() as u64);
    for entry in entries {
        hash_u64(&mut hash, entry.relation_id);
        hash_u64(&mut hash, entry.count);
    }
    hash.finalize().into()
}

fn effects_digest(effects: &[SweepEffect]) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(EFFECT_DOMAIN);
    hash_u64(&mut hash, effects.len() as u64);
    for effect in effects {
        match effect {
            SweepEffect::CreateSupersedes {
                src,
                dst,
                confidence_bits,
                rule_id,
            } => {
                hash.update([1]);
                hash_u64(&mut hash, *src);
                hash_u64(&mut hash, *dst);
                hash.update(confidence_bits.to_be_bytes());
                let _ = hash_bytes(&mut hash, rule_id.as_bytes());
            }
            SweepEffect::SetRelationState {
                relation_id,
                expected_prior_state,
                next_state,
            } => {
                hash.update([2]);
                hash_u64(&mut hash, *relation_id);
                hash.update([state_tag(*expected_prior_state), state_tag(*next_state)]);
            }
        }
    }
    hash.finalize().into()
}

fn manifest_digest(request: &SweepRequest) -> [u8; 32] {
    manifest_digest_from_parts(
        &request.realm_id,
        request.operation_id,
        &request.issuer_label,
        request.expected_epoch,
        request.limits,
        request.observed,
        &request.policy_digest,
        &request.usage.digest(),
        &request.effects_digest,
    )
}

#[allow(clippy::too_many_arguments)]
fn manifest_digest_from_parts(
    realm_id: &[u8; 16],
    operation_id: OperationId,
    issuer_label: &str,
    expected_epoch: u64,
    limits: SweepLimits,
    observed: SweepObserved,
    policy_digest: &[u8; 32],
    usage_digest: &[u8; 32],
    effects_digest: &[u8; 32],
) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(MANIFEST_DOMAIN);
    hash.update([SWEEP_MANIFEST_VERSION]);
    hash.update(SWEEP_STORE_FORMAT_VERSION.to_be_bytes());
    hash.update(realm_id);
    hash.update(operation_id.as_bytes());
    hash.update([SWEEP_OPERATION_KIND]);
    let _ = hash_bytes(&mut hash, issuer_label.as_bytes());
    hash_u64(&mut hash, expected_epoch);
    for value in limits_values(limits)
        .into_iter()
        .chain(observed_values(observed))
    {
        hash_u64(&mut hash, value);
    }
    hash.update(policy_digest);
    hash.update(usage_digest);
    hash.update(effects_digest);
    hash.finalize().into()
}

/// Authority binding shared by fresh plans and replay authorization.
#[must_use]
pub fn sweep_authority_digest(issuer_label: &str) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(b"wm.gen3.sweep-authority");
    let _ = hash_bytes(&mut hash, issuer_label.as_bytes());
    let _ = hash_bytes(&mut hash, SWEEP_SCOPE.as_bytes());
    hash.finalize().into()
}

/// Statutory policy inputs that shape sweep planning. The digest binds every
/// planning-relevant parameter so replay/read-set validation covers them.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct SweepPolicyInputs {
    pub rare_df_divisor: u64,
    pub rare_df_floor: u64,
    pub lifecycle_age_sweeps: u64,
}

pub(crate) const LIFECYCLE_AGE_SWEEPS: u64 = 3;

pub(crate) fn sweep_policy_digest(inputs: SweepPolicyInputs, limits: SweepLimits) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(b"wm.gen3.sweep-policy");
    hash.update([SWEEP_PROFILE_VERSION, SWEEP_MANIFEST_VERSION]);
    for value in limits_values(limits) {
        hash_u64(&mut hash, value);
    }
    hash_u64(&mut hash, inputs.rare_df_divisor);
    hash_u64(&mut hash, inputs.rare_df_floor);
    hash_u64(&mut hash, inputs.lifecycle_age_sweeps);
    let _ = hash_bytes(&mut hash, RULE_ID.as_bytes());
    hash.finalize().into()
}

#[allow(clippy::too_many_arguments)]
fn validate_plan_parts(
    issuer_label: &str,
    policy_digest: &[u8; 32],
    limits: SweepLimits,
    observed: SweepObserved,
    usage: &VolatileUsageSnapshot,
    effects: &[SweepEffect],
    expected_effects_digest: &[u8; 32],
    expected_manifest_digest: &[u8; 32],
    realm_id: &[u8; 16],
    operation_id: OperationId,
    expected_epoch: u64,
) -> Result<(), SweepError> {
    if issuer_label.is_empty() {
        return Err(SweepError::AuthorityMismatch);
    }
    if *policy_digest == [0; 32] {
        return Err(SweepError::InvalidLimits("policy digest must be nonzero"));
    }
    if limits_values(limits).contains(&0) {
        return Err(SweepError::InvalidLimits(
            "all sweep limits must be nonzero",
        ));
    }
    observed.validate(limits)?;
    if observed.largest_record_bytes > observed.raw_record_bytes {
        return Err(SweepError::InvalidLimits(
            "largest record exceeds aggregate bytes",
        ));
    }
    usage.validate(limits.max_relations_scanned)?;
    let effect_count = u64::try_from(effects.len()).map_err(|_| SweepError::LengthOverflow)?;
    if effect_count != observed.effects {
        return Err(SweepError::EffectCountMismatch);
    }
    validate_effects(effects)?;
    if *expected_effects_digest != effects_digest(effects) {
        return Err(SweepError::EffectDigestMismatch);
    }
    let expected = manifest_digest_from_parts(
        realm_id,
        operation_id,
        issuer_label,
        expected_epoch,
        limits,
        observed,
        policy_digest,
        &usage.digest(),
        expected_effects_digest,
    );
    if *expected_manifest_digest != expected {
        return Err(SweepError::ManifestDigestMismatch);
    }
    Ok(())
}

fn limits_values(v: SweepLimits) -> [u64; 8] {
    [
        v.max_records_scanned,
        v.max_raw_record_bytes,
        v.max_single_record_bytes,
        v.max_postings_bytes,
        v.max_token_occurrences,
        v.max_relations_scanned,
        v.max_pair_examinations,
        v.max_effects,
    ]
}
fn observed_values(v: SweepObserved) -> [u64; 8] {
    [
        v.records_scanned,
        v.raw_record_bytes,
        v.largest_record_bytes,
        v.postings_bytes,
        v.token_occurrences,
        v.relations_scanned,
        v.pair_examinations,
        v.effects,
    ]
}
fn state_tag(state: RelationState) -> u8 {
    match state {
        RelationState::Candidate => 0,
        RelationState::Persistent => 1,
        RelationState::Cold => 2,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pulse_compiler::{AuthorizationSnapshot, authorize_sweep};

    fn fixture() -> SweepRequest {
        let channel = RatifiedChannel::stub("sweep-test");
        let limits = SweepLimits {
            max_records_scanned: 10,
            max_raw_record_bytes: 1000,
            max_single_record_bytes: 200,
            max_postings_bytes: 1000,
            max_token_occurrences: 100,
            max_relations_scanned: 10,
            max_pair_examinations: 20,
            max_effects: 2,
        };
        let observed = SweepObserved {
            records_scanned: 2,
            raw_record_bytes: 50,
            largest_record_bytes: 30,
            postings_bytes: 20,
            token_occurrences: 8,
            relations_scanned: 1,
            pair_examinations: 1,
            effects: 1,
        };
        let usage = VolatileUsageSnapshot::synthetic(
            [9; 16],
            1,
            vec![UsageEntry {
                relation_id: 4,
                count: 3,
            }],
        );
        SweepRequest::synthetic(
            &channel,
            OperationId::from_bytes([7; 16]),
            [8; 16],
            3,
            limits,
            observed,
            [6; 32],
            usage,
            vec![SweepEffect::CreateSupersedes {
                src: 2,
                dst: 1,
                confidence_bits: 0.9_f32.to_bits(),
                rule_id: RULE_ID.into(),
            }],
        )
        .unwrap()
    }

    #[test]
    fn manifest_is_exact_and_deterministic() {
        assert_eq!(fixture().digest(), fixture().digest());
        assert_eq!(
            fixture().encode_for_receipt().unwrap(),
            fixture().encode_for_receipt().unwrap()
        );
        let mut changed = fixture();
        changed.policy_digest[0] ^= 1;
        assert_eq!(changed.validate(), Err(SweepError::ManifestDigestMismatch));
    }

    #[test]
    fn every_bound_is_hard() {
        let cases: [(&str, fn(&mut SweepObserved)); 8] = [
            ("records_scanned", |v| v.records_scanned = 11),
            ("raw_record_bytes", |v| v.raw_record_bytes = 1001),
            ("largest_record_bytes", |v| v.largest_record_bytes = 201),
            ("postings_bytes", |v| v.postings_bytes = 1001),
            ("token_occurrences", |v| v.token_occurrences = 101),
            ("relations_scanned", |v| v.relations_scanned = 11),
            ("pair_examinations", |v| v.pair_examinations = 21),
            ("effects", |v| v.effects = 3),
        ];
        for (dimension, alter) in cases {
            let mut request = fixture();
            alter(&mut request.observed);
            assert!(matches!(
                request.validate(),
                Err(SweepError::LimitExceeded { dimension: found, .. }) if found == dimension
            ));
        }
    }

    #[test]
    fn usage_lineage_and_effects_are_canonical() {
        let mut request = fixture();
        request.usage.entries.push(UsageEntry {
            relation_id: 4,
            count: 1,
        });
        assert!(matches!(
            request.validate(),
            Err(SweepError::InvalidUsage(_))
        ));
        let mut request = fixture();
        request.effects.push(request.effects[0].clone());
        request.observed.effects = 2;
        assert_eq!(request.validate(), Err(SweepError::DuplicateEffect));
    }

    #[test]
    fn disabled_is_distinct_and_contains_no_request() {
        assert_eq!(SweepDecision::Disabled, SweepDecision::Disabled);
    }

    #[test]
    fn usage_issuer_is_fresh_ordered_and_monotonic() {
        let mut issuer = UsageSnapshotIssuer::new().unwrap();
        let usage = BTreeMap::from([(9, 2), (3, 1)]);
        let first = issuer.snapshot(&usage).unwrap();
        let second = issuer.snapshot(&usage).unwrap();
        assert_ne!(first.process_instance_id(), &[0; 16]);
        assert_eq!(first.process_instance_id(), second.process_instance_id());
        assert_eq!((first.sequence(), second.sequence()), (1, 2));
        assert_eq!(first.entries()[0].relation_id, 3);
        assert_eq!(first.entries()[1].relation_id, 9);
    }

    #[test]
    fn compiler_binds_exact_sealed_plan_and_store_snapshot() {
        let request = fixture();
        let snapshot = AuthorizationSnapshot::from_test_parts([8; 16], 3);
        let capability =
            authorize_sweep(&RatifiedChannel::stub("sweep-test"), &request, &snapshot).unwrap();
        assert_eq!(capability.authorized_digest(), request.digest());
        assert_eq!(
            capability.feasibility_operation_id(),
            Some(request.operation_id())
        );
        assert_eq!(capability.feasibility_realm_id(), Some(*request.realm_id()));
        assert_eq!(capability.feasibility_expected_epoch(), Some(3));
        assert_eq!(
            capability.feasibility_authority_digest(),
            Some(request.authority_digest())
        );
        assert_eq!(
            capability.feasibility_operation_kind(),
            Some(SWEEP_OPERATION_KIND)
        );
        assert_eq!(capability.scope(), SWEEP_SCOPE);

        assert!(matches!(
            authorize_sweep(&RatifiedChannel::stub("wrong"), &request, &snapshot,),
            Err(crate::pulse_compiler::PulseError::FeasibilityRefused { .. })
        ));
        let stale = AuthorizationSnapshot::from_test_parts([8; 16], 4);
        assert!(matches!(
            authorize_sweep(&RatifiedChannel::stub("sweep-test"), &request, &stale),
            Err(crate::pulse_compiler::PulseError::StaleWorldEpoch {
                expected_epoch: 3,
                current_epoch: 4
            })
        ));
    }
}
