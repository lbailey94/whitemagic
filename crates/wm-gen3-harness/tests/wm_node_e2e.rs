//! End-to-end tests for `wm-node`: spawned binary over a real UDS, SIGTERM
//! cleanup, double-bind refusal, and the stdlib Python client driving the node.

use serde_json::{Value, json};
use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

fn unique_socket(tag: &str) -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    std::env::temp_dir().join(format!(
        "wm-node-e2e-{tag}-{}-{nanos}.sock",
        std::process::id()
    ))
}

fn spawn_node(socket: &Path) -> Child {
    Command::new(env!("CARGO_BIN_EXE_wm-node"))
        .arg("--socket")
        .arg(socket)
        .env_remove("WM_STORE")
        .env_remove("WM_NODE_SOCKET")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn wm-node")
}

fn wait_for_socket(path: &Path, timeout: Duration) {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if path.exists() {
            return;
        }
        std::thread::sleep(Duration::from_millis(10));
    }
    panic!(
        "socket {} did not appear within {timeout:?}",
        path.display()
    );
}

fn wait_for_exit(child: &mut Child, timeout: Duration) -> Option<std::process::ExitStatus> {
    let deadline = Instant::now() + timeout;
    loop {
        match child.try_wait() {
            Ok(Some(status)) => return Some(status),
            Ok(None) => {}
            Err(e) => panic!("try_wait failed: {e}"),
        }
        if Instant::now() >= deadline {
            return None;
        }
        std::thread::sleep(Duration::from_millis(20));
    }
}

fn terminate(child: &mut Child) -> std::process::ExitStatus {
    let _ = Command::new("kill")
        .arg("-TERM")
        .arg(child.id().to_string())
        .status();
    if let Some(status) = wait_for_exit(child, Duration::from_secs(5)) {
        return status;
    }
    let _ = child.kill();
    wait_for_exit(child, Duration::from_secs(5)).expect("child did not exit after SIGKILL")
}

fn rpc(socket: &Path, id: u64, method: &str, params: Value) -> Value {
    let stream = UnixStream::connect(socket).expect("connect to wm-node");
    stream
        .set_read_timeout(Some(Duration::from_secs(5)))
        .expect("set timeout");
    let mut writer = stream.try_clone().expect("clone stream");
    let mut reader = BufReader::new(stream);
    let request = json!({"jsonrpc": "2.0", "id": id, "method": method, "params": params});
    writer
        .write_all(request.to_string().as_bytes())
        .expect("write request");
    writer.write_all(b"\n").expect("write newline");
    writer.flush().expect("flush request");
    let mut line = String::new();
    reader.read_line(&mut line).expect("read response");
    serde_json::from_str(&line).expect("valid JSON response")
}

fn read_stderr(child: &mut Child) -> String {
    let mut text = String::new();
    if let Some(mut pipe) = child.stderr.take() {
        let _ = pipe.read_to_string(&mut text);
    }
    text
}

#[test]
fn spawned_node_serves_protocol_and_shuts_down_gracefully() {
    let socket = unique_socket("lifecycle");
    let mut child = spawn_node(&socket);
    wait_for_socket(&socket, Duration::from_secs(10));

    let mode = std::fs::metadata(&socket)
        .expect("stat socket")
        .permissions()
        .mode()
        & 0o777;
    assert_eq!(mode, 0o600, "spawned socket mode {mode:o}, expected 0600");

    let status = rpc(&socket, 1, "node.status", json!({}));
    assert_eq!(status["result"]["ok"], true, "status: {status}");
    assert_eq!(status["result"]["protocol"], "wm-node/1");

    let put = rpc(
        &socket,
        2,
        "tuple.put",
        json!({"kind": "Generic", "tag": "e2e", "payload": "hi", "ttl_ms": 60000}),
    );
    let id = put["result"]["id"].as_str().expect("put id").to_string();
    let get = rpc(
        &socket,
        3,
        "tuple.get",
        json!({"kind": "Generic", "tag": "e2e"}),
    );
    assert_eq!(get["result"]["count"], 1);
    let take = rpc(
        &socket,
        4,
        "tuple.take",
        json!({"kind": "Generic", "tag": "e2e"}),
    );
    assert_eq!(take["result"]["tuple"]["id"], id);

    let status = terminate(&mut child);
    assert!(
        status.success(),
        "wm-node must exit 0 on SIGTERM: {status:?}\n{}",
        read_stderr(&mut child)
    );
    assert!(!socket.exists(), "socket file must be removed on SIGTERM");
}

