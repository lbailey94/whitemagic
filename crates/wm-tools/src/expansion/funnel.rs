//! Local install-funnel instrumentation (scope 1) — activation evidence.
//!
//! The funnel answers "did an install activate?" without any transmission:
//! milestones are recorded as typed `telemetry.funnel` rows in the existing
//! `telemetry` galaxy (evidence, not cognition — same exclusions apply), and
//! the authoritative milestone ledger lives beside the store in
//! `<store-root>/funnel_state.json` (atomic rename on write, mirroring
//! `profile_contract.json` / `landlock_state.json`).
//!
//! Scope 1 only: no transport, no consent surface, no install-id. Nothing
//! leaves the device; `wm telemetry status` is display-only and read-only.
//!
//! - `record_launch` — first writable server init on a store: `first_launch`,
//!   `init_ok`, and `active_dN` for calendar day N ≥ 1 after the first launch
//!   (deterministic UTC-midnight timestamp, so retries deduplicate).
//! - `record_tool_milestone` — a successful `memory.create` / `session.record`
//!   emits `first_memory`; a successful `session.continuity` with ≥ 1 prior
//!   turn emits `first_resume`. One record each, ever.
//!
//! Channel attribution is best effort and content-free: `WM_INSTALL_CHANNEL`
//! (npm/docker launchers), the installer's `<store-root>/install_channel`
//! marker (`install_sh[:ref]`), a `/.dockerenv` probe, the binary path
//! heuristic, or `install.json`'s `installed_via`. The vocabulary is exactly
//! the site's `INSTALL_CHANNELS` (`whitemagic-site/lib/telemetry.ts`).
//!
//! Kill switch: `WM_FUNNEL_DISABLED=1` suppresses all emissions (reads and
//! `wm telemetry status` keep working).

#![forbid(unsafe_code)]

use std::path::Path;

use chrono::{DateTime, NaiveDate, SecondsFormat, Utc};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use wm_core::Galaxy;
use wm_memory::MemoryQuery;
use wm_memory::MemoryStore;
use wm_memory::search::SearchEngine;

use super::telemetry_tools;

/// Record kind for funnel milestone rows.
pub const FUNNEL_KIND: &str = "telemetry.funnel";
/// Marker file written by `scripts/install.sh` (content `install_sh[:ref]`).
pub const INSTALL_CHANNEL_FILE: &str = "install_channel";
/// Authoritative milestone ledger beside `install.json` / `landlock_state.json`.
pub const FUNNEL_STATE_FILE: &str = "funnel_state.json";
const STATE_TMP_FILE: &str = ".funnel_state.json.tmp";
const STATE_SCHEMA: u32 = 1;
const SOURCE: &str = "wm-funnel";
/// Site middleware ref cap (`whitemagic-site/middleware.ts`).
const REF_CAP: usize = 24;

pub const M_FIRST_LAUNCH: &str = "first_launch";
pub const M_INIT_OK: &str = "init_ok";
pub const M_FIRST_MEMORY: &str = "first_memory";
pub const M_FIRST_RESUME: &str = "first_resume";

/// Transport disclosure shared by the CLI status output and the schema text.
pub const TRANSPORT_LINE: &str =
    "none — records stay on-device; no share command exists in this build";

/// Installation channel vocabulary — identical to the site's
/// `INSTALL_CHANNELS` set.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Channel {
    InstallSh,
    Binary,
    Npm,
    Docker,
    Cargo,
    Source,
    Unknown,
}

impl Channel {
    /// Site-vocabulary spelling.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::InstallSh => "install_sh",
            Self::Binary => "binary",
            Self::Npm => "npm",
            Self::Docker => "docker",
            Self::Cargo => "cargo",
            Self::Source => "source",
            Self::Unknown => "unknown",
        }
    }

    /// Parse a site-vocabulary channel name (case-insensitive).
    #[must_use]
    pub fn parse(value: &str) -> Option<Self> {
        match value.to_ascii_lowercase().as_str() {
            "install_sh" => Some(Self::InstallSh),
            "binary" => Some(Self::Binary),
            "npm" => Some(Self::Npm),
            "docker" => Some(Self::Docker),
            "cargo" => Some(Self::Cargo),
            "source" => Some(Self::Source),
            "unknown" => Some(Self::Unknown),
            _ => None,
        }
    }

    /// Map an `installed_via` label (`crates/wm-mcp/src/update.rs`
    /// `detect_installed_via` vocabulary) onto the site channel set.
    /// Homebrew formula installs are source-distributed, hence `source`.
    #[must_use]
    pub fn from_installed_via(via: &str) -> Self {
        match via.trim().to_ascii_lowercase().as_str() {
            "cargo" => Self::Cargo,
            "npm" => Self::Npm,
            "homebrew" => Self::Source,
            "release-binary" => Self::Binary,
            _ => Self::Unknown,
        }
    }
}

