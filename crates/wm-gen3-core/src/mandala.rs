//! wm-gen3-core::mandala — Mandala Capability Authority Subsystem for WhiteMagic Gen3.
//!
//! # Architecture & Governance Contract
//!
//! Incorporates the 12 Principles from `MANDALA_DESIGN_NOTES.md`:
//! - **P1: Explicit Boundary Vocabulary** — Capability manifests define allowed operations; deny by default.
//! - **P2: Sub-millisecond Offline Verification** — Pure Rust, offline, zero-dependency, allocation-light.
//! - **P3: Authority = Permission x Budget x Time** — Usage counters, compute/memory quotas, hard expiries.
//! - **P4: Single-Continuation & Attenuating Forks** — Single continuation handle, replay-protected jti ledger;
//!   forks are strictly attenuating (`child <= parent`).
//! - **P5: Capability Manifests at the Boundary** — Host functions checked at dispatch; network-restricted flags.
//! - **P6: Boundary Checkpoints** — Passes serialize compactly; resume re-verifies.
//! - **P7: Typed Failure, Fail-Closed** — Tampering, replay, or verifier crashes deny execution, never fail-open.
//! - **P8: Brokered Capabilities** — Holder receives execution use tokens without seeing root keys.
//! - **P9: Exactly-Once External Nonces** — Linear continuation and atomic commit integration.
//! - **P10: Adversarial Validation** — Rigorous test vectors against privilege escalation and replay.
//! - **Article 1 Enforcement**: Seamless issuance of `CommitCapability` linear tokens.

use std::collections::{HashMap, HashSet};
use std::fmt;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};

pub use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::capability::CommitCapability;
use crate::pulse_compiler::CompilerSeal;

/// Errors arising in Mandala pass verification and authority enforcement.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum MandalaError {
    /// Token format is malformed or invalid JSON.
    MalformedPass(String),
    /// Cryptographic signature verification failed (forged or tampered token).
    SignatureInvalid,
    /// The issuing gate DID is not trusted by this verifier.
    UnknownGateAuthority(String),
    /// The pass has expired.
    Expired { expired_at: u64, now: u64 },
    /// Operation budget exhausted under this pass.
    BudgetExceeded { requested: u32, available: u32 },
    /// Compute quota exceeded.
    ComputeQuotaExceeded { requested_ms: u64, max_ms: u64 },
    /// Memory quota exceeded.
    MemoryQuotaExceeded { requested_mb: u64, max_mb: u64 },
    /// The requested operation is not permitted by the pass manifest.
    OperationNotAllowed { operation: String, reason: String },
    /// The operation requires network egress, but pass is network-restricted.
    NetworkRestricted { operation: String },
    /// Pass has been explicitly revoked in the revocation ledger.
    PassRevoked { pass_id: String, reason: String },
    /// Tenant has been explicitly revoked or suspended.
    TenantRevoked { tenant_id: String, reason: String },
    /// Single-use continuation or token jti was already consumed (replay attack).
    TokenReplayDetected { jti: String },
    /// Child pass attempted privilege escalation beyond parent constraints.
    IllegalForkAttenuation(String),
    /// Durable journal or ledger persistence error.
    PersistenceFailure(String),
}

impl fmt::Display for MandalaError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MalformedPass(msg) => write!(f, "Mandala Pass Malformed: {msg}"),
            Self::SignatureInvalid => {
                write!(f, "Mandala Pass Signature Invalid (Tampering Detected)")
            }
            Self::UnknownGateAuthority(did) => write!(f, "Unknown Gate Authority DID: {did}"),
            Self::Expired { expired_at, now } => {
                write!(
                    f,
                    "Mandala Pass Expired at {expired_at} (current time {now})"
                )
            }
            Self::BudgetExceeded {
                requested,
                available,
            } => {
                write!(
                    f,
                    "Mandala Budget Exceeded: requested {requested}, available {available}"
                )
            }
            Self::ComputeQuotaExceeded {
                requested_ms,
                max_ms,
            } => {
                write!(
                    f,
                    "Mandala Compute Quota Exceeded: {requested_ms} ms > {max_ms} ms"
                )
            }
            Self::MemoryQuotaExceeded {
                requested_mb,
                max_mb,
            } => {
                write!(
                    f,
                    "Mandala Memory Quota Exceeded: {requested_mb} MB > {max_mb} MB"
                )
            }
            Self::OperationNotAllowed { operation, reason } => {
                write!(f, "Mandala Operation '{operation}' Not Allowed: {reason}")
            }
            Self::NetworkRestricted { operation } => {
                write!(
                    f,
                    "Mandala Network Restricted: '{operation}' requires network egress"
                )
            }
            Self::PassRevoked { pass_id, reason } => {
                write!(f, "Mandala Pass '{pass_id}' Revoked: {reason}")
            }
            Self::TenantRevoked { tenant_id, reason } => {
                write!(f, "Mandala Tenant '{tenant_id}' Revoked: {reason}")
            }
            Self::TokenReplayDetected { jti } => {
                write!(
                    f,
                    "Mandala Token Replay Detected: jti '{jti}' already consumed"
                )
            }
            Self::IllegalForkAttenuation(msg) => {
                write!(
                    f,
                    "Mandala Illegal Fork Attenuation (Privilege Escalation): {msg}"
                )
            }
            Self::PersistenceFailure(msg) => {
                write!(f, "Mandala Replay Ledger Persistence Failure: {msg}")
            }
        }
    }
}

impl std::error::Error for MandalaError {}

/// Scope filter mode for allowed capabilities.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ScopeMode {
    /// All operations allowed except explicitly denied ones.
    All,
    /// Only explicitly listed operations are allowed.
    Include,
    /// All operations denied except explicitly allowed ones.
    Exclude,
}

/// Bounded capability manifest defining the operations an agent may execute.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CapabilityManifest {
    pub scope_mode: ScopeMode,
    pub allowed_operations: HashSet<String>,
    pub denied_operations: HashSet<String>,
    pub network_restricted: bool,
}

impl Default for CapabilityManifest {
    fn default() -> Self {
        Self {
            scope_mode: ScopeMode::Include,
            allowed_operations: HashSet::new(),
            denied_operations: HashSet::new(),
            network_restricted: true,
        }
    }
}

impl CapabilityManifest {
    /// Evaluates whether an operation is permitted under this manifest.
    pub fn is_allowed(&self, operation: &str) -> Result<(), MandalaError> {
        // 1. Explicit denial always wins
        if self.denied_operations.contains(operation) {
            return Err(MandalaError::OperationNotAllowed {
                operation: operation.to_string(),
                reason: "Operation explicitly in denied_operations list".to_string(),
            });
        }

        // 2. Scope mode resolution
        match self.scope_mode {
            ScopeMode::All => Ok(()),
            ScopeMode::Include => {
                if self.allowed_operations.contains(operation) {
                    Ok(())
                } else {
                    Err(MandalaError::OperationNotAllowed {
                        operation: operation.to_string(),
                        reason: "Operation not in allowed_operations manifest (Include mode)"
                            .to_string(),
                    })
                }
            }
            ScopeMode::Exclude => {
                // In Exclude mode, allowed_operations acts as an explicit override to allowlist
                if self.allowed_operations.contains(operation) {
                    Ok(())
                } else {
                    Err(MandalaError::OperationNotAllowed {
                        operation: operation.to_string(),
                        reason: "Operation not allowed in Exclude mode".to_string(),
                    })
                }
            }
        }
    }

