//! Cross-Memory Consistency Layer (CMCL) — Proposal 1
//!
//! Provides real-time cross-galaxy coherence, vector clocks, bounded-latency
//! causal consensus, and crash-barrier write provenance across WhiteMagic's
//! multi-galaxy LMDB memory shards (Codex, Karma, Citta, Aria, Dreams, etc.).

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::collections::{HashSet, VecDeque};
use thiserror::Error;
use wm_core::Galaxy;

/// Maximum number of receipts preserved in the bounded history buffer.
const DEFAULT_RECEIPT_CAPACITY: usize = 512;

/// Vector clock tracking causal mutation progress across all 14 memory galaxies.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct VectorClock {
    clocks: [u64; Galaxy::COUNT],
}

impl Default for VectorClock {
    fn default() -> Self {
        Self::new()
    }
}

impl VectorClock {
    /// Create a zero-initialized vector clock.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            clocks: [0; Galaxy::COUNT],
        }
    }

    /// Helper to convert a galaxy into its zero-based index in `Galaxy::all()`.
    const fn galaxy_index(galaxy: Galaxy) -> usize {
        match galaxy {
            Galaxy::Aria => 0,
            Galaxy::Citta => 1,
            Galaxy::Codex => 2,
            Galaxy::Journals => 3,
            Galaxy::Dreams => 4,
            Galaxy::Research => 5,
            Galaxy::Sessions => 6,
            Galaxy::Substrate => 7,
            Galaxy::Tutorial => 8,
            Galaxy::Universal => 9,
            Galaxy::Karma => 10,
            Galaxy::Dharma => 11,
            Galaxy::Associations => 12,
            Galaxy::Embeddings => 13,
        }
    }

    /// Get clock value for a specific galaxy.
    #[must_use]
    pub const fn get(&self, galaxy: Galaxy) -> u64 {
        self.clocks[Self::galaxy_index(galaxy)]
    }

    /// Set clock value for a specific galaxy.
    pub fn set(&mut self, galaxy: Galaxy, val: u64) {
        self.clocks[Self::galaxy_index(galaxy)] = val;
    }

    /// Increment and return the new clock value for a specific galaxy.
    pub fn tick(&mut self, galaxy: Galaxy) -> u64 {
        let idx = Self::galaxy_index(galaxy);
        self.clocks[idx] = self.clocks[idx].saturating_add(1);
        self.clocks[idx]
    }

    /// Merge with another vector clock by taking the component-wise maximum.
    pub fn merge(&mut self, other: &Self) {
        for i in 0..Galaxy::COUNT {
            if other.clocks[i] > self.clocks[i] {
                self.clocks[i] = other.clocks[i];
            }
        }
    }

    /// Returns `true` if `self` causally precedes `other` (`self < other`).
    #[must_use]
    pub fn happened_before(&self, other: &Self) -> bool {
        let mut strictly_smaller = false;
        for i in 0..Galaxy::COUNT {
            if self.clocks[i] > other.clocks[i] {
                return false;
            }
            if self.clocks[i] < other.clocks[i] {
                strictly_smaller = true;
            }
        }
        strictly_smaller
    }

    /// Returns `true` if `self` and `other` are causally concurrent (neither precedes the other).
    #[must_use]
    pub fn is_concurrent(&self, other: &Self) -> bool {
        !self.happened_before(other) && !other.happened_before(self) && self != other
    }

    /// Calculate Manhattan distance (total skew) between two clocks across all galaxies.
    #[must_use]
    pub fn distance(&self, other: &Self) -> u64 {
        let mut total = 0u64;
        for i in 0..Galaxy::COUNT {
            total = total.saturating_add(self.clocks[i].abs_diff(other.clocks[i]));
        }
        total
    }
}

/// A cross-galaxy write mutation operation submitted for consistency verification.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WriteOp {
    /// Multi-step crash barrier correlation ID (e.g. from U6 WriteAuditJournal).
    pub operation_id: Option<String>,
    /// Target galaxy for the write.
    pub galaxy: Galaxy,
    /// Unique memory key or ID.
    pub key: String,
    /// SHA-256 or blake3 content hash for idempotency and integrity.
    pub content_hash: String,
    /// Causal vector clock associated with the write.
    pub vector_clock: VectorClock,
    /// Epoch timestamp in seconds.
    pub timestamp: u64,
    /// Mutation source (e.g. "agent:copilot", "mcp:client", "daemon:citta").
    pub source: String,
    /// Whether this write was signed and authorized by Dharma governance.
    pub dharma_provenance: bool,
}

