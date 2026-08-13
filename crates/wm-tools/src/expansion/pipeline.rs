//! Pipeline & skill tools — pipeline.create, pipeline.list, pipeline.status,
//! skill.invoke, skill.list.
//!
//! Gana::Horn — "System building, pipelines, invocation, status"
//!
//! Pipelines are stored as memories in the Sessions galaxy with a special
//! "pipeline" tag. Skills are stored in the Codex galaxy with a "skill" tag.
//! Both are lightweight, memory-backed constructs — no external process spawning.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore};

// ── pipeline.create ──────────────────────────────────────────────────

/// Create a named pipeline by storing its definition as a memory.
///
/// The pipeline definition is a JSON object with steps, stored as memory
/// content in the Sessions galaxy with "pipeline" tag.
pub struct PipelineCreateTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl PipelineCreateTool {
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
impl Tool for PipelineCreateTool {
    fn name(&self) -> &str {
        "pipeline.create"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Create a named pipeline with steps stored in memory"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let name = args
            .get("name")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("name (string) required".into()))?;
        let steps = args
            .get("steps")
            .and_then(|v| v.as_array())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("steps (array) required".into()))?;

        let definition = json!({
            "name": name,
            "steps": steps,
            "created_at": chrono::Utc::now().to_rfc3339(),
        });

        let mut mem = Memory::new(Galaxy::Sessions, definition.to_string());
        mem.metadata.tags = vec!["pipeline".into(), name.into()];
        mem.metadata.importance = 0.7;
        let id = mem.metadata.id;
        self.store.put(Galaxy::Sessions, &mem)?;

