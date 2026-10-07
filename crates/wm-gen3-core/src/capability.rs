//! wm-gen3-core::capability — Affine Capability Security, Verified Warrants,
//! Replay-Protection Nullifiers, and Transactional Commit Ratchets.
//!
//! # The (3 | 1) Factorization
//! ```text
//! [Select -> Transform -> Evaluate] | Commit(CommitCapability)
//!       (epistemic, reversible)     | (causal, irreversible)
//! ```
//!
//! - `VerifiedWarrant`: Opaque token constructible ONLY by `CorpusCallosum::arbitrate`.
//!   Guarantees all three Law 8 invariants: `Margin >= 0.85`, `Risk <= 0.10`, `Status == K1`.
//! - `CommitCapability`: Linear/affine token. Cannot be cloned or copied.
//!   Consumed upon commit ($C_{\text{commit}} \to \varnothing$).
//! - `NullifierSet`: Replay protection tracking `(epoch, sequence_id, token_digest)`.
//! - `execute_transactional_commit`: Enforces atomic transaction semantics:
//!   `verify + mutate + register nullifier + emit receipt`.

use std::collections::HashSet;
use std::fmt;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::bicameral::EpistemicStatus;
use crate::intake::OperationId;

#[derive(Debug, PartialEq, Clone)]
enum WarrantBasis {
    Arbitrated,
    Feasibility {
        operation_id: OperationId,
        realm_id: [u8; 16],
        expected_epoch: u64,
        authority_digest: [u8; 32],
        operation_kind: u8,
    },
    Mandala {
        pass_id: String,
        jti: String,
        slot_id: String,
        tenant_id: String,
    },
}

/// Errors arising in capability issuance, verification, or consumption.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum CapabilityError {
    /// Invariant failure: one or more statutory Law 8 conditions were not met.
    InvariantsUnmet {
        margin_bits: u64,
        risk_bits: u64,
        status: String,
        reason: String,
    },
    /// Replay attack: a warrant/capability with this nullifier was already consumed.
    ReplayAttackDetected {
        epoch: u64,
        sequence_id: u64,
        digest: [u8; 16],
    },
    /// Execution error during atomic state mutation.
    MutationFailed(String),
    /// Persistent storage failure on nullifier registration.
    PersistenceFailure(String),
    /// Mutation payload does not match authorized digest in warrant.
    UnauthorizedPayload {
        authorized: [u8; 32],
        presented: [u8; 32],
    },
    /// A capability was presented to an executor for a different issuance basis.
    WrongCapabilityBasis { required: String, actual: String },
    /// Boundary contract violation across subsystem or agent boundaries.
    BoundaryContractViolation {
        expected: String,
        actual: String,
        reason: String,
    },
}

impl fmt::Display for CapabilityError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvariantsUnmet { reason, .. } => {
                write!(f, "Capability Invariants Unmet: {}", reason)
            }
            Self::ReplayAttackDetected {
                epoch, sequence_id, ..
            } => {
                write!(
                    f,
                    "Replay Attack Detected: (epoch={}, seq={}) already consumed",
                    epoch, sequence_id
                )
            }
            Self::MutationFailed(msg) => write!(f, "Atomic Mutation Failed: {}", msg),
            Self::PersistenceFailure(msg) => write!(f, "Nullifier Persistence Failure: {}", msg),
            Self::UnauthorizedPayload {
                authorized,
                presented,
            } => {
                write!(
                    f,
                    "Unauthorized Mutation Payload: authorized {:?}, presented {:?}",
                    authorized, presented
                )
            }
            Self::WrongCapabilityBasis { required, actual } => {
                write!(
                    f,
                    "Wrong Capability Basis: required {required}, got {actual}"
                )
            }
            Self::BoundaryContractViolation {
                expected,
                actual,
                reason,
            } => {
                write!(
                    f,
                    "Boundary Contract Violation: expected {expected}, got {actual}: {reason}"
                )
            }
        }
    }
}

impl std::error::Error for CapabilityError {}

/// Typed representation categories for agent-to-agent and subsystem boundaries.
///
/// Enforces semantic boundaries to prevent subtle format degradation, covert side-channels,
/// and accidental belief-to-memory pollution.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum RepresentationType {
    /// Formatted, structured symbolic tokens (e.g. AST, JSON schemas, typed S-expressions).
    StructuredSymbolic,
    /// Continuous dense vector representation (e.g. latent activations, fastembed vectors).
    DenseVectorEmbedding,
    /// Explicit uncertainty or belief distribution over discrete propositions or world states.
    EpistemicBeliefDistribution,
    /// Discrete executable action specification with schema-validated parameters.
    DiscreteActionSpec,
    /// Unstructured natural language text.
    UnstructuredNaturalLanguage,
}

