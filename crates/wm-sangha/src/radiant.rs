//! Radiant Layer — surplus resource routing across mesh nodes.
//!
//! **N18**: Enables WhiteMagic nodes to donate surplus compute, share
//! models, and route tasks to underutilized peers. Implements:
//!
//! - **ResourceInventory**: Track local + peer surplus (idle CPU, free RAM, model capacity)
//! - **TaskRouting**: Route tasks to peers when local resources are constrained
//! - **GiftToken Economics**: Track contributions/receipts to encourage reciprocity
//! - **ModelSharing**: Share loaded model endpoints across the mesh
//!
//! CyberBrains Layer 5 (Radiant — surplus routing).

#![forbid(unsafe_code)]

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::peer::PeerId;

// ── Resource Snapshot ─────────────────────────────────────────────────

/// A snapshot of a node's available resources.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceSnapshot {
    /// Peer ID (or "local" for this node).
    pub peer_id: PeerId,
    /// Idle CPU fraction (0.0 = fully utilized, 1.0 = idle).
    pub idle_cpu: f32,
    /// Free RAM in MB.
    pub free_ram_mb: f32,
    /// Whether a large model is loaded.
    pub has_large_model: bool,
    /// Model name if loaded (e.g., "llama-7b").
    pub loaded_model: Option<String>,
    /// Energy level (0.0–1.0, from Harmony Vector).
    pub energy_level: f32,
    /// Timestamp (Unix seconds).
    pub timestamp: i64,
}

impl ResourceSnapshot {
    /// Create a new resource snapshot.
    #[must_use]
    pub fn new(peer_id: impl Into<String>) -> Self {
        Self {
            peer_id: peer_id.into(),
            idle_cpu: 0.0,
            free_ram_mb: 0.0,
            has_large_model: false,
            loaded_model: None,
            energy_level: 1.0,
            timestamp: chrono::Utc::now().timestamp(),
        }
    }

    /// Whether this node has surplus compute (idle CPU > 0.3 and energy > 0.3).
    #[must_use]
    pub fn has_surplus(&self) -> bool {
        self.idle_cpu > 0.3 && self.energy_level > 0.3
    }

    /// Surplus score (0.0–1.0) — higher = more available.
    #[must_use]
    pub fn surplus_score(&self) -> f32 {
        let cpu_factor = self.idle_cpu;
        let energy_factor = self.energy_level;
        let ram_factor = (self.free_ram_mb / 4096.0).clamp(0.0, 1.0);
        let model_factor = if self.has_large_model { 0.2 } else { 0.0 };
        (cpu_factor.mul_add(0.4, energy_factor * 0.3) + ram_factor * 0.2 + model_factor)
            .clamp(0.0, 1.0)
    }
}

// ── Resource Inventory ────────────────────────────────────────────────

/// Tracks resource snapshots for local + all peer nodes.
pub struct ResourceInventory {
    snapshots: HashMap<PeerId, ResourceSnapshot>,
    /// Local peer ID.
    local_id: PeerId,
}

impl std::fmt::Debug for ResourceInventory {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ResourceInventory")
            .field("nodes", &self.snapshots.len())
            .field("local_id", &self.local_id)
            .finish_non_exhaustive()
    }
}

impl ResourceInventory {
    /// Create a new inventory with the local node ID.
    #[must_use]
    pub fn new(local_id: impl Into<String>) -> Self {
        let local_id = local_id.into();
        Self {
            snapshots: HashMap::new(),
            local_id,
        }
    }

    /// Update the local snapshot.
    pub fn update_local(&mut self, snapshot: ResourceSnapshot) {
        self.snapshots.insert(self.local_id.clone(), snapshot);
    }

    /// Update a peer snapshot.
    pub fn update_peer(&mut self, snapshot: ResourceSnapshot) {
        self.snapshots.insert(snapshot.peer_id.clone(), snapshot);
    }

    /// Get the local snapshot.
    #[must_use]
    pub fn local(&self) -> Option<&ResourceSnapshot> {
        self.snapshots.get(&self.local_id)
    }

