# Conformal Prediction — v5 Feature

**Added**: v5.2.2 (2026-08-08)
**Status**: Complete — new crate `wm-conformal` + 7 MCP tools, 20 tests, 0 clippy warnings.

## What it is

**Conformal prediction** is a distribution-free method for uncertainty
quantification. Unlike heuristic confidence scores (e.g. softmax
probability), it produces prediction *sets* (classification) or
*intervals* (regression) with a **finite-sample, distribution-free
coverage guarantee**:

```text
P(true outcome ∈ prediction set) ≥ 1 − α
```

This holds for *any* underlying model and *any* data distribution —
no calibration curves, no recalibration, no distributional assumptions.
This was a net-new capability in neither v26 nor v5; v5's older
"ConformalCalibrator" was actually isotonic-style confidence calibration
(a single threshold), not conformal prediction.

## How it works

1. **Calibration**: on a held-out calibration set, compute a
   *nonconformity score* per example — how much the model "disagrees"
   with the true outcome:
   - Classification: `1 − p(y_true)` (or APS cumulative mass)
   - Regression: `|ŷ − y|`
2. **Quantile**: the `⌈(n+1)(1−α)⌉`-th smallest score becomes the
   threshold `q`.
3. **Prediction**: include outcomes with score ≤ `q` (classification) or
   return `[ŷ − q, ŷ + q]` (regression).

Because calibration scores are exchangeable with test scores, the
coverage guarantee holds with no assumptions about the model.

## Components

### `wm-conformal` crate

| Type | Purpose |
|---|---|
| `SplitConformalClassifier` | Label prediction sets, nonconformity `1 − score` |
| `SplitConformalRegressor` | Value intervals, nonconformity absolute residual |
| `AdaptivePredictionSets` | APS variant (Romano et al. 2020) — smaller sets for calibrated models, with the required uniform tie-break term |
| `CoverageReport` | Empirical coverage evaluation on held-out data (drift monitoring) |

All types are `serde`-serializable for persistence across restarts.

### MCP tools (7)

| Tool | Purpose |
|---|---|
| `conformal.fit_classifier` | Add `(scores, label)` samples, (re)fit the classifier + APS |
| `conformal.fit_regressor` | Add `(predicted, actual)` samples, (re)fit the regressor |
| `conformal.predict_set` | Predict a label set; `mode: "aps"` for the adaptive variant |
| `conformal.predict_interval` | Predict `[lower, upper]` around a point value |
| `conformal.status` | Current calibration state, sample counts, alphas |
| `conformal.export` | Serialize the full store (samples + fitted models) to JSON |
| `conformal.import` | Restore the store from exported JSON |

## Usage

```bash
# Calibrate a classifier (90% coverage guarantee)
wm --store ~/.local/share/whitemagic \
   "conformal.fit_classifier" alpha=0.1 \
   samples='[{"scores":[0.9,0.05,0.05],"label":0},
              {"scores":[0.1,0.85,0.05],"label":1}, ...]'

# Predict a set with the guarantee
wm --store ~/.local/share/whitemagic \
   "conformal.predict_set" scores='[0.8,0.1,0.1]'
# → {"classes":[0],"coverage_guarantee":0.9,...}

# Regression interval (95% coverage)
wm --store ~/.local/share/whitemagic \
   "conformal.fit_regressor" samples='[{"predicted":1.1,"actual":1.0}, ...]' alpha=0.05
wm --store ~/.local/share/whitemagic \
   "conformal.predict_interval" value=5.0
# → {"point":5.0,"lower":4.2,"upper":5.8,"coverage_guarantee":0.95}
```

## Guarantee verification

The coverage guarantee is verified statistically in `crates/wm-conformal`:

- `marginal_coverage_holds_in_simulation` — classifier coverage ≈ 0.90
  averaged over 40 independent calibration draws (80K test points), with
  tight ±0.008 bounds.
- `regressor_interval_coverage_holds_in_simulation` — regressor coverage
  ≈ 0.95 with the same rigor.
- `aps_coverage_holds_in_simulation` — APS coverage ≥ 0.89 (the guarantee
  is a lower bound; APS may over-cover for poorly calibrated models).
- `CoverageReport` unit tests — empirical coverage evaluation.

## Design notes

- **Graceful degradation**: all `lock()` sites use `map_err` — a poisoned
  store degrades a call instead of panicking the server.
- **No unsafe**: `#![forbid(unsafe_code)]`.
- **Persistence**: `conformal.export`/`import` round-trip the full state;
  `ConformalStore` unit test verifies fitted models survive serialization.
- **APS tie-break**: the uniform term `U ~ U(0,1)` in the APS nonconformity
  score is essential for the coverage guarantee with discrete scores; it
  uses an internal SplitMix64 PRNG (deterministic per instance).
