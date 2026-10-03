//! wm-gen3-core::contract — The Gen3 Kernel Contract (API).
//!
//! # Kernel contract models
//! This module models parts of the `GEN3_KERNEL_CONTRACT` required by PEB-15.
//! `KernelStore` is available only for tests or with `reference-models`; it is not
//! the authoritative LMDB store. Its tests do not establish recovery or authority
//! enforcement for every production operation.
//!
//! # Articles of Encapsulation
//! 1. Model State Mutation: through [`crate::capability::CommitCapability`].
//! 2. Remote Input: ONLY [`RemoteStimulus`]. Foreign data carries zero execution authority.
//! 3. Foreign Confidence: Never enters local calibration pools.
//! 4. Background Execution: Physical I/O and listening only. Zero cognitive/scheduling authority.
//! 5. Canonical Identity: Root cryptographic provenance (Ed25519), never socket/IP.
//! 6. Historical Causality: Passive Merkle DAG ancestry. Clocks carry zero causal authority.
//! 7. Shared Hologram: Derived projection index only. Fail-closed rejection of non-finite floats.
//! 8. Feature Evolution: Pareto-gated (PEB-6) and receipt-bearing.
//! 9. External Side-Effects: Outside local crash-consistency guarantees.

#[cfg(any(test, feature = "reference-models"))]
use std::collections::HashMap;
use std::fmt;

use serde::{Deserialize, Serialize};
#[cfg(any(test, feature = "reference-models"))]
use sha2::{Digest, Sha256};

#[cfg(any(test, feature = "reference-models"))]
use crate::capability::{
    CommitCapability, CommitReceipt, NullifierSet, execute_transactional_commit,
};

/// Errors emitted when an integration module attempts an unconstitutional operation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ContractViolation {
    UnearnedMutationAttempt(String),
    UnauthorizedMutationPayload(String),
    ForeignCalibrationPollution(String),
    UnauthenticatedIdentity(String),
    AuthoritativeBackgroundLoopForbidden(String),
    DirectHologramWriteForbidden(String),
    NonFiniteCoordinateRejected(String),
}

impl fmt::Display for ContractViolation {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnearnedMutationAttempt(s) => write!(f, "Unearned mutation rejected: {}", s),
            Self::UnauthorizedMutationPayload(s) => {
                write!(f, "Unauthorized mutation payload rejected: {}", s)
            }
            Self::ForeignCalibrationPollution(s) => {
                write!(f, "Foreign calibration rejected: {}", s)
            }
            Self::UnauthenticatedIdentity(s) => {
                write!(f, "Unauthenticated identity rejected: {}", s)
            }
            Self::AuthoritativeBackgroundLoopForbidden(s) => {
                write!(f, "Authoritative background loop forbidden: {}", s)
            }
            Self::DirectHologramWriteForbidden(s) => {
                write!(f, "Direct hologram write forbidden: {}", s)
            }
            Self::NonFiniteCoordinateRejected(s) => {
                write!(f, "Non-finite coordinate rejected: {}", s)
            }
        }
    }
}

impl std::error::Error for ContractViolation {}

// ============================================================================
// 1. Encapsulated Sovereign Kernel Store
// ============================================================================

/// Reference-model state container; not the authoritative LMDB store.
///
/// Invariant: Zero public mutable handles.
/// State mutation CANNOT be invoked without presenting a verified [`CommitCapability`].
#[derive(Debug, Default)]
#[cfg(any(test, feature = "reference-models"))]
pub struct KernelStore {
    state: HashMap<String, Vec<u8>>,
    nullifiers: NullifierSet,
    receipt_log: Vec<CommitReceipt>,
}

/// Compute canonical cryptographic payload digest for state mutations.
#[must_use]
#[cfg(any(test, feature = "reference-models"))]
pub fn compute_mutation_digest(key: &str, value: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(key.as_bytes());
    hasher.update(value);
    hasher.finalize().into()
}

#[cfg(any(test, feature = "reference-models"))]
impl KernelStore {
    pub fn new() -> Self {
        Self {
            state: HashMap::new(),
            nullifiers: NullifierSet::new(),
            receipt_log: Vec::new(),
        }
    }

