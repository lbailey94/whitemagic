//! wm-gen3-core::peer — Decentralized Agent Trust & Social Graph
//!
//! Provides cryptographic peer identity and social trust tiers:
//! - Local: On-device processes (highest trust, Landlock bounded).
//! - Trusted: Monastic fleet peers (laptop, Mac, VPS) with mutual Ed25519 authentication.
//! - Net: Remote attested WAN peers.
//! - Stranger: Discovered / unverified peers (strictly quarantined, read-only remote stimulus).
//! - Blocked: Banned / Byzantine nodes (dropped at wire framing level).

use std::collections::HashMap;
use std::fmt;
use std::fs::{File, OpenOptions};
use std::io::{self, Read, Write};
use std::path::Path;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PeerTrustTier {
    /// Banned / Byzantine node; dropped at wire framing level.
    Blocked = 0,
    /// Discovered or unverified peer; read-only stimulus, quarantine queue.
    Stranger = 1,
    /// Remote attested WAN peer with established rate limits.
    Net = 2,
    /// Fully authenticated fleet node (e.g. laptop, Mac, VPS).
    /// Authorized for direct dispatches, signed continuity sync, and shared triage.
    Trusted = 3,
    /// On-device process (same machine, shared kernel, Landlock sandboxed).
    Local = 4,
}

impl fmt::Display for PeerTrustTier {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Blocked => write!(f, "blocked"),
            Self::Stranger => write!(f, "stranger"),
            Self::Net => write!(f, "net"),
            Self::Trusted => write!(f, "trusted"),
            Self::Local => write!(f, "local"),
        }
    }
}

impl std::str::FromStr for PeerTrustTier {
    type Err = String;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_ascii_lowercase().as_str() {
            "blocked" | "ban" => Ok(Self::Blocked),
            "stranger" | "unknown" => Ok(Self::Stranger),
            "net" | "wan" => Ok(Self::Net),
            "trusted" | "fleet" => Ok(Self::Trusted),
            "local" | "host" => Ok(Self::Local),
            other => Err(format!("unknown peer trust tier: {other}")),
        }
    }
}

/// A cryptographic peer identity in the WhiteMagic social trust graph.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerIdentity {
    /// Human-readable node identifier (e.g. "t4800-s", "miranda-macbook", "whitemagic-vps").
    pub node_id: String,
    /// Ed25519 public verifying key bytes [u8; 32].
    pub public_key: [u8; 32],
    /// Hex-encoded public key representation.
    pub public_key_hex: String,
    /// Current trust admission tier.
    pub trust_tier: PeerTrustTier,
    /// Rolling reputation score in [0.0, 1.0]. Drops on invalid signatures or protocol violations.
    pub reputation: f64,
    /// Last seen epoch or timestamp.
    pub last_seen: u64,
    /// Optional IP address or host string.
    pub endpoint: Option<String>,
    /// Explicitly granted capabilities (e.g. "sync", "dispatch", "skeleton_exec").
    pub capabilities: Vec<String>,
}

impl PeerIdentity {
    pub fn new(node_id: &str, public_key: [u8; 32], trust_tier: PeerTrustTier) -> Self {
        let public_key_hex = public_key
            .iter()
            .map(|b| format!("{:02x}", b))
            .collect::<String>();
        Self {
            node_id: node_id.to_string(),
            public_key,
            public_key_hex,
            trust_tier,
            reputation: if trust_tier == PeerTrustTier::Trusted || trust_tier == PeerTrustTier::Local
            {
                1.0
            } else {
                0.5
            },
            last_seen: 0,
            endpoint: None,
            capabilities: match trust_tier {
                PeerTrustTier::Local | PeerTrustTier::Trusted => vec![
                    "sync".into(),
                    "dispatch".into(),
                    "telemetry".into(),
                    "triage".into(),
                ],
                PeerTrustTier::Net => vec!["sync_read".into(), "dispatch".into()],
                PeerTrustTier::Stranger => vec!["stimulus_only".into()],
                PeerTrustTier::Blocked => Vec::new(),
            },
        }
    }

    /// Check if peer is permitted to perform a capability.
    pub fn can(&self, capability: &str) -> bool {
        if self.trust_tier == PeerTrustTier::Blocked {
            return false;
        }
        self.capabilities.iter().any(|c| c == capability || c == "*")
    }
}

/// Persistent directory of known peers and their trust classifications.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PeerDirectory {
    pub peers: HashMap<String, PeerIdentity>,
}

impl PeerDirectory {
    /// Load peer directory from JSON file, or initialize a default directory.
    pub fn load_or_init(path: &Path) -> io::Result<Self> {
        if path.exists() {
            let mut file = File::open(path)?;
            let mut content = String::new();
            file.read_to_string(&mut content)?;
            if let Ok(dir) = serde_json::from_str::<Self>(&content) {
                return Ok(dir);
            }
        }

        let dir = Self::default();
        let _ = dir.save(path);
        Ok(dir)
    }

