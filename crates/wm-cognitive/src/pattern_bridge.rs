//! Pattern matching bridge — connects pattern-matching systems to the
//! imagination engine for scenario evaluation.
//!
//! Phase VI of the Imagination Engine:
//! - **Constellation novelty**: Assess whether a scenario is in familiar territory
//! - **Strategy-informed evaluation**: Use synthesized patterns as priors
//! - **Spreading activation**: Retrieve relevant memories for scenario context
//! - **Surprise gate**: Flag unexpected predicted outcomes for deeper analysis

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};

use wm_bicameral::scenario::Scenario;

use crate::constellation::ConstellationReport;
use crate::neural::{GateDecision, SpreadingActivation, SurpriseGate};
use crate::strategy::SynthesisReport;

// ── Pattern Assessment Results ────────────────────────────────────────

/// Result of constellation-based novelty assessment for a scenario.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConstellationNovelty {
    /// Whether the scenario's action is in familiar territory (true = familiar).
    pub is_familiar: bool,
    /// Number of constellations detected in the memory space.
    pub constellation_count: usize,
    /// Novelty score (0.0 = completely familiar, 1.0 = completely novel).
    pub novelty_score: f32,
    /// Name of the closest constellation (if any).
    pub closest_constellation: Option<String>,
}

/// Result of strategy-informed evaluation priors.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StrategyPrior {
    /// Number of strategy patterns available.
    pub pattern_count: usize,
    /// Themes discovered in the strategy synthesis.
    pub themes: Vec<String>,
    /// Prior score adjustment (applied to scenario score).
    pub score_adjustment: f32,
}

/// Result of surprise gate evaluation on a scenario's predicted outcomes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurpriseAssessment {
    /// Gate decision for the scenario's predicted outcome.
    pub decision: GateDecisionKind,
    /// Novelty score of the predicted outcome.
    pub novelty_score: f32,
    /// Whether the scenario should be flagged for deeper analysis.
    pub needs_deep_analysis: bool,
}

/// Serializable version of GateDecision.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GateDecisionKind {
    /// Encode with boosted importance (high novelty).
    Encode,
    /// Encode normally (moderate novelty).
    EncodeNormal,
    /// Skip encoding (low novelty).
    Skip,
}

impl From<GateDecision> for GateDecisionKind {
    fn from(d: GateDecision) -> Self {
        match d {
            GateDecision::Encode => Self::Encode,
            GateDecision::EncodeNormal => Self::EncodeNormal,
            GateDecision::Skip => Self::Skip,
        }
    }
}

/// Enriched scenario with pattern-matching data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatternEnrichedScenario {
    /// The original scenario.
    pub scenario: Scenario,
    /// Constellation novelty assessment.
    pub novelty: ConstellationNovelty,
    /// Strategy-informed prior.
    pub strategy_prior: StrategyPrior,
    /// Surprise gate assessment.
    pub surprise: SurpriseAssessment,
    /// Adjusted score incorporating pattern data.
    pub adjusted_score: f32,
}

impl PatternEnrichedScenario {
    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "action": self.scenario.action,
            "score": self.scenario.score,
            "adjusted_score": self.adjusted_score,
            "novelty": {
                "is_familiar": self.novelty.is_familiar,
                "constellation_count": self.novelty.constellation_count,
                "novelty_score": self.novelty.novelty_score,
                "closest_constellation": self.novelty.closest_constellation,
            },
            "strategy_prior": {
                "pattern_count": self.strategy_prior.pattern_count,
                "themes": self.strategy_prior.themes,
                "score_adjustment": self.strategy_prior.score_adjustment,
            },
            "surprise": {
                "decision": match self.surprise.decision {
                    GateDecisionKind::Encode => "encode",
                    GateDecisionKind::EncodeNormal => "encode_normal",
                    GateDecisionKind::Skip => "skip",
                },
                "novelty_score": self.surprise.novelty_score,
                "needs_deep_analysis": self.surprise.needs_deep_analysis,
            },
        })
    }
}