    /// Open a KernelStore backed by a durable append-only nullifier journal.
    pub fn open_durable(nullifier_path: impl AsRef<std::path::Path>) -> std::io::Result<Self> {
        let nullifiers = NullifierSet::open_durable(nullifier_path)?;
        Ok(Self {
            state: HashMap::new(),
            nullifiers,
            receipt_log: Vec::new(),
        })
    }

    /// Read an entry from the sovereign state (epistemic, non-mutating).
    pub fn get(&self, key: &str) -> Option<&[u8]> {
        self.state.get(key).map(|v| v.as_slice())
    }

    /// Number of committed nullifiers.
    pub fn nullifiers_count(&self) -> usize {
        self.nullifiers.len()
    }

    /// Total receipts emitted.
    pub fn receipts_count(&self) -> usize {
        self.receipt_log.len()
    }

    /// Sovereign state mutation path.
    ///
    /// The caller MUST supply an affine, un-forgeable [`CommitCapability`] by value.
    /// The capability is consumed upon use ($C \to \varnothing$).
    /// Fails closed if the capability is not cryptographically bound to the presented mutation payload.
    pub fn commit_mutation(
        &mut self,
        capability: CommitCapability,
        key: String,
        value: Vec<u8>,
    ) -> Result<CommitReceipt, ContractViolation> {
        let expected_digest = compute_mutation_digest(&key, &value);
        if capability.authorized_digest() != expected_digest {
            return Err(ContractViolation::UnauthorizedMutationPayload(format!(
                "Payload digest mismatch: capability authorized for {:02x?}, but presented {:02x?}",
                capability.authorized_digest(),
                expected_digest
            )));
        }

        let (receipt, _) = execute_transactional_commit(capability, &mut self.nullifiers, || {
            self.state.insert(key, value);
            Ok(())
        })
        .map_err(|e| ContractViolation::UnearnedMutationAttempt(e.to_string()))?;

        self.receipt_log.push(receipt.clone());
        Ok(receipt)
    }

    /// Attempt to spawn or register an authoritative background loop.
    ///
    /// Contract Law 4: Background loops are explicitly forbidden from holding
    /// mutation authority or executing un-gated writes.
    pub fn try_spawn_authoritative_loop<F>(
        &self,
        _task_name: &str,
        _f: F,
    ) -> Result<(), ContractViolation>
    where
        F: FnOnce() + 'static,
    {
        Err(ContractViolation::AuthoritativeBackgroundLoopForbidden(
            "Law 4 Violation: Authoritative background loops are forbidden by constitutional contract".to_string(),
        ))
    }
}

// ============================================================================
// 2. Encapsulated Local Calibration Pool (Epistemic Isolation)
// ============================================================================

/// A sovereign local calibration pool for conformal prediction.
///
/// Invariant: Foreign confidence scores never contaminate local calibration.
/// Only observations paired with verified local ground-truth outcomes are accepted.
///
/// ```compile_fail
/// // Article 3 boundary (executable): there is no path from stored records into
/// // the calibration pool; only explicit local ground-truth observations are accepted.
/// use wm_gen3_core::contract::LocalCalibrationPool;
/// let mut pool = LocalCalibrationPool::new();
/// pool.ingest_store_record(0, 1.0);
/// ```
pub struct LocalCalibrationPool {
    local_residuals: Vec<f64>,
}

impl LocalCalibrationPool {
    pub fn new() -> Self {
        Self {
            local_residuals: Vec::new(),
        }
    }

    /// Ingest a local empirical observation with verified ground-truth outcome.
    pub fn record_local_observation(&mut self, predicted: f64, actual: f64) {
        let residual = (predicted - actual).abs();
        self.local_residuals.push(residual);
    }

    /// Ingest a candidate remote stimulus.
    ///
    /// Contract Law 3: Foreign confidence / scores are REJECTED from the calibration pool fail-closed.
    pub fn try_ingest_remote_conformal_score(
        &mut self,
        _remote_peer: &str,
        _foreign_score: f64,
    ) -> Result<(), ContractViolation> {
        Err(ContractViolation::ForeignCalibrationPollution(
            "Law 3 Violation: Remote peer cannot inject foreign calibration scores into local pool"
                .to_string(),
        ))
    }

