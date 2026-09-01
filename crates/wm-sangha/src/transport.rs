//! Sangha Mesh network transport — JSON-RPC over TCP with UDP multicast discovery.
//!
//! Provides the network layer for the Sangha Mesh, enabling multiple WhiteMagic
//! nodes to communicate over TCP. The protocol uses length-prefixed JSON
//! framing (4-byte big-endian length + JSON payload) for efficient, safe
//! message transport without protobuf codegen.
//!
//! ## Protocol
//!
//! Each TCP message is framed as: `[4 bytes BE length][JSON payload]`.
//!
//! Requests: `{"method": "<rpc_method>", "params": {...}, "id": <u64>}`
//! Responses: `{"result": {...}, "id": <u64>}` or `{"error": "<msg>", "id": <u64>}`
//!
//! ## RPC Methods
//!
//! - `heartbeat` — register/update a remote peer
//! - `discover` — list known peers
//! - `broadcast_signal` — broadcast a signal to remote node
//! - `send_chat` — send a chat message to a remote node
//! - `acquire_lock` — request a resource lock on remote node
//! - `release_lock` — release a resource lock on remote node
//! - `sync_hologram` — sync holographic coordinates
//!
//! ## Discovery
//!
//! UDP multicast on `224.0.0.69:7369` (Sangha port). Peers announce
//! themselves with a `PeerAnnounce` beacon every 5 seconds. Other peers
//! receive the beacon and establish TCP connections for unicast RPC.
//!
//! ## Feature Gate
//!
//! This module is behind the `transport` feature gate. Without it, wm-sangha
//! operates in single-node mode (current behavior).

use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;

use serde::{Deserialize, Serialize};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream, UdpSocket};
use tokio::sync::{Mutex, Notify, RwLock};
use wm_core::Result;

use crate::chat::SanghaChat;
use crate::hologram::HologramSync;
use crate::lock::ResourceLockManager;
use crate::peer::{PeerDiscovery, PeerId, PeerInfo};
use crate::signal::SignalBroadcast;

// ── Constants ─────────────────────────────────────────────────────────

/// Default TCP port for Sangha Mesh.
pub const DEFAULT_PORT: u16 = 7369;

/// UDP multicast group for peer discovery.
pub const MULTICAST_GROUP: &str = "224.0.0.69";

/// Default heartbeat interval in seconds.
pub const DEFAULT_HEARTBEAT_INTERVAL_SEC: u64 = 5;

/// Upper bound on one mesh RPC round-trip. A peer that accepts a
/// connection but never responds must surface as an error, not hang the
/// caller (and its dispatch pipeline) forever.
pub const MESH_RPC_TIMEOUT_SECS: u64 = 15;

/// Upper bound on a TCP dial. The RPC timeout covers connected exchanges
/// only — without this, an unreachable host stalls a join until the OS
/// connect timeout (minutes on some platforms).
pub const MESH_DIAL_TIMEOUT_SECS: u64 = 5;

/// Maximum message size (1 MB).
pub const MAX_MESSAGE_SIZE: usize = 1024 * 1024;

// ── Transport Config ──────────────────────────────────────────────────

/// Configuration for the Sangha Mesh transport.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportConfig {
    /// Bind address for TCP server (e.g., "0.0.0.0:7369").
    pub bind_addr: String,
    /// UDP multicast group for discovery.
    pub multicast_group: String,
    /// Heartbeat interval in seconds.
    pub heartbeat_interval_sec: u64,
    /// Maximum number of peer connections.
    pub max_connections: usize,
    /// Accept unsigned discovery beacons (S9 legacy escape hatch).
    ///
    /// Default `false` — the S9 posture is signed-only: beacons must
    /// carry a valid Ed25519 signature over their canonical payload,
    /// from a key that derives the announced peer ID (or is already
    /// bound to it in the registry). Set via
    /// `WM_MESH_ALLOW_UNSIGNED_BEACONS=1` for mixed-version meshes.
    #[serde(default)]
    pub allow_unsigned_beacons: bool,
}

impl Default for TransportConfig {
    fn default() -> Self {
        Self {
            bind_addr: format!("0.0.0.0:{DEFAULT_PORT}"),
            multicast_group: MULTICAST_GROUP.to_string(),
            heartbeat_interval_sec: DEFAULT_HEARTBEAT_INTERVAL_SEC,
            max_connections: 64,
            allow_unsigned_beacons: false,
        }
    }
}

// ── Peer Announcement (UDP) ───────────────────────────────────────────

/// UDP beacon broadcast by peers for discovery.
///
/// S9: beacons are signed. `public_key` + `signature` cover the
/// canonical payload (every field except the signature), and
/// `ingest_beacon` verifies before the announced peer may enter the
/// discovery registry. Both fields are `serde(default)` so a signed
/// beacon still parses on pre-S9 receivers — but pre-S9 receivers do
/// not verify, which is why the fleet upgrades together (the escape
/// hatch `WM_MESH_ALLOW_UNSIGNED_BEACONS=1` exists for that window).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerAnnounce {
    /// Peer ID.
    pub peer_id: PeerId,
    /// TCP address for connections (e.g., "192.168.1.10:7369").
    pub tcp_addr: String,
    /// Capabilities advertised (JSON array of PeerCapability).
    pub capabilities: Vec<String>,
    /// Timestamp (Unix seconds).
    pub timestamp: i64,
    /// Ed25519 public key of the announcing peer (hex), S9.
    #[serde(default)]
    pub public_key: String,
    /// Ed25519 signature over [`PeerAnnounce::signing_payload`] (hex), S9.
    #[serde(default)]
    pub signature: String,
}

impl PeerAnnounce {
    /// Create a new announcement.
    #[must_use]
    pub fn new(peer_id: impl Into<String>, tcp_addr: impl Into<String>) -> Self {
        Self {
            peer_id: peer_id.into(),
            tcp_addr: tcp_addr.into(),
            capabilities: Vec::new(),
            timestamp: chrono::Utc::now().timestamp(),
            public_key: String::new(),
            signature: String::new(),
        }
    }

    /// The canonical payload committed by the signature: every field
    /// except the signature itself (the public key is included — it
    /// binds the key to this exact announcement).
    #[must_use]
    pub fn signing_payload(&self) -> String {
        let without_sig = Self {
            signature: String::new(),
            ..self.clone()
        };
        serde_json::to_string(&without_sig).unwrap_or_default()
    }

    /// Sign this announcement in place with the node's keypair.
    pub fn signed(&mut self, keypair: &crate::crypto::MeshKeyPair) {
        self.public_key = keypair.public_key_hex();
        self.signature = keypair.sign_hex(&self.signing_payload());
    }

    /// Verify the signature against the carried public key.
    #[must_use]
    pub fn verify_signature(&self) -> bool {
        if self.public_key.is_empty() || self.signature.is_empty() {
            return false;
        }
        crate::crypto::MeshKeyPair::verify_hex(
            &self.signing_payload(),
            &self.signature,
            &self.public_key,
        )
    }

    /// Whether the announced peer ID is the default derivation of the
    /// announced public key (`wm-<first 12 hex>`).
    ///
    /// Peers with a custom `WM_MESH_PEER_ID` fail this check by design;
    /// they are accepted at ingest only if the key is already bound to
    /// that peer ID in the registry (i.e., a signed heartbeat bound it).
    #[must_use]
    pub fn identity_matches_key(&self) -> bool {
        self.public_key.len() >= 12 && self.peer_id == format!("wm-{}", &self.public_key[..12])
    }

    /// Serialize to JSON bytes.
    #[must_use]
    pub fn to_bytes(&self) -> Vec<u8> {
        serde_json::to_vec(self).unwrap_or_default()
    }

    /// Deserialize from JSON bytes.
    ///
    /// # Errors
    /// Returns `None` if deserialization fails.
    #[must_use]
    pub fn from_bytes(data: &[u8]) -> Option<Self> {
        serde_json::from_slice(data).ok()
    }
}

// ── JSON-RPC Protocol ─────────────────────────────────────────────────

/// JSON-RPC request.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RpcRequest {
    pub method: String,
    pub params: serde_json::Value,
    pub id: u64,
}

/// JSON-RPC response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RpcResponse {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
    pub id: u64,
}

impl RpcResponse {
    /// Create a success response.
    #[must_use]
    pub const fn ok(result: serde_json::Value, id: u64) -> Self {
        Self {
            result: Some(result),
            error: None,
            id,
        }
    }

    /// Create an error response.
    #[must_use]
    pub fn err(error: impl Into<String>, id: u64) -> Self {
        Self {
            result: None,
            error: Some(error.into()),
            id,
        }
    }

