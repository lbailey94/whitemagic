#![cfg(target_os = "linux")]

//! Real CLI envelope checks. Builder-field tests are separate from network qualification.
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};

static NEXT_DIRECTORY: AtomicU64 = AtomicU64::new(0);

struct Scratch(PathBuf);

impl Scratch {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "wm-envelope-cli-{}-{}",
            std::process::id(),
            NEXT_DIRECTORY.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn binary() -> Command {
    Command::new(env!("CARGO_BIN_EXE_wm-sandbox"))
}

#[test]
fn malformed_envelopes_refuse_before_any_payload_marker() {
    let scratch = Scratch::new();
    let marker = scratch.0.join("payload-must-not-run");
    let base = serde_json::json!({"program":"/usr/bin/touch", "args":[marker]});
    let invalid = [
        serde_json::json!({"schema":"unsupported"}),
        serde_json::json!({"schema":null}),
        serde_json::json!({"program":""}),
        serde_json::json!({"program":123}),
        serde_json::json!({"program":"/usr/bin/touch\u{0}"}),
        serde_json::json!({"args":null}),
        serde_json::json!({"args":"ignored"}),
        serde_json::json!({"args":[marker,123]}),
        serde_json::json!({"args":[marker,"\u{0}"]}),
        serde_json::json!({"net":"false"}),
        serde_json::json!({"net":1}),
        serde_json::json!({"net":null}),
        serde_json::json!({"workspace":false}),
        serde_json::json!({"workspace":null}),
        serde_json::json!({"workspace":""}),
        serde_json::json!({"workspace":"/tmp\u{0}"}),
        serde_json::json!({"rw":"false"}),
        serde_json::json!({"rw":null}),
        serde_json::json!({"rw":true}),
        serde_json::json!({"egress":["example.org:443"], "net":true}),
        serde_json::json!({"egress":null}),
        serde_json::json!({"unknown_policy":true}),
    ];
    for fields in invalid {
        let mut request = base.clone();
        request
            .as_object_mut()
            .unwrap()
            .extend(fields.as_object().unwrap().clone());
        let output = binary()
            .args(["--exec", &request.to_string()])
            .output()
            .unwrap();
        assert_eq!(
            output.status.code(),
            Some(64),
            "request={request}, output={output:?}"
        );
        assert!(!marker.exists(), "request={request}");
        assert!(String::from_utf8_lossy(&output.stderr).contains("invalid JSON envelope"));
    }
    let base = base.to_string();
    for request in [
        format!("{{\"net\":false,\"net\":true,{}", &base[1..]),
        format!("{{\"program\":\"ignored\",{}", &base[1..]),
        format!("{base} {{}}"),
        "[]".to_string(),
        "{".to_string(),
    ] {
        let output = binary().args(["--exec", &request]).output().unwrap();
        assert_eq!(
            output.status.code(),
            Some(64),
            "request={request}, output={output:?}"
        );
        assert!(!marker.exists(), "request={request}");
    }
    let output = binary().arg("--exec").output().unwrap();
    assert_eq!(output.status.code(), Some(64));
    assert!(!marker.exists());
}

#[test]
fn cli_preserves_literal_arguments_and_valid_optional_fields() {
    let scratch = Scratch::new();
    for net in [false, true] {
        for rw in [false, true] {
            let request = serde_json::json!({
                "schema":"wm-sandbox-exec-v1",
                "program":"/usr/bin/printf",
                "args":["[%s]\n", "", "a b", "--help", "雪", "$HOME", "$(touch ignored)"],
                "workspace":scratch.0,
                "rw":rw,
                "net":net,
                "egress":[],
            });
            let output = binary()
                .args(["--exec", &request.to_string()])
                .output()
                .unwrap();
            assert!(output.status.success(), "{output:?}");
            assert_eq!(
                String::from_utf8(output.stdout).unwrap(),
                "[]\n[a b]\n[--help]\n[雪]\n[$HOME]\n[$(touch ignored)]\n"
            );
        }
    }
    let marker = scratch.0.join("valid-legacy-envelope");
    let request = serde_json::json!({"program":"/usr/bin/touch", "args":[marker]});
    let output = binary()
        .args(["--exec", &request.to_string()])
        .output()
        .unwrap();
    assert!(output.status.success(), "{output:?}");
    assert!(marker.exists());
}

#[test]
fn confinement_setup_failure_cannot_execute_either_cli_form() {
    let scratch = Scratch::new();
    let invalid_rule = scratch.0.join("regular-file-with-directory-access-rule");
    fs::write(&invalid_rule, "fixture").unwrap();
    let marker = scratch.0.join("unconfined-payload-must-not-run");
    let request = serde_json::json!({"program":"/usr/bin/touch", "args":[marker]});
    let output = binary()
        .arg("--ro")
        .arg(&invalid_rule)
        .args(["--exec", &request.to_string()])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(126), "{output:?}");
    assert!(!marker.exists());
    assert!(String::from_utf8_lossy(&output.stderr).contains("confinement failed"));

    let output = binary()
        .arg("--ro")
        .arg(&invalid_rule)
        .args(["--", "/usr/bin/touch"])
        .arg(&marker)
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(126), "{output:?}");
    assert!(!marker.exists());
}
