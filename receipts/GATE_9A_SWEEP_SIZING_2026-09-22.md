# Gate 9A bounded synthetic sweep sizing — 2026-09-22

**Status:** synthetic preflight sizing evidence only. It does not implement a Store writer,
invoke `think_sweep`, access a real store or history, invoke a model, ratify policy, or close
Gate 9A.

## Runnable artifact and method

[`crates/wm-gen3-core/tests/gate9a_sweep_sizing.rs`](../crates/wm-gen3-core/tests/gate9a_sweep_sizing.rs)
constructs in-memory synthetic `EvidenceStore` records and calls the actual Rust
`field::tokenize` and `field::propose_supersedes` functions. It reproduces the current deterministic
token-index, document-frequency, lexical pair order, duplicate-pair exclusion, and proposal rule;
it does **not** call the mutating `Substrate::think_sweep` path. Posting bytes are encoded as the
actual `rmp_serde` `Vec<u64>` shape used by Store postings. “Raw record bytes” here means exact
input `content + source` bytes, not guessed MessagePack `WireRecord` bytes; the future LMDB
preflight must measure its actual decoded/serialized reads separately.

Fixture safety caps are explicit: 384 records, 2,048 extra-byte single token, 512 synthetic
relations, 786,432 total content bytes, 20,000 token occurrences, 131,072 posting bytes, 32,768
pair examinations, and 8,192 effects. The harness aborts if a cap is crossed. Every fixture is
repeated three times; only its deterministic observed counts are compared, not timing.

Command and result, on `rustc 1.98.0 (88d9e12ae 2026-08-18)`:

```text
cargo test --offline --locked -p wm-gen3-core --test gate9a_sweep_sizing -- --nocapture
1 passed; 0 failed
```

| Fixture × 3 | Records | Raw bytes / max record | Token occurrences | Posting bytes | Relations | Pairs | Effects | Elapsed range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| small | 32 | 2,032 / 65 | 128 | 204 | 32 | 62 | 28 | 2,499–3,290 µs |
| medium | 160 | 10,287 / 67 | 640 | 976 | 192 | 2,320 | 480 | 69,547–82,632 µs |
| stress | 384 | 26,897 / 2,111 | 1,537 | 3,603 | 512 | 14,084 | 3,108 | 358,306–415,487 µs |

The stress fixture deliberately contains one 2 KiB token. Token occurrences alone would make it
appear close to the ordinary fixture shape while its raw allocation is materially different.
Timing is a debug-build observation on this machine, not a universal performance or capacity
claim.

## Provisional ceiling recommendation for ratification review

Use hard refusal, never truncation, and bind every selected value into the future request and
receipt policy digest. The following is a conservative **starting proposal**, not a ratified
production policy: it stays above the measured medium case but below capped stress in each primary
dimension, leaving the stress fixture as a refusal test and avoiding extrapolation beyond observed
work.

| Preflight dimension | Proposed starting ceiling | Basis / headroom |
|---|---:|---|
| records scanned | 256 | 1.6× medium; 2/3 capped stress |
| raw record bytes (aggregate) | 16 KiB | > medium 10,287 B; rejects 26,897 B stress payload |
| raw bytes per record | 1 KiB | catches the 2,111 B single-token stress record |
| token occurrences | 1,024 | 1.6× medium; below stress 1,537 |
| posting bytes decoded | 2 KiB | ~2× medium; below stress 3,603 B |
| relations scanned | 256 | > medium 192; 1/2 fixture cap |
| pair examinations | 8,192 | >3× medium; below stress 14,084 |
| emitted effects | 1,024 | >2× medium; below stress 3,108 |

The prior six-limit shape omits raw input bytes. This measurement requires adding aggregate raw
record bytes and preferably a per-record raw-byte limit to the immutable `SweepLimits` and its
digest; posting bytes and token counts cannot substitute. If the operator chooses a different
machine envelope or workload objective, rerun the bounded fixture with an explicitly revised cap
and replace this table rather than silently raising a constant.

## First transactional API dependencies

Sol’s pending immutable sweep request must bind: operation ID, realm, expected global epoch,
authority descriptor/digest, ordered effects, limits, **observed counts**, policy digest, and
trusted process-local usage-snapshot digest. The compiler must issue the same `CommitCapability`
for a distinct sweep scope/kind. Receipt direction is an explicitly tagged intake/sweep envelope
and fresh-only Store v5, rejecting v4 with no migration; the exact byte schema remains a
coordinator decision. Replay must retrieve the original sealed plan by operation ID rather than
rescan.

Only after those types and ceilings are ratified should Store add a `commit_sweep` transaction:
validate capability/replay/format/epoch/read set and all observed limits, allocate counters,
apply the exact ordered effects, advance epoch, then write one nullifier and tagged receipt.

## Next focused acceptance cases

1. Every one-over limit, including aggregate and per-record raw bytes, refuses before capability
   issuance with no durable effects after reopen.
2. The stress single-token fixture crosses raw-byte policy even when its token count is acceptable.
3. Repeated just-under fixtures have identical observed and effect digests; timings are not part
   of equality.
4. A stale epoch, changed observed/limits/effects/usage digest, or duplicate relation pair has no
   counter, relation, epoch, nullifier, or receipt effect.
5. Transaction cut points after each relation, both counters, epoch, nullifier, and receipt roll
   back fully; disabled/error paths return typed outcomes with no allocation.
