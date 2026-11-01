use std::process::Command;

#[test]
fn inspect_cli_nonexistent_store_fails_closed() {
    let non_existent = std::env::temp_dir().join(format!("wm-inspect-none-{}", uuid::Uuid::new_v4()));
    assert!(!non_existent.exists());

    let output = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            non_existent.to_str().expect("UTF-8 temp path"),
            "inspect",
            "--promise",
            "strict-zero-write",
        ])
        .output()
        .expect("run wm inspect");

    assert!(!output.status.success(), "inspect must fail on non-existent store");
    assert!(!non_existent.exists(), "non-existent store directory must not be auto-created");
}

#[test]
fn inspect_cli_strict_zero_write_passes_verification() {
    let store = std::env::temp_dir().join(format!("wm-inspect-zw-{}", uuid::Uuid::new_v4()));
    let seed = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "remember",
            "Immutable archive record for CLI inspection test.",
        ])
        .output()
        .expect("run wm remember");
    assert!(seed.status.success());

    let output = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "inspect",
            "--promise",
            "strict-zero-write",
            "--json",
        ])
        .output()
        .expect("run wm inspect --json");

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    let report: serde_json::Value = serde_json::from_str(&stdout).expect("valid json output");
    assert_eq!(report["promise"], "strict-zero-write");
    assert_eq!(report["audit_events_appended"], 0);
    assert_eq!(report["zero_writes_verified"], true);

    let _ = std::fs::remove_dir_all(&store);
}

#[test]
fn inspect_cli_recall_with_inspect_promise() {
    let store = std::env::temp_dir().join(format!("wm-inspect-recall-{}", uuid::Uuid::new_v4()));
    let seed = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "remember",
            "Canal system status is operational in Port Meridian.",
        ])
        .output()
        .expect("run wm remember");
    assert!(seed.status.success());

    let output = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "recall",
            "--inspect-promise",
            "strict-zero-write",
            "Canal system status",
        ])
        .output()
        .expect("run wm recall with inspect promise");

    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("Port Meridian") || stdout.contains("operational"));

    let _ = std::fs::remove_dir_all(&store);
}
