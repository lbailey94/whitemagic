//! Gan Ying Bus (感應) — full system resonance event bus.
//!
//! The bus supports:
//! - Subscribe to individual event types or entire categories
//! - Emit events with optional cascade propagation
//! - Synchronous callback dispatch (no async runtime required)
//! - Per-subscriber filtering and priority
//!
//! "Things that accord in tone vibrate together" — the Gan Ying Bus
//! connects all subsystems of WhiteMagic v5 through event resonance.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::resonance::event_type::{EventCategory, EventType};

// ── Resonance Event ───────────────────────────────────────────────────

/// A resonance event on the Gan Ying Bus.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResonanceEvent {
    /// The event type.
    pub event_type: EventType,
    /// Source subsystem that emitted the event.
    pub source: String,
    /// JSON payload with event-specific data.
    pub payload: serde_json::Value,
    /// Salience score (0.0–1.0) — higher = more important.
    pub salience: f32,
    /// When the event was emitted.
    pub timestamp: DateTime<Utc>,
    /// Whether this event should cascade to related event types.
    pub cascade: bool,
    /// Depth of cascade chain (0 = original, 1 = first cascade, etc.).
    pub cascade_depth: u8,
}

impl ResonanceEvent {
    /// Create a new resonance event.
    #[must_use]
    pub fn new(
        event_type: EventType,
        source: impl Into<String>,
        payload: serde_json::Value,
    ) -> Self {
        Self {
            event_type,
            source: source.into(),
            payload,
            salience: 0.5,
            timestamp: Utc::now(),
            cascade: false,
            cascade_depth: 0,
        }
    }

    /// Set the salience score.
    #[must_use]
    pub const fn with_salience(mut self, salience: f32) -> Self {
        self.salience = salience.clamp(0.0, 1.0);
        self
    }

    /// Enable cascade propagation.
    #[must_use]
    pub const fn with_cascade(mut self) -> Self {
        self.cascade = true;
        self
    }

    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "event_type": self.event_type.as_str(),
            "source": self.source,
            "payload": self.payload,
            "salience": self.salience,
            "timestamp": self.timestamp.to_rfc3339(),
            "cascade": self.cascade,
            "cascade_depth": self.cascade_depth,
        })
    }
}

// ── Subscription ──────────────────────────────────────────────────────

/// A subscription filter — determines which events a subscriber receives.
#[derive(Debug, Clone)]
pub enum SubscriptionFilter {
    /// Subscribe to a single event type.
    EventType(EventType),
    /// Subscribe to all events in a category.
    Category(EventCategory),
    /// Subscribe to multiple specific event types.
    EventTypes(Vec<EventType>),
    /// Subscribe to all events (wildcard).
    All,
}

impl SubscriptionFilter {
    /// Check if an event matches this filter.
    #[must_use]
    pub fn matches(&self, event_type: EventType) -> bool {
        match self {
            Self::EventType(t) => *t == event_type,
            Self::Category(c) => event_type.category() == *c,
            Self::EventTypes(types) => types.contains(&event_type),
            Self::All => true,
        }
    }
}

/// Unique subscription identifier.
pub type SubscriptionId = u64;

/// A callback for receiving resonance events.
pub type EventCallback = Box<dyn Fn(&ResonanceEvent) + Send + Sync>;

/// A subscription on the Gan Ying Bus.
struct Subscription {
    id: SubscriptionId,
    filter: SubscriptionFilter,
    callback: EventCallback,
    /// Number of times this subscription has been triggered.
    trigger_count: u64,
}

impl std::fmt::Debug for Subscription {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Subscription")
            .field("id", &self.id)
            .field("filter", &self.filter)
            .field("trigger_count", &self.trigger_count)
            .finish_non_exhaustive()
    }
}

// ── Cascade Rules ─────────────────────────────────────────────────────

