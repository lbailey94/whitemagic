//! Benchmarks for mutable structures: GanaRegistry, LearnedDreamCycle, LearnedCycleStrategy.

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;
use std::time::Duration;
use wm_core::{CycleStrategy, Gana, GanaRegistry, LearnedCycleStrategy, LearnedDreamCycle};

// ── GanaRegistry Benchmarks ───────────────────────────────────────────

fn bench_gana_registry_record_usage(c: &mut Criterion) {
    c.bench_function("gana_registry_record_usage", |b| {
        let mut registry = GanaRegistry::new();
        let ganas = [
            Gana::Horn,
            Gana::Encampment,
            Gana::WinnowingBasket,
            Gana::Star,
            Gana::Neck,
        ];
        let mut i = 0;
        b.iter(|| {
            registry.record_usage(black_box(ganas[i % ganas.len()]), black_box(true));
            i += 1;
        });
    });
}

fn bench_gana_registry_record_co_usage(c: &mut Criterion) {
    c.bench_function("gana_registry_record_co_usage", |b| {
        let mut registry = GanaRegistry::with_threshold(1000);
        let pairs: [(Gana, Gana); 4] = [
            (Gana::Horn, Gana::Encampment),
            (Gana::Star, Gana::Neck),
            (Gana::Horn, Gana::WinnowingBasket),
            (Gana::Ghost, Gana::StraddlingLegs),
        ];
        let mut i = 0;
        b.iter(|| {
            let (a, b_gana) = pairs[i % pairs.len()];
            registry.record_co_usage(black_box(a), black_box(b_gana));
            i += 1;
        });
    });
}

fn bench_gana_registry_co_usage_count(c: &mut Criterion) {
    let mut registry = GanaRegistry::new();
    for _ in 0..100 {
        registry.record_co_usage(Gana::Horn, Gana::Encampment);
    }

    c.bench_function("gana_registry_co_usage_count", |b| {
        b.iter(|| {
            let count = registry.co_usage_count(black_box(Gana::Horn), black_box(Gana::Encampment));
            black_box(count);
        });
    });
}

fn bench_gana_registry_analyze_drift(c: &mut Criterion) {
    let mut registry = GanaRegistry::with_threshold(5);
    for _ in 0..10 {
        registry.record_co_usage(Gana::Horn, Gana::WinnowingBasket);
    }
    for _ in 0..6 {
        registry.record_co_usage(Gana::Star, Gana::Neck);
    }
    for _ in 0..5 {
        registry.record_co_usage(Gana::Ghost, Gana::StraddlingLegs);
    }

    c.bench_function("gana_registry_analyze_drift", |b| {
        b.iter(|| {
            let merges = registry.analyze_drift(black_box(3));
            black_box(merges);
        });
    });
}

fn bench_gana_registry_serialization(c: &mut Criterion) {
    let mut registry = GanaRegistry::with_threshold(10);
    for i in 0..50 {
        registry.record_usage(Gana::Horn, i % 3 != 0);
        registry.record_co_usage(Gana::Horn, Gana::Encampment);
    }

    c.bench_function("gana_registry_serialize", |b| {
        b.iter(|| {
            let json = serde_json::to_string(black_box(&registry)).unwrap();
            black_box(json);
        });
    });

    let json = serde_json::to_string(&registry).unwrap();
    c.bench_function("gana_registry_deserialize", |b| {
        b.iter(|| {
            let mut back: GanaRegistry = serde_json::from_str(black_box(&json)).unwrap();
            back.rebuild_pairs();
            black_box(back);
        });
    });
}

// ── LearnedDreamCycle Benchmarks ──────────────────────────────────────

fn bench_dream_cycle_record_phase(c: &mut Criterion) {
    c.bench_function("dream_cycle_record_phase", |b| {
        let mut cycle = LearnedDreamCycle::new();
        let mut i = 0u8;
        b.iter(|| {
            cycle.record_phase(
                black_box(i % 12),
                black_box(true),
                black_box(0.8),
                black_box(100),
            );
            i += 1;
        });
    });
}

fn bench_dream_cycle_phases_to_run(c: &mut Criterion) {
    let mut cycle = LearnedDreamCycle::new();
    for i in 0..12u8 {
        for _ in 0..10 {
            cycle.record_phase(i, i % 3 != 0, f32::from(i).mul_add(0.03, 0.5), 100);
        }
    }

    c.bench_function("dream_cycle_phases_to_run", |b| {
        b.iter(|| {
            let phases = cycle.phases_to_run();
            black_box(phases);
        });
    });
}

