//! Landlock v0 E2E — a real `wm serve` process under `WM_LANDLOCK=1`
//! must keep working normally (all its writes live under the store root),
//! disclose the report through the persisted state file, and leave the
//! flag-off path byte-for-byte unchanged.

use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};

struct ServeProcess {
    child: Child,
    stdin: std::process::ChildStdin,
    stdout: BufReader<std::process::ChildStdout>,
}

impl ServeProcess {
    fn spawn(store_root: &std::path::Path, landlock: bool) -> Self {
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_wm"));
        cmd.args([
            "serve",
            "--store",
            &store_root.display().to_string(),
            "--transport",
            "stdio",
            "--rate-limit",
            "0",
        ])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
        if landlock {
            cmd.env("WM_LANDLOCK", "1");
        }
        let mut child = cmd.spawn().expect("spawn wm serve");
        let stdin = child.stdin.take().expect("stdin");
        let stdout = BufReader::new(child.stdout.take().expect("stdout"));
        Self {
            child,
            stdin,
            stdout,
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
        let mut line = String::new();
        self.stdout
            .read_line(&mut line)
            .expect("read response line");
        serde_json::from_str(&line).expect("valid JSON-RPC response")
    }

    fn wm(&mut self, route: &str, args: &serde_json::Value, id: u64) -> serde_json::Value {
        let resp = self.rpc(
            "tools/call",
            &serde_json::json!({"name": "wm", "arguments": {"route": route, "args": args}}),
            id,
        );
        let content = resp
            .get("result")
            .and_then(|r| r.get("content"))
            .and_then(|c| c.as_array())
            .and_then(|a| a.first())
            .and_then(|c| c.get("text"))
            .and_then(|t| t.as_str())
            .map_or_else(
                || panic!("tools/call {route} returned no content: {resp}"),
                String::from,
            );
        serde_json::from_str(&content)
            .unwrap_or_else(|_| panic!("tools/call {route} content is not JSON: {content}"))
    }
}

impl Drop for ServeProcess {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

fn handshake(server: &mut ServeProcess) {
    let init = server.rpc(
        "initialize",
        &serde_json::json!({
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "landlock-e2e", "version": "1.0"},
        }),
        1,
    );
    assert_eq!(
        init["result"]["serverInfo"]["name"], "whitemagic",
        "initialize handshake failed: {init}"
    );
}

/// The persisted report must be enabled and any of the honest outcomes:
/// enforced on this kernel, degraded-but-labeled elsewhere.
fn assert_report_shape(report: &serde_json::Value, store_root: &std::path::Path) {
    assert_eq!(report["enabled"], true, "report must be enabled: {report}");
    assert_eq!(
        report["store_root"],
        store_root.display().to_string(),
        "report must name the store root: {report}"
    );
    let outcome = report["outcome"].as_str().expect("outcome string");
    assert!(
        [
            "enforced",
            "partial",
            "unsupported",
            "platform_unsupported",
            "failed"
        ]
        .contains(&outcome),
        "outcome must be an honest v0 label: {report}"
    );
}

#[test]
fn serve_with_landlock_keeps_working_and_persists_report() {
    let tmp = tempfile::tempdir().expect("temp store root");
    let mut server = ServeProcess::spawn(tmp.path(), true);
    handshake(&mut server);

    // Normal operation under confinement: create + search round-trip.
    let created = server.wm(
        "memory.create",
        &serde_json::json!({
            "content": "landlock e2e marker: whole-process confinement leaves store-root writes intact",
            "tags": ["landlock", "e2e"],
        }),
        2,
    );
    assert_eq!(
        created["status"], "success",
        "memory.create must succeed under Landlock: {created}"
    );
    let id = created["id"]
        .as_str()
        .expect("memory.create returns an id")
        .to_string();

    let searched = server.wm(
        "memory.search",
        &serde_json::json!({"query": "landlock e2e marker"}),
        3,
    );
    assert_eq!(
        searched["status"], "success",
        "memory.search must succeed under Landlock: {searched}"
    );

    // Destructive gate is orthogonal to the kernel sandbox and must hold:
    // refuse without confirm, succeed with confirm.
    let refused = server.wm("memory.delete", &serde_json::json!({"id": id}), 4);
    assert_ne!(
        refused["status"], "success",
        "destructive delete without confirm must be refused: {refused}"
    );
    let deleted = server.wm(
        "memory.delete",
        &serde_json::json!({"id": id, "confirm": true}),
        5,
    );
    assert_eq!(
        deleted["status"], "success",
        "confirmed delete must succeed under Landlock: {deleted}"
    );

    // The process persists its own report under the (granted) store root.
    // (The /status disclosure of the same report is asserted by a
    // status_payload unit test in server.rs — /status is HTTP-only.)
    let report_path = tmp.path().join("landlock_state.json");
    let body = std::fs::read_to_string(&report_path)
        .expect("landlock_state.json must be persisted under the store root");
    let report: serde_json::Value =
        serde_json::from_str(&body).expect("persisted report is valid JSON");
    assert_report_shape(&report, tmp.path());
}

#[test]
fn serve_without_flag_unchanged_no_report_file() {
    let tmp = tempfile::tempdir().expect("temp store root");
    let mut server = ServeProcess::spawn(tmp.path(), false);
    handshake(&mut server);

    let created = server.wm(
        "memory.create",
        &serde_json::json!({"content": "flag-off baseline marker"}),
        2,
    );
    assert_eq!(
        created["status"], "success",
        "flag-off serve must work normally"
    );

    assert!(
        !tmp.path().join("landlock_state.json").exists(),
        "flag-off serve must persist no Landlock report"
    );
}
