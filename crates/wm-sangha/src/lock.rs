//! Distributed resource lock manager — lease-based with TTL.

#![forbid(unsafe_code)]

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::peer::PeerId;

// ── Lock State ────────────────────────────────────────────────────────

/// State of a resource lock.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LockState {
    /// Lock is held by a peer.
    Held,
    /// Lock has expired (TTL elapsed).
    Expired,
    /// Lock is free (released or never acquired).
    Free,
}

// ── Lock Entry ────────────────────────────────────────────────────────

/// A resource lock entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LockEntry {
    /// The resource being locked (e.g., "memory:galaxy:codex").
    pub resource: String,
    /// The peer holding the lock.
    pub holder: PeerId,
    /// When the lock was acquired (Unix seconds).
    pub acquired_at: i64,
    /// TTL in seconds (lock expires after this).
    pub ttl_sec: i64,
    /// Current state.
    pub state: LockState,
    /// Number of times this lock has been acquired.
    pub acquisition_count: u64,
}

impl LockEntry {
    /// Whether this lock has expired.
    #[must_use]
    pub fn is_expired(&self) -> bool {
        let now = chrono::Utc::now().timestamp();
        now - self.acquired_at > self.ttl_sec
    }

    /// Remaining TTL in seconds.
    #[must_use]
    pub fn remaining_ttl(&self) -> i64 {
        let now = chrono::Utc::now().timestamp();
        let elapsed = now - self.acquired_at;
        self.ttl_sec - elapsed
    }
}

// ── Resource Lock Manager ─────────────────────────────────────────────

/// Distributed resource lock manager — lease-based with TTL.
///
/// Provides acquire/release/extend semantics for distributed locks.
/// Locks automatically expire after their TTL. Deadlock detection
/// is timeout-based (expired locks are reclaimed).
pub struct ResourceLockManager {
    locks: HashMap<String, LockEntry>,
    /// Default TTL for new locks.
    default_ttl_sec: i64,
    /// Maximum locks a single peer can hold simultaneously.
    max_locks_per_peer: usize,
    /// Total acquires.
    total_acquires: u64,
    /// Total releases.
    total_releases: u64,
    /// Total expired locks.
    total_expired: u64,
    /// Total denied (already held).
    total_denied: u64,
    /// Total denied due to per-peer limit.
    total_peer_limit_denied: u64,
}

impl Default for ResourceLockManager {
    fn default() -> Self {
        Self::new(30)
    }
}

impl std::fmt::Debug for ResourceLockManager {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ResourceLockManager")
            .field("active_locks", &self.locks.len())
            .field("total_acquires", &self.total_acquires)
            .field("total_releases", &self.total_releases)
            .finish_non_exhaustive()
    }
}

impl ResourceLockManager {
    /// Create a new lock manager with a default TTL.
    #[must_use]
    pub fn new(default_ttl_sec: i64) -> Self {
        Self {
            locks: HashMap::new(),
            default_ttl_sec,
            max_locks_per_peer: 32,
            total_acquires: 0,
            total_releases: 0,
            total_expired: 0,
            total_denied: 0,
            total_peer_limit_denied: 0,
        }
    }

    /// Create a new lock manager with a custom per-peer lock limit.
    #[must_use]
    pub fn with_peer_limit(default_ttl_sec: i64, max_locks_per_peer: usize) -> Self {
        Self {
            max_locks_per_peer,
            ..Self::new(default_ttl_sec)
        }
    }

    /// Get the maximum locks per peer.
    #[must_use]
    pub const fn max_locks_per_peer(&self) -> usize {
        self.max_locks_per_peer
    }

    /// Try to acquire a lock on a resource.
    /// Returns `true` if the lock was acquired, `false` if it's held by another peer.
    pub fn acquire(&mut self, resource: &str, peer_id: &str) -> bool {
        self.acquire_with_ttl(resource, peer_id, self.default_ttl_sec)
    }

    /// Try to acquire a lock with a specific TTL.
    pub fn acquire_with_ttl(&mut self, resource: &str, peer_id: &str, ttl_sec: i64) -> bool {
        // Check if there's an existing lock
        if let Some(existing) = self.locks.get(resource) {
            if existing.holder == peer_id {
                // Re-acquire (extend) — doesn't increase peer's lock count
                self.total_acquires += 1;
                let entry = LockEntry {
                    resource: resource.to_string(),
                    holder: peer_id.to_string(),
                    acquired_at: chrono::Utc::now().timestamp(),
                    ttl_sec,
                    state: LockState::Held,
                    acquisition_count: existing.acquisition_count + 1,
                };
                self.locks.insert(resource.to_string(), entry);
                return true;
            }

            if !existing.is_expired() {
                // Lock is held by someone else and not expired
                self.total_denied += 1;
                return false;
            }

            // Lock expired — reclaim
            self.total_expired += 1;
        }

        // Per-peer lock limit check (only for new acquisitions)
        let peer_lock_count = self.locks.values().filter(|l| l.holder == peer_id).count();
        if peer_lock_count >= self.max_locks_per_peer {
            self.total_peer_limit_denied += 1;
            self.total_denied += 1;
            return false;
        }

        // Acquire new lock
        self.total_acquires += 1;
        let entry = LockEntry {
            resource: resource.to_string(),
            holder: peer_id.to_string(),
            acquired_at: chrono::Utc::now().timestamp(),
            ttl_sec,
            state: LockState::Held,
            acquisition_count: 1,
        };
        self.locks.insert(resource.to_string(), entry);
        true
    }

