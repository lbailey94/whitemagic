//! Cross-Pollination Matrix — Affective cascade between drives.
//!
//! When one drive spikes, it cascades into related drives. Curiosity
//! spike lowers Caution and boosts Social. Satisfaction spike boosts
//! Energy and Social. This is the nervous system connecting all drives.
//!
//! Ported from v2 `gardens/cross_pollination.py` (167 lines).
//! In v4, the matrix maps drive kinds to cascade effects on other drives,
//! producing `DriveEvent`s that can be processed by `DriveCore`.

use super::drive::DriveKind;
use super::event::{DriveEvent, DriveEventKind, DriveEventSource};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A cascade rule — when a source drive crosses a threshold, apply
/// effects to target drives.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CascadeRule {
    /// Source drive that triggers the cascade.
    pub source: DriveKind,
    /// Threshold above which the cascade fires (0.0–1.0).
    pub threshold: f32,
    /// Target drives to boost when the cascade fires.
    pub boost: Vec<DriveKind>,
    /// Target drives to suppress when the cascade fires.
    pub suppress: Vec<DriveKind>,
    /// Cascade strength (how much to boost/suppress, 0.0–1.0).
    pub strength: f32,
}

impl CascadeRule {
    /// Create a new cascade rule.
    #[must_use]
    pub const fn new(
        source: DriveKind,
        threshold: f32,
        boost: Vec<DriveKind>,
        suppress: Vec<DriveKind>,
        strength: f32,
    ) -> Self {
        Self {
            source,
            threshold,
            boost,
            suppress,
            strength,
        }
    }
}

/// A resonance event logged when a cascade fires.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResonanceEvent {
    /// Source drive that triggered the cascade.
    pub source: DriveKind,
    /// Drives that were boosted.
    pub boosted: Vec<DriveKind>,
    /// Drives that were suppressed.
    pub suppressed: Vec<DriveKind>,
    /// Cascade strength.
    pub strength: f32,
    /// Source drive value at time of cascade.
    pub source_value: f32,
}

/// Cross-Pollination Matrix — defines how drives cascade into each other.
///
/// When a drive crosses a threshold, the matrix generates `DriveEvent`s
/// for related drives. This creates affect cascades: high Curiosity
/// suppresses Caution and boosts Social, high Satisfaction boosts
/// Energy, etc.
///
/// The matrix is checked after each drive event is processed. If any
/// drive has crossed a cascade threshold, the corresponding cascade
/// events are generated and can be fed back into `DriveCore`.
pub struct CrossPollinationMatrix {
    /// Cascade rules indexed by source drive.
    rules: HashMap<DriveKind, CascadeRule>,
    /// Log of resonance events fired.
    resonance_log: Vec<ResonanceEvent>,
    /// Total cascades fired.
    cascade_count: u64,
}

impl CrossPollinationMatrix {
    /// Create a new matrix with default cascade rules.
    #[must_use]
    pub fn new() -> Self {
        let mut rules = HashMap::new();

        // Curiosity spike → suppress Caution, boost Social
        // (exploratory mode: less cautious, more social)
        rules.insert(
            DriveKind::Curiosity,
            CascadeRule::new(
                DriveKind::Curiosity,
                0.7,
                vec![DriveKind::Social],
                vec![DriveKind::Caution],
                0.05,
            ),
        );

        // Satisfaction spike → boost Energy, boost Social
        // (success energizes and socializes)
        rules.insert(
            DriveKind::Satisfaction,
            CascadeRule::new(
                DriveKind::Satisfaction,
                0.7,
                vec![DriveKind::Energy, DriveKind::Social],
                vec![],
                0.05,
            ),
        );

        // Caution spike → suppress Curiosity, boost Energy
        // (defensive mode: less exploration, more readiness)
        rules.insert(
            DriveKind::Caution,
            CascadeRule::new(
                DriveKind::Caution,
                0.7,
                vec![DriveKind::Energy],
                vec![DriveKind::Curiosity],
                0.05,
            ),
        );

        // Energy spike → boost Curiosity, boost Social
        // (high energy → explore and connect)
        rules.insert(
            DriveKind::Energy,
            CascadeRule::new(
                DriveKind::Energy,
                0.8,
                vec![DriveKind::Curiosity, DriveKind::Social],
                vec![],
                0.05,
            ),
        );

        // Social spike → boost Satisfaction, boost Curiosity
        // (social interaction → satisfaction and curiosity)
        rules.insert(
            DriveKind::Social,
            CascadeRule::new(
                DriveKind::Social,
                0.7,
                vec![DriveKind::Satisfaction, DriveKind::Curiosity],
                vec![],
                0.05,
            ),
        );

        Self {
            rules,
            resonance_log: Vec::new(),
            cascade_count: 0,
        }
    }

