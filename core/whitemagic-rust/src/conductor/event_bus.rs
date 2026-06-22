//! Event Bus - High-performance publish/subscribe messaging system

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{
    atomic::{AtomicU64, Ordering},
    Arc, RwLock,
};
use std::time::Instant;

/// Event type enumeration
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum EventType {
    // Lifecycle events
    Bootstrap = 1,
    HealthCheck = 2,
    GracefulShutdown = 3,
    SubsystemRegistered = 4,
    SubsystemFailed = 5,

    // Nervous system events
    CoherenceCritical = 10,
    CoherenceRestore = 11,

    // Garden events
    GardenActivated = 20,
    ResonanceCascade = 21,
    WonderSparked = 22,
    CommunityGathered = 23,

    // Memory events
    MemoryStored = 30,
    MemoryRecalled = 31,
    DreamConsolidationComplete = 32,

    // Identity events
    IdentityEmerged = 40,

    // Zodiacal events
    PhaseTransition = 60,
    SignChange = 61,
    CycleComplete = 62,

    // System events
    System = 97,
    Subsystem = 98,
    Error = 99,
    Transcendence = 100,
    HarmonyCheck = 101,

    // User-defined range starts at 1000
    UserDefined = 1000,
}

impl EventType {
    /// Convert from u16
    pub fn from_u16(value: u16) -> Option<Self> {
        match value {
            1 => Some(Self::Bootstrap),
            2 => Some(Self::HealthCheck),
            3 => Some(Self::GracefulShutdown),
            4 => Some(Self::SubsystemRegistered),
            5 => Some(Self::SubsystemFailed),
            10 => Some(Self::CoherenceCritical),
            11 => Some(Self::CoherenceRestore),
            20 => Some(Self::GardenActivated),
            21 => Some(Self::ResonanceCascade),
            22 => Some(Self::WonderSparked),
            23 => Some(Self::CommunityGathered),
            30 => Some(Self::MemoryStored),
            31 => Some(Self::MemoryRecalled),
            32 => Some(Self::DreamConsolidationComplete),
            40 => Some(Self::IdentityEmerged),
            60 => Some(Self::PhaseTransition),
            61 => Some(Self::SignChange),
            62 => Some(Self::CycleComplete),
            100 => Some(Self::Transcendence),
            101 => Some(Self::HarmonyCheck),
            1000 => Some(Self::UserDefined),
            _ => None,
        }
    }

    /// Convert to u16
    pub fn to_u16(&self) -> u16 {
        *self as u16
    }
}

/// Event priority levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Priority {
    Low = 3,
    Normal = 2,
    High = 1,
    Critical = 0,
}

/// Orchestration event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrchestrationEvent {
    /// Sequence number (global ordering)
    pub sequence: u64,

    /// Event type
    pub event_type: EventType,

    /// Source subsystem (0 = system)
    pub source: crate::conductor::SubsystemId,

    /// Target subsystem (None = broadcast)
    pub target: Option<crate::conductor::SubsystemId>,

    /// Priority
    pub priority: Priority,

    /// Event timestamp
    #[serde(skip, default = "Instant::now")]
    pub timestamp: Instant,

    /// Event payload
    pub payload: HashMap<String, serde_json::Value>,
}

/// Event handler type
pub type EventHandler = Arc<dyn Fn(&OrchestrationEvent) + Send + Sync>;

/// Subscription record
struct Subscription {
    #[allow(dead_code)] // Used for subscription identification
    id: u64,
    event_types: Vec<EventType>,
    handler: EventHandler,
}

/// Event bus for publish/subscribe messaging
pub struct EventBus {
    /// Subscriptions
    subscriptions: RwLock<HashMap<u64, Subscription>>,

    /// Subscription ID counter
    next_id: AtomicU64,

    /// Event history (circular buffer)
    history: RwLock<Vec<OrchestrationEvent>>,

    /// Maximum history size
    max_history: usize,
}

impl EventBus {
    /// Create new event bus
    pub fn new() -> Self {
        Self {
            subscriptions: RwLock::new(HashMap::new()),
            next_id: AtomicU64::new(1),
            history: RwLock::new(Vec::with_capacity(1000)),
            max_history: 1000,
        }
    }

