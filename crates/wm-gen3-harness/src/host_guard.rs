//! Host-guard policy engine: structured host signals -> bounded mitigations.
//!
//! No CLI wiring lives here. The engine is pure policy ([`plan`]) over
//! [`HostSignals`] plus persisted [`HostGuardState`], and one injectable
//! [`CommandRunner`] for execution. Safety envelope:
//!
//! - never a shell: commands are exec'd directly, no `sh -c`, no sudo, no
//!   SIGKILL, no `disable`/`mask`;
//! - mutations are rate-limited by [`SentinelCircuitBreaker`]
//!   (`max_remediations_per_hour`, default 2) and by a per-unit cap
//!   ([`MAX_UNIT_STOPS_PER_DAY`]);
//! - `dry_run` reports the decision without running commands or consuming
//!   breaker/state budget.
//!
//! Decision ladder:
//! - L0 report (always): digest + board post (deduped by digest);
//! - L1 stop crash-looping units (`ActiveState=activating` AND
//!   `SubState=auto-restart` AND `NRestarts >= 20`);
//! - L2 defer `fleet-sync.timer` / `fleet-sync-full.timer` on critical pressure;
//! - L3 SIGTERM orphan heavy inference processes (only with `kill_orphans`);
//! - recovery: resume deferred timers after 2 consecutive calm runs.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use sha2::{Digest as _, Sha256};

use wm_gen3_core::sentinel::SentinelCircuitBreaker;

use crate::host_health::{HostSignals, ProcessInfo, Verdict};

pub const SCHEMA_VERSION: u32 = 1;
pub const HOUR_SECS: u64 = 3_600;
pub const DAY_SECS: u64 = 86_400;
pub const BOARD_TARGET: &str = "@lucas";

pub const PSI_FULL_WARN_AVG10: f64 = 10.0;
pub const PSI_FULL_CRIT_AVG10: f64 = 30.0;
pub const MEM_AVAILABLE_WARN_FRACTION: f64 = 0.15;
pub const MEM_AVAILABLE_CRIT_FRACTION: f64 = 0.05;
pub const MEM_AVAILABLE_CRIT_KIB: u64 = 512 * 1024;
pub const SWAP_WARN_FRACTION: f64 = 0.60;
pub const SWAP_CRIT_FRACTION: f64 = 0.85;
pub const DISK_WARN_GIB: f64 = 20.0;
pub const DISK_CRIT_GIB: f64 = 5.0;
pub const CRASH_LOOP_MIN_RESTARTS: u64 = 20;
pub const ORPHAN_RSS_MIB: u64 = 1024;
pub const ORPHAN_MIN_AGE_SECS: u64 = 600;
pub const MAX_MUTATIONS_PER_HOUR: usize = 2;
pub const MAX_UNIT_STOPS_PER_DAY: usize = 2;
pub const CALM_RUNS_TO_RESUME: u32 = 2;

/// Decision-table thresholds. `Policy::default()` carries the production
/// values; tests override single fields for row coverage.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Policy {
    pub psi_warn_avg10: f64,
    pub psi_crit_avg10: f64,
    pub mem_available_warn_fraction: f64,
    pub mem_available_crit_fraction: f64,
    pub mem_available_crit_kib: u64,
    pub swap_warn_fraction: f64,
    pub swap_crit_fraction: f64,
    pub disk_warn_gib: f64,
    pub disk_crit_gib: f64,
    pub disk_warn_pct: f64,
    pub disk_crit_pct: f64,
    pub crash_loop_min_restarts: u64,
    pub orphan_rss_mib: u64,
    pub orphan_min_age_secs: u64,
    pub orphan_comms: BTreeSet<String>,
    pub orphan_python_markers: Vec<String>,
    pub kill_orphans: bool,
    pub calm_runs_to_resume: u32,
    pub protected_units: Vec<String>,
    pub protected_comms: BTreeSet<String>,
    pub defer_units: Vec<String>,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            psi_warn_avg10: PSI_FULL_WARN_AVG10,
            psi_crit_avg10: PSI_FULL_CRIT_AVG10,
            mem_available_warn_fraction: MEM_AVAILABLE_WARN_FRACTION,
            mem_available_crit_fraction: MEM_AVAILABLE_CRIT_FRACTION,
            mem_available_crit_kib: MEM_AVAILABLE_CRIT_KIB,
            swap_warn_fraction: SWAP_WARN_FRACTION,
            swap_crit_fraction: SWAP_CRIT_FRACTION,
            disk_warn_gib: DISK_WARN_GIB,
            disk_crit_gib: DISK_CRIT_GIB,
            disk_warn_pct: crate::host_health::DISK_PCT_WARN,
            disk_crit_pct: crate::host_health::DISK_PCT_CRIT,
            crash_loop_min_restarts: CRASH_LOOP_MIN_RESTARTS,
            orphan_rss_mib: ORPHAN_RSS_MIB,
            orphan_min_age_secs: ORPHAN_MIN_AGE_SECS,
            orphan_comms: ["llama-server", "ollama"]
                .into_iter()
                .map(String::from)
                .collect(),
            orphan_python_markers: ["lane", "eval", "bench"]
                .into_iter()
                .map(String::from)
                .collect(),
            kill_orphans: false,
            calm_runs_to_resume: CALM_RUNS_TO_RESUME,
            protected_units: [
                "wm-serve@*",
                "wm-gateway*",
                "sangha-*",
                "syncthing*",
                "gnome-*",
                "gdm*",
                "dbus*",
                "sshd*",
            ]
            .into_iter()
            .map(String::from)
            .collect(),
            protected_comms: [
                "wm",
                "wm9",
                "wm10",
                "wm-gen3",
                "valkyrie",
                "codex",
                "chatgpt",
                "electron",
                "chrome",
                "brave",
                "firefox",
                "Xorg",
                "gnome-shell",
                "systemd",
                "dbus-daemon",
            ]
            .into_iter()
            .map(String::from)
            .collect(),
            defer_units: ["fleet-sync.timer", "fleet-sync-full.timer"]
                .into_iter()
                .map(String::from)
                .collect(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "action", rename_all = "snake_case")]
