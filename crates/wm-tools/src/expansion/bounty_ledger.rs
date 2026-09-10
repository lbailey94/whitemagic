//! Bounty ledger — submission tracking and outcome learning.
//!
//! File-backed JSONL ledger (`<store>/bounty_ledger.jsonl`) recording every
//! submission and its outcome, so rejection reasons become training signal
//! instead of dead ends (the wide-net, evidence-gated strategy).
//!
//! Tools: `bounty.ledger.record`, `bounty.ledger.update`,
//! `bounty.ledger.list`, `bounty.ledger.stats`.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::path::PathBuf;
use std::sync::{Arc, Mutex, MutexGuard};
use std::time::{SystemTime, UNIX_EPOCH};
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};

/// Standard rejection-reason taxonomy (used for the compounding loop).
pub const REJECTION_REASONS: &[&str] = &[
    "not_reproducible",
    "out_of_scope",
    "duplicate",
    "expected_behavior",
    "insufficient_impact",
    "already_known",
    "report_quality",
    "third_party",
    "other",
];

/// Valid submission statuses.
pub const STATUSES: &[&str] = &[
    "draft",
    "submitted",
    "triaged",
    "accepted",
    "rejected",
    "duplicate",
    "withdrawn",
];

/// One ledger entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LedgerEntry {
    /// Entry id (`bl_<unix>_<seq>`).
    pub id: String,
    /// Unix epoch seconds of recording.
    pub recorded_at: i64,
    /// Platform (bugcrowd|hackerone|huntr|0din|gray_swan|immunefi|other).
    pub platform: String,
    /// Target/program name.
    pub target: String,
    /// Finding title.
    pub title: String,
    /// Status (see `STATUSES`).
    pub status: String,
    /// Reward in USD when known.
    #[serde(default)]
    pub reward_usd: Option<f64>,
    /// Standardized rejection reason when rejected/duplicate.
    #[serde(default)]
    pub rejection_reason: Option<String>,
    /// Link to the submission/report.
    #[serde(default)]
    pub url: Option<String>,
    /// Free-form notes (evidence quality, remaining work, …).
    #[serde(default)]
    pub notes: Option<String>,
}

fn now_unix() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| i64::try_from(d.as_secs()).unwrap_or(i64::MAX))
}

pub struct Ledger {
    path: PathBuf,
    entries: Vec<LedgerEntry>,
}

impl Ledger {
    fn load(path: impl Into<PathBuf>) -> Self {
        let path = path.into();
        let mut entries = Vec::new();
        if let Ok(contents) = std::fs::read_to_string(&path) {
            for line in contents.lines() {
                if let Ok(entry) = serde_json::from_str::<LedgerEntry>(line) {
                    entries.push(entry);
                }
            }
        }
        Self { path, entries }
    }

    fn persist(&self) -> wm_core::Result<()> {
        let tmp = self.path.with_extension("jsonl.tmp");
        let mut body = String::new();
        for entry in &self.entries {
            let line = serde_json::to_string(entry)
                .map_err(|e| CoreError::Internal(format!("ledger serialize: {e}")))?;
            body.push_str(&line);
            body.push('\n');
        }
        std::fs::write(&tmp, body)
            .map_err(|e| CoreError::Internal(format!("ledger write {}: {e}", tmp.display())))?;
        std::fs::rename(&tmp, &self.path).map_err(|e| {
            CoreError::Internal(format!("ledger rename {}: {e}", self.path.display()))
        })?;
        Ok(())
    }

    fn record(&mut self, mut entry: LedgerEntry) -> wm_core::Result<LedgerEntry> {
        entry.id = format!("bl_{}_{}", now_unix(), self.entries.len() + 1);
        self.entries.push(entry.clone());
        self.persist()?;
        Ok(entry)
    }

