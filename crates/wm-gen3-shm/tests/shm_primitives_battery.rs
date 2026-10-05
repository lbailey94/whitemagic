//! Comprehensive test battery for WhiteMagic Gen3 POSIX Shared Memory Substrate.
//!
//! Validates:
//! 1. Memory topology and page-aligned superblock formatting.
//! 2. High-velocity lock-free MPMC ring queue operations (single and multi-thread).
//! 3. Linda associative tuple operations (out, in, rd).
//! 4. Digital stigmergic pheromone conflict detection and decay.
//! 5. Named SHM cross-instance synchronization and unlinking.

use std::sync::Arc;
use std::sync::atomic::Ordering;
use std::thread;
use uuid::Uuid;
use wm_gen3_shm::*;

#[test]
fn test_anonymous_substrate_initialization() {
    let substrate = ShmSubstrate::anonymous().expect("Failed to create anonymous substrate");
    let sb = substrate.superblock();

    assert_eq!(sb.magic, SHM_MAGIC);
    assert_eq!(sb.version, SHM_VERSION);
    assert_eq!(sb.flags, 1);
    assert_eq!(sb.epoch.load(Ordering::Relaxed), 1);
    assert_eq!(sb.total_size, SHM_TOTAL_SIZE as u64);

    assert_eq!(sb.heartbeat_offset, HEARTBEAT_OFFSET as u64);
    assert_eq!(sb.ring_offsets[0], RING_0_OFFSET as u64);
    assert_eq!(sb.ring_offsets[1], RING_1_OFFSET as u64);
    assert_eq!(sb.ring_offsets[2], RING_2_OFFSET as u64);
    assert_eq!(sb.ring_offsets[3], RING_3_OFFSET as u64);
    assert_eq!(sb.tuple_table_offset, TUPLE_TABLE_OFFSET as u64);
    assert_eq!(sb.stigmergy_offset, STIGMERGY_OFFSET as u64);
    assert_eq!(sb.arena_offset, ARENA_OFFSET as u64);

    assert_eq!(substrate.heartbeats().len(), MAX_WORKERS);
}

#[test]
fn test_mpmc_ring_single_thread_push_pop() {
    let substrate = ShmSubstrate::anonymous().expect("Substrate");
    let ring = substrate.ring(0).expect("Ring 0");

    let messages = ["alpha", "beta", "gamma", "delta", "epsilon"];
    for (i, msg) in messages.iter().enumerate() {
        ring.push(msg.as_bytes(), i as u32).expect("Push failed");
    }

    let mut buf = [0u8; 64];
    for (i, expected_msg) in messages.iter().enumerate() {
        let (len, flags) = ring
            .pop(&mut buf)
            .expect("Pop failed")
            .expect("Item exists");
        assert_eq!(&buf[..len], expected_msg.as_bytes());
        assert_eq!(flags, i as u32);
    }

    // Queue is now empty
    let empty_res = ring.pop(&mut buf).expect("Pop on empty");
    assert!(empty_res.is_none());
}

#[test]
fn test_mpmc_ring_concurrent_producers_consumers() {
    let substrate = Arc::new(ShmSubstrate::anonymous().expect("Substrate"));
    let items_per_producer = 250usize;
    let num_producers = 4usize;
    let num_consumers = 4usize;
    let total_items = items_per_producer * num_producers;

    let mut prod_handles = Vec::new();
    for p in 0..num_producers {
        let sub = Arc::clone(&substrate);
        prod_handles.push(thread::spawn(move || {
            let ring = sub.ring(1).expect("Ring 1");
            for i in 0..items_per_producer {
                let val = (p * 10000 + i) as u64;
                let bytes = val.to_le_bytes();
                while ring.push(&bytes, p as u32).is_err() {
                    thread::yield_now();
                }
            }
        }));
    }

    let received = Arc::new(std::sync::atomic::AtomicUsize::new(0));
    let mut cons_handles = Vec::new();
    for _ in 0..num_consumers {
        let sub = Arc::clone(&substrate);
        let rec = Arc::clone(&received);
        cons_handles.push(thread::spawn(move || {
            let ring = sub.ring(1).expect("Ring 1");
            let mut buf = [0u8; 16];
            loop {
                if let Ok(Some((len, _flags))) = ring.pop(&mut buf) {
                    assert_eq!(len, 8);
                    let count = rec.fetch_add(1, Ordering::Relaxed);
                    if count + 1 >= total_items {
                        break;
                    }
                } else {
                    if rec.load(Ordering::Relaxed) >= total_items {
                        break;
                    }
                    thread::yield_now();
                }
            }
        }));
    }

    for h in prod_handles {
        h.join().unwrap();
    }
    for h in cons_handles {
        h.join().unwrap();
    }

    assert_eq!(received.load(Ordering::Relaxed), total_items);
}

