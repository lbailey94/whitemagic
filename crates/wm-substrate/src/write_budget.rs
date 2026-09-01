//! Write-budget telemetry — the system learning its own cost.
//!
//! The irony tax: WhiteMagic gives agents durable continuity while
//! shortening the life of the SSD that holds the store. This module makes
//! the cost *visible*: it tracks how many bytes the store grew per day
//! (LMDB high-water mark + Tantivy index size), keeps a 90-day daily
//! ledger at `<store-root>/write_budget.json`, and answers the operational
//! question "did the store write more than usual today?" — the Harmony
//! Vector's frugality dimension.
//!
//! Measurement model (honest approximations, stated plainly):
//! - LMDB: `data.mdb` file size is a high-water mark — it grows in
//!   increments and never shrinks without compaction, so deltas measure
//!   growth, and free-after-delete space is not credited. This is the
//!   right bias for SSD-wear accounting (over-count writes, never under).
//! - Tantivy: directory size on disk, walked at most once per 5 minutes
//!   and cached between walks (a segment-merging index changes size in
//!   steps; per-request walks would cost more I/O than they measure).
//! - Backups and dream-cycle compactions are attributed to the day they
//!   grew the files, same as any write.

#![forbid(unsafe_code)]

use chrono::{DateTime, Duration, NaiveDate, Utc};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

/// Daily ledger retention — 90 days is enough for "30-day average" plus
/// seasonal drift, small enough that the file stays a few KB.
const RETENTION_DAYS: i64 = 90;
/// Minimum interval between Tantivy directory walks (expensive I/O).
const TANTIVY_WALK_INTERVAL_SECS: i64 = 300;
/// How many days of history feed the reported average.
const AVERAGE_WINDOW_DAYS: i64 = 30;

/// Per-day write totals attributed to one UTC date.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct DayWrites {
    /// Attributed bytes for this day (positive growth only).
    pub bytes: u64,
    /// How many observation samples contributed (diagnostics).
    pub samples: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct LastSample {
    ts: String,
    lmdb_bytes: u64,
    tantivy_bytes: u64,
}

#[derive(Debug, Default, Serialize, Deserialize)]
struct WriteBudgetState {
    version: u8,
    /// UTC date (YYYY-MM-DD) → totals.
    days: BTreeMap<String, DayWrites>,
    last_sample: Option<LastSample>,
    /// First day the ledger recorded — lifetime context for the report.
    tracking_since: Option<String>,
}

impl WriteBudgetState {
    const fn new() -> Self {
        Self {
            version: 1,
            days: BTreeMap::new(),
            last_sample: None,
            tracking_since: None,
        }
    }
}

/// One observation's outcome: how many bytes were attributed, and to when.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct WriteBudgetDelta {
    /// Bytes attributed to `date` by this observation.
    pub attributed_bytes: u64,
    /// UTC date the bytes were attributed to.
    pub date: NaiveDate,
}

/// The operational summary `wm doctor` and `/status` render.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WriteBudgetReport {
    /// Bytes attributed today (UTC) so far.
    pub today_bytes: u64,
    /// Bytes attributed yesterday, for "more than usual?" comparison.
    pub yesterday_bytes: Option<u64>,
    /// Mean daily bytes over the available history (≤ 30 days).
    pub avg_30d_bytes: u64,
    /// Days of history currently in the ledger.
    pub days_tracked: u32,
    /// Busiest day in the ledger: (date, bytes).
    pub busiest_day: Option<(String, u64)>,
    /// Current LMDB high-water size (bytes).
    pub lmdb_bytes: u64,
    /// Current Tantivy index size (bytes).
    pub tantivy_bytes: u64,
}

/// Daily write-budget ledger for one store.
///
/// Thread-safe through the caller (`McpServer` holds it in a `Mutex`);
/// persistence is an atomic tmp+rename of a small JSON file.
#[derive(Debug)]
pub struct WriteBudgetLedger {
    path: PathBuf,
    lmdb_data_mdb: PathBuf,
    tantivy_dir: PathBuf,
    state: WriteBudgetState,
    last_tantivy_walk: Option<DateTime<Utc>>,
    cached_tantivy_bytes: u64,
}

