//! Acceptance test battery Gate PEB-22: Turnkey Public Benchmark Suite (`wm-benchmark`).
//!
//! Validates:
//! 1. Headless Execution: `wm_benchmark --suite 10of10` completes successfully without intervention.
//! 2. Markdown Report Emission: Emits standardized markdown comparison table.
//! 3. Cryptographic JSON Receipt: Emits deterministic metrics and timestamped receipt.

use std::fs;
use std::process::Command;

#[test]
fn peb22_turnkey_public_benchmark_suite_execution() {
    let tmp_dir = std::env::temp_dir().join(format!("wm-bench-suite-{}", uuid::Uuid::new_v4()));
    fs::create_dir_all(&tmp_dir).expect("create bench tmp dir");

    let report_file = tmp_dir.join("BENCHMARK_REPORT.md");
    let receipt_file = tmp_dir.join("benchmark_receipt.json");

    let output = Command::new(env!("CARGO_BIN_EXE_wm_benchmark"))
        .args([
            "--suite",
            "10of10",
            "--report",
            report_file.to_str().unwrap(),
            "--receipt",
            receipt_file.to_str().unwrap(),
        ])
        .output()
        .expect("execute wm_benchmark --suite 10of10");

    assert!(
        output.status.success(),
        "wm_benchmark failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("10/10 LIVING SUBSTRATE ECOSYSTEM BENCHMARK"));
    assert!(stdout.contains("ALL 4 LIVING SUBSTRATE PILLARS RATIFIED: 10/10 ACROSS THE BOARD"));

    // 1. Verify Markdown report emission
    assert!(
        report_file.exists(),
        "Benchmark report file must be written"
    );
    let report_content = fs::read_to_string(&report_file).unwrap();
    assert!(report_content.contains("WhiteMagic Gen3: Living Substrate Benchmark Report"));
    assert!(report_content.contains("90-Day Idle Sleep Retention"));
    assert!(report_content.contains("Hebbian Spreading Latency"));
    assert!(report_content.contains("MCP Cold-Start Handshake"));
    assert!(report_content.contains("PASS"));

    // 2. Verify JSON receipt emission
    assert!(
        receipt_file.exists(),
        "Benchmark receipt file must be written"
    );
    let receipt_content = fs::read_to_string(&receipt_file).unwrap();
    let receipt: serde_json::Value = serde_json::from_str(&receipt_content).unwrap();
    assert_eq!(receipt["suite"], "10of10_ecosystem");
    assert_eq!(receipt["status"], "passed");
    assert!(
        receipt["metrics"]["hebbian_spreading_latency_ms"]
            .as_f64()
            .unwrap()
            < 10.0
    );
    assert!(
        receipt["metrics"]["mcp_cold_start_handshake_ms"]
            .as_f64()
            .unwrap()
            < 50.0
    );
    assert_eq!(receipt["metrics"]["identity_field_fidelity"], 1.0);

    let _ = fs::remove_dir_all(&tmp_dir);
}
