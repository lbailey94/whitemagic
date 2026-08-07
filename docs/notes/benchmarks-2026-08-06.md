# WhiteMagic v4 Performance Benchmarks — 2026-08-06

## Environment

- **Binary**: `target/release/wm` (15 MB, release profile, optimized)
- **Store**: `.whitemagic/lmdb/` (1 GB map size, 14 galaxies, ~120 entries)
- **Runtime**: Linux, 8-core CPU, 32 GB RAM
- **Build**: Rust 1.85+, `--release` profile

---

## Summary

| Metric | Value |
|--------|-------|
| Binary size | 15 MB |
| Startup time (cold) | 40 ms |
| Startup time (warm) | 10–15 ms |
| Idle CPU | 0 ticks over 2s (zero overhead) |
| Max RSS | ~12.5 MB |
| MCP round-trip (init + dispatch) | 21–26 ms warm |
| Direct tool dispatch (gnosis) | 21–26 ms |
| WM meta-tool dispatch (NLU route) | 23–26 ms |

---

## Criterion Benchmarks

### Bicameral Router (wm-bicameral)

| Benchmark | Time | Notes |
|-----------|------|-------|
| `classify_simple` | 2.89 µs | TF-IDF NLU classification, simple input |
| `classify_medium` | 3.93 µs | Medium complexity input |
| `classify_complex` | 5.32 µs | Complex multi-intent input |
| `route_simple_with_handlers` | 4.65 µs | Full routing with handler dispatch |
| `route_complex_with_handlers` | 5.92 µs | Complex routing with handlers |
| `budget_record_usage` | 2.51 ns | Budget tracking, atomic ops |
| `budget_recommend_downgrade` | 595 ps | Budget recommendation check |
| `budget_summary` | 2.37 ns | Budget summary computation |
| `bicameral_reason_with_router` | 4.27 µs | Full bicameral reasoning cycle |
| `bicameral_classify_with_router` | 3.21 µs | Bicameral classification |
| `speculative_decode_draft_accepted` | 275 ns | Speculative decoding (accepted) |
| `speculative_decode_with_verify` | 1.85 µs | Speculative decoding with verification |
| `speculative_stats` | 16.7 ns | Stats update |

### Consciousness (wm-consciousness)

| Benchmark | Time | Notes |
|-----------|------|-------|
| `dream_cycle/10_memories` | 53.8 ms | Dream cycle consolidation, 10 memories |

### Memory (wm-memory)

| Benchmark | Time | Notes |
|-----------|------|-------|
| `tantivy_search/rust` | 42.6 µs | Full-text search, "rust" query |
| `tantivy_search/memory` | 43.7 µs | Full-text search, "memory" query |
| `tantivy_search/benchmark` | 42.5 µs | Full-text search, "benchmark" query |
| `tantivy_search/django` | 42.0 µs | Full-text search, "django" query |
| `lmdb_put_batch/individual_100` | 105.8 ms | 100 individual LMDB writes |
| `lmdb_put_batch/batch_100` | 17.4 ms | 100 batched LMDB writes (6x faster) |
| `lmdb_put_batch/individual_1000` | 979 ms | 1000 individual LMDB writes |
| `lmdb_put_batch/batch_1000` | 54.6 ms | 1000 batched LMDB writes (18x faster) |

### Dispatch (wm-dispatch)

| Benchmark | Time | Notes |
|-----------|------|-------|
| `dispatch_e_stop` | 33.1 ns | Emergency stop dispatch |
| `dispatch_all_8_builtins` | 252 ns | Dispatch through all 8 builtin tools |
| `safety_bitmask_check` | 1.28 ns | Safety bitmask evaluation |

---

## MCP Server Performance

### Startup Latency

| Run | Wall Clock | Notes |
|-----|-----------|-------|
| 1 (cold) | 40 ms | First run, cold caches |
| 2 (warm) | 10 ms | Warm caches |
| 3 (warm) | 10 ms | Warm caches |

### MCP Round-Trip (Initialize + Tool Dispatch)

**WM meta-tool (NLU routing)**:

| Run | Total Latency |
|-----|--------------|
| 1 (cold) | 93 ms |
| 2 (warm) | 26 ms |
| 3 (warm) | 24 ms |
| 4 (warm) | 25 ms |
| 5 (warm) | 23 ms |

**Direct tool call (gnosis)**:

| Run | Total Latency |
|-----|--------------|
| 1 (cold) | 34 ms |
| 2 (warm) | 22 ms |
| 3 (warm) | 26 ms |
| 4 (warm) | 21 ms |
| 5 (warm) | 22 ms |

**Direct tool call (memory.create)**:

| Run | Total Latency |
|-----|--------------|
| 1 (cold) | 30 ms |
| 2 (warm) | 21 ms |
| 3 (warm) | 23 ms |

### Idle Resource Usage

- **CPU**: 0 ticks (utime + stime) over 2 seconds with no requests — zero idle overhead
- **Max RSS**: ~12.5 MB resident set
- **Binary size**: 15 MB

---

## Key Findings

1. **NLU routing overhead is negligible**: WM meta-tool dispatch (23–26 ms) is within 1–2 ms of direct tool dispatch (21–26 ms). The TF-IDF classify step adds ~3–5 µs, dwarfed by LMDB I/O.

2. **Batch writes are 6–18x faster**: LMDB batch writes significantly outperform individual writes (17 ms vs 106 ms for 100 entries; 55 ms vs 979 ms for 1000 entries).

3. **Full-text search is sub-50 µs**: Tantivy search consistently delivers ~42 µs per query across all test terms.

4. **Dispatch pipeline is nanosecond-scale**: The core dispatch path (safety check + tool call) takes 33–252 ns, with safety bitmask checks at 1.28 ns.

5. **Zero idle overhead**: The server consumes no CPU when idle, confirming the brain-wave eco mode effectively suspends background processing in Delta state.

6. **Low memory footprint**: 12.5 MB RSS for a 169-tool, 19-crate cognitive architecture with LMDB + Tantivy + consciousness subsystems.

7. **Fast startup**: 10–15 ms warm startup makes the server suitable for short-lived MCP sessions.
