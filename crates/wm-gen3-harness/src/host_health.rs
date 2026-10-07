//! Host-health diagnostics for `wm selftest` (Linux, best-effort).
//!
//! The 2026-10-06 incident: three systemd user units crash-looped ~6.5k times
//! each, agent sessions left 2.7 GiB local-inference servers and a desktop
//! app resident, and the host thrashed on zram swap — while `wm selftest`
//! happily reported `{"status":"ok"}` because it never looked at the host.
//! This module makes the environment diagnostic honest: disk headroom,
//! available memory, kernel pressure-stall, swap/zram saturation,
//! crash-looping user units, and the top memory consumers.
//!
//! Design rules:
//! - never fail the install-invariant contract (`status` stays `ok`); the host
//!   verdict rides separately as `host_status`;
//! - every probe is best-effort — a missing `/proc/pressure` or `systemctl`
//!   degrades to no check, never to an error;
//! - parsers take `&str` so the grading logic is unit-testable without a host;
//! - [`collect_signals`] exposes the same probes as structured data for the
//!   host-guard policy engine; [`collect`] derives its checks from those
//!   signals, so the `wm selftest` JSON/human output is byte-compatible with
//!   the pre-signal implementation for healthy hosts.

use std::collections::BTreeSet;

use serde::Serialize;

const DISK_WARN_GIB: f64 = 20.0;
const DISK_CRIT_GIB: f64 = 5.0;
const MEM_WARN_FRACTION: f64 = 0.15;
const MEM_CRIT_FRACTION: f64 = 0.05;
const PSI_WARN_AVG10: f64 = 10.0;
const PSI_CRIT_AVG10: f64 = 30.0;
const SWAP_WARN_FRACTION: f64 = 0.60;
const SWAP_CRIT_FRACTION: f64 = 0.85;
const TOP_PROCESSES: usize = 5;

/// Percentage-used disk thresholds exposed for the host-guard policy. The
/// selftest verdicts remain driven by the free-GiB thresholds above, so the
/// `wm selftest` contract does not change.
pub const DISK_PCT_WARN: f64 = 90.0;
pub const DISK_PCT_CRIT: f64 = 95.0;

/// Processes inspected per signal collection (top-N by RSS); `collect()` still
/// renders only `TOP_PROCESSES` for byte-compatible selftest output.
const SIGNAL_PROCESS_LIMIT: usize = 16;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Verdict {
    Ok,
    Warn,
    Critical,
}