#[test]
fn test_linda_tuple_operations() {
    let substrate = Arc::new(ShmSubstrate::anonymous().expect("Substrate"));
    let space = ShmTupleSpace::new(substrate);

    let t1 = RawTuple {
        id: Uuid::new_v4(),
        kind_discriminator: 1, // Claim
        resource_hash: 0x12345678,
        holder_issuer_hash: 0xABCD,
        resource_path: "/src/core/mod.rs".to_string(),
        tag: "claim:exclusive".to_string(),
        payload: b"claim payload data".to_vec(),
        created_at_ms: 1000,
        expires_at_ms: 5000,
        landlock_token: [0u8; 32],
        capability_mask: 0x07,
    };

    let t2 = RawTuple {
        id: Uuid::new_v4(),
        kind_discriminator: 2, // Task
        resource_hash: 0x87654321,
        holder_issuer_hash: 0xDCBA,
        resource_path: "/src/net/port.rs".to_string(),
        tag: "task:dispatch".to_string(),
        payload: b"task specification".to_vec(),
        created_at_ms: 1000,
        expires_at_ms: 0,
        landlock_token: [1u8; 32],
        capability_mask: 0x01,
    };

    // 1. Out
    space.out(&t1).expect("Out t1");
    space.out(&t2).expect("Out t2");

    // 2. Read matching without taking (rd)
    let claims = space.rd_matching(Some(1), None, 10, 1500);
    assert_eq!(claims.len(), 1);
    assert_eq!(claims[0].id, t1.id);
    assert_eq!(claims[0].resource_path, "/src/core/mod.rs");
    assert_eq!(claims[0].payload, b"claim payload data");

    // 3. Take matching (in)
    let taken = space
        .in_matching(Some(2), Some(0x87654321), 1500)
        .expect("In t2");
    assert_eq!(taken.id, t2.id);
    assert_eq!(taken.resource_path, "/src/net/port.rs");

    // 4. Verify taken tuple is no longer present
    let taken_again = space.in_matching(Some(2), Some(0x87654321), 1500);
    assert!(taken_again.is_none());

    // 5. Verify t1 still present and takes it
    let taken_t1 = space.in_matching(Some(1), None, 1500).expect("In t1");
    assert_eq!(taken_t1.id, t1.id);

    let empty = space.in_matching(None, None, 1500);
    assert!(empty.is_none());
}

