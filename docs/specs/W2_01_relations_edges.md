# Wave-2 spec 01 — Relations / associations (edges)

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `3d67663` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. Freeze at operator
ratification + `receipts/` entry.

**Row:** Relations/associations (wave plan §3; compile edges · dynamics **parked** · E6).
**Wire:** typed edges `(w,s,c,t)` already first-class; `supersedes` semantics owned by A3.
**Nucleus touch points:** Part 1 invariants 3 (provenance) and 9 (evidence/belief/speculation
distinct); N2 relation form; E6 precondition (relations first-class).
**Caution carried:** **"Hebbian parked" means the serving path, not the mechanism** — Hebbian is
live in Gen2 `wm-memory` (`activate`/`decay`; `memory.relate` re-activates) and absent from the
serving path (`graph_weight` default 0.0). The spec must say which side it means on every line.
**Do not re-raise:** errata W2-1 (typed links never persisted in v26 — recorded); the 460 MB bloat
figure is comment-sourced (UNVERIFIED).

---

## 1. Frozen behavioral spec

### 1.1 Edge form and round-trip

- `e = (w, s, c, t)` — learned strength · sign/direction · resource cost · trust — plus `kind`,
  `src`/`dst`, `class`, provenance, `state` (`PHASE1_CONTRACTS.md:58-63`). (SOURCE-IMPLEMENTED)
- **Typed persistence is the contract:** `kind` and direction survive save/load and transfer;
  the C5 canary (relation kinds/endpoints byte-identical across processes) is the template.
  The v26 class — typed columns exist, hydration ignores them, save re-inserts 3-column triples
  (`sqlite_backend.py:735-739`) — is **excluded**.
- **Direction is stored, not implied:** mined edges may be bidirectional, causal one-way; a
  direction flip in a fixture must register (H3 discipline, A3).
- **Edge provenance is mandatory:** miner run / extractor / transfer / manual — otherwise the
  edge is not admitted (v26 kept only `edge_type='causal'` metadata).

### 1.2 The closed kind vocabulary

- `supersedes` + `contradicts` are first-class and owned by N2/A3.
- `related · extends · temporal · causal · cascade` may exist only with **operational meaning per
  kind** (what changes in selection/disclosure because of this kind). A declared vocabulary that
  no store enforces is the v26 failure class and is excluded.
- **Strength `w`:** derived-at-write values (miner score, extractor confidence, cosine) are
  admissible with their derivation recorded; **use-learned strength (Hebbian) is parked** —
  re-entry only via the §3 manifest rule (promotion policy), and parked means the serving path
  here; the mechanism status must be stated wherever cited.

### 1.3 Selection influence is explicit — no hidden couplings

- The registered relation-driven ordering path is R + strata (N2/A3). Any further edge influence
  (graph walk, spreading activation, entity boost) requires its own registration; a weight that
  stays in the formula when its signal is absent (the v26 entity-boost 0.25 class) is excluded.
- **Counts are edges, not attempts:** counters increment on admitted rows only (v26's
  `links_created` incremented over `INSERT OR IGNORE` skips — the class is excluded).
- **Rate/quality gates, not name blacklists:** mining on homogeneous streams must be bounded by a
  declared rate/quality rule (the 1.36M-edge / ~460 MB incident class — figure UNVERIFIED — was
  "fixed" by excluding sessions + isolated galaxies by name; a blacklist is not a gate).

### 1.4 Dynamics (parked — do not execute)

No decay, prune, or Hebbian updates on the Gen3 side until the promotion policy exists. The live
Gen2 asymmetry (use increments counters, time decrements strength) is observed, not inherited.
Cold rotation's edge cleanup is A-row material (retention row 02).

### 1.5 Statutory parameters named (Tier-2)

Kind vocabulary (closed, versioned with the spec) · admission requirements (provenance, direction)
· any rate/quality bound (declared, not tuned).

### 1.6 Non-goals

No Hebbian dynamics · no unregistered ranking couplings · no name-blacklist gating · no
attempt-counting metrics · no per-kind decay until earned.

---

## 2. Selection history

**Ancestor (Gen1 v26):** two link vocabularies, one physical store — `associations` dict (id →
strength, no kind) hydrates and persists; `links` dict (`LinkType` 7 kinds + counters) exists in
`to_dict`/`from_dict` only, **no DB column**; every save strips typing. Writers mapped kinds then
never reached the DB. Hebbian in three places, none load-bearing (link package zero importers,
SQL `hebbian_strengthen` zero callers, graph-walk counters only). `CausalMiner` zero invocation
sites; its own comment records the 1.36M-edge bloat. Edge→ranking couplings all
extraction/mining-dependent.

**Selection fate:** folded into Gen2 `associations.rs` (typed edges persist; Hebbian live in
mechanism, absent from serving path); ratified verdict compiles **typed edges only**; dynamics
parked behind E6 + manifest rule.

**Evidence levels:** v26 source organs SOURCE-IMPLEMENTED; runtime distributions UNVERIFIED (no
Gen1 DB on host); Gen2 mechanism SOURCE-IMPLEMENTED + live, serving integration knob-gated
(`WM_RECALL_GRAPH_WEIGHT`); Gen3 edge form NAMED (compile target).

---

## 3. Adversarial cases

1. **Round-trip erasure** — mine a directed edge, update/re-save the source; kind/direction
   survive (both typed-update and hydration paths).
2. **Target-side symmetry** — an edge visible from `src` is visible from `dst` (or the
   asymmetry is declared); divergent decay per row is not a phantom.
3. **Extraction-dependent signal** — A/B separates "no edges" from "edges present but
   unhelpful"; a weight cannot be live without its signal.
4. **Homogeneous-stream growth** — a declared rate/quality gate bounds edge creation (blacklist
   excluded).
5. **Causal from weak ordering** — Δt=0 / clock skew cannot invert cause; ties are disclosed.
6. **Attempts ≠ rows** — counters count admitted rows only.
7. **Transfer asymmetry** — a transferred edge keeps or explicitly drops itself, never silently
   reverts to `associated_with` filtering.
8. **Read discipline (9.1.8)** — traversal/reads take no locks and mutate nothing durable.

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| R (A3) as the relation-ordering path | ordering flips (C2) | flat strata | RE-ENTERS |
| Edge presence vs extraction off | entity/graph couplings measured | coupling weights must not stay live with no signal | EFFECTFUL |
| Decay/prune (if ever admitted) | survival distribution | distribution shift | PERSISTENT |
| Manifest-rule trial (Hebbian) | must change a measured outcome | no change = decoration | RE-ENTERS |

No inert passengers: an edge kind with no operational meaning fails admission.

---

## 5. Acceptance + owner

Wrapper-side:

1. **C5 extension** — kind/direction/provenance round-trip across processes.
2. **Direction registration** — fixture flips register.
3. **No hidden coupling** — ordering reconstructible from journal (B1 discipline).
4. **Counts** — generated from admitted rows; attempts excluded.
5. **Manifest gate** — any dynamics import carries ancestor · wire · acceptance · owner +
   promotion policy; otherwise refused.

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + wired adversarial cases + demonstrated ablation (where implemented) +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W2_SPEC_01_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
