//! Transaction tools — begin, commit, rollback for multi-tool sequences.
//!
//! `transaction.begin` snapshots all memory galaxies into Journals and
//! stores the backup ID in a shared transaction state. `transaction.rollback`
//! restores all galaxies from the snapshot. `transaction.commit` clears the
//! transaction state, keeping the changes.

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use std::sync::{Arc, Mutex};
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_memory::{Memory, MemoryStore};

use super::common::galaxy_name;
use wm_core::Galaxy;

/// Shared transaction state — holds the active backup ID (if any).
pub type TransactionState = Arc<Mutex<Option<String>>>;

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
        "Begin a transaction — snapshots all galaxies for potential rollback"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
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

        for galaxy in Galaxy::memory_galaxies() {
            let memories = self.store.scan(galaxy, 10_000)?;
            let count = memories.len();
            total_backed_up += count;
            galaxy_data.insert(
                galaxy_name(galaxy).to_string(),
                json!({
                    "count": count,
                    "memories": memories.iter().map(|m| {
                        json!({
                            "id": m.metadata.id,
                            "content": m.content,
                            "tags": m.metadata.tags,
                            "importance": m.metadata.importance,
                            "created_at": m.metadata.created_at.to_rfc3339(),
                            "content_hash": m.metadata.content_hash,
                        })
                    }).collect::<Vec<_>>(),
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
    state: TransactionState,
    stats: ToolStats,
    effects: EffectRow,
}

impl TransactionCommitTool {
    pub fn new(state: TransactionState) -> Self {
        Self {
            state,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

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
        "Commit a transaction — keeps all changes, clears rollback snapshot"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut guard = self.state.lock().map_err(|e| {
            wm_core::CoreError::Governance(format!("transaction state lock error: {e}"))
        })?;
        match guard.take() {
            Some(id) => Ok(json!({
                "status": "success",
                "transaction_id": id,
                "message": "transaction committed — changes kept",
            })),
            None => Err(wm_core::CoreError::Governance(
                "no active transaction to commit".into(),
            )),
        }
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `transaction.rollback` — restore all galaxies from the transaction snapshot.
pub struct TransactionRollbackTool {
    store: Arc<MemoryStore>,
    state: TransactionState,
    stats: ToolStats,
    effects: EffectRow,
}

impl TransactionRollbackTool {
    pub fn new(store: Arc<MemoryStore>, state: TransactionState) -> Self {
        Self {
            store,
            state,
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
        "Rollback a transaction — restores all galaxies from snapshot"
    }
    fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let mut guard = self.state.lock().map_err(|e| {
            wm_core::CoreError::Governance(format!("transaction state lock error: {e}"))
        })?;
        let snapshot_id = match guard.take() {
            Some(id) => id,
            None => {
                return Err(wm_core::CoreError::Governance(
                    "no active transaction to rollback".into(),
                ));
            }
        };

        // Find the snapshot in Journals by backup_id
        let journals = self.store.scan(Galaxy::Journals, 10_000)?;
        let snapshot = journals
            .iter()
            .find(|m| {
                m.metadata.tags.contains(&"transaction".to_string())
                    && m.content.contains(&snapshot_id)
            })
            .ok_or_else(|| {
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
            let galaxy_entry = match galaxies.get(gname) {
                Some(e) => e,
                None => continue,
            };

            // Clear existing memories in this galaxy (single transaction)
            total_cleared += self.store.clear_galaxy(galaxy)?;

            // Restore from snapshot (single transaction via batch_put)
            let empty = Vec::new();
            let memories = galaxy_entry
                .get("memories")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let mut to_put: Vec<Memory> = Vec::with_capacity(memories.len());
            for mem_val in memories {
                let content = mem_val
                    .get("content")
                    .and_then(serde_json::Value::as_str)
                    .unwrap_or("");
                let mut mem = Memory::new(galaxy, content.to_string());
                if let Some(tags) = mem_val.get("tags").and_then(|v| v.as_array()) {
                    mem.metadata.tags = tags
                        .iter()
                        .filter_map(|t| t.as_str().map(String::from))
                        .collect();
                }
                if let Some(imp) = mem_val
                    .get("importance")
                    .and_then(serde_json::Value::as_f64)
                {
                    mem.metadata.importance = imp as f32;
                }
                to_put.push(mem);
            }
            total_restored += self.store.batch_put(galaxy, &to_put)?;
        }

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

    #[test]
    fn transaction_begin_commit_workflow() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));

        // Create a memory
        let mem = Memory::new(Galaxy::Codex, "test content".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        // Begin transaction
        let begin = TransactionBeginTool::new(Arc::clone(&store), Arc::clone(&state));
        let result = begin.call(&mut Context::new(BrainWave::Gamma), json!({}));
        assert!(result.is_ok());
        assert!(state.lock().unwrap().is_some());

        // Commit
        let commit = TransactionCommitTool::new(Arc::clone(&state));
        let result = commit.call(&mut Context::new(BrainWave::Gamma), json!({}));
        assert!(result.is_ok());
        assert!(state.lock().unwrap().is_none());
    }

    #[test]
    fn transaction_begin_rollback_restores_data() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));

        // Create a memory
        let mem = Memory::new(Galaxy::Codex, "original content".into());
        store.put(Galaxy::Codex, &mem).unwrap();

        // Begin transaction
        let begin = TransactionBeginTool::new(store.clone(), state.clone());
        let result = begin.call(&mut Context::new(BrainWave::Gamma), json!({}));
        assert!(result.is_ok());

        // Modify: delete the memory
        store.delete(Galaxy::Codex, mem.metadata.id).unwrap();
        assert_eq!(store.count(Galaxy::Codex).unwrap(), 0);

        // Rollback
        let rollback = TransactionRollbackTool::new(store.clone(), state);
        let result = rollback.call(&mut Context::new(BrainWave::Gamma), json!({}));
        assert!(result.is_ok());

        // Verify memory was restored
        let memories = store.scan(Galaxy::Codex, 10_000).unwrap();
        assert_eq!(memories.len(), 1);
        assert_eq!(memories[0].content, "original content");
    }

    #[test]
    fn transaction_begin_twice_errors() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(Some("existing-id".into())));

        let begin = TransactionBeginTool::new(store, state);
        let result = begin.call(&mut Context::new(BrainWave::Gamma), json!({}));
        assert!(result.is_err());
    }

    #[test]
    fn transaction_commit_without_begin_errors() {
        let state: TransactionState = Arc::new(Mutex::new(None));
        let commit = TransactionCommitTool::new(state);
        let result = commit.call(&mut Context::new(BrainWave::Gamma), json!({}));
        assert!(result.is_err());
    }

    #[test]
    fn transaction_rollback_without_begin_errors() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));
        let rollback = TransactionRollbackTool::new(store, state);
        let result = rollback.call(&mut Context::new(BrainWave::Gamma), json!({}));
        assert!(result.is_err());
    }

    #[test]
    fn transaction_rollback_is_destructive() {
        let (_tmp, store) = open_store();
        let state: TransactionState = Arc::new(Mutex::new(None));
        let rollback = TransactionRollbackTool::new(store, state);
        assert!(rollback.effects().destructive);
    }
}
