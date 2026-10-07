# Row-exit packet — B5 · W2_01 · W2_02 · W2_03 · W2_04 · W2_07 (for operator review)

**Prepared 2026-09-18 (session `221fbb57`) · status: RATIFIED 2026-09-18 — B5 / W2_01 / W2_02 / W2_03 / W2_04 / W2_07 exited (see receipts `W1_ROW_EXIT_B5_2026-09-18.md` and `W2_ROW_EXIT_*_2026-09-18.md`).**
Wave plan §2 and §3 exit criteria: frozen spec + adversarial cases wired + ablation designed/demonstrated + journal events declared + receipt; **no inert acceptance test**. This packet changes no verdict, claim, or gate.

---

## B5 — Galaxies, compartments & recall views

- **Specs:** `docs/specs/W1_B5_galaxies_compartments.md` (`80a99e62…`), `docs/specs/W1_B5_RECALL_VIEW_REGISTRATION.md` (`99b25e8a…`), `docs/specs/W1_SCORER_DETERMINISM_REGISTRATION.md` (`cbf3f014…`).
- **Implementations:** compile/link side `c174ee0`; recall-side view `10b48d8`; scorer determinism unit (`ops.rs`).
- **Acceptance §5:**
  1. Compile/link side: 30 labels (> Gen2 dynamic cap 20); store file set invariant `{data.mdb, lock.mdb}`; no per-name resources; labels derived from provenance (`corpus:<label>:<tags>`); membership ≠ authz declared; inspect exposes no registry/compartment surface (`IMPL_B5_ACCEPTANCE_2026-09-17`).
  2. Recall-side view campaign: 8/8 campaign cases PASS (`IMPL_B5_RECALL_VIEW_2026-09-17`).
  3. Fresh 0-diff regression & F-1 resolution: same-binary determinism achieved at **0 ULP (1,300/1,300 scores exact, 100.00%)** across seeds 6–10 in C00 and C01; 0 ordering diffs, 0 metric diffs; behavioral equivalence vs `10b48d8` verified (0 ordering diffs, 0 metric diffs); Erratum #37 recorded (`IMPL_SCORER_DETERMINISM_2026-09-18`).
  4. Sweep stream determinism: identical event streams across runs.
  5. Adversarial cases: 5/5 determinism unit tests pass.
- **Bundles:** `impl_b5_2026-09-17/` (`eba1590b…`), `impl_b5_recall_view_2026-09-17/` (`edf7be53…`), `impl_scorer_determinism_2026-09-18/` (`a53a47f6…`).
- **Receipt:** `receipts/W1_ROW_EXIT_B5_2026-09-18.md`.
- **Disposition:** READY FOR RATIFICATION.

---

## W2_01 — Relations & associations edges

- **Spec:** `docs/specs/W2_01_relations_edges.md` (`b355bdda…`; freeze `W2_SPEC_BATCH_FREEZE_2026-09-17`).
- **Acceptance §5:**
  1. C5 extension: relations byte-identical across processes incl. `rule_id`, `state`, `w/s/c/t`.
  2. Direction registration: later→earlier; flip fixture registers.
  3. No hidden coupling: rank-field audit + no-planner scan + 0-diff.
  4. Counts are edges, not attempts: admitted rows = raw proposals = 5; deduped endpoint metric = 1; sweep attempt stats separate.
  5. Manifest gate: driver scan confirms no `hebbian`/`decay`/`strengthen`/`weaken`/`edge-prune` symbol in serving path (dynamics parked).
- **Bundle:** `impl_w2_01_2026-09-17/` (`add54402…`).
- **Receipt:** `receipts/W2_ROW_EXIT_01_2026-09-18.md`.
- **Disposition:** READY FOR RATIFICATION.

---

## W2_02 — Retention & lifecycle

- **Spec:** `docs/specs/W2_02_retention_lifecycle.md` (`c9a2f09f…`; freeze `W2_SPEC_BATCH_FREEZE_2026-09-17`).
- **Acceptance §5:**
  1. Primary behavioral retention: 5/5 records 100% preserved across 5 `think_sweep` passes while relations transitioned `Candidate → Persistent → Cold`.
  2. Pure reads invariant: `data.mdb` sha256 invariant across 10 recall passes.
  3. All-zero success impossible: failed writes loudly raise typed refusals (`remember.refusal` journaled).
  4. Organ naming & symbol scan: 6 destructive retention/forget patterns absent from source and binary; no background scheduler.
  5. Fixed import tier: records created `Persistent` on every constructor.
- **Bundle:** `impl_w2_02_2026-09-18/` (`e7c95b88…`).
- **Receipt:** `receipts/W2_ROW_EXIT_02_2026-09-18.md`.
- **Disposition:** READY FOR RATIFICATION.

---

## W2_03 — Currentness strata

