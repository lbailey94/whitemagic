//! Imagination Configurator — System III self-regulation.
//!
//! Inspired by SR²AM (2026), the configurator decides *when* and *how deeply*
//! to simulate. Not every task needs imagination — routine tool dispatches
//! go direct (System I), while novel/complex problems trigger simulation
//! (System II).
//!
//! Deliberation modes:
//! - **Direct**: No simulation (simple/routine tasks, ~85% of queries)
//! - **Shallow**: 1-2 step rollout (moderate complexity)
//! - **Deep**: 3-5 step rollout with multiple candidates (complex/novel)
//! - **Research**: Extended simulation with memory storage (novel problems)

use serde::{Deserialize, Serialize};

/// How deeply to deliberate before acting.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum DeliberationMode {
    /// Direct action — no simulation needed (simple/routine tasks).
    Direct,
    /// Shallow simulation — 1-2 steps ahead (moderate complexity).
    Shallow,
    /// Deep simulation — 3-5 steps ahead with multiple candidates (complex/novel).
    Deep,
    /// Research mode — extended simulation with memory storage (novel problems).
    Research,
}

impl DeliberationMode {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Direct => "direct",
            Self::Shallow => "shallow",
            Self::Deep => "deep",
            Self::Research => "research",
        }
    }

    /// Number of simulation steps (horizon) for this mode.
    #[must_use]
    pub const fn horizon(self) -> usize {
        match self {
            Self::Direct => 0,
            Self::Shallow => 2,
            Self::Deep => 5,
            Self::Research => 10,
        }
    }

    /// Number of candidate actions to generate.
    #[must_use]
    pub const fn n_candidates(self) -> usize {
        match self {
            Self::Direct => 0,
            Self::Shallow => 2,
            Self::Deep => 4,
            Self::Research => 6,
        }
    }

    /// Whether this mode uses the creative (right) hemisphere.
    #[must_use]
    pub const fn uses_creative(self) -> bool {
        matches!(self, Self::Deep | Self::Research)
    }

    /// Whether this mode stores findings to memory.
    #[must_use]
    pub const fn stores_hypotheses(self) -> bool {
        matches!(self, Self::Research)
    }

    /// All modes in order of increasing deliberation.
    #[must_use]
    pub const fn all() -> [Self; 4] {
        [Self::Direct, Self::Shallow, Self::Deep, Self::Research]
    }
}

impl std::fmt::Display for DeliberationMode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Configuration for the imagination configurator.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfiguratorConfig {
    /// Complexity threshold for shallow mode (0.0–1.0).
    pub shallow_threshold: f32,
    /// Complexity threshold for deep mode (0.0–1.0).
    pub deep_threshold: f32,
    /// Complexity threshold for research mode (0.0–1.0).
    pub research_threshold: f32,
    /// Novelty threshold for triggering deep mode even if complexity is moderate.
    pub novelty_deep_threshold: f32,
    /// Stakes threshold — high-stakes tasks get deeper deliberation.
    pub high_stakes_threshold: f32,
}

impl Default for ConfiguratorConfig {
    fn default() -> Self {
        Self {
            shallow_threshold: 0.3,
            deep_threshold: 0.6,
            research_threshold: 0.8,
            novelty_deep_threshold: 0.7,
            high_stakes_threshold: 0.7,
        }
    }
}

/// System III — the imagination configurator.
///
/// Decides when and how deeply to simulate based on:
/// 1. **Task complexity** — measured by prompt length, keyword analysis
/// 2. **Novelty** — how unfamiliar is this situation?
/// 3. **Stakes** — how important is the outcome?
///
/// Following SR²AM's key insight: the configurator learns to plan *further ahead*,
/// not *more often*. Most tasks go direct; only novel/complex ones trigger simulation.
pub struct ImaginationConfigurator {
    config: ConfiguratorConfig,
}

impl ImaginationConfigurator {
    /// Create a new configurator with the given config.
    #[must_use]
    pub const fn new(config: ConfiguratorConfig) -> Self {
        Self { config }
    }

    /// Create a configurator with default config.
    #[must_use]
    pub fn with_defaults() -> Self {
        Self::new(ConfiguratorConfig::default())
    }

    /// Decide deliberation mode based on task complexity, novelty, and stakes.
    ///
    /// - `task`: The task description (used for complexity estimation)
    /// - `novelty`: How novel/unfamiliar this situation is (0.0–1.0)
    /// - `stakes`: How important the outcome is (0.0–1.0)
    #[must_use]
    pub fn decide(&self, task: &str, novelty: f32, stakes: f32) -> DeliberationMode {
        let complexity = self.estimate_complexity(task);

        // High stakes bumps deliberation up one level
        let effective_complexity = if stakes > self.config.high_stakes_threshold {
            (complexity + 0.15).min(1.0)
        } else {
            complexity
        };

        // High novelty can trigger deep mode even at moderate complexity
        if novelty > self.config.novelty_deep_threshold
            && effective_complexity > self.config.shallow_threshold
        {
            return DeliberationMode::Deep;
        }

        if effective_complexity >= self.config.research_threshold {
            DeliberationMode::Research
        } else if effective_complexity >= self.config.deep_threshold {
            DeliberationMode::Deep
        } else if effective_complexity >= self.config.shallow_threshold {
            DeliberationMode::Shallow
        } else {
            DeliberationMode::Direct
        }
    }

