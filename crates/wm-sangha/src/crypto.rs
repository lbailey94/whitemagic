//! Mesh cryptography — Ed25519 per-peer identity and message signing.
//!
//! Replaces the shared-secret HMAC layer with asymmetric keys, so a
//! compromised peer can **never** forge another peer's identity or
//! messages: each peer signs with its own secret key, and the community
//! verifies against the peer's bound public key. This is the v26
//! `pulse_verification` Tier-0 design (Ed25519 + Merkle) ported to v5.
//!
//! Payloads are signed as canonical JSON with the signature stripped, so
//! verification is robust against field reordering.

#![forbid(unsafe_code)]

use ed25519_dalek::{Signer, SigningKey, Verifier, VerifyingKey};
use std::fmt;
use wm_core::kdf::{MESH_IDENTITY_INFO, hkdf32};

/// A peer's signing keypair (secret + public). Secret keys are zeroized on
/// drop (zeroize feature of ed25519-dalek).
pub struct MeshKeyPair {
    signing: SigningKey,
}

impl fmt::Debug for MeshKeyPair {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MeshKeyPair")
            .field("public_key", &self.public_key_hex())
            .finish_non_exhaustive()
    }
}

impl Clone for MeshKeyPair {
    fn clone(&self) -> Self {
        Self {
            signing: SigningKey::from_bytes(&self.signing.to_bytes()),
        }
    }
}

impl MeshKeyPair {
    /// Derive the canonical (9.1.8+) mesh identity from node root material:
    /// HKDF-SHA256 with `info = "wm/mesh-identity/v1"` (S9 §2.1 / Q39 §2).
    /// `root` is the canonical root bytes ([`wm_core::kdf::root_bytes`] —
    /// 64-hex material decoded, other material raw); the attestation subkey
    /// derives from the same root. This is the key the node advertises; use
    /// [`Self::from_seed`] only for the one-release dual-verify migration and
    /// legacy fixtures.
    #[must_use]
    pub fn derive_identity(root: &[u8]) -> Self {
        Self::from_secret(hkdf32(root, MESH_IDENTITY_INFO))
    }

    /// True when `pubkey_hex` is a valid identity for this root in either era.
    ///
    /// Covers both the HKDF-derived key and the legacy XOR-fold key — the
    /// one-release migration seam. Drop the legacy arm after the migration
    /// release (S9 §2.1).
    #[must_use]
    pub fn accepts_identity(pubkey_hex: &str, root: &[u8]) -> bool {
        pubkey_hex == Self::derive_identity(root).public_key_hex()
            || pubkey_hex == Self::from_seed(root).public_key_hex()
    }

    /// Generate a fresh keypair from a 32-byte seed (deterministic for
    /// reproducible tests; production should derive from a secret).
    ///
    /// **Legacy derivation (pre-9.1.8):** raw seed bytes XOR-folded into 32
    /// bytes — kept for the dual-verify migration and historical fixtures;
    /// new code derives with [`Self::derive_identity`].
    #[must_use]
    pub fn from_seed(seed: &[u8]) -> Self {
        let mut bytes = [0u8; 32];
        let n = seed.len().min(32);
        bytes[..n].copy_from_slice(&seed[..n]);
        for (i, b) in seed.iter().enumerate().skip(n) {
            bytes[i % 32] ^= b;
        }
        Self {
            signing: SigningKey::from_bytes(&bytes),
        }
    }

    /// Create a keypair from a full 32-byte secret key.
    #[must_use]
    pub fn from_secret(secret: [u8; 32]) -> Self {
        Self {
            signing: SigningKey::from_bytes(&secret),
        }
    }

    /// The public key as lowercase hex (the peer's mesh identity).
    #[must_use]
    pub fn public_key_hex(&self) -> String {
        hex_encode(&self.signing.verifying_key().to_bytes())
    }

    /// Sign a payload, returning the signature as lowercase hex.
    #[must_use]
    pub fn sign_hex(&self, payload: &str) -> String {
        let sig = self.signing.sign(payload.as_bytes());
        hex_encode(&sig.to_bytes())
    }

