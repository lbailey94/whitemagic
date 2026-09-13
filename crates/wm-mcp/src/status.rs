//! `wm status` — the human-facing answer to "is WhiteMagic ready?".
//!
//! Deliberately not `wm doctor`: status reports the supported surface in
//! plain language (store, counts, index, last backup, profile, update
//! availability) and stays quiet about optional subsystems. Diagnostics and
//! grading live in `wm doctor` / `wm doctor --deep`.

#![forbid(unsafe_code)]

use serde::Serialize;
use std::path::{Path, PathBuf};

use wm_memory::MemoryStore;

/// Status report (stable shape; `--json` for agents).
#[derive(Debug, Clone, Serialize)]
pub struct StatusReport {
    pub version: String,
    pub store_path: String,
    pub store_ok: bool,
    pub memories: u64,
    pub sessions: u64,
    pub index_ok: bool,
    pub last_backup: Option<String>,
    pub last_backup_age_secs: Option<u64>,
    pub profile: String,
    pub project: Option<String>,
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
        let ready = self.store_ok && self.index_ok;
        let mut out = vec![format!(
            "WhiteMagic {}  {}",
            self.version,
            if ready { "ready" } else { "needs attention" }
        )];
        out.push(format!("Memory store       {}", self.store_path));
        out.push(format!("Memories           {}", thousands(self.memories)));
        out.push(format!("Sessions           {}", thousands(self.sessions)));
        out.push(format!(
            "Search index       {}",
            if self.index_ok { "healthy" } else { "missing" }
        ));
        match (&self.last_backup, self.last_backup_age_secs) {
            (Some(ts), Some(age)) => {
                out.push(format!("Last backup        {ts} ({} ago)", human_age(age)));
            }
            _ => {
                out.push("Last backup        none found (~/whitemagic-backups)".to_string());
            }
        }
        out.push(format!("MCP profile        {}", self.profile));
        if let Some(p) = &self.project {
            out.push(format!("Project scope      {p}"));
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

fn last_backup() -> (Option<String>, Option<u64>) {
    let log: PathBuf = dirs_home().join("whitemagic-backups").join("backup.log");
    let Ok(text) = std::fs::read_to_string(&log) else {
        return (None, None);
    };
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

/// Collect status for the given store root (the directory containing `lmdb/`).
#[must_use]
pub fn collect(store_root: &Path) -> StatusReport {
    let lmdb = store_root.join("lmdb");
    let profile = std::env::var("WM_TOOL_PROFILE").unwrap_or_else(|_| "curated".to_string());
    let project = std::env::var("WM_PROJECT").ok().filter(|s| !s.is_empty());
    let index_ok = lmdb.join("tantivy").exists();
    let (last_backup, last_backup_age_secs) = last_backup();

    let mut memories = 0u64;
    let mut sessions = 0u64;
    let mut store_ok = false;
    if lmdb.exists() {
        if let Ok(store) = MemoryStore::open_default(&lmdb) {
            store_ok = true;
            for g in wm_core::Galaxy::memory_galaxies() {
                memories += store.count(g).unwrap_or(0) as u64;
            }
            sessions = store.count(wm_core::Galaxy::Sessions).unwrap_or(0) as u64;
        }
    }

    let update = read_install_json(store_root).and_then(|v| {
        let latest = v.get("latest_seen").and_then(serde_json::Value::as_str)?;
        if latest == env!("CARGO_PKG_VERSION") {
            None
        } else {
            Some(format!(
                "{latest} available (installed via {})",
                v.get("installed_via")
                    .and_then(serde_json::Value::as_str)
                    .unwrap_or("release-binary")
            ))
        }
    });

    StatusReport {
        version: env!("CARGO_PKG_VERSION").to_string(),
        store_path: store_root.display().to_string(),
        store_ok,
        memories,
        sessions,
        index_ok,
        last_backup,
        last_backup_age_secs,
        profile,
        project,
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
        assert_eq!(r.memories, 0);
        let lines = r.lines();
        assert!(lines[0].contains("WhiteMagic"));
        assert!(lines.iter().any(|l| l.contains("Search index")));
    }

    #[test]
    fn thousands_formats() {
        assert_eq!(thousands(0), "0");
        assert_eq!(thousands(1482), "1,482");
        assert_eq!(thousands(1_000_000), "1,000,000");
    }
}
