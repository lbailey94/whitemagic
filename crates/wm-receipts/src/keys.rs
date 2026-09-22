//! Receipt signing keys and `did:key` identity.
//!
//! One identity per WM node/store, zero setup:
//!
//! 1. `WM_RECEIPT_KEY` — 64-hex-char root material (explicit override).
//! 2. `WM_MESH_KEY` — the node root; the receipt signer is a domain-separated
//!    HKDF-SHA256 subkey (`wm/receipt-signing/v1`).
//! 3. `<store>/.receipt_key` — 32 raw bytes, created mode 0600 on first use
//!    (same pattern as `.seal_key`).
//!
//! The `did:key` in `issuer.id` identifies this node/store. No human-principal
//! claim is made anywhere in the receipt.

use std::path::Path;

use ed25519_dalek::{Signer, SigningKey, VerifyingKey};
use wm_core::kdf::{hkdf32, root_bytes};

use crate::error::{ReceiptError, Result};

/// HKDF info string for the receipt signer (new, versioned; see kdf.rs).
pub const RECEIPT_SIGNING_INFO: &str = "wm/receipt-signing/v1";
/// Explicit receipt-key override (64 hex chars of root material).
pub const RECEIPT_KEY_ENV: &str = "WM_RECEIPT_KEY";
/// Node root key (64 hex chars); the receipt signer derives from it.
pub const MESH_KEY_ENV: &str = "WM_MESH_KEY";
/// Store-local key file, created on first use.
pub const RECEIPT_KEY_FILE: &str = ".receipt_key";
/// Raw key length for the store-local file.
const KEY_LEN: usize = 32;

/// A resolved signing identity: the Ed25519 key plus its `did:key`.
#[derive(Debug, Clone)]
pub struct ReceiptKey {
    signing: SigningKey,
    did: String,
}

impl ReceiptKey {
    /// Derive from root material (env value): HKDF-SHA256 with the receipt info
    /// string, so the signer never reuses the mesh identity key itself.
    #[must_use]
    pub fn from_root_material(material: &str) -> Self {
        let seed = hkdf32(&root_bytes(material), RECEIPT_SIGNING_INFO);
        Self::from_seed(seed)
    }

    /// Derive from the 32 raw bytes of a store-local key file.
    pub fn from_file_bytes(bytes: &[u8]) -> Result<Self> {
        let seed: [u8; KEY_LEN] = bytes.try_into().map_err(|_| {
            ReceiptError::Key(format!(
                "{RECEIPT_KEY_FILE} is {} bytes, expected {KEY_LEN}",
                bytes.len()
            ))
        })?;
        Ok(Self::from_seed(hkdf32(&seed, RECEIPT_SIGNING_INFO)))
    }

    /// Build directly from a 32-byte seed (tests, vectors, explicit keys).
    #[must_use]
    pub fn from_seed(seed: [u8; KEY_LEN]) -> Self {
        let signing = SigningKey::from_bytes(&seed);
        let did = did_key(&signing.verifying_key());
        Self { signing, did }
    }

    /// The issuer `did:key`.
    #[must_use]
    pub fn did(&self) -> &str {
        &self.did
    }

    /// The public key.
    #[must_use]
    pub fn verifying_key(&self) -> VerifyingKey {
        self.signing.verifying_key()
    }

    /// The private signing key (crate-internal: disclosure re-signing only).
    pub(crate) const fn signing_key(&self) -> &SigningKey {
        &self.signing
    }

    /// Sign bytes; returns base64url (no padding) per the CR envelope.
    #[must_use]
    pub fn sign(&self, message: &[u8]) -> String {
        b64u(self.signing.sign(message).to_bytes())
    }
}

/// `did:key` encoding: base58btc(`0xed01` || raw Ed25519 public key).
#[must_use]
pub fn did_key(verifying: &VerifyingKey) -> String {
    let mut bytes = Vec::with_capacity(34);
    bytes.extend_from_slice(&[0xed, 0x01]);
    bytes.extend_from_slice(&verifying.to_bytes());
    format!("did:key:z{}", bs58::encode(bytes).into_string())
}

/// Resolve the emission key by the documented precedence.
///
/// `store_root` is only needed when neither env var is set.
pub fn resolve_key(store_root: Option<&Path>) -> Result<ReceiptKey> {
    for name in [RECEIPT_KEY_ENV, MESH_KEY_ENV] {
        if let Ok(material) = std::env::var(name) {
            if !material.trim().is_empty() {
                return Ok(ReceiptKey::from_root_material(&material));
            }
        }
    }
    match store_root {
        Some(root) => ReceiptKey::from_file_bytes(&load_or_create_key_file(root)?),
        None => Err(ReceiptError::Key(format!(
            "no receipt key: set {RECEIPT_KEY_ENV} or {MESH_KEY_ENV}, \
             or provide a store root for {RECEIPT_KEY_FILE}"
        ))),
    }
}

