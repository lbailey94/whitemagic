//! Cross-implementation acceptance: the Python reference verifies WM bundles,
//! and both implementations compute identical digests for the same receipt.
//!
//! Skipped (not failed) when the CR checkout or `python3` is unavailable, so
//! CI without the sibling repo stays green; the acceptance run records the
//! real verdicts to `receipts/s1_wm_receipts_20260922/`.

use std::process::Command;

use serde_json::{Value, json};
use wm_receipts::emit::{envelope, receipt_digest, sign_receipt};
use wm_receipts::keys::ReceiptKey;
use wm_receipts::profiles::{
    KarmaHeadInput, ModelRef, SessionReceiptInput, TurnEvidence, gate_id_for_store,
    karma_head_bundle, session_bundle,
};
use wm_receipts::verify::verify_bundle;

const CR_REPO_DEFAULT: &str = "/home/lucas/Desktop/continuity-receipt";

fn cr_repo() -> Option<String> {
    let repo = std::env::var("WM_CR_REPO").unwrap_or_else(|_| CR_REPO_DEFAULT.to_string());
    if std::path::Path::new(&repo)
        .join("continuity_receipt")
        .is_dir()
    {
        Some(repo)
    } else {
        None
    }
}

fn python_available() -> bool {
    Command::new("python3")
        .arg("--version")
        .output()
        .is_ok_and(|output| output.status.success())
}

fn key() -> ReceiptKey {
    ReceiptKey::from_seed([7u8; 32])
}

fn session_bundle_fixture() -> Value {
    let digest =
        |text: &str| wm_receipts::emit::digest_of(&json!(text)).expect("digest of test string");
    let turn = |sequence: u64| TurnEvidence {
        memory_id: format!("00000000-0000-7000-8000-{sequence:012}"),
        sequence,
        role: if sequence % 2 == 0 { "user" } else { "ai" }.into(),
        turn_type: "message".into(),
        timestamp_ms: 1_758_500_000_000 + i64::try_from(sequence).expect("sequence fits i64"),
        content_sha256: digest(&format!("turn-{sequence}")),
    };
    session_bundle(
        &key(),
        &SessionReceiptInput {
            session_id: "11111111-1111-7111-8111-111111111111".into(),
            user: "default".into(),
            session_start_id: "22222222-2222-7222-8222-222222222222".into(),
            session_start_created_at: "2026-09-22T09:00:00Z".into(),
            store_gate_id: gate_id_for_store("/tmp/wm-s1-acceptance/store").expect("gate"),
            issued_at: "2026-09-22T10:00:00Z".into(),
            expires_at: "2026-09-23T10:00:00Z".into(),
            from_sequence: 1,
            to_sequence: 2,
            duration_ms: 3_600_000,
            turns: vec![turn(1), turn(2)],
            model: ModelRef::wm_local("session-chronicle"),
        },
    )
    .expect("session bundle")
}

#[test]
fn python_reference_verifies_wm_session_bundle_trusted() {
    let (Some(repo), true) = (cr_repo(), python_available()) else {
        eprintln!("skipping: python3 or WM_CR_REPO checkout unavailable");
        return;
    };
    let bundle = session_bundle_fixture();
    let rust = verify_bundle(&bundle, false);
    assert!(rust.is_trusted(), "rust verdict: {rust:?}");

    let dir = tempfile::tempdir().expect("tempdir");
    let path = dir.path().join("session-bundle.json");
    std::fs::write(
        &path,
        serde_json::to_vec_pretty(&bundle).expect("serialize"),
    )
    .expect("write bundle");

    let output = Command::new("python3")
        .env("PYTHONPATH", &repo)
        .args(["-m", "continuity_receipt.verify"])
        .arg(&path)
        .output()
        .expect("run python verifier");
    assert!(
        output.status.success(),
        "python verifier failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let verdict: Value = serde_json::from_slice(&output.stdout).expect("verdict json");
    assert_eq!(verdict["verdict"], "TRUSTED", "python verdict: {verdict}");
    assert_eq!(
        rust.verdict,
        verdict["verdict"].as_str().expect("verdict str")
    );
}

#[test]
fn python_reference_verifies_wm_karma_head_bundle_trusted() {
    let (Some(repo), true) = (cr_repo(), python_available()) else {
        eprintln!("skipping: python3 or WM_CR_REPO checkout unavailable");
        return;
    };
    let bundle = karma_head_bundle(
        &key(),
        &KarmaHeadInput {
            entry_count: 42,
            chain_head: "ab".repeat(32),
            merkle_root: Some("cd".repeat(32)),
            scans_digest: wm_receipts::emit::digest_of(&json!(["entry-1", "entry-2"]))
                .expect("digest"),
            integrity_ok: true,
            store_gate_id: gate_id_for_store("/tmp/wm-s1-acceptance/store").expect("gate"),
            issued_at: "2026-09-22T10:00:00Z".into(),
            expires_at: "2026-09-23T10:00:00Z".into(),
            model: ModelRef::wm_local("karma-ledger"),
        },
    )
    .expect("karma bundle");
    assert!(verify_bundle(&bundle, false).is_trusted());

    let dir = tempfile::tempdir().expect("tempdir");
    let path = dir.path().join("karma-bundle.json");
    std::fs::write(
        &path,
        serde_json::to_vec_pretty(&bundle).expect("serialize"),
    )
    .expect("write bundle");
    let output = Command::new("python3")
        .env("PYTHONPATH", &repo)
        .args(["-m", "continuity_receipt.verify"])
        .arg(&path)
        .output()
        .expect("run python verifier");
    assert!(
        output.status.success(),
        "python verifier failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let verdict: Value = serde_json::from_slice(&output.stdout).expect("verdict json");
    assert_eq!(verdict["verdict"], "TRUSTED", "python verdict: {verdict}");
}

#[test]
fn python_reference_digest_matches_rust_digest() {
    let (Some(repo), true) = (cr_repo(), python_available()) else {
        eprintln!("skipping: python3 or WM_CR_REPO checkout unavailable");
        return;
    };
    let unsigned = envelope(
        "urn:uuid:33333333-3333-7333-8333-333333333333",
        "urn:uuid:44444444-4444-7444-8444-444444444444",
        "2026-09-22T10:00:00Z",
        "agent",
        key().did(),
        "task.termination",
        0,
        None,
        &json!({
            "reason": "completed",
            "limits_at_stop": { "cpu_ms": 0, "wall_ms": 0, "spend_minor": 0, "currency": "USD" },
            "remaining": {},
        }),
    );
    let receipt = sign_receipt(&unsigned, &key()).expect("sign");
    let rust_digest = receipt_digest(&receipt).expect("digest");

    let dir = tempfile::tempdir().expect("tempdir");
    let path = dir.path().join("receipt.json");
    std::fs::write(&path, serde_json::to_vec(&receipt).expect("serialize")).expect("write");

    let script = format!(
        "import json,sys; sys.path.insert(0, {repo:?}); \
         from continuity_receipt.bundle import receipt_digest; \
         print(receipt_digest(json.load(open({path:?}))))",
        repo = repo,
        path = path.to_string_lossy().to_string(),
    );
    let output = Command::new("python3")
        .args(["-c", &script])
        .output()
        .expect("run python digest");
    assert!(
        output.status.success(),
        "python digest failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let python_digest = String::from_utf8_lossy(&output.stdout).trim().to_string();
    assert_eq!(rust_digest, python_digest, "canonical digest divergence");
}
