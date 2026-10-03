# RECEIPT — B5 recall-side scope view registration ratified (2026-09-17)

**Status: FROZEN — 2026-09-17.** Operator ratified in session; the registration is in effect as
the frozen contract for the recall-side scope view unit. AI session
`6c634017-b18a-454f-9b06-67baa2355f32` (opencode) prepared, applied the operator's review
adjustments, verified pins, and attests; it does not ratify. Append-only; corrections create a
new receipt referencing this one.

---

## 1. Frozen artifacts

| Field | Value |
|---|---|
| Registration | `docs/specs/W1_B5_RECALL_VIEW_REGISTRATION.md` |
| SHA-256 | `99b25e8a1350220a7ba66e21c38f9638c79fe9bbe9b5025c4232a4b5f3ce6c3b` |
| Git blob hash | `20c4d1103d5b741e6390ffa6046179f3c2a1ce44` |
| Parent spec | `docs/specs/W1_B5_galaxies_compartments.md` (frozen; batch-B receipt) |
| Companion | `docs/specs/W2_02_04_ACCEPTANCE_PREP.md` (acceptance prep; not part of this freeze) |

## 2. Operator act — RECORDED

| Field | Value |
|---|---|
| Operator | Lucas Bailey |
| Act | Ratification of the B5 recall-side scope view registration + execution authorization for the W2_02/W2_04 acceptance slices + commit |
| Directive (verbatim) | **"All three: ratify, authorize, commit"** |
| Owner assigned | Lucas Bailey (operator) — B5 recall-side scope view row |
| AI attestation | Session `6c634017` applied the operator's review adjustments (cross-scope crowd-out acceptance case; frozen label grammar; pinned disclosure cause `no_candidates_in_scope`; wording fixes) and verified every citation — attestation only |

## 3. What was ratified

- Scope is a **view over provenance** (not a store, registry, class hierarchy, access-control
  system, or ranking modifier): an optional, caller-supplied `scope` selector; population filter
  applied **before** scoring/selection; explicit-only (no implicit/default scoping); no
  fabrication (empty view disclosed); no resources; no security claim.
- **Declared derivation rule and label grammar:** `corpus:<label>:<tags>`; labels are opaque,
  exact, case-sensitive, nonempty, colon-free byte strings; no trimming, case folding, Unicode
  normalization, aliases, or inference; invalid selectors are typed caller errors (fail-closed,
  no journal); malformed record provenance is label-less.
- **Acceptance:** fresh 0-diff regression (gate-neutralized recipe; ordering/metrics exact,
  scores ≤ 1 f32 ULP; journal sets identical), view correctness, filter-not-scorer,
  **cross-scope crowd-out** (filter-before-selection demonstrated), empty-view pinned
  disclosure, malformed-selector refusal, explicit-only, bare bytes.
- **Ablation:** the selector argument itself (no env switch).
- **Non-goals:** no isolation/authorization semantics; class/tier/capability items declared N/A;
  no harness contract change beyond the additive optional arg.

## 4. Verification

Docs-only: no code, gates, thresholds, or verdicts changed. The receipt pins the post-review
text (adjustments applied **before** the pin, including the recorded ratification block).
Citations line-checked against: `IMPL_B5_ACCEPTANCE_2026-09-17`, `crates/wm-gen3-core/src/ops.rs`
(`RecallQuery`, hit `source`/chain, A2 reason/cause vocabulary), and
`crates/wm-gen3-harness/src/main.rs` (source mapping `corpus:{galaxy}:{tags}`; existing `scope`
arg precedent on `inspect`).

## 5. Consequence

- Implementation proceeds under the registration: implementation freeze (source hash at the tip
  that adds the selector) → fresh 0-diff regression → acceptance demonstration → receipt
  `IMPL_B5_RECALL_VIEW_<date>.md`.
- W2_02/W2_04 acceptance slices are authorized for execution
  (`docs/specs/W2_02_04_ACCEPTANCE_PREP.md`; operator checklist recorded 2026-09-17).
- Standing-authorization scope clarified (`receipts/W2_SPEC_BATCH_FREEZE_CLARIFICATION_2026-09-17.md`;
  errata `#36`).
- No verdict, claim, gate, or threshold changes; WEAK stays WEAK.

## 6. Attestation

AI session `6c634017` prepared the registration, applied the operator's four review adjustments
(plus read-back consistency fixes), and records the operator's authorizing act. Ratification is
an external operator act; this receipt records it — it does not itself ratify.