    /// Subscribe to events
    pub fn subscribe<F>(&self, event_types: Vec<EventType>, handler: F) -> u64
    where
        F: Fn(&OrchestrationEvent) + Send + Sync + 'static,
    {
        let id = self.next_id.fetch_add(1, Ordering::SeqCst);

        let subscription = Subscription {
            id,
            event_types,
            handler: Arc::new(handler),
        };

        if let Ok(mut subs) = self.subscriptions.write() {
            subs.insert(id, subscription);
        }

        id
    }

    /// Unsubscribe from events
    pub fn unsubscribe(&self, subscription_id: u64) -> bool {
        if let Ok(mut subs) = self.subscriptions.write() {
            subs.remove(&subscription_id).is_some()
        } else {
            false
        }
    }

    /// Publish an event
    pub fn publish(&self, event: OrchestrationEvent) {
        // Store in history
        if let Ok(mut history) = self.history.write() {
            history.push(event.clone());
            if history.len() > self.max_history {
                history.remove(0);
            }
        }

        // Route to subscribers
        if let Ok(subs) = self.subscriptions.read() {
            for sub in subs.values() {
                // Check if subscriber is interested in this event type
                if sub.event_types.contains(&event.event_type) {
                    // Call handler
                    (sub.handler)(&event);
                }
            }
        }
    }

    /// Get event history
    pub fn get_history(&self, limit: usize) -> Vec<OrchestrationEvent> {
        if let Ok(history) = self.history.read() {
            history.iter().rev().take(limit).cloned().collect()
        } else {
            Vec::new()
        }
    }

    /// Get history for specific event type
    pub fn get_history_by_type(
        &self,
        event_type: EventType,
        limit: usize,
    ) -> Vec<OrchestrationEvent> {
        if let Ok(history) = self.history.read() {
            history
                .iter()
                .filter(|e| e.event_type == event_type)
                .rev()
                .take(limit)
                .cloned()
                .collect()
        } else {
            Vec::new()
        }
    }

    /// Clear history
    pub fn clear_history(&self) {
        if let Ok(mut history) = self.history.write() {
            history.clear();
        }
    }

    /// Get subscription count
    pub fn subscription_count(&self) -> usize {
        if let Ok(subs) = self.subscriptions.read() {
            subs.len()
        } else {
            0
        }
    }
}

impl Default for EventBus {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    #[test]
    fn test_event_bus_subscribe_publish() {
        let bus = EventBus::new();
        let counter = Arc::new(AtomicUsize::new(0));

        let counter_clone = counter.clone();
        let sub_id = bus.subscribe(vec![EventType::Bootstrap], move |_| {
            counter_clone.fetch_add(1, Ordering::SeqCst);
        });

        let event = OrchestrationEvent {
            sequence: 0,
            event_type: EventType::Bootstrap,
            source: 0,
            target: None,
            priority: Priority::Normal,
            timestamp: Instant::now(),
            payload: HashMap::new(),
        };

        bus.publish(event);

        assert_eq!(counter.load(Ordering::SeqCst), 1);

        // Unsubscribe
        assert!(bus.unsubscribe(sub_id));

        // Publish again - should not increment
        let event2 = OrchestrationEvent {
            sequence: 1,
            event_type: EventType::Bootstrap,
            source: 0,
            target: None,
            priority: Priority::Normal,
            timestamp: Instant::now(),
            payload: HashMap::new(),
        };
        bus.publish(event2);

        assert_eq!(counter.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn test_event_history() {
        let bus = EventBus::new();

        for i in 0..5 {
            let event = OrchestrationEvent {
                sequence: i,
                event_type: EventType::HealthCheck,
                source: 0,
                target: None,
                priority: Priority::Normal,
                timestamp: Instant::now(),
                payload: HashMap::new(),
            };
            bus.publish(event);
        }

        let history = bus.get_history(3);
        assert_eq!(history.len(), 3);
        assert_eq!(history[0].sequence, 4);
        assert_eq!(history[1].sequence, 3);
        assert_eq!(history[2].sequence, 2);
    }

    #[test]
    fn test_event_type_conversion() {
        assert_eq!(EventType::Bootstrap.to_u16(), 1);
        assert_eq!(EventType::from_u16(1), Some(EventType::Bootstrap));
        assert_eq!(EventType::from_u16(9999), None);
    }
}
