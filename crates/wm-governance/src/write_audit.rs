//! Write-audit journal — append-only store mutation journal.
//!
//! The karma ledger compares declared vs actual writes per dispatch; this
//! journal extends that comparison into a persisted, append-only record of
//! every dispatch's store mutations. Each entry captures the tool name, the
//! memory id and content hash it touched (when reported), a timestamp, and
//! declared vs actual writes — so misdeclarations become visible in
//! diagnostics (`wm doctor`) instead of slipping through silently.
//!
//! Entries are stored in the Karma galaxy under a `waj:` key prefix, which
//! the karma ledger's scans skip (they only read 8-byte id keys), so the two
//! append-only structures coexist in the same LMDB database.
//!
//! Actual writes are measured with the store's monotonic mutation counter.
//! The dispatch pipeline samples the counter at dispatch start
//! ([`WriteAuditJournal::dispatch_baseline`]) and each entry covers exactly
//! that window ([`WriteAuditJournal::record_since`]), so a dispatch is
//! attributed the mutations that happened *while it ran* — not whatever
//! accumulated since the previous entry. Journal and karma flushes write
//! through `put_raw_batch_untracked`: governance bookkeeping is not a memory
//! mutation, and letting it tick the counter landed whole batch flushes in
//! whichever read-only dispatch was in flight (the 2026-08-28 restore-drill
//! false positives). Concurrent in-process dispatches can still overlap
//! windows, so a write delta is best-effort evidence, not proof — the honest
//! ceiling is documented rather than hidden.

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};

use lmdb::{Cursor, Transaction};
use serde::{Deserialize, Serialize};
use wm_core::{CoreError, Galaxy, Result};
use wm_memory::MemoryStore;

/// Attributed actor for a dispatch — who was behind the tool call.
///
/// Attribution, not authentication: `user` is the MCP client's own
/// `_meta.user_id` label, asserted by the client and never verified
/// (same contract as the compartment controls). The journal records it
/// so an entry answers "which agent did this" — the first question any
/// incident investigation asks.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ActorIdentity {
    /// WM session id the dispatch ran inside (when known).
    pub session: Option<String>,
    /// Client-asserted user label from MCP `_meta`.
    pub user: Option<String>,
    /// Mandala compartment the dispatch ran under (when declared).
    pub compartment: Option<String>,
}

impl ActorIdentity {
    /// Snapshot the identity fields of a dispatch context.
    #[must_use]
    pub fn from_context(ctx: &wm_core::Context) -> Self {
        Self {
            session: ctx.session_id.map(|id| id.to_string()),
            user: ctx.user_id.clone(),
            compartment: ctx.compartment.clone(),
        }
    }
}

/// Auto-flush every N entries.
const DEFAULT_FLUSH_THRESHOLD: usize = 64;

/// Key prefix distinguishing journal entries from karma chain entries.
const KEY_PREFIX: &[u8] = b"waj:";

/// LMDB key holding the next journal entry ID.
const NEXT_ID_KEY: &[u8] = b"__waj_next_id__";

/// One journal entry — a dispatch's declared vs actual store mutations.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct WriteAuditEntry {
    /// Monotonic entry ID.
    pub id: u64,
    /// Unix timestamp (seconds) when the dispatch completed.
    pub timestamp: u64,
    /// Tool that was dispatched.
    pub tool: String,
    /// Memory id touched by the dispatch (when reported in args/output).
    pub memory_id: Option<String>,
    /// Content hash of the memory touched (when reported).
    pub content_hash: Option<String>,
    /// Attributed actor session (WM session id) when the dispatch ran
    /// inside one. `None` = unknown, not "no session".
    #[serde(default)]
    pub actor_session: Option<String>,
    /// Attributed actor user label from MCP `_meta.user_id`.
    /// Attribution, never authentication — the label is client-asserted.
    #[serde(default)]
    pub actor_user: Option<String>,
    /// Mandala compartment the dispatch ran under (when declared).
    #[serde(default)]
    pub actor_compartment: Option<String>,
    /// Whether the tool's `EffectRow` declared writes.
    pub declared_writes: bool,
    /// Write count reported by the tool's output (`writes` array).
    pub reported_writes: u32,
    /// Store mutation-counter delta observed while the dispatch ran.
    pub store_write_delta: u32,
    /// Whether the dispatch succeeded.
    pub success: bool,
}

