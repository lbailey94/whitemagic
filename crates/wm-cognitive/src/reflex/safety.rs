//! Safety bitmask system for the reflex tier.
//!
//! Each reflex handler declares a safety mask specifying which capabilities
//! it requires. The dispatch table has a global allowlist mask. A handler
//! is allowed to execute only if `(handler_mask & table_mask) == handler_mask`.
//!
//! This is a single AND instruction at runtime — no governance pipeline,
//! no Dharma evaluation, no karma ledger. Just a bitmask check.

use crate::reflex::types::SafetyMask;

/// Safety capability bits. Each bit in the `SafetyMask` corresponds to one
/// of these capabilities. A handler's mask must be a subset of the table's
/// allowlist mask for the handler to execute.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u32)]
pub enum SafetyBit {
    /// Emergency stop — highest priority, always allowed
    EmergencyStop = 1 << 0,
    /// Actuator control (motors, relays, magnets)
    ActuatorControl = 1 << 1,
    /// Sensor reading
    SensorRead = 1 << 2,
    /// Network packet dropping
    PacketDrop = 1 << 3,
    /// Alert issuance (no physical actuation)
    IssueAlert = 1 << 4,
    /// Power reduction
    PowerReduction = 1 << 5,
    /// Beam dump (particle physics)
    BeamDump = 1 << 6,
    /// Correction application (QEC, orbit, etc.)
    ApplyCorrection = 1 << 7,
    /// System reset
    SystemReset = 1 << 8,
    /// External communication (send data out)
    ExternalComm = 1 << 9,
    /// Log to gnosis audit trail
    GnosisLog = 1 << 10,
    /// Read system state
    StateRead = 1 << 11,
    /// Modify safety parameters
    ModifySafety = 1 << 12,
    /// Trigger fallback procedure
    TriggerFallback = 1 << 13,
    /// Hardware watchdog interaction
    Watchdog = 1 << 14,
    /// Calibration adjustment
    Calibrate = 1 << 15,
}

impl SafetyBit {
    /// Convert this bit to a `SafetyMask`.
    #[must_use]
    pub const fn mask(self) -> SafetyMask {
        self as u32
    }
}

/// Allow all capabilities — use only in testing or fully trusted environments.
pub const SAFETY_ALLOW_ALL: SafetyMask = 0xFFFF_FFFF;

/// Deny all capabilities — no reflex can execute.
pub const SAFETY_DENY_ALL: SafetyMask = 0x0000_0000;

/// Default safety mask for production.
///
/// Allows emergency stop, sensor read, issue alert, power reduction,
/// gnosis log, state read, and trigger fallback. Does NOT allow actuator
/// control, packet drop, beam dump, correction, system reset, external
/// comm, modify safety, watchdog, or calibration without explicit opt-in.
pub const SAFETY_DEFAULT: SafetyMask = SafetyBit::EmergencyStop.mask()
    | SafetyBit::SensorRead.mask()
    | SafetyBit::IssueAlert.mask()
    | SafetyBit::PowerReduction.mask()
    | SafetyBit::GnosisLog.mask()
    | SafetyBit::StateRead.mask()
    | SafetyBit::TriggerFallback.mask();

/// Check if a handler's required mask is allowed by the table's allowlist mask.
///
/// This is the core safety check: `(handler_mask & table_mask) == handler_mask`.
/// It's a single AND + compare — no function calls, no allocation.
#[must_use]
pub const fn is_allowed(handler_mask: SafetyMask, table_mask: SafetyMask) -> bool {
    (handler_mask & table_mask) == handler_mask
}

/// Combine multiple `SafetyBit`s into a single mask.
#[must_use]
pub const fn combine(bits: &[SafetyBit]) -> SafetyMask {
    let mut mask: SafetyMask = 0;
    let mut i = 0;
    while i < bits.len() {
        mask |= bits[i].mask();
        i += 1;
    }
    mask
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn allow_all_permits_everything() {
        assert!(is_allowed(
            SafetyBit::ActuatorControl.mask(),
            SAFETY_ALLOW_ALL
        ));
        assert!(is_allowed(0xFFFF_FFFF, SAFETY_ALLOW_ALL));
    }

    #[test]
    fn deny_all_blocks_everything() {
        assert!(!is_allowed(
            SafetyBit::EmergencyStop.mask(),
            SAFETY_DENY_ALL
        ));
        assert!(!is_allowed(0x1, SAFETY_DENY_ALL));
    }

    #[test]
    fn default_allows_emergency_stop() {
        assert!(is_allowed(SafetyBit::EmergencyStop.mask(), SAFETY_DEFAULT));
    }

    #[test]
    fn default_blocks_actuator_control() {
        assert!(!is_allowed(
            SafetyBit::ActuatorControl.mask(),
            SAFETY_DEFAULT
        ));
    }

    #[test]
    fn default_allows_sensor_read() {
        assert!(is_allowed(SafetyBit::SensorRead.mask(), SAFETY_DEFAULT));
    }

    #[test]
    fn default_blocks_beam_dump() {
        assert!(!is_allowed(SafetyBit::BeamDump.mask(), SAFETY_DEFAULT));
    }

    #[test]
    fn default_allows_power_reduction() {
        assert!(is_allowed(SafetyBit::PowerReduction.mask(), SAFETY_DEFAULT));
    }

    #[test]
    fn combine_multiple_bits() {
        let mask = combine(&[
            SafetyBit::EmergencyStop,
            SafetyBit::SensorRead,
            SafetyBit::IssueAlert,
        ]);
        assert!(is_allowed(mask, SAFETY_DEFAULT));
    }

    #[test]
    fn combine_with_blocked_bit() {
        let mask = combine(&[SafetyBit::SensorRead, SafetyBit::ActuatorControl]);
        assert!(!is_allowed(mask, SAFETY_DEFAULT));
    }

    #[test]
    fn is_allowed_const_eval() {
        // Verify the check is const-evaluable (no runtime overhead)
        const RESULT: bool = is_allowed(SafetyBit::EmergencyStop.mask(), SAFETY_DEFAULT);
        const { assert!(RESULT) };
    }

    #[test]
    fn subset_mask_allowed() {
        // If handler requires bits 0+2 and table has bits 0+1+2+3, allowed
        let handler = SafetyBit::EmergencyStop.mask() | SafetyBit::SensorRead.mask();
        let table = SafetyBit::EmergencyStop.mask()
            | SafetyBit::ActuatorControl.mask()
            | SafetyBit::SensorRead.mask()
            | SafetyBit::PacketDrop.mask();
        assert!(is_allowed(handler, table));
    }

    #[test]
    fn non_subset_mask_blocked() {
        // If handler requires bit 1 (ActuatorControl) and table doesn't have it, blocked
        let handler = SafetyBit::ActuatorControl.mask();
        let table = SafetyBit::EmergencyStop.mask() | SafetyBit::SensorRead.mask();
        assert!(!is_allowed(handler, table));
    }
}
