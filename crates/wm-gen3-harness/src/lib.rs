//! WhiteMagic Gen3 — Harness and Hybrid Contract Bridge library.

#![forbid(unsafe_code)]
#![recursion_limit = "512"]

pub mod bridge;

#[cfg(feature = "systemone")]
pub mod decision_receipt;
