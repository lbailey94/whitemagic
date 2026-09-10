//! Model signing — Ed25519-signed artifact enforcement.
//!
//! Rust port of the Python `whitemagic/security/model_signing.py`
//! (Edgerunner Violet security layer, OpenSSF Model Signing-inspired):
//! models/artifacts are hash-bound and cryptographically signed before
//! inference is allowed; unsigned or tampered artifacts are surfaced as
//! verdicts the caller must gate on. Python tracked manifests in a
//! registry keyed by model name with trust levels; the Rust port keeps the
//! semantics that survive as pure logic — recompute the SHA-256, verify
//! the Ed25519 signature over the canonical payload, and check the
//! artifact's hash equals the signed hash. Trust-state management and
//! persistence stay with the caller (registry-free, store-free).
//!
//! Nonce + ROE-hash binding (Python's engagement-token interlock): both
//! are optional fields inside the signed payload, so a signature binds a
//! model artifact to a specific engagement context when present.
//!
//! Canonical serialization (byte-deterministic, `gratitude_ledger` style):
//! the signature input is `serde_json::to_string` of a fixed-field
//! projection struct — field order == declaration order, compact (no
//! spaces), absent bindings serialize as `null`:
//!
//! ```json
//! {"artifact_id":"phi-3-mini.gguf","content_hash":"…","nonce":"…","rules_of_engagement_hash":null}
//! ```
//!
//! `signer_pubkey_hex`, `signature`, and `signed_at` are excluded (identity
//! and output, not input). Pure verification logic — no LLM, no network,
//! no store.

#![forbid(unsafe_code)]

use std::path::Path;

use chrono::Utc;
use serde::Serialize;
use sha2::{Digest as _, Sha256};

use crate::network_profile::AgentKeypair;

/// SHA-256 hex digest of raw bytes (`karma_ledger` helper style).
#[must_use]
pub fn sha256_hex_bytes(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hex_encode(&hasher.finalize())
}

/// A signed model/artifact manifest: hash bound and Ed25519 signed.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct ModelSignature {
    /// Human-facing artifact identifier (file name, model tag, …).
    pub artifact_id: String,
    /// SHA-256 hex of the artifact bytes.
    pub content_hash: String,
    /// Signer's Ed25519 public key (lowercase hex).
    pub signer_pubkey_hex: String,
    /// Ed25519 signature (hex) over the canonical payload.
    pub signature: String,
    /// Unix epoch seconds of signing.
    pub signed_at: i64,
    /// Optional engagement nonce bound into the signature.
    pub nonce: Option<String>,
    /// Optional rules-of-engagement hash bound into the signature.
    pub rules_of_engagement_hash: Option<String>,
}

/// Canonical signed projection of a manifest — fixed field order for
/// byte-deterministic serialization. `signer_pubkey_hex`, `signature`, and
/// `signed_at` are excluded (identity and output, not input).
#[derive(Serialize)]
struct ModelPayload<'a> {
    artifact_id: &'a str,
    content_hash: &'a str,
    nonce: Option<&'a str>,
    rules_of_engagement_hash: Option<&'a str>,
}

/// Outcome of verifying a signed artifact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ModelVerdict {
    /// Signature verifies and the artifact bytes hash to the signed hash.
    Valid,
    /// Signature does not verify against the manifest's signer key (or a
    /// signed field — including an optional nonce/ROE binding — was
    /// tampered with).
    BadSignature,
    /// Signature verifies but the artifact bytes do not hash to the signed
    /// hash — possible tampering or wrong artifact.
    HashMismatch {
        /// Hash recorded in the signed manifest.
        expected: String,
        /// Hash recomputed from the presented artifact.
        actual: String,
    },
}

/// Signs model/artifact bytes with an Ed25519 keypair. Pure logic — the
/// key management surface is the caller's job.
pub struct ModelSigner {
    keypair: AgentKeypair,
}

impl std::fmt::Debug for ModelSigner {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ModelSigner")
            .field("public_key", &self.keypair.public_key_hex())
            .finish()
    }
}

impl ModelSigner {
    /// Create a signer with a fresh OS-entropy keypair.
    #[must_use]
    pub fn new() -> Self {
        Self {
            keypair: AgentKeypair::generate(),
        }
    }

    /// Create a signer from an explicit keypair (deterministic tests,
    /// restored signer identities).
    #[must_use]
    pub const fn with_keypair(keypair: AgentKeypair) -> Self {
        Self { keypair }
    }

    /// The signer's Ed25519 public key (hex).
    #[must_use]
    pub fn signer_public_key_hex(&self) -> String {
        self.keypair.public_key_hex()
    }