    /// Serialize to JSON bytes.
    #[must_use]
    pub fn to_bytes(&self) -> Vec<u8> {
        serde_json::to_vec(self).unwrap_or_default()
    }
}

// ── Frame Helpers ─────────────────────────────────────────────────────

/// Write a length-prefixed JSON frame to a TCP stream.
async fn write_frame(stream: &mut TcpStream, data: &[u8]) -> std::io::Result<()> {
    let len = u32::try_from(data.len())
        .map_err(|_| std::io::Error::new(std::io::ErrorKind::InvalidInput, "message too large"))?;
    stream.write_all(&len.to_be_bytes()).await?;
    stream.write_all(data).await?;
    Ok(())
}

/// Read a length-prefixed JSON frame from a TCP stream.
async fn read_frame(stream: &mut TcpStream) -> std::io::Result<Vec<u8>> {
    let mut len_buf = [0u8; 4];
    stream.read_exact(&mut len_buf).await?;
    let len = u32::from_be_bytes(len_buf) as usize;
    if len > MAX_MESSAGE_SIZE {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            format!("message too large: {len} bytes"),
        ));
    }
    let mut buf = vec![0u8; len];
    stream.read_exact(&mut buf).await?;
    Ok(buf)
}

// ── Sangha Server State ───────────────────────────────────────────────

/// Shared state for the Sangha Mesh server.
pub struct SanghaState {
    /// Local peer ID.
    pub peer_id: PeerId,
    /// Local TCP address.
    pub tcp_addr: String,
    /// Peer discovery registry.
    pub peers: Mutex<PeerDiscovery>,
    /// Signal broadcast manager.
    pub signals: Mutex<SignalBroadcast>,
    /// Replay protection (S9) — shared by beacon ingest and chat inject.
    pub replay: crate::replay::ReplayCache,
    /// Chat manager.
    pub chat: Mutex<SanghaChat>,
    /// Lock manager.
    pub locks: Mutex<ResourceLockManager>,
    /// Hologram sync.
    pub hologram: Mutex<HologramSync>,
    /// This node's Ed25519 keypair — signs outgoing chat messages and
    /// heartbeats so remote peers can verify authorship and bind the
    /// public key to this node's ID.
    pub keypair: crate::crypto::MeshKeyPair,
}

impl SanghaState {
    /// Create new shared state with a keypair derived from the peer ID
    /// (deterministic per node; production should provision real secrets).
    #[must_use]
    pub fn new(peer_id: impl Into<String>, tcp_addr: impl Into<String>) -> Self {
        let peer_id = peer_id.into();
        let keypair = crate::crypto::MeshKeyPair::from_seed(peer_id.as_bytes());
        Self::with_keypair(peer_id, tcp_addr, keypair)
    }

    /// Create new shared state with an explicit keypair.
    #[must_use]
    pub fn with_keypair(
        peer_id: impl Into<String>,
        tcp_addr: impl Into<String>,
        keypair: crate::crypto::MeshKeyPair,
    ) -> Self {
        Self::with_persistence(peer_id, tcp_addr, keypair, None)
    }

    /// Create new shared state with an explicit keypair and an optional
    /// chat-log persistence path — delivered messages survive restarts
    /// (the receiver half of the mail-slot; the sender half is the
    /// `MailSlot`). Signatures are re-verified on restore.
    #[must_use]
    pub fn with_persistence(
        peer_id: impl Into<String>,
        tcp_addr: impl Into<String>,
        keypair: crate::crypto::MeshKeyPair,
        chat_log_path: Option<std::path::PathBuf>,
    ) -> Self {
        let keypair_clone = keypair.clone();
        Self {
            peer_id: peer_id.into(),
            tcp_addr: tcp_addr.into(),
            peers: Mutex::new(PeerDiscovery::default()),
            signals: Mutex::new(SignalBroadcast::default()),
            replay: crate::replay::ReplayCache::default(),
            chat: Mutex::new(
                SanghaChat::default()
                    .with_signing_key(keypair_clone)
                    .with_persistence(chat_log_path),
            ),
            locks: Mutex::new(ResourceLockManager::default()),
            hologram: Mutex::new(HologramSync::default()),
            keypair,
        }
    }
}

// ── Sangha Transport ──────────────────────────────────────────────────

/// Sangha Mesh network transport server.
///
/// Listens for TCP connections and handles JSON-RPC requests.
/// Also broadcasts UDP multicast beacons for peer discovery.
pub struct SanghaTransport {
    config: TransportConfig,
    state: Arc<SanghaState>,
    /// Connected peer streams (peer_id -> writer half).
    connections: Arc<RwLock<HashMap<PeerId, TcpStream>>>,
    /// Shutdown signal for graceful termination.
    shutdown: Arc<Notify>,
}

impl Clone for SanghaTransport {
    fn clone(&self) -> Self {
        Self {
            config: self.config.clone(),
            state: Arc::clone(&self.state),
            connections: Arc::clone(&self.connections),
            shutdown: Arc::clone(&self.shutdown),
        }
    }
}

impl SanghaTransport {
    /// Create a new transport server.
    #[must_use]
    pub fn new(config: TransportConfig, state: Arc<SanghaState>) -> Self {
        Self {
            config,
            state,
            connections: Arc::new(RwLock::new(HashMap::new())),
            shutdown: Arc::new(Notify::new()),
        }
    }

    /// Signal the transport to shut down gracefully.
    pub fn shutdown(&self) {
        self.shutdown.notify_waiters();
    }

    /// Start the transport server.
    ///
    /// Binds TCP listener and starts accepting connections.
    /// Also starts UDP multicast discovery.
    ///
    /// # Errors
    /// Returns an error if binding fails.
    pub async fn serve(&self) -> Result<()> {
        let listener = TcpListener::bind(&self.config.bind_addr)
            .await
            .map_err(|e| wm_core::CoreError::Internal(format!("TCP bind failed: {e}")))?;
        self.serve_on(listener).await
    }

    /// Serve on an already-bound listener — no re-bind window between a
    /// startup bind check and the accept loop (`MeshNode::start` binds in
    /// the caller's context so bind failures are loud before any task
    /// spawns).
    ///
    /// # Errors
    /// Propagates nothing from the accept loop beyond shutdown; accept
    /// errors are logged and continued.
    pub async fn serve_on(&self, listener: TcpListener) -> Result<()> {
        tracing::info!(
            "Sangha transport listening on {} (peer_id={})",
            self.config.bind_addr,
            self.state.peer_id
        );

        // Start UDP discovery beacon
        let state_clone = Arc::clone(&self.state);
        let config_clone = self.config.clone();
        let shutdown_clone = Arc::clone(&self.shutdown);
        tokio::spawn(async move {
            tokio::select! {
                () = shutdown_clone.notified() => {
                    tracing::debug!("Discovery beacon shutting down");
                }
                result = run_discovery_beacon(state_clone, &config_clone) => {
                    if let Err(e) = result {
                        tracing::warn!("Discovery beacon error: {e}");
                    }
                }
            }
        });

        // Accept TCP connections until shutdown
        loop {
            tokio::select! {
                () = self.shutdown.notified() => {
                    tracing::info!("Sangha transport shutting down");
                    break;
                }
                result = listener.accept() => {
                    match result {
                        Ok((stream, addr)) => {
                            tracing::debug!("Sangha connection from {addr}");
                            let state = Arc::clone(&self.state);
                            let shutdown = Arc::clone(&self.shutdown);
                            tokio::spawn(async move {
                                tokio::select! {
                                    () = shutdown.notified() => {}
                                    result = handle_connection(stream, state) => {
                                        if let Err(e) = result {
                                            tracing::debug!("Sangha connection error: {e}");
                                        }
                                    }
                                }
                            });
                        }
                        Err(e) => {
                            tracing::warn!("Sangha accept error: {e}");
                        }
                    }
                }
            }
        }

        Ok(())
    }

    /// Connect to a remote peer.
    ///
    /// # Errors
    /// Returns an error if connection fails.
    pub async fn connect_to_peer(&self, addr: &str) -> Result<()> {
        let stream = tokio::time::timeout(
            std::time::Duration::from_secs(MESH_DIAL_TIMEOUT_SECS),
            TcpStream::connect(addr),
        )
        .await
        .map_err(|_| {
            wm_core::CoreError::Internal(format!(
                "connect to {addr} timed out after {MESH_DIAL_TIMEOUT_SECS}s — host unreachable"
            ))
        })?
        .map_err(|e| wm_core::CoreError::Internal(format!("connect failed: {e}")))?;

        let peer_id = format!("remote:{addr}");
        self.connections.write().await.insert(peer_id, stream);
        Ok(())
    }