fn bench_dream_cycle_update_phase_order(c: &mut Criterion) {
    c.bench_function("dream_cycle_update_phase_order", |b| {
        let mut cycle = LearnedDreamCycle::new();
        // Pre-populate with data
        for i in 0..12u8 {
            for _ in 0..10 {
                cycle.record_phase(i, i % 3 != 0, f32::from(i).mul_add(0.03, 0.5), 100);
            }
        }
        b.iter(|| {
            // record_phase triggers update_phase_order internally
            cycle.record_phase(black_box(0), black_box(true), black_box(0.9), black_box(50));
        });
    });
}

fn bench_dream_cycle_serialization(c: &mut Criterion) {
    let mut cycle = LearnedDreamCycle::new();
    for i in 0..12u8 {
        for _ in 0..10 {
            cycle.record_phase(i, i % 3 != 0, f32::from(i).mul_add(0.03, 0.5), 100);
        }
    }

    c.bench_function("dream_cycle_serialize", |b| {
        b.iter(|| {
            let json = serde_json::to_string(black_box(&cycle)).unwrap();
            black_box(json);
        });
    });

    let json = serde_json::to_string(&cycle).unwrap();
    c.bench_function("dream_cycle_deserialize", |b| {
        b.iter(|| {
            let back: LearnedDreamCycle = serde_json::from_str(black_box(&json)).unwrap();
            black_box(back);
        });
    });
}

// ── LearnedCycleStrategy Benchmarks ───────────────────────────────────

fn bench_cycle_strategy_record_cycle(c: &mut Criterion) {
    c.bench_function("cycle_strategy_record_cycle", |b| {
        let mut strategy = LearnedCycleStrategy::with_strategy(CycleStrategy::PriorityBased);
        let mut i = 0u8;
        b.iter(|| {
            strategy.record_cycle(
                black_box(i % 8),
                black_box(2u64),
                black_box(0.8),
                black_box(100u64),
            );
            i += 1;
        });
    });
}

fn bench_cycle_strategy_cycles_to_run(c: &mut Criterion) {
    let mut strategy = LearnedCycleStrategy::with_strategy(CycleStrategy::PriorityBased);
    for i in 0..8u8 {
        for _ in 0..10 {
            strategy.record_cycle(i, u64::from(i % 3), f32::from(i).mul_add(0.04, 0.5), 100);
        }
    }

    c.bench_function("cycle_strategy_cycles_to_run", |b| {
        b.iter(|| {
            let cycles = strategy.cycles_to_run();
            black_box(cycles);
        });
    });
}

fn bench_cycle_strategy_update_priority_order(c: &mut Criterion) {
    c.bench_function("cycle_strategy_update_priority_order", |b| {
        let mut strategy = LearnedCycleStrategy::with_strategy(CycleStrategy::PriorityBased);
        // Pre-populate
        for i in 0..8u8 {
            for _ in 0..10 {
                strategy.record_cycle(i, u64::from(i % 3), f32::from(i).mul_add(0.04, 0.5), 100);
            }
        }
        b.iter(|| {
            // record_cycle triggers update_priority_order internally
            strategy.record_cycle(
                black_box(0),
                black_box(3u64),
                black_box(0.9),
                black_box(50u64),
            );
        });
    });
}

fn bench_cycle_strategy_serialization(c: &mut Criterion) {
    let mut strategy = LearnedCycleStrategy::with_strategy(CycleStrategy::PriorityBased);
    for i in 0..8u8 {
        for _ in 0..10 {
            strategy.record_cycle(i, u64::from(i % 3), f32::from(i).mul_add(0.04, 0.5), 100);
        }
    }

    c.bench_function("cycle_strategy_serialize", |b| {
        b.iter(|| {
            let json = serde_json::to_string(black_box(&strategy)).unwrap();
            black_box(json);
        });
    });

    let json = serde_json::to_string(&strategy).unwrap();
    c.bench_function("cycle_strategy_deserialize", |b| {
        b.iter(|| {
            let back: LearnedCycleStrategy = serde_json::from_str(black_box(&json)).unwrap();
            black_box(back);
        });
    });
}

criterion_group! {
    name = benches;
    config = Criterion::default()
        .warm_up_time(Duration::from_secs(1))
        .measurement_time(Duration::from_secs(2));
    targets = bench_gana_registry_record_usage,
        bench_gana_registry_record_co_usage,
        bench_gana_registry_co_usage_count,
        bench_gana_registry_analyze_drift,
        bench_gana_registry_serialization,
        bench_dream_cycle_record_phase,
        bench_dream_cycle_phases_to_run,
        bench_dream_cycle_update_phase_order,
        bench_dream_cycle_serialization,
        bench_cycle_strategy_record_cycle,
        bench_cycle_strategy_cycles_to_run,
        bench_cycle_strategy_update_priority_order,
        bench_cycle_strategy_serialization,
}
criterion_main!(benches);
