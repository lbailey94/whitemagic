//! Token / savings ledger aggregation for `wm ledger`.
//!
//! Local-only: reads `<store>/lmdb/savings_ledger.jsonl` (written by
//! `session.record` / `session.continuity`) and
//! `<store>/lmdb/mutable_tool_stats.json` (dispatch counters). Nothing here
//! transmits; metric definitions and the attribution rules live in
//! `docs/TOKEN_LEDGER.md`.
//!
//! Attribution rule (2026-09-21, token-ledger v0): provider/harness prompt
//! caching is *context*, not a WhiteMagic saving. This report therefore keeps
//! them separate:
//!
//! - `state_to_context_ratio` — stored bytes vs bytes injected by WM's
//!   bounded envelopes (the WM-attributable compression).
//! - `token_equivalent_saved_estimate` — `(bytes_available - bytes_injected) / 4`
//!   with the divisor disclosed; an estimate, never a billing claim.
//! - `local_ops` — WM dispatch calls (100% local compute), by family.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use anyhow::Result;
use serde_json::{Value, json};

const LEDGER_FILE: &str = "savings_ledger.jsonl";
const TOOL_STATS_FILE: &str = "mutable_tool_stats.json";
const CALIBRATION_FILE: &str = "savings_calibration.json";
/// Default estimate divisor (bytes per token) when a store has no local
/// calibration. Disclosed in every output; calibrate with
/// `wm ledger --calibrate <bytes_per_token>`.
pub const DEFAULT_BYTES_PER_TOKEN: f64 = 4.0;

fn lmdb_path(store_root: &Path) -> PathBuf {
    store_root.join("lmdb")
}

/// Read the per-store calibration divisor (validated 1.0–16.0; default 4.0).
#[must_use]
pub fn bytes_per_token(store_root: &Path) -> f64 {
    std::fs::read_to_string(lmdb_path(store_root).join(CALIBRATION_FILE))
        .ok()
        .and_then(|text| serde_json::from_str::<Value>(&text).ok())
        .and_then(|v| v.get("bytes_per_token").and_then(Value::as_f64))
        .filter(|v| (1.0..=16.0).contains(v))
        .unwrap_or(DEFAULT_BYTES_PER_TOKEN)
}

/// Write the per-store calibration divisor.
///
/// The divisor is a local estimate setting, not a claim: encode a
/// representative sample with the tokenizer of your choice, divide bytes by
/// tokens, and set the result here.
pub fn set_calibration(store_root: &Path, divisor: f64) -> Result<()> {
    if !(1.0..=16.0).contains(&divisor) {
        anyhow::bail!("bytes_per_token must be in 1.0..=16.0 (got {divisor})");
    }
    let lmdb = lmdb_path(store_root);
    std::fs::create_dir_all(&lmdb)?;
    let payload = json!({
        "bytes_per_token": divisor,
        "note": "Local tokenizer calibration divisor. The 4.0 default is a disclosed estimate; set this by encoding a representative sample with the tokenizer of your choice.",
        "set_at": chrono::Utc::now().to_rfc3339(),
    });
    std::fs::write(
        lmdb.join(CALIBRATION_FILE),
        serde_json::to_string_pretty(&payload)?,
    )?;
    Ok(())
}

fn family_of(tool: &str) -> &'static str {
    if tool.starts_with("memory.") {
        "memory"
    } else if tool.starts_with("session.") {
        "session"
    } else if tool == "gnosis" {
        "gnosis"
    } else {
        "other"
    }
}

/// Accumulated ledger counters (one row set per op family).
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
struct Counters {
    record_calls: u64,
    record_bytes_stored: u64,
    continuity_calls: u64,
    bytes_available: u64,
    bytes_injected: u64,
    turns_available: u64,
    turns_returned: u64,
    turns_omitted: u64,
    recall_calls: u64,
    recall_results: u64,
    recall_bytes_available: u64,
    recall_bytes_injected: u64,
    malformed_rows: u64,
}

