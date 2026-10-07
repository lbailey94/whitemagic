//! Offline verification for signed Gen3 receipts, plus outcome backfill.
//!
//! `verify_receipt_file` checks supported WhiteMagic receipt profiles against
//! the store's Mandala gate key without touching the substrate. These are
//! dedicated WM profiles, not a general Continuity Receipt verifier.
//! `record_outcome` signs an outcome for a subject receipt and journals it to
//! `<store>/receipts/outcomes.jsonl` for the learning loop; the signed record
//! carries the subject margin and the success assertion so calibration is not
//! inert. `gate_key_fingerprint` reports the store gate key's SHA-256
//! fingerprint and `did:key` form without creating or mutating anything.

use std::io::Read;
use std::path::{Path, PathBuf};

use serde::de::{MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer, Serialize};
use serde_json::{Map, Value, json};
use sha2::{Digest, Sha256};
use wm_gen3_core::mandala::{
    Signature, Signer, SigningKey, Verifier, VerifyingKey, resolve_or_create_mandala_gate_key,
};

const MAX_RECEIPT_FILE_BYTES: u64 = 8 * 1024 * 1024;

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

/// Fingerprint the store's existing Mandala gate key without creating one.
///
/// Returns `(fingerprint, did)` where the fingerprint is the lower-case hex
/// SHA-256 of the raw bytes stored in `mandala_gate_key.bin`, and the DID is
/// the Ed25519 `did:key` form (multicodec prefix `0xed01` + public key,
/// multibase base58btc with the `z` prefix). Read-only: errors clearly when
/// the key file is missing, unreadable, or not exactly 32 bytes.
pub fn gate_key_fingerprint(store_path: &Path) -> Result<(String, String), String> {
    let key_path = store_path.join("mandala_gate_key.bin");
    let bytes = std::fs::read(&key_path)
        .map_err(|e| format!("gate key read ({}): {e}", key_path.display()))?;
    if bytes.len() != 32 {
        return Err(format!("gate key must be 32 bytes, got {}", bytes.len()));
    }
    let fingerprint = hex_encode(&Sha256::digest(&bytes));
    let mut array = [0u8; 32];
    array.copy_from_slice(&bytes);
    let public_key = SigningKey::from_bytes(&array).verifying_key().to_bytes();
    Ok((fingerprint, ed25519_did_key(&public_key)))
}

/// Encode an Ed25519 public key as `did:key:z...` (multicodec `0xed01`).
fn ed25519_did_key(public_key: &[u8; 32]) -> String {
    let mut multicodec = Vec::with_capacity(34);
    multicodec.extend_from_slice(&[0xed, 0x01]);
    multicodec.extend_from_slice(public_key);
    format!("did:key:z{}", base58btc_encode(&multicodec))
}

/// Base58btc encode (Bitcoin alphabet), as used by `did:key` multibase.
fn base58btc_encode(input: &[u8]) -> String {
    const ALPHABET: &[u8; 58] = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
    let leading_zeros = input.iter().take_while(|&&byte| byte == 0).count();
    let mut digits: Vec<u8> = Vec::new();
    for &byte in &input[leading_zeros..] {
        let mut carry = u32::from(byte);
        for digit in &mut digits {
            carry += u32::from(*digit) << 8;
            *digit = (carry % 58) as u8;
            carry /= 58;
        }
        while carry > 0 {
            digits.push((carry % 58) as u8);
            carry /= 58;
        }
    }
    let mut encoded = String::with_capacity(leading_zeros + digits.len());
    for _ in 0..leading_zeros {
        encoded.push('1');
    }
    for &digit in digits.iter().rev() {
        encoded.push(char::from(ALPHABET[usize::from(digit)]));
    }
    encoded
}

/// Verify a supported signed WhiteMagic profile receipt against the store's gate key.
pub fn verify_receipt_file(path: &Path, store_path: &Path) -> Result<Value, String> {
    let file = std::fs::File::open(path).map_err(|e| format!("receipt read: {e}"))?;
    let mut raw = Vec::new();
    file.take(MAX_RECEIPT_FILE_BYTES + 1)
        .read_to_end(&mut raw)
        .map_err(|e| format!("receipt read: {e}"))?;
    if raw.len() as u64 > MAX_RECEIPT_FILE_BYTES {
        return Err(format!(
            "receipt exceeds {} byte limit",
            MAX_RECEIPT_FILE_BYTES
        ));
    }
    let value = parse_strict_json(
        std::str::from_utf8(&raw).map_err(|e| format!("receipt encoding: {e}"))?,
    )?;
    verify_receipt_value(&value, store_path)
}

/// Parse JSON while rejecting duplicate object members at every depth.
pub fn parse_strict_json(raw: &str) -> Result<Value, String> {
    let mut deserializer = serde_json::Deserializer::from_str(raw);
    let StrictJson(value) =
        StrictJson::deserialize(&mut deserializer).map_err(|e| format!("JSON parse: {e}"))?;
    deserializer.end().map_err(|e| format!("JSON parse: {e}"))?;
    Ok(value)
}

/// JSON value deserializer that rejects duplicate object members at every depth.
struct StrictJson(Value);

impl<'de> Deserialize<'de> for StrictJson {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct StrictVisitor;
        impl<'de> Visitor<'de> for StrictVisitor {
            type Value = StrictJson;
            fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                formatter.write_str("a JSON value without duplicate object members")
            }
            fn visit_unit<E: serde::de::Error>(self) -> Result<Self::Value, E> {
                Ok(StrictJson(Value::Null))
            }
            fn visit_none<E: serde::de::Error>(self) -> Result<Self::Value, E> {
                self.visit_unit()
            }
            fn visit_bool<E: serde::de::Error>(self, value: bool) -> Result<Self::Value, E> {
                Ok(StrictJson(Value::Bool(value)))
            }
            fn visit_i64<E: serde::de::Error>(self, value: i64) -> Result<Self::Value, E> {
                Ok(StrictJson(Value::Number(value.into())))
            }
            fn visit_u64<E: serde::de::Error>(self, value: u64) -> Result<Self::Value, E> {
                Ok(StrictJson(Value::Number(value.into())))
            }
            fn visit_f64<E: serde::de::Error>(self, value: f64) -> Result<Self::Value, E> {
                serde_json::Number::from_f64(value)
                    .map(|number| StrictJson(Value::Number(number)))
                    .ok_or_else(|| E::custom("non-finite JSON number"))
            }
            fn visit_str<E: serde::de::Error>(self, value: &str) -> Result<Self::Value, E> {
                Ok(StrictJson(Value::String(value.to_owned())))
            }
            fn visit_string<E: serde::de::Error>(self, value: String) -> Result<Self::Value, E> {
                Ok(StrictJson(Value::String(value)))
            }
            fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<Self::Value, A::Error> {
                let mut values = Vec::new();
                while let Some(StrictJson(value)) = seq.next_element()? {
                    values.push(value);
                }
                Ok(StrictJson(Value::Array(values)))
            }
            fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Self::Value, A::Error> {
                let mut values = Map::new();
                while let Some((key, StrictJson(value))) = map.next_entry::<String, StrictJson>()? {
                    if values.insert(key.clone(), value).is_some() {
                        return Err(serde::de::Error::custom(format!(
                            "duplicate object member '{key}'"
                        )));
                    }
                }
                Ok(StrictJson(Value::Object(values)))
            }
        }
        deserializer.deserialize_any(StrictVisitor)
    }
}

