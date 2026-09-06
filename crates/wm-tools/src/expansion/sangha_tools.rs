//! Sangha Mesh tools — sangha.peers, sangha.signal, sangha.chat, sangha.locks.
//!
//! Gana::Room — multi-agent coordination and mesh management.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use std::path::PathBuf;
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

/// Resources starting with this prefix are *scope claims*: they coordinate
/// through the durable lease ledger (`wm-leases.json`, the same substrate as
/// `code.claim`) in addition to the in-process manager, so mesh scope claims
/// are visible across processes and worktrees (F-1). Arbitrary resources
/// (e.g. `memory:galaxy:codex`) stay manager-only.
pub(crate) const MESH_SCOPE_PREFIX: &str = "scope:";

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
            // Scope claims write the durable ledger (F-1); the rest of the
            // surface only reads. Declared per the session-tools precedent.
            effects: EffectRow {
                reads: vec![Resource::Filesystem],
                writes: vec![Resource::Filesystem],
                ..Default::default()
            },
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
        "Manage distributed resource locks (args: action=acquire|release|list, resource, peer). Resources prefixed 'scope:' are coordination scopes: acquire requires intent and records an owner-matched, TTL-bounded claim in the durable lease ledger (visible via code.list); other resources are in-process only."
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

                if resource.starts_with(MESH_SCOPE_PREFIX) {
                    return self.acquire_scope(&mut lm, resource, peer, &args);
                }

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

                if resource.starts_with(MESH_SCOPE_PREFIX) {
                    return self.release_scope(&mut lm, resource, peer, &args);
                }

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

impl SanghaLocksTool {
    /// Acquire a `scope:` resource — durable ledger first (the cross-process
    /// truth), then the in-process manager. A live claim by another owner is
    /// denied with holder + intent, whether it was taken through the mesh or
    /// through `code.claim` (zero false free across substrates).
    fn acquire_scope(
        &self,
        lm: &mut ResourceLockManager,
        resource: &str,
        peer: &str,
        args: &Value,
    ) -> wm_core::Result<Value> {
        let intent = super::coordination::require_str(args, "intent")?;
        let ttl = match args.get("ttl_secs").and_then(Value::as_i64) {
            Some(t) => super::coordination::clamp_ttl(t)?,
            None => 3600,
        };
        let root = super::coordination::resolve_root(args)?;
        let ledger = super::coordination::LeaseLedger::discover(&root)?;

        match ledger.try_claim(resource, &intent, peer, ttl)? {
            Err(holder) => Ok(json!({
                "status": "denied",
                "resource": resource,
                "peer": peer,
                "holder": holder.owner_session,
                "holder_intent": holder.intent,
                "expires_at": holder.expires_at,
                "next_action": "wait for expiry, ask the holder to release, or claim a different scope",
            })),
            Ok(lease) => {
                if !lm.acquire_with_ttl(resource, peer, ttl) {
                    // In-process manager refused (per-peer limit): roll the
                    // durable claim back so both surfaces stay consistent.
                    let _ = ledger.release_scope(resource, peer)?;
                    return Ok(json!({
                        "status": "denied",
                        "resource": resource,
                        "peer": peer,
                        "reason": "per-peer lock limit reached on this node",
                    }));
                }
                Ok(json!({
                    "status": "success",
                    "resource": resource,
                    "peer": peer,
                    "intent": intent,
                    "expires_at": lease.expires_at,
                    "ttl_secs": ttl,
                    "ledger": ledger.path().display().to_string(),
                    "lock_count": lm.lock_count(),
                }))
            }
        }
    }

