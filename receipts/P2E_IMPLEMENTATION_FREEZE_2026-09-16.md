# RECEIPT — P2E implementation freeze (GEN3-P2E-DISPERSION-001)

**Status: IMPLEMENTATION FROZEN · 2026-09-16.** No D0/D1 run may start before this receipt.

---

## 1. Frozen implementation

| Field | Value |
|---|---|
| Implementation commit | this commit (dispersion weighting, default off) |
| Candidate binary | `target/release/wm-gen3`, sha256 `b51112e9ec63a0ec45aec27a336c824c242eaf3775cfb4004fd751cf62fc7eb6` |
| Estimator | exactly pre-reg §4: `C(t) = 1 − H(contexts|t)/log m_t`; contexts = provenance sessions from record sources; `m ≤ 1` or `df = 0` → 1; no epsilon; weighted support `idf·C`; `total = 0` → support 0 |
| New switch | `WM_GEN3_DISPERSION=1` (default off; D0 unchanged) |
| Tests | 25 unit (incl. weighted D2 properties + estimator-effect test) + 5 doctests + 1 ignored (A3 diagnostic); closure scans PASS |

## 2. Regression proof

- **D0** (projection + arbitration, dispersion off) on frozen seed 11: **0 per-query diffs**
  vs the recorded P2D B2 result — the frozen paths are behavior-identical.
- **D1 smoke** (seed 16, all three switches): plumbing green; `"dispersion":true` in all
  selection/run.end events; `"arbitration":"Structural"`; no errors.

## 3. Run plan

D0/D1 × seeds 16–20 (holdout_p2e), one batch, pinned invocation; categories `T8 T1 T6 T2`.
Analysis per pre-reg §5: P1 (ΔM2 ≥ +8 pp or ceiling fallback), P2 (negative-margin ≤ 50 % of the
cause-A set; median margin gain ≥ +0.05), top-5 preservation, H4/H6, downstream verified/R@1,
**raw and audit-adjudicated** scorings with the frozen v1.2 flag list. T9 untouched.

## 4. Rules

R, geometry, arbitration, R1 all unchanged; only the declared switch is new. Any modification
re-baselines.