/// Boundary Contract enforcing representation typing and payload verification at subsystem boundaries.
///
/// Prevents covert side channels, semantic drift, and untyped belief pollution across agent boundaries.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BoundaryContract {
    pub contract_id: String,
    pub source_subsystem: String,
    pub target_subsystem: String,
    pub expected_representation: RepresentationType,
    pub enforce_digest_match: bool,
}

impl BoundaryContract {
    #[must_use]
    pub fn new(
        contract_id: impl Into<String>,
        source_subsystem: impl Into<String>,
        target_subsystem: impl Into<String>,
        expected_representation: RepresentationType,
    ) -> Self {
        Self {
            contract_id: contract_id.into(),
            source_subsystem: source_subsystem.into(),
            target_subsystem: target_subsystem.into(),
            expected_representation,
            enforce_digest_match: true,
        }
    }

    /// Verifies that an incoming handoff payload adheres to this boundary contract.
    pub fn verify_handoff(
        &self,
        actual_representation: RepresentationType,
        expected_digest: Option<[u8; 32]>,
        actual_payload: &[u8],
    ) -> Result<(), CapabilityError> {
        if actual_representation != self.expected_representation {
            return Err(CapabilityError::BoundaryContractViolation {
                expected: format!("{:?}", self.expected_representation),
                actual: format!("{:?}", actual_representation),
                reason: format!(
                    "Boundary contract '{}' failed: representation mismatch between {} -> {}",
                    self.contract_id, self.source_subsystem, self.target_subsystem
                ),
            });
        }

        if self.enforce_digest_match {
            if let Some(expected) = expected_digest {
                use sha2::{Digest, Sha256};
                let mut hasher = Sha256::new();
                hasher.update(actual_payload);
                let actual_digest: [u8; 32] = hasher.finalize().into();
                if actual_digest != expected {
                    return Err(CapabilityError::UnauthorizedPayload {
                        authorized: expected,
                        presented: actual_digest,
                    });
                }
            }
        }

        Ok(())
    }
}

/// An unforgeable, opaque witness issued exclusively by the Corpus Callosum.
///
/// Fields are strictly private to prevent external construction.
#[derive(Debug, PartialEq)]
pub struct VerifiedWarrant {
    candidate_id: Option<u64>,
    authorized_digest: [u8; 32],
    composite_margin: Option<f64>,
    estimated_risk: Option<f64>,
    epistemic_status: Option<EpistemicStatus>,
    epoch: u64,
    sequence_id: Option<u64>,
    token_digest: Option<[u8; 16]>,
    scope: String,
    basis: WarrantBasis,
    _private: (),
}

/// Borrowed, typed view of the fields that exist only for arbitration warrants.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ArbitrationWarrantView {
    pub candidate_id: u64,
    pub composite_margin: f64,
    pub estimated_risk: f64,
    pub epistemic_status: EpistemicStatus,
    pub epoch: u64,
    pub sequence_id: u64,
    pub token_digest: [u8; 16],
}

impl VerifiedWarrant {
    /// Mint a verified warrant. Strictly verifies ALL THREE Law 8 invariants:
    /// 1. `epistemic_status == EpistemicStatus::Affirmed` (K1 warrant)
    /// 2. `composite_margin >= 0.85` (High utility and success probability)
    /// 3. `estimated_risk <= 0.10` (Low operational risk)
    // Sealed mint mirrors the warrant fields one-to-one; grouping them would obscure the audit surface.
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn mint_from_arbitration(
        _seal: crate::pulse_compiler::CompilerSeal,
        candidate_id: u64,
        authorized_digest: [u8; 32],
        margin: f64,
        risk: f64,
        status: EpistemicStatus,
        epoch: u64,
        sequence_id: u64,
        token_digest: [u8; 16],
        scope: impl Into<String>,
    ) -> Result<Self, CapabilityError> {
        let is_affirmed = status == EpistemicStatus::Affirmed;
        let margin_ok = margin >= 0.85;
        let risk_ok = risk <= 0.10;

        if is_affirmed && margin_ok && risk_ok {
            Ok(Self {
                candidate_id: Some(candidate_id),
                authorized_digest,
                composite_margin: Some(margin),
                estimated_risk: Some(risk),
                epistemic_status: Some(status),
                epoch,
                sequence_id: Some(sequence_id),
                token_digest: Some(token_digest),
                scope: scope.into(),
                basis: WarrantBasis::Arbitrated,
                _private: (),
            })
        } else {
            let reason = format!(
                "Law 8 Violation: Affirmed={}, Margin={:.3}>=0.85 ({}), Risk={:.3}<=0.10 ({})",
                is_affirmed, margin, margin_ok, risk, risk_ok
            );
            Err(CapabilityError::InvariantsUnmet {
                margin_bits: margin.to_bits(),
                risk_bits: risk.to_bits(),
                status: status.to_string(),
                reason,
            })
        }
    }

