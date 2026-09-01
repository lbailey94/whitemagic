//! MeshNode — the serve-side supervisor that turns `wm serve --mesh` into a
//! live Sangha mesh node.
//!
//! A [`MeshNode`] owns a [`SanghaTransport`] plus its [`SanghaState`] and
//! runs three background tasks: the TCP JSON-RPC server, the UDP multicast
//! beacon listener (discovery receive side), and the auto-join loop that
//! dials discovered peers and binds identities with signed heartbeats.
//!
//! ## Join sequence (verified behavior — see `docs/MESH_JOIN_PROTOCOL.md`)
//!
//! 1. Beacon: each node announces `PeerAnnounce { peer_id, tcp_addr, ... }`
//!    every `beacon_interval_sec` on multicast `224.0.0.69:7369`.
//! 2. Dial: the auto-join loop (or an explicit `sangha.mesh.join`) connects
//!    TCP to an announced address.
//! 3. Bind: the dialer sends a **signed heartbeat** (`PeerInfo::signed`)
//!    carrying its own identity; the receiver verifies the signature and
//!    binds the Ed25519 public key to the peer ID (first-seen binding —
//!    later announcements with a different key are refused as identity
//!    theft, and quarantined peers cannot re-register).
//! 4. Coordinate: signed chat, signals, locks, and hologram sync flow as
//!    verified JSON-RPC over the length-prefixed TCP framing.
//!
//! The [`MeshSlot`] is the shared handle: `wm serve` creates one at init,
//! the mesh tools and `/status` read it, and the CLI fills it after
//! spawning the node.

#![forbid(unsafe_code)]

use std::sync::Arc;

use serde_json::{Value, json};
use wm_core::Result;

use crate::crypto::MeshKeyPair;
use crate::peer::PeerInfo;
use crate::transport::{SanghaState, SanghaTransport, TransportConfig};

// ── Environment knobs ─────────────────────────────────────────────────

/// `WM_MESH=1` — enable the mesh transport (strict parse, mirrors
/// `WM_LANDLOCK`).
pub const ENV_MESH: &str = "WM_MESH";
/// `WM_MESH_BIND` — TCP bind address (default `0.0.0.0:7369`).
pub const ENV_MESH_BIND: &str = "WM_MESH_BIND";
/// `WM_MESH_PEER_ID` — readable node name (default derived from the key).
pub const ENV_MESH_PEER_ID: &str = "WM_MESH_PEER_ID";
/// `WM_MESH_INTERVAL` — beacon/auto-join cadence in seconds (default 5).
pub const ENV_MESH_INTERVAL: &str = "WM_MESH_INTERVAL";
/// `WM_MESH_AGENT_AWAY_SECS` — how long after the last agent request the
/// node still counts its agent as present (default 300).
pub const ENV_MESH_AGENT_AWAY_SECS: &str = "WM_MESH_AGENT_AWAY_SECS";

/// Whether the mesh transport was requested: `WM_MESH=1` (strict).
#[must_use]
pub fn env_requested() -> bool {
    parse_flag(std::env::var(ENV_MESH).ok().as_deref())
}

/// Strict flag parse: only exactly `1` enables (no truthy spellings).
#[must_use]
pub fn parse_flag(value: Option<&str>) -> bool {
    value.is_some_and(|v| v == "1")
}

fn env_or(key: &str, default: &str) -> String {
    std::env::var(key)
        .ok()
        .filter(|v| !v.trim().is_empty())
        .unwrap_or_else(|| default.to_string())
}

// ── MeshSlot ──────────────────────────────────────────────────────────

/// Shared slot holding the live node, created by the server at init and
/// filled by the CLI after `MeshNode::start`.
///
/// Tools and `/status` read it; an empty slot means the server runs
/// without the mesh transport.
#[derive(Default)]
pub struct MeshSlot(std::sync::RwLock<Option<Arc<MeshNode>>>);

impl MeshSlot {
    /// Create an empty slot.
    #[must_use]
    pub fn new() -> Arc<Self> {
        Arc::new(Self::default())
    }

    /// Install the live node (idempotent — the last install wins).
    pub fn set(&self, node: Arc<MeshNode>) {
        if let Ok(mut guard) = self.0.write() {
            *guard = Some(node);
        }
    }

    /// The live node, if the mesh transport is enabled.
    #[must_use]
    pub fn get(&self) -> Option<Arc<MeshNode>> {
        self.0.read().ok().and_then(|guard| guard.clone())
    }
}

// ── Configuration ─────────────────────────────────────────────────────

/// Configuration for a live mesh node.
#[derive(Debug, Clone)]
pub struct MeshNodeConfig {
    /// TCP bind address for the transport server.
    pub bind_addr: String,
    /// This node's peer ID.
    pub peer_id: String,
    /// Beacon + auto-join cadence in seconds.
    pub beacon_interval_sec: u64,
    /// Dial discovered peers automatically.
    pub auto_join: bool,
    /// UDP multicast group for discovery. Defaults to the production
    /// group; tests must use their own group — the default carries live
    /// LAN traffic whenever a real mesh node is beaconing on this host's
    /// network, and production beacons land in test registries.
    pub multicast_group: String,
    /// How long after the last agent request this node still counts its
    /// agent as present (`WM_MESH_AGENT_AWAY_SECS`, default 300). Node
    /// liveness and agent presence are different truths: the node can be
    /// up and beaconing while the agent is away, and that absence is a
    /// state to report, never a failure to fix.
    pub agent_away_secs: u64,
    /// Optional state directory for durable mesh state: the outbound
    /// mail slot (`mesh_mail_slot.json`) and the delivered-chat log
    /// (`mesh_chat_log.json`) live here and survive restarts. `None` =
    /// in-memory only (tests, throwaway nodes).
    pub state_dir: Option<std::path::PathBuf>,
}

