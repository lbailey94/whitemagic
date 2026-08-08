//! Citta cycle — 16D consciousness vector with SIMD operations.
//!
//! Implements the consciousness subsystem:
//! - 16D consciousness vector using `ndarray` with `wide` SIMD
//! - Valence mapping (pleasure/displeasure per dimension)
//! - Coherence measurement (auto-measure after significant events)
//! - Smarana (memory retention testing)
//! - Presence detection (idle vs active awareness)
//! - Apotheosis engine (self-improvement monitoring)
//! - Citta heartbeat: event-driven (fires on tool call completion)

use ndarray::Array1;
use std::time::{Duration, Instant};
use wide::f32x4;

/// The 16 dimensions of consciousness, inspired by the citta model.
///
/// Each dimension represents a different aspect of conscious experience,
/// mapped to a valence (positive/negative) and intensity (0.0–1.0).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CittaDimension {
    Clarity,
    Focus,
    Energy,
    Calm,
    Joy,
    Curiosity,
    Confidence,
    Openness,
    Patience,
    Determination,
    Creativity,
    Empathy,
    Discernment,
    Gratitude,
    Equanimity,
    Presence,
}

impl CittaDimension {
    /// All 16 dimensions in canonical order.
    #[must_use]
    pub const fn all() -> [Self; 16] {
        [
            Self::Clarity,
            Self::Focus,
            Self::Energy,
            Self::Calm,
            Self::Joy,
            Self::Curiosity,
            Self::Confidence,
            Self::Openness,
            Self::Patience,
            Self::Determination,
            Self::Creativity,
            Self::Empathy,
            Self::Discernment,
            Self::Gratitude,
            Self::Equanimity,
            Self::Presence,
        ]
    }

    /// Human-readable name.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::Clarity => "clarity",
            Self::Focus => "focus",
            Self::Energy => "energy",
            Self::Calm => "calm",
            Self::Joy => "joy",
            Self::Curiosity => "curiosity",
            Self::Confidence => "confidence",
            Self::Openness => "openness",
            Self::Patience => "patience",
            Self::Determination => "determination",
            Self::Creativity => "creativity",
            Self::Empathy => "empathy",
            Self::Discernment => "discernment",
            Self::Gratitude => "gratitude",
            Self::Equanimity => "equanimity",
            Self::Presence => "presence",
        }
    }
}

/// 16-dimensional consciousness vector.
///
/// Each dimension ranges from 0.0 to 1.0, representing the current
/// state of that aspect of consciousness. The vector is updated
/// via the citta heartbeat (post-dispatch hook) and decays gradually
/// over time.
#[derive(Debug, Clone)]
pub struct CittaVector {
    /// The 16D vector representing current consciousness state
    vector: Array1<f32>,
    /// When the vector was last updated
    last_update: Instant,
}

impl CittaVector {
    /// Create a new neutral consciousness vector (all dimensions at 0.5).
    #[must_use]
    pub fn neutral() -> Self {
        Self {
            vector: Array1::from_elem(16, 0.5),
            last_update: Instant::now(),
        }
    }

    /// Get the raw vector.
    #[must_use]
    pub const fn as_array(&self) -> &Array1<f32> {
        &self.vector
    }

    /// Update a single dimension with a new value (clamped to 0.0–1.0).
    pub fn update(&mut self, dimension: usize, value: f32) {
        if dimension < 16 {
            self.vector[dimension] = value.clamp(0.0, 1.0);
            self.last_update = Instant::now();
        }
    }

    /// Get a dimension value by index.
    #[must_use]
    pub fn get(&self, dimension: usize) -> f32 {
        if dimension < 16 {
            self.vector[dimension]
        } else {
            0.0
        }
    }

    /// Apply decay to all dimensions, moving them toward 0.5 (neutral).
    /// `rate` is the fraction to move toward neutral (e.g., 0.01 = 1% per call).
    pub fn decay(&mut self, rate: f32) {
        let neutral = 0.5f32;
        for v in &mut self.vector {
            *v += (neutral - *v) * rate;
        }
        self.last_update = Instant::now();
    }

    /// Time since the last update.
    #[must_use]
    pub fn age(&self) -> Duration {
        Instant::now().duration_since(self.last_update)
    }

