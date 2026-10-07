//! WhiteMagic Gen3 — `wm-node`: Geth-style consensus daemon socket (Phase 2).
//!
//! Binds a Unix domain socket and speaks **newline-delimited JSON-RPC 2.0**:
//! one JSON object per line, exactly one response line per request line.
//! Malformed frames receive an explicit `-32700` (or `-32600`) error line with
//! `id: null` — frames are never dropped silently.
//!
//! Socket path resolution: `--socket` → `WM_NODE_SOCKET` → `<store>/wm-node.sock`
//! → `$XDG_RUNTIME_DIR/wm-node.sock` → `$TMPDIR/wm-node.sock`.
//! Store resolution: `--store` → `WM_STORE`; with no store the node runs fully
//! in memory. With a store, tuples persist through the `tuple_space` primitive
//! and signals/proposals persist as JSON beside them.
//!
//! Phase 2 verbs (aliases in parentheses mirror the RFC §IV `wm_*` names):
//! * `node.status`
//! * `tuple.put`   (`wm_submitTuple`) — Linda `out`
//! * `tuple.get`   (`wm_readTuple`)   — Linda `rd`, non-destructive
//! * `tuple.take`  (`wm_takeTuple`)   — Linda `in`, destructive
//! * `signal.emit` (`wm_emitPheromone`)
//! * `signal.read` (`wm_senseField`)
//! * `proposal.put`(`wm_proposeSkeleton`) — Phase 2 scaffold
//! * `proposal.vote`(`wm_castVote`)       — Phase 2 scaffold
//! * `proposal.get` (`wm_getProposal`)    — scaffold inspection
//!
//! Single-writer safety: a second bind on a live socket is refused with a clear
//! error. `SIGTERM`/`SIGINT` shut the node down gracefully and remove the socket.

#![forbid(unsafe_code)]

use clap::Parser;
use signal_hook::consts::{SIGINT, SIGTERM};
use std::collections::HashMap;
use std::io::{BufRead, BufReader, BufWriter, Read, Write};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::Sender;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};
use uuid::Uuid;

use wm_gen3_core::stigmergy::{Pheromone, PheromoneKind, StigmergicField};
use wm_gen3_core::tuple_space::{Tuple, TupleKind, TuplePattern, TupleSpace};

const PROTOCOL: &str = "wm-node/1";
const JSONRPC_VERSION: &str = "2.0";
const SOCKET_FILE_NAME: &str = "wm-node.sock";
const TUPLES_FILE: &str = "wm-tuples.msgpack";
const SIGNALS_FILE: &str = "wm-signals.json";
const PROPOSALS_FILE: &str = "wm-proposals.json";
const DEFAULT_REQUIRED_VOTES: usize = 2;
const MAX_FRAME_BYTES: usize = 4 * 1024 * 1024;
const MAX_SOCKET_PATH_BYTES: usize = 100;
const ACCEPT_POLL_INTERVAL: Duration = Duration::from_millis(20);
const CONNECTION_POLL_INTERVAL: Duration = Duration::from_millis(250);

const PARSE_ERROR: i32 = -32700;
const INVALID_REQUEST: i32 = -32600;
const METHOD_NOT_FOUND: i32 = -32601;
const INVALID_PARAMS: i32 = -32602;
const INTERNAL_ERROR: i32 = -32603;

#[derive(Parser)]
#[command(
    name = "wm-node",
    version,
    about = "WhiteMagic Gen3 Geth-style consensus node: newline-delimited JSON-RPC over a Unix domain socket",
    after_help = "Socket resolution: --socket, WM_NODE_SOCKET, <store>/wm-node.sock, $XDG_RUNTIME_DIR/wm-node.sock, then $TMPDIR/wm-node.sock.\nStore resolution: --store, WM_STORE. Without a store the node runs fully in memory."
)]
struct Cli {
    /// Directory for persisted tuples/signals/proposals (optional; falls back to WM_STORE)
    #[arg(long, value_name = "DIR")]
    store: Option<PathBuf>,

    /// Unix domain socket path (optional; overrides WM_NODE_SOCKET and <store>/wm-node.sock)
    #[arg(long, value_name = "PATH")]
    socket: Option<PathBuf>,
}

/// JSON-RPC error surfaced from a verb handler.
struct RpcError {
    code: i32,
    message: String,
    data: Option<Value>,
}

impl RpcError {
    fn new(code: i32, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
            data: None,
        }
    }

    fn invalid_params(message: impl Into<String>) -> Self {
        Self::new(INVALID_PARAMS, message)
    }

    fn internal(message: impl Into<String>) -> Self {
        Self::new(INTERNAL_ERROR, message)
    }

    fn method_not_found(name: &str) -> Self {
        Self::new(METHOD_NOT_FOUND, format!("method not found: {name}"))
    }
}

/// Phase 2 scaffold vote record (PoCD quorum wiring lands in Phase 3).
#[derive(Debug, Clone, Serialize, Deserialize)]
struct ProposalVote {
    validator_id: String,
    /// `"approve"` or `"reject"`.
    decision: String,
    causal_lift: f64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    signature: Option<String>,
    ts_ms: u64,
}

/// Phase 2 scaffold proposal: an opaque action skeleton plus collected votes.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct Proposal {
    proposal_id: Uuid,
    task_id: Uuid,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    target: Option<String>,
    skeleton: Value,
    required_votes: usize,
    votes: Vec<ProposalVote>,
    /// `"pending"`, `"sealed"`, or `"rejected"`.
    status: String,
    created_at_ms: u64,
}

/// Shared mutable node state, guarded by a single mutex (single-writer store).
struct NodeState {
    tuples: TupleSpace,
    signals: StigmergicField,
    proposals: HashMap<Uuid, Proposal>,
    store: Option<PathBuf>,
    socket_path: PathBuf,
    started_at_ms: u64,
    started: Instant,
    requests: u64,
}

impl NodeState {
    fn load(socket_path: PathBuf, store: Option<PathBuf>) -> Result<Self, String> {
        let (tuples, signals, proposals) = if let Some(dir) = store.as_deref() {
            std::fs::create_dir_all(dir)
                .map_err(|e| format!("cannot create store {}: {e}", dir.display()))?;
            let tuples = TupleSpace::load_from_path(dir.join(TUPLES_FILE))
                .map_err(|e| format!("cannot load tuples: {e}"))?;
            let signals = StigmergicField::load_from_file(dir.join(SIGNALS_FILE))
                .map_err(|e| format!("cannot load signals: {e}"))?;
            let proposals = load_proposals(dir)?;
            (tuples, signals, proposals)
        } else {
            (TupleSpace::new(), StigmergicField::new(), HashMap::new())
        };

        Ok(Self {
            tuples,
            signals,
            proposals,
            store,
            socket_path,
            started_at_ms: now_ms(),
            started: Instant::now(),
            requests: 0,
        })
    }

