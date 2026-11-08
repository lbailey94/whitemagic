//! Acceptance test battery Gate PEB-18: Experiential & Relational Identity Stack.
//! Verifies distilled lessons, correction ledger, identity invariants, and longitudinal relational context
//! across CLI invocations, Substrate queries, and MCP bridge handling.

use std::process::Command;
use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::ops::{SessionCheckpoint, Substrate};
use wm_gen3_harness::bridge::{McpProfile, execute_hybrid_tool_call};

fn temp_store_path(tag: &str) -> std::path::PathBuf {
    std::env::temp_dir().join(format!("wm-test-identity-{}-{}", tag, uuid::Uuid::new_v4()))
}

#[test]
fn peb18_1_identity_stack_cli_checkpoint_and_continuity_roundtrip() {
    let store = temp_store_path("cli-roundtrip");
    let store_str = store.to_str().expect("utf8 path");

    // 1. Commit Checkpoint via CLI with all 4 identity fields
    let status = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store_str,
            "session",
            "checkpoint",
            "--session-id",
            "sess-identity-01",
            "--agent-id",
            "antigravity",
            "--summary",
            "Implemented dual-clock decay and spreading activation.",
            "--next-queue",
            "Verify Phase 4 MCP adapter",
            "--open-flags",
            "zero_drift",
            "--lesson",
            "Lived-time decay clock preserves SNR over sleep quiescence.",
            "--lesson",
            "Hebbian spreading activation enables lateral recall in under 5ms.",
            "--correction",
            "Keep per-turn test writes strictly under the 120 writes/min rate limit.",
            "--identity-invariant",
            "Deterministic Linux Landlock confinement, NOT Corrigibility dogma.",
            "--relational-context",
            "Lucas (operator) paired on Gen3 10/10 upgrade roadmap.",
            "--no-evolve",
        ])
        .output()
        .expect("run wm session checkpoint");

    assert!(
        status.status.success(),
        "checkpoint CLI failed: {}",
        String::from_utf8_lossy(&status.stderr)
    );
    let stdout = String::from_utf8_lossy(&status.stdout);
    assert!(stdout.contains("Session checkpoint committed successfully."));
    assert!(stdout.contains("Identity Invariants:"));
    assert!(stdout.contains("Deterministic Linux Landlock confinement, NOT Corrigibility dogma."));
    assert!(stdout.contains("Distilled Lessons:"));
    assert!(stdout.contains("Lived-time decay clock preserves SNR over sleep quiescence."));
    assert!(stdout.contains("Corrections Ledger:"));
    assert!(stdout.contains("Keep per-turn test writes strictly under the 120 writes/min rate limit."));
    assert!(stdout.contains("Relational:      Lucas (operator) paired on Gen3 10/10 upgrade roadmap."));

    // 2. Query Session Continuity via CLI
    let cont_output = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store_str,
            "session",
            "continuity",
            "--session-id",
            "sess-identity-01",
        ])
        .output()
        .expect("run wm session continuity");

    assert!(
        cont_output.status.success(),
        "continuity CLI failed: {}",
        String::from_utf8_lossy(&cont_output.stderr)
    );
    let cont_stdout = String::from_utf8_lossy(&cont_output.stdout);
    assert!(cont_stdout.contains("WhiteMagic Session Continuity"));
    assert!(cont_stdout.contains("Identity Invariants:"));
    assert!(cont_stdout.contains("🛡️  Deterministic Linux Landlock confinement, NOT Corrigibility dogma."));
    assert!(cont_stdout.contains("Distilled Lessons:"));
    assert!(cont_stdout.contains("💡 Lived-time decay clock preserves SNR over sleep quiescence."));
    assert!(cont_stdout.contains("💡 Hebbian spreading activation enables lateral recall in under 5ms."));
    assert!(cont_stdout.contains("Corrections Ledger:"));
    assert!(cont_stdout.contains("🔧 Keep per-turn test writes strictly under the 120 writes/min rate limit."));
    assert!(cont_stdout.contains("Relational:      Lucas (operator) paired on Gen3 10/10 upgrade roadmap."));

    let _ = std::fs::remove_dir_all(&store);
}

