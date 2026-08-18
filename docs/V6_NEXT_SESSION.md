# V6 Next Session Handoff

**Prepared:** 2026-08-17
**Branch:** `v6-dev`
**Latest commit:** `9992487` plus the current roadmap documentation

## Current Results

After typed keys + query-class planner (50q A/B, 2026-08-18):

- R@1: `0.68` (up from `0.66`)
- R@5: `0.86` (held)
- R@10: `0.96` (up from `0.94`)
- MRR: `0.7559` (up from `0.7403`)
- Candidate presence: `1.00` (up from `0.96`)
- Expected-session presence: `0.98` (held)
- Query p50: `115.6 ms` (up from `78.0 ms`; planner raises candidate budgets)
- Query p95: `281.3 ms` (up from `168.2 ms`; same cause)
- Total wall clock: `104.6 s` (down from `172.4 s`; batch ingest)

All acceptance gates pass. Two questions improved (tennis racket R@1, Japan
trip R@5), one regressed (Feb 14th R@5). The 16 remaining R@1 misses are all
ranking losses with candidate present — not candidate retrieval failures.

## Next Slice

Done this session:
1. Cold/warm in-process search measured (10k: cold `0.520 ms`, warm `0.355 ms`).
2. Batch sidecar ingest accepted (`append_batch` + `memory.batch_create`; 1k
   records `66.4 ms` vs `708.9 ms` single).
3. Typed index-time keys in `wm-memory/src/episodic_keys.rs`.
4. Query-class planner in `wm-memory/src/query_planner.rs`.
5. 50q A/B completed: R@1 `0.68`, R@5 `0.86`, R@10 `0.96`, MRR `0.7559`,
   candidate presence `1.00`. All gates pass.

Decision (per prior session's branch logic): R@5 held at 0.86, R@1/MRR moved
up. Keep keys+planner. Next accuracy slice is dual-granularity session/segment
records for counts and multi-hop.

Still open:
6. Dual-granularity session/segment records for count and multi-hop questions
   (How many bikes, Japan trip duration).
7. Query-class scoring on the existing candidate set for the 16 R@1 ranking
   misses (temporal recency, validity, preference lane).
8. MCP p95 still includes a fresh `wm serve` process; do not claim it as
   in-process search time.
9. Do not add broad synonym expansion, LLM query rewriting, or full HRR
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
