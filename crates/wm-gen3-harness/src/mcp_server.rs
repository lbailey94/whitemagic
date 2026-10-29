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
use wm_gen3_core::firebreak::{Firebreak, FirebreakGate};
use wm_gen3_core::ops::Substrate;
use wm_gen3_core::{ContextCacheToken, ToolSchemaDefinition};

use crate::bridge::{
    McpProfile, execute_hybrid_tool_call, execute_legacy_tool_call, get_legacy_tools_list,
    get_tools_list_for_profile,
};

/// Build version — single source of truth is the workspace Cargo.toml.
pub const WM_VERSION: &str = env!("CARGO_PKG_VERSION");
const MODERN_PROTOCOL_VERSION: &str = "2026-07-28";
const LEGACY_PROTOCOL_VERSION: &str = "2024-11-05";
const LEGACY_PROTOCOL_VERSIONS: &[&str] = &["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"];
const SUPPORTED_PROTOCOL_VERSIONS: &[&str] = &[MODERN_PROTOCOL_VERSION, LEGACY_PROTOCOL_VERSION];
const PROTOCOL_VERSION_META: &str = "io.modelcontextprotocol/protocolVersion";
const CLIENT_CAPABILITIES_META: &str = "io.modelcontextprotocol/clientCapabilities";
const CLIENT_INFO_META: &str = "io.modelcontextprotocol/clientInfo";

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
        firebreak: Firebreak,
    },
    Legacy {
        reader: Gen2Reader,
        store_path: PathBuf,
        profile: McpProfile,
        firebreak: Firebreak,
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
        let firebreak = Firebreak::promoted();
        log_firebreak_arm_state(&firebreak);
        Self::Gen3 {
            substrate: Box::new(Mutex::new(substrate)),
            store_path: store_path.to_path_buf(),
            profile,
            readonly,
            firebreak,
        }
    }

    #[must_use]
    pub fn legacy(reader: Gen2Reader, store_path: &Path, profile: McpProfile) -> Self {
        let firebreak = Firebreak::promoted();
        log_firebreak_arm_state(&firebreak);
        Self::Legacy {
            reader,
            store_path: store_path.to_path_buf(),
            profile,
            firebreak,
        }
    }

    #[must_use]
    pub fn firebreak(&self) -> &Firebreak {
        match self {
            Self::Gen3 { firebreak, .. } | Self::Legacy { firebreak, .. } => firebreak,
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
        if request.is_array() && contains_modern_request(request) {
            return Some(json_rpc_error(
                Value::Null,
                -32600,
                "stdio accepts one JSON-RPC message per line",
                None,
            ));
        }
        let method = request.get("method").and_then(Value::as_str).unwrap_or("");
        let modern = has_modern_metadata(request) || method == "server/discover";
        let Some(id) = request.get("id").cloned() else {
            // Modern methods require a JSON-RPC request ID. Legacy notifications
            // remain no-response messages per JSON-RPC 2.0.
            return modern
                .then(|| json_rpc_error(Value::Null, -32600, "invalid JSON-RPC request", None));
        };

        if modern {
            if let Err((code, message)) = validate_modern_jsonrpc(request) {
                return Some(json_rpc_error(Value::Null, code, message, None));
            }
            if let Err((code, message, data)) = validate_modern_request(request) {
                return Some(json_rpc_error(id, code, message, data));
            }
        }

        if modern && method == "server/discover" {
            return Some(json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "resultType": "complete",
                    "supportedVersions": SUPPORTED_PROTOCOL_VERSIONS,
                    "capabilities": { "tools": {} },
                    "ttlMs": 0,
                    "cacheScope": "private",
                    "_meta": {
                        "io.modelcontextprotocol/serverInfo": {
                            "name": "whitemagic-gen3",
                            "version": WM_VERSION
                        }
                    }
                }
            }));
        }
        if modern && method == "initialize" {
            return Some(json_rpc_error(
                id,
                -32601,
                "initialize is only available to legacy clients",
                None,
            ));
        }

        let mut response = match (method, self) {
            ("initialize", Self::Gen3 { profile, .. }) => json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "protocolVersion": LEGACY_PROTOCOL_VERSION,
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
                    "protocolVersion": LEGACY_PROTOCOL_VERSION,
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
            ("ping", _) if !modern => json!({ "jsonrpc": "2.0", "id": id, "result": {} }),
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

                let result = if modern {
                    json!({
                        "resultType": "complete",
                        "tools": tools,
                        "ttlMs": 0,
                        "cacheScope": "private",
                        "_meta": {
                            "profile": profile_name(*profile),
                            "context_cache_token": cache_token.cache_token,
                            "canonical_prefix_bytes": cache_token.canonical_prefix_bytes,
                            "estimated_prefix_tokens": cache_token.estimated_prefix_tokens,
                            "epoch": epoch
                        }
                    })
                } else {
                    json!({
                        "tools": tools,
                        "_meta": {
                            "profile": profile_name(*profile),
                            "context_cache_token": cache_token.cache_token,
                            "canonical_prefix_bytes": cache_token.canonical_prefix_bytes,
                            "estimated_prefix_tokens": cache_token.estimated_prefix_tokens,
                            "epoch": epoch
                        }
                    })
                };
                json!({
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": result
                })
            }
            ("tools/list", Self::Legacy { profile, .. }) => {
                let result = if modern {
                    json!({
                        "resultType": "complete",
                        "tools": get_legacy_tools_list(),
                        "ttlMs": 0,
                        "cacheScope": "private",
                        "_meta": { "profile": profile_name(*profile), "legacy": true, "readonly": true }
                    })
                } else {
                    json!({
                        "tools": get_legacy_tools_list(),
                        "_meta": { "profile": profile_name(*profile), "legacy": true, "readonly": true }
                    })
                };
                json!({ "jsonrpc": "2.0", "id": id, "result": result })
            }
            (
                "tools/call",
                Self::Gen3 {
                    substrate,
                    store_path,
                    readonly,
                    profile,
                    firebreak,
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
                // Firebreak seam: forbidden → refuse (even with confirm);
                // dangerous → require `confirm: true`; caution → pass with
                // advisories. The gate runs before the bridge is touched.
                let (verdict, advisories, result) = match firebreak.gate(name, args) {
                    FirebreakGate::Pass {
                        verdict,
                        advisories,
                    } => {
                        let result = {
                            // A poisoned substrate mutex must not wedge the server;
                            // recover the inner guard so later requests still make
                            // progress.
                            let mut guard = substrate.lock().unwrap_or_else(|e| e.into_inner());
                            execute_hybrid_tool_call(
                                name, args, &mut guard, store_path, *readonly, *profile,
                            )
                        };
                        (verdict, advisories, result)
                    }
                    FirebreakGate::Refuse {
                        verdict,
                        message,
                        advisories,
                    } => (verdict, advisories, Err(message)),
                };
                let disclosure = Firebreak::is_on_seam(name)
                    .then(|| firebreak_disclosure(firebreak, verdict, advisories));
                tool_call_envelope(id, result, disclosure, modern)
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
                tool_call_envelope(
                    id,
                    execute_legacy_tool_call(name, args, reader),
                    None,
                    modern,
                )
            }
            _ => json!({
                "jsonrpc": "2.0",
                "id": id,
                "error": { "code": -32601, "message": format!("unknown method: {method}") }
            }),
        };
        if modern {
            if let Some(result) = response.get_mut("result").and_then(Value::as_object_mut) {
                let metadata = result.entry("_meta").or_insert_with(|| json!({}));
                if let Some(meta) = metadata.as_object_mut() {
                    meta.insert(
                        "io.modelcontextprotocol/serverInfo".into(),
                        json!({ "name": "whitemagic-gen3", "version": WM_VERSION }),
                    );
                }
            }
        }
        Some(response)
    }
}

