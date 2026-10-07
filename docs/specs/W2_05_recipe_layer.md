# Wave-2 spec 05 — Recipe layer (candidate)

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/archive/research/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `3d67663` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. Freeze at operator
ratification + `receipts/` entry.

**Row:** Recipe layer (candidate) (wave plan §3; **compile candidate** · E16).
**Wire:** operator vocabulary + recipe runtime; **anti-bloat law** attaches to every candidate.
**Gate (wave plan §9):** **the recipe layer executes only after its anti-bloat review** — this
spec freezes the candidate contract and the review criteria; the review itself is an operator-act
precondition recorded in the receipt.
**Nucleus touch points:** §2.4 (missing-primitive candidate: "operator vocabulary + recipe
runtime — the anti-bloat law attaches to every candidate; SkillForge metadata is not evidence");
canon §7 (compositions enter as recipes, not classes).
**Caution carried:** E16 corrected — v26 **did** run whole-call trace mining (33 persisted
skills, 22 auto-forged, 4-verb vocabulary, `parameters={}`); the **operator-level runtime did
not** exist; Gen2 `skill.*` is lookup-only. Metadata is not evidence.

---

## 1. Frozen behavioral spec

### 1.1 The recipe contract

- A **recipe** is a composition of existing operations, expressed in the **operator vocabulary**,
  replayable, whose replay produces **journal-visible effects** (the acceptance). No new
  class/module per composition (anti-bloat law; canon §7).
- A recipe stores what it needs to replay: named steps, populated parameters, and provenance of
  its forge (operator-authored / mined-from-traces / amended). `parameters={}` write-only
  shells are excluded.
- **Replay must actually match:** the v26 failure class is a forge that persisted skills the
  router never matched (write-only recipes; zero amendments, 4/33 with execution history,
  `parameters={}`). A recipe that cannot be invoked is storage, not a runtime.

### 1.2 Amendment and evolution

- Recipe amendments are journaled events (what changed, why); a layer with zero amendments and no
  amendment path is a snapshot, not an evolving vocabulary. No claim of evolution without
  observed amendments.

### 1.3 Vocabulary discipline

- The operator vocabulary (the 4-verb style vocabulary is the ancestor shape) enters only with
  operational meaning per verb; trace mining may *propose* recipes, never silently define
  vocabulary.
- Compositions observed in traces are candidates, not classes: the anti-bloat review is where
  candidate→recipe admission happens (criteria: replay-visible effect, non-trivial reuse, no
  class explosion).

### 1.4 Evidence

- Recipes are journal-attested on replay (N4); recipe metadata caches (SkillForge JSON class) are
  **not** evidence of capability (E16).
- No implicit authority: a recipe replays existing operations with their existing effect rows;
  recipes cannot escalate effects (Firebreak/capability seams unchanged).

### 1.5 Statutory parameters named (Tier-2)

Vocabulary version · parameter schema (populated or refused) · amendment event schema.

### 1.6 Non-goals

No classes per composition · no write-only skills · no runtime before the anti-bloat review ·
no vocabulary by mining fiat · no effect escalation.

---

## 2. Selection history

**Ancestor (Gen1 v26):** the 28-slot Engine Framework was **metadata** (77 concepts; 54/77
classes exist; 12/28 canonical names have a class in the declared path; no base class, no
dispatcher). Executables ran as pipelines (Kaizen detectors, Serendipity live at startup,
Apotheosis in-memory). **SkillForge actually ran and persisted 33 skill JSONs** (22 auto-forged)
— whole-call traces, ops string-matched into 4 verbs (SEARCH/ANALYZE/TRANSFORM/CONSOLIDATE),
`parameters={}`, 4/33 with execution history, zero amendments; **replay was dormant** (router
never matched forged skills) — recipes were write-only.

**Selection fate:** folded; ratified as a **missing-primitive candidate** (operator vocabulary +
recipe runtime) under the anti-bloat law; Gen2's `skill.*` is lookup-only (Codex-tagged memories;
invocation = lookup/echo), SkillForge exists only as a catalog name — "SkillForge metadata is not
evidence" holds for Gen2, while v26's mining is the ancestor.

**Evidence levels:** v26 forge SOURCE-IMPLEMENTED + persisted artifacts (33 JSONs); replay dormant
(STATICALLY-REACHABLE absence); engine framework metadata (SOURCE-IMPLEMENTED, no execution);
Gen2 lookup-only (SOURCE-IMPLEMENTED + live); Gen3 runtime NAMED (candidate; gate = anti-bloat
review).

---

## 3. Adversarial cases

1. **Write-only replay** — a forged recipe the router never matches fails acceptance (invoke it
   or don't store it).
2. **Empty parameters** — `parameters={}`-class shells refused.
3. **Class creep** — a composition that adds a class fails the anti-bloat review; it must enter
   as a recipe.
4. **Replay effect** — replaying a recipe yields a journal-visible effect; a no-effect replay is
   a defect.
5. **Amendment path** — amendments are journaled; a layer that cannot amend is disclosed as a
   snapshot.
6. **Vocabulary by fiat** — mined traces propose; only the review admits vocabulary.
7. **Effect escalation** — a recipe cannot widen effect rows of its steps.
8. **Metadata-as-evidence** — no capability claim cites SkillForge-style metadata.

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Replay | journal-visible effects | none (recipes inert → fail) | EXECUTED → EFFECTFUL |
| Skill store deletion | no ordering change (not a scorer until earned) | baseline | — (negative control) |
| Amendment flow | amendments observed | zero-amendment snapshot disclosed | RE-ENTERS (evolution claim) |

No inert passengers: a stored recipe with no visible replay effect is rejected at admission.

---

## 5. Acceptance + owner

Wrapper-side:

1. **Anti-bloat review passed** — precondition recorded in the receipt (operator act).
2. **Replay journal-visible** — effect events per replay; repeatable.
3. **No write-only storage** — every stored recipe is invocable by the runtime.
4. **Compositions as recipes** — no class additions.
5. **Amendment journaling** — observed (or the snapshot disclosure stands).

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + anti-bloat review + wired adversarial cases + demonstrated ablation +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Anti-bloat review completed (operator act; criteria above): ______________________
- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W2_SPEC_05_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
