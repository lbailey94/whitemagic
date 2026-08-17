//! In-process v6 episodic search scaling measurements.

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;
use std::time::Duration;
use tempfile::tempdir;
use wm_core::{EpisodicKind, EpisodicRecord, Provenance, ProvenanceSource};
use wm_memory::MemoryStore;

fn bench_episodic_search(c: &mut Criterion) {
    let mut group = c.benchmark_group("episodic_search");

    for count in [100, 1_000, 10_000] {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        for sequence in 0..count {
            let content = if sequence % 5 == 0 {
                format!("Rust memory retrieval benchmark item {sequence}")
            } else {
                format!("Unrelated episodic record {sequence}")
            };
            let record = EpisodicRecord::new(
                None,
                sequence as u64,
                EpisodicKind::Observation,
                content,
                Provenance::new(ProvenanceSource::User),
            );
            store.episodic().append(&record).unwrap();
        }

        group.bench_function(format!("scan_and_score_{count}"), |b| {
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

criterion_group! {
    name = benches;
    config = Criterion::default()
        .warm_up_time(Duration::from_secs(1))
        .measurement_time(Duration::from_secs(2));
    targets = bench_episodic_search
}
criterion_main!(benches);
