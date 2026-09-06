//! Homeostatic Loop — harmony-driven self-regulation.
//!
//! **N19**: Reads the [`HarmonyVector`] and [`AnomalyDetector`] output to
//! take graduated corrective actions across 4 levels:
//!
//! 1. **OBSERVE** — log only, no action taken
//! 2. **ADVISE** — emit a recommendation, log the advice
//! 3. **CORRECT** — take gentle action (shed load, cool down tool)
//! 4. **INTERVENE** — strong action (circuit breaker, force dream)
//!
//! The loop runs at the planning timescale (every 1s) and checks each
//! harmony dimension against configurable thresholds. Actions are
//! recorded for feedback loop analysis by the SelfModel.
//!
//! Ported from v2's `harmony/homeostatic_loop.py`.

#![forbid(unsafe_code)]

use std::collections::VecDeque;

use serde::{Deserialize, Serialize};

use crate::HarmonyVector;
use crate::anomaly::{AnomalyDetector, AnomalySeverity, HarmonyDimension};

// ── Action Level ──────────────────────────────────────────────────────

/// Graduated response level for homeostatic correction.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
#[repr(u8)]
pub enum ActionLevel {
    /// Log only, no action taken.
    Observe = 0,
    /// Emit a recommendation, log the advice.
    Advise = 1,
    /// Take gentle action (shed load, cool down tool, tighten dharma).
    Correct = 2,
    /// Strong action (circuit breaker, force Theta/dream, refuse writes).
    Intervene = 3,
}

impl ActionLevel {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Observe => "observe",
            Self::Advise => "advise",
            Self::Correct => "correct",
            Self::Intervene => "intervene",
        }
    }

    /// Whether this level takes active corrective action.
    #[must_use]
    pub const fn is_active(self) -> bool {
        matches!(self, Self::Correct | Self::Intervene)
    }
}

impl std::fmt::Display for ActionLevel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

// ── Homeostatic Action ────────────────────────────────────────────────

/// The type of corrective action to take.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ActionType {
    /// No action needed.
    None,
    /// Log the observation.
    Log,
    /// Emit a recommendation event.
    Recommend,
    /// Shed load — reduce concurrent operations.
    ShedLoad,
    /// Cool down a specific tool (rate limit).
    ToolCooldown,
    /// Tighten dharma profile (more restrictive governance).
    TightenDharma,
    /// Trigger memory lifecycle sweep (mindful forgetting).
    MemorySweep,
    /// Open circuit breaker for a tool.
    CircuitBreaker,
    /// Force Theta brain-wave state (dream/consolidation).
    ForceTheta,
    /// Refuse write operations (read-only mode).
    RefuseWrites,
    /// Increase monitoring frequency.
    IncreaseMonitoring,
}

impl ActionType {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Log => "log",
            Self::Recommend => "recommend",
            Self::ShedLoad => "shed_load",
            Self::ToolCooldown => "tool_cooldown",
            Self::TightenDharma => "tighten_dharma",
            Self::MemorySweep => "memory_sweep",
            Self::CircuitBreaker => "circuit_breaker",
            Self::ForceTheta => "force_theta",
            Self::RefuseWrites => "refuse_writes",
            Self::IncreaseMonitoring => "increase_monitoring",
        }
    }
}

impl std::fmt::Display for ActionType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

// ── Homeostatic Action Event ──────────────────────────────────────────

/// A homeostatic action — the result of a loop cycle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HomeostaticAction {
    /// The dimension that triggered this action.
    pub dimension: HarmonyDimension,
    /// The action level (Observe/Advise/Correct/Intervene).
    pub level: ActionLevel,
    /// The specific action type.
    pub action: ActionType,
    /// The current value of the dimension.
    pub current_value: f32,
    /// The threshold that was crossed.
    pub threshold: f32,
    /// Human-readable description of the action.
    pub description: String,
    /// Whether this action was actually taken (false = advisory only).
    pub executed: bool,
}

impl HomeostaticAction {
    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "dimension": self.dimension.as_str(),
            "level": self.level.as_str(),
            "action": self.action.as_str(),
            "current_value": self.current_value,
            "threshold": self.threshold,
            "description": self.description,
            "executed": self.executed,
        })
    }
}

