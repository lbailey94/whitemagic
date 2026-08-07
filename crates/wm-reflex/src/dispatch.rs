//! Reflex dispatch table — pre-compiled function pointer lookup.
//!
//! The dispatch table is a fixed-size array of 256 handler slots, indexed
//! by `ReflexId` (u8). Each slot contains an optional handler function
//! pointer and its required safety mask.
//!
//! Dispatch is O(1): array index → bitmask AND → function call.
//! No hash lookup, no trait dispatch, no allocation.

use crate::safety::{SAFETY_DEFAULT, SafetyBit, is_allowed};
use crate::types::{ReflexArgs, ReflexError, ReflexId, ReflexOutput, SafetyMask};
use std::time::Instant;

/// A reflex handler function pointer. Takes stack-allocated args, returns
/// stack-allocated output. No heap allocation in the handler path.
pub type ReflexHandler = fn(&ReflexArgs) -> Result<ReflexOutput, ReflexError>;

/// A registered reflex handler entry.
#[derive(Clone, Copy)]
struct HandlerEntry {
    handler: ReflexHandler,
    required_mask: SafetyMask,
}

impl std::fmt::Debug for HandlerEntry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("HandlerEntry")
            .field(
                "required_mask",
                &format_args!("{:#010x}", self.required_mask),
            )
            .finish_non_exhaustive()
    }
}

/// Pre-compiled reflex dispatch table.
///
/// Contains up to 256 handler slots indexed by `ReflexId`. The table has
/// a global safety allowlist mask that controls which handlers are permitted
/// to execute.
///
/// # Dispatch Path
///
/// 1. Look up handler by `reflex_id` (array index — O(1))
/// 2. Check `(handler.required_mask & table.safety_mask) == handler.required_mask`
/// 3. Call `handler.handler(&args)` — direct function pointer, no vtable
/// 4. Return `ReflexOutput`
///
/// No heap allocation, no hash lookup, no trait dispatch.
pub struct ReflexDispatchTable {
    handlers: [Option<HandlerEntry>; 256],
    safety_mask: SafetyMask,
    dispatch_count: u64,
}

impl std::fmt::Debug for ReflexDispatchTable {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ReflexDispatchTable")
            .field("safety_mask", &format_args!("{:#010x}", self.safety_mask))
            .field("dispatch_count", &self.dispatch_count)
            .field("registered_count", &self.registered_count())
            .finish_non_exhaustive()
    }
}

impl Default for ReflexDispatchTable {
    fn default() -> Self {
        Self::new(SAFETY_DEFAULT)
    }
}

impl ReflexDispatchTable {
    /// Create a new dispatch table with the given safety allowlist mask.
    #[must_use]
    pub fn new(safety_mask: SafetyMask) -> Self {
        Self {
            handlers: std::array::from_fn(|_| None),
            safety_mask,
            dispatch_count: 0,
        }
    }

    /// Create a dispatch table that allows all safety bits (testing only).
    #[must_use]
    pub fn permissive() -> Self {
        Self::new(crate::safety::SAFETY_ALLOW_ALL)
    }

    /// Register a handler at the given reflex ID with its required safety mask.
    ///
    /// If a handler is already registered at this ID, it is replaced.
    /// A warning is logged to alert developers of potential rule injection.
    pub fn register(&mut self, id: ReflexId, handler: ReflexHandler, required_mask: SafetyMask) {
        if self.handlers[id as usize].is_some() {
            tracing::warn!(
                reflex_id = id,
                "Re-registering handler at occupied slot — previous handler replaced"
            );
        }
        self.handlers[id as usize] = Some(HandlerEntry {
            handler,
            required_mask,
        });
    }

    /// Register a handler with a single safety bit.
    pub fn register_with_bit(&mut self, id: ReflexId, handler: ReflexHandler, bit: SafetyBit) {
        self.register(id, handler, bit.mask());
    }

    /// Unregister a handler at the given reflex ID.
    pub const fn unregister(&mut self, id: ReflexId) {
        self.handlers[id as usize] = None;
    }

