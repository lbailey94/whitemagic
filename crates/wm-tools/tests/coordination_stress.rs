//! High-concurrency stress & contention benchmark for B3 coordination (G3-CRB-1 Phase 1).
//!
//! Asserts:
//! 1. 50 concurrent tasks competing for the exact same scope: exactly 1 winner, 49 conflicts, zero split-brain.
//! 2. 50 concurrent tasks claiming disjoint scopes: exactly 50 successes, 0 lost updates, exactly 50 entries in ledger.
//! 3. 50 concurrent releases: exactly 50 successes, scope transitions to free.
//! 4. Continuous snapshot-readonly readers under heavy write traffic: zero torn reads, zero lockfile leaks.
//! 5. Stale lock stealing: lockfile older than STALE_LOCK_SECS is cleaned up automatically without wedging.

use serde_json::{Value, json};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::Arc;
use std::time::Duration as StdDuration;
use tokio::sync::Barrier;
use wm_core::{Context, Tool};
use wm_tools::expansion::{CodeCheckTool, CodeClaimTool, CodeListTool, CodeReleaseTool};

fn fake_git_repo() -> (tempfile::TempDir, PathBuf) {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().to_path_buf();
    fs::create_dir_all(root.join(".git/objects")).unwrap();
    fs::write(root.join(".git/HEAD"), "ref: refs/heads/main\n").unwrap();
    (dir, root)
}

fn root_str(root: &Path) -> Value {
    json!(root.display().to_string())
}