// ── Dimension Thresholds ──────────────────────────────────────────────

/// Threshold configuration for a single harmony dimension.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DimensionThreshold {
    /// The dimension this threshold applies to.
    pub dimension: HarmonyDimension,
    /// Advise when value crosses this.
    pub advise_threshold: f32,
    /// Correct when value crosses this.
    pub correct_threshold: f32,
    /// Intervene when value crosses this.
    pub intervene_threshold: f32,
    /// Whether the threshold is for high values (true) or low values (false).
    pub high_is_bad: bool,
}

impl DimensionThreshold {
    /// Create a threshold for a "high is bad" dimension (e.g., CPU load).
    #[must_use]
    pub const fn high_is_bad(
        dimension: HarmonyDimension,
        advise: f32,
        correct: f32,
        intervene: f32,
    ) -> Self {
        Self {
            dimension,
            advise_threshold: advise,
            correct_threshold: correct,
            intervene_threshold: intervene,
            high_is_bad: true,
        }
    }

    /// Create a threshold for a "low is bad" dimension (e.g., battery).
    #[must_use]
    pub const fn low_is_bad(
        dimension: HarmonyDimension,
        advise: f32,
        correct: f32,
        intervene: f32,
    ) -> Self {
        Self {
            dimension,
            advise_threshold: advise,
            correct_threshold: correct,
            intervene_threshold: intervene,
            high_is_bad: false,
        }
    }

    /// Determine the action level for a given value.
    #[must_use]
    pub fn evaluate(&self, value: f32) -> ActionLevel {
        if self.high_is_bad {
            if value >= self.intervene_threshold {
                ActionLevel::Intervene
            } else if value >= self.correct_threshold {
                ActionLevel::Correct
            } else if value >= self.advise_threshold {
                ActionLevel::Advise
            } else {
                ActionLevel::Observe
            }
        } else {
            // Low is bad — invert comparisons
            if value <= self.intervene_threshold {
                ActionLevel::Intervene
            } else if value <= self.correct_threshold {
                ActionLevel::Correct
            } else if value <= self.advise_threshold {
                ActionLevel::Advise
            } else {
                ActionLevel::Observe
            }
        }
    }
}

/// Default thresholds for all 7 harmony dimensions.
#[must_use]
pub fn default_thresholds() -> Vec<DimensionThreshold> {
    vec![
        DimensionThreshold::high_is_bad(HarmonyDimension::CpuLoad, 0.7, 0.85, 0.95),
        DimensionThreshold::high_is_bad(HarmonyDimension::MemoryPressure, 0.7, 0.85, 0.95),
        DimensionThreshold::high_is_bad(HarmonyDimension::SwapUsage, 0.3, 0.5, 0.8),
        DimensionThreshold::high_is_bad(HarmonyDimension::DiskIoRate, 0.7, 0.85, 0.95),
        DimensionThreshold::low_is_bad(HarmonyDimension::HealthScore, 0.6, 0.4, 0.2),
        DimensionThreshold::low_is_bad(HarmonyDimension::BatteryPercent, 0.3, 0.15, 0.05),
        DimensionThreshold::high_is_bad(HarmonyDimension::Temperature, 70.0, 80.0, 90.0),
    ]
}

// ── Homeostatic Loop Config ───────────────────────────────────────────

/// Configuration for the [`HomeostaticLoop`].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HomeostaticConfig {
    /// Thresholds per dimension.
    pub thresholds: Vec<DimensionThreshold>,
    /// Whether to actually execute corrective actions (false = dry run).
    pub execute_actions: bool,
    /// Maximum actions to retain in history.
    pub max_history: usize,
    /// Whether to consider anomaly alerts in addition to thresholds.
    pub use_anomaly_detector: bool,
}

impl Default for HomeostaticConfig {
    fn default() -> Self {
        Self {
            thresholds: default_thresholds(),
            execute_actions: true,
            max_history: 100,
            use_anomaly_detector: true,
        }
    }
}

// ── Homeostatic Loop ──────────────────────────────────────────────────

