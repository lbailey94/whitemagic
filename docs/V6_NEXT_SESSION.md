# V6 Next Session Handoff

**Prepared:** 2026-08-17
**Branch:** `v6-dev`
**Latest commit:** `9992487` plus the current roadmap documentation

## Current Results

The v6 episodic path currently records:

- R@1: `0.66`
- R@5: `0.86`
- R@10: `0.94`
- MRR: `0.7403`
- Candidate presence: `0.96`
- Expected-session presence: `0.98`
- Query p50: `78.0 ms`
- Query p95: `168.2 ms`

The accepted v6 term sidecar and bounded candidate path preserve accuracy and
bring p50 below the `100 ms` target. P95 remains above the `150 ms` target and
needs process-boundary and tail profiling.

## Next Slice

1. Run cold versus warm in-process and MCP latency measurements.
2. Measure batch episodic indexing separately from single-record capture.
3. Add specific index-time entity/date/domain keys from the earlier WhiteMagic
   keyword V2 strategy.
4. Add a query-class planner for exact, temporal, update, multi-hop, preference,
   and procedural queries.
5. Re-run the fixed 50-question A/B by query class.
6. Do not add broad synonym expansion, LLM query rewriting, or full HRR
   indexing before these deterministic experiments are measured.

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
