//! Security event bus — typed pub/sub channel for all governance security
//! modules.
//!
//! Rust port of the Python-era `whitemagic/security/event_bus.py`
//! (DEFERRED_OBJECTIVES_2026 Q2): every security seam (Dharma gate,
//! [`crate::Firebreak`], [`crate::EconomicFirewall`], Sangha quarantine,
//! engagement tokens) publishes events here, and subscribers such as
//! [`crate::PatternImmunity`] receive them in real time.
//!
//! Design parity with the Python original:
//! - typed + wildcard subscriptions, callbacks fire **outside** the bus lock
//!   (a subscriber may publish without deadlocking — the immune-system loop
//!   relies on this),
//! - bounded history ring ([`RING_CAPACITY`], the Python `deque(maxlen=…)`),
//! - per-type counters,
//! - optional JSONL persistence (same style as `economic_firewall.rs`).
//!
//! The Redis cross-process transport of the original is deliberately
//! unpromoted — WMv9 governance is in-process; `wm-sangha` is the mesh seam.

use std::collections::{HashMap, VecDeque};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

/// Bounded history ring capacity (Python `deque(maxlen=1024)`).
pub const RING_CAPACITY: usize = 1024;

/// JSONL file name used when a sink directory is attached.
const SINK_FILE: &str = "security_bus_events.jsonl";

/// Canonical security event classes.
///
/// Names align with the seams that emit them: `DharmaBlocked` (Dharma gate),
/// `FirebreakVeto` ([`crate::Firebreak`]), `EconomicDenied` /
/// `RateLimited` ([`crate::EconomicFirewall`]), `AuthFailure` / `Anomaly`
/// (network identity), `Quarantine` (Sangha bad-apple), `PatternLearned`
/// (the [`crate::PatternImmunity`] escalation emitted back onto the bus).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SecurityEventType {
    /// A dispatch blocked by the Dharma gate.
    DharmaBlocked,
    /// A dispatch vetoed by the Firebreak (forbidden pattern / scope law).
    FirebreakVeto,
    /// An economic action denied by the transaction firewall.
    EconomicDenied,
    /// A rate limit tripped.
    RateLimited,
    /// An authentication or signature failure.
    AuthFailure,
    /// A behavioral anomaly worth pattern learning.
    Anomaly,
    /// A peer (or payload) quarantined.
    Quarantine,
    /// The immune system auto-learned a threat pattern (escalation loop).
    PatternLearned,
}

impl SecurityEventType {
    /// Snake-case name, matching the Python `security.*` string convention
    /// (without the `security.` prefix).
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::DharmaBlocked => "dharma_blocked",
            Self::FirebreakVeto => "firebreak_veto",
            Self::EconomicDenied => "economic_denied",
            Self::RateLimited => "rate_limited",
            Self::AuthFailure => "auth_failure",
            Self::Anomaly => "anomaly",
            Self::Quarantine => "quarantine",
            Self::PatternLearned => "pattern_learned",
        }
    }
}

/// Severity of a security event (ordered low → critical).
#[derive(
    Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    /// Informational.
    Info,
    /// Low.
    Low,
    /// Medium — worth recording.
    Medium,
    /// High — pattern-learning material.
    High,
    /// Critical — escalation material.
    Critical,
}

impl Severity {
    /// Snake-case name, parity with the Python `info|low|medium|high|critical`.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Info => "info",
            Self::Low => "low",
            Self::Medium => "medium",
            Self::High => "high",
            Self::Critical => "critical",
        }
    }
}

/// A security event published to the bus.
///
/// Field parity with the Python `SecurityEvent` dataclass: `event_type`,
/// `source`, `severity`, `tool_name`, `agent_id`, `detail`, `metadata`,
/// `event_id`, `timestamp` (epoch seconds here, matching the crate).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SecurityEvent {
    /// Unique event id (UUID v4).
    pub event_id: String,
    /// Canonical event class.
    pub event_type: SecurityEventType,
    /// Module that emitted the event (e.g. `"transaction_firewall"`).
    pub source: String,
    /// Severity.
    pub severity: Severity,
    /// Producing tool call (empty when not applicable).
    pub tool_name: String,
    /// Initiating agent (empty when not applicable).
    pub agent_id: String,
    /// Human/agent-readable detail.
    pub detail: String,
    /// Free-form structured metadata.
    pub metadata: serde_json::Map<String, serde_json::Value>,
    /// Unix epoch seconds.
    pub timestamp: i64,
}