        Ok(json!({
            "status": "success",
            "pipeline_name": name,
            "pipeline_id": id.to_string(),
            "steps_count": steps.len(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── pipeline.list ────────────────────────────────────────────────────

/// List all stored pipelines.
pub struct PipelineListTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl PipelineListTool {
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
impl Tool for PipelineListTool {
    fn name(&self) -> &str {
        "pipeline.list"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List all stored pipelines"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mems = self.store.scan_all(Galaxy::Sessions)?;
        let pipelines: Vec<Value> = mems
            .iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "pipeline"))
            .map(|m| {
                let def: Value = serde_json::from_str(&m.content).unwrap_or(Value::Null);
                json!({
                    "id": m.metadata.id,
                    "name": m.metadata.tags.iter()
                        .find(|t| *t != "pipeline")
                        .cloned()
                        .unwrap_or_default(),
                    "steps_count": def.get("steps").and_then(Value::as_array).map_or(0, std::vec::Vec::len),
                    "created_at": m.metadata.created_at.to_rfc3339(),
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "count": pipelines.len(),
            "pipelines": pipelines,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── pipeline.status ──────────────────────────────────────────────────

/// Get the status of a specific pipeline by name or ID.
pub struct PipelineStatusTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl PipelineStatusTool {
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
impl Tool for PipelineStatusTool {
    fn name(&self) -> &str {
        "pipeline.status"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Get detailed status of a specific pipeline"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let name = args.get("name").and_then(|v| v.as_str());
        let id_str = args.get("id").and_then(|v| v.as_str());

        if name.is_none() && id_str.is_none() {
            return Err(wm_core::CoreError::InvalidArgs(
                "Either name (string) or id (string) required".into(),
            ));
        }

        let mems = self.store.scan_all(Galaxy::Sessions)?;
        let pipeline = mems.iter().find(|m| {
            m.metadata.tags.iter().any(|t| t == "pipeline")
                && (name.is_some_and(|n| m.metadata.tags.contains(&n.to_string()))
                    || id_str.is_some_and(|id| m.metadata.id.to_string() == id))
        });

        match pipeline {
            Some(m) => {
                let def: Value = serde_json::from_str(&m.content).unwrap_or(Value::Null);
                Ok(json!({
                    "status": "success",
                    "id": m.metadata.id,
                    "name": m.metadata.tags.iter()
                        .find(|t| *t != "pipeline")
                        .cloned()
                        .unwrap_or_default(),
                    "definition": def,
                    "importance": m.metadata.importance,
                    "created_at": m.metadata.created_at.to_rfc3339(),
                }))
            }
            None => Err(wm_core::CoreError::NotFound("Pipeline not found".into())),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── skill.invoke ─────────────────────────────────────────────────────

/// Invoke a skill by name. Skills are stored memories in the Codex galaxy
/// with a "skill" tag. Invocation looks up the skill and returns its
/// definition for execution.
pub struct SkillInvokeTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SkillInvokeTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SkillInvokeTool {
    fn name(&self) -> &str {
        "skill.invoke"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Invoke a named skill from the Codex galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let skill_name = args
            .get("skill")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("skill (string) required".into()))?;
        let params = args.get("params").cloned().unwrap_or(Value::Null);

        let mems = self.store.scan(Galaxy::Codex, 500)?;
        let skill = mems.iter().find(|m| {
            m.metadata.tags.iter().any(|t| t == "skill")
                && m.metadata.tags.contains(&skill_name.to_string())
        });

        match skill {
            Some(m) => {
                let definition: Value = serde_json::from_str(&m.content).unwrap_or(Value::Null);
                Ok(json!({
                    "status": "success",
                    "skill": skill_name,
                    "skill_id": m.metadata.id,
                    "definition": definition,
                    "params": params,
                    "invoked_at": chrono::Utc::now().to_rfc3339(),
                }))
            }
            None => Err(wm_core::CoreError::NotFound(format!(
                "Skill '{skill_name}' not found"
            ))),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── skill.list ───────────────────────────────────────────────────────

/// List all available skills.
pub struct SkillListTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SkillListTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SkillListTool {
    fn name(&self) -> &str {
        "skill.list"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List all available skills in the Codex galaxy"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mems = self.store.scan(Galaxy::Codex, 500)?;
        let skills: Vec<Value> = mems
            .iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "skill"))
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "name": m.metadata.tags.iter()
                        .find(|t| *t != "skill")
                        .cloned()
                        .unwrap_or_default(),
                    "importance": m.metadata.importance,
                    "content_preview": m.content.chars().take(100).collect::<String>(),
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "count": skills.len(),
            "skills": skills,
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
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, Arc::new(store))
    }

    fn seed_pipeline(store: &Arc<MemoryStore>) -> uuid::Uuid {
        let definition = json!({
            "name": "test-pipeline",
            "steps": [
                {"tool": "memory.create", "args": {"content": "step 1"}},
                {"tool": "memory.search", "args": {"query": "step 1"}}
            ]
        });
        let mut mem = Memory::new(Galaxy::Sessions, definition.to_string());
        mem.metadata.tags = vec!["pipeline".into(), "test-pipeline".into()];
        mem.metadata.importance = 0.7;
        let id = mem.metadata.id;
        store.put(Galaxy::Sessions, &mem).unwrap();
        id
    }

    fn seed_skill(store: &Arc<MemoryStore>) -> uuid::Uuid {
        let definition = json!({
            "name": "summarize",
            "handler": "memory.consolidate",
            "params_schema": {"galaxy": "string"}
        });
        let mut mem = Memory::new(Galaxy::Codex, definition.to_string());
        mem.metadata.tags = vec!["skill".into(), "summarize".into()];
        mem.metadata.importance = 0.8;
        let id = mem.metadata.id;
        store.put(Galaxy::Codex, &mem).unwrap();
        id
    }

    #[tokio::test]
    async fn pipeline_create_stores_definition() {
        let (_tmp, store) = open_store();
        let tool = PipelineCreateTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"name": "my-pipeline", "steps": [{"tool": "memory.create"}]}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["pipeline_name"], "my-pipeline");
        assert_eq!(obj["steps_count"], 1);
    }

    #[tokio::test]
    async fn pipeline_create_missing_name() {
        let (_tmp, store) = open_store();
        let tool = PipelineCreateTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"steps": []}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn pipeline_create_missing_steps() {
        let (_tmp, store) = open_store();
        let tool = PipelineCreateTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"name": "test"}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn pipeline_list_shows_pipelines() {
        let (_tmp, store) = open_store();
        seed_pipeline(&store);

        let tool = PipelineListTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["count"], 1);
        let pipelines = obj["pipelines"].as_array().unwrap();
        assert_eq!(pipelines[0]["name"], "test-pipeline");
    }

    #[tokio::test]
    async fn pipeline_list_empty() {
        let (_tmp, store) = open_store();
        let tool = PipelineListTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["count"], 0);
    }

    #[tokio::test]
    async fn pipeline_status_by_name() {
        let (_tmp, store) = open_store();
        seed_pipeline(&store);

        let tool = PipelineStatusTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"name": "test-pipeline"}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["name"], "test-pipeline");
        assert!(obj["definition"].is_object());
    }

    #[tokio::test]
    async fn pipeline_status_not_found() {
        let (_tmp, store) = open_store();
        let tool = PipelineStatusTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"name": "nonexistent"}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn pipeline_status_missing_args() {
        let (_tmp, store) = open_store();
        let tool = PipelineStatusTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn skill_invoke_finds_skill() {
        let (_tmp, store) = open_store();
        seed_skill(&store);

        let tool = SkillInvokeTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"skill": "summarize", "params": {"galaxy": "codex"}}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["skill"], "summarize");
        assert!(obj["definition"].is_object());
    }

    #[tokio::test]
    async fn skill_invoke_not_found() {
        let (_tmp, store) = open_store();
        let tool = SkillInvokeTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"skill": "nonexistent"}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn skill_invoke_missing_skill_arg() {
        let (_tmp, store) = open_store();
        let tool = SkillInvokeTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn skill_list_shows_skills() {
        let (_tmp, store) = open_store();
        seed_skill(&store);

        let tool = SkillListTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["count"], 1);
        let skills = obj["skills"].as_array().unwrap();
        assert_eq!(skills[0]["name"], "summarize");
    }

    #[tokio::test]
    async fn skill_list_empty() {
        let (_tmp, store) = open_store();
        let tool = SkillListTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["count"], 0);
    }
}
