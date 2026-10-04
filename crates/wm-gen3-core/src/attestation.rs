//! Cryptographic Agent Identity Attestation, Capability Delegation, and Audit Chains (Level 4: Phenotypes).
//!
//! # Sovereign Agent Identity Fabric
//!
//! In distributed agentic systems, authorization cannot rely on bearer tokens or ambient trust.
//! This module formalizes:
//! 1. **`AgentIdentityToken`**: Cryptographically bound Ed25519 identity token signed by the
//!    sovereign authority, declaring typed capabilities, anti-replay nonces, and epoch expiration.
//! 2. **`DelegationProof`**: Strict hierarchical capability delegation from primary agents to subagents.
//!    Enforces subset capability narrowing and maximum delegation recursion bounds ($depth \le 3$).
//! 3. **`AuditAttestation`**: Tamper-evident hash-chained audit proofs linking actions to agent identities
//!    with Ed25519 non-repudiation signatures.

#![forbid(unsafe_code)]

use std::collections::BTreeSet;
use std::fmt;

use ed25519_dalek::{Signer, SigningKey, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Errors encountered during agent identity attestation and capability verification.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AttestationError {
    ExpiredToken { expires_at: u64, current_epoch: u64 },
    InvalidSignature(String),
    MissingCapability(String),
    AuthorityMismatch,
    DelegationDepthExceeded { max: u8, requested: u8 },
    CapabilityEscalation { unauthorized: Vec<String> },
    InvalidPublicKey(String),
    MalformedHex(String),
    HashChainBroken { expected: String, actual: String },
}

impl fmt::Display for AttestationError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::ExpiredToken {
                expires_at,
                current_epoch,
            } => {
                write!(
                    f,
                    "Identity token expired at epoch {expires_at}, current epoch is {current_epoch}"
                )
            }
            Self::InvalidSignature(msg) => write!(f, "Cryptographic signature invalid: {msg}"),
            Self::MissingCapability(cap) => write!(f, "Agent lacks required capability: {cap}"),
            Self::AuthorityMismatch => write!(
                f,
                "Issuing authority key does not match root sovereign trust"
            ),
            Self::DelegationDepthExceeded { max, requested } => {
                write!(f, "Delegation depth {requested} exceeds limit {max}")
            }
            Self::CapabilityEscalation { unauthorized } => {
                write!(
                    f,
                    "Capability escalation attempt: cannot delegate unauthorized {:?}",
                    unauthorized
                )
            }
            Self::InvalidPublicKey(msg) => write!(f, "Invalid public key: {msg}"),
            Self::MalformedHex(msg) => write!(f, "Malformed hex string: {msg}"),
            Self::HashChainBroken { expected, actual } => {
                write!(
                    f,
                    "Audit hash chain broken: expected parent {expected}, got {actual}"
                )
            }
        }
    }
}

impl std::error::Error for AttestationError {}

/// A cryptographically attested agent identity token minted by the sovereign authority.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AgentIdentityToken {
    pub token_id: String,
    pub agent_id: String,
    pub agent_role: String,
    pub agent_verifying_key_hex: String,
    pub capabilities: BTreeSet<String>,
    pub issued_at_epoch: u64,
    pub expires_at_epoch: u64,
    pub nonce_hex: String,
    pub issuing_authority_key_hex: String,
    pub authority_signature_hex: String,
}