    /// Hash and sign a file on disk (streamed in 8 KiB chunks). The
    /// artifact id is the file name.
    ///
    /// # Errors
    ///
    /// Propagates I/O errors from opening or reading `path`.
    pub fn sign_file(&self, path: &Path) -> std::io::Result<ModelSignature> {
        use std::io::Read;
        let mut hasher = Sha256::new();
        let mut file = std::fs::File::open(path)?;
        let mut buf = [0u8; 8192];
        loop {
            let read = file.read(&mut buf)?;
            if read == 0 {
                break;
            }
            hasher.update(&buf[..read]);
        }
        let content_hash = hex_encode(&hasher.finalize());
        let artifact_id = path.file_name().map_or_else(
            || "artifact".to_owned(),
            |n| n.to_string_lossy().into_owned(),
        );
        Ok(self.sign_hash(&artifact_id, &content_hash))
    }

    /// Hash and sign in-memory bytes. The artifact id defaults to
    /// `"inline"` — callers wanting a meaningful id should sign the hash
    /// via [`Self::sign_hash`].
    #[must_use]
    pub fn sign_bytes(&self, bytes: &[u8]) -> ModelSignature {
        self.sign_hash("inline", &sha256_hex_bytes(bytes))
    }

    /// Sign an already-computed SHA-256 hex hash (e.g. from a streamed
    /// hash of a huge artifact).
    #[must_use]
    pub fn sign_hash(&self, artifact_id: &str, content_hash: &str) -> ModelSignature {
        let signature = ModelSignature {
            artifact_id: artifact_id.to_owned(),
            content_hash: content_hash.to_ascii_lowercase(),
            signer_pubkey_hex: self.keypair.public_key_hex(),
            signature: String::new(),
            signed_at: Utc::now().timestamp(),
            nonce: None,
            rules_of_engagement_hash: None,
        };
        let sig = self
            .keypair
            .sign_hex(canonical_payload(&signature).as_bytes());
        ModelSignature {
            signature: sig,
            ..signature
        }
    }

    /// Attach an engagement binding (nonce + ROE hash) to an existing
    /// manifest and re-sign, so the binding is covered by the signature.
    #[must_use]
    pub fn bind_engagement(
        &self,
        mut signature: ModelSignature,
        nonce: &str,
        rules_of_engagement_hash: &str,
    ) -> ModelSignature {
        signature.nonce = Some(nonce.to_owned());
        signature.rules_of_engagement_hash = Some(rules_of_engagement_hash.to_ascii_lowercase());
        let sig = self
            .keypair
            .sign_hex(canonical_payload(&signature).as_bytes());
        ModelSignature {
            signature: sig,
            ..signature
        }
    }
}

impl Default for ModelSigner {
    fn default() -> Self {
        Self::new()
    }
}

/// Verify raw artifact bytes against a [`ModelSignature`]: recompute the
/// SHA-256, verify the Ed25519 signature over the canonical payload, and
/// check the hashes match.
#[must_use]
pub fn verify_model(bytes: &[u8], signature: &ModelSignature) -> ModelVerdict {
    verify_model_hash(&sha256_hex_bytes(bytes), signature)
}

/// Verify a recomputed SHA-256 hex hash against a [`ModelSignature`]
/// (same checks as [`verify_model`] for callers that hashed huge artifacts
/// incrementally).
#[must_use]
pub fn verify_model_hash(hash_hex: &str, signature: &ModelSignature) -> ModelVerdict {
    if !crate::network_profile::verify_signature(
        &signature.signer_pubkey_hex,
        canonical_payload(signature).as_bytes(),
        &signature.signature,
    ) {
        return ModelVerdict::BadSignature;
    }
    let actual = hash_hex.to_ascii_lowercase();
    let expected = signature.content_hash.to_ascii_lowercase();
    if expected != actual {
        return ModelVerdict::HashMismatch { expected, actual };
    }
    ModelVerdict::Valid
}

/// Canonical signed payload for a manifest (module docs document the exact
/// wire format).
fn canonical_payload(signature: &ModelSignature) -> String {
    serde_json::to_string(&ModelPayload {
        artifact_id: &signature.artifact_id,
        content_hash: &signature.content_hash,
        nonce: signature.nonce.as_deref(),
        rules_of_engagement_hash: signature.rules_of_engagement_hash.as_deref(),
    })
    .unwrap_or_default()
}