/// Lowercase, `[a-z0-9_-]`, capped at 24 chars — the exact sanitization the
/// site middleware applies to `install.sh?ref=` (`middleware.ts`). Empty
/// results become `None` (no ref recorded).
#[must_use]
pub fn sanitize_ref(raw: &str) -> Option<String> {
    let cleaned: String = raw
        .chars()
        .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-')
        .map(|c| c.to_ascii_lowercase())
        .collect();
    let capped: String = cleaned.chars().take(REF_CAP).collect();
    if capped.is_empty() {
        None
    } else {
        Some(capped)
    }
}

fn parse_channel_with_ref(raw: &str) -> Option<(Channel, Option<String>)> {
    let raw = raw.trim();
    if raw.is_empty() {
        return None;
    }
    let (name, reference) = match raw.split_once(':') {
        Some((name, reference)) => (name, sanitize_ref(reference)),
        None => (raw, None),
    };
    let channel = Channel::parse(name)?;
    Some((channel, reference))
}

/// `installed_via` heuristic for a binary path.
///
/// Kept byte-for-byte in sync with `wm_mcp::update::detect_installed_via`
/// (which cannot be called from here: `wm-mcp` depends on `wm-tools`, not the
/// other way around); the `funnel_detection_matches_wm_update` test in
/// `wm-mcp` pins the parity.
#[must_use]
pub fn installed_via_from_exe(exe: &Path) -> &'static str {
    let p = exe.display().to_string();
    if p.contains("/.cargo/bin/") {
        "cargo"
    } else if p.contains("/Cellar/") || p.contains("/homebrew/") {
        "homebrew"
    } else if p.contains("/node_modules/") || p.contains("/npm/") {
        "npm"
    } else {
        "release-binary"
    }
}

/// Pure channel classifier. Precedence:
/// `WM_INSTALL_CHANNEL` → `<store>/install_channel` → `/.dockerenv` →
/// exe path heuristic → `install.json` `installed_via` → `unknown`.
///
/// An explicit but unrecognized env/marker value classifies as `unknown`
/// rather than falling through: an instrumentation value that cannot be
/// understood is not evidence for any other channel.
#[must_use]
pub fn classify_channel(
    channel_file: Option<&str>,
    env_channel: Option<&str>,
    in_container: bool,
    exe: Option<&Path>,
    install_json_via: Option<&str>,
) -> (Channel, Option<String>) {
    if let Some(raw) = env_channel.filter(|raw| !raw.trim().is_empty()) {
        return parse_channel_with_ref(raw).unwrap_or((Channel::Unknown, None));
    }
    if let Some(raw) = channel_file.filter(|raw| !raw.trim().is_empty()) {
        if let Some(parsed) = parse_channel_with_ref(raw) {
            return parsed;
        }
    }
    if in_container {
        return (Channel::Docker, None);
    }
    if let Some(exe) = exe {
        let channel = Channel::from_installed_via(installed_via_from_exe(exe));
        if channel != Channel::Unknown {
            return (channel, None);
        }
    }
    if let Some(via) = install_json_via {
        let channel = Channel::from_installed_via(via);
        if channel != Channel::Unknown {
            return (channel, None);
        }
    }
    (Channel::Unknown, None)
}

/// Gather the classifier inputs from the environment and filesystem.
/// Best effort: any unreadable input simply drops out of the precedence.
#[must_use]
pub fn detect_channel(store_root: &Path) -> (Channel, Option<String>) {
    let channel_file = std::fs::read_to_string(store_root.join(INSTALL_CHANNEL_FILE)).ok();
    let env_channel = std::env::var("WM_INSTALL_CHANNEL").ok();
    let in_container = Path::new("/.dockerenv").exists();
    let exe = std::env::current_exe().ok();
    let install_json_via = install_via_from_json(store_root);
    classify_channel(
        channel_file.as_deref(),
        env_channel.as_deref(),
        in_container,
        exe.as_deref(),
        install_json_via.as_deref(),
    )
}