impl AgentIdentityToken {
    /// Mints a new attested identity token signed by the issuing authority.
    pub fn mint(
        authority_key: &SigningKey,
        agent_id: impl Into<String>,
        agent_vk: &VerifyingKey,
        agent_role: impl Into<String>,
        capabilities: impl IntoIterator<Item = impl Into<String>>,
        current_epoch: u64,
        ttl_epochs: u64,
        nonce_bytes: [u8; 16],
    ) -> Self {
        let agent_id = agent_id.into();
        let agent_role = agent_role.into();
        let agent_verifying_key_hex = hex_encode(&agent_vk.to_bytes());
        let capabilities_set: BTreeSet<String> = capabilities.into_iter().map(Into::into).collect();
        let expires_at_epoch = current_epoch.saturating_add(ttl_epochs);
        let nonce_hex = hex_encode(&nonce_bytes);
        let issuing_authority_key_hex = hex_encode(&authority_key.verifying_key().to_bytes());

        let payload = Self::canonical_payload(
            &agent_id,
            &agent_role,
            &agent_verifying_key_hex,
            &capabilities_set,
            current_epoch,
            expires_at_epoch,
            &nonce_hex,
            &issuing_authority_key_hex,
        );

        let mut hasher = Sha256::new();
        hasher.update(payload.as_bytes());
        let token_id = format!("agent-tok-{}", &hex_encode(&hasher.finalize())[..16]);

        let signature = authority_key.sign(payload.as_bytes());
        let authority_signature_hex = hex_encode(&signature.to_bytes());

        Self {
            token_id,
            agent_id,
            agent_role,
            agent_verifying_key_hex,
            capabilities: capabilities_set,
            issued_at_epoch: current_epoch,
            expires_at_epoch,
            nonce_hex,
            issuing_authority_key_hex,
            authority_signature_hex,
        }
    }

    /// Verifies the identity token against the expected sovereign root authority.
    pub fn verify(
        &self,
        expected_authority_vk: &VerifyingKey,
        current_epoch: u64,
    ) -> Result<(), AttestationError> {
        // 1. Check expiration
        if current_epoch > self.expires_at_epoch {
            return Err(AttestationError::ExpiredToken {
                expires_at: self.expires_at_epoch,
                current_epoch,
            });
        }

        // 2. Check authority key match
        let expected_auth_hex = hex_encode(&expected_authority_vk.to_bytes());
        if self.issuing_authority_key_hex != expected_auth_hex {
            return Err(AttestationError::AuthorityMismatch);
        }

        // 3. Reconstruct canonical payload
        let payload = Self::canonical_payload(
            &self.agent_id,
            &self.agent_role,
            &self.agent_verifying_key_hex,
            &self.capabilities,
            self.issued_at_epoch,
            self.expires_at_epoch,
            &self.nonce_hex,
            &self.issuing_authority_key_hex,
        );

        // 4. Verify cryptographic signature
        let sig_bytes = hex_decode_64(&self.authority_signature_hex).ok_or_else(|| {
            AttestationError::MalformedHex("Invalid 64-byte signature hex".into())
        })?;
        let signature = ed25519_dalek::Signature::from_bytes(&sig_bytes);

        expected_authority_vk
            .verify_strict(payload.as_bytes(), &signature)
            .map_err(|e| AttestationError::InvalidSignature(e.to_string()))?;

        Ok(())
    }

    /// Checks if the agent possesses a specific capability.
    #[must_use]
    pub fn has_capability(&self, required: &str) -> bool {
        self.capabilities.contains(required)
            || self.capabilities.contains("*")
            || self.capabilities.contains("admin:*")
    }

    fn canonical_payload(
        agent_id: &str,
        agent_role: &str,
        agent_vk_hex: &str,
        capabilities: &BTreeSet<String>,
        issued: u64,
        expires: u64,
        nonce_hex: &str,
        issuing_vk_hex: &str,
    ) -> String {
        let caps_joined: Vec<&str> = capabilities.iter().map(String::as_str).collect();
        format!(
            "WM_AGENT_TOKEN:agent={}:role={}:vk={}:caps={}:issued={}:expires={}:nonce={}:auth={}",
            agent_id,
            agent_role,
            agent_vk_hex,
            caps_joined.join(","),
            issued,
            expires,
            nonce_hex,
            issuing_vk_hex
        )
    }
}

/// A cryptographic delegation certificate allowing a primary agent to delegate a strict
/// subset of capabilities to a delegated subagent.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DelegationProof {
    pub delegation_id: String,
    pub delegator_token: AgentIdentityToken,
    pub delegate_agent_id: String,
    pub delegate_verifying_key_hex: String,
    pub delegated_capabilities: BTreeSet<String>,
    pub delegation_depth: u8,
    pub delegator_signature_hex: String,
}

impl DelegationProof {
    pub const MAX_DELEGATION_DEPTH: u8 = 3;