    /// Estimate task complexity from the task description.
    ///
    /// Uses heuristics: word count, question marks, complexity markers,
    /// and conditional/logical operators.
    #[must_use]
    pub fn estimate_complexity(&self, task: &str) -> f32 {
        let lower = task.to_lowercase();
        let word_count = task.split_whitespace().count();

        // Base complexity from length
        let length_score = (word_count as f32 / 50.0).min(0.4);

        // Complexity markers
        let complexity_markers = [
            "complex",
            "nuanced",
            "tradeoff",
            "trade-off",
            "multi-step",
            "interdisciplinary",
            "contextual",
            "conditional",
            "depends",
            "optimize",
            "analyze",
            "design",
            "architecture",
            "refactor",
            "integrate",
            "debug",
            "investigate",
            "research",
            "compare",
            "evaluate",
            "assess",
            "strategy",
            "plan",
        ];
        let marker_count = complexity_markers
            .iter()
            .filter(|m| lower.contains(*m))
            .count();
        let marker_score = (marker_count as f32 * 0.1).min(0.3);

        // Logical operators indicate multi-condition reasoning
        let logical_markers = [
            "if", "else", "when", "unless", "while", "for each", "either", "or",
        ];
        let logical_count = logical_markers
            .iter()
            .filter(|m| lower.contains(*m))
            .count();
        let logical_score = (logical_count as f32 * 0.05).min(0.15);

        // Questions indicate uncertainty
        let question_count = task.matches('?').count();
        let question_score = (question_count as f32 * 0.05).min(0.15);

        let total = length_score + marker_score + logical_score + question_score;
        total.min(1.0)
    }

