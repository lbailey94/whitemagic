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

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
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

/// Helper: hex encode arbitrary bytes.
fn hex_encode_bytes(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

/// Helper: decode 64 hex characters into 32-byte array.
fn decode_hex_into_32(hex_str: &str, out: &mut [u8; 32]) -> Result<(), String> {
    if hex_str.len() != 64 {
        return Err(format!(
            "expected 64 hex characters for 32-byte key, got {}",
            hex_str.len()
        ));
    }
    for i in 0..32 {
        out[i] = u8::from_str_radix(&hex_str[i * 2..i * 2 + 2], 16)
            .map_err(|e| format!("invalid hex character at offset {}: {e}", i * 2))?;
    }
    Ok(())
}

/// Helper: decode 128 hex characters into 64-byte array.
fn decode_hex_into_64(hex_str: &str, out: &mut [u8; 64]) -> Result<(), String> {
    if hex_str.len() != 128 {
        return Err(format!(
            "expected 128 hex characters for 64-byte signature, got {}",
            hex_str.len()
        ));
    }
    for i in 0..64 {
        out[i] = u8::from_str_radix(&hex_str[i * 2..i * 2 + 2], 16)
            .map_err(|e| format!("invalid hex character at offset {}: {e}", i * 2))?;
    }
    Ok(())
}

/// A cryptographically signed ban certificate gossiped across the monastic fleet.
///
/// In alignment with VIOLET Architecture (P1 Scope-of-Engagement, P3 Fail-Closed Guards,
/// and P4 Dual Ledgers), a ban is not an arbitrary local mutation, but a signed attestation
/// binding the issuing authority, target identity, reason, evidence digest, and TTL.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BanCertificate {
    /// Node ID or identity of the issuing authority (must be Trusted or Local).
    pub issuer_node_id: String,
    /// Ed25519 public key hex of the issuing authority.
    pub issuer_public_key_hex: String,
    /// Target node ID or public key hex being banned.
    pub target_identity: String,
    /// Optional target public key hex (if known).
    pub target_public_key_hex: Option<String>,
    /// Rationale for the ban (e.g. Byzantine stimulus, signature forgery, RoE breach).
    pub reason: String,
    /// SHA-256 digest of evidence (e.g. malformed frame, invalid signature payload, replay nonce).
    pub evidence_hash: String,
    /// Timestamp (UTC epoch seconds) when certificate was minted.
    pub issued_at: u64,
    /// Time-to-live in seconds (0 = permanent ban).
    pub ttl_secs: u64,
    /// Hex-encoded Ed25519 signature over canonical payload.
    pub signature_hex: String,
}

impl BanCertificate {
    pub fn canonical_payload(
        issuer_key_hex: &str,
        target_identity: &str,
        target_key_hex: Option<&str>,
        reason: &str,
        evidence_hash: &str,
        issued_at: u64,
        ttl_secs: u64,
    ) -> String {
        format!(
            "WHITEMAGIC:BAN_CERT:v1|issuer:{}|target:{}|target_key:{}|reason:{}|evidence:{}|issued_at:{}|ttl:{}",
            issuer_key_hex,
            target_identity,
            target_key_hex.unwrap_or("none"),
            reason,
            evidence_hash,
            issued_at,
            ttl_secs
        )
    }

    /// Issue and sign a new BanCertificate.
    pub fn issue(
        signing_key: &SigningKey,
        issuer_node_id: &str,
        target_identity: &str,
        target_public_key_hex: Option<&str>,
        reason: &str,
        evidence_hash: &str,
        issued_at: u64,
        ttl_secs: u64,
    ) -> Self {
        let issuer_pubkey = signing_key.verifying_key().to_bytes();
        let issuer_public_key_hex = hex_encode_bytes(&issuer_pubkey);
        let payload = Self::canonical_payload(
            &issuer_public_key_hex,
            target_identity,
            target_public_key_hex,
            reason,
            evidence_hash,
            issued_at,
            ttl_secs,
        );
        let sig: Signature = signing_key.sign(payload.as_bytes());
        let signature_hex = hex_encode_bytes(&sig.to_bytes());

        Self {
            issuer_node_id: issuer_node_id.to_string(),
            issuer_public_key_hex,
            target_identity: target_identity.to_string(),
            target_public_key_hex: target_public_key_hex.map(|s| s.to_string()),
            reason: reason.to_string(),
            evidence_hash: evidence_hash.to_string(),
            issued_at,
            ttl_secs,
            signature_hex,
        }
    }

