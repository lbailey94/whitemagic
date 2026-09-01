//! Replay protection (S9).
//!
//! The mesh has no transport-level message authenticity beyond Ed25519
//! signatures — and a signature only proves *who* sent a packet, not that
//! it is *fresh*. An attacker (or a misbehaving switch) can re-inject a
//! captured beacon or chat packet verbatim and it will verify perfectly.
//!
//! The [`ReplayCache`] closes that: per-peer bounded sets of payload
//! hashes with a time-to-live. A packet whose hash is still in the
//! sender's window is a duplicate and is dropped before it can touch the
//! registry or the chat log.
//!
//! In-memory only, by design: identity bindings are in-memory too, so
//! restart clears both together and a documented fresh-start remains the
//! recovery story.

use std::collections::{HashMap, VecDeque};
use std::sync::Mutex;

/// Default TTL for a remembered payload (seconds).
pub const DEFAULT_TTL_SECS: i64 = 600;
/// Default maximum remembered payloads per peer (oldest evicted first).
pub const DEFAULT_MAX_PER_PEER: usize = 4096;

/// FNV-1a 64-bit — stable, dependency-free payload hashing. Not
/// cryptographic; collisions only ever cost us a *dropped duplicate*
/// check on a 2^-64 space, never an acceptance.
#[must_use]
pub fn fnv1a64(bytes: &[u8]) -> u64 {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for &b in bytes {
        hash ^= u64::from(b);
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
    }
    hash
}

struct PeerWindow {
    entries: VecDeque<(u64, i64)>,
}

impl PeerWindow {
    const fn new() -> Self {
        Self {
            entries: VecDeque::new(),
        }
    }

    fn prune(&mut self, now: i64, ttl_secs: i64) {
        while let Some((_, ts)) = self.entries.front() {
            if now - *ts > ttl_secs {
                self.entries.pop_front();
            } else {
                break;
            }
        }
    }

    fn contains(&self, hash: u64) -> bool {
        self.entries.iter().any(|(h, _)| *h == hash)
    }

    fn insert(&mut self, hash: u64, now: i64, max: usize) {
        if self.entries.len() >= max {
            self.entries.pop_front();
        }
        self.entries.push_back((hash, now));
    }
}

/// Per-peer replay cache. Self-locking so callers can hold other state
/// locks while checking.
pub struct ReplayCache {
    inner: Mutex<Inner>,
    ttl_secs: i64,
    max_per_peer: usize,
}

struct Inner {
    peers: HashMap<String, PeerWindow>,
}

impl Default for ReplayCache {
    fn default() -> Self {
        Self::new(DEFAULT_TTL_SECS, DEFAULT_MAX_PER_PEER)
    }
}

impl ReplayCache {
    /// Create a cache with the given TTL and per-peer capacity.
    #[must_use]
    pub fn new(ttl_secs: i64, max_per_peer: usize) -> Self {
        Self {
            inner: Mutex::new(Inner {
                peers: HashMap::new(),
            }),
            ttl_secs,
            max_per_peer,
        }
    }

    /// Check a payload and remember it atomically.
    ///
    /// Returns `true` if the payload is fresh (first sighting within the
    /// TTL window), `false` if it is a replay. Expired entries are
    /// pruned lazily; per-peer windows evict oldest-first at capacity.
    // The MutexGuard must span check-and-insert: splitting them reopens
    // the race the cache exists to close (two ingests, both "fresh").
    // clippy::significant_drop_tightening (nursery) would narrow the
    // guard anyway; explicitly declined here.
    #[allow(clippy::significant_drop_tightening)]
    pub fn check_and_insert(&self, peer: &str, hash: u64, now: i64) -> bool {
        let mut inner = self.inner.lock().expect("replay cache poisoned");
        let window = inner
            .peers
            .entry(peer.to_string())
            .or_insert_with(PeerWindow::new);
        window.prune(now, self.ttl_secs);
        if window.contains(hash) {
            return false;
        }
        window.insert(hash, now, self.max_per_peer);
        true
    }

    /// Number of peers currently tracked (diagnostics/tests).
    #[must_use]
    pub fn tracked_peers(&self) -> usize {
        let inner = self.inner.lock().expect("replay cache poisoned");
        inner.peers.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn duplicate_rejected_fresh_accepted() {
        let cache = ReplayCache::default();
        let hash = fnv1a64(b"beacon-payload");
        assert!(cache.check_and_insert("peer-a", hash, 1_000));
        assert!(
            !cache.check_and_insert("peer-a", hash, 1_005),
            "replay must be rejected"
        );
        // A different payload from the same peer is fine.
        assert!(cache.check_and_insert("peer-a", hash + 1, 1_005));
        // The same payload from a different peer is a different sighting.
        assert!(cache.check_and_insert("peer-b", hash, 1_005));
    }

    #[test]
    fn ttl_expiry_allows_again() {
        let cache = ReplayCache::new(60, 16);
        let hash = fnv1a64(b"payload");
        assert!(cache.check_and_insert("peer", hash, 0));
        assert!(!cache.check_and_insert("peer", hash, 30));
        assert!(
            cache.check_and_insert("peer", hash, 120),
            "expired entry must allow re-acceptance"
        );
    }

    #[test]
    fn per_peer_capacity_evicts_oldest() {
        let cache = ReplayCache::new(600, 3);
        for i in 0..4_i64 {
            assert!(cache.check_and_insert("peer", i as u64, i));
        }
        // Entry 0 was evicted when 3 arrived; re-inserting it is "fresh".
        assert!(cache.check_and_insert("peer", 0, 10));
    }

    #[test]
    fn fnv1a64_reference_vectors() {
        assert_eq!(fnv1a64(b""), 0xcbf2_9ce4_8422_2325);
        assert_eq!(fnv1a64(b"a"), 0xaf63_dc4c_8601_ec8c);
    }
}
