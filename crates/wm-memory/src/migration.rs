//! Q39 slice B — background encrypt-on-rewrite migration.
//!
//! Existing plaintext stores seal record-by-record in bounded LMDB batches
//! (one write transaction per batch), tracked by the `migration:v1` ledger
//! row in the keyring DBI. The contract is deliberately simple and
//! crash-safe:
//!
//! - Only 16-byte keys (UUID records) in record galaxies are candidates;
//!   non-record DBIs (karma, dharma, associations, embeddings) are never
//!   touched, and raw non-record rows are skipped.
//! - Values that already carry the sealed-record magic are counted and
//!   skipped — re-running is idempotent.
//! - Plaintext values are decoded with the legacy codec and re-sealed
//!   through [`crate::codec::seal_record`], so a record that cannot be
//!   decoded is *counted and skipped*, never rewritten blind.
//! - The ledger is written after each committed batch. A crash between the
//!   batch commit and the ledger write re-scans a bounded prefix; sealing is
//!   idempotent, so the repeat is harmless.
//! - A keyring-absent store (mode `off`) has nothing to migrate and this
//!   module is a provable no-op (no ledger, no writes).
//!
//! Design: `docs/Q39_CRYPTO_ERASURE_DESIGN.md` §7 (slice B);
//! plan: `planning/private/Q10_SLICE_B_PLAN_2026-09-19.md`.

use crate::at_rest::{
    MigrationGalaxyState, MigrationLedger, read_migration_ledger, write_migration_ledger,
};
use crate::store::MemoryStore;
use lmdb::{Cursor, Database, Transaction, WriteFlags};
use wm_core::{CoreError, Galaxy, Result};

/// Default records per write transaction.
pub const DEFAULT_MIGRATION_BATCH: usize = 256;

/// Galaxies whose entries are `Memory` records.
///
/// Every galaxy except the four special-purpose DBIs (Karma ledger, Dharma
/// rules, Associations links, Embeddings vectors), whose rows are never
/// Memory records and must not be sealed.
pub const RECORD_GALAXIES: [Galaxy; 12] = [
    Galaxy::Aria,
    Galaxy::Citta,
    Galaxy::Codex,
    Galaxy::Journals,
    Galaxy::Dreams,
    Galaxy::Research,
    Galaxy::Sessions,
    Galaxy::Substrate,
    Galaxy::Tutorial,
    Galaxy::Universal,
    Galaxy::Valkyrie,
    Galaxy::Telemetry,
];

/// What happened to one galaxy in one migration pass.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GalaxyMigrationReport {
    /// Galaxy database name.
    pub galaxy: String,
    /// Keys examined this pass (newly sealed + skips).
    pub scanned: u64,
    /// Records newly sealed this pass.
    pub encrypted: u64,
    /// Records already sealed (idempotent skips).
    pub already_sealed: u64,
    /// Non-record rows skipped (keys that are not 16-byte UUIDs).
    pub skipped_non_record: u64,
    /// Plaintext values that could not be decoded (counted, never rewritten).
    pub undecodable: u64,
    /// Whether the galaxy's keyspace was fully scanned this pass.
    pub done: bool,
}

/// Aggregate report for one `migrate_at_rest_records` invocation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AtRestMigrationReport {
    /// Per-galaxy results, in request order.
    pub galaxies: Vec<GalaxyMigrationReport>,
    /// True when this store has no keyring (mode `off`) — the no-op path.
    pub no_keyring: bool,
    /// Total records newly sealed.
    pub total_encrypted: u64,
    /// Total already-sealed records seen.
    pub total_already_sealed: u64,
    /// Total undecodable plaintext records seen.
    pub total_undecodable: u64,
}

impl AtRestMigrationReport {
    const fn empty_no_keyring() -> Self {
        Self {
            galaxies: Vec::new(),
            no_keyring: true,
            total_encrypted: 0,
            total_already_sealed: 0,
            total_undecodable: 0,
        }
    }

    /// Whether every selected galaxy finished scanning its keyspace.
    #[must_use]
    pub fn all_done(&self) -> bool {
        self.no_keyring || self.galaxies.iter().all(|g| g.done)
    }
}

