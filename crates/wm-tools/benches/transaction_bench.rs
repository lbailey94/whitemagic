use criterion::{BenchmarkId, Criterion, criterion_group, criterion_main};
use std::sync::{Arc, Mutex};
use wm_core::{BrainWave, Context, Galaxy, Tool};
use wm_memory::{Memory, MemoryStore};
use wm_tools::expansion::transaction::{
    TransactionBeginTool, TransactionRollbackTool, TransactionState,
};

fn bench_transaction_begin_empty(c: &mut Criterion) {
    c.bench_function("transaction_begin_empty", |b| {
        b.iter_batched(
            || {
                let tmp = tempfile::tempdir().unwrap();
                let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
                let state: TransactionState = Arc::new(Mutex::new(None));
                (store, state, tmp)
            },
            |(store, state, _tmp)| {
                let tool = TransactionBeginTool::new(store, state);
                tool.call(&mut Context::new(BrainWave::Gamma), serde_json::json!({}))
                    .unwrap();
            },
            criterion::BatchSize::SmallInput,
        );
    });
}

fn bench_transaction_begin_with_memories(c: &mut Criterion) {
    let mut group = c.benchmark_group("transaction_begin_with_memories");
    for n in [1, 10, 50, 100] {
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |b, &n| {
            b.iter_batched(
                || {
                    let tmp = tempfile::tempdir().unwrap();
                    let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
                    for i in 0..n {
                        let mem = Memory::new(Galaxy::Codex, format!("memory {i}"));
                        store.put(Galaxy::Codex, &mem).unwrap();
                    }
                    let state: TransactionState = Arc::new(Mutex::new(None));
                    (store, state, tmp)
                },
                |(store, state, _tmp)| {
                    let tool = TransactionBeginTool::new(store, state);
                    tool.call(&mut Context::new(BrainWave::Gamma), serde_json::json!({}))
                        .unwrap();
                },
                criterion::BatchSize::SmallInput,
            );
        });
    }
    group.finish();
}

fn bench_transaction_rollback_empty(c: &mut Criterion) {
    c.bench_function("transaction_rollback_empty", |b| {
        b.iter_batched(
            || {
                let tmp = tempfile::tempdir().unwrap();
                let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
                let state: TransactionState = Arc::new(Mutex::new(None));
                let begin = TransactionBeginTool::new(store.clone(), state.clone());
                begin
                    .call(&mut Context::new(BrainWave::Gamma), serde_json::json!({}))
                    .unwrap();
                (store, state, tmp)
            },
            |(store, state, _tmp)| {
                let tool = TransactionRollbackTool::new(store, state);
                tool.call(&mut Context::new(BrainWave::Gamma), serde_json::json!({}))
                    .unwrap();
            },
            criterion::BatchSize::SmallInput,
        );
    });
}

fn bench_transaction_rollback_with_memories(c: &mut Criterion) {
    let mut group = c.benchmark_group("transaction_rollback_with_memories");
    for n in [1, 10, 50, 100] {
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |b, &n| {
            b.iter_batched(
                || {
                    let tmp = tempfile::tempdir().unwrap();
                    let store = Arc::new(MemoryStore::open_default(tmp.path()).unwrap());
                    for i in 0..n {
                        let mem = Memory::new(Galaxy::Codex, format!("memory {i}"));
                        store.put(Galaxy::Codex, &mem).unwrap();
                    }
                    let state: TransactionState = Arc::new(Mutex::new(None));
                    let begin = TransactionBeginTool::new(store.clone(), state.clone());
                    begin
                        .call(&mut Context::new(BrainWave::Gamma), serde_json::json!({}))
                        .unwrap();
                    (store, state, tmp)
                },
                |(store, state, _tmp)| {
                    let tool = TransactionRollbackTool::new(store, state);
                    tool.call(&mut Context::new(BrainWave::Gamma), serde_json::json!({}))
                        .unwrap();
                },
                criterion::BatchSize::SmallInput,
            );
        });
    }
    group.finish();
}

criterion_group!(
    transaction_benches,
    bench_transaction_begin_empty,
    bench_transaction_begin_with_memories,
    bench_transaction_rollback_empty,
    bench_transaction_rollback_with_memories,
);
criterion_main!(transaction_benches);
