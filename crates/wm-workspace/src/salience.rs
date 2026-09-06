//! Salience scoring — the core arbitration signal.
//!
//! Ported from v2's `salience_arbiter.py`. The v2 formula was multiplicative:
//! `composite = urgency * novelty * confidence`. We keep this rather than the
//! additive formula proposed in the roadmap because multiplicative scoring
//! captures the intuition that an event with zero urgency OR zero novelty
//! OR zero confidence should not win the spotlight, regardless of how high
//! the other dimensions are.

use serde::{Deserialize, Serialize};

/// Salience score — the composite arbitration signal.
///
/// Each component ranges from 0.0 to 1.0:
/// - **Urgency**: How time-critical is this event? (1.0 = immediate action needed)
/// - **Novelty**: How unexpected is this event? (1.0 = completely novel)
/// - **Confidence**: How reliable is the signal? (1.0 = high confidence)
///
/// The composite score is multiplicative: `urgency * novelty * confidence`.
/// This means any zero component zeroes out the entire score, preventing
/// low-confidence or non-novel events from winning the spotlight even if
/// they're urgent.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct Salience {
    /// Time-criticality (0.0 = no rush, 1.0 = immediate action needed).
    pub urgency: f32,
    /// Unexpectedness (0.0 = expected, 1.0 = completely novel).
    pub novelty: f32,
    /// Signal reliability (0.0 = unreliable, 1.0 = high confidence).
    pub confidence: f32,
}

impl Default for Salience {
    fn default() -> Self {
        Self {
            urgency: 0.0,
            novelty: 0.0,
            confidence: 1.0,
        }
    }
}

impl Salience {
    /// Create a new salience score with the given components.
    #[must_use]
    pub const fn new(urgency: f32, novelty: f32, confidence: f32) -> Self {
        Self {
            urgency,
            novelty,
            confidence,
        }
    }

    /// Compute the composite salience score (multiplicative).
    ///
    /// `composite = urgency * novelty * confidence`
    ///
    /// Range: 0.0 to 1.0. Any zero component zeroes the entire score.
    #[must_use]
    pub fn composite(&self) -> f32 {
        self.urgency * self.novelty * self.confidence
    }

    /// Check if this salience score is high enough to preempt the spotlight.
    ///
    /// Events with composite > 0.8 can immediately preempt the current
    /// spotlight holder.
    #[must_use]
    pub fn is_high_salience(&self) -> bool {
        self.composite() > 0.8
    }

    /// Check if this salience score is negligible (composite < 0.01).
    #[must_use]
    pub fn is_negligible(&self) -> bool {
        self.composite() < 0.01
    }

    /// Clamp all components to [0.0, 1.0].
    #[must_use]
    pub const fn clamped(&self) -> Self {
        Self {
            urgency: self.urgency.clamp(0.0, 1.0),
            novelty: self.novelty.clamp(0.0, 1.0),
            confidence: self.confidence.clamp(0.0, 1.0),
        }
    }

    /// Sanitize all components: replace NaN/Infinity with 0.0, then clamp to [0.0, 1.0].
    ///
    /// This prevents salience poisoning where impossible values could
    /// artificially inflate or deflate the composite score.
    #[must_use]
    pub const fn sanitized(&self) -> Self {
        const fn clean(v: f32) -> f32 {
            if v.is_nan() || v.is_infinite() {
                0.0
            } else {
                v.clamp(0.0, 1.0)
            }
        }
        Self {
            urgency: clean(self.urgency),
            novelty: clean(self.novelty),
            confidence: clean(self.confidence),
        }
    }
}

impl std::fmt::Display for Salience {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "Salience({:.2}×{:.2}×{:.2}={:.4})",
            self.urgency,
            self.novelty,
            self.confidence,
            self.composite()
        )
    }
}

