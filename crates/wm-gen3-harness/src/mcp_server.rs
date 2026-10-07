//! Gen3 MCP server core: shared backend/dispatch plus zero-dependency
//! HTTP and SSE transports.
//!
//! The backend is either a writable Gen3 `Substrate` or a read-only legacy
//! Gen2 mount (`compat::Gen2Reader`). One JSON-RPC handler serves stdio (from
//! the `wm` CLI), streamable HTTP (`POST /mcp`), and classic SSE
//! (`GET /sse` + `POST /messages`).
//!
//! Transports are built on `std::net` + threads only — the same house style
//! as `wm-gen3-core::transport` — so no async or HTTP crate is introduced.

use std::collections::HashMap;
use std::io::{self, Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, mpsc};
use std::time::{Duration, Instant};

use serde_json::{Value, json};

use wm_gen3_core::compat::Gen2Reader;
use wm_gen3_core::ops::Substrate;
use wm_gen3_core::{ContextCacheToken, ToolSchemaDefinition};

use crate::bridge::{
    McpProfile, execute_hybrid_tool_call, execute_legacy_tool_call, get_legacy_tools_list,
    get_tools_list_for_profile,
};

/// Build version — single source of truth is the workspace Cargo.toml.
pub const WM_VERSION: &str = env!("CARGO_PKG_VERSION");

const MAX_HTTP_HEAD: usize = 32 * 1024;
const MAX_HTTP_BODY: usize = 4 * 1024 * 1024;
const MAX_CONNECTIONS: usize = 64;
const SSE_KEEPALIVE: Duration = Duration::from_secs(15);
const IO_TIMEOUT: Duration = Duration::from_secs(30);

/// Network transports served over TCP.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NetworkTransport {
    /// Streamable HTTP: `POST /mcp` returns JSON (single or batch).
    Http,
    /// Classic SSE: `GET /sse` opens the event stream, `POST /messages` sends.
    Sse,
}

impl NetworkTransport {
    #[must_use]
    pub fn name(self) -> &'static str {
        match self {
            Self::Http => "http",
            Self::Sse => "sse",
        }
    }
}

/// One served MCP backend (writable Gen3 substrate or read-only Gen2 mount).
pub enum McpBackend {
    Gen3 {
        substrate: Box<Mutex<Substrate>>,
        store_path: PathBuf,
        profile: McpProfile,
        readonly: bool,
    },
    Legacy {
        reader: Gen2Reader,
        store_path: PathBuf,
        profile: McpProfile,
    },
}

impl McpBackend {
    #[must_use]
    pub fn gen3(
        substrate: Substrate,
        store_path: &Path,
        profile: McpProfile,
        readonly: bool,
    ) -> Self {
        Self::Gen3 {
            substrate: Box::new(Mutex::new(substrate)),
            store_path: store_path.to_path_buf(),
            profile,
            readonly,
        }
    }

    #[must_use]
    pub fn legacy(reader: Gen2Reader, store_path: &Path, profile: McpProfile) -> Self {
        Self::Legacy {
            reader,
            store_path: store_path.to_path_buf(),
            profile,
        }
    }

    #[must_use]
    pub fn legacy_mode(&self) -> bool {
        matches!(self, Self::Legacy { .. })
    }

    #[must_use]
    pub fn profile(&self) -> McpProfile {
        match self {
            Self::Gen3 { profile, .. } | Self::Legacy { profile, .. } => *profile,
        }
    }

    #[must_use]
    pub fn store_path(&self) -> &Path {
        match self {
            Self::Gen3 { store_path, .. } | Self::Legacy { store_path, .. } => store_path,
        }
    }

    #[must_use]
    pub fn readonly(&self) -> bool {
        match self {
            Self::Gen3 { readonly, .. } => *readonly,
            Self::Legacy { .. } => true,
        }
    }

