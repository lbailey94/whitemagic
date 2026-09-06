//! Inference router benchmark — measures classification and routing latency.

use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;
use std::sync::Arc;
use std::time::Duration;
use wm_bicameral::{
    BicameralConfig, BicameralEngine, HemisphereInput, InferenceRouter, RouterConfig,
    SpeculativeConfig, SpeculativeDecoder, TierHandler,
};

// --- Tier handler stubs for benchmarking ---

struct StubHandler {
    name: &'static str,
}

impl TierHandler for StubHandler {
    fn handle(&self, prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
        Ok((format!("response to: {prompt}"), 0.9))
    }
    fn name(&self) -> &'static str {
        self.name
    }
}

struct StubHandlerLow {
    name: &'static str,
}

impl TierHandler for StubHandlerLow {
    fn handle(&self, prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
        Ok((format!("low confidence response to: {prompt}"), 0.3))
    }
    fn name(&self) -> &'static str {
        self.name
    }
}

fn bench_classify(c: &mut Criterion) {
    let router = InferenceRouter::new(RouterConfig::default());

    let simple = "what is 2+2";
    let medium = "explain how memory consolidation works in the system";
    let complex = "analyze the philosophical implications of quantum mechanics in consciousness studies and propose a novel theoretical framework";

    c.bench_function("classify_simple", |b| {
        b.iter(|| {
            let assessment = router.classify(black_box(simple), None, None, false);
            black_box(assessment);
        });
    });

    c.bench_function("classify_medium", |b| {
        b.iter(|| {
            let assessment = router.classify(black_box(medium), None, None, false);
            black_box(assessment);
        });
    });

    c.bench_function("classify_complex", |b| {
        b.iter(|| {
            let assessment = router.classify(black_box(complex), None, None, false);
            black_box(assessment);
        });
    });
}

fn bench_route_with_handlers(c: &mut Criterion) {
    let mut router = InferenceRouter::new(RouterConfig::default());
    router.register_handler(
        wm_bicameral::InferenceTier::EdgeRules,
        Arc::new(StubHandler { name: "edge" }),
    );
    router.register_handler(
        wm_bicameral::InferenceTier::LocalLlamaCpp,
        Arc::new(StubHandler { name: "llamacpp" }),
    );
    router.register_handler(
        wm_bicameral::InferenceTier::LocalSmall,
        Arc::new(StubHandler { name: "small" }),
    );

    c.bench_function("route_simple_with_handlers", |b| {
        b.iter(|| {
            let resp = router.route(black_box("what is 2+2"), None, None, false, None);
            black_box(resp);
        });
    });

    c.bench_function("route_complex_with_handlers", |b| {
        b.iter(|| {
            let resp = router.route(
                black_box("analyze the philosophical implications of quantum mechanics"),
                None,
                None,
                false,
                None,
            );
            black_box(resp);
        });
    });
}

fn bench_budget_tracker(c: &mut Criterion) {
    use wm_bicameral::TokenBudgetTracker;

    c.bench_function("budget_record_usage", |b| {
        let mut tracker = TokenBudgetTracker::new(100_000);
        b.iter(|| {
            tracker.record_usage(black_box(500), black_box(200));
        });
    });

    c.bench_function("budget_recommend_downgrade", |b| {
        let tracker = TokenBudgetTracker::new(100_000);
        b.iter(|| {
            let result = tracker.recommend_downgrade(black_box(wm_bicameral::InferenceTier::Cloud));
            black_box(result);
        });
    });

    c.bench_function("budget_summary", |b| {
        let tracker = TokenBudgetTracker::new(100_000);
        b.iter(|| {
            let summary = tracker.summary();
            black_box(summary);
        });
    });
}

fn bench_bicameral_with_router(c: &mut Criterion) {
    let engine = BicameralEngine::left_only(BicameralConfig::default())
        .with_router(InferenceRouter::new(RouterConfig::default()));

    let input = HemisphereInput::new("what is rust programming language");

    c.bench_function("bicameral_reason_with_router", |b| {
        b.iter(|| {
            let result = engine.reason(black_box(&input));
            black_box(result);
        });
    });

    c.bench_function("bicameral_classify_with_router", |b| {
        b.iter(|| {
            let assessment = engine.classify(black_box("what is rust"));
            black_box(assessment);
        });
    });
}

fn bench_speculative(c: &mut Criterion) {
    let draft = Arc::new(StubHandler { name: "draft" }) as Arc<dyn TierHandler>;
    let verify = Arc::new(StubHandler { name: "verify" }) as Arc<dyn TierHandler>;
    let decoder = SpeculativeDecoder::new(draft, verify, SpeculativeConfig::default());

    c.bench_function("speculative_decode_draft_accepted", |b| {
        b.iter(|| {
            let result = decoder.generate(black_box("what is 2+2"), 100);
            black_box(result);
        });
    });

    // Low-confidence draft forces verify path
    let draft_low = Arc::new(StubHandlerLow { name: "draft_low" }) as Arc<dyn TierHandler>;
    let decoder_verify = SpeculativeDecoder::new(
        draft_low,
        Arc::new(StubHandler { name: "verify" }) as Arc<dyn TierHandler>,
        SpeculativeConfig::default(),
    );

    c.bench_function("speculative_decode_with_verify", |b| {
        b.iter(|| {
            let result = decoder_verify.generate(black_box("explain quantum mechanics"), 200);
            black_box(result);
        });
    });

    c.bench_function("speculative_stats", |b| {
        b.iter(|| {
            let stats = decoder.stats();
            black_box(stats);
        });
    });
}

criterion_group! {
    name = benches;
    config = Criterion::default()
        .warm_up_time(Duration::from_secs(1))
        .measurement_time(Duration::from_secs(2));
    targets = bench_classify, bench_route_with_handlers, bench_budget_tracker, bench_bicameral_with_router, bench_speculative
}
criterion_main!(benches);