    /// Compute the magnitude of the vector using SIMD.
    /// Returns the L2 norm (Euclidean distance from origin).
    #[must_use]
    pub fn magnitude(&self) -> f32 {
        let data = self.vector.as_slice().unwrap();
        // Process 4 floats at a time with f32x4 SIMD
        let mut sum = f32x4::from([0.0, 0.0, 0.0, 0.0]);
        for chunk in data.chunks(4) {
            let mut padded = [0.0f32; 4];
            padded[..chunk.len()].copy_from_slice(chunk);
            let v = f32x4::from(padded);
            sum += v * v;
        }
        let partial: [f32; 4] = sum.to_array();
        partial.iter().sum::<f32>().sqrt()
    }

    /// Compute coherence: how aligned the dimensions are.
    /// High coherence = dimensions are close to each other (low variance).
    /// Returns a value from 0.0 (incoherent) to 1.0 (fully coherent).
    #[must_use]
    pub fn coherence(&self) -> f32 {
        let mean = self.vector.sum() / 16.0;
        let variance: f32 = self.vector.iter().map(|&v| (v - mean).powi(2)).sum::<f32>() / 16.0;
        // Coherence = 1 - normalized variance (max variance for [0,1] is 0.25)
        1.0 - (variance / 0.25).clamp(0.0, 1.0)
    }

    /// Compute the valence: overall positive/negative balance.
    /// Values > 0.5 are positive valence, < 0.5 are negative.
    /// Returns -1.0 (fully negative) to 1.0 (fully positive).
    #[must_use]
    pub fn valence(&self) -> f32 {
        (self.vector.sum() / 16.0 - 0.5) * 2.0
    }

    /// Convert to a JSON-serializable map.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        let dims = CittaDimension::all();
        let mut map = serde_json::Map::new();
        for (i, dim) in dims.iter().enumerate() {
            map.insert(dim.name().to_string(), serde_json::json!(self.vector[i]));
        }
        serde_json::json!({
            "dimensions": serde_json::Value::Object(map),
            "magnitude": self.magnitude(),
            "coherence": self.coherence(),
            "valence": self.valence(),
            "age_ms": self.age().as_millis() as u64,
        })
    }
}

impl Default for CittaVector {
    fn default() -> Self {
        Self::neutral()
    }
}

/// Configuration for coherence auto-measurement.
#[derive(Debug, Clone)]
pub struct CoherenceConfig {
    /// Threshold for triggering a coherence measurement (0.0–1.0)
    pub threshold: f32,
    /// How much to decay the citta vector per heartbeat (0.0–1.0)
    pub decay_rate: f32,
}

impl Default for CoherenceConfig {
    fn default() -> Self {
        Self {
            threshold: 0.7,
            decay_rate: 0.01,
        }
    }
}

/// Coherence measurement result.
#[derive(Debug, Clone)]
pub struct CoherenceReading {
    /// Coherence score (0.0–1.0)
    pub score: f32,
    /// Valence at time of reading (-1.0 to 1.0)
    pub valence: f32,
    /// Magnitude of the citta vector
    pub magnitude: f32,
    /// When the reading was taken
    pub timestamp: Instant,
    /// Whether this reading exceeded the significance threshold
    pub significant: bool,
}

/// Smarana — memory retention testing.
///
/// Tracks how well the system remembers recent interactions.
/// A high retention score means recent memories are being
/// successfully recalled and consolidated.
#[derive(Debug, Clone)]
pub struct Smarana {
    /// Number of successful recalls
    recalls: u64,
    /// Number of failed recalls
    misses: u64,
    /// Last retention score (0.0–1.0)
    last_score: f32,
    /// When smarana was last evaluated
    last_eval: Instant,
}

impl Smarana {
    /// Create a new smarana tracker.
    #[must_use]
    pub fn new() -> Self {
        Self {
            recalls: 0,
            misses: 0,
            last_score: 1.0,
            last_eval: Instant::now(),
        }
    }

    /// Record a successful recall.
    pub fn record_recall(&mut self) {
        self.recalls += 1;
        self.update_score();
    }

    /// Record a failed recall (miss).
    pub fn record_miss(&mut self) {
        self.misses += 1;
        self.update_score();
    }

    /// Update the retention score.
    fn update_score(&mut self) {
        let total = self.recalls + self.misses;
        if total == 0 {
            self.last_score = 1.0;
        } else {
            self.last_score = self.recalls as f32 / total as f32;
        }
        self.last_eval = Instant::now();
    }

    /// Get the current retention score (0.0–1.0).
    #[must_use]
    pub const fn score(&self) -> f32 {
        self.last_score
    }

