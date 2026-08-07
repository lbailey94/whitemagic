//! WhiteMagic v4 Reflex Tier — Sub-100µs dispatch for safety-critical loops.
//!
//! The reflex tier bypasses the entire cognitive pipeline (NLU, Dharma, rate
//! limiter, circuit breaker, karma) and executes via a pre-compiled dispatch
//! table with direct function pointers. The only safety check is a single
//! bitmask AND against a pre-compiled allowlist.
//!
//! Design constraints:
//! - No trait objects (`dyn Tool`) — direct function pointers
//! - No heap allocation — stack-allocated `ReflexArgs` / `ReflexOutput`
//! - No serde — fixed-layout structs with `#[repr(C)]`
//! - No governance pipeline — bitmask safety check only
//! - Reflex tools cannot call cognitive tools (no upward calls)

#![forbid(unsafe_code)]

pub mod builtins;
pub mod dispatch;
pub mod safety;
pub mod types;

pub use dispatch::{ReflexDispatchTable, ReflexHandler};
pub use safety::{SAFETY_ALLOW_ALL, SAFETY_DENY_ALL, SafetyBit};
pub use types::{ReflexArgs, ReflexCommand, ReflexError, ReflexId, ReflexOutput, SafetyMask};