impl MeshNodeConfig {
    /// Resolve the config from the environment (falling back to defaults).
    ///
    /// `bind_override` (the `--mesh-bind` flag) wins over `WM_MESH_BIND`.
    /// The peer ID defaults to `wm-` + the first 12 hex chars of the node's
    /// public key — stable across restarts when `WM_MESH_KEY` is set,
    /// unique otherwise. `WM_MESH_PEER_ID` gives it a readable name.
    #[must_use]
    pub fn from_env(bind_override: Option<&str>, keypair: &MeshKeyPair) -> Self {
        let bind_addr = bind_override
            .filter(|s| !s.trim().is_empty())
            .map_or_else(|| env_or(ENV_MESH_BIND, "0.0.0.0:7369"), String::from);
        let default_peer = format!("wm-{}", &keypair.public_key_hex()[..12]);
        let peer_id = env_or(ENV_MESH_PEER_ID, &default_peer);
        let beacon_interval_sec = std::env::var(ENV_MESH_INTERVAL)
            .ok()
            .and_then(|v| v.trim().parse::<u64>().ok())
            .filter(|v| *v > 0)
            .unwrap_or(crate::transport::DEFAULT_HEARTBEAT_INTERVAL_SEC);
        Self {
            bind_addr,
            peer_id,
            beacon_interval_sec,
            auto_join: true,
            multicast_group: crate::transport::MULTICAST_GROUP.to_string(),
            agent_away_secs: env_or(ENV_MESH_AGENT_AWAY_SECS, "300")
                .trim()
                .parse::<u64>()
                .ok()
                .filter(|v| *v > 0)
                .unwrap_or(300),
            state_dir: None,
        }
    }

    /// The address this node announces to peers. A `0.0.0.0` bind is not
    /// reachable as-is; the announced host becomes `127.0.0.1` (the local
    /// two-node proof works out of the box). For cross-host meshes set the
    /// bind (or `WM_MESH_BIND`) to a LAN-reachable address.
    #[must_use]
    pub fn announce_addr(&self) -> String {
        if let Some(port) = self.bind_addr.strip_prefix("0.0.0.0:") {
            format!("127.0.0.1:{port}")
        } else {
            self.bind_addr.clone()
        }
    }
}

/// The connection key the transport uses for a dialed address.
fn conn_key(addr: &str) -> String {
    format!("remote:{addr}")
}

/// Whether an error is a PERMANENT refusal (quarantine, identity/binding
/// rejection) rather than an availability failure. Refusals are never
/// queued; everything else (connect failed, dial/rpc timeout, dead
/// socket, peer not connected) is treated as availability and stored.
/// v0 heuristic: refusal shapes are explicit strings — a matching-refusal
/// false negative would queue a message that flush then drops on the next
/// refusal, so the failure mode is bounded.
fn is_refusal(text: &str) -> bool {
    text.contains("quarantined") || text.contains("identity") || text.contains("rejected")
}

// ── MeshNode ──────────────────────────────────────────────────────────

/// A live Sangha mesh node — transport + state + background tasks.
pub struct MeshNode {
    config: MeshNodeConfig,
    state: Arc<SanghaState>,
    transport: Arc<SanghaTransport>,
    /// Last agent activity observed on this node (`None` = no request
    /// seen yet — presence must be demonstrated, absence is the default
    /// reportable state).
    agent_activity: std::sync::Mutex<Option<std::time::Instant>>,
    /// Outbound store-and-forward queue (sender-side mail slot). Chat
    /// that cannot be delivered because the peer is unreachable is
    /// stored here (bounded, persisted) and flushed FIFO on the next
    /// successful join to that peer.
    mail_slot: std::sync::Mutex<crate::mail_slot::MailSlot>,
}

impl MeshNode {
    /// Start the node: bind the TCP transport, spawn the beacon listener
    /// and the auto-join loop.
    ///
    /// # Errors
    /// Fails before any task spawns when the TCP bind address is unusable
    /// (a pre-bind check keeps startup failures loud at the call site).
    pub async fn start(config: MeshNodeConfig, keypair: MeshKeyPair) -> Result<Arc<Self>> {
        // Bind HERE, in the caller's context: a bad bind address fails
        // loudly at startup instead of inside a spawned task. The listener
        // is handed straight to the serve loop (no re-bind window).
        let listener = tokio::net::TcpListener::bind(&config.bind_addr)
            .await
            .map_err(|e| {
                wm_core::CoreError::Internal(format!(
                    "mesh TCP bind {} failed: {e}",
                    config.bind_addr
                ))
            })?;

        let transport_config = TransportConfig {
            bind_addr: config.bind_addr.clone(),
            heartbeat_interval_sec: config.beacon_interval_sec,
            multicast_group: config.multicast_group.clone(),
            allow_unsigned_beacons: std::env::var("WM_MESH_ALLOW_UNSIGNED_BEACONS")
                .is_ok_and(|v| v.trim() == "1"),
            ..TransportConfig::default()
        };
        let chat_log_path = config
            .state_dir
            .as_ref()
            .map(|d| d.join("mesh_chat_log.json"));
        let state = Arc::new(SanghaState::with_persistence(
            config.peer_id.clone(),
            config.announce_addr(),
            keypair,
            chat_log_path,
        ));
        let transport = Arc::new(SanghaTransport::new(
            transport_config.clone(),
            Arc::clone(&state),
        ));
        let mail_slot = match &config.state_dir {
            Some(dir) => {
                let _ = std::fs::create_dir_all(dir);
                crate::mail_slot::MailSlot::restore(
                    crate::mail_slot::MailSlotConfig::default(),
                    dir.join("mesh_mail_slot.json"),
                )
            }
            None => crate::mail_slot::MailSlot::new(crate::mail_slot::MailSlotConfig::default()),
        };

        // TCP JSON-RPC server on the pre-bound listener.
        tokio::spawn({
            let t = Arc::clone(&transport);
            async move {
                if let Err(e) = t.serve_on(listener).await {
                    tracing::error!("mesh transport serve failed: {e}");
                }
            }
        });
        // Discovery receive side (UDP multicast listener).
        tokio::spawn({
            let s = Arc::clone(&state);
            async move {
                if let Err(e) = crate::transport::listen_for_beacons(s, &transport_config).await {
                    tracing::warn!("mesh beacon listener stopped: {e}");
                }
            }
        });
        // Auto-join: dial discovered peers and bind identities.
        let node = Arc::new(Self {
            config: config.clone(),
            state,
            transport,
            agent_activity: std::sync::Mutex::new(None),
            mail_slot: std::sync::Mutex::new(mail_slot),
        });
        if config.auto_join {
            tokio::spawn(auto_join_loop(
                Arc::clone(&node),
                std::time::Duration::from_secs(config.beacon_interval_sec.max(1)),
            ));
        }
        tracing::info!(
            peer_id = %node.config.peer_id,
            bind = %node.config.bind_addr,
            announce = %node.config.announce_addr(),
            "Sangha mesh node started"
        );
        Ok(node)
    }

