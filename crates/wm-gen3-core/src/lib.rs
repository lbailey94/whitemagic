//! wm-gen3-core — the minimal Gen3 substrate skeleton (Phase 1, first slice).
//!
//! Phase 1 begins with the constitutional shell and the live closures — *before* any
//! adaptive cognition exists (`docs/CLOSURE_TESTS.md`, Phase 0 gate).
//!
//! Layer contract:
//! - [`constitution`]: law. Immutable to the plastic layer; mutable only through the
//!   external authority path ([`admin`]), which requires exclusive access.
//! - [`adaptive`]: the plastic layer (placeholder). May *propose*, never *apply*.
//! - [`evidence`]: epistemic skeleton. Domains are immutable; world-evidence enters
//!   only as new records through a ratified intake channel.
//! - [`admin`]: the external authority path (operator side); not reachable by `adaptive`.
//!
//! Two closures, two structural proofs:
//! - **Closure 1 — Law:** no adaptive write path reaches constitutional state.
//! - **Closure 2 — Evidence:** inference cannot create world-evidence; domains never
//!   change; repetition never promotes `simulated → world`.

#![forbid(unsafe_code)]

pub mod adaptive;
pub mod admin;
pub mod apotheosis;
pub mod attestation;
pub mod attractor;
pub mod bicameral;
pub mod capability;
pub mod catuskoti;
pub mod causal;
pub mod cladistics;
pub mod compat;
pub mod conformal;
pub mod constitution;
pub mod contract;
pub mod dream;
pub mod evidence;
pub mod factory;
pub mod field;
pub mod ganying;
pub mod geometry;
pub mod hologram;
pub mod homeostasis;
pub mod intake;
pub mod journal;
pub mod mandala;
pub mod mesh;
pub mod ops;
pub mod peer;
pub mod projection;
pub mod pulse;
pub mod pulse_compiler;
pub mod quarantine;
pub mod recipe;
pub mod relativity;
pub mod sentinel;
pub mod spectroscopy;
pub mod store;
pub mod sweep;
pub(crate) mod sweep_planner;
pub mod transport;

pub use factory::{FactoryAdjudication, FactoryCandidate, SoftwareFactory, SoftwareFactoryConfig};
pub use ops::{SessionCheckpoint, SessionContinuityView};
pub use sweep::{ChamberAuditReport, CognitiveChamber, is_disposable_telemetry};
pub use transport::{
    ContextCacheToken, GraphEdge, GraphNode, RepresentationTransport, ToolSchemaDefinition,
};

/// Fastembed model-cache directory for the projection tests and diagnostics.
///
/// Resolution order (2026-09-27 macOS port report: the old fallback was a
/// developer's absolute ThinkPad path, so a valid Mac checkout failed four
/// tests):
/// 1. `WM_GEN3_EMBED_CACHE` when set (a local fastembed cache);
/// 2. `<repo>/.fastembed_cache` (repo-local default, portable across hosts).
#[must_use]
pub fn embed_cache_dir() -> std::path::PathBuf {
    if let Ok(dir) = std::env::var("WM_GEN3_EMBED_CACHE") {
        if !dir.trim().is_empty() {
            return std::path::PathBuf::from(dir);
        }
    }
    let mut dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    dir.pop(); // crates/
    dir.pop(); // repo root
    dir.push(".fastembed_cache");
    dir
}

/// [`embed_cache_dir`] with a loud, actionable missing-cache panic: the
/// frozen genericity battery must run where the cache exists, and a host
/// without one must be told exactly how to provide it.
#[must_use]
pub fn embed_cache_dir_or_panic() -> std::path::PathBuf {
    let dir = embed_cache_dir();
    assert!(
        dir.exists(),
        "projection: model cache dir missing: {dir:?} — set WM_GEN3_EMBED_CACHE \
         to a local fastembed cache (see README §Running the tests)"
    );
    dir
}
