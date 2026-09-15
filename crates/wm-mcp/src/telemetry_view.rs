//! `wm telemetry` — machine schema + display-only transmission preview
//! (P1, 2026-09-15).
//!
//! WhiteMagic records local diagnostic evidence; nothing is transmitted.
//! `wm telemetry schema` publishes the exact record contract and retention
//! policy; `wm telemetry preview` shows — from the local store — precisely
//! what a future opt-in transmission WOULD carry, after the same credential
//! redaction pass that guards ingest. Preview performs no network I/O and
//! writes nothing.

use std::path::Path;

use serde_json::{Value, json};
use wm_core::Galaxy;
use wm_memory::MemoryStore;

/// Version of the machine telemetry contract.
pub const SCHEMA_VERSION: &str = "1.0";

/// Record kinds accepted by the typed telemetry path.
pub const RECORD_KINDS: &[&str] = &[
    "telemetry.window",
    "telemetry.rollup",
    "telemetry.observation",
];

/// The machine-readable telemetry contract: fields, retention, redaction,
/// and the transport posture. Display-only until an opt-in phase exists.
#[must_use]
pub fn schema_json() -> Value {
    json!({
        "schema_version": SCHEMA_VERSION,
        "transport": {
            "mode": "none",
            "detail": "Records stay on-device. No transmission path exists in this build; `wm telemetry preview` is display-only.",
        },
        "content_posture": "content-free by producer convention: records carry timestamps, metric names/values, policy identity, and harmony dimensions. The typed path does not enforce a field allowlist, so a caller could add extra keys; preview applies credential redaction but does not strip paths or arbitrary content",
        "redaction": {
            "pass": "wm_memory::redact_credential_content",
            "classes": [
                "private_key_pem",
                "aws_access_key_id",
                "github_token",
                "openai_style_key",
                "slack_token",
                "jwt",
                "credential_assignment",
            ],
            "applied_to": ["ingest", "telemetry-preview"],
        },
        "retention": {
            "windows_days": 7,
            "rollups_days": 90,
            "observations": "retained with rollups (policy decision trail)",
            "prune": "`telemetry.retention` reports the inventory (read-only); the destructive `telemetry.prune` requires confirm: true",
        },
        "records": [
            {
                "kind": "telemetry.window",
                "required": ["kind", "ts", "harmony_score", "dims", "dim_notes"],
                "optional": ["importance", "source", "tags"],
                "notes": "dim_notes is mandatory: a window without provenance notes is a probe and must not pollute trend lanes",
            },
            {
                "kind": "telemetry.rollup",
                "required": ["kind", "ts", "harmony_score|harmony.avg", "dims"],
                "optional": ["importance", "source", "tags"],
            },
            {
                "kind": "telemetry.observation",
                "required": ["kind", "ts", "policy_id", "metric", "state", "action", "value"],
                "optional": ["subject", "actuator", "step"],
                "notes": "policy-decision record from the observation ladder (Yama bridge)",
            },
        ],
    })
}

/// Human-readable rendering of [`schema_json`].
#[must_use]
pub fn schema_lines() -> Vec<String> {
    let mut out = vec![
        format!("Telemetry schema v{SCHEMA_VERSION} — recorded locally, never transmitted"),
        String::new(),
        "Record kinds:".to_string(),
    ];
    for kind in RECORD_KINDS {
        out.push(format!("  {kind}"));
    }
    out.extend([
        String::new(),
        "Content posture: content-free by producer convention (timestamps, metric names/values,"
            .to_string(),
        "policy identity, harmony dimensions). Extra keys are not stripped; redaction is"
            .to_string(),
        "shape-based, so preview scrubs credential spans but does not remove paths.".to_string(),
        String::new(),
        "Redaction pass: credential spans scrubbed before any preview/send (same pass as ingest)."
            .to_string(),
        "Retention: windows 7 d, rollups 90 d, observations with rollups; telemetry.retention"
            .to_string(),
        "reports the inventory read-only and telemetry.prune deletes it (confirm-gated)."
            .to_string(),
        String::new(),
        "Transport: none — display-only until an explicit opt-in phase exists.".to_string(),
        "Machine form: wm telemetry schema --json".to_string(),
    ]);
    out
}