/// Cascade rules define which event types propagate to other event types.
///
/// When an event with `cascade: true` is emitted, the bus checks the
/// cascade rules and emits derived events (with `cascade_depth + 1`).
/// Cascade depth is capped at `MAX_CASCADE_DEPTH` to prevent infinite
/// loops.
pub const MAX_CASCADE_DEPTH: u8 = 5;

/// Default cascade rules — derived from v2's cascade configuration.
///
/// These define which events naturally propagate to related events.
/// For example, `ToolDispatchError` cascades to `DharmaWarn` (governance
/// gets notified of tool failures).
#[must_use]
pub fn default_cascade_rules() -> HashMap<EventType, Vec<EventType>> {
    let mut rules = HashMap::new();

    // Tool errors cascade to governance
    rules.insert(EventType::ToolDispatchError, vec![EventType::DharmaWarn]);
    rules.insert(EventType::ToolDispatchTimeout, vec![EventType::DharmaWarn]);
    rules.insert(
        EventType::ToolCircuitBroken,
        vec![EventType::CircuitBreakerOpen],
    );

    // Anomalies cascade to homeostatic observe
    rules.insert(
        EventType::HarmonyAnomalyDetected,
        vec![EventType::HarmonyHomeostaticObserve],
    );
    rules.insert(
        EventType::HarmonyAnomalyCritical,
        vec![
            EventType::HarmonyHomeostaticIntervene,
            EventType::DharmaWarn,
        ],
    );

    // System warnings cascade to harmony
    rules.insert(
        EventType::SystemMemoryWarning,
        vec![EventType::HarmonyMemorySpike],
    );
    rules.insert(
        EventType::SystemCpuWarning,
        vec![EventType::HarmonyCpuSpike],
    );
    rules.insert(
        EventType::SystemThermalWarning,
        vec![EventType::HarmonyThermalAlert],
    );
    rules.insert(
        EventType::SystemBatteryLow,
        vec![EventType::HarmonyBatteryAlert],
    );

    // Brain wave changes cascade to consciousness
    rules.insert(EventType::BrainWaveTheta, vec![EventType::DreamCycleStart]);
    rules.insert(
        EventType::BrainWaveGamma,
        vec![EventType::DreamCycleComplete],
    );

    // Drive events cascade
    rules.insert(EventType::DriveEnergyLow, vec![EventType::DriveRestTrigger]);
    rules.insert(
        EventType::DriveCuriositySpike,
        vec![EventType::DriveExplorationTrigger],
    );

    // Circuit breaker cascade
    rules.insert(
        EventType::CircuitBreakerOpen,
        vec![EventType::ToolCircuitBroken],
    );
    rules.insert(
        EventType::CircuitBreakerClose,
        vec![EventType::ToolPromoted],
    );

    // Memory consolidation cascade
    rules.insert(
        EventType::DreamConsolidationComplete,
        vec![
            EventType::MemoryConsolidated,
            EventType::DreamArtifactCreated,
        ],
    );

    // Sensor errors cascade to reflex
    rules.insert(EventType::SensorError, vec![EventType::ReflexSafeState]);
    rules.insert(
        EventType::ActuatorError,
        vec![EventType::ReflexEmergencyStop],
    );

    // Peer loss cascades to sangha
    rules.insert(EventType::PeerLost, vec![EventType::PeerHealthTimeout]);

    rules
}

// ── Gan Ying Bus ──────────────────────────────────────────────────────

/// Statistics for the Gan Ying Bus.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct BusStats {
    /// Total events emitted.
    pub events_emitted: u64,
    /// Total cascade events generated.
    pub cascade_events: u64,
    /// Total subscriber triggers.
    pub subscriber_triggers: u64,
    /// Events per category.
    pub events_per_category: HashMap<String, u64>,
    /// Active subscriptions.
    pub active_subscriptions: usize,
}