pub enum Action {
    StopUnit {
        unit: String,
    },
    DeferTimer {
        unit: String,
    },
    ResumeTimer {
        unit: String,
    },
    TerminateProcess {
        pid: u32,
    },
    PostBoard {
        digest: String,
        severity: Verdict,
        summary: String,
    },
}

impl Action {
    pub fn label(&self) -> String {
        match self {
            Action::StopUnit { unit } => format!("stop unit {unit}"),
            Action::DeferTimer { unit } => format!("defer timer {unit}"),
            Action::ResumeTimer { unit } => format!("resume timer {unit}"),
            Action::TerminateProcess { pid } => format!("terminate process pid {pid} (SIGTERM)"),
            Action::PostBoard {
                severity, summary, ..
            } => {
                format!("post board [{}] {summary}", severity.as_str())
            }
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct Plan {
    pub severity: Verdict,
    pub reasons: Vec<String>,
    pub actions: Vec<Action>,
    pub suppressed: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ExecutionReport {
    pub severity: Verdict,
    pub dry_run: bool,
    pub executed: Vec<Action>,
    pub skipped: Vec<String>,
    pub failed: Vec<String>,
}

/// Persisted guard state. `#[serde(default)]` plus
/// [`HostGuardState::from_json_or_default`] keep a corrupt or older state file
/// from wedging the guard: parse failures reset to defaults.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct HostGuardState {
    pub schema_version: u32,
    pub breaker: SentinelCircuitBreaker,
    /// Per-unit stop timestamps (epoch seconds, pruned to a 24h window).
    pub unit_stops: BTreeMap<String, Vec<u64>>,
    /// Timers deferred by L2 (unit -> epoch seconds when deferred).
    pub deferred_timers: BTreeMap<String, u64>,
    /// Consecutive calm runs (severity ok, no failed actions).
    pub calm_runs: u32,
    pub last_digest: Option<String>,
    pub last_post_at: Option<u64>,
}

impl Default for HostGuardState {
    fn default() -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            breaker: SentinelCircuitBreaker::default(),
            unit_stops: BTreeMap::new(),
            deferred_timers: BTreeMap::new(),
            calm_runs: 0,
            last_digest: None,
            last_post_at: None,
        }
    }
}

impl HostGuardState {
    pub fn to_json(&self) -> String {
        serde_json::to_string(self).unwrap_or_default()
    }

    /// Parse persisted state; corrupt JSON or an unknown schema version falls
    /// back to [`HostGuardState::default`].
    pub fn from_json_or_default(text: &str) -> Self {
        match serde_json::from_str::<HostGuardState>(text) {
            Ok(state) if state.schema_version == SCHEMA_VERSION => state,
            _ => Self::default(),
        }
    }
}

/// Injectable command boundary. `Some(stdout)` means the command ran and
/// exited successfully; `None` means it could not run or failed.
pub trait CommandRunner {
    fn run(&self, program: &str, args: &[&str]) -> Option<String>;
}

/// Real runner: direct exec only, resolved through `WM_SYSTEMCTL_BIN`
/// (default `/usr/bin/systemctl`) and `WM_SANGHA_BIN` (default `sangha`).
/// Refuses shells, sudo, SIGKILL, `disable`, and `mask`.
#[derive(Debug, Default, Clone, Copy)]
pub struct SystemRunner;

impl SystemRunner {
    fn resolve(program: &str) -> String {
        match program {
            "systemctl" => std::env::var("WM_SYSTEMCTL_BIN")
                .ok()
                .filter(|value| !value.is_empty())
                .unwrap_or_else(|| "/usr/bin/systemctl".to_string()),
            "sangha" => std::env::var("WM_SANGHA_BIN")
                .ok()
                .filter(|value| !value.is_empty())
                .unwrap_or_else(|| "sangha".to_string()),
            "kill" => {
                if Path::new("/bin/kill").exists() {
                    "/bin/kill".to_string()
                } else {
                    "/usr/bin/kill".to_string()
                }
            }
            other => other.to_string(),
        }
    }
}

impl CommandRunner for SystemRunner {
    fn run(&self, program: &str, args: &[&str]) -> Option<String> {
        let forbidden_arg = args.iter().any(|arg| {
            matches!(
                *arg,
                "-c" | "-9"
                    | "-KILL"
                    | "SIGKILL"
                    | "--signal=KILL"
                    | "--signal=SIGKILL"
                    | "disable"
                    | "mask"
            )
        });
        if matches!(program, "sh" | "bash" | "sudo") || forbidden_arg {
            return None;
        }
        let output = Command::new(Self::resolve(program))
            .args(args)
            .output()
            .ok()?;
        if !output.status.success() {
            return None;
        }
        Some(String::from_utf8_lossy(&output.stdout).into_owned())
    }
}

/// systemd-shaped unit names only: `^[A-Za-z0-9@_.:-]+\.(service|timer)$`.
pub fn validate_unit_name(unit: &str) -> bool {
    let stem_valid = unit
        .strip_suffix(".service")
        .or_else(|| unit.strip_suffix(".timer"))
        .is_some_and(|stem| !stem.is_empty());
    stem_valid
        && unit
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '@' | '_' | '.' | ':' | '-'))
}

/// Single-wildcard glob used for the protected-unit patterns (`syncthing*`).
pub fn unit_matches_pattern(unit: &str, pattern: &str) -> bool {
    match pattern.split_once('*') {
        None => unit == pattern,
        Some((prefix, suffix)) => {
            unit.starts_with(prefix)
                && unit.ends_with(suffix)
                && unit.len() >= prefix.len() + suffix.len()
        }
    }
}

pub fn unit_is_protected(unit: &str, patterns: &[String]) -> bool {
    patterns
        .iter()
        .any(|pattern| unit_matches_pattern(unit, pattern))
}

/// Plan with the current wall clock. Deterministic work lives in [`plan_at`].
pub fn plan(signals: &HostSignals, state: &HostGuardState, policy: &Policy) -> Plan {
    plan_at(signals, state, policy, unix_now())
}

