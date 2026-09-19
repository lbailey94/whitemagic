//! Persistent Memory wire compatibility.
//!
//! Commit 70495ef wrote a 30-field metadata sequence ending in revision_count.
//! Later validity/corroboration fields were inserted before that counter. Serde
//! defaults cannot repair shifted positional fields. Accept only that precise
//! historical sequence on fallback; never turn malformed modern validity into Active.
//! New writes use named fields so future additive fields cannot shift positions.

use crate::memory::{Memory, MemoryMetadata, MemoryType, Tier};
use chacha20poly1305::aead::{Aead, Payload};
use chacha20poly1305::{KeyInit, XChaCha20Poly1305, XNonce};
use chrono::{DateTime, Utc};
use serde::Deserialize;
use uuid::Uuid;
use wm_core::{Coordinate5D, Galaxy, HolographicCoords};
use zeroize::Zeroizing;

/// Magic prefix of a Q39 slice-B sealed record value.
pub const RECORD_MAGIC: [u8; 4] = *b"WMEN";

/// Envelope format version written after [`RECORD_MAGIC`].
pub const RECORD_FORMAT_VERSION: u8 = 1;

/// XChaCha20-Poly1305 nonce length.
pub const RECORD_NONCE_LEN: usize = 24;

/// Bytes before the ciphertext: magic + version byte + content version + nonce.
pub const RECORD_HEADER_LEN: usize = 4 + 1 + 8 + RECORD_NONCE_LEN;

/// Smallest well-formed sealed record (header + Poly1305 tag).
pub const RECORD_MIN_LEN: usize = RECORD_HEADER_LEN + 16;

const RECORD_AAD_INFO: &[u8] = b"wm/record-aead/v1";

/// Whether `bytes` carries the sealed-record magic. Our plaintext encodings
/// start with a msgpack array/map header, never `WMEN`, so this is
/// unambiguous for values this codec produces; an unknown future envelope
/// version still reaches [`open_record`] and fails closed there.
#[must_use]
pub fn is_sealed_record(bytes: &[u8]) -> bool {
    bytes.len() >= RECORD_MAGIC.len() && bytes[..RECORD_MAGIC.len()] == RECORD_MAGIC
}

/// AAD binding a record body to its galaxy, identity, and content version
/// (Q39 §2 ruling 1): `info || name_len || galaxy db name || record id ||
/// version`, lengths/fixed-width fields making the encoding injective.
#[must_use]
pub fn record_aad(galaxy_db_name: &str, record_id: &[u8; 16], version: u64) -> Vec<u8> {
    let name = galaxy_db_name.as_bytes();
    let mut aad = Vec::with_capacity(RECORD_AAD_INFO.len() + 2 + name.len() + 16 + 8);
    aad.extend_from_slice(RECORD_AAD_INFO);
    aad.extend_from_slice(&(name.len() as u16).to_le_bytes());
    aad.extend_from_slice(name);
    aad.extend_from_slice(record_id);
    aad.extend_from_slice(&version.to_le_bytes());
    aad
}

/// Sealed-record content version, when `blob` carries the envelope.
#[must_use]
pub fn sealed_record_version(blob: &[u8]) -> Option<u64> {
    if !is_sealed_record(blob) || blob.len() < RECORD_HEADER_LEN {
        return None;
    }
    let mut bytes = [0u8; 8];
    bytes.copy_from_slice(&blob[5..13]);
    Some(u64::from_le_bytes(bytes))
}

/// Seal a plaintext record body under the galaxy DEK. The content version
/// travels in the (AAD-bound) header so readers can rebuild the AAD before
/// decrypting.
#[must_use = "the sealed bytes are the value to store"]
pub fn seal_record(
    plaintext: &[u8],
    key: &[u8; 32],
    galaxy_db_name: &str,
    record_id: &[u8; 16],
    version: u64,
) -> Result<Vec<u8>, String> {
    let cipher = XChaCha20Poly1305::new(key.into());
    let mut nonce = [0u8; RECORD_NONCE_LEN];
    crate::at_rest::fill_random(&mut nonce).map_err(|e| format!("record seal entropy: {e}"))?;
    let aad = record_aad(galaxy_db_name, record_id, version);
    let ciphertext = cipher
        .encrypt(
            XNonce::from_slice(&nonce),
            Payload {
                msg: plaintext,
                aad: &aad,
            },
        )
        .map_err(|_| "record seal failed (AEAD error)".to_string())?;
    let mut out = Vec::with_capacity(RECORD_HEADER_LEN + ciphertext.len());
    out.extend_from_slice(&RECORD_MAGIC);
    out.push(RECORD_FORMAT_VERSION);
    out.extend_from_slice(&version.to_le_bytes());
    out.extend_from_slice(&nonce);
    out.extend_from_slice(&ciphertext);
    Ok(out)
}

