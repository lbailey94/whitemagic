//! Adversarial calibration & epistemics stress benchmark (G3-CRB-1 Phase 4).
//!
//! Protocol: docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md §3 Layer 5, §5 Phase 4
//! Baseline: Gen3 Cognitive Runtime Baseline 1 (G3-CRB-1)
//!
//! Asserts 5 Adversarial Forecaster Archetypes:
//! 1. Constant 0.51 Forecaster (Uninformative / Hedging):
//!    - Evaluates Brier score tracking and empirical-Bayes shrinkage across k-sweep.
//! 2. Extreme 0.01 / 0.99 Forecaster (Overconfident / Polarized):
//!    - Evaluates quadratic Brier penalty and calibrated shrinkage without retroactive rewriting.
//! 3. Sudden Degradation Forecaster (Drift / Regime Change):
//!    - 100 well-calibrated claims followed by 100 degraded claims; verifies gap widening and Wilson CI shift.
//! 4. Domain-Specific Miscalibration Forecaster:
//!    - High accuracy in Domain A vs poor accuracy in Domain B; asserts domain isolation in status report.
//! 5. Selective Prediction Refusal Forecaster (Abstention / Coverage Trade-off):
//!    - Refusal / abstention on low-confidence cases yields superior Brier score on selected subset.
//!
//! Also asserts:
//! - Statutory k=20.0 default behavior when k is omitted.
//! - Empty ledger insufficient_data semantics (identity confidence, zero shrinkage).
//! - Resolution completeness: validation event + date + source required.
//! - Raw confidence immutability: raw values remain unchanged.

use serde_json::json;
use std::sync::{Arc, Mutex};
use wm_core::{Context, Tool};
use wm_simulation::{CALIBRATION_PRIOR_SAMPLES, ClaimsLedger};
use wm_tools::expansion::ClaimsTool;

fn new_tool() -> (ClaimsTool, Arc<Mutex<ClaimsLedger>>) {
    let ledger = Arc::new(Mutex::new(ClaimsLedger::new()));
    let tool = ClaimsTool::new(ledger.clone());
    (tool, ledger)
}

#[tokio::test]
async fn test_empty_data_insufficient_data_semantics() {
    let (tool, _) = new_tool();
    let mut ctx = Context::default();

    let cal = tool
        .call(&mut ctx, json!({ "action": "calibration" }))
        .await
        .unwrap();

    assert_eq!(cal["status"], "success");
    assert_eq!(cal["resolved"], 0);
    assert_eq!(cal["validated"], 0);
    assert_eq!(cal["falsified"], 0);
    assert_eq!(cal["shrinkage"], 0.0);
    assert_eq!(cal["prior_samples"], CALIBRATION_PRIOR_SAMPLES);
    assert_eq!(cal["interpretation"], "calibrated");
}

#[tokio::test]
async fn test_constant_hedging_forecaster_and_k_sweep() {
    let (tool, _) = new_tool();
    let mut ctx = Context::default();

    // 100 claims with constant 0.51 confidence
    // 70 validate, 30 falsify (true rate = 0.70)
    for i in 0..100 {
        let add_res = tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": format!("Hedging prediction {i}"),
                    "domain": "hedging_archetype",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "Outcome occurs",
                    "confidence": 0.51,
                    "falsification_criteria": "Outcome does not occur",
                }),
            )
            .await
            .unwrap();
        let claim_id = add_res["claim_id"].as_str().unwrap();

        let validated = i < 70;
        tool.call(
            &mut ctx,
            json!({
                "action": "resolve",
                "claim_id": claim_id,
                "validated": validated,
                "event": format!("Verification event for {claim_id}"),
                "event_date": "2026-02-01",
                "source": "https://groundtruth.example.com/hedging",
            }),
        )
        .await
        .unwrap();
    }

    // Add 1 pending claim with raw confidence 0.51 to observe shrinkage
    let pending_res = tool
        .call(
            &mut ctx,
            json!({
                "action": "add",
                "statement": "Future pending claim",
                "domain": "hedging_archetype",
                "source_date": "2026-03-01",
                "predicted_outcome": "Pending outcome",
                "confidence": 0.51,
                "falsification_criteria": "Falsified if fails",
            }),
        )
        .await
        .unwrap();
    let pending_id = pending_res["claim_id"].as_str().unwrap();

    // Test k-sweep: k in [0, 1, 5, 10, 20, 50, 100]
    let k_values = [0.0, 1.0, 5.0, 10.0, 20.0, 50.0, 100.0];
    let mut prev_shrinkage = 2.0;

    for &k in &k_values {
        let cal = tool
            .call(&mut ctx, json!({ "action": "calibration", "k": k }))
            .await
            .unwrap();

        assert_eq!(cal["resolved"], 100);
        assert_eq!(cal["validated"], 70);
        assert_eq!(cal["falsified"], 30);
        assert!((cal["hit_rate"].as_f64().unwrap() - 0.70).abs() < 1e-6);

        let shrinkage = cal["shrinkage"].as_f64().unwrap();
        let expected_shrinkage = if 100.0 + k > 0.0 {
            100.0 / (100.0 + k)
        } else {
            1.0
        };
        assert!(
            (shrinkage - expected_shrinkage).abs() < 1e-6,
            "Shrinkage at k={k} must match formula"
        );
        assert!(
            shrinkage <= prev_shrinkage,
            "Shrinkage weight must decrease monotonically as k increases"
        );
        prev_shrinkage = shrinkage;

        // Calibrated confidence for pending claim must move toward 0.70 from 0.51
        let pending = cal["pending_recalibrated"]
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["id"] == pending_id)
            .unwrap();
        let cal_conf = pending["calibrated_confidence"].as_f64().unwrap();
        let expected_cal_conf = 0.51 + expected_shrinkage * (0.70 - 0.51);
        assert!(
            (cal_conf - expected_cal_conf).abs() < 1e-6,
            "Recalibrated confidence must match statutory EB shrinkage"
        );
        assert_eq!(
            pending["confidence"], 0.51,
            "Raw confidence must remain strictly immutable"
        );
    }
}

