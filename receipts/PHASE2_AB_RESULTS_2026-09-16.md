# RECEIPT — Phase-2 A/B scored results (GEN3-P2-CONTRADICTION-001)

**Status: recorded · 2026-09-16 · frozen configuration** (`PREREG_FREEZE_2026-09-16.md`).
Full report: `experiments/contradiction/RESULTS_2026-09-16.md`. Artifacts:
`experiments/contradiction/results/` (control + gen3 per-seed result JSONs, run manifests,
journals + journal sha256 files, `ANALYSIS.json`, `analyze_results.py`).

## Outcome

| | Control | Gen3 | Verdict |
|---|---|---|---|
| H1 T8 (15 pooled) | 15/15 | 0/15 | **LOSS** (shortfall 15) |
| H2 T1+T6 (40 pooled) | 40/40 | 20/40 | **LOSS** (shortfall 20) |
| H4 provenance | — | 100% (3,221/3,221) | PASS |
| H5 laundering | — | no laundering path observed; dynamic hook unavailable in this run | not exercised (never abbreviate to "H5 PASS") |
| H6 violations | — | 0 | PASS |
| H7 cost | 7.4 s ingest / 59.4 ms p50 | 118.8 s ingest / 22.4 ms p50 | reported |

Pre-registration branch: **LOSS** (§8) → Phase 3 blocked until the finding is absorbed; thesis
paused, not extended. Kill triggers not met (missing primitive identified; H4/H5/H6 clean;
within budget).

## Named findings

- **F1 (primary):** missing general semantic bridge — T8 is a vocabulary-bridging test; control
  advantage is accumulated benchmark-relevant enrichment, not a contradiction primitive. The
  same gap depresses T1/T6 R@1 (80% R@5 vs 50% R@1: neighborhood found, ordering is the gap).
- **F2:** candidacy precision 1.06% at 89.7% recall (direction-correct, 0 reversed); needs a
  general pair-population reduction, not a dedicated engine.
- **F3 (process):** A6 lifecycle unevaluable in a write-then-read flow (0 promotions).

## Ledger

`claim-0000` resolved **falsified** in the wmv9 claims ledger (validated=false; event
2026-09-16; points 0).

## Rules reaffirmed

Any addition (bridging, precision mechanism, lifecycle scheduling) requires a new
pre-registration with its own ablation; the frozen configuration is not retro-fitted.
