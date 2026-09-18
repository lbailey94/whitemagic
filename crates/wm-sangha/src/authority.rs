//! Local mesh authority policy — the node's own grant table.
//!
//! [`crate::peer::PeerAuthority`] inside a heartbeat is **peer-declared**:
//! the sender signs its own claims, so it can claim anything. This module is
//! the local, authoritative answer to "what may THIS peer do on THIS node".
//! Enforcement is **default-deny**: a bound peer with no local grant gets
//! [`PeerAuthority::none()`] regardless of what it declared.
//!
//! Provisioning is an operator action on a side map
//! (`<store>/mesh_authority.json`, override with `WM_MESH_AUTHORITY_FILE`):
//!
//! ```json
//! {
//!   "mode": "enforce",
//!   "grants": {
//!     "wm-0a1b2c3d4e5f": {
//!       "public_key": "…hex…",
//!       "can_execute": true,
//!       "can_write_memory": false,
//!       "can_delegate": false
//!     }
//!   }
//! }
//! ```
//!
//! - `mode: "enforce"` (default) — unprovisioned bound peers are denied
//!   action-class traffic (chat, signals, locks). Discovery still works:
//!   hints and binds are not authority.
//! - `mode: "advisory"` — the legacy behavior (peer-declared authority is
//!   honored) for a migration window; loud in `/status`.
//! - `public_key` pins the grant to the peer's bound key; **omit it and the
//!   grant inherits the TOFU binding** (first signed heartbeat wins).
//! - A missing file means enforce with no grants. A malformed file fails
//!   closed the same way, loudly.
//!
//! Changing the file applies at node start; edit + restart to change policy.

use std::collections::BTreeMap;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::peer::PeerAuthority;

/// `WM_MESH_AUTHORITY` — `enforce` (default) | `advisory`.
pub const ENV_MESH_AUTHORITY: &str = "WM_MESH_AUTHORITY";
/// `WM_MESH_AUTHORITY_FILE` — side-map path override.
pub const ENV_MESH_AUTHORITY_FILE: &str = "WM_MESH_AUTHORITY_FILE";

/// Enforcement mode for the local authority policy.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum AuthorityMode {
    /// Unprovisioned peers are denied action-class traffic (default).
    #[default]
    Enforce,
    /// Legacy: peer-declared authority is honored (migration window only).
    Advisory,
}

impl AuthorityMode {
    /// Stable label for status surfaces and errors.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Enforce => "enforce",
            Self::Advisory => "advisory",
        }
    }

    /// Strict parse: only the exact labels count (house style).
    #[must_use]
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim() {
            "enforce" => Some(Self::Enforce),
            "advisory" => Some(Self::Advisory),
            _ => None,
        }
    }
}

/// One operator grant for a peer ID.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthorityGrant {
    /// Optional identity pin: when set, the grant applies only while the
    /// peer's bound key matches. Omitted = the grant follows the TOFU
    /// binding (the first signed heartbeat to claim the ID wins).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub public_key: Option<String>,
    /// The capabilities this node grants the peer.
    #[serde(flatten)]
    pub authority: PeerAuthority,
}

/// Where a peer's effective authority came from — named in gate errors so
/// operators can tell "not provisioned" from "provisioned without rights".
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AuthoritySource {
    /// An operator grant in this node's policy.
    Provisioned,
    /// Peer-declared, honored because the policy is in advisory mode.
    AdvisoryDeclared,
    /// No grant and enforce mode — default-deny.
    DefaultDenied,
}

/// The authority a peer effectively holds on this node.
#[derive(Debug, Clone)]
pub struct EffectiveAuthority {
    /// The authority to enforce.
    pub authority: PeerAuthority,
    /// Why that authority (disclosure for error messages and status).
    pub source: AuthoritySource,
}

/// The local policy: mode + grants keyed by peer ID.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MeshAuthorityPolicy {
    /// Enforcement mode (file value; `WM_MESH_AUTHORITY` overrides at load).
    #[serde(default)]
    pub mode: AuthorityMode,
    /// Operator grants, keyed by peer ID.
    #[serde(default)]
    pub grants: BTreeMap<String, AuthorityGrant>,
}

impl MeshAuthorityPolicy {
    /// Enforce mode with no grants — the fail-closed default.
    #[must_use]
    pub fn enforce() -> Self {
        Self::default()
    }

    /// Advisory mode (legacy peer-declared authority) — migration only.
    #[must_use]
    pub const fn advisory() -> Self {
        Self {
            mode: AuthorityMode::Advisory,
            grants: BTreeMap::new(),
        }
    }