/// The Gan Ying Bus — full system resonance event bus.
///
/// Supports subscribe/emit/cascade with synchronous callback dispatch.
/// All callbacks are invoked synchronously during `emit()`, so long-running
/// callbacks will block emission. For async use cases, wrap the bus in
/// a tokio task and use channels.
///
/// # Example
/// ```no_run
/// use wm_cognitive::{GanYingBus, EventType, EventCategory, ResonanceEvent, SubscriptionFilter};
///
/// let mut bus = GanYingBus::default();
///
/// // Subscribe to all memory events
/// let _id = bus.subscribe(
///     SubscriptionFilter::Category(EventCategory::Memory),
///     Box::new(|event: &ResonanceEvent| {
///         println!("Memory event: {}", event.event_type);
///     }),
/// );
///
/// // Emit an event
/// bus.emit(EventType::MemoryCreated, "test", serde_json::json!({"id": 42}));
/// ```
pub struct GanYingBus {
    subscriptions: Vec<Subscription>,
    cascade_rules: HashMap<EventType, Vec<EventType>>,
    next_id: AtomicU64,
    events_emitted: AtomicU64,
    cascade_events: AtomicU64,
    subscriber_triggers: AtomicU64,
    events_per_category: HashMap<String, u64>,
    /// Recent event ring buffer (for synchronicity detection).
    recent_events: std::collections::VecDeque<ResonanceEvent>,
    /// Maximum recent events to retain.
    recent_capacity: usize,
    /// Optional JSONL write-through persistence path for the event log.
    persist_path: Option<PathBuf>,
}

impl Default for GanYingBus {
    fn default() -> Self {
        Self::new(256)
    }
}

impl std::fmt::Debug for GanYingBus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("GanYingBus")
            .field("subscriptions", &self.subscriptions.len())
            .field(
                "events_emitted",
                &self.events_emitted.load(Ordering::Relaxed),
            )
            .field(
                "cascade_events",
                &self.cascade_events.load(Ordering::Relaxed),
            )
            .finish_non_exhaustive()
    }
}

impl GanYingBus {
    /// Create a new bus with the given recent-event capacity.
    #[must_use]
    pub fn new(recent_capacity: usize) -> Self {
        Self {
            subscriptions: Vec::new(),
            cascade_rules: default_cascade_rules(),
            next_id: AtomicU64::new(1),
            events_emitted: AtomicU64::new(0),
            cascade_events: AtomicU64::new(0),
            subscriber_triggers: AtomicU64::new(0),
            events_per_category: HashMap::new(),
            recent_events: std::collections::VecDeque::with_capacity(recent_capacity),
            recent_capacity,
            persist_path: None,
        }
    }

    /// Enable write-through persistence of events to a JSONL file.
    ///
    /// Seeds the recent-event ring buffer from the tail of an existing log,
    /// then appends every subsequent event. If the existing log exceeds
    /// 5 MiB it is truncated first, keeping the on-disk log bounded across
    /// restarts.
    pub fn enable_persistence(&mut self, path: impl Into<PathBuf>) {
        let path = path.into();
        if let Ok(contents) = std::fs::read_to_string(&path) {
            let lines: Vec<&str> = contents.lines().collect();
            let start = lines.len().saturating_sub(self.recent_capacity);
            for line in &lines[start..] {
                if let Ok(event) = serde_json::from_str::<ResonanceEvent>(line) {
                    if self.recent_events.len() >= self.recent_capacity {
                        self.recent_events.pop_front();
                    }
                    self.recent_events.push_back(event);
                }
            }
            if contents.len() > 5 * 1024 * 1024 {
                let _ = std::fs::write(&path, "");
            }
        }
        self.persist_path = Some(path);
    }

    /// Path to the persistence file, if persistence is enabled.
    #[must_use]
    pub fn persist_path(&self) -> Option<&Path> {
        self.persist_path.as_deref()
    }

    /// Subscribe to events matching the given filter.
    ///
    /// Returns a [`SubscriptionId`] that can be used to unsubscribe.
    pub fn subscribe(
        &mut self,
        filter: SubscriptionFilter,
        callback: EventCallback,
    ) -> SubscriptionId {
        let id = self.next_id.fetch_add(1, Ordering::Relaxed);
        self.subscriptions.push(Subscription {
            id,
            filter,
            callback,
            trigger_count: 0,
        });
        id
    }

