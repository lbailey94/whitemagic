//! Synchronicity Detector — detects meaningful coincidences in the event stream.
//!
//! Inspired by Jung's concept of synchronicity ("meaningful coincidence"),
//! this module detects patterns where events from different subsystems
//! occur in close temporal proximity, suggesting underlying resonance
//! even when there's no direct causal link.
//!
//! The detector maintains a sliding window of recent events and checks
//! for co-occurrence patterns: when events from 2+ different subsystems
//! fire within a short time window, a [`Synchronicity`] is recorded.
//!
//! Ported from v2's `synchronicity_detector.py` (81 lines Python→Rust).

#![forbid(unsafe_code)]

use std::collections::VecDeque;

use serde::{Deserialize, Serialize};

use crate::bus::ResonanceEvent;
use crate::event_type::EventType;
use crate::nervous_system::NervousSubsystem;

// ── Synchronicity ─────────────────────────────────────────────────────

/// A detected synchronicity — meaningful co-occurrence of events from
/// different subsystems within a time window.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Synchronicity {
    /// The event types that co-occurred.
    pub event_types: Vec<EventType>,
    /// The subsystems involved.
    pub subsystems: Vec<NervousSubsystem>,
    /// Number of events in the synchronicity.
    pub event_count: usize,
    /// Number of distinct subsystems involved.
    pub subsystem_count: usize,
    /// Time span of the synchronicity (milliseconds).
    pub time_span_ms: i64,
    /// Mean salience of the events.
    pub mean_salience: f32,
    /// When the synchronicity was detected (Unix timestamp).
    pub detected_at: i64,
}

impl Synchronicity {
    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "event_types": self.event_types.iter().map(|e| e.as_str()).collect::<Vec<_>>(),
            "subsystems": self.subsystems.iter().map(|s| s.as_str()).collect::<Vec<_>>(),
            "event_count": self.event_count,
            "subsystem_count": self.subsystem_count,
            "time_span_ms": self.time_span_ms,
            "mean_salience": self.mean_salience,
            "detected_at": self.detected_at,
        })
    }

    /// Whether this is a "strong" synchronicity (3+ subsystems).
    #[must_use]
    pub const fn is_strong(&self) -> bool {
        self.subsystem_count >= 3
    }

    /// Strength score (0.0–1.0) based on subsystem count and salience.
    #[must_use]
    pub fn strength(&self) -> f32 {
        let subsystem_factor = (self.subsystem_count as f32 - 1.0) / 6.0; // 1 subsystem = 0, 7 = 1
        let salience_factor = self.mean_salience;
        (subsystem_factor * 0.6 + salience_factor * 0.4).clamp(0.0, 1.0)
    }
}

// ── Synchronicity Detector ────────────────────────────────────────────

/// Configuration for the [`SynchronicityDetector`].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SynchronicityConfig {
    /// Time window in milliseconds for co-occurrence detection.
    pub time_window_ms: i64,
    /// Minimum number of distinct subsystems for a synchronicity.
    pub min_subsystems: usize,
    /// Maximum events to retain in the sliding window.
    pub max_window_events: usize,
    /// Minimum mean salience for a synchronicity to be recorded.
    pub min_salience: f32,
}

impl Default for SynchronicityConfig {
    fn default() -> Self {
        Self {
            time_window_ms: 5000, // 5 seconds
            min_subsystems: 2,
            max_window_events: 100,
            min_salience: 0.3,
        }
    }
}

/// Synchronicity detector — finds meaningful co-occurrences in the event stream.
///
/// The detector maintains a sliding window of recent events. When events
/// from `min_subsystems` or more distinct subsystems occur within
/// `time_window_ms`, a [`Synchronicity`] is recorded.
///
/// # Example
/// ```no_run
/// use wm_resonance::{SynchronicityDetector, ResonanceEvent, EventType};
///
/// let mut detector = SynchronicityDetector::default();
///
/// // Feed events to detector
/// let event = ResonanceEvent::new(EventType::CittaAdvance, "test", serde_json::json!({}));
/// detector.observe(&event);
/// ```
pub struct SynchronicityDetector {
    window: VecDeque<ResonanceEvent>,
    config: SynchronicityConfig,
    /// Detected synchronicities.
    synchronicities: Vec<Synchronicity>,
    /// Total events observed.
    total_observed: u64,
}

impl Default for SynchronicityDetector {
    fn default() -> Self {
        Self::new(SynchronicityConfig::default())
    }
}