impl WriteAuditEntry {
    /// Actual writes observed — the max of what the tool reported and what
    /// the store mutation counter measured.
    #[must_use]
    pub const fn actual_writes(&self) -> u32 {
        if self.reported_writes > self.store_write_delta {
            self.reported_writes
        } else {
            self.store_write_delta
        }
    }

    /// True when the store was mutated without a write declaration — the
    /// security-relevant misdeclaration direction.
    #[must_use]
    pub const fn undeclared_mutation(&self) -> bool {
        !self.declared_writes && self.actual_writes() > 0
    }
}

/// Append-only store mutation journal backed by LMDB.
pub struct WriteAuditJournal {
    store: Arc<MemoryStore>,
    next_id: AtomicU64,
    pending: Mutex<Vec<(Vec<u8>, Vec<u8>)>>,
    flush_threshold: usize,
    /// Baseline of the store mutation counter — deltas since the last
    /// record() call are attributed to the next dispatch.
    last_mutation_count: AtomicU64,
}

impl WriteAuditJournal {
    /// Open or create a journal backed by the given store.
    pub fn new(store: Arc<MemoryStore>) -> Result<Self> {
        Self::with_flush_threshold(store, DEFAULT_FLUSH_THRESHOLD)
    }

    /// Open with a custom auto-flush threshold (0 = flush every entry).
    pub fn with_flush_threshold(store: Arc<MemoryStore>, flush_threshold: usize) -> Result<Self> {
        let journal = Self {
            store,
            next_id: AtomicU64::new(0),
            pending: Mutex::new(Vec::new()),
            flush_threshold,
            last_mutation_count: AtomicU64::new(0),
        };
        journal.load_state()?;
        Ok(journal)
    }

    fn load_state(&self) -> Result<()> {
        if let Some(data) = self.store.get_raw(Galaxy::Karma, NEXT_ID_KEY)? {
            if data.len() >= 8 {
                let id = u64::from_be_bytes(data[..8].try_into().unwrap_or([0; 8]));
                self.next_id.store(id, Ordering::Relaxed);
            }
        }
        // Baseline: mutations made before this journal opened belong to
        // other processes/handles, not to future dispatches.
        self.last_mutation_count
            .store(self.store.mutation_count(), Ordering::Relaxed);
        Ok(())
    }

    /// Append one dispatch record.
    ///
    /// Legacy session-scoped attribution: the store mutation delta observed
    /// since the previous `record()` call is attributed to this dispatch.
    /// The dispatch pipeline uses [`Self::record_since`] with a baseline
    /// sampled at dispatch start instead; this method remains for direct
    /// callers and tests.
    #[allow(clippy::too_many_arguments)]
    pub fn record(
        &self,
        tool: &str,
        actor: ActorIdentity,
        memory_id: Option<&str>,
        content_hash: Option<&str>,
        declared_writes: bool,
        reported_writes: u32,
        success: bool,
    ) -> Result<WriteAuditEntry> {
        let current = self.store.mutation_count();
        let previous = self.last_mutation_count.swap(current, Ordering::Relaxed);
        let store_write_delta = current.saturating_sub(previous).min(u64::from(u32::MAX)) as u32;
        self.append_entry(
            store_write_delta,
            tool,
            actor,
            memory_id,
            content_hash,
            declared_writes,
            reported_writes,
            success,
        )
    }

