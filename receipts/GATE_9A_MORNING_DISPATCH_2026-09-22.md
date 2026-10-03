# Gate 9A morning dispatch — 2026-09-22

Status: active work allocation, not a closure verdict. Overnight changes were planning only.
Latest root independent checks before dispatch: 9 Store tests and 12 documentation tests passed.
Those focused results do not replace a refreshed integrated acceptance battery.

## Parallel work started

Terra: runnable bounded synthetic sizing using actual Rust tokenizer/candidate behavior; count
records AND raw record bytes, posting bytes, token expansion, relations, pairs, and effects.
Use an explicit fixture resource cap; no real stores or models. Report measured envelope,
repeatability and proposed conservative limits. Do not confuse measured timings with universal
performance qualification. No production mutation path changes in this sizing step.

Sol: implement immutable sweep request/effect/usage/receipt types and canonical validation/framing
with explicit limits. Numeric production ceilings await Terra; configurable limits permit unit
boundary tests now. Compiler authorization must require trusted sealed planner/usage evidence,
not merely a caller-chosen digest. Same CommitCapability, no parallel sweep authority. Do not
connect production writers before the validated preflight/storage interfaces are ready.

Coordinator: settle receipt and caller compatibility, review sizing/validation, then orchestrate
storage integration and independent evidence. Ops/harness edits remain coordinator-owned until
explicitly reassigned. No overlapping code ownership.

## Integration direction, not yet implemented

- Preserve current usage-dependent lifecycle semantics with explicitly volatile, trusted
  process-local snapshot evidence. Never substitute age-only demotion.
- Disabled sweep is a typed no-op with no canonical writes. Errors propagate, never ID zero.
- Receipt decoding needs an explicit operation discriminator. Prefer a fresh-only format bump
  when the common intake/sweep envelope lands; reject unsupported prior format, no migration.
- One operation-ID namespace per realm; reuse across kinds conflicts.
- Replay must identify the original exact plan before recomputing from changed state or usage.
  A newly scanned effect list under the old ID is not a valid replay implementation.
- Automatic post-batch sweep cannot share an intake receipt. Preserve it only with a distinct,
  specified operation/retry contract, or explicitly report not_requested and document the
  compatibility change. No unreceipted automatic mutation remains in the qualified path.

## Remaining closure work after sweep

Derived-cache authority/version/invalidation boundaries; production article/adversary coverage;
exact candidate integrated tests, release/features and source hashes; explicit findings verdict.
Do not declare these complete merely because the canonical sweep transaction passes.
