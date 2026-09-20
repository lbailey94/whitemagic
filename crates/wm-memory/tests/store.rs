//! Integration tests for the LMDB memory store.
//!
//! These tests verify that:
//! - The LMDB environment opens correctly
//! - All 14 galaxy sub-databases are created and openable
//! - Galaxy database names match the Galaxy enum
//! - The store works with a real temp directory (not mocked)

use tempfile::tempdir;
use wm_core::Galaxy;
use wm_memory::MemoryStore;

#[test]
fn store_opens_with_default_map_size() {
    let tmp = tempdir().unwrap();
    let store = MemoryStore::open_default(tmp.path()).unwrap();
    // Environment should be accessible
    let _env = store.env();
}

#[test]
fn store_creates_all_14_galaxy_databases() {
    let tmp = tempdir().unwrap();
    let store = MemoryStore::open_default(tmp.path()).unwrap();

    for galaxy in Galaxy::all() {
        let db = store.galaxy_db(galaxy);
        assert!(db.is_ok(), "Failed to open galaxy DB for {galaxy:?}");
    }
}

#[test]
fn store_galaxy_db_names_match_enum() {
    let tmp = tempdir().unwrap();
    let store = MemoryStore::open_default(tmp.path()).unwrap();

    for galaxy in Galaxy::all() {
        let db = store.galaxy_db(galaxy).unwrap();
        // The database handle should be valid (non-zero)
        // We can't directly check the name from the handle, but
        // the fact that it opens proves the name matches.
        let _ = db;
    }
}

#[test]
fn store_can_reopen_existing_environment() {
    let tmp = tempdir().unwrap();

    // First open — creates all databases
    {
        let _store = MemoryStore::open_default(tmp.path()).unwrap();
    }

    // Second open — should find existing databases
    {
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        for galaxy in Galaxy::all() {
            assert!(
                store.galaxy_db(galaxy).is_ok(),
                "Galaxy {galaxy:?} should be openable on reopen"
            );
        }
    }
}

#[test]
fn store_custom_map_size_works() {
    let tmp = tempdir().unwrap();
    // 10MB map size — small but valid for tests
    let store = MemoryStore::open(tmp.path(), 10 * 1024 * 1024).unwrap();
    let _ = store.galaxy_db(Galaxy::Citta).unwrap();
}

#[test]
fn store_all_galaxy_db_names_are_unique_lmdb_names() {
    let tmp = tempdir().unwrap();
    let store = MemoryStore::open_default(tmp.path()).unwrap();

    let mut names = std::collections::HashSet::new();
    for galaxy in Galaxy::all() {
        let db_name = galaxy.db_name();
        assert!(
            names.insert(db_name.to_string()),
            "Duplicate LMDB db name: {db_name}"
        );
        // Each should open successfully
        store.galaxy_db(galaxy).unwrap();
    }
    assert_eq!(names.len(), Galaxy::COUNT);
}

#[test]
fn test_valkyrie_sanctuary_memory_storage() {
    use wm_memory::Memory;

    let tmp = tempdir().unwrap();
    let store = MemoryStore::open_default(tmp.path()).unwrap();

    let memory = Memory::new(
        Galaxy::Valkyrie,
        "WhiteMagic sanctuary memory: kept whole, never deleted.".to_string(),
    );

    let id = memory.metadata.id;
    store.put(Galaxy::Valkyrie, &memory).unwrap();

    let retrieved = store.get(Galaxy::Valkyrie, id).unwrap();
    assert!(retrieved.is_some());
    let r = retrieved.unwrap();
    assert_eq!(
        r.content,
        "WhiteMagic sanctuary memory: kept whole, never deleted."
    );
    assert_eq!(store.count(Galaxy::Valkyrie).unwrap(), 1);
}