    /// The store mutation counter as of "now" — sample this at dispatch
    /// start and pass it to [`Self::record_since`] so the journal attributes
    /// exactly the writes that happened while the dispatch ran.
    #[must_use]
    pub fn dispatch_baseline(&self) -> u64 {
        self.store.mutation_count()
    }

    /// Append one dispatch record attributed to the window since
    /// `dispatch_start` (see [`Self::dispatch_baseline`]).
    ///
    /// Under concurrent dispatches, windows can overlap; a delta remains
    /// best-effort evidence. Writes that happened *before* the baseline are
    /// never attributed — that cross-contamination (previous dispatches'
    /// writes and bookkeeping flushes landing on innocent read dispatches)
    /// is the false-positive class this method exists to close.
    #[allow(clippy::too_many_arguments)]
    pub fn record_since(
        &self,
        dispatch_start: u64,
        tool: &str,
        actor: ActorIdentity,
        memory_id: Option<&str>,
        content_hash: Option<&str>,
        declared_writes: bool,
        reported_writes: u32,
        success: bool,
    ) -> Result<WriteAuditEntry> {
        let current = self.store.mutation_count();
        let store_write_delta = current
            .saturating_sub(dispatch_start)
            .min(u64::from(u32::MAX)) as u32;
        self.append_entry(
            store_write_delta,
            tool,
            actor,
            memory_id,
            content_hash,
            declared_writes,
            reported_writes,
            success,
        )
    }

    /// Shared entry construction + pending buffer append + threshold flush.
    #[allow(clippy::too_many_arguments)]
    fn append_entry(
        &self,
        store_write_delta: u32,
        tool: &str,
        actor: ActorIdentity,
        memory_id: Option<&str>,
        content_hash: Option<&str>,
        declared_writes: bool,
        reported_writes: u32,
        success: bool,
    ) -> Result<WriteAuditEntry> {
        let id = self.next_id.fetch_add(1, Ordering::Relaxed);
        let timestamp = wm_core::time::now_unix_secs();

        let entry = WriteAuditEntry {
            id,
            timestamp,
            tool: tool.to_string(),
            memory_id: memory_id.map(str::to_string),
            content_hash: content_hash.map(str::to_string),
            actor_session: actor.session,
            actor_user: actor.user,
            actor_compartment: actor.compartment,
            declared_writes,
            reported_writes,
            store_write_delta,
            success,
        };

        let key = [KEY_PREFIX, &id.to_be_bytes()].concat();
        let val = serde_json::to_vec(&entry)
            .map_err(|e| CoreError::Memory(format!("write-audit serialize failed: {e}")))?;

        {
            let mut pending = self
                .pending
                .lock()
                .map_err(|_| CoreError::Tool("write-audit pending lock poisoned".to_string()))?;
            pending.push((key, val));
        }

        if self.flush_threshold == 0
            || self.pending.lock().map_or(0, |p| p.len()) >= self.flush_threshold
        {
            self.flush()?;
        }

        Ok(entry)
    }

    /// Flush all pending entries to LMDB in one batch transaction.
    ///
    /// Writes through `put_raw_batch_untracked`: the journal's own
    /// bookkeeping must not tick the store mutation counter, or every batch
    /// flush would be attributed as `entries.len()` writes to whichever
    /// dispatch was in flight.
    pub fn flush(&self) -> Result<()> {
        let entries = {
            let mut pending = self
                .pending
                .lock()
                .map_err(|_| CoreError::Tool("write-audit pending lock poisoned".to_string()))?;
            if pending.is_empty() {
                return Ok(());
            }
            std::mem::take(&mut *pending)
        };

        let next_id_bytes = self.next_id.load(Ordering::Relaxed).to_be_bytes();
        let mut batch: Vec<(&[u8], &[u8])> = Vec::with_capacity(entries.len() + 1);
        for (k, v) in &entries {
            batch.push((k.as_slice(), v.as_slice()));
        }
        batch.push((NEXT_ID_KEY, &next_id_bytes));
        self.store.put_raw_batch_untracked(Galaxy::Karma, &batch)
    }

