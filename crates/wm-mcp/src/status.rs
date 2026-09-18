//! `wm status` — the human-facing answer to "is WhiteMagic ready?".
//!
//! Deliberately not `wm doctor`: status reports the supported surface in
//! plain language (store, counts, index, last backup, profile, update
//! availability) and stays quiet about optional subsystems. Diagnostics and
//! grading live in `wm doctor` / `wm doctor --deep`.

#![forbid(unsafe_code)]

use serde::Serialize;
use std::path::{Path, PathBuf};
use std::time::Duration;

use wm_memory::MemoryStore;

/// Inspection env-open cap (9.1.6): a live writer or a crashed server's
/// wedged lock file can make LMDB env opens block forever; inspection
/// reports `store_busy` instead of hanging.
const INSPECTION_OPEN_TIMEOUT: Duration = Duration::from_secs(5);

/// Human-facing health summary for a store root.
#[derive(Debug, Clone, Serialize)]
pub struct StatusReport {
    pub version: String,
    pub store_path: String,
    /// `not_initialized` (fresh install — no store yet), `ready`, or
    /// `attention`. A fresh install is a state, not a failure: it must not
    /// read as `needs attention` / `DEGRADED` (review round 2).
    pub state: String,
    pub store_ok: bool,
    pub memories: u64,
    pub sessions: u64,
    pub index_ok: bool,
    /// Live documents read from the Tantivy index (None when unreadable).
    pub index_memories: Option<u64>,
    /// Documents a rebuild would change (healable drift; 0 = index matches
    /// what a rebuild of the store would produce).
    pub index_drift: Option<i64>,
    /// Documents intentionally not indexed by the sanitization gate — a
    /// documented reserve, not drift.
    pub index_skip_reserve: Option<u64>,
    /// Why the index is degraded, or a note when it is healthy with a reserve.
    pub index_detail: Option<String>,
    pub last_backup: Option<String>,
    pub last_backup_age_secs: Option<u64>,
    /// Backup root the nightly runner last chose (card or NVMe staging).
    pub backup_target: Option<String>,
    /// Age of the newest store snapshot found under the target/staging.
    pub backup_newest_age_secs: Option<u64>,
    /// Snapshots are sitting in `nvme-fallback/` awaiting the next fold.
    pub backup_staging_pending: bool,
    /// Store snapshot dirs found directly under `~/whitemagic-backups` — the
    /// history-split signature (one chain must survive on one root).
    pub backup_history_split: bool,
    pub profile: String,
    pub project: Option<String>,
    /// Channel marker written by `scripts/install.sh`
    /// (`<store-root>/install_channel`, content `install_sh[:ref]`). Read even
    /// when the store is not initialized — an arrival record, not store state.
    pub install_channel: Option<String>,
    /// Sanitized install ref from the marker, if any.
    pub install_channel_ref: Option<String>,
    pub update: Option<String>,
}

fn thousands(n: u64) -> String {
    let s = n.to_string();
    let mut out = String::new();
    for (i, ch) in s.chars().enumerate() {
        if i > 0 && (s.len() - i) % 3 == 0 {
            out.push(',');
        }
        out.push(ch);
    }
    out
}

