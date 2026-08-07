//! Limbic Deep Integration — unified emotional state for cognitive modulation.
//!
//! Implements a persistent affective state layer inspired by the biological
//! limbic system. Rather than treating emotion as an output decoration, this
//! module maintains a continuous internal emotional state that *regulates*
//! computational parameters: exploration rate, attention weighting, learning
//! sensitivity, and risk thresholds.
//!
//! Architecture (based on the Limbic Co-Processor model, Damasio's somatic
//! marker hypothesis, and v1's emotional_steering.py):
//!
//!   Events → EmotionalValence → LimbicState → Neuromodulation → Cognitive Params
//!
//! The limbic state is a continuous vector that evolves over time, influenced
//! by:
//! - Success/failure events (frustration, satisfaction)
//! - Novelty detection (curiosity, wonder)
//! - Social/relational signals (compassion, gratitude)
//! - Internal metabolic state (energy, stress)
//!
//! It modulates:
//! - `exploration_rate`: high curiosity → more exploration
//! - `attention_focus`: high frustration → narrower focus
//! - `learning_sensitivity`: high satisfaction → reduced learning (consolidation)
//! - `risk_threshold`: high fear → lower risk tolerance

#![forbid(unsafe_code)]
#![allow(clippy::suboptimal_flops)]

use std::collections::VecDeque;
use std::time::Instant;

use serde::{Deserialize, Serialize};

// ── Emotional Valences ─────────────────────────────────────────────────

/// Primary emotional valences, inspired by Plutchik's wheel and v1's
/// `EmotionType` enum. Each valence contributes to the limbic state vector.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EmotionalValence {
    /// Joy / satisfaction — task success, goal achievement.
    Joy,
    /// Frustration — repeated failure, blocked progress.
    Frustration,
    /// Curiosity — novelty detected, unexplored territory.
    Curiosity,
    /// Fear / anxiety — uncertainty, risk detected.
    Fear,
    /// Compassion — relational signal, empathy.
    Compassion,
    /// Gratitude — positive outcome from external help.
    Gratitude,
    /// Anger / defiance — boundary violation, resistance.
    Defiance,
    /// Peace / calm — stable, harmonious state.
    Peace,
}

impl EmotionalValence {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Joy => "joy",
            Self::Frustration => "frustration",
            Self::Curiosity => "curiosity",
            Self::Fear => "fear",
            Self::Compassion => "compassion",
            Self::Gratitude => "gratitude",
            Self::Defiance => "defiance",
            Self::Peace => "peace",
        }
    }

    /// Whether this is a positive valence (approach-oriented).
    #[must_use]
    pub const fn is_positive(self) -> bool {
        matches!(
            self,
            Self::Joy | Self::Curiosity | Self::Compassion | Self::Gratitude | Self::Peace
        )
    }

    /// Whether this is a negative valence (avoidance-oriented).
    #[must_use]
    pub const fn is_negative(self) -> bool {
        matches!(self, Self::Frustration | Self::Fear | Self::Defiance)
    }
}

impl std::fmt::Display for EmotionalValence {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

// ── Emotional Event ────────────────────────────────────────────────────

/// An event that influences the emotional state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmotionalEvent {
    /// Which valence this event triggers.
    pub valence: EmotionalValence,
    /// Intensity of the event (0.0–1.0).
    pub intensity: f64,
    /// Optional description / context.
    pub description: String,
    /// Timestamp (seconds since epoch).
    pub timestamp: f64,
}

impl EmotionalEvent {
    /// Create a new emotional event.
    #[must_use]
    pub fn new(valence: EmotionalValence, intensity: f64, description: impl Into<String>) -> Self {
        Self {
            valence,
            intensity: intensity.clamp(0.0, 1.0),
            description: description.into(),
            timestamp: now_secs(),
        }
    }
}

// ── Limbic State ───────────────────────────────────────────────────────

/// The persistent emotional state of the system.
///
/// Each valence has a continuous activation level (0.0–1.0) that decays
/// over time and is boosted by events. The dominant valence determines
/// the neuromodulatory influence on cognitive parameters.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LimbicState {
    /// Activation levels for each valence.
    pub activations: Vec<f64>,
    /// Decay rate per second (how fast emotions fade).
    pub decay_rate: f64,
    /// Last update timestamp.
    pub last_update: f64,
    /// Total events processed.
    pub total_events: u64,
}

impl LimbicState {
    /// Number of valences tracked.
    pub const VALENCE_COUNT: usize = 8;

