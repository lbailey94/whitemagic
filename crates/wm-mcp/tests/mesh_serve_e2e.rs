//! Sangha mesh R0 E2E — two real `wm serve --mesh` processes on one machine
//! must discover each other, bind signed identities, exchange verified
//! chat, and enforce the bad-apple rule (quarantine refuses chat and rejoin,
//! release restores the join path). This is the two-node local proof the
//! join protocol (`docs/MESH_JOIN_PROTOCOL.md`) is written from.
//!
//! Unix-only: both test cases bind loopback TCP listeners and spawn real
//! server processes, and every helper exists solely for those tests —
//! without this gate the helpers are dead code on Windows and trip
//! `deny(dead_code)` there.
#![cfg(unix)]

use std::io::{BufRead, BufReader, Read, Write};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc::{Receiver, channel};
use std::time::{Duration, Instant};

use wm_sangha::{ChatMessage, MeshKeyPair, PeerAuthority, PeerInfo};

struct ServeProcess {
    child: Child,
    stdin: std::process::ChildStdin,
    responses: Receiver<String>,
}

impl ServeProcess {
    /// Spawn `wm serve --mesh` on a throwaway store with a fixed identity.
    fn spawn(store_root: &std::path::Path, peer_id: &str, port: u16) -> Self {
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
            "full",
            "--mesh",
            "--mesh-bind",
            &format!("127.0.0.1:{port}"),
        ])
        .env("WM_MESH_KEY", format!("e2e-mesh-key-{peer_id}"))
        .env("WM_MESH_PEER_ID", peer_id)
        .env("WM_MESH_INTERVAL", "1")
        // Determinism: keep strict-mode (Ahimsa) outcomes independent of the
        // host's current load.
        .env("WM_HOMEOSTASIS_FROZEN", "1")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
        let mut child = cmd.spawn().expect("spawn wm serve --mesh");
        let stdin = child.stdin.take().expect("stdin");
        let stdout = child.stdout.take().expect("stdout");
        // Drain stdout on a dedicated thread: a wedged serve process must
        // surface as a timeout error here, not hang the whole CI job (a
        // blocking read_line has no deadline of its own).
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

    /// Call a `sangha.mesh.*` route; returns the parsed JSON content.
    fn mesh(&mut self, route: &str, args: &serde_json::Value, id: u64) -> serde_json::Value {
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

    /// Non-panicking variant for retry loops: `Ok` on a usable report,
    /// `Err` carrying the raw failure text on error responses or
    /// unparseable content (transient startup states) — so retry loops can
    /// surface *why* they kept failing instead of just timing out.
    fn try_mesh(
        &mut self,
        route: &str,
        args: &serde_json::Value,
        id: u64,
    ) -> Result<serde_json::Value, String> {
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
            .map(String::from);
        let content = match content {
            Some(c) => c,
            None => {
                return Err(format!("tools/call {route} returned no content: {resp}"));
            }
        };
        match serde_json::from_str::<serde_json::Value>(&content) {
            Ok(v) if v.get("status").and_then(serde_json::Value::as_str) != Some("error") => Ok(v),
            _ => Err(format!("tools/call {route} failed: {content}")),
        }
    }

    /// Call a route expecting an error result; returns the error text.
    fn mesh_err(&mut self, route: &str, args: &serde_json::Value, id: u64) -> String {
        let resp = self.rpc(
            "tools/call",
            &serde_json::json!({"name": "wm", "arguments": {"route": route, "args": args}}),
            id,
        );
        let text = resp
            .get("result")
            .and_then(|r| r.get("content"))
            .and_then(|c| c.as_array())
            .and_then(|a| a.first())
            .and_then(|c| c.get("text"))
            .and_then(|t| t.as_str())
            .unwrap_or("")
            .to_string();
        assert!(
            !text.is_empty(),
            "tools/call {route} must return content: {resp}"
        );
        text
    }
}

