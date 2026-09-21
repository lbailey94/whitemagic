//! Emergent Expressibility & The Recipe Challenge Benchmark (G3-CRB-1 Phase 6).
//!
//! Protocol: docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md §3 Layer 6, §5 Phase 6
//! Baseline: Gen3 Cognitive Runtime Baseline 1 (G3-CRB-1)
//!
//! Tests the 4 Autonomous Workflows using ONLY existing G3-CRB-1 primitives:
//! 1. Workflow A (Multi-Step Defect Diagnosis & Patch Verification)
//! 2. Workflow B (Distributed Multi-Agent Handoff via Leases & Continuity)
//! 3. Workflow C (Epistemic Hypothesis Registration & Empirical Validation)
//! 4. Workflow D (The Intentionally Awful Workflow: Spec Change + Crash + Expiry + Falsification + Recovery)
//!
//! Asserts that the Minimal Cognitive Runtime possesses full operational expressibility
//! without requiring additional engine-level orchestration bloat (W2_05 Recipe Layer).

use serde_json::json;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::time::sleep;
use wm_core::{Context, Tool};
use wm_memory::MemoryStore;
use wm_simulation::ClaimsLedger;
use wm_tools::expansion::{
    ClaimsTool, CodeCheckTool, CodeClaimTool, CodeReleaseTool, SessionCheckpointNodiscoveryTool,
    SessionContinuityTool, SessionRecordTool, SessionReplayTool, SessionStartTool,
};

fn fake_git_repo() -> (tempfile::TempDir, PathBuf) {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().to_path_buf();
    fs::create_dir_all(root.join(".git/objects")).unwrap();
    fs::write(root.join(".git/HEAD"), "ref: refs/heads/main\n").unwrap();
    (dir, root)
}

fn test_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("lmdb");
    fs::create_dir_all(&path).unwrap();
    (dir, Arc::new(MemoryStore::open_default(path).unwrap()))
}

fn root_str(root: &Path) -> serde_json::Value {
    json!(root.display().to_string())
}

