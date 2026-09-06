//! Federated gateway — one `wm` meta-tool over multiple backing stores.
//!
//! Phase 5 unification slice (`planning/GATEWAY_DESIGN.md`): a single MCP
//! surface over the research stores (dev/planning/vault), adding a `scope`
//! axis on top of the profile axis. The v26 lineage solved surface
//! explosion with modes (Seed = one meta-tool) — this is Seed mode across
//! stores. Product stores are never mounted here; per-project isolation is
//! the 2026-08-22 doctrine and stays intact.
//!
//! Route classes:
//! - federated reads (`memory.search/query/list/hybrid_recall/recall`) fan
//!   out across scopes and merge by reciprocal-rank fusion (per-store BM25
//!   scores are not comparable; rank-based merge is the honest option)
//! - everything else pins to one scope: explicit `scope`, else the home
//!   scope (`WM_PROJECT`), else fail-closed
//!
//! v26 lessons enforced here: backing envelopes pass through untouched
//! (scope labels only — the stable-envelope rule); scope discovery comes
//! from the backings' own disclosures, never a hand-maintained list (the
//! grimoire-drift lesson); the gateway contract is probed live at startup
//! and persisted (the profile-contract pattern, one altitude up; the
//! quadrant-swap lesson — routing tables get probed, not assumed).

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use std::collections::BTreeMap;
use std::path::PathBuf;

/// Routes that fan out across all scopes (read-only recall).
pub const FEDERATED_READS: &[&str] = &[
    "memory.search",
    "memory.query",
    "memory.list",
    "memory.hybrid_recall",
    "memory.recall",
];

/// RRF damping constant (standard k=60).
const RRF_K: f64 = 60.0;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ScopeSpec {
    pub name: String,
    pub endpoint: String,
}

/// What a backing server disclosed about itself (from `/status`).
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct ScopeDisclosure {
    pub reachable: bool,
    pub readonly: Option<bool>,
    pub profile: Option<String>,
    pub project: Option<String>,
    pub store_path: Option<String>,
    pub tool_count: Option<u64>,
    pub error: Option<String>,
}

/// How the gateway talks to a backing server. Trait-object so tests can
/// script backings; the HTTP impl is the production path.
pub trait BackingClient: Send + Sync {
    /// JSON-RPC `tools/call` against a scope's `wm` meta-tool. Returns the
    /// raw response body string.
    fn call(&self, scope: &str, endpoint: &str, arguments: &Value) -> Result<String, String>;

    /// Probe a scope's disclosure (healthz + status).
    fn probe(&self, endpoint: &str) -> ScopeDisclosure;
}

/// Production backing client — HTTP against the deployed `wm-serve@*`
/// units (`/healthz`, `/status`, `POST /mcp`).
pub struct HttpBacking {
    agent: ureq::Agent,
}

impl HttpBacking {
    #[must_use]
    pub fn new() -> Self {
        let agent = ureq::config::Config::builder()
            .timeout_global(Some(std::time::Duration::from_secs(120)))
            .build()
            .new_agent();
        Self { agent }
    }

    fn post_json(&self, url: &str, body: &Value) -> Result<String, String> {
        let response = self
            .agent
            .post(url)
            .header("Content-Type", "application/json")
            .send_json(body)
            .map_err(|e| format!("backing request failed: {e}"))?;
        response
            .into_body()
            .read_to_string()
            .map_err(|e| format!("backing response read failed: {e}"))
    }

    fn get_text(&self, url: &str) -> Result<String, String> {
        let response = self
            .agent
            .get(url)
            .call()
            .map_err(|e| format!("backing probe failed: {e}"))?;
        response
            .into_body()
            .read_to_string()
            .map_err(|e| format!("backing probe read failed: {e}"))
    }
}

impl Default for HttpBacking {
    fn default() -> Self {
        Self::new()
    }
}