    #[must_use]
    pub fn mode_name(&self) -> &'static str {
        match self {
            Self::Gen3 {
                readonly: false, ..
            } => "readwrite",
            Self::Gen3 { readonly: true, .. } => "readonly",
            Self::Legacy { .. } => "legacy-readonly",
        }
    }

    /// Handle one JSON-RPC request. Returns `None` for notifications.
    #[must_use]
    pub fn handle(&self, request: &Value) -> Option<Value> {
        // Notifications (no id) never receive a response (JSON-RPC 2.0).
        request.get("id")?;
        let id = request.get("id").cloned().unwrap_or(Value::Null);
        let method = request.get("method").and_then(Value::as_str).unwrap_or("");

        Some(match (method, self) {
            ("initialize", Self::Gen3 { profile, .. }) => json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": { "tools": {} },
                    "serverInfo": {
                        "name": "whitemagic-gen3",
                        "version": WM_VERSION,
                        "profile": profile_name(*profile)
                    }
                }
            }),
            (
                "initialize",
                Self::Legacy {
                    profile,
                    store_path,
                    ..
                },
            ) => json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": { "tools": {} },
                    "serverInfo": {
                        "name": "whitemagic-gen3",
                        "version": WM_VERSION,
                        "profile": profile_name(*profile),
                        "legacy": true,
                        "mode": "readonly",
                        "store": store_path.display().to_string()
                    },
                    "instructions": "Read-only Gen2 compatibility mount. Tools: memory.search/list/read/count/stats. Writes and session tools are unavailable; migrate with `wm migrate --source <legacy-dir>` for a writable Gen3 store."
                }
            }),
            ("ping", _) => json!({ "jsonrpc": "2.0", "id": id, "result": {} }),
            (
                "tools/list",
                Self::Gen3 {
                    substrate,
                    profile,
                    readonly,
                    ..
                },
            ) => {
                let tools = get_tools_list_for_profile(*profile, *readonly);
                let tool_schemas: Vec<ToolSchemaDefinition> = tools
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .map(|t| ToolSchemaDefinition {
                                name: t
                                    .get("name")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or("")
                                    .to_string(),
                                description: t
                                    .get("description")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or("")
                                    .to_string(),
                                parameters_schema: t
                                    .get("inputSchema")
                                    .map(|v| v.to_string())
                                    .unwrap_or_default(),
                            })
                            .collect()
                    })
                    .unwrap_or_default();
                let const_hash = [0u8; 32];
                let epoch = substrate
                    .lock()
                    .unwrap_or_else(|e| e.into_inner())
                    .store()
                    .epoch()
                    .unwrap_or(0);
                let cache_token = ContextCacheToken::compute(&tool_schemas, &const_hash, epoch);

                json!({
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "tools": tools,
                        "_meta": {
                            "profile": profile_name(*profile),
                            "context_cache_token": cache_token.cache_token,
                            "canonical_prefix_bytes": cache_token.canonical_prefix_bytes,
                            "estimated_prefix_tokens": cache_token.estimated_prefix_tokens,
                            "epoch": epoch
                        }
                    }
                })
            }
            ("tools/list", Self::Legacy { profile, .. }) => json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "tools": get_legacy_tools_list(),
                    "_meta": {
                        "profile": profile_name(*profile),
                        "legacy": true,
                        "readonly": true
                    }
                }
            }),
            (
                "tools/call",
                Self::Gen3 {
                    substrate,
                    store_path,
                    readonly,
                    profile,
                    ..
                },
            ) => {
                let name = request
                    .pointer("/params/name")
                    .and_then(Value::as_str)
                    .unwrap_or("");
                let empty_obj = Value::Object(serde_json::Map::new());
                let args = request
                    .pointer("/params/arguments")
                    .or_else(|| request.pointer("/params/input"))
                    .unwrap_or(&empty_obj);
                let result = {
                    // A poisoned substrate mutex must not wedge the server; recover
                    // the inner guard so later requests still make progress.
                    let mut guard = substrate.lock().unwrap_or_else(|e| e.into_inner());
                    execute_hybrid_tool_call(
                        name, args, &mut guard, store_path, *readonly, *profile,
                    )
                };
                tool_call_envelope(id, result)
            }
            ("tools/call", Self::Legacy { reader, .. }) => {
                let name = request
                    .pointer("/params/name")
                    .and_then(Value::as_str)
                    .unwrap_or("");
                let empty_obj = Value::Object(serde_json::Map::new());
                let args = request
                    .pointer("/params/arguments")
                    .or_else(|| request.pointer("/params/input"))
                    .unwrap_or(&empty_obj);
                tool_call_envelope(id, execute_legacy_tool_call(name, args, reader))
            }
            _ => json!({
                "jsonrpc": "2.0",
                "id": id,
                "error": { "code": -32601, "message": format!("unknown method: {method}") }
            }),
        })
    }
}

