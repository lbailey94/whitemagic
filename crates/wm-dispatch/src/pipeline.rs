//! Dispatch pipeline — the request processing chain.
//!
//! Pipeline order:
//! 1. Effect check — brain-wave compatibility (zero-cost, inline)
//! 2. Dharma gate — ethical governance verdict
//! 3. Rate limit — sliding window per-tool + global
//! 4. Circuit breaker — fault tolerance, fast-fail on repeated errors
//! 5. Tool call — execute the tool
//! 6. Karma record — declared vs actual effects, SHA-256 chain to LMDB
//! 7. Stats — success/failure and latency tracking

use std::sync::Arc;
use std::time::Instant;
use wm_core::{Args, Context, CoreError, Output, Result, Tool};

use crate::circuit_breaker::CircuitBreakerRegistry;
use crate::rate_limiter::RateLimiter;
use wm_governance::{ActionVerdict, DharmaGate, KarmaLedger};

/// The dispatch pipeline processes tool calls through governance,
/// rate limiting, circuit breaking, and karma tracking before and after
/// the actual tool execution.
pub struct DispatchPipeline {
    rate_limiter: Arc<RateLimiter>,
    circuit_breakers: Arc<CircuitBreakerRegistry>,
    dharma_gate: Arc<DharmaGate>,
    karma_ledger: Option<Arc<KarmaLedger>>,
}

impl DispatchPipeline {
    /// Create a new dispatch pipeline with the given components.
    pub const fn new(
        rate_limiter: Arc<RateLimiter>,
        circuit_breakers: Arc<CircuitBreakerRegistry>,
        dharma_gate: Arc<DharmaGate>,
        karma_ledger: Option<Arc<KarmaLedger>>,
    ) -> Self {
        Self {
            rate_limiter,
            circuit_breakers,
            dharma_gate,
            karma_ledger,
        }
    }

    /// Create a pipeline with default components and no karma ledger.
    #[must_use]
    pub fn with_defaults() -> Self {
        Self::new(
            Arc::new(RateLimiter::default()),
            Arc::new(CircuitBreakerRegistry::default()),
            Arc::new(DharmaGate::default()),
            None,
        )
    }

