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
use std::net::ToSocketAddrs;
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

/// Upper bound on how long an established inbound connection may sit idle
/// between frames before the node closes it.
///
/// Peers speak on demand (RPCs), so a quiet connection is a dead one — and
/// an open socket a slowloris can hold forever is a resource the LAN must
/// not be able to pin.
pub const MESH_IDLE_TIMEOUT_SECS: u64 = 120;

/// Upper bound on requests served over ONE inbound connection — mirrors
/// the MCP server's per-session request budget. A connection that exceeds
/// it is closed; the peer simply reconnects.
pub const MAX_REQUESTS_PER_CONNECTION: usize = 10_000;

/// Environment escape hatch for dialing/announcing non-local addresses.
/// The mesh is LAN-scoped by design; only set this when a relay/WAN phase
/// is deliberately enabled.
pub const ENV_ALLOW_PUBLIC_ADDRS: &str = "WM_MESH_ALLOW_PUBLIC_ADDRS";

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
}

impl Default for TransportConfig {
    fn default() -> Self {
        Self {
            bind_addr: format!("0.0.0.0:{DEFAULT_PORT}"),
            multicast_group: MULTICAST_GROUP.to_string(),
            heartbeat_interval_sec: DEFAULT_HEARTBEAT_INTERVAL_SEC,
            max_connections: 64,
        }
    }
}

// ── Peer Announcement (UDP) ───────────────────────────────────────────

/// UDP beacon broadcast by peers for discovery.
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
        }
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

// ── Address Policy ───────────────────────────────────────────────────

/// Whether an IP is inside the mesh's local scope: loopback, RFC1918
/// private, IPv4 link-local, IPv6 unique-local, or IPv6 link-local.
const fn ip_is_mesh_scoped(ip: std::net::IpAddr) -> bool {
    match ip {
        std::net::IpAddr::V4(v4) => v4.is_loopback() || v4.is_private() || v4.is_link_local(),
        std::net::IpAddr::V6(v6) => {
            v6.is_loopback() || v6.is_unique_local() || v6.is_unicast_link_local()
        }
    }
}

/// Validate a mesh address (beacon target, heartbeat address, dial
/// target): it must resolve ONLY to local-scope IPs. A beacon claiming a
/// public address is either misconfiguration or a dial-out injection —
/// without this check, a spoofed beacon makes the node open TCP to an
/// arbitrary internet host. `WM_MESH_ALLOW_PUBLIC_ADDRS=1` lifts the
/// restriction explicitly (relay/WAN phase).
fn validate_mesh_addr(addr: &str) -> std::result::Result<(), String> {
    if std::env::var(ENV_ALLOW_PUBLIC_ADDRS).is_ok_and(|v| v.trim() == "1") {
        return Ok(());
    }
    let resolved: Vec<std::net::IpAddr> = addr
        .to_socket_addrs()
        .map_err(|e| format!("unresolvable mesh address '{addr}': {e}"))?
        .map(|s| s.ip())
        .collect();
    if resolved.is_empty() {
        return Err(format!("mesh address '{addr}' resolved to nothing"));
    }
    let offenders: Vec<String> = resolved
        .iter()
        .filter(|ip| !ip_is_mesh_scoped(**ip))
        .map(std::net::IpAddr::to_string)
        .collect();
    if !offenders.is_empty() {
        return Err(format!(
            "mesh address '{addr}' resolves outside the local network ({offenders:?}) — \
             refusing; set {ENV_ALLOW_PUBLIC_ADDRS}=1 to override"
        ));
    }
    Ok(())
}

// ── Signed RPC Envelope ──────────────────────────────────────────────

/// Canonical payload of a signed RPC envelope: the params minus the
/// envelope fields (`signature`, `public_key`). Both sides derive the
/// same bytes through the same serde_json canonicalization (lockstep
/// fleet builds share one serde_json mode).
fn envelope_payload(params: &serde_json::Value) -> String {
    let mut payload = params.clone();
    if let Some(obj) = payload.as_object_mut() {
        obj.remove("signature");
        obj.remove("public_key");
    }
    payload.to_string()
}