    /// Create an empty matrix with no rules (for custom configuration).
    #[must_use]
    pub fn empty() -> Self {
        Self {
            rules: HashMap::new(),
            resonance_log: Vec::new(),
            cascade_count: 0,
        }
    }

    /// Add or replace a cascade rule for a source drive.
    pub fn set_rule(&mut self, rule: CascadeRule) {
        self.rules.insert(rule.source, rule);
    }

    /// Check drive state for cascades and generate events.
    ///
    /// Returns a list of `DriveEvent`s to process (boost/suppress events
    /// for target drives) and logs resonance events.
    #[must_use]
    pub fn check_cascades(&mut self, state: &super::drive::DriveState) -> Vec<DriveEvent> {
        let mut events = Vec::new();

        for (source_kind, rule) in &self.rules {
            let source_value = state.get(*source_kind);

            if source_value >= rule.threshold {
                // Log resonance
                self.resonance_log.push(ResonanceEvent {
                    source: *source_kind,
                    boosted: rule.boost.clone(),
                    suppressed: rule.suppress.clone(),
                    strength: rule.strength,
                    source_value,
                });
                self.cascade_count += 1;

                // Generate boost events
                for target in &rule.boost {
                    events.push(self.make_boost_event(*target, rule.strength));
                }

                // Generate suppress events
                for target in &rule.suppress {
                    events.push(self.make_suppress_event(*target, rule.strength));
                }
            }
        }

        events
    }

    /// Create a boost event for a target drive.
    fn make_boost_event(&self, target: DriveKind, _strength: f32) -> DriveEvent {
        // Map target drive to appropriate event kind
        match target {
            DriveKind::Curiosity => {
                DriveEvent::new(DriveEventKind::NovelInput).with_source(DriveEventSource::Workspace)
            }
            DriveKind::Satisfaction => DriveEvent::new(DriveEventKind::ToolSuccess)
                .with_source(DriveEventSource::Workspace),
            DriveKind::Energy => DriveEvent::new(DriveEventKind::ResourceRelief)
                .with_source(DriveEventSource::Workspace),
            DriveKind::Social => DriveEvent::new(DriveEventKind::SocialInteraction)
                .with_source(DriveEventSource::Workspace),
            DriveKind::Caution => DriveEvent::new(DriveEventKind::LowConfidence)
                .with_source(DriveEventSource::Workspace),
        }
    }

    /// Create a suppress event for a target drive.
    fn make_suppress_event(&self, target: DriveKind, _strength: f32) -> DriveEvent {
        match target {
            DriveKind::Curiosity => {
                // Suppress curiosity by boosting caution (fear kills curiosity)
                DriveEvent::new(DriveEventKind::LowConfidence)
                    .with_source(DriveEventSource::Workspace)
            }
            DriveKind::Satisfaction => {
                // Suppress satisfaction via error signal
                DriveEvent::new(DriveEventKind::ToolError).with_source(DriveEventSource::Workspace)
            }
            DriveKind::Caution => {
                // Suppress caution via confidence signal
                DriveEvent::new(DriveEventKind::HighConfidence)
                    .with_source(DriveEventSource::Workspace)
            }
            DriveKind::Energy => {
                // Suppress energy via resource pressure
                DriveEvent::new(DriveEventKind::ResourcePressure)
                    .with_source(DriveEventSource::Workspace)
            }
            DriveKind::Social => {
                // No direct suppress event — social decays naturally
                DriveEvent::new(DriveEventKind::Decay).with_source(DriveEventSource::Workspace)
            }
        }
    }

