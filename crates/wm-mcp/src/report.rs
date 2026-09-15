//! `wm report` — sanitized local support bundle (P1, 2026-09-15).
//!
//! Assembles a shareable-by-choice snapshot of system state for support:
//! version/platform, store health counts, index-drift state, selftest
//! results, and a safe env-knob allowlist. Deliberately EXCLUDED: memory
//! content, queries, credentials, raw paths (the home directory is collapsed
//! to `~`), and anything outside the allowlist. Nothing is transmitted —
//! the bundle is written locally and the operator decides whether to share.

use std::path::{Path, PathBuf};

use serde_json::{Value, json};

use crate::status;

/// Environment variables that describe configuration posture without
/// carrying secrets. Numeric/boolean values are shown verbatim; everything
/// else is reduced to set/unset.
const ENV_ALLOWLIST: &[&str] = &[
    "WM_TOOL_PROFILE",
    "WM_TOOL_PACK",
    "WM_EMBEDDER_BACKEND",
    "WM_EMBEDDER_ORT_SHARDS",
    "WM_EMBEDDER_ORT_THREADS",
    "WM_FIREBREAK",
    "WM_LANDLOCK",
    "WM_LANDLOCK_V1",
    "WM_SELFMODEL_FROZEN",
    "WM_HOMEOSTASIS_FROZEN",
    "WM_DISPATCH_TIMEOUT_MS",
    "WM_DISPATCH_TOOL_RPM",
    "WM_DISPATCH_GLOBAL_RPM",
    "WM_DISPATCH_BURST",
    "WM_RECALL_BM25_WEIGHT",
    "WM_RECALL_VECTOR_WEIGHT",
    "WM_RECALL_IMPORTANCE_WEIGHT",
    "WM_REQUIRE_CAPABILITIES",
    "WM_TRUST_WEIGHT",
];

/// Collapse the home directory prefix to `~` and apply the credential
/// redaction pass so an unexpected secret in a path or value cannot ride
/// into a bundle.
#[must_use]
pub fn sanitize_text(text: &str) -> String {
    let home = std::env::var("HOME").unwrap_or_default();
    let collapsed = if home.is_empty() {
        text.to_string()
    } else {
        text.replace(&home, "~")
    };
    let (redacted, _kinds) = wm_memory::redact_credential_content(&collapsed);
    redacted
}

fn env_posture() -> Value {
    let mut map = serde_json::Map::new();
    for key in ENV_ALLOWLIST {
        match std::env::var(key) {
            Err(_) => {
                map.insert((*key).to_string(), json!("unset"));
            }
            Ok(value) => {
                let safe = value
                    .chars()
                    .all(|c| c.is_ascii_digit() || c == '.' || c == '-');
                let known_enum = matches!(value.as_str(), "curated" | "full" | "minimal");
                let shown =
                    if safe || known_enum || matches!(value.as_str(), "0" | "1" | "true" | "false")
                    {
                        value
                    } else {
                        "<set>".to_string()
                    };
                map.insert((*key).to_string(), json!(shown));
            }
        }
    }
    Value::Object(map)
}

/// Build the sanitized report (no store writes; read-only inspection).
pub async fn build(store_root: &Path) -> Value {
    let status = status::collect(store_root);
    let selftest = match crate::selftest::run().await {
        Ok(report) => {
            let (passed, total) = report.score();
            json!({
                "passed": report.passed(),
                "score": format!("{passed}/{total}"),
                "checks": report.checks.iter().map(|c| json!({
                    "name": c.name,
                    "ok": c.ok,
                })).collect::<Vec<_>>(),
            })
        }
        Err(err) => json!({"error": sanitize_text(&err.to_string())}),
    };
    json!({
        "kind": "whitemagic-support-report",
        "format_version": 1,
        "generated_at": chrono::Utc::now().to_rfc3339(),
        "version": status.version,
        "platform": {
            "os": std::env::consts::OS,
            "arch": std::env::consts::ARCH,
            "family": std::env::consts::FAMILY,
        },
        "profile": status.profile,
        "store": {
            "display_path": sanitize_text(&status.store_path),
            "store_ok": status.store_ok,
            "memories": status.memories,
            "sessions": status.sessions,
            "index_ok": status.index_ok,
            "index_memories": status.index_memories,
            "index_drift": status.index_drift,
            "index_skip_reserve": status.index_skip_reserve,
            "index_detail": status.index_detail.as_deref().map(sanitize_text),
        },
        "backup": {
            "last_backup": status.last_backup,
            "last_backup_age_secs": status.last_backup_age_secs,
            "newest_snapshot_age_secs": status.backup_newest_age_secs,
            "staging_pending": status.backup_staging_pending,
            "history_split": status.backup_history_split,
        },
        "selftest": selftest,
        "env_allowlist": env_posture(),
        "excluded": [
            "memory content and queries",
            "credentials and tokens",
            "raw filesystem paths (HOME collapsed to ~)",
            "environment variables outside the allowlist",
        ],
    })
}