    /// Persist peer directory atomically.
    pub fn save(&self, path: &Path) -> io::Result<()> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let temp_path = path.with_extension("tmp");
        let content = serde_json::to_string_pretty(self)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

        let mut file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(&temp_path)?;
        file.write_all(content.as_bytes())?;
        file.flush()?;
        std::fs::rename(temp_path, path)?;
        Ok(())
    }

    /// Insert or update a peer identity.
    pub fn admit(&mut self, peer: PeerIdentity) {
        self.peers.insert(peer.node_id.clone(), peer);
    }

    /// Retrieve peer by human-readable node ID.
    pub fn get_by_id(&self, node_id: &str) -> Option<&PeerIdentity> {
        self.peers.get(node_id)
    }

    /// Retrieve peer by public key bytes.
    pub fn get_by_key(&self, key: &[u8; 32]) -> Option<&PeerIdentity> {
        self.peers.values().find(|p| &p.public_key == key)
    }

    /// Update peer trust tier by node_id or hex public key.
    pub fn set_tier(&mut self, target: &str, tier: PeerTrustTier) -> Result<(), String> {
        if let Some(peer) = self.peers.get_mut(target) {
            peer.trust_tier = tier;
            return Ok(());
        }
        if let Some(peer) = self.peers.values_mut().find(|p| p.public_key_hex == target) {
            peer.trust_tier = tier;
            return Ok(());
        }
        Err(format!("peer `{target}` not found in directory"))
    }

    /// Check if public key is classified as Trusted or Local.
    pub fn is_trusted(&self, key: &[u8; 32]) -> bool {
        self.get_by_key(key)
            .map(|p| p.trust_tier >= PeerTrustTier::Trusted)
            .unwrap_or(false)
    }

    /// Check if public key is explicitly Blocked.
    pub fn is_blocked(&self, key: &[u8; 32]) -> bool {
        self.get_by_key(key)
            .map(|p| p.trust_tier == PeerTrustTier::Blocked)
            .unwrap_or(false)
    }

    /// List all peers sorted by node ID.
    pub fn list(&self) -> Vec<&PeerIdentity> {
        let mut list: Vec<&PeerIdentity> = self.peers.values().collect();
        list.sort_by(|a, b| a.node_id.cmp(&b.node_id));
        list
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_peer_identity_creation_and_tiers() {
        let mut key = [0u8; 32];
        key[0] = 42;
        let peer = PeerIdentity::new("test-node", key, PeerTrustTier::Trusted);

        assert_eq!(peer.node_id, "test-node");
        assert_eq!(peer.trust_tier, PeerTrustTier::Trusted);
        assert_eq!(peer.reputation, 1.0);
        assert!(peer.can("sync"));
        assert!(peer.can("dispatch"));

        let blocked = PeerIdentity::new("bad-node", key, PeerTrustTier::Blocked);
        assert_eq!(blocked.trust_tier, PeerTrustTier::Blocked);
        assert!(!blocked.can("sync"));
        assert!(!blocked.can("dispatch"));
    }

    #[test]
    fn test_peer_tier_display_and_parse() {
        let tiers = [
            (PeerTrustTier::Blocked, "blocked"),
            (PeerTrustTier::Stranger, "stranger"),
            (PeerTrustTier::Net, "net"),
            (PeerTrustTier::Trusted, "trusted"),
            (PeerTrustTier::Local, "local"),
        ];

        for (tier, s) in tiers {
            assert_eq!(tier.to_string(), s);
            assert_eq!(s.parse::<PeerTrustTier>().unwrap(), tier);
        }

        assert!("invalid".parse::<PeerTrustTier>().is_err());
    }

    #[test]
    fn test_peer_directory_operations() {
        let mut dir = PeerDirectory::default();
        let key_a = [1u8; 32];
        let key_b = [2u8; 32];

        dir.admit(PeerIdentity::new("laptop", key_a, PeerTrustTier::Local));
        dir.admit(PeerIdentity::new("vps", key_b, PeerTrustTier::Stranger));

        assert_eq!(dir.list().len(), 2);
        assert!(dir.is_trusted(&key_a));
        assert!(!dir.is_trusted(&key_b));

        // Promote vps to Trusted
        assert!(dir.set_tier("vps", PeerTrustTier::Trusted).is_ok());
        assert!(dir.is_trusted(&key_b));

        // Demote to Blocked
        assert!(dir.set_tier("vps", PeerTrustTier::Blocked).is_ok());
        assert!(dir.is_blocked(&key_b));
        assert!(!dir.is_trusted(&key_b));
    }
}

