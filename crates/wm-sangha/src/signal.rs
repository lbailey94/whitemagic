//! Signal broadcast — publish/subscribe for mesh-wide event sharing.

#![forbid(unsafe_code)]

use std::sync::atomic::{AtomicU64, Ordering};

use serde::{Deserialize, Serialize};

use crate::peer::PeerId;

// ── Signal Type ───────────────────────────────────────────────────────

/// Types of signals that can be broadcast across the mesh.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SignalType {
    /// A memory was created on a peer.
    MemoryCreated,
    /// An anomaly was detected on a peer.
    AnomalyDetected,
    /// A dream artifact was produced.
    DreamArtifact,
    /// A tool execution result.
    ToolResult,
    /// A holographic coordinate update.
    HologramUpdate,
    /// A peer status change.
    PeerStatus,
    /// A custom signal type.
    Custom,
}

impl SignalType {
    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::MemoryCreated => "memory_created",
            Self::AnomalyDetected => "anomaly_detected",
            Self::DreamArtifact => "dream_artifact",
            Self::ToolResult => "tool_result",
            Self::HologramUpdate => "hologram_update",
            Self::PeerStatus => "peer_status",
            Self::Custom => "custom",
        }
    }
}

// ── Signal ────────────────────────────────────────────────────────────

/// A signal broadcast across the mesh.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Signal {
    /// Unique signal ID.
    pub id: u64,
    /// Signal type.
    pub signal_type: SignalType,
    /// Source peer ID.
    pub source: PeerId,
    /// JSON payload.
    pub payload: serde_json::Value,
    /// Timestamp (Unix milliseconds).
    pub timestamp: i64,
    /// Importance score (0.0–1.0).
    pub importance: f32,
}

impl Signal {
    /// Create a new signal.
    #[must_use]
    pub fn new(
        signal_type: SignalType,
        source: impl Into<String>,
        payload: serde_json::Value,
    ) -> Self {
        Self {
            id: 0, // Will be assigned by broadcast
            signal_type,
            source: source.into(),
            payload,
            timestamp: chrono::Utc::now().timestamp_millis(),
            importance: 0.5,
        }
    }

    /// Set importance.
    #[must_use]
    pub const fn with_importance(mut self, importance: f32) -> Self {
        self.importance = importance;
        self
    }

    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "id": self.id,
            "signal_type": self.signal_type.as_str(),
            "source": self.source,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "importance": self.importance,
        })
    }
}

// ── Signal Broadcast ──────────────────────────────────────────────────

/// A subscriber callback for signals.
pub type SignalCallback = Box<dyn Fn(&Signal) + Send + Sync>;

/// Subscription filter for signals.
#[derive(Debug, Clone)]
pub enum SignalFilter {
    /// Subscribe to all signals.
    All,
    /// Subscribe to a specific signal type.
    Type(SignalType),
    /// Subscribe to signals from a specific peer.
    Source(PeerId),
    /// Subscribe to signals with importance >= threshold.
    MinImportance(f32),
}

impl SignalFilter {
    /// Check if a signal matches this filter.
    #[must_use]
    pub fn matches(&self, signal: &Signal) -> bool {
        match self {
            Self::All => true,
            Self::Type(t) => signal.signal_type == *t,
            Self::Source(s) => signal.source == *s,
            Self::MinImportance(min) => signal.importance >= *min,
        }
    }
}

/// Subscription ID.
pub type SubscriptionId = u64;

/// Signal broadcast — publish/subscribe for mesh-wide event sharing.
pub struct SignalBroadcast {
    next_id: AtomicU64,
    next_signal_id: AtomicU64,
    subscriptions: Vec<(SubscriptionId, SignalFilter, SignalCallback)>,
    /// Total signals broadcast.
    total_broadcast: u64,
    /// Total signals delivered to subscribers.
    total_delivered: u64,
    /// Recent signals (ring buffer).
    recent: std::collections::VecDeque<Signal>,
    /// Max recent signals to retain.
    max_recent: usize,
}

impl Default for SignalBroadcast {
    fn default() -> Self {
        Self::new(100)
    }
}

impl std::fmt::Debug for SignalBroadcast {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SignalBroadcast")
            .field("subscriptions", &self.subscriptions.len())
            .field("total_broadcast", &self.total_broadcast)
            .field("total_delivered", &self.total_delivered)
            .finish_non_exhaustive()
    }
}

impl SignalBroadcast {
    /// Create a new signal broadcast manager.
    #[must_use]
    pub fn new(max_recent: usize) -> Self {
        Self {
            next_id: AtomicU64::new(1),
            next_signal_id: AtomicU64::new(1),
            subscriptions: Vec::new(),
            total_broadcast: 0,
            total_delivered: 0,
            recent: std::collections::VecDeque::with_capacity(max_recent),
            max_recent,
        }
    }

    /// Subscribe to signals matching a filter.
    pub fn subscribe(&mut self, filter: SignalFilter, callback: SignalCallback) -> SubscriptionId {
        let id = self.next_id.fetch_add(1, Ordering::Relaxed);
        self.subscriptions.push((id, filter, callback));
        id
    }

    /// Unsubscribe by ID.
    pub fn unsubscribe(&mut self, id: SubscriptionId) -> bool {
        let before = self.subscriptions.len();
        self.subscriptions.retain(|(sid, _, _)| *sid != id);
        self.subscriptions.len() < before
    }

    /// Broadcast a signal to all matching subscribers.
    pub fn broadcast(&mut self, mut signal: Signal) -> u64 {
        signal.id = self.next_signal_id.fetch_add(1, Ordering::Relaxed);
        self.total_broadcast += 1;

        // Add to recent
        if self.recent.len() >= self.max_recent {
            self.recent.pop_front();
        }
        self.recent.push_back(signal.clone());

        let mut delivered = 0u64;
        for (_, filter, callback) in &self.subscriptions {
            if filter.matches(&signal) {
                callback(&signal);
                delivered += 1;
            }
        }

        self.total_delivered += delivered;
        delivered
    }

