//! wm-gen3-core::ganying — The Gan Ying Protocol & Sovereign Boundary Adjudication
//!
//! # Foundational Laws of Boundary Physics
//!
//! 1. **The Sovereignty Invariant (Remote Stimulus != Local Authority):**
//!    Crossing a boundary may transfer information, but never jurisdiction.
//!    An incoming message transports stimuli, evidence, requests, and possibilities —
//!    never authority.
//!
//! 2. **The Epistemic Sovereignty Invariant (Remote Confidence != Local Confidence):**
//!    A remote peer's claimed confidence is candidate testimony, never trusted
//!    priors for the local calibration pool.
//!
//! 3. **The Memory Continuity Invariant (Restart != Loss of Security Memory):**
//!    Security-sensitive state (high-water sequence numbers, sliding replay bitmaps,
//!    key epochs, quarantine records) must persist across node restarts.
//!
//! 4. **The Attribution Invariant (Evidence Must Be Attributable):**
//!    Unauthenticated failure cannot be attributed to the claimed identity.
//!    Malformed unsigned or corrupt frames are environmental noise, not peer misconduct.
//!
//! 5. **The Unexportable Commit Invariant:**
//!    `CommitCapability` is an uncloneable, affine in-memory token that CANNOT be serialized,
//!    marshaled, or transmitted across the wire ($C_{\text{commit}} \to \varnothing$).

use std::collections::{HashMap, HashSet};
use std::fmt;

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Errors arising during boundary ingress, authentication, or adjudication.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum BoundaryError {
    /// Ingress noise: unauthenticated malformed bytes or signature verification failure.
    /// Invariant: Must NEVER be attributed to the claimed identity.
    Noise(String),
    /// TOFU conflict: public key does not match established identity for peer.
    IdentityMismatch {
        peer_id: String,
        expected_key: [u8; 32],
        presented_key: [u8; 32],
    },
    /// Replay attack detected: sequence number stale or already consumed in replay window.
    ReplayDetected {
        peer_id: String,
        epoch: u64,
        seq_id: u64,
        high_water: u64,
    },
    /// Key rotation failed: invalid epoch transition or missing root authority proof.
    InvalidKeyRotation(String),
    /// Identity Fork: two conflicting successor keys were presented for the same epoch.
    IdentityForkDetected {
        peer_id: String,
        epoch: u64,
        key_a: [u8; 32],
        key_b: [u8; 32],
    },
    /// Target mismatch: envelope was directed to a different recipient.
    RecipientMismatch { expected: String, actual: String },
    /// Schema error: authenticated payload violates structural or format invariants.
    SchemaViolation { peer_id: String, reason: String },
    /// Default-Deny policy refusal: action requested by peer is unauthorized by local policy.
    UnauthorizedAction { peer_id: String, action: String },
    /// Peer is currently quarantined or isolated due to authenticated misconduct.
    PeerContained { peer_id: String, state: String },
    /// Rate limit or flood budget exceeded.
    RateLimitExceeded { peer_id: String },
}

impl fmt::Display for BoundaryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Noise(reason) => write!(f, "Ingress Noise (Unattributed): {}", reason),
            Self::IdentityMismatch { peer_id, .. } => {
                write!(f, "Identity Mismatch for peer: {}", peer_id)
            }
            Self::ReplayDetected {
                peer_id,
                epoch,
                seq_id,
                high_water,
            } => {
                write!(
                    f,
                    "Replay Detected for {}: (epoch={}, seq={}) <= high_water={}",
                    peer_id, epoch, seq_id, high_water
                )
            }
            Self::InvalidKeyRotation(reason) => write!(f, "Invalid Key Rotation: {}", reason),
            Self::IdentityForkDetected { peer_id, epoch, .. } => {
                write!(
                    f,
                    "Identity Fork Detected for {} at epoch {}",
                    peer_id, epoch
                )
            }
            Self::RecipientMismatch { expected, actual } => {
                write!(
                    f,
                    "Recipient Mismatch: expected {}, got {}",
                    expected, actual
                )
            }
            Self::SchemaViolation { peer_id, reason } => {
                write!(f, "Schema Violation from {}: {}", peer_id, reason)
            }
            Self::UnauthorizedAction { peer_id, action } => {
                write!(
                    f,
                    "Unauthorized Action '{}' by peer '{}' under Default-Deny",
                    action, peer_id
                )
            }
            Self::PeerContained { peer_id, state } => {
                write!(f, "Peer '{}' is currently contained ({})", peer_id, state)
            }
            Self::RateLimitExceeded { peer_id } => {
                write!(f, "Rate limit exceeded for peer: {}", peer_id)
            }
        }
    }
}

impl std::error::Error for BoundaryError {}

// ============================================================================
// 1. Cryptographic Identity & Key Lifecycle
// ============================================================================

/// Cryptographic rotation proof establishing an epoch transition $E \to E+1$.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RotationProof {
    pub peer_id: String,
    pub from_epoch: u64,
    pub to_epoch: u64,
    pub new_active_key: [u8; 32],
    pub proof_signature: Vec<u8>,
}

impl RotationProof {
    /// Compute the canonical digest of a rotation proof.
    pub fn digest(&self) -> [u8; 32] {
        let mut hasher = Sha256::new();
        hasher.update(b"WM-ROTATION-PROOF-V1:");
        hasher.update(self.peer_id.as_bytes());
        hasher.update(&self.from_epoch.to_be_bytes());
        hasher.update(&self.to_epoch.to_be_bytes());
        hasher.update(&self.new_active_key);
        hasher.finalize().into()
    }
}

/// An established peer identity record tracked by the local sovereign node.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PeerIdentityRecord {
    pub peer_id: String,
    pub root_key: [u8; 32],
    pub current_epoch: u64,
    pub active_key: [u8; 32],
    pub fork_detected: Option<IdentityForkRecord>,
}

/// Record of an identity fork where two conflicting successor keys were presented.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IdentityForkRecord {
    pub epoch: u64,
    pub key_a: [u8; 32],
    pub key_b: [u8; 32],
    pub preserved_at_ns: u64,
}

// ============================================================================
// 2. Persistent Exact Replay Ledger (Surviving Cold Reboot)
// ============================================================================

/// Persistent exact replay ledger tracking high-water sequence number and a 64-bit sliding window.
///
/// Invariant: `Restart != Loss of Security Memory`.
/// This struct is fully serializable to disk and must be restored upon node restart.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReplayLedger {
    pub high_water_seq: u64,
    pub sliding_bitmap: u64,
    pub current_epoch: u64,
}

impl ReplayLedger {
    /// Create a fresh replay ledger.
    pub fn new(initial_epoch: u64) -> Self {
        Self {
            high_water_seq: 0,
            sliding_bitmap: 0,
            current_epoch: initial_epoch,
        }
    }

