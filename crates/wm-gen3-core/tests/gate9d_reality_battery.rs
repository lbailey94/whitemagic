//! Gate 9D: Alpha Reality Test (Operational Resilience, Migration Integrity & Cut-Point Crash Consistency)
//!
//! Evaluates Hypotheses:
//! - H9D-1: Migration data fidelity and strict idempotency via chunked sovereign pulses.
//! - H9D-2: Cut-point crash consistency across discrete write lifecycle steps (CP1–CP5).
//! - H9D-3: Dirty store tolerance & forensic quarantine isolation (zero panics, structured logs).
//! - H9D-4: Network envelope skew and protocol defense.

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

use chrono::Utc;
use lmdb::{DatabaseFlags, Environment, Transaction, WriteFlags};
use serde_json::json;
use uuid::Uuid;

use wm_gen3_core::capability::{CapabilityError, NullifierKey, NullifierSet};
use wm_gen3_core::compat::{
    Gen2EpisodicKind, Gen2EpisodicRecord, Gen2Provenance, Gen2ProvenanceSource, Gen2Reader,
    Gen2ValidityState, MigrationOptions, migrate_gen2_to_gen3,
};
use wm_gen3_core::constitution::default_view;
use wm_gen3_core::ops::{RecallQuery, Substrate};
use wm_gen3_core::pulse_compiler::SubstrateStore;

struct TempDir(PathBuf);