    /// Cryptographically verify the certificate and ensure it has not expired.
    pub fn verify(&self, now_secs: u64) -> Result<(), String> {
        if self.ttl_secs > 0 && now_secs > self.issued_at.saturating_add(self.ttl_secs) {
            return Err(format!(
                "ban certificate expired: issued_at={}, ttl={}, now={}",
                self.issued_at, self.ttl_secs, now_secs
            ));
        }

        let mut issuer_pubkey_bytes = [0u8; 32];
        decode_hex_into_32(&self.issuer_public_key_hex, &mut issuer_pubkey_bytes)?;

        let verifying_key = VerifyingKey::from_bytes(&issuer_pubkey_bytes)
            .map_err(|e| format!("invalid issuer verifying key: {e}"))?;

        let mut sig_bytes = [0u8; 64];
        decode_hex_into_64(&self.signature_hex, &mut sig_bytes)?;
        let signature = Signature::from_bytes(&sig_bytes);

        let payload = Self::canonical_payload(
            &self.issuer_public_key_hex,
            &self.target_identity,
            self.target_public_key_hex.as_deref(),
            &self.reason,
            &self.evidence_hash,
            self.issued_at,
            self.ttl_secs,
        );

        verifying_key
            .verify(payload.as_bytes(), &signature)
            .map_err(|e| format!("ban certificate signature verification failed: {e}"))?;

        Ok(())
    }
}