impl Counters {
    fn fold_row(&mut self, row: &Value) {
        let u = |key: &str| row.get(key).and_then(Value::as_u64).unwrap_or(0);
        match row.get("op").and_then(Value::as_str) {
            Some("record") => {
                self.record_calls += 1;
                self.record_bytes_stored += u("bytes_stored");
            }
            Some("continuity") => {
                self.continuity_calls += 1;
                self.bytes_available += u("bytes_available");
                self.bytes_injected += u("bytes_injected");
                self.turns_available += u("turns_available");
                self.turns_returned += u("turns_returned");
                self.turns_omitted += u("turns_omitted");
            }
            Some("recall") => {
                self.recall_calls += 1;
                self.recall_results += u("results");
                self.recall_bytes_available += u("bytes_available");
                self.recall_bytes_injected += u("bytes_injected");
            }
            _ => {}
        }
    }
}

/// Fold every complete line in `bytes` into `counters` (and optional day
/// buckets). Returns the bytes consumed through the last newline — a torn
/// final line is left for the next pass, so a crash cannot double-count.
fn fold_bytes(
    bytes: &[u8],
    counters: &mut Counters,
    mut days: Option<&mut BTreeMap<String, Counters>>,
) -> usize {
    let Some(last_newline) = bytes.iter().rposition(|b| *b == b'\n') else {
        return 0;
    };
    for line in bytes[..=last_newline].split(|b| *b == b'\n') {
        if line.iter().all(u8::is_ascii_whitespace) {
            continue;
        }
        let Ok(text) = std::str::from_utf8(line) else {
            counters.malformed_rows += 1;
            continue;
        };
        let Ok(row) = serde_json::from_str::<Value>(text) else {
            counters.malformed_rows += 1;
            continue;
        };
        counters.fold_row(&row);
        if let Some(days) = days.as_deref_mut() {
            let day = row
                .get("ts_ms")
                .and_then(Value::as_u64)
                .and_then(|ms| chrono::DateTime::from_timestamp_millis(i64::try_from(ms).ok()?))
                .map_or_else(
                    || "unknown".to_string(),
                    |dt| dt.format("%Y-%m-%d").to_string(),
                );
            days.entry(day).or_default().fold_row(&row);
        }
    }
    last_newline + 1
}

const ROLLUP_FILE: &str = "savings_rollup.json";

#[derive(Debug, Default)]
struct Rollup {
    cursor_bytes: u64,
    days: BTreeMap<String, Counters>,
    totals: Counters,
}

fn load_rollup(lmdb: &Path) -> Rollup {
    let Ok(text) = std::fs::read_to_string(lmdb.join(ROLLUP_FILE)) else {
        return Rollup::default();
    };
    let Ok(v) = serde_json::from_str::<Value>(&text) else {
        tracing::warn!("savings rollup is unparseable; starting a fresh fold");
        return Rollup::default();
    };
    Rollup {
        cursor_bytes: v.get("cursor_bytes").and_then(Value::as_u64).unwrap_or(0),
        days: v
            .get("days")
            .and_then(|d| serde_json::from_value(d.clone()).ok())
            .unwrap_or_default(),
        totals: v
            .get("totals")
            .and_then(|t| serde_json::from_value(t.clone()).ok())
            .unwrap_or_default(),
    }
}

fn write_rollup(lmdb: &Path, rollup: &Rollup) -> Result<()> {
    let payload = json!({
        "version": 1,
        "ledger_file": LEDGER_FILE,
        "cursor_bytes": rollup.cursor_bytes,
        "days": rollup.days,
        "totals": rollup.totals,
        "folded_at": chrono::Utc::now().to_rfc3339(),
    });
    let path = lmdb.join(ROLLUP_FILE);
    let tmp = path.with_extension("tmp");
    std::fs::write(&tmp, serde_json::to_string_pretty(&payload)?)?;
    std::fs::rename(&tmp, &path)?;
    Ok(())
}

