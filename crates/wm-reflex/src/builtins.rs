//! Built-in reflex handlers — ready-to-use safety-critical reflexes.
//!
//! These are pre-compiled handler functions that can be registered into
//! a `ReflexDispatchTable`. Each handler is a pure function pointer with
//! no heap allocation.

use crate::dispatch::ReflexHandler;
use crate::safety::SafetyBit;
use crate::types::{ReflexArgs, ReflexCommand, ReflexError, ReflexId, ReflexOutput};

/// Built-in reflex IDs.
pub mod ids {
    use super::ReflexId;

    /// Emergency stop — halt all actuators.
    pub const E_STOP: ReflexId = 0;
    /// Collision avoidance — brake or redirect.
    pub const COLLISION_AVOID: ReflexId = 1;
    /// Thermal limit — reduce power.
    pub const THERMAL_LIMIT: ReflexId = 2;
    /// Frequency deviation — trigger correction (power grid).
    pub const FREQ_DEVIATION: ReflexId = 3;
    /// Beam instability — beam dump (particle physics).
    pub const BEAM_INSTABILITY: ReflexId = 4;
    /// P-wave detection — issue alert (seismic).
    pub const PWAVE_DETECT: ReflexId = 5;
    /// Packet drop — drop + log (cybersecurity).
    pub const PACKET_DROP: ReflexId = 6;
    /// QEC correction — apply quantum error correction.
    pub const QEC_CORRECT: ReflexId = 7;
}

/// Emergency stop handler. Halt all actuators immediately.
pub const fn e_stop(_args: &ReflexArgs) -> Result<ReflexOutput, ReflexError> {
    Ok(ReflexOutput::e_stop(0).with_priority(255))
}

/// Collision avoidance handler. Issues brake command.
pub const fn collision_avoid(_args: &ReflexArgs) -> Result<ReflexOutput, ReflexError> {
    Ok(ReflexOutput::new(0, ReflexCommand::EmergencyStop).with_priority(200))
}

/// Thermal limit handler. Reduces power to safe level.
pub const fn thermal_limit(_args: &ReflexArgs) -> Result<ReflexOutput, ReflexError> {
    Ok(ReflexOutput::new(0, ReflexCommand::ReducePower).with_priority(180))
}

/// Frequency deviation handler. Triggers correction.
pub const fn freq_deviation(_args: &ReflexArgs) -> Result<ReflexOutput, ReflexError> {
    Ok(ReflexOutput::new(0, ReflexCommand::ApplyCorrection).with_priority(150))
}

/// Beam instability handler. Triggers beam dump.
pub const fn beam_instability(_args: &ReflexArgs) -> Result<ReflexOutput, ReflexError> {
    Ok(ReflexOutput::new(0, ReflexCommand::EmergencyStop).with_priority(250))
}

/// P-wave detection handler. Issues seismic alert.
pub const fn pwave_detect(_args: &ReflexArgs) -> Result<ReflexOutput, ReflexError> {
    Ok(ReflexOutput::alert(0).with_priority(160))
}

/// Packet drop handler. Drops the packet.
pub const fn packet_drop(_args: &ReflexArgs) -> Result<ReflexOutput, ReflexError> {
    Ok(ReflexOutput::new(0, ReflexCommand::Drop).with_priority(100))
}

/// QEC correction handler. Applies quantum error correction.
pub const fn qec_correct(_args: &ReflexArgs) -> Result<ReflexOutput, ReflexError> {
    Ok(ReflexOutput::new(0, ReflexCommand::ApplyCorrection).with_priority(220))
}

/// A descriptor for a built-in reflex.
pub struct BuiltinReflex {
    /// Reflex ID.
    pub id: ReflexId,
    /// Name of the reflex.
    pub name: &'static str,
    /// The handler function pointer.
    pub handler: ReflexHandler,
    /// Required safety bit.
    pub safety_bit: SafetyBit,
}

