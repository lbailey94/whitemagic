//! Peer discovery and registry — mDNS-style peer management.
//!
//! Tracks all known peers in the mesh, their capabilities, and health
//! status. Peers are evicted after a configurable timeout if no heartbeat
//! is received.

#![forbid(unsafe_code)]

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

// ── Peer ID ───────────────────────────────────────────────────────────

/// Unique identifier for a peer node.
pub type PeerId = String;

// ── Peer Capability ───────────────────────────────────────────────────

/// Capabilities a peer can advertise.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PeerCapability {
    /// Has a specific tool loaded.
    Tool(String),
    /// Has a specific LLM model loaded.
    Model(String),
    /// Has a specific Gana specialization.
    Gana(String),
    /// Can accept offloaded inference tasks.
    Inference,
    /// Can share memory/federated search.
    Memory,
    /// Can coordinate dream cycles.
    Dream,
    /// Full mesh participant (all capabilities).
    Full,
}

impl PeerCapability {
    /// Human-readable string.
    #[must_use]
    pub fn as_str(&self) -> String {
        match self {
            Self::Tool(t) => t.clone(),
            Self::Model(m) => m.clone(),
            Self::Gana(g) => g.clone(),
            Self::Inference => "inference".to_string(),
            Self::Memory => "memory".to_string(),
            Self::Dream => "dream".to_string(),
            Self::Full => "full".to_string(),
        }
    }
}

// ── Peer Authority ───────────────────────────────────────────────────

/// Authority scope for a peer — limits what a peer is allowed to do.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct PeerAuthority {
    /// Whether this peer can execute tools.
    #[serde(default)]
    pub can_execute: bool,
    /// Whether this peer can write to memory.
    #[serde(default)]
    pub can_write_memory: bool,
    /// Whether this peer can delegate authority to other peers.
    #[serde(default)]
    pub can_delegate: bool,
    /// Maximum trust score this peer can assign to delegated peers.
    #[serde(default = "default_delegate_cap")]
    pub delegate_trust_cap: f32,
    /// Allowed tool patterns (empty = all tools allowed).
    #[serde(default)]
    pub allowed_tools: Vec<String>,
    /// Denied tool patterns (takes precedence over allowed).
    #[serde(default)]
    pub denied_tools: Vec<String>,
}

impl PeerAuthority {
    /// Full authority — trusted peer with all permissions.
    #[must_use]
    pub const fn full() -> Self {
        Self {
            can_execute: true,
            can_write_memory: true,
            can_delegate: true,
            delegate_trust_cap: 0.8,
            allowed_tools: Vec::new(),
            denied_tools: Vec::new(),
        }
    }

    /// Read-only authority — can execute read tools but not write.
    #[must_use]
    pub const fn read_only() -> Self {
        Self {
            can_execute: true,
            can_write_memory: false,
            can_delegate: false,
            delegate_trust_cap: 0.0,
            allowed_tools: Vec::new(),
            denied_tools: Vec::new(),
        }
    }

    /// No authority — untrusted peer.
    #[must_use]
    pub const fn none() -> Self {
        Self {
            can_execute: false,
            can_write_memory: false,
            can_delegate: false,
            delegate_trust_cap: 0.0,
            allowed_tools: Vec::new(),
            denied_tools: Vec::new(),
        }
    }

    /// Check if a tool is allowed.
    #[must_use]
    pub fn is_tool_allowed(&self, tool_name: &str) -> bool {
        if self.denied_tools.iter().any(|p| tool_name.starts_with(p)) {
            return false;
        }
        if self.allowed_tools.is_empty() {
            return true;
        }
        self.allowed_tools.iter().any(|p| tool_name.starts_with(p))
    }
}

const fn default_trust() -> f32 {
    0.5
}

const fn default_delegate_cap() -> f32 {
    0.5
}

// ── Peer Info ─────────────────────────────────────────────────────────

