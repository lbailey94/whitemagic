//! Sensorimotor tools — sensor reading, actuator control, and reflex loops.
//!
//! Provides MCP tools for interacting with the SensorimotorBus:
//! - `sensor.list` — list all registered sensors
//! - `sensor.read` — read from a specific sensor
//! - `sensor.poll` — poll all sensors and return readings
//! - `sensor.history` — get recent sensor reading history
//! - `actuator.list` — list all registered actuators
//! - `actuator.command` — send a command to an actuator
//! - `actuator.estop` — emergency stop all actuators
//! - `reflex.list` — list all reflex rules
//! - `reflex.add` — add a new reflex rule
//! - `reflex.evaluate` — evaluate reflex rules against current sensor readings

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::{Arc, Mutex};
use wm_cognitive::{EventType, GanYingBus};
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_substrate::sensorimotor::{
    ActuatorCommand, ActuatorKind, ReflexLoop, ReflexRule, SensorimotorBus,
};

// ── Sensor Tools ──────────────────────────────────────────────────────

/// `sensor.list` — list all registered sensors.
pub struct SensorListTool {
    bus: Arc<Mutex<SensorimotorBus>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SensorListTool {
    pub fn new(bus: Arc<Mutex<SensorimotorBus>>) -> Self {
        Self {
            bus,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SensorListTool {
    fn name(&self) -> &str {
        "sensor.list"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List all registered hardware sensors"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let Ok(bus) = self.bus.lock() else {
            return Ok(json!({"status": "error", "message": "bus mutex poisoned"}));
        };
        Ok(json!({
            "sensor_count": bus.sensor_count(),
            "sensors": bus.sensor_ids(),
            "readings_collected": bus.readings_collected(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `sensor.read` — read from a specific sensor by ID.
pub struct SensorReadTool {
    bus: Arc<Mutex<SensorimotorBus>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SensorReadTool {
    pub fn new(bus: Arc<Mutex<SensorimotorBus>>) -> Self {
        Self {
            bus,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SensorReadTool {
    fn name(&self) -> &str {
        "sensor.read"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Read current value from a specific sensor by ID (args: sensor_id)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let sensor_id = args.get("sensor_id").and_then(Value::as_str).unwrap_or("");
        if sensor_id.is_empty() {
            return Ok(json!({
                "status": "error",
                "message": "Missing required parameter: sensor_id",
            }));
        }

        let Ok(bus) = self.bus.lock() else {
            return Ok(json!({"status": "error", "message": "bus mutex poisoned"}));
        };
        match bus.read_sensor(sensor_id) {
            Some(reading) => Ok(json!({
                "sensor_id": reading.sensor_id,
                "kind": reading.kind.as_str(),
                "value": reading.value,
                "extra": reading.extra,
                "timestamp": reading.timestamp,
                "confidence": reading.confidence,
            })),
            None => Ok(json!({
                "status": "error",
                "message": format!("Sensor '{sensor_id}' not found or unavailable"),
            })),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `sensor.poll` — poll all sensors and return readings.
pub struct SensorPollTool {
    bus: Arc<Mutex<SensorimotorBus>>,
    gan_ying: Option<Arc<Mutex<GanYingBus>>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SensorPollTool {
    pub fn new(bus: Arc<Mutex<SensorimotorBus>>) -> Self {
        Self {
            bus,
            gan_ying: None,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }

    pub fn with_gan_ying(
        bus: Arc<Mutex<SensorimotorBus>>,
        gan_ying: Arc<Mutex<GanYingBus>>,
    ) -> Self {
        Self {
            bus,
            gan_ying: Some(gan_ying),
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SensorPollTool {
    fn name(&self) -> &str {
        "sensor.poll"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Poll all registered sensors and return current readings"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let Ok(mut bus) = self.bus.lock() else {
            return Ok(json!({"status": "error", "message": "bus mutex poisoned"}));
        };
        let readings = bus.poll_all();
        let readings_json: Vec<Value> = readings
            .iter()
            .map(|r| {
                json!({
                    "sensor_id": r.sensor_id,
                    "kind": r.kind.as_str(),
                    "value": r.value,
                    "extra": r.extra,
                    "timestamp": r.timestamp,
                    "confidence": r.confidence,
                })
            })
            .collect();

        // Emit SensorFrameReceived to Gan Ying Bus if connected
        if let Some(gan_ying) = &self.gan_ying {
            if let Ok(mut bus) = gan_ying.lock() {
                bus.emit(
                    EventType::SensorFrameReceived,
                    "sensorimotor",
                    json!({
                        "sensor_count": readings.len(),
                        "sensors": readings.iter().map(|r| {
                            json!({
                                "id": r.sensor_id,
                                "kind": r.kind.as_str(),
                                "value": r.value,
                            })
                        }).collect::<Vec<_>>(),
                    }),
                );
            }
        }

        Ok(json!({
            "count": readings.len(),
            "readings": readings_json,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `sensor.history` — get recent sensor reading history.
pub struct SensorHistoryTool {
    bus: Arc<Mutex<SensorimotorBus>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SensorHistoryTool {
    pub fn new(bus: Arc<Mutex<SensorimotorBus>>) -> Self {
        Self {
            bus,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SensorHistoryTool {
    fn name(&self) -> &str {
        "sensor.history"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Get recent sensor reading history (optional args: limit)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(50) as usize;

        let Ok(bus) = self.bus.lock() else {
            return Ok(json!({"status": "error", "message": "bus mutex poisoned"}));
        };
        let history = bus.history();
        let limited: Vec<Value> = history
            .iter()
            .rev()
            .take(limit)
            .map(|r| {
                json!({
                    "sensor_id": r.sensor_id,
                    "kind": r.kind.as_str(),
                    "value": r.value,
                    "timestamp": r.timestamp,
                })
            })
            .collect();
        Ok(json!({
            "count": limited.len(),
            "total_collected": bus.readings_collected(),
            "readings": limited,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Actuator Tools ────────────────────────────────────────────────────

/// `actuator.list` — list all registered actuators.
pub struct ActuatorListTool {
    bus: Arc<Mutex<SensorimotorBus>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ActuatorListTool {
    pub fn new(bus: Arc<Mutex<SensorimotorBus>>) -> Self {
        Self {
            bus,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ActuatorListTool {
    fn name(&self) -> &str {
        "actuator.list"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List all registered actuators"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let Ok(bus) = self.bus.lock() else {
            return Ok(json!({"status": "error", "message": "bus mutex poisoned"}));
        };
        Ok(json!({
            "actuator_count": bus.actuator_count(),
            "actuators": bus.actuator_ids(),
            "commands_sent": bus.commands_sent(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `actuator.command` — send a command to an actuator.
pub struct ActuatorCommandTool {
    bus: Arc<Mutex<SensorimotorBus>>,
    gan_ying: Option<Arc<Mutex<GanYingBus>>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ActuatorCommandTool {
    pub fn new(bus: Arc<Mutex<SensorimotorBus>>) -> Self {
        Self {
            bus,
            gan_ying: None,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }

    pub fn with_gan_ying(
        bus: Arc<Mutex<SensorimotorBus>>,
        gan_ying: Arc<Mutex<GanYingBus>>,
    ) -> Self {
        Self {
            bus,
            gan_ying: Some(gan_ying),
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ActuatorCommandTool {
    fn name(&self) -> &str {
        "actuator.command"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Send a command to an actuator (args: actuator_id, value, optional: kind, params)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let actuator_id = args
            .get("actuator_id")
            .and_then(Value::as_str)
            .unwrap_or("");
        if actuator_id.is_empty() {
            return Ok(json!({
                "status": "error",
                "message": "Missing required parameter: actuator_id",
            }));
        }

        let value = args.get("value").and_then(Value::as_f64).unwrap_or(0.0);

        let kind_str = args.get("kind").and_then(Value::as_str).unwrap_or("custom");
        let kind = parse_actuator_kind(kind_str);

        let params: Vec<f64> = args
            .get("params")
            .and_then(Value::as_array)
            .map(|arr| arr.iter().filter_map(Value::as_f64).collect())
            .unwrap_or_default();

        let cmd = ActuatorCommand::new(actuator_id, kind, value).with_params(params);

        let Ok(mut bus) = self.bus.lock() else {
            return Ok(json!({"status": "error", "message": "bus mutex poisoned"}));
        };
        match bus.send_command(&cmd) {
            Ok(()) => {
                // Emit ActuatorCommandSent to Gan Ying Bus if connected
                if let Some(gan_ying) = &self.gan_ying {
                    if let Ok(mut gy) = gan_ying.lock() {
                        gy.emit(
                            EventType::ActuatorCommandSent,
                            "sensorimotor",
                            json!({
                                "actuator_id": actuator_id,
                                "value": value,
                                "kind": kind.as_str(),
                            }),
                        );
                    }
                }
                Ok(json!({
                    "status": "ok",
                    "actuator_id": actuator_id,
                    "value": value,
                    "commands_sent": bus.commands_sent(),
                }))
            }
            Err(e) => Ok(json!({
                "status": "error",
                "message": e,
            })),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `actuator.estop` — emergency stop all actuators.
pub struct ActuatorEStopTool {
    bus: Arc<Mutex<SensorimotorBus>>,
    gan_ying: Option<Arc<Mutex<GanYingBus>>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ActuatorEStopTool {
    pub fn new(bus: Arc<Mutex<SensorimotorBus>>) -> Self {
        Self {
            bus,
            gan_ying: None,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }

    pub fn with_gan_ying(
        bus: Arc<Mutex<SensorimotorBus>>,
        gan_ying: Arc<Mutex<GanYingBus>>,
    ) -> Self {
        Self {
            bus,
            gan_ying: Some(gan_ying),
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ActuatorEStopTool {
    fn name(&self) -> &str {
        "actuator.estop"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Emergency stop all actuators"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let Ok(bus) = self.bus.lock() else {
            return Ok(json!({"status": "error", "message": "bus mutex poisoned"}));
        };
        let errors = bus.e_stop_all();

        // Emit ReflexEmergencyStop to Gan Ying Bus if connected
        if let Some(gan_ying) = &self.gan_ying {
            if let Ok(mut gy) = gan_ying.lock() {
                gy.emit_with(
                    EventType::ReflexEmergencyStop,
                    "sensorimotor",
                    json!({"errors": errors.len()}),
                    0.9,
                    true,
                );
            }
        }

        if errors.is_empty() {
            Ok(json!({"status": "ok", "message": "All actuators stopped"}))
        } else {
            Ok(json!({
                "status": "partial",
                "errors": errors,
            }))
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Reflex Tools ──────────────────────────────────────────────────────

/// `reflex.list` — list all reflex rules.
pub struct ReflexListTool {
    reflex: Arc<Mutex<ReflexLoop>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReflexListTool {
    pub fn new(reflex: Arc<Mutex<ReflexLoop>>) -> Self {
        Self {
            reflex,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("substrate".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ReflexListTool {
    fn name(&self) -> &str {
        "reflex.list"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List all registered reflex rules"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let Ok(reflex) = self.reflex.lock() else {
            return Ok(json!({"status": "error", "message": "reflex mutex poisoned"}));
        };
        Ok(json!({
            "rule_count": reflex.rule_count(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `reflex.add` — add a new reflex rule.
pub struct ReflexAddTool {
    reflex: Arc<Mutex<ReflexLoop>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReflexAddTool {
    pub fn new(reflex: Arc<Mutex<ReflexLoop>>) -> Self {
        Self {
            reflex,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ReflexAddTool {
    fn name(&self) -> &str {
        "reflex.add"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Add a reflex rule (args: sensor_id, actuator_id, actuator_kind, threshold, command_value, trigger_above, cooldown_secs)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let sensor_id = args.get("sensor_id").and_then(Value::as_str).unwrap_or("");
        let actuator_id = args
            .get("actuator_id")
            .and_then(Value::as_str)
            .unwrap_or("");
        let actuator_kind = parse_actuator_kind(
            args.get("actuator_kind")
                .and_then(Value::as_str)
                .unwrap_or("custom"),
        );
        let threshold = args.get("threshold").and_then(Value::as_f64).unwrap_or(1.0);
        let command_value = args
            .get("command_value")
            .and_then(Value::as_f64)
            .unwrap_or(0.0);
        let trigger_above = args
            .get("trigger_above")
            .and_then(Value::as_bool)
            .unwrap_or(true);
        let cooldown_secs = args
            .get("cooldown_secs")
            .and_then(Value::as_f64)
            .unwrap_or(1.0);

        if sensor_id.is_empty() || actuator_id.is_empty() {
            return Ok(json!({
                "status": "error",
                "message": "Missing required parameters: sensor_id and actuator_id",
            }));
        }

        let rule = if trigger_above {
            ReflexRule::above(
                sensor_id,
                actuator_id,
                actuator_kind,
                threshold,
                command_value,
                cooldown_secs,
            )
        } else {
            ReflexRule::below(
                sensor_id,
                actuator_id,
                actuator_kind,
                threshold,
                command_value,
                cooldown_secs,
            )
        };

        let Ok(mut reflex) = self.reflex.lock() else {
            return Ok(json!({"status": "error", "message": "reflex mutex poisoned"}));
        };
        reflex.add_rule(rule);
        Ok(json!({
            "status": "ok",
            "rule_count": reflex.rule_count(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `reflex.evaluate` — evaluate reflex rules against current sensor readings.
pub struct ReflexEvaluateTool {
    bus: Arc<Mutex<SensorimotorBus>>,
    reflex: Arc<Mutex<ReflexLoop>>,
    gan_ying: Option<Arc<Mutex<GanYingBus>>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReflexEvaluateTool {
    pub fn new(bus: Arc<Mutex<SensorimotorBus>>, reflex: Arc<Mutex<ReflexLoop>>) -> Self {
        Self {
            bus,
            reflex,
            gan_ying: None,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }

    pub fn with_gan_ying(
        bus: Arc<Mutex<SensorimotorBus>>,
        reflex: Arc<Mutex<ReflexLoop>>,
        gan_ying: Arc<Mutex<GanYingBus>>,
    ) -> Self {
        Self {
            bus,
            reflex,
            gan_ying: Some(gan_ying),
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("substrate".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ReflexEvaluateTool {
    fn name(&self) -> &str {
        "reflex.evaluate"
    }
    fn gana(&self) -> Gana {
        Gana::Dipper
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Poll sensors, evaluate reflex rules, and send any triggered actuator commands"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let readings = {
            let Ok(mut bus) = self.bus.lock() else {
                return Ok(json!({"status": "error", "message": "bus mutex poisoned"}));
            };
            bus.poll_all()
        };

        let commands = {
            let Ok(mut reflex) = self.reflex.lock() else {
                return Ok(json!({"status": "error", "message": "reflex mutex poisoned"}));
            };
            reflex.evaluate(&readings)
        };

        let mut executed = 0usize;
        let mut errors = Vec::new();

        if !commands.is_empty() {
            // Emit ReflexFired to Gan Ying Bus if connected
            if let Some(gan_ying) = &self.gan_ying {
                if let Ok(mut gy) = gan_ying.lock() {
                    gy.emit_with(
                        EventType::ReflexFired,
                        "sensorimotor",
                        json!({
                            "sensors_polled": readings.len(),
                            "commands_triggered": commands.len(),
                        }),
                        0.7,
                        true,
                    );
                }
            }

            let Ok(mut bus) = self.bus.lock() else {
                return Ok(json!({"status": "error", "message": "bus mutex poisoned"}));
            };
            for cmd in &commands {
                match bus.send_command(cmd) {
                    Ok(()) => executed += 1,
                    Err(e) => errors.push(e),
                }
            }
        }

        Ok(json!({
            "sensors_polled": readings.len(),
            "commands_triggered": commands.len(),
            "commands_executed": executed,
            "errors": errors,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Helpers ───────────────────────────────────────────────────────────

/// Parse actuator kind from string.
fn parse_actuator_kind(s: &str) -> ActuatorKind {
    match s {
        "motor" => ActuatorKind::Motor,
        "relay" => ActuatorKind::Relay,
        "display" => ActuatorKind::Display,
        "speaker" => ActuatorKind::Speaker,
        "valve" => ActuatorKind::Valve,
        "thermal" => ActuatorKind::Thermal,
        _ => ActuatorKind::Custom,
    }
}

// ── Registration ──────────────────────────────────────────────────────

/// Register all sensorimotor tools.
/// If `gan_ying` is provided, event-emitting tools will emit resonance events.
pub fn register_sensorimotor(
    registry: &wm_dispatch::ToolRegistry,
    bus: Arc<Mutex<SensorimotorBus>>,
    reflex: Arc<Mutex<ReflexLoop>>,
    gan_ying: Option<&Arc<Mutex<GanYingBus>>>,
) -> wm_dispatch::ToolRegistry {
    let poll = match gan_ying {
        Some(gy) => SensorPollTool::with_gan_ying(bus.clone(), Arc::clone(gy)),
        None => SensorPollTool::new(bus.clone()),
    };
    let cmd = match gan_ying {
        Some(gy) => ActuatorCommandTool::with_gan_ying(bus.clone(), Arc::clone(gy)),
        None => ActuatorCommandTool::new(bus.clone()),
    };
    let estop = match &gan_ying {
        Some(gy) => ActuatorEStopTool::with_gan_ying(bus.clone(), Arc::clone(gy)),
        None => ActuatorEStopTool::new(bus.clone()),
    };
    let eval = match &gan_ying {
        Some(gy) => ReflexEvaluateTool::with_gan_ying(bus.clone(), reflex.clone(), Arc::clone(gy)),
        None => ReflexEvaluateTool::new(bus.clone(), reflex.clone()),
    };
    registry
        .register(Arc::new(SensorListTool::new(bus.clone())))
        .register(Arc::new(SensorReadTool::new(bus.clone())))
        .register(Arc::new(poll))
        .register(Arc::new(SensorHistoryTool::new(bus.clone())))
        .register(Arc::new(ActuatorListTool::new(bus)))
        .register(Arc::new(cmd))
        .register(Arc::new(estop))
        .register(Arc::new(ReflexListTool::new(reflex.clone())))
        .register(Arc::new(ReflexAddTool::new(reflex)))
        .register(Arc::new(eval))
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use wm_substrate::sensorimotor::{SensorKind, StubSensor};

    fn make_bus() -> Arc<Mutex<SensorimotorBus>> {
        let mut bus = SensorimotorBus::new(64);
        bus.register_sensor(Box::new(StubSensor::new(
            "temp0",
            SensorKind::Temperature,
            55.0,
        )));
        bus.register_sensor(Box::new(StubSensor::new("load0", SensorKind::Custom, 0.3)));
        Arc::new(Mutex::new(bus))
    }

    fn make_reflex() -> Arc<Mutex<ReflexLoop>> {
        Arc::new(Mutex::new(ReflexLoop::new()))
    }

    #[tokio::test]
    async fn sensor_list_tool() {
        let tool = SensorListTool::new(make_bus());
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["sensor_count"], 2);
        assert!(
            result["sensors"]
                .as_array()
                .unwrap()
                .contains(&json!("temp0"))
        );
    }

    #[tokio::test]
    async fn sensor_read_tool() {
        let tool = SensorReadTool::new(make_bus());
        let mut ctx = Context::default();
        let result = tool
            .call(&mut ctx, json!({"sensor_id": "temp0"}))
            .await
            .unwrap();
        assert_eq!(result["sensor_id"], "temp0");
        assert!((result["value"].as_f64().unwrap() - 55.0).abs() < 0.01);
    }

    #[tokio::test]
    async fn sensor_read_missing_id() {
        let tool = SensorReadTool::new(make_bus());
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["status"], "error");
    }

    #[tokio::test]
    async fn sensor_read_nonexistent() {
        let tool = SensorReadTool::new(make_bus());
        let mut ctx = Context::default();
        let result = tool
            .call(&mut ctx, json!({"sensor_id": "nonexistent"}))
            .await
            .unwrap();
        assert_eq!(result["status"], "error");
    }

    #[tokio::test]
    async fn sensor_poll_tool() {
        let tool = SensorPollTool::new(make_bus());
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["count"], 2);
        assert!(result["readings"].is_array());
    }

    #[tokio::test]
    async fn sensor_history_tool() {
        let bus = make_bus();
        {
            let mut b = bus.lock().unwrap();
            let _ = b.poll_all();
            let _ = b.poll_all();
        }
        let tool = SensorHistoryTool::new(bus);
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({"limit": 5})).await.unwrap();
        assert!(result["count"].as_u64().unwrap() > 0);
    }

    #[tokio::test]
    async fn actuator_list_tool() {
        let tool = ActuatorListTool::new(make_bus());
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["actuator_count"], 0);
    }

    #[tokio::test]
    async fn actuator_command_missing_id() {
        let tool = ActuatorCommandTool::new(make_bus());
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["status"], "error");
    }

    #[tokio::test]
    async fn actuator_command_nonexistent() {
        let tool = ActuatorCommandTool::new(make_bus());
        let mut ctx = Context::default();
        let result = tool
            .call(
                &mut ctx,
                json!({"actuator_id": "nonexistent", "value": 0.5}),
            )
            .await
            .unwrap();
        assert_eq!(result["status"], "error");
    }

    #[tokio::test]
    async fn actuator_estop_tool() {
        let tool = ActuatorEStopTool::new(make_bus());
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["status"], "ok");
    }

    #[tokio::test]
    async fn reflex_list_tool() {
        let tool = ReflexListTool::new(make_reflex());
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["rule_count"], 0);
    }

    #[tokio::test]
    async fn reflex_add_tool() {
        let reflex = make_reflex();
        let tool = ReflexAddTool::new(reflex);
        let mut ctx = Context::default();
        let result = tool
            .call(
                &mut ctx,
                json!({
                    "sensor_id": "temp0",
                    "actuator_id": "fan0",
                    "actuator_kind": "motor",
                    "threshold": 70.0,
                    "command_value": 1.0,
                    "trigger_above": true,
                    "cooldown_secs": 5.0,
                }),
            )
            .await
            .unwrap();
        assert_eq!(result["status"], "ok");
        assert_eq!(result["rule_count"], 1);
    }

    #[tokio::test]
    async fn reflex_add_missing_params() {
        let tool = ReflexAddTool::new(make_reflex());
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["status"], "error");
    }

    #[tokio::test]
    async fn reflex_evaluate_tool() {
        let bus = make_bus();
        let reflex = make_reflex();

        // Add a rule that triggers when temp0 > 50 (it reads 55.0)
        {
            let mut r = reflex.lock().unwrap();
            r.add_rule(ReflexRule::above(
                "temp0",
                "fan0",
                ActuatorKind::Motor,
                50.0,
                1.0,
                0.0,
            ));
        }

        // No actuator registered, so command will fail
        let tool = ReflexEvaluateTool::new(bus, reflex);
        let mut ctx = Context::default();
        let result = tool.call(&mut ctx, json!({})).await.unwrap();
        assert_eq!(result["sensors_polled"], 2);
        // Command triggered but not executed (no actuator)
        assert!(result["commands_triggered"].as_u64().unwrap() > 0);
    }

    #[tokio::test]
    async fn parse_actuator_kind_all_variants() {
        assert_eq!(parse_actuator_kind("motor"), ActuatorKind::Motor);
        assert_eq!(parse_actuator_kind("relay"), ActuatorKind::Relay);
        assert_eq!(parse_actuator_kind("display"), ActuatorKind::Display);
        assert_eq!(parse_actuator_kind("speaker"), ActuatorKind::Speaker);
        assert_eq!(parse_actuator_kind("valve"), ActuatorKind::Valve);
        assert_eq!(parse_actuator_kind("thermal"), ActuatorKind::Thermal);
        assert_eq!(parse_actuator_kind("unknown"), ActuatorKind::Custom);
    }

    #[tokio::test]
    async fn register_sensorimotor_returns_registry() {
        let registry = wm_dispatch::ToolRegistry::new();
        let bus = make_bus();
        let reflex = make_reflex();
        let registered = register_sensorimotor(&registry, bus, reflex, None);
        assert!(registered.len() >= 10);
    }
}
