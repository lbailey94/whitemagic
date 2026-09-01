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
    /// Ed25519 signature over the identity payload (id, address,
    /// capabilities, authority, public key). Empty when unsigned.
    #[serde(default)]
    pub signature: String,
    /// The peer's Ed25519 public key (hex) — its mesh identity. The
    /// community binds this key to the peer ID on first registration and
    /// rejects any later announcement that claims the same ID with a
    /// different key.
    #[serde(default)]
    pub public_key: String,
    /// Whether this peer is quarantined — cut off from the community
    /// (messages rejected, locks revoked, re-registration refused) until
    /// explicitly released. One bad apple must not spoil the bunch.
    #[serde(default)]
    pub quarantined: bool,
    /// Why the peer was quarantined (visible to the community).
    #[serde(default)]
    pub quarantine_reason: Option<String>,
    /// Whether the peer's AGENT is present (a request was seen on the
    /// peer's node within its away threshold). Carried in the signed
    /// heartbeat — node liveness (beacons) and agent presence are
    /// different truths: a node can be up while its agent is away.
    /// Absence is a state to report, never a failure to fix.
    #[serde(default)]
    pub agent_present: bool,
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
            public_key: String::new(),
            quarantined: false,
            quarantine_reason: None,
            agent_present: false,
        }
    }

    /// Compute the identity payload to sign (all fields except the
    /// signature and public key).
    #[must_use]
    pub fn signing_payload(&self) -> String {
        let without_sig = Self {
            signature: String::new(),
            public_key: String::new(),
            ..self.clone()
        };
        serde_json::to_string(&without_sig).unwrap_or_default()
    }

    /// Sign this peer's identity with its own Ed25519 keypair. The public
    /// key is embedded in the record and bound to the peer ID by the
    /// registry on registration.
    #[must_use]
    pub fn signed(mut self, keypair: &crate::crypto::MeshKeyPair) -> Self {
        self.public_key = keypair.public_key_hex();
        self.signature = keypair.sign_hex(&self.signing_payload());
        self
    }

    /// Verify this peer's identity signature against its own public key.
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
            public_key: String::new(),
            quarantined: false,
            quarantine_reason: None,
            agent_present: false,
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

/// Automatic quarantine policy — the community defends itself without
/// waiting for a human decision.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoQuarantineConfig {
    /// Whether auto-quarantine is active.
    pub enabled: bool,
    /// A peer is auto-quarantined after this many consecutive
    /// verification failures (forged/unsigned messages, bad identities).
    pub max_verification_failures: u32,
    /// A peer whose trust score falls below this floor is auto-quarantined.
    pub trust_floor: f32,
}

impl Default for AutoQuarantineConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            max_verification_failures: 3,
            trust_floor: 0.2,
        }
    }
}