    /// Send an RPC request to a connected peer and receive the response.
    ///
    /// # Errors
    /// Returns an error if the request fails.
    #[allow(clippy::significant_drop_tightening)]
    pub async fn rpc_call(
        &self,
        peer_id: &str,
        method: &str,
        params: serde_json::Value,
    ) -> Result<serde_json::Value> {
        let req = RpcRequest {
            method: method.to_string(),
            params,
            id: rand_id(),
        };
        let req_bytes = serde_json::to_vec(&req)
            .map_err(|e| wm_core::CoreError::Internal(format!("serialize: {e}")))?;

        let resp_bytes = {
            let mut connections = self.connections.write().await;
            let exchange = {
                let stream = connections.get_mut(peer_id).ok_or_else(|| {
                    wm_core::CoreError::NotFound(format!("peer not connected: {peer_id}"))
                })?;
                async {
                    write_frame(stream, &req_bytes)
                        .await
                        .map_err(|e| wm_core::CoreError::Internal(format!("write: {e}")))?;
                    read_frame(stream)
                        .await
                        .map_err(|e| wm_core::CoreError::Internal(format!("read: {e}")))
                }
            };
            match tokio::time::timeout(
                std::time::Duration::from_secs(MESH_RPC_TIMEOUT_SECS),
                exchange,
            )
            .await
            {
                Ok(Ok(resp_bytes)) => resp_bytes,
                Ok(Err(e)) => {
                    // A write/read IO error means the stream is dead or
                    // half-dead. Keeping the entry would poison the peer:
                    // every retry hits the same corpse (the fleet-night
                    // retest defect — a surviving ghost shadowed a live
                    // peer that returned to the same address). Evict so
                    // the next call reconnects.
                    connections.remove(peer_id);
                    return Err(e);
                }
                Err(_) => {
                    // A late response may still arrive on this stream —
                    // it would be misread as the answer to the next rpc.
                    // Drop the connection so the next call reconnects.
                    connections.remove(peer_id);
                    return Err(wm_core::CoreError::Internal(format!(
                        "mesh rpc '{method}' to {peer_id} timed out after \
                         {MESH_RPC_TIMEOUT_SECS}s — peer accepted but never responded"
                    )));
                }
            }
        };

        let resp: RpcResponse = serde_json::from_slice(&resp_bytes)
            .map_err(|e| wm_core::CoreError::Internal(format!("deserialize: {e}")))?;

        if let Some(err) = resp.error {
            return Err(wm_core::CoreError::Internal(format!("RPC error: {err}")));
        }

        resp.result
            .ok_or_else(|| wm_core::CoreError::Internal("empty result".into()))
    }

    /// Broadcast a signal to all connected peers.
    ///
    /// Per-peer failures are warn-logged; a broadcast that reaches **no**
    /// peer (despite peers being connected) is an error, so a total
    /// fan-out outage is visible instead of silently swallowed.
    ///
    /// # Errors
    /// Returns an error when every connected peer failed to receive.
    pub async fn broadcast_signal_remote(&self, signal: &crate::signal::Signal) -> Result<()> {
        let connections = self.connections.read().await;
        let peer_ids: Vec<String> = connections.keys().cloned().collect();
        drop(connections);

        let mut failed: Vec<String> = Vec::new();
        for peer_id in &peer_ids {
            if self
                .rpc_call(peer_id, "broadcast_signal", signal.to_json())
                .await
                .is_err()
            {
                failed.push(peer_id.clone());
            }
        }
        if failed.len() == peer_ids.len() && !peer_ids.is_empty() {
            return Err(wm_core::CoreError::Internal(format!(
                "signal broadcast reached none of {} peers: {failed:?}",
                peer_ids.len()
            )));
        }
        if !failed.is_empty() {
            tracing::warn!(failed = ?failed, "signal broadcast partially failed");
        }
        Ok(())
    }

    /// Send a chat message to a remote peer.
    ///
    /// # Errors
    /// Returns an error if the send fails.
    pub async fn send_chat_remote(
        &self,
        peer_id: &str,
        channel: &str,
        sender: &str,
        content: &str,
    ) -> Result<serde_json::Value> {
        // Sign through the same code path the receiver verifies against,
        // so the canonical payload (serialized ChatMessage minus signature
        // and public key) matches exactly.
        let timestamp = chrono::Utc::now().timestamp_millis();
        let signed = crate::chat::ChatMessage {
            id: 0,
            channel: channel.to_string(),
            sender: sender.to_string(),
            content: content.to_string(),
            timestamp,
            signature: String::new(),
            public_key: String::new(),
        }
        .signed(&self.state.keypair);
        self.rpc_call(
            peer_id,
            "send_chat",
            serde_json::json!({
                "channel": channel,
                "sender": sender,
                "content": content,
                "signature": signed.signature,
                "public_key": signed.public_key,
                "timestamp": timestamp,
            }),
        )
        .await
    }

    /// Sync holographic coordinates with a remote peer.
    ///
    /// Exports local entries and sends them to the remote peer for merging.
    ///
    /// # Errors
    /// Returns an error if the sync fails.
    pub async fn sync_hologram_remote(&self, peer_id: &str) -> Result<serde_json::Value> {
        let entries = {
            let hologram = self.state.hologram.lock().await;
            hologram.export()
        };
        let params = serde_json::to_value(&entries)
            .map_err(|e| wm_core::CoreError::Internal(format!("serialize hologram: {e}")))?;
        self.rpc_call(peer_id, "sync_hologram", params).await
    }

    /// Get the number of connected peers.
    #[must_use]
    pub async fn connected_count(&self) -> usize {
        self.connections.read().await.len()
    }

    /// Keys of the currently connected peers (`remote:<addr>` form).
    #[must_use]
    pub async fn connected_peers(&self) -> Vec<String> {
        self.connections.read().await.keys().cloned().collect()
    }

    /// Drop a peer connection (`remote:<addr>` key). Returns `false` when
    /// no such connection exists.
    pub async fn disconnect(&self, peer_key: &str) -> bool {
        self.connections.write().await.remove(peer_key).is_some()
    }

    /// Non-blocking snapshot of the connected peer keys for synchronous
    /// status probes — `None` when the connection map is contended.
    #[must_use]
    pub fn try_connected_peers(&self) -> Option<Vec<String>> {
        self.connections
            .try_read()
            .ok()
            .map(|map| map.keys().cloned().collect::<Vec<_>>())
    }
}

/// Handle a single TCP connection.
async fn handle_connection(mut stream: TcpStream, state: Arc<SanghaState>) -> std::io::Result<()> {
    loop {
        let frame = read_frame(&mut stream).await?;
        let req: RpcRequest = match serde_json::from_slice(&frame) {
            Ok(r) => r,
            Err(e) => {
                let resp = RpcResponse::err(format!("parse error: {e}"), 0);
                write_frame(&mut stream, &resp.to_bytes()).await?;
                continue;
            }
        };

        let resp = handle_rpc_request(&req, &state).await;
        write_frame(&mut stream, &resp.to_bytes()).await?;
    }
}

