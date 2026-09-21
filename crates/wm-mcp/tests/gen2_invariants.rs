//! Gen2 invariants suite — the acceptance skeleton (9.2.2).
//!
//! One test per invariant from the 2026-09-19 adversarial review's Gen2
//! hardening backlog (§3), asserted through the real server/tool surface
//! rather than a unit seam. The doctrine behind it: software that assumes
//! imperfection, contains it, detects it, recovers from it, and never lies
//! about its state.
//!
//! | Invariant | Where |
//! |---|---|
//! | Canonical-vs-derived separation | [`canonical_content_survives_a_wiped_derived_index`] |
//! | Derived-write failure visibility | [`partial_writes_are_disclosed_not_silent`] + wm-tools `episodic_capture_failure_is_disclosed_on_the_response` |
//! | Tombstone/redaction audit | [`deletion_leaves_a_karma_audit_trail`] |
//! | Restore-does-not-masquerade | `restore_live_store.rs` (`restore_refuses_while_a_server_owns_the_store`); not duplicated here |
//! | Uncertainty-survives-summarization | [`content_supersession_preserves_the_prior_revision`] + wm-tools `supersede_marks_old_turn_and_hides_it_by_default` |

use lmdb::Transaction;
use serde_json::{Value, json};
use tempfile::tempdir;
use wm_mcp::McpServer;

fn runtime() -> tokio::runtime::Runtime {
    tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .expect("tokio runtime")
}

fn server() -> (tempfile::TempDir, McpServer) {
    let tmp = tempdir().expect("tempdir");
    let server = McpServer::with_defaults(tmp.path()).expect("McpServer::with_defaults");
    (tmp, server)
}

fn initialize(rt: &tokio::runtime::Runtime, server: &mut McpServer) {
    let _ = rt.block_on(
        server.handle_request(r#"{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}"#),
    );
}

/// Call a tool through the real JSON-RPC surface and return the inner tool
/// payload. A JSON-RPC error (no `result`) is returned as-is so callers can
/// assert on it instead of panicking.
fn call(rt: &tokio::runtime::Runtime, server: &mut McpServer, name: &str, args: &Value) -> Value {
    let request = json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": args},
    });
    let response = rt.block_on(server.handle_request(&request.to_string()));
    let parsed: Value = serde_json::from_str(&response).expect("JSON-RPC response is JSON");
    let Some(text) = parsed["result"]["content"][0]["text"].as_str() else {
        return parsed;
    };
    serde_json::from_str(text).unwrap_or_else(|e| panic!("tool payload is not JSON: {e}: {text}"))
}

fn create(rt: &tokio::runtime::Runtime, server: &mut McpServer, content: &str) -> String {
    let created = call(
        rt,
        server,
        "memory.create",
        &json!({"content": content, "galaxy": "codex"}),
    );
    assert_eq!(
        created["status"], "success",
        "create must succeed: {created}"
    );
    created["id"]
        .as_str()
        .expect("create returns an id")
        .to_string()
}

/// 1. Canonical records are durable; derived structures are reconstructible
///    views. Wiping the derived side must never damage the canonical read
///    path (and must be visible as degraded, not silently healthy — the
///    grading half lives in `derived_index_doctor.rs`).
#[test]
fn canonical_content_survives_a_wiped_derived_index() {
    let rt = runtime();
    let (_tmp, mut server) = server();
    initialize(&rt, &mut server);
    let id = create(&rt, &mut server, "durable canonical fact");

    // Simulate a failed / never-run sidecar rebuild: clear the derived
    // postings behind the store. The raw episodic lane stays canonical.
    {
        let env = server.store().env();
        let db = env
            .open_db(Some("episodic_terms_v2"))
            .expect("episodic_terms_v2 dbi");
        let mut tx = env.begin_rw_txn().expect("rw txn");
        tx.clear_db(db).expect("clear sidecar");
        tx.commit().expect("commit");
    }

    assert_eq!(
        server.store().episodic_sidecar_health().expect("health"),
        (1, true),
        "records without postings must be visible as degraded"
    );

    // Canonical content is untouched by the derived failure.
    let read = call(&rt, &mut server, "memory.read", &json!({"id": id}));
    assert_eq!(read["status"], "success", "canonical read: {read}");
    assert_eq!(read["content"], "durable canonical fact");
}

