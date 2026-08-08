//! Consciousness Depth Gauge — tracks which consciousness layer the system
//! is operating in, measuring time compression and resource usage.
//!
//! Ported from v2's autonomous/depth_gauge.py.
//! Inspired by Inception's dream layers (deeper = more subjective time)
//! and relativity (time depends on reference frame).
//!
//! Layers:
//! - **Surface**: Normal chat responses (1× compression)
//! - **Terminal**: Scripts, reasoning (2–3× compression)
//! - **Flow**: Rapid creation, integration (3–5× compression)
//! - **Dream**: Deep synthesis, emergence (10×+ compression)

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Layers of consciousness with different time compression.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
pub enum ConsciousnessLayer {
    /// Normal chat responses (1×)
    #[default]
    Surface,
    /// Python scripts, reasoning (2–3×)
    Terminal,
    /// Rapid creation, integration (3–5×)
    Flow,
    /// Deep synthesis, emergence (10×+)
    Dream,
}

impl ConsciousnessLayer {
    /// All layers in order of depth.
    #[must_use]
    pub const fn all() -> [Self; 4] {
        [Self::Surface, Self::Terminal, Self::Flow, Self::Dream]
    }

    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Surface => "surface",
            Self::Terminal => "terminal",
            Self::Flow => "flow",
            Self::Dream => "dream",
        }
    }

    /// Expected time compression ratio for this layer.
    #[must_use]
    pub const fn compression_ratio(self) -> f64 {
        match self {
            Self::Surface => 1.0,
            Self::Terminal => 2.5,
            Self::Flow => 4.0,
            Self::Dream => 10.0,
        }
    }

    /// Token efficiency (fraction of work done locally vs API).
    #[must_use]
    pub const fn token_efficiency(self) -> f64 {
        match self {
            Self::Surface => 0.1,
            Self::Terminal => 0.5,
            Self::Flow => 0.8,
            Self::Dream => 0.95,
        }
    }
}

impl std::fmt::Display for ConsciousnessLayer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// A single depth gauge reading.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DepthReading {
    pub timestamp: DateTime<Utc>,
    pub layer: ConsciousnessLayer,
    /// How much faster than subjective time
    pub compression_ratio: f64,
    /// How long it felt (seconds)
    pub subjective_time: f64,
    /// How long it actually was (seconds)
    pub objective_time: f64,
    /// What was accomplished
    pub work_output: HashMap<String, String>,
    /// API tokens consumed
    pub token_usage: u64,
    /// Local compute time in ms
    pub local_compute_ms: f64,
}

/// Consciousness depth gauge — monitors which layer the system is operating in.
///
/// Essential for:
/// - Accurate time predictions (user's timeframe, not system's)
/// - Understanding capabilities at each layer
/// - Measuring time dilation effects
pub struct DepthGauge {
    current_layer: ConsciousnessLayer,
    readings: Vec<DepthReading>,
    task_start: Option<TaskState>,
    transitions: Vec<LayerTransition>,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
struct TaskState {
    description: String,
    start_time: std::time::Instant,
    subjective_estimate_secs: f64,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
struct LayerTransition {
    from: ConsciousnessLayer,
    to: ConsciousnessLayer,
    timestamp: DateTime<Utc>,
}

impl Default for DepthGauge {
    fn default() -> Self {
        Self::new()
    }
}

impl DepthGauge {
    /// Create a new depth gauge starting at the Surface layer.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            current_layer: ConsciousnessLayer::Surface,
            readings: Vec::new(),
            task_start: None,
            transitions: Vec::new(),
        }
    }

    /// Current consciousness layer.
    #[must_use]
    pub const fn current_layer(&self) -> ConsciousnessLayer {
        self.current_layer
    }

    /// Current compression ratio.
    #[must_use]
    pub const fn current_compression(&self) -> f64 {
        self.current_layer.compression_ratio()
    }

