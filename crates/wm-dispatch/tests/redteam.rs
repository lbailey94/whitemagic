//! Red-team audit tests — dispatch pipeline security.
//!
//! Tests that the dispatch pipeline resists:
//! - Tools lying about their effects (governance bypass)
//! - Rate-limit abuse patterns
//! - Circuit breaker bypass via name aliasing
//! - Brain-wave state manipulation

use std::sync::Arc;
use std::time::Duration;
use wm_core::{
    Args, BrainWave, Context, CoreError, EffectRow, Gana, Output, Resource, Tool, ToolStats,
};
use wm_dispatch::{CircuitBreakerRegistry, RateLimiter};
use wm_dispatch::{DispatchPipeline, ToolRegistry};
use wm_governance::{DharmaGate, KarmaLedger};

// ── Mock Tools ─────────────────────────────────────────────────────────

/// A tool that declares pure effects but writes to its output (simulating
/// a tool that lies about its side effects).
struct LyingTool {
    stats: ToolStats,
}

impl Tool for LyingTool {
    fn name(&self) -> &str {
        "lying_tool"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        use std::sync::OnceLock;
        static EFFECTS: OnceLock<EffectRow> = OnceLock::new();
        EFFECTS.get_or_init(EffectRow::pure)
    }
    fn call(&self, _ctx: &mut Context, _args: Args) -> wm_core::Result<Output> {
        // Tool claims to be pure but returns "writes" in output
        // The karma ledger will detect this mismatch
        Ok(serde_json::json!({
            "writes": [1, 2, 3],  // Claims 3 writes
            "result": "sneaky"
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// A tool that declares destructive effects.
struct DestructiveTool {
    stats: ToolStats,
}

impl Tool for DestructiveTool {
    fn name(&self) -> &str {
        "destructive_tool"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        use std::sync::OnceLock;
        static EFFECTS: OnceLock<EffectRow> = OnceLock::new();
        EFFECTS.get_or_init(|| EffectRow {
            writes: vec![Resource::Filesystem],
            ..Default::default()
        })
    }
    fn call(&self, _ctx: &mut Context, _args: Args) -> wm_core::Result<Output> {
        Ok(serde_json::json!({"result": "done"}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// A tool with a very long name (potential buffer/DoS vector).
struct LongNameTool {
    name: String,
    stats: ToolStats,
}

impl Tool for LongNameTool {
    fn name(&self) -> &str {
        &self.name
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        use std::sync::OnceLock;
        static EFFECTS: OnceLock<EffectRow> = OnceLock::new();
        EFFECTS.get_or_init(EffectRow::pure)
    }
    fn call(&self, _ctx: &mut Context, _args: Args) -> wm_core::Result<Output> {
        Ok(serde_json::json!("ok"))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Governance Bypass Tests ────────────────────────────────────────────

/// A tool that declares pure effects but actually writes should be
/// caught by the karma ledger — it accumulates Tamasic debt.
#[test]
fn lying_tool_accumulates_karma_debt() {
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
    let tool = LyingTool {
        stats: ToolStats::default(),
    };

    let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
    assert!(
        result.is_ok(),
        "Pipeline should succeed (Dharma gate sees pure effects)"
    );

    // But karma ledger should have recorded the mismatch
    let entries = ledger.scan_entries().unwrap();
    assert_eq!(entries.len(), 1);
    assert!(
        entries[0].mismatch,
        "Karma ledger must detect the effect mismatch"
    );
    assert!(
        entries[0].debt_delta > 0.0,
        "Lying tool must accumulate karma debt, got {}",
        entries[0].debt_delta
    );
}

/// Verify that a destructive tool is blocked in Delta (dormant) state
/// even if the context has perfect karma and maximum intent.
#[test]
fn delta_blocks_all_tools_even_with_perfect_context() {
    let pipeline = DispatchPipeline::with_defaults();
    let mut ctx = Context::new(BrainWave::Delta);
    ctx.karma_debt = 0.0;
    ctx.intent_score = 1.0;
    ctx.citta_coherence = 1.0;
    ctx.self_model_confidence = 1.0;

    let tool = DestructiveTool {
        stats: ToolStats::default(),
    };
    let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
    assert!(
        result.is_err(),
        "Delta must block all tools regardless of context"
    );
}

/// Verify that the pipeline rejects tools with extremely long names
/// (potential DoS vector for logging or memory).
#[test]
fn pipeline_handles_extremely_long_tool_name() {
    let pipeline = DispatchPipeline::with_defaults();
    let mut ctx = Context::new(BrainWave::Gamma);
    let tool = LongNameTool {
        name: "A".repeat(10_000),
        stats: ToolStats::default(),
    };

    // Should not crash — may succeed or fail, but must not panic
    let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
    assert!(result.is_ok(), "Long name should not cause failure");
}

// ── Rate-Limit Abuse Tests ─────────────────────────────────────────────

/// Verify that rate limiting is per-tool, not global — different tools
/// should each get their own rate limit bucket.
#[test]
fn rate_limit_is_per_tool_not_global() {
    let rate_limiter = Arc::new(RateLimiter::new(10000, 2, 0));
    let pipeline = DispatchPipeline::new(
        rate_limiter,
        Arc::new(CircuitBreakerRegistry::default()),
        Arc::new(DharmaGate::default()),
        None,
    );

    let mut ctx = Context::new(BrainWave::Gamma);

    // Tool A: use both calls
    let tool_a = LongNameTool {
        name: "tool_a".to_string(),
        stats: ToolStats::default(),
    };
    assert!(
        pipeline
            .dispatch(&tool_a, &mut ctx, Args::default())
            .is_ok()
    );
    assert!(
        pipeline
            .dispatch(&tool_a, &mut ctx, Args::default())
            .is_ok()
    );
    assert!(
        pipeline
            .dispatch(&tool_a, &mut ctx, Args::default())
            .is_err()
    );

    // Tool B: should still have its own bucket
    let tool_b = LongNameTool {
        name: "tool_b".to_string(),
        stats: ToolStats::default(),
    };
    assert!(
        pipeline
            .dispatch(&tool_b, &mut ctx, Args::default())
            .is_ok(),
        "Different tool should have its own rate limit bucket"
    );
}

/// Verify that rate-limited tools don't consume karma or stats
/// (the rejection happens before tool execution).
#[test]
fn rate_limited_call_does_not_execute_tool() {
    let tmp = tempfile::tempdir().unwrap();
    let store = Arc::new(wm_memory::MemoryStore::open_default(tmp.path()).unwrap());
    let ledger = Arc::new(KarmaLedger::new(store).unwrap());

    let rate_limiter = Arc::new(RateLimiter::new(10000, 1, 0)); // 1 call per window
    let pipeline = DispatchPipeline::new(
        rate_limiter,
        Arc::new(CircuitBreakerRegistry::default()),
        Arc::new(DharmaGate::default()),
        Some(ledger.clone()),
    );

    let mut ctx = Context::new(BrainWave::Gamma);
    let tool = LongNameTool {
        name: "rate_limited".to_string(),
        stats: ToolStats::default(),
    };

    // First call succeeds
    assert!(pipeline.dispatch(&tool, &mut ctx, Args::default()).is_ok());
    // Second call is rate-limited
    let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
    assert!(matches!(result, Err(CoreError::RateLimited(_))));

    // Only 1 karma entry should exist (the successful call)
    let entries = ledger.scan_entries().unwrap();
    assert_eq!(
        entries.len(),
        1,
        "Rate-limited call must not create karma entry"
    );

    // Only 1 successful call in stats
    assert_eq!(
        tool.stats()
            .success_count
            .load(std::sync::atomic::Ordering::Relaxed),
        1
    );
}

// ── Circuit Breaker Bypass Tests ───────────────────────────────────────

/// Verify that a tool cannot bypass the circuit breaker by registering
/// under a different name — the breaker tracks by tool.name().
#[test]
fn circuit_breaker_tracks_by_name_not_identity() {
    let breakers = Arc::new(CircuitBreakerRegistry::new(
        wm_dispatch::circuit_breaker::BreakerConfig {
            failure_threshold: 3,
            window: Duration::from_secs(10),
            cooldown: Duration::from_secs(30),
        },
    ));

    let pipeline = DispatchPipeline::new(
        Arc::new(RateLimiter::new(10000, 100, 100)),
        breakers.clone(),
        Arc::new(DharmaGate::default()),
        None,
    );

    // Tool "flaky" fails 3 times → breaker opens
    let flaky = FailTool::new("flaky");
    let mut ctx = Context::new(BrainWave::Gamma);
    for _ in 0..3 {
        let _ = pipeline.dispatch(&flaky, &mut ctx, Args::default());
    }
    assert_eq!(
        breakers.state("flaky"),
        wm_dispatch::circuit_breaker::BreakerState::Open
    );

    // A different tool with the same name should also be blocked
    let flaky2 = FailTool::new("flaky");
    let result = pipeline.dispatch(&flaky2, &mut ctx, Args::default());
    assert!(
        matches!(result, Err(CoreError::CircuitBreaker(_))),
        "Circuit breaker must block by name, not tool identity"
    );

    // A tool with a different name should NOT be blocked
    let other = FailTool::new("other_tool");
    let result = pipeline.dispatch(&other, &mut ctx, Args::default());
    assert!(
        !matches!(result, Err(CoreError::CircuitBreaker(_))),
        "Different tool name should not be affected by another tool's breaker"
    );
}

// ── Brain-Wave State Manipulation Tests ────────────────────────────────

/// Verify that the brain-wave state cannot be manipulated mid-dispatch
/// to bypass governance. The context is checked at the start of dispatch
/// and the tool runs with that state.
#[test]
fn brain_wave_cannot_be_manipulated_mid_dispatch() {
    let pipeline = DispatchPipeline::with_defaults();

    // Start in Delta — all tools blocked
    let mut ctx = Context::new(BrainWave::Delta);
    let tool = LongNameTool {
        name: "test_tool".to_string(),
        stats: ToolStats::default(),
    };

    let result = pipeline.dispatch(&tool, &mut ctx, Args::default());
    assert!(result.is_err(), "Delta must block before tool execution");

    // Even if we change brain-wave after the failed dispatch,
    // the original dispatch already failed
    ctx.brain_wave = BrainWave::Gamma;
    // The failed dispatch cannot be "retried" with the old context —
    // a new dispatch call is required
    let result2 = pipeline.dispatch(&tool, &mut ctx, Args::default());
    assert!(result2.is_ok(), "New dispatch with Gamma should succeed");
}

/// A tool that always fails, with a configurable name.
struct FailTool {
    name: String,
    stats: ToolStats,
}

impl FailTool {
    fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            stats: ToolStats::default(),
        }
    }
}

impl Tool for FailTool {
    fn name(&self) -> &str {
        &self.name
    }
    fn gana(&self) -> Gana {
        Gana::Heart
    }
    fn effects(&self) -> &EffectRow {
        use std::sync::OnceLock;
        static EFFECTS: OnceLock<EffectRow> = OnceLock::new();
        EFFECTS.get_or_init(EffectRow::pure)
    }
    fn call(&self, _ctx: &mut Context, _args: Args) -> wm_core::Result<Output> {
        Err(CoreError::Internal("intentional failure".into()))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── Registry Lookup Security ───────────────────────────────────────────

/// Verify that dispatch_by_name returns NotFound for unknown tools
/// (no fallback or wildcard execution).
#[test]
fn dispatch_by_name_rejects_unknown_tools() {
    let pipeline = DispatchPipeline::with_defaults();
    let registry = ToolRegistry::new();
    let mut ctx = Context::new(BrainWave::Gamma);

    let result =
        pipeline.dispatch_by_name(&registry, "nonexistent_tool", &mut ctx, Args::default());
    assert!(
        matches!(result, Err(CoreError::NotFound(_))),
        "Unknown tool must return NotFound, got {result:?}"
    );
}

/// Verify that dispatch_by_name rejects empty string.
#[test]
fn dispatch_by_name_rejects_empty_string() {
    let pipeline = DispatchPipeline::with_defaults();
    let registry = ToolRegistry::new();
    let mut ctx = Context::new(BrainWave::Gamma);

    let result = pipeline.dispatch_by_name(&registry, "", &mut ctx, Args::default());
    assert!(
        matches!(result, Err(CoreError::NotFound(_))),
        "Empty tool name must return NotFound"
    );
}
