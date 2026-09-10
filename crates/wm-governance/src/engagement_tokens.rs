//! Engagement tokens — signed scope-of-engagement authorizations.
//!
//! Rust port of the Python `whitemagic/security/engagement_tokens.py`
//! (Edgerunner Violet security layer): cryptographic certificates that
//! authorize time-bounded, scope-limited offensive-security actions
//! (PoC pipeline / red-team engagements). No red-ops action may proceed
//! without a valid, unexpired, unrevoked token bound to the exact
//! rules-of-engagement text it was issued against.
//!
//! Semantics ported from the Python original:
//! - issuance binds the token fields cryptographically (Python: HMAC-SHA256
//!   over canonical JSON; here: Ed25519 over canonical JSON — asymmetric,
//!   so validators only need the issuer public key)
//! - validation order: signature → revocation → expiry → ROE-hash match
//!   (Python: hash check → revoked → expired → scope)
//! - revocation mutates state *after* issuance and is therefore outside the
//!   signed payload (Python mutates `revoked` on the stored token the same way)
//! - optional expiry (`expires_at: None` = engagement runs until revoked)
//! - nonce: fresh unpredictable value per token, replay-hardens re-issued
//!   authorizations that share the same ROE + scope
//!
//! Canonical serialization (byte-deterministic, `gratitude_ledger` style):
//! the signature input is `serde_json::to_string` of a fixed-field projection
//! struct — field order == declaration order, compact (no spaces), enum
//! variants serialize as `"Poc"` / `"Redteam"` / `"Demo"` / `{"Custom":"..."}`
//! and `expires_at` as an integer or `null`:
//!
//! ```json
//! {"id":"evt_…","issued_to":"…","scope":"Redteam","rules_of_engagement_hash":"…","nonce":"…","issued_at":1700000000,"expires_at":1700003600}
//! ```
//!
//! The `revoked` flag and the `signature` itself are excluded (state change
//! and output, not input). Pure logic — no store, no network.

#![forbid(unsafe_code)]

use std::collections::BTreeSet;

use chrono::Utc;
use getrandom::SysRng;
use serde::{Deserialize, Serialize};
use sha2::{Digest as _, Sha256};

use crate::network_profile::AgentKeypair;

/// SHA-256 hex digest of a string (`karma_ledger` helper style) — the
/// caller hashes the rules-of-engagement text with this before issuance,
/// so tokens never store the ROE prose itself.
#[must_use]
pub fn sha256_hex(input: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(input.as_bytes());
    hex_encode(&hasher.finalize())
}

/// Engagement scope — what class of action the token authorizes.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum EngagementScope {
    /// Proof-of-concept pipeline (reproducible, defensive-oriented work).
    Poc,
    /// Red-team engagement (offensive security exercise).
    Redteam,
    /// Demonstration only — no live targets.
    Demo,
    /// Custom engagement class with a free-form label.
    Custom(String),
}

impl EngagementScope {
    /// Stable lowercase label for logs / verdict reasons.
    #[must_use]
    pub fn label(&self) -> &str {
        match self {
            Self::Poc => "poc",
            Self::Redteam => "redteam",
            Self::Demo => "demo",
            Self::Custom(name) => name,
        }
    }
}

/// A signed, time-bounded, scope-limited authorization for engagement
/// actions.
///
/// Every field except `revoked` and `signature` is covered by the Ed25519
/// signature over the canonical payload (see module docs): mutating any
/// signed field invalidates the token.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EngagementToken {
    /// Token id (`evt_` + 24 random hex chars, Python `evt_` prefix parity).
    pub id: String,
    /// Agent the token was issued to.
    pub issued_to: String,
    /// Engagement class authorized.
    pub scope: EngagementScope,
    /// SHA-256 hex of the rules-of-engagement text this token is bound to.
    pub rules_of_engagement_hash: String,
    /// Fresh random hex nonce (replay hardening across re-issues).
    pub nonce: String,
    /// Unix epoch seconds of issuance.
    pub issued_at: i64,
    /// Unix epoch seconds of expiry, or `None` for revocation-only lifetime.
    pub expires_at: Option<i64>,
    /// Revocation flag — mutable after issuance, outside the signature.
    pub revoked: bool,
    /// Ed25519 signature (hex) over the canonical token payload.
    pub signature: String,
}

/// Canonical signed projection of a token — fixed field order for
/// byte-deterministic serialization. `revoked` and `signature` are
/// excluded (state change and output, not input).
#[derive(Serialize)]
struct TokenPayload<'a> {
    id: &'a str,
    issued_to: &'a str,
    scope: &'a EngagementScope,
    rules_of_engagement_hash: &'a str,
    nonce: &'a str,
    issued_at: i64,
    expires_at: Option<i64>,
}

