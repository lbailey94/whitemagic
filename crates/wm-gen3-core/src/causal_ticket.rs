//! Causal JEV Decision & Gate 13 Capability Ticket.
//!
//! Replaces conversational text negotiations of safety with cryptographically signed,
//! Pearl SCM Level 2/3 interventional utility proofs bound to kernel Landlock LSM tokens.

use chrono::Utc;
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fmt;
use std::path::PathBuf;
use uuid::Uuid;

use crate::mandala::{MandalaError, SandboxRuleset, WorkspaceClaim, LandlockSandbox};

/// Errors relating to causal capability tickets.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum CausalTicketError {
    Expired { now_ms: u64, expires_ms: u64 },
    InvalidSignature,
    InvalidPublicKey,
    Mandala(String),
}

impl fmt::Display for CausalTicketError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Expired { now_ms, expires_ms } => {
                write!(f, "Ticket has expired (now: {now_ms}, expires: {expires_ms})")
            }
            Self::InvalidSignature => write!(f, "Cryptographic signature verification failed"),
            Self::InvalidPublicKey => write!(f, "Invalid public key encoding"),
            Self::Mandala(msg) => write!(f, "Mandala sandbox error: {msg}"),
        }
    }
}

impl std::error::Error for CausalTicketError {}

impl From<MandalaError> for CausalTicketError {
    fn from(err: MandalaError) -> Self {
        Self::Mandala(err.to_string())
    }
}

/// A cryptographically signed capability ticket coupling Pearl SCM causal inference
/// to kernel Landlock LSM access permissions.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CausalCapabilityTicket {
    /// Unique task identifier.
    pub task_id: Uuid,
    /// Semantic action or tool invocation name (e.g. "patch_bridge").
    pub action_name: String,
    /// Causal treatment variable name (e.g. "RouteChoice").
    pub treatment_var: String,
    /// Target candidate treatment value evaluated under $do(X = x)$.
    pub candidate_val: f64,
    /// Pearl Level 2 causal lift: $\mathbb{E}[Y \mid do(X = \text{cand})] - \mathbb{E}[Y \mid do(X = \text{base})]$.
    pub causal_lift: f64,
    /// Pearl Level 3 counterfactual risk probability: $P(Y_{X=x'} \le 0 \mid X=x, Y=y)$.
    pub counterfactual_risk: f64,
    /// Unified JEV decision tensor composite score.
    pub jev_decision_score: f64,
    /// Whitelisted read-only filesystem paths.
    pub allowed_read_paths: Vec<PathBuf>,
    /// Whitelisted read-write filesystem paths.
    pub allowed_write_paths: Vec<PathBuf>,
    /// Whether outbound TCP network access is permitted.
    pub network_allowed: bool,
    /// Issuance timestamp in Unix milliseconds.
    pub issued_at_ms: u64,
    /// Expiration timestamp in Unix milliseconds.
    pub expires_at_ms: u64,
    /// Node or agent identity issuing this ticket.
    pub issuer_id: String,
    /// Ed25519 verifying public key (32 bytes).
    #[serde(with = "serde_pubkey")]
    pub issuer_pk: [u8; 32],
    /// Ed25519 signature over the canonical ticket digest (64 bytes).
    #[serde(with = "serde_sig")]
    pub signature: [u8; 64],
}

mod serde_pubkey {
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    pub fn serialize<S>(bytes: &[u8; 32], s: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if s.is_human_readable() {
            let mut hex_str = String::with_capacity(64);
            for b in bytes {
                hex_str.push_str(&format!("{b:02x}"));
            }
            s.serialize_str(&hex_str)
        } else {
            bytes.serialize(s)
        }
    }

    pub fn deserialize<'de, D>(d: D) -> Result<[u8; 32], D::Error>
    where
        D: Deserializer<'de>,
    {
        if d.is_human_readable() {
            let s = String::deserialize(d)?;
            if s.len() != 64 {
                return Err(serde::de::Error::custom("expected 64 hex characters for public key"));
            }
            let mut arr = [0u8; 32];
            for i in 0..32 {
                arr[i] = u8::from_str_radix(&s[i * 2..i * 2 + 2], 16)
                    .map_err(serde::de::Error::custom)?;
            }
            Ok(arr)
        } else {
            let bytes = Vec::<u8>::deserialize(d)?;
            if bytes.len() != 32 {
                return Err(serde::de::Error::custom("expected 32 bytes for public key"));
            }
            let mut arr = [0u8; 32];
            arr.copy_from_slice(&bytes);
            Ok(arr)
        }
    }
}