/// Persistent directory of known peers and their trust classifications.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PeerDirectory {
    pub peers: HashMap<String, PeerIdentity>,
    #[serde(default)]
    pub ban_certificates: Vec<BanCertificate>,
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

    /// Apply a signed BanCertificate to this directory.
    ///
    /// Cryptographic & Governance Invariants:
    /// 1. Signature validity: The certificate signature must match the issuer's public key.
    /// 2. TTL validity: If ttl_secs > 0, the certificate must not have expired.
    /// 3. Issuer authority: The issuer MUST be known in this directory and hold `Trusted` or `Local` tier.
    ///    Stranger or Blocked peers CANNOT ban other nodes (prevents Byzantine censorship/gossip poisoning).
    /// 4. Target demotion: The target's tier is set to `Blocked`, reputation set to `0.0`, and all capabilities revoked.
    ///    If the target was not previously known, an explicit `Blocked` identity is created.
    /// 5. Immutable ledger: The certificate is recorded in `self.ban_certificates`.
    pub fn apply_ban(&mut self, cert: &BanCertificate, now_secs: u64) -> Result<String, String> {
        // 1. Verify cryptographic integrity and TTL
        cert.verify(now_secs)?;

        // 2. Verify issuer authority in this directory
        let mut issuer_key = [0u8; 32];
        decode_hex_into_32(&cert.issuer_public_key_hex, &mut issuer_key)?;

        let issuer_peer = self.peers.values().find(|p| {
            p.public_key == issuer_key
                || p.public_key_hex == cert.issuer_public_key_hex
                || p.node_id == cert.issuer_node_id
        });

        match issuer_peer {
            Some(p) if p.trust_tier >= PeerTrustTier::Trusted => {
                // Authorized fleet issuer
            }
            Some(p) => {
                return Err(format!(
                    "issuer `{}` has tier `{}`, which lacks authority to issue bans (must be `trusted` or `local`)",
                    cert.issuer_node_id, p.trust_tier
                ));
            }
            None => {
                return Err(format!(
                    "issuer `{}` (key {}) is unknown; cannot accept unauthenticated ban from outside trusted fleet",
                    cert.issuer_node_id, cert.issuer_public_key_hex
                ));
            }
        }

        // 3. Apply the ban to target
        let mut target_found = false;
        let mut target_pubkey = [0u8; 32];
        let has_target_key = if let Some(ref tk) = cert.target_public_key_hex {
            decode_hex_into_32(tk, &mut target_pubkey).is_ok()
        } else {
            false
        };

        for peer in self.peers.values_mut() {
            if peer.node_id == cert.target_identity
                || (has_target_key && peer.public_key == target_pubkey)
                || peer.public_key_hex == cert.target_identity
            {
                peer.trust_tier = PeerTrustTier::Blocked;
                peer.reputation = 0.0;
                peer.capabilities.clear();
                target_found = true;
            }
        }

        if !target_found {
            let mut new_peer = PeerIdentity::new(
                &cert.target_identity,
                if has_target_key { target_pubkey } else { [0u8; 32] },
                PeerTrustTier::Blocked,
            );
            new_peer.reputation = 0.0;
            new_peer.capabilities.clear();
            self.peers.insert(cert.target_identity.clone(), new_peer);
        }

        // 4. Record certificate (deduplicated by signature)
        if !self.ban_certificates.iter().any(|c| c.signature_hex == cert.signature_hex) {
            self.ban_certificates.push(cert.clone());
        }

        Ok(format!(
            "Target `{}` blocked via valid BanCertificate issued by `{}` (reason: {})",
            cert.target_identity, cert.issuer_node_id, cert.reason
        ))
    }

    /// Retrieve active (non-expired) ban certificates.
    pub fn active_bans(&self, now_secs: u64) -> Vec<&BanCertificate> {
        self.ban_certificates
            .iter()
            .filter(|c| c.ttl_secs == 0 || now_secs <= c.issued_at.saturating_add(c.ttl_secs))
            .collect()
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

    #[test]
    fn test_ban_certificate_lifecycle_and_validation() {
        let seed = [7u8; 32];
        let signing_key = SigningKey::from_bytes(&seed);

        let cert = BanCertificate::issue(
            &signing_key,
            "laptop-node",
            "byzantine-node-99",
            None,
            "forged HMAC heartbeat detected",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            1000,
            3600,
        );

        // Verification succeeds before TTL
        assert!(cert.verify(2000).is_ok());

        // Verification fails after TTL
        assert!(cert.verify(5000).is_err());

        // Signature verification fails if payload tampered
        let mut tampered = cert.clone();
        tampered.reason = "tampered reason".into();
        assert!(tampered.verify(2000).is_err());
    }

    #[test]
    fn test_peer_directory_apply_ban_governance() {
        let seed_trusted = [11u8; 32];
        let trusted_signing_key = SigningKey::from_bytes(&seed_trusted);
        let trusted_pubkey = trusted_signing_key.verifying_key().to_bytes();

        let seed_stranger = [22u8; 32];
        let stranger_signing_key = SigningKey::from_bytes(&seed_stranger);
        let stranger_pubkey = stranger_signing_key.verifying_key().to_bytes();

        let mut dir = PeerDirectory::default();
        dir.admit(PeerIdentity::new("trusted-authority", trusted_pubkey, PeerTrustTier::Trusted));
        dir.admit(PeerIdentity::new("stranger-node", stranger_pubkey, PeerTrustTier::Stranger));
        dir.admit(PeerIdentity::new("innocent-peer", [33u8; 32], PeerTrustTier::Net));

        // 1. Stranger attempts to ban innocent peer -> MUST FAIL (unauthorized issuer)
        let stranger_cert = BanCertificate::issue(
            &stranger_signing_key,
            "stranger-node",
            "innocent-peer",
            None,
            "gossip poisoning attack",
            "deadbeef",
            1000,
            0,
        );
        assert!(dir.apply_ban(&stranger_cert, 1005).is_err());
        assert_eq!(dir.get_by_id("innocent-peer").unwrap().trust_tier, PeerTrustTier::Net);

        // 2. Trusted authority issues ban -> MUST SUCCEED
        let valid_cert = BanCertificate::issue(
            &trusted_signing_key,
            "trusted-authority",
            "innocent-peer",
            None,
            "confirmed Byzantine behavior",
            "deadbeef01",
            1000,
            0,
        );
        assert!(dir.apply_ban(&valid_cert, 1005).is_ok());
        let target = dir.get_by_id("innocent-peer").unwrap();
        assert_eq!(target.trust_tier, PeerTrustTier::Blocked);
        assert_eq!(target.reputation, 0.0);
        assert!(!target.can("sync"));
        assert_eq!(dir.ban_certificates.len(), 1);
    }
}

