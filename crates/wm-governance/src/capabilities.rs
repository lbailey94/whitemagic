//! Monadic capability-based effects and typed authorization grants.
//!
//! Enforces object-capability security across the tool dispatch surface:
//! tools declare their required effect capabilities (filesystem, network, IPC,
//! memory, model adaptation), and callers must present a valid, unexpired,
//! unrevoked [`CapabilityGrant`] or signed [`crate::engagement_tokens::EngagementToken`]
//! granting the required capability set before execution proceeds.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::engagement_tokens::{EngagementScope, EngagementToken};

/// Atomic effect capability bitflags.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Capability {
    /// Read access to the local filesystem.
    FsRead,
    /// Write / modify access to the local filesystem.
    FsWrite,
    /// Outbound network connection establishment.
    NetOutbound,
    /// Inbound network listener binding.
    NetInbound,
    /// Process spawning, subshell execution, and IPC creation.
    IpcSpawn,
    /// Read query against the local LMDB memory substrate.
    MemoryRead,
    /// Write / create memories in the local substrate.
    MemoryWrite,
    /// Delete or tombstone memories in the substrate.
    MemoryDelete,
    /// Trigger SEAL self-adapting inner-loop or LoRA weight modifications.
    SealAdapt,
    /// Invoke external or local model inference engines.
    ModelInvoke,
    /// Modify Dharma ethical policies, canary registries, or governance rules.
    AdminGovernance,
}

impl Capability {
    /// Bitmask representation of this capability.
    #[must_use]
    pub const fn bit(self) -> u32 {
        match self {
            Self::FsRead => 1 << 0,
            Self::FsWrite => 1 << 1,
            Self::NetOutbound => 1 << 2,
            Self::NetInbound => 1 << 3,
            Self::IpcSpawn => 1 << 4,
            Self::MemoryRead => 1 << 5,
            Self::MemoryWrite => 1 << 6,
            Self::MemoryDelete => 1 << 7,
            Self::SealAdapt => 1 << 8,
            Self::ModelInvoke => 1 << 9,
            Self::AdminGovernance => 1 << 10,
        }
    }

    /// Canonical lowercase label for this capability.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::FsRead => "fs:read",
            Self::FsWrite => "fs:write",
            Self::NetOutbound => "net:outbound",
            Self::NetInbound => "net:inbound",
            Self::IpcSpawn => "ipc:spawn",
            Self::MemoryRead => "memory:read",
            Self::MemoryWrite => "memory:write",
            Self::MemoryDelete => "memory:delete",
            Self::SealAdapt => "seal:adapt",
            Self::ModelInvoke => "model:invoke",
            Self::AdminGovernance => "admin:governance",
        }
    }

    /// Parse a capability from its canonical string label.
    #[must_use]
    pub fn from_label(label: &str) -> Option<Self> {
        match label {
            "fs:read" => Some(Self::FsRead),
            "fs:write" => Some(Self::FsWrite),
            "net:outbound" => Some(Self::NetOutbound),
            "net:inbound" => Some(Self::NetInbound),
            "ipc:spawn" => Some(Self::IpcSpawn),
            "memory:read" => Some(Self::MemoryRead),
            "memory:write" => Some(Self::MemoryWrite),
            "memory:delete" => Some(Self::MemoryDelete),
            "seal:adapt" => Some(Self::SealAdapt),
            "model:invoke" => Some(Self::ModelInvoke),
            "admin:governance" => Some(Self::AdminGovernance),
            _ => None,
        }
    }
}

/// A compact, bitmask-backed set of granted or required capabilities.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct CapabilitySet {
    bits: u32,
}

impl CapabilitySet {
    /// Empty capability set (zero privileges).
    pub const EMPTY: Self = Self { bits: 0 };

    /// Read-only inspection privileges (safe for public or untrusted callers).
    pub const READ_ONLY: Self = Self {
        bits: Capability::FsRead.bit()
            | Capability::MemoryRead.bit()
            | Capability::ModelInvoke.bit(),
    };

    /// Standard agent operating privileges.
    pub const STANDARD_AGENT: Self = Self {
        bits: Capability::FsRead.bit()
            | Capability::MemoryRead.bit()
            | Capability::MemoryWrite.bit()
            | Capability::ModelInvoke.bit(),
    };

