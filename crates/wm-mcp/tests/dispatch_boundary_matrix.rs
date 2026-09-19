//! Q08 dispatch-boundary matrix — drift checks and the alias-boundary fixture.
//!
//! The matrix artifact is `docs/contract/boundary-matrix.md`. These checks
//! rebuild the registry in-process and prove (a) the destructive set and
//! `SCOPE_REGISTRY` cannot drift apart, (b) the committed matrix block still
//! matches the registry, and (c) the cross-boundary equivalence class for a
//! destructive route at the MCP alias boundary — same route, same effect
//! row, same refusal — which the pipeline and NLU sweeps cover at their own
//! boundaries ([`wm_dispatch`] unit tests,
//! `nlu_cannot_reach_any_destructive_tool`).

use std::path::Path;
use wm_mcp::McpServer;
use wm_mcp::boundary_matrix::{META_ROUTES, RouteClass, boundary_cells, classify, render_block};

const BEGIN: &str = "<!-- BEGIN GENERATED: q08-route-matrix -->";
const END: &str = "<!-- END GENERATED: q08-route-matrix -->";

fn registry_for_test() -> (tempfile::TempDir, McpServer) {
    let tmp = tempfile::tempdir().expect("tempdir");
    let server = McpServer::with_defaults(tmp.path()).expect("McpServer::with_defaults");
    (tmp, server)
}

#[test]
fn destructive_set_and_scope_registry_agree_both_ways() {
    let (_tmp, server) = registry_for_test();
    let registered: Vec<String> = server
        .registry()
        .all_ref()
        .iter()
        .filter(|tool| tool.effects().destructive)
        .map(|tool| tool.name().to_string())
        .collect();
    assert!(
        registered.len() >= 11,
        "destructive set shrank unexpectedly: {registered:?}"
    );

    let mut missing: Vec<&String> = registered
        .iter()
        .filter(|name| {
            !wm_governance::firebreak::SCOPE_REGISTRY
                .iter()
                .any(|(route, _)| *route == name.as_str())
        })
        .collect();
    missing.sort();
    assert!(
        missing.is_empty(),
        "destructive routes missing from SCOPE_REGISTRY (firebreak fails open): {missing:?}"
    );

    for (route, _) in wm_governance::firebreak::SCOPE_REGISTRY {
        let tool = server.registry().get(route).unwrap_or_else(|| {
            panic!("SCOPE_REGISTRY names {route}, which is not a registered route")
        });
        assert!(
            tool.effects().destructive,
            "SCOPE_REGISTRY names {route}, which is not declared destructive"
        );
    }
}

#[test]
fn boundary_cells_pin_the_expected_verdicts() {
    assert_eq!(
        boundary_cells("memory.delete", RouteClass::Destructive),
        ["C", "C", "R", "N", "PC", "—"]
    );
    assert_eq!(
        boundary_cells("memory.search", RouteClass::Read),
        ["A", "A", "A", "N", "F", "—"]
    );
    assert_eq!(
        boundary_cells("memory.create", RouteClass::Write),
        ["A", "A", "A", "N", "P", "—"]
    );
    assert_eq!(
        boundary_cells("wm", RouteClass::Meta),
        ["A", "A", "—", "N", "P", "—"]
    );
}

#[test]
fn registry_classification_and_meta_set_hold() {
    let (_tmp, server) = registry_for_test();
    let tools = server.registry().all_ref();
    assert!(
        tools.len() >= 290,
        "full registry unexpectedly small ({}); profile leak into the test process?",
        tools.len()
    );
    for meta in META_ROUTES {
        assert!(
            tools.iter().any(|tool| tool.name() == *meta),
            "meta route {meta} missing from the registry"
        );
        let tool = tools.iter().find(|tool| tool.name() == *meta).unwrap();
        assert_eq!(classify(tool.as_ref()), RouteClass::Meta);
    }
    let mut classed = 0usize;
    for tool in tools {
        match classify(tool.as_ref()) {
            RouteClass::Meta
            | RouteClass::Destructive
            | RouteClass::Spawn
            | RouteClass::Coordination
            | RouteClass::Write
            | RouteClass::Read => classed += 1,
        }
    }
    assert_eq!(classed, tools.len());
}

