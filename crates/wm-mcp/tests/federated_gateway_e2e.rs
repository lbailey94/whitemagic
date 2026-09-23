//! Q08-G2 — spawned federated-gateway E2E over the real HTTP transport.
//!
//! Closes the boundary-matrix §4/§6 G2 gap: B5's gateway was covered only by
//! mocks plus the manual `scripts/q03_acceptance.py --mode gateway` script.
//! This test spawns two real backings (`wm serve --transport sse`) and one
//! federated gateway (`wm serve --federate ...`), then exercises the q03
//! gateway segment against them:
//!
//! 1. federated read (`memory.search`) fans out, merges, labels both scopes;
//! 2. a pinned write (`code.claim` with top-level `scope`) lands on the named
//!    backing (verified directly against that backing), not the other one;
//! 3. `code.release` through the owning backing cleans up;
//! 4. an unknown pinned scope fails closed (`unknown_scope`) naming the
//!    reachable scopes.
//!
//! Raw `std::net::TcpStream` HTTP keeps the test dependency-free. Unix-only
//! (process-spawn/teardown precedent).
#![cfg(unix)]

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

struct ChildGuard(Child);

impl Drop for ChildGuard {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

fn free_port() -> u16 {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    listener.local_addr().unwrap().port()
}

fn spawn_backing(store: &Path, root: &Path, port: u16) -> ChildGuard {
    ChildGuard(
        Command::new(env!("CARGO_BIN_EXE_wm"))
            .args([
                "serve",
                "--store",
                store.to_str().unwrap(),
                "--transport",
                "sse",
                "--bind",
                &format!("127.0.0.1:{port}"),
                "--profile",
                "full",
                "--rate-limit",
                "0",
            ])
            .env("WM_HOMEOSTASIS_FROZEN", "1")
            .env("WM_SELFMODEL_FROZEN", "1")
            .env("WM_PROJECT_ROOT", root)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn backing"),
    )
}

/// `code.claim` writes its lease ledger under the project root's git dir;
/// each backing gets its own disposable repo so scope pinning is testable.
fn init_git_root(path: &Path) {
    std::fs::create_dir_all(path).unwrap();
    let status = Command::new("git")
        .args(["init", "-q"])
        .current_dir(path)
        .status()
        .expect("git init");
    assert!(status.success(), "git init failed at {}", path.display());
}

fn spawn_gateway(spec: &str, port: u16, contract: &Path) -> ChildGuard {
    ChildGuard(
        Command::new(env!("CARGO_BIN_EXE_wm"))
            .args([
                "serve",
                "--federate",
                spec,
                "--transport",
                "sse",
                "--bind",
                &format!("127.0.0.1:{port}"),
            ])
            .env("WM_PROJECT", "dev")
            .env("WM_GATEWAY_CONTRACT_PATH", contract)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn gateway"),
    )
}

fn raw_http(port: u16, request: &str) -> Option<String> {
    let mut stream = TcpStream::connect(("127.0.0.1", port)).ok()?;
    stream
        .set_read_timeout(Some(Duration::from_secs(30)))
        .ok()?;
    stream.write_all(request.as_bytes()).ok()?;
    let mut buf = String::new();
    stream.read_to_string(&mut buf).ok()?;
    let (_, body) = buf.split_once("\r\n\r\n")?;
    Some(body.to_string())
}

fn healthz(port: u16) -> bool {
    let request =
        format!("GET /healthz HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n");
    raw_http(port, &request).is_some_and(|body| body.contains("ok"))
}

fn wait_ready(port: u16, label: &str) {
    let deadline = Instant::now() + Duration::from_secs(45);
    while Instant::now() < deadline {
        if healthz(port) {
            return;
        }
        std::thread::sleep(Duration::from_millis(150));
    }
    panic!("{label} on port {port} never became ready");
}

/// POST a `wm` tools/call and return the inner envelope.
fn call_wm(
    port: u16,
    route: &str,
    args: serde_json::Value,
    scope: Option<&str>,
) -> serde_json::Value {
    let mut arguments = serde_json::Map::new();
    arguments.insert("route".into(), serde_json::json!(route));
    arguments.insert("args".into(), args);
    let mut arguments = serde_json::Value::Object(arguments);
    if let Some(scope) = scope {
        arguments["scope"] = serde_json::json!(scope);
    }
    let body = serde_json::json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "wm", "arguments": arguments},
    })
    .to_string();
    let request = format!(
        "POST /mcp HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
        body.len()
    );
    let response = raw_http(port, &request).expect("gateway/backing HTTP response");
    let outer: serde_json::Value = serde_json::from_str(&response).expect("JSON-RPC response");
    assert!(outer.get("error").is_none(), "JSON-RPC error: {outer}");
    let text = outer["result"]["content"][0]["text"]
        .as_str()
        .expect("content text");
    serde_json::from_str(text).expect("inner envelope JSON")
}