/// Outcome of validating an engagement token.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TokenVerdict {
    /// Signature, revocation, expiry, and ROE binding all check out.
    Valid,
    /// Signature does not verify against the issuer key (or a signed field
    /// was tampered with).
    BadSignature,
    /// Token is revoked (flag on the token itself, or in the issuer's
    /// revocation set).
    Revoked,
    /// Token expiry has passed (`now > expires_at`).
    Expired,
    /// The presented rules-of-engagement hash does not match the one the
    /// token was issued against.
    RulesOfEngagementMismatch {
        /// ROE hash bound into the token at issuance.
        expected: String,
        /// ROE hash presented for validation.
        actual: String,
    },
}

/// Errors from issuer-side operations.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum EngagementTokenError {
    /// The issuer never issued a token with this id.
    #[error("unknown engagement token id: {id}")]
    UnknownToken {
        /// The unrecognized token id.
        id: String,
    },
    /// The token's signature field is not 64 hex chars (128 hex digits).
    #[error("engagement token signature field is malformed (expected 128 hex chars)")]
    MalformedSignature,
}

/// Issues and validates engagement tokens, holding the Ed25519 issuer
/// keypair and the revocation set. Pure logic — persistence is the
/// caller's job.
pub struct EngagementIssuer {
    keypair: AgentKeypair,
    issued: BTreeSet<String>,
    revoked: BTreeSet<String>,
}

impl std::fmt::Debug for EngagementIssuer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("EngagementIssuer")
            .field("public_key", &self.keypair.public_key_hex())
            .field("issued", &self.issued.len())
            .field("revoked", &self.revoked.len())
            .finish()
    }
}

impl EngagementIssuer {
    /// Create an issuer with a fresh OS-entropy keypair.
    #[must_use]
    pub fn new() -> Self {
        Self {
            keypair: AgentKeypair::generate(),
            issued: BTreeSet::new(),
            revoked: BTreeSet::new(),
        }
    }

    /// Create an issuer from an explicit keypair (deterministic tests,
    /// restored issuer identities).
    #[must_use]
    pub const fn with_keypair(keypair: AgentKeypair) -> Self {
        Self {
            keypair,
            issued: BTreeSet::new(),
            revoked: BTreeSet::new(),
        }
    }

    /// The issuer's Ed25519 public key (hex) — publish this so validators
    /// that do not hold the keypair can still pin the issuer identity.
    #[must_use]
    pub fn signer_public_key_hex(&self) -> String {
        self.keypair.public_key_hex()
    }

    /// Issue a token for `issued_to` bound to the given scope and
    /// rules-of-engagement hash.
    ///
    /// `ttl_seconds = None` means the token never expires (revocation-only
    /// lifetime, matching the Python `max_uses = 0`-style "unbounded"
    /// convention).
    pub fn issue(
        &mut self,
        issued_to: &str,
        scope: EngagementScope,
        rules_of_engagement_hash: &str,
        ttl_seconds: Option<i64>,
    ) -> EngagementToken {
        let issued_at = Utc::now().timestamp();
        let token = EngagementToken {
            id: format!("evt_{}", random_hex(12)),
            issued_to: issued_to.to_owned(),
            scope,
            rules_of_engagement_hash: rules_of_engagement_hash.to_ascii_lowercase(),
            nonce: random_hex(16),
            issued_at,
            expires_at: ttl_seconds.map(|ttl| issued_at + ttl),
            revoked: false,
            signature: String::new(),
        };
        let signature = self.keypair.sign_hex(canonical_payload(&token).as_bytes());
        self.issued.insert(token.id.clone());
        EngagementToken { signature, ..token }
    }

    /// Validate a token against the current wall clock and the
    /// rules-of-engagement hash in force.
    ///
    /// Checks, in Python-parity order: signature → revocation → expiry →
    /// ROE-hash match. A `malformed` verdict reason surfaces as
    /// [`EngagementTokenError`]; every policy outcome is a
    /// [`TokenVerdict`].
    ///
    /// # Errors
    ///
    /// [`EngagementTokenError::MalformedSignature`] when the signature
    /// field is not 128 hex chars.
    pub fn validate(
        &self,
        token: &EngagementToken,
        rules_of_engagement_hash: &str,
    ) -> Result<TokenVerdict, EngagementTokenError> {
        self.validate_at(token, rules_of_engagement_hash, Utc::now().timestamp())
    }