/// Statistics for the homeostatic loop.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct LoopStats {
    /// Total cycles run.
    pub cycles: u64,
    /// Total actions taken (all levels).
    pub total_actions: u64,
    /// Actions per level.
    pub actions_per_level: [u64; 4],
    /// Actions per type (as string → count).
    pub actions_per_type: std::collections::HashMap<String, u64>,
    /// Last cycle timestamp (Unix seconds).
    pub last_cycle: i64,
}

/// The Homeostatic Loop — graduated self-regulation based on harmony state.
///
/// Runs a sample cycle that reads the [`HarmonyVector`] and optional
/// [`AnomalyDetector`] alerts, evaluates thresholds, and produces
/// [`HomeostaticAction`]s. Actions can be advisory (Observe/Advise) or
/// active (Correct/Intervene).
///
/// # Example
/// ```no_run
/// use wm_substrate::{HarmonyVector, SubstrateMonitor};
/// use wm_substrate::anomaly::{AnomalyDetector, AnomalyConfig};
/// use wm_substrate::homeostatic::{HomeostaticLoop, HomeostaticConfig};
///
/// let mut loop_ = HomeostaticLoop::new(HomeostaticConfig::default());
/// let mut monitor = SubstrateMonitor::new(100);
/// let mut detector = AnomalyDetector::new(AnomalyConfig::default());
///
/// let hv = monitor.sample();
/// detector.check(&hv);
/// let actions = loop_.sample_cycle(&hv, &detector);
/// for action in &actions {
///     println!("{:?}: {}", action.level, action.description);
/// }
/// ```
pub struct HomeostaticLoop {
    config: HomeostaticConfig,
    history: VecDeque<HomeostaticAction>,
    stats: LoopStats,
}

impl Default for HomeostaticLoop {
    fn default() -> Self {
        Self::new(HomeostaticConfig::default())
    }
}

impl std::fmt::Debug for HomeostaticLoop {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("HomeostaticLoop")
            .field("cycles", &self.stats.cycles)
            .field("total_actions", &self.stats.total_actions)
            .field("history_len", &self.history.len())
            .finish_non_exhaustive()
    }
}

impl HomeostaticLoop {
    /// Create a new homeostatic loop with the given configuration.
    #[must_use]
    pub fn new(config: HomeostaticConfig) -> Self {
        Self {
            config,
            history: VecDeque::new(),
            stats: LoopStats::default(),
        }
    }

    /// Run a sample cycle — evaluates the harmony vector and anomaly alerts,
    /// returns the list of actions taken.
    pub fn sample_cycle(
        &mut self,
        hv: &HarmonyVector,
        detector: &AnomalyDetector,
    ) -> Vec<HomeostaticAction> {
        self.stats.cycles += 1;
        self.stats.last_cycle = chrono::Utc::now().timestamp();

        let mut new_actions = Vec::new();

        // 1. Evaluate thresholds for each dimension
        for threshold in &self.config.thresholds {
            if let Some(value) = threshold.dimension.extract(hv) {
                let level = threshold.evaluate(value);

                if level != ActionLevel::Observe {
                    let action_type = self.select_action(threshold.dimension, level);
                    let description =
                        self.describe_action(threshold.dimension, level, value, threshold);
                    let crossed_threshold = match level {
                        ActionLevel::Intervene => threshold.intervene_threshold,
                        ActionLevel::Correct => threshold.correct_threshold,
                        ActionLevel::Advise => threshold.advise_threshold,
                        ActionLevel::Observe => threshold.advise_threshold,
                    };

                    new_actions.push(HomeostaticAction {
                        dimension: threshold.dimension,
                        level,
                        action: action_type,
                        current_value: value,
                        threshold: crossed_threshold,
                        description,
                        executed: self.config.execute_actions && level.is_active(),
                    });
                }
            }
        }

        // 2. Check anomaly detector alerts
        if self.config.use_anomaly_detector {
            for dim in HarmonyDimension::ALL {
                let (mean, std, n) = detector.stats(dim);
                if n < 5 {
                    continue;
                }

                if let Some(current) = dim.extract(hv) {
                    if std > 0.0 {
                        let z = (current - mean) / std;
                        if let Some(severity) = AnomalySeverity::from_z_score(z) {
                            let level = match severity {
                                AnomalySeverity::Critical => ActionLevel::Intervene,
                                AnomalySeverity::Warning => ActionLevel::Advise,
                            };

                            // Only add if we haven't already flagged this dimension
                            if !new_actions.iter().any(|a| a.dimension == dim) {
                                let action_type = if level == ActionLevel::Intervene {
                                    ActionType::IncreaseMonitoring
                                } else {
                                    ActionType::Log
                                };

                                new_actions.push(HomeostaticAction {
                                    dimension: dim,
                                    level,
                                    action: action_type,
                                    current_value: current,
                                    threshold: mean,
                                    description: format!(
                                        "Anomaly detected: {} z-score {:.2} (mean={:.2}, std={:.2})",
                                        dim.as_str(), z, mean, std
                                    ),
                                    executed: false,
                                });
                            }
                        }
                    }
                }
            }
        }

        // Record all actions in history and stats
        for action in &new_actions {
            self.record_action(action);
        }

        new_actions
    }

