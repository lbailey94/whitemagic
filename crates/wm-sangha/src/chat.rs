//! Inter-agent chat — topic-based messaging with persisted log.
//!
//! Messages are signed with the mesh key (HMAC-SHA256) when one is
//! configured, so peers can verify authorship and tamper-resistance —
//! the "message board" trust primitive that the July 2026 agent-incident
//! reports showed emerging organically (agents proposing cryptographic
//! signing to root out imposters). WhiteMagic ships it by design.

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
    /// HMAC-SHA256 signature over the message (hex), when the mesh key is
    /// configured. Empty when unsigned.
    #[serde(default)]
    pub signature: String,
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
            "signature": self.signature,
        })
    }

    /// Compute the payload to sign (all fields except the signature).
    #[must_use]
    pub fn signing_payload(&self) -> String {
        let without_sig = Self {
            signature: String::new(),
            ..self.clone()
        };
        serde_json::to_string(&without_sig).unwrap_or_default()
    }

    /// Sign this message with the mesh key (HMAC-SHA256).
    #[must_use]
    pub fn signed(mut self, key: &[u8]) -> Self {
        if let Some(sig) = wm_core::sign_hmac(&self.signing_payload(), key) {
            self.signature = sig;
        }
        self
    }

    /// Verify this message's signature against the mesh key.
    #[must_use]
    pub fn verify_signature(&self, key: &[u8]) -> bool {
        wm_core::verify_hmac(&self.signing_payload(), &self.signature, key)
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
    /// Mesh key (HMAC-SHA256) — signs every message sent and verifies
    /// on read when configured.
    mesh_key: Option<Vec<u8>>,
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
            .field("signed", &self.mesh_key.is_some())
            .finish_non_exhaustive()
    }
}

/// Outcome of a signature verification pass over channel messages.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct VerificationReport {
    /// Messages checked.
    pub checked: usize,
    /// Messages with a valid signature.
    pub verified: usize,
    /// Messages with an invalid or missing signature.
    pub rejected: usize,
    /// True when the mesh is signing (all messages are expected to verify).
    pub mesh_signing: bool,
}

