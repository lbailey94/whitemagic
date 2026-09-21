//! `wm selftest` — a five-second end-to-end invariant check on a throwaway store.
//!
//! Intended for installs, updates, bug reports, CI, and agents that
//! want to verify their own memory layer before trusting it.
//!
//! Every check is local, deterministic, and touches only a temporary
//! namespace; real memories are never read or written. The report is also
//! machine-readable (`--json`) so an updater can refuse to commit an upgrade
//! whose candidate binary fails its own selftest.

#![forbid(unsafe_code)]

use serde::Serialize;
use serde_json::{Value, json};
use std::time::Instant;

use crate::McpServer;

/// One selftest check result.
#[derive(Debug, Clone, Serialize)]
pub struct Check {
    /// Stable machine name.
    pub name: &'static str,
    /// Whether the invariant held.
    pub ok: bool,
    /// Human-readable detail (paths, ids, counts).
    pub detail: String,
    /// Wall time for this check.
    pub ms: u128,
}

/// The full selftest report.
#[derive(Debug, Clone, Serialize)]
pub struct Report {
    /// Binary version under test.
    pub version: String,
    /// True when every check passed (serialized for the updater gate).
    pub passed: bool,
    /// Individual checks, in execution order.
    pub checks: Vec<Check>,
    /// Total wall time.
    pub total_ms: u128,
}

impl Report {
    /// True when every check passed.
    #[must_use]
    pub fn passed(&self) -> bool {
        self.checks.iter().all(|c| c.ok)
    }

    /// `passed/total` summary.
    #[must_use]
    pub fn score(&self) -> (usize, usize) {
        (
            self.checks.iter().filter(|c| c.ok).count(),
            self.checks.len(),
        )
    }
}

pub(crate) async fn call(server: &mut McpServer, id: u64, route: &str, args: Value) -> Value {
    let req = json!({
        "jsonrpc": "2.0", "id": id, "method": "tools/call",
        "params": {"name": "wm", "arguments": {"route": route, "args": args}}
    });
    let resp = server.handle_request(&req.to_string()).await;
    let v: Value = serde_json::from_str(&resp).unwrap_or_default();
    let text = v
        .pointer("/result/content/0/text")
        .and_then(Value::as_str)
        .unwrap_or("{}");
    serde_json::from_str(text).unwrap_or_else(|_| json!({}))
}

pub(crate) async fn handshake(server: &mut McpServer) -> Value {
    let req = json!({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "wm-selftest", "version": "0"}}
    });
    let resp = server.handle_request(&req.to_string()).await;
    serde_json::from_str(&resp).unwrap_or_default()
}

fn check(name: &'static str, ok: bool, detail: String, started: Instant) -> Check {
    Check {
        name,
        ok,
        detail,
        ms: started.elapsed().as_millis(),
    }
}

