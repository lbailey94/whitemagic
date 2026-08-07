//! Inter-agent chat — topic-based messaging with persisted log.

#![forbid(unsafe_code)]

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::peer::PeerId;

// ── Chat Channel ──────────────────────────────────────────────────────

/// A chat channel topic.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct ChatChannel {
    /// Channel name (e.g., "gana:1", "project:alpha", "domain:math").
    pub name: String,
}

impl ChatChannel {
    /// Create a new channel.
    #[must_use]
    pub fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }

    /// Create a Gana-based channel.
    #[must_use]
    pub fn gana(gana_id: u8) -> Self {
        Self::new(format!("gana:{gana_id}"))
    }

    /// Create a project-based channel.
    #[must_use]
    pub fn project(project: &str) -> Self {
        Self::new(format!("project:{project}"))
    }
}

// ── Chat Message ──────────────────────────────────────────────────────

/// A chat message between agents.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    /// Unique message ID.
    pub id: u64,
    /// Channel name.
    pub channel: String,
    /// Sender peer ID.
    pub sender: PeerId,
    /// Message content.
    pub content: String,
    /// Timestamp (Unix milliseconds).
    pub timestamp: i64,
}

impl ChatMessage {
    /// Convert to JSON.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "id": self.id,
            "channel": self.channel,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp,
        })
    }
}

// ── Sangha Chat ───────────────────────────────────────────────────────

/// Inter-agent chat with topic-based channels.
///
/// Messages are fire-and-forget (async semantics in a real transport).
/// A message log is maintained per channel for late joiners.
pub struct SanghaChat {
    next_msg_id: u64,
    /// Messages per channel.
    channels: HashMap<String, Vec<ChatMessage>>,
    /// Max messages per channel.
    max_per_channel: usize,
    /// Total messages sent.
    total_messages: u64,
}

impl Default for SanghaChat {
    fn default() -> Self {
        Self::new(100)
    }
}

impl std::fmt::Debug for SanghaChat {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SanghaChat")
            .field("channels", &self.channels.len())
            .field("total_messages", &self.total_messages)
            .finish_non_exhaustive()
    }
}

impl SanghaChat {
    /// Create a new chat manager.
    #[must_use]
    pub fn new(max_per_channel: usize) -> Self {
        Self {
            next_msg_id: 1,
            channels: HashMap::new(),
            max_per_channel,
            total_messages: 0,
        }
    }

    /// Send a message to a channel.
    ///
    /// Message content is sanitized: control characters are stripped and
    /// length is capped at 4096 characters to prevent message injection.
    pub fn send(&mut self, channel: &str, sender: &str, content: impl Into<String>) -> ChatMessage {
        let raw_content = content.into();
        let sanitized: String = raw_content
            .chars()
            .filter(|c| !c.is_control() || *c == '\n' || *c == '\t')
            .take(4096)
            .collect();

        let msg = ChatMessage {
            id: self.next_msg_id,
            channel: channel.to_string(),
            sender: sender.to_string(),
            content: sanitized,
            timestamp: chrono::Utc::now().timestamp_millis(),
        };
        self.next_msg_id += 1;
        self.total_messages += 1;

        let msgs = self.channels.entry(channel.to_string()).or_default();
        if msgs.len() >= self.max_per_channel {
            msgs.remove(0);
        }
        msgs.push(msg.clone());
        msg
    }

    /// Read messages from a channel (optionally only after a given message ID).
    #[must_use]
    pub fn read(&self, channel: &str, after_id: Option<u64>) -> Vec<&ChatMessage> {
        if let Some(msgs) = self.channels.get(channel) {
            match after_id {
                Some(id) => msgs.iter().filter(|m| m.id > id).collect(),
                None => msgs.iter().collect(),
            }
        } else {
            Vec::new()
        }
    }

    /// Get all channel names.
    #[must_use]
    pub fn channels(&self) -> Vec<&String> {
        self.channels.keys().collect()
    }

    /// Number of messages in a channel.
    #[must_use]
    pub fn channel_message_count(&self, channel: &str) -> usize {
        self.channels.get(channel).map_or(0, Vec::len)
    }

    /// Total messages sent.
    #[must_use]
    pub const fn total_messages(&self) -> u64 {
        self.total_messages
    }

    /// Clear a channel.
    pub fn clear_channel(&mut self, channel: &str) {
        self.channels.remove(channel);
    }