/// Errors raised by the Cross-Memory Consistency Layer.
#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum ConsistencyError {
    #[error("Causal violation on {galaxy:?}: required clock {required} > active clock {actual}")]
    CausalViolation {
        galaxy: Galaxy,
        required: u64,
        actual: u64,
    },

    #[error("Concurrent conflict on {galaxy:?}: active {active:?}, incoming {incoming:?}")]
    ConcurrentConflict {
        galaxy: Galaxy,
        active: VectorClock,
        incoming: VectorClock,
    },

    #[error("Uncommitted crash barrier detected for operation '{operation_id}'")]
    UncommittedBarrierDetected { operation_id: String },

    #[error("Missing Dharma provenance signature on write to {galaxy:?}")]
    MissingDharmaProvenance { galaxy: Galaxy },
}

/// Provenance and coherence receipt issued upon successfully applying a cross-galaxy write.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoherenceReceipt {
    pub operation_id: Option<String>,
    pub galaxy: Galaxy,
    pub key: String,
    pub vector_clock: VectorClock,
    pub applied_at: u64,
    pub coherence_score: f32,
}

/// Global system-wide snapshot of cross-memory consistency state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoherenceSnapshot {
    pub global_clock: VectorClock,
    pub total_writes_tracked: u64,
    pub active_uncommitted_barriers: usize,
    pub coherence_ratio: f32,
    pub last_reconciled_epoch: u64,
}

/// Detail report of a detected conflict between concurrent cross-galaxy operations.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConflictReport {
    pub operation_id: Option<String>,
    pub galaxy: Galaxy,
    pub key: String,
    pub active_clock: VectorClock,
    pub incoming_clock: VectorClock,
    pub reason: String,
}

/// Conflict resolution strategy for concurrent writes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Resolution {
    /// Accept incoming write and advance vector clock.
    AcceptIncoming,
    /// Retain current active memory state, discarding incoming write.
    KeepActive,
    /// Merge vector clocks component-wise and mark reconciled.
    MergeClocks,
}

/// Core trait defining the Cross-Memory Consistency contract.
pub trait CrossMemoryConsistency {
    /// Verify and record a cross-galaxy write, updating causal clocks.
    fn record_write(&mut self, op: &WriteOp) -> Result<CoherenceReceipt, ConsistencyError>;

    /// Check if reading from `galaxy` satisfies the caller's required vector clock.
    fn verify_causal_read(&self, galaxy: Galaxy, required_clock: &VectorClock) -> Result<(), ConsistencyError>;

    /// Resolve a concurrent mutation conflict.
    fn resolve_conflict(&mut self, conflict: &ConflictReport, strategy: Resolution) -> CoherenceReceipt;

    /// Retrieve the current point-in-time coherence snapshot.
    fn snapshot(&self) -> CoherenceSnapshot;
}

/// Thread-safe manager implementing the Cross-Memory Consistency Layer (CMCL).
#[derive(Debug)]
pub struct CrossMemoryConsistencyManager {
    global_clock: VectorClock,
    uncommitted_barriers: HashSet<String>,
    receipt_history: VecDeque<CoherenceReceipt>,
    total_writes: u64,
    last_epoch: u64,
    enforce_dharma: bool,
}

impl Default for CrossMemoryConsistencyManager {
    fn default() -> Self {
        Self::new()
    }
}

impl CrossMemoryConsistencyManager {
    /// Create a new consistency manager with default buffer limits.
    #[must_use]
    pub fn new() -> Self {
        Self {
            global_clock: VectorClock::new(),
            uncommitted_barriers: HashSet::new(),
            receipt_history: VecDeque::with_capacity(DEFAULT_RECEIPT_CAPACITY),
            total_writes: 0,
            last_epoch: 0,
            enforce_dharma: false,
        }
    }

    /// Configure whether Dharma governance authorization is strictly enforced.
    #[must_use]
    pub fn with_dharma_enforcement(mut self, enforce: bool) -> Self {
        self.enforce_dharma = enforce;
        self
    }

