//! WhiteMagic Gen3 — Tacit Continuity Vault Miner (DIR-08)
//!
//! Sub-symbolic cyberbrain indexing 1,389 sessions, 132,090 messages from opencode.db
//! into an associative query graph and System 0.5 Model2Vec static vector index.

pub mod schema;
pub mod extractor;
pub mod chunker;
pub mod embedder;
pub mod graph;
pub mod retrieval;
pub mod shm_bridge;
pub mod daemon;
pub mod cold_storage;

pub use retrieval::TacitVaultEngine;
pub use cold_storage::ColdStorageEngine;

/// Truncate a UTF-8 string safely at or before `max_bytes` without slicing inside a multi-byte code point
pub fn safe_truncate(s: &str, max_bytes: usize) -> &str {
    if s.len() <= max_bytes {
        return s;
    }
    let mut boundary = max_bytes;
    while !s.is_char_boundary(boundary) && boundary > 0 {
        boundary -= 1;
    }
    &s[..boundary]
}