impl WriteBudgetLedger {
    /// Ledger path convention: `<store-root>/write_budget.json` (read by
    /// `wm doctor`), with the LMDB env and Tantivy index as siblings of
    /// the store root's `lmdb/` directory.
    #[must_use]
    pub fn paths(store_root: &Path) -> (PathBuf, PathBuf, PathBuf) {
        (
            store_root.join("write_budget.json"),
            store_root.join("lmdb").join("data.mdb"),
            store_root.join("lmdb").join("tantivy"),
        )
    }

    /// Open (or initialize) the ledger for a store root.
    #[must_use]
    pub fn load(store_root: &Path) -> Self {
        let (path, lmdb_data_mdb, tantivy_dir) = Self::paths(store_root);
        let state = std::fs::read_to_string(&path)
            .ok()
            .and_then(|raw| {
                let parsed = serde_json::from_str::<WriteBudgetState>(&raw).ok()?;
                Some(parsed)
            })
            .unwrap_or_else(|| {
                if path.exists() {
                    // A corrupt ledger must never wedge the server: start
                    // fresh (advisory telemetry; the next write rebuilds).
                    tracing::warn!(
                        path = %path.display(),
                        "write_budget.json unreadable — starting a fresh ledger"
                    );
                }
                WriteBudgetState::new()
            });
        Self {
            path,
            lmdb_data_mdb,
            tantivy_dir,
            state,
            last_tantivy_walk: None,
            cached_tantivy_bytes: 0,
        }
    }

    /// Observe current sizes, attribute positive growth to today (UTC),
    /// prune history beyond retention, and persist. Cheap when called
    /// more often than the Tantivy walk interval — only a `stat` runs.
    pub fn observe(&mut self, now: DateTime<Utc>) -> WriteBudgetDelta {
        let lmdb_bytes = std::fs::metadata(&self.lmdb_data_mdb).map_or(0, |m| m.len());
        let walk_due = self
            .last_tantivy_walk
            .is_none_or(|last| (now - last).num_seconds() >= TANTIVY_WALK_INTERVAL_SECS);
        if walk_due {
            self.cached_tantivy_bytes = dir_size(&self.tantivy_dir);
            self.last_tantivy_walk = Some(now);
        }
        let total_bytes = lmdb_bytes.saturating_add(self.cached_tantivy_bytes);

        let (attributed, date) = match &self.state.last_sample {
            Some(last) => {
                let growth =
                    total_bytes.saturating_sub(last.lmdb_bytes.saturating_add(last.tantivy_bytes));
                (growth, now.date_naive())
            }
            None => (0, now.date_naive()),
        };

        self.state.last_sample = Some(LastSample {
            ts: now.to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
            lmdb_bytes,
            tantivy_bytes: self.cached_tantivy_bytes,
        });

        let day_key = date.to_string();
        if attributed > 0 {
            let entry = self.state.days.entry(day_key.clone()).or_default();
            entry.bytes = entry.bytes.saturating_add(attributed);
            entry.samples = entry.samples.saturating_add(1);
        }
        if self.state.tracking_since.is_none() {
            self.state.tracking_since = Some(day_key);
        }
        self.prune(now.date_naive());
        self.persist();
        WriteBudgetDelta {
            attributed_bytes: attributed,
            date,
        }
    }

    /// Drop days older than the retention window.
    fn prune(&mut self, today: NaiveDate) {
        let Some(cutoff) = today.checked_sub_signed(Duration::days(RETENTION_DAYS)) else {
            return;
        };
        self.state.days.retain(|day, _| {
            NaiveDate::parse_from_str(day, "%Y-%m-%d").is_ok_and(|d| d >= cutoff) // unparseable keys are kept for inspection
        });
    }

