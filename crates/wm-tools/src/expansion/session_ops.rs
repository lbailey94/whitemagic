//! Session tools — record, replay, continuity, handoff (v26 parity).
//!
//! Port of the v26 session recorder / handoff surface (the last Phase-1
//! gap): turns are recorded chronologically into the Sessions galaxy,
//! replayed in full/selective/progressive modes, summarized across
//! sessions for continuity, and packaged for handoff to another device.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore};

fn turn_json(mem: &Memory) -> Option<Value> {
    let v: Value = serde_json::from_str(&mem.content).ok()?;
    if v.get("type").and_then(Value::as_str) == Some("session_turn") {
        Some(v)
    } else {
        None
    }
}

/// Load turns for a session (or all sessions), newest last.
fn load_turns(
    store: &MemoryStore,
    session_id: Option<&str>,
    limit: usize,
) -> wm_core::Result<Vec<(Memory, Value)>> {
    let memories = store.scan_all(Galaxy::Sessions)?;
    let mut turns: Vec<(Memory, Value)> = memories
        .iter()
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
            }),
            &["content"],
        )
    }
    fn description(&self) -> &str {
        "Record a conversation turn as persistent session memory. Args: content (required), role (user|ai, default user), turn_type (default message), importance (0-1, default 0.5), session_id (optional — defaults to the most recent session)."
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
        let session_id: String = if let Some(sid) = session_id {
            sid.to_string()
        } else {
            let memories = self.store.scan_all(Galaxy::Sessions)?;
            memories
                .iter()
                .filter(|m| m.metadata.tags.contains(&"start".to_string()))
                .map(|m| m.metadata.id.to_string())
                .next_back()
                .ok_or_else(|| {
                    wm_core::CoreError::Tool("no session found — run session.start first".into())
                })?
        };

        // Sequence = existing turns for this session + 1.
        let sequence = load_turns(&self.store, Some(&session_id), 10_000)?.len() as u64 + 1;

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
                "timestamp": chrono::Utc::now().timestamp_millis(),
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
                "turn_types": super::common::str_array_prop("Selective mode: turn types to keep"),
                "min_importance": super::common::num_prop("Selective mode floor (default 0.7)"),
                "token_budget": super::common::int_prop("Progressive mode token budget (default 2000)"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Replay session turns. Args: mode (full|selective|progressive, default full), session_id (optional), n (default 50), turn_types (list, for selective), min_importance (0-1, default 0.7, for selective), token_budget (default 2000, for progressive)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let mode = args.get("mode").and_then(Value::as_str).unwrap_or("full");
        let session_id = args.get("session_id").and_then(Value::as_str);
        let n = args.get("n").and_then(Value::as_u64).unwrap_or(50) as usize;
        let turns = load_turns(&self.store, session_id, 10_000)?;

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
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Get cross-session continuity — the last N turns of the most recent prior session ('where we left off'). Args: current_session_id (optional, excluded), n (default 10)."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let current = args.get("current_session_id").and_then(Value::as_str);
        let n = args.get("n").and_then(Value::as_u64).unwrap_or(10) as usize;

        // Find the most recent session_start that is not the current session.
        let memories = self.store.scan_all(Galaxy::Sessions)?;
        let previous = memories.iter().rfind(|m| {
            m.metadata.tags.contains(&"start".to_string())
                && current.is_none_or(|c| m.metadata.id.to_string() != c)
        });

        let Some(prev) = previous else {
            return Ok(json!({
                "status": "success",
                "previous_session": null,
                "turns": [],
                "count": 0,
                "message": "no previous session found",
            }));
        };

        let prev_id = prev.metadata.id.to_string();
        let mut turns = load_turns(&self.store, Some(&prev_id), 10_000)?;
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
                let turns = load_turns(&self.store, Some(session_id), 10_000)?;
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
                        "created_at": chrono::Utc::now().timestamp_millis(),
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
pub fn register_session_ops(
    registry: &wm_dispatch::ToolRegistry,
    store: &Arc<MemoryStore>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(SessionRecordTool::new(store.clone())))
        .register(Arc::new(SessionReplayTool::new(store.clone())))
        .register(Arc::new(SessionContinuityTool::new(store.clone())))
        .register(Arc::new(SessionHandoffTool::new(store.clone())))
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
