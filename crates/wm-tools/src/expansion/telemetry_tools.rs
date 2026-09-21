//! Edge-galaxy telemetry tools — typed records, hourly rollups, retention.
//!
//! Thread 4 (2026-09-13): the `telemetry` galaxy is evidence, not cognition
//! (excluded from default recall/dream/consolidation). These tools give the
//! producers a typed contract and the operators a retention path:
//!
//! - `telemetry.record` — validate + store one window/rollup record.
//! - `telemetry.rollup` — aggregate completed hours into `telemetry.rollup`
//!   memories (deterministic content, so re-runs deduplicate).
//! - `telemetry.prune`  — destructive retention: delete windows/rollups older
//!   than their horizons (pipeline requires `confirm: true`).
//! - `telemetry.retention` — read-only planner: per-tier counts/ages/eligible
//!   inventory under the same horizons as prune; never gated.
//!
//! Policy target (see `docs/EDGE_GALAXY_TELEMETRY.md`): ring 5 min / windows
//! 7 d / hourly rollups 90 d. This module implements the window + rollup
//! halves of that policy; the producer's local ring is Lakshmi's concern.

#![forbid(unsafe_code)]

use std::collections::BTreeMap;
use std::sync::Arc;

use async_trait::async_trait;
use chrono::{DateTime, Duration as ChronoDuration, Timelike, Utc};
use serde_json::{Value, json};
use wm_core::{Context, CoreError, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::Memory;
use wm_memory::MemoryStore;
use wm_memory::search::SearchEngine;

use super::common;

const TAG_WINDOW: &str = "window";
const TAG_ROLLUP: &str = "rollup";
const TAG_OBSERVATION: &str = "observation";
const TAG_FUNNEL: &str = "funnel";
const RECORD_KINDS: [&str; 4] = [
    "telemetry.window",
    "telemetry.rollup",
    "telemetry.observation",
    "telemetry.funnel",
];
pub(crate) const IMPORTANCE_CEILING: f32 = 0.40;
const SOURCE_TRUST: f32 = 0.7;

fn telemetry_effects(destructive: bool, writes: bool) -> EffectRow {
    EffectRow {
        reads: vec![Resource::Galaxy("telemetry".into())],
        writes: if writes {
            vec![Resource::Galaxy("telemetry".into())]
        } else {
            vec![]
        },
        destructive,
        ..Default::default()
    }
}

/// Validate a telemetry record shape. Returns the kind string.
pub(crate) fn validate_record(record: &Value) -> std::result::Result<&'static str, String> {
    let kind = record
        .get("kind")
        .and_then(Value::as_str)
        .ok_or_else(|| "record.kind is required".to_string())?;
    let kind = RECORD_KINDS
        .iter()
        .find(|k| **k == kind)
        .ok_or_else(|| format!("record.kind must be one of {RECORD_KINDS:?}, got '{kind}'"))?;
    record
        .get("ts")
        .and_then(Value::as_str)
        .ok_or_else(|| "record.ts (RFC3339) is required".to_string())?;
    if *kind == "telemetry.funnel" {
        // Local activation evidence: milestone identity plus bounded,
        // content-free attribution fields. No free-text field is accepted.
        let milestone = record
            .get("milestone")
            .and_then(Value::as_str)
            .filter(|milestone| !milestone.is_empty())
            .ok_or_else(|| {
                "record.milestone (non-empty string) is required for telemetry.funnel records"
                    .to_string()
            })?;
        if !super::funnel::is_known_milestone(milestone) {
            return Err(format!(
                "record.milestone '{milestone}' is not a known funnel milestone"
            ));
        }
        if let Some(channel) = record.get("channel") {
            let channel = channel.as_str().ok_or_else(|| {
                "record.channel (string) must be a site install channel".to_string()
            })?;
            if super::funnel::Channel::parse(channel).is_none() {
                return Err(format!(
                    "record.channel '{channel}' must be one of install_sh|binary|npm|docker|cargo|source|unknown"
                ));
            }
        }
        for field in ["version", "os", "arch"] {
            if record.get(field).is_some_and(|value| !value.is_string()) {
                return Err(format!("record.{field} (string) is required when present"));
            }
        }
        if record
            .get("day_offset")
            .is_some_and(|offset| offset.as_u64().is_none())
        {
            return Err(
                "record.day_offset (non-negative integer) is required when present".to_string(),
            );
        }
        return Ok(kind);
    }
    if *kind == "telemetry.observation" {
        // Policy decision records (step-0 observation ladder): identity and
        // transition fields are mandatory; harmony/dims do not apply.
        for field in ["policy_id", "metric", "state", "action"] {
            if record
                .get(field)
                .and_then(Value::as_str)
                .is_none_or(str::is_empty)
            {
                return Err(format!(
                    "record.{field} (non-empty string) is required for telemetry.observation records"
                ));
            }
        }
        if record.get("value").and_then(Value::as_f64).is_none() {
            return Err(
                "record.value (number) is required for telemetry.observation records".to_string(),
            );
        }
        return Ok(kind);
    }
    // Windows and rollups carry a harmony score; rollups aggregate it as
    // `{"harmony":{"avg":...}}`, windows as the scalar `harmony_score`.
    let harmony = record
        .get("harmony_score")
        .and_then(Value::as_f64)
        .or_else(|| {
            record
                .get("harmony")
                .and_then(|h| h.get("avg"))
                .and_then(Value::as_f64)
        })
        .ok_or_else(|| "record.harmony_score (0.0-1.0) is required".to_string())?;
    if !(0.0..=1.0).contains(&harmony) {
        return Err(format!(
            "record.harmony_score must be in 0.0-1.0, got {harmony}"
        ));
    }
    if !record.get("dims").is_some_and(Value::is_object) {
        return Err("record.dims (object) is required".to_string());
    }
    // Windows must carry the honesty field: a window without provenance notes
    // is a probe, and probes must not pollute trend lanes (learned live
    // 2026-09-13 when a typed probe flattened the dashboard dharma trend).
    if *kind == "telemetry.window" && !record.get("dim_notes").is_some_and(Value::is_object) {
        return Err(
            "record.dim_notes (object) is required for telemetry.window records".to_string(),
        );
    }
    Ok(kind)
}