/// Fold the unfolded ledger tail into `<lmdb>/savings_rollup.json`.
///
/// Idempotent and crash-safe: the cursor advances only past complete lines,
/// and a shrunken/rotated ledger resets the cursor (folded totals stay as
/// history). Best-effort callers (daemon checkpoint, shutdown) log failures
/// instead of failing.
pub fn rollup_in_lmdb(lmdb: &Path) -> Result<Value> {
    let mut rollup = load_rollup(lmdb);
    let Ok(bytes) = std::fs::read(lmdb.join(LEDGER_FILE)) else {
        write_rollup(lmdb, &rollup)?;
        return Ok(json!({
            "status": "success",
            "cursor_bytes": rollup.cursor_bytes,
            "days": rollup.days.len(),
            "note": "no ledger yet",
        }));
    };
    if (bytes.len() as u64) < rollup.cursor_bytes {
        tracing::warn!(
            "savings ledger shrank below the rollup cursor; resetting the cursor (folded totals kept)"
        );
        rollup.cursor_bytes = 0;
    }
    let start = usize::try_from(rollup.cursor_bytes)
        .unwrap_or(0)
        .min(bytes.len());
    let mut totals = rollup.totals.clone();
    let consumed = fold_bytes(&bytes[start..], &mut totals, Some(&mut rollup.days));
    rollup.totals = totals;
    rollup.cursor_bytes += consumed as u64;
    write_rollup(lmdb, &rollup)?;
    Ok(json!({
        "status": "success",
        "cursor_bytes": rollup.cursor_bytes,
        "days": rollup.days.len(),
        "totals": {
            "record": {"calls": rollup.totals.record_calls, "bytes_stored": rollup.totals.record_bytes_stored},
            "continuity": {
                "calls": rollup.totals.continuity_calls,
                "bytes_available": rollup.totals.bytes_available,
                "bytes_injected": rollup.totals.bytes_injected,
            },
            "recall": {
                "calls": rollup.totals.recall_calls,
                "bytes_available": rollup.totals.recall_bytes_available,
                "bytes_injected": rollup.totals.recall_bytes_injected,
            },
        },
    }))
}

/// Aggregate the local ledger + dispatch stats into one report value.
///
/// Reads the folded rollup plus only the unfolded tail (O(tail)); missing
/// files are reported as zeros with `ledger_present: false` — a fresh store
/// is not an error.
pub fn aggregate(store_root: &Path) -> Result<Value> {
    aggregate_mode(store_root, true)
}

/// Full-history scan (`wm ledger --full`) — audits, never the hot path.
pub fn aggregate_full(store_root: &Path) -> Result<Value> {
    aggregate_mode(store_root, false)
}

fn aggregate_mode(store_root: &Path, use_rollup: bool) -> Result<Value> {
    let lmdb = lmdb_path(store_root);
    let ledger_path = lmdb.join(LEDGER_FILE);
    let rollup_present = lmdb.join(ROLLUP_FILE).exists();

    let (mut counters, start) = if use_rollup {
        let rollup = load_rollup(&lmdb);
        (rollup.totals, rollup.cursor_bytes)
    } else {
        (Counters::default(), 0)
    };
    let ledger_present = ledger_path.exists();
    if let Ok(bytes) = std::fs::read(&ledger_path) {
        let mut start = usize::try_from(start).unwrap_or(0);
        if start > bytes.len() {
            start = 0; // rotated/shrunken ledger: fold from the top, totals kept
        }
        fold_bytes(&bytes[start..], &mut counters, None);
    }

    // Dispatch counters: every WM operation is local compute. The families
    // are the recall/continuity surface; "other" is governance/diagnostics.
    let mut local_total = 0u64;
    let mut families: BTreeMap<&'static str, u64> = BTreeMap::new();
    let mut tools: BTreeMap<String, u64> = BTreeMap::new();
    let stats_path = lmdb.join(TOOL_STATS_FILE);
    let stats_present = stats_path.exists();
    if let Ok(text) = std::fs::read_to_string(&stats_path) {
        if let Ok(stats) = serde_json::from_str::<Value>(&text) {
            if let Some(obj) = stats.as_object() {
                for (name, entry) in obj {
                    let calls = entry.get("call_count").and_then(Value::as_u64).unwrap_or(0);
                    if calls == 0 {
                        continue;
                    }
                    local_total += calls;
                    *families.entry(family_of(name)).or_insert(0) += calls;
                    *tools.entry(name.clone()).or_insert(0) += calls;
                }
            }
        }
    }
    let mut top_tools: Vec<Value> = tools
        .iter()
        .map(|(name, calls)| json!({"tool": name, "calls": calls}))
        .collect();
    top_tools.sort_by(|a, b| {
        b["calls"]
            .as_u64()
            .cmp(&a["calls"].as_u64())
            .then_with(|| a["tool"].as_str().cmp(&b["tool"].as_str()))
    });
    top_tools.truncate(5);

    let c = counters;
    let saved = c.bytes_available.saturating_sub(c.bytes_injected);
    let divisor = bytes_per_token(store_root);
    let token_equivalent = (saved as f64 / divisor).round() as u64;
    let ratio = if c.bytes_injected == 0 {
        Value::Null
    } else {
        json!((c.bytes_available as f64 / c.bytes_injected as f64 * 100.0).round() / 100.0)
    };

    Ok(json!({
        "status": "success",
        "store": store_root.display().to_string(),
        "ledger_path": ledger_path.display().to_string(),
        "ledger_present": ledger_present,
        "rollup_present": rollup_present,
        "stats_present": stats_present,
        "malformed_rows": c.malformed_rows,
        "record": {"calls": c.record_calls, "bytes_stored": c.record_bytes_stored},
        "continuity": {
            "calls": c.continuity_calls,
            "bytes_available": c.bytes_available,
            "bytes_injected": c.bytes_injected,
            "turns_available": c.turns_available,
            "turns_returned": c.turns_returned,
            "turns_omitted": c.turns_omitted,
        },
        "recall": {
            "calls": c.recall_calls,
            "results": c.recall_results,
            "bytes_available": c.recall_bytes_available,
            "bytes_injected": c.recall_bytes_injected,
        },
        "state_to_context_ratio": ratio,
        "token_equivalent_saved_estimate": token_equivalent,
        "bytes_per_token_divisor": divisor,
        "local_ops": {
            "total": local_total,
            "by_family": families,
            "top_tools": top_tools,
        },
        "disclaimer": "Local-only diagnostic estimate. State-over-transcript is WhiteMagic-attributable; provider/harness prompt caching is context, not our saving. See docs/TOKEN_LEDGER.md.",
    }))
}

