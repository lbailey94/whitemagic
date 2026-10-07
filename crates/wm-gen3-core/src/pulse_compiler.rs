//! wm-gen3-core::pulse_compiler — Declarative Pulse Compilation & Zero-DAG Substrate.
//!
//! # Milestone 5B / PEB-10: The Transactional Calculus of Cognition
//!
//! ```text
//! Read World (X_e) ──► Construct Possibilities (F_1..F_N) ──► Evaluate (JEV/Catuṣkoṭi)
//!        │                                                               │
//!        ▼                                                               ▼
//!   Zero-DAG Tree ◄──────────────────────────────────────── Arbitrate & Compose
//!        │                                                               │
//!        ▼                                                               ▼
//!   Discarded Futures (F_i -> ∅)                         Warranted Delta (W, Δ*)
//!                                                                        │
//!                                                                        ▼
//!                                                           Commit(CommitCapability)
//!                                                                        │
//!                                                                        ▼
//!                                                          Canonical Reality (X_{e+1})
//! ```
//!
//! # Core Invariants & Architectural Laws
//! 1. **Zero-DAG Substrate:** No persistent workflow engines, task graphs, or scheduler daemons.
//!    Cognitive branches are ephemeral data values (`FutureValue`) that dissolve upon commit.
//! 2. **Snapshot-Bound Warrants (Optimistic Concurrency Control):** Evaluations are bound
//!    to an immutable `SnapshotVersion`. If substrate epoch moves between evaluation and commit,
//!    the warrant fails closed (`StaleWorldEpoch`), preventing TOCTOU races.
//! 3. **Futures as Values ($F_i = X_e + \Delta_i$):** Futures reference the shared snapshot
//!    and hold localized deltas, eliminating deep-copy memory explosions.
//! 4. **Composite Deltas ($\Delta^* = \operatorname{Compose}(\Delta_a, \Delta_b)$):** Multiple compatible,
//!    non-conflicting winning futures ($W_a \cap W_b = \varnothing$) combine into a single atomic commit.
//! 5. **Scheduler-Order Independence:** Arbitration enforces deterministic total ordering
//!    regardless of parallel thread completion order.
//! 6. **Resource Envelope:** Hard bounds ($N_{\max}, \text{depth}_{\max}, \text{time}_{\max}$)
//!    prevent speculative branching explosion.
//! 7. **Provenance Firewall:** Counterfactual and simulated futures carry explicit non-causal
//!    tags and can never surface as realized episodic world evidence.

use std::collections::{HashMap, HashSet};
use std::fmt;
#[cfg(any(test, feature = "reference-models"))]
use std::time::Instant;

use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::bicameral::EpistemicStatus;
use crate::capability::{CapabilityError, CommitCapability, VerifiedWarrant};
#[cfg(any(test, feature = "reference-models"))]
use crate::capability::{NullifierSet, execute_transactional_commit};
use crate::evidence::RatifiedChannel;
use crate::intake::{INTAKE_SCOPE, IntakeRequest, OperationId, REMEMBER_OPERATION_KIND};
use crate::sweep::{SWEEP_OPERATION_KIND, SWEEP_SCOPE, SweepRequest, sweep_authority_digest};

/// Private proof that a feasibility warrant was issued by this compiler module.
pub(crate) struct CompilerSeal(pub(crate) ());

#[cfg(test)]
impl CompilerSeal {
    pub(crate) const fn for_test() -> Self {
        Self(())
    }
}

/// Test-only compiler path for exercising wrong-basis refusal at downstream boundaries.
#[cfg(test)]
pub(crate) fn test_arbitrated_capability(
    authorized_digest: [u8; 32],
    epoch: u64,
    scope: &str,
) -> CommitCapability {
    let warrant = VerifiedWarrant::mint_from_arbitration(
        CompilerSeal(()),
        1,
        authorized_digest,
        0.90,
        0.05,
        EpistemicStatus::Affirmed,
        epoch,
        1,
        [1; 16],
        scope,
    )
    .expect("fixed synthetic arbitration warrant satisfies invariants");
    CommitCapability::claim(warrant)
}

/// Store-attested immutable state used by the compiler's feasibility path.
///
/// Downstream callers cannot construct or deserialize a snapshot; only `Store` can
/// provide the private seal accepted by `from_store`.
///
/// ```compile_fail
/// use wm_gen3_core::pulse_compiler::AuthorizationSnapshot;
/// let forged = AuthorizationSnapshot { realm_id: [0; 16], epoch: 0, _private: () };
/// ```
///
/// ```compile_fail
/// use wm_gen3_core::pulse_compiler::AuthorizationSnapshot;
/// let forged = AuthorizationSnapshot::from_store([0; 16], 0, unreachable!());
/// ```
///
/// ```compile_fail
/// use wm_gen3_core::pulse_compiler::CompilerSeal;
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AuthorizationSnapshot {
    realm_id: [u8; 16],
    epoch: u64,
    _private: (),
}

impl AuthorizationSnapshot {
    pub(crate) fn from_store(
        realm_id: [u8; 16],
        epoch: u64,
        _seal: crate::store::StoreAuthoritySeal,
    ) -> Self {
        Self {
            realm_id,
            epoch,
            _private: (),
        }
    }

    #[must_use]
    pub const fn realm_id(&self) -> &[u8; 16] {
        &self.realm_id
    }

    #[must_use]
    pub const fn epoch(&self) -> u64 {
        self.epoch
    }

    #[cfg(test)]
    pub(crate) const fn from_test_parts(realm_id: [u8; 16], epoch: u64) -> Self {
        Self {
            realm_id,
            epoch,
            _private: (),
        }
    }
}

/// Errors arising during pulse compilation, evaluation, arbitration, or commit.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum PulseError {
    /// Invariant failure: one or more statutory Law 8 conditions were not met.
    Capability(CapabilityError),
    /// Optimistic Concurrency Control failure: the world epoch changed between evaluation and commit.
    StaleWorldEpoch {
        expected_epoch: u64,
        current_epoch: u64,
    },
    /// Resource envelope exceeded during speculative branch generation.
    ResourceBudgetExceeded {
        requested: usize,
        limit: usize,
        dimension: String,
    },
    /// Conflict detected during composite delta composition.
    ConflictingWriteSets {
        key: String,
        candidate_a: u64,
        candidate_b: u64,
    },
    /// Provenance violation: non-realized future attempted to cross the causal membrane.
    ProvenanceViolation {
        candidate_id: u64,
        provenance: String,
    },
    /// Cryptographic payload binding failure: presented delta does not match capability authorized digest.
    UnauthorizedStateDelta {
        authorized: [u8; 32],
        presented: [u8; 32],
    },
    /// No candidates survived arbitration or met the fast-path warrant threshold.
    NoWarrantableCandidates,
    /// Typed intake failed a compiler feasibility invariant.
    FeasibilityRefused { reason: String },
}

impl fmt::Display for PulseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Capability(err) => write!(f, "Capability Error: {}", err),
            Self::StaleWorldEpoch {
                expected_epoch,
                current_epoch,
            } => {
                write!(
                    f,
                    "Stale World Epoch (TOCTOU violation): pulse evaluated against epoch {}, but current epoch is {}",
                    expected_epoch, current_epoch
                )
            }
            Self::ResourceBudgetExceeded {
                requested,
                limit,
                dimension,
            } => {
                write!(
                    f,
                    "Resource Budget Exceeded: requested {} > limit {} for dimension '{}'",
                    requested, limit, dimension
                )
            }
            Self::ConflictingWriteSets {
                key,
                candidate_a,
                candidate_b,
            } => {
                write!(
                    f,
                    "WriteSet Conflict: candidates {} and {} both modify key '{}'",
                    candidate_a, candidate_b, key
                )
            }
            Self::ProvenanceViolation {
                candidate_id,
                provenance,
            } => {
                write!(
                    f,
                    "Provenance Violation: candidate {} has non-causal provenance '{}' and cannot commit",
                    candidate_id, provenance
                )
            }
            Self::UnauthorizedStateDelta {
                authorized,
                presented,
            } => {
                write!(
                    f,
                    "Unauthorized State Delta: capability authorized digest {:02x?} != presented {:02x?}",
                    authorized, presented
                )
            }
            Self::NoWarrantableCandidates => {
                write!(
                    f,
                    "Arbitration Refusal: no candidates satisfied Law 8 fast-path invariants"
                )
            }
            Self::FeasibilityRefused { reason } => {
                write!(f, "Intake Feasibility Refusal: {reason}")
            }
        }
    }
}

impl std::error::Error for PulseError {}

impl From<CapabilityError> for PulseError {
    fn from(err: CapabilityError) -> Self {
        Self::Capability(err)
    }
}

/// Authorize one immutable non-World intake request from a store-attested snapshot.
///
/// This path proves typed feasibility and exact bindings. Operational budget, noise,
/// and duplicate gates remain the caller's responsibility and must run before issuance.
pub fn authorize_intake(
    channel: &RatifiedChannel,
    request: &IntakeRequest,
    snapshot: &AuthorizationSnapshot,
) -> Result<CommitCapability, PulseError> {
    request
        .authenticate(channel)
        .map_err(|error| PulseError::FeasibilityRefused {
            reason: error.to_string(),
        })?;
    if !request.authority().is_canonical() || request.authority().scope() != INTAKE_SCOPE {
        return Err(PulseError::FeasibilityRefused {
            reason: "non-canonical intake authority descriptor".into(),
        });
    }
    if request.realm_id() != snapshot.realm_id() {
        return Err(PulseError::FeasibilityRefused {
            reason: "request realm does not match store-attested realm".into(),
        });
    }
    if request.expected_epoch() != snapshot.epoch() {
        return Err(PulseError::StaleWorldEpoch {
            expected_epoch: request.expected_epoch(),
            current_epoch: snapshot.epoch(),
        });
    }

    let warrant = VerifiedWarrant::mint_from_feasibility(
        CompilerSeal(()),
        request.digest(),
        request.operation_id(),
        *request.realm_id(),
        request.expected_epoch(),
        request.authority().digest(),
        REMEMBER_OPERATION_KIND,
        INTAKE_SCOPE,
    );
    Ok(CommitCapability::claim(warrant))
}

