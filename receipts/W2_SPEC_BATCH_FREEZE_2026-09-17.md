# RECEIPT — Wave-2 spec batch freeze ratified (2026-09-17)

**Status: FROZEN — 2026-09-17.** Operator ratified in session; the seven specs are in effect as
the frozen behavioral contracts for their rows. AI session
`c7ab9666-b4cc-4e87-a062-299467db4026` (opencode) prepared, verified, and attests; it does not
ratify. Append-only; corrections create a new receipt referencing this one.

---

## 1. Frozen artifacts (batch unit)

| # | File | SHA-256 |
|---|---|---|
| 01 | `docs/specs/W2_01_relations_edges.md` | `b355bdda609157117a6cb208f54485cc480b5be0672a0bab624366eb60833e91` |
| 02 | `docs/specs/W2_02_retention_lifecycle.md` | `c9a2f09f3cd8b15d537c8af2565c0ebe55bdbcb9b582d208952ff99d53647462` |
| 03 | `docs/specs/W2_03_currentness_strata.md` | `df769f3099dadb48ab24833acbf8cd53349469585e3730766809c4a47930310f` |
| 04 | `docs/specs/W2_04_dream_consolidation.md` | `71f66725da651ba43c5e18e9593b1ddc84114e8740b583d77e3247df2f47ee88` |
| 05 | `docs/specs/W2_05_recipe_layer.md` | `60dcf5f3c7869b0c4bf0204ff8d1df563daf9826b3d83d6ebafaa53b59d71102` |
| 06 | `docs/specs/W2_06_rsi_over_journal.md` | `4a980a083fa7d09002f35eb96ec8837db5852f34ff096824715014d2dd18bf56` |
| 07 | `docs/specs/W2_07_selfmodel_inspect.md` | `09ed2e9f33ec1f2bce7a7ec3b0039c68d080f45a6c9d167ba7bdee04d31488fe` |

Compiled per `docs/PHASE4_WAVE_PLAN.md` §7 + §3 (wave-2 table), under the frozen nucleus
`docs/NUCLEUS.md` (`73c5a9cf…`). Tip at compilation: `3d67663` (tree clean; freeze unit commits
with this receipt). Any edit after ratification is a new version with its own amendment receipt.

## 2. Operator act — RECORDED

Owner assignment and freeze authorization prompted in session, 2026-09-17; operator instruction
recorded verbatim: **"continue with all remaining batches, items, slices, and phases"**
(extending the batch-A standing authorization).

| Field | Value |
|---|---|
| Operator | Lucas Bailey |
| Act | In-session authorization of the Wave-2 spec batch freeze + owner assignment + commit |
| Owner assigned | Lucas Bailey (operator) — all seven rows |
| AI attestation | Session `c7ab9666` compiled the specs, line-checked citations, verified pins — attestation only |

## 3. What was ratified (per row)

- **01 relations/edges** — typed persistence round-trip (kind/direction/provenance; C5 template);
  closed kind vocabulary with operational meaning per kind; **Hebbian parked on the serving path
  only** (mechanism status stated); no hidden ranking couplings; counts = admitted rows; rate/
  quality gates, not name blacklists.
- **02 retention/lifecycle** — **RetentionEngine ≠ Lifecycle::forget** named separately; import
  tier fixed `persistent`; forgetting is propose-and-review; cold rotation hash-verified; uniform
  object-type policy; all-zero "success" impossible; thresholds statutory.
- **03 currentness strata** — request-time derivation (no `WM_VALIDITY_*`-class knobs); 0/1/2
  semantics with historical uniformity; **F4 guard** (no phantom states; deduped metrics);
  arbitration mode named on every strata claim.
- **04 dream/consolidation** — consolidation = journal-attested pass with measured ordering
  effect; **no destructive triage**; 13/12 phase counts never inherited; engines/reports are not
  execution; CITTA label artifact excluded; field half gated to wave 4.
- **05 recipe layer (candidate)** — replay produces **journal-visible effects**; compositions
  enter as recipes, not classes; `parameters={}`/write-only classes excluded; amendments
  journaled; **anti-bloat review is the recorded gate precondition** (operator act before
  execution).
- **06 RSI over journal** — issue series journal-observable with stable identity; **maker ≠
  checker** (independent witness; disappearance ≠ success; threshold motion excluded);
  resolutions labeled asserted vs verified; execution claims require execution; ratios published;
  constants provenance.
- **07 self-model/inspect** — inspect answers tier/authority/explanation, read-only; **one
  calibration universe named** (self-model metric series), cross-universe quotes excluded;
  durable graduated actions; unfed model = display-only disclosure; optimizer outputs are
  proposals.

## 4. Verification

Docs-only artifacts: no code, gates, thresholds, or verdicts changed; no build/test run required.
At compilation: all seven spec sha256s recorded above; `docs/NUCLEUS.md` re-hashed `73c5a9cf…`
and `docs/PHASE4_WAVE_PLAN.md` re-hashed `60688d72…` — both match the ratified pins. Citations
line-checked against the wave-2 evidence set: `W2_gen2_source_map.md` §1–§7 (with file:line
pointers), `W2_associations_relations.md`, `W2_rsi_selfmodel.md`, `PHASE4_WAVE2_FINDINGS.md`
(index + divergences 1–6), errata register W2 items, and the DO_NOT_MIGRATE appendix (items
#1/#2/#3/#7/#8/#20/#21/#23/#24 cited where binding). No UNVERIFIED item is presented as measured
(ratios carry their artifacts; comment-sourced figures stay flagged).

## 5. Companion hashes

| Artifact | sha256 |
|---|---|
| `docs/PHASE4_WAVE_PLAN.md` | `60688d725d38c36f43e734904efae9bc9e160ffa2facffa69b1267c83a5b2fd0` |
| `docs/NUCLEUS.md` (frozen) | `73c5a9cfb9af65e52f7cf1dbae60f250ae2c9180b8d3f554d108acc01eb83495` |
| Wave-1 batch-A receipts | `receipts/W1_SPEC_A{1,2,3}_FREEZE_2026-09-17.md` |
| Wave-1 batch-B receipts | `receipts/W1_SPEC_B{1..5}_FREEZE_2026-09-17.md` |

## 6. Consequences

- **Wave-2 rows are specified.** Execution remains gated per row: the recipe layer waits on its
  anti-bloat review (recorded in that spec's freeze block); dynamics (Hebbian) wait on the
  promotion-policy manifest rule; field integration waits on the propagation task; learned phase
  selection and conformal recall remain experimental.
- No verdict, claim, gate, or threshold changes; WEAK stays WEAK; ledger stays at 8 claims.
- Adversarial cases must be wired as runnable acceptance assertions per row before exit; no row
  ships with an inert acceptance test.

## 7. Attestation

AI session `c7ab9666` compiled the seven Wave-2 specs, verified every pin and citation above, and
recorded the operator's authorizing act and owner assignment. Ratification is an external
operator act; this receipt records it — it does not itself ratify.
