//! Signed decision receipts for the System One organ.
//!
//! Profile `continuity-receipt/0.5#decision`: a tamper-evident record of one
//! caller-pulsed decision — state digest, candidate-set digest, per-question
//! verdicts, model identity, policy version, and latency — signed with the
//! store's Mandala gate key.

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use wm_gen3_core::mandala::{Signer, SigningKey, Verifier, VerifyingKey};

/// One signed decision receipt.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionReceipt {
    pub spec: String,
    pub receipt_id: String,
    pub tenant_id: String,
    pub session_id: String,
    pub timestamp_ms: u64,
    pub state_digest: String,
    pub candidate_set_digest: String,
    #[serde(default)]
    pub candidate_set_version: Option<String>,
    #[serde(default)]
    pub task_class: Option<String>,
    pub decision_digest: String,
    #[serde(default)]
    pub chosen: Option<Value>,
    #[serde(default)]
    pub confidence: Option<Value>,
    #[serde(default)]
    pub act_probability: Option<Value>,
    #[serde(default)]
    pub model_id: Option<String>,
    pub policy_version: String,
    pub latency_ms: f64,
    pub issuer_did: String,
    #[serde(default)]
    pub signature: Option<String>,
}

impl DecisionReceipt {
    /// Build an unsigned receipt from a decision outcome and its request context.
    #[must_use]
    pub fn from_outcome(
        outcome: &Value,
        state: &Value,
        questions: &Value,
        args: &Value,
        issuer_did: String,
    ) -> Self {
        let empty = serde_json::Map::new();
        let answers = outcome
            .get("answers")
            .and_then(Value::as_object)
            .unwrap_or(&empty);

        let decisions: Vec<Value> = answers
            .iter()
            .map(|(id, answer)| {
                let qtype = answer
                    .get("type")
                    .and_then(Value::as_str)
                    .unwrap_or("unknown");
                let chosen = match qtype {
                    "choice" => answer.get("choice").cloned(),
                    "score" => answer.get("score").cloned(),
                    "noul" => answer.get("noul").cloned(),
                    _ => None,
                };
                json!({
                    "id": id,
                    "type": qtype,
                    "chosen": chosen,
                    "confidence": answer.get("confidence").cloned(),
                    "act_probability": answer
                        .get("rl_agent")
                        .and_then(|meta| meta.get("act_probability"))
                        .cloned(),
                })
            })
            .collect();

        let first = decisions.first().cloned().unwrap_or(Value::Null);
        let timestamp_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|duration| duration.as_millis() as u64)
            .unwrap_or(0);

        Self {
            spec: "continuity-receipt/0.5#decision".to_string(),
            receipt_id: uuid::Uuid::new_v4().to_string(),
            tenant_id: arg_str(args, "tenant_id").unwrap_or_else(|| "local".to_string()),
            session_id: arg_str(args, "session_id").unwrap_or_else(|| "adhoc".to_string()),
            timestamp_ms,
            state_digest: sha256_hex(state),
            candidate_set_digest: sha256_hex(questions),
            candidate_set_version: arg_str(args, "candidate_set_version"),
            task_class: arg_str(args, "task_class"),
            decision_digest: sha256_hex(&Value::Array(decisions)),
            chosen: first.get("chosen").cloned(),
            confidence: first.get("confidence").cloned(),
            act_probability: first.get("act_probability").cloned(),
            model_id: outcome
                .get("model")
                .and_then(Value::as_str)
                .map(str::to_string),
            policy_version: arg_str(args, "policy_version")
                .unwrap_or_else(|| "systemone/0.1".to_string()),
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
        if let Some(version) = &self.candidate_set_version {
            hasher.update(version.as_bytes());
        }
        hasher.update(b"|");
        if let Some(task_class) = &self.task_class {
            hasher.update(task_class.as_bytes());
        }
        hasher.update(b"|");
        hasher.update(self.decision_digest.as_bytes());
        hasher.update(b"|");
        if let Some(chosen) = &self.chosen {
            hasher.update(chosen.to_string().as_bytes());
        }
        hasher.update(b"|");
        if let Some(confidence) = &self.confidence {
            hasher.update(confidence.to_string().as_bytes());
        }
        hasher.update(b"|");
        if let Some(act) = &self.act_probability {
            hasher.update(act.to_string().as_bytes());
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
        let signature = wm_gen3_core::mandala::Signature::from_bytes(&array);
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

    fn fixture() -> DecisionReceipt {
        let outcome = json!({
            "model": "rl-agent",
            "latency_ms": 123.4,
            "answers": {
                "department": {
                    "type": "choice",
                    "choice": "billing",
                    "probabilities": {"billing": 0.93, "technical": 0.07},
                    "confidence": 0.72,
                    "rl_agent": {"act_probability": 1.0}
                }
            }
        });
        let state = json!("Charged twice for order #4417");
        let questions = json!({"department": {"type": "choice", "instructions": "which?", "criteria": ["billing", "technical"]}});
        let args = json!({"tenant_id": "tenant-primary", "task_class": "route_dispatch"});
        DecisionReceipt::from_outcome(
            &outcome,
            &state,
            &questions,
            &args,
            "did:key:test".to_string(),
        )
    }

    #[test]
    fn sign_and_verify_roundtrip() {
        let mut receipt = fixture();
        assert_eq!(
            receipt.chosen.as_ref().and_then(Value::as_str),
            Some("billing")
        );
        let key = SigningKey::from_bytes(&[7u8; 32]);
        receipt.sign(&key);
        receipt
            .verify(&key.verifying_key())
            .expect("signature verifies");

        let wrong = SigningKey::from_bytes(&[9u8; 32]);
        assert!(receipt.verify(&wrong.verifying_key()).is_err());
    }

    #[test]
    fn tamper_breaks_verification() {
        let mut receipt = fixture();
        let key = SigningKey::from_bytes(&[7u8; 32]);
        receipt.sign(&key);
        receipt.chosen = Some(json!("technical"));
        assert!(receipt.verify(&key.verifying_key()).is_err());
    }

    #[test]
    fn digests_are_deterministic() {
        let first = fixture();
        let second = fixture();
        assert_eq!(first.state_digest, second.state_digest);
        assert_eq!(first.candidate_set_digest, second.candidate_set_digest);
        assert_eq!(first.decision_digest, second.decision_digest);
    }
}
