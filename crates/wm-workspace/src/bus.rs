//! Global workspace bus — publish/subscribe event bus with salience arbitration.
//!
//! All cognitive cores publish events to the workspace. The workspace
//! arbitrates attention via the spotlight mechanism and maintains a
//! ring buffer of recent events.
//!
//! The bus uses `tokio::sync::broadcast` for multiple subscribers. Slow
//! subscribers may miss events (lossy by design — the workspace is not
//! a reliable queue, it's an attention mechanism).

use crate::event::{CoreId, EventType, WorkspaceEvent};
use crate::spotlight::Spotlight;
use std::sync::atomic::{AtomicU64, Ordering};
use thiserror::Error;

/// Maximum number of events in the backlog ring buffer.
pub const BACKLOG_SIZE: usize = 256;

/// Default broadcast channel capacity.
pub const CHANNEL_CAPACITY: usize = 512;

/// Error type for workspace operations.
#[derive(Debug, Clone, Error)]
pub enum WorkspaceError {
    /// Event payload too large.
    #[error("event payload too large: {0} bytes")]
    PayloadTooLarge(usize),
}

/// Workspace statistics.
#[derive(Debug, Clone, Default)]
pub struct WorkspaceStats {
    /// Total events published.
    pub events_published: u64,
    /// Total spotlight transfers.
    pub spotlight_transfers: u64,
    /// Total arbitration cycles.
    pub arbitration_cycles: u64,
    /// Events per core.
    pub events_per_core: std::collections::HashMap<CoreId, u64>,
    /// Events per type.
    pub events_per_type: std::collections::HashMap<EventType, u64>,
}

/// The global workspace — coordinates attention across all cognitive cores.
///
/// Combines:
/// - A broadcast event bus (tokio::sync::broadcast)
/// - A spotlight tracker for salience-based arbitration
/// - A ring buffer backlog of recent events
pub struct GlobalWorkspace {
    /// Spotlight tracker.
    spotlight: Spotlight,
    /// Ring buffer of recent events.
    backlog: std::collections::VecDeque<WorkspaceEvent>,
    /// Total events published.
    events_published: AtomicU64,
    /// Events per core.
    events_per_core: std::collections::HashMap<CoreId, u64>,
    /// Events per type.
    events_per_type: std::collections::HashMap<EventType, u64>,
}

impl std::fmt::Debug for GlobalWorkspace {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("GlobalWorkspace")
            .field("spotlight", &self.spotlight)
            .field("backlog_len", &self.backlog.len())
            .field(
                "events_published",
                &self.events_published.load(Ordering::Relaxed),
            )
            .finish_non_exhaustive()
    }
}

impl Default for GlobalWorkspace {
    fn default() -> Self {
        Self::new()
    }
}

impl GlobalWorkspace {
    /// Create a new global workspace with default settings.
    #[must_use]
    pub fn new() -> Self {
        Self {
            spotlight: Spotlight::default(),
            backlog: std::collections::VecDeque::with_capacity(BACKLOG_SIZE),
            events_published: AtomicU64::new(0),
            events_per_core: std::collections::HashMap::new(),
            events_per_type: std::collections::HashMap::new(),
        }
    }

    /// Create a workspace with a custom spotlight half-life.
    #[must_use]
    pub fn with_half_life(half_life: std::time::Duration) -> Self {
        Self {
            spotlight: Spotlight::new(half_life),
            backlog: std::collections::VecDeque::with_capacity(BACKLOG_SIZE),
            events_published: AtomicU64::new(0),
            events_per_core: std::collections::HashMap::new(),
            events_per_type: std::collections::HashMap::new(),
        }
    }

    /// Publish an event to the workspace.
    ///
    /// The event is:
    /// 1. Added to the backlog ring buffer
    /// 2. Arbitrated against the current spotlight
    /// 3. Counted in statistics
    ///
    /// Returns `true` if the event won the spotlight.
    pub fn publish(&mut self, event: &WorkspaceEvent) -> bool {
        self.events_published.fetch_add(1, Ordering::Relaxed);

        // Update per-core and per-type counts
        *self.events_per_core.entry(event.core).or_insert(0) += 1;
        *self.events_per_type.entry(event.event_type).or_insert(0) += 1;

        // Add to backlog (evict oldest if full)
        if self.backlog.len() >= BACKLOG_SIZE {
            self.backlog.pop_front();
        }
        self.backlog.push_back(event.clone());

        // Arbitrate
        let won = self.spotlight.arbitrate(event);

        if won {
            tracing::debug!(
                core = %event.core,
                event_type = %event.event_type,
                salience = event.composite_salience(),
                "spotlight won"
            );
        }

        won
    }