/// `installed_via` from `<store-root>/install.json`, without depending on the
/// `wm-mcp` reader (crate layering).
fn install_via_from_json(store_root: &Path) -> Option<String> {
    let text = std::fs::read_to_string(store_root.join("install.json")).ok()?;
    let value: Value = serde_json::from_str(&text).ok()?;
    value
        .get("installed_via")
        .and_then(Value::as_str)
        .map(str::to_string)
}

/// Parse an `install_channel` marker body into `(channel, ref)`.
#[must_use]
pub fn parse_marker(content: &str) -> Option<(String, Option<String>)> {
    let (channel, reference) = parse_channel_with_ref(content)?;
    Some((channel.as_str().to_string(), reference))
}

/// Platform label in the site vocabulary (`linux|macos|windows|other`).
#[must_use]
pub fn platform_os() -> &'static str {
    match std::env::consts::OS {
        "linux" => "linux",
        "macos" => "macos",
        "windows" => "windows",
        _ => "other",
    }
}

/// Arch label in the site vocabulary (`x86_64|aarch64|other`).
#[must_use]
pub fn platform_arch() -> &'static str {
    match std::env::consts::ARCH {
        "x86_64" => "x86_64",
        "aarch64" => "aarch64",
        _ => "other",
    }
}

/// Whether a milestone string is part of the funnel contract.
#[must_use]
pub fn is_known_milestone(milestone: &str) -> bool {
    matches!(
        milestone,
        M_FIRST_LAUNCH | M_INIT_OK | M_FIRST_MEMORY | M_FIRST_RESUME
    ) || milestone
        .strip_prefix("active_d")
        .is_some_and(|day| !day.is_empty() && day.chars().all(|c| c.is_ascii_digit()))
}

/// `WM_FUNNEL_DISABLED=1` (or `true`) suppresses all emissions.
#[must_use]
pub fn disabled() -> bool {
    std::env::var("WM_FUNNEL_DISABLED").is_ok_and(|v| v == "1" || v == "true")
}

/// Authoritative milestone ledger (`<store-root>/funnel_state.json`).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct FunnelState {
    #[serde(default)]
    pub schema: u32,
    /// RFC 3339 first-launch timestamp.
    #[serde(default)]
    pub first_launch: Option<String>,
    /// UTC calendar day (`YYYY-MM-DD`) of the first launch.
    #[serde(default)]
    pub first_launch_day: Option<String>,
    /// Classified channel at first launch.
    #[serde(default)]
    pub channel: Option<String>,
    /// Sanitized channel ref at first launch (if any).
    #[serde(default)]
    pub channel_ref: Option<String>,
    /// Product version at first launch.
    #[serde(default)]
    pub version: Option<String>,
    /// Emitted milestone strings (including `active_dN`).
    #[serde(default)]
    pub milestones: Vec<String>,
    /// UTC day offsets with an emitted `active_dN` record.
    #[serde(default)]
    pub active_days: Vec<u32>,
}

/// Read the ledger if present (no store needed).
#[must_use]
pub fn read_state(store_root: &Path) -> Option<FunnelState> {
    let text = std::fs::read_to_string(store_root.join(FUNNEL_STATE_FILE)).ok()?;
    serde_json::from_str(&text).ok()
}

/// Atomically persist the ledger (tmp + rename, the
/// `profile_contract.json` pattern).
fn save_state(store_root: &Path, state: &FunnelState) -> std::io::Result<()> {
    std::fs::create_dir_all(store_root)?;
    let mut state = state.clone();
    if state.schema == 0 {
        state.schema = STATE_SCHEMA;
    }
    state.milestones.sort();
    state.milestones.dedup();
    state.active_days.sort_unstable();
    state.active_days.dedup();
    let path = store_root.join(FUNNEL_STATE_FILE);
    let tmp = store_root.join(STATE_TMP_FILE);
    let body = serde_json::to_string_pretty(&state).map_err(std::io::Error::other)?;
    std::fs::write(&tmp, body)?;
    std::fs::rename(&tmp, &path)
}

