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
use sha2::{Digest, Sha256};
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

/// Latest checkpoint handoff for a session: `(checkpoint_id, created_at,
/// handoff)`. Shared by `session.digest` and `session.continuity` so the
/// structured handoff (next_queue, open_flags, git, tests_green, lease_id)
/// surfaces wherever "where were we?" resolves.
fn latest_checkpoint_handoff(
    store: &MemoryStore,
    session_id: &str,
) -> wm_core::Result<Option<(String, DateTime<Utc>, Value)>> {
    Ok(store
        .scan_all(Galaxy::Sessions)?
        .iter()
        .filter(|m| {
            m.metadata.tags.contains(&"checkpoint".to_string()) && m.content.contains(session_id)
        })
        .filter_map(|m| {
            let parsed: Value = serde_json::from_str(&m.content).ok()?;
            parsed
                .get("handoff")
                .filter(|h| !h.is_null())
                .cloned()
                .map(|h| (m.metadata.id.to_string(), m.metadata.created_at, h))
        })
        .max_by_key(|(_, created_at, _)| *created_at))
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

/// Continuity output bounds (2026-09-21 reviewer finding: one 100,000-char
/// turn produced a ~200 KB JSON-RPC response — a single pathological memory
/// dumping tens of thousands of tokens into the context window continuity
/// exists to protect). Per-turn content is capped, the turns budget bounds
/// the whole response, and every turn carries its memory id so the exact
/// original stays one `memory.read` away.
const CONTINUITY_DEFAULT_MAX_CONTENT_BYTES: usize = 8 * 1024;
const CONTINUITY_DEFAULT_MAX_RESPONSE_BYTES: usize = 48 * 1024;
const CONTINUITY_MIN_BUDGET_BYTES: usize = 256;
const CONTINUITY_MAX_BUDGET_BYTES: usize = 256 * 1024;
/// Wrapper/metadata allowance inside the turns budget: turn objects carry
/// ~200 B of metadata each, so a single capped turn plus its metadata must
/// stay under the budget.
const CONTINUITY_WRAPPER_ALLOWANCE: usize = 256;

/// Largest byte index <= `max` that sits on a UTF-8 boundary.
fn floor_char_boundary_index(s: &str, max: usize) -> usize {
    let mut end = max.min(s.len());
    while end > 0 && !s.is_char_boundary(end) {
        end -= 1;
    }
    end
}

/// Continuity turn: metadata plus bounded content and an exact-read id.
fn format_continuity_turn(mem: &Memory, v: &Value, max_content_bytes: usize) -> Value {
    let role = v.get("role").and_then(Value::as_str).unwrap_or("?");
    let content = v.get("content").and_then(Value::as_str).unwrap_or("");
    let end = floor_char_boundary_index(content, max_content_bytes);
    json!({
        "memory_id": mem.metadata.id.to_string(),
        "session_id": v.get("session_id"),
        "sequence": v.get("sequence"),
        "role": role,
        "turn_type": v.get("turn_type"),
        "importance": v.get("importance"),
        "content": &content[..end],
        "content_bytes": content.len(),
        "content_truncated": end < content.len(),
    })
}

const LOSSLESS_MAX_PAGE_SIZE: usize = 64;
const LOSSLESS_DEFAULT_PAGE_SIZE: usize = 16;
const LOSSLESS_MIN_WIRE_BYTES: usize = 1024;
const LOSSLESS_MAX_WIRE_BYTES: usize = 49_152;

fn hex_encode(bytes: &[u8]) -> String {
    use std::fmt::Write as _;
    bytes
        .iter()
        .fold(String::with_capacity(bytes.len() * 2), |mut out, b| {
            let _ = write!(out, "{b:02x}");
            out
        })
}

fn hex_decode(value: &str) -> Option<Vec<u8>> {
    if value.len() > 4096
        || value.len() % 2 != 0
        || !value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return None;
    }
    (0..value.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&value[i..i + 2], 16).ok())
        .collect()
}

fn base64_encode(bytes: &[u8]) -> String {
    const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::with_capacity(bytes.len().div_ceil(3) * 4);
    for chunk in bytes.chunks(3) {
        let n = u32::from(chunk[0]) << 16
            | u32::from(*chunk.get(1).unwrap_or(&0)) << 8
            | u32::from(*chunk.get(2).unwrap_or(&0));
        out.push(char::from(TABLE[((n >> 18) & 63) as usize]));
        out.push(char::from(TABLE[((n >> 12) & 63) as usize]));
        out.push(if chunk.len() > 1 {
            char::from(TABLE[((n >> 6) & 63) as usize])
        } else {
            '='
        });
        out.push(if chunk.len() > 2 {
            char::from(TABLE[(n & 63) as usize])
        } else {
            '='
        });
    }
    out
}

#[cfg(test)]
fn base64_decode(value: &str) -> Option<Vec<u8>> {
    const fn digit(byte: u8) -> Option<u8> {
        match byte {
            b'A'..=b'Z' => Some(byte - b'A'),
            b'a'..=b'z' => Some(byte - b'a' + 26),
            b'0'..=b'9' => Some(byte - b'0' + 52),
            b'+' => Some(62),
            b'/' => Some(63),
            _ => None,
        }
    }
    if value.len() % 4 != 0 {
        return None;
    }
    let mut out = Vec::new();
    for chunk in value.as_bytes().chunks_exact(4) {
        let a = digit(chunk[0])?;
        let b = digit(chunk[1])?;
        let c = if chunk[2] == b'=' {
            0
        } else {
            digit(chunk[2])?
        };
        let d = if chunk[3] == b'=' {
            0
        } else {
            digit(chunk[3])?
        };
        out.push((a << 2) | (b >> 4));
        if chunk[2] != b'=' {
            out.push((b << 4) | (c >> 2));
        }
        if chunk[3] != b'=' {
            out.push((c << 6) | d);
        }
    }
    Some(out)
}

#[derive(Clone)]
struct LosslessTurn {
    memory: Memory,
    turn: Value,
    content: String,
    content_hash: String,
}

fn lossless_error(kind: &str) -> wm_core::CoreError {
    wm_core::CoreError::InvalidArgs(format!("lossless_{kind}"))
}

fn lossless_cursor(
    session_id: &str,
    include_superseded: bool,
    page_size: usize,
    max_wire: usize,
    view: &str,
    index: usize,
    offset: usize,
) -> String {
    // This is deliberately an unsigned, canonical placement hint. It is not
    // authority: every request rebuilds the visible view before placement.
    let value = json!({"v":1,"session_id":session_id,"include_superseded":include_superseded,"page_size":page_size,"max_wire_bytes":max_wire,"view":view,"index":index,"offset":offset});
    hex_encode(value.to_string().as_bytes())
}

fn parse_lossless_cursor(
    cursor: &str,
    session_id: &str,
    include_superseded: bool,
    page_size: usize,
    max_wire: usize,
) -> wm_core::Result<(String, usize, usize)> {
    let bytes = hex_decode(cursor).ok_or_else(|| lossless_error("invalid_cursor"))?;
    let text = String::from_utf8(bytes).map_err(|_| lossless_error("invalid_cursor"))?;
    let value: Value = serde_json::from_str(&text).map_err(|_| lossless_error("invalid_cursor"))?;
    let canonical = json!({"v":value.get("v"),"session_id":value.get("session_id"),"include_superseded":value.get("include_superseded"),"page_size":value.get("page_size"),"max_wire_bytes":value.get("max_wire_bytes"),"view":value.get("view"),"index":value.get("index"),"offset":value.get("offset")});
    let canonical_text =
        serde_json::to_string(&canonical).map_err(|_| lossless_error("invalid_cursor"))?;
    if canonical_text != text
        || value.get("v").and_then(Value::as_u64) != Some(1)
        || value.get("session_id").and_then(Value::as_str) != Some(session_id)
        || value.get("include_superseded").and_then(Value::as_bool) != Some(include_superseded)
        || value.get("page_size").and_then(Value::as_u64) != Some(page_size as u64)
        || value.get("max_wire_bytes").and_then(Value::as_u64) != Some(max_wire as u64)
    {
        return Err(lossless_error("invalid_cursor"));
    }
    let view = value
        .get("view")
        .and_then(Value::as_str)
        .filter(|v| {
            v.len() == 64
                && v.bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        })
        .ok_or_else(|| lossless_error("invalid_cursor"))?;
    let index = value
        .get("index")
        .and_then(Value::as_u64)
        .and_then(|v| usize::try_from(v).ok())
        .ok_or_else(|| lossless_error("invalid_cursor"))?;
    let offset = value
        .get("offset")
        .and_then(Value::as_u64)
        .and_then(|v| usize::try_from(v).ok())
        .ok_or_else(|| lossless_error("invalid_cursor"))?;
    Ok((view.to_string(), index, offset))
}

/// The documented `session.record` turn-type vocabulary.
///
/// Digest/continuity key on these sections; a value outside the list is a
/// caller error, not a new historical fact (2026-09-19 review).
pub const TURN_TYPES: &[&str] = &[
    "message",
    "decision",
    "breakthrough",
    "question",
    "answer",
    "code_change",
    "error",
    "summary",
    "context",
];

/// Maximum track-slug length (the `track:<slug>` tag suffix).
pub const TRACK_MAX_LEN: usize = 64;

