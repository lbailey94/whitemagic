//! Cross-process tool-usage statistics for `wm stats` (P1, 2026-09-15).
//!
//! `mutable_tool_stats.json` is written by a running server at checkpoint and
//! shutdown; a fresh inspection process has zero in-memory counters. `wm stats`
//! used to build an inspection server and print ITS counters, which read as
//! "no usage" on every invocation (P0 audit: "cross-process `wm stats`" absent).
//! This module reads the persisted snapshots instead and estimates weekly
//! activity from the daily rollups the server appends.

use std::collections::BTreeMap;
use std::path::Path;

use serde::{Deserialize, Serialize};
use wm_core::ToolStatsSnapshot;

/// One tool's usage row, derived from a persisted snapshot.
#[derive(Debug, Clone, PartialEq)]
pub struct ToolUsageRow {
    pub name: String,
    pub calls: u64,
    pub successes: u64,
    pub failures: u64,
    pub avg_ms: f64,
    pub peak_ms: f64,
    pub last_used_unix: u64,
    pub effectiveness: f32,
}

/// A daily cumulative rollup (tools → snapshot at that day's checkpoint).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DailyRollup {
    pub date: String,
    pub tools: BTreeMap<String, ToolStatsSnapshot>,
}

fn row_from(name: &str, snap: &ToolStatsSnapshot) -> ToolUsageRow {
    ToolUsageRow {
        name: name.to_string(),
        calls: snap.call_count,
        successes: snap.success_count,
        failures: snap.call_count.saturating_sub(snap.success_count),
        avg_ms: snap.p50_latency_ns as f64 / 1_000_000.0,
        peak_ms: snap.peak_latency_ns as f64 / 1_000_000.0,
        last_used_unix: snap.last_used_unix,
        effectiveness: snap.effectiveness,
    }
}

/// Read persisted per-tool snapshots from `<lmdb>/mutable_tool_stats.json`.
///
/// Returns rows sorted by call count (descending), then name. Missing file →
/// empty; unparsable file → an explicit error so `wm stats` can say the
/// snapshot is corrupt instead of pretending there is no usage.
pub fn load_tool_stats_checked(lmdb_dir: &Path) -> std::result::Result<Vec<ToolUsageRow>, String> {
    let path = lmdb_dir.join("mutable_tool_stats.json");
    let Ok(text) = std::fs::read_to_string(&path) else {
        return Ok(Vec::new());
    };
    let snapshots: BTreeMap<String, ToolStatsSnapshot> = serde_json::from_str(&text)
        .map_err(|e| format!("{} is unreadable: {e}", path.display()))?;
    Ok(rows_from(&snapshots))
}

/// Convenience wrapper that treats an unreadable snapshot as empty (tests and
/// callers that only need best-effort rows).
#[must_use]
pub fn load_tool_stats(lmdb_dir: &Path) -> Vec<ToolUsageRow> {
    load_tool_stats_checked(lmdb_dir).unwrap_or_default()
}

fn rows_from(snapshots: &BTreeMap<String, ToolStatsSnapshot>) -> Vec<ToolUsageRow> {
    let mut rows: Vec<ToolUsageRow> = snapshots
        .iter()
        .filter(|(_, snap)| snap.call_count > 0)
        .map(|(name, snap)| row_from(name, snap))
        .collect();
    rows.sort_by(|a, b| b.calls.cmp(&a.calls).then_with(|| a.name.cmp(&b.name)));
    rows
}

/// Read the daily rollup history (`<lmdb>/stats_history.jsonl`).
#[must_use]
pub fn load_history(lmdb_dir: &Path) -> Vec<DailyRollup> {
    let path = lmdb_dir.join("stats_history.jsonl");
    let Ok(text) = std::fs::read_to_string(&path) else {
        return Vec::new();
    };
    text.lines()
        .filter(|line| !line.trim().is_empty())
        .filter_map(|line| serde_json::from_str::<DailyRollup>(line).ok())
        .collect()
}

/// Append a daily rollup, at most once per date (idempotent per day).
///
/// Returns true when a row was written. The file lives beside the tool stats
/// so `wm stats --week` can work without a running server.
pub fn append_daily_rollup(
    lmdb_dir: &Path,
    date: &str,
    tools: &BTreeMap<String, ToolStatsSnapshot>,
) -> std::io::Result<bool> {
    let history = load_history(lmdb_dir);
    if history.iter().any(|row| row.date == date) {
        return Ok(false);
    }
    let path = lmdb_dir.join("stats_history.jsonl");
    let rollup = DailyRollup {
        date: date.to_string(),
        tools: tools.clone(),
    };
    let mut line = serde_json::to_string(&rollup).map_err(std::io::Error::other)?;
    line.push('\n');
    use std::io::Write as _;
    let mut file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)?;
    file.write_all(line.as_bytes())?;
    Ok(true)
}

