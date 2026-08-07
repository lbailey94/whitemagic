//! Dispatch pipeline benchmark — measures pipeline overhead per tool call.

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;
use std::sync::Arc;
use std::time::Duration;
use tempfile::tempdir;
use wm_core::{Args, BrainWave, Context, EffectRow, Gana, Tool, ToolStats};
use wm_dispatch::{DispatchPipeline, ToolRegistry};
use wm_governance::DharmaGate;
use wm_memory::MemoryStore;

struct NoopTool {
    effects: EffectRow,
    stats: ToolStats,
}

impl NoopTool {
    fn new() -> Self {
        Self {
            effects: EffectRow::default(),
            stats: ToolStats::default(),
        }
    }
}

impl Tool for NoopTool {
    fn name(&self) -> &str {
        "noop"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn call(&self, _ctx: &mut Context, _args: Args) -> wm_core::Result<serde_json::Value> {
        Ok(serde_json::json!({"status": "ok"}))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

fn bench_pipeline_dispatch(c: &mut Criterion) {
    let tmp = tempdir().unwrap();
    let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
    let karma_ledger = Arc::new(wm_governance::KarmaLedger::new(store).unwrap());
    let dharma_gate = Arc::new(DharmaGate::default());

    let pipeline = DispatchPipeline::new(
        Arc::new(wm_dispatch::RateLimiter::new(u64::MAX, u64::MAX, u64::MAX)),
        Arc::new(wm_dispatch::CircuitBreakerRegistry::default()),
        dharma_gate,
        Some(karma_ledger),
    );

    let tool = NoopTool::new();
    let mut ctx = Context::new(BrainWave::Gamma);

    c.bench_function("dispatch_noop_with_karma", |b| {
        b.iter(|| {
            let result = pipeline
                .dispatch(&tool, &mut ctx, black_box(serde_json::json!({})))
                .unwrap();
            black_box(result);
        });
    });

    let pipeline_no_karma = DispatchPipeline::new(
        Arc::new(wm_dispatch::RateLimiter::new(u64::MAX, u64::MAX, u64::MAX)),
        Arc::new(wm_dispatch::CircuitBreakerRegistry::default()),
        Arc::new(DharmaGate::default()),
        None,
    );

    c.bench_function("dispatch_noop_no_karma", |b| {
        b.iter(|| {
            let result = pipeline_no_karma
                .dispatch(&tool, &mut ctx, black_box(serde_json::json!({})))
                .unwrap();
            black_box(result);
        });
    });
}

fn bench_registry_lookup(c: &mut Criterion) {
    let registry = ToolRegistry::new();
    let reg = registry.register(Arc::new(NoopTool::new()));

    c.bench_function("registry_get_by_name", |b| {
        b.iter(|| {
            let tool = reg.get(black_box("noop"));
            black_box(tool);
        });
    });

    c.bench_function("registry_all", |b| {
        b.iter(|| {
            let tools = reg.all();
            black_box(tools.len());
        });
    });
}

criterion_group! {
    name = benches;
    config = Criterion::default()
        .warm_up_time(Duration::from_secs(1))
        .measurement_time(Duration::from_secs(2));
    targets = bench_pipeline_dispatch, bench_registry_lookup
}
criterion_main!(benches);
