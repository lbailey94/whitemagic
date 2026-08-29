//! Landlock v0 — whole-process filesystem confinement at serve init.
//!
//! Opt-in via `WM_LANDLOCK=1` (off by default). The v0 ruleset handles every
//! **write-class** filesystem right and grants them only beneath the store
//! root; read rights are never handled, so reads stay free. On kernels
//! without Landlock (or with it disabled in the LSM stack) the process
//! continues **unconfined with a loud warning** — availability stays up,
//! degradation is never silent.
//!
//! Call-site contract: `restrict_to_store_root` must run on the **main
//! thread before any runtime is spawned** (the tokio workers inherit the
//! restriction of their spawning thread). v0 is thread-local by design —
//! the same property the v1 per-tool pathway (a dedicated restricted
//! thread, gated by `EffectRow::sandbox`) builds on, so this is an upgrade
//! seam, not a rewrite.
//!
//! Reporting follows the profile-contract doctrine: the outcome is logged,
//! served via `/status`, and persisted to `<store-root>/landlock_state.json`
//! (atomic rename) where `wm doctor` grades it read-only. The confined
//! process can always write its own store root, so persistence never fights
//! the sandbox.

use serde::{Deserialize, Serialize};
use std::path::Path;

/// Outcome of a Landlock v0 application attempt.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LandlockOutcome {
    /// Ruleset fully enforced — write-class FS rights confined to the store root.
    Enforced,
    /// Kernel enforced a subset of the requested rights (best-effort downgrade
    /// on an older Landlock ABI). Still meaningful confinement; flagged for visibility.
    Partial,
    /// Kernel lacks Landlock (not built in, disabled at boot, or blocked) —
    /// process continues unconfined.
    Unsupported,
    /// Landlock is Linux-only; the process continues unconfined on this platform.
    PlatformUnsupported,
    /// Ruleset application failed (e.g. seccomp interference) — process
    /// continues unconfined.
    Failed,
    /// `WM_LANDLOCK` was not set — the feature is off by default.
    Off,
}

impl LandlockOutcome {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Enforced => "enforced",
            Self::Partial => "partial",
            Self::Unsupported => "unsupported",
            Self::PlatformUnsupported => "platform_unsupported",
            Self::Failed => "failed",
            Self::Off => "off",
        }
    }

    /// True when a ruleset was applied and at least partly bites.
    #[must_use]
    pub const fn is_enforcing(self) -> bool {
        matches!(self, Self::Enforced | Self::Partial)
    }
}

/// Report of a Landlock v0 application attempt, rendered by `/status`,
/// persisted to the store root, and graded by `wm doctor`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LandlockReport {
    /// Whether `WM_LANDLOCK=1` was requested.
    pub enabled: bool,
    pub outcome: LandlockOutcome,
    pub detail: String,
    /// The store root granted the write-class rights.
    pub store_root: String,
    /// RFC 3339 timestamp of the attempt (`wm_core::time` registry).
    pub requested_at: String,
}

impl LandlockReport {
    #[must_use]
    pub fn off(store_root: &Path) -> Self {
        Self {
            enabled: false,
            outcome: LandlockOutcome::Off,
            detail: "WM_LANDLOCK not set — no ruleset applied".to_string(),
            store_root: store_root.display().to_string(),
            requested_at: wm_core::time::now_rfc3339(),
        }
    }
}

/// Strict flag parse: only exactly `1` enables (no truthy spellings).
#[must_use]
pub fn parse_flag(value: Option<&str>) -> bool {
    value.is_some_and(|v| v == "1")
}

/// Whether Landlock v0 was requested via `WM_LANDLOCK=1`.
#[must_use]
pub fn requested() -> bool {
    parse_flag(std::env::var("WM_LANDLOCK").ok().as_deref())
}

/// Apply the v0 whole-process ruleset at the serve call-site.
///
/// Handles every write-class filesystem right and grants them only beneath
/// `store_root`, plus two declared grants outside it: `/dev/null` (a black
/// hole git needs) and the git common dir under `WM_PROJECT_ROOT` (the
/// `code.claim` lease ledger is a designed Phase-2 write target there).
/// Never fatal — every failure mode degrades to a reported outcome and an
/// unconfined process.
#[must_use]
pub fn restrict_to_store_root(store_root: &Path) -> LandlockReport {
    apply(store_root, true, git_dir_grant().as_deref())
}

