# RECEIPT — P2E scored results (GEN3-P2E-DISPERSION-001)

**Status: recorded · 2026-09-16 · frozen plan/holdout/implementation.** Full report:
`experiments/semantic_projection/RESULTS_P2E_2026-09-16.md`.

## Outcome (holdout seeds 16–20, pooled T1+T6)

| | D0 | D1 |
|---|---|---|
| Raw verified / top-5 / M2 | 34/40 · 40/40 · 85.0 % | 34/40 · 40/40 · 85.0 % |
| Adjudicated verified / M2 (38 q) | **34/38 · 89.5 %** | **32/38 · 84.2 %** |
| Cause-A negative margins | 6/6 | **2/6** |
| Median margin | −0.01297 | −0.00425 (gain +0.0087) |

| Bar | Pin | Result | Verdict |
|---|---|---|---|
| P1 ΔM2 | ≥ +8 pp | 0.0 pp (not ceiling) | FAIL |
| P2a negative-margin | ≤ 50 % of A0 | 6 → 2 | PASS |
| P2b median margin gain | ≥ +0.05 | +0.0087 | FAIL |
| top-5 preservation / H4 / H6 | — | 40 = 40 · 100 % · 0 | PASS |

**Falsified** (ΔM2 ≤ 0; P2b missed) → `claim-0004` resolved **falsified** in the wmv9 ledger.

## Findings

- Dispersion **unblocks 4/6 template-blocked questions at the margin** (the designed mechanism
  works directionally) but the effect is a **net redistribution**: seed 16 `music` (legitimate)
  regresses; seed 18 `music` "improves" only because it is an **audit-flagged label conflict**.
  Raw aggregates unchanged; adjudicated result worse by 2 questions.
- The audit protocol demonstrated its value: without it, the seed-18 regression would have been
  scored as a gain.
- Remaining blockers are of a different kind than cause A; the diagnosis (global rarity vs
  contextual specificity) survives, this remedy is rejected.
- T8 0/15 (probe); H4 100 %; H6 zero.

## Rules

Nothing re-run or re-tuned. Next successors require a fresh registration and a fresh holdout
(all of 1–5 / 6–10 / 11–15 / 16–20 are scored). Budget: 2 cell sessions + analysis; implementation
flagged separately. claim-0003 remains WEAK/unresolved; claim-0000/0001/0002/0004 falsified.
