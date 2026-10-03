//! Signed shortlist receipts for the System 0.5 retrieval organ.
//!
//! Profile `continuity-receipt/0.5#shortlist`: a tamper-evident record of one
//! retrieval pulse — state digest, candidate-set digest, ranked shortlist
//! digest, gate decision, margin, model identity — signed with the store's
//! Mandala gate key.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use wm_gen3_core::mandala::{Signature, Signer, SigningKey, Verifier, VerifyingKey};

/// One signed shortlist receipt.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShortlistReceipt {
    pub spec: String,
    pub receipt_id: String,
    pub tenant_id: String,
    pub session_id: String,
    pub timestamp_ms: u64,
    pub state_digest: String,
    pub candidate_set_digest: String,
    pub shortlist_digest: String,
    pub gate: String,
    #[serde(default)]
    pub top1: Option<String>,
    pub confidence: f64,
    pub margin: f64,
    #[serde(default)]
    pub task_class: Option<String>,
    #[serde(default)]
    pub model_id: Option<String>,
    pub policy_version: String,
    pub latency_ms: f64,
    pub issuer_did: String,
    #[serde(default)]
    pub signature: Option<String>,
}

impl ShortlistReceipt {
    /// Build an unsigned receipt from a shortlist outcome and its request context.
    #[must_use]
    pub fn from_outcome(
        outcome: &Value,
        state: &Value,
        routes: &Value,
        args: &Value,
        issuer_did: String,
    ) -> Self {
        let timestamp_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|duration| duration.as_millis() as u64)
            .unwrap_or(0);

        Self {
            spec: "continuity-receipt/0.5#shortlist".to_string(),
            receipt_id: uuid::Uuid::new_v4().to_string(),
            tenant_id: arg_str(args, "tenant_id").unwrap_or_else(|| "local".to_string()),
            session_id: arg_str(args, "session_id").unwrap_or_else(|| "adhoc".to_string()),
            timestamp_ms,
            state_digest: sha256_hex(state),
            candidate_set_digest: sha256_hex(routes),
            shortlist_digest: sha256_hex(outcome.get("ranked").unwrap_or(&Value::Null)),
            gate: outcome
                .get("gate")
                .and_then(Value::as_str)
                .unwrap_or("unknown")
                .to_string(),
            top1: outcome
                .get("top1")
                .and_then(Value::as_str)
                .map(str::to_string),
            confidence: outcome
                .get("confidence")
                .and_then(Value::as_f64)
                .unwrap_or(0.0),
            margin: outcome.get("margin").and_then(Value::as_f64).unwrap_or(0.0),
            task_class: arg_str(args, "task_class"),
            model_id: outcome
                .get("model")
                .and_then(Value::as_str)
                .map(str::to_string),
            policy_version: arg_str(args, "policy_version")
                .unwrap_or_else(|| "system05/0.1".to_string()),
            latency_ms: outcome
                .get("latency_ms")
                .and_then(Value::as_f64)
                .unwrap_or(0.0),
            issuer_did,
            signature: None,
        }
    }

    /// Canonical signing bytes (the signature field itself is excluded).
    #[must_use]
    pub fn canonical_signing_bytes(&self) -> Vec<u8> {
        let mut hasher = Sha256::new();
        hasher.update(self.spec.as_bytes());
        hasher.update(b"|");
        hasher.update(self.receipt_id.as_bytes());
        hasher.update(b"|");
        hasher.update(self.tenant_id.as_bytes());
        hasher.update(b"|");
        hasher.update(self.session_id.as_bytes());
        hasher.update(b"|");
        hasher.update(self.timestamp_ms.to_le_bytes());
        hasher.update(b"|");
        hasher.update(self.state_digest.as_bytes());
        hasher.update(b"|");
        hasher.update(self.candidate_set_digest.as_bytes());
        hasher.update(b"|");
        hasher.update(self.shortlist_digest.as_bytes());
        hasher.update(b"|");
        hasher.update(self.gate.as_bytes());
        hasher.update(b"|");
        if let Some(top1) = &self.top1 {
            hasher.update(top1.as_bytes());
        }
        hasher.update(b"|");
        hasher.update(self.confidence.to_bits().to_le_bytes());
        hasher.update(b"|");
        hasher.update(self.margin.to_bits().to_le_bytes());
        hasher.update(b"|");
        if let Some(task_class) = &self.task_class {
            hasher.update(task_class.as_bytes());
        }
        hasher.update(b"|");
        if let Some(model_id) = &self.model_id {
            hasher.update(model_id.as_bytes());
        }
        hasher.update(b"|");
        hasher.update(self.policy_version.as_bytes());
        hasher.update(b"|");
        hasher.update(self.latency_ms.to_bits().to_le_bytes());
        hasher.update(b"|");
        hasher.update(self.issuer_did.as_bytes());
        hasher.finalize().to_vec()
    }

    /// Sign with the store's Mandala gate key.
    pub fn sign(&mut self, key: &SigningKey) {
        let signature = key.sign(&self.canonical_signing_bytes());
        self.signature = Some(hex_encode(&signature.to_bytes()));
    }

    /// Verify against a gate verifying key.
    pub fn verify(&self, key: &VerifyingKey) -> Result<(), String> {
        let signature_hex = self.signature.as_ref().ok_or("unsigned receipt")?;
        let bytes = hex_decode(signature_hex).ok_or("signature is not valid hex")?;
        if bytes.len() != 64 {
            return Err("signature must be 64 bytes".to_string());
        }
        let mut array = [0u8; 64];
        array.copy_from_slice(&bytes);
        let signature = Signature::from_bytes(&array);
        key.verify(&self.canonical_signing_bytes(), &signature)
            .map_err(|e| format!("signature invalid: {e}"))
    }
}