/// Information about a known peer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerInfo {
    /// Unique peer ID (typically hostname + port).
    pub id: PeerId,
    /// Network address (e.g., "192.168.1.10:8080").
    pub address: String,
    /// Capabilities advertised by this peer.
    pub capabilities: Vec<PeerCapability>,
    /// Last heartbeat timestamp (Unix seconds).
    pub last_seen: i64,
    /// Whether this peer is currently alive.
    pub alive: bool,
    /// Number of heartbeats received.
    pub heartbeat_count: u64,
    /// Trust score (0.0 = untrusted, 1.0 = fully trusted).
    #[serde(default = "default_trust")]
    pub trust_score: f32,
    /// Authority scope — what this peer is authorized to do.
    #[serde(default)]
    pub authority: PeerAuthority,
    /// Number of successful interactions.
    #[serde(default)]
    pub successful_interactions: u64,
    /// Number of failed interactions.
    #[serde(default)]
    pub failed_interactions: u64,
    /// Delegated by (peer ID that delegated authority to this peer, if any).
    #[serde(default)]
    pub delegated_by: Option<PeerId>,
    /// HMAC-SHA256 signature over the identity payload (id, address,
    /// capabilities, authority), when the mesh key is configured. Empty
    /// when unsigned.
    #[serde(default)]
    pub signature: String,
    /// Whether this peer is quarantined — cut off from the community
    /// (messages rejected, locks revoked, re-registration refused) until
    /// explicitly released. One bad apple must not spoil the bunch.
    #[serde(default)]
    pub quarantined: bool,
    /// Why the peer was quarantined (visible to the community).
    #[serde(default)]
    pub quarantine_reason: Option<String>,
}

impl PeerInfo {
    /// Create a new peer entry.
    #[must_use]
    pub fn new(id: impl Into<String>, address: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            address: address.into(),
            capabilities: Vec::new(),
            last_seen: chrono::Utc::now().timestamp(),
            alive: true,
            heartbeat_count: 0,
            trust_score: default_trust(),
            authority: PeerAuthority::read_only(),
            successful_interactions: 0,
            failed_interactions: 0,
            delegated_by: None,
            signature: String::new(),
            quarantined: false,
            quarantine_reason: None,
        }
    }

    /// Compute the identity payload to sign (all fields except the signature).
    #[must_use]
    pub fn signing_payload(&self) -> String {
        let without_sig = Self {
            signature: String::new(),
            ..self.clone()
        };
        serde_json::to_string(&without_sig).unwrap_or_default()
    }

    /// Sign this peer's identity with the mesh key (HMAC-SHA256).
    #[must_use]
    pub fn signed(mut self, key: &[u8]) -> Self {
        if let Some(sig) = wm_core::sign_hmac(&self.signing_payload(), key) {
            self.signature = sig;
        }
        self
    }

    /// Verify this peer's identity signature against the mesh key.
    #[must_use]
    pub fn verify_signature(&self, key: &[u8]) -> bool {
        wm_core::verify_hmac(&self.signing_payload(), &self.signature, key)
    }

    /// Record a heartbeat from this peer.
    pub fn heartbeat(&mut self) {
        self.last_seen = chrono::Utc::now().timestamp();
        self.alive = true;
        self.heartbeat_count += 1;
    }

    /// Add a capability.
    pub fn add_capability(&mut self, cap: PeerCapability) {
        if !self.capabilities.contains(&cap) {
            self.capabilities.push(cap);
        }
    }

    /// Check if this peer has a specific capability.
    #[must_use]
    pub fn has_capability(&self, cap: &PeerCapability) -> bool {
        self.capabilities.contains(cap) || self.capabilities.contains(&PeerCapability::Full)
    }

    /// Whether this peer has a specific tool.
    #[must_use]
    pub fn has_tool(&self, tool_name: &str) -> bool {
        self.capabilities.contains(&PeerCapability::Full)
            || self
                .capabilities
                .iter()
                .any(|c| matches!(c, PeerCapability::Tool(t) if t == tool_name))
    }

    /// Whether this peer has a specific model.
    #[must_use]
    pub fn has_model(&self, model_name: &str) -> bool {
        self.capabilities.contains(&PeerCapability::Full)
            || self
                .capabilities
                .iter()
                .any(|c| matches!(c, PeerCapability::Model(m) if m == model_name))
    }

    /// Set the trust score for this peer.
    pub const fn set_trust(&mut self, trust: f32) {
        self.trust_score = trust.clamp(0.0, 1.0);
    }

    /// Record a successful interaction.
    pub fn record_success(&mut self) {
        self.successful_interactions += 1;
        // Trust increases with successful interactions (capped at 1.0)
        let boost = 0.01_f32.min(1.0 - self.trust_score);
        self.trust_score = (self.trust_score + boost).min(1.0);
    }

    /// Record a failed interaction.
    pub fn record_failure(&mut self) {
        self.failed_interactions += 1;
        // Trust decreases with failed interactions (floored at 0.0)
        let penalty = 0.05_f32.min(self.trust_score);
        self.trust_score = (self.trust_score - penalty).max(0.0);
    }

    /// Compute reliability score based on interaction history.
    #[must_use]
    pub fn reliability(&self) -> f32 {
        let total = self.successful_interactions + self.failed_interactions;
        if total == 0 {
            return 0.5;
        }
        self.successful_interactions as f32 / total as f32
    }

    /// Whether this peer is trusted enough for write operations.
    #[must_use]
    pub fn is_trusted_for_writes(&self, threshold: f32) -> bool {
        self.trust_score >= threshold && self.authority.can_write_memory
    }

    /// Set authority for this peer.
    pub fn set_authority(&mut self, authority: PeerAuthority) {
        self.authority = authority;
    }

    /// Delegate authority to another peer from this peer.
    ///
    /// Returns a new PeerInfo with delegated authority, or None if this peer
    /// cannot delegate.
    #[must_use]
    pub fn delegate_to(&self, peer_id: &str, address: &str) -> Option<Self> {
        if !self.authority.can_delegate {
            return None;
        }

        // Delegated trust cannot exceed the delegator's trust or the delegate cap
        let delegated_trust = self.trust_score.min(self.authority.delegate_trust_cap);

        // Delegated authority is more restricted than the delegator's
        let delegated_authority = PeerAuthority {
            can_execute: self.authority.can_execute,
            can_write_memory: self.authority.can_write_memory && delegated_trust > 0.5,
            can_delegate: false, // No further delegation (prevent chains)
            delegate_trust_cap: 0.0,
            allowed_tools: self.authority.allowed_tools.clone(),
            denied_tools: self.authority.denied_tools.clone(),
        };

        Some(Self {
            id: peer_id.to_string(),
            address: address.to_string(),
            capabilities: Vec::new(),
            last_seen: chrono::Utc::now().timestamp(),
            alive: true,
            heartbeat_count: 0,
            trust_score: delegated_trust,
            authority: delegated_authority,
            successful_interactions: 0,
            failed_interactions: 0,
            delegated_by: Some(self.id.clone()),
            signature: String::new(),
            quarantined: false,
            quarantine_reason: None,
        })
    }
}