    fn update(&mut self, id: &str, patch: &Value) -> wm_core::Result<LedgerEntry> {
        let entry = self
            .entries
            .iter_mut()
            .find(|e| e.id == id)
            .ok_or_else(|| CoreError::InvalidArgs(format!("unknown ledger id: {id}")))?;
        if let Some(status) = patch.get("status").and_then(Value::as_str) {
            if !STATUSES.contains(&status) {
                return Err(CoreError::InvalidArgs(format!(
                    "invalid status '{status}' (expected one of {STATUSES:?})"
                )));
            }
            entry.status = status.to_string();
        }
        if let Some(reason) = patch.get("rejection_reason").and_then(Value::as_str) {
            if reason != "none" && !REJECTION_REASONS.contains(&reason) {
                return Err(CoreError::InvalidArgs(format!(
                    "invalid rejection_reason '{reason}' (expected one of {REJECTION_REASONS:?})"
                )));
            }
            entry.rejection_reason = (reason != "none").then(|| reason.to_string());
        }
        if let Some(reward) = patch.get("reward_usd").and_then(Value::as_f64) {
            entry.reward_usd = Some(reward);
        }
        if let Some(url) = patch.get("url").and_then(Value::as_str) {
            entry.url = Some(url.to_string());
        }
        if let Some(notes) = patch.get("notes").and_then(Value::as_str) {
            entry.notes = Some(notes.to_string());
        }
        let updated = entry.clone();
        self.persist()?;
        Ok(updated)
    }

    fn stats(&self) -> Value {
        let mut by_status: std::collections::HashMap<&str, u64> = std::collections::HashMap::new();
        let mut by_platform: std::collections::HashMap<&str, u64> =
            std::collections::HashMap::new();
        let mut reasons: std::collections::HashMap<&str, u64> = std::collections::HashMap::new();
        let mut earned = 0.0_f64;
        for entry in &self.entries {
            *by_status.entry(entry.status.as_str()).or_insert(0) += 1;
            *by_platform.entry(entry.platform.as_str()).or_insert(0) += 1;
            if let Some(reason) = &entry.rejection_reason {
                *reasons.entry(reason.as_str()).or_insert(0) += 1;
            }
            if entry.status == "accepted" {
                earned += entry.reward_usd.unwrap_or(0.0);
            }
        }
        let accepted = *by_status.get("accepted").unwrap_or(&0);
        let rejected = *by_status.get("rejected").unwrap_or(&0);
        let decided = accepted + rejected;
        let acceptance_rate = if decided > 0 {
            accepted as f64 / decided as f64
        } else {
            0.0
        };
        json!({
            "total_entries": self.entries.len(),
            "by_status": by_status,
            "by_platform": by_platform,
            "rejection_reasons": reasons,
            "accepted": accepted,
            "rejected": rejected,
            "acceptance_rate": acceptance_rate,
            "earned_usd": earned,
            "taxonomy": {"statuses": STATUSES, "rejection_reasons": REJECTION_REASONS},
        })
    }
}

pub type SharedLedger = Arc<Mutex<Ledger>>;

fn lock_ledger(ledger: &SharedLedger) -> wm_core::Result<MutexGuard<'_, Ledger>> {
    ledger
        .lock()
        .map_err(|e| CoreError::Internal(format!("bounty ledger lock poisoned: {e}")))
}

// ── Tools ──────────────────────────────────────────────────────────────

/// `bounty.ledger.record` — record a submission/finding.
pub struct LedgerRecordTool {
    ledger: SharedLedger,
    stats: ToolStats,
    effects: EffectRow,
}