/// Run the full selftest and return the report. Errors only on infrastructure
/// failure (cannot create the temp namespace); individual invariants land in
/// the report as failed checks instead.
pub async fn run() -> anyhow::Result<Report> {
    let overall = Instant::now();
    let mut checks: Vec<Check> = Vec::new();
    let version = env!("CARGO_PKG_VERSION").to_string();

    // 1. Binary — running at all proves loadability; report identity.
    {
        let t = Instant::now();
        let exe = std::env::current_exe().map(|p| p.display().to_string());
        let size = exe
            .as_ref()
            .ok()
            .and_then(|p| std::fs::metadata(p).ok())
            .map_or(0, |m| m.len());
        checks.push(check(
            "binary",
            exe.is_ok(),
            format!(
                "{} ({} bytes, v{version})",
                exe.unwrap_or_else(|e| format!("unreadable: {e}")),
                size
            ),
            t,
        ));
    }

    // 2. Throwaway store.
    let tmp = tempfile::tempdir()?;
    let store_path = tmp.path().join("lmdb");
    let t = Instant::now();
    let mut server = match McpServer::with_defaults(&store_path) {
        Ok(s) => {
            checks.push(check(
                "store_open",
                true,
                format!("temp store at {}", store_path.display()),
                t,
            ));
            s
        }
        Err(e) => {
            checks.push(check("store_open", false, format!("open failed: {e}"), t));
            let passed = checks.iter().all(|c| c.ok);
            return Ok(Report {
                version,
                passed,
                checks,
                total_ms: overall.elapsed().as_millis(),
            });
        }
    };

    // 3. MCP handshake.
    {
        let t = Instant::now();
        let v = handshake(&mut server).await;
        let ok = v.get("result").is_some();
        checks.push(check(
            "mcp_handshake",
            ok,
            if ok {
                "initialize answered".to_string()
            } else {
                format!("initialize failed: {v}")
            },
            t,
        ));
    }

    // 4. Registry surface.
    {
        let t = Instant::now();
        let v = call(&mut server, 4, "tools.list", json!({})).await;
        let count = v.get("tools").and_then(Value::as_array).map_or(0, Vec::len);
        checks.push(check(
            "registry",
            count > 0,
            format!("{count} routes in the tool catalog"),
            t,
        ));
    }

    // 5. Memory write + read.
    let token = format!("wm-selftest-{}", std::process::id());
    let created_id: String = {
        let t = Instant::now();
        let created = call(
            &mut server,
            5,
            "memory.create",
            json!({"content": format!("selftest marker {token}"), "tags": ["selftest"]}),
        )
        .await;
        let id = created
            .get("id")
            .and_then(Value::as_str)
            .unwrap_or("")
            .to_string();
        let ok_create = created.get("status").and_then(Value::as_str) == Some("success");
        let read = call(
            &mut server,
            6,
            "memory.read",
            json!({"id": id, "galaxy": "codex"}),
        )
        .await;
        let ok_read = read
            .get("content")
            .and_then(Value::as_str)
            .is_some_and(|c| c.contains(&token));
        checks.push(check(
            "memory_write_read",
            ok_create && ok_read,
            format!("id={id}"),
            t,
        ));
        id
    };

    // 6. Live search sees the write (index visibility within one process).
    {
        let t = Instant::now();
        let found = call(
            &mut server,
            7,
            "memory.search",
            json!({"query": token, "limit": 5}),
        )
        .await;
        let hit = found
            .get("results")
            .and_then(Value::as_array)
            .is_some_and(|rs| {
                rs.iter().any(|r| {
                    r.get("id").and_then(Value::as_str) == Some(created_id.as_str())
                        || r.get("content")
                            .and_then(Value::as_str)
                            .is_some_and(|c| c.contains(&token))
                })
            });
        checks.push(check(
            "search_live",
            hit,
            format!(
                "recall_mode={}",
                found
                    .get("recall_mode")
                    .and_then(Value::as_str)
                    .unwrap_or("?")
            ),
            t,
        ));
    }

    // 7. Session continuity skips the empty newest session.
    {
        let t = Instant::now();
        call(
            &mut server,
            8,
            "session.start",
            json!({"title": "selftest A"}),
        )
        .await;
        call(
            &mut server,
            9,
            "session.record",
            json!({"content": "selftest decision", "role": "user", "turn_type": "decision"}),
        )
        .await;
        call(
            &mut server,
            10,
            "session.start",
            json!({"title": "selftest B (empty)"}),
        )
        .await;
        let cont = call(&mut server, 11, "session.continuity", json!({"n": 5})).await;
        let count = cont.get("count").and_then(Value::as_u64).unwrap_or(0);
        checks.push(check(
            "session_continuity",
            count >= 1,
            format!("recovered {count} turn(s) from the prior session"),
            t,
        ));
    }

    // 8. Restart persistence — drop the server, reopen, read again.
    {
        let t = Instant::now();
        drop(server);
        let mut server2 = McpServer::with_defaults(&store_path)?;
        let read = call(
            &mut server2,
            12,
            "memory.read",
            json!({"id": created_id, "galaxy": "codex"}),
        )
        .await;
        let ok = read
            .get("content")
            .and_then(Value::as_str)
            .is_some_and(|c| c.contains(&token));
        checks.push(check(
            "restart_persistence",
            ok,
            "marker survived a store close/reopen".to_string(),
            t,
        ));
    }

    let passed = checks.iter().all(|c| c.ok);
    Ok(Report {
        version,
        passed,
        checks,
        total_ms: overall.elapsed().as_millis(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn selftest_passes_on_clean_install() {
        let report = run().await.expect("selftest infrastructure");
        assert!(
            report.passed(),
            "selftest must pass on a clean store: {report:?}"
        );
        assert!(report.checks.len() >= 8, "expected the full check set");
    }
}
