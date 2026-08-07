//! Holographic coordinate sync — share and merge holographic coordinates
//! across nodes for federated memory.

#![forbid(unsafe_code)]

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::peer::PeerId;

// ── Hologram Entry ────────────────────────────────────────────────────

/// A holographic coordinate entry shared across the mesh.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HologramEntry {
    /// Content hash (unique identifier for the content).
    pub content_hash: String,
    /// 4D holographic coordinates (r, theta, phi, t).
    pub coords: [f32; 4],
    /// Importance score (0.0–1.0).
    pub importance: f32,
    /// Source peer that created this entry.
    pub source: PeerId,
    /// Timestamp (Unix seconds).
    pub timestamp: i64,
}

impl HologramEntry {
    /// Create a new hologram entry.
    #[must_use]
    pub fn new(
        content_hash: impl Into<String>,
        coords: [f32; 4],
        importance: f32,
        source: impl Into<String>,
    ) -> Self {
        Self {
            content_hash: content_hash.into(),
            coords,
            importance,
            source: source.into(),
            timestamp: chrono::Utc::now().timestamp(),
        }
    }

    /// Distance to another entry in 4D space.
    #[must_use]
    pub fn distance_to(&self, other: &Self) -> f32 {
        let dx = self.coords[0] - other.coords[0];
        let dy = self.coords[1] - other.coords[1];
        let dz = self.coords[2] - other.coords[2];
        let dt = self.coords[3] - other.coords[3];
        dt.mul_add(dt, dz.mul_add(dz, dx.mul_add(dx, dy * dy)))
            .sqrt()
    }
}

// ── Constellation Merge ───────────────────────────────────────────────

/// Result of merging two constellations.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConstellationMerge {
    /// Number of entries from the local constellation.
    pub local_count: usize,
    /// Number of entries from the remote constellation.
    pub remote_count: usize,
    /// Number of entries merged (shared content hashes).
    pub merged_count: usize,
    /// Number of new entries added from remote.
    pub new_from_remote: usize,
    /// Number of conflicts resolved.
    pub conflicts_resolved: usize,
}

impl ConstellationMerge {
    /// Whether this was a clean merge (no conflicts).
    #[must_use]
    pub const fn is_clean(&self) -> bool {
        self.conflicts_resolved == 0
    }
}

// ── Hologram Sync ─────────────────────────────────────────────────────

/// Holographic coordinate synchronization — shares and merges holographic
/// coordinates across nodes for federated memory.
///
/// Conflict resolution is importance-weighted and timestamp-based:
/// - If remote has higher importance, remote wins.
/// - If importance is equal, newer timestamp wins.
pub struct HologramSync {
    /// Local hologram entries keyed by content hash.
    entries: HashMap<String, HologramEntry>,
    /// Total syncs performed.
    total_syncs: u64,
    /// Total entries merged.
    total_merged: u64,
    /// Total conflicts resolved.
    total_conflicts: u64,
}

impl Default for HologramSync {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Debug for HologramSync {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("HologramSync")
            .field("entries", &self.entries.len())
            .field("total_syncs", &self.total_syncs)
            .finish_non_exhaustive()
    }
}

impl HologramSync {
    /// Create a new hologram sync manager.
    #[must_use]
    pub fn new() -> Self {
        Self {
            entries: HashMap::new(),
            total_syncs: 0,
            total_merged: 0,
            total_conflicts: 0,
        }
    }

    /// Add a local entry.
    pub fn add_local(&mut self, entry: HologramEntry) {
        self.entries.insert(entry.content_hash.clone(), entry);
    }

    /// Get an entry by content hash.
    #[must_use]
    pub fn get(&self, content_hash: &str) -> Option<&HologramEntry> {
        self.entries.get(content_hash)
    }

    /// Number of entries.
    #[must_use]
    pub fn entry_count(&self) -> usize {
        self.entries.len()
    }