    /// Dispatch a tool call through the full pipeline.
    pub fn dispatch(&self, tool: &dyn Tool, ctx: &mut Context, args: Args) -> Result<Output> {
        let start = Instant::now();

        // 1. Effect check — brain-wave compatibility
        if !tool.effects().is_available_in(ctx.brain_wave) {
            return Err(CoreError::Governance(format!(
                "tool '{}' not available in {:?} brain-wave state",
                tool.name(),
                ctx.brain_wave
            )));
        }

        // 1b. Coherence gate — refuse writes when citta coherence is low
        const COHERENCE_THRESHOLD: f32 = 0.3;
        if !tool.effects().writes.is_empty() && ctx.citta_coherence < COHERENCE_THRESHOLD {
            return Err(CoreError::Governance(format!(
                "tool '{}' requires write access but citta coherence is {:.2} (minimum {:.2})",
                tool.name(),
                ctx.citta_coherence,
                COHERENCE_THRESHOLD
            )));
        }

        // 1c. Self-model confidence — conservative dispatch when confidence is low
        const CONFIDENCE_THRESHOLD: f32 = 0.5;
        if ctx.self_model_confidence < CONFIDENCE_THRESHOLD {
            tracing::warn!(
                tool = tool.name(),
                confidence = ctx.self_model_confidence,
                "low self-model confidence — conservative dispatch mode"
            );
            // Block write operations when confidence is low — can't trust side effects
            if !tool.effects().writes.is_empty() {
                return Err(CoreError::Governance(format!(
                    "tool '{}' requires write access but self-model confidence is {:.2} (minimum {:.2}) — conservative dispatch blocks writes",
                    tool.name(),
                    ctx.self_model_confidence,
                    CONFIDENCE_THRESHOLD
                )));
            }
        }

        // 1d. Drive caution gate — warn on high-caution write operations
        const DRIVE_CAUTION_THRESHOLD: f32 = 0.85;
        if !tool.effects().writes.is_empty() && ctx.drive_caution > DRIVE_CAUTION_THRESHOLD {
            tracing::warn!(
                tool = tool.name(),
                drive_caution = ctx.drive_caution,
                "high drive caution — write operation flagged for review"
            );
        }

        // 1e. Drive energy gate — warn on low-energy write operations
        const DRIVE_ENERGY_THRESHOLD: f32 = 0.15;
        if !tool.effects().writes.is_empty() && ctx.drive_energy < DRIVE_ENERGY_THRESHOLD {
            tracing::warn!(
                tool = tool.name(),
                drive_energy = ctx.drive_energy,
                "low drive energy — write operation may be resource-constrained"
            );
        }

        // 2. Dharma gate — ethical governance
        let verdict = self.dharma_gate.evaluate(tool.effects(), ctx);
        match verdict {
            ActionVerdict::Panic(reason) => {
                tracing::error!(tool = tool.name(), reason = %reason, "Dharma PANIC");
                return Err(CoreError::Governance(reason));
            }
            ActionVerdict::Intervene(reason) => {
                tracing::warn!(tool = tool.name(), reason = %reason, "Dharma INTERVENE");
                return Err(CoreError::Governance(reason));
            }
            ActionVerdict::Correct(reason) => {
                tracing::info!(tool = tool.name(), reason = %reason, "Dharma CORRECT — proceeding with restrictions");
            }
            ActionVerdict::Advise(reason) => {
                tracing::debug!(tool = tool.name(), reason = %reason, "Dharma ADVISE");
            }
            ActionVerdict::Observe => {}
        }

        // 3. Rate limit
        if let Err(retry_after_ms) = self.rate_limiter.try_acquire(tool.name()) {
            return Err(CoreError::RateLimited(format!(
                "{}: retry after {}ms",
                tool.name(),
                retry_after_ms
            )));
        }

        // 4. Circuit breaker
        if self.circuit_breakers.is_open(tool.name()) {
            return Err(CoreError::CircuitBreaker(tool.name().to_string()));
        }

        // 4b. Destructive tool confirmation — requires explicit `confirm: true` in args
        if tool.effects().destructive {
            let confirmed = args
                .get("confirm")
                .and_then(serde_json::Value::as_bool)
                .unwrap_or(false);
            if !confirmed {
                return Err(CoreError::Governance(format!(
                    "tool '{}' is destructive — pass `\"confirm\": true` in args to proceed",
                    tool.name()
                )));
            }
        }

        // 4c. Compartment access control — check declared galaxy reads/writes
        //        plus runtime galaxy argument from tool args.
        //
        //        Tools like memory.read accept a `galaxy` argument at runtime that
        //        may differ from the default galaxy declared in their EffectRow.
        //        We check both the static declarations and the runtime argument
        //        to prevent compartment bypass via runtime galaxy selection.
        let mut checked_galaxies: Vec<wm_core::Galaxy> = Vec::new();

        for resource in &tool.effects().reads {
            if let wm_core::Resource::Galaxy(name) = resource {
                if let Some(galaxy) = wm_core::Galaxy::from_db_name(name) {
                    if !ctx.can_access_galaxy(galaxy) {
                        return Err(CoreError::Governance(format!(
                            "compartment '{}' cannot read galaxy '{}' (tool '{}')",
                            ctx.compartment.as_deref().unwrap_or("none"),
                            name,
                            tool.name()
                        )));
                    }
                    checked_galaxies.push(galaxy);
                }
            }
        }
        for resource in &tool.effects().writes {
            if let wm_core::Resource::Galaxy(name) = resource {
                if let Some(galaxy) = wm_core::Galaxy::from_db_name(name) {
                    if !ctx.can_write_galaxy(galaxy) {
                        return Err(CoreError::Governance(format!(
                            "compartment '{}' cannot write to galaxy '{}' (tool '{}')",
                            ctx.compartment.as_deref().unwrap_or("none"),
                            name,
                            tool.name()
                        )));
                    }
                    checked_galaxies.push(galaxy);
                }
            }
        }

        // Check runtime `galaxy` argument if present and not already checked
        if let Some(galaxy_str) = args.get("galaxy").and_then(serde_json::Value::as_str) {
            if !galaxy_str.is_empty() {
                if let Some(runtime_galaxy) = wm_core::Galaxy::from_db_name(galaxy_str) {
                    if !checked_galaxies.contains(&runtime_galaxy) {
                        // Determine if this is a read or write based on EffectRow writes
                        let has_writes = !tool.effects().writes.is_empty();
                        if has_writes {
                            if !ctx.can_write_galaxy(runtime_galaxy) {
                                return Err(CoreError::Governance(format!(
                                    "compartment '{}' cannot write to galaxy '{}' (tool '{}' runtime arg)",
                                    ctx.compartment.as_deref().unwrap_or("none"),
                                    galaxy_str,
                                    tool.name()
                                )));
                            }
                        } else if !ctx.can_access_galaxy(runtime_galaxy) {
                            return Err(CoreError::Governance(format!(
                                "compartment '{}' cannot read galaxy '{}' (tool '{}' runtime arg)",
                                ctx.compartment.as_deref().unwrap_or("none"),
                                galaxy_str,
                                tool.name()
                            )));
                        }
                    }
                }
            }
        }

        // 5. Tool call
        let result = tool.call(ctx, args);
        let elapsed = start.elapsed();

        // 6. Stats + circuit breaker feedback + karma record
        if let Ok(output) = &result {
            tool.stats().record_success(elapsed, elapsed);
            self.circuit_breakers.record_success(tool.name());

            if let Some(ref ledger) = self.karma_ledger {
                let declared_writes = !tool.effects().writes.is_empty();
                let actual_writes = output
                    .get("writes")
                    .and_then(|w| w.as_array())
                    .map_or(0, |a| a.len() as u32);
                if let Err(e) = ledger.record(tool.name(), declared_writes, actual_writes, true) {
                    tracing::warn!(error = %e, "Karma ledger record failed");
                }
                ctx.karma_debt = ledger.total_debt();
            }
        } else {
            tool.stats().record_failure(elapsed);
            self.circuit_breakers.record_failure(tool.name());

            if let Some(ref ledger) = self.karma_ledger {
                let declared_writes = !tool.effects().writes.is_empty();
                if let Err(ke) = ledger.record(tool.name(), declared_writes, 0, false) {
                    tracing::warn!(error = %ke, "Karma ledger record failed");
                }
                ctx.karma_debt = ledger.total_debt();
            }
        }

        result
    }

