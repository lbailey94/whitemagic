//! Subprocess spawn policy — the B2 seam between tools and the OS runner.
//!
//! In-process Landlock (v0/v1) cannot confine a child process a tool
//! launches: the restriction is thread-local and the child never inherits
//! it. Confinement therefore has to wrap the *spawned command* instead.
//! The dispatcher resolves a [`SpawnPolicy`] from the tool's effect row and
//! hands it to the tool through [`crate::Context::spawn`]; the tool builds
//! its `std::process::Command` through [`SpawnPolicy::command`].
//!
//! When a runner is active the command is invoked as
//! `mandala-sandbox --exec '<json envelope>'`; the envelope carries the
//! program, args, and whether the tool's effect row grants network. The OS
//! wrapper owns the actual containment policy (bubblewrap profile,
//! namespaces, binds) — WM only decides *which* commands are eligible and
//! *what* the tool declared. When no runner resolves, `command()` returns a
//! plain command; the dispatcher is responsible for the loud-degrade
//! warning and counter (the doctrine of Landlock v0/v1).
//!
//! Runner discovery (strict, in order):
//! 1. `WM_SANDBOX_RUNNER` — explicit path; `""`/`0`/`false`/`off`/`none`
//!    disable; a value that is not a file disables with a WARN.
//! 2. `mandala-sandbox` on `PATH`.

use std::path::{Path, PathBuf};
use std::process::Command;

use crate::effects::{EffectRow, Resource};

/// Environment override for the runner path.
pub const RUNNER_ENV: &str = "WM_SANDBOX_RUNNER";

/// Program name looked up on `PATH` when no explicit override is set.
pub const RUNNER_PROGRAM: &str = "mandala-sandbox";

/// Schema tag carried in every `--exec` JSON envelope.
pub const ENVELOPE_SCHEMA: &str = "wm-sandbox-exec-v1";

/// How the runner path was resolved.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RunnerSource {
    /// Explicit `WM_SANDBOX_RUNNER` override.
    Env,
    /// Found on `PATH`.
    Path,
}

impl RunnerSource {
    /// Stable string for status/report rendering.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Env => "env",
            Self::Path => "path",
        }
    }
}

/// A resolved sandbox runner.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RunnerInfo {
    /// Absolute (or PATH-relative) runner executable.
    pub path: PathBuf,
    /// How it was resolved.
    pub source: RunnerSource,
}

/// Explicit-off tokens for [`RUNNER_ENV`] (case-insensitive).
const DISABLED_TOKENS: &[&str] = &["0", "false", "off", "none"];

/// Classification of the `WM_SANDBOX_RUNNER` value.
#[derive(Debug, Clone, PartialEq, Eq)]
enum EnvRunner {
    /// Variable not set — fall through to `PATH`.
    Unset,
    /// Explicitly disabled (token or non-file path).
    Disabled,
    /// Explicit path.
    Path(PathBuf),
}

fn classify_env(raw: &str) -> EnvRunner {
    let trimmed = raw.trim();
    if trimmed.is_empty()
        || DISABLED_TOKENS
            .iter()
            .any(|v| trimmed.eq_ignore_ascii_case(v))
    {
        return EnvRunner::Disabled;
    }
    let path = PathBuf::from(trimmed);
    if path.is_file() {
        EnvRunner::Path(path)
    } else {
        tracing::warn!(
            value = trimmed,
            "WM_SANDBOX_RUNNER does not name a file — subprocess sandbox disabled"
        );
        EnvRunner::Disabled
    }
}

fn env_runner() -> EnvRunner {
    std::env::var(RUNNER_ENV).map_or(EnvRunner::Unset, |raw| classify_env(&raw))
}

fn path_runner_in(path_var: &std::ffi::OsStr) -> Option<RunnerInfo> {
    std::env::split_paths(path_var)
        .map(|dir| dir.join(RUNNER_PROGRAM))
        .find(|candidate| candidate.is_file())
        .map(|path| RunnerInfo {
            path,
            source: RunnerSource::Path,
        })
}

fn path_runner() -> Option<RunnerInfo> {
    std::env::var_os("PATH").and_then(|path_var| path_runner_in(&path_var))
}

/// Resolve the active sandbox runner: explicit env override, else `PATH`.
#[must_use]
pub fn detect_runner() -> Option<RunnerInfo> {
    match env_runner() {
        EnvRunner::Path(path) => Some(RunnerInfo {
            path,
            source: RunnerSource::Env,
        }),
        EnvRunner::Disabled => None,
        EnvRunner::Unset => path_runner(),
    }
}

/// Whether the effect row grants network access (drives the runner's
/// `--net` selection for the spawned command).
#[must_use]
pub fn net_grant(effects: &EffectRow) -> bool {
    effects
        .reads
        .iter()
        .chain(effects.writes.iter())
        .any(|r| matches!(r, Resource::Network))
}

/// Per-dispatch spawn confinement policy handed to tools via
/// [`crate::Context::spawn`].
///
/// `runner: None` = inert policy: [`Self::command`] returns a plain
/// command (the dispatcher counts and warns the degradation).
#[derive(Debug, Clone, Default)]
pub struct SpawnPolicy {
    runner: Option<PathBuf>,
    allow_net: bool,
}

impl SpawnPolicy {
    /// Inert policy — commands run unconfined.
    #[must_use]
    pub fn disabled() -> Self {
        Self::default()
    }

    /// Build from a resolved runner path and network grant.
    #[must_use]
    pub const fn from_runner(runner: Option<PathBuf>, allow_net: bool) -> Self {
        Self { runner, allow_net }
    }