fn profile_name(profile: McpProfile) -> &'static str {
    match profile {
        McpProfile::Cyberbrain => "cyberbrain",
        McpProfile::Full => "full",
    }
}

fn json_rpc_error(id: Value, code: i64, message: impl Into<String>, data: Option<Value>) -> Value {
    let mut error = json!({ "code": code, "message": message.into() });
    if let Some(data) = data {
        error["data"] = data;
    }
    json!({ "jsonrpc": "2.0", "id": id, "error": error })
}

fn validate_modern_jsonrpc(request: &Value) -> Result<(), (i64, String)> {
    let valid_id = request.get("id").is_some_and(|id| {
        id.is_string()
            || id
                .as_i64()
                .is_some_and(|number| number.unsigned_abs() <= 9_007_199_254_740_991)
            || id
                .as_u64()
                .is_some_and(|number| number <= 9_007_199_254_740_991)
    });
    if request.get("jsonrpc").and_then(Value::as_str) != Some("2.0")
        || !valid_id
        || request.get("method").and_then(Value::as_str).is_none()
    {
        return Err((-32600, "invalid JSON-RPC request".into()));
    }
    Ok(())
}

fn validate_modern_request(request: &Value) -> Result<(), (i64, String, Option<Value>)> {
    let Some(params) = request.get("params").and_then(Value::as_object) else {
        return Err((
            -32602,
            "modern request params must be an object".into(),
            None,
        ));
    };
    let Some(meta) = params.get("_meta").and_then(Value::as_object) else {
        return Err((
            -32602,
            "modern request metadata must be an object".into(),
            None,
        ));
    };
    let Some(version) = meta.get(PROTOCOL_VERSION_META).and_then(Value::as_str) else {
        return Err((-32602, "protocolVersion metadata is required".into(), None));
    };
    if version != MODERN_PROTOCOL_VERSION {
        return Err((
            -32022,
            "Unsupported protocol version".into(),
            Some(json!({ "supported": SUPPORTED_PROTOCOL_VERSIONS, "requested": version })),
        ));
    }
    if !meta
        .get(CLIENT_CAPABILITIES_META)
        .is_some_and(valid_client_capabilities)
    {
        return Err((
            -32602,
            "clientCapabilities metadata does not match the protocol schema".into(),
            None,
        ));
    }
    let method = request.get("method").and_then(Value::as_str).unwrap_or("");
    let Some(params) = request.get("params").and_then(Value::as_object) else {
        return Err((-32602, "request params must be an object".into(), None));
    };
    if method == "tools/call" {
        if !params.get("name").is_some_and(Value::is_string)
            || params
                .get("arguments")
                .is_some_and(|arguments| !arguments.is_object())
        {
            return Err((
                -32602,
                "tools/call requires a string name and object arguments".into(),
                None,
            ));
        }
    }
    if method == "tools/list"
        && params
            .get("cursor")
            .is_some_and(|cursor| !cursor.is_string())
    {
        return Err((-32602, "tools/list cursor must be a string".into(), None));
    }
    if let Some(client_info) = meta.get(CLIENT_INFO_META) {
        if !client_info.is_object()
            || !client_info.get("name").is_some_and(Value::is_string)
            || !client_info.get("version").is_some_and(Value::is_string)
        {
            return Err((
                -32602,
                "clientInfo metadata must include string name and version".into(),
                None,
            ));
        }
    }
    Ok(())
}

