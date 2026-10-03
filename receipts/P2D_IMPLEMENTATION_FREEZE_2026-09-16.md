# RECEIPT — P2D implementation freeze (GEN3-P2D-ARBITRATION-001)

**Status: IMPLEMENTATION FROZEN · 2026-09-16.** No B0/B1/B2 run may start before this receipt.
Any code change after it re-baselines the experiment.

---

## 1. Frozen implementation

| Field | Value |
|---|---|
| Implementation commit | `2b8bcae` (arbitration selector, default off) |
| Candidate binary | `target/release/wm-gen3`, sha256 `f07c85ebfcca20e3ec93b44d6f0935b77c0b3145ed18eaebe9ff09f65617e200` |
| Arbitration semantics | strata 0/1/2 by live supersedes state; within-stratum lexical → semantic → recency → id; no blending, no tunables; `include_historical` collapses strata |
| New switch | `WM_GEN3_ARBITRATION=structural` (default: PenaltyMultiplier, unchanged) |
| Tests | 23 unit (incl. strata test) + 5 compile-fail docs green |
| Closure scans | PASS |

## 2. Regression proof on frozen paths (required by pre-reg §5 sanity)

New binary, same commands, discovery seed 1:
- **B0** (defaults) vs recorded P2C reproduction C01: **0 per-query diffs** (verified, R@1, R@5, MRR, first-match).
- **B1** (`WM_GEN3_PROJECTION=1`) vs recorded C11: **0 per-query diffs**.
⇒ the frozen selector and naive path are behavior-identical; only the new switch changes behavior.

## 3. Run plan (after this receipt)

1. Smoke (non-evidence): B2 on seed 11 — plumbing + strata visible in journals.
2. B0/B1/B2 × seeds 11–15, one batch, frozen invocation:
   - B0: defaults · B1: `WM_GEN3_PROJECTION=1` · B2: `WM_GEN3_PROJECTION=1 WM_GEN3_ARBITRATION=structural`
   - `--data holdout_p2d`, categories `T8 T1 T6 T2`, pinned flags.
3. Analysis: ΔReach = Top5_B2 − Top5_B0 (≥ +4 required); ΔOrdering = M2_B2 − M2_B0 (≥ −5 pp
   required); downstream verified/R@1; per-seed; T8 probe; costs.

## 4. Rules

Geometry and R unchanged; R1 paused; naive B1 preserved in-batch; nothing else changed. Any
modification re-baselines.