impl Drop for ServeProcess {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

fn handshake(server: &mut ServeProcess, client: &str, id: u64) {
    let init = server.rpc(
        "initialize",
        &serde_json::json!({
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": client, "version": "1.0"},
        }),
        id,
    );
    assert_eq!(
        init["result"]["serverInfo"]["name"], "whitemagic",
        "initialize handshake failed: {init}"
    );
}

/// Retry a fallible closure until it succeeds or the deadline passes.
fn wait_for<T>(what: &str, secs: u64, mut f: impl FnMut() -> Option<T>) -> T {
    let deadline = Instant::now() + Duration::from_secs(secs);
    loop {
        if let Some(v) = f() {
            return v;
        }
        assert!(
            Instant::now() < deadline,
            "{what} did not happen within {secs}s"
        );
        std::thread::sleep(Duration::from_millis(300));
    }
}

// ── Raw mesh-frame harness (S1 mesh phase 2) ─────────────────────────
//
// The mesh listener speaks length-prefixed JSON-RPC (`[4-byte BE len][JSON]`)
// directly, below the MCP/tool layer. These helpers let the phase-2 ingest
// gates (signed-only chat, heartbeat freshness/replay, envelope dedup,
// authority) be exercised on the wire exactly as a peer would.

/// A raw TCP connection to a live mesh listener.
struct RawMeshStream {
    stream: std::net::TcpStream,
}

impl RawMeshStream {
    /// Dial the mesh port, retrying while the server process boots.
    fn connect(port: u16) -> Self {
        let deadline = Instant::now() + Duration::from_secs(20);
        loop {
            match std::net::TcpStream::connect(format!("127.0.0.1:{port}")) {
                Ok(stream) => {
                    let _ = stream.set_read_timeout(Some(Duration::from_secs(15)));
                    let _ = stream.set_write_timeout(Some(Duration::from_secs(15)));
                    return Self { stream };
                }
                Err(e) => {
                    assert!(
                        Instant::now() < deadline,
                        "raw mesh connect to 127.0.0.1:{port} failed: {e}"
                    );
                    std::thread::sleep(Duration::from_millis(200));
                }
            }
        }
    }