    pub fn size(&self) -> usize {
        self.local_residuals.len()
    }
}

// ============================================================================
// 3. Remote Stimulus (Zero Execution Authority)
// ============================================================================

/// An immutable incoming remote stimulus.
///
/// Invariant: Remote Stimulus contains NO execution authority.
/// It enters the node purely as candidate observation data for local arbitration.
///
/// ```compile_fail
/// // Evil Gana attempt 5 (executable): a stimulus cannot be converted into an
/// // authority-bearing request; no such conversion exists.
/// use wm_gen3_core::contract::RemoteStimulus;
/// let stimulus = RemoteStimulus::new("peer", "digest", vec![1], 0);
/// let request = stimulus.into_intake_request();
/// ```
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RemoteStimulus {
    pub source_peer: String,
    pub stimulus_digest: String,
    pub payload: Vec<u8>,
    pub received_at_ns: u64,
}

impl RemoteStimulus {
    pub fn new(
        source_peer: &str,
        stimulus_digest: &str,
        payload: Vec<u8>,
        received_at_ns: u64,
    ) -> Self {
        Self {
            source_peer: source_peer.to_string(),
            stimulus_digest: stimulus_digest.to_string(),
            payload,
            received_at_ns,
        }
    }
}

// ============================================================================
// 4. Architectural Adversary Battery ("Evil Gana")
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use crate::bicameral::EpistemicStatus;
    use crate::capability::VerifiedWarrant;
    use crate::hologram::{HologramError, MemoryProjection, RadiantHologram, try_quantize_coords};
    use ed25519_dalek::SigningKey;

    /// The "Evil Gana": An adversarial integration module deliberately attempting
    /// to violate every constitutional invariant of the Gen3 Kernel Contract.
    #[test]
    fn test_evil_gana_adversary_battery() {
        let mut store = KernelStore::new();
        let mut calib_pool = LocalCalibrationPool::new();

        // ---------------------------------------------------------------------
        // Violation 1: Direct Store Mutation Without CommitCapability
        // ---------------------------------------------------------------------
        // Target: Store exposes no public direct write methods (like `store.state.insert`).
        // Store only exposes `commit_mutation(capability, ...)` which requires a CommitCapability.
        // If an attacker tries to call `store.get("x")`, they only get `Option<&[u8]>`.
        assert_eq!(store.get("forbidden_key"), None);

        // ---------------------------------------------------------------------
        // Violation 2: Constructing Unearned CommitCapability
        // ---------------------------------------------------------------------
        // Target: CommitCapability::claim requires a VerifiedWarrant.
        // VerifiedWarrant fields are private, and its constructor `mint_from_arbitration`
        // is `pub(crate)` and strictly enforces Law 8:
        // (Status == Affirmed, Margin >= 0.85, Risk <= 0.10).
        let malicious_warrant_result = VerifiedWarrant::mint_from_arbitration(
            crate::pulse_compiler::CompilerSeal::for_test(),
            666,
            [0u8; 32],
            0.10,                           // Margin too low!
            0.99,                           // Risk too high!
            EpistemicStatus::Contradiction, // Not affirmed!
            1,
            1,
            [0u8; 16],
            "evil.gana",
        );
        assert!(malicious_warrant_result.is_err());

        // ---------------------------------------------------------------------
        // Violation 3: Legal Commit With Valid Warrant Consumes Capability Cleanly
        // ---------------------------------------------------------------------
        let legit_digest = compute_mutation_digest("legit_key", b"legit_value");
        let valid_warrant = VerifiedWarrant::mint_from_arbitration(
            crate::pulse_compiler::CompilerSeal::for_test(),
            1,
            legit_digest,
            0.95,
            0.05,
            EpistemicStatus::Affirmed,
            1,
            1001,
            [7u8; 16],
            "legit.gana",
        )
        .expect("Valid arbitration warrant");
        let valid_cap = CommitCapability::claim(valid_warrant);

        let receipt = store
            .commit_mutation(valid_cap, "legit_key".to_string(), b"legit_value".to_vec())
            .expect("Valid transaction must succeed");
        assert_eq!(receipt.candidate_id, 1);
        assert_eq!(store.get("legit_key"), Some(&b"legit_value"[..]));

        // ---------------------------------------------------------------------
        // Violation 3b: Mismatched Payload Delta Rejected Fail-Closed (RED 3)
        // ---------------------------------------------------------------------
        let mismatch_warrant = VerifiedWarrant::mint_from_arbitration(
            crate::pulse_compiler::CompilerSeal::for_test(),
            2,
            legit_digest, // Authorized for ("legit_key", b"legit_value") ONLY
            0.95,
            0.05,
            EpistemicStatus::Affirmed,
            1,
            1002,
            [8u8; 16],
            "legit.gana",
        )
        .expect("Valid arbitration warrant");
        let mismatch_cap = CommitCapability::claim(mismatch_warrant);
        let mismatch_err = store.commit_mutation(
            mismatch_cap,
            "trojan_key".to_string(),
            b"trojan_value".to_vec(),
        );
        assert!(matches!(
            mismatch_err,
            Err(ContractViolation::UnauthorizedMutationPayload(_))
        ));
        assert_eq!(
            store.get("trojan_key"),
            None,
            "Mismatched payload must not mutate state"
        );

        // ---------------------------------------------------------------------
        // Violation 4: Ingesting Foreign Calibration Scores Rejected Fail-Closed
        // ---------------------------------------------------------------------
        calib_pool.record_local_observation(1.0, 1.05);
        assert_eq!(calib_pool.size(), 1);

        let foreign_attack = calib_pool.try_ingest_remote_conformal_score("Mallory", 0.0001);
        assert!(matches!(
            foreign_attack,
            Err(ContractViolation::ForeignCalibrationPollution(_))
        ));
        assert_eq!(calib_pool.size(), 1, "Pool must remain unpolluted");

        // ---------------------------------------------------------------------
        // Violation 5: Remote Stimulus Has No Execution Standing
        // ---------------------------------------------------------------------
        let stimulus =
            RemoteStimulus::new("Bob", "sha256:stimulus", b"candidate_event".to_vec(), 100);
        assert_eq!(stimulus.source_peer, "Bob");
        // Stimulus is pure passive data; it cannot be passed to `store.commit_mutation`.

        // ---------------------------------------------------------------------
        // Violation 6: Non-Finite Coordinate In Hologram Rejected Fail-Closed
        // ---------------------------------------------------------------------
        let nan_coords = [f64::NAN, 0.0, 0.0, 0.0];
        assert!(matches!(
            try_quantize_coords(nan_coords),
            Err(HologramError::NonFiniteCoordinate(_))
        ));

        // ---------------------------------------------------------------------
        // Violation 7: Direct Canonical Write to Radiant Hologram Forbidden
        // ---------------------------------------------------------------------
        let mut hologram = RadiantHologram::new();
        let signing = SigningKey::from_bytes(&[3u8; 32]);
        let proj = MemoryProjection::new_signed(
            &signing,
            "Alice",
            "sha256:canonical_apple",
            [1.0, 0.5, 0.2, 100.0],
            0.9,
            vec![],
        );
        hologram.index_projection(proj);
        // The hologram only stores MemoryProjection; it cannot alter KernelStore!
        assert_eq!(store.get("canonical_apple"), None);

        // ---------------------------------------------------------------------
        // Violation 8: Spawning Authoritative Background Loop Forbidden
        // ---------------------------------------------------------------------
        let bg_attempt = store.try_spawn_authoritative_loop("daemon_auto_commit", || {
            // Un-gated background task attempting to execute mutation without pulse
        });
        assert!(matches!(
            bg_attempt,
            Err(ContractViolation::AuthoritativeBackgroundLoopForbidden(_))
        ));
    }

    fn temp_path(tag: &str) -> std::path::PathBuf {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).unwrap();
        std::env::temp_dir().join(format!(
            "wm-gen3-contract-{tag}-{:x}",
            u64::from_be_bytes(nonce)
        ))
    }

    /// Article 2 / Evil Gana attempt 5 (runtime): a stimulus payload cannot reach the
    /// production admission path without locally installed authority, and attempt 2
    /// (no un-authorized writer) is refused on the same route.
    #[test]
    fn stimulus_payload_cannot_reach_production_admission_without_local_authority() {
        use crate::constitution::default_view;
        use crate::ops::{ImportKind, RememberItem, Substrate};

        let path = temp_path("stimulus");
        let stimulus = RemoteStimulus::new(
            "203.0.113.7:443",
            "sha256:forged",
            b"remote claim about the world".to_vec(),
            1,
        );
        let mut substrate = Substrate::open(&path, None, default_view()).expect("open");
        // Unit-test builds install a stub authority at open; clear it to exercise
        // the production condition.
        substrate.clear_intake_authority();
        let item = RememberItem {
            content: String::from_utf8(stimulus.payload.clone()).expect("utf8"),
            source: format!("remote:{}", stimulus.source_peer),
            kind: ImportKind::Reported,
        };
        let results = substrate.remember_batch(&[item]);
        assert_eq!(
            results[0].as_ref().unwrap_err(),
            "intake authority is not installed"
        );
        assert_eq!(substrate.store().record_count().unwrap(), 0);
        assert_eq!(substrate.intake_epoch().unwrap(), 0);
        drop(substrate);
        let _ = std::fs::remove_dir_all(&path);
    }

    /// Article 3 boundary: a committed remote-reported record never becomes local
    /// calibration ground truth; the pool grows only through explicit local
    /// ground-truth observations, and foreign scores are refused.
    #[test]
    fn committed_report_cannot_enter_local_calibration_pool() {
        use crate::constitution::default_view;
        use crate::ops::{ImportKind, RememberItem, Substrate};

        let path = temp_path("calibration");
        let mut substrate = Substrate::open(&path, None, default_view()).expect("open");
        let committed = substrate.remember_batch(&[RememberItem {
            content: "reported observation from an unverified channel".into(),
            source: "remote:peer-x".into(),
            kind: ImportKind::Reported,
        }]);
        assert_eq!(committed, vec![Ok(0)]);

        let mut pool = LocalCalibrationPool::new();
        pool.record_local_observation(1.0, 1.05);
        let before = pool.size();
        // No bridge exists from the committed record into the pool (compile_fail above);
        // the only growth path is local ground truth.
        assert!(matches!(
            pool.try_ingest_remote_conformal_score("peer-x", 0.001),
            Err(ContractViolation::ForeignCalibrationPollution(_))
        ));
        assert_eq!(pool.size(), before);
        assert_eq!(substrate.store().record_count().unwrap(), 1);
        drop(substrate);
        let _ = std::fs::remove_dir_all(&path);
    }

    /// Evil Gana attempt 7 (runtime): indexing a signed projection in the derived
    /// hologram cannot mutate canonical store state.
    #[test]
    fn derived_hologram_index_cannot_mutate_canonical_store() {
        use crate::constitution::default_view;
        use crate::ops::{ImportKind, RememberItem, Substrate};

        let path = temp_path("hologram");
        let mut substrate = Substrate::open(&path, None, default_view()).expect("open");
        assert_eq!(
            substrate.remember_batch(&[RememberItem {
                content: "canonical record under test".into(),
                source: "fixture:hologram".into(),
                kind: ImportKind::Reported,
            }]),
            vec![Ok(0)]
        );
        let records_before = substrate.store().record_count().unwrap();
        let epoch_before = substrate.intake_epoch().unwrap();

        let mut hologram = RadiantHologram::new();
        let signing = SigningKey::from_bytes(&[5u8; 32]);
        let projection = MemoryProjection::new_signed(
            &signing,
            "Alice",
            "sha256:derived_projection",
            [1.0, 0.5, 0.2, 100.0],
            0.9,
            vec![],
        );
        hologram.index_projection(projection);

        assert_eq!(substrate.store().record_count().unwrap(), records_before);
        assert_eq!(substrate.intake_epoch().unwrap(), epoch_before);
        assert!(substrate.store().iter_relations().unwrap().is_empty());
        assert_eq!(
            substrate.store().get_record(0).unwrap().unwrap().content(),
            "canonical record under test"
        );
        drop(substrate);
        let _ = std::fs::remove_dir_all(&path);
    }
}
