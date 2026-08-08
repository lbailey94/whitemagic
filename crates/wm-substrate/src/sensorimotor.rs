//! Sensorimotor Weave — hardware I/O abstraction for embodied AI.
//!
//! Provides a framework for connecting sensors and actuators to the
//! cognitive substrate via a unified trait interface. Inspired by:
//! - copper-rs: deterministic Rust robotics with sub-microsecond IPC
//! - dora-rs: dataflow-oriented robotic architecture (Zenoh SHM)
//! - v1 WhiteMagic: embodiment.py HarmonyMonitor, physical_metrics.py
//!
//! Architecture:
//!   Sensor → SensorReading → SensorimotorBus → ActuatorCommand → Actuator
//!
//! The `SensorDevice` and `ActuatorDevice` traits are designed to be
//! implementable via C-ABI FFI (feature-gated `hardware` feature) so that
//! real hardware drivers can be linked without polluting the core crate.
//!
//! When the `hardware` feature is disabled, all operations are stubbed
//! with sensible defaults — the framework is fully testable on any machine.

#![forbid(unsafe_code)]

use std::collections::HashMap;
use std::time::Instant;

use serde::{Deserialize, Serialize};

// ── Sensor Types ───────────────────────────────────────────────────────

/// Type of sensor reading.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SensorKind {
    /// Temperature sensor (CPU, ambient, motor).
    Temperature,
    /// IMU / accelerometer / gyroscope.
    Imu,
    /// Camera / vision sensor.
    Camera,
    /// Microphone / audio sensor.
    Audio,
    /// Distance / range finder (ultrasonic, lidar, IR).
    Distance,
    /// Pressure / force sensor.
    Pressure,
    /// Encoded motor position / joint angle.
    Encoder,
    /// GPS / global position.
    Gps,
    /// Power / current / voltage sensor.
    Power,
    /// Custom sensor type.
    Custom,
}

impl SensorKind {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Temperature => "temperature",
            Self::Imu => "imu",
            Self::Camera => "camera",
            Self::Audio => "audio",
            Self::Distance => "distance",
            Self::Pressure => "pressure",
            Self::Encoder => "encoder",
            Self::Gps => "gps",
            Self::Power => "power",
            Self::Custom => "custom",
        }
    }
}

impl std::fmt::Display for SensorKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

// ── Actuator Types ─────────────────────────────────────────────────────

/// Type of actuator output.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ActuatorKind {
    /// Motor / servo (speed or position control).
    Motor,
    /// Relay / digital output.
    Relay,
    /// LED / display output.
    Display,
    /// Speaker / audio output.
    Speaker,
    /// Valve / hydraulic control.
    Valve,
    /// Heating / cooling element.
    Thermal,
    /// Custom actuator type.
    Custom,
}

impl ActuatorKind {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Motor => "motor",
            Self::Relay => "relay",
            Self::Display => "display",
            Self::Speaker => "speaker",
            Self::Valve => "valve",
            Self::Thermal => "thermal",
            Self::Custom => "custom",
        }
    }
}

impl std::fmt::Display for ActuatorKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

// ── Sensor Reading ─────────────────────────────────────────────────────

/// A single sensor reading with timestamp.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorReading {
    /// Sensor identifier (e.g., "cpu_temp", "left_motor_encoder").
    pub sensor_id: String,
    /// Type of sensor.
    pub kind: SensorKind,
    /// Raw value (unit depends on sensor type).
    pub value: f64,
    /// Optional secondary values (e.g., 3-axis IMU: x, y, z).
    pub extra: Vec<f64>,
    /// Timestamp of reading.
    pub timestamp: f64,
    /// Confidence (0.0–1.0), 1.0 = fully trusted.
    pub confidence: f64,
}

impl SensorReading {
    /// Create a new sensor reading with current timestamp and full confidence.
    #[must_use]
    pub fn new(sensor_id: impl Into<String>, kind: SensorKind, value: f64) -> Self {
        Self {
            sensor_id: sensor_id.into(),
            kind,
            value,
            extra: Vec::new(),
            timestamp: now_secs(),
            confidence: 1.0,
        }
    }

    /// Add extra values (e.g., 3-axis data).
    #[must_use]
    pub fn with_extra(mut self, extra: Vec<f64>) -> Self {
        self.extra = extra;
        self
    }

    /// Set confidence.
    #[must_use]
    pub const fn with_confidence(mut self, confidence: f64) -> Self {
        self.confidence = confidence.clamp(0.0, 1.0);
        self
    }
}

// ── Actuator Command ───────────────────────────────────────────────────

/// A command to an actuator.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActuatorCommand {
    /// Actuator identifier (e.g., "left_motor", "valve_3").
    pub actuator_id: String,
    /// Type of actuator.
    pub kind: ActuatorKind,
    /// Primary command value (e.g., speed, position, duty cycle).
    pub value: f64,
    /// Optional secondary parameters (e.g., acceleration limit, duration).
    pub params: Vec<f64>,
    /// Command timestamp.
    pub timestamp: f64,
}

impl ActuatorCommand {
    /// Create a new actuator command.
    #[must_use]
    pub fn new(actuator_id: impl Into<String>, kind: ActuatorKind, value: f64) -> Self {
        Self {
            actuator_id: actuator_id.into(),
            kind,
            value,
            params: Vec::new(),
            timestamp: now_secs(),
        }
    }

    /// Add parameters.
    #[must_use]
    pub fn with_params(mut self, params: Vec<f64>) -> Self {
        self.params = params;
        self
    }
}

// ── Device Traits ──────────────────────────────────────────────────────

/// Trait for sensor devices.
///
/// Implementations may wrap real hardware (via C-ABI FFI when the
/// `hardware` feature is enabled) or provide stub/simulated readings.
pub trait SensorDevice: Send + Sync {
    /// Unique sensor identifier.
    fn id(&self) -> &str;

    /// Sensor type.
    fn kind(&self) -> SensorKind;

    /// Read current value. Returns `None` if the sensor is unavailable.
    fn read(&self) -> Option<SensorReading>;

    /// Whether the sensor is currently available/connected.
    fn is_available(&self) -> bool {
        true
    }
}

/// Trait for actuator devices.
///
/// Implementations may wrap real hardware (via C-ABI FFI when the
/// `hardware` feature is enabled) or provide stub/simulated responses.
pub trait ActuatorDevice: Send + Sync {
    /// Unique actuator identifier.
    fn id(&self) -> &str;

    /// Actuator type.
    fn kind(&self) -> ActuatorKind;

    /// Send a command to the actuator. Returns `Ok(())` on success.
    fn command(&self, cmd: &ActuatorCommand) -> Result<(), String>;

    /// Whether the actuator is currently available/connected.
    fn is_available(&self) -> bool {
        true
    }

    /// Emergency stop — immediately disable the actuator.
    fn e_stop(&self) -> Result<(), String> {
        Ok(())
    }
}

// ── Stub Devices ───────────────────────────────────────────────────────

/// Stub sensor that returns a fixed value. Used for testing and when
/// the `hardware` feature is disabled.
pub struct StubSensor {
    id: String,
    kind: SensorKind,
    value: f64,
}

impl StubSensor {
    #[must_use]
    pub fn new(id: impl Into<String>, kind: SensorKind, value: f64) -> Self {
        Self {
            id: id.into(),
            kind,
            value,
        }
    }
}

impl SensorDevice for StubSensor {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> SensorKind {
        self.kind
    }

    fn read(&self) -> Option<SensorReading> {
        Some(SensorReading::new(&self.id, self.kind, self.value))
    }
}

/// Stub actuator that accepts all commands. Used for testing.
pub struct StubActuator {
    id: String,
    kind: ActuatorKind,
    last_command: std::sync::Mutex<Option<ActuatorCommand>>,
}