    pub(crate) fn mint_from_feasibility(
        _seal: crate::pulse_compiler::CompilerSeal,
        authorized_digest: [u8; 32],
        operation_id: OperationId,
        realm_id: [u8; 16],
        expected_epoch: u64,
        authority_digest: [u8; 32],
        operation_kind: u8,
        scope: impl Into<String>,
    ) -> Self {
        Self {
            candidate_id: None,
            authorized_digest,
            composite_margin: None,
            estimated_risk: None,
            epistemic_status: None,
            epoch: expected_epoch,
            sequence_id: None,
            token_digest: None,
            scope: scope.into(),
            basis: WarrantBasis::Feasibility {
                operation_id,
                realm_id,
                expected_epoch,
                authority_digest,
                operation_kind,
            },
            _private: (),
        }
    }

    pub fn arbitration(&self) -> Result<ArbitrationWarrantView, CapabilityError> {
        match &self.basis {
            WarrantBasis::Arbitrated => Ok(ArbitrationWarrantView {
                candidate_id: self.candidate_id.ok_or_else(wrong_arbitration_basis)?,
                composite_margin: self.composite_margin.ok_or_else(wrong_arbitration_basis)?,
                estimated_risk: self.estimated_risk.ok_or_else(wrong_arbitration_basis)?,
                epistemic_status: self.epistemic_status.ok_or_else(wrong_arbitration_basis)?,
                epoch: self.epoch,
                sequence_id: self.sequence_id.ok_or_else(wrong_arbitration_basis)?,
                token_digest: self.token_digest.ok_or_else(wrong_arbitration_basis)?,
            }),
            WarrantBasis::Feasibility { .. } | WarrantBasis::Mandala { .. } => {
                Err(wrong_arbitration_basis())
            }
        }
    }

    #[must_use]
    pub fn epoch(&self) -> u64 {
        self.epoch
    }

    #[must_use]
    pub fn scope(&self) -> &str {
        &self.scope
    }

    #[must_use]
    pub fn authorized_digest(&self) -> [u8; 32] {
        self.authorized_digest
    }

    // Tuple is the feasibility basis itself; a type alias would just rename the same fields.
    #[allow(clippy::type_complexity)]
    fn feasibility(&self) -> Option<(OperationId, [u8; 16], u64, [u8; 32], u8)> {
        match &self.basis {
            WarrantBasis::Arbitrated | WarrantBasis::Mandala { .. } => None,
            WarrantBasis::Feasibility {
                operation_id,
                realm_id,
                expected_epoch,
                authority_digest,
                operation_kind,
            } => Some((
                *operation_id,
                *realm_id,
                *expected_epoch,
                *authority_digest,
                *operation_kind,
            )),
        }
    }

    pub(crate) fn mint_from_mandala_pass(
        _seal: crate::pulse_compiler::CompilerSeal,
        authorized_digest: [u8; 32],
        pass_id: String,
        jti: String,
        slot_id: String,
        tenant_id: String,
        epoch: u64,
        scope: impl Into<String>,
    ) -> Self {
        Self {
            candidate_id: None,
            authorized_digest,
            composite_margin: None,
            estimated_risk: None,
            epistemic_status: None,
            epoch,
            sequence_id: None,
            token_digest: None,
            scope: scope.into(),
            basis: WarrantBasis::Mandala {
                pass_id,
                jti,
                slot_id,
                tenant_id,
            },
            _private: (),
        }
    }

    #[must_use]
    pub fn mandala_pass_info(&self) -> Option<(&str, &str, &str, &str)> {
        match &self.basis {
            WarrantBasis::Mandala {
                pass_id,
                jti,
                slot_id,
                tenant_id,
            } => Some((
                pass_id.as_str(),
                jti.as_str(),
                slot_id.as_str(),
                tenant_id.as_str(),
            )),
            _ => None,
        }
    }
}

fn wrong_arbitration_basis() -> CapabilityError {
    CapabilityError::WrongCapabilityBasis {
        required: "arbitration".into(),
        actual: "feasibility".into(),
    }
}