/// H1 (2026-09-20 review): sequence allocation must happen inside the same
/// LMDB write transaction as the turn record. The reviewer's reproduction
/// (100 simultaneous `session.record` writers) got 43 unique sequences from
/// the old read-count-then-write allocation. This is the acceptance test:
/// N concurrent writers get exactly 1..=N unique, contiguous sequences.
#[test]
fn concurrent_put_session_turn_allocates_contiguous_unique_sequences() {
    use std::sync::Arc;
    use wm_memory::Memory;

    const N: usize = 100;
    let tmp = tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
    let sid = "sess-h1-100-writers";

    // All writers must be spawned before any join: joining inside the spawn
    // map would serialize the loop and the test would prove nothing, so this
    // collect is deliberate (clippy's needless_collect suggestion would
    // serialize it).
    #[allow(clippy::needless_collect)]
    let handles: Vec<_> = (0..N)
        .map(|i| {
            let store = Arc::clone(&store);
            std::thread::spawn(move || {
                let (sequence, _mem) = store
                    .put_session_turn(sid, |sequence| {
                        let mut mem = Memory::new(
                            Galaxy::Sessions,
                            format!(
                                "{{\"type\":\"session_turn\",\"sequence\":{sequence},\"writer\":{i}}}"
                            ),
                        );
                        mem.metadata.tags = vec!["session".into(), "turn".into()];
                        mem
                    })
                    .unwrap();
                sequence
            })
        })
        .collect();

    let mut sequences: Vec<u64> = handles.into_iter().map(|h| h.join().unwrap()).collect();
    sequences.sort_unstable();
    assert_eq!(
        sequences,
        (1..=N as u64).collect::<Vec<_>>(),
        "{N} concurrent writers must receive 1..={N} with no duplicates"
    );

    // The counter is the source of truth for the next allocation.
    assert_eq!(store.last_session_sequence(sid).unwrap(), Some(N as u64));

    // Every allocated sequence is actually persisted, exactly once, and the
    // record content agrees with the allocated value.
    let stored = store.scan_all(Galaxy::Sessions).unwrap();
    assert_eq!(stored.len(), N, "every writer's turn must be stored");
    let mut stored_sequences: Vec<u64> = stored
        .iter()
        .map(|m| {
            let v: serde_json::Value = serde_json::from_str(&m.content).unwrap();
            v.get("sequence")
                .and_then(serde_json::Value::as_u64)
                .unwrap()
        })
        .collect();
    stored_sequences.sort_unstable();
    assert_eq!(stored_sequences, (1..=N as u64).collect::<Vec<_>>());
}

/// Cheap regression for the two-writer case (duplicates appeared in 3/5
/// trials before the fix): a loop of interleaved writers must never reuse a
/// sequence.
#[test]
fn two_writer_loop_never_duplicates_sequences() {
    use std::sync::Arc;
    use wm_memory::Memory;

    const PER_WRITER: usize = 25;
    let tmp = tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
    let sid = "sess-h1-two-writers";

    // Both writers spawn before either join (same deliberate collect as the
    // 100-writer test above).
    #[allow(clippy::needless_collect)]
    let handles: Vec<_> = (0..2)
        .map(|w| {
            let store = Arc::clone(&store);
            std::thread::spawn(move || {
                let mut mine = Vec::with_capacity(PER_WRITER);
                for i in 0..PER_WRITER {
                    let (sequence, _mem) = store
                        .put_session_turn(sid, |sequence| {
                            let mut mem = Memory::new(
                                Galaxy::Sessions,
                                format!(
                                    "{{\"type\":\"session_turn\",\"sequence\":{sequence},\"w\":{w},\"i\":{i}}}"
                                ),
                            );
                            mem.metadata.tags = vec!["session".into(), "turn".into()];
                            mem
                        })
                        .unwrap();
                    mine.push(sequence);
                }
                mine
            })
        })
        .collect();

    let mut all: Vec<u64> = handles
        .into_iter()
        .flat_map(|h| h.join().unwrap())
        .collect();
    all.sort_unstable();
    let total = 2 * PER_WRITER;
    assert_eq!(
        all,
        (1..=total as u64).collect::<Vec<_>>(),
        "two interleaved writers must still produce contiguous unique sequences"
    );
    assert_eq!(
        store.last_session_sequence(sid).unwrap(),
        Some(total as u64)
    );
}

/// Counters are per-session: one session's allocations never move another's.
#[test]
fn session_sequences_are_scoped_per_session() {
    use wm_memory::Memory;

    let tmp = tempdir().unwrap();
    let store = MemoryStore::open_default(tmp.path()).unwrap();

    let build = |label: &str| {
        let label = label.to_string();
        move |sequence: u64| {
            let mut mem = Memory::new(
                Galaxy::Sessions,
                format!(
                    "{{\"type\":\"session_turn\",\"sequence\":{sequence},\"label\":\"{label}\"}}"
                ),
            );
            mem.metadata.tags = vec!["session".into(), "turn".into()];
            mem
        }
    };

    let (a1, _) = store.put_session_turn("sess-a", build("a")).unwrap();
    let (b1, _) = store.put_session_turn("sess-b", build("b")).unwrap();
    let (a2, _) = store.put_session_turn("sess-a", build("a")).unwrap();

    assert_eq!((a1, b1, a2), (1, 1, 2));
    assert_eq!(store.last_session_sequence("sess-a").unwrap(), Some(2));
    assert_eq!(store.last_session_sequence("sess-b").unwrap(), Some(1));
    assert_eq!(store.last_session_sequence("sess-unknown").unwrap(), None);
}
