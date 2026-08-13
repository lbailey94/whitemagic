//! Session tools — start, checkpoint, recall, end.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore};

/// `session.start` — create a new session memory.
pub struct SessionStartTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionStartTool {
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
#[async_trait]
impl Tool for SessionStartTool {
    fn name(&self) -> &str {
        "session.start"
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
                "title": super::common::str_prop("Session title"),
                "user": super::common::str_prop("User identifier (default 'default')"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Start a new session — creates a session memory in Sessions galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let title = args
            .get("title")
            .and_then(|v| v.as_str())
            .unwrap_or("Untitled Session");
        let user = args
            .get("user")
            .and_then(|v| v.as_str())
            .unwrap_or("default");
        let mut mem = Memory::new(
            Galaxy::Sessions,
            json!({
                "type": "session_start",
                "title": title,
                "user": user,
            })
            .to_string(),
        );
        mem.metadata.tags = vec!["session".into(), "start".into()];
        mem.metadata.importance = 0.7;
        self.store.put(Galaxy::Sessions, &mem)?;
        Ok(json!({
            "status": "success",
            "session_id": mem.metadata.id,
            "title": title,
            "user": user,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.checkpoint` — save a checkpoint in a session.
pub struct SessionCheckpointTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionCheckpointTool {
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
#[async_trait]
impl Tool for SessionCheckpointTool {
    fn name(&self) -> &str {
        "session.checkpoint"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Save a checkpoint in a session"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let session_id = args
            .get("session_id")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let label = args
            .get("label")
            .and_then(|v| v.as_str())
            .unwrap_or("checkpoint");
        let data = args.get("data").cloned().unwrap_or_else(|| json!({}));
        let mut mem = Memory::new(
            Galaxy::Sessions,
            json!({
                "type": "checkpoint",
                "session_id": session_id,
                "label": label,
                "data": data,
            })
            .to_string(),
        );
        mem.metadata.tags = vec!["session".into(), "checkpoint".into()];
        mem.metadata.importance = 0.5;
        self.store.put(Galaxy::Sessions, &mem)?;
        Ok(json!({
            "status": "success",
            "checkpoint_id": mem.metadata.id,
            "session_id": session_id,
            "label": label,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.recall` — retrieve session memories.
pub struct SessionRecallTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionRecallTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sessions".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SessionRecallTool {
    fn name(&self) -> &str {
        "session.recall"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Recall session memories by session_id"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let session_id = args
            .get("session_id")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;
        let memories = self.store.scan(Galaxy::Sessions, 500)?;
        let filtered: Vec<Value> = memories
            .iter()
            .filter(|m| m.content.contains(session_id))
            .take(limit)
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "content": m.content,
                    "tags": m.metadata.tags,
                    "created_at": m.metadata.created_at.to_rfc3339(),
                })
            })
            .collect();
        Ok(json!({
            "status": "success",
            "session_id": session_id,
            "count": filtered.len(),
            "memories": filtered,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.end` — end a session.
pub struct SessionEndTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionEndTool {
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
#[async_trait]
impl Tool for SessionEndTool {
    fn name(&self) -> &str {
        "session.end"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "End a session — writes a session_end marker"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let session_id = args
            .get("session_id")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let summary = args.get("summary").and_then(|v| v.as_str()).unwrap_or("");
        let mut mem = Memory::new(
            Galaxy::Sessions,
            json!({
                "type": "session_end",
                "session_id": session_id,
                "summary": summary,
            })
            .to_string(),
        );
        mem.metadata.tags = vec!["session".into(), "end".into()];
        mem.metadata.importance = 0.6;
        self.store.put(Galaxy::Sessions, &mem)?;
        Ok(json!({
            "status": "success",
            "session_id": session_id,
            "end_id": mem.metadata.id,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}