fn profile_name(profile: McpProfile) -> &'static str {
    match profile {
        McpProfile::Cyberbrain => "cyberbrain",
        McpProfile::Full => "full",
    }
}

fn tool_call_envelope(id: Value, result: Result<Value, String>) -> Value {
    match result {
        Ok(val) => json!({
            "jsonrpc": "2.0",
            "id": id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": serde_json::to_string_pretty(&val).unwrap_or_else(|_| val.to_string())
                    }
                ],
                "isError": false
            }
        }),
        Err(err_msg) => json!({
            "jsonrpc": "2.0",
            "id": id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": format!("Error: {err_msg}")
                    }
                ],
                "isError": true
            }
        }),
    }
}

/// Dispatch one HTTP body: single request or batch. `None` = notifications only.
#[must_use]
pub fn dispatch_json(backend: &McpBackend, body: &[u8]) -> Option<String> {
    let parsed = if body.len() > MAX_HTTP_BODY {
        Err(format!("request body exceeds {MAX_HTTP_BODY} byte limit"))
    } else {
        std::str::from_utf8(body)
            .map_err(|error| format!("request is not UTF-8: {error}"))
            .and_then(crate::receipt_verify::parse_strict_json)
    };
    let value: Value = match parsed {
        Ok(v) => v,
        Err(error) => {
            return Some(
                json!({
                    "jsonrpc": "2.0",
                    "id": null,
                    "error": { "code": -32700, "message": format!("parse error: {error}") }
                })
                .to_string(),
            );
        }
    };
    match value {
        Value::Array(items) => {
            let responses: Vec<Value> = items
                .iter()
                .filter_map(|request| backend.handle(request))
                .collect();
            if responses.is_empty() {
                None
            } else {
                Some(Value::Array(responses).to_string())
            }
        }
        other => backend.handle(&other).map(|response| response.to_string()),
    }
}

struct ServerCtx {
    backend: Arc<McpBackend>,
    sessions: Mutex<HashMap<String, mpsc::Sender<String>>>,
    active: AtomicUsize,
    auth_token: Option<String>,
}

/// Loopback-default bind policy for the network transports.
///
/// A non-loopback bind is refused unless `WM_SERVE_ALLOW_REMOTE=1` *and* a
/// bearer token is configured via `WM_SERVE_TOKEN`.
fn validate_network_bind(
    bind: SocketAddr,
    allow_remote: bool,
    has_token: bool,
) -> Result<(), String> {
    if bind.ip().is_loopback() {
        return Ok(());
    }
    if allow_remote && has_token {
        return Ok(());
    }
    Err(format!(
        "refusing non-loopback bind {bind}: set WM_SERVE_ALLOW_REMOTE=1 and WM_SERVE_TOKEN=<token> to expose the MCP server remotely"
    ))
}

/// Constant-time byte comparison (length is not secret).
fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut diff = 0u8;
    for (x, y) in a.iter().zip(b.iter()) {
        diff |= x ^ y;
    }
    diff == 0
}

/// `Authorization: Bearer <token>` check on the constant-time comparison path.
fn authorization_matches(header: Option<&str>, expected: &str) -> bool {
    let Some(value) = header else {
        return false;
    };
    let Some((scheme, credentials)) = value.split_once(' ') else {
        return false;
    };
    scheme.eq_ignore_ascii_case("bearer")
        && constant_time_eq(credentials.trim().as_bytes(), expected.as_bytes())
}