/// Evaluate the decision table. Never mutates `state`; returns the bounded
/// action list plus human reasons and suppression notes.
pub fn plan_at(signals: &HostSignals, state: &HostGuardState, policy: &Policy, now: u64) -> Plan {
    let mut reasons = Vec::new();
    let mut suppressed = Vec::new();
    let mut planned = Vec::new();

    let pressure = pressure_verdict(signals, policy, &mut reasons);
    let mut severity = pressure;

    let mut stop_units: Vec<String> = Vec::new();
    if !signals.crash_loop_units.is_empty() {
        severity = severity.max(Verdict::Critical);
        for unit in &signals.crash_loop_units {
            reasons.push(format!(
                "crash-loop: {} ActiveState={} SubState={} NRestarts={}",
                unit.unit, unit.active_state, unit.sub_state, unit.n_restarts
            ));
            if unit.active_state != "activating" || unit.sub_state != "auto-restart" {
                suppressed.push(format!("stop {}: state is not auto-restart", unit.unit));
                continue;
            }
            if unit.n_restarts < policy.crash_loop_min_restarts {
                suppressed.push(format!(
                    "stop {}: NRestarts={} below threshold {}",
                    unit.unit, unit.n_restarts, policy.crash_loop_min_restarts
                ));
                continue;
            }
            if unit_is_protected(&unit.unit, &policy.protected_units) {
                suppressed.push(format!("stop {}: protected unit", unit.unit));
                continue;
            }
            if !validate_unit_name(&unit.unit) {
                suppressed.push(format!("stop {}: invalid unit name", unit.unit));
                continue;
            }
            stop_units.push(unit.unit.clone());
        }
        stop_units.sort();
        stop_units.dedup();
    }

    for unit in &signals.failed_loop_units {
        severity = severity.max(Verdict::Warn);
        reasons.push(format!(
            "failed unit {} (report-only; failed units do not auto-restart)",
            unit.unit
        ));
    }

    let mut kill_pids: Vec<u32> = Vec::new();
    for process in &signals.top_processes {
        if !orphan_candidate(process, policy, now) {
            continue;
        }
        severity = severity.max(Verdict::Warn);
        reasons.push(format!(
            "orphan candidate pid {} {} ({} MiB, age {}s)",
            process.pid,
            process.comm,
            process.rss_mib,
            now.saturating_sub(process.start_epoch)
        ));
        if policy.protected_comms.contains(&process.comm) {
            suppressed.push(format!("terminate {}: protected comm", process.comm));
            continue;
        }
        if process.pid <= 1 {
            suppressed.push(format!("terminate pid {}: refusing pid <= 1", process.pid));
            continue;
        }
        if !policy.kill_orphans {
            suppressed.push(format!(
                "terminate pid {}: kill_orphans disabled",
                process.pid
            ));
            continue;
        }
        kill_pids.push(process.pid);
    }
    kill_pids.sort_unstable();
    kill_pids.dedup();

    let mut defer_timers: Vec<String> = Vec::new();
    if pressure == Verdict::Critical {
        for timer in &policy.defer_units {
            if !validate_unit_name(timer) {
                suppressed.push(format!("defer {timer}: invalid unit name"));
                continue;
            }
            if state.deferred_timers.contains_key(timer) {
                suppressed.push(format!("defer {timer}: already deferred"));
                continue;
            }
            reasons.push(format!("critical pressure: defer {timer}"));
            defer_timers.push(timer.clone());
        }
    }

    let mut resume_timers: Vec<String> = Vec::new();
    if !state.deferred_timers.is_empty() {
        if severity == Verdict::Ok && state.calm_runs >= policy.calm_runs_to_resume {
            for timer in state.deferred_timers.keys() {
                reasons.push(format!(
                    "recovery: resume {timer} after {} calm runs",
                    state.calm_runs
                ));
                resume_timers.push(timer.clone());
            }
        } else if severity == Verdict::Ok {
            suppressed.push(format!(
                "timers deferred; {} of {} calm runs",
                state.calm_runs, policy.calm_runs_to_resume
            ));
        } else {
            suppressed.push(format!(
                "timers deferred; host severity {}",
                severity.as_str()
            ));
        }
    }

    for unit in stop_units {
        planned.push(Action::StopUnit { unit });
    }
    for unit in defer_timers {
        planned.push(Action::DeferTimer { unit });
    }
    for pid in kill_pids {
        planned.push(Action::TerminateProcess { pid });
    }
    for unit in resume_timers {
        planned.push(Action::ResumeTimer { unit });
    }

    let mut plan = Plan {
        severity,
        reasons,
        actions: planned,
        suppressed,
    };
    let digest_value = digest(signals, &plan);
    if state.last_digest.as_deref() == Some(digest_value.as_str()) {
        plan.suppressed.push(format!(
            "board post suppressed: digest {digest_value} unchanged"
        ));
    } else {
        let summary = summary_line(&plan);
        plan.actions.push(Action::PostBoard {
            digest: digest_value,
            severity: plan.severity,
            summary,
        });
    }
    plan
}