/// Open a sealed record body for `galaxy_db_name`/`record_id`. Any wrong
/// key, wrong identity (transplanted ciphertext), bitflip, or truncation
/// fails closed.
pub fn open_record(
    blob: &[u8],
    key: &[u8; 32],
    galaxy_db_name: &str,
    record_id: &[u8; 16],
) -> Result<Zeroizing<Vec<u8>>, String> {
    if blob.len() < RECORD_MIN_LEN {
        return Err(format!(
            "sealed record is {} bytes (minimum {RECORD_MIN_LEN})",
            blob.len()
        ));
    }
    if !is_sealed_record(blob) {
        return Err("value does not carry the WMEN record envelope".to_string());
    }
    if blob[4] != RECORD_FORMAT_VERSION {
        return Err(format!(
            "unsupported record envelope version {} (expected {RECORD_FORMAT_VERSION})",
            blob[4]
        ));
    }
    let version = sealed_record_version(blob).expect("length checked above");
    let aad = record_aad(galaxy_db_name, record_id, version);
    let cipher = XChaCha20Poly1305::new(key.into());
    let nonce = XNonce::from_slice(&blob[13..RECORD_HEADER_LEN]);
    let plaintext = cipher
        .decrypt(
            nonce,
            Payload {
                msg: &blob[RECORD_HEADER_LEN..],
                aad: &aad,
            },
        )
        .map_err(|_| {
            "record open failed (wrong key, tampered ciphertext, or AAD mismatch)".to_string()
        })?;
    Ok(Zeroizing::new(plaintext))
}

pub fn decode(bytes: &[u8]) -> Result<Memory, rmp_serde::decode::Error> {
    match rmp_serde::from_slice(bytes) {
        Ok(memory) => Ok(memory),
        Err(original) => {
            // rmp-serde compact encoding: outer array(3), metadata array16(30).
            // Named maps and all other sequence shapes must retain the original
            // error rather than accidentally dropping a modern lifecycle state.
            if !bytes.starts_with(&[0x93, 0xdc, 0, 30]) {
                return Err(original);
            }
            let legacy: LegacyMemory = rmp_serde::from_slice(bytes)?;
            let m = legacy.metadata;
            Ok(Memory {
                metadata: MemoryMetadata {
                    id: m.id,
                    galaxy: m.galaxy,
                    content_hash: m.content_hash,
                    tags: m.tags,
                    importance: m.importance,
                    created_at: m.created_at,
                    accessed_at: m.accessed_at,
                    access_count: m.access_count,
                    coords: m.coords,
                    coord5d: m.coord5d,
                    memory_type: m.memory_type,
                    neuro_score: m.neuro_score,
                    novelty_score: m.novelty_score,
                    emotional_valence: m.emotional_valence,
                    emotional_weight: m.emotional_weight,
                    is_protected: m.is_protected,
                    is_private: m.is_private,
                    model_exclude: m.model_exclude,
                    source: m.source,
                    source_trust: m.source_trust,
                    half_life_days: m.half_life_days,
                    recall_count: m.recall_count,
                    version: m.version,
                    agent_id: m.agent_id,
                    title: m.title,
                    topic: m.topic,
                    tier: m.tier,
                    class: m.class,
                    dup_count: m.dup_count,
                    revision_count: m.revision_count,
                    validity: wm_core::episodic::ValidityState::Active,
                    corroborated_by: Vec::new(),
                },
                content: legacy.content,
                embedding: legacy.embedding,
            })
        }
    }
}

#[derive(Deserialize)]
#[cfg_attr(test, derive(serde::Serialize))]
struct LegacyMemory {
    metadata: LegacyMetadata,
    content: String,
    embedding: Option<Vec<f32>>,
}