fn valid_client_capabilities(value: &Value) -> bool {
    let Some(capabilities) = value.as_object() else {
        return false;
    };
    for field in [
        "experimental",
        "roots",
        "sampling",
        "elicitation",
        "extensions",
    ] {
        if let Some(value) = capabilities.get(field) {
            if !value.is_object() {
                return false;
            }
        }
    }
    for map_field in ["experimental", "extensions"] {
        if let Some(map) = capabilities.get(map_field).and_then(Value::as_object) {
            if map.values().any(|entry| !entry.is_object()) {
                return false;
            }
        }
    }
    for (container, fields) in [
        ("sampling", &["context", "tools"][..]),
        ("elicitation", &["form", "url"][..]),
    ] {
        if let Some(object) = capabilities.get(container).and_then(Value::as_object) {
            if fields
                .iter()
                .any(|field| object.get(*field).is_some_and(|value| !value.is_object()))
            {
                return false;
            }
        }
    }
    true
}

fn has_modern_metadata(request: &Value) -> bool {
    request.pointer("/params/_meta").is_some_and(|meta| {
        meta.get(PROTOCOL_VERSION_META).is_some()
            || meta.get(CLIENT_CAPABILITIES_META).is_some()
            || meta.get(CLIENT_INFO_META).is_some()
    })
}

fn contains_modern_request(request: &Value) -> bool {
    let is_modern = |message: &Value| {
        has_modern_metadata(message)
            || message.get("method").and_then(Value::as_str) == Some("server/discover")
    };
    request.as_array().map_or_else(
        || is_modern(request),
        |messages| messages.iter().any(is_modern),
    )
}

fn modern_http_error(
    id: Value,
    status: &'static str,
    code: i64,
    message: &str,
) -> (String, String) {
    (
        status.into(),
        json_rpc_error(id, code, message, None).to_string(),
    )
}