    /// Mark an operation ID as an active uncommitted crash barrier.
    pub fn register_uncommitted_barrier(&mut self, op_id: &str) {
        self.uncommitted_barriers.insert(op_id.to_string());
    }

    /// Commit or clear an operation ID's crash barrier.
    pub fn commit_barrier(&mut self, op_id: &str) {
        self.uncommitted_barriers.remove(op_id);
    }

    /// Check if an operation ID is currently uncommitted.
    #[must_use]
    pub fn is_uncommitted(&self, op_id: &str) -> bool {
        self.uncommitted_barriers.contains(op_id)
    }

    /// Retrieve the current active vector clock.
    #[must_use]
    pub const fn global_clock(&self) -> &VectorClock {
        &self.global_clock
    }

    /// Compute current coherence ratio (0.0 to 1.0) based on uncommitted barrier load.
    #[must_use]
    pub fn coherence_ratio(&self) -> f32 {
        if self.uncommitted_barriers.is_empty() {
            1.0
        } else {
            let penalty = (self.uncommitted_barriers.len() as f32 * 0.05).min(0.8);
            1.0 - penalty
        }
    }
}

impl CrossMemoryConsistency for CrossMemoryConsistencyManager {
    fn record_write(&mut self, op: &WriteOp) -> Result<CoherenceReceipt, ConsistencyError> {
        // 1. Dharma governance check
        if self.enforce_dharma && !op.dharma_provenance {
            return Err(ConsistencyError::MissingDharmaProvenance { galaxy: op.galaxy });
        }

        // 2. Uncommitted barrier check: if the operation itself is an uncommitted crash barrier,
        // we flag it if dependent cross-galaxy operations attempt to build on it before commit.
        if let Some(ref op_id) = op.operation_id {
            if self.uncommitted_barriers.contains(op_id) {
                return Err(ConsistencyError::UncommittedBarrierDetected {
                    operation_id: op_id.clone(),
                });
            }
        }

        // 3. Monotonic causal advance
        self.global_clock.tick(op.galaxy);
        self.global_clock.merge(&op.vector_clock);

        self.total_writes = self.total_writes.saturating_add(1);
        self.last_epoch = op.timestamp;

        let receipt = CoherenceReceipt {
            operation_id: op.operation_id.clone(),
            galaxy: op.galaxy,
            key: op.key.clone(),
            vector_clock: self.global_clock,
            applied_at: op.timestamp,
            coherence_score: self.coherence_ratio(),
        };

        if self.receipt_history.len() >= DEFAULT_RECEIPT_CAPACITY {
            self.receipt_history.pop_front();
        }
        self.receipt_history.push_back(receipt.clone());

        Ok(receipt)
    }

    fn verify_causal_read(&self, galaxy: Galaxy, required_clock: &VectorClock) -> Result<(), ConsistencyError> {
        let actual = self.global_clock.get(galaxy);
        let required = required_clock.get(galaxy);

        if actual < required {
            return Err(ConsistencyError::CausalViolation {
                galaxy,
                required,
                actual,
            });
        }
        Ok(())
    }

    fn resolve_conflict(&mut self, conflict: &ConflictReport, strategy: Resolution) -> CoherenceReceipt {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |d| d.as_secs());

        match strategy {
            Resolution::AcceptIncoming => {
                self.global_clock.merge(&conflict.incoming_clock);
                self.global_clock.tick(conflict.galaxy);
            }
            Resolution::KeepActive => {
                self.global_clock.tick(conflict.galaxy);
            }
            Resolution::MergeClocks => {
                self.global_clock.merge(&conflict.active_clock);
                self.global_clock.merge(&conflict.incoming_clock);
                self.global_clock.tick(conflict.galaxy);
            }
        }