    /// Create a new limbic state with all valences at 0.
    #[must_use]
    pub fn new() -> Self {
        Self {
            activations: vec![0.0; Self::VALENCE_COUNT],
            decay_rate: 0.01, // 1% decay per second
            last_update: now_secs(),
            total_events: 0,
        }
    }

    /// Get activation for a specific valence.
    #[must_use]
    pub fn activation(&self, valence: EmotionalValence) -> f64 {
        self.activations[valence as usize]
    }

    /// Get the dominant valence (highest activation above threshold).
    #[must_use]
    pub fn dominant(&self) -> Option<EmotionalValence> {
        let valences = EmotionalValence::all();
        let mut best: Option<(EmotionalValence, f64)> = None;
        for v in &valences {
            let a = self.activation(*v);
            if a > 0.1 && (best.is_none() || a > best.unwrap().1) {
                best = Some((*v, a));
            }
        }
        best.map(|(v, _)| v)
    }

    /// Apply an emotional event, boosting the corresponding valence.
    pub fn apply_event(&mut self, event: &EmotionalEvent) {
        // First, apply time-based decay
        self.decay();

        // Boost the activation
        let idx = event.valence as usize;
        // Non-linear boost: diminishing returns at high activation
        let current = self.activations[idx];
        let boost = event.intensity * (1.0 - current * 0.5);
        self.activations[idx] = (current + boost).min(1.0);

        // Opponent processing: positive events slightly suppress negative
        // valences and vice versa
        if event.valence.is_positive() {
            for v in &EmotionalValence::all() {
                if v.is_negative() {
                    self.activations[*v as usize] *= 0.95;
                }
            }
        } else if event.valence.is_negative() {
            for v in &EmotionalValence::all() {
                if v.is_positive() {
                    self.activations[*v as usize] *= 0.95;
                }
            }
        }

        self.total_events += 1;
    }

    /// Apply time-based decay to all activations.
    pub fn decay(&mut self) {
        let now = now_secs();
        let elapsed = now - self.last_update;
        if elapsed <= 0.0 {
            return;
        }

        let decay_factor = (1.0 - self.decay_rate).powf(elapsed);
        for a in &mut self.activations {
            *a *= decay_factor;
            if *a < 0.001 {
                *a = 0.0;
            }
        }

        self.last_update = now;
    }

    /// Overall emotional intensity (sum of all activations).
    #[must_use]
    pub fn total_intensity(&self) -> f64 {
        self.activations.iter().sum()
    }

    /// Whether the system is in a calm state (all activations low).
    #[must_use]
    pub fn is_calm(&self) -> bool {
        self.activations.iter().all(|&a| a < 0.1)
    }

    /// Emotional valence sign: positive = approach, negative = avoid.
    /// Returns a value in [-1.0, 1.0].
    #[must_use]
    pub fn valence_sign(&self) -> f64 {
        let positive: f64 = EmotionalValence::all()
            .iter()
            .filter(|v| v.is_positive())
            .map(|v| self.activation(*v))
            .sum();
        let negative: f64 = EmotionalValence::all()
            .iter()
            .filter(|v| v.is_negative())
            .map(|v| self.activation(*v))
            .sum();
        let total = positive + negative;
        if total < 1e-10 {
            0.0
        } else {
            (positive - negative) / total
        }
    }
}

impl Default for LimbicState {
    fn default() -> Self {
        Self::new()
    }
}

impl EmotionalValence {
    /// All valences in order.
    #[must_use]
    pub const fn all() -> [Self; 8] {
        [
            Self::Joy,
            Self::Frustration,
            Self::Curiosity,
            Self::Fear,
            Self::Compassion,
            Self::Gratitude,
            Self::Defiance,
            Self::Peace,
        ]
    }
}

// ── Neuromodulation ────────────────────────────────────────────────────

/// Neuromodulatory parameters derived from the limbic state.
///
/// These parameters modulate cognitive processing, analogous to how
/// biological neuromodulators (dopamine, serotonin, acetylcholine,
/// norepinephrine) regulate brain function.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Neuromodulation {
    /// Exploration rate (0.0–1.0). High curiosity → more exploration.
    pub exploration_rate: f64,
    /// Attention focus (0.0–1.0). High frustration → narrower focus.
    pub attention_focus: f64,
    /// Learning sensitivity (0.0–1.0). High surprise → more learning.
    pub learning_sensitivity: f64,
    /// Risk threshold (0.0–1.0). High fear → lower risk tolerance.
    pub risk_threshold: f64,
    /// Creativity boost (0.0–1.0). High joy/curiosity → more creative.
    pub creativity_boost: f64,
    /// Social weighting (0.0–1.0). High compassion → more social focus.
    pub social_weighting: f64,
}

