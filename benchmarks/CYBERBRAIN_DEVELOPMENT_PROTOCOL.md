# Cyberbrain development fixture protocol v2

This revision exercises the existing synthetic development corpus. It does
not change its authored routing prompts, routing accuracy floors or other
semantic checks, and it is not a frozen answer-quality holdout.

The earlier Mac run at source `ce064eb0` recorded 200 baseline inputs and 134
retained inputs, with directory file lengths reported as 536 KiB and 520 KiB
(3.0% reduction; the legacy output labelled bytes/1024 as KB). It failed the
then-required `>5%` assertion. That result
remains a failure under its original protocol; it is not rescored as passing.
The raw [native CI result](https://github.com/lbailey94/whitemagic/actions/runs/41903807890/job/126833514035)
and retained delivery logs identify that original observation.

`dir_size` sums file lengths, including LMDB's page-sized data file, locks
and journals. It does not measure retained logical payload bytes or allocated
filesystem blocks. Page size, allocation/reuse and fixed file overhead can
dominate a 200-input debug fixture. A universal percentage reduction is not
an intake correctness invariant.

Protocol v2 therefore asserts actual outcomes:

- Every baseline input produces a successful insert result; failures are no
  longer discarded while incrementing the displayed count.
- Every retained gated insert succeeds.
- The dropped count equals the separately collected noise and antibody
  classifications.
- Successful retained inputs plus deliberately dropped inputs account for
  the entire corpus.
- The existing nonzero antibody/redaction controls and all later semantic
  routing, supersession and fallback checks remain active.

Raw directory file lengths, their observed reduction and elapsed times remain
printed for each new run, with no host-independent storage/performance floor.
The reduction percentage retains its earlier zero-clamped formula; raw sizes
must be consulted if the gated directory grows. No physical storage saving,
network containment, paid cloud-call saving or independent adoption follows
from these synthetic measurements.

Summary labels now report counted antibody/redaction verdicts, simulated
cloud-tier decisions, the selected glyph counts and the reported struct-size
estimate. They do not assert unmeasured nanosecond antibody latency, actual
paid-call savings, zero egress, safe workload execution, or cache residency.
The underlying numeric observations and semantic expectations are unchanged.

Run the current fixture with:

```sh
cargo test -p wm-gen3-core --features operator --test cyberbrain_valkyrie_benchmark -- --nocapture
```

Debug uses 200 inputs and release uses 1,000. Label new results as protocol v2
and keep prior attempts intact. Do not substitute a development rerun for an
independently frozen answer-quality evaluation.
