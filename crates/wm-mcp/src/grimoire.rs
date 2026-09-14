//! `wm grimoire` — guided, agent-first first-run orchestration.
//!
//! The product already ships every deterministic primitive a new install
//! needs (quickstart, selftest, setup, status, update, continuity). The
//! grimoire wires them into one guided pass so an arriving agent can go
//! from "binary on PATH" to "taught and demonstrated" without reading the
//! docs:
//!
//! ```text
//! host → substrate → release → agent → memory → teach → continuity
//! ```
//!
//! Two audiences, one run: humans get stable `[OK]/[WARN]/[SKIP]/[FAIL]`
//! lines, agents get `--json` with the same steps. The pass is read-only
//! unless `--write` is given (which applies `wm setup` to detected client
//! configs), and it never touches the real store for the continuity demo —
//! that runs on a throwaway store like the selftest.

#![forbid(unsafe_code)]

use serde::Serialize;
use serde_json::{Value, json};
use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use crate::McpServer;

/// Outcome of one grimoire step.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum StepStatus {
    /// The check ran and passed.
    Ok,
    /// Something optional is missing or degraded; the install still works.
    Warn,
    /// The step could not run in this environment (offline, platform).
    Skip,
    /// The step ran and failed; the install is not ready.
    Fail,
}

/// One grimoire step.
#[derive(Debug, Clone, Serialize)]
pub struct Step {
    /// Stable machine name (host, substrate, release, agent, memory, teach, continuity).
    pub name: &'static str,
    /// Step outcome.
    pub status: StepStatus,
    /// Human-readable detail (values, paths, counts).
    pub detail: String,
    /// Wall time for this step.
    pub ms: u128,
}

/// The full grimoire report.
#[derive(Debug, Clone, Serialize)]
pub struct Report {
    /// Binary version under test.
    pub version: String,
    /// True when no step failed (warnings and skips are still "ready").
    pub ready: bool,
    /// Steps in execution order.
    pub steps: Vec<Step>,
    /// Total wall time.
    pub total_ms: u128,
}

/// Options for a grimoire run.
#[derive(Debug, Clone)]
pub struct Options {
    /// Store root to report on (created on first serve; never written here).
    pub store: PathBuf,
    /// Apply `wm setup` to detected client configs.
    pub write: bool,
    /// Best-effort release check (network); off in tests.
    pub check_release: bool,
}

fn step(name: &'static str, status: StepStatus, detail: String, started: Instant) -> Step {
    Step {
        name,
        status,
        detail,
        ms: started.elapsed().as_millis(),
    }
}

fn read_meminfo_gb() -> Option<u64> {
    let text = std::fs::read_to_string("/proc/meminfo").ok()?;
    let kb: u64 = text
        .lines()
        .find(|l| l.starts_with("MemTotal:"))?
        .split_whitespace()
        .nth(1)?
        .parse()
        .ok()?;
    Some(kb / 1024 / 1024)
}

fn has_avx2() -> bool {
    std::fs::read_to_string("/proc/cpuinfo").is_ok_and(|t| t.contains(" avx2 "))
}

fn host_step() -> Step {
    let t = Instant::now();
    let os = std::env::consts::OS;
    let arch = std::env::consts::ARCH;
    let kernel = std::fs::read_to_string("/proc/sys/kernel/osrelease")
        .ok()
        .map(|s| s.trim().to_string());
    let cores = std::thread::available_parallelism().map_or(0, std::num::NonZero::get);

    let supported = matches!(
        (os, arch),
        ("linux" | "windows", "x86_64") | ("macos", "x86_64" | "aarch64")
    );

    let mut detail = format!("{os} {arch}");
    if let Some(k) = &kernel {
        let _ = write!(detail, ", kernel {k}");
    }
    if cores > 0 {
        let _ = write!(detail, ", {cores} cores");
    }
    if let Some(gb) = read_meminfo_gb() {
        let _ = write!(detail, ", {gb} GB RAM");
    }
    if has_avx2() {
        detail.push_str(", AVX2");
    }
    if !supported {
        detail.push_str(" (outside the install-gated alpha targets)");
    }

    step(
        "host",
        if supported {
            StepStatus::Ok
        } else {
            StepStatus::Warn
        },
        detail,
        t,
    )
}