    fn persist_tuples(&self) -> Result<(), String> {
        if let Some(dir) = &self.store {
            self.tuples
                .save_to_path(dir.join(TUPLES_FILE), true)
                .map_err(|e| format!("persist tuples: {e}"))?;
        }
        Ok(())
    }

    fn persist_signals(&self) -> Result<(), String> {
        if let Some(dir) = &self.store {
            self.signals
                .save_to_file(dir.join(SIGNALS_FILE))
                .map_err(|e| format!("persist signals: {e}"))?;
        }
        Ok(())
    }

    fn persist_proposals(&self) -> Result<(), String> {
        if let Some(dir) = &self.store {
            let mut proposals: Vec<&Proposal> = self.proposals.values().collect();
            proposals.sort_by_key(|p| p.created_at_ms);
            let bytes = serde_json::to_vec_pretty(&proposals)
                .map_err(|e| format!("serialize proposals: {e}"))?;
            write_atomic(&dir.join(PROPOSALS_FILE), &bytes)?;
        }
        Ok(())
    }
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

fn load_proposals(dir: &Path) -> Result<HashMap<Uuid, Proposal>, String> {
    let path = dir.join(PROPOSALS_FILE);
    if !path.exists() {
        return Ok(HashMap::new());
    }
    let bytes = std::fs::read(&path).map_err(|e| format!("read {}: {e}", path.display()))?;
    let proposals: Vec<Proposal> =
        serde_json::from_slice(&bytes).map_err(|e| format!("parse {}: {e}", path.display()))?;
    Ok(proposals.into_iter().map(|p| (p.proposal_id, p)).collect())
}

fn write_atomic(path: &Path, bytes: &[u8]) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("create dir {}: {e}", parent.display()))?;
    }
    let tmp = path.with_extension(format!("tmp-{}", Uuid::new_v4()));
    std::fs::write(&tmp, bytes).map_err(|e| format!("write {}: {e}", tmp.display()))?;
    std::fs::rename(&tmp, path).map_err(|e| format!("rename into {}: {e}", path.display()))?;
    Ok(())
}

/// Binds the UDS, refusing a second live writer and clearing stale socket files.
fn bind_listener(path: &Path) -> Result<UnixListener, String> {
    let path_bytes = path.as_os_str().len();
    if path_bytes > MAX_SOCKET_PATH_BYTES {
        return Err(format!(
            "socket path is {path_bytes} bytes, exceeding the Linux UDS limit (~{MAX_SOCKET_PATH_BYTES}): {}",
            path.display()
        ));
    }
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("create socket dir {}: {e}", parent.display()))?;
        }
    }
    if path.exists() {
        match UnixStream::connect(path) {
            Ok(_) => {
                return Err(format!(
                    "another wm-node is already listening on {} (refusing second bind)",
                    path.display()
                ));
            }
            Err(_) => {
                // Stale socket left by a previous crash: reclaim it.
                std::fs::remove_file(path)
                    .map_err(|e| format!("remove stale socket {}: {e}", path.display()))?;
            }
        }
    }
    let listener = UnixListener::bind(path).map_err(|e| {
        if e.kind() == std::io::ErrorKind::AddrInUse {
            format!(
                "another wm-node is already listening on {} (refusing second bind): {e}",
                path.display()
            )
        } else {
            format!("bind {}: {e}", path.display())
        }
    })?;
    let _ = std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o600));
    Ok(listener)
}

#[derive(Deserialize)]
struct RpcRequest {
    #[serde(default)]
    jsonrpc: String,
    #[serde(default)]
    id: Option<Value>,
    #[serde(default)]
    method: Option<String>,
    #[serde(default)]
    params: Option<Value>,
}

fn ok_response(id: &Value, result: Value) -> Value {
    json!({"jsonrpc": JSONRPC_VERSION, "id": id, "result": result})
}

fn error_response(id: &Value, err: &RpcError) -> Value {
    let mut error = json!({"code": err.code, "message": err.message});
    if let Some(data) = &err.data {
        error["data"] = data.clone();
    }
    json!({"jsonrpc": JSONRPC_VERSION, "id": id, "error": error})
}

/// Turns one raw frame into exactly one response line (including parse failures).
fn respond_to_frame(state: &mut NodeState, text: &str) -> Value {
    if text.len() > MAX_FRAME_BYTES {
        return error_response(
            &Value::Null,
            &RpcError::new(INVALID_REQUEST, "frame exceeds maximum size"),
        );
    }
    match serde_json::from_str::<RpcRequest>(text) {
        Err(e) => {
            let mut err = RpcError::new(PARSE_ERROR, "parse error");
            err.data = Some(json!({"detail": e.to_string()}));
            error_response(&Value::Null, &err)
        }
        Ok(req) => {
            let id = req.id.clone().unwrap_or(Value::Null);
            if req.jsonrpc != JSONRPC_VERSION {
                return error_response(
                    &id,
                    &RpcError::new(INVALID_REQUEST, "expected jsonrpc \"2.0\""),
                );
            }
            let Some(method) = req.method.as_deref() else {
                return error_response(&id, &RpcError::new(INVALID_REQUEST, "missing method"));
            };
            let params = req
                .params
                .clone()
                .filter(|p| !p.is_null())
                .unwrap_or_else(|| json!({}));
            match dispatch(state, method, &params) {
                Ok(result) => ok_response(&id, result),
                Err(err) => error_response(&id, &err),
            }
        }
    }
}

fn dispatch(state: &mut NodeState, method: &str, params: &Value) -> Result<Value, RpcError> {
    state.requests += 1;
    match method {
        "node.status" | "wm_nodeStatus" => node_status(state),
        "tuple.put" | "wm_submitTuple" => tuple_put(state, params),
        "tuple.get" | "wm_readTuple" => tuple_get(state, params),
        "tuple.take" | "wm_takeTuple" => tuple_take(state, params),
        "signal.emit" | "wm_emitPheromone" => signal_emit(state, params),
        "signal.read" | "wm_senseField" => signal_read(state, params),
        "proposal.put" | "wm_proposeSkeleton" => proposal_put(state, params),
        "proposal.vote" | "wm_castVote" => proposal_vote(state, params),
        "proposal.get" | "wm_getProposal" => proposal_get(state, params),
        "wm_getReceipt" => Err(RpcError::new(
            METHOD_NOT_FOUND,
            "wm_getReceipt is not part of Phase 2; SCITT receipts land in Phase 4",
        )),
        other => Err(RpcError::method_not_found(other)),
    }
}