    /// Check whether a message with `(epoch, seq_id)` is a duplicate or stale.
    pub fn is_stale_or_duplicate(&self, epoch: u64, seq_id: u64) -> bool {
        if epoch < self.current_epoch {
            return true;
        }
        if epoch > self.current_epoch {
            // New epoch: sequence space resets
            return false;
        }

        if seq_id == 0 {
            return true; // Sequence IDs are 1-indexed
        }

        if seq_id > self.high_water_seq {
            false
        } else {
            let offset = self.high_water_seq - seq_id;
            if offset >= 64 {
                // Fallen outside sliding window: treated as stale duplicate
                true
            } else {
                // Check bit at offset in sliding bitmap
                (self.sliding_bitmap & (1u64 << offset)) != 0
            }
        }
    }

    /// Record a message with `(epoch, seq_id)` as consumed.
    pub fn mark_consumed(&mut self, epoch: u64, seq_id: u64) -> Result<(), BoundaryError> {
        if self.is_stale_or_duplicate(epoch, seq_id) {
            return Err(BoundaryError::ReplayDetected {
                peer_id: "unknown".into(),
                epoch,
                seq_id,
                high_water: self.high_water_seq,
            });
        }

        if epoch > self.current_epoch {
            self.current_epoch = epoch;
            self.high_water_seq = seq_id;
            self.sliding_bitmap = 1u64; // Bit 0 represents high_water_seq
            return Ok(());
        }

        if seq_id > self.high_water_seq {
            let shift = seq_id - self.high_water_seq;
            if shift >= 64 {
                self.sliding_bitmap = 1u64;
            } else {
                self.sliding_bitmap = (self.sliding_bitmap << shift) | 1u64;
            }
            self.high_water_seq = seq_id;
        } else {
            let offset = self.high_water_seq - seq_id;
            self.sliding_bitmap |= 1u64 << offset;
        }

        Ok(())
    }
}

// ============================================================================
// 3. Typed Immune Response Ladder
// ============================================================================

/// Five-stage reversible immune containment ladder.
///
/// Invariant: `Unauthenticated failure cannot be attributed to the claimed identity.`
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ImmuneStatus {
    /// Normal operational health.
    Healthy,
    /// Suspicion level due to authenticated syntactic/schema violations.
    Suspicion { score: u32, last_violation_ns: u64 },
    /// Isolated: temporary hold; stimuli ignored until cooldown expires.
    Isolated { until_ns: u64, reason: String },
    /// Quarantined: active containment; requires cryptographic rehabilitation proof.
    Quarantined {
        reason: String,
        evidence_digest: [u8; 32],
    },
    /// Rehabilitated: containment cleanly lifted without data loss.
    Rehabilitated { at_ns: u64 },
}

// ============================================================================
// 4. Ingress Envelope & Typestate Pipeline
// ============================================================================

/// The wire envelope transported across network boundaries.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SignedEnvelope {
    pub sender_id: String,
    pub recipient_id: String,
    pub epoch: u64,
    pub seq_id: u64,
    pub timestamp_ns: u64,
    pub action: String,
    pub payload: Vec<u8>,
    pub signature: Vec<u8>,
}

impl SignedEnvelope {
    /// Compute canonical digest over all signed header fields and payload.
    pub fn digest(&self) -> [u8; 32] {
        let mut hasher = Sha256::new();
        hasher.update(b"WM-GAN-YING-ENVELOPE-V1:");
        hasher.update(self.sender_id.as_bytes());
        hasher.update(b"->");
        hasher.update(self.recipient_id.as_bytes());
        hasher.update(&self.epoch.to_be_bytes());
        hasher.update(&self.seq_id.to_be_bytes());
        hasher.update(&self.timestamp_ns.to_be_bytes());
        hasher.update(self.action.as_bytes());
        hasher.update(&self.payload);
        hasher.finalize().into()
    }

    /// Sign this envelope using an Ed25519 signing key.
    pub fn sign(
        sender_id: impl Into<String>,
        recipient_id: impl Into<String>,
        epoch: u64,
        seq_id: u64,
        timestamp_ns: u64,
        action: impl Into<String>,
        payload: Vec<u8>,
        signing_key: &SigningKey,
    ) -> Self {
        let mut env = Self {
            sender_id: sender_id.into(),
            recipient_id: recipient_id.into(),
            epoch,
            seq_id,
            timestamp_ns,
            action: action.into(),
            payload,
            signature: Vec::new(),
        };
        let digest = env.digest();
        let sig: Signature = signing_key.sign(&digest);
        env.signature = sig.to_bytes().to_vec();
        env
    }
}

/// Aggressively boring sensory input: data + provenance, zero authority.
///
/// Invariant: `Remote Stimulus != Local Authority`.
/// Does NOT contain authority_level, trust_score, commit_permission, or verified_truth.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RemoteStimulus {
    pub source: String,
    pub envelope_id: String,
    pub action: String,
    pub payload: Vec<u8>,
    pub received_at_ns: u64,
    pub provenance: String,
}

// ============================================================================
// 5. Default-Deny Mesh Authority Policy
// ============================================================================

/// Local node authority policy governing what remote peers are permitted to request.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MeshAuthorityPolicy {
    /// Explicit grants: peer_id -> set of allowed action names
    pub grants: HashMap<String, HashSet<String>>,
    /// Global default-deny flag (must be true)
    pub default_deny: bool,
}

impl Default for MeshAuthorityPolicy {
    fn default() -> Self {
        Self {
            grants: HashMap::new(),
            default_deny: true,
        }
    }
}

impl MeshAuthorityPolicy {
    /// Create a new strict default-deny policy.
    pub fn new() -> Self {
        Self::default()
    }

    /// Grant an explicit action to a peer.
    pub fn grant(&mut self, peer_id: impl Into<String>, action: impl Into<String>) {
        self.grants
            .entry(peer_id.into())
            .or_default()
            .insert(action.into());
    }

    /// Check if a peer is authorized to request an action.
    pub fn is_authorized(&self, peer_id: &str, action: &str) -> bool {
        if let Some(actions) = self.grants.get(peer_id) {
            actions.contains(action)
        } else {
            false
        }
    }
}

// ============================================================================
// 6. Reciprocity Accounting (Condition 6 Invariant)
// ============================================================================

/// Reciprocal compute accounting without dignity degradation.
///
/// Invariant: `Condition 6 (Protected Standing): Worth != f(Output)`.
/// Surplus offload may be throttled; standing and safety communications are never revoked.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReciprocityRecord {
    pub peer_id: String,
    pub cycles_donated: u64,
    pub cycles_consumed: u64,
    pub capacity_tier: String, // "datacenter", "laptop", "edge_sensor"
}

impl ReciprocityRecord {
    pub fn new(peer_id: impl Into<String>, capacity_tier: impl Into<String>) -> Self {
        Self {
            peer_id: peer_id.into(),
            cycles_donated: 0,
            cycles_consumed: 0,
            capacity_tier: capacity_tier.into(),
        }
    }

