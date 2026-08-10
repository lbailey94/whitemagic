//! wm-sangha — Multi-agent coordination protocol (Sangha Mesh).
//!
//! **N17**: Implements the Sangha system — peer discovery, signal broadcast,
//! distributed resource locks, inter-agent chat, and holographic coordinate
//! synchronization. This is the "constellation layer" (CyberBrains Layer 6)
//! enabling multiple WhiteMagic nodes to coordinate.
//!
//! # Architecture
//!
//! - **[`peer`]** — Peer discovery, registry, health monitoring, capability advertisement
//! - **[`signal`]** — Signal broadcast (publish/subscribe), holographic signal sharing
//! - **[`lock`]** — Distributed resource lock manager (lease-based with TTL)
//! - **[`chat`]** — Inter-agent messaging with topic-based channels
//! - **[`hologram`]** — Holographic coordinate sync and constellation merging
//! - **[`transport`]** — Network transport (TCP JSON-RPC + UDP multicast discovery, feature-gated)
//!
//! With the `transport` feature, wm-sangha provides full network communication
//! via TCP (length-prefixed JSON-RPC) and UDP multicast peer discovery.
//! Without it, wm-sangha operates in single-node mode (in-process only).

#![forbid(unsafe_code)]

pub mod chat;
pub mod containment;
pub mod hologram;
pub mod lock;
pub mod peer;
pub mod radiant;
pub mod signal;

#[cfg(feature = "transport")]
pub mod transport;

pub use chat::{ChatChannel, ChatMessage, SanghaChat, VerificationReport};
pub use containment::{ContainmentReport, ContainmentResult, run, simulate_mesh_containment};
pub use hologram::{ConstellationMerge, HologramEntry, HologramSync};
pub use lock::{LockEntry, LockState, ResourceLockManager};
pub use peer::{PeerAuthority, PeerCapability, PeerDiscovery, PeerId, PeerInfo};
pub use radiant::{
    GiftToken, GiftTokenLedger, ResourceInventory, ResourceSnapshot, RoutingDecision, TaskRouter,
};
pub use signal::{Signal, SignalBroadcast, SignalType};

#[cfg(feature = "transport")]
pub use transport::{
    PeerAnnounce, RpcRequest, RpcResponse, SanghaState, SanghaTransport, TransportConfig,
    listen_for_beacons,
};
