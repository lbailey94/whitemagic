# RECEIPT — P2D scored results (GEN3-P2D-ARBITRATION-001)

**Status: recorded · 2026-09-16 · frozen plan/holdout/implementation.** Full report:
`experiments/semantic_projection/RESULTS_P2D_2026-09-16.md`.

## Outcome (holdout seeds 11–15)

| | B0 (R) | B1 (S+R naive) | B2 (S+R arbitration) |
|---|---|---|---|
| verified | 26/40 | 32/40 | **34/40** |
| top-5 | 38/40 | 40/40 | 40/40 |
| M2 ordering | 68.4 % | 80.0 % | **85.0 %** |
| R@1 | 65.0 % | 80.0 % | 85.0 % |

| Bar | Pin | Result | Verdict |
|---|---|---|---|
| ΔReach (B2−B0) | ≥ +4 | **+2** | FAIL (headroom: B0 = 38/40 ⇒ max +2) |
| ΔOrdering (B2−B0) | ≥ −5 pp | **+16.6 pp** | PASS |

**Outcome: WEAK** → recorded, not escalated. `claim-0003` remains **pending** (no ledger
resolution). Calibration lesson recorded: reach bars need **headroom-aware** calibration.

## Descriptive findings

- B2 retains B1's reach exactly (both ceiling) and beats B1's ordering by **+5.0 pp**; beats
  R-only ordering by **+16.6 pp** — the strongest cell on every downstream measure to date.
- Naive fusion's ordering degradation (observed on seeds 6–10) is **corpus-sensitive**: on 11–15
  B1 already exceeded B0 (80 % vs 68.4 %).
- Seed-14 anomaly: 8/8 top-5, 2/8 verified (perfect reach, rank-1 failure) — same family as the
  earlier seed-2 anomaly.
- T8 0/15 (external probe, unchanged). H4 = 100 %, H6 = 0 all cells.

## Rules

Nothing re-run or re-tuned; next steps require a new registration (options in the report §5).
Budget: 3 cell sessions + analysis; implementation session flagged separately.