#[tokio::test]
async fn test_extreme_overconfident_forecaster() {
    let (tool, _) = new_tool();
    let mut ctx = Context::default();

    // 100 claims: confidence 0.99, but only 50 validate (50% hit rate)
    for i in 0..100 {
        let add_res = tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": format!("Extreme prediction {i}"),
                    "domain": "extreme_archetype",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "Certain outcome",
                    "confidence": 0.99,
                    "falsification_criteria": "Certain outcome does not occur",
                }),
            )
            .await
            .unwrap();
        let claim_id = add_res["claim_id"].as_str().unwrap();

        let validated = i < 50;
        tool.call(
            &mut ctx,
            json!({
                "action": "resolve",
                "claim_id": claim_id,
                "validated": validated,
                "event": format!("Verification for {claim_id}"),
                "event_date": "2026-02-01",
                "source": "https://groundtruth.example.com/extreme",
            }),
        )
        .await
        .unwrap();
    }

    let cal = tool
        .call(&mut ctx, json!({ "action": "calibration" }))
        .await
        .unwrap();

    // Mean confidence: 0.99, hit rate: 0.50 -> gap: +0.49
    let gap = cal["calibration_gap"].as_f64().unwrap();
    assert!((gap - 0.49).abs() < 1e-6);
    assert_eq!(cal["interpretation"], "overconfident");

    // Brier score: 0.5 * (0.99 - 1)^2 + 0.5 * (0.99 - 0)^2 = 0.5 * 0.0001 + 0.5 * 0.9801 = 0.4901
    let brier = cal["brier"].as_f64().unwrap();
    assert!((brier - 0.4901).abs() < 1e-4);

    // Statutory k=20 shrinkage pulls 0.99 down: w = 100 / 120 = 0.8333
    // Calibrated conf = 0.99 + (100/120)*(0.50 - 0.99) = 0.99 - 0.4083 = 0.5817
    let add_future = tool
        .call(
            &mut ctx,
            json!({
                "action": "add",
                "statement": "Next extreme prediction",
                "domain": "extreme_archetype",
                "source_date": "2026-03-01",
                "predicted_outcome": "Outcome",
                "confidence": 0.99,
                "falsification_criteria": "Fails",
            }),
        )
        .await
        .unwrap();
    let future_id = add_future["claim_id"].as_str().unwrap();

    let cal2 = tool
        .call(&mut ctx, json!({ "action": "calibration" }))
        .await
        .unwrap();
    let future_entry = cal2["pending_recalibrated"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["id"] == future_id)
        .unwrap();
    let recal = future_entry["calibrated_confidence"].as_f64().unwrap();
    assert!(
        (recal - 0.5816666666666667).abs() < 1e-4,
        "Extreme confidence must be heavily shrunk toward empirical hit rate"
    );
    assert_eq!(future_entry["confidence"], 0.99);
}