/// All built-in reflexes.
pub static BUILTINS: &[BuiltinReflex] = &[
    BuiltinReflex {
        id: ids::E_STOP,
        name: "e_stop",
        handler: e_stop,
        safety_bit: SafetyBit::EmergencyStop,
    },
    BuiltinReflex {
        id: ids::COLLISION_AVOID,
        name: "collision_avoid",
        handler: collision_avoid,
        safety_bit: SafetyBit::ActuatorControl,
    },
    BuiltinReflex {
        id: ids::THERMAL_LIMIT,
        name: "thermal_limit",
        handler: thermal_limit,
        safety_bit: SafetyBit::PowerReduction,
    },
    BuiltinReflex {
        id: ids::FREQ_DEVIATION,
        name: "freq_deviation",
        handler: freq_deviation,
        safety_bit: SafetyBit::ApplyCorrection,
    },
    BuiltinReflex {
        id: ids::BEAM_INSTABILITY,
        name: "beam_instability",
        handler: beam_instability,
        safety_bit: SafetyBit::BeamDump,
    },
    BuiltinReflex {
        id: ids::PWAVE_DETECT,
        name: "pwave_detect",
        handler: pwave_detect,
        safety_bit: SafetyBit::IssueAlert,
    },
    BuiltinReflex {
        id: ids::PACKET_DROP,
        name: "packet_drop",
        handler: packet_drop,
        safety_bit: SafetyBit::PacketDrop,
    },
    BuiltinReflex {
        id: ids::QEC_CORRECT,
        name: "qec_correct",
        handler: qec_correct,
        safety_bit: SafetyBit::ApplyCorrection,
    },
];

/// Register all built-in reflexes into a dispatch table.
///
/// Only registers reflexes whose safety bit is allowed by the table's
/// current safety mask. This allows selective registration based on
/// the deployment context.
pub fn register_builtins(table: &mut crate::ReflexDispatchTable) {
    for builtin in BUILTINS {
        table.register_with_bit(builtin.id, builtin.handler, builtin.safety_bit);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dispatch::ReflexDispatchTable;
    #[test]
    fn e_stop_returns_emergency_stop() {
        let args = ReflexArgs::default();
        let out = e_stop(&args).unwrap();
        assert_eq!(out.command, ReflexCommand::EmergencyStop);
        assert_eq!(out.priority, 255);
    }

    #[test]
    fn collision_avoid_returns_emergency_stop() {
        let args = ReflexArgs::default();
        let out = collision_avoid(&args).unwrap();
        assert_eq!(out.command, ReflexCommand::EmergencyStop);
        assert_eq!(out.priority, 200);
    }

    #[test]
    fn thermal_limit_returns_reduce_power() {
        let args = ReflexArgs::default();
        let out = thermal_limit(&args).unwrap();
        assert_eq!(out.command, ReflexCommand::ReducePower);
    }

    #[test]
    fn freq_deviation_returns_correction() {
        let args = ReflexArgs::default();
        let out = freq_deviation(&args).unwrap();
        assert_eq!(out.command, ReflexCommand::ApplyCorrection);
    }

    #[test]
    fn beam_instability_returns_emergency_stop() {
        let args = ReflexArgs::default();
        let out = beam_instability(&args).unwrap();
        assert_eq!(out.command, ReflexCommand::EmergencyStop);
        assert_eq!(out.priority, 250);
    }

    #[test]
    fn pwave_detect_returns_alert() {
        let args = ReflexArgs::default();
        let out = pwave_detect(&args).unwrap();
        assert_eq!(out.command, ReflexCommand::IssueAlert);
    }

    #[test]
    fn packet_drop_returns_drop() {
        let args = ReflexArgs::default();
        let out = packet_drop(&args).unwrap();
        assert_eq!(out.command, ReflexCommand::Drop);
    }

    #[test]
    fn qec_correct_returns_correction() {
        let args = ReflexArgs::default();
        let out = qec_correct(&args).unwrap();
        assert_eq!(out.command, ReflexCommand::ApplyCorrection);
        assert_eq!(out.priority, 220);
    }

    #[test]
    fn register_builtins_all() {
        let mut table = ReflexDispatchTable::permissive();
        register_builtins(&mut table);
        assert_eq!(table.registered_count(), 8);
    }

    #[test]
    fn register_builtins_dispatch_all() {
        let mut table = ReflexDispatchTable::permissive();
        register_builtins(&mut table);
        let args = ReflexArgs::default();

        for builtin in BUILTINS {
            let result = table.dispatch(builtin.id, &args);
            assert!(result.is_ok(), "dispatch failed for {}", builtin.name);
        }
    }

    #[test]
    fn builtins_count() {
        assert_eq!(BUILTINS.len(), 8);
    }

    #[test]
    fn builtins_ids_unique() {
        let ids: Vec<_> = BUILTINS.iter().map(|b| b.id).collect();
        let unique: std::collections::HashSet<_> = ids.iter().collect();
        assert_eq!(
            ids.len(),
            unique.len(),
            "built-in reflex IDs must be unique"
        );
    }
}