    /// Enforce-mode policy with `WM_MESH_AUTHORITY` applied; no file.
    #[must_use]
    pub fn from_env() -> Self {
        let mut policy = Self::enforce();
        apply_env_mode(&mut policy);
        policy
    }

    /// Resolve the policy for a node start: load `path` when present (a
    /// missing file is the empty enforce policy), apply the env mode
    /// override, and **fail closed loudly** on a malformed file.
    #[must_use]
    pub fn resolve(path: Option<&Path>) -> Self {
        let mut policy = match path {
            Some(p) => match Self::load(p) {
                Ok(policy) => policy,
                Err(e) => {
                    tracing::error!(
                        path = %p.display(),
                        error = %e,
                        "mesh authority file is unreadable — failing closed (enforce, no grants)"
                    );
                    Self::enforce()
                }
            },
            None => Self::enforce(),
        };
        apply_env_mode(&mut policy);
        policy
    }

    /// Load and validate a policy file.
    ///
    /// # Errors
    /// Returns a human-readable reason when the file cannot be read or
    /// parsed.
    pub fn load(path: &Path) -> Result<Self, String> {
        let text =
            std::fs::read_to_string(path).map_err(|e| format!("read {}: {e}", path.display()))?;
        serde_json::from_str(&text).map_err(|e| format!("parse {}: {e}", path.display()))
    }

    /// Whether the policy is in advisory (legacy) mode.
    #[must_use]
    pub const fn is_advisory(&self) -> bool {
        matches!(self.mode, AuthorityMode::Advisory)
    }

    /// Number of operator grants.
    #[must_use]
    pub fn grant_count(&self) -> usize {
        self.grants.len()
    }

    /// Provision (or replace) a grant.
    pub fn grant(&mut self, peer_id: impl Into<String>, grant: AuthorityGrant) {
        self.grants.insert(peer_id.into(), grant);
    }

    /// Revoke a grant. Returns whether one existed.
    pub fn revoke(&mut self, peer_id: &str) -> bool {
        self.grants.remove(peer_id).is_some()
    }

    /// The authority this node will enforce for `peer_id`/`bound_key`,
    /// given what the peer declared about itself.
    ///
    /// A grant with a `public_key` pin applies only while the bound key
    /// matches; a pinless grant follows the TOFU binding.
    #[must_use]
    pub fn authority_for(
        &self,
        peer_id: &str,
        bound_key: &str,
        declared: &PeerAuthority,
    ) -> EffectiveAuthority {
        if let Some(grant) = self.grants.get(peer_id) {
            let pinned = grant
                .public_key
                .as_deref()
                .is_some_and(|key| key == bound_key);
            let unpinned = grant.public_key.is_none();
            if pinned || unpinned {
                return EffectiveAuthority {
                    authority: grant.authority.clone(),
                    source: AuthoritySource::Provisioned,
                };
            }
        }
        match self.mode {
            AuthorityMode::Advisory => EffectiveAuthority {
                authority: declared.clone(),
                source: AuthoritySource::AdvisoryDeclared,
            },
            AuthorityMode::Enforce => EffectiveAuthority {
                authority: PeerAuthority::none(),
                source: AuthoritySource::DefaultDenied,
            },
        }
    }

    /// Compact status disclosure (mode + grant count + granted peer IDs).
    #[must_use]
    pub fn status_summary(&self) -> serde_json::Value {
        serde_json::json!({
            "mode": self.mode.as_str(),
            "grants": self.grant_count(),
            "granted_peers": self.grants.keys().collect::<Vec<_>>(),
        })
    }
}