    /// Send one framed JSON-RPC request and read the framed response.
    fn call(&mut self, method: &str, params: &serde_json::Value, id: u64) -> serde_json::Value {
        let req = serde_json::json!({"method": method, "params": params, "id": id});
        let bytes = serde_json::to_vec(&req).expect("serialize raw request");
        let len = u32::try_from(bytes.len()).expect("frame fits u32");
        self.stream
            .write_all(&len.to_be_bytes())
            .and_then(|()| self.stream.write_all(&bytes))
            .and_then(|()| self.stream.flush())
            .expect("write raw frame");
        let mut len_buf = [0u8; 4];
        self.stream
            .read_exact(&mut len_buf)
            .expect("read frame len");
        let len = u32::from_be_bytes(len_buf) as usize;
        let mut buf = vec![0u8; len];
        self.stream.read_exact(&mut buf).expect("read frame body");
        serde_json::from_slice(&buf).expect("parse raw response")
    }
}

/// A deterministic raw-frame client identity.
fn raw_client(peer_id: &str) -> MeshKeyPair {
    MeshKeyPair::from_seed(format!("raw-client-{peer_id}").as_bytes())
}

/// Signed heartbeat params for a raw client (identity + declared authority).
fn raw_heartbeat(
    keypair: &MeshKeyPair,
    peer_id: &str,
    authority: PeerAuthority,
) -> serde_json::Value {
    let mut peer = PeerInfo::new(peer_id, "127.0.0.1:1");
    peer.authority = authority;
    serde_json::to_value(peer.signed(keypair)).expect("serialize heartbeat")
}

/// Signed chat params matching what `send_chat_remote_with_envelope`
/// produces (the receiver verifies against this exact shape).
fn raw_chat(
    keypair: &MeshKeyPair,
    sender: &str,
    channel: &str,
    content: &str,
    envelope_id: &str,
    timestamp: i64,
) -> serde_json::Value {
    let msg = ChatMessage {
        id: 0,
        channel: channel.to_string(),
        sender: sender.to_string(),
        content: content.to_string(),
        timestamp,
        signature: String::new(),
        public_key: String::new(),
        envelope_id: envelope_id.to_string(),
    }
    .signed(keypair);
    serde_json::json!({
        "id": msg.id,
        "channel": msg.channel,
        "sender": msg.sender,
        "content": msg.content,
        "signature": msg.signature,
        "public_key": msg.public_key,
        "timestamp": msg.timestamp,
        "envelope_id": msg.envelope_id,
    })
}

/// Raw-frame heartbeat/chat ingest gates: a bound peer's heartbeat replays
/// are acknowledged without rebinding, stale heartbeats and unsigned chat
/// are refused, and a repeated envelope id is reported as a duplicate while
/// the channel log keeps exactly one copy.
#[cfg(unix)]
#[test]
fn raw_frame_heartbeat_replay_and_chat_dedup() {
    let store = tempfile::tempdir().expect("store");
    let _node = ServeProcess::spawn(store.path(), "raw-node-a", 17_415);
    let mut mesh = RawMeshStream::connect(17_415);
    let kp = raw_client("alpha");

    // Signed heartbeat binds on first sight.
    let heartbeat = raw_heartbeat(&kp, "raw-alpha", PeerAuthority::read_only());
    let resp = mesh.call("heartbeat", &heartbeat, 1);
    assert!(
        resp["error"].is_null(),
        "signed heartbeat must bind: {resp}"
    );

    // The exact same signed record again → acknowledged as a replay.
    let resp = mesh.call("heartbeat", &heartbeat, 2);
    assert_eq!(resp["result"]["replayed"], true, "{resp}");

    // A stale signed heartbeat (outside the registry timeout window) is
    // refused before any binding.
    let mut stale = PeerInfo::new("raw-alpha", "127.0.0.1:1");
    stale.last_seen = chrono::Utc::now().timestamp() - 3600;
    let stale = serde_json::to_value(stale.signed(&kp)).expect("serialize stale");
    let resp = mesh.call("heartbeat", &stale, 3);
    assert_eq!(resp["error"], "stale heartbeat rejected", "{resp}");

    // Unsigned chat is refused outright over the mesh transport.
    let unsigned = serde_json::json!({
        "channel": "raw",
        "sender": "raw-alpha",
        "content": "unsigned relay",
    });
    let resp = mesh.call("send_chat", &unsigned, 4);
    assert_eq!(
        resp["error"], "unsigned chat is not accepted over the mesh transport",
        "{resp}"
    );

    // Signed fresh chat stores; the same envelope id is deduped.
    let envelope = ChatMessage::new_envelope_id("raw-alpha");
    let chat = raw_chat(
        &kp,
        "raw-alpha",
        "raw",
        "exactly once",
        &envelope,
        chrono::Utc::now().timestamp_millis(),
    );
    let resp = mesh.call("send_chat", &chat, 5);
    assert_eq!(resp["result"]["duplicate"], false, "{resp}");
    let resp = mesh.call("send_chat", &chat, 6);
    assert_eq!(resp["result"]["duplicate"], true, "{resp}");
}

/// Raw-frame authority gates: an unbound claimant is distinguished from a
/// bound peer whose stored authority withholds execution; signal and lock
/// paths enforce the same stored-authority check.
#[cfg(unix)]
#[test]
fn raw_frame_binding_and_authority_gates() {
    let store = tempfile::tempdir().expect("store");
    let _node = ServeProcess::spawn(store.path(), "raw-node-b", 17_416);
    let mut mesh = RawMeshStream::connect(17_416);
    let now = chrono::Utc::now().timestamp_millis();

    // Chat from a never-bound sender → "not identity-bound".
    let ghost = raw_client("ghost");
    let chat = raw_chat(&ghost, "raw-ghost", "raw", "let me in", "env-ghost", now);
    let resp = mesh.call("send_chat", &chat, 1);
    let err = resp["error"].as_str().unwrap_or_default().to_string();
    assert!(err.contains("not identity-bound"), "{resp}");

    // A peer that self-declares `PeerAuthority::none()` binds fine, but
    // every execution-class path refuses it with the authority error.
    let no_exec = raw_client("noexec");
    let heartbeat = raw_heartbeat(&no_exec, "raw-noexec", PeerAuthority::none());
    let resp = mesh.call("heartbeat", &heartbeat, 2);
    assert!(resp["error"].is_null(), "{resp}");

    let chat = raw_chat(
        &no_exec,
        "raw-noexec",
        "raw",
        "not allowed",
        "env-noexec",
        now,
    );
    let resp = mesh.call("send_chat", &chat, 3);
    let err = resp["error"].as_str().unwrap_or_default().to_string();
    assert!(err.contains("lacks can_execute authority"), "{resp}");

    let lock = serde_json::json!({
        "resource": "memory:galaxy:codex",
        "holder": "raw-noexec",
        "ttl_sec": 30,
    });
    let resp = mesh.call("acquire_lock", &lock, 4);
    let err = resp["error"].as_str().unwrap_or_default().to_string();
    assert!(err.contains("lacks can_execute authority"), "{resp}");

    // Signals carry no signature: the gate enforces the CLAIMED source's
    // stored authority (an unbound claim is still refused).
    let signal = serde_json::json!({
        "id": 0,
        "signal_type": "peer_status",
        "source": "raw-ghost",
        "payload": {"status": "online"},
        "timestamp": now,
        "importance": 0.5,
    });
    let resp = mesh.call("broadcast_signal", &signal, 5);
    let err = resp["error"].as_str().unwrap_or_default().to_string();
    assert!(err.contains("not identity-bound"), "{resp}");
}

// Unix-gated: both e2e tests wedge on Windows CI runners (UDP multicast
// discovery never completes, rpc() hits its 30s timeout — 2026-09-02 reds
// on f550abe, classified pre-existing during earlier review). Root
// cause is Windows multicast support, tracked with the WM_MESH_MULTICAST_GROUP
// work on the alpha.8.x train; until then these
// run on Linux/macOS only rather than block Windows CI on an env difference.
#[cfg(unix)]
#[test]
fn two_serve_nodes_discover_chat_and_quarantine() {
    let store_a = tempfile::tempdir().expect("store a");
    let store_b = tempfile::tempdir().expect("store b");
    let mut a = ServeProcess::spawn(store_a.path(), "e2e-node-a", 17_411);
    let mut b = ServeProcess::spawn(store_b.path(), "e2e-node-b", 17_412);
    handshake(&mut a, "mesh-e2e-a", 1);
    handshake(&mut b, "mesh-e2e-b", 1);

    // 1. Both nodes disclose a live mesh through /status-equivalent tool.
    let status_a = a.mesh("sangha.mesh.status", &serde_json::json!({}), 2);
    assert_eq!(status_a["enabled"], true, "A mesh status: {status_a}");
    assert_eq!(status_a["peer_id"], "e2e-node-a", "{status_a}");
    assert_eq!(status_a["announce"], "127.0.0.1:17411", "{status_a}");
    assert_eq!(status_a["public_key"].as_str().map(str::len), Some(64));

    // 2. DISCOVER + BIND: A joins B — the signed heartbeat registers A's
    //    identity on B (remote_registry reflects B's view after the bind).
    //    Each failed attempt carries the tool's error text; the timeout
    //    panic surfaces the last one so CI logs name the actual failure.
    let deadline = Instant::now() + Duration::from_secs(30);
    let mut last_err;
    let joined = loop {
        match a.try_mesh(
            "sangha.mesh.join",
            &serde_json::json!({"address": "127.0.0.1:17412"}),
            3,
        ) {
            Ok(report) => match report.get("remote_registry") {
                Some(registry) => break registry.clone(),
                None => last_err = format!("join report has no remote_registry: {report}"),
            },
            Err(err) => last_err = err,
        }
        assert!(
            Instant::now() < deadline,
            "A join B did not happen within 30s — last error: {last_err}"
        );
        std::thread::sleep(Duration::from_millis(300));
    };
    // B's registry must contain A (the signed heartbeat bound it), and must
    // never contain B itself: multicast loopback delivers a node's own
    // beacon back to its listener, and a self-entry is a registry bug.
    let peers = joined["peers"].as_array().cloned().unwrap_or_default();
    assert!(
        peers.iter().any(|p| p["id"] == "e2e-node-a"),
        "B must have registered A: {joined}"
    );
    assert!(
        peers.iter().all(|p| p["id"] != "e2e-node-b"),
        "a node must never register itself in its own registry: {joined}"
    );

    // 3. CHAT: signed message from A lands on B and verifies.
    let sent = a.mesh(
        "sangha.mesh.chat",
        &serde_json::json!({
            "peer": "127.0.0.1:17412",
            "channel": "gana:room",
            "content": "two-node proof: hello from A",
        }),
        4,
    );
    assert_eq!(sent["status"], "ok", "{sent}");
    let inbox = wait_for("B receives the chat", 15, || {
        let read = b.mesh(
            "sangha.mesh.read",
            &serde_json::json!({"channel": "gana:room"}),
            5,
        );
        (read["count"].as_u64()? >= 1).then_some(read)
    });
    assert_eq!(inbox["messages"][0]["sender"], "e2e-node-a");
    assert_eq!(
        inbox["messages"][0]["content"],
        "two-node proof: hello from A"
    );

    // 4. QUARANTINE: B cuts A off — registry quarantine (rejoin refused),
    //    messages purged, locks revoked, connection dropped.
    let q = b.mesh(
        "sangha.mesh.quarantine",
        &serde_json::json!({
            "action": "quarantine",
            "peer_id": "e2e-node-a",
            "reason": "R0 E2E: simulated bad apple",
        }),
        6,
    );
    assert_eq!(q["quarantined"], true, "{q}");
    let listed = b.mesh(
        "sangha.mesh.quarantine",
        &serde_json::json!({"action": "list"}),
        7,
    );
    assert_eq!(
        listed["quarantined"][0]["peer_id"], "e2e-node-a",
        "{listed}"
    );

    // A's further chat is refused at ingest (bad-apple rule).
    let refused = a.mesh_err(
        "sangha.mesh.chat",
        &serde_json::json!({
            "peer": "127.0.0.1:17412",
            "channel": "gana:room",
            "content": "let me back in",
        }),
        8,
    );
    assert!(
        refused.contains("quarantined") || refused.contains("rejected"),
        "quarantine must refuse the message: {refused}"
    );

    // A fresh join attempt hits the rejoin refusal.
    let rejoin = a.mesh_err(
        "sangha.mesh.join",
        &serde_json::json!({"address": "127.0.0.1:17412"}),
        9,
    );
    assert!(
        rejoin.contains("quarantined") || rejoin.contains("rejected"),
        "quarantined peer must not re-register: {rejoin}"
    );

    // 5. RELEASE restores the join path (rejoin succeeds again).
    let released = b.mesh(
        "sangha.mesh.quarantine",
        &serde_json::json!({"action": "release", "peer_id": "e2e-node-a"}),
        10,
    );
    assert_eq!(released["released"], true, "{released}");
    let rejoined = wait_for("A rejoin B after release", 30, || {
        a.try_mesh(
            "sangha.mesh.join",
            &serde_json::json!({"address": "127.0.0.1:17412"}),
            11,
        )
        .ok()?
        .get("remote_registry")
        .cloned()
    });
    assert!(rejoined["peer_count"].as_u64().is_some(), "{rejoined}");

    // 6. Mesh status on B reflects the restored relationship (A in the
    //    registry, not quarantined).
    let status_b = wait_for("B status shows A registered again", 15, || {
        let s = b
            .try_mesh("sangha.mesh.status", &serde_json::json!({}), 12)
            .ok()?;
        (s["peers"]["peer_count"].as_u64()? >= 1).then_some(s)
    });
    assert_eq!(status_b["peer_id"], "e2e-node-b", "{status_b}");
}

/// The fleet-night retest protocol (2026-08-31), as a
/// permanent regression test: a peer-side process death used to poison the
/// survivor's connection entry — chat broke, rejoin was blocked by the
/// connected-peers guard, and a live peer returning to the same address was
/// shadowed by the ghost until restart. With evict-on-IO-error and
/// fresh-dial joins, the survivor must self-heal: the dead entry evicts on
/// the first failed rpc, and the returning peer reconnects cleanly.
#[cfg(unix)]
#[test]
fn dead_peer_connection_does_not_poison_rejoin() {
    let store_a = tempfile::tempdir().expect("store survivor");
    let store_b = tempfile::tempdir().expect("store victim");
    let mut a = ServeProcess::spawn(store_a.path(), "e2e-survivor", 17_413);
    let mut b = ServeProcess::spawn(store_b.path(), "e2e-victim", 17_414);
    handshake(&mut a, "mesh-e2e-retest-a", 1);
    handshake(&mut b, "mesh-e2e-retest-b", 1);

    // 1. Baseline: survivor joins victim and a signed chat lands.
    wait_for("survivor joins victim", 30, || {
        a.try_mesh(
            "sangha.mesh.join",
            &serde_json::json!({"address": "127.0.0.1:17414"}),
            2,
        )
        .ok()?
        .get("remote_registry")
        .cloned()
    });
    wait_for("baseline chat lands on victim", 20, || {
        a.try_mesh(
            "sangha.mesh.chat",
            &serde_json::json!({
                "peer": "127.0.0.1:17414",
                "channel": "retest",
                "content": "before the kill",
            }),
            3,
        )
        .ok()?;
        b.try_mesh(
            "sangha.mesh.read",
            &serde_json::json!({"channel": "retest"}),
            4,
        )
        .ok()?
        .get("count")
        .and_then(serde_json::Value::as_u64)
        .filter(|c| *c >= 1)
        .map(|_| ())
    });

    // 2. KILL the victim mid-session (process death, the defect class).
    let _ = b.child.kill();
    let _ = b.child.wait();

    // 3. The survivor's chat to the dead victim must QUEUE (S3 mail slot:
    //    agent_asleep, stored for delivery on rejoin) — and the dead
    //    connection must evict, not poison.
    wait_for("chat to dead victim queues", 20, || {
        a.try_mesh(
            "sangha.mesh.chat",
            &serde_json::json!({
                "peer": "127.0.0.1:17414",
                "channel": "retest",
                "content": "into the void",
            }),
            5,
        )
        .ok()?
        .get("queued")
        .and_then(serde_json::Value::as_bool)
        .filter(|q| *q)
        .map(|_| ())
    });
    wait_for("dead connection evicted from survivor", 15, || {
        let s = a
            .try_mesh("sangha.mesh.status", &serde_json::json!({}), 6)
            .ok()?;
        let connected = s["connected"].as_array()?;
        (!connected
            .iter()
            .any(|k| k.as_str().is_some_and(|k| k.contains("17414"))))
        .then_some(())
    });

    // 4. The victim returns (same store, same identity, same address —
    //    the exact scenario the ghost used to shadow).
    let mut b2 = ServeProcess::spawn(store_b.path(), "e2e-victim", 17_414);
    handshake(&mut b2, "mesh-e2e-retest-b2", 1);

    // 5. Rejoin must succeed (fresh dial) — and the rejoin FLUSHES the
    //    mail slot: the message queued while the victim was down lands on
    //    its return, alongside the live chat that follows.
    wait_for("survivor rejoins returned victim", 30, || {
        a.try_mesh(
            "sangha.mesh.join",
            &serde_json::json!({"address": "127.0.0.1:17414"}),
            7,
        )
        .ok()?
        .get("remote_registry")
        .cloned()
    });
    wait_for("queued + live chat land on returned victim", 20, || {
        a.try_mesh(
            "sangha.mesh.chat",
            &serde_json::json!({
                "peer": "127.0.0.1:17414",
                "channel": "retest",
                "content": "after the return",
            }),
            8,
        )
        .ok()?;
        b2.try_mesh(
            "sangha.mesh.read",
            &serde_json::json!({"channel": "retest"}),
            9,
        )
        .ok()?
        .get("messages")
        .and_then(serde_json::Value::as_array)
        .map(|msgs| {
            msgs.iter().any(|m| m["content"] == "into the void")
                && msgs.iter().any(|m| m["content"] == "after the return")
        })
        .filter(|found| *found)
        .map(|_| ())
    });
    // The mail slot drained.
    let mail = a.mesh(
        "sangha.mesh.mail",
        &serde_json::json!({"action": "list"}),
        10,
    );
    assert_eq!(mail["queued_total"], 0, "{mail}");
}