    /// Dispatch a tool by name, looking it up in a registry.
    ///
    /// Convenience method that combines registry lookup with pipeline dispatch.
    /// Returns `NotFound` if the tool isn't registered.
    pub fn dispatch_by_name(
        &self,
        registry: &crate::ToolRegistry,
        name: &str,
        ctx: &mut Context,
        args: Args,
    ) -> Result<Output> {
        let tool = registry
            .get(name)
            .ok_or_else(|| CoreError::NotFound(format!("tool '{name}' not registered")))?;
        self.dispatch(tool.as_ref(), ctx, args)
    }

    /// Access the rate limiter.
    #[must_use]
    pub fn rate_limiter(&self) -> &RateLimiter {
        &self.rate_limiter
    }

    /// Access the circuit breaker registry.
    #[must_use]
    pub fn circuit_breakers(&self) -> &CircuitBreakerRegistry {
        &self.circuit_breakers
    }

    /// Access the Dharma gate.
    #[must_use]
    pub fn dharma_gate(&self) -> &DharmaGate {
        &self.dharma_gate
    }

    /// Access the karma ledger (if configured).
    #[must_use]
    pub fn karma_ledger(&self) -> Option<&KarmaLedger> {
        self.karma_ledger.as_deref()
    }
}

impl Default for DispatchPipeline {
    fn default() -> Self {
        Self::with_defaults()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::{BrainWave, EffectRow, Gana, ToolStats};

    struct TestTool {
        name: String,
        effects: EffectRow,
        stats: ToolStats,
        should_fail: bool,
    }

    impl TestTool {
        fn new(name: &str, effects: EffectRow) -> Self {
            Self {
                name: name.to_string(),
                effects,
                stats: ToolStats::default(),
                should_fail: false,
            }
        }

        fn failing(name: &str) -> Self {
            Self {
                name: name.to_string(),
                effects: EffectRow::pure(),
                stats: ToolStats::default(),
                should_fail: true,
            }
        }
    }

    impl Tool for TestTool {
        fn name(&self) -> &str {
            &self.name
        }
        fn gana(&self) -> Gana {
            Gana::Heart
        }
        fn effects(&self) -> &EffectRow {
            &self.effects
        }
        fn call(&self, _ctx: &mut Context, _args: Args) -> Result<Output> {
            if self.should_fail {
                Err(CoreError::Tool(self.name.clone()))
            } else {
                Ok(serde_json::json!("ok"))
            }
        }
        fn stats(&self) -> &ToolStats {
            &self.stats
        }
    }

    #[test]
    fn pipeline_dispatch_success() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        let tool = TestTool::new("test_tool", EffectRow::pure());

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_dispatch_failure_records_stats() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        let tool = TestTool::failing("failing_tool");

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_err());
        assert_eq!(
            tool.stats()
                .call_count
                .load(std::sync::atomic::Ordering::Relaxed),
            1
        );
    }

    #[test]
    fn pipeline_blocks_incompatible_brain_wave() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Delta);
        let tool = TestTool::new("test_tool", EffectRow::pure());

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(_)) => {}
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_dharma_blocks_destructive_in_strict_mode() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Theta);
        let tool = TestTool::new(
            "destructive_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Filesystem],
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(_)) => {}
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_rate_limit_blocks_excess() {
        let rate_limiter = Arc::new(RateLimiter::new(1000, 2, 0));
        let pipeline = DispatchPipeline::new(
            rate_limiter,
            Arc::new(CircuitBreakerRegistry::default()),
            Arc::new(DharmaGate::default()),
            None,
        );

        let mut ctx = Context::new(BrainWave::Gamma);
        let tool = TestTool::new("limited_tool", EffectRow::pure());

        assert!(pipeline.dispatch(&tool, &mut ctx, Args::default()).is_ok());
        assert!(pipeline.dispatch(&tool, &mut ctx, Args::default()).is_ok());
        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_err());
        match result {
            Err(CoreError::RateLimited(_)) => {}
            other => panic!("Expected RateLimited error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_circuit_breaker_opens_on_repeated_failures() {
        let breakers = Arc::new(CircuitBreakerRegistry::new(
            crate::circuit_breaker::BreakerConfig {
                failure_threshold: 3,
                window: std::time::Duration::from_secs(10),
                cooldown: std::time::Duration::from_secs(30),
            },
        ));
        let pipeline = DispatchPipeline::new(
            Arc::new(RateLimiter::new(10000, 100, 100)),
            breakers.clone(),
            Arc::new(DharmaGate::default()),
            None,
        );

        let mut ctx = Context::new(BrainWave::Gamma);
        let tool = TestTool::failing("flaky_tool");

        for _ in 0..3 {
            let _ = pipeline.dispatch(&tool, &mut ctx, Args::default());
        }

        assert_eq!(
            breakers.state("flaky_tool"),
            crate::circuit_breaker::BreakerState::Open
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_err());
        match result {
            Err(CoreError::CircuitBreaker(_)) => {}
            other => panic!("Expected CircuitBreaker error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_karma_ledger_records() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(wm_memory::MemoryStore::open_default(tmp.path()).unwrap());
        let ledger = Arc::new(KarmaLedger::new(store).unwrap());

        let pipeline = DispatchPipeline::new(
            Arc::new(RateLimiter::default()),
            Arc::new(CircuitBreakerRegistry::default()),
            Arc::new(DharmaGate::default()),
            Some(ledger.clone()),
        );

        let mut ctx = Context::new(BrainWave::Gamma);
        let tool = TestTool::new("karma_test_tool", EffectRow::pure());

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
        assert_eq!(ledger.next_id(), 1);
        assert_eq!(ctx.karma_debt, 0.0);
    }

    #[test]
    fn pipeline_karma_debt_updates_context() {
        let tmp = tempfile::tempdir().unwrap();
        let store = Arc::new(wm_memory::MemoryStore::open_default(tmp.path()).unwrap());
        let ledger = Arc::new(KarmaLedger::new(store).unwrap());

        let pipeline = DispatchPipeline::new(
            Arc::new(RateLimiter::default()),
            Arc::new(CircuitBreakerRegistry::default()),
            Arc::new(DharmaGate::default()),
            Some(ledger),
        );

        let mut ctx = Context::new(BrainWave::Gamma);
        let tool = TestTool::new(
            "wasteful_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
        assert!(
            (ctx.karma_debt - 0.2).abs() < 0.001,
            "Context karma_debt should be 0.2, got {}",
            ctx.karma_debt
        );
    }

    #[test]
    fn pipeline_coherence_gate_blocks_writes() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.citta_coherence = 0.1; // Below 0.3 threshold
        let tool = TestTool::new(
            "write_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(msg)) => {
                assert!(msg.contains("coherence"));
            }
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_coherence_gate_allows_reads() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.citta_coherence = 0.1; // Below threshold, but no writes
        let tool = TestTool::new("read_tool", EffectRow::pure());

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_coherence_gate_allows_writes_when_coherent() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.citta_coherence = 0.5; // Above threshold
        let tool = TestTool::new(
            "write_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_low_confidence_blocks_writes() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.self_model_confidence = 0.3; // Below 0.5 threshold
        let tool = TestTool::new(
            "write_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(msg)) => {
                assert!(msg.contains("confidence"));
                assert!(msg.contains("conservative"));
            }
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_low_confidence_allows_reads() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.self_model_confidence = 0.3; // Below threshold, but no writes
        let tool = TestTool::new("read_tool", EffectRow::pure());

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_high_confidence_allows_writes() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.self_model_confidence = 0.8; // Above threshold
        let tool = TestTool::new(
            "write_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_high_caution_warns_on_writes() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.drive_caution = 0.9; // Above 0.85 threshold
        let tool = TestTool::new(
            "write_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        // Should still succeed — caution is a warning, not a block
        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_low_energy_warns_on_writes() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.drive_energy = 0.1; // Below 0.15 threshold
        let tool = TestTool::new(
            "write_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        // Should still succeed — low energy is a warning, not a block
        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_drive_gates_dont_affect_reads() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.drive_caution = 0.95;
        ctx.drive_energy = 0.05;
        let tool = TestTool::new("read_tool", EffectRow::pure());

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_destructive_blocked_without_confirm() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        let tool = TestTool::new(
            "destructive_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                destructive: true,
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, serde_json::json!({}));
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(msg)) => {
                assert!(msg.contains("destructive"));
                assert!(msg.contains("confirm"));
            }
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_destructive_allowed_with_confirm() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        let tool = TestTool::new(
            "destructive_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                destructive: true,
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, serde_json::json!({"confirm": true}));
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_destructive_blocked_with_false_confirm() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        let tool = TestTool::new(
            "destructive_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                destructive: true,
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, serde_json::json!({"confirm": false}));
        assert!(result.is_err());
    }

    #[test]
    fn pipeline_compartment_no_restriction_allows_all() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        // No compartment set — full access
        let tool = TestTool::new(
            "write_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_compartment_sandbox_blocks_write_to_codex() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("sandbox".into());
        let tool = TestTool::new(
            "write_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(msg)) => {
                assert!(msg.contains("sandbox"));
                assert!(msg.contains("codex"));
            }
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_compartment_sandbox_blocks_read_from_karma() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("sandbox".into());
        let tool = TestTool::new(
            "read_tool",
            EffectRow::read_only(vec![wm_core::Resource::Galaxy("karma".into())]),
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(msg)) => {
                assert!(msg.contains("sandbox"));
                assert!(msg.contains("karma"));
            }
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_compartment_sandbox_allows_write_to_tutorial() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("sandbox".into());
        let tool = TestTool::new(
            "write_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("tutorial".into())],
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_compartment_sandbox_allows_read_from_research() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("sandbox".into());
        let tool = TestTool::new(
            "read_tool",
            EffectRow::read_only(vec![wm_core::Resource::Galaxy("research".into())]),
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_compartment_production_blocks_read_from_karma() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("production".into());
        let tool = TestTool::new(
            "read_tool",
            EffectRow::read_only(vec![wm_core::Resource::Galaxy("karma".into())]),
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(msg)) => {
                assert!(msg.contains("production"));
                assert!(msg.contains("karma"));
            }
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_compartment_production_allows_write_to_codex() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("production".into());
        let tool = TestTool::new(
            "write_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_compartment_secure_allows_write_to_codex() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("secure".into());
        let tool = TestTool::new(
            "write_tool",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_compartment_secure_blocks_read_from_karma() {
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("secure".into());
        let tool = TestTool::new(
            "read_tool",
            EffectRow::read_only(vec![wm_core::Resource::Galaxy("karma".into())]),
        );

        let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(msg)) => {
                assert!(msg.contains("secure"));
                assert!(msg.contains("karma"));
            }
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    // ── Runtime galaxy argument enforcement tests ──────────────────────

    #[test]
    fn pipeline_compartment_production_blocks_runtime_galaxy_write_bypass() {
        // Tool declares writes to "codex" (allowed for production) but runtime
        // galaxy arg is "karma" — production should be blocked from writing karma.
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("production".into());
        let tool = TestTool::new(
            "memory_update",
            EffectRow {
                writes: vec![wm_core::Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        );

        let args = serde_json::json!({"galaxy": "karma"});
        let result = pipeline.dispatch(&tool, &mut ctx, args);
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(msg)) => {
                assert!(msg.contains("production"));
                assert!(msg.contains("karma"));
                assert!(msg.contains("runtime"));
            }
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_compartment_production_blocks_runtime_galaxy_read_bypass() {
        // Tool declares reads from "codex" (allowed for production) but runtime
        // galaxy arg is "karma" — production should be blocked from reading karma.
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("production".into());
        let tool = TestTool::new(
            "memory_read",
            EffectRow::read_only(vec![wm_core::Resource::Galaxy("codex".into())]),
        );

        let args = serde_json::json!({"galaxy": "karma"});
        let result = pipeline.dispatch(&tool, &mut ctx, args);
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(msg)) => {
                assert!(msg.contains("production"));
                assert!(msg.contains("karma"));
                assert!(msg.contains("runtime"));
            }
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    #[test]
    fn pipeline_compartment_production_allows_runtime_galaxy_same_as_declared() {
        // Tool declares reads from "codex" and runtime galaxy arg is also "codex"
        // — production should allow this (no duplicate check needed).
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("production".into());
        let tool = TestTool::new(
            "memory_read",
            EffectRow::read_only(vec![wm_core::Resource::Galaxy("codex".into())]),
        );

        let args = serde_json::json!({"galaxy": "codex"});
        let result = pipeline.dispatch(&tool, &mut ctx, args);
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_compartment_no_restriction_allows_runtime_galaxy() {
        // No compartment — runtime galaxy arg should be allowed regardless.
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        let tool = TestTool::new(
            "memory_read",
            EffectRow::read_only(vec![wm_core::Resource::Galaxy("codex".into())]),
        );

        let args = serde_json::json!({"galaxy": "karma"});
        let result = pipeline.dispatch(&tool, &mut ctx, args);
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_compartment_production_allows_runtime_memory_galaxy() {
        // Production compartment — runtime galaxy arg "codex" should be allowed
        // since production can access all memory galaxies.
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("production".into());
        let tool = TestTool::new(
            "memory_read",
            EffectRow::read_only(vec![wm_core::Resource::Galaxy("codex".into())]),
        );

        let args = serde_json::json!({"galaxy": "research"});
        let result = pipeline.dispatch(&tool, &mut ctx, args);
        assert!(result.is_ok());
    }

    #[test]
    fn pipeline_compartment_production_blocks_runtime_system_galaxy() {
        // Production compartment — runtime galaxy arg "karma" should be blocked
        // since production can't access system galaxies.
        let pipeline = DispatchPipeline::with_defaults();
        let mut ctx = Context::new(BrainWave::Gamma);
        ctx.compartment = Some("production".into());
        let tool = TestTool::new(
            "memory_read",
            EffectRow::read_only(vec![wm_core::Resource::Galaxy("codex".into())]),
        );

        let args = serde_json::json!({"galaxy": "karma"});
        let result = pipeline.dispatch(&tool, &mut ctx, args);
        assert!(result.is_err());
        match result {
            Err(CoreError::Governance(msg)) => {
                assert!(msg.contains("production"));
                assert!(msg.contains("karma"));
                assert!(msg.contains("runtime"));
            }
            other => panic!("Expected Governance error, got {other:?}"),
        }
    }

    #[test]
    fn benchmark_pipeline_overhead() {
        let pipeline = DispatchPipeline::with_defaults();
        let tool = TestTool::new("bench_tool", EffectRow::pure());
        let args = Args::default();

        // Warm up
        for _ in 0..100 {
            let mut ctx = Context::new(BrainWave::Gamma);
            let _ = pipeline.dispatch(&tool, &mut ctx, args.clone());
        }

        // Measure pipeline dispatch
        let n = 10_000;
        let start = std::time::Instant::now();
        for _ in 0..n {
            let mut ctx = Context::new(BrainWave::Gamma);
            let _ = pipeline.dispatch(&tool, &mut ctx, args.clone());
        }
        let pipeline_ns = start.elapsed().as_nanos() / n;

        // Measure direct tool call (no pipeline)
        let start = std::time::Instant::now();
        for _ in 0..n {
            let mut ctx = Context::new(BrainWave::Gamma);
            let _ = tool.call(&mut ctx, args.clone());
        }
        let direct_ns = start.elapsed().as_nanos() / n;

        let overhead_ns = pipeline_ns.saturating_sub(direct_ns);
        println!(
            "\n  Pipeline: {pipeline_ns} ns/call | Direct: {direct_ns} ns/call | Overhead: {overhead_ns} ns/call"
        );

        // Pipeline overhead should be under 5µs per call (5000 ns)
        // This is a sanity check, not a hard CI gate — adjust if hardware varies.
        assert!(
            overhead_ns < 5_000,
            "Pipeline overhead {overhead_ns} ns/call exceeds 5µs budget"
        );
    }
}