/// Apply `WM_MESH_AUTHORITY` over the file/default mode. An unrecognized
/// value is loud and leaves the mode unchanged (never silently advisory).
fn apply_env_mode(policy: &mut MeshAuthorityPolicy) {
    let Some(raw) = std::env::var(ENV_MESH_AUTHORITY).ok() else {
        return;
    };
    if let Some(mode) = AuthorityMode::parse(&raw) {
        policy.mode = mode;
    } else {
        tracing::error!(
            value = %raw,
            "WM_MESH_AUTHORITY must be 'enforce' or 'advisory' — keeping {}",
            policy.mode.as_str()
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn writable(_peer: &str) -> AuthorityGrant {
        AuthorityGrant {
            public_key: None,
            authority: PeerAuthority {
                can_execute: true,
                can_write_memory: true,
                ..PeerAuthority::none()
            },
        }
    }

    #[test]
    fn default_mode_is_enforce_and_denies_unknown_peers() {
        let policy = MeshAuthorityPolicy::enforce();
        let effective = policy.authority_for("someone", "ab12", &PeerAuthority::full());
        assert_eq!(effective.source, AuthoritySource::DefaultDenied);
        assert!(!effective.authority.can_execute);
        assert!(!effective.authority.can_write_memory);
        assert!(!effective.authority.can_delegate);
    }

    #[test]
    fn advisory_honors_declared_authority() {
        let policy = MeshAuthorityPolicy::advisory();
        let effective = policy.authority_for("someone", "ab12", &PeerAuthority::read_only());
        assert_eq!(effective.source, AuthoritySource::AdvisoryDeclared);
        assert!(effective.authority.can_execute);
        assert!(!effective.authority.can_write_memory);
    }

    #[test]
    fn grant_applies_and_survives_pinless_tofu() {
        let mut policy = MeshAuthorityPolicy::enforce();
        policy.grant("peer-a", writable("peer-a"));
        let effective = policy.authority_for("peer-a", "any-bound-key", &PeerAuthority::none());
        assert_eq!(effective.source, AuthoritySource::Provisioned);
        assert!(effective.authority.can_execute);
        assert!(effective.authority.can_write_memory);
    }

    #[test]
    fn pinned_grant_requires_the_matching_bound_key() {
        let mut policy = MeshAuthorityPolicy::enforce();
        let mut grant = writable("peer-a");
        grant.public_key = Some("aaaa".into());
        policy.grant("peer-a", grant);

        let matching = policy.authority_for("peer-a", "aaaa", &PeerAuthority::read_only());
        assert_eq!(matching.source, AuthoritySource::Provisioned);

        let mismatched = policy.authority_for("peer-a", "bbbb", &PeerAuthority::read_only());
        assert_eq!(mismatched.source, AuthoritySource::DefaultDenied);
        assert!(!mismatched.authority.can_execute);
    }

    #[test]
    fn revoke_removes_the_grant() {
        let mut policy = MeshAuthorityPolicy::enforce();
        policy.grant("peer-a", writable("peer-a"));
        assert_eq!(policy.grant_count(), 1);
        assert!(policy.revoke("peer-a"));
        assert!(!policy.revoke("peer-a"));
        let effective = policy.authority_for("peer-a", "k", &PeerAuthority::full());
        assert_eq!(effective.source, AuthoritySource::DefaultDenied);
    }

    #[test]
    fn load_parses_the_documented_file_shape() {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join("mesh_authority.json");
        std::fs::write(
            &path,
            r#"{
                "mode": "advisory",
                "grants": {
                    "wm-abc": {
                        "public_key": "deadbeef",
                        "can_execute": true,
                        "can_write_memory": false,
                        "can_delegate": false
                    }
                }
            }"#,
        )
        .expect("write");
        let policy = MeshAuthorityPolicy::load(&path).expect("load");
        assert_eq!(policy.mode, AuthorityMode::Advisory);
        let effective = policy.authority_for("wm-abc", "deadbeef", &PeerAuthority::none());
        assert!(effective.authority.can_execute);
        assert!(!effective.authority.can_write_memory);
    }

    #[test]
    fn malformed_file_fails_closed() {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join("mesh_authority.json");
        std::fs::write(&path, "{ not json").expect("write");
        assert!(MeshAuthorityPolicy::load(&path).is_err());
        let policy = MeshAuthorityPolicy::resolve(Some(&path));
        assert_eq!(policy.mode, AuthorityMode::Enforce);
        assert_eq!(policy.grant_count(), 0);
    }

    #[test]
    fn missing_file_resolves_to_enforce() {
        let dir = tempfile::tempdir().expect("tempdir");
        let policy = MeshAuthorityPolicy::resolve(Some(&dir.path().join("absent.json")));
        assert_eq!(policy.mode, AuthorityMode::Enforce);
        assert_eq!(policy.grant_count(), 0);
    }

    #[test]
    fn mode_parse_is_strict() {
        assert_eq!(
            AuthorityMode::parse("enforce"),
            Some(AuthorityMode::Enforce)
        );
        assert_eq!(
            AuthorityMode::parse("advisory"),
            Some(AuthorityMode::Advisory)
        );
        assert_eq!(AuthorityMode::parse("Advisory"), None);
        assert_eq!(AuthorityMode::parse("0"), None);
        assert_eq!(AuthorityMode::parse(""), None);
    }
}