/// Apply the ruleset without the production call-site (used by tests, which
/// run on pooled harness threads and must confine only themselves).
#[must_use]
pub fn restrict_to_store_root_thread(store_root: &Path) -> LandlockReport {
    apply(store_root, false, None)
}

/// Test-only variant with an explicit extra grant path (e.g. a repo's
/// `.git`), so the lease-ledger contract can be pinned hermetically without
/// touching process environment.
#[must_use]
pub fn restrict_with_grants_thread(store_root: &Path, git_dir: Option<&Path>) -> LandlockReport {
    apply(store_root, false, git_dir)
}

/// The git common dir under `WM_PROJECT_ROOT` — the coordination lease
/// ledger (`code.claim` → `wm-leases.json`) is a DESIGNED write target
/// there, outside the store root. Only the default layout (`<root>/.git`
/// as a directory) is granted: worktrees with a common dir elsewhere are
/// the documented v0 limitation (v1 per-tool pathway is the seam).
fn git_dir_grant() -> Option<std::path::PathBuf> {
    let root = std::env::var("WM_PROJECT_ROOT").ok()?;
    let dir = std::path::Path::new(&root).join(".git");
    dir.is_dir().then_some(dir)
}

fn apply(store_root: &Path, whole_process: bool, git_dir: Option<&Path>) -> LandlockReport {
    let detail_root = store_root.display().to_string();
    let base = |outcome: LandlockOutcome, detail: String| LandlockReport {
        enabled: true,
        outcome,
        detail,
        store_root: detail_root.clone(),
        requested_at: wm_core::time::now_rfc3339(),
    };

    #[cfg(target_os = "linux")]
    {
        match imp::restrict(store_root, whole_process, git_dir) {
            Ok(Ok((status, abi, grants))) => {
                let (outcome, mut detail) = imp::outcome_of(&status, abi);
                if !grants.is_empty() {
                    detail.push_str("; declared grants: ");
                    detail.push_str(&grants.join(", "));
                }
                base(
                    outcome,
                    format!("{detail} (no_new_privs={})", status.no_new_privs),
                )
            }
            Ok(Err(outcome)) => base(
                outcome,
                "kernel does not enforce Landlock (not built in, disabled in the \
                 LSM stack, or blocked); process continues UNCONFINED"
                    .to_string(),
            ),
            Err(e) => base(
                LandlockOutcome::Failed,
                format!("ruleset application failed, process continues unconfined: {e}"),
            ),
        }
    }

    #[cfg(not(target_os = "linux"))]
    {
        let _ = whole_process;
        let _ = git_dir;
        base(
            LandlockOutcome::PlatformUnsupported,
            "Landlock is a Linux LSM; process continues unconfined on this platform".to_string(),
        )
    }
}

/// Persist the report to `<store-root>/landlock_state.json` (atomic rename).
///
/// Mirrors `profile_contract.json`. Writable and read-only servers both
/// persist: the file describes the *process*, not the store mode, and the
/// doctor grades it either way.
pub fn persist_report(store_root: &Path, report: &LandlockReport) {
    let path = store_root.join("landlock_state.json");
    let tmp = store_root.join(".landlock_state.json.tmp");
    let write = serde_json::to_string_pretty(report)
        .map(|body| std::fs::write(&tmp, body).and_then(|()| std::fs::rename(&tmp, &path)));
    if let Err(e) = write {
        tracing::warn!(
            path = %path.display(),
            error = %e,
            "could not persist Landlock report"
        );
    }
}

/// Load a persisted report (the doctor's read path).
#[must_use]
pub fn load_report(store_root: &Path) -> Option<LandlockReport> {
    let body = std::fs::read_to_string(store_root.join("landlock_state.json")).ok()?;
    serde_json::from_str(&body).ok()
}