// Frozen schema from 70495ef, in its original order. No defaults: fallback
// requires all 30 fields, including the revision counter and privacy flags.
#[derive(Deserialize)]
#[cfg_attr(test, derive(serde::Serialize))]
struct LegacyMetadata {
    id: Uuid,
    galaxy: Galaxy,
    content_hash: String,
    tags: Vec<String>,
    importance: f32,
    created_at: DateTime<Utc>,
    accessed_at: DateTime<Utc>,
    access_count: u64,
    coords: HolographicCoords,
    coord5d: Coordinate5D,
    memory_type: MemoryType,
    neuro_score: f32,
    novelty_score: f32,
    emotional_valence: f32,
    emotional_weight: f32,
    is_protected: bool,
    is_private: bool,
    model_exclude: bool,
    source: String,
    source_trust: f32,
    half_life_days: f32,
    recall_count: u64,
    version: u64,
    agent_id: String,
    title: Option<String>,
    topic: Option<String>,
    tier: Tier,
    class: Option<crate::typology::MemoryClass>,
    dup_count: u64,
    revision_count: u32,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::MemoryStore;
    use wm_core::episodic::ValidityState;

    fn legacy_bytes(memory: Memory) -> Vec<u8> {
        let m = memory.metadata;
        let legacy = LegacyMemory {
            metadata: LegacyMetadata {
                id: m.id,
                galaxy: m.galaxy,
                content_hash: m.content_hash,
                tags: m.tags,
                importance: m.importance,
                created_at: m.created_at,
                accessed_at: m.accessed_at,
                access_count: m.access_count,
                coords: m.coords,
                coord5d: m.coord5d,
                memory_type: m.memory_type,
                neuro_score: m.neuro_score,
                novelty_score: m.novelty_score,
                emotional_valence: m.emotional_valence,
                emotional_weight: m.emotional_weight,
                is_protected: m.is_protected,
                is_private: m.is_private,
                model_exclude: m.model_exclude,
                source: m.source,
                source_trust: m.source_trust,
                half_life_days: m.half_life_days,
                recall_count: m.recall_count,
                version: m.version,
                agent_id: m.agent_id,
                title: m.title,
                topic: m.topic,
                tier: m.tier,
                class: m.class,
                dup_count: m.dup_count,
                revision_count: m.revision_count,
            },
            content: memory.content,
            embedding: memory.embedding,
        };
        rmp_serde::to_vec(&legacy).unwrap()
    }

    #[test]
    fn legacy_s11_preserves_content_revision_and_privacy_without_rewriting() {
        let dir = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(dir.path()).unwrap();
        let mut mem = Memory::new(Galaxy::Sessions, "unchanged historical source".into());
        mem.metadata.revision_count = 7;
        mem.metadata.is_private = true;
        mem.metadata.model_exclude = true;
        mem.metadata.tags = vec!["historical".into()];
        let id = mem.metadata.id;
        let expected = serde_json::to_value(&mem).unwrap();
        let bytes = legacy_bytes(mem);
        assert!(rmp_serde::from_slice::<Memory>(&bytes).is_err());
        store
            .put_raw(Galaxy::Sessions, id.as_bytes(), &bytes)
            .unwrap();
        let read = store.get(Galaxy::Sessions, id).unwrap().unwrap();
        assert_eq!(serde_json::to_value(&read).unwrap(), expected);
        assert_eq!(store.scan_all(Galaxy::Sessions).unwrap().len(), 1);
        assert_eq!(
            store
                .get_raw(Galaxy::Sessions, id.as_bytes())
                .unwrap()
                .unwrap(),
            bytes
        );
        store.put(Galaxy::Sessions, &read).unwrap();
        let named = store
            .get_raw(Galaxy::Sessions, id.as_bytes())
            .unwrap()
            .unwrap();
        assert!(!named.starts_with(&[0x93]));
        assert_eq!(
            serde_json::to_value(decode(&named).unwrap()).unwrap(),
            expected
        );
    }

    #[test]
    fn modern_validity_is_preserved_in_both_encodings() {
        for state in [
            ValidityState::Active,
            ValidityState::Archived,
            ValidityState::Erased,
            ValidityState::Revoked {
                reason: "withdrawn".into(),
            },
            ValidityState::Superseded { by: Uuid::new_v4() },
        ] {
            let mut mem = Memory::new(Galaxy::Codex, "modern source".into());
            mem.metadata.validity = state;
            mem.metadata.corroborated_by = vec![Uuid::new_v4()];
            for bytes in [
                rmp_serde::to_vec(&mem).unwrap(),
                rmp_serde::to_vec_named(&mem).unwrap(),
            ] {
                assert_eq!(
                    serde_json::to_value(decode(&bytes).unwrap()).unwrap(),
                    serde_json::to_value(&mem).unwrap()
                );
            }
        }
    }

