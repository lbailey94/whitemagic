//! Self-play training loop benchmark — measures cycle latency and throughput.

use criterion::{BenchmarkId, Criterion, criterion_group, criterion_main};
use std::hint::black_box;
use wm_bicameral::{
    ExactMatchVerifier, LoRAAdapterManager, SelfPlayConfig, SelfPlayLoop, TaskProposer, TaskSolver,
    TierHandler,
};

struct StubProposer {
    response: String,
}

impl TierHandler for StubProposer {
    fn handle(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
        Ok((self.response.clone(), 0.9))
    }
    fn name(&self) -> &'static str {
        "bench_proposer"
    }
}

struct StubSolver {
    response: String,
}

impl TierHandler for StubSolver {
    fn handle(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
        Ok((self.response.clone(), 0.9))
    }
    fn name(&self) -> &'static str {
        "bench_solver"
    }
}

fn make_loop() -> SelfPlayLoop {
    let proposer = TaskProposer::ungrounded(Box::new(StubProposer {
        response: r#"{"prompt": "What is 2+2?", "expected": "4", "difficulty": 0.1}"#.to_string(),
    }));
    let solver = TaskSolver::new(Box::new(StubSolver {
        response: "The answer is 4.".to_string(),
    }));
    let verifier = Box::new(ExactMatchVerifier::new());
    let tmp = tempfile::tempdir().unwrap();
    let adapter = LoRAAdapterManager::new(tmp.path().to_path_buf());
    SelfPlayLoop::new(
        proposer,
        solver,
        verifier,
        adapter,
        SelfPlayConfig::default(),
    )
}

fn bench_single_cycle(c: &mut Criterion) {
    c.bench_function("self_play_single_cycle", |b| {
        b.iter(|| {
            let mut loop_ = make_loop();
            loop_.run_cycle("");
            black_box(loop_.stats());
        });
    });
}

fn bench_multi_cycle(c: &mut Criterion) {
    let mut group = c.benchmark_group("self_play_multi_cycle");
    for n in [1, 5, 10, 20] {
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |b, &n| {
            b.iter(|| {
                let mut loop_ = make_loop();
                loop_.config.max_cycles_per_run = n;
                loop_.run("");
                black_box(loop_.stats());
            });
        });
    }
    group.finish();
}

fn bench_stats_record(c: &mut Criterion) {
    c.bench_function("self_play_stats_record", |b| {
        b.iter(|| {
            let mut loop_ = make_loop();
            loop_.run_cycle("");
            black_box(loop_.stats().clone());
        });
    });
}

criterion_group!(
    benches,
    bench_single_cycle,
    bench_multi_cycle,
    bench_stats_record
);
criterion_main!(benches);
