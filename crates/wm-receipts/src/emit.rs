//! Envelope emission, hash chaining, and signing for `continuity-receipt/0.2`.
//!
//! Byte-exact rules (frozen by the reference implementation): the canonical
//! view of a receipt is the object **excluding `sig`**; both `prev` links and
//! signatures are computed over that same view. Canonicalization and hashing
//! are delegated to the independent `continuity-receipt` crate.

use continuity_receipt::canon::{canonical_bytes, sha256_prefixed};
use serde_json::{Value, json};

use crate::error::{ReceiptError, Result};
use crate::keys::ReceiptKey;

/// Spec id emitted by this implementation.
pub const SPEC_ID: &str = "continuity-receipt/0.2";

/// Record types of spec 0.2.
pub const RECORD_TYPES: [&str; 7] = [
    "session.pass.created",
    "task.decision",
    "task.execution",
    "delivery.attestation",
    "task.termination",
    "settlement",
    "authority.succession",
];

/// Required body fields per record type (spec §4).
#[must_use]
pub fn required_fields(record_type: &str) -> Option<&'static [&'static str]> {
    match record_type {
        "session.pass.created" => Some(&[
            "gate_id",
            "mandala_class",
            "quotas",
            "expires_at",
            "policy_version",
            "mandate_ref",
            "agent_id",
        ]),
        "task.decision" => Some(&[
            "action",
            "action_args_hash",
            "model",
            "input_provenance",
            "decision",
            "policy_version",
        ]),
        "task.execution" => Some(&["tool_calls", "egress", "resources", "sandbox_class"]),
        "delivery.attestation" => Some(&["request_hash", "response_hash", "counterparty"]),
        "task.termination" => Some(&["reason", "limits_at_stop", "remaining"]),
        "settlement" => Some(&[
            "rail",
            "rail_ref",
            "amount",
            "gated_on_delivery",
            "settled_at",
        ]),
        "authority.succession" => {
            Some(&["from_authority", "to_authority", "effective_at", "reason"])
        }
        _ => None,
    }
}

/// Validate a body against the record type's required fields.
pub fn validate_body(record_type: &str, body: &Value) -> Result<()> {
    let fields = required_fields(record_type)
        .ok_or_else(|| ReceiptError::InvalidArgs(format!("unknown record type: {record_type}")))?;
    let object = body.as_object().ok_or_else(|| {
        ReceiptError::InvalidArgs(format!("body for {record_type} is not an object"))
    })?;
    let missing: Vec<&str> = fields
        .iter()
        .filter(|name| !object.contains_key(**name))
        .copied()
        .collect();
    if missing.is_empty() {
        Ok(())
    } else {
        Err(ReceiptError::InvalidArgs(format!(
            "body for {record_type} missing required fields {missing:?}"
        )))
    }
}

/// The canonical view: the object without its `sig` member.
#[must_use]
pub fn unsigned_view(receipt: &Value) -> Value {
    match receipt {
        Value::Object(map) => {
            let mut clone = map.clone();
            clone.remove("sig");
            Value::Object(clone)
        }
        other => other.clone(),
    }
}

/// `sha256(canonical(unsigned view))` — the chain link and anchor digest.
pub fn receipt_digest(receipt: &Value) -> Result<String> {
    let bytes = canonical_bytes(&unsigned_view(receipt))
        .map_err(|error| ReceiptError::Canon(error.to_string()))?;
    Ok(sha256_prefixed(&bytes))
}

/// `sha256` over the canonical form of any value (body digests, commitments).
pub fn digest_of(value: &Value) -> Result<String> {
    let bytes = canonical_bytes(value).map_err(|error| ReceiptError::Canon(error.to_string()))?;
    Ok(sha256_prefixed(&bytes))
}

/// `sha256:` over raw bytes (turn-content commitments).
#[must_use]
pub fn content_digest(text: &str) -> String {
    sha256_prefixed(text.as_bytes())
}

/// Assemble an unsigned envelope. `seq` starts at 0; `prev` is `null` at seq 0.
// Nine call-site fields mirror the wire envelope; a struct would only add
// indirection at the one place the envelope is built.
#[allow(clippy::too_many_arguments)]
#[must_use]
pub fn envelope(
    task_id: &str,
    receipt_id: &str,
    issued_at: &str,
    issuer_kind: &str,
    issuer_did: &str,
    record_type: &str,
    seq: usize,
    prev: Option<&str>,
    body: &Value,
) -> Value {
    json!({
        "spec": SPEC_ID,
        "receipt_id": receipt_id,
        "task_id": task_id,
        "issued_at": issued_at,
        "issuer": { "kind": issuer_kind, "id": issuer_did },
        "type": record_type,
        "seq": seq,
        "prev": prev,
        "body": body,
    })
}

