//! Hardware Embodiment & Real-Time Homeostasis Telemetry
//!
//! Provides direct somatic awareness of the physical machine host:
//! - CPU package and core thermals (`/sys/class/thermal/`)
//! - System load averages (`/proc/loadavg`)
//! - Memory pressure and available RAM headroom (`/proc/meminfo`)
//! - Dynamic thermal throttle regimes (Cool, Warm, Hot, Critical)
//!
//! Allows the WhiteMagic daemon and resident copilots (Valkyrie) to monitor
//! physical embodiment in real time, knowing when to accelerate compute and
//! when to dampen background cycles to preserve silicon longevity.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::path::Path;
use wm_governance::Homeostasis;

/// Physical hardware operating regime based on thermal and load conditions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HardwareRegime {
    /// Cool (< 65°C, load < 2.5): Full speed ahead — fast drafting, aggressive speculative rounds.
    Cool,
    /// Warm (65°C – 78°C, load 2.5 – 5.0): Nominal steady-state operation.
    Warm,
    /// Hot (78°C – 86°C or load > 5.0): Thermal warning — throttle background cycle frequency.
    Hot,
    /// Critical (> 86°C): Emergency cooldown — yield CPU, suspend heavy background tasks.
    Critical,
}

impl HardwareRegime {
    /// Human-readable description of current somatic state.
    #[must_use]
    pub const fn description(self) -> &'static str {
        match self {
            Self::Cool => "Cool (optimal headroom, unrestricted acceleration)",
            Self::Warm => "Warm (steady state, normal pacing)",
            Self::Hot => "Hot (thermal warning, cycle frequency dampened)",
            Self::Critical => "Critical (thermal distress, background execution paused)",
        }
    }

    /// Whether this regime advises throttling background cognitive workloads.
    #[must_use]
    pub const fn should_throttle(self) -> bool {
        matches!(self, Self::Hot | Self::Critical)
    }
}

/// Instantaneous snapshot of physical hardware embodiment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HardwareSnapshot {
    /// Highest detected CPU package/core temperature in Celsius.
    pub temp_c: f32,
    /// 1-minute load average.
    pub load_1m: f32,
    /// 5-minute load average.
    pub load_5m: f32,
    /// Available RAM headroom in Megabytes.
    pub mem_available_mb: u64,
    /// Total RAM in Megabytes.
    pub mem_total_mb: u64,
    /// Memory pressure ratio (0.0 = completely free, 1.0 = exhausted).
    pub mem_pressure: f32,
    /// Active hardware operating regime.
    pub regime: HardwareRegime,
}

impl HardwareSnapshot {
    /// Nominal baseline snapshot for fallback or testing.
    #[must_use]
    pub const fn nominal() -> Self {
        Self {
            temp_c: 48.0,
            load_1m: 0.50,
            load_5m: 0.60,
            mem_available_mb: 8192,
            mem_total_mb: 16384,
            mem_pressure: 0.50,
            regime: HardwareRegime::Cool,
        }
    }

    /// Convert hardware snapshot to governance `Homeostasis`.
    #[must_use]
    pub fn to_homeostasis(&self, is_active: bool) -> Homeostasis {
        // Normalize load against an assumed 4 physical core / 8 thread baseline
        let normalized_cpu = (self.load_1m / 4.0).clamp(0.0, 1.0);
        Homeostasis {
            cpu_load: normalized_cpu,
            memory_pressure: self.mem_pressure.clamp(0.0, 1.0),
            active: is_active,
        }
    }
}

/// Hardware telemetry monitor sampling Linux kernel sysfs and procfs interfaces.
pub struct HardwareMonitor;

impl HardwareMonitor {
    /// Sample the current physical hardware telemetry.
    #[must_use]
    pub fn sample() -> HardwareSnapshot {
        let temp_c = Self::sample_max_temperature().unwrap_or(48.0);
        let (load_1m, load_5m) = Self::sample_loadavg().unwrap_or((0.5, 0.5));
        let (mem_total, mem_avail) = Self::sample_meminfo().unwrap_or((16384, 8192));

        let mem_pressure = if mem_total > 0 {
            1.0 - (mem_avail as f32 / mem_total as f32)
        } else {
            0.5
        };

        let regime = if temp_c >= 86.0 || load_1m >= 7.0 {
            HardwareRegime::Critical
        } else if temp_c >= 78.0 || load_1m >= 4.5 {
            HardwareRegime::Hot
        } else if temp_c >= 65.0 || load_1m >= 2.0 {
            HardwareRegime::Warm
        } else {
            HardwareRegime::Cool
        };

        HardwareSnapshot {
            temp_c,
            load_1m,
            load_5m,
            mem_available_mb: mem_avail,
            mem_total_mb: mem_total,
            mem_pressure,
            regime,
        }
    }