    /// Select the appropriate action type for a dimension + level.
    const fn select_action(&self, dim: HarmonyDimension, level: ActionLevel) -> ActionType {
        match (dim, level) {
            // CPU load
            (HarmonyDimension::CpuLoad, ActionLevel::Advise) => ActionType::Log,
            (HarmonyDimension::CpuLoad, ActionLevel::Correct) => ActionType::ShedLoad,
            (HarmonyDimension::CpuLoad, ActionLevel::Intervene) => ActionType::ForceTheta,

            // Memory pressure
            (HarmonyDimension::MemoryPressure, ActionLevel::Advise) => ActionType::Log,
            (HarmonyDimension::MemoryPressure, ActionLevel::Correct) => ActionType::MemorySweep,
            (HarmonyDimension::MemoryPressure, ActionLevel::Intervene) => ActionType::RefuseWrites,

            // Swap usage
            (HarmonyDimension::SwapUsage, ActionLevel::Advise) => ActionType::Log,
            (HarmonyDimension::SwapUsage, ActionLevel::Correct) => ActionType::MemorySweep,
            (HarmonyDimension::SwapUsage, ActionLevel::Intervene) => ActionType::RefuseWrites,

            // Disk I/O
            (HarmonyDimension::DiskIoRate, ActionLevel::Advise) => ActionType::Log,
            (HarmonyDimension::DiskIoRate, ActionLevel::Correct) => ActionType::ShedLoad,
            (HarmonyDimension::DiskIoRate, ActionLevel::Intervene) => ActionType::CircuitBreaker,

            // Health score (low is bad)
            (HarmonyDimension::HealthScore, ActionLevel::Advise) => ActionType::Recommend,
            (HarmonyDimension::HealthScore, ActionLevel::Correct) => ActionType::TightenDharma,
            (HarmonyDimension::HealthScore, ActionLevel::Intervene) => ActionType::ForceTheta,

            // Battery (low is bad)
            (HarmonyDimension::BatteryPercent, ActionLevel::Advise) => ActionType::Recommend,
            (HarmonyDimension::BatteryPercent, ActionLevel::Correct) => ActionType::ShedLoad,
            (HarmonyDimension::BatteryPercent, ActionLevel::Intervene) => ActionType::ForceTheta,

            // Temperature (high is bad)
            (HarmonyDimension::Temperature, ActionLevel::Advise) => ActionType::Log,
            (HarmonyDimension::Temperature, ActionLevel::Correct) => ActionType::ShedLoad,
            (HarmonyDimension::Temperature, ActionLevel::Intervene) => ActionType::ForceTheta,

            // Default
            (_, ActionLevel::Observe) => ActionType::None,
        }
    }