/// Validate the 2026-07-28 Streamable HTTP binding before dispatch. Legacy
/// requests without modern metadata keep their established HTTP behavior.
fn dispatch_http_json(
    backend: &McpBackend,
    body: &[u8],
    headers: &HashMap<String, String>,
) -> (String, String) {
    let parsed = std::str::from_utf8(body)
        .map_err(|error| error.to_string())
        .and_then(|body| {
            crate::receipt_verify::parse_strict_json(body).map_err(|error| error.to_string())
        });
    let Ok(request) = parsed else {
        let response = dispatch_json(backend, body).unwrap_or_else(|| "{}".into());
        return ("400 Bad Request".into(), response);
    };
    let version_header = headers.get("mcp-protocol-version").map(String::as_str);
    let method_header = headers.get("mcp-method").map(String::as_str);
    let method = request.get("method").and_then(Value::as_str);
    let body_version = request
        .pointer("/params/_meta/io.modelcontextprotocol~1protocolVersion")
        .and_then(Value::as_str);
    let legacy_header =
        version_header.is_some_and(|version| LEGACY_PROTOCOL_VERSIONS.contains(&version));
    let modern = (version_header.is_some() && !legacy_header)
        || body_version.is_some()
        || contains_modern_request(&request)
        || method == Some("server/discover");

    if modern {
        let id = request.get("id").cloned().unwrap_or(Value::Null);
        if request.is_array() {
            let (status, response) = modern_http_error(
                Value::Null,
                "400 Bad Request",
                -32600,
                "modern Streamable HTTP accepts one JSON-RPC message per POST",
            );
            return (status, response);
        }
        if id.is_null() {
            let (status, response) = modern_http_error(
                id,
                "400 Bad Request",
                -32600,
                "notifications are not supported over modern Streamable HTTP",
            );
            return (status, response);
        }
        if method_header != method {
            let (status, response) = modern_http_error(
                id,
                "400 Bad Request",
                -32020,
                "Header mismatch: Mcp-Method does not match request method",
            );
            return (status, response);
        }
        if version_header.is_none() || body_version.is_none() || version_header != body_version {
            let (status, response) = modern_http_error(
                id,
                "400 Bad Request",
                -32020,
                "Header mismatch: MCP-Protocol-Version is missing or does not match request metadata",
            );
            return (status, response);
        }
        let needs_name = matches!(
            method,
            Some("tools/call" | "resources/read" | "prompts/get")
        );
        let body_name = request
            .pointer("/params/name")
            .or_else(|| request.pointer("/params/uri"));
        if needs_name {
            let Some(header_name) = headers.get("mcp-name") else {
                let (status, response) = modern_http_error(
                    id,
                    "400 Bad Request",
                    -32020,
                    "Header mismatch: required Mcp-Name header is missing",
                );
                return (status, response);
            };
            if body_name.and_then(Value::as_str) != decode_mcp_header_value(header_name).as_deref()
            {
                let (status, response) = modern_http_error(
                    id,
                    "400 Bad Request",
                    -32020,
                    "Header mismatch: Mcp-Name does not match request params",
                );
                return (status, response);
            }
        }
        if let Err((code, message, data)) = validate_modern_request(&request) {
            return (
                "400 Bad Request".into(),
                json_rpc_error(id, code, message, data).to_string(),
            );
        }
        let Some(method) = method else {
            let (status, response) =
                modern_http_error(id, "400 Bad Request", -32600, "invalid JSON-RPC request");
            return (status, response);
        };
        if !matches!(method, "server/discover" | "tools/list" | "tools/call") {
            let (status, response) =
                modern_http_error(id, "404 Not Found", -32601, "Method not found");
            return (status, response);
        }
        let response = backend.handle(&request).unwrap_or_else(|| "{}".into());
        return ("200 OK".into(), response.to_string());
    }

    let response = dispatch_json(backend, body).unwrap_or_default();
    if response.is_empty() {
        ("202 Accepted".into(), response)
    } else {
        ("200 OK".into(), response)
    }
}

/// Startup arm-state line. Disarming (`WM_FIREBREAK=0`) must be loud, never
/// silent doctrine.
fn log_firebreak_arm_state(firebreak: &Firebreak) {
    if firebreak.is_armed() {
        let (forbidden, dangerous, caution) = firebreak.pattern_counts();
        eprintln!(
            "gen3: firebreak armed — {forbidden} forbidden / {dangerous} dangerous / {caution} \
             caution patterns at the MCP dispatch seam"
        );
    } else {
        eprintln!(
            "gen3: firebreak DISARMED via WM_FIREBREAK=0 — forbidden-command, dangerous and \
             caution gating are OFF"
        );
    }
}

/// The `firebreak` disclosure object attached to on-seam responses: arm
/// state, verdict and advisories. A gate that acts silently is a gate nobody
/// can audit.
fn firebreak_disclosure(firebreak: &Firebreak, verdict: &str, advisories: Vec<String>) -> Value {
    json!({
        "armed": firebreak.is_armed(),
        "verdict": verdict,
        "advisories": advisories,
    })
}