#[cfg(target_os = "linux")]
mod imp {
    use super::LandlockOutcome;
    use landlock::{
        ABI, AccessFs, CompatLevel, Compatible, LandlockStatus, PathBeneath, PathFd,
        RestrictSelfAttr, RestrictionStatus, Ruleset, RulesetAttr, RulesetCreatedAttr,
        RulesetStatus,
    };
    use std::path::Path;

    /// Newest ABI first; the probe walks down until a write set is fully
    /// supported.ABI V9 is the newest this crate knows; newer kernels map
    /// onto it cleanly.
    const WRITE_ABI_LADDER: [ABI; 9] = [
        ABI::V9,
        ABI::V8,
        ABI::V7,
        ABI::V6,
        ABI::V5,
        ABI::V4,
        ABI::V3,
        ABI::V2,
        ABI::V1,
    ];

    /// Highest ABI whose full write set the running kernel supports.
    ///
    /// Pure userspace checks — the crate caches the kernel's Landlock ABI
    /// and a HardRequirement `handle_access` errors without creating any
    /// ruleset — so probing is free and side-effect-free. Requesting exactly
    /// this set keeps `FullyEnforced` reachable on every Landlock-enabled
    /// kernel instead of permanently reporting a best-effort downgrade.
    fn effective_write_abi() -> Option<ABI> {
        for abi in WRITE_ABI_LADDER {
            let probe = Ruleset::default()
                .set_compatibility(CompatLevel::HardRequirement)
                .handle_access(AccessFs::from_write(abi));
            if probe.is_ok() {
                return Some(abi);
            }
        }
        None
    }

    /// Restrict outcome: outer layer = ruleset setup errors; inner layer =
    /// an `Unsupported` verdict or the restriction status with the
    /// effective ABI and the declared extra grants.
    type RestrictOutcome =
        Result<Result<(RestrictionStatus, ABI, Vec<String>), LandlockOutcome>, String>;

    pub(super) fn restrict(
        store_root: &Path,
        whole_process: bool,
        git_dir: Option<&Path>,
    ) -> RestrictOutcome {
        // PathFd::new yields its own error type; the report only needs the
        // message, so every stage maps to String. The probe ladder finding
        // nothing means Landlock itself is unavailable — that is an
        // Unsupported outcome, not an application failure.
        let Some(abi) = effective_write_abi() else {
            return Ok(Err(LandlockOutcome::Unsupported));
        };
        let write_set = AccessFs::from_write(abi);
        let root_fd = PathFd::new(store_root).map_err(|e| e.to_string())?;
        let mut created = Ruleset::default()
            .set_compatibility(CompatLevel::BestEffort)
            .handle_access(write_set)
            .map_err(|e| e.to_string())?
            .create()
            .map_err(|e| e.to_string())?
            .add_rule(PathBeneath::new(root_fd, write_set))
            .map_err(|e| e.to_string())?;
        let mut grants: Vec<String> = Vec::new();
        // git and other subprocesses open /dev/null O_RDWR ("could not open
        // '/dev/null' for reading and writing" under confinement). Grant
        // ONLY WriteFile: the full write set contains directory-class and
        // device-class rights a char device can never enforce, and a
        // partially-enforceable rule would downgrade the whole ruleset to
        // `partial` (found by the post-fix live check, 2026-08-29). A black
        // hole grants nothing an attacker can use.
        let devnull = PathFd::new("/dev/null").map_err(|e| e.to_string())?;
        created = created
            .add_rule(PathBeneath::new(devnull, AccessFs::WriteFile))
            .map_err(|e| e.to_string())?;
        grants.push("/dev/null (WriteFile)".to_string());
        // The coordination lease ledger (`code.claim` → `wm-leases.json` in
        // the git common dir) is a designed write target OUTSIDE the store
        // root (found live 2026-08-29: code.claim got EACCES under
        // confinement on the wmv5 unit). Grant the full write set on the
        // git dir itself — a purposeful, narrow grant of the repo's own
        // coordination directory, not a widening of the data plane.
        if let Some(dir) = git_dir {
            let fd = PathFd::new(dir).map_err(|e| e.to_string())?;
            created = created
                .add_rule(PathBeneath::new(fd, write_set))
                .map_err(|e| e.to_string())?;
            grants.push(format!("git-dir {}", dir.display()));
        }
        if whole_process {
            created = created.all_threads(true).map_err(|e| e.to_string())?;
        }
        let status = created.restrict_self().map_err(|e| e.to_string())?;
        Ok(Ok((status, abi, grants)))
    }

