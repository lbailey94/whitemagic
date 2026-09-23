//! Q08-G1 — daemon-cycle E2E: bounded `run_daemon` on a disposable store.
//!
//! Closes the boundary-matrix §4/§6 G1 gap: `run_daemon` had no E2E — B4's
//! daemon boundary was covered only by unit tests. Shape: the test re-executes
//! itself as a child (Q06 precedent, `wm-memory/src/episodic.rs`), waits for
//! the daemon's `[sweep 1]` summary line, kills the child, and asserts on the
//! store afterwards:
//!
//! 1. cycle gating is health-driven — the frozen low-health child skips every
//!    cycle ("skipped (health)" in the Substrate gnosis log), the healthy child
//!    runs at least one;
//! 2. the daemon boundary dispatches **no route** — the write-audit journal
//!    stays empty (the regression guard for D2: cycles cannot reach a
//!    destructive registry route);
//! 3. a canary record written before the spawn survives byte-identical.
//!
//! Unix-only: relies on re-exec + kill discipline (SIGKILL precedent in
//! `wm-memory`).
#![cfg(unix)]

use std::io::{BufRead, BufReader};
use std::path::Path;
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::time::Duration;
use wm_core::Galaxy;
use wm_memory::{Memory, MemoryStore};

const CHILD_ENV: &str = "WM_Q08_DAEMON_PHASE";
const STORE_ENV: &str = "WM_Q08_DAEMON_STORE";
const TEST_NAME: &str = "daemon_cycle_e2e_health_gate_and_no_dispatch";
const CANARY: &str = "q08 daemon canary: alpha-omega";

fn open_store(store_path: &Path) -> MemoryStore {
    MemoryStore::open_default(store_path).expect("open store")
}

/// Write the canary through the supported path and return its id.
fn write_canary(store_path: &Path) -> String {
    let store = open_store(store_path);
    let memory = Memory::new(Galaxy::Codex, CANARY.to_string());
    store.put(Galaxy::Codex, &memory).unwrap();
    memory.metadata.id.to_string()
}

/// Child branch: pin the requested homeostasis and run the daemon until the
/// parent kills us. `cfg!(test)` in this binary keeps `refresh_homeostasis`
/// from overriding the pinned values.
fn run_child_phase(phase: &str, store_path: &Path) {
    let mut server = wm_mcp::McpServer::with_defaults(store_path).expect("child server");
    let (cpu_load, memory_pressure) = match phase {
        "low_health" => (1.0, 1.0),
        _ => (0.0, 0.0),
    };
    server
        .dharma_gate()
        .update_homeostasis(wm_governance::Homeostasis {
            cpu_load,
            memory_pressure,
            active: false,
        });

    let config = wm_mcp::daemon::DaemonConfig {
        cycle_interval: Duration::from_secs(1),
        // Everything except the cycle sweep is parked far away or disabled:
        // the test needs exactly one bounded sweep.
        dream_interval: Duration::from_secs(3600),
        brain_wave_interval: Duration::from_secs(3600),
        homeostasis_interval: Duration::from_secs(3600),
        codegen_interval: Duration::from_secs(0),
        codegen_auto_apply: false,
        research_interval: Duration::from_secs(3600),
        selfplay_interval: Duration::from_secs(0),
        watchdog_timeout: Duration::from_secs(0),
        checkpoint_interval: Duration::from_secs(0),
        gan_ying_interval: Duration::from_secs(3600),
        citta_interval: Duration::from_secs(3600),
        watchdog_audit_interval: Duration::from_secs(3600),
        symbiosync_interval: Duration::from_secs(3600),
        phagic_interval: Duration::from_secs(3600),
        ..Default::default()
    };
    wm_mcp::daemon::run_daemon(&mut server, &config).expect("daemon run");
}

#[test]
fn daemon_cycle_e2e_health_gate_and_no_dispatch() {
    if let Ok(phase) = std::env::var(CHILD_ENV) {
        let store = std::env::var(STORE_ENV).expect("child store env");
        run_child_phase(&phase, Path::new(&store));
        return;
    }

    for phase in ["low_health", "healthy"] {
        let tmp = tempfile::tempdir().unwrap();
        let store_path = tmp.path().join("lmdb");
        let canary_id = write_canary(&store_path);

        let mut child = Command::new(std::env::current_exe().unwrap())
            .args([TEST_NAME, "--exact", "--nocapture"])
            .env(CHILD_ENV, phase)
            .env(STORE_ENV, &store_path)
            .env("WM_HOMEOSTASIS_FROZEN", "1")
            .env("WM_SELFMODEL_FROZEN", "1")
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .expect("spawn daemon child");

        // Wait for the first sweep summary, then stop the child.
        let stdout = child.stdout.take().expect("child stdout");
        let (tx, rx) = mpsc::channel();
        let reader = std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                if line.contains("[sweep 1]") {
                    let _ = tx.send(line);
                    break;
                }
            }
        });
        let sweep = rx.recv_timeout(Duration::from_secs(90));
        child.kill().ok();
        child.wait().ok();
        reader.join().ok();
        assert!(
            sweep.is_ok(),
            "phase {phase}: daemon never printed a sweep summary"
        );

        // ── assertions on the store after the child is reaped ────────────
        let store = open_store(&store_path);

        let cycle_logs: Vec<Memory> = store
            .scan(Galaxy::Substrate, 500)
            .unwrap()
            .into_iter()
            .filter(|m| m.metadata.tags.iter().any(|t| t == "autonomous"))
            .collect();
        assert!(
            !cycle_logs.is_empty(),
            "phase {phase}: expected gnosis cycle logs"
        );
        let all_skipped = cycle_logs
            .iter()
            .all(|m| m.content.contains("skipped (health)"));
        if phase == "low_health" {
            assert!(
                all_skipped,
                "low-health phase must skip every cycle, got: {:?}",
                cycle_logs.iter().map(|m| &m.content).collect::<Vec<_>>()
            );
        } else {
            assert!(
                !all_skipped,
                "healthy phase must execute at least one cycle, got: {:?}",
                cycle_logs.iter().map(|m| &m.content).collect::<Vec<_>>()
            );
        }

        let canary = store
            .scan(Galaxy::Codex, 100)
            .unwrap()
            .into_iter()
            .find(|m| m.content == CANARY)
            .expect("canary present after the daemon run");
        assert_eq!(canary.metadata.id.to_string(), canary_id);

        // The daemon boundary dispatches no route: nothing may reach the
        // write-audit journal (destructive or otherwise).
        let journal = wm_governance::WriteAuditJournal::new(std::sync::Arc::new(store)).unwrap();
        assert!(
            journal.scan_entries().unwrap().is_empty(),
            "phase {phase}: daemon must not dispatch audited writes"
        );
    }
}
