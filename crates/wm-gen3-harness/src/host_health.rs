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
//! - parsers take `&str` so the grading logic is unit-testable without a host.

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
    #[cfg(target_os = "linux")]
    {
        collect_linux()
    }
    #[cfg(not(target_os = "linux"))]
    {
        HostHealth::from_checks(Vec::new(), Vec::new())
    }
}

#[cfg(target_os = "linux")]
fn collect_linux() -> HostHealth {
    use std::fs;

    let mut checks = Vec::new();

    if let Ok(meminfo) = fs::read_to_string("/proc/meminfo") {
        if let Some(check) = memory_check(&meminfo) {
            checks.push(check);
        }
    }
    let pressure_memory = fs::read_to_string("/proc/pressure/memory").ok();
    let pressure_io = fs::read_to_string("/proc/pressure/io").ok();
    if let Some(check) = pressure_check(pressure_memory.as_deref(), pressure_io.as_deref()) {
        checks.push(check);
    }
    if let Ok(swaps) = fs::read_to_string("/proc/swaps") {
        if let Some(check) = swap_check(&swaps) {
            checks.push(check);
        }
    }
    if let Some(df_output) = run_command("df", &["-Pk", "/"]) {
        if let Some(check) = disk_check(&df_output) {
            checks.push(check);
        }
    }
    if let Some(units) = run_command(
        "systemctl",
        &[
            "--user",
            "list-units",
            "--state=activating",
            "--no-legend",
            "--no-pager",
        ],
    ) {
        checks.push(crash_loop_check(&units));
    }

    HostHealth::from_checks(checks, top_memory_processes(TOP_PROCESSES))
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

fn memory_check(meminfo: &str) -> Option<Check> {
    let total_kib = parse_meminfo_value(meminfo, "MemTotal:")?;
    let available_kib = parse_meminfo_value(meminfo, "MemAvailable:")?;
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

fn pressure_check(memory: Option<&str>, io: Option<&str>) -> Option<Check> {
    let memory_full = memory.and_then(|text| parse_psi_avg10(text, "full"));
    let io_full = io.and_then(|text| parse_psi_avg10(text, "full"));
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

fn swap_check(swaps: &str) -> Option<Check> {
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

fn disk_check(df_output: &str) -> Option<Check> {
    let line = df_output
        .lines()
        .skip(1)
        .find(|line| !line.trim().is_empty())?;
    let fields: Vec<&str> = line.split_whitespace().collect();
    if fields.len() < 5 {
        return None;
    }
    let available_kib: u64 = fields[3].parse().ok()?;
    let capacity = fields[4];
    let free_gib = available_kib as f64 / 1024.0 / 1024.0;
    let detail = format!("/: {free_gib:.1} GiB free ({capacity} used)");
    if free_gib < DISK_CRIT_GIB {
        return Some(Check::new(
            "disk",
            Verdict::Critical,
            detail,
            Some(
                "disk is nearly full: prune build caches (scripts/prune_build_cache.sh), \
                 vacuum journals, and remove stale target/ trees"
                    .to_string(),
            ),
        ));
    }
    if free_gib < DISK_WARN_GIB {
        return Some(Check::new(
            "disk",
            Verdict::Warn,
            detail,
            Some("disk headroom below 20 GiB (the stop-and-clean threshold)".to_string()),
        ));
    }
    Some(Check::new("disk", Verdict::Ok, detail, None))
}

fn crash_loop_check(units_output: &str) -> Check {
    let mut looping: Vec<&str> = units_output
        .lines()
        .filter(|line| line.contains("auto-restart"))
        .filter_map(|line| line.split_whitespace().next())
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

#[cfg(target_os = "linux")]
fn top_memory_processes(limit: usize) -> Vec<ProcessMemory> {
    use std::fs;

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
        processes.push(ProcessMemory {
            pid,
            name: comm.to_string(),
            rss_mib: rss_kib / 1024,
        });
    }
    processes.sort_by(|left, right| right.rss_mib.cmp(&left.rss_mib));
    processes.truncate(limit);
    processes
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
}
