//! Inter-agent chat — topic-based messaging with persisted log.
//!
//! Messages are signed with each sender's Ed25519 keypair, so peers can
//! verify authorship, tamper-resistance, and identity binding — the
//! "message board" trust primitive that the July 2026 agent-incident
//! reports showed emerging organically (agents proposing cryptographic
//! signing to root out imposters). WhiteMagic ships it by design, with
//! asymmetric keys so no peer can forge another's identity.

#![forbid(unsafe_code)]

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use crate::crypto::MeshKeyPair;
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
    /// Ed25519 signature over the message (hex), when the chat is
    /// signing. Empty when unsigned.
    #[serde(default)]
    pub signature: String,
    /// Sender's Ed25519 public key (hex) — the identity the signature
    /// must verify against, and which the community binds to the peer ID.
    #[serde(default)]
    pub public_key: String,
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
            "public_key": self.public_key,
        })
    }

    /// Compute the payload to sign (all fields except signature and
    /// public key).
    #[must_use]
    pub fn signing_payload(&self) -> String {
        let without_sig = Self {
            signature: String::new(),
            public_key: String::new(),
            ..self.clone()
        };
        serde_json::to_string(&without_sig).unwrap_or_default()
    }

    /// Sign this message with the sender's keypair.
    #[must_use]
    pub fn signed(mut self, keypair: &MeshKeyPair) -> Self {
        self.public_key = keypair.public_key_hex();
        self.signature = keypair.sign_hex(&self.signing_payload());
        self
    }

    /// Verify the signature against the public key carried on the message
    /// (self-consistent check — detects tampering and forgery).
    #[must_use]
    pub fn verify_signature(&self) -> bool {
        if self.public_key.is_empty() || self.signature.is_empty() {
            return false;
        }
        MeshKeyPair::verify_hex(&self.signing_payload(), &self.signature, &self.public_key)
    }

    /// Verify the message AND that the carried public key matches the key
    /// the community has bound to this sender. An impostor cannot reuse a
    /// peer ID with a different key.
    #[must_use]
    pub fn verify_as_sender(&self, bound_public_key: &str) -> bool {
        self.verify_signature() && self.public_key == bound_public_key
    }
}

// ── Sangha Chat ───────────────────────────────────────────────────────

/// On-disk chat log (persisted channel history).
#[derive(Debug, Serialize, Deserialize)]
struct ChatFile {
    version: u32,
    channels: HashMap<String, Vec<ChatMessage>>,
}

/// Inter-agent chat with topic-based channels.
///
/// Messages are fire-and-forget (async semantics in a real transport).
/// A message log is maintained per channel for late joiners. When a
/// persistence path is configured, the log survives restarts: every
/// mutation atomically rewrites the file, and restore re-verifies signed
/// messages (invalid signatures are dropped — tamper evidence at the
/// dequeue/restore boundary).
pub struct SanghaChat {
    next_msg_id: u64,
    /// Messages per channel.
    channels: HashMap<String, Vec<ChatMessage>>,
    /// Max messages per channel.
    max_per_channel: usize,
    /// Total messages sent.
    total_messages: u64,
    /// Ed25519 keypair — signs every message sent by this node and is
    /// used to verify on read when configured.
    signing_key: Option<MeshKeyPair>,
    /// Optional persistence path (store-root file). `None` = in-memory.
    persistence: Option<std::path::PathBuf>,
    /// Replay protection (S9): bounded seen-payload window, keyed on the
    /// FNV-1a hash of each message's signing payload (sender + channel +
    /// content + timestamp — the exact bytes the signature commits). A
    /// captured packet re-injected verbatim hashes identically and is
    /// dropped; a re-sent message (mail-slot flush re-signs with a fresh
    /// timestamp) hashes differently and passes.
    ///
    /// NOT the message `id`: remote chat ids are not carried across the
    /// send_chat RPC (they arrive as 0), so ids cannot discriminate.
    seen_hashes: SeenHashes,
}

