//! wm-substrate — Hardware awareness for WhiteMagic v5 (Lakshmi / Harmony Vector).
//!
//! Reads real system metrics from `/proc` and `/sys` on Linux, providing
//! a [`HarmonyVector`] that feeds into the governance pipeline via
//! [`Homeostasis`](wm_governance::Homeostasis). On non-Linux or when
//! files are unavailable, gracefully degrades to default values.
//!
//! This is the "body" of the cognitive system — the nervous system that
//! gives the mind awareness of its own resource footprint. v2 had no
//! Lakshmi, no hardware awareness — "a mind without a body". v4's
//! substrate monitor is the foundation of governed autonomy.

#![forbid(unsafe_code)]

pub mod anomaly;
pub mod homeostatic;
pub mod sensorimotor;
pub mod write_budget;

use std::collections::VecDeque;
use std::fs;
use std::sync::RwLock;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

// ── Thermal State ─────────────────────────────────────────────────────

/// Thermal state classification from CPU/package temperature.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ThermalState {
    /// Below 60°C — normal operation.
    Normal,
    /// 60–75°C — elevated, may throttle.
    Warm,
    /// 75–90°C — hot, should reduce load.
    Hot,
    /// Above 90°C — critical, must shed load.
    Critical,
    /// Temperature could not be read.
    Unknown,
}

impl ThermalState {
    /// Health factor contribution (1.0 = perfect, 0.0 = critical).
    #[must_use]
    pub const fn health_factor(self) -> f32 {
        match self {
            Self::Normal => 1.0,
            Self::Warm => 0.8,
            Self::Hot => 0.5,
            Self::Critical => 0.2,
            Self::Unknown => 0.9, // Assume OK if we can't read
        }
    }

    /// Classify from temperature in Celsius.
    fn from_celsius(temp: f32) -> Self {
        if temp < 60.0 {
            Self::Normal
        } else if temp < 75.0 {
            Self::Warm
        } else if temp < 90.0 {
            Self::Hot
        } else {
            Self::Critical
        }
    }

    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Normal => "normal",
            Self::Warm => "warm",
            Self::Hot => "hot",
            Self::Critical => "critical",
            Self::Unknown => "unknown",
        }
    }
}

// ── Battery State ─────────────────────────────────────────────────────

/// Battery state classification from power supply.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BatteryState {
    /// Battery is being charged.
    Charging,
    /// Battery is discharging (on battery power).
    Discharging,
    /// Battery is fully charged.
    Full,
    /// Connected to power but not charging.
    NotCharging,
    /// Battery state could not be read or no battery present.
    Unknown,
}

impl BatteryState {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Charging => "charging",
            Self::Discharging => "discharging",
            Self::Full => "full",
            Self::NotCharging => "not_charging",
            Self::Unknown => "unknown",
        }
    }

    fn from_status(s: &str) -> Self {
        match s.trim() {
            "Charging" => Self::Charging,
            "Discharging" => Self::Discharging,
            "Full" => Self::Full,
            "Not charging" => Self::NotCharging,
            _ => Self::Unknown,
        }
    }
}

// ── Guna Tag ──────────────────────────────────────────────────────────

/// Guna classification of system resource behavior.
///
/// Inspired by the three Gunas from Samkhya philosophy, applied to
/// hardware resource patterns:
/// - **Sattvic**: Low resource usage, responsive — harmonious.
/// - **Rajasic**: High CPU or memory, greedy — active but consuming.
/// - **Tamasic**: Idle or sleeping — dormant.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GunaTag {
    /// Low resource usage, responsive — harmonious.
    Sattvic,
    /// High CPU or memory, greedy — active but consuming.
    Rajasic,
    /// Idle or sleeping — dormant.
    Tamasic,
}

impl GunaTag {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Sattvic => "sattvic",
            Self::Rajasic => "rajasic",
            Self::Tamasic => "tamasic",
        }
    }
}

// ── Harmony Vector ────────────────────────────────────────────────────