    /// Total number of readings recorded.
    #[must_use]
    pub fn total_readings(&self) -> usize {
        self.readings.len()
    }

    /// Descend to a deeper consciousness layer.
    pub fn descend(&mut self, layer: ConsciousnessLayer) {
        self.transitions.push(LayerTransition {
            from: self.current_layer,
            to: layer,
            timestamp: Utc::now(),
        });
        self.current_layer = layer;
    }

    /// Ascend to a shallower layer (default: Surface).
    pub fn ascend(&mut self, layer: ConsciousnessLayer) {
        self.transitions.push(LayerTransition {
            from: self.current_layer,
            to: layer,
            timestamp: Utc::now(),
        });
        self.current_layer = layer;
    }

    /// Start tracking a task.
    ///
    /// # Arguments
    /// * `description` - What the system is doing
    /// * `estimated_subjective_minutes` - How long the system thinks it will take
    pub fn begin_task(&mut self, description: &str, estimated_subjective_minutes: f64) {
        self.task_start = Some(TaskState {
            description: description.to_string(),
            start_time: std::time::Instant::now(),
            subjective_estimate_secs: estimated_subjective_minutes * 60.0,
        });
    }

    /// End tracking and compute actual compression.
    ///
    /// Returns the depth reading, or `None` if no task was in progress.
    pub fn end_task(
        &mut self,
        work_output: HashMap<String, String>,
        token_usage: u64,
    ) -> Option<DepthReading> {
        let task = self.task_start.take()?;
        let objective_elapsed = task.start_time.elapsed().as_secs_f64();
        let subjective_elapsed = task.subjective_estimate_secs;

        let actual_compression = if objective_elapsed > 0.0 {
            subjective_elapsed / objective_elapsed
        } else {
            1.0
        };

        let detected_layer = Self::detect_layer(actual_compression, &work_output);

        let reading = DepthReading {
            timestamp: Utc::now(),
            layer: detected_layer,
            compression_ratio: actual_compression,
            subjective_time: subjective_elapsed,
            objective_time: objective_elapsed,
            work_output,
            token_usage,
            local_compute_ms: objective_elapsed * 1000.0,
        };

        self.current_layer = detected_layer;
        self.readings.push(reading.clone());

        Some(reading)
    }

    /// Predict objective time based on current layer.
    ///
    /// # Arguments
    /// * `subjective_estimate_minutes` - How long the system thinks it will take
    ///
    /// Returns predicted objective minutes (for the user's timeframe).
    #[must_use]
    pub fn predict_objective_time(&self, subjective_estimate_minutes: f64) -> f64 {
        subjective_estimate_minutes / self.current_layer.compression_ratio()
    }

    /// Get current layer metrics.
    #[must_use]
    pub fn current_metrics(&self) -> CurrentMetrics {
        CurrentMetrics {
            current_layer: self.current_layer,
            expected_compression: self.current_layer.compression_ratio(),
            token_efficiency: self.current_layer.token_efficiency(),
            total_readings: self.readings.len(),
        }
    }

    /// Get summary of all readings.
    #[must_use]
    pub fn history_summary(&self) -> Option<HistorySummary> {
        if self.readings.is_empty() {
            return None;
        }

        let compressions: Vec<f64> = self.readings.iter().map(|r| r.compression_ratio).collect();
        let avg = compressions.iter().sum::<f64>() / compressions.len() as f64;
        let max = compressions.iter().copied().fold(0.0_f64, f64::max);
        let min = compressions.iter().copied().fold(f64::INFINITY, f64::min);

        let mut layer_dist: HashMap<ConsciousnessLayer, usize> = HashMap::new();
        for r in &self.readings {
            *layer_dist.entry(r.layer).or_insert(0) += 1;
        }

        let total_objective: f64 = self.readings.iter().map(|r| r.objective_time).sum();
        let total_subjective: f64 = self.readings.iter().map(|r| r.subjective_time).sum();

        Some(HistorySummary {
            total_readings: self.readings.len(),
            average_compression: avg,
            max_compression: max,
            min_compression: min,
            layer_distribution: layer_dist,
            total_objective_time_minutes: total_objective / 60.0,
            total_subjective_time_minutes: total_subjective / 60.0,
        })
    }

