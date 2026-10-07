# Theory ↔ Mechanism Map — what the design corpus cashes out to

**Status:** design record · 2026-09-17 (updated 2026-09-19: sources + entry-gate note + GATED-S-003
count criterion + Brier identity) · **not binding** (`CHARTER.md` binds; `DESIGN_CANON.md`
remembers; this file classifies). Written from a second pass over the founding conversations
(`~/Desktop/dev journal/WHITEMAGIC CHATGPT CONVERSATIONS.txt`, cited as CONV with segment map in
§7) against the current record: `HANDOFF.md`, `archive/legacy/ARCHITECTURE_CONSOLIDATION.md`,
`experiments/testbed_ii/gated{,2,3}/REPORT_GATED*.md`, `archive/legacy/METABOLISM_PLAN.md`.

Purpose: one place that says, for every theoretical frame in the corpus, **which status label it
carries**, **where it lives** (code, docs, experiment, or nothing yet), and **what would move
it**. This is not a fourth thesis (CONV L3967–3971: *"We now have enough philosophy"*). It assigns no verdicts of its own; the Phase-3 verdicts live in the ratified
`archive/research/PHASE3_DECOMPOSITION.md` (entry decision 2026-09-17).

## 0. Status vocabulary (fixed — extend only with an operator receipt)

| Label | Means |
|---|---|
| **OPERATIONAL** | implemented and exercised; evidence exists in-tree |
| **PARTIAL** | a mechanism exists; the concept *as described* does not |
| **RENDER-ONLY** | deliberately no runtime branch (Charter §3.10) |
| **FALSIFIED** | tested under a frozen registration and rejected as stated |
| **DEFERRED** | out of scope by decree; re-entry has a named gate |
| **UNTESTED** | no mechanism yet; entry requires an experiment |

---

## 1. The epistemic spine — one law, three costumes

> **Absence of evidence must not masquerade as evidence of absence.**

It appears at three altitudes; all three are now **OPERATIONAL**:

| Costume | Where | Source |
|---|---|---|
| Retrieval abstention | WMv9 `memory.search` → `insufficient_evidence / no_results_above_floors`; WMgen3 `selection.decision.abstained` + journal | CONV L145–153 |
| "No silent zeros" | MandalaOS doctrine; Gen2 `wm status` index-drift disclosure | CONV L442–446 |
| "Label every claim" | Site claim types (Measured/Observed/Hypothesis/Research goal); claims ledger | CONV L143–153, L1443–1457 |

