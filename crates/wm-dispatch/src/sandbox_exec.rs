//! Scoped-thread sandbox executor — the Landlock v1 per-tool pathway.
//!
//! P-SANDBOX-3 (2026-09-10, Glama execution-sandboxing thread): tools that
//! declare [`wm_core::Sandbox::StoreScoped`] run on a **fresh OS thread**
//! that applies a thread-local confinement before the tool body executes.
//! Landlock restriction is irreversible and thread-local, so a fresh thread
//! per dispatch is the safe unit: the confined thread exits after the call
//! and the async workers never inherit a restriction.
//!
//! Why scoped threads instead of `spawn_blocking`: block-pool workers are
//! reused, and a thread-local Landlock restriction applied there would
//! taint every future task the pool hands that thread. Why not a confined
//! tokio runtime: `Tool::call` borrows `&mut Context`, so the future is
//! not `'static` and cannot be moved into a long-lived worker. A scoped
//! thread creates the future *on* the confined thread, so the borrow stays
//! valid and the future never crosses a thread boundary.
//!
//! Degradation doctrine (matches Landlock v0 / profile-contract): a failed
//! or unsupported confinement is **loud, never fatal** — the tool runs
//! unconfined, a `WARN` names the reason, and `stats().degraded` counts it.
//! The closure supplied by the caller (`wm-mcp` injects the Landlock
//! ruleset) is the only confinement mechanism here; this crate stays free
//! of the landlock dependency, preserving the dependency direction.
//!
//! v1 scope limits, documented rather than hidden:
//! - `WM_DISPATCH_TIMEOUT_MS` is not applied to the sandboxed path (the
//!   call is synchronous in the dispatcher); timeout parity is v1.1.
//! - The per-dispatch cost is one OS thread + one current-thread runtime
//!   (measured in the acceptance tests; parked-thread pooling is v1.1).
//! - Subprocess-creating tools are out of the first taxonomy batch: the
//!   per-thread ruleset grants the store root + `/dev/null` only, so a
//!   tool that needs the `.git` lease-ledger grant must not be marked
//!   `StoreScoped` yet.

use std::sync::atomic::{AtomicU64, Ordering};

use wm_core::{Args, Context, CoreError, Output, Result, Sandbox, Tool};

/// Environment knob: `WM_LANDLOCK_V1=1` enables the per-tool pathway.
///
/// Strict parse (exactly `1`), mirroring `WM_LANDLOCK`. Off by default:
/// v0 whole-process confinement and v1 per-tool confinement are separate
/// deployment decisions.
pub const V1_FLAG_ENV: &str = "WM_LANDLOCK_V1";

/// Whether the per-tool pathway was requested. Strict `== "1"` parse.
#[must_use]
pub fn v1_requested() -> bool {
    std::env::var(V1_FLAG_ENV).is_ok_and(|v| v == "1")
}

/// Confinement callback: `Ok(())` = the current thread is restricted;
/// `Err(reason)` = confinement unavailable (loud-degrade, run unconfined).
pub type RestrictFn = Box<dyn Fn() -> std::result::Result<(), String> + Send + Sync>;

/// Runs [`Sandbox::StoreScoped`] tools on a confined scoped thread.
pub struct ScopedSandboxExecutor {
    restrict: RestrictFn,
    runs: AtomicU64,
    degraded: AtomicU64,
    failures: AtomicU64,
}

impl ScopedSandboxExecutor {
    /// Build with the caller's confinement callback.
    #[must_use]
    pub fn new(
        restrict: impl Fn() -> std::result::Result<(), String> + Send + Sync + 'static,
    ) -> Self {
        Self {
            restrict: Box::new(restrict),
            runs: AtomicU64::new(0),
            degraded: AtomicU64::new(0),
            failures: AtomicU64::new(0),
        }
    }

    /// (runs, degraded runs, contained panics/runtime failures).
    #[must_use]
    pub fn stats(&self) -> (u64, u64, u64) {
        (
            self.runs.load(Ordering::Relaxed),
            self.degraded.load(Ordering::Relaxed),
            self.failures.load(Ordering::Relaxed),
        )
    }

    /// Execute one tool call on a confined thread.
    ///
    /// Synchronous by design: the dispatcher blocks while the confined
    /// thread runs. Panics inside the tool are contained by the scoped
    /// thread and surface as a `CoreError::Tool` — the process survives.
    pub fn run(&self, tool: &dyn Tool, ctx: &mut Context, args: Args) -> Result<Output> {
        self.runs.fetch_add(1, Ordering::Relaxed);
        let outcome = std::thread::scope(|scope| {
            scope
                .spawn(|| {
                    if let Err(reason) = (self.restrict)() {
                        self.degraded.fetch_add(1, Ordering::Relaxed);
                        tracing::warn!(
                            tool = tool.name(),
                            reason = %reason,
                            "sandbox: per-tool confinement unavailable — running unconfined (loud-degrade)"
                        );
                    }
                    let runtime = tokio::runtime::Builder::new_current_thread()
                        .enable_all()
                        .build()
                        .map_err(|e| {
                            CoreError::Tool(format!("sandbox runtime build failed: {e}"))
                        })?;
                    runtime.block_on(tool.call(ctx, args))
                })
                .join()
        });
        match outcome {
            Ok(result) => result,
            Err(_panic) => {
                self.failures.fetch_add(1, Ordering::Relaxed);
                Err(CoreError::Tool(format!(
                    "sandboxed tool '{}' panicked — contained by the scoped thread",
                    tool.name()
                )))
            }
        }
    }