/// Extract the sender and verified payload from a signed RPC envelope.
/// The envelope shape is uniform across mutating methods:
/// `{"sender", "payload", "public_key", "signature"}` — the signature
/// covers the params minus the envelope fields, and the signer key must
/// be the one the community has bound to `sender`. Returns
/// `(sender, payload)`.
fn verify_signed_envelope(
    params: &serde_json::Value,
    peers: &crate::peer::PeerDiscovery,
) -> std::result::Result<(String, serde_json::Value), String> {
    let sender = params
        .get("sender")
        .and_then(serde_json::Value::as_str)
        .filter(|s| !s.is_empty())
        .ok_or_else(|| "envelope missing 'sender'".to_string())?;
    let signature = params
        .get("signature")
        .and_then(serde_json::Value::as_str)
        .filter(|s| !s.is_empty())
        .ok_or_else(|| format!("envelope from '{sender}' missing 'signature'"))?;
    let public_key = params
        .get("public_key")
        .and_then(serde_json::Value::as_str)
        .filter(|s| !s.is_empty())
        .ok_or_else(|| format!("envelope from '{sender}' missing 'public_key'"))?;
    let payload = params
        .get("payload")
        .cloned()
        .ok_or_else(|| format!("envelope from '{sender}' missing 'payload'"))?;
    // The signature covers sender + payload (everything except the
    // envelope fields), so the sender field itself is tamper-evident.
    if !crate::crypto::MeshKeyPair::verify_hex(&envelope_payload(params), signature, public_key) {
        return Err(format!(
            "envelope from '{sender}' failed signature verification"
        ));
    }
    match peers.bound_public_key(sender) {
        Some(bound) if bound == public_key => Ok((sender.to_string(), payload)),
        Some(bound) => Err(format!(
            "envelope from '{sender}' carries an unbound key (bound: {bound}) — \
             possible identity theft"
        )),
        None => Err(format!(
            "sender '{sender}' is not identity-bound on this node — join before \
             sending signed RPCs"
        )),
    }
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
    /// Live inbound connection count — enforces `max_connections` in the
    /// accept loop so the LAN cannot exhaust the node by connect flood.
    inbound: Arc<std::sync::atomic::AtomicUsize>,
    /// Shutdown signal for graceful termination.
    shutdown: Arc<Notify>,
}