/// Load `<store>/.receipt_key`, creating it (32 bytes, mode 0600) on first use.
pub fn load_or_create_key_file(store_root: &Path) -> Result<Vec<u8>> {
    let path = store_root.join(RECEIPT_KEY_FILE);
    if path.exists() {
        let bytes = std::fs::read(&path)?;
        if bytes.len() != KEY_LEN {
            return Err(ReceiptError::Key(format!(
                "receipt key at {} is {} bytes, expected {KEY_LEN}",
                path.display(),
                bytes.len()
            )));
        }
        return Ok(bytes);
    }
    let bytes = generate_random_bytes(KEY_LEN);
    std::fs::write(&path, &bytes)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600));
    }
    Ok(bytes)
}

/// 32 random bytes from `/dev/urandom`, with a time+PID hash fallback.
fn generate_random_bytes(n: usize) -> Vec<u8> {
    use sha2::{Digest, Sha256};
    use std::io::Read;

    let mut buffer = vec![0u8; n];
    if let Ok(mut file) = std::fs::File::open("/dev/urandom") {
        if file.read_exact(&mut buffer).is_ok() {
            return buffer;
        }
    }
    let mut hasher = Sha256::new();
    hasher.update(
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos()
            .to_le_bytes(),
    );
    hasher.update(std::process::id().to_le_bytes());
    let digest = hasher.finalize();
    buffer.copy_from_slice(&digest[..n]);
    buffer
}

/// base64url without padding (CR `sig.value` encoding).
#[must_use]
pub fn b64u(data: impl AsRef<[u8]>) -> String {
    use base64::Engine as _;
    base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(data)
}

/// Decode base64url without padding.
#[must_use]
pub fn b64u_decode(text: &str) -> Option<Vec<u8>> {
    use base64::Engine as _;
    base64::engine::general_purpose::URL_SAFE_NO_PAD
        .decode(text)
        .ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn seed() -> [u8; 32] {
        [7u8; 32]
    }

    #[test]
    fn did_key_has_ed25519_multicodec_prefix() {
        let key = ReceiptKey::from_seed(seed());
        assert!(key.did().starts_with("did:key:z"));
        let raw = bs58::decode(&key.did()["did:key:z".len()..])
            .into_vec()
            .expect("valid base58");
        assert_eq!(raw.len(), 34);
        assert_eq!(raw[0], 0xed);
        assert_eq!(raw[1], 0x01);
        assert_eq!(&raw[2..], key.verifying_key().as_bytes());
    }

    #[test]
    fn env_material_derivation_is_deterministic_and_domain_separated() {
        let material = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff";
        let a = ReceiptKey::from_root_material(material);
        let b = ReceiptKey::from_root_material(material);
        assert_eq!(a.did(), b.did(), "same material must yield the same DID");

        // Domain separation: the derived receipt key must differ from the mesh
        // identity subkey for the same root.
        let mesh_seed = hkdf32(&root_bytes(material), wm_core::kdf::MESH_IDENTITY_INFO);
        let receipt_seed = hkdf32(&root_bytes(material), RECEIPT_SIGNING_INFO);
        assert_ne!(mesh_seed, receipt_seed);
    }

    #[test]
    fn file_key_round_trips_and_rejects_wrong_length() {
        let dir = tempfile::tempdir().expect("tempdir");
        let bytes = load_or_create_key_file(dir.path()).expect("create");
        assert_eq!(bytes.len(), KEY_LEN);
        let again = load_or_create_key_file(dir.path()).expect("reload");
        assert_eq!(bytes, again, "key file must be stable across loads");

        std::fs::write(dir.path().join(RECEIPT_KEY_FILE), b"short").expect("write");
        assert!(load_or_create_key_file(dir.path()).is_err());
    }

    #[test]
    fn sign_and_public_verification_round_trip() {
        let key = ReceiptKey::from_seed(seed());
        let signature = key.sign(b"message");
        let decoded = b64u_decode(&signature).expect("valid b64u");
        let sig = ed25519_dalek::Signature::from_slice(&decoded).expect("signature bytes");
        use ed25519_dalek::Verifier;
        assert!(key.verifying_key().verify(b"message", &sig).is_ok());
        assert!(key.verifying_key().verify(b"other", &sig).is_err());
    }
}