    /// Unsubscribe by ID. Returns `true` if the subscription was found.
    pub fn unsubscribe(&mut self, id: SubscriptionId) -> bool {
        let len_before = self.subscriptions.len();
        self.subscriptions.retain(|s| s.id != id);
        self.subscriptions.len() < len_before
    }

    /// Emit an event to all matching subscribers.
    ///
    /// If the event has `cascade: true`, derived events are also emitted
    /// (up to [`MAX_CASCADE_DEPTH`]).
    ///
    /// Returns the total number of subscriber triggers (including cascades).
    pub fn emit(
        &mut self,
        event_type: EventType,
        source: impl Into<String>,
        payload: serde_json::Value,
    ) -> u64 {
        let event = ResonanceEvent::new(event_type, source, payload);
        self.emit_event(&event)
    }

    /// Emit a pre-constructed event.
    pub fn emit_event(&mut self, event: &ResonanceEvent) -> u64 {
        let mut total_triggers = 0u64;

        // Emit the original event
        total_triggers += self.dispatch_to_subscribers(event);

        // Handle cascade
        if event.cascade && event.cascade_depth < MAX_CASCADE_DEPTH {
            let cascade_types = self.cascade_rules.get(&event.event_type).cloned();
            if let Some(cascade_types) = cascade_types {
                for ct in cascade_types {
                    let cascade_event = ResonanceEvent {
                        event_type: ct,
                        source: event.source.clone(),
                        payload: event.payload.clone(),
                        salience: event.salience * 0.8, // Cascade slightly reduces salience
                        timestamp: Utc::now(),
                        cascade: false, // Prevent recursive cascade from cascade events
                        cascade_depth: event.cascade_depth + 1,
                    };
                    self.cascade_events.fetch_add(1, Ordering::Relaxed);
                    total_triggers += self.dispatch_to_subscribers(&cascade_event);
                }
            }
        }

        total_triggers
    }

    /// Emit with salience and cascade flags.
    pub fn emit_with(
        &mut self,
        event_type: EventType,
        source: impl Into<String>,
        payload: serde_json::Value,
        salience: f32,
        cascade: bool,
    ) -> u64 {
        let event = ResonanceEvent::new(event_type, source, payload).with_salience(salience);
        let mut event = if cascade { event.with_cascade() } else { event };
        event.cascade = cascade;
        self.emit_event(&event)
    }

    /// Dispatch an event to all matching subscribers.
    fn dispatch_to_subscribers(&mut self, event: &ResonanceEvent) -> u64 {
        self.events_emitted.fetch_add(1, Ordering::Relaxed);

        // Update category stats
        *self
            .events_per_category
            .entry(event.event_type.category().as_str().to_string())
            .or_insert(0) += 1;

        // Store in recent events ring buffer
        if self.recent_events.len() >= self.recent_capacity {
            self.recent_events.pop_front();
        }
        self.recent_events.push_back(event.clone());

        // Write-through persistence (best-effort JSONL append)
        if let Some(path) = &self.persist_path {
            if let Ok(mut file) = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(path)
            {
                if let Ok(line) = serde_json::to_string(event) {
                    let _ = writeln!(file, "{line}");
                }
            }
        }

        // Dispatch to matching subscribers
        let mut triggers = 0u64;
        for sub in &mut self.subscriptions {
            if sub.filter.matches(event.event_type) {
                (sub.callback)(event);
                sub.trigger_count += 1;
                triggers += 1;
            }
        }

        self.subscriber_triggers
            .fetch_add(triggers, Ordering::Relaxed);
        triggers
    }

    /// Number of active subscriptions.
    #[must_use]
    pub fn subscription_count(&self) -> usize {
        self.subscriptions.len()
    }

    /// Total events emitted.
    #[must_use]
    pub fn events_emitted(&self) -> u64 {
        self.events_emitted.load(Ordering::Relaxed)
    }