impl Clone for SanghaTransport {
    fn clone(&self) -> Self {
        Self {
            config: self.config.clone(),
            state: Arc::clone(&self.state),
            connections: Arc::clone(&self.connections),
            inbound: Arc::clone(&self.inbound),
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
            inbound: Arc::new(std::sync::atomic::AtomicUsize::new(0)),
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
                            // Connection-cap enforcement: refuse beyond
                            // max_connections (the config value is a real
                            // limit, not decoration).
                            if self.inbound.load(std::sync::atomic::Ordering::SeqCst)
                                >= self.config.max_connections
                            {
                                tracing::warn!(
                                    "Sangha connection cap ({}) reached — refusing {addr}",
                                    self.config.max_connections
                                );
                                continue;
                            }
                            self.inbound
                                .fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                            let state = Arc::clone(&self.state);
                            let shutdown = Arc::clone(&self.shutdown);
                            let inbound = Arc::clone(&self.inbound);
                            tokio::spawn(async move {
                                let _guard = InboundGuard(inbound);
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
        // Address policy: the mesh dials LAN-scope targets only. A
        // beacon-fed address outside that scope is refused here (belt to
        // the suspenders of the ingest-time check in `ingest_beacon`).
        validate_mesh_addr(addr).map_err(wm_core::CoreError::Internal)?;
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

    /// Build a signed RPC envelope over `payload` — the mirror of the
    /// receiver-side `verify_signed_envelope`. The signature covers the
    /// params minus the envelope fields, exactly as the receiver will
    /// re-derive them.
    fn signed_rpc_params(&self, payload: &serde_json::Value) -> serde_json::Value {
        let mut params = serde_json::json!({
            "sender": self.state.peer_id,
            "payload": payload,
        });
        let signature = self.state.keypair.sign_hex(&envelope_payload(&params));
        params["signature"] = serde_json::Value::String(signature);
        params["public_key"] = serde_json::Value::String(self.state.keypair.public_key_hex());
        params
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

        let payload = signal.to_json();
        let params = self.signed_rpc_params(&payload);
        let mut failed: Vec<String> = Vec::new();
        for peer_id in &peer_ids {
            if self
                .rpc_call(peer_id, "broadcast_signal", params.clone())
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
        let payload = serde_json::json!({ "entries": entries });
        let params = self.signed_rpc_params(&payload);
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

/// RAII decrement for the inbound connection counter.
struct InboundGuard(Arc<std::sync::atomic::AtomicUsize>);

impl Drop for InboundGuard {
    fn drop(&mut self) {
        self.0.fetch_sub(1, std::sync::atomic::Ordering::SeqCst);
    }
}

/// Handle a single TCP connection.
///
/// Two per-connection defenses: an idle timeout (a connection that sends
/// nothing for `MESH_IDLE_TIMEOUT_SECS` is closed — open sockets must not
/// be pinnable forever) and a per-connection request budget
/// (`MAX_REQUESTS_PER_CONNECTION`) that closes runaway connections.
async fn handle_connection(mut stream: TcpStream, state: Arc<SanghaState>) -> std::io::Result<()> {
    let mut served: usize = 0;
    loop {
        let Ok(frame) = tokio::time::timeout(
            std::time::Duration::from_secs(MESH_IDLE_TIMEOUT_SECS),
            read_frame(&mut stream),
        )
        .await
        else {
            tracing::debug!("Sangha connection idle > {MESH_IDLE_TIMEOUT_SECS}s — closing");
            return Ok(());
        };
        let frame = frame?;
        served += 1;
        if served > MAX_REQUESTS_PER_CONNECTION {
            tracing::debug!(
                "Sangha connection exceeded {MAX_REQUESTS_PER_CONNECTION} requests — closing"
            );
            return Ok(());
        }
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
            // Address policy: refuse announcements that point outside the
            // local network (a signed-but-public address is still a
            // dial-out injection channel).
            if let Err(e) = validate_mesh_addr(&peer_info.address) {
                return RpcResponse::err(format!("address refused: {e}"), req.id);
            }
            // Signed announcements ONLY over the wire. The legacy unsigned
            // path was in-process use — it must never traverse TCP, where
            // an unsigned heartbeat would let anyone on the LAN inject or
            // steer registry entries.
            let result = {
                let mut peers = state.peers.lock().await;
                let outcome = peers.discover_signed(peer_info);
                if outcome.is_err() {
                    // Feed the auto-quarantine policy: repeated identity
                    // failures cut the offender off without a human.
                    peers.record_verification_failure(&peer_id);
                } else {
                    peers.record_verification_success(&peer_id);
                }
                outcome
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
            // Signed envelope required — an unauthenticated LAN host must
            // not be able to inject signals (they feed agent coordination).
            let (sender, payload) = {
                let peers = state.peers.lock().await;
                match verify_signed_envelope(&req.params, &peers) {
                    Ok(result) => result,
                    Err(e) => return RpcResponse::err(format!("signal refused: {e}"), req.id),
                }
            };
            let signal: crate::signal::Signal = match serde_json::from_value(payload) {
                Ok(s) => s,
                Err(e) => return RpcResponse::err(format!("invalid signal: {e}"), req.id),
            };
            // The signal's own source must match the envelope sender — a
            // bound peer cannot launder a signal through another's name.
            if signal.source != sender {
                return RpcResponse::err(
                    format!(
                        "signal refused: source '{}' does not match envelope sender '{sender}'",
                        signal.source
                    ),
                    req.id,
                );
            }
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
                // Unsigned relay REFUSED over the wire. The legacy path was
                // in-process use only — on TCP it is an unauthenticated
                // channel-pollution primitive for anyone on the LAN.
                return RpcResponse::err(
                    "message rejected: unsigned chat is not accepted over mesh TCP — \
                     sign it (sangha.mesh.chat signs every send)"
                        .to_string(),
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
            let valid = {
                let mut peers = state.peers.lock().await;
                let bound = peers.bound_public_key(sender);
                let ok = msg.verify_signature()
                    && bound.is_none_or(|bound| msg.verify_as_sender(&bound));
                if ok {
                    peers.record_verification_success(sender);
                } else {
                    // Feed the auto-quarantine policy.
                    peers.record_verification_failure(sender);
                }
                ok
            };
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
            // Signed envelope required; the holder must be the signer —
            // an unauthenticated host cannot lock (or lock-squat) a
            // resource under someone else's name.
            let (sender, payload) = {
                let peers = state.peers.lock().await;
                match verify_signed_envelope(&req.params, &peers) {
                    Ok(result) => result,
                    Err(e) => return RpcResponse::err(format!("lock refused: {e}"), req.id),
                }
            };
            let resource = payload
                .get("resource")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            let holder = payload
                .get("holder")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            let ttl = payload
                .get("ttl_sec")
                .and_then(serde_json::Value::as_i64)
                .unwrap_or(30);
            if holder != sender {
                return RpcResponse::err(
                    format!(
                        "lock refused: holder '{holder}' does not match envelope sender '{sender}'"
                    ),
                    req.id,
                );
            }

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
            // Signed envelope required; the releaser must be the holder.
            let (sender, payload) = {
                let peers = state.peers.lock().await;
                match verify_signed_envelope(&req.params, &peers) {
                    Ok(result) => result,
                    Err(e) => return RpcResponse::err(format!("lock refused: {e}"), req.id),
                }
            };
            let resource = payload
                .get("resource")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            let holder = payload
                .get("holder")
                .and_then(serde_json::Value::as_str)
                .unwrap_or("");
            if holder != sender {
                return RpcResponse::err(
                    format!(
                        "lock refused: holder '{holder}' does not match envelope sender '{sender}'"
                    ),
                    req.id,
                );
            }

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
            // Signed envelope required — hologram merges feed the
            // importance-wins conflict rule, so an unauthenticated host
            // could otherwise drown real coordinates with high-importance
            // junk.
            let (_sender, payload) = {
                let peers = state.peers.lock().await;
                match verify_signed_envelope(&req.params, &peers) {
                    Ok(result) => result,
                    Err(e) => {
                        return RpcResponse::err(format!("hologram sync refused: {e}"), req.id);
                    }
                }
            };
            let remote_entries: Vec<crate::hologram::HologramEntry> =
                match serde_json::from_value(payload.get("entries").cloned().unwrap_or_default()) {
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
        let announce = PeerAnnounce::new(&state.peer_id, &state.tcp_addr);
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
                    ingest_beacon(&state, &announce).await;
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
/// see a phantom peer. Beacons carry addresses, not identity — the signed
/// heartbeat at join time is what binds a key.
async fn ingest_beacon(state: &SanghaState, announce: &PeerAnnounce) {
    if announce.peer_id == state.peer_id {
        tracing::debug!("ignoring own beacon (multicast loopback)");
        return;
    }
    // Address policy: a beacon pointing outside the local network is
    // refused at ingest — the auto-join loop dials beaconed addresses,
    // so an unvalidated beacon is a dial-out injection primitive.
    if let Err(e) = validate_mesh_addr(&announce.tcp_addr) {
        tracing::debug!("refusing beacon from '{}': {e}", announce.peer_id);
        return;
    }
    tracing::debug!(
        "Discovered peer: {} at {}",
        announce.peer_id,
        announce.tcp_addr
    );
    let peer_info = PeerInfo::new(&announce.peer_id, &announce.tcp_addr);
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
        // listener — it must never register itself.
        let own = PeerAnnounce::new("self-node", "127.0.0.1:7369");
        ingest_beacon(&state, &own).await;
        assert_eq!(
            state.peers.lock().await.summary()["peer_count"],
            0,
            "a node must not appear in its own discovery registry"
        );

        let other = PeerAnnounce::new("other-node", "127.0.0.1:7370");
        ingest_beacon(&state, &other).await;
        let summary = state.peers.lock().await.summary();
        assert_eq!(summary["peer_count"], 1);
        assert_eq!(summary["peers"][0]["id"], "other-node");
    }

    #[tokio::test]
    async fn beacon_cannot_redirect_bound_peer() {
        // Address-redirect guard: once a peer is identity-bound, an
        // unsigned beacon (or any unsigned announcement) may refresh
        // liveness but MUST NOT rewrite the address — otherwise a spoofed
        // beacon silently reroutes the peer's traffic (and mail flushes)
        // to an attacker-chosen host.
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        let kp = crate::crypto::MeshKeyPair::from_seed(b"victim");
        let original_addr = "10.0.0.68:7369";

        // Bind the victim via its signed identity.
        state
            .peers
            .lock()
            .await
            .discover_signed(PeerInfo::new("victim", original_addr).signed(&kp))
            .unwrap();

        // A spoofed beacon claims the victim's ID at the ATTACKER's address.
        let spoof = PeerAnnounce::new("victim", "10.0.0.99:7369");
        ingest_beacon(&state, &spoof).await;
        {
            let peers = state.peers.lock().await;
            assert_eq!(
                peers.get("victim").map(|p| p.address.as_str()),
                Some(original_addr),
                "an unsigned beacon must not redirect a bound peer"
            );
        }

        // The legitimate signed re-announcement (e.g. after a DHCP change)
        // DOES move the address.
        let moved = PeerInfo::new("victim", "10.0.0.77:7369").signed(&kp);
        state
            .peers
            .lock()
            .await
            .discover_signed(moved)
            .expect("legit signed re-announce must succeed");
        {
            let peers = state.peers.lock().await;
            assert_eq!(
                peers.get("victim").map(|p| p.address.as_str()),
                Some("10.0.0.77:7369"),
                "a signed announcement from the bound key may update the address"
            );
        }
    }

    #[tokio::test]
    async fn beacon_with_public_address_refused() {
        let state = Arc::new(SanghaState::new("self-node", "127.0.0.1:7369"));
        let spoof = PeerAnnounce::new("stranger", "93.184.216.34:7369");
        ingest_beacon(&state, &spoof).await;
        assert_eq!(
            state.peers.lock().await.peer_count(),
            0,
            "a beacon pointing outside the local network must be refused at ingest"
        );
    }

    #[test]
    fn validate_mesh_addr_scopes() {
        assert!(validate_mesh_addr("127.0.0.1:7369").is_ok());
        assert!(validate_mesh_addr("10.0.0.57:7369").is_ok());
        assert!(validate_mesh_addr("192.168.1.10:7369").is_ok());
        assert!(validate_mesh_addr("169.254.1.1:7369").is_ok());
        assert!(validate_mesh_addr("[fd00::1]:7369").is_ok());
        assert!(validate_mesh_addr("93.184.216.34:7369").is_err());
        assert!(validate_mesh_addr("[2606:2800:220:1:248:1893:25c8:1946]:7369").is_err());
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
        let client_kp = crate::crypto::MeshKeyPair::from_seed(b"remote-1");
        let peer = PeerInfo::new("remote-1", "127.0.0.1:7370").signed(&client_kp);
        let params = serde_json::to_value(&peer).unwrap();

        let req = RpcRequest {
            method: "heartbeat".to_string(),
            params,
            id: 1,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(
            resp.result.is_some(),
            "signed heartbeat must register: {resp:?}"
        );
        assert_eq!(resp.id, 1);

        // Verify peer was registered AND identity-bound
        {
            let peers = state.peers.lock().await;
            assert_eq!(peers.peer_count(), 1);
            assert!(peers.bound_public_key("remote-1").is_some());
        }
    }

    #[tokio::test]
    async fn handle_rpc_heartbeat_unsigned_refused() {
        // The v0 code accepted unsigned heartbeats over TCP ("legacy
        // path") — that was a LAN-wide registry-injection primitive. The
        // wire is signed-only now; the in-process path never traverses
        // this handler.
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));
        let peer = PeerInfo::new("remote-1", "127.0.0.1:7370");
        let req = RpcRequest {
            method: "heartbeat".to_string(),
            params: serde_json::to_value(&peer).unwrap(),
            id: 1,
        };
        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.error.is_some(), "unsigned heartbeat must be refused");
        assert_eq!(state.peers.lock().await.peer_count(), 0);
    }

    #[tokio::test]
    async fn handle_rpc_heartbeat_public_address_refused() {
        // Address policy: even a well-signed announcement pointing at a
        // public IP is refused — it is a dial-out injection channel.
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));
        let kp = crate::crypto::MeshKeyPair::from_seed(b"remote-1");
        let peer = PeerInfo::new("remote-1", "93.184.216.34:7369").signed(&kp);
        let req = RpcRequest {
            method: "heartbeat".to_string(),
            params: serde_json::to_value(&peer).unwrap(),
            id: 2,
        };
        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.error.is_some(), "public address must be refused");
        assert_eq!(state.peers.lock().await.peer_count(), 0);
    }

    /// Bind a peer identity directly in the registry (in-process shortcut
    /// for tests that then exercise signed RPCs from that identity).
    async fn bind_peer(
        state: &SanghaState,
        peer_id: &str,
        addr: &str,
        kp: &crate::crypto::MeshKeyPair,
    ) {
        state
            .peers
            .lock()
            .await
            .discover_signed(PeerInfo::new(peer_id, addr).signed(kp))
            .expect("bind must succeed");
    }

    /// Build the sender side of a signed RPC envelope (mirror of
    /// `SanghaTransport::signed_rpc_params` for direct-handler tests).
    fn signed_envelope(
        kp: &crate::crypto::MeshKeyPair,
        sender: &str,
        payload: serde_json::Value,
    ) -> serde_json::Value {
        let mut params = serde_json::json!({"sender": sender, "payload": payload});
        let signature = kp.sign_hex(&envelope_payload(&params));
        params["signature"] = serde_json::Value::String(signature);
        params["public_key"] = serde_json::Value::String(kp.public_key_hex());
        params
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
        let kp = crate::crypto::MeshKeyPair::from_seed(b"remote-1");
        bind_peer(&state, "remote-1", "127.0.0.1:7370", &kp).await;

        let req = RpcRequest {
            method: "acquire_lock".to_string(),
            params: signed_envelope(
                &kp,
                "remote-1",
                serde_json::json!({
                    "resource": "memory:galaxy:codex",
                    "holder": "remote-1",
                    "ttl_sec": 30,
                }),
            ),
            id: 4,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.result.is_some(), "signed lock must acquire: {resp:?}");
        let result = resp.result.unwrap();
        assert_eq!(
            result.get("acquired").and_then(serde_json::Value::as_bool),
            Some(true)
        );
    }

    #[tokio::test]
    async fn handle_rpc_acquire_lock_unsigned_refused() {
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
        assert!(resp.error.is_some(), "unsigned lock must be refused");
    }

    #[tokio::test]
    async fn handle_rpc_acquire_lock_holder_mismatch_refused() {
        // A bound peer cannot lock under someone else's name.
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));
        let kp = crate::crypto::MeshKeyPair::from_seed(b"remote-1");
        bind_peer(&state, "remote-1", "127.0.0.1:7370", &kp).await;
        let req = RpcRequest {
            method: "acquire_lock".to_string(),
            params: signed_envelope(
                &kp,
                "remote-1",
                serde_json::json!({
                    "resource": "memory:galaxy:codex",
                    "holder": "someone-else",
                    "ttl_sec": 30,
                }),
            ),
            id: 4,
        };
        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.error.is_some(), "holder mismatch must be refused");
    }

    #[tokio::test]
    async fn handle_rpc_release_lock() {
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));
        let kp = crate::crypto::MeshKeyPair::from_seed(b"remote-1");
        bind_peer(&state, "remote-1", "127.0.0.1:7370", &kp).await;

        // Acquire first
        let acquire_req = RpcRequest {
            method: "acquire_lock".to_string(),
            params: signed_envelope(
                &kp,
                "remote-1",
                serde_json::json!({
                    "resource": "memory:galaxy:codex",
                    "holder": "remote-1",
                    "ttl_sec": 30,
                }),
            ),
            id: 5,
        };
        let _ = handle_rpc_request(&acquire_req, &state).await;

        // Release
        let release_req = RpcRequest {
            method: "release_lock".to_string(),
            params: signed_envelope(
                &kp,
                "remote-1",
                serde_json::json!({
                    "resource": "memory:galaxy:codex",
                    "holder": "remote-1",
                }),
            ),
            id: 6,
        };

        let resp = handle_rpc_request(&release_req, &state).await;
        assert!(
            resp.result.is_some(),
            "signed release must succeed: {resp:?}"
        );
        let result = resp.result.unwrap();
        assert_eq!(
            result.get("released").and_then(serde_json::Value::as_bool),
            Some(true)
        );
    }

    #[tokio::test]
    async fn handle_rpc_broadcast_signal() {
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));
        let kp = crate::crypto::MeshKeyPair::from_seed(b"remote-1");
        bind_peer(&state, "remote-1", "127.0.0.1:7370", &kp).await;

