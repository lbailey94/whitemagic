//! Task tools — distribute, status.

#![forbid(unsafe_code)]

use async_trait::async_trait;

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

#[async_trait]
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
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "task": super::common::str_prop("Non-empty task description to record"),
                "agent_id": super::common::str_prop("Requested assignee label; not a verified or contacted agent"),
            }),
            &["task"],
        )
    }
    fn description(&self) -> &str {
        "Record a task assignment memo; does not contact, verify, or execute an agent"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let task = args
            .get("task")
            .and_then(|v| v.as_str())
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("Non-empty 'task' parameter required".into())
            })?;
        let agent_id = args
            .get("agent_id")
            .and_then(|v| v.as_str())
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .unwrap_or("any");
        let mut mem = Memory::new(
            Galaxy::Substrate,
            json!({
                "type": "task",
                "task": task,
                "agent_id": agent_id,
                "status": "recorded",
            })
            .to_string(),
        );
        mem.metadata.tags = vec!["task".into(), "recorded".into()];
        mem.metadata.importance = 0.7;
        self.store.put(Galaxy::Substrate, &mem)?;
        Ok(json!({
            "status": "success",
            "task_id": mem.metadata.id,
            "task": task,
            "agent_id": agent_id,
            "assignment_state": "recorded_only",
            "agent_verified": false,
            "agent_contacted": false,
            "execution_started": false,
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

#[async_trait]
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
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "task_id": super::common::str_prop("Optional exact task memo UUID"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "List recorded task assignment memos; does not report agent execution state"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let task_id = args
            .get("task_id")
            .and_then(|v| v.as_str())
            .map(uuid::Uuid::parse_str)
            .transpose()
            .map_err(|error| {
                wm_core::CoreError::InvalidArgs(format!("Invalid task_id UUID: {error}"))
            })?;
        let memories = self.store.scan(Galaxy::Substrate, 500)?;
        let tasks: Vec<Value> = memories
            .iter()
            .filter(|m| m.metadata.tags.contains(&"task".to_string()))
            .filter(|m| task_id.is_none_or(|id| m.metadata.id == id))
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

#[cfg(test)]
mod tests {
    use super::*;

    fn open_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        (tmp, store)
    }

    #[tokio::test]
    async fn distribute_records_memo_without_claiming_agent_execution() {
        let (_tmp, store) = open_store();
        let result = TaskDistributeTool::new(store.clone())
            .call(
                &mut Context::default(),
                json!({"task": "inspect invented fixture", "agent_id": "agent-example"}),
            )
            .await
            .unwrap();
        assert_eq!(result["assignment_state"], "recorded_only");
        assert_eq!(result["agent_verified"], false);
        assert_eq!(result["agent_contacted"], false);
        assert_eq!(result["execution_started"], false);

        let saved = store.scan(Galaxy::Substrate, 10).unwrap();
        assert_eq!(saved.len(), 1);
        let body: Value = serde_json::from_str(&saved[0].content).unwrap();
        assert_eq!(body["status"], "recorded");
    }

    #[tokio::test]
    async fn distribute_rejects_missing_or_blank_task() {
        let (_tmp, store) = open_store();
        let tool = TaskDistributeTool::new(store);
        for args in [json!({}), json!({"task": "  "})] {
            let error = tool.call(&mut Context::default(), args).await.unwrap_err();
            assert!(error.to_string().contains("Non-empty 'task'"));
        }
    }

    #[tokio::test]
    async fn status_reads_recorded_task_memos() {
        let (_tmp, store) = open_store();
        let created = TaskDistributeTool::new(store.clone())
            .call(&mut Context::default(), json!({"task": "bounded audit"}))
            .await
            .unwrap();
        let result = TaskStatusTool::new(store)
            .call(
                &mut Context::default(),
                json!({"task_id": created["task_id"]}),
            )
            .await
            .unwrap();
        assert_eq!(result["count"], 1);
        assert!(
            result["tasks"][0]["content"]
                .as_str()
                .unwrap()
                .contains("bounded audit")
        );
    }
}
