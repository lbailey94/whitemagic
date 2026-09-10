//! Release artifact manifest — signed provenance for shipped binaries.
//!
//! P-PROV-5/B(a) (2026-09-10, Glama rug-pull/tool-poisoning thread): a
//! release is a manifest (artifacts + hashes + binary identity, including
//! the tool-surface pin from `wm_tools::profiles::surface_hash`) signed
//! with the node key lineage — the same Ed25519 `WM_MESH_KEY` convention
//! as record attestations (hex-decoded 32 bytes, domain-prefixed
//! byte-stable payload, lowercase hex). Key-lineage discipline follows
//! the S9/Q39 direction: [`ReleaseManifest::key_lineage`] names the
//! derivation in effect (`wm-record-attestation/v1` era today, i.e. the
//! mesh key hex-decoded; `wm/release-signing/v1` HKDF subkey once S9
//! rules it), so verifiers pin the era and old manifests keep verifying
//! against their recorded pubkey after any re-key.
//!
//! CI wiring (release.yml) is the operator's lane: the private key lives
//! in CI secrets, the manifest rides the release alongside SHA256SUMS,
//! and the release public key is pinned in `scripts/install.sh`. This
//! module is the sign/verify core plus tests; it mints no keys and reads
//! no environment — key custody stays out of the library by design.

use ed25519_dalek::{Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};

/// Domain prefix for every signed release payload. Cross-protocol
/// confusion is impossible by construction: a release signature can never
/// verify as a record attestation or mesh payload or vice versa, even
/// though the key material is shared by lineage.
pub const RELEASE_MANIFEST_DOMAIN: &str = "wm-release-manifest/v1";

/// Key-lineage value for manifests signed with today's convention: the
/// mesh key hex-decoded, exactly like record attestations. The
/// `wm/release-signing/v1` HKDF subkey replaces this string once S9
/// rules the derivation — verifiers match on the recorded value.
pub const KEY_LINEAGE_MESH_ERA: &str = "wm-record-attestation/v1-era (WM_MESH_KEY hex-decoded)";

/// One shipped artifact pinned by hash.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ReleaseArtifact {
    /// File name as published (e.g. `wm-x86_64-linux`).
    pub name: String,
    /// SHA-256 of the published bytes (lowercase hex, 64 chars).
    pub sha256_hex: String,
    /// Published size in bytes.
    pub bytes: u64,
}

/// Signed provenance for one release. Artifacts are sorted by name at
/// construction so the signing payload is byte-stable regardless of the
/// order the release job lists them.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ReleaseManifest {
    /// Manifest domain (always [`RELEASE_MANIFEST_DOMAIN`] at v1).
    pub domain: String,
    /// Package version of the release build.
    pub package_version: String,
    /// Git SHA the release was built from (`"unknown"` when unavailable).
    pub git_sha: String,
    /// Tool-surface pin (hex, see `wm_tools::profiles::surface_hash`).
    pub surface_hash: String,
    /// Artifacts sorted by name.
    pub artifacts: Vec<ReleaseArtifact>,
    /// Key-derivation descriptor (see [`KEY_LINEAGE_MESH_ERA`]).
    pub key_lineage: String,
    /// Signer public key (lowercase hex) — the lineage identity.
    pub public_key_hex: String,
    /// Ed25519 signature over [`release_payload`] (lowercase hex).
    pub signature_hex: String,
}

impl ReleaseManifest {
    /// Build an unsigned manifest. Artifacts are sorted by name for a
    /// byte-stable signing payload.
    #[must_use]
    pub fn new(
        package_version: &str,
        git_sha: &str,
        surface_hash: &str,
        artifacts: Vec<ReleaseArtifact>,
        key_lineage: &str,
    ) -> Self {
        let mut artifacts = artifacts;
        artifacts.sort_by(|a, b| a.name.cmp(&b.name));
        Self {
            domain: RELEASE_MANIFEST_DOMAIN.to_string(),
            package_version: package_version.to_string(),
            git_sha: git_sha.to_string(),
            surface_hash: surface_hash.to_string(),
            artifacts,
            key_lineage: key_lineage.to_string(),
            public_key_hex: String::new(),
            signature_hex: String::new(),
        }
    }
}

/// Canonical signed payload. Pipe-delimited fixed-order fields — no
/// canonical-JSON dependency, byte-stable by construction (same discipline
/// as [`crate::attestation::attestation_payload`]).
#[must_use]
pub fn release_payload(m: &ReleaseManifest) -> String {
    let mut out = format!(
        "{}|{}|{}|{}|{}|{}",
        RELEASE_MANIFEST_DOMAIN,
        m.package_version,
        m.git_sha,
        m.surface_hash,
        m.key_lineage,
        m.artifacts.len()
    );
    for a in &m.artifacts {
        out.push('|');
        out.push_str(&a.name);
        out.push(':');
        out.push_str(&a.sha256_hex);
        out.push(':');
        out.push_str(&a.bytes.to_string());
    }
    out
}

/// Sign a manifest with a 32-byte secret key (hex, node key lineage).
/// Returns the manifest with `public_key_hex` + `signature_hex` filled,
/// or `None` on bad key material. Pure function — CI-secret handling
/// lives at the call site (release job), never here.
#[must_use]
pub fn sign_release(m: &ReleaseManifest, secret_hex: &str) -> Option<ReleaseManifest> {
    let secret = decode_key_hex(secret_hex.trim())?;
    let signing = SigningKey::from_bytes(&secret);
    let sig = signing.sign(release_payload(m).as_bytes());
    Some(ReleaseManifest {
        public_key_hex: hex_of(&signing.verifying_key().to_bytes()),
        signature_hex: hex_of(&sig.to_bytes()),
        ..m.clone()
    })
}