    /// Release a lock. Returns `true` if the lock was held by the given peer.
    pub fn release(&mut self, resource: &str, peer_id: &str) -> bool {
        if let Some(lock) = self.locks.get(resource) {
            if lock.holder == peer_id {
                self.locks.remove(resource);
                self.total_releases += 1;
                return true;
            }
        }
        false
    }

    /// Revoke every lock held by a peer (quarantine). Returns the number
    /// of locks released — a bad apple cannot hold the community's
    /// resources hostage after it is cut off.
    pub fn revoke_peer(&mut self, peer_id: &str) -> usize {
        let held: Vec<String> = self
            .locks
            .iter()
            .filter(|(_, l)| l.holder == peer_id)
            .map(|(resource, _)| resource.clone())
            .collect();
        let count = held.len();
        for resource in held {
            self.locks.remove(&resource);
            self.total_releases += 1;
        }
        count
    }

    /// Extend a lock's TTL. Returns `true` if the lock was held by the given peer.
    pub fn extend(&mut self, resource: &str, peer_id: &str, additional_sec: i64) -> bool {
        if let Some(lock) = self.locks.get_mut(resource) {
            if lock.holder == peer_id && !lock.is_expired() {
                lock.ttl_sec += additional_sec;
                return true;
            }
        }
        false
    }

    /// Evict expired locks. Returns the number of locks evicted.
    pub fn evict_expired(&mut self) -> usize {
        let to_evict: Vec<String> = self
            .locks
            .iter()
            .filter(|(_, l)| l.is_expired())
            .map(|(r, _)| r.clone())
            .collect();

        for r in &to_evict {
            self.locks.remove(r);
            self.total_expired += 1;
        }

        to_evict.len()
    }

    /// Get a lock entry.
    #[must_use]
    pub fn get(&self, resource: &str) -> Option<&LockEntry> {
        self.locks.get(resource)
    }

    /// Number of active locks.
    #[must_use]
    pub fn lock_count(&self) -> usize {
        self.locks.len()
    }

    /// Get all locks held by a peer.
    #[must_use]
    pub fn locks_by_peer(&self, peer_id: &str) -> Vec<&LockEntry> {
        self.locks
            .values()
            .filter(|l| l.holder == peer_id)
            .collect()
    }

    /// Total acquires.
    #[must_use]
    pub const fn total_acquires(&self) -> u64 {
        self.total_acquires
    }

    /// Total releases.
    #[must_use]
    pub const fn total_releases(&self) -> u64 {
        self.total_releases
    }

    /// Total denied.
    #[must_use]
    pub const fn total_denied(&self) -> u64 {
        self.total_denied
    }

    /// Total expired.
    #[must_use]
    pub const fn total_expired(&self) -> u64 {
        self.total_expired
    }

    /// Total denied due to per-peer lock limit.
    #[must_use]
    pub const fn total_peer_limit_denied(&self) -> u64 {
        self.total_peer_limit_denied
    }