fn node_status(state: &NodeState) -> Result<Value, RpcError> {
    Ok(json!({
        "ok": true,
        "protocol": PROTOCOL,
        "version": env!("CARGO_PKG_VERSION"),
        "pid": std::process::id(),
        "socket": state.socket_path.display().to_string(),
        "store": state.store.as_ref().map(|p| p.display().to_string()),
        "started_at_ms": state.started_at_ms,
        "uptime_ms": state.started.elapsed().as_millis() as u64,
        "tuples": state.tuples.len(),
        "signals": state.signals.all().len(),
        "proposals": state.proposals.len(),
        "requests": state.requests,
    }))
}

fn params_object(params: &Value) -> Result<&Map<String, Value>, RpcError> {
    params
        .as_object()
        .ok_or_else(|| RpcError::invalid_params("params must be a JSON object"))
}

fn opt_str<'a>(obj: &'a Map<String, Value>, keys: &[&str]) -> Option<&'a str> {
    keys.iter()
        .find_map(|k| obj.get(*k).and_then(Value::as_str))
}

fn required_str(obj: &Map<String, Value>, keys: &[&str], what: &str) -> Result<String, RpcError> {
    opt_str(obj, keys)
        .map(str::to_string)
        .ok_or_else(|| RpcError::invalid_params(format!("missing required field '{what}'")))
}

fn opt_u64(obj: &Map<String, Value>, keys: &[&str]) -> Option<u64> {
    keys.iter()
        .find_map(|k| obj.get(*k).and_then(Value::as_u64))
}

fn opt_f64(obj: &Map<String, Value>, keys: &[&str]) -> Option<f64> {
    keys.iter()
        .find_map(|k| obj.get(*k).and_then(Value::as_f64))
}

fn opt_bool(obj: &Map<String, Value>, keys: &[&str]) -> Option<bool> {
    keys.iter()
        .find_map(|k| obj.get(*k).and_then(Value::as_bool))
}

fn opt_uuid(obj: &Map<String, Value>, keys: &[&str]) -> Result<Option<Uuid>, RpcError> {
    match opt_str(obj, keys) {
        None => Ok(None),
        Some(s) => Uuid::parse_str(s)
            .map(Some)
            .map_err(|e| RpcError::invalid_params(format!("invalid uuid '{}': {e}", keys[0]))),
    }
}

fn parse_string_vec(value: Option<&Value>) -> Result<Vec<String>, RpcError> {
    match value {
        None | Some(Value::Null) => Ok(Vec::new()),
        Some(Value::String(s)) => Ok(vec![s.clone()]),
        Some(Value::Array(items)) => items
            .iter()
            .map(|item| {
                item.as_str()
                    .map(str::to_string)
                    .ok_or_else(|| RpcError::invalid_params("scope entries must be strings"))
            })
            .collect(),
        Some(_) => Err(RpcError::invalid_params(
            "scope must be a string or an array of strings",
        )),
    }
}

fn parse_line_range(value: Option<&Value>) -> Result<Option<(u32, u32)>, RpcError> {
    match value {
        None | Some(Value::Null) => Ok(None),
        Some(Value::Array(items)) if items.len() == 2 => {
            let start = items[0]
                .as_u64()
                .ok_or_else(|| RpcError::invalid_params("line_range[0] must be an integer"))?;
            let end = items[1]
                .as_u64()
                .ok_or_else(|| RpcError::invalid_params("line_range[1] must be an integer"))?;
            Ok(Some((
                start.min(u32::MAX as u64) as u32,
                end.min(u32::MAX as u64) as u32,
            )))
        }
        Some(_) => Err(RpcError::invalid_params("line_range must be [start, end]")),
    }
}

fn decode_hex(s: &str) -> Result<Vec<u8>, RpcError> {
    if s.len() % 2 != 0 {
        return Err(RpcError::invalid_params("hex string has odd length"));
    }
    (0..s.len())
        .step_by(2)
        .map(|i| {
            u8::from_str_radix(&s[i..i + 2], 16)
                .map_err(|_| RpcError::invalid_params("hex string contains a non-hex character"))
        })
        .collect()
}

fn parse_tuple_kind(value: &Value, obj: &Map<String, Value>) -> Result<TupleKind, RpcError> {
    match value {
        Value::String(name) => parse_tuple_kind_shorthand(name, obj),
        Value::Object(_) => serde_json::from_value(value.clone())
            .map_err(|e| RpcError::invalid_params(format!("invalid TupleKind object: {e}"))),
        _ => Err(RpcError::invalid_params(
            "'kind' must be a shorthand string or a TupleKind object",
        )),
    }
}

fn parse_tuple_kind_shorthand(name: &str, obj: &Map<String, Value>) -> Result<TupleKind, RpcError> {
    let lower = name.to_ascii_lowercase();
    match lower.as_str() {
        "generic" => Ok(TupleKind::Generic {
            tag: opt_str(obj, &["tag"]).unwrap_or("generic").to_string(),
            payload: opt_str(obj, &["payload"]).unwrap_or_default().to_string(),
        }),
        "claim" => Ok(TupleKind::Claim {
            resource: required_str(obj, &["resource"], "resource")?,
            holder: required_str(obj, &["holder"], "holder")?,
            ttl_ms: opt_u64(obj, &["ttl_ms"]).unwrap_or(0),
        }),
        "task" => Ok(TupleKind::Task {
            task_id: opt_uuid(obj, &["task_id"])?.unwrap_or_else(Uuid::new_v4),
            action: required_str(obj, &["action"], "action")?,
            target: required_str(obj, &["target"], "target")?,
            payload: match opt_str(obj, &["payload"]) {
                Some(s) => decode_hex(s)?,
                None => Vec::new(),
            },
        }),
        "authoritygrant" | "authority_grant" => {
            let token = match opt_str(obj, &["landlock_token"]) {
                Some(s) => {
                    let bytes = decode_hex(s)?;
                    if bytes.len() != 32 {
                        return Err(RpcError::invalid_params(
                            "landlock_token must be 32 bytes (64 hex chars)",
                        ));
                    }
                    let mut token = [0u8; 32];
                    token.copy_from_slice(&bytes);
                    token
                }
                None => [0u8; 32],
            };
            Ok(TupleKind::AuthorityGrant {
                task_id: opt_uuid(obj, &["task_id"])?.unwrap_or_else(Uuid::new_v4),
                granter: required_str(obj, &["granter"], "granter")?,
                capability_mask: opt_u64(obj, &["capability_mask"]).unwrap_or(0),
                landlock_token: token,
            })
        }
        "resultnotice" | "result_notice" => Ok(TupleKind::ResultNotice {
            task_id: opt_uuid(obj, &["task_id"])?.unwrap_or_else(Uuid::new_v4),
            success: opt_bool(obj, &["success"]).unwrap_or(true),
            output_summary: opt_str(obj, &["output_summary"])
                .unwrap_or_default()
                .to_string(),
            duration_ms: opt_u64(obj, &["duration_ms"]).unwrap_or(0),
        }),
        "pheromonesync" | "pheromone_sync" => Ok(TupleKind::PheromoneSync {
            resource: required_str(obj, &["resource"], "resource")?,
            intensity: opt_f64(obj, &["intensity"]).unwrap_or(1.0),
            issuer: opt_str(obj, &["issuer"]).unwrap_or_default().to_string(),
        }),
        other => Err(RpcError::invalid_params(format!(
            "unknown tuple kind shorthand '{other}' (expected Generic|Claim|Task|AuthorityGrant|ResultNotice|PheromoneSync)"
        ))),
    }
}