        CoherenceReceipt {
            operation_id: conflict.operation_id.clone(),
            galaxy: conflict.galaxy,
            key: conflict.key.clone(),
            vector_clock: self.global_clock,
            applied_at: now,
            coherence_score: self.coherence_ratio(),
        }
    }

    fn snapshot(&self) -> CoherenceSnapshot {
        CoherenceSnapshot {
            global_clock: self.global_clock,
            total_writes_tracked: self.total_writes,
            active_uncommitted_barriers: self.uncommitted_barriers.len(),
            coherence_ratio: self.coherence_ratio(),
            last_reconciled_epoch: self.last_epoch,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vector_clock_ordering_and_merge() {
        let mut vc1 = VectorClock::new();
        let mut vc2 = VectorClock::new();

        assert_eq!(vc1, vc2);
        assert!(!vc1.happened_before(&vc2));

        vc1.tick(Galaxy::Codex);
        assert!(vc2.happened_before(&vc1));
        assert!(!vc1.happened_before(&vc2));

        vc2.tick(Galaxy::Karma);
        // Now vc1 has Codex=1, Karma=0; vc2 has Codex=0, Karma=1 -> concurrent!
        assert!(vc1.is_concurrent(&vc2));

        vc1.merge(&vc2);
        assert_eq!(vc1.get(Galaxy::Codex), 1);
        assert_eq!(vc1.get(Galaxy::Karma), 1);
    }

    #[test]
    fn test_consistency_manager_record_and_verify_read() {
        let mut cm = CrossMemoryConsistencyManager::new();

        let op = WriteOp {
            operation_id: Some("op-100".into()),
            galaxy: Galaxy::Codex,
            key: "memory:123".into(),
            content_hash: "blake3:abc".into(),
            vector_clock: VectorClock::new(),
            timestamp: 1_700_000_000,
            source: "test".into(),
            dharma_provenance: true,
        };

        let receipt = cm.record_write(&op).expect("write should apply cleanly");
        assert_eq!(receipt.galaxy, Galaxy::Codex);
        assert_eq!(receipt.vector_clock.get(Galaxy::Codex), 1);

        // Verify causal read: requires Codex <= 1 -> OK
        let mut req_clock = VectorClock::new();
        req_clock.set(Galaxy::Codex, 1);
        assert!(cm.verify_causal_read(Galaxy::Codex, &req_clock).is_ok());

        // Verify causal read: requires Codex >= 5 -> CausalViolation
        req_clock.set(Galaxy::Codex, 5);
        let err = cm.verify_causal_read(Galaxy::Codex, &req_clock).unwrap_err();
        assert_eq!(
            err,
            ConsistencyError::CausalViolation {
                galaxy: Galaxy::Codex,
                required: 5,
                actual: 1
            }
        );
    }

    #[test]
    fn test_uncommitted_crash_barrier_detection() {
        let mut cm = CrossMemoryConsistencyManager::new();
        cm.register_uncommitted_barrier("uncommitted-op-999");
        assert!(cm.is_uncommitted("uncommitted-op-999"));

        let op = WriteOp {
            operation_id: Some("uncommitted-op-999".into()),
            galaxy: Galaxy::Karma,
            key: "audit:001".into(),
            content_hash: "hash".into(),
            vector_clock: VectorClock::new(),
            timestamp: 100,
            source: "agent".into(),
            dharma_provenance: true,
        };

        let err = cm.record_write(&op).unwrap_err();
        assert_eq!(
            err,
            ConsistencyError::UncommittedBarrierDetected {
                operation_id: "uncommitted-op-999".into()
            }
        );

        // Once barrier committed, write succeeds
        cm.commit_barrier("uncommitted-op-999");
        assert!(!cm.is_uncommitted("uncommitted-op-999"));
        assert!(cm.record_write(&op).is_ok());
    }

    #[test]
    fn test_conflict_resolution_strategies() {
        let mut cm = CrossMemoryConsistencyManager::new();
        let mut active = VectorClock::new();
        active.tick(Galaxy::Citta);

        let mut incoming = VectorClock::new();
        incoming.tick(Galaxy::Karma);

        let conflict = ConflictReport {
            operation_id: Some("op-conflict".into()),
            galaxy: Galaxy::Citta,
            key: "state:citta".into(),
            active_clock: active,
            incoming_clock: incoming,
            reason: "concurrent divergence".into(),
        };

        let receipt = cm.resolve_conflict(&conflict, Resolution::MergeClocks);
        assert!(receipt.vector_clock.get(Galaxy::Citta) >= 1);
        assert!(receipt.vector_clock.get(Galaxy::Karma) >= 1);

        let snap = cm.snapshot();
        assert_eq!(snap.active_uncommitted_barriers, 0);
        assert_eq!(snap.coherence_ratio, 1.0);
    }
}