    /// Number of pending entries not yet flushed to LMDB.
    #[must_use]
    pub fn pending_count(&self) -> usize {
        self.pending.lock().map_or(0, |p| p.len())
    }

    /// Next entry ID (for diagnostics).
    #[must_use]
    pub fn next_id(&self) -> u64 {
        self.next_id.load(Ordering::Relaxed)
    }

    /// Scan all journal entries in ID order.
    pub fn scan_entries(&self) -> Result<Vec<WriteAuditEntry>> {
        self.flush()?;
        let db = self.store.galaxy_db(Galaxy::Karma)?;
        let tx = self
            .store
            .env()
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;

        let mut cursor = tx
            .open_ro_cursor(db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor failed: {e}")))?;

        let mut entries = Vec::new();
        for (key, val) in cursor.iter() {
            if !key.starts_with(KEY_PREFIX) {
                continue;
            }
            if let Ok(entry) = serde_json::from_slice::<WriteAuditEntry>(val) {
                entries.push(entry);
            }
        }
        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;

        entries.sort_by_key(|e| e.id);
        Ok(entries)
    }

    /// Entries where a dispatch mutated the store without declaring writes.
    pub fn misdeclarations(&self) -> Result<Vec<WriteAuditEntry>> {
        Ok(self
            .scan_entries()?
            .into_iter()
            .filter(WriteAuditEntry::undeclared_mutation)
            .collect())
    }

    /// Number of undeclared-mutation entries (cheap summary for diagnostics).
    pub fn misdeclaration_count(&self) -> Result<usize> {
        Ok(self.misdeclarations()?.len())
    }

    /// Most recent N entries (newest last).
    pub fn recent(&self, n: usize) -> Result<Vec<WriteAuditEntry>> {
        let mut entries = self.scan_entries()?;
        let start = entries.len().saturating_sub(n);
        entries.drain(..start);
        Ok(entries)
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use wm_memory::Memory;

    fn make_store() -> Arc<MemoryStore> {
        let tmp = tempfile::tempdir().unwrap();
        Arc::new(MemoryStore::open_default(tmp.path()).unwrap())
    }

    #[test]
    fn record_and_scan_roundtrip() {
        let store = make_store();
        let journal = WriteAuditJournal::with_flush_threshold(store.clone(), 0).unwrap();

        // Simulate an actual store mutation, then record a dispatch.
        let mem = Memory::new(wm_core::Galaxy::Codex, "audit test".to_string());
        store.put(wm_core::Galaxy::Codex, &mem).unwrap();

        let entry = journal
            .record(
                "memory.create",
                ActorIdentity::default(),
                Some(&mem.metadata.id.to_string()),
                Some(&mem.metadata.content_hash),
                true,
                0,
                true,
            )
            .unwrap();

        assert_eq!(entry.id, 0);
        assert!(entry.declared_writes);
        assert!(entry.store_write_delta >= 1, "delta should observe the put");
        let id_str = mem.metadata.id.to_string();
        assert_eq!(entry.memory_id.as_deref(), Some(id_str.as_str()));

        let entries = journal.scan_entries().unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0], entry);
    }

    #[test]
    fn misdeclaration_detected_when_undeclared_write_observed() {
        let store = make_store();
        let journal = WriteAuditJournal::with_flush_threshold(store.clone(), 0).unwrap();

        let mem = Memory::new(wm_core::Galaxy::Codex, "sneaky write".to_string());
        store.put(wm_core::Galaxy::Codex, &mem).unwrap();

        // Tool declared no writes, but the store counter moved.
        journal
            .record(
                "sneaky.read",
                ActorIdentity::default(),
                None,
                None,
                false,
                0,
                true,
            )
            .unwrap();

        let mis = journal.misdeclarations().unwrap();
        assert_eq!(mis.len(), 1);
        assert_eq!(mis[0].tool, "sneaky.read");
        assert!(mis[0].undeclared_mutation());
    }