    /// Get the configurator's config.
    #[must_use]
    pub const fn config(&self) -> &ConfiguratorConfig {
        &self.config
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── DeliberationMode tests ─────────────────────────────────────────

    #[test]
    fn mode_horizons() {
        assert_eq!(DeliberationMode::Direct.horizon(), 0);
        assert_eq!(DeliberationMode::Shallow.horizon(), 2);
        assert_eq!(DeliberationMode::Deep.horizon(), 5);
        assert_eq!(DeliberationMode::Research.horizon(), 10);
    }

    #[test]
    fn mode_n_candidates() {
        assert_eq!(DeliberationMode::Direct.n_candidates(), 0);
        assert_eq!(DeliberationMode::Shallow.n_candidates(), 2);
        assert_eq!(DeliberationMode::Deep.n_candidates(), 4);
        assert_eq!(DeliberationMode::Research.n_candidates(), 6);
    }

    #[test]
    fn mode_uses_creative() {
        assert!(!DeliberationMode::Direct.uses_creative());
        assert!(!DeliberationMode::Shallow.uses_creative());
        assert!(DeliberationMode::Deep.uses_creative());
        assert!(DeliberationMode::Research.uses_creative());
    }

    #[test]
    fn mode_stores_hypotheses() {
        assert!(!DeliberationMode::Direct.stores_hypotheses());
        assert!(!DeliberationMode::Shallow.stores_hypotheses());
        assert!(!DeliberationMode::Deep.stores_hypotheses());
        assert!(DeliberationMode::Research.stores_hypotheses());
    }

    #[test]
    fn mode_all_has_4() {
        assert_eq!(DeliberationMode::all().len(), 4);
    }

    #[test]
    fn mode_as_str() {
        assert_eq!(DeliberationMode::Direct.as_str(), "direct");
        assert_eq!(DeliberationMode::Shallow.as_str(), "shallow");
        assert_eq!(DeliberationMode::Deep.as_str(), "deep");
        assert_eq!(DeliberationMode::Research.as_str(), "research");
    }

    #[test]
    fn mode_display() {
        assert_eq!(format!("{}", DeliberationMode::Direct), "direct");
        assert_eq!(format!("{}", DeliberationMode::Research), "research");
    }

    // ── Complexity estimation tests ────────────────────────────────────

    #[test]
    fn simple_task_low_complexity() {
        let config = ImaginationConfigurator::with_defaults();
        let complexity = config.estimate_complexity("hello");
        assert!(
            complexity < 0.3,
            "simple task should have low complexity: {complexity}"
        );
    }

    #[test]
    fn complex_task_high_complexity() {
        let config = ImaginationConfigurator::with_defaults();
        let task = "Analyze and design a complex multi-step architecture with tradeoffs and conditional logic for the system";
        let complexity = config.estimate_complexity(task);
        assert!(
            complexity > 0.5,
            "complex task should have high complexity: {complexity}"
        );
    }

    #[test]
    fn questions_increase_complexity() {
        let config = ImaginationConfigurator::with_defaults();
        let no_q = config.estimate_complexity("do the thing");
        let with_q = config.estimate_complexity("do the thing? or that thing? or another?");
        assert!(with_q > no_q, "questions should increase complexity");
    }

    #[test]
    fn complexity_capped_at_one() {
        let config = ImaginationConfigurator::with_defaults();
        let task = "complex nuanced tradeoff optimize analyze design architecture refactor integrate debug investigate research compare evaluate assess strategy plan if else when unless while either or";
        let complexity = config.estimate_complexity(task);
        assert!(complexity <= 1.0);
    }

    // ── Decision tests ─────────────────────────────────────────────────

    #[test]
    fn simple_task_direct() {
        let config = ImaginationConfigurator::with_defaults();
        let mode = config.decide("hello", 0.1, 0.1);
        assert_eq!(mode, DeliberationMode::Direct);
    }

    #[test]
    fn moderate_task_shallow() {
        let config = ImaginationConfigurator::with_defaults();
        let mode = config.decide("analyze and evaluate the complex data report", 0.2, 0.3);
        assert_eq!(mode, DeliberationMode::Shallow);
    }

    #[test]
    fn complex_task_deep() {
        let config = ImaginationConfigurator::with_defaults();
        let task = "Design and optimize a complex multi-step architecture with tradeoffs, conditional logic, and assess the strategy";
        let mode = config.decide(task, 0.3, 0.5);
        assert_eq!(mode, DeliberationMode::Deep);
    }

    #[test]
    fn novel_task_triggers_deep() {
        let config = ImaginationConfigurator::with_defaults();
        // Moderate complexity but high novelty → Deep
        let mode = config.decide("analyze and evaluate the complex data", 0.8, 0.3);
        assert_eq!(mode, DeliberationMode::Deep);
    }

    #[test]
    fn very_complex_task_research() {
        let config = ImaginationConfigurator::with_defaults();
        let task = "Research and investigate complex interdisciplinary tradeoffs with conditional multi-step architecture design and optimization strategy. Analyze and evaluate if the plan works. When should we assess alternatives? Compare and debug the integration.";
        let mode = config.decide(task, 0.5, 0.5);
        assert_eq!(mode, DeliberationMode::Research);
    }

    #[test]
    fn high_stakes_bumps_deliberation() {
        let config = ImaginationConfigurator::with_defaults();
        // Task at shallow threshold with high stakes → should bump to deep
        let mode = config.decide("analyze the data", 0.2, 0.9);
        assert!(
            mode >= DeliberationMode::Shallow,
            "high stakes should at least trigger shallow: {mode}"
        );
    }

    // ── Config tests ───────────────────────────────────────────────────

    #[test]
    fn custom_config_thresholds() {
        let config = ConfiguratorConfig {
            shallow_threshold: 0.5,
            deep_threshold: 0.7,
            research_threshold: 0.9,
            novelty_deep_threshold: 0.8,
            high_stakes_threshold: 0.8,
        };
        let configurator = ImaginationConfigurator::new(config);
        // With higher thresholds, moderate tasks go direct
        let mode = configurator.decide("analyze the data", 0.2, 0.3);
        assert_eq!(mode, DeliberationMode::Direct);
    }

    #[test]
    fn config_accessor() {
        let configurator = ImaginationConfigurator::with_defaults();
        let config = configurator.config();
        assert!((config.shallow_threshold - 0.3).abs() < 0.01);
    }

    // ── Edge cases ─────────────────────────────────────────────────────

    #[test]
    fn empty_task_is_direct() {
        let config = ImaginationConfigurator::with_defaults();
        let mode = config.decide("", 0.0, 0.0);
        assert_eq!(mode, DeliberationMode::Direct);
    }

    #[test]
    fn max_novelty_with_simple_task_still_direct() {
        let config = ImaginationConfigurator::with_defaults();
        // High novelty but very low complexity → novelty gate requires complexity > shallow_threshold
        let mode = config.decide("hi", 1.0, 0.1);
        assert_eq!(mode, DeliberationMode::Direct);
    }

    #[test]
    fn max_stakes_with_simple_task() {
        let config = ImaginationConfigurator::with_defaults();
        // Simple task with max stakes → complexity bumped by 0.15 → still < 0.3
        let mode = config.decide("hello", 0.0, 1.0);
        assert_eq!(mode, DeliberationMode::Direct);
    }
}