impl StatusReport {
    /// Human-readable lines (no ANSI; the CLI adds presentation).
    #[must_use]
    pub fn lines(&self) -> Vec<String> {
        let initialized = self.state != "not_initialized";
        let ready = initialized && self.store_ok && self.index_ok;
        let mut out = vec![format!(
            "WhiteMagic {}  {}",
            self.version,
            if !initialized {
                "not initialized (fresh install)"
            } else if ready {
                "ready"
            } else {
                "needs attention"
            }
        )];
        out.push(format!("Memory store       {}", self.store_path));
        out.push(format!("Memories           {}", thousands(self.memories)));
        out.push(format!("Sessions           {}", thousands(self.sessions)));
        let index_line = if initialized {
            match (&self.index_detail, self.index_ok) {
                (_, true) => self
                    .index_detail
                    .clone()
                    .unwrap_or_else(|| "healthy".to_string()),
                (Some(detail), false) => format!("DEGRADED — {detail}"),
                (None, false) => "DEGRADED".to_string(),
            }
        } else {
            "not created yet (first run)".to_string()
        };
        out.push(format!("Search index       {index_line}"));
        if let (Some(ts), Some(age)) = (&self.last_backup, self.last_backup_age_secs) {
            out.push(format!("Last backup        {ts} ({} ago)", human_age(age)));
        } else {
            let where_ = self
                .backup_target
                .clone()
                .unwrap_or_else(|| "~/whitemagic-backups".to_string());
            out.push(format!("Last backup        none found ({where_})"));
        }
        if let Some(target) = &self.backup_target {
            out.push(format!("Backup target      {target}"));
        }
        if let Some(age) = self.backup_newest_age_secs {
            if age > 48 * 3600 {
                out.push(format!(
                    "Backup warn        newest snapshot is {} old (>48h) — check the card mount",
                    human_age(age)
                ));
            }
        }
        if self.backup_staging_pending {
            out.push(
                "Backup note        NVMe staging holds snapshots awaiting the next card fold"
                    .to_string(),
            );
        }
        if self.backup_history_split {
            out.push(
                "Backup warn        snapshots found directly under ~/whitemagic-backups — history split"
                    .to_string(),
            );
        }
        out.push(format!("MCP profile        {}", self.profile));
        if let Some(p) = &self.project {
            out.push(format!("Project scope      {p}"));
        }
        if let Some(channel) = &self.install_channel {
            let line = match &self.install_channel_ref {
                Some(reference) => format!("Installed via      {channel} (ref: {reference})"),
                None => format!("Installed via      {channel}"),
            };
            out.push(line);
        }
        if let Some(u) = &self.update {
            out.push(format!("Update             {u}"));
        } else {
            out.push("Update             run 'wm update check'".to_string());
        }
        out
    }
}

fn human_age(secs: u64) -> String {
    if secs < 3600 {
        format!("{}m", secs / 60)
    } else if secs < 86_400 {
        format!("{}h", secs / 3600)
    } else {
        format!("{}d", secs / 86_400)
    }
}

fn backup_log_path() -> PathBuf {
    dirs_home().join("whitemagic-backups").join("backup.log")
}

fn last_backup_from(text: &str) -> (Option<String>, Option<u64>) {
    // Prefer the newest store-backup line (` OK `); fall back to any line.
    let pick = text
        .lines()
        .rev()
        .find(|l| l.contains(" OK "))
        .or_else(|| text.lines().rev().find(|l| !l.trim().is_empty()));
    let Some(line) = pick else {
        return (None, None);
    };
    let ts = line.split_whitespace().next().unwrap_or("").to_string();
    let age = chrono::DateTime::parse_from_rfc3339(&ts).ok().map(|t| {
        let now = chrono::Utc::now();
        (now.timestamp() - t.with_timezone(&chrono::Utc).timestamp()).max(0) as u64
    });
    (Some(ts), age)
}

/// Backup root named by the newest runner line: `TARGET <path> (card ...)` or
/// the loud staging WARN (`staging on NVMe (<path>)`).
fn backup_target_from(text: &str) -> Option<String> {
    for line in text.lines().rev() {
        if let Some(idx) = line.find("TARGET ") {
            let rest = &line[idx + "TARGET ".len()..];
            let target = rest.split_whitespace().next().unwrap_or("");
            if target.starts_with('/') {
                return Some(target.to_string());
            }
        }
        if let Some(idx) = line.find("staging on NVMe (") {
            let rest = &line[idx + "staging on NVMe (".len()..];
            if let Some(end) = rest.find(')') {
                return Some(rest[..end].to_string());
            }
        }
    }
    None
}

