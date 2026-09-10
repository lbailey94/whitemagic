//! Pattern immunity — the immune system that auto-learns threat patterns
//! from the security event bus.
//!
//! Rust port of the Python-era `whitemagic/core/immune/pattern_immunity.py`
//! (DEFERRED_OBJECTIVES_2026 Q2): "ImmuneSystem receives `SecurityEvent`
//! messages and auto-learns threat patterns from them."
//!
//! The Python original only recorded threats detected elsewhere; the Q2
//! completion condition is the *subscription*: [`PatternImmunity`] attaches
//! to a [`SecurityEventBus`] as a wildcard subscriber and, for every event
//! whose normalized signature (event type + tool + agent) has been seen
//! [`PATTERN_THRESHOLD`] times, marks the signature as immune and emits a
//! `PatternLearned` event back onto the bus — closing the loop. The bus
//! fires subscribers outside its lock and [`PatternImmunity::observe`]
//! ignores `PatternLearned` events, so the loop terminates by construction.
//!
//! Learned patterns persist as JSON at an injected path (tempfile-friendly),
//! and [`PatternImmunity::is_immune`] answers "have we seen this signature
//! often enough to treat it as known?".

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

use sha2::{Digest, Sha256};

use crate::security_events::{SecurityEvent, SecurityEventBus, SecurityEventType, Severity};

/// Observations of one signature required before it counts as immune
/// (the Python `known_patterns` promotion rule, pinned at 3 by the Q2 test).
pub const PATTERN_THRESHOLD: u64 = 3;

/// A learned threat pattern.
///
/// `id` is the SHA-256 digest of the normalized `kind` signature — stable
/// across restarts, so persistence merges rather than duplicates.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct ThreatPattern {
    /// SHA-256 hex digest of the normalized signature.
    pub id: String,
    /// Normalized signature: `event_type|tool_name|agent_id`.
    pub kind: String,
    /// Observations seen so far.
    pub count: u64,
    /// Unix epoch seconds of the first observation.
    pub first_seen: i64,
    /// Unix epoch seconds of the last observation.
    pub last_seen: i64,
    /// Highest severity observed for this signature.
    pub severity: Severity,
}

#[derive(Debug, Default, serde::Serialize, serde::Deserialize)]
struct PatternStore {
    patterns: Vec<ThreatPattern>,
}

/// The immune system: subscribes to the security event bus, learns repeated
/// threat signatures, and escalates at the threshold.
///
/// Interior state is behind a `Mutex`; share as `Arc<PatternImmunity>` (the
/// bus subscription constructed by [`PatternImmunity::subscribe_to_bus`]
/// already holds one).
#[derive(Debug)]
pub struct PatternImmunity {
    patterns: Mutex<HashMap<String, ThreatPattern>>,
    threshold: u64,
    bus: Option<Arc<SecurityEventBus>>,
    store_path: Option<PathBuf>,
}

impl PatternImmunity {
    /// Standalone immune system (no bus, no store). Prefer
    /// [`PatternImmunity::subscribe_to_bus`] for the wired loop.
    #[must_use]
    pub fn new(threshold: u64) -> Self {
        Self {
            patterns: Mutex::new(HashMap::new()),
            threshold,
            bus: None,
            store_path: None,
        }
    }

    /// Inject the JSON persistence path (tempfile-friendly; created on save).
    #[must_use]
    pub fn with_store(mut self, path: PathBuf) -> Self {
        self.store_path = Some(path);
        self
    }

    /// Build the immune system and wire it into the bus as a wildcard
    /// subscriber, returning the shared handle. This is the Q2 loop:
    /// bus events flow in, learned patterns flow back out as
    /// `PatternLearned` events.
    #[must_use]
    pub fn subscribe_to_bus(
        bus: &Arc<SecurityEventBus>,
        threshold: u64,
        store_path: Option<PathBuf>,
    ) -> Arc<Self> {
        let immunity = Arc::new(Self {
            patterns: Mutex::new(HashMap::new()),
            threshold,
            bus: Some(Arc::clone(bus)),
            store_path,
        });
        let observer = Arc::clone(&immunity);
        let _subscription = bus.subscribe_all(move |event| observer.observe(event));
        immunity
    }

    /// The normalized signature of an event:
    /// `event_type|tool_name|agent_id`, lowercased and trimmed.
    #[must_use]
    pub fn kind_for(event: &SecurityEvent) -> String {
        format!(
            "{}|{}|{}",
            event.event_type.as_str(),
            normalize(&event.tool_name),
            normalize(&event.agent_id)
        )
    }

    /// SHA-256 hex digest of a signature (the pattern id).
    #[must_use]
    pub fn digest(kind: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(normalize(kind).as_bytes());
        format!("{:x}", hasher.finalize())
    }

