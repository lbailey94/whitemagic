//! In-process v6 episodic search and ingest measurements.

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;
use std::time::Duration;
use tempfile::tempdir;
use wm_core::{EpisodicKind, EpisodicRecord, Provenance, ProvenanceSource};
use wm_memory::MemoryStore;

fn sample_record(sequence: u64) -> EpisodicRecord {
    let content = if sequence % 5 == 0 {
        format!("Rust memory retrieval benchmark item {sequence}")
    } else {
        format!("Unrelated episodic record {sequence}")
    };
    EpisodicRecord::new(
        None,
        sequence,
        EpisodicKind::Observation,
        content,
        Provenance::new(ProvenanceSource::User),
    )
}

fn populated_store(count: usize) -> (tempfile::TempDir, MemoryStore) {
    let tmp = tempdir().unwrap();
    let store = MemoryStore::open_default(tmp.path()).unwrap();
    let records: Vec<EpisodicRecord> = (0..count as u64).map(sample_record).collect();
    store.episodic().append_batch(&records).unwrap();
    (tmp, store)
}

fn bench_episodic_search(c: &mut Criterion) {
    let mut group = c.benchmark_group("episodic_search");

    for count in [100, 1_000, 10_000] {
        let (_tmp, store) = populated_store(count);
        group.bench_function(format!("warm_search_{count}"), |b| {
            b.iter(|| {
                let results = store
                    .episodic()
                    .search(black_box("rust memory retrieval"), 10, false)
                    .unwrap();
                black_box(results);
            });
        });
    }

    group.finish();
}

fn bench_episodic_ingest(c: &mut Criterion) {
    let mut group = c.benchmark_group("episodic_ingest");
    let count = 1_000u64;
    let records: Vec<EpisodicRecord> = (0..count).map(sample_record).collect();

    group.bench_function("append_single_1000", |b| {
        b.iter(|| {
            let tmp = tempdir().unwrap();
            let store = MemoryStore::open_default(tmp.path()).unwrap();
            for record in &records {
                store.episodic().append(record).unwrap();
            }
            black_box(store.mutation_count());
        });
    });

    group.bench_function("append_batch_1000", |b| {
        b.iter(|| {
            let tmp = tempdir().unwrap();
            let store = MemoryStore::open_default(tmp.path()).unwrap();
            store.episodic().append_batch(&records).unwrap();
            black_box(store.mutation_count());
        });
    });

    group.finish();
}

criterion_group! {
    name = benches;
    config = Criterion::default()
        .warm_up_time(Duration::from_secs(1))
        .measurement_time(Duration::from_secs(2));
    targets = bench_episodic_search, bench_episodic_ingest
}
criterion_main!(benches);
