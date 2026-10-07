//! wm-gen3-core::mesh — Mandala P2P Mesh & Sovereign Synchronization
//!
//! Enforces:
//! 1. Zero-Bypass Remote Ingress: Remote data enters strictly as `RemoteStimulus`.
//!    A remote peer cannot directly mutate state or acquire local `CommitCapability`.
//! 2. Identity Decoupling: IP addresses and sockets have zero authority; Ed25519
//!    keys authenticate peer identity.
//! 3. Ancestry Over Chronology: Wall-clock timestamps carry zero causal authority.
//! 4. Partition-Healing Dual-Preservation: Concurrent branches merge idempotently.
//! 5. Sneakernet Portability: Live TCP sync and air-gapped `.wmpack` bundles use
//!    identical cryptographic validation and deduplication semantics.

use std::collections::HashMap;
use std::fmt;
use std::fs::{File, OpenOptions};
use std::io::{self, Read, Write};
use std::net::{IpAddr, Ipv4Addr, SocketAddr, TcpListener, TcpStream, ToSocketAddrs};
use std::path::Path;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::mandala::ContinuityReceipt05;

use crate::bicameral::{ActionSkeleton, GeneseedVault};
use crate::cladistics::{
    CandidateAssessment, EvolutionaryFate, FitnessVector, GenomeId, ParetoGate,
    ProtectedVectorDelta,
};
use crate::evidence::{Domain, EvidenceRecord};
use crate::ops::{ImportKind, RememberItem, Substrate};
use crate::store::StoreError;
use crate::transport::{
    DEFAULT_CONNECT_TIMEOUT, DEFAULT_FRAME_ASSEMBLY_TIMEOUT, PhysicalFrameCodec,
};

pub const DEFAULT_MESH_PORT: u16 = 7369;
pub const MESH_PROTOCOL_VERSION: u32 = 1;
pub const WMPACK_MAGIC: &str = "WMPACK1";

// ============================================================================
// 1. Errors & Status Types
// ============================================================================

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum MeshError {
    IoError(String),
    FramingError(String),
    HandshakeFailed(String),
    InvalidSignature(String),
    UntrustedSigner(String),
    ProtocolMismatch {
        expected: u32,
        received: u32,
    },
    BundleCorrupted(String),
    StoreError(String),
    Timeout(String),
    /// Unsigned, mis-signed, or non-allowlisted peer request refused.
    Unauthorized(String),
}

impl fmt::Display for MeshError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::IoError(s) => write!(f, "Mesh I/O error: {}", s),
            Self::FramingError(s) => write!(f, "Mesh framing error: {}", s),
            Self::HandshakeFailed(s) => write!(f, "Mesh handshake failed: {}", s),
            Self::InvalidSignature(s) => write!(f, "Invalid cryptographic signature: {}", s),
            Self::UntrustedSigner(s) => write!(f, "Untrusted signer: {}", s),
            Self::ProtocolMismatch { expected, received } => {
                write!(
                    f,
                    "Protocol version mismatch: expected {}, received {}",
                    expected, received
                )
            }
            Self::BundleCorrupted(s) => write!(f, "Sync bundle corrupted: {}", s),
            Self::StoreError(s) => write!(f, "Store operation error: {}", s),
            Self::Timeout(s) => write!(f, "Operation timed out: {}", s),
            Self::Unauthorized(s) => write!(f, "Unauthorized mesh request: {}", s),
        }
    }
}

impl std::error::Error for MeshError {}

impl From<io::Error> for MeshError {
    fn from(err: io::Error) -> Self {
        Self::IoError(err.to_string())
    }
}

impl From<StoreError> for MeshError {
    fn from(err: StoreError) -> Self {
        Self::StoreError(err.to_string())
    }
}

// ============================================================================
// 2. Wire Protocol Envelopes
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshHandshake {
    pub node_id: String,
    pub public_key: [u8; 32],
    pub epoch: u64,
    pub record_count: u64,
    pub head_hash: String,
    pub protocol_version: u32,
    /// Client liveness challenge; echoed by the server ack. Zero = legacy unsigned.
    #[serde(default)]
    pub nonce: [u8; 32],
    /// Server signature over the canonical ack payload (empty on client requests).
    #[serde(default)]
    pub signature: Vec<u8>,
}

impl MeshHandshake {
    /// Canonical payload covered by the responder's Ed25519 handshake signature.
    pub fn signing_payload(&self) -> Vec<u8> {
        format!(
            "WHITEMAGIC:MESH_HANDSHAKE_ACK:v1|node:{}|pubkey:{}|epoch:{}|records:{}|head:{}|proto:{}|nonce:{}",
            self.node_id,
            hex_encode_key(&self.public_key),
            self.epoch,
            self.record_count,
            self.head_hash,
            self.protocol_version,
            hex_encode_key(&self.nonce)
        )
        .into_bytes()
    }

    /// Sign this handshake ack in place with the responder's sovereign mesh key.
    pub fn sign_with(&mut self, signing_key: &SigningKey) {
        self.public_key = signing_key.verifying_key().to_bytes();
        let payload = self.signing_payload();
        self.signature = signing_key.sign(&payload).to_bytes().to_vec();
    }

    /// Verify the ack signature and that it echoes the client's challenge nonce.
    pub fn verify(&self, expected_nonce: &[u8; 32]) -> Result<(), MeshError> {
        if &self.nonce != expected_nonce {
            return Err(MeshError::Unauthorized(
                "handshake ack nonce does not match the client challenge".to_string(),
            ));
        }
        if self.signature.is_empty() {
            return Err(MeshError::Unauthorized(
                "handshake ack carries no signature".to_string(),
            ));
        }
        let sig_bytes: [u8; 64] = self.signature.as_slice().try_into().map_err(|_| {
            MeshError::Unauthorized("handshake ack signature length != 64 bytes".to_string())
        })?;
        let verifying_key = VerifyingKey::from_bytes(&self.public_key)
            .map_err(|e| MeshError::Unauthorized(format!("invalid handshake key: {e}")))?;
        verifying_key
            .verify(&self.signing_payload(), &Signature::from_bytes(&sig_bytes))
            .map_err(|e| {
                MeshError::Unauthorized(format!("handshake ack signature verification failed: {e}"))
            })
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SyncRecord {
    pub record_id: u64,
    pub content: String,
    pub source: String,
    pub kind: String,
    pub sha256: String,
    pub created_at: u64,
}

impl SyncRecord {
    pub fn from_evidence_record(rec: &EvidenceRecord) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(rec.content().as_bytes());
        let sha256 = format!("{:x}", hasher.finalize());

        let kind = match rec.domain() {
            Domain::World => "reported",
            Domain::System => "system",
            Domain::Simulated => "simulated",
            Domain::Reported => "reported",
        };

        Self {
            record_id: rec.id(),
            content: rec.content().to_string(),
            source: rec.source().to_string(),
            kind: kind.to_string(),
            sha256,
            created_at: rec.created_at(),
        }
    }

    pub fn to_remember_item(&self) -> RememberItem {
        let kind = match self.kind.as_str() {
            "system" => ImportKind::System,
            "simulated" => ImportKind::Simulated,
            _ => ImportKind::Reported,
        };

        RememberItem {
            content: self.content.clone(),
            source: self.source.clone(),
            kind,
        }
    }

    /// Verify the content-addressed digest carried by this record before ingest.
    ///
    /// Wire records are signed indirectly through the enclosing `SyncResponse`
    /// (or bundle); this digest binds the payload bytes to the record the peer
    /// signed. Unverifiable records are refused loudly rather than appended.
    pub fn verify_integrity(&self) -> Result<(), MeshError> {
        if self.sha256.is_empty() {
            return Err(MeshError::BundleCorrupted(format!(
                "record {} carries no sha256 digest; refusing unverifiable ingest",
                self.record_id
            )));
        }
        let mut hasher = Sha256::new();
        hasher.update(self.content.as_bytes());
        let digest = format!("{:x}", hasher.finalize());
        if digest != self.sha256 {
            return Err(MeshError::BundleCorrupted(format!(
                "record {} content digest mismatch (declared {}, computed {}); refusing ingest",
                self.record_id, self.sha256, digest
            )));
        }
        Ok(())
    }
}

fn hex_encode_key(key: &[u8; 32]) -> String {
    key.iter().map(|b| format!("{:02x}", b)).collect()
}

/// Maximum accepted age/skew of a signed sync response (defense-in-depth on
/// top of the handshake-nonce binding).
pub const MESH_RESPONSE_MAX_AGE_MS: u64 = 120_000;

fn now_millis() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

fn random_nonce() -> [u8; 32] {
    let mut bytes = [0u8; 32];
    if getrandom::fill(&mut bytes).is_err() {
        // A zero nonce is refused by peers, so fail closed rather than reuse it.
        bytes = [0u8; 32];
    }
    bytes
}

fn random_session_id() -> String {
    uuid::Uuid::new_v4().to_string()
}

/// Parse `WM_MESH_PEER_ALLOWLIST`: comma-separated peer node ids or 32-byte
/// pubkey hex. Empty entries are ignored; matching is case-insensitive.
fn parse_peer_allowlist(raw: &str) -> Vec<String> {
    raw.split(',')
        .map(str::trim)
        .filter(|entry| !entry.is_empty())
        .map(|entry| entry.to_ascii_lowercase())
        .collect()
}

fn mesh_peer_allowlist() -> Vec<String> {
    parse_peer_allowlist(&std::env::var("WM_MESH_PEER_ALLOWLIST").unwrap_or_default())
}

fn peer_allowed(allowlist: &[String], node_id: &str, public_key: &[u8; 32]) -> bool {
    let node_id = node_id.to_ascii_lowercase();
    let key_hex = hex_encode_key(public_key);
    allowlist
        .iter()
        .any(|entry| entry == &node_id || entry == &key_hex)
}

/// Peer-pinning policy: an empty allowlist means loopback-only sync; a
/// non-empty allowlist requires the peer node id or pubkey to be listed.
fn check_peer_allowlist(
    allowlist: &[String],
    is_loopback: bool,
    node_id: &str,
    public_key: &[u8; 32],
) -> Result<(), MeshError> {
    if allowlist.is_empty() {
        return if is_loopback {
            Ok(())
        } else {
            Err(MeshError::Unauthorized(format!(
                "refusing remote mesh peer '{node_id}' ({}): WM_MESH_PEER_ALLOWLIST is empty; loopback-only sync",
                hex_encode_key(public_key)
            )))
        };
    }
    if peer_allowed(allowlist, node_id, public_key) {
        Ok(())
    } else {
        Err(MeshError::UntrustedSigner(format!(
            "peer '{node_id}' ({}) is not in WM_MESH_PEER_ALLOWLIST",
            hex_encode_key(public_key)
        )))
    }
}

/// Shared authorization gate for signed sync requests: handshake binding,
/// peer pinning, and replay protection.
#[allow(clippy::too_many_arguments)]
fn authorize_signed_request(
    label: &str,
    handshake_nonce: Option<[u8; 32]>,
    nonce: [u8; 32],
    requester_id: &str,
    requester_pubkey: &[u8; 32],
    session_id: &str,
    is_loopback: bool,
    allowlist: &[String],
    replay: &ReplayCache,
) -> Result<(), MeshError> {
    match handshake_nonce {
        Some(expected) if nonce == expected => {}
        Some(_) => {
            return Err(MeshError::Unauthorized(format!(
                "{label}: nonce does not match handshake challenge"
            )));
        }
        None => {
            return Err(MeshError::Unauthorized(format!(
                "{label}: handshake required before sync"
            )));
        }
    }
    check_peer_allowlist(allowlist, is_loopback, requester_id, requester_pubkey)?;
    let replay_key = format!("{}:{}", hex_encode_key(requester_pubkey), session_id);
    replay.observe(&replay_key, now_secs())
}

/// Bounded replay cache for signed requests, keyed by requester pubkey + session id.
#[derive(Default)]
struct ReplayCache {
    seen: Mutex<HashMap<String, u64>>,
}

impl ReplayCache {
    fn observe(&self, key: &str, now_secs: u64) -> Result<(), MeshError> {
        let mut seen = self.seen.lock().unwrap_or_else(|e| e.into_inner());
        seen.retain(|_, first_seen| {
            now_secs.saturating_sub(*first_seen) <= MESH_REPLAY_WINDOW_SECS
        });
        if seen.contains_key(key) {
            return Err(MeshError::Unauthorized(format!(
                "replayed mesh request for session '{key}' refused"
            )));
        }
        seen.insert(key.to_string(), now_secs);
        Ok(())
    }
}

const MESH_REPLAY_WINDOW_SECS: u64 = MESH_RESPONSE_MAX_AGE_MS / 1000;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncRequest {
    pub requester_id: String,
    pub since_epoch: u64,
    pub limit: usize,
    /// Ed25519 public key of the requester (zeroed on legacy unsigned clients).
    #[serde(default)]
    pub requester_pubkey: [u8; 32],
    /// Ed25519 signature over the canonical request payload.
    #[serde(default)]
    pub signature: Vec<u8>,
    /// Handshake challenge nonce this request is bound to.
    #[serde(default)]
    pub nonce: [u8; 32],
    /// Per-request session id (replay cache key).
    #[serde(default)]
    pub session_id: String,
}

impl SyncRequest {
    /// Canonical payload covered by the requester's Ed25519 signature.
    pub fn signing_payload(&self) -> Vec<u8> {
        format!(
            "WHITEMAGIC:MESH_SYNC_REQ:v2|requester:{}|pubkey:{}|since:{}|limit:{}|nonce:{}|session:{}",
            self.requester_id,
            hex_encode_key(&self.requester_pubkey),
            self.since_epoch,
            self.limit,
            hex_encode_key(&self.nonce),
            self.session_id
        )
        .into_bytes()
    }

