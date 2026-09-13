//! B2 — subprocess spawn sandbox registry.
//!
//! Tools that declare `Sandbox::Subprocess` launch external processes
//! through [`wm_core::sandbox::SpawnPolicy`], which the dispatcher injects
//! into the [`wm_core::Context`] before the call. This module owns the
//! process-wide runner resolution, the dispatch counters, and the
//! loud-degrade bookkeeping:
//!
//! - **confined**: a declared tool dispatched with a runner attached —
//!   counted, and the active policy disclosed on the response.
//! - **degraded**: a declared tool dispatched with no runner resolvable —
//!   counted, warned (once per tool), and the command *still runs*
//!   unconfined. Availability first, drift never silent.
//! - **unconfined spawns**: a tool that declares `spawns` but not
//!   `Sandbox::Subprocess` — counted and warned once per tool, because a
//!   declared spawn site that bypasses the policy is exactly the drift
//!   this seam exists to surface. It does not fail the call.
//!
//! Runner discovery lives in [`wm_core::sandbox::detect_runner`]
//! (`WM_SANDBOX_RUNNER` env → `PATH` lookup). The dispatcher attaches a
//! registry explicitly via
//! [`DispatchPipeline::with_subprocess_sandbox`](crate::DispatchPipeline::with_subprocess_sandbox);
//! without one the declarations are inert (same doctrine as the Landlock
//! v1 executor).

use std::collections::HashSet;
use std::sync::Mutex;
use std::sync::atomic::{AtomicU64, Ordering};

use wm_core::sandbox::{ENVELOPE_SCHEMA, RunnerInfo, SpawnPolicy, detect_runner};
use wm_core::{EffectRow, Sandbox};

/// Process-wide subprocess sandbox registry.
pub struct SubprocessSandbox {
    runner: Option<RunnerInfo>,
    dispatches: AtomicU64,
    degraded: AtomicU64,
    unconfined_spawns: AtomicU64,
    /// Tools already warned about (once-per-tool log discipline).
    warned: Mutex<HashSet<String>>,
}

impl SubprocessSandbox {
    /// Resolve the runner from the environment / `PATH`.
    #[must_use]
    pub fn detect() -> Self {
        Self::with_runner(detect_runner())
    }

    /// Build with an explicit runner resolution (tests, deterministic deployments).
    #[must_use]
    pub fn with_runner(runner: Option<RunnerInfo>) -> Self {
        Self {
            runner,
            dispatches: AtomicU64::new(0),
            degraded: AtomicU64::new(0),
            unconfined_spawns: AtomicU64::new(0),
            warned: Mutex::new(HashSet::new()),
        }
    }

    /// Whether a runner is attached.
    #[must_use]
    pub const fn is_active(&self) -> bool {
        self.runner.is_some()
    }

    /// The resolved runner, if any.
    #[must_use]
    pub const fn runner(&self) -> Option<&RunnerInfo> {
        self.runner.as_ref()
    }

    /// Whether the tool contractually routes its spawns through the policy.
    #[must_use]
    pub fn declared(effects: &EffectRow) -> bool {
        effects.sandbox == Sandbox::Subprocess
    }

    /// Per-dispatch policy for the given effect row (net grant derived
    /// from `Resource::Network`). Inert when no runner is attached.
    #[must_use]
    pub fn policy_for(&self, effects: &EffectRow) -> SpawnPolicy {
        SpawnPolicy::from_runner(
            self.runner.as_ref().map(|r| r.path.clone()),
            wm_core::sandbox::net_grant(effects),
        )
    }

    /// Count a declared dispatch that carried an active runner.
    pub fn note_confined(&self) {
        self.dispatches.fetch_add(1, Ordering::Relaxed);
    }