/// Stable content digest for board-post dedupe: severity + observed units +
/// planned mutations (the board action itself is excluded).
pub fn digest(signals: &HostSignals, plan: &Plan) -> String {
    let mut hasher = Sha256::new();
    hasher.update(plan.severity.as_str().as_bytes());

    let mut crash_units: Vec<&str> = signals
        .crash_loop_units
        .iter()
        .map(|unit| unit.unit.as_str())
        .collect();
    crash_units.sort_unstable();
    crash_units.dedup();
    for unit in crash_units {
        hasher.update(b"|crash:");
        hasher.update(unit.as_bytes());
    }

    let mut failed_units: Vec<&str> = signals
        .failed_loop_units
        .iter()
        .map(|unit| unit.unit.as_str())
        .collect();
    failed_units.sort_unstable();
    failed_units.dedup();
    for unit in failed_units {
        hasher.update(b"|failed:");
        hasher.update(unit.as_bytes());
    }

    for action in &plan.actions {
        if matches!(action, Action::PostBoard { .. }) {
            continue;
        }
        hasher.update(b"|action:");
        hasher.update(serde_json::to_string(action).unwrap_or_default().as_bytes());
    }
    hasher
        .finalize()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

/// Human-readable plan lines.
pub fn render(signals: &HostSignals, plan: &Plan) -> Vec<String> {
    let mut lines = Vec::new();
    lines.push(format!("Host guard: {}", plan.severity.as_str()));
    for reason in &plan.reasons {
        lines.push(format!("  [signal] {reason}"));
    }
    for note in &plan.suppressed {
        lines.push(format!("  [suppressed] {note}"));
    }
    for action in &plan.actions {
        lines.push(format!("  [action] {}", action.label()));
    }
    lines.push(format!("  digest {}", digest(signals, plan)));
    lines
}

/// Execute a plan through the runner. Non-fatal: failures are reported, not
/// propagated. `dry_run` performs the same gating reads but runs nothing and
/// consumes no breaker/unit/state budget.
pub fn execute(
    plan: &Plan,
    state: &mut HostGuardState,
    runner: &dyn CommandRunner,
    now: u64,
    dry_run: bool,
) -> ExecutionReport {
    let mut report = ExecutionReport {
        severity: plan.severity,
        dry_run,
        executed: Vec::new(),
        skipped: Vec::new(),
        failed: Vec::new(),
    };

    for action in &plan.actions {
        match action {
            Action::StopUnit { unit } => {
                if !validate_unit_name(unit) {
                    report
                        .skipped
                        .push(format!("stop {unit}: invalid unit name"));
                    continue;
                }
                if unit_stops_in_window(state, unit, now) >= MAX_UNIT_STOPS_PER_DAY {
                    report.skipped.push(format!(
                        "stop {unit}: per-unit cap {MAX_UNIT_STOPS_PER_DAY}/24h"
                    ));
                    continue;
                }
                if !breaker_allows(state, now, dry_run) {
                    report
                        .skipped
                        .push(format!("stop {unit}: circuit breaker active"));
                    continue;
                }
                if dry_run {
                    report.executed.push(action.clone());
                    continue;
                }
                match runner.run("systemctl", &["--user", "stop", unit.as_str()]) {
                    Some(_) => {
                        record_remediation(state, now);
                        record_unit_stop(state, unit, now);
                        report.executed.push(action.clone());
                    }
                    None => {
                        record_failure(state, now);
                        report.failed.push(format!("stop {unit}: runner failed"));
                    }
                }
            }
            Action::DeferTimer { unit } => {
                if !validate_unit_name(unit) {
                    report
                        .skipped
                        .push(format!("defer {unit}: invalid unit name"));
                    continue;
                }
                if !breaker_allows(state, now, dry_run) {
                    report
                        .skipped
                        .push(format!("defer {unit}: circuit breaker active"));
                    continue;
                }
                if dry_run {
                    report.executed.push(action.clone());
                    continue;
                }
                match runner.run("systemctl", &["--user", "stop", unit.as_str()]) {
                    Some(_) => {
                        record_remediation(state, now);
                        state.deferred_timers.insert(unit.clone(), now);
                        report.executed.push(action.clone());
                    }
                    None => {
                        record_failure(state, now);
                        report.failed.push(format!("defer {unit}: runner failed"));
                    }
                }
            }
            Action::ResumeTimer { unit } => {
                if !validate_unit_name(unit) {
                    report
                        .skipped
                        .push(format!("resume {unit}: invalid unit name"));
                    continue;
                }
                if dry_run {
                    report.executed.push(action.clone());
                    continue;
                }
                match runner.run("systemctl", &["--user", "start", unit.as_str()]) {
                    Some(_) => {
                        state.deferred_timers.remove(unit);
                        report.executed.push(action.clone());
                    }
                    None => report.failed.push(format!("resume {unit}: runner failed")),
                }
            }
            Action::TerminateProcess { pid } => {
                if *pid <= 1 {
                    report
                        .skipped
                        .push(format!("terminate pid {pid}: refusing pid <= 1"));
                    continue;
                }
                if !breaker_allows(state, now, dry_run) {
                    report
                        .skipped
                        .push(format!("terminate pid {pid}: circuit breaker active"));
                    continue;
                }
                if dry_run {
                    report.executed.push(action.clone());
                    continue;
                }
                let pid_arg = pid.to_string();
                match runner.run("kill", &["-TERM", pid_arg.as_str()]) {
                    Some(_) => {
                        record_remediation(state, now);
                        report.executed.push(action.clone());
                    }
                    None => {
                        record_failure(state, now);
                        report
                            .failed
                            .push(format!("terminate pid {pid}: runner failed"));
                    }
                }
            }
            Action::PostBoard {
                digest,
                severity,
                summary,
            } => {
                if dry_run {
                    report.executed.push(action.clone());
                    continue;
                }
                let title = format!("[host-guard {}] {}", severity.as_str(), summary);
                let body = format!("{summary}\n\ndigest={digest}");
                match runner.run(
                    "sangha",
                    &[
                        "post",
                        "--title",
                        title.as_str(),
                        "--target",
                        BOARD_TARGET,
                        "--type",
                        "flag",
                        "--provenance",
                        "computed",
                        "--body",
                        body.as_str(),
                    ],
                ) {
                    Some(_) => {
                        state.last_post_at = Some(now);
                        state.last_digest = Some(digest.clone());
                        report.executed.push(action.clone());
                    }
                    None => report.failed.push("board post: runner failed".to_string()),
                }
            }
        }
    }

    if !dry_run {
        if plan.severity == Verdict::Ok && report.failed.is_empty() {
            state.calm_runs = state.calm_runs.saturating_add(1);
        } else {
            state.calm_runs = 0;
        }
    }

    report
}

fn pressure_verdict(signals: &HostSignals, policy: &Policy, reasons: &mut Vec<String>) -> Verdict {
    let mut verdict = Verdict::Ok;

    if signals.mem_total_kib > 0 {
        let fraction = signals.mem_available_fraction;
        let detail = format!(
            "memory {:.1}% available ({:.1} GiB)",
            fraction * 100.0,
            signals.mem_available_kib as f64 / 1024.0 / 1024.0
        );
        if fraction < policy.mem_available_crit_fraction
            || signals.mem_available_kib < policy.mem_available_crit_kib
        {
            verdict = verdict.max(Verdict::Critical);
            reasons.push(format!("{detail}: critical"));
        } else if fraction < policy.mem_available_warn_fraction {
            verdict = verdict.max(Verdict::Warn);
            reasons.push(format!("{detail}: warning"));
        }
    }

    let psi_worst = match (signals.psi_memory_full_avg10, signals.psi_io_full_avg10) {
        (None, None) => None,
        (memory, io) => Some(memory.unwrap_or(0.0).max(io.unwrap_or(0.0))),
    };
    if let Some(worst) = psi_worst {
        if worst >= policy.psi_crit_avg10 {
            verdict = verdict.max(Verdict::Critical);
            reasons.push(format!("pressure stall full avg10 {worst:.1}%: critical"));
        } else if worst >= policy.psi_warn_avg10 {
            verdict = verdict.max(Verdict::Warn);
            reasons.push(format!("pressure stall full avg10 {worst:.1}%: warning"));
        }
    }

    if signals.swap_total_kib > 0 {
        let fraction = signals.swap_used_fraction;
        let kind = if signals.swap_is_zram {
            "zram swap"
        } else {
            "swap"
        };
        if fraction >= policy.swap_crit_fraction {
            verdict = verdict.max(Verdict::Critical);
            reasons.push(format!("{kind} {:.0}% used: critical", fraction * 100.0));
        } else if fraction >= policy.swap_warn_fraction {
            verdict = verdict.max(Verdict::Warn);
            reasons.push(format!("{kind} {:.0}% used: warning", fraction * 100.0));
        }
    }

    if let Some(free_gib) = signals.disk_free_gib {
        let pct = signals.disk_used_pct;
        let detail = match pct {
            Some(value) => format!("/ free {free_gib:.1} GiB ({value:.0}% used)"),
            None => format!("/ free {free_gib:.1} GiB"),
        };
        let pct_critical = pct.is_some_and(|value| value >= policy.disk_crit_pct);
        let pct_warning = pct.is_some_and(|value| value >= policy.disk_warn_pct);
        if free_gib < policy.disk_crit_gib || pct_critical {
            verdict = verdict.max(Verdict::Critical);
            reasons.push(format!("{detail}: critical"));
        } else if free_gib < policy.disk_warn_gib || pct_warning {
            verdict = verdict.max(Verdict::Warn);
            reasons.push(format!("{detail}: warning"));
        }
    }

    verdict
}

/// Orphan inference targets: heavy (>= 1 GiB RSS), old (>= 600 s), and either
/// a known local-inference server (`llama-server`, `ollama`) or a `python3`
/// process whose cmdline matches lane/eval/bench. The signal-level
/// `is_orphan` flag is advisory context; this inference is what the guard acts
/// on, and only when `kill_orphans` is enabled.
fn orphan_candidate(process: &ProcessInfo, policy: &Policy, now: u64) -> bool {
    if process.rss_mib < policy.orphan_rss_mib {
        return false;
    }
    if now.saturating_sub(process.start_epoch) < policy.orphan_min_age_secs {
        return false;
    }
    if policy.orphan_comms.contains(&process.comm) {
        return true;
    }
    process.comm == "python3" && cmdline_matches_inference(&process.cmdline, policy)
}

fn cmdline_matches_inference(cmdline: &str, policy: &Policy) -> bool {
    let lowered = cmdline.to_lowercase();
    policy
        .orphan_python_markers
        .iter()
        .any(|marker| lowered.contains(&marker.to_lowercase()))
}

fn summary_line(plan: &Plan) -> String {
    if plan.reasons.is_empty() {
        return format!("host {}: no anomalies", plan.severity.as_str());
    }
    let joined = plan.reasons.join("; ");
    let truncated: String = joined.chars().take(400).collect();
    format!("host {}: {}", plan.severity.as_str(), truncated)
}

fn breaker_allows(state: &mut HostGuardState, now: u64, dry_run: bool) -> bool {
    if dry_run {
        state.breaker.clone().can_remediate(now)
    } else {
        state.breaker.can_remediate(now)
    }
}

fn record_remediation(state: &mut HostGuardState, now: u64) {
    state.breaker.record_action(now);
    state.breaker.record_success();
}

fn record_failure(state: &mut HostGuardState, now: u64) {
    state.breaker.record_failure(now);
}

fn record_unit_stop(state: &mut HostGuardState, unit: &str, now: u64) {
    let stops = state.unit_stops.entry(unit.to_string()).or_default();
    stops.retain(|stamp| now.saturating_sub(*stamp) < DAY_SECS);
    stops.push(now);
}

fn unit_stops_in_window(state: &HostGuardState, unit: &str, now: u64) -> usize {
    state
        .unit_stops
        .get(unit)
        .map(|stamps| {
            stamps
                .iter()
                .filter(|stamp| now.saturating_sub(**stamp) < DAY_SECS)
                .count()
        })
        .unwrap_or(0)
}

fn unix_now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::host_health::CrashLoopUnit;
    use std::cell::RefCell;

    const NOW: u64 = 1_800_000_000;

    #[derive(Default)]
    struct FakeRunner {
        calls: RefCell<Vec<(String, Vec<String>)>>,
        fail_all: bool,
    }

    impl FakeRunner {
        fn failing() -> Self {
            Self {
                calls: RefCell::new(Vec::new()),
                fail_all: true,
            }
        }

        fn calls(&self) -> Vec<(String, Vec<String>)> {
            self.calls.borrow().clone()
        }
    }

    impl CommandRunner for FakeRunner {
        fn run(&self, program: &str, args: &[&str]) -> Option<String> {
            self.calls.borrow_mut().push((
                program.to_string(),
                args.iter().map(|arg| arg.to_string()).collect(),
            ));
            if self.fail_all {
                None
            } else {
                Some(String::new())
            }
        }
    }

    fn healthy_signals() -> HostSignals {
        HostSignals {
            mem_total_kib: 16_000_000,
            mem_available_kib: 8_000_000,
            mem_available_fraction: 0.5,
            psi_memory_full_avg10: Some(0.2),
            psi_io_full_avg10: Some(0.1),
            swap_total_kib: 16_000_000,
            swap_used_kib: 1_000_000,
            swap_used_fraction: 0.0625,
            swap_is_zram: true,
            disk_free_gib: Some(100.0),
            disk_used_pct: Some(50.0),
            crash_loop_units: Vec::new(),
            failed_loop_units: Vec::new(),
            top_processes: Vec::new(),
            unit_probe_ok: true,
        }
    }

    fn crash_unit(unit: &str, n_restarts: u64) -> CrashLoopUnit {
        CrashLoopUnit {
            unit: unit.to_string(),
            active_state: "activating".to_string(),
            sub_state: "auto-restart".to_string(),
            n_restarts,
            load_state: "loaded".to_string(),
            fragment_path: format!("/home/u/.config/systemd/user/{unit}"),
        }
    }

    fn failed_unit(unit: &str, n_restarts: u64) -> CrashLoopUnit {
        CrashLoopUnit {
            unit: unit.to_string(),
            active_state: "failed".to_string(),
            sub_state: "failed".to_string(),
            n_restarts,
            load_state: "loaded".to_string(),
            fragment_path: format!("/home/u/.config/systemd/user/{unit}"),
        }
    }

    fn process(pid: u32, comm: &str, rss_mib: u64, age_secs: u64, cmdline: &str) -> ProcessInfo {
        ProcessInfo {
            pid,
            ppid: 1,
            comm: comm.to_string(),
            cmdline: cmdline.to_string(),
            rss_mib,
            exe: String::new(),
            cgroup_unit: "app-gnome-x.scope".to_string(),
            start_epoch: NOW.saturating_sub(age_secs),
            is_orphan: true,
        }
    }

    fn action_pids(plan: &Plan) -> Vec<u32> {
        plan.actions
            .iter()
            .filter_map(|action| match action {
                Action::TerminateProcess { pid } => Some(*pid),
                _ => None,
            })
            .collect()
    }

    fn action_units<'a>(plan: &'a Plan, pick: fn(&Action) -> Option<&str>) -> Vec<&'a str> {
        plan.actions.iter().filter_map(pick).collect()
    }

    #[test]
    fn nominal_plan_reports_only() {
        let plan = plan_at(
            &healthy_signals(),
            &HostGuardState::default(),
            &Policy::default(),
            NOW,
        );
        assert_eq!(plan.severity, Verdict::Ok);
        assert!(plan.reasons.is_empty());
        assert_eq!(plan.actions.len(), 1);
        assert!(matches!(plan.actions[0], Action::PostBoard { .. }));
    }

    #[test]
    fn late_pressure_warns_without_mutation() {
        let mut signals = healthy_signals();
        signals.mem_available_fraction = 0.10;
        signals.mem_available_kib = 1_600_000;
        let plan = plan_at(
            &signals,
            &HostGuardState::default(),
            &Policy::default(),
            NOW,
        );
        assert_eq!(plan.severity, Verdict::Warn);
        assert!(plan.reasons.iter().any(|reason| reason.contains("memory")));
        assert!(!plan.actions.iter().any(|action| matches!(
            action,
            Action::StopUnit { .. } | Action::DeferTimer { .. } | Action::TerminateProcess { .. }
        )));
    }

    #[test]
    fn psi_warning_row_warns_only() {
        let mut signals = healthy_signals();
        signals.psi_memory_full_avg10 = Some(15.0);
        let plan = plan_at(
            &signals,
            &HostGuardState::default(),
            &Policy::default(),
            NOW,
        );
        assert_eq!(plan.severity, Verdict::Warn);
        assert!(
            plan.reasons
                .iter()
                .any(|reason| reason.contains("pressure stall"))
        );
        assert!(!plan.actions.iter().any(|action| matches!(
            action,
            Action::StopUnit { .. } | Action::DeferTimer { .. } | Action::TerminateProcess { .. }
        )));
    }

    #[test]
    fn critical_pressure_defers_sync_timers_once() {
        let mut signals = healthy_signals();
        signals.mem_available_fraction = 0.03;
        signals.mem_available_kib = 400_000;
        let policy = Policy::default();
        let plan = plan_at(&signals, &HostGuardState::default(), &policy, NOW);
        assert_eq!(plan.severity, Verdict::Critical);
        let defers = action_units(&plan, |action| match action {
            Action::DeferTimer { unit } => Some(unit.as_str()),
            _ => None,
        });
        assert_eq!(defers, vec!["fleet-sync.timer", "fleet-sync-full.timer"]);

        let mut state = HostGuardState::default();
        let runner = FakeRunner::default();
        let report = execute(&plan, &mut state, &runner, NOW, false);
        assert!(report.failed.is_empty());
        let calls = runner.calls();
        assert_eq!(
            calls[0],
            (
                "systemctl".to_string(),
                vec![
                    "--user".to_string(),
                    "stop".to_string(),
                    "fleet-sync.timer".to_string()
                ]
            )
        );
        assert_eq!(
            calls[1],
            (
                "systemctl".to_string(),
                vec![
                    "--user".to_string(),
                    "stop".to_string(),
                    "fleet-sync-full.timer".to_string()
                ]
            )
        );
        assert_eq!(calls[2].0, "sangha");
        assert_eq!(calls[2].1[0], "post");
        assert_eq!(state.deferred_timers.len(), 2);

        let second = plan_at(&signals, &state, &policy, NOW + 60);
        assert!(
            !second
                .actions
                .iter()
                .any(|action| matches!(action, Action::DeferTimer { .. }))
        );
        assert!(
            second
                .suppressed
                .iter()
                .any(|note| note.contains("already deferred"))
        );
    }

    #[test]
    fn crash_loop_gating_requires_twenty_restarts() {
        let mut signals = healthy_signals();
        signals.crash_loop_units = vec![
            crash_unit("edge-galaxy.service", 5),
            crash_unit("wm-chatd.service", 6534),
        ];
        let plan = plan_at(
            &signals,
            &HostGuardState::default(),
            &Policy::default(),
            NOW,
        );
        assert_eq!(plan.severity, Verdict::Critical);
        assert_eq!(
            action_units(&plan, |action| match action {
                Action::StopUnit { unit } => Some(unit.as_str()),
                _ => None,
            }),
            vec!["wm-chatd.service"]
        );
        assert!(
            plan.suppressed.iter().any(
                |note| note.contains("edge-galaxy.service") && note.contains("below threshold")
            )
        );
    }

    #[test]
    fn failed_units_are_never_stopped() {
        let mut signals = healthy_signals();
        signals.failed_loop_units = vec![failed_unit("aether-server.service", 6534)];
        let plan = plan_at(
            &signals,
            &HostGuardState::default(),
            &Policy::default(),
            NOW,
        );
        assert_eq!(plan.severity, Verdict::Warn);
        assert!(
            !plan
                .actions
                .iter()
                .any(|action| matches!(action, Action::StopUnit { .. }))
        );
        assert!(
            plan.reasons
                .iter()
                .any(|reason| reason.contains("aether-server.service") && reason.contains("failed"))
        );
    }

    #[test]
    fn protected_units_and_processes_denied() {
        let mut signals = healthy_signals();
        signals.crash_loop_units = vec![
            crash_unit("syncthing.service", 500),
            crash_unit("gnome-shell.service", 500),
        ];
        signals.top_processes = vec![process(
            777,
            "chrome",
            4096,
            7200,
            "/usr/bin/chrome --type=renderer",
        )];
        let mut policy = Policy::default();
        policy.kill_orphans = true;
        let plan = plan_at(&signals, &HostGuardState::default(), &policy, NOW);
        assert!(!plan.actions.iter().any(|action| matches!(
            action,
            Action::StopUnit { .. } | Action::TerminateProcess { .. }
        )));
        assert!(
            plan.suppressed
                .iter()
                .any(|note| note.contains("syncthing.service"))
        );
    }

    #[test]
    fn orphan_inference_server_selected_and_chrome_never() {
        let mut signals = healthy_signals();
        signals.top_processes = vec![
            process(4242, "llama-server", 2761, 3600, "llama-server --port 8080"),
            process(777, "chrome", 4096, 7200, "/usr/bin/chrome --type=renderer"),
            process(
                888,
                "python3",
                2048,
                1000,
                "python3 scripts/lane_eval_bench.py",
            ),
            process(999, "python3", 2048, 1000, "python3 app.py"),
            process(111, "ollama", 100, 7200, "ollama serve"),
        ];
        let mut policy = Policy::default();
        policy.kill_orphans = true;
        let plan = plan_at(&signals, &HostGuardState::default(), &policy, NOW);
        assert_eq!(plan.severity, Verdict::Warn);
        assert_eq!(action_pids(&plan), vec![888, 4242]);

        let mut state = HostGuardState::default();
        let runner = FakeRunner::default();
        let report = execute(&plan, &mut state, &runner, NOW, false);
        assert!(report.failed.is_empty());
        let calls = runner.calls();
        assert_eq!(
            calls[0],
            (
                "kill".to_string(),
                vec!["-TERM".to_string(), "888".to_string()]
            )
        );
        assert_eq!(
            calls[1],
            (
                "kill".to_string(),
                vec!["-TERM".to_string(), "4242".to_string()]
            )
        );
    }

    #[test]
    fn report_only_when_kill_orphans_disabled() {
        let mut signals = healthy_signals();
        signals.top_processes = vec![process(4242, "llama-server", 2761, 3600, "llama-server")];
        let plan = plan_at(
            &signals,
            &HostGuardState::default(),
            &Policy::default(),
            NOW,
        );
        assert_eq!(plan.severity, Verdict::Warn);
        assert!(action_pids(&plan).is_empty());
        assert!(
            plan.suppressed
                .iter()
                .any(|note| note.contains("kill_orphans disabled"))
        );
    }

    #[test]
    fn recovery_resumes_timers_after_two_calm_runs() {
        let mut state = HostGuardState::default();
        state.calm_runs = 2;
        state
            .deferred_timers
            .insert("fleet-sync.timer".to_string(), NOW - 3600);
        let plan = plan_at(&healthy_signals(), &state, &Policy::default(), NOW);
        assert_eq!(
            action_units(&plan, |action| match action {
                Action::ResumeTimer { unit } => Some(unit.as_str()),
                _ => None,
            }),
            vec!["fleet-sync.timer"]
        );
        let runner = FakeRunner::default();
        let report = execute(&plan, &mut state, &runner, NOW, false);
        assert!(report.failed.is_empty());
        assert_eq!(
            runner.calls()[0],
            (
                "systemctl".to_string(),
                vec![
                    "--user".to_string(),
                    "start".to_string(),
                    "fleet-sync.timer".to_string()
                ]
            )
        );
        assert!(state.deferred_timers.is_empty());
        assert_eq!(state.calm_runs, 3);

        let mut early = HostGuardState::default();
        early.calm_runs = 1;
        early
            .deferred_timers
            .insert("fleet-sync.timer".to_string(), NOW - 60);
        let plan = plan_at(&healthy_signals(), &early, &Policy::default(), NOW);
        assert!(
            !plan
                .actions
                .iter()
                .any(|action| matches!(action, Action::ResumeTimer { .. }))
        );
        assert!(
            plan.suppressed
                .iter()
                .any(|note| note.contains("calm runs"))
        );
    }

    #[test]
    fn breaker_caps_mutations_per_hour() {
        let mut signals = healthy_signals();
        signals.crash_loop_units = vec![
            crash_unit("a.service", 100),
            crash_unit("b.service", 100),
            crash_unit("c.service", 100),
        ];
        let plan = plan_at(
            &signals,
            &HostGuardState::default(),
            &Policy::default(),
            NOW,
        );
        assert_eq!(
            plan.actions
                .iter()
                .filter(|action| matches!(action, Action::StopUnit { .. }))
                .count(),
            3
        );

        let mut state = HostGuardState::default();
        let runner = FakeRunner::default();
        let report = execute(&plan, &mut state, &runner, NOW, false);
        let executed_stops = report
            .executed
            .iter()
            .filter(|action| matches!(action, Action::StopUnit { .. }))
            .count();
        assert_eq!(executed_stops, 2);
        assert!(
            report
                .skipped
                .iter()
                .any(|note| note.contains("circuit breaker"))
        );
        assert!(state.breaker.is_tripped);
    }

    #[test]
    fn per_unit_stop_cap_blocks_third_stop() {
        let mut signals = healthy_signals();
        signals.crash_loop_units = vec![crash_unit("a.service", 100)];
        let plan = plan_at(
            &signals,
            &HostGuardState::default(),
            &Policy::default(),
            NOW,
        );
        let mut state = HostGuardState::default();
        state
            .unit_stops
            .insert("a.service".to_string(), vec![NOW - 60, NOW - 120]);
        let runner = FakeRunner::default();
        let report = execute(&plan, &mut state, &runner, NOW, false);
        assert!(
            !report
                .executed
                .iter()
                .any(|action| matches!(action, Action::StopUnit { .. }))
        );
        assert!(
            report
                .skipped
                .iter()
                .any(|note| note.contains("per-unit cap"))
        );
    }

    #[test]
    fn dry_run_consumes_nothing() {
        let mut signals = healthy_signals();
        signals.crash_loop_units = vec![crash_unit("a.service", 100)];
        let plan = plan_at(
            &signals,
            &HostGuardState::default(),
            &Policy::default(),
            NOW,
        );
        let mut state = HostGuardState::default();
        state.calm_runs = 5;
        let before = state.to_json();
        let runner = FakeRunner::default();
        let report = execute(&plan, &mut state, &runner, NOW, true);
        assert!(report.dry_run);
        assert!(runner.calls().is_empty());
        assert_eq!(state.to_json(), before);
        assert!(
            report
                .executed
                .iter()
                .any(|action| matches!(action, Action::StopUnit { .. }))
        );
    }

    #[test]
    fn failing_runner_records_breaker_failure() {
        let mut signals = healthy_signals();
        signals.crash_loop_units = vec![crash_unit("a.service", 100)];
        let plan = plan_at(
            &signals,
            &HostGuardState::default(),
            &Policy::default(),
            NOW,
        );
        let mut state = HostGuardState::default();
        let runner = FakeRunner::failing();
        let report = execute(&plan, &mut state, &runner, NOW, false);
        assert!(!report.failed.is_empty());
        assert_eq!(state.breaker.consecutive_failures, 1);
    }

    #[test]
    fn state_roundtrip_and_corrupt_defaults() {
        let mut state = HostGuardState::default();
        state.calm_runs = 3;
        state.last_digest = Some("abc".to_string());
        state.last_post_at = Some(NOW);
        state
            .unit_stops
            .insert("a.service".to_string(), vec![NOW - 10, NOW - 20]);
        state
            .deferred_timers
            .insert("fleet-sync.timer".to_string(), NOW - 30);
        state.breaker.record_action(NOW - 40);

        let restored = HostGuardState::from_json_or_default(&state.to_json());
        assert_eq!(restored.calm_runs, 3);
        assert_eq!(restored.last_digest.as_deref(), Some("abc"));
        assert_eq!(restored.last_post_at, Some(NOW));
        assert_eq!(restored.unit_stops["a.service"].len(), 2);
        assert_eq!(restored.deferred_timers.len(), 1);
        assert_eq!(restored.breaker.remediation_history.len(), 1);

        let corrupt = HostGuardState::from_json_or_default("{not json");
        assert_eq!(corrupt.calm_runs, 0);
        assert_eq!(corrupt.schema_version, SCHEMA_VERSION);

        let wrong_version = HostGuardState::from_json_or_default(r#"{"schema_version": 99}"#);
        assert_eq!(wrong_version.schema_version, SCHEMA_VERSION);
        assert!(wrong_version.unit_stops.is_empty());

        let sparse = HostGuardState::from_json_or_default(r#"{"schema_version": 1}"#);
        assert_eq!(
            sparse.breaker.max_remediations_per_hour,
            MAX_MUTATIONS_PER_HOUR
        );
        assert!(sparse.last_digest.is_none());
    }

    #[test]
    fn digest_is_stable_and_dedupes_board_posts() {
        let signals = healthy_signals();
        let policy = Policy::default();
        let state = HostGuardState::default();
        let plan = plan_at(&signals, &state, &policy, NOW);
        let first = digest(&signals, &plan);
        let same = plan_at(&signals, &state, &policy, NOW);
        assert_eq!(digest(&signals, &same), first);

        let mut posted = HostGuardState::default();
        posted.last_digest = Some(first.clone());
        let deduped = plan_at(&signals, &posted, &policy, NOW);
        assert!(
            !deduped
                .actions
                .iter()
                .any(|action| matches!(action, Action::PostBoard { .. }))
        );
        assert!(
            deduped
                .suppressed
                .iter()
                .any(|note| note.contains("digest"))
        );

        let mut sick = healthy_signals();
        sick.mem_available_fraction = 0.03;
        sick.mem_available_kib = 100_000;
        let sick_plan = plan_at(&sick, &state, &policy, NOW);
        assert_ne!(digest(&sick, &sick_plan), first);
    }

    #[test]
    fn unit_validation_matches_systemd_shape() {
        assert!(validate_unit_name("fleet-sync.timer"));
        assert!(validate_unit_name("wm-serve@1000.service"));
        assert!(!validate_unit_name("fleet-sync.timer; rm -rf /"));
        assert!(!validate_unit_name(".service"));
        assert!(!validate_unit_name("edge-galaxy.socket"));
        assert!(!validate_unit_name(""));
    }

    #[test]
    fn protected_patterns_match_prefix_wildcards() {
        let policy = Policy::default();
        assert!(unit_is_protected(
            "wm-serve@1000.service",
            &policy.protected_units
        ));
        assert!(unit_is_protected(
            "syncthing.service",
            &policy.protected_units
        ));
        assert!(unit_is_protected("dbus.socket", &policy.protected_units));
        assert!(!unit_is_protected(
            "edge-galaxy.service",
            &policy.protected_units
        ));
    }

    #[test]
    fn render_includes_reasons_actions_and_digest() {
        let mut signals = healthy_signals();
        signals.crash_loop_units = vec![crash_unit("a.service", 100)];
        let plan = plan_at(
            &signals,
            &HostGuardState::default(),
            &Policy::default(),
            NOW,
        );
        let rendered = render(&signals, &plan).join("\n");
        assert!(rendered.contains("Host guard: critical"));
        assert!(rendered.contains("[action] stop unit a.service"));
        assert!(rendered.contains("digest "));
    }
}