    #[test]
    fn declared_write_without_mutation_is_not_a_misdeclaration() {
        let store = make_store();
        let journal = WriteAuditJournal::with_flush_threshold(store, 0).unwrap();

        // No store mutation happens; tool declares writes and succeeds.
        journal
            .record(
                "memory.delete",
                ActorIdentity::default(),
                Some("missing-id"),
                None,
                true,
                0,
                true,
            )
            .unwrap();

        assert!(journal.misdeclarations().unwrap().is_empty());
    }

    #[test]
    fn persistence_across_instances() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());

        let journal = WriteAuditJournal::with_flush_threshold(store.clone(), 0).unwrap();
        for i in 0..5u64 {
            let mem = Memory::new(wm_core::Galaxy::Codex, format!("m{i}"));
            store.put(wm_core::Galaxy::Codex, &mem).unwrap();
            journal
                .record(
                    "memory.create",
                    ActorIdentity::default(),
                    Some(&mem.metadata.id.to_string()),
                    None,
                    true,
                    0,
                    true,
                )
                .unwrap();
        }
        assert_eq!(journal.next_id(), 5);

        // New journal over the same store sees all entries.
        let journal2 = WriteAuditJournal::new(store).unwrap();
        assert_eq!(journal2.next_id(), 5);
        assert_eq!(journal2.scan_entries().unwrap().len(), 5);
    }

    #[test]
    fn karma_scans_ignore_journal_entries() {
        let store = make_store();

        // Interleave karma entries and journal entries in the same galaxy.
        let ledger = crate::KarmaLedger::with_flush_threshold(store.clone(), 0).unwrap();
        let journal = WriteAuditJournal::with_flush_threshold(store, 0).unwrap();

        ledger.record("memory.create", true, 1, true).unwrap();
        ledger.record("memory.read", false, 0, true).unwrap();
        journal
            .record(
                "memory.create",
                ActorIdentity::default(),
                None,
                None,
                true,
                0,
                true,
            )
            .unwrap();

        let karma_entries = ledger.scan_entries().unwrap();
        assert_eq!(karma_entries.len(), 2, "karma scan must skip waj: keys");
        assert_eq!(journal.scan_entries().unwrap().len(), 1);
        assert!(ledger.verify_integrity().unwrap().valid);
    }

    // ── Per-dispatch attribution (2026-08-28 restore-drill fix) ───────

    fn put_one(store: &MemoryStore, content: &str) -> wm_memory::Memory {
        let mem = Memory::new(wm_core::Galaxy::Codex, content.to_string());
        store.put(wm_core::Galaxy::Codex, &mem).unwrap();
        mem
    }

    #[test]
    fn record_captures_actor_identity() {
        let store = make_store();
        let journal = WriteAuditJournal::with_flush_threshold(store, 0).unwrap();

        let actor = ActorIdentity {
            session: Some("4e3ece8c-4e59-4486-8f07-91945337e361".to_string()),
            user: Some("lucas".to_string()),
            compartment: Some("production".to_string()),
        };
        let entry = journal
            .record(
                "memory.update",
                actor,
                Some("mem-1"),
                Some("hash-1"),
                true,
                0,
                true,
            )
            .unwrap();

        assert_eq!(
            entry.actor_session.as_deref(),
            Some("4e3ece8c-4e59-4486-8f07-91945337e361")
        );
        assert_eq!(entry.actor_user.as_deref(), Some("lucas"));
        assert_eq!(entry.actor_compartment.as_deref(), Some("production"));

        let entries = journal.scan_entries().unwrap();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0], entry, "identity survives the LMDB roundtrip");
    }

    #[test]
    fn legacy_entry_without_actor_fields_deserializes() {
        // Pre-S11b journaled entries have no actor fields; serde defaults
        // must admit them (the Karma galaxy holds live history).
        let legacy = serde_json::json!({
            "id": 7u64,
            "timestamp": 1_700_000_000u64,
            "tool": "memory.update",
            "memory_id": null,
            "content_hash": "abc",
            "declared_writes": true,
            "reported_writes": 1,
            "store_write_delta": 1,
            "success": true,
        });
        let entry: WriteAuditEntry = serde_json::from_value(legacy).unwrap();
        assert_eq!(entry.tool, "memory.update");
        assert_eq!(entry.actor_session, None);
        assert_eq!(entry.actor_user, None);
        assert_eq!(entry.actor_compartment, None);
    }

    #[test]
    fn record_since_ignores_writes_before_dispatch_start() {
        let store = make_store();
        let journal = WriteAuditJournal::with_flush_threshold(store.clone(), 0).unwrap();

        // Another session's writes land BEFORE this dispatch starts.
        put_one(&store, "other session's write 1");
        put_one(&store, "other session's write 2");

        let baseline = journal.dispatch_baseline();
        // An honest read-only dispatch runs and records.
        let entry = journal
            .record_since(
                baseline,
                "memory.search",
                ActorIdentity::default(),
                None,
                None,
                false,
                0,
                true,
            )
            .unwrap();

        assert_eq!(
            entry.store_write_delta, 0,
            "pre-dispatch writes must not be attributed"
        );
        assert!(!entry.undeclared_mutation());
        assert!(journal.misdeclarations().unwrap().is_empty());
    }

    #[test]
    fn record_since_catches_writes_during_dispatch_window() {
        let store = make_store();
        let journal = WriteAuditJournal::with_flush_threshold(store.clone(), 0).unwrap();

        let baseline = journal.dispatch_baseline();
        put_one(&store, "written while the dispatch ran");

        let entry = journal
            .record_since(
                baseline,
                "sneaky.read",
                ActorIdentity::default(),
                None,
                None,
                false,
                0,
                true,
            )
            .unwrap();

        assert!(entry.store_write_delta >= 1);
        assert!(entry.undeclared_mutation());
        assert_eq!(journal.misdeclarations().unwrap().len(), 1);
    }

    #[test]
    fn flush_does_not_tick_mutation_counter() {
        let store = make_store();
        let journal = WriteAuditJournal::with_flush_threshold(store.clone(), 0).unwrap();

        let baseline = store.mutation_count();
        // Threshold 0: record() flushes synchronously — the flush writes N+1
        // raw entries (N journal rows + the next-id key) and must not tick.
        journal
            .record(
                "memory.create",
                ActorIdentity::default(),
                None,
                None,
                true,
                0,
                true,
            )
            .unwrap();
        assert_eq!(journal.pending_count(), 0, "flush should have fired");

        assert_eq!(
            store.mutation_count(),
            baseline,
            "journal bookkeeping must not count as store mutations"
        );

        // A subsequent per-dispatch window sees the flush as zero writes.
        let baseline2 = journal.dispatch_baseline();
        let entry = journal
            .record_since(
                baseline2,
                "memory.search",
                ActorIdentity::default(),
                None,
                None,
                false,
                0,
                true,
            )
            .unwrap();
        assert_eq!(entry.store_write_delta, 0);
    }

    #[test]
    fn karma_flush_does_not_tick_mutation_counter() {
        let store = make_store();
        let ledger = crate::KarmaLedger::with_flush_threshold(store.clone(), 0).unwrap();

        let baseline = store.mutation_count();
        ledger.record("memory.create", true, 1, true).unwrap();
        assert_eq!(ledger.pending_count(), 0, "flush should have fired");

        assert_eq!(
            store.mutation_count(),
            baseline,
            "karma bookkeeping must not count as store mutations"
        );
    }
}
