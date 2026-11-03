use std::fs;
use std::process::Command;
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

#[test]
fn test_sandbox_envelope_exec_mandala_b2() {
    let tmp_dir = std::env::temp_dir().join(format!("wm_sandbox_envelope_{}", std::process::id()));
    fs::create_dir_all(&tmp_dir).expect("create test tmp dir");
    let test_file = tmp_dir.join("envelope_test.txt");

    let builder = SandboxBuilder::new().rw_path(&tmp_dir).allow_net(false);
    let status = builder
        .spawn_command("touch", &[test_file.to_string_lossy().to_string()])
        .expect("spawn touch via builder");
    assert!(status.success());
    assert!(test_file.exists());

    let _ = fs::remove_dir_all(&tmp_dir);
}

#[cfg(target_os = "linux")]
#[test]
fn test_sandbox_exec_refuses_failed_confinement_before_child_runs() {
    for envelope in [false, true] {
        let marker = std::env::temp_dir().join(format!(
            "wm_sandbox_refused_child_{}_{}",
            std::process::id(),
            envelope
        ));
        assert!(!marker.exists(), "child marker must start absent");

        // A file cannot receive the directory rights in this RW ruleset.
        // The CLI must refuse execution when Landlock rejects that rule.
        let mut command = Command::new(env!("CARGO_BIN_EXE_wm-sandbox"));
        command.args(["--rw", "/dev/null"]);
        if envelope {
            command.arg("--exec").arg(
                serde_json::json!({
                    "program": "/usr/bin/touch",
                    "args": [marker.to_string_lossy()]
                })
                .to_string(),
            );
        } else {
            command.args(["--", "/usr/bin/touch"]).arg(&marker);
        }
        let output = command.output().expect("run sandbox CLI");
        let child_ran = marker.exists();
        if child_ran {
            fs::remove_file(&marker).expect("remove unexpected child marker");
        }

        assert!(!child_ran, "child ran after failed confinement: {output:?}");
        assert_eq!(output.status.code(), Some(126), "{output:?}");
        assert!(
            String::from_utf8_lossy(&output.stderr).contains("confinement failed"),
            "{output:?}"
        );
    }
}

#[cfg(target_os = "linux")]
#[test]
fn test_sandbox_exec_confines_valid_child() {
    if probe_sandbox_status().kernel_landlock_abi < 5 {
        eprintln!("Skipping valid CLI confinement check: filesystem ABI 5 unavailable");
        return;
    }

    let denied_root = std::path::Path::new("/dev/shm");
    if !denied_root.is_dir() {
        eprintln!("Skipping valid CLI confinement check: /dev/shm unavailable");
        return;
    }
    let allowed_dir = std::path::Path::new("/tmp")
        .join(format!("wm_sandbox_exec_allowed_{}", std::process::id()));
    // This caller-owned path is outside the default writable /tmp grant,
    // including when the checkout itself happens to live under /tmp.
    let denied_dir = denied_root.join(format!("wm_sandbox_exec_denied_{}", std::process::id()));
    fs::create_dir(&allowed_dir).expect("create allowed test directory");
    fs::create_dir(&denied_dir).expect("create denied test directory");
    let allowed_marker = allowed_dir.join("child-ran");
    let denied_marker = denied_dir.join("escaped");

    let output = Command::new(env!("CARGO_BIN_EXE_wm-sandbox"))
        .args([
            "--",
            "/bin/sh",
            "-c",
            "printf confined > \"$1\"; if printf escaped > \"$2\"; then exit 42; fi",
            "--",
        ])
        .arg(&allowed_marker)
        .arg(&denied_marker)
        .current_dir(&allowed_dir)
        .output()
        .expect("run valid sandbox CLI");
    let child_output = fs::read_to_string(&allowed_marker);
    let escaped = denied_marker.exists();
    fs::remove_dir_all(&allowed_dir).expect("remove allowed test directory");
    fs::remove_dir_all(&denied_dir).expect("remove denied test directory");

    assert!(output.status.success(), "{output:?}");
    assert_eq!(
        child_output.expect("child ran in allowed directory"),
        "confined"
    );
    assert!(!escaped, "child wrote outside its permitted directory");
}