// ── Pattern Bridge ────────────────────────────────────────────────────

/// Configuration for the pattern bridge.
#[derive(Debug, Clone)]
pub struct PatternBridgeConfig {
    /// Whether constellation novelty assessment is enabled.
    pub enable_constellation: bool,
    /// Whether strategy-informed priors are enabled.
    pub enable_strategy: bool,
    /// Whether surprise gate is enabled.
    pub enable_surprise: bool,
    /// Bonus for familiar scenarios (added to score).
    pub familiarity_bonus: f32,
    /// Penalty for novel scenarios (subtracted from score).
    pub novelty_penalty: f32,
}

impl Default for PatternBridgeConfig {
    fn default() -> Self {
        Self {
            enable_constellation: true,
            enable_strategy: true,
            enable_surprise: true,
            familiarity_bonus: 0.05,
            novelty_penalty: 0.02,
        }
    }
}

/// Pattern bridge — connects pattern-matching systems to scenario evaluation.
///
/// Uses constellation detection, strategy synthesis, and surprise gating
/// to enrich scenarios with pattern-awareness.
pub struct PatternBridge {
    config: PatternBridgeConfig,
    surprise_gate: SurpriseGate,
    /// Cached constellation report (refreshed periodically).
    cached_constellation: Option<ConstellationReport>,
    /// Cached synthesis report.
    cached_synthesis: Option<SynthesisReport>,
}

impl Default for PatternBridge {
    fn default() -> Self {
        Self::new(PatternBridgeConfig::default())
    }
}

impl PatternBridge {
    /// Create a new pattern bridge with the given config.
    #[must_use]
    pub fn new(config: PatternBridgeConfig) -> Self {
        Self {
            config,
            surprise_gate: SurpriseGate::default(),
            cached_constellation: None,
            cached_synthesis: None,
        }
    }

    /// Update the cached constellation report.
    pub fn update_constellations(&mut self, report: ConstellationReport) {
        self.cached_constellation = Some(report);
    }

    /// Update the cached synthesis report.
    pub fn update_strategies(&mut self, report: SynthesisReport) {
        self.cached_synthesis = Some(report);
    }

    /// Assess constellation novelty for a scenario.
    #[must_use]
    pub fn assess_novelty(&self, scenario: &Scenario) -> ConstellationNovelty {
        let report = self.cached_constellation.as_ref();
        let constellation_count = report.map_or(0, |r| r.constellations.len());

        // Check if the scenario's action matches any constellation's dominant tags
        let action_lower = scenario.action.to_lowercase();
        let closest = report.and_then(|r| {
            r.constellations.iter().find_map(|c| {
                let matches = c
                    .dominant_tags
                    .iter()
                    .any(|tag| action_lower.contains(&tag.to_lowercase()));
                if matches { Some(c.name.clone()) } else { None }
            })
        });

        let is_familiar = closest.is_some();
        let novelty_score = if is_familiar {
            0.2
        } else if constellation_count > 0 {
            // Some constellations exist but none match — moderately novel
            0.6
        } else {
            // No constellations at all — completely novel
            1.0
        };

        ConstellationNovelty {
            is_familiar,
            constellation_count,
            novelty_score,
            closest_constellation: closest,
        }
    }

    /// Compute strategy-informed prior for a scenario.
    #[must_use]
    pub fn strategy_prior(&self, scenario: &Scenario) -> StrategyPrior {
        let report = self.cached_synthesis.as_ref();
        let pattern_count = report.map_or(0, |r| r.strategies_synthesized);
        let themes = report.map_or(Vec::new(), |r| r.themes.clone());

        // Score adjustment: if scenario action matches a theme, give a bonus
        let action_lower = scenario.action.to_lowercase();
        let matches_theme = themes
            .iter()
            .any(|t| action_lower.contains(&t.to_lowercase()));

        let score_adjustment = if matches_theme { 0.1 } else { 0.0 };

        StrategyPrior {
            pattern_count,
            themes,
            score_adjustment,
        }
    }