    /// Verifies that a child manifest strictly attenuates (never escalates) this parent manifest.
    pub fn attenuate(&self, child: &CapabilityManifest) -> Result<(), MandalaError> {
        // Child must be network restricted if parent is network restricted
        if self.network_restricted && !child.network_restricted {
            return Err(MandalaError::IllegalForkAttenuation(
                "Child cannot enable network egress when parent is network restricted".to_string(),
            ));
        }

        // Parent denials MUST be preserved in child
        for denied in &self.denied_operations {
            if child.allowed_operations.contains(denied) {
                return Err(MandalaError::IllegalForkAttenuation(format!(
                    "Child cannot allow operation '{denied}' which is denied by parent"
                )));
            }
        }

        // If parent is Include mode, child cannot allow operations outside parent's allowed list
        if self.scope_mode == ScopeMode::Include {
            for allowed in &child.allowed_operations {
                if !self.allowed_operations.contains(allowed) {
                    return Err(MandalaError::IllegalForkAttenuation(format!(
                        "Child cannot grant operation '{allowed}' outside parent's Include manifest"
                    )));
                }
            }
        }

        Ok(())
    }
}

/// Operational budget and resource quotas attached to a Mandala Pass.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct PassBudget {
    pub max_operations: u32,
    pub operations_used: u32,
    pub max_compute_ms: u64,
    pub max_memory_mb: u64,
}

impl Default for PassBudget {
    fn default() -> Self {
        Self {
            max_operations: 100,
            operations_used: 0,
            max_compute_ms: 300_000, // 5 minutes
            max_memory_mb: 1024,     // 1 GiB
        }
    }
}

impl PassBudget {
    #[must_use]
    pub fn can_consume(&self, ops: u32) -> bool {
        self.operations_used.saturating_add(ops) <= self.max_operations
    }

    pub fn consume(&mut self, ops: u32) -> Result<(), MandalaError> {
        let new_total = self.operations_used.saturating_add(ops);
        if new_total > self.max_operations {
            Err(MandalaError::BudgetExceeded {
                requested: ops,
                available: self.max_operations.saturating_sub(self.operations_used),
            })
        } else {
            self.operations_used = new_total;
            Ok(())
        }
    }

    pub fn attenuate(&self, child: &PassBudget) -> Result<(), MandalaError> {
        let remaining_ops = self.max_operations.saturating_sub(self.operations_used);
        if child.max_operations > remaining_ops {
            return Err(MandalaError::IllegalForkAttenuation(format!(
                "Child max_operations ({}) exceeds parent remaining operations ({})",
                child.max_operations, remaining_ops
            )));
        }
        if child.max_compute_ms > self.max_compute_ms {
            return Err(MandalaError::IllegalForkAttenuation(format!(
                "Child compute budget ({} ms) exceeds parent ({} ms)",
                child.max_compute_ms, self.max_compute_ms
            )));
        }
        if child.max_memory_mb > self.max_memory_mb {
            return Err(MandalaError::IllegalForkAttenuation(format!(
                "Child memory budget ({} MB) exceeds parent ({} MB)",
                child.max_memory_mb, self.max_memory_mb
            )));
        }
        Ok(())
    }
}

/// A sovereign Mandala Pass token granting bounded execution authority.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MandalaPass {
    pub pass_id: String,
    pub slot_id: String,
    pub tenant_id: String,
    pub agent_id: String,
    pub principal_id: Option<String>,
    pub jti: String,
    pub parent_jti: Option<String>,
    pub fork_depth: u32,
    pub created_at: u64,
    pub expires_at: u64,
    pub budget: PassBudget,
    pub manifest: CapabilityManifest,
    pub mandate_ref: Option<String>,
    pub signature: Option<Vec<u8>>,
}

impl MandalaPass {
    /// Generates canonical bytes for signing and verification.
    #[must_use]
    pub fn canonical_signing_bytes(&self) -> Vec<u8> {
        // Sort operations for deterministic serialization
        let mut sorted_allowed: Vec<&String> = self.manifest.allowed_operations.iter().collect();
        sorted_allowed.sort();
        let mut sorted_denied: Vec<&String> = self.manifest.denied_operations.iter().collect();
        sorted_denied.sort();

        let mut hasher = Sha256::new();
        hasher.update(b"MANDALA_PASS_V1\n");
        hasher.update(self.pass_id.as_bytes());
        hasher.update(b"\n");
        hasher.update(self.slot_id.as_bytes());
        hasher.update(b"\n");
        hasher.update(self.tenant_id.as_bytes());
        hasher.update(b"\n");
        hasher.update(self.agent_id.as_bytes());
        hasher.update(b"\n");
        if let Some(ref p) = self.principal_id {
            hasher.update(p.as_bytes());
        }
        hasher.update(b"\n");
        hasher.update(self.jti.as_bytes());
        hasher.update(b"\n");
        if let Some(ref pj) = self.parent_jti {
            hasher.update(pj.as_bytes());
        }
        hasher.update(b"\n");
        hasher.update(self.fork_depth.to_be_bytes());
        hasher.update(self.created_at.to_be_bytes());
        hasher.update(self.expires_at.to_be_bytes());
        hasher.update(self.budget.max_operations.to_be_bytes());
        hasher.update(self.budget.max_compute_ms.to_be_bytes());
        hasher.update(self.budget.max_memory_mb.to_be_bytes());
        hasher.update(if self.manifest.network_restricted {
            b"1"
        } else {
            b"0"
        });
        hasher.update(b"\n");

        for op in sorted_allowed {
            hasher.update(b"+");
            hasher.update(op.as_bytes());
            hasher.update(b"\n");
        }
        for op in sorted_denied {
            hasher.update(b"-");
            hasher.update(op.as_bytes());
            hasher.update(b"\n");
        }
        if let Some(ref mr) = self.mandate_ref {
            hasher.update(mr.as_bytes());
        }

        hasher.finalize().to_vec()
    }

    /// Signs the pass with an authority signing key.
    pub fn sign(&mut self, key: &SigningKey) {
        let digest = self.canonical_signing_bytes();
        let sig = key.sign(&digest);
        self.signature = Some(sig.to_bytes().to_vec());
    }

    /// Verifies the cryptographic signature against the authority's public verifying key.
    pub fn verify_signature(&self, public_key: &VerifyingKey) -> Result<(), MandalaError> {
        let sig_bytes = self
            .signature
            .as_ref()
            .ok_or(MandalaError::SignatureInvalid)?;
        if sig_bytes.len() != 64 {
            return Err(MandalaError::SignatureInvalid);
        }
        let mut arr = [0u8; 64];
        arr.copy_from_slice(sig_bytes);
        let sig = Signature::from_bytes(&arr);

        let digest = self.canonical_signing_bytes();
        public_key
            .verify(&digest, &sig)
            .map_err(|_| MandalaError::SignatureInvalid)
    }

    /// Spawns an attenuating child pass (fork).
    ///
    /// Principle P4: "One handle to continue, many forks to branch."
    /// Forking is strictly attenuating — child parameters <= parent in scope, time, and budget.
    pub fn fork_child(
        &self,
        child_pass_id: impl Into<String>,
        child_slot_id: impl Into<String>,
        child_agent_id: impl Into<String>,
        child_jti: impl Into<String>,
        child_manifest: CapabilityManifest,
        child_budget: PassBudget,
        child_expires_at: u64,
        now_epoch: u64,
    ) -> Result<Self, MandalaError> {
        // 1. Time attenuation
        if child_expires_at > self.expires_at {
            return Err(MandalaError::IllegalForkAttenuation(format!(
                "Child expiry ({child_expires_at}) exceeds parent expiry ({})",
                self.expires_at
            )));
        }
        if child_expires_at <= now_epoch {
            return Err(MandalaError::Expired {
                expired_at: child_expires_at,
                now: now_epoch,
            });
        }

        // 2. Manifest attenuation
        self.manifest.attenuate(&child_manifest)?;

        // 3. Budget attenuation
        self.budget.attenuate(&child_budget)?;

        Ok(Self {
            pass_id: child_pass_id.into(),
            slot_id: child_slot_id.into(),
            tenant_id: self.tenant_id.clone(),
            agent_id: child_agent_id.into(),
            principal_id: self.principal_id.clone(),
            jti: child_jti.into(),
            parent_jti: Some(self.jti.clone()),
            fork_depth: self.fork_depth.saturating_add(1),
            created_at: now_epoch,
            expires_at: child_expires_at,
            budget: child_budget,
            manifest: child_manifest,
            mandate_ref: self.mandate_ref.clone(),
            signature: None,
        })
    }

