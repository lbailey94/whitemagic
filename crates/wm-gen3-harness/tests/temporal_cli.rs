use std::process::Command;

#[test]
fn temporal_assert_cli_rejects_public_recorded_at_before_opening_store() {
    let store = std::env::temp_dir().join(format!("wm-temporal-cli-{}", uuid::Uuid::new_v4()));
    let output = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "temporal-assert",
            "--request-json",
            r#"{"recorded_at":"2000-01-01T00:00:00Z"}"#,
        ])
        .output()
        .expect("run wm temporal-assert");
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("unknown field `recorded_at`"), "{stderr}");
    assert!(
        !store.exists(),
        "request validation must precede store open"
    );
}