    /// This node's peer ID.
    #[must_use]
    pub fn peer_id(&self) -> &str {
        &self.config.peer_id
    }

    /// This node's announced address.
    #[must_use]
    pub fn announce_addr(&self) -> String {
        self.config.announce_addr()
    }

    /// This node's public key (hex) — its mesh identity.
    #[must_use]
    pub fn public_key_hex(&self) -> String {
        self.state.keypair.public_key_hex()
    }

    /// Record agent activity (the server calls this on every JSON-RPC
    /// request). Presence must be demonstrated — an idle node's agent
    /// reads as away after the configured threshold.
    pub fn note_agent_activity(&self) {
        *self
            .agent_activity
            .lock()
            .expect("agent activity lock poisoned") = Some(std::time::Instant::now());
    }

    /// Whether this node's agent is present: a request was seen within
    /// the configured away threshold.
    #[must_use]
    pub fn agent_present(&self) -> bool {
        let last = self
            .agent_activity
            .lock()
            .expect("agent activity lock poisoned")
            .map(|t| t.elapsed());
        match last {
            None => false,
            Some(elapsed) => elapsed < std::time::Duration::from_secs(self.config.agent_away_secs),
        }
    }

    /// This node's signed identity announcement with its CURRENT agent
    /// presence — the single construction path for heartbeats, so joins
    /// and re-announcements always carry fresh state.
    fn identity_announcement(&self) -> PeerInfo {
        let mut identity = PeerInfo::new(&self.config.peer_id, self.config.announce_addr());
        identity.agent_present = self.agent_present();
        identity.signed(&self.state.keypair)
    }

    /// Dial `addr` **fresh** — every join drops any existing connection to
    /// the address first, then dials and sends our signed identity
    /// heartbeat so the remote binds our public key to our peer ID. The
    /// response carries the remote's discovery registry as observed after
    /// the bind.
    ///
    /// Fresh-dial discipline is the anti-ghost rule: a surviving connection
    /// entry may be a corpse (the remote died, or half-closed) — trusting
    /// it shadows the live peer that returned to the same address (the
    /// fleet-night retest defect). An explicit join is exactly the moment
    /// to pay the reconnect cost.
    ///
    /// # Errors
    /// Fails on connection errors or an identity rejection (e.g. we are
    /// quarantined on the remote, or our key conflicts with a binding).
    pub async fn join(&self, addr: &str) -> Result<Value> {
        let key = conn_key(addr);
        tracing::debug!(peer = %addr, "mesh join: fresh dial");
        self.transport.disconnect(&key).await;
        self.transport.connect_to_peer(addr).await?;
        let identity = self.identity_announcement();
        tracing::debug!(peer = %addr, "mesh join: connected, sending signed heartbeat");
        self.transport
            .rpc_call(
                &key,
                "heartbeat",
                serde_json::to_value(&identity).map_err(|e| {
                    wm_core::CoreError::Internal(format!("serialize identity: {e}"))
                })?,
            )
            .await?;
        tracing::debug!(peer = %addr, "mesh join: heartbeat accepted, reading remote registry");
        let remote_registry = self
            .transport
            .rpc_call(&key, "discover", Value::Null)
            .await?;
        tracing::debug!(peer = %addr, "mesh join: complete");
        // Mail flush: the peer just proved reachable — deliver anything
        // stored for it (FIFO; availability failure keeps the rest).
        let (mail_flushed, mail_remaining) = self.flush_mail_to(addr).await;
        Ok(json!({
            "connected": addr,
            "peer_id": self.config.peer_id,
            "remote_registry": remote_registry,
            "mail_flushed": mail_flushed,
            "mail_remaining": mail_remaining,
        }))
    }

    /// Send a signed chat message to `target` — a peer ID (resolved through
    /// the discovery registry) or a `host:port` address. Fresh dials carry
    /// the signed heartbeat first, so identity binds even on a self-healed
    /// connection. Locally quarantined peers are refused outright.
    ///
    /// **Store-and-forward:** when the peer is unreachable (offline, asleep,
    /// wedged) the message is stored in the bounded mail slot and delivered
    /// FIFO on the next successful join — the response carries
    /// `"status": "queued"`, `queued: true`, `reason_code: "agent_asleep"`,
    /// and the queue depth. Permanent refusals (quarantine, identity
    /// rejection) are errors, never queued. When the slot is full the call
    /// fails with `asleep_queue_full` and the bound `kind`.
    ///
    /// # Errors
    /// Fails when the target cannot be resolved, the peer is quarantined,
    /// the remote rejects the message, or the mail slot is full.
    pub async fn chat(&self, target: &str, channel: &str, content: &str) -> Result<Value> {
        let (peer_id, addr) = self.resolve_target(target).await?;
        if let Some(id) = &peer_id {
            if self.state.peers.lock().await.is_quarantined(id) {
                return Err(wm_core::CoreError::Tool(format!(
                    "peer '{id}' is quarantined on this node — release it before messaging"
                )));
            }
        }
        let key = conn_key(&addr);
        if !self.transport.connected_peers().await.contains(&key) {
            // A failed join is either availability (queue the message) or
            // refusal (propagate — e.g. we are quarantined on the remote).
            if let Err(e) = self.join(&addr).await {
                if !is_refusal(&e.to_string()) {
                    return self.queue_mail(&addr, peer_id.as_deref(), channel, content);
                }
                return Err(e);
            }
        }
        match self
            .transport
            .send_chat_remote(&key, channel, &self.config.peer_id, content)
            .await
        {
            Ok(_) => Ok(json!({
                "status": "ok",
                "queued": false,
                "to": addr,
                "peer_id": peer_id,
                "channel": channel,
                "signed_by": self.config.peer_id,
            })),
            Err(e) => {
                if !is_refusal(&e.to_string()) {
                    return self.queue_mail(&addr, peer_id.as_deref(), channel, content);
                }
                Err(e)
            }
        }
    }

