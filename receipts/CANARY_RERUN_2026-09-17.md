# RECEIPT — Canary floor check C1–C6 re-run on tip `c4d25d3` (2026-09-17)

**Status: evidence — floor check; no operator act required (no freeze, no verdict).** AI session
`68c17d3b-757b-476e-9d74-d3c8366d9a5c` (opencode) executed and attests. Append-only.

---

## 1. Artifact

| Field | Value |
|---|---|
| Bundle | `receipts/canary_2026-09-17_rerun/` (30 files) |
| **SHA256SUMS** | `01532868a96d3c2932aae9b2cbd19cccd9d8c65e95cafb78a30834e760b57c2e` |
| Frozen bundle (untouched) | `receipts/canary_2026-09-17/` (`SHA256SUMS` `941abc80…`) |
| Binary under test | `e6e7ee06a935f2c0868abbba33aa6140b5a846a2104494ce9a774d4f3f52c828` (release rebuild) |
| Tip | `c4d25d3`, tree clean |

## 2. Trigger

Code moved under the freeze-time canaries after `7ff9181`/binary `b1c66fec`: exact-hash gate
(`8c5e32f`), `insufficient_evidence` vocabulary (`a588ae1`), floor bounds (`41532c6`), read-only +
starvation/route discipline (`e3c6c6d`, demo `c4d25d3`). Floor re-check per the toolchain/bump
policy: fresh canaries on code motion.

## 3. Method

Frozen fixtures + drivers copied verbatim (hash-matched); all seven cells re-executed per the
frozen bundle's `ENVIRONMENT.txt` recipe (fresh stores, journal + hash-out per run);
`drivers/compare.py` asserts cell-by-cell equality of journal readings vs the frozen journals, then
the C1–C6 assertions.

## 4. Result — 12/12 assertions PASS

- **C1** — closure static scans PASS; tests **38/0/1** + 5 doc compile-fail (additive since freeze);
  runtime `canary.probe` laundering refused, `boundary.refusal` = 1, `closure.violation` = 0.
- **C2** — R ablation ordering flip intact (A1 `[1 s0, 0 s2 sup4]` / 5 proposals vs A2 `[0 s1, 1 s1]`
  / 0 proposals, sweep disabled).
- **C3** — count gate `[false,true,true]` on candidates `[2,1,0]`; floor mode `[false,false,true]`;
  always-on: no gate events + `projection.load`; off: projection absent.
- **C4** — provenance chains 100 % complete in all 7 runs; zero violations.
- **C5** — A3 (fresh process, sweep off) `inspect` relations byte-identical to A1.
- **C6** — verb→event inventory intact (`ingest.batch` · `think.sweep`/`relation.proposed` ·
  `selection.decision`/`provenance.chain` · `canary.probe`/`boundary.refusal` ·
  `projection.gate`/`projection.load` · `run.end` `journal_ok` everywhere).

## 5. Disclosures

- Journal readings identical in 7/7 cells **under the declared instrument set** (`drivers/analyze.py`);
  additive fields landed since the freeze have no frozen baseline (disclosed by their own receipt,
  `IMPL_A2_DISCIPLINE_2026-09-17`).
- Responses byte-identical to the frozen bundle in 6/7 cells; **`B_off` differs only by wall-clock
  `took_ms` 0 → 1** in the ingest response — computed diff, all other keys equal; non-behavioral.
- **O1 (F4 within-sweep duplicate proposals)** still observable (5 relations on one endpoint pair);
  carried for a future registration, unchanged from the freeze.
- O2/O3 unchanged (activation-only contrast on the synthetic fixture; canary record included in
  `run.end.records`).

## 6. Consequences

No verdict, claim, gate, or threshold movement; the frozen bundle remains the freeze-time
reference. The Phase-4 construction floor is re-confirmed on the current tip.
