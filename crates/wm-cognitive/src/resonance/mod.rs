//! wm-resonance — Gan Ying Bus (感應) — full system resonance event bus.
//!
//! "Things that accord in tone vibrate together" — the Gan Ying Bus is
//! WhiteMagic v5's internal event resonance system, connecting all
//! subsystems through 229 event types across 9 categories.
//!
//! # Architecture
//!
//! - **[`event_type`]** — 229 event types in 9 categories
//! - **[`bus`]** — subscribe/emit/cascade event bus
//! - **[`nervous_system`]** — Unified Nervous System (7 biological subsystems)
//! - **[`synchronicity`]** — Synchronicity Detector (meaningful coincidence detection)
//!
//! # Quick Start
//!
//! ```no_run
//! use wm_cognitive::{GanYingBus, EventType, EventCategory, SubscriptionFilter, ResonanceEvent};
//!
//! let mut bus = GanYingBus::default();
//!
//! // Subscribe to all memory events
//! let _id = bus.subscribe(
//!     SubscriptionFilter::Category(EventCategory::Memory),
//!     Box::new(|event: &ResonanceEvent| {
//!         println!("Memory event: {}", event.event_type);
//!     }),
//! );
//!
//! // Emit with cascade
//! bus.emit_with(EventType::MemoryCreated, "test", serde_json::json!({"id": 42}), 0.8, true);
//! ```

#![forbid(unsafe_code)]

pub mod bus;
pub mod event_type;
pub mod nervous_system;
pub mod synchronicity;

// Re-exports
pub use bus::{
    BusStats, EventCallback, GanYingBus, MAX_CASCADE_DEPTH, ResonanceEvent, SubscriptionFilter,
    SubscriptionId, default_cascade_rules,
};
pub use event_type::{EventCategory, EventType};
pub use nervous_system::{NervousSubsystem, SubsystemHealth, UnifiedNervousSystem};
pub use synchronicity::{Synchronicity, SynchronicityConfig, SynchronicityDetector};
