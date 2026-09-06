//! Workspace event types — published by cognitive cores.

use crate::salience::Salience;
use serde::{Deserialize, Serialize};
use std::time::Instant;

/// Identifier for a cognitive core (the source of an event).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CoreId {
    /// Citta consciousness cycle.
    Citta,
    /// Dream cycle.
    Dream,
    /// Brain-wave state manager.
    BrainWave,
    /// Autonomous cycle runner.
    Autonomous,
    /// Tool dispatch pipeline.
    Dispatch,
    /// Reflex tier.
    Reflex,
    /// Self-model / predictive introspection.
    SelfModel,
    /// Drive core (emotion/motivation).
    Drive,
    /// Homeostasis monitor.
    Homeostasis,
    /// External sensor / embodiment layer.
    Sensor,
    /// User-defined core (custom ID).
    Custom(u16),
}

impl CoreId {
    /// Human-readable name.
    #[must_use]
    pub const fn name(&self) -> &str {
        match self {
            Self::Citta => "citta",
            Self::Dream => "dream",
            Self::BrainWave => "brain_wave",
            Self::Autonomous => "autonomous",
            Self::Dispatch => "dispatch",
            Self::Reflex => "reflex",
            Self::SelfModel => "self_model",
            Self::Drive => "drive",
            Self::Homeostasis => "homeostasis",
            Self::Sensor => "sensor",
            Self::Custom(_) => "custom",
        }
    }
}

impl std::fmt::Display for CoreId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Custom(id) => write!(f, "custom_{id}"),
            _ => write!(f, "{}", self.name()),
        }
    }
}

/// Type of workspace event.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EventType {
    /// An error occurred in a core.
    Error,
    /// A reward signal was produced.
    Reward,
    /// A core is requesting attention (wants the spotlight).
    AttentionRequest,
    /// A novel detection was made (unexpected pattern, anomaly).
    NovelDetection,
    /// A metric crossed a threshold (from self-model or homeostasis).
    ThresholdCrossing,
    /// A drive state changed (curiosity, caution, etc.).
    DriveUpdate,
    /// A safety alert was triggered (from reflex tier or dharma).
    SafetyAlert,
}

impl EventType {
    /// Human-readable name.
    #[must_use]
    pub const fn name(&self) -> &'static str {
        match self {
            Self::Error => "error",
            Self::Reward => "reward",
            Self::AttentionRequest => "attention_request",
            Self::NovelDetection => "novel_detection",
            Self::ThresholdCrossing => "threshold_crossing",
            Self::DriveUpdate => "drive_update",
            Self::SafetyAlert => "safety_alert",
        }
    }
}

impl std::fmt::Display for EventType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.name())
    }
}

/// A workspace event published by a cognitive core.
///
/// Each event carries a salience score that determines its priority in
/// the spotlight arbitration. The payload is a JSON value containing
/// core-specific data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkspaceEvent {
    /// The core that produced this event.
    pub core: CoreId,
    /// The type of event.
    pub event_type: EventType,
    /// Salience score (urgency × novelty × confidence).
    pub salience: Salience,
    /// Core-specific payload data.
    pub payload: serde_json::Value,
    /// When the event was created.
    #[serde(skip, default = "Instant::now")]
    pub timestamp: Instant,
}

impl WorkspaceEvent {
    /// Create a new workspace event with the given salience.
    #[must_use]
    pub fn new(
        core: CoreId,
        event_type: EventType,
        salience: Salience,
        payload: serde_json::Value,
    ) -> Self {
        Self {
            core,
            event_type,
            salience,
            payload,
            timestamp: Instant::now(),
        }
    }

    /// Create a new event with default urgency based on event type.
    #[must_use]
    pub fn with_default_urgency(
        core: CoreId,
        event_type: EventType,
        novelty: f32,
        confidence: f32,
        payload: serde_json::Value,
    ) -> Self {
        let urgency = crate::salience::default_urgency(&event_type);
        Self::new(
            core,
            event_type,
            Salience::new(urgency, novelty, confidence),
            payload,
        )
    }

    /// Get the composite salience score.
    #[must_use]
    pub fn composite_salience(&self) -> f32 {
        self.salience.composite()
    }

    /// Check if this event should preempt the current spotlight.
    #[must_use]
    pub fn should_preempt(&self) -> bool {
        self.salience.is_high_salience()
    }

    /// Age of this event (time since creation).
    #[must_use]
    pub fn age(&self) -> std::time::Duration {
        self.timestamp.elapsed()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn core_id_names() {
        assert_eq!(CoreId::Citta.name(), "citta");
        assert_eq!(CoreId::Dream.name(), "dream");
        assert_eq!(CoreId::Reflex.name(), "reflex");
        assert_eq!(CoreId::Custom(42).name(), "custom");
    }

    #[test]
    fn core_id_display_custom() {
        assert_eq!(format!("{}", CoreId::Custom(7)), "custom_7");
        assert_eq!(format!("{}", CoreId::Citta), "citta");
    }

    #[test]
    fn event_type_names() {
        assert_eq!(EventType::Error.name(), "error");
        assert_eq!(EventType::SafetyAlert.name(), "safety_alert");
        assert_eq!(EventType::NovelDetection.name(), "novel_detection");
    }

    #[test]
    fn event_new() {
        let event = WorkspaceEvent::new(
            CoreId::Reflex,
            EventType::SafetyAlert,
            Salience::new(1.0, 0.8, 0.9),
            serde_json::json!({"sensor": "imu_1", "value": 42.0}),
        );
        assert_eq!(event.core, CoreId::Reflex);
        assert_eq!(event.event_type, EventType::SafetyAlert);
        assert!((event.composite_salience() - 0.72).abs() < 0.001);
    }

    #[test]
    fn event_with_default_urgency() {
        let event = WorkspaceEvent::with_default_urgency(
            CoreId::Homeostasis,
            EventType::ThresholdCrossing,
            0.5,
            0.9,
            serde_json::json!({"metric": "cpu", "value": 95.0}),
        );
        // ThresholdCrossing has default urgency 0.8
        assert!((event.salience.urgency - 0.8).abs() < 0.001);
        assert!((event.salience.novelty - 0.5).abs() < 0.001);
        assert!((event.salience.confidence - 0.9).abs() < 0.001);
    }

    #[test]
    fn event_should_preempt() {
        let high = WorkspaceEvent::new(
            CoreId::Reflex,
            EventType::SafetyAlert,
            Salience::new(0.95, 0.95, 0.95),
            serde_json::json!({}),
        );
        assert!(high.should_preempt());

        let low = WorkspaceEvent::new(
            CoreId::Drive,
            EventType::DriveUpdate,
            Salience::new(0.2, 0.3, 0.5),
            serde_json::json!({}),
        );
        assert!(!low.should_preempt());
    }

    #[test]
    fn event_age_grows() {
        let event = WorkspaceEvent::new(
            CoreId::Citta,
            EventType::AttentionRequest,
            Salience::new(0.5, 0.5, 0.5),
            serde_json::json!({}),
        );
        std::thread::sleep(std::time::Duration::from_millis(10));
        assert!(event.age().as_millis() >= 10);
    }
}