    /// Get a JSON summary.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "active_locks": self.locks.len(),
            "total_acquires": self.total_acquires,
            "total_releases": self.total_releases,
            "total_denied": self.total_denied,
            "total_expired": self.total_expired,
            "locks": self.locks.values().map(|l| serde_json::json!({
                "resource": l.resource,
                "holder": l.holder,
                "state": match l.state {
                    LockState::Held => "held",
                    LockState::Expired => "expired",
                    LockState::Free => "free",
                },
                "remaining_ttl": l.remaining_ttl(),
            })).collect::<Vec<_>>(),
        })
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn acquire_and_release() {
        let mut lm = ResourceLockManager::default();
        assert!(lm.acquire("resource:1", "node-1"));
        assert_eq!(lm.lock_count(), 1);
        assert!(lm.release("resource:1", "node-1"));
        assert_eq!(lm.lock_count(), 0);
    }

    #[test]
    fn acquire_denied_when_held() {
        let mut lm = ResourceLockManager::default();
        assert!(lm.acquire("resource:1", "node-1"));
        assert!(!lm.acquire("resource:1", "node-2"));
        assert_eq!(lm.total_denied(), 1);
    }

    #[test]
    fn reacquire_extends() {
        let mut lm = ResourceLockManager::default();
        assert!(lm.acquire("resource:1", "node-1"));
        assert!(lm.acquire("resource:1", "node-1")); // Re-acquire
        assert_eq!(lm.total_acquires(), 2);
        let lock = lm.get("resource:1").unwrap();
        assert_eq!(lock.acquisition_count, 2);
    }

    #[test]
    fn release_wrong_peer_fails() {
        let mut lm = ResourceLockManager::default();
        assert!(lm.acquire("resource:1", "node-1"));
        assert!(!lm.release("resource:1", "node-2"));
        assert_eq!(lm.lock_count(), 1);
    }

    #[test]
    fn expired_lock_reclaimed() {
        let mut lm = ResourceLockManager::new(0);
        assert!(lm.acquire("resource:1", "node-1"));

        std::thread::sleep(std::time::Duration::from_secs(1));

        // node-2 should be able to acquire since the lock expired
        assert!(lm.acquire("resource:1", "node-2"));
        assert!(lm.total_expired() >= 1);
    }

    #[test]
    fn extend_lock() {
        let mut lm = ResourceLockManager::new(10);
        assert!(lm.acquire("resource:1", "node-1"));
        assert!(lm.extend("resource:1", "node-1", 30));

        let lock = lm.get("resource:1").unwrap();
        assert!(lock.ttl_sec >= 40);
    }

    #[test]
    fn extend_wrong_peer_fails() {
        let mut lm = ResourceLockManager::default();
        assert!(lm.acquire("resource:1", "node-1"));
        assert!(!lm.extend("resource:1", "node-2", 10));
    }

    #[test]
    fn evict_expired() {
        let mut lm = ResourceLockManager::new(0);
        lm.acquire("resource:1", "node-1");
        lm.acquire("resource:2", "node-1");

        std::thread::sleep(std::time::Duration::from_secs(1));
        let evicted = lm.evict_expired();
        assert_eq!(evicted, 2);
        assert_eq!(lm.lock_count(), 0);
    }

    #[test]
    fn locks_by_peer() {
        let mut lm = ResourceLockManager::default();
        lm.acquire("resource:1", "node-1");
        lm.acquire("resource:2", "node-1");
        lm.acquire("resource:3", "node-2");

        let node1_locks = lm.locks_by_peer("node-1");
        assert_eq!(node1_locks.len(), 2);
    }

    #[test]
    fn lock_entry_remaining_ttl() {
        let entry = LockEntry {
            resource: "test".to_string(),
            holder: "node-1".to_string(),
            acquired_at: chrono::Utc::now().timestamp(),
            ttl_sec: 30,
            state: LockState::Held,
            acquisition_count: 1,
        };
        assert!(entry.remaining_ttl() > 25);
        assert!(!entry.is_expired());
    }

    #[test]
    fn lock_manager_summary() {
        let mut lm = ResourceLockManager::default();
        lm.acquire("resource:1", "node-1");

        let summary = lm.summary();
        assert_eq!(summary["active_locks"], 1);
        assert_eq!(summary["total_acquires"], 1);
    }

    #[test]
    fn acquire_with_custom_ttl() {
        let mut lm = ResourceLockManager::default();
        assert!(lm.acquire_with_ttl("resource:1", "node-1", 60));
        let lock = lm.get("resource:1").unwrap();
        assert_eq!(lock.ttl_sec, 60);
    }

    #[test]
    fn per_peer_lock_limit_enforced() {
        let mut lm = ResourceLockManager::with_peer_limit(60, 5);
        // Acquire 5 locks — all should succeed
        for i in 0..5 {
            assert!(lm.acquire(&format!("resource-{i}"), "greedy-peer"));
        }
        // 6th lock should be denied
        assert!(!lm.acquire("resource-5", "greedy-peer"));
        assert_eq!(lm.total_peer_limit_denied(), 1);
        assert_eq!(lm.locks_by_peer("greedy-peer").len(), 5);
    }

    #[test]
    fn per_peer_limit_does_not_affect_reacquire() {
        let mut lm = ResourceLockManager::with_peer_limit(60, 2);
        assert!(lm.acquire("resource:1", "node-1"));
        assert!(lm.acquire("resource:2", "node-1"));
        // At limit, but re-acquiring existing lock should still work
        assert!(lm.acquire("resource:1", "node-1"));
        assert_eq!(lm.total_peer_limit_denied(), 0);
    }

    #[test]
    fn per_peer_limit_allows_other_peers() {
        let mut lm = ResourceLockManager::with_peer_limit(60, 2);
        assert!(lm.acquire("resource:1", "node-1"));
        assert!(lm.acquire("resource:2", "node-1"));
        // node-1 is at limit, but node-2 can still acquire
        assert!(lm.acquire("resource:3", "node-2"));
        assert_eq!(lm.total_peer_limit_denied(), 0);
    }

    #[test]
    fn per_peer_limit_release_frees_slot() {
        let mut lm = ResourceLockManager::with_peer_limit(60, 2);
        assert!(lm.acquire("resource:1", "node-1"));
        assert!(lm.acquire("resource:2", "node-1"));
        // At limit
        assert!(!lm.acquire("resource:3", "node-1"));
        // Release one and try again
        assert!(lm.release("resource:1", "node-1"));
        assert!(lm.acquire("resource:3", "node-1"));
        assert_eq!(lm.total_peer_limit_denied(), 1);
    }
}