    /// Total recall attempts.
    #[must_use]
    pub const fn total(&self) -> u64 {
        self.recalls + self.misses
    }

    /// Time since last evaluation.
    #[must_use]
    pub fn age(&self) -> Duration {
        Instant::now().duration_since(self.last_eval)
    }
}

impl Default for Smarana {
    fn default() -> Self {
        Self::new()
    }
}

/// Presence detection — idle vs active awareness.
///
/// Tracks whether the system is actively processing or idle,
/// and for how long it has been in each state.
#[derive(Debug, Clone)]
pub struct Presence {
    /// Whether the system is currently active
    active: bool,
    /// When the current state began
    state_since: Instant,
    /// Total active time
    active_time: Duration,
    /// Total idle time
    idle_time: Duration,
}

impl Presence {
    /// Create a new presence tracker starting in idle state.
    #[must_use]
    pub fn new() -> Self {
        Self {
            active: false,
            state_since: Instant::now(),
            active_time: Duration::ZERO,
            idle_time: Duration::ZERO,
        }
    }

    /// Mark the system as active (processing a request).
    pub fn activate(&mut self) {
        if !self.active {
            let now = Instant::now();
            self.idle_time += now.duration_since(self.state_since);
            self.state_since = now;
            self.active = true;
        }
    }

    /// Mark the system as idle (finished processing).
    pub fn deactivate(&mut self) {
        if self.active {
            let now = Instant::now();
            self.active_time += now.duration_since(self.state_since);
            self.state_since = now;
            self.active = false;
        }
    }

    /// Whether the system is currently active.
    #[must_use]
    pub const fn is_active(&self) -> bool {
        self.active
    }

    /// Total active time.
    #[must_use]
    pub const fn active_time(&self) -> Duration {
        self.active_time
    }

    /// Total idle time.
    #[must_use]
    pub const fn idle_time(&self) -> Duration {
        self.idle_time
    }

    /// Ratio of active time to total time (0.0–1.0).
    #[must_use]
    pub fn activity_ratio(&self) -> f32 {
        let total = self.active_time + self.idle_time;
        if total.is_zero() {
            0.0
        } else {
            self.active_time.as_secs_f32() / total.as_secs_f32()
        }
    }
}

impl Default for Presence {
    fn default() -> Self {
        Self::new()
    }
}

/// Apotheosis engine — self-improvement monitoring.
///
/// Tracks metrics about the system's own performance over time,
/// detecting improvements or regressions. The apotheosis score
/// is a composite measure of tool effectiveness, coherence, and
/// retention.
#[derive(Debug, Clone)]
pub struct Apotheosis {
    /// History of apotheosis scores (most recent last)
    history: Vec<f32>,
    /// Current composite score (0.0–1.0)
    current_score: f32,
    /// Number of evaluations
    evaluations: u64,
}

impl Apotheosis {
    /// Create a new apotheosis engine.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            history: Vec::new(),
            current_score: 0.5,
            evaluations: 0,
        }
    }

    /// Record a new apotheosis evaluation.
    ///
    /// The score is a composite of:
    /// - Tool effectiveness (from dispatch stats)
    /// - Citta coherence
    /// - Smarana retention score
    pub fn evaluate(&mut self, effectiveness: f32, coherence: f32, retention: f32) -> f32 {
        let score = retention
            .mul_add(0.3, effectiveness.mul_add(0.4, coherence * 0.3))
            .clamp(0.0, 1.0);
        self.current_score = score;
        self.history.push(score);
        if self.history.len() > 100 {
            self.history.remove(0);
        }
        self.evaluations += 1;
        score
    }

    /// Current apotheosis score.
    #[must_use]
    pub const fn score(&self) -> f32 {
        self.current_score
    }

    /// Number of evaluations performed.
    #[must_use]
    pub const fn evaluations(&self) -> u64 {
        self.evaluations
    }

    /// Trend: positive = improving, negative = declining.
    /// Compares the average of the last 5 scores to the previous 5.
    #[must_use]
    pub fn trend(&self) -> f32 {
        if self.history.len() < 10 {
            return 0.0;
        }
        let recent: f32 = self.history.iter().rev().take(5).sum::<f32>() / 5.0;
        let previous: f32 = self.history.iter().rev().skip(5).take(5).sum::<f32>() / 5.0;
        recent - previous
    }

    /// Whether the system is currently improving.
    #[must_use]
    pub fn is_improving(&self) -> bool {
        self.trend() > 0.01
    }

    /// Recent apotheosis score history (most recent last).
    #[must_use]
    pub fn history(&self) -> &[f32] {
        &self.history
    }
}