/// Verify one parsed receipt using the same pinned-key and exact-field rules as file input.
pub fn verify_receipt_value(value: &Value, store_path: &Path) -> Result<Value, String> {
    let object = value
        .as_object()
        .ok_or_else(|| "receipt must be a JSON object".to_string())?;
    let spec = value
        .get("spec")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_string();
    if spec.is_empty() {
        return Err("receipt has no 'spec' field".to_string());
    }
    let profile = match spec.as_str() {
        "continuity-receipt/0.5#decision" => "decision",
        "continuity-receipt/0.5#shortlist" => "shortlist",
        "continuity-receipt/1.5#deliberation" => "deliberation-v1",
        "continuity-receipt/1.5#deliberation.v2" => "deliberation-v2",
        "continuity-receipt/0.5#outcome" => "outcome",
        "continuity-receipt/2#consultation" => "consultation",
        _ => return Err(format!("unsupported receipt spec: {spec}")),
    };
    check_exact_fields(object, profile)?;
    check_unambiguous_signed_fields(object, profile)?;
    check_signature_format(object)?;
    let key = load_verifying_key(store_path)?;
    let expected_did = format!(
        "did:key:{}",
        key.to_bytes()
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>()
    );
    let issuer_did = value
        .get("issuer_did")
        .and_then(Value::as_str)
        .ok_or_else(|| "receipt has no string issuer_did".to_string())?;
    if issuer_did != expected_did {
        return Err(format!(
            "issuer_did mismatch: expected {expected_did}, got {issuer_did}"
        ));
    }

    let result = verify_profile(value, &key, profile);
    result.map_err(|e| format!("receipt verification refused: {e}"))?;
    let (signature_scope, unauthenticated_fields, numeric_projection, scope_notes) = match profile {
        "deliberation-v1" => (
            "continuity-receipt/1.5#deliberation legacy canonical_payload_v1",
            vec![
                "latency_ms",
                "degraded",
                "slm_model_sha256",
                "prompt_version",
                "layer",
            ],
            vec![
                "margin_prior, conformal_tau, and confidence are formatted to six decimal places in the signed payload",
            ],
            vec![
                "inquiry text is checked against the signed inquiry_digest; issuer_did and spec are checked by local key pinning and exact profile dispatch; listed fields are not included in the v1 signature",
            ],
        ),
        "deliberation-v2" => (
            "continuity-receipt/1.5#deliberation.v2 canonical_payload_v2",
            vec!["latency_ms", "layer"],
            vec![
                "margin_prior, conformal_tau, and confidence are formatted to six decimal places in the signed payload",
            ],
            vec![
                "inquiry text is checked against the signed inquiry_digest; issuer_did and spec are checked by local key pinning and exact profile dispatch; listed fields are not included in the v2 signature",
            ],
        ),
        "consultation" => (
            "continuity-receipt/2#consultation canonical_payload",
            vec!["spec", "issuer_did"],
            vec!["latency_ms is formatted to three decimal places in the signed payload"],
            vec![
                "spec is fixed by receipt dispatch and issuer_did is pinned to the local gate key; model and endpoint are signed configuration labels, not independent attestations of the executing model or endpoint; question and response content are not present to recompute their signed digests",
            ],
        ),
        "decision" => (
            "continuity-receipt/0.5#decision canonical_signing_bytes",
            vec![],
            vec!["numeric fields use their exact encoded bit or integer representation"],
            vec![
                "signature authenticates issuer assertions and claimed state, candidate, and decision digests; source bytes are unavailable, so those digests are not recomputed and decision correctness is not assessed",
            ],
        ),
        "shortlist" => (
            "continuity-receipt/0.5#shortlist canonical_signing_bytes",
            vec![],
            vec!["confidence, margin, and latency use their exact encoded bit representation"],
            vec![
                "signature authenticates issuer assertions and claimed state, candidate, and shortlist digests; source bytes are unavailable, so those digests are not recomputed and ranking correctness is not assessed",
            ],
        ),
        "outcome" => (
            "continuity-receipt/0.5#outcome canonical_signing_bytes",
            vec![],
            vec![
                "recorded_at_ms uses its exact integer representation",
                "margin is signed via its exact f64 bit representation",
            ],
            vec![
                "signature authenticates the local issuer's outcome assertion only; the referenced subject receipt is not verified here and subject_verified or outcome truth is not independently established; signed margin and success are issuer assertions, not independently measured",
            ],
        ),
        _ => unreachable!("profile was matched above"),
    };

    Ok(json!({
        "status": "success",
        "valid": true,
        "profile": profile,
        "spec": spec,
        "receipt_id": value.get("receipt_id"),
        "issuer_did": value.get("issuer_did"),
        "detail": (),
        "verified_offline": true,
        "signature_scope": signature_scope,
        "unauthenticated_fields": unauthenticated_fields,
        "numeric_projection": numeric_projection,
        "scope_notes": scope_notes,
    }))
}

fn check_signature_format(object: &Map<String, Value>) -> Result<(), String> {
    let signature = object
        .get("signature")
        .and_then(Value::as_str)
        .ok_or_else(|| "receipt has no string signature".to_string())?;
    if signature.len() != 128 || !signature.is_ascii() {
        return Err("signature must be exactly 128 ASCII hex characters".to_string());
    }
    if !signature.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err("signature contains non-hex ASCII characters".to_string());
    }
    Ok(())
}

fn check_exact_fields(object: &Map<String, Value>, profile: &str) -> Result<(), String> {
    let allowed: &[&str] = match profile {
        "decision" => &[
            "spec",
            "receipt_id",
            "tenant_id",
            "session_id",
            "timestamp_ms",
            "state_digest",
            "candidate_set_digest",
            "candidate_set_version",
            "task_class",
            "decision_digest",
            "chosen",
            "confidence",
            "act_probability",
            "model_id",
            "policy_version",
            "latency_ms",
            "issuer_did",
            "signature",
        ],
        "shortlist" => &[
            "spec",
            "receipt_id",
            "tenant_id",
            "session_id",
            "timestamp_ms",
            "state_digest",
            "candidate_set_digest",
            "shortlist_digest",
            "gate",
            "top1",
            "confidence",
            "margin",
            "task_class",
            "model_id",
            "policy_version",
            "latency_ms",
            "issuer_did",
            "signature",
        ],
        "deliberation-v1" => &[
            "spec",
            "receipt_id",
            "timestamp_ms",
            "inquiry",
            "inquiry_digest",
            "candidates",
            "chosen_route",
            "margin_prior",
            "conformal_tau",
            "confidence",
            "latency_ms",
            "degraded",
            "slm_model_sha256",
            "prompt_version",
            "layer",
            "issuer_did",
            "signature",
        ],
        "deliberation-v2" => &[
            "spec",
            "receipt_id",
            "timestamp_ms",
            "inquiry",
            "inquiry_digest",
            "candidates",
            "chosen_route",
            "margin_prior",
            "conformal_tau",
            "confidence",
            "latency_ms",
            "degraded",
            "slm_model_sha256",
            "prompt_version",
            "layer",
            "issuer_did",
            "signature",
        ],
        "outcome" => &[
            "spec",
            "record_id",
            "subject_receipt",
            "subject_spec",
            "subject_verified",
            "outcome",
            "margin",
            "success",
            "corrected_route",
            "note",
            "tenant_id",
            "session_id",
            "recorded_at_ms",
            "issuer_did",
            "signature",
        ],
        "consultation" => &[
            "spec",
            "receipt_id",
            "timestamp_ms",
            "question_digest",
            "response_digest",
            "model",
            "endpoint",
            "prompt_version",
            "max_tokens",
            "latency_ms",
            "issuer_did",
            "signature",
        ],
        _ => return Err(format!("unsupported receipt profile: {profile}")),
    };
    if let Some(field) = object
        .keys()
        .find(|field| !allowed.contains(&field.as_str()))
    {
        return Err(format!("unknown field '{field}' for {profile}"));
    }
    Ok(())
}