impl Verdict {
    fn label(self) -> &'static str {
        match self {
            Verdict::Ok => "[OK]  ",
            Verdict::Warn => "[WARN]",
            Verdict::Critical => "[CRIT]",
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct Check {
    pub name: String,
    pub verdict: Verdict,
    pub detail: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub hint: Option<String>,
}

impl Check {
    fn new(name: &str, verdict: Verdict, detail: String, hint: Option<String>) -> Self {
        Self {
            name: name.to_string(),
            verdict,
            detail,
            hint,
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct ProcessMemory {
    pub pid: u32,
    pub name: String,
    pub rss_mib: u64,
}

/// A systemd user unit observed in a non-healthy state.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct CrashLoopUnit {
    pub unit: String,
    pub active_state: String,
    pub sub_state: String,
    pub n_restarts: u64,
    pub load_state: String,
    pub fragment_path: String,
}

/// A process sampled from `/proc`, enriched for orphan inference.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct ProcessInfo {
    pub pid: u32,
    pub ppid: u32,
    pub comm: String,
    pub cmdline: String,
    pub rss_mib: u64,
    pub exe: String,
    pub cgroup_unit: String,
    pub start_epoch: u64,
    pub is_orphan: bool,
}

/// Structured host signals consumed by `host_guard`.
#[derive(Debug, Clone, Default, Serialize)]
pub struct HostSignals {
    pub mem_total_kib: u64,
    pub mem_available_kib: u64,
    pub mem_available_fraction: f64,
    pub psi_memory_full_avg10: Option<f64>,
    pub psi_io_full_avg10: Option<f64>,
    pub swap_total_kib: u64,
    pub swap_used_kib: u64,
    pub swap_used_fraction: f64,
    pub swap_is_zram: bool,
    pub disk_free_gib: Option<f64>,
    pub disk_used_pct: Option<f64>,
    pub crash_loop_units: Vec<CrashLoopUnit>,
    pub failed_loop_units: Vec<CrashLoopUnit>,
    pub top_processes: Vec<ProcessInfo>,
    /// Runtime-only degradation state: false when the `systemctl` probe itself
    /// could not run (a missing systemctl contributes no crash-loop check).
    /// Deliberately not part of the serialized signal contract.
    #[serde(skip)]
    pub unit_probe_ok: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct HostHealth {
    pub status: Verdict,
    pub checks: Vec<Check>,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub top_memory_processes: Vec<ProcessMemory>,
}

impl HostHealth {
    fn from_checks(checks: Vec<Check>, top_memory_processes: Vec<ProcessMemory>) -> Self {
        let status = checks
            .iter()
            .map(|check| check.verdict)
            .max()
            .unwrap_or(Verdict::Ok);
        Self {
            status,
            checks,
            top_memory_processes,
        }
    }

    /// Human-readable lines for the `wm selftest` console report.
    pub fn render_lines(&self) -> Vec<String> {
        if self.checks.is_empty() {
            return Vec::new();
        }
        let mut lines = Vec::with_capacity(self.checks.len() + self.top_memory_processes.len() + 2);
        lines.push(format!("Host health: {}", self.status.as_str()));
        for check in &self.checks {
            lines.push(format!(
                "  {} {}: {}",
                check.verdict.label(),
                check.name,
                check.detail
            ));
            if let Some(hint) = &check.hint {
                lines.push(format!("         -> {hint}"));
            }
        }
        if !self.top_memory_processes.is_empty() {
            lines.push("Top memory processes:".to_string());
            for process in &self.top_memory_processes {
                lines.push(format!(
                    "  {:>6.1} MiB  {} (pid {})",
                    process.rss_mib as f64, process.name, process.pid
                ));
            }
        }
        lines
    }
}

impl Verdict {
    pub fn as_str(self) -> &'static str {
        match self {
            Verdict::Ok => "ok",
            Verdict::Warn => "warn",
            Verdict::Critical => "critical",
        }
    }
}

/// Collect host health. Every probe is best-effort; a probe that cannot run
/// simply contributes no check.
pub fn collect() -> HostHealth {
    health_from_signals(&collect_signals())
}

fn health_from_signals(signals: &HostSignals) -> HostHealth {
    let top_memory_processes = signals
        .top_processes
        .iter()
        .take(TOP_PROCESSES)
        .map(|process| ProcessMemory {
            pid: process.pid,
            name: process.comm.clone(),
            rss_mib: process.rss_mib,
        })
        .collect();
    HostHealth::from_checks(checks_from_signals(signals), top_memory_processes)
}

/// Derive the `wm selftest` checks from structured signals. Detail strings are
/// byte-compatible with the pre-signal probes for healthy hosts (disk capacity
/// is re-rendered from the parsed percentage, which `df -Pk` prints as an
/// integer).
fn checks_from_signals(signals: &HostSignals) -> Vec<Check> {
    let mut checks = Vec::new();
    if let Some(check) = memory_check_values(signals.mem_total_kib, signals.mem_available_kib) {
        checks.push(check);
    }
    if let Some(check) =
        pressure_check_values(signals.psi_memory_full_avg10, signals.psi_io_full_avg10)
    {
        checks.push(check);
    }
    if let Some(check) = swap_check_values(
        signals.swap_total_kib,
        signals.swap_used_kib,
        signals.swap_is_zram,
    ) {
        checks.push(check);
    }
    if let Some(free_gib) = signals.disk_free_gib {
        checks.push(disk_check_values(free_gib, signals.disk_used_pct));
    }
    if signals.unit_probe_ok {
        checks.push(crash_loop_check_values(&signals.crash_loop_units));
    }
    checks
}

/// Collect structured host signals. Probes are best-effort: a missing file or
/// command degrades to a neutral value (`None`/`0`) instead of an error.
pub fn collect_signals() -> HostSignals {
    #[cfg(target_os = "linux")]
    {
        collect_signals_linux()
    }
    #[cfg(not(target_os = "linux"))]
    {
        HostSignals::default()
    }
}

#[cfg(target_os = "linux")]
fn collect_signals_linux() -> HostSignals {
    use std::fs;

    let mut signals = HostSignals::default();

    if let Ok(meminfo) = fs::read_to_string("/proc/meminfo") {
        signals.mem_total_kib = parse_meminfo_value(&meminfo, "MemTotal:").unwrap_or(0);
        signals.mem_available_kib = parse_meminfo_value(&meminfo, "MemAvailable:").unwrap_or(0);
        if signals.mem_total_kib > 0 {
            signals.mem_available_fraction =
                signals.mem_available_kib as f64 / signals.mem_total_kib as f64;
        }
    }

    signals.psi_memory_full_avg10 = fs::read_to_string("/proc/pressure/memory")
        .ok()
        .and_then(|text| parse_psi_avg10(&text, "full"));
    signals.psi_io_full_avg10 = fs::read_to_string("/proc/pressure/io")
        .ok()
        .and_then(|text| parse_psi_avg10(&text, "full"));

    if let Ok(swaps) = fs::read_to_string("/proc/swaps") {
        let (total_kib, used_kib, is_zram) = parse_swaps(&swaps);
        signals.swap_total_kib = total_kib;
        signals.swap_used_kib = used_kib;
        signals.swap_is_zram = is_zram;
        if total_kib > 0 {
            signals.swap_used_fraction = used_kib as f64 / total_kib as f64;
        }
    }

    if let Some(df_output) = run_command("df", &["-Pk", "/"]) {
        if let Some((free_gib, used_pct)) = parse_df(&df_output) {
            signals.disk_free_gib = Some(free_gib);
            signals.disk_used_pct = used_pct;
        }
    }

    let (crash_loop_units, failed_loop_units, unit_probe_ok) = probe_user_units();
    signals.crash_loop_units = crash_loop_units;
    signals.failed_loop_units = failed_loop_units;
    signals.unit_probe_ok = unit_probe_ok;
    signals.top_processes = collect_processes(SIGNAL_PROCESS_LIMIT);

    signals
}

/// Inspect user units for crash loops. Candidates come from the activating
/// list (kept from the original probe) plus the failed list; `systemctl show`
/// is only invoked for those candidates.
#[cfg(target_os = "linux")]
fn probe_user_units() -> (Vec<CrashLoopUnit>, Vec<CrashLoopUnit>, bool) {
    let activating = run_command(
        "systemctl",
        &[
            "--user",
            "list-units",
            "--state=activating",
            "--no-legend",
            "--no-pager",
        ],
    );
    let failed = run_command(
        "systemctl",
        &[
            "--user",
            "list-units",
            "--state=failed",
            "--no-legend",
            "--no-pager",
        ],
    );
    if activating.is_none() && failed.is_none() {
        return (Vec::new(), Vec::new(), false);
    }

    let mut seen = BTreeSet::new();
    let mut candidates: Vec<(String, bool)> = Vec::new();
    if let Some(text) = &activating {
        for line in text.lines() {
            let Some(unit) = unit_token(line) else {
                continue;
            };
            if seen.insert(unit.clone()) {
                candidates.push((unit, line.contains("auto-restart")));
            }
        }
    }
    if let Some(text) = &failed {
        for line in text.lines() {
            let Some(unit) = unit_token(line) else {
                continue;
            };
            if seen.insert(unit.clone()) {
                candidates.push((unit, false));
            }
        }
    }

    let mut crash_loop_units = Vec::new();
    let mut failed_loop_units = Vec::new();
    for (unit, raw_auto_restart) in candidates {
        let show = run_command(
            "systemctl",
            &[
                "--user",
                "show",
                &unit,
                "-p",
                "ActiveState",
                "-p",
                "SubState",
                "-p",
                "NRestarts",
                "-p",
                "LoadState",
                "-p",
                "FragmentPath",
            ],
        );
        match show
            .as_deref()
            .and_then(|text| parse_systemctl_show(&unit, text))
        {
            Some(unit_info) if unit_info.active_state == "failed" => {
                failed_loop_units.push(unit_info);
            }
            Some(unit_info)
                if unit_info.active_state == "activating"
                    && unit_info.sub_state == "auto-restart" =>
            {
                crash_loop_units.push(unit_info);
            }
            Some(_) => {}
            None if raw_auto_restart => crash_loop_units.push(CrashLoopUnit {
                unit,
                active_state: "activating".to_string(),
                sub_state: "auto-restart".to_string(),
                n_restarts: 0,
                load_state: String::new(),
                fragment_path: String::new(),
            }),
            None => {}
        }
    }
    crash_loop_units.sort_by(|left, right| left.unit.cmp(&right.unit));
    failed_loop_units.sort_by(|left, right| left.unit.cmp(&right.unit));
    (crash_loop_units, failed_loop_units, true)
}

/// First whitespace token of a `list-units` row, when it is a service/timer.
fn unit_token(line: &str) -> Option<String> {
    let token = line.split_whitespace().next()?;
    if token.ends_with(".service") || token.ends_with(".timer") {
        Some(token.to_string())
    } else {
        None
    }
}

/// Parse `systemctl show <unit> -p ActiveState -p SubState -p NRestarts
/// -p LoadState -p FragmentPath` output. Returns `None` when `ActiveState` is
/// absent, which is the signal that the show probe did not really run.
pub fn parse_systemctl_show(unit: &str, text: &str) -> Option<CrashLoopUnit> {
    let mut active_state = None;
    let mut sub_state = String::new();
    let mut n_restarts = 0;
    let mut load_state = String::new();
    let mut fragment_path = String::new();
    for line in text.lines() {
        let Some((key, value)) = line.split_once('=') else {
            continue;
        };
        match key {
            "ActiveState" => active_state = Some(value.to_string()),
            "SubState" => sub_state = value.to_string(),
            "NRestarts" => n_restarts = value.parse().unwrap_or(0),
            "LoadState" => load_state = value.to_string(),
            "FragmentPath" => fragment_path = value.to_string(),
            _ => {}
        }
    }
    Some(CrashLoopUnit {
        unit: unit.to_string(),
        active_state: active_state?,
        sub_state,
        n_restarts,
        load_state,
        fragment_path,
    })
}

fn run_command(program: &str, args: &[&str]) -> Option<String> {
    let output = std::process::Command::new(program)
        .args(args)
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    String::from_utf8(output.stdout).ok()
}

fn memory_check_values(total_kib: u64, available_kib: u64) -> Option<Check> {
    if total_kib == 0 {
        return None;
    }
    let fraction = available_kib as f64 / total_kib as f64;
    let detail = format!(
        "{:.1} GiB available of {:.1} GiB ({:.0}%)",
        available_kib as f64 / 1024.0 / 1024.0,
        total_kib as f64 / 1024.0 / 1024.0,
        fraction * 100.0
    );
    if fraction < MEM_CRIT_FRACTION {
        return Some(Check::new(
            "memory",
            Verdict::Critical,
            detail,
            Some(
                "memory is nearly exhausted: stop local inference servers and heavy \
                 background apps before continuing"
                    .to_string(),
            ),
        ));
    }
    if fraction < MEM_WARN_FRACTION {
        return Some(Check::new(
            "memory",
            Verdict::Warn,
            detail,
            Some("close unused heavy apps (browsers, IDE renderers, local models)".to_string()),
        ));
    }
    Some(Check::new("memory", Verdict::Ok, detail, None))
}

fn parse_meminfo_value(meminfo: &str, key: &str) -> Option<u64> {
    meminfo.lines().find_map(|line| {
        let rest = line.strip_prefix(key)?;
        rest.split_whitespace().next()?.parse().ok()
    })
}

fn pressure_check_values(memory_full: Option<f64>, io_full: Option<f64>) -> Option<Check> {
    if memory_full.is_none() && io_full.is_none() {
        return None;
    }
    let memory_full = memory_full.unwrap_or(0.0);
    let io_full = io_full.unwrap_or(0.0);
    let worst = memory_full.max(io_full);
    let detail = format!(
        "stall avg10 — memory full {memory_full:.1}%, io full {io_full:.1}% \
         (share of time all tasks were blocked on reclaim/io)"
    );
    if worst >= PSI_CRIT_AVG10 {
        return Some(Check::new(
            "pressure",
            Verdict::Critical,
            detail,
            Some(
                "the host is actively stalling on memory reclaim/io: free memory now \
                 (stop background inference and crash-looping units); zram swap is a \
                 symptom, not a fix"
                    .to_string(),
            ),
        ));
    }
    if worst >= PSI_WARN_AVG10 {
        return Some(Check::new(
            "pressure",
            Verdict::Warn,
            detail,
            Some(
                "sustained memory pressure detected: reduce concurrent heavy jobs \
                 (local models, builds, browsers)"
                    .to_string(),
            ),
        ));
    }
    Some(Check::new("pressure", Verdict::Ok, detail, None))
}

fn parse_psi_avg10(text: &str, kind: &str) -> Option<f64> {
    let line = text.lines().find(|line| line.starts_with(kind))?;
    line.split_whitespace()
        .find_map(|token| token.strip_prefix("avg10=")?.parse().ok())
}

fn parse_swaps(swaps: &str) -> (u64, u64, bool) {
    let mut total_kib: u64 = 0;
    let mut used_kib: u64 = 0;
    let mut zram = false;
    for line in swaps.lines().skip(1) {
        let fields: Vec<&str> = line.split_whitespace().collect();
        if fields.len() < 4 {
            continue;
        }
        let size: u64 = fields[2].parse().unwrap_or(0);
        let used: u64 = fields[3].parse().unwrap_or(0);
        total_kib += size;
        used_kib += used;
        if fields[0].contains("zram") {
            zram = true;
        }
    }
    (total_kib, used_kib, zram)
}

fn swap_check_values(total_kib: u64, used_kib: u64, zram: bool) -> Option<Check> {
    if total_kib == 0 {
        return None;
    }
    let fraction = used_kib as f64 / total_kib as f64;
    let kind = if zram { "swap/zram" } else { "swap" };
    let detail = format!(
        "{:.1} GiB of {:.1} GiB used ({:.0}%){}",
        used_kib as f64 / 1024.0 / 1024.0,
        total_kib as f64 / 1024.0 / 1024.0,
        fraction * 100.0,
        if zram {
            " — zram pages live in RAM"
        } else {
            ""
        }
    );
    if fraction >= SWAP_CRIT_FRACTION {
        return Some(Check::new(
            kind,
            Verdict::Critical,
            detail,
            Some("swap is nearly full; resident working set no longer fits in RAM".to_string()),
        ));
    }
    if fraction >= SWAP_WARN_FRACTION {
        return Some(Check::new(
            kind,
            Verdict::Warn,
            detail,
            Some("large resident footprint; consider stopping unused background jobs".to_string()),
        ));
    }
    Some(Check::new(kind, Verdict::Ok, detail, None))
}

fn parse_df(df_output: &str) -> Option<(f64, Option<f64>)> {
    let line = df_output
        .lines()
        .skip(1)
        .find(|line| !line.trim().is_empty())?;
    let fields: Vec<&str> = line.split_whitespace().collect();
    if fields.len() < 5 {
        return None;
    }
    let available_kib: u64 = fields[3].parse().ok()?;
    let free_gib = available_kib as f64 / 1024.0 / 1024.0;
    let used_pct = fields[4]
        .strip_suffix('%')
        .and_then(|value| value.parse::<f64>().ok());
    Some((free_gib, used_pct))
}

fn disk_check_values(free_gib: f64, used_pct: Option<f64>) -> Check {
    let capacity = used_pct
        .map(|pct| format!("{pct:.0}%"))
        .unwrap_or_else(|| "?".to_string());
    let detail = format!("/: {free_gib:.1} GiB free ({capacity} used)");
    if free_gib < DISK_CRIT_GIB {
        return Check::new(
            "disk",
            Verdict::Critical,
            detail,
            Some(
                "disk is nearly full: prune build caches (scripts/prune_build_cache.sh), \
                 vacuum journals, and remove stale target/ trees"
                    .to_string(),
            ),
        );
    }
    if free_gib < DISK_WARN_GIB {
        return Check::new(
            "disk",
            Verdict::Warn,
            detail,
            Some("disk headroom below 20 GiB (the stop-and-clean threshold)".to_string()),
        );
    }
    Check::new("disk", Verdict::Ok, detail, None)
}

fn crash_loop_check_values(units: &[CrashLoopUnit]) -> Check {
    let mut looping: Vec<&str> = units
        .iter()
        .map(|unit| unit.unit.as_str())
        .filter(|unit| !unit.is_empty())
        .collect();
    looping.sort_unstable();
    looping.dedup();
    if looping.is_empty() {
        Check::new(
            "crash-loops",
            Verdict::Ok,
            "none detected".to_string(),
            None,
        )
    } else {
        Check::new(
            "crash-loops",
            Verdict::Critical,
            format!(
                "{} unit(s) stuck in auto-restart: {}",
                looping.len(),
                looping.join(", ")
            ),
            Some(
                "stop the looping unit(s): systemctl --user stop <unit>; then fix the \
                 unit or add StartLimitIntervalSec/StartLimitBurst"
                    .to_string(),
            ),
        )
    }
}

/// Join a `/proc/<pid>/cmdline` buffer: NUL separators become spaces.
pub fn parse_cmdline(bytes: &[u8]) -> String {
    let joined: Vec<u8> = bytes
        .iter()
        .map(|byte| if *byte == 0 { b' ' } else { *byte })
        .collect();
    String::from_utf8_lossy(&joined).trim_end().to_string()
}

/// Extract the last `.service`/`.scope` path component from a `/proc/<pid>/cgroup`
/// file (handles both the v2 single-line and v1 `name=systemd:` formats).
pub fn parse_cgroup_unit(cgroup: &str) -> String {
    for line in cgroup.lines().rev() {
        let path = line.rsplit_once(':').map(|(_, path)| path).unwrap_or(line);
        for component in path.rsplit('/') {
            if component.ends_with(".service") || component.ends_with(".scope") {
                return component.to_string();
            }
        }
    }
    String::new()
}

/// Read `PPid:` from a `/proc/<pid>/status` buffer.
pub fn parse_ppid(status: &str) -> Option<u32> {
    status
        .lines()
        .find_map(|line| line.strip_prefix("PPid:"))
        .and_then(|rest| rest.split_whitespace().next())
        .and_then(|value| value.parse().ok())
}

/// Orphan heuristic: a process reparented to init (`ppid == 1`) or one whose
/// cgroup still sits in a `session-*.scope`. When `KillUserProcesses=no`, a
/// login/agent session's processes are left behind in such a scope after the
/// session exits; the ppid check is the strong signal, the scope check is
/// advisory.
pub fn infer_orphan(ppid: u32, cgroup: &str) -> bool {
    ppid == 1 || cgroup_has_session_scope(cgroup)
}

fn cgroup_has_session_scope(cgroup: &str) -> bool {
    cgroup
        .split(|character| character == '/' || character == ':')
        .any(|component| component.starts_with("session-") && component.ends_with(".scope"))
}

#[cfg(target_os = "linux")]
fn collect_processes(limit: usize) -> Vec<ProcessInfo> {
    use std::fs;
    use std::time::UNIX_EPOCH;

    let mut processes = Vec::new();
    let Ok(entries) = fs::read_dir("/proc") else {
        return processes;
    };
    for entry in entries.flatten() {
        let name = entry.file_name();
        let Some(name) = name.to_str() else { continue };
        let Ok(pid) = name.parse::<u32>() else {
            continue;
        };
        let Ok(status) = fs::read_to_string(format!("/proc/{pid}/status")) else {
            continue;
        };
        let Some(comm) = status
            .lines()
            .find_map(|line| line.strip_prefix("Name:"))
            .map(str::trim)
        else {
            continue;
        };
        let Some(rss_kib) = status
            .lines()
            .find_map(|line| line.strip_prefix("VmRSS:"))
            .and_then(|rest| rest.split_whitespace().next())
            .and_then(|value| value.parse::<u64>().ok())
        else {
            continue;
        };
        // Start time comes from `/proc/<pid>` fs metadata (a stable "born at"
        // approximation for long-lived processes). No metadata: skip the entry.
        let Some(start_epoch) = fs::metadata(format!("/proc/{pid}"))
            .ok()
            .and_then(|metadata| metadata.modified().ok())
            .and_then(|modified| modified.duration_since(UNIX_EPOCH).ok())
            .map(|duration| duration.as_secs())
        else {
            continue;
        };
        let cmdline = fs::read(format!("/proc/{pid}/cmdline"))
            .ok()
            .map(|bytes| parse_cmdline(&bytes))
            .unwrap_or_default();
        let cgroup_text = fs::read_to_string(format!("/proc/{pid}/cgroup")).unwrap_or_default();
        let cgroup_unit = parse_cgroup_unit(&cgroup_text);
        let exe = fs::read_link(format!("/proc/{pid}/exe"))
            .ok()
            .map(|path| path.to_string_lossy().into_owned())
            .unwrap_or_default();
        let ppid = parse_ppid(&status).unwrap_or(0);
        processes.push(ProcessInfo {
            pid,
            ppid,
            comm: comm.to_string(),
            cmdline,
            rss_mib: rss_kib / 1024,
            exe,
            cgroup_unit,
            start_epoch,
            is_orphan: infer_orphan(ppid, &cgroup_text),
        });
    }
    processes.sort_by(|left, right| right.rss_mib.cmp(&left.rss_mib));
    processes.truncate(limit);
    processes
}

#[cfg(test)]
fn memory_check(meminfo: &str) -> Option<Check> {
    let total_kib = parse_meminfo_value(meminfo, "MemTotal:")?;
    let available_kib = parse_meminfo_value(meminfo, "MemAvailable:")?;
    memory_check_values(total_kib, available_kib)
}

#[cfg(test)]
fn pressure_check(memory: Option<&str>, io: Option<&str>) -> Option<Check> {
    let memory_full = memory.and_then(|text| parse_psi_avg10(text, "full"));
    let io_full = io.and_then(|text| parse_psi_avg10(text, "full"));
    pressure_check_values(memory_full, io_full)
}

#[cfg(test)]
fn swap_check(swaps: &str) -> Option<Check> {
    let (total_kib, used_kib, zram) = parse_swaps(swaps);
    swap_check_values(total_kib, used_kib, zram)
}

#[cfg(test)]
fn disk_check(df_output: &str) -> Option<Check> {
    let (free_gib, used_pct) = parse_df(df_output)?;
    Some(disk_check_values(free_gib, used_pct))
}

#[cfg(test)]
fn crash_loop_check(units_output: &str) -> Check {
    let units: Vec<CrashLoopUnit> = units_output
        .lines()
        .filter(|line| line.contains("auto-restart"))
        .filter_map(|line| {
            let unit = line.split_whitespace().next()?.to_string();
            Some(CrashLoopUnit {
                unit,
                active_state: "activating".to_string(),
                sub_state: "auto-restart".to_string(),
                n_restarts: 0,
                load_state: "loaded".to_string(),
                fragment_path: String::new(),
            })
        })
        .collect();
    crash_loop_check_values(&units)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn meminfo_grades_available_fraction() {
        let healthy = "MemTotal:       16000000 kB\nMemAvailable:   9000000 kB\n";
        assert_eq!(memory_check(healthy).unwrap().verdict, Verdict::Ok);

        let warn = "MemTotal:       16000000 kB\nMemAvailable:   1600000 kB\n";
        assert_eq!(memory_check(warn).unwrap().verdict, Verdict::Warn);

        let critical = "MemTotal:       16000000 kB\nMemAvailable:   500000 kB\n";
        assert_eq!(memory_check(critical).unwrap().verdict, Verdict::Critical);
    }

    #[test]
    fn psi_parses_full_avg10() {
        let text = "some avg10=4.40 avg60=6.79 avg300=22.39 total=1\nfull avg10=4.39 avg60=6.36 avg300=20.63 total=2\n";
        assert_eq!(parse_psi_avg10(text, "full"), Some(4.39));
        assert_eq!(parse_psi_avg10(text, "some"), Some(4.40));
    }

    #[test]
    fn pressure_worst_of_memory_and_io() {
        let calm = "some avg10=0.00 avg60=0.30 avg300=0.67 total=1\nfull avg10=0.28 avg60=0.28 avg300=0.63 total=2\n";
        let io_stalled = "some avg10=4.40 avg60=6.79 avg300=22.39 total=1\nfull avg10=32.28 avg60=37.70 avg300=31.98 total=2\n";
        assert_eq!(
            pressure_check(Some(calm), Some(io_stalled))
                .unwrap()
                .verdict,
            Verdict::Critical
        );
        assert_eq!(
            pressure_check(Some(calm), Some(calm)).unwrap().verdict,
            Verdict::Ok
        );
        assert!(pressure_check(None, None).is_none());
    }

    #[test]
    fn swaps_grade_and_flag_zram() {
        let healthy = "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n/dev/zram0                              partition\t16252924\t4456444\t100\n";
        let check = swap_check(healthy).unwrap();
        assert_eq!(check.verdict, Verdict::Ok);
        assert!(check.detail.contains("zram"));

        let heavy = "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n/dev/zram0                              partition\t16252924\t14500000\t100\n";
        assert_eq!(swap_check(heavy).unwrap().verdict, Verdict::Critical);
    }

    #[test]
    fn df_grades_available_gib() {
        let healthy = "Filesystem     1024-blocks      Used Available Capacity Mounted on\n/dev/nvme0n1p2   245000000 201000000  44000000      83% /\n";
        assert_eq!(disk_check(healthy).unwrap().verdict, Verdict::Ok);

        let warn = "Filesystem     1024-blocks      Used Available Capacity Mounted on\n/dev/nvme0n1p2   245000000 230000000  15000000      94% /\n";
        assert_eq!(disk_check(warn).unwrap().verdict, Verdict::Warn);

        let critical = "Filesystem     1024-blocks      Used Available Capacity Mounted on\n/dev/nvme0n1p2   245000000 243000000   4000000      99% /\n";
        assert_eq!(disk_check(critical).unwrap().verdict, Verdict::Critical);
    }

    #[test]
    fn crash_loop_check_flags_auto_restart_units() {
        let clean = "  graphical-session.target loaded active active\n";
        assert_eq!(crash_loop_check(clean).verdict, Verdict::Ok);

        let looping = "  edge-galaxy.service loaded activating auto-restart Edge-galaxy telemetry store\n  wm-chatd.service loaded activating auto-restart Magic-Chat web BFF\n";
        let check = crash_loop_check(looping);
        assert_eq!(check.verdict, Verdict::Critical);
        assert!(check.detail.contains("edge-galaxy.service"));
        assert!(check.detail.contains("wm-chatd.service"));
    }

    #[test]
    fn overall_status_is_worst_check() {
        let checks = vec![
            Check::new("disk", Verdict::Ok, "fine".to_string(), None),
            Check::new("memory", Verdict::Warn, "tight".to_string(), None),
            Check::new("pressure", Verdict::Critical, "stalling".to_string(), None),
        ];
        let health = HostHealth::from_checks(checks, Vec::new());
        assert_eq!(health.status, Verdict::Critical);
        let lines = health.render_lines();
        assert!(lines[0].contains("critical"));
    }

    #[test]
    fn render_includes_hints_and_top_processes() {
        let checks = vec![Check::new(
            "crash-loops",
            Verdict::Critical,
            "1 unit stuck".to_string(),
            Some("systemctl --user stop x.service".to_string()),
        )];
        let top = vec![ProcessMemory {
            pid: 42,
            name: "llama-server".to_string(),
            rss_mib: 2761,
        }];
        let health = HostHealth::from_checks(checks, top);
        let rendered = health.render_lines().join("\n");
        assert!(rendered.contains("systemctl --user stop x.service"));
        assert!(rendered.contains("llama-server (pid 42)"));
    }

    #[test]
    fn parse_systemctl_show_reads_contract_fields() {
        let text = "ActiveState=activating\nSubState=auto-restart\nNRestarts=6534\nLoadState=loaded\nFragmentPath=/home/u/.config/systemd/user/edge-galaxy.service\n";
        let unit = parse_systemctl_show("edge-galaxy.service", text).unwrap();
        assert_eq!(unit.unit, "edge-galaxy.service");
        assert_eq!(unit.active_state, "activating");
        assert_eq!(unit.sub_state, "auto-restart");
        assert_eq!(unit.n_restarts, 6534);
        assert_eq!(unit.load_state, "loaded");
        assert_eq!(
            unit.fragment_path,
            "/home/u/.config/systemd/user/edge-galaxy.service"
        );
        assert!(parse_systemctl_show("x.service", "SubState=auto-restart\n").is_none());
    }

    #[test]
    fn parse_cmdline_joins_nul_separated_args() {
        assert_eq!(
            parse_cmdline(b"llama-server\0--port\08080\0"),
            "llama-server --port 8080"
        );
        assert_eq!(parse_cmdline(b""), "");
        assert_eq!(
            parse_cmdline(b"python3\0scripts/lane_eval.py\0"),
            "python3 scripts/lane_eval.py"
        );
    }

    #[test]
    fn parse_cgroup_unit_returns_last_component() {
        let v2 = "0::/user.slice/user-1000.slice/user@1000.service/app.slice/app-gnome-Alacritty-1234.scope";
        assert_eq!(parse_cgroup_unit(v2), "app-gnome-Alacritty-1234.scope");
        let v1 = "1:name=systemd:/user.slice/user-1000.slice/session-2.scope\n";
        assert_eq!(parse_cgroup_unit(v1), "session-2.scope");
        assert_eq!(parse_cgroup_unit("garbage"), "");
    }

    #[test]
    fn parse_ppid_reads_status_line() {
        let status = "Name:\tllama-server\nPPid:\t1234\nVmRSS:\t 2826240 kB\n";
        assert_eq!(parse_ppid(status), Some(1234));
        assert_eq!(parse_ppid("Name:\tx\n"), None);
    }

    #[test]
    fn infer_orphan_flags_reparented_and_session_scoped() {
        assert!(infer_orphan(
            1,
            "0::/user.slice/user-1000.slice/user@1000.service"
        ));
        assert!(infer_orphan(
            4242,
            "0::/user.slice/user-1000.slice/session-2.scope"
        ));
        assert!(!infer_orphan(
            4242,
            "0::/user.slice/user-1000.slice/user@1000.service/app.slice"
        ));
    }

    #[test]
    fn signal_checks_match_legacy_output() {
        let meminfo = "MemTotal:       16000000 kB\nMemAvailable:    9000000 kB\n";
        let psi_mem = "some avg10=1.00 avg60=1.00 avg300=1.00 total=1\nfull avg10=4.39 avg60=1.00 avg300=1.00 total=2\n";
        let psi_io = "some avg10=1.00 avg60=1.00 avg300=1.00 total=1\nfull avg10=0.28 avg60=1.00 avg300=1.00 total=2\n";
        let swaps = "Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n/dev/zram0                              partition\t16252924\t4456444\t100\n";
        let df = "Filesystem     1024-blocks      Used Available Capacity Mounted on\n/dev/nvme0n1p2   245000000 201000000  44000000      83% /\n";
        let units =
            "  edge-galaxy.service loaded activating auto-restart Edge-galaxy telemetry store\n";

        let expected = vec![
            memory_check(meminfo).unwrap(),
            pressure_check(Some(psi_mem), Some(psi_io)).unwrap(),
            swap_check(swaps).unwrap(),
            disk_check(df).unwrap(),
            crash_loop_check(units),
        ];

        let signals = HostSignals {
            mem_total_kib: 16_000_000,
            mem_available_kib: 9_000_000,
            mem_available_fraction: 9_000_000.0 / 16_000_000.0,
            psi_memory_full_avg10: parse_psi_avg10(psi_mem, "full"),
            psi_io_full_avg10: parse_psi_avg10(psi_io, "full"),
            swap_total_kib: 16_252_924,
            swap_used_kib: 4_456_444,
            swap_used_fraction: 4_456_444.0 / 16_252_924.0,
            swap_is_zram: true,
            disk_free_gib: Some(44_000_000.0 / 1024.0 / 1024.0),
            disk_used_pct: Some(83.0),
            crash_loop_units: vec![CrashLoopUnit {
                unit: "edge-galaxy.service".to_string(),
                active_state: "activating".to_string(),
                sub_state: "auto-restart".to_string(),
                n_restarts: 0,
                load_state: String::new(),
                fragment_path: String::new(),
            }],
            failed_loop_units: Vec::new(),
            top_processes: Vec::new(),
            unit_probe_ok: true,
        };

        let actual = checks_from_signals(&signals);
        assert_eq!(actual.len(), expected.len());
        for (actual, expected) in actual.iter().zip(expected.iter()) {
            assert_eq!(actual.name, expected.name);
            assert_eq!(actual.verdict, expected.verdict);
            assert_eq!(actual.detail, expected.detail);
        }
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn collect_signals_reports_memory_and_sorted_processes() {
        let signals = collect_signals();
        assert!(signals.mem_total_kib > 0);
        assert!((0.0..=1.5).contains(&signals.mem_available_fraction));
        let mut sorted = signals.top_processes.clone();
        sorted.sort_by(|left, right| right.rss_mib.cmp(&left.rss_mib));
        assert_eq!(signals.top_processes.len(), sorted.len());
        for (actual, expected) in signals.top_processes.iter().zip(sorted.iter()) {
            assert_eq!(actual.pid, expected.pid);
        }
    }
}
