//! WhiteMagic Gen3 — Harness and Hybrid Contract Bridge library.

#![forbid(unsafe_code)]
#![recursion_limit = "512"]

pub mod bridge;
pub mod host_guard;
pub mod host_health;
pub mod mcp_server;

#[cfg(feature = "systemone")]
pub mod decision_receipt;

#[cfg(feature = "system05")]
pub mod shortlist_receipt;

pub mod receipt_verify;

pub mod deliberation;
pub mod grimoire;
pub mod starter_galaxy;
pub mod systemtwo;
