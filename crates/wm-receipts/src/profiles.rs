//! WM bundle profiles: the honest mapping from WM evidence onto CR 0.2
//! record types.
//!
//! Two profiles ship in S1 (see `planning/private/RECEIPTS_S1_SCOPE_2026-09-22.md`):
//!
//! - **session** — `session.pass.created` → `task.decision` →
//!   `delivery.attestation` → `task.termination`. Binds the session mandate,
//!   the emission decision, the delivered turn evidence, and the stop.
//! - **karma_head** — the flagship: attests the karma-chain **head** (entry
//!   count + merkle root + head digest), never individual events. The emitter
//!   refuses to attest a chain that fails its integrity check.
//!
//! `task.execution` is deliberately unused: its required `sandbox_class` enum
//! has no honest value for an unconfined local emission (filed as CR spec
//! feedback, scope doc §5). Until a `local`/`process` value exists, evidence
//! rides `delivery.attestation`.

use chrono::{Duration, SecondsFormat, Utc};
use serde_json::{Value, json};

use crate::emit::{TaskChain, digest_of};
use crate::error::{ReceiptError, Result};
use crate::keys::ReceiptKey;

/// WM's receipt policy version recorded on every bundle.
pub const POLICY_VERSION: &str = concat!("wm-", env!("CARGO_PKG_VERSION"), "/receipts-v1");

/// Governance class recorded in `session.pass.created.mandala_class`.
///
/// This is a *class label*: WM's local dispatch seam is the lite governance
/// class; `gate_id` names the real issuer (`wm-local:<store>`). CR 0.2 has no
/// `local` class — filed as spec feedback.
pub const WM_MANDALA_CLASS: &str = "gate-lite";

/// The model/actor that made the emission decision (spec `model` object).
#[derive(Debug, Clone)]
pub struct ModelRef {
    /// Provider (e.g. `wm-local`).
    pub provider: String,
    /// Model or component id (e.g. `session-chronicle`, `karma-ledger`).
    pub id: String,
    /// Optional version.
    pub version: Option<String>,
}

impl ModelRef {
    /// The WM-local component reference used by both S1 profiles.
    #[must_use]
    pub fn wm_local(id: &str) -> Self {
        Self {
            provider: "wm-local".into(),
            id: id.into(),
            version: Some(env!("CARGO_PKG_VERSION").into()),
        }
    }

    fn to_value(&self) -> Value {
        let mut value = json!({ "provider": self.provider, "id": self.id });
        if let (Some(version), Some(object)) = (&self.version, value.as_object_mut()) {
            object.insert("version".into(), json!(version));
        }
        value
    }
}

/// One session turn's evidence reference (content stays out of the receipt;
/// only its SHA-256 is committed).
#[derive(Debug, Clone)]
pub struct TurnEvidence {
    /// Turn memory id.
    pub memory_id: String,
    /// Per-session sequence.
    pub sequence: u64,
    /// `user` | `ai`.
    pub role: String,
    /// Turn type (message, decision, …).
    pub turn_type: String,
    /// Millisecond epoch timestamp.
    pub timestamp_ms: i64,
    /// `sha256:` of the turn content.
    pub content_sha256: String,
}

impl TurnEvidence {
    fn to_value(&self) -> Value {
        json!({
            "memory_id": self.memory_id,
            "sequence": self.sequence,
            "role": self.role,
            "turn_type": self.turn_type,
            "timestamp_ms": self.timestamp_ms,
            "content_sha256": self.content_sha256,
        })
    }
}

/// Inputs for a session receipt bundle.
#[derive(Debug, Clone)]
pub struct SessionReceiptInput {
    /// Session uuid (urn form or bare).
    pub session_id: String,
    /// Session `user` string (honest identifier; CR prefers DID/URN — feedback).
    pub user: String,
    /// `session.start` memory id.
    pub session_start_id: String,
    /// `session.start` created_at (RFC 3339).
    pub session_start_created_at: String,
    /// `wm-local:<store>` gate id.
    pub store_gate_id: String,
    /// Emission timestamp (RFC 3339 UTC, second precision).
    pub issued_at: String,
    /// Mandate expiry.
    pub expires_at: String,
    /// First covered sequence.
    pub from_sequence: u64,
    /// Last covered sequence.
    pub to_sequence: u64,
    /// Session wall duration in milliseconds.
    pub duration_ms: u64,
    /// Coverage of turns.
    pub turns: Vec<TurnEvidence>,
    /// Decision actor.
    pub model: ModelRef,
}

/// Inputs for a karma-chain-head attestation bundle.
#[derive(Debug, Clone)]
pub struct KarmaHeadInput {
    /// Allocated karma entries (the ledger's `next_id`).
    pub entry_count: u64,
    /// Current chain head digest.
    pub chain_head: String,
    /// Merkle checkpoint root, when one has been computed.
    pub merkle_root: Option<String>,
    /// `sha256:` over the scanned ledger entries (binds what was read).
    pub scans_digest: String,
    /// Result of the deep integrity check; `false` refuses emission.
    pub integrity_ok: bool,
    /// `wm-local:<store>` gate id.
    pub store_gate_id: String,
    /// Emission timestamp (RFC 3339 UTC, second precision).
    pub issued_at: String,
    /// Mandate expiry.
    pub expires_at: String,
    /// Decision actor.
    pub model: ModelRef,
}

