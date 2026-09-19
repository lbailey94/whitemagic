//! Install-funnel scope 2 — explicit opt-in sharing (2026-09-18).
//!
//! Scope 1 records activation milestones locally and transmits nothing. This
//! module adds the consented transmission path:
//!
//! - Consent is a local flag (`<store-root>/funnel_share.json`) written only
//!   by the human-facing `wm telemetry enable --share` command; an agent may
//!   not consent for a human (non-TTY runs require the explicit `--yes` flag
//!   and still print the exact payload).
//! - The envelope is `funnel/1`, content-free: a random install id (rotatable
//!   with `wm telemetry reset-id`), version/os/arch, the best-effort install
//!   channel (+ ref), first-launch timestamp, milestone names, active day
//!   offsets, and raw session/memory counts. No memory text, no prompts, no
//!   paths, no hostnames, no IPs.
//! - Transport is best effort and never on the critical path: sends happen on
//!   `wm telemetry enable --share` (synchronous, 2 s deadline) and from a
//!   detached worker on launches/milestones when sharing is enabled. One
//!   offline envelope is spooled (`<store-root>/funnel_pending.json`) and
//!   retried once, then dropped.
//!
//! `WM_FUNNEL_DISABLED=1` suppresses emission and sending; `WM_FUNNEL_ENDPOINT`
//! overrides the endpoint (self-hosters and tests).

#![forbid(unsafe_code)]

use std::path::Path;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

use super::funnel::{self, FunnelState};

/// Local consent + share ledger beside `funnel_state.json`.
pub const SHARE_STATE_FILE: &str = "funnel_share.json";
/// At most one spooled envelope awaiting a single retry.
pub const PENDING_FILE: &str = "funnel_pending.json";
const SHARE_TMP_FILE: &str = ".funnel_share.json.tmp";
const PENDING_TMP_FILE: &str = ".funnel_pending.json.tmp";
const SHARE_SCHEMA: u32 = 1;
/// Envelope schema name (`INSTALL_FUNNEL_TELEMETRY.md` §2).
pub const ENVELOPE_SCHEMA: &str = "funnel/1";
/// First-party endpoint; overridable for tests and self-hosters.
pub const DEFAULT_ENDPOINT: &str = "https://www.whitemagic.dev/api/funnel";
/// Transport deadline: best effort, never blocking a user command for long.
pub const SEND_TIMEOUT: Duration = Duration::from_secs(2);

/// Consent + delivery state (`<store-root>/funnel_share.json`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShareState {
    #[serde(default)]
    pub schema: u32,
    /// Written only by the explicit human-facing consent command.
    #[serde(default)]
    pub enabled: bool,
    /// Random uuidv4, generated locally at first consent; rotatable.
    #[serde(default)]
    pub install_id: Option<String>,
    #[serde(default)]
    pub enabled_at: Option<String>,
    #[serde(default)]
    pub last_sent_at: Option<String>,
    /// Bounded outcome label (`ok`, `http_<code>`, `network`, `dropped`).
    #[serde(default)]
    pub last_result: Option<String>,
    /// Last successfully sent envelope (dedup: identical envelopes skip).
    #[serde(default)]
    pub last_envelope: Option<Value>,
}

impl Default for ShareState {
    fn default() -> Self {
        Self {
            schema: SHARE_SCHEMA,
            enabled: false,
            install_id: None,
            enabled_at: None,
            last_sent_at: None,
            last_result: None,
            last_envelope: None,
        }
    }
}

/// Read the share ledger; a missing or malformed file means "not sharing".
#[must_use]
pub fn read_share(store_root: &Path) -> ShareState {
    std::fs::read_to_string(store_root.join(SHARE_STATE_FILE))
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_default()
}