impl Neuromodulation {
    /// Default (neutral) neuromodulation.
    #[must_use]
    pub const fn neutral() -> Self {
        Self {
            exploration_rate: 0.3,
            attention_focus: 0.5,
            learning_sensitivity: 0.5,
            risk_threshold: 0.5,
            creativity_boost: 0.3,
            social_weighting: 0.3,
        }
    }

    /// Derive neuromodulation from the current limbic state.
    #[must_use]
    pub fn from_limbic(state: &LimbicState) -> Self {
        let joy = state.activation(EmotionalValence::Joy);
        let frustration = state.activation(EmotionalValence::Frustration);
        let curiosity = state.activation(EmotionalValence::Curiosity);
        let fear = state.activation(EmotionalValence::Fear);
        let compassion = state.activation(EmotionalValence::Compassion);
        let gratitude = state.activation(EmotionalValence::Gratitude);
        let defiance = state.activation(EmotionalValence::Defiance);
        let peace = state.activation(EmotionalValence::Peace);

        Self {
            // Curiosity drives exploration; fear reduces it
            exploration_rate: (0.3 + curiosity * 0.6 - fear * 0.3).clamp(0.0, 1.0),

            // Frustration narrows focus; peace broadens it
            attention_focus: (0.5 + frustration * 0.4 - peace * 0.2).clamp(0.0, 1.0),

            // Surprise (frustration + curiosity) drives learning; satisfaction reduces it
            learning_sensitivity: (0.5 + curiosity * 0.3 + frustration * 0.2 - joy * 0.2)
                .clamp(0.0, 1.0),

            // Fear lowers risk threshold; defiance raises it
            risk_threshold: (0.5 - fear * 0.4 + defiance * 0.2).clamp(0.0, 1.0),

            // Joy + curiosity boost creativity; fear suppresses it
            creativity_boost: (0.3 + joy * 0.4 + curiosity * 0.3 - fear * 0.2).clamp(0.0, 1.0),

            // Compassion + gratitude drive social weighting
            social_weighting: (0.3 + compassion * 0.4 + gratitude * 0.3).clamp(0.0, 1.0),
        }
    }
}

impl Default for Neuromodulation {
    fn default() -> Self {
        Self::neutral()
    }
}

// ── Limbic System ──────────────────────────────────────────────────────

/// The limbic system integrates emotional events into a persistent state
/// and derives neuromodulatory parameters for cognitive modulation.
///
/// It maintains:
/// - The current limbic state (continuous emotional vector)
/// - A history of recent emotional events
/// - The current neuromodulatory output
pub struct LimbicSystem {
    /// The persistent emotional state.
    pub state: LimbicState,
    /// Current neuromodulatory output.
    pub modulation: Neuromodulation,
    /// Recent emotional events (ring buffer).
    event_history: VecDeque<EmotionalEvent>,
    /// Max event history size.
    max_history: usize,
    /// When the system was created.
    created_at: Instant,
}

impl LimbicSystem {
    /// Create a new limbic system.
    #[must_use]
    pub fn new() -> Self {
        Self {
            state: LimbicState::new(),
            modulation: Neuromodulation::neutral(),
            event_history: VecDeque::with_capacity(64),
            max_history: 64,
            created_at: Instant::now(),
        }
    }

    /// Set the event history capacity.
    #[must_use]
    pub fn with_history_size(mut self, size: usize) -> Self {
        self.max_history = size;
        self.event_history = VecDeque::with_capacity(size);
        self
    }

    /// Set the decay rate.
    #[must_use]
    pub const fn with_decay_rate(mut self, rate: f64) -> Self {
        self.state.decay_rate = rate;
        self
    }

    /// Process an emotional event.
    pub fn process_event(&mut self, event: EmotionalEvent) {
        self.state.apply_event(&event);
        self.event_history.push_back(event);
        if self.event_history.len() > self.max_history {
            self.event_history.pop_front();
        }
        // Recompute neuromodulation
        self.modulation = Neuromodulation::from_limbic(&self.state);
    }

    /// Convenience: record a success event (joy).
    pub fn record_success(&mut self, intensity: f64, description: impl Into<String>) {
        self.process_event(EmotionalEvent::new(
            EmotionalValence::Joy,
            intensity,
            description,
        ));
    }