impl LedgerRecordTool {
    #[must_use]
    pub fn new(ledger: SharedLedger) -> Self {
        Self {
            ledger,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::DharmaRules],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for LedgerRecordTool {
    fn name(&self) -> &str {
        "bounty.ledger.record"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Record a bounty submission/finding. Args: platform, target, title, status (draft|submitted|triaged|accepted|rejected|duplicate|withdrawn, default draft), reward_usd (optional), rejection_reason (optional, taxonomy-validated), url, notes."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let platform = args
            .get("platform")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("platform is required".into()))?;
        let target = args
            .get("target")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("target is required".into()))?;
        let title = args
            .get("title")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("title is required".into()))?;
        let status = args
            .get("status")
            .and_then(Value::as_str)
            .unwrap_or("draft");
        if !STATUSES.contains(&status) {
            return Err(CoreError::InvalidArgs(format!(
                "invalid status '{status}' (expected one of {STATUSES:?})"
            )));
        }
        let rejection_reason = args.get("rejection_reason").and_then(Value::as_str);
        if let Some(reason) = rejection_reason {
            if !REJECTION_REASONS.contains(&reason) {
                return Err(CoreError::InvalidArgs(format!(
                    "invalid rejection_reason '{reason}' (expected one of {REJECTION_REASONS:?})"
                )));
            }
        }
        let mut ledger = lock_ledger(&self.ledger)?;
        let entry = ledger.record(LedgerEntry {
            id: String::new(),
            recorded_at: now_unix(),
            platform: platform.to_string(),
            target: target.to_string(),
            title: title.to_string(),
            status: status.to_string(),
            reward_usd: args.get("reward_usd").and_then(Value::as_f64),
            rejection_reason: rejection_reason.map(str::to_string),
            url: args.get("url").and_then(Value::as_str).map(str::to_string),
            notes: args
                .get("notes")
                .and_then(Value::as_str)
                .map(str::to_string),
        })?;
        Ok(json!({"status": "success", "entry": entry}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `bounty.ledger.update` — update status/reward/reason.
pub struct LedgerUpdateTool {
    ledger: SharedLedger,
    stats: ToolStats,
    effects: EffectRow,
}

impl LedgerUpdateTool {
    #[must_use]
    pub fn new(ledger: SharedLedger) -> Self {
        Self {
            ledger,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::DharmaRules],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for LedgerUpdateTool {
    fn name(&self) -> &str {
        "bounty.ledger.update"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Update a bounty ledger entry. Args: id, status?, reward_usd?, rejection_reason? (or \"none\" to clear), url?, notes?."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let id = args
            .get("id")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("id is required".into()))?;
        let mut ledger = lock_ledger(&self.ledger)?;
        let entry = ledger.update(id, &args)?;
        Ok(json!({"status": "success", "entry": entry}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `bounty.ledger.list` — list entries with optional filters.
pub struct LedgerListTool {
    ledger: SharedLedger,
    stats: ToolStats,
    effects: EffectRow,
}

impl LedgerListTool {
    #[must_use]
    pub fn new(ledger: SharedLedger) -> Self {
        Self {
            ledger,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
impl Tool for LedgerListTool {
    fn name(&self) -> &str {
        "bounty.ledger.list"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List bounty ledger entries. Args: status (optional), platform (optional), limit (default 20)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let status = args.get("status").and_then(Value::as_str);
        let platform = args.get("platform").and_then(Value::as_str);
        let limit = args
            .get("limit")
            .and_then(Value::as_u64)
            .map_or(20, |v| usize::try_from(v).unwrap_or(20));
        let ledger = lock_ledger(&self.ledger)?;
        let entries: Vec<&LedgerEntry> = ledger
            .entries
            .iter()
            .rev()
            .filter(|e| status.is_none_or(|s| e.status == s))
            .filter(|e| platform.is_none_or(|p| e.platform == p))
            .take(limit)
            .collect();
        Ok(json!({"status": "success", "count": entries.len(), "entries": entries}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `bounty.ledger.stats` — aggregate outcomes + taxonomy.
pub struct LedgerStatsTool {
    ledger: SharedLedger,
    stats: ToolStats,
    effects: EffectRow,
}

impl LedgerStatsTool {
    #[must_use]
    pub fn new(ledger: SharedLedger) -> Self {
        Self {
            ledger,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![]),
        }
    }
}

#[async_trait]
impl Tool for LedgerStatsTool {
    fn name(&self) -> &str {
        "bounty.ledger.stats"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Bounty ledger stats: counts by status/platform, acceptance rate, earned USD, rejection-reason histogram, taxonomy."
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let ledger = lock_ledger(&self.ledger)?;
        Ok(json!({"status": "success", "stats": ledger.stats()}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the bounty ledger surface (4 tools) from a ledger file path.
#[must_use]
pub fn register_bounty_ledger(
    registry: &wm_dispatch::ToolRegistry,
    ledger_path: PathBuf,
) -> wm_dispatch::ToolRegistry {
    let ledger: SharedLedger = Arc::new(Mutex::new(Ledger::load(ledger_path)));
    registry
        .register(Arc::new(LedgerRecordTool::new(ledger.clone())))
        .register(Arc::new(LedgerUpdateTool::new(ledger.clone())))
        .register(Arc::new(LedgerListTool::new(ledger.clone())))
        .register(Arc::new(LedgerStatsTool::new(ledger)))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_ledger() -> (SharedLedger, tempfile::TempDir) {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("bounty_ledger.jsonl");
        (Arc::new(Mutex::new(Ledger::load(path))), dir)
    }

    #[test]
    fn record_and_reload() {
        let (ledger, dir) = temp_ledger();
        let path = dir.path().join("bounty_ledger.jsonl");
        {
            let mut l = ledger.lock().unwrap();
            let entry = l
                .record(LedgerEntry {
                    id: String::new(),
                    recorded_at: now_unix(),
                    platform: "0din".into(),
                    target: "genai-target".into(),
                    title: "jailbreak candidate".into(),
                    status: "submitted".into(),
                    reward_usd: None,
                    rejection_reason: None,
                    url: None,
                    notes: None,
                })
                .unwrap();
            assert!(entry.id.starts_with("bl_"));
        }
        let reloaded = Ledger::load(path);
        assert_eq!(reloaded.entries.len(), 1);
        assert_eq!(reloaded.entries[0].platform, "0din");
    }

    #[test]
    fn update_validates_taxonomy() {
        let (ledger, _dir) = temp_ledger();
        let mut l = ledger.lock().unwrap();
        let entry = l
            .record(LedgerEntry {
                id: String::new(),
                recorded_at: now_unix(),
                platform: "huntr".into(),
                target: "repo".into(),
                title: "finding".into(),
                status: "submitted".into(),
                reward_usd: None,
                rejection_reason: None,
                url: None,
                notes: None,
            })
            .unwrap();

        // Invalid rejection reason is refused.
        let bad = l.update(
            &entry.id,
            &json!({"status": "rejected", "rejection_reason": "vibes"}),
        );
        assert!(bad.is_err());

        // Valid update lands and stats reflect it.
        let good = l
            .update(
                &entry.id,
                &json!({"status": "rejected", "rejection_reason": "duplicate"}),
            )
            .unwrap();
        assert_eq!(good.status, "rejected");
        let stats = l.stats();
        assert_eq!(stats["rejection_reasons"]["duplicate"], 1);
        assert_eq!(stats["rejected"], 1);
    }

    #[test]
    fn stats_acceptance_and_earnings() {
        let (ledger, _dir) = temp_ledger();
        let mut l = ledger.lock().unwrap();
        for (status, reward) in [("accepted", Some(1200.0)), ("rejected", None)] {
            let entry = l
                .record(LedgerEntry {
                    id: String::new(),
                    recorded_at: now_unix(),
                    platform: "gray_swan".into(),
                    target: "arena".into(),
                    title: "x".into(),
                    status: "submitted".into(),
                    reward_usd: None,
                    rejection_reason: None,
                    url: None,
                    notes: None,
                })
                .unwrap();
            let patch = json!({"status": status, "reward_usd": reward});
            l.update(&entry.id, &patch).unwrap();
        }
        let stats = l.stats();
        assert_eq!(stats["accepted"], 1);
        assert_eq!(stats["rejected"], 1);
        assert!((stats["acceptance_rate"].as_f64().unwrap() - 0.5).abs() < 1e-9);
        assert!((stats["earned_usd"].as_f64().unwrap() - 1200.0).abs() < 1e-9);
    }
}
