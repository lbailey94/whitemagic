//! Dream cycle benchmark — measures throughput with realistic memory load.

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;
use std::time::Duration;
use tempfile::tempdir;
use wm_consciousness::{DreamContext, DreamCycle};
use wm_core::Galaxy;
use wm_memory::{AssociationStore, Memory, MemoryStore};

fn seed_memories(store: &MemoryStore, count: usize) {
    let galaxies = [
        Galaxy::Codex,
        Galaxy::Research,
        Galaxy::Sessions,
        Galaxy::Citta,
        Galaxy::Aria,
        Galaxy::Dreams,
        Galaxy::Universal,
    ];
    for i in 0..count {
        let galaxy = galaxies[i % galaxies.len()];
        let content = match i % 5 {
            0 => format!("Rust memory system LMDB storage benchmark item {i}"),
            1 => format!("Rust memory LMDB performance test entry {i}"),
            2 => format!("Python web framework Django tutorial part {i}"),
            3 => format!("Session handoff notes for task {i}"),
            _ => format!("Dream cycle consolidation research note {i}"),
        };
        let importance = match i % 10 {
            0 => 0.95,
            1..=3 => 0.7,
            4..=7 => 0.4,
            _ => 0.05,
        };
        let mem = Memory::new(galaxy, content)
            .with_importance(importance)
            .with_tags(vec![format!("tag_{}", i % 8), format!("cat_{}", i % 4)]);
        let _ = store.put(galaxy, &mem);
    }
}

fn bench_dream_cycle(c: &mut Criterion) {
    let mut group = c.benchmark_group("dream_cycle");

    for count in [10, 50, 200] {
        if count >= 200 {
            group.sample_size(10);
        }
        group.bench_function(format!("{count}_memories"), |b| {
            b.iter(|| {
                let tmp = tempdir().unwrap();
                let store = MemoryStore::open_default(tmp.path()).unwrap();
                let assoc = AssociationStore::open(store.env()).unwrap();
                seed_memories(&store, count);

                let ctx = DreamContext::new(&store, &assoc);
                let mut cycle = DreamCycle::new();
                let result = cycle.run(&ctx);

                black_box(result);
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
    targets = bench_dream_cycle
}
criterion_main!(benches);