#[tokio::test]
async fn test_workflow_a_defect_diagnosis_and_verification() {
    let (_dir_repo, root) = fake_git_repo();
    let (_dir_store, store) = test_store();
    let claims_ledger = Arc::new(Mutex::new(ClaimsLedger::new()));

    let start_tool = SessionStartTool::new(store.clone());
    let record_tool = SessionRecordTool::new(store.clone());
    let checkpoint_tool = SessionCheckpointNodiscoveryTool::new(store.clone());
    let claim_tool = CodeClaimTool::new(None);
    let release_tool = CodeReleaseTool::new(None);
    let claims_tool = ClaimsTool::new(claims_ledger.clone());
    let mut ctx = Context::default();

    // Step A1: Start session. session.start mints the id; a caller-supplied
    // session_id is not honored, and session.record now refuses ids that do
    // not name an existing session_start (2026-09-21 orphan-turn guard).
    let start_res = start_tool.call(&mut ctx, json!({})).await.unwrap();
    assert_eq!(start_res["status"], "success");
    let diag_session_id = start_res["session_id"].as_str().unwrap().to_string();

    // Step A2: Register falsifiable defect hypothesis
    let claim_res = claims_tool
        .call(
            &mut ctx,
            json!({
                "action": "add",
                "statement": "Queue race condition resolved by atomic flag in worker dispatch",
                "domain": "defect_diagnosis",
                "source_date": "2026-09-18",
                "predicted_outcome": "Passes all 50 concurrent dispatch tests",
                "confidence": 0.85,
                "falsification_criteria": "Any deadlocks or lost tasks detected during verification",
            }),
        )
        .await
        .unwrap();
    assert_eq!(claim_res["status"], "success");
    let claim_id = claim_res["claim_id"].as_str().unwrap();

    // Step A3: Record defect reproduction turn
    let turn1 = record_tool
        .call(
            &mut ctx,
            json!({
                "session_id": diag_session_id,
                "role": "ai",
                "content": "Reproduction: 50 concurrent dispatchers deadlock on mutex acquisition in worker loop",
            }),
        )
        .await
        .unwrap();
    assert_eq!(turn1["status"], "success");

    // Step A4: Claim lease on target file
    let lease_res = claim_tool
        .call(
            &mut ctx,
            json!({
                "scope": "crates/core/queue.rs",
                "intent": "replace mutex with atomic CAS loop",
                "owner_session": diag_session_id,
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(lease_res["status"], "success");

    // Step A5: Record patch synthesis turn
    let turn2 = record_tool
        .call(
            &mut ctx,
            json!({
                "session_id": diag_session_id,
                "role": "ai",
                "content": "Patch applied: AtomicBool state flag replaces Mutex guard in try_dispatch",
            }),
        )
        .await
        .unwrap();
    assert_eq!(turn2["status"], "success");

    // Step A6: Test verification passes -> Resolve claim as validated
    let resolve_res = claims_tool
        .call(
            &mut ctx,
            json!({
                "action": "resolve",
                "claim_id": claim_id,
                "validated": true,
                "event": "50/50 concurrent dispatch iterations passed with zero deadlocks",
                "event_date": "2026-09-18",
                "source": "receipt://test-runner/queue_stress",
            }),
        )
        .await
        .unwrap();
    assert_eq!(resolve_res["status"], "success");
    assert_eq!(resolve_res["claim_status"], "validated");

    // Step A7: Checkpoint nodiscovery with continuity receipt
    let ckpt_res = checkpoint_tool
        .call(
            &mut ctx,
            json!({
                "session_id": diag_session_id,
                "project": root_str(&root),
                "continuity_receipt": {
                    "task": "queue deadlock resolution",
                    "status": "completed",
                    "modified_files": ["crates/core/queue.rs"],
                    "verified": true,
                }
            }),
        )
        .await
        .unwrap();
    assert_eq!(ckpt_res["status"], "success");

    // Step A8: Release lease
    let rel_res = release_tool
        .call(
            &mut ctx,
            json!({
                "scope": "crates/core/queue.rs",
                "owner_session": diag_session_id,
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(rel_res["status"], "success");
    assert_eq!(rel_res["state"], "released");
}

#[tokio::test]
async fn test_workflow_b_multi_agent_distributed_handoff() {
    let (_dir_repo, root) = fake_git_repo();
    let (_dir_store, store) = test_store();

    let start_tool = SessionStartTool::new(store.clone());
    let record_tool = SessionRecordTool::new(store.clone());
    let checkpoint_tool = SessionCheckpointNodiscoveryTool::new(store.clone());
    let continuity_tool = SessionContinuityTool::new(store.clone());
    let replay_tool = SessionReplayTool::new(store.clone());
    let claim_tool = CodeClaimTool::new(None);
    let release_tool = CodeReleaseTool::new(None);
    let mut ctx = Context::default();

    // === WORKER ALPHA ===
    let alpha_start = start_tool.call(&mut ctx, json!({})).await.unwrap();
    let alpha_session_id = alpha_start["session_id"].as_str().unwrap().to_string();

    let claim_alpha = claim_tool
        .call(
            &mut ctx,
            json!({
                "scope": "crates/pipeline/mod.rs",
                "intent": "implement ingestion pipeline stage",
                "owner_session": alpha_session_id,
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(claim_alpha["status"], "success");

    record_tool
        .call(
            &mut ctx,
            json!({
                "session_id": alpha_session_id,
                "role": "ai",
                "content": "Stage 1 (Ingest) implemented. Requires Stage 2 (Transform) from successor.",
            }),
        )
        .await
        .unwrap();

    checkpoint_tool
        .call(
            &mut ctx,
            json!({
                "session_id": alpha_session_id,
                "project": root_str(&root),
                "next_queue": ["transform: crates/pipeline/mod.rs"],
                "open_flags": ["stage_1:done"],
                "tests_green": true,
                "lease_id": "crates/pipeline/mod.rs",
            }),
        )
        .await
        .unwrap();

    release_tool
        .call(
            &mut ctx,
            json!({
                "scope": "crates/pipeline/mod.rs",
                "owner_session": alpha_session_id,
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();

    // === WORKER BETA (Autonomous Successor) ===
    let beta_start = start_tool.call(&mut ctx, json!({})).await.unwrap();
    let beta_session_id = beta_start["session_id"].as_str().unwrap().to_string();

    // Discover prior work via project-root continuity
    let cont_res = continuity_tool
        .call(
            &mut ctx,
            json!({
                "session_id": beta_session_id,
                "project": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(cont_res["status"], "success");
    assert_eq!(cont_res["previous_session"], alpha_session_id);
    let handoff = &cont_res["checkpoint"];
    assert_eq!(
        handoff["next_queue"][0],
        "transform: crates/pipeline/mod.rs"
    );
    assert_eq!(handoff["open_flags"][0], "stage_1:done");
    assert_eq!(handoff["tests_green"], true);

    // Replay Alpha's turns
    let replay_res = replay_tool
        .call(&mut ctx, json!({ "session_id": alpha_session_id }))
        .await
        .unwrap();
    assert_eq!(replay_res["count"], 1);

    // Acquire lease and complete stage 2
    let claim_beta = claim_tool
        .call(
            &mut ctx,
            json!({
                "scope": "crates/pipeline/mod.rs",
                "intent": "implement transform pipeline stage per handoff receipt",
                "owner_session": beta_session_id,
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(claim_beta["status"], "success");

    record_tool
        .call(
            &mut ctx,
            json!({
                "session_id": beta_session_id,
                "role": "ai",
                "content": "Stage 2 (Transform) completed cleanly based on Stage 1 input.",
            }),
        )
        .await
        .unwrap();

    release_tool
        .call(
            &mut ctx,
            json!({
                "scope": "crates/pipeline/mod.rs",
                "owner_session": beta_session_id,
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();
}

#[tokio::test]
async fn test_workflow_c_epistemic_hypothesis_validation_loop() {
    let claims_ledger = Arc::new(Mutex::new(ClaimsLedger::new()));
    let claims_tool = ClaimsTool::new(claims_ledger.clone());
    let mut ctx = Context::default();

    // Register 5 competing hypotheses
    let confidences = [0.90, 0.70, 0.60, 0.40, 0.20];
    let mut claim_ids = Vec::new();

    for (i, &conf) in confidences.iter().enumerate() {
        let add_res = claims_tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": format!("Scientific hypothesis {i} regarding latency scaling"),
                    "domain": "systems_research",
                    "source_date": "2026-09-18",
                    "predicted_outcome": "Observed metric within tolerance",
                    "confidence": conf,
                    "falsification_criteria": "Observed metric exceeds tolerance",
                }),
            )
            .await
            .unwrap();
        claim_ids.push(add_res["claim_id"].as_str().unwrap().to_string());
    }

    // Resolve: 3 validate, 2 falsify
    let outcomes = [true, true, true, false, false];
    for (cid, &val) in claim_ids.iter().zip(outcomes.iter()) {
        claims_tool
            .call(
                &mut ctx,
                json!({
                    "action": "resolve",
                    "claim_id": cid,
                    "validated": val,
                    "event": format!("Empirical benchmark verification for {cid}"),
                    "event_date": "2026-09-18",
                    "source": "receipt://experiment-suite-v1",
                }),
            )
            .await
            .unwrap();
    }

    // Evaluate statutory calibration
    let cal = claims_tool
        .call(&mut ctx, json!({ "action": "calibration" }))
        .await
        .unwrap();
    assert_eq!(cal["resolved"], 5);
    assert_eq!(cal["validated"], 3);
    assert_eq!(cal["falsified"], 2);
    assert!((cal["hit_rate"].as_f64().unwrap() - 0.60).abs() < 1e-6);

    // Register pending prediction to observe statutory shrinkage
    let future_res = claims_tool
        .call(
            &mut ctx,
            json!({
                "action": "add",
                "statement": "Next experiment hypothesis",
                "domain": "systems_research",
                "source_date": "2026-09-18",
                "predicted_outcome": "Metric matches",
                "confidence": 0.85,
                "falsification_criteria": "Metric deviates",
            }),
        )
        .await
        .unwrap();
    let future_id = future_res["claim_id"].as_str().unwrap();

    let cal2 = claims_tool
        .call(&mut ctx, json!({ "action": "calibration" }))
        .await
        .unwrap();
    let entry = cal2["pending_recalibrated"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["id"] == future_id)
        .unwrap();

    // Raw confidence 0.85 is preserved; calibrated confidence shrunk toward 0.60
    assert_eq!(entry["confidence"], 0.85);
    let cal_conf = entry["calibrated_confidence"].as_f64().unwrap();
    // w = 5 / (5 + 20) = 0.20 -> cal_conf = 0.85 + 0.20 * (0.60 - 0.85) = 0.85 - 0.05 = 0.80
    assert!((cal_conf - 0.80).abs() < 1e-6);
}

#[tokio::test]
async fn test_workflow_d_the_intentionally_awful_workflow() {
    let (_dir_repo, root) = fake_git_repo();
    let (_dir_store, store) = test_store();
    let claims_ledger = Arc::new(Mutex::new(ClaimsLedger::new()));

    let start_tool = SessionStartTool::new(store.clone());
    let record_tool = SessionRecordTool::new(store.clone());
    let continuity_tool = SessionContinuityTool::new(store.clone());
    let checkpoint_tool = SessionCheckpointNodiscoveryTool::new(store.clone());
    let claim_tool = CodeClaimTool::new(None);
    let check_tool = CodeCheckTool::new(None);
    let release_tool = CodeReleaseTool::new(None);
    let claims_tool = ClaimsTool::new(claims_ledger.clone());
    let mut ctx = Context::default();

    // === PHASE D1: Worker 1 starts under Spec v1 ===
    let w1_start = start_tool.call(&mut ctx, json!({})).await.unwrap();
    let w1_session_id = w1_start["session_id"].as_str().unwrap().to_string();

    // Worker 1 acquires lease with TTL = 1 second
    let claim1 = claim_tool
        .call(
            &mut ctx,
            json!({
                "scope": "crates/compiler/scanner.rs",
                "intent": "implement ASCII-only scanner per Spec v1",
                "owner_session": w1_session_id,
                "ttl_secs": 1,
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(claim1["status"], "success");

    let claim_v1 = claims_tool
        .call(
            &mut ctx,
            json!({
                "action": "add",
                "statement": "ASCII scanner will satisfy all compiler benchmarks",
                "domain": "compiler_spec",
                "source_date": "2026-09-18",
                "predicted_outcome": "Benchmarks pass",
                "confidence": 0.90,
                "falsification_criteria": "Unicode test cases fail",
            }),
        )
        .await
        .unwrap();
    let claim_v1_id = claim_v1["claim_id"].as_str().unwrap().to_string();

    // Verify lease is active
    let check_active = check_tool
        .call(
            &mut ctx,
            json!({
                "scope": "crates/compiler/scanner.rs",
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(check_active["state"], "claimed");
    assert_eq!(check_active["holder"], w1_session_id);

    // Record Worker 1 turn before crash
    record_tool
        .call(
            &mut ctx,
            json!({
                "session_id": w1_session_id,
                "role": "ai",
                "content": "Beginning ASCII scanner implementation per Spec v1",
            }),
        )
        .await
        .unwrap();

    // Partial checkpoint from Worker 1 before crash
    checkpoint_tool
        .call(
            &mut ctx,
            json!({
                "session_id": w1_session_id,
                "project": root_str(&root),
                "next_queue": ["finish_ascii_scanner"],
                "open_flags": ["spec:v1"],
                "tests_green": false,
            }),
        )
        .await
        .unwrap();

    // === PHASE D2: Requirements Shift & Hard Crash ===
    // Spec changes mid-flight: Unicode UTF-8 required!
    // Worker 1 process drops off without releasing lease!

    // === PHASE D3: Lease Expiry Simulation ===
    // Wait for TTL (1 sec) to expire
    sleep(Duration::from_millis(1100)).await;

    // External CI test falsifies the abandoned ASCII hypothesis
    claims_tool
        .call(
            &mut ctx,
            json!({
                "action": "resolve",
                "claim_id": claim_v1_id,
                "validated": false,
                "event": "Unicode UTF-8 test suite executed and rejected ASCII-only scanner",
                "event_date": "2026-09-18",
                "source": "receipt://ci/unicode-failure",
            }),
        )
        .await
        .unwrap();

    // === PHASE D4: Successor Worker 2 Awakens ===
    let w2_start = start_tool.call(&mut ctx, json!({})).await.unwrap();
    let w2_session_id = w2_start["session_id"].as_str().unwrap().to_string();

    // Successor checks lock status -> lease has expired -> state is "free"
    let check_res = check_tool
        .call(
            &mut ctx,
            json!({
                "scope": "crates/compiler/scanner.rs",
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(check_res["state"], "free");

    // Successor discovers prior session via continuity
    let cont_res = continuity_tool
        .call(
            &mut ctx,
            json!({
                "current_session_id": w2_session_id,
                "project": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(cont_res["status"], "success");
    assert_eq!(cont_res["previous_session"], w1_session_id);
    let handoff = &cont_res["checkpoint"];
    assert_eq!(handoff["open_flags"][0], "spec:v1");

    // Successor calls claim -> cleanly claims the scope under Spec v2
    let claim2 = claim_tool
        .call(
            &mut ctx,
            json!({
                "scope": "crates/compiler/scanner.rs",
                "intent": "implement full UTF-8 Unicode scanner per updated Spec v2",
                "owner_session": w2_session_id,
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(claim2["status"], "success");
    assert_eq!(claim2["owner_session"], w2_session_id);

    // Successor records new implementation turn
    record_tool
        .call(
            &mut ctx,
            json!({
                "session_id": w2_session_id,
                "role": "ai",
                "content": "UTF-8 Unicode decoder implemented. All Unicode test cases passing.",
            }),
        )
        .await
        .unwrap();

    // Successor checkpoints new clean state
    checkpoint_tool
        .call(
            &mut ctx,
            json!({
                "session_id": w2_session_id,
                "project": root_str(&root),
                "next_queue": ["completed_utf8_scanner"],
                "open_flags": ["spec:v2"],
                "tests_green": true,
            }),
        )
        .await
        .unwrap();

    // Successor releases lease cleanly
    let rel2 = release_tool
        .call(
            &mut ctx,
            json!({
                "scope": "crates/compiler/scanner.rs",
                "owner_session": w2_session_id,
                "root": root_str(&root),
            }),
        )
        .await
        .unwrap();
    assert_eq!(rel2["status"], "success");
    assert_eq!(rel2["state"], "released");

    // Verify claims ledger recorded the miss honestly
    let cal = claims_tool
        .call(&mut ctx, json!({ "action": "calibration" }))
        .await
        .unwrap();
    assert_eq!(cal["falsified"], 1);
    assert_eq!(cal["validated"], 0);
    assert_eq!(cal["hit_rate"], 0.0);
}