/// Serve a backend over TCP until SIGINT/SIGTERM or process exit.
///
/// On shutdown the listener stops accepting, in-flight connections are given a
/// short grace period to drain, and the process exits cleanly.
pub fn serve_network(backend: McpBackend, bind: SocketAddr, transport: NetworkTransport) -> ! {
    let token = std::env::var("WM_SERVE_TOKEN")
        .ok()
        .filter(|token| !token.is_empty());
    let allow_remote = std::env::var("WM_SERVE_ALLOW_REMOTE")
        .map(|v| v == "1")
        .unwrap_or(false);
    if let Err(e) = validate_network_bind(bind, allow_remote, token.is_some()) {
        eprintln!("gen3: {e}");
        std::process::exit(2);
    }

    let ctx = Arc::new(ServerCtx {
        backend: Arc::new(backend),
        sessions: Mutex::new(HashMap::new()),
        active: AtomicUsize::new(0),
        auth_token: token,
    });
    let listener = match TcpListener::bind(bind) {
        Ok(listener) => listener,
        Err(e) => {
            eprintln!("gen3: cannot bind {bind}: {e}");
            std::process::exit(1);
        }
    };
    if let Err(e) = listener.set_nonblocking(true) {
        eprintln!("gen3: cannot configure listener: {e}");
        std::process::exit(1);
    }
    eprintln!(
        "gen3: serve transport={} bind={} posture={} auth={} mode={} profile={} store={}",
        transport.name(),
        bind,
        if bind.ip().is_loopback() {
            "loopback"
        } else {
            "remote"
        },
        if ctx.auth_token.is_some() {
            "bearer-required"
        } else {
            "none"
        },
        ctx.backend.mode_name(),
        profile_name(ctx.backend.profile()),
        ctx.backend.store_path().display()
    );

    let shutdown = Arc::new(AtomicBool::new(false));
    #[cfg(unix)]
    {
        let _ = signal_hook::flag::register(signal_hook::consts::SIGINT, Arc::clone(&shutdown));
        let _ = signal_hook::flag::register(signal_hook::consts::SIGTERM, Arc::clone(&shutdown));
    }

    while !shutdown.load(Ordering::SeqCst) {
        match listener.accept() {
            Ok((stream, _peer)) => {
                if ctx.active.load(Ordering::SeqCst) >= MAX_CONNECTIONS {
                    let mut stream = stream;
                    let _ = write_response(
                        &mut stream,
                        "503 Service Unavailable",
                        "application/json",
                        br#"{"error":"connection limit reached"}"#,
                    );
                    continue;
                }
                ctx.active.fetch_add(1, Ordering::SeqCst);
                let ctx = Arc::clone(&ctx);
                std::thread::spawn(move || {
                    let _ = handle_conn(stream, &ctx, transport);
                    ctx.active.fetch_sub(1, Ordering::SeqCst);
                });
            }
            Err(ref e) if e.kind() == io::ErrorKind::WouldBlock => {
                std::thread::sleep(Duration::from_millis(10));
            }
            Err(e) => {
                eprintln!("gen3: accept failed: {e}");
                std::thread::sleep(Duration::from_millis(50));
            }
        }
    }

    let in_flight = ctx.active.load(Ordering::SeqCst);
    eprintln!("gen3: shutdown signal received; draining {in_flight} in-flight connection(s)");
    let deadline = Instant::now() + Duration::from_secs(5);
    while ctx.active.load(Ordering::SeqCst) > 0 && Instant::now() < deadline {
        std::thread::sleep(Duration::from_millis(10));
    }
    eprintln!("gen3: shutdown complete");
    std::process::exit(0);
}