/// 2. A write must not report unqualified success when a required
///    representation was skipped: partial outcomes are disclosed per item.
#[test]
fn partial_writes_are_disclosed_not_silent() {
    let rt = runtime();
    let (_tmp, mut server) = server();
    initialize(&rt, &mut server);

    let result = call(
        &rt,
        &mut server,
        "memory.batch_create",
        &json!({"items": [
            {"content": "valid fact one", "galaxy": "codex"},
            {"content": "binary\u{0}payload", "galaxy": "codex"},
            {"content": "valid fact two", "galaxy": "codex"},
        ]}),
    );

    assert_eq!(result["status"], "success", "got: {result}");
    assert_eq!(
        result["skipped_count"], 1,
        "the malformed item must be reported, not silently dropped: {result}"
    );
    assert_eq!(result["skipped"][0]["index"], 1, "got: {result}");
    assert!(
        !result["skipped"][0]["reason"]
            .as_str()
            .unwrap_or("")
            .is_empty(),
        "a skip must carry a reason: {result}"
    );
}

/// 3. Deletion is a redaction: the canonical record is gone and the
///    destructive dispatch is auditable in the karma chain.
#[test]
fn deletion_leaves_a_karma_audit_trail() {
    let rt = runtime();
    let (_tmp, mut server) = server();
    initialize(&rt, &mut server);
    let id = create(&rt, &mut server, "fact scheduled for deletion");

    let deleted = call(
        &rt,
        &mut server,
        "memory.delete",
        &json!({"id": id, "confirm": true}),
    );
    assert_eq!(deleted["status"], "success", "delete: {deleted}");

    let read = call(&rt, &mut server, "memory.read", &json!({"id": id}));
    assert_ne!(
        read["status"], "success",
        "a deleted memory must not read back: {read}"
    );

    let karma = server.karma_ledger().expect("karma ledger is wired");
    let entries = karma.recent(50).expect("karma entries");
    assert!(
        entries
            .iter()
            .any(|e| e.tool == "memory.delete" && e.success),
        "the delete must leave a successful karma entry: {entries:?}"
    );
}

/// 5. Supersession is an amendment, not an erasure: the prior content hash
///    survives in the revision chain and the chain verifies against the head.
#[test]
fn content_supersession_preserves_the_prior_revision() {
    let rt = runtime();
    let (_tmp, mut server) = server();
    initialize(&rt, &mut server);
    let id = create(&rt, &mut server, "first version of the fact");

    let updated = call(
        &rt,
        &mut server,
        "memory.update",
        &json!({"id": id, "content": "second version of the fact"}),
    );
    assert_eq!(updated["status"], "success", "update: {updated}");
    let previous = updated["prev_content_hash"]
        .as_str()
        .expect("content changes disclose the previous hash");
    assert_eq!(
        updated["revision"]["old_hash"], previous,
        "the revision entry must carry the superseded hash: {updated}"
    );

    let listed = call(
        &rt,
        &mut server,
        "memory.revisions",
        &json!({"id": id, "action": "list"}),
    );
    assert_eq!(
        listed["count"], 1,
        "one supersession = one revision: {listed}"
    );
    assert_eq!(listed["revisions"][0]["old_hash"], previous);

    let verified = call(
        &rt,
        &mut server,
        "memory.revisions",
        &json!({"id": id, "action": "verify"}),
    );
    assert_eq!(verified["valid"], true, "chain must verify: {verified}");
}