fn save_share(store_root: &Path, state: &ShareState) -> std::io::Result<()> {
    std::fs::create_dir_all(store_root)?;
    let mut state = state.clone();
    if state.schema == 0 {
        state.schema = SHARE_SCHEMA;
    }
    let body = serde_json::to_string_pretty(&state).map_err(std::io::Error::other)?;
    let tmp = store_root.join(SHARE_TMP_FILE);
    std::fs::write(&tmp, body)?;
    std::fs::rename(&tmp, store_root.join(SHARE_STATE_FILE))
}

/// Whether sending is currently consented (and not kill-switched).
#[must_use]
pub fn sharing(store_root: &Path) -> bool {
    !funnel::disabled() && read_share(store_root).enabled
}

/// Mint a fresh install id without persisting it (the consent preview shows
/// the exact id that will be stored and sent).
#[must_use]
pub fn new_install_id() -> String {
    uuid::Uuid::new_v4().to_string()
}

/// Record consent with a caller-supplied id (mints one when `None`).
///
/// # Errors
/// I/O failures writing the share ledger.
pub fn enable_with(store_root: &Path, install_id: Option<String>) -> std::io::Result<ShareState> {
    let mut state = read_share(store_root);
    state.enabled = true;
    if let Some(id) = install_id {
        state.install_id = Some(id);
    }
    if state.install_id.is_none() {
        state.install_id = Some(new_install_id());
    }
    if state.enabled_at.is_none() {
        state.enabled_at = Some(now_rfc3339());
    }
    save_share(store_root, &state)?;
    Ok(state)
}

/// Record consent: enable sharing and mint the install id on first use.
///
/// # Errors
/// I/O failures writing the share ledger.
pub fn enable(store_root: &Path) -> std::io::Result<ShareState> {
    enable_with(store_root, None)
}

/// Stop all sharing; the install id is retained until an explicit reset.
///
/// # Errors
/// I/O failures writing the share ledger.
pub fn disable(store_root: &Path) -> std::io::Result<ShareState> {
    let mut state = read_share(store_root);
    state.enabled = false;
    save_share(store_root, &state)?;
    Ok(state)
}

/// Rotate the install id (the old id is retired; the server cannot be told,
/// it simply stops seeing it).
///
/// # Errors
/// I/O failures writing the share ledger.
pub fn reset_id(store_root: &Path) -> std::io::Result<ShareState> {
    let mut state = read_share(store_root);
    state.install_id = Some(uuid::Uuid::new_v4().to_string());
    state.last_envelope = None;
    save_share(store_root, &state)?;
    Ok(state)
}

/// Endpoint for this build (`WM_FUNNEL_ENDPOINT` wins).
#[must_use]
pub fn endpoint() -> String {
    std::env::var("WM_FUNNEL_ENDPOINT")
        .ok()
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| DEFAULT_ENDPOINT.to_string())
}

/// Session/memory counts in the `wm status` vocabulary: logical sessions are
/// `session.start` records, memories are the sum over memory galaxies.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Counts {
    pub sessions: u64,
    pub memories: u64,
}

/// Collect the envelope counts with the same semantics `wm status` uses.
#[must_use]
pub fn local_counts(store: &wm_memory::MemoryStore) -> Counts {
    let memories = wm_core::Galaxy::memory_galaxies()
        .iter()
        .map(|galaxy| store.count(*galaxy).unwrap_or(0) as u64)
        .sum();
    let sessions = store
        .count_by_tag(wm_core::Galaxy::Sessions, "start")
        .unwrap_or(0) as u64;
    Counts { sessions, memories }
}