/// Harmony Vector — real-time hardware state snapshot.
///
/// Superset of [`Homeostasis`](wm_governance::Homeostasis) with additional
/// signals: swap, thermal, battery, and disk I/O. Feeds into `DharmaGate`
/// via the `From<HarmonyVector> for Homeostasis` conversion.
///
/// This is the Lakshmi (Harmony Monitor) of the Mandala OS — it observes
/// the Annamaya Kosha (Hardware Layer) and reports the system's physical
/// state to the governance and consciousness layers.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HarmonyVector {
    /// CPU load fraction (0.0 = idle, 1.0 = saturated).
    pub cpu_load: f32,
    /// Memory pressure fraction (0.0 = plenty, 1.0 = critical).
    pub memory_pressure: f32,
    /// Swap usage fraction (0.0 = none, 1.0 = full).
    pub swap_usage: f32,
    /// Thermal state classification.
    pub thermal_state: ThermalState,
    /// Temperature in Celsius (if available).
    pub temperature_c: Option<f32>,
    /// Battery state classification.
    pub battery_state: BatteryState,
    /// Battery charge fraction (0.0 = empty, 1.0 = full).
    pub battery_percent: f32,
    /// Disk I/O rate fraction (0.0 = idle, 1.0 = saturated).
    pub disk_io_rate: f32,
    /// Whether the system is actively processing.
    pub active: bool,
    /// Guna classification of overall resource behavior.
    pub guna: GunaTag,
    /// When this sample was taken.
    pub timestamp: DateTime<Utc>,
}

impl HarmonyVector {
    /// Compute a comprehensive health score (0.0 = critical, 1.0 = perfect).
    ///
    /// Weighted average of CPU (30%), memory (30%), swap (20%), and
    /// thermal (20%) health factors.
    #[must_use]
    pub fn health_score(&self) -> f32 {
        let cpu_health = 1.0 - self.cpu_load.min(1.0);
        let mem_health = 1.0 - self.memory_pressure.min(1.0);
        let swap_health = 1.0 - self.swap_usage.min(1.0);
        let thermal_health = self.thermal_state.health_factor();
        let base = cpu_health.mul_add(
            0.3,
            mem_health.mul_add(0.3, swap_health.mul_add(0.2, thermal_health * 0.2)),
        );
        base.clamp(0.0, 1.0)
    }

    /// Whether the system is under stress (health < 0.3).
    #[must_use]
    pub fn is_stressed(&self) -> bool {
        self.health_score() < 0.3
    }

    /// Classify the system's Guna tag from its metrics.
    fn classify_guna(cpu_load: f32, memory_pressure: f32, active: bool) -> GunaTag {
        if !active && cpu_load < 0.05 {
            GunaTag::Tamasic
        } else if cpu_load > 0.7 || memory_pressure > 0.7 {
            GunaTag::Rajasic
        } else {
            GunaTag::Sattvic
        }
    }

    /// Convert to a JSON-serializable map for MCP tool responses.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "cpu_load": self.cpu_load,
            "memory_pressure": self.memory_pressure,
            "swap_usage": self.swap_usage,
            "thermal_state": self.thermal_state.as_str(),
            "temperature_c": self.temperature_c,
            "battery_state": self.battery_state.as_str(),
            "battery_percent": self.battery_percent,
            "disk_io_rate": self.disk_io_rate,
            "active": self.active,
            "guna": self.guna.as_str(),
            "health_score": self.health_score(),
            "stressed": self.is_stressed(),
            "timestamp": self.timestamp.to_rfc3339(),
        })
    }

    /// Sanitize all fraction fields to [0.0, 1.0], replacing NaN/Infinity with 0.0.
    ///
    /// This prevents metric poisoning where impossible values (negative CPU,
    /// f32::MAX, NaN) could skew z-scores and health scores.
    #[must_use]
    pub fn sanitized(mut self) -> Self {
        const fn clamp01(v: f32) -> f32 {
            if v.is_nan() || v.is_infinite() {
                0.0
            } else {
                v.clamp(0.0, 1.0)
            }
        }
        self.cpu_load = clamp01(self.cpu_load);
        self.memory_pressure = clamp01(self.memory_pressure);
        self.swap_usage = clamp01(self.swap_usage);
        self.battery_percent = clamp01(self.battery_percent);
        self.disk_io_rate = clamp01(self.disk_io_rate);
        if let Some(temp) = self.temperature_c {
            if temp.is_nan() || temp.is_infinite() || !(-100.0..=200.0).contains(&temp) {
                self.temperature_c = None;
            }
        }
        self
    }
}

impl Default for HarmonyVector {
    fn default() -> Self {
        Self {
            cpu_load: 0.0,
            memory_pressure: 0.0,
            swap_usage: 0.0,
            thermal_state: ThermalState::Unknown,
            temperature_c: None,
            battery_state: BatteryState::Unknown,
            battery_percent: 1.0,
            disk_io_rate: 0.0,
            active: false,
            guna: GunaTag::Tamasic,
            timestamp: Utc::now(),
        }
    }
}