/// Rebuild the ledger from the funnel-tagged records in the `telemetry`
/// galaxy.
///
/// Used when the state file is missing (fingerprint loss: reinstall, store
/// restore from a snapshot predating the ledger). The tag index is the
/// filter — every `funnel`-tagged row is read, with no key-order row cap
/// (a fixed 4096-row scan could silently miss a milestone and re-emit it
/// with a fresh timestamp). Rows absent from the galaxy (e.g. purged) are
/// unrecoverable and will be re-emitted.
#[must_use]
pub fn rebuild_from_galaxy(store: &MemoryStore) -> FunnelState {
    let mut state = FunnelState {
        schema: STATE_SCHEMA,
        ..FunnelState::default()
    };
    let memories = store
        .query(
            Galaxy::Telemetry,
            &MemoryQuery::new()
                .with_tags(vec!["funnel".to_string()])
                .with_limit(usize::MAX),
        )
        .unwrap_or_default();
    for memory in &memories {
        if !memory.metadata.tags.iter().any(|t| t == "funnel") {
            continue;
        }
        let Ok(record) = serde_json::from_str::<Value>(&memory.content) else {
            continue;
        };
        if record.get("kind").and_then(Value::as_str) != Some(FUNNEL_KIND) {
            continue;
        }
        let Some(milestone) = record.get("milestone").and_then(Value::as_str) else {
            continue;
        };
        if milestone == M_FIRST_LAUNCH {
            let ts = record.get("ts").and_then(Value::as_str).map(str::to_string);
            let candidate_day = ts.as_deref().and_then(utc_day);
            let current_day = state.first_launch.as_deref().and_then(utc_day);
            let earlier = match (state.first_launch.as_ref(), candidate_day, current_day) {
                (None, _, _) => true,
                (Some(_), Some(candidate), Some(current)) => candidate < current,
                _ => false,
            };
            if earlier {
                state.first_launch = ts;
                state.first_launch_day = candidate_day.map(|day| day.to_string());
                state.channel = record
                    .get("channel")
                    .and_then(Value::as_str)
                    .map(str::to_string);
                state.version = record
                    .get("version")
                    .and_then(Value::as_str)
                    .map(str::to_string);
            }
        }
        if milestone.starts_with("active_d") {
            if let Some(offset) = record.get("day_offset").and_then(Value::as_u64) {
                if let Ok(offset) = u32::try_from(offset) {
                    state.active_days.push(offset);
                }
            }
        }
        if !state.milestones.iter().any(|m| m == milestone) {
            state.milestones.push(milestone.to_string());
        }
    }
    state.milestones.sort();
    state.milestones.dedup();
    state.active_days.sort_unstable();
    state.active_days.dedup();
    state
}

fn utc_day(ts: &str) -> Option<NaiveDate> {
    DateTime::parse_from_rfc3339(ts)
        .ok()
        .map(|stamp| stamp.with_timezone(&Utc).date_naive())
}

fn utc_midnight(day: NaiveDate) -> String {
    let naive = day.and_hms_opt(0, 0, 0).unwrap_or_default();
    DateTime::<Utc>::from_naive_utc_and_offset(naive, Utc)
        .to_rfc3339_opts(SecondsFormat::Secs, true)
}

/// Load the ledger, rebuilding from the galaxy when the file is missing.
fn load_or_rebuild(store: &MemoryStore, store_root: &Path) -> FunnelState {
    read_state(store_root).unwrap_or_else(|| rebuild_from_galaxy(store))
}

/// Emit one funnel record through the centralized telemetry store path
/// (tags/class/ceiling discipline stays there). Returns `Some(deduplicated)`
/// when the record is present in the galaxy after the call, `None` on a
/// store failure.
fn emit(store: &MemoryStore, search: Option<&SearchEngine>, record: &Value) -> Option<bool> {
    match telemetry_tools::store_record(store, search, record, FUNNEL_KIND, SOURCE) {
        Ok((_id, deduplicated)) => Some(deduplicated),
        Err(e) => {
            tracing::warn!(error = %e, "funnel milestone store failed");
            None
        }
    }
}

fn push_milestone(state: &mut FunnelState, milestone: &str) {
    if !state.milestones.iter().any(|m| m == milestone) {
        state.milestones.push(milestone.to_string());
    }
}

