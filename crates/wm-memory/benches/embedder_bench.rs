//! Embedder benchmark — measures embedding generation latency.

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;
use std::time::Duration;
use wm_memory::{Embedder, StubEmbedder};

fn bench_stub_embed_single(c: &mut Criterion) {
    let embedder = StubEmbedder::new(384);

    c.bench_function("stub_embed_single_short", |b| {
        b.iter(|| {
            let vec = embedder.embed(black_box("hello world")).unwrap();
            black_box(vec);
        });
    });

    c.bench_function("stub_embed_single_long", |b| {
        let long_text = "This is a longer text passage that might represent a typical memory entry \
            in the WhiteMagic system, containing multiple sentences and enough content to \
            exercise the hash-based embedding pipeline across the full dimensionality of the \
            vector space.";
        b.iter(|| {
            let vec = embedder.embed(black_box(long_text)).unwrap();
            black_box(vec);
        });
    });
}

fn bench_stub_embed_batch(c: &mut Criterion) {
    let embedder = StubEmbedder::new(384);

    let texts: Vec<&str> = vec!["hello"; 32];
    c.bench_function("stub_embed_batch_32", |b| {
        b.iter(|| {
            let vecs = embedder.embed_batch(black_box(&texts)).unwrap();
            black_box(vecs);
        });
    });

    let texts: Vec<&str> = vec!["hello"; 128];
    c.bench_function("stub_embed_batch_128", |b| {
        b.iter(|| {
            let vecs = embedder.embed_batch(black_box(&texts)).unwrap();
            black_box(vecs);
        });
    });

    let texts: Vec<&str> = vec!["hello"; 256];
    c.bench_function("stub_embed_batch_256", |b| {
        b.iter(|| {
            let vecs = embedder.embed_batch(black_box(&texts)).unwrap();
            black_box(vecs);
        });
    });
}

fn bench_stub_embed_dimension(c: &mut Criterion) {
    c.bench_function("stub_embed_dim_128", |b| {
        let embedder = StubEmbedder::new(128);
        b.iter(|| {
            let vec = embedder.embed(black_box("test text")).unwrap();
            black_box(vec);
        });
    });

    c.bench_function("stub_embed_dim_384", |b| {
        let embedder = StubEmbedder::new(384);
        b.iter(|| {
            let vec = embedder.embed(black_box("test text")).unwrap();
            black_box(vec);
        });
    });

    c.bench_function("stub_embed_dim_768", |b| {
        let embedder = StubEmbedder::new(768);
        b.iter(|| {
            let vec = embedder.embed(black_box("test text")).unwrap();
            black_box(vec);
        });
    });

    c.bench_function("stub_embed_dim_1024", |b| {
        let embedder = StubEmbedder::new(1024);
        b.iter(|| {
            let vec = embedder.embed(black_box("test text")).unwrap();
            black_box(vec);
        });
    });
}

criterion_group! {
    name = benches;
    config = Criterion::default()
        .warm_up_time(Duration::from_secs(1))
        .measurement_time(Duration::from_secs(2));
    targets = bench_stub_embed_single, bench_stub_embed_batch, bench_stub_embed_dimension
}
criterion_main!(benches);