/// Default urgency mapping for event types.
///
/// Ported from v2's event-type → urgency mapping. Safety alerts and errors
/// have the highest urgency; novel detections and drive updates are moderate.
#[must_use]
pub const fn default_urgency(event_type: &crate::event::EventType) -> f32 {
    use crate::event::EventType;
    match event_type {
        EventType::SafetyAlert => 1.0,
        EventType::Error => 0.9,
        EventType::ThresholdCrossing => 0.8,
        EventType::AttentionRequest => 0.6,
        EventType::NovelDetection => 0.4,
        EventType::Reward => 0.3,
        EventType::DriveUpdate => 0.2,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn composite_multiplicative() {
        let s = Salience::new(0.8, 0.5, 1.0);
        assert_eq!(s.composite(), 0.4);
    }

    #[test]
    fn composite_zero_urgency() {
        let s = Salience::new(0.0, 1.0, 1.0);
        assert_eq!(s.composite(), 0.0);
    }

    #[test]
    fn composite_zero_novelty() {
        let s = Salience::new(1.0, 0.0, 1.0);
        assert_eq!(s.composite(), 0.0);
    }

    #[test]
    fn composite_zero_confidence() {
        let s = Salience::new(1.0, 1.0, 0.0);
        assert_eq!(s.composite(), 0.0);
    }

    #[test]
    fn composite_all_max() {
        let s = Salience::new(1.0, 1.0, 1.0);
        assert_eq!(s.composite(), 1.0);
    }

    #[test]
    fn is_high_salience() {
        assert!(Salience::new(0.95, 0.95, 0.95).is_high_salience());
        assert!(!Salience::new(0.5, 0.5, 0.5).is_high_salience());
    }

    #[test]
    fn is_negligible() {
        assert!(Salience::new(0.01, 0.01, 0.01).is_negligible());
        assert!(!Salience::new(0.5, 0.5, 0.5).is_negligible());
    }

    #[test]
    fn clamped() {
        let s = Salience::new(1.5, -0.5, 2.0);
        let c = s.clamped();
        assert_eq!(c.urgency, 1.0);
        assert_eq!(c.novelty, 0.0);
        assert_eq!(c.confidence, 1.0);
    }

    #[test]
    fn default_salience_has_confidence_1() {
        let s = Salience::default();
        assert_eq!(s.confidence, 1.0);
        assert_eq!(s.urgency, 0.0);
        assert_eq!(s.novelty, 0.0);
    }

    #[test]
    fn display_format() {
        let s = Salience::new(0.5, 0.4, 0.8);
        let display = format!("{s}");
        assert!(display.contains("0.50"));
        assert!(display.contains("0.16"));
    }

    #[test]
    fn default_urgency_safety_alert() {
        use crate::event::EventType;
        assert_eq!(default_urgency(&EventType::SafetyAlert), 1.0);
    }

    #[test]
    fn default_urgency_error() {
        use crate::event::EventType;
        assert_eq!(default_urgency(&EventType::Error), 0.9);
    }

    #[test]
    fn default_urgency_drive_update() {
        use crate::event::EventType;
        assert_eq!(default_urgency(&EventType::DriveUpdate), 0.2);
    }

    #[test]
    fn sanitized_replaces_nan_and_infinity() {
        let s = Salience::new(f32::NAN, f32::INFINITY, -0.5);
        let clean = s.sanitized();
        assert_eq!(clean.urgency, 0.0, "NaN should become 0.0");
        assert_eq!(clean.novelty, 0.0, "Infinity should become 0.0");
        assert_eq!(clean.confidence, 0.0, "Negative should become 0.0");
    }

    #[test]
    fn sanitized_clamps_oversized() {
        let s = Salience::new(2.0, 1.5, 0.8);
        let clean = s.sanitized();
        assert_eq!(clean.urgency, 1.0);
        assert_eq!(clean.novelty, 1.0);
        assert_eq!(clean.confidence, 0.8);
    }

    #[test]
    fn sanitized_preserves_valid() {
        let s = Salience::new(0.5, 0.3, 0.9);
        let clean = s.sanitized();
        assert_eq!(clean, s);
    }
}