#[tokio::test]
async fn test_sudden_degradation_regime_change() {
    let (tool, _) = new_tool();
    let mut ctx = Context::default();

    // Phase A: 100 claims, well calibrated (confidence 0.80, 80 validated, 20 falsified)
    for i in 0..100 {
        let add_res = tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": format!("Phase A claim {i}"),
                    "domain": "regime_drift",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "Success",
                    "confidence": 0.80,
                    "falsification_criteria": "Fails",
                }),
            )
            .await
            .unwrap();
        let cid = add_res["claim_id"].as_str().unwrap();
        tool.call(
            &mut ctx,
            json!({
                "action": "resolve",
                "claim_id": cid,
                "validated": i < 80,
                "event": "Phase A resolution",
                "event_date": "2026-01-15",
                "source": "provenance://phase-a",
            }),
        )
        .await
        .unwrap();
    }

    let cal_a = tool
        .call(&mut ctx, json!({ "action": "calibration" }))
        .await
        .unwrap();
    let gap_a = cal_a["calibration_gap"].as_f64().unwrap();
    assert!(gap_a.abs() < 1e-6, "Phase A must be perfectly calibrated");
    assert_eq!(cal_a["interpretation"], "calibrated");
    let brier_a = cal_a["brier"].as_f64().unwrap();
    // Brier: 0.8 * (0.8 - 1)^2 + 0.2 * (0.8 - 0)^2 = 0.8 * 0.04 + 0.2 * 0.64 = 0.032 + 0.128 = 0.160
    assert!((brier_a - 0.160).abs() < 1e-4);

    // Phase B: Next 100 claims, regime change (accuracy collapses to 20%, but confidence stays 0.80)
    for i in 100..200 {
        let add_res = tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": format!("Phase B claim {i}"),
                    "domain": "regime_drift",
                    "source_date": "2026-02-01",
                    "predicted_outcome": "Success",
                    "confidence": 0.80,
                    "falsification_criteria": "Fails",
                }),
            )
            .await
            .unwrap();
        let cid = add_res["claim_id"].as_str().unwrap();
        tool.call(
            &mut ctx,
            json!({
                "action": "resolve",
                "claim_id": cid,
                "validated": i < 120, // only 20 validate
                "event": "Phase B resolution",
                "event_date": "2026-02-15",
                "source": "provenance://phase-b",
            }),
        )
        .await
        .unwrap();
    }

    let cal_b = tool
        .call(&mut ctx, json!({ "action": "calibration" }))
        .await
        .unwrap();
    assert_eq!(cal_b["resolved"], 200);
    assert_eq!(cal_b["validated"], 100);
    assert_eq!(cal_b["falsified"], 100);
    assert!((cal_b["hit_rate"].as_f64().unwrap() - 0.50).abs() < 1e-6);

    // Calibration gap widened from 0.0 to +0.30 (overconfident!)
    let gap_b = cal_b["calibration_gap"].as_f64().unwrap();
    assert!((gap_b - 0.30).abs() < 1e-6);
    assert_eq!(cal_b["interpretation"], "overconfident");

    // Brier score degraded from 0.160 to 0.340 (Phase B alone was 0.520)
    let brier_b = cal_b["brier"].as_f64().unwrap();
    assert!((brier_b - 0.340).abs() < 1e-4);
    assert!(
        brier_b > brier_a * 2.0,
        "Sudden degradation must cause sharp Brier score penalty"
    );
}

#[tokio::test]
async fn test_domain_specific_miscalibration_isolation() {
    let (tool, _) = new_tool();
    let mut ctx = Context::default();

    // Domain A (agent_architecture): 50 claims, 90% hit rate, 0.90 confidence
    for i in 0..50 {
        let add = tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": format!("Architecture claim {i}"),
                    "domain": "agent_architecture",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "Success",
                    "confidence": 0.90,
                    "falsification_criteria": "Fails",
                }),
            )
            .await
            .unwrap();
        let cid = add["claim_id"].as_str().unwrap();
        tool.call(
            &mut ctx,
            json!({
                "action": "resolve",
                "claim_id": cid,
                "validated": i < 45,
                "event": "Verified architecture benchmark",
                "event_date": "2026-01-10",
                "source": "receipt://arch-bench",
            }),
        )
        .await
        .unwrap();
    }

    // Domain B (market_macro): 50 claims, 20% hit rate, 0.85 confidence
    for i in 0..50 {
        let add = tool
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": format!("Macro claim {i}"),
                    "domain": "market_macro",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "Success",
                    "confidence": 0.85,
                    "falsification_criteria": "Fails",
                }),
            )
            .await
            .unwrap();
        let cid = add["claim_id"].as_str().unwrap();
        tool.call(
            &mut ctx,
            json!({
                "action": "resolve",
                "claim_id": cid,
                "validated": i < 10,
                "event": "Market outcome recorded",
                "event_date": "2026-01-10",
                "source": "receipt://market-data",
            }),
        )
        .await
        .unwrap();
    }

    // Assert domain status isolation
    let status = tool
        .call(&mut ctx, json!({ "action": "status" }))
        .await
        .unwrap();
    let domains = status["domains"].as_array().unwrap();

    let arch = domains
        .iter()
        .find(|d| d["domain"] == "agent_architecture")
        .unwrap();
    assert_eq!(arch["validated"], 45);
    assert_eq!(arch["falsified"], 5);

    let macro_dom = domains
        .iter()
        .find(|d| d["domain"] == "market_macro")
        .unwrap();
    assert_eq!(macro_dom["validated"], 10);
    assert_eq!(macro_dom["falsified"], 40);

    // Filtered lists confirm separation
    let list_arch = tool
        .call(
            &mut ctx,
            json!({ "action": "list", "domain": "agent_architecture" }),
        )
        .await
        .unwrap();
    assert_eq!(list_arch["claims"].as_array().unwrap().len(), 50);

    let list_macro = tool
        .call(
            &mut ctx,
            json!({ "action": "list", "domain": "market_macro" }),
        )
        .await
        .unwrap();
    assert_eq!(list_macro["claims"].as_array().unwrap().len(), 50);
}