fn arg_str(args: &Value, key: &str) -> Option<String> {
    args.get(key)
        .and_then(Value::as_str)
        .map(str::to_string)
        .filter(|value| !value.is_empty())
}

fn sha256_hex(value: &Value) -> String {
    let mut hasher = Sha256::new();
    hasher.update(value.to_string().as_bytes());
    hex_encode(&hasher.finalize())
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn hex_decode(hex: &str) -> Option<Vec<u8>> {
    if hex.len() % 2 != 0 {
        return None;
    }
    (0..hex.len())
        .step_by(2)
        .map(|index| u8::from_str_radix(&hex[index..index + 2], 16).ok())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn fixture() -> ShortlistReceipt {
        let outcome = json!({
            "model": "potion-base-32M",
            "latency_ms": 12.345678901234567,
            "ranked": [{"route": "memory.create", "score": 0.71}, {"route": "memory.search", "score": 0.42}],
            "top1": "memory.create",
            "confidence": 0.7100000000000001,
            "margin": 0.07857093214988708,
            "gate": "dispatch"
        });
        let state = json!("remember this: the red block belongs in bay 3");
        let routes = json!({"memory.create": "Store a new memory or fact.", "memory.search": "Retrieve memories by query."});
        let args = json!({"tenant_id": "tenant-primary", "task_class": "route_dispatch"});
        ShortlistReceipt::from_outcome(&outcome, &state, &routes, &args, "did:key:test".to_string())
    }

    #[test]
    fn sign_and_verify_roundtrip() {
        let mut receipt = fixture();
        assert_eq!(receipt.gate, "dispatch");
        assert_eq!(receipt.top1.as_deref(), Some("memory.create"));
        let key = SigningKey::from_bytes(&[7u8; 32]);
        receipt.sign(&key);
        receipt
            .verify(&key.verifying_key())
            .expect("signature verifies");
        let wrong = SigningKey::from_bytes(&[9u8; 32]);
        assert!(receipt.verify(&wrong.verifying_key()).is_err());
    }

    #[test]
    fn sign_survives_json_roundtrip() {
        let mut receipt = fixture();
        let key = SigningKey::from_bytes(&[7u8; 32]);
        receipt.sign(&key);
        let json = serde_json::to_string_pretty(&receipt).expect("serialize");
        let back: ShortlistReceipt = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(
            receipt.canonical_signing_bytes(),
            back.canonical_signing_bytes(),
            "canonical bytes must survive a JSON round trip"
        );
        back.verify(&key.verifying_key()).expect("roundtrip verifies");
    }

    #[test]
    fn tamper_breaks_verification() {
        let mut receipt = fixture();
        let key = SigningKey::from_bytes(&[7u8; 32]);
        receipt.sign(&key);
        receipt.margin += 0.01;
        assert!(receipt.verify(&key.verifying_key()).is_err());
    }

    #[test]
    fn digests_are_deterministic() {
        let first = fixture();
        let second = fixture();
        assert_eq!(first.state_digest, second.state_digest);
        assert_eq!(first.candidate_set_digest, second.candidate_set_digest);
        assert_eq!(first.shortlist_digest, second.shortlist_digest);
    }
}