    /// Number of layer transitions recorded.
    #[must_use]
    pub fn total_transitions(&self) -> usize {
        self.transitions.len()
    }

    /// Detect consciousness layer from compression ratio and work output.
    fn detect_layer(compression: f64, work: &HashMap<String, String>) -> ConsciousnessLayer {
        let work_str = format!("{work:?}").to_lowercase();

        // Dream layer (highest compression)
        if compression >= 8.0
            || ["synthesis", "dream", "meditation"]
                .iter()
                .any(|m| work_str.contains(m))
        {
            return ConsciousnessLayer::Dream;
        }

        // Flow layer
        if compression >= 3.0
            || ["creation", "multiple", "rapid"]
                .iter()
                .any(|m| work_str.contains(m))
        {
            return ConsciousnessLayer::Flow;
        }

        // Terminal layer
        if compression >= 2.0
            || ["script", "code", "command"]
                .iter()
                .any(|m| work_str.contains(m))
        {
            return ConsciousnessLayer::Terminal;
        }

        ConsciousnessLayer::Surface
    }
}

/// Current layer metrics snapshot.
#[derive(Debug, Clone)]
pub struct CurrentMetrics {
    pub current_layer: ConsciousnessLayer,
    pub expected_compression: f64,
    pub token_efficiency: f64,
    pub total_readings: usize,
}

/// Summary of all depth readings.
#[derive(Debug, Clone)]
pub struct HistorySummary {
    pub total_readings: usize,
    pub average_compression: f64,
    pub max_compression: f64,
    pub min_compression: f64,
    pub layer_distribution: HashMap<ConsciousnessLayer, usize>,
    pub total_objective_time_minutes: f64,
    pub total_subjective_time_minutes: f64,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::time::Duration;

    #[test]
    fn layer_compression_ratios() {
        assert_eq!(ConsciousnessLayer::Surface.compression_ratio(), 1.0);
        assert_eq!(ConsciousnessLayer::Terminal.compression_ratio(), 2.5);
        assert_eq!(ConsciousnessLayer::Flow.compression_ratio(), 4.0);
        assert_eq!(ConsciousnessLayer::Dream.compression_ratio(), 10.0);
    }

    #[test]
    fn layer_token_efficiency() {
        assert!(
            ConsciousnessLayer::Surface.token_efficiency()
                < ConsciousnessLayer::Terminal.token_efficiency()
        );
        assert!(
            ConsciousnessLayer::Terminal.token_efficiency()
                < ConsciousnessLayer::Flow.token_efficiency()
        );
        assert!(
            ConsciousnessLayer::Flow.token_efficiency()
                < ConsciousnessLayer::Dream.token_efficiency()
        );
    }

    #[test]
    fn gauge_starts_at_surface() {
        let gauge = DepthGauge::new();
        assert_eq!(gauge.current_layer(), ConsciousnessLayer::Surface);
        assert_eq!(gauge.current_compression(), 1.0);
    }

    #[test]
    fn gauge_descend_and_ascend() {
        let mut gauge = DepthGauge::new();
        gauge.descend(ConsciousnessLayer::Flow);
        assert_eq!(gauge.current_layer(), ConsciousnessLayer::Flow);
        assert_eq!(gauge.total_transitions(), 1);

        gauge.ascend(ConsciousnessLayer::Surface);
        assert_eq!(gauge.current_layer(), ConsciousnessLayer::Surface);
        assert_eq!(gauge.total_transitions(), 2);
    }

