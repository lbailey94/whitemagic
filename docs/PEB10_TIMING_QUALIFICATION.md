# PEB-10 timing qualification

The `test_peb10_benchmark_execution` unit test checks deterministic state,
isolation, TOCTOU, conflict, budget, provenance, and memory invariants. It still
prints timing observations, but timing does not decide functional test success.

Run `python3 benchmarks/qualify_peb10_timing.py` to collect seven independent
release-mode executions. The harness records the host, Rust compiler, every
sample, and the sample range and median. The retained Linux qualification floor
is a median speedup of 1.4x. The comparison's Gen2 DAG is emulated by the
benchmark and is not a measurement of a historical production implementation.
Shared CI hosts can still vary; the full samples make that variability visible.

## Current result: unqualified

The public v10.4.0 source revision `19169fa8c2fccfb51fc1b1b6e0c762257288a65`
did not meet the retained floor in [Benchmarks run 39058427484](https://github.com/lbailey94/whitemagic/actions/runs/39058427484).
Its [uploaded PEB-10 timing artifact](https://github.com/lbailey94/whitemagic/actions/runs/39058427484/artifacts/12110283492)
contains seven samples:

`1.114017109938, 1.083083465136, 1.101908304498, 1.197109677273, 1.120952899106, 1.138141822918, 1.104045413013`.

The median is `1.114017109938x` (range `1.083083465136x–1.197109677273x`),
below the unchanged `1.4x` floor. This revision remains **unqualified for the
PEB-10 performance criterion**. The comparison is a repeatable wall-clock
comparison against an emulated DAG baseline, not historical production
performance. Do not infer a performance pass from functional tests, release
availability, or install certification.

The next useful step is to profile the Pulse and emulated-DAG paths by phase on
a controlled runner, retaining the existing fixture and floor. That can locate
the measured cost before proposing any source change; it does not itself change
this failed result or qualify a later revision.