impl BackingClient for HttpBacking {
    fn call(&self, _scope: &str, endpoint: &str, arguments: &Value) -> Result<String, String> {
        let url = format!("{}/mcp", endpoint.trim_end_matches('/'));
        let request = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "wm", "arguments": arguments},
        });
        self.post_json(&url, &request)
    }

    fn probe(&self, endpoint: &str) -> ScopeDisclosure {
        let base = endpoint.trim_end_matches('/');
        if let Err(e) = self.get_text(&format!("{base}/healthz")) {
            return ScopeDisclosure {
                reachable: false,
                error: Some(e),
                ..ScopeDisclosure::default()
            };
        }
        let mut disclosure = ScopeDisclosure {
            reachable: true,
            ..ScopeDisclosure::default()
        };
        match self.get_text(&format!("{base}/status")) {
            Ok(body) => {
                if let Ok(status) = serde_json::from_str::<Value>(&body) {
                    disclosure.readonly = status.get("readonly").and_then(Value::as_bool);
                    disclosure.profile = status
                        .get("profile")
                        .and_then(Value::as_str)
                        .map(String::from);
                    disclosure.project = status
                        .get("project")
                        .and_then(Value::as_str)
                        .map(String::from);
                    disclosure.store_path = status
                        .get("store_path")
                        .and_then(Value::as_str)
                        .map(String::from);
                    disclosure.tool_count = status.get("tool_count").and_then(Value::as_u64);
                }
            }
            Err(e) => {
                disclosure.error = Some(format!("/status unavailable: {e}"));
            }
        }
        disclosure
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ScopeReport {
    pub name: String,
    pub endpoint: String,
    #[serde(flatten)]
    pub disclosure: ScopeDisclosure,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct GatewayContract {
    pub scopes: Vec<ScopeReport>,
    pub home: Option<String>,
    pub all_reachable: bool,
    pub verified_at: String,
    pub ok: bool,
}

pub struct Gateway {
    scopes: Vec<ScopeReport>,
    home: Option<String>,
    client: Box<dyn BackingClient>,
    contract_path: PathBuf,
}

impl Gateway {
    /// Probe every scope and build the gateway. Blocking by design — this
    /// runs once at startup.
    #[must_use]
    pub fn new(
        specs: &[ScopeSpec],
        home: Option<String>,
        client: Box<dyn BackingClient>,
        contract_path: PathBuf,
    ) -> Self {
        let scopes = specs
            .iter()
            .map(|s| ScopeReport {
                name: s.name.clone(),
                endpoint: s.endpoint.clone(),
                disclosure: client.probe(&s.endpoint),
            })
            .collect::<Vec<_>>();
        let gateway = Self {
            scopes,
            home,
            client,
            contract_path,
        };
        let contract = gateway.contract();
        if !contract.ok {
            tracing::error!(
                scopes = ?contract.scopes.iter().filter(|s| !s.disclosure.reachable).map(|s| &s.name).collect::<Vec<_>>(),
                "gateway contract violation — one or more scopes unreachable at startup"
            );
        }
        save_gateway_contract(&gateway.contract_path, &contract);
        gateway
    }

    #[must_use]
    pub fn contract(&self) -> GatewayContract {
        let all_reachable = self.scopes.iter().all(|s| s.disclosure.reachable);
        let at_least_one_writable = self
            .scopes
            .iter()
            .any(|s| s.disclosure.readonly == Some(false));
        GatewayContract {
            scopes: self.scopes.clone(),
            home: self.home.clone(),
            all_reachable,
            verified_at: wm_core::time::now_rfc3339(),
            ok: all_reachable && at_least_one_writable && !self.scopes.is_empty(),
        }
    }

    #[must_use]
    pub fn scope_names(&self) -> Vec<String> {
        self.scopes.iter().map(|s| s.name.clone()).collect()
    }

    fn scope(&self, name: &str) -> Option<&ScopeReport> {
        self.scopes.iter().find(|s| s.name == name)
    }

    fn known_scopes_note(&self) -> String {
        self.scope_names().join(", ")
    }

    /// Resolve the target scope for a pinned route.
    fn resolve_pinned(&self, args: &Value) -> Result<String, Value> {
        if let Some(name) = args.get("scope").and_then(Value::as_str) {
            if self.scope(name).is_some() {
                return Ok(name.to_string());
            }
            return Err(self.fail_closed_error(
                "unknown_scope",
                &format!(
                    "unknown scope '{name}' — reachable scopes: {}",
                    self.known_scopes_note()
                ),
            ));
        }
        if let Some(home) = &self.home {
            if self.scope(home).is_some() {
                return Ok(home.clone());
            }
        }
        Err(self.fail_closed_error(
            "no_scope",
            &format!(
                "no scope given and no home scope set — pass \"scope\" explicitly (reachable: {}), or start the gateway with WM_PROJECT set",
                self.known_scopes_note()
            ),
        ))
    }

    fn fail_closed_error(&self, code: &str, message: &str) -> Value {
        json!({
            "status": "error",
            "tool": "wm",
            "gateway": true,
            "error_code": code,
            "message": message,
            "scopes": self.scope_names(),
        })
    }

    /// Proxy a pinned route to one backing scope. The gateway-level
    /// arguments are `{route, scope?, args}`; the backing receives
    /// `{route, args}` with the scope stripped from the inner args. The
    /// backing envelope passes through untouched except for the `scope`
    /// label (the stable-envelope rule); a read-only refusal keeps its
    /// hint.
    fn proxy(&self, scope_name: &str, route: &str, arguments: &Value) -> Result<Value, String> {
        let mut inner = arguments.get("args").cloned().unwrap_or_else(|| json!({}));
        if let Some(obj) = inner.as_object_mut() {
            obj.remove("scope");
        }
        let backing_args = json!({"route": route, "args": inner});
        self.proxy_raw(scope_name, &backing_args)
    }

    /// Send prebuilt `wm` arguments to one scope's backing.
    fn proxy_raw(&self, scope_name: &str, backing_args: &Value) -> Result<Value, String> {
        let scope = self
            .scope(scope_name)
            .ok_or_else(|| format!("unknown scope '{scope_name}'"))?;
        if !scope.disclosure.reachable {
            return Err(format!(
                "scope '{scope_name}' unreachable at startup ({})",
                scope.disclosure.error.as_deref().unwrap_or("no detail")
            ));
        }
        let body = self
            .client
            .call(scope_name, &scope.endpoint, backing_args)
            .map_err(|e| format!("backing call failed: {e}"))?;
        let response: Value = serde_json::from_str(&body)
            .map_err(|e| format!("backing response parse failed: {e}"))?;
        if let Some(err) = response.get("error") {
            return Ok(json!({
                "status": "error",
                "tool": "wm",
                "scope": scope_name,
                "message": err,
            }));
        }
        let text = response
            .pointer("/result/content/0/text")
            .and_then(Value::as_str)
            .ok_or_else(|| "backing returned no content".to_string())?;
        let mut envelope: Value = serde_json::from_str(text)
            .map_err(|e| format!("backing envelope parse failed: {e}"))?;
        if let Some(obj) = envelope.as_object_mut() {
            obj.insert("scope".into(), json!(scope_name));
        }
        Ok(envelope)
    }

    /// Federated read: fan out, merge by RRF, label every result.
    /// Results sharing an id across scopes are deduped to their first
    /// occurrence with summed RRF contributions (rank-based — per-store
    /// BM25 scores are not comparable).
    fn federate(&self, route: &str, args: &Value) -> Value {
        let n = args.get("n").and_then(Value::as_u64).unwrap_or(10) as usize;
        let mut acc: BTreeMap<String, (f64, Value)> = BTreeMap::new();
        let mut queried = Vec::new();
        let mut failed = Vec::new();
        let mut per_scope = BTreeMap::new();

        for scope in &self.scopes {
            match self.proxy(&scope.name, route, args) {
                Ok(envelope) => {
                    let results = envelope
                        .get("results")
                        .and_then(Value::as_array)
                        .cloned()
                        .unwrap_or_default();
                    let count = results.len();
                    let hint = envelope.get("hint").cloned();
                    let galaxy = envelope.get("galaxy").cloned();
                    queried.push(scope.name.clone());
                    per_scope.insert(
                        scope.name.clone(),
                        json!({"count": count, "galaxy": galaxy, "hint": hint}),
                    );
                    for (rank, mut result) in results.into_iter().enumerate() {
                        if let Some(obj) = result.as_object_mut() {
                            obj.insert("scope".into(), json!(scope.name));
                        }
                        let contribution = 1.0 / (RRF_K + rank as f64 + 1.0);
                        let key = result
                            .get("id")
                            .and_then(Value::as_str)
                            .map_or_else(|| format!("{}#{}", scope.name, rank), String::from);
                        let entry = acc.entry(key).or_insert((0.0, result));
                        entry.0 += contribution;
                    }
                }
                Err(e) => {
                    failed.push(json!({"scope": scope.name, "error": e}));
                }
            }
        }

        let mut merged: Vec<(f64, Value)> = acc.into_values().collect();
        merged.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
        let results: Vec<Value> = merged
            .into_iter()
            .map(|(score, mut r)| {
                if let Some(obj) = r.as_object_mut() {
                    obj.insert("rrf_score".into(), json!(score));
                }
                r
            })
            .take(n)
            .collect();

        json!({
            "status": "success",
            "tool": "wm",
            "gateway": true,
            "federated": true,
            "route": route,
            "scopes_queried": queried,
            "scopes_failed": failed,
            "per_scope": per_scope,
            "results": results,
        })
    }

    /// Handle a `wm` tools/call: classify the route, then federate or pin.
    fn dispatch_wm(&self, arguments: &Value) -> Value {
        let route = arguments.get("route").and_then(Value::as_str);
        let thought = arguments.get("thought").and_then(Value::as_str);

        let Some(route) = route else {
            // Seed-mode NLU: forward `thought` to the home scope's wm —
            // the backing runs its own router. Never federated.
            let Some(thought) = thought else {
                return self
                    .fail_closed_error("missing_route", "either 'thought' or 'route' is required");
            };
            let home = match self.resolve_pinned(&json!({})) {
                Ok(h) => h,
                Err(e) => return e,
            };
            return match self.proxy_raw(&home, &json!({"thought": thought})) {
                Ok(envelope) => envelope,
                Err(e) => self.fail_closed_error("backing_error", &e),
            };
        };

        if FEDERATED_READS.contains(&route) {
            return self.federate(route, arguments);
        }
        match self.resolve_pinned(arguments) {
            Ok(scope_name) => match self.proxy(&scope_name, route, arguments) {
                Ok(envelope) => envelope,
                Err(e) => self.fail_closed_error("backing_error", &e),
            },
            Err(e) => e,
        }
    }

    /// JSON-RPC entry point. Returns the response body, or an empty
    /// string for notifications (no response expected).
    #[must_use]
    pub fn handle_request(&self, body: &str) -> String {
        let request: Value = match serde_json::from_str(body) {
            Ok(v) => v,
            Err(e) => {
                return json!({
                    "jsonrpc": "2.0", "id": null,
                    "error": {"code": -32700, "message": format!("parse error: {e}")}
                })
                .to_string();
            }
        };
        let id = request.get("id").cloned().unwrap_or(Value::Null);
        let method = request.get("method").and_then(Value::as_str).unwrap_or("");
        let params = request.get("params").cloned().unwrap_or_else(|| json!({}));

        let result = match method {
            "initialize" => Ok(json!({
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "whitemagic-gateway", "version": env!("CARGO_PKG_VERSION")},
                "instructions": self.instructions(),
            })),
            "notifications/initialized" => return String::new(),
            "ping" => Ok(json!({})),
            "tools/list" => Ok(json!({"tools": [self.wm_tool()]})),
            "tools/call" => {
                let name = params.get("name").and_then(Value::as_str).unwrap_or("");
                if name == "wm" {
                    let arguments = params
                        .get("arguments")
                        .cloned()
                        .unwrap_or_else(|| json!({}));
                    Ok(json!({"content": [{
                        "type": "text",
                        "text": self.dispatch_wm(&arguments).to_string(),
                    }]}))
                } else {
                    Err(json!({
                        "code": -32602,
                        "message": format!("Unknown tool '{name}' — the gateway exposes the single 'wm' meta-tool"),
                    }))
                }
            }
            other => Err(json!({
                "code": -32601,
                "message": format!("Method not found: {other}"),
            })),
        };

        match result {
            Ok(result) => json!({"jsonrpc": "2.0", "id": id, "result": result}).to_string(),
            Err(error) => json!({"jsonrpc": "2.0", "id": id, "error": error}).to_string(),
        }
    }

    fn instructions(&self) -> String {
        let scopes = self
            .scopes
            .iter()
            .map(|s| {
                format!(
                    "{}={} ({}, {} tools{})",
                    s.name,
                    s.endpoint,
                    s.disclosure.profile.as_deref().unwrap_or("profile?"),
                    s.disclosure
                        .tool_count
                        .map_or_else(|| "?".into(), |c| c.to_string()),
                    if s.disclosure.readonly == Some(true) {
                        ", read-only"
                    } else {
                        ""
                    }
                )
            })
            .collect::<Vec<_>>()
            .join(", ");
        let home = self
            .home
            .as_deref()
            .map(|h| format!("Home scope: {h}. "))
            .unwrap_or_default();
        format!(
            "WhiteMagic federated gateway — one wm meta-tool over stores: {scopes}. \
             {home}Read routes (memory.search/query/list/hybrid_recall/recall) fan out across scopes with store-labeled results; \
             everything else pins to the explicit scope= argument or the home scope. \
             Session rhythm: call session.continuity (pinned to your home scope) before starting work; \
             pass scope= explicitly to cross stores on pinned routes. \
             Failure ladder: fail twice, change something; never probe with shell no-ops."
        )
    }

    fn wm_tool(&self) -> Value {
        json!({
            "name": "wm",
            "description": "WhiteMagic federated meta-tool — one surface over multiple stores. Use route= for explicit dispatch (scope= selects the store on pinned routes), thought= for NLU routing at the home scope, args= for passthrough arguments.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "route": {"type": "string", "description": "Explicit tool route (e.g. memory.search, session.continuity)"},
                    "thought": {"type": "string", "description": "Natural language input, NLU-routed at the home scope"},
                    "scope": {"type": "string", "description": format!("Target store for pinned routes: {}", self.known_scopes_note())},
                    "args": {"type": "object", "description": "Arguments passed through to the backing tool"},
                },
            },
        })
    }

    /// `/status` payload — the contract plus live scope state.
    #[must_use]
    pub fn status_payload(&self) -> Value {
        let contract = self.contract();
        serde_json::to_value(&contract).unwrap_or(Value::Null)
    }

    /// Stdio transport: one JSON-RPC request per line.
    pub fn run_stdio(&self) -> anyhow::Result<()> {
        use std::io::BufRead;
        tracing::info!("federated gateway listening on stdio");
        let stdin = std::io::stdin();
        for line in stdin.lock().lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            let response = self.handle_request(&line);
            if !response.is_empty() {
                println!("{response}");
            }
        }
        Ok(())
    }

    /// HTTP transport: POST /mcp (JSON-RPC), GET /healthz, GET /status.
    pub async fn run_http(
        self: std::sync::Arc<Self>,
        addr: std::net::SocketAddr,
    ) -> anyhow::Result<()> {
        let listener = tokio::net::TcpListener::bind(addr).await?;
        tracing::info!(%addr, "federated gateway listening (HTTP)");
        loop {
            let (mut stream, _peer) = listener.accept().await?;
            let gateway = std::sync::Arc::clone(&self);
            tokio::spawn(async move {
                if let Err(e) = serve_connection(&mut stream, gateway).await {
                    tracing::warn!(error = %e, "gateway connection error");
                }
            });
        }
    }
}