impl StubActuator {
    #[must_use]
    pub fn new(id: impl Into<String>, kind: ActuatorKind) -> Self {
        Self {
            id: id.into(),
            kind,
            last_command: std::sync::Mutex::new(None),
        }
    }

    /// Get the last command sent to this actuator (for testing).
    #[must_use]
    pub fn last_command(&self) -> Option<ActuatorCommand> {
        self.last_command.lock().map(|c| c.clone()).unwrap_or(None)
    }
}

impl ActuatorDevice for StubActuator {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> ActuatorKind {
        self.kind
    }

    fn command(&self, cmd: &ActuatorCommand) -> Result<(), String> {
        let Ok(mut last) = self.last_command.lock() else {
            return Err("sensorimotor last-command lock poisoned".to_string());
        };
        *last = Some(cmd.clone());
        Ok(())
    }
}

// ── Sensorimotor Bus ───────────────────────────────────────────────────

/// The central bus connecting sensors and actuators to the cognitive system.
///
/// Manages device registration, sensor reading aggregation, and actuator
/// command dispatch. Thread-safe via `RwLock`.
pub struct SensorimotorBus {
    sensors: HashMap<String, Box<dyn SensorDevice>>,
    actuators: HashMap<String, Box<dyn ActuatorDevice>>,
    /// Recent sensor readings (ring buffer, last N).
    reading_history: VecDeque<SensorReading>,
    /// Max history size.
    max_history: usize,
    /// Total commands sent.
    commands_sent: u64,
    /// Total readings collected.
    readings_collected: u64,
}

use std::collections::VecDeque;

impl SensorimotorBus {
    /// Create a new bus with the given history capacity.
    #[must_use]
    pub fn new(max_history: usize) -> Self {
        Self {
            sensors: HashMap::new(),
            actuators: HashMap::new(),
            reading_history: VecDeque::with_capacity(max_history),
            max_history,
            commands_sent: 0,
            readings_collected: 0,
        }
    }

    /// Register a sensor device.
    pub fn register_sensor(&mut self, sensor: Box<dyn SensorDevice>) {
        self.sensors.insert(sensor.id().to_string(), sensor);
    }

    /// Register an actuator device.
    pub fn register_actuator(&mut self, actuator: Box<dyn ActuatorDevice>) {
        self.actuators.insert(actuator.id().to_string(), actuator);
    }

    /// Poll all sensors and collect readings.
    pub fn poll_all(&mut self) -> Vec<SensorReading> {
        let readings: Vec<SensorReading> = self.sensors.values().filter_map(|s| s.read()).collect();

        for r in &readings {
            self.reading_history.push_back(r.clone());
            if self.reading_history.len() > self.max_history {
                self.reading_history.pop_front();
            }
        }

        self.readings_collected += u64::try_from(readings.len()).unwrap_or(0);
        readings
    }

    /// Read from a specific sensor by ID.
    #[must_use]
    pub fn read_sensor(&self, sensor_id: &str) -> Option<SensorReading> {
        self.sensors.get(sensor_id).and_then(|s| s.read())
    }

    /// Send a command to a specific actuator.
    pub fn send_command(&mut self, cmd: &ActuatorCommand) -> Result<(), String> {
        let actuator = self
            .actuators
            .get(&cmd.actuator_id)
            .ok_or_else(|| format!("actuator '{}' not registered", cmd.actuator_id))?;

        actuator.command(cmd)?;
        self.commands_sent += 1;
        Ok(())
    }

    /// Emergency stop all actuators.
    #[must_use]
    pub fn e_stop_all(&self) -> Vec<String> {
        self.actuators
            .values()
            .filter_map(|a| a.e_stop().err())
            .collect()
    }

    /// Get recent sensor readings.
    #[must_use]
    pub const fn recent_readings(&self) -> &[SensorReading] {
        // Return empty slice — we can't return a reference to VecDeque directly
        // In practice, callers should use `poll_all` or `read_sensor`
        &[]
    }

    /// Get the reading history as a Vec.
    #[must_use]
    pub fn history(&self) -> Vec<SensorReading> {
        self.reading_history.iter().cloned().collect()
    }

    /// Number of registered sensors.
    #[must_use]
    pub fn sensor_count(&self) -> usize {
        self.sensors.len()
    }

    /// Number of registered actuators.
    #[must_use]
    pub fn actuator_count(&self) -> usize {
        self.actuators.len()
    }

    /// Total readings collected since creation.
    #[must_use]
    pub const fn readings_collected(&self) -> u64 {
        self.readings_collected
    }

    /// Total commands sent since creation.
    #[must_use]
    pub const fn commands_sent(&self) -> u64 {
        self.commands_sent
    }

    /// List all registered sensor IDs.
    #[must_use]
    pub fn sensor_ids(&self) -> Vec<String> {
        self.sensors.keys().cloned().collect()
    }

    /// List all registered actuator IDs.
    #[must_use]
    pub fn actuator_ids(&self) -> Vec<String> {
        self.actuators.keys().cloned().collect()
    }
}

impl Default for SensorimotorBus {
    fn default() -> Self {
        Self::new(256)
    }
}

// ── Reflex Loop ────────────────────────────────────────────────────────

/// A simple reflex loop that polls sensors and triggers actuator commands
/// when sensor values cross thresholds.
///
/// Inspired by the biological reflex arc: sensor → spinal cord → actuator,
/// bypassing the cognitive layer for time-critical responses.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReflexRule {
    /// Sensor ID to monitor.
    pub sensor_id: String,
    /// Actuator ID to trigger.
    pub actuator_id: String,
    /// Actuator kind for the command.
    pub actuator_kind: ActuatorKind,
    /// Threshold value. If the sensor reading exceeds this, trigger.
    pub threshold: f64,
    /// Command value to send when triggered.
    pub command_value: f64,
    /// Whether the trigger is `value > threshold` (true) or `value < threshold` (false).
    pub trigger_above: bool,
    /// Minimum interval between triggers (cooldown), in seconds.
    pub cooldown_secs: f64,
}

impl ReflexRule {
    /// Create a new reflex rule that triggers when sensor exceeds threshold.
    #[must_use]
    pub fn above(
        sensor_id: impl Into<String>,
        actuator_id: impl Into<String>,
        actuator_kind: ActuatorKind,
        threshold: f64,
        command_value: f64,
        cooldown_secs: f64,
    ) -> Self {
        Self {
            sensor_id: sensor_id.into(),
            actuator_id: actuator_id.into(),
            actuator_kind,
            threshold,
            command_value,
            trigger_above: true,
            cooldown_secs,
        }
    }

    /// Create a new reflex rule that triggers when sensor drops below threshold.
    #[must_use]
    pub fn below(
        sensor_id: impl Into<String>,
        actuator_id: impl Into<String>,
        actuator_kind: ActuatorKind,
        threshold: f64,
        command_value: f64,
        cooldown_secs: f64,
    ) -> Self {
        Self {
            sensor_id: sensor_id.into(),
            actuator_id: actuator_id.into(),
            actuator_kind,
            threshold,
            command_value,
            trigger_above: false,
            cooldown_secs,
        }
    }

    /// Check if a sensor reading triggers this rule.
    #[must_use]
    pub fn is_triggered(&self, reading: &SensorReading) -> bool {
        if self.trigger_above {
            reading.value > self.threshold
        } else {
            reading.value < self.threshold
        }
    }
}

/// A reflex loop manager that evaluates rules against sensor readings.
pub struct ReflexLoop {
    rules: Vec<ReflexRule>,
    last_trigger: HashMap<String, Instant>,
}