    /// Release a `scope:` resource — owner-matched on the durable ledger;
    /// the in-process manager entry is also released when the caller held it.
    fn release_scope(
        &self,
        lm: &mut ResourceLockManager,
        resource: &str,
        peer: &str,
        args: &Value,
    ) -> wm_core::Result<Value> {
        let root = super::coordination::resolve_root(args)?;
        let ledger = super::coordination::LeaseLedger::discover(&root)?;

        let ledger_outcome = ledger.release_scope(resource, peer)?;
        let manager_released = lm.release(resource, peer);

        match ledger_outcome {
            Err(holder) => Ok(json!({
                "status": "not_owner",
                "resource": resource,
                "peer": peer,
                "holder": holder.owner_session,
                "holder_intent": holder.intent,
                "expires_at": holder.expires_at,
                "note": "only the owning peer can release a scope claim",
            })),
            Ok(released) => Ok(json!({
                "status": "success",
                "resource": resource,
                "peer": peer,
                "ledger_released": released,
                "manager_released": manager_released,
            })),
        }
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
                        .map_or(0, |mut lm| lm.revoke_peer(peer_id))
                } else {
                    0
                };
                // The bad apple's durable scope claims (F-1 bridge) are freed
                // too — quarantine is the community override that bypasses
                // owner matching. Best-effort: a mesh node with no nearby
                // checkout has no ledger to clean.
                let scopes_freed = if quarantined {
                    args.get("root")
                        .and_then(Value::as_str)
                        .map(PathBuf::from)
                        .or_else(|| {
                            std::env::var("WM_PROJECT_ROOT")
                                .ok()
                                .filter(|s| !s.trim().is_empty())
                                .map(PathBuf::from)
                        })
                        .and_then(|root| {
                            super::coordination::LeaseLedger::discover(&root)
                                .ok()
                                .and_then(|ledger| {
                                    ledger.force_release_peer(peer_id, MESH_SCOPE_PREFIX).ok()
                                })
                        })
                        .unwrap_or_default()
                } else {
                    Vec::new()
                };
                // Purge the bad apple's messages from every channel so its
                // words do not linger in the community's logs.
                let purged = if quarantined {
                    self.chat.lock().map_or(0, |mut c| {
                        let channel = args
                            .get("channel")
                            .and_then(Value::as_str)
                            .map(str::to_string);
                        c.purge_sender(peer_id, channel.as_deref())
                    })
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
                    "scopes_freed": scopes_freed,
                    "messages_purged": purged,
                    "message": if quarantined {
                        format!("peer {peer_id} quarantined ({reason}); {revoked} lock(s) revoked, {} scope claim(s) freed, {purged} message(s) purged", scopes_freed.len())
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
            let keypair = wm_sangha::MeshKeyPair::from_seed(b"rogue-seed");
            discovery
                .lock()
                .unwrap()
                .discover_signed(rogue.signed(&keypair))
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

    // ── F-1: mesh scope claims in the durable ledger ──────────────────

    use crate::expansion::coordination::{CodeClaimTool, CodeListTool, LeaseLedger};

    /// Fresh local git repository with one empty initial commit (mirror of
    /// the coordination test helper — the ledger needs a git common dir).
    fn git_repo() -> (tempfile::TempDir, std::path::PathBuf) {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path().to_path_buf();
        let run = |args: &[&str]| {
            std::process::Command::new("git")
                .args(args)
                .current_dir(&root)
                .output()
                .expect("git must be available")
        };
        assert!(run(&["init", "-q"]).status.success());
        assert!(run(&["config", "user.email", "t@t"]).status.success());
        assert!(run(&["config", "user.name", "t"]).status.success());
        assert!(
            run(&["commit", "--allow-empty", "-m", "c1"])
                .status
                .success()
        );
        (dir, root)
    }

    #[tokio::test]
    async fn mesh_scope_acquire_records_durable_ledger_claim() {
        let (_guard, root) = git_repo();
        let tool = SanghaLocksTool::new(test_locks());
        let list = CodeListTool::new();
        let mut ctx = Context::default();
        let root_arg = json!(root.display().to_string());

        let acq = tool
            .call(
                &mut ctx,
                json!({
                    "action": "acquire",
                    "resource": "scope:wm-sangha/hologram-sync",
                    "peer": "node-1",
                    "intent": "rebuilding the hologram index",
                    "ttl_secs": 600,
                    "root": root_arg,
                }),
            )
            .await
            .unwrap();
        assert_eq!(acq["status"], "success", "got: {acq}");
        assert_eq!(acq["intent"], "rebuilding the hologram index");
        assert_eq!(acq["ttl_secs"], 600);

        // The claim is visible to the code.claim surface (same ledger).
        let listed = list
            .call(&mut ctx, json!({"root": root_arg}))
            .await
            .unwrap();
        assert_eq!(listed["count"], 1, "got: {listed}");
        assert_eq!(
            listed["leases"][0]["scope"],
            "scope:wm-sangha/hologram-sync"
        );
        assert_eq!(listed["leases"][0]["owner_session"], "node-1");
        assert_eq!(
            listed["leases"][0]["intent"],
            "rebuilding the hologram index"
        );
    }

    #[tokio::test]
    async fn mesh_scope_denied_when_code_claim_holds_it() {
        let (_guard, root) = git_repo();
        let locks = SanghaLocksTool::new(test_locks());
        let claim = CodeClaimTool::new(None);
        let mut ctx = Context::default();
        let root_arg = json!(root.display().to_string());

        claim
            .call(
                &mut ctx,
                json!({
                    "scope": "scope:wm-sangha/hologram-sync",
                    "intent": "claimed from the repo side",
                    "owner_session": "session-aaa",
                    "root": root_arg,
                }),
            )
            .await
            .unwrap();

        let denied = locks
            .call(
                &mut ctx,
                json!({
                    "action": "acquire",
                    "resource": "scope:wm-sangha/hologram-sync",
                    "peer": "node-9",
                    "intent": "mesh side wants it too",
                    "root": root_arg,
                }),
            )
            .await
            .unwrap();
        assert_eq!(denied["status"], "denied", "got: {denied}");
        assert_eq!(denied["holder"], "session-aaa");
        assert_eq!(denied["holder_intent"], "claimed from the repo side");
    }

    #[tokio::test]
    async fn mesh_scope_release_owner_matched() {
        let (_guard, root) = git_repo();
        let locks = SanghaLocksTool::new(test_locks());
        let mut ctx = Context::default();
        let root_arg = json!(root.display().to_string());
        let resource = "scope:wm-sangha/chat-archive";

        locks
            .call(
                &mut ctx,
                json!({
                    "action": "acquire", "resource": resource, "peer": "node-1",
                    "intent": "archiving", "root": root_arg,
                }),
            )
            .await
            .unwrap();

        let wrong = locks
            .call(
                &mut ctx,
                json!({"action": "release", "resource": resource, "peer": "node-2", "root": root_arg}),
            )
            .await
            .unwrap();
        assert_eq!(wrong["status"], "not_owner", "got: {wrong}");
        assert_eq!(wrong["holder"], "node-1");

        let right = locks
            .call(
                &mut ctx,
                json!({"action": "release", "resource": resource, "peer": "node-1", "root": root_arg}),
            )
            .await
            .unwrap();
        assert_eq!(right["status"], "success", "got: {right}");
        assert_eq!(right["ledger_released"], true);

        let check = LeaseLedger::discover(root.as_path()).unwrap();
        let (active, _) = check.snapshot().unwrap();
        assert!(active.is_empty(), "scope must be free after owner release");
    }

    #[tokio::test]
    async fn non_scope_resources_never_touch_the_ledger() {
        let (_guard, root) = git_repo();
        let tool = SanghaLocksTool::new(test_locks());
        let mut ctx = Context::default();

        let acq = tool
            .call(
                &mut ctx,
                json!({
                    "action": "acquire",
                    "resource": "memory:galaxy:codex",
                    "peer": "node-1",
                    "root": json!(root.display().to_string()),
                }),
            )
            .await
            .unwrap();
        assert_eq!(acq["status"], "success");

        let path = LeaseLedger::discover(root.as_path())
            .unwrap()
            .path()
            .to_path_buf();
        assert!(
            !path.exists(),
            "non-scope resources must not write the ledger"
        );
    }

    #[tokio::test]
    async fn quarantine_frees_durable_scope_claims() {
        let (_guard, root) = git_repo();
        let discovery = test_discovery();
        let locks = test_locks();
        let tool = SanghaQuarantineTool::new(discovery.clone(), test_chat(), locks.clone());
        let mut ctx = Context::default();
        let root_arg = root.display().to_string();

        // Rogue peer registers and holds both a manager lock and a durable
        // scope claim.
        {
            let rogue = PeerInfo::new("rogue-2", "127.0.0.1:9002");
            let keypair = wm_sangha::MeshKeyPair::from_seed(b"rogue-2");
            discovery
                .lock()
                .unwrap()
                .discover_signed(rogue.signed(&keypair))
                .unwrap();
        }
        locks
            .lock()
            .unwrap()
            .acquire_with_ttl("res:1", "rogue-2", 3600);
        let ledger = LeaseLedger::discover(std::path::Path::new(&root_arg)).unwrap();
        ledger
            .try_claim("scope:wm-sangha/relay", "held by rogue", "rogue-2", 3600)
            .unwrap()
            .unwrap();

        let q = tool
            .call(
                &mut ctx,
                json!({
                    "action": "quarantine", "peer_id": "rogue-2",
                    "reason": "bad apple", "root": root_arg,
                }),
            )
            .await
            .unwrap();
        assert_eq!(q["status"], "success", "got: {q}");
        assert_eq!(q["locks_revoked"], 1);
        assert_eq!(
            q["scopes_freed"],
            json!(["scope:wm-sangha/relay"]),
            "got: {q}"
        );

        let (active, _) = ledger.snapshot().unwrap();
        assert!(
            !active.iter().any(|l| l.scope == "scope:wm-sangha/relay"),
            "quarantine must free the peer's durable scope claims"
        );
    }

    #[tokio::test]
    async fn mesh_scope_acquire_requires_intent() {
        let (_guard, root) = git_repo();
        let tool = SanghaLocksTool::new(test_locks());
        let mut ctx = Context::default();

        let err = tool
            .call(
                &mut ctx,
                json!({
                    "action": "acquire",
                    "resource": "scope:wm-sangha/relay",
                    "peer": "node-1",
                    "root": json!(root.display().to_string()),
                }),
            )
            .await;
        assert!(err.is_err(), "scope acquires need a mandatory intent");
    }
}
