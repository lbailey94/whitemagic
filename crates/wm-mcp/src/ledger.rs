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
/// Disclosed estimate divisor (bytes per token). Recalibrate against a real
/// tokenizer before any external publication; see docs/TOKEN_LEDGER.md.
const BYTES_PER_TOKEN: u64 = 4;

fn lmdb_path(store_root: &Path) -> PathBuf {
    store_root.join("lmdb")
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
        "state_to_context_ratio": ratio,
        "token_equivalent_saved_estimate": saved / BYTES_PER_TOKEN,
        "bytes_per_token_divisor": BYTES_PER_TOKEN,
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
        report["bytes_per_token_divisor"].as_u64().unwrap_or(4),
        report["token_equivalent_saved_estimate"]
            .as_u64()
            .unwrap_or(0)
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
}