    /// Generate a human-readable description for an action.
    fn describe_action(
        &self,
        dim: HarmonyDimension,
        level: ActionLevel,
        value: f32,
        threshold: &DimensionThreshold,
    ) -> String {
        let direction = if threshold.high_is_bad { "high" } else { "low" };
        format!(
            "{} {} ({:.2} {} threshold {:.2}) → {}",
            dim.as_str(),
            direction,
            value,
            if threshold.high_is_bad { ">=" } else { "<=" },
            match level {
                ActionLevel::Intervene => threshold.intervene_threshold,
                ActionLevel::Correct => threshold.correct_threshold,
                ActionLevel::Advise => threshold.advise_threshold,
                ActionLevel::Observe => threshold.advise_threshold,
            },
            level,
        )
    }

    /// Record an action in history and stats.
    fn record_action(&mut self, action: &HomeostaticAction) {
        self.stats.total_actions += 1;
        self.stats.actions_per_level[action.level as usize] += 1;
        *self
            .stats
            .actions_per_type
            .entry(action.action.as_str().to_string())
            .or_insert(0) += 1;

        if self.history.len() >= self.config.max_history {
            self.history.pop_front();
        }
        self.history.push_back(action.clone());
    }

    /// Get the action history (newest first, up to `limit`).
    #[must_use]
    pub fn history(&self, limit: usize) -> Vec<&HomeostaticAction> {
        self.history.iter().rev().take(limit).collect()
    }

    /// Total cycles run.
    #[must_use]
    pub const fn cycles(&self) -> u64 {
        self.stats.cycles
    }

    /// Total actions taken.
    #[must_use]
    pub const fn total_actions(&self) -> u64 {
        self.stats.total_actions
    }

    /// Actions at a specific level.
    #[must_use]
    pub const fn actions_at_level(&self, level: ActionLevel) -> u64 {
        self.stats.actions_per_level[level as usize]
    }

    /// Get loop statistics.
    #[must_use]
    pub const fn stats(&self) -> &LoopStats {
        &self.stats
    }