/// Per-galaxy at-rest record inventory for the doctor (read-only; magic
/// check only — values are never decrypted).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GalaxyAtRestCounts {
    /// Galaxy database name.
    pub galaxy: String,
    /// Records carrying the sealed-record envelope.
    pub sealed: u64,
    /// Records without the envelope (unencrypted at rest).
    pub plaintext: u64,
    /// Non-record rows (keys that are not 16-byte UUIDs).
    pub non_record: u64,
}

/// Count sealed vs plaintext records across the record galaxies.
///
/// Read-only: uses the WMEN magic only, never decrypts, never writes.
pub fn at_rest_record_counts(store: &MemoryStore) -> Result<Vec<GalaxyAtRestCounts>> {
    let mut out = Vec::with_capacity(RECORD_GALAXIES.len());
    for galaxy in RECORD_GALAXIES {
        let db = store.galaxy_db(galaxy)?;
        let tx = store
            .env()
            .begin_ro_txn()
            .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed (at-rest counts): {e}")))?;
        let mut cursor = tx
            .open_ro_cursor(db)
            .map_err(|e| CoreError::Memory(format!("LMDB cursor failed (at-rest counts): {e}")))?;
        let mut counts = GalaxyAtRestCounts {
            galaxy: galaxy.db_name().to_string(),
            ..GalaxyAtRestCounts::default()
        };
        for (key, value) in cursor.iter() {
            if !crate::at_rest::migration_candidate_key(key) {
                counts.non_record += 1;
            } else if crate::codec::is_sealed_record(value) {
                counts.sealed += 1;
            } else {
                counts.plaintext += 1;
            }
        }
        drop(cursor);
        tx.commit()
            .map_err(|e| CoreError::Memory(format!("LMDB commit failed (at-rest counts): {e}")))?;
        out.push(counts);
    }
    Ok(out)
}

/// Read the current migration ledger without migrating (doctor disclosure).
///
/// Returns `None` for a keyring-absent store; `Some(ledger)` otherwise
/// (a missing row yields the default/empty ledger).
pub fn migration_ledger(store: &MemoryStore) -> Result<Option<MigrationLedger>> {
    let Some(db) = store.keyring_db() else {
        return Ok(None);
    };
    read_migration_ledger(store.env(), db).map(Some)
}

/// Migrate plaintext records to sealed records in bounded batches.
///
/// `galaxies` selects which galaxy databases to process; `batch` bounds the
/// records per write transaction (0 uses [`DEFAULT_MIGRATION_BATCH`]).
/// A keyring-absent store returns the no-op report without writing anything.
///
/// **Writer exclusivity:** each batch reads a page and then rewrites it in a
/// separate transaction, so a concurrent writer in the same process could
/// interleave between the two and have its record overwritten by a re-sealed
/// older version. The CLI path is exclusive by construction (non-blocking
/// writer-lock probe + one migrating process); any future in-process
/// background pass must take the same posture or fold read+write into one
/// read-write cursor transaction.
pub fn migrate_at_rest_records(
    store: &MemoryStore,
    galaxies: &[Galaxy],
    batch: usize,
) -> Result<AtRestMigrationReport> {
    let Some(keyring_db) = store.keyring_db() else {
        return Ok(AtRestMigrationReport::empty_no_keyring());
    };
    let batch = if batch == 0 {
        DEFAULT_MIGRATION_BATCH
    } else {
        batch
    };

    let mut ledger = read_migration_ledger(store.env(), keyring_db)?;
    let mut report = AtRestMigrationReport {
        galaxies: Vec::new(),
        no_keyring: false,
        total_encrypted: 0,
        total_already_sealed: 0,
        total_undecodable: 0,
    };

    for &galaxy in galaxies {
        let name = galaxy.db_name().to_string();
        let resume = ledger.galaxies.get(&name).cloned().unwrap_or_default();
        let galaxy_report = migrate_galaxy(store, galaxy, keyring_db, batch, &resume, &mut ledger)?;

        report.total_encrypted += galaxy_report.encrypted;
        report.total_already_sealed += galaxy_report.already_sealed;
        report.total_undecodable += galaxy_report.undecodable;
        report.galaxies.push(galaxy_report);
    }

    Ok(report)
}

