//! Persistent Memory wire compatibility.
//!
//! Commit 70495ef wrote a 30-field metadata sequence ending in revision_count.
//! Later validity/corroboration fields were inserted before that counter. Serde
//! defaults cannot repair shifted positional fields. Accept only that precise
//! historical sequence on fallback; never turn malformed modern validity into Active.
//! New writes use named fields so future additive fields cannot shift positions.

use crate::memory::{Memory, MemoryMetadata, MemoryType, Tier};
use chrono::{DateTime, Utc};
use serde::Deserialize;
use uuid::Uuid;
use wm_core::{Coordinate5D, Galaxy, HolographicCoords};

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
}