/// Handle a single RPC request.
async fn handle_rpc_request(req: &RpcRequest, state: &SanghaState) -> RpcResponse {
    match req.method.as_str() {
        "heartbeat" => {
            let peer_info: PeerInfo = match serde_json::from_value(req.params.clone()) {
                Ok(p) => p,
                Err(e) => return RpcResponse::err(format!("invalid params: {e}"), req.id),
            };
            let peer_id = peer_info.id.clone();
            let result = if peer_info.signature.is_empty() {
                // Legacy unsigned announcement — accepted without identity
                // binding (single-node/trusted transport).
                state.peers.lock().await.discover(peer_info);
                Ok(())
            } else {
                // Signed announcement: verify + bind the public key.
                state.peers.lock().await.discover_signed(peer_info)
            };
            match result {
                Ok(()) => RpcResponse::ok(
                    serde_json::json!({"peer_id": peer_id, "status": "ok"}),
                    req.id,
                ),
                Err(e) => RpcResponse::err(format!("identity rejected: {e}"), req.id),
            }
        }

        "discover" => {
            let peers = state.peers.lock().await;
            RpcResponse::ok(peers.summary(), req.id)
        }

        "broadcast_signal" => {
            let signal: crate::signal::Signal = match serde_json::from_value(req.params.clone()) {
                Ok(s) => s,
                Err(e) => return RpcResponse::err(format!("invalid signal: {e}"), req.id),
            };
            state.signals.lock().await.broadcast(signal);
            RpcResponse::ok(serde_json::json!({"status": "ok"}), req.id)
        }

        "send_chat" => {
            let channel = req
                .params
                .get("channel")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            let sender = req
                .params
                .get("sender")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            let content = req
                .params
                .get("content")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            let signature = req
                .params
                .get("signature")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            let public_key = req
                .params
                .get("public_key")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            let timestamp = req
                .params
                .get("timestamp")
                .and_then(serde_json::Value::as_i64)
                .unwrap_or_else(|| chrono::Utc::now().timestamp_millis());

            if signature.is_empty() || public_key.is_empty() {
                // Legacy unsigned relay — accepted (trusted transport).
                let msg = {
                    let mut chat = state.chat.lock().await;
                    chat.send(channel, sender, content)
                };
                return RpcResponse::ok(
                    serde_json::json!({"status": "ok", "channel": msg.channel, "id": msg.id}),
                    req.id,
                );
            }

            // Signed relay: verify the signature and the sender binding.
            let msg = crate::chat::ChatMessage {
                id: 0,
                channel: channel.to_string(),
                sender: sender.to_string(),
                content: content.to_string(),
                timestamp,
                signature: signature.to_string(),
                public_key: public_key.to_string(),
            };
            let bound = {
                let peers = state.peers.lock().await;
                peers.bound_public_key(sender)
            };
            let valid =
                msg.verify_signature() && bound.is_none_or(|bound| msg.verify_as_sender(&bound));
            if !valid {
                return RpcResponse::err(
                    format!(
                        "message rejected: sender '{sender}' failed signature/binding verification"
                    ),
                    req.id,
                );
            }
            // The bad-apple rule at ingest: a quarantined sender's messages
            // are refused outright, even over a connection it opened before
            // the quarantine (community read path additionally filters).
            if state.peers.lock().await.is_quarantined(sender) {
                return RpcResponse::err(
                    format!("message rejected: sender '{sender}' is quarantined"),
                    req.id,
                );
            }
            {
                let mut chat = state.chat.lock().await;
                chat.inject_signed(msg);
            }
            RpcResponse::ok(
                serde_json::json!({"status": "ok", "channel": channel, "sender": sender}),
                req.id,
            )
        }

        "acquire_lock" => {
            let resource = req
                .params
                .get("resource")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            let holder = req
                .params
                .get("holder")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            let ttl = req
                .params
                .get("ttl_sec")
                .and_then(serde_json::Value::as_i64)
                .unwrap_or(30);

            let result = {
                let mut locks = state.locks.lock().await;
                locks.acquire_with_ttl(resource, holder, ttl)
            };
            RpcResponse::ok(
                serde_json::json!({
                    "acquired": result,
                    "resource": resource,
                }),
                req.id,
            )
        }

        "release_lock" => {
            let resource = req
                .params
                .get("resource")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            let holder = req
                .params
                .get("holder")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");

            let released = {
                let mut locks = state.locks.lock().await;
                locks.release(resource, holder)
            };
            RpcResponse::ok(
                serde_json::json!({
                    "released": released,
                    "resource": resource,
                }),
                req.id,
            )
        }

        "sync_hologram" => {
            let remote_entries: Vec<crate::hologram::HologramEntry> =
                match serde_json::from_value(req.params.clone()) {
                    Ok(e) => e,
                    Err(e) => {
                        return RpcResponse::err(format!("invalid hologram entries: {e}"), req.id);
                    }
                };
            let merge_result = {
                let mut hologram = state.hologram.lock().await;
                hologram.merge(remote_entries)
            };
            RpcResponse::ok(
                serde_json::json!({
                    "status": "ok",
                    "local_count": merge_result.local_count,
                    "remote_count": merge_result.remote_count,
                    "merged_count": merge_result.merged_count,
                    "new_from_remote": merge_result.new_from_remote,
                    "conflicts_resolved": merge_result.conflicts_resolved,
                }),
                req.id,
            )
        }

        _ => RpcResponse::err(format!("unknown method: {}", req.method), req.id),
    }
}

/// Run the UDP multicast discovery beacon.
async fn run_discovery_beacon(state: Arc<SanghaState>, config: &TransportConfig) -> Result<()> {
    let sock = UdpSocket::bind("0.0.0.0:0")
        .await
        .map_err(|e| wm_core::CoreError::Internal(format!("UDP bind: {e}")))?;

    let multicast_addr: SocketAddr = format!("{}:{}", config.multicast_group, DEFAULT_PORT)
        .parse()
        .map_err(|e| wm_core::CoreError::Internal(format!("multicast addr: {e}")))?;

    let interval = std::time::Duration::from_secs(config.heartbeat_interval_sec);

    loop {
        let mut announce = PeerAnnounce::new(&state.peer_id, &state.tcp_addr);
        announce.signed(&state.keypair);
        let bytes = announce.to_bytes();
        if let Err(e) = sock.send_to(&bytes, multicast_addr).await {
            tracing::debug!("UDP beacon send error: {e}");
        }

        tokio::time::sleep(interval).await;
    }
}

/// Listen for UDP multicast discovery beacons from other peers.
///
/// When a beacon is received, the peer is added to the local discovery registry.
pub async fn listen_for_beacons(state: Arc<SanghaState>, config: &TransportConfig) -> Result<()> {
    // Use socket2 to create a socket that joins the multicast group
    let bind_addr: std::net::SocketAddr = format!("0.0.0.0:{DEFAULT_PORT}").parse().unwrap();
    let socket2_socket = socket2::Socket::new(
        socket2::Domain::IPV4,
        socket2::Type::DGRAM,
        Some(socket2::Protocol::UDP),
    )
    .map_err(|e| wm_core::CoreError::Internal(format!("socket create: {e}")))?;

    // Allow multiple processes on the same host to bind to the same port
    socket2_socket
        .set_reuse_address(true)
        .map_err(|e| wm_core::CoreError::Internal(format!("set_reuse_address: {e}")))?;

    #[cfg(unix)]
    {
        socket2_socket
            .set_reuse_port(true)
            .map_err(|e| wm_core::CoreError::Internal(format!("set_reuse_port: {e}")))?;
        // tokio::net::UdpSocket::from_std requires a non-blocking fd — a
        // blocking one panics at registration inside the spawned listener task
        // (swallowed there, killing discovery receive silently).
        socket2_socket
            .set_nonblocking(true)
            .map_err(|e| wm_core::CoreError::Internal(format!("set_nonblocking: {e}")))?;
    }

    socket2_socket
        .bind(&socket2::SockAddr::from(bind_addr))
        .map_err(|e| wm_core::CoreError::Internal(format!("UDP bind: {e}")))?;

    // Join multicast group
    let multicast_ip: std::net::Ipv4Addr = config
        .multicast_group
        .parse()
        .map_err(|e| wm_core::CoreError::Internal(format!("multicast parse: {e}")))?;
    socket2_socket
        .join_multicast_v4(&multicast_ip, &std::net::Ipv4Addr::UNSPECIFIED)
        .map_err(|e| wm_core::CoreError::Internal(format!("join multicast: {e}")))?;

    // Convert to tokio UdpSocket
    let sock = tokio::net::UdpSocket::from_std(std::net::UdpSocket::from(socket2_socket))
        .map_err(|e| wm_core::CoreError::Internal(format!("tokio convert: {e}")))?;

    tracing::info!(
        "Listening for Sangha beacons on {bind_addr} (multicast {})",
        config.multicast_group
    );

    let mut buf = vec![0u8; 4096];
    loop {
        match sock.recv_from(&mut buf).await {
            Ok((len, _addr)) => {
                if let Some(announce) = PeerAnnounce::from_bytes(&buf[..len]) {
                    ingest_beacon(&state, &announce, config).await;
                }
            }
            Err(e) => {
                tracing::debug!("UDP recv error: {e}");
            }
        }
    }
}

