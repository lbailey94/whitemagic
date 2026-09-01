//! Sangha mesh transport tools — `sangha.mesh.*` (R0).
//!
//! These tools talk to the live [`MeshNode`] through the shared
//! [`MeshSlot`]: `wm serve --mesh` installs the node after startup, and the
//! tools expose its join/chat/read/quarantine/status surface. When the
//! server was started without the mesh transport, every tool fails with an
//! actionable error instead of pretending.
//!
//! Gana::Room — mesh coordination. Registered on the full surface; the
//! curated product surface excludes `sangha.*` by design.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use std::sync::Arc;

use serde_json::Value;
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_sangha::mesh_node::{MeshNode, MeshSlot};

fn mesh_off_error() -> CoreError {
    CoreError::Tool(
        "mesh transport not enabled on this server — start `wm serve` with \
         --mesh (or WM_MESH=1); the sangha.mesh tools live on --profile full"
            .into(),
    )
}

fn node_or_err(slot: &MeshSlot) -> Result<Arc<MeshNode>, CoreError> {
    slot.get().ok_or_else(mesh_off_error)
}

fn read_effects() -> EffectRow {
    EffectRow::read_only(vec![Resource::Galaxy("sangha".into())])
}

fn write_effects() -> EffectRow {
    EffectRow {
        writes: vec![Resource::Galaxy("sangha".into())],
        ..Default::default()
    }
}

// ── sangha.mesh.status ────────────────────────────────────────────────