/// Validate a track slug: the machine-addressable name of a work track.
///
/// Lowercase ASCII alphanumeric start, then lowercase alphanumeric or
/// `-`, `_`, `.`, `/`; 1..=`TRACK_MAX_LEN` chars. Strict on purpose — the
/// slug is a tag suffix, so near-duplicates (`Harness-2` vs `harness-2`)
/// would silently split one track's log in two.
pub(crate) fn validate_track(track: &str) -> wm_core::Result<()> {
    let valid = !track.is_empty()
        && track.len() <= TRACK_MAX_LEN
        && track
            .chars()
            .next()
            .is_some_and(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
        && track.chars().all(|c| {
            c.is_ascii_lowercase() || c.is_ascii_digit() || matches!(c, '-' | '_' | '.' | '/')
        });
    if valid {
        Ok(())
    } else {
        Err(wm_core::CoreError::InvalidArgs(format!(
            "invalid track {track:?} — must start with a-z0-9, contain only a-z0-9, '-', '_', '.', '/', \
             and be at most {TRACK_MAX_LEN} chars"
        )))
    }
}

/// `session.record` — record a conversation turn as persistent session memory.
pub struct SessionRecordTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
    search: Option<Arc<wm_memory::SearchEngine>>,
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
            search: None,
        }
    }

    /// Index writes at write time so `wm status` index health and
    /// `memory.search` agree with canonical storage without waiting for the
    /// next startup heal (2026-09-15 review finding).
    #[must_use]
    pub fn with_search(mut self, search: Option<Arc<wm_memory::SearchEngine>>) -> Self {
        self.search = search;
        self
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
                "turn_type": json!({
                    "type": "string",
                    "enum": TURN_TYPES,
                    "description": "Turn type (default message)",
                }),
                "importance": super::common::bounded_num_prop("0-1 importance (default 0.5)", 0.0, 1.0),
                "session_id": super::common::str_prop("Target session (default: most recent session)"),
                "supersedes": super::common::str_prop("Memory id of an earlier turn this record corrects/replaces (amend-with-supersede)"),
                "track": super::common::str_prop("Optional track slug (lowercase; a-z0-9 start, then a-z0-9-_. /) — tags this turn into that track's implementation log (session.track_log)"),
            }),
            &["content"],
        )
    }
    fn description(&self) -> &str {
        "Record a conversation turn as persistent session memory. Args: content (required), role (user|ai, default user), turn_type (default message), importance (0-1, default 0.5), session_id (optional — defaults to the most recent session), supersedes (optional turn memory-id — marks the old turn superseded so replay/continuity/digest use the new record), track (optional slug — tags the turn into that track's log, read back with session.track_log)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let role = args.get("role").and_then(Value::as_str).unwrap_or("user");
        if !matches!(role, "user" | "ai") {
            return Err(wm_core::CoreError::InvalidArgs(
                "role must be 'user' or 'ai'".into(),
            ));
        }
        // Blank content is a caller error (memory.create rejects it too);
        // whitespace-only turns must not become historical facts.
        let content = args
            .get("content")
            .and_then(Value::as_str)
            .filter(|s| !s.trim().is_empty())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("content is required and must not be blank".into())
            })?;
        // The documented vocabulary is the contract; an unknown type would
        // otherwise be stored as a malformed historical fact (2026-09-19
        // review: arbitrary strings were accepted despite the fixed list).
        let turn_type = args
            .get("turn_type")
            .and_then(Value::as_str)
            .unwrap_or("message");
        if !TURN_TYPES.contains(&turn_type) {
            return Err(wm_core::CoreError::InvalidArgs(format!(
                "turn_type must be one of: {}",
                TURN_TYPES.join(", ")
            )));
        }
        // Canonical importance contract (2026-09-19 review): the same
        // validator memory.create/update use — out-of-range values are
        // caller errors, never silently clamped. This path used to accept
        // importance=1.5 and store 1.0 while sibling APIs rejected it.
        let importance = wm_dispatch::write_gate::parse_importance_value(args.get("importance"))
            .map_err(wm_core::CoreError::InvalidArgs)?
            .unwrap_or(0.5);
        let session_id = args.get("session_id").and_then(Value::as_str);
        // Track membership is a machine-readable tag (`track:<slug>`), so a
        // malformed slug is a caller error — never a silent near-duplicate
        // track (2026-09-20 track-log design).
        let track = args.get("track").and_then(Value::as_str);
        if let Some(track) = track {
            validate_track(track)?;
        }

        // Resolve the session: explicit id, or the most recent session_start.
        // Resolution MUST use `created_at`, not iteration position: LMDB scan
        // order is key (UUID) order, which is random for v4 UUIDs — picking
        // positionally (`next_back`) silently misfiles turns into an
        // arbitrary session once more than one start exists.
        let session_id: String = if let Some(sid) = session_id {
            // 2026-09-21 reviewer finding: any string was accepted, so a typo
            // or stale id silently created an orphan turn (Memories 1,
            // Sessions 0) that continuity then could not recover. An
            // explicit id must name an existing session_start; session.import
            // is the recovery path for genuinely orphaned/imported turns.
            let parsed = uuid::Uuid::parse_str(sid).map_err(|e| {
                wm_core::CoreError::InvalidArgs(format!("invalid session_id {sid:?}: {e}"))
            })?;
            let is_start = self
                .store
                .get(Galaxy::Sessions, parsed)?
                .is_some_and(|m| m.metadata.tags.iter().any(|t| t == "start"));
            if !is_start {
                return Err(wm_core::CoreError::NotFound(format!(
                    "no session found with id {sid} — run session.start first \
                     (session.import is the recovery path for orphan/imported turns)"
                )));
            }
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

        // Amend-with-supersede (P2) target: validated before the turn is
        // written, so a bad id never burns a sequence.
        let supersedes = match args.get("supersedes").and_then(Value::as_str) {
            Some(old_id_str) => {
                let old_id = uuid::Uuid::parse_str(old_id_str).map_err(|e| {
                    wm_core::CoreError::InvalidArgs(format!("invalid 'supersedes' id: {e}"))
                })?;
                if self.store.get(Galaxy::Sessions, old_id)?.is_none() {
                    return Err(wm_core::CoreError::NotFound(format!(
                        "superseded turn {old_id} not found"
                    )));
                }
                Some(old_id)
            }
            None => None,
        };

        // H1 (2026-09-20 review): the sequence is allocated inside the same
        // LMDB write transaction as the turn record — never derived from a
        // scan. Concurrent writers get unique, contiguous sequences; a crash
        // rolls back counter and record together.
        let timestamp = wm_core::time::now_unix_millis();
        let (sequence, mem) = self.store.put_session_turn(&session_id, |sequence| {
            let mut turn = json!({
                "type": "session_turn",
                "session_id": session_id,
                "sequence": sequence,
                "role": role,
                "turn_type": turn_type,
                "importance": importance,
                "content": content,
                "timestamp": timestamp,
            });
            if let Some(track) = track {
                turn["track"] = json!(track);
            }
            let mut mem = Memory::new(Galaxy::Sessions, turn.to_string());
            mem.metadata.tags = vec![
                "session".into(),
                "turn".into(),
                role.into(),
                turn_type.into(),
                format!("session:{session_id}"),
            ];
            if let Some(track) = track {
                mem.metadata.tags.push(format!("track:{track}"));
            }
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
            mem.metadata.importance = importance as f32;
            // Amend-with-supersede (P2): the new record carries the pointer;
            // the old turn is marked after the new one commits (below).
            if let Some(old_id) = supersedes {
                mem.metadata.tags.push(format!("supersedes:{old_id}"));
            }
            mem
        })?;

        // Mark the corrected turn so default retrieval uses the new record.
        // History stays intact — the old turn remains queryable via
        // include_superseded. Ordering: the new turn commits first, so a
        // crash between the two writes leaves the old turn visible
        // (contradiction preserved) rather than superseded with no
        // replacement.
        if let Some(old_id) = supersedes {
            if let Some(mut old) = self.store.get(Galaxy::Sessions, old_id)? {
                old.metadata
                    .tags
                    .push(format!("superseded-by:{}", mem.metadata.id));
                self.store.put(Galaxy::Sessions, &old)?;
                super::common::index_memory(&self.store, self.search.as_deref(), &old);
            }
        }

        super::common::index_memory(&self.store, self.search.as_deref(), &mem);
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

    fn lossless(&self, args: &Value) -> wm_core::Result<Value> {
        const ALLOWED: &[&str] = &[
            "mode",
            "session_id",
            "include_superseded",
            "page_size",
            "max_wire_bytes",
            "cursor",
        ];
        let object = args
            .as_object()
            .ok_or_else(|| lossless_error("invalid_args"))?;
        if object.keys().any(|key| !ALLOWED.contains(&key.as_str())) {
            return Err(lossless_error("unsupported_selection_args"));
        }
        let session_id = args
            .get("session_id")
            .and_then(Value::as_str)
            .filter(|s| !s.is_empty())
            .ok_or_else(|| lossless_error("session_id_required"))?;
        uuid::Uuid::parse_str(session_id).map_err(|_| lossless_error("invalid_session_id"))?;
        let include_superseded = match args.get("include_superseded") {
            None => false,
            Some(v) => v.as_bool().ok_or_else(|| lossless_error("invalid_args"))?,
        };
        let size_arg = |name: &str, default: usize| -> wm_core::Result<usize> {
            match args.get(name) {
                None => Ok(default),
                Some(v) => v
                    .as_u64()
                    .and_then(|v| usize::try_from(v).ok())
                    .ok_or_else(|| lossless_error("invalid_args")),
            }
        };
        let page_size = size_arg("page_size", LOSSLESS_DEFAULT_PAGE_SIZE)?;
        let max_wire = size_arg("max_wire_bytes", LOSSLESS_MAX_WIRE_BYTES)?;
        if !(1..=LOSSLESS_MAX_PAGE_SIZE).contains(&page_size)
            || !(LOSSLESS_MIN_WIRE_BYTES..=LOSSLESS_MAX_WIRE_BYTES).contains(&max_wire)
        {
            return Err(lossless_error("invalid_args"));
        }

        // Reject untrusted syntax and bindings before consulting source records.
        let placement = match args.get("cursor") {
            None => None,
            Some(v) => Some(parse_lossless_cursor(
                v.as_str().ok_or_else(|| lossless_error("invalid_cursor"))?,
                session_id,
                include_superseded,
                page_size,
                max_wire,
            )?),
        };
        let memories = self.store.scan_all_strict(Galaxy::Sessions)?;
        let start = memories.iter().find(|m| {
            m.metadata.id.to_string() == session_id
                && m.metadata.tags.contains(&"start".to_string())
                && !m.metadata.is_private
                && !m.metadata.model_exclude
        });
        if start.is_none() {
            return Err(wm_core::CoreError::NotFound("session not found".into()));
        }
        let mut turns = Vec::new();
        for memory in memories {
            if memory.metadata.is_private
                || memory.metadata.model_exclude
                || (!include_superseded
                    && memory
                        .metadata
                        .tags
                        .iter()
                        .any(|t| t.starts_with("superseded-by:")))
            {
                continue;
            }
            let tagged = memory
                .metadata
                .tags
                .contains(&format!("session:{session_id}"));
            let turn = match serde_json::from_str::<Value>(&memory.content) {
                Ok(v) => v,
                Err(_) if tagged => return Err(lossless_error("malformed_selected_turn")),
                Err(_) => continue,
            };
            if turn.get("type").and_then(Value::as_str) != Some("session_turn") {
                if tagged && memory.metadata.tags.iter().any(|tag| tag == "turn") {
                    return Err(lossless_error("malformed_selected_turn"));
                }
                continue;
            }
            if !tagged && turn.get("session_id").and_then(Value::as_str) != Some(session_id) {
                continue;
            }
            let content = turn
                .get("content")
                .and_then(Value::as_str)
                .ok_or_else(|| lossless_error("malformed_selected_turn"))?
                .to_string();
            // A selected session tag contradicting its payload is corruption,
            // not a reason to silently omit an advertised session record.
            if turn.get("session_id").and_then(Value::as_str) != Some(session_id)
                || turn.get("sequence").and_then(Value::as_u64).is_none()
                || turn.get("timestamp").and_then(Value::as_i64).is_none()
            {
                return Err(lossless_error("malformed_selected_turn"));
            }
            turns.push(LosslessTurn {
                content_hash: hex_encode(&Sha256::digest(content.as_bytes())),
                memory,
                turn,
                content,
            });
        }
        turns.sort_by_key(|turn| {
            (
                turn.turn["sequence"].as_u64().unwrap(),
                turn.turn["timestamp"].as_i64().unwrap(),
                turn.memory.metadata.id,
            )
        });
        let visible_ids: std::collections::HashSet<String> = turns
            .iter()
            .map(|t| t.memory.metadata.id.to_string())
            .collect();
        let metadata: Vec<Value> = turns.iter().map(|t| {
            let relationships: Vec<&str> = t.memory.metadata.tags.iter().filter_map(|tag| {
                let (_, id) = tag.split_once(':')?;
                ((tag.starts_with("superseded-by:") || tag.starts_with("supersedes:")) && visible_ids.contains(id)).then_some(tag.as_str())
            }).collect();
            json!({"role":t.turn.get("role"),"turn_type":t.turn.get("turn_type"),"importance":t.turn.get("importance"),"created_at":t.memory.metadata.created_at,"source":t.memory.metadata.source,"source_trust":t.memory.metadata.source_trust,"agent_id":t.memory.metadata.agent_id,"supersession":relationships})
        }).collect();
        let manifest: Vec<Value> = turns.iter().zip(&metadata).map(|(t,m)| json!({"id":t.memory.metadata.id,"sequence":t.turn["sequence"],"timestamp":t.turn["timestamp"],"hash":t.content_hash,"metadata":m})).collect();
        let view = hex_encode(&Sha256::digest(json!({"v":1,"galaxy":"sessions","session_id":session_id,"include_superseded":include_superseded,"page_size":page_size,"max_wire_bytes":max_wire,"records":manifest}).to_string().as_bytes()));
        let (mut index, mut offset) = match placement {
            Some((token_view, index, offset)) => {
                if token_view != view {
                    return Err(lossless_error("stale_view"));
                }
                (index, offset)
            }
            None => (0, 0),
        };
        if index > turns.len() || (index == turns.len() && offset != 0) {
            return Err(lossless_error("invalid_placement"));
        }
        if index < turns.len() && offset != 0 && offset >= turns[index].content.len() {
            return Err(lossless_error("invalid_placement"));
        }
        let mut records = Vec::new();
        while index < turns.len() && records.len() < page_size {
            let turn = &turns[index];
            let bytes = turn.content.as_bytes();
            let whole = json!({"record_id":turn.memory.metadata.id.to_string(),"sequence":turn.turn["sequence"],"timestamp":turn.turn["timestamp"],"metadata":metadata[index],"content_encoding":"utf-8","content":turn.content,"content_sha256":turn.content_hash,"complete":true});
            let candidate = json!({"status":"success","mode":"lossless","session_id":session_id,"galaxy":"sessions","view_fingerprint":view,"records":records.iter().cloned().chain(std::iter::once(whole.clone())).collect::<Vec<_>>(),"has_more":index+1<turns.len(),"next_cursor":if index+1==turns.len() {Value::Null} else {json!(lossless_cursor(session_id,include_superseded,page_size,max_wire,&view,index+1,0))},"complete":index+1==turns.len()});
            if offset == 0 && serde_json::to_vec(&candidate).unwrap().len() <= max_wire {
                records.push(whole);
                index += 1;
                offset = 0;
                continue;
            }
            if !records.is_empty() {
                break;
            }
            let mut take = bytes.len().saturating_sub(offset);
            while take > 0 {
                let end = offset + take;
                let chunk = json!({"record_id":turn.memory.metadata.id.to_string(),"sequence":turn.turn["sequence"],"timestamp":turn.turn["timestamp"],"metadata":metadata[index],"content_sha256":turn.content_hash,"chunk":{"encoding":"base64","byte_offset":offset,"total_bytes":bytes.len(),"data_b64":base64_encode(&bytes[offset..end]),"complete":end==bytes.len()}});
                let next = if end == bytes.len() {
                    lossless_cursor(
                        session_id,
                        include_superseded,
                        page_size,
                        max_wire,
                        &view,
                        index + 1,
                        0,
                    )
                } else {
                    lossless_cursor(
                        session_id,
                        include_superseded,
                        page_size,
                        max_wire,
                        &view,
                        index,
                        end,
                    )
                };
                let final_chunk = end == bytes.len() && index + 1 == turns.len();
                let candidate = json!({"status":"success","mode":"lossless","session_id":session_id,"galaxy":"sessions","view_fingerprint":view,"records":[chunk.clone()],"has_more":!final_chunk,"next_cursor":if final_chunk {Value::Null} else {json!(next)},"complete":final_chunk});
                if serde_json::to_vec(&candidate).unwrap().len() <= max_wire {
                    records.push(chunk);
                    if end == bytes.len() {
                        index += 1;
                        offset = 0;
                    } else {
                        offset = end;
                    }
                    break;
                }
                take /= 2;
            }
            if records.is_empty() {
                return Err(lossless_error("wire_ceiling_too_small"));
            }
            break;
        }
        let complete = index == turns.len() && offset == 0;
        let response = json!({"status":"success","mode":"lossless","session_id":session_id,"galaxy":"sessions","view_fingerprint":view,"records":records,"has_more":!complete,"next_cursor":if complete { Value::Null } else { json!(lossless_cursor(session_id,include_superseded,page_size,max_wire,&view,index,offset)) },"complete":complete});
        if serde_json::to_vec(&response).unwrap().len() > max_wire {
            return Err(lossless_error("wire_ceiling_too_small"));
        }
        Ok(response)
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
                "mode": super::common::str_prop("full | selective | progressive | lossless (default full)"),
                "session_id": super::common::str_prop("Target session (required explicit UUID for lossless; otherwise default most recent)"),
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
            "page_size": super::common::int_prop("Lossless mode records per page (1-64, default 16)"),
            "max_wire_bytes": super::common::int_prop("Lossless mode serialized JSON ceiling (1024-49152)"),
            "cursor": super::common::str_prop("Lossless mode opaque placement cursor"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Replay session turns. Legacy full/selective/progressive use optional session_id, n and since/until. Lossless requires an explicit session UUID and permits only mode, session_id, include_superseded, page_size (1-64, default16), max_wire_bytes (1024-49152, default49152), cursor. Follow returned cursors with unchanged settings for byte-exact content; base64 chunks are raw bytes, concatenate before UTF-8 decoding. Changed visible views refuse stale_view. Cursors are unsigned non-authority placement hints. Tool-result JSON budget is not the outer transport or model budget."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let mode = args.get("mode").and_then(Value::as_str).unwrap_or("full");
        if mode == "lossless" {
            return self.lossless(&args);
        }
        let requested_session_id = args
            .get("session_id")
            .and_then(Value::as_str)
            .filter(|sid| !sid.is_empty());
        // Match session.record, digest, and export: omission means the most
        // recent session_start by created_at, never all sessions in LMDB key
        // order. Per-session sequence numbers collide, so replaying the
        // unfiltered set can otherwise interleave unrelated conversations.
        let session_id = match requested_session_id {
            Some(sid) => Some(sid.to_string()),
            None => self
                .store
                .scan_all(Galaxy::Sessions)?
                .iter()
                .filter(|m| m.metadata.tags.contains(&"start".to_string()))
                .max_by_key(|m| m.metadata.created_at)
                .map(|m| m.metadata.id.to_string()),
        };
        let n = args.get("n").and_then(Value::as_u64).unwrap_or(50) as usize;
        let include_superseded = args
            .get("include_superseded")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        // No resolved session_start is a cold/no-start state, not permission
        // to replay arbitrary orphan turn records. Explicit IDs below still
        // retain their existing direct replay behavior for recovery callers.
        let loaded_turns = match session_id.as_deref() {
            Some(sid) => load_turns(&self.store, Some(sid), 10_000, include_superseded)?,
            None => Vec::new(),
        };
        let turns = filter_by_time(loaded_turns, &args)?;

        // An explicitly requested session that has no turns is an error, not
        // an empty success — silent emptiness hides typos and stale IDs.
        if requested_session_id.is_some() && turns.is_empty() {
            return Err(wm_core::CoreError::InvalidArgs(format!(
                "no session found with id {requested_session_id:?}"
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
                "max_content_bytes": super::common::int_prop("Per-turn content cap in bytes (256-262144, default 8192)"),
                "max_response_bytes": super::common::int_prop("Turns budget in bytes (256-262144, default 49152)"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Get cross-session continuity — the last N turns of the most recent prior session ('where we left off') plus that session's latest checkpoint handoff (next_queue, open_flags, git state, tests_green, lease_id) when one exists. Args: current_session_id (optional, excluded), n (default 10), since/until (epoch seconds | RFC 3339 | YYYY-MM-DD), max_content_bytes (per-turn cap, default 8192), max_response_bytes (turns budget, default 49152). Output is bounded: each turn carries memory_id, content_bytes, and content_truncated; the newest turns win when the budget is exceeded (turns_omitted), and an oversized checkpoint handoff is replaced by a truncation marker. Read exact originals with memory.read id=<memory_id>."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let current = args
            .get("current_session_id")
            .or_else(|| args.get("session_id"))
            .and_then(Value::as_str);
        let n = args.get("n").and_then(Value::as_u64).unwrap_or(10) as usize;
        let size_arg = |name: &str, default: usize| -> wm_core::Result<usize> {
            match args.get(name) {
                None => Ok(default),
                Some(v) => v
                    .as_u64()
                    .and_then(|v| usize::try_from(v).ok())
                    .ok_or_else(|| {
                        wm_core::CoreError::InvalidArgs(format!("{name} must be an integer"))
                    }),
            }
        };
        let max_content_bytes =
            size_arg("max_content_bytes", CONTINUITY_DEFAULT_MAX_CONTENT_BYTES)?;
        let max_response_bytes =
            size_arg("max_response_bytes", CONTINUITY_DEFAULT_MAX_RESPONSE_BYTES)?;
        if !(CONTINUITY_MIN_BUDGET_BYTES..=CONTINUITY_MAX_BUDGET_BYTES).contains(&max_content_bytes)
            || !(CONTINUITY_MIN_BUDGET_BYTES..=CONTINUITY_MAX_BUDGET_BYTES)
                .contains(&max_response_bytes)
        {
            return Err(wm_core::CoreError::InvalidArgs(format!(
                "continuity budgets must be in {CONTINUITY_MIN_BUDGET_BYTES}..={CONTINUITY_MAX_BUDGET_BYTES} bytes"
            )));
        }

        // Find the most recent session_start that is not the current session.
        // `rfind` on scan order is a UUID lottery (LMDB iterates by key, and
        // v4 keys are random) — resolve by `created_at` instead.
        //
        // Empty-newest-session guard (2026-09-13, first-run feedback): a
        // session that was just started but has no turns yet is the caller's
        // *current* session in all but name. The default previous session is
        // therefore the most recent candidate that actually recorded a turn;
        // only when no candidate has turns do we fall back to the newest and
        // report its empty turn list truthfully.
        let memories = self.store.scan_all(Galaxy::Sessions)?;
        let mut starts: Vec<_> = memories
            .iter()
            .filter(|m| {
                m.metadata.tags.contains(&"start".to_string())
                    && current.is_none_or(|c| m.metadata.id.to_string() != c)
            })
            .collect();
        starts.sort_by_key(|m| std::cmp::Reverse(m.metadata.created_at));
        let previous = starts
            .iter()
            .find(|m| {
                let sid = m.metadata.id.to_string();
                load_turns(&self.store, Some(&sid), 1, false).is_ok_and(|turns| !turns.is_empty())
            })
            .copied()
            .or_else(|| starts.first().copied());

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
        let selected = turns.split_off(total.saturating_sub(n));
        // Newest first: the budget drops the OLDEST selected turns first —
        // recent context is what "where we left off" is for. The newest turn
        // is always kept (content-capped), so the response is bounded even
        // when a single turn exceeds the whole budget.
        let newest_first: Vec<(Memory, Value)> = selected.into_iter().rev().collect();
        let per_turn_cap = max_content_bytes.min(
            max_response_bytes
                .saturating_sub(CONTINUITY_WRAPPER_ALLOWANCE)
                .max(1),
        );
        let mut formatted_rev: Vec<Value> = Vec::new();
        let mut used = 0usize;
        let mut turns_omitted = 0usize;
        for (idx, (mem, v)) in newest_first.iter().enumerate() {
            let turn = format_continuity_turn(mem, v, per_turn_cap);
            let size = serde_json::to_string(&turn).map_or(0, |s| s.len());
            if idx > 0 && used + size > max_response_bytes {
                turns_omitted = newest_first.len() - idx;
                break;
            }
            used += size;
            formatted_rev.push(turn);
        }
        let tail: Vec<Value> = formatted_rev.into_iter().rev().collect();
        let content_truncated = tail.iter().any(|t| t["content_truncated"] == true);
        let truncated = turns_omitted > 0 || content_truncated;

        // The previous session's latest checkpoint handoff is the most
        // actionable part of "where were we?" — the server's own instructions
        // tell agents to hand off through these fields (next_queue,
        // open_flags, git, tests_green, lease_id), so continuity must surface
        // them or the handoff is write-only (2026-09-17 reviewer finding).
        // Same key and shape as session.digest's checkpoint state. An
        // oversized handoff is replaced by a marker so it cannot blow the
        // response budget; its id reads the full record.
        let (checkpoint, checkpoint_id) = match latest_checkpoint_handoff(&self.store, &prev_id)? {
            Some((id, _, handoff)) => {
                let bytes = serde_json::to_string(&handoff).map_or(0, |s| s.len());
                if bytes > max_response_bytes {
                    (
                        json!({
                            "truncated": true,
                            "bytes": bytes,
                            "hint": format!(
                                "checkpoint handoff exceeds the {max_response_bytes} B budget — read the full record with memory.read id={id}"
                            ),
                        }),
                        Value::String(id),
                    )
                } else {
                    (handoff, Value::String(id))
                }
            }
            None => (Value::Null, Value::Null),
        };

        let mut response = json!({
            "status": "success",
            "previous_session": prev_id,
            "count": tail.len(),
            "turns": tail,
            "checkpoint": checkpoint,
            "checkpoint_id": checkpoint_id,
            "truncated": truncated,
            "turns_omitted": turns_omitted,
            "max_content_bytes": per_turn_cap,
            "max_response_bytes": max_response_bytes,
        });
        if truncated {
            response["hint"] = json!(format!(
                "continuity output is bounded (per-turn cap {per_turn_cap} B, turns budget \
                 {max_response_bytes} B). Every turn carries memory_id; read the exact \
                 original with memory.read id=<memory_id>."
            ));
        }
        Ok(response)
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
            if let Some((_, _, cp)) = latest_checkpoint_handoff(&self.store, &session_id)? {
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
    search: Option<Arc<wm_memory::SearchEngine>>,
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
            search: None,
        }
    }

    /// Index writes at write time (2026-09-15 review finding).
    #[must_use]
    pub fn with_search(mut self, search: Option<Arc<wm_memory::SearchEngine>>) -> Self {
        self.search = search;
        self
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
                super::common::index_memory(&self.store, self.search.as_deref(), &mem);
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
                super::common::index_memory(&self.store, self.search.as_deref(), &updated);
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

/// The `track:<slug>` tag on a memory, if present.
fn track_of(mem: &Memory) -> Option<&str> {
    mem.metadata
        .tags
        .iter()
        .find_map(|t| t.strip_prefix("track:"))
}

/// `session.track_log` — read the per-track implementation log.
///
/// Tracks are the machine-readable form of the doc-level track ledger:
/// `session.record` / `session.checkpoint` tag entries with `track:<slug>`,
/// and this tool reads them back. With `track`/`tracks` it returns the merged
/// chronological log plus the latest checkpoint handoff per track; with
/// neither it returns an overview of every track (entry count, last activity,
/// latest preview) — the orchestrator's re-read surface for directional
/// alignment across related tracks. The alignment verdict is the reader's;
/// this tool supplies the log and staleness facts.
pub struct SessionTrackLogTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionTrackLogTool {
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
impl Tool for SessionTrackLogTool {
    fn name(&self) -> &str {
        "session.track_log"
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
                "track": super::common::str_prop("Track slug to read (recorded via session.record/session.checkpoint 'track')"),
                "tracks": super::common::str_array_prop("Multiple track slugs — merged chronologically (the related-ticket review view)"),
                "since": super::common::str_prop("Time-range floor: epoch seconds, RFC 3339, or YYYY-MM-DD"),
                "until": super::common::str_prop("Time-range ceiling: epoch seconds, RFC 3339, or YYYY-MM-DD"),
                "limit": super::common::positive_int_prop("Max entries returned per track, most recent kept (default 100)"),
                "include_superseded": {
                    "type": "boolean",
                    "description": "Include superseded turns (default false — the current story only)."
                },
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Read the per-track implementation log — turns and checkpoints tagged with a track slug. Args: track (single) or tracks (array, merged chronologically), since/until, limit (default 100, most recent kept per track), include_superseded. With neither track nor tracks: an overview of every track (entry count, last activity, latest preview) for cross-track alignment review."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let mut requested: Vec<String> = Vec::new();
        if let Some(track) = args.get("track").and_then(Value::as_str) {
            validate_track(track)?;
            requested.push(track.to_string());
        }
        if let Some(tracks) = args.get("tracks").and_then(Value::as_array) {
            for t in tracks {
                let t = t.as_str().ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("'tracks' entries must be strings".into())
                })?;
                validate_track(t)?;
                if !requested.iter().any(|r| r == t) {
                    requested.push(t.to_string());
                }
            }
        }
        let limit = args
            .get("limit")
            .and_then(Value::as_u64)
            .unwrap_or(100)
            .clamp(1, 1000) as usize;
        let include_superseded = args
            .get("include_superseded")
            .and_then(Value::as_bool)
            .unwrap_or(false);

        // Same time-bound contract as replay/continuity/digest: invalid
        // bounds are a caller error, never silence.
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

        type Entries = std::collections::BTreeMap<String, Vec<(DateTime<Utc>, Value)>>;
        let mut by_track: Entries = std::collections::BTreeMap::new();
        let mut latest_checkpoint: std::collections::BTreeMap<String, (DateTime<Utc>, Value)> =
            std::collections::BTreeMap::new();

        for mem in &self.store.scan_all(Galaxy::Sessions)? {
            let Some(track) = track_of(mem) else { continue };
            if !requested.is_empty() && !requested.iter().any(|r| r == track) {
                continue;
            }
            if !include_superseded
                && mem
                    .metadata
                    .tags
                    .iter()
                    .any(|t| t.starts_with("superseded-by:"))
            {
                continue;
            }
            let created_at = mem.metadata.created_at;
            if since.is_some_and(|t| created_at < t) || until.is_some_and(|t| created_at > t) {
                continue;
            }
            let entry = if let Some(turn) = turn_json(mem) {
                Some(json!({
                    "kind": "turn",
                    "track": track,
                    "session_id": turn.get("session_id"),
                    "sequence": turn.get("sequence"),
                    "role": turn.get("role"),
                    "turn_type": turn.get("turn_type"),
                    "importance": turn.get("importance"),
                    "created_at": created_at.to_rfc3339(),
                    "content": turn.get("content"),
                }))
            } else if mem.metadata.tags.contains(&"checkpoint".to_string()) {
                serde_json::from_str::<Value>(&mem.content)
                    .ok()
                    .map(|parsed| {
                        json!({
                            "kind": "checkpoint",
                            "track": track,
                            "session_id": parsed.get("session_id"),
                            "label": parsed.get("label"),
                            "created_at": created_at.to_rfc3339(),
                            "handoff": parsed.get("handoff"),
                        })
                    })
            } else {
                None
            };
            let Some(entry) = entry else { continue };
            if entry["kind"] == "checkpoint" {
                latest_checkpoint
                    .entry(track.to_string())
                    .and_modify(|(ts, existing)| {
                        if created_at > *ts {
                            *ts = created_at;
                            *existing = entry.clone();
                        }
                    })
                    .or_insert_with(|| (created_at, entry.clone()));
            }
            by_track
                .entry(track.to_string())
                .or_default()
                .push((created_at, entry));
        }

        let now = Utc::now();
        let overview = requested.is_empty();
        let track_names: Vec<String> = if overview {
            by_track.keys().cloned().collect()
        } else {
            requested
        };
        let mut tracks: Vec<Value> = Vec::with_capacity(track_names.len());
        for track in track_names {
            let mut list = by_track.remove(&track).unwrap_or_default();
            list.sort_by_key(|(ts, _)| *ts);
            let entry_count = list.len();
            let last_activity = list.last().map(|(ts, _)| *ts);
            let latest_entry = list.last().map(|(_, e)| {
                json!({
                    "kind": e.get("kind"),
                    "turn_type": e.get("turn_type"),
                    "label": e.get("label"),
                    "preview": e
                        .get("content")
                        .and_then(Value::as_str)
                        .map(|s| s.chars().take(160).collect::<String>()),
                })
            });
            if list.len() > limit {
                list.drain(0..list.len() - limit);
            }
            let mut out = json!({
                "track": track,
                "known": entry_count > 0,
                "entry_count": entry_count,
                "returned": list.len(),
                "last_activity_at": last_activity.map(|t| t.to_rfc3339()),
                "age_seconds": last_activity.map(|t| (now - t).num_seconds().max(0)),
                "latest_checkpoint": latest_checkpoint.get(&track).map(|(ts, cp)| {
                    json!({
                        "created_at": ts.to_rfc3339(),
                        "entry": cp,
                    })
                }),
            });
            if overview {
                out["latest_entry"] = latest_entry.unwrap_or(Value::Null);
            } else {
                out["entries"] = Value::Array(list.into_iter().map(|(_, e)| e).collect());
            }
            tracks.push(out);
        }

        Ok(json!({
            "status": "success",
            "mode": if overview { "overview" } else { "log" },
            "track_count": tracks.len(),
            "tracks": tracks,
            "disclosure": "directional alignment is the reader's judgment — this view supplies the log, the checkpoint handoff, and staleness facts (age_seconds)",
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
        .register(Arc::new(
            SessionRecordTool::new(store.clone()).with_search(search.clone()),
        ))
        .register(Arc::new(SessionReplayTool::new(store.clone())))
        .register(Arc::new(SessionContinuityTool::new(store.clone())))
        .register(Arc::new(SessionTrackLogTool::new(store.clone())))
        .register(Arc::new(
            SessionHandoffTool::new(store.clone()).with_search(search.clone()),
        ))
        .register(Arc::new(SessionExportTool::new(store.clone())))
        .register(Arc::new(SessionImportTool::new(store.clone(), search)))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::expansion::session::SessionCheckpointNodiscoveryTool;

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
    async fn replay_omitted_session_id_uses_latest_session_start() {
        let store = test_store();
        // Session-local sequence numbers intentionally collide here. The
        // omitted-id path must select by session_start.created_at before it
        // ever orders turns, rather than combining both conversations.
        let older = start_session_aged(&store, 120);
        record_aged_turn(&store, &older, 0, "older-session-only");
        let latest = start_session_aged(&store, 60);
        record_aged_turn(&store, &latest, 0, "latest-session-only");

        let replay = SessionReplayTool::new(store);
        let mut ctx = Context::default();

        let omitted = replay
            .call(&mut ctx, json!({"mode": "full"}))
            .await
            .unwrap();
        assert_eq!(omitted["session_id"], latest);
        assert_eq!(
            omitted["count"], 1,
            "omitted id must not combine sessions: {omitted}"
        );
        assert_eq!(omitted["turns"][0]["content"], "latest-session-only");

        let explicit_older = replay
            .call(&mut ctx, json!({"session_id": older, "mode": "full"}))
            .await
            .unwrap();
        assert_eq!(explicit_older["session_id"], older);
        assert_eq!(explicit_older["count"], 1);
        assert_eq!(explicit_older["turns"][0]["content"], "older-session-only");
    }

    #[tokio::test]
    async fn replay_without_any_session_remains_truthfully_empty() {
        let replay = SessionReplayTool::new(test_store());
        let mut ctx = Context::default();

        let value = replay.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(value["status"], "success");
        assert_eq!(value["session_id"], Value::Null);
        assert_eq!(value["count"], 0);
        assert_eq!(value["turns"], json!([]));
    }

    #[tokio::test]
    async fn replay_omitted_id_does_not_combine_orphan_turns_without_a_start() {
        let store = test_store();
        // Explicit session IDs are supported by session.record even before a
        // start record exists. Omission must not turn these recovery records
        // into a synthetic combined "latest" session.
        record_aged_turn(&store, "orphan-a", 0, "orphan-a-only");
        record_aged_turn(&store, "orphan-b", 0, "orphan-b-only");

        let replay = SessionReplayTool::new(store);
        let mut ctx = Context::default();

        let omitted = replay.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(omitted["session_id"], Value::Null);
        assert_eq!(
            omitted["count"], 0,
            "omitted id must not combine orphans: {omitted}"
        );
        assert_eq!(omitted["turns"], json!([]));

        let explicit = replay
            .call(&mut ctx, json!({"session_id": "orphan-a"}))
            .await
            .unwrap();
        assert_eq!(explicit["session_id"], "orphan-a");
        assert_eq!(explicit["count"], 1);
        assert_eq!(explicit["turns"][0]["content"], "orphan-a-only");
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
    async fn continuity_skips_empty_newest_session() {
        // First-run feedback (2026-09-13): session A records a decision, the
        // user starts an empty session B, and `session.continuity` with no
        // arguments must not answer from the empty B — it must recall A.
        let store = test_store();
        let sid1 = start_session(&store);
        record_aged_turn(
            &store,
            &sid1,
            0,
            "Decision: use SQLite for the report cache",
        );
        let sid2 = start_session(&store); // empty newest session, never named

        let continuity = SessionContinuityTool::new(store);
        let mut ctx = Context::default();
        let v = continuity.call(&mut ctx, json!({"n": 5})).await.unwrap();
        assert_ne!(
            v["previous_session"], sid2,
            "empty newest session must be skipped: {v}"
        );
        assert_eq!(v["previous_session"], sid1);
        assert_eq!(v["count"], 1);
        assert!(
            v["turns"][0]["content"]
                .as_str()
                .unwrap()
                .contains("SQLite")
        );
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

    /// 2026-09-21 reviewer finding: a 100,000-char turn produced a ~200 KB
    /// JSON-RPC response with no truncation or budget. Continuity must bound
    /// per-turn content and the response, disclose it, and keep the exact
    /// original reachable by id.
    #[tokio::test]
    async fn continuity_bounds_pathological_turn_content() {
        let store = test_store();
        let sid = start_session(&store);
        let huge = "A".repeat(100_000);
        let first = SessionRecordTool::new(store.clone())
            .call(
                &mut Context::default(),
                json!({"role": "ai", "content": huge, "session_id": sid}),
            )
            .await
            .unwrap();
        let turn_id = first["memory_id"].as_str().unwrap().to_string();
        let current = start_session(&store);

        let continuity = SessionContinuityTool::new(store.clone());
        let v = continuity
            .call(
                &mut Context::default(),
                json!({"current_session_id": current}),
            )
            .await
            .unwrap();

        assert_eq!(v["count"], 1);
        assert_eq!(v["truncated"], true);
        assert_eq!(v["turns"][0]["content_truncated"], true);
        assert_eq!(v["turns"][0]["content_bytes"], 100_000);
        assert_eq!(v["turns"][0]["memory_id"], turn_id);
        let cap = v["max_content_bytes"].as_u64().unwrap() as usize;
        assert!(v["turns"][0]["content"].as_str().unwrap().len() <= cap);
        let wire = serde_json::to_string(&v).unwrap();
        assert!(
            wire.len() <= CONTINUITY_DEFAULT_MAX_RESPONSE_BYTES + 2048,
            "response must stay near the default budget ({} bytes)",
            wire.len()
        );
        assert!(v["hint"].as_str().unwrap().contains("memory.read"));

        // Truncation is display-only: the canonical record is intact.
        let id = uuid::Uuid::parse_str(&turn_id).unwrap();
        let mem = store.get(Galaxy::Sessions, id).unwrap().unwrap();
        assert_eq!(mem.content.matches('A').count(), 100_000);
    }

    #[tokio::test]
    async fn continuity_budget_keeps_newest_turns_and_reports_omissions() {
        let store = test_store();
        let sid = start_session(&store);
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();
        for i in 0..10 {
            record
                .call(
                    &mut ctx,
                    json!({
                        "role": "ai",
                        "content": format!("turn-{i}-{}", "x".repeat(5_000)),
                        "session_id": sid,
                    }),
                )
                .await
                .unwrap();
        }
        let current = start_session(&store);
        let continuity = SessionContinuityTool::new(store.clone());
        let v = continuity
            .call(
                &mut ctx,
                json!({"current_session_id": current, "max_response_bytes": 12_288}),
            )
            .await
            .unwrap();

        let omitted = v["turns_omitted"].as_u64().unwrap();
        assert!(omitted > 0, "budget must omit older turns: {v}");
        assert_eq!(v["truncated"], true);
        let kept = v["turns"].as_array().unwrap();
        assert!(!kept.is_empty());
        let seqs: Vec<u64> = kept
            .iter()
            .map(|t| t["sequence"].as_u64().unwrap())
            .collect();
        assert_eq!(*seqs.last().unwrap(), 10, "newest turn must be kept");
        assert!(
            seqs.windows(2).all(|w| w[0] < w[1]),
            "turns stay chronological: {seqs:?}"
        );
        for t in kept {
            assert!(t["memory_id"].as_str().is_some(), "exact-read id required");
        }
        let wire = serde_json::to_string(&v).unwrap();
        assert!(
            wire.len() <= 12_288 + 2048,
            "response must stay near the requested budget ({} bytes)",
            wire.len()
        );
    }

    #[tokio::test]
    async fn continuity_budget_args_are_validated() {
        let store = test_store();
        let continuity = SessionContinuityTool::new(store);
        let mut ctx = Context::default();
        let err = continuity
            .call(&mut ctx, json!({"max_response_bytes": 1}))
            .await
            .unwrap_err();
        assert!(err.to_string().contains("continuity budgets"), "got: {err}");
        let err = continuity
            .call(&mut ctx, json!({"max_content_bytes": "big"}))
            .await
            .unwrap_err();
        assert!(err.to_string().contains("must be an integer"), "got: {err}");
    }

    /// 2026-09-21 reviewer finding: recording into a nonexistent session id
    /// returned success and left an orphan turn (Memories 1, Sessions 0).
    #[tokio::test]
    async fn record_rejects_unknown_session_ids() {
        let store = test_store();
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();

        let err = record
            .call(
                &mut ctx,
                json!({"content": "orphan turn probe",
                        "session_id": "00000000-0000-0000-0000-000000000999"}),
            )
            .await
            .unwrap_err();
        assert!(
            err.to_string().contains("no session found"),
            "unknown id must be refused: {err}"
        );
        assert!(
            store.scan_all(Galaxy::Sessions).unwrap().is_empty(),
            "refused record must not write anything"
        );

        let err = record
            .call(
                &mut ctx,
                json!({"content": "x", "session_id": "not-a-uuid"}),
            )
            .await
            .unwrap_err();
        assert!(
            err.to_string().contains("invalid session_id"),
            "malformed id must be a caller error: {err}"
        );

        // A real started session still accepts turns.
        let sid = start_session(&store);
        let ok = record
            .call(&mut ctx, json!({"content": "real turn", "session_id": sid}))
            .await
            .unwrap();
        assert_eq!(ok["status"], "success");
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

    /// 2026-09-15 review: session writes must be indexed AT WRITE TIME, or a
    /// live writable server accumulates index drift until the next heal and
    /// `wm status` reports DEGRADED for a self-healing condition.
    #[tokio::test]
    async fn session_record_indexes_at_write_time() {
        let dir = tempfile::tempdir().unwrap();
        let lmdb = dir.path().join("lmdb");
        std::fs::create_dir_all(&lmdb).unwrap();
        let store = Arc::new(MemoryStore::open_default(&lmdb).unwrap());
        let tantivy = dir.path().join("tantivy");
        std::fs::create_dir_all(&tantivy).unwrap();
        let search = Arc::new(wm_memory::SearchEngine::open(&tantivy).unwrap());

        let sid = start_session(&store);
        let mut ctx = Context::default();
        SessionRecordTool::new(store.clone())
            .with_search(Some(search.clone()))
            .call(
                &mut ctx,
                json!({"role": "ai", "turn_type": "decision", "importance": 0.7,
                        "content": "amber lighthouse protocol engaged", "session_id": sid}),
            )
            .await
            .unwrap();

        let docs = search.count_docs_in_galaxy("sessions").unwrap();
        assert!(
            docs >= 1,
            "session.record must index its write immediately (docs={docs})"
        );
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

    /// H1 (2026-09-20 review): 100 simultaneous `session.record` writers used
    /// to yield 43 unique sequences (allocation was read-count-then-write).
    /// Sequences are now allocated inside the record's own write transaction.
    #[tokio::test(flavor = "multi_thread", worker_threads = 8)]
    async fn concurrent_record_writers_get_unique_contiguous_sequences() {
        const N: usize = 100;
        let store = test_store();
        let sid = start_session(&store);
        let tool = Arc::new(SessionRecordTool::new(store));

        let mut handles = Vec::with_capacity(N);
        for i in 0..N {
            let tool = Arc::clone(&tool);
            let sid = sid.clone();
            handles.push(tokio::spawn(async move {
                let mut ctx = Context::default();
                let v = tool
                    .call(
                        &mut ctx,
                        json!({
                            "session_id": sid,
                            "role": "ai",
                            "turn_type": "message",
                            "content": format!("concurrent turn {i}"),
                        }),
                    )
                    .await
                    .unwrap();
                v["sequence"].as_u64().expect("sequence in response")
            }));
        }

        let mut sequences = Vec::with_capacity(N);
        for handle in handles {
            sequences.push(handle.await.unwrap());
        }
        sequences.sort_unstable();
        assert_eq!(
            sequences,
            (1..=N as u64).collect::<Vec<_>>(),
            "{N} concurrent session.record writers must get 1..={N}"
        );
    }

    /// The supersede ordering contract: the replacement turn commits first,
    /// then the old turn is marked. Default replay hides the old turn;
    /// include_superseded preserves the contradiction.
    #[tokio::test]
    async fn supersede_marks_old_turn_and_hides_it_by_default() {
        let store = test_store();
        let sid = start_session(&store);
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();

        let first = record
            .call(
                &mut ctx,
                json!({"session_id": sid, "content": "we chose A"}),
            )
            .await
            .unwrap();
        let first_id = first["memory_id"].as_str().unwrap().to_string();
        let second = record
            .call(
                &mut ctx,
                json!({"session_id": sid, "content": "we chose B", "supersedes": first_id}),
            )
            .await
            .unwrap();
        assert_eq!(second["sequence"], 2);

        // Old turn is marked, so default retrieval prefers the new record.
        let old = store
            .get(
                wm_core::Galaxy::Sessions,
                uuid::Uuid::parse_str(&first_id).unwrap(),
            )
            .unwrap()
            .unwrap();
        assert!(
            old.metadata
                .tags
                .iter()
                .any(|t| t.starts_with("superseded-by:")),
            "old turn must carry superseded-by: {:?}",
            old.metadata.tags
        );

        let replay = SessionReplayTool::new(store.clone());
        let visible = replay
            .call(&mut ctx, json!({"mode": "full", "session_id": sid}))
            .await
            .unwrap();
        assert_eq!(visible["count"], 1, "default view shows the current story");
        assert_eq!(visible["turns"][0]["content"], "we chose B");

        let full = replay
            .call(
                &mut ctx,
                json!({"mode": "full", "session_id": sid, "include_superseded": true}),
            )
            .await
            .unwrap();
        assert_eq!(full["count"], 2, "history stays queryable");
    }

    #[tokio::test]
    async fn record_requires_content_and_valid_role() {
        let store = test_store();
        let sid = start_session(&store);
        let tool = SessionRecordTool::new(store);
        let mut ctx = Context::default();
        assert!(
            tool.call(&mut ctx, json!({"role": "system", "content": "x"}))
                .await
                .is_err()
        );
        // 2026-09-19 review: blank/whitespace content and unknown turn
        // types are caller errors, not historical facts.
        for bad in [json!(""), json!("   "), json!("\n\t")] {
            let err = tool
                .call(&mut ctx, json!({"content": bad, "session_id": sid}))
                .await
                .unwrap_err();
            assert!(
                err.to_string().contains("content"),
                "content={bad:?}: {err}"
            );
        }
        let err = tool
            .call(
                &mut ctx,
                json!({"content": "x", "session_id": sid, "turn_type": "observation"}),
            )
            .await
            .unwrap_err();
        assert!(err.to_string().contains("turn_type"), "{err}");
        // The documented vocabulary still lands.
        let v = tool
            .call(
                &mut ctx,
                json!({"content": "x", "session_id": sid, "turn_type": "context"}),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success", "{v}");
    }

    /// 2026-09-19 review: importance is defined on 0.0-1.0; this path used
    /// to accept 1.5 and silently store 1.0 while memory.create/update
    /// rejected the same value. Out-of-range is a caller error here too.
    #[tokio::test]
    async fn record_rejects_out_of_range_importance() {
        let store = test_store();
        let sid = start_session(&store);
        let record = SessionRecordTool::new(store);
        let mut ctx = Context::default();
        for bad in [json!(1.5), json!(999), json!(-0.25), json!("2.0")] {
            let err = record
                .call(
                    &mut ctx,
                    json!({"content": "x", "session_id": sid, "importance": bad}),
                )
                .await
                .unwrap_err();
            assert!(
                err.to_string().contains("importance"),
                "importance={bad} must be rejected, got: {err}"
            );
        }
        // Boundaries and a valid value still land (string forms included —
        // the same permissive input contract as memory.create/update).
        for good in [json!(0.0), json!(1.0), json!(0.75), json!("0.4")] {
            let v = record
                .call(
                    &mut ctx,
                    json!({"content": "x", "session_id": sid, "importance": good}),
                )
                .await
                .unwrap();
            assert_eq!(v["status"], "success", "{v}");
        }
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
    async fn record_rejects_invalid_track_slug() {
        let store = test_store();
        let sid = start_session(&store);
        let record = SessionRecordTool::new(store);
        let mut ctx = Context::default();
        let mut bad = vec![
            String::new(),
            "Track-A".to_string(),
            "has space".to_string(),
            "-leading".to_string(),
        ];
        bad.push("x".repeat(TRACK_MAX_LEN + 1));
        for bad in &bad {
            let err = record
                .call(
                    &mut ctx,
                    json!({"content": "x", "session_id": sid, "track": bad}),
                )
                .await
                .unwrap_err()
                .to_string();
            assert!(err.contains("invalid track"), "slug {bad:?}: {err}");
        }
        // Valid slugs pass: digits start, dash/dot/slash/underscore.
        let ok = record
            .call(
                &mut ctx,
                json!({"content": "x", "session_id": sid, "track": "wmv9/harness-2.1_a"}),
            )
            .await
            .unwrap();
        assert_eq!(ok["status"], "success");
    }

    #[tokio::test]
    async fn track_log_reads_recorded_turns_per_track() {
        let store = test_store();
        let sid = start_session(&store);
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();
        for (track, content) in [
            ("harness-2", "harness: schema check landed"),
            ("safety-a", "safety: mask gate landed"),
            ("harness-2", "harness: manifest regen done"),
        ] {
            record
                .call(
                    &mut ctx,
                    json!({
                        "role": "ai",
                        "content": content,
                        "session_id": sid,
                        "track": track,
                        "turn_type": "summary",
                    }),
                )
                .await
                .unwrap();
        }

        let log = SessionTrackLogTool::new(store);
        let v = log
            .call(&mut ctx, json!({"track": "harness-2"}))
            .await
            .unwrap();
        assert_eq!(v["mode"], "log");
        assert_eq!(v["tracks"][0]["track"], "harness-2");
        assert_eq!(v["tracks"][0]["entry_count"], 2);
        assert_eq!(v["tracks"][0]["returned"], 2);
        assert_eq!(
            v["tracks"][0]["entries"][0]["content"],
            "harness: schema check landed"
        );
        assert_eq!(
            v["tracks"][0]["entries"][1]["content"],
            "harness: manifest regen done"
        );
        assert!(v["tracks"][0]["age_seconds"].as_i64().unwrap() >= 0);

        // Overview lists every track with last-activity facts, no entries.
        let all = log.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(all["mode"], "overview");
        assert_eq!(all["track_count"], 2);
        let names: Vec<&str> = all["tracks"]
            .as_array()
            .unwrap()
            .iter()
            .map(|t| t["track"].as_str().unwrap())
            .collect();
        assert_eq!(names, vec!["harness-2", "safety-a"]);
        assert!(all["tracks"][0]["entries"].is_null());
        assert_eq!(all["tracks"][0]["latest_entry"]["turn_type"], "summary");
        assert!(
            all["tracks"][0]["latest_entry"]["preview"]
                .as_str()
                .unwrap()
                .contains("manifest regen")
        );

        // An unknown track is disclosed as empty, never fabricated.
        let unknown = log
            .call(&mut ctx, json!({"track": "never-seen"}))
            .await
            .unwrap();
        assert_eq!(unknown["tracks"][0]["known"], false);
        assert_eq!(unknown["tracks"][0]["entry_count"], 0);
    }

    #[tokio::test]
    async fn track_log_merges_related_tracks_and_filters_time() {
        let store = test_store();
        let sid = start_session(&store);
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();
        for (track, content) in [
            ("harness-2", "old harness note"),
            ("safety-a", "safety note"),
            ("harness-2", "new harness note"),
        ] {
            record
                .call(
                    &mut ctx,
                    json!({"role": "ai", "content": content, "session_id": sid, "track": track}),
                )
                .await
                .unwrap();
        }
        // Age the first harness turn out of the since window.
        for mut mem in store.scan_all(Galaxy::Sessions).unwrap() {
            if mem.content.contains("old harness note") {
                mem.metadata.created_at = Utc::now() - chrono::Duration::days(3);
                store.put(Galaxy::Sessions, &mem).unwrap();
            }
        }

        let log = SessionTrackLogTool::new(store);
        let cutoff = (Utc::now() - chrono::Duration::days(1))
            .format("%Y-%m-%d")
            .to_string();
        let v = log
            .call(
                &mut ctx,
                json!({"tracks": ["harness-2", "safety-a"], "since": cutoff}),
            )
            .await
            .unwrap();
        assert_eq!(v["track_count"], 2);
        let harness = &v["tracks"][0];
        assert_eq!(harness["track"], "harness-2");
        assert_eq!(harness["entry_count"], 1, "aged turn filtered: {v}");
        assert_eq!(harness["entries"][0]["content"], "new harness note");
        let safety = &v["tracks"][1];
        assert_eq!(safety["track"], "safety-a");
        assert_eq!(safety["entry_count"], 1);

        // Bad slug in the array is a caller error, not a silent miss.
        let err = log
            .call(&mut ctx, json!({"tracks": ["harness-2", "Bad Slug"]}))
            .await
            .unwrap_err()
            .to_string();
        assert!(err.contains("invalid track"), "{err}");
    }

    #[tokio::test]
    async fn track_log_hides_superseded_turns_by_default() {
        let store = test_store();
        let sid = start_session(&store);
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();
        let first = record
            .call(
                &mut ctx,
                json!({"role": "ai", "content": "v1 estimate", "session_id": sid,
                       "track": "bench", "turn_type": "summary"}),
            )
            .await
            .unwrap();
        record
            .call(
                &mut ctx,
                json!({"role": "ai", "content": "v2 estimate", "session_id": sid,
                       "track": "bench", "turn_type": "summary",
                       "supersedes": first["memory_id"]}),
            )
            .await
            .unwrap();

        let log = SessionTrackLogTool::new(store);
        let v = log.call(&mut ctx, json!({"track": "bench"})).await.unwrap();
        assert_eq!(v["tracks"][0]["entry_count"], 1);
        assert_eq!(v["tracks"][0]["entries"][0]["content"], "v2 estimate");
        let all = log
            .call(
                &mut ctx,
                json!({"track": "bench", "include_superseded": true}),
            )
            .await
            .unwrap();
        assert_eq!(all["tracks"][0]["entry_count"], 2);
    }

    #[tokio::test]
    async fn checkpoint_track_lands_in_track_log() {
        let store = test_store();
        let sid = start_session(&store);
        let checkpoint = SessionCheckpointNodiscoveryTool::new(store.clone());
        let mut ctx = Context::default();
        let v = checkpoint
            .call(
                &mut ctx,
                json!({
                    "session_id": sid,
                    "track": "harness-2",
                    "label": "slice2-done",
                    "next_queue": ["regen manifest", "push after ceremony"],
                    "open_flags": ["none"],
                }),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");

        let log = SessionTrackLogTool::new(store);
        let out = log
            .call(&mut ctx, json!({"track": "harness-2"}))
            .await
            .unwrap();
        assert_eq!(out["tracks"][0]["entry_count"], 1);
        assert_eq!(out["tracks"][0]["entries"][0]["kind"], "checkpoint");
        assert_eq!(
            out["tracks"][0]["latest_checkpoint"]["entry"]["label"],
            "slice2-done"
        );
        assert_eq!(
            out["tracks"][0]["latest_checkpoint"]["entry"]["handoff"]["next_queue"][0],
            "regen manifest"
        );

        // Invalid checkpoint track is refused before any write.
        let err = checkpoint
            .call(&mut ctx, json!({"session_id": sid, "track": "Bad"}))
            .await
            .unwrap_err()
            .to_string();
        assert!(err.contains("invalid track"), "{err}");
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
        assert!(
            v["checkpoint"].is_null() && v["checkpoint_id"].is_null(),
            "no checkpoint recorded — the fields must be present but null: {v}"
        );
    }

    #[tokio::test]
    async fn continuity_surfaces_latest_checkpoint_handoff() {
        // Reviewer finding (2026-09-17): session.checkpoint's structured
        // handoff was write-only — continuity returned the summary turn but
        // dropped next_queue/open_flags, the most actionable part of the
        // handoff. The latest checkpoint for the previous session must ride
        // along with the turn tail.
        let store = test_store();
        let sid1 = start_session(&store);
        let record = SessionRecordTool::new(store.clone());
        let mut ctx = Context::default();
        record
            .call(
                &mut ctx,
                json!({"role": "ai", "turn_type": "summary", "importance": 0.9,
                        "content": "seam work done", "session_id": sid1}),
            )
            .await
            .unwrap();

        let seed_checkpoint = |handoff: Value, age_secs: i64| {
            let mut cp = Memory::new(
                Galaxy::Sessions,
                json!({
                    "type": "checkpoint",
                    "session_id": sid1,
                    "label": "wrap",
                    "data": {},
                    "handoff": handoff,
                })
                .to_string(),
            );
            cp.metadata.tags = vec!["session".into(), "checkpoint".into()];
            cp.metadata.created_at = Utc::now() - chrono::Duration::seconds(age_secs);
            store.put(Galaxy::Sessions, &cp).unwrap();
            cp.metadata.id.to_string()
        };
        seed_checkpoint(
            json!({"next_queue": ["stale task"], "open_flags": ["stale flag"]}),
            120,
        );
        let newest_id = seed_checkpoint(
            json!({
                "git": {"commit": "abc1234", "branch": "main", "dirty_count": 0},
                "tests_green": true,
                "next_queue": ["fuzz malformed headers", "verify seal"],
                "open_flags": ["header length cap unresolved"],
            }),
            0,
        );

        let sid2 = start_session(&store);
        let continuity = SessionContinuityTool::new(store);
        let v = continuity
            .call(&mut ctx, json!({"current_session_id": sid2}))
            .await
            .unwrap();
        assert_eq!(v["previous_session"], sid1);
        assert_eq!(
            v["checkpoint"]["next_queue"][0], "fuzz malformed headers",
            "the latest checkpoint must win over an older one: {v}"
        );
        assert_eq!(
            v["checkpoint"]["open_flags"][0], "header length cap unresolved",
            "open flags must survive the handoff through continuity: {v}"
        );
        assert_eq!(v["checkpoint"]["git"]["commit"], "abc1234");
        assert_eq!(v["checkpoint"]["tests_green"], true);
        assert_eq!(v["checkpoint_id"].as_str().unwrap(), newest_id);
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

    #[tokio::test]
    async fn lossless_replay_binds_explicit_session_chunks_and_detects_stale_view() {
        let store = test_store();
        let older = start_session_aged(&store, 60);
        let newer = start_session_aged(&store, 0);
        let content = format!("prefix {} DISTINCT-FACT-AFTER-120", "é".repeat(9000));
        let mut turn = Memory::new(Galaxy::Sessions, json!({"type":"session_turn","session_id":older,"sequence":1,"timestamp":1_i64,"content":content}).to_string());
        turn.metadata.tags = vec!["session".into(), "turn".into(), format!("session:{older}")];
        store.put(Galaxy::Sessions, &turn).unwrap();
        let mut other = Memory::new(Galaxy::Sessions, json!({"type":"session_turn","session_id":newer,"sequence":1,"timestamp":1_i64,"content":"newer-only"}).to_string());
        other.metadata.tags = vec!["session".into(), "turn".into(), format!("session:{newer}")];
        store.put(Galaxy::Sessions, &other).unwrap();
        let replay = SessionReplayTool::new(store.clone());
        let mut ctx = Context::default();
        let mut response = replay
            .call(
                &mut ctx,
                json!({"mode":"lossless","session_id":older,"page_size":1,"max_wire_bytes":2048}),
            )
            .await
            .unwrap();
        assert_eq!(response["session_id"], older);
        assert!(response["records"][0].get("chunk").is_some());
        let mut bytes = Vec::new();
        loop {
            assert!(serde_json::to_vec(&response).unwrap().len() <= 2048);
            for record in response["records"].as_array().unwrap() {
                if let Some(chunk) = record.get("chunk") {
                    assert_eq!(chunk["byte_offset"].as_u64().unwrap() as usize, bytes.len());
                    bytes.extend(base64_decode(chunk["data_b64"].as_str().unwrap()).unwrap());
                } else {
                    bytes.extend(record["content"].as_str().unwrap().as_bytes());
                }
            }
            if response["complete"] == true {
                assert!(response["next_cursor"].is_null());
                break;
            }
            let cursor = response["next_cursor"].as_str().unwrap();
            response = replay.call(&mut ctx, json!({"mode":"lossless","session_id":older,"page_size":1,"max_wire_bytes":2048,"cursor":cursor})).await.unwrap();
        }
        assert_eq!(String::from_utf8(bytes).unwrap(), content);
        let first = replay
            .call(
                &mut ctx,
                json!({"mode":"lossless","session_id":older,"page_size":1,"max_wire_bytes":2048}),
            )
            .await
            .unwrap();
        let stale_cursor = first["next_cursor"].as_str().unwrap().to_string();
        let mut appended = Memory::new(Galaxy::Sessions, json!({"type":"session_turn","session_id":older,"sequence":2,"timestamp":2_i64,"content":"later"}).to_string());
        appended.metadata.tags = vec!["session".into(), "turn".into(), format!("session:{older}")];
        store.put(Galaxy::Sessions, &appended).unwrap();
        assert!(replay.call(&mut ctx, json!({"mode":"lossless","session_id":older,"page_size":1,"max_wire_bytes":2048,"cursor":stale_cursor})).await.unwrap_err().to_string().contains("stale_view"));
    }

    fn lossless_fixture_turn(sid: &str, sequence: u64, text: &str) -> Memory {
        let mut m = Memory::new(Galaxy::Sessions, json!({"type":"session_turn","session_id":sid,"sequence":sequence,"timestamp":1_i64,"role":"ai","turn_type":"decision","importance":0.8,"content":text}).to_string());
        m.metadata.tags = vec!["turn".into(), format!("session:{sid}")];
        m
    }

    #[tokio::test]
    async fn lossless_strict_args_and_cursor_prevalidation_before_corrupt_scan() {
        let store = test_store();
        let sid = start_session(&store);
        store
            .put_raw(
                Galaxy::Sessions,
                uuid::Uuid::new_v4().as_bytes(),
                b"not-a-memory",
            )
            .unwrap();
        let replay = SessionReplayTool::new(store);
        for (key, value) in [
            ("include_superseded", json!("false")),
            ("page_size", json!(null)),
            ("page_size", json!(-1)),
            ("max_wire_bytes", json!("2048")),
            ("cursor", json!(false)),
            ("cursor", json!("a€")),
            ("cursor", json!("🔑")),
        ] {
            let mut args = json!({"mode":"lossless","session_id":sid});
            args[key] = value;
            let error = replay
                .call(&mut Context::default(), args)
                .await
                .unwrap_err()
                .to_string();
            assert!(
                error.contains("invalid_args") || error.contains("invalid_cursor"),
                "{key}: {error}"
            );
            assert!(!error.contains("incomplete scan"));
        }
        let error = replay
            .call(
                &mut Context::default(),
                json!({"mode":"lossless","session_id":sid}),
            )
            .await
            .unwrap_err()
            .to_string();
        assert!(error.contains("refusing incomplete scan"));
    }

    #[tokio::test]
    async fn lossless_metadata_staleness_settings_seek_and_partial_resume() {
        let store = test_store();
        let sid = start_session(&store);
        let mut turn = lossless_fixture_turn(&sid, 1, &"€\n".repeat(2000));
        store.put(Galaxy::Sessions, &turn).unwrap();
        let replay = SessionReplayTool::new(store.clone());
        let args = json!({"mode":"lossless","session_id":sid,"page_size":1,"max_wire_bytes":2048});
        let first = replay
            .call(&mut Context::default(), args.clone())
            .await
            .unwrap();
        let cursor = first["next_cursor"].as_str().unwrap();
        for (key, value) in [("page_size", json!(2)), ("max_wire_bytes", json!(4096))] {
            let mut next = args.clone();
            next["cursor"] = json!(cursor);
            next[key] = value;
            assert!(
                replay
                    .call(&mut Context::default(), next)
                    .await
                    .unwrap_err()
                    .to_string()
                    .contains("invalid_cursor")
            );
        }
        let (view, _, _) = parse_lossless_cursor(cursor, &sid, false, 1, 2048).unwrap();
        // A valid edited cursor is an authorized seek, not a forged-authority bypass.
        let mut seek = args.clone();
        seek["cursor"] = json!(lossless_cursor(
            &sid,
            false,
            1,
            2048,
            &view,
            0,
            turn.content.len() - 2
        ));
        // Placement refers to the inner exact content, not its JSON envelope.
        let inner = serde_json::from_str::<Value>(&turn.content).unwrap()["content"]
            .as_str()
            .unwrap()
            .to_string();
        seek["cursor"] = json!(lossless_cursor(
            &sid,
            false,
            1,
            2048,
            &view,
            0,
            inner.len() - 2
        ));
        let tail = replay.call(&mut Context::default(), seek).await.unwrap();
        assert!(tail["records"][0].get("content").is_none());
        assert_eq!(
            base64_decode(tail["records"][0]["chunk"]["data_b64"].as_str().unwrap()).unwrap(),
            inner.as_bytes()[inner.len() - 2..]
        );
        assert!(tail["next_cursor"].is_null());
        let mut changed = serde_json::from_str::<Value>(&turn.content).unwrap();
        changed["role"] = json!("human");
        turn.content = changed.to_string();
        store.put(Galaxy::Sessions, &turn).unwrap();
        let mut next = args;
        next["cursor"] = json!(cursor);
        assert!(
            replay
                .call(&mut Context::default(), next)
                .await
                .unwrap_err()
                .to_string()
                .contains("stale_view")
        );
    }

    #[tokio::test]
    async fn lossless_visibility_empty_nonturn_ties_and_supersession() {
        let store = test_store();
        let sid = start_session(&store);
        let replay = SessionReplayTool::new(store.clone());
        let mut args = json!({"mode":"lossless","session_id":sid,"page_size":64});
        let empty = replay
            .call(&mut Context::default(), args.clone())
            .await
            .unwrap();
        assert_eq!(empty["records"], json!([]));
        assert!(empty["next_cursor"].is_null());
        assert_eq!(empty["complete"], true);
        let mut a = lossless_fixture_turn(&sid, 1, "");
        let mut b = lossless_fixture_turn(&sid, 1, "second");
        // Old valid turn envelope without the optional session tag remains readable.
        b.metadata.tags.clear();
        let mut hidden = lossless_fixture_turn(&sid, 2, "PRIVATE-SENTINEL");
        hidden.metadata.is_private = true;
        let mut excluded = lossless_fixture_turn(&sid, 3, "EXCLUDED-SENTINEL");
        excluded.metadata.model_exclude = true;
        a.metadata
            .tags
            .push(format!("supersedes:{}", hidden.metadata.id));
        let mut handoff = Memory::new(
            Galaxy::Sessions,
            json!({"type":"session_handoff"}).to_string(),
        );
        handoff.metadata.tags = vec![format!("session:{sid}")];
        store
            .put_batch(
                Galaxy::Sessions,
                &[a.clone(), b.clone(), hidden.clone(), excluded, handoff],
            )
            .unwrap();
        let result = replay
            .call(&mut Context::default(), args.clone())
            .await
            .unwrap();
        let wire = result.to_string();
        assert!(!wire.contains("SENTINEL"));
        assert!(!wire.contains(&hidden.metadata.id.to_string()));
        let mut ids = vec![a.metadata.id.to_string(), b.metadata.id.to_string()];
        ids.sort();
        assert_eq!(
            result["records"]
                .as_array()
                .unwrap()
                .iter()
                .map(|r| r["record_id"].as_str().unwrap().to_string())
                .collect::<Vec<_>>(),
            ids
        );
        a.metadata
            .tags
            .push(format!("superseded-by:{}", b.metadata.id));
        store.put(Galaxy::Sessions, &a).unwrap();
        assert_eq!(
            replay
                .call(&mut Context::default(), args.clone())
                .await
                .unwrap()["records"]
                .as_array()
                .unwrap()
                .len(),
            1
        );
        args["include_superseded"] = json!(true);
        assert_eq!(
            replay.call(&mut Context::default(), args).await.unwrap()["records"]
                .as_array()
                .unwrap()
                .len(),
            2
        );
        let mut start = store
            .get(Galaxy::Sessions, uuid::Uuid::parse_str(&sid).unwrap())
            .unwrap()
            .unwrap();
        start.metadata.model_exclude = true;
        store.put(Galaxy::Sessions, &start).unwrap();
        assert!(
            replay
                .call(
                    &mut Context::default(),
                    json!({"mode":"lossless","session_id":sid})
                )
                .await
                .unwrap_err()
                .to_string()
                .contains("not found")
        );
    }

    #[tokio::test]
    async fn lossless_malformed_selected_turn_fails_and_schema_advertises_mode() {
        let store = test_store();
        let sid = start_session(&store);
        let mut bad = lossless_fixture_turn(&sid, 1, "good");
        bad.content = "{broken".into();
        store.put(Galaxy::Sessions, &bad).unwrap();
        let replay = SessionReplayTool::new(store);
        assert!(
            replay
                .call(
                    &mut Context::default(),
                    json!({"mode":"lossless","session_id":sid})
                )
                .await
                .unwrap_err()
                .to_string()
                .contains("malformed_selected_turn")
        );
        assert!(replay.input_schema().to_string().contains("lossless"));
        assert!(replay.description().contains("explicit session UUID"));
    }

    #[test]
    fn lossless_arbitrary_cursor_text_is_panic_free() {
        use proptest::prelude::*;
        proptest!(|(text in any::<String>())| { let _ = hex_decode(&text); });
        assert!(hex_decode("AB").is_none());
    }

    #[tokio::test]
    async fn lossless_selection_reaches_record_after_ten_thousand_sources() {
        let store = test_store();
        let sid = start_session(&store);
        let mut sources = Vec::new();
        for i in 1..=10_001_u128 {
            let mut m = Memory::new(Galaxy::Sessions, "unrelated".into());
            m.metadata.id = uuid::Uuid::from_u128(i);
            sources.push(m);
        }
        let mut target = lossless_fixture_turn(&sid, 1, "AFTER-TEN-THOUSAND");
        target.metadata.id = uuid::Uuid::from_u128(u128::MAX);
        sources.push(target);
        store.put_batch(Galaxy::Sessions, &sources).unwrap();
        let replay = SessionReplayTool::new(store);
        let result = replay
            .call(
                &mut Context::default(),
                json!({"mode":"lossless","session_id":sid}),
            )
            .await
            .unwrap();
        assert_eq!(result["records"][0]["content"], "AFTER-TEN-THOUSAND");
    }

    #[tokio::test]
    async fn lossless_tag_payload_disagreement_refuses_and_missing_start_is_not_found() {
        let store = test_store();
        let sid = start_session(&store);
        let mut m = lossless_fixture_turn(&uuid::Uuid::new_v4().to_string(), 1, "contradiction");
        m.metadata.tags = vec![format!("session:{sid}")];
        store.put(Galaxy::Sessions, &m).unwrap();
        let replay = SessionReplayTool::new(store);
        assert!(
            replay
                .call(
                    &mut Context::default(),
                    json!({"mode":"lossless","session_id":sid})
                )
                .await
                .unwrap_err()
                .to_string()
                .contains("malformed_selected_turn")
        );
        assert!(
            replay
                .call(
                    &mut Context::default(),
                    json!({"mode":"lossless","session_id":uuid::Uuid::new_v4().to_string()})
                )
                .await
                .unwrap_err()
                .to_string()
                .contains("not found")
        );
    }
}
