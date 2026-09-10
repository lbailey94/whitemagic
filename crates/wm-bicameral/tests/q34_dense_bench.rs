//! Q34 experiment-1 bench harness (spike, 2026-09-09, session 7f56e966).
//! Measures dense-encoding compression + losslessness + latency on a FIXED
//! fixture corpus of internal-context-style strings. Measurement only:
//! losslessness is asserted (regression safety); ratios are PRINTED for
//! human M3-gate adjudication in the session memo, never self-passed.
//! Run both arms:
//!   cargo test -p wm-bicameral --test q34_dense_bench -- --nocapture
//!   WM_DENSE_ENCODING=1 cargo test -p wm-bicameral --test q34_dense_bench -- --nocapture
//! NOTE: the encoder is constructed explicitly enabled here — the env knob
//! gates server *wiring*, not this unit. Arm comparison therefore measures
//! enabled-vs-disabled config, which is exactly the promotion delta.

use std::time::Instant;
use wm_bicameral::dense_encoding::{DenseEncoder, DenseEncodingConfig};

/// Fixed corpus: internal tool-dispatch / memory-query / pipeline phrasings.
const FIXTURES: [&str; 10] = [
    "Search the memory database for all entries tagged with consciousness that have an importance score greater than 0.8 and return the top 10 results sorted by importance descending",
    "For each memory tagged aria-era extract associations filter for importance above threshold merge with related memories transform into knowledge graph detect communities and export to markdown",
    "Dispatch tool memory search with query consciousness and limit 10 then rerank results by trust weight and return evidence bundle with source spans",
    "The dream cycle consolidation phase skipped telemetry inputs and promoted two candidate lessons to verified procedures pending regression monitoring",
    "Association miner traversed cross galaxy links from the seed memory at depth 2 and propagated activation across 14 confirmed edges",
    "Convergence bench report retrieval at 1 is 0.86 retrieval at 5 is 1.00 with mean reciprocal rank 0.923 across 50 canonical questions",
    "Quarantine the compromised peer purge its messages revoke its locks and refuse rejoin until key rotation completes successfully",
    "Nightly backup sealed the store manifest anchored off device with Merkle root published and rotation policy verified against recovery objectives",
    "Short status ping with no repetitive phrasing at all",
    "Memory update rejected importance out of class band telemetry ceiling enforced write gate stage intact journal entry recorded",
];

#[test]
fn q34_dense_bench_measurement() {
    let enabled = DenseEncoder::new(DenseEncodingConfig {
        enabled: true,
        ..DenseEncodingConfig::default()
    });
    // Same corpus, decode-hint stripped — separates codec performance from
    // legend overhead (decode may degrade; that is itself a finding).
    let no_hint = DenseEncoder::new(DenseEncodingConfig {
        enabled: true,
        include_decode_hint: false,
        ..DenseEncodingConfig::default()
    });
    let disabled = DenseEncoder::new(DenseEncodingConfig::default());

    let mut tot_orig = 0usize;
    let mut tot_enc = 0usize;
    let mut lossless_n = 0usize;
    let t0 = Instant::now();
    for (i, fx) in FIXTURES.iter().enumerate() {
        let enc = enabled.encode(fx);
        let dec = enabled.decode(&enc);
        // Design contract (matches in-file suite): decode is APPROXIMATE —
        // keyword containment, not byte equality. Record both.
        let lossless = dec == *fx;
        lossless_n += usize::from(lossless);
        let kept = fx
            .split_whitespace()
            .filter(|w| w.len() > 4 && dec.to_lowercase().contains(&w.to_lowercase()))
            .count();
        let total_kw = fx.split_whitespace().filter(|w| w.len() > 4).count();
        let ratio = enabled.compression_ratio(fx);
        println!(
            "fixture {i}: orig={}B enc={}B ratio={:.3} saved={:.1}% lossless={lossless} kw={kept}/{total_kw}",
            fx.len(),
            enc.len(),
            ratio,
            (1.0 - ratio) * 100.0
        );
        tot_orig += fx.len();
        tot_enc += enc.len();
    }
    let dt = t0.elapsed();
    // Disabled arm must be byte-identical passthrough (the promotion baseline).
    for (i, fx) in FIXTURES.iter().enumerate() {
        assert_eq!(
            disabled.encode(fx),
            *fx,
            "disabled arm must passthrough (fixture {i})"
        );
    }
    let total_ratio = tot_enc as f64 / tot_orig as f64;
    println!(
        "TOTAL: orig={tot_orig}B enc={tot_enc}B ratio={total_ratio:.3} saved={:.1}% lossless={lossless_n}/10 in {dt:?} (10 fixtures, encode+decode)",
        (1.0 - total_ratio) * 100.0
    );
    // Hint-off arm.
    let (mut h_orig, mut h_enc, mut h_lossless) = (0usize, 0usize, 0usize);
    for fx in &FIXTURES {
        let enc = no_hint.encode(fx);
        let dec = no_hint.decode(&enc);
        h_lossless += usize::from(dec == **fx);
        h_orig += fx.len();
        h_enc += enc.len();
    }
    let h_ratio = h_enc as f64 / h_orig as f64;
    println!(
        "NO-HINT: orig={h_orig}B enc={h_enc}B ratio={h_ratio:.3} saved={:.1}% lossless={h_lossless}/10",
        (1.0 - h_ratio) * 100.0
    );
}
