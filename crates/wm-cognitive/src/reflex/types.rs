//! Reflex tier type definitions — stack-allocated, no heap.

use thiserror::Error;

/// Reflex handler ID (0–255). Used as direct array index into the dispatch table.
pub type ReflexId = u8;

/// Safety bitmask. Each bit corresponds to a capability in the `SafetyBit` enum.
/// A reflex handler is allowed to execute only if `(handler_mask & table_mask) == handler_mask`.
pub type SafetyMask = u32;

/// Reflex error — no allocation, returned on the stack.
#[derive(Debug, Clone, Error)]
pub enum ReflexError {
    /// No handler registered for this reflex ID.
    #[error("no handler registered for reflex id {0}")]
    NotRegistered(ReflexId),
    /// Handler's safety mask is not a subset of the table's allowlist.
    #[error("reflex blocked by safety mask: handler={handler_mask:#010x} table={table_mask:#010x}")]
    SafetyBlocked {
        /// The reflex ID that was blocked.
        id: ReflexId,
        /// The handler's required safety mask.
        handler_mask: SafetyMask,
        /// The table's current safety mask.
        table_mask: SafetyMask,
    },
    /// Handler returned an error.
    #[error("reflex {0} handler error: {1}")]
    HandlerFailed(ReflexId, String),
    /// Payload too large for the fixed buffer.
    #[error("payload too large: {0} bytes, max {1}")]
    PayloadTooLarge(usize, usize),
}

/// Actuator command type.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
#[derive(Default)]
pub enum ReflexCommand {
    /// Halt all actuators immediately.
    EmergencyStop = 0,
    /// Reduce power to safe level.
    ReducePower = 1,
    /// Apply correction (domain-specific payload).
    ApplyCorrection = 2,
    /// Issue alert (no physical actuation).
    IssueAlert = 3,
    /// Drop packet / reject request.
    Drop = 4,
    /// No action needed (pass-through).
    #[default]
    NoOp = 5,
    /// Custom command (payload defines action).
    Custom = 255,
}

/// Maximum payload size for reflex arguments.
pub const MAX_ARG_PAYLOAD: usize = 240;

/// Maximum payload size for reflex output.
pub const MAX_OUTPUT_PAYLOAD: usize = 120;

/// Stack-allocated reflex arguments — 256 bytes total, no heap.
///
/// Passed directly to the handler function pointer. The `payload` buffer
/// is a fixed-size array; `payload_len` indicates how many bytes are valid.
#[derive(Debug, Clone, Copy)]
#[repr(C)]
pub struct ReflexArgs {
    /// Timestamp in nanoseconds (from sensor or monotonic clock).
    pub timestamp_ns: u64,
    /// ID of the sensor that triggered this reflex.
    pub sensor_id: u16,
    /// Number of valid bytes in `payload`.
    pub payload_len: u8,
    /// Fixed payload buffer.
    pub payload: [u8; MAX_ARG_PAYLOAD],
}

impl Default for ReflexArgs {
    fn default() -> Self {
        Self {
            timestamp_ns: 0,
            sensor_id: 0,
            payload_len: 0,
            payload: [0u8; MAX_ARG_PAYLOAD],
        }
    }
}

impl ReflexArgs {
    /// Create a new `ReflexArgs` with the given sensor ID and timestamp.
    #[must_use]
    pub const fn new(sensor_id: u16, timestamp_ns: u64) -> Self {
        Self {
            timestamp_ns,
            sensor_id,
            payload_len: 0,
            payload: [0u8; MAX_ARG_PAYLOAD],
        }
    }

    /// Set the payload from a slice. Returns an error if the payload is too large.
    pub fn set_payload(&mut self, data: &[u8]) -> Result<(), ReflexError> {
        if data.len() > MAX_ARG_PAYLOAD {
            return Err(ReflexError::PayloadTooLarge(data.len(), MAX_ARG_PAYLOAD));
        }
        self.payload[..data.len()].copy_from_slice(data);
        self.payload_len = data.len() as u8;
        Ok(())
    }

    /// Get the valid payload bytes.
    #[must_use]
    pub fn payload(&self) -> &[u8] {
        &self.payload[..self.payload_len as usize]
    }
}

/// Stack-allocated reflex output — 128 bytes total, no heap.
///
/// Returned by the handler function pointer. Contains the actuator command
/// and any domain-specific payload.
#[derive(Debug, Clone, Copy)]
#[repr(C)]
pub struct ReflexOutput {
    /// ID of the target actuator.
    pub actuator_id: u16,
    /// Command to execute.
    pub command: ReflexCommand,
    /// Priority (0=lowest, 255=highest).
    pub priority: u8,
    /// Fixed payload buffer.
    pub payload: [u8; MAX_OUTPUT_PAYLOAD],
    /// Number of valid bytes in `payload`.
    pub payload_len: u8,
}

