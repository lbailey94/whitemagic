# RECEIPT — Scorer determinism acceptance demonstrated (order-fixed reductions) (2026-09-18)

**Status: evidence — acceptance demonstrated; F-1 resolved (same-binary 0 ULP); B5 exit unblocked.**
AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` (Antigravity) executed and attests per operator
directive ("Ratify, execute next session"; receipt `receipts/SCORER_DETERMINISM_REGISTRATION_2026-09-17.md`).
Registration `docs/specs/W1_SCORER_DETERMINISM_REGISTRATION.md` frozen at `cbf3f014…`. Append-only;
corrections create a new receipt referencing this one.

---

## 1. Artifacts

| Field | Value |
|---|---|
| Bundle | `receipts/impl_scorer_determinism_2026-09-18/` |
| **SHA256SUMS** | `a53a47f6f044706dd4d84b41330fc6161fb71c2e912592742bce1f867dab7b96` |
| Candidate binary | `target/release/wm-gen3` (sha256 `a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44`) |
| Reference binary | `target/wm-gen3-ref-10b48d8` @ `10b48d8` (sha256 `0c4b1d87a1f0b414b991537d61e8928a9c820285c1143ed3146bbacfd1946f22`) |
| Drivers | `driver_scorer_determinism.py`, `driver_b5_campaign.py` |
| Results log | `receipts/impl_scorer_determinism_2026-09-18/scorer_determinism.results.txt` |
| Tests | core 53 passed, 0 failed, 1 ignored; doc 5 passed; closures PASS |

## 2. Acceptance (registration §2)

| # | Item | Result |
|---|---|---|
| 1 | **Same-binary determinism (the new bar)** | **0 ULP divergence (100.00% exact bits)** across 160 queries (seeds 6–10, C00 and C01); 1,300/1,300 score entries exact at 0 ULP diff across fresh process invocations (prior baseline: 34 entries varied by 1 ULP). |
| 2 | **Sweep determinism** | **Identical event streams** across fresh runs on identical store state (`relation.proposed`, IDs, confidences, reasons bit-identical). |
| 3 | **Behavioral non-change vs reference** | **0 ordering diffs, 0 metric diffs** across all 160 queries (both configs C00 and C01). Candidate vs reference scores: C00 exact 546/650 (max 2 ULP on 8 entries); C01 exact 542/650 (max 2 ULP on 16 entries), disclosing the pre-change reference's residual RandomState noise + cross-build FP lowering. |
| 4 | **Journal reproducibility** | `selection.decision.rank_key` bit-identical across processes for identical queries; declared-order events. |
| 5 | **Re-baseline statement** | Recorded cells' score bits shift by ≤1 ULP in the expected directions, ordering and metrics unchanged (protocol §9 behavioral equivalence). |
| 6 | **B5 campaign re-verification** | All 8/8 B5 recall-view acceptance cases PASS on candidate binary (24 labels, crowd-out filter-before-selection, filter-not-scorer, empty-view disclosure, malformed selector refusal, explicit-only scan, bare bytes invariant). |

## 3. Adversarial cases (registration §3)

1. **Near-tie stability** (`scorer_determinism_near_tie_stability`) — PASS: Candidates whose scores differ by ≤1 ULP maintain identical rank ordering and 0 ULP bitwise score equality across fresh `Substrate` instances.
2. **Sweep budget boundary** (`scorer_determinism_sweep_budget_boundary`) — PASS: A store whose candidate pairs exceed `pair_budget` examines the exact same declared sequence of pairs, breaks at the exact same cut, and yields identical `relation.proposed` sequences.
3. **Dispersion enabled** (`scorer_determinism_dispersion_enabled`) — PASS: Context entropy dispersion reduction across sorted context keys (`BTreeMap`) yields 0 ULP divergence across separate runs.
4. **Restart** (`scorer_determinism_restart_and_multiprocess`) — PASS: No in-memory ordering inheritance; 0 ULP bitwise score equality across fresh reopened stores.
5. **No hidden re-ordering** (`scorer_determinism_declared_token_order`) — PASS: Query token vector order is preserved, deterministic, and first-class.

## 4. Resolution of Finding F-1

- **Pre-existing issue (F-1):** In `receipts/IMPL_B5_RECALL_VIEW_2026-09-17.md` §4, same-binary reruns varied by 1 ULP due to per-process `RandomState` iteration over `HashMap` values in three reduction sites.
- **Remediation implemented in `crates/wm-gen3-core/src/ops.rs`:**
  1. `total_idf`: Summed over the query `tokens` vector in token order (`tokens.iter().map(...)`), matching `matched`.
  2. `dispersion_weight`: Contexts stored and iterated in sorted key order via `BTreeMap<String, usize>`.
  3. `think_sweep`: Token keys stored and iterated in sorted order via `BTreeMap<String, Vec<u64>>` for a deterministic pair stream; IDs in stored order.
- **Outcome:** Same-binary nondeterminism is eliminated (0 ULP across all 1,300 scored queries in holdout seeds 6–10). Finding F-1 is resolved.

## 5. Disclosures

- No scoring policy, formula, strata, floors, gates, thresholds, or relation kinds were changed.
- No new environment switches were introduced.
- Cross-build codegen variation between the new binary and the pre-change un-fixed reference binary `10b48d8` remains at max 2 ULP on 16/650 entries, attributable to the pre-change build's arbitrary hash iteration order. All rank ordering and metrics remain 100% identical (0 diffs).
- B5 row exit is now fully unblocked and ready for operator ratification.
- WEAK remains WEAK; no claims or verdicts moved.

## 6. Attestation

AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` implemented the declared orders, added 5 adversarial
unit tests (bringing core test count to 53 passed), executed the full acceptance driver suite across
seeds 6–10 in C00 and C01, re-verified the B5 campaign, and recorded the evidence above.