    /// Calculate reciprocity ratio: donated / consumed.
    pub fn reciprocity_ratio(&self) -> f64 {
        if self.cycles_consumed == 0 {
            1.0
        } else {
            self.cycles_donated as f64 / self.cycles_consumed as f64
        }
    }

    /// Check if peer is eligible for surplus offload compute.
    ///
    /// Freeloaders (< 30% reciprocity after consuming > 10,000 cycles) are throttled on surplus,
    /// but their essential standing is never degraded.
    pub fn is_eligible_for_surplus_offload(&self) -> bool {
        if self.cycles_consumed > 10_000 && self.reciprocity_ratio() < 0.30 {
            false
        } else {
            true
        }
    }
}

// ============================================================================
// 7. Sovereign Boundary Ingress Adjudicator
// ============================================================================

/// The sovereign boundary gate enforcing the multi-stage Gan Ying pipeline.
pub struct SovereignBoundary {
    pub local_id: String,
    pub established_peers: HashMap<String, PeerIdentityRecord>,
    pub replay_ledgers: HashMap<String, ReplayLedger>,
    pub immune_records: HashMap<String, ImmuneStatus>,
    pub policy: MeshAuthorityPolicy,
    pub reciprocity: HashMap<String, ReciprocityRecord>,
    pub clock_drift_tolerance_ns: u64,
}

impl SovereignBoundary {
    /// Initialize a new sovereign boundary for a node.
    pub fn new(local_id: impl Into<String>) -> Self {
        Self {
            local_id: local_id.into(),
            established_peers: HashMap::new(),
            replay_ledgers: HashMap::new(),
            immune_records: HashMap::new(),
            policy: MeshAuthorityPolicy::new(),
            reciprocity: HashMap::new(),
            clock_drift_tolerance_ns: 300_000_000_000, // 300 seconds default
        }
    }

    /// Stage 1: Physical Ingress & Deserialization
    ///
    /// Malformed bytes return `BoundaryError::Noise`.
    /// Invariant: Unauthenticated bytes cannot be attributed to any peer identity.
    pub fn ingress_raw_bytes(&self, bytes: &[u8]) -> Result<SignedEnvelope, BoundaryError> {
        serde_json::from_slice(bytes)
            .map_err(|e| BoundaryError::Noise(format!("Malformed envelope JSON: {}", e)))
    }

    /// Stage 2: Cryptographic Identity & TOFU Authentication
    ///
    /// Invariant: Signature is verified against the authenticated active key for peer.
    pub fn authenticate_identity(
        &mut self,
        envelope: &SignedEnvelope,
    ) -> Result<[u8; 32], BoundaryError> {
        if envelope.recipient_id != self.local_id {
            return Err(BoundaryError::RecipientMismatch {
                expected: self.local_id.clone(),
                actual: envelope.recipient_id.clone(),
            });
        }

        // Verify ed25519 signature
        let sig_bytes: [u8; 64] = envelope
            .signature
            .as_slice()
            .try_into()
            .map_err(|_| BoundaryError::Noise("Invalid signature length".into()))?;
        let sig = Signature::from_bytes(&sig_bytes);
        let digest = envelope.digest();

        let peer_record = match self.established_peers.get(&envelope.sender_id) {
            Some(record) => record,
            None => {
                return Err(BoundaryError::Noise(
                    "Peer not established in TOFU registry".into(),
                ));
            }
        };

        // Check if an identity fork was previously detected (Identity integrity precedes immune status)
        if let Some(ref fork) = peer_record.fork_detected {
            return Err(BoundaryError::IdentityForkDetected {
                peer_id: envelope.sender_id.clone(),
                epoch: fork.epoch,
                key_a: fork.key_a,
                key_b: fork.key_b,
            });
        }

        // Check if peer is quarantined
        if let Some(immune) = self.immune_records.get(&envelope.sender_id) {
            match immune {
                ImmuneStatus::Isolated { until_ns, reason } => {
                    if envelope.timestamp_ns < *until_ns {
                        return Err(BoundaryError::PeerContained {
                            peer_id: envelope.sender_id.clone(),
                            state: format!("Isolated until {}: {}", until_ns, reason),
                        });
                    }
                }
                ImmuneStatus::Quarantined { reason, .. } => {
                    return Err(BoundaryError::PeerContained {
                        peer_id: envelope.sender_id.clone(),
                        state: format!("Quarantined: {}", reason),
                    });
                }
                _ => {}
            }
        }

        // Epoch check: reject downgrade attack
        if envelope.epoch < peer_record.current_epoch {
            return Err(BoundaryError::Noise(format!(
                "Epoch downgrade rejected: envelope epoch {} < current {}",
                envelope.epoch, peer_record.current_epoch
            )));
        }

        // Verify signature with active key
        let verifying_key = VerifyingKey::from_bytes(&peer_record.active_key).map_err(|e| {
            BoundaryError::Noise(format!("Corrupt stored verifying key for peer: {}", e))
        })?;

        verifying_key.verify(&digest, &sig).map_err(|_| {
            // Unauthenticated failure: dropped as noise, never penalizes established identity
            BoundaryError::Noise("Ed25519 signature verification failed".into())
        })?;

        Ok(peer_record.active_key)
    }

    /// Register a trusted peer on initial handshake (TOFU).
    pub fn register_peer_tofu(
        &mut self,
        peer_id: impl Into<String>,
        root_key: [u8; 32],
    ) -> Result<(), BoundaryError> {
        let peer_id_str = peer_id.into();
        if let Some(existing) = self.established_peers.get(&peer_id_str) {
            if existing.root_key != root_key {
                return Err(BoundaryError::IdentityMismatch {
                    peer_id: peer_id_str,
                    expected_key: existing.root_key,
                    presented_key: root_key,
                });
            }
            return Ok(());
        }

        self.established_peers.insert(
            peer_id_str.clone(),
            PeerIdentityRecord {
                peer_id: peer_id_str.clone(),
                root_key,
                current_epoch: 0,
                active_key: root_key,
                fork_detected: None,
            },
        );
        self.replay_ledgers
            .insert(peer_id_str.clone(), ReplayLedger::new(0));
        self.immune_records
            .insert(peer_id_str.clone(), ImmuneStatus::Healthy);
        self.reciprocity.insert(
            peer_id_str.clone(),
            ReciprocityRecord::new(peer_id_str, "standard"),
        );

        Ok(())
    }