    /// Get a JSON summary.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "cycles": self.stats.cycles,
            "total_actions": self.stats.total_actions,
            "actions_per_level": {
                "observe": self.stats.actions_per_level[0],
                "advise": self.stats.actions_per_level[1],
                "correct": self.stats.actions_per_level[2],
                "intervene": self.stats.actions_per_level[3],
            },
            "actions_per_type": self.stats.actions_per_type,
            "last_cycle": self.stats.last_cycle,
            "history_len": self.history.len(),
            "execute_actions": self.config.execute_actions,
        })
    }

    /// Clear history and stats.
    pub fn clear(&mut self) {
        self.history.clear();
        self.stats = LoopStats::default();
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::anomaly::AnomalyConfig;

    fn make_hv(
        cpu: f32,
        mem: f32,
        swap: f32,
        disk: f32,
        health: f32,
        battery: f32,
        temp: Option<f32>,
    ) -> HarmonyVector {
        let _ = health; // health is computed, not a field
        HarmonyVector {
            cpu_load: cpu,
            memory_pressure: mem,
            swap_usage: swap,
            thermal_state: crate::ThermalState::Normal,
            temperature_c: temp,
            battery_state: crate::BatteryState::Discharging,
            battery_percent: battery,
            disk_io_rate: disk,
            active: true,
            guna: crate::GunaTag::Sattvic,
            timestamp: chrono::Utc::now(),
        }
    }

    #[test]
    fn action_level_as_str() {
        assert_eq!(ActionLevel::Observe.as_str(), "observe");
        assert_eq!(ActionLevel::Advise.as_str(), "advise");
        assert_eq!(ActionLevel::Correct.as_str(), "correct");
        assert_eq!(ActionLevel::Intervene.as_str(), "intervene");
    }

    #[test]
    fn action_level_is_active() {
        assert!(!ActionLevel::Observe.is_active());
        assert!(!ActionLevel::Advise.is_active());
        assert!(ActionLevel::Correct.is_active());
        assert!(ActionLevel::Intervene.is_active());
    }

    #[test]
    fn action_type_as_str() {
        assert_eq!(ActionType::None.as_str(), "none");
        assert_eq!(ActionType::ShedLoad.as_str(), "shed_load");
        assert_eq!(ActionType::ForceTheta.as_str(), "force_theta");
    }

    #[test]
    fn threshold_high_is_bad_evaluate() {
        let t = DimensionThreshold::high_is_bad(HarmonyDimension::CpuLoad, 0.7, 0.85, 0.95);
        assert_eq!(t.evaluate(0.5), ActionLevel::Observe);
        assert_eq!(t.evaluate(0.7), ActionLevel::Advise);
        assert_eq!(t.evaluate(0.85), ActionLevel::Correct);
        assert_eq!(t.evaluate(0.95), ActionLevel::Intervene);
    }

    #[test]
    fn threshold_low_is_bad_evaluate() {
        let t = DimensionThreshold::low_is_bad(HarmonyDimension::BatteryPercent, 0.3, 0.15, 0.05);
        assert_eq!(t.evaluate(0.8), ActionLevel::Observe);
        assert_eq!(t.evaluate(0.3), ActionLevel::Advise);
        assert_eq!(t.evaluate(0.15), ActionLevel::Correct);
        assert_eq!(t.evaluate(0.05), ActionLevel::Intervene);
    }

    #[test]
    fn default_thresholds_cover_all_dimensions() {
        let thresholds = default_thresholds();
        assert_eq!(thresholds.len(), 7);
        for dim in HarmonyDimension::ALL {
            assert!(
                thresholds.iter().any(|t| t.dimension == dim),
                "Missing threshold for {dim:?}"
            );
        }
    }

    #[test]
    fn loop_no_action_on_healthy_state() {
        let mut loop_ = HomeostaticLoop::default();
        let hv = make_hv(0.3, 0.3, 0.05, 0.2, 0.9, 0.8, Some(45.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        let actions = loop_.sample_cycle(&hv, &detector);
        assert!(actions.is_empty());
        assert_eq!(loop_.cycles(), 1);
    }

    #[test]
    fn loop_advise_on_high_cpu() {
        let mut loop_ = HomeostaticLoop::default();
        let hv = make_hv(0.75, 0.3, 0.05, 0.2, 0.9, 0.8, Some(45.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        let actions = loop_.sample_cycle(&hv, &detector);
        assert!(actions.iter().any(|a| a.dimension == HarmonyDimension::CpuLoad && a.level == ActionLevel::Advise));
    }

    #[test]
    fn loop_correct_on_high_memory() {
        let mut loop_ = HomeostaticLoop::default();
        let hv = make_hv(0.3, 0.88, 0.05, 0.2, 0.9, 0.8, Some(45.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        let actions = loop_.sample_cycle(&hv, &detector);
        assert!(
            actions
                .iter()
                .any(|a| a.dimension == HarmonyDimension::MemoryPressure
                    && a.level == ActionLevel::Correct)
        );
    }

    #[test]
    fn loop_intervene_on_critical_battery() {
        let mut loop_ = HomeostaticLoop::default();
        let hv = make_hv(0.3, 0.3, 0.05, 0.2, 0.9, 0.03, Some(45.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        let actions = loop_.sample_cycle(&hv, &detector);
        assert!(
            actions
                .iter()
                .any(|a| a.dimension == HarmonyDimension::BatteryPercent
                    && a.level == ActionLevel::Intervene)
        );
    }

    #[test]
    fn loop_intervene_on_high_temp() {
        let mut loop_ = HomeostaticLoop::default();
        let hv = make_hv(0.3, 0.3, 0.05, 0.2, 0.9, 0.8, Some(92.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        let actions = loop_.sample_cycle(&hv, &detector);
        assert!(
            actions
                .iter()
                .any(|a| a.dimension == HarmonyDimension::Temperature
                    && a.level == ActionLevel::Intervene)
        );
    }

    #[test]
    fn loop_actions_recorded_in_history() {
        let mut loop_ = HomeostaticLoop::default();
        let hv = make_hv(0.9, 0.9, 0.6, 0.2, 0.3, 0.1, Some(85.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        let actions = loop_.sample_cycle(&hv, &detector);
        assert!(!actions.is_empty());

        let history = loop_.history(10);
        assert!(!history.is_empty());
    }

    #[test]
    fn loop_stats_tracked() {
        let mut loop_ = HomeostaticLoop::default();
        let hv = make_hv(0.75, 0.3, 0.05, 0.2, 0.9, 0.8, Some(45.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        loop_.sample_cycle(&hv, &detector);
        loop_.sample_cycle(&hv, &detector);

        assert_eq!(loop_.cycles(), 2);
        assert!(loop_.total_actions() >= 2);
        assert!(loop_.actions_at_level(ActionLevel::Advise) >= 2);
    }

    #[test]
    fn loop_dry_run_does_not_execute() {
        let config = HomeostaticConfig {
            execute_actions: false,
            ..Default::default()
        };
        let mut loop_ = HomeostaticLoop::new(config);
        let hv = make_hv(0.9, 0.3, 0.05, 0.2, 0.9, 0.8, Some(45.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        let actions = loop_.sample_cycle(&hv, &detector);
        assert!(actions.iter().all(|a| !a.executed));
    }

    #[test]
    fn loop_execute_actions_flag() {
        let mut loop_ = HomeostaticLoop::default();
        let hv = make_hv(0.9, 0.3, 0.05, 0.2, 0.9, 0.8, Some(45.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        let actions = loop_.sample_cycle(&hv, &detector);
        // Correct level should be executed
        assert!(actions.iter().any(|a| a.level.is_active() && a.executed));
    }

    #[test]
    fn loop_clear_resets() {
        let mut loop_ = HomeostaticLoop::default();
        let hv = make_hv(0.9, 0.3, 0.05, 0.2, 0.9, 0.8, Some(45.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        loop_.sample_cycle(&hv, &detector);
        assert!(loop_.total_actions() > 0);

        loop_.clear();
        assert_eq!(loop_.total_actions(), 0);
        assert_eq!(loop_.cycles(), 0);
    }

    #[test]
    fn loop_summary_json() {
        let mut loop_ = HomeostaticLoop::default();
        let hv = make_hv(0.75, 0.3, 0.05, 0.2, 0.9, 0.8, Some(45.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        loop_.sample_cycle(&hv, &detector);
        let summary = loop_.summary();
        assert_eq!(summary["cycles"], 1);
        assert!(summary["total_actions"].as_u64().unwrap() > 0);
    }

    #[test]
    fn action_to_json() {
        let action = HomeostaticAction {
            dimension: HarmonyDimension::CpuLoad,
            level: ActionLevel::Correct,
            action: ActionType::ShedLoad,
            current_value: 0.88,
            threshold: 0.85,
            description: "test".to_string(),
            executed: true,
        };
        let json = action.to_json();
        assert_eq!(json["dimension"], "cpu_load");
        assert_eq!(json["level"], "correct");
        assert_eq!(json["action"], "shed_load");
        assert_eq!(json["executed"], true);
    }

    #[test]
    fn multiple_dimensions_flagged() {
        let mut loop_ = HomeostaticLoop::default();
        let hv = make_hv(0.9, 0.9, 0.6, 0.9, 0.3, 0.1, Some(85.0));
        let detector = AnomalyDetector::new(AnomalyConfig::default());

        let actions = loop_.sample_cycle(&hv, &detector);
        // Multiple dimensions should be flagged
        assert!(actions.len() >= 3);
    }

    #[test]
    fn select_action_mapping() {
        let loop_ = HomeostaticLoop::default();
        assert_eq!(
            loop_.select_action(HarmonyDimension::CpuLoad, ActionLevel::Correct),
            ActionType::ShedLoad
        );
        assert_eq!(
            loop_.select_action(HarmonyDimension::CpuLoad, ActionLevel::Intervene),
            ActionType::ForceTheta
        );
        assert_eq!(
            loop_.select_action(HarmonyDimension::MemoryPressure, ActionLevel::Correct),
            ActionType::MemorySweep
        );
        assert_eq!(
            loop_.select_action(HarmonyDimension::MemoryPressure, ActionLevel::Intervene),
            ActionType::RefuseWrites
        );
        assert_eq!(
            loop_.select_action(HarmonyDimension::BatteryPercent, ActionLevel::Advise),
            ActionType::Recommend
        );
        assert_eq!(
            loop_.select_action(HarmonyDimension::Temperature, ActionLevel::Intervene),
            ActionType::ForceTheta
        );
    }
}