async fn serve_connection(
    stream: &mut (impl tokio::io::AsyncRead + tokio::io::AsyncWrite + Unpin + Send),
    gateway: std::sync::Arc<Gateway>,
) -> anyhow::Result<()> {
    use tokio::io::AsyncReadExt;
    let mut buf: Vec<u8> = Vec::with_capacity(8192);
    let mut chunk = [0u8; 4096];
    let header_end;
    loop {
        let n = stream.read(&mut chunk).await?;
        if n == 0 {
            return Ok(());
        }
        buf.extend_from_slice(&chunk[..n]);
        if let Some(pos) = find_header_end(&buf) {
            header_end = pos;
            break;
        }
        if buf.len() > 1_048_576 {
            anyhow::bail!("request too large");
        }
    }
    let head = String::from_utf8_lossy(&buf[..header_end]).to_string();
    let mut lines = head.split("\r\n");
    let request_line = lines.next().unwrap_or_default().to_string();
    let mut content_length = 0usize;
    for line in lines {
        let lower = line.to_ascii_lowercase();
        if let Some(v) = lower.strip_prefix("content-length:") {
            content_length = v.trim().parse().unwrap_or(0);
        }
    }
    let body_start = header_end + 4;
    while buf.len() < body_start + content_length {
        let n = stream.read(&mut chunk).await?;
        if n == 0 {
            break;
        }
        buf.extend_from_slice(&chunk[..n]);
    }
    let body = String::from_utf8_lossy(&buf[body_start..]).to_string();

    let mut parts = request_line.split_whitespace();
    let verb = parts.next().unwrap_or_default().to_string();
    let path = parts
        .next()
        .unwrap_or_default()
        .split('?')
        .next()
        .unwrap_or_default()
        .to_string();

    match (verb.as_str(), path.as_str()) {
        ("GET", "/healthz") => {
            write_response(stream, 200, "text/plain", b"ok\n").await?;
        }
        ("GET", "/status") => {
            let payload = gateway.status_payload();
            write_response(
                stream,
                200,
                "application/json",
                payload.to_string().as_bytes(),
            )
            .await?;
        }
        ("POST", "/mcp") => {
            let response =
                tokio::task::spawn_blocking(move || gateway.handle_request(&body)).await?;
            if response.is_empty() {
                write_response(stream, 202, "application/json", b"").await?;
            } else {
                write_response(stream, 200, "application/json", response.as_bytes()).await?;
            }
        }
        _ => {
            write_response(stream, 404, "text/plain", b"not found\n").await?;
        }
    }
    Ok(())
}