fn hex_encode(bytes: &[u8]) -> String {
    use std::fmt::Write as _;
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        let _ = write!(out, "{b:02x}");
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn signer() -> ModelSigner {
        ModelSigner::with_keypair(crate::network_profile::AgentKeypair::from_seed([7u8; 32]))
    }

    #[test]
    fn sign_bytes_verify_model_roundtrip() {
        let sig = signer().sign_bytes(b"model weights");
        assert_eq!(sig.artifact_id, "inline");
        assert_eq!(sig.content_hash, sha256_hex_bytes(b"model weights"));
        assert_eq!(verify_model(b"model weights", &sig), ModelVerdict::Valid);
    }

    #[test]
    fn wrong_artifact_fails() {
        let sig = signer().sign_bytes(b"model weights");
        match verify_model(b"tampered weights", &sig) {
            ModelVerdict::HashMismatch { expected, actual } => {
                assert_eq!(expected, sig.content_hash);
                assert_eq!(actual, sha256_hex_bytes(b"tampered weights"));
                assert_ne!(expected, actual);
            }
            other => panic!("expected hash mismatch, got {other:?}"),
        }
    }

    #[test]
    fn tampered_signature_fails() {
        let signer = signer();
        let mut sig = signer.sign_hash("phi-3-mini", &sha256_hex_bytes(b"weights"));
        sig.signature = "0".repeat(128);
        assert_eq!(
            verify_model_hash(&sha256_hex_bytes(b"weights"), &sig),
            ModelVerdict::BadSignature
        );
    }

    #[test]
    fn tampered_artifact_id_fails_signature() {
        let signer = signer();
        let sig = signer.sign_hash("phi-3-mini", &sha256_hex_bytes(b"weights"));
        let mut swapped = sig;
        swapped.artifact_id = "phi-4-mini".to_owned();
        assert_eq!(
            verify_model_hash(&sha256_hex_bytes(b"weights"), &swapped),
            ModelVerdict::BadSignature
        );
    }

    #[test]
    fn foreign_signer_key_fails() {
        let signer_a =
            ModelSigner::with_keypair(crate::network_profile::AgentKeypair::from_seed([1u8; 32]));
        let signer_b =
            ModelSigner::with_keypair(crate::network_profile::AgentKeypair::from_seed([2u8; 32]));
        let sig = signer_a.sign_hash("m", &sha256_hex_bytes(b"weights"));
        let mut forged = sig;
        forged.signer_pubkey_hex = signer_b.signer_public_key_hex();
        assert_eq!(
            verify_model_hash(&sha256_hex_bytes(b"weights"), &forged),
            ModelVerdict::BadSignature
        );
    }

    #[test]
    fn verify_model_hash_matches_verify_model() {
        let sig = signer().sign_bytes(b"weights");
        assert_eq!(
            verify_model_hash(&sig.content_hash, &sig),
            verify_model(b"weights", &sig)
        );
    }

    #[test]
    fn engagement_binding_is_signed() {
        let signer = signer();
        let base = signer.sign_hash("phi-3-mini", &sha256_hex_bytes(b"weights"));
        let bound = signer.bind_engagement(base, "nonce-123", "roe-hash-abc");
        assert_eq!(bound.nonce.as_deref(), Some("nonce-123"));
        assert_eq!(
            verify_model_hash(&sha256_hex_bytes(b"weights"), &bound),
            ModelVerdict::Valid
        );
        // Tampering with either binding field breaks the signature.
        let mut tampered_nonce = bound.clone();
        tampered_nonce.nonce = Some("nonce-999".to_owned());
        assert_eq!(
            verify_model_hash(&sha256_hex_bytes(b"weights"), &tampered_nonce),
            ModelVerdict::BadSignature
        );
        let mut tampered_roe = bound;
        tampered_roe.rules_of_engagement_hash = Some("roe-hash-xyz".to_owned());
        assert_eq!(
            verify_model_hash(&sha256_hex_bytes(b"weights"), &tampered_roe),
            ModelVerdict::BadSignature
        );
    }

    #[test]
    fn sign_file_roundtrip() {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join("phi-3-mini.gguf");
        std::fs::write(&path, b"file model weights").expect("write");
        let sig = signer().sign_file(&path).expect("sign");
        assert_eq!(sig.artifact_id, "phi-3-mini.gguf");
        assert_eq!(
            verify_model(b"file model weights", &sig),
            ModelVerdict::Valid
        );
        // A different file with the same content hashes identically — the
        // binding is content, not location.
        let other = dir.path().join("phi-3-mini-copy.gguf");
        std::fs::write(&other, b"file model weights").expect("write");
        let sig2 = signer().sign_file(&other).expect("sign");
        assert_eq!(sig.content_hash, sig2.content_hash);
    }

    #[test]
    fn canonical_payload_is_deterministic() {
        let mk = |nonce: Option<&str>, roe: Option<&str>| ModelSignature {
            artifact_id: "phi-3-mini".to_owned(),
            content_hash: "abc".to_owned(),
            signer_pubkey_hex: "ff".repeat(32),
            signature: String::new(),
            signed_at: 1_700_000_000,
            nonce: nonce.map(str::to_owned),
            rules_of_engagement_hash: roe.map(str::to_owned),
        };
        let p1 = canonical_payload(&mk(None, None));
        let p2 = canonical_payload(&mk(None, None));
        assert_eq!(p1, p2);
        assert_eq!(
            p1,
            r#"{"artifact_id":"phi-3-mini","content_hash":"abc","nonce":null,"rules_of_engagement_hash":null}"#
        );
        assert_eq!(
            canonical_payload(&mk(Some("n"), Some("r"))),
            r#"{"artifact_id":"phi-3-mini","content_hash":"abc","nonce":"n","rules_of_engagement_hash":"r"}"#
        );
        // Identity/output fields never leak into the payload.
        assert!(!p1.contains("signature"));
        assert!(!p1.contains("signer"));
        assert!(!p1.contains("signed_at"));
    }
}