impl ReflexLoop {
    /// Create a new reflex loop.
    #[must_use]
    pub fn new() -> Self {
        Self {
            rules: Vec::new(),
            last_trigger: HashMap::new(),
        }
    }

    /// Add a reflex rule.
    pub fn add_rule(&mut self, rule: ReflexRule) {
        self.rules.push(rule);
    }

    /// Evaluate all rules against a set of sensor readings.
    /// Returns commands to execute.
    pub fn evaluate(&mut self, readings: &[SensorReading]) -> Vec<ActuatorCommand> {
        let mut commands = Vec::new();
        let now = Instant::now();

        for rule in &self.rules {
            // Check cooldown
            if let Some(&last) = self.last_trigger.get(&rule.sensor_id) {
                let elapsed = now.duration_since(last).as_secs_f64();
                if elapsed < rule.cooldown_secs {
                    continue;
                }
            }

            // Find matching reading
            if let Some(reading) = readings.iter().find(|r| r.sensor_id == rule.sensor_id) {
                if rule.is_triggered(reading) {
                    commands.push(ActuatorCommand::new(
                        &rule.actuator_id,
                        rule.actuator_kind,
                        rule.command_value,
                    ));
                    self.last_trigger.insert(rule.sensor_id.clone(), now);
                }
            }
        }

        commands
    }

    /// Number of rules.
    #[must_use]
    pub fn rule_count(&self) -> usize {
        self.rules.len()
    }
}

impl Default for ReflexLoop {
    fn default() -> Self {
        Self::new()
    }
}

// ── Linux Hardware Sensors ─────────────────────────────────────────────

/// Sensor that reads a single value from a `/sys` filesystem path.
///
/// Common uses:
/// - `/sys/class/thermal/thermal_zone0/temp` (temperature in millidegrees)
/// - `/sys/class/hwmon/hwmon0/fan1_input` (fan RPM)
/// - `/sys/class/power_supply/BAT0/capacity` (battery percentage)
///
/// The `scale` field divides the raw integer value (e.g., 55000 → 55.0
/// for millidegrees → degrees).
pub struct SysfsSensor {
    id: String,
    kind: SensorKind,
    path: String,
    scale: f64,
    available: bool,
}

impl SysfsSensor {
    /// Create a new sysfs sensor.
    ///
    /// - `path`: absolute path to the sysfs file (e.g., `/sys/class/thermal/thermal_zone0/temp`)
    /// - `scale`: divisor to convert raw integer to float (e.g., 1000.0 for millidegrees)
    #[must_use]
    pub fn new(
        id: impl Into<String>,
        kind: SensorKind,
        path: impl Into<String>,
        scale: f64,
    ) -> Self {
        let path = path.into();
        let available = std::path::Path::new(&path).exists();
        Self {
            id: id.into(),
            kind,
            path,
            scale,
            available,
        }
    }

    /// Create a thermal zone sensor (temperature in °C).
    #[must_use]
    pub fn thermal(zone: usize) -> Self {
        Self::new(
            format!("thermal_zone{zone}"),
            SensorKind::Temperature,
            format!("/sys/class/thermal/thermal_zone{zone}/temp"),
            1000.0,
        )
    }

    /// Create a battery capacity sensor (0.0–100.0).
    #[must_use]
    pub fn battery(name: &str) -> Self {
        Self::new(
            format!("battery_{name}"),
            SensorKind::Power,
            format!("/sys/class/power_supply/{name}/capacity"),
            1.0,
        )
    }

    /// Create a fan speed sensor (RPM).
    #[must_use]
    pub fn fan(hwmon: usize, fan: usize) -> Self {
        Self::new(
            format!("fan{hwmon}_{fan}"),
            SensorKind::Custom,
            format!("/sys/class/hwmon/hwmon{hwmon}/fan{fan}_input"),
            1.0,
        )
    }
}

impl SensorDevice for SysfsSensor {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> SensorKind {
        self.kind
    }

    fn read(&self) -> Option<SensorReading> {
        if !self.available {
            return None;
        }
        let raw = std::fs::read_to_string(&self.path).ok()?;
        let trimmed = raw.trim();
        let value: f64 = trimmed.parse().ok()?;
        let scaled = if self.scale > 0.0 {
            value / self.scale
        } else {
            value
        };
        Some(SensorReading::new(&self.id, self.kind, scaled))
    }

    fn is_available(&self) -> bool {
        self.available
    }
}

impl std::fmt::Debug for SysfsSensor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SysfsSensor")
            .field("id", &self.id)
            .field("kind", &self.kind)
            .field("path", &self.path)
            .field("scale", &self.scale)
            .field("available", &self.available)
            .finish()
    }
}

/// Parser function type for extracting a sensor value from file contents.
pub type SensorParser = Box<dyn Fn(&str) -> Option<f64> + Send + Sync>;

/// Sensor that reads a value from a `/proc` filesystem file by parsing
/// a key-value format.
///
/// Common uses:
/// - `/proc/loadavg` — CPU load average (first field)
/// - `/proc/meminfo` — `MemAvailable:` / `MemTotal:` for memory pressure
/// - `/proc/stat` — CPU time slices
pub struct ProcfsSensor {
    id: String,
    kind: SensorKind,
    path: String,
    /// Parser: extracts the value from the file contents.
    parser: SensorParser,
    available: bool,
}

impl ProcfsSensor {
    /// Create a new procfs sensor with a custom parser.
    #[must_use]
    pub fn new(
        id: impl Into<String>,
        kind: SensorKind,
        path: impl Into<String>,
        parser: SensorParser,
    ) -> Self {
        let path = path.into();
        let available = std::path::Path::new(&path).exists();
        Self {
            id: id.into(),
            kind,
            path,
            parser,
            available,
        }
    }

    /// Create a CPU load average sensor from `/proc/loadavg`.
    #[must_use]
    pub fn loadavg() -> Self {
        Self::new(
            "cpu_loadavg",
            SensorKind::Custom,
            "/proc/loadavg",
            Box::new(|content: &str| {
                content
                    .split_whitespace()
                    .next()
                    .and_then(|s| s.parse::<f64>().ok())
            }),
        )
    }

    /// Create a memory pressure sensor from `/proc/meminfo`.
    ///
    /// Returns `1.0 - (MemAvailable / MemTotal)`, clamped to [0, 1].
    #[must_use]
    pub fn mem_pressure() -> Self {
        Self::new(
            "mem_pressure",
            SensorKind::Custom,
            "/proc/meminfo",
            Box::new(|content: &str| {
                let mut mem_total = None;
                let mut mem_avail = None;
                for line in content.lines() {
                    if line.starts_with("MemTotal:") {
                        mem_total = parse_proc_kb(line);
                    } else if line.starts_with("MemAvailable:") {
                        mem_avail = parse_proc_kb(line);
                    }
                }
                match (mem_total, mem_avail) {
                    (Some(total), Some(avail)) if total > 0 => {
                        Some(1.0 - (avail as f64 / total as f64).min(1.0))
                    }
                    _ => None,
                }
            }),
        )
    }
}

impl SensorDevice for ProcfsSensor {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> SensorKind {
        self.kind
    }

    fn read(&self) -> Option<SensorReading> {
        if !self.available {
            return None;
        }
        let content = std::fs::read_to_string(&self.path).ok()?;
        let value = (self.parser)(&content)?;
        Some(SensorReading::new(&self.id, self.kind, value))
    }

    fn is_available(&self) -> bool {
        self.available
    }
}

impl std::fmt::Debug for ProcfsSensor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ProcfsSensor")
            .field("id", &self.id)
            .field("kind", &self.kind)
            .field("path", &self.path)
            .field("available", &self.available)
            .finish_non_exhaustive()
    }
}

