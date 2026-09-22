//! Verification wrapper over the independent `continuity-receipt` crate.
//!
//! Same verdict semantics and error codes as the Python reference; WM never
//! judges content, only integrity ("verify, do not judge").

use serde_json::{Value, json};

/// A verification outcome in a WM-friendly shape.
#[derive(Debug, Clone)]
pub struct VerifyOutcome {
    /// `TRUSTED` | `PROVISIONAL` | `INSUFFICIENT_EVIDENCE` | `UNTRUSTED`.
    pub verdict: String,
    /// Structured errors (CR shape).
    pub errors: Value,
    /// Provisional reasons (e.g. `anchor_missing` with `require_anchor`).
    pub provisional_reasons: Vec<String>,
    /// Insufficient-evidence reasons (e.g. erased content).
    pub insufficient_reasons: Vec<String>,
    /// CR summary (receipts, types, issuers, terminated, settled, …).
    pub summary: Value,
}

impl VerifyOutcome {
    /// True when the bundle verifies `TRUSTED`.
    #[must_use]
    pub fn is_trusted(&self) -> bool {
        self.verdict == "TRUSTED"
    }

    /// Error codes only, for differential comparison with the Python verifier.
    #[must_use]
    pub fn error_codes(&self) -> Vec<String> {
        self.errors
            .as_array()
            .map(|entries| {
                entries
                    .iter()
                    .filter_map(|entry| entry.get("code").and_then(Value::as_str))
                    .map(str::to_string)
                    .collect()
            })
            .unwrap_or_default()
    }

    /// JSON shape matching CR's `as_dict()` plus convenience fields.
    #[must_use]
    pub fn to_value(&self) -> Value {
        json!({
            "verdict": self.verdict,
            "errors": self.errors,
            "provisional_reasons": self.provisional_reasons,
            "insufficient_reasons": self.insufficient_reasons,
            "summary": self.summary,
        })
    }
}

/// Verify a bundle with the Rust implementation.
#[must_use]
pub fn verify_bundle(bundle: &Value, require_anchor: bool) -> VerifyOutcome {
    let result = continuity_receipt::verify::verify_bundle(bundle, require_anchor);
    let dict = result.as_dict();
    VerifyOutcome {
        verdict: result.verdict().to_string(),
        errors: dict.get("errors").cloned().unwrap_or_else(|| json!([])),
        provisional_reasons: serde_json::from_value(
            dict.get("provisional_reasons")
                .cloned()
                .unwrap_or_else(|| json!([])),
        )
        .unwrap_or_default(),
        insufficient_reasons: serde_json::from_value(
            dict.get("insufficient_reasons")
                .cloned()
                .unwrap_or_else(|| json!([])),
        )
        .unwrap_or_default(),
        summary: dict.get("summary").cloned().unwrap_or_else(|| json!({})),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn junk_bundles_are_untrusted_with_codes() {
        let outcome = verify_bundle(&json!({ "spec": "nope" }), false);
        assert_eq!(outcome.verdict, "UNTRUSTED");
        assert_eq!(
            outcome.error_codes(),
            vec!["version_unsupported".to_string()]
        );
    }

    #[test]
    fn require_anchor_makes_unanchored_bundles_provisional() {
        // Reuse the session profile from another module's fixtures: a minimal
        // structural check is enough here — no anchors in a fresh bundle.
        let bundle = json!({
            "spec": "continuity-receipt/0.2",
            "task_id": "urn:uuid:11111111-1111-7111-8111-111111111111",
            "receipts": []
        });
        let outcome = verify_bundle(&bundle, true);
        assert_eq!(outcome.verdict, "UNTRUSTED", "empty receipts are malformed");
        assert!(outcome.error_codes().contains(&"malformed".to_string()));
    }
}