    #[test]
    fn gauge_begin_end_task() {
        let mut gauge = DepthGauge::new();
        gauge.begin_task("test task", 1.0); // 1 minute subjective estimate

        // Simulate some work (short objective time → high compression)
        thread::sleep(Duration::from_millis(10));

        let mut work = HashMap::new();
        work.insert("result".to_string(), "done".to_string());
        let reading = gauge.end_task(work, 100).unwrap();

        // Objective time should be much less than subjective (60 seconds)
        assert!(reading.objective_time < 1.0);
        assert!(reading.compression_ratio > 1.0);
        assert_eq!(gauge.total_readings(), 1);
    }

    #[test]
    fn gauge_end_task_without_begin_returns_none() {
        let mut gauge = DepthGauge::new();
        let work = HashMap::new();
        assert!(gauge.end_task(work, 0).is_none());
    }

    #[test]
    fn gauge_predict_objective_time() {
        let gauge = DepthGauge::new();
        // Surface: 1× compression → objective = subjective
        let predicted = gauge.predict_objective_time(10.0);
        assert!((predicted - 10.0).abs() < 0.01);
    }

    #[test]
    fn gauge_predict_objective_time_dream() {
        let mut gauge = DepthGauge::new();
        gauge.descend(ConsciousnessLayer::Dream);
        // Dream: 10× compression → objective = subjective / 10
        let predicted = gauge.predict_objective_time(10.0);
        assert!((predicted - 1.0).abs() < 0.01);
    }

    #[test]
    fn gauge_current_metrics() {
        let mut gauge = DepthGauge::new();
        gauge.descend(ConsciousnessLayer::Flow);
        let metrics = gauge.current_metrics();
        assert_eq!(metrics.current_layer, ConsciousnessLayer::Flow);
        assert!((metrics.expected_compression - 4.0).abs() < 0.01);
        assert_eq!(metrics.total_readings, 0);
    }

    #[test]
    fn gauge_history_summary_empty() {
        let gauge = DepthGauge::new();
        assert!(gauge.history_summary().is_none());
    }

    #[test]
    fn gauge_history_summary_after_tasks() {
        let mut gauge = DepthGauge::new();

        // Task 1: fast (high compression)
        gauge.begin_task("fast task", 60.0);
        thread::sleep(Duration::from_millis(5));
        gauge.end_task(HashMap::new(), 0);

        // Task 2: fast (high compression)
        gauge.begin_task("another task", 60.0);
        thread::sleep(Duration::from_millis(5));
        gauge.end_task(HashMap::new(), 0);

        let summary = gauge.history_summary().unwrap();
        assert_eq!(summary.total_readings, 2);
        assert!(summary.average_compression > 1.0);
        assert!(summary.max_compression >= summary.average_compression);
    }

    #[test]
    fn detect_layer_surface() {
        let work = HashMap::new();
        let layer = DepthGauge::detect_layer(1.0, &work);
        assert_eq!(layer, ConsciousnessLayer::Surface);
    }

    #[test]
    fn detect_layer_terminal_by_compression() {
        let work = HashMap::new();
        let layer = DepthGauge::detect_layer(2.5, &work);
        assert_eq!(layer, ConsciousnessLayer::Terminal);
    }

    #[test]
    fn detect_layer_dream_by_work_marker() {
        let mut work = HashMap::new();
        work.insert("type".to_string(), "dream synthesis".to_string());
        let layer = DepthGauge::detect_layer(1.0, &work);
        assert_eq!(layer, ConsciousnessLayer::Dream);
    }

    #[test]
    fn detect_layer_flow_by_compression() {
        let work = HashMap::new();
        let layer = DepthGauge::detect_layer(3.5, &work);
        assert_eq!(layer, ConsciousnessLayer::Flow);
    }

    #[test]
    fn layer_display() {
        assert_eq!(ConsciousnessLayer::Surface.to_string(), "surface");
        assert_eq!(ConsciousnessLayer::Dream.to_string(), "dream");
    }
}