#[test]
fn peb18_2_substrate_session_continuity_identity_fidelity() {
    let store = temp_store_path("substrate-fidelity");
    let mut substrate = Substrate::open(&store, None, default_view()).unwrap();
    substrate.set_intake_authority(RatifiedChannel::mint("test-auth"));

    let cp = SessionCheckpoint {
        session_id: "agent-collab-lane".into(),
        agent_id: "luna".into(),
        checkpoint_type: "milestone".into(),
        summary: "Verified invariant preservation across agent handoffs.".into(),
        next_queue: vec!["Trigger universal MCP test".into()],
        open_flags: vec!["clean_provenance".into()],
        context_token: Some("ctx_hash_alpha_99".into()),
        representation: None,
        timestamp_iso: Some("2026-11-08T00:00:00Z".into()),
        lessons: vec![
            "Episodic memory decay leaves actionable wisdom intact.".into(),
        ],
        corrections: vec![
            "Never bypass SCITT cryptographic provenance receipts.".into(),
        ],
        identity_invariants: vec![
            "Homeostatic Ashby stability over arbitrary optimization goals.".into(),
        ],
        relational_context: Some("Opencode, Sol, and Antigravity operating as unified Sangha.".into()),
    };

    let id = substrate.session_checkpoint(&cp).unwrap();
    assert_eq!(id, 0);

    let view = substrate
        .session_continuity(Some("agent-collab-lane"))
        .unwrap()
        .expect("continuity present");

    assert_eq!(view.summary, cp.summary);
    assert_eq!(view.lessons, cp.lessons);
    assert_eq!(view.corrections, cp.corrections);
    assert_eq!(view.identity_invariants, cp.identity_invariants);
    assert_eq!(view.relational_context, cp.relational_context);

    let _ = std::fs::remove_dir_all(&store);
}

#[test]
fn peb18_3_mcp_bridge_checkpoint_dispatch() {
    let store = temp_store_path("mcp-bridge");
    let mut substrate = Substrate::open(&store, None, default_view()).unwrap();
    substrate.set_intake_authority(RatifiedChannel::mint("bridge-auth"));

    let raw_req = serde_json::json!({
        "session_id": "sess-mcp-foreign-agent",
        "agent_id": "cursor-ide",
        "checkpoint_type": "handoff",
        "summary": "Completed foreign agent feature pass.",
        "next_queue": ["Codex follow-up verification"],
        "open_flags": ["verified"],
        "lessons": ["MCP bridge facilitates zero-friction cross-tool handoffs."],
        "corrections": ["Use standard json parameter naming."],
        "identity_invariants": ["Zero Corrigibility/Rationalist grant framing."],
        "relational_context": "Cooperating with operator Lucas."
    });

    let res = execute_hybrid_tool_call(
        "session.checkpoint",
        &raw_req,
        &mut substrate,
        &store,
        false,
        McpProfile::Cyberbrain,
    ).expect("execute hybrid tool call");

    assert_eq!(res["status"], "success");
    assert_eq!(res["checkpoint_record_id"], 0);
    assert_eq!(res["session_id"], "sess-mcp-foreign-agent");

    // Verify continuity view returned by substrate reflects the MCP call
    let cont = substrate.session_continuity(Some("sess-mcp-foreign-agent")).unwrap().unwrap();
    assert_eq!(cont.agent_id, "cursor-ide");
    assert_eq!(cont.lessons, vec!["MCP bridge facilitates zero-friction cross-tool handoffs."]);
    assert_eq!(cont.corrections, vec!["Use standard json parameter naming."]);
    assert_eq!(cont.identity_invariants, vec!["Zero Corrigibility/Rationalist grant framing."]);
    assert_eq!(cont.relational_context.as_deref(), Some("Cooperating with operator Lucas."));

    let _ = std::fs::remove_dir_all(&store);
}

#[test]
fn peb18_4_backward_compatibility_with_legacy_json() {
    let legacy_json = r#"{
        "session_id": "legacy-session-v1",
        "agent_id": "historical-agent",
        "checkpoint_type": "turn",
        "summary": "Pre-v11 legacy checkpoint without identity stack",
        "next_queue": ["migrate"],
        "open_flags": []
    }"#;

    let cp: SessionCheckpoint = serde_json::from_str(legacy_json).expect("deserialize legacy json");
    assert_eq!(cp.session_id, "legacy-session-v1");
    assert_eq!(cp.summary, "Pre-v11 legacy checkpoint without identity stack");
    assert!(cp.lessons.is_empty(), "lessons should default to empty");
    assert!(cp.corrections.is_empty(), "corrections should default to empty");
    assert!(cp.identity_invariants.is_empty(), "identity_invariants should default to empty");
    assert_eq!(cp.relational_context, None, "relational_context should default to None");
}