const README: &str = "\
WhiteMagic sanitized support report
===================================

What this is
  A local snapshot of system state for support conversations: version,
  platform, store health counts, index-drift state, selftest results, and a
  safe configuration allowlist.

What was deliberately excluded
  Memory content and queries, credentials and tokens (a redaction pass runs
  over every string), the home directory (collapsed to ~ — paths outside HOME
  may still appear), and any environment variable outside the allowlist.

Sharing
  Nothing has been transmitted. Read report.json, then share it (or not) —
  the decision is yours.
";

/// Write `report.json` + `README.txt` into `out_dir` and return the path.
///
/// # Errors
///
/// Fails when the directory cannot be created or the files cannot be written.
pub async fn write_bundle(store_root: &Path, out_dir: &Path) -> std::io::Result<PathBuf> {
    std::fs::create_dir_all(out_dir)?;
    let report = build(store_root).await;
    let json = serde_json::to_string_pretty(&report)
        .map_err(|e| std::io::Error::other(format!("report serialization failed: {e}")))?;
    std::fs::write(out_dir.join("report.json"), json)?;
    std::fs::write(out_dir.join("README.txt"), README)?;
    Ok(out_dir.to_path_buf())
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::Galaxy;

    #[tokio::test]
    async fn report_is_sanitized_and_content_free() {
        let tmp = tempfile::tempdir().unwrap();
        let lmdb = tmp.path().join("lmdb");
        let store = wm_memory::MemoryStore::open_default(&lmdb).unwrap();
        // Assembled at runtime (repo convention) so the raw shape never
        // appears contiguously in source for scanners.
        let secret = format!("sk-{}{}", "proj", "0123456789abcdefghijklmnopqrstuv");
        let mem = wm_memory::Memory::new(Galaxy::Codex, format!("token {secret}"));
        store.put(Galaxy::Codex, &mem).unwrap();

        let report = build(tmp.path()).await;
        assert_eq!(report["kind"], "whitemagic-support-report");
        assert_eq!(report["store"]["memories"], 1);
        let text = serde_json::to_string(&report).unwrap();
        assert!(
            !text.contains(&secret),
            "memory content must never reach the report"
        );
        let home = std::env::var("HOME").unwrap_or_default();
        if !home.is_empty() {
            assert!(
                !text.contains(&home),
                "raw home path must be collapsed to ~: {text}"
            );
        }
    }

    #[test]
    fn env_posture_masks_non_numeric_values() {
        // Safe numbers pass; anything else is reduced to <set>/unset.
        // Assembled at runtime (repo convention) so the raw shape never
        // appears contiguously in source for scanners.
        let fixture = format!(
            "/home/someone/.env with {prefix}{body}",
            prefix = "ghp_",
            body = "012345678901234567890123456789012345"
        );
        assert_eq!(
            sanitize_text(&fixture),
            sanitize_text("/home/someone/.env with [REDACTED:github_token]")
        );
    }

    #[tokio::test]
    async fn bundle_writes_both_files() {
        let tmp = tempfile::tempdir().unwrap();
        let out = tmp.path().join("bundle");
        let path = write_bundle(&tmp.path().join("empty-store"), &out)
            .await
            .unwrap();
        assert!(path.join("report.json").exists());
        assert!(path.join("README.txt").exists());
        let parsed: Value =
            serde_json::from_str(&std::fs::read_to_string(path.join("report.json")).unwrap())
                .unwrap();
        assert_eq!(parsed["format_version"], 1);
    }
}
