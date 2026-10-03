# B5 extension — Recall-side scope view (registration)

**Status: FROZEN — operator-ratified 2026-09-17** (freeze receipt
`receipts/W1_B5_RECALL_VIEW_REGISTRATION_2026-09-17.md`) · compiled against WMgen3 tip `528047e`;
source tree clean before creation of this registration document. Implementation proceeds under
this registration (implementation freeze → fresh 0-diff regression → acceptance demonstration;
receipt `IMPL_B5_RECALL_VIEW_<date>.md`). Registration required because this unit changes the
recall surface (external review, 2026-09-17; `HANDOFF.md` opener; checkpoint `823eebb2`).
Incorporates operator review adjustments (cross-scope crowd-out acceptance case, frozen label
grammar, pinned disclosure vocabulary). Parent spec:
`docs/specs/W1_B5_galaxies_compartments.md` (frozen; compile/link side accepted in
`IMPL_B5_ACCEPTANCE_2026-09-17`). **The view is not a boundary** — nothing here creates an
isolation, security, or authorization semantics; the label→ontology bridge is a *selection over
provenance*, and the disclosure is the contract.

---

## 0. What exists today (evidence)

- Gen3 scope is **provenance-based**: the harness maps `galaxy` + `tags` into record
  `source = "corpus:<label>:<tags>"` (`crates/wm-gen3-harness/src/main.rs:250`).
- A1 scope law (demonstrated): admission/dedup are **per scope**, keyed
  `(content sha256, source, kind)`; no global dedup (`IMPL_A1_FIXTURES_2026-09-17`).
- B5 acceptance (demonstrated): 30 labels (over Gen2's dynamic cap 20) create **no per-name
  resources** — store file set stays `{data.mdb, lock.mdb}`; label views are reconstructible
  from provenance chains; `inspect` exposes no galaxy/label/registry/compartment/capability
  surface. The view filter was **wrapper-side** (driver): prefix filter, no new API.
- `recall` today has no scope selector: `RecallQuery { query, limit, candidate_limit,
  include_historical, min_score, min_coverage }` (`crates/wm-gen3-core/src/ops.rs:95`); results
  carry `source` + provenance chain per hit (`ops.rs:893`).

## 1. Scope of this registration (what changes, what must not)

**Change:** `recall` accepts an **optional** scope view selector (`scope=<label>`) and, when
present, selects only records whose provenance parses to that label. Default (absent) behavior
is untouched.

**Declared view derivation rule (ablatable, pinned here):**
`view(label) = { record : record.source = "corpus:<label>:<tags>" }` — the label is the second
colon-separated component of a `corpus:`-prefixed source. Records whose source does not match
that shape belong to no label view (reachable unscoped only). No other provenance scheme is
implied; a second scheme is a new registration.

**Declared label grammar (lexical law; no validation machinery beyond this).** A label is an
**opaque, exact, case-sensitive byte string**: nonempty, containing no `:` character. No trimming,
no case folding, no Unicode normalization, no aliases, no inference — `"Foo"`, `"foo"` and
`" foo "` are three distinct valid labels. *Record side:* a source is view membership only when
it is exactly `corpus:<label>:<tags>` with `<label>` nonempty and colon-free; `corpus::tags`
therefore carries the **empty label**, which is not a view — such records are label-less. *Caller
side:* a selector violating the grammar (empty, or containing `:`) is an **invalid selector** — a
typed caller error, fail-closed, **no journal entry** (same discipline as A2's out-of-range
floors), never a silent empty view. A record-side or caller-side violation can never alias,
normalize, or widen into a valid view.

**View-not-boundary clauses (contract):**
1. The view is a **population filter applied before selection**, not a scorer and not a
   boundary: within-view ordering must equal unscoped ordering restricted to the view.
2. **Explicit selection stays explicit**: the selector exists only when a caller supplies it.
   No environment variable, config default, or inference path may scope a recall implicitly —
   the explicit path must not become the default path (B5 §1.1; adversarial case 3).
3. **No fabrication**: a valid label with zero records yields an **empty result list with the
   pinned disclosure** — `abstained: true`, `reason: "insufficient_evidence"`, additive
   `cause: "no_candidates_in_scope"` (with the `scope` field present) — never an error and never
   synthesized results (B5 §1.2). The A2 reason vocabulary is reused exactly; exactly one new
   cause token is declared here.
4. **No new resources**: the selector creates no registry, no per-name store, no cap surface
   (closed by absence — B5 acceptance §2).
5. **No security claim**: the view is not isolation and must never be described as one;
   cross-scope membership semantics (`_meta`-style authz) remain link-side and out of Gen3.

## 2. Wire (implementation contract)

| Piece | Pin |
|---|---|
| Core | `RecallQuery` gains `scope: Option<String>`; candidate population filtered by the §1 rule before scoring/selection; scoring, strata, floors, and abstention logic unchanged |
| Adapter | `memory.episodic_search` accepts an optional `scope` arg (same arg name the harness already uses for `inspect`); absent → pre-change request/response behavior unchanged |
| Journal | `selection.decision` gains **additive** fields only when a scope is present: `scope` (label, exact bytes) and `scope_considered` (candidates in view). Empty view → `abstained: true`, `reason: "insufficient_evidence"`, additive `cause: "no_candidates_in_scope"`; a view with candidates that floors exclude keeps `cause: "no_results_above_floors"` (scope present); an invalid selector → typed caller error, **no journal** (A2 discipline). Absent scope → event unchanged (required for the journal half of the 0-diff regression) |
| Switches | none added; the selector itself is the ablation surface |
| Default path | no scope → pre-change request/response behavior unchanged (population, ordering, metrics, journal events; §3.1 is the proof) |

## 3. Acceptance (fresh; no inert entries)

1. **Fresh 0-diff regression (the gate).** New binary with no scope argument ≡ source-frozen
   reference at the pre-change tip on the **gate-neutralized regression corpus** (protocol §9
   recipe; `transform_id gate-neutralize.v1.2026-09-17` where the standard corpus is used):
   per-query × 6 fields 0 diffs, ordering/metrics exact, scores ≤ 1 f32 ULP; journal event
   sets identical (timing fields excluded).
2. **View correctness.** Fresh fixture campaign (scripted + hash-recorded, new labels distinct
   from the B5 acceptance set, including a shared-token cross-label pair): `scope=L` returns
   exactly the label-L records. Tested at two label counts, one over Gen2's cap 20 (the
   view-not-registry claim) and one with a shared token across labels (no bleed).