mod serde_sig {
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    pub fn serialize<S>(bytes: &[u8; 64], s: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        if s.is_human_readable() {
            let mut hex_str = String::with_capacity(128);
            for b in bytes {
                hex_str.push_str(&format!("{b:02x}"));
            }
            s.serialize_str(&hex_str)
        } else {
            bytes.serialize(s)
        }
    }

    pub fn deserialize<'de, D>(d: D) -> Result<[u8; 64], D::Error>
    where
        D: Deserializer<'de>,
    {
        if d.is_human_readable() {
            let s = String::deserialize(d)?;
            if s.len() != 128 {
                return Err(serde::de::Error::custom("expected 128 hex characters for signature"));
            }
            let mut arr = [0u8; 64];
            for i in 0..64 {
                arr[i] = u8::from_str_radix(&s[i * 2..i * 2 + 2], 16)
                    .map_err(serde::de::Error::custom)?;
            }
            Ok(arr)
        } else {
            let bytes = Vec::<u8>::deserialize(d)?;
            if bytes.len() != 64 {
                return Err(serde::de::Error::custom("expected 64 bytes for signature"));
            }
            let mut arr = [0u8; 64];
            arr.copy_from_slice(&bytes);
            Ok(arr)
        }
    }
}

impl CausalCapabilityTicket {
    /// Computes the canonical SHA-256 digest string of this ticket.
    #[must_use]
    pub fn canonical_digest(&self) -> [u8; 32] {
        let mut hasher = Sha256::new();
        hasher.update(b"WHITEMAGIC:CAUSAL_TICKET:v1\n");
        hasher.update(self.task_id.as_bytes());
        hasher.update(b":");
        hasher.update(self.action_name.as_bytes());
        hasher.update(b":");
        hasher.update(self.treatment_var.as_bytes());
        hasher.update(b":");
        hasher.update(format!("{:.6}", self.candidate_val).as_bytes());
        hasher.update(b":");
        hasher.update(format!("{:.6}", self.causal_lift).as_bytes());
        hasher.update(b":");
        hasher.update(format!("{:.6}", self.counterfactual_risk).as_bytes());
        hasher.update(b":");
        hasher.update(format!("{:.6}", self.jev_decision_score).as_bytes());
        hasher.update(b":");
        for p in &self.allowed_read_paths {
            hasher.update(p.to_string_lossy().as_bytes());
            hasher.update(b",");
        }
        hasher.update(b":");
        for p in &self.allowed_write_paths {
            hasher.update(p.to_string_lossy().as_bytes());
            hasher.update(b",");
        }
        hasher.update(b":");
        hasher.update(if self.network_allowed { b"net_ok" } else { b"no_net" });
        hasher.update(b":");
        hasher.update(self.issued_at_ms.to_le_bytes());
        hasher.update(b":");
        hasher.update(self.expires_at_ms.to_le_bytes());
        hasher.update(b":");
        hasher.update(self.issuer_id.as_bytes());
        hasher.finalize().into()
    }

    /// Mints and cryptographically signs a new CausalCapabilityTicket.
    pub fn mint(
        task_id: Uuid,
        action_name: impl Into<String>,
        treatment_var: impl Into<String>,
        candidate_val: f64,
        causal_lift: f64,
        counterfactual_risk: f64,
        jev_decision_score: f64,
        allowed_read_paths: Vec<PathBuf>,
        allowed_write_paths: Vec<PathBuf>,
        network_allowed: bool,
        ttl_ms: u64,
        issuer_id: impl Into<String>,
        signing_key: &SigningKey,
    ) -> Self {
        let now_ms = Utc::now().timestamp_millis().max(0) as u64;
        let expires_at_ms = now_ms + ttl_ms.max(1000);
        let issuer_pk = signing_key.verifying_key().to_bytes();

        let mut ticket = Self {
            task_id,
            action_name: action_name.into(),
            treatment_var: treatment_var.into(),
            candidate_val,
            causal_lift,
            counterfactual_risk,
            jev_decision_score,
            allowed_read_paths,
            allowed_write_paths,
            network_allowed,
            issued_at_ms: now_ms,
            expires_at_ms,
            issuer_id: issuer_id.into(),
            issuer_pk,
            signature: [0u8; 64],
        };

        let digest = ticket.canonical_digest();
        let sig: Signature = signing_key.sign(&digest);
        ticket.signature = sig.to_bytes();
        ticket
    }