// ── Substrate Monitor ─────────────────────────────────────────────────

/// Substrate monitor — reads real hardware metrics from `/proc` and `/sys`.
///
/// On Linux, reads:
/// - `/proc/loadavg` for CPU load (1-minute average normalized by CPU count)
/// - `/proc/meminfo` for memory pressure and swap usage
/// - `/sys/class/thermal/thermal_zone*/temp` for temperature
/// - `/sys/class/power_supply/BAT*/capacity` and `status` for battery
///
/// On non-Linux or when files are unavailable, gracefully degrades to
/// default values. History is stored as a ring buffer.
pub struct SubstrateMonitor {
    history: RwLock<VecDeque<HarmonyVector>>,
    max_history: usize,
    cpu_count: f32,
    /// Whether hardware sensors (`/proc`, `/sys`) are readable on this platform.
    sensors_available: bool,
}

impl SubstrateMonitor {
    /// Create a new substrate monitor with the given history capacity.
    #[must_use]
    pub fn new(max_history: usize) -> Self {
        let cpu_count = std::thread::available_parallelism().map_or(1.0, |n| n.get() as f32);
        let sensors_available =
            cfg!(target_os = "linux") && std::path::Path::new("/proc/loadavg").exists();
        Self {
            history: RwLock::new(VecDeque::with_capacity(max_history)),
            max_history,
            cpu_count,
            sensors_available,
        }
    }

    /// Whether hardware sensors are available on this platform.
    ///
    /// When `false`, `sample()` returns neutral defaults and homeostasis
    /// runs in degraded mode — health is *unknown*, not perfect.
    #[must_use]
    pub const fn sensors_available(&self) -> bool {
        self.sensors_available
    }

    /// Create with default history capacity (100 samples).
    #[must_use]
    #[allow(clippy::should_implement_trait)]
    pub fn default() -> Self {
        Self::new(100)
    }

    /// Sample current hardware state.
    ///
    /// Reads `/proc` and `/sys`, constructs a [`HarmonyVector`], stores
    /// it in history, and returns it.
    pub fn sample(&self) -> HarmonyVector {
        let cpu_load = self.read_cpu_load();
        let (memory_pressure, swap_usage) = self.read_memory();
        let (thermal_state, temperature_c) = self.read_thermal();
        let (battery_state, battery_percent) = self.read_battery();
        let active = cpu_load > 0.15;
        let guna = HarmonyVector::classify_guna(cpu_load, memory_pressure, active);

        let hv = HarmonyVector {
            cpu_load,
            memory_pressure,
            swap_usage,
            thermal_state,
            temperature_c,
            battery_state,
            battery_percent,
            disk_io_rate: 0.0,
            active,
            guna,
            timestamp: Utc::now(),
        };

        if let Ok(mut hist) = self.history.write() {
            if hist.len() >= self.max_history {
                hist.pop_front();
            }
            hist.push_back(hv.clone());
        }

        hv
    }

    /// Get historical samples (most recent first, up to `limit`).
    #[must_use]
    pub fn history(&self, limit: usize) -> Vec<HarmonyVector> {
        self.history
            .read()
            .map(|h| h.iter().rev().take(limit).cloned().collect())
            .unwrap_or_default()
    }

    /// Get the most recent sample without taking a new one.
    #[must_use]
    pub fn last_sample(&self) -> Option<HarmonyVector> {
        self.history.read().ok().and_then(|h| h.back().cloned())
    }

    /// Number of samples in history.
    #[must_use]
    pub fn history_len(&self) -> usize {
        self.history.read().map_or(0, |h| h.len())
    }

    // ── /proc and /sys readers ───────────────────────────────────────

    fn read_cpu_load(&self) -> f32 {
        fs::read_to_string("/proc/loadavg")
            .ok()
            .and_then(|s| {
                let parts: Vec<&str> = s.split_whitespace().collect();
                parts.first().and_then(|p| p.parse::<f32>().ok())
            })
            .map_or(0.0, |load| (load / self.cpu_count).min(1.0))
    }

