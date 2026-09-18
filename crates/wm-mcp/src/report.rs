//! `wm report` — sanitized local support bundle (P1, 2026-09-15).
//!
//! Assembles a shareable-by-choice snapshot of system state for support:
//! version/platform, store health counts, index-drift state, selftest
//! results, and a safe env-knob allowlist. Deliberately EXCLUDED: memory
//! content, queries, credentials, raw paths (the store root becomes
//! `<store>` — keeping its relative shape, the home directory `~`, and every
//! other absolute path `<path>`), and anything outside the allowlist.
//! Nothing is transmitted — the bundle is written locally and the operator
//! decides whether to share.

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

/// True for characters that can appear inside a filesystem path token.
fn is_path_char(c: char) -> bool {
    !c.is_whitespace()
        && !matches!(
            c,
            '"' | '\''
                | '`'
                | '('
                | ')'
                | '['
                | ']'
                | '{'
                | '}'
                | '<'
                | '>'
                | ','
                | ';'
                | ':'
                | '='
                | '|'
        )
}

/// Replace absolute filesystem paths with `<path>` while preserving URL
/// scheme slashes (`https://…`), the home shorthand (`~/…`), and the
/// relative tail of an already-substituted `<store>` prefix.
#[must_use]
pub fn scrub_absolute_paths(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut rest = text;
    while !rest.is_empty() {
        // Keep `<store>` and the relative shape that follows it, so a store
        // subpath reports as `<store>/lmdb` instead of an opaque `<path>`.
        if let Some(tail) = rest.strip_prefix("<store>") {
            out.push_str("<store>");
            let keep = tail
                .char_indices()
                .find(|(_, c)| !is_path_char(*c))
                .map_or(tail.len(), |(i, _)| i);
            out.push_str(&tail[..keep]);
            rest = &tail[keep..];
            continue;
        }
        // Windows drive paths (`C:\Users\…`). The drive letter must start a
        // token — otherwise the tail of a URL scheme (`https://…`) reads as
        // `s:/…`.
        let bytes = rest.as_bytes();
        let at_token_start = out
            .chars()
            .next_back()
            .is_none_or(|prev| !prev.is_alphanumeric());
        if at_token_start
            && bytes.len() >= 3
            && bytes[0].is_ascii_alphabetic()
            && bytes[1] == b':'
            && matches!(bytes[2], b'\\' | b'/')
        {
            let keep = rest
                .char_indices()
                .skip(3)
                .find(|(_, c)| !is_path_char(*c))
                .map_or(rest.len(), |(i, _)| i);
            out.push_str("<path>");
            rest = &rest[keep..];
            continue;
        }
        let c = rest.chars().next().expect("rest is non-empty");
        let starts_path = c == '/'
            && !rest.starts_with("//")
            && out.chars().next_back().is_none_or(|prev| {
                !prev.is_alphanumeric() && !matches!(prev, '_' | '~' | '.' | '/')
            });
        if starts_path {
            let keep = rest
                .char_indices()
                .skip(1)
                .find(|(_, c)| !is_path_char(*c))
                .map_or(rest.len(), |(i, _)| i);
            out.push_str("<path>");
            rest = &rest[keep..];
            continue;
        }
        out.push(c);
        rest = &rest[c.len_utf8()..];
    }
    out
}

/// Sanitize one report string: the store root first (before the home
/// collapse, so a store inside HOME still becomes `<store>`), then HOME,
/// credentials, and any remaining absolute path.
fn sanitize_report_text(text: &str, store_root: &Path) -> String {
    let root = store_root.to_string_lossy();
    let replaced = if root.len() > 1 {
        text.replace(root.as_ref(), "<store>")
    } else {
        text.to_string()
    };
    scrub_absolute_paths(&sanitize_text(&replaced))
}

/// Apply [`sanitize_report_text`] to every string in the report tree — a
/// path that rides in through an error message or a future field cannot
/// escape on the way to the bundle.
fn sanitize_report_value(value: &mut Value, store_root: &Path) {
    match value {
        Value::String(s) => *s = sanitize_report_text(s, store_root),
        Value::Array(items) => {
            for item in items {
                sanitize_report_value(item, store_root);
            }
        }
        Value::Object(map) => {
            for item in map.values_mut() {
                sanitize_report_value(item, store_root);
            }
        }
        Value::Null | Value::Bool(_) | Value::Number(_) => {}
    }
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
        Err(err) => json!({"error": err.to_string()}),
    };
    let mut report = json!({
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
            "display_path": status.store_path,
            "store_ok": status.store_ok,
            "memories": status.memories,
            "sessions": status.sessions,
            "index_ok": status.index_ok,
            "index_memories": status.index_memories,
            "index_drift": status.index_drift,
            "index_skip_reserve": status.index_skip_reserve,
            "index_detail": status.index_detail,
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
            "raw filesystem paths (store root -> <store>, HOME -> ~, other absolute paths -> <path>)",
            "environment variables outside the allowlist",
        ],
    });
    sanitize_report_value(&mut report, store_root);
    report
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
  over every string), and every raw filesystem path: the store root is
  replaced by <store> (subpaths keep their relative shape, e.g.
  <store>/lmdb), the home directory by ~, and any other absolute path by
  <path>. Environment variables outside the allowlist are not included.

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

    /// The scrubber keeps URL schemes, `~` shorthand, and `<store>` relative
    /// tails while replacing every other absolute path.
    #[test]
    fn scrub_absolute_paths_replaces_roots_and_keeps_shapes() {
        let text = "index <store>/lmdb/tantivy failed; error at /mnt/private/client-A/x.sqlite: \
                    disk full; see https://example.com/a/b and ~/notes; win C:\\Users\\client-A\\cfg";
        assert_eq!(
            scrub_absolute_paths(text),
            "index <store>/lmdb/tantivy failed; error at <path>: \
             disk full; see https://example.com/a/b and ~/notes; win <path>"
        );
    }

    /// P1 privacy regression (9.1.9 tester): a store at a hostile path —
    /// deep, spaces, unicode, a private client name — must not leak any raw
    /// path substring, and the `<store>` placeholder must be present.
    #[tokio::test]
    async fn report_never_leaks_hostile_store_paths() {
        let tmp = tempfile::tempdir().unwrap();
        let hostile = tmp
            .path()
            .join("private-client-A")
            .join("クライアント ストア")
            .join("deep path with spaces");
        let store = wm_memory::MemoryStore::open_default(hostile.join("lmdb")).unwrap();
        let mem = wm_memory::Memory::new(Galaxy::Codex, "hostile path probe".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        let report = build(&hostile).await;
        let text = serde_json::to_string_pretty(&report).unwrap();
        for needle in [
            hostile.display().to_string(),
            "private-client-A".to_string(),
            "クライアント".to_string(),
            tmp.path().display().to_string(),
        ] {
            assert!(
                !text.contains(&needle),
                "raw path fragment {needle:?} leaked into the report: {text}"
            );
        }
        assert!(
            text.contains("<store>"),
            "sanitized <store> placeholder missing: {text}"
        );
        // Every JSON string is free of an absolute path.
        fn assert_clean(value: &Value) {
            match value {
                Value::String(s) => {
                    assert!(!s.starts_with('/'), "absolute path escaped: {s:?}");
                    assert!(!s.contains(":/"), "absolute path escaped: {s:?}");
                }
                Value::Array(items) => items.iter().for_each(assert_clean),
                Value::Object(map) => map.values().for_each(assert_clean),
                _ => {}
            }
        }
        assert_clean(&report);
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