    /// Find entries near a given coordinate within a radius.
    #[must_use]
    pub fn nearby(&self, coords: &[f32; 4], radius: f32) -> Vec<&HologramEntry> {
        let probe = HologramEntry::new("probe", *coords, 0.0, "system");
        self.entries
            .values()
            .filter(|e| e.distance_to(&probe) <= radius)
            .collect()
    }

    /// Merge a remote constellation into the local one.
    /// Returns the merge result.
    pub fn merge(&mut self, remote: Vec<HologramEntry>) -> ConstellationMerge {
        self.total_syncs += 1;
        let local_count = self.entries.len();
        let remote_count = remote.len();
        let mut merged: usize = 0;
        let mut new_from_remote: usize = 0;
        let mut conflicts: usize = 0;

        for entry in remote {
            if let Some(existing) = self.entries.get(&entry.content_hash) {
                // Conflict — resolve by importance, then timestamp
                merged += 1;
                if entry.importance > existing.importance
                    || (entry.importance == existing.importance
                        && entry.timestamp > existing.timestamp)
                {
                    self.entries.insert(entry.content_hash.clone(), entry);
                    conflicts += 1;
                }
            } else {
                // New entry from remote
                self.entries.insert(entry.content_hash.clone(), entry);
                new_from_remote += 1;
            }
        }

        self.total_merged += merged as u64;
        self.total_conflicts += conflicts as u64;

        ConstellationMerge {
            local_count,
            remote_count,
            merged_count: merged,
            new_from_remote,
            conflicts_resolved: conflicts,
        }
    }

    /// Export all entries for sharing with other nodes.
    #[must_use]
    pub fn export(&self) -> Vec<HologramEntry> {
        self.entries.values().cloned().collect()
    }

    /// Total syncs performed.
    #[must_use]
    pub const fn total_syncs(&self) -> u64 {
        self.total_syncs
    }

    /// Total entries merged.
    #[must_use]
    pub const fn total_merged(&self) -> u64 {
        self.total_merged
    }

    /// Total conflicts resolved.
    #[must_use]
    pub const fn total_conflicts(&self) -> u64 {
        self.total_conflicts
    }