    /// Persist atomically; failures are warn-only (advisory telemetry must
    /// never take a server down).
    fn persist(&self) {
        match serde_json::to_string_pretty(&self.state) {
            Ok(body) => {
                let tmp = self
                    .path
                    .with_file_name(format!("write_budget.json.tmp.{}", std::process::id()));
                if let Err(e) =
                    std::fs::write(&tmp, body).and_then(|()| std::fs::rename(&tmp, &self.path))
                {
                    tracing::warn!(
                        path = %self.path.display(),
                        error = %e,
                        "failed to persist write budget ledger"
                    );
                }
            }
            Err(e) => tracing::warn!(error = %e, "write budget serialization failed"),
        }
    }

    /// Refresh the size sample WITHOUT persisting — the read-only surface
    /// for `wm doctor` and `/status` (a status probe must not write).
    pub fn fresh_report(&mut self) -> WriteBudgetReport {
        let lmdb_bytes = std::fs::metadata(&self.lmdb_data_mdb).map_or(0, |m| m.len());
        let walk_due = self
            .last_tantivy_walk
            .is_none_or(|last| (Utc::now() - last).num_seconds() >= TANTIVY_WALK_INTERVAL_SECS);
        if walk_due {
            self.cached_tantivy_bytes = dir_size(&self.tantivy_dir);
            self.last_tantivy_walk = Some(Utc::now());
        }
        self.state.last_sample = Some(LastSample {
            ts: Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
            lmdb_bytes,
            tantivy_bytes: self.cached_tantivy_bytes,
        });
        self.report()
    }

    /// Operational summary for `wm doctor` and `/status` (as of now).
    #[must_use]
    pub fn report(&self) -> WriteBudgetReport {
        self.report_as_of(Utc::now())
    }

    /// Operational summary relative to an explicit instant (tests, replay).
    #[must_use]
    pub fn report_as_of(&self, now: DateTime<Utc>) -> WriteBudgetReport {
        let today = now.date_naive();
        let today_key = today.to_string();
        let yesterday_key = (today - Duration::days(1)).to_string();
        let today_bytes = self.state.days.get(&today_key).map_or(0, |d| d.bytes);
        let yesterday_bytes = self.state.days.get(&yesterday_key).map(|d| d.bytes);

        // Average over the trailing 30-day window (not the ledger's whole
        // retention): recent behavior is the comparison that matters.
        let mut sum = 0u64;
        let mut counted = 0u32;
        for offset in 0..AVERAGE_WINDOW_DAYS {
            let key = (today - Duration::days(offset)).to_string();
            if let Some(day) = self.state.days.get(&key) {
                sum = sum.saturating_add(day.bytes);
                counted += 1;
            }
        }
        let avg = if counted > 0 {
            sum / u64::from(counted)
        } else {
            0
        };

        let busiest_day = self
            .state
            .days
            .iter()
            .max_by_key(|(_, d)| d.bytes)
            .map(|(day, d)| (day.clone(), d.bytes))
            .filter(|(_, bytes)| *bytes > 0);

        let (lmdb_bytes, tantivy_bytes) = match &self.state.last_sample {
            Some(last) => (last.lmdb_bytes, last.tantivy_bytes),
            None => (0, 0),
        };

        WriteBudgetReport {
            today_bytes,
            yesterday_bytes,
            avg_30d_bytes: avg,
            days_tracked: u32::try_from(self.state.days.len()).unwrap_or(u32::MAX),
            busiest_day,
            lmdb_bytes,
            tantivy_bytes,
        }
    }

    /// JSON rendering for `/status`.
    #[must_use]
    pub fn report_json(&self) -> serde_json::Value {
        let r = self.report();
        json!({
            "today_bytes": r.today_bytes,
            "yesterday_bytes": r.yesterday_bytes,
            "avg_30d_bytes": r.avg_30d_bytes,
            "days_tracked": r.days_tracked,
            "busiest_day": r.busiest_day,
            "lmdb_bytes": r.lmdb_bytes,
            "tantivy_bytes": r.tantivy_bytes,
        })
    }