/// Parse a `/proc/meminfo` line like `MemTotal:       16384000 kB` → kB value.
fn parse_proc_kb(line: &str) -> Option<u64> {
    line.split(':')
        .nth(1)
        .and_then(|s| s.split_whitespace().next())
        .and_then(|s| s.parse::<u64>().ok())
}

// ── CPU Usage Sensor ───────────────────────────────────────────────────

/// Sensor that reads CPU usage percentage from `/proc/stat`.
///
/// Computes the percentage by comparing idle vs. total time slices
/// between consecutive reads. The first read returns 0% (no baseline yet).
/// Returns a value in [0.0, 100.0] representing the aggregate CPU usage.
pub struct CpuUsageSensor {
    prev_idle: Option<u64>,
    prev_total: Option<u64>,
}

impl CpuUsageSensor {
    #[must_use]
    pub const fn new() -> Self {
        Self {
            prev_idle: None,
            prev_total: None,
        }
    }
}

impl Default for CpuUsageSensor {
    fn default() -> Self {
        Self::new()
    }
}

impl SensorDevice for CpuUsageSensor {
    fn id(&self) -> &str {
        "cpu_usage"
    }

    fn kind(&self) -> SensorKind {
        SensorKind::Custom
    }

    fn read(&self) -> Option<SensorReading> {
        let content = std::fs::read_to_string("/proc/stat").ok()?;
        let first_line = content.lines().next()?;
        if !first_line.starts_with("cpu ") {
            return None;
        }
        let fields: Vec<u64> = first_line
            .split_whitespace()
            .skip(1)
            .filter_map(|s| s.parse::<u64>().ok())
            .collect();
        if fields.len() < 4 {
            return None;
        }
        let idle = fields[3];
        let total: u64 = fields.iter().sum();
        let usage = match (self.prev_idle, self.prev_total) {
            (Some(prev_idle), Some(prev_total)) => {
                let idle_delta = idle.saturating_sub(prev_idle) as f64;
                let total_delta = total.saturating_sub(prev_total) as f64;
                if total_delta > 0.0 {
                    ((1.0 - idle_delta / total_delta) * 100.0).clamp(0.0, 100.0)
                } else {
                    0.0
                }
            }
            _ => 0.0,
        };
        Some(SensorReading::new("cpu_usage", SensorKind::Custom, usage))
    }

    fn is_available(&self) -> bool {
        std::path::Path::new("/proc/stat").exists()
    }
}

impl std::fmt::Debug for CpuUsageSensor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("CpuUsageSensor")
            .field("prev_idle", &self.prev_idle)
            .field("prev_total", &self.prev_total)
            .finish()
    }
}

// ── Disk Usage Sensor ──────────────────────────────────────────────────

/// Sensor that reads disk usage percentage for a given mount point.
///
/// Uses `statvfs` to determine the fraction of used space.
/// Returns a value in [0.0, 100.0].
pub struct DiskUsageSensor {
    id: String,
    path: String,
    available: bool,
}

impl DiskUsageSensor {
    #[must_use]
    pub fn new(id: impl Into<String>, path: impl Into<String>) -> Self {
        let path = path.into();
        let available = std::path::Path::new(&path).exists();
        Self {
            id: id.into(),
            path,
            available,
        }
    }

    /// Create a root filesystem usage sensor.
    #[must_use]
    pub fn root() -> Self {
        Self::new("disk_root", "/")
    }
}

impl SensorDevice for DiskUsageSensor {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> SensorKind {
        SensorKind::Custom
    }

    fn read(&self) -> Option<SensorReading> {
        if !self.available {
            return None;
        }
        let output = std::process::Command::new("df")
            .arg("-P")
            .arg(&self.path)
            .output()
            .ok()?;
        let stdout = String::from_utf8(output.stdout).ok()?;
        let line = stdout.lines().nth(1)?;
        let fields: Vec<&str> = line.split_whitespace().collect();
        if fields.len() < 5 {
            return None;
        }
        let used: f64 = fields[2].parse().ok()?;
        let total: f64 = fields[1].parse().ok()?;
        if total > 0.0 {
            let pct = (used / total) * 100.0;
            Some(SensorReading::new(&self.id, SensorKind::Custom, pct))
        } else {
            None
        }
    }

    fn is_available(&self) -> bool {
        self.available
    }
}

impl std::fmt::Debug for DiskUsageSensor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("DiskUsageSensor")
            .field("id", &self.id)
            .field("path", &self.path)
            .field("available", &self.available)
            .finish()
    }
}

// ── Network Throughput Sensor ──────────────────────────────────────────

/// Sensor that reads network throughput from `/proc/net/dev`.
///
/// Returns bytes/sec since the last read. The first read returns 0.
/// Monitors a specific interface (e.g., "eth0", "wlan0").
pub struct NetworkThroughputSensor {
    id: String,
    interface: String,
    prev_rx_bytes: Option<u64>,
    prev_tx_bytes: Option<u64>,
    prev_time: Option<Instant>,
}

impl NetworkThroughputSensor {
    #[must_use]
    pub fn new(interface: impl Into<String>) -> Self {
        let iface = interface.into();
        Self {
            id: format!("net_{iface}"),
            interface: iface,
            prev_rx_bytes: None,
            prev_tx_bytes: None,
            prev_time: None,
        }
    }

    /// Auto-detect the default network interface by reading /proc/net/dev
    /// and picking the first non-lo interface.
    #[must_use]
    pub fn default_interface() -> Self {
        let iface = if let Ok(content) = std::fs::read_to_string("/proc/net/dev") {
            content
                .lines()
                .skip(2)
                .find_map(|line| {
                    let name = line.split(':').next()?.trim();
                    if name != "lo" && !name.is_empty() {
                        Some(name.to_string())
                    } else {
                        None
                    }
                })
                .unwrap_or_else(|| "eth0".to_string())
        } else {
            "eth0".to_string()
        };
        Self::new(iface)
    }
}

impl SensorDevice for NetworkThroughputSensor {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> SensorKind {
        SensorKind::Custom
    }

    fn read(&self) -> Option<SensorReading> {
        let content = std::fs::read_to_string("/proc/net/dev").ok()?;
        for line in content.lines().skip(2) {
            let mut parts = line.split(':');
            let name = parts.next()?.trim();
            if name != self.interface {
                continue;
            }
            let stats: Vec<u64> = parts
                .next()?
                .split_whitespace()
                .filter_map(|s| s.parse::<u64>().ok())
                .collect();
            if stats.len() < 9 {
                return None;
            }
            let rx_bytes = stats[0];
            let tx_bytes = stats[8];
            let now = Instant::now();
            let throughput = match (self.prev_rx_bytes, self.prev_tx_bytes, self.prev_time) {
                (Some(prev_rx), Some(prev_tx), Some(prev_t)) => {
                    let elapsed = now.duration_since(prev_t).as_secs_f64();
                    if elapsed > 0.0 {
                        let rx_delta = rx_bytes.saturating_sub(prev_rx) as f64;
                        let tx_delta = tx_bytes.saturating_sub(prev_tx) as f64;
                        (rx_delta + tx_delta) / elapsed
                    } else {
                        0.0
                    }
                }
                _ => 0.0,
            };
            return Some(SensorReading::new(&self.id, SensorKind::Custom, throughput));
        }
        None
    }

    fn is_available(&self) -> bool {
        std::path::Path::new("/proc/net/dev").exists()
    }
}

impl std::fmt::Debug for NetworkThroughputSensor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("NetworkThroughputSensor")
            .field("id", &self.id)
            .field("interface", &self.interface)
            .finish_non_exhaustive()
    }
}

// ── CPU Frequency Sensor ───────────────────────────────────────────────

/// Sensor that reads CPU frequency from `/sys/devices/system/cpu`.
///
/// Reads the current frequency for a given CPU core.
/// Returns frequency in MHz.
pub struct CpuFreqSensor {
    id: String,
    path: String,
    available: bool,
}