    /// Red-team / breaker diagnostic privileges.
    pub const REDTEAM_DIAGNOSTIC: Self = Self {
        bits: Capability::FsRead.bit()
            | Capability::FsWrite.bit()
            | Capability::NetOutbound.bit()
            | Capability::IpcSpawn.bit()
            | Capability::MemoryRead.bit()
            | Capability::MemoryWrite.bit()
            | Capability::ModelInvoke.bit(),
    };

    /// Full administrative root privileges.
    pub const ALL: Self = Self {
        bits: (1 << 11) - 1,
    };

    /// Construct a set from raw bitmask.
    #[must_use]
    pub const fn from_bits(bits: u32) -> Self {
        Self { bits }
    }

    /// Retrieve the underlying u32 bitmask.
    #[must_use]
    pub const fn bits(self) -> u32 {
        self.bits
    }

    /// Check if the set contains a specific capability.
    #[must_use]
    pub const fn contains(self, cap: Capability) -> bool {
        (self.bits & cap.bit()) != 0
    }

    /// Add a capability to the set.
    pub const fn insert(&mut self, cap: Capability) {
        self.bits |= cap.bit();
    }

    /// Remove a capability from the set.
    pub const fn remove(&mut self, cap: Capability) {
        self.bits &= !cap.bit();
    }

    /// Check if this capability set is empty.
    #[must_use]
    pub const fn is_empty(self) -> bool {
        self.bits == 0
    }

    /// Check if `self` is a superset of `required` (i.e. contains all required capabilities).
    #[must_use]
    pub const fn satisfies(self, required: Self) -> bool {
        (self.bits & required.bits) == required.bits
    }

    /// Union of two capability sets.
    #[must_use]
    pub const fn union(self, other: Self) -> Self {
        Self {
            bits: self.bits | other.bits,
        }
    }

    /// Intersection of two capability sets.
    #[must_use]
    pub const fn intersection(self, other: Self) -> Self {
        Self {
            bits: self.bits & other.bits,
        }
    }

    /// Difference (`self` without `other`).
    #[must_use]
    pub const fn difference(self, other: Self) -> Self {
        Self {
            bits: self.bits & !other.bits,
        }
    }

    /// Convert into a list of string labels for serialization and logging.
    #[must_use]
    pub fn labels(self) -> Vec<&'static str> {
        let all = [
            Capability::FsRead,
            Capability::FsWrite,
            Capability::NetOutbound,
            Capability::NetInbound,
            Capability::IpcSpawn,
            Capability::MemoryRead,
            Capability::MemoryWrite,
            Capability::MemoryDelete,
            Capability::SealAdapt,
            Capability::ModelInvoke,
            Capability::AdminGovernance,
        ];
        all.into_iter()
            .filter(|c| self.contains(*c))
            .map(Capability::label)
            .collect()
    }
}

impl Default for CapabilitySet {
    fn default() -> Self {
        Self::EMPTY
    }
}

impl From<Capability> for CapabilitySet {
    fn from(cap: Capability) -> Self {
        Self { bits: cap.bit() }
    }
}

impl<const N: usize> From<[Capability; N]> for CapabilitySet {
    fn from(caps: [Capability; N]) -> Self {
        let mut set = Self::EMPTY;
        for cap in caps {
            set.insert(cap);
        }
        set
    }
}

/// Errors occurring during capability assertions or verification.
#[derive(Debug, Error, PartialEq, Eq, Clone)]
pub enum CapabilityError {
    /// Required capabilities are missing from the grant.
    #[error("Missing capabilities: required [{required}], but granted [{granted}]")]
    MissingCapabilities { required: String, granted: String },
    /// The authorization token or grant has expired.
    #[error("Capability grant expired at unix epoch {expired_at}, current time {now}")]
    GrantExpired { expired_at: i64, now: i64 },
    /// The underlying engagement token was revoked.
    #[error("Engagement token {token_id} has been revoked")]
    TokenRevoked { token_id: String },
    /// The engagement token's Ed25519 signature does not verify against the
    /// supplied issuer key (forged, tampered, or wrong issuer).
    #[error("Engagement token {token_id} signature is invalid for the supplied issuer key")]
    TokenSignatureInvalid { token_id: String },
    /// File access path outside allowed bounds.
    #[error("Path '{path}' is not permitted by capability grant (allowed: {allowed:?})")]
    PathDisallowed { path: String, allowed: Vec<String> },
    /// Outbound network host is not permitted by capability grant.
    #[error("Host '{host}' is not permitted by capability grant (allowed: {allowed:?})")]
    HostDisallowed { host: String, allowed: Vec<String> },
}

