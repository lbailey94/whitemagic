//! WhiteMagic v4 wm-polyglot — Polyglot language bridges.
//!
//! Provides a unified interface for calling functions in Julia, Haskell,
//! Zig, and Koka from the WhiteMagic runtime. All language backends
//! implement the `PolyglotBackend` trait and are managed by a
//! `PolyglotRegistry`.
//!
//! ## Architecture
//!
//! - `value::PolyglotValue` — cross-language data representation
//! - `backend::PolyglotBackend` — trait for language runtimes
//! - `backend::PolyglotRegistry` — manages multiple backends
//! - `cabi::CabiBackend` — C ABI backend (Zig, Koka, Haskell)
//! - `julia::JuliaBackend` — Julia runtime via jlrs (requires `julia` feature)
//! - `tool::PolyglotTool` — WhiteMagic `Tool` wrapper for dispatch pipeline
//!
//! ## Usage
//!
//! ```no_run
//! use wm_polyglot::{PolyglotRegistry, cabi::zig_backend, tool::PolyglotTool};
//! use std::sync::{Arc, Mutex};
//!
//! let mut registry = PolyglotRegistry::new();
//! registry.register(Box::new(zig_backend()));
//! let registry = Arc::new(Mutex::new(registry));
//! let tool = PolyglotTool::new(registry);
//! ```

// unsafe_code is allowed in this crate (Cargo.toml lints.rust)
// The C ABI backend requires unsafe for FFI library loading and function calls.

pub mod backend;
pub mod cabi;
pub mod julia;
pub mod tool;
pub mod value;

pub use backend::{PolyglotBackend, PolyglotRegistry};
pub use cabi::{CabiBackend, haskell_backend, koka_backend, zig_backend};
pub use julia::JuliaBackend;
pub use tool::PolyglotTool;
pub use value::{PolyglotError, PolyglotValue};
