//! LMDB memory store benchmarks — put, get, scan, search.

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;
use std::time::Duration;
use tempfile::tempdir;
use wm_core::Galaxy;
use wm_memory::{Memory, MemoryStore, SearchEngine};

fn bench_put(c: &mut Criterion) {
    let mut group = c.benchmark_group("lmdb_put");

    for count in [100, 1000] {
        group.bench_function(format!("{count}_writes"), |b| {
            b.iter(|| {
                let tmp = tempdir().unwrap();
                let store = MemoryStore::open_default(tmp.path()).unwrap();
                for i in 0..count {
                    let mem = Memory::new(Galaxy::Codex, format!("benchmark item {i}"))
                        .with_tags(vec![format!("tag_{}", i % 10)]);
                    let _ = store.put(Galaxy::Codex, &mem);
                }
                black_box(());
            });
        });
    }

    group.finish();
}

fn bench_get(c: &mut Criterion) {
    let tmp = tempdir().unwrap();
    let store = MemoryStore::open_default(tmp.path()).unwrap();

    let mut ids = Vec::new();
    for i in 0..1000 {
        let mem = Memory::new(Galaxy::Codex, format!("benchmark item {i}"));
        let id = mem.metadata.id;
        let _ = store.put(Galaxy::Codex, &mem);
        ids.push(id);
    }

    c.bench_function("lmdb_get_single", |b| {
        b.iter(|| {
            let id = black_box(&ids[500]);
            let _ = store.get(Galaxy::Codex, *id);
        });
    });

    c.bench_function("lmdb_get_batch_100", |b| {
        b.iter(|| {
            for id in &ids[..100] {
                let _ = store.get(Galaxy::Codex, *id);
            }
        });
    });
}

fn bench_scan(c: &mut Criterion) {
    let tmp = tempdir().unwrap();
    let store = MemoryStore::open_default(tmp.path()).unwrap();

    for i in 0..1000 {
        let mem = Memory::new(Galaxy::Codex, format!("scan benchmark item {i}"));
        let _ = store.put(Galaxy::Codex, &mem);
    }

    let mut group = c.benchmark_group("lmdb_scan");

    for limit in [10, 100, 1000] {
        group.bench_function(format!("limit_{limit}"), |b| {
            b.iter(|| {
                let results = store.scan(Galaxy::Codex, black_box(limit)).unwrap();
                black_box(results);
            });
        });
    }

    group.finish();
}

fn bench_search(c: &mut Criterion) {
    let tmp = tempdir().unwrap();
    let store = MemoryStore::open_default(tmp.path()).unwrap();
    let tantivy_path = tmp.path().join("tantivy");
    std::fs::create_dir_all(&tantivy_path).unwrap();
    let search = SearchEngine::open(&tantivy_path).unwrap();

    let mut writer = search.writer().unwrap();
    for i in 0..500 {
        let content = match i % 5 {
            0 => format!("Rust memory system LMDB storage benchmark item {i}"),
            1 => format!("Rust memory LMDB performance test entry {i}"),
            2 => format!("Python web framework Django tutorial part {i}"),
            3 => format!("Session handoff notes for task {i}"),
            _ => format!("Dream cycle consolidation research note {i}"),
        };
        let mem = Memory::new(Galaxy::Codex, content);
        let _ = store.put(Galaxy::Codex, &mem);
        let _ = search.add_document(
            &mut writer,
            &mem.metadata.id.to_string(),
            Galaxy::Codex.db_name(),
            &mem.content,
            &mem.metadata.tags,
            mem.metadata.created_at.timestamp(),
        );
    }
    search.commit(&mut writer).unwrap();

    let mut group = c.benchmark_group("tantivy_search");

    for query in ["rust", "memory", "benchmark", "django"] {
        group.bench_function(query, |b| {
            b.iter(|| {
                let results = search.search(black_box(query), 10).unwrap();
                black_box(results);
            });
        });
    }

    group.finish();
}

fn bench_put_batch(c: &mut Criterion) {
    let mut group = c.benchmark_group("lmdb_put_batch");

    for count in [100, 1000] {
        // Benchmark individual puts
        group.bench_function(format!("individual_{count}"), |b| {
            b.iter(|| {
                let tmp = tempdir().unwrap();
                let store = MemoryStore::open_default(tmp.path()).unwrap();
                for i in 0..count {
                    let mem = Memory::new(Galaxy::Codex, format!("batch item {i}"));
                    let _ = store.put(Galaxy::Codex, &mem);
                }
                black_box(());
            });
        });

        // Benchmark batch put
        group.bench_function(format!("batch_{count}"), |b| {
            b.iter(|| {
                let tmp = tempdir().unwrap();
                let store = MemoryStore::open_default(tmp.path()).unwrap();
                let mems: Vec<Memory> = (0..count)
                    .map(|i| Memory::new(Galaxy::Codex, format!("batch item {i}")))
                    .collect();
                let _ = store.put_batch(Galaxy::Codex, &mems);
                black_box(());
            });
        });
    }

    group.finish();
}

criterion_group! {
    name = benches;
    config = Criterion::default()
        .warm_up_time(Duration::from_secs(1))
        .measurement_time(Duration::from_secs(2));
    targets = bench_put, bench_get, bench_scan, bench_search, bench_put_batch
}
criterion_main!(benches);
