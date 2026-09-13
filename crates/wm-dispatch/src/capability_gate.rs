//! Dispatch-side capability authorization (PLAN_F F-1, dispatch half).
//!
//! Tools declare the capabilities they invoke (`EffectRow::invokes`, wm-core
//! vocabulary). This module maps that vocabulary onto the governance
//! [`CapabilitySet`] (wm-governance) and validates a presented engagement
//! credential before dispatch proceeds:
//!
//! - A credential presented under `args["_engagement"]`
//!   (`{ "token": <EngagementToken>, "issuer_public_key": "<hex>" }`) is
//!   **always** verified when present: Ed25519 signature → revocation →
//!   expiry → scope-derived capability coverage. A failing credential
//!   refuses the call in every mode — presented evidence must be valid.
//! - Without a credential, behavior depends on the gate mode:
//!   - [`CapabilityGateMode::Advisory`] (default): dispatch proceeds; the
//!     unmet requirement is logged at debug level for observability.
//!   - [`CapabilityGateMode::Strict`] (`WM_REQUIRE_CAPABILITIES=1`): tools
//!     whose `invokes` map to a non-empty capability set are refused with an
//!     actionable error.
//!
//! The credential key is removed from the args before execution, so tokens
//! never reach tool bodies, the write-audit digest, or the flight recorder.
//!
//! Scope note (v1): Ed25519 engagement tokens are the only verifiable
//! evidence path. `AdminGovernance`, `MemoryDelete`, and `SealAdapt` are not
//! grantable by any current [`EngagementScope`], so strict mode refuses
//! tools that declare them until a signed-grant path exists — that is the
//! intended conservative default, not a bug.

use serde::{Deserialize, Serialize};
use wm_core::{Capability as CoreCapability, EffectRow};
use wm_governance::capabilities::{
    Capability, CapabilitySet, assert_engagement_token_capabilities,
};
use wm_governance::engagement_tokens::EngagementToken;

/// Key under which a dispatch caller presents an engagement credential.
pub const ENGAGEMENT_KEY: &str = "_engagement";

/// Credential shape — mirrors the mesh transport's `EngagementCredential`
/// without taking a dependency on `wm-sangha`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DispatchEngagementCredential {
    /// Scope-of-engagement token issued by an Ed25519 key.
    pub token: EngagementToken,
    /// Issuer public key (hex) the token signature is checked against.
    pub issuer_public_key: String,
}

/// How the pipeline treats a missing credential for a capability-requiring
/// tool.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CapabilityGateMode {
    /// Log-only: requirements are observed, never enforced.
    Advisory,
    /// Enforce: uncredentialed capability-requiring dispatches are refused.
    Strict,
}

impl CapabilityGateMode {
    /// Read the mode from `WM_REQUIRE_CAPABILITIES` (`1`/`true`/`strict` =
    /// strict; anything else = advisory).
    #[must_use]
    pub fn from_env() -> Self {
        match std::env::var("WM_REQUIRE_CAPABILITIES").as_deref() {
            Ok("1" | "true" | "strict") => Self::Strict,
            _ => Self::Advisory,
        }
    }

    /// Whether this mode enforces the requirement.
    #[must_use]
    pub const fn is_strict(self) -> bool {
        matches!(self, Self::Strict)
    }

    /// Canonical label for logs and diagnostics.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::Advisory => "advisory",
            Self::Strict => "strict",
        }
    }
}

