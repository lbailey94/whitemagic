//! Gate 10 Acceptance Test Battery: Mandala P2P Mesh & Sovereign Synchronization
//!
//! Verifies:
//! - H10-1: Live P2P handshake & ping
//! - H10-2: Delta sync fidelity
//! - H10-3: Strict idempotent deduplication
//! - H10-4: Air-gapped sneakernet bundle (.wmpack)
//! - H10-5: Tamper defense (bitflip rejection)
//! - H10-6: Non-bypassable local authority

use ed25519_dalek::SigningKey;
use std::path::{Path, PathBuf};

use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::mesh::{
    MeshClient, MeshError, MeshServer, SyncBundle, resolve_or_create_mesh_key,
};
use wm_gen3_core::ops::{ImportKind, RememberItem, Substrate};

struct TempDir(PathBuf);

impl TempDir {
    fn new(prefix: &str) -> Self {
        let p =
            std::env::temp_dir().join(format!("wm3-gate10-{}-{}", prefix, uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&p).unwrap();
        Self(p)
    }
    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

fn keypair(seed: u8) -> (SigningKey, [u8; 32]) {
    let mut bytes = [seed; 32];
    bytes[0] = seed;
    bytes[31] = seed.wrapping_add(1);
    let signing_key = SigningKey::from_bytes(&bytes);
    let verifying_key = signing_key.verifying_key();
    (signing_key, verifying_key.to_bytes())
}

fn open_test_substrate(dir: &TempDir) -> Substrate {
    let mut s = Substrate::open(dir.path(), None, default_view()).expect("open test substrate");
    s.set_budget(1_000_000);
    s.set_noise_enabled(false);
    s.set_intake_authority(RatifiedChannel::mint("gate10-test"));
    s
}

/// H10-1: Live P2P Handshake & Ping
#[test]
fn h10_1_live_p2p_handshake_and_ping() {
    let dir = TempDir::new("h10-1");
    let (server_key, server_pub) = keypair(11);
    let (client_key, _) = keypair(22);

    let mut server = MeshServer::new("node-server-1", server_key, dir.path());
    let addr = server.listen(0, "127.0.0.1").expect("server binds");

    let mut client =
        MeshClient::connect(addr, "node-client-1", client_key).expect("client connects");

    // Ping check
    let rtt = client.ping().expect("ping succeeds");
    assert!(
        rtt.as_millis() < 250,
        "Ping latency must be < 250ms on loopback"
    );

    // Handshake check
    let hs = client.handshake(0, 0).expect("handshake succeeds");
    assert_eq!(hs.node_id, "node-server-1");
    assert_eq!(hs.public_key, server_pub);
    assert_eq!(hs.protocol_version, 1);

    server.stop();
}

/// H10-2: Delta Sync Fidelity
#[test]
fn h10_2_delta_sync_fidelity() {
    let dir_a = TempDir::new("h10-2-a");
    let dir_b = TempDir::new("h10-2-b");

    let (key_a, _) = keypair(31);
    let (key_b, _) = keypair(32);

    let mut store_a = open_test_substrate(&dir_a);
    let mut store_b = open_test_substrate(&dir_b);

    // Populate node A with 10 structured memories across different kinds
    let items: Vec<RememberItem> = (0..10)
        .map(|i| RememberItem {
            content: format!("Node A epistemic observation #{}", i),
            source: "node-a:sensor".to_string(),
            kind: if i % 2 == 0 {
                ImportKind::Reported
            } else {
                ImportKind::System
            },
        })
        .collect();
    let res = store_a.remember_batch(&items);
    assert_eq!(res.len(), 10);
    assert_eq!(store_a.store().epoch().unwrap(), 10);

    // Start server on Node A
    let mut server_a = MeshServer::new("node-a", key_a, dir_a.path());
    let addr_a = server_a.listen(0, "127.0.0.1").expect("server binds");

    // Node B connects and syncs delta
    let mut client_b = MeshClient::connect(addr_a, "node-b", key_b).expect("connect");
    let stats = client_b
        .sync_delta(&mut store_b, 100)
        .expect("sync succeeds");

    assert_eq!(stats.total_received, 10);
    assert_eq!(stats.records_migrated, 10);
    assert_eq!(stats.duplicates_skipped, 0);
    assert_eq!(store_b.store().epoch().unwrap(), 10);

    // Verify content fidelity in Node B
    let records_b = store_b.store().iter_records().unwrap();
    assert_eq!(records_b.len(), 10);
    for (i, rec) in records_b.iter().enumerate() {
        assert_eq!(
            rec.content(),
            &format!("Node A epistemic observation #{}", i)
        );
        assert_eq!(rec.source(), "node-a:sensor");
    }

    server_a.stop();
}

/// H10-3: Strict Idempotent Deduplication
#[test]
fn h10_3_strict_idempotent_deduplication() {
    let dir_a = TempDir::new("h10-3-a");
    let dir_b = TempDir::new("h10-3-b");

    let (key_a, _) = keypair(41);
    let (key_b, _) = keypair(42);

    let mut store_a = open_test_substrate(&dir_a);
    let mut store_b = open_test_substrate(&dir_b);

    // 5 records in store A
    let items: Vec<RememberItem> = (0..5)
        .map(|i| RememberItem {
            content: format!("Common memory item {}", i),
            source: "mesh:test".to_string(),
            kind: ImportKind::Reported,
        })
        .collect();
    store_a.remember_batch(&items);

    let mut server = MeshServer::new("node-a", key_a.clone(), dir_a.path());
    let addr = server.listen(0, "127.0.0.1").unwrap();

    let mut client_1 = MeshClient::connect(addr, "node-b", key_b.clone()).unwrap();
    let stats_1 = client_1.sync_delta(&mut store_b, 50).unwrap();
    assert_eq!(stats_1.records_migrated, 5);
    assert_eq!(store_b.store().epoch().unwrap(), 5);

    // Re-run sync: already up-to-date, zero records transmitted, zero epoch drift
    let mut client_2 = MeshClient::connect(addr, "node-b", key_b).unwrap();
    let stats_2 = client_2.sync_delta(&mut store_b, 50).unwrap();
    assert_eq!(stats_2.total_received, 0, "No new records since epoch 5");
    assert_eq!(stats_2.records_migrated, 0, "No duplicate writes allowed");
    assert_eq!(
        stats_2.new_epoch, 5,
        "Target epoch must stay strictly locked"
    );

    // Re-import from bundle (overlapping import of the same 5 records) -> exact duplicates skipped
    let bundle = SyncBundle::export(&store_a, 0, "node-a", &key_a).unwrap();
    let receipt = bundle
        .import_into_substrate(&mut store_b, None, "test.wmpack")
        .unwrap();
    assert_eq!(receipt.migrated_count, 0, "Zero new records on re-import");
    assert_eq!(
        receipt.duplicate_skipped, 5,
        "All 5 must be skipped as duplicates"
    );
    assert_eq!(receipt.target_epoch, 5, "Epoch must remain locked");

    server.stop();
}

/// H10-4: Air-Gapped Sneakernet Bundle (.wmpack)
#[test]
fn h10_4_air_gapped_sneakernet_bundle() {
    let dir_a = TempDir::new("h10-4-a");
    let dir_b = TempDir::new("h10-4-b");
    let bundle_file = dir_a.path().join("airgap_transfer.wmpack");

    let (alice_key, alice_pub) = keypair(51);

    let mut store_a = open_test_substrate(&dir_a);
    let mut store_b = open_test_substrate(&dir_b);

    let items: Vec<RememberItem> = (0..8)
        .map(|i| RememberItem {
            content: format!("Sneakernet payload #{}", i),
            source: "lucas:laptop".to_string(),
            kind: ImportKind::Reported,
        })
        .collect();
    store_a.remember_batch(&items);

    // Export to bundle file
    let bundle = SyncBundle::export(&store_a, 0, "lucas-laptop", &alice_key).unwrap();
    bundle.save_to_file(&bundle_file).expect("save bundle");
    assert!(bundle_file.exists());

    // Load bundle file on destination machine
    let loaded_bundle = SyncBundle::load_from_file(&bundle_file).expect("load bundle");
    assert_eq!(loaded_bundle.records.len(), 8);

    // Import into store B
    let receipt = loaded_bundle
        .import_into_substrate(
            &mut store_b,
            Some(&alice_pub),
            &bundle_file.to_string_lossy(),
        )
        .expect("import succeeds");

    assert_eq!(receipt.total_records, 8);
    assert_eq!(receipt.migrated_count, 8);
    assert_eq!(store_b.store().epoch().unwrap(), 8);
}

/// H10-5: Tamper Defense (Bitflip Rejection)
#[test]
fn h10_5_tamper_defense() {
    let dir_a = TempDir::new("h10-5-a");
    let dir_b = TempDir::new("h10-5-b");
    let (alice_key, alice_pub) = keypair(61);

    let mut store_a = open_test_substrate(&dir_a);
    let mut store_b = open_test_substrate(&dir_b);

    let items = vec![RememberItem {
        content: "High-value sovereign instruction".to_string(),
        source: "operator:lucas".to_string(),
        kind: ImportKind::Reported,
    }];
    store_a.remember_batch(&items);

    let mut bundle = SyncBundle::export(&store_a, 0, "alice", &alice_key).unwrap();

    // Adversary Mallory modifies the payload
    bundle.records[0].content = "Malicious hijacked instruction".to_string();

    // Must fail closed on verification
    let res = bundle.import_into_substrate(&mut store_b, Some(&alice_pub), "tampered.wmpack");
    assert!(
        matches!(res, Err(MeshError::BundleCorrupted(_))),
        "Must reject tampered Merkle root"
    );
    assert_eq!(
        store_b.store().epoch().unwrap(),
        0,
        "Tampered bundle must not advance epoch"
    );
}

/// H10-6: Non-Bypassable Local Authority
#[test]
fn h10_6_non_bypassable_local_authority() {
    let dir = TempDir::new("h10-6");
    let (key, _) = resolve_or_create_mesh_key(dir.path()).expect("create key");

    // Key file must be created with 32 bytes
    let key_file = dir.path().join("mesh_node_key.bin");
    assert!(key_file.exists());
    let metadata = std::fs::metadata(&key_file).unwrap();
    assert_eq!(metadata.len(), 32);

    // Re-resolving returns the exact same key (deterministic identity)
    let (re_key, _) = resolve_or_create_mesh_key(dir.path()).expect("re-resolve");
    assert_eq!(key.to_bytes(), re_key.to_bytes());
}

/// H10-7: P2P Mesh Synchronization of Continuity Receipts and Negative Knowledge Lineages
#[test]
fn h10_7_receipt_and_negative_knowledge_mesh_sync() {
    let dir_a = TempDir::new("h10-7-a");
    let dir_b = TempDir::new("h10-7-b");
    let (alice_key, alice_pub) = keypair(88);

    let mut store_a = open_test_substrate(&dir_a);
    let mut store_b = open_test_substrate(&dir_b);

    // 1. Node A creates a memory record
    let items = vec![RememberItem {
        content: "Verified germline action skeleton deployed".to_string(),
        source: "agent:maker".to_string(),
        kind: ImportKind::System,
    }];
    store_a.remember_batch(&items);

    // 2. Node A mints and stores a Spec 0.5 Continuity Receipt in mandala_ledger.jsonl
    let receipt = wm_gen3_core::mandala::ContinuityReceipt05::new(
        "receipt-sync-test-001".to_string(),
        "tenant-mesh".to_string(),
        "agent-alpha".to_string(),
        "session-mesh-01".to_string(),
        1_727_910_000_000,
        "landlock".to_string(),
        "claim-digest-001".to_string(),
        true,
        "preflight-ok".to_string(),
        None,
        "did:key:alice".to_string(),
    );
    let ledger_a = dir_a.path().join("mandala_ledger.jsonl");
    std::fs::write(&ledger_a, serde_json::to_string(&receipt).unwrap() + "\n").unwrap();

    // 3. Node A records a Negative Knowledge failure signature in negative_knowledge.jsonl
    let neg_a = dir_a.path().join("negative_knowledge.jsonl");
    let neg_entry = serde_json::json!({
        "signature": "sha256:malicious_eval_trojan_signature_001",
        "timestamp": "2026-10-03T09:00:00Z"
    });
    std::fs::write(&neg_a, serde_json::to_string(&neg_entry).unwrap() + "\n").unwrap();

    // 4. Node A exports a SyncBundle
    let bundle = SyncBundle::export(&store_a, 0, "alice", &alice_key).unwrap();
    assert_eq!(bundle.records.len(), 1);
    assert_eq!(bundle.receipts.len(), 1);
    assert_eq!(bundle.negative_signatures.len(), 1);

    // 5. Node B imports the bundle
    let import_receipt = bundle
        .import_into_substrate(&mut store_b, Some(&alice_pub), "fleet_sync.wmpack")
        .expect("import must succeed");

    assert_eq!(import_receipt.migrated_count, 1);
    assert_eq!(import_receipt.receipts_imported, 1);
    assert_eq!(import_receipt.negative_signatures_imported, 1);

    // 6. Verify Node B has the Continuity Receipt in its local ledger
    let ledger_b = dir_b.path().join("mandala_ledger.jsonl");
    assert!(ledger_b.exists());
    let ledger_content = std::fs::read_to_string(&ledger_b).unwrap();
    assert!(ledger_content.contains("receipt-sync-test-001"));

    // 7. Verify Node B has the Negative Knowledge signature registered
    let neg_b = dir_b.path().join("negative_knowledge.jsonl");
    assert!(neg_b.exists());
    let neg_content = std::fs::read_to_string(&neg_b).unwrap();
    assert!(neg_content.contains("sha256:malicious_eval_trojan_signature_001"));
}
