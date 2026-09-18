//! `wm config` sample-selection CLI guards (9.1.9 tester finding).
//!
//! `--sample-full` parsed but the dispatch only honored `--sample`, so the
//! flag fell through to the effective-config dump — the research surface
//! (hemispheres, cloud LLM, daemon schedules) never reached stdout. These
//! tests pin the CLI behavior end to end.

use std::process::Command;

fn wm(args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_wm"))
        .args(args)
        .output()
        .expect("run wm")
}

fn stdout_of(out: &std::process::Output) -> String {
    String::from_utf8_lossy(&out.stdout).into_owned()
}

#[test]
fn config_sample_full_prints_the_research_sample() {
    let out = wm(&["config", "--sample-full"]);
    assert!(out.status.success(), "wm config --sample-full must exit 0");
    let text = stdout_of(&out);
    for needle in [
        "[llm]",
        "[embedder]",
        "[daemon]",
        "llm_api_key",
        "llm_endpoint",
        "llama_endpoint",
        "left hemisphere",
        "right hemisphere",
        "dream_interval_secs",
        "selfplay_interval_secs",
    ] {
        assert!(
            text.contains(needle),
            "--sample-full output missing {needle:?}:\n{text}"
        );
    }
    assert!(
        !text.contains("# Effective WhiteMagic Configuration"),
        "--sample-full must print a sample, not the effective config:\n{text}"
    );
}

#[test]
fn config_sample_stays_on_the_small_product_surface() {
    let out = wm(&["config", "--sample"]);
    assert!(out.status.success(), "wm config --sample must exit 0");
    let text = stdout_of(&out);
    assert!(text.contains("[store]") && text.contains("[llm]"), "{text}");
    for absent in ["[daemon]", "llm_api_key", "left hemisphere"] {
        assert!(
            !text.contains(absent),
            "small sample must not carry the research surface ({absent:?}):\n{text}"
        );
    }
}

#[test]
fn config_init_sample_full_writes_the_full_sample() {
    let tmp = tempfile::tempdir().unwrap();
    let store = tmp.path().join("store");
    let out = wm(&[
        "config",
        "--init",
        "--sample-full",
        "--store",
        store.to_str().unwrap(),
    ]);
    assert!(
        out.status.success(),
        "wm config --init --sample-full failed: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    let written = std::fs::read_to_string(store.join("config.toml")).unwrap();
    for needle in ["[llm]", "[daemon]", "llm_api_key", "llama_endpoint"] {
        assert!(
            written.contains(needle),
            "--init --sample-full wrote the wrong surface ({needle:?}):\n{written}"
        );
    }
}