    /// Current ledger size on disk (diagnostics).
    #[must_use]
    pub fn ledger_path(&self) -> &Path {
        &self.path
    }

    /// Year-of-era helper used by tests to build dates portably.
    #[cfg(test)]
    const fn base_date() -> NaiveDate {
        NaiveDate::from_ymd_opt(2026, 8, 28).expect("valid date")
    }
}

/// Recursive directory size (bytes). Bounded by what exists; missing dirs
/// count as zero.
fn dir_size(path: &Path) -> u64 {
    let mut total = 0u64;
    let Ok(entries) = std::fs::read_dir(path) else {
        return 0;
    };
    for entry in entries.flatten() {
        let Ok(meta) = entry.metadata() else {
            continue;
        };
        if meta.is_dir() {
            total = total.saturating_add(dir_size(&entry.path()));
        } else {
            total = total.saturating_add(meta.len());
        }
    }
    total
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{Datelike, TimeZone};

    fn at(day: NaiveDate, hour: u32) -> DateTime<Utc> {
        Utc.with_ymd_and_hms(day.year(), day.month(), day.day(), hour, 0, 0)
            .single()
            .expect("valid test time")
    }

    /// Store root with a data.mdb and a tantivy dir whose sizes the test
    /// controls directly.
    fn fake_store() -> (tempfile::TempDir, PathBuf) {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path().to_path_buf();
        std::fs::create_dir_all(root.join("lmdb/tantivy")).unwrap();
        (dir, root)
    }

    fn write_sizes(root: &Path, lmdb: u64, tantivy: u64) {
        let mdb = root.join("lmdb/data.mdb");
        if mdb.exists() {
            std::fs::remove_file(&mdb).unwrap();
        }
        std::fs::write(&mdb, vec![0u8; lmdb as usize]).unwrap();
        let seg = root.join("lmdb/tantivy/seg.0");
        if seg.exists() {
            std::fs::remove_file(&seg).unwrap();
        }
        std::fs::write(&seg, vec![0u8; tantivy as usize]).unwrap();
    }

    #[test]
    fn first_observation_baselines_without_attributing() {
        let (_dir, root) = fake_store();
        write_sizes(&root, 1_000, 500);
        let mut ledger = WriteBudgetLedger::load(&root);
        let delta = ledger.observe(at(WriteBudgetLedger::base_date(), 10));
        assert_eq!(delta.attributed_bytes, 0, "first sample is a baseline");
        assert_eq!(ledger.report().lmdb_bytes, 1_000);
        assert_eq!(ledger.report().tantivy_bytes, 500);
    }

    #[test]
    fn growth_attributed_to_current_day() {
        let (_dir, root) = fake_store();
        write_sizes(&root, 1_000, 500);
        let mut ledger = WriteBudgetLedger::load(&root);
        ledger.observe(at(WriteBudgetLedger::base_date(), 10));

        write_sizes(&root, 1_000 + 4_200, 500 + 100);
        let delta = ledger.observe(at(WriteBudgetLedger::base_date(), 11));
        assert_eq!(delta.attributed_bytes, 4_300);
        // Day-sensitive assertions pin the clock — report() is wall-clock
        // based, and a UTC rollover mid-suite must not flip these.
        let report = ledger.report_as_of(at(WriteBudgetLedger::base_date(), 11));
        assert_eq!(report.today_bytes, 4_300);
        assert_eq!(report.yesterday_bytes, None);
        assert_eq!(report.busiest_day, Some(("2026-08-28".into(), 4_300)));
    }

    #[test]
    fn shrink_attributed_as_zero_not_negative() {
        let (_dir, root) = fake_store();
        write_sizes(&root, 10_000, 0);
        let mut ledger = WriteBudgetLedger::load(&root);
        ledger.observe(at(WriteBudgetLedger::base_date(), 10));
        write_sizes(&root, 500, 0); // compaction shrank the store
        let delta = ledger.observe(at(WriteBudgetLedger::base_date(), 11));
        assert_eq!(delta.attributed_bytes, 0, "never credit deletes as writes");
        assert_eq!(
            ledger
                .report_as_of(at(WriteBudgetLedger::base_date(), 11))
                .today_bytes,
            0
        );
    }

    #[test]
    fn utc_midnight_rollover_starts_new_day() {
        let (_dir, root) = fake_store();
        write_sizes(&root, 1_000, 0);
        let mut ledger = WriteBudgetLedger::load(&root);
        ledger.observe(at(WriteBudgetLedger::base_date(), 10));

        // Give the first day real attributed growth.
        write_sizes(&root, 3_000, 0);
        ledger.observe(at(WriteBudgetLedger::base_date(), 22));

        write_sizes(&root, 4_000, 0);
        let next = WriteBudgetLedger::base_date().succ_opt().unwrap();
        ledger.observe(at(next, 1));
        let report = ledger.report_as_of(at(next, 1));
        assert_eq!(report.today_bytes, 1_000);
        assert_eq!(report.yesterday_bytes, Some(2_000));
    }

    #[test]
    fn tantivy_walk_throttled_within_interval() {
        let (_dir, root) = fake_store();
        write_sizes(&root, 1_000, 100);
        let mut ledger = WriteBudgetLedger::load(&root);
        ledger.observe(at(WriteBudgetLedger::base_date(), 10));

        // Grow tantivy and observe 1s later — inside the 5-min walk window,
        // so the cached size (100) is used and only the baseline shift shows.
        write_sizes(&root, 1_000, 9_999);
        let delta = ledger.observe(at(WriteBudgetLedger::base_date(), 10) + Duration::seconds(1));
        assert_eq!(
            delta.attributed_bytes, 0,
            "stale tantivy cache must not over-attribute"
        );

        // After the walk window the new size is observed.
        let delta = ledger.observe(at(WriteBudgetLedger::base_date(), 10) + Duration::seconds(301));
        assert_eq!(delta.attributed_bytes, 9_899);
    }

    #[test]
    fn ledger_roundtrips_and_recovers_from_corruption() {
        let (_dir, root) = fake_store();
        write_sizes(&root, 1_000, 0);
        let mut ledger = WriteBudgetLedger::load(&root);
        ledger.observe(at(WriteBudgetLedger::base_date(), 10));
        write_sizes(&root, 5_000, 0);
        ledger.observe(at(WriteBudgetLedger::base_date(), 12));

        // Roundtrip: a fresh load sees the recorded history (clock pinned).
        let reloaded = WriteBudgetLedger::load(&root);
        assert_eq!(
            reloaded
                .report_as_of(at(WriteBudgetLedger::base_date(), 12))
                .today_bytes,
            4_000
        );

        // Corruption: a fresh load starts clean instead of panicking.
        std::fs::write(root.join("write_budget.json"), "{not json").unwrap();
        let corrupted = WriteBudgetLedger::load(&root);
        assert_eq!(corrupted.report().days_tracked, 0);
    }

    #[test]
    fn retention_prunes_old_days() {
        let (_dir, root) = fake_store();
        write_sizes(&root, 1_000, 0);
        let mut ledger = WriteBudgetLedger::load(&root);
        ledger.observe(at(WriteBudgetLedger::base_date(), 10));

        // Hand-write an ancient day and a real recent day into the ledger.
        let ancient = (WriteBudgetLedger::base_date() - Duration::days(120)).to_string();
        ledger.state.days.insert(
            ancient.clone(),
            DayWrites {
                bytes: 7,
                samples: 1,
            },
        );
        ledger.state.days.insert(
            "2026-08-28".into(),
            DayWrites {
                bytes: 5,
                samples: 1,
            },
        );
        ledger.prune(WriteBudgetLedger::base_date());
        assert!(!ledger.state.days.contains_key(&ancient), "old days prune");
        assert!(
            ledger.state.days.contains_key("2026-08-28"),
            "recent days survive"
        );
    }
}
