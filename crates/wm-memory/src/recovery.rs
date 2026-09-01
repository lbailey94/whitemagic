//! LMDB corruption recovery — integrity checks, repair, and map-size growth.
//!
//! Provides defense-in-depth against LMDB data store corruption:
//! - **Integrity check**: Read-only scan of all galaxy DBs, verifying
//!   deserialization of every entry.
//! - **Auto-repair**: Quarantine corrupted entries, rebuild secondary indexes
//!   from valid memories.
//! - **Map-size growth**: Detect `MDB_MAP_FULL` and reopen with a larger
//!   virtual address space.
//!
//! Recovery strategies control how aggressively the store attempts to recover:
//! - `None`: No recovery — fail on corruption (current behavior).
//! - `WarnOnly`: Log warnings but don't modify data.
//! - `AutoRepair`: Quarantine corrupted entries and rebuild indexes.
//! - `AutoRepairAndGrow`: AutoRepair + grow map size on `MDB_MAP_FULL`.

use std::fmt::Write;
use std::path::{Path, PathBuf};

use lmdb::{Cursor, Environment, Transaction};
use serde::{Deserialize, Serialize};
use wm_core::{CoreError, Galaxy, Result};

use crate::memory::Memory;
use crate::store::MemoryStore;

// ── Recovery Strategy ─────────────────────────────────────────────────

/// Strategy for handling LMDB corruption on open.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum RecoveryStrategy {
    /// No recovery — fail on corruption.
    #[default]
    None,
    /// Log warnings but don't modify data.
    WarnOnly,
    /// Quarantine corrupted entries and rebuild indexes.
    AutoRepair,
    /// AutoRepair + grow map size on MDB_MAP_FULL.
    AutoRepairAndGrow,
}

#[allow(clippy::derivable_impls, clippy::should_implement_trait)]
impl RecoveryStrategy {
    /// Whether this strategy performs repairs.
    #[must_use]
    pub const fn repairs(self) -> bool {
        matches!(self, Self::AutoRepair | Self::AutoRepairAndGrow)
    }

    /// Whether this strategy can grow map size.
    #[must_use]
    pub const fn grows_map(self) -> bool {
        matches!(self, Self::AutoRepairAndGrow)
    }
}

// ── Integrity Report ──────────────────────────────────────────────────

/// Per-galaxy integrity check result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GalaxyIntegrity {
    /// Galaxy name.
    pub galaxy: String,
    /// Total entries scanned.
    pub total: usize,
    /// Entries that deserialized successfully.
    pub valid: usize,
    /// Entries that failed deserialization.
    pub corrupted: usize,
    /// Corrupted keys (hex-encoded).
    pub corrupted_keys: Vec<String>,
}

impl GalaxyIntegrity {
    /// Whether this galaxy is clean.
    #[must_use]
    pub const fn is_clean(&self) -> bool {
        self.corrupted == 0
    }
}

/// Full integrity report across all galaxies.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntegrityReport {
    /// Per-galaxy results.
    pub galaxies: Vec<GalaxyIntegrity>,
    /// Total entries across all galaxies.
    pub total_entries: usize,
    /// Total valid entries.
    pub total_valid: usize,
    /// Total corrupted entries.
    pub total_corrupted: usize,
    /// Whether the store is clean.
    pub is_clean: bool,
}

impl IntegrityReport {
    /// Get a human-readable summary.
    #[must_use]
    pub fn summary(&self) -> String {
        if self.is_clean {
            format!(
                "Store is clean: {} entries across {} galaxies, 0 corrupted",
                self.total_entries,
                self.galaxies.len()
            )
        } else {
            format!(
                "Store has corruption: {} valid, {} corrupted out of {} total entries",
                self.total_valid, self.total_corrupted, self.total_entries
            )
        }
    }
}

// ── Repair Report ─────────────────────────────────────────────────────

/// Result of a repair operation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RepairReport {
    /// Integrity report after repair.
    pub integrity: IntegrityReport,
    /// Number of entries quarantined.
    pub quarantined: usize,
    /// Number of index entries rebuilt.
    pub indexes_rebuilt: usize,
    /// Path to the quarantine file (if any).
    pub quarantine_path: Option<String>,
    /// Path to the backup of the original data file (if any).
    pub backup_path: Option<String>,
    /// New map size (if grown).
    pub new_map_size: Option<usize>,
}