    /// Get a peer snapshot.
    #[must_use]
    pub fn peer(&self, peer_id: &str) -> Option<&ResourceSnapshot> {
        self.snapshots.get(peer_id)
    }

    /// Find peers with surplus compute.
    #[must_use]
    pub fn peers_with_surplus(&self) -> Vec<&ResourceSnapshot> {
        self.snapshots
            .values()
            .filter(|s| s.peer_id != self.local_id && s.has_surplus())
            .collect()
    }

    /// Find the best peer to offload a task to (highest surplus score).
    #[must_use]
    pub fn best_offload_target(&self) -> Option<&ResourceSnapshot> {
        self.peers_with_surplus().into_iter().max_by(|a, b| {
            a.surplus_score()
                .partial_cmp(&b.surplus_score())
                .unwrap_or(std::cmp::Ordering::Equal)
        })
    }

    /// Find peers with a specific model loaded.
    #[must_use]
    pub fn peers_with_model(&self, model_name: &str) -> Vec<&ResourceSnapshot> {
        self.snapshots
            .values()
            .filter(|s| s.peer_id != self.local_id && s.loaded_model.as_deref() == Some(model_name))
            .collect()
    }

    /// Number of nodes tracked.
    #[must_use]
    pub fn node_count(&self) -> usize {
        self.snapshots.len()
    }

    /// Get a JSON summary.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "local_id": self.local_id,
            "node_count": self.snapshots.len(),
            "nodes": self.snapshots.values().map(|s| serde_json::json!({
                "peer_id": s.peer_id,
                "idle_cpu": s.idle_cpu,
                "free_ram_mb": s.free_ram_mb,
                "has_large_model": s.has_large_model,
                "energy_level": s.energy_level,
                "surplus_score": s.surplus_score(),
            })).collect::<Vec<_>>(),
        })
    }
}

// ── Gift Token ────────────────────────────────────────────────────────

/// A gift token — tracks contributions and receipts between nodes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GiftToken {
    /// From peer.
    pub from: PeerId,
    /// To peer.
    pub to: PeerId,
    /// Amount (compute units).
    pub amount: f32,
    /// What was donated (e.g., "inference", "memory_search").
    pub kind: String,
    /// Timestamp (Unix seconds).
    pub timestamp: i64,
}

impl GiftToken {
    /// Create a new gift token.
    #[must_use]
    pub fn new(
        from: impl Into<String>,
        to: impl Into<String>,
        amount: f32,
        kind: impl Into<String>,
    ) -> Self {
        Self {
            from: from.into(),
            to: to.into(),
            amount,
            kind: kind.into(),
            timestamp: chrono::Utc::now().timestamp(),
        }
    }
}

// ── Gift Token Ledger ─────────────────────────────────────────────────

/// Tracks gift token contributions and receipts — encourages reciprocity
/// and prevents freeloading. Compatible with karma (good contributions
/// → positive karma).
pub struct GiftTokenLedger {
    /// Local peer ID.
    local_id: PeerId,
    /// All gift tokens.
    tokens: Vec<GiftToken>,
    /// Total donated by local node.
    total_donated: f32,
    /// Total received by local node.
    total_received: f32,
}

impl std::fmt::Debug for GiftTokenLedger {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("GiftTokenLedger")
            .field("local_id", &self.local_id)
            .field("tokens", &self.tokens.len())
            .field("total_donated", &self.total_donated)
            .field("total_received", &self.total_received)
            .finish()
    }
}

impl GiftTokenLedger {
    /// Create a new ledger.
    #[must_use]
    pub fn new(local_id: impl Into<String>) -> Self {
        Self {
            local_id: local_id.into(),
            tokens: Vec::new(),
            total_donated: 0.0,
            total_received: 0.0,
        }
    }

    /// Record a donation from local to a peer.
    pub fn donate(&mut self, to: &str, amount: f32, kind: &str) {
        let token = GiftToken::new(&self.local_id, to, amount, kind);
        self.total_donated += amount;
        self.tokens.push(token);
    }