    #[test]
    fn invalid_modern_validity_and_truncated_legacy_fail_closed() {
        let mem = Memory::new(Galaxy::Codex, "source".into());
        let bytes = legacy_bytes(mem.clone());
        assert!(decode(&bytes[..bytes.len() - 1]).is_err());
        let mut modern = serde_json::to_value(mem).unwrap();
        modern["metadata"]["validity"] = serde_json::json!(0);
        assert!(decode(&rmp_serde::to_vec_named(&modern).unwrap()).is_err());
    }

    fn seal_memory(memory: &Memory, key: &[u8; 32]) -> (Vec<u8>, Vec<u8>) {
        let plaintext = rmp_serde::to_vec_named(memory).unwrap();
        let sealed = seal_record(
            &plaintext,
            key,
            memory.metadata.galaxy.db_name(),
            memory.metadata.id.as_bytes(),
            memory.metadata.version,
        )
        .unwrap();
        (plaintext, sealed)
    }

    fn open_memory(
        blob: &[u8],
        memory: &Memory,
        key: &[u8; 32],
    ) -> Result<Zeroizing<Vec<u8>>, String> {
        open_record(
            blob,
            key,
            memory.metadata.galaxy.db_name(),
            memory.metadata.id.as_bytes(),
        )
    }

    #[test]
    fn sealed_record_roundtrips_and_is_detected() {
        let key = [7u8; 32];
        let mut mem = Memory::new(Galaxy::Codex, "sealed content".into());
        mem.metadata.version = 3;
        let (plaintext, sealed) = seal_memory(&mem, &key);

        assert!(!is_sealed_record(&plaintext));
        assert!(is_sealed_record(&sealed));
        assert_eq!(&sealed[..4], b"WMEN");
        assert_eq!(sealed[4], RECORD_FORMAT_VERSION);
        assert_eq!(sealed_record_version(&sealed), Some(3));

        let opened = open_memory(&sealed, &mem, &key).unwrap();
        assert_eq!(&opened[..], plaintext.as_slice());
        assert_eq!(
            serde_json::to_value(decode(&opened).unwrap()).unwrap(),
            serde_json::to_value(&mem).unwrap()
        );
        assert!(!is_sealed_record(&opened));
    }

    #[test]
    fn sealed_record_rejects_wrong_key_tamper_and_truncation() {
        let key = [7u8; 32];
        let mem = Memory::new(Galaxy::Codex, "hostile weather".into());
        let (_, sealed) = seal_memory(&mem, &key);

        let wrong_key = [8u8; 32];
        assert!(open_memory(&sealed, &mem, &wrong_key).is_err());

        let mut flipped = sealed.clone();
        let last = flipped.len() - 1;
        flipped[last] ^= 0x01;
        assert!(open_memory(&flipped, &mem, &key).is_err());

        let truncated = &sealed[..sealed.len() - 1];
        assert!(open_memory(truncated, &mem, &key).is_err());

        let mut bad_version = sealed.clone();
        bad_version[4] = 9;
        assert!(open_memory(&bad_version, &mem, &key).is_err());

        let mut header_version_flip = sealed.clone();
        header_version_flip[5] ^= 0x01;
        assert!(open_memory(&header_version_flip, &mem, &key).is_err());

        let plaintext = rmp_serde::to_vec_named(&mem).unwrap();
        assert!(open_memory(&plaintext, &mem, &key).is_err());
    }

    #[test]
    fn sealed_record_refuses_transplanted_identity() {
        let key = [7u8; 32];
        let mem = Memory::new(Galaxy::Codex, "bound to place".into());
        let (_, sealed) = seal_memory(&mem, &key);
        let id = mem.metadata.id.as_bytes();

        assert!(open_memory(&sealed, &mem, &key).is_ok());
        assert!(
            open_record(&sealed, &key, "sessions", id).is_err(),
            "ciphertext moved to another galaxy must fail"
        );
        let other_id = *Uuid::new_v4().as_bytes();
        assert!(
            open_record(&sealed, &key, mem.metadata.galaxy.db_name(), &other_id).is_err(),
            "ciphertext moved to another record id must fail"
        );
    }

    #[test]
    fn record_aad_is_injective_across_name_boundaries() {
        let id = *Uuid::new_v4().as_bytes();
        assert_ne!(record_aad("a", &id, 1), record_aad("ab", &id, 1));
        assert_ne!(record_aad("codex", &id, 1), record_aad("codex", &id, 2));
        assert_eq!(record_aad("codex", &id, 1), record_aad("codex", &id, 1));
    }
}