// ── Quarantine Entry ──────────────────────────────────────────────────

/// A quarantined entry that failed deserialization.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuarantineEntry {
    /// Galaxy name.
    pub galaxy: String,
    /// Key (hex-encoded).
    pub key_hex: String,
    /// Raw value (base64-encoded).
    pub value_base64: String,
    /// Error message from deserialization attempt.
    pub error: String,
}

// ── Recovery Functions ────────────────────────────────────────────────

/// Maximum map size for auto-growth (4 GB).
// Windows NTFS materializes the LMDB map file at full size on open, so the
// auto-grow ceiling is smaller there (see MemoryStore::open_default).
#[cfg(windows)]
const MAX_MAP_SIZE: usize = 256 * 1024 * 1024;
#[cfg(not(windows))]
const MAX_MAP_SIZE: usize = 4 * 1024 * 1024 * 1024;

/// Initial map size if none specified.
#[allow(dead_code)]
const DEFAULT_MAP_SIZE: usize = 1024 * 1024 * 1024; // 1 GB

/// Check the integrity of all memory galaxies in the store.
///
/// This is a read-only operation — it does not modify any data.
/// Scans all 10 memory galaxies (excluding Karma, Dharma, Associations,
/// and Embeddings which store non-Memory data).
pub fn check_integrity(store: &MemoryStore) -> Result<IntegrityReport> {
    let mut galaxies = Vec::new();
    let mut total_entries = 0;
    let mut total_valid = 0;
    let mut total_corrupted = 0;

    for galaxy in Galaxy::memory_galaxies() {
        let gi = check_galaxy_integrity(store, galaxy)?;
        total_entries += gi.total;
        total_valid += gi.valid;
        total_corrupted += gi.corrupted;
        galaxies.push(gi);
    }

    let is_clean = total_corrupted == 0;
    Ok(IntegrityReport {
        galaxies,
        total_entries,
        total_valid,
        total_corrupted,
        is_clean,
    })
}

/// Check integrity of a single galaxy.
fn check_galaxy_integrity(store: &MemoryStore, galaxy: Galaxy) -> Result<GalaxyIntegrity> {
    let db = store.galaxy_db(galaxy)?;
    let env = store.env();

    let tx = env
        .begin_ro_txn()
        .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;

    let mut cursor = tx
        .open_ro_cursor(db)
        .map_err(|e| CoreError::Memory(format!("LMDB cursor failed: {e}")))?;

    let mut total = 0;
    let mut valid = 0;
    let mut corrupted_keys = Vec::new();

    for (key, val) in cursor.iter() {
        total += 1;
        match rmp_serde::from_slice::<Memory>(val) {
            Ok(_) => valid += 1,
            Err(_) => {
                corrupted_keys.push(hex_encode(key));
            }
        }
    }

    drop(cursor);
    tx.commit()
        .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;

    let corrupted = total - valid;
    Ok(GalaxyIntegrity {
        galaxy: galaxy.db_name().to_string(),
        total,
        valid,
        corrupted,
        corrupted_keys,
    })
}

/// Repair a corrupted LMDB store.
///
/// This will:
/// 1. Back up the original data file.
/// 2. Scan all memory galaxies for corrupted entries.
/// 3. Quarantine corrupted entries to a sidecar JSONL file.
/// 4. Delete corrupted entries from the store.
/// 5. Rebuild secondary indexes from valid memories.
///
/// Returns a `RepairReport` with details of what was done.
pub fn repair(store: &mut MemoryStore, store_path: &Path) -> Result<RepairReport> {
    let quarantine_path = store_path.join("quarantine.jsonl");
    let backup_path = backup_data_file(store_path)?;

    // Collect corrupted entries and quarantine them
    let mut quarantined_entries: Vec<QuarantineEntry> = Vec::new();
    let mut indexes_rebuilt = 0;

    for galaxy in Galaxy::memory_galaxies() {
        let corrupted = collect_and_quarantine(store, galaxy, &mut quarantined_entries)?;

        if corrupted.is_empty() {
            continue;
        }

        // Delete corrupted entries from the store
        for key_hex in &corrupted {
            let key = hex_decode(key_hex);
            let _ = store.delete_raw(galaxy, &key);
        }

        // Rebuild indexes for this galaxy
        indexes_rebuilt += rebuild_galaxy_indexes(store, galaxy)?;
    }

    // Write quarantine file
    let quarantine_str = if quarantined_entries.is_empty() {
        None
    } else {
        write_quarantine_file(&quarantine_path, &quarantined_entries)?;
        Some(quarantine_path.to_string_lossy().to_string())
    };

    // Verify integrity after repair
    let integrity = check_integrity(store)?;

    let quarantined = quarantined_entries.len();
    Ok(RepairReport {
        integrity,
        quarantined,
        indexes_rebuilt,
        quarantine_path: quarantine_str,
        backup_path: Some(backup_path.to_string_lossy().to_string()),
        new_map_size: None,
    })
}

