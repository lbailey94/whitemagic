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
    /// Generate a fresh keypair from a 32-byte seed (deterministic for
    /// reproducible tests; production should derive from a secret).
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

// ── Key derivation (S9) ───────────────────────────────────────────────
//
// The fleet master secret (`WM_MESH_KEY`) must never seed a key directly:
// raw ASCII bytes are a biased, low-entropy seed, and sharing one key
// across purposes couples every protocol. HKDF-SHA256 with explicit
// domain strings derives one independent subkey per purpose.

/// HKDF domain for the node identity (Ed25519) key.
pub const DOMAIN_IDENTITY: &str = "sangha/identity/v1";
/// HKDF domain for future chat-specific key material.
///
/// Note: chat *signatures* deliberately use the identity key (chat
/// messages bind to the peer identity established by signed heartbeats);
/// this domain is reserved for chat-specific symmetric material.
pub const DOMAIN_CHAT: &str = "sangha/chat/v1";
/// HKDF domain for mail-slot key material.
pub const DOMAIN_MAIL_SLOT: &str = "sangha/mailslot/v1";

const HKDF_SALT: &[u8] = b"sangha/hkdf/v1";

/// Derive a domain-separated 32-byte subkey from the fleet master secret
/// via HKDF-SHA256. Deterministic: the same master + domain always yields
/// the same key; different domains yield independent keys.
#[must_use]
pub fn derive_key(master: &[u8], domain: &str) -> [u8; 32] {
    let hk = hkdf::Hkdf::<sha2::Sha256>::new(Some(HKDF_SALT), master);
    let mut okm = [0u8; 32];
    // 32 bytes never exceeds the HKDF output limit; expand cannot fail.
    hk.expand(domain.as_bytes(), &mut okm)
        .expect("32-byte OKM is a valid HKDF length");
    okm
}

impl MeshKeyPair {
    /// Derive a keypair from the fleet master secret and an HKDF domain.
    ///
    /// This is the production path: `WM_MESH_KEY` is master key material,
    /// never a seed. Changing the domain derives an unrelated key.
    #[must_use]
    pub fn derive_from_master(master: &[u8], domain: &str) -> Self {
        Self::from_secret(derive_key(master, domain))
    }
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
    fn hkdf_deterministic_and_domain_separated() {
        let master = b"fleet-master-secret";
        let a1 = derive_key(master, DOMAIN_IDENTITY);
        let a2 = derive_key(master, DOMAIN_IDENTITY);
        assert_eq!(a1, a2, "same master + domain must be deterministic");

        let chat = derive_key(master, DOMAIN_CHAT);
        let mail = derive_key(master, DOMAIN_MAIL_SLOT);
        assert_ne!(a1, chat, "different domains must derive independent keys");
        assert_ne!(chat, mail);

        let other = derive_key(b"another-master", DOMAIN_IDENTITY);
        assert_ne!(a1, other, "different masters must derive different keys");

        // Derived keypairs sign and verify like any other.
        let kp = MeshKeyPair::derive_from_master(master, DOMAIN_IDENTITY);
        let sig = kp.sign_hex("payload");
        assert!(MeshKeyPair::verify_hex(
            "payload",
            &sig,
            &kp.public_key_hex()
        ));
    }

    #[test]
    fn weak_ascii_master_still_yields_full_entropy_key() {
        // The historical bug: raw ASCII env bytes as the Ed25519 seed are
        // biased (each byte < 128, human-readable). HKDF output must not
        // reproduce the master bytes in the derived key.
        let master = b"aaaaaaaaaaaaaaaa";
        let derived = derive_key(master, DOMAIN_IDENTITY);
        assert!(derived.iter().any(|&b| b > 0x7f));
        assert_ne!(&derived[..16], master);
    }
}