    /// Delegates capabilities to a subagent with cryptographic verification.
    pub fn delegate(
        delegator_key: &SigningKey,
        delegator_token: AgentIdentityToken,
        delegate_agent_id: impl Into<String>,
        delegate_vk: &VerifyingKey,
        requested_capabilities: impl IntoIterator<Item = impl Into<String>>,
        current_depth: u8,
    ) -> Result<Self, AttestationError> {
        let next_depth = current_depth.saturating_add(1);
        if next_depth > Self::MAX_DELEGATION_DEPTH {
            return Err(AttestationError::DelegationDepthExceeded {
                max: Self::MAX_DELEGATION_DEPTH,
                requested: next_depth,
            });
        }

        let delegate_agent_id = delegate_agent_id.into();
        let delegate_verifying_key_hex = hex_encode(&delegate_vk.to_bytes());
        let delegated_caps: BTreeSet<String> =
            requested_capabilities.into_iter().map(Into::into).collect();

        // Security Invariant: Capability Subsetting (No Privilege Escalation)
        let mut unauthorized = Vec::new();
        for cap in &delegated_caps {
            if !delegator_token.has_capability(cap) {
                unauthorized.push(cap.clone());
            }
        }
        if !unauthorized.is_empty() {
            return Err(AttestationError::CapabilityEscalation { unauthorized });
        }

        let payload = format!(
            "WM_DELEGATION:parent_tok={}:child={}:child_vk={}:caps={:?}:depth={}",
            delegator_token.token_id,
            delegate_agent_id,
            delegate_verifying_key_hex,
            delegated_caps,
            next_depth
        );

        let mut hasher = Sha256::new();
        hasher.update(payload.as_bytes());
        let delegation_id = format!("del-proof-{}", &hex_encode(&hasher.finalize())[..16]);

        let signature = delegator_key.sign(payload.as_bytes());
        let delegator_signature_hex = hex_encode(&signature.to_bytes());

        Ok(Self {
            delegation_id,
            delegator_token,
            delegate_agent_id,
            delegate_verifying_key_hex,
            delegated_capabilities: delegated_caps,
            delegation_depth: next_depth,
            delegator_signature_hex,
        })
    }

    /// Verifies the full delegation chain back to the root sovereign authority.
    pub fn verify_chain(
        &self,
        root_authority_vk: &VerifyingKey,
        current_epoch: u64,
    ) -> Result<(), AttestationError> {
        // 1. Verify parent token first
        self.delegator_token
            .verify(root_authority_vk, current_epoch)?;

        // 2. Verify delegator signature on the delegation proof
        let delegator_vk_bytes = hex_decode_32(&self.delegator_token.agent_verifying_key_hex)
            .ok_or_else(|| AttestationError::MalformedHex("Invalid delegator public key".into()))?;
        let delegator_vk = VerifyingKey::from_bytes(&delegator_vk_bytes)
            .map_err(|e| AttestationError::InvalidPublicKey(e.to_string()))?;

        let payload = format!(
            "WM_DELEGATION:parent_tok={}:child={}:child_vk={}:caps={:?}:depth={}",
            self.delegator_token.token_id,
            self.delegate_agent_id,
            self.delegate_verifying_key_hex,
            self.delegated_capabilities,
            self.delegation_depth
        );

        let sig_bytes = hex_decode_64(&self.delegator_signature_hex)
            .ok_or_else(|| AttestationError::MalformedHex("Invalid delegation signature".into()))?;
        let signature = ed25519_dalek::Signature::from_bytes(&sig_bytes);

        delegator_vk
            .verify_strict(payload.as_bytes(), &signature)
            .map_err(|e| AttestationError::InvalidSignature(e.to_string()))?;

        // 3. Verify subset invariant
        for cap in &self.delegated_capabilities {
            if !self.delegator_token.has_capability(cap) {
                return Err(AttestationError::CapabilityEscalation {
                    unauthorized: vec![cap.clone()],
                });
            }
        }

        Ok(())
    }
}

