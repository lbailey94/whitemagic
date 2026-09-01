//! Benchmark for reflex dispatch latency.
//!
//! Target: <100µs end-to-end for reflex dispatch.
//! Expected: <1µs (array index + bitmask + fn call).

use criterion::{Criterion, black_box, criterion_group, criterion_main};
use std::time::Duration;
use wm_cognitive::reflex::{ReflexArgs, ReflexDispatchTable, ReflexId, builtins};

fn bench_dispatch_single(c: &mut Criterion) {
    let mut table = ReflexDispatchTable::permissive();
    builtins::register_builtins(&mut table);
    let args = ReflexArgs::new(1, 42);

    c.bench_function("dispatch_e_stop", |b| {
        b.iter(|| {
            let id: ReflexId = black_box(builtins::ids::E_STOP);
            let _ = black_box(table.dispatch(id, &args).unwrap());
        });
    });
}

fn bench_dispatch_all_builtins(c: &mut Criterion) {
    let mut table = ReflexDispatchTable::permissive();
    builtins::register_builtins(&mut table);
    let args = ReflexArgs::new(1, 42);

    c.bench_function("dispatch_all_8_builtins", |b| {
        b.iter(|| {
            for builtin in builtins::BUILTINS {
                let _ = black_box(table.dispatch(builtin.id, &args).unwrap());
            }
        });
    });
}

fn bench_safety_check(c: &mut Criterion) {
    use wm_cognitive::reflex::safety::{SAFETY_DEFAULT, SafetyBit, is_allowed};
    let handler_mask = SafetyBit::EmergencyStop.mask();

    c.bench_function("safety_bitmask_check", |b| {
        b.iter(|| {
            black_box(is_allowed(
                black_box(handler_mask),
                black_box(SAFETY_DEFAULT),
            ))
        });
    });
}

criterion_group! {
    name = benches;
    config = Criterion::default()
        .warm_up_time(Duration::from_secs(1))
        .measurement_time(Duration::from_secs(2));
    targets = bench_dispatch_single, bench_dispatch_all_builtins, bench_safety_check
}
criterion_main!(benches);