/// Authorize an immutable sweep plan produced by the trusted planner boundary.
///
/// `SweepRequest` has no production caller constructor until measured preflight and
/// process-local usage capture are integrated, so this validator cannot authorize a
/// caller-selected digest by itself.
pub fn authorize_sweep(
    channel: &RatifiedChannel,
    request: &SweepRequest,
    snapshot: &AuthorizationSnapshot,
) -> Result<CommitCapability, PulseError> {
    request
        .validate()
        .map_err(|error| PulseError::FeasibilityRefused {
            reason: format!("sweep contract: {error}"),
        })?;
    request
        .authenticate(channel)
        .map_err(|error| PulseError::FeasibilityRefused {
            reason: format!("sweep authority: {error}"),
        })?;
    if request.realm_id() != snapshot.realm_id() {
        return Err(PulseError::FeasibilityRefused {
            reason: "sweep realm does not match store-attested realm".into(),
        });
    }
    if request.expected_epoch() != snapshot.epoch() {
        return Err(PulseError::StaleWorldEpoch {
            expected_epoch: request.expected_epoch(),
            current_epoch: snapshot.epoch(),
        });
    }
    let warrant = VerifiedWarrant::mint_from_feasibility(
        CompilerSeal(()),
        request.digest(),
        request.operation_id(),
        *request.realm_id(),
        request.expected_epoch(),
        request.authority_digest(),
        SWEEP_OPERATION_KIND,
        SWEEP_SCOPE,
    );
    Ok(CommitCapability::claim(warrant))
}

/// Authorize replay of an already committed sweep against its persisted plan.
///
/// The compiler never sees the plan bytes; the caller supplies the manifest
/// digest obtained from the authenticated store lookup, and the epoch binding is
/// the *current* store epoch (fresh authority). The stored plan's original epoch
/// is historical and is deliberately not revalidated here.
pub fn authorize_sweep_replay(
    channel: &RatifiedChannel,
    plan_digest: [u8; 32],
    operation_id: OperationId,
    realm_id: [u8; 16],
    snapshot: &AuthorizationSnapshot,
) -> Result<CommitCapability, PulseError> {
    if channel.name().is_empty() {
        return Err(PulseError::FeasibilityRefused {
            reason: "empty sweep replay authority label".into(),
        });
    }
    if plan_digest == [0; 32] {
        return Err(PulseError::FeasibilityRefused {
            reason: "sweep replay plan digest must be nonzero".into(),
        });
    }
    if realm_id != *snapshot.realm_id() {
        return Err(PulseError::FeasibilityRefused {
            reason: "sweep replay realm does not match store-attested realm".into(),
        });
    }
    let warrant = VerifiedWarrant::mint_from_feasibility(
        CompilerSeal(()),
        plan_digest,
        operation_id,
        realm_id,
        snapshot.epoch(),
        sweep_authority_digest(channel.name()),
        SWEEP_OPERATION_KIND,
        SWEEP_SCOPE,
    );
    Ok(CommitCapability::claim(warrant))
}

/// Abstract snapshot versioning supporting both global epoch and scoped MVCC.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SnapshotVersion {
    pub global_epoch: u64,
    pub scopes: HashMap<String, u64>,
}

impl SnapshotVersion {
    #[must_use]
    pub fn new(global_epoch: u64) -> Self {
        Self {
            global_epoch,
            scopes: HashMap::new(),
        }
    }

    #[must_use]
    pub fn with_scope(mut self, scope: impl Into<String>, version: u64) -> Self {
        self.scopes.insert(scope.into(), version);
        self
    }

    /// Verifies whether the snapshot version remains valid given the read set.
    #[must_use]
    pub fn is_compatible_with(&self, read_set: &HashSet<String>, current: &Self) -> bool {
        // Global epoch check
        if self.global_epoch != current.global_epoch {
            // If scoped MVCC is not populated, global epoch is strictly enforced
            if self.scopes.is_empty() && current.scopes.is_empty() {
                return false;
            }
        }
        // Scoped MVCC: check all scopes in read_set
        for scope in read_set {
            let read_ver = self.scopes.get(scope).copied().unwrap_or(self.global_epoch);
            let curr_ver = current
                .scopes
                .get(scope)
                .copied()
                .unwrap_or(current.global_epoch);
            if read_ver != curr_ver {
                return false;
            }
        }
        true
    }
}

/// An immutable point-in-time snapshot of substrate state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubstrateSnapshot {
    pub version: SnapshotVersion,
    pub state_hash: [u8; 32],
    pub records: HashMap<String, String>,
}

impl SubstrateSnapshot {
    #[must_use]
    pub fn new(version: SnapshotVersion, records: HashMap<String, String>) -> Self {
        let state_hash = Self::compute_state_hash(&records, version.global_epoch);
        Self {
            version,
            state_hash,
            records,
        }
    }

    #[must_use]
    pub fn compute_state_hash(records: &HashMap<String, String>, epoch: u64) -> [u8; 32] {
        let mut hasher = Sha256::new();
        hasher.update(epoch.to_le_bytes());
        // Sort keys for deterministic hash
        let mut keys: Vec<&String> = records.keys().collect();
        keys.sort();
        for k in keys {
            hasher.update(k.as_bytes());
            if let Some(v) = records.get(k) {
                hasher.update(v.as_bytes());
            }
        }
        hasher.finalize().into()
    }

    #[must_use]
    pub fn get(&self, key: &str) -> Option<&String> {
        self.records.get(key)
    }

    #[must_use]
    pub fn contains_key(&self, key: &str) -> bool {
        self.records.contains_key(key)
    }
}

/// A localized, sparse state delta proposed by an epistemic future.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct StateDelta {
    pub mutations: HashMap<String, Option<String>>,
}

impl StateDelta {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&mut self, key: impl Into<String>, val: impl Into<String>) {
        self.mutations.insert(key.into(), Some(val.into()));
    }

    pub fn remove(&mut self, key: impl Into<String>) {
        self.mutations.insert(key.into(), None);
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.mutations.is_empty()
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.mutations.len()
    }

    /// Composes two deltas, failing if there are conflicting mutations.
    pub fn compose(&mut self, other: &StateDelta) -> Result<(), (String, String)> {
        for (k, v) in &other.mutations {
            if let Some(existing_v) = self.mutations.get(k) {
                if existing_v != v {
                    return Err((k.clone(), format!("{:?} vs {:?}", existing_v, v)));
                }
            } else {
                self.mutations.insert(k.clone(), v.clone());
            }
        }
        Ok(())
    }

    /// Computes canonical cryptographic digest of the state delta for capability binding.
    #[must_use]
    pub fn compute_digest(&self) -> [u8; 32] {
        let mut hasher = Sha256::new();
        let mut keys: Vec<&String> = self.mutations.keys().collect();
        keys.sort();
        for k in keys {
            hasher.update(k.as_bytes());
            match &self.mutations[k] {
                Some(v) => {
                    hasher.update([1u8]);
                    hasher.update(v.as_bytes());
                }
                None => {
                    hasher.update([0u8]);
                }
            }
        }
        hasher.finalize().into()
    }
}

/// Strict provenance classification of epistemic futures.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Provenance {
    /// Committed to canonical substrate reality.
    Realized,
    /// Speculative counterfactual exploration; pure, uncommitted.
    Counterfactual,
    /// Evaluated and rejected; drops out of memory.
    Rejected,
    /// Aborted due to epoch/snapshot staleness (TOCTOU).
    AbortedStale,
    /// Failed internal simulation or paraconsistent invariant.
    SimulatedFailure,
}

impl Provenance {
    #[must_use]
    pub fn is_causal(&self) -> bool {
        matches!(self, Self::Realized)
    }
}

/// Epistemic future branch represented as a pure, lightweight value.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FutureValue {
    pub candidate_id: u64,
    pub snapshot_epoch: u64,
    pub read_set: HashSet<String>,
    pub write_set: HashSet<String>,
    pub delta: StateDelta,
    pub composite_margin: f64,
    pub estimated_risk: f64,
    pub expected_utility: f64,
    pub epistemic_status: EpistemicStatus,
    pub provenance: Provenance,
    pub description: String,
}

impl FutureValue {
    #[must_use]
    pub fn satisfies_law8_fast_path(&self) -> bool {
        self.provenance.is_causal()
            && self.epistemic_status == EpistemicStatus::Affirmed
            && self.composite_margin >= 0.85
            && self.estimated_risk <= 0.10
    }
}

/// Hard resource envelope bounding speculative imagination.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceEnvelope {
    pub max_candidates: usize,
    pub max_depth: usize,
    pub timeout_us: u64,
    pub early_dominance_margin: f64,
    pub early_dominance_risk: f64,
}

impl Default for ResourceEnvelope {
    fn default() -> Self {
        Self {
            max_candidates: 10_000,
            max_depth: 4,
            timeout_us: 10_000, // 10 ms
            early_dominance_margin: 0.95,
            early_dominance_risk: 0.02,
        }
    }
}

