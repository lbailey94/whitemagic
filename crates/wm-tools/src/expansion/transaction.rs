//! Transaction tools — begin, commit, rollback for multi-tool sequences.
//!
//! `transaction.begin` snapshots all memory galaxies into Journals and
//! stores the backup ID in a shared transaction state. `transaction.rollback`
//! restores all galaxies from the snapshot. `transaction.commit` clears the
//! transaction state, keeping the changes.
//!
//! Exactness contract (release gate):
//! - Snapshots serialize complete `Memory` records — IDs, timestamps, hashes,
//!   coordinates, privacy flags, provenance, and versions are preserved.
//! - Snapshots are not truncated: every memory in every memory galaxy is
//!   captured, so rollback cannot silently drop data.
//! - Rollback validates and restores before clearing the active transaction,
//!   so a failed restore can be retried.
//! - Commit and successful rollback remove the journal snapshot, so
//!   transactions do not accumulate permanent recovery data.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::{Arc, Mutex};
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore, SearchEngine};

use super::common::galaxy_name;
use wm_core::Galaxy;

/// Shared transaction state — holds the active backup ID (if any).
pub type TransactionState = Arc<Mutex<Option<String>>>;

/// Locate the transaction snapshot memory in Journals by backup ID.
fn find_snapshot(store: &MemoryStore, snapshot_id: &str) -> wm_core::Result<Option<Memory>> {
    for mem in store.scan_all(Galaxy::Journals)? {
        if mem.metadata.tags.iter().any(|t| t == "transaction") && mem.content.contains(snapshot_id)
        {
            return Ok(Some(mem));
        }
    }
    Ok(None)
}

/// Parse a galaxy snapshot entry back into exact `Memory` records.
///
/// Prefers the current full-record format. Falls back to the legacy
/// field-level format so snapshots taken by earlier builds still restore.
fn parse_snapshot_memories(galaxy_entry: &Value, galaxy: Galaxy) -> Vec<Memory> {
    let Some(arr) = galaxy_entry.get("memories").and_then(Value::as_array) else {
        return Vec::new();
    };
    if arr.is_empty() {
        return Vec::new();
    }
    // Full-record format: every element deserializes as a complete Memory.
    if let Ok(memories) = serde_json::from_value::<Vec<Memory>>(Value::Array(arr.clone())) {
        return memories;
    }
    // Legacy field-level format (pre-exact-rollback snapshots).
    arr.iter()
        .map(|mem_val| {
            let content = mem_val.get("content").and_then(Value::as_str).unwrap_or("");
            let mut mem = Memory::new(galaxy, content.to_string());
            if let Some(tags) = mem_val.get("tags").and_then(Value::as_array) {
                mem.metadata.tags = tags
                    .iter()
                    .filter_map(|t| t.as_str().map(String::from))
                    .collect();
            }
            if let Some(imp) = mem_val.get("importance").and_then(Value::as_f64) {
                mem.metadata.importance = imp as f32;
            }
            mem
        })
        .collect()
}

/// `transaction.begin` — snapshot all galaxies, store backup ID for rollback.
pub struct TransactionBeginTool {
    store: Arc<MemoryStore>,
    state: TransactionState,
    stats: ToolStats,
    effects: EffectRow,
}