/// `wm ledger` — print the local report (human table or JSON).
pub fn run(store_root: &Path, as_json: bool, full: bool) -> Result<()> {
    let report = if full {
        aggregate_full(store_root)?
    } else {
        aggregate(store_root)?
    };
    if as_json {
        println!("{}", serde_json::to_string_pretty(&report)?);
        return Ok(());
    }

    let c = &report["continuity"];
    let r = &report["record"];
    let local = &report["local_ops"];
    println!("=== Local savings ledger ===");
    println!("Store: {}", report["store"].as_str().unwrap_or(""));
    if !report["ledger_present"].as_bool().unwrap_or(false) {
        println!("Ledger: not present yet — it fills as sessions record and resume.");
    }
    println!(
        "Records: {} calls · {} bytes stored",
        r["calls"].as_u64().unwrap_or(0),
        r["bytes_stored"].as_u64().unwrap_or(0)
    );
    println!(
        "Continuity: {} calls · {} bytes available → {} bytes injected (ratio {})",
        c["calls"].as_u64().unwrap_or(0),
        c["bytes_available"].as_u64().unwrap_or(0),
        c["bytes_injected"].as_u64().unwrap_or(0),
        report["state_to_context_ratio"]
    );
    println!(
        "Token-equivalent saved (estimate, bytes/{}): {}",
        report["bytes_per_token_divisor"]
            .as_f64()
            .unwrap_or(DEFAULT_BYTES_PER_TOKEN),
        report["token_equivalent_saved_estimate"]
            .as_u64()
            .unwrap_or(0)
    );
    let rc = &report["recall"];
    println!(
        "Recall: {} calls · {} results · {} bytes available → {} bytes injected",
        rc["calls"].as_u64().unwrap_or(0),
        rc["results"].as_u64().unwrap_or(0),
        rc["bytes_available"].as_u64().unwrap_or(0),
        rc["bytes_injected"].as_u64().unwrap_or(0)
    );
    println!(
        "Local WM ops (100% local compute): {} total",
        local["total"].as_u64().unwrap_or(0)
    );
    if let Some(fams) = local["by_family"].as_object() {
        let parts: Vec<String> = fams
            .iter()
            .map(|(k, v)| format!("{k}={}", v.as_u64().unwrap_or(0)))
            .collect();
        println!("  by family: {}", parts.join(" · "));
    }
    println!("{}", report["disclaimer"].as_str().unwrap_or(""));
    Ok(())
}