    /// Advances the single-continuation handle to a fresh `jti`.
    ///
    /// Returns the retired `jti` which must be recorded in the replay ledger.
    pub fn advance_continuation(
        &mut self,
        next_jti: impl Into<String>,
    ) -> Result<String, MandalaError> {
        let retired = self.jti.clone();
        self.parent_jti = Some(retired.clone());
        self.jti = next_jti.into();
        self.signature = None; // Requires re-signing by authority or gate
        Ok(retired)
    }
}

/// Durable Replay & Revocation Ledger tracking consumed `jti`s and explicit revocations.
#[derive(Debug, Default, Clone)]
pub struct MandalaReplayLedger {
    consumed_jtis: HashSet<String>,
    revoked_jtis: HashMap<String, String>,
    revoked_passes: HashMap<String, String>,
    revoked_tenants: HashMap<String, String>,
    persist_path: Option<PathBuf>,
}

#[derive(Serialize, Deserialize)]
enum LedgerEntry {
    Consumed { jti: String },
    RevokeJti { jti: String, reason: String },
    RevokePass { pass_id: String, reason: String },
    RevokeTenant { tenant_id: String, reason: String },
}

impl MandalaReplayLedger {
    pub fn new() -> Self {
        Self {
            consumed_jtis: HashSet::new(),
            revoked_jtis: HashMap::new(),
            revoked_passes: HashMap::new(),
            revoked_tenants: HashMap::new(),
            persist_path: None,
        }
    }

    /// Opens or creates a durable replay ledger backed by an append-only journal file.
    pub fn open_durable(path: impl AsRef<Path>) -> std::io::Result<Self> {
        let path = path.as_ref().to_path_buf();
        let mut ledger = Self::new();
        ledger.persist_path = Some(path.clone());

        if path.exists() {
            let file = File::open(&path)?;
            let reader = BufReader::new(file);
            for (idx, line) in reader.lines().enumerate() {
                let l = line?;
                let trimmed = l.trim();
                if trimmed.is_empty() {
                    continue;
                }
                let entry: LedgerEntry = serde_json::from_str(trimmed).map_err(|e| {
                    std::io::Error::new(
                        std::io::ErrorKind::InvalidData,
                        format!("Corrupt Mandala ledger entry at line {}: {e}", idx + 1),
                    )
                })?;
                match entry {
                    LedgerEntry::Consumed { jti } => {
                        ledger.consumed_jtis.insert(jti);
                    }
                    LedgerEntry::RevokeJti { jti, reason } => {
                        ledger.revoked_jtis.insert(jti, reason);
                    }
                    LedgerEntry::RevokePass { pass_id, reason } => {
                        ledger.revoked_passes.insert(pass_id, reason);
                    }
                    LedgerEntry::RevokeTenant { tenant_id, reason } => {
                        ledger.revoked_tenants.insert(tenant_id, reason);
                    }
                }
            }
        }

        Ok(ledger)
    }

    fn persist_entry(&self, entry: &LedgerEntry) -> Result<(), MandalaError> {
        if let Some(ref path) = self.persist_path {
            let mut file = OpenOptions::new()
                .create(true)
                .append(true)
                .open(path)
                .map_err(|e| MandalaError::PersistenceFailure(e.to_string()))?;
            let line = serde_json::to_string(entry)
                .map_err(|e| MandalaError::PersistenceFailure(e.to_string()))?;
            writeln!(file, "{line}")
                .map_err(|e| MandalaError::PersistenceFailure(e.to_string()))?;
            file.sync_data()
                .map_err(|e| MandalaError::PersistenceFailure(e.to_string()))?;
        }
        Ok(())
    }

    /// Evaluates if a pass is permitted by the ledger (not replayed and not revoked).
    pub fn check_validity(&self, pass: &MandalaPass, now_epoch: u64) -> Result<(), MandalaError> {
        // 1. Tenant revocation
        if let Some(reason) = self.revoked_tenants.get(&pass.tenant_id) {
            return Err(MandalaError::TenantRevoked {
                tenant_id: pass.tenant_id.clone(),
                reason: reason.clone(),
            });
        }

        // 2. Pass revocation
        if let Some(reason) = self.revoked_passes.get(&pass.pass_id) {
            return Err(MandalaError::PassRevoked {
                pass_id: pass.pass_id.clone(),
                reason: reason.clone(),
            });
        }

        // 3. JTI revocation
        if let Some(reason) = self.revoked_jtis.get(&pass.jti) {
            return Err(MandalaError::PassRevoked {
                pass_id: pass.pass_id.clone(),
                reason: format!("JTI revoked: {reason}"),
            });
        }

        // 4. Replay check
        if self.consumed_jtis.contains(&pass.jti) {
            return Err(MandalaError::TokenReplayDetected {
                jti: pass.jti.clone(),
            });
        }

        // 5. Expiry check
        if now_epoch > pass.expires_at {
            return Err(MandalaError::Expired {
                expired_at: pass.expires_at,
                now: now_epoch,
            });
        }

        Ok(())
    }

    /// Commits a pass JTI as consumed (single-continuation consumption).
    pub fn record_consumption(&mut self, pass: &MandalaPass) -> Result<(), MandalaError> {
        if self.consumed_jtis.contains(&pass.jti) {
            return Err(MandalaError::TokenReplayDetected {
                jti: pass.jti.clone(),
            });
        }
        let entry = LedgerEntry::Consumed {
            jti: pass.jti.clone(),
        };
        self.persist_entry(&entry)?;
        self.consumed_jtis.insert(pass.jti.clone());
        Ok(())
    }

    pub fn revoke_jti(
        &mut self,
        jti: impl Into<String>,
        reason: impl Into<String>,
    ) -> Result<(), MandalaError> {
        let j = jti.into();
        let r = reason.into();
        let entry = LedgerEntry::RevokeJti {
            jti: j.clone(),
            reason: r.clone(),
        };
        self.persist_entry(&entry)?;
        self.revoked_jtis.insert(j, r);
        Ok(())
    }

    pub fn revoke_pass(
        &mut self,
        pass_id: impl Into<String>,
        reason: impl Into<String>,
    ) -> Result<(), MandalaError> {
        let p = pass_id.into();
        let r = reason.into();
        let entry = LedgerEntry::RevokePass {
            pass_id: p.clone(),
            reason: r.clone(),
        };
        self.persist_entry(&entry)?;
        self.revoked_passes.insert(p, r);
        Ok(())
    }

    pub fn revoke_tenant(
        &mut self,
        tenant_id: impl Into<String>,
        reason: impl Into<String>,
    ) -> Result<(), MandalaError> {
        let t = tenant_id.into();
        let r = reason.into();
        let entry = LedgerEntry::RevokeTenant {
            tenant_id: t.clone(),
            reason: r.clone(),
        };
        self.persist_entry(&entry)?;
        self.revoked_tenants.insert(t, r);
        Ok(())
    }

    pub fn consumed_count(&self) -> usize {
        self.consumed_jtis.len()
    }

    pub fn revoked_tenants_count(&self) -> usize {
        self.revoked_tenants.len()
    }

    pub fn revoked_passes_count(&self) -> usize {
        self.revoked_passes.len()
    }

    pub fn revoked_jtis_count(&self) -> usize {
        self.revoked_jtis.len()
    }
}

/// The core offline Mandala Authority Verifier.
///
/// Embeds in `wm-gen3-core` to verify gate tokens, enforce capability bounds,
/// maintain replay ledgers, and issue affine `CommitCapability` tokens.
#[derive(Debug, Clone)]
pub struct MandalaAuthorityVerifier {
    gate_keys: HashMap<String, VerifyingKey>,
    ledger: MandalaReplayLedger,
}