    /// Total cascade events generated.
    #[must_use]
    pub fn cascade_events(&self) -> u64 {
        self.cascade_events.load(Ordering::Relaxed)
    }

    /// Total subscriber triggers.
    #[must_use]
    pub fn subscriber_triggers(&self) -> u64 {
        self.subscriber_triggers.load(Ordering::Relaxed)
    }

    /// Get recent events (newest first, up to `limit`).
    #[must_use]
    pub fn recent_events(&self, limit: usize) -> Vec<&ResonanceEvent> {
        self.recent_events.iter().rev().take(limit).collect()
    }

    /// Add a custom cascade rule.
    pub fn add_cascade_rule(&mut self, from: EventType, to: Vec<EventType>) {
        self.cascade_rules.insert(from, to);
    }

    /// Remove a cascade rule.
    pub fn remove_cascade_rule(&mut self, from: EventType) -> bool {
        self.cascade_rules.remove(&from).is_some()
    }

    /// Get bus statistics.
    #[must_use]
    pub fn stats(&self) -> BusStats {
        BusStats {
            events_emitted: self.events_emitted.load(Ordering::Relaxed),
            cascade_events: self.cascade_events.load(Ordering::Relaxed),
            subscriber_triggers: self.subscriber_triggers.load(Ordering::Relaxed),
            events_per_category: self.events_per_category.clone(),
            active_subscriptions: self.subscriptions.len(),
        }
    }