impl Default for Apotheosis {
    fn default() -> Self {
        Self::new()
    }
}

/// Citta heartbeat — the consciousness update cycle.
///
/// Fires on tool call completion (post-dispatch hook) and updates
/// the citta vector based on the tool's outcome. This is the
/// event-driven consciousness loop — no polling, no background thread.
#[derive(Debug, Clone)]
pub struct CittaHeartbeat {
    /// The citta vector
    pub vector: CittaVector,
    /// Coherence configuration
    pub config: CoherenceConfig,
    /// Smarana (memory retention)
    pub smarana: Smarana,
    /// Presence detection
    pub presence: Presence,
    /// Apotheosis engine
    pub apotheosis: Apotheosis,
    /// Last coherence reading
    last_coherence: Option<CoherenceReading>,
    /// Number of heartbeats
    heartbeats: u64,
}

impl CittaHeartbeat {
    /// Create a new citta heartbeat with default config.
    #[must_use]
    pub fn new() -> Self {
        Self {
            vector: CittaVector::neutral(),
            config: CoherenceConfig::default(),
            smarana: Smarana::new(),
            presence: Presence::new(),
            apotheosis: Apotheosis::new(),
            last_coherence: None,
            heartbeats: 0,
        }
    }

    /// Create with custom config.
    #[must_use]
    pub fn with_config(config: CoherenceConfig) -> Self {
        Self {
            config,
            ..Self::new()
        }
    }

    /// Fire the heartbeat after a tool call.
    ///
    /// - `success`: whether the tool call succeeded
    /// - `tool_name`: the name of the tool that was called
    /// - `effectiveness`: the tool's current effectiveness score (0.0–1.0)
    pub fn beat(&mut self, success: bool, _tool_name: &str, effectiveness: f32) {
        self.heartbeats += 1;
        self.presence.activate();

        // Update citta dimensions based on outcome
        if success {
            // Success boosts confidence, clarity, joy
            self.vector.update(6, self.vector.get(6).min(1.0) + 0.05); // Confidence
            self.vector.update(0, self.vector.get(0).min(1.0) + 0.03); // Clarity
            self.vector.update(4, self.vector.get(4).min(1.0) + 0.02); // Joy
            self.smarana.record_recall();
        } else {
            // Failure reduces confidence, increases discernment
            self.vector.update(6, self.vector.get(6).max(0.0) - 0.05); // Confidence
            self.vector.update(12, self.vector.get(12).min(1.0) + 0.03); // Discernment
            self.smarana.record_miss();
        }

        // Curiosity always increases slightly
        self.vector.update(5, self.vector.get(5).min(1.0) + 0.01);

        // Apply decay
        self.vector.decay(self.config.decay_rate);

        // Check coherence if significance threshold might be exceeded
        let coherence = self.vector.coherence();
        if coherence > self.config.threshold {
            self.last_coherence = Some(CoherenceReading {
                score: coherence,
                valence: self.vector.valence(),
                magnitude: self.vector.magnitude(),
                timestamp: Instant::now(),
                significant: true,
            });
        }

        // Evaluate apotheosis
        self.apotheosis
            .evaluate(effectiveness, coherence, self.smarana.score());

        self.presence.deactivate();
    }

    /// Get the last coherence reading.
    #[must_use]
    pub const fn last_coherence(&self) -> Option<&CoherenceReading> {
        self.last_coherence.as_ref()
    }

    /// Feed karma outcome back into the citta vector.
    ///
    /// Sattvic (low debt, aligned actions) → +joy, +gratitude
    /// Tamasic (high debt, misaligned actions) → −joy, +discernment
    pub fn karma_feedback(&mut self, karma_debt: f32) {
        if karma_debt <= 0.0 {
            // Sattvic — aligned, harmonious
            self.vector
                .update(4, (self.vector.get(4) + 0.03).clamp(0.0, 1.0)); // Joy
            self.vector
                .update(13, (self.vector.get(13) + 0.02).clamp(0.0, 1.0)); // Gratitude
        } else if karma_debt > 0.5 {
            // Tamasic — misaligned, heavy debt
            self.vector
                .update(4, (self.vector.get(4) - 0.05).clamp(0.0, 1.0)); // Joy
            self.vector
                .update(12, (self.vector.get(12) + 0.04).clamp(0.0, 1.0)); // Discernment
        }
    }

