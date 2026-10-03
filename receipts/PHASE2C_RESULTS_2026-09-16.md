# RECEIPT — P2C scored results (GEN3-P2C-INTERACTION-001)

**Status: recorded · 2026-09-16 · frozen plan + frozen holdout** (`P2C_FREEZE_2026-09-16.md`).
Full report: `experiments/semantic_projection/RESULTS_P2C_2026-09-16.md`. Artifacts:
`results_p2c/` (holdout + reproduction cells, journals), `ANALYSIS_P2C.json`.

## Outcome (holdout seeds 6–10)

| | C00 | C01 | C10 | C11 |
|---|---|---|---|---|
| verified | 20/40 | **28/40** | 20/40 | 24/40 |
| top-5 | 30/40 | 32/40 | 30/40 | **40/40** |
| M2 ordering | 66.7 % | **87.5 %** | 66.7 % | 60.0 % |

`I_top5 = +8` (bar met) · `I_verified = −4` (**falsification trigger**) · `I_M2 = −27.5 pp`
(secondary failed) → **claim-0002 falsified** in the wmv9 ledger.

## Key observations

1. **Replicated:** S-alone null (C10 ≡ C00, per-seed exact, both datasets — third replication);
   reach interaction (top-5 +6 discovery → +8 holdout).
2. **Did not replicate:** verified gain (discovery +6 → holdout −4) and ordering interaction
   (discovery +5.9 pp → holdout −27.5 pp). C11 maximizes coverage but *degrades rank-1
   precision* relative to supersession alone on unseen data.
3. **Leading candidate primitive:** projection arbitration (no principled fusion; the naive
   max-union mis-ranks once semantic candidates enter a demoted landscape). Geometry delivered
   reach; fusion is the remaining failure.
4. T8 probe 0/15 everywhere (decoupled, stands).
5. Costs reported per pre-reg: cold p50 14 → ~300 ms (S-on), model load ~16 s pooled, warm
   embedding ~0.1 texts/ms — real semantic-compute cost, not only lifecycle artifact.
6. Reproduction (seeds 1–5) reproduced P2B exactly — implementation stability confirmed.
7. H4 = 100 %, H6 = 0 in every cell.

## Rules

Nothing is re-run or re-tuned. Any successor (projection-arbitration registration, R1 gating)
requires a new pre-registration with a **fresh** holdout (6–10 are now scored) and its own
budget. Phase 3 remains blocked. Budget: 3 P2C sessions logged (within cap).
