//! At-rest record sealing benchmarks (Q39 slice B) — plaintext vs sealed
//! store paths, plus the background migration.
//!
//! The delta this measures is the cost of the WMEN envelope: a keyfile
//! (mode B) store seals every record write under the galaxy DEK and opens
//! every record read. Numbers are quotable only from a release build:
//! `cargo bench -p wm-memory --bench at_rest_bench`.

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;
use std::time::Duration;
use tempfile::tempdir;
use wm_core::Galaxy;
use wm_memory::{AtRestConfig, Memory, MemoryStore, RECORD_GALAXIES};

const TEST_MAP: usize = 64 * 1024 * 1024;

fn seed(store: &MemoryStore, count: usize) -> Vec<uuid::Uuid> {
    (0..count)
        .map(|i| {
            let mem = Memory::new(Galaxy::Codex, format!("at-rest benchmark item {i}"))
                .with_tags(vec![format!("tag_{}", i % 10)]);
            let id = mem.metadata.id;
            store.put(Galaxy::Codex, &mem).unwrap();
            id
        })
        .collect()
}

fn bench_put(c: &mut Criterion) {
    let mut group = c.benchmark_group("at_rest_put");
    group.sample_size(20);
    group.measurement_time(Duration::from_secs(10));

    // Fresh store per sample: a shared store grows across iterations, and
    // LMDB page-split cost then dominates the cipher delta entirely.
    for count in [100, 1000] {
        group.bench_function(format!("plaintext_{count}_writes"), |b| {
            b.iter_with_setup(
                || {
                    let dir = tempdir().unwrap();
                    let store =
                        MemoryStore::open_with_at_rest(dir.path(), TEST_MAP, &AtRestConfig::off())
                            .unwrap();
                    (dir, store)
                },
                |(dir, store)| {
                    for i in 0..count {
                        let mem = Memory::new(Galaxy::Codex, format!("benchmark item {i}"));
                        let _ = store.put(Galaxy::Codex, &mem);
                    }
                    drop(store);
                    drop(dir);
                },
            );
        });
        group.bench_function(format!("sealed_{count}_writes"), |b| {
            b.iter_with_setup(
                || {
                    let dir = tempdir().unwrap();
                    let store = MemoryStore::open_with_at_rest(
                        dir.path(),
                        TEST_MAP,
                        &AtRestConfig::keyfile(),
                    )
                    .unwrap();
                    (dir, store)
                },
                |(dir, store)| {
                    for i in 0..count {
                        let mem = Memory::new(Galaxy::Codex, format!("benchmark item {i}"));
                        let _ = store.put(Galaxy::Codex, &mem);
                    }
                    drop(store);
                    drop(dir);
                },
            );
        });
    }
    group.finish();
}

fn bench_get_and_scan(c: &mut Criterion) {
    let mut group = c.benchmark_group("at_rest_read");

    let plain_dir = tempdir().unwrap();
    let plain =
        MemoryStore::open_with_at_rest(plain_dir.path(), TEST_MAP, &AtRestConfig::off()).unwrap();
    let plain_ids = seed(&plain, 1000);

    let sealed_dir = tempdir().unwrap();
    let sealed =
        MemoryStore::open_with_at_rest(sealed_dir.path(), TEST_MAP, &AtRestConfig::keyfile())
            .unwrap();
    let sealed_ids = seed(&sealed, 1000);

    group.bench_function("plaintext_get_single", |b| {
        b.iter(|| {
            let id = black_box(&plain_ids[500]);
            let _ = plain.get(Galaxy::Codex, *id);
        });
    });
    group.bench_function("sealed_get_single", |b| {
        b.iter(|| {
            let id = black_box(&sealed_ids[500]);
            let _ = sealed.get(Galaxy::Codex, *id);
        });
    });
    group.bench_function("plaintext_get_batch_100", |b| {
        b.iter(|| {
            for id in &plain_ids[..100] {
                let _ = plain.get(Galaxy::Codex, *id);
            }
        });
    });
    group.bench_function("sealed_get_batch_100", |b| {
        b.iter(|| {
            for id in &sealed_ids[..100] {
                let _ = sealed.get(Galaxy::Codex, *id);
            }
        });
    });
    group.bench_function("plaintext_scan_100", |b| {
        b.iter(|| {
            black_box(plain.scan(Galaxy::Codex, 100).unwrap());
        });
    });
    group.bench_function("sealed_scan_100", |b| {
        b.iter(|| {
            black_box(sealed.scan(Galaxy::Codex, 100).unwrap());
        });
    });
    group.finish();
}

fn bench_migration(c: &mut Criterion) {
    let mut group = c.benchmark_group("at_rest_migration");
    group.sample_size(10);
    group.measurement_time(Duration::from_secs(10));

    for count in [100, 1000] {
        group.bench_function(format!("seal_{count}_plaintext_records"), |b| {
            b.iter_with_setup(
                || {
                    let dir = tempdir().unwrap();
                    let store =
                        MemoryStore::open_with_at_rest(dir.path(), TEST_MAP, &AtRestConfig::off())
                            .unwrap();
                    seed(&store, count);
                    drop(store);
                    let keyed = MemoryStore::open_with_at_rest(
                        dir.path(),
                        TEST_MAP,
                        &AtRestConfig::keyfile(),
                    )
                    .unwrap();
                    (dir, keyed)
                },
                |(dir, store)| {
                    let report =
                        wm_memory::migrate_at_rest_records(&store, &RECORD_GALAXIES, 256).unwrap();
                    assert_eq!(report.total_encrypted, count as u64);
                    drop(store);
                    drop(dir);
                },
            );
        });
    }
    group.finish();
}

criterion_group!(benches, bench_put, bench_get_and_scan, bench_migration);
criterion_main!(benches);