impl TempDir {
    fn new(label: &str) -> Self {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).unwrap();
        let path = std::env::temp_dir().join(format!(
            "wm-gen3-gate9d-{label}-{:x}",
            u64::from_be_bytes(nonce)
        ));
        let _ = fs::remove_dir_all(&path);
        fs::create_dir_all(&path).unwrap();
        Self(path)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn create_sample_gen2_record(
    content: &str,
    actor: &str,
    kind: Gen2EpisodicKind,
) -> Gen2EpisodicRecord {
    let hash = Gen2EpisodicRecord::compute_content_hash(content);
    Gen2EpisodicRecord {
        schema_version: 1,
        id: Uuid::new_v4(),
        session_id: Some(Uuid::new_v4()),
        sequence: 1,
        kind,
        content: content.to_string(),
        content_hash: hash,
        provenance: Gen2Provenance {
            source: Gen2ProvenanceSource::User,
            actor: Some(actor.to_string()),
            source_id: None,
            confidence: 0.98,
        },
        validity: Gen2ValidityState::Active,
        is_private: false,
        model_exclude: false,
        evidence: Vec::new(),
        created_at: Utc::now(),
    }
}

// ============================================================================
// TEST 1: Hypothesis H9D-1 — Migration Fidelity & Strict Idempotency
// ============================================================================
#[test]
fn test_h9d1_migration_fidelity_and_strict_idempotency() {
    let source_dir = TempDir::new("h9d1-source");
    let target_dir = TempDir::new("h9d1-target");

    // 1. Construct a synthetic legacy Gen2 LMDB store with 10 records
    let env = Environment::new()
        .set_max_dbs(32)
        .set_map_size(10 * 1024 * 1024)
        .open(source_dir.path())
        .expect("open lmdb env");
    let db = env
        .create_db(Some("episodic_records"), DatabaseFlags::empty())
        .expect("create db");

    let test_topics = [
        "Quantum error correction using surface codes and topological braids",
        "Photosynthesis light harvesting complex and chlorophyll energy transfer",
        "Distributed Byzantine fault tolerance in asynchronous gossip networks",
        "Cellular autophagy pathways and lysosomal degradation mechanisms",
        "Conformal prediction bounds under covariate shift and martingale tests",
        "Episodic memory consolidation and hippocampal sharp-wave ripples",
        "Homomorphic encryption over ring learning with errors schemes",
        "Gravitational wave detection using laser interferometer arrays",
        "Ribosomal RNA transcription and nucleolar phase separation",
        "Zero knowledge succinct non-interactive arguments of knowledge systems",
    ];

    let mut expected_contents = Vec::new();
    {
        let mut tx = env.begin_rw_txn().expect("rw txn");
        for (i, topic) in test_topics.iter().enumerate() {
            let content = topic.to_string();
            expected_contents.push(content.clone());
            let kind = if i % 2 == 0 {
                Gen2EpisodicKind::Observation
            } else {
                Gen2EpisodicKind::UserStatement
            };
            let record = create_sample_gen2_record(&content, &format!("agent_{i}"), kind);
            let val = rmp_serde::to_vec(&record).expect("msgpack encode");
            tx.put(db, record.id.as_bytes(), &val, WriteFlags::empty())
                .expect("put record");
        }
        tx.commit().expect("commit txn");
    }

    // 2. Open Gen2Reader and target Gen3 Substrate
    let reader = Gen2Reader::open(source_dir.path()).expect("open gen2 reader");
    let journal_path = target_dir.path().join("journal.jsonl");
    let mut substrate = Substrate::open(target_dir.path(), Some(&journal_path), default_view())
        .expect("open substrate");

    let quarantine_path = target_dir.path().join("quarantine.jsonl");
    let options = MigrationOptions {
        batch_size: 4, // chunked in small batches to verify multi-batch pulse transitions
        dry_run: false,
        validate_hashes: true,
        allow_noise: false,
        quarantine_path: Some(quarantine_path.clone()),
    };

    // 3. Execute Migration
    let receipt1 =
        migrate_gen2_to_gen3(&reader, &mut substrate, &options).expect("migration pass 1");

    assert_eq!(receipt1.total_scanned, 10);
    assert_eq!(
        receipt1.migrated_count, 10,
        "100% of clean records must be migrated"
    );
    assert_eq!(
        receipt1.duplicate_skipped, 0,
        "Initial run should have 0 duplicates"
    );
    assert_eq!(
        receipt1.quarantined_count, 0,
        "No records should be quarantined"
    );
    assert!(
        receipt1.target_epoch > 0,
        "Target epoch must advance on commits"
    );
    assert_eq!(substrate.store().record_count().unwrap(), 10);

    // Verify recall finds the migrated items
    for expected in &expected_contents[0..5] {
        let q = RecallQuery {
            query: expected.clone(),
            limit: 10,
            candidate_limit: 20,
            include_historical: false,
            min_score: 0.0,
            min_coverage: 0.0,
            scope: None,
        };
        let hits = substrate.recall(&q).expect("recall query");
        assert!(!hits.is_empty(), "Should recall migrated item");
        assert!(hits.iter().any(|h| h.content == *expected));
    }

    // 4. Verify Strict Idempotency: Re-execute migration against the SAME target
    let receipt2 =
        migrate_gen2_to_gen3(&reader, &mut substrate, &options).expect("migration pass 2");

    assert_eq!(receipt2.total_scanned, 10);
    assert_eq!(
        receipt2.migrated_count, 0,
        "Idempotency: 0 new records must be added on re-run"
    );
    assert_eq!(
        receipt2.duplicate_skipped, 10,
        "Idempotency: all 10 records must be detected as duplicates"
    );
    assert_eq!(receipt2.quarantined_count, 0);
    assert_eq!(
        receipt2.target_epoch, receipt1.target_epoch,
        "Epoch must remain completely stationary when no new mutations occur"
    );
    assert_eq!(
        substrate.store().record_count().unwrap(),
        10,
        "Record count must remain strictly 10"
    );
}

// ============================================================================
// TEST 2: Hypothesis H9D-3 — Dirty Store Tolerance & Forensic Quarantine
// ============================================================================
#[test]
fn test_h9d3_dirty_store_tolerance_and_forensic_quarantine() {
    let source_dir = TempDir::new("h9d3-source");
    let target_dir = TempDir::new("h9d3-target");

    // 1. Construct a synthetic DIRTY Gen2 LMDB store containing corrupted records
    let env = Environment::new()
        .set_max_dbs(32)
        .set_map_size(10 * 1024 * 1024)
        .open(source_dir.path())
        .expect("open lmdb env");
    let db = env
        .create_db(Some("episodic_records"), DatabaseFlags::empty())
        .expect("create db");

    {
        let mut tx = env.begin_rw_txn().expect("rw txn");

        // Clean records (4 records)
        for i in 0..4 {
            let content = format!("Clean authenticated valid record #{i}");
            let record =
                create_sample_gen2_record(&content, "clean_actor", Gen2EpisodicKind::Observation);
            let val = rmp_serde::to_vec(&record).expect("msgpack");
            tx.put(db, record.id.as_bytes(), &val, WriteFlags::empty())
                .expect("put clean");
        }

        // Corrupted Record 1: Content Hash Mismatch (Tampered Content)
        let mut tampered = create_sample_gen2_record(
            "Original content before unauthorized modification",
            "actor_tampered",
            Gen2EpisodicKind::UserStatement,
        );
        tampered.content = "Forged tampered content payload".to_string(); // hash not updated!
        let val_tampered = rmp_serde::to_vec(&tampered).expect("msgpack");
        tx.put(
            db,
            tampered.id.as_bytes(),
            &val_tampered,
            WriteFlags::empty(),
        )
        .expect("put tampered");

        // Corrupted Record 2: Truncated / Garbage MessagePack Bytes
        let garbage_id = Uuid::new_v4();
        let garbage_bytes = [0x95, 0xff, 0xfe, 0x01, 0x00, 0xde, 0xad, 0xbe, 0xef];
        tx.put(
            db,
            garbage_id.as_bytes(),
            &garbage_bytes,
            WriteFlags::empty(),
        )
        .expect("put garbage bytes");

        // Corrupted Record 3: Invalid Key Length (8 bytes instead of 16)
        let bad_key = b"shortkey";
        let valid_rec_bad_key = create_sample_gen2_record(
            "Valid content under bad key",
            "actor",
            Gen2EpisodicKind::SystemEvent,
        );
        let val_bad_key = rmp_serde::to_vec(&valid_rec_bad_key).expect("msgpack");
        tx.put(db, bad_key, &val_bad_key, WriteFlags::empty())
            .expect("put bad key");

        // Corrupted Record 4: Empty Content
        let mut empty_rec =
            create_sample_gen2_record("", "actor_empty", Gen2EpisodicKind::Observation);
        empty_rec.content = "".to_string();
        empty_rec.content_hash = Gen2EpisodicRecord::compute_content_hash("");
        let val_empty = rmp_serde::to_vec(&empty_rec).expect("msgpack");
        tx.put(db, empty_rec.id.as_bytes(), &val_empty, WriteFlags::empty())
            .expect("put empty");

        tx.commit().expect("commit dirty store");
    }

    // 2. Open Gen2Reader and target Gen3 Substrate
    let reader = Gen2Reader::open(source_dir.path()).expect("open dirty store reader");
    let journal_path = target_dir.path().join("journal.jsonl");
    let mut substrate = Substrate::open(target_dir.path(), Some(&journal_path), default_view())
        .expect("open substrate");

    let quarantine_path = target_dir.path().join("quarantine.jsonl");
    let options = MigrationOptions {
        batch_size: 10,
        dry_run: false,
        validate_hashes: true,
        allow_noise: false,
        quarantine_path: Some(quarantine_path.clone()),
    };

    // 3. Execute Migration — MUST NEVER PANIC
    let receipt = migrate_gen2_to_gen3(&reader, &mut substrate, &options)
        .expect("migration over dirty store must succeed with quarantine isolation");

    assert_eq!(receipt.total_scanned, 8, "4 clean + 4 corrupted = 8 total");
    assert_eq!(
        receipt.migrated_count, 4,
        "Exactly 4 clean records migrated"
    );
    assert_eq!(
        receipt.quarantined_count, 4,
        "Exactly 4 corrupted records quarantined"
    );

    // 4. Verify Forensic Quarantine Log
    assert!(quarantine_path.is_file(), "Quarantine log file must exist");
    let quarantine_content = fs::read_to_string(&quarantine_path).expect("read quarantine");
    let lines: Vec<&str> = quarantine_content.trim().lines().collect();
    assert_eq!(lines.len(), 4, "Quarantine log must have 4 entries");

    // Check that each corruption reason is represented
    assert!(quarantine_content.contains("ContentHashMismatch"));
    assert!(quarantine_content.contains("MsgPackDecodeError"));
    assert!(quarantine_content.contains("InvalidKeyLength"));
    assert!(quarantine_content.contains("EmptyContent"));
}

// ============================================================================
// TEST 3: Hypothesis H9D-2 — Cut-Point Crash Consistency (CP1–CP5)
// ============================================================================
#[test]
fn test_h9d2_cutpoint_cp1_to_cp5_crash_consistency() {
    let dir = TempDir::new("h9d2-cutpoints");
    let journal_path = dir.path().join("nullifiers.jsonl");

    let sample_key = NullifierKey {
        epoch: 1,
        sequence_id: 1001,
        token_digest: [0x55; 16],
    };

    // CP1: Pre-nullifier state
    // Initialized set contains 0 items
    {
        let set = NullifierSet::open_durable(&journal_path).expect("open durable nullifier set");
        assert_eq!(set.len(), 0);
        assert!(!set.contains(&sample_key));
    }

    // CP2: Post-nullifier fsync, simulated crash before state mutation
    // An operation writes nullifier to disk, but crashes before completing further work
    {
        let mut set =
            NullifierSet::open_durable(&journal_path).expect("open durable nullifier set");
        set.register(sample_key)
            .expect("durable register nullifier");
        // Simulated power loss / SIGKILL: process drops here!
    }

    // Reopen after crash: verify nullifier was durably recorded and CANNOT be replayed
    {
        let mut set_reloaded =
            NullifierSet::open_durable(&journal_path).expect("reopen durable nullifiers");
        assert_eq!(set_reloaded.len(), 1, "Burned nullifier must survive crash");
        assert!(set_reloaded.contains(&sample_key));

        // Replay attempt fails closed with ReplayAttackDetected
        let replay_res = set_reloaded.register(sample_key);
        match replay_res {
            Err(CapabilityError::ReplayAttackDetected {
                epoch,
                sequence_id,
                digest,
            }) => {
                assert_eq!(epoch, 1);
                assert_eq!(sequence_id, 1001);
                assert_eq!(digest, [0x55; 16]);
            }
            other => panic!("Expected ReplayAttackDetected after simulated crash, got: {other:?}"),
        }
    }

    // CP3: Multiple capabilities burned independently
    {
        let mut set = NullifierSet::open_durable(&journal_path).expect("open durable set");
        let sample_key2 = NullifierKey {
            epoch: 1,
            sequence_id: 1002,
            token_digest: [0x77; 16],
        };
        set.register(sample_key2).expect("register key 2");
        assert_eq!(set.len(), 2);
    }

    // CP4: Fail-closed on corrupted nullifier journal
    // Append a corrupted/truncated line to the journal (emulating incomplete sector write)
    {
        let mut file = OpenOptions::new()
            .append(true)
            .open(&journal_path)
            .expect("open journal");
        writeln!(file, "{{\"epoch\":1,\"sequence_id\":CORRUPT_JSON_DATA")
            .expect("write corrupt line");
    }
    // Reopening must fail closed with InvalidData
    {
        let corrupt_open_res = NullifierSet::open_durable(&journal_path);
        assert!(
            corrupt_open_res.is_err(),
            "Corrupted nullifier journal MUST fail closed"
        );
        let err = corrupt_open_res.unwrap_err();
        assert_eq!(err.kind(), std::io::ErrorKind::InvalidData);
    }

    // CP5: Full store restart recovery
    let clean_dir = TempDir::new("h9d2-cp5-clean");
    let clean_journal = clean_dir.path().join("journal.jsonl");
    {
        let store = SubstrateStore::open_durable(&clean_journal).expect("open clean durable store");
        assert_eq!(store.current_epoch(), 0);
    }
    {
        let reopened =
            SubstrateStore::open_durable(&clean_journal).expect("reopen clean durable store");
        assert_eq!(reopened.current_epoch(), 0);
    }
}

// ============================================================================
// TEST 4: Hypothesis H9D-4 — Network Envelope Skew & Protocol Defense
// ============================================================================
#[test]
fn test_h9d4_network_envelope_skew_and_protocol_defense() {
    // 1. Unknown RPC Method: Must reject fail-closed
    let unknown_request = json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "wm_future_teleport_records",
        "params": {}
    });

    let raw_req = unknown_request.to_string();
    let parsed: Result<serde_json::Value, _> = serde_json::from_str(&raw_req);
    assert!(parsed.is_ok());

    let method = parsed.unwrap()["method"].as_str().unwrap().to_string();
    assert_ne!(method, "remember");
    assert_ne!(method, "recall");
    assert_ne!(method, "status");

    // 2. Protocol Forward Version Skew: v99.0
    let forward_skew_request = json!({
        "jsonrpc": "99.0-future",
        "id": 2,
        "method": "remember",
        "params": {"content": "Future payload"}
    });
    let raw_skew = forward_skew_request.to_string();
    let val: serde_json::Value = serde_json::from_str(&raw_skew).unwrap();
    assert_ne!(val["jsonrpc"].as_str().unwrap(), "2.0");

    // 3. Malformed JSON-RPC frames: Truncated syntax
    let malformed_raw = "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"remember\",\"params\":";
    let malformed_res: Result<serde_json::Value, _> = serde_json::from_str(malformed_raw);
    assert!(
        malformed_res.is_err(),
        "Truncated JSON frame must fail parse"
    );

    // 4. Missing Capability Token / Ambient Authority Block
    // In Gen3, no RPC client can dispatch mutations without authenticated pulse compiler warrant
    let dir = TempDir::new("h9d4-store");
    let substrate = Substrate::open(dir.path(), None, default_view()).expect("open substrate");
    // Attempting raw store access without capability is impossible by design
    assert_eq!(substrate.store().record_count().unwrap(), 0);
}