/// Record launch-time milestones once per store.
///
/// `first_launch`, `init_ok`, and `active_dN` for a launch on UTC day N ≥ 1
/// after the first launch (deterministic UTC-midnight timestamp — a retried
/// emission deduplicates).
///
/// Returns the number of newly written records. Best effort: a failed store
/// write only warns and leaves the milestone pending for the next launch.
#[must_use]
pub fn record_launch(
    store: &MemoryStore,
    search: Option<&SearchEngine>,
    store_root: &Path,
) -> usize {
    if disabled() {
        return 0;
    }
    let now = Utc::now();
    let today = now.date_naive();
    let version = env!("CARGO_PKG_VERSION");
    let mut state = load_or_rebuild(store, store_root);
    let mut emitted = 0_usize;

    if state.first_launch.is_none() {
        let (channel, reference) = detect_channel(store_root);
        let record = json!({
            "kind": FUNNEL_KIND,
            "ts": now.to_rfc3339_opts(SecondsFormat::Secs, true),
            "milestone": M_FIRST_LAUNCH,
            "channel": channel.as_str(),
            "version": version,
            "os": platform_os(),
            "arch": platform_arch(),
        });
        if let Some(deduplicated) = emit(store, search, &record) {
            state.first_launch = Some(now.to_rfc3339_opts(SecondsFormat::Secs, true));
            state.first_launch_day = Some(today.to_string());
            state.channel = Some(channel.as_str().to_string());
            state.channel_ref = reference;
            state.version = Some(version.to_string());
            push_milestone(&mut state, M_FIRST_LAUNCH);
            emitted += usize::from(!deduplicated);
        }
    }

    if !state.milestones.iter().any(|m| m == M_INIT_OK) {
        let record = json!({
            "kind": FUNNEL_KIND,
            "ts": now.to_rfc3339_opts(SecondsFormat::Secs, true),
            "milestone": M_INIT_OK,
            "version": version,
        });
        if emit(store, search, &record).is_some() {
            push_milestone(&mut state, M_INIT_OK);
            emitted += 1;
        }
    }

    let first_day = state
        .first_launch_day
        .as_deref()
        .and_then(|day| NaiveDate::parse_from_str(day, "%Y-%m-%d").ok())
        .or_else(|| state.first_launch.as_deref().and_then(utc_day));
    if let Some(first_day) = first_day {
        if let Ok(offset) = u32::try_from(today.signed_duration_since(first_day).num_days()) {
            if offset >= 1 && !state.active_days.contains(&offset) {
                let milestone = format!("active_d{offset}");
                let record = json!({
                    "kind": FUNNEL_KIND,
                    "ts": utc_midnight(today),
                    "milestone": milestone,
                    "version": version,
                    "day_offset": offset,
                });
                if emit(store, search, &record).is_some() {
                    state.active_days.push(offset);
                    push_milestone(&mut state, &milestone);
                    emitted += 1;
                }
            }
        }
    }

    if let Err(e) = save_state(store_root, &state) {
        tracing::warn!(error = %e, "funnel state could not be persisted");
    }
    emitted
}

/// Record tool-driven milestones once per store.
///
/// `first_memory` on the first successful `memory.create` / `session.record`,
/// `first_resume` on the first successful `session.continuity` that recovered
/// at least one prior turn (`count >= 1` with a non-null `previous_session`).
///
/// Returns the number of newly written records.
#[must_use]
pub fn record_tool_milestone(
    store: &MemoryStore,
    search: Option<&SearchEngine>,
    store_root: &Path,
    tool: &str,
    response: Option<&Value>,
) -> usize {
    if disabled() {
        return 0;
    }
    let milestone = match tool {
        "memory.create" | "session.record" => M_FIRST_MEMORY,
        "session.continuity" => {
            let recovered = response.is_some_and(|value| {
                value.get("count").and_then(Value::as_u64).unwrap_or(0) >= 1
                    && value
                        .get("previous_session")
                        .is_some_and(|previous| !previous.is_null())
            });
            if !recovered {
                return 0;
            }
            M_FIRST_RESUME
        }
        _ => return 0,
    };
    let mut state = load_or_rebuild(store, store_root);
    if state.milestones.iter().any(|m| m == milestone) {
        return 0;
    }
    let record = json!({
        "kind": FUNNEL_KIND,
        "ts": Utc::now().to_rfc3339_opts(SecondsFormat::Secs, true),
        "milestone": milestone,
        "version": env!("CARGO_PKG_VERSION"),
    });
    if let Some(deduplicated) = emit(store, search, &record) {
        push_milestone(&mut state, milestone);
        if let Err(e) = save_state(store_root, &state) {
            tracing::warn!(error = %e, "funnel state could not be persisted");
        }
        usize::from(!deduplicated)
    } else {
        0
    }
}