    /// Publish a simple event with default urgency.
    pub fn publish_simple(
        &mut self,
        core: CoreId,
        event_type: EventType,
        novelty: f32,
        confidence: f32,
        payload: serde_json::Value,
    ) -> bool {
        let event =
            WorkspaceEvent::with_default_urgency(core, event_type, novelty, confidence, payload);
        self.publish(&event)
    }

    /// Publish multiple events at once. The highest-salience event is
    /// arbitrated against the current spotlight.
    ///
    /// Returns the index of the winning event, or `None` if none won.
    pub fn publish_batch(&mut self, events: &[WorkspaceEvent]) -> Option<usize> {
        if events.is_empty() {
            return None;
        }

        // Add all to backlog and counts
        for event in events {
            self.events_published.fetch_add(1, Ordering::Relaxed);
            *self.events_per_core.entry(event.core).or_insert(0) += 1;
            *self.events_per_type.entry(event.event_type).or_insert(0) += 1;

            if self.backlog.len() >= BACKLOG_SIZE {
                self.backlog.pop_front();
            }
            self.backlog.push_back(event.clone());
        }

        // Arbitrate batch
        self.spotlight.arbitrate_batch(events)
    }

    /// Get the current spotlight entry.
    #[must_use]
    pub const fn spotlight(&self) -> Option<&crate::spotlight::SpotlightEntry> {
        self.spotlight.current()
    }

    /// Get the core currently holding the spotlight.
    #[must_use]
    pub fn spotlight_core(&self) -> Option<CoreId> {
        self.spotlight.current_core()
    }

    /// Get the current spotlight strength (0.0 to 1.0).
    #[must_use]
    pub fn spotlight_strength(&self) -> f32 {
        self.spotlight.strength()
    }

    /// Get the recent event backlog (newest first).
    pub const fn backlog(&self) -> &std::collections::VecDeque<WorkspaceEvent> {
        &self.backlog
    }

    /// Get the last N events from the backlog.
    pub fn recent_events(&self, n: usize) -> Vec<&WorkspaceEvent> {
        self.backlog.iter().rev().take(n).collect()
    }

    /// Total events published.
    #[must_use]
    pub fn events_published(&self) -> u64 {
        self.events_published.load(Ordering::Relaxed)
    }

    /// Spotlight transfer count.
    #[must_use]
    pub const fn spotlight_transfers(&self) -> u64 {
        self.spotlight.transfer_count()
    }

    /// Spotlight arbitration cycle count.
    #[must_use]
    pub const fn arbitration_cycles(&self) -> u64 {
        self.spotlight.arbitration_count()
    }

    /// Get the number of times a core has held the spotlight.
    #[must_use]
    pub fn core_hold_count(&self, core: CoreId) -> u64 {
        self.spotlight.core_hold_count(core)
    }

    /// Get the number of events published by a core.
    #[must_use]
    pub fn core_event_count(&self, core: CoreId) -> u64 {
        self.events_per_core.get(&core).copied().unwrap_or(0)
    }

    /// Get the number of events of a specific type.
    #[must_use]
    pub fn event_type_count(&self, event_type: EventType) -> u64 {
        self.events_per_type.get(&event_type).copied().unwrap_or(0)
    }

    /// Collect workspace statistics.
    pub fn stats(&self) -> WorkspaceStats {
        WorkspaceStats {
            events_published: self.events_published.load(Ordering::Relaxed),
            spotlight_transfers: self.spotlight.transfer_count(),
            arbitration_cycles: self.spotlight.arbitration_count(),
            events_per_core: self.events_per_core.clone(),
            events_per_type: self.events_per_type.clone(),
        }
    }