impl SecurityEvent {
    /// New event with a fresh UUID and wall-clock timestamp.
    #[must_use]
    pub fn new(event_type: SecurityEventType, source: impl Into<String>) -> Self {
        Self {
            event_id: uuid::Uuid::new_v4().to_string(),
            event_type,
            source: source.into(),
            severity: Severity::Info,
            tool_name: String::new(),
            agent_id: String::new(),
            detail: String::new(),
            metadata: serde_json::Map::new(),
            timestamp: now_secs(),
        }
    }

    /// Attach the producing tool call.
    #[must_use]
    pub fn with_tool(mut self, tool_name: impl Into<String>) -> Self {
        self.tool_name = tool_name.into();
        self
    }

    /// Attach the initiating agent.
    #[must_use]
    pub fn with_agent(mut self, agent_id: impl Into<String>) -> Self {
        self.agent_id = agent_id.into();
        self
    }

    /// Attach human-readable detail.
    #[must_use]
    pub fn with_detail(mut self, detail: impl Into<String>) -> Self {
        self.detail = detail.into();
        self
    }

    /// Set the severity.
    #[must_use]
    pub const fn with_severity(mut self, severity: Severity) -> Self {
        self.severity = severity;
        self
    }

    /// Attach one metadata entry.
    #[must_use]
    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }

    /// Pin the timestamp (tests, replays).
    #[must_use]
    pub const fn with_timestamp(mut self, timestamp: i64) -> Self {
        self.timestamp = timestamp;
        self
    }
}

type Subscriber = Arc<dyn Fn(&SecurityEvent) + Send + Sync>;

struct Subscription {
    id: u64,
    callback: Subscriber,
}
// The callback is intentionally omitted from the debug output — it is not printable.
#[allow(clippy::missing_fields_in_debug)]
impl std::fmt::Debug for Subscription {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Subscription")
            .field("id", &self.id)
            .finish()
    }
}

#[derive(Debug, Default)]
struct Inner {
    history: VecDeque<SecurityEvent>,
    typed: HashMap<SecurityEventType, Vec<Subscription>>,
    wildcard: Vec<Subscription>,
    stats: HashMap<SecurityEventType, u64>,
    next_id: u64,
}

/// The unified security event bus.
///
/// `Arc`-shareable: interior state is behind a `Mutex`, and subscriber
/// callbacks are invoked outside the lock, so a subscriber may publish
/// (the [`crate::PatternImmunity`] `PatternLearned` loop does exactly that).
pub struct SecurityEventBus {
    inner: Mutex<Inner>,
    sink_dir: Option<PathBuf>,
}

impl std::fmt::Debug for SecurityEventBus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let inner = self.inner.lock().expect("security event bus lock poisoned");
        f.debug_struct("SecurityEventBus")
            .field("history_len", &inner.history.len())
            .field(
                "subscriber_count",
                &(inner.wildcard.len() + inner.typed.values().map(Vec::len).sum::<usize>()),
            )
            .field("stats", &inner.stats)
            .field("sink_dir", &self.sink_dir)
            .finish()
    }
}

impl Default for SecurityEventBus {
    fn default() -> Self {
        Self::new()
    }
}