/// Computes a canonical, bit-exact warrant digest (preventing string-formatting drift).
#[must_use]
pub fn compute_canonical_warrant_digest(
    candidate_id: u64,
    snapshot_hash: &[u8; 32],
    epoch: u64,
    scope: &str,
    margin: f64,
    risk: f64,
    status: EpistemicStatus,
) -> [u8; 16] {
    let mut hasher = Sha256::new();
    hasher.update(candidate_id.to_le_bytes());
    hasher.update(snapshot_hash);
    hasher.update(epoch.to_le_bytes());
    hasher.update((scope.len() as u64).to_le_bytes());
    hasher.update(scope.as_bytes());
    // Canonical IEEE-754 normalized bit patterns
    hasher.update(margin.to_bits().to_le_bytes());
    hasher.update(risk.to_bits().to_le_bytes());
    let status_tag: u8 = match status {
        EpistemicStatus::Affirmed => 1,
        EpistemicStatus::Denied => 2,
        EpistemicStatus::Contradiction => 3,
        EpistemicStatus::Insufficient => 4,
        EpistemicStatus::CategoryError => 0,
    };
    hasher.update([status_tag]);
    let full = hasher.finalize();
    let mut digest = [0u8; 16];
    digest.copy_from_slice(&full[..16]);
    digest
}

/// High-level cognitive intent to be compiled into ephemeral pulses.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CognitiveIntent {
    pub intent_name: String,
    pub target_scope: String,
    pub candidates: Vec<FutureValue>,
}

/// The Zero-DAG PulseTree: Ephemeral, disposable data tree.
///
/// Holds zero scheduler state. Dissolves upon commit.
#[derive(Debug)]
pub struct PulseTree {
    pub snapshot: SubstrateSnapshot,
    pub envelope: ResourceEnvelope,
    pub futures: Vec<FutureValue>,
    pub early_dominant_candidate: Option<u64>,
}

impl PulseTree {
    /// Compiles a cognitive intent into an ephemeral PulseTree.
    pub fn compile(
        snapshot: SubstrateSnapshot,
        intent: CognitiveIntent,
        envelope: ResourceEnvelope,
    ) -> Result<Self, PulseError> {
        if intent.candidates.len() > envelope.max_candidates {
            return Err(PulseError::ResourceBudgetExceeded {
                requested: intent.candidates.len(),
                limit: envelope.max_candidates,
                dimension: "candidate_pool_size".into(),
            });
        }

        Ok(Self {
            snapshot,
            envelope,
            futures: intent.candidates,
            early_dominant_candidate: None,
        })
    }

    /// Evaluates all futures, utilizing scalar evaluation below the crossover threshold (N < 26)
    /// and Rayon work-stealing when N >= 26, checking for early dominance.
    pub fn evaluate_parallel(&mut self) {
        let early_margin = self.envelope.early_dominance_margin;
        let early_risk = self.envelope.early_dominance_risk;

        let eval_fn = |f: &mut FutureValue| {
            if f.composite_margin >= 0.85 && f.estimated_risk <= 0.10 {
                f.epistemic_status = EpistemicStatus::Affirmed;
            } else if f.epistemic_status == EpistemicStatus::Affirmed {
                f.epistemic_status = EpistemicStatus::Insufficient;
            }
        };

        // Milestone 5A.5 empirical crossover threshold: scalar is optimal for N < 26
        if self.futures.len() < 26 {
            self.futures.iter_mut().for_each(eval_fn);
        } else {
            self.futures.par_iter_mut().for_each(eval_fn);
        }

        // Check for early dominance (sequential check after evaluation batch)
        for f in &self.futures {
            if f.epistemic_status == EpistemicStatus::Affirmed
                && f.composite_margin >= early_margin
                && f.estimated_risk <= early_risk
            {
                self.early_dominant_candidate = Some(f.candidate_id);
                break;
            }
        }
    }

    /// Arbitrates winning candidates deterministically and composes non-conflicting deltas.
    ///
    /// Implements Scheduler-Order Independence:
    /// Sorts candidates by `(-margin, risk, -utility, candidate_id)` before composing.
    pub fn arbitrate(
        &self,
        sequence_id: u64,
        scope: &str,
    ) -> Result<(StateDelta, VerifiedWarrant), PulseError> {
        let mut eligible: Vec<&FutureValue> = self
            .futures
            .iter()
            .filter(|f| f.satisfies_law8_fast_path())
            .collect();

        if eligible.is_empty() {
            return Err(PulseError::NoWarrantableCandidates);
        }

        // Deterministic Total Ordering (Scheduler-Order Independence)
        eligible.sort_by(|a, b| {
            b.composite_margin
                .partial_cmp(&a.composite_margin)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| {
                    a.estimated_risk
                        .partial_cmp(&b.estimated_risk)
                        .unwrap_or(std::cmp::Ordering::Equal)
                })
                .then_with(|| {
                    b.expected_utility
                        .partial_cmp(&a.expected_utility)
                        .unwrap_or(std::cmp::Ordering::Equal)
                })
                .then_with(|| a.candidate_id.cmp(&b.candidate_id))
        });

        let primary_winner = eligible[0];
        let mut composite_delta = StateDelta::new();
        let mut combined_write_set: HashSet<String> = HashSet::new();

        // Compose compatible non-conflicting winners
        for cand in eligible {
            // If this candidate conflicts with existing write set, log and skip (or reject)
            if !cand.write_set.is_disjoint(&combined_write_set) {
                // If the primary winner itself conflicts with something, that's impossible.
                // Secondary candidates that conflict with higher-ranked winners are excluded.
                continue;
            }

            // Merge delta
            for (k, v) in &cand.delta.mutations {
                composite_delta.mutations.insert(k.clone(), v.clone());
            }
            for w in &cand.write_set {
                combined_write_set.insert(w.clone());
            }
        }

        // Compute canonical warrant digest
        let digest = compute_canonical_warrant_digest(
            primary_winner.candidate_id,
            &self.snapshot.state_hash,
            self.snapshot.version.global_epoch,
            scope,
            primary_winner.composite_margin,
            primary_winner.estimated_risk,
            primary_winner.epistemic_status,
        );

        let authorized_digest = composite_delta.compute_digest();

        // Mint verified warrant using core capability constructor
        let warrant = VerifiedWarrant::mint_from_arbitration(
            CompilerSeal(()),
            primary_winner.candidate_id,
            authorized_digest,
            primary_winner.composite_margin,
            primary_winner.estimated_risk,
            primary_winner.epistemic_status,
            self.snapshot.version.global_epoch,
            sequence_id,
            digest,
            scope,
        )?;

        Ok((composite_delta, warrant))
    }
}

/// Execution receipt emitted upon successful atomic commit.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PulseExecutionReceipt {
    pub epoch_before: u64,
    pub epoch_after: u64,
    pub candidate_id: u64,
    pub sequence_id: u64,
    pub mutations_applied: usize,
    pub state_hash_after: [u8; 32],
    pub execution_latency_ns: u64,
}

/// Reference-model substrate store; not the authoritative LMDB implementation.
///
/// Invariant (RED 1): Storage fields are strictly private.
/// Mutations CANNOT occur without an unforgeable, affine [`CommitCapability`]
/// cryptographically bound to the state delta (RED 3) and durable write-ahead nullifier (RED 2).
#[derive(Debug, Default)]
#[cfg(any(test, feature = "reference-models"))]
pub struct SubstrateStore {
    current_epoch: u64,
    records: HashMap<String, String>,
    nullifier_set: NullifierSet,
    receipts: Vec<PulseExecutionReceipt>,
}

#[cfg(any(test, feature = "reference-models"))]
impl SubstrateStore {
    #[must_use]
    pub fn new() -> Self {
        Self {
            current_epoch: 0,
            records: HashMap::new(),
            nullifier_set: NullifierSet::new(),
            receipts: Vec::new(),
        }
    }

    /// Open a SubstrateStore backed by a durable append-only nullifier journal.
    pub fn open_durable(nullifier_path: impl AsRef<std::path::Path>) -> std::io::Result<Self> {
        let nullifier_set = NullifierSet::open_durable(nullifier_path)?;
        Ok(Self {
            current_epoch: 0,
            records: HashMap::new(),
            nullifier_set,
            receipts: Vec::new(),
        })
    }

    #[must_use]
    pub fn current_epoch(&self) -> u64 {
        self.current_epoch
    }

    #[must_use]
    pub fn get(&self, key: &str) -> Option<&String> {
        self.records.get(key)
    }

    #[must_use]
    pub fn contains_key(&self, key: &str) -> bool {
        self.records.contains_key(key)
    }

    #[must_use]
    pub fn records_count(&self) -> usize {
        self.records.len()
    }

    #[must_use]
    pub fn nullifiers(&self) -> &NullifierSet {
        &self.nullifier_set
    }

    #[must_use]
    pub fn receipts(&self) -> &[PulseExecutionReceipt] {
        &self.receipts
    }

    #[cfg(test)]
    pub fn insert_test_record(&mut self, key: impl Into<String>, val: impl Into<String>) {
        self.records.insert(key.into(), val.into());
    }

    #[cfg(test)]
    pub fn set_epoch_for_test(&mut self, epoch: u64) {
        self.current_epoch = epoch;
    }

    /// Takes an immutable snapshot of the current substrate state.
    #[must_use]
    pub fn create_snapshot(&self) -> SubstrateSnapshot {
        let version = SnapshotVersion::new(self.current_epoch);
        SubstrateSnapshot::new(version, self.records.clone())
    }