Corollaries, likewise settled as doctrine (some OPERATIONAL, some PARTIAL — see §3):
receipts before trust (CONV L228–232); observe before enforce + the graduated ladder
(observe → notify → nudge → throttle → human-confirmed isolate; CONV L268–310, L526);
safety-through-continuity (persistent accountability over kill-switches; CONV L1593–1625);
and the moral-uncertainty stance — **grade the environment, not the mind** ("safe if AI isn't
conscious, humane if it is"; CONV L287–302, L1661–1685), sharpened to *"developmental power is
governance power"* (CONV L3737–3753).

## 2. The two Closures are information-flow properties (analysis)

The strongest *formalizable* contribution in the corpus. Read them as label-flow rules:

| Closure | Charter | Information-flow reading | Enforcement today |
|---|---|---|---|
| **1 — Law** | §3.7 | **Non-interference / capability typing**: constitutional state is high-integrity; no low-integrity (adaptive) write path may reach it; reads only through an immutable typed view | `constitution.rs` types + static write-unreachability analysis + compile-fail proofs + live canaries (`CLOSURE_TESTS.md`; Phase-1 receipt: 12 unit + 5 compile-fail, scans green) |
| **2 — Evidence** | §3.8 | **Taint tracking / label immutability**: `domain ∈ {world, system, simulated, reported}` is set at construction and never mutates; `world` enters only as new records through a ratified intake channel | Same machinery; canary probes (laundering / testimony / unchannelled) refuse and log |

Why this matters: everything else in the philosophy is persuasion — *these two are
type-checkable*. The Gen2 lesson they encode is exact: canaries that exist but never fire are
worth nothing (`archive/research/CODE_ARCHAEOLOGY.md` §12), so the gate is a **demonstrated live refusal**, not a
module's presence. If the project ever earns a formal-methods budget, this is where it goes.

## 3. Frame ledger

Statuses per §0. "Moves it" names the smallest thing that would change the label.

### 3.1 Epistemics & governance

| Frame | Origin | Status | Where it lives | Moves it |
|---|---|---|---|---|
| Evidence-warrant ladder | CONV L143–153, L1443–1457 | **OPERATIONAL** | Site claim components; claims ledger; this repo's doc discipline | — |
| Abstention / no silent zeros | CONV L145–153, L442–446 | **OPERATIONAL** | Gen2 abstention contract; WMgen3 journal | — |
| Receipts / journal-as-evidence | CONV L228–232 | **OPERATIONAL** | Gen2 write-audit + karma; WMgen3 JSONL journal + hash out | — |
| Closure 1 — Law | CONV L4036 | **OPERATIONAL** | §2 above | A failing canary would demote it to broken |
| Closure 2 — Evidence | CONV L4036 | **OPERATIONAL** | §2 above | Same |
| Calibration (Brier / conformal / empirical-Bayes) | CONV L3058, L3543 | **OPERATIONAL** | Gen2 live-store ledger carries the Brier figures (0.078 is **not** the v26 runtime number: v26 = 0.2563 overall / 0.0731 time_estimate; `citta/calibration.jsonl` has CRPS only — Errata #25); `wm-conformal`; shrinkage | — |
| Observe-before-enforce + graduated ladder | CONV L268–310, L526 | **PARTIAL** (org level) | MandalaOS lane; this substrate contributes evidence, not enforcement | MandalaOS false-positive data |
| Safety-through-continuity | CONV L1593–1625 | **UNTESTED** | Substrate pieces exist (provenance, supersession, continuity); the *claim* is not tested | A longitudinal study; not planned |
| Credit-assignment ladder | CONV L3869–3885 | **PARTIAL** | Ratified as the causal-attribution gate (Charter §6); no mechanism exercised | Phase 3; first credited structure |

### 3.2 Memory & retrieval

| Frame | Origin | Status | Where it lives | Moves it |
|---|---|---|---|---|
| Supersession / currentness as core relation | CONV §2; the experiments | **OPERATIONAL — emerged as the one cross-ecology survivor** | Rule `candidacy.v1.shared-rare+value-diff+temporal`; structural strata; Testbed II: stale-label suppression 1/20 vs 8/20 | — |
| Projection as optional lens (multiview memory) | CONV L1910–1963 | **PARTIAL** — conditional lens confirmed *in designed regime* (gated2: adjudicated g2 53 vs g0 36); solo null (P2B falsified) | `projection.rs`, τ=0.694, `WM_GEN3_PROJECTION` | An activation rule that is neither always-on (cost) nor floor-based (falsified); the count<2 criterion is confirmed gate-scoped (GATED-S-003, claim-0007) for state resolution only — the ≥2-candidate boundary stays open |
| Activation policy for lenses | `GEN3-GATED-S-001/-002` → `-003` | **FALSIFIED** (floor policy, gate-scoped) / **PARTIAL** (count<2 criterion: confirmed gate-scoped, state resolution only — claim-0007) | Reports in `experiments/testbed_ii/gated*/` | A primitive that distinguishes "no support" from "low support", or catches the ≥2-candidate regime — recorded design question, not planned |
| Retention lifecycle (rotation not deletion) | Gen1 `mindful_forgetting` | **OPERATIONAL** (Gen2) | Gen2 retention + cold rotation; WMgen3 lifecycle stub | Phase-3 compile row |
| Hebbian associations | Dec 2025 NeuralMemory | **PARTIAL** | Gen2 `associations.rs`; WMgen3 promotion policy candidate | Phase 3 |
| Holographic coordinates / stars | CONV L1910–1963, L2655–2665 | **RENDER-ONLY** in Gen2 (coords demoted to visualization; "no semantic locality" verdict) + DESIGN in canon §3.3 | Gen2 coord systems; canon §3.3 | A demonstration that projections beat flat ranking on a real corpus |
| Hypergraph relations | CONV L2066–2114 | **UNTESTED** | Canon §3.5 DESIGN; relations today are flat typed edges | Phase 3; a task where multi-source relations decide |

### 3.3 Cognition & selection

| Frame | Origin | Status | Where it lives | Moves it |
|---|---|---|---|---|
| Field dynamics (activation/decay/inhibition/temperature) | CONV L2154–2219 | **PARTIAL** (Gen2 primitives) / **DEFERRED** (WMgen3 field) | Gen2 activation map, 300 s decay **declared but never applied** (`tick_decay` has zero callers — activations saturate; live propagation is offline-only); WMgen3 `e=(w,s,c,t)` only (errata 2026-09-17, `archive/research/PHASE4_ERRATA.md` F-14) | A task where propagation beats retrieval (none demonstrated; v26's read-side SA channel was live in the default planner — see `archive/research/findings/W3_field_activation.md`) |
| Selection theory (constitution → eligible → Pareto → statutes + exploration budget) | CONV L4089–4096, L4098–4122; Charter §6 | **PARTIAL** | Per-operation selection contracts in Phase 1; Pareto/statutory layer pending | Phase 3 |
| Recall compiler / verbs-as-ISA / planner | CONV L2323–2366, L2515–2550 | **UNTESTED** — the verb-basis thesis is unvalidated | Four verbs built; no compiler | A composability demonstration in Phase 3 |
| Thought-stars vs memory-stars (stellar lifecycle) | CONV L2116–2152 | **UNTESTED** | Canon §3.4 DESIGN | Any experiment where ephemeral→durable promotion matters |
| Spectral meta-gardens (eigenmodes) | CONV L3078–3088 | **DEFERRED** | Julia lab plan; canon §7 | Phase 3+; needs the resonance matrix to exist first |
| Credit = traceable participation (no co-occurrence credit; delayed horizon) | CONV L3869–3885 | see 3.1 | — | — |
| Soma/germline, Geneseed, developmental ecology | CONV L3587–3615, L3887–3905, L3737 | **DEFERRED** (Phase 4 by scaffold decree) | Canon §10; re-entry rule: *after selection is demonstrated* | A working selection loop |
| Membranes / endosymbiosis (logical, not physical) | CONV L3755–3793 | **RENDER-ONLY** stance | Not needed until integration pressure exists | — |

### 3.4 The symbolic set (all RENDER-ONLY by law, Charter §3.10)

Alchemy/Magnum Opus (already promoted to historiography in `planning/MAGNUM_OPUS.md`),
Tree of Life (9 spheres ↔ 9 verbs — noted convergent, not causal), Yijing (64-basis
combinatorics), Suares, Wu Xing, Gan Ying (感應 — "resonance": the *concept* is PARTIAL in
Gen2's event bus, which is a conventional pub/sub), Yogācāra (dispositions without fixed
essence — the closest philosophical analogue to "identity is a view over the store"),
Mahāmudrā (arise/dissolve without grasping — the analogue of field dynamics), Huna, Hopi.
Rule: **symbols may render; symbols may never dispatch** (CONV L4063). Symbols don't need
status labels beyond this; they are the corpus's design language and narrative memory.

## 4. Real-math notes (what implementing each frame would actually be)

- **The field, if built**, is a **weighted hypergraph + diffusion-with-restart**: activation =
  random walk with restart, decay = damping, "temperature" = inverse softmax temperature on hop
  selection, constellations = **metastable communities** of the resonance operator. Pre-register
  its failure modes with it: over-smoothing, hub dominance/popularity collapse, walk starvation
  on cold regions. The doc's spectral plan (Laplacian/NMF/community detection → meta-gardens,
  CONV L3078–3088) is the correct offline analysis for exactly this object.
- **Temperature is a metaphor with a precise referent** (sampling temperature); if it ever becomes
  a parameter, define it operationally first (inverse softmax on hop selection, or a retrieval-
  breadth variance), or it becomes the first violation of "symbols never dispatch."
- **Credit assignment** = incremental causal attribution: traceable participation > correlation,
  delayed horizon as a statute, co-occurrence permanently ineligible. The contribution record
  (CONV L3873) is the audit object.
- **Selection** = constrained multi-objective optimization where the constitution is a
  *feasibility constraint* (never a tradeable score) and exploration is an explicit budget line.
- **M = externally grounded intake / total processing** (`archive/legacy/METABOLISM_PLAN.md` §3). Monitor, never
  a target — Goodhart is already named in the plan. Its product half is the release cadence.
- **Currentness strata** (structural arbitration: current/unresolved/superseded, ranks within)
  is the empirically strongest mechanism produced so far — more than any field math.

## 5. Tensions kept visible

1. **"No subsystem per capability" vs Gen2's best pieces being subsystems.** Resolution: the
   seam, bundles, revisions, karma chain are *substrate*, not capabilities. Say so explicitly so
   the rule never confiscates the foundations.
2. **The verb-basis thesis is unvalidated.** Four verbs + minimal field lost the Phase-2 A/B;
   what's earned so far is state *resolution*, not recall, and reuse/composability is untested.
   The honest claim: *a small substrate resolves "what is current" better; it does not yet
   remember more.*
3. **The field can become "Gardens in mathematical clothing"** (CONV L4102's own warning).
   Antidote already in force: `e=(w,s,c,t)`, nothing more until an experiment demands it.
4. **Consciousness language vs claim discipline** — resolved only by operational definitions and
   environment-grading (§1). Any runtime wellbeing claim would have to pass the same bar as any
   capability claim.

## 6. The bets, with status

| # | Bet | Status |
|---|---|---|
| 1 | Immutable epistemic domains (Closure 2) | **OPERATIONAL** |
| 2 | Supersession/currentness as the core relation | **EARNED** (cross-ecology) |
| 3 | Gated lenses | **FALSIFIED as floor policy** (GATED-S-001/002); count<2 criterion **confirmed gate-scoped** (GATED-S-003, claim-0007); lens conditionality survives |
| 4 | Mechanized selection replacing human curation | **UNTESTED** (architecture only) |
| 5 | Metabolic openness as measurable health | **PARTIAL** (metric defined; first honest reading pending) |

## 7. Sources & citation conventions

- **CONV** = `~/Desktop/dev journal/WHITEMAGIC CHATGPT CONVERSATIONS.txt` (moved from the
  Desktop 2026-09-16; same file). Segments: **§1** L5–1740 (9.1.6→9.1.7 audit + lab identity) ·
  **§2** L1741–3420 (Gen3 design sessions) · **§3** L3422–4271 (Gen1/Gen2 expedition + strategy).
  Cite as `CONV §2 L2197`.
- Companion records: `DESIGN_CANON.md` (converged design vocabulary, IMPL/PARTIAL/DESIGN tags),
  `archive/legacy/ARCHITECTURE_CONSOLIDATION.md` (per-mechanism experiment matrix),
  `archive/research/PHASE3_DECOMPOSITION.md` (route families + hypotheses), `archive/legacy/METABOLISM_PLAN.md`, `CHARTER.md`.
- External projects referenced by the corpus (Zero/Moving Castles, Aventurine, Savannah,
  alignment-via-RPG) are context, not lineage — see CONV §3 L3563–3648 and L3755–3793.

## 8. Discipline rules this map exists to protect

1. **No fourth thesis.** The next artifact after this map must be a pre-registration, a receipt,
   or nothing (CONV L3967–3971).
2. **Symbols render; symbols never dispatch** (Charter §3.10).
3. **One name per concept** (the Mandala-Glossary discipline: one canonical name per concept;
   metaphor overload is the flagged failure mode of the baroque era).
4. **Verdicts are gated**: this map assigns none; ratified Phase-3 verdicts live in
   `archive/research/PHASE3_DECOMPOSITION.md` (entry decision 2026-09-17; `receipts/PHASE3_COMPILE_PASS_2026-09-17.md`).
5. **Counts and statuses are generated or tested**, never narrated upward (HANDOFF §4).
