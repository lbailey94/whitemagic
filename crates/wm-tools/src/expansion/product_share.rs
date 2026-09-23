//! Product telemetry — explicit opt-in sharing (schema 1, basic mode).
//!
//! The site's `/api/ingest` plane is an allowlist of enums and bounded
//! integers (`whitemagic-site/lib/telemetry.ts`): unknown keys are rejected,
//! and no field can carry prompts, memories, paths, code, or names. This
//! module is the core emitter for it:
//!
//! - **Consent is deliberate and local.** Nothing is sent unless
//!   `<store-root>/product_share.json` says `enabled: true`, which only the
//!   human-facing `wm telemetry product-enable --share` command writes; the
//!   exact payload is printed before the send.
//! - **Basic mode only.** No install id, no longitudinal identifier —
//!   aggregate counters (`launches`, store inventory) and the version/os/arch
//!   vocabulary. `WM_TELEMETRY_CLIENT` / `WM_TELEMETRY_INSTALLED_VIA` are
//!   validated against the site enums and omitted when unrecognized.
//! - **Best effort.** One send with a bounded deadline; on failure the
//!   payload is spooled (`<store-root>/product_pending.json`) for one retry.
//!   `WM_PRODUCT_TELEMETRY_DISABLED=1` is the kill switch;
//!   `WM_PRODUCT_TELEMETRY_ENDPOINT` overrides the endpoint (tests,
//!   self-hosters).

#![forbid(unsafe_code)]

use std::path::Path;

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use super::funnel;

/// Local consent + delivery ledger beside `funnel_share.json`.
pub const STATE_FILE: &str = "product_share.json";
/// At most one spooled payload awaiting a single retry.
pub const PENDING_FILE: &str = "product_pending.json";
const STATE_TMP_FILE: &str = ".product_share.json.tmp";
const PENDING_TMP_FILE: &str = ".product_pending.json.tmp";
/// Ingest schema version (`whitemagic-site/lib/telemetry.ts`).
pub const SCHEMA: u32 = 1;
/// First-party endpoint; overridable for tests and self-hosters.
pub const DEFAULT_ENDPOINT: &str = "https://www.whitemagic.dev/api/ingest";

/// Site allowlists (kept in lockstep with `lib/telemetry.ts`).
pub const CLIENT_FAMILIES: &[&str] = &[
    "claude-code",
    "claude-desktop",
    "cursor",
    "codex",
    "windsurf",
    "vscode",
    "opencode",
    "gemini-cli",
    "other",
];
pub const INSTALL_CHANNELS: &[&str] = &[
    "binary",
    "install_sh",
    "npm",
    "docker",
    "cargo",
    "source",
    "unknown",
];
pub const EVENT_NAMES: &[&str] = &[
    "launches",
    "mcp_connections",
    "grimoire_started",
    "grimoire_completed",
    "first_memory_stored",
    "first_continuity_success",
    "memory_stores",
    "memory_recalls",
    "recall_misses",
    "recall_failures",
    "tool_calls",
    "dreams_completed",
    "backups",
    "restores",
];
/// Site bound on a single event count.
pub const MAX_EVENT_COUNT: u64 = 100_000;

/// Consent + delivery state (`<store-root>/product_share.json`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductState {
    #[serde(default)]
    pub schema: u32,
    /// Written only by the explicit human-facing consent command.
    #[serde(default)]
    pub enabled: bool,
    #[serde(default)]
    pub enabled_at: Option<String>,
    #[serde(default)]
    pub last_sent_at: Option<String>,
    /// Bounded outcome label (`ok`, `http_<code>`, `network`, `dropped`).
    #[serde(default)]
    pub last_result: Option<String>,
    /// Last successfully sent payload (dedup: identical payloads skip).
    #[serde(default)]
    pub last_payload: Option<Value>,
}

impl Default for ProductState {
    fn default() -> Self {
        Self {
            schema: SCHEMA,
            enabled: false,
            enabled_at: None,
            last_sent_at: None,
            last_result: None,
            last_payload: None,
        }
    }
}

/// Kill switch (shared with the funnel kill switch semantics).
#[must_use]
pub fn disabled() -> bool {
    matches!(
        std::env::var("WM_PRODUCT_TELEMETRY_DISABLED").as_deref(),
        Ok("1" | "true")
    )
}

/// Endpoint for this build (`WM_PRODUCT_TELEMETRY_ENDPOINT` wins).
#[must_use]
pub fn endpoint() -> String {
    std::env::var("WM_PRODUCT_TELEMETRY_ENDPOINT")
        .ok()
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| DEFAULT_ENDPOINT.to_string())
}

