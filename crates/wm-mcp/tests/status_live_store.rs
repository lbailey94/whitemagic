//! Live-store inspection regression (9.1.6).
//!
//! `wm status` / `wm grimoire` hung forever when a server held the store:
//! LMDB's write env-open falls back to a blocking shared lock when the
//! exclusive writer lock is taken, then opens `data.mdb` for writing and
//! wedges on its internal mutex. Inspection (`status::collect`) must open
//! read-only, and write-intent callers must detect the held lock with the
//! non-blocking `probe_write_lock` probe.
//!
//! This test spawns a real `wm serve` on a throwaway store (the served
//! store holds the LMDB writer lock across processes), then proves:
//!   - `status::collect` completes promptly and reports the store healthy
//!   - `probe_write_lock` reports the lock held
//!   - releasing the server frees the lock for `probe_write_lock`

#![cfg(not(windows))]

use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc::{Receiver, channel};
use std::time::{Duration, Instant};

struct ServeProcess {
    child: Child,
    stdin: std::process::ChildStdin,
    responses: Receiver<String>,
}

impl ServeProcess {
    fn spawn(store_root: &std::path::Path) -> Self {
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
        let _ = self.stdin.write_all(b"");
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

#[test]
fn status_collect_completes_on_a_live_store() {
    let root = tempfile::tempdir().expect("tempdir");
    let mut server = ServeProcess::spawn(root.path());
    server.rpc("initialize", 1);
    server.rpc("notifications/initialized", 2);

    // A served store is writable: prove it so the lock is genuinely held.
    let created = server.rpc("tools/call", 3);
    assert!(created.get("result").is_some() || created.get("error").is_some());

    // The regression: this hung forever before the readonly-first fix.
    let started = Instant::now();
    let report = wm_mcp::status::collect(root.path());
    assert!(
        started.elapsed() < Duration::from_secs(20),
        "status::collect must complete promptly on a live store"
    );
    assert!(report.store_ok, "served store must report store_ok");

    // The probe sees the held writer lock across processes.
    assert!(
        wm_memory::MemoryStore::probe_write_lock(root.path()).is_err(),
        "probe must detect the held LMDB writer lock"
    );

    drop(server);

    // Released: the probe now acquires the lock.
    assert!(
        wm_memory::MemoryStore::probe_write_lock(root.path()).is_ok(),
        "probe must succeed after the server exits"
    );
}

/// 2026-09-21 reviewer finding: once a real indexed store exists, a one-shot
/// `wm status` emitted the Backlog B2 read-only-index write-visibility warning
/// on stderr whenever ambient `RUST_LOG` admitted WARN — a healthy install
/// looked suspicious. The inspection process opens the index quietly now; the
/// long-lived read-only server keeps the loud disclosure.
#[test]
fn status_stderr_stays_clean_when_rust_log_admits_warnings() {
    let root = tempfile::tempdir().expect("tempdir");
    let store = root.path().join("store");
    let store_arg = store.to_str().expect("store path").to_string();

    // Fixture: a real store with an indexed write.
    let out = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "session",
            "start",
            "--store",
            &store_arg,
            "--title",
            "status stderr fixture",
        ])
        .output()
        .expect("run wm session start");
    assert!(
        out.status.success(),
        "fixture must initialize an indexed store: {}",
        String::from_utf8_lossy(&out.stderr)
    );

    let out = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args(["status", "--store", &store_arg])
        .env("RUST_LOG", "warn")
        .output()
        .expect("run wm status");
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(out.status.success(), "status must succeed: {stderr}");
    assert!(
        !stderr.contains("read-only search index opened"),
        "one-shot status must not disclose read-only index write-visibility: {stderr}"
    );
    assert!(
        !stderr.contains("WARN"),
        "healthy status must not emit warning noise under RUST_LOG=warn: {stderr}"
    );
    assert!(
        String::from_utf8_lossy(&out.stdout).contains("ready"),
        "status report still expected on stdout"
    );
}
