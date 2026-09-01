//! Corpus callosum — bounded bidirectional communication channel
//! between the left and right hemispheres.
//!
//! Messages flow through the callosum with a configurable bandwidth limit.
//! Each message has a kind (critique, counter-argument, agreement) and
//! a text payload. The callosum tracks total bytes transferred.

use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicUsize, Ordering};

/// Kind of message sent through the corpus callosum.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MessageKind {
    /// A critique of the other hemisphere's output.
    Critique,
    /// A counter-argument responding to a critique.
    Counter,
    /// An agreement or concession.
    Agreement,
    /// A request for more information.
    Query,
}

/// A message sent through the corpus callosum.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    /// Which direction this message flows.
    pub direction: MessageDirection,
    /// The kind of message.
    pub kind: MessageKind,
    /// The message payload (text).
    pub payload: String,
    /// Which round of debate this message belongs to.
    pub round: usize,
}

/// Direction of a callosum message.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MessageDirection {
    /// Left → Right.
    LeftToRight,
    /// Right → Left.
    RightToLeft,
}

/// Configuration for the corpus callosum.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CallosumConfig {
    /// Maximum bytes per message.
    pub max_message_bytes: usize,
    /// Maximum total bytes across all messages.
    pub max_total_bytes: usize,
}

impl Default for CallosumConfig {
    fn default() -> Self {
        Self {
            max_message_bytes: 1024,
            max_total_bytes: 8192,
        }
    }
}

/// Corpus callosum — bounded communication channel between hemispheres.
pub struct CorpusCallosum {
    messages: std::sync::Mutex<Vec<Message>>,
    total_bytes: AtomicUsize,
    max_total_bytes: usize,
    max_message_bytes: usize,
}

impl CorpusCallosum {
    /// Create a new corpus callosum with the given bandwidth limit (bytes).
    #[must_use]
    pub const fn new(bandwidth_bytes: usize) -> Self {
        Self {
            messages: std::sync::Mutex::new(Vec::new()),
            total_bytes: AtomicUsize::new(0),
            max_total_bytes: bandwidth_bytes * 8,
            max_message_bytes: bandwidth_bytes,
        }
    }

    /// Create a new corpus callosum with explicit config.
    #[must_use]
    #[allow(clippy::missing_const_for_fn)]
    pub fn with_config(config: &CallosumConfig) -> Self {
        Self {
            messages: std::sync::Mutex::new(Vec::new()),
            total_bytes: AtomicUsize::new(0),
            max_total_bytes: config.max_total_bytes,
            max_message_bytes: config.max_message_bytes,
        }
    }

    /// Send a message through the callosum.
    /// Returns `false` if the message would exceed bandwidth limits.
    pub fn send(&self, message: Message) -> bool {
        let payload_bytes = message.payload.len();
        if payload_bytes > self.max_message_bytes {
            return false;
        }

        let current = self.total_bytes.load(Ordering::Relaxed);
        if current + payload_bytes > self.max_total_bytes {
            return false;
        }

        self.total_bytes.fetch_add(payload_bytes, Ordering::Relaxed);
        if let Ok(mut msgs) = self.messages.lock() {
            msgs.push(message);
        }
        true
    }

    /// Get all messages exchanged.
    #[must_use]
    pub fn messages(&self) -> Vec<Message> {
        self.messages.lock().map(|m| m.clone()).unwrap_or_default()
    }

    /// Get total bytes transferred.
    #[must_use]
    pub fn total_bytes(&self) -> usize {
        self.total_bytes.load(Ordering::Relaxed)
    }

    /// Get the number of messages exchanged.
    #[must_use]
    pub fn message_count(&self) -> usize {
        self.messages.lock().map_or(0, |m| m.len())
    }

    /// Get messages for a specific round.
    #[must_use]
    pub fn messages_for_round(&self, round: usize) -> Vec<Message> {
        self.messages
            .lock()
            .map(|m| m.iter().filter(|msg| msg.round == round).cloned().collect())
            .unwrap_or_default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn callosum_send_and_retrieve() {
        let callosum = CorpusCallosum::new(1024);
        let msg = Message {
            direction: MessageDirection::LeftToRight,
            kind: MessageKind::Critique,
            payload: "Your analysis misses edge cases".into(),
            round: 0,
        };
        assert!(callosum.send(msg));
        assert_eq!(callosum.message_count(), 1);
    }

    #[test]
    fn callosum_bandwidth_limit() {
        let callosum = CorpusCallosum::new(64); // 64 bytes per message, 512 total
        for i in 0..20 {
            let msg = Message {
                direction: MessageDirection::LeftToRight,
                kind: MessageKind::Critique,
                payload: format!("Critique number {i} with some padding text"),
                round: 0,
            };
            let sent = callosum.send(msg);
            if !sent {
                break;
            }
        }
        // Should have stopped before 20 messages due to bandwidth
        assert!(callosum.message_count() < 20);
        assert!(callosum.total_bytes() <= 512);
    }

    #[test]
    fn callosum_message_too_large() {
        let callosum = CorpusCallosum::new(32); // 32 bytes per message
        let msg = Message {
            direction: MessageDirection::LeftToRight,
            kind: MessageKind::Critique,
            payload: "This message is way too long to fit in the bandwidth limit".into(),
            round: 0,
        };
        assert!(!callosum.send(msg));
        assert_eq!(callosum.message_count(), 0);
    }

    #[test]
    fn callosum_messages_for_round() {
        let callosum = CorpusCallosum::new(1024);
        for round in 0..3 {
            for i in 0..2 {
                let msg = Message {
                    direction: if i % 2 == 0 {
                        MessageDirection::LeftToRight
                    } else {
                        MessageDirection::RightToLeft
                    },
                    kind: MessageKind::Counter,
                    payload: format!("Round {round} message {i}"),
                    round,
                };
                callosum.send(msg);
            }
        }
        assert_eq!(callosum.messages_for_round(0).len(), 2);
        assert_eq!(callosum.messages_for_round(1).len(), 2);
        assert_eq!(callosum.messages_for_round(2).len(), 2);
        assert_eq!(callosum.messages_for_round(3).len(), 0);
    }

    #[test]
    fn callosum_with_config() {
        let config = CallosumConfig {
            max_message_bytes: 100,
            max_total_bytes: 500,
        };
        let callosum = CorpusCallosum::with_config(&config);
        let msg = Message {
            direction: MessageDirection::RightToLeft,
            kind: MessageKind::Agreement,
            payload: "I agree".into(),
            round: 0,
        };
        assert!(callosum.send(msg));
        assert_eq!(callosum.total_bytes(), 7);
    }
}
