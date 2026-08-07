use criterion::{BenchmarkId, Criterion, criterion_group, criterion_main};
use std::sync::Arc;
use wm_core::{BrainWave, Context, Tool, ToolStatsSnapshot};
use wm_memory::MemoryStore;
use wm_tools::expansion::{DispatchTelemetry, FrictionAutoLogTool, FrictionLogTool, friction_hash};

fn bench_friction_hash(c: &mut Criterion) {
    c.bench_function("friction_hash", |b| {
        b.iter(|| {
            let _ = friction_hash("memory.search", "error", "high", "Tantivy index not found");
        });
    });
}

fn bench_log_error_new(c: &mut Criterion) {
    let telemetry = DispatchTelemetry {
        tool: "memory.search".to_string(),
        success: false,
        latency_ms: 45.3,
        error: "Tantivy index not found".to_string(),
        brain_wave: "Beta".to_string(),
        effectiveness: 0.42,
        karma_debt: 0.15,
        self_model_confidence: 0.58,
        drive_bias_confidence: 0.71,
        citta_coherence: 0.5,
        citta_valence: 0.0,
        tool_stats: ToolStatsSnapshot::default(),
        routed_via_wm: true,
        arg_size_bytes: 156,
        response_size_bytes: 0,
    };

    c.bench_function("log_error_new_entry", |b| {
        b.iter(|| {
            let tmp = tempfile::tempdir().unwrap();
            let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
            let tool = FrictionAutoLogTool::new(store, None);
            tool.log_error(&telemetry).unwrap();
        });
    });
}

fn bench_log_error_dedup(c: &mut Criterion) {
    let telemetry = DispatchTelemetry {
        tool: "memory.search".to_string(),
        success: false,
        latency_ms: 45.3,
        error: "Tantivy index not found".to_string(),
        brain_wave: "Beta".to_string(),
        effectiveness: 0.42,
        karma_debt: 0.15,
        self_model_confidence: 0.58,
        drive_bias_confidence: 0.71,
        citta_coherence: 0.5,
        citta_valence: 0.0,
        tool_stats: ToolStatsSnapshot::default(),
        routed_via_wm: true,
        arg_size_bytes: 156,
        response_size_bytes: 0,
    };

    let mut group = c.benchmark_group("log_error_dedup");
    for n in [1, 10, 50, 100] {
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |b, &n| {
            b.iter_batched(
                || {
                    let tmp = tempfile::tempdir().unwrap();
                    let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
                    let tool = FrictionAutoLogTool::new(store, None);
                    for _ in 0..n {
                        tool.log_error(&telemetry).unwrap();
                    }
                    tool
                },
                |tool| {
                    tool.log_error(&telemetry).unwrap();
                },
                criterion::BatchSize::SmallInput,
            );
        });
    }
    group.finish();
}

fn bench_friction_log_tool_call(c: &mut Criterion) {
    c.bench_function("friction_log_tool_call", |b| {
        b.iter_batched(
            || {
                let tmp = tempfile::tempdir().unwrap();
                let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
                FrictionLogTool::new(store, None)
            },
            |tool| {
                let mut ctx = Context::new(BrainWave::Gamma);
                tool.call(
                    &mut ctx,
                    serde_json::json!({
                        "what_happened": "Tool returned unexpected empty result",
                        "expected_behavior": "Should return matching memories",
                        "suggested_fix": "Check index state",
                        "severity": "medium",
                        "category": "ux",
                        "tool_name": "memory.search",
                    }),
                )
                .unwrap();
            },
            criterion::BatchSize::SmallInput,
        );
    });
}

criterion_group!(
    rsi_benches,
    bench_friction_hash,
    bench_log_error_new,
    bench_log_error_dedup,
    bench_friction_log_tool_call,
);
criterion_main!(rsi_benches);
