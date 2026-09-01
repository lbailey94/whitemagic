//! Anomaly detection and Yin-Yang balance tracking for the Harmony Vector.
//!
//! **N20**: Statistical health monitoring via z-score sliding windows on
//! 7 harmony dimensions, plus action/reflection balance tracking.
//!
//! The [`AnomalyDetector`] computes rolling z-scores for each numeric
//! dimension of the [`HarmonyVector`]. When a dimension deviates
//! significantly from its recent baseline, an [`AnomalyAlert`] is
//! emitted. This feeds into the homeostatic loop (N19) and the
//! Gan Ying Bus (N16).
//!
//! The [`YinYangTracker`] classifies each tool dispatch as Yang
//! (create/write/delete/execute) or Yin (read/search/analyze/reflect)
//! and maintains a rolling balance ratio. Too much Yang signals
//! burnout risk; too much Yin signals stagnation.

#![forbid(unsafe_code)]

use std::collections::VecDeque;

use serde::{Deserialize, Serialize};

use crate::HarmonyVector;

// ── Harmony Dimension ─────────────────────────────────────────────────

/// Numeric dimensions of the Harmony Vector that can be monitored
/// for anomalies.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HarmonyDimension {
    /// CPU load fraction (0.0–1.0).
    CpuLoad,
    /// Memory pressure fraction (0.0–1.0).
    MemoryPressure,
    /// Swap usage fraction (0.0–1.0).
    SwapUsage,
    /// Disk I/O rate fraction (0.0–1.0).
    DiskIoRate,
    /// Composite health score (0.0–1.0).
    HealthScore,
    /// Battery charge fraction (0.0–1.0).
    BatteryPercent,
    /// CPU temperature in Celsius (if available).
    Temperature,
}

impl HarmonyDimension {
    /// All 7 dimensions in canonical order.
    pub const ALL: [Self; 7] = [
        Self::CpuLoad,
        Self::MemoryPressure,
        Self::SwapUsage,
        Self::DiskIoRate,
        Self::HealthScore,
        Self::BatteryPercent,
        Self::Temperature,
    ];

    /// Extract the numeric value from a HarmonyVector for this dimension.
    #[must_use]
    pub fn extract(&self, hv: &HarmonyVector) -> Option<f32> {
        match self {
            Self::CpuLoad => Some(hv.cpu_load),
            Self::MemoryPressure => Some(hv.memory_pressure),
            Self::SwapUsage => Some(hv.swap_usage),
            Self::DiskIoRate => Some(hv.disk_io_rate),
            Self::HealthScore => Some(hv.health_score()),
            Self::BatteryPercent => Some(hv.battery_percent),
            Self::Temperature => hv.temperature_c,
        }
    }

    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::CpuLoad => "cpu_load",
            Self::MemoryPressure => "memory_pressure",
            Self::SwapUsage => "swap_usage",
            Self::DiskIoRate => "disk_io_rate",
            Self::HealthScore => "health_score",
            Self::BatteryPercent => "battery_percent",
            Self::Temperature => "temperature",
        }
    }

    /// Whether an increase in this dimension is "bad" (i.e., high values
    /// indicate problems). For battery_percent and health_score, low
    /// values are anomalous, so the direction is inverted.
    #[must_use]
    const fn is_inverted(self) -> bool {
        matches!(self, Self::BatteryPercent | Self::HealthScore)
    }
}

// ── Anomaly Alert ─────────────────────────────────────────────────────

/// Severity of an anomaly.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AnomalySeverity {
    /// |z| > 2.0 — mild deviation, worth logging.
    Warning,
    /// |z| > 3.0 — significant deviation, action may be needed.
    Critical,
}

impl AnomalySeverity {
    /// Classify from absolute z-score.
    #[must_use]
    pub fn from_z_score(z: f32) -> Option<Self> {
        let z = z.abs();
        if z > 3.0 {
            Some(Self::Critical)
        } else if z > 2.0 {
            Some(Self::Warning)
        } else {
            None
        }
    }

    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Warning => "warning",
            Self::Critical => "critical",
        }
    }
}

/// Direction of the anomaly relative to the baseline.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AnomalyDirection {
    /// Value is above the rolling mean.
    Above,
    /// Value is below the rolling mean.
    Below,
}

impl AnomalyDirection {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Above => "above",
            Self::Below => "below",
        }
    }

    fn from_z_score(z: f32) -> Self {
        if z > 0.0 { Self::Above } else { Self::Below }
    }
}

/// Whether this anomaly is harmful (i.e., the deviation is in the
/// "bad" direction for this dimension).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AnomalyImpact {
    /// The deviation is in the harmful direction.
    Harmful,
    /// The deviation is in the beneficial direction.
    Beneficial,
}

impl AnomalyImpact {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Harmful => "harmful",
            Self::Beneficial => "beneficial",
        }
    }
}

/// An anomaly alert for a single harmony dimension.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyAlert {
    /// Which dimension is anomalous.
    pub dimension: HarmonyDimension,
    /// The z-score of the current value.
    pub z_score: f32,
    /// Whether the value is above or below the baseline.
    pub direction: AnomalyDirection,
    /// Severity level (Warning or Critical).
    pub severity: AnomalySeverity,
    /// Whether the deviation is harmful or beneficial.
    pub impact: AnomalyImpact,
    /// The current value.
    pub current_value: f32,
    /// The rolling mean at the time of detection.
    pub baseline_mean: f32,
    /// The rolling std dev at the time of detection.
    pub baseline_std: f32,
}

impl AnomalyAlert {
    /// Convert to JSON for MCP tool responses.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "dimension": self.dimension.as_str(),
            "z_score": self.z_score,
            "direction": self.direction.as_str(),
            "severity": self.severity.as_str(),
            "impact": self.impact.as_str(),
            "current_value": self.current_value,
            "baseline_mean": self.baseline_mean,
            "baseline_std": self.baseline_std,
        })
    }
}

// ── Anomaly Detector ──────────────────────────────────────────────────