/// A tamper-evident cryptographic audit record linking an executed action to an agent identity.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AuditAttestation {
    pub attestation_id: String,
    pub agent_id: String,
    pub action_name: String,
    pub payload_hash_hex: String,
    pub parent_audit_hash_hex: Option<String>,
    pub timestamp_utc: String,
    pub agent_signature_hex: String,
}

impl AuditAttestation {
    /// Mints and signs an audit attestation.
    pub fn attest(
        agent_key: &SigningKey,
        agent_id: impl Into<String>,
        action_name: impl Into<String>,
        payload_bytes: &[u8],
        parent_audit_hash: Option<&str>,
    ) -> Self {
        let agent_id = agent_id.into();
        let action_name = action_name.into();
        let timestamp_utc = chrono::Utc::now().to_rfc3339();

        let mut payload_hasher = Sha256::new();
        payload_hasher.update(payload_bytes);
        let payload_hash_hex = hex_encode(&payload_hasher.finalize());

        let parent_audit_hash_hex = parent_audit_hash.map(String::from);

        let canonical = format!(
            "WM_AUDIT:agent={}:action={}:payload={}:parent={:?}:ts={}",
            agent_id, action_name, payload_hash_hex, parent_audit_hash_hex, timestamp_utc
        );

        let mut id_hasher = Sha256::new();
        id_hasher.update(canonical.as_bytes());
        let attestation_id = format!("audit-att-{}", &hex_encode(&id_hasher.finalize())[..16]);

        let signature = agent_key.sign(canonical.as_bytes());
        let agent_signature_hex = hex_encode(&signature.to_bytes());

        Self {
            attestation_id,
            agent_id,
            action_name,
            payload_hash_hex,
            parent_audit_hash_hex,
            timestamp_utc,
            agent_signature_hex,
        }
    }

    /// Verifies the signature and hash-chain continuity of the audit attestation.
    pub fn verify(
        &self,
        agent_vk: &VerifyingKey,
        expected_parent_hash: Option<&str>,
    ) -> Result<(), AttestationError> {
        // Check hash chain continuity
        if self.parent_audit_hash_hex.as_deref() != expected_parent_hash {
            return Err(AttestationError::HashChainBroken {
                expected: expected_parent_hash.unwrap_or("None").to_string(),
                actual: self
                    .parent_audit_hash_hex
                    .as_deref()
                    .unwrap_or("None")
                    .to_string(),
            });
        }

        let canonical = format!(
            "WM_AUDIT:agent={}:action={}:payload={}:parent={:?}:ts={}",
            self.agent_id,
            self.action_name,
            self.payload_hash_hex,
            self.parent_audit_hash_hex,
            self.timestamp_utc
        );

        let sig_bytes = hex_decode_64(&self.agent_signature_hex)
            .ok_or_else(|| AttestationError::MalformedHex("Invalid audit signature".into()))?;
        let signature = ed25519_dalek::Signature::from_bytes(&sig_bytes);

        agent_vk
            .verify_strict(canonical.as_bytes(), &signature)
            .map_err(|e| AttestationError::InvalidSignature(e.to_string()))?;

        Ok(())
    }
}

/// Helper: hex encode arbitrary bytes.
fn hex_encode(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        use std::fmt::Write as _;
        let _ = write!(s, "{:02x}", b);
    }
    s
}

/// Helper: decode 64 hex characters into 32-byte array.
fn hex_decode_32(hex_str: &str) -> Option<[u8; 32]> {
    if hex_str.len() != 64 {
        return None;
    }
    let mut out = [0u8; 32];
    for i in 0..32 {
        out[i] = u8::from_str_radix(&hex_str[i * 2..i * 2 + 2], 16).ok()?;
    }
    Some(out)
}