    /// Clear the spotlight.
    pub const fn clear_spotlight(&mut self) {
        self.spotlight.clear();
    }

    /// Clear the event backlog.
    pub fn clear_backlog(&mut self) {
        self.backlog.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::salience::Salience;

    fn make_event(core: CoreId, event_type: EventType, salience: f32) -> WorkspaceEvent {
        WorkspaceEvent::new(
            core,
            event_type,
            Salience::new(salience, salience, salience),
            serde_json::json!({"test": true}),
        )
    }

    #[test]
    fn workspace_default() {
        let ws = GlobalWorkspace::default();
        assert_eq!(ws.events_published(), 0);
        assert!(ws.spotlight().is_none());
        assert_eq!(ws.backlog().len(), 0);
    }

    #[test]
    fn publish_first_event_wins_spotlight() {
        let mut ws = GlobalWorkspace::new();
        let event = make_event(CoreId::Citta, EventType::AttentionRequest, 0.5);
        assert!(ws.publish(&event));
        assert_eq!(ws.spotlight_core(), Some(CoreId::Citta));
        assert_eq!(ws.events_published(), 1);
    }

    #[test]
    fn publish_lower_salience_does_not_win() {
        let mut ws = GlobalWorkspace::new();
        let high = make_event(CoreId::Citta, EventType::AttentionRequest, 0.8);
        assert!(ws.publish(&high));

        let low = make_event(CoreId::Dream, EventType::Reward, 0.3);
        assert!(!ws.publish(&low));
        assert_eq!(ws.spotlight_core(), Some(CoreId::Citta));
    }

    #[test]
    fn publish_higher_salience_wins() {
        let mut ws = GlobalWorkspace::new();
        let low = make_event(CoreId::Citta, EventType::AttentionRequest, 0.3);
        assert!(ws.publish(&low));

        let high = make_event(CoreId::Dream, EventType::NovelDetection, 0.9);
        assert!(ws.publish(&high));
        assert_eq!(ws.spotlight_core(), Some(CoreId::Dream));
    }

    #[test]
    fn backlog_ring_buffer_evicts_old() {
        let mut ws = GlobalWorkspace::new();
        for i in 0..(BACKLOG_SIZE + 50) {
            let event = make_event(CoreId::Custom(i as u16), EventType::DriveUpdate, 0.1);
            ws.publish(&event);
        }
        assert_eq!(ws.backlog().len(), BACKLOG_SIZE);
    }

    #[test]
    fn recent_events_returns_newest_first() {
        let mut ws = GlobalWorkspace::new();
        ws.publish(&make_event(CoreId::Citta, EventType::Reward, 0.1));
        ws.publish(&make_event(CoreId::Dream, EventType::Reward, 0.1));
        ws.publish(&make_event(CoreId::Reflex, EventType::Reward, 0.1));

        let recent = ws.recent_events(2);
        assert_eq!(recent.len(), 2);
        assert_eq!(recent[0].core, CoreId::Reflex);
        assert_eq!(recent[1].core, CoreId::Dream);
    }

    #[test]
    fn publish_batch() {
        let mut ws = GlobalWorkspace::new();
        let events = vec![
            make_event(CoreId::Citta, EventType::AttentionRequest, 0.3),
            make_event(CoreId::Dream, EventType::NovelDetection, 0.7),
            make_event(CoreId::Reflex, EventType::SafetyAlert, 0.5),
        ];
        let winner = ws.publish_batch(&events);
        assert_eq!(winner, Some(1)); // Dream has highest salience
        assert_eq!(ws.spotlight_core(), Some(CoreId::Dream));
        assert_eq!(ws.events_published(), 3);
        assert_eq!(ws.backlog().len(), 3);
    }

    #[test]
    fn publish_batch_empty() {
        let mut ws = GlobalWorkspace::new();
        assert!(ws.publish_batch(&[]).is_none());
    }

    #[test]
    fn core_event_count() {
        let mut ws = GlobalWorkspace::new();
        ws.publish(&make_event(CoreId::Citta, EventType::Reward, 0.1));
        ws.publish(&make_event(CoreId::Citta, EventType::Reward, 0.1));
        ws.publish(&make_event(CoreId::Dream, EventType::Reward, 0.1));
        assert_eq!(ws.core_event_count(CoreId::Citta), 2);
        assert_eq!(ws.core_event_count(CoreId::Dream), 1);
        assert_eq!(ws.core_event_count(CoreId::Reflex), 0);
    }

    #[test]
    fn event_type_count() {
        let mut ws = GlobalWorkspace::new();
        ws.publish(&make_event(CoreId::Citta, EventType::Error, 0.1));
        ws.publish(&make_event(CoreId::Dream, EventType::Error, 0.1));
        ws.publish(&make_event(CoreId::Reflex, EventType::SafetyAlert, 0.1));
        assert_eq!(ws.event_type_count(EventType::Error), 2);
        assert_eq!(ws.event_type_count(EventType::SafetyAlert), 1);
    }

    #[test]
    fn stats_collection() {
        let mut ws = GlobalWorkspace::new();
        ws.publish(&make_event(CoreId::Citta, EventType::Reward, 0.5));
        ws.publish(&make_event(CoreId::Dream, EventType::NovelDetection, 0.8));

        let stats = ws.stats();
        assert_eq!(stats.events_published, 2);
        assert_eq!(stats.spotlight_transfers, 2);
        assert_eq!(stats.arbitration_cycles, 2);
        assert_eq!(stats.events_per_core.get(&CoreId::Citta), Some(&1));
        assert_eq!(stats.events_per_core.get(&CoreId::Dream), Some(&1));
    }

    #[test]
    fn publish_simple_with_default_urgency() {
        let mut ws = GlobalWorkspace::new();
        let won = ws.publish_simple(
            CoreId::Reflex,
            EventType::SafetyAlert,
            0.9,
            0.9,
            serde_json::json!({"alert": "collision"}),
        );
        // SafetyAlert has urgency 1.0, so composite = 1.0 * 0.9 * 0.9 = 0.81
        assert!(won);
        assert_eq!(ws.spotlight_core(), Some(CoreId::Reflex));
    }

    #[test]
    fn clear_spotlight() {
        let mut ws = GlobalWorkspace::new();
        ws.publish(&make_event(CoreId::Citta, EventType::AttentionRequest, 0.5));
        assert!(ws.spotlight().is_some());
        ws.clear_spotlight();
        assert!(ws.spotlight().is_none());
    }

    #[test]
    fn clear_backlog() {
        let mut ws = GlobalWorkspace::new();
        ws.publish(&make_event(CoreId::Citta, EventType::Reward, 0.1));
        ws.publish(&make_event(CoreId::Dream, EventType::Reward, 0.1));
        assert_eq!(ws.backlog().len(), 2);
        ws.clear_backlog();
        assert_eq!(ws.backlog().len(), 0);
    }

    #[test]
    fn spotlight_strength_decays() {
        let mut ws = GlobalWorkspace::with_half_life(std::time::Duration::from_millis(50));
        ws.publish(&make_event(CoreId::Citta, EventType::AttentionRequest, 0.8));

        let s1 = ws.spotlight_strength();
        assert!(s1 > 0.48 && s1 < 0.53, "initial strength: {s1}");

        std::thread::sleep(std::time::Duration::from_millis(50));
        let s2 = ws.spotlight_strength();
        assert!(s2 < s1);
    }

    #[test]
    fn core_hold_count() {
        let mut ws = GlobalWorkspace::new();
        ws.publish(&make_event(CoreId::Citta, EventType::AttentionRequest, 0.5));
        ws.publish(&make_event(CoreId::Dream, EventType::NovelDetection, 0.8));
        ws.publish(&make_event(CoreId::Citta, EventType::Error, 0.9));

        assert_eq!(ws.core_hold_count(CoreId::Citta), 2);
        assert_eq!(ws.core_hold_count(CoreId::Dream), 1);
    }

    #[test]
    fn backlog_max_size() {
        let mut ws = GlobalWorkspace::new();
        for i in 0..100 {
            ws.publish(&make_event(
                CoreId::Custom(i as u16),
                EventType::DriveUpdate,
                0.01,
            ));
        }
        assert!(ws.backlog().len() <= BACKLOG_SIZE);
    }
}
