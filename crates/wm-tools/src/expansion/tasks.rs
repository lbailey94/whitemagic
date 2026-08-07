//! Task tools — distribute, status.

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore};

pub struct TaskDistributeTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TaskDistributeTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

impl Tool for TaskDistributeTool {
    fn name(&self) -> &str {
        "task.distribute"
    }
    fn gana(&self) -> Gana {
        Gana::TurtleBeak
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Distribute a task to registered agents"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let task = args.get("task").and_then(|v| v.as_str()).unwrap_or("");
        let agent_id = args
            .get("agent_id")
            .and_then(|v| v.as_str())
            .unwrap_or("any");
        let mut mem = Memory::new(
            Galaxy::Substrate,
            json!({
                "type": "task",
                "task": task,
                "agent_id": agent_id,
                "status": "distributed",
            })
            .to_string(),
        );
        mem.metadata.tags = vec!["task".into(), "distributed".into()];
        mem.metadata.importance = 0.7;
        self.store.put(Galaxy::Substrate, &mem)?;
        Ok(json!({
            "status": "success",
            "task_id": mem.metadata.id,
            "task": task,
            "agent_id": agent_id,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `task.status` — check task status.
pub struct TaskStatusTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TaskStatusTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

impl Tool for TaskStatusTool {
    fn name(&self) -> &str {
        "task.status"
    }
    fn gana(&self) -> Gana {
        Gana::TurtleBeak
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Check status of distributed tasks"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let task_id = args.get("task_id").and_then(|v| v.as_str()).unwrap_or("");
        let memories = self.store.scan(Galaxy::Substrate, 500)?;
        let tasks: Vec<Value> = memories
            .iter()
            .filter(|m| m.metadata.tags.contains(&"task".to_string()))
            .filter(|m| task_id.is_empty() || m.metadata.id.to_string().contains(task_id))
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "content": m.content,
                    "tags": m.metadata.tags,
                })
            })
            .collect();
        Ok(json!({
            "status": "success",
            "count": tasks.len(),
            "tasks": tasks,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}