// ── Peer Discovery ────────────────────────────────────────────────────

/// Configuration for peer discovery.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerDiscoveryConfig {
    /// Heartbeat timeout in seconds — peers not seen for this long are evicted.
    pub heartbeat_timeout_sec: i64,
    /// Maximum number of peers to track.
    pub max_peers: usize,
}

impl Default for PeerDiscoveryConfig {
    fn default() -> Self {
        Self {
            heartbeat_timeout_sec: 30,
            max_peers: 100,
        }
    }
}

/// Peer discovery and registry — tracks all known peers in the mesh.
pub struct PeerDiscovery {
    config: PeerDiscoveryConfig,
    peers: HashMap<PeerId, PeerInfo>,
    /// Total heartbeats received across all peers.
    total_heartbeats: u64,
    /// Total peers ever discovered (including evicted).
    total_discovered: u64,
}

impl Default for PeerDiscovery {
    fn default() -> Self {
        Self::new(PeerDiscoveryConfig::default())
    }
}

impl std::fmt::Debug for PeerDiscovery {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PeerDiscovery")
            .field("peers", &self.peers.len())
            .field("total_heartbeats", &self.total_heartbeats)
            .field("total_discovered", &self.total_discovered)
            .finish_non_exhaustive()
    }
}

impl PeerDiscovery {
    /// Create a new peer discovery manager.
    #[must_use]
    pub fn new(config: PeerDiscoveryConfig) -> Self {
        Self {
            config,
            peers: HashMap::new(),
            total_heartbeats: 0,
            total_discovered: 0,
        }
    }