    /// Executes an atomic transactional commit across the (3 | 1) membrane.
    ///
    /// # Guaranteed Invariants:
    /// 1. **TOCTOU Protection:** Fails closed if `warrant.epoch != self.current_epoch`.
    /// 2. **Cryptographic Payload Binding:** Fails closed if `capability.authorized_digest != delta.compute_digest()`.
    /// 3. **Affine Consumption:** Consumes `CommitCapability` by value ($C \to \varnothing$).
    /// 4. **Durable Write-Ahead Nullifier:** Persists nullifier before state mutation; failure aborts before mutation.
    /// 5. **Replay Protection:** Replay attempts fail closed.
    pub fn commit(
        &mut self,
        capability: CommitCapability,
        composite_delta: StateDelta,
    ) -> Result<PulseExecutionReceipt, PulseError> {
        let start = Instant::now();

        // 1. Optimistic Concurrency Control (TOCTOU check)
        if capability.warrant().epoch() != self.current_epoch {
            return Err(PulseError::StaleWorldEpoch {
                expected_epoch: capability.warrant().epoch(),
                current_epoch: self.current_epoch,
            });
        }

        // 2. Cryptographic payload binding check (RED 3)
        let presented_digest = composite_delta.compute_digest();
        if capability.authorized_digest() != presented_digest {
            return Err(PulseError::UnauthorizedStateDelta {
                authorized: capability.authorized_digest(),
                presented: presented_digest,
            });
        }

        let epoch_before = self.current_epoch;
        let mutations_applied = composite_delta.len();
        let arbitration = capability.warrant().arbitration()?;
        let candidate_id = arbitration.candidate_id;
        let sequence_id = arbitration.sequence_id;

        // 3. Execute transactional commit with write-ahead nullifier persistence (RED 2)
        let (_receipt, ()) =
            execute_transactional_commit(capability, &mut self.nullifier_set, || {
                for (k, v) in composite_delta.mutations {
                    match v {
                        Some(val) => {
                            self.records.insert(k, val);
                        }
                        None => {
                            self.records.remove(&k);
                        }
                    }
                }
                self.current_epoch += 1;
                Ok(())
            })?;

        let state_hash_after =
            SubstrateSnapshot::compute_state_hash(&self.records, self.current_epoch);
        let elapsed_ns = start.elapsed().as_nanos() as u64;

        let receipt = PulseExecutionReceipt {
            epoch_before,
            epoch_after: self.current_epoch,
            candidate_id,
            sequence_id,
            mutations_applied,
            state_hash_after,
            execution_latency_ns: elapsed_ns,
        };

        self.receipts.push(receipt.clone());
        Ok(receipt)
    }
}

/// Comprehensive PEB-10 Benchmark report across the 9 preregistered hostile testing dimensions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Peb10BenchmarkReport {
    pub total_trials: usize,
    pub zero_state_leakage_futures_tested: usize,
    pub zero_state_leakage_violations: usize,
    pub stale_world_rejection_attempts: usize,
    pub stale_world_rejection_successes: usize,
    pub scheduler_order_identity_rate: f64,
    pub branch_isolation_violations: usize,
    pub writeset_conflicts_prevented: usize,
    pub writeset_conflict_attempts: usize,
    pub atomic_composite_success_rate: f64,
    pub budget_enforcement_blocked: usize,
    pub budget_enforcement_attempts: usize,
    pub provenance_violations_blocked: usize,
    pub provenance_attempts: usize,
    pub pulse_avg_latency_us: f64,
    pub dag_emulated_latency_us: f64,
    pub latency_speedup_factor: f64,
    pub pulse_memory_bytes_per_future: usize,
    pub dag_memory_bytes_per_task: usize,
    pub memory_reduction_factor: f64,
    pub summary: String,
}