/// Configuration for [`AnomalyDetector`].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyConfig {
    /// Sliding window size (number of samples to retain per dimension).
    pub window_size: usize,
    /// Warning threshold (|z| > this → Warning).
    pub warning_threshold: f32,
    /// Critical threshold (|z| > this → Critical).
    pub critical_threshold: f32,
    /// Minimum samples before z-score is computed (avoid noise from
    /// small windows).
    pub min_samples: usize,
    /// Epsilon for std dev to avoid division by zero.
    pub std_epsilon: f32,
}

impl Default for AnomalyConfig {
    fn default() -> Self {
        Self {
            window_size: 100,
            warning_threshold: 2.0,
            critical_threshold: 3.0,
            min_samples: 10,
            std_epsilon: 1e-6,
        }
    }
}

/// Sliding window statistics for a single dimension.
#[derive(Debug, Clone)]
struct DimensionWindow {
    values: VecDeque<f32>,
    /// Cached sum for O(1) mean computation.
    sum: f64,
    /// Cached sum of squares for O(1) std dev computation.
    sum_sq: f64,
}

impl DimensionWindow {
    fn new(capacity: usize) -> Self {
        Self {
            values: VecDeque::with_capacity(capacity),
            sum: 0.0,
            sum_sq: 0.0,
        }
    }

    fn push(&mut self, value: f32, capacity: usize) {
        self.sum += f64::from(value);
        self.sum_sq = f64::from(value).mul_add(f64::from(value), self.sum_sq);
        self.values.push_back(value);
        if self.values.len() > capacity {
            if let Some(old) = self.values.pop_front() {
                self.sum -= f64::from(old);
                self.sum_sq = f64::from(old).mul_add(-f64::from(old), self.sum_sq);
            }
        }
    }

    fn len(&self) -> usize {
        self.values.len()
    }

    fn mean(&self) -> f32 {
        if self.values.is_empty() {
            0.0
        } else {
            (self.sum / self.values.len() as f64) as f32
        }
    }

    #[allow(clippy::suboptimal_flops)]
    fn std_dev(&self, epsilon: f32) -> f32 {
        let n = self.values.len() as f64;
        if n < 2.0 {
            return epsilon;
        }
        let mean = self.sum / n;
        let variance = self.sum_sq / n - mean * mean;
        let variance = variance.max(0.0);
        (variance.sqrt() as f32).max(epsilon)
    }
}

/// Clamp a metric value to its valid range for the given dimension.
///
/// This prevents poisoned metrics (e.g., negative CPU load, f32::MAX temperature)
/// from skewing the rolling statistics and generating false anomaly alerts.
#[must_use]
const fn clamp_metric(dim: HarmonyDimension, value: f32) -> f32 {
    if value.is_nan() || value.is_infinite() {
        return match dim {
            HarmonyDimension::Temperature => 0.0,
            _ => 0.0,
        };
    }
    match dim {
        HarmonyDimension::CpuLoad
        | HarmonyDimension::MemoryPressure
        | HarmonyDimension::SwapUsage
        | HarmonyDimension::DiskIoRate
        | HarmonyDimension::HealthScore
        | HarmonyDimension::BatteryPercent => value.clamp(0.0, 1.0),
        HarmonyDimension::Temperature => value.clamp(-40.0, 200.0),
    }
}

/// Anomaly detector using z-score sliding windows on harmony dimensions.
///
/// Maintains a rolling window of [`HarmonyVector`] samples and computes
/// z-scores for each of the 7 numeric dimensions. When a dimension's
/// z-score exceeds the warning or critical threshold, an [`AnomalyAlert`]
/// is generated.
///
/// # Example
/// ```no_run
/// use wm_substrate::{SubstrateMonitor, anomaly::{AnomalyDetector, AnomalySeverity}};
///
/// let monitor = SubstrateMonitor::default();
/// let mut detector = AnomalyDetector::default();
///
/// let hv = monitor.sample();
/// let alerts = detector.check(&hv);
/// for alert in &alerts {
///     if alert.severity == AnomalySeverity::Critical {
///         // Take corrective action
///     }
/// }
/// ```
pub struct AnomalyDetector {
    windows: [DimensionWindow; 7],
    config: AnomalyConfig,
    /// Total number of alerts detected since creation.
    alert_count: u64,
    /// Number of samples processed.
    sample_count: u64,
}

impl Default for AnomalyDetector {
    fn default() -> Self {
        Self::new(AnomalyConfig::default())
    }
}

impl AnomalyDetector {
    /// Create a new anomaly detector with the given configuration.
    #[must_use]
    pub fn new(config: AnomalyConfig) -> Self {
        let cap = config.window_size;
        Self {
            windows: [
                DimensionWindow::new(cap),
                DimensionWindow::new(cap),
                DimensionWindow::new(cap),
                DimensionWindow::new(cap),
                DimensionWindow::new(cap),
                DimensionWindow::new(cap),
                DimensionWindow::new(cap),
            ],
            config,
            alert_count: 0,
            sample_count: 0,
        }
    }

    /// Process a new HarmonyVector sample and return any anomaly alerts.
    ///
    /// The sample is added to the rolling window, then z-scores are
    /// computed for each dimension. Dimensions with |z| > warning_threshold
    /// generate alerts.
    ///
    /// Metric values are clamped to valid ranges before being added to
    /// the window, preventing poisoned metrics (e.g., negative CPU, f32::MAX)
    /// from skewing z-scores.
    ///
    /// Note: the current sample is included in the window before computing
    /// the z-score, which slightly dampens the score. This is intentional —
    /// it prevents a single spike from generating a false positive when
    /// the window is large.
    pub fn check(&mut self, hv: &HarmonyVector) -> Vec<AnomalyAlert> {
        let mut alerts = Vec::new();

        for (i, dim) in HarmonyDimension::ALL.iter().enumerate() {
            if let Some(raw_value) = dim.extract(hv) {
                let value = clamp_metric(*dim, raw_value);
                self.windows[i].push(value, self.config.window_size);

                if self.windows[i].len() >= self.config.min_samples {
                    let mean = self.windows[i].mean();
                    let std = self.windows[i].std_dev(self.config.std_epsilon);
                    let z = (value - mean) / std;

                    if let Some(severity) = AnomalySeverity::from_z_score(z) {
                        let direction = AnomalyDirection::from_z_score(z);
                        let impact = self.classify_impact(*dim, direction);
                        alerts.push(AnomalyAlert {
                            dimension: *dim,
                            z_score: z,
                            direction,
                            severity,
                            impact,
                            current_value: value,
                            baseline_mean: mean,
                            baseline_std: std,
                        });
                    }
                }
            }
        }

        self.sample_count += 1;
        self.alert_count += alerts.len() as u64;
        alerts
    }