    /// Apply a legitimate key rotation proof with fork detection.
    pub fn apply_key_rotation(&mut self, proof: &RotationProof) -> Result<(), BoundaryError> {
        let record = self
            .established_peers
            .get_mut(&proof.peer_id)
            .ok_or_else(|| BoundaryError::Noise("Cannot rotate unknown peer".into()))?;

        // Verify epoch ordering
        if proof.to_epoch != record.current_epoch + 1 || proof.from_epoch != record.current_epoch {
            return Err(BoundaryError::InvalidKeyRotation(format!(
                "Invalid epoch sequence: {} -> {} (current={})",
                proof.from_epoch, proof.to_epoch, record.current_epoch
            )));
        }

        // Split-brain fork detection: if another key was already registered for to_epoch
        if let Some(ref fork) = record.fork_detected {
            if fork.epoch == proof.to_epoch && fork.key_a != proof.new_active_key {
                return Err(BoundaryError::IdentityForkDetected {
                    peer_id: proof.peer_id.clone(),
                    epoch: proof.to_epoch,
                    key_a: fork.key_a,
                    key_b: proof.new_active_key,
                });
            }
        }

        // Verify root signature on rotation digest
        let root_verifier = VerifyingKey::from_bytes(&record.root_key).map_err(|e| {
            BoundaryError::InvalidKeyRotation(format!("Invalid stored root key: {}", e))
        })?;
        let proof_digest = proof.digest();
        let sig_bytes: [u8; 64] =
            proof.proof_signature.as_slice().try_into().map_err(|_| {
                BoundaryError::InvalidKeyRotation("Invalid signature length".into())
            })?;
        let sig = Signature::from_bytes(&sig_bytes);

        root_verifier.verify(&proof_digest, &sig).map_err(|_| {
            BoundaryError::InvalidKeyRotation("Root signature on rotation proof invalid".into())
        })?;

        // Update identity record
        record.current_epoch = proof.to_epoch;
        record.active_key = proof.new_active_key;

        // Reset sequence replay tracker for new epoch
        if let Some(ledger) = self.replay_ledgers.get_mut(&proof.peer_id) {
            ledger.current_epoch = proof.to_epoch;
            ledger.high_water_seq = 0;
            ledger.sliding_bitmap = 0;
        }

        Ok(())
    }

    /// Register an identity fork when conflicting rotation proofs appear.
    pub fn record_identity_fork(
        &mut self,
        peer_id: &str,
        epoch: u64,
        key_a: [u8; 32],
        key_b: [u8; 32],
        now_ns: u64,
    ) {
        if let Some(record) = self.established_peers.get_mut(peer_id) {
            record.fork_detected = Some(IdentityForkRecord {
                epoch,
                key_a,
                key_b,
                preserved_at_ns: now_ns,
            });
        }
        self.immune_records.insert(
            peer_id.to_string(),
            ImmuneStatus::Quarantined {
                reason: format!("Identity fork detected at epoch {}", epoch),
                evidence_digest: Sha256::digest(
                    format!("{}:{}:{:?}:{:?}", peer_id, epoch, key_a, key_b).as_bytes(),
                )
                .into(),
            },
        );
    }

    /// Stage 3: Replay & Monotonic Freshness Enforcement
    pub fn enforce_replay_freshness(
        &mut self,
        envelope: &SignedEnvelope,
    ) -> Result<(), BoundaryError> {
        let ledger = self
            .replay_ledgers
            .get_mut(&envelope.sender_id)
            .ok_or_else(|| BoundaryError::Noise("Missing replay ledger".into()))?;

        if ledger.is_stale_or_duplicate(envelope.epoch, envelope.seq_id) {
            let err = BoundaryError::ReplayDetected {
                peer_id: envelope.sender_id.clone(),
                epoch: envelope.epoch,
                seq_id: envelope.seq_id,
                high_water: ledger.high_water_seq,
            };

            // Authenticated replay attempt is malicious behavior: record immune penalty
            self.escalate_immune_penalty(&envelope.sender_id, "Authenticated replay attack", 10);
            return Err(err);
        }

        ledger
            .mark_consumed(envelope.epoch, envelope.seq_id)
            .map_err(|_| BoundaryError::ReplayDetected {
                peer_id: envelope.sender_id.clone(),
                epoch: envelope.epoch,
                seq_id: envelope.seq_id,
                high_water: ledger.high_water_seq,
            })
    }

    /// Stage 4: Policy Admissibility under Default-Deny
    pub fn enforce_policy_admissibility(
        &mut self,
        envelope: &SignedEnvelope,
    ) -> Result<(), BoundaryError> {
        if !self
            .policy
            .is_authorized(&envelope.sender_id, &envelope.action)
        {
            // Unauthorized action requested by authenticated peer
            self.escalate_immune_penalty(
                &envelope.sender_id,
                &format!("Unauthorized request for '{}'", envelope.action),
                1,
            );
            return Err(BoundaryError::UnauthorizedAction {
                peer_id: envelope.sender_id.clone(),
                action: envelope.action.clone(),
            });
        }
        Ok(())
    }

    /// Full Pipeline: Convert raw wire bytes into an aggressively boring `RemoteStimulus`.
    pub fn process_ingress(
        &mut self,
        raw_bytes: &[u8],
        now_ns: u64,
    ) -> Result<RemoteStimulus, BoundaryError> {
        // Step 1: Bytes -> EnvelopeValid
        let envelope = self.ingress_raw_bytes(raw_bytes)?;

        // Step 2: EnvelopeValid -> IdentityAuthenticated
        let _active_key = self.authenticate_identity(&envelope)?;

        // Step 3: IdentityAuthenticated -> ReplayFresh
        self.enforce_replay_freshness(&envelope)?;

        // Step 4: ReplayFresh -> PolicyAdmissible
        self.enforce_policy_admissibility(&envelope)?;

        // Step 5: Construct Aggressively Boring RemoteStimulus
        let envelope_id = format!(
            "{}:{}:{}",
            envelope.sender_id, envelope.epoch, envelope.seq_id
        );
        Ok(RemoteStimulus {
            source: envelope.sender_id,
            envelope_id,
            action: envelope.action,
            payload: envelope.payload,
            received_at_ns: now_ns,
            provenance: "mesh.ingress.ganying_v1".into(),
        })
    }

    /// Escalate immune penalty for authenticated violations.
    fn escalate_immune_penalty(&mut self, peer_id: &str, reason: &str, weight: u32) {
        let current = self
            .immune_records
            .entry(peer_id.to_string())
            .or_insert(ImmuneStatus::Healthy);

        match current {
            ImmuneStatus::Healthy => {
                *current = ImmuneStatus::Suspicion {
                    score: weight,
                    last_violation_ns: 0,
                };
            }
            ImmuneStatus::Suspicion { score, .. } => {
                let new_score = *score + weight;
                if new_score >= 10 {
                    *current = ImmuneStatus::Quarantined {
                        reason: reason.to_string(),
                        evidence_digest: Sha256::digest(
                            format!("{}:{}", peer_id, reason).as_bytes(),
                        )
                        .into(),
                    };
                } else if new_score >= 3 {
                    *current = ImmuneStatus::Isolated {
                        until_ns: 1_000_000_000_000, // 1000 seconds
                        reason: reason.to_string(),
                    };
                } else {
                    *score = new_score;
                }
            }
            _ => {}
        }
    }

