//! Bounded replay cache and ingest guard for live mesh traffic
//! (S9 brief §2.2–2.3).
//!
//! One abstraction reused by beacons, heartbeats, and chat: entries are keyed
//! by `(key_id, timestamp)` — `key_id` is a peer id or public key — and are
//! held for the freshness window (2× the protocol interval). In-memory only:
//! replay across restarts matters for stored payloads, not live mesh traffic.

#![forbid(unsafe_code)]

use std::collections::{HashMap, VecDeque};
use std::net::IpAddr;
use std::time::{Duration, Instant};

/// Verdict for one `(key_id, timestamp)` observation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReplayVerdict {
    /// First sighting inside the window; recorded now.
    Fresh,
    /// Already seen inside the window; refuse the payload.
    Replayed,
    /// Timestamp outside the freshness window (too old or too far ahead).
    OutsideWindow,
}

/// Bounded, in-memory replay cache. The freshness window is supplied per
/// observation so each protocol (beacon, heartbeat, chat) can use its own
/// 2× interval without sharing a constructor-time constant.
#[derive(Debug)]
pub struct ReplayCache {
    seen: HashMap<(String, u64), Instant>,
    order: VecDeque<(String, u64)>,
    capacity: usize,
}

impl ReplayCache {
    /// `capacity` bounds the number of live entries.
    #[must_use]
    pub fn new(capacity: usize) -> Self {
        Self {
            seen: HashMap::new(),
            order: VecDeque::new(),
            capacity: capacity.max(1),
        }
    }

    /// Observe one `(key_id, timestamp)`. `now` is the monotonic clock for TTL
    /// bookkeeping; `now_unix` is the wall clock in the timestamp's domain;
    /// `window` is the freshness tolerance (and the entry TTL). Returns
    /// [`ReplayVerdict::Fresh`] and records the entry on first sight.
    pub fn check_and_insert(
        &mut self,
        key_id: &str,
        timestamp: u64,
        now: Instant,
        now_unix: u64,
        window: Duration,
    ) -> ReplayVerdict {
        if now_unix.abs_diff(timestamp) > window.as_secs() {
            return ReplayVerdict::OutsideWindow;
        }
        self.prune(now, window);
        let key = (key_id.to_string(), timestamp);
        if self.seen.contains_key(&key) {
            return ReplayVerdict::Replayed;
        }
        self.seen.insert(key.clone(), now);
        self.order.push_back(key);
        self.evict_to_capacity();
        ReplayVerdict::Fresh
    }

    /// Live entries (diagnostics/tests).
    #[must_use]
    pub fn len(&self) -> usize {
        self.seen.len()
    }

    /// True when no live entries remain.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.seen.is_empty()
    }

    fn prune(&mut self, now: Instant, window: Duration) {
        while let Some(front) = self.order.front() {
            let expired = self
                .seen
                .get(front)
                .is_none_or(|at| now.saturating_duration_since(*at) >= window);
            if !expired {
                break;
            }
            if let Some(key) = self.order.pop_front() {
                self.seen.remove(&key);
            }
        }
    }

    fn evict_to_capacity(&mut self) {
        while self.order.len() > self.capacity {
            if let Some(key) = self.order.pop_front() {
                self.seen.remove(&key);
            }
        }
    }
}

/// Per-source token window for beacon floods (TITO-style suppression).
#[derive(Debug)]
pub struct SourceRateLimiter {
    per_source: HashMap<IpAddr, (Instant, u32)>,
    limit_per_window: u32,
}

impl SourceRateLimiter {
    /// `limit_per_window` observations are admitted per source address in each
    /// window; everything above is refused until the window rolls over.
    #[must_use]
    pub fn new(limit_per_window: u32) -> Self {
        Self {
            per_source: HashMap::new(),
            limit_per_window: limit_per_window.max(1),
        }
    }

    /// Admit or refuse one observation from `source`.
    pub fn allow(&mut self, source: IpAddr, now: Instant, window: Duration) -> bool {
        let entry = self.per_source.entry(source).or_insert((now, 0));
        if now.saturating_duration_since(entry.0) >= window {
            *entry = (now, 0);
        }
        if entry.1 >= self.limit_per_window {
            return false;
        }
        entry.1 += 1;
        true
    }

    /// Tracked sources (diagnostics/tests).
    #[must_use]
    pub fn tracked_sources(&self) -> usize {
        self.per_source.len()
    }
}

/// Verdict for one beacon ingest attempt.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IngestVerdict {
    /// Fresh, in-window, within rate — process the beacon.
    Accepted,
    /// Source exceeded its per-window beacon budget.
    RateLimited,
    /// Timestamp outside the 2× interval freshness window.
    Stale,
    /// `(peer_id, timestamp)` already observed inside the window.
    Replayed,
}

/// Ingest guard for beacons: freshness, per-source rate limit, replay cache.
#[derive(Debug)]
pub struct IngestGuard {
    replay: ReplayCache,
    rate: SourceRateLimiter,
}

impl IngestGuard {
    /// `capacity` bounds the replay cache; `limit_per_source` bounds beacons
    /// admitted per source address per interval window.
    #[must_use]
    pub fn new(capacity: usize, limit_per_source: u32) -> Self {
        Self {
            replay: ReplayCache::new(capacity),
            rate: SourceRateLimiter::new(limit_per_source),
        }
    }

