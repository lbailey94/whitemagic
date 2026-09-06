//! Record attestations (Track F Slice A, D5 opening move) — tamper-evident
//! provenance for created memories.
//!
//! Every `memory.create` with a node key available appends one attestation
//! to the `attestations` DBI, keyed `att:{galaxy}:{memory_id}`. The entry
//! binds the memory's content hash to the creating agent and node via an
//! Ed25519 signature — the same algorithm (and, by default, the same key
//! material) as the Sangha mesh identity, so signatures verify against the
//! peer keys the fleet already binds.
//!
//! Payload domain separation: the signed bytes begin with
//! `ATTESTATION_DOMAIN` (`wm-record-attestation/v1`), so a record
//! attestation can never verify as a mesh heartbeat/chat payload or vice
//! versa, even though the key is shared. The choice of mesh-key reuse vs a
//! domain-separated attestation seed is inspiron's S9 call (key/KDF plans);
//! this default is documented for overrule — re-keying means new
//! attestations only, old ones keep verifying under the recorded pubkey.
//!
//! Why the sign/verify helper lives here instead of reusing
//! `wm_sangha::crypto`: `wm-memory` must stay free of `wm-sangha` (mesh is
//! a transport over stores, never a store dependency — otherwise future
//! mesh↔store wiring cycles). The scheme is identical (Ed25519 over the
//! domain-prefixed payload, lowercase hex); only the call site differs.
//!
//! Merkle convention for `wm anchor`: [`merkle_root_hex`] uses the same
//! Bitcoin-convention loop as the karma anchor (duplicate-last on odd
//! layers, `sha256(left || right)` upward, `sha256("")` for the empty
//! set), so anchor roots are comparable across subsystems. (Follow-up:
//! factor the shared loop out of `KarmaLedger::compute_merkle_root`.)

use ed25519_dalek::{Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use wm_core::Galaxy;

use crate::memory::MemoryId;

/// Domain prefix for every signed attestation payload. Cross-protocol
/// confusion is impossible by construction: no other WhiteMagic protocol
/// signs bytes beginning with this string.
pub const ATTESTATION_DOMAIN: &str = "wm-record-attestation/v1";

/// Name of the LMDB sub-database holding attestations.
pub const ATTESTATIONS_DB: &str = "attestations";

/// Environment variable carrying the node signing key (hex, 32 bytes) —
/// the same `WM_MESH_KEY` the Sangha mesh uses for peer identity.
pub const ATTESTATION_KEY_ENV: &str = "WM_MESH_KEY";

/// One attestation: a node's signed claim "I created this record with
/// this content hash at this time as this agent".
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RecordAttestation {
    /// Attestation domain (always [`ATTESTATION_DOMAIN`] at v1).
    pub domain: String,
    /// Galaxy db name (e.g. `"codex"`).
    pub galaxy: String,
    /// Memory id (hyphenated UUID string).
    pub memory_id: String,
    /// The memory's `content_hash` at creation time.
    pub record_hash: String,
    /// Attributing agent: dispatch session UUID when inside one,
    /// `user_id` when set, else `"local"`.
    pub agent_id: String,
    /// Unix timestamp (seconds) of the creating dispatch.
    pub timestamp: u64,
    /// Signer public key (lowercase hex) — the node's mesh identity.
    pub public_key_hex: String,
    /// Ed25519 signature over [`attestation_payload`] (lowercase hex).
    pub signature_hex: String,
}

/// Result of checking one memory's attestation.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AttestationReport {
    /// An attestation row exists for this memory.
    pub attested: bool,
    /// The signature verifies against the recorded pubkey and payload.
    pub signature_valid: bool,
    /// The attested `record_hash` equals the memory's live `content_hash`
    /// (false after a content update — the revisions chain, not the
    /// attestation, covers updates by design).
    pub matches_head: bool,
    /// The attested memory id is present in its galaxy (false when the
    /// memory was deleted after attestation — the attestation row
    /// survives as evidence of what was claimed).
    pub memory_present: bool,
    /// Human-readable break descriptions; empty when fully valid.
    pub breaks: Vec<String>,
}