impl SecurityEventBus {
    /// Empty bus, unbounded subscribers, no persistence sink.
    #[must_use]
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(Inner::default()),
            sink_dir: None,
        }
    }

    /// Attach a JSONL sink directory: every published event is appended to
    /// `<dir>/security_bus_events.jsonl` (same style as `economic_firewall`).
    #[must_use]
    pub fn with_jsonl_dir(mut self, dir: PathBuf) -> Self {
        self.sink_dir = Some(dir);
        self
    }

    /// Subscribe to one event class. Returns the subscription id for
    /// [`SecurityEventBus::unsubscribe`].
    #[must_use]
    pub fn subscribe(
        &self,
        event_type: SecurityEventType,
        callback: impl Fn(&SecurityEvent) + Send + Sync + 'static,
    ) -> u64 {
        let mut inner = self.inner.lock().expect("security event bus lock poisoned");
        inner.next_id += 1;
        let id = inner.next_id;
        inner
            .typed
            .entry(event_type)
            .or_default()
            .push(Subscription {
                id,
                callback: Arc::new(callback),
            });
        id
    }

    /// Subscribe to every event class (the Python wildcard subscriber).
    #[must_use]
    pub fn subscribe_all(&self, callback: impl Fn(&SecurityEvent) + Send + Sync + 'static) -> u64 {
        let mut inner = self.inner.lock().expect("security event bus lock poisoned");
        inner.next_id += 1;
        let id = inner.next_id;
        inner.wildcard.push(Subscription {
            id,
            callback: Arc::new(callback),
        });
        id
    }

    /// Remove a subscription by id (typed and wildcard). Unknown ids are
    /// silently ignored, parity with the Python `unsubscribe`.
    pub fn unsubscribe(&self, id: u64) {
        let mut inner = self.inner.lock().expect("security event bus lock poisoned");
        for list in inner.typed.values_mut() {
            list.retain(|sub| sub.id != id);
        }
        inner.wildcard.retain(|sub| sub.id != id);
    }

    /// Publish an event: append to the history ring, bump per-type stats,
    /// then invoke matching subscribers **outside** the bus lock. Subscriber
    /// panics propagate; errors in the JSONL sink are logged, never fatal.
    pub fn publish(&self, event: &SecurityEvent) {
        let (subscribers, sink_line) = {
            let mut inner = self.inner.lock().expect("security event bus lock poisoned");
            if inner.history.len() >= RING_CAPACITY {
                inner.history.pop_front();
            }
            inner.history.push_back(event.clone());
            *inner.stats.entry(event.event_type).or_default() += 1;
            let mut subscribers: Vec<Subscriber> = Vec::new();
            if let Some(list) = inner.typed.get(&event.event_type) {
                subscribers.extend(list.iter().map(|sub| Arc::clone(&sub.callback)));
            }
            subscribers.extend(inner.wildcard.iter().map(|sub| Arc::clone(&sub.callback)));
            let sink_line = self
                .sink_dir
                .as_ref()
                .map(|dir| (dir.clone(), serde_json::to_string(event)));
            drop(inner);
            (subscribers, sink_line)
        };
        for subscriber in &subscribers {
            subscriber(event);
        }
        if let Some((dir, line)) = sink_line {
            match line {
                Ok(line) => {
                    if let Err(err) = append_jsonl(&dir, SINK_FILE, &line) {
                        tracing::warn!("security event bus: could not append to sink: {err}");
                    }
                }
                Err(err) => {
                    tracing::warn!("security event bus: could not serialize event: {err}");
                }
            }
        }
    }

    /// Snapshot of the history ring (oldest → newest).
    #[must_use]
    pub fn history(&self) -> Vec<SecurityEvent> {
        self.inner
            .lock()
            .expect("security event bus lock poisoned")
            .history
            .iter()
            .cloned()
            .collect()
    }

    /// Event statistics: ring occupancy, per-type counters, subscribers.
    #[must_use]
    pub fn stats(&self) -> BusStats {
        let inner = self.inner.lock().expect("security event bus lock poisoned");
        BusStats {
            total_events: inner.history.len(),
            by_type: inner.stats.clone(),
            subscriber_count: inner.wildcard.len()
                + inner.typed.values().map(Vec::len).sum::<usize>(),
        }
    }
}

/// Bus statistics, parity with the Python `stats()` dict.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct BusStats {
    /// Events currently held by the history ring.
    pub total_events: usize,
    /// Lifetime publish counter per event type.
    pub by_type: HashMap<SecurityEventType, u64>,
    /// Active typed + wildcard subscriptions.
    pub subscriber_count: usize,
}