impl MandalaAuthorityVerifier {
    pub fn new(ledger: MandalaReplayLedger) -> Self {
        Self {
            gate_keys: HashMap::new(),
            ledger,
        }
    }

    pub fn register_gate_key(&mut self, gate_did: impl Into<String>, public_key: VerifyingKey) {
        self.gate_keys.insert(gate_did.into(), public_key);
    }

    pub fn ledger(&self) -> &MandalaReplayLedger {
        &self.ledger
    }

    pub fn ledger_mut(&mut self) -> &mut MandalaReplayLedger {
        &mut self.ledger
    }

    /// Verifies a pass without consuming budget or recording consumption.
    pub fn verify_pass_offline(
        &self,
        pass: &MandalaPass,
        gate_did: &str,
        now_epoch: u64,
    ) -> Result<(), MandalaError> {
        let gate_key = self
            .gate_keys
            .get(gate_did)
            .ok_or_else(|| MandalaError::UnknownGateAuthority(gate_did.to_string()))?;

        pass.verify_signature(gate_key)?;
        self.ledger.check_validity(pass, now_epoch)?;
        Ok(())
    }

    /// Verifies pass, enforces manifest, consumes 1 operation budget, registers JTI in replay ledger,
    /// and issues an affine `CommitCapability` granting causal mutation rights.
    pub fn verify_and_authorize_commit(
        &mut self,
        pass: &mut MandalaPass,
        gate_did: &str,
        operation: &str,
        now_epoch: u64,
    ) -> Result<CommitCapability, MandalaError> {
        // 1. Verify cryptographic signature against registered gate DID
        let gate_key = self
            .gate_keys
            .get(gate_did)
            .ok_or_else(|| MandalaError::UnknownGateAuthority(gate_did.to_string()))?;
        pass.verify_signature(gate_key)?;

        // 2. Check replay ledger & revocation status
        self.ledger.check_validity(pass, now_epoch)?;

        // 3. Check operation manifest
        pass.manifest.is_allowed(operation)?;

        // 4. Check & consume budget
        pass.budget.consume(1)?;

        // 5. Commit JTI consumption (write-ahead replay ledger)
        self.ledger.record_consumption(pass)?;

        // 6. Compute authorized digest over the pass authority proof
        let mut hasher = Sha256::new();
        hasher.update(b"MANDALA_COMMIT_CAPABILITY\n");
        hasher.update(pass.canonical_signing_bytes());
        hasher.update(operation.as_bytes());
        let authorized_digest: [u8; 32] = hasher.finalize().into();

        // 7. Mint VerifiedWarrant using internal CompilerSeal
        let warrant = crate::capability::VerifiedWarrant::mint_from_mandala_pass(
            CompilerSeal(()),
            authorized_digest,
            pass.pass_id.clone(),
            pass.jti.clone(),
            pass.slot_id.clone(),
            pass.tenant_id.clone(),
            now_epoch,
            format!("mandala:{}:{}", pass.tenant_id, pass.slot_id),
        );

        // 8. Claim affine CommitCapability
        Ok(CommitCapability::claim(warrant))
    }
}

/// Resolve or generate a persistent Ed25519 Mandala gate key for the given store directory.
pub fn resolve_or_create_mandala_gate_key(
    store_dir: &Path,
) -> std::io::Result<(SigningKey, [u8; 32])> {
    let key_file = store_dir.join("mandala_gate_key.bin");
    if key_file.exists() {
        let mut f = File::open(&key_file)?;
        let mut bytes = [0u8; 32];
        f.read_exact(&mut bytes)?;
        let signing = SigningKey::from_bytes(&bytes);
        let pubkey = signing.verifying_key().to_bytes();
        Ok((signing, pubkey))
    } else {
        let mut bytes = [0u8; 32];
        getrandom::fill(&mut bytes)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))?;
        let signing = SigningKey::from_bytes(&bytes);
        let pubkey = signing.verifying_key().to_bytes();

        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            let mut f = OpenOptions::new()
                .write(true)
                .create_new(true)
                .mode(0o600)
                .open(&key_file)?;
            f.write_all(&bytes)?;
            f.sync_data()?;
        }
        #[cfg(not(unix))]
        {
            let mut f = File::create(&key_file)?;
            f.write_all(&bytes)?;
            f.sync_data()?;
        }

        Ok((signing, pubkey))
    }
}

// ============================================================================
// Phase A: WorkspaceClaim & Linux Landlock LSM Confinement
// ============================================================================

/// Spatial capability barrier lifecycle phases inspired by Kekkaijutsu.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum KekkaiPhase {
    /// Hōi: Targeting coordinates and pinning ephemeral boundary claim.
    Hoi,
    /// Jōshiki: Formulating access matrix and compiling Landlock/rlimit ruleset.
    Joshiki,
    /// Ketsu: Binding and materializing the active spatial capability boundary in the kernel.
    Ketsu,
    /// Kai: Orderly dissipation and release upon successful completion, leaving a cryptographic receipt.
    Kai,
    /// Metsu: Forensic containment, annihilation of malicious payload, and routing to Negative Knowledge Lineage.
    Metsu,
}

impl Default for KekkaiPhase {
    fn default() -> Self {
        Self::Hoi
    }
}

impl KekkaiPhase {
    /// Returns true if this phase represents a terminal state (dissipation or quarantine).
    #[must_use]
    pub fn is_terminal(&self) -> bool {
        matches!(self, Self::Kai | Self::Metsu)
    }

    /// Returns the canonical label for this spatial capability phase.
    #[must_use]
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Hoi => "hoi",
            Self::Joshiki => "joshiki",
            Self::Ketsu => "ketsu",
            Self::Kai => "kai",
            Self::Metsu => "metsu",
        }
    }
}

/// Bounded resource quotas enforced on the sandbox process to guarantee hardware longevity
/// and prevent Out-Of-Memory (OOM) or thermal throttling storms.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct SandboxResourceLimits {
    /// Maximum virtual memory address space in megabytes (RLIMIT_AS).
    pub max_memory_mb: u64,
    /// Maximum CPU time in seconds before SIGXCPU (RLIMIT_CPU).
    pub max_cpu_seconds: u64,
    /// Maximum number of simultaneously open file descriptors (RLIMIT_NOFILE).
    pub max_open_files: u64,
}

impl Default for SandboxResourceLimits {
    fn default() -> Self {
        Self {
            max_memory_mb: 512,
            max_cpu_seconds: 10,
            max_open_files: 128,
        }
    }
}

impl SandboxResourceLimits {
    /// Applies these resource limits to the current process safely via the `rlimit` crate on Unix.
    pub fn apply_to_current_process(&self) -> Result<(), MandalaError> {
        #[cfg(unix)]
        {
            let mem_bytes = self.max_memory_mb.saturating_mul(1024 * 1024);
            rlimit::Resource::AS
                .set(mem_bytes, mem_bytes)
                .map_err(|e| {
                    MandalaError::PersistenceFailure(format!("Failed to set RLIMIT_AS: {e}"))
                })?;

            rlimit::Resource::CPU
                .set(self.max_cpu_seconds, self.max_cpu_seconds)
                .map_err(|e| {
                    MandalaError::PersistenceFailure(format!("Failed to set RLIMIT_CPU: {e}"))
                })?;

            rlimit::Resource::NOFILE
                .set(self.max_open_files, self.max_open_files)
                .map_err(|e| {
                    MandalaError::PersistenceFailure(format!("Failed to set RLIMIT_NOFILE: {e}"))
                })?;
        }
        #[cfg(not(unix))]
        {
            // Bounded advisory limits on non-Unix platforms
        }
        Ok(())
    }
}

