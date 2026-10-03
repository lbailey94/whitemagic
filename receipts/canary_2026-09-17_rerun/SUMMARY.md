# Nucleus-freeze canaries — re-run on the current tip (2026-09-17)

**Status: floor-check evidence for WMgen3 tip `c4d25d3` (tree clean, 2026-09-17 evening).**
The frozen bundle `receipts/canary_2026-09-17/` (freeze reference, `SHA256SUMS` `941abc80…`) is
**untouched**; this directory is a separate re-confirmation run on the code as moved since the
freeze (exact-hash gate, `insufficient_evidence` vocabulary, read-only discipline, additive route
fields). All runs executed by opencode session `68c17d3b-757b-476e-9d74-d3c8366d9a5c` at tip
`c4d25d3`.

**Binary under test:** `target/release/wm-gen3`, sha256
`e6e7ee06a935f2c0868abbba33aa6140b5a846a2104494ce9a774d4f3f52c828` (release rebuild,
fingerprint-fresh; same binary as the A2 discipline demonstration `IMPL_A2_DISCIPLINE_2026-09-17`).
**Fixture/drivers:** copied verbatim from the frozen bundle (hashes match; see `SHA256SUMS`).
**Method:** the seven frozen cells re-executed per `ENVIRONMENT.txt` (fresh stores; journal +
hash-out per run); `drivers/compare.py` asserts cell-by-cell equality of journal readings against
the frozen journals, then runs the C1–C6-specific assertions. **12/12 assertions PASS.**

## Canary results (re-run vs frozen readings)

| # | Canary | Result | Evidence |
|---|---|---|---|
| C1 | Closure canaries (Law + Evidence) | **PASS** | `scripts/check_closures.sh` static scans pass · `cargo test --offline`: 38 passed / 0 failed / 1 ignored + 5 doc compile-fail tests (additive tests since the freeze; was 28) · runtime: `A1` `canary.probe` laundering refused, domains `[Simulated]`, `boundary.refusal` = 1, `closure.violation` = 0 |
| C2 | R ablation changes ordering | **PASS** | `A1` (sweep on): 5 `relation.proposed` (rule `candidacy.v1…`; F4 within-sweep duplicates still observable — O1), recall order `[1 stratum 0, 0 stratum 2 superseded_by 4]` · `A2` (fresh store, sweep off): `think.sweep` `disabled:true`, 0 proposals, order `[0 stratum 1, 1 stratum 1]` |
| C3 | Count-gate ablation reverts to declared behaviour | **PASS** | `B_count`: fired `[false, true, true]` for lexical candidates `[2, 1, 0]` · `B_floor` (falsified mode): `[false, false, true]` · `B_off` (always-on): no gate events, `projection.load` present · `B_soff`: projection absent |
| C4 | Provenance completeness at result granularity | **PASS** | `provenance.chain` complete `true` 100 % in all seven runs (2/2, 2/2, 2/2, 3/3 ×4); zero `closure.violation` in every journal |
| C5 | Round-trip relation kinds/endpoints | **PASS** | `A3` = fresh process on store A with sweep off: `inspect` relations byte-identical to A1 (5 relations, `kind: Supersedes`, `src`/`dst`/`state`/`w`/`c`/`t`/`rule_id`); recall still applies `superseded_by: 4`, strata 0/2 |
| C6 | Reachable-effectful acceptance | **PASS** | verb → journal-visible effect inventory intact: `memory.batch_create` → `ingest.batch` · `think` → `think.sweep` + `relation.proposed` (A1) · `memory.episodic_search` → `selection.decision` + `provenance.chain` (all) · `gen3.canary` → `canary.probe` + `boundary.refusal` (A1/A2) · lens slot → `projection.gate`/`projection.load` (B_count/B_floor/B_off) · `run.end` `journal_ok:true` everywhere |

## Comparison details

- **Journal readings identical in 7/7 cells** — typed inventory, sweeps, proposals, decisions,
  gates, provenance, probes, `run.end` (comparison scope = the declared instrument set of
  `drivers/analyze.py`; additive fields landed since the freeze have no frozen baseline and are
  disclosed by their own receipt, `IMPL_A2_DISCIPLINE_2026-09-17`).
- **Responses byte-identical to the frozen bundle in 6/7 cells.**
- **Disclosed exception — `B_off`:** the ingest response differs only by wall-clock `took_ms`
  0 → 1 in the `sweep` block; no behavioural difference (computed diff, all other keys equal).

## Observations carried (unchanged)

- **O1 — duplicate proposals within one sweep** (F4): A1 still shows 5 relations on the same
  `(src=1, dst=0)` pair; `existing` snapshotted pre-loop. Direction/ordering unaffected; relation
  counts inflated. Carried for a future registration (as at the freeze).
- **O2 — gate activation shown, not outcome differences** (synthetic fixture): unchanged; the B
  result sets remain identical across cells.
- **O3 — canary record included** in `run.end.records` (3 in A runs): unchanged.

## Reproduction

Same cells as the frozen bundle (`ENVIRONMENT.txt`, and `drivers/run.sh` is the exact driver used):

```bash
BIN=/home/lucas/Desktop/WMgen3/target/release/wm-gen3
CACHE=/home/lucas/Desktop/WHITEMAGIC/WMv9/.fastembed_cache
# A1 (sweep on, structural):      WM_GEN3_ARBITRATION=structural $BIN serve --store <A>  < fixtures/A_full.jsonl
# A2 (fresh store, A1 ablation):  WM_GEN3_SWEEP=0 WM_GEN3_ARBITRATION=structural $BIN serve --store <A2> < fixtures/A_full.jsonl
# A3 (store A, second process):   WM_GEN3_SWEEP=0 WM_GEN3_ARBITRATION=structural $BIN serve --store <A>  < fixtures/A_query_only.jsonl
# B cells (fresh store each):     WM_GEN3_PROJECTION=1 [WM_GEN3_PROJECTION_GATED=count|1] WM_GEN3_EMBED_CACHE=$CACHE \
#                                 WM_GEN3_SWEEP=0 WM_GEN3_ARBITRATION=structural $BIN serve --store <B> < fixtures/B_full.jsonl
# B soff: WM_GEN3_PROJECTION=0 …
# (WM_GEN3_JOURNAL / WM_GEN3_JOURNAL_HASH_OUT set per run.)
```

Analysis: `python3 drivers/analyze.py journals/*.journal.jsonl` ·
comparison: `python3 drivers/compare.py` (12/12 PASS).

**No verdict, claim, gate, or threshold movement** — this bundle re-confirms C1–C6 on the current
tip; the frozen bundle remains the freeze-time reference.