fn parse_pheromone_kind(value: Option<&Value>) -> Result<PheromoneKind, RpcError> {
    match value {
        None | Some(Value::Null) => Ok(PheromoneKind::Custom("signal".into())),
        Some(Value::String(s)) => match s.to_ascii_lowercase().as_str() {
            "mutationactive" | "mutation_active" | "mutation-active" => {
                Ok(PheromoneKind::MutationActive)
            }
            "inspection" => Ok(PheromoneKind::Inspection),
            "refactoring" => Ok(PheromoneKind::Refactoring),
            "reviewpending" | "review_pending" | "review-pending" => {
                Ok(PheromoneKind::ReviewPending)
            }
            _ => Ok(PheromoneKind::Custom(s.clone())),
        },
        Some(other) => serde_json::from_value(other.clone())
            .map_err(|e| RpcError::invalid_params(format!("invalid pheromone kind: {e}"))),
    }
}

fn parse_pattern(
    obj: &Map<String, Value>,
) -> Result<(TuplePattern, Option<Uuid>, usize), RpcError> {
    let pattern = TuplePattern {
        kind_filter: opt_str(obj, &["kind", "kind_filter"]).map(str::to_string),
        resource_match: opt_str(obj, &["resource", "resource_match"]).map(str::to_string),
        holder_match: opt_str(obj, &["holder", "holder_match"]).map(str::to_string),
        task_id_match: opt_uuid(obj, &["task_id"])?,
        tag_match: opt_str(obj, &["tag", "tag_match"]).map(str::to_string),
    };
    let id = opt_uuid(obj, &["id"])?;
    let limit = opt_u64(obj, &["limit"]).unwrap_or(64) as usize;
    Ok((pattern, id, limit))
}

fn tuple_put(state: &mut NodeState, params: &Value) -> Result<Value, RpcError> {
    let root = params_object(params)?;
    // Accept either the flat form or `{"tuple": {...}}`.
    let source = root.get("tuple").and_then(Value::as_object).unwrap_or(root);
    let kind_value = source
        .get("kind")
        .ok_or_else(|| RpcError::invalid_params("missing required field 'kind'"))?;
    let ttl_ms = opt_u64(source, &["ttl_ms", "ttl"]).unwrap_or(0);
    let kind = parse_tuple_kind(kind_value, source)?;
    let tuple = Tuple::new(kind, ttl_ms);
    let id = tuple.id;
    let body = serde_json::to_value(&tuple)
        .map_err(|e| RpcError::internal(format!("serialize tuple: {e}")))?;
    let expires_at_ms = tuple.expires_at_ms;
    state.tuples.out(tuple);
    state.persist_tuples().map_err(RpcError::internal)?;
    Ok(
        json!({"id": id, "expires_at_ms": expires_at_ms, "tuple": body, "tuples": state.tuples.len()}),
    )
}

fn tuple_get(state: &mut NodeState, params: &Value) -> Result<Value, RpcError> {
    let obj = params_object(params)?;
    let (pattern, id_filter, limit) = parse_pattern(obj)?;
    let matches = state.tuples.rd_matching(&pattern, now_ms());
    let mut tuples = Vec::new();
    for tuple in matches {
        if let Some(id) = id_filter {
            if tuple.id != id {
                continue;
            }
        }
        if limit > 0 && tuples.len() >= limit {
            break;
        }
        tuples.push(
            serde_json::to_value(&tuple)
                .map_err(|e| RpcError::internal(format!("serialize tuple: {e}")))?,
        );
    }
    Ok(json!({"found": !tuples.is_empty(), "count": tuples.len(), "tuples": tuples}))
}

fn tuple_take(state: &mut NodeState, params: &Value) -> Result<Value, RpcError> {
    let obj = params_object(params)?;
    let (pattern, id_filter, _) = parse_pattern(obj)?;
    if id_filter.is_some() {
        return Err(RpcError::invalid_params(
            "tuple.take does not support an 'id' filter; take by kind/tag/resource",
        ));
    }
    match state.tuples.in_matching(&pattern, now_ms()) {
        Some(tuple) => {
            let body = serde_json::to_value(&tuple)
                .map_err(|e| RpcError::internal(format!("serialize tuple: {e}")))?;
            state.persist_tuples().map_err(RpcError::internal)?;
            Ok(json!({"found": true, "tuple": body, "tuples": state.tuples.len()}))
        }
        None => Ok(json!({"found": false, "tuple": null, "tuples": state.tuples.len()})),
    }
}

fn pheromone_json(pheromone: &Pheromone, now_ms: u64) -> Value {
    let mut value = serde_json::to_value(pheromone).unwrap_or(Value::Null);
    if let Some(obj) = value.as_object_mut() {
        obj.insert(
            "current_intensity".into(),
            json!(pheromone.current_intensity(now_ms)),
        );
    }
    value
}