    /// Evaluate surprise for a scenario's predicted outcome.
    #[must_use]
    pub fn evaluate_surprise(&self, scenario: &Scenario) -> SurpriseAssessment {
        // Use the scenario's novelty score as input to the surprise gate
        let novelty = scenario.novelty;
        let decision = self.surprise_gate.evaluate(novelty);

        let needs_deep_analysis = matches!(decision, GateDecision::Encode);

        SurpriseAssessment {
            decision: decision.into(),
            novelty_score: novelty,
            needs_deep_analysis,
        }
    }

    /// Enrich a scenario with pattern-matching data.
    #[must_use]
    pub fn enrich_scenario(&self, scenario: &Scenario) -> PatternEnrichedScenario {
        let novelty = if self.config.enable_constellation {
            self.assess_novelty(scenario)
        } else {
            ConstellationNovelty {
                is_familiar: false,
                constellation_count: 0,
                novelty_score: scenario.novelty,
                closest_constellation: None,
            }
        };

        let strategy_prior = if self.config.enable_strategy {
            self.strategy_prior(scenario)
        } else {
            StrategyPrior {
                pattern_count: 0,
                themes: Vec::new(),
                score_adjustment: 0.0,
            }
        };

        let surprise = if self.config.enable_surprise {
            self.evaluate_surprise(scenario)
        } else {
            SurpriseAssessment {
                decision: GateDecisionKind::EncodeNormal,
                novelty_score: scenario.novelty,
                needs_deep_analysis: false,
            }
        };

        // Compute adjusted score
        let mut adjusted = scenario.score;
        if novelty.is_familiar {
            adjusted += self.config.familiarity_bonus;
        } else if novelty.novelty_score > 0.5 {
            adjusted -= self.config.novelty_penalty;
        }
        adjusted += strategy_prior.score_adjustment;
        adjusted = adjusted.clamp(0.0, 1.0);

        PatternEnrichedScenario {
            scenario: scenario.clone(),
            novelty,
            strategy_prior,
            surprise,
            adjusted_score: adjusted,
        }
    }

    /// Enrich multiple scenarios.
    #[must_use]
    pub fn enrich_scenarios(&self, scenarios: &[Scenario]) -> Vec<PatternEnrichedScenario> {
        scenarios.iter().map(|s| self.enrich_scenario(s)).collect()
    }

    /// Get the configuration.
    #[must_use]
    pub const fn config(&self) -> &PatternBridgeConfig {
        &self.config
    }

