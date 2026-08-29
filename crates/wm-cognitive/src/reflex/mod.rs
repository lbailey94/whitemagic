//! Reflex tier — sub-100µs dispatch for safety-critical loops.

pub mod builtins;
pub mod dispatch;
pub mod safety;
pub mod types;

pub use dispatch::{ReflexDispatchTable, ReflexHandler};
pub use safety::{SAFETY_ALLOW_ALL, SAFETY_DENY_ALL, SafetyBit};
pub use types::{ReflexArgs, ReflexCommand, ReflexError, ReflexId, ReflexOutput, SafetyMask};