    /// Classify whether an anomaly in the given direction is harmful or
    /// beneficial for this dimension.
    const fn classify_impact(
        &self,
        dim: HarmonyDimension,
        direction: AnomalyDirection,
    ) -> AnomalyImpact {
        // For inverted dimensions (battery, health), low values are bad.
        // So "Below" is harmful, "Above" is beneficial.
        if dim.is_inverted() {
            match direction {
                AnomalyDirection::Below => AnomalyImpact::Harmful,
                AnomalyDirection::Above => AnomalyImpact::Beneficial,
            }
        } else {
            // For normal dimensions (cpu, memory, etc.), high values are bad.
            match direction {
                AnomalyDirection::Above => AnomalyImpact::Harmful,
                AnomalyDirection::Below => AnomalyImpact::Beneficial,
            }
        }
    }

    /// Get the current rolling statistics for a dimension.
    ///
    /// Returns `(mean, std_dev, sample_count)` for the dimension's window.
    #[must_use]
    pub fn stats(&self, dim: HarmonyDimension) -> (f32, f32, usize) {
        let idx = HarmonyDimension::ALL.iter().position(|d| *d == dim);
        match idx {
            Some(i) => {
                let w = &self.windows[i];
                (w.mean(), w.std_dev(self.config.std_epsilon), w.len())
            }
            None => (0.0, 0.0, 0),
        }
    }

    /// Total alerts detected since creation.
    #[must_use]
    pub const fn alert_count(&self) -> u64 {
        self.alert_count
    }

    /// Total samples processed.
    #[must_use]
    pub const fn sample_count(&self) -> u64 {
        self.sample_count
    }

    /// Number of samples in the window for a specific dimension.
    #[must_use]
    pub fn window_len(&self, dim: HarmonyDimension) -> usize {
        HarmonyDimension::ALL
            .iter()
            .position(|d| *d == dim)
            .map_or(0, |i| self.windows[i].len())
    }

    /// Get a JSON summary of the detector's state.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        let dims: Vec<serde_json::Value> = HarmonyDimension::ALL
            .iter()
            .map(|dim| {
                let (mean, std, n) = self.stats(*dim);
                serde_json::json!({
                    "dimension": dim.as_str(),
                    "mean": mean,
                    "std_dev": std,
                    "samples": n,
                })
            })
            .collect();

        serde_json::json!({
            "dimensions": dims,
            "total_alerts": self.alert_count,
            "total_samples": self.sample_count,
            "window_size": self.config.window_size,
            "warning_threshold": self.config.warning_threshold,
            "critical_threshold": self.config.critical_threshold,
        })
    }
}

// ── Yin-Yang Tracker ──────────────────────────────────────────────────

/// Classification of a dispatch as Yang (active/creative) or Yin
/// (passive/receptive).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DispatchNature {
    /// Yang — create, write, delete, execute, build, act.
    Yang,
    /// Yin — read, search, analyze, reflect, observe, query.
    Yin,
}

impl DispatchNature {
    /// Classify a tool name as Yang or Yin based on its action type.
    ///
    /// Yang verbs: create, write, delete, associate, consolidate, decay,
    /// update, tag, flush, end, distribute, trigger, dispatch, execute,
    /// build, act, start, register, import, export.
    ///
    /// Yin verbs: read, list, search, query, scan, status, report, list,
    /// history, analyze, reflect, observe, check, count, tags, stats,
    /// health, config, show, get, surface, detect.
    #[must_use]
    pub fn from_tool_name(name: &str) -> Self {
        // Check for Yang (active) keywords first — they're more specific
        let yang_keywords = [
            "create",
            "write",
            "delete",
            "associate",
            "consolidate",
            "decay",
            "update",
            "tag",
            "flush",
            "end",
            "distribute",
            "trigger",
            "dispatch",
            "execute",
            "build",
            "act",
            "start",
            "register",
            "import",
            "export",
            "retire",
            "clear",
            "remove",
            "set",
            "put",
            "post",
            "send",
            "emit",
            "activate",
            "shutdown",
            "stop",
            "restart",
        ];

        let yin_keywords = [
            "read",
            "list",
            "search",
            "query",
            "scan",
            "status",
            "report",
            "history",
            "analyze",
            "reflect",
            "observe",
            "check",
            "count",
            "tags",
            "stats",
            "health",
            "config",
            "show",
            "get",
            "surface",
            "detect",
            "gnosis",
            "list",
            "effectiveness",
            "heartbeat",
            "recall",
            "checkpoint",
            "help",
            "doctor",
            "polyglot",
            "brain",
        ];

        let lower = name.to_lowercase();

        // Check if any yang keyword is a substring
        for kw in &yang_keywords {
            if lower.contains(kw) {
                return Self::Yang;
            }
        }

        // Check if any yin keyword is a substring
        for kw in &yin_keywords {
            if lower.contains(kw) {
                return Self::Yin;
            }
        }

        // Default: if it contains a dot, check the action part
        if let Some(action) = lower.rsplit('.').next() {
            for kw in &yang_keywords {
                if action.contains(kw) {
                    return Self::Yang;
                }
            }
            for kw in &yin_keywords {
                if action.contains(kw) {
                    return Self::Yin;
                }
            }
        }

        // Default to Yin (safe — reading/observing)
        Self::Yin
    }

    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Yang => "yang",
            Self::Yin => "yin",
        }
    }
}

/// Balance state of the Yin-Yang ratio.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BalanceState {
    /// Yang ratio > 0.7 — too much action, burnout risk.
    YangExcess,
    /// Yin ratio < 0.3 — too much passivity, stagnation risk.
    YinExcess,
    /// Balanced — ratio between 0.3 and 0.7.
    Balanced,
}

