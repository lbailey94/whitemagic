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

// ── MeshNode ──────────────────────────────────────────────────────────

/// A live Sangha mesh node — transport + state + background tasks.
pub struct MeshNode {
    config: MeshNodeConfig,
    state: Arc<SanghaState>,
    transport: Arc<SanghaTransport>,
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
            ..TransportConfig::default()
        };
        let state = Arc::new(SanghaState::with_keypair(
            config.peer_id.clone(),
            config.announce_addr(),
            keypair,
        ));
        let transport = Arc::new(SanghaTransport::new(
            transport_config.clone(),
            Arc::clone(&state),
        ));

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

    /// Dial `addr` (if not already connected) and send our signed identity
    /// heartbeat so the remote binds our public key to our peer ID. The
    /// response carries the remote's discovery registry as observed after
    /// the bind.
    ///
    /// # Errors
    /// Fails on connection errors or an identity rejection (e.g. we are
    /// quarantined on the remote, or our key conflicts with a binding).
    pub async fn join(&self, addr: &str) -> Result<Value> {
        let key = conn_key(addr);
        if !self.transport.connected_peers().await.contains(&key) {
            self.transport.connect_to_peer(addr).await?;
        }
        let identity = PeerInfo::new(&self.config.peer_id, self.config.announce_addr())
            .signed(&self.state.keypair);
        self.transport
            .rpc_call(
                &key,
                "heartbeat",
                serde_json::to_value(&identity).map_err(|e| {
                    wm_core::CoreError::Internal(format!("serialize identity: {e}"))
                })?,
            )
            .await?;
        let remote_registry = self
            .transport
            .rpc_call(&key, "discover", Value::Null)
            .await?;
        Ok(json!({
            "connected": addr,
            "peer_id": self.config.peer_id,
            "remote_registry": remote_registry,
        }))
    }

    /// Send a signed chat message to `target` — a peer ID (resolved through
    /// the discovery registry) or a `host:port` address. Fresh dials carry
    /// the signed heartbeat first, so identity binds even on a self-healed
    /// connection. Locally quarantined peers are refused outright.
    ///
    /// # Errors
    /// Fails when the target cannot be resolved, the peer is quarantined
    /// locally, or the remote rejects the message (unknown/unbound sender
    /// with a bad signature, quarantined on the remote, ...).
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
            self.join(&addr).await?;
        }
        self.transport
            .send_chat_remote(&key, channel, &self.config.peer_id, content)
            .await?;
        Ok(json!({
            "status": "ok",
            "to": addr,
            "peer_id": peer_id,
            "channel": channel,
            "signed_by": self.config.peer_id,
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
            "connected": connected.map_or(Value::Null, |c| json!(c)),
            "peers": unwrap_or_null(peers),
            "chat": unwrap_or_null(chat),
            "locks": unwrap_or_null(locks),
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
    loop {
        tokio::time::sleep(interval).await;
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

    async fn spawn_node_with(peer_id: &str, port: u16, auto_join: bool) -> Arc<MeshNode> {
        let keypair = MeshKeyPair::from_seed(peer_id.as_bytes());
        let config = MeshNodeConfig {
            bind_addr: format!("127.0.0.1:{port}"),
            peer_id: peer_id.to_string(),
            beacon_interval_sec: 1,
            auto_join,
        };
        MeshNode::start(config, keypair)
            .await
            .unwrap_or_else(|e| panic!("{peer_id} start failed: {e}"))
    }

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
        let node = spawn_node_with("slot-node", 17_601, false).await;
        slot.set(Arc::clone(&node));
        assert_eq!(slot.get().expect("node").peer_id(), "slot-node");
    }

    #[tokio::test]
    async fn join_binds_identity_both_ways_and_chat_flows() {
        let a = spawn_node_with("node-a", 17_602, false).await;
        let b = spawn_node_with("node-b", 17_603, false).await;

        // A joins B: A's signed heartbeat lands on B → B binds A's key.
        let report = within("a join b", a.join("127.0.0.1:17603"))
            .await
            .expect("a join b");
        assert_eq!(report["connected"], "127.0.0.1:17603");
        // B's registry now contains A (the heartbeat registered it).
        assert_eq!(
            report["remote_registry"]["peer_count"].as_u64(),
            Some(1),
            "B must have registered A: {report}"
        );

        // B joins A so both registries know both peers.
        within("b join a", b.join("127.0.0.1:17602"))
            .await
            .expect("b join a");

        // Chat by peer ID (resolved through the registry), signed.
        let sent = within("a chat b", a.chat("node-b", "general", "hello from a"))
            .await
            .expect("a chat b");
        assert_eq!(sent["status"], "ok");
        assert_eq!(sent["peer_id"], "node-b");

        // B received the signed message.
        let inbox = b.read_chat("general", 10).await.expect("b read");
        assert_eq!(inbox["count"], 1, "B must have A's message: {inbox}");
        assert_eq!(inbox["messages"][0]["sender"], "node-a");
        assert_eq!(inbox["messages"][0]["content"], "hello from a");
    }

    #[tokio::test]
    async fn quarantine_cuts_off_and_refuses_rejoin() {
        let a = spawn_node_with("node-a", 17_604, false).await;
        let b = spawn_node_with("node-b", 17_605, false).await;
        within("a join b", a.join("127.0.0.1:17605"))
            .await
            .expect("a join b");
        within("b join a", b.join("127.0.0.1:17604"))
            .await
            .expect("b join a");

        // B quarantines A: locks revoked, messages purged, connection dropped.
        let report = within("quarantine", b.quarantine_peer("node-a", "e2e bad apple"))
            .await
            .expect("quarantine");
        assert_eq!(report["quarantined"], true);
        assert_eq!(report["revoked_locks"], 0);

        // B's status shows A quarantined.
        let listed = b.quarantined().await.expect("list");
        assert_eq!(listed["quarantined"][0]["peer_id"], "node-a");

        // A's further chat is refused: the connection was dropped and the
        // re-dial's identity heartbeat hits the quarantine refusal.
        let refused = within(
            "chat after quarantine",
            a.chat("node-b", "general", "let me back in"),
        )
        .await;
        assert!(
            refused.is_err(),
            "quarantined peer must not rejoin or send: {refused:?}"
        );

        // Release → rejoin works again.
        let released = b.release_quarantine("node-a").await.expect("release");
        assert_eq!(released["released"], true);
        within("rejoin after release", a.join("127.0.0.1:17605"))
            .await
            .expect("rejoin after release");
    }

    #[tokio::test]
    async fn status_reports_node_shape() {
        let node = spawn_node_with("node-a", 17_606, false).await;
        let status = node.status().await.expect("status");
        assert_eq!(status["enabled"], true);
        assert_eq!(status["peer_id"], "node-a");
        assert_eq!(status["announce"], "127.0.0.1:17606");
        assert!(status["public_key"].as_str().is_some_and(|k| k.len() == 64));
        // The sync variant never blocks and carries the same identity.
        let sync = node.status_try();
        assert_eq!(sync["peer_id"], "node-a");
    }
}
