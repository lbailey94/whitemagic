//! Per-memory revision chain (V8 S11c) — tamper-evident content history.
//!
//! Every `memory.update` that changes content appends one revision entry
//! to the `revisions` DBI, keyed `rev:{galaxy}:{memory_id}:{seq}`. The
//! chain is *self-verifying by construction*:
//!
//! - `seq` is continuous (gaps prove deletion);
//! - `entry[n].new_hash == entry[n+1].old_hash` (breaks prove splicing);
//! - the last `new_hash` must equal the memory's current `content_hash`
//!   (mismatch proves an out-of-band rewrite).
//!
//! Entries carry hashes, not full content — cheap local tamper-*evidence*
//! (recovery of old text rides `wm backup`). The chain hashes nothing of
//! its own; it needs no keys and no crypto infrastructure, and it detects
//! the exact rewrite class the write-audit journal cannot see: edits that
//! are declared, journaled, and still leave no record of what was there
//! before.

use serde::{Deserialize, Serialize};
use wm_core::Galaxy;

use crate::memory::MemoryId;

/// One content revision of a memory — appended on every content change.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct MemoryRevision {
    /// 0-based position in this memory's revision chain.
    pub seq: u32,
    /// Unix timestamp (seconds) of the update dispatch.
    pub timestamp: u64,
    /// Content hash immediately before the change.
    pub old_hash: String,
    /// Content hash immediately after the change.
    pub new_hash: String,
    /// Attributed actor session (WM session id), when the dispatch ran
    /// inside one.
    #[serde(default)]
    pub actor_session: Option<String>,
    /// Attributed actor user label from MCP `_meta` (client-asserted).
    #[serde(default)]
    pub actor_user: Option<String>,
}

/// Who performed a revision — snapshotted from the dispatch context.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RevisionActor {
    pub session: Option<String>,
    pub user: Option<String>,
}

/// Result of walking one memory's revision chain.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RevisionChainReport {
    pub entries: usize,
    /// False when the chain has internal breaks (seq gaps, hash-linkage
    /// splices) or the head hash does not match the live content hash.
    pub valid: bool,
    /// Human-readable break descriptions; empty when valid.
    pub breaks: Vec<String>,
    /// The last entry's `new_hash` equals the memory's current
    /// `content_hash` (vacuously true for a memory with no revisions).
    pub matches_head: bool,
}

/// Verify a revision chain against the memory's current content hash.
#[must_use]
pub fn verify_chain(entries: &[MemoryRevision], current_hash: &str) -> RevisionChainReport {
    let mut breaks = Vec::new();
    for (i, entry) in entries.iter().enumerate() {
        if entry.seq != i as u32 {
            breaks.push(format!(
                "seq discontinuity at position {i}: expected {i}, found {}",
                entry.seq
            ));
        }
        if i > 0 {
            let prev = &entries[i - 1];
            if prev.new_hash != entry.old_hash {
                breaks.push(format!(
                    "hash-linkage break at seq {}: prev new_hash != entry old_hash",
                    entry.seq
                ));
            }
        }
    }
    let matches_head = match entries.last() {
        None => true,
        Some(last) => last.new_hash == current_hash,
    };
    if !matches_head {
        breaks.push(
            "head mismatch: last revision new_hash != current memory content_hash".to_string(),
        );
    }
    RevisionChainReport {
        entries: entries.len(),
        valid: breaks.is_empty(),
        breaks,
        matches_head,
    }
}

/// LMDB key for one revision: `rev:{galaxy}:{memory_id}:{seq:010}`.
/// Zero-padded seq keeps lexicographic order == numeric order.
#[must_use]
pub fn revision_key(galaxy: Galaxy, id: MemoryId, seq: u32) -> Vec<u8> {
    format!("rev:{}:{}:{seq:010}", galaxy.db_name(), id).into_bytes()
}

/// Key prefix covering every revision of one memory (for range scans).
#[must_use]
pub fn revision_prefix(galaxy: Galaxy, id: MemoryId) -> Vec<u8> {
    format!("rev:{}:{}:", galaxy.db_name(), id).into_bytes()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rev(seq: u32, old_hash: &str, new_hash: &str) -> MemoryRevision {
        MemoryRevision {
            seq,
            timestamp: 1_700_000_000,
            old_hash: old_hash.to_string(),
            new_hash: new_hash.to_string(),
            actor_session: Some("ses-1".to_string()),
            actor_user: None,
        }
    }

    #[test]
    fn intact_chain_is_valid() {
        let entries = vec![rev(0, "h0", "h1"), rev(1, "h1", "h2"), rev(2, "h2", "h3")];
        let report = verify_chain(&entries, "h3");
        assert!(report.valid, "{:?}", report.breaks);
        assert!(report.matches_head);
        assert_eq!(report.entries, 3);
    }

    #[test]
    fn deleted_entry_breaks_seq_continuity() {
        let entries = vec![rev(0, "h0", "h1"), rev(2, "h1", "h3")];
        let report = verify_chain(&entries, "h3");
        assert!(!report.valid);
        assert!(
            report
                .breaks
                .iter()
                .any(|b| b.contains("seq discontinuity"))
        );
    }

    #[test]
    fn spliced_entry_breaks_hash_linkage() {
        // An attacker rewrites entry 0's old_hash; linkage to the (removed)
        // prehistory breaks, and the splice is visible even though seq runs
        // continuously.
        let mut entries = vec![rev(0, "h0", "h1"), rev(1, "h1", "h2")];
        entries[0].new_hash = "forged".to_string();
        let report = verify_chain(&entries, "h2");
        assert!(!report.valid);
        assert!(report.breaks.iter().any(|b| b.contains("hash-linkage")));
    }

    #[test]
    fn out_of_band_rewrite_breaks_head_match() {
        let entries = vec![rev(0, "h0", "h1")];
        let report = verify_chain(&entries, "h_undisclosed_edit");
        assert!(!report.valid);
        assert!(!report.matches_head);
        assert!(report.breaks.iter().any(|b| b.contains("head mismatch")));
    }

    #[test]
    fn empty_chain_is_vacuously_valid() {
        let report = verify_chain(&[], "anything");
        assert!(report.valid);
        assert!(report.matches_head);
        assert_eq!(report.entries, 0);
    }

    #[test]
    fn keys_sort_numerically() {
        let id = MemoryId::nil();
        let mut keys: Vec<Vec<u8>> = (0..12u32)
            .map(|s| revision_key(Galaxy::Codex, id, s))
            .collect();
        keys.sort();
        for (i, key) in keys.iter().enumerate() {
            assert!(String::from_utf8_lossy(key).ends_with(&format!("{i:010}")));
        }
        assert!(revision_prefix(Galaxy::Codex, id).starts_with(b"rev:"));
    }
}
