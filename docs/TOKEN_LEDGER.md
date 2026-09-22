# Token Ledger (v0)

Local, on-device measurement of the state WhiteMagic keeps out of model context.
Nothing in this file describes an off-device report; the ledger never leaves the store.

## What it is

`session.record` and `session.continuity` append one JSON line each to
`<store>/lmdb/savings_ledger.jsonl`; the recall route appends one per call.
`wm ledger` aggregates those rows plus the dispatch counters in
`mutable_tool_stats.json`; `wm stats` prints a compact savings block (the
ledger is local-only — nothing leaves the store):

```bash
wm ledger            # human summary (rollups + unfolded tail)
wm ledger --json     # machine-readable
wm ledger --full     # full-history scan (audits)
wm ledger --rollup   # fold the unfolded tail now
wm ledger --calibrate 3.7   # set the per-store bytes/token divisor
wm stats             # compact savings block at the end
wm ledger --store ~/.local/share/whitemagic
```

## Rollups

`wm ledger` and the `wm stats` savings block read a cursor-based daily rollup
(`<store>/lmdb/savings_rollup.json`) plus only the unfolded tail, so the report
stays cheap as the ledger grows. The fold runs at the daemon checkpoint and on
demand (`wm ledger --rollup`); it is idempotent, advances the cursor only past
complete lines (a torn write is re-read next pass), and keeps folded totals if
the ledger is rotated or shrunk. `wm ledger --full` scans everything for
audits. The raw ledger remains the evidence of record — rollups aggregate, they
do not replace it.

The ledger is evidence, not a gate: a ledger write failure is logged and never
fails the tool call. It is local diagnostic data — exportable and deletable with
the store.

## Metric definitions

| Field | Definition |
|---|---|
| `record.bytes_stored` | Turn content bytes written into the local store. |
| `continuity.bytes_available` | Stored bytes the bounded continuity envelope stands in for. |
| `continuity.bytes_injected` | Bytes the envelope actually placed into the caller's context. |
| `recall.bytes_available` | Full stored content of the results a recall returned. |
| `recall.bytes_injected` | Navigation text actually returned by the recall (scrubbed/bounded). |
| `recall.results` | Result count for the call. |
| `state_to_context_ratio` | `bytes_available / bytes_injected` — the WhiteMagic-attributable compression. |
| `token_equivalent_saved_estimate` | `(bytes_available - bytes_injected) / divisor`. **Estimate**; the divisor defaults to 4.0 and is disclosed in the output. Calibrate per store with `wm ledger --calibrate <bytes_per_token>` (encode a representative sample with the tokenizer of your choice; valid 1.0–16.0). |
| `local_ops` | Dispatch calls by tool family. Every WhiteMagic operation is local compute (LMDB + Tantivy + episodic); none is a model call. |

## Attribution rules (binding for any public use)

1. **Cache is context; memory is attribution.** Provider/harness prompt caching
   (the cache-read share of input tokens) is *not* a WhiteMagic saving. Never
   merge the two numbers, and never describe the cache share as "our saving".
2. **Every percentage names its numerator, denominator, n, date, and method.**
   Numbers without a source link do not ship.
3. **Claim labels apply** (`Measured` / `Observed` / `Hypothesis` /
   `Research goal`). The ledger's state-over-transcript ratio is **Measured**
   from local rows; the token-equivalent is an **estimate** and must be labeled
   as one.
4. **Tokens only in public copy.** Dollar figures do not appear on the public
   site (hosting-plan constraint); cost-per-task belongs in repository and grant
   material.
5. **No off-device telemetry.** The ledger exists only in the store; nothing is
   transmitted, aggregated, or shared by default.

## What this is not

- Not a billing or metering system. It measures context state, not usage.
- Not a claim that WhiteMagic causes provider cache hits.
- Not a substitute for the T1 harness: the rigorous number is cost/tokens per
  task **with and without** WhiteMagic, published with the traps from
  `BENCHMARK_LANDSCAPE_2026-09-19.md`.

## Status and next steps

- **v0 (this slice):** record/continuity/recall rows + `wm ledger` aggregation.
- **v0.1 (2026-09-22):** cursor-based daily rollups (`savings_rollup.json`,
  folded at the daemon checkpoint and via `wm ledger --rollup`), so `wm ledger`
  and `wm stats` read rollups + the unfolded tail; `--full` for audits.
- **Backfill report:** `python3 scripts/token_ledger_report.py [--json]` scans every
  project store's dispatch counters and ledger plus the opencode session DB — entirely
  locally — and prints the cache-context and state-over-transcript picture. First run
  (2026-09-21): 8 stores · 246,122 local WM ops · 1,242 opencode sessions with a 97.59%
  cache-served share (context, not attribution) · ledger rows begin at the next
  record/continuity.
- **Next:** dashboard panel; tokenizer calibration.
- **Then:** T1 with/without delta; the tokens-only public artifact.

Heritage: Gen1 shipped `consciousness.token_economy` / `consciousness.token_report`;
the Phase-4 archaeology verdict was "token_economy mostly real instrumentation".
This is that watcher, revived at the dispatch seam with attribution rules.
