# Wave-2 spec 04 — Dream / consolidation half

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/archive/research/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `3d67663` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. Freeze at operator
ratification + `receipts/` entry.

**Row:** Dream / consolidation half (wave plan §3; **compile** · E15 adjacency).
**Wire:** selection/lifecycle pass over the journal; **13 vs 12 phases never inherited**.
**Nucleus touch points:** N2/N4 (selection + journal-as-evidence); Part 1 invariants 2 and 3.
**Caution carried:** Gen2 engines/reports are **catalog names, not execution** (W2 §3);
"CITTA 18,204 (85 %)" is a **storage-label artifact**, not a capability (errata W2-3).
**Do not re-raise:** errata W2-4 (13 vs 12 phases recorded — never inherited either way).

---

## 1. Frozen behavioral spec

### 1.1 What consolidation is (and its teeth)

- Consolidation = a **selection/lifecycle pass over the journal** whose execution is
  journal-attested and whose result **changes a measured ordering** (promotions/demotions
  observable in later recall). Reports alone are not consolidation (W2 §3: alchemical rounds
  return heuristic counters — not engine execution). (SOURCE-IMPLEMENTED template; MEASURED
  acceptance required per instance)
- **Phase taxonomy is not a contract:** neither Gen1's 13 phases nor Gen2's 12 are inherited;
  a phase set is implementation detail. Learned phase selection (Gen2 `LearnedDreamCycle`) is
  experimental and enters only with its own measurement (effectiveness skip < 0.2 after 5 runs is
  Gen2 behavior, not a statute here).
- **No destructive triage:** Gen1's dream triage DELETEd rows; the pass may decay, promote, or
  propose — never delete (invariant 2). Edge halving is likewise not inherited.

### 1.2 Journal as the instrument (N4)

- Every consolidation action is a journal event; a pass that claims to have run without events is
  invalid, not silently unmeasured (N4 rule). In-memory-only "ran" claims (v26 `CycleEngine`)
  are excluded.
- Selection explanations (N3) cover consolidation-driven changes: a later recall must be able to
  attribute ordering changes to pass events.

### 1.3 The field half stays out

- The v26 field/priming half was never integrated (tool-only `apply_priming`); Gen2's decay never
  ticks (`tick_decay` uncalled — DO_NOT_MIGRATE #20). No priming/write-back enters through this
  row; the propagation-beats-retrieval task remains the named gate (wave 4).

### 1.4 Statutory parameters named (Tier-2)

Scheduling cadence (explicit, not assumed) · pass budgets (fail-closed) · promotion/demotion
policy constants (named per instance, none swept).

### 1.5 Non-goals

No phase-count inheritance · no destructive triage · no report-as-capability · no field
integration · no learned-phase claims without measurement · no CITTA-label citations.

---

## 2. Selection history

**Ancestor (Gen1 v26):** 13-phase dream that *did* write — triage DELETEs, edge halving,
promotions, kaizen insights; `CycleEngine` wrote nothing (in-memory, no attestation); the field
half never integrated; the citta stream sink was lossy (deque 100, rewritten) and the "18,204
CITTA turns" headline is every session turn written as `MemoryType.CITTA` — the real taxonomy is
`turn_type` tags (B2).

**Gen2:** dream live end-to-end under the daemon (12 phases, brain-wave-gated); learned phase
selection experimental; the 28 "engines" are catalogs/report generators, not execution units;
alchemical rounds are heuristic counters.

**Ratified reading:** the consolidation half is **real** (selection/lifecycle pass over the
journal); engine vocabulary is surface. Any Gen3 consolidation compiles as a measured pass, not a
phase-count port.

**Evidence levels:** v26 dream SOURCE-IMPLEMENTED (writes observed in files); CycleEngine
in-memory (UNVERIFIED it ran); Gen2 dream SOURCE-IMPLEMENTED + daemon-wired/live; Gen3 target
NAMED (pass + measurement).

---

## 3. Adversarial cases

1. **Destructive triage** — no deletion path may be reachable from consolidation; a delete
   proposal requires its own registration (row 02 discipline).
2. **In-memory "ran"** — a pass without journal events is unmeasurable and fails acceptance.
3. **Report-as-capability** — heuristic counters (alchemical-round class) may not be offered as
   execution evidence.
4. **Label artifact** — no CITTA count is cited as consolidation capability; turn_type is the
   real taxonomy.
5. **Phase inheritance** — an artifact quoting 13 or 12 phases as a requirement fails; phase sets
   are implementation.
6. **Field smuggling** — priming/decay from the field half cannot enter via consolidation; the
   named wave-4 task gates it.
7. **Teeth test** — a consolidation instance that changes no measured ordering is decoration
   (report it as such, or fail).

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Consolidation pass | ordering/selection deltas measured | no deltas | RE-ENTERS (must be non-zero where claimed) |
| Scheduling (daemon) | passes occur on cadence | no passes, no promotions | EXECUTED |
| Learned phase selection (if admitted) | effectiveness-based ordering of phases | fixed order | EFFECTFUL |

No inert passengers: every pass instance carries its measured delta before it can be cited.

---

## 5. Acceptance + owner

Wrapper-side:

1. **Pass-effect measurement** — consolidation changes a measured ordering (or is labeled
   decoration).
2. **Journal attestation** — every pass action is an event; hash-out linkage (N4).
3. **No destructive triage** — delete paths unreachable.
4. **No label citations** — capability statements use turn_type, not CITTA counts.
5. **Phase-agnostic** — no phase count is a requirement.

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + wired adversarial cases + demonstrated ablation (where implemented) +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W2_SPEC_04_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