    /// Update the safety allowlist mask. This takes effect immediately for
    /// all subsequent dispatches.
    pub const fn set_safety_mask(&mut self, mask: SafetyMask) {
        self.safety_mask = mask;
    }

    /// Get the current safety allowlist mask.
    #[must_use]
    pub const fn safety_mask(&self) -> SafetyMask {
        self.safety_mask
    }

    /// Get the total number of dispatches since table creation.
    #[must_use]
    pub const fn dispatch_count(&self) -> u64 {
        self.dispatch_count
    }

    /// Count the number of registered handlers.
    #[must_use]
    pub fn registered_count(&self) -> usize {
        self.handlers.iter().filter(|h| h.is_some()).count()
    }

    /// Check if a handler is registered at the given ID.
    #[must_use]
    pub const fn is_registered(&self, id: ReflexId) -> bool {
        self.handlers[id as usize].is_some()
    }

    /// Dispatch a reflex call. This is the hot path — O(1) array index +
    /// bitmask AND + function call. No heap allocation.
    ///
    /// # Errors
    ///
    /// Returns `ReflexError::NotRegistered` if no handler is at this ID.
    /// Returns `ReflexError::SafetyBlocked` if the handler's required mask
    /// is not a subset of the table's allowlist.
    /// Returns `ReflexError::HandlerFailed` if the handler returns an error.
    pub fn dispatch(
        &mut self,
        id: ReflexId,
        args: &ReflexArgs,
    ) -> Result<ReflexOutput, ReflexError> {
        self.dispatch_count += 1;

        let entry = self.handlers[id as usize].ok_or(ReflexError::NotRegistered(id))?;

        if !is_allowed(entry.required_mask, self.safety_mask) {
            return Err(ReflexError::SafetyBlocked {
                id,
                handler_mask: entry.required_mask,
                table_mask: self.safety_mask,
            });
        }

        (entry.handler)(args).map_err(|e| match e {
            ReflexError::HandlerFailed(_, _) => ReflexError::HandlerFailed(id, e.to_string()),
            other => other,
        })
    }

