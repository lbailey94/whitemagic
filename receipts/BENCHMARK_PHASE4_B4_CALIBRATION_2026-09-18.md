# RECEIPT — Benchmark Phase 4: B4 Calibration & Adversarial Epistemics (2026-09-18)

**Status: VERIFIED & DEMONSTRATED — 2026-09-18.** Executed per `docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md` Phase 4 against baseline `G3-CRB-1`. AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` (Antigravity) executed and attests. Append-only; corrections create a new receipt referencing this one.

---

## 1. Benchmark Execution Parameters

| Parameter | Value |
|---|---|
| **Benchmark Suite** | `crates/wm-tools/tests/calibration_adversarial_stress.rs` |
| **Driver Script** | `benchmarks/driver_phase4_b4_calibration.py` |
| **Target Baseline** | `G3-CRB-1` (Commit `60b3439`, Core hash `a5ec583b…`) |
| **Epistemic Archetypes** | 5 adversarial archetypes (Hedging, Polarized, Regime Drift, Domain-Split, Selective) |
| **Empirical-Bayes Sweep** | $k \in \{0, 1, 5, 10, 20, 50, 100\}$ (statutory default: $k=20.0$) |
| **Wall-Clock Duration** | 0.41 seconds |
| **Outcome** | 6/6 suites PASS (0 failed, 0 invariant violations) |

---

## 2. Invariant Verification Index

| Test Case | Invariant Evaluated | Empirical Result |
|---|---|---|
| `test_empty_data_insufficient_data_semantics` | **Zero Data Baseline**: When ledger has 0 resolved claims, calibration report must return identity confidence, 0 shrinkage, and `calibrated`. | **PASS**: `resolved: 0`, `shrinkage: 0.0`, `prior_samples: 20.0`, `interpretation: calibrated`. |
| `test_constant_hedging_forecaster_and_k_sweep` | **Hedging Resilience & $k$-Sweep**: 100 claims with uninformative 0.51 confidence against 70% true hit rate. | **PASS**: Shrinkage weight $w$ drops monotonically as $k$ increases ($1.0000 \to 0.5000$). At statutory $k=20.0$, $w=0.8333$, pulling calibrated prediction to $0.6683$ without altering raw $0.51$ record. |
| `test_extreme_overconfident_forecaster` | **Overconfidence Penalty & Brier Quadratic Loss**: 100 claims with 0.99 confidence against 50% true hit rate. | **PASS**: Calibration gap $= +0.4900$ ("overconfident"), Brier $= 0.4901$ (severe penalty vs 0.2500 random baseline). Statutory $k=20$ shrinks calibrated confidence to $0.5817$. |
| `test_sudden_degradation_regime_change` | **Regime Drift Detection**: 100 well-calibrated claims (0.80 conf, 80% hit) followed by 100 collapsed claims (0.80 conf, 20% hit). | **PASS**: Gap widened from $0.0000$ to $+0.3000$ ("overconfident"). Brier degraded from $0.1600$ to $0.3400$. Wilson 95% interval contracted to $[0.4314, 0.5686]$, definitively rejecting the 0.80 prior. |
| `test_domain_specific_miscalibration_isolation` | **Domain Segregation Invariant**: High-reliability domain ("agent_architecture", 90% hit) vs miscalibrated domain ("market_macro", 20% hit). | **PASS**: Domain-filtered listings and status reports preserved exact independent counters (45/5 vs 10/40), preventing domain contamination. |
| `test_selective_prediction_refusal_superiority` | **Selective Abstention Superiority**: Agent abstains on 50 high-uncertainty propositions, predicting only on 50 high-signal claims. | **PASS**: Selective predictor achieved $0.1600$ Brier vs $0.2500$ for indiscriminate predictor ($0.0900$ lower squared error). |

---

## 3. Empirical-Bayes Shrinkage Table ($N=100$, True Rate $= 0.70$)

| Prior Weight ($k$) | Shrinkage Weight ($w = \frac{N}{N+k}$) | Raw Confidence ($p_{raw}$) | Calibrated Confidence ($p_{cal}$) | Regime Interpretation |
|---|---|---|---|---|
| **$k = 0$** | $1.0000$ | $0.5100$ | $0.7000$ | Maximum shrinkage (vulnerable to small-sample noise) |
| **$k = 1$** | $0.9901$ | $0.5100$ | $0.6981$ | Rapid empirical adaptation |
| **$k = 5$** | $0.9524$ | $0.5100$ | $0.6910$ | Moderate sample discounting |
| **$k = 10$** | $0.9091$ | $0.5100$ | $0.6827$ | Substantial prior resistance |
| **$k = 20$** | **$0.8333$** | **$0.5100$** | **$0.6683$** | **Statutory Gen3 Balance ($N=20 \Rightarrow w=0.50$)** |
| **$k = 50$** | $0.6667$ | $0.5100$ | $0.6367$ | Conservative shrinkage |
| **$k = 100$** | $0.5000$ | $0.5100$ | $0.6050$ | Heavy prior anchoring |

---

## 4. Constitutional Epistemic Laws Confirmed

1. **`belief ≠ evidence` (Part 1 Invariant 9)**:
   Claims remain predictive hypotheses recorded in the claims ledger; they never mutate into immutable sensory records or overwrite underlying historical data.
2. **Immutable Raw Confidences**:
   Recalibration via empirical-Bayes shrinkage ($w = \frac{n}{n+k}$) produces a distinct `calibrated_confidence` field. The agent's original stated confidence is never retroactively altered.
3. **Resolution Completeness**:
   Every claim resolution demands an immutable `ValidationEvent`, epoch date, and provenance source URI; claims cannot be resolved twice.

---

## 5. Attestation

AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` executed `benchmarks/driver_phase4_b4_calibration.py`, verified all 5 adversarial archetypes, evaluated the $k$-sweep, and recorded this receipt.
No verdict, claim, gate, or threshold movement; WEAK stays WEAK.