    /// [`Self::validate`] at an explicit timestamp (testable expiry).
    ///
    /// # Errors
    ///
    /// [`EngagementTokenError::MalformedSignature`] when the signature
    /// field is not 128 hex chars.
    pub fn validate_at(
        &self,
        token: &EngagementToken,
        rules_of_engagement_hash: &str,
        now: i64,
    ) -> Result<TokenVerdict, EngagementTokenError> {
        if !is_hex_str(&token.signature, 128) {
            return Err(EngagementTokenError::MalformedSignature);
        }
        if !crate::network_profile::verify_signature(
            &self.keypair.public_key_hex(),
            canonical_payload(token).as_bytes(),
            &token.signature,
        ) {
            return Ok(TokenVerdict::BadSignature);
        }
        if token.revoked || self.revoked.contains(&token.id) {
            return Ok(TokenVerdict::Revoked);
        }
        if token.expires_at.is_some_and(|expires_at| now > expires_at) {
            return Ok(TokenVerdict::Expired);
        }
        let expected = token.rules_of_engagement_hash.to_ascii_lowercase();
        let actual = rules_of_engagement_hash.trim().to_ascii_lowercase();
        if expected != actual {
            return Ok(TokenVerdict::RulesOfEngagementMismatch { expected, actual });
        }
        Ok(TokenVerdict::Valid)
    }

    /// Revoke a previously issued token — takes effect immediately, even
    /// for tokens whose `revoked` flag was not flipped on the copy held by
    /// the caller.
    ///
    /// # Errors
    ///
    /// [`EngagementTokenError::UnknownToken`] when the id was never issued
    /// by this issuer.
    pub fn revoke(&mut self, id: &str) -> Result<(), EngagementTokenError> {
        if !self.issued.contains(id) {
            return Err(EngagementTokenError::UnknownToken { id: id.to_owned() });
        }
        self.revoked.insert(id.to_owned());
        Ok(())
    }
}

impl Default for EngagementIssuer {
    fn default() -> Self {
        Self::new()
    }
}

/// Canonical signed payload for a token (module docs document the exact
/// wire format).
fn canonical_payload(token: &EngagementToken) -> String {
    serde_json::to_string(&TokenPayload {
        id: &token.id,
        issued_to: &token.issued_to,
        scope: &token.scope,
        rules_of_engagement_hash: &token.rules_of_engagement_hash,
        nonce: &token.nonce,
        issued_at: token.issued_at,
        expires_at: token.expires_at,
    })
    .unwrap_or_default()
}

fn hex_encode(bytes: &[u8]) -> String {
    use std::fmt::Write as _;
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        let _ = write!(out, "{b:02x}");
    }
    out
}

fn random_hex(n_bytes: usize) -> String {
    use getrandom::rand_core::{Rng, UnwrapErr};
    let mut buf = vec![0u8; n_bytes];
    UnwrapErr(SysRng).fill_bytes(&mut buf);
    hex_encode(&buf)
}