/// `sangha.mesh.status` — this node's mesh identity, connections, registry.
pub struct MeshStatusTool {
    slot: Arc<MeshSlot>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MeshStatusTool {
    pub fn new(slot: Arc<MeshSlot>) -> Self {
        Self {
            slot,
            stats: ToolStats::default(),
            effects: read_effects(),
        }
    }
}

#[async_trait]
impl Tool for MeshStatusTool {
    fn name(&self) -> &str {
        "sangha.mesh.status"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Sangha mesh node status: peer ID, public key, bind/announce addresses, \
         connected peers, discovery registry, chat and lock summaries"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let node = node_or_err(&self.slot)?;
        node.status().await
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sangha.mesh.join ──────────────────────────────────────────────────

/// `sangha.mesh.join` — dial a peer and bind identities with a signed
/// heartbeat.
pub struct MeshJoinTool {
    slot: Arc<MeshSlot>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MeshJoinTool {
    pub fn new(slot: Arc<MeshSlot>) -> Self {
        Self {
            slot,
            stats: ToolStats::default(),
            effects: write_effects(),
        }
    }
}

#[async_trait]
impl Tool for MeshJoinTool {
    fn name(&self) -> &str {
        "sangha.mesh.join"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Join a mesh peer: connect TCP to `address` (host:port) and exchange \
         signed identity heartbeats so both nodes bind each other's keys"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let node = node_or_err(&self.slot)?;
        let address = args
            .get("address")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("address required (host:port)".into()))?;
        node.join(address).await
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sangha.mesh.chat ──────────────────────────────────────────────────

/// `sangha.mesh.chat` — send a signed chat message to a peer.
pub struct MeshChatTool {
    slot: Arc<MeshSlot>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MeshChatTool {
    pub fn new(slot: Arc<MeshSlot>) -> Self {
        Self {
            slot,
            stats: ToolStats::default(),
            effects: write_effects(),
        }
    }
}

#[async_trait]
impl Tool for MeshChatTool {
    fn name(&self) -> &str {
        "sangha.mesh.chat"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Send a signed chat message to a mesh peer (args: peer — peer ID or \
         host:port address, channel, content). The message is signed with this \
         node's Ed25519 key and verified against the peer's binding on arrival"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let node = node_or_err(&self.slot)?;
        let peer = args
            .get("peer")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("peer required (ID or host:port)".into()))?;
        let channel = args
            .get("channel")
            .and_then(Value::as_str)
            .unwrap_or("general");
        let content = args
            .get("content")
            .and_then(Value::as_str)
            .ok_or_else(|| CoreError::InvalidArgs("content required".into()))?;
        node.chat(peer, channel, content).await
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sangha.mesh.read ──────────────────────────────────────────────────

/// `sangha.mesh.read` — read received chat from a channel.
pub struct MeshReadTool {
    slot: Arc<MeshSlot>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MeshReadTool {
    pub fn new(slot: Arc<MeshSlot>) -> Self {
        Self {
            slot,
            stats: ToolStats::default(),
            effects: read_effects(),
        }
    }
}

#[async_trait]
impl Tool for MeshReadTool {
    fn name(&self) -> &str {
        "sangha.mesh.read"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Read received mesh chat (args: channel, limit — default 20, newest last)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let node = node_or_err(&self.slot)?;
        let channel = args
            .get("channel")
            .and_then(Value::as_str)
            .unwrap_or("general");
        let limit = args
            .get("limit")
            .and_then(Value::as_u64)
            .unwrap_or(20)
            .clamp(1, 100) as usize;
        node.read_chat(channel, limit).await
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sangha.mesh.quarantine ────────────────────────────────────────────

/// `sangha.mesh.quarantine` — the bad-apple rule on the live node.
pub struct MeshQuarantineTool {
    slot: Arc<MeshSlot>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MeshQuarantineTool {
    pub fn new(slot: Arc<MeshSlot>) -> Self {
        Self {
            slot,
            stats: ToolStats::default(),
            effects: write_effects(),
        }
    }
}

#[async_trait]
impl Tool for MeshQuarantineTool {
    fn name(&self) -> &str {
        "sangha.mesh.quarantine"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Community governance on the mesh node (actions: quarantine, release, \
         list). quarantine: peer_id + reason — registry quarantine (rejoin \
         refused), chat purged, locks revoked, connection dropped; release: \
         peer_id; list: quarantined peers with reasons"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let node = node_or_err(&self.slot)?;
        match args.get("action").and_then(Value::as_str).unwrap_or("list") {
            "quarantine" => {
                let peer_id = args.get("peer_id").and_then(Value::as_str).ok_or_else(|| {
                    CoreError::InvalidArgs("peer_id required for quarantine".into())
                })?;
                let reason = args
                    .get("reason")
                    .and_then(Value::as_str)
                    .unwrap_or("community governance action");
                node.quarantine_peer(peer_id, reason).await
            }
            "release" => {
                let peer_id = args
                    .get("peer_id")
                    .and_then(Value::as_str)
                    .ok_or_else(|| CoreError::InvalidArgs("peer_id required for release".into()))?;
                node.release_quarantine(peer_id).await
            }
            "list" => node.quarantined().await,
            other => Err(CoreError::InvalidArgs(format!(
                "unknown sangha.mesh.quarantine action: {other}"
            ))),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sangha.mesh.mail ──────────────────────────────────────────────────

/// `sangha.mesh.mail` — the store-and-forward queue's operator surface.
pub struct MeshMailTool {
    slot: Arc<MeshSlot>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MeshMailTool {
    pub fn new(slot: Arc<MeshSlot>) -> Self {
        Self {
            slot,
            stats: ToolStats::default(),
            effects: read_effects(),
        }
    }
}

#[async_trait]
impl Tool for MeshMailTool {
    fn name(&self) -> &str {
        "sangha.mesh.mail"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Mesh mail slot (store-and-forward) — actions: list (queued entries \
         + published bounds), flush (deliver now — optional peer address), \
         drop (id). Chat to an unreachable peer is queued here \
         (agent_asleep) and delivered FIFO on rejoin; a full slot rejects \
         with asleep_queue_full"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let node = node_or_err(&self.slot)?;
        match args.get("action").and_then(Value::as_str).unwrap_or("list") {
            "list" => Ok(node.mail_list()),
            "flush" => {
                let peer = args.get("peer").and_then(Value::as_str);
                node.flush_mail(peer).await
            }
            "drop" => {
                let id = args
                    .get("id")
                    .and_then(Value::as_str)
                    .ok_or_else(|| CoreError::InvalidArgs("id required for drop".into()))?;
                node.drop_mail(id)
            }
            other => Err(CoreError::InvalidArgs(format!(
                "unknown sangha.mesh.mail action: {other}"
            ))),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Registration ──────────────────────────────────────────────────────

/// Register the mesh transport tools. Always registered (the full registry
/// is built before profile filtering); the tools fail with an actionable
/// error when no node was installed in the slot.
pub fn register_sangha_mesh(
    registry: &wm_dispatch::ToolRegistry,
    slot: Arc<MeshSlot>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(MeshStatusTool::new(Arc::clone(&slot))))
        .register(Arc::new(MeshJoinTool::new(Arc::clone(&slot))))
        .register(Arc::new(MeshChatTool::new(Arc::clone(&slot))))
        .register(Arc::new(MeshReadTool::new(Arc::clone(&slot))))
        .register(Arc::new(MeshMailTool::new(Arc::clone(&slot))))
        .register(Arc::new(MeshQuarantineTool::new(slot)))
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use wm_core::Context;
    fn ctx() -> Context {
        Context::default()
    }

    #[tokio::test]
    async fn tools_fail_actionably_when_mesh_off() {
        let slot = MeshSlot::new();
        assert!(
            MeshStatusTool::new(Arc::clone(&slot))
                .call(&mut ctx(), json!({}))
                .await
                .is_err()
        );
        assert!(
            MeshJoinTool::new(Arc::clone(&slot))
                .call(&mut ctx(), json!({"address": "127.0.0.1:1"}))
                .await
                .is_err()
        );
        let chat_err = MeshChatTool::new(Arc::clone(&slot))
            .call(&mut ctx(), json!({"peer": "x", "content": "y"}))
            .await
            .unwrap_err();
        assert!(chat_err.to_string().contains("--mesh"), "{chat_err}");
    }

    #[tokio::test]
    async fn mesh_tools_drive_a_live_two_node_mesh() {
        use wm_sangha::MeshKeyPair;
        use wm_sangha::mesh_node::MeshNodeConfig;

        let spawn = |id: &str, port: u16| {
            let keypair = MeshKeyPair::from_seed(id.as_bytes());
            let config = MeshNodeConfig {
                bind_addr: format!("127.0.0.1:{port}"),
                peer_id: id.to_string(),
                beacon_interval_sec: 1,
                auto_join: false,
                multicast_group: wm_sangha::transport::MULTICAST_GROUP.to_string(),
                agent_away_secs: 300,
                state_dir: None,
            };
            MeshNode::start(config, keypair)
        };
        let a = spawn("tool-node-a", 17_621).await.expect("a");
        let b = spawn("tool-node-b", 17_622).await.expect("b");

        let slot = MeshSlot::new();
        slot.set(Arc::clone(&a));

        // join through the tool (both directions — in production the
        // auto-join loop does this organically via beacons)
        let joined = MeshJoinTool::new(Arc::clone(&slot))
            .call(&mut ctx(), json!({"address": "127.0.0.1:17622"}))
            .await
            .expect("join");
        assert_eq!(joined["remote_registry"]["peer_count"], 1);
        let b_slot = MeshSlot::new();
        b_slot.set(Arc::clone(&b));
        MeshJoinTool::new(Arc::clone(&b_slot))
            .call(&mut ctx(), json!({"address": "127.0.0.1:17621"}))
            .await
            .expect("reverse join");

        // chat + read across the pair
        let chat_slot = MeshSlot::new();
        chat_slot.set(Arc::clone(&a));
        MeshChatTool::new(Arc::clone(&chat_slot))
            .call(
                &mut ctx(),
                json!({"peer": "tool-node-b", "channel": "ops", "content": "hi b"}),
            )
            .await
            .expect("chat");
        let read_slot = MeshSlot::new();
        read_slot.set(Arc::clone(&b));
        let inbox = MeshReadTool::new(read_slot)
            .call(&mut ctx(), json!({"channel": "ops"}))
            .await
            .expect("read");
        assert_eq!(inbox["messages"][0]["content"], "hi b");

        // quarantine through the tool; further chat is refused
        let q_slot = MeshSlot::new();
        q_slot.set(Arc::clone(&b));
        let quarantined = MeshQuarantineTool::new(Arc::clone(&q_slot))
            .call(
                &mut ctx(),
                json!({"action": "quarantine", "peer_id": "tool-node-a", "reason": "test"}),
            )
            .await
            .expect("quarantine");
        assert_eq!(quarantined["quarantined"], true);
        let refused = MeshChatTool::new(chat_slot)
            .call(
                &mut ctx(),
                json!({"peer": "tool-node-b", "channel": "ops", "content": "??"}),
            )
            .await;
        assert!(refused.is_err(), "quarantined sender must be refused");
    }
}