/// Store a validated record in the telemetry galaxy. Returns (id, deduplicated).
///
/// Shared with the funnel emitter (`super::funnel`) so tags/class/ceiling
/// discipline stays centralized on the typed path.
pub(crate) fn store_record(
    store: &MemoryStore,
    search: Option<&SearchEngine>,
    record: &Value,
    kind: &str,
    source: &str,
) -> std::result::Result<(String, bool), String> {
    let content =
        serde_json::to_string(record).map_err(|e| format!("record serialization failed: {e}"))?;
    let mut memory = Memory::new(Galaxy::Telemetry, content);
    let mut tags: Vec<String> = record
        .get("tags")
        .and_then(Value::as_array)
        .map(|arr| {
            arr.iter()
                .filter_map(Value::as_str)
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default();
    for required in ["telemetry", "edge"] {
        if !tags.iter().any(|t| t == required) {
            tags.push(required.to_string());
        }
    }
    let kind_tag = match kind {
        "telemetry.window" => TAG_WINDOW,
        "telemetry.observation" => TAG_OBSERVATION,
        "telemetry.funnel" => TAG_FUNNEL,
        _ => TAG_ROLLUP,
    };
    if !tags.iter().any(|t| t == kind_tag) {
        tags.push(kind_tag.to_string());
    }
    memory.metadata.tags = tags;
    let importance = record
        .get("importance")
        .and_then(Value::as_f64)
        .map_or(0.3_f32, |v| v as f32);
    // Clamp rather than reject: the typed telemetry path is machine-fed, and
    // the contract is the class ceiling. A negative value would otherwise
    // make the record unreachable in importance-ordered browse.
    memory.metadata.importance = importance.clamp(0.0, IMPORTANCE_CEILING);
    memory.metadata.title = record
        .get("ts")
        .and_then(Value::as_str)
        .map(|ts| format!("telemetry {kind_tag} {ts}"));
    memory.metadata.source = source.to_string();
    memory.metadata.source_trust = SOURCE_TRUST;
    memory.metadata.class =
        wm_memory::typology::detect_class(&memory.content, &memory.metadata.tags)
            .or(Some(wm_memory::typology::MemoryClass::Telemetry));
    memory.metadata.tier = memory.metadata.class.map_or(
        wm_memory::memory::Tier::Working,
        wm_memory::typology::initial_tier,
    );

    let new_id = memory.metadata.id;
    let stored_id = store
        .put_dedup(Galaxy::Telemetry, &memory)
        .map_err(|e| format!("telemetry store failed: {e}"))?;
    let deduplicated = stored_id != new_id;
    if !deduplicated {
        common::index_memory(store, search, &memory);
    }
    Ok((stored_id.to_string(), deduplicated))
}

/// `telemetry.record` — validate and store one window/rollup record.
pub struct TelemetryRecordTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TelemetryRecordTool {
    /// Create the record tool.
    #[must_use]
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: telemetry_effects(false, true),
        }
    }
}