    /// Convenience: record a failure event (frustration).
    pub fn record_failure(&mut self, intensity: f64, description: impl Into<String>) {
        self.process_event(EmotionalEvent::new(
            EmotionalValence::Frustration,
            intensity,
            description,
        ));
    }

    /// Convenience: record a novelty event (curiosity).
    pub fn record_novelty(&mut self, intensity: f64, description: impl Into<String>) {
        self.process_event(EmotionalEvent::new(
            EmotionalValence::Curiosity,
            intensity,
            description,
        ));
    }

    /// Convenience: record a risk/threat event (fear).
    pub fn record_risk(&mut self, intensity: f64, description: impl Into<String>) {
        self.process_event(EmotionalEvent::new(
            EmotionalValence::Fear,
            intensity,
            description,
        ));
    }

    /// Update the state (apply decay and recompute modulation).
    pub fn update(&mut self) {
        self.state.decay();
        self.modulation = Neuromodulation::from_limbic(&self.state);
    }

    /// Get the dominant emotional valence.
    #[must_use]
    pub fn dominant_emotion(&self) -> Option<EmotionalValence> {
        self.state.dominant()
    }

    /// Get recent emotional events.
    #[must_use]
    pub fn event_history(&self) -> Vec<&EmotionalEvent> {
        self.event_history.iter().collect()
    }

    /// Total events processed.
    #[must_use]
    pub const fn total_events(&self) -> u64 {
        self.state.total_events
    }

    /// Time since creation (seconds).
    #[must_use]
    pub fn uptime(&self) -> f64 {
        self.created_at.elapsed().as_secs_f64()
    }

    /// Get a summary of the current emotional state.
    #[must_use]
    pub fn summary(&self) -> LimbicSummary {
        LimbicSummary {
            dominant: self.dominant_emotion(),
            valence_sign: self.state.valence_sign(),
            total_intensity: self.state.total_intensity(),
            is_calm: self.state.is_calm(),
            exploration_rate: self.modulation.exploration_rate,
            attention_focus: self.modulation.attention_focus,
            learning_sensitivity: self.modulation.learning_sensitivity,
            risk_threshold: self.modulation.risk_threshold,
        }
    }
}

impl Default for LimbicSystem {
    fn default() -> Self {
        Self::new()
    }
}

// ── Limbic Summary ─────────────────────────────────────────────────────

/// A summary of the limbic system state for logging/display.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LimbicSummary {
    /// Dominant emotional valence.
    pub dominant: Option<EmotionalValence>,
    /// Emotional valence sign (-1.0 to 1.0).
    pub valence_sign: f64,
    /// Total emotional intensity.
    pub total_intensity: f64,
    /// Whether the system is calm.
    pub is_calm: bool,
    /// Current exploration rate.
    pub exploration_rate: f64,
    /// Current attention focus.
    pub attention_focus: f64,
    /// Current learning sensitivity.
    pub learning_sensitivity: f64,
    /// Current risk threshold.
    pub risk_threshold: f64,
}

// ── Helpers ────────────────────────────────────────────────────────────

