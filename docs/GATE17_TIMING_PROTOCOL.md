# Gate17 full-recall timing protocol v1

The functional Gate17 tests always check three-record/two-hop retrieval and
Hebbian co-activation/consolidation. Their diagnostic elapsed time is not a
performance qualification. A macOS debug CI run retained on November 11,
2026 failed its former single-measurement 5ms assertion at 6.007291ms. That
observation remains a failure under the former protocol.

This protocol measures the complete `Substrate::recall` operation, including
lexical scoring, LMDB reads, relation traversal and journal writes. It does
not isolate graph diffusion or establish a general sub-millisecond claim.

Run `bash scripts/qualify_gate17_timing.sh /fresh/path/results.log` from the
repository root. The wrapper refuses an existing output path and runs exactly
`test_gate17_release_recall_latency` with `--release`, `--ignored`, `--exact`
and `--test-threads=1`. The test refuses a debug build. CI requires this
qualification separately on Linux x86-64 and macOS arm64 and retains each log.

The fixture has three synthetic linked target records plus the temporary
substrate helper's baseline seed. One target is the lexical seed and two
causal edges connect the three targets. Its flat-query control precedes edge
insertion. The timed sequence
contains nine consecutive full recalls, beginning with the first resonant
query after setup; there is no discarded warm-up or outlier. Every query must
return all three linked records, and **every sample must be strictly below
5,000,000ns**. The budget is unchanged; no median replaces a failed sample.

The test emits all nine nanosecond durations, profile, OS/architecture and
the wrapper-supplied source revision and test/recall-source SHA-256 hashes.
The wrapper checks the exact test execution, passing summary, one complete
timing record, source bindings, sample count and unchanged strict budget.
Zero filtered tests, ignored tests, absent/incorrect records and over-budget
samples fail qualification even if a command exits successfully.

These source identities describe observed inputs, not a signed build
attestation. A pass applies to this fixture, build profile and observed host;
it does not establish an arbitrary-corpus latency guarantee. The retained
debug failure is not rescored using this new protocol.