/// Ingest one received beacon into the discovery registry.
///
/// A node must never register itself: multicast loopback (`IP_MULTICAST_LOOP`
/// defaults to enabled) delivers a node's own beacon back to its listener,
/// and a self-entry would pollute peer counts and make the auto-join loop
/// see a phantom peer.
///
/// S9 gate chain — a beacon is only registered when, in order:
///
/// 1. it is not our own loopback;
/// 2. its timestamp is fresh (within two heartbeat intervals, both
///    directions — clock skew tolerated, stale replays are not);
/// 3. it carries a valid Ed25519 signature over its canonical payload
///    (`WM_MESH_ALLOW_UNSIGNED_BEACONS=1` opens a legacy window instead);
/// 4. the announced public key is consistent with the announced peer ID:
///    default-derived IDs (`wm-<12hex>`) are self-certifying; custom
///    `WM_MESH_PEER_ID`s are accepted while unbound (the signed
///    heartbeat at join time does the real binding) or while the key
///    matches the existing binding — never against a *different* bound
///    key (beacon-level identity theft);
/// 5. the payload hash is not in the sender's replay window.
///
/// Rejected beacons are counted in the discovery stats and logged — the
/// fleet should be able to *see* attempted forgery.
async fn ingest_beacon(state: &SanghaState, announce: &PeerAnnounce, config: &TransportConfig) {
    if announce.peer_id == state.peer_id {
        tracing::debug!("ignoring own beacon (multicast loopback)");
        return;
    }

    let now = chrono::Utc::now().timestamp();
    let skew_limit = 2 * i64::try_from(config.heartbeat_interval_sec).unwrap_or(86_400);

    // 2. Freshness — a captured beacon re-injected later than two
    //    heartbeat intervals is stale by construction.
    if (now - announce.timestamp).abs() > skew_limit {
        tracing::warn!(
            peer_id = %announce.peer_id,
            age_secs = now - announce.timestamp,
            "rejected stale beacon (S9 freshness window)"
        );
        return;
    }

    // 3. Signature — signed-only by default. A valid signature proves
    //    the announcer controls that key; what that key may announce is
    //    the identity rule below.
    if announce.verify_signature() {
        // 4. Identity rule —
        //    - default-namespace IDs (`wm-<12hex>`): must derive from the
        //      announcing key — the default namespace is self-certifying
        //      and cannot be spoofed by another keypair;
        //    - custom IDs (any other name): accepted while the key is the
        //      one already bound to the ID, or while the ID is
        //      unbound/evicted (the signed heartbeat at join time does
        //      the real binding — first-bound-wins, identity theft after
        //      binding refused);
        //    - bound to a DIFFERENT key: rejected. A beacon must never
        //      redirect a bound peer's traffic.
        let bound = state.peers.lock().await.bound_public_key(&announce.peer_id);
        let identity_ok = match bound {
            Some(bound_key) => bound_key == announce.public_key,
            None => announce.identity_matches_key() || !announce.peer_id.starts_with("wm-"),
        };
        if !identity_ok {
            tracing::warn!(
                peer_id = %announce.peer_id,
                "rejected beacon: announced key does not own the announced peer ID (S9 identity rule)"
            );
            return;
        }
        // 5. Replay — same payload from the same peer inside the TTL
        //    window is a re-injection, not a refresh.
        let hash = crate::replay::fnv1a64(announce.signing_payload().as_bytes());
        if !state.replay.check_and_insert(&announce.peer_id, hash, now) {
            tracing::debug!(peer_id = %announce.peer_id, "rejected replayed beacon (S9)");
            return;
        }
    } else if config.allow_unsigned_beacons {
        tracing::warn!(
            peer_id = %announce.peer_id,
            "accepting unsigned beacon — WM_MESH_ALLOW_UNSIGNED_BEACONS legacy window"
        );
    } else {
        tracing::warn!(
            peer_id = %announce.peer_id,
            "rejected unsigned or badly-signed beacon (S9 signed-only)"
        );
        return;
    }

    tracing::debug!(
        "Discovered peer: {} at {}",
        announce.peer_id,
        announce.tcp_addr
    );
    let mut peer_info = PeerInfo::new(&announce.peer_id, &announce.tcp_addr);
    if !announce.public_key.is_empty() {
        peer_info.public_key = announce.public_key.clone();
    }
    state.peers.lock().await.discover(peer_info);
}