async fn substrate_step() -> Step {
    let t = Instant::now();
    match crate::selftest::run().await {
        Ok(report) => {
            let (passed, total) = report.score();
            step(
                "substrate",
                if report.passed() {
                    StepStatus::Ok
                } else {
                    StepStatus::Fail
                },
                format!("{passed}/{total} invariants in {} ms", report.total_ms),
                t,
            )
        }
        Err(e) => step(
            "substrate",
            StepStatus::Fail,
            format!("selftest could not run: {e}"),
            t,
        ),
    }
}

fn release_step() -> Step {
    let t = Instant::now();
    let current = env!("CARGO_PKG_VERSION");
    match crate::update::fetch_manifest_text(
        crate::update::DEFAULT_MANIFEST_URL,
        Duration::from_secs(5),
    ) {
        Ok(text) => match serde_json::from_str::<crate::update::ReleaseManifest>(&text) {
            Ok(m) if m.version == current => {
                step("release", StepStatus::Ok, format!("{current} (current)"), t)
            }
            Ok(m) => step(
                "release",
                StepStatus::Warn,
                format!(
                    "{} available (current {current}) — run 'wm update check'",
                    m.version
                ),
                t,
            ),
            Err(e) => step(
                "release",
                StepStatus::Warn,
                format!("{current} (manifest unreadable: {e})"),
                t,
            ),
        },
        Err(_) => step(
            "release",
            StepStatus::Skip,
            format!("{current} (offline — update check skipped)"),
            t,
        ),
    }
}

fn agent_step(write: bool) -> Step {
    let t = Instant::now();
    let exe = std::env::current_exe().ok();
    let detected: Vec<_> = crate::setup::specs()
        .into_iter()
        .filter(|s| s.config_path.exists())
        .collect();

    if detected.is_empty() {
        return step(
            "agent",
            StepStatus::Warn,
            "no MCP client config detected — wire one with 'wm setup <client>'".to_string(),
            t,
        );
    }

    let mut parts = Vec::new();
    let mut status = StepStatus::Ok;
    for spec in &detected {
        let configured = std::fs::read_to_string(&spec.config_path)
            .is_ok_and(|text| text.contains("whitemagic"));
        if configured {
            parts.push(format!("{}: configured", spec.id));
            continue;
        }
        if write {
            match exe.as_deref().map(|e| crate::setup::write(spec, e)) {
                Some(Ok((msg, _backup))) => parts.push(format!("{}: {msg}", spec.id)),
                Some(Err(e)) => {
                    status = StepStatus::Warn;
                    parts.push(format!("{}: write failed: {e}", spec.id));
                }
                None => {
                    status = StepStatus::Warn;
                    parts.push(format!("{}: cannot resolve this binary", spec.id));
                }
            }
        } else {
            parts.push(format!(
                "{}: found — run 'wm setup {} --write'",
                spec.id, spec.id
            ));
        }
    }

    step("agent", status, parts.join("; "), t)
}

fn memory_step(store: &Path) -> Step {
    let t = Instant::now();
    let report = crate::status::collect(store);
    let embedder = if std::env::var("WM_EMBEDDER_ENDPOINT").is_ok()
        || std::env::var("WM_EMBEDDER_BACKEND").is_ok()
    {
        "local embeddings configured"
    } else {
        "lexical search (no model needed)"
    };

    if !report.store_ok {
        return step(
            "memory",
            StepStatus::Ok,
            format!(
                "no store yet at {} — created on first 'wm serve' or agent write; {embedder}",
                store.display()
            ),
            t,
        );
    }

    let status = if report.index_ok {
        StepStatus::Ok
    } else {
        StepStatus::Warn
    };
    step(
        "memory",
        status,
        format!(
            "{} — {} memories, {} sessions, index {}; {embedder}",
            store.display(),
            report.memories,
            report.sessions,
            if report.index_ok {
                "healthy"
            } else {
                "missing"
            }
        ),
        t,
    )
}

/// The core habits an arriving agent should internalize. The contract is
/// explicit `route=` dispatch; these are the mappings worth teaching first.
pub const VOCABULARY: &[(&str, &str)] = &[
    ("remember / record X", "memory.create"),
    ("find X / what do you remember about X", "memory.search"),
    ("what did we decide about X", "memory.search"),
    ("resume work", "session.continuity"),
    ("correct a belief", "memory.update (supersede)"),
    ("discover the surface", "tools.list"),
    ("finish work", "session.record summary + session.checkpoint"),
];

fn teach_step() -> Step {
    let t = Instant::now();
    step(
        "teach",
        StepStatus::Ok,
        format!(
            "explicit route= is the contract; {} core habits (see skill.md)",
            VOCABULARY.len()
        ),
        t,
    )
}