/// A structured capability grant binding permissions to an agent or session.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CapabilityGrant {
    /// Unique grant ID.
    pub id: String,
    /// Principal to whom this grant applies.
    pub principal: String,
    /// Granted capabilities.
    pub capabilities: CapabilitySet,
    /// Optional underlying EngagementToken id.
    pub engagement_token_id: Option<String>,
    /// Restricted filesystem directories (empty = unrestricted within capability).
    pub allowed_paths: Vec<String>,
    /// Restricted outbound destination hosts (empty = unrestricted within capability).
    pub allowed_hosts: Vec<String>,
    /// Unix epoch seconds when issued.
    pub issued_at: i64,
    /// Unix epoch seconds when expired (`None` = until revoked).
    pub expires_at: Option<i64>,
}

impl CapabilityGrant {
    /// Issue a new grant with standard fields.
    #[must_use]
    pub fn new(
        id: impl Into<String>,
        principal: impl Into<String>,
        capabilities: CapabilitySet,
        issued_at: i64,
        expires_at: Option<i64>,
    ) -> Self {
        Self {
            id: id.into(),
            principal: principal.into(),
            capabilities,
            engagement_token_id: None,
            allowed_paths: Vec::new(),
            allowed_hosts: Vec::new(),
            issued_at,
            expires_at,
        }
    }

    /// Add a path restriction.
    #[must_use]
    pub fn with_allowed_path(mut self, path: impl Into<String>) -> Self {
        self.allowed_paths.push(path.into());
        self
    }

    /// Add a host restriction.
    #[must_use]
    pub fn with_allowed_host(mut self, host: impl Into<String>) -> Self {
        self.allowed_hosts.push(host.into());
        self
    }

    /// Bind to an engagement token.
    #[must_use]
    pub fn with_engagement_token(mut self, token_id: impl Into<String>) -> Self {
        self.engagement_token_id = Some(token_id.into());
        self
    }

    /// Verify this grant against required capabilities, current time, and optional path/host.
    pub fn assert(
        &self,
        required: CapabilitySet,
        now: i64,
        path: Option<&str>,
        host: Option<&str>,
    ) -> Result<(), CapabilityError> {
        // Expiry check
        if let Some(exp) = self.expires_at {
            if now >= exp {
                return Err(CapabilityError::GrantExpired {
                    expired_at: exp,
                    now,
                });
            }
        }

        // Capabilities check
        if !self.capabilities.satisfies(required) {
            let missing = required.difference(self.capabilities);
            return Err(CapabilityError::MissingCapabilities {
                required: missing.labels().join(", "),
                granted: self.capabilities.labels().join(", "),
            });
        }

        // Path restriction check if FsRead or FsWrite required
        if (required.contains(Capability::FsRead) || required.contains(Capability::FsWrite))
            && !self.allowed_paths.is_empty()
        {
            if let Some(p) = path {
                let allowed = self.allowed_paths.iter().any(|root| p.starts_with(root));
                if !allowed {
                    return Err(CapabilityError::PathDisallowed {
                        path: p.to_string(),
                        allowed: self.allowed_paths.clone(),
                    });
                }
            }
        }

        // Host restriction check if NetOutbound required
        if required.contains(Capability::NetOutbound) && !self.allowed_hosts.is_empty() {
            if let Some(h) = host {
                let allowed = self.allowed_hosts.iter().any(|allowed| allowed == h);
                if !allowed {
                    return Err(CapabilityError::HostDisallowed {
                        host: h.to_string(),
                        allowed: self.allowed_hosts.clone(),
                    });
                }
            }
        }

        Ok(())
    }
}