/// Read-only funnel report for `wm telemetry status`: works with no store,
/// never takes an LMDB writer lock (inspection opens only), writes nothing.
#[must_use]
pub fn status_report(store_root: &Path) -> Value {
    let state = read_state(store_root);
    let mut channel = state.as_ref().and_then(|s| s.channel.clone());
    let mut channel_ref = state.as_ref().and_then(|s| s.channel_ref.clone());
    let mut first_launch = state.as_ref().and_then(|s| s.first_launch.clone());
    let mut milestones = state
        .as_ref()
        .map(|s| s.milestones.clone())
        .unwrap_or_default();
    let mut active_days = state
        .as_ref()
        .map(|s| s.active_days.clone())
        .unwrap_or_default();

    let lmdb = store_root.join("lmdb");
    let store_present = lmdb.join("data.mdb").exists();
    if (channel.is_none() || first_launch.is_none()) && store_present {
        if let Ok(store) = MemoryStore::open_inspection(&lmdb) {
            let rebuilt = rebuild_from_galaxy(&store);
            if channel.is_none() {
                channel = rebuilt.channel;
            }
            if first_launch.is_none() {
                first_launch = rebuilt.first_launch;
            }
            if milestones.is_empty() {
                milestones = rebuilt.milestones;
            }
            if active_days.is_empty() {
                active_days = rebuilt.active_days;
            }
        }
    }
    if channel.is_none() {
        let (detected, reference) = detect_channel(store_root);
        channel = Some(detected.as_str().to_string());
        channel_ref = reference;
    }

    json!({
        "status": "success",
        "read_only": true,
        "store": store_root.display().to_string(),
        "store_present": store_present,
        "channel": channel,
        "channel_ref": channel_ref,
        "first_launch": first_launch,
        "milestones": milestones,
        "active_days": active_days,
        "state_file": state.is_some(),
        "transport": TRANSPORT_LINE,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn open_store() -> (tempfile::TempDir, MemoryStore) {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path().join("lmdb")).unwrap();
        (tmp, store)
    }

    fn funnel_records(store: &MemoryStore) -> Vec<Value> {
        store
            .scan(Galaxy::Telemetry, 512)
            .unwrap()
            .into_iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "funnel"))
            .filter_map(|m| serde_json::from_str::<Value>(&m.content).ok())
            .collect()
    }

    #[test]
    fn channel_vocabulary_matches_the_site() {
        for (channel, name) in [
            (Channel::InstallSh, "install_sh"),
            (Channel::Binary, "binary"),
            (Channel::Npm, "npm"),
            (Channel::Docker, "docker"),
            (Channel::Cargo, "cargo"),
            (Channel::Source, "source"),
            (Channel::Unknown, "unknown"),
        ] {
            assert_eq!(channel.as_str(), name);
            assert_eq!(Channel::parse(name), Some(channel));
        }
        assert_eq!(Channel::parse("install-sh"), None, "site spelling only");
    }

    #[test]
    fn classifier_precedence_and_ref_sanitization() {
        let exe = Path::new("/home/u/.cargo/bin/wm");
        // WM_INSTALL_CHANNEL wins over everything.
        assert_eq!(
            classify_channel(Some("install_sh:hero"), Some("npm"), false, Some(exe), None),
            (Channel::Npm, None)
        );
        // Marker wins over container/exe/install.json.
        assert_eq!(
            classify_channel(
                Some("install_sh:HERO!!2026"),
                None,
                true,
                Some(exe),
                Some("cargo")
            ),
            (Channel::InstallSh, Some("hero2026".to_string()))
        );
        // Ref sanitization: lowercased, [a-z0-9_-], capped at 24.
        let (_, reference) = classify_channel(
            Some(&format!("install_sh:{}", "A".repeat(40))),
            None,
            false,
            None,
            None,
        );
        assert_eq!(reference, Some("a".repeat(24)));
        // Container probe.
        assert_eq!(
            classify_channel(None, None, true, Some(exe), None),
            (Channel::Docker, None)
        );
        // Exe heuristic maps onto the site set; homebrew is source-distributed.
        assert_eq!(
            classify_channel(None, None, false, Some(exe), None),
            (Channel::Cargo, None)
        );
        assert_eq!(
            classify_channel(
                None,
                None,
                false,
                Some(Path::new("/opt/homebrew/bin/wm")),
                None
            ),
            (Channel::Source, None)
        );
        assert_eq!(
            classify_channel(
                None,
                None,
                false,
                Some(Path::new("/usr/local/bin/wm")),
                None
            ),
            (Channel::Binary, None)
        );
        // install.json is consulted after the exe heuristic.
        assert_eq!(
            classify_channel(None, None, false, Some(exe), Some("npm")),
            (Channel::Cargo, None)
        );
        assert_eq!(
            classify_channel(None, None, false, None, Some("npm")),
            (Channel::Npm, None)
        );
        // Unknown env value stays unknown (explicit but unrecognized).
        assert_eq!(
            classify_channel(None, Some("mystery"), false, None, Some("npm")),
            (Channel::Unknown, None)
        );
        // Nothing matches.
        assert_eq!(
            classify_channel(None, None, false, None, None),
            (Channel::Unknown, None)
        );
    }

    #[test]
    fn sanitize_ref_matches_site_middleware() {
        assert_eq!(sanitize_ref("Hero-Ref_2"), Some("hero-ref_2".to_string()));
        assert_eq!(sanitize_ref("!!!"), None);
        assert_eq!(sanitize_ref(""), None);
        assert_eq!(
            sanitize_ref("abcdefghijklmnopqrstuvwxyz0123456789"),
            Some("abcdefghijklmnopqrstuvwx".to_string())
        );
    }

    #[test]
    fn record_launch_emits_first_launch_and_init_ok_once() {
        let (tmp, store) = open_store();
        let root = tmp.path();
        // A marker makes the channel deterministic without touching env.
        std::fs::write(root.join(INSTALL_CHANNEL_FILE), "install_sh:hero\n").unwrap();
        let emitted = record_launch(&store, None, root);
        assert_eq!(emitted, 2, "first_launch + init_ok");
        let records = funnel_records(&store);
        assert_eq!(records.len(), 2);
        let launch = records
            .iter()
            .find(|r| r["milestone"] == M_FIRST_LAUNCH)
            .unwrap();
        assert_eq!(launch["channel"], "install_sh");
        assert_eq!(launch["version"], env!("CARGO_PKG_VERSION"));
        assert!(launch["os"].is_string() && launch["arch"].is_string());
        assert!(records.iter().any(|r| r["milestone"] == M_INIT_OK));

        // State ledger exists and is authoritative on the second launch.
        let state = read_state(root).expect("state ledger written");
        assert_eq!(state.channel.as_deref(), Some("install_sh"));
        assert_eq!(state.channel_ref.as_deref(), Some("hero"));
        assert_eq!(record_launch(&store, None, root), 0, "milestones fire once");
        assert_eq!(funnel_records(&store).len(), 2);
        assert!(
            !root.join(STATE_TMP_FILE).exists(),
            "atomic write must not leave the tmp file behind"
        );
    }

    #[test]
    fn rebuilt_state_prevents_reemission_when_ledger_is_lost() {
        let (tmp, store) = open_store();
        let root = tmp.path();
        std::fs::write(root.join(INSTALL_CHANNEL_FILE), "install_sh\n").unwrap();
        assert_eq!(record_launch(&store, None, root), 2);
        std::fs::remove_file(root.join(FUNNEL_STATE_FILE)).unwrap();
        assert_eq!(
            record_launch(&store, None, root),
            0,
            "galaxy rebuild recovers emitted milestones"
        );
        let state = read_state(root).expect("ledger re-persisted from the rebuild");
        assert!(state.milestones.iter().any(|m| m == M_FIRST_LAUNCH));
        assert!(state.milestones.iter().any(|m| m == M_INIT_OK));
        assert_eq!(state.channel.as_deref(), Some("install_sh"));
    }

    #[test]
    fn active_day_emitted_once_with_midnight_timestamp() {
        let (tmp, store) = open_store();
        let root = tmp.path();
        let today = Utc::now().date_naive();
        let first = today - chrono::Duration::days(2);
        let state = FunnelState {
            schema: 1,
            first_launch: Some(utc_midnight(first)),
            first_launch_day: Some(first.to_string()),
            channel: Some("npm".to_string()),
            version: Some("test".to_string()),
            milestones: vec![M_FIRST_LAUNCH.to_string(), M_INIT_OK.to_string()],
            active_days: vec![],
            ..FunnelState::default()
        };
        std::fs::write(
            root.join(FUNNEL_STATE_FILE),
            serde_json::to_string(&state).unwrap(),
        )
        .unwrap();
        assert_eq!(record_launch(&store, None, root), 1, "active_d2 once");
        let records = funnel_records(&store);
        let active = records
            .iter()
            .find(|r| r["milestone"] == "active_d2")
            .expect("active_d2 record");
        assert_eq!(active["day_offset"], 2);
        assert_eq!(active["ts"], utc_midnight(today));
        assert_eq!(
            record_launch(&store, None, root),
            0,
            "same day offset never repeats"
        );
    }

    #[test]
    fn tool_milestones_fire_once_with_the_documented_triggers() {
        let (tmp, store) = open_store();
        let root = tmp.path();
        let empty = json!({"status": "success", "previous_session": null, "count": 0});
        assert_eq!(
            record_tool_milestone(&store, None, root, "session.continuity", Some(&empty)),
            0,
            "no prior turn → no first_resume"
        );
        assert_eq!(
            record_tool_milestone(&store, None, root, "memory.create", None),
            1
        );
        assert_eq!(
            record_tool_milestone(&store, None, root, "session.record", None),
            0,
            "first_memory is once"
        );
        let hit = json!({"status": "success", "previous_session": "abc", "count": 3});
        assert_eq!(
            record_tool_milestone(&store, None, root, "session.continuity", Some(&hit)),
            1
        );
        assert_eq!(
            record_tool_milestone(&store, None, root, "session.continuity", Some(&hit)),
            0,
            "first_resume is once"
        );
        assert_eq!(
            record_tool_milestone(&store, None, root, "memory.search", Some(&hit)),
            0,
            "unrelated tools record nothing"
        );
        let milestones: Vec<String> = funnel_records(&store)
            .iter()
            .filter_map(|r| r["milestone"].as_str().map(str::to_string))
            .collect();
        assert!(milestones.contains(&M_FIRST_MEMORY.to_string()));
        assert!(milestones.contains(&M_FIRST_RESUME.to_string()));
    }

    #[test]
    fn status_report_is_read_only_and_survives_a_missing_store() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        std::fs::write(root.join(INSTALL_CHANNEL_FILE), "install_sh:hero\n").unwrap();
        let report = status_report(root);
        assert_eq!(report["read_only"], true);
        assert_eq!(report["channel"], "install_sh");
        assert_eq!(report["channel_ref"], "hero");
        assert_eq!(report["first_launch"], Value::Null);
        assert_eq!(report["state_file"], false);
        assert!(
            report["transport"].as_str().unwrap().starts_with("none"),
            "transport posture must be disclosed: {report}"
        );
        assert!(
            !root.join("lmdb").exists(),
            "status must not create the store"
        );

        // With a store but no ledger, the galaxy rebuild fills the report.
        let (tmp2, store) = open_store();
        let root2 = tmp2.path();
        let _ = record_launch(&store, None, root2);
        std::fs::remove_file(root2.join(FUNNEL_STATE_FILE)).unwrap();
        let report = status_report(root2);
        assert_eq!(report["store_present"], true);
        assert!(report["first_launch"].is_string());
        assert!(
            report["milestones"]
                .as_array()
                .unwrap()
                .iter()
                .any(|m| m == M_FIRST_LAUNCH),
            "galaxy fallback must recover milestones"
        );
        assert_eq!(report["state_file"], false);
    }

    #[test]
    fn funnel_records_pass_the_typed_path_validation() {
        // The emitter must produce records the typed telemetry path accepts.
        let record = json!({
            "kind": FUNNEL_KIND,
            "ts": "2026-09-18T00:00:00Z",
            "milestone": "active_d2",
            "version": "9.1.9",
            "day_offset": 2,
        });
        assert_eq!(
            telemetry_tools::validate_record(&record).unwrap(),
            FUNNEL_KIND
        );
    }

    #[test]
    fn milestone_vocabulary_is_bounded() {
        assert!(is_known_milestone("first_launch"));
        assert!(is_known_milestone("active_d1"));
        assert!(is_known_milestone("active_d365"));
        assert!(!is_known_milestone("active_d"));
        assert!(!is_known_milestone("active_dx"));
        assert!(!is_known_milestone("free text"));
    }

    #[test]
    fn disabled_flag_parses() {
        // The kill switch is env-based; verify the shape without mutating
        // process env (tests share a process).
        assert!(!disabled(), "unset by default in the test harness");
    }
}