/// Read the share ledger; a missing or malformed file means "not sharing".
#[must_use]
pub fn read_share(store_root: &Path) -> ProductState {
    std::fs::read_to_string(store_root.join(STATE_FILE))
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_default()
}

fn save_share(store_root: &Path, state: &ProductState) -> std::io::Result<()> {
    std::fs::create_dir_all(store_root)?;
    let mut state = state.clone();
    if state.schema == 0 {
        state.schema = SCHEMA;
    }
    let body = serde_json::to_string_pretty(&state).map_err(std::io::Error::other)?;
    let tmp = store_root.join(STATE_TMP_FILE);
    std::fs::write(&tmp, body)?;
    std::fs::rename(&tmp, store_root.join(STATE_FILE))
}

/// Whether sending is currently consented (and not kill-switched).
#[must_use]
pub fn sharing(store_root: &Path) -> bool {
    !disabled() && read_share(store_root).enabled
}

/// Record consent (idempotent; the timestamp is set on first enable).
///
/// # Errors
/// I/O failures writing the share ledger.
pub fn enable(store_root: &Path) -> std::io::Result<ProductState> {
    let mut state = read_share(store_root);
    state.enabled = true;
    if state.enabled_at.is_none() {
        state.enabled_at = Some(now_rfc3339());
    }
    save_share(store_root, &state)?;
    Ok(state)
}

/// Stop all sharing (the ledger stays for auditability).
///
/// # Errors
/// I/O failures writing the share ledger.
pub fn disable(store_root: &Path) -> std::io::Result<ProductState> {
    let mut state = read_share(store_root);
    state.enabled = false;
    save_share(store_root, &state)?;
    Ok(state)
}

/// Build the exact schema-1 payload for the given event counters.
///
/// Unknown event names and out-of-range counts are dropped (the site would
/// reject the whole payload otherwise); an empty event set yields `None`.
#[must_use]
pub fn build_payload(events: &[(&str, u64)]) -> Option<Value> {
    build_payload_with(
        events,
        std::env::var("WM_TELEMETRY_CLIENT").ok().as_deref(),
        std::env::var("WM_TELEMETRY_INSTALLED_VIA").ok().as_deref(),
    )
}

/// `build_payload` with the optional client/channel labels passed explicitly
/// (the env-reading wrapper above is the production path; this seam keeps
/// tests free of process-global env mutation).
#[must_use]
pub fn build_payload_with(
    events: &[(&str, u64)],
    client: Option<&str>,
    channel: Option<&str>,
) -> Option<Value> {
    let mut map = serde_json::Map::new();
    for (name, count) in events {
        if EVENT_NAMES.contains(name) && *count <= MAX_EVENT_COUNT {
            map.insert((*name).to_string(), json!(count));
        }
    }
    if map.is_empty() {
        return None;
    }
    let mut payload = json!({
        "schema": SCHEMA,
        "wm_version": env!("CARGO_PKG_VERSION"),
        "platform": funnel::platform_os(),
        "arch": funnel::platform_arch(),
        "events": map,
    });
    let client = client
        .map(str::trim)
        .filter(|value| CLIENT_FAMILIES.contains(value));
    if let Some(client) = client {
        payload["client"] = json!(client);
    }
    let channel = channel
        .map(str::trim)
        .filter(|value| INSTALL_CHANNELS.contains(value));
    if let Some(channel) = channel {
        payload["installed_via"] = json!(channel);
    }
    Some(payload)
}

/// The default heartbeat payload: one launch plus the store's memory
/// inventory snapshot (bounded to the site's per-event ceiling).
#[must_use]
pub fn heartbeat_payload(memories: u64) -> Option<Value> {
    build_payload(&[
        ("launches", 1),
        ("memory_stores", memories.min(MAX_EVENT_COUNT)),
    ])
}

fn now_rfc3339() -> String {
    chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true)
}

/// Send one payload synchronously best effort.
///
/// On failure the payload is spooled for a single retry (unless spooling
/// also fails, which is reported as `network`). Identical payloads that were
/// already acknowledged are skipped as `ok` without a request.
pub fn send_payload(
    store_root: &Path,
    payload: &Value,
    poster: &dyn super::funnel_share::Poster,
) -> String {
    let state = read_share(store_root);
    if state.last_payload.as_ref() == Some(payload) && state.last_result.as_deref() == Some("ok") {
        return "ok".to_string();
    }
    match poster.post(&endpoint(), payload) {
        Ok(()) => {
            let mut state = read_share(store_root);
            state.last_sent_at = Some(now_rfc3339());
            state.last_result = Some("ok".to_string());
            state.last_payload = Some(payload.clone());
            let _ = save_share(store_root, &state);
            let _ = std::fs::remove_file(store_root.join(PENDING_FILE));
            "ok".to_string()
        }
        Err(label) => {
            let spooled = save_pending(store_root, payload, 0);
            let mut state = read_share(store_root);
            state.last_result = Some(label.clone());
            let _ = save_share(store_root, &state);
            if spooled {
                label
            } else {
                "network".to_string()
            }
        }
    }
}