fn tool_call_envelope(
    id: Value,
    result: Result<Value, String>,
    firebreak: Option<Value>,
    modern: bool,
) -> Value {
    let (text, is_error) = match result {
        Ok(val) => (
            serde_json::to_string_pretty(&val).unwrap_or_else(|_| val.to_string()),
            false,
        ),
        Err(err_msg) => (format!("Error: {err_msg}"), true),
    };
    let mut result = json!({
        "content": [
            {
                "type": "text",
                "text": text
            }
        ],
        "isError": is_error
    });
    if modern {
        result["resultType"] = json!("complete");
    }
    if let Some(disclosure) = firebreak {
        result["firebreak"] = disclosure;
    }
    json!({
        "jsonrpc": "2.0",
        "id": id,
        "result": result
    })
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

fn dispatch_legacy_sse_json(backend: &McpBackend, body: &[u8]) -> Option<String> {
    let parsed = std::str::from_utf8(body)
        .ok()
        .and_then(|body| crate::receipt_verify::parse_strict_json(body).ok());
    let has_modern = parsed.as_ref().is_some_and(|value| {
        let is_modern_request = |request: &Value| {
            has_modern_metadata(request)
                || request.get("method").and_then(Value::as_str) == Some("server/discover")
        };
        value.as_array().map_or_else(
            || is_modern_request(value),
            |requests| requests.iter().any(is_modern_request),
        )
    });
    if has_modern {
        let id = parsed
            .as_ref()
            .and_then(|value| value.get("id"))
            .cloned()
            .unwrap_or(Value::Null);
        return Some(
            json_rpc_error(
                id,
                -32601,
                "modern MCP is unavailable on the legacy HTTP+SSE transport",
                None,
            )
            .to_string(),
        );
    }
    dispatch_json(backend, body)
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
    let mcp_endpoint = (transport == NetworkTransport::Http && path == "/mcp")
        || (transport == NetworkTransport::Sse && matches!(path, "/sse" | "/messages"));
    if mcp_endpoint
        && headers
            .get("origin")
            .is_some_and(|origin| !is_allowed_local_origin(origin))
    {
        return write_response(
            &mut stream,
            "403 Forbidden",
            "application/json",
            br#"{"error":"Origin is not allowed"}"#,
        );
    }

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
            let (status, text) = dispatch_http_json(&ctx.backend, &body, &headers);
            write_response(&mut stream, &status, "application/json", text.as_bytes())
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
                    if let Some(text) = dispatch_legacy_sse_json(&ctx.backend, &body) {
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

fn is_allowed_local_origin(origin: &str) -> bool {
    let Some((scheme, authority)) = origin.split_once("://") else {
        return false;
    };
    if !scheme.eq_ignore_ascii_case("http") && !scheme.eq_ignore_ascii_case("https") {
        return false;
    }
    if authority.is_empty()
        || authority
            .chars()
            .any(|ch| matches!(ch, '/' | '?' | '#' | '@'))
    {
        return false;
    }
    let host = if let Some(rest) = authority.strip_prefix('[') {
        let Some((address, suffix)) = rest.split_once(']') else {
            return false;
        };
        if !suffix.is_empty()
            && (!suffix.starts_with(':')
                || suffix.len() == 1
                || !suffix[1..].bytes().all(|byte| byte.is_ascii_digit()))
        {
            return false;
        }
        address
    } else {
        let (host, port) = authority.split_once(':').unwrap_or((authority, ""));
        if authority.matches(':').count() > 1
            || (authority.contains(':')
                && (port.is_empty() || !port.bytes().all(|byte| byte.is_ascii_digit())))
        {
            return false;
        }
        host
    };
    matches!(
        host.to_ascii_lowercase().as_str(),
        "localhost" | "127.0.0.1" | "::1"
    )
}

fn decode_mcp_header_value(value: &str) -> Option<String> {
    if let Some(encoded) = value
        .strip_prefix("=?base64?")
        .and_then(|value| value.strip_suffix("?="))
    {
        let bytes = decode_base64(encoded)?;
        return String::from_utf8(bytes).ok();
    }
    let bytes = value.as_bytes();
    let safe_ascii = bytes
        .iter()
        .all(|byte| *byte == b'\t' || (0x20..=0x7e).contains(byte));
    let sentinel = value.starts_with("=?base64?") && value.ends_with("?=");
    if !safe_ascii
        || bytes
            .first()
            .is_some_and(|byte| matches!(byte, b' ' | b'\t'))
        || bytes
            .last()
            .is_some_and(|byte| matches!(byte, b' ' | b'\t'))
        || sentinel
    {
        return None;
    }
    Some(value.to_owned())
}

fn decode_base64(encoded: &str) -> Option<Vec<u8>> {
    if encoded.len() % 4 != 0 {
        return None;
    }
    let mut output = Vec::with_capacity(encoded.len() / 4 * 3);
    for (index, chunk) in encoded.as_bytes().chunks_exact(4).enumerate() {
        let final_chunk = index + 1 == encoded.len() / 4;
        let a = base64_digit(chunk[0])?;
        let b = base64_digit(chunk[1])?;
        let c = if chunk[2] == b'=' {
            0
        } else {
            base64_digit(chunk[2])?
        };
        let d = if chunk[3] == b'=' {
            0
        } else {
            base64_digit(chunk[3])?
        };
        if (!final_chunk && (chunk[2] == b'=' || chunk[3] == b'='))
            || (chunk[2] == b'=' && chunk[3] != b'=')
        {
            return None;
        }
        output.push((a << 2) | (b >> 4));
        if chunk[2] != b'=' {
            output.push((b << 4) | (c >> 2));
        }
        if chunk[3] != b'=' {
            output.push((c << 6) | d);
        }
    }
    Some(output)
}

fn base64_digit(byte: u8) -> Option<u8> {
    match byte {
        b'A'..=b'Z' => Some(byte - b'A'),
        b'a'..=b'z' => Some(byte - b'a' + 26),
        b'0'..=b'9' => Some(byte - b'0' + 52),
        b'+' => Some(62),
        b'/' => Some(63),
        _ => None,
    }
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

    fn modern_request(id: u64, method: &str, params: Value) -> Value {
        let mut params = params;
        params["_meta"] = json!({
            "io.modelcontextprotocol/protocolVersion": MODERN_PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientCapabilities": {}
        });
        json!({ "jsonrpc": "2.0", "id": id, "method": method, "params": params })
    }

    fn modern_headers(method: &str, name: Option<&str>) -> HashMap<String, String> {
        let mut headers = HashMap::from([
            (
                "mcp-protocol-version".into(),
                MODERN_PROTOCOL_VERSION.into(),
            ),
            ("mcp-method".into(), method.into()),
        ]);
        if let Some(name) = name {
            headers.insert("mcp-name".into(), name.into());
        }
        headers
    }

    #[test]
    fn modern_discovery_and_tools_results_match_2026_core_shape() {
        let (backend, store) = test_backend("modern-results");
        let discover = backend
            .handle(&modern_request(1, "server/discover", json!({})))
            .unwrap();
        assert_eq!(
            discover["result"]["supportedVersions"],
            json!([MODERN_PROTOCOL_VERSION, LEGACY_PROTOCOL_VERSION])
        );
        assert_eq!(discover["result"]["resultType"], json!("complete"));
        assert_eq!(discover["result"]["capabilities"]["tools"], json!({}));
        assert_eq!(discover["result"]["ttlMs"], json!(0));
        assert_eq!(discover["result"]["cacheScope"], json!("private"));

        let list = backend
            .handle(&modern_request(2, "tools/list", json!({})))
            .unwrap();
        assert_eq!(list["result"]["resultType"], json!("complete"));
        assert_eq!(list["result"]["ttlMs"], json!(0));
        assert_eq!(list["result"]["cacheScope"], json!("private"));
        assert!(list["result"]["tools"].is_array());

        let call = backend
            .handle(&modern_request(
                3,
                "tools/call",
                json!({
                    "name": "memory.count", "arguments": {}
                }),
            ))
            .unwrap();
        assert_eq!(call["result"]["resultType"], json!("complete"));
        assert_eq!(call["result"]["isError"], json!(false));
        drop(backend);
        std::fs::remove_dir_all(store).expect("remove modern fixture");
    }

    #[test]
    fn modern_metadata_versions_and_http_mirrors_are_checked() {
        let (backend, store) = test_backend("modern-validation");
        let mut missing_capabilities = modern_request(1, "tools/list", json!({}));
        missing_capabilities["params"]["_meta"]
            .as_object_mut()
            .unwrap()
            .remove(CLIENT_CAPABILITIES_META);
        assert_eq!(
            backend.handle(&missing_capabilities).unwrap()["error"]["code"],
            json!(-32602)
        );

        let mut unsupported = modern_request(2, "tools/list", json!({}));
        unsupported["params"]["_meta"][PROTOCOL_VERSION_META] = json!("2099-01-01");
        let error = backend.handle(&unsupported).unwrap();
        assert_eq!(error["error"]["code"], json!(-32022));
        assert_eq!(
            error["error"]["data"]["supported"],
            json!([MODERN_PROTOCOL_VERSION, LEGACY_PROTOCOL_VERSION])
        );
        assert_eq!(error["error"]["data"]["requested"], json!("2099-01-01"));

        let modern_batch = json!([
            modern_request(34, "tools/list", json!({})),
            modern_request(35, "tools/list", json!({}))
        ]);
        let batch_error = backend.handle(&modern_batch).unwrap();
        assert_eq!(batch_error["error"]["code"], json!(-32600));

        let mut headers = modern_headers("tools/list", None);
        headers.insert("mcp-protocol-version".into(), "2099-01-01".into());
        let (status, body) = dispatch_http_json(
            &backend,
            modern_request(3, "tools/list", json!({}))
                .to_string()
                .as_bytes(),
            &headers,
        );
        let value: Value = serde_json::from_str(&body).unwrap();
        assert_eq!(status, "400 Bad Request");
        assert_eq!(value["error"]["code"], json!(-32020));

        let (status, body) = dispatch_http_json(
            &backend,
            modern_batch.to_string().as_bytes(),
            &HashMap::new(),
        );
        let value: Value = serde_json::from_str(&body).unwrap();
        assert_eq!(status, "400 Bad Request");
        assert_eq!(value["error"]["code"], json!(-32600));

        let legacy = json!({"jsonrpc":"2.0", "id": 30, "method":"tools/list"});
        let legacy_headers = HashMap::from([(
            "mcp-protocol-version".into(),
            LEGACY_PROTOCOL_VERSION.into(),
        )]);
        let (status, body) =
            dispatch_http_json(&backend, legacy.to_string().as_bytes(), &legacy_headers);
        let value: Value = serde_json::from_str(&body).unwrap();
        assert_eq!(status, "200 OK");
        assert_eq!(value["id"], json!(30));
        assert!(value["result"].get("resultType").is_none());

        let mut malformed_capabilities = modern_request(31, "tools/list", json!({}));
        malformed_capabilities["params"]["_meta"][CLIENT_CAPABILITIES_META] =
            json!({"sampling": false});
        assert_eq!(
            backend.handle(&malformed_capabilities).unwrap()["error"]["code"],
            json!(-32602)
        );

        let unknown_method = backend
            .handle(&modern_request(32, "ping", json!({})))
            .unwrap();
        assert_eq!(unknown_method["error"]["code"], json!(-32601));

        let before_epoch = match &backend {
            McpBackend::Gen3 { substrate, .. } => {
                substrate.lock().unwrap().store().epoch().unwrap()
            }
            McpBackend::Legacy { .. } => unreachable!(),
        };
        let invalid_call = modern_request(
            33,
            "tools/call",
            json!({
                "name": "memory.create", "arguments": "not-an-object"
            }),
        );
        assert_eq!(
            backend.handle(&invalid_call).unwrap()["error"]["code"],
            json!(-32602)
        );
        let after_epoch = match &backend {
            McpBackend::Gen3 { substrate, .. } => {
                substrate.lock().unwrap().store().epoch().unwrap()
            }
            McpBackend::Legacy { .. } => unreachable!(),
        };
        assert_eq!(
            before_epoch, after_epoch,
            "invalid modern calls must not mutate the store"
        );

        let request = modern_request(
            4,
            "tools/call",
            json!({
                "name": "memory.count", "arguments": {}
            }),
        );
        let (status, body) = dispatch_http_json(
            &backend,
            request.to_string().as_bytes(),
            &modern_headers("tools/call", Some("memory.count")),
        );
        assert_eq!(status, "200 OK");
        let value: Value = serde_json::from_str(&body).unwrap();
        assert_eq!(value["result"]["resultType"], json!("complete"));

        assert!(is_allowed_local_origin("http://localhost:3000"));
        assert!(is_allowed_local_origin("https://127.0.0.1"));
        assert!(!is_allowed_local_origin("https://localhost.example"));
        assert!(!is_allowed_local_origin("http://example.com"));
        assert_eq!(
            decode_mcp_header_value("=?base64?SGVsbG8sIOS4lueVjA==?=").as_deref(),
            Some("Hello, 世界")
        );
        assert_eq!(decode_mcp_header_value("=?base64?bad?="), None);
        drop(backend);
        std::fs::remove_dir_all(store).expect("remove validation fixture");
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

    fn armed_backend(tag: &str, armed: bool) -> (McpBackend, PathBuf) {
        let store =
            std::env::temp_dir().join(format!("wm-firebreak-{tag}-{}", uuid::Uuid::new_v4()));
        let substrate = Substrate::open(&store, None, wm_gen3_core::constitution::default_view())
            .expect("open isolated firebreak fixture");
        let backend = McpBackend::Gen3 {
            substrate: Box::new(Mutex::new(substrate)),
            store_path: store.clone(),
            profile: McpProfile::Full,
            readonly: false,
            firebreak: Firebreak::with_armed(armed),
        };
        (backend, store)
    }

    fn call_tool(backend: &McpBackend, id: u64, name: &str, args: Value) -> Value {
        backend
            .handle(&json!({
                "jsonrpc": "2.0",
                "id": id,
                "method": "tools/call",
                "params": { "name": name, "arguments": args }
            }))
            .expect("tools/call response")
    }

    #[test]
    fn firebreak_seam_gates_forbidden_dangerous_and_caution() {
        let (backend, store) = armed_backend("gate", true);

        // Recording an incident that quotes a forbidden command must pass,
        // and off-seam calls carry no firebreak disclosure.
        let incident = call_tool(
            &backend,
            1,
            "memory.create",
            json!({ "content": "incident: operator ran rm -rf / on the store" }),
        );
        assert_eq!(incident["result"]["isError"], json!(false), "{incident}");
        assert!(incident["result"].get("firebreak").is_none());

        // Forbidden never passes, even with confirm.
        let forbidden = call_tool(
            &backend,
            2,
            "mandala.evaluate",
            json!({ "command": "rm -rf /", "confirm": true }),
        );
        assert_eq!(forbidden["result"]["isError"], json!(true), "{forbidden}");
        assert!(
            forbidden["result"]["content"][0]["text"]
                .as_str()
                .unwrap_or("")
                .contains("FORBIDDEN")
        );
        assert_eq!(
            forbidden["result"]["firebreak"]["verdict"],
            json!("forbidden")
        );
        assert_eq!(forbidden["result"]["firebreak"]["armed"], json!(true));

        // Dangerous without confirm is refused before the bridge.
        let dangerous = call_tool(
            &backend,
            3,
            "mandala.evaluate",
            json!({ "command": "sudo rm -r /tmp/firebreak-probe" }),
        );
        assert_eq!(dangerous["result"]["isError"], json!(true), "{dangerous}");
        assert!(
            dangerous["result"]["content"][0]["text"]
                .as_str()
                .unwrap_or("")
                .contains("confirm")
        );

        // The same payload with confirm reaches dispatch.
        let confirmed = call_tool(
            &backend,
            4,
            "mandala.evaluate",
            json!({ "command": "sudo rm -r /tmp/firebreak-probe", "confirm": true }),
        );
        assert_eq!(confirmed["result"]["isError"], json!(false), "{confirmed}");
        assert_eq!(
            confirmed["result"]["firebreak"]["verdict"],
            json!("dangerous-confirmed")
        );

        // Caution passes with advisories attached to the response.
        let caution = call_tool(
            &backend,
            5,
            "mandala.evaluate",
            json!({ "command": "rm /tmp/firebreak-scratch" }),
        );
        assert_eq!(caution["result"]["isError"], json!(false), "{caution}");
        assert_eq!(caution["result"]["firebreak"]["verdict"], json!("caution"));
        assert!(
            caution["result"]["firebreak"]["advisories"]
                .as_array()
                .is_some_and(|advisories| !advisories.is_empty())
        );

        drop(backend);
        std::fs::remove_dir_all(store).expect("remove isolated firebreak fixture");
    }

    #[test]
    fn firebreak_router_scans_the_effective_target() {
        let (backend, store) = armed_backend("router", true);

        // Routed prose stays off-seam.
        let routed_prose = call_tool(
            &backend,
            1,
            "wm",
            json!({
                "route": "memory.create",
                "args": { "content": "note: rm -rf / was attempted" }
            }),
        );
        assert_eq!(
            routed_prose["result"]["isError"],
            json!(false),
            "{routed_prose}"
        );

        // Routed exec is still scanned and refused.
        let routed_exec = call_tool(
            &backend,
            2,
            "wm",
            json!({
                "route": "mandala.evaluate",
                "args": { "command": "rm -rf /", "confirm": true }
            }),
        );
        assert_eq!(
            routed_exec["result"]["isError"],
            json!(true),
            "{routed_exec}"
        );
        assert_eq!(
            routed_exec["result"]["firebreak"]["verdict"],
            json!("forbidden")
        );

        // Natural-language thought is prose.
        let thought = call_tool(
            &backend,
            3,
            "wm",
            json!({ "thought": "remember that rm -rf / destroys the store" }),
        );
        assert_eq!(thought["result"]["isError"], json!(false), "{thought}");

        drop(backend);
        std::fs::remove_dir_all(store).expect("remove isolated firebreak fixture");
    }

    #[test]
    fn firebreak_disarm_is_honored_and_disclosed() {
        let (backend, store) = armed_backend("disarmed", false);
        let response = call_tool(
            &backend,
            1,
            "mandala.evaluate",
            json!({ "command": "rm -rf /", "confirm": true }),
        );
        assert_eq!(response["result"]["isError"], json!(false), "{response}");
        assert_eq!(response["result"]["firebreak"]["armed"], json!(false));
        assert_eq!(response["result"]["firebreak"]["verdict"], json!("allow"));
        drop(backend);
        std::fs::remove_dir_all(store).expect("remove isolated firebreak fixture");
    }
}