/// Collect corrupted entries from a galaxy and add them to the quarantine list.
/// Returns the hex-encoded keys of corrupted entries.
fn collect_and_quarantine(
    store: &MemoryStore,
    galaxy: Galaxy,
    quarantine: &mut Vec<QuarantineEntry>,
) -> Result<Vec<String>> {
    let db = store.galaxy_db(galaxy)?;
    let env = store.env();

    let tx = env
        .begin_ro_txn()
        .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;

    let mut cursor = tx
        .open_ro_cursor(db)
        .map_err(|e| CoreError::Memory(format!("LMDB cursor failed: {e}")))?;

    let mut corrupted_keys = Vec::new();

    for (key, val) in cursor.iter() {
        match rmp_serde::from_slice::<Memory>(val) {
            Ok(_) => {}
            Err(e) => {
                corrupted_keys.push(hex_encode(key));
                quarantine.push(QuarantineEntry {
                    galaxy: galaxy.db_name().to_string(),
                    key_hex: hex_encode(key),
                    value_base64: base64_encode(val),
                    error: e.to_string(),
                });
            }
        }
    }

    drop(cursor);
    tx.commit()
        .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;

    Ok(corrupted_keys)
}

/// Rebuild secondary indexes for a galaxy by re-adding all valid memories.
fn rebuild_galaxy_indexes(store: &MemoryStore, galaxy: Galaxy) -> Result<usize> {
    let db = store.galaxy_db(galaxy)?;
    let env = store.env();
    let index_dbs = store.index_dbs();

    // First pass: collect all valid memories
    let memories: Vec<Memory> = {
        let tx = env
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed: {e}")))?;
        let mut cursor = tx
            .open_ro_cursor(db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor failed: {e}")))?;
        let mut mems = Vec::new();
        for (_key, val) in cursor.iter() {
            if let Ok(mem) = rmp_serde::from_slice::<Memory>(val) {
                mems.push(mem);
            }
        }
        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;
        mems
    };

    // Second pass: remove old index entries and re-add
    let mut count = 0;
    let mut tx = env
        .begin_rw_txn()
        .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed: {e}")))?;

    // Remove all existing index entries for this galaxy
    // (We do this by removing each memory's indexes, then re-adding)
    for mem in &memories {
        let _ = index_dbs.remove(&mut tx, galaxy, mem);
    }

    for mem in &memories {
        index_dbs.add(&mut tx, galaxy, mem)?;
        count += 1;
    }

    tx.commit()
        .map_err(|e| CoreError::Memory(format!("LMDB commit failed: {e}")))?;

    Ok(count)
}

/// Back up the LMDB data file before repair.
fn backup_data_file(store_path: &Path) -> Result<PathBuf> {
    let data_file = store_path.join("data.mdb");
    if !data_file.exists() {
        return Err(CoreError::Memory(format!(
            "LMDB data file not found: {}",
            data_file.display()
        )));
    }

    let timestamp = chrono::Utc::now().format("%Y%m%d_%H%M%S");
    let backup = store_path.join(format!("data.mdb.corrupt-{timestamp}"));
    std::fs::copy(&data_file, &backup)
        .map_err(|e| CoreError::Memory(format!("backup failed: {e}")))?;
    Ok(backup)
}

/// Write quarantine entries to a JSONL file.
fn write_quarantine_file(path: &Path, entries: &[QuarantineEntry]) -> Result<()> {
    use std::io::Write;
    let mut file = std::fs::File::create(path)
        .map_err(|e| CoreError::Memory(format!("quarantine file create: {e}")))?;
    for entry in entries {
        let line = serde_json::to_string(entry)
            .map_err(|e| CoreError::Memory(format!("quarantine serialize: {e}")))?;
        writeln!(file, "{line}")
            .map_err(|e| CoreError::Memory(format!("quarantine write: {e}")))?;
    }
    Ok(())
}

/// Open a MemoryStore with recovery support.
///
/// If `strategy` is `None`, behaves like `MemoryStore::open()`.
/// Otherwise, attempts to open the store, and if corruption is detected,
/// performs the appropriate recovery actions.
pub fn open_with_recovery(
    path: impl AsRef<Path>,
    map_size: usize,
    strategy: RecoveryStrategy,
) -> Result<MemoryStore> {
    let path = path.as_ref().to_path_buf();

    // First, try normal open
    match MemoryStore::open(&path, map_size) {
        Ok(store) => {
            // Check integrity
            let report = check_integrity(&store)?;
            if report.is_clean {
                return Ok(store);
            }

            // Corruption detected
            match strategy {
                RecoveryStrategy::None => Err(CoreError::Memory(format!(
                    "LMDB corruption detected: {} corrupted entries. Use recovery strategy to repair.",
                    report.total_corrupted
                ))),
                RecoveryStrategy::WarnOnly => {
                    tracing::warn!(
                        "LMDB corruption detected: {} corrupted entries. WarnOnly strategy — no repair performed.",
                        report.total_corrupted
                    );
                    Ok(store)
                }
                RecoveryStrategy::AutoRepair | RecoveryStrategy::AutoRepairAndGrow => {
                    tracing::warn!(
                        "LMDB corruption detected: {} corrupted entries. Attempting auto-repair.",
                        report.total_corrupted
                    );
                    let mut store = store;
                    let repair_report = repair(&mut store, &path)?;
                    tracing::info!(
                        "LMDB repair complete: {} quarantined, {} indexes rebuilt. Backup: {:?}",
                        repair_report.quarantined,
                        repair_report.indexes_rebuilt,
                        repair_report.backup_path
                    );
                    Ok(store)
                }
            }
        }
        Err(e) => {
            // Open failed — could be MAP_FULL or corruption
            if strategy.grows_map() && map_size < MAX_MAP_SIZE {
                let new_map_size = (map_size * 2).min(MAX_MAP_SIZE);
                tracing::warn!(
                    "LMDB open failed ({e}). Retrying with larger map size: {} -> {}",
                    map_size,
                    new_map_size
                );
                return open_with_recovery(&path, new_map_size, strategy);
            }
            Err(e)
        }
    }
}

/// Attempt to grow the map size of an existing store.
///
/// This closes the current environment and reopens with a larger map size.
/// Returns the new map size on success.
///
/// Note: This function is not needed in normal operation since
/// `open_with_recovery` handles map size growth on open. It is provided
/// for cases where the store needs to grow while running.
pub fn grow_map_size(path: impl AsRef<Path>, current_size: usize) -> Result<usize> {
    let path = path.as_ref();
    let new_size = (current_size * 2).min(MAX_MAP_SIZE);
    if new_size == current_size {
        return Err(CoreError::Memory(format!(
            "Map size already at maximum ({current_size} bytes)"
        )));
    }

    // Verify we can open with the new size
    let env = Environment::new()
        .set_map_size(new_size)
        .set_max_dbs(32)
        .open(path)
        .map_err(|e| CoreError::Memory(format!("LMDB grow_map_size open: {e}")))?;
    drop(env);

    tracing::info!("Map size grown: {current_size} -> {new_size}");
    Ok(new_size)
}

// ── Encoding Helpers ──────────────────────────────────────────────────

/// Encode bytes as hex string.
fn hex_encode(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        let _ = write!(s, "{b:02x}");
    }
    s
}

