//! Stdio transport purity: every stdout line must be JSON-RPC.
//!
//! The stdio transport is the primary local client path (npm/Docker clients
//! spawn `wm serve --transport stdio`), so a single human-readable line on
//! stdout corrupts the protocol stream. `memory.ingest` shipped exactly that
//! bug — a banner and a report printed from the shared tool function — and it
//! was only caught by a client crashing mid-session (2026-09-24). This
//! spawned-binary fixture pins the class: it drives the real binary over real
//! pipes and fails on the first non-JSON stdout line, before a user has to.
//!
//! Windows: the spawned stdio `wm serve` e2e wedges (same class as the
//! profile/Landlock/startup e2e); tracked separately.

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

    /// Send a request and return the next stdout line **unparsed** — the
    /// caller decides whether it is valid JSON (that is the assertion).
    fn send_raw(&mut self, method: &str, params: &serde_json::Value, id: u64) -> String {
        let req = serde_json::json!({
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params,
        });
        writeln!(self.stdin, "{req}").expect("write request");
        self.stdin.flush().expect("flush request");
        self.responses
            .recv_timeout(Duration::from_secs(30))
            .unwrap_or_else(|_| {
                panic!("{method} (id {id}) got no stdout line within 30s — serve wedged?")
            })
    }

    fn rpc(&mut self, method: &str, params: &serde_json::Value, id: u64) -> serde_json::Value {
        let line = self.send_raw(method, params, id);
        serde_json::from_str(&line).unwrap_or_else(|e| {
            panic!("stdout line after {method} (id {id}) is not JSON-RPC ({e}): {line:?}")
        })
    }
}

impl Drop for ServeProcess {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

#[test]
fn stdio_stdout_is_json_only_across_ingest_and_catalog() {
    let tmp = tempfile::tempdir().unwrap();
    let source = tmp.path().join("ingest-src");
    std::fs::create_dir_all(&source).unwrap();
    std::fs::write(source.join("note.md"), "# sample\nstdio purity note\n").unwrap();
    let store_root = tmp.path().join("store");
    std::fs::create_dir_all(&store_root).unwrap();

    let mut serve = ServeProcess::spawn(&store_root);
    serve.rpc(
        "initialize",
        &serde_json::json!({
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "stdio-purity-e2e", "version": "1.0"},
        }),
        1,
    );

    // tools/list: the catalog path (also exercises the enriched outputSchemas).
    let tools = serve.rpc("tools/list", &serde_json::json!({}), 2);
    assert!(
        tools["result"]["tools"].is_array(),
        "tools/list must return a catalog: {tools}"
    );

    // memory.ingest: the tool that leaked a human banner + report to stdout.
    // The banner printed before the response and the report printed before the
    // response is written, so the next stdout line *is* the response only if
    // the tool path is silent. A leaked line fails the JSON parse here.
    let ingest = serve.rpc(
        "tools/call",
        &serde_json::json!({
            "name": "memory.ingest",
            "arguments": {"source": source.display().to_string(), "dry_run": true}
        }),
        3,
    );
    let payload = ingest
        .get("result")
        .and_then(|result| result.get("structuredContent"))
        .unwrap_or(&ingest);
    assert!(
        payload.get("files_found").is_some(),
        "ingest must return its structured report over stdio: {ingest}"
    );

    // A trailing request proves nothing leaked *after* the ingest response.
    let pong = serve.rpc(
        "tools/call",
        &serde_json::json!({
            "name": "memory.list",
            "arguments": {"limit": 1}
        }),
        4,
    );
    assert!(
        pong["result"].is_object(),
        "post-ingest request must answer cleanly: {pong}"
    );
}