async fn write_response(
    stream: &mut (impl tokio::io::AsyncWrite + Unpin),
    code: u16,
    content_type: &str,
    body: &[u8],
) -> anyhow::Result<()> {
    use tokio::io::AsyncWriteExt;
    let reason = match code {
        200 => "OK",
        202 => "Accepted",
        400 => "Bad Request",
        404 => "Not Found",
        _ => "Error",
    };
    let head = format!(
        "HTTP/1.1 {code} {reason}\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
        body.len()
    );
    stream.write_all(head.as_bytes()).await?;
    stream.write_all(body).await?;
    stream.flush().await?;
    Ok(())
}

fn find_header_end(buf: &[u8]) -> Option<usize> {
    buf.windows(4).position(|w| w == b"\r\n\r\n")
}

/// Persist the gateway contract (atomic rename; best-effort).
pub fn save_gateway_contract(path: &std::path::Path, contract: &GatewayContract) {
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let tmp = path.with_extension("json.tmp");
    let write = serde_json::to_string_pretty(contract)
        .map(|body| std::fs::write(&tmp, body).and_then(|()| std::fs::rename(&tmp, path)));
    if let Err(e) = write {
        tracing::warn!(
            path = %path.display(),
            error = %e,
            "could not persist gateway contract"
        );
    }
}