/// Map a tool's wm-core `invokes` list onto the governance capability
/// vocabulary.
///
/// Mapping decisions:
/// - `Search` / `VectorSearch` are memory reads.
/// - `Embed` / `LlmInfer` are model invocations.
/// - `Execute` is process spawning; `NetworkRequest` is outbound network.
/// - `Dream` consolidates memories (write); `CittaUpdate` is internal state
///   and maps to no external capability.
/// - `Delegate` (tool-to-tool delegation) is conservatively mapped to
///   `AdminGovernance` — delegation is a governed act; no current tool
///   declares it.
#[must_use]
pub fn required_capabilities(effects: &EffectRow) -> CapabilitySet {
    let mut set = CapabilitySet::EMPTY;
    for cap in &effects.invokes {
        let mapped = match cap {
            CoreCapability::MemoryRead | CoreCapability::Search | CoreCapability::VectorSearch => {
                Some(Capability::MemoryRead)
            }
            CoreCapability::MemoryWrite => Some(Capability::MemoryWrite),
            CoreCapability::MemoryDelete => Some(Capability::MemoryDelete),
            CoreCapability::Embed | CoreCapability::LlmInfer => Some(Capability::ModelInvoke),
            CoreCapability::Execute => Some(Capability::IpcSpawn),
            CoreCapability::NetworkRequest => Some(Capability::NetOutbound),
            CoreCapability::Delegate => Some(Capability::AdminGovernance),
            CoreCapability::Dream => Some(Capability::MemoryWrite),
            CoreCapability::CittaUpdate => None,
        };
        if let Some(c) = mapped {
            set.insert(c);
        }
    }
    set
}

/// Outcome of a capability-gate evaluation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GateOutcome {
    /// The tool declares no governance-mapped capabilities.
    NotRequired,
    /// A valid credential covered the required set.
    Satisfied { required: CapabilitySet },
    /// No credential was presented and the mode is advisory.
    AdvisoryMissing { required: CapabilitySet },
}