#[tokio::test(flavor = "multi_thread", worker_threads = 8)]
async fn test_50_tasks_competing_for_single_scope_zero_split_brain() {
    let (_dir, root) = fake_git_repo();
    let num_tasks = 50;
    let barrier = Arc::new(Barrier::new(num_tasks));
    let mut handles = Vec::new();

    for i in 0..num_tasks {
        let root = root.clone();
        let barrier = barrier.clone();
        handles.push(tokio::spawn(async move {
            barrier.wait().await;
            let claim = CodeClaimTool::new(None);
            let mut ctx = Context::default();
            claim
                .call(
                    &mut ctx,
                    json!({
                        "scope": "crates/core/hot_path.rs",
                        "intent": format!("critical edit from task {i}"),
                        "owner_session": format!("session-{i:03}"),
                        "root": root_str(&root),
                    }),
                )
                .await
                .unwrap()
        }));
    }

    let mut successes = 0;
    let mut conflicts = 0;
    let mut winner_holder = String::new();

    for handle in handles {
        let res = handle.await.unwrap();
        let status = res["status"].as_str().unwrap();
        if status == "success" {
            successes += 1;
            winner_holder = res["owner_session"].as_str().unwrap().to_string();
        } else if status == "conflict" {
            conflicts += 1;
            assert!(res["holder"].is_string());
            assert!(res["holder_intent"].is_string());
        } else {
            panic!("unexpected status: {status}");
        }
    }

    assert_eq!(successes, 1, "exactly ONE task must acquire the scope");
    assert_eq!(
        conflicts,
        num_tasks - 1,
        "all other tasks must receive conflict"
    );

    // Verify check confirms the exact winner
    let check = CodeCheckTool::new(None);
    let mut ctx = Context::default();
    let check_res = check
        .call(
            &mut ctx,
            json!({
                "scope": "crates/core/hot_path.rs",
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();

    assert_eq!(check_res["state"], "claimed");
    assert_eq!(check_res["holder"], winner_holder);
}

#[tokio::test(flavor = "multi_thread", worker_threads = 8)]
async fn test_50_tasks_disjoint_scopes_no_lost_updates() {
    let (_dir, root) = fake_git_repo();
    let num_tasks = 50;
    let barrier = Arc::new(Barrier::new(num_tasks));
    let mut handles = Vec::new();

    for i in 0..num_tasks {
        let root = root.clone();
        let barrier = barrier.clone();
        handles.push(tokio::spawn(async move {
            barrier.wait().await;
            let claim = CodeClaimTool::new(None);
            let mut ctx = Context::default();
            claim
                .call(
                    &mut ctx,
                    json!({
                        "scope": format!("crates/module_{i:03}/file.rs"),
                        "intent": format!("independent feature {i}"),
                        "owner_session": format!("worker-{i:03}"),
                        "root": root_str(&root),
                    }),
                )
                .await
                .unwrap()
        }));
    }

    for handle in handles {
        let res = handle.await.unwrap();
        assert_eq!(
            res["status"], "success",
            "every disjoint claim must succeed: {res}"
        );
    }

    // List all leases and verify count is exactly num_tasks
    let list = CodeListTool::new();
    let mut ctx = Context::default();
    let list_res = list
        .call(&mut ctx, json!({"root": root_str(&root)}))
        .await
        .unwrap();

    assert_eq!(list_res["status"], "success");
    let active_count = list_res["count"].as_u64().unwrap();
    assert_eq!(
        active_count, num_tasks as u64,
        "zero lost updates: all 50 disjoint leases must exist"
    );

    // Now concurrently release all 50 leases
    let barrier_rel = Arc::new(Barrier::new(num_tasks));
    let mut rel_handles = Vec::new();

    for i in 0..num_tasks {
        let root = root.clone();
        let barrier = barrier_rel.clone();
        rel_handles.push(tokio::spawn(async move {
            barrier.wait().await;
            let release = CodeReleaseTool::new(None);
            let mut ctx = Context::default();
            release
                .call(
                    &mut ctx,
                    json!({
                        "scope": format!("crates/module_{i:03}/file.rs"),
                        "lease_id": format!("crates/module_{i:03}/file.rs"),
                        "owner_session": format!("worker-{i:03}"),
                        "root": root_str(&root),
                    }),
                )
                .await
                .unwrap()
        }));
    }

    for handle in rel_handles {
        let res = handle.await.unwrap();
        assert_eq!(
            res["status"], "success",
            "every exact-owner release must succeed: {res}"
        );
        assert_eq!(res["state"], "released");
    }

    let final_list = list
        .call(&mut ctx, json!({"root": root_str(&root)}))
        .await
        .unwrap();
    assert_eq!(
        final_list["count"].as_u64().unwrap(),
        0,
        "all leases successfully released"
    );
    drop(_dir);
}

#[tokio::test(flavor = "multi_thread", worker_threads = 8)]
async fn test_snapshot_readonly_immunity_under_heavy_write_churn() {
    let (_dir, root) = fake_git_repo();
    let num_writers = 10;
    let num_readers = 10;
    let iterations = 10;

    let mut writer_handles = Vec::new();
    let mut reader_handles = Vec::new();

    // Writers claiming and releasing rapidly
    for w in 0..num_writers {
        let root = root.clone();
        writer_handles.push(tokio::spawn(async move {
            let claim = CodeClaimTool::new(None);
            let release = CodeReleaseTool::new(None);
            let mut ctx = Context::default();
            for it in 0..iterations {
                let scope = format!("churn/scope_{w}.rs");
                let owner = format!("writer-{w}");
                let _ = claim
                    .call(
                        &mut ctx,
                        json!({
                            "scope": scope,
                            "intent": format!("churn {it}"),
                            "owner_session": owner,
                            "root": root_str(&root),
                        }),
                    )
                    .await;
                tokio::time::sleep(StdDuration::from_millis(5)).await;
                let _ = release
                    .call(
                        &mut ctx,
                        json!({
                            "scope": scope,
                            "lease_id": scope,
                            "owner_session": owner,
                            "root": root_str(&root),
                        }),
                    )
                    .await;
            }
        }));
    }

    // Readers continuously checking and listing
    for r in 0..num_readers {
        let root = root.clone();
        reader_handles.push(tokio::spawn(async move {
            let check = CodeCheckTool::new(None);
            let list = CodeListTool::new();
            let mut ctx = Context::default();
            let mut read_ops = 0;
            for _ in 0..(iterations * 4) {
                let scope = format!("churn/scope_{}.rs", r % num_writers);
                let c_res = check
                    .call(
                        &mut ctx,
                        json!({
                            "scope": scope,
                            "root": root_str(&root),
                        }),
                    )
                    .await
                    .unwrap();
                assert!(c_res["state"] == "claimed" || c_res["state"] == "free");

                let l_res = list
                    .call(&mut ctx, json!({"root": root_str(&root)}))
                    .await
                    .unwrap();
                assert_eq!(l_res["status"], "success");
                read_ops += 1;
                tokio::time::sleep(StdDuration::from_millis(3)).await;
            }
            read_ops
        }));
    }

    for h in writer_handles {
        h.await.unwrap();
    }
    for h in reader_handles {
        let reads = h.await.unwrap();
        assert!(reads > 0, "readers executed unblocked");
    }

    // Confirm no stray lockfile remains
    let lock_file = root.join(".git/wm-leases.json.lock");
    assert!(!lock_file.exists(), "lockfile must not linger after churn");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn test_stale_lockfile_recovery_steals_and_succeeds() {
    let (_dir, root) = fake_git_repo();
    let lock_file = root.join(".git/wm-leases.json.lock");

    // Manually create a simulated crashed writer's lockfile
    fs::write(&lock_file, "crashed_pid_99999").unwrap();

    // Set mtime to 35 seconds ago using `touch -d "35 seconds ago"` (STALE_LOCK_SECS is 30s)
    let status = Command::new("touch")
        .args(["-d", "35 seconds ago", lock_file.to_str().unwrap()])
        .status()
        .expect("touch command must succeed");
    assert!(status.success());

    // Claim should detect stale lock, steal it, and succeed
    let claim = CodeClaimTool::new(None);
    let mut ctx = Context::default();
    let res = claim
        .call(
            &mut ctx,
            json!({
                "scope": "recovery/file.rs",
                "intent": "resuming after stale lock",
                "owner_session": "heir-session",
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();

    assert_eq!(res["status"], "success", "must steal stale lock: {res}");
    assert!(!lock_file.exists(), "lockfile released after operation");

    // Verify check sees the claim
    let check = CodeCheckTool::new(None);
    let check_res = check
        .call(
            &mut ctx,
            json!({
                "scope": "recovery/file.rs",
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(check_res["state"], "claimed");
    assert_eq!(check_res["holder"], "heir-session");
}