    /// Cheap pre-verification gate: freshness window (`2 × interval`) plus the
    /// per-source rate limit. Runs before any signature work.
    pub fn pre_check(
        &mut self,
        source: IpAddr,
        timestamp: u64,
        now: Instant,
        now_unix: u64,
        interval: Duration,
    ) -> Result<(), IngestVerdict> {
        let window = interval.saturating_mul(2);
        if now_unix.abs_diff(timestamp) > window.as_secs() {
            return Err(IngestVerdict::Stale);
        }
        if !self.rate.allow(source, now, interval) {
            return Err(IngestVerdict::RateLimited);
        }
        Ok(())
    }

    /// Record a **signature-verified** observation and answer whether it was
    /// fresh. Only verified observations enter the replay cache: recording
    /// before verification would let a forged beacon with the same timestamp
    /// block the genuine one (a same-second denial of service).
    pub fn record_verified(
        &mut self,
        peer_id: &str,
        timestamp: u64,
        now: Instant,
        now_unix: u64,
        interval: Duration,
    ) -> ReplayVerdict {
        self.replay.check_and_insert(
            peer_id,
            timestamp,
            now,
            now_unix,
            interval.saturating_mul(2),
        )
    }

    /// Live replay entries (diagnostics/tests).
    #[must_use]
    pub fn replay_len(&self) -> usize {
        self.replay.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::Ipv4Addr;

    fn cache() -> ReplayCache {
        ReplayCache::new(8)
    }

    fn ip(last: u8) -> IpAddr {
        IpAddr::V4(Ipv4Addr::new(127, 0, 0, last))
    }

    #[test]
    fn fresh_then_replay_per_key_and_timestamp() {
        let mut c = cache();
        let now = Instant::now();
        let w = Duration::from_secs(10);
        assert_eq!(
            c.check_and_insert("peer-a", 1000, now, 1002, w),
            ReplayVerdict::Fresh
        );
        assert_eq!(
            c.check_and_insert("peer-a", 1000, now, 1002, w),
            ReplayVerdict::Replayed
        );
        assert_eq!(
            c.check_and_insert("peer-b", 1000, now, 1002, w),
            ReplayVerdict::Fresh
        );
        assert_eq!(
            c.check_and_insert("peer-a", 1001, now, 1002, w),
            ReplayVerdict::Fresh
        );
        assert_eq!(c.len(), 3);
    }

    #[test]
    fn outside_window_is_refused_both_directions() {
        let mut c = cache();
        let now = Instant::now();
        let w = Duration::from_secs(10);
        assert_eq!(
            c.check_and_insert("peer-a", 900, now, 1000, w),
            ReplayVerdict::OutsideWindow
        );
        assert_eq!(
            c.check_and_insert("peer-a", 1200, now, 1000, w),
            ReplayVerdict::OutsideWindow
        );
        assert!(c.is_empty(), "refused observations are not recorded");
    }

    #[test]
    fn capacity_is_bounded_and_oldest_evicted() {
        let mut c = ReplayCache::new(3);
        let now = Instant::now();
        let w = Duration::from_secs(60);
        for i in 0..5u64 {
            assert_eq!(
                c.check_and_insert("peer", i, now, i, w),
                ReplayVerdict::Fresh
            );
        }
        assert!(c.len() <= 3, "cache must stay within capacity");
        assert_eq!(
            c.check_and_insert("peer", 0, now, 0, w),
            ReplayVerdict::Fresh
        );
    }

    #[test]
    fn zero_window_ages_entries_immediately() {
        let mut c = ReplayCache::new(8);
        let now = Instant::now();
        assert_eq!(
            c.check_and_insert("p", 7, now, 7, Duration::ZERO),
            ReplayVerdict::Fresh
        );
        assert_eq!(
            c.check_and_insert("p", 7, now, 7, Duration::ZERO),
            ReplayVerdict::Fresh
        );
    }

    #[test]
    fn rate_limiter_refills_after_window() {
        let mut r = SourceRateLimiter::new(2);
        let now = Instant::now();
        let w = Duration::from_secs(5);
        assert!(r.allow(ip(1), now, w));
        assert!(r.allow(ip(1), now, w));
        assert!(!r.allow(ip(1), now, w), "third beacon in window refused");
        assert!(r.allow(ip(2), now, w), "other sources unaffected");
        // A later window rolls over (advance by sleeping past the window).
        let later = now + w + Duration::from_millis(1);
        assert!(r.allow(ip(1), later, w), "window rollover re-admits");
    }

    #[test]
    fn ingest_guard_applies_freshness_rate_and_replay() {
        let mut g = IngestGuard::new(32, 1);
        let now = Instant::now();
        let interval = Duration::from_secs(5);

        // Stale (older than 2× interval) — refused, not recorded.
        assert_eq!(
            g.pre_check(ip(1), 900, now, 1000, interval),
            Err(IngestVerdict::Stale)
        );
        // Fresh pre-check passes.
        assert_eq!(g.pre_check(ip(1), 1000, now, 1000, interval), Ok(()));
        // Second beacon from the same source in the window — rate-limited.
        assert_eq!(
            g.pre_check(ip(1), 1000, now, 1000, interval),
            Err(IngestVerdict::RateLimited)
        );
        // Another source still admitted.
        assert_eq!(g.pre_check(ip(2), 1000, now, 1000, interval), Ok(()));

        // Replay cache applies only to verified observations.
        assert_eq!(
            g.record_verified("peer-a", 1000, now, 1000, interval),
            ReplayVerdict::Fresh
        );
        assert_eq!(
            g.record_verified("peer-a", 1000, now, 1000, interval),
            ReplayVerdict::Replayed
        );
        assert_eq!(
            g.record_verified("peer-b", 1000, now, 1000, interval),
            ReplayVerdict::Fresh
        );
        assert_eq!(g.replay_len(), 2);
    }
}