/// Estimate per-tool activity over the last `days` daily rollups.
///
/// Cumulative counters restart with each server process, so a rollup whose
/// counter is lower than the previous rollup's is treated as a restart: the
/// row's value contributes from zero. The estimate is disclosed as an
/// estimate — it is derived, never recorded per call.
#[must_use]
pub fn weekly_deltas(history: &[DailyRollup], days: usize) -> Vec<ToolUsageRow> {
    let window = &history[history.len().saturating_sub(days)..];
    let mut totals: BTreeMap<String, ToolUsageRow> = BTreeMap::new();
    let mut previous: Option<&DailyRollup> = None;
    for rollup in window {
        for (name, snap) in &rollup.tools {
            let delta_calls = match previous.and_then(|p| p.tools.get(name)) {
                Some(prev) if snap.call_count >= prev.call_count => {
                    snap.call_count - prev.call_count
                }
                // First sighting or a restart: the whole current value is
                // this window's activity.
                _ => snap.call_count,
            };
            if delta_calls == 0 {
                continue;
            }
            let entry = totals.entry(name.clone()).or_insert_with(|| ToolUsageRow {
                name: name.clone(),
                calls: 0,
                successes: 0,
                failures: 0,
                avg_ms: 0.0,
                peak_ms: 0.0,
                last_used_unix: 0,
                effectiveness: 0.0,
            });
            let delta_successes = match previous.and_then(|p| p.tools.get(name)) {
                Some(prev) if snap.success_count >= prev.success_count => {
                    snap.success_count - prev.success_count
                }
                _ => snap.success_count,
            };
            entry.calls += delta_calls;
            entry.successes += delta_successes;
            entry.failures = entry.calls.saturating_sub(entry.successes);
            entry.avg_ms = snap.p50_latency_ns as f64 / 1_000_000.0;
            entry.peak_ms = entry.peak_ms.max(snap.peak_latency_ns as f64 / 1_000_000.0);
            entry.last_used_unix = entry.last_used_unix.max(snap.last_used_unix);
            entry.effectiveness = snap.effectiveness;
        }
        previous = Some(rollup);
    }
    let mut rows: Vec<ToolUsageRow> = totals.into_values().collect();
    rows.sort_by(|a, b| b.calls.cmp(&a.calls).then_with(|| a.name.cmp(&b.name)));
    rows
}

#[cfg(test)]
mod tests {
    use super::*;

    fn snap(calls: u64, successes: u64, last: u64) -> ToolStatsSnapshot {
        ToolStatsSnapshot {
            call_count: calls,
            success_count: successes,
            p50_latency_ns: 2_000_000,
            peak_latency_ns: 9_000_000,
            last_used_unix: last,
            effectiveness: 0.9,
            ..Default::default()
        }
    }

    #[test]
    fn loads_and_sorts_persisted_stats() {
        let tmp = tempfile::tempdir().unwrap();
        let mut map = BTreeMap::new();
        map.insert("memory.create".to_string(), snap(12, 11, 100));
        map.insert("session.continuity".to_string(), snap(40, 40, 200));
        map.insert("never.called".to_string(), snap(0, 0, 0));
        std::fs::write(
            tmp.path().join("mutable_tool_stats.json"),
            serde_json::to_string(&map).unwrap(),
        )
        .unwrap();

        let rows = load_tool_stats(tmp.path());
        assert_eq!(rows.len(), 2, "zero-call tools are not shown");
        assert_eq!(rows[0].name, "session.continuity");
        assert_eq!(rows[0].calls, 40);
        assert_eq!(rows[1].name, "memory.create");
        assert_eq!(rows[1].failures, 1);
        assert!((rows[1].avg_ms - 2.0).abs() < f64::EPSILON);
    }

    #[test]
    fn missing_stats_file_is_empty_not_an_error() {
        let tmp = tempfile::tempdir().unwrap();
        assert!(load_tool_stats(tmp.path()).is_empty());
    }

    #[test]
    fn daily_rollup_appends_once_per_date() {
        let tmp = tempfile::tempdir().unwrap();
        let mut map = BTreeMap::new();
        map.insert("memory.create".to_string(), snap(3, 3, 1));
        assert!(append_daily_rollup(tmp.path(), "2026-09-14", &map).unwrap());
        assert!(!append_daily_rollup(tmp.path(), "2026-09-14", &map).unwrap());
        assert!(append_daily_rollup(tmp.path(), "2026-09-15", &map).unwrap());
        assert_eq!(load_history(tmp.path()).len(), 2);
    }

    #[test]
    fn weekly_deltas_sum_within_a_process_and_reset_across_restarts() {
        let mut day1 = BTreeMap::new();
        day1.insert("memory.search".to_string(), snap(10, 10, 1));
        let mut day2 = BTreeMap::new();
        day2.insert("memory.search".to_string(), snap(17, 16, 2));
        // Restart: the counter drops back to 4 (new process).
        let mut day3 = BTreeMap::new();
        day3.insert("memory.search".to_string(), snap(4, 4, 3));
        let history = vec![
            DailyRollup {
                date: "2026-09-13".into(),
                tools: day1,
            },
            DailyRollup {
                date: "2026-09-14".into(),
                tools: day2,
            },
            DailyRollup {
                date: "2026-09-15".into(),
                tools: day3,
            },
        ];
        let rows = weekly_deltas(&history, 7);
        assert_eq!(rows.len(), 1);
        // 10 (first sighting) + 7 (growth) + 4 (post-restart activity).
        assert_eq!(rows[0].calls, 21);
        assert_eq!(rows[0].failures, 1);
    }

    #[test]
    fn weekly_deltas_window_limits_days() {
        let mut map = BTreeMap::new();
        map.insert("t".to_string(), snap(5, 5, 1));
        let mut map2 = BTreeMap::new();
        map2.insert("t".to_string(), snap(9, 9, 2));
        let history = vec![
            DailyRollup {
                date: "2026-09-13".into(),
                tools: map,
            },
            DailyRollup {
                date: "2026-09-14".into(),
                tools: map2,
            },
        ];
        let rows = weekly_deltas(&history, 1);
        assert_eq!(rows[0].calls, 9, "one-day window sees only the last rollup");
    }
}