/// Canonical signed payload. Pipe-delimited fixed-order fields — no
/// canonical-JSON dependency, byte-stable by construction.
#[must_use]
pub fn attestation_payload(
    galaxy: &str,
    memory_id: &str,
    record_hash: &str,
    agent_id: &str,
    timestamp: u64,
) -> String {
    format!("{ATTESTATION_DOMAIN}|{galaxy}|{memory_id}|{record_hash}|{agent_id}|{timestamp}")
}

/// LMDB key for one memory's attestation: `att:{galaxy}:{memory_id}`.
#[must_use]
pub fn attestation_key(galaxy: Galaxy, id: MemoryId) -> Vec<u8> {
    format!("att:{}:{}", galaxy.db_name(), id).into_bytes()
}

/// Key prefix covering the whole attestation DBI (for full scans).
#[must_use]
pub fn attestation_prefix() -> Vec<u8> {
    b"att:".to_vec()
}

/// SHA-256 of a string, lowercase hex.
#[must_use]
pub fn sha256_hex(s: &str) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let digest = Sha256::digest(s.as_bytes());
    digest.iter().fold(String::with_capacity(64), |mut out, b| {
        out.push(HEX[(b >> 4) as usize] as char);
        out.push(HEX[(b & 0x0f) as usize] as char);
        out
    })
}

/// Decode 64-char hex into 32 bytes.
fn decode_key_hex(hex: &str) -> Option<[u8; 32]> {
    if hex.len() != 64 {
        return None;
    }
    let bytes = hex.as_bytes();
    let mut out = [0u8; 32];
    for (i, chunk) in bytes.chunks_exact(2).enumerate() {
        let hi = hex_val(chunk[0])?;
        let lo = hex_val(chunk[1])?;
        out[i] = (hi << 4) | lo;
    }
    Some(out)
}

const fn hex_val(b: u8) -> Option<u8> {
    match b {
        b'0'..=b'9' => Some(b - b'0'),
        b'a'..=b'f' => Some(b - b'a' + 10),
        b'A'..=b'F' => Some(b - b'A' + 10),
        _ => None,
    }
}

/// Sign an attestation payload with a 32-byte secret key (hex).
/// Returns `(public_key_hex, signature_hex)`, or `None` on bad key
/// material. Pure function — env handling lives at the call site.
#[must_use]
pub fn sign_attestation(payload: &str, secret_hex: &str) -> Option<(String, String)> {
    let secret = decode_key_hex(secret_hex.trim())?;
    let signing = SigningKey::from_bytes(&secret);
    let sig = signing.sign(payload.as_bytes());
    Some((
        hex_of(&signing.verifying_key().to_bytes()),
        hex_of(&sig.to_bytes()),
    ))
}

fn hex_of(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        out.push(HEX[(b >> 4) as usize] as char);
        out.push(HEX[(b & 0x0f) as usize] as char);
    }
    out
}

/// Verify an attestation's signature against its recorded pubkey.
#[must_use]
pub fn verify_attestation(att: &RecordAttestation) -> bool {
    if att.domain != ATTESTATION_DOMAIN {
        return false;
    }
    let payload = attestation_payload(
        &att.galaxy,
        &att.memory_id,
        &att.record_hash,
        &att.agent_id,
        att.timestamp,
    );
    let (Some(pk_bytes), Some(sig_bytes)) = (
        decode_pubkey(&att.public_key_hex),
        decode_sig(&att.signature_hex),
    ) else {
        return false;
    };
    let Ok(pk) = VerifyingKey::from_bytes(&pk_bytes) else {
        return false;
    };
    let sig = ed25519_dalek::Signature::from_bytes(&sig_bytes);
    pk.verify(payload.as_bytes(), &sig).is_ok()
}

fn decode_pubkey(hex: &str) -> Option<[u8; 32]> {
    decode_key_hex(hex)
}

fn decode_sig(hex: &str) -> Option<[u8; 64]> {
    if hex.len() != 128 {
        return None;
    }
    let bytes = hex.as_bytes();
    let mut out = [0u8; 64];
    for (i, chunk) in bytes.chunks_exact(2).enumerate() {
        out[i] = (hex_val(chunk[0])? << 4) | hex_val(chunk[1])?;
    }
    Some(out)
}