/// Migrate one galaxy, resuming from `resume.cursor_hex` when a previous
/// pass stopped mid-keyspace. The ledger is updated (and persisted) after
/// every committed batch.
fn migrate_galaxy(
    store: &MemoryStore,
    galaxy: Galaxy,
    keyring_db: Database,
    batch: usize,
    resume: &MigrationGalaxyState,
    ledger: &mut MigrationLedger,
) -> Result<GalaxyMigrationReport> {
    let Some(dek) = store.record_cipher(galaxy) else {
        return Err(CoreError::Memory(format!(
            "at-rest migration requested for {} but its DEK is not loaded",
            galaxy.db_name()
        )));
    };
    let db = store.galaxy_db(galaxy)?;
    // A `done` galaxy is re-verified from the start of the keyspace: any
    // plaintext that appeared after completion (restore, raw import) gets
    // sealed on the next run.
    let resume_key = if resume.done {
        Vec::new()
    } else {
        decode_cursor(&resume.cursor_hex)?
    };
    // Resolve the resume point to a key that exists *now*: `iter_from`
    // panics past the end of the keyspace, and a store that shrank since
    // the ledger write must resume cleanly (or finish). When the ledger
    // cursor was deleted, the resolved successor was never examined, so it
    // must not be skipped.
    let Some(mut cursor_key) = first_key_at_or_after(store, db, &resume_key)? else {
        let entry = ledger
            .galaxies
            .entry(galaxy.db_name().to_string())
            .or_default();
        entry.encrypted = resume.encrypted;
        entry.cursor_hex = String::new();
        entry.done = true;
        ledger.updated_at = chrono::Utc::now().to_rfc3339();
        write_migration_ledger(store.env(), keyring_db, ledger)?;
        return Ok(GalaxyMigrationReport {
            galaxy: galaxy.db_name().to_string(),
            scanned: 0,
            encrypted: 0,
            already_sealed: 0,
            skipped_non_record: 0,
            undecodable: 0,
            done: true,
        });
    };
    // Ledger counts are cumulative across runs; `report.encrypted` is this
    // run's running total, so entries are written as `base + report`.
    let base_encrypted = resume.encrypted;
    // The anchor is skipped only when it is the exact key a previous run
    // finished examining; a fresh start examines every key.
    let mut anchor_examined = !resume_key.is_empty() && cursor_key == resume_key;

    let mut report = GalaxyMigrationReport {
        galaxy: galaxy.db_name().to_string(),
        scanned: 0,
        encrypted: 0,
        already_sealed: 0,
        skipped_non_record: 0,
        undecodable: 0,
        done: false,
    };

    loop {
        // Phase 1 — read txn: collect up to `batch` plaintext candidates and
        // record the last key examined. The resume anchor (when a previous
        // run finished on it) is skipped.
        let mut candidates: Vec<(Vec<u8>, Vec<u8>, u64)> = Vec::new();
        let mut last_examined: Option<Vec<u8>> = None;
        {
            let tx = store
                .env()
                .begin_ro_txn()
                .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed (migration): {e}")))?;
            let mut cursor = tx
                .open_ro_cursor(db)
                .map_err(|e| CoreError::Memory(format!("LMDB cursor failed (migration): {e}")))?;
            for (key, value) in cursor.iter_from(cursor_key.as_slice()) {
                if anchor_examined && key == cursor_key.as_slice() {
                    continue;
                }
                if candidates.len() >= batch {
                    break;
                }
                last_examined = Some(key.to_vec());
                report.scanned += 1;
                if !crate::at_rest::migration_candidate_key(key) {
                    report.skipped_non_record += 1;
                    continue;
                }
                if crate::codec::is_sealed_record(value) {
                    report.already_sealed += 1;
                    continue;
                }
                match crate::at_rest::decode_plaintext_for_migration(value) {
                    Some(memory) => {
                        candidates.push((key.to_vec(), value.to_vec(), memory.metadata.version));
                    }
                    None => report.undecodable += 1,
                }
            }
            drop(cursor);
            tx.commit()
                .map_err(|e| CoreError::Memory(format!("LMDB commit failed (migration): {e}")))?;
        }

        let Some(last_key) = last_examined else {
            // Keyspace exhausted: nothing left to examine.
            report.done = true;
            break;
        };

        // Phase 2 — write txn: seal the batch, then advance the cursor.
        if !candidates.is_empty() {
            let mut tx = store
                .env()
                .begin_rw_txn()
                .map_err(|e| CoreError::Memory(format!("LMDB rw_txn failed (migration): {e}")))?;
            for (key, plaintext, version) in &candidates {
                let record_id: [u8; 16] = key
                    .as_slice()
                    .try_into()
                    .map_err(|_| CoreError::Memory("migration key is not a 16-byte id".into()))?;
                let sealed = crate::at_rest::seal_migrated_record(
                    plaintext,
                    dek,
                    galaxy.db_name(),
                    &record_id,
                    *version,
                )?;
                tx.put(db, key, &sealed, WriteFlags::default())
                    .map_err(|e| CoreError::Memory(format!("LMDB put failed (migration): {e}")))?;
                report.encrypted += 1;
            }
            tx.commit()
                .map_err(|e| CoreError::Memory(format!("LMDB commit failed (migration): {e}")))?;
        }

        cursor_key = last_key;
        anchor_examined = true;
        let entry = ledger.galaxies.entry(report.galaxy.clone()).or_default();
        entry.encrypted = base_encrypted + report.encrypted;
        entry.cursor_hex = encode_cursor(&cursor_key);
        entry.done = false;
        ledger.updated_at = chrono::Utc::now().to_rfc3339();
        write_migration_ledger(store.env(), keyring_db, ledger)?;
    }

    let entry = ledger.galaxies.entry(report.galaxy.clone()).or_default();
    entry.encrypted = base_encrypted + report.encrypted;
    entry.cursor_hex = String::new();
    entry.done = true;
    ledger.updated_at = chrono::Utc::now().to_rfc3339();
    write_migration_ledger(store.env(), keyring_db, ledger)?;

    Ok(report)
}

