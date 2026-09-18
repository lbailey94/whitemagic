//! HKDF-SHA256 derivation for domain-separated subkeys (S9 x Q39).
//!
//! One root (the node key material) fans out into purpose-scoped subkeys;
//! subkeys never cross-derive. The info strings are versioned and ruled in
//! `docs/Q39_CRYPTO_ERASURE_DESIGN.md` §2 and
//! `docs/S9_SECURITY_BRIEF_2026-09-10.md` §2.1 — do not invent new strings
//! without updating both.

#![forbid(unsafe_code)]

/// Mesh node identity subkey (`wm/mesh-identity/v1`).
pub const MESH_IDENTITY_INFO: &str = "wm/mesh-identity/v1";

/// Record-attestation signer subkey (`wm/record-attestation/v1`).
pub const RECORD_ATTESTATION_INFO: &str = "wm/record-attestation/v1";

/// Galaxy DEK-wrap KEK info-string prefix (`wm/galaxy-dek/v1`, Q39 §2/§3).
///
/// One KEK per galaxy derives from the store root key as
/// `hkdf32(rk, galaxy_dek_info(<galaxy-db-name>))`; the full info string is
/// also the wrapping AEAD's AAD, so a wrapped DEK cannot be transplanted
/// between galaxies. Declared in `docs/Q39_CRYPTO_ERASURE_DESIGN.md`.
pub const GALAXY_DEK_INFO_PREFIX: &str = "wm/galaxy-dek/v1";

/// Info string (and AEAD AAD) binding a galaxy DEK wrap to its galaxy:
/// `wm/galaxy-dek/v1/<galaxy-db-name>`.
#[must_use]
pub fn galaxy_dek_info(galaxy_db_name: &str) -> String {
    format!("{GALAXY_DEK_INFO_PREFIX}/{galaxy_db_name}")
}

/// Release-artifact signing subkey (`wm/release-signing/v1`) — reserved, not yet wired.
///
/// The CI release manifest still signs with the hex-decoded lineage key and
/// records that in `key_lineage`; do not switch it on without the
/// release-side migration.
pub const RELEASE_SIGNING_INFO: &str = "wm/release-signing/v1";

/// HKDF-SHA256: derive 32 bytes from root material with a versioned info string.
///
/// `salt = None` (RFC 5869 permits an all-zero salt; the root material is
/// high-entropy and per-node).
#[must_use]
pub fn hkdf32(root: &[u8], info: &str) -> [u8; 32] {
    let mut out = [0u8; 32];
    expand(root, info, &mut out);
    out
}

/// HKDF-SHA256 expand into a caller-provided buffer (for non-32-byte outputs).
///
/// # Panics
///
/// Panics when `okm` exceeds the HKDF-SHA256 maximum (`255 * 32` bytes).
pub fn expand(root: &[u8], info: &str, okm: &mut [u8]) {
    let hk = hkdf::Hkdf::<sha2::Sha256>::new(None, root);
    hk.expand(info.as_bytes(), okm)
        .expect("HKDF-SHA256 output length must be <= 255*32 bytes");
}

/// Canonical root material from an environment/config value (S9 §2.1).
///
/// A 64-hex-char key is decoded to its 32 canonical bytes; anything else is
/// used raw so legacy/test material keeps a stable identity. The mesh
/// identity and the record-attestation subkey derive from the same canonical
/// root; purpose APIs may additionally require canonical material (record
/// attestations derive only from a 64-hex root — an honest negative, never an
/// off-contract root).
#[must_use]
pub fn root_bytes(material: &str) -> Vec<u8> {
    let trimmed = material.trim();
    if trimmed.len() == 64 {
        if let Some(decoded) = decode_hex32(trimmed) {
            return decoded.to_vec();
        }
    }
    material.as_bytes().to_vec()
}