/// Sign an envelope: Ed25519 over the canonical unsigned view.
pub fn sign_receipt(receipt: &Value, key: &ReceiptKey) -> Result<Value> {
    let bytes = canonical_bytes(&unsigned_view(receipt))
        .map_err(|error| ReceiptError::Canon(error.to_string()))?;
    let signature = key.sign(&bytes);
    let mut signed = receipt.clone();
    let object = signed
        .as_object_mut()
        .ok_or_else(|| ReceiptError::InvalidArgs("receipt is not an object".into()))?;
    object.insert(
        "sig".into(),
        json!({ "alg": "ed25519", "key": key.did(), "value": signature }),
    );
    Ok(signed)
}

/// A task chain under construction: signed receipts with `prev` links.
#[derive(Debug, Clone)]
pub struct TaskChain {
    task_id: String,
    key: ReceiptKey,
    receipts: Vec<Value>,
}

impl TaskChain {
    /// New chain with a fresh UUIDv7 task id.
    #[must_use]
    pub fn new(key: ReceiptKey) -> Self {
        Self {
            task_id: format!("urn:uuid:{}", uuid::Uuid::now_v7()),
            key,
            receipts: Vec::new(),
        }
    }

    /// New chain with an explicit task id (tests, re-emission).
    #[must_use]
    pub fn with_task_id(key: ReceiptKey, task_id: impl Into<String>) -> Self {
        Self {
            task_id: task_id.into(),
            key,
            receipts: Vec::new(),
        }
    }

    /// The task id shared by every receipt in this chain.
    #[must_use]
    pub fn task_id(&self) -> &str {
        &self.task_id
    }

    /// Signed receipts added so far.
    #[must_use]
    pub fn receipts(&self) -> &[Value] {
        &self.receipts
    }

    /// Append a signed receipt for `record_type` with `body`.
    // `body` is taken by value for caller ergonomics (`chain.add(t, json!{…})`);
    // it is not consumed beyond validation + serialization.
    #[allow(clippy::needless_pass_by_value)]
    pub fn add(&mut self, record_type: &str, body: Value, issued_at: &str) -> Result<&Value> {
        validate_body(record_type, &body)?;
        let prev = match self.receipts.last() {
            Some(last) => Some(receipt_digest(last)?),
            None => None,
        };
        let unsigned = envelope(
            &self.task_id,
            &format!("urn:uuid:{}", uuid::Uuid::now_v7()),
            issued_at,
            "agent",
            self.key.did(),
            record_type,
            self.receipts.len(),
            prev.as_deref(),
            &body,
        );
        let signed = sign_receipt(&unsigned, &self.key)?;
        self.receipts.push(signed);
        Ok(self.receipts.last().expect("just pushed"))
    }

    /// The wire bundle: `{spec, task_id, receipts}`.
    #[must_use]
    pub fn bundle(&self) -> Value {
        json!({
            "spec": SPEC_ID,
            "task_id": self.task_id,
            "receipts": self.receipts,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key() -> ReceiptKey {
        ReceiptKey::from_seed([7u8; 32])
    }

    fn simple_body() -> Value {
        json!({
            "reason": "completed",
            "limits_at_stop": { "cpu_ms": 0, "wall_ms": 10, "spend_minor": 0, "currency": "USD" },
            "remaining": {},
        })
    }

    #[test]
    fn chain_links_and_verifies() {
        let mut chain = TaskChain::new(key());
        let first = chain
            .add("task.termination", simple_body(), "2026-09-22T10:00:00Z")
            .expect("add");
        assert_eq!(first["seq"], 0);
        assert!(first["prev"].is_null());
        second_add(&mut chain);
        assert_eq!(chain.receipts().len(), 2);
        assert_eq!(
            chain.receipts()[1]["prev"].as_str().expect("prev"),
            &receipt_digest(&chain.receipts()[0]).expect("digest")
        );
    }

    fn second_add(chain: &mut TaskChain) {
        let duplicate = chain
            .add("task.termination", simple_body(), "2026-09-22T10:00:01Z")
            .expect("add");
        assert_eq!(duplicate["seq"], 1);
    }

    #[test]
    fn unknown_type_and_missing_fields_are_refused() {
        let mut chain = TaskChain::new(key());
        assert!(
            chain
                .add("nope.type", json!({}), "2026-09-22T10:00:00Z")
                .is_err()
        );
        assert!(
            chain
                .add(
                    "task.termination",
                    json!({ "reason": "completed" }),
                    "2026-09-22T10:00:00Z"
                )
                .is_err()
        );
    }

    #[test]
    fn unsigned_view_strips_only_sig() {
        let mut chain = TaskChain::new(key());
        chain
            .add("task.termination", simple_body(), "2026-09-22T10:00:00Z")
            .expect("add");
        let receipt = &chain.receipts()[0];
        let view = unsigned_view(receipt);
        assert!(view.get("sig").is_none());
        assert!(view.get("body").is_some());
        assert!(receipt.get("sig").is_some());
    }
}