    /// Store an undeliverable message in the mail slot (the sender-side
    /// IETF divergence: there is no relay to hold recipient queues, so the
    /// sender remembers). Returns the queued report or the `asleep_queue_full`
    /// error when a bound would be exceeded.
    fn queue_mail(
        &self,
        addr: &str,
        peer_id: Option<&str>,
        channel: &str,
        content: &str,
    ) -> Result<Value> {
        let (id, depth, bounds) = {
            let mut slot = self.mail_slot.lock().expect("mail slot lock poisoned");
            match slot.enqueue(addr, channel, &self.config.peer_id, content) {
                Ok(id) => (id, slot.total(), slot.bounds()),
                Err(full) => {
                    tracing::warn!(peer = %addr, kind = ?full.kind, "mesh mail slot full — message not stored");
                    return Err(wm_core::CoreError::Tool(format!(
                        "asleep_queue_full: mail slot bound reached (kind: {:?}) — \
                         message NOT stored; free the queue (sangha.mesh.mail drop/flush) and retry",
                        full.kind
                    )));
                }
            }
        };
        tracing::info!(peer = %addr, %id, depth, "mesh chat queued for delivery on rejoin");
        Ok(json!({
            "status": "queued",
            "queued": true,
            "id": id,
            "to": addr,
            "peer_id": peer_id,
            "channel": channel,
            "reason_code": "agent_asleep",
            "reason": "peer unreachable — stored for delivery on rejoin (FIFO, bounded, TTL)",
            "queue_depth": depth,
            "bounds": bounds,
            "signed_by": self.config.peer_id,
        }))
    }

    /// Flush the mail slot FIFO to one peer (called after every successful
    /// join and by the mail tool). A refused message (quarantined/identity
    /// on the remote) is dropped — it will never be deliverable. An
    /// availability failure stops the flush; the rest stays queued.
    /// Returns `(delivered, remaining)`.
    async fn flush_mail_to(&self, addr: &str) -> (usize, usize) {
        let pending = {
            let slot = self.mail_slot.lock().expect("mail slot lock poisoned");
            slot.entries_for(addr)
        };
        if pending.is_empty() {
            return (0, 0);
        }
        let key = conn_key(addr);
        let mut delivered_ids: Vec<String> = Vec::new();
        let mut dropped_ids: Vec<String> = Vec::new();
        for msg in &pending {
            match self
                .transport
                .send_chat_remote(&key, &msg.channel, &msg.sender, &msg.content)
                .await
            {
                Ok(_) => delivered_ids.push(msg.id.clone()),
                Err(e) => {
                    let text = e.to_string();
                    if !is_refusal(&text) {
                        tracing::debug!(peer = %addr, mail = %msg.id, "mail flush deferred: {text}");
                        break;
                    }
                    tracing::warn!(peer = %addr, mail = %msg.id, "mail dropped (permanent refusal): {text}");
                    dropped_ids.push(msg.id.clone());
                }
            }
        }
        let removed = {
            let mut slot = self.mail_slot.lock().expect("mail slot lock poisoned");
            slot.remove_ids(&delivered_ids);
            slot.remove_ids(&dropped_ids);
            slot.total()
        };
        if !delivered_ids.is_empty() {
            tracing::info!(peer = %addr, delivered = delivered_ids.len(), "mesh mail flushed");
        }
        (delivered_ids.len() + dropped_ids.len(), removed)
    }

    /// The mail slot's status summary (queue depth, bounds).
    #[must_use]
    pub fn mail_summary(&self) -> Value {
        self.mail_slot
            .lock()
            .expect("mail slot lock poisoned")
            .summary()
    }

    /// Full mail listing — every queued entry with its metadata plus the
    /// published bounds (IETF MUST publish actual bounds).
    #[must_use]
    pub fn mail_list(&self) -> Value {
        let entries: Vec<Value> = {
            let slot = self.mail_slot.lock().expect("mail slot lock poisoned");
            slot.entries()
                .iter()
                .map(|m| {
                    json!({
                        "id": m.id,
                        "peer": m.peer,
                        "channel": m.channel,
                        "sender": m.sender,
                        "content": m.content,
                        "queued_at": m.queued_at,
                        "attempts": m.attempts,
                    })
                })
                .collect()
        };
        let mut summary = self.mail_summary();
        summary["entries"] = json!(entries);
        summary
    }

    /// Force a flush now — all pending peers, or one address. The per-peer
    /// report names what went out and what stayed queued.
    pub async fn flush_mail(&self, peer: Option<&str>) -> Result<Value> {
        let peers: Vec<String> = match peer {
            Some(p) => vec![p.to_string()],
            None => self
                .mail_slot
                .lock()
                .expect("mail slot lock poisoned")
                .pending_peers(),
        };
        let mut reports = Vec::new();
        for addr in &peers {
            let (delivered, remaining) = self.flush_mail_to(addr).await;
            reports.push(json!({
                "peer": addr,
                "delivered": delivered,
                "remaining": remaining,
            }));
        }
        Ok(json!({
            "status": "ok",
            "flushed": reports,
            "mail": self.mail_summary(),
        }))
    }

    /// Drop one queued message by id (operator action).
    pub fn drop_mail(&self, id: &str) -> Result<Value> {
        let dropped = self
            .mail_slot
            .lock()
            .expect("mail slot lock poisoned")
            .drop_message(id);
        Ok(json!({
            "dropped": dropped,
            "id": id,
            "mail": self.mail_summary(),
        }))
    }

    /// Read received chat messages from a channel (newest last).
    ///
    /// # Errors
    /// Fails on internal errors only.
    pub async fn read_chat(&self, channel: &str, limit: usize) -> Result<Value> {
        let messages: Vec<Value> = {
            let chat = self.state.chat.lock().await;
            chat.read(channel, None)
                .iter()
                .rev()
                .take(limit)
                .map(|m| m.to_json())
                .collect()
        };
        Ok(json!({
            "channel": channel,
            "count": messages.len(),
            "messages": messages,
        }))
    }

    /// Quarantine a peer — the bad-apple rule at mesh level: registry
    /// quarantine (rejoin refused), chat messages purged, resource locks
    /// revoked, and the TCP connection dropped. Returns the action report.
    ///
    /// # Errors
    /// Fails when the peer is unknown to this node's registry.
    pub async fn quarantine_peer(&self, peer_id: &str, reason: &str) -> Result<Value> {
        let (_, addr) = self.resolve_target(peer_id).await?;
        let quarantined = self.state.peers.lock().await.quarantine(peer_id, reason);
        let purged = self.state.chat.lock().await.purge_sender(peer_id, None);
        let revoked = self.state.locks.lock().await.revoke_peer(peer_id);
        if quarantined {
            self.transport.disconnect(&conn_key(&addr)).await;
        }
        tracing::warn!(
            peer_id,
            reason,
            purged,
            revoked,
            "mesh peer quarantined — rejoin refused until released"
        );
        Ok(json!({
            "quarantined": quarantined,
            "peer_id": peer_id,
            "reason": reason,
            "purged_messages": purged,
            "revoked_locks": revoked,
        }))
    }