    /// Get the spreading activation engine (for external use).
    #[must_use]
    pub fn spreading_activation(&self) -> SpreadingActivation {
        SpreadingActivation::default()
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use wm_bicameral::scenario::Scenario;
    use wm_bicameral::world_model::PredictedState;

    fn make_scenario(action: &str, novelty: f32, score: f32) -> Scenario {
        Scenario {
            action: action.to_string(),
            trajectory: vec![PredictedState::new("initial state".to_string(), 0.7)],
            score,
            risk: 0.3,
            novelty,
            rationale: "test scenario".to_string(),
            breakdown: None,
        }
    }

    #[test]
    fn pattern_bridge_default() {
        let bridge = PatternBridge::default();
        assert!(bridge.config().enable_constellation);
        assert!(bridge.config().enable_strategy);
        assert!(bridge.config().enable_surprise);
    }

    #[test]
    fn assess_novelty_no_constellations() {
        let bridge = PatternBridge::default();
        let scenario = make_scenario("explore new territory", 0.8, 0.5);
        let novelty = bridge.assess_novelty(&scenario);
        assert!(!novelty.is_familiar);
        assert_eq!(novelty.constellation_count, 0);
        assert!((novelty.novelty_score - 1.0).abs() < 0.001);
    }

    #[test]
    fn assess_novelty_with_matching_constellation() {
        use crate::constellation::{Constellation, ConstellationReport};
        use wm_core::Galaxy;

        let mut bridge = PatternBridge::default();
        let mut report = ConstellationReport::new();
        report.constellations.push(Constellation {
            name: "exploration".to_string(),
            memory_ids: vec![],
            centroid: (0.5, 0.5, 0.5),
            dominant_tags: vec!["explore".to_string()],
            size: 5,
            galaxies: vec![Galaxy::Codex],
        });
        bridge.update_constellations(report);

        let scenario = make_scenario("explore the data", 0.3, 0.6);
        let novelty = bridge.assess_novelty(&scenario);
        assert!(novelty.is_familiar);
        assert_eq!(
            novelty.closest_constellation.as_deref(),
            Some("exploration")
        );
        assert!((novelty.novelty_score - 0.2).abs() < 0.001);
    }

    #[test]
    fn assess_novelty_with_non_matching_constellation() {
        use crate::constellation::{Constellation, ConstellationReport};
        use wm_core::Galaxy;

        let mut bridge = PatternBridge::default();
        let mut report = ConstellationReport::new();
        report.constellations.push(Constellation {
            name: "other".to_string(),
            memory_ids: vec![],
            centroid: (0.5, 0.5, 0.5),
            dominant_tags: vec!["unrelated".to_string()],
            size: 3,
            galaxies: vec![Galaxy::Codex],
        });
        bridge.update_constellations(report);

        let scenario = make_scenario("explore the data", 0.7, 0.5);
        let novelty = bridge.assess_novelty(&scenario);
        assert!(!novelty.is_familiar);
        assert_eq!(novelty.constellation_count, 1);
        assert!((novelty.novelty_score - 0.6).abs() < 0.001);
    }

    #[test]
    fn strategy_prior_no_patterns() {
        let bridge = PatternBridge::default();
        let scenario = make_scenario("test action", 0.5, 0.5);
        let prior = bridge.strategy_prior(&scenario);
        assert_eq!(prior.pattern_count, 0);
        assert!(prior.themes.is_empty());
        assert!((prior.score_adjustment - 0.0).abs() < 0.001);
    }

    #[test]
    fn strategy_prior_with_matching_theme() {
        use crate::strategy::SynthesisReport;

        let mut bridge = PatternBridge::default();
        let mut report = SynthesisReport::new();
        report.strategies_synthesized = 3;
        report.themes = vec!["optimize".to_string(), "caching".to_string()];
        bridge.update_strategies(report);

        let scenario = make_scenario("optimize the cache", 0.4, 0.6);
        let prior = bridge.strategy_prior(&scenario);
        assert_eq!(prior.pattern_count, 3);
        assert_eq!(prior.themes.len(), 2);
        assert!((prior.score_adjustment - 0.1).abs() < 0.001);
    }

    #[test]
    fn evaluate_surprise_high_novelty() {
        let bridge = PatternBridge::default();
        let scenario = make_scenario("novel action", 0.8, 0.5);
        let surprise = bridge.evaluate_surprise(&scenario);
        assert_eq!(surprise.decision, GateDecisionKind::Encode);
        assert!(surprise.needs_deep_analysis);
        assert!((surprise.novelty_score - 0.8).abs() < 0.001);
    }

    #[test]
    fn evaluate_surprise_low_novelty() {
        let bridge = PatternBridge::default();
        let scenario = make_scenario("routine action", 0.05, 0.5);
        let surprise = bridge.evaluate_surprise(&scenario);
        assert_eq!(surprise.decision, GateDecisionKind::Skip);
        assert!(!surprise.needs_deep_analysis);
    }

    #[test]
    fn evaluate_surprise_moderate_novelty() {
        let bridge = PatternBridge::default();
        let scenario = make_scenario("moderate action", 0.3, 0.5);
        let surprise = bridge.evaluate_surprise(&scenario);
        assert_eq!(surprise.decision, GateDecisionKind::EncodeNormal);
        assert!(!surprise.needs_deep_analysis);
    }

    #[test]
    fn enrich_scenario_combines_all() {
        use crate::constellation::{Constellation, ConstellationReport};
        use wm_core::Galaxy;

        let mut bridge = PatternBridge::default();
        let mut report = ConstellationReport::new();
        report.constellations.push(Constellation {
            name: "testing".to_string(),
            memory_ids: vec![],
            centroid: (0.5, 0.5, 0.5),
            dominant_tags: vec!["test".to_string()],
            size: 4,
            galaxies: vec![Galaxy::Codex],
        });
        bridge.update_constellations(report);

        let scenario = make_scenario("test the system", 0.3, 0.5);
        let enriched = bridge.enrich_scenario(&scenario);
        assert!(enriched.novelty.is_familiar);
        assert!(enriched.adjusted_score >= scenario.score);
    }

    #[test]
    fn enrich_scenario_novel_gets_penalty() {
        let bridge = PatternBridge::default();
        let scenario = make_scenario("completely new approach", 0.9, 0.5);
        let enriched = bridge.enrich_scenario(&scenario);
        assert!(!enriched.novelty.is_familiar);
        assert!(enriched.adjusted_score < scenario.score);
    }

    #[test]
    fn enrich_scenarios_batch() {
        let bridge = PatternBridge::default();
        let scenarios = vec![
            make_scenario("action1", 0.3, 0.5),
            make_scenario("action2", 0.7, 0.6),
        ];
        let enriched = bridge.enrich_scenarios(&scenarios);
        assert_eq!(enriched.len(), 2);
    }

    #[test]
    fn pattern_enriched_scenario_to_json() {
        let bridge = PatternBridge::default();
        let scenario = make_scenario("test action", 0.5, 0.5);
        let enriched = bridge.enrich_scenario(&scenario);
        let json = enriched.to_json();
        assert!(json["action"].as_str().is_some());
        assert!(json["adjusted_score"].as_f64().is_some());
        assert!(json["novelty"]["novelty_score"].as_f64().is_some());
        assert!(json["surprise"]["decision"].as_str().is_some());
    }

    #[test]
    fn gate_decision_kind_from_gate_decision() {
        assert_eq!(
            GateDecisionKind::from(GateDecision::Encode),
            GateDecisionKind::Encode
        );
        assert_eq!(
            GateDecisionKind::from(GateDecision::EncodeNormal),
            GateDecisionKind::EncodeNormal
        );
        assert_eq!(
            GateDecisionKind::from(GateDecision::Skip),
            GateDecisionKind::Skip
        );
    }

    #[test]
    fn spreading_activation_default() {
        let bridge = PatternBridge::default();
        let sa = bridge.spreading_activation();
        assert_eq!(sa.max_hops, 3);
    }

    #[test]
    fn disabled_constellation_skips_assessment() {
        let config = PatternBridgeConfig {
            enable_constellation: false,
            ..Default::default()
        };
        let bridge = PatternBridge::new(config);
        let scenario = make_scenario("test", 0.5, 0.5);
        let enriched = bridge.enrich_scenario(&scenario);
        assert_eq!(enriched.novelty.constellation_count, 0);
        assert!((enriched.novelty.novelty_score - 0.5).abs() < 0.001);
    }

    #[test]
    fn disabled_strategy_skips_prior() {
        let config = PatternBridgeConfig {
            enable_strategy: false,
            ..Default::default()
        };
        let bridge = PatternBridge::new(config);
        let scenario = make_scenario("test", 0.5, 0.5);
        let enriched = bridge.enrich_scenario(&scenario);
        assert_eq!(enriched.strategy_prior.pattern_count, 0);
        assert!((enriched.strategy_prior.score_adjustment - 0.0).abs() < 0.001);
    }
}