    /// Observe one event: increment the matching pattern or create it.
    /// When the count crosses the threshold exactly, persist the store
    /// (if wired) and emit a `PatternLearned` event back onto the bus
    /// (if wired). `PatternLearned` events are ignored — the loop must not
    /// feed on itself.
    pub fn observe(&self, event: &SecurityEvent) {
        if event.event_type == SecurityEventType::PatternLearned {
            return;
        }
        let kind = Self::kind_for(event);
        let id = Self::digest(&kind);
        let now = now_secs();
        let crossed = {
            let mut patterns = self
                .patterns
                .lock()
                .expect("pattern immunity lock poisoned");
            let entry = patterns.entry(id.clone()).or_insert_with(|| ThreatPattern {
                id: id.clone(),
                kind: kind.clone(),
                count: 0,
                first_seen: now,
                last_seen: now,
                severity: event.severity,
            });
            entry.count += 1;
            entry.last_seen = now;
            if event.severity > entry.severity {
                entry.severity = event.severity;
            }
            let crossed = entry.count == self.threshold;
            drop(patterns);
            crossed
        };
        if !crossed {
            return;
        }
        if self.store_path.is_some()
            && let Err(err) = self.save()
        {
            tracing::warn!("pattern immunity: could not persist store: {err}");
        }
        if let Some(bus) = &self.bus {
            let count = self
                .patterns
                .lock()
                .expect("pattern immunity lock poisoned")
                .get(&id)
                .map_or(self.threshold, |p| p.count);
            bus.publish(
                &SecurityEvent::new(SecurityEventType::PatternLearned, "pattern_immunity")
                    .with_detail(kind)
                    .with_severity(Severity::Medium)
                    .with_metadata("pattern_id", serde_json::Value::String(id))
                    .with_metadata("count", serde_json::json!(count))
                    .with_metadata("threshold", serde_json::json!(self.threshold)),
            );
        }
    }

    /// Whether the signature has been observed at least `threshold` times —
    /// the system is immune to it.
    #[must_use]
    pub fn is_immune(&self, kind: &str) -> bool {
        let id = Self::digest(kind);
        self.patterns
            .lock()
            .expect("pattern immunity lock poisoned")
            .get(&id)
            .is_some_and(|p| p.count >= self.threshold)
    }

    /// Snapshot of learned patterns, most-observed first.
    #[must_use]
    pub fn learned_patterns(&self) -> Vec<ThreatPattern> {
        let mut patterns: Vec<ThreatPattern> = self
            .patterns
            .lock()
            .expect("pattern immunity lock poisoned")
            .values()
            .cloned()
            .collect();
        patterns.sort_by(|a, b| b.count.cmp(&a.count).then_with(|| a.kind.cmp(&b.kind)));
        patterns
    }

    /// Number of distinct learned signatures.
    #[must_use]
    pub fn pattern_count(&self) -> usize {
        self.patterns
            .lock()
            .expect("pattern immunity lock poisoned")
            .len()
    }

    /// Persist the pattern store as JSON at the injected path.
    ///
    /// # Errors
    /// Propagates filesystem errors (missing/unwritable path).
    pub fn save(&self) -> std::io::Result<()> {
        let Some(path) = &self.store_path else {
            return Ok(());
        };
        let store = PatternStore {
            patterns: self.learned_patterns(),
        };
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let json = serde_json::to_string_pretty(&store).map_err(std::io::Error::other)?;
        std::fs::write(path, json)
    }

    /// Merge the persisted store into memory (existing entries win).
    /// Returns the number of patterns merged.
    ///
    /// # Errors
    /// Propagates filesystem and parse errors.
    pub fn load(&self) -> std::io::Result<usize> {
        let Some(path) = &self.store_path else {
            return Ok(0);
        };
        let raw = std::fs::read_to_string(path)?;
        let store: PatternStore = serde_json::from_str(&raw).map_err(std::io::Error::other)?;
        let mut patterns = self
            .patterns
            .lock()
            .expect("pattern immunity lock poisoned");
        let mut merged = 0;
        for pattern in store.patterns {
            let id = Self::digest(&pattern.kind);
            let should_insert = patterns
                .get(&id)
                .is_none_or(|existing| existing.count < pattern.count);
            if should_insert {
                patterns.insert(id, pattern);
                merged += 1;
            }
        }
        drop(patterns);
        Ok(merged)
    }
}

fn normalize(part: &str) -> String {
    part.trim().to_ascii_lowercase()
}