#[test]
fn matrix_block_matches_committed_artifact() {
    let (_tmp, server) = registry_for_test();
    let generated = render_block(server.registry());
    let doc_path =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../docs/contract/boundary-matrix.md");
    let doc = std::fs::read_to_string(&doc_path)
        .unwrap_or_else(|e| panic!("read {}: {e}", doc_path.display()));
    let committed = extract_between(&doc, BEGIN, END);
    if std::env::var("WM_UPDATE_Q08_MATRIX").ok().as_deref() == Some("1") {
        let updated = replace_between(&doc, BEGIN, END, &generated);
        std::fs::write(&doc_path, updated).expect("write matrix artifact");
        return;
    }
    assert_eq!(
        committed.trim(),
        generated.trim(),
        "docs/contract/boundary-matrix.md is stale versus the registry; \
         regenerate with WM_UPDATE_Q08_MATRIX=1 cargo test -p whitemagic \
         --test dispatch_boundary_matrix matrix_block_matches_committed_artifact"
    );
}

fn extract_between<'a>(text: &'a str, begin: &str, end: &str) -> &'a str {
    let start = text
        .find(begin)
        .unwrap_or_else(|| panic!("missing marker {begin}"))
        + begin.len();
    let rest = &text[start..];
    let stop = rest
        .find(end)
        .unwrap_or_else(|| panic!("missing marker {end}"));
    &rest[..stop]
}

fn replace_between(text: &str, begin: &str, end: &str, replacement: &str) -> String {
    let start = text.find(begin).expect("begin marker") + begin.len();
    let stop = text[start..].find(end).expect("end marker") + start;
    format!("{}\n{}{}", &text[..start], replacement, &text[stop..])
}

#[cfg(not(windows))]
mod alias_boundary {
    use std::io::{BufRead, BufReader, Write};
    use std::process::{Child, Command, Stdio};
    use std::sync::mpsc::{Receiver, channel};
    use std::time::Duration;

    use serde_json::{Value, json};

    struct Serve {
        child: Child,
        stdin: std::process::ChildStdin,
        responses: Receiver<String>,
    }

    impl Serve {
        fn spawn(store_root: &std::path::Path) -> Self {
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
            cmd.env("WM_HOMEOSTASIS_FROZEN", "1");
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

        fn rpc(&mut self, method: &str, params: &Value, id: u64) -> Value {
            let request = json!({
                "jsonrpc": "2.0",
                "id": id,
                "method": method,
                "params": params,
            });
            writeln!(self.stdin, "{request}").expect("write request");
            self.stdin.flush().expect("flush request");
            let line = self
                .responses
                .recv_timeout(Duration::from_secs(30))
                .unwrap_or_else(|_| panic!("{method} (id {id}) got no response within 30s"));
            serde_json::from_str(&line)
                .unwrap_or_else(|e| panic!("{method} returned invalid JSON ({e}): {line}"))
        }

        fn call(&mut self, name: &str, arguments: &Value, id: u64) -> Value {
            self.rpc(
                "tools/call",
                &json!({"name": name, "arguments": arguments}),
                id,
            )
        }
    }

    impl Drop for Serve {
        fn drop(&mut self) {
            let _ = self.child.kill();
            let _ = self.child.wait();
        }
    }

    fn content_json(response: &Value) -> Value {
        let text = response["result"]["content"][0]["text"]
            .as_str()
            .unwrap_or_else(|| panic!("no content text in response: {response}"));
        serde_json::from_str(text).unwrap_or_else(|e| panic!("content is not JSON ({e}): {text}"))
    }

    #[test]
    fn destructive_alias_requires_confirm_and_preserves_the_record() {
        let store = tempfile::tempdir().expect("store");
        let mut serve = Serve::spawn(store.path());
        let init = serve.rpc(
            "initialize",
            &json!({
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "q08-boundary", "version": "1.0"},
            }),
            0,
        );
        assert_eq!(init["result"]["serverInfo"]["name"], "whitemagic");

        let created = content_json(&serve.call(
            "memory.create",
            &json!({"content": "q08 alias-boundary probe (safe to delete)", "galaxy": "codex"}),
            1,
        ));
        let id = created["id"].as_str().expect("created id").to_string();

        let refused = serve.call("memory.delete", &json!({"id": id}), 2);
        let message = refused["error"]["message"]
            .as_str()
            .unwrap_or_else(|| panic!("alias delete without confirm must refuse: {refused}"));
        assert!(
            message.contains("destructive"),
            "refusal must name the confirm gate: {message}"
        );

        let survived = content_json(&serve.call("memory.read", &json!({"id": id}), 3));
        assert_ne!(
            survived["status"], "not_found",
            "a refused delete must not touch the record: {survived}"
        );

        let deleted = serve.call("memory.delete", &json!({"id": id, "confirm": true}), 4);
        assert!(
            deleted.get("error").is_none(),
            "confirmed delete must be admitted: {deleted}"
        );

        let gone = content_json(&serve.call("memory.read", &json!({"id": id}), 5));
        assert_eq!(
            gone["status"], "not_found",
            "confirmed delete must remove the record"
        );
    }
}
