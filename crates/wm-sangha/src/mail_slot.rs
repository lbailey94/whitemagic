//! Bounded store-and-forward mail slot (sender side).
//!
//! The IETF profile (`draft-chapman-a2a-offline-delivery-00`) models
//! recipient-side queues behind an always-on endpoint. Our p2p mesh has no
//! relay: the observed failure is a SENDER dialing an OFFLINE peer — send
//! fails, nothing is queued anywhere, and the sender must remember. This
//! module is the sender-side divergence (documented in
//! `docs/MESH_JOIN_PROTOCOL.md`): messages that could not be delivered are
//! stored per destination peer, bounded, persisted across restarts, and
//! flushed FIFO on the next successful join.
//!
//! Bounds (published, IETF MUST): reference bounds adopted — 500 messages,
//! 2 MiB total, 50 pending per peer, 7-day TTL. Exceeding a bound is a
//! distinct `asleep_queue_full` rejection with a `kind`, never a silent
//! drop.

use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

/// Maximum messages queued globally.
pub const MAX_QUEUED_MESSAGES: usize = 500;
/// Maximum total queued bytes (content bytes summed).
pub const MAX_QUEUED_BYTES: usize = 2 * 1024 * 1024;
/// Maximum pending messages per destination peer.
pub const MAX_PENDING_PER_PEER: usize = 50;
/// Queue TTL: entries older than this are purged undelivered.
pub const DEFAULT_TTL_SECS: u64 = 7 * 24 * 3600;

/// One stored message awaiting delivery.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueuedMessage {
    /// Unique mail id (`mail-<millis>-<seq>`).
    pub id: String,
    /// Destination address (`host:port`) the message is bound for.
    pub peer: String,
    /// Chat channel.
    pub channel: String,
    /// Sender peer id (this node at enqueue time).
    pub sender: String,
    /// Message content.
    pub content: String,
    /// Enqueue time (unix seconds) — TTL clock.
    pub queued_at: i64,
    /// Delivery attempts so far (failed flushes increment).
    pub attempts: u32,
}

/// Which bound rejected an enqueue (IETF `asleep_queue_full` `kind`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum QueueFullKind {
    /// Global message-count cap.
    Messages,
    /// Global byte cap.
    Bytes,
    /// Per-peer pending cap.
    Peer,
}

impl std::fmt::Display for QueueFull {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "asleep_queue_full ({:?})", self.kind)
    }
}

/// An enqueue rejected because a bound would be exceeded. Distinct from
/// any availability error: the message was NOT stored.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct QueueFull {
    pub kind: QueueFullKind,
}

/// Tunables (the published bounds).
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct MailSlotConfig {
    pub max_messages: usize,
    pub max_bytes: usize,
    pub max_per_peer: usize,
    pub ttl_secs: u64,
}