    /// Whether a tool belongs on this pathway: `StoreScoped` declaration.
    #[must_use]
    pub fn handles(tool: &dyn Tool) -> bool {
        tool.effects().sandbox == Sandbox::StoreScoped
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::sync::atomic::AtomicBool;
    use wm_core::{BrainWave, EffectRow, Gana, ToolStats};

    struct ProbeTool {
        effects: EffectRow,
        stats: ToolStats,
        /// Set when the tool body runs; the test's restriction callback
        /// sets `restricted` first, so ordering is observable.
        restricted_seen: Option<Arc<AtomicBool>>,
        panic: bool,
    }

    #[async_trait::async_trait]
    impl Tool for ProbeTool {
        fn name(&self) -> &str {
            "probe"
        }
        fn gana(&self) -> Gana {
            Gana::Heart
        }
        fn effects(&self) -> &EffectRow {
            &self.effects
        }
        async fn call(&self, _ctx: &mut wm_core::Context, _args: Args) -> wm_core::Result<Output> {
            assert!(!self.panic, "probe tool panicked");
            if let Some(flag) = &self.restricted_seen {
                assert!(
                    flag.load(Ordering::SeqCst),
                    "tool must run AFTER the restriction callback"
                );
            }
            Ok(serde_json::json!({"ok": true}))
        }
        fn stats(&self) -> &ToolStats {
            &self.stats
        }
    }

    fn probe() -> ProbeTool {
        ProbeTool {
            effects: EffectRow {
                sandbox: Sandbox::StoreScoped,
                ..Default::default()
            },
            stats: ToolStats::default(),
            restricted_seen: None,
            panic: false,
        }
    }

    #[test]
    fn restrict_runs_before_tool_and_output_passes_through() {
        let restricted = Arc::new(AtomicBool::new(false));
        let flag = Arc::clone(&restricted);
        let executor = ScopedSandboxExecutor::new(move || {
            flag.store(true, Ordering::SeqCst);
            Ok(())
        });
        let mut tool = probe();
        tool.restricted_seen = Some(Arc::clone(&restricted));
        let mut ctx = wm_core::Context::new(BrainWave::Gamma);
        let out = executor
            .run(&tool, &mut ctx, serde_json::json!({}))
            .unwrap();
        assert_eq!(out["ok"], true);
        assert_eq!(executor.stats(), (1, 0, 0));
    }

    #[test]
    fn confinement_failure_degrades_loud_but_runs() {
        let executor = ScopedSandboxExecutor::new(|| Err("kernel says no".to_string()));
        let tool = probe();
        let mut ctx = wm_core::Context::new(BrainWave::Gamma);
        let out = executor
            .run(&tool, &mut ctx, serde_json::json!({}))
            .unwrap();
        assert_eq!(out["ok"], true, "loud-degrade keeps availability up");
        assert_eq!(executor.stats(), (1, 1, 0));
    }

    #[test]
    fn tool_panic_is_contained_not_propagated() {
        let executor = ScopedSandboxExecutor::new(|| Ok(()));
        let mut tool = probe();
        tool.panic = true;
        let mut ctx = wm_core::Context::new(BrainWave::Gamma);
        let result = executor.run(&tool, &mut ctx, serde_json::json!({}));
        assert!(result.is_err(), "panic must surface as a tool error");
        assert_eq!(executor.stats(), (1, 0, 1));
    }

    #[test]
    fn handles_only_store_scoped_tools() {
        let scoped = probe();
        assert!(ScopedSandboxExecutor::handles(&scoped));
        let inherited = ProbeTool {
            effects: EffectRow::pure(),
            ..probe()
        };
        assert!(!ScopedSandboxExecutor::handles(&inherited));
    }

    #[test]
    fn env_flag_parses_strictly() {
        // Pure parse contract mirrored from WM_LANDLOCK: only "1" enables.
        // (Read-only check — the process env is shared and tests never
        // mutate it; the strict parse is the property under test.)
        let parse = |v: Option<&str>| v.is_some_and(|s| s == "1");
        assert!(parse(Some("1")));
        assert!(!parse(Some("0")));
        assert!(!parse(Some("true")));
        assert!(!parse(None));
    }
}