impl std::fmt::Debug for SynchronicityDetector {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SynchronicityDetector")
            .field("window_len", &self.window.len())
            .field("synchronicities", &self.synchronicities.len())
            .field("total_observed", &self.total_observed)
            .finish_non_exhaustive()
    }
}

impl SynchronicityDetector {
    /// Create a new detector with the given configuration.
    #[must_use]
    pub fn new(config: SynchronicityConfig) -> Self {
        Self {
            window: VecDeque::with_capacity(config.max_window_events),
            config,
            synchronicities: Vec::new(),
            total_observed: 0,
        }
    }

    /// Observe a new event and check for synchronicities.
    pub fn observe(&mut self, event: &ResonanceEvent) -> Option<Synchronicity> {
        self.total_observed += 1;

        // Add to window
        self.window.push_back(event.clone());
        if self.window.len() > self.config.max_window_events {
            self.window.pop_front();
        }

        // Check for synchronicity
        let sync = self.check_synchronicity();

        if let Some(ref sync) = sync {
            self.synchronicities.push(sync.clone());
        }

        sync
    }

    /// Check the current window for synchronicities.
    fn check_synchronicity(&self) -> Option<Synchronicity> {
        if self.window.len() < self.config.min_subsystems {
            return None;
        }

        let now_ts = chrono::Utc::now().timestamp_millis();
        let window_start = now_ts - self.config.time_window_ms;

        // Collect events within the time window
        let recent: Vec<&ResonanceEvent> = self
            .window
            .iter()
            .filter(|e| e.timestamp.timestamp_millis() >= window_start)
            .collect();

        if recent.len() < self.config.min_subsystems {
            return None;
        }

        // Collect distinct subsystems
        let mut subsystems: Vec<NervousSubsystem> = Vec::new();
        let mut event_types: Vec<EventType> = Vec::new();
        let mut salience_sum = 0.0f32;

        for event in &recent {
            let subsystem = NervousSubsystem::from_event_type(event.event_type);
            if !subsystems.contains(&subsystem) {
                subsystems.push(subsystem);
            }
            if !event_types.contains(&event.event_type) {
                event_types.push(event.event_type);
            }
            salience_sum += event.salience;
        }

        if subsystems.len() < self.config.min_subsystems {
            return None;
        }

        let mean_salience = salience_sum / recent.len() as f32;
        if mean_salience < self.config.min_salience {
            return None;
        }

        // Compute time span
        let timestamps: Vec<i64> = recent
            .iter()
            .map(|e| e.timestamp.timestamp_millis())
            .collect();
        let time_span_ms =
            timestamps.iter().max().unwrap_or(&0) - timestamps.iter().min().unwrap_or(&0);

        let subsystem_count = subsystems.len();
        let event_count = recent.len();

        Some(Synchronicity {
            event_types,
            subsystems,
            event_count,
            subsystem_count,
            time_span_ms,
            mean_salience,
            detected_at: now_ts,
        })
    }

    /// Get all detected synchronicities.
    #[must_use]
    pub fn synchronicities(&self) -> &[Synchronicity] {
        &self.synchronicities
    }

    /// Number of synchronicities detected.
    #[must_use]
    pub fn count(&self) -> usize {
        self.synchronicities.len()
    }

    /// Number of strong synchronicities (3+ subsystems).
    #[must_use]
    pub fn strong_count(&self) -> usize {
        self.synchronicities
            .iter()
            .filter(|s| s.is_strong())
            .count()
    }

    /// Total events observed.
    #[must_use]
    pub const fn total_observed(&self) -> u64 {
        self.total_observed
    }

    /// Get recent synchronicities (last N).
    #[must_use]
    pub fn recent(&self, n: usize) -> &[Synchronicity] {
        let start = self.synchronicities.len().saturating_sub(n);
        &self.synchronicities[start..]
    }

    /// Clear all detected synchronicities.
    pub fn clear(&mut self) {
        self.synchronicities.clear();
        self.window.clear();
    }