fn signal_emit(state: &mut NodeState, params: &Value) -> Result<Value, RpcError> {
    let obj = params_object(params)?;
    let target_path = required_str(obj, &["target_path", "path"], "target_path")?;
    let ast_scope = parse_string_vec(obj.get("ast_scope").or_else(|| obj.get("scope")))?;
    let kind = parse_pheromone_kind(obj.get("kind"))?;
    let intensity = opt_f64(obj, &["intensity", "initial_intensity"]).unwrap_or(1.0);
    let half_life_ms = opt_u64(obj, &["half_life_ms", "half_life"]).unwrap_or(60_000);
    let issuer = opt_str(obj, &["issuer"])
        .unwrap_or("wm-node-client")
        .to_string();
    let line_range = parse_line_range(obj.get("line_range"))?;

    let mut pheromone = Pheromone::new(
        target_path,
        ast_scope,
        kind,
        intensity,
        half_life_ms,
        issuer,
    );
    if let Some((start, end)) = line_range {
        pheromone = pheromone.with_line_range(start, end);
    }
    if let Some(metadata) = obj.get("metadata") {
        let map = metadata
            .as_object()
            .ok_or_else(|| RpcError::invalid_params("metadata must be an object of strings"))?;
        for (key, value) in map {
            let text = value
                .as_str()
                .ok_or_else(|| RpcError::invalid_params("metadata values must be strings"))?;
            pheromone = pheromone.with_metadata(key.clone(), text);
        }
    }

    let id = pheromone.id;
    let emitted_at_ms = pheromone.emitted_at_ms;
    let initial_intensity = pheromone.initial_intensity;
    let half_life_ms = pheromone.half_life_ms;
    let path_out = pheromone.target_path.clone();
    state.signals.emit(pheromone);
    state.persist_signals().map_err(RpcError::internal)?;
    Ok(json!({
        "id": id,
        "target_path": path_out,
        "emitted_at_ms": emitted_at_ms,
        "initial_intensity": initial_intensity,
        "half_life_ms": half_life_ms,
        "signals": state.signals.all().len(),
    }))
}

fn signal_read(state: &mut NodeState, params: &Value) -> Result<Value, RpcError> {
    let obj = params_object(params)?;
    let threshold = opt_f64(obj, &["threshold", "min_intensity"]).unwrap_or(0.0);
    let ignore_issuer = opt_str(obj, &["ignore_issuer"]).map(str::to_string);
    let now = now_ms();
    let path = opt_str(obj, &["target_path", "path"]).filter(|p| !p.is_empty());

    let signals: Vec<Value> = if let Some(path) = path {
        let scope = parse_string_vec(obj.get("ast_scope").or_else(|| obj.get("scope")))?;
        let line_range = parse_line_range(obj.get("line_range"))?;
        state
            .signals
            .sense_conflicts(
                path,
                &scope,
                line_range,
                threshold,
                now,
                ignore_issuer.as_deref(),
            )
            .into_iter()
            .map(|(pheromone, _)| pheromone_json(pheromone, now))
            .collect()
    } else {
        state
            .signals
            .all()
            .iter()
            .filter(|p| p.current_intensity(now) >= threshold)
            .filter(|p| {
                ignore_issuer
                    .as_deref()
                    .is_none_or(|issuer| p.issuer != issuer)
            })
            .map(|p| pheromone_json(p, now))
            .collect()
    };

    Ok(json!({"count": signals.len(), "signals": signals, "now_ms": now}))
}

fn proposal_put(state: &mut NodeState, params: &Value) -> Result<Value, RpcError> {
    let obj = params_object(params)?;
    let task_id = opt_uuid(obj, &["task_id"])?.unwrap_or_else(Uuid::new_v4);
    let target = opt_str(obj, &["target", "target_file"]).map(str::to_string);
    let required_votes = opt_u64(obj, &["required_votes"])
        .unwrap_or(DEFAULT_REQUIRED_VOTES as u64)
        .max(1) as usize;
    let skeleton = obj
        .get("skeleton")
        .cloned()
        .unwrap_or_else(|| params.clone());
    let proposal = Proposal {
        proposal_id: Uuid::new_v4(),
        task_id,
        target,
        skeleton,
        required_votes,
        votes: Vec::new(),
        status: "pending".into(),
        created_at_ms: now_ms(),
    };
    let response = json!({
        "proposal_id": proposal.proposal_id,
        "task_id": proposal.task_id,
        "status": proposal.status,
        "required_votes": proposal.required_votes,
    });
    state.proposals.insert(proposal.proposal_id, proposal);
    state.persist_proposals().map_err(RpcError::internal)?;
    Ok(response)
}

fn proposal_key(state: &NodeState, obj: &Map<String, Value>) -> Result<Uuid, RpcError> {
    if let Some(raw) = opt_str(obj, &["proposal_id", "id"]) {
        return Uuid::parse_str(raw)
            .map_err(|e| RpcError::invalid_params(format!("invalid proposal_id: {e}")));
    }
    if let Some(raw) = opt_str(obj, &["task_id"]) {
        let task_id = Uuid::parse_str(raw)
            .map_err(|e| RpcError::invalid_params(format!("invalid task_id: {e}")))?;
        return state
            .proposals
            .values()
            .find(|p| p.task_id == task_id)
            .map(|p| p.proposal_id)
            .ok_or_else(|| RpcError::invalid_params(format!("no proposal for task_id {task_id}")));
    }
    Err(RpcError::invalid_params(
        "missing 'proposal_id' (or 'task_id')",
    ))
}

fn proposal_vote(state: &mut NodeState, params: &Value) -> Result<Value, RpcError> {
    let obj = params_object(params)?;
    let key = proposal_key(state, obj)?;
    let validator_id = required_str(obj, &["validator_id"], "validator_id")?;
    let decision_raw = opt_str(obj, &["decision"]).unwrap_or_default();
    let decision = match decision_raw.to_ascii_lowercase().as_str() {
        "approve" | "approved" | "yes" | "accept" => "approve",
        "reject" | "rejected" | "no" | "deny" => "reject",
        other => {
            return Err(RpcError::invalid_params(format!(
                "decision must be 'approve' or 'reject', got '{other}'"
            )));
        }
    };
    let causal_lift = opt_f64(obj, &["causal_lift"]).unwrap_or(0.0);
    let signature = opt_str(obj, &["signature"]).map(str::to_string);
    if let Some(sig) = &signature {
        if sig.len() != 128 || !sig.chars().all(|c| c.is_ascii_hexdigit()) {
            return Err(RpcError::invalid_params(
                "signature must be 128 hex characters (64 bytes)",
            ));
        }
    }

    let vote = ProposalVote {
        validator_id,
        decision: decision.to_string(),
        causal_lift,
        signature,
        ts_ms: now_ms(),
    };

    let response = {
        let proposal = state
            .proposals
            .get_mut(&key)
            .ok_or_else(|| RpcError::invalid_params(format!("unknown proposal {key}")))?;
        if let Some(existing) = proposal
            .votes
            .iter_mut()
            .find(|v| v.validator_id == vote.validator_id)
        {
            *existing = vote;
        } else {
            proposal.votes.push(vote);
        }
        let approve = proposal
            .votes
            .iter()
            .filter(|v| v.decision == "approve")
            .count();
        let reject = proposal
            .votes
            .iter()
            .filter(|v| v.decision == "reject")
            .count();
        let net_lift: f64 = proposal.votes.iter().map(|v| v.causal_lift).sum();
        proposal.status = if approve >= proposal.required_votes && net_lift > 0.0 {
            "sealed".to_string()
        } else if reject >= proposal.required_votes
            || ((approve + reject) >= proposal.required_votes && net_lift <= 0.0)
        {
            "rejected".to_string()
        } else {
            "pending".to_string()
        };
        json!({
            "proposal_id": proposal.proposal_id,
            "task_id": proposal.task_id,
            "status": proposal.status,
            "approve": approve,
            "reject": reject,
            "votes": proposal.votes.len(),
            "net_lift": net_lift,
            "required_votes": proposal.required_votes,
        })
    };
    state.persist_proposals().map_err(RpcError::internal)?;
    Ok(response)
}