/// Build the exact `funnel/1` payload for these state snapshots.
#[must_use]
pub fn build_envelope(
    store_root: &Path,
    state: &FunnelState,
    share: &ShareState,
    counts: Counts,
) -> Option<Value> {
    let install_id = share.install_id.as_deref()?;
    let (channel, reference) = if let Some(channel) = state.channel.clone() {
        (channel, state.channel_ref.clone())
    } else {
        let (detected, reference) = funnel::detect_channel(store_root);
        (detected.as_str().to_string(), reference)
    };
    let mut envelope = json!({
        "schema": ENVELOPE_SCHEMA,
        "install_id": install_id,
        "version": env!("CARGO_PKG_VERSION"),
        "os": funnel::platform_os(),
        "arch": funnel::platform_arch(),
        "channel": channel,
        "first_launch": state.first_launch,
        "milestones": state.milestones,
        "active_days": state.active_days,
        "counts": { "sessions": counts.sessions, "memories": counts.memories },
    });
    if let Some(reference) = reference {
        envelope["ref"] = Value::String(reference);
    }
    Some(envelope)
}

fn now_rfc3339() -> String {
    chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true)
}

/// HTTP poster seam: production wraps `ureq`, tests inject fakes.
pub trait Poster {
    /// POST the envelope; `Ok(())` only on a 2xx response.
    ///
    /// # Errors
    /// Network failure or a non-2xx status, as a bounded label.
    fn post(&self, url: &str, envelope: &Value) -> Result<(), String>;
}

/// `ureq` poster with the bounded deadline.
pub struct UreqPoster;

impl Poster for UreqPoster {
    fn post(&self, url: &str, envelope: &Value) -> Result<(), String> {
        let agent = ureq::config::Config::builder()
            .timeout_global(Some(SEND_TIMEOUT))
            .timeout_connect(Some(SEND_TIMEOUT))
            .build()
            .new_agent();
        match agent.post(url).send_json(envelope.clone()) {
            Ok(response) => {
                let status = response.status().as_u16();
                if (200..300).contains(&status) {
                    Ok(())
                } else {
                    Err(format!("http_{status}"))
                }
            }
            Err(ureq::Error::StatusCode(code)) => Err(format!("http_{code}")),
            Err(_) => Err("network".to_string()),
        }
    }
}

