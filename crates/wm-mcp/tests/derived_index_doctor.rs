//! H2 (2026-09-20): doctor must grade a degraded derived episodic index
//! (canonical raw records present, term-postings sidecar empty) as DEGRADED,
//! and `wm reindex` must repair it from the raw lane.
//!
//! Companion unit coverage lives in `wm-memory`:
//! `episodic::tests::sidecar_health_exposes_incomplete_derived_index_and_rebuild_heals`.

use lmdb::Transaction;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use tempfile::tempdir;

fn wm(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_wm"))
        .args(args)
        .output()
        .expect("run wm")
}

fn text_of(out: &Output) -> String {
    format!(
        "{}{}",
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    )
}

fn init_store(root: &Path) -> String {
    let root_arg = root.to_str().expect("store path").to_string();
    let out = wm(&[
        "session",
        "start",
        "--store",
        &root_arg,
        "--title",
        "derived index fixture",
    ]);
    assert!(
        out.status.success(),
        "fixture: session start must initialize the store: {}",
        text_of(&out)
    );
    root_arg
}

/// Simulate a failed / never-run sidecar rebuild: clear the derived postings
/// directly. The raw episodic lane stays canonical.
fn clear_episodic_sidecar(store_root: &Path) -> PathBuf {
    let lmdb_path = store_root.join("lmdb");
    let env = lmdb::Environment::new()
        .set_map_size(1 << 30)
        .set_max_dbs(64)
        .open(&lmdb_path)
        .expect("open lmdb env");
    let db = env
        .open_db(Some("episodic_terms_v2"))
        .expect("open episodic_terms_v2");
    let mut tx = env.begin_rw_txn().expect("rw txn");
    tx.clear_db(db).expect("clear sidecar");
    tx.commit().expect("commit");
    lmdb_path
}

#[test]
fn doctor_grades_degraded_episodic_sidecar_and_reindex_repairs() {
    let tmp = tempdir().expect("tempdir");
    let store = tmp.path().join("store");
    let store_arg = init_store(&store);

    // Baseline: the session start mirrored into the episodic lane and its
    // sidecar write populated the term postings — doctor is healthy.
    let out = wm(&["doctor", "--store", &store_arg]);
    assert!(
        out.status.success(),
        "healthy baseline before the fixture: {}",
        text_of(&out)
    );

    clear_episodic_sidecar(&store);

    // Doctor must grade DEGRADED — not "All systems healthy" — and exit 1.
    let out = wm(&["doctor", "--store", &store_arg]);
    let text = text_of(&out);
    assert!(
        !out.status.success(),
        "doctor must not exit 0 on a degraded derived index: {text}"
    );
    assert!(
        text.contains("DEGRADED: canonical memory intact, derived episodic index incomplete"),
        "doctor must name the degraded derived index: {text}"
    );
    assert!(
        !text.contains("All systems healthy"),
        "a degraded store must never be called healthy: {text}"
    );

    // Repair: `wm reindex` rebuilds the sidecar from the raw records.
    let out = wm(&["reindex", "--store", &store_arg]);
    let text = text_of(&out);
    assert!(out.status.success(), "reindex repair: {text}");
    assert!(
        text.contains("Episodic term sidecar rebuilt from"),
        "reindex must rebuild the episodic sidecar: {text}"
    );

    // And the store is healthy again.
    let out = wm(&["doctor", "--store", &store_arg]);
    let text = text_of(&out);
    assert!(out.status.success(), "healthy after repair: {text}");
    assert!(text.contains("All systems healthy"), "{text}");
}