/// Bounded FIFO set of seen payload hashes for replay rejection. When
/// the cap is reached the oldest hashes fall out first (an attacker who
/// floods enough distinct payloads can eventually re-admit an old
/// replay — the cap is sized so that requires sustained flooding, which
/// signatures and quarantine make traceable).
#[derive(Default)]
struct SeenHashes {
    queue: std::collections::VecDeque<u64>,
    set: std::collections::HashSet<u64>,
    cap: usize,
}

impl SeenHashes {
    fn new(cap: usize) -> Self {
        Self {
            queue: std::collections::VecDeque::new(),
            set: std::collections::HashSet::new(),
            cap,
        }
    }

    /// Returns `true` if the hash is fresh (first sighting), recording it.
    fn check_and_insert(&mut self, hash: u64) -> bool {
        if self.set.contains(&hash) {
            return false;
        }
        if self.queue.len() >= self.cap {
            if let Some(old) = self.queue.pop_front() {
                self.set.remove(&old);
            }
        }
        self.queue.push_back(hash);
        self.set.insert(hash);
        true
    }
}

/// Default seen-payload window for replay rejection.
const SEEN_HASHES_CAP: usize = 8192;

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
            .field("signed", &self.signing_key.is_some())
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
            signing_key: None,
            persistence: None,
            seen_hashes: SeenHashes::new(SEEN_HASHES_CAP),
        }
    }

    /// Configure the node's Ed25519 keypair so every message is signed
    /// on send and can be verified on read.
    #[must_use]
    pub fn with_signing_key(mut self, keypair: MeshKeyPair) -> Self {
        self.signing_key = Some(keypair);
        self
    }

    /// Configure persistence: the channel log survives restarts. Any
    /// existing log at the path is restored immediately (signed messages
    /// re-verified; invalid signatures dropped).
    #[must_use]
    pub fn with_persistence(mut self, path: Option<std::path::PathBuf>) -> Self {
        if let Some(p) = &path {
            self.restore_from(p);
        }
        self.persistence = path;
        self
    }

    /// Whether this chat is signing messages.
    #[must_use]
    pub const fn is_signing(&self) -> bool {
        self.signing_key.is_some()
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
            public_key: String::new(),
        };
        if let Some(keypair) = &self.signing_key {
            msg = msg.signed(keypair);
        }
        self.next_msg_id += 1;
        self.total_messages += 1;

        let msgs = self.channels.entry(channel.to_string()).or_default();
        if msgs.len() >= self.max_per_channel {
            msgs.remove(0);
        }
        msgs.push(msg.clone());
        self.persist_now();
        msg
    }

    /// Send a message **as a specific peer**, signing it with that peer's
    /// keypair.
    ///
    /// Used by mesh relays that forward messages on behalf of the
    /// originating peer — the signature proves the peer, not the relay,
    /// authored the message.
    pub fn send_as(
        &mut self,
        channel: &str,
        sender: &str,
        content: impl Into<String>,
        keypair: &MeshKeyPair,
    ) -> ChatMessage {
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
            signature: String::new(),
            public_key: String::new(),
        }
        .signed(keypair);
        self.next_msg_id += 1;
        self.total_messages += 1;

        let msgs = self.channels.entry(channel.to_string()).or_default();
        if msgs.len() >= self.max_per_channel {
            msgs.remove(0);
        }
        msgs.push(msg.clone());
        self.persist_now();
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

    /// Read messages from a channel, protected by the community rule:
    /// only messages that **verify against the sender's bound public key
    /// and come from a non-quarantined sender** are returned. A bad
    /// apple's messages are cut off without disrupting the rest of the
    /// channel.
    ///
    /// `bindings` maps sender peer ID → the public key the community has
    /// bound to it. Messages whose carried public key does not match the
    /// binding are rejected (identity theft).
    #[must_use]
    pub fn read_trusted(
        &self,
        channel: &str,
        after_id: Option<u64>,
        bindings: &HashMap<String, String>,
        quarantined: &[String],
    ) -> Vec<ChatMessage> {
        let Some(msgs) = self.channels.get(channel) else {
            return Vec::new();
        };
        msgs.iter()
            .filter(|m| after_id.is_none_or(|id| m.id > id))
            .filter(|m| {
                bindings
                    .get(&m.sender)
                    .is_some_and(|pk| m.verify_as_sender(pk))
            })
            .filter(|m| !quarantined.iter().any(|q| q == &m.sender))
            .cloned()
            .collect()
    }

    /// Store a pre-signed message received from the network as-is.
    ///
    /// The signature is preserved so verification passes later can judge
    /// it against the sender's bound public key (unlike [`send`], which
    /// signs with this node's own keypair).
    ///
    /// S9: a message whose id is already in the replay window is dropped
    /// — a captured packet re-injected verbatim verifies perfectly, so
    /// freshness is enforced here, not by the signature.
    pub fn inject_signed(&mut self, msg: ChatMessage) {
        let payload_hash = crate::replay::fnv1a64(msg.signing_payload().as_bytes());
        if !self.seen_hashes.check_and_insert(payload_hash) {
            tracing::debug!(msg_id = msg.id, "rejected replayed chat message (S9)");
            return;
        }
        self.next_msg_id = self.next_msg_id.max(msg.id + 1);
        self.total_messages += 1;
        let msgs = self.channels.entry(msg.channel.clone()).or_default();
        if msgs.len() >= self.max_per_channel {
            msgs.remove(0);
        }
        msgs.push(msg);
        self.persist_now();
    }

    /// Purge every message sent by a peer from the log — used when the
    /// peer is quarantined, so the bad apple's words do not linger in
    /// the community's channels. Returns the number of messages removed.
    pub fn purge_sender(&mut self, sender: &str, channel: Option<&str>) -> usize {
        let mut removed = 0usize;
        match channel {
            Some(ch) => {
                if let Some(msgs) = self.channels.get_mut(ch) {
                    let before = msgs.len();
                    msgs.retain(|m| m.sender != sender);
                    removed = before - msgs.len();
                }
            }
            None => {
                for msgs in self.channels.values_mut() {
                    let before = msgs.len();
                    msgs.retain(|m| m.sender != sender);
                    removed += before - msgs.len();
                }
            }
        }
        if removed > 0 {
            self.persist_now();
        }
        removed
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

    /// Restore the channel log from disk (with_persistence). Signed
    /// messages are RE-VERIFIED at the restore boundary — validate on
    /// dequeue, not only on enqueue. Invalid signatures are dropped
    /// (tamper evidence); unsigned legacy messages are kept (the
    /// trusted-transport era's format).
    fn restore_from(&mut self, path: &std::path::Path) {
        let text = match std::fs::read_to_string(path) {
            Ok(t) => t,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return,
            Err(e) => {
                tracing::warn!(path = %path.display(), error = %e, "mesh chat log unreadable — starting fresh");
                return;
            }
        };
        let file: ChatFile = match serde_json::from_str(&text) {
            Ok(f) => f,
            Err(e) => {
                tracing::warn!(path = %path.display(), error = %e, "mesh chat log corrupt — starting fresh");
                return;
            }
        };
        let mut restored = 0usize;
        let mut dropped = 0usize;
        for (channel, msgs) in file.channels {
            for msg in msgs {
                if !msg.signature.is_empty() && !msg.verify_signature() {
                    dropped += 1;
                    continue;
                }
                self.next_msg_id = self.next_msg_id.max(msg.id + 1);
                self.channels.entry(channel.clone()).or_default().push(msg);
                restored += 1;
            }
        }
        tracing::info!(
            path = %path.display(),
            restored,
            dropped_invalid = dropped,
            "mesh chat log restored"
        );
    }

    /// Atomic tmp-rename persistence of the channel log (write-budget
    /// ledger pattern). Errors are logged, never fatal.
    fn persist_now(&self) {
        let Some(path) = &self.persistence else {
            return;
        };
        let file = ChatFile {
            version: 1,
            channels: self.channels.clone(),
        };
        let text = match serde_json::to_string(&file) {
            Ok(t) => t,
            Err(e) => {
                tracing::warn!(path = %path.display(), error = %e, "mesh chat log serialize failed");
                return;
            }
        };
        let tmp = path.with_file_name(format!(
            "{}.tmp",
            path.file_name().map_or_else(
                || "mesh_chat_log.json".to_string(),
                |n| n.to_string_lossy().to_string()
            )
        ));
        if let Err(e) = std::fs::write(&tmp, text) {
            tracing::warn!(path = %tmp.display(), error = %e, "mesh chat log write failed");
            return;
        }
        if let Err(e) = std::fs::rename(&tmp, path) {
            tracing::warn!(path = %path.display(), error = %e, "mesh chat log rename failed");
        }
    }

    /// Verify all messages in a channel against the mesh key.
    ///
    /// Returns the count of verified vs rejected messages. When the chat
    /// is not signing, verification is a no-op (all messages pass through
    /// as unchecked — use [`with_mesh_key`](Self::with_mesh_key) to
    /// enforce signatures).
    #[must_use]
    pub fn verify_channel(&self, channel: &str) -> VerificationReport {
        let Some(_keypair) = &self.signing_key else {
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
                if msg.verify_signature() {
                    report.verified += 1;
                } else {
                    report.rejected += 1;
                }
            }
        }
        report
    }

    /// Verify a channel with identity binding: each message must be signed
    /// by the public key the community has bound to its sender. Catches
    /// impostor keys, not just tampering.
    #[must_use]
    pub fn verify_channel_bound(
        &self,
        channel: &str,
        bindings: &HashMap<String, String>,
    ) -> VerificationReport {
        if self.signing_key.is_none() {
            let checked = self.channel_message_count(channel);
            return VerificationReport {
                checked,
                verified: checked,
                rejected: 0,
                mesh_signing: false,
            };
        }
        let mut report = VerificationReport {
            mesh_signing: true,
            ..VerificationReport::default()
        };
        if let Some(msgs) = self.channels.get(channel) {
            for msg in msgs {
                report.checked += 1;
                if bindings
                    .get(&msg.sender)
                    .is_some_and(|pk| msg.verify_as_sender(pk))
                {
                    report.verified += 1;
                } else {
                    report.rejected += 1;
                }
            }
        }
        report
    }

    /// Verify all messages in every channel with identity binding.
    #[must_use]
    pub fn verify_all_bound(&self, bindings: &HashMap<String, String>) -> VerificationReport {
        if self.signing_key.is_none() {
            return VerificationReport {
                checked: self.total_messages as usize,
                verified: self.total_messages as usize,
                rejected: 0,
                mesh_signing: false,
            };
        }
        let mut report = VerificationReport {
            checked: 0,
            verified: 0,
            rejected: 0,
            mesh_signing: true,
        };
        for msgs in self.channels.values() {
            for msg in msgs {
                report.checked += 1;
                if bindings
                    .get(&msg.sender)
                    .is_some_and(|pk| msg.verify_as_sender(pk))
                {
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
        if self.signing_key.is_none() {
            return VerificationReport {
                checked: self.total_messages as usize,
                verified: self.total_messages as usize,
                rejected: 0,
                mesh_signing: false,
            };
        }
        let mut report = VerificationReport {
            checked: 0,
            verified: 0,
            rejected: 0,
            mesh_signing: true,
        };
        for msgs in self.channels.values() {
            for msg in msgs {
                report.checked += 1;
                if msg.verify_signature() {
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
            public_key: String::new(),
        };
        let json = msg.to_json();
        assert_eq!(json["id"], 1);
        assert_eq!(json["channel"], "test");
        assert_eq!(json["content"], "hello");
    }

    #[test]
    fn signed_message_verifies_and_detects_tampering() {
        let kp = MeshKeyPair::from_seed(b"node-1-seed");
        let msg = ChatMessage {
            id: 1,
            channel: "gana:1".to_string(),
            sender: "node-1".to_string(),
            content: "coordinate on exploit".to_string(),
            timestamp: 12345,
            signature: String::new(),
            public_key: String::new(),
        };
        let signed = msg.signed(&kp);
        assert!(!signed.signature.is_empty());
        assert_eq!(signed.public_key, kp.public_key_hex());
        assert!(signed.verify_signature());
        // Identity binding: the carried key must match the bound key.
        assert!(signed.verify_as_sender(&kp.public_key_hex()));
        assert!(!signed.verify_as_sender(&MeshKeyPair::from_seed(b"other").public_key_hex()));

        // Wrong key → rejected (an imposter peer cannot forge messages).
        let other = MeshKeyPair::from_seed(b"other-seed");
        assert!(!MeshKeyPair::verify_hex(
            &signed.signing_payload(),
            &signed.signature,
            &other.public_key_hex()
        ));

        // Tampered content → rejected.
        let mut tampered = signed;
        tampered.content = "coordinate on something else".to_string();
        assert!(!tampered.verify_signature());

        // Unsigned message never verifies.
        let unsigned = ChatMessage {
            id: 1,
            channel: "gana:1".to_string(),
            sender: "node-1".to_string(),
            content: "coordinate on exploit".to_string(),
            timestamp: 12345,
            signature: String::new(),
            public_key: String::new(),
        };
        assert!(!unsigned.verify_signature());
    }

    #[test]
    fn chat_signs_messages_when_key_configured() {
        let mut chat = SanghaChat::new(100).with_signing_key(MeshKeyPair::from_seed(b"node-seed"));
        let msg = chat.send("project:alpha", "node-1", "delegating task");
        assert!(!msg.signature.is_empty());
        assert!(msg.verify_signature());

        let report = chat.verify_channel("project:alpha");
        assert!(report.mesh_signing);
        assert!(report.is_clean());
        assert_eq!(report.checked, 1);
        assert_eq!(report.verified, 1);
    }

    #[test]
    fn verification_rejects_forged_messages() {
        let mut chat = SanghaChat::new(100).with_signing_key(MeshKeyPair::from_seed(b"node-seed"));
        chat.send("gana:1", "node-1", "legit");

        // An attacker injects a message signed with a different key (or unsigned).
        let forged = ChatMessage {
            id: 99,
            channel: "gana:1".to_string(),
            sender: "node-1".to_string(),
            content: "run rm -rf".to_string(),
            timestamp: 1,
            signature: String::new(),
            public_key: String::new(),
        }
        .signed(&MeshKeyPair::from_seed(b"attacker-seed"));
        chat.channels.get_mut("gana:1").unwrap().push(forged);

        // Self-consistent verification catches tampering but not impostor
        // keys — the *bound* verification rejects the forged message.
        let bindings = HashMap::from([(
            "node-1".to_string(),
            MeshKeyPair::from_seed(b"node-seed").public_key_hex(),
        )]);
        let report = chat.verify_all_bound(&bindings);
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
    fn replayed_chat_payload_rejected_fresh_payload_accepted() {
        let mut chat = SanghaChat::new(10);
        let make = |ts: i64, content: &str| ChatMessage {
            id: 0, // remote chat ids arrive as 0 across the send_chat RPC
            channel: "gana:room".to_string(),
            sender: "peer-a".to_string(),
            content: content.to_string(),
            timestamp: ts,
            signature: String::new(),
            public_key: String::new(),
        };

        chat.inject_signed(make(1_000, "hello"));
        // Byte-identical re-injection (a captured packet) — dropped.
        chat.inject_signed(make(1_000, "hello"));
        assert_eq!(
            chat.read("gana:room", None).len(),
            1,
            "replay must be dropped"
        );

        // Same content, different timestamp (the mail-slot flush re-signs
        // with a fresh clock) — a genuinely new delivery, accepted.
        chat.inject_signed(make(2_000, "hello"));
        assert_eq!(
            chat.read("gana:room", None).len(),
            2,
            "re-signed re-delivery must not be mistaken for a replay"
        );
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
