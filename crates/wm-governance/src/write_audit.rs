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
    /// Whether the dispatch was confirm-gated and what the caller declared.
    /// `None` = not a confirm-gated (destructive) dispatch. `Some(true)` =
    /// a destructive dispatch that carried `confirm: true`. `Some(false)` =
    /// a destructive dispatch recorded without confirm (direct journal
    /// callers only — the pipeline gate refuses those before execution).
    /// The delete-confirm audit field (fix-queue P1.6, the Jul-13 law):
    /// every destructive journal entry answers "was this confirmed?".
    #[serde(default)]
    pub confirmed: Option<bool>,
    /// Whether the dispatch succeeded.
    pub success: bool,
    /// Compact digest of the dispatch's input arguments (Q35b flight-
    /// recorder groundwork, 2026-09-09). NOT the raw args: the digest
    /// captures route identity + arg keys + value SHA-256s so a replay
    /// harness can verify input identity without storing untrusted
    /// payloads verbatim in the journal. `None` = caller didn't supply
    /// (legacy entries; serde default keeps them deserializable).
    #[serde(default)]
    pub args_digest: Option<String>,
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
            None,
            None,
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
        args_digest: Option<String>,
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
            None,
            args_digest,
        )
    }

    /// [`Self::record_since`] for a confirm-gated (destructive) dispatch:
    /// the entry records what the caller declared under `confirmed` — the
    /// delete-confirm audit field. `Some(true)` means the dispatch carried
    /// `confirm: true`; `Some(false)` is only reachable through direct
    /// journal callers, since the pipeline gate refuses unconfirmed
    /// destructive dispatches before execution.
    #[allow(clippy::too_many_arguments)]
    pub fn record_since_confirmed(
        &self,
        dispatch_start: u64,
        tool: &str,
        actor: ActorIdentity,
        memory_id: Option<&str>,
        content_hash: Option<&str>,
        declared_writes: bool,
        reported_writes: u32,
        success: bool,
        confirmed: bool,
        args_digest: Option<String>,
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
            Some(confirmed),
            args_digest,
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
        confirmed: Option<bool>,
        args_digest: Option<String>,
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
            confirmed,
            args_digest,
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
                None,
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
                None,
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
                None,
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

/// Q35b flight-recorder groundwork (2026-09-09): compact args digest.
///
/// Captures route identity + arg keys + per-value SHA-256s so a replay
/// harness can verify input identity WITHOUT storing untrusted payloads
/// verbatim in the journal (prompt-injection surface stays out of the
/// audit trail). Shape: `route|k1=h(k1v),k2=h(k2v)` — sorted keys for
/// determinism. Values ≤64 chars inline hashable; larger values hash
/// their length prefix + bytes. No raw values, ever.
#[must_use]
pub fn args_digest(route: &str, args: &serde_json::Value) -> String {
    use std::fmt::Write as _;
    let mut out = String::with_capacity(64);
    let _ = write!(out, "{route}");
    if let Some(obj) = args.as_object() {
        let mut keys: Vec<&String> = obj.keys().collect();
        keys.sort();
        for k in keys {
            let v = &obj[k];
            let vstr = v.to_string();
            let _ = write!(out, "|{k}=");
            if vstr.len() <= 64 {
                let _ = write!(out, "{}", sha256_hex(vstr.as_bytes()));
            } else {
                let _ = write!(out, "len{}:{}", vstr.len(), sha256_hex(vstr.as_bytes()));
            }
        }
    }
    out
}

fn sha256_hex(data: &[u8]) -> String {
    // Minimal SHA-256 (FIPS 180-4). wm-governance has no sha2 dep today;
    // ~40 lines, deterministic, no external pulls.
    use std::fmt::Write as _;
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
        0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
        0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
        0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
        0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
        0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];
    let mut h: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
        0x5be0cd19,
    ];
    let mut msg = data.to_vec();
    let bitlen = (data.len() as u64) * 8;
    msg.push(0x80);
    while msg.len() % 64 != 56 {
        msg.push(0);
    }
    msg.extend_from_slice(&bitlen.to_be_bytes());
    for chunk in msg.chunks(64) {
        let mut w = [0u32; 64];
        for (i, word) in chunk.chunks(4).enumerate() {
            w[i] = u32::from_be_bytes([word[0], word[1], word[2], word[3]]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh) =
            (h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]);
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);
            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }
    let mut out = String::with_capacity(64);
    h.iter().for_each(|x| {
        let _ = write!(out, "{x:08x}");
    });
    out
}

#[cfg(test)]
mod q35b_tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn args_digest_is_deterministic_and_key_order_insensitive() {
        let a = args_digest("memory.search", &json!({"query": "x", "limit": 3}));
        let b = args_digest("memory.search", &json!({"limit": 3, "query": "x"}));
        assert_eq!(a, b, "key order must not change the digest");
        assert!(a.starts_with("memory.search|limit="));
        assert!(a.contains("|query="));
        assert!(!a.contains("\"x\""), "raw values never appear: {a}");
    }

    #[test]
    fn args_digest_changes_with_route_and_values() {
        let a = args_digest("memory.search", &json!({"query": "x"}));
        let b = args_digest("memory.create", &json!({"query": "x"}));
        let c = args_digest("memory.search", &json!({"query": "y"}));
        assert_ne!(a, b);
        assert_ne!(a, c);
    }

    #[test]
    fn args_digest_handles_large_values_with_length_prefix() {
        let big = "z".repeat(500);
        let d = args_digest("memory.create", &json!({"content": big}));
        assert!(d.contains("len502:"), "large values get length prefix: {d}");
        assert!(!d.contains(&big), "large raw value never stored");
    }

    #[test]
    fn sha256_known_vectors() {
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
        assert_eq!(
            sha256_hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn legacy_entries_without_digest_deserialize() {
        // Pre-Q35b stored JSON has no args_digest — serde default must hold.
        let legacy = r#"{"id":1,"timestamp":0,"tool":"memory.create","memory_id":null,
            "content_hash":null,"actor_session":null,"actor_user":null,
            "actor_compartment":null,"declared_writes":true,"reported_writes":1,
            "store_write_delta":1,"success":true,"confirmed":null}"#;
        let e: WriteAuditEntry =
            serde_json::from_str(legacy).expect("legacy entry must deserialize");
        assert_eq!(e.args_digest, None);
    }
}