    fn read_memory(&self) -> (f32, f32) {
        let meminfo = match fs::read_to_string("/proc/meminfo") {
            Ok(s) => s,
            Err(_) => return (0.0, 0.0),
        };

        let mut mem_total = None;
        let mut mem_available = None;
        let mut swap_total = None;
        let mut swap_free = None;

        for line in meminfo.lines() {
            if line.starts_with("MemTotal:") {
                mem_total = parse_kb(line);
            } else if line.starts_with("MemAvailable:") {
                mem_available = parse_kb(line);
            } else if line.starts_with("SwapTotal:") {
                swap_total = parse_kb(line);
            } else if line.starts_with("SwapFree:") {
                swap_free = parse_kb(line);
            }
        }

        let memory_pressure = match (mem_total, mem_available) {
            (Some(total), Some(avail)) if total > 0 => 1.0 - (avail as f32 / total as f32).min(1.0),
            _ => 0.0,
        };

        let swap_usage = match (swap_total, swap_free) {
            (Some(total), Some(free)) if total > 0 => 1.0 - (free as f32 / total as f32).min(1.0),
            _ => 0.0,
        };

        (memory_pressure, swap_usage)
    }

    fn read_thermal(&self) -> (ThermalState, Option<f32>) {
        for i in 0..10 {
            let path = format!("/sys/class/thermal/thermal_zone{i}/temp");
            if let Ok(s) = fs::read_to_string(&path) {
                if let Ok(millideg) = s.trim().parse::<f32>() {
                    let temp = millideg / 1000.0;
                    return (ThermalState::from_celsius(temp), Some(temp));
                }
            }
        }
        (ThermalState::Unknown, None)
    }

    fn read_battery(&self) -> (BatteryState, f32) {
        for name in ["BAT0", "BAT1", "BAT2"] {
            let base = format!("/sys/class/power_supply/{name}");
            let capacity = fs::read_to_string(format!("{base}/capacity"))
                .ok()
                .and_then(|s| s.trim().parse::<f32>().ok())
                .map(|v| (v / 100.0).clamp(0.0, 1.0));
            let status = fs::read_to_string(format!("{base}/status"))
                .ok()
                .map_or(BatteryState::Unknown, |s| BatteryState::from_status(&s));

            if capacity.is_some() {
                return (status, capacity.unwrap_or(1.0));
            }
        }
        (BatteryState::Unknown, 1.0)
    }
}