    /// Detect a runner and build a policy with an explicit net grant.
    #[must_use]
    pub fn detected(allow_net: bool) -> Self {
        Self::from_runner(detect_runner().map(|r| r.path), allow_net)
    }

    /// Detect a runner and derive the net grant from the effect row.
    #[must_use]
    pub fn for_effects(effects: &EffectRow) -> Self {
        Self::detected(net_grant(effects))
    }

    /// Whether a runner is attached.
    #[must_use]
    pub const fn is_active(&self) -> bool {
        self.runner.is_some()
    }

    /// The attached runner path, if any.
    #[must_use]
    pub fn runner(&self) -> Option<&Path> {
        self.runner.as_deref()
    }

    /// Whether the spawned command may use the network.
    #[must_use]
    pub const fn allow_net(&self) -> bool {
        self.allow_net
    }

    /// Build the envelope the OS runner interprets.
    #[must_use]
    pub fn envelope(&self, program: &str, args: &[&str]) -> serde_json::Value {
        serde_json::json!({
            "schema": ENVELOPE_SCHEMA,
            "program": program,
            "args": args,
            "net": self.allow_net,
        })
    }

    /// Serialized envelope (what actually lands on the runner's argv).
    #[must_use]
    pub fn envelope_json(&self, program: &str, args: &[&str]) -> String {
        self.envelope(program, args).to_string()
    }

    /// Build a command honoring the policy.
    ///
    /// Active runner → `runner --exec '<envelope>'`; inactive → plain
    /// `program args...`. Callers must use this for every external spawn
    /// when the tool declares `Sandbox::Subprocess`.
    #[must_use]
    pub fn command(&self, program: &str, args: &[&str]) -> Command {
        match &self.runner {
            None => {
                let mut cmd = Command::new(program);
                cmd.args(args);
                cmd
            }
            Some(runner) => {
                let mut cmd = Command::new(runner);
                cmd.arg("--exec").arg(self.envelope_json(program, args));
                cmd
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::OsStr;

    fn network_effects() -> EffectRow {
        EffectRow {
            reads: vec![Resource::Network],
            ..Default::default()
        }
    }

    #[test]
    fn env_classification_is_strict() {
        assert_eq!(classify_env(""), EnvRunner::Disabled);
        assert_eq!(classify_env("0"), EnvRunner::Disabled);
        assert_eq!(classify_env("OFF"), EnvRunner::Disabled);
        assert_eq!(classify_env("none"), EnvRunner::Disabled);
        assert_eq!(classify_env("  false "), EnvRunner::Disabled);
        // A non-existent path disables (with a warning), never falls back.
        assert_eq!(classify_env("/no/such/runner"), EnvRunner::Disabled);
        // An existing file resolves.
        let exe = std::env::current_exe().expect("test exe");
        assert_eq!(classify_env(exe.to_str().unwrap()), EnvRunner::Path(exe));
    }

    #[test]
    fn path_lookup_finds_runner_only_when_present() {
        let dir = std::env::temp_dir().join(format!("wm-sandbox-test-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path_var = dir.as_os_str();
        assert_eq!(path_runner_in(path_var), None, "empty dir finds nothing");
        let fake = dir.join(RUNNER_PROGRAM);
        std::fs::write(&fake, b"#!/bin/sh\n").unwrap();
        let found = path_runner_in(path_var).expect("runner found");
        assert_eq!(found.path, fake);
        assert_eq!(found.source, RunnerSource::Path);
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn inactive_policy_builds_plain_command() {
        let policy = SpawnPolicy::disabled();
        assert!(!policy.is_active());
        let cmd = policy.command("gh", &["issue", "list"]);
        assert_eq!(cmd.get_program(), OsStr::new("gh"));
        let args: Vec<_> = cmd.get_args().collect();
        assert_eq!(args, vec![OsStr::new("issue"), OsStr::new("list")]);
    }

    #[test]
    fn active_policy_wraps_with_json_envelope() {
        let policy = SpawnPolicy::from_runner(Some(PathBuf::from("/opt/mandala-sandbox")), true);
        assert!(policy.is_active());
        let cmd = policy.command("timeout", &["30", "gh"]);
        assert_eq!(cmd.get_program(), OsStr::new("/opt/mandala-sandbox"));
        let args: Vec<_> = cmd.get_args().collect();
        assert_eq!(args[0], OsStr::new("--exec"));
        let envelope: serde_json::Value =
            serde_json::from_str(args[1].to_str().unwrap()).expect("envelope is JSON");
        assert_eq!(envelope["schema"], ENVELOPE_SCHEMA);
        assert_eq!(envelope["program"], "timeout");
        assert_eq!(envelope["args"], serde_json::json!(["30", "gh"]));
        assert_eq!(envelope["net"], true);
    }

    #[test]
    fn net_grant_derives_from_effect_row() {
        assert!(net_grant(&network_effects()));
        assert!(!net_grant(&EffectRow::pure()));
        let write_net = EffectRow {
            writes: vec![Resource::Network],
            ..Default::default()
        };
        assert!(net_grant(&write_net));
    }

    #[test]
    fn for_effects_uses_detection_and_declared_network() {
        let policy = SpawnPolicy::for_effects(&network_effects());
        assert!(policy.allow_net());
        // In this test process no runner is configured, so the policy is
        // inert — but the net grant still reflects the declaration.
        let envelope = policy.envelope("true", &[]);
        assert_eq!(envelope["net"], true);
    }
}