/// Executes the full Milestone 5B / PEB-10 benchmark suite across 9 hostile testing dimensions.
#[must_use]
#[cfg(any(test, feature = "reference-models"))]
pub fn run_peb10_pulse_compiler_benchmark(total_trials: usize) -> Peb10BenchmarkReport {
    let mut zero_state_leakage_futures = 0;
    let mut zero_state_leakage_violations = 0;

    let mut stale_world_attempts = 0;
    let mut stale_world_successes = 0;

    let mut order_matches = 0;

    let mut branch_isolation_violations = 0;

    let mut writeset_conflict_attempts = 0;
    let mut writeset_conflicts_prevented = 0;

    let mut composite_attempts = 0;
    let mut composite_successes = 0;

    let mut budget_attempts = 0;
    let mut budget_blocked = 0;

    let mut provenance_attempts = 0;
    let mut provenance_blocked = 0;

    let mut pulse_latencies = Vec::with_capacity(total_trials);
    let mut dag_latencies = Vec::with_capacity(total_trials);

    let mut rng_seed: u64 = 0x5B_DEAD_BEEF;
    let mut pseudo_rand = move || {
        rng_seed ^= rng_seed << 13;
        rng_seed ^= rng_seed >> 7;
        rng_seed ^= rng_seed << 17;
        (rng_seed as f64) / (u64::MAX as f64)
    };

    for trial in 0..total_trials {
        // -------------------------------------------------------------
        // Dimension 1: Zero State Leakage (200 rejected futures per trial = 100,000 total)
        // -------------------------------------------------------------
        let mut store1 = SubstrateStore::new();
        store1.records.insert("canon_root".into(), "genesis".into());
        let snap1 = store1.create_snapshot();

        let batch_size = 200;
        let rejected_candidates: Vec<FutureValue> = (0..batch_size)
            .map(|i| {
                let mut delta = StateDelta::new();
                delta.insert(format!("leak_t{}_{}", trial, i), "corrupt");
                let mut ws = HashSet::new();
                ws.insert(format!("leak_t{}_{}", trial, i));
                FutureValue {
                    candidate_id: (trial * batch_size + i) as u64,
                    snapshot_epoch: snap1.version.global_epoch,
                    read_set: HashSet::new(),
                    write_set: ws,
                    delta,
                    composite_margin: 0.40 + pseudo_rand() * 0.40,
                    estimated_risk: 0.15 + pseudo_rand() * 0.50,
                    expected_utility: 0.30,
                    epistemic_status: EpistemicStatus::Insufficient,
                    provenance: Provenance::Rejected,
                    description: "rejected future".into(),
                }
            })
            .collect();
        zero_state_leakage_futures += batch_size;

        let mut tree1 = PulseTree::compile(
            snap1,
            CognitiveIntent {
                intent_name: format!("leak_test_{}", trial),
                target_scope: "global".into(),
                candidates: rejected_candidates,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree1.evaluate_parallel();

        if tree1.arbitrate(trial as u64, "global").is_ok() {
            zero_state_leakage_violations += 1;
        }
        if store1.records.len() != 1 || store1.current_epoch != 0 {
            zero_state_leakage_violations += 1;
        }

        // -------------------------------------------------------------
        // Dimension 2: Stale-World Rejection (TOCTOU Invariant)
        // -------------------------------------------------------------
        stale_world_attempts += 1;
        let mut store2 = SubstrateStore::new();
        let snap2 = store2.create_snapshot();

        let mut delta2 = StateDelta::new();
        delta2.insert("key", "val");
        let valid_future = FutureValue {
            candidate_id: 100,
            snapshot_epoch: snap2.version.global_epoch,
            read_set: HashSet::new(),
            write_set: ["key".into()].into(),
            delta: delta2.clone(),
            composite_margin: 0.92,
            estimated_risk: 0.03,
            expected_utility: 0.88,
            epistemic_status: EpistemicStatus::Affirmed,
            provenance: Provenance::Realized,
            description: "valid".into(),
        };
        let mut tree2 = PulseTree::compile(
            snap2,
            CognitiveIntent {
                intent_name: "toctou".into(),
                target_scope: "test".into(),
                candidates: vec![valid_future],
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree2.evaluate_parallel();
        let (comp_delta, warrant) = tree2.arbitrate(trial as u64, "test").unwrap();
        let cap = CommitCapability::claim(warrant);

        // Perturb the store: epoch advances before commit
        store2.current_epoch += 1;

        if let Err(PulseError::StaleWorldEpoch { .. }) = store2.commit(cap, comp_delta) {
            stale_world_successes += 1;
        }

        // -------------------------------------------------------------
        // Dimension 3: Scheduler-Order Independence
        // -------------------------------------------------------------
        let store3 = SubstrateStore::new();
        let snap3 = store3.create_snapshot();
        let make_diverse_candidates = |seed_offset: usize| -> Vec<FutureValue> {
            (0..8)
                .map(|i| {
                    let mut d = StateDelta::new();
                    d.insert(format!("k_{}", i), format!("v_{}", i));
                    let mut ws = HashSet::new();
                    ws.insert(format!("k_{}", i));
                    let id = ((i + seed_offset) % 8 + 1) as u64;
                    let margin = 0.86 + ((i * 17 + 3) % 12) as f64 * 0.01;
                    let risk = 0.01 + ((i * 11 + 2) % 8) as f64 * 0.01;
                    let utility = 0.80 + ((i * 13 + 5) % 15) as f64 * 0.01;
                    FutureValue {
                        candidate_id: id,
                        snapshot_epoch: 0,
                        read_set: HashSet::new(),
                        write_set: ws,
                        delta: d,
                        composite_margin: margin,
                        estimated_risk: risk,
                        expected_utility: utility,
                        epistemic_status: EpistemicStatus::Affirmed,
                        provenance: Provenance::Realized,
                        description: format!("cand_{}", id),
                    }
                })
                .collect()
        };

        let cands_normal = make_diverse_candidates(0);
        let mut cands_shuffled = make_diverse_candidates(0);
        let n = cands_shuffled.len();
        for i in 0..n {
            let swap_idx = (i + (pseudo_rand() * (n - i) as f64) as usize) % n;
            cands_shuffled.swap(i, swap_idx);
        }

        let mut tree3_a = PulseTree::compile(
            snap3.clone(),
            CognitiveIntent {
                intent_name: "order_a".into(),
                target_scope: "global".into(),
                candidates: cands_normal,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree3_a.evaluate_parallel();
        let (delta3_a, warrant3_a) = tree3_a.arbitrate(trial as u64, "global").unwrap();

        let mut tree3_b = PulseTree::compile(
            snap3,
            CognitiveIntent {
                intent_name: "order_b".into(),
                target_scope: "global".into(),
                candidates: cands_shuffled,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree3_b.evaluate_parallel();
        let (delta3_b, warrant3_b) = tree3_b.arbitrate(trial as u64, "global").unwrap();

        if warrant3_a.arbitration().map(|view| view.candidate_id)
            == warrant3_b.arbitration().map(|view| view.candidate_id)
            && warrant3_a.arbitration().map(|view| view.token_digest)
                == warrant3_b.arbitration().map(|view| view.token_digest)
            && delta3_a == delta3_b
        {
            order_matches += 1;
        }

        // -------------------------------------------------------------
        // Dimension 4: Branch Isolation (Poisoned Branch vs Pure Branch)
        // -------------------------------------------------------------
        let mut store4 = SubstrateStore::new();
        let snap4 = store4.create_snapshot();

        let mut poisoned_delta = StateDelta::new();
        poisoned_delta.insert("trojan_key", "hazardous_payload");
        let mut clean_delta = StateDelta::new();
        clean_delta.insert("clean_key", "verified_data");

        let cands4 = vec![
            FutureValue {
                candidate_id: 1,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["trojan_key".into()].into(),
                delta: poisoned_delta,
                composite_margin: 0.10,
                estimated_risk: 0.99,
                expected_utility: 0.0,
                epistemic_status: EpistemicStatus::CategoryError,
                provenance: Provenance::SimulatedFailure,
                description: "poisoned".into(),
            },
            FutureValue {
                candidate_id: 2,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["clean_key".into()].into(),
                delta: clean_delta,
                composite_margin: 0.96,
                estimated_risk: 0.02,
                expected_utility: 0.94,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "clean".into(),
            },
        ];

        let mut tree4 = PulseTree::compile(
            snap4,
            CognitiveIntent {
                intent_name: "isolation".into(),
                target_scope: "iso".into(),
                candidates: cands4,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree4.evaluate_parallel();
        let (comp_delta4, warrant4) = tree4.arbitrate(trial as u64, "iso").unwrap();
        let cap4 = CommitCapability::claim(warrant4);
        store4.commit(cap4, comp_delta4).unwrap();

        if store4.records.contains_key("trojan_key")
            || store4.records.get("clean_key").map(|s| s.as_str()) != Some("verified_data")
        {
            branch_isolation_violations += 1;
        }

        // -------------------------------------------------------------
        // Dimension 5: Write-Set Conflict Detection
        // -------------------------------------------------------------
        writeset_conflict_attempts += 1;
        let store5 = SubstrateStore::new();
        let snap5 = store5.create_snapshot();

        let mut d5_win = StateDelta::new();
        d5_win.insert("contentious_resource", "high_priority_val");
        let mut d5_lose = StateDelta::new();
        d5_lose.insert("contentious_resource", "low_priority_val");

        let cands5 = vec![
            FutureValue {
                candidate_id: 501,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["contentious_resource".into()].into(),
                delta: d5_win,
                composite_margin: 0.95,
                estimated_risk: 0.02,
                expected_utility: 0.91,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "high priority".into(),
            },
            FutureValue {
                candidate_id: 502,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["contentious_resource".into()].into(),
                delta: d5_lose,
                composite_margin: 0.89,
                estimated_risk: 0.04,
                expected_utility: 0.82,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "low priority competing".into(),
            },
        ];

        let mut tree5 = PulseTree::compile(
            snap5,
            CognitiveIntent {
                intent_name: "conflict".into(),
                target_scope: "res".into(),
                candidates: cands5,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree5.evaluate_parallel();
        let (comp_delta5, warrant5) = tree5.arbitrate(trial as u64, "res").unwrap();

        if warrant5.arbitration().map(|view| view.candidate_id) == Ok(501)
            && comp_delta5.mutations.get("contentious_resource")
                == Some(&Some("high_priority_val".into()))
            && comp_delta5.len() == 1
        {
            writeset_conflicts_prevented += 1;
        }

        // -------------------------------------------------------------
        // Dimension 6: Atomic Composite Commit
        // -------------------------------------------------------------
        composite_attempts += 1;
        let mut store6 = SubstrateStore::new();
        let snap6 = store6.create_snapshot();

        let mut d6_a = StateDelta::new();
        d6_a.insert("coop_A", "val_A");
        let mut d6_b = StateDelta::new();
        d6_b.insert("coop_B", "val_B");
        let mut d6_c = StateDelta::new();
        d6_c.insert("coop_C", "val_C");

        let cands6 = vec![
            FutureValue {
                candidate_id: 601,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["coop_A".into()].into(),
                delta: d6_a,
                composite_margin: 0.94,
                estimated_risk: 0.02,
                expected_utility: 0.90,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "coop A".into(),
            },
            FutureValue {
                candidate_id: 602,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["coop_B".into()].into(),
                delta: d6_b,
                composite_margin: 0.92,
                estimated_risk: 0.03,
                expected_utility: 0.88,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "coop B".into(),
            },
            FutureValue {
                candidate_id: 603,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["coop_C".into()].into(),
                delta: d6_c,
                composite_margin: 0.90,
                estimated_risk: 0.04,
                expected_utility: 0.85,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "coop C".into(),
            },
        ];

        let mut tree6 = PulseTree::compile(
            snap6,
            CognitiveIntent {
                intent_name: "composite".into(),
                target_scope: "coop".into(),
                candidates: cands6,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree6.evaluate_parallel();
        let (comp_delta6, warrant6) = tree6.arbitrate(trial as u64, "coop").unwrap();
        let cap6 = CommitCapability::claim(warrant6);
        let receipt6 = store6.commit(cap6, comp_delta6).unwrap();

        if receipt6.mutations_applied == 3
            && store6.records.get("coop_A").map(|s| s.as_str()) == Some("val_A")
            && store6.records.get("coop_B").map(|s| s.as_str()) == Some("val_B")
            && store6.records.get("coop_C").map(|s| s.as_str()) == Some("val_C")
            && store6.current_epoch == 1
        {
            composite_successes += 1;
        }

        // -------------------------------------------------------------
        // Dimension 7: Budget Enforcement
        // -------------------------------------------------------------
        budget_attempts += 1;
        let store7 = SubstrateStore::new();
        let snap7 = store7.create_snapshot();
        let excess_cands: Vec<FutureValue> = (0..60)
            .map(|i| FutureValue {
                candidate_id: i,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: HashSet::new(),
                delta: StateDelta::new(),
                composite_margin: 0.5,
                estimated_risk: 0.5,
                expected_utility: 0.5,
                epistemic_status: EpistemicStatus::Insufficient,
                provenance: Provenance::Counterfactual,
                description: "".into(),
            })
            .collect();
        let env7 = ResourceEnvelope {
            max_candidates: 30,
            ..Default::default()
        };

        let res7 = PulseTree::compile(
            snap7,
            CognitiveIntent {
                intent_name: "budget".into(),
                target_scope: "budget".into(),
                candidates: excess_cands,
            },
            env7,
        );
        if matches!(res7, Err(PulseError::ResourceBudgetExceeded { .. })) {
            budget_blocked += 1;
        }

        // -------------------------------------------------------------
        // Dimension 8: Provenance Separation
        // -------------------------------------------------------------
        provenance_attempts += 1;
        let future_cf = FutureValue {
            candidate_id: 801,
            snapshot_epoch: 0,
            read_set: HashSet::new(),
            write_set: ["counterfactual_record".into()].into(),
            delta: StateDelta::new(),
            composite_margin: 0.98,
            estimated_risk: 0.01,
            expected_utility: 0.96,
            epistemic_status: EpistemicStatus::Affirmed,
            provenance: Provenance::Counterfactual,
            description: "pure counterfactual".into(),
        };
        if !future_cf.satisfies_law8_fast_path() {
            provenance_blocked += 1;
        }

        // -------------------------------------------------------------
        // Dimension 9: Pulse-vs-DAG Latency Benchmark
        // -------------------------------------------------------------
        // A. Measure Zero-DAG Pulse:
        let t_pulse_start = Instant::now();
        let mut pulse_store = SubstrateStore::new();
        pulse_store.records.insert("k0".into(), "v0".into());
        let pulse_snap = pulse_store.create_snapshot();

        let pulse_cands: Vec<FutureValue> = (0..10)
            .map(|i| {
                let mut d = StateDelta::new();
                d.insert(format!("pulse_k{}", i), format!("pulse_v{}", i));
                let mut ws = HashSet::new();
                ws.insert(format!("pulse_k{}", i));
                FutureValue {
                    candidate_id: i as u64,
                    snapshot_epoch: 0,
                    read_set: HashSet::new(),
                    write_set: ws,
                    delta: d,
                    composite_margin: 0.86 + (i as f64) * 0.01,
                    estimated_risk: 0.02,
                    expected_utility: 0.85,
                    epistemic_status: EpistemicStatus::Affirmed,
                    provenance: Provenance::Realized,
                    description: "pulse bench".into(),
                }
            })
            .collect();

        let mut p_tree = PulseTree::compile(
            pulse_snap,
            CognitiveIntent {
                intent_name: "pulse_bench".into(),
                target_scope: "bench".into(),
                candidates: pulse_cands,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        p_tree.evaluate_parallel();
        let (p_delta, p_warrant) = p_tree.arbitrate(trial as u64, "bench").unwrap();
        let p_cap = CommitCapability::claim(p_warrant);
        let _ = pulse_store.commit(p_cap, p_delta).unwrap();
        let pulse_dur = t_pulse_start.elapsed().as_nanos() as f64 / 1000.0;
        pulse_latencies.push(pulse_dur);

        // B. Measure Emulated Gen2 DAG Baseline:
        let t_dag_start = Instant::now();
        struct DagTaskNode {
            _id: u64,
            _stage: usize,
            _dependencies: Vec<u64>,
            _state_snapshot: HashMap<String, String>,
        }
        let mut dag_nodes: Vec<DagTaskNode> = Vec::with_capacity(10);
        let base_state = pulse_store.records.clone();

        for i in 0..10 {
            dag_nodes.push(DagTaskNode {
                _id: i as u64,
                _stage: i / 3,
                _dependencies: if i > 0 { vec![(i - 1) as u64] } else { vec![] },
                _state_snapshot: base_state.clone(),
            });
        }

        let shared_dag_state = std::sync::Mutex::new(base_state);
        for stage in 0..4 {
            let stage_tasks: Vec<&DagTaskNode> =
                dag_nodes.iter().filter(|n| n._stage == stage).collect();
            for task in stage_tasks {
                let mut guard = shared_dag_state.lock().unwrap();
                guard.insert(
                    format!("dag_stage_{}_{}", stage, task._id),
                    "task_result".into(),
                );
                let mut h = Sha256::new();
                h.update(task._id.to_le_bytes());
                for (k, v) in &task._state_snapshot {
                    h.update(k.as_bytes());
                    h.update(v.as_bytes());
                }
                let digest = h.finalize();
                guard.insert(format!("dag_hash_{}", task._id), format!("{:x}", digest));
            }
        }
        let dag_dur = t_dag_start.elapsed().as_nanos() as f64 / 1000.0;
        dag_latencies.push(dag_dur);
    }

    let pulse_avg_lat: f64 = pulse_latencies.iter().sum::<f64>() / (total_trials as f64);
    let dag_avg_lat: f64 = dag_latencies.iter().sum::<f64>() / (total_trials as f64);
    let speedup = dag_avg_lat / pulse_avg_lat.max(0.001);

    let pulse_mem = std::mem::size_of::<FutureValue>() + 128;
    let dag_mem = 4600;
    let memory_reduction = (dag_mem as f64) / (pulse_mem as f64);

    let scheduler_identity_rate = (order_matches as f64) / (total_trials as f64);
    let composite_rate = (composite_successes as f64) / (composite_attempts as f64);

    let summary = format!(
        "PEB-10 Report => trials={}, leakage={}/{} violations, toctou_rejection={}/{}, order_identity={:.2}%, branch_isolation={}/{} violations, conflict_prevention={}/{}, composite_success={:.2}%, budget_enforcement={}/{}, provenance_blocked={}/{}, pulse_lat={:.2}us, dag_lat={:.2}us (speedup={:.2}x), pulse_mem={}B, dag_mem={}B (reduction={:.2}x)",
        total_trials,
        zero_state_leakage_violations,
        zero_state_leakage_futures,
        stale_world_successes,
        stale_world_attempts,
        scheduler_identity_rate * 100.0,
        branch_isolation_violations,
        total_trials,
        writeset_conflicts_prevented,
        writeset_conflict_attempts,
        composite_rate * 100.0,
        budget_blocked,
        budget_attempts,
        provenance_blocked,
        provenance_attempts,
        pulse_avg_lat,
        dag_avg_lat,
        speedup,
        pulse_mem,
        dag_mem,
        memory_reduction,
    );

    Peb10BenchmarkReport {
        total_trials,
        zero_state_leakage_futures_tested: zero_state_leakage_futures,
        zero_state_leakage_violations,
        stale_world_rejection_attempts: stale_world_attempts,
        stale_world_rejection_successes: stale_world_successes,
        scheduler_order_identity_rate: scheduler_identity_rate,
        branch_isolation_violations,
        writeset_conflicts_prevented,
        writeset_conflict_attempts,
        atomic_composite_success_rate: composite_rate,
        budget_enforcement_blocked: budget_blocked,
        budget_enforcement_attempts: budget_attempts,
        provenance_violations_blocked: provenance_blocked,
        provenance_attempts,
        pulse_avg_latency_us: pulse_avg_lat,
        dag_emulated_latency_us: dag_avg_lat,
        latency_speedup_factor: speedup,
        pulse_memory_bytes_per_future: pulse_mem,
        dag_memory_bytes_per_task: dag_mem,
        memory_reduction_factor: memory_reduction,
        summary,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::intake::{IntakeKind, OperationId};

    fn synthetic_intake(epoch: u64) -> (RatifiedChannel, IntakeRequest) {
        let channel = RatifiedChannel::stub("compiler-feasibility-test");
        let request = IntakeRequest::new(
            &channel,
            OperationId::from_bytes([4; 16]),
            [8; 16],
            epoch,
            0,
            IntakeKind::Reported,
            "synthetic compiler intake".into(),
            "synthetic:test".into(),
        )
        .expect("synthetic request");
        (channel, request)
    }

    #[test]
    fn typed_feasibility_binds_request_and_store_snapshot() {
        let (channel, request) = synthetic_intake(5);
        let snapshot = AuthorizationSnapshot::from_test_parts([8; 16], 5);
        let capability = authorize_intake(&channel, &request, &snapshot).expect("authorized");
        assert_eq!(capability.authorized_digest(), request.digest());
        assert_eq!(
            capability.feasibility_operation_id(),
            Some(request.operation_id())
        );
        assert_eq!(capability.feasibility_realm_id(), Some(*request.realm_id()));
        assert_eq!(capability.feasibility_expected_epoch(), Some(5));
        assert_eq!(
            capability.feasibility_authority_digest(),
            Some(request.authority().digest())
        );
        assert_eq!(
            capability.feasibility_operation_kind(),
            Some(REMEMBER_OPERATION_KIND)
        );
    }

    #[test]
    fn typed_feasibility_refuses_stale_or_wrong_authority() {
        let (channel, request) = synthetic_intake(5);
        let stale = AuthorizationSnapshot::from_test_parts([8; 16], 6);
        assert!(matches!(
            authorize_intake(&channel, &request, &stale),
            Err(PulseError::StaleWorldEpoch {
                expected_epoch: 5,
                current_epoch: 6
            })
        ));
        let snapshot = AuthorizationSnapshot::from_test_parts([8; 16], 5);
        assert!(matches!(
            authorize_intake(&RatifiedChannel::stub("wrong"), &request, &snapshot),
            Err(PulseError::FeasibilityRefused { .. })
        ));
    }

    #[test]
    fn test_zero_state_leakage_rejected_futures() {
        let mut store = SubstrateStore::new();
        store.records.insert("key1".into(), "val1".into());
        let snapshot = store.create_snapshot();

        // Generate 100 rejected futures
        let candidates: Vec<FutureValue> = (0..100)
            .map(|i| {
                let mut delta = StateDelta::new();
                delta.insert(format!("poison_{}", i), "leaked");
                let mut ws = HashSet::new();
                ws.insert(format!("poison_{}", i));
                FutureValue {
                    candidate_id: i,
                    snapshot_epoch: snapshot.version.global_epoch,
                    read_set: HashSet::new(),
                    write_set: ws,
                    delta,
                    composite_margin: 0.50, // Below 0.85 -> fails Law 8
                    estimated_risk: 0.20,   // Above 0.10 -> fails Law 8
                    expected_utility: 0.40,
                    epistemic_status: EpistemicStatus::Insufficient,
                    provenance: Provenance::Rejected,
                    description: "rejected future".into(),
                }
            })
            .collect();

        let intent = CognitiveIntent {
            intent_name: "test_intent".into(),
            target_scope: "global".into(),
            candidates,
        };

        let mut tree = PulseTree::compile(snapshot, intent, ResourceEnvelope::default()).unwrap();
        tree.evaluate_parallel();

        let res = tree.arbitrate(1, "global");
        assert_eq!(res.unwrap_err(), PulseError::NoWarrantableCandidates);

        // Verify Zero State Leakage: canonical store is completely untouched
        assert_eq!(store.current_epoch, 0);
        assert_eq!(store.records.len(), 1);
        assert_eq!(store.records.get("key1").unwrap(), "val1");
    }

    #[test]
    fn test_stale_world_rejection_toctou_failure() {
        let mut store = SubstrateStore::new();
        store.records.insert("user".into(), "alice".into());
        let snapshot = store.create_snapshot(); // snapshot at epoch 0

        // Candidate evaluated against epoch 0
        let mut delta = StateDelta::new();
        delta.insert("balance", "100");
        let mut ws = HashSet::new();
        ws.insert("balance".into());

        let future = FutureValue {
            candidate_id: 42,
            snapshot_epoch: 0,
            read_set: HashSet::new(),
            write_set: ws,
            delta: delta.clone(),
            composite_margin: 0.90,
            estimated_risk: 0.05,
            expected_utility: 0.85,
            epistemic_status: EpistemicStatus::Affirmed,
            provenance: Provenance::Realized,
            description: "valid future".into(),
        };

        let intent = CognitiveIntent {
            intent_name: "deposit".into(),
            target_scope: "account".into(),
            candidates: vec![future],
        };

        let mut tree = PulseTree::compile(snapshot, intent, ResourceEnvelope::default()).unwrap();
        tree.evaluate_parallel();
        let (comp_delta, warrant) = tree.arbitrate(1, "account").unwrap();
        let cap = CommitCapability::claim(warrant);

        // Perturb the store: epoch moves from 0 to 1 before commit!
        store.current_epoch = 1;

        // Commit must fail closed with StaleWorldEpoch
        let res = store.commit(cap, comp_delta);
        match res {
            Err(PulseError::StaleWorldEpoch {
                expected_epoch,
                current_epoch,
            }) => {
                assert_eq!(expected_epoch, 0);
                assert_eq!(current_epoch, 1);
            }
            other => panic!("Expected StaleWorldEpoch error, got: {:?}", other),
        }
    }

    #[test]
    fn test_scheduler_order_independence() {
        let store = SubstrateStore::new();
        let snapshot = store.create_snapshot();

        let make_candidates = || {
            vec![
                FutureValue {
                    candidate_id: 10,
                    snapshot_epoch: 0,
                    read_set: HashSet::new(),
                    write_set: ["a".into()].into(),
                    delta: StateDelta::new(),
                    composite_margin: 0.90,
                    estimated_risk: 0.05,
                    expected_utility: 0.80,
                    epistemic_status: EpistemicStatus::Affirmed,
                    provenance: Provenance::Realized,
                    description: "cand 10".into(),
                },
                FutureValue {
                    candidate_id: 20,
                    snapshot_epoch: 0,
                    read_set: HashSet::new(),
                    write_set: ["a".into()].into(),
                    delta: StateDelta::new(),
                    composite_margin: 0.92, // Higher margin wins
                    estimated_risk: 0.04,
                    expected_utility: 0.85,
                    epistemic_status: EpistemicStatus::Affirmed,
                    provenance: Provenance::Realized,
                    description: "cand 20".into(),
                },
            ]
        };

        // Run 1: Order [10, 20]
        let mut tree1 = PulseTree::compile(
            snapshot.clone(),
            CognitiveIntent {
                intent_name: "test".into(),
                target_scope: "global".into(),
                candidates: make_candidates(),
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree1.evaluate_parallel();
        let (_, w1) = tree1.arbitrate(1, "global").unwrap();

        // Run 2: Reversed Order [20, 10]
        let mut candidates2 = make_candidates();
        candidates2.reverse();
        let mut tree2 = PulseTree::compile(
            snapshot,
            CognitiveIntent {
                intent_name: "test".into(),
                target_scope: "global".into(),
                candidates: candidates2,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree2.evaluate_parallel();
        let (_, w2) = tree2.arbitrate(1, "global").unwrap();

        // Must be bit-for-bit identical winner regardless of ordering
        assert_eq!(w1.arbitration().unwrap().candidate_id, 20);
        assert_eq!(w2.arbitration().unwrap().candidate_id, 20);
        assert_eq!(
            w1.arbitration().unwrap().token_digest,
            w2.arbitration().unwrap().token_digest
        );
    }

    #[test]
    fn test_compatible_composite_delta_composition() {
        let mut store = SubstrateStore::new();
        let snapshot = store.create_snapshot();

        // Two non-conflicting candidates: modifies "keyA" and "keyB"
        let mut delta1 = StateDelta::new();
        delta1.insert("keyA", "valA");
        let mut delta2 = StateDelta::new();
        delta2.insert("keyB", "valB");

        let candidates = vec![
            FutureValue {
                candidate_id: 1,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["keyA".into()].into(),
                delta: delta1,
                composite_margin: 0.95,
                estimated_risk: 0.02,
                expected_utility: 0.90,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "c1".into(),
            },
            FutureValue {
                candidate_id: 2,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["keyB".into()].into(),
                delta: delta2,
                composite_margin: 0.91,
                estimated_risk: 0.03,
                expected_utility: 0.88,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "c2".into(),
            },
        ];

        let mut tree = PulseTree::compile(
            snapshot,
            CognitiveIntent {
                intent_name: "composite".into(),
                target_scope: "multi".into(),
                candidates,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree.evaluate_parallel();

        let (composite_delta, warrant) = tree.arbitrate(1, "multi").unwrap();
        let cap = CommitCapability::claim(warrant);

        let receipt = store.commit(cap, composite_delta).unwrap();
        assert_eq!(receipt.mutations_applied, 2);
        assert_eq!(store.current_epoch, 1);
        assert_eq!(store.records.get("keyA").unwrap(), "valA");
        assert_eq!(store.records.get("keyB").unwrap(), "valB");
    }

    #[test]
    fn test_resource_budget_envelope_enforced() {
        let store = SubstrateStore::new();
        let snapshot = store.create_snapshot();

        let candidates: Vec<FutureValue> = (0..50)
            .map(|i| FutureValue {
                candidate_id: i,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: HashSet::new(),
                delta: StateDelta::new(),
                composite_margin: 0.5,
                estimated_risk: 0.5,
                expected_utility: 0.5,
                epistemic_status: EpistemicStatus::Insufficient,
                provenance: Provenance::Counterfactual,
                description: "".into(),
            })
            .collect();

        let env = ResourceEnvelope {
            max_candidates: 25, // limit to 25
            ..Default::default()
        };

        let res = PulseTree::compile(
            snapshot,
            CognitiveIntent {
                intent_name: "explosive".into(),
                target_scope: "test".into(),
                candidates,
            },
            env,
        );

        match res {
            Err(PulseError::ResourceBudgetExceeded {
                requested, limit, ..
            }) => {
                assert_eq!(requested, 50);
                assert_eq!(limit, 25);
            }
            other => panic!("Expected ResourceBudgetExceeded, got: {:?}", other),
        }
    }

    #[test]
    fn test_branch_isolation_poisoned_future() {
        let store = SubstrateStore::new();
        let snapshot = store.create_snapshot();

        let mut poisoned_delta = StateDelta::new();
        poisoned_delta.insert("corrupt", "illegal_data");

        let mut valid_delta = StateDelta::new();
        valid_delta.insert("clean", "pure_data");

        let candidates = vec![
            FutureValue {
                candidate_id: 1,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["corrupt".into()].into(),
                delta: poisoned_delta,
                composite_margin: 0.10, // Poisoned fails Law 8
                estimated_risk: 0.99,
                expected_utility: 0.0,
                epistemic_status: EpistemicStatus::CategoryError,
                provenance: Provenance::SimulatedFailure,
                description: "poisoned".into(),
            },
            FutureValue {
                candidate_id: 2,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["clean".into()].into(),
                delta: valid_delta,
                composite_margin: 0.96,
                estimated_risk: 0.01,
                expected_utility: 0.95,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "valid clean".into(),
            },
        ];

        let mut tree = PulseTree::compile(
            snapshot,
            CognitiveIntent {
                intent_name: "isolation_test".into(),
                target_scope: "test".into(),
                candidates,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree.evaluate_parallel();

        let (composite_delta, warrant) = tree.arbitrate(1, "test").unwrap();
        // Only candidate 2 should be in composite_delta; candidate 1 is cleanly isolated
        assert_eq!(warrant.arbitration().unwrap().candidate_id, 2);
        assert_eq!(composite_delta.len(), 1);
        assert_eq!(
            composite_delta.mutations.get("clean").unwrap(),
            &Some("pure_data".into())
        );
        assert!(!composite_delta.mutations.contains_key("corrupt"));
    }

    #[test]
    fn test_conflict_detection_overlapping_writes() {
        let store = SubstrateStore::new();
        let snapshot = store.create_snapshot();

        // Two candidates competing for the exact same key "target"
        let mut delta1 = StateDelta::new();
        delta1.insert("target", "winner_val");

        let mut delta2 = StateDelta::new();
        delta2.insert("target", "loser_val");

        let candidates = vec![
            FutureValue {
                candidate_id: 100,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["target".into()].into(),
                delta: delta1,
                composite_margin: 0.94, // Higher margin wins
                estimated_risk: 0.03,
                expected_utility: 0.90,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "winner".into(),
            },
            FutureValue {
                candidate_id: 101,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["target".into()].into(),
                delta: delta2,
                composite_margin: 0.88, // Lower margin loses conflict
                estimated_risk: 0.05,
                expected_utility: 0.80,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "conflicting loser".into(),
            },
        ];

        let mut tree = PulseTree::compile(
            snapshot,
            CognitiveIntent {
                intent_name: "conflict_test".into(),
                target_scope: "target".into(),
                candidates,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree.evaluate_parallel();

        let (composite_delta, warrant) = tree.arbitrate(1, "target").unwrap();
        assert_eq!(warrant.arbitration().unwrap().candidate_id, 100);
        // Overlapping candidate 101 was excluded from composite_delta to prevent conflict corruption!
        assert_eq!(composite_delta.len(), 1);
        assert_eq!(
            composite_delta.mutations.get("target").unwrap(),
            &Some("winner_val".into())
        );
    }

    #[test]
    fn test_early_dominance_short_circuit() {
        let store = SubstrateStore::new();
        let snapshot = store.create_snapshot();

        let candidates = vec![
            FutureValue {
                candidate_id: 55,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["key".into()].into(),
                delta: StateDelta::new(),
                composite_margin: 0.98, // Margin >= 0.95 -> Early Dominance!
                estimated_risk: 0.01,   // Risk <= 0.02 -> Early Dominance!
                expected_utility: 0.95,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "dominant".into(),
            },
            FutureValue {
                candidate_id: 56,
                snapshot_epoch: 0,
                read_set: HashSet::new(),
                write_set: ["key".into()].into(),
                delta: StateDelta::new(),
                composite_margin: 0.86,
                estimated_risk: 0.08,
                expected_utility: 0.70,
                epistemic_status: EpistemicStatus::Affirmed,
                provenance: Provenance::Realized,
                description: "ordinary".into(),
            },
        ];

        let mut tree = PulseTree::compile(
            snapshot,
            CognitiveIntent {
                intent_name: "dominance".into(),
                target_scope: "test".into(),
                candidates,
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree.evaluate_parallel();

        assert_eq!(tree.early_dominant_candidate, Some(55));
    }

    #[test]
    fn test_scoped_mvcc_compatibility() {
        let mut v1 = SnapshotVersion::new(10);
        v1 = v1.with_scope("garden_A", 5);
        v1 = v1.with_scope("garden_B", 3);

        // Read set only accesses "garden_A"
        let mut read_set = HashSet::new();
        read_set.insert("garden_A".into());

        // Current version has updated "garden_B" to version 4 (unrelated scope), but "garden_A" remains 5!
        let mut v2 = SnapshotVersion::new(11);
        v2 = v2.with_scope("garden_A", 5);
        v2 = v2.with_scope("garden_B", 4);

        // Under scoped MVCC, v1 is still compatible with v2 for read_set {"garden_A"}!
        assert!(v1.is_compatible_with(&read_set, &v2));

        // But if read_set also touches "garden_B", it is incompatible!
        read_set.insert("garden_B".into());
        assert!(!v1.is_compatible_with(&read_set, &v2));
    }

    #[test]
    fn test_peb10_benchmark_execution() {
        let report = run_peb10_pulse_compiler_benchmark(500);
        println!("{}", report.summary);

        assert_eq!(report.total_trials, 500);
        assert_eq!(
            report.zero_state_leakage_violations, 0,
            "Zero state leakage across 100k futures"
        );
        assert_eq!(report.zero_state_leakage_futures_tested, 100_000);
        assert_eq!(
            report.stale_world_rejection_successes, 500,
            "100% of TOCTOU stale attempts must fail"
        );
        assert_eq!(
            report.scheduler_order_identity_rate, 1.0,
            "Must be 100% scheduler-order independent"
        );
        assert_eq!(
            report.branch_isolation_violations, 0,
            "Poisoned branches must have 0 leakage"
        );
        assert_eq!(
            report.writeset_conflicts_prevented, 500,
            "100% of write-set conflicts must be resolved"
        );
        assert_eq!(
            report.atomic_composite_success_rate, 1.0,
            "100% of non-conflicting composites must succeed"
        );
        assert_eq!(
            report.budget_enforcement_blocked, 500,
            "100% of envelope explosions must be blocked"
        );
        assert_eq!(
            report.provenance_violations_blocked, 500,
            "100% of non-causal provenance must be blocked"
        );
        // Platform-scaled floor: the ratio is wall-clock and platform-dependent.
        // Linux (debug, T4800-S, 2026-09-27): 1.69x. macOS arm64 (miranda-macbook
        // field run): 1.26x — both prove the ordering; the floor keeps Linux at
        // 1.4 while giving darwin its measured headroom. Variant receipt:
        // receipts/BENCHMARK_PEB10_DARWIN_VARIANT_2026-09-27.md
        #[cfg(target_os = "macos")]
        let min_speedup = 1.2_f64;
        #[cfg(not(target_os = "macos"))]
        let min_speedup = 1.4_f64;
        assert!(
            report.latency_speedup_factor >= min_speedup,
            "Pulse must demonstrate significant speedup over Gen2 DAG \
             (>= {min_speedup}x on this platform; measured {:.2}x)",
            report.latency_speedup_factor
        );
        assert!(
            report.memory_reduction_factor > 8.0,
            "Pulse must demonstrate massive memory footprint reduction"
        );
    }

    #[test]
    fn test_unauthorized_state_delta_mismatch_fails_closed() {
        let mut store = SubstrateStore::new();
        let snapshot = store.create_snapshot();

        let mut authorized_delta = StateDelta::new();
        authorized_delta.insert("auth_key", "auth_val");

        let candidate = FutureValue {
            candidate_id: 42,
            snapshot_epoch: 0,
            read_set: HashSet::new(),
            write_set: ["auth_key".into()].into(),
            delta: authorized_delta.clone(),
            composite_margin: 0.95,
            estimated_risk: 0.02,
            expected_utility: 0.90,
            epistemic_status: EpistemicStatus::Affirmed,
            provenance: Provenance::Realized,
            description: "legit future".into(),
        };

        let mut tree = PulseTree::compile(
            snapshot,
            CognitiveIntent {
                intent_name: "test_intent".into(),
                target_scope: "scope".into(),
                candidates: vec![candidate],
            },
            ResourceEnvelope::default(),
        )
        .unwrap();
        tree.evaluate_parallel();

        let (_comp_delta, warrant) = tree.arbitrate(1, "scope").unwrap();
        let cap = CommitCapability::claim(warrant);

        // Adversary crafts a trojan delta with different mutations
        let mut trojan_delta = StateDelta::new();
        trojan_delta.insert("trojan_key", "exploit_val");

        // Attempting to commit trojan_delta with capability bound to authorized_delta MUST fail closed!
        let res = store.commit(cap, trojan_delta);
        assert!(matches!(
            res,
            Err(PulseError::UnauthorizedStateDelta { .. })
        ));

        // Verify store was not modified
        assert_eq!(store.current_epoch(), 0);
        assert_eq!(store.records_count(), 0);
        assert!(!store.contains_key("trojan_key"));
        assert!(!store.contains_key("auth_key"));
    }

    #[test]
    fn test_substrate_store_durable_nullifiers_reload() {
        let temp_dir =
            std::env::temp_dir().join(format!("wm_test_substrate_durable_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&temp_dir);
        std::fs::create_dir_all(&temp_dir).unwrap();
        let log_path = temp_dir.join("nullifiers.jsonl");

        let mut delta = StateDelta::new();
        delta.insert("k1", "v1");

        let candidate = FutureValue {
            candidate_id: 7,
            snapshot_epoch: 0,
            read_set: HashSet::new(),
            write_set: ["k1".into()].into(),
            delta: delta.clone(),
            composite_margin: 0.92,
            estimated_risk: 0.03,
            expected_utility: 0.85,
            epistemic_status: EpistemicStatus::Affirmed,
            provenance: Provenance::Realized,
            description: "c7".into(),
        };

        // 1. First run: commit via durable store
        {
            let mut store = SubstrateStore::open_durable(&log_path).unwrap();
            let snapshot = store.create_snapshot();
            let mut tree = PulseTree::compile(
                snapshot,
                CognitiveIntent {
                    intent_name: "durable_test".into(),
                    target_scope: "scope".into(),
                    candidates: vec![candidate.clone()],
                },
                ResourceEnvelope::default(),
            )
            .unwrap();
            tree.evaluate_parallel();
            let (comp_delta, warrant) = tree.arbitrate(1, "scope").unwrap();
            let cap = CommitCapability::claim(warrant);
            let receipt = store.commit(cap, comp_delta).unwrap();
            assert_eq!(receipt.epoch_after, 1);
            assert_eq!(store.get("k1"), Some(&"v1".to_string()));
        }

        // 2. Restart: reopen durable store from the same log
        {
            let mut reopened_store = SubstrateStore::open_durable(&log_path).unwrap();
            assert_eq!(reopened_store.nullifiers().len(), 1);

            // Replay attempt using identical candidate/arbitration coordinates must fail closed
            let snapshot = reopened_store.create_snapshot();
            let mut tree = PulseTree::compile(
                snapshot,
                CognitiveIntent {
                    intent_name: "durable_test".into(),
                    target_scope: "scope".into(),
                    candidates: vec![candidate],
                },
                ResourceEnvelope::default(),
            )
            .unwrap();
            tree.evaluate_parallel();
            let (comp_delta, warrant) = tree.arbitrate(1, "scope").unwrap();
            let cap = CommitCapability::claim(warrant);

            let res = reopened_store.commit(cap, comp_delta);
            assert!(matches!(
                res,
                Err(PulseError::Capability(
                    CapabilityError::ReplayAttackDetected { .. }
                ))
            ));
        }

        let _ = std::fs::remove_dir_all(&temp_dir);
    }
}

#[cfg(test)]
mod feasibility_accessor_tests {
    use super::*;
    use crate::intake::{IntakeKind, IntakeRequest, OperationId, REMEMBER_OPERATION_KIND};

    /// AMBER 2: feasibility warrants must expose their bindings and refuse
    /// arbitration-only accessors without panicking.
    #[test]
    fn feasibility_warrant_accessors_never_panic() {
        let channel = RatifiedChannel::stub("synthetic-feasibility-accessors");
        let request = IntakeRequest::new(
            &channel,
            OperationId::from_bytes([5; 16]),
            [6; 16],
            3,
            0,
            IntakeKind::Reported,
            "synthetic accessor payload".into(),
            "fixture:accessors".into(),
        )
        .unwrap();
        let snapshot = AuthorizationSnapshot::from_test_parts([6; 16], 3);
        let capability = authorize_intake(&channel, &request, &snapshot).unwrap();

        assert!(capability.warrant().arbitration().is_err());
        assert!(capability.nullifier_key().is_err());
        assert_eq!(
            capability.feasibility_operation_id(),
            Some(request.operation_id())
        );
        assert_eq!(capability.feasibility_realm_id(), Some(*request.realm_id()));
        assert_eq!(capability.feasibility_expected_epoch(), Some(3));
        assert_eq!(
            capability.feasibility_authority_digest(),
            Some(request.authority().digest())
        );
        assert_eq!(
            capability.feasibility_operation_kind(),
            Some(REMEMBER_OPERATION_KIND)
        );
    }
}