impl TransactionBeginTool {
    pub fn new(store: Arc<MemoryStore>, state: TransactionState) -> Self {
        Self {
            store,
            state,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("journals".into())],
                reads: vec![],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for TransactionBeginTool {
    fn name(&self) -> &str {
        "transaction.begin"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Begin a transaction — snapshots all memory galaxies (exact records) for potential rollback"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut guard = self.state.lock().map_err(|e| {
            wm_core::CoreError::Governance(format!("transaction state lock error: {e}"))
        })?;
        if guard.is_some() {
            return Err(wm_core::CoreError::Governance(
                "transaction already in progress — commit or rollback first".into(),
            ));
        }

        let backup_id = uuid::Uuid::new_v4();
        let mut galaxy_data = serde_json::Map::new();
        let mut total_backed_up = 0usize;

        // Full scan with exact record serialization: an exact rollback cannot
        // be truncated at an arbitrary limit, and field-picked snapshots
        // silently dropped IDs, timestamps, hashes, privacy flags, and
        // provenance on restore.
        for galaxy in Galaxy::memory_galaxies() {
            let memories = self.store.scan_all(galaxy)?;
            let count = memories.len();
            total_backed_up += count;
            galaxy_data.insert(
                galaxy_name(galaxy).to_string(),
                json!({
                    "count": count,
                    "memories": memories,
                }),
            );
        }

        let backup_content = json!({
            "type": "transaction_snapshot",
            "backup_id": backup_id,
            "timestamp": chrono::Utc::now().to_rfc3339(),
            "total_memories": total_backed_up,
            "galaxies": galaxy_data,
        })
        .to_string();

        let mut backup_mem = Memory::new(Galaxy::Journals, backup_content);
        backup_mem.metadata.tags = vec!["transaction".to_string()];
        backup_mem.metadata.importance = 1.0;
        self.store.put(Galaxy::Journals, &backup_mem)?;

        let id_str = backup_id.to_string();
        *guard = Some(id_str.clone());

        Ok(json!({
            "status": "success",
            "transaction_id": id_str,
            "total_memories_snapshotted": total_backed_up,
            "galaxies_snapshotted": Galaxy::memory_galaxies().len(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `transaction.commit` — clear transaction state, keeping all changes.
pub struct TransactionCommitTool {
    store: Arc<MemoryStore>,
    state: TransactionState,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TransactionCommitTool {
    pub fn new(
        store: Arc<MemoryStore>,
        state: TransactionState,
        search: Option<Arc<SearchEngine>>,
    ) -> Self {
        Self {
            store,
            state,
            search,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for TransactionCommitTool {
    fn name(&self) -> &str {
        "transaction.commit"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Commit a transaction — keeps all changes, removes the rollback snapshot"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut guard = self.state.lock().map_err(|e| {
            wm_core::CoreError::Governance(format!("transaction state lock error: {e}"))
        })?;
        let snapshot_id = match guard.as_ref() {
            Some(id) => id.clone(),
            None => {
                return Err(wm_core::CoreError::Governance(
                    "no active transaction to commit".into(),
                ));
            }
        };

        // Remove the rollback snapshot so committed transactions leave no
        // permanent recovery data behind. A missing snapshot is fine
        // (idempotent commit); a failed delete keeps the transaction active
        // so the caller can retry.
        if let Some(mem) = find_snapshot(&self.store, &snapshot_id)? {
            let mem_id = mem.metadata.id.to_string();
            self.store.delete(Galaxy::Journals, mem.metadata.id)?;
            super::common::deindex(self.search.as_deref(), &mem_id);
        }

        *guard = None;
        Ok(json!({
            "status": "success",
            "transaction_id": snapshot_id,
            "message": "transaction committed — changes kept, snapshot removed",
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `transaction.rollback` — restore all galaxies from the transaction snapshot.
pub struct TransactionRollbackTool {
    store: Arc<MemoryStore>,
    state: TransactionState,
    search: Option<Arc<SearchEngine>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl TransactionRollbackTool {
    pub fn new(
        store: Arc<MemoryStore>,
        state: TransactionState,
        search: Option<Arc<SearchEngine>>,
    ) -> Self {
        Self {
            store,
            state,
            search,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("universal".into())],
                reads: vec![Resource::Galaxy("journals".into())],
                destructive: true,
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for TransactionRollbackTool {
    fn name(&self) -> &str {
        "transaction.rollback"
    }
    fn gana(&self) -> Gana {
        Gana::Void
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Rollback a transaction — restores exact pre-transaction records"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut guard = self.state.lock().map_err(|e| {
            wm_core::CoreError::Governance(format!("transaction state lock error: {e}"))
        })?;
        let snapshot_id = match guard.as_ref() {
            Some(id) => id.clone(),
            None => {
                return Err(wm_core::CoreError::Governance(
                    "no active transaction to rollback".into(),
                ));
            }
        };

        // Locate and parse the snapshot BEFORE touching any galaxy. On any
        // failure the transaction state is left intact so rollback can be
        // retried — a partial restore with no retry state was the old
        // failure mode.
        let snapshot = find_snapshot(&self.store, &snapshot_id)?.ok_or_else(|| {
            wm_core::CoreError::NotFound(format!(
                "transaction snapshot {snapshot_id} not found in journals"
            ))
        })?;

        let backup: Value = serde_json::from_str(&snapshot.content).map_err(|e| {
            wm_core::CoreError::Memory(format!("failed to parse transaction snapshot: {e}"))
        })?;

        let galaxies = backup
            .get("galaxies")
            .and_then(|v| v.as_object())
            .ok_or_else(|| {
                wm_core::CoreError::Memory("snapshot has no 'galaxies' object".into())
            })?;

        let mut total_restored = 0usize;
        let mut total_cleared = 0usize;

        for galaxy in Galaxy::memory_galaxies() {
            let gname = galaxy_name(galaxy);
            let Some(galaxy_entry) = galaxies.get(gname) else {
                continue;
            };

            // Exact records from the snapshot (with legacy fallback).
            let memories = parse_snapshot_memories(galaxy_entry, galaxy);

            // Clear existing memories in this galaxy (single transaction) and
            // de-index them so full-text search doesn't return stale hits.
            let existing = self.store.scan_all(galaxy)?;
            for mem in &existing {
                super::common::deindex(self.search.as_deref(), &mem.metadata.id.to_string());
            }
            total_cleared += self.store.clear_galaxy(galaxy)?;

            // Restore from the snapshot (single transaction via batch_put,
            // which preserves each memory's original UUID and index entries).
            total_restored += self.store.batch_put(galaxy, &memories)?;
            for mem in &memories {
                super::common::index_memory(self.search.as_deref(), mem);
            }
        }

        // Success — the snapshot restored, so the transaction is complete.
        *guard = None;

        Ok(json!({
            "status": "success",
            "transaction_id": snapshot_id,
            "galaxies_restored": Galaxy::memory_galaxies().len(),
            "memories_cleared": total_cleared,
            "memories_restored": total_restored,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::BrainWave;

    fn open_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
        (tmp, store)
    }

    #[tokio::test]
    async fn transaction_begin_commit_workflow() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));

        // Create a memory
        let mem = Memory::new(Galaxy::Codex, "test content".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        // Begin transaction
        let begin = TransactionBeginTool::new(Arc::clone(&store), Arc::clone(&state));
        let result = begin
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await;
        assert!(result.is_ok());
        assert!(state.lock().unwrap().is_some());

        // Commit
        let commit = TransactionCommitTool::new(Arc::clone(&store), Arc::clone(&state), None);
        let result = commit
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await;
        assert!(result.is_ok());
        assert!(state.lock().unwrap().is_none());
    }

    #[tokio::test]
    async fn transaction_begin_rollback_restores_data() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));

        // Create a memory
        let mem = Memory::new(Galaxy::Codex, "original content".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        // Begin transaction
        let begin = TransactionBeginTool::new(store.clone(), state.clone());
        let result = begin
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await;
        assert!(result.is_ok());

        // Modify: delete the memory
        store.delete(Galaxy::Codex, mem.metadata.id).unwrap();
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 0);

        // Rollback
        let rollback = TransactionRollbackTool::new(store.clone(), state, None);
        let result = rollback
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await;
        assert!(result.is_ok());

        // Verify memory was restored
        let memories = store.scan(Galaxy::Codex, 10_000).unwrap();
        assert_eq!(memories.len(), 1);
        assert_eq!(memories[0].content, "original content");
    }

    #[tokio::test]
    async fn transaction_begin_twice_errors() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(Some("existing-id".into())));

        let begin = TransactionBeginTool::new(store, state);
        let result = begin
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn transaction_commit_without_begin_errors() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));
        let commit = TransactionCommitTool::new(store, state, None);
        let result = commit
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn transaction_rollback_without_begin_errors() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));
        let rollback = TransactionRollbackTool::new(store, state, None);
        let result = rollback
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn transaction_rollback_is_destructive() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));
        let rollback = TransactionRollbackTool::new(store, state, None);
        assert!(rollback.effects().destructive);
    }

    #[tokio::test]
    async fn rollback_restores_exact_records() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));

        let mut mem = Memory::new(Galaxy::Codex, "exact record content".into());
        mem.metadata.tags = vec!["alpha".into(), "beta".into()];
        mem.metadata.importance = 0.9;
        mem.metadata.is_private = true;
        mem.metadata.model_exclude = true;
        store.put(Galaxy::Codex, &mem).unwrap();
        let original_json = serde_json::to_value(&mem).unwrap();

        let begin = TransactionBeginTool::new(store.clone(), state.clone());
        begin
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await
            .unwrap();

        // Mutate the memory, then roll back.
        let mut mutated = store.get(Galaxy::Codex, mem.metadata.id).unwrap().unwrap();
        mutated.metadata.tags = vec!["changed".into()];
        mutated.metadata.importance = 0.1;
        mutated.metadata.is_private = false;
        store.put(Galaxy::Codex, &mutated).unwrap();

        let rollback = TransactionRollbackTool::new(store.clone(), state.clone(), None);
        rollback
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await
            .unwrap();

        // Exact record: same UUID, timestamps, hashes, flags, coordinates.
        let restored = store.get(Galaxy::Codex, mem.metadata.id).unwrap().unwrap();
        assert_eq!(serde_json::to_value(&restored).unwrap(), original_json);
        assert!(state.lock().unwrap().is_none());
    }

    #[tokio::test]
    async fn rollback_is_not_truncated_at_ten_thousand() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));

        // 10,001 memories — the old snapshot path capped scans at 10,000 and
        // silently dropped the rest, so rollback deleted real data.
        let memories: Vec<Memory> = (0..10_001)
            .map(|i| Memory::new(Galaxy::Codex, format!("bulk memory {i}")))
            .collect();
        store.batch_put(Galaxy::Codex, &memories).unwrap();

        let begin = TransactionBeginTool::new(store.clone(), state.clone());
        let result = begin
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await
            .unwrap();
        assert_eq!(
            result["total_memories_snapshotted"], 10_001,
            "snapshot must not truncate"
        );

        // Wipe the galaxy, then roll back.
        store.clear_galaxy(Galaxy::Codex).unwrap();
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 0);

        let rollback = TransactionRollbackTool::new(store.clone(), state.clone(), None);
        let result = rollback
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await
            .unwrap();
        assert_eq!(result["memories_restored"], 10_001);
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 10_001);
    }

    #[tokio::test]
    async fn commit_removes_snapshot() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));

        let mem = Memory::new(Galaxy::Codex, "commit cleanup".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        let begin = TransactionBeginTool::new(store.clone(), state.clone());
        begin
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await
            .unwrap();
        let snapshot_id = state.lock().unwrap().clone().unwrap();
        assert!(find_snapshot(&store, &snapshot_id).unwrap().is_some());

        let commit = TransactionCommitTool::new(store.clone(), state.clone(), None);
        commit
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await
            .unwrap();

        assert!(state.lock().unwrap().is_none());
        assert!(
            find_snapshot(&store, &snapshot_id).unwrap().is_none(),
            "commit must remove the journal snapshot"
        );
    }

    #[tokio::test]
    async fn failed_rollback_keeps_transaction_state() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));

        let mem = Memory::new(Galaxy::Codex, "retryable rollback".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        let begin = TransactionBeginTool::new(store.clone(), state.clone());
        begin
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await
            .unwrap();
        let snapshot_id = state.lock().unwrap().clone().unwrap();

        // Corrupt the snapshot: replace it with a same-tagged journal
        // memory whose content does not parse as a snapshot.
        let snapshot_mem = find_snapshot(&store, &snapshot_id).unwrap().unwrap();
        store
            .delete(Galaxy::Journals, snapshot_mem.metadata.id)
            .unwrap();
        let mut corrupt = Memory::new(Galaxy::Journals, format!("corrupted {snapshot_id}"));
        corrupt.metadata.tags = vec!["transaction".into()];
        store.put(Galaxy::Journals, &corrupt).unwrap();

        let rollback = TransactionRollbackTool::new(store.clone(), state.clone(), None);
        let result = rollback
            .call(&mut Context::new(BrainWave::Gamma), json!({}))
            .await;
        assert!(result.is_err(), "corrupted snapshot must fail rollback");

        // The transaction stays active so rollback can be retried.
        assert_eq!(
            state.lock().unwrap().as_deref(),
            Some(snapshot_id.as_str()),
            "failed rollback must keep the transaction state"
        );
    }
}
