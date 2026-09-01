//! Session tools — record, replay, continuity, handoff (v26 parity).
//!
//! Port of the v26 session recorder / handoff surface (the last Phase-1
//! gap): turns are recorded chronologically into the Sessions galaxy,
//! replayed in full/selective/progressive modes, summarized across
//! sessions for continuity, and packaged for handoff to another device.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use chrono::{DateTime, NaiveDate, TimeZone, Utc};
use serde_json::{Value, json};
use std::fmt::Write as _;
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore};

/// Parse a time-bound argument: epoch seconds (number) or RFC 3339 /
/// `YYYY-MM-DD` (string; date-only means start of day for `since`, end of
/// day for `until`).
fn parse_time_bound(v: &Value, end_of_day: bool) -> Option<DateTime<Utc>> {
    if let Some(secs) = v
        .as_i64()
        .or_else(|| v.as_u64().and_then(|u| i64::try_from(u).ok()))
    {
        return Utc.timestamp_opt(secs, 0).single();
    }
    let s = v.as_str()?;
    if let Ok(dt) = DateTime::parse_from_rfc3339(s) {
        return Some(dt.with_timezone(&Utc));
    }
    let day = NaiveDate::parse_from_str(s, "%Y-%m-%d").ok()?;
    let naive = if end_of_day {
        day.and_hms_opt(23, 59, 59)?
    } else {
        day.and_hms_opt(0, 0, 0)?
    };
    Some(naive.and_utc())
}

/// Apply `since`/`until` time-range filters over loaded turns by their
/// memory creation time. Invalid bounds are a caller error, not silence.
fn filter_by_time(
    turns: Vec<(Memory, Value)>,
    args: &Value,
) -> wm_core::Result<Vec<(Memory, Value)>> {
    let since = match args.get("since") {
        Some(v) if !v.is_null() => Some(parse_time_bound(v, false).ok_or_else(|| {
            wm_core::CoreError::InvalidArgs(
                "invalid 'since' — use epoch seconds, RFC 3339, or YYYY-MM-DD".into(),
            )
        })?),
        _ => None,
    };
    let until = match args.get("until") {
        Some(v) if !v.is_null() => Some(parse_time_bound(v, true).ok_or_else(|| {
            wm_core::CoreError::InvalidArgs(
                "invalid 'until' — use epoch seconds, RFC 3339, or YYYY-MM-DD".into(),
            )
        })?),
        _ => None,
    };
    Ok(turns
        .into_iter()
        .filter(|(m, _)| {
            since.is_none_or(|t| m.metadata.created_at >= t)
                && until.is_none_or(|t| m.metadata.created_at <= t)
        })
        .collect())
}

fn turn_json(mem: &Memory) -> Option<Value> {
    let v: Value = serde_json::from_str(&mem.content).ok()?;
    if v.get("type").and_then(Value::as_str) == Some("session_turn") {
        Some(v)
    } else {
        None
    }
}

/// Load turns for a session (or all sessions).
///
/// Turns tagged `superseded-by:<id>` are excluded unless
/// `include_superseded` — supersession is the amend mechanism for evolving
/// stories, and consumers want the current story by default.
fn load_turns(
    store: &MemoryStore,
    session_id: Option<&str>,
    limit: usize,
    include_superseded: bool,
) -> wm_core::Result<Vec<(Memory, Value)>> {
    let memories = store.scan_all(Galaxy::Sessions)?;
    let mut turns: Vec<(Memory, Value)> = memories
        .iter()
        .filter(|m| {
            include_superseded
                || !m
                    .metadata
                    .tags
                    .iter()
                    .any(|t| t.starts_with("superseded-by:"))
        })
        .filter_map(|m| turn_json(m).map(|v| (m.clone(), v)))
        .filter(|(_, v)| {
            session_id.is_none_or(|sid| v.get("session_id").and_then(Value::as_str) == Some(sid))
        })
        .collect();
    turns.sort_by_key(|(_, v)| {
        (
            v.get("sequence").and_then(Value::as_u64).unwrap_or(0),
            v.get("timestamp").and_then(Value::as_i64).unwrap_or(0),
        )
    });
    turns.truncate(limit);
    Ok(turns)
}

fn format_turn(v: &Value, full: bool) -> Value {
    let role = v.get("role").and_then(Value::as_str).unwrap_or("?");
    let content = v.get("content").and_then(Value::as_str).unwrap_or("");
    if full {
        json!({
            "session_id": v.get("session_id"),
            "sequence": v.get("sequence"),
            "role": role,
            "turn_type": v.get("turn_type"),
            "importance": v.get("importance"),
            "content": content,
        })
    } else {
        json!({
            "sequence": v.get("sequence"),
            "role": role,
            "turn_type": v.get("turn_type"),
            "preview": content.chars().take(120).collect::<String>(),
        })
    }
}