- **Spec:** `docs/specs/W2_03_currentness_strata.md` (`df769f30…`; freeze `W2_SPEC_BATCH_FREEZE_2026-09-17`).
- **Acceptance §5:**
  1. C2 template: ordering flip reproduced under `WM_GEN3_SWEEP=1` (strata order `[1, 0]`, strata `[0, 2]`) vs `WM_GEN3_SWEEP=0` (strata `[1, 1]`, default key order).
  2. No-knob derivation: environment-cleared runs reproduce strata derivation at request time; zero `WM_VALIDITY_*` symbols in binary or source.
  3. F4 guard: unit test `strata_f4_duplicate_relations_single_effective_state` (3 duplicate relations on one endpoint pair produce exactly one effective state: 1 stratum-0, 1 stratum-2; deduped metrics: 3 rows / 1 pair).
  4. Journal fields: `stratum` and `superseded_by` present per recall result; ordering reconstructible from journal.
  5. Mode disclosure: all strata claims explicitly name arbitration mode (`Structural`).
- **Bundle:** `impl_w2_03_07_2026-09-17/` (`3344ca9d…`).
- **Receipt:** `receipts/W2_ROW_EXIT_03_2026-09-18.md`.
- **Disposition:** READY FOR RATIFICATION.

---

## W2_04 — Dream & consolidation

- **Spec:** `docs/specs/W2_04_dream_consolidation.md` (`71f66725…`; freeze `W2_SPEC_BATCH_FREEZE_2026-09-17`).
- **Acceptance §5:**
  1. Matched A/B control: Store A (consolidation active) demoted unused relation to `Cold`, un-penalizing earlier record and shifting stratum from 2 to 1 in recall; Store B (control) retained active `Persistent` relation, keeping earlier record penalized by statutory 0.6x supersede multiplier.
  2. Journal attestation: 2 `relation.state_change` events attested (`candidate→persistent` and `persistent→cold`) with complete N4 hash linkage.
  3. Semantic object preservation: 2/2 records and relations preserved in-place; 0 deletions/purges.
  4. Restart persistence: relation `Cold` state verified across fresh process invocations.
  5. Phase-agnostic scan: confirmed absence of `DreamPhase`, 12/13-phase enums, CITTA metrics, and unintegrated priming/decay symbols.
- **Bundle:** `impl_w2_04_2026-09-18/` (`7b2b426b…`).
- **Receipt:** `receipts/W2_ROW_EXIT_04_2026-09-18.md`.
- **Disposition:** READY FOR RATIFICATION.

---

## W2_07 — Self-model & inspect

- **Spec:** `docs/specs/W2_07_selfmodel_inspect.md` (`09ed2e9f…`; freeze `W2_SPEC_BATCH_FREEZE_2026-09-17`).
- **Acceptance §5:**
  1. Inspect answers & pure read: inspect answers tier 1 constitution (authority: writers/readers/invariants), tier 2 statutes (budget + policy), tier 3 adaptive (records/relations); read-only verified (`data.mdb` and journal sha256 unchanged across `scope: all` and `scope: tiers`).
  2. Universe labeling & key scan: recursive key scan finds zero calibration / conformal / self-model / forecast / claims keys, and zero action / alert / optimizer / certification keys; absent surfaces disclosed by absence.
  3. Durable action log: disclosed: no graduated-action / optimizer machinery exists in Gen3; key scan asserts nothing claims one.
  4. Feeder disclosure: disclosed: no self-model metric series in Gen3; `projection.stats` is `null` when slot is off.
  5. No silent constants: inspect reports declared tier state and statutes; no un-journaled constant overrides.
- **Bundle:** `impl_w2_03_07_2026-09-17/` (`3344ca9d…`).
- **Receipt:** `receipts/W2_ROW_EXIT_07_2026-09-18.md`.
- **Disposition:** READY FOR RATIFICATION.

---

## Operator act — RATIFIED 2026-09-18

- [x] B5 exit ratified — Lucas Bailey (operator) — 2026-09-18 · receipt `W1_ROW_EXIT_B5_2026-09-18.md`
- [x] W2_01 exit ratified — Lucas Bailey (operator) — 2026-09-18 · receipt `W2_ROW_EXIT_01_2026-09-18.md`
- [x] W2_02 exit ratified — Lucas Bailey (operator) — 2026-09-18 · receipt `W2_ROW_EXIT_02_2026-09-18.md`
- [x] W2_03 exit ratified — Lucas Bailey (operator) — 2026-09-18 · receipt `W2_ROW_EXIT_03_2026-09-18.md`
- [x] W2_04 exit ratified — Lucas Bailey (operator) — 2026-09-18 · receipt `W2_ROW_EXIT_04_2026-09-18.md`
- [x] W2_07 exit ratified — Lucas Bailey (operator) — 2026-09-18 · receipt `W2_ROW_EXIT_07_2026-09-18.md`

Recorded by the attesting session `221fbb57` per the operator's in-session directive (verbatim: **"I ratify all docs"**); ratification is the operator's act — the session records it, it does not ratify.