    /// Discover a new peer (or update an existing one).
    pub fn discover(&mut self, peer: PeerInfo) {
        if !self.peers.contains_key(&peer.id) {
            self.total_discovered += 1;
        }
        if self.peers.len() >= self.config.max_peers && !self.peers.contains_key(&peer.id) {
            return; // At capacity
        }
        self.peers.insert(peer.id.clone(), peer);
    }

    /// Discover a peer whose identity signature verifies against the mesh
    /// key. Unsigned or wrongly-signed identities are rejected — an
    /// attacker cannot impersonate a peer by spoofing its ID.
    pub fn discover_signed(&mut self, peer: PeerInfo, key: &[u8]) -> Result<(), String> {
        if peer.signature.is_empty() {
            return Err(format!(
                "peer '{}' announced without an identity signature",
                peer.id
            ));
        }
        if !peer.verify_signature(key) {
            return Err(format!(
                "peer '{}' failed identity verification (bad or forged signature)",
                peer.id
            ));
        }
        if let Some(existing) = self.peers.get(&peer.id) {
            if existing.quarantined {
                return Err(format!(
                    "peer '{}' is quarantined{} — release it before it can rejoin",
                    peer.id,
                    existing
                        .quarantine_reason
                        .as_deref()
                        .map(|r| format!(" ({r})"))
                        .unwrap_or_default()
                ));
            }
        }
        self.discover(peer);
        Ok(())
    }

    /// Verify a stored peer's identity signature against the mesh key.
    #[must_use]
    pub fn verify_peer(&self, peer_id: &str, key: &[u8]) -> bool {
        self.get(peer_id).is_some_and(|p| p.verify_signature(key))
    }

    /// Quarantine a peer — cut it off from the community. Returns `false`
    /// if the peer is unknown or already quarantined.
    pub fn quarantine(&mut self, peer_id: &str, reason: &str) -> bool {
        if let Some(peer) = self.peers.get_mut(peer_id) {
            if peer.quarantined {
                return false;
            }
            peer.quarantined = true;
            peer.quarantine_reason = Some(reason.to_string());
            true
        } else {
            false
        }
    }

    /// Release a peer from quarantine so it can rejoin the mesh.
    pub fn release_quarantine(&mut self, peer_id: &str) -> bool {
        if let Some(peer) = self.peers.get_mut(peer_id) {
            if peer.quarantined {
                peer.quarantined = false;
                peer.quarantine_reason = None;
                return true;
            }
        }
        false
    }

    /// Whether a peer is quarantined.
    #[must_use]
    pub fn is_quarantined(&self, peer_id: &str) -> bool {
        self.get(peer_id).is_some_and(|p| p.quarantined)
    }

    /// All quarantined peers.
    #[must_use]
    pub fn quarantined(&self) -> Vec<&PeerInfo> {
        self.peers.values().filter(|p| p.quarantined).collect()
    }

    /// Record a heartbeat from a peer.
    pub fn heartbeat(&mut self, peer_id: &str) -> bool {
        if let Some(peer) = self.peers.get_mut(peer_id) {
            peer.heartbeat();
            self.total_heartbeats += 1;
            true
        } else {
            false
        }
    }

    /// Evict peers that haven't been seen for longer than the timeout.
    /// Returns the number of peers evicted.
    pub fn evict_stale(&mut self) -> usize {
        let now = chrono::Utc::now().timestamp();
        let timeout = self.config.heartbeat_timeout_sec;
        let to_evict: Vec<PeerId> = self
            .peers
            .iter()
            .filter(|(_, p)| now - p.last_seen > timeout)
            .map(|(id, _)| id.clone())
            .collect();

        for id in &to_evict {
            self.peers.remove(id);
        }

        to_evict.len()
    }

    /// Get a peer by ID.
    #[must_use]
    pub fn get(&self, peer_id: &str) -> Option<&PeerInfo> {
        self.peers.get(peer_id)
    }

    /// Get all alive peers.
    #[must_use]
    pub fn alive_peers(&self) -> Vec<&PeerInfo> {
        self.peers.values().filter(|p| p.alive).collect()
    }

