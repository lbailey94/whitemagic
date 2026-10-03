# RECEIPT — P2B scored results (GEN3-P2B-PROJECTION-001)

**Status: recorded · 2026-09-16 · implementation-frozen config** (`P2B_IMPLEMENTATION_FREEZE_2026-09-16.md`).
Full report: `experiments/semantic_projection/RESULTS_2026-09-16.md`. Artifacts:
`results/{C00,C01,C10,C11}/` (per-seed result JSONs + manifests + journals), `ANALYSIS_P2B.json`.

## Outcome

| | C00 | C01 | C10 | C11 | Verdict |
|---|---|---|---|---|---|
| T1+T6 top-5 (n=40) | 26 | 32 | 26 | **38** | M1 pass only in interaction |
| T1+T6 verified | 12/40 | 20/40 | 12/40 | **26/40** | — |
| M2 conditional ordering | 46.2 % | 62.5 % | 46.2 % | 68.4 % | supersedes **PASS** (+16.3 pp); preservation **PASS** |
| T8 | 0/15 | 0/15 | 0/15 | 0/15 | **FAIL** |
| M3 precision / recall | — | 1.59 % / 89.7 % | — | 2.20 % / **65.5 %** | precision PASS (2.07×), recall **FAIL** |
| M4 pair reduction | — | 0 % | — (no sweep) | **40.0 %** | **FAIL** (<50 %) |
| H4 / H6 | 100 % / 0 | 100 % / 0 | 100 % / 0 | 100 % / 0 | PASS |

**Pre-registered branch: projection rejected** (§7 triggers: M1 solo, M3 recall, M4) →
`claim-0001` resolved **falsified**.

## Key observations (not claims)

1. **C10 ≡ C00 exactly (all seeds, all metrics).** Semantic expansion without temporal
   re-ranking changes nothing measurable — the primitives are **dependent**, not orthogonal.
2. **C11 is materially better than C01** (verified 20→26, top-5 32→38, R@1 50→65 %,
   M2 62.5→68.4 %) — the composition effect is real but does not satisfy the registered claim.
3. **T8 remains 0/15**: τ = 0.694 (battery-safe) is too strict for the dietary↔vegetarian
   bridge with bge-small.
4. Cost: ingest +7 s (C01 103 → C11 110 s pooled); query p50 13.7 → 291 ms dominated by
   per-process model reload + embedding (the required externalized cost, and it is large).

## Rules

Nothing is re-run or re-tuned; any successor (narrower composition claim, different geometry,
or a different gate design) requires a new pre-registration with its own budget and ablation.
Phase 3 remains blocked. Budget: 5/5 cell sessions + 1 implementation session (flagged
separately in `BUDGET.md`).