fn append_jsonl(dir: &Path, file: &str, line: &str) -> std::io::Result<()> {
    let path = dir.join(file);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    use std::io::Write;
    let mut f = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)?;
    f.write_all(line.as_bytes())?;
    f.write_all(b"\n")
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

    fn event(event_type: SecurityEventType, detail: &str) -> SecurityEvent {
        SecurityEvent::new(event_type, "test_source")
            .with_tool("tip.send")
            .with_agent("agent_1")
            .with_detail(detail)
            .with_severity(Severity::Medium)
            .with_timestamp(1_789_000_000)
    }

    #[test]
    fn subscribe_delivers_matching_and_wildcard_receives_all() {
        let bus = SecurityEventBus::new();
        let typed_hits = Arc::new(AtomicUsize::new(0));
        let wildcard_hits = Arc::new(AtomicUsize::new(0));
        let t = Arc::clone(&typed_hits);
        let _typed = bus.subscribe(SecurityEventType::DharmaBlocked, move |_e| {
            t.fetch_add(1, Ordering::Relaxed);
        });
        let w = Arc::clone(&wildcard_hits);
        let _wildcard = bus.subscribe_all(move |_e| {
            w.fetch_add(1, Ordering::Relaxed);
        });
        bus.publish(&event(SecurityEventType::DharmaBlocked, "one"));
        bus.publish(&event(SecurityEventType::RateLimited, "two"));
        assert_eq!(typed_hits.load(Ordering::Relaxed), 1);
        assert_eq!(wildcard_hits.load(Ordering::Relaxed), 2);
        let stats = bus.stats();
        assert_eq!(stats.total_events, 2);
        assert_eq!(stats.subscriber_count, 2);
    }

    #[test]
    fn unsubscribe_stops_delivery() {
        let bus = SecurityEventBus::new();
        let hits = Arc::new(AtomicUsize::new(0));
        let h = Arc::clone(&hits);
        let id = bus.subscribe_all(move |_e| {
            h.fetch_add(1, Ordering::Relaxed);
        });
        bus.publish(&event(SecurityEventType::Anomaly, "one"));
        bus.unsubscribe(id);
        bus.publish(&event(SecurityEventType::Anomaly, "two"));
        assert_eq!(hits.load(Ordering::Relaxed), 1);
        assert_eq!(bus.stats().subscriber_count, 0);
    }

    #[test]
    fn history_ring_is_bounded() {
        let bus = SecurityEventBus::new();
        for i in 0..(RING_CAPACITY + 16) {
            bus.publish(&event(SecurityEventType::Anomaly, &format!("e{i}")));
        }
        let history = bus.history();
        assert_eq!(history.len(), RING_CAPACITY);
        assert_eq!(history[0].detail, "e16");
        assert_eq!(history.last().map(|e| e.detail.as_str()), Some("e1039"));
    }

    #[test]
    fn jsonl_sink_writes_one_line_per_event() {
        let dir = tempfile::tempdir().expect("tmpdir");
        let bus = SecurityEventBus::new().with_jsonl_dir(dir.path().to_path_buf());
        bus.publish(&event(SecurityEventType::Quarantine, "bad peer"));
        bus.publish(&event(SecurityEventType::AuthFailure, "bad sig"));
        let raw = std::fs::read_to_string(dir.path().join(SINK_FILE)).expect("sink file");
        let lines: Vec<&str> = raw.lines().collect();
        assert_eq!(lines.len(), 2);
        let parsed: SecurityEvent = serde_json::from_str(lines[0]).expect("parse");
        assert_eq!(parsed.event_type, SecurityEventType::Quarantine);
        assert_eq!(parsed.severity, Severity::Medium);
    }

    #[test]
    fn severity_orders_low_to_critical() {
        assert!(Severity::Critical > Severity::Info);
        assert!(Severity::High > Severity::Medium);
        assert_eq!(Severity::Medium.as_str(), "medium");
    }

    #[test]
    fn event_type_names_match_python_convention() {
        assert_eq!(SecurityEventType::DharmaBlocked.as_str(), "dharma_blocked");
        assert_eq!(SecurityEventType::FirebreakVeto.as_str(), "firebreak_veto");
        assert_eq!(
            SecurityEventType::EconomicDenied.as_str(),
            "economic_denied"
        );
        assert_eq!(
            serde_json::to_string(&SecurityEventType::PatternLearned).expect("serde"),
            "\"pattern_learned\""
        );
    }

    #[test]
    fn subscriber_may_publish_without_deadlock() {
        // The immune-system loop shape: a wildcard subscriber publishes a
        // PatternLearned event back onto the bus from inside its callback.
        let bus = Arc::new(SecurityEventBus::new());
        let publisher = Arc::clone(&bus);
        let learned = Arc::new(AtomicUsize::new(0));
        let l = Arc::clone(&learned);
        let _loop = bus.subscribe_all(move |e| {
            if e.event_type == SecurityEventType::Anomaly {
                publisher.publish(&event(SecurityEventType::PatternLearned, "loop"));
            } else if e.event_type == SecurityEventType::PatternLearned {
                l.fetch_add(1, Ordering::Relaxed);
            }
        });
        bus.publish(&event(SecurityEventType::Anomaly, "trigger"));
        assert_eq!(learned.load(Ordering::Relaxed), 1);
    }
}