    /// Record a receipt from a peer to local.
    pub fn receive(&mut self, from: &str, amount: f32, kind: &str) {
        let token = GiftToken::new(from, &self.local_id, amount, kind);
        self.total_received += amount;
        self.tokens.push(token);
    }

    /// Net balance (donated - received). Positive = net contributor.
    #[must_use]
    pub fn net_balance(&self) -> f32 {
        self.total_donated - self.total_received
    }

    /// Whether this node is freeloading (received >> donated).
    #[must_use]
    pub fn is_freeloading(&self) -> bool {
        self.total_received > 0.0 && self.total_donated / self.total_received < 0.3
    }

    /// Total donated.
    #[must_use]
    pub const fn total_donated(&self) -> f32 {
        self.total_donated
    }

    /// Total received.
    #[must_use]
    pub const fn total_received(&self) -> f32 {
        self.total_received
    }

    /// Number of tokens.
    #[must_use]
    pub fn token_count(&self) -> usize {
        self.tokens.len()
    }

    /// Get a JSON summary.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "local_id": self.local_id,
            "total_donated": self.total_donated,
            "total_received": self.total_received,
            "net_balance": self.net_balance(),
            "is_freeloading": self.is_freeloading(),
            "token_count": self.tokens.len(),
        })
    }
}

// ── Task Routing ──────────────────────────────────────────────────────

/// Decision for task routing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RoutingDecision {
    /// Execute locally.
    Local,
    /// Offload to a specific peer.
    Offload(PeerId),
    /// Reject — no suitable node.
    Reject(String),
}

impl RoutingDecision {
    /// Whether this is an offload decision.
    #[must_use]
    pub const fn is_offload(&self) -> bool {
        matches!(self, Self::Offload(_))
    }

    /// Whether this is a reject.
    #[must_use]
    pub const fn is_reject(&self) -> bool {
        matches!(self, Self::Reject(_))
    }
}

/// Task router — decides where to execute a task based on resource inventory.
pub struct TaskRouter {
    inventory: ResourceInventory,
    ledger: GiftTokenLedger,
}

impl std::fmt::Debug for TaskRouter {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("TaskRouter")
            .field("inventory", &self.inventory)
            .field("ledger", &self.ledger)
            .finish()
    }
}

impl TaskRouter {
    /// Create a new task router.
    #[must_use]
    pub fn new(local_id: impl Into<String>) -> Self {
        let local_id = local_id.into();
        Self {
            inventory: ResourceInventory::new(local_id.clone()),
            ledger: GiftTokenLedger::new(local_id),
        }
    }

    /// Get the resource inventory.
    #[must_use]
    pub const fn inventory(&self) -> &ResourceInventory {
        &self.inventory
    }

    /// Get the gift token ledger.
    #[must_use]
    pub const fn ledger(&self) -> &GiftTokenLedger {
        &self.ledger
    }

    /// Get mutable inventory.
    pub const fn inventory_mut(&mut self) -> &mut ResourceInventory {
        &mut self.inventory
    }

    /// Get mutable ledger.
    pub const fn ledger_mut(&mut self) -> &mut GiftTokenLedger {
        &mut self.ledger
    }

    /// Route a task. Decides whether to execute locally or offload to a peer.
    #[must_use]
    pub fn route(&self, requires_large_model: bool, local_energy_low: bool) -> RoutingDecision {
        // If local energy is low, try to offload
        if local_energy_low {
            if let Some(target) = self.inventory.best_offload_target() {
                return RoutingDecision::Offload(target.peer_id.clone());
            }
            return RoutingDecision::Reject("Low energy and no peers with surplus".to_string());
        }

        // If task requires a large model and we don't have it, try to find a peer
        if requires_large_model {
            if let Some(local) = self.inventory.local() {
                if !local.has_large_model {
                    // Find a peer with a large model
                    let model_peers: Vec<_> = self.inventory.peers_with_surplus();
                    if let Some(target) = model_peers.first() {
                        return RoutingDecision::Offload(target.peer_id.clone());
                    }
                    return RoutingDecision::Reject(
                        "No peers with large model available".to_string(),
                    );
                }
            }
        }

        // Default: execute locally
        RoutingDecision::Local
    }

