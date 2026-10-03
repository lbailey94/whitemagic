//! Offline verification for signed Gen3 receipts, plus outcome backfill.
//!
//! `verify_receipt_file` checks a `#decision` or `#shortlist` receipt against
//! the store's Mandala gate key without touching the substrate.
//! `record_outcome` signs an outcome for a subject receipt and journals it to
//! `<store>/receipts/outcomes.jsonl` for the learning loop.

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use wm_gen3_core::mandala::{
    Signature, Signer, SigningKey, Verifier, VerifyingKey, resolve_or_create_mandala_gate_key,
};

/// Read the store's gate verifying key without creating one.
fn load_verifying_key(store_path: &Path) -> Result<VerifyingKey, String> {
    let key_path = store_path.join("mandala_gate_key.bin");
    let bytes = std::fs::read(&key_path)
        .map_err(|e| format!("gate key read ({}): {e}", key_path.display()))?;
    if bytes.len() != 32 {
        return Err(format!("gate key must be 32 bytes, got {}", bytes.len()));
    }
    let mut array = [0u8; 32];
    array.copy_from_slice(&bytes);
    Ok(SigningKey::from_bytes(&array).verifying_key())
}

/// Verify a signed receipt file against the store's gate key.
pub fn verify_receipt_file(path: &Path, store_path: &Path) -> Result<Value, String> {
    let raw = std::fs::read_to_string(path).map_err(|e| format!("receipt read: {e}"))?;
    let value: Value = serde_json::from_str(&raw).map_err(|e| format!("receipt parse: {e}"))?;
    let spec = value
        .get("spec")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_string();
    if spec.is_empty() {
        return Err("receipt has no 'spec' field".to_string());
    }
    let key = load_verifying_key(store_path)?;

    let (valid, profile, detail) = if spec.ends_with("#decision") {
        verify_profile(&value, &key, "decision")
    } else if spec.ends_with("#shortlist") {
        verify_profile(&value, &key, "shortlist")
    } else if spec.ends_with("#deliberation") {
        verify_profile(&value, &key, "deliberation")
    } else if spec.ends_with("#outcome") {
        verify_profile(&value, &key, "outcome")
    } else {
        return Err(format!("unsupported receipt spec: {spec}"));
    };

    Ok(json!({
        "status": "success",
        "valid": valid,
        "profile": profile,
        "spec": spec,
        "receipt_id": value.get("receipt_id"),
        "issuer_did": value.get("issuer_did"),
        "detail": detail,
        "verified_offline": true,
    }))
}

fn verify_profile(
    value: &Value,
    key: &VerifyingKey,
    profile: &str,
) -> (bool, &'static str, Option<String>) {
    let result: Result<(), String> = match profile {
        "decision" => {
            #[cfg(feature = "systemone")]
            {
                serde_json::from_value::<crate::decision_receipt::DecisionReceipt>(value.clone())
                    .map_err(|e| e.to_string())
                    .and_then(|receipt| receipt.verify(key))
            }
            #[cfg(not(feature = "systemone"))]
            {
                Err("systemone feature not compiled".to_string())
            }
        }
        "shortlist" => {
            #[cfg(feature = "system05")]
            {
                serde_json::from_value::<crate::shortlist_receipt::ShortlistReceipt>(value.clone())
                    .map_err(|e| e.to_string())
                    .and_then(|receipt| receipt.verify(key))
            }
            #[cfg(not(feature = "system05"))]
            {
                Err("system05 feature not compiled".to_string())
            }
        }
        "deliberation" => {
            serde_json::from_value::<crate::deliberation::DeliberationReceipt>(value.clone())
                .map_err(|e| e.to_string())
                .and_then(|receipt| {
                    receipt.verify()?;
                    let pubkey_bytes = key.to_bytes();
                    let expected_did = format!(
                        "did:key:{}",
                        pubkey_bytes.iter().map(|b| format!("{:02x}", b)).collect::<String>()
                    );
                    if receipt.issuer_did != expected_did {
                        return Err(format!(
                            "issuer_did mismatch: expected {expected_did}, got {}",
                            receipt.issuer_did
                        ));
                    }
                    Ok(())
                })
        }
        _ => serde_json::from_value::<OutcomeRecord>(value.clone())
            .map_err(|e| e.to_string())
            .and_then(|record| record.verify(key)),
    };
    let profile: &'static str = if profile == "decision" {
        "decision"
    } else if profile == "shortlist" {
        "shortlist"
    } else if profile == "deliberation" {
        "deliberation"
    } else {
        "outcome"
    };
    (result.is_ok(), profile, result.err())
}

/// Signed outcome record for a subject receipt.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutcomeRecord {
    pub spec: String,
    pub record_id: String,
    pub subject_receipt: String,
    pub subject_spec: String,
    pub subject_verified: bool,
    pub outcome: String,
    #[serde(default)]
    pub corrected_route: Option<String>,
    #[serde(default)]
    pub note: Option<String>,
    pub tenant_id: String,
    pub session_id: String,
    pub recorded_at_ms: u64,
    pub issuer_did: String,
    #[serde(default)]
    pub signature: Option<String>,
}