/// Merkle root over leaf-hash strings.
///
/// Same convention as the karma anchor (`KarmaLedger::compute_merkle_root`):
/// duplicate-last on odd layers, `sha256(left || right)` upward, `sha256("")`
/// for the empty set. Leaves must be pre-sorted by the caller for determinism.
#[must_use]
pub fn merkle_root_hex(leaves: &[String]) -> String {
    if leaves.is_empty() {
        return sha256_hex("");
    }
    let mut layer: Vec<String> = leaves.to_vec();
    while layer.len() > 1 {
        if layer.len() % 2 != 0 {
            let last = layer.last().cloned().unwrap_or_default();
            layer.push(last);
        }
        let mut next = Vec::with_capacity(layer.len() / 2);
        for pair in layer.chunks(2) {
            next.push(sha256_hex(&format!("{}{}", pair[0], pair[1])));
        }
        layer = next;
    }
    layer.into_iter().next().unwrap_or_default()
}

/// Anchor leaf input for one attestation: binds the record hash to the
/// attestation signature. `wm anchor` sorts leaves before hashing.
#[must_use]
pub fn anchor_leaf_input(record_hash: &str, signature_hex: &str) -> String {
    sha256_hex(&format!("{record_hash}|{signature_hex}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    const TEST_KEY: &str = "0bd1c44170ca3d916648a983dcdb8583d22f2da5b29fdd5ede4b38e805435577";

    fn test_attestation() -> RecordAttestation {
        let payload = attestation_payload("codex", "mem-1", "hash-1", "ses-1", 1_700_000_000);
        let (pk, sig) = sign_attestation(&payload, TEST_KEY).unwrap();
        RecordAttestation {
            domain: ATTESTATION_DOMAIN.to_string(),
            galaxy: "codex".to_string(),
            memory_id: "mem-1".to_string(),
            record_hash: "hash-1".to_string(),
            agent_id: "ses-1".to_string(),
            timestamp: 1_700_000_000,
            public_key_hex: pk,
            signature_hex: sig,
        }
    }

    #[test]
    fn payload_is_domain_prefixed_and_deterministic() {
        let a = attestation_payload("codex", "m", "h", "a", 1);
        let b = attestation_payload("codex", "m", "h", "a", 1);
        assert_eq!(a, b);
        assert!(a.starts_with("wm-record-attestation/v1|"));
        assert_ne!(a, attestation_payload("codex", "m", "h", "a", 2));
    }

    #[test]
    fn sign_and_verify_roundtrip() {
        assert!(verify_attestation(&test_attestation()));
    }

    #[test]
    fn tampered_record_hash_rejected() {
        let mut att = test_attestation();
        att.record_hash = "forged".to_string();
        assert!(!verify_attestation(&att));
    }

    #[test]
    fn wrong_domain_rejected() {
        let mut att = test_attestation();
        att.domain = "mesh-heartbeat".to_string();
        assert!(!verify_attestation(&att));
    }

    #[test]
    fn bad_key_material_returns_none() {
        let payload = attestation_payload("codex", "m", "h", "a", 1);
        assert!(sign_attestation(&payload, "zz").is_none());
        assert!(sign_attestation(&payload, "abcd").is_none());
        assert!(sign_attestation(&payload, "").is_none());
    }

    #[test]
    fn merkle_root_matches_karma_convention() {
        // Empty set: sha256("").
        assert_eq!(
            merkle_root_hex(&[]),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
        // Single leaf: the leaf itself.
        assert_eq!(merkle_root_hex(&["abc".to_string()]), "abc");
        // Two leaves: sha256(a || b).
        assert_eq!(
            merkle_root_hex(&["a".to_string(), "b".to_string()]),
            sha256_hex("ab")
        );
        // Three leaves: duplicate-last, then hash up.
        let three = merkle_root_hex(&["a".to_string(), "b".to_string(), "c".to_string()]);
        let level1 = [sha256_hex("ab"), sha256_hex("cc")];
        assert_eq!(three, sha256_hex(&format!("{}{}", level1[0], level1[1])));
        // Deterministic.
        assert_eq!(
            merkle_root_hex(&["x".to_string(), "y".to_string()]),
            merkle_root_hex(&["x".to_string(), "y".to_string()])
        );
    }

    #[test]
    fn keys_are_structured() {
        let id = MemoryId::nil();
        let key = String::from_utf8(attestation_key(Galaxy::Codex, id)).unwrap();
        assert!(key.starts_with("att:codex:"));
        assert_eq!(String::from_utf8(attestation_prefix()).unwrap(), "att:");
    }
}