    pub(super) fn outcome_of(status: &RestrictionStatus, abi: ABI) -> (LandlockOutcome, String) {
        let abi_note = match status.landlock {
            LandlockStatus::Available {
                kernel_abi: Some(k),
                ..
            } => format!(
                "Landlock ABI v{} (kernel v{k} newer than crate)",
                abi as u32
            ),
            _ => format!("Landlock ABI v{}", abi as u32),
        };
        match status.ruleset {
            RulesetStatus::FullyEnforced => (
                LandlockOutcome::Enforced,
                format!(
                    "write-class FS rights confined to the store root + /dev/null ({abi_note})"
                ),
            ),
            RulesetStatus::PartiallyEnforced => (
                LandlockOutcome::Partial,
                format!(
                    "kernel enforced a subset of the requested write-class rights \
                     (best-effort downgrade); process partially confined ({abi_note})"
                ),
            ),
            RulesetStatus::NotEnforced => (
                LandlockOutcome::Unsupported,
                "kernel does not enforce Landlock (not built in, disabled in the \
                 LSM stack, or blocked); process continues UNCONFINED"
                    .to_string(),
            ),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn flag_parse_is_strict() {
        assert!(!parse_flag(None));
        assert!(parse_flag(Some("1")));
        // Deliberately strict: no truthy spellings, per the v0 spec.
        assert!(!parse_flag(Some("0")));
        assert!(!parse_flag(Some("true")));
        assert!(!parse_flag(Some("yes")));
        assert!(!parse_flag(Some("")));
    }

    #[test]
    fn off_report_shape() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let report = LandlockReport::off(tmp.path());
        assert!(!report.enabled);
        assert_eq!(report.outcome, LandlockOutcome::Off);
        assert!(!report.outcome.is_enforcing());
    }

    #[test]
    fn report_serializes() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let report = LandlockReport::off(tmp.path());
        let json = serde_json::to_string(&report).expect("serialize");
        assert!(json.contains("\"outcome\":\"off\""));
        let back: LandlockReport = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(back, report);
    }

