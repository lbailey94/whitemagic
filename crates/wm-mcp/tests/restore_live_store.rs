//! Restore-under-a-live-writer regression (9.1.9, review round 2).
//!
//! `wm backup` already refuses while a server owns the store, but `wm
//! restore --force` did not check ownership: it happily replaced the store
//! root underneath a running `wm serve`, which then shut down with missing
//! Tantivy files and left a healthy LMDB with a broken search index.
//!
//! This test spawns a real `wm serve` on a throwaway store and proves:
//!   - the live server holds the LMDB writer lock (fixture)
//!   - `wm restore --force` is refused while that lock is held
//!   - the refusal explains the ownership rule
//!   - once the server exits, the same restore succeeds
//!
//! `--force` overwrites an existing *idle* store; it never overrides store
//! ownership.

#![cfg(not(windows))]

use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Output, Stdio};
use std::sync::mpsc::{Receiver, channel};
use std::time::{Duration, Instant};

struct ServeProcess {
    child: Child,
    stdin: std::process::ChildStdin,
    responses: Receiver<String>,
}

impl ServeProcess {
    fn spawn(store_root: &Path) -> Self {
        let mut child = Command::new(env!("CARGO_BIN_EXE_wm"))
            .args(["serve", "--profile", "curated", "--store"])
            .arg(store_root)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn wm serve");

        let stdout = child.stdout.take().expect("stdout");
        let stdin = child.stdin.take().expect("stdin");
        let (tx, rx) = channel();
        std::thread::spawn(move || {
            let mut lines = BufReader::new(stdout).lines();
            while let Some(Ok(line)) = lines.next() {
                if tx.send(line).is_err() {
                    break;
                }
            }
        });
        Self {
            child,
            stdin,
            responses: rx,
        }
    }

    fn rpc(&mut self, method: &str, id: u32) -> serde_json::Value {
        let req = serde_json::json!({"jsonrpc": "2.0", "id": id, "method": method});
        writeln!(self.stdin, "{req}").expect("write rpc");
        let deadline = Instant::now() + Duration::from_secs(30);
        loop {
            let remaining = deadline.saturating_duration_since(Instant::now());
            let line = self
                .responses
                .recv_timeout(remaining)
                .unwrap_or_else(|_| panic!("no response to {method} within 30s"));
            let value: serde_json::Value = serde_json::from_str(&line).expect("json rpc line");
            if value.get("id").and_then(serde_json::Value::as_u64) == Some(u64::from(id)) {
                return value;
            }
        }
    }
}

impl Drop for ServeProcess {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

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

#[test]
fn restore_refuses_while_a_server_owns_the_store() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let store = tmp.path().join("store");
    let backups = tmp.path().join("backups");
    let store_arg = store.to_str().expect("store path").to_string();

    // Fresh store via the CLI bootstrap path (9.1.9 F6), then an idle backup.
    let out = wm(&[
        "session",
        "start",
        "--store",
        &store_arg,
        "--title",
        "restore fixture",
    ]);
    assert!(
        out.status.success(),
        "fixture: session start must initialize the store: {}",
        text_of(&out)
    );

    let out = wm(&[
        "backup",
        "--store",
        &store_arg,
        "--out",
        backups.to_str().expect("backups path"),
    ]);
    assert!(out.status.success(), "fixture: backup: {}", text_of(&out));
    let backup_dir: PathBuf = std::fs::read_dir(&backups)
        .expect("backups dir")
        .map(|e| e.expect("entry").path())
        .find(|p| p.is_dir())
        .expect("backup directory");
    let backup_arg = backup_dir.to_str().expect("backup path").to_string();

    // A live writer owns the store.
    let mut server = ServeProcess::spawn(&store);
    server.rpc("initialize", 1);
    server.rpc("notifications/initialized", 2);
    assert!(
        wm_memory::MemoryStore::probe_write_lock(&store).is_err(),
        "fixture: spawned server must hold the LMDB writer lock"
    );

    // `--force` must not override ownership: the restore is refused and the
    // store stays owned.
    let out = wm(&[
        "restore",
        "--backup",
        &backup_arg,
        "--store",
        &store_arg,
        "--force",
    ]);
    let refusal = text_of(&out);
    assert!(
        !out.status.success(),
        "restore must be refused while the store is owned: {refusal}"
    );
    assert!(
        refusal.contains("never overrides store ownership"),
        "refusal must explain the ownership rule: {refusal}"
    );
    assert!(
        wm_memory::MemoryStore::probe_write_lock(&store).is_err(),
        "server must still own the store after the refused restore"
    );

    drop(server);

    // Idle again: the same restore is now a normal --force overwrite.
    assert!(
        wm_memory::MemoryStore::probe_write_lock(&store).is_ok(),
        "fixture: lock must be released after the server exits"
    );
    let out = wm(&[
        "restore",
        "--backup",
        &backup_arg,
        "--store",
        &store_arg,
        "--force",
    ]);
    assert!(
        out.status.success(),
        "restore must succeed on an idle store: {}",
        text_of(&out)
    );
}