impl BalanceState {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::YangExcess => "yang_excess",
            Self::YinExcess => "yin_excess",
            Self::Balanced => "balanced",
        }
    }

    /// Classify from Yang ratio.
    fn from_ratio(yang_ratio: f32) -> Self {
        if yang_ratio > 0.7 {
            Self::YangExcess
        } else if yang_ratio < 0.3 {
            Self::YinExcess
        } else {
            Self::Balanced
        }
    }

    /// Recommended action for this balance state.
    #[must_use]
    pub const fn recommendation(self) -> &'static str {
        match self {
            Self::YangExcess => {
                "High action ratio — suggest consolidation, dream cycle, or reflection pause"
            }
            Self::YinExcess => {
                "Low action ratio — suggest exploration, curiosity drive boost, or active task"
            }
            Self::Balanced => "Balance is healthy — no action needed",
        }
    }
}

/// Yin-Yang balance tracker.
///
/// Maintains a rolling window of dispatch classifications (Yang/Yin)
/// and computes the balance ratio. When the ratio drifts outside the
/// ideal range (0.3–0.7), it flags the imbalance.
///
/// # Example
/// ```no_run
/// use wm_substrate::anomaly::{YinYangTracker, BalanceState};
///
/// let mut tracker = YinYangTracker::default();
/// tracker.record("memory.create"); // Yang
/// tracker.record("memory.read");   // Yin
/// let balance = tracker.balance();
/// assert_eq!(balance.state, BalanceState::Balanced);
/// ```
pub struct YinYangTracker {
    /// Rolling window of dispatch natures.
    window: VecDeque<DispatchNature>,
    /// Window capacity.
    capacity: usize,
    /// Yang count in current window.
    yang_count: usize,
    /// Yin count in current window.
    yin_count: usize,
    /// Total Yang dispatches since creation.
    total_yang: u64,
    /// Total Yin dispatches since creation.
    total_yin: u64,
}

impl Default for YinYangTracker {
    fn default() -> Self {
        Self::new(100)
    }
}

impl YinYangTracker {
    /// Create a new tracker with the given window size.
    #[must_use]
    pub fn new(window_size: usize) -> Self {
        Self {
            window: VecDeque::with_capacity(window_size),
            capacity: window_size,
            yang_count: 0,
            yin_count: 0,
            total_yang: 0,
            total_yin: 0,
        }
    }

    /// Record a tool dispatch by name (auto-classified as Yang or Yin).
    pub fn record(&mut self, tool_name: &str) {
        let nature = DispatchNature::from_tool_name(tool_name);
        self.record_nature(nature);
    }

    /// Record a dispatch with a pre-determined nature.
    pub fn record_nature(&mut self, nature: DispatchNature) {
        match nature {
            DispatchNature::Yang => {
                self.yang_count += 1;
                self.total_yang += 1;
            }
            DispatchNature::Yin => {
                self.yin_count += 1;
                self.total_yin += 1;
            }
        }
        self.window.push_back(nature);
        if self.window.len() > self.capacity {
            if let Some(old) = self.window.pop_front() {
                match old {
                    DispatchNature::Yang => self.yang_count -= 1,
                    DispatchNature::Yin => self.yin_count -= 1,
                }
            }
        }
    }

    /// Current Yang ratio (0.0 = all Yin, 1.0 = all Yang).
    #[must_use]
    pub fn yang_ratio(&self) -> f32 {
        let total = self.yang_count + self.yin_count;
        if total == 0 {
            0.5 // Neutral default
        } else {
            self.yang_count as f32 / total as f32
        }
    }

    /// Current Yin ratio (1.0 - yang_ratio).
    #[must_use]
    pub fn yin_ratio(&self) -> f32 {
        1.0 - self.yang_ratio()
    }

    /// Current balance state.
    #[must_use]
    pub fn state(&self) -> BalanceState {
        BalanceState::from_ratio(self.yang_ratio())
    }

    /// Get a balance snapshot.
    #[must_use]
    pub fn balance(&self) -> YinYangBalance {
        YinYangBalance {
            yang_ratio: self.yang_ratio(),
            yin_ratio: self.yin_ratio(),
            yang_count: self.yang_count,
            yin_count: self.yin_count,
            state: self.state(),
            total_yang: self.total_yang,
            total_yin: self.total_yin,
        }
    }

    /// Number of dispatches in the current window.
    #[must_use]
    pub fn window_len(&self) -> usize {
        self.window.len()
    }

    /// Total dispatches (Yang + Yin) since creation.
    #[must_use]
    pub const fn total_dispatches(&self) -> u64 {
        self.total_yang + self.total_yin
    }

    /// Get a JSON summary.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        let b = self.balance();
        serde_json::json!({
            "yang_ratio": b.yang_ratio,
            "yin_ratio": b.yin_ratio,
            "yang_count": b.yang_count,
            "yin_count": b.yin_count,
            "state": b.state.as_str(),
            "recommendation": b.state.recommendation(),
            "total_yang": b.total_yang,
            "total_yin": b.total_yin,
            "window_size": self.capacity,
        })
    }
}

/// A snapshot of the Yin-Yang balance.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct YinYangBalance {
    /// Current Yang ratio (0.0–1.0).
    pub yang_ratio: f32,
    /// Current Yin ratio (0.0–1.0).
    pub yin_ratio: f32,
    /// Yang count in current window.
    pub yang_count: usize,
    /// Yin count in current window.
    pub yin_count: usize,
    /// Current balance state.
    pub state: BalanceState,
    /// Total Yang dispatches since creation.
    pub total_yang: u64,
    /// Total Yin dispatches since creation.
    pub total_yin: u64,
}

