//! Mandala gate-lite pass verification (S2).
//!
//! Gate-lite issues passes as a compact JWS-like token: three base64url
//! segments (`header.payload.signature`), Ed25519 (`alg: EdDSA`), `kid` = the
//! gate's `did:key`. The signature covers
//! `b64u(canon(header)) + "." + b64u(canon(claims))` with the same JCS subset
//! the continuity-receipt crate implements — so verification is offline and
//! byte-exact against `MANDALA_OS/gate-lite/gate_lite/tokens.py`.
//!
//! WM treats the pass as *authority evidence*: it verifies integrity and the
//! claims it can check locally (issuer key, expiry, audience, class, policy
//! version), records the token commitment in the receipt, and does not claim
//! gate-lite registry state it cannot see (replay/slot binding — see the S2
//! scope's Mandala-side requests).

use base64::Engine as _;
use serde_json::Value;

use crate::emit::content_digest;
use crate::error::ReceiptError;

/// Default accepted gate-lite policy versions.
pub const DEFAULT_POLICY_VERSIONS: [&str; 1] = ["2026-09-17.1"];

/// Gate-lite slot quotas carried by a pass.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PassQuotas {
    /// CPU budget (milliseconds).
    pub cpu_ms: u64,
    /// Memory cap (MiB).
    pub mem_mb: u64,
    /// Disk cap (MiB).
    pub disk_mb: u64,
    /// Wall-clock budget (milliseconds).
    pub wall_ms: u64,
}

/// Optional spend budget carried by a pass.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PassBudget {
    /// Amount in minor units.
    pub minor: u64,
    /// ISO-4217-like currency code.
    pub currency: String,
}

/// Verified gate-lite pass claims plus the raw-token commitment.
#[derive(Debug, Clone)]
pub struct PassClaims {
    /// `iss` (`gate:<gate_id>`).
    pub issuer: String,
    /// `sub` (agent `did:key`).
    pub subject: String,
    /// `aud` (expected `gate-lite`).
    pub audience: String,
    /// `mandala.class`.
    pub gate_class: String,
    /// `mandala.slot_class`.
    pub slot_class: String,
    /// `mandala.quotas`.
    pub quotas: PassQuotas,
    /// `budget` when present.
    pub budget: Option<PassBudget>,
    /// `policy_version`.
    pub policy_version: String,
    /// `exp` (epoch seconds).
    pub expires_at: i64,
    /// `jti`.
    pub jti: String,
    /// `sha256:` of the raw token string — the pass binding recorded in the
    /// receipt (`pass_token_id` slot until Mandala emits its own id).
    pub token_digest: String,
    /// The gate's `did:key` (token `kid`).
    pub gate_did: String,
}

impl PassClaims {
    /// `expires_at` as RFC 3339 UTC.
    #[must_use]
    pub fn expires_at_rfc3339(&self) -> String {
        chrono::DateTime::from_timestamp(self.expires_at, 0).map_or_else(
            || self.expires_at.to_string(),
            |time| time.to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
        )
    }
}

/// Pass verification failure.
#[derive(Debug, thiserror::Error)]
pub enum PassError {
    /// Token is not a well-formed three-segment token with the expected claims.
    #[error("malformed pass: {0}")]
    Malformed(String),
    /// Signature does not verify against the `kid` public key.
    #[error("pass signature does not verify")]
    BadSignature,
    /// `kid` does not match the expected gate.
    #[error("pass issued by a different gate (kid {kid})")]
    WrongIssuer {
        /// The unexpected key id.
        kid: String,
    },
    /// Token expired.
    #[error("pass expired at {expires_at}")]
    Expired {
        /// Expiry (epoch seconds).
        expires_at: i64,
    },
    /// Audience is not gate-lite.
    #[error("pass audience {audience:?} is not gate-lite")]
    WrongAudience {
        /// The unexpected audience.
        audience: String,
    },
    /// Governance class is not gate-lite.
    #[error("pass class {class:?} is not gate-lite")]
    WrongClass {
        /// The unexpected class.
        class: String,
    },
    /// Policy version is not accepted.
    #[error("pass policy version {version:?} is not accepted")]
    PolicyVersion {
        /// The unexpected version.
        version: String,
    },
    /// `sub` is missing or empty.
    #[error("pass subject is empty")]
    EmptySubject,
}

