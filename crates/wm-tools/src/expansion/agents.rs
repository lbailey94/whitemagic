//! Agent tools — register, list, heartbeat.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore, SearchEngine, content_hash as compute_hash};

pub struct AgentRegisterTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl AgentRegisterTool {
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
#[async_trait]
impl Tool for AgentRegisterTool {
    fn name(&self) -> &str {
        "agent.register"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Register a new agent in the Substrate galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let name = args
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("unnamed");
        let capabilities = args.get("capabilities").cloned().unwrap_or(json!([]));
        let mut mem = Memory::new(
            Galaxy::Substrate,
            json!({
                "type": "agent_register",
                "name": name,
                "capabilities": capabilities,
            })
            .to_string(),
        );
        mem.metadata.tags = vec!["agent".into(), "registration".into()];
        mem.metadata.importance = 0.8;
        self.store.put(Galaxy::Substrate, &mem)?;
        Ok(json!({
            "status": "success",
            "agent_id": mem.metadata.id,
            "name": name,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `agent.list` — list registered agents.
pub struct AgentListTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl AgentListTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for AgentListTool {
    fn name(&self) -> &str {
        "agent.list"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List all registered agents"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let memories = self.store.scan(Galaxy::Substrate, 500)?;
        let agents: Vec<Value> = memories
            .iter()
            .filter(|m| m.metadata.tags.contains(&"agent".to_string()))
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
            "count": agents.len(),
            "agents": agents,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `agent.heartbeat` — record an agent heartbeat.
pub struct AgentHeartbeatTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl AgentHeartbeatTool {
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
#[async_trait]
impl Tool for AgentHeartbeatTool {
    fn name(&self) -> &str {
        "agent.heartbeat"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Record an agent heartbeat"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let agent_id = args.get("agent_id").and_then(|v| v.as_str()).unwrap_or("");
        let status = args
            .get("status")
            .and_then(|v| v.as_str())
            .unwrap_or("alive");
        let mem = Memory::new(
            Galaxy::Substrate,
            json!({
                "type": "heartbeat",
                "agent_id": agent_id,
                "status": status,
            })
            .to_string(),
        );
        self.store.put(Galaxy::Substrate, &mem)?;
        Ok(json!({
            "status": "success",
            "agent_id": agent_id,
            "heartbeat_id": mem.metadata.id,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `agent.trust` — get or set trust level for an agent.
///
/// If `trust_level` is provided, updates the agent's trust level (0.0–1.0).
/// Otherwise, returns the current trust level.
pub struct AgentTrustTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl AgentTrustTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                reads: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for AgentTrustTool {
    fn name(&self) -> &str {
        "agent.trust"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Get or set trust level for an agent (0.0–1.0)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let agent_id = args
            .get("agent_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("Missing 'agent_id' parameter".into())
            })?;

        let memories = self.store.scan(Galaxy::Substrate, 500)?;
        let agent_mem = memories
            .iter()
            .filter(|m| m.metadata.tags.contains(&"agent".to_string()))
            .find(|m| {
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(&m.content) {
                    data.get("name").and_then(|v| v.as_str()) == Some(agent_id)
                        || m.metadata.id.to_string() == agent_id
                } else {
                    false
                }
            })
            .ok_or_else(|| wm_core::CoreError::NotFound(format!("Agent '{agent_id}' not found")))?;

        let mut data: serde_json::Value =
            serde_json::from_str(&agent_mem.content).map_err(|e| {
                wm_core::CoreError::Memory(format!("Failed to parse agent record: {e}"))
            })?;

        if let Some(trust) = args.get("trust_level").and_then(serde_json::Value::as_f64) {
            let trust = trust.clamp(0.0, 1.0);
            data["trust_level"] = json!(trust);
            let mut updated = Memory::new(Galaxy::Substrate, data.to_string());
            updated.metadata.id = agent_mem.metadata.id;
            updated.metadata.tags.clone_from(&agent_mem.metadata.tags);
            updated.metadata.importance = agent_mem.metadata.importance;
            updated.metadata.content_hash = compute_hash(&updated.content);
            self.store.put(Galaxy::Substrate, &updated)?;
            Ok(json!({
                "status": "success",
                "agent_id": agent_id,
                "trust_level": trust,
                "action": "set",
            }))
        } else {
            let trust = data
                .get("trust_level")
                .and_then(serde_json::Value::as_f64)
                .unwrap_or(0.5);
            Ok(json!({
                "status": "success",
                "agent_id": agent_id,
                "trust_level": trust,
                "action": "get",
            }))
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `agent.descriptions` — get or set description for an agent.
pub struct AgentDescriptionsTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl AgentDescriptionsTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                reads: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for AgentDescriptionsTool {
    fn name(&self) -> &str {
        "agent.descriptions"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Get or set description for an agent"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let agent_id = args
            .get("agent_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("Missing 'agent_id' parameter".into())
            })?;

        let memories = self.store.scan(Galaxy::Substrate, 500)?;
        let agent_mem = memories
            .iter()
            .filter(|m| m.metadata.tags.contains(&"agent".to_string()))
            .find(|m| {
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(&m.content) {
                    data.get("name").and_then(|v| v.as_str()) == Some(agent_id)
                        || m.metadata.id.to_string() == agent_id
                } else {
                    false
                }
            })
            .ok_or_else(|| wm_core::CoreError::NotFound(format!("Agent '{agent_id}' not found")))?;

        let mut data: serde_json::Value =
            serde_json::from_str(&agent_mem.content).map_err(|e| {
                wm_core::CoreError::Memory(format!("Failed to parse agent record: {e}"))
            })?;

        if let Some(desc) = args.get("description").and_then(|v| v.as_str()) {
            data["description"] = json!(desc);
            let mut updated = Memory::new(Galaxy::Substrate, data.to_string());
            updated.metadata.id = agent_mem.metadata.id;
            updated.metadata.tags.clone_from(&agent_mem.metadata.tags);
            updated.metadata.importance = agent_mem.metadata.importance;
            updated.metadata.content_hash = compute_hash(&updated.content);
            self.store.put(Galaxy::Substrate, &updated)?;
            Ok(json!({
                "status": "success",
                "agent_id": agent_id,
                "description": desc,
                "action": "set",
            }))
        } else {
            let desc = data
                .get("description")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            Ok(json!({
                "status": "success",
                "agent_id": agent_id,
                "description": desc,
                "action": "get",
            }))
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `agent.capabilities` — get or set capabilities for an agent.
pub struct AgentCapabilitiesTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl AgentCapabilitiesTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                reads: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for AgentCapabilitiesTool {
    fn name(&self) -> &str {
        "agent.capabilities"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Get or set capabilities for an agent"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let agent_id = args
            .get("agent_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("Missing 'agent_id' parameter".into())
            })?;

        let memories = self.store.scan(Galaxy::Substrate, 500)?;
        let agent_mem = memories
            .iter()
            .filter(|m| m.metadata.tags.contains(&"agent".to_string()))
            .find(|m| {
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(&m.content) {
                    data.get("name").and_then(|v| v.as_str()) == Some(agent_id)
                        || m.metadata.id.to_string() == agent_id
                } else {
                    false
                }
            })
            .ok_or_else(|| wm_core::CoreError::NotFound(format!("Agent '{agent_id}' not found")))?;

        let mut data: serde_json::Value =
            serde_json::from_str(&agent_mem.content).map_err(|e| {
                wm_core::CoreError::Memory(format!("Failed to parse agent record: {e}"))
            })?;

        if let Some(caps) = args.get("capabilities").and_then(|v| v.as_array()) {
            data["capabilities"] = json!(caps);
            let mut updated = Memory::new(Galaxy::Substrate, data.to_string());
            updated.metadata.id = agent_mem.metadata.id;
            updated.metadata.tags.clone_from(&agent_mem.metadata.tags);
            updated.metadata.importance = agent_mem.metadata.importance;
            updated.metadata.content_hash = compute_hash(&updated.content);
            self.store.put(Galaxy::Substrate, &updated)?;
            Ok(json!({
                "status": "success",
                "agent_id": agent_id,
                "capabilities": caps,
                "action": "set",
            }))
        } else {
            let caps = data.get("capabilities").cloned().unwrap_or(json!([]));
            Ok(json!({
                "status": "success",
                "agent_id": agent_id,
                "capabilities": caps,
                "action": "get",
            }))
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `agent.heartbeat.history` — retrieve heartbeat history for an agent.
pub struct AgentHeartbeatHistoryTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl AgentHeartbeatHistoryTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for AgentHeartbeatHistoryTool {
    fn name(&self) -> &str {
        "agent.heartbeat.history"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Retrieve heartbeat history for an agent"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let agent_id = args
            .get("agent_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("Missing 'agent_id' parameter".into())
            })?;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;

        let memories = self.store.scan(Galaxy::Substrate, 10_000)?;
        let mut heartbeats: Vec<Value> = memories
            .iter()
            .filter(|m| {
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(&m.content) {
                    data.get("type").and_then(|v| v.as_str()) == Some("heartbeat")
                        && data.get("agent_id").and_then(|v| v.as_str()) == Some(agent_id)
                } else {
                    false
                }
            })
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "timestamp": m.metadata.created_at.to_rfc3339(),
                    "content": m.content,
                })
            })
            .collect();
        heartbeats.truncate(limit);

        Ok(json!({
            "status": "success",
            "agent_id": agent_id,
            "count": heartbeats.len(),
            "heartbeats": heartbeats,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `agent.deregister` — remove an agent from the registry.
pub struct AgentDeregisterTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl AgentDeregisterTool {
    pub fn new(store: Arc<MemoryStore>, search: Option<Arc<SearchEngine>>) -> Self {
        Self {
            store,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                reads: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for AgentDeregisterTool {
    fn name(&self) -> &str {
        "agent.deregister"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Deregister an agent (removes registration record)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let agent_id = args
            .get("agent_id")
            .and_then(|v| v.as_str())
            .ok_or_else(|| {
                wm_core::CoreError::InvalidArgs("Missing 'agent_id' parameter".into())
            })?;

        let memories = self.store.scan(Galaxy::Substrate, 500)?;
        let agent_mem = memories
            .iter()
            .filter(|m| m.metadata.tags.contains(&"agent".to_string()))
            .find(|m| {
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(&m.content) {
                    data.get("name").and_then(|v| v.as_str()) == Some(agent_id)
                        || m.metadata.id.to_string() == agent_id
                } else {
                    false
                }
            })
            .ok_or_else(|| wm_core::CoreError::NotFound(format!("Agent '{agent_id}' not found")))?;

        self.store
            .delete(Galaxy::Substrate, agent_mem.metadata.id)?;
        super::common::deindex(self.search.as_deref(), &agent_mem.metadata.id.to_string());

        Ok(json!({
            "status": "success",
            "agent_id": agent_id,
            "deregistered": true,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_memory::MemoryStore;

    fn test_store() -> Arc<MemoryStore> {
        let dir = tempfile::tempdir().unwrap();
        Arc::new(MemoryStore::open_default(dir.path()).unwrap())
    }

    #[tokio::test]
    async fn agent_trust_get_default() {
        let store = test_store();
        let reg = AgentRegisterTool::new(store.clone());
        let mut ctx = Context::default();
        let _ = reg.call(&mut ctx, json!({"name": "worker-1"})).await;

        let tool = AgentTrustTool::new(store);
        let result = tool.call(&mut ctx, json!({"agent_id": "worker-1"})).await;
        assert!(result.is_ok());
        let v = result.unwrap();
        assert_eq!(v["action"], "get");
        assert_eq!(v["trust_level"], 0.5);
    }

    #[tokio::test]
    async fn agent_trust_set_and_get() {
        let store = test_store();
        let reg = AgentRegisterTool::new(store.clone());
        let mut ctx = Context::default();
        let _ = reg.call(&mut ctx, json!({"name": "worker-2"})).await;

        let tool = AgentTrustTool::new(store);
        let _ = tool
            .call(
                &mut ctx,
                json!({"agent_id": "worker-2", "trust_level": 0.9}),
            )
            .await;

        let result = tool.call(&mut ctx, json!({"agent_id": "worker-2"})).await;
        assert!(result.is_ok());
        let v = result.unwrap();
        assert_eq!(v["action"], "get");
        assert_eq!(v["trust_level"], 0.9);
    }

    #[tokio::test]
    async fn agent_descriptions_set_and_get() {
        let store = test_store();
        let reg = AgentRegisterTool::new(store.clone());
        let mut ctx = Context::default();
        let _ = reg.call(&mut ctx, json!({"name": "worker-3"})).await;

        let tool = AgentDescriptionsTool::new(store);
        let _ = tool
            .call(
                &mut ctx,
                json!({"agent_id": "worker-3", "description": "A test agent"}),
            )
            .await;

        let result = tool.call(&mut ctx, json!({"agent_id": "worker-3"})).await;
        assert!(result.is_ok());
        let v = result.unwrap();
        assert_eq!(v["description"], "A test agent");
    }

    #[tokio::test]
    async fn agent_capabilities_set_and_get() {
        let store = test_store();
        let reg = AgentRegisterTool::new(store.clone());
        let mut ctx = Context::default();
        let _ = reg
            .call(
                &mut ctx,
                json!({"name": "worker-4", "capabilities": ["read"]}),
            )
            .await;

        let tool = AgentCapabilitiesTool::new(store);
        let result = tool.call(&mut ctx, json!({"agent_id": "worker-4"})).await;
        assert!(result.is_ok());
        let v = result.unwrap();
        assert_eq!(v["capabilities"], json!(["read"]));

        let _ = tool
            .call(
                &mut ctx,
                json!({"agent_id": "worker-4", "capabilities": ["read", "write"]}),
            )
            .await;
        let result = tool.call(&mut ctx, json!({"agent_id": "worker-4"})).await;
        let v = result.unwrap();
        assert_eq!(v["capabilities"], json!(["read", "write"]));
    }

    #[tokio::test]
    async fn agent_heartbeat_history() {
        let store = test_store();
        let reg = AgentRegisterTool::new(store.clone());
        let mut ctx = Context::default();
        let _ = reg.call(&mut ctx, json!({"name": "worker-5"})).await;

        let hb = AgentHeartbeatTool::new(store.clone());
        let _ = hb
            .call(&mut ctx, json!({"agent_id": "worker-5", "status": "alive"}))
            .await;
        let _ = hb
            .call(&mut ctx, json!({"agent_id": "worker-5", "status": "busy"}))
            .await;

        let tool = AgentHeartbeatHistoryTool::new(store);
        let result = tool.call(&mut ctx, json!({"agent_id": "worker-5"})).await;
        assert!(result.is_ok());
        let v = result.unwrap();
        assert_eq!(v["count"], 2);
    }

    #[tokio::test]
    async fn agent_deregister() {
        let store = test_store();
        let reg = AgentRegisterTool::new(store.clone());
        let mut ctx = Context::default();
        let _ = reg.call(&mut ctx, json!({"name": "worker-6"})).await;

        let tool = AgentDeregisterTool::new(store.clone(), None);
        let result = tool.call(&mut ctx, json!({"agent_id": "worker-6"})).await;
        assert!(result.is_ok());
        assert_eq!(result.unwrap()["deregistered"], true);

        let list = AgentListTool::new(store);
        let result = list.call(&mut ctx, json!({})).await;
        let v = result.unwrap();
        assert_eq!(v["count"], 0);
    }

    #[tokio::test]
    async fn agent_trust_not_found() {
        let store = test_store();
        let tool = AgentTrustTool::new(store);
        let mut ctx = Context::default();
        let result = tool
            .call(&mut ctx, json!({"agent_id": "nonexistent"}))
            .await;
        assert!(result.is_err());
    }
}