/// Snapshot dirs (`whitemagic-backup-*`) one level below `root`, skipping the
/// named subtrees (e.g. `nvme-fallback`, `logs`, `seals`, `anchors`, `trust`).
fn snapshot_dirs(root: &Path, skip: &[&str]) -> Vec<PathBuf> {
    let mut found = Vec::new();
    let Ok(stores) = std::fs::read_dir(root) else {
        return found;
    };
    for store in stores.flatten() {
        let store_path = store.path();
        let name = store.file_name();
        let name = name.to_string_lossy();
        if !store_path.is_dir() || skip.contains(&name.as_ref()) {
            continue;
        }
        if let Ok(whitemagic_backup) = std::fs::read_dir(&store_path) {
            for entry in whitemagic_backup.flatten() {
                let entry_name = entry.file_name();
                if entry_name
                    .to_string_lossy()
                    .starts_with("whitemagic-backup-")
                    && entry.path().is_dir()
                {
                    found.push(entry.path());
                }
            }
        }
    }
    found
}

/// Age in seconds of the newest snapshot dir under `root`.
fn newest_snapshot_age_in(root: &Path, skip: &[&str]) -> Option<u64> {
    snapshot_dirs(root, skip)
        .iter()
        .filter_map(|d| {
            std::fs::metadata(d)
                .ok()
                .and_then(|m| m.modified().ok())
                .map(|t| (d, t))
        })
        .max_by_key(|(_, t)| *t)
        .map(|(_, t)| {
            std::time::SystemTime::now()
                .duration_since(t)
                .map_or(0, |d| d.as_secs())
        })
}

fn dirs_home() -> PathBuf {
    std::env::var_os("HOME").map_or_else(|| PathBuf::from("."), PathBuf::from)
}

/// Read `install.json` (update channel/state) beside the store.
#[must_use]
pub fn read_install_json(store_root: &Path) -> Option<serde_json::Value> {
    let p = store_root.join("install.json");
    let text = std::fs::read_to_string(p).ok()?;
    serde_json::from_str(&text).ok()
}

/// Read the installer's channel marker even when the store is not
/// initialized. A marker is an arrival record, not store state — it must
/// never flip `state` to initialized.
#[must_use]
pub fn read_install_channel(store_root: &Path) -> Option<(String, Option<String>)> {
    let text = std::fs::read_to_string(store_root.join("install_channel")).ok()?;
    wm_tools::expansion::funnel::parse_marker(&text)
}