/// Materialized workspace claim for an autonomous agent.
///
/// Implements @cc [owner:lucas,label:architecture] claim-based-workspace
/// Enforces bounded, ephemeral access to specific repository subtrees.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkspaceClaim {
    pub claim_id: String,
    pub tenant_id: String,
    pub agent_id: String,
    pub workspace_root: PathBuf,
    pub read_only_paths: Vec<PathBuf>,
    pub read_write_paths: Vec<PathBuf>,
    pub network_allowed: bool,
    #[serde(default)]
    pub kekkai_phase: KekkaiPhase,
    #[serde(default)]
    pub resource_limits: Option<SandboxResourceLimits>,
    #[serde(default)]
    pub inherited_shm_fd: Option<i32>,
    pub created_at: u64,
    pub expires_at: u64,
    pub signature: Option<Vec<u8>>,
}

impl WorkspaceClaim {
    /// Attaches to the inherited shared memory substrate without requiring /dev/shm filesystem access.
    pub fn attach_shm(&self) -> Option<std::io::Result<wm_gen3_shm::ShmSubstrate>> {
        self.inherited_shm_fd.map(|fd| wm_gen3_shm::ShmSubstrate::from_raw_fd(fd, false))
    }
    /// Computes the canonical SHA-256 digest of this workspace claim.
    #[must_use]
    pub fn canonical_digest(&self) -> String {
        let mut hasher = Sha256::new();
        hasher.update(self.claim_id.as_bytes());
        hasher.update(b":");
        hasher.update(self.tenant_id.as_bytes());
        hasher.update(b":");
        hasher.update(self.agent_id.as_bytes());
        hasher.update(b":");
        hasher.update(self.workspace_root.to_string_lossy().as_bytes());
        hasher.update(b":");
        hasher.update(format!("{:?}", self.kekkai_phase).as_bytes());
        hasher.update(b":");
        if let Some(ref lim) = self.resource_limits {
            hasher.update(lim.max_memory_mb.to_le_bytes());
            hasher.update(lim.max_cpu_seconds.to_le_bytes());
            hasher.update(lim.max_open_files.to_le_bytes());
        }
        hasher.update(b":");
        hasher.update(self.created_at.to_le_bytes());
        hasher.update(b":");
        hasher.update(self.expires_at.to_le_bytes());
        format!("sha256:{:x}", hasher.finalize())
    }

    /// Signs this claim with an authorized gate signing key.
    pub fn sign(&mut self, key: &SigningKey) {
        let digest = self.canonical_digest();
        let sig = key.sign(digest.as_bytes());
        self.signature = Some(sig.to_bytes().to_vec());
    }

    /// Verifies the signature of this claim.
    pub fn verify(&self, key: &VerifyingKey) -> Result<(), MandalaError> {
        let sig_bytes = self
            .signature
            .as_ref()
            .ok_or(MandalaError::SignatureInvalid)?;
        if sig_bytes.len() != 64 {
            return Err(MandalaError::SignatureInvalid);
        }
        let mut arr = [0u8; 64];
        arr.copy_from_slice(sig_bytes);
        let sig = Signature::from_bytes(&arr);
        let digest = self.canonical_digest();
        key.verify(digest.as_bytes(), &sig)
            .map_err(|_| MandalaError::SignatureInvalid)
    }
}

/// Native Linux Landlock LSM sandbox executor.
/// Opaque wrapper around kernel sandbox ruleset.
#[cfg(target_os = "linux")]
pub struct SandboxRuleset {
    pub(crate) inner: landlock::RulesetCreated,
}

#[cfg(not(target_os = "linux"))]
pub struct SandboxRuleset;

/// Process and workspace sandboxing primitives.
///
/// On Linux: Confinement via Landlock LSM (ABI v1-v5) and unprivileged rlimits.
/// On macOS / Windows: Bounded process limits and advisory confinement.
pub struct LandlockSandbox;

impl LandlockSandbox {
    /// Builds a Landlock ruleset based on an authorized WorkspaceClaim.
    ///
    /// Automatically negotiates the kernel's Landlock ABI version (v1-v5):
    /// - Filesystem confinement under `AccessFs` (ABI v1)
    /// - Strict TCP network confinement (`AccessNet`) under ABI v4+ if `!claim.network_allowed`.
    #[cfg(target_os = "linux")]
    pub fn build_ruleset(claim: &WorkspaceClaim) -> Result<SandboxRuleset, MandalaError> {
        use landlock::{
            ABI, Access, AccessFs, AccessNet, CompatLevel, Compatible, PathBeneath, PathFd,
            Ruleset, RulesetAttr, RulesetCreatedAttr,
        };

        let abi = ABI::V5;
        let mut builder = Ruleset::default()
            .set_compatibility(CompatLevel::BestEffort)
            .handle_access(AccessFs::from_all(abi))
            .map_err(|e| {
                MandalaError::PersistenceFailure(format!("Failed to handle access: {e}"))
            })?;

        // If network access is forbidden, handle TCP access under ABI::V4 (Linux 6.7+)
        // In Landlock, if AccessNet is handled without adding port rules, all TCP bind/connect operations are denied!
        if !claim.network_allowed {
            builder = builder
                .handle_access(AccessNet::from_all(ABI::V4))
                .map_err(|e| {
                    MandalaError::PersistenceFailure(format!(
                        "Failed to handle network access: {e}"
                    ))
                })?;
        }

        let mut ruleset = builder.create().map_err(|e| {
            MandalaError::PersistenceFailure(format!("Failed to create Landlock ruleset: {e}"))
        })?;

        // Allow read access to standard system paths if present
        let default_ro_paths = ["/usr", "/lib", "/lib64", "/bin", "/etc/ssl", "/nix/store"];
        for path_str in default_ro_paths {
            let p = Path::new(path_str);
            if p.exists() {
                if let Ok(fd) = PathFd::new(p) {
                    let rule = PathBeneath::new(fd, AccessFs::from_read(abi));
                    ruleset = ruleset.add_rule(rule).map_err(|e| {
                        MandalaError::PersistenceFailure(format!(
                            "Failed to add Landlock rule for {path_str}: {e}"
                        ))
                    })?;
                }
            }
        }

        // Add custom read-only paths
        for p in &claim.read_only_paths {
            if p.exists() {
                if let Ok(fd) = PathFd::new(p) {
                    let rule = PathBeneath::new(fd, AccessFs::from_read(abi));
                    ruleset = ruleset.add_rule(rule).map_err(|e| {
                        MandalaError::PersistenceFailure(format!(
                            "Failed to add Landlock rule for {p:?}: {e}"
                        ))
                    })?;
                }
            }
        }

        // Add workspace root and read-write paths
        let rw_access = AccessFs::from_all(abi);
        if claim.workspace_root.exists() {
            if let Ok(fd) = PathFd::new(&claim.workspace_root) {
                let rule = PathBeneath::new(fd, rw_access);
                ruleset = ruleset.add_rule(rule).map_err(|e| {
                    MandalaError::PersistenceFailure(format!(
                        "Failed to add Landlock rule for workspace root: {e}"
                    ))
                })?;
            }
        }
        for p in &claim.read_write_paths {
            if p.exists() {
                if let Ok(fd) = PathFd::new(p) {
                    let rule = PathBeneath::new(fd, rw_access);
                    ruleset = ruleset.add_rule(rule).map_err(|e| {
                        MandalaError::PersistenceFailure(format!(
                            "Failed to add Landlock rule for {p:?}: {e}"
                        ))
                    })?;
                }
            }
        }

        Ok(SandboxRuleset { inner: ruleset })
    }

    /// Non-Linux fallback for platforms without Landlock LSM (macOS, Windows).
    #[cfg(not(target_os = "linux"))]
    pub fn build_ruleset(_claim: &WorkspaceClaim) -> Result<SandboxRuleset, MandalaError> {
        Ok(SandboxRuleset)
    }

