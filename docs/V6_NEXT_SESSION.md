# V6 Next Session Handoff

**Prepared:** 2026-08-17
**Branch:** `v6-dev`
**Latest commit:** `e4efa2f` — role-aware scoring, coverage grace, number bonus

## Current Results

After role-aware episodic records, coverage grace, and number-proximity bonus
(50q A/B, 2026-08-18, commit `e4efa2f`):

- R@1: `0.74` (up from `0.68`)
- R@5: `0.98` (up from `0.90`)
- R@10: `0.98` (held)
- MRR: `0.8400` (up from `0.7654`)
- Candidate presence: `1.00` (held)
- Expected-session presence: `1.00` (held)
- Query p50: `214.0 ms`
- Query p95: `430.3 ms`
- Total wall clock: `126.5 s`

All acceptance gates pass. 4 new R@1 wins (bikes, RAM, bass, Spotify),
1 regression (IKEA bookshelf assembly, rank 1→2). Net +3 R@1.
The 13 remaining R@1 misses are all ranking losses with candidate present;
8 are at rank 2–3.

## Next Slice

Done across sessions:
1. Cold/warm in-process search measured (10k: cold `0.520 ms`, warm `0.355 ms`).
2. Batch sidecar ingest accepted (`append_batch` + `memory.batch_create`; 1k
   records `66.4 ms` vs `708.9 ms` single).
3. Typed index-time keys in `wm-memory/src/episodic_keys.rs`.
4. Query-class planner in `wm-memory/src/query_planner.rs`.
5. 50q A/B with keys+planner: R@1 `0.68`, R@5 `0.86`, R@10 `0.96`,
   MRR `0.7559`, candidate presence `1.00`.
6. Cross-key term matching: query terms now match against `content_keys` for
   coverage scoring, bridging vocabulary gaps.
7. Vocabulary aliases: direct entity surface forms (dog, cat, yoga, commute,
   play, bookshelf, internet plan).
8. Tuned planner knobs: ExactFact 0.12→0.18, Temporal/KU 0.2→0.15,
   Preference 0.18→0.25, MultiHop 0.1→0.12.
9. 50q A/B with all three: R@1 `0.68`, R@5 `0.90`, R@10 `0.98`,
   MRR `0.7654`, session presence `1.00`. No regressions.
10. Role-aware episodic records: `capture_explicit_memories` sets
    `EpisodicKind::UserStatement`/`AssistantResponse` from tags.
11. Coverage grace for UserStatement: +1 matched term (capped at
    `query_terms.len()`) for coverage calculation. Bridges verb mismatch
    (e.g. query 'take' not in user's answer turn).
12. Number-proximity bonus: `how many/much/long` queries get +0.03 for
    content with numeric tokens or number words.
13. 50q A/B with role+grace+number: R@1 `0.74`, R@5 `0.98`, R@10 `0.98`,
    MRR `0.8400`. Net +3 R@1 (4 wins, 1 regression).

Decision: keep all changes. Next accuracy slice is investigating the IKEA
bookshelf regression and the 8 rank 2–3 near-misses.

Still open:
14. IKEA bookshelf regression: answer in user turn but a different user turn
    in the same session out-ranks it. May need answer-bearing term boost.
15. UCLA is the only question still not in top 10 (candidate rank 28). Query
    'Bachelor's degree in Computer Science' has too many common terms.
16. Latency increased from 118ms to 214ms p50 — need to investigate cause
    (likely the `contains_number_word` scan on every candidate).
17. MCP p95 still includes a fresh `wm serve` process; do not claim it as
    in-process search time.
18. Do not add broad synonym expansion, LLM query rewriting, or full HRR
    indexing before the next 50q class A/B is measured.

## Verification

```bash
cargo test --workspace --all-targets --quiet
cargo clippy --all-targets -- -D warnings
cargo fmt --all -- --check
cargo bench -p wm-memory --bench episodic_bench -- --quick
cargo build --release --bin wm
python3 scripts/curated_smoke_test.py --binary target/release/wm
```

## References

- [`STRATEGY_V6.md`](../STRATEGY_V6.md)
- [`docs/V6_MEMORY_RESEARCH.md`](V6_MEMORY_RESEARCH.md)
- [`docs/V6_EPISODIC_PERFORMANCE_PLAN.md`](V6_EPISODIC_PERFORMANCE_PLAN.md)
- [`docs/V6_ACCURACY_PERFORMANCE_ROADMAP.md`](V6_ACCURACY_PERFORMANCE_ROADMAP.md)
- [`docs/V6_HOLOGRAPHIC_MEMORY.md`](V6_HOLOGRAPHIC_MEMORY.md)
- `WMdocs/benchmarks/LONGMEMEVAL_OPTIMIZATION_ROADMAP.md`
- `WMdocs/whitemagic-v4/v2-reference/README.md`