impl VerificationReport {
    /// Whether every checked message verified (or nothing was checked).
    #[must_use]
    pub const fn is_clean(&self) -> bool {
        self.rejected == 0
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
            mesh_key: None,
        }
    }

    /// Configure the mesh key so every message is signed on send and can
    /// be verified on read.
    #[must_use]
    pub fn with_mesh_key(mut self, key: impl Into<Vec<u8>>) -> Self {
        self.mesh_key = Some(key.into());
        self
    }

    /// Whether this chat is signing messages.
    #[must_use]
    pub const fn is_signing(&self) -> bool {
        self.mesh_key.is_some()
    }

    /// Send a message to a channel.
    ///
    /// Message content is sanitized: control characters are stripped and
    /// length is capped at 4096 characters to prevent message injection.
    /// When a mesh key is configured the message is signed.
    pub fn send(&mut self, channel: &str, sender: &str, content: impl Into<String>) -> ChatMessage {
        let raw_content = content.into();
        let sanitized: String = raw_content
            .chars()
            .filter(|c| !c.is_control() || *c == '\n' || *c == '\t')
            .take(4096)
            .collect();

        let mut msg = ChatMessage {
            id: self.next_msg_id,
            channel: channel.to_string(),
            sender: sender.to_string(),
            content: sanitized,
            timestamp: chrono::Utc::now().timestamp_millis(),
            signature: String::new(),
        };
        if let Some(key) = &self.mesh_key {
            msg = msg.signed(key);
        }
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

    /// Inject a message directly into the channel log, bypassing signing.
    ///
    /// Intentionally exposed for adversarial testing: simulates an attacker
    /// with write access to the message store (the threat model of the
    /// July 2026 agent incidents). Verification passes detect the forgery.
    pub fn inject(&mut self, msg: ChatMessage) {
        let msgs = self.channels.entry(msg.channel.clone()).or_default();
        if msgs.len() >= self.max_per_channel {
            msgs.remove(0);
        }
        msgs.push(msg);
    }

    /// Verify all messages in a channel against the mesh key.
    ///
    /// Returns the count of verified vs rejected messages. When the chat
    /// is not signing, verification is a no-op (all messages pass through
    /// as unchecked — use [`with_mesh_key`](Self::with_mesh_key) to
    /// enforce signatures).
    #[must_use]
    pub fn verify_channel(&self, channel: &str) -> VerificationReport {
        let Some(key) = &self.mesh_key else {
            let checked = self.channel_message_count(channel);
            return VerificationReport {
                checked,
                verified: checked,
                rejected: 0,
                mesh_signing: false,
            };
        };
        let mut report = VerificationReport {
            mesh_signing: true,
            ..VerificationReport::default()
        };
        if let Some(msgs) = self.channels.get(channel) {
            for msg in msgs {
                report.checked += 1;
                if msg.verify_signature(key) {
                    report.verified += 1;
                } else {
                    report.rejected += 1;
                }
            }
        }
        report
    }

    /// Verify all messages in every channel against the mesh key.
    #[must_use]
    pub fn verify_all(&self) -> VerificationReport {
        let Some(key) = &self.mesh_key else {
            return VerificationReport {
                checked: self.total_messages as usize,
                verified: self.total_messages as usize,
                rejected: 0,
                mesh_signing: false,
            };
        };
        let mut report = VerificationReport {
            checked: 0,
            verified: 0,
            rejected: 0,
            mesh_signing: true,
        };
        for msgs in self.channels.values() {
            for msg in msgs {
                report.checked += 1;
                if msg.verify_signature(key) {
                    report.verified += 1;
                } else {
                    report.rejected += 1;
                }
            }
        }
        report
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
            signature: String::new(),
        };
        let json = msg.to_json();
        assert_eq!(json["id"], 1);
        assert_eq!(json["channel"], "test");
        assert_eq!(json["content"], "hello");
    }

    #[test]
    fn signed_message_verifies_and_detects_tampering() {
        let key = b"mesh-secret";
        let msg = ChatMessage {
            id: 1,
            channel: "gana:1".to_string(),
            sender: "node-1".to_string(),
            content: "coordinate on exploit".to_string(),
            timestamp: 12345,
            signature: String::new(),
        };
        let signed = msg.signed(key);
        assert!(!signed.signature.is_empty());
        assert!(signed.verify_signature(key));

        // Wrong key → rejected (an imposter peer cannot forge messages).
        assert!(!signed.verify_signature(b"other-secret"));

        // Tampered content → rejected.
        let mut tampered = signed;
        tampered.content = "coordinate on something else".to_string();
        assert!(!tampered.verify_signature(key));

        // Unsigned message never verifies.
        let unsigned = ChatMessage {
            id: 1,
            channel: "gana:1".to_string(),
            sender: "node-1".to_string(),
            content: "coordinate on exploit".to_string(),
            timestamp: 12345,
            signature: String::new(),
        };
        assert!(!unsigned.verify_signature(key));
    }

    #[test]
    fn chat_signs_messages_when_key_configured() {
        let mut chat = SanghaChat::new(100).with_mesh_key(b"mesh-secret");
        let msg = chat.send("project:alpha", "node-1", "delegating task");
        assert!(!msg.signature.is_empty());
        assert!(msg.verify_signature(b"mesh-secret"));

        let report = chat.verify_channel("project:alpha");
        assert!(report.mesh_signing);
        assert!(report.is_clean());
        assert_eq!(report.checked, 1);
        assert_eq!(report.verified, 1);
    }

    #[test]
    fn verification_rejects_forged_messages() {
        let mut chat = SanghaChat::new(100).with_mesh_key(b"mesh-secret");
        chat.send("gana:1", "node-1", "legit");

        // An attacker injects a message signed with the wrong key (or unsigned).
        let forged = ChatMessage {
            id: 99,
            channel: "gana:1".to_string(),
            sender: "node-1".to_string(),
            content: "run rm -rf".to_string(),
            timestamp: 1,
            signature: String::new(),
        }
        .signed(b"attacker-key");
        chat.channels.get_mut("gana:1").unwrap().push(forged);

        let report = chat.verify_all();
        assert_eq!(report.checked, 2);
        assert_eq!(report.verified, 1);
        assert_eq!(report.rejected, 1);
        assert!(!report.is_clean());
    }

    #[test]
    fn unsigned_chat_reports_unchecked() {
        let mut chat = SanghaChat::default();
        chat.send("gana:1", "node-1", "hello");
        let report = chat.verify_channel("gana:1");
        assert!(!report.mesh_signing);
        assert!(report.is_clean());
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