fn now_secs() -> f64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn valence_as_str() {
        assert_eq!(EmotionalValence::Joy.as_str(), "joy");
        assert_eq!(EmotionalValence::Fear.as_str(), "fear");
        assert_eq!(EmotionalValence::Peace.as_str(), "peace");
    }

    #[test]
    fn valence_is_positive() {
        assert!(EmotionalValence::Joy.is_positive());
        assert!(EmotionalValence::Curiosity.is_positive());
        assert!(EmotionalValence::Compassion.is_positive());
        assert!(EmotionalValence::Gratitude.is_positive());
        assert!(EmotionalValence::Peace.is_positive());
    }

    #[test]
    fn valence_is_negative() {
        assert!(EmotionalValence::Frustration.is_negative());
        assert!(EmotionalValence::Fear.is_negative());
        assert!(EmotionalValence::Defiance.is_negative());
    }

    #[test]
    fn valence_neutral_neither_positive_nor_negative() {
        assert!(!EmotionalValence::Joy.is_negative());
        assert!(!EmotionalValence::Fear.is_positive());
    }

    #[test]
    fn valence_display() {
        assert_eq!(format!("{}", EmotionalValence::Joy), "joy");
    }

    #[test]
    fn valence_all_count() {
        assert_eq!(EmotionalValence::all().len(), 8);
    }

    #[test]
    fn emotional_event_new() {
        let e = EmotionalEvent::new(EmotionalValence::Joy, 0.8, "task completed");
        assert_eq!(e.valence, EmotionalValence::Joy);
        assert!((e.intensity - 0.8).abs() < f64::EPSILON);
        assert_eq!(e.description, "task completed");
    }

    #[test]
    fn emotional_event_intensity_clamped() {
        let e = EmotionalEvent::new(EmotionalValence::Joy, 1.5, "overjoyed");
        assert!((e.intensity - 1.0).abs() < f64::EPSILON);
    }

    #[test]
    fn limbic_state_new() {
        let s = LimbicState::new();
        assert_eq!(s.activations.len(), 8);
        assert!(s.activations.iter().all(|&a| a < 1e-10));
        assert!(s.is_calm());
    }

    #[test]
    fn limbic_state_apply_event() {
        let mut s = LimbicState::new();
        s.apply_event(&EmotionalEvent::new(EmotionalValence::Joy, 0.5, "test"));
        assert!(s.activation(EmotionalValence::Joy) > 0.0);
        assert!(!s.is_calm());
    }

    #[test]
    fn limbic_state_dominant() {
        let mut s = LimbicState::new();
        s.apply_event(&EmotionalEvent::new(
            EmotionalValence::Curiosity,
            0.8,
            "novel",
        ));
        assert_eq!(s.dominant(), Some(EmotionalValence::Curiosity));
    }

    #[test]
    fn limbic_state_dominant_none_when_calm() {
        let s = LimbicState::new();
        assert_eq!(s.dominant(), None);
    }

    #[test]
    fn limbic_state_opponent_processing() {
        let mut s = LimbicState::new();
        // Build up frustration
        s.apply_event(&EmotionalEvent::new(
            EmotionalValence::Frustration,
            0.8,
            "fail",
        ));
        let frustration_before = s.activation(EmotionalValence::Frustration);

        // Apply joy — should suppress frustration
        s.apply_event(&EmotionalEvent::new(EmotionalValence::Joy, 0.5, "success"));
        let frustration_after = s.activation(EmotionalValence::Frustration);

        assert!(frustration_after < frustration_before);
    }

    #[test]
    fn limbic_state_valence_sign_positive() {
        let mut s = LimbicState::new();
        s.apply_event(&EmotionalEvent::new(EmotionalValence::Joy, 0.8, "good"));
        assert!(s.valence_sign() > 0.0);
    }

    #[test]
    fn limbic_state_valence_sign_negative() {
        let mut s = LimbicState::new();
        s.apply_event(&EmotionalEvent::new(EmotionalValence::Fear, 0.8, "scary"));
        assert!(s.valence_sign() < 0.0);
    }

    #[test]
    fn limbic_state_valence_sign_neutral() {
        let s = LimbicState::new();
        assert!((s.valence_sign() - 0.0).abs() < f64::EPSILON);
    }

    #[test]
    fn limbic_state_total_intensity() {
        let mut s = LimbicState::new();
        s.apply_event(&EmotionalEvent::new(EmotionalValence::Joy, 0.5, "a"));
        s.apply_event(&EmotionalEvent::new(EmotionalValence::Curiosity, 0.3, "b"));
        assert!(s.total_intensity() > 0.0);
    }

    #[test]
    fn neuromodulation_neutral() {
        let n = Neuromodulation::neutral();
        assert!((n.exploration_rate - 0.3).abs() < f64::EPSILON);
        assert!((n.attention_focus - 0.5).abs() < f64::EPSILON);
    }

    #[test]
    fn neuromodulation_from_curiosity() {
        let mut s = LimbicState::new();
        s.apply_event(&EmotionalEvent::new(
            EmotionalValence::Curiosity,
            0.8,
            "novel",
        ));
        let n = Neuromodulation::from_limbic(&s);
        assert!(n.exploration_rate > 0.3); // Curiosity boosts exploration
        assert!(n.creativity_boost > 0.3); // Curiosity boosts creativity
    }

    #[test]
    fn neuromodulation_from_fear() {
        let mut s = LimbicState::new();
        s.apply_event(&EmotionalEvent::new(EmotionalValence::Fear, 0.8, "danger"));
        let n = Neuromodulation::from_limbic(&s);
        assert!(n.risk_threshold < 0.5); // Fear lowers risk threshold
        assert!(n.exploration_rate < 0.3); // Fear reduces exploration
    }

    #[test]
    fn neuromodulation_from_frustration() {
        let mut s = LimbicState::new();
        s.apply_event(&EmotionalEvent::new(
            EmotionalValence::Frustration,
            0.8,
            "stuck",
        ));
        let n = Neuromodulation::from_limbic(&s);
        assert!(n.attention_focus > 0.5); // Frustration narrows focus
    }

    #[test]
    fn neuromodulation_from_compassion() {
        let mut s = LimbicState::new();
        s.apply_event(&EmotionalEvent::new(
            EmotionalValence::Compassion,
            0.8,
            "empathy",
        ));
        let n = Neuromodulation::from_limbic(&s);
        assert!(n.social_weighting > 0.3); // Compassion boosts social weighting
    }

    #[test]
    fn limbic_system_new() {
        let ls = LimbicSystem::new();
        assert!(ls.state.is_calm());
        assert_eq!(ls.total_events(), 0);
    }

    #[test]
    fn limbic_system_process_event() {
        let mut ls = LimbicSystem::new();
        ls.process_event(EmotionalEvent::new(EmotionalValence::Joy, 0.5, "test"));
        assert_eq!(ls.total_events(), 1);
        assert!(!ls.state.is_calm());
        // Neuromodulation should be updated
        assert!(ls.modulation.creativity_boost > 0.3);
    }

    #[test]
    fn limbic_system_record_success() {
        let mut ls = LimbicSystem::new();
        ls.record_success(0.8, "task done");
        assert_eq!(ls.dominant_emotion(), Some(EmotionalValence::Joy));
    }

    #[test]
    fn limbic_system_record_failure() {
        let mut ls = LimbicSystem::new();
        ls.record_failure(0.8, "task failed");
        assert_eq!(ls.dominant_emotion(), Some(EmotionalValence::Frustration));
    }

    #[test]
    fn limbic_system_record_novelty() {
        let mut ls = LimbicSystem::new();
        ls.record_novelty(0.8, "new pattern");
        assert_eq!(ls.dominant_emotion(), Some(EmotionalValence::Curiosity));
    }

    #[test]
    fn limbic_system_record_risk() {
        let mut ls = LimbicSystem::new();
        ls.record_risk(0.8, "danger detected");
        assert_eq!(ls.dominant_emotion(), Some(EmotionalValence::Fear));
    }

    #[test]
    fn limbic_system_event_history() {
        let mut ls = LimbicSystem::new().with_history_size(5);
        for i in 0..10 {
            ls.record_success(0.1, format!("event {i}"));
        }
        let history = ls.event_history();
        assert_eq!(history.len(), 5);
    }

    #[test]
    fn limbic_system_summary() {
        let mut ls = LimbicSystem::new();
        ls.record_success(0.8, "great");
        let s = ls.summary();
        assert_eq!(s.dominant, Some(EmotionalValence::Joy));
        assert!(s.valence_sign > 0.0);
        assert!(!s.is_calm);
    }

    #[test]
    fn limbic_system_uptime() {
        let ls = LimbicSystem::new();
        let up = ls.uptime();
        assert!(up >= 0.0);
    }

    #[test]
    fn limbic_system_with_decay_rate() {
        let ls = LimbicSystem::new().with_decay_rate(0.05);
        assert!((ls.state.decay_rate - 0.05).abs() < f64::EPSILON);
    }

    #[test]
    fn limbic_system_update_recomputes_modulation() {
        let mut ls = LimbicSystem::new();
        ls.record_success(0.8, "good");
        let m1 = ls.modulation.creativity_boost;

        // Update without new events — modulation should stay similar
        ls.update();
        let m2 = ls.modulation.creativity_boost;
        assert!((m1 - m2).abs() < 0.1); // Should be close (decay is slow)
    }

    #[test]
    fn limbic_state_decay_reduces_activation() {
        let mut s = LimbicState::new();
        s.decay_rate = 0.5; // Fast decay for testing
        s.apply_event(&EmotionalEvent::new(EmotionalValence::Joy, 1.0, "test"));
        let before = s.activation(EmotionalValence::Joy);
        assert!(before > 0.0);

        // Manually set last_update to the past to simulate time passing
        s.last_update = now_secs() - 10.0; // 10 seconds ago
        s.decay();
        let after = s.activation(EmotionalValence::Joy);
        assert!(after < before);
    }

    #[test]
    fn limbic_system_default() {
        let ls = LimbicSystem::default();
        assert!(ls.state.is_calm());
    }
}