fn proposal_get(state: &mut NodeState, params: &Value) -> Result<Value, RpcError> {
    let obj = params_object(params)?;
    let key = proposal_key(state, obj)?;
    let proposal = state
        .proposals
        .get(&key)
        .ok_or_else(|| RpcError::invalid_params(format!("unknown proposal {key}")))?;
    Ok(json!({"proposal": proposal}))
}

/// Reads exactly one newline-terminated frame, bounded by `MAX_FRAME_BYTES`.
fn read_frame(reader: &mut BufReader<UnixStream>, buf: &mut Vec<u8>) -> std::io::Result<usize> {
    let n = {
        let mut limited = reader.take((MAX_FRAME_BYTES + 1) as u64);
        limited.read_until(b'\n', buf)?
    };
    if n > MAX_FRAME_BYTES && !buf.ends_with(b"\n") {
        // Oversized frame without a terminator yet: discard the rest of the line.
        let mut sink = Vec::new();
        loop {
            sink.clear();
            let mut limited = reader.take(64 * 1024);
            match limited.read_until(b'\n', &mut sink) {
                Ok(0) => break,
                Ok(_) if sink.ends_with(b"\n") => break,
                Ok(_) => continue,
                Err(e)
                    if e.kind() == std::io::ErrorKind::WouldBlock
                        || e.kind() == std::io::ErrorKind::TimedOut =>
                {
                    break;
                }
                Err(e) => return Err(e),
            }
        }
    }
    Ok(n)
}

fn handle_connection(
    stream: UnixStream,
    state: Arc<Mutex<NodeState>>,
    shutdown: Arc<AtomicBool>,
) -> std::io::Result<()> {
    stream.set_read_timeout(Some(CONNECTION_POLL_INTERVAL))?;
    let reader_stream = stream.try_clone()?;
    let mut reader = BufReader::new(reader_stream);
    let mut writer = BufWriter::new(stream);
    let mut buf: Vec<u8> = Vec::new();

    loop {
        buf.clear();
        let n = match read_frame(&mut reader, &mut buf) {
            Ok(n) => n,
            Err(e)
                if e.kind() == std::io::ErrorKind::WouldBlock
                    || e.kind() == std::io::ErrorKind::TimedOut =>
            {
                if shutdown.load(Ordering::SeqCst) {
                    return Ok(());
                }
                continue;
            }
            Err(e) => return Err(e),
        };
        if n == 0 {
            return Ok(());
        }

        let text = String::from_utf8_lossy(&buf);
        let trimmed = text.trim_end_matches('\n').trim_end_matches('\r');
        let response = {
            let mut guard = state
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            respond_to_frame(&mut guard, trimmed)
        };
        let mut bytes = serde_json::to_vec(&response).unwrap_or_else(|_| {
            br#"{"jsonrpc":"2.0","id":null,"error":{"code":-32603,"message":"response serialization failed"}}"#.to_vec()
        });
        bytes.push(b'\n');
        writer.write_all(&bytes)?;
        writer.flush()?;
    }
}

/// Binds the socket, loads the store, and serves until `shutdown` is flagged.
fn run_server(
    bind_path: &Path,
    store: Option<PathBuf>,
    shutdown: Arc<AtomicBool>,
    ready: Option<Sender<()>>,
) -> Result<(), String> {
    let listener = bind_listener(bind_path)?;
    listener
        .set_nonblocking(true)
        .map_err(|e| format!("set nonblocking on {}: {e}", bind_path.display()))?;
    let state = Arc::new(Mutex::new(NodeState::load(bind_path.to_path_buf(), store)?));

    if let Some(tx) = ready {
        let _ = tx.send(());
    }

    while !shutdown.load(Ordering::SeqCst) {
        match listener.accept() {
            Ok((stream, _)) => {
                let state = Arc::clone(&state);
                let shutdown = Arc::clone(&shutdown);
                std::thread::spawn(move || {
                    if let Err(e) = handle_connection(stream, state, shutdown) {
                        eprintln!("wm-node: connection error: {e}");
                    }
                });
            }
            Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                std::thread::sleep(ACCEPT_POLL_INTERVAL);
            }
            Err(e) => {
                eprintln!("wm-node: accept error: {e}");
                std::thread::sleep(ACCEPT_POLL_INTERVAL);
            }
        }
    }

    drop(listener);
    if bind_path.exists() {
        if let Err(e) = std::fs::remove_file(bind_path) {
            eprintln!(
                "wm-node: failed to remove socket {}: {e}",
                bind_path.display()
            );
        }
    }
    Ok(())
}

fn resolve_store(cli_store: Option<PathBuf>) -> Option<PathBuf> {
    if cli_store.is_some() {
        return cli_store;
    }
    std::env::var_os("WM_STORE")
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
}

fn resolve_socket(cli_socket: Option<PathBuf>, store: Option<&Path>) -> PathBuf {
    if let Some(p) = cli_socket {
        return p;
    }
    if let Some(p) = std::env::var_os("WM_NODE_SOCKET").filter(|v| !v.is_empty()) {
        return PathBuf::from(p);
    }
    if let Some(store) = store {
        return store.join(SOCKET_FILE_NAME);
    }
    if let Some(runtime) = std::env::var_os("XDG_RUNTIME_DIR").filter(|v| !v.is_empty()) {
        return PathBuf::from(runtime).join(SOCKET_FILE_NAME);
    }
    std::env::temp_dir().join(SOCKET_FILE_NAME)
}