impl Default for ReflexOutput {
    fn default() -> Self {
        Self {
            actuator_id: 0,
            command: ReflexCommand::NoOp,
            priority: 0,
            payload: [0u8; MAX_OUTPUT_PAYLOAD],
            payload_len: 0,
        }
    }
}

impl ReflexOutput {
    /// Create a new `ReflexOutput` with the given actuator and command.
    #[must_use]
    pub const fn new(actuator_id: u16, command: ReflexCommand) -> Self {
        Self {
            actuator_id,
            command,
            priority: 0,
            payload: [0u8; MAX_OUTPUT_PAYLOAD],
            payload_len: 0,
        }
    }

    /// Set the payload from a slice. Returns an error if the payload is too large.
    pub fn set_payload(&mut self, data: &[u8]) -> Result<(), ReflexError> {
        if data.len() > MAX_OUTPUT_PAYLOAD {
            return Err(ReflexError::PayloadTooLarge(data.len(), MAX_OUTPUT_PAYLOAD));
        }
        self.payload[..data.len()].copy_from_slice(data);
        self.payload_len = data.len() as u8;
        Ok(())
    }

    /// Get the valid payload bytes.
    #[must_use]
    pub fn payload(&self) -> &[u8] {
        &self.payload[..self.payload_len as usize]
    }

    /// Create an emergency-stop output for the given actuator.
    #[must_use]
    pub const fn e_stop(actuator_id: u16) -> Self {
        Self::new(actuator_id, ReflexCommand::EmergencyStop).with_priority(255)
    }

    /// Create an alert output (no physical actuation).
    #[must_use]
    pub const fn alert(actuator_id: u16) -> Self {
        Self::new(actuator_id, ReflexCommand::IssueAlert)
    }

    /// Builder: set priority.
    #[must_use]
    pub const fn with_priority(mut self, priority: u8) -> Self {
        self.priority = priority;
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reflex_args_default() {
        let args = ReflexArgs::default();
        assert_eq!(args.sensor_id, 0);
        assert_eq!(args.timestamp_ns, 0);
        assert_eq!(args.payload_len, 0);
        assert!(args.payload().is_empty());
    }

    #[test]
    fn reflex_args_set_payload() {
        let mut args = ReflexArgs::new(42, 1_000_000);
        args.set_payload(b"hello").unwrap();
        assert_eq!(args.payload_len, 5);
        assert_eq!(args.payload(), b"hello");
    }

    #[test]
    fn reflex_args_payload_too_large() {
        let mut args = ReflexArgs::default();
        let big = vec![0u8; MAX_ARG_PAYLOAD + 1];
        let err = args.set_payload(&big).unwrap_err();
        assert!(matches!(err, ReflexError::PayloadTooLarge(_, _)));
    }

    #[test]
    fn reflex_args_max_payload() {
        let mut args = ReflexArgs::default();
        let exact = vec![0xABu8; MAX_ARG_PAYLOAD];
        args.set_payload(&exact).unwrap();
        assert_eq!(args.payload_len as usize, MAX_ARG_PAYLOAD);
        assert_eq!(args.payload(), &exact[..]);
    }

    #[test]
    fn reflex_output_e_stop() {
        let out = ReflexOutput::e_stop(7);
        assert_eq!(out.actuator_id, 7);
        assert_eq!(out.command, ReflexCommand::EmergencyStop);
        assert_eq!(out.priority, 255);
    }

    #[test]
    fn reflex_output_alert() {
        let out = ReflexOutput::alert(3);
        assert_eq!(out.command, ReflexCommand::IssueAlert);
        assert_eq!(out.priority, 0);
    }

    #[test]
    fn reflex_output_set_payload() {
        let mut out = ReflexOutput::new(1, ReflexCommand::ApplyCorrection);
        out.set_payload(b"correct").unwrap();
        assert_eq!(out.payload(), b"correct");
    }

    #[test]
    fn reflex_output_payload_too_large() {
        let mut out = ReflexOutput::default();
        let big = vec![0u8; MAX_OUTPUT_PAYLOAD + 1];
        let err = out.set_payload(&big).unwrap_err();
        assert!(matches!(err, ReflexError::PayloadTooLarge(_, _)));
    }

    #[test]
    fn reflex_command_default_is_noop() {
        assert_eq!(ReflexCommand::default(), ReflexCommand::NoOp);
    }

    #[test]
    fn reflex_args_size_no_heap() {
        // Field order: u64 (8) + u16 (2) + u8 (1) + [u8; 240] = 251, padded to 256
        // (repr(C) alignment is 8 due to u64, array has align 1 so no internal pad)
        let size = std::mem::size_of::<ReflexArgs>();
        assert!(size <= 256, "ReflexArgs is {size} bytes, expected <= 256");
    }

    #[test]
    fn reflex_output_size_no_heap() {
        // ReflexOutput: 2 + 1 + 1 + 120 + 1 = 125, padded to 128
        let size = std::mem::size_of::<ReflexOutput>();
        assert!(size <= 128, "ReflexOutput is {size} bytes, expected <= 128");
    }
}