/// Refuse values that the existing delimiter-concatenated wire format cannot
/// uniquely represent. Producer encodings remain unchanged for compatibility.
fn check_unambiguous_signed_fields(
    object: &Map<String, Value>,
    profile: &str,
) -> Result<(), String> {
    let signed_strings: &[&str] = match profile {
        "decision" => &[
            "spec",
            "receipt_id",
            "tenant_id",
            "session_id",
            "state_digest",
            "candidate_set_digest",
            "decision_digest",
            "policy_version",
            "issuer_did",
        ],
        "shortlist" => &[
            "spec",
            "receipt_id",
            "tenant_id",
            "session_id",
            "state_digest",
            "candidate_set_digest",
            "shortlist_digest",
            "gate",
            "policy_version",
            "issuer_did",
        ],
        "deliberation-v1" => &["receipt_id", "inquiry_digest", "chosen_route"],
        "deliberation-v2" => &[
            "receipt_id",
            "inquiry_digest",
            "chosen_route",
            "slm_model_sha256",
            "prompt_version",
        ],
        "outcome" => &[
            "spec",
            "record_id",
            "subject_receipt",
            "subject_spec",
            "outcome",
            "tenant_id",
            "session_id",
            "issuer_did",
        ],
        "consultation" => &[
            "receipt_id",
            "question_digest",
            "response_digest",
            "model",
            "endpoint",
            "prompt_version",
        ],
        _ => return Err(format!("unsupported receipt profile: {profile}")),
    };
    for field in signed_strings {
        if let Some(value) = object.get(*field).and_then(Value::as_str)
            && value.contains('|')
        {
            return Err(format!(
                "signed field '{field}' contains an unsafe '|' delimiter"
            ));
        }
    }

    let optional_strings: &[&str] = match profile {
        "decision" => &["candidate_set_version", "task_class", "model_id"],
        "shortlist" => &["top1", "task_class", "model_id"],
        "outcome" => &["corrected_route", "note"],
        _ => &[],
    };
    for field in optional_strings {
        if let Some(value) = object.get(*field).and_then(Value::as_str) {
            if value.is_empty() {
                return Err(format!("optional signed field '{field}' cannot be empty"));
            }
            if value.contains('|') {
                return Err(format!(
                    "signed field '{field}' contains an unsafe '|' delimiter"
                ));
            }
        }
    }

    if profile == "decision" {
        for field in ["chosen", "confidence", "act_probability"] {
            if let Some(value) = object.get(field)
                && value.to_string().contains('|')
            {
                return Err(format!(
                    "serialized optional signed field '{field}' contains an unsafe '|' delimiter"
                ));
            }
        }
    }
    if profile == "outcome" {
        if let Some(margin) = object.get("margin") {
            let value = margin
                .as_f64()
                .ok_or_else(|| "outcome field 'margin' must be a JSON number".to_string())?;
            if !value.is_finite() {
                return Err("outcome field 'margin' must be finite".to_string());
            }
        }
        if let Some(success) = object.get("success")
            && !success.is_boolean()
        {
            return Err("outcome field 'success' must be a JSON boolean".to_string());
        }
    }
    if profile.starts_with("deliberation-") {
        let candidates = object
            .get("candidates")
            .and_then(Value::as_array)
            .ok_or_else(|| "deliberation candidates must be an array".to_string())?;
        for (index, candidate) in candidates.iter().enumerate() {
            let name = candidate
                .as_str()
                .ok_or_else(|| format!("deliberation candidate {index} must be a string"))?;
            if name.is_empty() || name.contains(',') || name.contains('|') {
                return Err(format!(
                    "deliberation candidate {index} has an ambiguous delimiter or empty name"
                ));
            }
        }
    }
    Ok(())
}

fn verify_profile(value: &Value, key: &VerifyingKey, profile: &str) -> Result<(), String> {
    match profile {
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
        "deliberation-v1" | "deliberation-v2" => {
            serde_json::from_value::<crate::deliberation::DeliberationReceipt>(value.clone())
                .map_err(|e| e.to_string())
                .and_then(|receipt| {
                    receipt.verify()?;
                    let mut hasher = Sha256::new();
                    hasher.update(receipt.inquiry.as_bytes());
                    let actual_digest = format!("{:x}", hasher.finalize());
                    if receipt.inquiry_digest != actual_digest {
                        return Err("inquiry text does not match signed inquiry_digest".to_string());
                    }
                    let expected_spec = if profile == "deliberation-v1" {
                        crate::deliberation::DELIBERATION_SPEC_V1
                    } else {
                        crate::deliberation::DELIBERATION_SPEC
                    };
                    if receipt.spec != expected_spec {
                        return Err(format!("spec/profile mismatch: expected {expected_spec}"));
                    }
                    Ok(())
                })
        }
        "consultation" => {
            serde_json::from_value::<crate::systemtwo::ConsultationReceipt>(value.clone())
                .map_err(|e| e.to_string())
                .and_then(|receipt| receipt.verify())
        }
        "outcome" => serde_json::from_value::<OutcomeRecord>(value.clone())
            .map_err(|e| e.to_string())
            .and_then(|record| record.verify(key)),
        _ => Err(format!("unsupported receipt profile: {profile}")),
    }
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
    /// Subject's top1-top2 margin (shortlist `margin` or deliberation
    /// `margin_prior`), signed when the subject exposes it.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub margin: Option<f64>,
    /// Issuer's success assertion derived from the recorded outcome value.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub success: Option<bool>,
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
    pub fn new(
        subject_receipt: String,
        subject_spec: String,
        subject_verified: bool,
        margin: Option<f64>,
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
            margin: margin.filter(|value| value.is_finite()),
            success: Some(outcome == "success"),
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
        // Optional calibration fields are appended only when present so that
        // outcome records signed before they existed remain verifiable.
        if let Some(margin) = self.margin {
            hasher.update(b"|margin:");
            hasher.update(margin.to_bits().to_le_bytes());
        }
        if let Some(success) = self.success {
            hasher.update(b"|success:");
            hasher.update([u8::from(success)]);
        }
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

/// Subject top1-top2 margin: shortlist `margin` or deliberation `margin_prior`.
///
/// Callers must only sign or calibrate on this value after the subject receipt
/// verified against the store gate key.
fn subject_margin(subject: &Value) -> Option<f64> {
    subject
        .get("margin")
        .and_then(Value::as_f64)
        .or_else(|| subject.get("margin_prior").and_then(Value::as_f64))
        .filter(|margin| margin.is_finite())
}

/// A verified calibration sample extracted from one outcomes journal line.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct VerifiedOutcome {
    /// Signed margin from the outcome receipt or its verified subject.
    pub margin: f64,
    /// Signed (receipt) or corroborated (reference line) success assertion.
    pub success: bool,
}

/// Why an outcomes journal line yielded no calibration sample.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutcomeLineSkip {
    /// Malformed, unsigned, bad-signature, or with no verifiable subject.
    Unverified,
    /// The line verified but carries no signed margin (legacy record).
    NoMargin,
}