    /// Dispatch with timing. Returns the output and the dispatch duration.
    /// Useful for benchmarks and latency monitoring.
    pub fn dispatch_timed(
        &mut self,
        id: ReflexId,
        args: &ReflexArgs,
    ) -> (Result<ReflexOutput, ReflexError>, std::time::Duration) {
        let start = Instant::now();
        let result = self.dispatch(id, args);
        (result, start.elapsed())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{ReflexCommand, ReflexOutput};

    fn ok_handler(_args: &ReflexArgs) -> Result<ReflexOutput, ReflexError> {
        Ok(ReflexOutput::new(1, ReflexCommand::NoOp))
    }

    fn fail_handler(_args: &ReflexArgs) -> Result<ReflexOutput, ReflexError> {
        Err(ReflexError::HandlerFailed(99, "test failure".to_string()))
    }

    fn e_stop_handler(_args: &ReflexArgs) -> Result<ReflexOutput, ReflexError> {
        Ok(ReflexOutput::e_stop(1))
    }

    #[test]
    fn register_and_dispatch() {
        let mut table = ReflexDispatchTable::permissive();
        table.register(0, ok_handler, 0);
        let args = ReflexArgs::default();
        let result = table.dispatch(0, &args).unwrap();
        assert_eq!(result.command, ReflexCommand::NoOp);
        assert_eq!(table.dispatch_count(), 1);
    }

    #[test]
    fn dispatch_unregistered() {
        let mut table = ReflexDispatchTable::permissive();
        let args = ReflexArgs::default();
        let err = table.dispatch(42, &args).unwrap_err();
        assert!(matches!(err, ReflexError::NotRegistered(42)));
    }

    #[test]
    fn safety_blocked() {
        let mut table = ReflexDispatchTable::new(SAFETY_DEFAULT);
        // Register a handler that requires ActuatorControl (not in default mask)
        table.register(5, ok_handler, SafetyBit::ActuatorControl.mask());
        let args = ReflexArgs::default();
        let err = table.dispatch(5, &args).unwrap_err();
        assert!(matches!(err, ReflexError::SafetyBlocked { .. }));
    }

    #[test]
    fn safety_allowed_emergency_stop() {
        let mut table = ReflexDispatchTable::new(SAFETY_DEFAULT);
        table.register(0, e_stop_handler, SafetyBit::EmergencyStop.mask());
        let args = ReflexArgs::default();
        let result = table.dispatch(0, &args).unwrap();
        assert_eq!(result.command, ReflexCommand::EmergencyStop);
    }

    #[test]
    fn handler_failure_propagates() {
        let mut table = ReflexDispatchTable::permissive();
        table.register(10, fail_handler, 0);
        let args = ReflexArgs::default();
        let err = table.dispatch(10, &args).unwrap_err();
        assert!(matches!(err, ReflexError::HandlerFailed(_, _)));
    }

    #[test]
    fn unregister_handler() {
        let mut table = ReflexDispatchTable::permissive();
        table.register(3, ok_handler, 0);
        assert!(table.is_registered(3));
        table.unregister(3);
        assert!(!table.is_registered(3));
        let args = ReflexArgs::default();
        assert!(matches!(
            table.dispatch(3, &args).unwrap_err(),
            ReflexError::NotRegistered(3)
        ));
    }

    #[test]
    fn replace_handler() {
        let mut table = ReflexDispatchTable::permissive();
        table.register(1, ok_handler, 0);
        table.register(1, e_stop_handler, 0);
        let args = ReflexArgs::default();
        let result = table.dispatch(1, &args).unwrap();
        assert_eq!(result.command, ReflexCommand::EmergencyStop);
    }

    #[test]
    fn set_safety_mask_dynamically() {
        let mut table = ReflexDispatchTable::new(SAFETY_DEFAULT);
        table.register(0, ok_handler, SafetyBit::ActuatorControl.mask());
        let args = ReflexArgs::default();

        // Blocked by default
        assert!(table.dispatch(0, &args).is_err());

        // Allow actuator control
        table.set_safety_mask(table.safety_mask() | SafetyBit::ActuatorControl.mask());
        assert!(table.dispatch(0, &args).is_ok());
    }

    #[test]
    fn dispatch_timed() {
        let mut table = ReflexDispatchTable::permissive();
        table.register(0, ok_handler, 0);
        let args = ReflexArgs::default();
        let (result, duration) = table.dispatch_timed(0, &args);
        assert!(result.is_ok());
        // Should be well under 100µs
        assert!(
            duration.as_micros() < 100,
            "dispatch took {duration:?}, expected <100µs"
        );
    }

    #[test]
    fn registered_count() {
        let mut table = ReflexDispatchTable::permissive();
        assert_eq!(table.registered_count(), 0);
        table.register(0, ok_handler, 0);
        table.register(1, ok_handler, 0);
        table.register(2, ok_handler, 0);
        assert_eq!(table.registered_count(), 3);
        table.unregister(1);
        assert_eq!(table.registered_count(), 2);
    }

    #[test]
    fn register_with_bit() {
        let mut table = ReflexDispatchTable::permissive();
        table.register_with_bit(0, ok_handler, SafetyBit::SensorRead);
        assert!(table.is_registered(0));
        let args = ReflexArgs::default();
        assert!(table.dispatch(0, &args).is_ok());
    }

    #[test]
    fn default_safety_mask() {
        let table = ReflexDispatchTable::default();
        assert_eq!(table.safety_mask(), SAFETY_DEFAULT);
    }

    #[test]
    fn dispatch_count_increments() {
        let mut table = ReflexDispatchTable::permissive();
        table.register(0, ok_handler, 0);
        let args = ReflexArgs::default();
        for _ in 0..100 {
            let _ = table.dispatch(0, &args);
        }
        assert_eq!(table.dispatch_count(), 100);
    }

    #[test]
    fn re_registering_handler_replaces_silently() {
        let mut table = ReflexDispatchTable::permissive();
        table.register(0, ok_handler, 0);
        assert!(table.is_registered(0));
        // Re-register — should replace, not crash
        table.register(0, ok_handler, 0);
        assert!(table.is_registered(0));
        assert_eq!(table.registered_count(), 1);
    }
}