/// Evaluate the capability gate for one dispatch.
///
/// Mutates `args` by removing the credential key when present (it must not
/// reach tool bodies or audit digests). Returns `Err(reason)` when a
/// presented credential is malformed or fails verification, or when strict
/// mode finds a requirement with no credential.
pub fn evaluate(
    effects: &EffectRow,
    args: &mut serde_json::Value,
    mode: CapabilityGateMode,
    now: i64,
) -> std::result::Result<GateOutcome, String> {
    let required = required_capabilities(effects);

    let credential_value = args
        .as_object_mut()
        .and_then(|object| object.remove(ENGAGEMENT_KEY));

    if let Some(value) = credential_value {
        let credential: DispatchEngagementCredential = serde_json::from_value(value)
            .map_err(|e| format!("malformed engagement credential: {e}"))?;
        assert_engagement_token_capabilities(
            &credential.token,
            &credential.issuer_public_key,
            required,
            now,
        )
        .map_err(|e| format!("engagement rejected: {e}"))?;
        return Ok(GateOutcome::Satisfied { required });
    }

    if required.is_empty() {
        return Ok(GateOutcome::NotRequired);
    }

    if mode.is_strict() {
        return Err(format!(
            "capability required ({}), none granted — present a signed engagement \
             credential under args[\"{}\"] (WM_REQUIRE_CAPABILITIES=1)",
            required.labels().join(", "),
            ENGAGEMENT_KEY
        ));
    }

    Ok(GateOutcome::AdvisoryMissing { required })
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::Capability as CoreCapability;
    use wm_governance::engagement_tokens::{EngagementIssuer, EngagementScope};
    use wm_governance::network_profile::AgentKeypair;

    fn effects_with(caps: Vec<CoreCapability>) -> EffectRow {
        EffectRow {
            invokes: caps,
            ..Default::default()
        }
    }

    fn credential_args(scope: EngagementScope) -> (serde_json::Value, EngagementToken) {
        let mut issuer = EngagementIssuer::with_keypair(AgentKeypair::from_seed([42u8; 32]));
        let issuer_key = issuer.signer_public_key_hex();
        let token = issuer.issue("tester", scope, "rules-hash", Some(3600));
        let args = serde_json::json!({
            ENGAGEMENT_KEY: {
                "token": token,
                "issuer_public_key": issuer_key,
            }
        });
        (args, token)
    }

    #[test]
    fn mapping_is_total_and_documented() {
        // Every core capability either maps to a governance capability or is
        // deliberately unmapped (CittaUpdate = internal state).
        let all = [
            CoreCapability::MemoryRead,
            CoreCapability::MemoryWrite,
            CoreCapability::MemoryDelete,
            CoreCapability::Search,
            CoreCapability::VectorSearch,
            CoreCapability::Embed,
            CoreCapability::LlmInfer,
            CoreCapability::Delegate,
            CoreCapability::Execute,
            CoreCapability::NetworkRequest,
            CoreCapability::Dream,
            CoreCapability::CittaUpdate,
        ];
        let mapped = required_capabilities(&effects_with(all.to_vec()));
        for expected in [
            Capability::MemoryRead,
            Capability::MemoryWrite,
            Capability::MemoryDelete,
            Capability::ModelInvoke,
            Capability::IpcSpawn,
            Capability::NetOutbound,
            Capability::AdminGovernance,
        ] {
            assert!(mapped.contains(expected), "missing {expected:?}");
        }
        // CittaUpdate maps to nothing; a pure-Citta row has no requirement.
        assert!(required_capabilities(&effects_with(vec![CoreCapability::CittaUpdate])).is_empty());
        assert!(required_capabilities(&EffectRow::pure()).is_empty());
    }

    #[test]
    fn advisory_missing_allows_and_strips_nothing() {
        let mut args = serde_json::json!({"content": "x"});
        let outcome = evaluate(
            &effects_with(vec![CoreCapability::MemoryWrite]),
            &mut args,
            CapabilityGateMode::Advisory,
            1_000,
        )
        .expect("advisory allows");
        assert!(matches!(outcome, GateOutcome::AdvisoryMissing { .. }));
        assert_eq!(args["content"], "x");
    }

    #[test]
    fn strict_missing_refuses_with_actionable_error() {
        let mut args = serde_json::json!({});
        let err = evaluate(
            &effects_with(vec![CoreCapability::MemoryWrite]),
            &mut args,
            CapabilityGateMode::Strict,
            1_000,
        )
        .unwrap_err();
        assert!(err.contains("memory:write"), "{err}");
        assert!(err.contains(ENGAGEMENT_KEY), "{err}");
    }

    #[test]
    fn valid_credential_satisfies_and_is_stripped() {
        let (mut args, _token) = credential_args(EngagementScope::Poc);
        let outcome = evaluate(
            &effects_with(vec![CoreCapability::MemoryWrite]),
            &mut args,
            CapabilityGateMode::Strict,
            1_000,
        )
        .expect("poc token grants memory:write");
        assert!(matches!(outcome, GateOutcome::Satisfied { .. }));
        assert!(
            args.get(ENGAGEMENT_KEY).is_none(),
            "credential must be stripped before execution"
        );
    }

    #[test]
    fn insufficient_scope_is_refused_even_in_advisory_mode() {
        let (mut args, _token) = credential_args(EngagementScope::Demo);
        let err = evaluate(
            &effects_with(vec![CoreCapability::MemoryWrite]),
            &mut args,
            CapabilityGateMode::Advisory,
            1_000,
        )
        .unwrap_err();
        assert!(err.contains("Missing capabilities"), "{err}");
    }

    #[test]
    fn forged_credential_is_refused() {
        let (mut args, token) = credential_args(EngagementScope::Poc);
        // Corrupt the signature in the presented copy.
        let bogus = "0".repeat(token.signature.len());
        args[ENGAGEMENT_KEY]["token"]["signature"] = serde_json::json!(bogus);
        let err = evaluate(
            &effects_with(vec![CoreCapability::MemoryWrite]),
            &mut args,
            CapabilityGateMode::Advisory,
            1_000,
        )
        .unwrap_err();
        assert!(err.contains("signature is invalid"), "{err}");
    }

    #[test]
    fn malformed_credential_is_refused() {
        let mut args = serde_json::json!({ENGAGEMENT_KEY: {"nope": true}});
        let err = evaluate(
            &EffectRow::pure(),
            &mut args,
            CapabilityGateMode::Advisory,
            1_000,
        )
        .unwrap_err();
        assert!(err.contains("malformed engagement credential"), "{err}");
    }

    #[test]
    fn mode_env_parsing_labels() {
        assert!(CapabilityGateMode::Strict.is_strict());
        assert!(!CapabilityGateMode::Advisory.is_strict());
        assert_eq!(CapabilityGateMode::Advisory.label(), "advisory");
    }
}
