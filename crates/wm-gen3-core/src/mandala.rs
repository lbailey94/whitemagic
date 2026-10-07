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
    /// Sandbox confinement was only partially enforced by the kernel (NOT full confinement).
    PartialEnforcement { details: String },
    /// Sandbox confinement was not enforced at all by the kernel.
    ConfinementNotEnforced { details: String },
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
            Self::PartialEnforcement { details } => {
                write!(
                    f,
                    "Mandala Sandbox Only Partially Enforced (Not Full Confinement): {details}"
                )
            }
            Self::ConfinementNotEnforced { details } => {
                write!(f, "Mandala Sandbox Not Enforced: {details}")
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

    /// Boolean mirror of [`Self::is_allowed`] used for attenuation proofs.
    ///
    /// `Include` and `Exclude` both permit exactly `allowed_operations - denied_operations`
    /// in this implementation; `All` permits everything not explicitly denied.
    fn permits(&self, operation: &str) -> bool {
        if self.denied_operations.contains(operation) {
            return false;
        }
        match self.scope_mode {
            ScopeMode::All => true,
            ScopeMode::Include | ScopeMode::Exclude => self.allowed_operations.contains(operation),
        }
    }

    /// Verifies that a child manifest monotonically attenuates (never escalates) this parent.
    ///
    /// Invariant: `Permitted(child) ⊆ Permitted(parent)` for every scope mode, where the
    /// permitted set of an `Include`/`Exclude` manifest is `allowed_operations` minus
    /// `denied_operations`, and `All` permits everything not explicitly denied.
    pub fn attenuate(&self, child: &CapabilityManifest) -> Result<(), MandalaError> {
        // Child must be network restricted if parent is network restricted
        if self.network_restricted && !child.network_restricted {
            return Err(MandalaError::IllegalForkAttenuation(
                "Child cannot enable network egress when parent is network restricted".to_string(),
            ));
        }

        // Child cannot widen the scope resolution mode beyond the parent's scope
        if child.scope_mode == ScopeMode::All && self.scope_mode != ScopeMode::All {
            return Err(MandalaError::IllegalForkAttenuation(format!(
                "Child cannot escalate scope mode to All from parent {:?} scope",
                self.scope_mode
            )));
        }

        if self.scope_mode == ScopeMode::All && child.scope_mode == ScopeMode::All {
            // Both permit the virtual universal set, so the child may only add denials.
            for denied in &self.denied_operations {
                if !child.denied_operations.contains(denied) {
                    return Err(MandalaError::IllegalForkAttenuation(format!(
                        "Child All-scope manifest drops parent denial of '{denied}'"
                    )));
                }
            }
        } else {
            // Prove each operation the child effectively permits is also permitted by the
            // parent. This covers Exclude parents, which the previous Include-only subset
            // check silently allowed to escalate.
            for op in &child.allowed_operations {
                if child.permits(op) && !self.permits(op) {
                    return Err(MandalaError::IllegalForkAttenuation(format!(
                        "Child permits operation '{op}' which parent {:?} does not permit",
                        self.scope_mode
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

/// Mixes a length-prefixed field into the canonical hash stream.
///
/// Length framing makes the encoding injective: values containing delimiter-like
/// bytes cannot be re-split across field boundaries.
fn hash_field(hasher: &mut Sha256, bytes: &[u8]) {
    hasher.update((bytes.len() as u64).to_be_bytes());
    hasher.update(bytes);
}

/// Mixes an optional string with an explicit presence marker.
fn hash_opt_field(hasher: &mut Sha256, value: Option<&str>) {
    match value {
        Some(v) => {
            hasher.update([1u8]);
            hash_field(hasher, v.as_bytes());
        }
        None => hasher.update([0u8]),
    }
}

/// Mixes a filesystem path using its native byte representation on Unix.
fn hash_path_field(hasher: &mut Sha256, path: &Path) {
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStrExt;
        hash_field(hasher, path.as_os_str().as_bytes());
    }
    #[cfg(not(unix))]
    {
        hash_field(hasher, path.to_string_lossy().as_bytes());
    }
}

/// Canonical, stable label for a scope mode (never `Debug`-formatted).
fn scope_mode_label(mode: ScopeMode) -> &'static str {
    match mode {
        ScopeMode::All => "all",
        ScopeMode::Include => "include",
        ScopeMode::Exclude => "exclude",
    }
}

impl MandalaPass {
    /// Generates canonical bytes for signing and verification.
    ///
    /// Every authority-bearing field is covered, including `manifest.scope_mode`,
    /// the network policy, and both capability lists in sorted order. Fields use
    /// length-prefixed framing so no two distinct manifests can hash to the same
    /// byte stream. `budget.operations_used` is intentionally excluded: it is
    /// mutable post-signature consumption state, and re-signing is required by
    /// `advance_continuation`.
    #[must_use]
    pub fn canonical_signing_bytes(&self) -> Vec<u8> {
        // Sort operations for deterministic serialization
        let mut sorted_allowed: Vec<&String> = self.manifest.allowed_operations.iter().collect();
        sorted_allowed.sort();
        let mut sorted_denied: Vec<&String> = self.manifest.denied_operations.iter().collect();
        sorted_denied.sort();

        let mut hasher = Sha256::new();
        hasher.update(b"MANDALA_PASS_V2\n");
        hash_field(&mut hasher, self.pass_id.as_bytes());
        hash_field(&mut hasher, self.slot_id.as_bytes());
        hash_field(&mut hasher, self.tenant_id.as_bytes());
        hash_field(&mut hasher, self.agent_id.as_bytes());
        hash_opt_field(&mut hasher, self.principal_id.as_deref());
        hash_field(&mut hasher, self.jti.as_bytes());
        hash_opt_field(&mut hasher, self.parent_jti.as_deref());
        hasher.update(self.fork_depth.to_be_bytes());
        hasher.update(self.created_at.to_be_bytes());
        hasher.update(self.expires_at.to_be_bytes());
        // Immutable budget ceilings
        hasher.update(self.budget.max_operations.to_be_bytes());
        hasher.update(self.budget.max_compute_ms.to_be_bytes());
        hasher.update(self.budget.max_memory_mb.to_be_bytes());
        // Manifest: scope mode and network policy carry semantic authority
        hash_field(
            &mut hasher,
            scope_mode_label(self.manifest.scope_mode).as_bytes(),
        );
        hasher.update([u8::from(self.manifest.network_restricted)]);
        hasher.update((sorted_allowed.len() as u64).to_be_bytes());
        for op in &sorted_allowed {
            hash_field(&mut hasher, op.as_bytes());
        }
        hasher.update((sorted_denied.len() as u64).to_be_bytes());
        for op in &sorted_denied {
            hash_field(&mut hasher, op.as_bytes());
        }
        hash_opt_field(&mut hasher, self.mandate_ref.as_deref());

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
    // Fork constructor mirrors the sealed parent pass fields one-to-one.
    #[allow(clippy::too_many_arguments)]
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
        getrandom::fill(&mut bytes).map_err(|e| std::io::Error::other(e.to_string()))?;
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
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum KekkaiPhase {
    /// Hōi: Targeting coordinates and pinning ephemeral boundary claim.
    #[default]
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
        self.inherited_shm_fd
            .map(|fd| wm_gen3_shm::ShmSubstrate::from_raw_fd(fd, false))
    }
    /// Computes the canonical SHA-256 digest of this workspace claim.
    ///
    /// Covers every capability-bearing field: identity, workspace root, sorted
    /// read-only and read-write paths, network policy, kekkai phase, resource
    /// limits, and the inherited shm fd. Length-prefixed framing prevents
    /// delimiter injection between fields.
    #[must_use]
    pub fn canonical_digest(&self) -> String {
        let mut sorted_ro: Vec<&PathBuf> = self.read_only_paths.iter().collect();
        sorted_ro.sort();
        let mut sorted_rw: Vec<&PathBuf> = self.read_write_paths.iter().collect();
        sorted_rw.sort();

        let mut hasher = Sha256::new();
        hasher.update(b"WORKSPACE_CLAIM_V2\n");
        hash_field(&mut hasher, self.claim_id.as_bytes());
        hash_field(&mut hasher, self.tenant_id.as_bytes());
        hash_field(&mut hasher, self.agent_id.as_bytes());
        hash_path_field(&mut hasher, &self.workspace_root);
        hasher.update((sorted_ro.len() as u64).to_be_bytes());
        for p in &sorted_ro {
            hash_path_field(&mut hasher, p);
        }
        hasher.update((sorted_rw.len() as u64).to_be_bytes());
        for p in &sorted_rw {
            hash_path_field(&mut hasher, p);
        }
        hasher.update([u8::from(self.network_allowed)]);
        hash_field(&mut hasher, self.kekkai_phase.as_str().as_bytes());
        match &self.resource_limits {
            Some(lim) => {
                hasher.update([1u8]);
                hasher.update(lim.max_memory_mb.to_be_bytes());
                hasher.update(lim.max_cpu_seconds.to_be_bytes());
                hasher.update(lim.max_open_files.to_be_bytes());
            }
            None => hasher.update([0u8]),
        }
        match self.inherited_shm_fd {
            Some(fd) => {
                hasher.update([1u8]);
                hasher.update(fd.to_be_bytes());
            }
            None => hasher.update([0u8]),
        }
        hasher.update(self.created_at.to_be_bytes());
        hasher.update(self.expires_at.to_be_bytes());
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

/// Kernel enforcement outcome for a sandbox restriction call.
///
/// Callers must never treat [`SandboxEnforcement::PartiallyEnforced`] as full
/// confinement: some requested restrictions were rejected or ignored by the kernel.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SandboxEnforcement {
    /// The kernel enforced every requested restriction.
    FullyEnforced,
    /// The kernel enforced only a subset of the requested restrictions.
    PartiallyEnforced,
    /// The kernel did not enforce the ruleset at all.
    NotEnforced,
}

impl SandboxEnforcement {
    /// Returns true only when every requested restriction is kernel-enforced.
    #[must_use]
    pub fn is_full(self) -> bool {
        matches!(self, Self::FullyEnforced)
    }

    /// Stable machine-readable label for reports and receipts.
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::FullyEnforced => "fully_enforced",
            Self::PartiallyEnforced => "partially_enforced",
            Self::NotEnforced => "not_enforced",
        }
    }
}

/// Explicit sandbox enforcement report.
///
/// Carries the enforcement classification out of the `restrict_*` calls so
/// partial confinement is visible to callers, receipts, and operators.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SandboxEnforcementReport {
    /// Digest of the `WorkspaceClaim` materialized, when one applies.
    pub workspace_claim_digest: Option<String>,
    /// Enforcement classification for this restriction call.
    pub status: SandboxEnforcement,
    /// Enforcement backend (e.g. `landlock`, `advisory-rlimit`).
    pub backend: String,
    /// Human-readable detail when enforcement is not full.
    pub details: Option<String>,
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

    /// Maps a Landlock kernel result into the explicit enforcement classification.
    #[cfg(target_os = "linux")]
    fn classify_enforcement(status: landlock::RulesetStatus) -> SandboxEnforcement {
        match status {
            landlock::RulesetStatus::FullyEnforced => SandboxEnforcement::FullyEnforced,
            landlock::RulesetStatus::PartiallyEnforced => SandboxEnforcement::PartiallyEnforced,
            landlock::RulesetStatus::NotEnforced => SandboxEnforcement::NotEnforced,
        }
    }

    /// Fails closed unless the kernel fully enforced the requested confinement.
    fn require_full_enforcement(status: SandboxEnforcement) -> Result<(), MandalaError> {
        match status {
            SandboxEnforcement::FullyEnforced => Ok(()),
            SandboxEnforcement::PartiallyEnforced => Err(MandalaError::PartialEnforcement {
                details:
                    "Landlock enforced only a subset of the requested restrictions; confinement \
                     is not complete"
                        .to_string(),
            }),
            SandboxEnforcement::NotEnforced => Err(MandalaError::ConfinementNotEnforced {
                details: "Landlock ruleset was not enforced by the kernel".to_string(),
            }),
        }
    }

    /// Enforces Landlock confinement and unprivileged resource limits on the current thread/process.
    ///
    /// Fails closed unless the kernel reports full enforcement. Use
    /// [`Self::restrict_current_process_reported`] to distinguish full, partial,
    /// and absent enforcement.
    pub fn restrict_current_process(claim: &WorkspaceClaim) -> Result<(), MandalaError> {
        let report = Self::restrict_current_process_reported(claim)?;
        Self::require_full_enforcement(report.status)
    }

    /// Enforces confinement and returns an explicit enforcement report.
    ///
    /// Partial confinement (for example an older Landlock ABI that enforces only
    /// filesystem rules) is reported as [`SandboxEnforcement::PartiallyEnforced`]
    /// and is never silently upgraded to full enforcement.
    pub fn restrict_current_process_reported(
        claim: &WorkspaceClaim,
    ) -> Result<SandboxEnforcementReport, MandalaError> {
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
            let enforcement = Self::classify_enforcement(status.ruleset);
            let details = match enforcement {
                SandboxEnforcement::FullyEnforced => None,
                SandboxEnforcement::PartiallyEnforced => Some(
                    "Landlock kernel enforced only a subset of the requested restrictions; \
                     confinement is not complete"
                        .to_string(),
                ),
                SandboxEnforcement::NotEnforced => {
                    Some("Landlock ruleset was not enforced by the kernel".to_string())
                }
            };
            Ok(SandboxEnforcementReport {
                workspace_claim_digest: Some(claim.canonical_digest()),
                status: enforcement,
                backend: "landlock".to_string(),
                details,
            })
        }

        // 3. Non-Linux: no kernel LSM, only advisory process limits can apply
        #[cfg(not(target_os = "linux"))]
        {
            let enforcement = if claim.resource_limits.is_some() {
                SandboxEnforcement::PartiallyEnforced
            } else {
                SandboxEnforcement::NotEnforced
            };
            Ok(SandboxEnforcementReport {
                workspace_claim_digest: Some(claim.canonical_digest()),
                status: enforcement,
                backend: "advisory-rlimit".to_string(),
                details: Some(
                    "No kernel LSM on this platform; filesystem/network confinement is advisory \
                     only"
                        .to_string(),
                ),
            })
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
    ///
    /// Fails closed unless the kernel reports full enforcement. Use
    /// [`Self::restrict_delegated_process_reported`] to distinguish full, partial,
    /// and absent enforcement.
    pub fn restrict_delegated_process(
        token: &crate::attestation::AgentIdentityToken,
        proof: Option<&crate::attestation::DelegationProof>,
        root_authority_vk: &ed25519_dalek::VerifyingKey,
        current_epoch: u64,
    ) -> Result<(), MandalaError> {
        let report = Self::restrict_delegated_process_reported(
            token,
            proof,
            root_authority_vk,
            current_epoch,
        )?;
        Self::require_full_enforcement(report.status)
    }

    /// Enforces delegated confinement and returns an explicit enforcement report.
    ///
    /// Partial confinement is reported as [`SandboxEnforcement::PartiallyEnforced`]
    /// and is never silently upgraded to full enforcement.
    pub fn restrict_delegated_process_reported(
        token: &crate::attestation::AgentIdentityToken,
        proof: Option<&crate::attestation::DelegationProof>,
        root_authority_vk: &ed25519_dalek::VerifyingKey,
        current_epoch: u64,
    ) -> Result<SandboxEnforcementReport, MandalaError> {
        #[cfg(target_os = "linux")]
        {
            let ruleset =
                Self::build_delegated_ruleset(token, proof, root_authority_vk, current_epoch)?;
            let status = ruleset.inner.restrict_self().map_err(|e| {
                MandalaError::PersistenceFailure(format!("Landlock restrict_self failed: {e}"))
            })?;
            let enforcement = Self::classify_enforcement(status.ruleset);
            let details = match enforcement {
                SandboxEnforcement::FullyEnforced => None,
                SandboxEnforcement::PartiallyEnforced => Some(
                    "Landlock kernel enforced only a subset of the delegated restrictions; \
                     confinement is not complete"
                        .to_string(),
                ),
                SandboxEnforcement::NotEnforced => {
                    Some("Landlock ruleset was not enforced by the kernel".to_string())
                }
            };
            Ok(SandboxEnforcementReport {
                workspace_claim_digest: None,
                status: enforcement,
                backend: "landlock-delegated".to_string(),
                details,
            })
        }

        #[cfg(not(target_os = "linux"))]
        {
            Ok(SandboxEnforcementReport {
                workspace_claim_digest: None,
                status: SandboxEnforcement::NotEnforced,
                backend: "none".to_string(),
                details: Some(
                    "No kernel LSM on this platform; delegated confinement is unavailable"
                        .to_string(),
                ),
            })
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
    // Receipt constructor mirrors the signed envelope fields one-to-one.
    #[allow(clippy::too_many_arguments)]
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
        hasher.update([if self.preflight_clearance { 1 } else { 0 }]);
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

    #[test]
    fn test_scope_mode_is_signed_and_flip_fails_closed() {
        let (signing, verifying) = test_gate_keypair();
        let gate_did = "did:key:scope-mode";

        let mut manifest = CapabilityManifest::default();
        manifest
            .allowed_operations
            .insert("memory:intake".to_string());

        let mut pass = MandalaPass {
            pass_id: "pass-scope-001".to_string(),
            slot_id: "slot-scope".to_string(),
            tenant_id: "tenant-scope".to_string(),
            agent_id: "agent-scope".to_string(),
            principal_id: None,
            jti: "jti-scope-001".to_string(),
            parent_jti: None,
            fork_depth: 0,
            created_at: 1000,
            expires_at: 2000,
            budget: PassBudget::default(),
            manifest,
            mandate_ref: None,
            signature: None,
        };
        pass.sign(&signing);

        let mut verifier = MandalaAuthorityVerifier::new(MandalaReplayLedger::new());
        verifier.register_gate_key(gate_did, verifying);
        assert!(verifier.verify_pass_offline(&pass, gate_did, 1500).is_ok());

        // Attacker flips scope_mode Include -> All after signing
        let mut tampered = pass.clone();
        tampered.manifest.scope_mode = ScopeMode::All;
        assert_eq!(
            tampered.verify_signature(&verifying).unwrap_err(),
            MandalaError::SignatureInvalid
        );
        assert_eq!(
            verifier
                .verify_pass_offline(&tampered, gate_did, 1500)
                .unwrap_err(),
            MandalaError::SignatureInvalid
        );

        // Authorization for an operation only permitted by the flipped All scope fails closed
        let mut escalated = pass.clone();
        escalated.manifest.scope_mode = ScopeMode::All;
        assert_eq!(
            verifier
                .verify_and_authorize_commit(&mut escalated, gate_did, "delete:everything", 1500)
                .unwrap_err(),
            MandalaError::SignatureInvalid
        );
    }

    #[test]
    fn test_pass_capability_ordering_is_canonical() {
        fn pass_with(allowed: &[&str]) -> MandalaPass {
            let mut manifest = CapabilityManifest::default();
            for op in allowed {
                manifest.allowed_operations.insert((*op).to_string());
            }
            MandalaPass {
                pass_id: "pass-order".to_string(),
                slot_id: "slot-order".to_string(),
                tenant_id: "tenant-order".to_string(),
                agent_id: "agent-order".to_string(),
                principal_id: None,
                jti: "jti-order".to_string(),
                parent_jti: None,
                fork_depth: 0,
                created_at: 1000,
                expires_at: 2000,
                budget: PassBudget::default(),
                manifest,
                mandate_ref: None,
                signature: None,
            }
        }

        let a = pass_with(&["memory:recall", "memory:intake", "tool:run"]);
        let b = pass_with(&["tool:run", "memory:recall", "memory:intake"]);
        assert_eq!(a.canonical_signing_bytes(), b.canonical_signing_bytes());
    }

    #[test]
    fn test_fork_scope_mode_escalation_rejected() {
        let parent = MandalaPass {
            pass_id: "pass-parent-scope".to_string(),
            slot_id: "slot-ps".to_string(),
            tenant_id: "tenant-scope".to_string(),
            agent_id: "agent-parent".to_string(),
            principal_id: None,
            jti: "jti-parent-scope".to_string(),
            parent_jti: None,
            fork_depth: 0,
            created_at: 1000,
            expires_at: 2000,
            budget: PassBudget::default(),
            manifest: CapabilityManifest {
                scope_mode: ScopeMode::Include,
                allowed_operations: ["read:data"].iter().map(|s| s.to_string()).collect(),
                denied_operations: HashSet::new(),
                network_restricted: true,
            },
            mandate_ref: None,
            signature: None,
        };

        let all_scope = CapabilityManifest {
            scope_mode: ScopeMode::All,
            allowed_operations: HashSet::new(),
            denied_operations: HashSet::new(),
            network_restricted: true,
        };
        let child_budget = PassBudget {
            max_operations: 5,
            operations_used: 0,
            max_compute_ms: 1_000,
            max_memory_mb: 128,
        };

        let escalated = parent.fork_child(
            "pass-child-all",
            "slot-ca",
            "agent-child",
            "jti-ca",
            all_scope.clone(),
            child_budget,
            1800,
            1200,
        );
        assert!(matches!(
            escalated.unwrap_err(),
            MandalaError::IllegalForkAttenuation(_)
        ));

        let mut parent_all = parent;
        parent_all.manifest = all_scope.clone();
        let allowed = parent_all.fork_child(
            "pass-child-all-2",
            "slot-ca2",
            "agent-child",
            "jti-ca2",
            all_scope,
            child_budget,
            1800,
            1200,
        );
        assert!(allowed.is_ok());
    }

    #[test]
    fn test_workspace_claim_all_scope_fields_signed() {
        let (signing, verifying) = test_gate_keypair();
        let base = WorkspaceClaim {
            claim_id: "claim-tamper-001".to_string(),
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
        let mut signed = base.clone();
        signed.sign(&signing);
        assert!(signed.verify(&verifying).is_ok());

        // Path ordering is canonicalized: the same set in any order verifies
        let mut reordered = signed.clone();
        reordered.read_only_paths.reverse();
        assert!(reordered.verify(&verifying).is_ok());

        let mut ro = signed.clone();
        ro.read_only_paths.push(PathBuf::from("/etc"));
        assert_eq!(
            ro.verify(&verifying).unwrap_err(),
            MandalaError::SignatureInvalid
        );

        let mut rw = signed.clone();
        rw.read_write_paths = vec![PathBuf::from("/tmp/elsewhere")];
        assert_eq!(
            rw.verify(&verifying).unwrap_err(),
            MandalaError::SignatureInvalid
        );

        let mut net = signed.clone();
        net.network_allowed = true;
        assert_eq!(
            net.verify(&verifying).unwrap_err(),
            MandalaError::SignatureInvalid
        );

        let mut shm = signed.clone();
        shm.inherited_shm_fd = Some(7);
        assert_eq!(
            shm.verify(&verifying).unwrap_err(),
            MandalaError::SignatureInvalid
        );

        let mut limits = signed.clone();
        limits.resource_limits = Some(SandboxResourceLimits {
            max_memory_mb: 64,
            ..SandboxResourceLimits::default()
        });
        assert_eq!(
            limits.verify(&verifying).unwrap_err(),
            MandalaError::SignatureInvalid
        );
    }

    #[test]
    fn test_partial_enforcement_is_not_full() {
        assert!(SandboxEnforcement::FullyEnforced.is_full());
        assert!(!SandboxEnforcement::PartiallyEnforced.is_full());
        assert!(!SandboxEnforcement::NotEnforced.is_full());

        assert!(
            LandlockSandbox::require_full_enforcement(SandboxEnforcement::FullyEnforced).is_ok()
        );
        assert!(matches!(
            LandlockSandbox::require_full_enforcement(SandboxEnforcement::PartiallyEnforced)
                .unwrap_err(),
            MandalaError::PartialEnforcement { .. }
        ));
        assert!(matches!(
            LandlockSandbox::require_full_enforcement(SandboxEnforcement::NotEnforced).unwrap_err(),
            MandalaError::ConfinementNotEnforced { .. }
        ));

        #[cfg(target_os = "linux")]
        {
            assert_eq!(
                LandlockSandbox::classify_enforcement(landlock::RulesetStatus::FullyEnforced),
                SandboxEnforcement::FullyEnforced
            );
            assert_eq!(
                LandlockSandbox::classify_enforcement(landlock::RulesetStatus::PartiallyEnforced),
                SandboxEnforcement::PartiallyEnforced
            );
            assert_eq!(
                LandlockSandbox::classify_enforcement(landlock::RulesetStatus::NotEnforced),
                SandboxEnforcement::NotEnforced
            );
        }
    }

    fn mk_manifest(mode: ScopeMode, allowed: &[&str], denied: &[&str]) -> CapabilityManifest {
        CapabilityManifest {
            scope_mode: mode,
            allowed_operations: allowed.iter().map(|s| s.to_string()).collect(),
            denied_operations: denied.iter().map(|s| s.to_string()).collect(),
            network_restricted: true,
        }
    }

    #[test]
    fn test_exclude_parent_rejects_include_escalation() {
        let parent = mk_manifest(ScopeMode::Exclude, &["read:data"], &[]);
        let escalating = mk_manifest(ScopeMode::Include, &["write:data"], &[]);
        assert!(matches!(
            parent.attenuate(&escalating).unwrap_err(),
            MandalaError::IllegalForkAttenuation(_)
        ));
        assert!(!parent.permits("write:data"));
        assert!(escalating.permits("write:data"));

        // End-to-end through fork_child: the child may not gain write the parent lacks.
        let parent_pass = MandalaPass {
            pass_id: "pass-exclude-parent".to_string(),
            slot_id: "slot-exp".to_string(),
            tenant_id: "tenant-exclude".to_string(),
            agent_id: "agent-parent".to_string(),
            principal_id: None,
            jti: "jti-exclude-parent".to_string(),
            parent_jti: None,
            fork_depth: 0,
            created_at: 1000,
            expires_at: 2000,
            budget: PassBudget::default(),
            manifest: parent.clone(),
            mandate_ref: None,
            signature: None,
        };
        let child_budget = PassBudget {
            max_operations: 5,
            operations_used: 0,
            max_compute_ms: 1_000,
            max_memory_mb: 128,
        };
        assert!(matches!(
            parent_pass
                .fork_child(
                    "pass-exclude-child",
                    "slot-ec",
                    "agent-child",
                    "jti-ec",
                    escalating,
                    child_budget,
                    1800,
                    1200,
                )
                .unwrap_err(),
            MandalaError::IllegalForkAttenuation(_)
        ));
        assert!(
            parent_pass
                .fork_child(
                    "pass-exclude-child-2",
                    "slot-ec2",
                    "agent-child",
                    "jti-ec2",
                    mk_manifest(ScopeMode::Include, &["read:data"], &[]),
                    child_budget,
                    1800,
                    1200,
                )
                .is_ok()
        );
    }

    #[test]
    fn test_exclude_child_widening_permitted_set_rejected() {
        // Parent permitted set is {read:data} (write is explicitly denied).
        let parent = mk_manifest(
            ScopeMode::Exclude,
            &["read:data", "write:data"],
            &["write:data"],
        );
        // Child excludes less (drops the denial), so its permitted set is a superset.
        let wider = mk_manifest(ScopeMode::Exclude, &["read:data", "write:data"], &[]);
        assert!(matches!(
            parent.attenuate(&wider).unwrap_err(),
            MandalaError::IllegalForkAttenuation(_)
        ));
        assert!(wider.permits("write:data"));
        assert!(!parent.permits("write:data"));

        // A child that only narrows the permitted set attenuates cleanly.
        let narrower = mk_manifest(ScopeMode::Exclude, &["read:data"], &[]);
        assert!(parent.attenuate(&narrower).is_ok());
    }

    #[test]
    fn test_all_parent_attenuation_and_denial_preservation() {
        let parent_all = mk_manifest(ScopeMode::All, &[], &["secret:exfil"]);

        // Parent All -> child Include is fine when the child adds no denied permission.
        assert!(
            parent_all
                .attenuate(&mk_manifest(ScopeMode::Include, &["read:data"], &[]))
                .is_ok()
        );

        // Child cannot permit an operation the parent explicitly denies.
        assert!(matches!(
            parent_all
                .attenuate(&mk_manifest(ScopeMode::Include, &["secret:exfil"], &[]))
                .unwrap_err(),
            MandalaError::IllegalForkAttenuation(_)
        ));

        // Child All-scope may not drop the parent's denial.
        assert!(matches!(
            parent_all
                .attenuate(&mk_manifest(ScopeMode::All, &[], &[]))
                .unwrap_err(),
            MandalaError::IllegalForkAttenuation(_)
        ));
        assert!(
            parent_all
                .attenuate(&mk_manifest(ScopeMode::All, &[], &["secret:exfil"]))
                .is_ok()
        );
    }

    #[test]
    fn test_multi_level_attenuation_chains() {
        // Include chain: each level narrows the permitted set.
        let root = mk_manifest(ScopeMode::Include, &["a", "b", "c"], &[]);
        let mid = mk_manifest(ScopeMode::Include, &["a", "b"], &[]);
        let leaf = mk_manifest(ScopeMode::Include, &["a"], &[]);
        assert!(root.attenuate(&mid).is_ok());
        assert!(mid.attenuate(&leaf).is_ok());

        // Escalation at any link in the chain is rejected.
        let escalated = mk_manifest(ScopeMode::Include, &["a", "d"], &[]);
        assert!(matches!(
            mid.attenuate(&escalated).unwrap_err(),
            MandalaError::IllegalForkAttenuation(_)
        ));

        // Mixed chain: Exclude root -> narrower Include descendants.
        let exclude_root = mk_manifest(ScopeMode::Exclude, &["a", "b"], &[]);
        assert!(
            exclude_root
                .attenuate(&mk_manifest(ScopeMode::Include, &["a"], &[]))
                .is_ok()
        );
        assert!(matches!(
            exclude_root
                .attenuate(&mk_manifest(ScopeMode::Include, &["c"], &[]))
                .unwrap_err(),
            MandalaError::IllegalForkAttenuation(_)
        ));
    }
}