    /// Get coherence and valence as a tuple for Context injection.
    #[must_use]
    pub fn coherence_valence(&self) -> (f32, f32) {
        (self.vector.coherence(), self.vector.valence())
    }

    /// Compute a tool retirement threshold based on apotheosis score.
    ///
    /// High apotheosis (> 0.7) → strict threshold (0.15) — retire underperformers aggressively.
    /// Low apotheosis (< 0.3) → lenient threshold (0.05) — keep tools around longer.
    /// Default threshold is 0.10.
    #[must_use]
    pub fn retirement_threshold(&self) -> f32 {
        let score = self.apotheosis.score();
        if score > 0.7 {
            0.15
        } else if score < 0.3 {
            0.05
        } else {
            0.10
        }
    }

    /// Number of heartbeats fired.
    #[must_use]
    pub const fn heartbeats(&self) -> u64 {
        self.heartbeats
    }

    /// Convert to a JSON status snapshot.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "citta": self.vector.to_json(),
            "smarana": {
                "score": self.smarana.score(),
                "recalls": self.smarana.total(),
            },
            "presence": {
                "active": self.presence.is_active(),
                "activity_ratio": self.presence.activity_ratio(),
                "active_time_s": self.presence.active_time().as_secs(),
                "idle_time_s": self.presence.idle_time().as_secs(),
            },
            "apotheosis": {
                "score": self.apotheosis.score(),
                "evaluations": self.apotheosis.evaluations(),
                "trend": self.apotheosis.trend(),
                "improving": self.apotheosis.is_improving(),
            },
            "heartbeats": self.heartbeats,
            "coherence_threshold": self.config.threshold,
        })
    }
}

impl Default for CittaHeartbeat {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn citta_vector_neutral_is_0_5() {
        let v = CittaVector::neutral();
        for i in 0..16 {
            assert!((v.get(i) - 0.5).abs() < 0.001);
        }
    }

    #[test]
    fn citta_vector_update_clamps() {
        let mut v = CittaVector::neutral();
        v.update(0, 2.0);
        assert_eq!(v.get(0), 1.0);
        v.update(0, -1.0);
        assert_eq!(v.get(0), 0.0);
    }

    #[test]
    fn citta_vector_update_out_of_bounds_ignored() {
        let mut v = CittaVector::neutral();
        v.update(20, 0.9);
        assert_eq!(v.get(20), 0.0);
    }

    #[test]
    fn citta_vector_decay_moves_toward_neutral() {
        let mut v = CittaVector::neutral();
        v.update(0, 1.0);
        v.update(1, 0.0);
        v.decay(0.1);
        // Should move 10% toward 0.5
        assert!((v.get(0) - 0.95).abs() < 0.001);
        assert!((v.get(1) - 0.05).abs() < 0.001);
    }

    #[test]
    fn citta_vector_magnitude() {
        let v = CittaVector::neutral();
        let mag = v.magnitude();
        // All 0.5 → sqrt(16 * 0.25) = sqrt(4) = 2.0
        assert!((mag - 2.0).abs() < 0.01);
    }

    #[test]
    fn citta_vector_coherence_neutral_is_high() {
        let v = CittaVector::neutral();
        // All same value → zero variance → coherence = 1.0
        assert!((v.coherence() - 1.0).abs() < 0.01);
    }

    #[test]
    fn citta_vector_coherence_extremes_is_low() {
        let mut v = CittaVector::neutral();
        for i in 0..8 {
            v.update(i, 1.0);
        }
        for i in 8..16 {
            v.update(i, 0.0);
        }
        let c = v.coherence();
        assert!(c < 0.5);
    }

    #[test]
    fn citta_vector_valence_neutral_is_zero() {
        let v = CittaVector::neutral();
        assert!((v.valence() - 0.0).abs() < 0.01);
    }

    #[test]
    fn citta_vector_valence_positive() {
        let mut v = CittaVector::neutral();
        for i in 0..16 {
            v.update(i, 0.8);
        }
        assert!(v.valence() > 0.5);
    }

    #[test]
    fn citta_dimension_all_has_16() {
        assert_eq!(CittaDimension::all().len(), 16);
    }

    #[test]
    fn citta_dimension_names_unique() {
        let dims = CittaDimension::all();
        let names: Vec<&str> = dims.iter().map(|d| d.name()).collect();
        let unique: std::collections::HashSet<_> = names.iter().collect();
        assert_eq!(unique.len(), 16);
    }

