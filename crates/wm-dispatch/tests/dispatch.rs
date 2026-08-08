//! Integration tests for the tool trait, stats tracking, and dispatch pipeline.
//!
//! These tests verify that:
//! - ToolStats atomically records success/failure
//! - Retirement and promotion thresholds work correctly
//! - The dispatch pipeline records stats after tool calls
//! - The tool registry routes by Gana and name

use async_trait::async_trait;
use std::sync::Arc;
use std::time::Duration;
use wm_core::{Args, Context, CoreError, EffectRow, Gana, Output, Tool, ToolStats};
use wm_dispatch::{DispatchPipeline, ToolRegistry};

// ── Mock Tool ─────────────────────────────────────────────────────────

/// A minimal tool for testing that always succeeds.
struct EchoTool {
    stats: ToolStats,
}

impl EchoTool {
    fn new() -> Self {
        Self {
            stats: ToolStats::default(),
        }
    }
}

#[async_trait]
impl Tool for EchoTool {
    fn name(&self) -> &str {
        "test.echo"
    }
    fn gana(&self) -> Gana {
        Gana::Horn
    }
    fn effects(&self) -> &EffectRow {
        // Return a static pure effect row
        use std::sync::OnceLock;
        static EFFECTS: OnceLock<EffectRow> = OnceLock::new();
        EFFECTS.get_or_init(EffectRow::pure)
    }
    async fn call(&self, _ctx: &mut Context, args: Args) -> wm_core::Result<Output> {
        Ok(args)
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// A tool that always fails.
struct FailTool {
    stats: ToolStats,
}

impl FailTool {
    fn new() -> Self {
        Self {
            stats: ToolStats::default(),
        }
    }
}

#[async_trait]
impl Tool for FailTool {
    fn name(&self) -> &str {
        "test.fail"
    }
    fn gana(&self) -> Gana {
        Gana::Heart
    }
    fn effects(&self) -> &EffectRow {
        use std::sync::OnceLock;
        static EFFECTS: OnceLock<EffectRow> = OnceLock::new();
        EFFECTS.get_or_init(EffectRow::pure)
    }
    async fn call(&self, _ctx: &mut Context, _args: Args) -> wm_core::Result<Output> {
        Err(CoreError::Internal("intentional failure".into()))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── ToolStats Tests ───────────────────────────────────────────────────

#[tokio::test]
async fn stats_record_success_increments_counters() {
    let stats = ToolStats::default();
    stats.record_success(Duration::from_millis(5), Duration::from_millis(3));
    assert_eq!(
        stats.call_count.load(std::sync::atomic::Ordering::Relaxed),
        1
    );
    assert_eq!(
        stats
            .success_count
            .load(std::sync::atomic::Ordering::Relaxed),
        1
    );
    assert_eq!(stats.success_rate(), 1.0);
}

#[tokio::test]
async fn stats_record_failure_increments_call_but_not_success() {
    let stats = ToolStats::default();
    stats.record_success(Duration::from_millis(5), Duration::from_millis(3));
    stats.record_failure(Duration::from_millis(2));
    assert_eq!(
        stats.call_count.load(std::sync::atomic::Ordering::Relaxed),
        2
    );
    assert_eq!(
        stats
            .success_count
            .load(std::sync::atomic::Ordering::Relaxed),
        1
    );
    assert_eq!(stats.success_rate(), 0.5);
}

#[tokio::test]
async fn stats_success_rate_is_one_when_no_calls() {
    let stats = ToolStats::default();
    assert_eq!(
        stats.success_rate(),
        1.0,
        "No calls should show 100% success rate"
    );
}

#[tokio::test]
async fn stats_should_retire_after_threshold_with_low_effectiveness() {
    let stats = ToolStats::default();
    // 1 success + 14 failures = ~0.067 effectiveness (< 0.2 threshold)
    stats.record_success(Duration::from_millis(1), Duration::from_millis(1));
    for _ in 0..14 {
        stats.record_failure(Duration::from_millis(1));
    }
    assert!(
        stats.should_retire(10, 0.2),
        "Should retire with low effectiveness after 15 calls"
    );
}

#[tokio::test]
async fn stats_should_not_retire_below_min_calls() {
    let stats = ToolStats::default();
    stats.record_failure(Duration::from_millis(1));
    assert!(
        !stats.should_retire(10, 0.2),
        "Should not retire with only 1 call"
    );
}

#[tokio::test]
async fn stats_should_not_retire_with_high_effectiveness() {
    let stats = ToolStats::default();
    for _ in 0..20 {
        stats.record_success(Duration::from_millis(1), Duration::from_millis(1));
    }
    assert!(
        !stats.should_retire(10, 0.2),
        "Should not retire with 100% success rate after 20 calls"
    );
}

#[tokio::test]
async fn stats_is_hot_after_call_threshold() {
    let stats = ToolStats::default();
    for _ in 0..1001 {
        stats.record_success(Duration::from_micros(100), Duration::from_micros(50));
    }
    assert!(stats.is_hot(1000), "1001 calls should be hot");
    assert!(
        !stats.is_hot(2000),
        "1001 calls should not be hot at threshold 2000"
    );
}

#[tokio::test]
async fn stats_snapshot_captures_all_fields() {
    let stats = ToolStats::default();
    stats.record_success(Duration::from_millis(10), Duration::from_millis(5));
    let snap = stats.snapshot();
    assert_eq!(snap.call_count, 1);
    assert_eq!(snap.success_count, 1);
    // effectiveness auto-updates from success rate: 1/1 = 1.0
    assert!((snap.effectiveness - 1.0).abs() < 0.01);
}

// ── DispatchPipeline Tests ────────────────────────────────────────────

#[tokio::test]
async fn pipeline_dispatch_success_records_stats() {
    let pipeline = DispatchPipeline::with_defaults();
    let tool = EchoTool::new();
    let mut ctx = Context::default();
    let args = serde_json::json!({"message": "hello"});

    let result = pipeline
        .dispatch(&tool, &mut ctx, args.clone())
        .await
        .unwrap();
    assert_eq!(result, args);
    assert_eq!(
        tool.stats
            .call_count
            .load(std::sync::atomic::Ordering::Relaxed),
        1
    );
    assert_eq!(
        tool.stats
            .success_count
            .load(std::sync::atomic::Ordering::Relaxed),
        1
    );
}

#[tokio::test]
async fn pipeline_dispatch_failure_records_stats() {
    let pipeline = DispatchPipeline::with_defaults();
    let tool = FailTool::new();
    let mut ctx = Context::default();

    let result = pipeline
        .dispatch(&tool, &mut ctx, serde_json::json!({}))
        .await;
    assert!(result.is_err());
    assert_eq!(
        tool.stats
            .call_count
            .load(std::sync::atomic::Ordering::Relaxed),
        1
    );
    assert_eq!(
        tool.stats
            .success_count
            .load(std::sync::atomic::Ordering::Relaxed),
        0
    );
}

// ── ToolRegistry Tests ────────────────────────────────────────────────

#[tokio::test]
async fn registry_register_and_lookup_by_name() {
    let mut registry = ToolRegistry::new();
    let tool = Arc::new(EchoTool::new());
    registry = registry.register(tool);

    assert_eq!(registry.len(), 1);
    assert!(registry.get("test.echo").is_some());
    assert!(registry.get("nonexistent").is_none());
}

#[tokio::test]
async fn registry_lookup_by_gana() {
    let mut registry = ToolRegistry::new();
    let echo = Arc::new(EchoTool::new());
    let fail = Arc::new(FailTool::new());
    registry = registry.register(echo);
    registry = registry.register(fail);

    let horn_tools = registry.by_gana(Gana::Horn);
    let heart_tools = registry.by_gana(Gana::Heart);
    assert_eq!(horn_tools.len(), 1);
    assert_eq!(heart_tools.len(), 1);
    assert_eq!(horn_tools[0].name(), "test.echo");
    assert_eq!(heart_tools[0].name(), "test.fail");
}

#[tokio::test]
async fn registry_empty_gana_returns_empty_vec() {
    let registry = ToolRegistry::new();
    assert!(registry.by_gana(Gana::Wall).is_empty());
}

#[tokio::test]
async fn registry_all_returns_all_tools() {
    let mut registry = ToolRegistry::new();
    registry = registry.register(Arc::new(EchoTool::new()));
    registry = registry.register(Arc::new(FailTool::new()));
    assert_eq!(registry.all().len(), 2);
}

#[tokio::test]
async fn registry_is_empty_check() {
    let registry = ToolRegistry::new();
    assert!(registry.is_empty());
}

// ── Context Tests ─────────────────────────────────────────────────────

#[tokio::test]
async fn context_scratchpad_set_and_get() {
    let mut ctx = Context::default();
    ctx.set("key1", serde_json::json!(42));
    ctx.set("key2", serde_json::json!("hello"));
    assert_eq!(ctx.get("key1"), Some(&serde_json::json!(42)));
    assert_eq!(ctx.get("key2"), Some(&serde_json::json!("hello")));
    assert_eq!(ctx.get("missing"), None);
}

#[tokio::test]
async fn context_brain_wave_reflects_construction() {
    let ctx = Context::new(wm_core::BrainWave::Gamma);
    assert_eq!(ctx.brain_wave(), wm_core::BrainWave::Gamma);

    let ctx2 = Context::new(wm_core::BrainWave::Delta);
    assert_eq!(ctx2.brain_wave(), wm_core::BrainWave::Delta);
}

// ── Brain-Wave Tool Filtering Tests ───────────────────────────────────

/// A tool with write effects (not available in Alpha/Theta/Delta).
struct WriteTool {
    stats: ToolStats,
}

impl WriteTool {
    fn new() -> Self {
        Self {
            stats: ToolStats::default(),
        }
    }
}

#[async_trait]
impl Tool for WriteTool {
    fn name(&self) -> &str {
        "test.write"
    }
    fn gana(&self) -> Gana {
        Gana::Encampment
    }
    fn effects(&self) -> &EffectRow {
        use std::sync::OnceLock;
        static EFFECTS: OnceLock<EffectRow> = OnceLock::new();
        EFFECTS.get_or_init(|| EffectRow {
            writes: vec![wm_core::Resource::Galaxy("codex".into())],
            ..Default::default()
        })
    }
    async fn call(&self, _ctx: &mut Context, _args: Args) -> wm_core::Result<Output> {
        Ok(serde_json::json!({"status": "ok"}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[tokio::test]
async fn registry_available_in_gamma_returns_all() {
    let mut registry = ToolRegistry::new();
    registry = registry.register(Arc::new(EchoTool::new()));
    registry = registry.register(Arc::new(WriteTool::new()));

    let available = registry.available_in(wm_core::BrainWave::Gamma);
    assert_eq!(available.len(), 2);
}

#[tokio::test]
async fn registry_available_in_alpha_excludes_writes() {
    let mut registry = ToolRegistry::new();
    registry = registry.register(Arc::new(EchoTool::new()));
    registry = registry.register(Arc::new(WriteTool::new()));

    let available = registry.available_in(wm_core::BrainWave::Alpha);
    assert_eq!(available.len(), 1);
    assert_eq!(available[0].name(), "test.echo");
}

#[tokio::test]
async fn registry_available_in_delta_returns_none() {
    let mut registry = ToolRegistry::new();
    registry = registry.register(Arc::new(EchoTool::new()));
    registry = registry.register(Arc::new(WriteTool::new()));

    let available = registry.available_in(wm_core::BrainWave::Delta);
    assert_eq!(available.len(), 0);
}

#[tokio::test]
async fn registry_available_count_matches() {
    let mut registry = ToolRegistry::new();
    registry = registry.register(Arc::new(EchoTool::new()));
    registry = registry.register(Arc::new(WriteTool::new()));

    assert_eq!(registry.available_count(wm_core::BrainWave::Gamma), 2);
    assert_eq!(registry.available_count(wm_core::BrainWave::Alpha), 1);
    assert_eq!(registry.available_count(wm_core::BrainWave::Delta), 0);
}