/// Verify a manifest's signature against its recorded pubkey and payload.
/// Unsigned manifests (empty pubkey/signature) never verify.
#[must_use]
pub fn verify_release(m: &ReleaseManifest) -> bool {
    if m.domain != RELEASE_MANIFEST_DOMAIN {
        return false;
    }
    if m.public_key_hex.is_empty() || m.signature_hex.is_empty() {
        return false;
    }
    let payload = release_payload(m);
    let (Some(pk_bytes), Some(sig_bytes)) = (
        decode_key_hex(&m.public_key_hex),
        decode_sig_hex(&m.signature_hex),
    ) else {
        return false;
    };
    let Ok(pk) = VerifyingKey::from_bytes(&pk_bytes) else {
        return false;
    };
    let sig = ed25519_dalek::Signature::from_bytes(&sig_bytes);
    pk.verify(payload.as_bytes(), &sig).is_ok()
}

/// Decode 64-char hex into 32 bytes (mirrors `attestation::decode_key_hex`;
/// kept local so this module's security-critical decode is reviewable in
/// one file).
fn decode_key_hex(hex: &str) -> Option<[u8; 32]> {
    if hex.len() != 64 {
        return None;
    }
    let mut out = [0u8; 32];
    for (i, chunk) in hex.as_bytes().chunks_exact(2).enumerate() {
        out[i] = (hex_val(chunk[0])? << 4) | hex_val(chunk[1])?;
    }
    Some(out)
}

fn decode_sig_hex(hex: &str) -> Option<[u8; 64]> {
    if hex.len() != 128 {
        return None;
    }
    let mut out = [0u8; 64];
    for (i, chunk) in hex.as_bytes().chunks_exact(2).enumerate() {
        out[i] = (hex_val(chunk[0])? << 4) | hex_val(chunk[1])?;
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

fn hex_of(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        out.push(HEX[(b >> 4) as usize] as char);
        out.push(HEX[(b & 0x0f) as usize] as char);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // Non-live test key (64 hex chars → 32 bytes). Never a real node key.
    const TEST_KEY_HEX: &str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

    fn test_manifest() -> ReleaseManifest {
        ReleaseManifest::new(
            "9.0.0",
            "caf9a36",
            &"ab".repeat(32),
            vec![
                ReleaseArtifact {
                    name: "wm-x86_64-linux".to_string(),
                    sha256_hex: "cd".repeat(32),
                    bytes: 22_500_000,
                },
                ReleaseArtifact {
                    name: "wm-aarch64-macos".to_string(),
                    sha256_hex: "ef".repeat(32),
                    bytes: 21_000_000,
                },
            ],
            KEY_LINEAGE_MESH_ERA,
        )
    }

    #[test]
    fn sign_and_verify_roundtrip() {
        let signed = sign_release(&test_manifest(), TEST_KEY_HEX).expect("test key signs");
        assert_eq!(signed.public_key_hex.len(), 64);
        assert_eq!(signed.signature_hex.len(), 128);
        assert!(verify_release(&signed));
    }

    #[test]
    fn tampered_artifact_hash_fails() {
        let signed = sign_release(&test_manifest(), TEST_KEY_HEX).expect("test key signs");
        let mut tampered = signed;
        tampered.artifacts[0].sha256_hex = "00".repeat(32);
        assert!(!verify_release(&tampered));
    }

    #[test]
    fn tampered_version_or_pin_fails() {
        let signed = sign_release(&test_manifest(), TEST_KEY_HEX).expect("test key signs");
        let mut tampered = signed.clone();
        tampered.package_version = "9.0.1".to_string();
        assert!(!verify_release(&tampered));
        tampered = signed;
        tampered.surface_hash = "ff".repeat(32);
        assert!(!verify_release(&tampered));
    }

    #[test]
    fn unsigned_and_wrong_domain_never_verify() {
        assert!(!verify_release(&test_manifest()));
        let mut signed = sign_release(&test_manifest(), TEST_KEY_HEX).expect("test key signs");
        signed.domain = "wm-record-attestation/v1".to_string();
        assert!(
            !verify_release(&signed),
            "a release signature must never verify as another protocol's payload"
        );
    }

    #[test]
    fn bad_key_material_returns_none() {
        assert!(sign_release(&test_manifest(), "").is_none());
        assert!(sign_release(&test_manifest(), "xyz").is_none());
        assert!(sign_release(&test_manifest(), &"ab".repeat(31)).is_none());
    }

    #[test]
    fn artifact_order_normalized_for_stable_payload() {
        // `new()` sorts by name, so listing order at the call site never
        // moves the payload (or the signature over it).
        let forward = test_manifest();
        let mut backward_artifacts = forward.artifacts.clone();
        backward_artifacts.reverse();
        let backward = ReleaseManifest::new(
            "9.0.0",
            "caf9a36",
            &"ab".repeat(32),
            backward_artifacts,
            KEY_LINEAGE_MESH_ERA,
        );
        assert_eq!(release_payload(&forward), release_payload(&backward));
    }

    #[test]
    fn payload_vector_is_byte_stable() {
        let p1 = release_payload(&test_manifest());
        let p2 = release_payload(&test_manifest());
        assert_eq!(p1, p2);
        assert!(p1.starts_with("wm-release-manifest/v1|9.0.0|caf9a36|"));
    }
}
