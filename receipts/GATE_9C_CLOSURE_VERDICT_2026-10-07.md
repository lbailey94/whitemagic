# Gate 9C Closure Verdict — Cognitive Re-Derivation & Candidacy Precision

- **Draft Date:** 2026-10-07 (engineering closure recorded by opencode; operator ratification pending)
- **Target Architecture:** WhiteMagic Gen3 substrate (`crates/wm-gen3-core`: `ops`, `recipe`, `sweep`, `projection`)
- **Base Commit:** `2a923b4c60f97570551d4bcbb02c290ad474f77b` (10.2.0-alpha.5, `main`)
- **Operator / Authority:** Lucas (ratification pending)
- **Preregistration:** `docs/PREREGISTRATION_PEB15_AMENDMENT_GATE9C.md` (H9C-1…H9C-4, frozen metric table)
- **Status:** **ENGINEERING CLOSURE — CLOSED WITH METRIC CAVEATS, PENDING OPERATOR RATIFICATION**

---

## 1. Statutory Closure Verdict

Pursuant to `docs/CHARTER.md` (Article 4, §3.10) and the Gate 9C amendment:

$$\boxed{ \textbf{GATE 9C (Cognitive Re-Derivation) IS ENGINEERING-CLOSED — RATIFICATION PENDING} }$$

The Gate 9C acceptance battery passes in CI and under local re-execution: the
28 Gana archetypes are stateless recipes, lexical anchor coherence eliminates
the cross-topic false-candidate class, conformal Forgotten Diamonds preserve
dormant-salience recovery without background loops, and projection-enabled
intake/sweep persist vectors and propose relations. The amendment's numeric
precision/recall thresholds are asserted constructively by `h9c1`, not
re-measured end-to-end; that caveat is recorded below.

## 2. Evidence

*Evidence class:* CI-fetched plus locally re-executed on the base commit
(cargo 1.98.0 / rustc 1.98.0, 2026-10-07T03:2xZ).

| Verification | Command / scope | Result |
|---|---|---|
| **Local re-execution (9C battery)** | `cargo test --locked -p wm-gen3-core --features operator,reference-models --test gate9c_precision_acceptance` | **4 passed, 0 failed** — `h9c1_anchor_coherence_eliminates_spurious_cross_topic_collisions`, `h9c2_gana_recipes_adhere_to_charter_and_article_4`, `h9c3_conformal_forgotten_diamonds_scoring_and_recovery`, `h9c4_requalified_projection_intake_and_sweep` (fastembed cache present, 0.05 s) |
| **CI (alpha.4)** | [run 37537977637](https://github.com/lbailey94/whitemagic/actions/runs/37537977637), `cargo test --workspace` | gate9c **4/4 passed on both Linux and macOS** (`operator` unified via the harness dependency) |
| **CI (alpha.5)** | [run 37562979314](https://github.com/lbailey94/whitemagic/actions/runs/37562979314) | Tests (Linux) killed (exit 143) before reaching the gate9c target; no failure recorded |
| **Static closures** | `bash scripts/check_closures.sh` (alpha.5 CI) | 3/3 PASS (Article 4 spawn boundary, mutation-surface isolation, dependency rule) |
| **Release integrity** | [run 37562982195](https://github.com/lbailey94/whitemagic/actions/runs/37562982195) | 10/10 jobs green (artifact/registry integrity for the same commit) |

## 3. Hypothesis Results

- **H9C-1 (precision / anchor coherence): EVIDENCED CONSTRUCTIVELY.** In the
  acceptance corpus the sweep proposes exactly the three true temporal-update
  pairs, proposes zero cross-topic false pairs, and every relation direction is
  temporally valid (`src > dst`). **Caveat:** the frozen thresholds
  (Precision ≥ 2.12 %, Recall ≥ 85 %, ≥ 50 % candidate-pair reduction) are not
  directly re-instrumented by this battery; the supporting metric study lives in
  `experiments/semantic_projection/` (Anomaly Study, Failure Taxonomy) and is
  not re-run as part of CI.
- **H9C-2 (Ganas as recipes): EVIDENCED.** Exactly 28 unique presets, four
  families × 7, parameter bounds enforced, pure plain-old-data with no runtime
  state or background authority (Article 4 / §3.10).
- **H9C-3 (Forgotten Diamonds): EVIDENCED.** Half-life decay matches
  `0.5^(Δt/τ)` at 1 and 10 half-lives; frequent access disqualifies; no daemon
  required.
- **H9C-4 (projection requalification): EVIDENCED.** Projection-enabled intake
  persists vectors to the `embeddings` DBI and projection-enabled sweep
  proposes the supersession relation.

## 4. Open Items & Caveats

1. **Frozen metric thresholds are not directly asserted** by the acceptance
   test (constructive 10-item corpus instead of a re-measured precision/recall
   run). If ratification requires the exact numbers, the projection study must
   be re-executed as a preregistered measurement.
2. **`h9c4` silently returns when the fastembed cache is absent** — in CI the
   model cache is warmed explicitly, so the test ran there; runs without a
   cache will report 4 passed while exercising only 3 hypotheses.
3. **CI activation incomplete:** no green main-branch run has yet executed the
   full workspace including this battery after the alpha.5 CI termination
   (run 37562979314, exit 143 before the battery step).
4. `docs/STORE_AND_DATA_HYGIENE.md` still carries a historical note about
   test-only cache defaults pointing at the WMv9 tree; that path is
   test/dead-code only and unrelated to runtime behavior.

## 5. Transition

Gate 9B and Gate 9D verdicts are issued contemporaneously. Operator
ratification is the remaining statutory step; open items above are carried as
ratification conditions.