    #[test]
    fn persist_and_load_roundtrip() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let report = LandlockReport::off(tmp.path());
        persist_report(tmp.path(), &report);
        let loaded = load_report(tmp.path()).expect("persisted report readable");
        assert_eq!(loaded, report);
        assert!(!tmp.path().join(".landlock_state.json.tmp").exists());
    }

    /// The v0 acceptance kernel probe, run on a dedicated thread so only
    /// that thread is confined (the test harness keeps its ambient rights).
    /// On a Landlock-enforcing kernel: writes under the store root succeed,
    /// writes outside fail. On a degraded kernel the report says so and
    /// both writes succeed (the test stays honest either way).
    #[test]
    fn restrict_grants_store_root_and_denies_outside() {
        let root = tempfile::tempdir().expect("root tempdir");
        let outside = tempfile::tempdir().expect("outside tempdir");
        let inside_path = root.path().join("inside.txt");
        let outside_path = outside.path().join("outside.txt");

        let root_path = root.path().to_path_buf();
        let handle = std::thread::spawn(move || {
            let report = restrict_to_store_root_thread(&root_path);
            let inside_ok = std::fs::write(&inside_path, b"ok").is_ok();
            let outside_ok = std::fs::write(&outside_path, b"no").is_ok();
            (report, inside_ok, outside_ok)
        });
        let (report, inside_ok, outside_ok) = handle.join().expect("worker joined");

        match report.outcome {
            LandlockOutcome::Enforced | LandlockOutcome::Partial => {
                assert!(report.enabled);
                assert!(report.outcome.is_enforcing());
                assert!(inside_ok, "store-root write must succeed while confined");
                assert!(
                    !outside_ok,
                    "outside-root write must fail while confined (report: {report:?})",
                );
            }
            other => {
                // Degraded kernel: no restriction applied, both writes succeed.
                assert!(!other.is_enforcing());
                assert!(
                    inside_ok && outside_ok,
                    "unconfined process must write freely"
                );
            }
        }
    }

    /// After a thread-local restriction on a worker, the harness thread
    /// (which spawned the worker BEFORE it restricted itself) keeps its
    /// ambient rights — the property v1's restricted-thread pathway relies on.
    #[cfg(target_os = "linux")]
    #[test]
    fn restriction_is_thread_local_not_process_wide() {
        let root = tempfile::tempdir().expect("root tempdir");
        let outside = tempfile::tempdir().expect("outside tempdir");
        let outside_path = outside.path().join("harness.txt");

        let root_path = root.path().to_path_buf();
        let handle = std::thread::spawn(move || {
            let report = restrict_to_store_root_thread(&root_path);
            report.outcome
        });
        let outcome = handle.join().expect("worker joined");

        if outcome.is_enforcing() {
            // The worker was confined; this harness thread was not.
            assert!(
                std::fs::write(&outside_path, b"harness").is_ok(),
                "harness thread must keep ambient rights after a sibling thread \
                 restricted itself"
            );
        }
    }

    /// `session.checkpoint`/`session.verify` run git capture as a subprocess
    /// from inside the (possibly confined) server, with the repo at
    /// WM_PROJECT_ROOT — i.e. OUTSIDE the store root. Read-class git
    /// commands must keep working under confinement. `git status` normally
    /// refreshes the index (a write to .git/) and may fail when confined;
    /// `GIT_OPTIONAL_LOCKS=0` disables that refresh. This test pins both.
    #[cfg(target_os = "linux")]
    #[test]
    fn git_capture_works_under_confinement() {
        // Build the throwaway repo UNCONFINED (harness thread): a repo
        // outside the store root is the checkpoint situation.
        let repo_dir = tempfile::tempdir().expect("repo tempdir");
        let store_dir = tempfile::tempdir().expect("store tempdir");
        let run_unconfined = |args: &[&str]| {
            let out = std::process::Command::new("git")
                .args(args)
                .current_dir(repo_dir.path())
                .env("GIT_AUTHOR_NAME", "t")
                .env("GIT_AUTHOR_EMAIL", "t@t")
                .env("GIT_COMMITTER_NAME", "t")
                .env("GIT_COMMITTER_EMAIL", "t@t")
                .output()
                .expect("spawn git (unconfined setup)");
            assert!(
                out.status.success(),
                "setup git {args:?} failed: {}",
                String::from_utf8_lossy(&out.stderr)
            );
        };
        run_unconfined(&["init", "-q"]);
        std::fs::write(repo_dir.path().join("f.txt"), "x").expect("write file");
        run_unconfined(&["add", "."]);
        run_unconfined(&["commit", "-qm", "init"]);

        let repo = repo_dir.path().to_path_buf();
        let store = store_dir.path().to_path_buf();
        let handle = std::thread::spawn(move || {
            let report = restrict_to_store_root_thread(&store);
            // The exact capture_git_state sequence, with stderr captured so
            // a failure names its mechanism instead of degrading silently.
            let probe = |git_args: &[&str], optional_locks: bool| {
                let mut cmd = std::process::Command::new("git");
                cmd.args(git_args)
                    .current_dir(&repo)
                    .env("GIT_OPTIONAL_LOCKS", if optional_locks { "0" } else { "1" });
                match cmd.output() {
                    Ok(o) => (
                        o.status.success(),
                        String::from_utf8_lossy(&o.stderr).trim().to_string(),
                    ),
                    Err(e) => (false, format!("spawn error: {e}")),
                }
            };
            (
                report.outcome,
                probe(&["rev-parse", "--is-inside-work-tree"], true),
                probe(&["rev-parse", "HEAD"], true),
                probe(&["status", "--porcelain"], true),
                probe(&["status", "--porcelain"], false),
            )
        });
        let (outcome, revparse_tree, revparse_head, status_fixed, status_raw) =
            handle.join().expect("worker joined");

        println!("outcome: {outcome:?}");
        println!("rev-parse --is-inside-work-tree: {revparse_tree:?}");
        println!("rev-parse HEAD: {revparse_head:?}");
        println!("status (GIT_OPTIONAL_LOCKS=0): {status_fixed:?}");
        println!("status (raw): {status_raw:?}");

        if outcome.is_enforcing() {
            assert!(
                revparse_tree.0,
                "git rev-parse --is-inside-work-tree must work under confinement: {revparse_tree:?}"
            );
            assert!(
                revparse_head.0,
                "git rev-parse HEAD must work under confinement: {revparse_head:?}"
            );
            assert!(
                status_fixed.0,
                "git status with GIT_OPTIONAL_LOCKS=0 must work under confinement: {status_fixed:?}"
            );
        }
    }

    /// The coordination lease ledger (`code.claim` → `wm-leases.json` in the
    /// repo's git common dir under WM_PROJECT_ROOT) is a DESIGNED write
    /// target outside the store root. Found live 2026-08-29: `code.claim`
    /// failed with EACCES on the Landlock-confined wmv5 unit — two shipped
    /// features conflicting at the boundary. This test pins both sides:
    /// with the git-dir grant the ledger writes succeed; without it they
    /// fail (the day-one catch, kept visible).
    #[cfg(target_os = "linux")]
    #[test]
    fn lease_ledger_writes_need_the_git_dir_grant() {
        let repo_dir = tempfile::tempdir().expect("repo tempdir");
        let store_dir = tempfile::tempdir().expect("store tempdir");
        let run_unconfined = |args: &[&str]| {
            let out = std::process::Command::new("git")
                .args(args)
                .current_dir(repo_dir.path())
                .env("GIT_AUTHOR_NAME", "t")
                .env("GIT_AUTHOR_EMAIL", "t@t")
                .env("GIT_COMMITTER_NAME", "t")
                .env("GIT_COMMITTER_EMAIL", "t@t")
                .output()
                .expect("spawn git (unconfined setup)");
            assert!(
                out.status.success(),
                "setup git {args:?} failed: {}",
                String::from_utf8_lossy(&out.stderr)
            );
        };
        run_unconfined(&["init", "-q"]);

        // The exact write shape of the lease ledger: lock file, payload
        // write, atomic rename (LeaseLedger's read-modify-write core).
        let ledger_write = |git_dir: &std::path::Path| -> (bool, bool) {
            let lock_ok = std::fs::write(git_dir.join("wm-leases.json.lock"), b"pid").is_ok();
            let tmp = git_dir.join(".wm-leases.json.tmp");
            let rename_ok = std::fs::write(&tmp, b"{}")
                .and_then(|()| std::fs::rename(&tmp, git_dir.join("wm-leases.json")))
                .is_ok();
            (lock_ok, rename_ok)
        };

        let repo = repo_dir.path().to_path_buf();
        let store = store_dir.path().to_path_buf();
        let granted = std::thread::spawn(move || {
            let git_dir = repo.join(".git");
            let report = restrict_with_grants_thread(&store, Some(&git_dir));
            (report.outcome, ledger_write(&git_dir))
        })
        .join()
        .expect("granted thread joined");

        let repo2 = repo_dir.path().to_path_buf();
        let store2 = store_dir.path().to_path_buf();
        let ungranted = std::thread::spawn(move || {
            let git_dir = repo2.join(".git");
            let report = restrict_to_store_root_thread(&store2);
            (report.outcome, ledger_write(&git_dir))
        })
        .join()
        .expect("ungranted thread joined");

        println!("granted outcome: {:?}", granted.0);
        println!("ungranted outcome: {:?}", ungranted.0);

        if granted.0.is_enforcing() {
            assert!(
                granted.1 == (true, true),
                "lease-ledger writes must succeed with the git-dir grant: {granted:?}"
            );
            if ungranted.0.is_enforcing() {
                assert!(
                    !(ungranted.1.0 && ungranted.1.1),
                    "without the grant the ledger write must fail (the day-one catch): {ungranted:?}"
                );
            }
        } else {
            // Degraded kernel: everything succeeds either way.
            assert!(granted.1 == (true, true) && ungranted.1 == (true, true));
        }
    }
}