3. **Filter-not-scorer (relative order).** For any label L: unscoped results restricted to L
   equal scoped results for L (relative order preserved), with limits ≥ store size.
4. **Cross-scope crowd-out (filter-before-selection).** Fixture: one valid L record plus enough
   higher-support out-of-scope records to exceed a deliberately small `candidate_limit`;
   `scope=L` must still return the L record. An implementation that filters *after* candidate
   selection fails; one that filters the population before scoring/selection passes. This turns
   the "filter before selection" contract into a demonstrated property.
5. **Unknown/empty label.** A valid zero-record label → empty `results` + the pinned disclosure
   (§1 clause 3); no error, no fabrication.
6. **Malformed selector.** `scope=""` and any selector containing `:` → typed caller error, no
   journal entry, no silent widening — the caller-side mirror of the malformed-provenance case.
7. **Explicit-only.** Source scan: no env/config/inference path can set a scope; absent arg
   leaves the default path untouched (case 1 covers behavior).
8. **Bare bytes.** Store file set and `data.mdb` hash unchanged by scoped reads (read-only
   discipline; the B5/A2 pattern).

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Scope view selector | `scope=L` → view population; journal shows `scope`/`scope_considered` | absent → full population, unchanged events | EXECUTED → EFFECTFUL (view changes the selected set) |

No env switch is introduced; the on/off comparison is the argument itself, journal-verified.
The filter-not-scorer case (acceptance 3) is the ablation's honesty check.

## 5. Adversarial cases (B5 §3 adapted; N/A items named, not skipped)

1. **Unbounded scope names** — a label creates no per-name resources (B5 acceptance; re-run in
   the fresh campaign).
2. **Isolation asymmetry** — N/A: Gen3 has no class markers or transfer machinery; the view
   makes no isolation claim (disclosed).
3. **Explicit-selection creep** — asserted: no implicit scoping path (acceptance 7).
4. **Capability typos** — N/A: no capability parameter exists in Gen3.
5. **Tier degradation label** — N/A: no tier labels in Gen3.
6. **Cap bypass** — closed by absence (no registry; B5 acceptance §2).
7. **Membership-vs-authz** — declared: the view is membership-shaped selection, never
   authorization (B5 §1.3).
8. **Fail-open-on-error** — N/A for governance; the nearest law: empty view is disclosed, not
   silently widened (acceptance 5; §1 clause 3).
9. **Narrative guard** — cited: no Gen3 metric cites the 47-galaxy figure (errata A#6).
10. **Malformed provenance** — a record whose source lacks the declared shape is label-less;
    it must never be selected by any label view (tested in the fresh campaign).
11. **Malformed selector** — `scope=""` or any selector containing `:` is refused as a typed
    caller error with no journal entry (acceptance 6); case 10 is the record-side mirror of the
    same parser boundary.

## 6. Non-goals

No isolation/security/authorization semantics · no class markers or transfers · no registries,
caps, or per-name resources · no implicit/default scoping · no automatic label inference (the
selector is caller-supplied only) · no label normalization, trimming, case folding, or aliasing ·
no changes to A1/A2, R/strata, projection gates, audit, or harness contract beyond the additive
optional arg · no per-result view scoring or blending.

## 7. Fences

| Piece | Pin |
|---|---|
| Candidate | new `wm-gen3` release build at the implementation-freeze tip; hash recorded in the receipt (instance label) |
| Reference | source-frozen pre-change tip rebuild for the 0-diff regression |
| Control | Gen2 v9.1.7 — untouched; this unit runs no A/B |
| Corpus | gate-neutralized regression corpus + fresh scripted fixture campaign (hashes in `MANIFEST`/transform record) |
| WMv9 | read-only |
| Audit | unchanged; run journal manifest + hash-out as always |
| Claims/verdicts | none moved; WEAK stays WEAK |

## 8. Freeze block

- [x] Owner assigned (operator): Lucas Bailey
- [x] Registration ratified (operator signature below) — freeze receipt
      `receipts/W1_B5_RECALL_VIEW_REGISTRATION_2026-09-17.md`
- [ ] Implementation freeze (source hash at the tip that adds the selector)
- [ ] 0-diff regression + acceptance demonstrated — receipt `IMPL_B5_RECALL_VIEW_<date>.md`

Operator signature: Lucas Bailey — recorded per in-session directive 2026-09-17
("All three: ratify, authorize, commit"; see the freeze receipt). Date: 2026-09-17

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this registration alone.