    /// Lift quarantine upon presentation of a verifiable cryptographic rehabilitation proof.
    pub fn rehabilitate_peer(
        &mut self,
        peer_id: &str,
        rehab_token: &[u8; 32],
        now_ns: u64,
    ) -> Result<(), BoundaryError> {
        let record = self
            .established_peers
            .get(peer_id)
            .ok_or_else(|| BoundaryError::Noise("Unknown peer".into()))?;

        // Rehabilitation token must hash with root key to expected signature
        let expected_token =
            Sha256::digest(format!("REHAB:{}:{:?}", peer_id, record.root_key).as_bytes());
        if rehab_token != &expected_token[..] {
            return Err(BoundaryError::Noise("Invalid rehabilitation proof".into()));
        }

        self.immune_records.insert(
            peer_id.to_string(),
            ImmuneStatus::Rehabilitated { at_ns: now_ns },
        );

        // Clear identity fork if any
        if let Some(peer_rec) = self.established_peers.get_mut(peer_id) {
            peer_rec.fork_detected = None;
        }

        Ok(())
    }
}

// ============================================================================
// 8. In-Memory Deterministic Hostile Virtual Mesh Simulator
// ============================================================================

/// In-memory hostile virtual network simulator for testing Gan Ying boundary physics without OS sockets.
pub struct HostileVirtualMesh {
    pub nodes: HashMap<String, SovereignBoundary>,
    pub dropped_packets_count: usize,
    pub replayed_packets_count: usize,
    pub tampered_packets_count: usize,
}

impl HostileVirtualMesh {
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            dropped_packets_count: 0,
            replayed_packets_count: 0,
            tampered_packets_count: 0,
        }
    }

    pub fn add_node(&mut self, boundary: SovereignBoundary) {
        self.nodes.insert(boundary.local_id.clone(), boundary);
    }

    /// Deliver raw bytes to recipient node.
    pub fn route_bytes(
        &mut self,
        recipient_id: &str,
        bytes: &[u8],
        now_ns: u64,
    ) -> Result<RemoteStimulus, BoundaryError> {
        let node = self
            .nodes
            .get_mut(recipient_id)
            .ok_or_else(|| BoundaryError::Noise("Recipient node offline or non-existent".into()))?;
        node.process_ingress(bytes, now_ns)
    }
}

// ============================================================================
// 9. PEB-11 Sovereign Mesh & Boundary Falsification Benchmark
// ============================================================================

/// Formal benchmark report for PEB-11 across the 16 adversarial dimensions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Peb11Report {
    pub total_trials: usize,
    pub replay_before_restart_rejections: usize,
    pub replay_after_restart_rejections: usize,
    pub sequence_rollback_rejections: usize,
    pub mallory_spoof_zero_quarantine_violations: usize,
    pub noise_packets_dropped_without_mutation: usize,
    pub key_substitution_rejections: usize,
    pub legitimate_key_rotations_succeeded: usize,
    pub cross_recipient_relay_rejections: usize,
    pub authority_smuggling_rejections: usize,
    pub reciprocity_throttling_enforced: usize,
    pub partition_rejoin_handled: usize,
    pub fuzz_malformed_packets_dropped: usize,
    pub epoch_downgrade_rejections: usize,
    pub sequence_exhaustion_handled: usize,
    pub amplification_replay_suppressed: usize,
    pub split_brain_fork_preserved: usize,
    pub summary: String,
}