/// Verification options: expected gate (optional pin), accepted policy
/// versions, and the verification time (epoch seconds — injectable for tests).
pub struct PassVerifyOptions<'a> {
    /// When set, `kid` must equal this gate `did:key`.
    pub expected_issuer: Option<&'a str>,
    /// Accepted `policy_version` values.
    pub accepted_policy_versions: &'a [&'a str],
    /// Current time in epoch seconds.
    pub now: i64,
}

fn malformed(detail: impl Into<String>) -> PassError {
    PassError::Malformed(detail.into())
}

fn string_field<'a>(claims: &'a Value, name: &str) -> std::result::Result<&'a str, PassError> {
    claims
        .get(name)
        .and_then(Value::as_str)
        .ok_or_else(|| malformed(format!("missing string claim {name:?}")))
}

fn u64_field(value: &Value, name: &str) -> std::result::Result<u64, PassError> {
    value
        .get(name)
        .and_then(Value::as_u64)
        .ok_or_else(|| malformed(format!("missing integer field {name:?}")))
}

/// Verify a gate-lite pass token offline.
///
/// Mirrors `gate_lite/tokens.py:22-38` (signature, `kid`, expiry) plus the
/// claims checks WM needs: `aud`, `mandala.class`, `policy_version`, subject.
pub fn verify_pass(
    token: &str,
    options: &PassVerifyOptions<'_>,
) -> std::result::Result<PassClaims, PassError> {
    let token = token.trim();
    let parts: Vec<&str> = token.split('.').collect();
    if parts.len() != 3 || parts.iter().any(|part| part.is_empty()) {
        return Err(malformed("expected three non-empty segments"));
    }
    let decode = |part: &str| -> std::result::Result<Value, PassError> {
        let bytes = base64::engine::general_purpose::URL_SAFE_NO_PAD
            .decode(part)
            .map_err(|error| malformed(format!("base64url decode failed: {error}")))?;
        serde_json::from_slice(&bytes)
            .map_err(|error| malformed(format!("segment is not JSON: {error}")))
    };
    let header = decode(parts[0])?;
    let claims = decode(parts[1])?;

    let alg = header
        .get("alg")
        .and_then(Value::as_str)
        .unwrap_or_default();
    if alg != "EdDSA" {
        return Err(malformed(format!("unsupported alg {alg:?}")));
    }
    let kid = header
        .get("kid")
        .and_then(Value::as_str)
        .ok_or_else(|| malformed("header has no kid"))?;
    if let Some(expected) = options.expected_issuer {
        if kid != expected {
            return Err(PassError::WrongIssuer {
                kid: kid.to_string(),
            });
        }
    }

    // Signature covers b64u(canon(header)) + "." + b64u(canon(claims)).
    let canon_header = continuity_receipt::canon::canonical_bytes(&header)
        .map_err(|error| malformed(format!("header canonicalization failed: {error}")))?;
    let canon_claims = continuity_receipt::canon::canonical_bytes(&claims)
        .map_err(|error| malformed(format!("claims canonicalization failed: {error}")))?;
    let signing_input = format!(
        "{}.{}",
        base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(canon_header),
        base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(canon_claims)
    );
    if !continuity_receipt::didkey::verify(kid, signing_input.as_bytes(), parts[2]) {
        return Err(PassError::BadSignature);
    }

    let issuer = string_field(&claims, "iss")?.to_string();
    let subject = string_field(&claims, "sub")?.to_string();
    if subject.trim().is_empty() {
        return Err(PassError::EmptySubject);
    }
    let audience = string_field(&claims, "aud")?.to_string();
    if audience != "gate-lite" {
        return Err(PassError::WrongAudience { audience });
    }
    let mandala = claims
        .get("mandala")
        .ok_or_else(|| malformed("missing mandala claim"))?;
    let gate_class = string_field(mandala, "class")?.to_string();
    if gate_class != "gate-lite" {
        return Err(PassError::WrongClass { class: gate_class });
    }
    let slot_class = string_field(mandala, "slot_class")?.to_string();
    let quotas_value = mandala
        .get("quotas")
        .ok_or_else(|| malformed("missing mandala.quotas"))?;
    let quotas = PassQuotas {
        cpu_ms: u64_field(quotas_value, "cpu_ms")?,
        mem_mb: u64_field(quotas_value, "mem_mb")?,
        disk_mb: u64_field(quotas_value, "disk_mb")?,
        wall_ms: u64_field(quotas_value, "wall_ms")?,
    };
    let budget = match claims.get("budget") {
        None | Some(Value::Null) => None,
        Some(value) => Some(PassBudget {
            minor: u64_field(value, "minor")?,
            currency: string_field(value, "currency")?.to_string(),
        }),
    };
    let policy_version = string_field(&claims, "policy_version")?.to_string();
    if !options
        .accepted_policy_versions
        .iter()
        .any(|accepted| *accepted == policy_version)
    {
        return Err(PassError::PolicyVersion {
            version: policy_version,
        });
    }
    let expires_at = claims
        .get("exp")
        .and_then(Value::as_i64)
        .ok_or_else(|| malformed("missing exp claim"))?;
    if expires_at < options.now {
        return Err(PassError::Expired { expires_at });
    }
    let jti = claims
        .get("jti")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_string();

    Ok(PassClaims {
        issuer,
        subject,
        audience,
        gate_class,
        slot_class,
        quotas,
        budget,
        policy_version,
        expires_at,
        jti,
        token_digest: content_digest(token),
        gate_did: kid.to_string(),
    })
}

