//! Profile-precedence E2E — the `wm serve` binary must resolve the tool
//! surface exactly as documented in AGENTS.md: explicit `--profile` flag
//! wins over `WM_TOOL_PROFILE`, which wins over the curated default taken
//! when both are absent. This is the spawned-process proof (the in-process
//! `e2e_curated_profile_filters_tool_surface` test cannot catch a CLI
//! regression like `--profile` defaulting to `full` and clobbering the
//! environment — that defect shipped in 5.7.7 and only reproduced when the
//! binary was launched as a subprocess).
//!
//! The disclosed surface is checked two ways per spawn: the `tools/list`
//! description (which names the active profile) and the `tools.list`
//! route (which enumerates the routable surface itself).

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
    /// Spawn `wm serve` on a throwaway store. `profile_flag` maps to the
    /// `--profile` argument; `env_profile` to `WM_TOOL_PROFILE` (removed
    /// from the environment when `None`, so the host shell cannot leak a
    /// value into the default-profile case).
    fn spawn(
        store_root: &std::path::Path,
        profile_flag: Option<&str>,
        env_profile: Option<&str>,
    ) -> Self {
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_wm"));
        cmd.args([
            "serve",
            "--store",
            &store_root.display().to_string(),
            "--transport",
            "stdio",
            "--rate-limit",
            "0",
        ]);
        if let Some(p) = profile_flag {
            cmd.args(["--profile", p]);
        }
        if let Some(p) = env_profile {
            cmd.env("WM_TOOL_PROFILE", p);
        } else {
            cmd.env_remove("WM_TOOL_PROFILE");
        }
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

    fn initialize(&mut self, id: u64) {
        let init = self.rpc(
            "initialize",
            &serde_json::json!({
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "profile-e2e", "version": "1.0"},
            }),
            id,
        );
        assert_eq!(
            init["result"]["serverInfo"]["name"], "whitemagic",
            "initialize handshake failed: {init}"
        );
    }

    /// The `tools/list` description for the single `wm` tool.
    fn disclosed_description(&mut self, id: u64) -> String {
        let resp = self.rpc("tools/list", &serde_json::json!({}), id);
        let tools = resp["result"]["tools"]
            .as_array()
            .unwrap_or_else(|| panic!("tools/list returned no tools array: {resp}"));
        assert_eq!(
            tools.len(),
            1,
            "serve must expose exactly the wm tool: {resp}"
        );
        assert_eq!(
            tools[0]["name"], "wm",
            "the single exposed tool must be wm: {resp}"
        );
        tools[0]["description"]
            .as_str()
            .unwrap_or_else(|| panic!("wm tool description missing: {resp}"))
            .to_string()
    }

    /// Call `wm(route="tools.list")` and return the routable tool names.
    fn disclosed_surface(&mut self, id: u64) -> Vec<String> {
        let resp = self.rpc(
            "tools/call",
            &serde_json::json!({
                "name": "wm",
                "arguments": {"route": "tools.list", "args": {}}
            }),
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
                || panic!("tools/call tools.list returned no content: {resp}"),
                String::from,
            );
        let parsed: serde_json::Value = serde_json::from_str(&content)
            .unwrap_or_else(|e| panic!("tools.list content is not JSON ({e}): {content}"));
        parsed["tools"]
            .as_array()
            .unwrap_or_else(|| panic!("tools.list has no tools array: {parsed}"))
            .iter()
            .filter_map(|t| t["name"].as_str().map(String::from))
            .collect()
    }
}

impl Drop for ServeProcess {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

/// The single test exercises all three precedence tiers; each tier spawns a
/// fresh process so the resolution logic runs from scratch every time.
#[test]
fn serve_profile_precedence_flag_over_env_over_default() {
    // 1. DEFAULT: no flag, no env → curated (the product surface).
    let store = tempfile::tempdir().expect("default store");
    let mut s = ServeProcess::spawn(store.path(), None, None);
    s.initialize(0);
    let desc = s.disclosed_description(1);
    assert!(
        desc.contains("curated tool surface"),
        "omitted --profile with no env must default to curated, disclosed: {desc}"
    );
    let surface = s.disclosed_surface(2);
    assert!(
        surface.iter().any(|n| n == "memory.create"),
        "curated surface must include memory.create: {surface:?}"
    );
    assert!(
        surface.iter().any(|n| n.starts_with("session.")),
        "curated surface must include the session hierarchy: {surface:?}"
    );
    assert!(
        !surface.iter().any(|n| n.starts_with("galaxy.")),
        "curated surface must exclude galaxy management tools: {surface:?}"
    );
    drop(s);

    // 2. ENV ONLY: WM_TOOL_PROFILE=minimal, no flag → minimal.
    let store = tempfile::tempdir().expect("env store");
    let mut s = ServeProcess::spawn(store.path(), None, Some("minimal"));
    s.initialize(0);
    let desc = s.disclosed_description(1);
    assert!(
        desc.contains("minimal tool surface"),
        "WM_TOOL_PROFILE must be honored when the flag is omitted, disclosed: {desc}"
    );
    let surface = s.disclosed_surface(2);
    assert!(
        surface.iter().any(|n| n == "memory.create"),
        "minimal surface must include memory.create: {surface:?}"
    );
    assert!(
        !surface.iter().any(|n| n == "memory.delete"),
        "minimal surface must exclude memory.delete: {surface:?}"
    );
    drop(s);

    // 3. FLAG WINS: --profile full + WM_TOOL_PROFILE=minimal → full.
    let store = tempfile::tempdir().expect("flag store");
    let mut s = ServeProcess::spawn(store.path(), Some("full"), Some("minimal"));
    s.initialize(0);
    let desc = s.disclosed_description(1);
    assert!(
        desc.contains("full tool surface"),
        "explicit --profile must win over WM_TOOL_PROFILE, disclosed: {desc}"
    );
    let surface = s.disclosed_surface(2);
    assert!(
        surface.iter().any(|n| n == "memory.delete"),
        "full surface must include memory.delete (flag beats env=minimal): {surface:?}"
    );
}
