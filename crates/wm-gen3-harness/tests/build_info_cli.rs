use sha2::{Digest, Sha256};
use std::fs;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[test]
fn build_info_is_read_only_and_hashes_the_running_executable() {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock after epoch")
        .as_nanos();
    let store = std::env::temp_dir().join(format!("wm-build-info-store-{nonce}"));
    assert!(!store.exists());

    let output = Command::new(env!("CARGO_BIN_EXE_wm"))
        .arg("--store")
        .arg(&store)
        .arg("build-info")
        .arg("--json")
        .env("HTTP_PROXY", "http://127.0.0.1:1")
        .env("HTTPS_PROXY", "http://127.0.0.1:1")
        .env("ALL_PROXY", "http://127.0.0.1:1")
        .output()
        .expect("run build-info");

    assert!(
        output.status.success(),
        "build-info failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        !store.exists(),
        "build-info must not create or open the store"
    );

    let identity: serde_json::Value = serde_json::from_slice(&output.stdout).expect("valid JSON");
    assert_eq!(identity["package_version"], env!("CARGO_PKG_VERSION"));
    assert!(
        identity["revision"]
            .as_str()
            .is_some_and(|value| !value.is_empty())
    );
    assert!(
        identity["commit_tree"]
            .as_str()
            .is_some_and(|value| !value.is_empty())
    );
    assert!(matches!(
        identity["worktree"].as_str(),
        Some("clean" | "dirty" | "unknown")
    ));

    let executable = env!("CARGO_BIN_EXE_wm");
    let expected_hash = Sha256::digest(fs::read(executable).expect("read test binary"));
    let mut expected_hex = String::with_capacity(expected_hash.len() * 2);
    for &byte in expected_hash.iter() {
        use std::fmt::Write as _;
        write!(&mut expected_hex, "{byte:02x}").expect("writing into String cannot fail");
    }
    assert_eq!(identity["executable_sha256"], expected_hex);
    assert!(identity["executable_sha256_error"].is_null());
}