#[test]
fn federated_gateway_e2e_pins_scopes_and_preserves_inner_payload() {
    let tmp = tempfile::tempdir().unwrap();
    let store_a = tmp.path().join("store-a/lmdb");
    let store_b = tmp.path().join("store-b/lmdb");
    let root_a = tmp.path().join("root-a");
    let root_b = tmp.path().join("root-b");
    let contract = tmp.path().join("gateway_contract.json");
    std::fs::create_dir_all(store_a.parent().unwrap()).unwrap();
    std::fs::create_dir_all(store_b.parent().unwrap()).unwrap();
    init_git_root(&root_a);
    init_git_root(&root_b);

    let port_a = free_port();
    let port_b = free_port();
    let port_g = free_port();
    let _backing_a = spawn_backing(&store_a, &root_a, port_a);
    let _backing_b = spawn_backing(&store_b, &root_b, port_b);
    wait_ready(port_a, "backing dev");
    wait_ready(port_b, "backing planning");

    // Seed each backing through its own supported write path (indexed).
    for (port, label) in [(port_a, "A"), (port_b, "B")] {
        let created = call_wm(
            port,
            "memory.create",
            serde_json::json!({"galaxy": "codex", "content": format!("q08 gateway canary {label}")}),
            None,
        );
        assert_eq!(created["status"], "success", "seed {label}: {created}");
    }

    let spec = format!("dev=http://127.0.0.1:{port_a},planning=http://127.0.0.1:{port_b}");
    let _gateway = spawn_gateway(&spec, port_g, &contract);
    wait_ready(port_g, "federated gateway");

    // 1. Federated read: fan out, merge, label both scopes.
    let read = call_wm(
        port_g,
        "memory.search",
        serde_json::json!({"query": "q08 gateway canary", "limit": 10}),
        None,
    );
    assert_eq!(read["federated"], true, "read: {read}");
    let queried: Vec<&str> = read["scopes_queried"]
        .as_array()
        .unwrap()
        .iter()
        .filter_map(|v| v.as_str())
        .collect();
    assert!(
        queried.contains(&"dev") && queried.contains(&"planning"),
        "{queried:?}"
    );
    assert_eq!(read["scopes_failed"].as_array().unwrap().len(), 0, "{read}");
    let labels: Vec<(String, String)> = read["results"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| {
            (
                r["scope"].as_str().unwrap_or_default().to_string(),
                r["id"].as_str().unwrap_or_default().to_string(),
            )
        })
        .collect();
    assert!(
        labels.iter().any(|(scope, _)| scope == "dev")
            && labels.iter().any(|(scope, _)| scope == "planning"),
        "both scopes must be labeled in the merged results: {labels:?}"
    );

    // 2. Pinned write through the gateway lands on `dev`, not `planning`.
    let lease = format!("q08-e2e/{}", std::process::id());
    let owner = "q08-e2e";
    let claim = call_wm(
        port_g,
        "code.claim",
        serde_json::json!({
            "scope": lease,
            "owner_session": owner,
            "intent": "Q08-G2 gateway scope-passthrough regression",
            "ttl_secs": 120,
        }),
        Some("dev"),
    );
    assert_eq!(claim["status"], "success", "claim: {claim}");
    let claim_text = claim.to_string();
    assert!(
        claim_text.contains(&lease),
        "claim must echo the lease: {claim}"
    );

    let direct = call_wm(
        port_a,
        "code.check",
        serde_json::json!({"scope": lease, "owner_session": owner}),
        None,
    );
    assert_eq!(direct["status"], "success", "direct check: {direct}");
    assert_ne!(
        direct["state"], "free",
        "the lease must be held on the `dev` backing: {direct}"
    );
    let other = call_wm(
        port_b,
        "code.check",
        serde_json::json!({"scope": lease, "owner_session": owner}),
        None,
    );
    // The other backing echoes the queried scope but reports it free: the
    // pinned write never landed there.
    assert_eq!(other["status"], "success", "other check: {other}");
    assert_eq!(
        other["state"], "free",
        "the pinned write must not land on the `planning` backing: {other}"
    );

    // 3. Release through the owning backing cleans up.
    let released = call_wm(
        port_a,
        "code.release",
        serde_json::json!({"scope": lease, "owner_session": owner}),
        None,
    );
    assert_eq!(released["status"], "success", "release: {released}");

    // 4. Unknown pinned scope fails closed, naming the reachable scopes.
    let refused = call_wm(
        port_g,
        "code.claim",
        serde_json::json!({
            "scope": "q08-e2e/never",
            "owner_session": owner,
            "intent": "must be refused",
            "ttl_secs": 60,
        }),
        Some("vault"),
    );
    assert_eq!(refused["error_code"], "unknown_scope", "refusal: {refused}");
    let message = refused.to_string();
    assert!(
        message.contains("dev") && message.contains("planning"),
        "refusal must name the reachable scopes: {refused}"
    );
}