/// A linear, affine capability token granting execution across the causal boundary.
///
/// # Affine & Concurrency Invariants
/// - Does NOT implement `Clone` or `Copy`.
/// - Passed by value into `execute_transactional_commit`, ensuring destruction upon use ($C \to \varnothing$).
/// - Does NOT implement `Send` or `Sync` (enforced via `PhantomData<*const ()>`).
///   Background tasks/threads CANNOT acquire or hold state mutation authority.
///
/// ```compile_fail
/// // Compile-time proof 1: Fields are private; cannot be forged externally.
/// use wm_gen3_core::capability::CommitCapability;
/// let cap = CommitCapability { warrant: todo!(), _affine: (), _not_send_sync: std::marker::PhantomData };
/// ```
///
/// ```compile_fail
/// // Compile-time proof 2: !Send; cannot be transferred to a background thread.
/// use wm_gen3_core::capability::CommitCapability;
/// fn assert_send<T: Send>() {}
/// assert_send::<CommitCapability>();
/// ```
///
/// ```compile_fail
/// // Compile-time proof 3: Not deserializable via serde; cannot be forged from wire data.
/// use wm_gen3_core::capability::CommitCapability;
/// serde_json::from_str::<CommitCapability>("{}");
/// ```
///
/// ```compile_fail
/// // Compile-time proof 4: !Sync; cannot be shared across concurrent threads or tasks.
/// use wm_gen3_core::capability::CommitCapability;
/// fn assert_sync<T: Sync>() {}
/// assert_sync::<CommitCapability>();
/// ```
#[must_use = "CommitCapability represents authorized causal execution and must be explicitly consumed"]
#[derive(Debug)]
pub struct CommitCapability {
    warrant: VerifiedWarrant,
    _affine: (),
    _not_send_sync: std::marker::PhantomData<*const ()>,
}

impl CommitCapability {
    /// Claims a CommitCapability from a valid `VerifiedWarrant`.
    pub fn claim(warrant: VerifiedWarrant) -> Self {
        Self {
            warrant,
            _affine: (),
            _not_send_sync: std::marker::PhantomData,
        }
    }

    #[must_use]
    pub fn warrant(&self) -> &VerifiedWarrant {
        &self.warrant
    }

    #[must_use]
    pub fn authorized_digest(&self) -> [u8; 32] {
        self.warrant.authorized_digest
    }

    #[must_use]
    pub fn scope(&self) -> &str {
        self.warrant.scope()
    }

    #[must_use]
    pub fn feasibility_operation_id(&self) -> Option<OperationId> {
        self.warrant.feasibility().map(|value| value.0)
    }

    #[must_use]
    pub fn feasibility_realm_id(&self) -> Option<[u8; 16]> {
        self.warrant.feasibility().map(|value| value.1)
    }

    #[must_use]
    pub fn feasibility_expected_epoch(&self) -> Option<u64> {
        self.warrant.feasibility().map(|value| value.2)
    }

    #[must_use]
    pub fn feasibility_authority_digest(&self) -> Option<[u8; 32]> {
        self.warrant.feasibility().map(|value| value.3)
    }

    #[must_use]
    pub fn feasibility_operation_kind(&self) -> Option<u8> {
        self.warrant.feasibility().map(|value| value.4)
    }

    #[must_use]
    pub fn mandala_pass_info(&self) -> Option<(&str, &str, &str, &str)> {
        self.warrant.mandala_pass_info()
    }

    pub fn nullifier_key(&self) -> Result<NullifierKey, CapabilityError> {
        let arbitration = self.warrant.arbitration()?;
        Ok(NullifierKey {
            epoch: arbitration.epoch,
            sequence_id: arbitration.sequence_id,
            token_digest: arbitration.token_digest,
        })
    }
}

/// Nullifier key identifying consumed capabilities for replay protection.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct NullifierKey {
    pub epoch: u64,
    pub sequence_id: u64,
    pub token_digest: [u8; 16],
}

/// An append-only registry of consumed capabilities preventing replay attacks.
/// Can be backed by durable on-disk storage to survive cold reboots.
#[derive(Debug, Default, Clone)]
pub struct NullifierSet {
    nullifiers: HashSet<NullifierKey>,
    persist_path: Option<PathBuf>,
}

impl NullifierSet {
    pub fn new() -> Self {
        Self {
            nullifiers: HashSet::new(),
            persist_path: None,
        }
    }