fn handle_conn(
    mut stream: TcpStream,
    ctx: &ServerCtx,
    transport: NetworkTransport,
) -> io::Result<()> {
    stream.set_read_timeout(Some(IO_TIMEOUT))?;
    stream.set_write_timeout(Some(IO_TIMEOUT))?;

    let (method, target, headers) = match read_head(&mut stream) {
        Ok(Some(head)) => head,
        Ok(None) => return Ok(()),
        Err(e) => {
            let msg = json!({
                "jsonrpc": "2.0",
                "id": null,
                "error": { "code": -32600, "message": format!("bad request: {e}") }
            })
            .to_string();
            return write_response(
                &mut stream,
                "400 Bad Request",
                "application/json",
                msg.as_bytes(),
            );
        }
    };

    if let Some(token) = &ctx.auth_token {
        if !authorization_matches(headers.get("authorization").map(String::as_str), token) {
            return write_response(
                &mut stream,
                "401 Unauthorized",
                "application/json",
                br#"{"error":"missing or invalid bearer token"}"#,
            );
        }
    }

    let path = target.split('?').next().unwrap_or("");
    let query = target.split_once('?').map_or("", |(_, query)| query);

    match (method.as_str(), path) {
        ("GET", "/health") => {
            let body = json!({
                "status": "ok",
                "server": "whitemagic-gen3",
                "version": WM_VERSION,
                "transport": transport.name(),
                "mode": ctx.backend.mode_name(),
                "profile": profile_name(ctx.backend.profile()),
                "store": ctx.backend.store_path().display().to_string(),
            })
            .to_string();
            write_response(&mut stream, "200 OK", "application/json", body.as_bytes())
        }
        ("POST", "/mcp") if transport == NetworkTransport::Http => {
            let body = match read_body(&mut stream, &headers) {
                Ok(body) => body,
                Err(e) => {
                    let msg = json!({
                        "jsonrpc": "2.0",
                        "id": null,
                        "error": { "code": -32600, "message": format!("bad request: {e}") }
                    })
                    .to_string();
                    return write_response(
                        &mut stream,
                        "400 Bad Request",
                        "application/json",
                        msg.as_bytes(),
                    );
                }
            };
            match dispatch_json(&ctx.backend, &body) {
                Some(text) => {
                    write_response(&mut stream, "200 OK", "application/json", text.as_bytes())
                }
                None => write_response(&mut stream, "202 Accepted", "application/json", b""),
            }
        }
        ("GET", "/mcp") if transport == NetworkTransport::Http => write_response(
            &mut stream,
            "405 Method Not Allowed",
            "application/json",
            br#"{"error":"use POST /mcp; no standalone SSE stream is offered"}"#,
        ),
        ("DELETE", "/mcp") => write_response(
            &mut stream,
            "405 Method Not Allowed",
            "application/json",
            b"",
        ),
        ("GET", "/sse") if transport == NetworkTransport::Sse => handle_sse_stream(stream, ctx),
        ("POST", "/messages") if transport == NetworkTransport::Sse => {
            let session_id = query_param(query, "sessionId").unwrap_or_default();
            let body = match read_body(&mut stream, &headers) {
                Ok(body) => body,
                Err(e) => {
                    let msg = json!({
                        "jsonrpc": "2.0",
                        "id": null,
                        "error": { "code": -32600, "message": format!("bad request: {e}") }
                    })
                    .to_string();
                    return write_response(
                        &mut stream,
                        "400 Bad Request",
                        "application/json",
                        msg.as_bytes(),
                    );
                }
            };
            let sender = ctx
                .sessions
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .get(&session_id)
                .cloned();
            match sender {
                None => write_response(
                    &mut stream,
                    "404 Not Found",
                    "application/json",
                    br#"{"error":"unknown or expired session"}"#,
                ),
                Some(sender) => {
                    if let Some(text) = dispatch_json(&ctx.backend, &body) {
                        let _ = sender.send(text);
                    }
                    write_response(&mut stream, "202 Accepted", "application/json", b"")
                }
            }
        }
        _ => write_response(
            &mut stream,
            "404 Not Found",
            "application/json",
            br#"{"error":"not found"}"#,
        ),
    }
}