/// Decode hex string to bytes.
fn hex_decode(hex: &str) -> Vec<u8> {
    (0..hex.len())
        .step_by(2)
        .filter_map(|i| u8::from_str_radix(&hex[i..i.saturating_add(2).min(hex.len())], 16).ok())
        .collect()
}

/// Encode bytes as base64 string.
fn base64_encode(bytes: &[u8]) -> String {
    use std::fmt::Write;
    const CHARS: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut result = String::new();
    for chunk in bytes.chunks(3) {
        let b0 = chunk[0];
        let b1 = *chunk.get(1).unwrap_or(&0);
        let b2 = *chunk.get(2).unwrap_or(&0);
        let _ = result.write_char(CHARS[(b0 >> 2) as usize & 0x3F] as char);
        let _ = result.write_char(CHARS[((b0 << 4) | (b1 >> 4)) as usize & 0x3F] as char);
        if chunk.len() > 1 {
            let _ = result.write_char(CHARS[((b1 << 2) | (b2 >> 6)) as usize & 0x3F] as char);
        } else {
            let _ = result.write_char('=');
        }
        if chunk.len() > 2 {
            let _ = result.write_char(CHARS[b2 as usize & 0x3F] as char);
        } else {
            let _ = result.write_char('=');
        }
    }
    result
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::memory::Memory;

    #[test]
    fn integrity_check_clean_store() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        // Add some memories
        for i in 0..5 {
            let mem = Memory::new(Galaxy::Codex, format!("memory-{i}"));
            store.put(Galaxy::Codex, &mem).unwrap();
        }

        let report = check_integrity(&store).unwrap();
        assert!(report.is_clean);
        assert_eq!(report.total_valid, 5);
        assert_eq!(report.total_corrupted, 0);
    }

    #[test]
    fn integrity_check_detects_corruption() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        // Add valid memories
        for i in 0..3 {
            let mem = Memory::new(Galaxy::Codex, format!("valid-{i}"));
            store.put(Galaxy::Codex, &mem).unwrap();
        }

        // Inject corrupted data
        store
            .put_raw(Galaxy::Codex, b"corrupted_key_1", b"not valid msgpack")
            .unwrap();
        store
            .put_raw(Galaxy::Codex, b"corrupted_key_2", b"also not valid")
            .unwrap();

        let report = check_integrity(&store).unwrap();
        assert!(!report.is_clean);
        assert_eq!(report.total_corrupted, 2);
        assert_eq!(report.total_valid, 3);

        // Check the galaxy report
        let codex = report
            .galaxies
            .iter()
            .find(|g| g.galaxy == "codex")
            .unwrap();
        assert_eq!(codex.corrupted, 2);
        assert_eq!(codex.corrupted_keys.len(), 2);
    }

    #[test]
    fn repair_quarantines_corrupted_entries() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = MemoryStore::open_default(tmp.path()).unwrap();

        // Add valid memories
        for i in 0..3 {
            let mem = Memory::new(Galaxy::Codex, format!("valid-{i}"));
            store.put(Galaxy::Codex, &mem).unwrap();
        }

        // Inject corrupted data
        store
            .put_raw(Galaxy::Codex, b"corrupt_key_1", b"invalid data 1")
            .unwrap();
        store
            .put_raw(Galaxy::Codex, b"corrupt_key_2", b"invalid data 2")
            .unwrap();

        // Repair
        let report = repair(&mut store, tmp.path()).unwrap();
        assert_eq!(report.quarantined, 2);
        assert!(report.integrity.is_clean);

        // Quarantine file should exist
        let quarantine_path = tmp.path().join("quarantine.jsonl");
        assert!(quarantine_path.exists());

        // Backup should exist
        assert!(report.backup_path.is_some());

        // Store should be clean after repair
        let integrity = check_integrity(&store).unwrap();
        assert!(integrity.is_clean);
        assert_eq!(integrity.total_valid, 3);
    }

    #[test]
    fn repair_preserves_valid_memories() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = MemoryStore::open_default(tmp.path()).unwrap();

        // Add valid memories across galaxies
        let mem1 = Memory::new(Galaxy::Codex, "important data".to_string());
        let mem2 = Memory::new(Galaxy::Research, "research note".to_string());
        let id1 = mem1.metadata.id;
        let id2 = mem2.metadata.id;
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Research, &mem2).unwrap();

        // Inject corruption
        store
            .put_raw(Galaxy::Codex, b"bad_key", b"corrupted")
            .unwrap();

        // Repair
        let _ = repair(&mut store, tmp.path()).unwrap();

        // Valid memories should still be accessible
        let retrieved1 = store.get(Galaxy::Codex, id1).unwrap();
        assert!(retrieved1.is_some());
        assert_eq!(retrieved1.unwrap().content, "important data");

        let retrieved2 = store.get(Galaxy::Research, id2).unwrap();
        assert!(retrieved2.is_some());
        assert_eq!(retrieved2.unwrap().content, "research note");
    }

    #[test]
    fn repair_rebuilds_indexes() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = MemoryStore::open_default(tmp.path()).unwrap();

        // Add a memory with tags
        let mut mem = Memory::new(Galaxy::Codex, "tagged memory".to_string());
        mem.metadata.tags = vec!["important".to_string(), "test".to_string()];
        let content_hash = mem.metadata.content_hash.clone();
        store.put(Galaxy::Codex, &mem).unwrap();

        // Verify index works before repair
        let found = store
            .find_by_content_hash(Galaxy::Codex, &content_hash)
            .unwrap();
        assert!(found.is_some());

        // Inject corruption
        store
            .put_raw(Galaxy::Codex, b"bad_key", b"corrupted")
            .unwrap();

        // Repair
        let report = repair(&mut store, tmp.path()).unwrap();
        assert!(report.indexes_rebuilt > 0);

        // Index should still work after repair
        let found = store
            .find_by_content_hash(Galaxy::Codex, &content_hash)
            .unwrap();
        assert!(found.is_some());
    }

    #[test]
    fn open_with_recovery_clean_store() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let mem = Memory::new(Galaxy::Codex, "test".to_string());
        store.put(Galaxy::Codex, &mem).unwrap();
        drop(store);

        // Reopen with recovery — should work fine
        let store = open_with_recovery(tmp.path(), DEFAULT_MAP_SIZE, RecoveryStrategy::AutoRepair);
        assert!(store.is_ok());
    }

    #[test]
    fn open_with_recovery_auto_repairs() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        // Add valid + corrupted data
        let mem = Memory::new(Galaxy::Codex, "valid".to_string());
        store.put(Galaxy::Codex, &mem).unwrap();
        store
            .put_raw(Galaxy::Codex, b"bad_key", b"corrupted data")
            .unwrap();
        drop(store);

        // Reopen with AutoRepair — should repair and succeed
        let store = open_with_recovery(tmp.path(), DEFAULT_MAP_SIZE, RecoveryStrategy::AutoRepair);
        assert!(store.is_ok());
        let store = store.unwrap();

        // Verify clean
        let report = check_integrity(&store).unwrap();
        assert!(report.is_clean);
        assert_eq!(report.total_valid, 1);
    }

    #[test]
    fn open_with_recovery_none_fails_on_corruption() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        // Add corrupted data
        store
            .put_raw(Galaxy::Codex, b"bad_key", b"corrupted data")
            .unwrap();
        drop(store);

        // Reopen with None — should fail
        let result = open_with_recovery(tmp.path(), DEFAULT_MAP_SIZE, RecoveryStrategy::None);
        assert!(result.is_err());
    }

    #[test]
    fn open_with_recovery_warn_only_succeeds() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();

        // Add corrupted data
        store
            .put_raw(Galaxy::Codex, b"bad_key", b"corrupted data")
            .unwrap();
        drop(store);

        // Reopen with WarnOnly — should succeed
        let store = open_with_recovery(tmp.path(), DEFAULT_MAP_SIZE, RecoveryStrategy::WarnOnly);
        assert!(store.is_ok());
    }

    #[test]
    fn grow_map_size_doubles() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open(tmp.path(), 1024 * 1024).unwrap();
        drop(store);

        let new_size = grow_map_size(tmp.path(), 1024 * 1024).unwrap();
        assert_eq!(new_size, 2 * 1024 * 1024);
    }

    #[test]
    fn grow_map_size_capped_at_max() {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open(tmp.path(), MAX_MAP_SIZE).unwrap();
        drop(store);

        // Already at max — should fail
        let result = grow_map_size(tmp.path(), MAX_MAP_SIZE);
        assert!(result.is_err());
    }

    #[test]
    fn hex_encode_decode_roundtrip() {
        let original = b"hello world";
        let encoded = hex_encode(original);
        let decoded = hex_decode(&encoded);
        assert_eq!(decoded, original);
    }

    #[test]
    fn base64_encode_known_values() {
        assert_eq!(base64_encode(b""), "");
        assert_eq!(base64_encode(b"f"), "Zg==");
        assert_eq!(base64_encode(b"fo"), "Zm8=");
        assert_eq!(base64_encode(b"foo"), "Zm9v");
        assert_eq!(base64_encode(b"foob"), "Zm9vYg==");
        assert_eq!(base64_encode(b"fooba"), "Zm9vYmE=");
        assert_eq!(base64_encode(b"foobar"), "Zm9vYmFy");
    }

    #[test]
    fn integrity_report_summary_clean() {
        let report = IntegrityReport {
            galaxies: vec![GalaxyIntegrity {
                galaxy: "codex".to_string(),
                total: 5,
                valid: 5,
                corrupted: 0,
                corrupted_keys: vec![],
            }],
            total_entries: 5,
            total_valid: 5,
            total_corrupted: 0,
            is_clean: true,
        };
        let summary = report.summary();
        assert!(summary.contains("clean"));
    }

    #[test]
    fn integrity_report_summary_corrupted() {
        let report = IntegrityReport {
            galaxies: vec![GalaxyIntegrity {
                galaxy: "codex".to_string(),
                total: 5,
                valid: 3,
                corrupted: 2,
                corrupted_keys: vec!["ab".to_string(), "cd".to_string()],
            }],
            total_entries: 5,
            total_valid: 3,
            total_corrupted: 2,
            is_clean: false,
        };
        let summary = report.summary();
        assert!(summary.contains("corruption"));
        assert!(summary.contains("2 corrupted"));
    }

    #[test]
    fn recovery_strategy_flags() {
        assert!(!RecoveryStrategy::None.repairs());
        assert!(!RecoveryStrategy::WarnOnly.repairs());
        assert!(RecoveryStrategy::AutoRepair.repairs());
        assert!(RecoveryStrategy::AutoRepairAndGrow.repairs());

        assert!(!RecoveryStrategy::None.grows_map());
        assert!(!RecoveryStrategy::WarnOnly.grows_map());
        assert!(!RecoveryStrategy::AutoRepair.grows_map());
        assert!(RecoveryStrategy::AutoRepairAndGrow.grows_map());
    }

    #[test]
    fn repair_on_clean_store_is_noop() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = MemoryStore::open_default(tmp.path()).unwrap();

        let mem = Memory::new(Galaxy::Codex, "clean".to_string());
        store.put(Galaxy::Codex, &mem).unwrap();

        let report = repair(&mut store, tmp.path()).unwrap();
        assert_eq!(report.quarantined, 0);
        assert!(report.integrity.is_clean);
    }

    #[test]
    fn repair_across_multiple_galaxies() {
        let tmp = tempfile::tempdir().unwrap();
        let mut store = MemoryStore::open_default(tmp.path()).unwrap();

        // Valid memories in different galaxies
        store
            .put(
                Galaxy::Codex,
                &Memory::new(Galaxy::Codex, "codex".to_string()),
            )
            .unwrap();
        store
            .put(
                Galaxy::Research,
                &Memory::new(Galaxy::Research, "research".to_string()),
            )
            .unwrap();
        store
            .put(Galaxy::Aria, &Memory::new(Galaxy::Aria, "aria".to_string()))
            .unwrap();

        // Corrupted entries in different galaxies
        store.put_raw(Galaxy::Codex, b"bad1", b"x").unwrap();
        store.put_raw(Galaxy::Research, b"bad2", b"y").unwrap();

        let report = repair(&mut store, tmp.path()).unwrap();
        assert_eq!(report.quarantined, 2);
        assert!(report.integrity.is_clean);
        assert_eq!(report.integrity.total_valid, 3);
    }
}