#[test]
fn spawned_second_node_refuses_double_bind() {
    let socket = unique_socket("double-bind");
    let mut first = spawn_node(&socket);
    wait_for_socket(&socket, Duration::from_secs(10));

    let mut second = spawn_node(&socket);
    let status = wait_for_exit(&mut second, Duration::from_secs(10));
    let status = match status {
        Some(status) => status,
        None => {
            let _ = second.kill();
            let _ = wait_for_exit(&mut second, Duration::from_secs(5));
            panic!("second wm-node did not exit after refusing the bind");
        }
    };
    let stderr = read_stderr(&mut second);
    assert!(!status.success(), "second node must fail: {status:?}");
    assert!(
        stderr.contains("already listening"),
        "expected a clear double-bind error, got: {stderr}"
    );

    // The first node is unharmed and still serving.
    let status_response = rpc(&socket, 1, "node.status", json!({}));
    assert_eq!(status_response["result"]["ok"], true);
    terminate(&mut first);
}

#[test]
fn spawned_node_refuses_regular_file_and_leaves_it_intact() {
    let path = unique_socket("not-a-socket").with_extension("txt");
    std::fs::write(&path, b"precious notes").expect("write regular file");

    let mut child = spawn_node(&path);
    let status = wait_for_exit(&mut child, Duration::from_secs(10));
    let status = match status {
        Some(status) => status,
        None => {
            let _ = child.kill();
            let _ = wait_for_exit(&mut child, Duration::from_secs(5));
            panic!("wm-node did not exit after refusing a non-socket path");
        }
    };
    let stderr = read_stderr(&mut child);
    assert!(
        !status.success(),
        "node must fail on a regular file: {status:?}"
    );
    assert!(
        stderr.contains("not a socket"),
        "expected a clear refusal, got: {stderr}"
    );
    assert!(path.exists(), "regular file must survive the refusal");
    assert_eq!(std::fs::read(&path).expect("read file"), b"precious notes");
    let _ = std::fs::remove_file(&path);
}

fn python3_available() -> bool {
    Command::new("python3")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

#[test]
fn python_client_drives_node() {
    if !python3_available() {
        eprintln!("skipping python_client_drives_node: python3 not available");
        return;
    }
    let script = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../scripts/wm_client.py");
    assert!(script.exists(), "missing {}", script.display());

    let socket = unique_socket("python");
    let mut child = spawn_node(&socket);
    wait_for_socket(&socket, Duration::from_secs(10));

    let run = |method: &str, params: &str| {
        let output = Command::new("python3")
            .arg(&script)
            .arg("--socket")
            .arg(&socket)
            .arg("call")
            .arg(method)
            .arg(params)
            .output()
            .expect("run wm_client.py");
        assert!(
            output.status.success(),
            "wm_client.py {method} failed:\n{}\n{}",
            String::from_utf8_lossy(&output.stderr),
            String::from_utf8_lossy(&output.stdout)
        );
        serde_json::from_slice::<Value>(&output.stdout).expect("wm_client.py stdout must be JSON")
    };

    let status = run("node.status", "{}");
    assert_eq!(status["result"]["ok"], true, "status: {status}");

    let put = run(
        "tuple.put",
        r#"{"kind":"Generic","tag":"py","payload":"hello","ttl_ms":60000}"#,
    );
    assert!(put["result"]["id"].is_string(), "put: {put}");

    let get = run("tuple.get", r#"{"kind":"Generic","tag":"py"}"#);
    assert_eq!(get["result"]["count"], 1, "get: {get}");

    terminate(&mut child);
}