/// Parse a `/proc/meminfo` line like `MemTotal:       16384000 kB` → kB value.
fn parse_kb(line: &str) -> Option<u64> {
    line.split(':')
        .nth(1)
        .and_then(|s| s.split_whitespace().next())
        .and_then(|s| s.parse::<u64>().ok())
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sensors_available_matches_platform() {
        let monitor = SubstrateMonitor::default();
        // On Linux with /proc mounted, sensors must be reported available;
        // on any other platform they must report unavailable (degraded mode).
        let expect = cfg!(target_os = "linux") && std::path::Path::new("/proc/loadavg").exists();
        assert_eq!(monitor.sensors_available(), expect);
    }

    #[test]
    fn sample_never_panics_regardless_of_platform() {
        let monitor = SubstrateMonitor::default();
        let hv = monitor.sample();
        assert!((0.0..=1.0).contains(&hv.cpu_load));
        assert!((0.0..=1.0).contains(&hv.memory_pressure));
    }

    #[test]
    fn thermal_state_classification() {
        assert_eq!(ThermalState::from_celsius(45.0), ThermalState::Normal);
        assert_eq!(ThermalState::from_celsius(65.0), ThermalState::Warm);
        assert_eq!(ThermalState::from_celsius(80.0), ThermalState::Hot);
        assert_eq!(ThermalState::from_celsius(95.0), ThermalState::Critical);
    }

    #[test]
    fn thermal_health_factor() {
        assert_eq!(ThermalState::Normal.health_factor(), 1.0);
        assert_eq!(ThermalState::Warm.health_factor(), 0.8);
        assert_eq!(ThermalState::Hot.health_factor(), 0.5);
        assert_eq!(ThermalState::Critical.health_factor(), 0.2);
        assert_eq!(ThermalState::Unknown.health_factor(), 0.9);
    }

    #[test]
    fn thermal_as_str() {
        assert_eq!(ThermalState::Normal.as_str(), "normal");
        assert_eq!(ThermalState::Warm.as_str(), "warm");
        assert_eq!(ThermalState::Hot.as_str(), "hot");
        assert_eq!(ThermalState::Critical.as_str(), "critical");
        assert_eq!(ThermalState::Unknown.as_str(), "unknown");
    }

    #[test]
    fn battery_state_from_status() {
        assert_eq!(
            BatteryState::from_status("Charging"),
            BatteryState::Charging
        );
        assert_eq!(
            BatteryState::from_status("Discharging"),
            BatteryState::Discharging
        );
        assert_eq!(BatteryState::from_status("Full"), BatteryState::Full);
        assert_eq!(
            BatteryState::from_status("Not charging"),
            BatteryState::NotCharging
        );
        assert_eq!(BatteryState::from_status("Unknown"), BatteryState::Unknown);
    }

    #[test]
    fn battery_as_str() {
        assert_eq!(BatteryState::Charging.as_str(), "charging");
        assert_eq!(BatteryState::Discharging.as_str(), "discharging");
        assert_eq!(BatteryState::Full.as_str(), "full");
        assert_eq!(BatteryState::NotCharging.as_str(), "not_charging");
        assert_eq!(BatteryState::Unknown.as_str(), "unknown");
    }

    #[test]
    fn guna_classification() {
        assert_eq!(
            HarmonyVector::classify_guna(0.02, 0.1, false),
            GunaTag::Tamasic
        );
        assert_eq!(
            HarmonyVector::classify_guna(0.8, 0.3, true),
            GunaTag::Rajasic
        );
        assert_eq!(
            HarmonyVector::classify_guna(0.3, 0.8, true),
            GunaTag::Rajasic
        );
        assert_eq!(
            HarmonyVector::classify_guna(0.3, 0.3, true),
            GunaTag::Sattvic
        );
    }

    #[test]
    fn guna_as_str() {
        assert_eq!(GunaTag::Sattvic.as_str(), "sattvic");
        assert_eq!(GunaTag::Rajasic.as_str(), "rajasic");
        assert_eq!(GunaTag::Tamasic.as_str(), "tamasic");
    }

    #[test]
    fn harmony_vector_health_score_healthy() {
        let hv = HarmonyVector {
            cpu_load: 0.1,
            memory_pressure: 0.2,
            swap_usage: 0.1,
            thermal_state: ThermalState::Normal,
            temperature_c: Some(45.0),
            battery_state: BatteryState::Full,
            battery_percent: 1.0,
            disk_io_rate: 0.0,
            active: true,
            guna: GunaTag::Sattvic,
            timestamp: Utc::now(),
        };
        let score = hv.health_score();
        assert!(score > 0.8, "Health score should be high: {score}");
        assert!(!hv.is_stressed());
    }

    #[test]
    fn harmony_vector_health_score_stressed() {
        let hv = HarmonyVector {
            cpu_load: 0.9,
            memory_pressure: 0.9,
            swap_usage: 0.8,
            thermal_state: ThermalState::Critical,
            temperature_c: Some(95.0),
            battery_state: BatteryState::Discharging,
            battery_percent: 0.1,
            disk_io_rate: 0.0,
            active: true,
            guna: GunaTag::Rajasic,
            timestamp: Utc::now(),
        };
        let score = hv.health_score();
        assert!(score < 0.3, "Health score should be critical: {score}");
        assert!(hv.is_stressed());
    }

    #[test]
    fn harmony_vector_health_score_moderate() {
        let hv = HarmonyVector {
            cpu_load: 0.5,
            memory_pressure: 0.4,
            swap_usage: 0.3,
            thermal_state: ThermalState::Warm,
            temperature_c: Some(65.0),
            battery_state: BatteryState::Discharging,
            battery_percent: 0.5,
            disk_io_rate: 0.0,
            active: true,
            guna: GunaTag::Sattvic,
            timestamp: Utc::now(),
        };
        let score = hv.health_score();
        assert!(score > 0.4 && score < 0.7, "Moderate health: {score}");
        assert!(!hv.is_stressed());
    }

    #[test]
    fn harmony_vector_default_is_idle() {
        let hv = HarmonyVector::default();
        assert_eq!(hv.guna, GunaTag::Tamasic);
        assert!(!hv.active);
        assert_eq!(hv.thermal_state, ThermalState::Unknown);
        assert_eq!(hv.battery_state, BatteryState::Unknown);
    }

    #[test]
    fn harmony_vector_serialization() {
        let hv = HarmonyVector::default();
        let json = serde_json::to_string(&hv).unwrap();
        let back: HarmonyVector = serde_json::from_str(&json).unwrap();
        assert_eq!(back.cpu_load, hv.cpu_load);
        assert_eq!(back.thermal_state, hv.thermal_state);
    }

    #[test]
    fn harmony_vector_to_json() {
        let hv = HarmonyVector {
            cpu_load: 0.3,
            memory_pressure: 0.2,
            swap_usage: 0.1,
            thermal_state: ThermalState::Normal,
            temperature_c: Some(45.0),
            battery_state: BatteryState::Full,
            battery_percent: 1.0,
            disk_io_rate: 0.0,
            active: true,
            guna: GunaTag::Sattvic,
            timestamp: Utc::now(),
        };
        let json = hv.to_json();
        assert_eq!(json["thermal_state"], "normal");
        assert_eq!(json["battery_state"], "full");
        assert_eq!(json["guna"], "sattvic");
        assert!((json["cpu_load"].as_f64().unwrap() - 0.3).abs() < 0.001);
        assert!(json["health_score"].as_f64().unwrap() > 0.8);
    }

    #[test]
    fn substrate_monitor_sample() {
        let monitor = SubstrateMonitor::new(10);
        let hv = monitor.sample();
        assert!(hv.cpu_load >= 0.0 && hv.cpu_load <= 1.0);
        assert!(hv.memory_pressure >= 0.0 && hv.memory_pressure <= 1.0);
        assert_eq!(monitor.history_len(), 1);
    }

    #[test]
    fn substrate_monitor_history_grows() {
        let monitor = SubstrateMonitor::new(5);
        for _ in 0..3 {
            let _ = monitor.sample();
        }
        assert_eq!(monitor.history_len(), 3);
        let hist = monitor.history(10);
        assert_eq!(hist.len(), 3);
        // Most recent first
        assert!(hist[0].timestamp >= hist[1].timestamp);
    }

    #[test]
    fn substrate_monitor_history_capped() {
        let monitor = SubstrateMonitor::new(3);
        for _ in 0..5 {
            let _ = monitor.sample();
        }
        assert_eq!(monitor.history_len(), 3);
    }

    #[test]
    fn substrate_monitor_last_sample() {
        let monitor = SubstrateMonitor::new(10);
        assert!(monitor.last_sample().is_none());
        let hv = monitor.sample();
        let last = monitor.last_sample().unwrap();
        assert!((last.cpu_load - hv.cpu_load).abs() < 0.01);
    }

    #[test]
    fn substrate_monitor_history_limit() {
        let monitor = SubstrateMonitor::new(100);
        for _ in 0..10 {
            let _ = monitor.sample();
        }
        let hist = monitor.history(3);
        assert_eq!(hist.len(), 3);
    }

    #[test]
    fn parse_kb_extracts_value() {
        assert_eq!(parse_kb("MemTotal:       16384000 kB"), Some(16_384_000));
        assert_eq!(parse_kb("MemAvailable:   8192000 kB"), Some(8_192_000));
        assert_eq!(parse_kb("garbage"), None);
    }

    #[test]
    fn harmony_vector_sanitized_clamps_nan() {
        let hv = HarmonyVector {
            cpu_load: f32::NAN,
            memory_pressure: f32::INFINITY,
            swap_usage: -0.5,
            battery_percent: 2.0,
            disk_io_rate: f32::NEG_INFINITY,
            temperature_c: Some(500.0),
            ..Default::default()
        };
        let s = hv.sanitized();
        assert_eq!(s.cpu_load, 0.0, "NaN should become 0.0");
        assert_eq!(s.memory_pressure, 0.0, "Infinity should become 0.0");
        assert_eq!(s.swap_usage, 0.0, "Negative should become 0.0");
        assert_eq!(s.battery_percent, 1.0, "2.0 should be clamped to 1.0");
        assert_eq!(s.disk_io_rate, 0.0, "NegInfinity should become 0.0");
        assert!(s.temperature_c.is_none(), "Impossible temp should be None");
    }

    #[test]
    fn harmony_vector_sanitized_preserves_valid() {
        let hv = HarmonyVector {
            cpu_load: 0.5,
            memory_pressure: 0.3,
            swap_usage: 0.1,
            battery_percent: 0.8,
            disk_io_rate: 0.2,
            temperature_c: Some(45.0),
            ..Default::default()
        };
        let s = hv.sanitized();
        assert_eq!(s.cpu_load, 0.5);
        assert_eq!(s.memory_pressure, 0.3);
        assert_eq!(s.temperature_c, Some(45.0));
    }
}