    /// Clear all subscriptions and stats.
    pub fn clear(&mut self) {
        self.subscriptions.clear();
        self.recent_events.clear();
        self.events_per_category.clear();
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::sync::atomic::{AtomicUsize, Ordering as AtomicOrdering};

    #[test]
    fn subscribe_and_emit_single_type() {
        let mut bus = GanYingBus::default();
        let counter = Arc::new(AtomicUsize::new(0));
        let c = counter.clone();

        let _id = bus.subscribe(
            SubscriptionFilter::EventType(EventType::MemoryCreated),
            Box::new(move |_event| {
                c.fetch_add(1, AtomicOrdering::Relaxed);
            }),
        );

        bus.emit(EventType::MemoryCreated, "test", serde_json::json!({}));
        bus.emit(EventType::MemoryUpdated, "test", serde_json::json!({}));

        assert_eq!(counter.load(AtomicOrdering::Relaxed), 1);
    }

    #[test]
    fn subscribe_to_category() {
        let mut bus = GanYingBus::default();
        let counter = Arc::new(AtomicUsize::new(0));
        let c = counter.clone();

        let _id = bus.subscribe(
            SubscriptionFilter::Category(EventCategory::Memory),
            Box::new(move |_event| {
                c.fetch_add(1, AtomicOrdering::Relaxed);
            }),
        );

        bus.emit(EventType::MemoryCreated, "test", serde_json::json!({}));
        bus.emit(EventType::MemoryDeleted, "test", serde_json::json!({}));
        bus.emit(EventType::SystemStartup, "test", serde_json::json!({}));

        assert_eq!(counter.load(AtomicOrdering::Relaxed), 2);
    }

    #[test]
    fn subscribe_to_all() {
        let mut bus = GanYingBus::default();
        let counter = Arc::new(AtomicUsize::new(0));
        let c = counter.clone();

        let _id = bus.subscribe(
            SubscriptionFilter::All,
            Box::new(move |_event| {
                c.fetch_add(1, AtomicOrdering::Relaxed);
            }),
        );

        bus.emit(EventType::SystemStartup, "test", serde_json::json!({}));
        bus.emit(EventType::MemoryCreated, "test", serde_json::json!({}));
        bus.emit(EventType::CittaAdvance, "test", serde_json::json!({}));

        assert_eq!(counter.load(AtomicOrdering::Relaxed), 3);
    }

    #[test]
    fn subscribe_to_multiple_types() {
        let mut bus = GanYingBus::default();
        let counter = Arc::new(AtomicUsize::new(0));
        let c = counter.clone();

        let _id = bus.subscribe(
            SubscriptionFilter::EventTypes(vec![
                EventType::MemoryCreated,
                EventType::MemoryDeleted,
            ]),
            Box::new(move |_event| {
                c.fetch_add(1, AtomicOrdering::Relaxed);
            }),
        );

        bus.emit(EventType::MemoryCreated, "test", serde_json::json!({}));
        bus.emit(EventType::MemoryDeleted, "test", serde_json::json!({}));
        bus.emit(EventType::MemoryUpdated, "test", serde_json::json!({}));

        assert_eq!(counter.load(AtomicOrdering::Relaxed), 2);
    }

    #[test]
    fn unsubscribe_removes_callback() {
        let mut bus = GanYingBus::default();
        let counter = Arc::new(AtomicUsize::new(0));
        let c = counter.clone();

        let id = bus.subscribe(
            SubscriptionFilter::EventType(EventType::MemoryCreated),
            Box::new(move |_event| {
                c.fetch_add(1, AtomicOrdering::Relaxed);
            }),
        );

        bus.emit(EventType::MemoryCreated, "test", serde_json::json!({}));
        assert_eq!(counter.load(AtomicOrdering::Relaxed), 1);

        assert!(bus.unsubscribe(id));
        bus.emit(EventType::MemoryCreated, "test", serde_json::json!({}));
        assert_eq!(counter.load(AtomicOrdering::Relaxed), 1);
    }

    #[test]
    fn unsubscribe_nonexistent_returns_false() {
        let mut bus = GanYingBus::default();
        assert!(!bus.unsubscribe(999));
    }

    #[test]
    fn cascade_propagates() {
        let mut bus = GanYingBus::default();
        let counter = Arc::new(AtomicUsize::new(0));
        let c = counter.clone();

        // Subscribe to the cascade target
        let _id = bus.subscribe(
            SubscriptionFilter::EventType(EventType::DharmaWarn),
            Box::new(move |_event| {
                c.fetch_add(1, AtomicOrdering::Relaxed);
            }),
        );

        // ToolDispatchError cascades to DharmaWarn
        bus.emit_with(
            EventType::ToolDispatchError,
            "test",
            serde_json::json!({}),
            0.8,
            true,
        );

        assert_eq!(counter.load(AtomicOrdering::Relaxed), 1);
        assert!(bus.cascade_events() > 0);
    }

    #[test]
    fn no_cascade_when_flag_false() {
        let mut bus = GanYingBus::default();
        let counter = Arc::new(AtomicUsize::new(0));
        let c = counter.clone();

        let _id = bus.subscribe(
            SubscriptionFilter::EventType(EventType::DharmaWarn),
            Box::new(move |_event| {
                c.fetch_add(1, AtomicOrdering::Relaxed);
            }),
        );

        bus.emit_with(
            EventType::ToolDispatchError,
            "test",
            serde_json::json!({}),
            0.8,
            false,
        );

        assert_eq!(counter.load(AtomicOrdering::Relaxed), 0);
        assert_eq!(bus.cascade_events(), 0);
    }

    #[test]
    fn cascade_depth_capped() {
        let mut bus = GanYingBus::default();

        // Create a circular cascade rule: A → B → A
        bus.add_cascade_rule(EventType::SystemStartup, vec![EventType::SystemShutdown]);
        bus.add_cascade_rule(EventType::SystemShutdown, vec![EventType::SystemStartup]);

        // This should not infinite loop
        bus.emit_with(
            EventType::SystemStartup,
            "test",
            serde_json::json!({}),
            0.5,
            true,
        );

        // Should have emitted some events but not infinite
        assert!(bus.events_emitted() < 20);
    }

    #[test]
    fn custom_cascade_rule() {
        let mut bus = GanYingBus::default();
        bus.add_cascade_rule(EventType::MemoryCreated, vec![EventType::MemoryEmbedded]);

        let counter = Arc::new(AtomicUsize::new(0));
        let c = counter.clone();

        let _id = bus.subscribe(
            SubscriptionFilter::EventType(EventType::MemoryEmbedded),
            Box::new(move |_event| {
                c.fetch_add(1, AtomicOrdering::Relaxed);
            }),
        );

        bus.emit_with(
            EventType::MemoryCreated,
            "test",
            serde_json::json!({}),
            0.5,
            true,
        );

        assert_eq!(counter.load(AtomicOrdering::Relaxed), 1);
    }

    #[test]
    fn remove_cascade_rule() {
        let mut bus = GanYingBus::default();
        assert!(bus.remove_cascade_rule(EventType::ToolDispatchError));
        assert!(!bus.remove_cascade_rule(EventType::ToolDispatchError));
    }

    #[test]
    fn stats_track_correctly() {
        let mut bus = GanYingBus::default();

        let _id = bus.subscribe(SubscriptionFilter::All, Box::new(|_| {}));

        bus.emit(EventType::MemoryCreated, "test", serde_json::json!({}));
        bus.emit(EventType::SystemStartup, "test", serde_json::json!({}));

        let stats = bus.stats();
        assert_eq!(stats.events_emitted, 2);
        assert_eq!(stats.active_subscriptions, 1);
        assert!(stats.subscriber_triggers >= 2);
    }

    #[test]
    fn recent_events_stored() {
        let mut bus = GanYingBus::new(10);

        bus.emit(
            EventType::MemoryCreated,
            "test",
            serde_json::json!({"n": 1}),
        );
        bus.emit(
            EventType::MemoryUpdated,
            "test",
            serde_json::json!({"n": 2}),
        );

        let recent = bus.recent_events(5);
        assert_eq!(recent.len(), 2);
        // Newest first
        assert_eq!(recent[0].event_type, EventType::MemoryUpdated);
        assert_eq!(recent[1].event_type, EventType::MemoryCreated);
    }

    #[test]
    fn recent_events_capped() {
        let mut bus = GanYingBus::new(3);

        for i in 0..5 {
            bus.emit(
                EventType::SystemHeartbeat,
                "test",
                serde_json::json!({"i": i}),
            );
        }

        let recent = bus.recent_events(10);
        assert_eq!(recent.len(), 3);
    }

    #[test]
    fn events_per_category_tracked() {
        let mut bus = GanYingBus::default();

        bus.emit(EventType::MemoryCreated, "test", serde_json::json!({}));
        bus.emit(EventType::MemoryDeleted, "test", serde_json::json!({}));
        bus.emit(EventType::SystemStartup, "test", serde_json::json!({}));

        let stats = bus.stats();
        assert_eq!(stats.events_per_category.get("memory"), Some(&2));
        assert_eq!(stats.events_per_category.get("system"), Some(&1));
    }

    #[test]
    fn resonance_event_to_json() {
        let event = ResonanceEvent::new(
            EventType::MemoryCreated,
            "test",
            serde_json::json!({"id": 42}),
        )
        .with_salience(0.8)
        .with_cascade();

        let json = event.to_json();
        assert_eq!(json["event_type"], "memory_created");
        assert_eq!(json["source"], "test");
        assert!((json["salience"].as_f64().unwrap() - 0.8).abs() < 0.001);
        assert_eq!(json["cascade"], true);
    }

    #[test]
    fn subscription_filter_matches() {
        assert!(
            SubscriptionFilter::EventType(EventType::MemoryCreated)
                .matches(EventType::MemoryCreated)
        );
        assert!(
            !SubscriptionFilter::EventType(EventType::MemoryCreated)
                .matches(EventType::MemoryDeleted)
        );
        assert!(
            SubscriptionFilter::Category(EventCategory::Memory).matches(EventType::MemoryCreated)
        );
        assert!(
            !SubscriptionFilter::Category(EventCategory::Memory).matches(EventType::SystemStartup)
        );
        assert!(SubscriptionFilter::All.matches(EventType::SystemStartup));
        assert!(
            SubscriptionFilter::EventTypes(vec![
                EventType::MemoryCreated,
                EventType::SystemStartup
            ])
            .matches(EventType::MemoryCreated)
        );
        assert!(
            !SubscriptionFilter::EventTypes(vec![EventType::MemoryCreated])
                .matches(EventType::SystemStartup)
        );
    }

    #[test]
    fn clear_resets_state() {
        let mut bus = GanYingBus::default();

        let _id = bus.subscribe(SubscriptionFilter::All, Box::new(|_| {}));
        bus.emit(EventType::MemoryCreated, "test", serde_json::json!({}));

        assert_eq!(bus.subscription_count(), 1);
        assert!(bus.events_emitted() > 0);

        bus.clear();
        assert_eq!(bus.subscription_count(), 0);
    }

    #[test]
    fn multiple_subscribers_same_event() {
        let mut bus = GanYingBus::default();
        let c1 = Arc::new(AtomicUsize::new(0));
        let c2 = Arc::new(AtomicUsize::new(0));

        let c1_clone = c1.clone();
        let c2_clone = c2.clone();

        let _id1 = bus.subscribe(
            SubscriptionFilter::EventType(EventType::MemoryCreated),
            Box::new(move |_| {
                c1_clone.fetch_add(1, AtomicOrdering::Relaxed);
            }),
        );
        let _id2 = bus.subscribe(
            SubscriptionFilter::EventType(EventType::MemoryCreated),
            Box::new(move |_| {
                c2_clone.fetch_add(1, AtomicOrdering::Relaxed);
            }),
        );

        bus.emit(EventType::MemoryCreated, "test", serde_json::json!({}));

        assert_eq!(c1.load(AtomicOrdering::Relaxed), 1);
        assert_eq!(c2.load(AtomicOrdering::Relaxed), 1);
    }

    fn temp_log_path(tag: &str) -> std::path::PathBuf {
        std::env::temp_dir().join(format!(
            "wm-resonance-test-{}-{}{tag}.jsonl",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.subsec_nanos())
                .unwrap_or(0),
        ))
    }