    /// Open or create a durable NullifierSet backed by an on-disk journal.
    /// Survives cold reboots: loads all previously committed nullifier keys.
    /// Fails closed if any journal entry is corrupt (zero silent skips).
    pub fn open_durable(path: impl AsRef<Path>) -> std::io::Result<Self> {
        let path = path.as_ref().to_path_buf();
        let mut nullifiers = HashSet::new();

        if path.exists() {
            let file = File::open(&path)?;
            let reader = BufReader::new(file);
            for (idx, line) in reader.lines().enumerate() {
                let l = line?;
                let trimmed = l.trim();
                if trimmed.is_empty() {
                    continue;
                }
                let key = serde_json::from_str::<NullifierKey>(trimmed).map_err(|e| {
                    std::io::Error::new(
                        std::io::ErrorKind::InvalidData,
                        format!("corrupt nullifier entry at line {}: {e}", idx + 1),
                    )
                })?;
                nullifiers.insert(key);
            }
        }

        Ok(Self {
            nullifiers,
            persist_path: Some(path),
        })
    }

    #[must_use]
    pub fn contains(&self, key: &NullifierKey) -> bool {
        self.nullifiers.contains(key)
    }

    pub fn register(&mut self, key: NullifierKey) -> Result<(), CapabilityError> {
        if self.nullifiers.contains(&key) {
            return Err(CapabilityError::ReplayAttackDetected {
                epoch: key.epoch,
                sequence_id: key.sequence_id,
                digest: key.token_digest,
            });
        }
        if let Some(ref path) = self.persist_path {
            let mut file = OpenOptions::new()
                .create(true)
                .append(true)
                .open(path)
                .map_err(|e| {
                    CapabilityError::PersistenceFailure(format!("journal open failed: {e}"))
                })?;
            let line = serde_json::to_string(&key).map_err(|e| {
                CapabilityError::PersistenceFailure(format!("serialization failed: {e}"))
            })?;
            writeln!(file, "{}", line).map_err(|e| {
                CapabilityError::PersistenceFailure(format!("journal write failed: {e}"))
            })?;
            file.sync_data().map_err(|e| {
                CapabilityError::PersistenceFailure(format!("journal fsync failed: {e}"))
            })?;
        }
        self.nullifiers.insert(key);
        Ok(())
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.nullifiers.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.nullifiers.is_empty()
    }
}

/// Permanent receipt emitted upon successful transactional commit.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CommitReceipt {
    pub candidate_id: u64,
    pub epoch: u64,
    pub sequence_id: u64,
    pub token_digest: [u8; 16],
    pub committed_at_ns: u64,
}

/// Atomically executes a state transition across the causal boundary.
///
/// Guarantees exact transactional semantics:
/// `verify replay + write-ahead nullifier persistence + execute mutation + emit receipt`.
/// Nullifier is durably recorded prior to state transition; if persistence fails,
/// mutation is NEVER executed (fail-closed).
pub fn execute_transactional_commit<T, F>(
    capability: CommitCapability,
    nullifiers: &mut NullifierSet,
    mutation: F,
) -> Result<(CommitReceipt, T), CapabilityError>
where
    F: FnOnce() -> Result<T, CapabilityError>,
{
    let arbitration = capability.warrant.arbitration()?;
    let key = capability.nullifier_key()?;

    // 1. Replay check
    if nullifiers.contains(&key) {
        return Err(CapabilityError::ReplayAttackDetected {
            epoch: key.epoch,
            sequence_id: key.sequence_id,
            digest: key.token_digest,
        });
    }

    // 2. Durable write-ahead nullifier registration (fsync first)
    // If journal persistence fails, mutation is NEVER executed!
    nullifiers.register(key)?;

    // 3. Perform state mutation
    match mutation() {
        Ok(output) => {
            let receipt = CommitReceipt {
                candidate_id: arbitration.candidate_id,
                epoch: arbitration.epoch,
                sequence_id: arbitration.sequence_id,
                token_digest: arbitration.token_digest,
                committed_at_ns: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map(|d| d.as_nanos() as u64)
                    .unwrap_or(0),
            };
            Ok((receipt, output))
        }
        Err(e) => {
            // Mutation failed after nullifier was registered.
            // The capability token is permanently burned and cannot be replayed.
            Err(e)
        }
    }
}

// -----------------------------------------------------------------------------
// TOPOLOGICAL METRICS & DYNAMICAL TRANSITION FRICTION
// -----------------------------------------------------------------------------