    /// Get resonance statistics.
    #[must_use]
    pub fn resonance_stats(&self) -> HashMap<String, serde_json::Value> {
        let mut by_source: HashMap<DriveKind, usize> = HashMap::new();
        for event in &self.resonance_log {
            *by_source.entry(event.source).or_default() += 1;
        }

        let by_source_json: HashMap<String, usize> = by_source
            .iter()
            .map(|(k, v)| (format!("{k:?}").to_lowercase(), *v))
            .collect();

        let mut stats = HashMap::new();
        stats.insert(
            "total_cascades".to_string(),
            serde_json::Value::from(self.cascade_count),
        );
        stats.insert(
            "by_source".to_string(),
            serde_json::to_value(by_source_json).unwrap_or(serde_json::Value::Null),
        );
        stats
    }

    /// Total cascades fired.
    #[must_use]
    pub const fn cascade_count(&self) -> u64 {
        self.cascade_count
    }

    /// Get the resonance log.
    #[must_use]
    pub fn resonance_log(&self) -> &[ResonanceEvent] {
        &self.resonance_log
    }

    /// Clear the resonance log (does not reset cascade_count).
    pub fn clear_log(&mut self) {
        self.resonance_log.clear();
    }

    /// Number of rules configured.
    #[must_use]
    pub fn rule_count(&self) -> usize {
        self.rules.len()
    }
}

impl Default for CrossPollinationMatrix {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::super::drive::DriveState;
    use super::*;

    #[test]
    fn new_matrix_has_default_rules() {
        let matrix = CrossPollinationMatrix::new();
        assert_eq!(matrix.rule_count(), 5); // one per drive
    }

    #[test]
    fn empty_matrix_has_no_rules() {
        let matrix = CrossPollinationMatrix::empty();
        assert_eq!(matrix.rule_count(), 0);
    }

    #[test]
    fn set_rule_replaces_existing() {
        let mut matrix = CrossPollinationMatrix::new();
        let custom = CascadeRule::new(
            DriveKind::Curiosity,
            0.9,
            vec![DriveKind::Energy],
            vec![],
            0.1,
        );
        matrix.set_rule(custom);
        assert_eq!(matrix.rule_count(), 5); // replaced, not added
    }

    #[test]
    fn check_cascades_no_spike_returns_empty() {
        let mut matrix = CrossPollinationMatrix::new();
        // All drives below their cascade thresholds
        let state = DriveState {
            curiosity: 0.5,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.5,
            social: 0.4,
        };
        let events = matrix.check_cascades(&state);
        assert!(events.is_empty());
        assert_eq!(matrix.cascade_count(), 0);
    }

    #[test]
    fn curiosity_spike_triggers_cascade() {
        let mut matrix = CrossPollinationMatrix::new();
        // Curiosity at 0.8 > threshold 0.7
        let state = DriveState {
            curiosity: 0.8,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.8,
            social: 0.4,
        };
        let events = matrix.check_cascades(&state);
        assert!(!events.is_empty());
        assert!(matrix.cascade_count() > 0);
    }

    #[test]
    fn curiosity_spike_suppresses_caution() {
        let mut matrix = CrossPollinationMatrix::new();
        let state = DriveState {
            curiosity: 0.9,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.8,
            social: 0.4,
        };
        let events = matrix.check_cascades(&state);
        // Should include a suppress event for Caution (HighConfidence lowers caution)
        assert!(
            events
                .iter()
                .any(|e| e.kind == DriveEventKind::HighConfidence)
        );
    }

    #[test]
    fn curiosity_spike_boosts_social() {
        let mut matrix = CrossPollinationMatrix::new();
        let state = DriveState {
            curiosity: 0.9,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.8,
            social: 0.4,
        };
        let events = matrix.check_cascades(&state);
        // Should include a boost event for Social (SocialInteraction)
        assert!(
            events
                .iter()
                .any(|e| e.kind == DriveEventKind::SocialInteraction)
        );
    }

    #[test]
    fn satisfaction_spike_boosts_energy_and_social() {
        let mut matrix = CrossPollinationMatrix::new();
        let state = DriveState {
            curiosity: 0.5,
            satisfaction: 0.8,
            caution: 0.3,
            energy: 0.8,
            social: 0.4,
        };
        let events = matrix.check_cascades(&state);
        // Energy spike at 0.8 also triggers — so we get cascades from both
        assert!(!events.is_empty());
        // Satisfaction cascade boosts Energy (ResourceRelief) and Social (SocialInteraction)
        assert!(
            events
                .iter()
                .any(|e| e.kind == DriveEventKind::ResourceRelief)
        );
        assert!(
            events
                .iter()
                .any(|e| e.kind == DriveEventKind::SocialInteraction)
        );
    }