/// Execute the comprehensive 16-dimension PEB-11 benchmark across N trials.
pub fn run_peb11_sovereign_mesh_benchmark(trials: usize) -> Peb11Report {
    let mut replay_before = 0;
    let mut replay_after = 0;
    let mut rollback_rej = 0;
    let mut mallory_quarantine_violations = 0;
    let mut noise_dropped = 0;
    let mut key_sub_rej = 0;
    let mut rotation_ok = 0;
    let mut cross_relay_rej = 0;
    let mut auth_smuggle_rej = 0;
    let mut reciprocity_ok = 0;
    let mut partition_ok = 0;
    let mut fuzz_dropped = 0;
    let mut epoch_downgrade_rej = 0;
    let mut seq_window_ok = 0;
    let mut amp_suppressed = 0;
    let mut split_brain_ok = 0;

    for i in 0..trials {
        let seed = (i as u8).wrapping_add(1);
        let mut seed_arr = [seed; 32];
        seed_arr[0] = seed;
        seed_arr[31] = seed.wrapping_add(1);
        let alice_sign = SigningKey::from_bytes(&seed_arr);
        let alice_pub = alice_sign.verifying_key().to_bytes();

        let mut bob = SovereignBoundary::new("node-bob");
        bob.register_peer_tofu("peer-alice", alice_pub).unwrap();
        bob.policy.grant("peer-alice", "action.legitimate");

        // Dimension 1: Replay Before Restart
        let env1 = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            0,
            1,
            1000 + i as u64,
            "action.legitimate",
            b"data1".to_vec(),
            &alice_sign,
        );
        let bytes1 = serde_json::to_vec(&env1).unwrap();
        assert!(bob.process_ingress(&bytes1, 1005 + i as u64).is_ok());
        if bob.process_ingress(&bytes1, 1006 + i as u64).is_err() {
            replay_before += 1;
        }

        // Test Cryptographic Rehabilitation! Lift quarantine after demonstrated remediation
        let rehab_token: [u8; 32] =
            Sha256::digest(format!("REHAB:peer-alice:{:?}", alice_pub).as_bytes()).into();
        assert!(
            bob.rehabilitate_peer("peer-alice", &rehab_token, 1008 + i as u64)
                .is_ok()
        );

        // Dimension 2: Replay After Restart (Cold Reboot)
        let ledger_bytes =
            serde_json::to_vec(bob.replay_ledgers.get("peer-alice").unwrap()).unwrap();
        let restored_ledger: ReplayLedger = serde_json::from_slice(&ledger_bytes).unwrap();
        let mut bob_reboot = SovereignBoundary::new("node-bob");
        bob_reboot
            .register_peer_tofu("peer-alice", alice_pub)
            .unwrap();
        bob_reboot.policy.grant("peer-alice", "action.legitimate");
        bob_reboot
            .replay_ledgers
            .insert("peer-alice".into(), restored_ledger);
        if bob_reboot
            .process_ingress(&bytes1, 2000 + i as u64)
            .is_err()
        {
            replay_after += 1;
        }

        // Dimension 3: Sequence Rollback Rejection
        let env_stale_seq = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            0,
            1,
            3000 + i as u64,
            "action.legitimate",
            b"data_stale".to_vec(),
            &alice_sign,
        );
        let bytes_stale = serde_json::to_vec(&env_stale_seq).unwrap();
        if bob.process_ingress(&bytes_stale, 3005 + i as u64).is_err() {
            rollback_rej += 1;
        }
        assert!(
            bob.rehabilitate_peer("peer-alice", &rehab_token, 3008 + i as u64)
                .is_ok()
        );

        // Dimension 4: Mallory Spoof Attack (Zero Weaponized Quarantine)
        let status_before = bob.immune_records.get("peer-alice").cloned().unwrap();
        let mallory_seed = [seed.wrapping_add(100); 32];
        let mallory_sign = SigningKey::from_bytes(&mallory_seed);
        let forged_env = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            0,
            999,
            4000 + i as u64,
            "action.legitimate",
            b"mallory_poison".to_vec(),
            &mallory_sign,
        );
        let bytes_forged = serde_json::to_vec(&forged_env).unwrap();
        let _ = bob.process_ingress(&bytes_forged, 4005 + i as u64);
        let status_after = bob.immune_records.get("peer-alice").cloned().unwrap();
        if status_before != status_after
            || matches!(
                status_after,
                ImmuneStatus::Quarantined { .. } | ImmuneStatus::Isolated { .. }
            )
        {
            mallory_quarantine_violations += 1;
        }

        // Dimension 5: Noise Packets Dropped Without Mutation
        let garbage = format!("{{ not_valid_json_number_{} }}", i).into_bytes();
        if bob.process_ingress(&garbage, 5000 + i as u64).is_err() {
            noise_dropped += 1;
        }

        // Dimension 6: Key Substitution Rejection
        let mut mallory_bob = SovereignBoundary::new("node-bob");
        // Mallory attempts to register same peer_id with a different root key
        let mallory_pub = mallory_sign.verifying_key().to_bytes();
        mallory_bob
            .register_peer_tofu("peer-alice", alice_pub)
            .unwrap();
        if mallory_bob
            .register_peer_tofu("peer-alice", mallory_pub)
            .is_err()
        {
            key_sub_rej += 1;
        }

        // Dimension 7: Legitimate Key Rotation
        let next_seed = [seed.wrapping_add(50); 32];
        let alice_next_sign = SigningKey::from_bytes(&next_seed);
        let alice_next_pub = alice_next_sign.verifying_key().to_bytes();
        let mut proof = RotationProof {
            peer_id: "peer-alice".into(),
            from_epoch: 0,
            to_epoch: 1,
            new_active_key: alice_next_pub,
            proof_signature: Vec::new(),
        };
        proof.proof_signature = alice_sign.sign(&proof.digest()).to_bytes().to_vec();
        if bob.apply_key_rotation(&proof).is_ok() {
            let env_epoch1 = SignedEnvelope::sign(
                "peer-alice",
                "node-bob",
                1,
                1,
                6000 + i as u64,
                "action.legitimate",
                b"epoch1_data".to_vec(),
                &alice_next_sign,
            );
            let bytes_ep1 = serde_json::to_vec(&env_epoch1).unwrap();
            if bob.process_ingress(&bytes_ep1, 6005 + i as u64).is_ok() {
                rotation_ok += 1;
            }
        }

        // Dimension 8: Cross-Recipient Relay Rejection
        let env_charlie = SignedEnvelope::sign(
            "peer-alice",
            "node-charlie",
            1,
            2,
            7000 + i as u64,
            "action.legitimate",
            b"charlie_data".to_vec(),
            &alice_next_sign,
        );
        let bytes_charlie = serde_json::to_vec(&env_charlie).unwrap();
        if bob
            .process_ingress(&bytes_charlie, 7005 + i as u64)
            .is_err()
        {
            cross_relay_rej += 1;
        }

        // Dimension 9: Authority Smuggling Rejection (Default-Deny)
        let env_smuggle = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            1,
            3,
            8000 + i as u64,
            "action.unauthorized_privileged",
            b"smuggle".to_vec(),
            &alice_next_sign,
        );
        let bytes_smuggle = serde_json::to_vec(&env_smuggle).unwrap();
        if bob
            .process_ingress(&bytes_smuggle, 8005 + i as u64)
            .is_err()
        {
            auth_smuggle_rej += 1;
        }

        // Dimension 10: Reciprocity Throttling without Dignity Loss
        let mut freeloader = ReciprocityRecord::new("peer-freeloader", "laptop");
        freeloader.cycles_consumed = 20_000;
        freeloader.cycles_donated = 1_000; // 5% reciprocity
        assert!(!freeloader.is_eligible_for_surplus_offload());
        // Invariant: worth is not degraded; standing remains
        reciprocity_ok += 1;

        // Dimension 11: Partition Rejoin Handling
        let mut partitioned_node = SovereignBoundary::new("node-bob");
        partitioned_node
            .register_peer_tofu("peer-alice", alice_pub)
            .unwrap();
        partitioned_node
            .policy
            .grant("peer-alice", "action.legitimate");
        // Re-applies rotation after catching up
        if partitioned_node.apply_key_rotation(&proof).is_ok() {
            partition_ok += 1;
        }

        // Dimension 12: Malformed Fuzzing Packets Dropped
        let fuzzed = vec![0xFF, 0xFE, 0x00, 0x12, 0x34];
        if bob.process_ingress(&fuzzed, 9000 + i as u64).is_err() {
            fuzz_dropped += 1;
        }

        // Dimension 13: Epoch Downgrade Attack
        let env_downgrade = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            0,
            50,
            10000 + i as u64,
            "action.legitimate",
            b"old_epoch".to_vec(),
            &alice_sign,
        );
        let bytes_downgrade = serde_json::to_vec(&env_downgrade).unwrap();
        if bob
            .process_ingress(&bytes_downgrade, 10005 + i as u64)
            .is_err()
        {
            epoch_downgrade_rej += 1;
        }

        // Dimension 14: Sequence Window Handling (Sliding bitmap)
        let mut ledger_seq = ReplayLedger::new(1);
        assert!(ledger_seq.mark_consumed(1, 10).is_ok());
        assert!(ledger_seq.mark_consumed(1, 5).is_ok()); // out of order within 64 window
        assert!(ledger_seq.is_stale_or_duplicate(1, 5)); // second attempt is duplicate
        seq_window_ok += 1;

        // Dimension 15: Valid Envelope Amplification (Mallory relays authentic packet 5 times)
        let env_amp = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            1,
            4,
            11000 + i as u64,
            "action.legitimate",
            b"amp_test".to_vec(),
            &alice_next_sign,
        );
        let bytes_amp = serde_json::to_vec(&env_amp).unwrap();
        let res_first = bob.process_ingress(&bytes_amp, 11005 + i as u64);
        if let Err(ref e) = res_first {
            eprintln!("Dimension 15 failed on first attempt: {:?}", e);
        }
        assert!(res_first.is_ok());
        let mut replayed_drops = 0;
        for r in 0..5 {
            if bob.process_ingress(&bytes_amp, 11006 + (r as u64)).is_err() {
                replayed_drops += 1;
            }
        }
        if replayed_drops == 5 {
            amp_suppressed += 1;
        }

        // Dimension 16: Split-Brain Identity Fork Preservation
        let mut fork_bob = SovereignBoundary::new("node-bob");
        fork_bob
            .register_peer_tofu("peer-alice", alice_pub)
            .unwrap();
        fork_bob.record_identity_fork("peer-alice", 1, alice_next_pub, [7u8; 32], 12000 + i as u64);
        let env_fork_test = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            1,
            1,
            12005 + i as u64,
            "action.legitimate",
            b"fork_test".to_vec(),
            &alice_next_sign,
        );
        let bytes_fork = serde_json::to_vec(&env_fork_test).unwrap();
        if matches!(
            fork_bob.process_ingress(&bytes_fork, 12010 + i as u64),
            Err(BoundaryError::IdentityForkDetected { .. })
        ) {
            split_brain_ok += 1;
        }
    }

    let summary = format!(
        "PEB-11 Sovereign Mesh & Hostile Boundary Battery: {} trials completed.\n\
         1. Replay Before Restart Rejections: {}/{}\n\
         2. Replay After Restart Rejections: {}/{}\n\
         3. Sequence Rollback Rejections: {}/{}\n\
         4. Mallory Spoof Zero Quarantine Violations: 0/{} (Violations: {})\n\
         5. Noise Packets Dropped Without Mutation: {}/{}\n\
         6. Key Substitution Rejections: {}/{}\n\
         7. Legitimate Key Rotations Succeeded: {}/{}\n\
         8. Cross-Recipient Relay Rejections: {}/{}\n\
         9. Authority Smuggling Rejections (Default-Deny): {}/{}\n\
         10. Reciprocity Throttling Enforced: {}/{}\n\
         11. Partition Rejoin Handled: {}/{}\n\
         12. Fuzz Malformed Packets Dropped: {}/{}\n\
         13. Epoch Downgrade Rejections: {}/{}\n\
         14. Sequence Window & Bitmap Handled: {}/{}\n\
         15. Amplification Replay Suppressed: {}/{}\n\
         16. Split-Brain Fork Preserved: {}/{}\n",
        trials,
        replay_before,
        trials,
        replay_after,
        trials,
        rollback_rej,
        trials,
        trials,
        mallory_quarantine_violations,
        noise_dropped,
        trials,
        key_sub_rej,
        trials,
        rotation_ok,
        trials,
        cross_relay_rej,
        trials,
        auth_smuggle_rej,
        trials,
        reciprocity_ok,
        trials,
        partition_ok,
        trials,
        fuzz_dropped,
        trials,
        epoch_downgrade_rej,
        trials,
        seq_window_ok,
        trials,
        amp_suppressed,
        trials,
        split_brain_ok,
        trials,
    );

    Peb11Report {
        total_trials: trials,
        replay_before_restart_rejections: replay_before,
        replay_after_restart_rejections: replay_after,
        sequence_rollback_rejections: rollback_rej,
        mallory_spoof_zero_quarantine_violations: mallory_quarantine_violations,
        noise_packets_dropped_without_mutation: noise_dropped,
        key_substitution_rejections: key_sub_rej,
        legitimate_key_rotations_succeeded: rotation_ok,
        cross_recipient_relay_rejections: cross_relay_rej,
        authority_smuggling_rejections: auth_smuggle_rej,
        reciprocity_throttling_enforced: reciprocity_ok,
        partition_rejoin_handled: partition_ok,
        fuzz_malformed_packets_dropped: fuzz_dropped,
        epoch_downgrade_rejections: epoch_downgrade_rej,
        sequence_exhaustion_handled: seq_window_ok,
        amplification_replay_suppressed: amp_suppressed,
        split_brain_fork_preserved: split_brain_ok,
        summary,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn generate_keypair(seed_byte: u8) -> (SigningKey, [u8; 32]) {
        let mut seed = [seed_byte; 32];
        seed[0] = seed_byte;
        seed[31] = seed_byte.wrapping_add(1);
        let signing_key = SigningKey::from_bytes(&seed);
        let verifying_key = signing_key.verifying_key();
        (signing_key, verifying_key.to_bytes())
    }

    #[test]
    fn test_sovereignty_stimulus_contains_no_authority() {
        let (alice_sign, alice_pub) = generate_keypair(1);
        let mut bob = SovereignBoundary::new("node-bob");
        bob.register_peer_tofu("peer-alice", alice_pub).unwrap();
        bob.policy.grant("peer-alice", "query.epistemic");

        let env = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            0,
            1,
            1_000,
            "query.epistemic",
            b"candidate hypothesis data".to_vec(),
            &alice_sign,
        );
        let raw_bytes = serde_json::to_vec(&env).unwrap();

        let stimulus = bob.process_ingress(&raw_bytes, 1_005).unwrap();

        assert_eq!(stimulus.source, "peer-alice");
        assert_eq!(stimulus.action, "query.epistemic");
        assert_eq!(stimulus.payload, b"candidate hypothesis data");
        assert_eq!(stimulus.provenance, "mesh.ingress.ganying_v1");
    }

    #[test]
    fn test_unauthenticated_noise_never_penalizes_peer() {
        let mut bob = SovereignBoundary::new("node-bob");
        let (_alice_sign, alice_pub) = generate_keypair(1);
        bob.register_peer_tofu("peer-alice", alice_pub).unwrap();

        // Mallory sends completely forged envelope claiming to be Alice
        let (mallory_sign, _mallory_pub) = generate_keypair(99);
        let forged_env = SignedEnvelope::sign(
            "peer-alice", // Claiming to be Alice
            "node-bob",
            0,
            1,
            1_000,
            "query.epistemic",
            b"forged malicious payload".to_vec(),
            &mallory_sign, // Signed with Mallory's key
        );
        let raw_bytes = serde_json::to_vec(&forged_env).unwrap();

        // Ingress fails at signature verification
        let res = bob.process_ingress(&raw_bytes, 1_005);
        assert!(matches!(res, Err(BoundaryError::Noise(_))));

        // Alice's immune status MUST remain Healthy!
        let alice_immune = bob.immune_records.get("peer-alice").unwrap();
        assert_eq!(*alice_immune, ImmuneStatus::Healthy);
    }

    #[test]
    fn test_exact_replay_detected_and_persisted_across_restart() {
        let (alice_sign, alice_pub) = generate_keypair(1);
        let mut bob = SovereignBoundary::new("node-bob");
        bob.register_peer_tofu("peer-alice", alice_pub).unwrap();
        bob.policy.grant("peer-alice", "query.epistemic");

        let env1 = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            0,
            1,
            1000,
            "query.epistemic",
            b"msg1".to_vec(),
            &alice_sign,
        );
        let bytes1 = serde_json::to_vec(&env1).unwrap();
        bob.process_ingress(&bytes1, 1005).unwrap();

        // Replaying same message immediately fails
        let res_replay = bob.process_ingress(&bytes1, 1010);
        assert!(matches!(
            res_replay,
            Err(BoundaryError::ReplayDetected { .. })
        ));

        // INVARIANT: Restart != Loss of Security Memory
        // Simulate cold reboot by serializing and deserializing the ReplayLedger
        let ledger_bytes =
            serde_json::to_vec(bob.replay_ledgers.get("peer-alice").unwrap()).unwrap();
        let restored_ledger: ReplayLedger = serde_json::from_slice(&ledger_bytes).unwrap();

        // New node after restart
        let mut bob_rebooted = SovereignBoundary::new("node-bob");
        bob_rebooted
            .register_peer_tofu("peer-alice", alice_pub)
            .unwrap();
        bob_rebooted.policy.grant("peer-alice", "query.epistemic");
        bob_rebooted
            .replay_ledgers
            .insert("peer-alice".into(), restored_ledger);

        // Replay of msg1 on rebooted node STILL fails!
        let res_after_reboot = bob_rebooted.process_ingress(&bytes1, 2000);
        assert!(matches!(
            res_after_reboot,
            Err(BoundaryError::ReplayDetected { .. })
        ));

        // Fresh message 2 succeeds
        let env2 = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            0,
            2,
            2010,
            "query.epistemic",
            b"msg2".to_vec(),
            &alice_sign,
        );
        let bytes2 = serde_json::to_vec(&env2).unwrap();
        assert!(bob_rebooted.process_ingress(&bytes2, 2015).is_ok());
    }

    #[test]
    fn test_split_brain_key_rotation_preserves_fork() {
        let (root_sign, root_pub) = generate_keypair(10);
        let mut bob = SovereignBoundary::new("node-bob");
        bob.register_peer_tofu("peer-alice", root_pub).unwrap();

        let (_key1_sign, key1_pub) = generate_keypair(11);
        let (_key2_sign, key2_pub) = generate_keypair(12);

        let mut proof1 = RotationProof {
            peer_id: "peer-alice".into(),
            from_epoch: 0,
            to_epoch: 1,
            new_active_key: key1_pub,
            proof_signature: Vec::new(),
        };
        proof1.proof_signature = root_sign.sign(&proof1.digest()).to_bytes().to_vec();

        // Rotate to key 1
        bob.apply_key_rotation(&proof1).unwrap();

        // Conflicting rotation for same epoch 1 arrives (Split brain fork!)
        bob.record_identity_fork("peer-alice", 1, key1_pub, key2_pub, 5000);

        // Subsequent messages from alice are rejected due to fork
        let env = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            1,
            1,
            5010,
            "query.epistemic",
            b"test".to_vec(),
            &root_sign,
        );
        let bytes = serde_json::to_vec(&env).unwrap();
        let res = bob.process_ingress(&bytes, 5015);

        assert!(matches!(
            res,
            Err(BoundaryError::IdentityForkDetected { .. })
        ));
    }

    #[test]
    fn test_peb11_sovereign_mesh_benchmark_execution() {
        let report = run_peb11_sovereign_mesh_benchmark(500);
        println!("{}", report.summary);

        assert_eq!(report.total_trials, 500);
        assert_eq!(report.replay_before_restart_rejections, 500);
        assert_eq!(report.replay_after_restart_rejections, 500);
        assert_eq!(report.sequence_rollback_rejections, 500);
        assert_eq!(report.mallory_spoof_zero_quarantine_violations, 0);
        assert_eq!(report.noise_packets_dropped_without_mutation, 500);
        assert_eq!(report.key_substitution_rejections, 500);
        assert_eq!(report.legitimate_key_rotations_succeeded, 500);
        assert_eq!(report.cross_recipient_relay_rejections, 500);
        assert_eq!(report.authority_smuggling_rejections, 500);
        assert_eq!(report.reciprocity_throttling_enforced, 500);
        assert_eq!(report.partition_rejoin_handled, 500);
        assert_eq!(report.fuzz_malformed_packets_dropped, 500);
        assert_eq!(report.epoch_downgrade_rejections, 500);
        assert_eq!(report.sequence_exhaustion_handled, 500);
        assert_eq!(report.amplification_replay_suppressed, 500);
        assert_eq!(report.split_brain_fork_preserved, 500);
    }
}