fn main() {
    let cli = Cli::parse();
    let store = resolve_store(cli.store);
    let socket_path = resolve_socket(cli.socket, store.as_deref());

    let shutdown = Arc::new(AtomicBool::new(false));
    for signal in [SIGTERM, SIGINT] {
        if let Err(e) = signal_hook::flag::register(signal, Arc::clone(&shutdown)) {
            eprintln!("wm-node: failed to register signal {signal}: {e}");
            std::process::exit(1);
        }
    }

    let mode = store.as_ref().map_or_else(
        || "in-memory (no --store)".to_string(),
        |s| format!("store {}", s.display()),
    );
    eprintln!(
        "wm-node {} · {} · {}",
        env!("CARGO_PKG_VERSION"),
        socket_path.display(),
        mode
    );

    if let Err(e) = run_server(&socket_path, store, shutdown, None) {
        eprintln!("wm-node: {e}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::mpsc;

    fn temp_path(prefix: &str, ext: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        std::env::temp_dir().join(format!("{prefix}-{}-{nanos}.{ext}", std::process::id()))
    }

    struct TestNode {
        socket: PathBuf,
        shutdown: Arc<AtomicBool>,
        handle: Option<std::thread::JoinHandle<Result<(), String>>>,
    }

    impl TestNode {
        fn stop(mut self) -> Result<(), String> {
            self.shutdown.store(true, Ordering::SeqCst);
            self.handle
                .take()
                .expect("node handle already taken")
                .join()
                .expect("wm-node test thread panicked")
        }
    }

    impl Drop for TestNode {
        fn drop(&mut self) {
            self.shutdown.store(true, Ordering::SeqCst);
        }
    }

    fn start_node(store: Option<PathBuf>) -> TestNode {
        let socket = temp_path("wm-node-test", "sock");
        let shutdown = Arc::new(AtomicBool::new(false));
        let (tx, rx) = mpsc::channel::<()>();
        let handle = std::thread::spawn({
            let socket = socket.clone();
            let shutdown = Arc::clone(&shutdown);
            move || run_server(&socket, store, shutdown, Some(tx))
        });
        rx.recv_timeout(Duration::from_secs(10))
            .expect("wm-node test server did not become ready");
        TestNode {
            socket,
            shutdown,
            handle: Some(handle),
        }
    }

    struct TestConn {
        stream: UnixStream,
        reader: BufReader<UnixStream>,
    }

    impl TestConn {
        fn connect(socket: &Path) -> Self {
            let stream = UnixStream::connect(socket).expect("connect to test node");
            stream
                .set_read_timeout(Some(Duration::from_secs(5)))
                .expect("set read timeout");
            let reader = BufReader::new(stream.try_clone().expect("clone stream"));
            Self { stream, reader }
        }

        fn send(&mut self, raw: &str) {
            self.stream.write_all(raw.as_bytes()).expect("write frame");
            self.stream.flush().expect("flush frame");
        }

        fn read(&mut self) -> Value {
            let mut line = String::new();
            self.reader.read_line(&mut line).expect("read response");
            serde_json::from_str(&line).expect("parse response JSON")
        }

        fn request(&mut self, id: u64, method: &str, params: Value) -> Value {
            let request = json!({"jsonrpc": "2.0", "id": id, "method": method, "params": params});
            self.send(&format!("{request}\n"));
            self.read()
        }
    }

    #[test]
    fn roundtrip_status_put_get_take() {
        let node = start_node(None);
        let socket = node.socket.clone();
        let mut conn = TestConn::connect(&socket);

        let status = conn.request(1, "node.status", json!({}));
        assert_eq!(status["result"]["ok"], true);
        assert_eq!(status["result"]["protocol"], "wm-node/1");
        assert_eq!(status["result"]["store"], Value::Null);

        let put = conn.request(
            2,
            "tuple.put",
            json!({"kind": "Generic", "tag": "greet", "payload": "hello", "ttl_ms": 60000}),
        );
        let put_id = put["result"]["id"].clone();
        assert!(put_id.is_string(), "put id: {put}");

        let get = conn.request(3, "tuple.get", json!({"kind": "Generic", "tag": "greet"}));
        assert_eq!(get["result"]["count"], 1);
        assert_eq!(get["result"]["tuples"][0]["id"], put_id);

        // get is non-destructive
        let get_again = conn.request(4, "tuple.get", json!({"kind": "Generic", "tag": "greet"}));
        assert_eq!(get_again["result"]["count"], 1);

        let take = conn.request(5, "tuple.take", json!({"kind": "Generic", "tag": "greet"}));
        assert_eq!(take["result"]["found"], true);
        assert_eq!(take["result"]["tuple"]["id"], put_id);

        let take_again = conn.request(6, "tuple.take", json!({"kind": "Generic", "tag": "greet"}));
        assert_eq!(take_again["result"]["found"], false);
        assert_eq!(take_again["result"]["tuple"], Value::Null);

        drop(conn);
        assert!(socket.exists());
        node.stop().expect("graceful shutdown");
        assert!(!socket.exists(), "socket must be removed on shutdown");
    }

    #[test]
    fn malformed_frames_receive_error_lines() {
        let node = start_node(None);
        let mut conn = TestConn::connect(&node.socket);

        conn.send("definitely not json\n");
        let parsed = conn.read();
        assert_eq!(parsed["id"], Value::Null);
        assert_eq!(parsed["error"]["code"], PARSE_ERROR);

        let unknown = conn.request(8, "nope.method", json!({}));
        assert_eq!(unknown["error"]["code"], METHOD_NOT_FOUND);

        conn.send("{\"jsonrpc\":\"2.0\",\"id\":9}\n");
        let missing_method = conn.read();
        assert_eq!(missing_method["error"]["code"], INVALID_REQUEST);

        conn.send("{\"jsonrpc\":\"1.0\",\"id\":10,\"method\":\"node.status\"}\n");
        let bad_version = conn.read();
        assert_eq!(bad_version["error"]["code"], INVALID_REQUEST);

        let bad_params = conn.request(11, "tuple.put", json!({}));
        assert_eq!(bad_params["error"]["code"], INVALID_PARAMS);

        // Bad frame does not poison the connection.
        let status = conn.request(12, "node.status", json!({}));
        assert_eq!(status["result"]["ok"], true);

        drop(conn);
        node.stop().expect("graceful shutdown");
    }

    #[test]
    fn second_bind_is_refused_and_first_survives() {
        let node = start_node(None);
        let err = bind_listener(&node.socket).expect_err("second bind must fail");
        assert!(err.contains("already listening"), "unexpected error: {err}");

        let mut conn = TestConn::connect(&node.socket);
        let status = conn.request(1, "node.status", json!({}));
        assert_eq!(status["result"]["ok"], true);
        drop(conn);

        node.stop().expect("graceful shutdown");
    }

    #[test]
    fn tuple_space_semantics_and_expiry() {
        let node = start_node(None);
        let mut conn = TestConn::connect(&node.socket);

        conn.request(
            1,
            "tuple.put",
            json!({"tuple": {"kind": "Generic", "tag": "q", "payload": "1"}, "ttl_ms": 0}),
        );
        conn.request(
            2,
            "tuple.put",
            json!({"kind": "Generic", "tag": "q", "payload": "2", "ttl_ms": 0}),
        );

        let get = conn.request(3, "tuple.get", json!({"kind": "Generic", "tag": "q"}));
        assert_eq!(get["result"]["count"], 2);

        let take1 = conn.request(4, "tuple.take", json!({"kind": "Generic", "tag": "q"}));
        assert_eq!(take1["result"]["tuple"]["kind"]["Generic"]["payload"], "1");

        let get2 = conn.request(5, "tuple.get", json!({"kind": "Generic", "tag": "q"}));
        assert_eq!(get2["result"]["count"], 1);

        let take2 = conn.request(6, "tuple.take", json!({"kind": "Generic", "tag": "q"}));
        assert_eq!(take2["result"]["tuple"]["kind"]["Generic"]["payload"], "2");

        let get3 = conn.request(7, "tuple.get", json!({"kind": "Generic", "tag": "q"}));
        assert_eq!(get3["result"]["count"], 0);

        // TTL expiry: 1ms TTL, then wait past it.
        conn.request(
            8,
            "tuple.put",
            json!({"kind": "Generic", "tag": "expiring", "payload": "x", "ttl_ms": 1}),
        );
        std::thread::sleep(Duration::from_millis(15));
        let expired = conn.request(
            9,
            "tuple.get",
            json!({"kind": "Generic", "tag": "expiring"}),
        );
        assert_eq!(expired["result"]["count"], 0);

        // take rejects an id filter explicitly.
        let rejected = conn.request(10, "tuple.take", json!({"id": Uuid::new_v4().to_string()}));
        assert_eq!(rejected["error"]["code"], INVALID_PARAMS);

        drop(conn);
        node.stop().expect("graceful shutdown");
    }

    #[test]
    fn signal_emit_read_and_decay() {
        let node = start_node(None);
        let mut conn = TestConn::connect(&node.socket);

        let emit = conn.request(
            1,
            "signal.emit",
            json!({"path": "src/lib.rs", "scope": ["fn:main"], "kind": "MutationActive",
                   "intensity": 0.8, "half_life": 30000, "issuer": "opencode"}),
        );
        assert!(emit["result"]["id"].is_string());
        assert_eq!(emit["result"]["signals"], 1);

        let read = conn.request(2, "signal.read", json!({"path": "src/lib.rs"}));
        assert_eq!(read["result"]["count"], 1);
        let intensity = read["result"]["signals"][0]["current_intensity"]
            .as_f64()
            .expect("intensity");
        assert!((0.7..=0.81).contains(&intensity), "intensity {intensity}");

        let other = conn.request(3, "signal.read", json!({"path": "src/other.rs"}));
        assert_eq!(other["result"]["count"], 0);

        let all = conn.request(4, "signal.read", json!({}));
        assert_eq!(all["result"]["count"], 1);

        conn.request(
            5,
            "signal.emit",
            json!({"target_path": "src/lib.rs", "scope": "fn:helper", "intensity": 1.0,
                   "half_life_ms": 1000, "issuer": "antigravity"}),
        );
        let two = conn.request(6, "signal.read", json!({"path": "src/lib.rs"}));
        assert_eq!(two["result"]["count"], 2);

        let ignored = conn.request(
            7,
            "signal.read",
            json!({"path": "src/lib.rs", "ignore_issuer": "opencode"}),
        );
        assert_eq!(ignored["result"]["count"], 1);

        drop(conn);
        node.stop().expect("graceful shutdown");
    }

    #[test]
    fn proposal_scaffold_quorum_seals() {
        let node = start_node(None);
        let mut conn = TestConn::connect(&node.socket);

        let put = conn.request(
            1,
            "proposal.put",
            json!({"target": "src/x.rs", "required_votes": 2,
                   "skeleton": {"target_file": "src/x.rs", "deltas": []}}),
        );
        let proposal_id = put["result"]["proposal_id"].as_str().unwrap().to_string();
        assert_eq!(put["result"]["status"], "pending");

        let vote1 = conn.request(
            2,
            "proposal.vote",
            json!({"proposal_id": proposal_id, "validator_id": "validator-a",
                   "decision": "approve", "causal_lift": 0.4}),
        );
        assert_eq!(vote1["result"]["status"], "pending");
        assert_eq!(vote1["result"]["approve"], 1);

        let vote2 = conn.request(
            3,
            "proposal.vote",
            json!({"proposal_id": proposal_id, "validator_id": "validator-b",
                   "decision": "Approve", "causal_lift": 0.3}),
        );
        assert_eq!(vote2["result"]["status"], "sealed");
        assert_eq!(vote2["result"]["approve"], 2);

        let get = conn.request(4, "proposal.get", json!({"proposal_id": proposal_id}));
        assert_eq!(get["result"]["proposal"]["status"], "sealed");
        assert_eq!(
            get["result"]["proposal"]["votes"].as_array().unwrap().len(),
            2
        );

        drop(conn);
        node.stop().expect("graceful shutdown");
    }

    #[test]
    fn store_persistence_survives_restart() {
        let store = temp_path("wm-node-store", "dir");
        let node = start_node(Some(store.clone()));
        let mut conn = TestConn::connect(&node.socket);
        conn.request(
            1,
            "tuple.put",
            json!({"kind": "Generic", "tag": "durable", "payload": "kept", "ttl_ms": 0}),
        );
        drop(conn);
        node.stop().expect("graceful shutdown");

        let node2 = start_node(Some(store.clone()));
        let mut conn2 = TestConn::connect(&node2.socket);
        let get = conn2.request(1, "tuple.get", json!({"kind": "Generic", "tag": "durable"}));
        assert_eq!(get["result"]["count"], 1);
        assert_eq!(
            get["result"]["tuples"][0]["kind"]["Generic"]["payload"],
            "kept"
        );
        drop(conn2);
        node2.stop().expect("graceful shutdown");
        let _ = std::fs::remove_dir_all(&store);
    }
}