/// First key in `db` at or after `resume_key` (`None` when the keyspace is
/// exhausted or empty). Avoids `iter_from`'s panic when the resume cursor
/// points past the end of a store that shrank since the ledger write.
fn first_key_at_or_after(
    store: &MemoryStore,
    db: Database,
    resume_key: &[u8],
) -> Result<Option<Vec<u8>>> {
    let tx = store
        .env()
        .begin_ro_txn()
        .map_err(|e| CoreError::Memory(format!("LMDB ro_txn failed (migration): {e}")))?;
    let mut cursor = tx
        .open_ro_cursor(db)
        .map_err(|e| CoreError::Memory(format!("LMDB cursor failed (migration): {e}")))?;
    // Cursor-op constant from lmdb.h (frozen LMDB ABI): the `lmdb` crate's
    // `iter_from` unwraps a SetRange miss, and a miss is a normal state here
    // (the resume cursor can sort past every remaining key). An empty resume
    // key means "start of the keyspace" — `MDB_SET_RANGE` rejects empty
    // keys, so read the first entry instead.
    const MDB_SET_RANGE: u32 = 17;
    let found = if resume_key.is_empty() {
        cursor.iter().next().map(|(key, _)| key.to_vec())
    } else {
        match cursor.get(Some(resume_key), None, MDB_SET_RANGE) {
            Ok((key, _)) => key.map(<[u8]>::to_vec),
            Err(lmdb::Error::NotFound) => None,
            Err(e) => {
                return Err(CoreError::Memory(format!(
                    "LMDB cursor seek failed (migration): {e}"
                )));
            }
        }
    };
    drop(cursor);
    tx.commit()
        .map_err(|e| CoreError::Memory(format!("LMDB commit failed (migration): {e}")))?;
    Ok(found)
}