/// RFC 3339 UTC, second precision (spec v0 timestamp form).
#[must_use]
pub fn now_rfc3339() -> String {
    Utc::now().to_rfc3339_opts(SecondsFormat::Secs, true)
}

/// RFC 3339 UTC `hours` in the future.
#[must_use]
pub fn rfc3339_in_hours(hours: i64) -> String {
    (Utc::now() + Duration::hours(hours)).to_rfc3339_opts(SecondsFormat::Secs, true)
}

/// A stable, non-identifying gate id derived from the store identity.
pub fn gate_id_for_store(store_identity: &str) -> Result<String> {
    let digest = digest_of(&json!({ "store": store_identity }))?;
    let hex = digest.strip_prefix("sha256:").unwrap_or(&digest);
    Ok(format!("wm-local:{}", hex.get(..16).unwrap_or(hex)))
}

/// Canonical digest of the turn evidence list.
pub fn turn_digest(turns: &[TurnEvidence]) -> Result<String> {
    let values: Vec<Value> = turns.iter().map(TurnEvidence::to_value).collect();
    digest_of(&Value::Array(values))
}

/// Build a session receipt bundle (profile P1).
pub fn session_bundle(key: &ReceiptKey, input: &SessionReceiptInput) -> Result<Value> {
    let evidence = turn_digest(&input.turns)?;
    let mandate_ref = digest_of(&json!({
        "session_start_id": input.session_start_id,
        "created_at": input.session_start_created_at,
        "session_id": input.session_id,
    }))?;
    let range = json!({
        "session_id": input.session_id,
        "from_sequence": input.from_sequence,
        "to_sequence": input.to_sequence,
    });

    let mut chain = TaskChain::new(key.clone());
    chain.add(
        "session.pass.created",
        json!({
            "gate_id": input.store_gate_id,
            "mandala_class": WM_MANDALA_CLASS,
            "quotas": { "cpu_ms": 0, "mem_mb": 0, "disk_mb": 0, "wall_ms": input.duration_ms },
            "expires_at": input.expires_at,
            "policy_version": POLICY_VERSION,
            "mandate_ref": mandate_ref,
            "agent_id": input.user,
        }),
        &input.issued_at,
    )?;
    chain.add(
        "task.decision",
        json!({
            "action": "session.receipt.emit",
            "action_args_hash": digest_of(&json!({ "range": range, "evidence": evidence }))?,
            "model": input.model.to_value(),
            "input_provenance": {
                "policy_id": "wm-local/receipts-v1",
                "allowed_sources": ["galaxy:sessions"],
                "observed_sources_hash": evidence,
            },
            "decision": "allow",
            "policy_version": POLICY_VERSION,
        }),
        &input.issued_at,
    )?;
    chain.add(
        "delivery.attestation",
        json!({
            "request_hash": digest_of(&range)?,
            "response_hash": evidence,
            "counterparty": { "id": key.did() },
        }),
        &input.issued_at,
    )?;
    chain.add(
        "task.termination",
        json!({
            "reason": "completed",
            "limits_at_stop": {
                "cpu_ms": 0,
                "wall_ms": input.duration_ms,
                "spend_minor": 0,
                "currency": "USD",
            },
            "remaining": {},
        }),
        &input.issued_at,
    )?;
    Ok(chain.bundle())
}

