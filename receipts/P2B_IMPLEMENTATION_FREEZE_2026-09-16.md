# RECEIPT — P2B implementation freeze (GEN3-P2B-PROJECTION-001)

**Status: IMPLEMENTATION FROZEN · 2026-09-16.** No scored cell may run before this receipt.
Any code change after this point re-baselines the experiment (new receipt).

---

## 1. Frozen implementation

| Field | Value |
|---|---|
| Implementation commit | `4d45b20` (`p2b(implement): semantic projection primitive (default off) + C01 reproduction`) |
| Candidate binary | `target/release/wm-gen3`, sha256 `93c667ec5e817857881c7241579fc902719dee41b5bad51fca839e917197c705` |
| Tests | 22 unit + 5 compile-fail doctests green (incl. genericity battery) |
| Closure scans | PASS (dependency rule; mutation-surface rule incl. `projection.rs`) |
| Run-time network | none — model loads from the local cache dir (`WM_GEN3_EMBED_CACHE=…/.fastembed_cache`, read-only); ONNX Runtime was fetched once at build time by `ort-sys` |

## 2. Threshold pin (τ)

| Field | Value |
|---|---|
| Rule (pre-committed) | maximum-margin separator at the midpoint of the frozen battery |
| Measurement | min positive `0.6998`; max hard negative `0.6882`; **τ = 0.694** (pinned in `projection.rs`) |
| Separation (frozen requirement) | **holds** — every positive ≥ τ, every hard negative ≤ τ |
| **Advisory (recorded)** | margin `0.0116 < 0.05` — the implementer's sensitivity warning, **not** a frozen kill criterion; the frozen plan requires separation only. Flagged for the operator. |

Battery raw cosines (frozen list): automobile↔car .9045 · physician↔doctor .8864 ·
relocated↔moved .9341 · canine↔dog .9549 · software-release↔version .7292 ·
storm/airport↔grounded-weather .6998 · radiator↔plumber-heating .7575 · river-bank↔bank-account .6146 ·
Apple-phone↔apple-fruit .5304 · band-set↔set-of-tools .6531 · bat-field↔bat-dusk .6882.

## 3. Reproduction safeguard (required before any projection interpretation)

C01 (projection off, frozen config) rerun on all 5 seeds:
**140/140 questions identical to the Phase-2 results** on verified, R@1, R@5, MRR, and first-match
rank (`experiments/semantic_projection/results/C01_reproduction/`). The unchanged baseline did
not move.

## 4. Cell invocation (identical harness command; switch-only differences)

| Cell | env |
|---|---|
| C00 | `WM_GEN3_SWEEP=0` |
| C01 | (defaults; reproduction already recorded, rerun in the batch per pre-reg) |
| C10 | `WM_GEN3_SWEEP=0 WM_GEN3_PROJECTION=1` |
| C11 | `WM_GEN3_PROJECTION=1` |

All cells: `WM_GEN3_EMBED_CACHE=/home/lucas/Desktop/WHITEMAGIC/WMv9/.fastembed_cache` (harmless
when projection off), seeds 1–5, categories `T8 T1 T6 T2`, pinned flags per the plan freeze.

## 5. Budget note

The implementation session (1) is recorded outside the plan's 5-session cell budget in
`BUDGET.md` and flagged for the operator's accounting preference.

## 6. Rules

No benchmark-derived parameters; no ANN; no corpus-specific vocabulary; frozen cells remain
behavior-identical; all cells run in one batch after this receipt and the plumbing smoke.