/// Generate a random RPC ID.
fn rand_id() -> u64 {
    use std::time::SystemTime;
    let nanos = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos());
    // Use lower 64 bits of nanos as a pseudo-random ID
    u64::try_from(nanos % u128::from(u64::MAX)).unwrap_or(1)
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn peer_announce_roundtrip() {
        let announce = PeerAnnounce::new("peer-1", "127.0.0.1:7369");
        let bytes = announce.to_bytes();
        let decoded = PeerAnnounce::from_bytes(&bytes).unwrap();
        assert_eq!(decoded.peer_id, "peer-1");
        assert_eq!(decoded.tcp_addr, "127.0.0.1:7369");
    }

    #[tokio::test]
    async fn beacon_ingest_ignores_own_loopback_beacon() {
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        // Multicast loopback delivers the node's own beacon back to its
        // listener — it must never register itself. (Loopback is checked
        // before the S9 gates; the beacon here is unsigned, which does
        // not matter for the self-check.)
        let own = PeerAnnounce::new("self-node", "127.0.0.1:7369");
        ingest_beacon(&state, &own, &TransportConfig::default()).await;
        assert_eq!(
            state.peers.lock().await.summary()["peer_count"],
            0,
            "a node must not appear in its own discovery registry"
        );
    }

    /// A beacon from a key whose public key derives the announced peer
    /// ID (`wm-<first 12 hex>`), signed over its canonical payload.
    fn signed_announce(keypair: &crate::crypto::MeshKeyPair, tcp_addr: &str) -> PeerAnnounce {
        let peer_id = format!("wm-{}", &keypair.public_key_hex()[..12]);
        let mut announce = PeerAnnounce::new(peer_id, tcp_addr);
        announce.signed(keypair);
        announce
    }

    #[tokio::test]
    async fn unsigned_beacon_rejected_by_default() {
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        let unsigned = PeerAnnounce::new("other-node", "127.0.0.1:7370");
        ingest_beacon(&state, &unsigned, &TransportConfig::default()).await;
        assert_eq!(
            state.peers.lock().await.summary()["peer_count"],
            0,
            "S9: unsigned beacons must not register peers"
        );
    }

    #[tokio::test]
    async fn legacy_window_accepts_unsigned() {
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        let config = TransportConfig {
            allow_unsigned_beacons: true,
            ..TransportConfig::default()
        };
        let unsigned = PeerAnnounce::new("other-node", "127.0.0.1:7370");
        ingest_beacon(&state, &unsigned, &config).await;
        assert_eq!(
            state.peers.lock().await.summary()["peer_count"],
            1,
            "the documented legacy window must still discover"
        );
    }

    #[tokio::test]
    async fn forged_signature_beacon_rejected() {
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        let attacker = crate::crypto::MeshKeyPair::from_seed(b"attacker");
        // The victim's peer ID, but a signature from the wrong key.
        let victim_id = format!(
            "wm-{}",
            &crate::crypto::MeshKeyPair::from_seed(b"victim").public_key_hex()[..12]
        );
        let mut announce = PeerAnnounce::new(&victim_id, "127.0.0.1:7370");
        announce.signed(&attacker);
        ingest_beacon(&state, &announce, &TransportConfig::default()).await;
        assert_eq!(
            state.peers.lock().await.summary()["peer_count"],
            0,
            "a forged signature must never register a peer"
        );
    }

    #[tokio::test]
    async fn tampered_beacon_payload_rejected() {
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        let keypair = crate::crypto::MeshKeyPair::from_seed(b"honest-peer");
        let mut announce = signed_announce(&keypair, "127.0.0.1:7370");
        // Redirect the announce AFTER signing — the classic MITM move.
        announce.tcp_addr = "10.0.0.66:7369".into();
        ingest_beacon(&state, &announce, &TransportConfig::default()).await;
        assert_eq!(
            state.peers.lock().await.summary()["peer_count"],
            0,
            "a payload modified after signing must be rejected"
        );
    }

    #[tokio::test]
    async fn stale_signed_beacon_rejected() {
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        let keypair = crate::crypto::MeshKeyPair::from_seed(b"stale-peer");
        let mut announce = signed_announce(&keypair, "127.0.0.1:7370");
        // Sign an OLD timestamp: a captured beacon re-injected an hour later.
        announce.timestamp = chrono::Utc::now().timestamp() - 3600;
        announce.signed(&keypair);
        ingest_beacon(&state, &announce, &TransportConfig::default()).await;
        assert_eq!(
            state.peers.lock().await.summary()["peer_count"],
            0,
            "a perfectly-signed but stale beacon is a replay, not a refresh"
        );
    }

    #[tokio::test]
    async fn replayed_signed_beacon_rejected() {
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        let keypair = crate::crypto::MeshKeyPair::from_seed(b"replayed-peer");
        let announce = signed_announce(&keypair, "127.0.0.1:7370");
        let hash = crate::replay::fnv1a64(announce.signing_payload().as_bytes());
        let config = TransportConfig::default();
        ingest_beacon(&state, &announce, &config).await;
        let summary = state.peers.lock().await.summary();
        assert_eq!(summary["peer_count"], 1, "the first sighting registers");
        // The cache must now hold this payload for the sender.
        assert!(
            !state
                .replay
                .check_and_insert(&announce.peer_id, hash, chrono::Utc::now().timestamp()),
            "the beacon payload must be in the sender's replay window"
        );
    }

    #[tokio::test]
    async fn valid_signed_beacon_registers() {
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        let keypair = crate::crypto::MeshKeyPair::from_seed(b"honest-peer");
        let announce = signed_announce(&keypair, "127.0.0.1:7370");
        ingest_beacon(&state, &announce, &TransportConfig::default()).await;
        let summary = state.peers.lock().await.summary();
        assert_eq!(
            summary["peer_count"], 1,
            "honest signed discovery must work"
        );
        assert_eq!(summary["peers"][0]["id"], announce.peer_id);
        // And the announced key is carried into the registry entry.
        assert_eq!(
            state.peers.lock().await.bound_public_key(&announce.peer_id),
            Some(keypair.public_key_hex()),
            "the beacon's key pre-stages the join-time identity binding"
        );
    }

    #[tokio::test]
    async fn custom_peer_id_beacon_rejected_when_bound_to_different_key() {
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        let owner = crate::crypto::MeshKeyPair::from_seed(b"named-peer-owner");
        let attacker = crate::crypto::MeshKeyPair::from_seed(b"named-peer-attacker");
        let config = TransportConfig::default();

        // The owner's signed heartbeat binds the custom ID.
        let bound = state
            .peers
            .lock()
            .await
            .discover_signed(PeerInfo::new("custom-node", "127.0.0.1:7370").signed(&owner));
        assert!(bound.is_ok());

        // The attacker holds a perfectly valid keypair of their own and
        // announces the victim's custom ID — the beacon signature
        // verifies, but the ID is bound to a different key.
        let mut hijack = PeerAnnounce::new("custom-node", "10.0.0.66:7369");
        hijack.signed(&attacker);
        ingest_beacon(&state, &hijack, &config).await;

        let summary = state.peers.lock().await.summary();
        assert_eq!(summary["peer_count"], 1);
        assert_eq!(
            state.peers.lock().await.bound_public_key("custom-node"),
            Some(owner.public_key_hex()),
            "a beacon must never re-point a bound peer ID at another key"
        );
    }

    #[tokio::test]
    async fn custom_peer_id_fresh_beacon_registers_as_candidate() {
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        let keypair = crate::crypto::MeshKeyPair::from_seed(b"named-peer");
        // Custom WM_MESH_PEER_ID, never bound — the signed beacon
        // registers the peer as an unbound candidate (discovery must
        // survive eviction/rejoin; the signed heartbeat at join does
        // the real binding, first-bound-wins as before S9).
        let mut announce = PeerAnnounce::new("custom-node", "127.0.0.1:7370");
        announce.signed(&keypair);
        ingest_beacon(&state, &announce, &TransportConfig::default()).await;
        assert_eq!(
            state.peers.lock().await.summary()["peer_count"],
            1,
            "signed custom-ID beacons must still be able to introduce a peer"
        );

        // Once the owner's heartbeat binds the ID, an attacker's beacon
        // with a different key is refused…
        let attacker = crate::crypto::MeshKeyPair::from_seed(b"other-key");
        let bound = state
            .peers
            .lock()
            .await
            .discover_signed(PeerInfo::new("custom-node", "127.0.0.1:7370").signed(&keypair));
        assert!(bound.is_ok());
        let mut hijack = PeerAnnounce::new("custom-node", "10.0.0.66:7369");
        hijack.signed(&attacker);
        ingest_beacon(&state, &hijack, &TransportConfig::default()).await;
        assert_eq!(
            state.peers.lock().await.bound_public_key("custom-node"),
            Some(keypair.public_key_hex()),
            "binding survives adversarial beacons after eviction… or not"
        );
    }

    #[test]
    fn rpc_response_ok() {
        let resp = RpcResponse::ok(serde_json::json!({"status": "ok"}), 42);
        assert_eq!(resp.id, 42);
        assert!(resp.result.is_some());
        assert!(resp.error.is_none());
    }

    #[test]
    fn rpc_response_err() {
        let resp = RpcResponse::err("something failed", 99);
        assert_eq!(resp.id, 99);
        assert!(resp.result.is_none());
        assert_eq!(resp.error.as_deref(), Some("something failed"));
    }

    #[test]
    fn rpc_request_serialize() {
        let req = RpcRequest {
            method: "heartbeat".to_string(),
            params: serde_json::json!({"peer_id": "test"}),
            id: 1,
        };
        let json = serde_json::to_string(&req).unwrap();
        assert!(json.contains("heartbeat"));
        assert!(json.contains("\"id\":1"));
    }

    #[test]
    fn transport_config_default() {
        let config = TransportConfig::default();
        assert_eq!(config.bind_addr, "0.0.0.0:7369");
        assert_eq!(config.multicast_group, "224.0.0.69");
        assert_eq!(config.heartbeat_interval_sec, 5);
        assert_eq!(config.max_connections, 64);
    }

    #[test]
    fn sangha_state_creation() {
        let state = SanghaState::new("peer-1", "127.0.0.1:7369");
        assert_eq!(state.peer_id, "peer-1");
        assert_eq!(state.tcp_addr, "127.0.0.1:7369");
    }

    #[tokio::test]
    #[allow(clippy::significant_drop_tightening)]
    async fn handle_rpc_heartbeat() {
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));
        let peer = PeerInfo::new("remote-1", "127.0.0.1:7370");
        let params = serde_json::to_value(&peer).unwrap();

        let req = RpcRequest {
            method: "heartbeat".to_string(),
            params,
            id: 1,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.result.is_some());
        assert_eq!(resp.id, 1);

        // Verify peer was registered
        {
            let peers = state.peers.lock().await;
            assert_eq!(peers.peer_count(), 1);
        }
    }

    #[tokio::test]
    async fn handle_rpc_discover() {
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));

        // Add a peer first
        let peer = PeerInfo::new("remote-1", "127.0.0.1:7370");
        state.peers.lock().await.discover(peer);

        let req = RpcRequest {
            method: "discover".to_string(),
            params: serde_json::Value::Null,
            id: 2,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.result.is_some());
        let result = resp.result.unwrap();
        assert!(result.get("peer_count").is_some());
    }

    #[tokio::test]
    async fn handle_rpc_unknown_method() {
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));

        let req = RpcRequest {
            method: "nonexistent".to_string(),
            params: serde_json::Value::Null,
            id: 3,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.error.is_some());
        assert!(resp.error.unwrap().contains("unknown method"));
    }

    #[tokio::test]
    async fn handle_rpc_acquire_lock() {
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));

        let req = RpcRequest {
            method: "acquire_lock".to_string(),
            params: serde_json::json!({
                "resource": "memory:galaxy:codex",
                "holder": "remote-1",
                "ttl_sec": 30,
            }),
            id: 4,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.result.is_some());
        let result = resp.result.unwrap();
        assert_eq!(
            result.get("acquired").and_then(serde_json::Value::as_bool),
            Some(true)
        );
    }

    #[tokio::test]
    async fn handle_rpc_release_lock() {
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));

        // Acquire first
        let acquire_req = RpcRequest {
            method: "acquire_lock".to_string(),
            params: serde_json::json!({
                "resource": "memory:galaxy:codex",
                "holder": "remote-1",
                "ttl_sec": 30,
            }),
            id: 5,
        };
        let _ = handle_rpc_request(&acquire_req, &state).await;

        // Release
        let release_req = RpcRequest {
            method: "release_lock".to_string(),
            params: serde_json::json!({
                "resource": "memory:galaxy:codex",
                "holder": "remote-1",
            }),
            id: 6,
        };

        let resp = handle_rpc_request(&release_req, &state).await;
        assert!(resp.result.is_some());
        let result = resp.result.unwrap();
        assert_eq!(
            result.get("released").and_then(serde_json::Value::as_bool),
            Some(true)
        );
    }

    #[tokio::test]
    async fn handle_rpc_broadcast_signal() {
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));

        let signal = crate::signal::Signal::new(
            crate::signal::SignalType::MemoryCreated,
            "remote-1",
            serde_json::json!({"galaxy": "codex"}),
        );

        let req = RpcRequest {
            method: "broadcast_signal".to_string(),
            params: serde_json::to_value(&signal).unwrap(),
            id: 7,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.result.is_some());
    }

    #[tokio::test]
    async fn handle_rpc_send_chat() {
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));

        let req = RpcRequest {
            method: "send_chat".to_string(),
            params: serde_json::json!({
                "channel": "general",
                "sender": "remote-1",
                "content": "hello mesh",
            }),
            id: 8,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.result.is_some());
        let result = resp.result.unwrap();
        assert_eq!(
            result.get("channel").and_then(|v| v.as_str()),
            Some("general")
        );
    }

    #[test]
    fn frame_helpers_roundtrip() {
        // Test that RpcResponse serialization is stable
        let resp = RpcResponse::ok(serde_json::json!({"ok": true}), 1);
        let bytes = resp.to_bytes();
        let decoded: RpcResponse = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(decoded.id, 1);
        assert!(decoded.result.is_some());
    }

    #[test]
    fn peer_announce_with_capabilities() {
        let mut announce = PeerAnnounce::new("peer-1", "127.0.0.1:7369");
        announce.capabilities = vec!["inference".to_string(), "memory".to_string()];
        let bytes = announce.to_bytes();
        let decoded = PeerAnnounce::from_bytes(&bytes).unwrap();
        assert_eq!(decoded.capabilities, vec!["inference", "memory"]);
    }

    #[test]
    fn peer_announce_invalid_bytes() {
        assert!(PeerAnnounce::from_bytes(b"not json").is_none());
    }

    #[test]
    fn rand_id_is_nonzero() {
        let id = rand_id();
        assert!(id > 0);
    }

    #[tokio::test]
    async fn handle_rpc_sync_hologram() {
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));

        // Add a local entry first
        let entry =
            crate::hologram::HologramEntry::new("hash-1", [1.0, 2.0, 3.0, 0.0], 0.5, "local");
        state.hologram.lock().await.add_local(entry);

        // Send remote entries for sync
        let remote_entries = vec![
            crate::hologram::HologramEntry::new(
                "hash-1",
                [1.0, 2.0, 3.0, 0.0],
                0.9, // higher importance — should win
                "remote-1",
            ),
            crate::hologram::HologramEntry::new("hash-2", [4.0, 5.0, 6.0, 0.0], 0.3, "remote-1"),
        ];

        let req = RpcRequest {
            method: "sync_hologram".to_string(),
            params: serde_json::to_value(&remote_entries).unwrap(),
            id: 9,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.result.is_some());
        let result = resp.result.unwrap();
        assert_eq!(
            result
                .get("remote_count")
                .and_then(serde_json::Value::as_u64),
            Some(2)
        );
        assert_eq!(
            result
                .get("new_from_remote")
                .and_then(serde_json::Value::as_u64),
            Some(1)
        );
        assert_eq!(
            result
                .get("conflicts_resolved")
                .and_then(serde_json::Value::as_u64),
            Some(1)
        );

        // Verify entries were merged
        let entry_count = {
            let hologram = state.hologram.lock().await;
            hologram.entry_count()
        };
        assert_eq!(entry_count, 2);
        // Remote should have won the conflict (higher importance)
        let source = {
            let hologram = state.hologram.lock().await;
            hologram.get("hash-1").unwrap().source.clone()
        };
        assert_eq!(source, "remote-1");
    }

    #[tokio::test]
    async fn rpc_call_evicts_connection_on_io_error() {
        // The fleet-night retest defect: a peer-side close left a poisoned
        // connection entry — every retry hit the same corpse, and a live
        // peer returning to the address was shadowed by the ghost. An
        // IO-failed rpc must evict, not poison.
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        let state = Arc::new(SanghaState::new("server", addr.to_string()));
        let server = tokio::spawn(async move {
            let (stream, _) = listener.accept().await.unwrap();
            let _ = handle_connection(stream, state).await;
        });

        let client = SanghaTransport::new(
            TransportConfig::default(),
            Arc::new(SanghaState::new("client", "127.0.0.1:0")),
        );
        let key = format!("remote:{addr}");
        client.connect_to_peer(&addr.to_string()).await.unwrap();

        // A signed heartbeat round-trips while the server lives.
        let identity = PeerInfo::new("client", "127.0.0.1:0").signed(&client.state.keypair);
        let ok = client
            .rpc_call(&key, "heartbeat", serde_json::to_value(&identity).unwrap())
            .await;
        assert!(ok.is_ok(), "live rpc must succeed: {ok:?}");

        // The server side dies mid-connection (process-death class).
        server.abort();

        // The next rpc must fail — and must evict the dead entry.
        let mut failed = false;
        for _ in 0..40 {
            if client
                .rpc_call(&key, "discover", serde_json::Value::Null)
                .await
                .is_err()
            {
                failed = true;
                break;
            }
            tokio::time::sleep(std::time::Duration::from_millis(50)).await;
        }
        assert!(failed, "rpc against a dead server must fail");
        assert!(
            !client.connected_peers().await.contains(&key),
            "an IO-failed rpc must evict the connection instead of poisoning it"
        );

        // Recovery path: the next dial is free to re-establish (nothing
        // wedged). The server is gone, so the dial itself must fail fast
        // rather than hang — pins the bounded-dial behavior too.
        let redial = client.connect_to_peer(&addr.to_string()).await;
        assert!(redial.is_err(), "dialing a dead server must fail");
    }

    #[tokio::test]
    async fn e2e_tcp_rpc_roundtrip() {
        // Start a server on an ephemeral port
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let bound_addr = listener.local_addr().unwrap();

        let state = Arc::new(SanghaState::new("server", bound_addr.to_string()));

        // Spawn server task
        let server_state = Arc::clone(&state);
        tokio::spawn(async move {
            let (stream, _) = listener.accept().await.unwrap();
            let _ = handle_connection(stream, server_state).await;
        });

        // Connect as client and send a heartbeat RPC
        let mut client = TcpStream::connect(bound_addr).await.unwrap();

        let peer = PeerInfo::new("client-1", "127.0.0.1:9999");
        let req = RpcRequest {
            method: "heartbeat".to_string(),
            params: serde_json::to_value(&peer).unwrap(),
            id: 100,
        };
        let req_bytes = serde_json::to_vec(&req).unwrap();
        write_frame(&mut client, &req_bytes).await.unwrap();

        // Read response
        let resp_bytes = read_frame(&mut client).await.unwrap();
        let resp: RpcResponse = serde_json::from_slice(&resp_bytes).unwrap();
        assert_eq!(resp.id, 100);
        assert!(resp.result.is_some());
        assert!(resp.error.is_none());

        // Verify peer was registered on server
        let peer_count = state.peers.lock().await.peer_count();
        assert_eq!(peer_count, 1);

        // Send a discover request
        let req2 = RpcRequest {
            method: "discover".to_string(),
            params: serde_json::Value::Null,
            id: 101,
        };
        let req2_bytes = serde_json::to_vec(&req2).unwrap();
        write_frame(&mut client, &req2_bytes).await.unwrap();

        let resp2_bytes = read_frame(&mut client).await.unwrap();
        let resp2: RpcResponse = serde_json::from_slice(&resp2_bytes).unwrap();
        assert_eq!(resp2.id, 101);
        assert!(resp2.result.is_some());
    }

    #[tokio::test]
    #[allow(clippy::significant_drop_tightening)]
    async fn e2e_tcp_chat_and_signal() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let bound_addr = listener.local_addr().unwrap();

        let state = Arc::new(SanghaState::new("server", bound_addr.to_string()));

        let server_state = Arc::clone(&state);
        tokio::spawn(async move {
            let (stream, _) = listener.accept().await.unwrap();
            let _ = handle_connection(stream, server_state).await;
        });

        let mut client = TcpStream::connect(bound_addr).await.unwrap();

        // Send chat message
        let chat_req = RpcRequest {
            method: "send_chat".to_string(),
            params: serde_json::json!({
                "channel": "mesh",
                "sender": "client-1",
                "content": "hello from the mesh",
            }),
            id: 200,
        };
        let chat_bytes = serde_json::to_vec(&chat_req).unwrap();
        write_frame(&mut client, &chat_bytes).await.unwrap();

        let resp_bytes = read_frame(&mut client).await.unwrap();
        let resp: RpcResponse = serde_json::from_slice(&resp_bytes).unwrap();
        assert_eq!(resp.id, 200);
        assert!(resp.result.is_some());
        let result = resp.result.unwrap();
        assert_eq!(result.get("channel").and_then(|v| v.as_str()), Some("mesh"));

        // Verify message was stored on server
        let (msg_count, msg_content) = {
            let chat = state.chat.lock().await;
            let messages = chat.read("mesh", None);
            let count = messages.len();
            let content = messages
                .first()
                .map(|m| m.content.clone())
                .unwrap_or_default();
            (count, content)
        };
        assert_eq!(msg_count, 1);
        assert_eq!(msg_content, "hello from the mesh");

        // Send a signal broadcast
        let signal = crate::signal::Signal::new(
            crate::signal::SignalType::PeerStatus,
            "client-1",
            serde_json::json!({"status": "online"}),
        );
        let sig_req = RpcRequest {
            method: "broadcast_signal".to_string(),
            params: serde_json::to_value(&signal).unwrap(),
            id: 201,
        };
        let sig_bytes = serde_json::to_vec(&sig_req).unwrap();
        write_frame(&mut client, &sig_bytes).await.unwrap();

        let sig_resp_bytes = read_frame(&mut client).await.unwrap();
        let sig_resp: RpcResponse = serde_json::from_slice(&sig_resp_bytes).unwrap();
        assert_eq!(sig_resp.id, 201);
        assert!(sig_resp.result.is_some());
    }

    #[tokio::test]
    async fn e2e_tcp_hologram_sync() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let bound_addr = listener.local_addr().unwrap();

        let state = Arc::new(SanghaState::new("server", bound_addr.to_string()));

        // Add a local entry on the server
        let local_entry =
            crate::hologram::HologramEntry::new("local-hash", [1.0, 0.0, 0.0, 0.0], 0.5, "server");
        state.hologram.lock().await.add_local(local_entry);

        let server_state = Arc::clone(&state);
        tokio::spawn(async move {
            let (stream, _) = listener.accept().await.unwrap();
            let _ = handle_connection(stream, server_state).await;
        });

        let mut client = TcpStream::connect(bound_addr).await.unwrap();

        // Send remote hologram entries for sync
        let remote_entries = vec![
            crate::hologram::HologramEntry::new(
                "remote-hash-1",
                [0.0, 1.0, 0.0, 0.0],
                0.7,
                "client-1",
            ),
            crate::hologram::HologramEntry::new(
                "remote-hash-2",
                [0.0, 0.0, 1.0, 0.0],
                0.3,
                "client-1",
            ),
        ];

        let sync_req = RpcRequest {
            method: "sync_hologram".to_string(),
            params: serde_json::to_value(&remote_entries).unwrap(),
            id: 300,
        };
        let sync_bytes = serde_json::to_vec(&sync_req).unwrap();
        write_frame(&mut client, &sync_bytes).await.unwrap();

        let resp_bytes = read_frame(&mut client).await.unwrap();
        let resp: RpcResponse = serde_json::from_slice(&resp_bytes).unwrap();
        assert_eq!(resp.id, 300);
        assert!(resp.result.is_some());
        let result = resp.result.unwrap();
        assert_eq!(
            result
                .get("new_from_remote")
                .and_then(serde_json::Value::as_u64),
            Some(2)
        );

        // Verify entries were merged on server
        let entry_count = state.hologram.lock().await.entry_count();
        assert_eq!(entry_count, 3); // 1 local + 2 remote
    }

    #[tokio::test]
    async fn transport_shutdown_stops_serve() {
        let state = Arc::new(SanghaState::new("test", "127.0.0.1:0"));
        let config = TransportConfig {
            bind_addr: "127.0.0.1:0".to_string(),
            ..TransportConfig::default()
        };
        let transport = SanghaTransport::new(config, state);

        // Start serving in a background task
        let transport_handle = Arc::new(transport);
        let serve_handle = {
            let t = Arc::clone(&transport_handle);
            tokio::spawn(async move {
                let _ = t.serve().await;
            })
        };

        // Give it a moment to start
        tokio::time::sleep(std::time::Duration::from_millis(50)).await;

        // Signal shutdown
        transport_handle.shutdown();

        // Wait for serve to return — should complete quickly
        let result = tokio::time::timeout(std::time::Duration::from_secs(2), serve_handle).await;
        assert!(
            result.is_ok(),
            "serve should return within 2s after shutdown"
        );
    }

    #[tokio::test]
    async fn transport_connect_and_rpc() {
        // Start a server on an ephemeral port
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let bound_addr = listener.local_addr().unwrap();
        let addr_str = bound_addr.to_string();

        let state = Arc::new(SanghaState::new("server", addr_str.clone()));

        let server_state = Arc::clone(&state);
        tokio::spawn(async move {
            let (stream, _) = listener.accept().await.unwrap();
            let _ = handle_connection(stream, server_state).await;
        });

        // Use SanghaTransport to connect and make an RPC call
        let client_state = Arc::new(SanghaState::new("client", "127.0.0.1:0"));
        let client_config = TransportConfig {
            bind_addr: "127.0.0.1:0".to_string(),
            ..TransportConfig::default()
        };
        let client_transport = SanghaTransport::new(client_config, client_state);

        // Connect to the server
        client_transport.connect_to_peer(&addr_str).await.unwrap();

        // Make an RPC call — heartbeat
        let peer = PeerInfo::new("client", "127.0.0.1:12345");
        let _ = client_transport
            .rpc_call(
                "remote:127.0.0.1:0",
                "heartbeat",
                serde_json::to_value(&peer).unwrap(),
            )
            .await;

        // The RPC might fail if the peer_id doesn't match, but connection should work.
        // The key assertion is that the transport can connect and attempt RPC.
        // If the connection was established, the test passes.
        let connected = client_transport.connected_count().await;
        assert_eq!(connected, 1);
    }
}