impl From<PassError> for ReceiptError {
    fn from(error: PassError) -> Self {
        Self::InvalidArgs(error.to_string())
    }
}

/// Result alias for pass operations.
pub type PassResult<T> = std::result::Result<T, PassError>;

#[cfg(test)]
mod tests {
    use super::*;

    /// A real gate-lite-issued token (deterministic fixture key
    /// `sha256("continuity-receipt/wm-s2-fixture")`, offline issuance; verified
    /// by gate-lite's own `tokens.verify_pass` at generation time).
    const FIXTURE_TOKEN: &str = "eyJhbGciOiJFZERTQSIsImtpZCI6ImRpZDprZXk6ejZNa2puU1ExbjlMZzlHR3NxdVlBeDhiS3hCMkVCM0ZuRTJTeWtyVHpUcXVDV3M2IiwidHlwIjoiSldUIn0.eyJhdWQiOiJnYXRlLWxpdGUiLCJidWRnZXQiOnsiY3VycmVuY3kiOiJVU0QiLCJtaW5vciI6MTAwMH0sImV4cCI6NDEwMjQ0NDgwMCwiaXNzIjoiZ2F0ZTpnYXRlLWxpdGUtMSIsImp0aSI6IjAxOTlhMGMwLTAwMDAtNzAwMC04MDAwLTAwMDAwMDAwZjE3YSIsIm1hbmRhbGEiOnsiY2xhc3MiOiJnYXRlLWxpdGUiLCJxdW90YXMiOnsiY3B1X21zIjozMDAwMDAsImRpc2tfbWIiOjUxMiwibWVtX21iIjoxMDI0LCJ3YWxsX21zIjo1NDAwMDAwfSwic2xvdF9jbGFzcyI6InNtYWxsIn0sInBvbGljeV92ZXJzaW9uIjoiMjAyNi0wOS0xNy4xIiwic3ViIjoiZGlkOmtleTp6Nk1rakFWbzl5MXJLNVg4a01IM0p1MnBqWkVaODRBNXFYOVh5TnI3U3Z4cWR6NHcifQ.07rDlytb7T2HFP6MRs_7OvAE5E5eTCEbChVam9YAk_3wVTCvCXBzXksrtqA30muxmxiPvrVMaZRyDv7U6mDMAw";
    const FIXTURE_GATE_DID: &str = "did:key:z6MkjnSQ1n9Lg9GGsquYAx8bKxB2EB3FnE2SykrTzTquCWs6";
    const FIXTURE_SUBJECT: &str = "did:key:z6MkjAVo9y1rK5X8kMH3Ju2pjZEZ84A5qX9XyNr7Svxqdz4w";