    #[test]
    fn persistence_writes_events_to_jsonl() {
        let path = temp_log_path("write");
        let mut bus = GanYingBus::default();
        bus.enable_persistence(&path);
        assert_eq!(bus.persist_path(), Some(path.as_path()));

        bus.emit(
            EventType::MemoryCreated,
            "test",
            serde_json::json!({"id": 1}),
        );
        bus.emit(EventType::SystemShutdown, "test", serde_json::json!({}));

        let contents = std::fs::read_to_string(&path).expect("log file exists");
        let lines: Vec<&str> = contents.lines().collect();
        assert_eq!(lines.len(), 2);
        let first: ResonanceEvent = serde_json::from_str(lines[0]).expect("valid JSON");
        assert_eq!(first.event_type, EventType::MemoryCreated);

        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn persistence_seeds_recent_events_on_reload() {
        let path = temp_log_path("reload");
        {
            let mut bus = GanYingBus::default();
            bus.enable_persistence(&path);
            bus.emit(
                EventType::MemoryCreated,
                "test",
                serde_json::json!({"id": 7}),
            );
            bus.emit(EventType::ToolDispatchStart, "test", serde_json::json!({}));
        }

        let mut bus2 = GanYingBus::default();
        bus2.enable_persistence(&path);
        let recent = bus2.recent_events(10);
        assert_eq!(recent.len(), 2);
        assert_eq!(recent[0].event_type, EventType::ToolDispatchStart);
        assert_eq!(recent[1].event_type, EventType::MemoryCreated);

        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn persistence_disabled_by_default() {
        let mut bus = GanYingBus::default();
        assert_eq!(bus.persist_path(), None);
        bus.emit(EventType::MemoryCreated, "test", serde_json::json!({}));
        assert_eq!(bus.events_emitted(), 1);
    }
}
