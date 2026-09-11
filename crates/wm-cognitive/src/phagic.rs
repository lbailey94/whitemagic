//! Cognitive Phagic Digestion Coordinator.
//!
//! Integrates the Non-Destructive Phagic Digestive Cold-Storage subsystem
//! into WhiteMagic's cognitive consciousness architecture.
//!
//! # Philosophy: Non-Destructive Phagocytosis
//! the project's sacred rule: Phagic systems must NEVER delete anything.
//! As memories drift outward toward the outer rim of each galaxy due to
//! waning access, fading harmonic resonance, and elapsed age, the Phagic
//! Coordinator gently digests them into distilled thematic nodes in the hot
//! active tier while preserving the full original memories with bit-level
//! fidelity in cold storage.

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use wm_core::{Galaxy, Result};
use wm_memory::cold_storage::{
    ColdQuery, OuterRimFactors, PhagicConfig, PhagicDigestReport, PhagicDigester,
};
use wm_memory::{Memory, MemoryId, MemoryStore, SearchEngine};

/// Overall health and statistics of the phagic cold-storage subsystem.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PhagicHealthSnapshot {
    /// Total memories resting in cold storage across all galaxies.
    pub total_cold_memories: usize,
    /// Cold memories counted by galaxy.
    pub cold_by_galaxy: HashMap<String, usize>,
    /// Total uncompressed raw bytes archived.
    pub total_raw_bytes: usize,
    /// Total compressed cold bytes on disk.
    pub total_cold_bytes: usize,
    /// Net storage bytes saved via compression.
    pub bytes_saved: usize,
    /// Average compression ratio (cold bytes / raw bytes).
    pub average_compression_ratio: f32,
    /// Number of active thematic digest nodes currently in the hot tier.
    pub active_digest_nodes: usize,
}

/// Cognitive coordinator for phagic digestion and cold memory lifecycle management.
pub struct PhagicCognitiveCoordinator {
    digester: PhagicDigester,
}

impl Default for PhagicCognitiveCoordinator {
    fn default() -> Self {
        Self::new(PhagicConfig::default())
    }
}

impl PhagicCognitiveCoordinator {
    /// Create a new coordinator with custom phagic configuration.
    #[must_use]
    pub const fn new(config: PhagicConfig) -> Self {
        Self {
            digester: PhagicDigester::new(config),
        }
    }

    /// Access the underlying digester.
    #[must_use]
    pub const fn digester(&self) -> &PhagicDigester {
        &self.digester
    }

    /// Perform a non-destructive digestive sweep across all eligible memory galaxies.
    pub fn run_digest_sweep(
        &self,
        store: &MemoryStore,
        search: Option<&SearchEngine>,
    ) -> Result<Vec<PhagicDigestReport>> {
        self.digester.digest_all(store, search)
    }

    /// Perform a digestion pass on a specific galaxy.
    pub fn digest_galaxy(
        &self,
        store: &MemoryStore,
        search: Option<&SearchEngine>,
        galaxy: Galaxy,
    ) -> Result<PhagicDigestReport> {
        self.digester.digest_galaxy(store, search, galaxy)
    }

    /// Thaw a cold-stored memory back into the active hot tier.
    pub fn thaw_memory(
        &self,
        store: &MemoryStore,
        search: Option<&SearchEngine>,
        id: MemoryId,
    ) -> Result<Memory> {
        self.digester.thaw(store, search, id)
    }