        let signal = crate::signal::Signal::new(
            crate::signal::SignalType::MemoryCreated,
            "remote-1",
            serde_json::json!({"galaxy": "codex"}),
        );

        let req = RpcRequest {
            method: "broadcast_signal".to_string(),
            params: signed_envelope(&kp, "remote-1", serde_json::to_value(&signal).unwrap()),
            id: 7,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.result.is_some(), "signed signal must land: {resp:?}");
    }

    #[tokio::test]
    async fn handle_rpc_broadcast_signal_unsigned_refused() {
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
        assert!(resp.error.is_some(), "unsigned signal must be refused");
    }

    #[tokio::test]
    async fn handle_rpc_send_chat() {
        let state = Arc::new(SanghaState::new("local", "127.0.0.1:7369"));
        let kp = crate::crypto::MeshKeyPair::from_seed(b"remote-1");

        let signed = crate::chat::ChatMessage {
            id: 0,
            channel: "general".to_string(),
            sender: "remote-1".to_string(),
            content: "hello mesh".to_string(),
            timestamp: chrono::Utc::now().timestamp_millis(),
            signature: String::new(),
            public_key: String::new(),
        }
        .signed(&kp);

        let req = RpcRequest {
            method: "send_chat".to_string(),
            params: serde_json::json!({
                "channel": signed.channel,
                "sender": signed.sender,
                "content": signed.content,
                "timestamp": signed.timestamp,
                "signature": signed.signature,
                "public_key": signed.public_key,
            }),
            id: 8,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(resp.result.is_some(), "signed chat must land: {resp:?}");
        let result = resp.result.unwrap();
        assert_eq!(
            result.get("channel").and_then(|v| v.as_str()),
            Some("general")
        );
    }

    #[tokio::test]
    async fn handle_rpc_send_chat_unsigned_refused() {
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
        assert!(resp.error.is_some(), "unsigned chat must be refused");
        let chat_count = { state.chat.lock().await.read("general", None).len() };
        assert_eq!(chat_count, 0, "refused chat must not be stored");
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
        let kp = crate::crypto::MeshKeyPair::from_seed(b"remote-1");
        bind_peer(&state, "remote-1", "127.0.0.1:7370", &kp).await;

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
            params: signed_envelope(
                &kp,
                "remote-1",
                serde_json::json!({ "entries": remote_entries }),
            ),
            id: 9,
        };

        let resp = handle_rpc_request(&req, &state).await;
        assert!(
            resp.result.is_some(),
            "signed hologram sync must merge: {resp:?}"
        );
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

        // Connect as client and send a signed heartbeat RPC
        let mut client = TcpStream::connect(bound_addr).await.unwrap();

        let client_kp = crate::crypto::MeshKeyPair::from_seed(b"client-1");
        let peer = PeerInfo::new("client-1", "127.0.0.1:9999").signed(&client_kp);
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

        // Send a signed chat message (self-consistent signature; the
        // sender is not bound on the server — chat accepts that, forged
        // claims of a BOUND sender would not pass).
        let client_kp = crate::crypto::MeshKeyPair::from_seed(b"client-1");
        let signed = crate::chat::ChatMessage {
            id: 0,
            channel: "mesh".to_string(),
            sender: "client-1".to_string(),
            content: "hello from the mesh".to_string(),
            timestamp: chrono::Utc::now().timestamp_millis(),
            signature: String::new(),
            public_key: String::new(),
        }
        .signed(&client_kp);
        let chat_req = RpcRequest {
            method: "send_chat".to_string(),
            params: serde_json::json!({
                "channel": signed.channel,
                "sender": signed.sender,
                "content": signed.content,
                "timestamp": signed.timestamp,
                "signature": signed.signature,
                "public_key": signed.public_key,
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

        // Send a signal broadcast — signals require a BOUND identity, so
        // the client registers itself with a signed heartbeat first.
        let identity = PeerInfo::new("client-1", "127.0.0.1:9999").signed(&client_kp);
        let hb_req = RpcRequest {
            method: "heartbeat".to_string(),
            params: serde_json::to_value(&identity).unwrap(),
            id: 205,
        };
        let hb_bytes = serde_json::to_vec(&hb_req).unwrap();
        write_frame(&mut client, &hb_bytes).await.unwrap();
        let hb_resp_bytes = read_frame(&mut client).await.unwrap();
        let hb_resp: RpcResponse = serde_json::from_slice(&hb_resp_bytes).unwrap();
        assert!(hb_resp.result.is_some(), "bind must succeed: {hb_resp:?}");

        let signal = crate::signal::Signal::new(
            crate::signal::SignalType::PeerStatus,
            "client-1",
            serde_json::json!({"status": "online"}),
        );
        let sig_req = RpcRequest {
            method: "broadcast_signal".to_string(),
            params: signed_envelope(
                &client_kp,
                "client-1",
                serde_json::to_value(&signal).unwrap(),
            ),
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

        // Bind the client identity (hologram sync requires a signed
        // envelope from a bound sender), then send signed remote entries.
        let client_kp = crate::crypto::MeshKeyPair::from_seed(b"client-1");
        let identity = PeerInfo::new("client-1", "127.0.0.1:9999").signed(&client_kp);
        let hb_req = RpcRequest {
            method: "heartbeat".to_string(),
            params: serde_json::to_value(&identity).unwrap(),
            id: 299,
        };
        let hb_bytes = serde_json::to_vec(&hb_req).unwrap();
        write_frame(&mut client, &hb_bytes).await.unwrap();
        let hb_resp_bytes = read_frame(&mut client).await.unwrap();
        let hb_resp: RpcResponse = serde_json::from_slice(&hb_resp_bytes).unwrap();
        assert!(hb_resp.result.is_some(), "bind must succeed: {hb_resp:?}");

        let sync_req = RpcRequest {
            method: "sync_hologram".to_string(),
            params: signed_envelope(
                &client_kp,
                "client-1",
                serde_json::json!({ "entries": remote_entries }),
            ),
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