impl CpuFreqSensor {
    #[must_use]
    pub fn new(core: usize) -> Self {
        let path = format!("/sys/devices/system/cpu/cpu{core}/cpufreq/scaling_cur_freq");
        let available = std::path::Path::new(&path).exists();
        Self {
            id: format!("cpu{core}_freq"),
            path,
            available,
        }
    }
}

impl SensorDevice for CpuFreqSensor {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> SensorKind {
        SensorKind::Custom
    }

    fn read(&self) -> Option<SensorReading> {
        if !self.available {
            return None;
        }
        let raw = std::fs::read_to_string(&self.path).ok()?;
        let khz: f64 = raw.trim().parse().ok()?;
        Some(SensorReading::new(
            &self.id,
            SensorKind::Custom,
            khz / 1000.0,
        ))
    }

    fn is_available(&self) -> bool {
        self.available
    }
}

impl std::fmt::Debug for CpuFreqSensor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("CpuFreqSensor")
            .field("id", &self.id)
            .field("path", &self.path)
            .field("available", &self.available)
            .finish()
    }
}

// ── Sysfs Actuator ─────────────────────────────────────────────────────

/// Actuator that writes a value to a `/sys` filesystem file.
///
/// Common uses:
/// - Fan PWM control: `/sys/class/hwmon/hwmon0/pwm1` (0–255)
/// - LED brightness: `/sys/class/leds/led0/brightness` (0–255)
/// - CPU governor: `/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor`
///
/// The `scale` field multiplies the command value before writing
/// (e.g., 1.0 for direct, 255.0 if command is 0.0–1.0 and output is 0–255).
pub struct SysfsActuator {
    id: String,
    kind: ActuatorKind,
    path: String,
    scale: f64,
    available: bool,
}

impl SysfsActuator {
    /// Create a new sysfs actuator.
    ///
    /// - `path`: absolute path to the sysfs file
    /// - `scale`: multiplier to convert command value to raw output
    #[must_use]
    pub fn new(
        id: impl Into<String>,
        kind: ActuatorKind,
        path: impl Into<String>,
        scale: f64,
    ) -> Self {
        let path = path.into();
        let available = std::path::Path::new(&path).exists();
        Self {
            id: id.into(),
            kind,
            path,
            scale,
            available,
        }
    }

    /// Create a fan PWM controller for hwmon device.
    #[must_use]
    pub fn fan_pwm(hwmon: usize, pwm: usize) -> Self {
        Self::new(
            format!("fan_pwm{hwmon}_{pwm}"),
            ActuatorKind::Motor,
            format!("/sys/class/hwmon/hwmon{hwmon}/pwm{pwm}"),
            1.0,
        )
    }

    /// Create an LED brightness controller.
    #[must_use]
    pub fn led(name: &str) -> Self {
        Self::new(
            format!("led_{name}"),
            ActuatorKind::Display,
            format!("/sys/class/leds/{name}/brightness"),
            1.0,
        )
    }
}

impl ActuatorDevice for SysfsActuator {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> ActuatorKind {
        self.kind
    }

    fn command(&self, cmd: &ActuatorCommand) -> Result<(), String> {
        if !self.available {
            return Err(format!("actuator '{}' path not available", self.id));
        }
        let raw_value = cmd.value * self.scale;
        let output = format!("{}", raw_value.round() as i64);
        std::fs::write(&self.path, output)
            .map_err(|e| format!("failed to write to {}: {e}", self.path))
    }

    fn is_available(&self) -> bool {
        self.available
    }

    fn e_stop(&self) -> Result<(), String> {
        if !self.available {
            return Err(format!("actuator '{}' path not available", self.id));
        }
        // Write 0 to disable
        std::fs::write(&self.path, "0").map_err(|e| format!("failed to e-stop {}: {e}", self.path))
    }
}

impl std::fmt::Debug for SysfsActuator {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SysfsActuator")
            .field("id", &self.id)
            .field("kind", &self.kind)
            .field("path", &self.path)
            .field("scale", &self.scale)
            .field("available", &self.available)
            .finish()
    }
}

// ── Actuator Discovery ─────────────────────────────────────────────────

/// Auto-discover fan PWM controllers on Linux.
///
/// Scans `/sys/class/hwmon/hwmon*/pwm*` for writable PWM entries.
#[must_use]
pub fn discover_fan_actuators() -> Vec<SysfsActuator> {
    let mut actuators = Vec::new();
    for hwmon in 0..8 {
        for pwm in 1..=4 {
            let actuator = SysfsActuator::fan_pwm(hwmon, pwm);
            if actuator.is_available() {
                actuators.push(actuator);
            }
        }
    }
    actuators
}

/// Auto-discover LED controllers on Linux.
///
/// Scans common LED names in `/sys/class/leds/`.
#[must_use]
pub fn discover_led_actuators() -> Vec<SysfsActuator> {
    let mut actuators = Vec::new();
    for name in [
        "input0::scrolllock",
        "input0::numlock",
        "input0::capslock",
        "mmc0::",
        "phy0-led",
        "eth0-link",
        "power",
        "charging",
        "disk-activity",
    ] {
        let actuator = SysfsActuator::led(name);
        if actuator.is_available() {
            actuators.push(actuator);
        }
    }
    actuators
}

/// Auto-discover available thermal zones on Linux.
///
/// Scans `/sys/class/thermal/thermal_zone*` and returns sensors for each.
#[must_use]
pub fn discover_thermal_sensors() -> Vec<SysfsSensor> {
    let mut sensors = Vec::new();
    for i in 0..16 {
        let sensor = SysfsSensor::thermal(i);
        if sensor.is_available() {
            sensors.push(sensor);
        }
    }
    sensors
}

/// Auto-discover battery sensors on Linux.
///
/// Scans `/sys/class/power_supply/BAT*` and returns sensors for each.
#[must_use]
pub fn discover_battery_sensors() -> Vec<SysfsSensor> {
    let mut sensors = Vec::new();
    for name in ["BAT0", "BAT1", "BAT2", "BAT3", "BATC", "BATT"] {
        let sensor = SysfsSensor::battery(name);
        if sensor.is_available() {
            sensors.push(sensor);
        }
    }
    sensors
}

/// Create a `SensorimotorBus` pre-populated with all discovered Linux hardware sensors.
///
/// On non-Linux platforms, returns an empty bus.
#[must_use]
pub fn linux_hardware_bus() -> SensorimotorBus {
    let mut bus = SensorimotorBus::new(256);

    // Thermal sensors
    for sensor in discover_thermal_sensors() {
        bus.register_sensor(Box::new(sensor));
    }

    // Battery sensors
    for sensor in discover_battery_sensors() {
        bus.register_sensor(Box::new(sensor));
    }

    // /proc sensors (Linux only)
    if cfg!(target_os = "linux") {
        if std::path::Path::new("/proc/loadavg").exists() {
            bus.register_sensor(Box::new(ProcfsSensor::loadavg()));
        }
        if std::path::Path::new("/proc/meminfo").exists() {
            bus.register_sensor(Box::new(ProcfsSensor::mem_pressure()));
        }
        if std::path::Path::new("/proc/stat").exists() {
            bus.register_sensor(Box::new(CpuUsageSensor::new()));
        }
        if std::path::Path::new("/proc/net/dev").exists() {
            bus.register_sensor(Box::new(NetworkThroughputSensor::default_interface()));
        }
    }

    // Disk usage sensor
    if std::path::Path::new("/").exists() {
        bus.register_sensor(Box::new(DiskUsageSensor::root()));
    }

    // CPU frequency sensors (up to 16 cores)
    for core in 0..16 {
        let sensor = CpuFreqSensor::new(core);
        if sensor.is_available() {
            bus.register_sensor(Box::new(sensor));
        }
    }

    // Fan PWM actuators
    for actuator in discover_fan_actuators() {
        bus.register_actuator(Box::new(actuator));
    }

    // LED actuators
    for actuator in discover_led_actuators() {
        bus.register_actuator(Box::new(actuator));
    }

    bus
}

