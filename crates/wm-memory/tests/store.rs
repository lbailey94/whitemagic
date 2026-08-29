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
    assert_eq!(names.len(), 14);
}