impl OutcomeRecord {
    /// Build an unsigned outcome record.
    #[must_use]
    pub fn new(
        subject_receipt: String,
        subject_spec: String,
        subject_verified: bool,
        args: &Value,
        issuer_did: String,
    ) -> Result<Self, String> {
        let outcome = args
            .get("outcome")
            .and_then(Value::as_str)
            .ok_or("missing required field 'outcome'")?;
        let recorded_at_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|duration| duration.as_millis() as u64)
            .unwrap_or(0);
        Ok(Self {
            spec: "continuity-receipt/0.5#outcome".to_string(),
            record_id: uuid::Uuid::new_v4().to_string(),
            subject_receipt,
            subject_spec,
            subject_verified,
            outcome: outcome.to_string(),
            corrected_route: args
                .get("corrected_route")
                .and_then(Value::as_str)
                .map(str::to_string),
            note: args.get("note").and_then(Value::as_str).map(str::to_string),
            tenant_id: args
                .get("tenant_id")
                .and_then(Value::as_str)
                .unwrap_or("local")
                .to_string(),
            session_id: args
                .get("session_id")
                .and_then(Value::as_str)
                .unwrap_or("adhoc")
                .to_string(),
            recorded_at_ms,
            issuer_did,
            signature: None,
        })
    }

    /// Canonical signing bytes (signature excluded).
    #[must_use]
    pub fn canonical_signing_bytes(&self) -> Vec<u8> {
        let mut hasher = Sha256::new();
        hasher.update(self.spec.as_bytes());
        hasher.update(b"|");
        hasher.update(self.record_id.as_bytes());
        hasher.update(b"|");
        hasher.update(self.subject_receipt.as_bytes());
        hasher.update(b"|");
        hasher.update(self.subject_spec.as_bytes());
        hasher.update(b"|");
        hasher.update([u8::from(self.subject_verified)]);
        hasher.update(b"|");
        hasher.update(self.outcome.as_bytes());
        hasher.update(b"|");
        if let Some(corrected) = &self.corrected_route {
            hasher.update(corrected.as_bytes());
        }
        hasher.update(b"|");
        if let Some(note) = &self.note {
            hasher.update(note.as_bytes());
        }
        hasher.update(b"|");
        hasher.update(self.tenant_id.as_bytes());
        hasher.update(b"|");
        hasher.update(self.session_id.as_bytes());
        hasher.update(b"|");
        hasher.update(self.recorded_at_ms.to_le_bytes());
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

/// Record an outcome for a subject receipt: sign it, write a sidecar next to
/// the receipt, and append it to `<store>/receipts/outcomes.jsonl`.
pub fn record_outcome(args: &Value, store_path: &Path, readonly: bool) -> Result<Value, String> {
    if readonly {
        return Err("read-only mode: decision.outcome refused".to_string());
    }
    let receipt_path = args
        .get("receipt_path")
        .and_then(Value::as_str)
        .ok_or("missing required field 'receipt_path'")?;
    let receipt_path = PathBuf::from(receipt_path);
    let raw = std::fs::read_to_string(&receipt_path).map_err(|e| format!("receipt read: {e}"))?;
    let subject: Value = serde_json::from_str(&raw).map_err(|e| format!("receipt parse: {e}"))?;
    let subject_receipt = subject
        .get("receipt_id")
        .and_then(Value::as_str)
        .unwrap_or("unknown")
        .to_string();
    let subject_spec = subject
        .get("spec")
        .and_then(Value::as_str)
        .unwrap_or("unknown")
        .to_string();

    let subject_verified = if subject_spec.contains('#') {
        verify_receipt_file(&receipt_path, store_path)
            .map(|report| report["valid"].as_bool().unwrap_or(false))
            .unwrap_or(false)
    } else {
        false
    };

    let (signing_key, _) = resolve_or_create_mandala_gate_key(store_path)
        .map_err(|e| format!("gate key error: {e}"))?;
    let gate_did = format!(
        "did:key:{}",
        signing_key
            .verifying_key()
            .to_bytes()
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    );

    let mut record = OutcomeRecord::new(
        subject_receipt.clone(),
        subject_spec,
        subject_verified,
        args,
        gate_did,
    )?;
    record.sign(&signing_key);
    record
        .verify(&signing_key.verifying_key())
        .map_err(|e| format!("outcome self-verification failed: {e}"))?;

    let receipts_dir = store_path.join("receipts");
    std::fs::create_dir_all(&receipts_dir).map_err(|e| format!("receipt dir: {e}"))?;
    let sidecar = PathBuf::from(format!("{}.outcome.json", receipt_path.display()));
    let serialized =
        serde_json::to_string_pretty(&record).map_err(|e| format!("outcome serialize: {e}"))?;
    std::fs::write(&sidecar, &serialized).map_err(|e| format!("outcome write: {e}"))?;

    let journal = receipts_dir.join("outcomes.jsonl");
    let journal_line =
        serde_json::to_string(&record).map_err(|e| format!("outcome serialize: {e}"))?;
    use std::io::Write;
    let mut file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&journal)
        .map_err(|e| format!("outcomes journal open: {e}"))?;
    file.write_all(journal_line.as_bytes())
        .and_then(|_| file.write_all(b"\n"))
        .map_err(|e| format!("outcomes journal write: {e}"))?;

    Ok(json!({
        "status": "success",
        "outcome": record,
        "sidecar_path": sidecar.display().to_string(),
        "journal_path": journal.display().to_string(),
    }))
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

    #[test]
    fn outcome_sign_and_verify_roundtrip() {
        let args =
            json!({"outcome": "success", "corrected_route": "memory.search", "note": "gold match"});
        let mut record = OutcomeRecord::new(
            "abc".to_string(),
            "continuity-receipt/0.5#shortlist".to_string(),
            true,
            &args,
            "did:key:test".to_string(),
        )
        .expect("record builds");
        let key = SigningKey::from_bytes(&[7u8; 32]);
        record.sign(&key);
        record.verify(&key.verifying_key()).expect("verifies");
        record.outcome = "failure".to_string();
        assert!(record.verify(&key.verifying_key()).is_err());
    }

    #[test]
    fn verify_receipt_file_reports_missing() {
        let result = verify_receipt_file(
            Path::new("/tmp/opencode/no-such-receipt.json"),
            Path::new("/tmp/opencode/no-such-store"),
        );
        assert!(result.is_err());
    }
}