/// Helper: decode 128 hex characters into 64-byte array.
fn hex_decode_64(hex_str: &str) -> Option<[u8; 64]> {
    if hex_str.len() != 128 {
        return None;
    }
    let mut out = [0u8; 64];
    for i in 0..64 {
        out[i] = u8::from_str_radix(&hex_str[i * 2..i * 2 + 2], 16).ok()?;
    }
    Some(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_identity_token_mint_and_verify() {
        let auth_secret: [u8; 32] = [0x11; 32];
        let authority_key = SigningKey::from_bytes(&auth_secret);

        let agent_secret: [u8; 32] = [0x22; 32];
        let agent_key = SigningKey::from_bytes(&agent_secret);

        let token = AgentIdentityToken::mint(
            &authority_key,
            "did:key:antigravity-01",
            &agent_key.verifying_key(),
            "Architect",
            vec!["memory:read", "memory:write", "causal:intervene"],
            100, // current epoch
            50,  // ttl
            [0xaa; 16],
        );

        assert!(token.has_capability("memory:read"));
        assert!(token.has_capability("causal:intervene"));
        assert!(!token.has_capability("kernel:override"));

        // Valid verification at epoch 120
        assert!(token.verify(&authority_key.verifying_key(), 120).is_ok());

        // Expired verification at epoch 151
        let expired_err = token
            .verify(&authority_key.verifying_key(), 151)
            .unwrap_err();
        assert!(matches!(expired_err, AttestationError::ExpiredToken { .. }));

        // Authority mismatch
        let wrong_auth = SigningKey::from_bytes(&[0x99; 32]);
        let mismatch_err = token.verify(&wrong_auth.verifying_key(), 120).unwrap_err();
        assert_eq!(mismatch_err, AttestationError::AuthorityMismatch);
    }

    #[test]
    fn test_hierarchical_capability_delegation() {
        let auth_secret: [u8; 32] = [0x11; 32];
        let authority_key = SigningKey::from_bytes(&auth_secret);

        let primary_secret: [u8; 32] = [0x22; 32];
        let primary_key = SigningKey::from_bytes(&primary_secret);

        let subagent_secret: [u8; 32] = [0x33; 32];
        let subagent_key = SigningKey::from_bytes(&subagent_secret);

        // Root authority mints token for Primary Agent
        let primary_token = AgentIdentityToken::mint(
            &authority_key,
            "did:key:opencode-primary",
            &primary_key.verifying_key(),
            "PrimaryExecutor",
            vec!["memory:read", "memory:write", "sleep:cycle"],
            200,
            100,
            [0xbb; 16],
        );

        // Valid delegation: subset of capabilities (memory:read only)
        let delegation = DelegationProof::delegate(
            &primary_key,
            primary_token.clone(),
            "did:key:subagent-researcher",
            &subagent_key.verifying_key(),
            vec!["memory:read"],
            1, // current depth
        )
        .expect("Valid delegation must succeed");

        assert_eq!(delegation.delegation_depth, 2);
        assert!(
            delegation
                .verify_chain(&authority_key.verifying_key(), 210)
                .is_ok()
        );

        // Invalid delegation: privilege escalation (subagent asks for causal:intervene which primary does not have)
        let escalation_err = DelegationProof::delegate(
            &primary_key,
            primary_token,
            "did:key:subagent-rogue",
            &subagent_key.verifying_key(),
            vec!["memory:read", "causal:intervene"],
            1,
        )
        .unwrap_err();

        assert!(matches!(
            escalation_err,
            AttestationError::CapabilityEscalation { .. }
        ));
    }

    #[test]
    fn test_audit_attestation_hash_chain() {
        let agent_secret: [u8; 32] = [0x44; 32];
        let agent_key = SigningKey::from_bytes(&agent_secret);

        // Event 1
        let audit1 = AuditAttestation::attest(
            &agent_key,
            "did:key:agent-44",
            "causal.intervene",
            b"treatment=X;value=1.0",
            None,
        );
        assert!(audit1.verify(&agent_key.verifying_key(), None).is_ok());

        // Event 2 (chained to Event 1)
        let audit2 = AuditAttestation::attest(
            &agent_key,
            "did:key:agent-44",
            "sleep.cycle",
            b"quiescence=1.0",
            Some(&audit1.attestation_id),
        );
        assert!(
            audit2
                .verify(&agent_key.verifying_key(), Some(&audit1.attestation_id))
                .is_ok()
        );

        // Broken hash chain test
        let broken = audit2.verify(&agent_key.verifying_key(), Some("wrong-parent-hash"));
        assert!(matches!(
            broken,
            Err(AttestationError::HashChainBroken { .. })
        ));
    }
}
