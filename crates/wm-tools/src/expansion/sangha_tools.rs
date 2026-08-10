//! Sangha Mesh tools — sangha.peers, sangha.signal, sangha.chat, sangha.locks.
//!
//! Gana::Room — multi-agent coordination and mesh management.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use std::sync::Arc;
use std::sync::Mutex;

use serde_json::{Value, json};
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_sangha::{
    PeerCapability, PeerDiscovery, PeerInfo, ResourceLockManager, SanghaChat, Signal,
    SignalBroadcast, SignalType,
};

// ── sangha.peers ──────────────────────────────────────────────────────

/// `sangha.peers` — List discovered peers and their capabilities.
pub struct SanghaPeersTool {
    discovery: Arc<Mutex<PeerDiscovery>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SanghaPeersTool {
    pub fn new(discovery: Arc<Mutex<PeerDiscovery>>) -> Self {
        Self {
            discovery,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sangha".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SanghaPeersTool {
    fn name(&self) -> &str {
        "sangha.peers"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List discovered peers in the Sangha mesh, optionally filter by capability"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let discovery = self
            .discovery
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("sangha discovery lock: {e}")))?;
        let peers: Vec<&PeerInfo> =
            if let Some(cap_str) = args.get("capability").and_then(Value::as_str) {
                let cap = parse_capability(cap_str);
                discovery.peers_with_capability(&cap)
            } else {
                discovery.alive_peers()
            };

        let peer_list: Vec<Value> = peers
            .iter()
            .map(|p| {
                json!({
                    "id": p.id,
                    "address": p.address,
                    "alive": p.alive,
                    "capabilities": p.capabilities.iter().map(wm_sangha::PeerCapability::as_str).collect::<Vec<_>>(),
                    "heartbeat_count": p.heartbeat_count,
                    "last_seen": p.last_seen,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "peer_count": peer_list.len(),
            "peers": peer_list,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sangha.discover ───────────────────────────────────────────────────

/// `sangha.discover` — Register or update a peer in the discovery registry.
pub struct SanghaDiscoverTool {
    discovery: Arc<Mutex<PeerDiscovery>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SanghaDiscoverTool {
    pub fn new(discovery: Arc<Mutex<PeerDiscovery>>) -> Self {
        Self {
            discovery,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sangha".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SanghaDiscoverTool {
    fn name(&self) -> &str {
        "sangha.discover"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Register or update a peer in the Sangha mesh (args: peer_id, address, capabilities)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let peer_id = args
            .get("peer_id")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("peer_id required".into()))?;

        let address = args
            .get("address")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("address required".into()))?;

        let mut peer = PeerInfo::new(peer_id, address);

        if let Some(caps) = args.get("capabilities").and_then(Value::as_array) {
            for cap in caps {
                if let Some(s) = cap.as_str() {
                    peer.add_capability(parse_capability(s));
                }
            }
        }

        let mut discovery = self
            .discovery
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("sangha discovery lock: {e}")))?;
        discovery.discover(peer);

        Ok(json!({
            "status": "success",
            "peer_id": peer_id,
            "address": address,
            "peer_count": discovery.peer_count(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sangha.signal ─────────────────────────────────────────────────────

/// `sangha.signal` — Broadcast a signal to the mesh.
pub struct SanghaSignalTool {
    broadcast: Arc<Mutex<SignalBroadcast>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SanghaSignalTool {
    pub fn new(broadcast: Arc<Mutex<SignalBroadcast>>) -> Self {
        Self {
            broadcast,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sangha".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SanghaSignalTool {
    fn name(&self) -> &str {
        "sangha.signal"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Broadcast a signal to the Sangha mesh (args: signal_type, source, data)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let signal_type_str = args
            .get("signal_type")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("signal_type required".into()))?;

        let source = args.get("source").and_then(Value::as_str).unwrap_or("user");

        let data = args.get("data").cloned().unwrap_or_else(|| json!({}));

        let signal_type = parse_signal_type(signal_type_str).ok_or_else(|| {
            wm_core::CoreError::InvalidArgs(format!("unknown signal type: {signal_type_str}"))
        })?;

        let signal = Signal::new(signal_type, source, data);
        let mut broadcast = self
            .broadcast
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("sangha broadcast lock: {e}")))?;
        let delivered = broadcast.broadcast(signal);

        Ok(json!({
            "status": "success",
            "delivered": delivered,
            "signal_type": signal_type_str,
            "subscription_count": broadcast.subscription_count(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sangha.chat ───────────────────────────────────────────────────────

/// `sangha.chat` — Send a message to a Sangha chat channel.
pub struct SanghaChatTool {
    chat: Arc<Mutex<SanghaChat>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SanghaChatTool {
    pub fn new(chat: Arc<Mutex<SanghaChat>>) -> Self {
        Self {
            chat,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sangha".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SanghaChatTool {
    fn name(&self) -> &str {
        "sangha.chat"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Send, read, or verify messages in a Sangha chat channel (args: action=send|read|verify, channel, sender, content, after_id)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let action = args.get("action").and_then(Value::as_str).unwrap_or("read");

        let channel = args
            .get("channel")
            .and_then(Value::as_str)
            .unwrap_or("general");

        let mut chat = self
            .chat
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("sangha chat lock: {e}")))?;

        match action {
            "send" => {
                let sender = args.get("sender").and_then(Value::as_str).ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("sender required for send".into())
                })?;

                let content = args.get("content").and_then(Value::as_str).ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("content required for send".into())
                })?;

                let msg = chat.send(channel, sender, content);
                Ok(json!({
                    "status": "success",
                    "message_id": msg.id,
                    "channel": msg.channel,
                    "sender": msg.sender,
                    "timestamp": msg.timestamp,
                    "signed": !msg.signature.is_empty(),
                }))
            }
            "read" => {
                let after_id = args.get("after_id").and_then(Value::as_u64);
                let messages = chat.read(channel, after_id);
                let msgs: Vec<Value> = messages
                    .iter()
                    .map(|m| {
                        json!({
                            "id": m.id,
                            "sender": m.sender,
                            "content": m.content,
                            "timestamp": m.timestamp,
                            "signed": !m.signature.is_empty(),
                        })
                    })
                    .collect();

                Ok(json!({
                    "status": "success",
                    "channel": channel,
                    "message_count": msgs.len(),
                    "messages": msgs,
                }))
            }
            "verify" => {
                let report = chat.verify_channel(channel);
                Ok(json!({
                    "status": "success",
                    "channel": channel,
                    "mesh_signing": report.mesh_signing,
                    "checked": report.checked,
                    "verified": report.verified,
                    "rejected": report.rejected,
                    "clean": report.is_clean(),
                }))
            }
            _ => Err(wm_core::CoreError::InvalidArgs(
                "action must be 'send', 'read', or 'verify'".into(),
            )),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sangha.locks ──────────────────────────────────────────────────────

/// `sangha.locks` — Manage distributed resource locks.
pub struct SanghaLocksTool {
    lock_manager: Arc<Mutex<ResourceLockManager>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SanghaLocksTool {
    pub fn new(lock_manager: Arc<Mutex<ResourceLockManager>>) -> Self {
        Self {
            lock_manager,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sangha".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SanghaLocksTool {
    fn name(&self) -> &str {
        "sangha.locks"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Manage distributed resource locks (args: action=acquire|release|list, resource, peer)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let action = args
            .get("action")
            .and_then(Value::as_str)
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("action required".into()))?;

        let mut lm = self
            .lock_manager
            .lock()
            .map_err(|e| wm_core::CoreError::Tool(format!("sangha lock-manager lock: {e}")))?;

        match action {
            "acquire" => {
                let resource = args
                    .get("resource")
                    .and_then(Value::as_str)
                    .ok_or_else(|| wm_core::CoreError::InvalidArgs("resource required".into()))?;

                let peer = args
                    .get("peer")
                    .and_then(Value::as_str)
                    .ok_or_else(|| wm_core::CoreError::InvalidArgs("peer required".into()))?;

                let success = lm.acquire(resource, peer);
                Ok(json!({
                    "status": if success { "success" } else { "denied" },
                    "resource": resource,
                    "peer": peer,
                    "lock_count": lm.lock_count(),
                }))
            }
            "release" => {
                let resource = args
                    .get("resource")
                    .and_then(Value::as_str)
                    .ok_or_else(|| wm_core::CoreError::InvalidArgs("resource required".into()))?;

                let peer = args
                    .get("peer")
                    .and_then(Value::as_str)
                    .ok_or_else(|| wm_core::CoreError::InvalidArgs("peer required".into()))?;

                let success = lm.release(resource, peer);
                Ok(json!({
                    "status": if success { "success" } else { "not_found" },
                    "resource": resource,
                    "peer": peer,
                }))
            }
            "list" => {
                let summary = lm.summary();
                Ok(json!({
                    "status": "success",
                    "summary": summary,
                }))
            }
            _ => Err(wm_core::CoreError::InvalidArgs(
                "action must be 'acquire', 'release', or 'list'".into(),
            )),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── sangha.quarantine ─────────────────────────────────────────────────

/// `sangha.quarantine` — community governance for the Sangha mesh.
///
/// Cuts a bad apple off from the mesh (quarantine), restores it (release),
/// or inspects the quarantine list. A quarantined peer's messages are
/// purged and filtered out by the community read path, its locks are
/// revoked, and it cannot re-register until released — one bad apple must
/// not spoil the whole bunch.
pub struct SanghaQuarantineTool {
    discovery: Arc<Mutex<PeerDiscovery>>,
    chat: Arc<Mutex<SanghaChat>>,
    lock_manager: Arc<Mutex<ResourceLockManager>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SanghaQuarantineTool {
    pub fn new(
        discovery: Arc<Mutex<PeerDiscovery>>,
        chat: Arc<Mutex<SanghaChat>>,
        lock_manager: Arc<Mutex<ResourceLockManager>>,
    ) -> Self {
        Self {
            discovery,
            chat,
            lock_manager,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("sangha".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for SanghaQuarantineTool {
    fn name(&self) -> &str {
        "sangha.quarantine"
    }
    fn gana(&self) -> Gana {
        Gana::Room
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Community governance for the Sangha mesh (actions: quarantine, release, list). quarantine: peer_id (required) + reason — revokes the peer's locks and purges its messages; release: peer_id; list: show quarantined peers."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let action = args.get("action").and_then(Value::as_str).unwrap_or("list");
        match action {
            "quarantine" => {
                let peer_id = args.get("peer_id").and_then(Value::as_str).ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("peer_id required for quarantine".into())
                })?;
                let reason = args
                    .get("reason")
                    .and_then(Value::as_str)
                    .unwrap_or("community governance action");
                let mut discovery = self
                    .discovery
                    .lock()
                    .map_err(|e| wm_core::CoreError::Tool(format!("sangha discovery lock: {e}")))?;
                let quarantined = discovery.quarantine(peer_id, reason);
                // Revoke everything the bad apple holds so the community
                // is never held hostage by its resources.
                let revoked = if quarantined {
                    self.lock_manager
                        .lock()
                        .map(|mut lm| lm.revoke_peer(peer_id))
                        .unwrap_or(0)
                } else {
                    0
                };
                // Purge the bad apple's messages from every channel so its
                // words do not linger in the community's logs.
                let purged = if quarantined {
                    self.chat
                        .lock()
                        .map(|mut c| {
                            let channel = args
                                .get("channel")
                                .and_then(Value::as_str)
                                .map(str::to_string);
                            c.purge_sender(peer_id, channel.as_deref())
                        })
                        .unwrap_or(0)
                } else {
                    0
                };
                Ok(json!({
                    "status": if quarantined { "success" } else { "error" },
                    "action": "quarantine",
                    "peer_id": peer_id,
                    "quarantined": quarantined,
                    "reason": reason,
                    "locks_revoked": revoked,
                    "messages_purged": purged,
                    "message": if quarantined {
                        format!("peer {peer_id} quarantined ({reason}); {revoked} lock(s) revoked, {purged} message(s) purged")
                    } else {
                        format!("peer {peer_id} unknown or already quarantined")
                    },
                }))
            }
            "release" => {
                let peer_id = args.get("peer_id").and_then(Value::as_str).ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("peer_id required for release".into())
                })?;
                let mut discovery = self
                    .discovery
                    .lock()
                    .map_err(|e| wm_core::CoreError::Tool(format!("sangha discovery lock: {e}")))?;
                let released = discovery.release_quarantine(peer_id);
                Ok(json!({
                    "status": if released { "success" } else { "error" },
                    "action": "release",
                    "peer_id": peer_id,
                    "released": released,
                    "message": if released {
                        format!("peer {peer_id} released from quarantine — it may rejoin the mesh")
                    } else {
                        format!("peer {peer_id} not quarantined or unknown")
                    },
                }))
            }
            "list" => {
                let discovery = self
                    .discovery
                    .lock()
                    .map_err(|e| wm_core::CoreError::Tool(format!("sangha discovery lock: {e}")))?;
                let quarantined: Vec<Value> = discovery
                    .quarantined()
                    .iter()
                    .map(|p| {
                        json!({
                            "peer_id": p.id,
                            "address": p.address,
                            "reason": p.quarantine_reason,
                        })
                    })
                    .collect();
                Ok(json!({
                    "status": "success",
                    "action": "list",
                    "quarantined_count": quarantined.len(),
                    "quarantined": quarantined,
                }))
            }
            other => Err(wm_core::CoreError::InvalidArgs(format!(
                "unknown sangha.quarantine action: {other}"
            ))),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Helpers ───────────────────────────────────────────────────────────

fn parse_capability(s: &str) -> PeerCapability {
    match s {
        "inference" => PeerCapability::Inference,
        "memory" => PeerCapability::Memory,
        "dream" => PeerCapability::Dream,
        "full" => PeerCapability::Full,
        _ => PeerCapability::Tool(s.to_string()),
    }
}

fn parse_signal_type(s: &str) -> Option<SignalType> {
    match s {
        "memory_created" => Some(SignalType::MemoryCreated),
        "anomaly_detected" => Some(SignalType::AnomalyDetected),
        "dream_artifact" => Some(SignalType::DreamArtifact),
        "tool_result" => Some(SignalType::ToolResult),
        "hologram_update" => Some(SignalType::HologramUpdate),
        "peer_status" => Some(SignalType::PeerStatus),
        "custom" => Some(SignalType::Custom),
        _ => None,
    }
}

// ── Registration ──────────────────────────────────────────────────────

/// Register all Sangha tools into a registry.
#[allow(clippy::needless_pass_by_value)]
pub fn register_sangha(
    registry: &wm_dispatch::ToolRegistry,
    discovery: Arc<Mutex<PeerDiscovery>>,
    broadcast: Arc<Mutex<SignalBroadcast>>,
    chat: Arc<Mutex<SanghaChat>>,
    lock_manager: Arc<Mutex<ResourceLockManager>>,
) -> wm_dispatch::ToolRegistry {
    registry
        .register(Arc::new(SanghaPeersTool::new(discovery.clone())))
        .register(Arc::new(SanghaDiscoverTool::new(discovery.clone())))
        .register(Arc::new(SanghaSignalTool::new(broadcast)))
        .register(Arc::new(SanghaChatTool::new(chat.clone())))
        .register(Arc::new(SanghaLocksTool::new(lock_manager.clone())))
        .register(Arc::new(SanghaQuarantineTool::new(
            discovery,
            chat,
            lock_manager,
        )))
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn test_discovery() -> Arc<Mutex<PeerDiscovery>> {
        Arc::new(Mutex::new(PeerDiscovery::default()))
    }
    fn test_broadcast() -> Arc<Mutex<SignalBroadcast>> {
        Arc::new(Mutex::new(SignalBroadcast::new(100)))
    }
    fn test_chat() -> Arc<Mutex<SanghaChat>> {
        Arc::new(Mutex::new(SanghaChat::new(100)))
    }
    fn test_locks() -> Arc<Mutex<ResourceLockManager>> {
        Arc::new(Mutex::new(ResourceLockManager::default()))
    }

    #[tokio::test]
    async fn sangha_quarantine_isolates_and_releases() {
        let discovery = test_discovery();
        let chat = test_chat();
        let locks = test_locks();
        let tool = SanghaQuarantineTool::new(discovery.clone(), chat.clone(), locks.clone());
        let mut ctx = Context::default();

        // Register a rogue peer via the discovery directly.
        {
            let rogue = PeerInfo::new("rogue-1", "127.0.0.1:9001");
            discovery
                .lock()
                .unwrap()
                .discover_signed(rogue.signed(b"mesh-secret"), b"mesh-secret")
                .unwrap();
        }
        // It holds a lock that must be revoked on quarantine.
        locks
            .lock()
            .unwrap()
            .acquire_with_ttl("res:1", "rogue-1", 3600);
        // And its messages must be purged on quarantine.
        chat.lock().unwrap().send("gana:1", "rogue-1", "poison");

        // Quarantine it.
        let q = tool
            .call(
                &mut ctx,
                json!({"action": "quarantine", "peer_id": "rogue-1", "reason": "malicious posts"}),
            )
            .await
            .unwrap();
        assert_eq!(q["status"], "success");
        assert_eq!(q["locks_revoked"], 1);
        assert_eq!(q["messages_purged"], 1);
        assert!(discovery.lock().unwrap().is_quarantined("rogue-1"));
        assert!(chat.lock().unwrap().read("gana:1", None).is_empty());

        // List shows it.
        let list = tool
            .call(&mut ctx, json!({"action": "list"}))
            .await
            .unwrap();
        assert_eq!(list["quarantined_count"], 1);

        // Release restores it.
        let rel = tool
            .call(&mut ctx, json!({"action": "release", "peer_id": "rogue-1"}))
            .await
            .unwrap();
        assert_eq!(rel["status"], "success");
        assert!(!discovery.lock().unwrap().is_quarantined("rogue-1"));
    }

    #[tokio::test]
    async fn sangha_quarantine_requires_peer_id() {
        let tool = SanghaQuarantineTool::new(test_discovery(), test_chat(), test_locks());
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({"action": "quarantine"})).await;
        assert!(result.is_err());
    }
    #[tokio::test]
    async fn sangha_peers_returns_list() {
        let discovery = test_discovery();
        let tool = SanghaPeersTool::new(discovery);
        let mut ctx = Context::default();
        let v = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["peer_count"], 0);
    }

    #[tokio::test]
    async fn sangha_discover_registers_peer() {
        let discovery = test_discovery();
        let tool = SanghaDiscoverTool::new(discovery);
        let mut ctx = Context::default();
        let v = tool
            .call(&mut ctx, json!({"peer_id": "node-1", "address": "127.0.0.1:8080", "capabilities": ["inference", "memory"]})).await
            .unwrap();
        assert_eq!(v["status"], "success");
        assert_eq!(v["peer_count"], 1);
    }

    #[tokio::test]
    async fn sangha_signal_broadcasts() {
        let broadcast = test_broadcast();
        let tool = SanghaSignalTool::new(broadcast);
        let mut ctx = Context::default();
        let v = tool
            .call(
                &mut ctx,
                json!({"signal_type": "peer_status", "source": "test", "data": {"status": "ok"}}),
            )
            .await
            .unwrap();
        assert_eq!(v["status"], "success");
        assert!(v["delivered"].is_number());
    }

    #[tokio::test]
    async fn sangha_chat_send_and_read() {
        let chat = test_chat();
        let tool = SanghaChatTool::new(chat);
        let mut ctx = Context::default();

        let send_v = tool
            .call(&mut ctx, json!({"action": "send", "channel": "general", "sender": "node-1", "content": "hello"})).await
            .unwrap();
        assert_eq!(send_v["status"], "success");

        let read_v = tool
            .call(&mut ctx, json!({"action": "read", "channel": "general"}))
            .await
            .unwrap();
        assert_eq!(read_v["message_count"], 1);
    }

    #[tokio::test]
    async fn sangha_locks_acquire_and_list() {
        let lm = test_locks();
        let tool = SanghaLocksTool::new(lm);
        let mut ctx = Context::default();

        let acq_v = tool
            .call(
                &mut ctx,
                json!({"action": "acquire", "resource": "res:1", "peer": "node-1"}),
            )
            .await
            .unwrap();
        assert_eq!(acq_v["status"], "success");

        let list_v = tool
            .call(&mut ctx, json!({"action": "list"}))
            .await
            .unwrap();
        assert!(list_v["summary"]["active_locks"].is_number());
    }

    #[tokio::test]
    async fn sangha_locks_release() {
        let lm = test_locks();
        let tool = SanghaLocksTool::new(lm);
        let mut ctx = Context::default();

        tool.call(
            &mut ctx,
            json!({"action": "acquire", "resource": "res:1", "peer": "node-1"}),
        )
        .await
        .unwrap();

        let rel_v = tool
            .call(
                &mut ctx,
                json!({"action": "release", "resource": "res:1", "peer": "node-1"}),
            )
            .await
            .unwrap();
        assert_eq!(rel_v["status"], "success");
    }

    #[tokio::test]
    async fn sangha_tools_are_room_gana() {
        assert_eq!(SanghaPeersTool::new(test_discovery()).gana(), Gana::Room);
        assert_eq!(SanghaSignalTool::new(test_broadcast()).gana(), Gana::Room);
        assert_eq!(SanghaChatTool::new(test_chat()).gana(), Gana::Room);
        assert_eq!(SanghaLocksTool::new(test_locks()).gana(), Gana::Room);
    }
}
