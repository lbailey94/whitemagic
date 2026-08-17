//! WhiteMagic v5 MCP — Model Context Protocol server
//!
//! Pure Rust JSON-RPC over stdio. Exposes a single `wm` fractal tool
//! that auto-routes to all internal tools.
//!
//! With the `python` feature, also provides PyO3 bindings for use as a
//! Python extension module (`whitemagic_v5`).

// wm-mcp has an FFI boundary (PyO3 bridge), so we use `deny` instead of
// `forbid` — the pyo3_bridge module can locally allow unsafe for PyO3 macros.
#![deny(unsafe_code)]

pub mod config;
pub mod cyberbrain;
pub mod daemon;
pub mod input_validation;
pub mod migrate;
pub mod seal;
mod server;

#[cfg(test)]
mod effect_audit;

pub use input_validation::{
    DEFAULT_MAX_REQUESTS_PER_SESSION, DEFAULT_RATE_LIMIT_RPM, MAX_PARAMS_SIZE, MAX_REQUEST_SIZE,
    MAX_STRING_LEN, RateWindow, RequestBudget, ValidationResult, validate_request,
    validate_tool_call_params, validate_tools_call,
};
pub use server::McpServer;

#[cfg(feature = "python")]
pub mod pyo3_bridge;
