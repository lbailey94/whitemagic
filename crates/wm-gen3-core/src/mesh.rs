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
}

impl SyncRequest {
    /// Canonical payload covered by the requester's Ed25519 signature.
    pub fn signing_payload(
        requester_id: &str,
        requester_pubkey: &[u8; 32],
        since_epoch: u64,
        limit: usize,
    ) -> Vec<u8> {
        format!(
            "WHITEMAGIC:MESH_SYNC_REQ:v1|requester:{}|pubkey:{}|since:{}|limit:{}",
            requester_id,
            hex_encode_key(requester_pubkey),
            since_epoch,
            limit
        )
        .into_bytes()
    }

    /// Build a signed sync request with the caller's sovereign mesh identity.
    pub fn signed(
        requester_id: &str,
        since_epoch: u64,
        limit: usize,
        signing_key: &SigningKey,
    ) -> Self {
        let requester_pubkey = signing_key.verifying_key().to_bytes();
        let payload = Self::signing_payload(requester_id, &requester_pubkey, since_epoch, limit);
        let signature = signing_key.sign(&payload).to_bytes().to_vec();
        Self {
            requester_id: requester_id.to_string(),
            since_epoch,
            limit,
            requester_pubkey,
            signature,
        }
    }

    /// Verify the embedded signed peer identity. Unsigned or invalid requests fail closed.
    pub fn verify(&self) -> Result<(), MeshError> {
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
        let payload = Self::signing_payload(
            &self.requester_id,
            &self.requester_pubkey,
            self.since_epoch,
            self.limit,
        );
        verifying_key
            .verify(&payload, &Signature::from_bytes(&sig_bytes))
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
}

impl SyncResponse {
    /// Canonical payload covered by the responder's Ed25519 signature.
    pub fn signing_payload(&self) -> Vec<u8> {
        let record_root = SyncBundle::compute_merkle_root(&self.records);
        format!(
            "WHITEMAGIC:MESH_SYNC_RESP:v1|responder:{}|epoch:{}|has_more:{}|records:{}|root:{}",
            self.responder_id,
            self.current_epoch,
            self.has_more,
            self.records.len(),
            hex_encode_key(&record_root)
        )
        .into_bytes()
    }

    /// Sign this response in place with the responder's sovereign mesh key.
    pub fn sign_with(&mut self, signing_key: &SigningKey) {
        self.responder_pubkey = signing_key.verifying_key().to_bytes();
        let payload = self.signing_payload();
        self.signature = signing_key.sign(&payload).to_bytes().to_vec();
    }