    /// Get recent signals.
    #[must_use]
    pub const fn recent(&self) -> &std::collections::VecDeque<Signal> {
        &self.recent
    }

    /// Total signals broadcast.
    #[must_use]
    pub const fn total_broadcast(&self) -> u64 {
        self.total_broadcast
    }

    /// Total deliveries to subscribers.
    #[must_use]
    pub const fn total_delivered(&self) -> u64 {
        self.total_delivered
    }

    /// Number of active subscriptions.
    #[must_use]
    pub fn subscription_count(&self) -> usize {
        self.subscriptions.len()
    }

    /// Get a JSON summary.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "total_broadcast": self.total_broadcast,
            "total_delivered": self.total_delivered,
            "subscriptions": self.subscriptions.len(),
            "recent_count": self.recent.len(),
        })
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::sync::atomic::AtomicUsize;

    #[test]
    fn signal_type_as_str() {
        assert_eq!(SignalType::MemoryCreated.as_str(), "memory_created");
        assert_eq!(SignalType::AnomalyDetected.as_str(), "anomaly_detected");
        assert_eq!(SignalType::Custom.as_str(), "custom");
    }

    #[test]
    fn signal_new() {
        let s = Signal::new(
            SignalType::MemoryCreated,
            "node-1",
            serde_json::json!({"id": 42}),
        );
        assert_eq!(s.source, "node-1");
        assert_eq!(s.signal_type, SignalType::MemoryCreated);
        assert_eq!(s.importance, 0.5);
    }

    #[test]
    fn signal_with_importance() {
        let s = Signal::new(SignalType::AnomalyDetected, "node-1", serde_json::json!({}))
            .with_importance(0.9);
        assert!((s.importance - 0.9).abs() < 0.001);
    }

    #[test]
    fn signal_filter_all_matches() {
        let s = Signal::new(SignalType::MemoryCreated, "node-1", serde_json::json!({}));
        assert!(SignalFilter::All.matches(&s));
    }

    #[test]
    fn signal_filter_type_matches() {
        let s = Signal::new(SignalType::MemoryCreated, "node-1", serde_json::json!({}));
        assert!(SignalFilter::Type(SignalType::MemoryCreated).matches(&s));
        assert!(!SignalFilter::Type(SignalType::AnomalyDetected).matches(&s));
    }

    #[test]
    fn signal_filter_source_matches() {
        let s = Signal::new(SignalType::MemoryCreated, "node-1", serde_json::json!({}));
        assert!(SignalFilter::Source("node-1".to_string()).matches(&s));
        assert!(!SignalFilter::Source("node-2".to_string()).matches(&s));
    }

    #[test]
    fn signal_filter_min_importance() {
        let s = Signal::new(SignalType::MemoryCreated, "node-1", serde_json::json!({}))
            .with_importance(0.8);
        assert!(SignalFilter::MinImportance(0.5).matches(&s));
        assert!(!SignalFilter::MinImportance(0.9).matches(&s));
    }

    #[test]
    fn broadcast_delivers_to_matching() {
        let mut sb = SignalBroadcast::default();
        let counter = Arc::new(AtomicUsize::new(0));
        let c = counter.clone();
        sb.subscribe(
            SignalFilter::Type(SignalType::MemoryCreated),
            Box::new(move |_| {
                c.fetch_add(1, Ordering::Relaxed);
            }),
        );

        sb.broadcast(Signal::new(
            SignalType::MemoryCreated,
            "node-1",
            serde_json::json!({}),
        ));
        sb.broadcast(Signal::new(
            SignalType::AnomalyDetected,
            "node-1",
            serde_json::json!({}),
        ));

        assert_eq!(counter.load(Ordering::Relaxed), 1);
        assert_eq!(sb.total_broadcast(), 2);
        assert_eq!(sb.total_delivered(), 1);
    }

    #[test]
    fn broadcast_assigns_unique_ids() {
        let mut sb = SignalBroadcast::default();
        let s1 = sb.broadcast(Signal::new(
            SignalType::MemoryCreated,
            "n1",
            serde_json::json!({}),
        ));
        let _ = s1;
        let s2 = sb.broadcast(Signal::new(
            SignalType::MemoryCreated,
            "n1",
            serde_json::json!({}),
        ));
        let _ = s2;

        let recent = sb.recent();
        assert_eq!(recent.len(), 2);
        assert_ne!(recent[0].id, recent[1].id);
    }

    #[test]
    fn unsubscribe_removes_subscription() {
        let mut sb = SignalBroadcast::default();
        let id = sb.subscribe(SignalFilter::All, Box::new(|_| {}));
        assert_eq!(sb.subscription_count(), 1);
        assert!(sb.unsubscribe(id));
        assert_eq!(sb.subscription_count(), 0);
    }

    #[test]
    fn broadcast_recent_capped() {
        let mut sb = SignalBroadcast::new(3);
        for i in 0..5 {
            sb.broadcast(Signal::new(SignalType::Custom, "n1", serde_json::json!(i)));
        }
        assert_eq!(sb.recent().len(), 3);
    }

    #[test]
    fn broadcast_summary() {
        let mut sb = SignalBroadcast::default();
        sb.subscribe(SignalFilter::All, Box::new(|_| {}));
        sb.broadcast(Signal::new(
            SignalType::MemoryCreated,
            "n1",
            serde_json::json!({}),
        ));

        let summary = sb.summary();
        assert_eq!(summary["total_broadcast"], 1);
        assert_eq!(summary["total_delivered"], 1);
    }
}