    /// Get a JSON summary.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "total_observed": self.total_observed,
            "synchronicities_detected": self.count(),
            "strong_synchronicities": self.strong_count(),
            "window_size": self.window.len(),
            "time_window_ms": self.config.time_window_ms,
            "min_subsystems": self.config.min_subsystems,
        })
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::bus::ResonanceEvent;

    fn make_event(event_type: EventType, salience: f32) -> ResonanceEvent {
        ResonanceEvent::new(event_type, "test", serde_json::json!({})).with_salience(salience)
    }

    #[test]
    fn no_synchronicity_with_single_subsystem() {
        let mut detector = SynchronicityDetector::default();

        // All events from the same subsystem (Memory = Enteric for consolidation, Motor for create)
        detector.observe(&make_event(EventType::MemoryCreated, 0.5));
        detector.observe(&make_event(EventType::MemoryUpdated, 0.5));
        detector.observe(&make_event(EventType::MemoryDeleted, 0.5));

        assert_eq!(detector.count(), 0);
    }

    #[test]
    fn detects_synchronicity_with_multiple_subsystems() {
        let mut detector = SynchronicityDetector::default();

        // Events from different subsystems
        detector.observe(&make_event(EventType::CittaAdvance, 0.7)); // Central
        let sync = detector.observe(&make_event(EventType::ToolDispatchStart, 0.8)); // Motor

        assert!(sync.is_some());
        let s = sync.unwrap();
        assert!(s.subsystem_count >= 2);
    }

    #[test]
    fn strong_synchronicity_has_3plus_subsystems() {
        let mut detector = SynchronicityDetector::default();

        detector.observe(&make_event(EventType::CittaAdvance, 0.8)); // Central
        detector.observe(&make_event(EventType::ToolDispatchStart, 0.8)); // Motor
        let sync = detector.observe(&make_event(EventType::DharmaWarn, 0.8)); // Immune

        assert!(sync.is_some());
        let s = sync.unwrap();
        assert!(s.is_strong());
        assert_eq!(s.subsystem_count, 3);
    }

    #[test]
    fn low_salience_filtered() {
        let mut detector = SynchronicityDetector::new(SynchronicityConfig {
            min_salience: 0.8,
            ..Default::default()
        });

        detector.observe(&make_event(EventType::CittaAdvance, 0.1)); // Central
        let sync = detector.observe(&make_event(EventType::ToolDispatchStart, 0.1)); // Motor

        assert!(sync.is_none());
    }

    #[test]
    fn synchronicity_strength() {
        let sync = Synchronicity {
            event_types: vec![
                EventType::CittaAdvance,
                EventType::ToolDispatchStart,
                EventType::DharmaWarn,
            ],
            subsystems: vec![
                NervousSubsystem::Central,
                NervousSubsystem::Motor,
                NervousSubsystem::Immune,
            ],
            event_count: 3,
            subsystem_count: 3,
            time_span_ms: 100,
            mean_salience: 0.8,
            detected_at: 0,
        };

        let strength = sync.strength();
        assert!(strength > 0.5);
        assert!(strength <= 1.0);
    }

    #[test]
    fn synchronicity_to_json() {
        let sync = Synchronicity {
            event_types: vec![EventType::CittaAdvance],
            subsystems: vec![NervousSubsystem::Central],
            event_count: 1,
            subsystem_count: 1,
            time_span_ms: 0,
            mean_salience: 0.5,
            detected_at: 12345,
        };

        let json = sync.to_json();
        assert_eq!(json["event_count"], 1);
        assert_eq!(json["detected_at"], 12345);
    }

    #[test]
    fn total_observed_tracked() {
        let mut detector = SynchronicityDetector::default();

        detector.observe(&make_event(EventType::SystemStartup, 0.5));
        detector.observe(&make_event(EventType::MemoryCreated, 0.5));
        detector.observe(&make_event(EventType::CittaAdvance, 0.5));

        assert_eq!(detector.total_observed(), 3);
    }

    #[test]
    fn clear_resets_state() {
        let mut detector = SynchronicityDetector::default();

        detector.observe(&make_event(EventType::CittaAdvance, 0.8));
        detector.observe(&make_event(EventType::ToolDispatchStart, 0.8));

        assert!(detector.count() > 0);

        detector.clear();
        assert_eq!(detector.count(), 0);
    }

    #[test]
    fn recent_synchronicities() {
        let mut detector = SynchronicityDetector::default();

        for _ in 0..5 {
            detector.observe(&make_event(EventType::CittaAdvance, 0.8));
            detector.observe(&make_event(EventType::ToolDispatchStart, 0.8));
        }

        let recent = detector.recent(3);
        assert!(recent.len() <= 3);
    }

    #[test]
    fn summary_json() {
        let mut detector = SynchronicityDetector::default();
        detector.observe(&make_event(EventType::CittaAdvance, 0.8));
        detector.observe(&make_event(EventType::ToolDispatchStart, 0.8));

        let summary = detector.summary();
        assert_eq!(summary["total_observed"], 2);
    }

    #[test]
    fn empty_detector() {
        let detector = SynchronicityDetector::default();
        assert_eq!(detector.count(), 0);
        assert_eq!(detector.total_observed(), 0);
        assert_eq!(detector.strong_count(), 0);
    }
}