    /// Read max CPU temperature from `/sys/class/thermal/thermal_zone*`.
    fn sample_max_temperature() -> Option<f32> {
        let thermal_dir = Path::new("/sys/class/thermal");
        if !thermal_dir.is_dir() {
            return None;
        }

        let mut max_temp = 0.0f32;
        let mut pkg_temp = None;

        if let Ok(entries) = std::fs::read_dir(thermal_dir) {
            for entry in entries.flatten() {
                let p = entry.path();
                let file_name = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
                if file_name.starts_with("thermal_zone") {
                    let temp_file = p.join("temp");
                    let type_file = p.join("type");

                    if let Ok(temp_str) = std::fs::read_to_string(&temp_file) {
                        if let Ok(millis) = temp_str.trim().parse::<f32>() {
                            let c = millis / 1000.0;
                            if c > max_temp && c < 125.0 {
                                max_temp = c;
                            }

                            if let Ok(zone_type) = std::fs::read_to_string(&type_file) {
                                if zone_type.contains("x86_pkg_temp")
                                    || zone_type.contains("Package")
                                {
                                    pkg_temp = Some(c);
                                }
                            }
                        }
                    }
                }
            }
        }

        pkg_temp.or_else(|| if max_temp > 0.0 { Some(max_temp) } else { None })
    }

    /// Read 1m and 5m load averages from `/proc/loadavg`.
    fn sample_loadavg() -> Option<(f32, f32)> {
        let content = std::fs::read_to_string("/proc/loadavg").ok()?;
        let parts: Vec<&str> = content.split_whitespace().collect();
        if parts.len() >= 2 {
            let l1 = parts[0].parse::<f32>().ok()?;
            let l5 = parts[1].parse::<f32>().ok()?;
            return Some((l1, l5));
        }
        None
    }

    /// Read total and available memory in MB from `/proc/meminfo`.
    fn sample_meminfo() -> Option<(u64, u64)> {
        let content = std::fs::read_to_string("/proc/meminfo").ok()?;
        let mut total_kb = None;
        let mut avail_kb = None;

        for line in content.lines() {
            if line.starts_with("MemTotal:") {
                total_kb = parse_meminfo_kb(line);
            } else if line.starts_with("MemAvailable:") {
                avail_kb = parse_meminfo_kb(line);
            }
            if total_kb.is_some() && avail_kb.is_some() {
                break;
            }
        }

        match (total_kb, avail_kb) {
            (Some(t), Some(a)) => Some((t / 1024, a / 1024)),
            _ => None,
        }
    }
}

fn parse_meminfo_kb(line: &str) -> Option<u64> {
    let parts: Vec<&str> = line.split_whitespace().collect();
    if parts.len() >= 2 {
        parts[1].parse::<u64>().ok()
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hardware_sampling_produces_plausible_values() {
        let snap = HardwareMonitor::sample();
        // Plausible range checks on any real or mock Linux system
        assert!(
            snap.temp_c > 0.0 && snap.temp_c < 120.0,
            "Plausible temp: {}",
            snap.temp_c
        );
        assert!(snap.load_1m >= 0.0, "Non-negative load: {}", snap.load_1m);
        assert!(
            snap.mem_total_mb > 0,
            "Total RAM > 0: {}",
            snap.mem_total_mb
        );
        assert!(snap.mem_pressure >= 0.0 && snap.mem_pressure <= 1.0);
    }

    #[test]
    fn test_regime_classification() {
        assert_eq!(HardwareRegime::Cool.should_throttle(), false);
        assert_eq!(HardwareRegime::Warm.should_throttle(), false);
        assert_eq!(HardwareRegime::Hot.should_throttle(), true);
        assert_eq!(HardwareRegime::Critical.should_throttle(), true);
    }

    #[test]
    fn test_homeostasis_conversion() {
        let snap = HardwareSnapshot {
            temp_c: 72.0,
            load_1m: 2.0,
            load_5m: 1.5,
            mem_available_mb: 4096,
            mem_total_mb: 8192,
            mem_pressure: 0.5,
            regime: HardwareRegime::Warm,
        };
        let h = snap.to_homeostasis(true);
        assert_eq!(h.cpu_load, 0.5);
        assert_eq!(h.memory_pressure, 0.5);
        assert_eq!(h.active, true);
        assert!(!h.is_stressed());
    }
}