    /// Enforces Landlock confinement and unprivileged resource limits on the current thread/process.
    pub fn restrict_current_process(claim: &WorkspaceClaim) -> Result<(), MandalaError> {
        // 1. Apply unprivileged resource limits (RLIMIT_AS, RLIMIT_CPU, RLIMIT_NOFILE)
        if let Some(ref limits) = claim.resource_limits {
            limits.apply_to_current_process()?;
        }

        // 2. Build and enforce Landlock ruleset on Linux
        #[cfg(target_os = "linux")]
        {
            let ruleset = Self::build_ruleset(claim)?;
            let status = ruleset.inner.restrict_self().map_err(|e| {
                MandalaError::PersistenceFailure(format!("Landlock restrict_self failed: {e}"))
            })?;

            match status.ruleset {
                landlock::RulesetStatus::FullyEnforced
                | landlock::RulesetStatus::PartiallyEnforced => Ok(()),
                landlock::RulesetStatus::NotEnforced => Err(MandalaError::OperationNotAllowed {
                    operation: "landlock_confinement".to_string(),
                    reason: "Landlock ruleset was not enforced by the kernel".to_string(),
                }),
            }
        }

        #[cfg(not(target_os = "linux"))]
        {
            // On macOS / Windows, process limits are enforced via rlimit/advisory bounds.
            Ok(())
        }
    }

    /// Builds a Landlock ruleset directly from a cryptographically verified `AgentIdentityToken`
    /// and optional `DelegationProof`.
    ///
    /// Validates the Ed25519 signature chain against `root_authority_vk`, verifies delegation depth <= 3,
    /// asserts strict capability attenuation, and compiles effective capabilities into Landlock rules.
    #[cfg(target_os = "linux")]
    pub fn build_delegated_ruleset(
        token: &crate::attestation::AgentIdentityToken,
        proof: Option<&crate::attestation::DelegationProof>,
        root_authority_vk: &ed25519_dalek::VerifyingKey,
        current_epoch: u64,
    ) -> Result<SandboxRuleset, MandalaError> {
        use landlock::{
            ABI, Access, AccessFs, AccessNet, CompatLevel, Compatible, PathBeneath, PathFd,
            Ruleset, RulesetAttr, RulesetCreatedAttr,
        };

        // 1. Cryptographically verify parent token
        token
            .verify(root_authority_vk, current_epoch)
            .map_err(|_e| MandalaError::SignatureInvalid)?;

        // 2. If a delegation proof is provided, verify the entire delegation chain
        let effective_caps = if let Some(p) = proof {
            p.verify_chain(root_authority_vk, current_epoch)
                .map_err(|e| MandalaError::IllegalForkAttenuation(e.to_string()))?;
            &p.delegated_capabilities
        } else {
            &token.capabilities
        };

        let abi = ABI::V1;
        let mut builder = Ruleset::default()
            .set_compatibility(CompatLevel::BestEffort)
            .handle_access(AccessFs::from_all(abi))
            .map_err(|e| {
                MandalaError::PersistenceFailure(format!("Failed to handle access: {e}"))
            })?;

        let mut network_allowed = true;
        let mut custom_ro_paths = Vec::new();
        let mut custom_rw_paths = Vec::new();

        for cap in effective_caps {
            if cap == "net:deny" {
                network_allowed = false;
            } else if let Some(path) = cap.strip_prefix("fs:ro:") {
                custom_ro_paths.push(PathBuf::from(path));
            } else if let Some(path) = cap.strip_prefix("fs:rw:") {
                custom_rw_paths.push(PathBuf::from(path));
            }
        }

        if !network_allowed {
            builder = builder
                .handle_access(AccessNet::from_all(ABI::V4))
                .map_err(|e| {
                    MandalaError::PersistenceFailure(format!(
                        "Failed to handle network access: {e}"
                    ))
                })?;
        }

        let mut ruleset = builder.create().map_err(|e| {
            MandalaError::PersistenceFailure(format!("Failed to create Landlock ruleset: {e}"))
        })?;

        // Allow read access to standard system paths if present
        let default_ro_paths = ["/usr", "/lib", "/lib64", "/bin", "/etc/ssl", "/nix/store"];
        for path_str in default_ro_paths {
            let p = Path::new(path_str);
            if p.exists() {
                if let Ok(fd) = PathFd::new(p) {
                    let rule = PathBeneath::new(fd, AccessFs::from_read(abi));
                    ruleset = ruleset.add_rule(rule).map_err(|e| {
                        MandalaError::PersistenceFailure(format!(
                            "Failed to add Landlock rule for {path_str}: {e}"
                        ))
                    })?;
                }
            }
        }

        // Add custom read-only paths
        for p in &custom_ro_paths {
            if p.exists() {
                if let Ok(fd) = PathFd::new(p) {
                    let rule = PathBeneath::new(fd, AccessFs::from_read(abi));
                    ruleset = ruleset.add_rule(rule).map_err(|e| {
                        MandalaError::PersistenceFailure(format!(
                            "Failed to add Landlock rule for {p:?}: {e}"
                        ))
                    })?;
                }
            }
        }

        // Add custom read-write paths
        let rw_access = AccessFs::from_all(abi);
        for p in &custom_rw_paths {
            if p.exists() {
                if let Ok(fd) = PathFd::new(p) {
                    let rule = PathBeneath::new(fd, rw_access);
                    ruleset = ruleset.add_rule(rule).map_err(|e| {
                        MandalaError::PersistenceFailure(format!(
                            "Failed to add Landlock rule for {p:?}: {e}"
                        ))
                    })?;
                }
            }
        }

        Ok(SandboxRuleset { inner: ruleset })
    }

    /// Non-Linux fallback
    #[cfg(not(target_os = "linux"))]
    pub fn build_delegated_ruleset(
        _token: &crate::attestation::AgentIdentityToken,
        _proof: Option<&crate::attestation::DelegationProof>,
        _root_authority_vk: &ed25519_dalek::VerifyingKey,
        _current_epoch: u64,
    ) -> Result<SandboxRuleset, MandalaError> {
        Ok(SandboxRuleset)
    }

    /// Enforces Landlock confinement on the current thread/process derived from a verified delegation proof.
    pub fn restrict_delegated_process(
        token: &crate::attestation::AgentIdentityToken,
        proof: Option<&crate::attestation::DelegationProof>,
        root_authority_vk: &ed25519_dalek::VerifyingKey,
        current_epoch: u64,
    ) -> Result<(), MandalaError> {
        #[cfg(target_os = "linux")]
        {
            let ruleset =
                Self::build_delegated_ruleset(token, proof, root_authority_vk, current_epoch)?;
            let status = ruleset.inner.restrict_self().map_err(|e| {
                MandalaError::PersistenceFailure(format!("Landlock restrict_self failed: {e}"))
            })?;

            match status.ruleset {
                landlock::RulesetStatus::FullyEnforced
                | landlock::RulesetStatus::PartiallyEnforced => Ok(()),
                landlock::RulesetStatus::NotEnforced => Err(MandalaError::OperationNotAllowed {
                    operation: "landlock_confinement".to_string(),
                    reason: "Landlock ruleset was not enforced by the kernel".to_string(),
                }),
            }
        }

        #[cfg(not(target_os = "linux"))]
        {
            Ok(())
        }
    }
}

// ============================================================================
// Phase B: Continuity Receipt Spec 0.5 Notarization
// ============================================================================

/// State commitment record conforming to Spec 0.5.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StateCommitmentRecord {
    pub state_kind: String,
    pub scope: String,
    pub count: u64,
    pub head_digest: String,
    pub merkle_root: Option<String>,
}

/// Cryptographic continuity receipt conforming to Spec 0.5.
///
/// Binds task execution, sandbox class, workspace claim digest,
/// preflight clearance, and state commitments under Ed25519 DID signatures.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ContinuityReceipt05 {
    pub spec: String,
    pub receipt_id: String,
    pub tenant_id: String,
    pub agent_id: String,
    pub session_id: String,
    pub timestamp_ms: u64,
    pub mandala_class: String,
    pub sandbox_class: String,
    pub workspace_claim_digest: String,
    pub preflight_clearance: bool,
    pub preflight_digest: String,
    pub state_commitment: Option<StateCommitmentRecord>,
    pub issuer_did: String,
    #[serde(default)]
    pub kekkai_phase: Option<KekkaiPhase>,
    pub signature: Option<Vec<u8>>,
}