    /// Find peers with a specific capability.
    #[must_use]
    pub fn peers_with_capability(&self, cap: &PeerCapability) -> Vec<&PeerInfo> {
        self.peers
            .values()
            .filter(|p| p.has_capability(cap))
            .collect()
    }

    /// Find peers that have a specific tool.
    #[must_use]
    pub fn peers_with_tool(&self, tool_name: &str) -> Vec<&PeerInfo> {
        self.peers
            .values()
            .filter(|p| p.has_tool(tool_name))
            .collect()
    }

    /// Find peers that have a specific model.
    #[must_use]
    pub fn peers_with_model(&self, model_name: &str) -> Vec<&PeerInfo> {
        self.peers
            .values()
            .filter(|p| p.has_model(model_name))
            .collect()
    }

    /// Number of known peers.
    #[must_use]
    pub fn peer_count(&self) -> usize {
        self.peers.len()
    }

    /// Total heartbeats received.
    #[must_use]
    pub const fn total_heartbeats(&self) -> u64 {
        self.total_heartbeats
    }

    /// Total peers ever discovered.
    #[must_use]
    pub const fn total_discovered(&self) -> u64 {
        self.total_discovered
    }

    /// Get a JSON summary.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "peer_count": self.peers.len(),
            "total_heartbeats": self.total_heartbeats,
            "total_discovered": self.total_discovered,
            "peers": self.peers.values().map(|p| serde_json::json!({
                "id": p.id,
                "address": p.address,
                "alive": p.alive,
                "capabilities": p.capabilities.iter().map(PeerCapability::as_str).collect::<Vec<_>>(),
                "heartbeat_count": p.heartbeat_count,
                "last_seen": p.last_seen,
            })).collect::<Vec<_>>(),
        })
    }

    /// Clear all peers.
    pub fn clear(&mut self) {
        self.peers.clear();
    }

    /// Find peers with trust score >= threshold.
    #[must_use]
    pub fn trusted_peers(&self, threshold: f32) -> Vec<&PeerInfo> {
        self.peers
            .values()
            .filter(|p| p.alive && p.trust_score >= threshold)
            .collect()
    }

    /// Find peers trusted enough for write operations.
    #[must_use]
    pub fn write_trusted_peers(&self, threshold: f32) -> Vec<&PeerInfo> {
        self.peers
            .values()
            .filter(|p| p.alive && p.is_trusted_for_writes(threshold))
            .collect()
    }

    /// Record a successful interaction for a peer.
    pub fn record_success(&mut self, peer_id: &str) -> bool {
        if let Some(peer) = self.peers.get_mut(peer_id) {
            peer.record_success();
            true
        } else {
            false
        }
    }

    /// Record a failed interaction for a peer.
    pub fn record_failure(&mut self, peer_id: &str) -> bool {
        if let Some(peer) = self.peers.get_mut(peer_id) {
            peer.record_failure();
            true
        } else {
            false
        }
    }

    /// Delegate authority from one peer to a new peer.
    ///
    /// The delegating peer must have `can_delegate` authority. The new peer
    /// is added to the registry with restricted authority.
    pub fn delegate(&mut self, delegator_id: &str, new_peer_id: &str, address: &str) -> bool {
        let delegated = {
            let Some(delegator) = self.peers.get(delegator_id) else {
                return false;
            };
            delegator.delegate_to(new_peer_id, address)
        };

        if let Some(peer) = delegated {
            self.discover(peer);
            true
        } else {
            false
        }
    }

    /// Get average trust score across all alive peers.
    #[must_use]
    pub fn average_trust(&self) -> f32 {
        let alive: Vec<&PeerInfo> = self.peers.values().filter(|p| p.alive).collect();
        if alive.is_empty() {
            return 0.0;
        }
        alive.iter().map(|p| p.trust_score).sum::<f32>() / alive.len() as f32
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn peer_info_new() {
        let peer = PeerInfo::new("node-1", "127.0.0.1:8080");
        assert_eq!(peer.id, "node-1");
        assert_eq!(peer.address, "127.0.0.1:8080");
        assert!(peer.alive);
        assert_eq!(peer.heartbeat_count, 0);
    }

    #[test]
    fn peer_identity_signing_verifies() {
        let key = b"mesh-secret";
        // Default authority is read_only.
        let peer = PeerInfo::new("node-1", "127.0.0.1:8080");

        let signed = peer.clone().signed(key);
        assert!(!signed.signature.is_empty());
        assert!(signed.verify_signature(key));

        // Wrong key → forged identity rejected.
        assert!(!signed.verify_signature(b"other-secret"));

        // Authority tampering (escalating privileges) → rejected.
        let mut escalated = signed;
        escalated.authority = PeerAuthority::full();
        assert!(!escalated.verify_signature(key));

        // Unsigned identity never verifies.
        assert!(!peer.verify_signature(key));
    }

    #[test]
    fn discover_signed_rejects_forged_peers() {
        let key = b"mesh-secret";
        let mut registry = PeerDiscovery::default();

        // Legitimate peer joins the mesh.
        let legit = PeerInfo::new("node-1", "127.0.0.1:8080").signed(key);
        assert!(registry.discover_signed(legit, key).is_ok());
        assert!(registry.verify_peer("node-1", key));

        // An attacker spoofs node-1's ID with the wrong key.
        let spoof = PeerInfo::new("node-1", "127.0.0.1:9999").signed(b"attacker-key");
        assert!(registry.discover_signed(spoof, key).is_err());

        // An unsigned announcement is rejected outright.
        let unsigned = PeerInfo::new("node-2", "127.0.0.1:8081");
        assert!(registry.discover_signed(unsigned, key).is_err());

        // The legit peer's identity is untouched.
        let stored = registry.get("node-1").unwrap();
        assert_eq!(stored.address, "127.0.0.1:8080");
        assert!(stored.verify_signature(key));
    }

    #[test]
    fn peer_info_heartbeat() {
        let mut peer = PeerInfo::new("node-1", "127.0.0.1:8080");
        peer.heartbeat();
        peer.heartbeat();
        assert_eq!(peer.heartbeat_count, 2);
    }

    #[test]
    fn peer_info_capabilities() {
        let mut peer = PeerInfo::new("node-1", "127.0.0.1:8080");
        peer.add_capability(PeerCapability::Tool("memory.search".to_string()));
        peer.add_capability(PeerCapability::Inference);

        assert!(peer.has_capability(&PeerCapability::Inference));
        assert!(peer.has_tool("memory.search"));
        assert!(!peer.has_tool("memory.create"));
    }

    #[test]
    fn peer_info_full_capability() {
        let mut peer = PeerInfo::new("node-1", "127.0.0.1:8080");
        peer.add_capability(PeerCapability::Full);

        assert!(peer.has_tool("anything"));
        assert!(peer.has_model("llama-7b"));
        assert!(peer.has_capability(&PeerCapability::Dream));
    }

    #[test]
    fn peer_discovery_discover() {
        let mut pd = PeerDiscovery::default();
        pd.discover(PeerInfo::new("node-1", "127.0.0.1:8080"));
        pd.discover(PeerInfo::new("node-2", "127.0.0.1:8081"));

        assert_eq!(pd.peer_count(), 2);
        assert_eq!(pd.total_discovered(), 2);
    }

    #[test]
    fn peer_discovery_heartbeat() {
        let mut pd = PeerDiscovery::default();
        pd.discover(PeerInfo::new("node-1", "127.0.0.1:8080"));

        assert!(pd.heartbeat("node-1"));
        assert!(!pd.heartbeat("unknown"));
        assert_eq!(pd.total_heartbeats(), 1);
    }

    #[test]
    fn peer_discovery_evict_stale() {
        let mut pd = PeerDiscovery::new(PeerDiscoveryConfig {
            heartbeat_timeout_sec: 0, // Immediate timeout
            max_peers: 100,
        });
        pd.discover(PeerInfo::new("node-1", "127.0.0.1:8080"));
        pd.discover(PeerInfo::new("node-2", "127.0.0.1:8081"));

        std::thread::sleep(std::time::Duration::from_secs(1));
        let evicted = pd.evict_stale();
        assert_eq!(evicted, 2);
        assert_eq!(pd.peer_count(), 0);
    }

    #[test]
    fn peer_discovery_max_peers() {
        let mut pd = PeerDiscovery::new(PeerDiscoveryConfig {
            heartbeat_timeout_sec: 30,
            max_peers: 2,
        });
        pd.discover(PeerInfo::new("node-1", "addr1"));
        pd.discover(PeerInfo::new("node-2", "addr2"));
        pd.discover(PeerInfo::new("node-3", "addr3")); // Should be rejected

        assert_eq!(pd.peer_count(), 2);
    }

    #[test]
    fn peer_discovery_find_by_capability() {
        let mut pd = PeerDiscovery::default();
        let mut p1 = PeerInfo::new("node-1", "addr1");
        p1.add_capability(PeerCapability::Inference);
        let mut p2 = PeerInfo::new("node-2", "addr2");
        p2.add_capability(PeerCapability::Memory);
        pd.discover(p1);
        pd.discover(p2);

        let inference_peers = pd.peers_with_capability(&PeerCapability::Inference);
        assert_eq!(inference_peers.len(), 1);
        assert_eq!(inference_peers[0].id, "node-1");
    }

    #[test]
    fn peer_discovery_find_by_tool() {
        let mut pd = PeerDiscovery::default();
        let mut p1 = PeerInfo::new("node-1", "addr1");
        p1.add_capability(PeerCapability::Tool("memory.search".to_string()));
        pd.discover(p1);

        let peers = pd.peers_with_tool("memory.search");
        assert_eq!(peers.len(), 1);
        assert_eq!(peers[0].id, "node-1");
    }

    #[test]
    fn peer_discovery_summary() {
        let mut pd = PeerDiscovery::default();
        pd.discover(PeerInfo::new("node-1", "addr1"));
        pd.heartbeat("node-1");

        let summary = pd.summary();
        assert_eq!(summary["peer_count"], 1);
        assert_eq!(summary["total_heartbeats"], 1);
    }

    #[test]
    fn peer_discovery_clear() {
        let mut pd = PeerDiscovery::default();
        pd.discover(PeerInfo::new("node-1", "addr1"));
        pd.clear();
        assert_eq!(pd.peer_count(), 0);
    }

    #[test]
    fn peer_capability_as_str() {
        assert_eq!(PeerCapability::Inference.as_str(), "inference");
        assert_eq!(PeerCapability::Memory.as_str(), "memory");
        assert_eq!(PeerCapability::Full.as_str(), "full");
        assert_eq!(PeerCapability::Tool("test".to_string()).as_str(), "test");
    }

    // ── Trust scoring tests ──────────────────────────────────────────

    #[test]
    fn peer_default_trust() {
        let peer = PeerInfo::new("node-1", "addr1");
        assert!((peer.trust_score - 0.5).abs() < 0.01);
    }

    #[test]
    fn peer_set_trust() {
        let mut peer = PeerInfo::new("node-1", "addr1");
        peer.set_trust(0.9);
        assert!((peer.trust_score - 0.9).abs() < 0.01);
        // Clamped
        peer.set_trust(2.0);
        assert!((peer.trust_score - 1.0).abs() < 0.01);
        peer.set_trust(-1.0);
        assert!((peer.trust_score - 0.0).abs() < 0.01);
    }

    #[test]
    fn peer_record_success_increases_trust() {
        let mut peer = PeerInfo::new("node-1", "addr1");
        let initial = peer.trust_score;
        for _ in 0..10 {
            peer.record_success();
        }
        assert!(
            peer.trust_score > initial,
            "Trust should increase with successes"
        );
        assert!(peer.trust_score <= 1.0);
        assert_eq!(peer.successful_interactions, 10);
    }

    #[test]
    fn peer_record_failure_decreases_trust() {
        let mut peer = PeerInfo::new("node-1", "addr1");
        peer.set_trust(0.8);
        let initial = peer.trust_score;
        for _ in 0..5 {
            peer.record_failure();
        }
        assert!(
            peer.trust_score < initial,
            "Trust should decrease with failures"
        );
        assert!(peer.trust_score >= 0.0);
        assert_eq!(peer.failed_interactions, 5);
    }

    #[test]
    fn peer_reliability() {
        let mut peer = PeerInfo::new("node-1", "addr1");
        assert!(
            (peer.reliability() - 0.5).abs() < 0.01,
            "No interactions → 0.5"
        );

        peer.record_success();
        peer.record_success();
        peer.record_failure();
        assert!((peer.reliability() - (2.0 / 3.0)).abs() < 0.01);
    }

    #[test]
    fn peer_authority_tool_filtering() {
        let auth = PeerAuthority {
            can_execute: true,
            can_write_memory: false,
            can_delegate: false,
            delegate_trust_cap: 0.0,
            allowed_tools: vec!["memory.".into()],
            denied_tools: vec!["memory.delete".into()],
        };
        assert!(auth.is_tool_allowed("memory.search"));
        assert!(!auth.is_tool_allowed("memory.delete"));
        assert!(!auth.is_tool_allowed("tool.execute"));
    }

    #[test]
    fn peer_authority_empty_allowed_allows_all() {
        let auth = PeerAuthority::full();
        assert!(auth.is_tool_allowed("anything"));
    }

    #[test]
    fn peer_delegation_creates_restricted_peer() {
        let mut delegator = PeerInfo::new("node-1", "addr1");
        delegator.set_trust(0.9);
        delegator.set_authority(PeerAuthority::full());

        let delegated = delegator.delegate_to("node-2", "addr2").unwrap();
        assert_eq!(delegated.id, "node-2");
        assert_eq!(delegated.delegated_by, Some("node-1".to_string()));
        // Delegated trust capped at delegate_trust_cap (0.8)
        assert!(delegated.trust_score <= 0.8);
        // Cannot further delegate
        assert!(!delegated.authority.can_delegate);
    }

    #[test]
    fn peer_delegation_fails_without_authority() {
        let delegator = PeerInfo::new("node-1", "addr1");
        // Default authority is read_only — no delegation
        assert!(delegator.delegate_to("node-2", "addr2").is_none());
    }

    #[test]
    fn peer_is_trusted_for_writes() {
        let mut peer = PeerInfo::new("node-1", "addr1");
        peer.set_trust(0.8);
        peer.set_authority(PeerAuthority {
            can_write_memory: true,
            ..PeerAuthority::read_only()
        });
        assert!(peer.is_trusted_for_writes(0.7));
        assert!(!peer.is_trusted_for_writes(0.9));
    }

    #[test]
    fn peer_discovery_trusted_peers() {
        let mut pd = PeerDiscovery::default();
        let mut p1 = PeerInfo::new("node-1", "addr1");
        p1.set_trust(0.9);
        let mut p2 = PeerInfo::new("node-2", "addr2");
        p2.set_trust(0.3);
        pd.discover(p1);
        pd.discover(p2);

        let trusted = pd.trusted_peers(0.7);
        assert_eq!(trusted.len(), 1);
        assert_eq!(trusted[0].id, "node-1");
    }

    #[test]
    fn peer_discovery_record_success_failure() {
        let mut pd = PeerDiscovery::default();
        pd.discover(PeerInfo::new("node-1", "addr1"));

        assert!(pd.record_success("node-1"));
        assert!(pd.record_failure("node-1"));
        assert!(!pd.record_success("unknown"));

        let peer = pd.get("node-1").unwrap();
        assert_eq!(peer.successful_interactions, 1);
        assert_eq!(peer.failed_interactions, 1);
    }

    #[test]
    fn peer_discovery_delegate() {
        let mut pd = PeerDiscovery::default();
        let mut p1 = PeerInfo::new("node-1", "addr1");
        p1.set_trust(0.9);
        p1.set_authority(PeerAuthority::full());
        pd.discover(p1);

        assert!(pd.delegate("node-1", "node-2", "addr2"));
        assert_eq!(pd.peer_count(), 2);
        let p2 = pd.get("node-2").unwrap();
        assert_eq!(p2.delegated_by, Some("node-1".to_string()));
    }

    #[test]
    fn peer_discovery_average_trust() {
        let mut pd = PeerDiscovery::default();
        let mut p1 = PeerInfo::new("node-1", "addr1");
        p1.set_trust(0.8);
        let mut p2 = PeerInfo::new("node-2", "addr2");
        p2.set_trust(0.6);
        pd.discover(p1);
        pd.discover(p2);

        let avg = pd.average_trust();
        assert!((avg - 0.7).abs() < 0.01);
    }
}