impl Default for MailSlotConfig {
    fn default() -> Self {
        Self {
            max_messages: MAX_QUEUED_MESSAGES,
            max_bytes: MAX_QUEUED_BYTES,
            max_per_peer: MAX_PENDING_PER_PEER,
            ttl_secs: DEFAULT_TTL_SECS,
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
struct MailFile {
    version: u32,
    bounds: MailSlotConfig,
    entries: Vec<QueuedMessage>,
}

/// The bounded, optionally-persistent outbound queue.
pub struct MailSlot {
    config: MailSlotConfig,
    entries: Vec<QueuedMessage>,
    path: Option<PathBuf>,
    seq: u64,
}

impl MailSlot {
    /// An in-memory slot (no persistence).
    #[must_use]
    pub const fn new(config: MailSlotConfig) -> Self {
        Self {
            config,
            entries: Vec::new(),
            path: None,
            seq: 0,
        }
    }

    /// A slot restored from disk (missing or corrupt file starts fresh —
    /// the corrupt-ledger recovery pattern from the write-budget ledger).
    #[must_use]
    pub fn restore(config: MailSlotConfig, path: PathBuf) -> Self {
        let mut slot = Self::new(config);
        match std::fs::read_to_string(&path) {
            Ok(text) => match serde_json::from_str::<MailFile>(&text) {
                Ok(file) => {
                    slot.entries = file.entries;
                    slot.seq = slot.entries.len() as u64;
                    tracing::info!(path = %path.display(), queued = slot.entries.len(), "mesh mail slot restored");
                }
                Err(e) => {
                    tracing::warn!(path = %path.display(), error = %e, "mesh mail slot file corrupt — starting fresh");
                }
            },
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
            Err(e) => {
                tracing::warn!(path = %path.display(), error = %e, "mesh mail slot unreadable — starting fresh");
            }
        }
        slot.path = Some(path);
        slot
    }

    /// Enqueue a message for `peer`. Applies bounds AFTER purging expired
    /// entries; returns the mail id or the bound that rejected it.
    ///
    /// # Errors
    /// [`QueueFull`] when any published bound would be exceeded.
    pub fn enqueue(
        &mut self,
        peer: &str,
        channel: &str,
        sender: &str,
        content: &str,
    ) -> Result<String, QueueFull> {
        self.purge_expired();

        if self.entries.len() >= self.config.max_messages {
            return Err(QueueFull {
                kind: QueueFullKind::Messages,
            });
        }
        if self.bytes_used() + content.len() > self.config.max_bytes {
            return Err(QueueFull {
                kind: QueueFullKind::Bytes,
            });
        }
        if self.depth_for(peer) >= self.config.max_per_peer {
            return Err(QueueFull {
                kind: QueueFullKind::Peer,
            });
        }

        self.seq = self.seq.wrapping_add(1);
        let id = format!(
            "mail-{}-{:04}",
            chrono::Utc::now().timestamp_millis(),
            self.seq % 10_000
        );
        self.entries.push(QueuedMessage {
            id,
            peer: peer.to_string(),
            channel: channel.to_string(),
            sender: sender.to_string(),
            content: content.to_string(),
            queued_at: chrono::Utc::now().timestamp(),
            attempts: 0,
        });
        self.persist();
        Ok(self
            .entries
            .last()
            .map(|m| m.id.clone())
            .unwrap_or_default())
    }

    /// Purge entries past their TTL. Returns the number purged.
    pub fn purge_expired(&mut self) -> usize {
        let now = chrono::Utc::now().timestamp();
        let before = self.entries.len();
        self.entries.retain(|m| {
            now - m.queued_at <= i64::try_from(self.config.ttl_secs).unwrap_or(i64::MAX)
        });
        let purged = before - self.entries.len();
        if purged > 0 {
            self.persist();
        }
        purged
    }

    /// Pending count for one peer.
    #[must_use]
    pub fn depth_for(&self, peer: &str) -> usize {
        self.entries.iter().filter(|m| m.peer == peer).count()
    }

    /// Total pending count.
    #[must_use]
    pub fn total(&self) -> usize {
        self.entries.len()
    }

    /// Total queued content bytes.
    #[must_use]
    pub fn bytes_used(&self) -> usize {
        self.entries.iter().map(|m| m.content.len()).sum()
    }

    /// FIFO snapshot of one peer's pending mail.
    #[must_use]
    pub fn entries_for(&self, peer: &str) -> Vec<QueuedMessage> {
        self.entries
            .iter()
            .filter(|m| m.peer == peer)
            .cloned()
            .collect()
    }

    /// Remove delivered/invalidated entries by id. Returns how many went.
    pub fn remove_ids(&mut self, ids: &[String]) -> usize {
        let before = self.entries.len();
        self.entries.retain(|m| !ids.contains(&m.id));
        let removed = before - self.entries.len();
        if removed > 0 {
            self.persist();
        }
        removed
    }

    /// Record a failed delivery attempt on one message.
    pub fn record_attempt(&mut self, id: &str) {
        if let Some(m) = self.entries.iter_mut().find(|m| m.id == id) {
            m.attempts = m.attempts.saturating_add(1);
            self.persist();
        }
    }

    /// Drop one message by id (operator action). Returns whether it existed.
    pub fn drop_message(&mut self, id: &str) -> bool {
        let before = self.entries.len();
        self.entries.retain(|m| m.id != id);
        let dropped = before - self.entries.len();
        if dropped > 0 {
            self.persist();
        }
        dropped > 0
    }

    /// Distinct destination peers with pending mail.
    #[must_use]
    pub fn pending_peers(&self) -> Vec<String> {
        let mut peers: Vec<String> = Vec::new();
        for m in &self.entries {
            if !peers.contains(&m.peer) {
                peers.push(m.peer.clone());
            }
        }
        peers
    }

    /// All pending entries (FIFO), for operator listing.
    #[must_use]
    pub fn entries(&self) -> &[QueuedMessage] {
        &self.entries
    }

    /// The published bounds as JSON (IETF MUST publish actual bounds).
    #[must_use]
    pub fn bounds(&self) -> serde_json::Value {
        serde_json::json!({
            "max_messages": self.config.max_messages,
            "max_bytes": self.config.max_bytes,
            "max_per_peer": self.config.max_per_peer,
            "ttl_secs": self.config.ttl_secs,
        })
    }

    /// Status summary for `/status` and the mail tool.
    #[must_use]
    pub fn summary(&self) -> serde_json::Value {
        let mut per_peer = serde_json::Map::new();
        for peer in self.pending_peers() {
            per_peer.insert(peer.clone(), serde_json::json!(self.depth_for(&peer)));
        }
        serde_json::json!({
            "queued_total": self.total(),
            "queued_bytes": self.bytes_used(),
            "per_peer": per_peer,
            "bounds": self.bounds(),
            "persisted": self.path.is_some(),
        })
    }

    /// Atomic tmp-rename persistence (write-budget ledger pattern).
    /// Errors are logged, never fatal — the mesh keeps running.
    fn persist(&self) {
        let Some(path) = &self.path else {
            return;
        };
        let file = MailFile {
            version: 1,
            bounds: self.config,
            entries: self.entries.clone(),
        };
        let text = match serde_json::to_string_pretty(&file) {
            Ok(t) => t,
            Err(e) => {
                tracing::warn!(path = %path.display(), error = %e, "mesh mail slot serialize failed");
                return;
            }
        };
        let tmp = tmp_path(path);
        if let Err(e) = std::fs::write(&tmp, text) {
            tracing::warn!(path = %tmp.display(), error = %e, "mesh mail slot write failed");
            return;
        }
        if let Err(e) = std::fs::rename(&tmp, path) {
            tracing::warn!(path = %path.display(), error = %e, "mesh mail slot rename failed");
        }
    }
}

fn tmp_path(path: &Path) -> PathBuf {
    let mut name = path.file_name().map_or_else(
        || "mesh_mail_slot.json.tmp".to_string(),
        |n| format!("{}.tmp", n.to_string_lossy()),
    );
    name.truncate(name.len());
    path.with_file_name(name)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn slot() -> MailSlot {
        MailSlot::new(MailSlotConfig {
            max_messages: 10,
            max_bytes: 1_000,
            max_per_peer: 3,
            ttl_secs: 7 * 24 * 3600,
        })
    }

    #[test]
    fn enqueue_is_fifo_with_ids() {
        let mut s = slot();
        let a = s.enqueue("p1", "general", "me", "first").unwrap();
        let b = s.enqueue("p1", "general", "me", "second").unwrap();
        assert_ne!(a, b);
        let pending = s.entries_for("p1");
        assert_eq!(pending.len(), 2);
        assert_eq!(pending[0].content, "first");
        assert_eq!(pending[1].content, "second");
        assert_eq!(s.total(), 2);
    }

    #[test]
    fn per_peer_bound_rejects_with_peer_kind() {
        let mut s = slot();
        for i in 0..3 {
            s.enqueue("p1", "c", "me", &format!("m{i}")).unwrap();
        }
        let err = s.enqueue("p1", "c", "me", "over").unwrap_err();
        assert_eq!(err.kind, QueueFullKind::Peer);
        // Other peers unaffected.
        s.enqueue("p2", "c", "me", "ok").unwrap();
    }

    #[test]
    fn global_message_bound_rejects_with_messages_kind() {
        let mut s = slot();
        // Fill the global cap across peers (each stays under per-peer 3).
        for i in 0..10 {
            s.enqueue(&format!("p{i}"), "c", "me", "x").unwrap();
        }
        let err = s.enqueue("p10", "c", "me", "over").unwrap_err();
        assert_eq!(err.kind, QueueFullKind::Messages);
    }

    #[test]
    fn byte_bound_rejects_with_bytes_kind() {
        let mut s = slot();
        let err = s.enqueue("p1", "c", "me", &"x".repeat(1_001)).unwrap_err();
        assert_eq!(err.kind, QueueFullKind::Bytes);
    }

    #[test]
    fn ttl_purge_drops_expired_entries() {
        let mut s = slot();
        s.enqueue("p1", "c", "me", "stale").unwrap();
        // Backdate past the TTL.
        if let Some(m) = s.entries.first_mut() {
            m.queued_at -= i64::try_from(s.config.ttl_secs).unwrap_or(i64::MAX) + 10;
        }
        assert_eq!(s.purge_expired(), 1);
        assert_eq!(s.total(), 0);
    }

    #[test]
    fn remove_ids_and_attempts_track_state() {
        let mut s = slot();
        let a = s.enqueue("p1", "c", "me", "keep").unwrap();
        let b = s.enqueue("p1", "c", "me", "drop-me").unwrap();
        s.record_attempt(&a);
        assert_eq!(s.entries_for("p1")[0].attempts, 1);
        assert_eq!(s.remove_ids(std::slice::from_ref(&b)), 1);
        assert_eq!(s.total(), 1);
        assert!(s.drop_message(&a));
        assert_eq!(s.total(), 0);
    }

    #[test]
    fn persistence_roundtrip_across_instances() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("mesh_mail_slot.json");
        {
            let mut s = MailSlot::restore(MailSlotConfig::default(), path.clone());
            s.enqueue("10.0.0.9:7369", "general", "me", "survives restart")
                .unwrap();
        }
        // A fresh instance (process restart analog) sees the same queue.
        let s = MailSlot::restore(MailSlotConfig::default(), path);
        assert_eq!(s.total(), 1);
        assert_eq!(
            s.entries_for("10.0.0.9:7369")[0].content,
            "survives restart"
        );
    }

    #[test]
    fn corrupt_file_starts_fresh() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("mesh_mail_slot.json");
        std::fs::write(&path, "not json at all").unwrap();
        let s = MailSlot::restore(MailSlotConfig::default(), path);
        assert_eq!(s.total(), 0);
        // And the slot still works.
        let mut s = s;
        s.enqueue("p1", "c", "me", "after corruption").unwrap();
        assert_eq!(s.total(), 1);
    }

    #[test]
    fn bounds_are_published() {
        let s = slot();
        let b = s.bounds();
        assert_eq!(b["max_per_peer"], 3);
        assert!(b["ttl_secs"].as_u64().unwrap() > 0);
    }
}