fn now_secs() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| i64::try_from(d.as_secs()).unwrap_or(i64::MAX))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    fn event(event_type: SecurityEventType, tool: &str, agent: &str) -> SecurityEvent {
        SecurityEvent::new(event_type, "test_source")
            .with_tool(tool)
            .with_agent(agent)
            .with_severity(Severity::High)
    }

    #[test]
    fn three_similar_events_learn_immunity() {
        let immunity = PatternImmunity::new(PATTERN_THRESHOLD);
        let kind = "dharma_blocked|tip.send|agent_1";
        assert!(!immunity.is_immune(kind));
        for _ in 0..3 {
            immunity.observe(&event(
                SecurityEventType::DharmaBlocked,
                "tip.send",
                "agent_1",
            ));
        }
        assert!(immunity.is_immune(kind));
        assert!(immunity.is_immune("DHARMA_BLOCKED|TIP.SEND|AGENT_1"));
    }

    #[test]
    fn below_threshold_is_not_immune() {
        let immunity = PatternImmunity::new(PATTERN_THRESHOLD);
        for _ in 0..(PATTERN_THRESHOLD - 1) {
            immunity.observe(&event(
                SecurityEventType::RateLimited,
                "tip.send",
                "agent_2",
            ));
        }
        assert!(!immunity.is_immune("rate_limited|tip.send|agent_2"));
        assert_eq!(immunity.pattern_count(), 1);
    }

    #[test]
    fn distinct_signatures_learn_separately() {
        let immunity = PatternImmunity::new(PATTERN_THRESHOLD);
        for _ in 0..3 {
            immunity.observe(&event(SecurityEventType::Quarantine, "mesh.join", "peer_a"));
        }
        immunity.observe(&event(SecurityEventType::Quarantine, "mesh.join", "peer_b"));
        assert!(immunity.is_immune("quarantine|mesh.join|peer_a"));
        assert!(!immunity.is_immune("quarantine|mesh.join|peer_b"));
        assert_eq!(immunity.pattern_count(), 2);
        let patterns = immunity.learned_patterns();
        assert_eq!(patterns.len(), 2);
        assert_eq!(patterns[0].count, 3);
    }

    #[test]
    fn pattern_learned_reemitted_once_closing_the_loop() {
        let bus = Arc::new(SecurityEventBus::new());
        let immunity = PatternImmunity::subscribe_to_bus(&bus, PATTERN_THRESHOLD, None);
        let learned = Arc::new(AtomicUsize::new(0));
        let l = Arc::clone(&learned);
        let _collector = bus.subscribe(SecurityEventType::PatternLearned, move |_e| {
            l.fetch_add(1, Ordering::Relaxed);
        });
        for _ in 0..5 {
            bus.publish(&event(SecurityEventType::Anomaly, "tool.x", "agent_9"));
        }
        assert!(immunity.is_immune("anomaly|tool.x|agent_9"));
        assert_eq!(learned.load(Ordering::Relaxed), 1, "escalate exactly once");
    }

    #[test]
    fn pattern_learned_events_are_not_self_observed() {
        let immunity = PatternImmunity::new(PATTERN_THRESHOLD);
        immunity.observe(&event(SecurityEventType::Quarantine, "mesh.join", "peer_c"));
        let before = immunity.pattern_count();
        immunity.observe(&SecurityEvent::new(
            SecurityEventType::PatternLearned,
            "pattern_immunity",
        ));
        assert_eq!(immunity.pattern_count(), before);
    }

    #[test]
    fn persistence_roundtrip() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let path = dir.path().join("immune").join("pattern_immunity.json");
        let first = PatternImmunity::new(PATTERN_THRESHOLD).with_store(path.clone());
        for _ in 0..3 {
            first.observe(&event(
                SecurityEventType::AuthFailure,
                "mesh.auth",
                "peer_d",
            ));
        }
        assert!(path.exists(), "store persisted at threshold crossing");
        let raw = std::fs::read_to_string(&path).expect("store file");
        let store: PatternStore = serde_json::from_str(&raw).expect("parse store");
        assert_eq!(store.patterns.len(), 1);

        let second = PatternImmunity::new(PATTERN_THRESHOLD).with_store(path);
        assert!(
            !second.is_immune("auth_failure|mesh.auth|peer_d"),
            "cold start"
        );
        let merged = second.load().expect("load");
        assert_eq!(merged, 1);
        assert!(second.is_immune("auth_failure|mesh.auth|peer_d"));
        let pattern = &second.learned_patterns()[0];
        assert_eq!(pattern.count, 3);
        assert_eq!(pattern.severity, Severity::High);
    }

    #[test]
    fn severity_escalates_to_maximum_observed() {
        let immunity = PatternImmunity::new(PATTERN_THRESHOLD);
        immunity
            .observe(&event(SecurityEventType::Anomaly, "t", "a").with_severity(Severity::Info));
        immunity.observe(
            &event(SecurityEventType::Anomaly, "t", "a").with_severity(Severity::Critical),
        );
        let pattern = immunity
            .learned_patterns()
            .into_iter()
            .next()
            .expect("pattern");
        assert_eq!(pattern.severity, Severity::Critical);
    }

    #[test]
    fn digest_is_stable_across_normalization() {
        let a = PatternImmunity::digest("Anomaly|Tool.X|AGENT_9");
        let b = PatternImmunity::digest("anomaly|tool.x|agent_9");
        assert_eq!(a, b);
        assert_eq!(a.len(), 64);
    }
}