/// Collect status for the given store root (the directory containing `lmdb/`).
#[must_use]
pub fn collect(store_root: &Path) -> StatusReport {
    let lmdb = store_root.join("lmdb");
    let profile = std::env::var("WM_TOOL_PROFILE").unwrap_or_else(|_| "curated".to_string());
    let project = std::env::var("WM_PROJECT").ok().filter(|s| !s.is_empty());
    let home_backups = dirs_home().join("whitemagic-backups");
    let log_text = std::fs::read_to_string(backup_log_path()).ok();
    let (last_backup, last_backup_age_secs) =
        log_text.as_deref().map_or((None, None), last_backup_from);
    let backup_target = log_text.as_deref().and_then(backup_target_from);
    let staging_root = home_backups.join("nvme-fallback");
    let backup_staging_pending = !snapshot_dirs(&staging_root, &[]).is_empty();
    let backup_history_split = !snapshot_dirs(&home_backups, &["nvme-fallback", "logs"]).is_empty();
    let backup_newest_age_secs = backup_target
        .as_deref()
        .map(Path::new)
        .and_then(|root| newest_snapshot_age_in(root, &[]))
        .or_else(|| newest_snapshot_age_in(&staging_root, &[]));

    let mut memories = 0u64;
    let mut sessions = 0u64;
    let mut store_ok = false;
    // A store exists once LMDB has written its data file. A missing store is
    // the fresh-install state, not degradation (review round 2).
    let initialized = lmdb.join("data.mdb").exists();
    let store = if lmdb.exists() {
        // Inspection never takes the lock file (9.1.6): read-only env opens
        // block forever against a live writer (lmdb-master falls back to a
        // blocking shared-lock wait) and against a crashed server's wedged
        // lock file. `open_inspection` is MDB_NOLOCK|MDB_RDONLY — pure mmap
        // reads, immune to both. Fall back to a bounded writable open only
        // for stores inspection cannot read (pre-cold/incomplete — those are
        // never served, so no lock is held).
        MemoryStore::open_inspection(&lmdb).ok().or_else(|| {
            MemoryStore::open_default_bounded(&lmdb, INSPECTION_OPEN_TIMEOUT)
                .ok()
                .flatten()
        })
    } else {
        None
    };
    if let Some(store) = store.as_ref() {
        store_ok = true;
        for g in wm_core::Galaxy::memory_galaxies() {
            memories += store.count(g).unwrap_or(0) as u64;
        }
        sessions = store.count(wm_core::Galaxy::Sessions).unwrap_or(0) as u64;
    }

    // Index health is MEASURED, not inferred from a directory existing
    // (2026-09-15 audit: a crashed writer left LMDB populated while the index
    // returned zero results, and status still reported `index_ok: true`).
    // The classification separates real drift from the documented
    // sanitization-skip reserve, so a healthy store is not called degraded
    // for content the gate never indexes.
    let index_dir = lmdb.join("tantivy");
    let mut index_ok = false;
    let mut index_memories = None;
    let mut index_drift = None;
    let mut index_skip_reserve = None;
    let mut index_detail = None;
    if index_dir.exists() {
        match wm_memory::search::SearchEngine::open_readonly(&index_dir) {
            Err(e) => {
                index_detail = Some(format!("unopenable: {e}"));
            }
            Ok(engine) => {
                if let Some(store) = store.as_ref() {
                    let class = wm_memory::reindex::classify_drift(store, &engine);
                    index_memories =
                        Some(class.galaxies.iter().map(|g| g.tantivy_count as u64).sum());
                    index_drift = Some(i64::try_from(class.healable_total).unwrap_or(i64::MAX));
                    index_skip_reserve = Some(class.skip_reserve_total as u64);
                    if class.healable_total == 0 {
                        index_ok = true;
                        if class.skip_reserve_total > 0 {
                            index_detail = Some(format!(
                                "healthy ({} docs not indexable by design)",
                                class.skip_reserve_total
                            ));
                        }
                    } else {
                        let named: Vec<String> = class
                            .galaxies
                            .iter()
                            .filter(|g| g.healable_gap != 0)
                            .map(|g| format!("{} ({:+})", g.galaxy, g.healable_gap))
                            .collect();
                        index_detail =
                            Some(format!("drift: {} — run 'wm reindex'", named.join(", ")));
                    }
                } else {
                    index_detail = Some("store unreadable — cannot verify the index".to_string());
                }
            }
        }
    } else {
        index_detail = Some("missing — run 'wm reindex'".to_string());
    }
    let update = read_install_json(store_root).and_then(|v| {
        let latest = v.get("latest_seen").and_then(serde_json::Value::as_str)?;
        let current = env!("CARGO_PKG_VERSION");
        if latest == current {
            // We have checked and are current: say so instead of telling the
            // user to run a check they already ran.
            let checked = v.get("last_check").and_then(serde_json::Value::as_str);
            Some(match checked {
                Some(ts) => format!("{current} (up to date, last checked {ts})"),
                None => format!("{current} (up to date)"),
            })
        } else {
            Some(format!(
                "{latest} available (installed via {})",
                v.get("installed_via")
                    .and_then(serde_json::Value::as_str)
                    .unwrap_or("release-binary")
            ))
        }
    });

    let state = if !initialized {
        "not_initialized"
    } else if store_ok && index_ok {
        "ready"
    } else {
        "attention"
    };

    let (install_channel, install_channel_ref) = read_install_channel(store_root)
        .map_or((None, None), |(channel, reference)| {
            (Some(channel), reference)
        });

    StatusReport {
        version: env!("CARGO_PKG_VERSION").to_string(),
        store_path: store_root.display().to_string(),
        state: state.to_string(),
        store_ok,
        memories,
        sessions,
        index_ok,
        index_memories,
        index_drift,
        index_skip_reserve,
        index_detail,
        last_backup,
        last_backup_age_secs,
        backup_target,
        backup_newest_age_secs,
        backup_staging_pending,
        backup_history_split,
        profile,
        project,
        install_channel,
        install_channel_ref,
        update,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_reports_missing_store_cleanly() {
        let tmp = tempfile::tempdir().unwrap();
        let r = collect(tmp.path());
        assert!(!r.store_ok);
        assert!(!r.index_ok);
        assert_eq!(r.state, "not_initialized");
        assert_eq!(r.memories, 0);
        let lines = r.lines();
        assert!(lines[0].contains("WhiteMagic"), "{lines:?}");
        assert!(
            lines[0].contains("not initialized"),
            "a fresh install is a state, not a failure: {lines:?}"
        );
        assert!(
            lines
                .iter()
                .all(|l| !l.contains("DEGRADED") && !l.contains("needs attention")),
            "a fresh install must not read as degraded: {lines:?}"
        );
        assert!(
            lines
                .iter()
                .any(|l| l.contains("Search index") && l.contains("not created yet")),
            "index line must name the fresh state: {lines:?}"
        );
    }

    #[test]
    fn install_marker_reports_channel_without_initializing() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(
            tmp.path().join("install_channel"),
            "install_sh:HERO!!2026\n",
        )
        .unwrap();
        let report = collect(tmp.path());
        assert_eq!(report.state, "not_initialized", "a marker is not a store");
        assert_eq!(report.install_channel.as_deref(), Some("install_sh"));
        assert_eq!(report.install_channel_ref.as_deref(), Some("hero2026"));
        let text = report.lines().join("\n");
        assert!(
            text.contains("Installed via      install_sh (ref: hero2026)"),
            "{text}"
        );
        assert!(
            !text.contains("needs attention"),
            "a fresh install with a marker is still a fresh install: {text}"
        );
    }

    #[test]
    fn status_reports_up_to_date_when_install_state_agrees() {
        let tmp = tempfile::tempdir().unwrap();
        let state = format!(
            r#"{{"latest_seen":"{}","last_check":"2026-09-14T02:00:00Z","installed_via":"release-binary"}}"#,
            env!("CARGO_PKG_VERSION")
        );
        std::fs::write(tmp.path().join("install.json"), state).unwrap();
        let report = collect(tmp.path());
        let update = report.update.expect("update line");
        assert!(update.contains("up to date"), "{update}");
    }

    #[test]
    fn status_reports_newer_release_when_install_state_lags() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(
            tmp.path().join("install.json"),
            r#"{"latest_seen":"99.0.0","installed_via":"cargo"}"#,
        )
        .unwrap();
        let report = collect(tmp.path());
        let update = report.update.expect("update line");
        assert!(update.contains("99.0.0 available"), "{update}");
        assert!(update.contains("cargo"), "{update}");
    }

    /// 2026-09-15 audit: a store whose index disagrees with canonical memory
    /// must never report `index_ok: true` — the crash scenario that motivated
    /// this check left LMDB populated while search returned zero results.
    #[test]
    fn status_reports_index_drift_as_degraded() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path().join("lmdb")).unwrap();
        let mem = wm_memory::memory::Memory::new(wm_core::Galaxy::Codex, "drift probe".into());
        store.put(wm_core::Galaxy::Codex, &mem).unwrap();

        // Index exists (so the old directory-existence check would say
        // healthy) but does not contain the memory: a rebuild would index it.
        let index_dir = tmp.path().join("lmdb").join("tantivy");
        std::fs::create_dir_all(&index_dir).unwrap();
        let engine = wm_memory::search::SearchEngine::open(&index_dir).unwrap();
        let mut writer = engine.writer().unwrap();
        engine.commit(&mut writer).unwrap();
        drop(writer);
        drop(engine);

        let r = collect(tmp.path());
        assert!(!r.index_ok, "drift must not report healthy: {r:?}");
        assert_eq!(r.index_drift, Some(1));
        assert!(
            r.index_detail.as_deref().unwrap_or("").contains("codex"),
            "drift names the galaxy: {:?}",
            r.index_detail
        );
        assert!(r.lines().iter().any(|l| l.contains("DEGRADED")));
    }

    #[test]
    fn status_reports_consistent_index_as_healthy() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path().join("lmdb")).unwrap();
        let mem = wm_memory::memory::Memory::new(wm_core::Galaxy::Codex, "consistent probe".into());
        store.put(wm_core::Galaxy::Codex, &mem).unwrap();

        let index_dir = tmp.path().join("lmdb").join("tantivy");
        std::fs::create_dir_all(&index_dir).unwrap();
        let engine = wm_memory::search::SearchEngine::open(&index_dir).unwrap();
        let mut writer = engine.writer().unwrap();
        engine.index_memory(&mut writer, &mem).unwrap();
        engine.commit(&mut writer).unwrap();
        drop(writer);
        drop(engine);

        let r = collect(tmp.path());
        assert!(r.index_ok, "consistent index must be healthy: {r:?}");
        assert_eq!(r.index_drift, Some(0));
        assert_eq!(r.index_memories, Some(1));
    }

    #[test]
    fn backup_target_parses_card_and_staging_lines() {
        let card = "2026-09-14T13:32:19-04:00 TARGET /media/lucas/SD_CARD1/whitemagic-backups (card /media/lucas/SD_CARD1 mounted)\n";
        assert_eq!(
            backup_target_from(card).as_deref(),
            Some("/media/lucas/SD_CARD1/whitemagic-backups")
        );
        let staged = "2026-09-14T03:30:00-04:00 WARN backup disk not mounted — staging on NVMe (/home/u/whitemagic-backups/nvme-fallback); folded into the card on the next card-present run.\n";
        assert_eq!(
            backup_target_from(staged).as_deref(),
            Some("/home/u/whitemagic-backups/nvme-fallback")
        );
        assert_eq!(backup_target_from("no target line here"), None);
    }

    #[test]
    fn status_warns_on_stale_split_and_staging() {
        let report = StatusReport {
            version: "test".into(),
            store_path: "/tmp/store".into(),
            state: "ready".into(),
            store_ok: true,
            memories: 0,
            sessions: 0,
            index_ok: true,
            index_memories: Some(0),
            index_drift: Some(0),
            index_skip_reserve: Some(0),
            index_detail: None,
            last_backup: None,
            last_backup_age_secs: None,
            backup_target: Some("/media/lucas/SD_CARD1/whitemagic-backups".into()),
            backup_newest_age_secs: Some(49 * 3600),
            backup_staging_pending: true,
            backup_history_split: true,
            profile: "curated".into(),
            project: None,
            install_channel: None,
            install_channel_ref: None,
            update: None,
        };
        let text = report.lines().join("\n");
        assert!(text.contains("none found (/media/lucas/SD_CARD1/whitemagic-backups)"));
        assert!(text.contains("Backup target"));
        assert!(text.contains("newest snapshot is 2d old (>48h)"), "{text}");
        assert!(text.contains("staging holds snapshots"), "{text}");
        assert!(text.contains("history split"), "{text}");
    }

    #[test]
    fn snapshot_scan_classifies_split_and_staging() {
        let tmp = tempfile::tempdir().unwrap();
        let home = tmp.path();
        std::fs::create_dir_all(home.join("wmv9/whitemagic-backup-20260914T000000Z")).unwrap();
        assert_eq!(
            snapshot_dirs(home, &["nvme-fallback", "logs"]).len(),
            1,
            "a store snapshot directly under home is the split signature"
        );
        assert!(
            snapshot_dirs(home, &["wmv9"]).is_empty(),
            "skip list must exclude named subtrees"
        );
        assert!(snapshot_dirs(&home.join("nvme-fallback"), &[]).is_empty());
        std::fs::create_dir_all(home.join("nvme-fallback/neon/whitemagic-backup-20260914T010000Z"))
            .unwrap();
        assert_eq!(snapshot_dirs(&home.join("nvme-fallback"), &[]).len(), 1);
        let age = newest_snapshot_age_in(home, &["nvme-fallback", "logs"]).unwrap();
        assert!(
            age < 60,
            "a snapshot just created must read as fresh: {age}s"
        );
    }

    #[test]
    fn thousands_formats() {
        assert_eq!(thousands(0), "0");
        assert_eq!(thousands(1482), "1,482");
        assert_eq!(thousands(1_000_000), "1,000,000");
    }
}