async fn continuity_step() -> anyhow::Result<Step> {
    let t = Instant::now();
    let tmp = tempfile::tempdir()?;
    let lmdb = tmp.path().join("lmdb");
    let token = format!("grimoire-{}", std::process::id());

    let mut server = McpServer::with_defaults(&lmdb)?;
    crate::selftest::call(
        &mut server,
        1,
        "session.start",
        json!({"title": "grimoire continuity"}),
    )
    .await;
    crate::selftest::call(
        &mut server,
        2,
        "session.record",
        json!({"content": format!("grimoire decision {token}"), "role": "user", "turn_type": "decision"}),
    )
    .await;
    drop(server);

    let mut reopened = McpServer::with_defaults(&lmdb)?;
    let cont = crate::selftest::call(&mut reopened, 3, "session.continuity", json!({"n": 5})).await;
    let count = cont.get("count").and_then(Value::as_u64).unwrap_or(0);
    let recovered = count >= 1
        && cont
            .get("turns")
            .and_then(Value::as_array)
            .is_some_and(|turns| {
                turns.iter().any(|turn| {
                    turn.get("content")
                        .and_then(Value::as_str)
                        .is_some_and(|c| c.contains(&token))
                })
            });

    Ok(step(
        "continuity",
        if recovered {
            StepStatus::Ok
        } else {
            StepStatus::Fail
        },
        if recovered {
            format!("decision recovered after store close/reopen ({count} turn(s))")
        } else {
            "continuity returned no matching turn after reopen".to_string()
        },
        t,
    ))
}

/// Run the full grimoire pass.
///
/// # Errors
///
/// Returns an error only when the report itself cannot be assembled (the
/// individual steps degrade into `[FAIL]` entries instead).
pub async fn run(opts: Options) -> anyhow::Result<Report> {
    let overall = Instant::now();
    let mut steps = vec![host_step()];
    steps.push(substrate_step().await);
    steps.push(if opts.check_release {
        release_step()
    } else {
        Step {
            name: "release",
            status: StepStatus::Skip,
            detail: format!("{} (release check disabled)", env!("CARGO_PKG_VERSION")),
            ms: 0,
        }
    });
    steps.push(agent_step(opts.write));
    steps.push(memory_step(&opts.store));
    steps.push(teach_step());
    steps.push(match continuity_step().await {
        Ok(s) => s,
        Err(e) => Step {
            name: "continuity",
            status: StepStatus::Fail,
            detail: format!("could not run: {e}"),
            ms: 0,
        },
    });

    let ready = steps.iter().all(|s| s.status != StepStatus::Fail);
    Ok(Report {
        version: env!("CARGO_PKG_VERSION").to_string(),
        ready,
        steps,
        total_ms: overall.elapsed().as_millis(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn host_step_reports_the_running_platform() {
        let s = host_step();
        assert_eq!(s.name, "host");
        assert!(matches!(s.status, StepStatus::Ok | StepStatus::Warn));
        assert!(s.detail.contains(std::env::consts::OS));
        assert!(s.detail.contains(std::env::consts::ARCH));
    }

    #[test]
    fn memory_step_is_calm_on_a_fresh_install() {
        let tmp = tempfile::tempdir().unwrap();
        let s = memory_step(tmp.path());
        assert_eq!(s.status, StepStatus::Ok);
        assert!(s.detail.contains("no store yet"));
    }

    #[test]
    fn teach_step_lists_the_core_habits() {
        let s = teach_step();
        assert_eq!(s.status, StepStatus::Ok);
        assert!(s.detail.contains("explicit route="));
        assert!(
            VOCABULARY
                .iter()
                .any(|(_, route)| *route == "memory.search")
        );
    }

    #[tokio::test]
    async fn grimoire_runs_end_to_end_on_a_throwaway_store() {
        let tmp = tempfile::tempdir().unwrap();
        let report = run(Options {
            store: tmp.path().to_path_buf(),
            write: false,
            check_release: false,
        })
        .await
        .expect("grimoire infrastructure");
        assert!(report.ready, "grimoire must be ready: {report:?}");
        let names: Vec<_> = report.steps.iter().map(|s| s.name).collect();
        assert_eq!(
            names,
            vec![
                "host",
                "substrate",
                "release",
                "agent",
                "memory",
                "teach",
                "continuity"
            ]
        );
        let continuity = report
            .steps
            .iter()
            .find(|s| s.name == "continuity")
            .unwrap();
        assert_eq!(continuity.status, StepStatus::Ok);
    }
}