/// `wm ledger --rollup` — fold the unfolded tail now and print a summary.
pub fn run_rollup(store_root: &Path, as_json: bool) -> Result<()> {
    let summary = rollup_in_lmdb(&lmdb_path(store_root))?;
    if as_json {
        println!("{}", serde_json::to_string_pretty(&summary)?);
    } else {
        println!(
            "Savings rollup folded: cursor {} bytes · {} day(s) · {} record / {} continuity / {} recall calls",
            summary["cursor_bytes"].as_u64().unwrap_or(0),
            summary["days"].as_u64().unwrap_or(0),
            summary["totals"]["record"]["calls"].as_u64().unwrap_or(0),
            summary["totals"]["continuity"]["calls"]
                .as_u64()
                .unwrap_or(0),
            summary["totals"]["recall"]["calls"].as_u64().unwrap_or(0),
        );
    }
    Ok(())
}

/// Compact savings block for `wm stats` (no store/disclaimer boilerplate —
/// the full report stays `wm ledger`).
pub fn run_brief(store_root: &Path) -> Result<()> {
    let report = aggregate(store_root)?;
    let c = &report["continuity"];
    let r = &report["record"];
    let rc = &report["recall"];
    let local = &report["local_ops"];
    println!("=== Savings Ledger (local-only) ===");
    println!(
        "Records: {} calls · Continuity: {} calls ({} B available → {} B injected, ratio {}) · Recall: {} calls",
        r["calls"].as_u64().unwrap_or(0),
        c["calls"].as_u64().unwrap_or(0),
        c["bytes_available"].as_u64().unwrap_or(0),
        c["bytes_injected"].as_u64().unwrap_or(0),
        report["state_to_context_ratio"],
        rc["calls"].as_u64().unwrap_or(0),
    );
    println!(
        "Token-equivalent saved (estimate, bytes/{}): {} · local WM ops: {}",
        report["bytes_per_token_divisor"]
            .as_f64()
            .unwrap_or(DEFAULT_BYTES_PER_TOKEN),
        report["token_equivalent_saved_estimate"]
            .as_u64()
            .unwrap_or(0),
        local["total"].as_u64().unwrap_or(0),
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture_store(dir: &Path) {
        let lmdb = dir.join("lmdb");
        std::fs::create_dir_all(&lmdb).unwrap();
        std::fs::write(
            lmdb.join(LEDGER_FILE),
            concat!(
                "{\"op\":\"record\",\"bytes_stored\":1000,\"ts_ms\":1}\n",
                "{\"op\":\"continuity\",\"bytes_available\":1000,\"bytes_injected\":100,\"turns_available\":5,\"turns_returned\":3,\"turns_omitted\":2,\"ts_ms\":2}\n",
                "{\"op\":\"recall\",\"results\":2,\"bytes_available\":800,\"bytes_injected\":200,\"ts_ms\":3}\n",
                "not json\n"
            ),
        )
        .unwrap();
        std::fs::write(
            lmdb.join(TOOL_STATS_FILE),
            r#"{"memory.search":{"call_count":10},"session.record":{"call_count":5},"karma.report":{"call_count":2}}"#,
        )
        .unwrap();
    }

    #[test]
    fn aggregate_separates_state_savings_from_local_ops() {
        let dir = tempfile::tempdir().unwrap();
        fixture_store(dir.path());
        let report = aggregate(dir.path()).unwrap();

        assert_eq!(report["record"]["calls"], 1);
        assert_eq!(report["record"]["bytes_stored"], 1000);
        assert_eq!(report["continuity"]["bytes_available"], 1000);
        assert_eq!(report["continuity"]["bytes_injected"], 100);
        assert_eq!(report["recall"]["calls"], 1);
        assert_eq!(report["recall"]["results"], 2);
        assert_eq!(report["recall"]["bytes_available"], 800);
        assert_eq!(report["recall"]["bytes_injected"], 200);
        assert_eq!(report["state_to_context_ratio"], 10.0);
        assert_eq!(report["token_equivalent_saved_estimate"], 225);
        assert_eq!(report["malformed_rows"], 1);
        assert_eq!(report["local_ops"]["total"], 17);
        assert_eq!(report["local_ops"]["by_family"]["memory"], 10);
        assert_eq!(report["local_ops"]["by_family"]["session"], 5);
        assert_eq!(report["local_ops"]["by_family"]["other"], 2);
        assert_eq!(report["local_ops"]["top_tools"][0]["tool"], "memory.search");
    }

    #[test]
    fn aggregate_reports_missing_ledger_without_error() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(dir.path().join("lmdb")).unwrap();
        let report = aggregate(dir.path()).unwrap();
        assert_eq!(report["ledger_present"], false);
        assert_eq!(report["continuity"]["calls"], 0);
        assert_eq!(report["state_to_context_ratio"], Value::Null);
    }

    #[test]
    fn calibration_changes_the_divisor_and_estimate() {
        let dir = tempfile::tempdir().unwrap();
        fixture_store(dir.path());
        assert_eq!(bytes_per_token(dir.path()), DEFAULT_BYTES_PER_TOKEN);

        set_calibration(dir.path(), 3.0).unwrap();
        assert_eq!(bytes_per_token(dir.path()), 3.0);
        let report = aggregate(dir.path()).unwrap();
        assert_eq!(report["bytes_per_token_divisor"], 3.0);
        // saved = 1000 - 100 = 900; 900 / 3 = 300
        assert_eq!(report["token_equivalent_saved_estimate"], 300);

        assert!(set_calibration(dir.path(), 0.5).is_err(), "below range");
        assert!(set_calibration(dir.path(), 20.0).is_err(), "above range");
    }

    #[test]
    fn rollup_then_aggregate_equals_full_scan() {
        let dir = tempfile::tempdir().unwrap();
        fixture_store(dir.path());
        let full = aggregate_full(dir.path()).unwrap();

        let folded = rollup_in_lmdb(&dir.path().join("lmdb")).unwrap();
        assert_eq!(folded["status"], "success");
        assert!(folded["cursor_bytes"].as_u64().unwrap() > 0);

        let report = aggregate(dir.path()).unwrap();
        assert_eq!(report["rollup_present"], true);
        assert_eq!(report["record"], full["record"]);
        assert_eq!(report["continuity"], full["continuity"]);
        assert_eq!(report["recall"], full["recall"]);
        assert_eq!(report["malformed_rows"], full["malformed_rows"]);
        assert_eq!(
            report["state_to_context_ratio"],
            full["state_to_context_ratio"]
        );
        assert_eq!(
            report["token_equivalent_saved_estimate"],
            full["token_equivalent_saved_estimate"]
        );
    }

    #[test]
    fn rollup_leaves_a_torn_line_for_the_next_pass() {
        let dir = tempfile::tempdir().unwrap();
        fixture_store(dir.path());
        let lmdb = dir.path().join("lmdb");
        let ledger = lmdb.join(LEDGER_FILE);
        let mut text = std::fs::read_to_string(&ledger).unwrap();
        text.push_str("{\"op\":\"record\",\"bytes_stored\":77,\"ts_ms\":4}"); // no newline: torn
        std::fs::write(&ledger, &text).unwrap();

        rollup_in_lmdb(&lmdb).unwrap();
        let first = aggregate(dir.path()).unwrap();
        assert_eq!(first["record"]["calls"], 1, "a torn line must not fold yet");

        std::fs::write(&ledger, format!("{text}\n")).unwrap();
        rollup_in_lmdb(&lmdb).unwrap();
        let second = aggregate(dir.path()).unwrap();
        assert_eq!(second["record"]["calls"], 2);
        assert_eq!(second["record"]["bytes_stored"], 1077);
    }

    #[test]
    fn shrunken_ledger_resets_cursor_and_keeps_totals() {
        let dir = tempfile::tempdir().unwrap();
        fixture_store(dir.path());
        let lmdb = dir.path().join("lmdb");
        rollup_in_lmdb(&lmdb).unwrap();

        // Rotation/shrink: a fresh ledger with one new row.
        std::fs::write(
            lmdb.join(LEDGER_FILE),
            "{\"op\":\"recall\",\"results\":1,\"bytes_available\":10,\"bytes_injected\":5,\"ts_ms\":5}\n",
        )
        .unwrap();
        rollup_in_lmdb(&lmdb).unwrap();

        let report = aggregate(dir.path()).unwrap();
        // Folded history is kept (1 record, 1 continuity, 1 recall) and the
        // fresh ledger's row is added once.
        assert_eq!(report["record"]["calls"], 1);
        assert_eq!(report["continuity"]["calls"], 1);
        assert_eq!(report["recall"]["calls"], 2);
        assert_eq!(report["recall"]["bytes_available"], 810);
    }
}