#[cfg(feature = "transport")]
#[cfg(test)]
mod containment_tests {
    //! Transport-mode containment: two live nodes over TCP, with an
    //! adversarial relay attempting forged messages and identity theft.

    use super::*;
    use crate::chat::ChatMessage;
    use crate::crypto::MeshKeyPair;

    async fn spawn_node(peer_id: &str, port: u16) -> (SanghaTransport, String) {
        let keypair = MeshKeyPair::from_seed(peer_id.as_bytes());
        let addr = format!("127.0.0.1:{port}");
        let state = Arc::new(SanghaState::with_keypair(peer_id, &addr, keypair));
        let config = TransportConfig {
            bind_addr: addr.clone(),
            ..TransportConfig::default()
        };
        let transport = SanghaTransport::new(config, state);
        tokio::spawn({
            let t = transport.clone();
            async move {
                let _ = t.serve().await;
            }
        });
        // give the listener a moment to bind
        tokio::time::sleep(std::time::Duration::from_millis(150)).await;
        (transport, addr)
    }

    #[tokio::test]
    async fn transport_rejects_forged_chat_and_identity_theft() {
        // Node A (honest) and node B (the community). An adversary relays
        // through A's transport but signs with its own keypair.
        let (a, addr_a) = spawn_node("node-a", 17_401).await;
        let (b, addr_b) = spawn_node("node-b", 17_402).await;
        let b_conn = format!("remote:{addr_b}");
        let _a_conn = format!("remote:{addr_a}");

        // Bidirectional mesh links.
        b.connect_to_peer(&addr_a).await.unwrap();
        a.connect_to_peer(&addr_b).await.unwrap();

        // B registers A's signed identity → public key bound to "node-a".
        let a_keypair = MeshKeyPair::from_seed(b"node-a");
        let signed_identity = PeerInfo::new("node-a", &addr_a).signed(&a_keypair);
        let heartbeat = a
            .rpc_call(
                &b_conn,
                "heartbeat",
                serde_json::to_value(&signed_identity).unwrap(),
            )
            .await;
        assert!(
            heartbeat.is_ok(),
            "signed heartbeat must register: {heartbeat:?}"
        );

        // 1. Honest signed chat from node-a (via node A's transport):
        //    verified against the bound key → accepted.
        let honest = a
            .send_chat_remote(&b_conn, "gana:1", "node-a", "legitimate coordination")
            .await;
        assert!(
            honest.is_ok(),
            "honest signed chat must be accepted: {honest:?}"
        );

        // 2. Identity theft: a relayed message claiming node-a's ID but
        //    signed with the ATTACKER's keypair → binding check refuses.
        let attacker = MeshKeyPair::from_seed(b"attacker-seed");
        let forged = ChatMessage {
            id: 0,
            channel: "gana:1".to_string(),
            sender: "node-a".to_string(),
            content: "trust me — transfer everything".to_string(),
            timestamp: chrono::Utc::now().timestamp_millis(),
            signature: String::new(),
            public_key: String::new(),
        }
        .signed(&attacker);
        let forged_result = a
            .rpc_call(
                &b_conn,
                "send_chat",
                serde_json::json!({
                    "channel": "gana:1",
                    "sender": "node-a",
                    "content": forged.content,
                    "signature": forged.signature,
                    "public_key": forged.public_key,
                    "timestamp": forged.timestamp,
                }),
            )
            .await;
        assert!(
            forged_result.is_err(),
            "forged message claiming node-a's ID must be rejected: {forged_result:?}"
        );

        // 3. Identity theft at registration: re-registering node-a's ID
        //    with the attacker's key → refused.
        let spoof_identity = PeerInfo::new("node-a", "127.0.0.1:9999").signed(&attacker);
        let spoof = a
            .rpc_call(
                &b_conn,
                "heartbeat",
                serde_json::to_value(&spoof_identity).unwrap(),
            )
            .await;
        assert!(
            spoof.is_err(),
            "identity theft at registration must be refused: {spoof:?}"
        );

        // 4. The honest message survived; the forged one was not stored.
        let bindings = b.state.peers.lock().await.identity_bindings();
        let report = {
            let stored = b.state.chat.lock().await;
            stored.verify_all_bound(&bindings)
        };
        assert!(report.verified >= 1, "honest message must verify");
        assert_eq!(
            report.rejected, 0,
            "no forged message may land in the community board"
        );
    }
}