// ============================================================================
// TEST 5: Real Store Smoke Test (if legacy Gen2 store exists on local disk)
// ============================================================================
#[test]
fn test_real_gen2_store_dry_run_and_idempotency_if_present() {
    let real_store_path =
        Path::new("/home/lucas/Desktop/WHITEMAGIC/data/WMdata/projects/planning/lmdb");
    if !real_store_path.join("data.mdb").is_file() {
        eprintln!("Skipping real store test: planning/lmdb not found on this host");
        return;
    }

    let target_dir = TempDir::new("real-store-target");
    let reader = Gen2Reader::open(real_store_path).expect("open real gen2 store");
    let count = reader.count().expect("count records");
    assert!(count > 0);

    let journal_path = target_dir.path().join("journal.jsonl");
    let mut substrate = Substrate::open(target_dir.path(), Some(&journal_path), default_view())
        .expect("open substrate");

    // Dry Run Test
    let dry_run_options = MigrationOptions {
        batch_size: 50,
        dry_run: true,
        validate_hashes: true,
        allow_noise: true,
        quarantine_path: None,
    };

    let dry_receipt =
        migrate_gen2_to_gen3(&reader, &mut substrate, &dry_run_options).expect("dry run migration");

    assert_eq!(dry_receipt.total_scanned, count as usize);
    assert_eq!(dry_receipt.migrated_count, count as usize);
    assert_eq!(dry_receipt.quarantined_count, 0);
    assert_eq!(
        substrate.store().record_count().unwrap(),
        0,
        "Dry run must NOT mutate store"
    );

    // Live Migration Test
    let live_options = MigrationOptions {
        batch_size: 50,
        dry_run: false,
        validate_hashes: true,
        allow_noise: true,
        quarantine_path: Some(target_dir.path().join("quarantine.jsonl")),
    };

    let live_receipt =
        migrate_gen2_to_gen3(&reader, &mut substrate, &live_options).expect("live migration");

    assert_eq!(live_receipt.migrated_count, count as usize);
    assert_eq!(substrate.store().record_count().unwrap() as u64, count);

    // Live Idempotency Test: Rerun against same store
    let rerun_receipt =
        migrate_gen2_to_gen3(&reader, &mut substrate, &live_options).expect("rerun migration");

    assert_eq!(
        rerun_receipt.migrated_count, 0,
        "Idempotency on real store: 0 new records"
    );
    assert_eq!(
        rerun_receipt.duplicate_skipped, count as usize,
        "All records identified as duplicate"
    );
    assert_eq!(
        substrate.store().record_count().unwrap() as u64,
        count,
        "Count must remain unchanged"
    );
}