    /// Release a quarantined peer so it can rejoin on its next heartbeat.
    ///
    /// # Errors
    /// Fails on internal errors only (unknown peers report `released: false`).
    pub async fn release_quarantine(&self, peer_id: &str) -> Result<Value> {
        let released = self.state.peers.lock().await.release_quarantine(peer_id);
        Ok(json!({"released": released, "peer_id": peer_id}))
    }

    /// The quarantined peer IDs with their reasons.
    ///
    /// # Errors
    /// Fails on internal errors only.
    pub async fn quarantined(&self) -> Result<Value> {
        let list: Vec<Value> = self
            .state
            .peers
            .lock()
            .await
            .quarantined()
            .iter()
            .map(|p| json!({"peer_id": p.id, "reason": p.quarantine_reason}))
            .collect();
        Ok(json!({"quarantined": list}))
    }

    /// Full node status (async — used by the `sangha.mesh.status` tool).
    ///
    /// # Errors
    /// Fails on internal errors only.
    pub async fn status(&self) -> Result<Value> {
        let peers = self.state.peers.lock().await.summary();
        let chat = self.state.chat.lock().await.summary();
        let locks = self.state.locks.lock().await.summary();
        let connected = self.transport.connected_peers().await;
        Ok(self.status_body(Some(&peers), Some(&chat), Some(&locks), Some(&connected)))
    }

    /// Best-effort status for the synchronous `/status` probe: contended
    /// locks render as `null` instead of blocking the request path.
    #[must_use]
    pub fn status_try(&self) -> Value {
        let peers = self.state.peers.try_lock().ok().map(|g| g.summary());
        let chat = self.state.chat.try_lock().ok().map(|g| g.summary());
        let locks = self.state.locks.try_lock().ok().map(|g| g.summary());
        // Connected peers need an async read lock; report the list observed
        // without blocking (null when contended).
        let connected = self.transport.try_connected_peers();
        self.status_body(
            peers.as_ref(),
            chat.as_ref(),
            locks.as_ref(),
            connected.as_deref(),
        )
    }

    fn status_body(
        &self,
        peers: Option<&Value>,
        chat: Option<&Value>,
        locks: Option<&Value>,
        connected: Option<&[String]>,
    ) -> Value {
        let unwrap_or_null = |v: Option<&Value>| v.cloned().unwrap_or(Value::Null);
        json!({
            "enabled": true,
            "peer_id": self.config.peer_id,
            "public_key": self.state.keypair.public_key_hex(),
            "bind": self.config.bind_addr,
            "announce": self.config.announce_addr(),
            "beacon_interval_sec": self.config.beacon_interval_sec,
            "auto_join": self.config.auto_join,
            "agent_present": self.agent_present(),
            "connected": connected.map_or(Value::Null, |c| json!(c)),
            "peers": unwrap_or_null(peers),
            "chat": unwrap_or_null(chat),
            "locks": unwrap_or_null(locks),
            "mail": self.mail_summary(),
        })
    }

    /// Resolve a chat target to `(peer_id, address)`. An address
    /// (`host:port`) passes through; a peer ID is looked up in the
    /// discovery registry.
    async fn resolve_target(&self, target: &str) -> Result<(Option<String>, String)> {
        if target.contains(':') {
            return Ok((None, target.to_string()));
        }
        let found = {
            let peers = self.state.peers.lock().await;
            peers
                .alive_peers()
                .into_iter()
                .find(|p| p.id == target)
                .map(|p| p.address.clone())
                // Fall back to quarantined peers so quarantine/release can
                // still resolve a target that is no longer "alive".
                .or_else(|| {
                    peers
                        .quarantined()
                        .into_iter()
                        .find(|p| p.id == target)
                        .map(|p| p.address.clone())
                })
        };
        if let Some(addr) = found {
            Ok((Some(target.to_string()), addr))
        } else {
            Err(wm_core::CoreError::NotFound(format!(
                "mesh peer '{target}' not in the discovery registry — \
                 use its address (host:port) or wait for its beacon"
            )))
        }
    }
}

