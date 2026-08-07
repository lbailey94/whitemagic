//! WhiteMagic v4 Global Workspace Bus — salience-based multi-objective arbitration.
//!
//! All cognitive cores publish state events to the workspace. The workspace
//! arbitrates attention: whichever core has the highest salience score wins
//! the "spotlight" for the next decision cycle.
//!
//! Design:
//! - Salience scoring: multiplicative (urgency × novelty × confidence)
//! - Spotlight decay: 0.5^(age / half_life), half_life defaults to 5s
//! - High-salience events (>0.8 composite) preempt the current spotlight
//! - Event bus: tokio::sync::broadcast channel for multiple subscribers
//! - Event backlog: ring buffer of last 256 events

#![forbid(unsafe_code)]

pub mod bus;
pub mod event;
pub mod salience;
pub mod spotlight;

pub use bus::{GlobalWorkspace, WorkspaceError, WorkspaceStats};
pub use event::{CoreId, EventType, WorkspaceEvent};
pub use salience::Salience;
pub use spotlight::{Spotlight, SpotlightEntry};