    /// Verify a payload against a hex-encoded signature and public key.
    #[must_use]
    pub fn verify_hex(payload: &str, signature_hex: &str, public_key_hex: &str) -> bool {
        let Some(sig_bytes) = hex_decode(signature_hex) else {
            return false;
        };
        let Some(pk_bytes) = hex_decode(public_key_hex) else {
            return false;
        };
        let Ok(pk_bytes): Result<[u8; 32], _> = pk_bytes.try_into() else {
            return false;
        };
        let Ok(sig_bytes): Result<[u8; 64], _> = sig_bytes.try_into() else {
            return false;
        };
        let Ok(pk) = VerifyingKey::from_bytes(&pk_bytes) else {
            return false;
        };
        let sig = ed25519_dalek::Signature::from_bytes(&sig_bytes);
        pk.verify(payload.as_bytes(), &sig).is_ok()
    }
}

/// Encode bytes as lowercase hex.
#[must_use]
pub fn hex_encode(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        out.push(HEX[(b >> 4) as usize] as char);
        out.push(HEX[(b & 0x0f) as usize] as char);
    }
    out
}

/// Decode lowercase/uppercase hex into bytes.
#[must_use]
pub fn hex_decode(hex: &str) -> Option<Vec<u8>> {
    if hex.len() % 2 != 0 {
        return None;
    }
    let bytes = hex.as_bytes();
    let mut out = Vec::with_capacity(hex.len() / 2);
    for chunk in bytes.chunks_exact(2) {
        let hi = hex_val(chunk[0])?;
        let lo = hex_val(chunk[1])?;
        out.push((hi << 4) | lo);
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sign_and_verify_roundtrip() {
        let kp = MeshKeyPair::from_seed(b"peer-seed-1");
        let payload = r#"{"id":1,"sender":"node-1"}"#;
        let sig = kp.sign_hex(payload);
        assert!(MeshKeyPair::verify_hex(payload, &sig, &kp.public_key_hex()));
    }

    #[test]
    fn wrong_key_or_tampered_payload_rejected() {
        let kp_a = MeshKeyPair::from_seed(b"peer-a");
        let kp_b = MeshKeyPair::from_seed(b"peer-b");
        let payload = "coordinate";
        let sig = kp_a.sign_hex(payload);

        // Wrong public key → rejected (forgery impossible without the key).
        assert!(!MeshKeyPair::verify_hex(
            payload,
            &sig,
            &kp_b.public_key_hex()
        ));
        // Tampered payload → rejected.
        assert!(!MeshKeyPair::verify_hex(
            "coordinate!",
            &sig,
            &kp_a.public_key_hex()
        ));
        // Garbage signature → rejected.
        assert!(!MeshKeyPair::verify_hex(
            payload,
            "zz",
            &kp_a.public_key_hex()
        ));
    }

    #[test]
    fn hex_roundtrip() {
        let bytes = [0u8, 1, 15, 16, 255, 128];
        let hex = hex_encode(&bytes);
        assert_eq!(hex, "00010f10ff80");
        assert_eq!(hex_decode(&hex).unwrap(), bytes);
        assert!(hex_decode("abc").is_none());
        assert!(hex_decode("zz").is_none());
    }

    #[test]
    fn kdf_migration_eras_are_deterministic_and_distinct() {
        let root = b"643232...not-hex-but-raw-env-material";
        let derived_a = MeshKeyPair::derive_identity(root);
        let derived_b = MeshKeyPair::derive_identity(root);
        let legacy = MeshKeyPair::from_seed(root);
        assert_eq!(derived_a.public_key_hex(), derived_b.public_key_hex());
        assert_ne!(
            derived_a.public_key_hex(),
            legacy.public_key_hex(),
            "HKDF identity must differ from the legacy XOR-fold identity"
        );

        // The derived key signs and verifies like any other identity.
        let payload = "beacon:node-1:127.0.0.1:7369:42";
        let sig = derived_a.sign_hex(payload);
        assert!(MeshKeyPair::verify_hex(
            payload,
            &sig,
            &derived_a.public_key_hex()
        ));
    }

    #[test]
    fn accepts_identity_covers_both_migration_eras() {
        let root = b"legacy-or-derived-roots";
        let derived = MeshKeyPair::derive_identity(root).public_key_hex();
        let legacy = MeshKeyPair::from_seed(root).public_key_hex();
        assert!(MeshKeyPair::accepts_identity(&derived, root));
        assert!(MeshKeyPair::accepts_identity(&legacy, root));
        assert!(!MeshKeyPair::accepts_identity(
            &MeshKeyPair::derive_identity(b"other-root").public_key_hex(),
            root
        ));
        assert!(!MeshKeyPair::accepts_identity("not-hex", root));
    }
}