fn handle_sse_stream(mut stream: TcpStream, ctx: &ServerCtx) -> io::Result<()> {
    let session_id = uuid::Uuid::new_v4().to_string();
    let (sender, receiver) = mpsc::channel::<String>();
    ctx.sessions
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .insert(session_id.clone(), sender);

    stream.write_all(
        b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-cache\r\nConnection: keep-alive\r\n\r\n",
    )?;
    stream.write_all(
        format!("event: endpoint\ndata: /messages?sessionId={session_id}\n\n").as_bytes(),
    )?;
    stream.flush()?;

    loop {
        match receiver.recv_timeout(SSE_KEEPALIVE) {
            Ok(text) => {
                if stream
                    .write_all(format!("event: message\ndata: {text}\n\n").as_bytes())
                    .is_err()
                {
                    break;
                }
            }
            Err(mpsc::RecvTimeoutError::Timeout) => {
                // Heartbeat doubles as a liveness probe for dead clients.
                if stream.write_all(b": keepalive\n\n").is_err() {
                    break;
                }
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => break,
        }
        if stream.flush().is_err() {
            break;
        }
    }

    ctx.sessions
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .remove(&session_id);
    Ok(())
}

type RequestHead = (String, String, HashMap<String, String>);

fn read_head(stream: &mut TcpStream) -> io::Result<Option<RequestHead>> {
    let mut buf = Vec::with_capacity(1024);
    let mut byte = [0u8; 1];
    loop {
        let n = stream.read(&mut byte)?;
        if n == 0 {
            return Ok(None);
        }
        buf.push(byte[0]);
        if buf.len() > MAX_HTTP_HEAD {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "request head too large",
            ));
        }
        if buf.ends_with(b"\r\n\r\n") {
            break;
        }
    }
    let head = String::from_utf8_lossy(&buf);
    let mut lines = head.split("\r\n");
    let request_line = lines.next().unwrap_or("");
    let mut parts = request_line.split_whitespace();
    let method = parts.next().unwrap_or("").to_string();
    let target = parts.next().unwrap_or("").to_string();
    let version = parts.next().unwrap_or("");
    if method.is_empty() || target.is_empty() || !version.starts_with("HTTP/1.") {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "malformed request line",
        ));
    }
    let mut headers = HashMap::new();
    for line in lines {
        if let Some((key, value)) = line.split_once(':') {
            headers.insert(key.trim().to_ascii_lowercase(), value.trim().to_string());
        }
    }
    Ok(Some((method, target, headers)))
}

fn read_body(stream: &mut TcpStream, headers: &HashMap<String, String>) -> io::Result<Vec<u8>> {
    if let Some(te) = headers.get("transfer-encoding") {
        if te.to_ascii_lowercase().contains("chunked") {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "chunked transfer-encoding not supported",
            ));
        }
    }
    let length = headers
        .get("content-length")
        .and_then(|v| v.parse::<usize>().ok())
        .unwrap_or(0);
    if length > MAX_HTTP_BODY {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "request body too large",
        ));
    }
    let mut body = vec![0u8; length];
    stream.read_exact(&mut body)?;
    Ok(body)
}

fn write_response(
    stream: &mut TcpStream,
    status: &str,
    content_type: &str,
    body: &[u8],
) -> io::Result<()> {
    let head = format!(
        "HTTP/1.1 {status}\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        body.len()
    );
    stream.write_all(head.as_bytes())?;
    stream.write_all(body)?;
    stream.flush()
}

