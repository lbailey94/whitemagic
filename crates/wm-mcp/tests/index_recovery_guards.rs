//! Index-recovery guards (9.1.9, review round 2).
//!
//! LMDB is canonical; the Tantivy index is a disposable accelerator. The
//! reviewer removed a segment file, watched `wm reindex` and
//! `wm doctor --repair` both fail at the index-open stage, then fixed it by
//! hand by moving the directory aside. These tests pin the automated flow:
//!
//!   - `wm reindex` under a live server refuses and leaves the index alone
//!   - an unopenable index is quarantined and rebuilt from LMDB, verified
//!   - `wm doctor --repair` performs the same recovery

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

fn init_store(root: &Path) -> String {
    let root_arg = root.to_str().expect("store path").to_string();
    let out = wm(&[
        "session",
        "start",
        "--store",
        &root_arg,
        "--title",
        "index recovery fixture",
    ]);
    assert!(
        out.status.success(),
        "fixture: session start must initialize the store: {}",
        text_of(&out)
    );
    root_arg
}

fn corrupt_index(store_root: &Path) {
    let meta = store_root.join("lmdb/tantivy/meta.json");
    assert!(
        meta.exists(),
        "fixture: index metadata must exist at {}",
        meta.display()
    );
    std::fs::write(&meta, b"{ not json").expect("corrupt index metadata");
}

fn corrupt_siblings(store_root: &Path) -> Vec<PathBuf> {
    let lmdb = store_root.join("lmdb");
    std::fs::read_dir(&lmdb)
        .expect("lmdb dir")
        .filter_map(std::result::Result::ok)
        .map(|e| e.path())
        .filter(|p| {
            p.file_name()
                .is_some_and(|n| n.to_string_lossy().contains(".corrupt."))
        })
        .collect()
}

#[test]
fn reindex_refuses_under_a_live_server_without_touching_the_index() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let store = tmp.path().join("store");
    let store_arg = init_store(&store);

    let mut server = ServeProcess::spawn(&store);
    server.rpc("initialize", 1);
    server.rpc("notifications/initialized", 2);

    let out = wm(&["reindex", "--store", &store_arg]);
    let refusal = text_of(&out);
    assert!(
        !out.status.success(),
        "reindex must refuse under a live server: {refusal}"
    );
    assert!(
        refusal.contains("server may be running"),
        "refusal must name the live-server remedy: {refusal}"
    );
    assert!(
        corrupt_siblings(&store).is_empty(),
        "a healthy index must never be quarantined"
    );

    drop(server);
}

#[test]
fn reindex_and_doctor_repair_recover_an_unopenable_index() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let store = tmp.path().join("store");
    let store_arg = init_store(&store);

    // wm reindex: quarantine + rebuild + verify.
    corrupt_index(&store);
    let out = wm(&["reindex", "--store", &store_arg]);
    let text = text_of(&out);
    assert!(out.status.success(), "reindex must recover: {text}");
    assert!(
        text.contains("quarantined to"),
        "reindex must disclose the quarantine: {text}"
    );
    assert!(
        text.contains("Verified: LMDB="),
        "reindex must verify against LMDB: {text}"
    );
    assert_eq!(
        corrupt_siblings(&store).len(),
        1,
        "the broken index is kept beside the fresh one"
    );

    // A second run on the recovered store is a plain rebuild, no quarantine.
    let out = wm(&["reindex", "--store", &store_arg]);
    let text = text_of(&out);
    assert!(out.status.success(), "clean reindex: {text}");
    assert!(
        !text.contains("quarantined to"),
        "no quarantine on a healthy index: {text}"
    );

    // wm doctor --repair: same recovery through the doctor door.
    corrupt_index(&store);
    let out = wm(&["doctor", "--store", &store_arg, "--repair"]);
    let text = text_of(&out);
    assert!(out.status.success(), "doctor --repair: {text}");
    assert!(
        text.contains("Index rebuilt from canonical LMDB"),
        "doctor --repair must rebuild the index: {text}"
    );
    assert_eq!(
        corrupt_siblings(&store).len(),
        2,
        "doctor's recovery also quarantines rather than deletes"
    );

    // And doctor is healthy afterwards.
    let out = wm(&["doctor", "--store", &store_arg]);
    let text = text_of(&out);
    assert!(out.status.success(), "doctor after recovery: {text}");
    assert!(
        text.contains("All systems healthy"),
        "doctor must be healthy after recovery: {text}"
    );
}