/// Canonical Spectral Distance: Euclidean distance in the Laplacian eigenspace.
///
/// Answers: "How far apart are these attractors geometrically?"
#[must_use]
pub fn spectral_distance(v_i: &[f64], v_j: &[f64]) -> f64 {
    v_i.iter()
        .zip(v_j.iter())
        .map(|(a, b)| (a - b).powi(2))
        .sum::<f64>()
        .sqrt()
}

/// Directed Transition Friction: Asymmetric dynamical cost of moving $i \to j$.
///
/// Answers: "How difficult is it for dynamics to move from attractor $i$ to attractor $j$?"
/// Note: $C(i \to j) \neq C(j \to i)$ in general; does not obey the triangle inequality.
#[must_use]
pub fn transition_friction(p_ij: f64) -> f64 {
    (1.0 - p_ij).clamp(0.0, 1.0)
}

/// Bagua Hypercube Distance: Combinatorial 3-bit Hamming distance hypothesis.
///
/// Answers: "Can a 3-bit combinatorial hypercube predict transition friction?"
#[must_use]
pub fn bagua_hamming_distance(basin_i: usize, basin_j: usize) -> f64 {
    ((basin_i ^ basin_j) as u32).count_ones() as f64
}

#[cfg(test)]
pub mod tests {
    use super::*;
    use crate::evidence::RatifiedChannel;
    use crate::intake::{IntakeKind, IntakeRequest, OperationId};
    use crate::pulse_compiler::{AuthorizationSnapshot, authorize_intake};

    #[test]
    fn basis_views_are_typed_and_wrong_executor_fails_before_mutation() {
        let arbitrated = VerifiedWarrant::mint_from_arbitration(
            crate::pulse_compiler::CompilerSeal::for_test(),
            7,
            [1; 32],
            0.9,
            0.05,
            EpistemicStatus::Affirmed,
            3,
            11,
            [2; 16],
            "synthetic.arbitration",
        )
        .unwrap();
        let view = arbitrated.arbitration().unwrap();
        assert_eq!(view.candidate_id, 7);
        assert_eq!(view.sequence_id, 11);

        let channel = RatifiedChannel::stub("synthetic-feasibility");
        let request = IntakeRequest::new(
            &channel,
            OperationId::from_bytes([3; 16]),
            [4; 16],
            0,
            0,
            IntakeKind::Reported,
            "synthetic".into(),
            "fixture".into(),
        )
        .unwrap();
        let snapshot = AuthorizationSnapshot::from_test_parts([4; 16], 0);
        let capability = authorize_intake(&channel, &request, &snapshot).unwrap();
        assert!(matches!(
            capability.warrant().arbitration(),
            Err(CapabilityError::WrongCapabilityBasis { .. })
        ));
        assert!(matches!(
            capability.nullifier_key(),
            Err(CapabilityError::WrongCapabilityBasis { .. })
        ));

        let capability = authorize_intake(&channel, &request, &snapshot).unwrap();
        let mut nullifiers = NullifierSet::new();
        let mut mutated = false;
        let result = execute_transactional_commit(capability, &mut nullifiers, || {
            mutated = true;
            Ok(())
        });
        assert!(matches!(
            result,
            Err(CapabilityError::WrongCapabilityBasis { .. })
        ));
        assert!(!mutated);
        assert!(nullifiers.is_empty());
    }

    #[test]
    fn test_warrant_invariants_enforced() {
        let auth_digest = [0u8; 32];
        let digest = [1u8; 16];

        // Valid: Affirmed, Margin >= 0.85, Risk <= 0.10
        let valid = VerifiedWarrant::mint_from_arbitration(
            crate::pulse_compiler::CompilerSeal::for_test(),
            1,
            auth_digest,
            0.90,
            0.05,
            EpistemicStatus::Affirmed,
            1,
            101,
            digest,
            "core.test",
        );
        assert!(valid.is_ok());

        // Invalid: High risk (> 0.10)
        let high_risk = VerifiedWarrant::mint_from_arbitration(
            crate::pulse_compiler::CompilerSeal::for_test(),
            2,
            auth_digest,
            0.95,
            0.25,
            EpistemicStatus::Affirmed,
            1,
            102,
            digest,
            "core.test",
        );
        assert!(high_risk.is_err());

        // Invalid: Low margin (< 0.85)
        let low_margin = VerifiedWarrant::mint_from_arbitration(
            crate::pulse_compiler::CompilerSeal::for_test(),
            3,
            auth_digest,
            0.75,
            0.02,
            EpistemicStatus::Affirmed,
            1,
            103,
            digest,
            "core.test",
        );
        assert!(low_margin.is_err());

        // Invalid: Contradiction (K3) even with high margin and low risk
        let contradiction = VerifiedWarrant::mint_from_arbitration(
            crate::pulse_compiler::CompilerSeal::for_test(),
            4,
            auth_digest,
            0.99,
            0.01,
            EpistemicStatus::Contradiction,
            1,
            104,
            digest,
            "core.test",
        );
        assert!(contradiction.is_err());
    }