    /// Get a JSON summary.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "entry_count": self.entries.len(),
            "total_syncs": self.total_syncs,
            "total_merged": self.total_merged,
            "total_conflicts": self.total_conflicts,
        })
    }

    /// Clear all entries.
    pub fn clear(&mut self) {
        self.entries.clear();
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_and_get() {
        let mut hs = HologramSync::new();
        let entry = HologramEntry::new("hash1", [1.0, 0.0, 0.0, 0.0], 0.8, "node-1");
        hs.add_local(entry);

        assert_eq!(hs.entry_count(), 1);
        assert!(hs.get("hash1").is_some());
        assert!(hs.get("hash2").is_none());
    }

    #[test]
    fn distance_to() {
        let e1 = HologramEntry::new("h1", [0.0, 0.0, 0.0, 0.0], 0.5, "n1");
        let e2 = HologramEntry::new("h2", [3.0, 4.0, 0.0, 0.0], 0.5, "n1");
        assert!((e1.distance_to(&e2) - 5.0).abs() < 0.001);
    }

    #[test]
    fn nearby_entries() {
        let mut hs = HologramSync::new();
        hs.add_local(HologramEntry::new("h1", [0.0, 0.0, 0.0, 0.0], 0.5, "n1"));
        hs.add_local(HologramEntry::new("h2", [1.0, 0.0, 0.0, 0.0], 0.5, "n1"));
        hs.add_local(HologramEntry::new("h3", [10.0, 0.0, 0.0, 0.0], 0.5, "n1"));

        let near = hs.nearby(&[0.0, 0.0, 0.0, 0.0], 2.0);
        assert_eq!(near.len(), 2);
    }

    #[test]
    fn merge_new_entries() {
        let mut hs = HologramSync::new();
        hs.add_local(HologramEntry::new("h1", [0.0, 0.0, 0.0, 0.0], 0.5, "n1"));

        let remote = vec![
            HologramEntry::new("h2", [1.0, 0.0, 0.0, 0.0], 0.5, "n2"),
            HologramEntry::new("h3", [2.0, 0.0, 0.0, 0.0], 0.5, "n2"),
        ];

        let result = hs.merge(remote);
        assert_eq!(result.new_from_remote, 2);
        assert_eq!(result.merged_count, 0);
        assert!(result.is_clean());
        assert_eq!(hs.entry_count(), 3);
    }

    #[test]
    fn merge_conflict_higher_importance_wins() {
        let mut hs = HologramSync::new();
        hs.add_local(HologramEntry::new("h1", [0.0, 0.0, 0.0, 0.0], 0.5, "n1"));

        let remote = vec![HologramEntry::new("h1", [1.0, 0.0, 0.0, 0.0], 0.9, "n2")];

        let result = hs.merge(remote);
        assert_eq!(result.conflicts_resolved, 1);
        assert!(!result.is_clean());

        let entry = hs.get("h1").unwrap();
        assert_eq!(entry.source, "n2");
        assert!((entry.importance - 0.9).abs() < 0.001);
    }

    #[test]
    fn merge_conflict_newer_timestamp_wins() {
        let mut hs = HologramSync::new();
        hs.add_local(HologramEntry::new("h1", [0.0, 0.0, 0.0, 0.0], 0.5, "n1"));

        let mut remote_entry = HologramEntry::new("h1", [1.0, 0.0, 0.0, 0.0], 0.5, "n2");
        remote_entry.timestamp = chrono::Utc::now().timestamp() + 100;

        let result = hs.merge(vec![remote_entry]);
        assert_eq!(result.conflicts_resolved, 1);

        let entry = hs.get("h1").unwrap();
        assert_eq!(entry.source, "n2");
    }

    #[test]
    fn merge_lower_importance_kept_local() {
        let mut hs = HologramSync::new();
        hs.add_local(HologramEntry::new("h1", [0.0, 0.0, 0.0, 0.0], 0.9, "n1"));

        let remote = vec![HologramEntry::new("h1", [1.0, 0.0, 0.0, 0.0], 0.3, "n2")];

        let result = hs.merge(remote);
        assert_eq!(result.conflicts_resolved, 0); // No conflict — local wins

        let entry = hs.get("h1").unwrap();
        assert_eq!(entry.source, "n1");
    }

    #[test]
    fn export_all() {
        let mut hs = HologramSync::new();
        hs.add_local(HologramEntry::new("h1", [0.0, 0.0, 0.0, 0.0], 0.5, "n1"));
        hs.add_local(HologramEntry::new("h2", [1.0, 0.0, 0.0, 0.0], 0.5, "n1"));

        let exported = hs.export();
        assert_eq!(exported.len(), 2);
    }

    #[test]
    fn clear() {
        let mut hs = HologramSync::new();
        hs.add_local(HologramEntry::new("h1", [0.0, 0.0, 0.0, 0.0], 0.5, "n1"));
        hs.clear();
        assert_eq!(hs.entry_count(), 0);
    }

    #[test]
    fn summary() {
        let mut hs = HologramSync::new();
        hs.add_local(HologramEntry::new("h1", [0.0, 0.0, 0.0, 0.0], 0.5, "n1"));
        hs.merge(vec![HologramEntry::new(
            "h2",
            [1.0, 0.0, 0.0, 0.0],
            0.5,
            "n2",
        )]);

        let summary = hs.summary();
        assert_eq!(summary["entry_count"], 2);
        assert_eq!(summary["total_syncs"], 1);
    }

    #[test]
    fn total_stats_tracked() {
        let mut hs = HologramSync::new();
        hs.add_local(HologramEntry::new("h1", [0.0, 0.0, 0.0, 0.0], 0.5, "n1"));
        hs.merge(vec![HologramEntry::new(
            "h1",
            [1.0, 0.0, 0.0, 0.0],
            0.9,
            "n2",
        )]);

        assert_eq!(hs.total_syncs(), 1);
        assert_eq!(hs.total_merged(), 1);
        assert_eq!(hs.total_conflicts(), 1);
    }
}