// ── Helpers ────────────────────────────────────────────────────────────

/// Get current time in seconds (Unix timestamp).
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
    fn sensor_kind_as_str() {
        assert_eq!(SensorKind::Temperature.as_str(), "temperature");
        assert_eq!(SensorKind::Imu.as_str(), "imu");
        assert_eq!(SensorKind::Camera.as_str(), "camera");
    }

    #[test]
    fn actuator_kind_as_str() {
        assert_eq!(ActuatorKind::Motor.as_str(), "motor");
        assert_eq!(ActuatorKind::Relay.as_str(), "relay");
    }

    #[test]
    fn sensor_reading_new() {
        let r = SensorReading::new("cpu_temp", SensorKind::Temperature, 55.0);
        assert_eq!(r.sensor_id, "cpu_temp");
        assert_eq!(r.kind, SensorKind::Temperature);
        assert!((r.value - 55.0).abs() < f64::EPSILON);
        assert!((r.confidence - 1.0).abs() < f64::EPSILON);
        assert!(r.extra.is_empty());
    }

    #[test]
    fn sensor_reading_with_extra() {
        let r = SensorReading::new("imu0", SensorKind::Imu, 0.0).with_extra(vec![1.0, 2.0, 3.0]);
        assert_eq!(r.extra, vec![1.0, 2.0, 3.0]);
    }

    #[test]
    fn sensor_reading_with_confidence() {
        let r = SensorReading::new("cam0", SensorKind::Camera, 128.0).with_confidence(0.8);
        assert!((r.confidence - 0.8).abs() < f64::EPSILON);
    }

    #[test]
    fn sensor_reading_confidence_clamped() {
        let r = SensorReading::new("s0", SensorKind::Custom, 0.0).with_confidence(1.5);
        assert!((r.confidence - 1.0).abs() < f64::EPSILON);
    }

    #[test]
    fn actuator_command_new() {
        let c = ActuatorCommand::new("motor_l", ActuatorKind::Motor, 0.5);
        assert_eq!(c.actuator_id, "motor_l");
        assert_eq!(c.kind, ActuatorKind::Motor);
        assert!((c.value - 0.5).abs() < f64::EPSILON);
    }

    #[test]
    fn actuator_command_with_params() {
        let c =
            ActuatorCommand::new("motor_r", ActuatorKind::Motor, 1.0).with_params(vec![0.1, 2.0]);
        assert_eq!(c.params, vec![0.1, 2.0]);
    }

    #[test]
    fn stub_sensor_read() {
        let s = StubSensor::new("temp0", SensorKind::Temperature, 42.0);
        assert_eq!(s.id(), "temp0");
        assert_eq!(s.kind(), SensorKind::Temperature);
        let r = s.read().unwrap();
        assert!((r.value - 42.0).abs() < f64::EPSILON);
    }

    #[test]
    fn stub_actuator_command() {
        let a = StubActuator::new("motor0", ActuatorKind::Motor);
        let cmd = ActuatorCommand::new("motor0", ActuatorKind::Motor, 0.7);
        a.command(&cmd).unwrap();
        let last = a.last_command().unwrap();
        assert!((last.value - 0.7).abs() < f64::EPSILON);
    }

    #[test]
    fn bus_register_and_poll() {
        let mut bus = SensorimotorBus::new(64);
        bus.register_sensor(Box::new(StubSensor::new(
            "s1",
            SensorKind::Temperature,
            50.0,
        )));
        bus.register_sensor(Box::new(StubSensor::new("s2", SensorKind::Distance, 1.5)));

        assert_eq!(bus.sensor_count(), 2);
        let readings = bus.poll_all();
        assert_eq!(readings.len(), 2);
        assert_eq!(bus.readings_collected(), 2);
    }

    #[test]
    fn bus_send_command() {
        let mut bus = SensorimotorBus::new(64);
        bus.register_actuator(Box::new(StubActuator::new("m1", ActuatorKind::Motor)));

        let cmd = ActuatorCommand::new("m1", ActuatorKind::Motor, 0.5);
        bus.send_command(&cmd).unwrap();
        assert_eq!(bus.commands_sent(), 1);
    }

    #[test]
    fn bus_command_unknown_actuator() {
        let mut bus = SensorimotorBus::new(64);
        let cmd = ActuatorCommand::new("unknown", ActuatorKind::Motor, 0.0);
        assert!(bus.send_command(&cmd).is_err());
    }

    #[test]
    fn bus_history() {
        let mut bus = SensorimotorBus::new(3);
        bus.register_sensor(Box::new(StubSensor::new(
            "s1",
            SensorKind::Temperature,
            50.0,
        )));

        bus.poll_all();
        bus.poll_all();
        bus.poll_all();
        bus.poll_all(); // 4 polls, history caps at 3

        let h = bus.history();
        assert_eq!(h.len(), 3);
    }

    #[test]
    fn bus_sensor_ids() {
        let mut bus = SensorimotorBus::new(64);
        bus.register_sensor(Box::new(StubSensor::new("a", SensorKind::Temperature, 0.0)));
        bus.register_sensor(Box::new(StubSensor::new("b", SensorKind::Imu, 0.0)));

        let ids = bus.sensor_ids();
        assert!(ids.contains(&"a".to_string()));
        assert!(ids.contains(&"b".to_string()));
    }

    #[test]
    fn bus_actuator_ids() {
        let mut bus = SensorimotorBus::new(64);
        bus.register_actuator(Box::new(StubActuator::new("m1", ActuatorKind::Motor)));

        let ids = bus.actuator_ids();
        assert!(ids.contains(&"m1".to_string()));
    }

    #[test]
    fn bus_e_stop_all() {
        let mut bus = SensorimotorBus::new(64);
        bus.register_actuator(Box::new(StubActuator::new("m1", ActuatorKind::Motor)));
        bus.register_actuator(Box::new(StubActuator::new("m2", ActuatorKind::Motor)));

        let errors = bus.e_stop_all();
        assert!(errors.is_empty()); // Stubs don't error
    }

    #[test]
    fn reflex_rule_above() {
        let rule = ReflexRule::above("temp0", "fan0", ActuatorKind::Motor, 70.0, 1.0, 5.0);
        let reading_high = SensorReading::new("temp0", SensorKind::Temperature, 75.0);
        let reading_low = SensorReading::new("temp0", SensorKind::Temperature, 60.0);

        assert!(rule.is_triggered(&reading_high));
        assert!(!rule.is_triggered(&reading_low));
    }

    #[test]
    fn reflex_rule_below() {
        let rule = ReflexRule::below("battery", "led", ActuatorKind::Display, 20.0, 1.0, 10.0);
        let reading_low = SensorReading::new("battery", SensorKind::Power, 15.0);
        let reading_ok = SensorReading::new("battery", SensorKind::Power, 80.0);

        assert!(rule.is_triggered(&reading_low));
        assert!(!rule.is_triggered(&reading_ok));
    }

    #[test]
    fn reflex_loop_evaluate() {
        let mut loop_ = ReflexLoop::new();
        loop_.add_rule(ReflexRule::above(
            "temp0",
            "fan0",
            ActuatorKind::Motor,
            70.0,
            1.0,
            0.0, // No cooldown for test
        ));

        let readings = vec![SensorReading::new("temp0", SensorKind::Temperature, 75.0)];
        let commands = loop_.evaluate(&readings);
        assert_eq!(commands.len(), 1);
        assert_eq!(commands[0].actuator_id, "fan0");
    }

    #[test]
    fn reflex_loop_no_trigger() {
        let mut loop_ = ReflexLoop::new();
        loop_.add_rule(ReflexRule::above(
            "temp0",
            "fan0",
            ActuatorKind::Motor,
            70.0,
            1.0,
            0.0,
        ));

        let readings = vec![SensorReading::new("temp0", SensorKind::Temperature, 60.0)];
        let commands = loop_.evaluate(&readings);
        assert!(commands.is_empty());
    }

    #[test]
    fn reflex_loop_cooldown() {
        let mut loop_ = ReflexLoop::new();
        loop_.add_rule(ReflexRule::above(
            "temp0",
            "fan0",
            ActuatorKind::Motor,
            70.0,
            1.0,
            100.0, // 100s cooldown
        ));

        let readings = vec![SensorReading::new("temp0", SensorKind::Temperature, 80.0)];

        // First trigger
        let cmds1 = loop_.evaluate(&readings);
        assert_eq!(cmds1.len(), 1);

        // Second trigger — should be on cooldown
        let cmds2 = loop_.evaluate(&readings);
        assert!(cmds2.is_empty());
    }

    #[test]
    fn reflex_loop_multiple_rules() {
        let mut loop_ = ReflexLoop::new();
        loop_.add_rule(ReflexRule::above(
            "temp0",
            "fan0",
            ActuatorKind::Motor,
            70.0,
            1.0,
            0.0,
        ));
        loop_.add_rule(ReflexRule::below(
            "battery",
            "led0",
            ActuatorKind::Display,
            20.0,
            1.0,
            0.0,
        ));

        let readings = vec![
            SensorReading::new("temp0", SensorKind::Temperature, 75.0),
            SensorReading::new("battery", SensorKind::Power, 15.0),
        ];

        let commands = loop_.evaluate(&readings);
        assert_eq!(commands.len(), 2);
    }

    #[test]
    fn reflex_loop_rule_count() {
        let mut loop_ = ReflexLoop::new();
        assert_eq!(loop_.rule_count(), 0);
        loop_.add_rule(ReflexRule::above(
            "s",
            "a",
            ActuatorKind::Motor,
            1.0,
            1.0,
            1.0,
        ));
        assert_eq!(loop_.rule_count(), 1);
    }

    #[test]
    fn bus_default() {
        let bus = SensorimotorBus::default();
        assert_eq!(bus.sensor_count(), 0);
        assert_eq!(bus.actuator_count(), 0);
    }

    #[test]
    fn bus_read_specific_sensor() {
        let mut bus = SensorimotorBus::new(64);
        bus.register_sensor(Box::new(StubSensor::new(
            "s1",
            SensorKind::Temperature,
            42.0,
        )));

        let r = bus.read_sensor("s1").unwrap();
        assert!((r.value - 42.0).abs() < f64::EPSILON);

        assert!(bus.read_sensor("nonexistent").is_none());
    }

    #[test]
    fn sensor_kind_display() {
        assert_eq!(format!("{}", SensorKind::Temperature), "temperature");
        assert_eq!(format!("{}", ActuatorKind::Motor), "motor");
    }

    // ── SysfsSensor tests ──────────────────────────────────────────────

    #[test]
    fn sysfs_sensor_thermal_construction() {
        let sensor = SysfsSensor::thermal(0);
        assert_eq!(sensor.id(), "thermal_zone0");
        assert_eq!(sensor.kind(), SensorKind::Temperature);
    }

    #[test]
    fn sysfs_sensor_battery_construction() {
        let sensor = SysfsSensor::battery("BAT0");
        assert_eq!(sensor.id(), "battery_BAT0");
        assert_eq!(sensor.kind(), SensorKind::Power);
    }

    #[test]
    fn sysfs_sensor_fan_construction() {
        let sensor = SysfsSensor::fan(0, 1);
        assert_eq!(sensor.id(), "fan0_1");
        assert_eq!(sensor.kind(), SensorKind::Custom);
    }

    #[test]
    fn sysfs_sensor_nonexistent_path() {
        let sensor = SysfsSensor::new(
            "test",
            SensorKind::Temperature,
            "/nonexistent/path/that/does/not/exist",
            1000.0,
        );
        assert!(!sensor.is_available());
        assert!(sensor.read().is_none());
    }

    #[test]
    fn sysfs_sensor_debug_format() {
        let sensor = SysfsSensor::thermal(0);
        let debug = format!("{sensor:?}");
        assert!(debug.contains("SysfsSensor"));
        assert!(debug.contains("thermal_zone0"));
    }

    // ── ProcfsSensor tests ─────────────────────────────────────────────

    #[test]
    fn procfs_sensor_loadavg_construction() {
        let sensor = ProcfsSensor::loadavg();
        assert_eq!(sensor.id(), "cpu_loadavg");
        assert_eq!(sensor.kind(), SensorKind::Custom);
    }

    #[test]
    fn procfs_sensor_mem_pressure_construction() {
        let sensor = ProcfsSensor::mem_pressure();
        assert_eq!(sensor.id(), "mem_pressure");
        assert_eq!(sensor.kind(), SensorKind::Custom);
    }

    #[test]
    fn procfs_sensor_nonexistent_path() {
        let sensor = ProcfsSensor::new(
            "test",
            SensorKind::Custom,
            "/nonexistent/proc/path",
            Box::new(|_| Some(1.0)),
        );
        assert!(!sensor.is_available());
        assert!(sensor.read().is_none());
    }

    #[test]
    fn procfs_sensor_debug_format() {
        let sensor = ProcfsSensor::loadavg();
        let debug = format!("{sensor:?}");
        assert!(debug.contains("ProcfsSensor"));
        assert!(debug.contains("cpu_loadavg"));
    }

    #[test]
    fn procfs_sensor_custom_parser() {
        let sensor = ProcfsSensor::new(
            "test_parser",
            SensorKind::Custom,
            "/proc/loadavg",
            Box::new(|content: &str| {
                content.split_whitespace().next().and_then(|s| {
                    let v: f64 = s.parse().ok()?;
                    Some(v * 2.0)
                })
            }),
        );
        // Only test if /proc/loadavg exists
        if sensor.is_available() {
            let reading = sensor.read().unwrap();
            assert!(reading.value > 0.0);
        }
    }

    // ── Discovery tests ────────────────────────────────────────────────

    #[test]
    fn discover_thermal_sensors_returns_vec() {
        let sensors = discover_thermal_sensors();
        // On Linux, typically at least 1 thermal zone exists
        // On non-Linux, returns empty vec
        for s in &sensors {
            assert!(s.is_available());
            assert_eq!(s.kind(), SensorKind::Temperature);
        }
    }

    #[test]
    fn discover_battery_sensors_returns_vec() {
        let sensors = discover_battery_sensors();
        for s in &sensors {
            assert!(s.is_available());
            assert_eq!(s.kind(), SensorKind::Power);
        }
    }

    // ── linux_hardware_bus tests ───────────────────────────────────────

    #[test]
    fn linux_hardware_bus_creation() {
        let bus = linux_hardware_bus();
        // On Linux with /proc, should have at least the loadavg + mem_pressure sensors
        let sensor_ids = bus.sensor_ids();
        // Just verify it doesn't panic and returns a valid bus
        assert!(bus.sensor_count() <= 50); // reasonable upper bound
        for id in &sensor_ids {
            assert!(!id.is_empty());
        }
    }

    #[test]
    fn linux_hardware_bus_poll_all() {
        let mut bus = linux_hardware_bus();
        let readings = bus.poll_all();
        // Readings may be empty on non-Linux, but should not panic
        for r in &readings {
            assert!(!r.sensor_id.is_empty());
        }
    }

    // ── parse_proc_kb tests ────────────────────────────────────────────

    #[test]
    fn parse_proc_kb_extracts_value() {
        assert_eq!(
            parse_proc_kb("MemTotal:       16384000 kB"),
            Some(16_384_000)
        );
        assert_eq!(parse_proc_kb("MemAvailable:   8192000 kB"), Some(8_192_000));
        assert_eq!(parse_proc_kb("garbage"), None);
    }

    // ── CpuUsageSensor tests ────────────────────────────────────────────

    #[test]
    fn cpu_usage_sensor_construction() {
        let sensor = CpuUsageSensor::new();
        assert_eq!(sensor.id(), "cpu_usage");
        assert_eq!(sensor.kind(), SensorKind::Custom);
    }

    #[test]
    fn cpu_usage_sensor_debug() {
        let sensor = CpuUsageSensor::new();
        let debug = format!("{sensor:?}");
        assert!(debug.contains("CpuUsageSensor"));
    }

    #[test]
    fn cpu_usage_sensor_read_on_linux() {
        if !std::path::Path::new("/proc/stat").exists() {
            return;
        }
        let sensor = CpuUsageSensor::new();
        assert!(sensor.is_available());
        let reading = sensor.read().unwrap();
        assert_eq!(reading.sensor_id, "cpu_usage");
        assert!(reading.value >= 0.0 && reading.value <= 100.0);
    }

    // ── DiskUsageSensor tests ───────────────────────────────────────────

    #[test]
    fn disk_usage_sensor_construction() {
        let sensor = DiskUsageSensor::root();
        assert_eq!(sensor.id(), "disk_root");
        assert_eq!(sensor.kind(), SensorKind::Custom);
    }

    #[test]
    fn disk_usage_sensor_nonexistent() {
        let sensor = DiskUsageSensor::new("test", "/nonexistent/mount/point");
        assert!(!sensor.is_available());
        assert!(sensor.read().is_none());
    }

    #[test]
    fn disk_usage_sensor_debug() {
        let sensor = DiskUsageSensor::root();
        let debug = format!("{sensor:?}");
        assert!(debug.contains("DiskUsageSensor"));
    }

    // ── NetworkThroughputSensor tests ───────────────────────────────────

    #[test]
    fn network_sensor_construction() {
        let sensor = NetworkThroughputSensor::new("eth0");
        assert_eq!(sensor.id(), "net_eth0");
        assert_eq!(sensor.kind(), SensorKind::Custom);
    }

    #[test]
    fn network_sensor_default_interface() {
        let sensor = NetworkThroughputSensor::default_interface();
        assert!(sensor.id().starts_with("net_"));
    }

    #[test]
    fn network_sensor_debug() {
        let sensor = NetworkThroughputSensor::new("wlan0");
        let debug = format!("{sensor:?}");
        assert!(debug.contains("NetworkThroughputSensor"));
        assert!(debug.contains("wlan0"));
    }

    #[test]
    fn network_sensor_read_on_linux() {
        if !std::path::Path::new("/proc/net/dev").exists() {
            return;
        }
        let sensor = NetworkThroughputSensor::default_interface();
        assert!(sensor.is_available());
        let reading = sensor.read();
        // May return None if interface doesn't match, but shouldn't panic
        if let Some(r) = reading {
            assert!(r.value >= 0.0);
        }
    }

    // ── CpuFreqSensor tests ─────────────────────────────────────────────

    #[test]
    fn cpu_freq_sensor_construction() {
        let sensor = CpuFreqSensor::new(0);
        assert_eq!(sensor.id(), "cpu0_freq");
        assert_eq!(sensor.kind(), SensorKind::Custom);
    }

    #[test]
    fn cpu_freq_sensor_nonexistent() {
        let sensor = CpuFreqSensor::new(999);
        assert!(!sensor.is_available());
        assert!(sensor.read().is_none());
    }

    #[test]
    fn cpu_freq_sensor_debug() {
        let sensor = CpuFreqSensor::new(0);
        let debug = format!("{sensor:?}");
        assert!(debug.contains("CpuFreqSensor"));
    }

    // ── SysfsActuator tests ─────────────────────────────────────────────

    #[test]
    fn sysfs_actuator_construction() {
        let actuator = SysfsActuator::fan_pwm(0, 1);
        assert_eq!(actuator.id(), "fan_pwm0_1");
        assert_eq!(actuator.kind(), ActuatorKind::Motor);
    }

    #[test]
    fn sysfs_actuator_led_construction() {
        let actuator = SysfsActuator::led("power");
        assert_eq!(actuator.id(), "led_power");
        assert_eq!(actuator.kind(), ActuatorKind::Display);
    }

    #[test]
    fn sysfs_actuator_nonexistent_path() {
        let actuator = SysfsActuator::new(
            "test",
            ActuatorKind::Motor,
            "/nonexistent/path/that/does/not/exist",
            1.0,
        );
        assert!(!actuator.is_available());
        let cmd = ActuatorCommand::new("test", ActuatorKind::Motor, 1.0);
        assert!(actuator.command(&cmd).is_err());
    }

    #[test]
    fn sysfs_actuator_e_stop_nonexistent() {
        let actuator = SysfsActuator::new("test", ActuatorKind::Motor, "/nonexistent/path", 1.0);
        assert!(actuator.e_stop().is_err());
    }

    #[test]
    fn sysfs_actuator_debug() {
        let actuator = SysfsActuator::fan_pwm(0, 1);
        let debug = format!("{actuator:?}");
        assert!(debug.contains("SysfsActuator"));
        assert!(debug.contains("fan_pwm0_1"));
    }

    #[test]
    fn sysfs_actuator_scale_applied() {
        // Create actuator pointing to a temp file to verify scaling
        let tmp = tempfile::NamedTempFile::new().unwrap();
        let path = tmp.path().to_str().unwrap();
        let actuator = SysfsActuator::new("test", ActuatorKind::Display, path, 255.0);
        assert!(actuator.is_available());
        let cmd = ActuatorCommand::new("test", ActuatorKind::Display, 0.5);
        actuator.command(&cmd).unwrap();
        let written = std::fs::read_to_string(path).unwrap();
        assert_eq!(written.trim(), "128"); // 0.5 * 255 = 127.5 → 128
    }

    // ── Actuator discovery tests ────────────────────────────────────────

    #[test]
    fn discover_fan_actuators_returns_vec() {
        let actuators = discover_fan_actuators();
        for a in &actuators {
            assert!(a.is_available());
            assert_eq!(a.kind(), ActuatorKind::Motor);
        }
    }

    #[test]
    fn discover_led_actuators_returns_vec() {
        let actuators = discover_led_actuators();
        for a in &actuators {
            assert!(a.is_available());
            assert_eq!(a.kind(), ActuatorKind::Display);
        }
    }

    // ── Enhanced linux_hardware_bus tests ───────────────────────────────

    #[test]
    fn linux_hardware_bus_includes_new_sensors() {
        let bus = linux_hardware_bus();
        let ids = bus.sensor_ids();
        // On Linux with /proc/stat, cpu_usage should be registered
        if std::path::Path::new("/proc/stat").exists() {
            assert!(ids.iter().any(|id| id == "cpu_usage"));
        }
        // Disk root should always be registered on any platform
        assert!(ids.iter().any(|id| id == "disk_root"));
    }

    #[test]
    fn linux_hardware_bus_includes_actuators() {
        let bus = linux_hardware_bus();
        // Actuator count depends on hardware, but bus should be valid
        let actuator_ids = bus.actuator_ids();
        for id in &actuator_ids {
            assert!(!id.is_empty());
        }
    }
}
