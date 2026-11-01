use std::process::Command;

#[test]
fn dream_cli_crystallization_and_associative_resonance() {
    let store = std::env::temp_dir().join(format!("wm-dream-res-{}", uuid::Uuid::new_v4()));

    // 1. Seed store with multi-turn session records
    let step1 = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "session",
            "record",
            "--session-id",
            "sesh-wave5-crystallize",
            "--content",
            "Initial deployment of Linux Landlock LSM kernel isolation profile",
        ])
        .output()
        .expect("run wm session record step 1");
    assert!(step1.status.success(), "record step 1 must succeed");

    let step2 = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "session",
            "record",
            "--session-id",
            "sesh-wave5-crystallize",
            "--content",
            "Verified zero-write promises with cryptographic provenance receipts",
        ])
        .output()
        .expect("run wm session record step 2");
    assert!(step2.status.success(), "record step 2 must succeed");

    // 2. Execute dual-phase dream cycle with --crystallize and --force
    let dream_output = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "dream",
            "--crystallize",
            "--force",
        ])
        .output()
        .expect("run wm dream --crystallize --force");

    assert!(dream_output.status.success(), "dream command must exit 0");
    let dream_stdout = String::from_utf8_lossy(&dream_output.stdout);
    assert!(
        dream_stdout.contains("Crystals:  1") || dream_stdout.contains("NREM Compaction"),
        "dream stdout should show NREM compaction and crystal synthesis"
    );

    // 3. Verify recall surfaces the memory crystal
    let recall_crystal = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "recall",
            "sesh-wave5-crystallize",
        ])
        .output()
        .expect("run wm recall");
    assert!(recall_crystal.status.success());
    let recall_stdout = String::from_utf8_lossy(&recall_crystal.stdout);
    assert!(
        recall_stdout.contains("memory_crystal") || recall_stdout.contains("Record #"),
        "recall should return the synthesized crystal record"
    );

    // 4. Test associative resonance recall with rich evidence bundle
    let resonance_recall = Command::new(env!("CARGO_BIN_EXE_wm"))
        .args([
            "--store",
            store.to_str().expect("UTF-8 temp path"),
            "recall",
            "--resonance",
            "--resonance-hops",
            "2",
            "--evidence",
            "Linux Landlock LSM",
        ])
        .output()
        .expect("run wm recall --resonance --evidence");

    assert!(resonance_recall.status.success());
    let res_stdout = String::from_utf8_lossy(&resonance_recall.stdout);
    let bundle: serde_json::Value = serde_json::from_str(&res_stdout).expect("valid JSON evidence bundle");

    assert!(bundle.get("resonance_expanded").is_some(), "evidence bundle must contain resonance_expanded flag");
    assert!(bundle.get("resonance_links").is_some(), "evidence bundle must contain resonance_links field");
    assert!(bundle["resonance_links"].is_array(), "resonance_links must be an array");

    let _ = std::fs::remove_dir_all(&store);
}
