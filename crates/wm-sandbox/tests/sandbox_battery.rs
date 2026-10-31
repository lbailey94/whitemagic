use std::fs;
use wm_sandbox::{SandboxBuilder, probe_sandbox_status, run_self_test};

#[test]
fn test_sandbox_status_probing() {
    let status = probe_sandbox_status();
    println!("STATUS: {:#?}", status);
    assert!(status.kernel_landlock_abi >= 1);
    assert!(status.landlock_supported);
    assert!(status.zero_egress_capable);
}

#[test]
fn test_sandbox_self_test_passes() {
    assert!(run_self_test());
}

#[test]
fn test_sandbox_spawn_command_success_and_confinement() {
    let builder = SandboxBuilder::new();
    let status = builder
        .spawn_command("echo", &["wm-sandbox-confined-test".to_string()])
        .expect("spawn echo");
    assert!(status.success());
}

#[test]
fn test_sandbox_builder_rw_and_ro_paths() {
    let tmp_dir = std::env::temp_dir().join(format!("wm_sandbox_test_{}", std::process::id()));
    fs::create_dir_all(&tmp_dir).expect("create test tmp dir");
    let test_file = tmp_dir.join("test.txt");

    let builder = SandboxBuilder::new().rw_path(&tmp_dir);

    let status = builder
        .spawn_command("touch", &[test_file.to_string_lossy().to_string()])
        .expect("spawn touch in rw dir");
    assert!(status.success());

    assert!(test_file.exists());
    let _ = fs::remove_dir_all(&tmp_dir);
}