fn is_hex_str(s: &str, expected_len: usize) -> bool {
    s.len() == expected_len && s.bytes().all(|b| b.is_ascii_hexdigit())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn issuer() -> EngagementIssuer {
        EngagementIssuer::with_keypair(AgentKeypair::from_seed([42u8; 32]))
    }

    fn roe_hash(text: &str) -> String {
        sha256_hex(text)
    }

    #[test]
    fn issue_validate_roundtrip() {
        let mut issuer = issuer();
        let token = issuer.issue(
            "agent-7",
            EngagementScope::Redteam,
            &roe_hash("roe: no exfiltration"),
            Some(3600),
        );
        assert!(token.id.starts_with("evt_"));
        assert_eq!(token.signature.len(), 128);
        assert_eq!(
            issuer
                .validate(&token, &roe_hash("roe: no exfiltration"))
                .expect("well-formed"),
            TokenVerdict::Valid
        );
    }

    #[test]
    fn no_expiry_token_never_expires() {
        let mut issuer = issuer();
        let token = issuer.issue("agent-7", EngagementScope::Poc, &roe_hash("roe"), None);
        assert_eq!(token.expires_at, None);
        assert_eq!(
            issuer
                .validate_at(&token, &roe_hash("roe"), token.issued_at + 100_000)
                .expect("well-formed"),
            TokenVerdict::Valid
        );
    }

    #[test]
    fn tampered_field_fails_signature() {
        let mut issuer = issuer();
        let mut token = issuer.issue("agent-7", EngagementScope::Demo, &roe_hash("roe"), Some(60));
        token.scope = EngagementScope::Redteam;
        assert_eq!(
            issuer
                .validate(&token, &roe_hash("roe"))
                .expect("well-formed"),
            TokenVerdict::BadSignature
        );
    }

    #[test]
    fn tampered_issued_to_fails_signature() {
        let mut issuer = issuer();
        let mut token = issuer.issue("agent-7", EngagementScope::Poc, &roe_hash("roe"), Some(60));
        token.issued_to = "agent-8".to_owned();
        assert_eq!(
            issuer
                .validate(&token, &roe_hash("roe"))
                .expect("well-formed"),
            TokenVerdict::BadSignature
        );
    }

    #[test]
    fn expired_fails() {
        let mut issuer = issuer();
        let token = issuer.issue("agent-7", EngagementScope::Poc, &roe_hash("roe"), Some(60));
        assert_eq!(
            issuer
                .validate_at(&token, &roe_hash("roe"), token.issued_at + 61)
                .expect("well-formed"),
            TokenVerdict::Expired
        );
        // Boundary: still valid exactly at expiry.
        assert_eq!(
            issuer
                .validate_at(
                    &token,
                    &roe_hash("roe"),
                    token.expires_at.unwrap_or_default()
                )
                .expect("well-formed"),
            TokenVerdict::Valid
        );
    }

    #[test]
    fn revoked_fails() {
        let mut issuer = issuer();
        let token = issuer.issue("agent-7", EngagementScope::Poc, &roe_hash("roe"), Some(60));
        issuer.revoke(&token.id).expect("issued");
        // Both revocation paths: issuer set and flipped flag.
        assert_eq!(
            issuer
                .validate(&token, &roe_hash("roe"))
                .expect("well-formed"),
            TokenVerdict::Revoked
        );
        let mut flagged = token.clone();
        flagged.revoked = true;
        assert_eq!(
            issuer
                .validate(&flagged, &roe_hash("roe"))
                .expect("well-formed"),
            TokenVerdict::Revoked
        );
    }

    #[test]
    fn roe_mismatch_fails() {
        let mut issuer = issuer();
        let token = issuer.issue(
            "agent-7",
            EngagementScope::Redteam,
            &roe_hash("roe v1"),
            Some(60),
        );
        match issuer
            .validate(&token, &roe_hash("roe v2"))
            .expect("well-formed")
        {
            TokenVerdict::RulesOfEngagementMismatch { expected, actual } => {
                assert_eq!(expected, roe_hash("roe v1"));
                assert_eq!(actual, roe_hash("roe v2"));
            }
            other => panic!("expected ROE mismatch, got {other:?}"),
        }
    }

    #[test]
    fn roe_hash_case_insensitive_match() {
        let mut issuer = issuer();
        let token = issuer.issue("agent-7", EngagementScope::Poc, &roe_hash("roe"), Some(60));
        let upper = roe_hash("roe").to_ascii_uppercase();
        assert_eq!(
            issuer.validate(&token, &upper).expect("well-formed"),
            TokenVerdict::Valid
        );
    }

    #[test]
    fn unknown_token_revocation_errors() {
        let mut issuer = issuer();
        assert_eq!(
            issuer.revoke("evt_does_not_exist"),
            Err(EngagementTokenError::UnknownToken {
                id: "evt_does_not_exist".to_owned()
            })
        );
    }

    #[test]
    fn malformed_signature_errors() {
        let mut issuer = issuer();
        let mut token = issuer.issue("agent-7", EngagementScope::Poc, &roe_hash("roe"), Some(60));
        token.signature = "zz".to_owned();
        assert_eq!(
            issuer.validate(&token, &roe_hash("roe")),
            Err(EngagementTokenError::MalformedSignature)
        );
    }

    #[test]
    fn other_issuer_key_rejects_token() {
        let mut issuer_a = EngagementIssuer::with_keypair(AgentKeypair::from_seed([1u8; 32]));
        let issuer_b = EngagementIssuer::with_keypair(AgentKeypair::from_seed([2u8; 32]));
        let token = issuer_a.issue("agent-7", EngagementScope::Poc, &roe_hash("roe"), Some(60));
        assert_eq!(
            issuer_b
                .validate(&token, &roe_hash("roe"))
                .expect("well-formed"),
            TokenVerdict::BadSignature
        );
    }

    #[test]
    fn canonical_payload_is_deterministic() {
        let mk = || EngagementToken {
            id: "evt_abc".to_owned(),
            issued_to: "agent-7".to_owned(),
            scope: EngagementScope::Custom("audit".to_owned()),
            rules_of_engagement_hash: roe_hash("roe"),
            nonce: "noncenonce".to_owned(),
            issued_at: 1_700_000_000,
            expires_at: Some(1_700_003_600),
            revoked: false,
            signature: String::new(),
        };
        let p1 = canonical_payload(&mk());
        let p2 = canonical_payload(&mk());
        assert_eq!(p1, p2);
        assert_eq!(
            p1,
            format!(
                r#"{{"id":"evt_abc","issued_to":"agent-7","scope":{{"Custom":"audit"}},"rules_of_engagement_hash":"{}","nonce":"noncenonce","issued_at":1700000000,"expires_at":1700003600}}"#,
                roe_hash("roe")
            )
        );
        // `revoked` and `signature` never leak into the payload.
        assert!(!p1.contains("revoked"));
        assert!(!p1.contains("signature"));
    }
}