    #[test]
    fn test_transactional_commit_and_replay_protection() {
        let auth_digest = [99u8; 32];
        let digest = [42u8; 16];
        let warrant = VerifiedWarrant::mint_from_arbitration(
            crate::pulse_compiler::CompilerSeal::for_test(),
            10,
            auth_digest,
            0.92,
            0.04,
            EpistemicStatus::Affirmed,
            1,
            555,
            digest,
            "sub.pulse",
        )
        .expect("Should mint valid warrant");

        let capability = CommitCapability::claim(warrant);
        assert_eq!(capability.authorized_digest(), auth_digest);
        let mut nullifiers = NullifierSet::new();

        let mut side_effect_counter = 0;

        // First execution succeeds
        let (receipt, _) = execute_transactional_commit(capability, &mut nullifiers, || {
            side_effect_counter += 1;
            Ok(())
        })
        .expect("Transaction must commit");

        assert_eq!(receipt.candidate_id, 10);
        assert_eq!(receipt.epoch, 1);
        assert_eq!(receipt.sequence_id, 555);
        assert_eq!(side_effect_counter, 1);
        assert_eq!(nullifiers.len(), 1);

        // Replay attempt with forged/identical warrant fails
        let warrant_replay = VerifiedWarrant::mint_from_arbitration(
            crate::pulse_compiler::CompilerSeal::for_test(),
            10,
            auth_digest,
            0.92,
            0.04,
            EpistemicStatus::Affirmed,
            1,
            555,
            digest,
            "sub.pulse",
        )
        .expect("Should mint warrant with same replay coords");
        let capability_replay = CommitCapability::claim(warrant_replay);

        let replay_result =
            execute_transactional_commit(capability_replay, &mut nullifiers, || {
                side_effect_counter += 1;
                Ok(())
            });

        assert!(matches!(
            replay_result,
            Err(CapabilityError::ReplayAttackDetected { .. })
        ));
        assert_eq!(
            side_effect_counter, 1,
            "Side effect must not execute on replay"
        );
    }

    #[test]
    fn test_failed_mutation_burns_capability_and_prevents_replay() {
        let auth_digest = [1u8; 32];
        let digest = [7u8; 16];
        let warrant = VerifiedWarrant::mint_from_arbitration(
            crate::pulse_compiler::CompilerSeal::for_test(),
            20,
            auth_digest,
            0.88,
            0.08,
            EpistemicStatus::Affirmed,
            2,
            777,
            digest,
            "sub.pulse",
        )
        .expect("Valid warrant");
        let capability = CommitCapability::claim(warrant);
        let mut nullifiers = NullifierSet::new();

        let failure_result: Result<(CommitReceipt, ()), CapabilityError> =
            execute_transactional_commit(capability, &mut nullifiers, || {
                Err(CapabilityError::MutationFailed("Simulated failure".into()))
            });

        assert!(failure_result.is_err());
        assert_eq!(
            nullifiers.len(),
            1,
            "Nullifier is burned to prevent replay of failed capability"
        );
    }