/// Load the most recent telemetry records (newest first, bounded).
#[must_use]
pub fn load_recent_telemetry(lmdb_dir: &Path, limit: usize) -> Vec<Value> {
    let Ok(store) = MemoryStore::open_inspection(lmdb_dir) else {
        return Vec::new();
    };
    // Scan order is key order (UUID), not time — overscan, then sort.
    let cap = limit.saturating_mul(50).max(500);
    let mut records: Vec<(chrono::DateTime<chrono::Utc>, Value)> = store
        .scan(Galaxy::Telemetry, cap)
        .unwrap_or_default()
        .into_iter()
        .filter_map(|mem| {
            let value: Value = serde_json::from_str(&mem.content).ok()?;
            Some((mem.metadata.created_at, value))
        })
        .collect();
    records.sort_by_key(|(created, _)| std::cmp::Reverse(*created));
    records.into_iter().take(limit).map(|(_, v)| v).collect()
}

/// Build the exact payload a hypothetical opt-in transmission would carry.
///
/// Applies the credential-redaction pass to the serialized form and returns
/// the payload plus the redaction classes that fired.
#[must_use]
pub fn build_preview(records: &[Value]) -> (Value, Vec<String>) {
    let payload = json!({
        "schema_version": SCHEMA_VERSION,
        "generated_at": chrono::Utc::now().to_rfc3339(),
        "transport": "none — display-only preview; nothing is sent",
        "records": records,
    });
    let serialized = serde_json::to_string_pretty(&payload).unwrap_or_default();
    let (redacted, kinds) = wm_memory::redact_credential_content(&serialized);
    let kinds: Vec<String> = kinds.into_iter().map(str::to_string).collect();
    if kinds.is_empty() {
        (payload, kinds)
    } else {
        // A redaction firing inside content-free telemetry is itself a
        // finding; surface the scrubbed payload rather than hiding it. If the
        // scrubbed text somehow fails to re-parse, show the SCRUBBED text —
        // never fall back to the pre-redaction value (fail-closed redaction).
        let parsed = serde_json::from_str(&redacted).unwrap_or_else(|_| {
            json!({
                "redacted_payload_text": redacted,
                "note": "redacted form did not re-parse as JSON; the scrubbed text is shown instead",
            })
        });
        (parsed, kinds)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn schema_covers_every_record_kind_and_retention() {
        let schema = schema_json();
        assert_eq!(schema["transport"]["mode"], "none");
        for kind in RECORD_KINDS {
            assert!(
                schema["records"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|r| r["kind"] == *kind),
                "schema must describe {kind}"
            );
        }
        assert_eq!(schema["retention"]["windows_days"], 7);
        assert_eq!(schema["retention"]["rollups_days"], 90);
        assert!(!schema_lines().is_empty());
    }

    #[test]
    fn schema_redaction_classes_match_the_detector() {
        // Every published class must be a real detector kind (2026-09-15
        // review: the schema named a class that could never fire). Exercising
        // each kind's fixture shape keeps this honest.
        let schema = schema_json();
        let published: Vec<&str> = schema["redaction"]["classes"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|v| v.as_str())
            .collect();
        let fixtures = [
            (
                format!(
                    "-----BEGIN {alg} PRIVATE KEY-----\nMIIEow\n-----END {alg} PRIVATE KEY-----",
                    alg = "RSA"
                ),
                "private_key_pem",
            ),
            ("AKIAIOSFODNN7EXAMPLE".to_string(), "aws_access_key_id"),
            (
                // Shapes are assembled at runtime (repo convention) so raw
                // credential patterns never appear contiguously in source.
                format!(
                    "{prefix}{body}",
                    prefix = "ghp_",
                    body = "012345678901234567890123456789012345"
                ),
                "github_token",
            ),
            (
                format!("sk-{}{}", "proj", "0123456789abcdefghijklmnopqrstuv"),
                "openai_style_key",
            ),
            (
                format!(
                    "{prefix}{body}",
                    prefix = "xoxb-",
                    body = "123456789012-1234567890123-AbCdEfGhIjKlMnOpQrStUvWx"
                ),
                "slack_token",
            ),
            (
                "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.dBV7hF3lZx9Kq2mN4pR8sT1uW5yA6bC7dE8fG9hI0jK"
                    .to_string(),
                "jwt",
            ),
            (
                "api_key = 'supersecretvalue123'".to_string(),
                "credential_assignment",
            ),
        ];
        for (fixture, expected) in fixtures {
            let (_, kinds) = wm_memory::redact_credential_content(&fixture);
            assert!(
                kinds.contains(&expected),
                "fixture must trigger {expected}: {kinds:?}"
            );
            assert!(
                published.contains(&expected),
                "detector kind {expected} missing from the published schema"
            );
        }
    }

    #[test]
    fn preview_is_content_free_and_redacts_credential_shaped_values() {
        let clean = json!({
            "kind": "telemetry.window",
            "ts": "2026-09-15T12:00:00Z",
            "harmony_score": 0.82,
            "dims": {"dharma": 0.9},
            "dim_notes": {"dharma": "steady"}
        });
        let (payload, kinds) = build_preview(std::slice::from_ref(&clean));
        assert!(
            kinds.is_empty(),
            "clean telemetry must not redact: {kinds:?}"
        );
        assert_eq!(payload["records"][0], clean);
        assert!(
            payload["transport"]
                .as_str()
                .unwrap_or("")
                .contains("display-only"),
            "preview must disclose that nothing is sent"
        );

        // Assembled at runtime (repo convention) so the raw shape never
        // appears contiguously in source for scanners.
        let leaky_key = format!("sk-{}{}", "proj", "0123456789abcdefghijklmnopqrstuv");
        let leaky = json!({
            "kind": "telemetry.observation",
            "ts": "2026-09-15T12:01:00Z",
            "policy_id": "spawn.undeclared.v1",
            "metric": "spawn",
            "state": "observing",
            "action": "notify",
            "value": 1.0,
            "subject": "proc:cat:/usr/bin/cat",
            "note": format!("token {leaky_key}")
        });
        let (payload, kinds) = build_preview(&[leaky]);
        assert!(
            kinds.iter().any(|k| k.contains("openai")),
            "credential-shaped value must be caught: {kinds:?}"
        );
        let text = serde_json::to_string(&payload).unwrap();
        assert!(
            !text.contains(&leaky_key),
            "redacted preview must not carry the raw span"
        );
    }

    #[test]
    fn recent_telemetry_reads_the_local_galaxy() {
        let tmp = tempfile::tempdir().unwrap();
        let lmdb = tmp.path().join("lmdb");
        let store = MemoryStore::open_default(&lmdb).unwrap();
        for n in 0..3 {
            let record = json!({
                "kind": "telemetry.rollup",
                "ts": format!("2026-09-15T12:0{n}:00Z"),
                "harmony": {"avg": 0.8},
                "dims": {"dharma": 0.9},
            });
            let mem = wm_memory::Memory::new(Galaxy::Telemetry, record.to_string());
            store.put(Galaxy::Telemetry, &mem).unwrap();
        }
        let recent = load_recent_telemetry(&lmdb, 2);
        assert_eq!(recent.len(), 2, "limit respected");
        assert!(recent.iter().all(|r| r["kind"] == "telemetry.rollup"));
        assert!(load_recent_telemetry(&tmp.path().join("missing"), 5).is_empty());
    }
}