    /// Count + warn (once per tool) a declared dispatch with no runner.
    pub fn note_degraded(&self, tool: &str) {
        self.dispatches.fetch_add(1, Ordering::Relaxed);
        self.degraded.fetch_add(1, Ordering::Relaxed);
        self.warn_once(
            tool,
            "subprocess sandbox: no runner resolved — declared spawn runs unconfined (loud-degrade)",
        );
    }

    /// Count + warn (once per tool) a spawn-declared tool that has not
    /// adopted the `Sandbox::Subprocess` contract.
    pub fn note_unconfined_spawn(&self, tool: &str) {
        self.unconfined_spawns.fetch_add(1, Ordering::Relaxed);
        self.warn_once(
            tool,
            "subprocess sandbox: tool declares spawns but not Sandbox::Subprocess — its spawns bypass the runner",
        );
    }

    fn warn_once(&self, tool: &str, message: &str) {
        if let Ok(mut warned) = self.warned.lock()
            && warned.insert(tool.to_string())
        {
            tracing::warn!(tool, "{message}");
        }
    }

    /// Read-only status for `/status`, `wm doctor`, and tests.
    #[must_use]
    pub fn status(&self) -> serde_json::Value {
        serde_json::json!({
            "active": self.is_active(),
            "runner": self.runner.as_ref().map(|r| r.path.display().to_string()),
            "source": self.runner.as_ref().map(|r| r.source.as_str()),
            "envelope": ENVELOPE_SCHEMA,
            "dispatches": self.dispatches.load(Ordering::Relaxed),
            "degraded": self.degraded.load(Ordering::Relaxed),
            "unconfined_spawns": self.unconfined_spawns.load(Ordering::Relaxed),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use wm_core::Resource;
    use wm_core::sandbox::RunnerSource;

    fn runner() -> RunnerInfo {
        RunnerInfo {
            path: PathBuf::from("/opt/mandala-sandbox"),
            source: RunnerSource::Env,
        }
    }

    fn declared_effects() -> EffectRow {
        EffectRow {
            reads: vec![Resource::Network, Resource::Process],
            spawns: true,
            sandbox: Sandbox::Subprocess,
            ..Default::default()
        }
    }

    #[test]
    fn declared_requires_the_subprocess_marker() {
        assert!(SubprocessSandbox::declared(&declared_effects()));
        let spawns_only = EffectRow {
            spawns: true,
            ..Default::default()
        };
        assert!(!SubprocessSandbox::declared(&spawns_only));
    }

    #[test]
    fn policy_derives_runner_and_net_grant() {
        let sb = SubprocessSandbox::with_runner(Some(runner()));
        let policy = sb.policy_for(&declared_effects());
        assert!(policy.is_active());
        assert!(policy.allow_net());
        assert_eq!(
            policy.runner(),
            Some(std::path::Path::new("/opt/mandala-sandbox"))
        );

        let local = EffectRow {
            reads: vec![Resource::Process],
            spawns: true,
            sandbox: Sandbox::Subprocess,
            ..Default::default()
        };
        assert!(!sb.policy_for(&local).allow_net());
    }

    #[test]
    fn missing_runner_degrades_but_still_builds_policy() {
        let sb = SubprocessSandbox::with_runner(None);
        let policy = sb.policy_for(&declared_effects());
        assert!(!policy.is_active());
        assert!(
            policy.allow_net(),
            "grant is declared, not runner-dependent"
        );
        sb.note_degraded("oss.bounty.scan");
        let status = sb.status();
        assert_eq!(status["active"], false);
        assert_eq!(status["dispatches"], 1);
        assert_eq!(status["degraded"], 1);
    }

    #[test]
    fn counters_are_separate() {
        let sb = SubprocessSandbox::with_runner(Some(runner()));
        sb.note_confined();
        sb.note_unconfined_spawn("session.record");
        let status = sb.status();
        assert_eq!(status["dispatches"], 1);
        assert_eq!(status["degraded"], 0);
        assert_eq!(status["unconfined_spawns"], 1);
        assert_eq!(status["source"], "env");
    }
}