    #[test]
    fn test_nullifier_durable_corrupt_entry_fails_closed() {
        let temp_dir =
            std::env::temp_dir().join(format!("wm_test_corrupt_nullifiers_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&temp_dir);
        std::fs::create_dir_all(&temp_dir).unwrap();
        let log_path = temp_dir.join("nullifiers.jsonl");

        // Write corrupt garbage line
        std::fs::write(&log_path, "NOT_VALID_JSON_NULLIFIER_LINE\n").unwrap();

        // Must fail closed with InvalidData
        let res = NullifierSet::open_durable(&log_path);
        assert!(res.is_err());
        assert_eq!(res.unwrap_err().kind(), std::io::ErrorKind::InvalidData);

        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_nullifier_persistence_failure_prevents_mutation() {
        let temp_dir =
            std::env::temp_dir().join(format!("wm_test_unwritable_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&temp_dir);
        std::fs::create_dir_all(&temp_dir).unwrap();

        let log_path = temp_dir.join("nullifiers.jsonl");
        // Create the file first so metadata and set_permissions succeed
        std::fs::write(&log_path, b"").unwrap();
        let mut set = NullifierSet::open_durable(&log_path).unwrap();

        // Make the file read-only so append fails with PermissionDenied
        let mut perms = std::fs::metadata(&log_path).unwrap().permissions();
        perms.set_readonly(true);
        std::fs::set_permissions(&log_path, perms).unwrap();

        let key = NullifierKey {
            epoch: 1,
            sequence_id: 1,
            token_digest: [1u8; 16],
        };

        let err = set.register(key);
        assert!(matches!(err, Err(CapabilityError::PersistenceFailure(_))));
        assert!(
            !set.contains(&key),
            "Unpersisted nullifier must not be registered"
        );

        // Restore write permissions for cleanup
        let mut perms = std::fs::metadata(&log_path).unwrap().permissions();
        // Clearing the read-only bit is intentional cleanup before directory removal.
        #[allow(clippy::permissions_set_readonly_false)]
        perms.set_readonly(false);
        let _ = std::fs::set_permissions(&log_path, perms);
        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_topological_metrics_and_directed_asymmetry() {
        let v1 = [0.1, 0.5, 0.9];
        let v2 = [0.1, 0.5, 0.9];
        assert!((spectral_distance(&v1, &v2)).abs() < 1e-6);

        // Dynamical asymmetry: P(1 -> 2) = 0.80 vs P(2 -> 1) = 0.05
        let c_12 = transition_friction(0.80);
        let c_21 = transition_friction(0.05);
        assert!(
            c_12 < c_21,
            "C(1->2) must be significantly lower than C(2->1)"
        );
        assert!((c_12 - 0.20).abs() < 1e-6);
        assert!((c_21 - 0.95).abs() < 1e-6);

        // Bagua Hamming distance
        assert_eq!(bagua_hamming_distance(0b000, 0b001), 1.0);
        assert_eq!(bagua_hamming_distance(0b000, 0b011), 2.0);
        assert_eq!(bagua_hamming_distance(0b000, 0b111), 3.0);
    }

    #[test]
    fn test_nullifier_durable_reload_survives_restart() {
        let temp_dir =
            std::env::temp_dir().join(format!("wm_test_nullifiers_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&temp_dir);
        std::fs::create_dir_all(&temp_dir).unwrap();
        let nullifier_log = temp_dir.join("nullifiers.jsonl");

        let key = NullifierKey {
            epoch: 1,
            sequence_id: 42,
            token_digest: [9u8; 16],
        };

        // 1. First lifecycle: register nullifier and write to durable log
        {
            let mut set = NullifierSet::open_durable(&nullifier_log).unwrap();
            assert!(!set.contains(&key));
            set.register(key).unwrap();
            assert!(set.contains(&key));
        }

        // 2. Cold reboot: reload from disk
        {
            let mut set_reloaded = NullifierSet::open_durable(&nullifier_log).unwrap();
            assert!(set_reloaded.contains(&key));
            // Replay attempt after reload fails
            let err = set_reloaded.register(key);
            assert!(matches!(
                err,
                Err(CapabilityError::ReplayAttackDetected { .. })
            ));
        }

        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_boundary_contract_verification() {
        use sha2::{Digest, Sha256};
        let contract = BoundaryContract::new(
            "bc-sim-to-arb",
            "SimulationSubsystem",
            "ArbiterSubsystem",
            RepresentationType::DiscreteActionSpec,
        );

        let valid_payload = b"{\"action\":\"commit_hypothesis\",\"candidate_id\":123}";
        let mut hasher = Sha256::new();
        hasher.update(valid_payload);
        let digest: [u8; 32] = hasher.finalize().into();

        // 1. Valid handoff matches representation and digest
        assert!(
            contract
                .verify_handoff(
                    RepresentationType::DiscreteActionSpec,
                    Some(digest),
                    valid_payload
                )
                .is_ok()
        );

        // 2. Representation mismatch fails with BoundaryContractViolation
        let repr_err = contract.verify_handoff(
            RepresentationType::UnstructuredNaturalLanguage,
            Some(digest),
            valid_payload,
        );
        assert!(matches!(
            repr_err,
            Err(CapabilityError::BoundaryContractViolation { .. })
        ));

        // 3. Payload corruption fails with UnauthorizedPayload
        let corrupted_payload = b"{\"action\":\"tampered_payload\"}";
        let digest_err = contract.verify_handoff(
            RepresentationType::DiscreteActionSpec,
            Some(digest),
            corrupted_payload,
        );
        assert!(matches!(
            digest_err,
            Err(CapabilityError::UnauthorizedPayload { .. })
        ));
    }
}
