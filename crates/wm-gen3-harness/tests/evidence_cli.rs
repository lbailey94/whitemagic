use std::process::Command;

#[test]
fn evidence_cli_empty_query_abstains() {
    let store = std::env::temp_dir().join(format!("wm-evidence-cli-{}", uuid::Uuid::new_v4()));
    // Initialize store
    let _ = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "remember",
            "seed record",
        ])
        .output();

    let output = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "evidence-recall",
            "--request-json",
            r#"{"query":""}"#,
        ])
        .output()
        .expect("run wm evidence-recall");
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    let v: serde_json::Value = serde_json::from_str(&stdout).expect("valid json output");
    assert_eq!(v["disposition"], "Insufficient");
    assert_eq!(v["abstention_recommended"], true);
    assert_eq!(v["stop_reason"], "NoMatchingEvidence");
    let _ = std::fs::remove_dir_all(&store);
}

#[test]
fn recall_flag_evidence_emits_json_bundle() {
    let store = std::env::temp_dir().join(format!("wm-evidence-cli-{}", uuid::Uuid::new_v4()));
    // First ingest a test record
    let _ = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "remember",
            "Zephyr Cove operates the canal shuttle program in Mist Reach",
        ])
        .output();

    let output = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "recall",
            "--evidence",
            "Which program does Zephyr Cove operate?",
        ])
        .output()
        .expect("run wm recall --evidence");
    assert!(output.status.success());
    let stdout = String::from_utf8_lossy(&output.stdout);
    let v: serde_json::Value = serde_json::from_str(&stdout).expect("valid json output");
    assert_eq!(v["coverage"], "Complete");
    assert_eq!(v["disposition"], "Resolved");
    assert_eq!(v["abstention_recommended"], false);
    assert_eq!(v["stop_reason"], "CompleteCover");
    assert!(v["hits"].as_array().map_or(0, |a| a.len()) >= 1);
    let _ = std::fs::remove_dir_all(&store);
}