    /// Build a signed sync request with the caller's sovereign mesh identity,
    /// generating a fresh nonce and session id.
    pub fn signed(
        requester_id: &str,
        since_epoch: u64,
        limit: usize,
        signing_key: &SigningKey,
    ) -> Self {
        Self::signed_with(
            requester_id,
            since_epoch,
            limit,
            random_nonce(),
            &random_session_id(),
            signing_key,
        )
    }

    /// Build a signed sync request bound to an explicit handshake nonce/session.
    pub fn signed_with(
        requester_id: &str,
        since_epoch: u64,
        limit: usize,
        nonce: [u8; 32],
        session_id: &str,
        signing_key: &SigningKey,
    ) -> Self {
        let mut req = Self {
            requester_id: requester_id.to_string(),
            since_epoch,
            limit,
            requester_pubkey: signing_key.verifying_key().to_bytes(),
            signature: Vec::new(),
            nonce,
            session_id: session_id.to_string(),
        };
        let payload = req.signing_payload();
        req.signature = signing_key.sign(&payload).to_bytes().to_vec();
        req
    }

    /// Verify the embedded signed peer identity. Unsigned or invalid requests fail closed.
    pub fn verify(&self) -> Result<(), MeshError> {
        if self.nonce == [0u8; 32] {
            return Err(MeshError::Unauthorized(format!(
                "sync_request from '{}' carries no handshake nonce",
                self.requester_id
            )));
        }
        if self.session_id.is_empty() {
            return Err(MeshError::Unauthorized(format!(
                "sync_request from '{}' carries no session id",
                self.requester_id
            )));
        }
        if self.signature.is_empty() {
            return Err(MeshError::Unauthorized(format!(
                "sync_request from '{}' carries no signature",
                self.requester_id
            )));
        }
        let sig_bytes: [u8; 64] = self.signature.as_slice().try_into().map_err(|_| {
            MeshError::Unauthorized("sync_request signature length != 64 bytes".to_string())
        })?;
        let verifying_key = VerifyingKey::from_bytes(&self.requester_pubkey)
            .map_err(|e| MeshError::Unauthorized(format!("invalid requester key: {e}")))?;
        verifying_key
            .verify(&self.signing_payload(), &Signature::from_bytes(&sig_bytes))
            .map_err(|e| {
                MeshError::Unauthorized(format!(
                    "sync_request signature verification failed for '{}': {}",
                    self.requester_id, e
                ))
            })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncResponse {
    pub responder_id: String,
    pub records: Vec<SyncRecord>,
    pub current_epoch: u64,
    pub has_more: bool,
    /// Ed25519 public key of the responder (zeroed on legacy unsigned servers).
    #[serde(default)]
    pub responder_pubkey: [u8; 32],
    /// Ed25519 signature over the canonical response payload (including the record Merkle root).
    #[serde(default)]
    pub signature: Vec<u8>,
    /// Echo of the request handshake nonce.
    #[serde(default)]
    pub nonce: [u8; 32],
    /// Echo of the request session id.
    #[serde(default)]
    pub session_id: String,
    /// Responder wall-clock time (ms) at signing; bounded freshness window.
    #[serde(default)]
    pub timestamp_ms: u64,
}

impl SyncResponse {
    /// Canonical payload covered by the responder's Ed25519 signature.
    pub fn signing_payload(&self) -> Vec<u8> {
        let record_root = SyncBundle::compute_merkle_root(&self.records);
        format!(
            "WHITEMAGIC:MESH_SYNC_RESP:v2|responder:{}|epoch:{}|has_more:{}|records:{}|root:{}|nonce:{}|session:{}|ts:{}",
            self.responder_id,
            self.current_epoch,
            self.has_more,
            self.records.len(),
            hex_encode_key(&record_root),
            hex_encode_key(&self.nonce),
            self.session_id,
            self.timestamp_ms
        )
        .into_bytes()
    }

    /// Sign this response in place with the responder's sovereign mesh key.
    pub fn sign_with(&mut self, signing_key: &SigningKey) {
        self.responder_pubkey = signing_key.verifying_key().to_bytes();
        let payload = self.signing_payload();
        self.signature = signing_key.sign(&payload).to_bytes().to_vec();
    }

    /// Verify signature, peer identity, nonce/session binding, and freshness.
    pub fn verify(
        &self,
        expected_pubkey: &[u8; 32],
        expected_nonce: &[u8; 32],
        expected_session: &str,
        now_ms: u64,
    ) -> Result<(), MeshError> {
        if &self.responder_pubkey != expected_pubkey {
            return Err(MeshError::UntrustedSigner(format!(
                "sync_response responder key {} does not match handshake key {}",
                hex_encode_key(&self.responder_pubkey),
                hex_encode_key(expected_pubkey)
            )));
        }
        if &self.nonce != expected_nonce {
            return Err(MeshError::Unauthorized(
                "sync_response nonce does not match the handshake challenge".to_string(),
            ));
        }
        if self.session_id != expected_session {
            return Err(MeshError::Unauthorized(
                "sync_response session id does not match the request".to_string(),
            ));
        }
        if self.timestamp_ms == 0 || now_ms.abs_diff(self.timestamp_ms) > MESH_RESPONSE_MAX_AGE_MS {
            return Err(MeshError::Unauthorized(format!(
                "stale sync_response (timestamp {} vs now {}; window {} ms)",
                self.timestamp_ms, now_ms, MESH_RESPONSE_MAX_AGE_MS
            )));
        }
        if self.signature.is_empty() {
            return Err(MeshError::Unauthorized(
                "sync_response carries no signature".to_string(),
            ));
        }
        let sig_bytes: [u8; 64] = self.signature.as_slice().try_into().map_err(|_| {
            MeshError::Unauthorized("sync_response signature length != 64 bytes".to_string())
        })?;
        let verifying_key = VerifyingKey::from_bytes(&self.responder_pubkey)
            .map_err(|e| MeshError::Unauthorized(format!("invalid responder key: {e}")))?;
        verifying_key
            .verify(&self.signing_payload(), &Signature::from_bytes(&sig_bytes))
            .map_err(|e| {
                MeshError::Unauthorized(format!("sync_response signature verification failed: {e}"))
            })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneBundle {
    pub sender_id: String,
    pub skeleton: ActionSkeleton,
    pub signature: Vec<u8>,
}

impl GeneBundle {
    pub fn sign(sender_id: &str, skeleton: &ActionSkeleton, signing_key: &SigningKey) -> Self {
        let skel_bytes = serde_json::to_vec(skeleton).unwrap_or_default();
        let sig = signing_key.sign(&skel_bytes);
        Self {
            sender_id: sender_id.to_string(),
            skeleton: skeleton.clone(),
            signature: sig.to_bytes().to_vec(),
        }
    }

    pub fn verify_signature(&self, public_key: &[u8; 32]) -> Result<(), MeshError> {
        let verifying_key = VerifyingKey::from_bytes(public_key)
            .map_err(|e| MeshError::InvalidSignature(e.to_string()))?;
        let sig_bytes: [u8; 64] = self.signature.as_slice().try_into().map_err(|_| {
            MeshError::InvalidSignature("Signature length must be 64 bytes".to_string())
        })?;
        let sig = Signature::from_bytes(&sig_bytes);
        let skel_bytes = serde_json::to_vec(&self.skeleton)
            .map_err(|e| MeshError::FramingError(e.to_string()))?;
        verifying_key
            .verify(&skel_bytes, &sig)
            .map_err(|e| MeshError::InvalidSignature(e.to_string()))
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneSyncRequest {
    pub requester_id: String,
    pub since_version: u32,
    /// Ed25519 public key of the requester (zeroed on legacy unsigned clients).
    #[serde(default)]
    pub requester_pubkey: [u8; 32],
    /// Ed25519 signature over the canonical request payload.
    #[serde(default)]
    pub signature: Vec<u8>,
    /// Handshake challenge nonce this request is bound to.
    #[serde(default)]
    pub nonce: [u8; 32],
    /// Per-request session id (replay cache key).
    #[serde(default)]
    pub session_id: String,
}

impl GeneSyncRequest {
    pub fn signing_payload(&self) -> Vec<u8> {
        format!(
            "WHITEMAGIC:MESH_GENE_SYNC_REQ:v1|requester:{}|pubkey:{}|since_version:{}|nonce:{}|session:{}",
            self.requester_id,
            hex_encode_key(&self.requester_pubkey),
            self.since_version,
            hex_encode_key(&self.nonce),
            self.session_id
        )
        .into_bytes()
    }

    /// Build a signed gene sync request bound to an explicit handshake nonce/session.
    pub fn signed_with(
        requester_id: &str,
        since_version: u32,
        nonce: [u8; 32],
        session_id: &str,
        signing_key: &SigningKey,
    ) -> Self {
        let mut req = Self {
            requester_id: requester_id.to_string(),
            since_version,
            requester_pubkey: signing_key.verifying_key().to_bytes(),
            signature: Vec::new(),
            nonce,
            session_id: session_id.to_string(),
        };
        let payload = req.signing_payload();
        req.signature = signing_key.sign(&payload).to_bytes().to_vec();
        req
    }

    /// Verify the embedded signed peer identity. Unsigned or invalid requests fail closed.
    pub fn verify(&self) -> Result<(), MeshError> {
        if self.nonce == [0u8; 32] {
            return Err(MeshError::Unauthorized(format!(
                "gene_sync_request from '{}' carries no handshake nonce",
                self.requester_id
            )));
        }
        if self.session_id.is_empty() {
            return Err(MeshError::Unauthorized(format!(
                "gene_sync_request from '{}' carries no session id",
                self.requester_id
            )));
        }
        if self.signature.is_empty() {
            return Err(MeshError::Unauthorized(format!(
                "gene_sync_request from '{}' carries no signature",
                self.requester_id
            )));
        }
        let sig_bytes: [u8; 64] = self.signature.as_slice().try_into().map_err(|_| {
            MeshError::Unauthorized("gene_sync_request signature length != 64 bytes".to_string())
        })?;
        let verifying_key = VerifyingKey::from_bytes(&self.requester_pubkey)
            .map_err(|e| MeshError::Unauthorized(format!("invalid requester key: {e}")))?;
        verifying_key
            .verify(&self.signing_payload(), &Signature::from_bytes(&sig_bytes))
            .map_err(|e| {
                MeshError::Unauthorized(format!(
                    "gene_sync_request signature verification failed for '{}': {}",
                    self.requester_id, e
                ))
            })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneSyncResponse {
    pub responder_id: String,
    pub genes: Vec<GeneBundle>,
    /// Ed25519 public key of the responder (zeroed on legacy unsigned servers).
    #[serde(default)]
    pub responder_pubkey: [u8; 32],
    /// Ed25519 signature over the canonical response payload (including the gene digest).
    #[serde(default)]
    pub signature: Vec<u8>,
    /// Echo of the request handshake nonce.
    #[serde(default)]
    pub nonce: [u8; 32],
    /// Echo of the request session id.
    #[serde(default)]
    pub session_id: String,
    /// Responder wall-clock time (ms) at signing; bounded freshness window.
    #[serde(default)]
    pub timestamp_ms: u64,
}

fn gene_bundle_digest(genes: &[GeneBundle]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update((genes.len() as u64).to_le_bytes());
    for gene in genes {
        hasher.update(&gene.signature);
        hasher.update(serde_json::to_vec(&gene.skeleton).unwrap_or_default());
    }
    hasher.finalize().into()
}

impl GeneSyncResponse {
    pub fn signing_payload(&self) -> Vec<u8> {
        format!(
            "WHITEMAGIC:MESH_GENE_SYNC_RESP:v1|responder:{}|genes:{}|digest:{}|nonce:{}|session:{}|ts:{}",
            self.responder_id,
            self.genes.len(),
            hex_encode_key(&gene_bundle_digest(&self.genes)),
            hex_encode_key(&self.nonce),
            self.session_id,
            self.timestamp_ms
        )
        .into_bytes()
    }

    /// Sign this response in place with the responder's sovereign mesh key.
    pub fn sign_with(&mut self, signing_key: &SigningKey) {
        self.responder_pubkey = signing_key.verifying_key().to_bytes();
        let payload = self.signing_payload();
        self.signature = signing_key.sign(&payload).to_bytes().to_vec();
    }

    /// Verify signature, peer identity, nonce/session binding, and freshness.
    pub fn verify(
        &self,
        expected_pubkey: &[u8; 32],
        expected_nonce: &[u8; 32],
        expected_session: &str,
        now_ms: u64,
    ) -> Result<(), MeshError> {
        if &self.responder_pubkey != expected_pubkey {
            return Err(MeshError::UntrustedSigner(format!(
                "gene_sync_response responder key {} does not match handshake key {}",
                hex_encode_key(&self.responder_pubkey),
                hex_encode_key(expected_pubkey)
            )));
        }
        if &self.nonce != expected_nonce {
            return Err(MeshError::Unauthorized(
                "gene_sync_response nonce does not match the handshake challenge".to_string(),
            ));
        }
        if self.session_id != expected_session {
            return Err(MeshError::Unauthorized(
                "gene_sync_response session id does not match the request".to_string(),
            ));
        }
        if self.timestamp_ms == 0 || now_ms.abs_diff(self.timestamp_ms) > MESH_RESPONSE_MAX_AGE_MS {
            return Err(MeshError::Unauthorized(format!(
                "stale gene_sync_response (timestamp {} vs now {}; window {} ms)",
                self.timestamp_ms, now_ms, MESH_RESPONSE_MAX_AGE_MS
            )));
        }
        if self.signature.is_empty() {
            return Err(MeshError::Unauthorized(
                "gene_sync_response carries no signature".to_string(),
            ));
        }
        let sig_bytes: [u8; 64] = self.signature.as_slice().try_into().map_err(|_| {
            MeshError::Unauthorized("gene_sync_response signature length != 64 bytes".to_string())
        })?;
        let verifying_key = VerifyingKey::from_bytes(&self.responder_pubkey)
            .map_err(|e| MeshError::Unauthorized(format!("invalid responder key: {e}")))?;
        verifying_key
            .verify(&self.signing_payload(), &Signature::from_bytes(&sig_bytes))
            .map_err(|e| {
                MeshError::Unauthorized(format!(
                    "gene_sync_response signature verification failed: {e}"
                ))
            })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneSyncStats {
    pub total_received: usize,
    pub genes_promoted: usize,
    pub genes_rejected: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "action", content = "payload")]
pub enum MeshEnvelope {
    #[serde(rename = "mesh.ping")]
    Ping { timestamp: u64 },
    #[serde(rename = "mesh.pong")]
    Pong {
        ping_timestamp: u64,
        server_timestamp: u64,
    },
    #[serde(rename = "mesh.handshake")]
    Handshake(MeshHandshake),
    #[serde(rename = "mesh.handshake_ack")]
    HandshakeAck(MeshHandshake),
    #[serde(rename = "mesh.sync_request")]
    SyncReq(SyncRequest),
    #[serde(rename = "mesh.sync_response")]
    SyncResp(SyncResponse),
    #[serde(rename = "mesh.gene_sync_request")]
    GeneSyncReq(GeneSyncRequest),
    #[serde(rename = "mesh.gene_sync_response")]
    GeneSyncResp(GeneSyncResponse),
    #[serde(rename = "mesh.error")]
    Error(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncStats {
    pub total_received: usize,
    pub records_migrated: usize,
    pub duplicates_skipped: usize,
    pub quarantined: usize,
    pub previous_epoch: u64,
    pub new_epoch: u64,
    pub roundtrip_ms: f64,
}

// ============================================================================
// 3. Offline Sneakernet Sync Bundles (.wmpack)
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BundleHeader {
    pub magic: String,
    pub timestamp: u64,
    pub author_id: String,
    pub author_pubkey: [u8; 32],
    pub from_epoch: u64,
    pub to_epoch: u64,
    pub record_count: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncBundle {
    pub header: BundleHeader,
    pub records: Vec<SyncRecord>,
    #[serde(default)]
    pub receipts: Vec<ContinuityReceipt05>,
    #[serde(default)]
    pub negative_signatures: Vec<String>,
    pub merkle_root: [u8; 32],
    pub signature: Vec<u8>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BundleImportReceipt {
    pub source_bundle: String,
    pub author_id: String,
    pub total_records: usize,
    pub migrated_count: usize,
    pub duplicate_skipped: usize,
    pub target_epoch: u64,
    pub timestamp: String,
    pub receipt_digest: String,
    #[serde(default)]
    pub receipts_imported: usize,
    #[serde(default)]
    pub negative_signatures_imported: usize,
}

impl SyncBundle {
    /// Compute Merkle root of record SHA-256 digests.
    pub fn compute_merkle_root(records: &[SyncRecord]) -> [u8; 32] {
        Self::compute_composite_merkle_root(records, &[], &[])
    }

    /// Compute composite Merkle root over records, continuity receipts, and negative knowledge signatures.
    pub fn compute_composite_merkle_root(
        records: &[SyncRecord],
        receipts: &[ContinuityReceipt05],
        negative_signatures: &[String],
    ) -> [u8; 32] {
        if receipts.is_empty() && negative_signatures.is_empty() {
            if records.is_empty() {
                return [0u8; 32];
            }

            let mut current_hashes: Vec<[u8; 32]> = records
                .iter()
                .map(|r| {
                    let mut hasher = Sha256::new();
                    hasher.update(r.content.as_bytes());
                    hasher.update(r.source.as_bytes());
                    hasher.update(r.kind.as_bytes());
                    hasher.finalize().into()
                })
                .collect();

            while current_hashes.len() > 1 {
                let mut next_level = Vec::with_capacity(current_hashes.len().div_ceil(2));
                for chunk in current_hashes.chunks(2) {
                    let mut hasher = Sha256::new();
                    hasher.update(chunk[0]);
                    if chunk.len() > 1 {
                        hasher.update(chunk[1]);
                    } else {
                        hasher.update(chunk[0]);
                    }
                    next_level.push(hasher.finalize().into());
                }
                current_hashes = next_level;
            }

            return current_hashes[0];
        }

        let records_root = Self::compute_merkle_root(records);
        let mut hasher = Sha256::new();
        hasher.update(records_root);
        hasher.update((receipts.len() as u64).to_le_bytes());
        for r in receipts {
            hasher.update(r.receipt_id.as_bytes());
            hasher.update(r.workspace_claim_digest.as_bytes());
            if let Some(ref s) = r.signature {
                hasher.update(s);
            }
        }
        hasher.update((negative_signatures.len() as u64).to_le_bytes());
        for s in negative_signatures {
            hasher.update(s.as_bytes());
        }
        hasher.finalize().into()
    }

    /// Sign bundle with Ed25519 signing key.
    pub fn sign_with(&mut self, key: &SigningKey) {
        let mut hasher = Sha256::new();
        hasher.update(self.header.magic.as_bytes());
        hasher.update(self.header.timestamp.to_le_bytes());
        hasher.update(self.header.author_id.as_bytes());
        hasher.update(self.header.author_pubkey);
        hasher.update(self.header.from_epoch.to_le_bytes());
        hasher.update(self.header.to_epoch.to_le_bytes());
        hasher.update(self.header.record_count.to_le_bytes());
        hasher.update(self.merkle_root);
        let digest = hasher.finalize();

        let sig: Signature = key.sign(&digest);
        self.signature = sig.to_bytes().to_vec();
    }

    /// Verify signature and internal Merkle root integrity.
    pub fn verify(&self, expected_pubkey: Option<&[u8; 32]>) -> Result<(), MeshError> {
        if self.header.magic != WMPACK_MAGIC {
            return Err(MeshError::BundleCorrupted(format!(
                "Invalid magic: expected {}, got {}",
                WMPACK_MAGIC, self.header.magic
            )));
        }

        if let Some(expected) = expected_pubkey {
            if &self.header.author_pubkey != expected {
                return Err(MeshError::UntrustedSigner(format!(
                    "Author pubkey {:?} does not match expected {:?}",
                    self.header.author_pubkey, expected
                )));
            }
        }

        // Verify Merkle root matches records, receipts, and negative knowledge
        let computed_root = Self::compute_composite_merkle_root(
            &self.records,
            &self.receipts,
            &self.negative_signatures,
        );
        if computed_root != self.merkle_root {
            return Err(MeshError::BundleCorrupted(
                "Merkle root mismatch: bundle payload tampered".to_string(),
            ));
        }

        // Verify signature
        let verifying_key = VerifyingKey::from_bytes(&self.header.author_pubkey)
            .map_err(|e| MeshError::InvalidSignature(e.to_string()))?;

        let sig_bytes: [u8; 64] = self
            .signature
            .as_slice()
            .try_into()
            .map_err(|_| MeshError::InvalidSignature("Signature length != 64".to_string()))?;
        let sig = Signature::from_bytes(&sig_bytes);

        let mut hasher = Sha256::new();
        hasher.update(self.header.magic.as_bytes());
        hasher.update(self.header.timestamp.to_le_bytes());
        hasher.update(self.header.author_id.as_bytes());
        hasher.update(self.header.author_pubkey);
        hasher.update(self.header.from_epoch.to_le_bytes());
        hasher.update(self.header.to_epoch.to_le_bytes());
        hasher.update(self.header.record_count.to_le_bytes());
        hasher.update(self.merkle_root);
        let digest = hasher.finalize();

        verifying_key
            .verify(&digest, &sig)
            .map_err(|e| MeshError::InvalidSignature(e.to_string()))?;

        Ok(())
    }

    /// Export records from Substrate starting from `since_epoch`.
    pub fn export(
        substrate: &Substrate,
        since_epoch: u64,
        author_id: &str,
        signing_key: &SigningKey,
    ) -> Result<Self, MeshError> {
        let store = substrate.store();
        let current_epoch = store.epoch()?;
        let all_records = store.iter_records()?;

        let filtered: Vec<SyncRecord> = all_records
            .iter()
            .filter(|r| r.id() >= since_epoch)
            .map(SyncRecord::from_evidence_record)
            .collect();

        let ledger_path = substrate.store().path().join("mandala_ledger.jsonl");
        let mut receipts = Vec::new();
        if ledger_path.exists() {
            if let Ok(content) = std::fs::read_to_string(&ledger_path) {
                for line in content.lines() {
                    if let Ok(rcp) = serde_json::from_str::<ContinuityReceipt05>(line) {
                        receipts.push(rcp);
                    }
                }
            }
        }

        let neg_path = substrate.store().path().join("negative_knowledge.jsonl");
        let mut negative_signatures = Vec::new();
        if neg_path.exists() {
            if let Ok(content) = std::fs::read_to_string(&neg_path) {
                for line in content.lines() {
                    if let Ok(val) = serde_json::from_str::<serde_json::Value>(line) {
                        if let Some(sig) = val.get("signature").and_then(|s| s.as_str()) {
                            negative_signatures.push(sig.to_string());
                        }
                    }
                }
            }
        }

        let merkle_root =
            Self::compute_composite_merkle_root(&filtered, &receipts, &negative_signatures);
        let record_count = filtered.len() as u64;

        let now_sec = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let header = BundleHeader {
            magic: WMPACK_MAGIC.to_string(),
            timestamp: now_sec,
            author_id: author_id.to_string(),
            author_pubkey: signing_key.verifying_key().to_bytes(),
            from_epoch: since_epoch,
            to_epoch: current_epoch,
            record_count,
        };

        let mut bundle = Self {
            header,
            records: filtered,
            receipts,
            negative_signatures,
            merkle_root,
            signature: Vec::new(),
        };

        bundle.sign_with(signing_key);
        Ok(bundle)
    }

    /// Save bundle to file on disk.
    pub fn save_to_file(&self, path: &Path) -> Result<(), MeshError> {
        let bytes =
            serde_json::to_vec_pretty(self).map_err(|e| MeshError::IoError(e.to_string()))?;
        let mut file = File::create(path)?;
        file.write_all(&bytes)?;
        file.sync_data()?;
        Ok(())
    }

    /// Load bundle from file on disk.
    pub fn load_from_file(path: &Path) -> Result<Self, MeshError> {
        let mut file = File::open(path)?;
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes)?;
        let bundle: Self = serde_json::from_slice(&bytes)
            .map_err(|e| MeshError::BundleCorrupted(e.to_string()))?;
        Ok(bundle)
    }

    /// Import and deduplicate bundle records into local Substrate.
    pub fn import_into_substrate(
        &self,
        substrate: &mut Substrate,
        expected_signer: Option<&[u8; 32]>,
        bundle_path_str: &str,
    ) -> Result<BundleImportReceipt, MeshError> {
        self.verify(expected_signer)?;

        // Per-record content-addressed digests: refuse unverifiable records
        // loudly before any mutation can occur.
        for record in &self.records {
            record.verify_integrity()?;
        }

        // Continuity receipts must carry a valid signature from the bundle
        // author before they are appended to the local ledger. Legacy unsigned
        // receipts are refused (prefer refuse over skipped-verification).
        let author_verifying_key = VerifyingKey::from_bytes(&self.header.author_pubkey)
            .map_err(|e| MeshError::InvalidSignature(format!("invalid bundle author key: {e}")))?;
        for receipt in &self.receipts {
            if receipt.signature.is_none() {
                return Err(MeshError::BundleCorrupted(format!(
                    "receipt '{}' carries no signature; refusing unverified import",
                    receipt.receipt_id
                )));
            }
            receipt.verify(&author_verifying_key).map_err(|e| {
                MeshError::InvalidSignature(format!(
                    "receipt '{}' signature verification failed: {e}",
                    receipt.receipt_id
                ))
            })?;
        }
        for signature in &self.negative_signatures {
            if signature.trim().is_empty() {
                return Err(MeshError::BundleCorrupted(
                    "negative knowledge entry carries an empty signature; refusing import"
                        .to_string(),
                ));
            }
        }

        let old_noise = substrate.noise_enabled();
        substrate.set_noise_enabled(false);
        let old_budget = substrate.budget();
        substrate.set_budget(0);

        let mut migrated_count = 0;
        let mut duplicate_skipped = 0;

        let items: Vec<RememberItem> = self.records.iter().map(|r| r.to_remember_item()).collect();

        // Chunked ingestion to keep transaction bounds optimal
        for chunk in items.chunks(100) {
            let mut new_items = Vec::new();
            for item in chunk {
                if substrate.contains_exact(&item.content, &item.source, item.kind) {
                    duplicate_skipped += 1;
                } else {
                    new_items.push(item.clone());
                }
            }

            if !new_items.is_empty() {
                let results = substrate.remember_batch(&new_items);
                for res in results {
                    match res {
                        Ok(_) => migrated_count += 1,
                        Err(e)
                            if e == "duplicate_exact"
                                || e.contains("RefusedByKernel: duplicate record") =>
                        {
                            duplicate_skipped += 1;
                        }
                        Err(e) => return Err(MeshError::StoreError(e)),
                    }
                }
            }
        }

        substrate.set_noise_enabled(old_noise);
        substrate.set_budget(old_budget);

        let target_epoch = substrate.store().epoch().unwrap_or(0);
        let timestamp = chrono::Utc::now().to_rfc3339();

        let receipt_digest = {
            let mut hasher = Sha256::new();
            hasher.update(bundle_path_str.as_bytes());
            hasher.update(self.header.author_id.as_bytes());
            hasher.update((migrated_count as u64).to_le_bytes());
            hasher.update((duplicate_skipped as u64).to_le_bytes());
            hasher.update(target_epoch.to_le_bytes());
            format!("{:x}", hasher.finalize())
        };

        let mut receipts_imported = 0;
        let ledger_path = substrate.store().path().join("mandala_ledger.jsonl");
        for rcp in &self.receipts {
            if let Ok(json) = serde_json::to_string(rcp) {
                if let Ok(mut f) = OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(&ledger_path)
                {
                    let _ = writeln!(f, "{json}");
                    receipts_imported += 1;
                }
            }
        }

        let mut negative_signatures_imported = 0;
        let neg_path = substrate.store().path().join("negative_knowledge.jsonl");
        for sig in &self.negative_signatures {
            let record = serde_json::json!({ "signature": sig, "timestamp": timestamp });
            if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(&neg_path) {
                let _ = writeln!(f, "{record}");
                negative_signatures_imported += 1;
            }
        }

        Ok(BundleImportReceipt {
            source_bundle: bundle_path_str.to_string(),
            author_id: self.header.author_id.clone(),
            total_records: self.records.len(),
            migrated_count,
            duplicate_skipped,
            target_epoch,
            timestamp,
            receipt_digest,
            receipts_imported,
            negative_signatures_imported,
        })
    }
}

// ============================================================================
// 4. Mesh Client & Server Engine
// ============================================================================

/// Resolve or generate a persistent Ed25519 node identity key for the given store directory.
pub fn resolve_or_create_mesh_key(store_dir: &Path) -> io::Result<(SigningKey, [u8; 32])> {
    std::fs::create_dir_all(store_dir)?;
    let key_file = store_dir.join("mesh_node_key.bin");
    if key_file.exists() {
        let mut f = File::open(&key_file)?;
        let mut bytes = [0u8; 32];
        f.read_exact(&mut bytes)?;
        let signing = SigningKey::from_bytes(&bytes);
        let pubkey = signing.verifying_key().to_bytes();
        Ok((signing, pubkey))
    } else {
        let mut bytes = [0u8; 32];
        getrandom::fill(&mut bytes).map_err(|e| io::Error::other(e.to_string()))?;
        let signing = SigningKey::from_bytes(&bytes);
        let pubkey = signing.verifying_key().to_bytes();

        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            let mut f = OpenOptions::new()
                .write(true)
                .create_new(true)
                .mode(0o600)
                .open(&key_file)?;
            f.write_all(&bytes)?;
            f.sync_data()?;
        }
        #[cfg(not(unix))]
        {
            let mut f = File::create(&key_file)?;
            f.write_all(&bytes)?;
            f.sync_data()?;
        }
        Ok((signing, pubkey))
    }
}

fn mesh_allow_remote() -> bool {
    std::env::var("WM_MESH_ALLOW_REMOTE")
        .map(|v| v == "1")
        .unwrap_or(false)
}

/// Validate a mesh bind host against the loopback-default policy.
///
/// Non-loopback binds are refused unless `WM_MESH_ALLOW_REMOTE=1` is set.
pub fn validate_mesh_bind(bind_host: &str) -> Result<(), MeshError> {
    validate_mesh_bind_with(mesh_allow_remote(), bind_host)
}

/// Resolve a bind host exactly once to a `SocketAddr` (fixing IPv6 formatting
/// like `::1` and removing the resolve-then-rebind TOCTOU window).
pub fn resolve_mesh_bind(bind_host: &str, port: u16) -> Result<SocketAddr, MeshError> {
    let host = bind_host.trim();
    if host.is_empty() {
        return Err(MeshError::Unauthorized(
            "empty mesh bind host; refusing to bind (set WM_MESH_ALLOW_REMOTE=1 to permit non-loopback binds)"
                .to_string(),
        ));
    }
    let bare = host
        .strip_prefix('[')
        .and_then(|inner| inner.strip_suffix(']'))
        .unwrap_or(host);
    if let Ok(ip) = bare.parse::<IpAddr>() {
        return Ok(SocketAddr::new(ip, port));
    }
    if host.eq_ignore_ascii_case("localhost") {
        return Ok(SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), port));
    }
    (host, port)
        .to_socket_addrs()
        .map_err(|e| MeshError::IoError(format!("cannot resolve mesh bind host '{host}': {e}")))?
        .next()
        .ok_or_else(|| MeshError::IoError(format!("cannot resolve mesh bind host '{host}'")))
}

fn validate_resolved_bind(allow_remote: bool, addr: SocketAddr) -> Result<(), MeshError> {
    if addr.ip().is_loopback() || allow_remote {
        return Ok(());
    }
    Err(MeshError::Unauthorized(format!(
        "refusing non-loopback mesh bind {addr}: set WM_MESH_ALLOW_REMOTE=1 to permit remote mesh listeners"
    )))
}

fn validate_mesh_bind_with(allow_remote: bool, bind_host: &str) -> Result<(), MeshError> {
    let addr = resolve_mesh_bind(bind_host, 0)?;
    validate_resolved_bind(allow_remote, addr)
}

const DEFAULT_MESH_MAX_CONNS: usize = 16;

fn parse_mesh_max_connections(raw: Option<&str>) -> usize {
    raw.and_then(|v| v.trim().parse::<usize>().ok())
        .filter(|&v| v > 0)
        .unwrap_or(DEFAULT_MESH_MAX_CONNS)
}

fn mesh_max_connections() -> usize {
    parse_mesh_max_connections(std::env::var("WM_MESH_MAX_CONNS").ok().as_deref())
}

/// Decrements the active-connection counter when a connection thread ends.
struct ConnSlot(Arc<AtomicUsize>);

impl Drop for ConnSlot {
    fn drop(&mut self) {
        self.0.fetch_sub(1, Ordering::SeqCst);
    }
}

pub struct MeshServer {
    pub node_id: String,
    pub signing_key: Arc<SigningKey>,
    pub substrate_path: std::path::PathBuf,
    pub listener: Option<TcpListener>,
    pub bound_addr: Option<SocketAddr>,
    pub is_running: Arc<Mutex<bool>>,
}

impl MeshServer {
    pub fn new(node_id: &str, signing_key: SigningKey, substrate_path: &Path) -> Self {
        Self {
            node_id: node_id.to_string(),
            signing_key: Arc::new(signing_key),
            substrate_path: substrate_path.to_path_buf(),
            listener: None,
            bound_addr: None,
            is_running: Arc::new(Mutex::new(false)),
        }
    }

    /// Start listening on specified port.
    ///
    /// Fails closed before binding when `bind_host` is non-loopback and
    /// `WM_MESH_ALLOW_REMOTE=1` is not set. The bind host is resolved exactly
    /// once and the actually-bound address is re-checked against the policy.
    pub fn listen(&mut self, port: u16, bind_host: &str) -> io::Result<SocketAddr> {
        self.listen_with_peer_allowlist(port, bind_host, mesh_peer_allowlist())
    }

    fn listen_with_peer_allowlist(
        &mut self,
        port: u16,
        bind_host: &str,
        peer_allowlist: Vec<String>,
    ) -> io::Result<SocketAddr> {
        let allow_remote = mesh_allow_remote();
        let requested = resolve_mesh_bind(bind_host, port)
            .map_err(|e| io::Error::new(io::ErrorKind::PermissionDenied, e.to_string()))?;
        validate_resolved_bind(allow_remote, requested)
            .map_err(|e| io::Error::new(io::ErrorKind::PermissionDenied, e.to_string()))?;

        let listener = TcpListener::bind(requested)?;
        let addr = listener.local_addr()?;
        // Re-check the socket that actually exists (guards against resolver
        // rebinding / interface changes between resolve and bind).
        validate_resolved_bind(allow_remote, addr)
            .map_err(|e| io::Error::new(io::ErrorKind::PermissionDenied, e.to_string()))?;
        listener.set_nonblocking(true)?;

        self.bound_addr = Some(addr);
        self.listener = Some(listener);
        *self.is_running.lock().unwrap_or_else(|e| e.into_inner()) = true;

        let running_flag = Arc::clone(&self.is_running);
        let listener_clone = self.listener.as_ref().unwrap().try_clone()?;
        let node_id = self.node_id.clone();
        let signing_key = Arc::clone(&self.signing_key);
        let sub_path = self.substrate_path.clone();
        let max_conns = mesh_max_connections();
        let active = Arc::new(AtomicUsize::new(0));
        let peer_allowlist = Arc::new(peer_allowlist);
        let replay_cache = Arc::new(ReplayCache::default());

        std::thread::spawn(move || {
            while *running_flag.lock().unwrap_or_else(|e| e.into_inner()) {
                match listener_clone.accept() {
                    Ok((mut stream, client_addr)) => {
                        if active.load(Ordering::SeqCst) >= max_conns {
                            let _ = stream.set_nonblocking(false);
                            let err = MeshEnvelope::Error(format!(
                                "mesh connection limit reached ({max_conns}); tune WM_MESH_MAX_CONNS"
                            ));
                            if let Ok(bytes) = serde_json::to_vec(&err) {
                                let _ = PhysicalFrameCodec::write_frame(&mut stream, &bytes);
                            }
                            continue;
                        }
                        active.fetch_add(1, Ordering::SeqCst);
                        let conn_slot = ConnSlot(Arc::clone(&active));
                        let node_id_inner = node_id.clone();
                        let sub_path_inner = sub_path.clone();
                        let signing_key_inner = Arc::clone(&signing_key);
                        let peer_allowlist_inner = Arc::clone(&peer_allowlist);
                        let replay_cache_inner = Arc::clone(&replay_cache);

                        std::thread::spawn(move || {
                            let _conn_slot = conn_slot;
                            let mut handshake_nonce: Option<[u8; 32]> = None;
                            let _ = stream.set_nonblocking(false);
                            let _ = stream.set_read_timeout(Some(DEFAULT_FRAME_ASSEMBLY_TIMEOUT));
                            let _ = stream.set_write_timeout(Some(DEFAULT_FRAME_ASSEMBLY_TIMEOUT));

                            loop {
                                // Per-frame assembly budget. The old code created
                                // `start` once per connection, so the budget was
                                // cumulative: a connection used for longer than
                                // DEFAULT_FRAME_ASSEMBLY_TIMEOUT was dropped on its
                                // next request (client-side "Unexpected EOF" — the
                                // 2026-09-27 macOS port report class).
                                let start = Instant::now();
                                let Ok(bytes) = PhysicalFrameCodec::read_frame(
                                    &mut stream,
                                    start,
                                    DEFAULT_FRAME_ASSEMBLY_TIMEOUT,
                                ) else {
                                    break;
                                };
                                let envelope: Result<MeshEnvelope, _> =
                                    serde_json::from_slice(&bytes);
                                match envelope {
                                    Ok(MeshEnvelope::Ping { timestamp }) => {
                                        let now = SystemTime::now()
                                            .duration_since(UNIX_EPOCH)
                                            .unwrap_or_default()
                                            .as_millis()
                                            as u64;
                                        let resp = MeshEnvelope::Pong {
                                            ping_timestamp: timestamp,
                                            server_timestamp: now,
                                        };
                                        if let Ok(resp_bytes) = serde_json::to_vec(&resp) {
                                            let _ = PhysicalFrameCodec::write_frame(
                                                &mut stream,
                                                &resp_bytes,
                                            );
                                        }
                                    }
                                    Ok(MeshEnvelope::Handshake(client_hs)) => {
                                        // Legacy/unsigned handshakes carry no challenge nonce
                                        // and are refused; every sync is nonce-bound.
                                        if client_hs.nonce == [0u8; 32]
                                            || client_hs.public_key == [0u8; 32]
                                        {
                                            let err = MeshEnvelope::Error(
                                                "handshake refused: missing client nonce or identity (unsigned/legacy handshake)"
                                                    .to_string(),
                                            );
                                            if let Ok(resp_bytes) = serde_json::to_vec(&err) {
                                                let _ = PhysicalFrameCodec::write_frame(
                                                    &mut stream,
                                                    &resp_bytes,
                                                );
                                            }
                                            continue;
                                        }
                                        handshake_nonce = Some(client_hs.nonce);

                                        // Open read-only view of store for stats
                                        let (epoch, count, head_hash) =
                                            match Substrate::open_readonly(
                                                &sub_path_inner,
                                                None,
                                                crate::constitution::default_view(),
                                            ) {
                                                Ok(sub) => {
                                                    let ep = sub.store().epoch().unwrap_or(0);
                                                    let cnt =
                                                        sub.store().record_count().unwrap_or(0)
                                                            as u64;
                                                    (ep, cnt, format!("{:x}", ep))
                                                }
                                                Err(_) => (0, 0, "0".to_string()),
                                            };

                                        let mut ack = MeshHandshake {
                                            node_id: node_id_inner.clone(),
                                            public_key: [0u8; 32],
                                            epoch,
                                            record_count: count,
                                            head_hash,
                                            protocol_version: MESH_PROTOCOL_VERSION,
                                            nonce: client_hs.nonce,
                                            signature: Vec::new(),
                                        };
                                        ack.sign_with(&signing_key_inner);
                                        let resp = MeshEnvelope::HandshakeAck(ack);

                                        if let Ok(resp_bytes) = serde_json::to_vec(&resp) {
                                            let _ = PhysicalFrameCodec::write_frame(
                                                &mut stream,
                                                &resp_bytes,
                                            );
                                        }
                                    }
                                    Ok(MeshEnvelope::SyncReq(req)) => {
                                        // Signed peer identity is mandatory: unsigned or
                                        // mis-signed sync requests are refused loudly and
                                        // no records are served.
                                        if let Err(e) = req.verify() {
                                            let err = MeshEnvelope::Error(format!(
                                                "sync_request refused: {e}"
                                            ));
                                            if let Ok(resp_bytes) = serde_json::to_vec(&err) {
                                                let _ = PhysicalFrameCodec::write_frame(
                                                    &mut stream,
                                                    &resp_bytes,
                                                );
                                            }
                                            continue;
                                        }
                                        if let Err(e) = authorize_signed_request(
                                            "sync_request",
                                            handshake_nonce,
                                            req.nonce,
                                            &req.requester_id,
                                            &req.requester_pubkey,
                                            &req.session_id,
                                            client_addr.ip().is_loopback(),
                                            &peer_allowlist_inner,
                                            &replay_cache_inner,
                                        ) {
                                            let err = MeshEnvelope::Error(format!(
                                                "sync_request refused: {e}"
                                            ));
                                            if let Ok(resp_bytes) = serde_json::to_vec(&err) {
                                                let _ = PhysicalFrameCodec::write_frame(
                                                    &mut stream,
                                                    &resp_bytes,
                                                );
                                            }
                                            continue;
                                        }
                                        let (records, current_epoch, has_more) =
                                            match Substrate::open_readonly(
                                                &sub_path_inner,
                                                None,
                                                crate::constitution::default_view(),
                                            ) {
                                                Ok(sub) => {
                                                    let ep = sub.store().epoch().unwrap_or(0);
                                                    match sub.store().iter_records() {
                                                        Ok(all) => {
                                                            let matched: Vec<SyncRecord> = all
                                                            .iter()
                                                            .filter(|r| r.id() >= req.since_epoch)
                                                            .take(req.limit)
                                                            .map(SyncRecord::from_evidence_record)
                                                            .collect();
                                                            let count = matched.len();
                                                            (matched, ep, count == req.limit)
                                                        }
                                                        Err(_) => (Vec::new(), ep, false),
                                                    }
                                                }
                                                Err(_) => (Vec::new(), 0, false),
                                            };

                                        let mut sync_resp = SyncResponse {
                                            responder_id: node_id_inner.clone(),
                                            records,
                                            current_epoch,
                                            has_more,
                                            responder_pubkey: [0u8; 32],
                                            signature: Vec::new(),
                                            nonce: req.nonce,
                                            session_id: req.session_id.clone(),
                                            timestamp_ms: now_millis(),
                                        };
                                        sync_resp.sign_with(&signing_key_inner);
                                        let resp = MeshEnvelope::SyncResp(sync_resp);

                                        if let Ok(resp_bytes) = serde_json::to_vec(&resp) {
                                            let _ = PhysicalFrameCodec::write_frame(
                                                &mut stream,
                                                &resp_bytes,
                                            );
                                        }
                                    }
                                    Ok(MeshEnvelope::GeneSyncReq(req)) => {
                                        if let Err(e) = req.verify() {
                                            let err = MeshEnvelope::Error(format!(
                                                "gene_sync_request refused: {e}"
                                            ));
                                            if let Ok(resp_bytes) = serde_json::to_vec(&err) {
                                                let _ = PhysicalFrameCodec::write_frame(
                                                    &mut stream,
                                                    &resp_bytes,
                                                );
                                            }
                                            continue;
                                        }
                                        if let Err(e) = authorize_signed_request(
                                            "gene_sync_request",
                                            handshake_nonce,
                                            req.nonce,
                                            &req.requester_id,
                                            &req.requester_pubkey,
                                            &req.session_id,
                                            client_addr.ip().is_loopback(),
                                            &peer_allowlist_inner,
                                            &replay_cache_inner,
                                        ) {
                                            let err = MeshEnvelope::Error(format!(
                                                "gene_sync_request refused: {e}"
                                            ));
                                            if let Ok(resp_bytes) = serde_json::to_vec(&err) {
                                                let _ = PhysicalFrameCodec::write_frame(
                                                    &mut stream,
                                                    &resp_bytes,
                                                );
                                            }
                                            continue;
                                        }
                                        let vault_path = sub_path_inner.join("vault.jsonl");
                                        let vault = GeneseedVault::load_or_init(&vault_path);
                                        let genes: Vec<GeneBundle> = vault
                                            .skeletons
                                            .iter()
                                            .filter(|s| {
                                                !s.deprecated && s.version >= req.since_version
                                            })
                                            .map(|skel| {
                                                GeneBundle::sign(
                                                    &node_id_inner,
                                                    skel,
                                                    &signing_key_inner,
                                                )
                                            })
                                            .collect();

                                        let mut gene_resp = GeneSyncResponse {
                                            responder_id: node_id_inner.clone(),
                                            genes,
                                            responder_pubkey: [0u8; 32],
                                            signature: Vec::new(),
                                            nonce: req.nonce,
                                            session_id: req.session_id.clone(),
                                            timestamp_ms: now_millis(),
                                        };
                                        gene_resp.sign_with(&signing_key_inner);
                                        let resp = MeshEnvelope::GeneSyncResp(gene_resp);

                                        if let Ok(resp_bytes) = serde_json::to_vec(&resp) {
                                            let _ = PhysicalFrameCodec::write_frame(
                                                &mut stream,
                                                &resp_bytes,
                                            );
                                        }
                                    }
                                    _ => {
                                        let err = MeshEnvelope::Error(
                                            "Unhandled mesh envelope".to_string(),
                                        );
                                        if let Ok(resp_bytes) = serde_json::to_vec(&err) {
                                            let _ = PhysicalFrameCodec::write_frame(
                                                &mut stream,
                                                &resp_bytes,
                                            );
                                        }
                                    }
                                }
                            }
                        });
                    }
                    Err(ref e) if e.kind() == io::ErrorKind::WouldBlock => {
                        std::thread::sleep(Duration::from_millis(5));
                    }
                    Err(_) => {
                        break;
                    }
                }
            }
        });

        Ok(addr)
    }

    pub fn stop(&mut self) {
        *self.is_running.lock().unwrap_or_else(|e| e.into_inner()) = false;
    }
}

pub struct MeshClient {
    pub stream: TcpStream,
    pub client_node_id: String,
    pub signing_key: SigningKey,
    /// Remote peer address (loopback-only policy anchor).
    pub peer_addr: SocketAddr,
    /// Pinned peer allowlist (`WM_MESH_PEER_ALLOWLIST`); empty = loopback-only.
    peer_allowlist: Vec<String>,
}

impl MeshClient {
    /// Connect to remote mesh server, pinning peers from `WM_MESH_PEER_ALLOWLIST`.
    pub fn connect(
        peer_addr: SocketAddr,
        client_node_id: &str,
        signing_key: SigningKey,
    ) -> Result<Self, MeshError> {
        Self::connect_with_peer_allowlist(
            peer_addr,
            client_node_id,
            signing_key,
            mesh_peer_allowlist(),
        )
    }

    fn connect_with_peer_allowlist(
        peer_addr: SocketAddr,
        client_node_id: &str,
        signing_key: SigningKey,
        peer_allowlist: Vec<String>,
    ) -> Result<Self, MeshError> {
        let stream = TcpStream::connect_timeout(&peer_addr, DEFAULT_CONNECT_TIMEOUT)?;
        stream.set_read_timeout(Some(DEFAULT_FRAME_ASSEMBLY_TIMEOUT))?;
        stream.set_write_timeout(Some(DEFAULT_FRAME_ASSEMBLY_TIMEOUT))?;

        Ok(Self {
            stream,
            client_node_id: client_node_id.to_string(),
            signing_key,
            peer_addr,
            peer_allowlist,
        })
    }

    /// Perform a nonce-challenged handshake and verify the pinned server identity.
    pub fn handshake(
        &mut self,
        local_epoch: u64,
        local_count: u64,
    ) -> Result<MeshHandshake, MeshError> {
        if self.peer_allowlist.is_empty() && !self.peer_addr.ip().is_loopback() {
            return Err(MeshError::Unauthorized(format!(
                "refusing remote mesh sync to {}: WM_MESH_PEER_ALLOWLIST is empty; loopback-only sync",
                self.peer_addr
            )));
        }
        let nonce = random_nonce();
        let hs = MeshHandshake {
            node_id: self.client_node_id.clone(),
            public_key: self.signing_key.verifying_key().to_bytes(),
            epoch: local_epoch,
            record_count: local_count,
            head_hash: format!("{:x}", local_epoch),
            protocol_version: MESH_PROTOCOL_VERSION,
            nonce,
            signature: Vec::new(),
        };

        let req = MeshEnvelope::Handshake(hs);
        let req_bytes =
            serde_json::to_vec(&req).map_err(|e| MeshError::FramingError(e.to_string()))?;
        PhysicalFrameCodec::write_frame(&mut self.stream, &req_bytes)
            .map_err(|e| MeshError::IoError(e.to_string()))?;

        let start = Instant::now();
        let resp_bytes =
            PhysicalFrameCodec::read_frame(&mut self.stream, start, DEFAULT_FRAME_ASSEMBLY_TIMEOUT)
                .map_err(|e| MeshError::IoError(e.to_string()))?;

        let env: MeshEnvelope = serde_json::from_slice(&resp_bytes)
            .map_err(|e| MeshError::FramingError(e.to_string()))?;

        match env {
            MeshEnvelope::HandshakeAck(server_hs) => {
                server_hs.verify(&nonce)?;
                check_peer_allowlist(
                    &self.peer_allowlist,
                    self.peer_addr.ip().is_loopback(),
                    &server_hs.node_id,
                    &server_hs.public_key,
                )?;
                Ok(server_hs)
            }
            MeshEnvelope::Error(e) => Err(MeshError::HandshakeFailed(e)),
            _ => Err(MeshError::HandshakeFailed(
                "Unexpected response during handshake".to_string(),
            )),
        }
    }

    /// Send authenticated ping and measure roundtrip duration.
    pub fn ping(&mut self) -> Result<Duration, MeshError> {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;

        let req = MeshEnvelope::Ping { timestamp: now };
        let req_bytes =
            serde_json::to_vec(&req).map_err(|e| MeshError::FramingError(e.to_string()))?;
        let start = Instant::now();

        PhysicalFrameCodec::write_frame(&mut self.stream, &req_bytes)
            .map_err(|e| MeshError::IoError(e.to_string()))?;

        let resp_bytes =
            PhysicalFrameCodec::read_frame(&mut self.stream, start, DEFAULT_FRAME_ASSEMBLY_TIMEOUT)
                .map_err(|e| MeshError::IoError(e.to_string()))?;

        let env: MeshEnvelope = serde_json::from_slice(&resp_bytes)
            .map_err(|e| MeshError::FramingError(e.to_string()))?;

        match env {
            MeshEnvelope::Pong { ping_timestamp, .. } if ping_timestamp == now => {
                Ok(start.elapsed())
            }
            MeshEnvelope::Error(e) => Err(MeshError::IoError(e)),
            _ => Err(MeshError::FramingError("Invalid pong response".to_string())),
        }
    }

    /// Sync delta from remote peer into local Substrate.
    pub fn sync_delta(
        &mut self,
        substrate: &mut Substrate,
        batch_limit: usize,
    ) -> Result<SyncStats, MeshError> {
        let start_time = Instant::now();
        let prev_epoch = substrate.store().epoch().unwrap_or(0);
        let prev_count = substrate.store().record_count().unwrap_or(0) as u64;

        let hs = self.handshake(prev_epoch, prev_count)?;

        // Signed peer identity bound to the handshake nonce + fresh session id.
        let session_id = random_session_id();
        let req = MeshEnvelope::SyncReq(SyncRequest::signed_with(
            &self.client_node_id,
            prev_epoch,
            batch_limit,
            hs.nonce,
            &session_id,
            &self.signing_key,
        ));

        let req_bytes =
            serde_json::to_vec(&req).map_err(|e| MeshError::FramingError(e.to_string()))?;
        PhysicalFrameCodec::write_frame(&mut self.stream, &req_bytes)
            .map_err(|e| MeshError::IoError(e.to_string()))?;

        let resp_bytes = PhysicalFrameCodec::read_frame(
            &mut self.stream,
            start_time,
            DEFAULT_FRAME_ASSEMBLY_TIMEOUT,
        )
        .map_err(|e| MeshError::IoError(e.to_string()))?;

        let env: MeshEnvelope = serde_json::from_slice(&resp_bytes)
            .map_err(|e| MeshError::FramingError(e.to_string()))?;

        let sync_resp = match env {
            MeshEnvelope::SyncResp(resp) => resp,
            MeshEnvelope::Error(e) => return Err(MeshError::StoreError(e)),
            _ => {
                return Err(MeshError::FramingError(
                    "Expected sync_response".to_string(),
                ));
            }
        };

        // Verify the responder's signed identity (bound to the handshake key),
        // nonce/session binding, freshness, and each record digest before any
        // ingest mutation.
        sync_resp.verify(&hs.public_key, &hs.nonce, &session_id, now_millis())?;
        for record in &sync_resp.records {
            record.verify_integrity()?;
        }

        let old_noise = substrate.noise_enabled();
        substrate.set_noise_enabled(false);
        let old_budget = substrate.budget();
        substrate.set_budget(0);

        let mut migrated_count = 0;
        let mut duplicate_skipped = 0;

        let items: Vec<RememberItem> = sync_resp
            .records
            .iter()
            .map(|r| r.to_remember_item())
            .collect();

        for chunk in items.chunks(100) {
            let mut new_items = Vec::new();
            for item in chunk {
                if substrate.contains_exact(&item.content, &item.source, item.kind) {
                    duplicate_skipped += 1;
                } else {
                    new_items.push(item.clone());
                }
            }

            if !new_items.is_empty() {
                let results = substrate.remember_batch(&new_items);
                for res in results {
                    match res {
                        Ok(_) => migrated_count += 1,
                        Err(e)
                            if e == "duplicate_exact"
                                || e.contains("RefusedByKernel: duplicate record") =>
                        {
                            duplicate_skipped += 1;
                        }
                        Err(e) => return Err(MeshError::StoreError(e)),
                    }
                }
            }
        }

        substrate.set_noise_enabled(old_noise);
        substrate.set_budget(old_budget);

        let new_epoch = substrate.store().epoch().unwrap_or(prev_epoch);

        Ok(SyncStats {
            total_received: sync_resp.records.len(),
            records_migrated: migrated_count,
            duplicates_skipped: duplicate_skipped,
            quarantined: 0,
            previous_epoch: prev_epoch,
            new_epoch,
            roundtrip_ms: start_time.elapsed().as_secs_f64() * 1000.0,
        })
    }

    /// Sync genetic action skeletons from remote peer into local GeneseedVault with ParetoGate auditing.
    pub fn sync_genes(
        &mut self,
        vault: &mut GeneseedVault,
        since_version: u32,
    ) -> Result<GeneSyncStats, MeshError> {
        let hs = self.handshake(0, 0)?;

        let session_id = random_session_id();
        let req = MeshEnvelope::GeneSyncReq(GeneSyncRequest::signed_with(
            &self.client_node_id,
            since_version,
            hs.nonce,
            &session_id,
            &self.signing_key,
        ));

        let req_bytes =
            serde_json::to_vec(&req).map_err(|e| MeshError::FramingError(e.to_string()))?;
        PhysicalFrameCodec::write_frame(&mut self.stream, &req_bytes)
            .map_err(|e| MeshError::IoError(e.to_string()))?;

        let start_time = Instant::now();
        let resp_bytes = PhysicalFrameCodec::read_frame(
            &mut self.stream,
            start_time,
            DEFAULT_FRAME_ASSEMBLY_TIMEOUT,
        )
        .map_err(|e| MeshError::IoError(e.to_string()))?;

        let env: MeshEnvelope = serde_json::from_slice(&resp_bytes)
            .map_err(|e| MeshError::FramingError(e.to_string()))?;

        let gene_resp = match env {
            MeshEnvelope::GeneSyncResp(resp) => resp,
            MeshEnvelope::Error(e) => return Err(MeshError::StoreError(e)),
            _ => {
                return Err(MeshError::FramingError(
                    "Expected gene_sync_response".to_string(),
                ));
            }
        };

        // Verify the responder's signed identity (bound to the handshake key),
        // nonce/session binding, and freshness before accepting any genes.
        gene_resp.verify(&hs.public_key, &hs.nonce, &session_id, now_millis())?;

        let total_received = gene_resp.genes.len();
        let mut genes_promoted = 0;
        let mut genes_rejected = 0;

        for bundle in &gene_resp.genes {
            // 1. Verify cryptographic signature from peer
            if bundle.verify_signature(&hs.public_key).is_err() {
                genes_rejected += 1;
                continue;
            }

            // 2. Suppress negative knowledge
            if vault.retired_signatures.contains(&bundle.skeleton.id) {
                genes_rejected += 1;
                continue;
            }

            // 3. Maker != Checker audit through local ParetoGate
            let local_existing = vault.get(&bundle.skeleton.id);
            let base_util = local_existing.map(|s| s.rolling_utility).unwrap_or(0.50);
            let fitness_delta = bundle.skeleton.rolling_utility - base_util;

            let assessment = CandidateAssessment {
                candidate_id: GenomeId::from_u64(bundle.skeleton.version as u64),
                parent_ids: bundle
                    .skeleton
                    .parent_id
                    .as_ref()
                    .map(|_| vec![GenomeId::from_u64(1)])
                    .unwrap_or_default(),
                mutation_signature: format!("{}-remote", bundle.skeleton.id),
                fitness_delta: FitnessVector {
                    utility: fitness_delta,
                    throughput: 0.0,
                },
                protected_delta: ProtectedVectorDelta::zero(),
                provenance_valid: true,
                closure_valid: true,
                attempts_self_modification: bundle.skeleton.id.contains("kernel")
                    || bundle.skeleton.id.contains("gate"),
            };

            let fate = ParetoGate::adjudicate(&assessment);
            match fate {
                EvolutionaryFate::Promote => {
                    if let Some(existing) = vault
                        .skeletons
                        .iter_mut()
                        .find(|s| s.id == bundle.skeleton.id)
                    {
                        if bundle.skeleton.version > existing.version
                            || bundle.skeleton.rolling_utility > existing.rolling_utility
                        {
                            *existing = bundle.skeleton.clone();
                            genes_promoted += 1;
                        } else {
                            genes_rejected += 1;
                        }
                    } else {
                        vault.skeletons.push(bundle.skeleton.clone());
                        genes_promoted += 1;
                    }
                }
                EvolutionaryFate::Retire | EvolutionaryFate::Quarantine => {
                    vault.retired_signatures.insert(bundle.skeleton.id.clone());
                    genes_rejected += 1;
                }
            }
        }

        Ok(GeneSyncStats {
            total_received,
            genes_promoted,
            genes_rejected,
        })
    }
}

// ============================================================================
// 5. Unit & Acceptance Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    struct TempDir(PathBuf);
    impl TempDir {
        fn new(prefix: &str) -> Self {
            let p =
                std::env::temp_dir().join(format!("wm3-mesh-{}-{}", prefix, uuid::Uuid::new_v4()));
            std::fs::create_dir_all(&p).unwrap();
            Self(p)
        }
        fn path(&self) -> &Path {
            &self.0
        }
    }
    impl Drop for TempDir {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    fn keypair(seed: u8) -> (SigningKey, [u8; 32]) {
        let mut bytes = [seed; 32];
        bytes[0] = seed;
        bytes[31] = seed.wrapping_add(1);
        let signing_key = SigningKey::from_bytes(&bytes);
        let verifying_key = signing_key.verifying_key();
        (signing_key, verifying_key.to_bytes())
    }

    fn synthetic_store(dir: &TempDir) -> Substrate {
        let mut s = Substrate::open(dir.path(), None, crate::constitution::default_view())
            .expect("open synthetic store");
        s.set_budget(1_000_000);
        s.set_noise_enabled(false);
        #[cfg(feature = "operator")]
        s.set_intake_authority(crate::evidence::RatifiedChannel::mint("mesh-test"));
        s
    }

    #[test]
    fn test_sync_bundle_export_and_import_integrity() {
        let dir_a = TempDir::new("export-a");
        let dir_b = TempDir::new("export-b");
        let (alice_key, alice_pub) = keypair(42);

        let mut store_a = synthetic_store(&dir_a);
        let mut store_b = synthetic_store(&dir_b);

        // Populate store A with 5 records
        let items: Vec<RememberItem> = (0..5)
            .map(|i| RememberItem {
                content: format!("Memory item {}", i),
                source: "operator:test".to_string(),
                kind: ImportKind::Reported,
            })
            .collect();
        store_a.remember_batch(&items);

        assert_eq!(store_a.store().epoch().unwrap(), 5);

        // Export bundle from store A
        let bundle = SyncBundle::export(&store_a, 0, "node-alice", &alice_key)
            .expect("bundle export succeeds");
        assert_eq!(bundle.records.len(), 5);
        assert_eq!(bundle.header.author_pubkey, alice_pub);

        // Verify bundle passes cryptographic validation
        bundle.verify(Some(&alice_pub)).expect("signature valid");

        // Import bundle into store B
        let receipt = bundle
            .import_into_substrate(&mut store_b, Some(&alice_pub), "synthetic.wmpack")
            .expect("bundle import succeeds");

        assert_eq!(receipt.total_records, 5);
        assert_eq!(receipt.migrated_count, 5);
        assert_eq!(receipt.duplicate_skipped, 0);
        assert_eq!(store_b.store().epoch().unwrap(), 5);

        // Re-import bundle into store B -> Strict idempotency (0 writes, 5 skipped)
        let re_receipt = bundle
            .import_into_substrate(&mut store_b, Some(&alice_pub), "synthetic.wmpack")
            .expect("re-import succeeds");
        assert_eq!(re_receipt.migrated_count, 0);
        assert_eq!(re_receipt.duplicate_skipped, 5);
        assert_eq!(store_b.store().epoch().unwrap(), 5);
    }

    #[test]
    fn test_sync_bundle_tamper_fails_closed() {
        let dir = TempDir::new("tamper-source");
        let (alice_key, alice_pub) = keypair(17);
        let mut store = synthetic_store(&dir);

        let items = vec![RememberItem {
            content: "Authentic claim".to_string(),
            source: "operator:test".to_string(),
            kind: ImportKind::Reported,
        }];
        store.remember_batch(&items);

        let mut bundle = SyncBundle::export(&store, 0, "node-alice", &alice_key).unwrap();

        // Tamper with record content
        bundle.records[0].content = "Tampered claim".to_string();

        let dir_target = TempDir::new("tamper-target");
        let mut store_target = synthetic_store(&dir_target);

        // Must fail closed due to Merkle root mismatch
        let res =
            bundle.import_into_substrate(&mut store_target, Some(&alice_pub), "tampered.wmpack");
        assert!(matches!(res, Err(MeshError::BundleCorrupted(_))));
        assert_eq!(store_target.store().epoch().unwrap(), 0);
    }

    #[test]
    fn test_live_tcp_mesh_ping_and_sync() {
        let dir_server = TempDir::new("tcp-server");
        let dir_client = TempDir::new("tcp-client");

        let (server_key, _) = keypair(1);
        let (client_key, _) = keypair(2);

        // Populate server store with 3 records
        let mut server_substrate = synthetic_store(&dir_server);
        let items: Vec<RememberItem> = (0..3)
            .map(|i| RememberItem {
                content: format!("Server record {}", i),
                source: "node:server".to_string(),
                kind: ImportKind::Reported,
            })
            .collect();
        server_substrate.remember_batch(&items);

        // Start mesh server
        let mut server = MeshServer::new("server-node", server_key, dir_server.path());
        let addr = server.listen(0, "127.0.0.1").expect("server binds to port");

        // Client connects and pings
        let mut client = MeshClient::connect(addr, "client-node", client_key)
            .expect("client connects to server");

        let ping_dur = client.ping().expect("ping succeeds");
        assert!(ping_dur.as_millis() < 500);

        // Client syncs delta from server
        let mut client_substrate = synthetic_store(&dir_client);
        assert_eq!(client_substrate.store().epoch().unwrap(), 0);

        let stats = client
            .sync_delta(&mut client_substrate, 100)
            .expect("sync delta succeeds");

        assert_eq!(stats.total_received, 3);
        assert_eq!(stats.records_migrated, 3);
        assert_eq!(stats.duplicates_skipped, 0);
        assert_eq!(client_substrate.store().epoch().unwrap(), 3);

        // Re-sync: verify idempotency over TCP
        let mut client_re = MeshClient::connect(addr, "client-node", keypair(3).0).unwrap();
        let re_stats = client_re
            .sync_delta(&mut client_substrate, 100)
            .expect("re-sync succeeds");
        assert_eq!(re_stats.records_migrated, 0);
        assert_eq!(client_substrate.store().epoch().unwrap(), 3);

        server.stop();
    }

    #[test]
    fn test_mesh_gene_exchange_and_pareto_auditing() {
        let dir_server = TempDir::new("gene-server");
        let (server_key, _) = keypair(11);
        let (client_key, _) = keypair(12);

        // Populate server vault with default action skeletons
        let server_vault_path = dir_server.path().join("vault.jsonl");
        let server_vault = GeneseedVault::load_or_init(&server_vault_path);
        assert!(!server_vault.skeletons.is_empty());
        let expected_count = server_vault
            .skeletons
            .iter()
            .filter(|s| !s.deprecated)
            .count();

        // Start mesh server
        let mut server = MeshServer::new("gene-server", server_key, dir_server.path());
        let addr = server.listen(0, "127.0.0.1").expect("server binds to port");

        // Client connects
        let mut client = MeshClient::connect(addr, "gene-client", client_key)
            .expect("client connects to server");

        // Empty client vault
        let mut client_vault = GeneseedVault {
            skeletons: Vec::new(),
            retired_signatures: std::collections::HashSet::new(),
            total_forks_minted: 0,
            total_retirements: 0,
        };

        // Sync genes from server into client vault with ParetoGate auditing
        let stats = client
            .sync_genes(&mut client_vault, 0)
            .expect("sync genes succeeds");

        assert_eq!(stats.total_received, expected_count);
        assert_eq!(stats.genes_promoted, expected_count);
        assert_eq!(stats.genes_rejected, 0);
        assert_eq!(client_vault.skeletons.len(), expected_count);

        // Verify Negative Knowledge suppression (Article 8)
        let first_id = client_vault.skeletons[0].id.clone();
        let mut client_vault_with_negative_knowledge = GeneseedVault {
            skeletons: Vec::new(),
            retired_signatures: {
                let mut set = std::collections::HashSet::new();
                set.insert(first_id);
                set
            },
            total_forks_minted: 0,
            total_retirements: 0,
        };

        let mut client2 = MeshClient::connect(addr, "gene-client-2", keypair(13).0).unwrap();
        let stats2 = client2
            .sync_genes(&mut client_vault_with_negative_knowledge, 0)
            .expect("sync genes succeeds");

        assert_eq!(stats2.genes_promoted, expected_count - 1);
        assert_eq!(stats2.genes_rejected, 1);

        server.stop();
    }

    fn sha256_hex(content: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(content.as_bytes());
        format!("{:x}", hasher.finalize())
    }

    #[test]
    fn mesh_refuses_non_loopback_bind_without_remote_opt_in() {
        for host in ["0.0.0.0", "::", "192.168.1.10", ""] {
            let err = validate_mesh_bind_with(false, host)
                .expect_err("non-loopback bind must be refused without opt-in");
            assert!(matches!(err, MeshError::Unauthorized(_)), "{host}: {err}");
            assert!(err.to_string().contains("WM_MESH_ALLOW_REMOTE"), "{err}");
        }
        validate_mesh_bind_with(false, "127.0.0.1").expect("loopback allowed");
        validate_mesh_bind_with(false, "localhost").expect("localhost allowed");
        validate_mesh_bind_with(false, "::1").expect("ipv6 loopback allowed");
        validate_mesh_bind_with(true, "0.0.0.0").expect("remote allowed only with opt-in");
    }

    #[test]
    fn mesh_listen_guard_refuses_non_loopback_without_env() {
        let dir = TempDir::new("bind-guard");
        let (key, _) = keypair(9);
        let mut server = MeshServer::new("bind-guard", key, dir.path());
        if std::env::var("WM_MESH_ALLOW_REMOTE").as_deref() != Ok("1") {
            let err = server
                .listen(0, "0.0.0.0")
                .expect_err("wildcard bind must be refused");
            assert_eq!(err.kind(), io::ErrorKind::PermissionDenied);
            assert!(err.to_string().contains("WM_MESH_ALLOW_REMOTE"));
        }
        let addr = server.listen(0, "127.0.0.1").expect("loopback binds");
        assert!(addr.ip().is_loopback());
        server.stop();
    }

    #[test]
    fn mesh_connection_cap_is_env_tunable_with_safe_default() {
        assert_eq!(parse_mesh_max_connections(None), DEFAULT_MESH_MAX_CONNS);
        assert_eq!(parse_mesh_max_connections(Some("4")), 4);
        assert_eq!(parse_mesh_max_connections(Some(" 8 ")), 8);
        assert_eq!(
            parse_mesh_max_connections(Some("0")),
            DEFAULT_MESH_MAX_CONNS
        );
        assert_eq!(
            parse_mesh_max_connections(Some("not-a-number")),
            DEFAULT_MESH_MAX_CONNS
        );
    }

    #[test]
    fn mesh_sync_request_signature_binds_identity_and_fields() {
        let (key, pubkey) = keypair(51);
        let req = SyncRequest::signed("node-a", 3, 50, &key);
        req.verify().expect("valid signature");
        assert_eq!(req.requester_pubkey, pubkey);

        let mut tampered = req.clone();
        tampered.limit = 51;
        assert!(matches!(tampered.verify(), Err(MeshError::Unauthorized(_))));

        let unsigned = SyncRequest {
            signature: Vec::new(),
            ..req.clone()
        };
        assert!(matches!(unsigned.verify(), Err(MeshError::Unauthorized(_))));
    }

    #[test]
    fn mesh_unsigned_sync_request_is_refused_over_wire() {
        let dir = TempDir::new("unsigned-req");
        let (server_key, _) = keypair(21);
        let mut server = MeshServer::new("unsigned-server", server_key, dir.path());
        let addr = server.listen(0, "127.0.0.1").expect("bind");

        let mut stream = TcpStream::connect(addr).expect("connect");
        stream
            .set_read_timeout(Some(Duration::from_secs(5)))
            .expect("read timeout");
        let unsigned = MeshEnvelope::SyncReq(SyncRequest {
            requester_id: "mallory".to_string(),
            since_epoch: 0,
            limit: 100,
            requester_pubkey: [0u8; 32],
            signature: Vec::new(),
            nonce: [0u8; 32],
            session_id: String::new(),
        });
        let bytes = serde_json::to_vec(&unsigned).expect("encode");
        PhysicalFrameCodec::write_frame(&mut stream, &bytes).expect("write frame");

        let resp = PhysicalFrameCodec::read_frame(
            &mut stream,
            Instant::now(),
            DEFAULT_FRAME_ASSEMBLY_TIMEOUT,
        )
        .expect("server answers instead of dropping");
        let env: MeshEnvelope = serde_json::from_slice(&resp).expect("decode");
        match env {
            MeshEnvelope::Error(msg) => {
                assert!(msg.contains("refused"), "unexpected error: {msg}");
                assert!(
                    msg.contains("no handshake nonce"),
                    "unexpected error: {msg}"
                );
            }
            other => panic!("unsigned request must be refused, got {other:?}"),
        }
        server.stop();
    }

    #[test]
    fn mesh_signed_sync_response_rejects_tampering_and_bad_identity() {
        let (key, pubkey) = keypair(31);
        let nonce = [9u8; 32];
        let session = "session-a";
        let now = now_millis();
        let records = vec![SyncRecord {
            record_id: 1,
            content: "authentic".to_string(),
            source: "node:a".to_string(),
            kind: "reported".to_string(),
            sha256: sha256_hex("authentic"),
            created_at: 0,
        }];
        let mut resp = SyncResponse {
            responder_id: "node-a".to_string(),
            records,
            current_epoch: 1,
            has_more: false,
            responder_pubkey: [0u8; 32],
            signature: Vec::new(),
            nonce,
            session_id: session.to_string(),
            timestamp_ms: now,
        };
        resp.sign_with(&key);
        resp.verify(&pubkey, &nonce, session, now)
            .expect("signed response verifies");

        let mut forged = resp.clone();
        forged.responder_pubkey = keypair(32).1;
        assert!(matches!(
            forged.verify(&pubkey, &nonce, session, now),
            Err(MeshError::UntrustedSigner(_))
        ));

        let mut tampered = resp.clone();
        tampered.records[0].content = "malicious".to_string();
        assert!(matches!(
            tampered.verify(&pubkey, &nonce, session, now),
            Err(MeshError::Unauthorized(_))
        ));
    }

    #[test]
    fn mesh_unsigned_handshake_refused_over_wire() {
        let dir = TempDir::new("unsigned-hs");
        let (server_key, _) = keypair(64);
        let mut server = MeshServer::new("hs-server", server_key, dir.path());
        let addr = server.listen(0, "127.0.0.1").expect("bind");

        let mut stream = TcpStream::connect(addr).expect("connect");
        stream
            .set_read_timeout(Some(Duration::from_secs(5)))
            .expect("read timeout");
        let legacy = MeshEnvelope::Handshake(MeshHandshake {
            node_id: "legacy".to_string(),
            public_key: [7u8; 32],
            epoch: 0,
            record_count: 0,
            head_hash: "0".to_string(),
            protocol_version: MESH_PROTOCOL_VERSION,
            nonce: [0u8; 32],
            signature: Vec::new(),
        });
        let bytes = serde_json::to_vec(&legacy).expect("encode");
        PhysicalFrameCodec::write_frame(&mut stream, &bytes).expect("write frame");

        let resp = PhysicalFrameCodec::read_frame(
            &mut stream,
            Instant::now(),
            DEFAULT_FRAME_ASSEMBLY_TIMEOUT,
        )
        .expect("server answers instead of dropping");
        let env: MeshEnvelope = serde_json::from_slice(&resp).expect("decode");
        match env {
            MeshEnvelope::Error(msg) => {
                assert!(msg.contains("handshake refused"), "unexpected error: {msg}");
            }
            other => panic!("unsigned handshake must be refused, got {other:?}"),
        }
        server.stop();
    }

    #[test]
    fn mesh_forged_handshake_ack_refused_by_pinned_client() {
        let (attacker_key, _) = keypair(61);
        let (_, expected_pub) = keypair(62);
        let listener = TcpListener::bind("127.0.0.1:0").expect("listener");
        let addr = listener.local_addr().expect("addr");
        let server = std::thread::spawn(move || {
            let (mut stream, _) = listener.accept().expect("accept");
            let bytes = PhysicalFrameCodec::read_frame(
                &mut stream,
                Instant::now(),
                DEFAULT_FRAME_ASSEMBLY_TIMEOUT,
            )
            .expect("read handshake");
            let env: MeshEnvelope = serde_json::from_slice(&bytes).expect("decode");
            let client_nonce = match env {
                MeshEnvelope::Handshake(hs) => hs.nonce,
                other => panic!("expected handshake, got {other:?}"),
            };
            let mut ack = MeshHandshake {
                node_id: "forged-server".to_string(),
                public_key: [0u8; 32],
                epoch: 0,
                record_count: 0,
                head_hash: "0".to_string(),
                protocol_version: MESH_PROTOCOL_VERSION,
                nonce: client_nonce,
                signature: Vec::new(),
            };
            ack.sign_with(&attacker_key);
            let bytes = serde_json::to_vec(&MeshEnvelope::HandshakeAck(ack)).expect("encode");
            PhysicalFrameCodec::write_frame(&mut stream, &bytes).expect("write ack");
        });

        let mut client = MeshClient::connect_with_peer_allowlist(
            addr,
            "pinned-client",
            keypair(63).0,
            vec![hex_encode_key(&expected_pub)],
        )
        .expect("connect");
        let err = client
            .handshake(0, 0)
            .expect_err("forged ack key must be refused");
        assert!(matches!(err, MeshError::UntrustedSigner(_)), "{err}");
        server.join().expect("fake server thread");
    }

    #[test]
    fn mesh_server_refuses_unlisted_requester() {
        let dir = TempDir::new("server-allow");
        let (server_key, _) = keypair(71);
        let mut server = MeshServer::new("server", server_key, dir.path());
        let addr = server
            .listen_with_peer_allowlist(0, "127.0.0.1", vec!["authorized-node".to_string()])
            .expect("bind with pinned allowlist");
        let (client_key, _) = keypair(72);

        let mut stream = TcpStream::connect(addr).expect("connect");
        stream
            .set_read_timeout(Some(Duration::from_secs(5)))
            .expect("read timeout");
        let nonce = [5u8; 32];
        let hs = MeshEnvelope::Handshake(MeshHandshake {
            node_id: "mallory".to_string(),
            public_key: client_key.verifying_key().to_bytes(),
            epoch: 0,
            record_count: 0,
            head_hash: "0".to_string(),
            protocol_version: MESH_PROTOCOL_VERSION,
            nonce,
            signature: Vec::new(),
        });
        let bytes = serde_json::to_vec(&hs).expect("encode handshake");
        PhysicalFrameCodec::write_frame(&mut stream, &bytes).expect("write handshake");
        let ack = PhysicalFrameCodec::read_frame(
            &mut stream,
            Instant::now(),
            DEFAULT_FRAME_ASSEMBLY_TIMEOUT,
        )
        .expect("read handshake ack");
        let ack: MeshEnvelope = serde_json::from_slice(&ack).expect("decode ack");
        match ack {
            MeshEnvelope::HandshakeAck(ack) => ack.verify(&nonce).expect("signed ack"),
            other => panic!("expected signed handshake ack, got {other:?}"),
        }

        let req = MeshEnvelope::SyncReq(SyncRequest::signed_with(
            "mallory",
            0,
            10,
            nonce,
            "session-unlisted",
            &client_key,
        ));
        let bytes = serde_json::to_vec(&req).expect("encode request");
        PhysicalFrameCodec::write_frame(&mut stream, &bytes).expect("write request");
        let resp = PhysicalFrameCodec::read_frame(
            &mut stream,
            Instant::now(),
            DEFAULT_FRAME_ASSEMBLY_TIMEOUT,
        )
        .expect("read response");
        let resp: MeshEnvelope = serde_json::from_slice(&resp).expect("decode response");
        match resp {
            MeshEnvelope::Error(msg) => {
                assert!(
                    msg.contains("WM_MESH_PEER_ALLOWLIST"),
                    "unexpected error: {msg}"
                );
            }
            other => panic!("unlisted requester must be refused, got {other:?}"),
        }
        server.stop();
    }

    #[test]
    fn mesh_replay_cache_and_stale_response_refused() {
        let (key, pubkey) = keypair(65);
        let nonce = [9u8; 32];
        let session = "session-replay";
        let now = now_millis();
        let records = vec![SyncRecord {
            record_id: 1,
            content: "x".to_string(),
            source: "s".to_string(),
            kind: "reported".to_string(),
            sha256: sha256_hex("x"),
            created_at: 0,
        }];
        let mut resp = SyncResponse {
            responder_id: "n".to_string(),
            records,
            current_epoch: 1,
            has_more: false,
            responder_pubkey: [0u8; 32],
            signature: Vec::new(),
            nonce,
            session_id: session.to_string(),
            timestamp_ms: now,
        };
        resp.sign_with(&key);
        resp.verify(&pubkey, &nonce, session, now)
            .expect("fresh valid response");

        let mut bad_nonce = resp.clone();
        bad_nonce.nonce = [8u8; 32];
        assert!(matches!(
            bad_nonce.verify(&pubkey, &nonce, session, now),
            Err(MeshError::Unauthorized(_))
        ));

        let mut bad_session = resp.clone();
        bad_session.session_id = "other".to_string();
        assert!(matches!(
            bad_session.verify(&pubkey, &nonce, session, now),
            Err(MeshError::Unauthorized(_))
        ));

        let mut stale = resp.clone();
        stale.timestamp_ms = now.saturating_sub(MESH_RESPONSE_MAX_AGE_MS + 1);
        stale.sign_with(&key);
        assert!(matches!(
            stale.verify(&pubkey, &nonce, session, now),
            Err(MeshError::Unauthorized(_))
        ));

        let cache = ReplayCache::default();
        cache
            .observe("key:session", 100)
            .expect("first observation");
        assert!(
            cache.observe("key:session", 100).is_err(),
            "replayed session must be refused"
        );
        cache
            .observe("key:other", 100)
            .expect("distinct session accepted");
        cache
            .observe("key:session", 100 + MESH_REPLAY_WINDOW_SECS + 1)
            .expect("expired replay entry is pruned");
    }

    #[test]
    fn mesh_peer_allowlist_policy() {
        let (_, pubkey) = keypair(66);
        let key_hex = hex_encode_key(&pubkey);
        let allow = parse_peer_allowlist(&format!("node-a, {} , ", key_hex.to_uppercase()));
        assert_eq!(allow.len(), 2);
        assert!(peer_allowed(&allow, "NODE-A", &pubkey));
        assert!(peer_allowed(&allow, "nobody", &pubkey));
        check_peer_allowlist(&allow, false, "node-a", &pubkey).expect("listed node id on remote");
        assert!(
            check_peer_allowlist(&allow, false, "mallory", &[3u8; 32]).is_err(),
            "unlisted remote peer must be refused"
        );

        // Empty allowlist = loopback-only sync.
        check_peer_allowlist(&[], true, "anyone", &pubkey).expect("loopback allowed");
        let err = check_peer_allowlist(&[], false, "remote", &pubkey)
            .expect_err("remote peer refused without an allowlist");
        assert!(err.to_string().contains("loopback-only"), "{err}");
    }

    #[test]
    fn mesh_bundle_receipt_signatures_verified_before_import() {
        fn receipt(id: &str) -> ContinuityReceipt05 {
            ContinuityReceipt05::new(
                id.to_string(),
                "tenant".to_string(),
                "agent".to_string(),
                "session".to_string(),
                1_700_000_000_000,
                "landlock".to_string(),
                "claim".to_string(),
                true,
                "preflight".to_string(),
                None,
                "did:key:alice".to_string(),
            )
        }

        fn bundle_with_receipts(
            author_key: &SigningKey,
            receipts: Vec<ContinuityReceipt05>,
        ) -> SyncBundle {
            let merkle_root = SyncBundle::compute_composite_merkle_root(&[], &receipts, &[]);
            let mut bundle = SyncBundle {
                header: BundleHeader {
                    magic: WMPACK_MAGIC.to_string(),
                    timestamp: 1_700_000_000,
                    author_id: "node-alice".to_string(),
                    author_pubkey: author_key.verifying_key().to_bytes(),
                    from_epoch: 0,
                    to_epoch: 0,
                    record_count: 0,
                },
                records: Vec::new(),
                receipts,
                negative_signatures: Vec::new(),
                merkle_root,
                signature: Vec::new(),
            };
            bundle.sign_with(author_key);
            bundle
        }

        let (alice_key, alice_pub) = keypair(67);
        let (mallory_key, _) = keypair(68);
        let dir = TempDir::new("receipt-target");
        let mut target = synthetic_store(&dir);

        let unsigned = bundle_with_receipts(&alice_key, vec![receipt("receipt-unsigned")]);
        let err = unsigned
            .import_into_substrate(&mut target, Some(&alice_pub), "unsigned.wmpack")
            .expect_err("unsigned receipt must be refused");
        assert!(matches!(err, MeshError::BundleCorrupted(_)), "{err}");

        let mut foreign = receipt("receipt-foreign");
        foreign.sign(&mallory_key);
        let foreign = bundle_with_receipts(&alice_key, vec![foreign]);
        let err = foreign
            .import_into_substrate(&mut target, Some(&alice_pub), "foreign.wmpack")
            .expect_err("foreign receipt signature must be refused");
        assert!(matches!(err, MeshError::InvalidSignature(_)), "{err}");

        let mut good = receipt("receipt-good");
        good.sign(&alice_key);
        let good = bundle_with_receipts(&alice_key, vec![good]);
        let receipt = good
            .import_into_substrate(&mut target, Some(&alice_pub), "good.wmpack")
            .expect("correctly signed receipt imports");
        assert_eq!(receipt.receipts_imported, 1);
    }

    #[test]
    fn mesh_resolve_bind_handles_ipv6_and_rebinding() {
        assert_eq!(
            resolve_mesh_bind("localhost", 7369)
                .expect("localhost resolves")
                .to_string(),
            "127.0.0.1:7369"
        );
        assert_eq!(
            resolve_mesh_bind("::1", 7369).expect("::1").to_string(),
            "[::1]:7369"
        );
        assert_eq!(
            resolve_mesh_bind("[::1]", 7369).expect("[::1]").to_string(),
            "[::1]:7369"
        );
        assert_eq!(
            resolve_mesh_bind("::", 0).expect("::").to_string(),
            "[::]:0"
        );
        assert!(resolve_mesh_bind("", 0).is_err());
        assert!(resolve_mesh_bind("no-such-host.invalid", 0).is_err());

        // Resolve-then-bind: the exact IPv6 loopback address is bound and reachable.
        let dir = TempDir::new("ipv6-bind");
        let (key, _) = keypair(69);
        let mut server = MeshServer::new("ipv6", key, dir.path());
        let bound = server.listen(0, "::1").expect("ipv6 loopback binds");
        assert!(bound.is_ipv6() && bound.ip().is_loopback());
        let (client_key, _) = keypair(70);
        let mut client =
            MeshClient::connect(bound, "ipv6-client", client_key).expect("connect to [::1]");
        client.ping().expect("ping over ipv6 loopback");
        server.stop();
    }

    #[test]
    fn mesh_record_and_bundle_digest_mismatches_fail_closed() {
        let dir = TempDir::new("digest-guard");
        let (key, pubkey) = keypair(41);
        let mut store = synthetic_store(&dir);
        store.remember_batch(&[RememberItem {
            content: "signed payload".to_string(),
            source: "operator:test".to_string(),
            kind: ImportKind::Reported,
        }]);

        let mut bundle = SyncBundle::export(&store, 0, "node-a", &key).expect("export");
        bundle
            .verify(Some(&pubkey))
            .expect("bundle signature valid");

        // The per-record digest is not covered by the bundle Merkle root, so
        // tampering it must be caught by the per-record integrity gate.
        bundle.records[0].sha256 = sha256_hex("something else");
        let dir_b = TempDir::new("digest-target");
        let mut target = synthetic_store(&dir_b);
        let res = bundle.import_into_substrate(&mut target, Some(&pubkey), "digest.wmpack");
        assert!(matches!(res, Err(MeshError::BundleCorrupted(_))));
        assert_eq!(target.store().epoch().unwrap(), 0);

        bundle.records[0].sha256 = String::new();
        let res = bundle.import_into_substrate(&mut target, Some(&pubkey), "digest.wmpack");
        assert!(matches!(res, Err(MeshError::BundleCorrupted(_))));

        let record = SyncRecord {
            record_id: 7,
            content: "x".to_string(),
            source: "s".to_string(),
            kind: "reported".to_string(),
            sha256: "deadbeef".to_string(),
            created_at: 0,
        };
        assert!(matches!(
            record.verify_integrity(),
            Err(MeshError::BundleCorrupted(_))
        ));
    }
}