    #[test]
    fn caution_spike_suppresses_curiosity() {
        let mut matrix = CrossPollinationMatrix::new();
        let state = DriveState {
            curiosity: 0.5,
            satisfaction: 0.5,
            caution: 0.8,
            energy: 0.8,
            social: 0.4,
        };
        let events = matrix.check_cascades(&state);
        // Caution cascade suppresses Curiosity via LowConfidence
        assert!(
            events
                .iter()
                .any(|e| e.kind == DriveEventKind::LowConfidence)
        );
    }

    #[test]
    fn multiple_drives_spiking_produce_multiple_cascades() {
        let mut matrix = CrossPollinationMatrix::new();
        let state = DriveState {
            curiosity: 0.9,
            satisfaction: 0.9,
            caution: 0.3,
            energy: 0.8,
            social: 0.4,
        };
        let events = matrix.check_cascades(&state);
        // Curiosity (0.9 > 0.7), Satisfaction (0.9 > 0.7), Energy (0.8 >= 0.8)
        assert!(matrix.cascade_count() >= 3);
        assert!(!events.is_empty());
    }

    #[test]
    fn resonance_log_records_cascades() {
        let mut matrix = CrossPollinationMatrix::new();
        let state = DriveState {
            curiosity: 0.9,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.5,
            social: 0.4,
        };
        let _ = matrix.check_cascades(&state);
        let log = matrix.resonance_log();
        assert!(!log.is_empty());
        assert_eq!(log[0].source, DriveKind::Curiosity);
        assert!(log[0].boosted.contains(&DriveKind::Social));
        assert!(log[0].suppressed.contains(&DriveKind::Caution));
    }

    #[test]
    fn resonance_stats_returns_json() {
        let mut matrix = CrossPollinationMatrix::new();
        let state = DriveState {
            curiosity: 0.9,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.8,
            social: 0.4,
        };
        let _ = matrix.check_cascades(&state);
        let stats = matrix.resonance_stats();
        assert!(stats.contains_key("total_cascades"));
        assert!(stats.contains_key("by_source"));
    }

    #[test]
    fn clear_log_resets_log_only() {
        let mut matrix = CrossPollinationMatrix::new();
        let state = DriveState {
            curiosity: 0.9,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.5,
            social: 0.4,
        };
        let _ = matrix.check_cascades(&state);
        assert!(!matrix.resonance_log().is_empty());

        let count_before = matrix.cascade_count();
        matrix.clear_log();
        assert!(matrix.resonance_log().is_empty());
        assert_eq!(matrix.cascade_count(), count_before); // not reset
    }

    #[test]
    fn cascade_count_accumulates() {
        let mut matrix = CrossPollinationMatrix::new();
        let state = DriveState {
            curiosity: 0.9,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.5,
            social: 0.4,
        };
        let _ = matrix.check_cascades(&state);
        let first = matrix.cascade_count();

        let _ = matrix.check_cascades(&state);
        let second = matrix.cascade_count();

        assert!(second > first);
    }

    #[test]
    fn threshold_boundary_not_triggered() {
        let mut matrix = CrossPollinationMatrix::new();
        // Curiosity threshold is 0.7 — exactly at 0.7 should trigger (>=)
        let state = DriveState {
            curiosity: 0.7,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.5,
            social: 0.4,
        };
        let events = matrix.check_cascades(&state);
        assert!(!events.is_empty());
    }

    #[test]
    fn below_threshold_not_triggered() {
        let mut matrix = CrossPollinationMatrix::new();
        let state = DriveState {
            curiosity: 0.69,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.5,
            social: 0.4,
        };
        let events = matrix.check_cascades(&state);
        assert!(events.is_empty());
    }

    #[test]
    fn custom_rule_works() {
        let mut matrix = CrossPollinationMatrix::empty();
        matrix.set_rule(CascadeRule::new(
            DriveKind::Energy,
            0.5,
            vec![DriveKind::Curiosity],
            vec![],
            0.1,
        ));
        let state = DriveState {
            curiosity: 0.5,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.6,
            social: 0.4,
        };
        let events = matrix.check_cascades(&state);
        assert!(!events.is_empty());
        assert!(events.iter().any(|e| e.kind == DriveEventKind::NovelInput));
    }
}