#[async_trait]
impl Tool for TelemetryRecordTool {
    fn name(&self) -> &str {
        "telemetry.record"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Record one telemetry window/rollup/observation/funnel record (schema wm-telemetry-v1) into the telemetry galaxy. Args: record (object with kind/ts/harmony_score/dims), source (optional trust label), importance (optional, capped 0.40). Deduplicates on identical content."
    }
    fn input_schema(&self) -> Value {
        common::schema(
            &json!({
                "record": {"type": "object", "description": "telemetry.window | telemetry.rollup | telemetry.observation | telemetry.funnel record (required)"},
                "source": common::str_prop("producer label (default 'agent')"),
                "importance": common::num_prop("0-1, capped to the telemetry class ceiling 0.40"),
            }),
            &["record"],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let record = if let Some(record) = args.get("record") {
            record.clone()
        } else if let Some(content) = args.get("content").and_then(Value::as_str) {
            serde_json::from_str(content)
                .map_err(|e| CoreError::InvalidArgs(format!("content is not JSON: {e}")))?
        } else {
            return Err(CoreError::InvalidArgs(
                "record (object) or content (JSON string) is required".into(),
            ));
        };
        let kind = validate_record(&record).map_err(CoreError::InvalidArgs)?;
        let mut record = record;
        if let Some(importance) = args.get("importance") {
            record["importance"] = importance.clone();
        }
        let source = args
            .get("source")
            .and_then(Value::as_str)
            .unwrap_or("agent");
        let (id, deduplicated) =
            store_record(&self.store, self.search.as_deref(), &record, kind, source)
                .map_err(CoreError::Internal)?;
        Ok(json!({
            "status": "success",
            "id": id,
            "galaxy": "telemetry",
            "kind": kind,
            "deduplicated": deduplicated,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

fn fnum(record: &Value, path: &[&str]) -> Option<f64> {
    let mut value = record;
    for key in path {
        value = value.get(*key)?;
    }
    value.as_f64()
}

fn round4(value: f64) -> f64 {
    (value * 10_000.0).round() / 10_000.0
}

/// Aggregate a set of window records into one hourly rollup record.
fn build_rollup(period_start: &str, period_end: &str, windows: &[Value]) -> Value {
    let mut dim_values: BTreeMap<String, Vec<f64>> = BTreeMap::new();
    let mut harmony: Vec<f64> = Vec::new();
    let mut guna = json!({"sattvic": 0, "rajasic": 0, "tamasic": 0});
    let mut topics: BTreeMap<String, u64> = BTreeMap::new();
    let mut event_count = 0_u64;
    for window in windows {
        if let Some(score) = fnum(window, &["harmony_score"]) {
            harmony.push(score);
        }
        if let Some(dims) = window.get("dims").and_then(Value::as_object) {
            for (name, score) in dims {
                if let Some(score) = score.as_f64() {
                    dim_values.entry(name.clone()).or_default().push(score);
                }
            }
        }
        if let Some(g) = window.get("guna").and_then(Value::as_object) {
            for key in ["sattvic", "rajasic", "tamasic"] {
                if let Some(v) = g.get(key).and_then(Value::as_u64) {
                    guna[key] = json!(guna[key].as_u64().unwrap_or(0) + v);
                }
            }
        }
        if let Some(events) = window.get("events").and_then(Value::as_array) {
            event_count += events.len() as u64;
            for event in events {
                if let Some(topic) = event.get("topic").and_then(Value::as_str) {
                    *topics.entry(topic.to_string()).or_default() += 1;
                }
            }
        }
    }
    let stats = |values: &[f64]| -> Value {
        if values.is_empty() {
            return json!({"avg": null, "min": null, "max": null});
        }
        let sum: f64 = values.iter().sum();
        json!({
            "avg": round4(sum / values.len() as f64),
            "min": round4(values.iter().copied().fold(f64::INFINITY, f64::min)),
            "max": round4(values.iter().copied().fold(f64::NEG_INFINITY, f64::max)),
        })
    };
    let dims: BTreeMap<String, Value> = dim_values
        .iter()
        .map(|(name, values)| (name.clone(), stats(values)))
        .collect();
    let harmony_stats = stats(&harmony);
    json!({
        "kind": "telemetry.rollup",
        "ts": period_end,
        "period_start": period_start,
        "period_end": period_end,
        "hours": 1,
        "samples": windows.len(),
        "dims": dims,
        "harmony": harmony_stats,
        "guna": guna,
        "events": {"count": event_count, "topics": topics},
        "source": "wm-rollup",
        "tags": ["telemetry", "edge", TAG_ROLLUP],
    })
}

fn period_bounds(ts: &str) -> Option<(String, String)> {
    let stamp = DateTime::parse_from_rfc3339(ts).ok()?.with_timezone(&Utc);
    let start = stamp.date_naive().and_hms_opt(stamp.hour(), 0, 0)?;
    let start = DateTime::<Utc>::from_naive_utc_and_offset(start, Utc);
    let end = start + ChronoDuration::hours(1);
    Some((
        start.to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
        end.to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
    ))
}

/// `telemetry.rollup` — aggregate completed hours into rollup memories.
pub struct TelemetryRollupTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TelemetryRollupTool {
    /// Create the rollup tool.
    #[must_use]
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: telemetry_effects(false, true),
        }
    }
}

#[async_trait]
impl Tool for TelemetryRollupTool {
    fn name(&self) -> &str {
        "telemetry.rollup"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Aggregate completed telemetry windows into hourly rollups (deterministic; re-runs deduplicate). Args: hours (scan horizon, default 24), include_current (default false — only completed hours), dry_run (default false)."
    }
    fn input_schema(&self) -> Value {
        common::schema(
            &json!({
                "hours": common::num_prop("how far back to scan (default 24)"),
                "include_current": common::bool_prop("include the in-progress hour (default false)"),
                "dry_run": common::bool_prop("report without writing (default false)"),
            }),
            &[],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let hours = args.get("hours").and_then(Value::as_f64).unwrap_or(24.0);
        let include_current = args
            .get("include_current")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let dry_run = args
            .get("dry_run")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let cutoff = Utc::now() - ChronoDuration::minutes((hours * 60.0) as i64);
        let current_period =
            period_bounds(&Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true))
                .map(|(start, _)| start);

        let memories = self
            .store
            .scan_all(Galaxy::Telemetry)
            .map_err(|e| CoreError::Internal(format!("telemetry scan failed: {e}")))?;
        let mut windows: BTreeMap<String, Vec<Value>> = BTreeMap::new();
        let mut skipped_current = 0_u64;
        let mut scanned = 0_u64;
        for memory in &memories {
            if !memory.metadata.tags.iter().any(|t| t == TAG_WINDOW) {
                continue;
            }
            let Ok(record) = serde_json::from_str::<Value>(&memory.content) else {
                continue;
            };
            let Some(ts) = record.get("ts").and_then(Value::as_str) else {
                continue;
            };
            let Some(stamp) = DateTime::parse_from_rfc3339(ts)
                .ok()
                .map(|s| s.with_timezone(&Utc))
            else {
                continue;
            };
            if stamp < cutoff {
                continue;
            }
            scanned += 1;
            let Some((start, _end)) = period_bounds(ts) else {
                continue;
            };
            if !include_current && current_period.as_deref() == Some(start.as_str()) {
                skipped_current += 1;
                continue;
            }
            windows.entry(start).or_default().push(record);
        }

        let mut written = 0_u64;
        let mut deduplicated = 0_u64;
        let mut first_period: Option<String> = None;
        let mut last_period: Option<String> = None;
        for (start, records) in &windows {
            let end = period_bounds(start).map_or_else(|| start.clone(), |(_, end)| end);
            let rollup = build_rollup(start, &end, records);
            first_period.get_or_insert_with(|| start.clone());
            last_period = Some(start.clone());
            if dry_run {
                continue;
            }
            let (_, dedup) = store_record(
                &self.store,
                self.search.as_deref(),
                &rollup,
                "telemetry.rollup",
                "wm-rollup",
            )
            .map_err(CoreError::Internal)?;
            if dedup {
                deduplicated += 1;
            } else {
                written += 1;
            }
        }
        Ok(json!({
            "status": "success",
            "dry_run": dry_run,
            "scanned": scanned,
            "windows": scanned,
            "periods": windows.len(),
            "written": written,
            "deduplicated": deduplicated,
            "skipped_current": skipped_current,
            "first_period": first_period,
            "last_period": last_period,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `telemetry.prune` — destructive retention for windows and rollups.
pub struct TelemetryPruneTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TelemetryPruneTool {
    /// Create the prune tool.
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: telemetry_effects(true, true),
        }
    }
}

#[async_trait]
impl Tool for TelemetryPruneTool {
    fn name(&self) -> &str {
        "telemetry.prune"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Destructive retention: delete telemetry windows/rollups older than their horizons (defaults 7 d windows / 90 d rollups). Args: windows_older_than_days, rollups_older_than_days, dry_run (default true), limit (0 = all). Requires confirm: true when dry_run is false."
    }
    fn input_schema(&self) -> Value {
        common::schema(
            &json!({
                "windows_older_than_days": common::num_prop("window horizon in days (default 7)"),
                "rollups_older_than_days": common::num_prop("rollup horizon in days (default 90)"),
                "dry_run": common::bool_prop("report without deleting (default true)"),
                "limit": common::num_prop("max records to inspect, 0 = all"),
            }),
            &[],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let window_days = args
            .get("windows_older_than_days")
            .and_then(Value::as_f64)
            .unwrap_or(7.0);
        let rollup_days = args
            .get("rollups_older_than_days")
            .and_then(Value::as_f64)
            .unwrap_or(90.0);
        let dry_run = args.get("dry_run").and_then(Value::as_bool).unwrap_or(true);
        let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(0) as usize;

        let memories = self
            .store
            .scan_all(Galaxy::Telemetry)
            .map_err(|e| CoreError::Internal(format!("telemetry scan failed: {e}")))?;
        let now = Utc::now();
        let mut scanned = 0_u64;
        let mut candidates = 0_u64;
        let mut deleted = 0_u64;
        let mut window_candidates = 0_u64;
        let mut rollup_candidates = 0_u64;
        let mut errors: Vec<String> = Vec::new();
        for memory in &memories {
            if limit > 0 && scanned as usize >= limit {
                break;
            }
            scanned += 1;
            let is_window = memory.metadata.tags.iter().any(|t| t == TAG_WINDOW);
            let is_rollup = memory.metadata.tags.iter().any(|t| t == TAG_ROLLUP);
            let horizon = if is_window {
                window_days
            } else if is_rollup {
                rollup_days
            } else {
                continue;
            };
            let age = now.signed_duration_since(memory.metadata.created_at);
            if age < ChronoDuration::minutes((horizon * 1440.0) as i64) {
                continue;
            }
            candidates += 1;
            if is_window {
                window_candidates += 1;
            } else {
                rollup_candidates += 1;
            }
            if dry_run {
                continue;
            }
            match self.store.delete(Galaxy::Telemetry, memory.metadata.id) {
                Ok(true) => deleted += 1,
                Ok(false) => {}
                Err(e) => errors.push(format!("{}: {e}", memory.metadata.id)),
            }
        }
        Ok(json!({
            "status": "success",
            "dry_run": dry_run,
            "scanned": scanned,
            "candidates": candidates,
            "deleted": deleted,
            "by_kind": {"window": window_candidates, "rollup": rollup_candidates},
            "horizons": {"windows_days": window_days, "rollups_days": rollup_days},
            "errors": errors,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Per-tier retention inventory. The eligibility rule mirrors `telemetry.prune`
/// exactly (age by `created_at`, eligible at `>= horizon`), so a planner run
/// reporting `prune_due: true` will have work when prune runs.
fn retention_inventory(
    store: &MemoryStore,
    window_days: f64,
    rollup_days: f64,
) -> std::result::Result<(Value, bool), String> {
    #[derive(Default)]
    struct Tier {
        count: u64,
        eligible: u64,
        bytes: u64,
        oldest: Option<DateTime<Utc>>,
        newest: Option<DateTime<Utc>>,
        oldest_eligible: Option<DateTime<Utc>>,
        oldest_kept: Option<DateTime<Utc>>,
    }

    fn stamp(dt: DateTime<Utc>) -> String {
        dt.to_rfc3339_opts(chrono::SecondsFormat::Secs, true)
    }

    impl Tier {
        fn observe(&mut self, created: DateTime<Utc>, eligible_now: bool, bytes: u64) {
            self.count += 1;
            self.bytes += bytes;
            self.oldest = Some(self.oldest.map_or(created, |o| o.min(created)));
            self.newest = Some(self.newest.map_or(created, |n| n.max(created)));
            if eligible_now {
                self.eligible += 1;
                self.oldest_eligible =
                    Some(self.oldest_eligible.map_or(created, |o| o.min(created)));
            } else {
                self.oldest_kept = Some(self.oldest_kept.map_or(created, |o| o.min(created)));
            }
        }

        fn ages(&self) -> Value {
            json!({
                "count": self.count,
                "bytes": self.bytes,
                "oldest_created": self.oldest.map(stamp),
                "newest_created": self.newest.map(stamp),
            })
        }

        fn json(&self, horizon_days: f64) -> Value {
            let mut value = self.ages();
            value["eligible"] = json!(self.eligible);
            value["oldest_eligible"] = json!(self.oldest_eligible.map(stamp));
            value["next_eligible_since"] = json!(
                self.oldest_kept
                    .map(|d| stamp(d + ChronoDuration::minutes((horizon_days * 1440.0) as i64)))
            );
            value
        }
    }

    let memories = store
        .scan_all(Galaxy::Telemetry)
        .map_err(|e| format!("telemetry scan failed: {e}"))?;
    let now = Utc::now();
    let mut windows = Tier::default();
    let mut rollups = Tier::default();
    let mut observations = Tier::default();
    let mut funnel = Tier::default();
    let mut unmanaged = Tier::default();
    for memory in &memories {
        let created = memory.metadata.created_at;
        let bytes = memory.content.len() as u64;
        let tags = &memory.metadata.tags;
        if tags.iter().any(|t| t == TAG_WINDOW) {
            let eligible = now.signed_duration_since(created)
                >= ChronoDuration::minutes((window_days * 1440.0) as i64);
            windows.observe(created, eligible, bytes);
        } else if tags.iter().any(|t| t == TAG_ROLLUP) {
            let eligible = now.signed_duration_since(created)
                >= ChronoDuration::minutes((rollup_days * 1440.0) as i64);
            rollups.observe(created, eligible, bytes);
        } else if tags.iter().any(|t| t == TAG_OBSERVATION) {
            observations.observe(created, false, bytes);
        } else if tags.iter().any(|t| t == TAG_FUNNEL) {
            funnel.observe(created, false, bytes);
        } else {
            unmanaged.observe(created, false, bytes);
        }
    }

    let mut observation_json = observations.ages();
    observation_json["managed"] = json!(false);
    observation_json["note"] = json!(
        "policy decision records are governance evidence; telemetry.prune does not delete them"
    );
    let mut funnel_json = funnel.ages();
    funnel_json["managed"] = json!(false);
    funnel_json["note"] =
        json!("store-lifetime evidence; telemetry.prune does not delete; reset explicitly");
    let mut unmanaged_json = unmanaged.ages();
    unmanaged_json["note"] = json!("telemetry rows without a window/rollup/observation/funnel tag");

    let prune_due = windows.eligible + rollups.eligible > 0;
    let inventory = json!({
        "windows": windows.json(window_days),
        "rollups": rollups.json(rollup_days),
        "observations": observation_json,
        "funnel": funnel_json,
        "unmanaged": unmanaged_json,
    });
    Ok((inventory, prune_due))
}

/// `telemetry.retention` — read-only retention planner.
pub struct TelemetryRetentionTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TelemetryRetentionTool {
    /// Create the retention planner.
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: telemetry_effects(false, false),
        }
    }
}

#[async_trait]
impl Tool for TelemetryRetentionTool {
    fn name(&self) -> &str {
        "telemetry.retention"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Read-only retention planner: per-tier counts/ages/eligibility for telemetry windows (7 d) and rollups (90 d) under the exact horizons telemetry.prune uses, plus managed=false observation inventory. No confirm and no dharma gate — safe to run any time; act with telemetry.prune."
    }
    fn input_schema(&self) -> Value {
        common::schema(
            &json!({
                "windows_older_than_days": common::num_prop("window horizon to project (default 7)"),
                "rollups_older_than_days": common::num_prop("rollup horizon to project (default 90)"),
            }),
            &[],
        )
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let window_days = args
            .get("windows_older_than_days")
            .and_then(Value::as_f64)
            .unwrap_or(7.0);
        let rollup_days = args
            .get("rollups_older_than_days")
            .and_then(Value::as_f64)
            .unwrap_or(90.0);
        let (inventory, prune_due) = retention_inventory(&self.store, window_days, rollup_days)
            .map_err(CoreError::Internal)?;
        Ok(json!({
            "status": "success",
            "read_only": true,
            "generated_at": Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
            "basis": "record created_at (identical to telemetry.prune)",
            "horizons": {"windows_days": window_days, "rollups_days": rollup_days},
            "inventory": inventory,
            "prune_due": prune_due,
            "advice": if prune_due {
                "eligible records exist — run telemetry.prune with dry_run:false + confirm:true"
            } else {
                "nothing eligible — no prune needed"
            },
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the telemetry surface (4 tools).
#[must_use]
pub fn register_telemetry(
    registry: &wm_dispatch::ToolRegistry,
    store: &Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(TelemetryRecordTool::new(
            Arc::clone(store),
            search.clone(),
        )))
        .register(Arc::new(TelemetryRollupTool::new(
            Arc::clone(store),
            search,
        )))
        .register(Arc::new(TelemetryPruneTool::new(Arc::clone(store))))
        .register(Arc::new(TelemetryRetentionTool::new(Arc::clone(store))))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn open_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        (tmp, store)
    }

    fn window_record(ts: &str, harmony: f64) -> Value {
        json!({
            "kind": "telemetry.window",
            "ts": ts,
            "window_seconds": 60,
            "source": "laksmi",
            "tags": ["telemetry", "edge", "laksmi", "window"],
            "harmony_score": harmony,
            "dims": {"fairness": 0.5, "responsiveness": 0.8},
            "dim_notes": {"fairness": "test"},
            "guna": {"sattvic": 1, "rajasic": 0, "tamasic": 2},
            "top": [],
            "events": [{"topic": "os.telemetry.energy", "value": 0.5, "threshold": 0.9}],
            "karma": {"total": 100.0, "delta": 0.0},
            "dharma": {"total": 1, "blocked": 0, "delta_total": 0, "delta_blocked": 0},
        })
    }

    #[tokio::test]
    async fn record_validates_and_stores() {
        let (_tmp, store) = open_store();
        let tool = TelemetryRecordTool::new(Arc::clone(&store), None);
        let out = tool
            .call(
                &mut Context::default(),
                json!({"record": window_record("2026-09-13T10:00:00+00:00", 0.6)}),
            )
            .await
            .unwrap();
        assert_eq!(out["status"], "success");
        assert_eq!(out["kind"], "telemetry.window");
        assert_eq!(out["deduplicated"], false);
        assert_eq!(store.count(Galaxy::Telemetry).unwrap(), 1);

        // Identical content deduplicates.
        let again = tool
            .call(
                &mut Context::default(),
                json!({"record": window_record("2026-09-13T10:00:00+00:00", 0.6)}),
            )
            .await
            .unwrap();
        assert_eq!(again["deduplicated"], true);
        assert_eq!(store.count(Galaxy::Telemetry).unwrap(), 1);

        // Invalid shapes are loud.
        let bad = tool
            .call(
                &mut Context::default(),
                json!({"record": {"kind": "telemetry.window", "ts": "x"}}),
            )
            .await;
        assert!(bad.is_err(), "missing harmony_score/dims must error");

        // A window without provenance notes is a probe, not evidence.
        let mut probe = window_record("2026-09-13T11:00:00+00:00", 0.5);
        probe.as_object_mut().unwrap().remove("dim_notes");
        let probe_reply = tool
            .call(&mut Context::default(), json!({"record": probe}))
            .await;
        assert!(probe_reply.is_err(), "windows require dim_notes");
    }

    #[tokio::test]
    async fn record_accepts_policy_observations_and_typed_rollups() {
        let (_tmp, store) = open_store();
        let tool = TelemetryRecordTool::new(Arc::clone(&store), None);
        let obs = json!({
            "kind": "telemetry.observation",
            "ts": "2026-09-13T12:00:00+00:00",
            "policy_id": "energy.over_budget.v1",
            "metric": "energy",
            "state": "observing",
            "action": "observe",
            "value": 0.33,
            "enter": 0.9,
            "exit": 0.97,
            "dwell_windows": 1,
            "tags": ["telemetry", "edge", "observation", "policy"],
        });
        let out = tool
            .call(&mut Context::default(), json!({"record": obs}))
            .await
            .unwrap();
        assert_eq!(out["kind"], "telemetry.observation");
        assert_eq!(store.count(Galaxy::Telemetry).unwrap(), 1);

        // Identity fields are mandatory for observations.
        let bad = json!({"kind": "telemetry.observation", "ts": "x", "metric": "energy"});
        assert!(
            tool.call(&mut Context::default(), json!({"record": bad}))
                .await
                .is_err()
        );

        // Rollups validate via harmony.avg (the typed path now matches what
        // the rollup builder actually produces).
        let rollup = json!({
            "kind": "telemetry.rollup",
            "ts": "2026-09-13T12:00:00+00:00",
            "harmony": {"avg": 0.6},
            "dims": {"fairness": {"avg": 0.5}},
        });
        let out = tool
            .call(&mut Context::default(), json!({"record": rollup}))
            .await
            .unwrap();
        assert_eq!(out["kind"], "telemetry.rollup");
        assert_eq!(store.count(Galaxy::Telemetry).unwrap(), 2);

        // Funnel records validate on milestone identity, not harmony.
        let funnel = json!({
            "kind": "telemetry.funnel",
            "ts": "2026-09-18T00:00:00+00:00",
            "milestone": "active_d2",
            "channel": "install_sh",
            "version": "9.1.9",
            "os": "linux",
            "arch": "x86_64",
            "day_offset": 2,
        });
        let out = tool
            .call(&mut Context::default(), json!({"record": funnel}))
            .await
            .unwrap();
        assert_eq!(out["kind"], "telemetry.funnel");
        assert_eq!(store.count(Galaxy::Telemetry).unwrap(), 3);
        let funnel_tags = store
            .scan_all(Galaxy::Telemetry)
            .unwrap()
            .into_iter()
            .find(|m| m.metadata.tags.iter().any(|t| t == TAG_FUNNEL))
            .expect("funnel tag");
        assert!(funnel_tags.metadata.importance <= IMPORTANCE_CEILING);

        // Unknown milestones and channels are loud.
        let bad_milestone = json!({
            "kind": "telemetry.funnel",
            "ts": "2026-09-18T00:00:00+00:00",
            "milestone": "activation",
        });
        assert!(
            tool.call(&mut Context::default(), json!({"record": bad_milestone}))
                .await
                .is_err()
        );
        let bad_channel = json!({
            "kind": "telemetry.funnel",
            "ts": "2026-09-18T00:00:00+00:00",
            "milestone": "first_launch",
            "channel": "email",
        });
        assert!(
            tool.call(&mut Context::default(), json!({"record": bad_channel}))
                .await
                .is_err()
        );
    }

    #[tokio::test]
    async fn rollup_aggregates_completed_hours_idempotently() {
        let (_tmp, store) = open_store();
        let current = Utc::now();
        let last_hour = (current - ChronoDuration::hours(1))
            .with_minute(30)
            .unwrap()
            .with_second(0)
            .unwrap();
        let prev = last_hour - ChronoDuration::hours(2);
        let ts_a = last_hour.to_rfc3339_opts(chrono::SecondsFormat::Secs, true);
        let ts_b = (last_hour + ChronoDuration::minutes(5))
            .to_rfc3339_opts(chrono::SecondsFormat::Secs, true);
        let ts_c = prev.to_rfc3339_opts(chrono::SecondsFormat::Secs, true);
        for (ts, harmony) in [(&ts_a, 0.4), (&ts_b, 0.6), (&ts_c, 0.9)] {
            let record = window_record(ts, harmony);
            let mem = Memory::new(Galaxy::Telemetry, serde_json::to_string(&record).unwrap());
            let mut mem = mem;
            mem.metadata.tags = vec!["telemetry".into(), "edge".into(), "window".into()];
            store.put(Galaxy::Telemetry, &mem).unwrap();
        }
        let tool = TelemetryRollupTool::new(Arc::clone(&store), None);
        let out = tool.call(&mut Context::default(), json!({})).await.unwrap();
        assert_eq!(out["periods"], 2);
        assert_eq!(out["written"], 2);
        let out2 = tool.call(&mut Context::default(), json!({})).await.unwrap();
        assert_eq!(out2["deduplicated"], 2, "re-run is idempotent");
        let rollups: Vec<_> = store
            .scan_all(Galaxy::Telemetry)
            .unwrap()
            .into_iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == TAG_ROLLUP))
            .collect();
        assert_eq!(rollups.len(), 2);
        let records: Vec<Value> = rollups
            .iter()
            .map(|m| serde_json::from_str(&m.content).unwrap())
            .collect();
        assert!(records.iter().all(|r| r["kind"] == "telemetry.rollup"));
        let total_events: u64 = records
            .iter()
            .map(|r| r["events"]["count"].as_u64().unwrap_or(0))
            .sum();
        assert_eq!(total_events, 3);
        let samples: Vec<u64> = records
            .iter()
            .map(|r| r["samples"].as_u64().unwrap_or(0))
            .collect();
        assert!(
            samples.contains(&2) && samples.contains(&1),
            "got {samples:?}"
        );
    }

    #[tokio::test]
    async fn prune_respects_horizons_and_dry_run() {
        let (_tmp, store) = open_store();
        let old = Utc::now() - ChronoDuration::days(10);
        let ancient = Utc::now() - ChronoDuration::days(100);
        let recent = Utc::now() - ChronoDuration::hours(1);
        for (tag, created) in [
            ("window", old),
            ("window", recent),
            ("rollup", ancient),
            ("rollup", recent),
        ] {
            let mut mem = Memory::new(Galaxy::Telemetry, format!("{{\"ts\":\"{created}\"}}"));
            mem.metadata.tags = vec!["telemetry".into(), tag.into()];
            mem.metadata.created_at = created;
            store.put(Galaxy::Telemetry, &mem).unwrap();
        }
        let tool = TelemetryPruneTool::new(Arc::clone(&store));
        let dry = tool
            .call(&mut Context::default(), json!({"dry_run": true}))
            .await
            .unwrap();
        assert_eq!(dry["dry_run"], true);
        assert_eq!(dry["candidates"], 2, "10d window + 100d rollup");
        assert_eq!(dry["deleted"], 0);
        assert_eq!(store.count(Galaxy::Telemetry).unwrap(), 4);

        let wet = tool
            .call(&mut Context::default(), json!({"dry_run": false}))
            .await
            .unwrap();
        assert_eq!(wet["deleted"], 2);
        assert_eq!(wet["by_kind"]["window"], 1);
        assert_eq!(wet["by_kind"]["rollup"], 1);
        assert_eq!(store.count(Galaxy::Telemetry).unwrap(), 2);
    }

    #[tokio::test]
    async fn retention_planner_reports_tiers_read_only() {
        let (_tmp, store) = open_store();
        let now = Utc::now();
        for (tag, created) in [
            ("window", now - ChronoDuration::days(10)),
            ("window", now - ChronoDuration::hours(1)),
            ("rollup", now - ChronoDuration::days(100)),
            ("rollup", now - ChronoDuration::hours(2)),
            ("observation", now - ChronoDuration::days(1)),
            ("funnel", now - ChronoDuration::days(400)),
            ("", now - ChronoDuration::days(30)),
        ] {
            let mut mem = Memory::new(Galaxy::Telemetry, format!("{{\"ts\":\"{created}\"}}"));
            mem.metadata.tags = if tag.is_empty() {
                vec!["telemetry".into()]
            } else {
                vec!["telemetry".into(), tag.into()]
            };
            mem.metadata.created_at = created;
            store.put(Galaxy::Telemetry, &mem).unwrap();
        }

        let tool = TelemetryRetentionTool::new(Arc::clone(&store));
        let out = tool.call(&mut Context::default(), json!({})).await.unwrap();
        assert_eq!(out["status"], "success");
        assert_eq!(out["read_only"], true);
        assert_eq!(out["prune_due"], true);
        assert_eq!(out["inventory"]["windows"]["count"], 2);
        assert_eq!(out["inventory"]["windows"]["eligible"], 1);
        assert_eq!(out["inventory"]["rollups"]["count"], 2);
        assert_eq!(out["inventory"]["rollups"]["eligible"], 1);
        assert_eq!(out["inventory"]["observations"]["count"], 1);
        assert_eq!(out["inventory"]["observations"]["managed"], false);
        assert_eq!(
            out["inventory"]["funnel"]["count"], 1,
            "funnel records are inventoried as a tier"
        );
        assert!(
            out["inventory"]["funnel"]["eligible"].is_null(),
            "funnel records are store-lifetime evidence — never prune-eligible"
        );
        assert_eq!(out["inventory"]["funnel"]["managed"], false);
        assert_eq!(out["inventory"]["unmanaged"]["count"], 1);
        assert!(
            out["inventory"]["windows"]["next_eligible_since"].is_string(),
            "a kept window must project its next eligibility"
        );
        assert!(out["inventory"]["windows"]["bytes"].as_u64().unwrap() > 0);
        assert_eq!(
            store.count(Galaxy::Telemetry).unwrap(),
            7,
            "the planner is read-only"
        );

        // Wider horizons project no work, without touching the store.
        let calm = tool
            .call(
                &mut Context::default(),
                json!({"windows_older_than_days": 365, "rollups_older_than_days": 3650}),
            )
            .await
            .unwrap();
        assert_eq!(calm["prune_due"], false);
        assert_eq!(store.count(Galaxy::Telemetry).unwrap(), 7);

        // And a wet prune executes exactly what the planner predicted —
        // windows/rollups only, never the funnel evidence.
        let prune = TelemetryPruneTool::new(Arc::clone(&store));
        let wet = prune
            .call(&mut Context::default(), json!({"dry_run": false}))
            .await
            .unwrap();
        assert_eq!(wet["deleted"], 2);
        assert_eq!(store.count(Galaxy::Telemetry).unwrap(), 5);
        assert_eq!(
            store
                .scan_all(Galaxy::Telemetry)
                .unwrap()
                .iter()
                .filter(|m| m.metadata.tags.iter().any(|t| t == TAG_FUNNEL))
                .count(),
            1,
            "prune must leave funnel records untouched"
        );
    }
}
