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

/// Aggregate the local ledger + dispatch stats into one report value.
///
/// Missing files are reported as zeros with `ledger_present: false` — a
/// fresh store is not an error.
pub fn aggregate(store_root: &Path) -> Result<Value> {
    let lmdb = lmdb_path(store_root);
    let ledger_path = lmdb.join(LEDGER_FILE);

    let mut record_calls = 0u64;
    let mut record_bytes_stored = 0u64;
    let mut continuity_calls = 0u64;
    let mut bytes_available = 0u64;
    let mut bytes_injected = 0u64;
    let mut turns_available = 0u64;
    let mut turns_returned = 0u64;
    let mut turns_omitted = 0u64;
    let mut recall_calls = 0u64;
    let mut recall_results = 0u64;
    let mut recall_bytes_available = 0u64;
    let mut recall_bytes_injected = 0u64;
    let mut malformed = 0u64;

    let ledger_present = ledger_path.exists();
    if let Ok(text) = std::fs::read_to_string(&ledger_path) {
        for line in text.lines().filter(|l| !l.trim().is_empty()) {
            let Ok(row) = serde_json::from_str::<Value>(line) else {
                malformed += 1;
                continue;
            };
            let u = |key: &str| row.get(key).and_then(Value::as_u64).unwrap_or(0);
            match row.get("op").and_then(Value::as_str) {
                Some("record") => {
                    record_calls += 1;
                    record_bytes_stored += u("bytes_stored");
                }
                Some("continuity") => {
                    continuity_calls += 1;
                    bytes_available += u("bytes_available");
                    bytes_injected += u("bytes_injected");
                    turns_available += u("turns_available");
                    turns_returned += u("turns_returned");
                    turns_omitted += u("turns_omitted");
                }
                Some("recall") => {
                    recall_calls += 1;
                    recall_results += u("results");
                    recall_bytes_available += u("bytes_available");
                    recall_bytes_injected += u("bytes_injected");
                }
                _ => {}
            }
        }
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

    let saved = bytes_available.saturating_sub(bytes_injected);
    let divisor = bytes_per_token(store_root);
    let token_equivalent = (saved as f64 / divisor).round() as u64;
    let ratio = if bytes_injected == 0 {
        Value::Null
    } else {
        json!((bytes_available as f64 / bytes_injected as f64 * 100.0).round() / 100.0)
    };

    Ok(json!({
        "status": "success",
        "store": store_root.display().to_string(),
        "ledger_path": ledger_path.display().to_string(),
        "ledger_present": ledger_present,
        "stats_present": stats_present,
        "malformed_rows": malformed,
        "record": {"calls": record_calls, "bytes_stored": record_bytes_stored},
        "continuity": {
            "calls": continuity_calls,
            "bytes_available": bytes_available,
            "bytes_injected": bytes_injected,
            "turns_available": turns_available,
            "turns_returned": turns_returned,
            "turns_omitted": turns_omitted,
        },
        "recall": {
            "calls": recall_calls,
            "results": recall_results,
            "bytes_available": recall_bytes_available,
            "bytes_injected": recall_bytes_injected,
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
pub fn run(store_root: &Path, as_json: bool) -> Result<()> {
    let report = aggregate(store_root)?;
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
}