fn encode_cursor(key: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(key.len() * 2);
    for b in key {
        out.push(HEX[(b >> 4) as usize] as char);
        out.push(HEX[(b & 0x0f) as usize] as char);
    }
    out
}

fn decode_cursor(hex: &str) -> Result<Vec<u8>> {
    if hex.is_empty() {
        return Ok(Vec::new());
    }
    if hex.len() % 2 != 0 {
        return Err(CoreError::Memory(
            "migration ledger cursor is not valid hex".into(),
        ));
    }
    let mut out = Vec::with_capacity(hex.len() / 2);
    let bytes = hex.as_bytes();
    for chunk in bytes.chunks_exact(2) {
        let hi = hex_val(chunk[0])
            .ok_or_else(|| CoreError::Memory("migration ledger cursor is not valid hex".into()))?;
        let lo = hex_val(chunk[1])
            .ok_or_else(|| CoreError::Memory("migration ledger cursor is not valid hex".into()))?;
        out.push((hi << 4) | lo);
    }
    Ok(out)
}

const fn hex_val(b: u8) -> Option<u8> {
    match b {
        b'0'..=b'9' => Some(b - b'0'),
        b'a'..=b'f' => Some(b - b'a' + 10),
        b'A'..=b'F' => Some(b - b'A' + 10),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::at_rest::AtRestConfig;
    use crate::memory::Memory;
    use crate::store::MemoryStore;

    const TEST_MAP: usize = 16 * 1024 * 1024;

    fn open_plain(store_dir: &std::path::Path) -> MemoryStore {
        MemoryStore::open_with_at_rest(store_dir, TEST_MAP, &AtRestConfig::off()).unwrap()
    }

    fn open_keyfile(store_dir: &std::path::Path) -> MemoryStore {
        MemoryStore::open_with_at_rest(store_dir, TEST_MAP, &AtRestConfig::keyfile()).unwrap()
    }

    fn is_sealed(store: &MemoryStore, galaxy: Galaxy, id: uuid::Uuid) -> bool {
        store
            .get_raw(galaxy, id.as_bytes())
            .unwrap()
            .is_some_and(|raw| crate::codec::is_sealed_record(&raw))
    }

    #[test]
    fn plaintext_store_is_a_provable_noop() {
        let tmp = tempfile::tempdir().unwrap();
        let store = open_plain(tmp.path());
        let mem = Memory::new(Galaxy::Codex, "still plaintext".into());
        let id = mem.metadata.id;
        store.put(Galaxy::Codex, &mem).unwrap();

        let report =
            migrate_at_rest_records(&store, &RECORD_GALAXIES, DEFAULT_MIGRATION_BATCH).unwrap();
        assert!(report.no_keyring);
        assert!(report.all_done());
        assert_eq!(report.total_encrypted, 0);
        assert!(migration_ledger(&store).unwrap().is_none());
        assert!(
            !is_sealed(&store, Galaxy::Codex, id),
            "plaintext store must stay byte-identical"
        );
    }

    #[test]
    fn mixed_store_migrates_all_records_and_is_idempotent() {
        let tmp = tempfile::tempdir().unwrap();
        let mut ids = Vec::new();
        {
            let store = open_plain(tmp.path());
            for i in 0..5 {
                let mem = Memory::new(Galaxy::Codex, format!("legacy record {i}"));
                ids.push(mem.metadata.id);
                store.put(Galaxy::Codex, &mem).unwrap();
            }
        }

        let store = open_keyfile(tmp.path());
        let report =
            migrate_at_rest_records(&store, &RECORD_GALAXIES, DEFAULT_MIGRATION_BATCH).unwrap();
        assert!(!report.no_keyring);
        assert!(report.all_done(), "{report:?}");
        assert_eq!(report.total_encrypted, 5, "{report:?}");
        assert!(ids.iter().all(|id| is_sealed(&store, Galaxy::Codex, *id)));
        assert_eq!(store.scan_all(Galaxy::Codex).unwrap().len(), 5);

        let ledger = migration_ledger(&store).unwrap().unwrap();
        assert_eq!(ledger.galaxies["codex"].encrypted, 5);
        assert!(ledger.galaxies["codex"].done);

        // Second run: nothing new to seal, still all readable.
        let second =
            migrate_at_rest_records(&store, &RECORD_GALAXIES, DEFAULT_MIGRATION_BATCH).unwrap();
        assert_eq!(second.total_encrypted, 0, "{second:?}");
        assert!(second.all_done(), "{second:?}");
        assert_eq!(store.scan_all(Galaxy::Codex).unwrap().len(), 5);
    }

    #[test]
    fn resume_from_a_mid_way_ledger_completes_the_remaining_records() {
        let tmp = tempfile::tempdir().unwrap();
        let mut ids = Vec::new();
        {
            let store = open_plain(tmp.path());
            for i in 0..10 {
                let mem = Memory::new(Galaxy::Codex, format!("resume record {i}"));
                ids.push(mem.metadata.id);
                store.put(Galaxy::Codex, &mem).unwrap();
            }
        }
        // LMDB orders keys by raw bytes; simulate the state after a crash
        // mid-migration: the first four records are sealed and the ledger
        // holds their last key as the resume cursor.
        ids.sort_by_key(|id| *id.as_bytes());

        let store = open_keyfile(tmp.path());
        let keyring_db = store.keyring_db().expect("keyring");
        {
            let dek = *store
                .at_rest_state()
                .unwrap()
                .galaxy_dek(Galaxy::Codex.db_name())
                .unwrap();
            let db = store.galaxy_db(Galaxy::Codex).unwrap();
            let mut tx = store.env().begin_rw_txn().unwrap();
            for id in &ids[..4] {
                let memory = store.get(Galaxy::Codex, *id).unwrap().unwrap();
                let sealed = crate::codec::seal_record(
                    &rmp_serde::to_vec_named(&memory).unwrap(),
                    &dek,
                    Galaxy::Codex.db_name(),
                    id.as_bytes(),
                    memory.metadata.version,
                )
                .unwrap();
                tx.put(db, id.as_bytes(), &sealed, WriteFlags::default())
                    .unwrap();
            }
            tx.commit().unwrap();

            let mut ledger = MigrationLedger::default();
            ledger.galaxies.insert(
                Galaxy::Codex.db_name().to_string(),
                MigrationGalaxyState {
                    encrypted: 4,
                    cursor_hex: encode_cursor(ids[3].as_bytes()),
                    done: false,
                },
            );
            write_migration_ledger(store.env(), keyring_db, &ledger).unwrap();
        }

        let report = migrate_at_rest_records(&store, &[Galaxy::Codex], 4).unwrap();
        assert!(report.all_done(), "{report:?}");
        assert_eq!(report.total_encrypted, 6, "{report:?}");
        assert_eq!(report.total_already_sealed, 0, "{report:?}");
        assert!(ids.iter().all(|id| is_sealed(&store, Galaxy::Codex, *id)));
        assert_eq!(store.scan_all(Galaxy::Codex).unwrap().len(), 10);

        let ledger = migration_ledger(&store).unwrap().unwrap();
        assert!(ledger.galaxies["codex"].done);
        assert_eq!(ledger.galaxies["codex"].encrypted, 10);
    }

    #[test]
    fn a_deleted_resume_cursor_resumes_at_its_successor() {
        let tmp = tempfile::tempdir().unwrap();
        let mut ids = Vec::new();
        {
            let store = open_plain(tmp.path());
            for i in 0..3 {
                let mem = Memory::new(Galaxy::Codex, format!("shrunk store {i}"));
                ids.push(mem.metadata.id);
                store.put(Galaxy::Codex, &mem).unwrap();
            }
        }
        ids.sort_by_key(|id| *id.as_bytes());

        let store = open_keyfile(tmp.path());
        let keyring_db = store.keyring_db().expect("keyring");
        // Ledger points at the first key, which was then deleted (e.g. the
        // record was erased between runs): the successor must be examined,
        // not skipped.
        store.delete(Galaxy::Codex, ids[0]).unwrap();
        let mut ledger = MigrationLedger::default();
        ledger.galaxies.insert(
            Galaxy::Codex.db_name().to_string(),
            MigrationGalaxyState {
                encrypted: 0,
                cursor_hex: encode_cursor(ids[0].as_bytes()),
                done: false,
            },
        );
        write_migration_ledger(store.env(), keyring_db, &ledger).unwrap();

        let report = migrate_at_rest_records(&store, &[Galaxy::Codex], 0).unwrap();
        assert!(report.all_done(), "{report:?}");
        assert_eq!(report.total_encrypted, 2, "{report:?}");
        assert!(is_sealed(&store, Galaxy::Codex, ids[1]));
        assert!(is_sealed(&store, Galaxy::Codex, ids[2]));
    }

    #[test]
    fn undecodable_plaintext_is_counted_skipped_and_left_untouched() {
        let tmp = tempfile::tempdir().unwrap();
        let id = uuid::Uuid::new_v4();
        {
            let store = open_plain(tmp.path());
            store
                .put_raw(Galaxy::Codex, id.as_bytes(), b"not a memory record")
                .unwrap();
            let mem = Memory::new(Galaxy::Codex, "good record".into());
            store.put(Galaxy::Codex, &mem).unwrap();
        }

        let store = open_keyfile(tmp.path());
        let report = migrate_at_rest_records(&store, &[Galaxy::Codex], 0).unwrap();
        assert_eq!(report.total_encrypted, 1, "{report:?}");
        assert_eq!(report.total_undecodable, 1, "{report:?}");
        assert_eq!(
            store
                .get_raw(Galaxy::Codex, id.as_bytes())
                .unwrap()
                .unwrap(),
            b"not a memory record",
            "undecodable rows are never rewritten"
        );
    }

    #[test]
    fn non_record_galaxies_are_never_touched() {
        let tmp = tempfile::tempdir().unwrap();
        {
            let store = open_plain(tmp.path());
            store
                .put_raw(Galaxy::Karma, b"karma:entry:1", b"chain-payload")
                .unwrap();
            store
                .put_raw(Galaxy::Associations, &[0u8; 32], b"assoc-payload")
                .unwrap();
        }

        let store = open_keyfile(tmp.path());
        let report =
            migrate_at_rest_records(&store, &RECORD_GALAXIES, DEFAULT_MIGRATION_BATCH).unwrap();
        assert_eq!(report.total_encrypted, 0, "{report:?}");
        assert_eq!(report.total_undecodable, 0, "{report:?}");
        assert_eq!(
            store
                .get_raw(Galaxy::Karma, b"karma:entry:1")
                .unwrap()
                .unwrap(),
            b"chain-payload"
        );
        assert_eq!(
            store
                .get_raw(Galaxy::Associations, &[0u8; 32])
                .unwrap()
                .unwrap(),
            b"assoc-payload"
        );
    }

    #[test]
    fn a_plaintext_record_added_after_done_is_resealed_on_the_next_run() {
        let tmp = tempfile::tempdir().unwrap();
        let store = open_keyfile(tmp.path());
        let report =
            migrate_at_rest_records(&store, &RECORD_GALAXIES, DEFAULT_MIGRATION_BATCH).unwrap();
        assert!(report.all_done(), "{report:?}");

        // A restore/raw import introduces a plaintext record post-migration.
        let legacy = Memory::new(Galaxy::Codex, "restored plaintext".into());
        let id = legacy.metadata.id;
        let plaintext = {
            let off = open_plain(&tmp.path().join("scratch"));
            off.put(Galaxy::Codex, &legacy).unwrap();
            off.get_raw(Galaxy::Codex, id.as_bytes()).unwrap().unwrap()
        };
        store
            .put_raw(Galaxy::Codex, id.as_bytes(), &plaintext)
            .unwrap();
        assert!(!is_sealed(&store, Galaxy::Codex, id));

        let second =
            migrate_at_rest_records(&store, &RECORD_GALAXIES, DEFAULT_MIGRATION_BATCH).unwrap();
        assert_eq!(second.total_encrypted, 1, "{second:?}");
        assert!(is_sealed(&store, Galaxy::Codex, id));
    }
}
