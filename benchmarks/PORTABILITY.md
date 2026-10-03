# Benchmark driver portability

All `benchmarks/driver_*.py` scripts resolve the checkout root from the
environment (2026-09-27 macOS port report: they hardcoded the ThinkPad path,
so a valid Mac checkout could not run Phase 1→3 without editing files).

| Variable | Default | Purpose |
|---|---|---|
| `WMGEN3_ROOT` | `/home/lucas/Desktop/WMgen3` | Gen3 checkout root (all drivers) |
| `WMGEN3_BIN` | `<WMGEN3_ROOT>/target/release/wm-gen3` | Binary under test (`driver_phase3_constitutional_fuzzing.py`, `driver_phase5_scale_slopes.py`) |
| `WMGEN3_EXPECTED_HASH` | platform baseline (below) | Override the pinned core-binary hash check |

## Platform-variant baseline lane

The core-binary hash is platform-specific; both baselines are blessed:

| Platform | `sys.platform` | sha256 |
|---|---|---|
| Linux x86_64 (T4800-S) | `linux` | `a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44` |
| macOS arm64 (miranda-macbook) | `darwin` | `c2ec0c714858613a65f3b9374d9f0a48cd22d7df3ceb60da6afbe3fe2fdf2062` |

On any other host, set `WMGEN3_EXPECTED_HASH` explicitly (a hash mismatch
fails loudly, by design — the receipt records which binary produced a run).

Example (macOS seat):

```sh
WMGEN3_ROOT=~/wmgen3 \
WMGEN3_BIN=~/wmgen3/target/release/wm-gen3 \
python3 benchmarks/driver_phase3_constitutional_fuzzing.py
```

Related: `receipts/BENCHMARK_PEB10_DARWIN_VARIANT_2026-09-27.md` (pulse-vs-DAG
latency variant), `receipts/BOUNDARY_MESH_TRANSPORT_SPAWNS_2026-09-27.md`.
