//! WhiteMagic Gen3 — Harness and Hybrid Contract Bridge library.

#![forbid(unsafe_code)]
#![recursion_limit = "512"]

pub mod bridge;

#[cfg(feature = "systemone")]
pub mod decision_receipt;

#[cfg(feature = "system05")]
pub mod shortlist_receipt;

#[cfg(any(feature = "systemone", feature = "system05"))]
pub mod receipt_verify;

pub mod deliberation;
pub mod grimoire;
pub mod starter_galaxy;
