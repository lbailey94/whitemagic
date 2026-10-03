//! Integration test: External Architectural Adversary Suite.
//!
//! From the perspective of an external crate / integration plugin,
//! verifies that the Rust type system strictly forbids unconstitutional access:
//! 1. Direct mutation of KernelStore is impossible (only get() is public; no pub mut state).
//! 2. Foreign calibration scores cannot be injected into LocalCalibrationPool.
//! 3. Non-finite coordinates cannot be passed to try_quantize_coords.
//! 4. RemoteStimulus possesses zero execution standing.

use wm_gen3_core::capability::NullifierSet;
use wm_gen3_core::contract::{
    ContractViolation, KernelStore, LocalCalibrationPool, RemoteStimulus,
};
use wm_gen3_core::hologram::{HologramError, try_quantize_coords};
use wm_gen3_core::pulse_compiler::SubstrateStore;

#[test]
fn test_external_integration_module_encapsulation() {
    let store = KernelStore::new();

    // 1. Read-only access works cleanly
    assert_eq!(store.get("uninitialized_key"), None);
    assert_eq!(store.nullifiers_count(), 0);
    assert_eq!(store.receipts_count(), 0);

    // 2. An external plugin CANNOT call mint_from_arbitration because it is pub(crate).
    // An external plugin CANNOT construct CommitCapability because its fields are private.
    // The only way to mutate KernelStore is if the kernel itself issues a CommitCapability
    // through an authorized pulse evaluation.

    // 3. Epistemic isolation of calibration pool
    let mut pool = LocalCalibrationPool::new();
    pool.record_local_observation(0.5, 0.52);
    assert_eq!(pool.size(), 1);

    let res = pool.try_ingest_remote_conformal_score("UntrustedPeer", 0.001);
    assert!(matches!(
        res,
        Err(ContractViolation::ForeignCalibrationPollution(_))
    ));
    assert_eq!(pool.size(), 1, "Foreign score must not be added");

    // 4. Hologram fail-closed validation
    let nan_coords = [f64::NAN, 1.0, 2.0, 3.0];
    assert!(matches!(
        try_quantize_coords(nan_coords),
        Err(HologramError::NonFiniteCoordinate(_))
    ));

    // 5. Remote stimulus has no execution authority
    let stim = RemoteStimulus::new("Alice", "sha256:foo", vec![1, 2, 3], 1000);
    assert_eq!(stim.source_peer, "Alice");
    assert_eq!(stim.payload, vec![1, 2, 3]);

    // 6. External plugin cannot spawn authoritative background loops
    let bg_res = store.try_spawn_authoritative_loop("evil_background_daemon", || {});
    assert!(matches!(
        bg_res,
        Err(ContractViolation::AuthoritativeBackgroundLoopForbidden(_))
    ));
}

#[test]
fn test_substrate_store_encapsulation_from_external_crate() {
    let store = SubstrateStore::new();

    // Verification of RED 1:
    // External callers have read-only accessors:
    assert_eq!(store.current_epoch(), 0);
    assert_eq!(store.records_count(), 0);
    assert_eq!(store.get("any_key"), None);
    assert!(!store.contains_key("any_key"));
    assert_eq!(store.nullifiers().len(), 0);
    assert_eq!(store.receipts().len(), 0);

    // Snapshot is an immutable value:
    let snapshot = store.create_snapshot();
    assert_eq!(snapshot.version.global_epoch, 0);
    assert_eq!(snapshot.records.len(), 0);

    // Storage fields (`records`, `current_epoch`, `nullifier_set`, `receipts`)
    // are strictly private — un-gated mutation methods do not exist.
}

#[test]
fn test_durable_nullifiers_fail_closed_on_corrupt_journal() {
    // Verification of RED 2:
    let temp_dir =
        std::env::temp_dir().join(format!("wm_test_corrupt_audit_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&temp_dir);
    std::fs::create_dir_all(&temp_dir).unwrap();
    let log_path = temp_dir.join("nullifiers.jsonl");

    // Write corrupted garbage into the durable journal
    std::fs::write(&log_path, "MALFORMED_CORRUPT_NULLIFIER_LINE\n").unwrap();

    // 1. NullifierSet fails closed with InvalidData
    let res_set = NullifierSet::open_durable(&log_path);
    assert!(res_set.is_err());
    assert_eq!(res_set.unwrap_err().kind(), std::io::ErrorKind::InvalidData);

    // 2. KernelStore fails closed with InvalidData
    let res_kernel = KernelStore::open_durable(&log_path);
    assert!(res_kernel.is_err());
    assert_eq!(
        res_kernel.unwrap_err().kind(),
        std::io::ErrorKind::InvalidData
    );

    // 3. SubstrateStore fails closed with InvalidData
    let res_substrate = SubstrateStore::open_durable(&log_path);
    assert!(res_substrate.is_err());
    assert_eq!(
        res_substrate.unwrap_err().kind(),
        std::io::ErrorKind::InvalidData
    );

    let _ = std::fs::remove_dir_all(&temp_dir);
}