    /// Get a JSON summary.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "total_messages": self.total_messages,
            "channels": self.channels.iter().map(|(name, msgs)| {
                serde_json::json!({
                    "name": name,
                    "message_count": msgs.len(),
                })
            }).collect::<Vec<_>>(),
        })
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn send_and_read() {
        let mut chat = SanghaChat::default();
        chat.send("gana:1", "node-1", "Hello");
        chat.send("gana:1", "node-2", "Hi there");

        let msgs = chat.read("gana:1", None);
        assert_eq!(msgs.len(), 2);
        assert_eq!(msgs[0].content, "Hello");
        assert_eq!(msgs[1].content, "Hi there");
    }

    #[test]
    fn read_after_id() {
        let mut chat = SanghaChat::default();
        chat.send("gana:1", "node-1", "First");
        chat.send("gana:1", "node-2", "Second");
        chat.send("gana:1", "node-1", "Third");

        let msgs = chat.read("gana:1", Some(1));
        assert_eq!(msgs.len(), 2);
        assert_eq!(msgs[0].content, "Second");
    }

    #[test]
    fn channel_isolation() {
        let mut chat = SanghaChat::default();
        chat.send("gana:1", "node-1", "A");
        chat.send("gana:2", "node-1", "B");

        assert_eq!(chat.channel_message_count("gana:1"), 1);
        assert_eq!(chat.channel_message_count("gana:2"), 1);
        assert_eq!(chat.read("gana:1", None)[0].content, "A");
    }

    #[test]
    fn max_per_channel() {
        let mut chat = SanghaChat::new(3);
        chat.send("ch", "n1", "1");
        chat.send("ch", "n1", "2");
        chat.send("ch", "n1", "3");
        chat.send("ch", "n1", "4"); // Should evict "1"

        assert_eq!(chat.channel_message_count("ch"), 3);
        let msgs = chat.read("ch", None);
        assert_eq!(msgs[0].content, "2");
    }

    #[test]
    fn channel_names() {
        let mut chat = SanghaChat::default();
        chat.send("gana:1", "n1", "x");
        chat.send("project:alpha", "n1", "y");

        let names = chat.channels();
        assert_eq!(names.len(), 2);
    }

    #[test]
    fn clear_channel() {
        let mut chat = SanghaChat::default();
        chat.send("ch", "n1", "x");
        chat.clear_channel("ch");
        assert_eq!(chat.channel_message_count("ch"), 0);
    }

    #[test]
    fn total_messages() {
        let mut chat = SanghaChat::default();
        chat.send("ch1", "n1", "a");
        chat.send("ch2", "n1", "b");
        assert_eq!(chat.total_messages(), 2);
    }

    #[test]
    fn chat_channel_constructors() {
        let c1 = ChatChannel::gana(5);
        assert_eq!(c1.name, "gana:5");

        let c2 = ChatChannel::project("alpha");
        assert_eq!(c2.name, "project:alpha");
    }

    #[test]
    fn message_to_json() {
        let msg = ChatMessage {
            id: 1,
            channel: "test".to_string(),
            sender: "node-1".to_string(),
            content: "hello".to_string(),
            timestamp: 12345,
        };
        let json = msg.to_json();
        assert_eq!(json["id"], 1);
        assert_eq!(json["channel"], "test");
        assert_eq!(json["content"], "hello");
    }

    #[test]
    fn summary() {
        let mut chat = SanghaChat::default();
        chat.send("ch1", "n1", "a");
        chat.send("ch1", "n2", "b");

        let summary = chat.summary();
        assert_eq!(summary["total_messages"], 2);
    }

    #[test]
    fn unique_message_ids() {
        let mut chat = SanghaChat::default();
        let m1 = chat.send("ch", "n1", "a");
        let m2 = chat.send("ch", "n1", "b");
        assert_ne!(m1.id, m2.id);
    }

    #[test]
    fn send_strips_control_characters() {
        let mut chat = SanghaChat::default();
        let msg = chat.send("ch", "n1", "hello\x00\x01\x02world");
        assert_eq!(msg.content, "helloworld");
    }

    #[test]
    fn send_preserves_newlines() {
        let mut chat = SanghaChat::default();
        let msg = chat.send("ch", "n1", "line1\nline2");
        assert_eq!(msg.content, "line1\nline2");
    }

    #[test]
    fn send_caps_message_length() {
        let mut chat = SanghaChat::default();
        let long = "x".repeat(5000);
        let msg = chat.send("ch", "n1", &long);
        assert_eq!(
            msg.content.len(),
            4096,
            "Message should be capped at 4096 chars"
        );
    }
}