/// Build a karma-chain-head attestation bundle (profile P2, the flagship).
///
/// Refuses when `integrity_ok` is false: no receipt for broken evidence.
pub fn karma_head_bundle(key: &ReceiptKey, input: &KarmaHeadInput) -> Result<Value> {
    if !input.integrity_ok {
        return Err(ReceiptError::Refused(
            "karma chain failed its integrity check; refusing to attest a head".into(),
        ));
    }
    let mandate_ref = digest_of(
        &json!({ "store_gate_id": input.store_gate_id, "chain_head": input.chain_head }),
    )?;

    let mut chain = TaskChain::new(key.clone());
    chain.add(
        "session.pass.created",
        json!({
            "gate_id": input.store_gate_id,
            "mandala_class": WM_MANDALA_CLASS,
            "quotas": { "cpu_ms": 0, "mem_mb": 0, "disk_mb": 0, "wall_ms": 0 },
            "expires_at": input.expires_at,
            "policy_version": POLICY_VERSION,
            "mandate_ref": mandate_ref,
            "agent_id": key.did(),
        }),
        &input.issued_at,
    )?;
    chain.add(
        "task.decision",
        json!({
            "action": "karma.chain.head.attest",
            "action_args_hash": digest_of(&json!({
                "entry_count": input.entry_count,
                "merkle_root": input.merkle_root,
            }))?,
            "model": input.model.to_value(),
            "input_provenance": {
                "policy_id": "wm-local/karma-v1",
                "allowed_sources": ["galaxy:karma"],
                "observed_sources_hash": input.scans_digest,
            },
            "decision": "allow",
            "policy_version": POLICY_VERSION,
        }),
        &input.issued_at,
    )?;
    chain.add(
        "delivery.attestation",
        json!({
            "request_hash": digest_of(&json!({
                "entry_count": input.entry_count,
                "merkle_root": input.merkle_root,
                "issued_at": input.issued_at,
            }))?,
            "response_hash": input.chain_head,
            "counterparty": { "id": key.did() },
        }),
        &input.issued_at,
    )?;
    chain.add(
        "task.termination",
        json!({
            "reason": "completed",
            "limits_at_stop": {
                "cpu_ms": 0,
                "wall_ms": 0,
                "spend_minor": 0,
                "currency": "USD",
            },
            "remaining": {},
        }),
        &input.issued_at,
    )?;
    Ok(chain.bundle())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::verify::verify_bundle;

    fn key() -> ReceiptKey {
        ReceiptKey::from_seed([7u8; 32])
    }

    fn turn(sequence: u64) -> TurnEvidence {
        TurnEvidence {
            memory_id: format!("00000000-0000-7000-8000-{sequence:012}"),
            sequence,
            role: if sequence % 2 == 0 { "user" } else { "ai" }.into(),
            turn_type: "message".into(),
            timestamp_ms: 1_758_500_000_000 + i64::try_from(sequence).expect("sequence fits i64"),
            content_sha256: digest_of(&json!(format!("turn-{sequence}"))).expect("digest"),
        }
    }

    fn session_input() -> SessionReceiptInput {
        SessionReceiptInput {
            session_id: "11111111-1111-7111-8111-111111111111".into(),
            user: "default".into(),
            session_start_id: "22222222-2222-7222-8222-222222222222".into(),
            session_start_created_at: "2026-09-22T09:00:00Z".into(),
            store_gate_id: gate_id_for_store("/tmp/wm-s1-test/store").expect("gate id"),
            issued_at: "2026-09-22T10:00:00Z".into(),
            expires_at: "2026-09-23T10:00:00Z".into(),
            from_sequence: 1,
            to_sequence: 2,
            duration_ms: 3_600_000,
            turns: vec![turn(1), turn(2)],
            model: ModelRef::wm_local("session-chronicle"),
        }
    }

    fn karma_input() -> KarmaHeadInput {
        KarmaHeadInput {
            entry_count: 42,
            chain_head: "ab".repeat(32),
            merkle_root: Some("cd".repeat(32)),
            scans_digest: digest_of(&json!(["entry-1", "entry-2"])).expect("digest"),
            integrity_ok: true,
            store_gate_id: gate_id_for_store("/tmp/wm-s1-test/store").expect("gate id"),
            issued_at: "2026-09-22T10:00:00Z".into(),
            expires_at: "2026-09-23T10:00:00Z".into(),
            model: ModelRef::wm_local("karma-ledger"),
        }
    }

    #[test]
    fn session_bundle_verifies_trusted() {
        let bundle = session_bundle(&key(), &session_input()).expect("bundle");
        assert_eq!(bundle["receipts"].as_array().expect("receipts").len(), 4);
        let outcome = verify_bundle(&bundle, false);
        assert!(outcome.is_trusted(), "{:?}", outcome.to_value());
    }

    #[test]
    fn tampered_evidence_is_untrusted() {
        let mut bundle = session_bundle(&key(), &session_input()).expect("bundle");
        bundle["receipts"][2]["body"]["response_hash"] =
            json!("sha256:".to_string() + &"00".repeat(32));
        let outcome = verify_bundle(&bundle, false);
        assert!(!outcome.is_trusted());
        assert_eq!(outcome.verdict, "UNTRUSTED");
    }

    #[test]
    fn karma_head_bundle_verifies_trusted_and_binds_the_head() {
        let input = karma_input();
        let bundle = karma_head_bundle(&key(), &input).expect("bundle");
        let outcome = verify_bundle(&bundle, false);
        assert!(outcome.is_trusted(), "{:?}", outcome.to_value());
        assert_eq!(
            bundle["receipts"][2]["body"]["response_hash"],
            input.chain_head
        );
    }

    #[test]
    fn invalid_chain_is_refused() {
        let mut input = karma_input();
        input.integrity_ok = false;
        let error = karma_head_bundle(&key(), &input).expect_err("must refuse");
        assert!(matches!(error, ReceiptError::Refused(_)));
    }

    #[test]
    fn turn_digest_is_order_sensitive() {
        let a = turn_digest(&[turn(1), turn(2)]).expect("digest");
        let b = turn_digest(&[turn(2), turn(1)]).expect("digest");
        assert_ne!(a, b);
    }
}