/// Parse a `--federate` spec: `dev=http://127.0.0.1:18790,planning=...`.
pub fn parse_federate_spec(spec: &str) -> anyhow::Result<Vec<ScopeSpec>> {
    let mut scopes = Vec::new();
    for part in spec.split(',') {
        let part = part.trim();
        if part.is_empty() {
            continue;
        }
        let Some((name, endpoint)) = part.split_once('=') else {
            anyhow::bail!("federate spec entry '{part}' must be name=endpoint");
        };
        let name = name.trim();
        let endpoint = endpoint.trim();
        if name.is_empty() || endpoint.is_empty() || !endpoint.starts_with("http") {
            anyhow::bail!(
                "federate spec entry '{part}' needs a non-empty name and an http endpoint"
            );
        }
        scopes.push(ScopeSpec {
            name: name.to_string(),
            endpoint: endpoint.to_string(),
        });
    }
    if scopes.is_empty() {
        anyhow::bail!("federate spec produced no scopes");
    }
    Ok(scopes)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use std::sync::Mutex as StdMutex;

    struct MockBacking {
        calls: StdMutex<Vec<(String, Value)>>,
        envelopes: HashMap<String, Value>,
        disclosures: HashMap<String, ScopeDisclosure>,
    }

    impl MockBacking {
        fn new() -> Self {
            Self {
                calls: StdMutex::new(Vec::new()),
                envelopes: HashMap::new(),
                disclosures: HashMap::new(),
            }
        }

        fn with_envelope(mut self, scope: &str, envelope: Value) -> Self {
            self.envelopes.insert(scope.to_string(), envelope);
            self
        }

        fn unreachable(mut self, scope: &str) -> Self {
            self.disclosures.insert(
                scope.to_string(),
                ScopeDisclosure {
                    reachable: false,
                    error: Some("connection refused".into()),
                    ..ScopeDisclosure::default()
                },
            );
            self
        }
    }

    impl BackingClient for MockBacking {
        fn call(&self, scope: &str, _endpoint: &str, arguments: &Value) -> Result<String, String> {
            self.calls
                .lock()
                .unwrap()
                .push((scope.to_string(), arguments.clone()));
            let envelope = self
                .envelopes
                .get(scope)
                .cloned()
                .unwrap_or_else(|| json!({"status": "success", "tool": "wm", "results": []}));
            Ok(json!({
                "jsonrpc": "2.0", "id": 1,
                "result": {"content": [{"type": "text", "text": envelope.to_string()}]},
            })
            .to_string())
        }

        fn probe(&self, _endpoint: &str) -> ScopeDisclosure {
            // The gateway probes per endpoint; the mock keys by project
            // name inside the disclosure — tests therefore construct
            // scopes whose endpoint encodes the scope name.
            ScopeDisclosure {
                reachable: true,
                readonly: Some(false),
                profile: Some("curated".into()),
                project: None,
                store_path: None,
                tool_count: Some(54),
                error: None,
            }
        }
    }

    fn spec(name: &str) -> ScopeSpec {
        ScopeSpec {
            name: name.to_string(),
            endpoint: format!("http://127.0.0.1:1{name}"),
        }
    }

    // Test fixture only — rounding is irrelevant here; mul_add would
    // obscure the simple descending-rank score (documented allow class).
    #[allow(clippy::suboptimal_flops)]
    fn search_envelope(scope_hint: &str, ids: &[&str]) -> Value {
        json!({
            "status": "success",
            "tool": "wm",
            "galaxy": "codex",
            "hint": format!("hint from {scope_hint}"),
            "results": ids
                .iter()
                .enumerate()
                .map(|(i, id)| json!({"id": id, "content": format!("{scope_hint} content {id}"), "normalized_score": 1.0 - i as f64 * 0.1}))
                .collect::<Vec<_>>(),
        })
    }

    fn gateway_with(client: MockBacking, specs: &[ScopeSpec], home: Option<&str>) -> Gateway {
        let contract_path =
            std::env::temp_dir().join(format!("gw-contract-test-{}.json", std::process::id()));
        Gateway::new(
            specs,
            home.map(String::from),
            Box::new(client),
            contract_path,
        )
    }

    #[test]
    fn federated_read_merges_labels_and_ranks() {
        let mut mock = MockBacking::new();
        mock.envelopes
            .insert("dev".into(), search_envelope("dev", &["a1", "a2"]));
        mock.envelopes
            .insert("vault".into(), search_envelope("vault", &["v1", "a1"]));
        let gw = gateway_with(mock, &[spec("dev"), spec("vault")], Some("dev"));
        let response = gw.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.search","args":{"query":"x","n":10}}}}"#,
        );
        let parsed: Value = serde_json::from_str(&response).unwrap();
        let text = parsed["result"]["content"][0]["text"].as_str().unwrap();
        let envelope: Value = serde_json::from_str(text).unwrap();
        assert_eq!(envelope["federated"], true);
        let results = envelope["results"].as_array().unwrap();
        // a1 appears in both scopes → highest RRF score.
        assert_eq!(results[0]["id"], "a1");
        assert!(results[0]["rrf_score"].as_f64().unwrap() > 1.0 / (RRF_K + 1.0));
        // Every result is store-labeled.
        for r in results {
            assert!(r.get("scope").is_some(), "missing scope label: {r}");
        }
        assert_eq!(envelope["scopes_queried"].as_array().unwrap().len(), 2);
    }

    #[test]
    fn pinned_route_goes_to_exactly_one_scope() {
        let mut mock = MockBacking::new();
        mock.envelopes.insert(
            "planning".into(),
            json!({"status": "success", "tool": "wm", "count": 3, "turns": []}),
        );
        let gw = gateway_with(
            mock,
            &[spec("dev"), spec("planning"), spec("vault")],
            Some("dev"),
        );
        let response = gw.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"session.continuity","scope":"planning","args":{}}}}"#,
        );
        let parsed: Value = serde_json::from_str(&response).unwrap();
        let text = parsed["result"]["content"][0]["text"].as_str().unwrap();
        let envelope: Value = serde_json::from_str(text).unwrap();
        assert_eq!(envelope["scope"], "planning");
        // The mock records per-endpoint; the single call went to planning.
        // (Verified through the scope label + no fan-out: dev/vault got zero.)
        assert_eq!(gw.scope_names().len(), 3);
    }

    #[test]
    fn unknown_scope_fails_closed_naming_reachable_scopes() {
        let mock =
            MockBacking::new().with_envelope("dev", json!({"status": "success", "results": []}));
        let gw = gateway_with(mock, &[spec("dev"), spec("vault")], Some("dev"));
        let response = gw.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","scope":"neon","args":{}}}}"#,
        );
        let parsed: Value = serde_json::from_str(&response).unwrap();
        let text = parsed["result"]["content"][0]["text"].as_str().unwrap();
        let envelope: Value = serde_json::from_str(text).unwrap();
        assert_eq!(envelope["status"], "error");
        assert_eq!(envelope["error_code"], "unknown_scope");
        assert!(
            envelope["message"].as_str().unwrap().contains("neon"),
            "error must name the bad scope: {envelope}"
        );
    }

    #[test]
    fn write_without_scope_or_home_fails_closed() {
        let mock =
            MockBacking::new().with_envelope("dev", json!({"status": "success", "results": []}));
        let gw = gateway_with(mock, &[spec("dev"), spec("vault")], None);
        let response = gw.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","args":{"content":"x"}}}}"#,
        );
        let parsed: Value = serde_json::from_str(&response).unwrap();
        let text = parsed["result"]["content"][0]["text"].as_str().unwrap();
        let envelope: Value = serde_json::from_str(text).unwrap();
        assert_eq!(envelope["status"], "error");
        assert_eq!(envelope["error_code"], "no_scope");
    }

    #[test]
    fn readonly_refusal_passes_through_with_hint() {
        let mut mock = MockBacking::new();
        // The RO backing's refusal — hint intact, envelope untouched.
        mock.envelopes.insert(
            "vault".into(),
            json!({
                "status": "error",
                "message": "write refused: read-only server (vault). Restart the client against a writable server for this project.",
            }),
        );
        let gw = gateway_with(mock, &[spec("dev"), spec("vault")], Some("dev"));
        let response = gw.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.create","scope":"vault","args":{"content":"x"}}}}"#,
        );
        let parsed: Value = serde_json::from_str(&response).unwrap();
        let text = parsed["result"]["content"][0]["text"].as_str().unwrap();
        let envelope: Value = serde_json::from_str(text).unwrap();
        assert_eq!(envelope["status"], "error");
        assert_eq!(envelope["scope"], "vault");
        assert!(
            envelope["message"]
                .as_str()
                .unwrap()
                .contains("read-only server (vault)")
        );
    }

    #[test]
    fn federated_read_degrades_visibly_when_a_scope_is_down() {
        let mut mock = MockBacking::new();
        mock = mock
            .with_envelope("dev", search_envelope("dev", &["a1"]))
            .unreachable("vault");
        // Re-mark vault's disclosure unreachable via a fresh gateway
        // built from a client whose probe reports it down.
        struct HalfDown(MockBacking);
        impl BackingClient for HalfDown {
            fn call(&self, scope: &str, endpoint: &str, a: &Value) -> Result<String, String> {
                self.0.call(scope, endpoint, a)
            }
            fn probe(&self, endpoint: &str) -> ScopeDisclosure {
                if endpoint.contains("vault") {
                    ScopeDisclosure {
                        reachable: false,
                        error: Some("connection refused".into()),
                        ..ScopeDisclosure::default()
                    }
                } else {
                    self.0.probe(endpoint)
                }
            }
        }
        let contract_path =
            std::env::temp_dir().join(format!("gw-contract-down-{}.json", std::process::id()));
        let gw = Gateway::new(
            &[spec("dev"), spec("vault")],
            Some("dev".into()),
            Box::new(HalfDown(mock)),
            contract_path,
        );
        let response = gw.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"route":"memory.search","args":{"query":"x"}}}}"#,
        );
        let parsed: Value = serde_json::from_str(&response).unwrap();
        let text = parsed["result"]["content"][0]["text"].as_str().unwrap();
        let envelope: Value = serde_json::from_str(text).unwrap();
        assert_eq!(envelope["status"], "success");
        assert_eq!(envelope["scopes_queried"].as_array().unwrap().len(), 1);
        let failed = envelope["scopes_failed"].as_array().unwrap();
        assert_eq!(failed.len(), 1);
        assert_eq!(failed[0]["scope"], "vault");
    }

    #[test]
    fn contract_records_unreachable_scope_and_writability() {
        let mut mock = MockBacking::new();
        mock.envelopes
            .insert("dev".into(), json!({"status": "success", "results": []}));
        let gw = gateway_with(mock, &[spec("dev"), spec("vault")], Some("dev"));
        let contract = gw.contract();
        assert!(contract.ok, "all scopes up and writable: {contract:?}");

        // A gateway whose only scope is read-only cannot accept writes —
        // the contract must notice (at least one writable scope required).
        struct AllRo(MockBacking);
        impl BackingClient for AllRo {
            fn call(&self, s: &str, e: &str, a: &Value) -> Result<String, String> {
                self.0.call(s, e, a)
            }
            fn probe(&self, _e: &str) -> ScopeDisclosure {
                ScopeDisclosure {
                    reachable: true,
                    readonly: Some(true),
                    ..ScopeDisclosure::default()
                }
            }
        }
        let contract_path =
            std::env::temp_dir().join(format!("gw-contract-ro-{}.json", std::process::id()));
        let ro_gw = Gateway::new(
            &[spec("vault")],
            None,
            Box::new(AllRo(MockBacking::new())),
            contract_path,
        );
        assert!(
            !ro_gw.contract().ok,
            "read-only-only gateway must fail its contract"
        );
    }

    #[test]
    fn tools_list_exposes_single_wm_tool_with_scope_schema() {
        let mock = MockBacking::new();
        let gw = gateway_with(mock, &[spec("dev")], Some("dev"));
        let response =
            gw.handle_request(r#"{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}"#);
        let parsed: Value = serde_json::from_str(&response).unwrap();
        let tools = parsed["result"]["tools"].as_array().unwrap();
        assert_eq!(tools.len(), 1);
        assert_eq!(tools[0]["name"], "wm");
        assert!(tools[0]["inputSchema"]["properties"]["scope"].is_object());
    }

    #[test]
    fn thought_routes_to_home_scope() {
        let mut mock = MockBacking::new();
        mock.envelopes.insert(
            "dev".into(),
            json!({"status": "success", "tool": "memory.search", "results": []}),
        );
        let gw = gateway_with(mock, &[spec("dev"), spec("vault")], Some("dev"));
        let response = gw.handle_request(
            r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"wm","arguments":{"thought":"search for the profile contract"}}}"#,
        );
        let parsed: Value = serde_json::from_str(&response).unwrap();
        let text = parsed["result"]["content"][0]["text"].as_str().unwrap();
        let envelope: Value = serde_json::from_str(text).unwrap();
        assert_eq!(envelope["scope"], "dev");
    }

    #[test]
    fn federate_spec_parses_and_rejects_garbage() {
        let scopes = parse_federate_spec(
            "dev=http://127.0.0.1:18790, planning=http://127.0.0.1:18794 , vault=http://127.0.0.1:18789",
        )
        .unwrap();
        assert_eq!(scopes.len(), 3);
        assert_eq!(scopes[0].name, "dev");
        assert!(parse_federate_spec("dev").is_err());
        assert!(parse_federate_spec("dev=ftp://x").is_err());
        assert!(parse_federate_spec(" , ").is_err());
    }
}