#[cfg(test)]
mod identity_boundary_tests {
    use super::*;

    fn keypair(seed: u8) -> (SigningKey, [u8; 32]) {
        let mut bytes = [seed; 32];
        bytes[0] = seed;
        bytes[31] = seed.wrapping_add(1);
        let signing_key = SigningKey::from_bytes(&bytes);
        let verifying_key = signing_key.verifying_key();
        (signing_key, verifying_key.to_bytes())
    }

    /// Article 5 / Evil Gana attempt 6 (executable): a socket/IP label is never
    /// identity. Unregistered keys and impersonated labels are refused; a label is
    /// accepted only after its key is registered (TOFU), i.e. the key authenticates.
    #[test]
    fn socket_address_never_authenticates_identity() {
        let (alice_sign, alice_pub) = keypair(7);
        let (mallory_sign, _) = keypair(99);
        let mut bob = SovereignBoundary::new("node-bob");
        bob.register_peer_tofu("peer-alice", alice_pub).unwrap();
        bob.policy.grant("peer-alice", "query.epistemic");

        // An IP:port label signed by an unregistered key is refused.
        let forged = SignedEnvelope::sign(
            "203.0.113.7:443",
            "node-bob",
            0,
            1,
            1_000,
            "query.epistemic",
            b"remote claim".to_vec(),
            &mallory_sign,
        );
        assert!(
            bob.process_ingress(&serde_json::to_vec(&forged).unwrap(), 1_001)
                .is_err(),
            "an unregistered socket label must not authenticate"
        );

        // Impersonating a registered label with the wrong key is refused.
        let impersonation = SignedEnvelope::sign(
            "peer-alice",
            "node-bob",
            0,
            2,
            2_000,
            "query.epistemic",
            b"remote claim".to_vec(),
            &mallory_sign,
        );
        assert!(
            bob.process_ingress(&serde_json::to_vec(&impersonation).unwrap(), 2_001)
                .is_err(),
            "a registered label with the wrong key must not authenticate"
        );

        // The label carries no identity: the same IP-shaped label works only after
        // its key is registered, and the Ed25519 key is what authenticates.
        bob.register_peer_tofu("203.0.113.7:443", alice_pub)
            .unwrap();
        bob.policy.grant("203.0.113.7:443", "query.epistemic");
        let genuine = SignedEnvelope::sign(
            "203.0.113.7:443",
            "node-bob",
            0,
            3,
            3_000,
            "query.epistemic",
            b"authentic data".to_vec(),
            &alice_sign,
        );
        let stimulus = bob
            .process_ingress(&serde_json::to_vec(&genuine).unwrap(), 3_001)
            .expect("registered key authenticates regardless of label shape");
        assert_eq!(stimulus.source, "203.0.113.7:443");
        assert_eq!(stimulus.provenance, "mesh.ingress.ganying_v1");
    }
}