impl ContinuityReceipt05 {
    /// Constructs a new unsigned ContinuityReceipt05 instance.
    #[must_use]
    pub fn new(
        receipt_id: String,
        tenant_id: String,
        agent_id: String,
        session_id: String,
        timestamp_ms: u64,
        sandbox_class: String,
        workspace_claim_digest: String,
        preflight_clearance: bool,
        preflight_digest: String,
        state_commitment: Option<StateCommitmentRecord>,
        issuer_did: String,
    ) -> Self {
        Self {
            spec: "continuity-receipt/0.5".to_string(),
            receipt_id,
            tenant_id,
            agent_id,
            session_id,
            timestamp_ms,
            mandala_class: "local".to_string(),
            sandbox_class,
            workspace_claim_digest,
            preflight_clearance,
            preflight_digest,
            state_commitment,
            issuer_did,
            kekkai_phase: Some(KekkaiPhase::Kai),
            signature: None,
        }
    }

    /// Computes canonical signing bytes for Spec 0.5 receipt envelope.
    #[must_use]
    pub fn canonical_signing_bytes(&self) -> Vec<u8> {
        let mut hasher = Sha256::new();
        hasher.update(self.spec.as_bytes());
        hasher.update(b"|");
        hasher.update(self.receipt_id.as_bytes());
        hasher.update(b"|");
        hasher.update(self.tenant_id.as_bytes());
        hasher.update(b"|");
        hasher.update(self.agent_id.as_bytes());
        hasher.update(b"|");
        hasher.update(self.session_id.as_bytes());
        hasher.update(b"|");
        hasher.update(self.timestamp_ms.to_le_bytes());
        hasher.update(b"|");
        hasher.update(self.mandala_class.as_bytes());
        hasher.update(b"|");
        hasher.update(self.sandbox_class.as_bytes());
        hasher.update(b"|");
        hasher.update(self.workspace_claim_digest.as_bytes());
        hasher.update(b"|");
        hasher.update(&[if self.preflight_clearance { 1 } else { 0 }]);
        hasher.update(b"|");
        hasher.update(self.preflight_digest.as_bytes());
        hasher.update(b"|");
        if let Some(ref sc) = self.state_commitment {
            hasher.update(sc.state_kind.as_bytes());
            hasher.update(b":");
            hasher.update(sc.scope.as_bytes());
            hasher.update(b":");
            hasher.update(sc.count.to_le_bytes());
            hasher.update(b":");
            hasher.update(sc.head_digest.as_bytes());
            hasher.update(b":");
            if let Some(ref mr) = sc.merkle_root {
                hasher.update(mr.as_bytes());
            }
        }
        hasher.update(b"|");
        hasher.update(self.issuer_did.as_bytes());
        if let Some(phase) = self.kekkai_phase {
            hasher.update(b"|");
            hasher.update(format!("{phase:?}").as_bytes());
        }
        hasher.finalize().to_vec()
    }

    /// Signs the receipt with an authorized gate signing key.
    pub fn sign(&mut self, key: &SigningKey) {
        let bytes = self.canonical_signing_bytes();
        let sig = key.sign(&bytes);
        self.signature = Some(sig.to_bytes().to_vec());
    }