fn decode_hex32(hex: &str) -> Option<[u8; 32]> {
    if hex.len() != 64 {
        return None;
    }
    let mut out = [0u8; 32];
    for (i, chunk) in hex.as_bytes().chunks_exact(2).enumerate() {
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

#[cfg(test)]
mod tests {
    use super::*;

    fn hex(bytes: &[u8]) -> String {
        const HEX: &[u8; 16] = b"0123456789abcdef";
        let mut out = String::with_capacity(bytes.len() * 2);
        for b in bytes {
            out.push(HEX[(b >> 4) as usize] as char);
            out.push(HEX[(b & 0x0f) as usize] as char);
        }
        out
    }

    #[test]
    fn rfc5869_test_case_1_is_reproduced() {
        // RFC 5869 A.1 — pins the underlying HKDF-SHA256 implementation.
        let ikm = [0x0b; 22];
        let salt: [u8; 13] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
        let info: [u8; 10] = [0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8, 0xf9];
        let hk = hkdf::Hkdf::<sha2::Sha256>::new(Some(&salt), &ikm);
        let mut okm = [0u8; 42];
        hk.expand(&info, &mut okm).unwrap();
        assert_eq!(
            hex(&okm),
            "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf\
             34007208d5b887185865"
        );
    }

    #[test]
    fn derivation_is_deterministic_and_domain_separated() {
        let root = b"node-root-material-0123456789";
        let mesh_a = hkdf32(root, MESH_IDENTITY_INFO);
        let mesh_b = hkdf32(root, MESH_IDENTITY_INFO);
        assert_eq!(
            mesh_a, mesh_b,
            "same root + info must derive the same subkey"
        );

        let attestation = hkdf32(root, RECORD_ATTESTATION_INFO);
        assert_ne!(
            mesh_a, attestation,
            "mesh identity and attestation subkeys must never collide"
        );
        assert_ne!(mesh_a, hkdf32(root, "wm/beacon/v1"));
        assert_ne!(mesh_a, hkdf32(b"another-root", MESH_IDENTITY_INFO));
    }

    #[test]
    fn galaxy_dek_info_is_versioned_and_per_galaxy() {
        assert_eq!(galaxy_dek_info("codex"), "wm/galaxy-dek/v1/codex");
        assert_eq!(
            galaxy_dek_info("codex"),
            format!("{GALAXY_DEK_INFO_PREFIX}/codex")
        );
        assert_ne!(galaxy_dek_info("codex"), galaxy_dek_info("sessions"));
        assert_ne!(
            galaxy_dek_info("codex"),
            RECORD_ATTESTATION_INFO,
            "DEK wrapping must never share purpose space with signers"
        );
    }

    #[test]
    fn expand_writes_only_the_requested_length() {
        let root = b"short-root";
        let mut out = [0xAAu8; 64];
        expand(root, MESH_IDENTITY_INFO, &mut out[..16]);
        assert_eq!(
            &out[16..],
            [0xAA; 48],
            "bytes past the output length untouched"
        );
    }

    #[test]
    fn root_material_is_canonical_hex_decode_with_raw_fallback() {
        let hex_key = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff";
        let decoded = root_bytes(hex_key);
        assert_eq!(decoded.len(), 32);
        assert_eq!(decoded[0], 0x00);
        assert_eq!(decoded[3], 0x33);
        assert_eq!(
            hkdf32(&decoded, MESH_IDENTITY_INFO),
            hkdf32(&root_bytes(hex_key), MESH_IDENTITY_INFO),
            "same env material must always derive the same subkey"
        );
        assert_ne!(
            decoded.as_slice(),
            hex_key.as_bytes(),
            "64-hex is decoded, not used as ASCII"
        );

        assert_eq!(root_bytes("legacy-or-test-key"), b"legacy-or-test-key");
        let invalid_64 = "z".repeat(64);
        assert_eq!(
            root_bytes(&invalid_64),
            invalid_64.as_bytes(),
            "64 chars that are not hex fall back to raw bytes"
        );
    }
}
