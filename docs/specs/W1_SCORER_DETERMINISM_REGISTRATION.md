# Scorer determinism — registration (order-fixed reductions)

**Status: FROZEN — operator-ratified 2026-09-17** (freeze receipt
`receipts/SCORER_DETERMINISM_REGISTRATION_2026-09-17.md`) · compiled against WMgen3 tip
`4a26875`; source tree clean before creation of this registration document. **Execution scheduled
for the next session** (operator directive "Ratify, execute next session"): implement the declared
orders → implementation freeze → acceptance → F-1 errata → B5 exit receipt.
Arises from **F-1** (`receipts/IMPL_B5_RECALL_VIEW_2026-09-17.md` §4): the B5 0-diff regression
missed its registered `≤1 f32 ULP` score bound by one ULP (max 2), because same-binary reruns
already vary by 1 ULP. This unit removes the *cause* (order-dependent reductions) rather than
re-wording the symptom.

---

## 0. What exists today (measured; evidence)

F-1 attribution (measured, bundle `impl_b5_recall_view_2026-09-17/noise_baseline.results.txt`):
same-binary reruns differ by 1 ULP (ref 18 entries, cand 34 entries; ordering identical);
candidate-vs-reference reached 2 ULP in 16/650 score entries. Root sites (code read):

1. `crates/wm-gen3-core/src/ops.rs:733` — `let total_idf: f32 = idf_map.values().sum();`
   (`idf_map: HashMap`; per-process RandomState iteration order; f32 addition is not associative).
2. `crates/wm-gen3-core/src/ops.rs:390` — dispersion entropy
   (`entropy -= p * p.ln()` over `per_context.values()`, f64) — same class; dormant by default
   (`WM_GEN3_DISPERSION` off).
3. `crates/wm-gen3-core/src/ops.rs:1126` — sweep pair enumeration
   (`'outer: for ids in token_ids.values()`) — iteration order decides which pairs are examined
   under the statutory pair budget and the order of `relation.proposed` / `relation.state_change`
   events. Ranking ordering unaffected so far; **audit reproducibility (N3/N4) is the stake**.

All three are per-process random (std `HashMap`), not build-dependent: the same binary produces
different score bits / event orders across runs.

## 1. Scope (what changes, what must not)

**Change:** replace the three order-dependent iterations with **declared orders**:

| Site | Declared order |
|---|---|
| `total_idf` | sum over the query `tokens` vector, in token order (the order already used for `matched`) |
| dispersion entropy | iterate contexts in sorted-key order (or an equivalent declared order) |
| sweep pair enumeration | iterate token keys sorted (deterministic pair stream), ids in their stored order |

**Must not change:** scoring policy or formula (only summation/enumeration order), strata, floors,
gates, thresholds, relation kinds, pair budget value, defaults, journal *vocabulary* (event
order becomes deterministic, event content unchanged), harness contract. **No new env switch.**

## 2. Acceptance

1. **Same-binary determinism (the new bar).** Two fresh processes on the same store and query
   set produce **identical score bits (0 ULP)** on the gate-neutralized regression corpus
   (seeds 6–10, C00 and C01) — this is what fails today (1 ULP).
2. **Sweep determinism.** Two runs of `think_sweep` from the same store state produce identical
   event streams (`relation.proposed`, `relation.state_change` sequences — same order, same ids,
   same reason fields; timing fields excluded).
3. **Behavioral non-change.** Candidate vs the pre-change build (`10b48d8`, sha `0c4b1d87…`) on
   the same corpus: ordering/metrics 0 diffs (both configs); scores ≤ 1 ULP (codegen band
   remains across builds and is disclosed; builds are not byte-reproducible).
4. **Journal reproducibility.** `selection.decision.rank_key` bits identical across processes
   for identical queries; declared-order event sequences for equal-timestamp events.
5. **Re-baseline statement.** Recorded cells' score bits may shift by ≤1 ULP from either
   direction of the change; ordering/metrics unchanged — behavioral equivalence under protocol §9
   (not an artifact-instance claim).
6. Tests green (core + doc), closures PASS, release build clean.

## 3. Adversarial cases

1. **Near-tie stability** — fixture with two candidates whose keys differ by ≤1 ULP; ordering
   must be identical across processes (today it could flip with the summation-order draw).
2. **Sweep budget boundary** — a store whose candidate pairs exceed the pair budget: the examined
   set must be identical across runs (declared pair stream), with the cut disclosed by stats.
3. **Dispersion enabled** — the dormant `WM_GEN3_DISPERSION=1` path must also be deterministic
   (sorted contexts) without changing its (falsified, default-off) behavior beyond bits.
4. **Restart** — determinism holds across store reopen (no in-memory ordering inheritance).
5. **No hidden re-ordering** — the deterministic orders are first-class and ablatable: a test
   asserts the token-order sum equals the sorted-key sum only for commuting cases (documenting
   they are the *same value* under a declared order; this is the fix, not a new tolerance).

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Declared orders | same-binary 0 ULP; deterministic sweep streams | (pre-change build) 1 ULP rerun noise; random event order | EXECUTED → EFFECTFUL |

No env switch: the comparison is before/after the revision, on frozen corpora.

## 5. Fences

| Piece | Pin |
|---|---|
| Candidate | implementation-freeze build at this unit's tip (hash recorded; instance label) |
| Pre-change reference | `10b48d8` rebuild (sha `0c4b1d87…` build recorded in the B5 bundle) |
| Corpus | gate-neutralized holdout seeds 6–10 (`corpus_dedup.sha256`, transform `gate-neutralize.v1.2026-09-17`) + the B5 campaign fixture (view semantics re-run to keep one coherent B5 exit bundle) |
| Control | Gen2 v9.1.7 untouched; no A/B |
| WMv9 | read-only |
| Claims/verdicts | none moved; WEAK stays WEAK; F-1 exits via errata on this unit's evidence |

## 6. Non-goals

No scoring policy/formula change · no threshold or gate change · no env switch · no
artifact-instance (byte-reproducible build) claim — cross-build codegen variation remains and is
disclosed · no determinism claim for anything outside the named sites (a future order-dependent
reduction added anywhere is a new finding).

## 7. Freeze block

- [x] Owner assigned (operator): Lucas Bailey
- [x] Registration ratified (operator signature below) — freeze receipt
      `receipts/SCORER_DETERMINISM_REGISTRATION_2026-09-17.md`
- [ ] Implementation freeze (source hash at the tip that declares the orders) — next session
- [ ] Acceptance demonstrated — receipt `IMPL_SCORER_DETERMINISM_<date>.md`; then the F-1 errata
      and the B5 exit receipt cite it.

Operator signature: Lucas Bailey — recorded per in-session directive 2026-09-17
("Ratify, execute next session"; see the freeze receipt). Date: 2026-09-17

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this registration alone.