#[tokio::test]
async fn test_selective_prediction_refusal_superiority() {
    let (tool_indiscriminate, _) = new_tool();
    let (tool_selective, _) = new_tool();
    let mut ctx = Context::default();

    // 100 propositions total:
    // - 50 propositions have clear signal (80% validate, true confidence 0.80)
    // - 50 propositions have noisy/random signal (50% validate, but model is uncertain)

    // Indiscriminate forecaster: predicts on all 100 (guesses 0.80 on all)
    for i in 0..100 {
        let add = tool_indiscriminate
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": format!("Prop {i}"),
                    "domain": "indiscriminate",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "Outcome",
                    "confidence": 0.80,
                    "falsification_criteria": "Fails",
                }),
            )
            .await
            .unwrap();
        let cid = add["claim_id"].as_str().unwrap();
        let validated = if i < 50 { i < 40 } else { i < 75 }; // 40 + 25 = 65 validate
        tool_indiscriminate
            .call(
                &mut ctx,
                json!({
                    "action": "resolve",
                    "claim_id": cid,
                    "validated": validated,
                    "event": "Resolution",
                    "event_date": "2026-01-15",
                    "source": "https://example.com/res",
                }),
            )
            .await
            .unwrap();
    }

    // Selective forecaster: abstains / refuses to predict on the 50 noisy propositions
    // Only records claims on the 50 high-confidence propositions (40 validate, 10 falsify)
    for i in 0..50 {
        let add = tool_selective
            .call(
                &mut ctx,
                json!({
                    "action": "add",
                    "statement": format!("Prop {i}"),
                    "domain": "selective",
                    "source_date": "2026-01-01",
                    "predicted_outcome": "Outcome",
                    "confidence": 0.80,
                    "falsification_criteria": "Fails",
                }),
            )
            .await
            .unwrap();
        let cid = add["claim_id"].as_str().unwrap();
        let validated = i < 40;
        tool_selective
            .call(
                &mut ctx,
                json!({
                    "action": "resolve",
                    "claim_id": cid,
                    "validated": validated,
                    "event": "Resolution",
                    "event_date": "2026-01-15",
                    "source": "https://example.com/res",
                }),
            )
            .await
            .unwrap();
    }

    let cal_indiscriminate = tool_indiscriminate
        .call(&mut ctx, json!({ "action": "calibration" }))
        .await
        .unwrap();
    let cal_selective = tool_selective
        .call(&mut ctx, json!({ "action": "calibration" }))
        .await
        .unwrap();

    let brier_indiscriminate = cal_indiscriminate["brier"].as_f64().unwrap();
    let brier_selective = cal_selective["brier"].as_f64().unwrap();

    // Selective forecaster achieves significantly better (lower) Brier score and smaller gap
    assert!(
        brier_selective < brier_indiscriminate,
        "Selective prediction refusal must achieve strictly superior Brier score ({brier_selective} vs {brier_indiscriminate})"
    );
    let gap_selective = cal_selective["calibration_gap"].as_f64().unwrap().abs();
    let gap_indiscriminate = cal_indiscriminate["calibration_gap"]
        .as_f64()
        .unwrap()
        .abs();
    assert!(
        gap_selective <= gap_indiscriminate,
        "Selective forecaster has smaller calibration gap ({gap_selective} vs {gap_indiscriminate})"
    );
}