#[test]
fn test_stigmergy_conflict_detection_and_decay() {
    let substrate = Arc::new(ShmSubstrate::anonymous().expect("Substrate"));
    let field = ShmStigmergyField::new(substrate);

    let p1 = RawPheromone {
        id: Uuid::new_v4(),
        kind: 0, // MutationActive
        target_path: "crates/wm-gen3-core/src/lib.rs".to_string(),
        ast_scope: "fn:do_exec".to_string(),
        line_start: 50,
        line_end: 100,
        initial_intensity: 1.0,
        half_life_ms: 1000,
        emitted_at_ms: 10_000,
        issuer: "subagent-alpha".to_string(),
    };

    field.emit(&p1).expect("Emit p1");

    // 1. Conflict on overlapping range (lines 60..70) at t=10_000
    let conflicts =
        field.sense_conflicts("crates/wm-gen3-core/src/lib.rs", 60, 70, 0.5, 10_000, None);
    assert_eq!(conflicts.len(), 1);
    assert_eq!(conflicts[0].active_issuer, "subagent-alpha");
    assert!((conflicts[0].intensity - 1.0).abs() < 1e-4);

    // 2. No conflict on disjoint range (lines 120..150)
    let no_conflicts = field.sense_conflicts(
        "crates/wm-gen3-core/src/lib.rs",
        120,
        150,
        0.5,
        10_000,
        None,
    );
    assert!(no_conflicts.is_empty());

    // 3. Ignore self issuer
    let ignored = field.sense_conflicts(
        "crates/wm-gen3-core/src/lib.rs",
        60,
        70,
        0.5,
        10_000,
        Some("subagent-alpha"),
    );
    assert!(ignored.is_empty());

    // 4. Decay after 1 half-life (1000ms later -> t=11_000)
    let half_decay =
        field.sense_conflicts("crates/wm-gen3-core/src/lib.rs", 60, 70, 0.1, 11_000, None);
    assert_eq!(half_decay.len(), 1);
    assert!((half_decay[0].intensity - 0.5).abs() < 1e-3);

    // 5. Evaporate when intensity below 0.2 (at t=14_000 -> 4 half-lives -> intensity = 0.0625)
    let purged = field.evaporate(14_000, 0.2);
    assert_eq!(purged, 1);

    let after_evap =
        field.sense_conflicts("crates/wm-gen3-core/src/lib.rs", 60, 70, 0.01, 14_000, None);
    assert!(after_evap.is_empty());
}

#[test]
fn test_named_shm_create_and_attach() {
    let test_name = format!("/wm_t_{}", &Uuid::new_v4().simple().to_string()[..8]);

    // 1. Creator creates named segment
    let creator = ShmSubstrate::open_or_create(&test_name).expect("Create named");
    assert!(creator.is_owner());

    // Write a tuple into creator's space
    let space1 = ShmTupleSpace::new(Arc::new(creator));
    let t = RawTuple {
        id: Uuid::new_v4(),
        kind_discriminator: 42,
        resource_hash: 9999,
        holder_issuer_hash: 8888,
        resource_path: "/test/path".to_string(),
        tag: "tag:sync".to_string(),
        payload: b"cross-process synchronization".to_vec(),
        created_at_ms: 100,
        expires_at_ms: 0,
        landlock_token: [0u8; 32],
        capability_mask: 0xFF,
    };
    space1.out(&t).expect("Out tuple in creator");

    // 2. Attacher attaches to the same named segment
    let attacher = ShmSubstrate::open_or_create(&test_name).expect("Attach named");
    assert!(!attacher.is_owner());
    assert_eq!(attacher.superblock().magic, SHM_MAGIC);

    let space2 = ShmTupleSpace::new(Arc::new(attacher));
    let matching = space2.rd_matching(Some(42), Some(9999), 1, 100);
    assert_eq!(matching.len(), 1);
    assert_eq!(matching[0].id, t.id);
    assert_eq!(matching[0].payload, b"cross-process synchronization");

    // Cleanup: unlink segment
    let mut cleaner = ShmSubstrate::open_or_create(&test_name).expect("Cleaner");
    cleaner.unlink().expect("Unlink test segment");
}

#[test]
fn test_portable_shm_name_validation() {
    let too_long = format!("/wm_{}", "a".repeat(32));
    let err = ShmSubstrate::open_or_create(&too_long)
        .err()
        .expect("long name refused");
    assert_eq!(err.kind(), std::io::ErrorKind::InvalidInput);
    assert!(err.to_string().contains("portable limit"), "{err}");

    let interior = ShmSubstrate::open_or_create("/wm/a")
        .err()
        .expect("interior slash refused");
    assert_eq!(interior.kind(), std::io::ErrorKind::InvalidInput);

    let empty = ShmSubstrate::open_or_create("/")
        .err()
        .expect("empty name refused");
    assert_eq!(empty.kind(), std::io::ErrorKind::InvalidInput);
}