/// Peer discovery and registry — tracks all known peers in the mesh.
pub struct PeerDiscovery {
    config: PeerDiscoveryConfig,
    peers: HashMap<PeerId, PeerInfo>,
    /// Receiver-clock liveness observations per peer. The signed
    /// `PeerInfo.last_seen` is the sender's claim; decay and status run on
    /// what THIS node observed (skewed sender clocks must not corrupt
    /// liveness math). Backfills from `last_seen` when absent.
    observed: HashMap<PeerId, i64>,
    /// Latest announced agent-presence per peer, from the peer's most
    /// recent verified heartbeat (the join carries it; re-announcements
    /// update it). Lives outside the stored `PeerInfo` because the signed
    /// entry must never be mutated post-verification — the refresh path
    /// would otherwise invalidate the stored signature.
    announced_agent_present: HashMap<PeerId, bool>,
    /// Total heartbeats received across all peers.
    total_heartbeats: u64,
    /// Total peers ever discovered (including evicted).
    total_discovered: u64,
    /// Auto-quarantine policy.
    auto_quarantine: AutoQuarantineConfig,
    /// Consecutive verification failures per peer.
    verification_failures: HashMap<PeerId, u32>,
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
            observed: HashMap::new(),
            announced_agent_present: HashMap::new(),
            total_heartbeats: 0,
            total_discovered: 0,
            auto_quarantine: AutoQuarantineConfig::default(),
            verification_failures: HashMap::new(),
        }
    }

    /// Configure the automatic quarantine policy.
    #[must_use]
    pub const fn with_auto_quarantine(mut self, config: AutoQuarantineConfig) -> Self {
        self.auto_quarantine = config;
        self
    }

    /// Current auto-quarantine policy.
    #[must_use]
    pub fn auto_quarantine_config(&self) -> AutoQuarantineConfig {
        self.auto_quarantine.clone()
    }

    /// Record a verification failure for a peer (forged signature, binding
    /// mismatch, bad identity). When the configured threshold is reached
    /// the peer is **automatically quarantined** — the community cuts the
    /// bad apple off without waiting for a human decision. Returns `true`
    /// if this failure triggered a new quarantine.
    pub fn record_verification_failure(&mut self, peer_id: &str) -> bool {
        let n = {
            let failures = self
                .verification_failures
                .entry(peer_id.to_string())
                .or_insert(0);
            *failures += 1;
            *failures
        };
        let already_quarantined = self.is_quarantined(peer_id);
        if self.auto_quarantine.enabled
            && n >= self.auto_quarantine.max_verification_failures
            && !already_quarantined
        {
            self.quarantine(
                peer_id,
                &format!("auto-quarantine: {n} consecutive verification failures"),
            );
            return true;
        }
        false
    }

    /// Clear a peer's verification-failure counter (after a success).
    pub fn record_verification_success(&mut self, peer_id: &str) {
        self.verification_failures.remove(peer_id);
    }

    /// Record a failed interaction for a peer (trust decay) — delegates to
    /// the peer's own `record_failure`.
    pub fn record_failure_for(&mut self, peer_id: &str) -> bool {
        if let Some(peer) = self.peers.get_mut(peer_id) {
            peer.record_failure();
            true
        } else {
            false
        }
    }

    /// The quarantine reason for a peer, if it is quarantined.
    #[must_use]
    pub fn quarantine_reason_of(&self, peer_id: &str) -> Option<String> {
        self.get(peer_id)
            .filter(|p| p.quarantined)
            .and_then(|p| p.quarantine_reason.clone())
    }

    /// Consecutive verification failures for a peer.
    #[must_use]
    pub fn verification_failures(&self, peer_id: &str) -> u32 {
        self.verification_failures
            .get(peer_id)
            .copied()
            .unwrap_or(0)
    }

    /// Quarantine a peer whose trust score has fallen below the configured
    /// floor (trust decay → automatic isolation). Returns `true` if a new
    /// quarantine was applied.
    pub fn quarantine_if_untrusted(&mut self, peer_id: &str) -> bool {
        if !self.auto_quarantine.enabled {
            return false;
        }
        if self.is_quarantined(peer_id) {
            return false;
        }
        let untrusted = self
            .get(peer_id)
            .is_some_and(|p| p.trust_score < self.auto_quarantine.trust_floor);
        if untrusted {
            self.quarantine(
                peer_id,
                &format!(
                    "auto-quarantine: trust {:.2} fell below the {:.2} floor",
                    self.get(peer_id).map_or(0.0, |p| p.trust_score),
                    self.auto_quarantine.trust_floor
                ),
            );
            return true;
        }
        false
    }

    /// Discover a new peer (or update an existing one).
    ///
    /// Callers of this method announce **unsigned** (UDP beacons, legacy
    /// heartbeats) — beacons carry addresses, not identity. If the peer is
    /// already identity-bound (a signed heartbeat bound its public key),
    /// an unsigned announcement may only refresh liveness and address;
    /// replacing the entry would clobber the binding and break signature
    /// verification for everything that peer sends afterwards.
    ///
    /// The stored entry is never mutated beyond what it announced: it is
    /// signed over its own fields, so post-hoc edits (e.g. stamping our
    /// clock into `last_seen`) would break re-verification. Liveness is
    /// therefore observed on OUR clock in the side map (`observed`) —
    /// decay and status read that, never the sender's timestamp (skewed
    /// sender clocks would otherwise freeze decay or evict healthy peers).
    pub fn discover(&mut self, peer: PeerInfo) {
        let now = chrono::Utc::now().timestamp();
        // Presence claims are accepted only from SIGNED announcements —
        // unsigned beacons construct `PeerInfo::new()` (agent_present
        // false by default) and must never clobber an announced truth,
        // or every beacon would drag a present agent back to "away".
        if !peer.signature.is_empty() {
            self.announced_agent_present
                .insert(peer.id.clone(), peer.agent_present);
        }
        if let Some(existing) = self.peers.get_mut(&peer.id) {
            self.observed.insert(peer.id.clone(), now);
            if !existing.public_key.is_empty() {
                existing.address = peer.address;
                existing.alive = true;
                return;
            }
        }
        if !self.peers.contains_key(&peer.id) {
            self.total_discovered += 1;
        }
        if self.peers.len() >= self.config.max_peers && !self.peers.contains_key(&peer.id) {
            return; // At capacity
        }
        self.observed.insert(peer.id.clone(), now);
        self.peers.insert(peer.id.clone(), peer);
    }

    /// Discover a peer whose identity is self-signed with its own Ed25519
    /// keypair, and bind the public key to the peer ID. Unsigned or
    /// wrongly-signed identities are rejected — an attacker cannot
    /// impersonate a peer by spoofing its ID, because the first-seen
    /// public key is bound and any later announcement claiming the same
    /// ID with a different key is refused. Quarantined peers cannot
    /// re-register until released.
    ///
    /// An existing registry entry with an **empty** bound key (e.g. from a
    /// UDP beacon — beacons carry addresses, not identity) is unbound: the
    /// first signed heartbeat performs the binding. Only a conflict with
    /// an already-bound key is identity theft.
    pub fn discover_signed(&mut self, peer: PeerInfo) -> Result<(), String> {
        if peer.signature.is_empty() || peer.public_key.is_empty() {
            return Err(format!(
                "peer '{}' announced without an identity signature",
                peer.id
            ));
        }
        if !peer.verify_signature() {
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
            if !existing.public_key.is_empty() && existing.public_key != peer.public_key {
                return Err(format!(
                    "peer '{}' identity theft refused: public key changed from {} to {}",
                    peer.id, existing.public_key, peer.public_key
                ));
            }
        }
        self.discover(peer);
        Ok(())
    }

    /// Verify a stored peer's identity signature against the mesh key.
    #[must_use]
    pub fn verify_peer(&self, peer_id: &str) -> bool {
        self.get(peer_id).is_some_and(PeerInfo::verify_signature)
    }

    /// The public key bound to a peer ID, if registered.
    #[must_use]
    pub fn bound_public_key(&self, peer_id: &str) -> Option<String> {
        self.get(peer_id).map(|p| p.public_key.clone())
    }

    /// Identity bindings for all registered peers (sender → public key),
    /// for the community read path.
    #[must_use]
    pub fn identity_bindings(&self) -> std::collections::HashMap<String, String> {
        self.peers
            .iter()
            .map(|(id, p)| (id.clone(), p.public_key.clone()))
            .filter(|(_, pk)| !pk.is_empty())
            .collect()
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
            self.observed
                .insert(peer_id.to_string(), chrono::Utc::now().timestamp());
            true
        } else {
            false
        }
    }

    /// Evict peers whose **receiver-observed** liveness is staler than the
    /// timeout. Quarantined peers are **spared** — the bad-apple record
    /// must survive decay, or silence would launder a quarantine into a
    /// clean slate. Returns the number of peers evicted.
    pub fn evict_stale(&mut self) -> usize {
        let now = chrono::Utc::now().timestamp();
        let timeout = self.config.heartbeat_timeout_sec;
        let to_evict: Vec<PeerId> = self
            .peers
            .iter()
            .filter(|(id, p)| {
                if p.quarantined {
                    return false;
                }
                let last = self.observed.get(*id).copied().unwrap_or(p.last_seen);
                now - last > timeout
            })
            .map(|(id, _)| id.clone())
            .collect();

        for id in &to_evict {
            self.peers.remove(id);
            self.observed.remove(id);
            self.announced_agent_present.remove(id);
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

    /// Get a JSON summary. `last_seen` per peer is the receiver-clock
    /// observation when available (the signed field is the sender's claim;
    /// status reports what THIS node observed). Each peer carries a
    /// derived `presence`: `online` (node observed recently + its agent
    /// present), `away` (node observed recently, agent absent — the
    /// gaming-Mac case), `offline` (no recent observation).
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        let now = chrono::Utc::now().timestamp();
        let timeout = self.config.heartbeat_timeout_sec;
        serde_json::json!({
            "peer_count": self.peers.len(),
            "total_heartbeats": self.total_heartbeats,
            "total_discovered": self.total_discovered,
            "heartbeat_timeout_sec": self.config.heartbeat_timeout_sec,
            "peers": self.peers.values().map(|p| {
                let observed_last_seen = self.observed.get(&p.id).copied().unwrap_or(p.last_seen);
                let agent_present = self
                    .announced_agent_present
                    .get(&p.id)
                    .copied()
                    .unwrap_or(p.agent_present);
                let node_up = now - observed_last_seen <= timeout;
                let presence = if !node_up {
                    "offline"
                } else if agent_present {
                    "online"
                } else {
                    "away"
                };
                serde_json::json!({
                    "id": p.id,
                    "address": p.address,
                    "alive": p.alive,
                    "presence": presence,
                    "agent_present": agent_present,
                    "capabilities": p.capabilities.iter().map(PeerCapability::as_str).collect::<Vec<_>>(),
                    "heartbeat_count": p.heartbeat_count,
                    "last_seen": observed_last_seen,
                })
            }).collect::<Vec<_>>(),
        })
    }

    /// Clear all peers.
    pub fn clear(&mut self) {
        self.peers.clear();
        self.observed.clear();
        self.announced_agent_present.clear();
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
    fn signed_heartbeat_binds_over_unsigned_beacon_entry() {
        let mut registry = PeerDiscovery::default();
        // A UDP beacon carries addresses, not identity: it registers the
        // peer with no public key bound.
        registry.discover(PeerInfo::new("node-1", "127.0.0.1:8080"));
        assert_eq!(
            registry.bound_public_key("node-1"),
            Some(String::new()),
            "beacon-discovered entry must be unbound"
        );

        // The peer's first signed heartbeat performs the binding — it must
        // not be refused as identity theft just because a beacon arrived
        // first (fast beacon cadence, slow process startup).
        let kp = crate::crypto::MeshKeyPair::from_seed(b"node-1-seed");
        let signed = PeerInfo::new("node-1", "127.0.0.1:8080").signed(&kp);
        registry
            .discover_signed(signed)
            .expect("signed heartbeat must bind over an unbound beacon entry");
        assert_eq!(
            registry.bound_public_key("node-1"),
            Some(kp.public_key_hex())
        );
    }

    #[test]
    fn identity_theft_refused_after_key_is_bound() {
        let mut registry = PeerDiscovery::default();
        let kp = crate::crypto::MeshKeyPair::from_seed(b"node-1-seed");
        let signed = PeerInfo::new("node-1", "127.0.0.1:8080").signed(&kp);
        registry
            .discover_signed(signed)
            .expect("first signed heartbeat binds");

        // A different key claiming the same (now-bound) ID is theft.
        let impostor = crate::crypto::MeshKeyPair::from_seed(b"impostor-seed");
        let forged = PeerInfo::new("node-1", "127.0.0.1:8080").signed(&impostor);
        let err = registry
            .discover_signed(forged)
            .expect_err("key change on a bound ID must be refused");
        assert!(err.contains("identity theft"), "{err}");
    }

    #[test]
    fn unsigned_beacon_never_clobbers_bound_identity() {
        let mut registry = PeerDiscovery::default();
        let kp = crate::crypto::MeshKeyPair::from_seed(b"node-1-seed");
        registry
            .discover_signed(PeerInfo::new("node-1", "127.0.0.1:8080").signed(&kp))
            .expect("signed heartbeat binds");

        // A later unsigned beacon refreshes liveness — and must keep the
        // bound key, or every signed message that peer sends afterwards
        // fails binding verification.
        registry.discover(PeerInfo::new("node-1", "127.0.0.1:8080"));
        assert_eq!(
            registry.bound_public_key("node-1"),
            Some(kp.public_key_hex()),
            "unsigned announce must not wipe the identity binding"
        );
        assert!(registry.get("node-1").is_some_and(|p| p.alive));
    }

    #[test]
    fn peer_identity_signing_verifies() {
        let kp = crate::crypto::MeshKeyPair::from_seed(b"node-1-seed");
        // Default authority is read_only.
        let peer = PeerInfo::new("node-1", "127.0.0.1:8080");

        let signed = peer.clone().signed(&kp);
        assert!(!signed.signature.is_empty());
        assert_eq!(signed.public_key, kp.public_key_hex());
        assert!(signed.verify_signature());

        // Wrong key → forged identity rejected.
        let other = crate::crypto::MeshKeyPair::from_seed(b"other-seed");
        assert!(!crate::crypto::MeshKeyPair::verify_hex(
            &signed.signing_payload(),
            &signed.signature,
            &other.public_key_hex()
        ));

        // Authority tampering (escalating privileges) → rejected.
        let mut escalated = signed;
        escalated.authority = PeerAuthority::full();
        assert!(!escalated.verify_signature());

        // Unsigned identity never verifies.
        assert!(!peer.verify_signature());
    }

    #[test]
    fn auto_quarantine_triggers_on_repeated_failures() {
        let kp = crate::crypto::MeshKeyPair::from_seed(b"node-seed");
        let mut registry = PeerDiscovery::default();
        registry
            .discover_signed(PeerInfo::new("node-1", "127.0.0.1:8080").signed(&kp))
            .unwrap();

        // Two failures: nothing yet.
        assert!(!registry.record_verification_failure("node-1"));
        assert!(!registry.record_verification_failure("node-1"));
        assert!(!registry.is_quarantined("node-1"));
        assert_eq!(registry.verification_failures("node-1"), 2);

        // Third failure crosses the default threshold (3) → auto-quarantine.
        assert!(registry.record_verification_failure("node-1"));
        assert!(registry.is_quarantined("node-1"));
        let reason = registry.quarantine_reason_of("node-1").unwrap();
        assert!(reason.contains("auto-quarantine"), "reason: {reason}");

        // A success resets the counter (post-release).
        registry.release_quarantine("node-1");
        registry.record_verification_success("node-1");
        assert_eq!(registry.verification_failures("node-1"), 0);
    }

    #[test]
    fn auto_quarantine_triggers_on_trust_floor() {
        let kp = crate::crypto::MeshKeyPair::from_seed(b"node-seed");
        let mut registry = PeerDiscovery::default();
        registry
            .discover_signed(PeerInfo::new("node-1", "127.0.0.1:8080").signed(&kp))
            .unwrap();

        // Decay trust below the default floor (0.2).
        for _ in 0..12 {
            registry.record_failure_for("node-1");
        }
        assert!(registry.quarantine_if_untrusted("node-1"));
        assert!(registry.is_quarantined("node-1"));
    }

    #[test]
    fn discover_signed_rejects_forged_peers() {
        let kp = crate::crypto::MeshKeyPair::from_seed(b"node-1-seed");
        let attacker = crate::crypto::MeshKeyPair::from_seed(b"attacker-seed");
        let mut registry = PeerDiscovery::default();

        // Legitimate peer joins the mesh; its public key is bound to the ID.
        let legit = PeerInfo::new("node-1", "127.0.0.1:8080").signed(&kp);
        assert!(registry.discover_signed(legit).is_ok());
        assert!(registry.verify_peer("node-1"));
        assert_eq!(
            registry.bound_public_key("node-1").as_deref(),
            Some(kp.public_key_hex().as_str())
        );

        // An attacker spoofs node-1's ID with a DIFFERENT key → refused
        // (identity theft: the bound public key changed).
        let spoof = PeerInfo::new("node-1", "127.0.0.1:9999").signed(&attacker);
        assert!(registry.discover_signed(spoof).is_err());

        // An unsigned announcement is rejected outright.
        let unsigned = PeerInfo::new("node-2", "127.0.0.1:8081");
        assert!(registry.discover_signed(unsigned).is_err());

        // The legit peer's identity is untouched.
        let stored = registry.get("node-1").unwrap();
        assert_eq!(stored.address, "127.0.0.1:8080");
        assert_eq!(stored.public_key, kp.public_key_hex());
        assert!(stored.verify_signature());
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
    fn evict_stale_spares_quarantined_peers() {
        let mut pd = PeerDiscovery::new(PeerDiscoveryConfig {
            heartbeat_timeout_sec: 0, // Immediate timeout
            max_peers: 100,
        });
        pd.discover(PeerInfo::new("free-1", "127.0.0.1:8080"));
        pd.discover(PeerInfo::new("bad-apple", "127.0.0.1:8081"));
        assert!(pd.quarantine("bad-apple", "test"));

        std::thread::sleep(std::time::Duration::from_secs(1));
        let evicted = pd.evict_stale();
        assert_eq!(evicted, 1);
        assert!(
            pd.get("bad-apple").is_some(),
            "quarantine record must survive registry decay"
        );
        assert!(pd.is_quarantined("bad-apple"));
    }

    #[test]
    fn decay_uses_receiver_clock_not_sender_clock() {
        // Signed heartbeats carry the sender's timestamp; a skewed clock
        // must not pin registry liveness math (ahead = decay never fires,
        // behind = healthy peers evicted). Decay and status run on the
        // receiver's observations; the signed entry itself is untouched.
        let mut pd = PeerDiscovery::default();
        let mut skewed = PeerInfo::new("skewed", "127.0.0.1:8080");
        skewed.last_seen = chrono::Utc::now().timestamp() + 600; // future sender clock
        let signed = skewed.signed(&crate::crypto::MeshKeyPair::from_seed(b"skew"));
        pd.discover_signed(signed).expect("signed peer registers");

        // The stored (signed) entry is exactly what the sender announced.
        assert!(pd.verify_peer("skewed"), "stored entry must still verify");
        // But liveness reporting observes on OUR clock.
        let summary = pd.summary();
        let last_seen = summary["peers"][0]["last_seen"].as_i64().unwrap();
        let now = chrono::Utc::now().timestamp();
        assert!(
            last_seen <= now,
            "status must report receiver-clock observation: {last_seen} > {now}"
        );
    }

    #[test]
    fn presence_derivation_online_away_offline() {
        // Node observed recently + agent present = online; observed but
        // agent absent = away (the gaming-Mac case); no recent observation
        // = offline. Absence is a state to report, never a failure.
        let mut pd = PeerDiscovery::new(PeerDiscoveryConfig {
            heartbeat_timeout_sec: 30,
            max_peers: 100,
        });
        let mut online = PeerInfo::new("p-online", "a1");
        online.agent_present = true;
        let online = online.signed(&crate::crypto::MeshKeyPair::from_seed(b"p-online"));
        pd.discover_signed(online).expect("signed peer registers");
        pd.discover(PeerInfo::new("p-away", "a2"));
        pd.discover(PeerInfo::new("p-offline", "a3"));
        pd.observed.insert(
            "p-offline".to_string(),
            chrono::Utc::now().timestamp() - 100,
        );

        let s = pd.summary();
        let presence_of = |id: &str| {
            s["peers"]
                .as_array()
                .unwrap()
                .iter()
                .find(|p| p["id"] == id)
                .unwrap()["presence"]
                .clone()
        };
        assert_eq!(presence_of("p-online"), "online");
        assert_eq!(presence_of("p-away"), "away");
        assert_eq!(presence_of("p-offline"), "offline");

        // Refresh path: a newer SIGNED announcement updates the side map
        // without mutating the stored signed entry (verify stays valid).
        // Unsigned claims (beacons) are gate-ignored.
        let mut now_away = PeerInfo::new("p-online", "a1");
        now_away.agent_present = false;
        let now_away = now_away.signed(&crate::crypto::MeshKeyPair::from_seed(b"p-online"));
        pd.discover_signed(now_away)
            .expect("same-key refresh registers");
        // Fresh summary — the earlier one is a snapshot, not a view.
        let refreshed = pd.summary();
        let presence_now = |id: &str| {
            refreshed["peers"]
                .as_array()
                .unwrap()
                .iter()
                .find(|p| p["id"] == id)
                .unwrap()["presence"]
                .clone()
        };
        assert_eq!(presence_now("p-online"), "away");
        assert!(pd.verify_peer("p-online"), "stored entry must still verify");
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