    /// Record a completed offload (for gift token tracking).
    pub fn record_offload(&mut self, to_peer: &str, amount: f32, kind: &str) {
        self.ledger.donate(to_peer, amount, kind);
    }

    /// Record received help from a peer.
    pub fn record_receipt(&mut self, from_peer: &str, amount: f32, kind: &str) {
        self.ledger.receive(from_peer, amount, kind);
    }

    /// Get a JSON summary.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "inventory": self.inventory.summary(),
            "ledger": self.ledger.summary(),
        })
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resource_snapshot_has_surplus() {
        let mut s = ResourceSnapshot::new("local");
        s.idle_cpu = 0.5;
        s.energy_level = 0.8;
        assert!(s.has_surplus());
    }

    #[test]
    fn resource_snapshot_no_surplus() {
        let mut s = ResourceSnapshot::new("local");
        s.idle_cpu = 0.1;
        s.energy_level = 0.2;
        assert!(!s.has_surplus());
    }

    #[test]
    fn resource_snapshot_surplus_score() {
        let mut s = ResourceSnapshot::new("local");
        s.idle_cpu = 0.8;
        s.free_ram_mb = 4096.0;
        s.energy_level = 0.9;
        s.has_large_model = true;
        let score = s.surplus_score();
        assert!(score > 0.5);
    }

    #[test]
    fn inventory_update_local() {
        let mut inv = ResourceInventory::new("local");
        let mut snap = ResourceSnapshot::new("local");
        snap.idle_cpu = 0.5;
        inv.update_local(snap);

        assert!(inv.local().is_some());
        assert_eq!(inv.node_count(), 1);
    }

    #[test]
    fn inventory_peers_with_surplus() {
        let mut inv = ResourceInventory::new("local");
        let mut local = ResourceSnapshot::new("local");
        local.idle_cpu = 0.1;
        inv.update_local(local);

        let mut peer1 = ResourceSnapshot::new("peer-1");
        peer1.idle_cpu = 0.6;
        peer1.energy_level = 0.8;
        inv.update_peer(peer1);

        let surplus = inv.peers_with_surplus();
        assert_eq!(surplus.len(), 1);
        assert_eq!(surplus[0].peer_id, "peer-1");
    }

    #[test]
    fn inventory_best_offload_target() {
        let mut inv = ResourceInventory::new("local");
        let mut p1 = ResourceSnapshot::new("peer-1");
        p1.idle_cpu = 0.4;
        p1.energy_level = 0.5;
        inv.update_peer(p1);

        let mut p2 = ResourceSnapshot::new("peer-2");
        p2.idle_cpu = 0.8;
        p2.energy_level = 0.9;
        p2.free_ram_mb = 8192.0;
        inv.update_peer(p2);

        let best = inv.best_offload_target();
        assert!(best.is_some());
        assert_eq!(best.unwrap().peer_id, "peer-2");
    }

    #[test]
    fn inventory_peers_with_model() {
        let mut inv = ResourceInventory::new("local");
        let mut p1 = ResourceSnapshot::new("peer-1");
        p1.loaded_model = Some("llama-7b".to_string());
        p1.has_large_model = true;
        inv.update_peer(p1);

        let peers = inv.peers_with_model("llama-7b");
        assert_eq!(peers.len(), 1);
    }

    #[test]
    fn gift_token_new() {
        let t = GiftToken::new("node-1", "node-2", 10.0, "inference");
        assert_eq!(t.from, "node-1");
        assert_eq!(t.to, "node-2");
        assert!((t.amount - 10.0).abs() < 0.001);
    }

    #[test]
    fn ledger_donate_and_receive() {
        let mut ledger = GiftTokenLedger::new("local");
        ledger.donate("peer-1", 10.0, "inference");
        ledger.receive("peer-2", 5.0, "memory_search");

        assert!((ledger.total_donated() - 10.0).abs() < 0.001);
        assert!((ledger.total_received() - 5.0).abs() < 0.001);
        assert!((ledger.net_balance() - 5.0).abs() < 0.001);
        assert!(!ledger.is_freeloading());
    }

    #[test]
    fn ledger_freeloading() {
        let mut ledger = GiftTokenLedger::new("local");
        ledger.receive("peer-1", 100.0, "inference");
        ledger.donate("peer-2", 10.0, "memory_search");

        assert!(ledger.is_freeloading());
    }

    #[test]
    fn ledger_not_freeloading_when_balanced() {
        let mut ledger = GiftTokenLedger::new("local");
        ledger.receive("peer-1", 100.0, "inference");
        ledger.donate("peer-2", 80.0, "memory_search");

        assert!(!ledger.is_freeloading());
    }

    #[test]
    fn task_router_local_execution() {
        let mut router = TaskRouter::new("local");
        let mut snap = ResourceSnapshot::new("local");
        snap.idle_cpu = 0.5;
        snap.has_large_model = true;
        router.inventory_mut().update_local(snap);

        let decision = router.route(false, false);
        assert!(matches!(decision, RoutingDecision::Local));
    }

    #[test]
    fn task_router_offload_on_low_energy() {
        let mut router = TaskRouter::new("local");
        let mut snap = ResourceSnapshot::new("local");
        snap.energy_level = 0.1;
        router.inventory_mut().update_local(snap);

        let mut peer = ResourceSnapshot::new("peer-1");
        peer.idle_cpu = 0.7;
        peer.energy_level = 0.9;
        router.inventory_mut().update_peer(peer);

        let decision = router.route(false, true);
        assert!(decision.is_offload());
    }

    #[test]
    fn task_router_reject_when_no_peers() {
        let mut router = TaskRouter::new("local");
        let mut snap = ResourceSnapshot::new("local");
        snap.energy_level = 0.1;
        router.inventory_mut().update_local(snap);

        let decision = router.route(false, true);
        assert!(decision.is_reject());
    }

    #[test]
    fn task_router_offload_for_large_model() {
        let mut router = TaskRouter::new("local");
        let mut snap = ResourceSnapshot::new("local");
        snap.has_large_model = false;
        snap.idle_cpu = 0.5;
        snap.energy_level = 0.8;
        router.inventory_mut().update_local(snap);

        let mut peer = ResourceSnapshot::new("peer-1");
        peer.idle_cpu = 0.6;
        peer.energy_level = 0.8;
        peer.has_large_model = true;
        peer.loaded_model = Some("llama-7b".to_string());
        router.inventory_mut().update_peer(peer);

        let decision = router.route(true, false);
        assert!(decision.is_offload());
    }

    #[test]
    fn task_router_record_offload() {
        let mut router = TaskRouter::new("local");
        router.record_offload("peer-1", 10.0, "inference");
        assert!((router.ledger().total_donated() - 10.0).abs() < 0.001);
    }

    #[test]
    fn task_router_record_receipt() {
        let mut router = TaskRouter::new("local");
        router.record_receipt("peer-1", 5.0, "memory_search");
        assert!((router.ledger().total_received() - 5.0).abs() < 0.001);
    }

    #[test]
    fn inventory_summary() {
        let mut inv = ResourceInventory::new("local");
        inv.update_local(ResourceSnapshot::new("local"));

        let summary = inv.summary();
        assert_eq!(summary["local_id"], "local");
        assert_eq!(summary["node_count"], 1);
    }

    #[test]
    fn ledger_summary() {
        let mut ledger = GiftTokenLedger::new("local");
        ledger.donate("p1", 10.0, "inference");

        let summary = ledger.summary();
        assert_eq!(summary["local_id"], "local");
        assert!((summary["total_donated"].as_f64().unwrap() - 10.0).abs() < 0.001);
    }

    #[test]
    fn routing_decision_helpers() {
        assert!(!RoutingDecision::Local.is_offload());
        assert!(RoutingDecision::Offload("p1".to_string()).is_offload());
        assert!(RoutingDecision::Reject("reason".to_string()).is_reject());
    }
}