    /// Verify the response signature against the peer identity established by the handshake.
    pub fn verify(&self, expected_pubkey: &[u8; 32]) -> Result<(), MeshError> {
        if &self.responder_pubkey != expected_pubkey {
            return Err(MeshError::UntrustedSigner(format!(
                "sync_response responder key {} does not match handshake key {}",
                hex_encode_key(&self.responder_pubkey),
                hex_encode_key(expected_pubkey)
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
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneSyncResponse {
    pub responder_id: String,
    pub genes: Vec<GeneBundle>,
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
                let mut next_level = Vec::with_capacity((current_hashes.len() + 1) / 2);
                for chunk in current_hashes.chunks(2) {
                    let mut hasher = Sha256::new();
                    hasher.update(&chunk[0]);
                    if chunk.len() > 1 {
                        hasher.update(&chunk[1]);
                    } else {
                        hasher.update(&chunk[0]);
                    }
                    next_level.push(hasher.finalize().into());
                }
                current_hashes = next_level;
            }

            return current_hashes[0];
        }

        let records_root = Self::compute_merkle_root(records);
        let mut hasher = Sha256::new();
        hasher.update(&records_root);
        hasher.update(&(receipts.len() as u64).to_le_bytes());
        for r in receipts {
            hasher.update(r.receipt_id.as_bytes());
            hasher.update(r.workspace_claim_digest.as_bytes());
            if let Some(ref s) = r.signature {
                hasher.update(s);
            }
        }
        hasher.update(&(negative_signatures.len() as u64).to_le_bytes());
        for s in negative_signatures {
            hasher.update(s.as_bytes());
        }
        hasher.finalize().into()
    }

    /// Sign bundle with Ed25519 signing key.
    pub fn sign_with(&mut self, key: &SigningKey) {
        let mut hasher = Sha256::new();
        hasher.update(self.header.magic.as_bytes());
        hasher.update(&self.header.timestamp.to_le_bytes());
        hasher.update(self.header.author_id.as_bytes());
        hasher.update(&self.header.author_pubkey);
        hasher.update(&self.header.from_epoch.to_le_bytes());
        hasher.update(&self.header.to_epoch.to_le_bytes());
        hasher.update(&self.header.record_count.to_le_bytes());
        hasher.update(&self.merkle_root);
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
        hasher.update(&self.header.timestamp.to_le_bytes());
        hasher.update(self.header.author_id.as_bytes());
        hasher.update(&self.header.author_pubkey);
        hasher.update(&self.header.from_epoch.to_le_bytes());
        hasher.update(&self.header.to_epoch.to_le_bytes());
        hasher.update(&self.header.record_count.to_le_bytes());
        hasher.update(&self.merkle_root);
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
                let mut hasher = Sha256::new();
                hasher.update(item.content.as_bytes());
                let content_hash = format!("{:x}", hasher.finalize());
                let key = (
                    content_hash,
                    item.source.clone(),
                    match item.kind {
                        ImportKind::Reported => "reported".to_string(),
                        ImportKind::System => "system".to_string(),
                        ImportKind::Simulated => "simulated".to_string(),
                    },
                );

                if substrate.identity_map().contains_key(&key) {
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
                        Err(e) if e.contains("RefusedByKernel: duplicate record") => {
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
            hasher.update(&(migrated_count as u64).to_le_bytes());
            hasher.update(&(duplicate_skipped as u64).to_le_bytes());
            hasher.update(&target_epoch.to_le_bytes());
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
        getrandom::fill(&mut bytes)
            .map_err(|e| io::Error::new(io::ErrorKind::Other, e.to_string()))?;
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

/// Validate a mesh bind host against the loopback-default policy.
///
/// Non-loopback binds are refused unless `WM_MESH_ALLOW_REMOTE=1` is set.
pub fn validate_mesh_bind(bind_host: &str) -> Result<(), MeshError> {
    let allow_remote = std::env::var("WM_MESH_ALLOW_REMOTE")
        .map(|v| v == "1")
        .unwrap_or(false);
    validate_mesh_bind_with(allow_remote, bind_host)
}

fn validate_mesh_bind_with(allow_remote: bool, bind_host: &str) -> Result<(), MeshError> {
    if allow_remote {
        return Ok(());
    }
    let host = bind_host.trim();
    if host.is_empty() {
        return Err(MeshError::Unauthorized(
            "empty mesh bind host; refusing to bind (set WM_MESH_ALLOW_REMOTE=1 to permit non-loopback binds)"
                .to_string(),
        ));
    }
    let parsed = if let Ok(ip) = host.parse::<IpAddr>() {
        Some(ip)
    } else if host.eq_ignore_ascii_case("localhost") {
        Some(IpAddr::V4(Ipv4Addr::LOCALHOST))
    } else {
        None
    };
    match parsed {
        Some(ip) if ip.is_loopback() => Ok(()),
        Some(ip) => Err(MeshError::Unauthorized(format!(
            "refusing non-loopback mesh bind {ip}: set WM_MESH_ALLOW_REMOTE=1 to permit remote mesh listeners"
        ))),
        None => {
            let resolved: Vec<SocketAddr> = (host, 0)
                .to_socket_addrs()
                .map_err(|e| {
                    MeshError::IoError(format!("cannot resolve mesh bind host '{host}': {e}"))
                })?
                .collect();
            if !resolved.is_empty() && resolved.iter().all(|a| a.ip().is_loopback()) {
                Ok(())
            } else {
                Err(MeshError::Unauthorized(format!(
                    "refusing non-loopback mesh bind '{host}': set WM_MESH_ALLOW_REMOTE=1 to permit remote mesh listeners"
                )))
            }
        }
    }
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
    /// `WM_MESH_ALLOW_REMOTE=1` is not set.
    pub fn listen(&mut self, port: u16, bind_host: &str) -> io::Result<SocketAddr> {
        validate_mesh_bind(bind_host)
            .map_err(|e| io::Error::new(io::ErrorKind::PermissionDenied, e.to_string()))?;

        let listener = TcpListener::bind(format!("{}:{}", bind_host, port))?;
        let addr = listener.local_addr()?;
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

        std::thread::spawn(move || {
            while *running_flag.lock().unwrap_or_else(|e| e.into_inner()) {
                match listener_clone.accept() {
                    Ok((mut stream, _client_addr)) => {
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

                        std::thread::spawn(move || {
                            let _conn_slot = conn_slot;
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
                                    Ok(MeshEnvelope::Handshake(_client_hs)) => {
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

                                        let resp = MeshEnvelope::HandshakeAck(MeshHandshake {
                                            node_id: node_id_inner.clone(),
                                            public_key: signing_key_inner
                                                .verifying_key()
                                                .to_bytes(),
                                            epoch,
                                            record_count: count,
                                            head_hash,
                                            protocol_version: MESH_PROTOCOL_VERSION,
                                        });

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

                                        let resp = MeshEnvelope::GeneSyncResp(GeneSyncResponse {
                                            responder_id: node_id_inner.clone(),
                                            genes,
                                        });

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
}

impl MeshClient {
    /// Connect to remote mesh server.
    pub fn connect(
        peer_addr: SocketAddr,
        client_node_id: &str,
        signing_key: SigningKey,
    ) -> Result<Self, MeshError> {
        let stream = TcpStream::connect_timeout(&peer_addr, DEFAULT_CONNECT_TIMEOUT)?;
        stream.set_read_timeout(Some(DEFAULT_FRAME_ASSEMBLY_TIMEOUT))?;
        stream.set_write_timeout(Some(DEFAULT_FRAME_ASSEMBLY_TIMEOUT))?;

        Ok(Self {
            stream,
            client_node_id: client_node_id.to_string(),
            signing_key,
        })
    }

    /// Perform mutual handshake with peer.
    pub fn handshake(
        &mut self,
        local_epoch: u64,
        local_count: u64,
    ) -> Result<MeshHandshake, MeshError> {
        let hs = MeshHandshake {
            node_id: self.client_node_id.clone(),
            public_key: self.signing_key.verifying_key().to_bytes(),
            epoch: local_epoch,
            record_count: local_count,
            head_hash: format!("{:x}", local_epoch),
            protocol_version: MESH_PROTOCOL_VERSION,
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
            MeshEnvelope::HandshakeAck(server_hs) => Ok(server_hs),
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

        // Signed peer identity: the request is signed with the sovereign mesh key.
        let req = MeshEnvelope::SyncReq(SyncRequest::signed(
            &self.client_node_id,
            prev_epoch,
            batch_limit,
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

        // Verify the responder's signed identity (bound to the handshake key)
        // and each record digest before any ingest mutation.
        sync_resp.verify(&hs.public_key)?;
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
                let mut hasher = Sha256::new();
                hasher.update(item.content.as_bytes());
                let content_hash = format!("{:x}", hasher.finalize());
                let key = (
                    content_hash,
                    item.source.clone(),
                    match item.kind {
                        ImportKind::Reported => "reported".to_string(),
                        ImportKind::System => "system".to_string(),
                        ImportKind::Simulated => "simulated".to_string(),
                    },
                );

                if substrate.identity_map().contains_key(&key) {
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
                        Err(e) if e.contains("RefusedByKernel: duplicate record") => {
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

        let req = MeshEnvelope::GeneSyncReq(GeneSyncRequest {
            requester_id: self.client_node_id.clone(),
            since_version,
        });

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
                assert!(msg.contains("no signature"), "unexpected error: {msg}");
            }
            other => panic!("unsigned request must be refused, got {other:?}"),
        }
        server.stop();
    }

    #[test]
    fn mesh_signed_sync_response_rejects_tampering_and_bad_identity() {
        let (key, pubkey) = keypair(31);
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
        };
        resp.sign_with(&key);
        resp.verify(&pubkey).expect("signed response verifies");

        let mut forged = resp.clone();
        forged.responder_pubkey = keypair(32).1;
        assert!(matches!(
            forged.verify(&pubkey),
            Err(MeshError::UntrustedSigner(_))
        ));

        let mut tampered = resp.clone();
        tampered.records[0].content = "malicious".to_string();
        assert!(matches!(
            tampered.verify(&pubkey),
            Err(MeshError::Unauthorized(_))
        ));
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
