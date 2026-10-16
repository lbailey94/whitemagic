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