impl YinYangBalance {
    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "yang_ratio": self.yang_ratio,
            "yin_ratio": self.yin_ratio,
            "yang_count": self.yang_count,
            "yin_count": self.yin_count,
            "state": self.state.as_str(),
            "recommendation": self.state.recommendation(),
            "total_yang": self.total_yang,
            "total_yin": self.total_yin,
        })
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{BatteryState, GunaTag, HarmonyVector, ThermalState};
    use chrono::Utc;

    fn make_hv(
        cpu: f32,
        mem: f32,
        swap: f32,
        disk: f32,
        battery: f32,
        temp: Option<f32>,
    ) -> HarmonyVector {
        HarmonyVector {
            cpu_load: cpu,
            memory_pressure: mem,
            swap_usage: swap,
            thermal_state: ThermalState::from_celsius(temp.unwrap_or(45.0)),
            temperature_c: temp,
            battery_state: BatteryState::Full,
            battery_percent: battery,
            disk_io_rate: disk,
            active: cpu > 0.15,
            guna: GunaTag::Sattvic,
            timestamp: Utc::now(),
        }
    }

    // ── HarmonyDimension tests ──────────────────────────────────────

    #[test]
    fn dimension_extract_cpu_load() {
        let hv = make_hv(0.5, 0.2, 0.1, 0.0, 1.0, Some(45.0));
        assert_eq!(HarmonyDimension::CpuLoad.extract(&hv), Some(0.5));
    }

    #[test]
    fn dimension_extract_memory_pressure() {
        let hv = make_hv(0.5, 0.3, 0.1, 0.0, 1.0, Some(45.0));
        assert_eq!(HarmonyDimension::MemoryPressure.extract(&hv), Some(0.3));
    }

    #[test]
    fn dimension_extract_swap_usage() {
        let hv = make_hv(0.5, 0.2, 0.4, 0.0, 1.0, Some(45.0));
        assert_eq!(HarmonyDimension::SwapUsage.extract(&hv), Some(0.4));
    }

    #[test]
    fn dimension_extract_disk_io() {
        let hv = make_hv(0.5, 0.2, 0.1, 0.6, 1.0, Some(45.0));
        assert_eq!(HarmonyDimension::DiskIoRate.extract(&hv), Some(0.6));
    }

    #[test]
    fn dimension_extract_health_score() {
        let hv = make_hv(0.1, 0.1, 0.0, 0.0, 1.0, Some(45.0));
        let health = HarmonyDimension::HealthScore.extract(&hv);
        assert!(health.is_some());
        assert!(health.unwrap() > 0.8);
    }

    #[test]
    fn dimension_extract_battery() {
        let hv = make_hv(0.5, 0.2, 0.1, 0.0, 0.7, Some(45.0));
        assert_eq!(HarmonyDimension::BatteryPercent.extract(&hv), Some(0.7));
    }

    #[test]
    fn dimension_extract_temperature() {
        let hv = make_hv(0.5, 0.2, 0.1, 0.0, 1.0, Some(72.0));
        assert_eq!(HarmonyDimension::Temperature.extract(&hv), Some(72.0));
    }

    #[test]
    fn dimension_extract_temperature_none() {
        let hv = make_hv(0.5, 0.2, 0.1, 0.0, 1.0, None);
        assert_eq!(HarmonyDimension::Temperature.extract(&hv), None);
    }

    #[test]
    fn dimension_all_has_seven() {
        assert_eq!(HarmonyDimension::ALL.len(), 7);
    }

    #[test]
    fn dimension_as_str() {
        assert_eq!(HarmonyDimension::CpuLoad.as_str(), "cpu_load");
        assert_eq!(HarmonyDimension::MemoryPressure.as_str(), "memory_pressure");
        assert_eq!(HarmonyDimension::SwapUsage.as_str(), "swap_usage");
        assert_eq!(HarmonyDimension::DiskIoRate.as_str(), "disk_io_rate");
        assert_eq!(HarmonyDimension::HealthScore.as_str(), "health_score");
        assert_eq!(HarmonyDimension::BatteryPercent.as_str(), "battery_percent");
        assert_eq!(HarmonyDimension::Temperature.as_str(), "temperature");
    }

    #[test]
    fn dimension_inverted_flags() {
        assert!(HarmonyDimension::BatteryPercent.is_inverted());
        assert!(HarmonyDimension::HealthScore.is_inverted());
        assert!(!HarmonyDimension::CpuLoad.is_inverted());
        assert!(!HarmonyDimension::MemoryPressure.is_inverted());
        assert!(!HarmonyDimension::Temperature.is_inverted());
    }

    // ── AnomalySeverity tests ───────────────────────────────────────

    #[test]
    fn severity_from_z_score() {
        assert_eq!(AnomalySeverity::from_z_score(1.5), None);
        assert_eq!(
            AnomalySeverity::from_z_score(2.5),
            Some(AnomalySeverity::Warning)
        );
        assert_eq!(
            AnomalySeverity::from_z_score(-2.5),
            Some(AnomalySeverity::Warning)
        );
        assert_eq!(
            AnomalySeverity::from_z_score(3.5),
            Some(AnomalySeverity::Critical)
        );
        assert_eq!(
            AnomalySeverity::from_z_score(-3.5),
            Some(AnomalySeverity::Critical)
        );
    }

    #[test]
    fn severity_as_str() {
        assert_eq!(AnomalySeverity::Warning.as_str(), "warning");
        assert_eq!(AnomalySeverity::Critical.as_str(), "critical");
    }

    // ── AnomalyDirection tests ──────────────────────────────────────

    #[test]
    fn direction_from_z_score() {
        assert_eq!(AnomalyDirection::from_z_score(2.5), AnomalyDirection::Above);
        assert_eq!(
            AnomalyDirection::from_z_score(-2.5),
            AnomalyDirection::Below
        );
    }

    // ── AnomalyDetector tests ───────────────────────────────────────

    #[test]
    fn anomaly_detector_no_alerts_with_few_samples() {
        let mut detector = AnomalyDetector::default();
        let hv = make_hv(0.5, 0.2, 0.1, 0.0, 1.0, Some(45.0));
        let alerts = detector.check(&hv);
        assert!(alerts.is_empty(), "Should not alert with < min_samples");
    }

    #[test]
    fn anomaly_detector_stable_no_alerts() {
        let mut detector = AnomalyDetector::default();
        // Feed 20 stable samples
        for _ in 0..20 {
            let hv = make_hv(0.3, 0.2, 0.1, 0.0, 1.0, Some(45.0));
            detector.check(&hv);
        }
        // 21st sample — same values, no anomaly
        let hv = make_hv(0.3, 0.2, 0.1, 0.0, 1.0, Some(45.0));
        let alerts = detector.check(&hv);
        assert!(alerts.is_empty(), "Stable values should not trigger alerts");
    }

    #[test]
    fn anomaly_detector_detects_spike() {
        let mut detector = AnomalyDetector::new(AnomalyConfig {
            min_samples: 5,
            ..Default::default()
        });
        // Feed 10 stable samples
        for _ in 0..10 {
            let hv = make_hv(0.2, 0.2, 0.1, 0.0, 1.0, Some(45.0));
            detector.check(&hv);
        }
        // Spike CPU to 0.95 — should trigger anomaly
        let hv = make_hv(0.95, 0.2, 0.1, 0.0, 1.0, Some(45.0));
        let alerts = detector.check(&hv);
        assert!(!alerts.is_empty(), "CPU spike should trigger an alert");
        let cpu_alert = alerts
            .iter()
            .find(|a| a.dimension == HarmonyDimension::CpuLoad);
        assert!(cpu_alert.is_some(), "Should have a CpuLoad alert");
        let alert = cpu_alert.unwrap();
        assert!(
            alert.z_score > 2.0,
            "Z-score should be > 2.0: {}",
            alert.z_score
        );
        assert_eq!(alert.direction, AnomalyDirection::Above);
        assert_eq!(alert.impact, AnomalyImpact::Harmful);
    }

    #[test]
    fn anomaly_detector_detects_drop() {
        let mut detector = AnomalyDetector::new(AnomalyConfig {
            min_samples: 5,
            ..Default::default()
        });
        // Feed 10 stable samples with full battery
        for _ in 0..10 {
            let hv = make_hv(0.2, 0.2, 0.1, 0.0, 1.0, Some(45.0));
            detector.check(&hv);
        }
        // Battery drops to 0.1 — should trigger anomaly (inverted: below is harmful)
        let hv = make_hv(0.2, 0.2, 0.1, 0.0, 0.1, Some(45.0));
        let alerts = detector.check(&hv);
        let bat_alert = alerts
            .iter()
            .find(|a| a.dimension == HarmonyDimension::BatteryPercent);
        assert!(bat_alert.is_some(), "Battery drop should trigger an alert");
        let alert = bat_alert.unwrap();
        assert_eq!(alert.direction, AnomalyDirection::Below);
        assert_eq!(alert.impact, AnomalyImpact::Harmful);
    }

    #[test]
    fn anomaly_detector_beneficial_anomaly() {
        let mut detector = AnomalyDetector::new(AnomalyConfig {
            min_samples: 5,
            ..Default::default()
        });
        // Feed 10 samples with high CPU
        for _ in 0..10 {
            let hv = make_hv(0.8, 0.2, 0.1, 0.0, 1.0, Some(45.0));
            detector.check(&hv);
        }
        // CPU drops to 0.1 — below baseline, beneficial for CPU dimension
        let hv = make_hv(0.1, 0.2, 0.1, 0.0, 1.0, Some(45.0));
        let alerts = detector.check(&hv);
        let cpu_alert = alerts
            .iter()
            .find(|a| a.dimension == HarmonyDimension::CpuLoad);
        assert!(cpu_alert.is_some(), "CPU drop should trigger an alert");
        let alert = cpu_alert.unwrap();
        assert_eq!(alert.direction, AnomalyDirection::Below);
        assert_eq!(alert.impact, AnomalyImpact::Beneficial);
    }

    #[test]
    fn anomaly_detector_stats() {
        let mut detector = AnomalyDetector::new(AnomalyConfig {
            min_samples: 3,
            ..Default::default()
        });
        for v in [0.2, 0.3, 0.4, 0.5] {
            let hv = make_hv(v, 0.2, 0.1, 0.0, 1.0, Some(45.0));
            detector.check(&hv);
        }
        let (mean, _std, n) = detector.stats(HarmonyDimension::CpuLoad);
        assert!((mean - 0.35).abs() < 0.01, "Mean should be ~0.35: {mean}");
        assert_eq!(n, 4);
    }

    #[test]
    fn anomaly_detector_alert_count() {
        let mut detector = AnomalyDetector::new(AnomalyConfig {
            min_samples: 5,
            ..Default::default()
        });
        for _ in 0..10 {
            let hv = make_hv(0.2, 0.2, 0.1, 0.0, 1.0, Some(45.0));
            detector.check(&hv);
        }
        assert_eq!(detector.alert_count(), 0);
        assert_eq!(detector.sample_count(), 10);

        // Spike
        let hv = make_hv(0.99, 0.2, 0.1, 0.0, 1.0, Some(45.0));
        let alerts = detector.check(&hv);
        assert!(detector.alert_count() >= 1);
        assert!(!alerts.is_empty());
    }

    #[test]
    fn anomaly_detector_window_len() {
        let mut detector = AnomalyDetector::new(AnomalyConfig {
            window_size: 5,
            min_samples: 2,
            ..Default::default()
        });
        for _ in 0..10 {
            let hv = make_hv(0.2, 0.2, 0.1, 0.0, 1.0, Some(45.0));
            detector.check(&hv);
        }
        // Window should be capped at 5
        assert_eq!(detector.window_len(HarmonyDimension::CpuLoad), 5);
    }

    #[test]
    fn anomaly_detector_summary() {
        let mut detector = AnomalyDetector::default();
        let hv = make_hv(0.3, 0.2, 0.1, 0.0, 1.0, Some(45.0));
        detector.check(&hv);
        let s = detector.summary();
        assert_eq!(s["total_samples"], 1);
        assert_eq!(s["total_alerts"], 0);
        assert!(s["dimensions"].is_array());
    }

    #[test]
    fn anomaly_alert_to_json() {
        let alert = AnomalyAlert {
            dimension: HarmonyDimension::CpuLoad,
            z_score: 3.5,
            direction: AnomalyDirection::Above,
            severity: AnomalySeverity::Critical,
            impact: AnomalyImpact::Harmful,
            current_value: 0.95,
            baseline_mean: 0.3,
            baseline_std: 0.15,
        };
        let json = alert.to_json();
        assert_eq!(json["dimension"], "cpu_load");
        assert_eq!(json["severity"], "critical");
        assert_eq!(json["direction"], "above");
        assert_eq!(json["impact"], "harmful");
    }

    // ── DispatchNature tests ────────────────────────────────────────

    #[test]
    fn dispatch_nature_yang_create() {
        assert_eq!(
            DispatchNature::from_tool_name("memory.create"),
            DispatchNature::Yang
        );
    }

    #[test]
    fn dispatch_nature_yang_delete() {
        assert_eq!(
            DispatchNature::from_tool_name("memory.delete"),
            DispatchNature::Yang
        );
    }

    #[test]
    fn dispatch_nature_yang_update() {
        assert_eq!(
            DispatchNature::from_tool_name("memory.update"),
            DispatchNature::Yang
        );
    }

    #[test]
    fn dispatch_nature_yang_consolidate() {
        assert_eq!(
            DispatchNature::from_tool_name("memory.consolidate"),
            DispatchNature::Yang
        );
    }

    #[test]
    fn dispatch_nature_yin_read() {
        assert_eq!(
            DispatchNature::from_tool_name("memory.read"),
            DispatchNature::Yin
        );
    }

    #[test]
    fn dispatch_nature_yin_search() {
        assert_eq!(
            DispatchNature::from_tool_name("memory.search"),
            DispatchNature::Yin
        );
    }

    #[test]
    fn dispatch_nature_yin_list() {
        assert_eq!(
            DispatchNature::from_tool_name("memory.list"),
            DispatchNature::Yin
        );
    }

    #[test]
    fn dispatch_nature_yin_status() {
        assert_eq!(
            DispatchNature::from_tool_name("citta.status"),
            DispatchNature::Yin
        );
    }

    #[test]
    fn dispatch_nature_yin_gnosis() {
        assert_eq!(
            DispatchNature::from_tool_name("gnosis"),
            DispatchNature::Yin
        );
    }

    #[test]
    fn dispatch_nature_default_yin() {
        assert_eq!(
            DispatchNature::from_tool_name("unknown.thing"),
            DispatchNature::Yin
        );
    }

    #[test]
    fn dispatch_nature_as_str() {
        assert_eq!(DispatchNature::Yang.as_str(), "yang");
        assert_eq!(DispatchNature::Yin.as_str(), "yin");
    }

    // ── BalanceState tests ──────────────────────────────────────────

    #[test]
    fn balance_state_from_ratio() {
        assert_eq!(BalanceState::from_ratio(0.8), BalanceState::YangExcess);
        assert_eq!(BalanceState::from_ratio(0.2), BalanceState::YinExcess);
        assert_eq!(BalanceState::from_ratio(0.5), BalanceState::Balanced);
        assert_eq!(BalanceState::from_ratio(0.3), BalanceState::Balanced);
        assert_eq!(BalanceState::from_ratio(0.7), BalanceState::Balanced);
    }

    #[test]
    fn balance_state_as_str() {
        assert_eq!(BalanceState::YangExcess.as_str(), "yang_excess");
        assert_eq!(BalanceState::YinExcess.as_str(), "yin_excess");
        assert_eq!(BalanceState::Balanced.as_str(), "balanced");
    }

    #[test]
    fn balance_state_recommendation() {
        assert!(!BalanceState::YangExcess.recommendation().is_empty());
        assert!(!BalanceState::YinExcess.recommendation().is_empty());
        assert!(!BalanceState::Balanced.recommendation().is_empty());
    }

    // ── YinYangTracker tests ────────────────────────────────────────

    #[test]
    fn yin_yang_empty_tracker() {
        let tracker = YinYangTracker::default();
        assert_eq!(tracker.yang_ratio(), 0.5); // Neutral default
        assert_eq!(tracker.state(), BalanceState::Balanced);
        assert_eq!(tracker.window_len(), 0);
        assert_eq!(tracker.total_dispatches(), 0);
    }

    #[test]
    fn yin_yang_balanced() {
        let mut tracker = YinYangTracker::default();
        tracker.record("memory.create"); // Yang
        tracker.record("memory.read"); // Yin
        assert_eq!(tracker.yang_ratio(), 0.5);
        assert_eq!(tracker.state(), BalanceState::Balanced);
    }

    #[test]
    fn yin_yang_yang_excess() {
        let mut tracker = YinYangTracker::default();
        tracker.record("memory.create"); // Yang
        tracker.record("memory.delete"); // Yang
        tracker.record("memory.update"); // Yang
        tracker.record("memory.read"); // Yin
        let balance = tracker.balance();
        assert_eq!(balance.state, BalanceState::YangExcess);
        assert!(balance.yang_ratio > 0.7);
    }

    #[test]
    fn yin_yang_yin_excess() {
        let mut tracker = YinYangTracker::default();
        tracker.record("memory.read"); // Yin
        tracker.record("memory.search"); // Yin
        tracker.record("memory.list"); // Yin
        tracker.record("gnosis"); // Yin
        let balance = tracker.balance();
        assert_eq!(balance.state, BalanceState::YinExcess);
        assert!(balance.yang_ratio < 0.3);
    }

    #[test]
    fn yin_yang_window_eviction() {
        let mut tracker = YinYangTracker::new(5);
        // Fill with Yang
        for _ in 0..5 {
            tracker.record("memory.create");
        }
        assert_eq!(tracker.window_len(), 5);
        assert_eq!(tracker.yang_ratio(), 1.0);

        // Add 3 Yin — should evict 3 Yang
        for _ in 0..3 {
            tracker.record("memory.read");
        }
        assert_eq!(tracker.window_len(), 5);
        let balance = tracker.balance();
        assert_eq!(balance.yang_count, 2);
        assert_eq!(balance.yin_count, 3);
    }

    #[test]
    fn yin_yang_total_counts() {
        let mut tracker = YinYangTracker::new(3);
        tracker.record("memory.create"); // Yang
        tracker.record("memory.read"); // Yin
        tracker.record("memory.delete"); // Yang
        tracker.record("memory.search"); // Yin (evicts first Yang from window)
        tracker.record("memory.update"); // Yang (evicts first Yin from window)

        let balance = tracker.balance();
        // Window has: read(Yin), delete(Yang), search(Yin), update(Yang) → wait, capacity 3
        // After 5 records with cap 3: window = [search(Yin), update(Yang)] — no, let me think...
        // Push create(Y) → [Y], push read(Yin) → [Y, Yin], push delete(Y) → [Y, Yin, Y],
        // push search(Yin) → evict Y → [Yin, Y, Yin], push update(Y) → evict Yin → [Y, Yin, Y]
        assert_eq!(balance.total_yang, 3);
        assert_eq!(balance.total_yin, 2);
    }

    #[test]
    fn yin_yang_record_nature_direct() {
        let mut tracker = YinYangTracker::default();
        tracker.record_nature(DispatchNature::Yang);
        tracker.record_nature(DispatchNature::Yin);
        assert_eq!(tracker.yang_ratio(), 0.5);
    }

    #[test]
    fn yin_yang_summary() {
        let mut tracker = YinYangTracker::default();
        tracker.record("memory.create");
        tracker.record("memory.read");
        let s = tracker.summary();
        assert_eq!(s["state"], "balanced");
        assert_eq!(s["total_yang"], 1);
        assert_eq!(s["total_yin"], 1);
    }

    #[test]
    fn yin_yang_balance_to_json() {
        let mut tracker = YinYangTracker::default();
        tracker.record("memory.create");
        tracker.record("memory.create");
        tracker.record("memory.create");
        tracker.record("memory.read");
        let balance = tracker.balance();
        let json = balance.to_json();
        assert_eq!(json["state"], "yang_excess");
    }

    // ── Metric clamping tests ───────────────────────────────────────

    #[test]
    fn impossible_metrics_clamped_negative_cpu() {
        let mut detector = AnomalyDetector::new(AnomalyConfig {
            min_samples: 5,
            ..Default::default()
        });
        // Feed 10 stable samples
        for _ in 0..10 {
            let hv = make_hv(0.3, 0.2, 0.1, 0.0, 1.0, Some(45.0));
            detector.check(&hv);
        }
        // Feed impossible negative CPU — should be clamped to 0.0, not skew z-score
        let hv = make_hv(-100.0, 0.2, 0.1, 0.0, 1.0, Some(45.0));
        let alerts = detector.check(&hv);
        // Clamped to 0.0, which is a deviation from 0.3 but not extreme
        // The key assertion: z-score should be bounded (not f32::MAX or NaN)
        for alert in &alerts {
            assert!(
                alert.z_score.abs() < 100.0,
                "z-score should be bounded, got {}",
                alert.z_score
            );
            assert!(!alert.z_score.is_nan(), "z-score should not be NaN");
            assert!(
                !alert.z_score.is_infinite(),
                "z-score should not be infinite"
            );
        }
    }

    #[test]
    fn impossible_metrics_clamped_f32_max() {
        let mut detector = AnomalyDetector::new(AnomalyConfig {
            min_samples: 5,
            ..Default::default()
        });
        for _ in 0..10 {
            let hv = make_hv(0.3, 0.2, 0.1, 0.0, 1.0, Some(45.0));
            detector.check(&hv);
        }
        // Feed f32::MAX CPU — should be clamped to 1.0
        let hv = make_hv(f32::MAX, 0.2, 0.1, 0.0, 1.0, Some(45.0));
        let alerts = detector.check(&hv);
        for alert in &alerts {
            assert!(
                alert.z_score.abs() < 100.0,
                "z-score should be bounded, got {}",
                alert.z_score
            );
            assert!(!alert.z_score.is_nan());
        }
    }

    #[test]
    fn impossible_metrics_clamped_nan() {
        let mut detector = AnomalyDetector::new(AnomalyConfig {
            min_samples: 5,
            ..Default::default()
        });
        for _ in 0..10 {
            let hv = make_hv(0.3, 0.2, 0.1, 0.0, 1.0, Some(45.0));
            detector.check(&hv);
        }
        // Feed NaN CPU — should be clamped to 0.0
        let hv = make_hv(f32::NAN, 0.2, 0.1, 0.0, 1.0, Some(45.0));
        let alerts = detector.check(&hv);
        for alert in &alerts {
            assert!(!alert.z_score.is_nan(), "z-score should not be NaN");
            assert!(alert.z_score.abs() < 100.0);
        }
    }

    #[test]
    fn impossible_metrics_clamped_extreme_temperature() {
        let mut detector = AnomalyDetector::new(AnomalyConfig {
            min_samples: 5,
            ..Default::default()
        });
        for _ in 0..10 {
            let hv = make_hv(0.3, 0.2, 0.1, 0.0, 1.0, Some(45.0));
            detector.check(&hv);
        }
        // Feed extreme temperature — should be clamped to 200.0
        let hv = make_hv(0.3, 0.2, 0.1, 0.0, 1.0, Some(1e10));
        let alerts = detector.check(&hv);
        for alert in &alerts {
            assert!(
                alert.z_score.abs() < 100.0,
                "z-score should be bounded, got {}",
                alert.z_score
            );
        }
    }

    #[test]
    fn clamp_metric_function_direct() {
        assert_eq!(clamp_metric(HarmonyDimension::CpuLoad, -1.0), 0.0);
        assert_eq!(clamp_metric(HarmonyDimension::CpuLoad, 2.0), 1.0);
        assert_eq!(clamp_metric(HarmonyDimension::CpuLoad, 0.5), 0.5);
        assert_eq!(clamp_metric(HarmonyDimension::BatteryPercent, -0.5), 0.0);
        assert_eq!(clamp_metric(HarmonyDimension::BatteryPercent, 1.5), 1.0);
        assert_eq!(clamp_metric(HarmonyDimension::Temperature, -100.0), -40.0);
        assert_eq!(clamp_metric(HarmonyDimension::Temperature, 500.0), 200.0);
        assert_eq!(clamp_metric(HarmonyDimension::Temperature, 45.0), 45.0);
        assert_eq!(clamp_metric(HarmonyDimension::CpuLoad, f32::NAN), 0.0);
        assert_eq!(clamp_metric(HarmonyDimension::CpuLoad, f32::INFINITY), 0.0);
    }
}
