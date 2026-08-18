# V6 Next Session Handoff

**Prepared:** 2026-08-17
**Branch:** `v6-dev`
**Latest commit:** `93afbad` — scoring+tuned 50q docs updated

## Current Results

After cross-key term matching, vocabulary aliases, and tuned planner knobs
(50q A/B, 2026-08-18, commit `5742e24`):

- R@1: `0.68` (held from keys+planner)
- R@5: `0.90` (up from `0.86`)
- R@10: `0.98` (up from `0.96`)
- MRR: `0.7654` (up from `0.7559`)
- Candidate presence: `1.00` (held)
- Expected-session presence: `1.00` (up from `0.98`)
- Query p50: `118.3 ms`
- Query p95: `302.6 ms`
- Total wall clock: `103.5 s`

All acceptance gates pass. No regressions. Two questions improved:
Golden Retriever (rank 9→4, R@5 gained), Spotify (not-in-top-10→4, R@5+R@10
gained). The 16 remaining R@1 misses are all ranking losses with candidate
present; 7 are at rank 2–4 (close to R@1).

## Next Slice

Done this session:
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

Decision: keep all changes. Next accuracy slice is dual-granularity
session/segment records for counts and multi-hop.

Still open:
10. Dual-granularity session/segment records for count and multi-hop questions
    (How many bikes, Japan trip duration).
11. UCLA is the only question still not in top 10 (candidate rank 28). Query
    'Bachelor's degree in Computer Science' has too many common terms.
12. MCP p95 still includes a fresh `wm serve` process; do not claim it as
    in-process search time.
13. Do not add broad synonym expansion, LLM query rewriting, or full HRR
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
