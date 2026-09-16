//! Startup-under-stress fixtures (AHIMSA Target B / security item 12).
//!
//! Spawned-binary fixture for the **healthy start** leg: a fresh store under
//! `WM_HOMEOSTASIS_FROZEN=1` opens, accepts a `memory.create`, and serves the
//! record back — the frozen pin does not break the normal path and the store
//! is not silently empty.
//!
//! The refusal legs are pinned in-process, deterministically:
//! - first-run starvation (typed homeostasis-limit error naming
//!   `WM_HOMEOSTASIS_FROZEN`) and healthy writes:
//!   `pipeline_strict_refusal_is_typed_and_distinct_from_starvation` in
//!   `wm-dispatch`;
//! - governance refusal (`VIOLATION_AHIMSA` under strict mode):
//!   `coordination_lease_acquisition_refused_in_strict_mode` and the
//!   coordination cleanup/no-discovery admissions in `wm-governance`.
//!
//! Why starvation is not reproduced through the spawned binary: the veto is
//! **load-sensitive by design** (it exists so host load aborts writes), and
//! `WM_HOMEOSTASIS_FROZEN=1` is precisely the disclosed determinism seam that
//! keeps a fresh store's confidence at its healthy default. A spawned fixture
//! would therefore be either flaky (unfrozen, host-load-dependent) or a test
//! of the pin rather than the veto — so the veto + its frozen-setting
//! disclosure are asserted in-process where they are deterministic.
//!
//! Windows: the spawned stdio `wm serve` e2e wedges (same class as the
//! profile/Landlock e2e); tracked separately.

#![cfg(not(windows))]

use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc::{Receiver, channel};
use std::time::Duration;

struct ServeProcess {
    child: Child,
    stdin: std::process::ChildStdin,
    responses: Receiver<String>,
}

impl ServeProcess {
    fn spawn(store_root: &std::path::Path) -> Self {
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_wm"));
        cmd.args([
            "serve",
            "--store",
            &store_root.display().to_string(),
            "--transport",
            "stdio",
            "--rate-limit",
            "0",
            "--profile",
            "curated",
        ]);
        // Deterministic runs: pin the homeostasis/self-model side of the
        // dispatch gate (also disclosed in the refusal text).
        cmd.env("WM_HOMEOSTASIS_FROZEN", "1");
        cmd.env_remove("WM_TOOL_PROFILE");
        cmd.env_remove("WM_TOOL_ALLOWLIST");
        cmd.stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        let mut child = cmd.spawn().expect("spawn wm serve");
        let stdin = child.stdin.take().expect("stdin");
        let stdout = child.stdout.take().expect("stdout");
        let (tx, responses) = channel();
        std::thread::spawn(move || {
            let mut reader = BufReader::new(stdout);
            let mut line = String::new();
            loop {
                line.clear();
                match reader.read_line(&mut line) {
                    Ok(0) | Err(_) => break,
                    Ok(_) => {
                        if tx.send(line.clone()).is_err() {
                            break;
                        }
                    }
                }
            }
        });
        Self {
            child,
            stdin,
            responses,
        }
    }

    fn rpc(&mut self, method: &str, params: &serde_json::Value, id: u64) -> serde_json::Value {
        let req = serde_json::json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params,
        });
        writeln!(self.stdin, "{req}").expect("write request");
        self.stdin.flush().expect("flush request");
        let line = self
            .responses
            .recv_timeout(Duration::from_secs(30))
            .unwrap_or_else(|_| {
                panic!("{method} (id {id}) got no response within 30s — serve process wedged?")
            });
        serde_json::from_str(&line)
            .unwrap_or_else(|e| panic!("{method} (id {id}) returned invalid JSON ({e}): {line}"))
    }

    fn initialize(&mut self, id: u64) {
        let init = self.rpc(
            "initialize",
            &serde_json::json!({
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "startup-stress-e2e", "version": "1.0"},
            }),
            id,
        );
        assert_eq!(
            init["result"]["serverInfo"]["name"], "whitemagic",
            "initialize handshake failed: {init}"
        );
    }
}

impl Drop for ServeProcess {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

#[test]
fn healthy_start_under_frozen_settings_creates_and_reads() {
    let tmp = tempfile::tempdir().unwrap();
    let mut serve = ServeProcess::spawn(tmp.path());
    serve.initialize(1);

    let created = serve.rpc(
        "tools/call",
        &serde_json::json!({
            "name": "memory.create",
            "arguments": {"content": "zxqstartupstress healthy-start record", "galaxy": "codex"}
        }),
        2,
    );
    let created_text = created.to_string();
    assert!(
        !created_text.contains("self-model confidence"),
        "healthy start must not trip the starvation veto: {created}"
    );
    assert!(
        created_text.contains("\"status\":\"success\"")
            || created_text.contains("\"status\": \"success\""),
        "healthy-start create must succeed: {created}"
    );

    let found = serve.rpc(
        "tools/call",
        &serde_json::json!({
            "name": "memory.search",
            "arguments": {"query": "zxqstartupstress healthy-start record"}
        }),
        3,
    );
    assert!(
        found.to_string().contains("zxqstartupstress"),
        "the record must be readable back — not a silently empty store: {found}"
    );
}