/// `session.record` — record a conversation turn as persistent session memory.
pub struct SessionRecordTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionRecordTool {
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("sessions".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for SessionRecordTool {
    fn name(&self) -> &str {
        "session.record"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "content": super::common::str_prop("Turn content"),
                "role": super::common::str_prop("user | ai (default user)"),
                "turn_type": super::common::str_prop("message, decision, breakthrough, question, answer, code_change, error, summary, context"),
                "importance": super::common::num_prop("0-1 importance (default 0.5)"),
                "session_id": super::common::str_prop("Target session (default: most recent session)"),
                "supersedes": super::common::str_prop("Memory id of an earlier turn this record corrects/replaces (amend-with-supersede)"),
            }),
            &["content"],
        )
    }
    fn description(&self) -> &str {
        "Record a conversation turn as persistent session memory. Args: content (required), role (user|ai, default user), turn_type (default message), importance (0-1, default 0.5), session_id (optional — defaults to the most recent session), supersedes (optional turn memory-id — marks the old turn superseded so replay/continuity/digest use the new record)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let role = args.get("role").and_then(Value::as_str).unwrap_or("user");
        if !matches!(role, "user" | "ai") {
            return Err(wm_core::CoreError::InvalidArgs(
                "role must be 'user' or 'ai'".into(),
            ));
        }
        let content = args
            .get("content")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("content is required".into()))?;
        let turn_type = args
            .get("turn_type")
            .and_then(Value::as_str)
            .unwrap_or("message");
        let importance = args
            .get("importance")
            .and_then(Value::as_f64)
            .unwrap_or(0.5)
            .clamp(0.0, 1.0);
        let session_id = args.get("session_id").and_then(Value::as_str);

        // Resolve the session: explicit id, or the most recent session_start.
        // Resolution MUST use `created_at`, not iteration position: LMDB scan
        // order is key (UUID) order, which is random for v4 UUIDs — picking
        // positionally (`next_back`) silently misfiles turns into an
        // arbitrary session once more than one start exists.
        let session_id: String = if let Some(sid) = session_id {
            sid.to_string()
        } else {
            self.store
                .scan_all(Galaxy::Sessions)?
                .iter()
                .filter(|m| m.metadata.tags.contains(&"start".to_string()))
                .max_by_key(|m| m.metadata.created_at)
                .map(|m| m.metadata.id.to_string())
                .ok_or_else(|| {
                    wm_core::CoreError::Tool("no session found — run session.start first".into())
                })?
        };

        // Sequence = existing turns for this session + 1 (superseded turns
        // still count — the log position is history, visibility is separate).
        let sequence = load_turns(&self.store, Some(&session_id), 10_000, true)?.len() as u64 + 1;

        let mut mem = Memory::new(
            Galaxy::Sessions,
            json!({
                "type": "session_turn",
                "session_id": session_id,
                "sequence": sequence,
                "role": role,
                "turn_type": turn_type,
                "importance": importance,
                "content": content,
                "timestamp": wm_core::time::now_unix_millis(),
            })
            .to_string(),
        );
        mem.metadata.tags = vec![
            "session".into(),
            "turn".into(),
            role.into(),
            turn_type.into(),
            format!("session:{session_id}"),
        ];
        // Provenance: the turn's role IS the authorship claim. An ai-role
        // turn is agent-written and must not claim user provenance — the
        // sessions-galaxy archaeology finding (2026-08-29) was that every
        // turn stamped user/1.0 because Memory::new defaulted there. Trust
        // classes per the retrieval-trust semantics: user 1.0, agent 0.7
        // (tool-ingested neutral).
        let (source, trust): (&str, f32) = if role == "user" {
            ("user", 1.0)
        } else {
            ("agent", 0.7)
        };
        mem.metadata.source = source.to_string();
        mem.metadata.source_trust = trust;

        // Amend-with-supersede (P2): mark the corrected turn so default
        // retrieval uses the new record. History stays intact — the old turn
        // remains queryable via include_superseded.
        if let Some(old_id_str) = args.get("supersedes").and_then(Value::as_str) {
            let old_id = uuid::Uuid::parse_str(old_id_str).map_err(|e| {
                wm_core::CoreError::InvalidArgs(format!("invalid 'supersedes' id: {e}"))
            })?;
            let mut old = self.store.get(Galaxy::Sessions, old_id)?.ok_or_else(|| {
                wm_core::CoreError::NotFound(format!("superseded turn {old_id} not found"))
            })?;
            old.metadata
                .tags
                .push(format!("superseded-by:{}", mem.metadata.id));
            self.store.put(Galaxy::Sessions, &old)?;
            mem.metadata.tags.push(format!("supersedes:{old_id}"));
        }

        mem.metadata.importance = importance as f32;
        self.store.put(Galaxy::Sessions, &mem)?;
        Ok(json!({
            "status": "success",
            "session_id": session_id,
            "sequence": sequence,
            "memory_id": mem.metadata.id.to_string(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.replay` — replay session turns (full, selective, progressive).
pub struct SessionReplayTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionReplayTool {
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sessions".into())]),
        }
    }
}

#[async_trait]
impl Tool for SessionReplayTool {
    fn name(&self) -> &str {
        "session.replay"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "mode": super::common::str_prop("full | selective | progressive (default full)"),
                "session_id": super::common::str_prop("Target session (default: most recent)"),
                "n": super::common::int_prop("Maximum turns (default 50)"),
                "since": super::common::str_prop("Time-range floor: epoch seconds, RFC 3339, or YYYY-MM-DD"),
                "until": super::common::str_prop("Time-range ceiling: epoch seconds, RFC 3339, or YYYY-MM-DD"),
                "include_superseded": {
                    "type": "boolean",
                    "description": "Also return turns replaced via supersedes (default false)."
                },
                "turn_types": super::common::str_array_prop("Selective mode: turn types to keep"),
                "min_importance": super::common::num_prop("Selective mode floor (default 0.7)"),
                "token_budget": super::common::int_prop("Progressive mode token budget (default 2000)"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Replay session turns. Args: mode (full|selective|progressive, default full), session_id (optional), n (default 50), since/until (epoch seconds | RFC 3339 | YYYY-MM-DD — applies to all modes), include_superseded (default false), turn_types (list, for selective), min_importance (0-1, default 0.7, for selective), token_budget (default 2000, for progressive)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let mode = args.get("mode").and_then(Value::as_str).unwrap_or("full");
        let session_id = args.get("session_id").and_then(Value::as_str);
        let n = args.get("n").and_then(Value::as_u64).unwrap_or(50) as usize;
        let include_superseded = args
            .get("include_superseded")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let turns = filter_by_time(
            load_turns(&self.store, session_id, 10_000, include_superseded)?,
            &args,
        )?;

        // An explicitly requested session that has no turns is an error, not
        // an empty success — silent emptiness hides typos and stale IDs.
        if session_id.is_some_and(|sid| !sid.is_empty()) && turns.is_empty() {
            return Err(wm_core::CoreError::InvalidArgs(format!(
                "no session found with id {session_id:?}"
            )));
        }

        let selected: Vec<(Memory, Value)> = match mode {
            "selective" => {
                let min_importance = args
                    .get("min_importance")
                    .and_then(Value::as_f64)
                    .unwrap_or(0.7);
                let turn_types: Vec<String> = args
                    .get("turn_types")
                    .and_then(Value::as_array)
                    .map_or_else(
                        || vec!["decision".into(), "breakthrough".into(), "answer".into()],
                        |a| {
                            a.iter()
                                .filter_map(Value::as_str)
                                .map(str::to_string)
                                .collect()
                        },
                    );
                turns
                    .into_iter()
                    .filter(|(_, v)| {
                        v.get("importance").and_then(Value::as_f64).unwrap_or(0.0) >= min_importance
                            && v.get("turn_type")
                                .and_then(Value::as_str)
                                .is_some_and(|t| turn_types.contains(&t.to_string()))
                    })
                    .collect()
            }
            "progressive" => {
                let budget = args
                    .get("token_budget")
                    .and_then(Value::as_u64)
                    .unwrap_or(2000) as usize;
                let mut used = 0usize;
                let mut out = Vec::new();
                for (m, v) in turns.into_iter().rev() {
                    let approx = v
                        .get("content")
                        .and_then(Value::as_str)
                        .map_or(0, |c| c.len() / 4);
                    if used + approx > budget {
                        break;
                    }
                    used += approx;
                    out.push((m, v));
                }
                out.reverse();
                out
            }
            _ => turns
                .into_iter()
                .rev()
                .take(n)
                .collect::<Vec<_>>()
                .into_iter()
                .rev()
                .collect(),
        };

        let full = mode != "progressive";
        let formatted: Vec<Value> = selected.iter().map(|(_, v)| format_turn(v, full)).collect();
        Ok(json!({
            "status": "success",
            "mode": mode,
            "count": formatted.len(),
            "session_id": session_id,
            "turns": formatted,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.continuity` — pull recent turns from the previous session.
pub struct SessionContinuityTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionContinuityTool {
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sessions".into())]),
        }
    }
}

#[async_trait]
impl Tool for SessionContinuityTool {
    fn name(&self) -> &str {
        "session.continuity"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "current_session_id": super::common::str_prop("Session to exclude (optional)"),
                "n": super::common::int_prop("Number of prior turns (default 10)"),
                "since": super::common::str_prop("Time-range floor: epoch seconds, RFC 3339, or YYYY-MM-DD"),
                "until": super::common::str_prop("Time-range ceiling: epoch seconds, RFC 3339, or YYYY-MM-DD"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Get cross-session continuity — the last N turns of the most recent prior session ('where we left off'). Args: current_session_id (optional, excluded), n (default 10), since/until (epoch seconds | RFC 3339 | YYYY-MM-DD)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let current = args.get("current_session_id").and_then(Value::as_str);
        let n = args.get("n").and_then(Value::as_u64).unwrap_or(10) as usize;

        // Find the most recent session_start that is not the current session.
        // `rfind` on scan order is a UUID lottery (LMDB iterates by key, and
        // v4 keys are random) — resolve by `created_at` instead.
        let memories = self.store.scan_all(Galaxy::Sessions)?;
        let previous = memories
            .iter()
            .filter(|m| {
                m.metadata.tags.contains(&"start".to_string())
                    && current.is_none_or(|c| m.metadata.id.to_string() != c)
            })
            .max_by_key(|m| m.metadata.created_at);

        let Some(prev) = previous else {
            // Empty-continuity false-negative guard (2026-08-28 cold-start
            // friction): "no previous session found" is truthful per-store
            // but reads as amnesia when the client is wired to the wrong
            // project store. The server knows its own scope — disclose it
            // with the same actionable-hint treatment the read-only write
            // refusal got (2026-08-22).
            let project = std::env::var("WM_PROJECT").ok().filter(|s| !s.is_empty());
            let store = self.store.path().display().to_string();
            let scope = project.map_or_else(
                || format!("store {store}"),
                |p| format!("store {store}, project '{p}'"),
            );
            return Ok(json!({
                "status": "success",
                "previous_session": null,
                "turns": [],
                "count": 0,
                "message": "no previous session found",
                "hint": format!(
                    "memory is project-scoped and this server's scope ({scope}) has no sessions. If you expected continuity for your project, your client may be wired to a different store: check the mcp block in your opencode config and compare with GET /status on the fleet (store_path, project). Per-project layout: docs/MULTI_PROJECT_MEMORY.md."
                ),
            }));
        };

        let prev_id = prev.metadata.id.to_string();
        let mut turns = filter_by_time(
            load_turns(&self.store, Some(&prev_id), 10_000, false)?,
            &args,
        )?;
        let total = turns.len();
        let tail: Vec<Value> = turns
            .split_off(total.saturating_sub(n))
            .iter()
            .map(|(_, v)| format_turn(v, true))
            .collect();
        Ok(json!({
            "status": "success",
            "previous_session": prev_id,
            "count": tail.len(),
            "turns": tail,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.digest` — compile a session's records into one handoff block.
///
/// The wrap-up writes itself: typed turns grouped by category,
/// importance-ordered, plus the latest structured checkpoint state if one
/// exists — so the manual wrap-up that duplicates records by hand becomes a
/// single deterministic call (experience-report item #4).
pub struct SessionDigestTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionDigestTool {
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sessions".into())]),
        }
    }
}

/// Display order for turn-type sections; unknown types follow, alphabetical.
const DIGEST_SECTION_ORDER: &[&str] = &["decision", "breakthrough", "error", "summary"];

#[async_trait]
impl Tool for SessionDigestTool {
    fn name(&self) -> &str {
        "session.digest"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "session_id": super::common::str_prop("Session to digest (default: most recent)"),
                "min_importance": super::common::num_prop("Importance floor (default 0.5)"),
                "include_checkpoint": {
                    "type": "boolean",
                    "description": "Append the latest checkpoint's git/handoff state (default true)."
                },
                "since": super::common::str_prop("Time-range floor: epoch seconds, RFC 3339, or YYYY-MM-DD"),
                "until": super::common::str_prop("Time-range ceiling: epoch seconds, RFC 3339, or YYYY-MM-DD"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Compile a session into a markdown handoff digest — turns grouped by type and importance-ordered, latest checkpoint state appended. Args: session_id (optional), min_importance (default 0.5), include_checkpoint (default true), since/until."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let session_id = match args.get("session_id").and_then(Value::as_str) {
            Some(sid) if !sid.is_empty() => sid.to_string(),
            _ => self
                .store
                .scan_all(Galaxy::Sessions)?
                .iter()
                .filter(|m| m.metadata.tags.contains(&"start".to_string()))
                .max_by_key(|m| m.metadata.created_at)
                .map(|m| m.metadata.id.to_string())
                .ok_or_else(|| {
                    wm_core::CoreError::Tool("no session found — run session.start first".into())
                })?,
        };
        let min_importance = args
            .get("min_importance")
            .and_then(Value::as_f64)
            .unwrap_or(0.5);
        let include_checkpoint = args
            .get("include_checkpoint")
            .and_then(Value::as_bool)
            .unwrap_or(true);

        let mut turns: Vec<_> = filter_by_time(
            load_turns(&self.store, Some(&session_id), 10_000, false)?,
            &args,
        )?
        .into_iter()
        .filter(|(_, v)| {
            v.get("importance").and_then(Value::as_f64).unwrap_or(0.0) >= min_importance
        })
        .collect();
        turns.sort_by(|a, b| {
            b.1.get("importance")
                .and_then(Value::as_f64)
                .unwrap_or(0.0)
                .total_cmp(&a.1.get("importance").and_then(Value::as_f64).unwrap_or(0.0))
        });

        // Group by turn_type; known sections first, others after (alphabetical).
        let mut groups: Vec<(String, Vec<&Value>)> = Vec::new();
        for (_, v) in &turns {
            let t = v
                .get("turn_type")
                .and_then(Value::as_str)
                .unwrap_or("message")
                .to_string();
            match groups.iter_mut().find(|(name, _)| *name == t) {
                Some((_, list)) => list.push(v),
                None => groups.push((t, vec![v])),
            }
        }
        groups.sort_by_key(|(name, _)| {
            (
                DIGEST_SECTION_ORDER
                    .iter()
                    .position(|k| k == name)
                    .unwrap_or(DIGEST_SECTION_ORDER.len()),
                name.clone(),
            )
        });

        let mut digest = format!("# Session handoff — {session_id}\n");
        let mut included = 0usize;
        for (turn_type, items) in &groups {
            writeln!(
                digest,
                "\n## {} ({})",
                capitalize(&pluralize(turn_type)),
                items.len()
            )
            .expect("write to String cannot fail");
            for v in items {
                let importance = v.get("importance").and_then(Value::as_f64).unwrap_or(0.0);
                let content = v.get("content").and_then(Value::as_str).unwrap_or("");
                writeln!(digest, "- ({importance:.2}) {content}")
                    .expect("write to String cannot fail");
                included += 1;
            }
        }

        // Latest verifiable checkpoint state, if any.
        let mut checkpoint_state = Value::Null;
        if include_checkpoint {
            if let Some(cp) = self
                .store
                .scan_all(Galaxy::Sessions)?
                .iter()
                .filter(|m| {
                    m.metadata.tags.contains(&"checkpoint".to_string())
                        && m.content.contains(&session_id)
                })
                .filter_map(|m| {
                    let parsed: Value = serde_json::from_str(&m.content).ok()?;
                    parsed
                        .get("handoff")
                        .filter(|h| !h.is_null())
                        .cloned()
                        .map(|h| (m.metadata.created_at, h))
                })
                .max_by_key(|(created_at, _)| *created_at)
                .map(|(_, handoff)| handoff)
            {
                digest.push_str("\n## Checkpoint state\n");
                if let Some(git) = cp.get("git") {
                    writeln!(
                        digest,
                        "- commit `{}` on `{}` ({} dirty files)",
                        git.get("commit").and_then(Value::as_str).unwrap_or("?"),
                        git.get("branch").and_then(Value::as_str).unwrap_or("?"),
                        git.get("dirty_count").and_then(Value::as_i64).unwrap_or(0)
                    )
                    .expect("write to String cannot fail");
                }
                if let Some(q) = cp.get("next_queue").and_then(Value::as_array) {
                    if !q.is_empty() {
                        writeln!(
                            digest,
                            "- next queue: {}",
                            q.iter()
                                .filter_map(Value::as_str)
                                .collect::<Vec<_>>()
                                .join(" → ")
                        )
                        .expect("write to String cannot fail");
                    }
                }
                if let Some(f) = cp.get("open_flags").and_then(Value::as_array) {
                    if !f.is_empty() {
                        writeln!(
                            digest,
                            "- open flags: {}",
                            f.iter()
                                .filter_map(Value::as_str)
                                .collect::<Vec<_>>()
                                .join("; ")
                        )
                        .expect("write to String cannot fail");
                    }
                }
                if let Some(tg) = cp.get("tests_green") {
                    writeln!(digest, "- tests green: {tg}").expect("write to String cannot fail");
                }
                checkpoint_state = cp;
            }
        }

        Ok(json!({
            "status": "success",
            "session_id": session_id,
            "digest": digest,
            "turns_included": included,
            "turns_total_scanned": turns.len(),
            "sections": groups.iter().map(|(t, items)| json!({"type": t, "count": items.len()})).collect::<Vec<_>>(),
            "checkpoint": checkpoint_state,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Capitalize the first letter of a label for section headings.
fn capitalize(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
        None => String::new(),
    }
}

/// Naive English plural for turn-type labels (decision→Decisions,
/// summary→Summaries).
fn pluralize(s: &str) -> String {
    if let Some(stem) = s.strip_suffix('y') {
        format!("{stem}ies")
    } else {
        format!("{s}s")
    }
}

/// `session.handoff` — package a session for transfer to another device.
pub struct SessionHandoffTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionHandoffTool {
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("sessions".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for SessionHandoffTool {
    fn name(&self) -> &str {
        "session.handoff"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "action": super::common::str_prop("transfer | accept | list"),
                "session_id": super::common::str_prop("transfer: session to hand off"),
                "message": super::common::str_prop("transfer: handoff note"),
                "handoff_id": super::common::str_prop("accept: handoff to accept"),
            }),
            &["action"],
        )
    }
    fn description(&self) -> &str {
        "Transfer or resume a session across devices (actions: transfer, accept, list). transfer: session_id (required) + message; accept: handoff_id; list: pending handoffs."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let action = args.get("action").and_then(Value::as_str).unwrap_or("list");
        match action {
            "transfer" => {
                let session_id =
                    args.get("session_id")
                        .and_then(Value::as_str)
                        .ok_or_else(|| {
                            wm_core::CoreError::InvalidArgs(
                                "session_id required for transfer".into(),
                            )
                        })?;
                let message = args.get("message").and_then(Value::as_str).unwrap_or("");
                let turns = load_turns(&self.store, Some(session_id), 10_000, false)?;
                if turns.is_empty() {
                    return Err(wm_core::CoreError::Tool(format!(
                        "session {session_id} has no recorded turns"
                    )));
                }
                let summary: Vec<Value> =
                    turns.iter().map(|(_, v)| format_turn(v, false)).collect();
                let handoff_id = format!("handoff-{}", uuid::Uuid::new_v4());
                let mut mem = Memory::new(
                    Galaxy::Sessions,
                    json!({
                        "type": "session_handoff",
                        "handoff_id": handoff_id,
                        "session_id": session_id,
                        "message": message,
                        "status": "pending",
                        "turn_count": summary.len(),
                        "summary": summary,
                        "created_at": wm_core::time::now_unix_millis(),
                    })
                    .to_string(),
                );
                mem.metadata.tags = vec![
                    "session".into(),
                    "handoff".into(),
                    format!("session:{session_id}"),
                ];
                mem.metadata.importance = 0.8;
                self.store.put(Galaxy::Sessions, &mem)?;
                Ok(json!({
                    "status": "success",
                    "action": "transfer",
                    "handoff_id": handoff_id,
                    "session_id": session_id,
                    "turn_count": summary.len(),
                }))
            }
            "accept" => {
                let handoff_id =
                    args.get("handoff_id")
                        .and_then(Value::as_str)
                        .ok_or_else(|| {
                            wm_core::CoreError::InvalidArgs("handoff_id required for accept".into())
                        })?;
                let memories = self.store.scan_all(Galaxy::Sessions)?;
                let found = memories.iter().find(|m| {
                    m.metadata.tags.contains(&"handoff".to_string())
                        && m.content.contains(handoff_id)
                });
                let Some(mem) = found else {
                    return Err(wm_core::CoreError::Tool(format!(
                        "handoff {handoff_id} not found"
                    )));
                };
                let mut updated = mem.clone();
                if let Ok(mut v) = serde_json::from_str::<Value>(&updated.content) {
                    v["status"] = json!("accepted");
                    updated.content = v.to_string();
                }
                self.store.put(Galaxy::Sessions, &updated)?;
                Ok(json!({
                    "status": "success",
                    "action": "accept",
                    "handoff_id": handoff_id,
                }))
            }
            "list" => {
                let memories = self.store.scan_all(Galaxy::Sessions)?;
                let handoffs: Vec<Value> = memories
                    .iter()
                    .filter(|m| m.metadata.tags.contains(&"handoff".to_string()))
                    .filter_map(|m| serde_json::from_str::<Value>(&m.content).ok())
                    .filter(|v| v.get("status").and_then(Value::as_str) == Some("pending"))
                    .map(|v| {
                        json!({
                            "handoff_id": v.get("handoff_id"),
                            "session_id": v.get("session_id"),
                            "message": v.get("message"),
                            "turn_count": v.get("turn_count"),
                        })
                    })
                    .collect();
                Ok(json!({
                    "status": "success",
                    "action": "list",
                    "pending_count": handoffs.len(),
                    "handoffs": handoffs,
                }))
            }
            other => Err(wm_core::CoreError::InvalidArgs(format!(
                "unknown session.handoff action: {other}"
            ))),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Register the session-ops tools (4).
#[must_use]
/// `session.export` — serialize a session to JSONL for store-to-store moves.
///
/// Exports the start marker, every turn (including superseded — history
/// travels with the session), and checkpoints, preserving ids, timestamps,
/// and tags so an import reconstructs the session faithfully.
pub struct SessionExportTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionExportTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sessions".into())]),
        }
    }
}

#[async_trait]
impl Tool for SessionExportTool {
    fn name(&self) -> &str {
        "session.export"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "session_id": super::common::str_prop("Session to export (default: most recent)"),
                "path": super::common::str_prop("Write JSONL to this file instead of returning inline"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Export a session as JSONL (start marker + turns + checkpoints, preserving ids/timestamps/tags). Args: session_id (optional), path (optional — writes to file; otherwise returns jsonl inline)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let session_id = match args.get("session_id").and_then(Value::as_str) {
            Some(sid) if !sid.is_empty() => sid.to_string(),
            _ => self
                .store
                .scan_all(Galaxy::Sessions)?
                .iter()
                .filter(|m| m.metadata.tags.contains(&"start".to_string()))
                .max_by_key(|m| m.metadata.created_at)
                .map(|m| m.metadata.id.to_string())
                .ok_or_else(|| {
                    wm_core::CoreError::Tool("no session found — run session.start first".into())
                })?,
        };

        // Start marker matches by id; turns/checkpoints carry the id in
        // content. Superseded turns are included deliberately: history is
        // part of the story being re-homed.
        let mut members: Vec<Memory> = self
            .store
            .scan_all(Galaxy::Sessions)?
            .into_iter()
            .filter(|m| m.metadata.id.to_string() == session_id || m.content.contains(&session_id))
            .collect();
        members.sort_by_key(|m| m.metadata.created_at);

        let mut jsonl = String::new();
        // Envelope v2 (S4): header line first, records after. Importers of
        // any version accept the stream; v1 readers that split on lines
        // would see the header as an unparseable record — acceptable for a
        // forward-only addition, and `wm` builds from this point on all
        // read envelopes.
        let header = wm_memory::envelope::EnvelopeHeader::new("session_export", members.len());
        jsonl.push_str(&header.header_line());
        jsonl.push('\n');
        for m in &members {
            let line = serde_json::to_string(m)
                .map_err(|e| wm_core::CoreError::Tool(format!("export serialize: {e}")))?;
            jsonl.push_str(&line);
            jsonl.push('\n');
        }

        let path_arg = args
            .get("path")
            .and_then(Value::as_str)
            .filter(|s| !s.is_empty());
        if let Some(dest) = path_arg {
            std::fs::write(dest, &jsonl)
                .map_err(|e| wm_core::CoreError::Tool(format!("export write {dest}: {e}")))?;
            Ok(json!({
                "status": "success",
                "session_id": session_id,
                "records": members.len(),
                "path": dest,
            }))
        } else {
            Ok(json!({
                "status": "success",
                "session_id": session_id,
                "records": members.len(),
                "jsonl": jsonl,
            }))
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.import` — restore exported sessions into this store.
///
/// Counterpart to [`SessionExportTool`]: reads JSONL lines (file path or
/// inline), validates the envelope header (`wm_memory::envelope`, S4 —
/// bare v1 payloads accepted), deserializes each full Memory record, and
/// puts it into the Sessions galaxy with its original id, timestamps, and
/// tags — so continuity/replay behave identically in the new store. When a
/// writable `SearchEngine` is available, records are indexed in the same
/// pass (one commit per import), so imported sessions are searchable
/// immediately and leave no index drift for `heal_index_drift` to sweep.
pub struct SessionImportTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<wm_memory::SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionImportTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<wm_memory::SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("sessions".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for SessionImportTool {
    fn name(&self) -> &str {
        "session.import"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "path": super::common::str_prop("Read JSONL from this file"),
                "jsonl": super::common::str_prop("Or pass the export payload inline"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Import sessions from session.export JSONL (path or inline jsonl) — envelope-v2 header validated when present, bare v1 accepted; preserves ids, timestamps, and tags; indexes into the search index; overwrites on id collision."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let payload = match args
            .get("path")
            .and_then(Value::as_str)
            .filter(|s| !s.is_empty())
        {
            Some(path) => std::fs::read_to_string(path)
                .map_err(|e| wm_core::CoreError::Tool(format!("import read {path}: {e}")))?,
            None => args
                .get("jsonl")
                .and_then(Value::as_str)
                .filter(|s| !s.is_empty())
                .ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs(
                        "provide either 'path' or inline 'jsonl'".into(),
                    )
                })?
                .to_string(),
        };

        // Envelope v2 (S4): the first non-empty line may be a header. A
        // refused header (newer format) aborts the import — partial
        // imports of a forward stream are the failure mode the envelope
        // exists to prevent.
        let mut envelope: Option<wm_memory::envelope::EnvelopeHeader> = None;
        let mut record_lines: Vec<&str> = Vec::new();
        let mut header_consumed = false;
        for line in payload.lines() {
            if line.trim().is_empty() {
                continue;
            }
            if !header_consumed {
                header_consumed = true;
                match wm_memory::envelope::read_header_line(line) {
                    wm_memory::envelope::HeaderRead::Header(h) => {
                        envelope = Some(h);
                        continue;
                    }
                    wm_memory::envelope::HeaderRead::Refused(msg) => {
                        return Err(wm_core::CoreError::Tool(msg));
                    }
                    wm_memory::envelope::HeaderRead::NotAHeader => {}
                }
            }
            record_lines.push(line);
        }

        // Index in the same pass when a writable engine is available.
        // Read-only engines cannot take the writer; the import still
        // lands in LMDB and `heal_index_drift` sweeps the gap at the next
        // writable startup — disclosed honestly below.
        let readonly_engine = self.search.as_ref().is_some_and(|s| s.is_readonly());
        if readonly_engine {
            tracing::warn!(
                "session.import running against a read-only search engine — records land \
                 in LMDB unindexed; they become searchable at the next writable startup \
                 (heal_index_drift)"
            );
        }
        let mut writer_slot = match (&self.search, readonly_engine) {
            (Some(s), false) => s.writer().ok(),
            _ => None,
        };

        let mut imported = 0usize;
        let mut indexed = 0usize;
        let mut skipped = 0usize;
        let mut session_ids: Vec<String> = Vec::new();
        for (lineno, line) in record_lines.iter().enumerate() {
            let mem: Memory = match serde_json::from_str(line) {
                Ok(m) => m,
                Err(e) => {
                    skipped += 1;
                    tracing::warn!(line = lineno + 1, error = %e, "skipping unparseable export line");
                    continue;
                }
            };
            if let Ok(parsed) = serde_json::from_str::<Value>(&mem.content) {
                if let Some(sid) = parsed.get("session_id").and_then(Value::as_str) {
                    if !session_ids.iter().any(|s| s == sid) {
                        session_ids.push(sid.to_string());
                    }
                }
            }
            // Tantivy documents are not keyed — delete-then-add keeps the
            // index honest on id collisions (re-imports), mirroring the
            // ingest ledger's re-ingest pattern.
            if let (Some(search), Some(writer)) = (&self.search, writer_slot.as_mut()) {
                let id_str = mem.metadata.id.to_string();
                let _ = search.delete_document(writer, &id_str);
                match search.add_document(
                    writer,
                    &id_str,
                    mem.metadata.galaxy.db_name(),
                    &mem.content,
                    &mem.metadata.tags,
                    mem.metadata.created_at.timestamp(),
                ) {
                    Ok(()) => indexed += 1,
                    Err(e) => {
                        tracing::warn!(id = %id_str, error = %e, "import index add failed (LMDB record kept)");
                    }
                }
            }
            self.store.put(Galaxy::Sessions, &mem)?;
            imported += 1;
        }

        if let Some(search) = &self.search {
            if let Some(mut writer) = writer_slot {
                search
                    .commit(&mut writer)
                    .map_err(|e| wm_core::CoreError::Tool(format!("import index commit: {e}")))?;
            }
        }

        let mut warnings: Vec<String> = Vec::new();
        if let Some(h) = &envelope {
            if h.count != imported {
                let msg = format!(
                    "envelope declares count {} but {} records imported",
                    h.count, imported
                );
                tracing::warn!("{msg}");
                warnings.push(msg);
            }
        }

        let envelope_info = envelope.as_ref().map(|h| {
            json!({
                "format_version": h.format_version,
                "kind": h.kind,
                "generator": h.generator,
                "created_at": h.created_at,
                "declared_count": h.count,
            })
        });

        Ok(json!({
            "status": "success",
            "imported": imported,
            "skipped": skipped,
            "session_ids": session_ids,
            "indexed": indexed,
            "envelope": envelope_info,
            "warnings": warnings,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

pub fn register_session_ops(
    registry: &wm_dispatch::ToolRegistry,
    store: &Arc<MemoryStore>,
    search: Option<Arc<wm_memory::SearchEngine>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(SessionRecordTool::new(store.clone())))
        .register(Arc::new(SessionReplayTool::new(store.clone())))
        .register(Arc::new(SessionContinuityTool::new(store.clone())))
        .register(Arc::new(SessionHandoffTool::new(store.clone())))
        .register(Arc::new(SessionExportTool::new(store.clone())))
        .register(Arc::new(SessionImportTool::new(store.clone(), search)))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_store() -> Arc<MemoryStore> {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("lmdb");
        std::fs::create_dir_all(&path).unwrap();
        Arc::new(MemoryStore::open_default(path).unwrap())
    }

    fn start_session(store: &MemoryStore) -> String {
        let mut mem = Memory::new(
            Galaxy::Sessions,
            json!({"type": "session_start"}).to_string(),
        );
        mem.metadata.tags = vec!["session".into(), "start".into()];
        store.put(Galaxy::Sessions, &mem).unwrap();
        mem.metadata.id.to_string()
    }

    /// Start a session with an explicit `created_at` age so tests can pin
    /// recency independent of UUID sort order.
    fn start_session_aged(store: &MemoryStore, age_secs: i64) -> String {
        let mut mem = Memory::new(
            Galaxy::Sessions,
            json!({"type": "session_start"}).to_string(),
        );
        mem.metadata.tags = vec!["session".into(), "start".into()];
        mem.metadata.created_at = chrono::Utc::now() - chrono::Duration::seconds(age_secs);
        store.put(Galaxy::Sessions, &mem).unwrap();
        mem.metadata.id.to_string()
    }

    /// Record a turn with a backdated creation time (for time-filter tests).
    fn record_aged_turn(store: &MemoryStore, sid: &str, age_days: u32, content: &str) {
        let mut mem = Memory::new(
            Galaxy::Sessions,
            json!({
                "type": "session_turn",
                "session_id": sid,
                "role": "ai",
                "turn_type": "decision",
                "importance": 0.9,
                "content": content,
            })
            .to_string(),
        );
        mem.metadata.tags = vec!["session".into(), "turn".into(), format!("session:{sid}")];
        mem.metadata.created_at = Utc::now() - chrono::Duration::days(i64::from(age_days));
        store.put(Galaxy::Sessions, &mem).unwrap();
    }

    #[tokio::test]
    async fn replay_time_filters_since_and_until() {
        let store = test_store();
        let sid = start_session(&store);
        record_aged_turn(&store, &sid, 3, "three days ago");
        record_aged_turn(&store, &sid, 2, "two days ago");
        record_aged_turn(&store, &sid, 1, "yesterday");
        record_aged_turn(&store, &sid, 0, "today");

        let replay = SessionReplayTool::new(store);
        let mut ctx = Context::default();

        // "What changed since Tuesday?" — date-only floor.
        let two_days_ago = (Utc::now() - chrono::Duration::days(2)).format("%Y-%m-%d");
        let v = replay
            .call(
                &mut ctx,
                json!({"session_id": sid, "since": two_days_ago.to_string()}),
            )
            .await
            .unwrap();
        assert_eq!(v["count"], 3, "since=date keeps day-of + later: {v}");

        // Epoch-seconds ceiling between the yesterday-turn and today.
        let until_epoch = (Utc::now() - chrono::Duration::hours(23)).timestamp();
        let v = replay
            .call(&mut ctx, json!({"session_id": sid, "until": until_epoch}))
            .await
            .unwrap();
        assert_eq!(
            v["count"], 3,
            "until=epoch(23h ago) keeps the three older turns: {v}"
        );

        // Combined window (half-day margins absorb sub-second record skew).
        let since = (Utc::now() - chrono::Duration::hours(60)).to_rfc3339();
        let until = (Utc::now() - chrono::Duration::hours(12)).to_rfc3339();
        let v = replay
            .call(
                &mut ctx,
                json!({"session_id": sid, "since": since, "until": until}),
            )
            .await
            .unwrap();
        assert_eq!(v["count"], 2, "window keeps two/two-days-ago turns: {v}");
        for turn in v["turns"].as_array().unwrap() {
            assert_ne!(
                turn["content"], "today",
                "time filters must exclude out-of-window turns"
            );
        }

        // Invalid bound is an error, not silence.
        assert!(
            replay
                .call(&mut ctx, json!({"session_id": sid, "since": "not-a-date"}))
                .await
                .is_err()
        );
    }

    #[tokio::test]
    async fn continuity_respects_since_filter() {
        let store = test_store();
        let sid1 = start_session(&store);
        record_aged_turn(&store, &sid1, 5, "ancient decision");
        record_aged_turn(&store, &sid1, 0, "fresh decision");
        let sid2 = start_session(&store);

        let continuity = SessionContinuityTool::new(store);
        let mut ctx = Context::default();
        let cutoff = (Utc::now() - chrono::Duration::days(1))
            .format("%Y-%m-%d")
            .to_string();
        let v = continuity
            .call(
                &mut ctx,
                json!({"current_session_id": sid2, "since": cutoff, "n": 10}),
            )
            .await
            .unwrap();
        assert_eq!(v["count"], 1, "only the fresh turn is in range: {v}");
        assert_eq!(v["turns"][0]["content"], "fresh decision");

        // Unfiltered still sees both.
        let all = continuity
            .call(&mut ctx, json!({"current_session_id": sid2, "n": 10}))
            .await
            .unwrap();
        assert_eq!(all["count"], 2);
    }

    #[tokio::test]
    async fn digest_groups_by_type_and_respects_importance_floor() {
        let store = test_store();
        let sid = start_session(&store);
        // Mixed types/importances; the 0.3 turn must not appear.
        for (turn_type, importance, content) in [
            ("summary", 0.6, "wrapped up"),
            ("decision", 0.9, "picked architecture CO over alternatives"),
            ("error", 0.95, "startForce root cause found"),
            ("breakthrough", 0.85, "watch resolution insight"),
            ("message", 0.3, "low-value chatter"),
        ] {
            let mut mem = Memory::new(
                Galaxy::Sessions,
                json!({
                    "type": "session_turn",
                    "session_id": sid,
                    "role": "ai",
                    "turn_type": turn_type,
                    "importance": importance,
                    "content": content,
                })
                .to_string(),
            );
            mem.metadata.tags = vec!["session".into(), "turn".into()];
            store.put(Galaxy::Sessions, &mem).unwrap();
        }

        let tool = SessionDigestTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"session_id": sid, "min_importance": 0.5}))
            .await
            .unwrap();

        assert_eq!(v["status"], "success");
        let digest = v["digest"].as_str().unwrap();
        // Every ≥0.85 turn present verbatim.
        for expected in [
            "startForce root cause found",
            "picked architecture CO over alternatives",
            "watch resolution insight",
        ] {
            assert!(
                digest.contains(expected),
                "digest must contain '{expected}': {digest}"
            );
        }
        // Nothing below the floor.
        assert!(!digest.contains("low-value chatter"), "got: {digest}");
        // Section order: decisions before breakthroughs before errors... per DIGEST_SECTION_ORDER decision<breakthrough<error; summary last of knowns.
        let d = digest.find("## Decisions").unwrap();
        let b = digest.find("## Breakthroughs").unwrap();
        let e = digest.find("## Errors").unwrap();
        let s = digest.find("## Summaries").unwrap();
        assert!(
            d < b && b < e && e < s,
            "sections must follow canonical order: {digest}"
        );
        assert_eq!(v["turns_included"], 4);

        // Raising the floor to 0.9 drops the breakthrough + summary.
        let strict = tool
            .call(&mut ctx, json!({"session_id": sid, "min_importance": 0.9}))
            .await
            .unwrap();
        let strict_digest = strict["digest"].as_str().unwrap();
        assert!(strict_digest.contains("startForce"));
        assert!(!strict_digest.contains("watch resolution insight"));
    }

    #[tokio::test]
    async fn digest_appends_checkpoint_state() {
        let store = test_store();
        let sid = start_session(&store);

        // Seed a checkpoint with handoff state directly (avoids git fixture).
        let mut cp = Memory::new(
            Galaxy::Sessions,
            json!({
                "type": "checkpoint",
                "session_id": sid,
                "label": "wrap",
                "data": {},
                "handoff": {
                    "git": {
                        "commit": "abc1234",
                        "branch": "main",
                        "dirty_count": 2
                    },
                    "tests_green": true,
                    "next_queue": ["first task", "second task"],
                    "open_flags": ["flaky probe"]
                }
            })
            .to_string(),
        );
        cp.metadata.tags = vec!["session".into(), "checkpoint".into()];
        store.put(Galaxy::Sessions, &cp).unwrap();

        let tool = SessionDigestTool::new(store);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"session_id": sid}))
            .await
            .unwrap();

        let digest = v["digest"].as_str().unwrap();
        assert!(digest.contains("## Checkpoint state"), "got: {digest}");
        assert!(digest.contains("abc1234"));
        assert!(digest.contains("first task → second task"));
        assert!(digest.contains("flaky probe"));
        assert_eq!(v["checkpoint"]["git"]["branch"], "main");
    }

    #[tokio::test]
    async fn supersedes_hides_old_turn_until_requested() {
        // P2: evolving stories amend instead of accumulating contradictory
        // blobs. The superseded turn leaves default retrieval but stays in
        // history behind include_superseded.
        let store = test_store();
        let sid = start_session(&store);
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();

        let first = record
            .call(
                &mut ctx,
                json!({"role": "ai", "turn_type": "decision", "importance": 0.9,
                        "content": "perf: 240ms", "session_id": sid}),
            )
            .await
            .unwrap();
        let old_id = first["memory_id"].as_str().unwrap().to_string();

        let second = record
            .call(
                &mut ctx,
                json!({"role": "ai", "turn_type": "decision", "importance": 0.9,
                        "content": "perf revised: 180ms after warm cache",
                        "session_id": sid, "supersedes": old_id}),
            )
            .await
            .unwrap();
        assert_eq!(second["status"], "success");
        let _new_id = second["memory_id"].as_str().unwrap().to_string();

        // Default replay shows only the correction.
        let replay = SessionReplayTool::new(store.clone());
        let v = replay
            .call(&mut ctx, json!({"session_id": sid}))
            .await
            .unwrap();
        assert_eq!(
            v["count"], 1,
            "superseded turn must be hidden by default: {v}"
        );
        assert_eq!(
            v["turns"][0]["content"],
            "perf revised: 180ms after warm cache"
        );

        // History stays intact behind the flag.
        let with_history = replay
            .call(
                &mut ctx,
                json!({"session_id": sid, "include_superseded": true}),
            )
            .await
            .unwrap();
        assert_eq!(with_history["count"], 2, "got: {with_history}");

        // Continuity and digest also use the current story.
        let sid2 = start_session(&store);
        let continuity = SessionContinuityTool::new(store.clone());
        let c = continuity
            .call(&mut ctx, json!({"current_session_id": sid2}))
            .await
            .unwrap();
        assert_eq!(c["count"], 1, "continuity must skip superseded turns: {c}");
        assert_eq!(
            c["turns"][0]["content"],
            "perf revised: 180ms after warm cache"
        );

        let digest = SessionDigestTool::new(store);
        let d = digest
            .call(&mut ctx, json!({"session_id": sid, "min_importance": 0.5}))
            .await
            .unwrap();
        let digest_text = d["digest"].as_str().unwrap();
        assert!(digest_text.contains("180ms"), "got: {digest_text}");
        assert!(
            !digest_text.contains("240ms"),
            "superseded claim must not leak: {digest_text}"
        );
    }

    #[tokio::test]
    async fn export_import_roundtrip_preserves_history() {
        // B3 acceptance: export → import into a FRESH store → continuity and
        // replay return identical turns (ids, timestamps, tags intact).
        let store_a = test_store();
        let sid = start_session(&store_a);
        let record = SessionRecordTool::new(store_a.clone());
        let mut ctx = Context::default();
        record_aged_turn(&store_a, &sid, 2, "day-one decision");
        record_aged_turn(&store_a, &sid, 1, "day-two decision");
        let first = record
            .call(
                &mut ctx,
                json!({"role": "ai", "turn_type": "decision", "importance": 0.9,
                        "content": "original claim", "session_id": sid}),
            )
            .await
            .unwrap();
        record
            .call(
                &mut ctx,
                json!({"role": "ai", "turn_type": "decision", "importance": 0.9,
                        "content": "corrected claim",
                        "session_id": sid,
                        "supersedes": first["memory_id"].as_str().unwrap()}),
            )
            .await
            .unwrap();

        // Export inline.
        let export = SessionExportTool::new(store_a.clone());
        // Title the start marker (S4: envelope roundtrip must preserve it).
        {
            let mut marker: Memory = store_a
                .scan_all(Galaxy::Sessions)
                .unwrap()
                .into_iter()
                .find(|m| m.metadata.tags.contains(&"start".to_string()))
                .unwrap();
            marker.metadata.title = Some("The Big Decision".to_string());
            marker.metadata.topic = Some("v8-slices".to_string());
            store_a.put(Galaxy::Sessions, &marker).unwrap();
        }
        let exported = export
            .call(&mut ctx, json!({"session_id": sid}))
            .await
            .unwrap();
        assert_eq!(exported["status"], "success");
        let jsonl = exported["jsonl"].as_str().unwrap();
        // start + 4 turns (incl. superseded) = 6 records minimum.
        assert_eq!(
            exported["records"], 5,
            "start + 2 aged + 2 claims: {exported}"
        );
        // Envelope v2: header line + 5 records.
        assert_eq!(jsonl.lines().count(), 6);
        let header_line = jsonl.lines().next().unwrap();
        match wm_memory::envelope::read_header_line(header_line) {
            wm_memory::envelope::HeaderRead::Header(h) => {
                assert_eq!(h.kind, "session_export");
                assert_eq!(h.count, 5);
            }
            other => panic!("first line must be the envelope header, got {other:?}"),
        }

        // Import into a completely fresh store.
        let store_b = test_store();
        let import = SessionImportTool::new(store_b.clone(), None);
        let imported = import
            .call(&mut ctx, json!({"jsonl": jsonl}))
            .await
            .unwrap();
        assert_eq!(imported["imported"], 5, "got: {imported}");
        assert_eq!(imported["skipped"], 0);
        assert_eq!(imported["session_ids"], json!([sid]));
        // Envelope disclosed; count matched.
        assert_eq!(imported["envelope"]["format_version"], 2);
        assert_eq!(imported["envelope"]["declared_count"], 5);
        assert_eq!(imported["warnings"], json!([]));
        // Title/topic survive the roundtrip (start marker carries them).
        let marker_b = store_b
            .scan_all(Galaxy::Sessions)
            .unwrap()
            .into_iter()
            .find(|m| m.metadata.tags.contains(&"start".to_string()))
            .unwrap();
        assert_eq!(marker_b.metadata.title.as_deref(), Some("The Big Decision"));
        assert_eq!(marker_b.metadata.topic.as_deref(), Some("v8-slices"));

        // Replay in store B matches the current story exactly...
        let replay_b = SessionReplayTool::new(store_b.clone());
        let v = replay_b
            .call(&mut ctx, json!({"session_id": sid}))
            .await
            .unwrap();
        assert_eq!(v["count"], 3, "two aged turns + correction: {v}");
        let contents: Vec<&str> = v["turns"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|t| t["content"].as_str())
            .collect();
        assert!(contents.contains(&"day-one decision"));
        assert!(contents.contains(&"corrected claim"));
        assert!(!contents.contains(&"original claim"));

        // ...and with history the superseded turn is still there.
        let full = replay_b
            .call(
                &mut ctx,
                json!({"session_id": sid, "include_superseded": true}),
            )
            .await
            .unwrap();
        assert_eq!(full["count"], 4);

        // Continuity in store B sees an imported prior session by recency.
        let new_sid = start_session(&store_b);
        let continuity = SessionContinuityTool::new(store_b);
        let c = continuity
            .call(
                &mut ctx,
                json!({"current_session_id": new_sid, "since":
                    (Utc::now() - chrono::Duration::days(3)).format("%Y-%m-%d").to_string()}),
            )
            .await
            .unwrap();
        assert_eq!(
            c["previous_session"], sid,
            "import must preserve created_at so recency resolution works"
        );
        assert_eq!(c["count"], 3);
    }

    #[tokio::test]
    async fn import_rejects_missing_payload() {
        let store = test_store();
        let tool = SessionImportTool::new(store, None);
        let mut ctx = Context::default();
        assert!(tool.call(&mut ctx, json!({})).await.is_err());
    }

    #[tokio::test]
    async fn import_refuses_newer_envelope_format() {
        let store = test_store();
        let mut ctx = Context::default();
        let header = wm_memory::envelope::EnvelopeHeader {
            format_version: wm_memory::envelope::ENVELOPE_FORMAT_VERSION + 1,
            kind: "session_export".into(),
            created_at: chrono::Utc::now().to_rfc3339(),
            count: 1,
            generator: "wm 99.0.0".into(),
        };
        let record =
            serde_json::to_string(&Memory::new(Galaxy::Sessions, "future".into())).unwrap();
        let payload = format!("{}\n{record}\n", header.header_line());
        let tool = SessionImportTool::new(store, None);
        let result = tool.call(&mut ctx, json!({"jsonl": payload})).await;
        let err = format!("{:?}", result.unwrap_err());
        assert!(err.contains("newer than this build supports"), "{err}");
    }

    /// S4 acceptance: import through a real writable engine leaves zero
    /// index drift — imported sessions are searchable immediately, and a
    /// re-import (id collisions) does not duplicate index documents.
    #[tokio::test]
    async fn import_indexes_tantivy_no_drift_even_on_reimport() {
        let dir = tempfile::tempdir().unwrap();
        let lmdb = dir.path().join("lmdb");
        std::fs::create_dir_all(&lmdb).unwrap();
        let store = Arc::new(MemoryStore::open_default(&lmdb).unwrap());
        let tantivy = dir.path().join("tantivy");
        std::fs::create_dir_all(&tantivy).unwrap();
        let search = Arc::new(wm_memory::SearchEngine::open(&tantivy).unwrap());

        // Export from a source store.
        let store_a = test_store();
        let sid = start_session(&store_a);
        let mut ctx = Context::default();
        SessionRecordTool::new(store_a.clone())
            .call(
                &mut ctx,
                json!({"role": "ai", "turn_type": "decision", "importance": 0.9,
                        "content": "kumquat governance ratchet engaged", "session_id": sid}),
            )
            .await
            .unwrap();
        let exported = SessionExportTool::new(store_a.clone())
            .call(&mut ctx, json!({"session_id": sid}))
            .await
            .unwrap();
        let jsonl = exported["jsonl"].as_str().unwrap().to_string();

        // Import into a fresh store WITH a writable engine — twice.
        let import = SessionImportTool::new(store.clone(), Some(search.clone()));
        for round in 1..=2 {
            let r = import
                .call(&mut ctx, json!({"jsonl": jsonl}))
                .await
                .unwrap();
            assert_eq!(r["status"], "success", "round {round}: {r}");
            assert_eq!(r["skipped"], 0);
            assert_eq!(
                r["indexed"], r["imported"],
                "round {round}: every record indexed: {r}"
            );
        }

        // The acceptance: no drift — LMDB and Tantivy agree after two
        // imports (delete-then-add kept the index honest on collision).
        let report = wm_memory::reindex::check_consistency(&store, &search);
        let drifted: Vec<_> = report
            .galaxies
            .iter()
            .filter(|g| g.drift)
            .map(|g| g.galaxy.clone())
            .collect();
        assert!(
            drifted.is_empty(),
            "import must leave zero index drift, drifted: {drifted:?}"
        );

        // And the imported content is actually findable through the index.
        let needle_id = store
            .scan_all(Galaxy::Sessions)
            .unwrap()
            .iter()
            .find(|m| m.content.contains("kumquat"))
            .unwrap()
            .metadata
            .id
            .to_string();
        let hits = search.search("kumquat governance ratchet", 10).unwrap();
        assert!(
            hits.iter().any(|h| h.memory_id == needle_id),
            "imported record must be searchable via the index: {hits:?}"
        );
    }

    #[tokio::test]
    async fn record_then_replay_full() {
        let store = test_store();
        let sid = start_session(&store);
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();
        for (i, role) in [("user", "hello"), ("ai", "hi there")].iter().enumerate() {
            let r = record
                .call(
                    &mut ctx,
                    json!({"role": role.0, "content": role.1, "session_id": sid}),
                )
                .await
                .unwrap();
            assert_eq!(r["sequence"], i as u64 + 1);
        }

        let replay = SessionReplayTool::new(store.clone());
        let v = replay
            .call(&mut ctx, json!({"mode": "full", "session_id": sid}))
            .await
            .unwrap();
        assert_eq!(v["count"], 2);
        assert_eq!(v["turns"][0]["content"], "hello");
        assert_eq!(v["turns"][1]["role"], "ai");
    }

    #[tokio::test]
    async fn record_requires_content_and_valid_role() {
        let store = test_store();
        let tool = SessionRecordTool::new(store);
        let mut ctx = Context::default();
        assert!(tool.call(&mut ctx, json!({})).await.is_err());
        assert!(
            tool.call(&mut ctx, json!({"role": "system", "content": "x"}))
                .await
                .is_err()
        );
    }

    /// Provenance contract (sessions-galaxy archaeology fix, 2026-08-29):
    /// the turn's role is its authorship claim — ai turns stamp agent/0.7,
    /// user turns stamp user/1.0, and nothing defaults to a user claim.
    #[tokio::test]
    async fn record_stamps_provenance_from_role() {
        let store = test_store();
        let sid = start_session(&store);
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();
        let ai = record
            .call(
                &mut ctx,
                json!({"role": "ai", "content": "agent turn", "session_id": sid}),
            )
            .await
            .unwrap();
        let user = record
            .call(
                &mut ctx,
                json!({"role": "user", "content": "human turn", "session_id": sid}),
            )
            .await
            .unwrap();

        let ai_mem = store
            .get(
                Galaxy::Sessions,
                uuid::Uuid::parse_str(ai["memory_id"].as_str().unwrap()).unwrap(),
            )
            .expect("ai turn stored")
            .expect("ai turn present");
        assert_eq!(ai_mem.metadata.source, "agent");
        assert!((ai_mem.metadata.source_trust - 0.7).abs() < 1e-5);

        let user_mem = store
            .get(
                Galaxy::Sessions,
                uuid::Uuid::parse_str(user["memory_id"].as_str().unwrap()).unwrap(),
            )
            .expect("user turn stored")
            .expect("user turn present");
        assert_eq!(user_mem.metadata.source, "user");
        assert!((user_mem.metadata.source_trust - 1.0).abs() < f32::EPSILON);
    }

    #[tokio::test]
    async fn continuity_returns_previous_session_tail() {
        let store = test_store();
        let sid1 = start_session(&store);
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();
        for i in 0..5 {
            record
                .call(
                    &mut ctx,
                    json!({"role": "user", "content": format!("turn {i}"), "session_id": sid1}),
                )
                .await
                .unwrap();
        }
        let sid2 = start_session(&store);
        let continuity = SessionContinuityTool::new(store);
        let v = continuity
            .call(&mut ctx, json!({"current_session_id": sid2, "n": 2}))
            .await
            .unwrap();
        assert_eq!(v["previous_session"], sid1);
        assert_eq!(v["count"], 2);
        assert_eq!(v["turns"][1]["content"], "turn 4");
        assert!(
            v.get("hint").is_none(),
            "non-empty continuity must not carry the scoping hint"
        );
    }

    #[tokio::test]
    async fn continuity_empty_store_discloses_project_scoping() {
        // Cold-start friction (2026-08-28): a client wired to the wrong
        // project store saw "no previous session found" — truthful but
        // indistinguishable from amnesia. Empty results must disclose the
        // server's scope and how to check the wiring.
        let store = test_store();
        let continuity = SessionContinuityTool::new(store);
        let mut ctx = Context::default();
        let v = continuity.call(&mut ctx, json!({})).await.unwrap();

        assert_eq!(v["status"], "success");
        assert_eq!(v["count"], 0);
        let hint = v["hint"].as_str().expect("hint present on empty store");
        assert!(hint.contains("project-scoped"), "got: {hint}");
        assert!(hint.contains("opencode config"), "got: {hint}");
        assert!(hint.contains("GET /status"), "got: {hint}");
        // The hint names the store this server actually serves.
        assert!(hint.contains("store "), "got: {hint}");
    }

    #[tokio::test]
    async fn record_defaults_to_newest_start_by_time_not_key_order() {
        // Regression: LMDB iterates by UUID key, which is random for v4 —
        // positional "last" silently misfiled turns into arbitrary sessions
        // once more than one start existed (observed live 2026-08-22 when a
        // fresh session's record landed in an older NEON session).
        let store = test_store();
        for age in [50_000, 40_000, 30_000, 20_000, 10_000] {
            start_session_aged(&store, age);
        }
        let newest = start_session_aged(&store, 0);

        let record = SessionRecordTool::new(store);
        let mut ctx = Context::default();
        let r = record
            .call(&mut ctx, json!({"role": "ai", "content": "latest turn"}))
            .await
            .unwrap();
        assert_eq!(
            r["session_id"], newest,
            "record without explicit session_id must target the newest start by created_at"
        );
    }

    #[tokio::test]
    async fn continuity_picks_newest_prior_by_time_not_key_order() {
        // Regression companion: continuity must exclude the current session
        // and pick the most recent PRIOR start by created_at, not by scan
        // position.
        let store = test_store();
        for age in [40_000, 30_000, 20_000] {
            start_session_aged(&store, age);
        }
        let newest_prior = start_session_aged(&store, 10);
        let current = start_session_aged(&store, 0);

        let continuity = SessionContinuityTool::new(store);
        let mut ctx = Context::default();
        let v = continuity
            .call(&mut ctx, json!({"current_session_id": current, "n": 1}))
            .await
            .unwrap();
        assert_eq!(
            v["previous_session"], newest_prior,
            "continuity must select the newest prior session by created_at"
        );
    }

    #[tokio::test]
    async fn handoff_transfer_accept_list() {
        let store = test_store();
        let sid = start_session(&store);
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();
        record
            .call(
                &mut ctx,
                json!({"role": "ai", "content": "context", "session_id": sid}),
            )
            .await
            .unwrap();

        let handoff = SessionHandoffTool::new(store.clone());
        let t = handoff
            .call(
                &mut ctx,
                json!({"action": "transfer", "session_id": sid, "message": "take over"}),
            )
            .await
            .unwrap();
        assert_eq!(t["status"], "success");
        let hid = t["handoff_id"].as_str().unwrap().to_string();

        let list = handoff
            .call(&mut ctx, json!({"action": "list"}))
            .await
            .unwrap();
        assert_eq!(list["pending_count"], 1);

        let a = handoff
            .call(&mut ctx, json!({"action": "accept", "handoff_id": hid}))
            .await
            .unwrap();
        assert_eq!(a["status"], "success");

        let list2 = handoff
            .call(&mut ctx, json!({"action": "list"}))
            .await
            .unwrap();
        assert_eq!(list2["pending_count"], 0);
    }
}