    fn options<'a>(
        expected: Option<&'a str>,
        versions: &'a [&'a str],
        now: i64,
    ) -> PassVerifyOptions<'a> {
        PassVerifyOptions {
            expected_issuer: expected,
            accepted_policy_versions: versions,
            now,
        }
    }

    #[test]
    fn verifies_a_real_gate_lite_token() {
        let claims = verify_pass(
            FIXTURE_TOKEN,
            &options(
                Some(FIXTURE_GATE_DID),
                &DEFAULT_POLICY_VERSIONS,
                1_700_000_000,
            ),
        )
        .expect("fixture verifies");
        assert_eq!(claims.issuer, "gate:gate-lite-1");
        assert_eq!(claims.subject, FIXTURE_SUBJECT);
        assert_eq!(claims.audience, "gate-lite");
        assert_eq!(claims.gate_class, "gate-lite");
        assert_eq!(claims.slot_class, "small");
        assert_eq!(
            claims.quotas,
            PassQuotas {
                cpu_ms: 300_000,
                mem_mb: 1024,
                disk_mb: 512,
                wall_ms: 5_400_000
            }
        );
        assert_eq!(
            claims.budget,
            Some(PassBudget {
                minor: 1000,
                currency: "USD".into()
            })
        );
        assert_eq!(claims.policy_version, "2026-09-17.1");
        assert_eq!(claims.expires_at, 4_102_444_800);
        assert_eq!(claims.gate_did, FIXTURE_GATE_DID);
        assert!(claims.token_digest.starts_with("sha256:"));
        assert_eq!(claims.expires_at_rfc3339(), "2100-01-01T00:00:00Z");
    }

    #[test]
    fn rejects_a_tampered_token() {
        let mut parts: Vec<&str> = FIXTURE_TOKEN.split('.').collect();
        // Swap in a different (valid base64url) payload: signature must fail.
        let other = base64::engine::general_purpose::URL_SAFE_NO_PAD
            .encode(br#"{"iss":"gate:evil","sub":"did:key:z1","aud":"gate-lite","mandala":{"class":"gate-lite","slot_class":"small","quotas":{"cpu_ms":1,"mem_mb":1,"disk_mb":1,"wall_ms":1}},"policy_version":"2026-09-17.1","exp":4102444800,"jti":"x"}"#);
        parts[1] = &other;
        let tampered = parts.join(".");
        let error = verify_pass(
            &tampered,
            &options(None, &DEFAULT_POLICY_VERSIONS, 1_700_000_000),
        )
        .expect_err("must reject");
        assert!(matches!(error, PassError::BadSignature), "{error}");
    }

    #[test]
    fn rejects_expired_wrong_gate_and_wrong_policy() {
        let error = verify_pass(
            FIXTURE_TOKEN,
            &options(None, &DEFAULT_POLICY_VERSIONS, 4_102_444_801),
        )
        .expect_err("expired");
        assert!(matches!(error, PassError::Expired { .. }), "{error}");

        let error = verify_pass(
            FIXTURE_TOKEN,
            &options(
                Some("did:key:z6Mkother"),
                &DEFAULT_POLICY_VERSIONS,
                1_700_000_000,
            ),
        )
        .expect_err("wrong gate");
        assert!(matches!(error, PassError::WrongIssuer { .. }), "{error}");

        let error = verify_pass(
            FIXTURE_TOKEN,
            &options(Some(FIXTURE_GATE_DID), &["0.0"], 1_700_000_000),
        )
        .expect_err("policy");
        assert!(matches!(error, PassError::PolicyVersion { .. }), "{error}");
    }

    #[test]
    fn rejects_malformed_tokens() {
        let error = verify_pass(
            "not-a-token",
            &options(None, &DEFAULT_POLICY_VERSIONS, 1_700_000_000),
        )
        .expect_err("malformed");
        assert!(matches!(error, PassError::Malformed(_)), "{error}");
    }
}