fn query_param(query: &str, key: &str) -> Option<String> {
    query.split('&').find_map(|pair| {
        let (k, v) = pair.split_once('=')?;
        (k == key).then(|| v.to_string())
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn network_dispatch_refuses_duplicate_malformed_and_oversized_raw_input() {
        let store = std::env::temp_dir().join(format!("wm-network-input-{}", uuid::Uuid::new_v4()));
        let substrate = Substrate::open(&store, None, wm_gen3_core::constitution::default_view())
            .expect("open isolated network fixture");
        let backend = McpBackend::gen3(substrate, &store, McpProfile::Full, false);
        let duplicated_receipt = br#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"receipts.verify","arguments":{"bundle":{"spec":"first","spec":"second"}}}}"#;
        let oversized = vec![b' '; MAX_HTTP_BODY + 1];
        for raw in [duplicated_receipt.as_slice(), b"\xff", oversized.as_slice()] {
            let response = dispatch_json(&backend, raw).expect("parse refusal");
            let value: Value = serde_json::from_str(&response).expect("response JSON");
            assert_eq!(value["id"], Value::Null);
            assert_eq!(value["error"]["code"], json!(-32700));
        }
        let ping = dispatch_json(&backend, br#"{"jsonrpc":"2.0","id":2,"method":"ping"}"#)
            .expect("next independent request succeeds");
        let value: Value = serde_json::from_str(&ping).expect("ping response");
        assert_eq!(value["id"], json!(2));
        assert_eq!(value["result"], json!({}));
        assert!(!store.join("mandala_gate_key.bin").exists());
        drop(backend);
        std::fs::remove_dir_all(store).expect("remove isolated network fixture");
    }

    const REAL_STORE: &str = "/home/lucas/wm-data/WMdata/projects/planning/lmdb";

    fn legacy_backend() -> Option<McpBackend> {
        if !Path::new(REAL_STORE).join("data.mdb").is_file() {
            eprintln!("skipping mcp_server test: {REAL_STORE} not present on this host");
            return None;
        }
        let reader = Gen2Reader::open(REAL_STORE).expect("open legacy store");
        Some(McpBackend::legacy(
            reader,
            Path::new(REAL_STORE),
            McpProfile::Full,
        ))
    }

    #[test]
    fn notifications_get_no_response() {
        let Some(backend) = legacy_backend() else {
            return;
        };
        assert!(
            backend
                .handle(&json!({"jsonrpc": "2.0", "method": "notifications/initialized"}))
                .is_none()
        );
    }

    #[test]
    fn legacy_backend_initialize_lists_read_only_surface() {
        let Some(backend) = legacy_backend() else {
            return;
        };
        let init = backend
            .handle(&json!({"jsonrpc": "2.0", "id": 1, "method": "initialize"}))
            .expect("initialize response");
        assert_eq!(init["result"]["serverInfo"]["legacy"], json!(true));
        assert_eq!(init["result"]["serverInfo"]["mode"], json!("readonly"));

        let list = backend
            .handle(&json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
            .expect("tools list");
        assert_eq!(list["result"]["tools"].as_array().map(Vec::len), Some(5));
        assert_eq!(list["result"]["_meta"]["legacy"], json!(true));

        let call = backend
            .handle(&json!({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": { "name": "memory.count", "arguments": {} }
            }))
            .expect("count response");
        assert_eq!(call["result"]["isError"], json!(false));

        let refused = backend
            .handle(&json!({
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": { "name": "memory.create", "arguments": { "content": "x" } }
            }))
            .expect("refusal response");
        assert_eq!(refused["result"]["isError"], json!(true));
    }

    #[test]
    fn dispatch_json_handles_batches_and_parse_errors() {
        let Some(backend) = legacy_backend() else {
            return;
        };
        let parse_error = dispatch_json(&backend, b"{not json").expect("parse error response");
        assert!(parse_error.contains("-32700"));

        let batch = br#"[
            {"jsonrpc":"2.0","id":1,"method":"ping"},
            {"jsonrpc":"2.0","method":"notifications/initialized"},
            {"jsonrpc":"2.0","id":2,"method":"ping"}
        ]"#;
        let response = dispatch_json(&backend, batch).expect("batch response");
        let value: Value = serde_json::from_str(&response).expect("valid batch JSON");
        assert_eq!(value.as_array().map(Vec::len), Some(2));

        let notification_only = br#"[{"jsonrpc":"2.0","method":"notifications/initialized"}]"#;
        assert!(dispatch_json(&backend, notification_only).is_none());
    }

    fn test_backend(tag: &str) -> (McpBackend, PathBuf) {
        let store = std::env::temp_dir().join(format!("wm-network-{tag}-{}", uuid::Uuid::new_v4()));
        let substrate = Substrate::open(&store, None, wm_gen3_core::constitution::default_view())
            .expect("open isolated network fixture");
        (
            McpBackend::gen3(substrate, &store, McpProfile::Full, false),
            store,
        )
    }

    fn test_ctx(backend: McpBackend, auth_token: Option<String>) -> Arc<ServerCtx> {
        Arc::new(ServerCtx {
            backend: Arc::new(backend),
            sessions: Mutex::new(HashMap::new()),
            active: AtomicUsize::new(0),
            auth_token,
        })
    }

    #[test]
    fn bind_guard_and_bearer_auth_policy() {
        let loopback: SocketAddr = "127.0.0.1:8787".parse().expect("addr");
        let wildcard: SocketAddr = "0.0.0.0:8787".parse().expect("addr");
        assert!(validate_network_bind(loopback, false, false).is_ok());
        assert!(
            validate_network_bind(wildcard, false, true).is_err(),
            "remote bind refused without WM_SERVE_ALLOW_REMOTE"
        );
        assert!(
            validate_network_bind(wildcard, true, false).is_err(),
            "remote bind refused without a token"
        );
        assert!(validate_network_bind(wildcard, true, true).is_ok());

        assert!(authorization_matches(Some("Bearer s3cret"), "s3cret"));
        assert!(authorization_matches(Some("bearer s3cret"), "s3cret"));
        assert!(!authorization_matches(Some("Bearer wrong"), "s3cret"));
        assert!(!authorization_matches(Some("Basic s3cret"), "s3cret"));
        assert!(!authorization_matches(
            Some("Bearer s3cret-extra"),
            "s3cret"
        ));
        assert!(!authorization_matches(None, "s3cret"));

        assert!(constant_time_eq(b"same", b"same"));
        assert!(!constant_time_eq(b"same", b"diff"));
        assert!(!constant_time_eq(b"short", b"longer"));
    }

    #[test]
    fn poisoned_substrate_mutex_is_recovered() {
        let (backend, store) = test_backend("poison");
        if let McpBackend::Gen3 { substrate, .. } = &backend {
            let _ = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                let _guard = substrate.lock().expect("first lock");
                panic!("poison the substrate mutex");
            }));
            assert!(substrate.is_poisoned(), "fixture must poison the mutex");
        } else {
            panic!("expected Gen3 backend");
        }

        let response = backend
            .handle(&json!({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": { "name": "memory.count", "arguments": {} }
            }))
            .expect("response after poison");
        assert_eq!(response["result"]["isError"], json!(false), "{response}");

        let list = backend
            .handle(&json!({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
            .expect("tools list after poison");
        assert!(
            list["result"]["tools"]
                .as_array()
                .map(|tools| !tools.is_empty())
                .unwrap_or(false)
        );

        drop(backend);
        std::fs::remove_dir_all(store).expect("remove isolated network fixture");
    }

    #[test]
    fn malformed_request_line_gets_http_400() {
        let (backend, store) = test_backend("malformed");
        let ctx = test_ctx(backend, None);
        let listener = TcpListener::bind("127.0.0.1:0").expect("listener");
        let addr = listener.local_addr().expect("addr");
        let server_ctx = Arc::clone(&ctx);
        let handle = std::thread::spawn(move || {
            let (stream, _) = listener.accept().expect("accept");
            let _ = handle_conn(stream, &server_ctx, NetworkTransport::Http);
        });

        let mut client = TcpStream::connect(addr).expect("connect");
        client
            .write_all(b"GARBAGE\r\n\r\n")
            .expect("write malformed request");
        let mut response = String::new();
        client.read_to_string(&mut response).expect("read response");
        handle.join().expect("server thread");

        assert!(
            response.starts_with("HTTP/1.1 400 Bad Request"),
            "malformed request lines must be answered, got: {response}"
        );
        drop(ctx);
        std::fs::remove_dir_all(store).expect("remove isolated network fixture");
    }

    #[test]
    fn bearer_token_gates_every_http_request() {
        let (backend, store) = test_backend("auth");
        let ctx = test_ctx(backend, Some("s3cret".to_string()));
        let listener = TcpListener::bind("127.0.0.1:0").expect("listener");
        let addr = listener.local_addr().expect("addr");
        let server_ctx = Arc::clone(&ctx);
        let handle = std::thread::spawn(move || {
            for _ in 0..2 {
                let (stream, _) = listener.accept().expect("accept");
                let _ = handle_conn(stream, &server_ctx, NetworkTransport::Http);
            }
        });

        let mut client = TcpStream::connect(addr).expect("connect");
        client
            .write_all(b"GET /health HTTP/1.1\r\nHost: local\r\n\r\n")
            .expect("write");
        let mut unauthorized = String::new();
        client
            .read_to_string(&mut unauthorized)
            .expect("read response");
        assert!(
            unauthorized.starts_with("HTTP/1.1 401 Unauthorized"),
            "missing token must be rejected, got: {unauthorized}"
        );

        let mut client = TcpStream::connect(addr).expect("connect");
        client
            .write_all(
                b"GET /health HTTP/1.1\r\nHost: local\r\nAuthorization: Bearer s3cret\r\n\r\n",
            )
            .expect("write");
        let mut authorized = String::new();
        client
            .read_to_string(&mut authorized)
            .expect("read response");
        assert!(
            authorized.starts_with("HTTP/1.1 200 OK"),
            "valid token must be accepted, got: {authorized}"
        );
        handle.join().expect("server thread");
        drop(ctx);
        std::fs::remove_dir_all(store).expect("remove isolated network fixture");
    }
}
