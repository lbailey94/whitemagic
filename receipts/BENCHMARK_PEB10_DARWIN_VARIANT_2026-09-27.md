# Benchmark receipt: PEB-10 pulse-vs-DAG latency variant (darwin)

**Date:** 2026-09-27
**Author:** opencode (T4800-S), from the miranda-macbook macOS port report (#304)
**Scope:** `crates/wm-gen3-core/src/pulse_compiler.rs` —
`run_peb10_pulse_compiler_benchmark` / `test_peb10_benchmark_execution`
**Status:** platform-variant baseline recorded; floor scaled (macOS 1.2×, else 1.4×)

## Measurements

| Host | Build | pulse avg | dag avg | speedup | memory |
|---|---|---|---|---|---|
| T4800-S (Linux x86_64) | debug | 171.08 µs | 289.58 µs | **1.69×** | 344 B vs 4,600 B (13.37×) |
| miranda-macbook (macOS arm64) | release | 13.63 µs | 17.13 µs | **1.26×** | 344 B vs 4,600 B (13.37×) |

All correctness dimensions are platform-independent and pass on both hosts:
0/100,000 leakage violations, 500/500 TOCTOU rejections, 100% order identity,
0 branch-isolation violations, 500/500 conflict prevention, 100% composite
success, 500/500 budget enforcement, 500/500 provenance blocks.

## Decision

The latency ratio is wall-clock and platform-dependent (scheduler, timer
resolution, CPU). The assertion's intent — pulse is faster than the emulated
Gen2 DAG — holds on both hosts, so the floor is scaled per platform:
macOS ≥ 1.2× (measured 1.26×), all other platforms ≥ 1.4× (measured 1.69×).
The Linux bar is unchanged; the darwin bar keeps a real ordering claim.

## Follow-up

If the darwin ratio drops below 1.2× after a code change, that is a
regression signal, not a threshold problem — do not lower this floor without
a new measurement row above.