    /// Retrieve a comprehensive health snapshot of cold storage.
    pub fn health_snapshot(&self, store: &MemoryStore) -> Result<PhagicHealthSnapshot> {
        let mut total_cold_memories = 0;
        let mut cold_by_galaxy = HashMap::new();
        let mut total_raw_bytes = 0;
        let mut total_cold_bytes = 0;

        for galaxy in Galaxy::all() {
            match galaxy {
                Galaxy::Substrate
                | Galaxy::Dharma
                | Galaxy::Karma
                | Galaxy::Embeddings
                | Galaxy::Associations => continue,
                _ => {}
            }
            let count = store.count_cold(Some(galaxy))?;
            if count > 0 {
                total_cold_memories += count;
                cold_by_galaxy.insert(galaxy.db_name().to_string(), count);
            }
        }

        // Query all cold records to compute bytes and ratios
        let all_summaries = store.query_cold_records(&ColdQuery {
            limit: 10_000,
            ..Default::default()
        })?;

        for summary in &all_summaries {
            total_raw_bytes += summary.uncompressed_size;
            total_cold_bytes += summary.compressed_size;
        }

        let bytes_saved = total_raw_bytes.saturating_sub(total_cold_bytes);
        let average_compression_ratio = if total_raw_bytes > 0 {
            total_cold_bytes as f32 / total_raw_bytes as f32
        } else {
            0.0
        };

        // Count active thematic digest nodes in the hot tier
        let mut active_digest_nodes = 0;
        for galaxy in Galaxy::all() {
            match galaxy {
                Galaxy::Substrate
                | Galaxy::Dharma
                | Galaxy::Karma
                | Galaxy::Embeddings
                | Galaxy::Associations => continue,
                _ => {}
            }
            if let Ok(mems) = store.scan(galaxy, 5_000) {
                for mem in mems {
                    if mem.metadata.tags.iter().any(|t| t == "phagic:digest") {
                        active_digest_nodes += 1;
                    }
                }
            }
        }

        Ok(PhagicHealthSnapshot {
            total_cold_memories,
            cold_by_galaxy,
            total_raw_bytes,
            total_cold_bytes,
            bytes_saved,
            average_compression_ratio,
            active_digest_nodes,
        })
    }

    /// Survey the outer-rim status of a galaxy without performing digestion.
    pub fn inspect_outer_rim(
        &self,
        store: &MemoryStore,
        galaxy: Galaxy,
    ) -> Result<Vec<(Memory, OuterRimFactors)>> {
        self.digester.scan_outer_rim(store, galaxy)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;
    use tempfile::tempdir;

    fn test_store() -> MemoryStore {
        let tmp = tempdir().unwrap();
        MemoryStore::open_default(tmp.path()).unwrap()
    }

    #[test]
    fn coordinator_health_snapshot_empty() {
        let store = test_store();
        let coord = PhagicCognitiveCoordinator::default();
        let health = coord.health_snapshot(&store).unwrap();

        assert_eq!(health.total_cold_memories, 0);
        assert_eq!(health.active_digest_nodes, 0);
        assert_eq!(health.bytes_saved, 0);
    }

    #[test]
    fn coordinator_digest_and_health_snapshot() {
        let store = test_store();
        let coord = PhagicCognitiveCoordinator::default();
        let galaxy = Galaxy::Codex;
        let now = Utc::now();

        // Add 2 distant memories
        for i in 1..=2 {
            let mut mem = Memory::new(
                galaxy,
                format!("Deep scientific treatise on non-destructive entropy reversal, volume {i}"),
            )
            .with_tags(vec!["physics".into(), "entropy".into()])
            .with_importance(0.02);
            mem.metadata.accessed_at = now - chrono::Duration::days(180);
            mem.metadata.access_count = 0;
            store.put(galaxy, &mem).unwrap();
        }

        let reports = coord.run_digest_sweep(&store, None).unwrap();
        assert!(!reports.is_empty());
        let codex_report = reports.iter().find(|r| r.galaxy == galaxy).unwrap();
        assert_eq!(codex_report.memories_digested, 2);

        let health = coord.health_snapshot(&store).unwrap();
        assert_eq!(health.total_cold_memories, 2);
        assert_eq!(health.active_digest_nodes, 1);
        assert!(health.total_raw_bytes > 0);
        assert!(health.total_cold_bytes > 0);
        assert!(health.bytes_saved > 0);
    }
}