/// Verify one `outcomes.jsonl` line and extract its signed calibration sample.
///
/// A line is accepted only when it is a signed outcome receipt that verifies
/// against the store's gate key, or when it references a subject receipt that
/// verifies. Margins are never read from unauthenticated lines: a reference
/// line takes the margin from the verified subject receipt, never from itself.
pub fn verified_outcome_sample(
    line: &str,
    store_path: &Path,
) -> Result<VerifiedOutcome, OutcomeLineSkip> {
    let value: Value = serde_json::from_str(line).map_err(|_| OutcomeLineSkip::Unverified)?;
    let is_receipt = value.get("spec").is_some() || value.get("signature").is_some();
    if is_receipt {
        let report =
            verify_receipt_value(&value, store_path).map_err(|_| OutcomeLineSkip::Unverified)?;
        if report["valid"].as_bool() != Some(true) {
            return Err(OutcomeLineSkip::Unverified);
        }
        let margin = value
            .get("margin")
            .and_then(Value::as_f64)
            .filter(|margin| margin.is_finite())
            .ok_or(OutcomeLineSkip::NoMargin)?;
        let success = value
            .get("success")
            .and_then(Value::as_bool)
            .unwrap_or(true);
        return Ok(VerifiedOutcome { margin, success });
    }

    // Reference line: not itself signed, so require a verifiable subject
    // receipt and take the margin from that signed receipt.
    let reference = value
        .get("subject_receipt")
        .and_then(Value::as_str)
        .or_else(|| value.get("subject_path").and_then(Value::as_str))
        .ok_or(OutcomeLineSkip::Unverified)?;
    let subject_path =
        resolve_subject_receipt(store_path, reference).ok_or(OutcomeLineSkip::Unverified)?;
    let subject_report =
        verify_receipt_file(&subject_path, store_path).map_err(|_| OutcomeLineSkip::Unverified)?;
    if subject_report["valid"].as_bool() != Some(true) {
        return Err(OutcomeLineSkip::Unverified);
    }
    let subject_raw =
        std::fs::read_to_string(&subject_path).map_err(|_| OutcomeLineSkip::Unverified)?;
    let subject: Value =
        serde_json::from_str(&subject_raw).map_err(|_| OutcomeLineSkip::Unverified)?;
    let margin = subject_margin(&subject).ok_or(OutcomeLineSkip::NoMargin)?;
    let success = value
        .get("success")
        .and_then(Value::as_bool)
        .or_else(|| {
            value
                .get("outcome")
                .and_then(Value::as_str)
                .map(|outcome| outcome == "success")
        })
        .ok_or(OutcomeLineSkip::Unverified)?;
    Ok(VerifiedOutcome { margin, success })
}