/// Send one envelope synchronously best effort.
///
/// On failure the envelope is spooled for a single retry (unless spooling
/// also fails, which is reported as `network`).
pub fn send_envelope(store_root: &Path, envelope: &Value, poster: &dyn Poster) -> String {
    match poster.post(&endpoint(), envelope) {
        Ok(()) => {
            let mut state = read_share(store_root);
            state.last_sent_at = Some(now_rfc3339());
            state.last_result = Some("ok".to_string());
            state.last_envelope = Some(envelope.clone());
            let _ = save_share(store_root, &state);
            let _ = std::fs::remove_file(store_root.join(PENDING_FILE));
            "ok".to_string()
        }
        Err(label) => {
            let spooled = save_pending(store_root, envelope, 0);
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

fn save_pending(store_root: &Path, envelope: &Value, attempts: u32) -> bool {
    let pending = json!({
        "spooled_at": now_rfc3339(),
        "attempts": attempts,
        "envelope": envelope,
    });
    let body = match serde_json::to_string_pretty(&pending) {
        Ok(body) => body,
        Err(_) => return false,
    };
    let tmp = store_root.join(PENDING_TMP_FILE);
    std::fs::write(&tmp, body).is_ok()
        && std::fs::rename(&tmp, store_root.join(PENDING_FILE)).is_ok()
}

fn read_pending(store_root: &Path) -> Option<(Value, u32)> {
    let text = std::fs::read_to_string(store_root.join(PENDING_FILE)).ok()?;
    let value: Value = serde_json::from_str(&text).ok()?;
    let envelope = value.get("envelope")?.clone();
    let attempts = value.get("attempts").and_then(Value::as_u64).unwrap_or(0);
    Some((envelope, u32::try_from(attempts).unwrap_or(0)))
}

/// Try the spooled envelope once; always clear the spool afterwards ("one
/// pending envelope is retried once, then dropped").
fn retry_pending(store_root: &Path, poster: &dyn Poster) {
    if let Some((envelope, _attempts)) = read_pending(store_root) {
        match poster.post(&endpoint(), &envelope) {
            Ok(()) => {
                let mut state = read_share(store_root);
                state.last_sent_at = Some(now_rfc3339());
                state.last_result = Some("ok".to_string());
                state.last_envelope = Some(envelope);
                let _ = save_share(store_root, &state);
            }
            Err(label) => {
                let mut state = read_share(store_root);
                state.last_result = Some(format!("{label}_dropped"));
                let _ = save_share(store_root, &state);
            }
        }
        let _ = std::fs::remove_file(store_root.join(PENDING_FILE));
    }
}

/// One worker pass: retry a spooled envelope once, then send the current
/// envelope if it differs from the last successful send.
///
/// Milestone changes send immediately; counts-only changes are throttled to
/// once per quiet period. Testable core of [`maybe_spawn`].
pub fn share_once(store_root: &Path, state: &FunnelState, counts: Counts, poster: &dyn Poster) {
    if !sharing(store_root) {
        return;
    }
    retry_pending(store_root, poster);
    let share = read_share(store_root);
    let Some(envelope) = build_envelope(store_root, state, &share, counts) else {
        return;
    };
    if share.last_envelope.as_ref() == Some(&envelope) {
        return;
    }
    if within_quiet_period(&share, &envelope) {
        return;
    }
    send_envelope(store_root, &envelope, poster);
}

/// Counts drift on every write; a launch whose milestone set is unchanged is
/// held to one send per hour. `last_sent_at` is set only on success, so an
/// offline machine retries each run (bounded by the spool rule).
fn within_quiet_period(share: &ShareState, envelope: &Value) -> bool {
    let Some(last_sent) = share.last_sent_at.as_deref() else {
        return false;
    };
    let Ok(last) = chrono::DateTime::parse_from_rfc3339(last_sent) else {
        return false;
    };
    let recent = chrono::Utc::now().signed_duration_since(last) < chrono::Duration::hours(1);
    let same_milestones = share
        .last_envelope
        .as_ref()
        .and_then(|value| value.get("milestones"))
        == envelope.get("milestones");
    recent && same_milestones
}

/// Detached best-effort share pass (never blocks the caller).
///
/// The caller supplies a state snapshot and counts collected synchronously
/// (cheap stat calls); the thread only performs the bounded network exchange
/// and ledger writes.
pub fn maybe_spawn(store_root: &Path, state: &FunnelState, counts: Counts) {
    if !sharing(store_root) {
        return;
    }
    let root = store_root.to_path_buf();
    let state = state.clone();
    std::thread::spawn(move || {
        share_once(&root, &state, counts, &UreqPoster);
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    struct FakePoster {
        fail: bool,
        calls: RefCell<Vec<Value>>,
    }

    impl FakePoster {
        fn ok() -> Self {
            Self {
                fail: false,
                calls: RefCell::new(Vec::new()),
            }
        }
        fn failing() -> Self {
            Self {
                fail: true,
                calls: RefCell::new(Vec::new()),
            }
        }
    }

    impl Poster for FakePoster {
        fn post(&self, _url: &str, envelope: &Value) -> Result<(), String> {
            if self.fail {
                Err("network".to_string())
            } else {
                self.calls.borrow_mut().push(envelope.clone());
                Ok(())
            }
        }
    }

    fn state_with_launch() -> FunnelState {
        FunnelState {
            schema: 1,
            first_launch: Some("2026-09-18T10:00:00Z".to_string()),
            first_launch_day: Some("2026-09-18".to_string()),
            channel: Some("install_sh".to_string()),
            channel_ref: Some("glama".to_string()),
            version: Some("9.2.0".to_string()),
            milestones: vec![
                "first_launch".to_string(),
                "init_ok".to_string(),
                "first_memory".to_string(),
            ],
            active_days: vec![0, 1],
        }
    }

    #[test]
    fn consent_lifecycle_generates_and_rotates_install_id() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        assert!(!sharing(root), "opt-in by default");
        let enabled = enable(root).unwrap();
        let id = enabled.install_id.expect("install id minted");
        assert!(uuid::Uuid::parse_str(&id).is_ok());
        assert!(sharing(root));
        let enabled_again = enable(root).unwrap();
        assert_eq!(
            enabled_again.install_id.as_deref(),
            Some(id.as_str()),
            "re-enabling keeps the id"
        );
        let disabled = disable(root).unwrap();
        assert!(!disabled.enabled);
        assert_eq!(disabled.install_id.as_deref(), Some(id.as_str()));
        assert!(!sharing(root));
        let rotated = reset_id(root).unwrap();
        assert_ne!(rotated.install_id.as_deref(), Some(id.as_str()));
        assert!(!root.join(SHARE_TMP_FILE).exists());
    }

    #[test]
    fn envelope_is_content_free_and_carries_the_decided_fields() {
        let tmp = tempfile::tempdir().unwrap();
        let share = enable(tmp.path()).unwrap();
        let envelope = build_envelope(
            tmp.path(),
            &state_with_launch(),
            &share,
            Counts {
                sessions: 3,
                memories: 12,
            },
        )
        .unwrap();
        assert_eq!(envelope["schema"], "funnel/1");
        assert_eq!(envelope["channel"], "install_sh");
        assert_eq!(envelope["ref"], "glama");
        assert_eq!(envelope["counts"]["sessions"], 3);
        assert_eq!(envelope["counts"]["memories"], 12);
        assert_eq!(envelope["active_days"], json!([0, 1]));
        assert_eq!(envelope["milestones"].as_array().unwrap().len(), 3);
        let text = serde_json::to_string(&envelope).unwrap();
        for banned in ["/home/", "/Users/", "prompt", "content"] {
            assert!(!text.contains(banned), "envelope must not carry {banned}");
        }
    }

    #[test]
    fn no_install_id_means_no_envelope() {
        let tmp = tempfile::tempdir().unwrap();
        let envelope = build_envelope(
            tmp.path(),
            &state_with_launch(),
            &ShareState::default(),
            Counts::default(),
        );
        assert!(envelope.is_none(), "no consent, no envelope");
    }

    #[test]
    fn share_once_dedups_identical_envelopes() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        enable(root).unwrap();
        let poster = FakePoster::ok();
        let state = state_with_launch();
        share_once(root, &state, Counts::default(), &poster);
        assert_eq!(poster.calls.borrow().len(), 1);
        share_once(root, &state, Counts::default(), &poster);
        assert_eq!(poster.calls.borrow().len(), 1, "identical envelope skips");
        let mut changed = state;
        changed.milestones.push("first_resume".to_string());
        share_once(root, &changed, Counts::default(), &poster);
        assert_eq!(poster.calls.borrow().len(), 2, "new milestone sends");
        assert!(read_share(root).last_sent_at.is_some());
    }

    #[test]
    fn failed_send_spools_once_then_drops_after_retry() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        enable(root).unwrap();
        let fail = FakePoster::failing();
        share_once(root, &state_with_launch(), Counts::default(), &fail);
        assert!(root.join(PENDING_FILE).exists(), "offline envelope spooled");
        let ok = FakePoster::ok();
        share_once(root, &state_with_launch(), Counts::default(), &ok);
        assert!(
            !root.join(PENDING_FILE).exists(),
            "pending retried once then cleared"
        );
        assert_eq!(
            ok.calls.borrow().len(),
            1,
            "the retried envelope delivers once; the identical current one is deduped"
        );
    }

    #[test]
    fn disabled_share_never_posts() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        let enabled = enable(root).unwrap();
        disable(root).unwrap();
        let poster = FakePoster::ok();
        share_once(root, &state_with_launch(), Counts::default(), &poster);
        assert!(poster.calls.borrow().is_empty());
        assert!(enabled.install_id.is_some());
    }
}