/// Derive default capabilities from an EngagementScope.
#[must_use]
pub fn capabilities_for_engagement(scope: &EngagementScope) -> CapabilitySet {
    match scope {
        EngagementScope::Poc => CapabilitySet::from([
            Capability::FsRead,
            Capability::MemoryRead,
            Capability::MemoryWrite,
            Capability::ModelInvoke,
        ]),
        EngagementScope::Redteam => CapabilitySet::REDTEAM_DIAGNOSTIC,
        EngagementScope::Demo => {
            CapabilitySet::from([Capability::MemoryRead, Capability::ModelInvoke])
        }
        EngagementScope::Custom(_) => CapabilitySet::READ_ONLY,
    }
}

/// Assert that an EngagementToken is validly signed by the issuer and grants
/// the required capability set at the given timestamp.
///
/// Full check set: Ed25519 signature → revocation → expiry → scope-derived
/// capabilities. The signature check comes first, so a forged token can never
/// pass on a lucky scope match.
pub fn assert_engagement_token_capabilities(
    token: &EngagementToken,
    issuer_public_key_hex: &str,
    required: CapabilitySet,
    now: i64,
) -> Result<(), CapabilityError> {
    if !crate::engagement_tokens::verify_token_signature(token, issuer_public_key_hex) {
        return Err(CapabilityError::TokenSignatureInvalid {
            token_id: token.id.clone(),
        });
    }

    if token.revoked {
        return Err(CapabilityError::TokenRevoked {
            token_id: token.id.clone(),
        });
    }

    if let Some(exp) = token.expires_at {
        if now >= exp {
            return Err(CapabilityError::GrantExpired {
                expired_at: exp,
                now,
            });
        }
    }

    let granted = capabilities_for_engagement(&token.scope);
    if !granted.satisfies(required) {
        let missing = required.difference(granted);
        return Err(CapabilityError::MissingCapabilities {
            required: missing.labels().join(", "),
            granted: granted.labels().join(", "),
        });
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn capability_bit_consistency() {
        assert_eq!(Capability::FsRead.bit(), 1);
        assert_eq!(Capability::FsWrite.bit(), 2);
        assert_eq!(Capability::AdminGovernance.bit(), 1 << 10);
    }

    #[test]
    fn capability_set_insert_remove() {
        let mut set = CapabilitySet::EMPTY;
        assert!(set.is_empty());
        assert!(!set.contains(Capability::FsRead));

        set.insert(Capability::FsRead);
        assert!(set.contains(Capability::FsRead));
        assert!(!set.is_empty());

        set.insert(Capability::NetOutbound);
        assert!(set.contains(Capability::NetOutbound));

        set.remove(Capability::FsRead);
        assert!(!set.contains(Capability::FsRead));
        assert!(set.contains(Capability::NetOutbound));
    }

    #[test]
    fn capability_satisfies_subsets() {
        let agent = CapabilitySet::STANDARD_AGENT;
        let read_fs = CapabilitySet::from(Capability::FsRead);
        let write_fs = CapabilitySet::from(Capability::FsWrite);

        assert!(agent.satisfies(read_fs));
        assert!(!agent.satisfies(write_fs)); // standard agent has memory write, not fs write
        assert!(CapabilitySet::ALL.satisfies(agent));
    }

    #[test]
    fn capability_labels_roundtrip() {
        let set = CapabilitySet::from([Capability::FsRead, Capability::SealAdapt]);
        let labels = set.labels();
        assert_eq!(labels, vec!["fs:read", "seal:adapt"]);

        assert_eq!(Capability::from_label("fs:read"), Some(Capability::FsRead));
        assert_eq!(Capability::from_label("invalid"), None);
    }

    #[test]
    fn capability_grant_assertion_expiry() {
        let grant = CapabilityGrant::new(
            "cpg_01",
            "agent_alpha",
            CapabilitySet::ALL,
            1000,
            Some(2000),
        );
        assert!(
            grant
                .assert(CapabilitySet::READ_ONLY, 1500, None, None)
                .is_ok()
        );

        let err = grant
            .assert(CapabilitySet::READ_ONLY, 2000, None, None)
            .unwrap_err();
        assert_eq!(
            err,
            CapabilityError::GrantExpired {
                expired_at: 2000,
                now: 2000
            }
        );
    }

    #[test]
    fn capability_grant_assertion_missing_privilege() {
        let grant =
            CapabilityGrant::new("cpg_02", "agent_beta", CapabilitySet::READ_ONLY, 1000, None);
        let err = grant
            .assert(CapabilitySet::from(Capability::FsWrite), 1500, None, None)
            .unwrap_err();
        match err {
            CapabilityError::MissingCapabilities { required, .. } => {
                assert!(required.contains("fs:write"));
            }
            other => panic!("Unexpected error: {other:?}"),
        }
    }

    #[test]
    fn capability_grant_path_restriction() {
        let grant = CapabilityGrant::new("cpg_03", "agent_gamma", CapabilitySet::ALL, 1000, None)
            .with_allowed_path("/safe/dir");

        assert!(
            grant
                .assert(
                    CapabilitySet::from(Capability::FsRead),
                    1500,
                    Some("/safe/dir/file.txt"),
                    None
                )
                .is_ok()
        );
        let err = grant
            .assert(
                CapabilitySet::from(Capability::FsRead),
                1500,
                Some("/etc/shadow"),
                None,
            )
            .unwrap_err();
        assert!(matches!(err, CapabilityError::PathDisallowed { .. }));
    }

    #[test]
    fn capability_grant_host_restriction() {
        let grant = CapabilityGrant::new("cpg_04", "agent_delta", CapabilitySet::ALL, 1000, None)
            .with_allowed_host("api.whitemagic.dev");

        assert!(
            grant
                .assert(
                    CapabilitySet::from(Capability::NetOutbound),
                    1500,
                    None,
                    Some("api.whitemagic.dev")
                )
                .is_ok()
        );
        let err = grant
            .assert(
                CapabilitySet::from(Capability::NetOutbound),
                1500,
                None,
                Some("evil.com"),
            )
            .unwrap_err();
        assert!(matches!(err, CapabilityError::HostDisallowed { .. }));
    }

    #[test]
    fn engagement_token_capability_assertions() {
        let mut issuer = crate::engagement_tokens::EngagementIssuer::with_keypair(
            crate::network_profile::AgentKeypair::from_seed([42u8; 32]),
        );
        let issuer_key = issuer.signer_public_key_hex();
        let token = issuer.issue("tester", EngagementScope::Poc, "hash", Some(5000));
        let now = token.issued_at + 1;

        // Poc grants FsRead, MemoryRead, MemoryWrite, ModelInvoke
        assert!(
            assert_engagement_token_capabilities(
                &token,
                &issuer_key,
                CapabilitySet::from(Capability::FsRead),
                now
            )
            .is_ok()
        );
        assert!(
            assert_engagement_token_capabilities(
                &token,
                &issuer_key,
                CapabilitySet::from(Capability::NetOutbound),
                now
            )
            .is_err()
        );

        // Revocation blocks
        let mut revoked = token.clone();
        revoked.revoked = true;
        let err = assert_engagement_token_capabilities(
            &revoked,
            &issuer_key,
            CapabilitySet::from(Capability::FsRead),
            now,
        )
        .unwrap_err();
        assert_eq!(
            err,
            CapabilityError::TokenRevoked {
                token_id: revoked.id
            }
        );

        // Forged signature blocks even with a matching scope
        let mut forged = token.clone();
        forged.signature = "0".repeat(128);
        let err = assert_engagement_token_capabilities(
            &forged,
            &issuer_key,
            CapabilitySet::from(Capability::FsRead),
            now,
        )
        .unwrap_err();
        assert_eq!(
            err,
            CapabilityError::TokenSignatureInvalid {
                token_id: forged.id
            }
        );

        // Wrong issuer key blocks
        let other_key = crate::network_profile::AgentKeypair::from_seed([9u8; 32]).public_key_hex();
        assert!(
            assert_engagement_token_capabilities(
                &token,
                &other_key,
                CapabilitySet::from(Capability::FsRead),
                now
            )
            .is_err()
        );

        // Expiry blocks
        assert!(
            assert_engagement_token_capabilities(
                &token,
                &issuer_key,
                CapabilitySet::from(Capability::FsRead),
                token.expires_at.unwrap() + 1
            )
            .is_err()
        );
    }
}
