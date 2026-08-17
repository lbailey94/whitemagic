//! `WhiteMagic` v4 Core — Types, Traits, and Gana Taxonomy
//!
//! This crate defines the foundational types shared across all `WhiteMagic`
//! subsystems: the 28 Gana enum, effect rows, tool traits, brain-wave states,
//! and core error types.

#![forbid(unsafe_code)]

pub mod attestation;
pub mod brain_wave;
pub mod context;
pub mod coords;
pub mod effects;
pub mod episodic;
pub mod error;
pub mod galaxy;
pub mod gana;
pub mod mutable;
pub mod security;
pub mod tool;

pub use attestation::{sign_hmac, verify_hmac};
pub use brain_wave::BrainWave;
pub use context::Context;
pub use coords::{Coordinate5D, HolographicCoords, Zone, find_nearby};
pub use effects::{Capability, CostEstimate, EffectRow, Resource};
pub use episodic::{
    EPISODIC_SCHEMA_VERSION, EpisodicId, EpisodicKind, EpisodicRecord, EvidenceRef,
    EvidenceRelation, MemoryTransition, Provenance, ProvenanceSource, ValidityState,
    ValidityTransitionError,
};
pub use error::{CoreError, Result};
pub use galaxy::Galaxy;
pub use gana::Gana;
pub use mutable::{
    CycleEffectiveness, CycleStrategy, DynamicGalaxy, DynamicGalaxyRegistry, GanaMerge,
    GanaRegistry, LearnedCycleStrategy, LearnedDreamCycle, PhaseEffectiveness,
};
pub use tool::{Args, Output, Tool, ToolStats, ToolStatsSnapshot};