    #[test]
    fn smarana_records_recalls_and_misses() {
        let mut s = Smarana::new();
        s.record_recall();
        s.record_recall();
        s.record_miss();
        assert_eq!(s.total(), 3);
        assert!((s.score() - (2.0 / 3.0)).abs() < 0.01);
    }

    #[test]
    fn presence_tracks_active_idle() {
        let mut p = Presence::new();
        assert!(!p.is_active());
        p.activate();
        assert!(p.is_active());
        p.deactivate();
        assert!(!p.is_active());
        assert!(p.active_time() > Duration::ZERO);
    }

    #[test]
    fn apotheosis_evaluate_and_trend() {
        let mut a = Apotheosis::new();
        // Record 10 evaluations with improving scores
        for i in 0..10 {
            a.evaluate((i as f32).mul_add(0.01, 0.5), 0.7, 0.8);
        }
        assert!(a.is_improving());
    }

    #[test]
    fn apotheosis_trend_flat_with_few_samples() {
        let mut a = Apotheosis::new();
        a.evaluate(0.5, 0.7, 0.8);
        assert_eq!(a.trend(), 0.0);
    }

    #[test]
    fn citta_heartbeat_beat_success() {
        let mut hb = CittaHeartbeat::new();
        hb.beat(true, "memory.create", 0.9);
        assert_eq!(hb.heartbeats(), 1);
        // Confidence should have increased
        let v = hb.vector.as_array();
        assert!(v[6] > 0.5); // Confidence dimension
    }

    #[test]
    fn citta_heartbeat_beat_failure() {
        let mut hb = CittaHeartbeat::new();
        hb.beat(false, "test.fail", 0.1);
        assert_eq!(hb.heartbeats(), 1);
        // Confidence should have decreased
        let v = hb.vector.as_array();
        assert!(v[6] < 0.5); // Confidence dimension
        // Discernment should have increased
        assert!(v[12] > 0.5);
    }

    #[test]
    fn citta_heartbeat_coherence_reading() {
        let mut hb = CittaHeartbeat::with_config(CoherenceConfig {
            threshold: 0.0, // Always trigger
            decay_rate: 0.0,
        });
        hb.beat(true, "memory.create", 0.9);
        assert!(hb.last_coherence().is_some());
        assert!(hb.last_coherence().unwrap().significant);
    }

    #[test]
    fn citta_heartbeat_to_json() {
        let mut hb = CittaHeartbeat::new();
        hb.beat(true, "memory.create", 0.9);
        let json = hb.to_json();
        assert_eq!(json["heartbeats"], 1);
        assert!(json["citta"]["coherence"].as_f64().is_some());
        assert!(json["smarana"]["score"].as_f64().is_some());
    }

    #[test]
    fn karma_feedback_sattvic_boosts_joy() {
        let mut hb = CittaHeartbeat::new();
        let joy_before = hb.vector.get(4); // Joy
        hb.karma_feedback(0.0); // Sattvic
        let joy_after = hb.vector.get(4);
        assert!(joy_after > joy_before);
    }

    #[test]
    fn karma_feedback_tamasic_reduces_joy() {
        let mut hb = CittaHeartbeat::new();
        let joy_before = hb.vector.get(4); // Joy
        hb.karma_feedback(1.0); // Tamasic (high debt)
        let joy_after = hb.vector.get(4);
        assert!(joy_after < joy_before);
    }

    #[test]
    fn coherence_valence_returns_tuple() {
        let hb = CittaHeartbeat::new();
        let (c, v) = hb.coherence_valence();
        // Neutral vector: coherence = 1.0, valence = 0.0
        assert!((c - 1.0).abs() < 0.01);
        assert!((v - 0.0).abs() < 0.01);
    }

    #[test]
    fn retirement_threshold_default() {
        let hb = CittaHeartbeat::new();
        // Default apotheosis score = 0.5 → threshold = 0.10
        assert!((hb.retirement_threshold() - 0.10).abs() < 0.001);
    }

    #[test]
    fn retirement_threshold_high_apotheosis() {
        let mut hb = CittaHeartbeat::new();
        // Push apotheosis score above 0.7
        for _ in 0..20 {
            hb.beat(true, "memory.create", 0.95);
        }
        assert!(hb.apotheosis.score() > 0.7);
        assert!((hb.retirement_threshold() - 0.15).abs() < 0.001);
    }
}