fn save_pending(store_root: &Path, payload: &Value, attempts: u32) -> bool {
    let pending = json!({
        "spooled_at": now_rfc3339(),
        "attempts": attempts,
        "payload": payload,
    });
    let body = match serde_json::to_string_pretty(&pending) {
        Ok(body) => body,
        Err(_) => return false,
    };
    let tmp = store_root.join(PENDING_TMP_FILE);
    std::fs::write(&tmp, body).is_ok()
        && std::fs::rename(&tmp, store_root.join(PENDING_FILE)).is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    struct FakePoster {
        result: Result<(), String>,
        calls: Mutex<Vec<(String, Value)>>,
    }

    impl FakePoster {
        fn ok() -> Self {
            Self {
                result: Ok(()),
                calls: Mutex::new(Vec::new()),
            }
        }

        fn failing(label: &str) -> Self {
            Self {
                result: Err(label.to_string()),
                calls: Mutex::new(Vec::new()),
            }
        }
    }

    impl super::super::funnel_share::Poster for FakePoster {
        fn post(&self, url: &str, payload: &Value) -> Result<(), String> {
            self.calls
                .lock()
                .unwrap()
                .push((url.to_string(), payload.clone()));
            self.result.clone()
        }
    }

    #[test]
    fn payload_is_allowlisted_and_bounded() {
        let payload = build_payload(&[
            ("launches", 1),
            ("memory_stores", 42),
            ("not_an_event", 5),
            ("tool_calls", MAX_EVENT_COUNT + 1),
        ])
        .expect("payload");
        assert_eq!(payload["schema"], 1);
        assert_eq!(payload["platform"], funnel::platform_os());
        assert_eq!(payload["arch"], funnel::platform_arch());
        assert_eq!(payload["events"]["launches"], 1);
        assert_eq!(payload["events"]["memory_stores"], 42);
        assert!(
            payload["events"].get("not_an_event").is_none(),
            "unknown event names must be dropped"
        );
        assert!(
            payload["events"].get("tool_calls").is_none(),
            "out-of-range counts must be dropped"
        );
        let allowed = [
            "schema",
            "wm_version",
            "platform",
            "arch",
            "client",
            "installed_via",
            "events",
        ];
        for key in payload.as_object().unwrap().keys() {
            assert!(allowed.contains(&key.as_str()), "unexpected key: {key}");
        }
        assert!(build_payload(&[]).is_none(), "empty event set yields none");
    }

    #[test]
    fn client_and_channel_env_are_validated() {
        // Unrecognized values are omitted rather than sent.
        let payload =
            build_payload_with(&[("launches", 1)], Some("not-a-client"), Some("sneaky")).unwrap();
        assert!(payload.get("client").is_none());
        assert!(payload.get("installed_via").is_none());

        let payload =
            build_payload_with(&[("launches", 1)], Some("opencode"), Some("install_sh")).unwrap();
        assert_eq!(payload["client"], "opencode");
        assert_eq!(payload["installed_via"], "install_sh");
    }

    #[test]
    fn consent_is_off_until_explicitly_enabled() {
        let tmp = tempfile::tempdir().unwrap();
        assert!(!sharing(tmp.path()));
        enable(tmp.path()).unwrap();
        assert!(sharing(tmp.path()));
        disable(tmp.path()).unwrap();
        assert!(!sharing(tmp.path()));
    }

    #[test]
    fn send_records_success_and_spools_failures() {
        let tmp = tempfile::tempdir().unwrap();
        let payload = heartbeat_payload(7).unwrap();

        let poster = FakePoster::ok();
        assert_eq!(send_payload(tmp.path(), &payload, &poster), "ok");
        assert_eq!(poster.calls.lock().unwrap().len(), 1);
        assert!(!tmp.path().join(PENDING_FILE).exists());
        let state = read_share(tmp.path());
        assert_eq!(state.last_result.as_deref(), Some("ok"));
        // Identical payload after success is deduped (no second request).
        assert_eq!(send_payload(tmp.path(), &payload, &poster), "ok");
        assert_eq!(poster.calls.lock().unwrap().len(), 1);

        let failing = FakePoster::failing("http_500");
        let other = heartbeat_payload(8).unwrap();
        assert_eq!(send_payload(tmp.path(), &other, &failing), "http_500");
        assert!(tmp.path().join(PENDING_FILE).exists());
        assert_eq!(
            read_share(tmp.path()).last_result.as_deref(),
            Some("http_500")
        );
    }
}
