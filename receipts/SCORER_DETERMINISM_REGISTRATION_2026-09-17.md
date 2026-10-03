# RECEIPT — Scorer determinism registration ratified (2026-09-17)

**Status: FROZEN — 2026-09-17 · execution scheduled next session.** Operator ratified in session;
the registration is in effect as the frozen contract for the order-fixed reductions unit. AI
session `6c634017-b18a-454f-9b06-67baa2355f32` (opencode) drafted and attests; it does not
ratify. Append-only; corrections create a new receipt referencing this one.

---

## 1. Frozen artifact

| Field | Value |
|---|---|
| Registration | `docs/specs/W1_SCORER_DETERMINISM_REGISTRATION.md` |
| SHA-256 | `cbf3f01440395c5d0affbd17af6b912f09e9f8e4107329ba3c9997a34e98e516` |
| Git blob hash | `2ebb2c8a3cc98aa111aa26f951ad8f4062be4705` |
| Arises from | **F-1** — `receipts/IMPL_B5_RECALL_VIEW_2026-09-17.md` §4; bundle `impl_b5_recall_view_2026-09-17/noise_baseline.results.txt` |

## 2. Operator act — RECORDED

| Field | Value |
|---|---|
| Operator | Lucas Bailey |
| Act | Ratification of the scorer-determinism registration; execution scheduled for the next session |
| Directive (verbatim) | **"Ratify, execute next session"** |
| Owner assigned | Lucas Bailey (operator) |
| AI attestation | Session `6c634017` measured F-1 (same-binary ≤1 ULP rerun noise; candidate-vs-reference max 2 ULP; ordering/metrics exact), located the three order-dependent sites (`ops.rs:733`, `:390`, `:1126`), and drafted the registration — attestation only |

## 3. What was ratified

- Declared orders for three order-dependent reductions: `total_idf` over the query token vector;
  dispersion entropy over sorted contexts; sweep pair enumeration over sorted token keys.
- Acceptance: same-binary reruns at **0 ULP** (today 1); identical sweep event streams across
  runs (today random); candidate vs pre-change `10b48d8` — ordering/metrics 0 diffs, scores
  ≤ 1 ULP (cross-build codegen band, disclosed); journal `rank_key` reproducibility; re-baseline
  statement (score bits may shift ≤1 ULP, ordering/metrics unchanged; protocol §9 equivalence).
- Non-goals: no formula/threshold/gate/vocabulary change; no env switch; no byte-reproducible
  build claim.
- Sequencing: this unit executes next session; the F-1 errata and the **B5 row exit** cite its
  evidence (B5 exit remains open until then).

## 4. Verification

Docs-only: no code, gates, thresholds, or verdicts changed. Registration hash recorded above
(post-ratification text, including the recorded act). Site citations line-checked against
`crates/wm-gen3-core/src/ops.rs` at tip `4a26875`.

## 5. Consequence

- Next session: implement → implementation freeze → acceptance (`IMPL_SCORER_DETERMINISM_<date>.md`)
  → F-1 errata → B5 exit receipt (operator act).
- No verdict, claim, gate, or threshold changes; WEAK stays WEAK; ledger unchanged.

## 6. Attestation

AI session `6c634017` drafted the registration from the measured F-1 evidence and records the
operator's authorizing act and scheduling directive. Ratification is an external operator act;
this receipt records it — it does not itself ratify.