/// Periodically dial discovered peers we are not connected to, carrying the
/// signed identity heartbeat on each fresh dial. Quarantined peers are
/// never dialed.
async fn auto_join_loop(node: Arc<MeshNode>, interval: std::time::Duration) {
    // Last agent-presence state we announced to connected peers —
    // re-announcement is change-triggered, plus a periodic reconciliation
    // beat: an announcement is an idempotent state update, and a lost one
    // (connection blip at the flip moment) must heal within a few cycles,
    // not stick forever.
    let mut last_announced_present = node.agent_present();
    let mut cycles: u64 = 0;
    loop {
        tokio::time::sleep(interval).await;
        cycles = cycles.wrapping_add(1);
        // Registry decay: peers silent past the heartbeat timeout drop
        // from the registry (quarantined entries are spared — the
        // bad-apple record survives). Beacons rebuild entries on wake;
        // decay keeps `alive` honest and stops the loop from forever
        // dialing the dead.
        let evicted = node.state.peers.lock().await.evict_stale();
        if evicted > 0 {
            tracing::debug!(evicted, "mesh registry decayed stale peers");
        }
        // Mail-slot TTL sweep: expired entries leave the queue undelivered
        // (the IETF purge-or-reject rule).
        let purged = node
            .mail_slot
            .lock()
            .expect("mail slot lock poisoned")
            .purge_expired();
        if purged > 0 {
            tracing::debug!(purged, "mesh mail slot expired entries purged");
        }
        // Agent-presence re-announce: our own presence flipped since the
        // last announcement, or the reconciliation beat came due — push a
        // signed heartbeat to every connected peer so their registries
        // reflect the truth (the join carries the state too; this covers
        // the no-join case).
        let now_present = node.agent_present();
        if now_present != last_announced_present || cycles % 5 == 0 {
            let identity = node.identity_announcement();
            let params = match serde_json::to_value(&identity) {
                Ok(v) => v,
                Err(e) => {
                    tracing::warn!("agent-presence announcement serialize failed: {e}");
                    Value::Null
                }
            };
            for key in node.transport.connected_peers().await {
                let _ = node
                    .transport
                    .rpc_call(&key, "heartbeat", params.clone())
                    .await;
            }
            tracing::debug!(present = now_present, "mesh agent-presence re-announced");
            last_announced_present = now_present;
        }
        let candidates: Vec<String> = {
            let peers = node.state.peers.lock().await;
            peers
                .alive_peers()
                .into_iter()
                .filter(|p| !p.quarantined && p.address != node.config.announce_addr())
                .map(|p| p.address.clone())
                .collect()
        };
        for addr in candidates {
            let key = conn_key(&addr);
            if node.transport.connected_peers().await.contains(&key) {
                continue;
            }
            match node.join(&addr).await {
                Ok(_) => tracing::info!(%addr, "mesh auto-join bound identity"),
                Err(e) => tracing::debug!(%addr, "mesh auto-join deferred: {e}"),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::crypto::MeshKeyPair;
    use std::future::Future;
    use std::time::Duration;

    /// A wedged mesh rpc must fail the test with a name, not hang the CI
    /// job forever (tokio tests have no built-in time limit).
    async fn within<T>(
        what: &str,
        fut: impl Future<Output = wm_core::Result<T>>,
    ) -> wm_core::Result<T> {
        const LIMIT: Duration = Duration::from_secs(10);
        tokio::time::timeout(LIMIT, fut)
            .await
            .unwrap_or_else(|_| panic!("{what} timed out after {LIMIT:?}"))
    }

    /// Spawn on the given multicast group. Nodes are never shut down —
    /// their beacon loops run as zombies for the whole test binary — so
    /// each test needs its own group: zombie beacons and live LAN traffic
    /// (production nodes beacon on the default group) otherwise corrupt
    /// exact-count assertions (observed live 2026-08-31: a production
    /// peer's beacon landed in a unit-test registry).
    async fn spawn_node_with(
        peer_id: &str,
        port: u16,
        auto_join: bool,
        group: &str,
        away_secs: u64,
    ) -> Arc<MeshNode> {
        let keypair = MeshKeyPair::from_seed(peer_id.as_bytes());
        let config = MeshNodeConfig {
            bind_addr: format!("127.0.0.1:{port}"),
            peer_id: peer_id.to_string(),
            beacon_interval_sec: 1,
            auto_join,
            multicast_group: group.to_string(),
            agent_away_secs: away_secs,
            state_dir: None,
        };
        MeshNode::start(config, keypair)
            .await
            .unwrap_or_else(|e| panic!("{peer_id} start failed: {e}"))
    }

    /// Isolated groups for tests asserting exact registry counts —
    /// one per counting test, since a test's zombie nodes keep
    /// beaconing after it returns.
    const TEST_GROUP_A: &str = "224.0.0.71";
    const TEST_GROUP_B: &str = "224.0.0.72";
    const TEST_GROUP_C: &str = "224.0.0.73";
    const TEST_GROUP_D: &str = "224.0.0.74";

    #[test]
    fn flag_parse_is_strict() {
        // Mirrors WM_LANDLOCK: only exactly "1" enables.
        assert!(!parse_flag(None));
        assert!(parse_flag(Some("1")));
        assert!(!parse_flag(Some("0")));
        assert!(!parse_flag(Some("true")));
        assert!(!parse_flag(Some("")));
    }

    #[test]
    fn announce_addr_normalizes_wildcard_bind() {
        let kp = MeshKeyPair::from_seed(b"cfg");
        let config = MeshNodeConfig {
            bind_addr: "0.0.0.0:7369".into(),
            peer_id: "n".into(),
            beacon_interval_sec: 5,
            auto_join: true,
            multicast_group: crate::transport::MULTICAST_GROUP.to_string(),
            agent_away_secs: 300,
            state_dir: None,
        };
        assert_eq!(config.announce_addr(), "127.0.0.1:7369");
        let explicit = MeshNodeConfig {
            bind_addr: "192.168.1.10:7369".into(),
            ..config
        };
        assert_eq!(explicit.announce_addr(), "192.168.1.10:7369");
        // Peer ID default derives from the key.
        let derived = MeshNodeConfig::from_env(None, &kp);
        assert_eq!(
            derived.peer_id,
            format!("wm-{}", &kp.public_key_hex()[..12])
        );
    }

    #[tokio::test]
    async fn slot_set_get_roundtrip() {
        let slot = MeshSlot::new();
        assert!(slot.get().is_none());
        let node = spawn_node_with("slot-node", 17_601, false, TEST_GROUP_A, 300).await;
        slot.set(Arc::clone(&node));
        assert_eq!(slot.get().expect("node").peer_id(), "slot-node");
    }

    #[tokio::test]
    async fn join_binds_identity_both_ways_and_chat_flows() {
        // Exact-count assert below → own group (zombie + LAN isolation).
        let a = spawn_node_with("jb-node-a", 17_602, false, TEST_GROUP_B, 300).await;
        let b = spawn_node_with("jb-node-b", 17_603, false, TEST_GROUP_B, 300).await;

        // A joins B: A's signed heartbeat lands on B → B binds A's key.
        // Membership style, not exact counts: on a host running a live
        // production node, that node's registry holds stale test addresses
        // from earlier runs and its auto-join keeps dialing them — foreign
        // entries can appear in any test registry over TCP even with
        // multicast isolation (observed live: `t4800s`).
        let report = within("a join b", a.join("127.0.0.1:17603"))
            .await
            .expect("a join b");
        assert_eq!(report["connected"], "127.0.0.1:17603");
        let peers = report["remote_registry"]["peers"]
            .as_array()
            .cloned()
            .unwrap_or_default();
        assert!(
            peers.iter().any(|p| p["id"] == "jb-node-a"),
            "B must have registered A: {report}"
        );
        assert!(
            peers.iter().all(|p| p["id"] != "jb-node-b"),
            "a node must never register itself: {report}"
        );

        // B joins A so both registries know both peers.
        within("b join a", b.join("127.0.0.1:17602"))
            .await
            .expect("b join a");

        // Chat by peer ID (resolved through the registry), signed.
        let sent = within("a chat b", a.chat("jb-node-b", "general", "hello from a"))
            .await
            .expect("a chat b");
        assert_eq!(sent["status"], "ok");
        assert_eq!(sent["peer_id"], "jb-node-b");

        // B received the signed message (async poll — the direct read
        // raced a rare injection delay under load).
        let deadline = std::time::Instant::now() + Duration::from_secs(10);
        let inbox = loop {
            let inbox = b.read_chat("general", 10).await.expect("b read");
            if inbox["count"] == 1 {
                break inbox;
            }
            assert!(
                std::time::Instant::now() < deadline,
                "B never received A's chat: {inbox}"
            );
            tokio::time::sleep(Duration::from_millis(200)).await;
        };
        assert_eq!(inbox["messages"][0]["sender"], "jb-node-a");
        assert_eq!(inbox["messages"][0]["content"], "hello from a");
    }

    #[tokio::test]
    async fn join_dials_fresh_and_leaves_no_ghost_entries() {
        // Membership asserts, not exact counts: on one host, every
        // wildcard-bound listener receives every local group's multicast
        // (Linux REUSEPORT demux) — the LAN bus is shared by design and
        // foreign entries can appear in any registry (observed live).
        let a = spawn_node_with("gd-node-a", 17_607, false, TEST_GROUP_C, 300).await;
        let b = spawn_node_with("gd-node-b", 17_608, false, TEST_GROUP_C, 300).await;

        within("first join", a.join("127.0.0.1:17608"))
            .await
            .expect("first join");

        // An explicit re-join must dial FRESH — drop the surviving stream
        // and reconnect — instead of trusting a possibly-dead entry (the
        // fleet-night ghost-shadow defect). It must succeed and leave
        // exactly one connection entry for the address.
        within("re-join", a.join("127.0.0.1:17608"))
            .await
            .expect("re-join");

        let keys = a.transport.connected_peers().await;
        assert_eq!(
            keys,
            vec!["remote:127.0.0.1:17608".to_string()],
            "re-join must not duplicate or strand connection entries: {keys:?}"
        );
        let status = b.status().await.expect("b status");
        let peers = status["peers"]["peers"]
            .as_array()
            .cloned()
            .unwrap_or_default();
        let a_entry = peers
            .iter()
            .find(|p| p["id"] == "gd-node-a")
            .unwrap_or_else(|| panic!("B must still track A: {status}"));
        assert_eq!(a_entry["address"], "127.0.0.1:17607", "{status}");
        assert!(
            !peers.iter().any(|p| p["id"] == "gd-node-b"),
            "a node must never register itself: {status}"
        );
    }

    #[tokio::test]
    async fn status_discloses_own_agent_presence() {
        let node = spawn_node_with("sp-node-a", 17_609, false, TEST_GROUP_A, 300).await;
        // No request seen yet — absence is the honest default state.
        let status = node.status().await.expect("status");
        assert_eq!(status["agent_present"], false, "{status}");
        // A request flips the node's own presence.
        node.note_agent_activity();
        let status = node.status().await.expect("status");
        assert_eq!(status["agent_present"], true, "{status}");
    }

    #[tokio::test]
    async fn agent_presence_transitions_propagate_to_peers() {
        // The fleet-night topology, asserted live: node up + agent active
        // = online; node up + agent away = away. Transitions propagate to
        // connected peers via change-triggered signed heartbeats.
        //
        // All polling uses async sleep: a std::thread::sleep inside a
        // current-thread tokio test blocks the executor and starves the
        // very loops being observed.
        let a = spawn_node_with("pr-node-a", 17_610, true, TEST_GROUP_D, 2).await;
        let b = spawn_node_with("pr-node-b", 17_611, true, TEST_GROUP_D, 2).await;

        // A's agent is active; the join heartbeat carries presence.
        a.note_agent_activity();
        within("a join b", a.join("127.0.0.1:17611"))
            .await
            .expect("a join b");

        let presence_of = |status: &Value, id: &str| {
            status["peers"]["peers"]
                .as_array()
                .and_then(|ps| ps.iter().find(|p| p["id"] == id))
                .map(|p| p["presence"].clone())
        };
        const POLL: Duration = Duration::from_millis(200);

        // Hold A's presence through the poll window — A stays active while
        // B's view converges.
        let deadline = std::time::Instant::now() + Duration::from_secs(15);
        loop {
            a.note_agent_activity();
            let s = b.status_try();
            if presence_of(&s, "pr-node-a") == Some(json!("online")) {
                break;
            }
            assert!(
                std::time::Instant::now() < deadline,
                "B sees A online did not happen in time: {s}"
            );
            tokio::time::sleep(POLL).await;
        }

        // A goes idle past its away threshold; the auto-join loop
        // re-announces the flip (and the reconciliation beat backstops it).
        tokio::time::sleep(Duration::from_millis(2_600)).await;
        let deadline = std::time::Instant::now() + Duration::from_secs(15);
        loop {
            let s = b.status_try();
            if presence_of(&s, "pr-node-a") == Some(json!("away")) {
                break;
            }
            assert!(
                std::time::Instant::now() < deadline,
                "B sees A away did not happen in time: {s}"
            );
            tokio::time::sleep(POLL).await;
        }

        // A returns; the flip propagates again.
        a.note_agent_activity();
        let deadline = std::time::Instant::now() + Duration::from_secs(15);
        loop {
            a.note_agent_activity();
            let s = b.status_try();
            if presence_of(&s, "pr-node-a") == Some(json!("online")) {
                break;
            }
            assert!(
                std::time::Instant::now() < deadline,
                "B sees A online again did not happen in time: {s}"
            );
            tokio::time::sleep(POLL).await;
        }
    }

    #[tokio::test]
    async fn chat_to_offline_peer_queues_and_delivers_on_rejoin() {
        // The S3 acceptance: send to an offline peer → queued (agent_asleep,
        // depth reported); the peer returns → join flushes FIFO → delivered.
        let a = spawn_node_with("ms-node-a", 17_621, false, TEST_GROUP_A, 300).await;
        // B does not exist yet — the address is a dead dial.
        let queued = within(
            "chat to offline peer",
            a.chat("127.0.0.1:17622", "general", "for when you wake"),
        )
        .await
        .expect("chat must queue, not fail");
        assert_eq!(queued["status"], "queued", "{queued}");
        assert_eq!(queued["queued"], true);
        assert_eq!(queued["reason_code"], "agent_asleep");
        assert_eq!(queued["queue_depth"], 1);
        assert_eq!(a.mail_summary()["queued_total"], 1);

        // B comes up; A joins — the join flushes the slot FIFO.
        let b = spawn_node_with("ms-node-b", 17_622, false, TEST_GROUP_A, 300).await;
        let report = within("a join b (flush)", a.join("127.0.0.1:17622"))
            .await
            .expect("a join b");
        assert_eq!(report["mail_flushed"], 1, "{report}");
        assert_eq!(report["mail_remaining"], 0);

        // B received the stored message; A's slot is empty.
        let deadline = std::time::Instant::now() + Duration::from_secs(10);
        let inbox = loop {
            let inbox = b.read_chat("general", 10).await.expect("b read");
            if inbox["count"].as_u64().is_some_and(|c| c >= 1) {
                break inbox;
            }
            assert!(
                std::time::Instant::now() < deadline,
                "queued mail was never delivered: {inbox}"
            );
            tokio::time::sleep(Duration::from_millis(200)).await;
        };
        assert_eq!(inbox["messages"][0]["content"], "for when you wake");
        assert_eq!(inbox["messages"][0]["sender"], "ms-node-a");
        assert_eq!(a.mail_summary()["queued_total"], 0);
    }

    #[tokio::test]
    async fn mail_slot_and_chat_log_persist_across_node_restart() {
        // Both halves of the mail-slot survive restart: the sender's queued
        // messages and the receiver's delivered chat log.
        let dir_a = tempfile::tempdir().expect("state dir a");
        let dir_b = tempfile::tempdir().expect("state dir b");
        let keypair_a = MeshKeyPair::from_seed(b"ms-persist-a");
        let keypair_b = MeshKeyPair::from_seed(b"ms-persist-b");
        let mk_config = |port: u16, dir: &std::path::Path| MeshNodeConfig {
            bind_addr: format!("127.0.0.1:{port}"),
            peer_id: if port == 17_624 {
                "mp-node-b".into()
            } else {
                "mp-node-a".into()
            },
            beacon_interval_sec: 1,
            auto_join: false,
            multicast_group: TEST_GROUP_B.to_string(),
            agent_away_secs: 300,
            state_dir: Some(dir.to_path_buf()),
        };

        // Generation 1: A queues mail to a dead peer; B receives a live chat.
        {
            let a = MeshNode::start(mk_config(17_623, dir_a.path()), keypair_a.clone())
                .await
                .expect("a gen1");
            let queued = a
                .chat("127.0.0.1:17699", "general", "queued before restart")
                .await
                .expect("queue to dead peer");
            assert_eq!(queued["queued"], true, "{queued}");
            let _b = MeshNode::start(mk_config(17_624, dir_b.path()), keypair_b.clone())
                .await
                .expect("b gen1");
            within("a join b", a.join("127.0.0.1:17624"))
                .await
                .expect("a join b");
            within(
                "live chat",
                a.chat("127.0.0.1:17624", "general", "delivered live"),
            )
            .await
            .expect("live chat");
            // Explicit drop; the zombies keep running but the FILES persist.
            // (MeshNode has no shutdown yet — file state is the restart truth.)
        }

        // Generation 2: fresh nodes, same state dirs, same identities.
        {
            let a = MeshNode::start(mk_config(17_625, dir_a.path()), keypair_a.clone())
                .await
                .expect("a gen2");
            let mail = a.mail_list();
            assert_eq!(
                mail["queued_total"], 1,
                "sender's queued mail must survive restart: {mail}"
            );
            assert_eq!(
                mail["entries"][0]["content"], "queued before restart",
                "{mail}"
            );
            let b = MeshNode::start(mk_config(17_624 + 100, dir_b.path()), keypair_b)
                .await
                .expect("b gen2");
            let inbox = b.read_chat("general", 10).await.expect("b gen2 read");
            assert_eq!(
                inbox["count"], 1,
                "receiver's delivered chat must survive restart: {inbox}"
            );
            assert_eq!(inbox["messages"][0]["content"], "delivered live");
            assert_eq!(inbox["messages"][0]["sender"], "mp-node-a");
        }
    }

    #[tokio::test]
    async fn chat_to_unresolvable_id_fails_without_queueing() {
        // An unknown peer ID is not an offline peer: there is no address to
        // deliver to, so nothing may be queued (the error already tells the
        // caller to use an address).
        let a = spawn_node_with("ms-node-c", 17_626, false, TEST_GROUP_A, 300).await;
        let err = within(
            "chat to unknown id",
            a.chat("ghost-peer", "general", "nowhere to go"),
        )
        .await;
        assert!(err.is_err(), "{err:?}");
        assert_eq!(a.mail_summary()["queued_total"], 0);
    }

    #[tokio::test]
    async fn quarantine_cuts_off_and_refuses_rejoin() {
        let a = spawn_node_with("q-node-a", 17_604, false, TEST_GROUP_A, 300).await;
        let b = spawn_node_with("q-node-b", 17_605, false, TEST_GROUP_A, 300).await;
        within("a join b", a.join("127.0.0.1:17605"))
            .await
            .expect("a join b");
        within("b join a", b.join("127.0.0.1:17604"))
            .await
            .expect("b join a");

        // B quarantines A: locks revoked, messages purged, connection dropped.
        let report = within("quarantine", b.quarantine_peer("q-node-a", "e2e bad apple"))
            .await
            .expect("quarantine");
        assert_eq!(report["quarantined"], true);
        assert_eq!(report["revoked_locks"], 0);

        // B's status shows A quarantined.
        let listed = b.quarantined().await.expect("list");
        assert_eq!(listed["quarantined"][0]["peer_id"], "q-node-a");

        // A's further chat is refused: the connection was dropped and the
        // re-dial's identity heartbeat hits the quarantine refusal.
        let refused = within(
            "chat after quarantine",
            a.chat("q-node-b", "general", "let me back in"),
        )
        .await;
        assert!(
            refused.is_err(),
            "quarantined peer must not rejoin or send: {refused:?}"
        );

        // Release → rejoin works again.
        let released = b.release_quarantine("q-node-a").await.expect("release");
        assert_eq!(released["released"], true);
        within("rejoin after release", a.join("127.0.0.1:17605"))
            .await
            .expect("rejoin after release");
    }

    #[tokio::test]
    async fn status_reports_node_shape() {
        let node = spawn_node_with("st-node-a", 17_606, false, TEST_GROUP_A, 300).await;
        let status = node.status().await.expect("status");
        assert_eq!(status["enabled"], true);
        assert_eq!(status["peer_id"], "st-node-a");
        assert_eq!(status["announce"], "127.0.0.1:17606");
        assert!(status["public_key"].as_str().is_some_and(|k| k.len() == 64));
        // The sync variant never blocks and carries the same identity.
        let sync = node.status_try();
        assert_eq!(sync["peer_id"], "st-node-a");
    }
}