    /// Verifies the cryptographic signature and checks expiration.
    pub fn verify(&self, now_ms: u64) -> Result<(), CausalTicketError> {
        if now_ms > self.expires_at_ms {
            return Err(CausalTicketError::Expired {
                now_ms,
                expires_ms: self.expires_at_ms,
            });
        }

        let vk = VerifyingKey::from_bytes(&self.issuer_pk)
            .map_err(|_| CausalTicketError::InvalidPublicKey)?;
        let sig = Signature::from_bytes(&self.signature);
        let digest = self.canonical_digest();

        vk.verify(&digest, &sig)
            .map_err(|_| CausalTicketError::InvalidSignature)
    }

    /// Converts this capability ticket into an authorized Mandala `WorkspaceClaim`
    /// for kernel-level Landlock LSM sandboxing.
    pub fn to_workspace_claim(&self, workspace_root: impl Into<PathBuf>) -> WorkspaceClaim {
        WorkspaceClaim {
            claim_id: format!("claim:causal:{}", self.task_id),
            tenant_id: "whitemagic".into(),
            agent_id: self.issuer_id.clone(),
            workspace_root: workspace_root.into(),
            read_only_paths: self.allowed_read_paths.clone(),
            read_write_paths: self.allowed_write_paths.clone(),
            network_allowed: self.network_allowed,
            kekkai_phase: crate::mandala::KekkaiPhase::default(),
            resource_limits: None,
            created_at: self.issued_at_ms / 1000,
            expires_at: self.expires_at_ms / 1000,
            signature: Some(self.signature.to_vec()),
        }
    }

    /// Builds a native Landlock sandbox ruleset from this ticket's authorized paths.
    #[cfg(target_os = "linux")]
    pub fn enforce_landlock(&self, workspace_root: impl Into<PathBuf>) -> Result<SandboxRuleset, MandalaError> {
        let claim = self.to_workspace_claim(workspace_root);
        LandlockSandbox::build_ruleset(&claim)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_causal_ticket_mint_verify_lifecycle() {
        let secret = [42u8; 32];
        let signing_key = SigningKey::from_bytes(&secret);
        let task_id = Uuid::new_v4();

        let ticket = CausalCapabilityTicket::mint(
            task_id,
            "patch_bridge",
            "RouteChoice",
            1.0,
            0.42,  // causal lift
            0.03,  // counterfactual risk (3%)
            0.89,  // JEV score
            vec![PathBuf::from("/etc/ssl")],
            vec![PathBuf::from("/home/lucas/SharedWorkspace/bridge.py")],
            false, // no network allowed
            60_000,
            "antigravity",
            &signing_key,
        );

        // Verification immediately at issue time must pass
        assert!(ticket.verify(ticket.issued_at_ms).is_ok());

        // Verification after TTL must fail with Expired
        let err = ticket.verify(ticket.expires_at_ms + 100).unwrap_err();
        match err {
            CausalTicketError::Expired { .. } => {}
            _ => panic!("Expected Expired error"),
        }

        // Tampered ticket must fail signature verification
        let mut tampered = ticket.clone();
        tampered.causal_lift = 0.99;
        let tamper_err = tampered.verify(tampered.issued_at_ms).unwrap_err();
        match tamper_err {
            CausalTicketError::InvalidSignature => {}
            _ => panic!("Expected InvalidSignature error"),
        }
    }

    #[test]
    fn test_to_workspace_claim_conversion() {
        let secret = [42u8; 32];
        let signing_key = SigningKey::from_bytes(&secret);
        let task_id = Uuid::new_v4();
        let ticket = CausalCapabilityTicket::mint(
            task_id,
            "test_action",
            "X",
            1.0,
            0.5,
            0.01,
            0.95,
            vec![],
            vec![PathBuf::from("/tmp/test")],
            false,
            10_000,
            "opencode",
            &signing_key,
        );

        let claim = ticket.to_workspace_claim("/home/lucas/workspace");
        assert_eq!(claim.agent_id, "opencode");
        assert_eq!(claim.read_write_paths.len(), 1);
        assert!(!claim.network_allowed);
    }
}