/// Resolve a journal reference to a receipt file inside `<store>/receipts`.
///
/// Only file names are honored (never `..` or absolute traversal); a bare
/// receipt id matches `<id>.json` or any `*-<id>.json` in the receipts dir.
fn resolve_subject_receipt(store_path: &Path, reference: &str) -> Option<PathBuf> {
    let receipts_dir = store_path.join("receipts");
    let file_name = Path::new(reference).file_name()?.to_str()?;
    if file_name.is_empty() {
        return None;
    }
    let direct = receipts_dir.join(file_name);
    if direct.is_file() {
        return Some(direct);
    }
    let exact = format!("{reference}.json");
    let suffix = format!("-{reference}.json");
    let mut matches: Vec<PathBuf> = std::fs::read_dir(&receipts_dir)
        .ok()?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name == exact || name.ends_with(&suffix))
        })
        .collect();
    matches.sort();
    matches.into_iter().next()
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
    if !subject_spec.contains('#') {
        return Err(format!(
            "subject receipt spec '{subject_spec}' has no '#profile' segment; \
             refusing to record an outcome for an unverifiable subject"
        ));
    }

    let subject_verified = verify_receipt_file(&receipt_path, store_path)
        .map(|report| report["valid"].as_bool().unwrap_or(false))
        .unwrap_or(false);
    // Only a verified subject receipt may contribute a signed margin; an
    // unverified subject file is attacker-controlled calibration input.
    let margin = if subject_verified {
        subject_margin(&subject)
    } else {
        None
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
        margin,
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

    let margin_omitted_reason = if record.margin.is_some() {
        None
    } else if !subject_verified {
        Some("subject_unverified")
    } else {
        Some("subject_lacks_signed_margin")
    };

    Ok(json!({
        "status": "success",
        "outcome": record,
        "margin_omitted_reason": margin_omitted_reason,
        "sidecar_path": sidecar.display().to_string(),
        "journal_path": journal.display().to_string(),
    }))
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn hex_decode(hex: &str) -> Option<Vec<u8>> {
    if !hex.is_ascii() || hex.len() % 2 != 0 {
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
    #[cfg(feature = "systemone")]
    use crate::decision_receipt::DecisionReceipt;
    use crate::deliberation::DeliberationReceipt;
    #[cfg(feature = "system05")]
    use crate::shortlist_receipt::ShortlistReceipt;
    use crate::systemtwo::{ConsultationReceipt, SystemTwoAnswer};
    use serde_json::json;

    fn fixture_store(key: &SigningKey) -> PathBuf {
        let path = std::env::temp_dir().join(format!("wm-receipt-verify-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir(&path).expect("create fixture store");
        std::fs::write(path.join("mandala_gate_key.bin"), key.to_bytes())
            .expect("write pinned key");
        path
    }

    fn signed_deliberation_subject(key: &SigningKey, path: &Path, margin_prior: f64) {
        let receipt = DeliberationReceipt::sign(
            key,
            "route this calibration fixture",
            &["memory.search".into(), "memory.create".into()],
            "memory.search",
            margin_prior,
            0.05,
            0.9,
            1.5,
            false,
            "model-sha256",
            "deliberation-prompt-v2",
        );
        std::fs::write(
            path,
            serde_json::to_vec(&receipt).expect("serialize subject"),
        )
        .expect("write subject receipt");
    }

    #[test]
    fn outcome_sign_and_verify_roundtrip() {
        let args =
            json!({"outcome": "success", "corrected_route": "memory.search", "note": "gold match"});
        let mut record = OutcomeRecord::new(
            "abc".to_string(),
            "continuity-receipt/0.5#shortlist".to_string(),
            true,
            Some(0.25),
            &args,
            "did:key:test".to_string(),
        )
        .expect("record builds");
        let key = SigningKey::from_bytes(&[7u8; 32]);
        record.sign(&key);
        record.verify(&key.verifying_key()).expect("verifies");
        assert_eq!(record.margin, Some(0.25));
        assert_eq!(record.success, Some(true));
        record.outcome = "failure".to_string();
        assert!(record.verify(&key.verifying_key()).is_err());
    }

    #[test]
    fn outcome_direct_verifier_rejects_unicode_and_ascii_nonhex_without_panicking() {
        let key = SigningKey::from_bytes(&[8u8; 32]);
        let args = json!({"outcome":"success"});
        let mut record = OutcomeRecord::new(
            "subject".into(),
            "continuity-receipt/0.5#decision".into(),
            true,
            None,
            &args,
            "did:key:test".into(),
        )
        .expect("record builds");
        record.sign(&key);
        record.signature = Some("😀".repeat(32));
        assert!(record.verify(&key.verifying_key()).is_err());
        record.signature = Some("g".repeat(128));
        assert!(record.verify(&key.verifying_key()).is_err());
    }

    #[test]
    fn healthy_outcome_producer_verifies_through_shared_profile_dispatch() {
        let key = SigningKey::from_bytes(&[18u8; 32]);
        let store = fixture_store(&key);
        let args = json!({"outcome":"success", "note":"observed locally"});
        let issuer_did = format!("did:key:{}", hex_encode(&key.verifying_key().to_bytes()));
        let mut record = OutcomeRecord::new(
            "subject-id".into(),
            "continuity-receipt/0.5#decision".into(),
            true,
            None,
            &args,
            issuer_did,
        )
        .expect("outcome receipt");
        record.sign(&key);
        assert_eq!(
            verify_receipt_value(&serde_json::to_value(record).unwrap(), &store).unwrap()["profile"],
            "outcome"
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[cfg(feature = "systemone")]
    #[test]
    fn healthy_decision_producer_verifies_through_shared_profile_dispatch() {
        let key = SigningKey::from_bytes(&[19u8; 32]);
        let store = fixture_store(&key);
        let outcome = json!({"model":"local-policy", "latency_ms":1.25, "answers":{"q":{"type":"choice", "choice":"allow", "confidence":0.9}}});
        let state = json!({"request":"read local note"});
        let questions = json!({"q":{"type":"choice", "choices":["allow", "deny"]}});
        let args = json!({"tenant_id":"tenant-test", "session_id":"session-test"});
        let issuer_did = format!("did:key:{}", hex_encode(&key.verifying_key().to_bytes()));
        let mut receipt =
            DecisionReceipt::from_outcome(&outcome, &state, &questions, &args, issuer_did);
        receipt.sign(&key);
        let value = serde_json::to_value(&receipt).expect("serialize decision receipt");
        assert_eq!(
            verify_receipt_value(&value, &store).unwrap()["profile"],
            "decision"
        );
        let mut tampered = value;
        tampered["state_digest"] = json!("tampered");
        assert!(verify_receipt_value(&tampered, &store).is_err());
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[cfg(feature = "system05")]
    #[test]
    fn healthy_shortlist_producer_verifies_through_shared_profile_dispatch() {
        let key = SigningKey::from_bytes(&[20u8; 32]);
        let store = fixture_store(&key);
        let outcome = json!({"model":"local-ranker", "latency_ms":2.5, "ranked":[{"route":"memory.search", "score":0.8}], "top1":"memory.search", "confidence":0.8, "margin":0.4, "gate":"dispatch"});
        let state = json!("find the red note");
        let routes = json!({"memory.search":"Search memories"});
        let args = json!({"tenant_id":"tenant-test", "session_id":"session-test"});
        let issuer_did = format!("did:key:{}", hex_encode(&key.verifying_key().to_bytes()));
        let mut receipt =
            ShortlistReceipt::from_outcome(&outcome, &state, &routes, &args, issuer_did);
        receipt.sign(&key);
        let value = serde_json::to_value(&receipt).expect("serialize shortlist receipt");
        assert_eq!(
            verify_receipt_value(&value, &store).unwrap()["profile"],
            "shortlist"
        );
        let mut tampered = value;
        tampered["gate"] = json!("defer");
        assert!(verify_receipt_value(&tampered, &store).is_err());
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn verify_receipt_file_reports_missing() {
        let result = verify_receipt_file(
            Path::new("/tmp/opencode/no-such-receipt.json"),
            Path::new("/tmp/opencode/no-such-store"),
        );
        assert!(result.is_err());
    }

    #[test]
    fn receipt_file_parser_rejects_duplicate_members() {
        let path = std::env::temp_dir().join(format!(
            "wm-receipt-duplicate-{}.json",
            uuid::Uuid::new_v4()
        ));
        std::fs::write(&path, br#"{"spec":"a","spec":"b"}"#).expect("write duplicate fixture");
        let result = verify_receipt_file(&path, Path::new("missing-store"));
        assert!(result.unwrap_err().contains("duplicate object member"));
        std::fs::remove_file(path).expect("cleanup duplicate fixture");
    }

    #[test]
    fn strict_json_parser_rejects_rpc_duplicate_members_before_value_collapse() {
        let raw = r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"arguments":{"bundle":{},"bundle":{"spec":"x"}}}}"#;
        assert!(
            parse_strict_json(raw)
                .unwrap_err()
                .contains("duplicate object member 'bundle'")
        );
    }

    #[test]
    fn public_deliberation_producer_verifies_file_and_rejects_tampering() {
        let key = SigningKey::from_bytes(&[41u8; 32]);
        let store = fixture_store(&key);
        let receipt = DeliberationReceipt::sign(
            &key,
            "choose | a route",
            &["memory.search".into(), "memory.create".into()],
            "memory.search",
            0.2,
            0.05,
            0.9,
            4.0,
            false,
            "model-sha256",
            "deliberation-prompt-v2",
        );
        let path = store.join("receipt.json");
        std::fs::write(&path, serde_json::to_vec(&receipt).expect("serialize"))
            .expect("write receipt");
        assert_eq!(
            verify_receipt_file(&path, &store).expect("verify file")["valid"],
            true
        );
        let mut value: Value =
            serde_json::from_slice(&std::fs::read(&path).expect("read receipt")).expect("parse");
        for malformed in ["😀".repeat(32), "g".repeat(128), "abc".to_string()] {
            let mut malformed_value = value.clone();
            malformed_value["signature"] = json!(malformed);
            assert!(verify_receipt_value(&malformed_value, &store).is_err());
        }
        value["chosen_route"] = json!("memory.create");
        assert!(verify_receipt_value(&value, &store).is_err());
        value["chosen_route"] = json!("memory.search");
        value["inquiry"] = json!("changed plain text");
        assert!(
            verify_receipt_value(&value, &store)
                .unwrap_err()
                .contains("inquiry text does not match")
        );
        value["inquiry"] = json!("choose | a route");
        value["latency_ms"] = json!(999.0);
        let scoped = verify_receipt_value(&value, &store).expect("unsigned latency is disclosed");
        assert!(
            scoped["unauthenticated_fields"]
                .as_array()
                .unwrap()
                .contains(&json!("latency_ms"))
        );
        value["latency_ms"] = json!(4.0);
        value["signature"] = json!("00");
        assert!(
            verify_receipt_value(&value, &store).is_err(),
            "malformed signature refused"
        );
        value["signature"] = json!(receipt.signature.clone());
        value["issuer_did"] = json!("did:key:unknown");
        assert!(
            verify_receipt_value(&value, &store)
                .unwrap_err()
                .contains("issuer_did mismatch")
        );
        value["issuer_did"] = json!(format!(
            "did:key:{}",
            hex_encode(&key.verifying_key().to_bytes())
        ));
        value["spec"] = json!("continuity-receipt/9#unknown");
        assert!(
            verify_receipt_value(&value, &store)
                .unwrap_err()
                .contains("unsupported receipt spec")
        );
        value["spec"] = json!(crate::deliberation::DELIBERATION_SPEC);
        value.as_object_mut().unwrap().remove("signature");
        assert!(
            verify_receipt_value(&value, &store).is_err(),
            "unsigned receipt refused"
        );
        value["signature"] = json!(receipt.signature.clone());
        value["unexpected"] = json!(true);
        assert!(
            verify_receipt_value(&value, &store)
                .unwrap_err()
                .contains("unknown field")
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn legacy_deliberation_v1_verifies_and_discloses_unsigned_fields() {
        let key = SigningKey::from_bytes(&[42u8; 32]);
        let store = fixture_store(&key);
        let receipt_id = "legacy-receipt";
        let inquiry = "legacy inquiry";
        let inquiry_digest = format!("{:x}", Sha256::digest(inquiry.as_bytes()));
        let candidates = vec!["memory.search".to_string(), "memory.create".to_string()];
        let chosen_route = "memory.search";
        let timestamp_ms = 1_700_000_000_000;
        let payload = DeliberationReceipt::canonical_payload_v1(
            receipt_id,
            &inquiry_digest,
            &candidates,
            chosen_route,
            0.2,
            0.05,
            0.9,
            timestamp_ms,
        );
        let signature = hex_encode(&key.sign(payload.as_bytes()).to_bytes());
        let receipt = DeliberationReceipt {
            spec: crate::deliberation::DELIBERATION_SPEC_V1.into(),
            receipt_id: receipt_id.into(),
            timestamp_ms,
            inquiry: inquiry.into(),
            inquiry_digest,
            candidates,
            chosen_route: chosen_route.into(),
            margin_prior: 0.2,
            conformal_tau: 0.05,
            confidence: 0.9,
            latency_ms: 5.0,
            degraded: true,
            slm_model_sha256: "legacy-unsigned-model".into(),
            prompt_version: "legacy-unsigned-prompt".into(),
            layer: "legacy-unsigned-layer".into(),
            issuer_did: format!("did:key:{}", hex_encode(&key.verifying_key().to_bytes())),
            signature,
        };
        let value = serde_json::to_value(receipt).expect("serialize legacy v1");
        let report = verify_receipt_value(&value, &store).expect("legacy v1 compatibility");
        assert_eq!(report["profile"], "deliberation-v1");
        for field in [
            "latency_ms",
            "degraded",
            "slm_model_sha256",
            "prompt_version",
            "layer",
        ] {
            assert!(
                report["unauthenticated_fields"]
                    .as_array()
                    .unwrap()
                    .contains(&json!(field))
            );
        }
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn public_consultation_producer_verifies_and_wrong_pinned_key_refuses() {
        let key = SigningKey::from_bytes(&[51u8; 32]);
        let store = fixture_store(&key);
        let answer = SystemTwoAnswer {
            content: "answer bytes".into(),
            model: "local-test".into(),
            endpoint: "http://127.0.0.1:11434/v1".into(),
            latency_ms: 8.25,
            max_tokens: 32,
            completion_tokens: Some(4),
        };
        let receipt = ConsultationReceipt::sign(&key, "question bytes", &answer);
        let value = serde_json::to_value(&receipt).expect("serialize");
        assert_eq!(
            verify_receipt_value(&value, &store).expect("verify")["valid"],
            true
        );
        let report = verify_receipt_value(&value, &store).expect("verification scope");
        assert!(
            report["scope_notes"][0]
                .as_str()
                .unwrap()
                .contains("configuration labels")
        );
        assert!(
            report["numeric_projection"][0]
                .as_str()
                .unwrap()
                .contains("three decimal places")
        );
        let mut tampered = value.clone();
        tampered["response_digest"] = json!("00");
        assert!(verify_receipt_value(&tampered, &store).is_err());
        let wrong_key = SigningKey::from_bytes(&[52u8; 32]);
        std::fs::write(store.join("mandala_gate_key.bin"), wrong_key.to_bytes())
            .expect("replace key");
        assert!(
            verify_receipt_value(&value, &store)
                .unwrap_err()
                .contains("issuer_did mismatch")
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn verifier_refuses_deliberation_candidate_join_collision() {
        let key = SigningKey::from_bytes(&[61u8; 32]);
        let store = fixture_store(&key);
        let receipt = DeliberationReceipt::sign(
            &key,
            "inquiry with | is digest-bound",
            &["a,b".into(), "c".into()],
            "chosen",
            0.4,
            0.1,
            0.8,
            1.0,
            false,
            "model",
            "prompt",
        );
        let mut colliding = receipt.clone();
        colliding.candidates = vec!["a".into(), "b,c".into()];
        assert_eq!(
            DeliberationReceipt::canonical_payload_v2(
                &receipt.receipt_id,
                &receipt.inquiry_digest,
                &receipt.candidates,
                &receipt.chosen_route,
                receipt.margin_prior,
                receipt.conformal_tau,
                receipt.confidence,
                receipt.degraded,
                &receipt.slm_model_sha256,
                &receipt.prompt_version,
                receipt.timestamp_ms,
            ),
            DeliberationReceipt::canonical_payload_v2(
                &colliding.receipt_id,
                &colliding.inquiry_digest,
                &colliding.candidates,
                &colliding.chosen_route,
                colliding.margin_prior,
                colliding.conformal_tau,
                colliding.confidence,
                colliding.degraded,
                &colliding.slm_model_sha256,
                &colliding.prompt_version,
                colliding.timestamp_ms,
            ),
            "distinct candidate boundaries collide in the legacy producer encoder"
        );
        colliding
            .verify()
            .expect("producer signature remains valid for alias");
        let value = serde_json::to_value(colliding).expect("serialize collision vector");
        assert!(
            verify_receipt_value(&value, &store)
                .unwrap_err()
                .contains("candidate 1")
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn verifier_refuses_consultation_delimiter_boundary_collision() {
        let key = SigningKey::from_bytes(&[62u8; 32]);
        let store = fixture_store(&key);
        let answer = SystemTwoAnswer {
            content: "answer".into(),
            model: "model-a|endpoint:model-b".into(),
            endpoint: "endpoint-b".into(),
            latency_ms: 2.0,
            max_tokens: 4,
            completion_tokens: Some(1),
        };
        let signed = ConsultationReceipt::sign(&key, "question", &answer);
        let mut colliding = signed.clone();
        colliding.model = "model-a".into();
        colliding.endpoint = "model-b|endpoint:endpoint-b".into();
        assert_eq!(
            ConsultationReceipt::canonical_payload(
                &signed.receipt_id,
                &signed.question_digest,
                &signed.response_digest,
                &signed.model,
                &signed.endpoint,
                &signed.prompt_version,
                signed.max_tokens,
                signed.latency_ms,
                signed.timestamp_ms,
            ),
            ConsultationReceipt::canonical_payload(
                &colliding.receipt_id,
                &colliding.question_digest,
                &colliding.response_digest,
                &colliding.model,
                &colliding.endpoint,
                &colliding.prompt_version,
                colliding.max_tokens,
                colliding.latency_ms,
                colliding.timestamp_ms,
            ),
            "distinct model/endpoint boundaries collide in the producer encoder"
        );
        colliding
            .verify()
            .expect("producer signature remains valid for alias");
        let value = serde_json::to_value(colliding).expect("serialize collision vector");
        assert!(
            verify_receipt_value(&value, &store)
                .unwrap_err()
                .contains("unsafe '|' delimiter")
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn verifier_refuses_empty_optional_string_alias() {
        let key = SigningKey::from_bytes(&[63u8; 32]);
        let store = fixture_store(&key);
        let args = json!({"outcome":"success", "note":""});
        let mut record = OutcomeRecord::new(
            "subject".into(),
            "continuity-receipt/0.5#decision".into(),
            true,
            None,
            &args,
            format!("did:key:{}", hex_encode(&key.verifying_key().to_bytes())),
        )
        .expect("outcome fixture");
        record.sign(&key);
        record
            .verify(&key.verifying_key())
            .expect("producer signature valid for Some empty");
        assert!(
            verify_receipt_value(&serde_json::to_value(record).unwrap(), &store)
                .unwrap_err()
                .contains("cannot be empty")
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn emitted_outcome_receipts_drive_calibration_tau() {
        let key = SigningKey::from_bytes(&[71u8; 32]);
        let store = fixture_store(&key);
        let gate = crate::deliberation::ConformalGate::new(0.95, 0.05);
        assert!((gate.calibrate_tau(&store) - 0.05).abs() < 1e-12);

        let success_subject = store.join("deliberation-success.json");
        let failure_subject = store.join("deliberation-failure.json");
        signed_deliberation_subject(&key, &success_subject, 0.5);
        signed_deliberation_subject(&key, &failure_subject, 0.01);

        for _ in 0..10 {
            let args = json!({
                "receipt_path": success_subject.display().to_string(),
                "outcome": "success",
            });
            let report = record_outcome(&args, &store, false).expect("emit success outcome");
            assert_eq!(report["outcome"]["subject_verified"], json!(true));
            assert_eq!(report["outcome"]["margin"].as_f64(), Some(0.5));
            assert_eq!(report["outcome"]["success"], json!(true));
        }
        for _ in 0..2 {
            let args = json!({
                "receipt_path": failure_subject.display().to_string(),
                "outcome": "failure",
            });
            let report = record_outcome(&args, &store, false).expect("emit failure outcome");
            assert_eq!(report["outcome"]["margin"].as_f64(), Some(0.01));
            assert_eq!(report["outcome"]["success"], json!(false));
        }

        let journal = std::fs::read_to_string(store.join("receipts").join("outcomes.jsonl"))
            .expect("read outcomes journal");
        assert_eq!(journal.lines().count(), 12);
        for line in journal.lines() {
            let value: Value = serde_json::from_str(line).expect("journal line parses");
            assert!(value.get("margin").is_some(), "margin must be signed");
            assert!(value.get("success").is_some(), "success must be signed");
            assert_eq!(
                verify_receipt_value(&value, &store).expect("journal outcome verifies")["valid"],
                true
            );
        }

        let report = gate.calibrate_tau_report(&store);
        assert_eq!(report.samples_used, 10);
        assert_eq!(report.lines_skipped_unverified, 0);
        assert_eq!(report.lines_skipped_no_margin, 0);
        assert!(!report.used_default_tau);
        assert!(
            (report.tau - 0.5).abs() < 1e-9,
            "calibration must honor signed margins and success filtering, got {}",
            report.tau
        );
        assert!((gate.calibrate_tau(&store) - report.tau).abs() < 1e-12);
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn unverified_subject_margin_is_not_signed() {
        let gate_key = SigningKey::from_bytes(&[78u8; 32]);
        let foreign_key = SigningKey::from_bytes(&[79u8; 32]);
        let store = fixture_store(&gate_key);
        let subject_path = store.join("foreign-subject.json");
        signed_deliberation_subject(&foreign_key, &subject_path, 0.99);
        let args = json!({
            "receipt_path": subject_path.display().to_string(),
            "outcome": "success",
        });
        let report = record_outcome(&args, &store, false).expect("record unverified outcome");
        assert_eq!(report["outcome"]["subject_verified"], json!(false));
        assert!(
            report["outcome"].get("margin").is_none(),
            "unverified subject margin must not be signed"
        );
        assert_eq!(report["outcome"]["success"], json!(true));
        assert_eq!(report["margin_omitted_reason"], json!("subject_unverified"));

        // The signed outcome still verifies, but carries no margin to calibrate on.
        let line = serde_json::to_string(&report["outcome"]).expect("serialize outcome");
        assert_eq!(
            verified_outcome_sample(&line, &store),
            Err(OutcomeLineSkip::NoMargin)
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn tampered_outcome_margin_and_success_fail_verification() {
        let key = SigningKey::from_bytes(&[72u8; 32]);
        let store = fixture_store(&key);
        let subject_path = store.join("deliberation-subject.json");
        signed_deliberation_subject(&key, &subject_path, 0.42);
        let args = json!({
            "receipt_path": subject_path.display().to_string(),
            "outcome": "success",
        });
        let report = record_outcome(&args, &store, false).expect("emit outcome");
        let record = report["outcome"].clone();
        let sidecar = PathBuf::from(report["sidecar_path"].as_str().expect("sidecar path"));
        assert_eq!(
            verify_receipt_file(&sidecar, &store).expect("sidecar verifies")["valid"],
            true
        );

        let mut tampered_margin = record.clone();
        tampered_margin["margin"] = json!(0.99);
        assert!(
            verify_receipt_value(&tampered_margin, &store).is_err(),
            "tampered margin must fail verification"
        );

        let mut tampered_success = record.clone();
        tampered_success["success"] = json!(false);
        assert!(
            verify_receipt_value(&tampered_success, &store).is_err(),
            "tampered success must fail verification"
        );

        let mut on_disk: Value =
            serde_json::from_slice(&std::fs::read(&sidecar).expect("read sidecar"))
                .expect("parse sidecar");
        on_disk["margin"] = json!(0.99);
        std::fs::write(
            &sidecar,
            serde_json::to_vec(&on_disk).expect("serialize tamper"),
        )
        .expect("write tampered sidecar");
        assert!(verify_receipt_file(&sidecar, &store).is_err());
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn legacy_outcome_without_margin_or_success_still_verifies() {
        let key = SigningKey::from_bytes(&[73u8; 32]);
        let store = fixture_store(&key);
        let mut legacy = OutcomeRecord {
            spec: "continuity-receipt/0.5#outcome".to_string(),
            record_id: "legacy-outcome".to_string(),
            subject_receipt: "subject".to_string(),
            subject_spec: "continuity-receipt/0.5#shortlist".to_string(),
            subject_verified: true,
            outcome: "success".to_string(),
            margin: None,
            success: None,
            corrected_route: None,
            note: None,
            tenant_id: "local".to_string(),
            session_id: "adhoc".to_string(),
            recorded_at_ms: 1_700_000_000_000,
            issuer_did: format!("did:key:{}", hex_encode(&key.verifying_key().to_bytes())),
            signature: None,
        };
        legacy.sign(&key);
        assert!(legacy.verify(&key.verifying_key()).is_ok());
        let value = serde_json::to_value(&legacy).expect("serialize legacy outcome");
        assert!(value.get("margin").is_none());
        assert!(value.get("success").is_none());
        assert_eq!(
            verify_receipt_value(&value, &store).expect("legacy outcome verifies")["valid"],
            true
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn outcome_flat_spec_subject_is_refused_explicitly() {
        let key = SigningKey::from_bytes(&[74u8; 32]);
        let store = fixture_store(&key);
        let flat_path = store.join("flat-subject.json");
        std::fs::write(
            &flat_path,
            serde_json::to_vec(&json!({
                "spec": "continuity-receipt/0.5",
                "receipt_id": "flat-subject",
                "margin": 0.4,
            }))
            .expect("serialize flat subject"),
        )
        .expect("write flat subject");
        let args = json!({
            "receipt_path": flat_path.display().to_string(),
            "outcome": "success",
        });
        let error = record_outcome(&args, &store, false).unwrap_err();
        assert!(
            error.contains("no '#profile' segment"),
            "unexpected error: {error}"
        );

        let missing_spec = store.join("missing-spec.json");
        std::fs::write(
            &missing_spec,
            serde_json::to_vec(&json!({"receipt_id": "missing-spec"}))
                .expect("serialize missing spec"),
        )
        .expect("write missing-spec subject");
        let args = json!({
            "receipt_path": missing_spec.display().to_string(),
            "outcome": "success",
        });
        assert!(
            record_outcome(&args, &store, false)
                .unwrap_err()
                .contains("no '#profile' segment")
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn outcome_args_refuse_missing_required_and_tolerate_unknown_keys() {
        let key = SigningKey::from_bytes(&[75u8; 32]);
        let store = fixture_store(&key);
        let subject_path = store.join("deliberation-subject.json");
        signed_deliberation_subject(&key, &subject_path, 0.3);
        let args = json!({
            "receipt_path": subject_path.display().to_string(),
            "outcome": "corrected",
            "corrected_route": "memory.create",
            "unexpected_extension": {"keep": true},
        });
        let report = record_outcome(&args, &store, false).expect("unknown extra args tolerated");
        assert_eq!(report["outcome"]["success"], json!(false));

        let missing = json!({"receipt_path": subject_path.display().to_string()});
        let error = record_outcome(&missing, &store, false).unwrap_err();
        assert!(error.contains("missing required field 'outcome'"));

        let mut with_unknown_field = report["outcome"].clone();
        with_unknown_field["mystery"] = json!(true);
        assert!(
            verify_receipt_value(&with_unknown_field, &store)
                .unwrap_err()
                .contains("unknown field")
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn outcome_typed_margin_and_success_refusals_are_explicit() {
        let key = SigningKey::from_bytes(&[77u8; 32]);
        let store = fixture_store(&key);
        let subject_path = store.join("deliberation-subject.json");
        signed_deliberation_subject(&key, &subject_path, 0.3);
        let args = json!({
            "receipt_path": subject_path.display().to_string(),
            "outcome": "success",
        });
        let report = record_outcome(&args, &store, false).expect("emit outcome");

        let mut bad_margin = report["outcome"].clone();
        bad_margin["margin"] = json!("high");
        assert!(
            verify_receipt_value(&bad_margin, &store)
                .unwrap_err()
                .contains("JSON number")
        );
        let mut bad_success = report["outcome"].clone();
        bad_success["success"] = json!("yes");
        assert!(
            verify_receipt_value(&bad_success, &store)
                .unwrap_err()
                .contains("JSON boolean")
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");
    }

    #[test]
    fn gate_key_fingerprint_known_vector_is_read_only() {
        let key = SigningKey::from_bytes(&[76u8; 32]);
        let store = fixture_store(&key);
        let before = std::fs::read(store.join("mandala_gate_key.bin")).expect("read key");
        let (fingerprint, did) = gate_key_fingerprint(&store).expect("fingerprint");
        assert_eq!(fingerprint, hex_encode(&Sha256::digest(&before)));
        assert!(did.starts_with("did:key:z"));
        let after = std::fs::read(store.join("mandala_gate_key.bin")).expect("read key again");
        assert_eq!(before, after);
        assert_eq!(
            std::fs::read_dir(&store).expect("read store").count(),
            1,
            "fingerprinting must not create sidecar files"
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");

        let missing =
            std::env::temp_dir().join(format!("wm-gate-missing-{}", uuid::Uuid::new_v4()));
        let error = gate_key_fingerprint(&missing).unwrap_err();
        assert!(error.contains("gate key read"), "unexpected error: {error}");
        assert!(!missing.join("mandala_gate_key.bin").exists());
        assert!(
            !missing.exists(),
            "fingerprinting must not create the store dir"
        );

        let malformed = fixture_store(&key);
        std::fs::write(malformed.join("mandala_gate_key.bin"), [0u8; 31]).expect("write short key");
        let error = gate_key_fingerprint(&malformed).unwrap_err();
        assert!(error.contains("32 bytes"), "unexpected error: {error}");
        std::fs::remove_dir_all(malformed).expect("cleanup malformed store");
    }

    #[test]
    fn gate_key_fingerprint_matches_known_ed25519_vectors() {
        let mut seed = [0u8; 32];
        seed.copy_from_slice(
            &hex_decode("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
                .expect("seed hex"),
        );
        let store = fixture_store(&SigningKey::from_bytes(&seed));
        let (fingerprint, did) = gate_key_fingerprint(&store).expect("fingerprint");
        assert_eq!(
            did,
            "did:key:z6MktwupdmLXVVqTzCw4i46r4uGyosGXRnR3XjN4Zq7oMMsw"
        );
        assert_eq!(
            fingerprint,
            "644d50ab64864c20a12b3c4656d46b4a48f69ef7c47ecdc8415cd28316b22ef5"
        );
        std::fs::remove_dir_all(store).expect("cleanup fixture store");

        let public_key =
            hex_decode("2e6fcce36701dc791488e0d0b1745cc1e33a4c1c9fcc41c63bd343dbbe0970e6")
                .expect("public key hex");
        let mut multicodec = vec![0xed, 0x01];
        multicodec.extend_from_slice(&public_key);
        assert_eq!(
            base58btc_encode(&multicodec),
            "6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"
        );
    }
}