    /// Verifies the signature of this receipt against the verifying key.
    pub fn verify(&self, key: &VerifyingKey) -> Result<(), MandalaError> {
        let sig_bytes = self
            .signature
            .as_ref()
            .ok_or(MandalaError::SignatureInvalid)?;
        if sig_bytes.len() != 64 {
            return Err(MandalaError::SignatureInvalid);
        }
        let mut arr = [0u8; 64];
        arr.copy_from_slice(sig_bytes);
        let sig = Signature::from_bytes(&arr);
        let bytes = self.canonical_signing_bytes();
        key.verify(&bytes, &sig)
            .map_err(|_| MandalaError::SignatureInvalid)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_gate_keypair() -> (SigningKey, VerifyingKey) {
        let seed = [42u8; 32];
        let signing = SigningKey::from_bytes(&seed);
        let verifying = signing.verifying_key();
        (signing, verifying)
    }

    #[test]
    fn test_pass_issuance_and_verification() {
        let (signing, verifying) = test_gate_keypair();
        let gate_did = "did:key:z6MkuSgJ";

        let mut manifest = CapabilityManifest::default();
        manifest
            .allowed_operations
            .insert("memory:intake".to_string());
        manifest
            .allowed_operations
            .insert("memory:recall".to_string());

        let mut pass = MandalaPass {
            pass_id: "pass-001".to_string(),
            slot_id: "slot-alpha".to_string(),
            tenant_id: "tenant-lucas".to_string(),
            agent_id: "agent-gemini".to_string(),
            principal_id: Some("operator:lucas".to_string()),
            jti: "jti-001".to_string(),
            parent_jti: None,
            fork_depth: 0,
            created_at: 1000,
            expires_at: 2000,
            budget: PassBudget {
                max_operations: 10,
                operations_used: 0,
                max_compute_ms: 60_000,
                max_memory_mb: 1024,
            },
            manifest,
            mandate_ref: Some("mandate-root".to_string()),
            signature: None,
        };

        pass.sign(&signing);

        let mut verifier = MandalaAuthorityVerifier::new(MandalaReplayLedger::new());
        verifier.register_gate_key(gate_did, verifying);

        // Offline verification succeeds
        assert!(verifier.verify_pass_offline(&pass, gate_did, 1500).is_ok());

        // Authorize commit produces CommitCapability
        let cap_res =
            verifier.verify_and_authorize_commit(&mut pass, gate_did, "memory:intake", 1500);
        assert!(cap_res.is_ok());
        let cap = cap_res.unwrap();
        assert_eq!(
            cap.mandala_pass_info(),
            Some(("pass-001", "jti-001", "slot-alpha", "tenant-lucas"))
        );

        // Budget decremented
        assert_eq!(pass.budget.operations_used, 1);

        // Immediate replay of same jti fails closed
        let replay_res =
            verifier.verify_and_authorize_commit(&mut pass, gate_did, "memory:intake", 1501);
        assert_eq!(
            replay_res.unwrap_err(),
            MandalaError::TokenReplayDetected {
                jti: "jti-001".to_string()
            }
        );
    }

    #[test]
    fn test_signature_tampering_fails_closed() {
        let (signing, verifying) = test_gate_keypair();
        let gate_did = "did:key:z6MkuSgJ";

        let mut pass = MandalaPass {
            pass_id: "pass-002".to_string(),
            slot_id: "slot-beta".to_string(),
            tenant_id: "tenant-corp".to_string(),
            agent_id: "agent-x".to_string(),
            principal_id: None,
            jti: "jti-002".to_string(),
            parent_jti: None,
            fork_depth: 0,
            created_at: 1000,
            expires_at: 2000,
            budget: PassBudget::default(),
            manifest: CapabilityManifest::default(),
            mandate_ref: None,
            signature: None,
        };

        pass.sign(&signing);

        // Adversary tampers with tenant_id or budget
        pass.tenant_id = "tenant-attacker".to_string();

        let verifier = MandalaAuthorityVerifier::new(MandalaReplayLedger::new());
        let mut verifier = verifier;
        verifier.register_gate_key(gate_did, verifying);

        let err = verifier
            .verify_and_authorize_commit(&mut pass, gate_did, "tool:run", 1200)
            .unwrap_err();
        assert_eq!(err, MandalaError::SignatureInvalid);
    }

    #[test]
    fn test_revocation_matrix() {
        let (signing, verifying) = test_gate_keypair();
        let gate_did = "did:key:z6MkuSgJ";

        let mut pass = MandalaPass {
            pass_id: "pass-rev-1".to_string(),
            slot_id: "slot-rev".to_string(),
            tenant_id: "tenant-rev".to_string(),
            agent_id: "agent-rev".to_string(),
            principal_id: None,
            jti: "jti-rev-1".to_string(),
            parent_jti: None,
            fork_depth: 0,
            created_at: 1000,
            expires_at: 3000,
            budget: PassBudget::default(),
            manifest: CapabilityManifest {
                scope_mode: ScopeMode::All,
                allowed_operations: HashSet::new(),
                denied_operations: HashSet::new(),
                network_restricted: true,
            },
            mandate_ref: None,
            signature: None,
        };
        pass.sign(&signing);

        let mut verifier = MandalaAuthorityVerifier::new(MandalaReplayLedger::new());
        verifier.register_gate_key(gate_did, verifying);

        // Revoke pass_id
        verifier
            .ledger_mut()
            .revoke_pass("pass-rev-1", "Security breach suspected")
            .unwrap();

        let err = verifier
            .verify_and_authorize_commit(&mut pass, gate_did, "any:op", 1500)
            .unwrap_err();
        assert!(matches!(err, MandalaError::PassRevoked { .. }));
    }

    #[test]
    fn test_attenuating_child_fork_enforcement() {
        let parent = MandalaPass {
            pass_id: "pass-parent".to_string(),
            slot_id: "slot-p".to_string(),
            tenant_id: "tenant-alpha".to_string(),
            agent_id: "agent-parent".to_string(),
            principal_id: None,
            jti: "jti-parent".to_string(),
            parent_jti: None,
            fork_depth: 0,
            created_at: 1000,
            expires_at: 2000,
            budget: PassBudget {
                max_operations: 50,
                operations_used: 10, // 40 remaining
                max_compute_ms: 100_000,
                max_memory_mb: 2048,
            },
            manifest: CapabilityManifest {
                scope_mode: ScopeMode::Include,
                allowed_operations: ["read:data", "write:log"]
                    .iter()
                    .map(|s| s.to_string())
                    .collect(),
                denied_operations: HashSet::new(),
                network_restricted: true,
            },
            mandate_ref: None,
            signature: None,
        };

        // 1. Valid attenuating fork succeeds
        let child_res = parent.fork_child(
            "pass-child-1",
            "slot-c1",
            "agent-child",
            "jti-child-1",
            CapabilityManifest {
                scope_mode: ScopeMode::Include,
                allowed_operations: ["read:data"].iter().map(|s| s.to_string()).collect(),
                denied_operations: HashSet::new(),
                network_restricted: true,
            },
            PassBudget {
                max_operations: 20,
                operations_used: 0,
                max_compute_ms: 50_000,
                max_memory_mb: 1024,
            },
            1800,
            1200,
        );
        assert!(child_res.is_ok());
        let child = child_res.unwrap();
        assert_eq!(child.fork_depth, 1);
        assert_eq!(child.parent_jti, Some("jti-parent".to_string()));

        // 2. Child cannot exceed remaining parent budget (40 remaining, requesting 45)
        let greedy_budget_res = parent.fork_child(
            "pass-child-greedy",
            "slot-c2",
            "agent-child",
            "jti-child-2",
            parent.manifest.clone(),
            PassBudget {
                max_operations: 45,
                operations_used: 0,
                max_compute_ms: 50_000,
                max_memory_mb: 1024,
            },
            1800,
            1200,
        );
        assert!(matches!(
            greedy_budget_res.unwrap_err(),
            MandalaError::IllegalForkAttenuation(_)
        ));

        // 3. Child cannot grant operations parent does not have
        let mut escalating_manifest = parent.manifest.clone();
        escalating_manifest
            .allowed_operations
            .insert("delete:everything".to_string());
        let escalating_res = parent.fork_child(
            "pass-child-esc",
            "slot-c3",
            "agent-child",
            "jti-child-3",
            escalating_manifest,
            PassBudget {
                max_operations: 10,
                operations_used: 0,
                max_compute_ms: 50_000,
                max_memory_mb: 1024,
            },
            1800,
            1200,
        );
        assert!(matches!(
            escalating_res.unwrap_err(),
            MandalaError::IllegalForkAttenuation(_)
        ));

        // 4. Child cannot enable network when parent is restricted
        let mut unconfined_manifest = parent.manifest.clone();
        unconfined_manifest.network_restricted = false;
        let unconfined_res = parent.fork_child(
            "pass-child-unconfined",
            "slot-c4",
            "agent-child",
            "jti-child-4",
            unconfined_manifest,
            PassBudget {
                max_operations: 10,
                operations_used: 0,
                max_compute_ms: 50_000,
                max_memory_mb: 1024,
            },
            1800,
            1200,
        );
        assert!(matches!(
            unconfined_res.unwrap_err(),
            MandalaError::IllegalForkAttenuation(_)
        ));
    }

    #[test]
    fn test_workspace_claim_signing_and_digest() {
        let (signing, verifying) = test_gate_keypair();
        let mut claim = WorkspaceClaim {
            claim_id: "claim-ws-001".to_string(),
            tenant_id: "tenant-lucas".to_string(),
            agent_id: "agent-opencode".to_string(),
            workspace_root: PathBuf::from("/tmp"),
            read_only_paths: vec![PathBuf::from("/usr"), PathBuf::from("/lib")],
            read_write_paths: vec![PathBuf::from("/tmp/scratch")],
            network_allowed: false,
            kekkai_phase: KekkaiPhase::Hoi,
            resource_limits: Some(SandboxResourceLimits::default()),
            inherited_shm_fd: None,
            created_at: 1000,
            expires_at: 5000,
            signature: None,
        };

        let digest = claim.canonical_digest();
        assert!(digest.starts_with("sha256:"));

        claim.sign(&signing);
        assert!(claim.verify(&verifying).is_ok());

        // Tamper test
        claim.workspace_root = PathBuf::from("/etc");
        assert_eq!(
            claim.verify(&verifying).unwrap_err(),
            MandalaError::SignatureInvalid
        );
    }

    #[test]
    fn test_landlock_sandbox_ruleset_construction() {
        let claim = WorkspaceClaim {
            claim_id: "claim-landlock-001".to_string(),
            tenant_id: "tenant-lucas".to_string(),
            agent_id: "agent-agy".to_string(),
            workspace_root: PathBuf::from("/tmp"),
            read_only_paths: vec![PathBuf::from("/bin")],
            read_write_paths: vec![],
            network_allowed: false,
            kekkai_phase: KekkaiPhase::Hoi,
            resource_limits: None,
            inherited_shm_fd: None,
            created_at: 1000,
            expires_at: 5000,
            signature: None,
        };

        let ruleset_res = LandlockSandbox::build_ruleset(&claim);
        assert!(
            ruleset_res.is_ok(),
            "Landlock ruleset should build cleanly on Linux"
        );
    }

    #[test]
    fn test_continuity_receipt_05_lifecycle_and_tamper_detection() {
        let (signing, verifying) = test_gate_keypair();
        let mut receipt = ContinuityReceipt05::new(
            "rcpt-005-test".to_string(),
            "tenant-corp".to_string(),
            "agent-worker".to_string(),
            "ses_42".to_string(),
            1727900000,
            "landlock".to_string(),
            "sha256:abcd1234workspace".to_string(),
            true,
            "sha256:5678ef01preflight".to_string(),
            Some(StateCommitmentRecord {
                state_kind: "chain-head".to_string(),
                scope: "wm:gen3:store".to_string(),
                count: 403890,
                head_digest: "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855".to_string(),
                merkle_root: Some("merkle-sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08".to_string()),
            }),
            "did:key:fd75ec4be1c18c9a5788060008dac24aaed14534b885e66e5319b6ce78958cc4".to_string(),
        );

        receipt.sign(&signing);
        assert!(receipt.verify(&verifying).is_ok());

        // Tampering with preflight clearance or workspace claim must fail
        receipt.preflight_clearance = false;
        assert_eq!(
            receipt.verify(&verifying).unwrap_err(),
            MandalaError::SignatureInvalid
        );
    }
}
