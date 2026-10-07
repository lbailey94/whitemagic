# Phase 4 — Wave plan (with DO_NOT_MIGRATE appendix)

**Status: plan · 2026-09-17 · authorized by the frozen nucleus** (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`, receipt `receipts/NUCLEUS_FREEZE_2026-09-17.md`). Read-only planning: assigns no
new verdicts, changes no gates, authorizes no code by itself. Each migration executes only under
its stated gate with its own frozen spec + receipts.

**Joins:** Track A (`PHASE4_GEN2_DELTA.md` — 9.1.8 capability source; control stays 9.1.7) ·
Track B (`PHASE4_GEN1_TREE.md` — wave taxonomy + extracted rows) · evidence in `docs/findings/`
(W1–W3 + W0 intermission) · corrections in `PHASE4_ERRATA.md` · methods in
`WAVE_EXTRACTION_PROTOCOL.md`.

---

## 0. Rules of engagement

1. **Gen1/Gen2 provide capabilities and evidence, not architecture** (compile-pass receipt §6).
2. **The nucleus is the floor and the ceiling:** nothing enters, replaces, or shadows N1–N5;
   C1 stays a declared slot; Part-3 statutes may gain versions, never lose their versioning.
3. **Every migration carries:** ancestor · wire · acceptance · owner, plus a **frozen
   behavioral spec**, **adversarial cases** (9.1.7 audit fix list + 9.1.8 additions), and an
   **ablation design with behavioral teeth** (criteria §2a:3).
4. **Evidence levels per claim** (protocol §3); **classify by function, never by name**;
   **counts generated, never narrated** (protocol §5).
5. **Nothing resurrected by narrative**; WEAK stays WEAK; rejected stays rejected absent a new
   registration + fresh holdout + ledger action.
6. **The 9.1.7 control is never re-baselined**; capability dispositions cite 9.1.8 (delta §0).

## 1. Wave map

| Wave | Content | Gate | State |
|---|---|---|---|
| **1 — Surfaces** | store/ingest · retrieval/ranking · disclosure · revisions · sessions/continuity · coordination · claims · galaxies · compartments | nucleus freeze (**open**) + per-family spec | **ready to spec** |
| **2 — Native cognitive** | relations/associations edges · retention/lifecycle link · currentness strata · dream/consolidation half · recipe-layer candidate · RSI-over-journal · self-model/inspect | freeze + per-mechanism spec | spec next |
| **3 — Lenses** | S stays as frozen; future projections only by registration | new registration + fresh holdout | closed for new work |
| **4 — Strange Gen1** | constellations/emergence · Geneseed · simulation/imagination · field dynamics | manifest rule (+ selection demonstrated for Geneseed) | manifest-gated |
| **5 — Hard remainder** | mesh/agents · reflex/sensor/actuator · transports | deferred gates (two-gate; enforced boundary; own receipts) | deferred |

## 2. Wave 1 — surfaces (spec-ready)

Per-row detail lives in `docs/findings/W1_*` (+ batch 2/3 rows); divergences from the Gen2 map
are listed in `PHASE4_WAVE1_FINDINGS.md` §"Migration-spec divergences". Owners: **unset —
operator assigns per spec session.**

| Row | Disposition | Wire (Gen3 expression) | Acceptance highlights | Divergence / caution |
|---|---|---|---|---|
| Durable store + ingestion | compile | `remember` contract + journal refusals; **exact-hash gate candidate**; near-dup only with declared battery; quarantine-not-purge | round-trip canary (frozen C5) + duplicate-refusal ablation; journal `duplicate_exact` vocabulary **owned by the spec** (Gen2 dedup is a non-journaled short-circuit — say which side discloses) | W1 §divergences 1; Charter §3.2 |
| Retrieval & ranking | compile (earned subset only) | `recall` + R/strata; **no Gen2 planners imported** (behavior under test) | earned-tier ordering ablation (sweep on/off; C2 template); disclosure fields per result | no planner imports; lexical–semantic design stays measured |
| Evidence disclosure | compile (contract) | declared floors + explicit `insufficient_evidence`; provenance chains | provenance-completeness canary (C4); **no swept thresholds** adversarial case | v26 `abstention_gate` existed → transformed (E4 errata) |
| Revisions/supersession | compile (already native R) | `supersedes` relation + structural strata + provenance | direction-aware proposal scoring; strata ordering ablation (C2) | **Gen2 has no first-class supersedes relation** — do not claim Gen2 agreement (W1 §3) |
| Sessions & continuity | split: link (storage) + compile (ops) | records + relations; continuity = `recall`/`think` over the record layer | lossless replay shape; no payload-less shells (W0 finding) | checkpoint lives in `session.rs`, not `session_ops.rs` (W1 §2); adopt `checkpoint_nodiscovery` rhythm |
| Coordination | link | statutes + journal; lease ledger link | two-writer case; read-only discipline (snapshot reads); **typed effects + always-releasable asymmetry** (delta §3.3) | link must not bypass typed effects; v26 advisory-only locks excluded |
| Claims / belief class | compile | belief-class records + resolution events; calibration = **statutory statistic** | resolution-record completeness; no destructive seed sync; declared battery only | v26 seed sync was destructive + degenerate (W1 row) |
| Galaxies / compartments | compile + link | scope labels/views over one store; compartments = statutes + scopes | scope-label behavior; Fail-open-on-engine-error case named | cap-20 bypass + `_meta` membership-vs-authz UNVERIFIED (W1 §4) |

**Wave-1 exit criteria:** each row has a frozen spec (ancestor · wire · acceptance · owner),
adversarial cases wired, ablation designed and, where implemented, demonstrated; journal events
declared for rungs 4–8 (protocol §1); receipts per row; **no row ships with an inert acceptance
test.**

## 3. Wave 2 — native cognitive

| Row | Disposition | Wire | Acceptance / ablation | Caution |
|---|---|---|---|---|
| Relations/associations (edges) | compile (edges); dynamics **parked** | typed edges `(w,s,c,t)` already first-class | edge round-trip (C5); promotion-policy manifest required before any Hebbian | v26 typing never persisted; Gen2's Hebbian lives in mechanism, absent from serving path (W2 §1) |
| Retention / lifecycle | link (Gen2) | statutory selection; fixed `persistent` in Gen3 until earned | retention-vs-lifecycle **named separately**; delete path (`forget`) is a different organ | v26 sweep never armed; all-zero "success" (W2 §2) |
| Currentness strata | compile (native) | structural strata 0/1/2 (already frozen, N2) | strata ordering ablation; **runtime behavior, not env knobs** | Gen2's strata sit behind env knobs (W2 §6) |
| Dream / consolidation half | compile | selection/lifecycle pass over the journal; **13 vs 12 phases never inherited** | consolidation pass changes measured ordering; CITTA label artifact not a capability | Gen2 engines/reports are catalog names, not execution (W2 §3) |
| Recipe layer (candidate) | compile candidate | operator vocabulary + recipe runtime; **anti-bloat law** | recipe replay produces journal-visible effects; compositions enter as recipes, not classes | SkillForge metadata is not evidence (E16) |
| RSI over journal | link | `think` over journal; proposal ≠ verification | maker ≠ checker; independent resolution verification | Gen2 RSI caller-asserted + curated-excluded; v26 self-cert (W2 §4) |
| Self-model / inspect | link + compile (inspect) | tier-map/selection explanations (N3) | inspect answers tier/authority/explanation per state | "calibration" names four universes — spec must name one (W2 §5) |

## 4. Wave 3 — lenses

- **S is already frozen** (C1: declared optional slot; `count < 2` scoped activation; 0.01
  floor permanently outside; ≥2 boundary an open question with a named gate).
- **No inherit-able lens behavior exists:** v26's coordinate channel was a silent always-on
  stage; Gen2 coords are hash-derived/diagnostic; `put_semantic` has zero production callers
  (W3_lens_projection.md). Any future projection enters only via **new registration + fresh holdout**
  (criteria §3.2/§5; multi-view notes are the map, not a plan).
- Projection-agreement stays **dormant** (thread 4); TIE stays parked (thread 2).

## 5. Wave 4 — strange Gen1 (manifest-gated)

| Row | Manifest so far (ancestor · wire · acceptance · owner) | Gate |
|---|---|---|
| Constellations/emergence | v26 emergence organs (zombie + hardcoded/random + real SQL detector, tool-invisible) · topology over relations · H8 six-condition test vs ablation · owner unset | manifest rule |
| Geneseed / inheritance | v26 `GeneseedVault` forker + V9.1 typed-parent-edge design (zero code in both gens) · typed parent edges + selection events · acceptance after selection demonstrated · owner unset | selection first |
| Simulation / imagination | Gen1 TZPF scorecard + self-scored rollout; Gen2 four disjoint organs · `simulated`-domain records + hypotheses + rollout over admitted evidence · domain canaries (**already law**) + outcome improvement vs ablation · owner unset | manifest rule |
| Field dynamics | v26 read-side channel live but no measured win; Gen2 decay never ticks · activation/decay field + operational regime parameter · **a task where propagation beats retrieval** · owner unset | that task |

## 6. Wave 5 — hard remainder (deferred)

- **Mesh/agents:** gate 1 (transport validation) has a reference implementation (9.1.8 signed
  beacons; delta §2.2); **gate 2 is authority-only**; unsigned RPC frames and the missing
  egress/consent hook must be resolved **before any `communicate` surface** (see the operator
  handoff `WHITEMAGIC_SAFETY_MASK_EGRESS_HANDOFF_2026-09-17.md`). Iceoryx2/any transport
  re-adoption gets its own manifest receipt.
- **Reflex/sensor/actuator:** PRESERVE→link; the link must **enforce, not document**, its
  boundary — the shipped Gen2 mask is inert (permissive = `SAFETY_ALLOW_ALL`); hard real-time
  stays outside cognition (CONV §2 L2627; MandalaOS boundary).
- **Retirements stay retired:** identity practice forms, monetary economy, `bagua.dispatch`,
  `council.deliberate` (E13/E24 rulings).

## 7. Cross-cutting spec template

Every migration spec (one per capability) must contain, in order:

1. **Frozen behavioral spec** — observable behavior, inputs/outputs, journal events, statutory
   parameters named (Tier-2), nothing benchmark-derived.
2. **Selection history** — ancestor (file/symbol) · observed behavior · selection fate ·
   evidence level per statement (protocol §3).
3. **Adversarial cases** — from the **9.1.7 audit fix list** (`WMv9/docs/V9_1_7_SCOPE_2026-09-15.md`
   §Tier 1: installer sentinel, atomic-vs-partial success, session write-time indexing, etc.)
   **plus the 9.1.8 additions** (delta §3.2: strict-mode refusal, no-subprocess discovery,
   `checkpoint_nodiscovery` semantics, signed-only beacon ingest, read-only discipline,
   starvation-vs-refusal distinction).
4. **Ablation** — disabling the mechanism changes a measured outcome; journal is the
   instrument (rungs 4–8, protocol §1); no inert passengers.
5. **Acceptance + owner** — wrapper-side evaluation; owner named by the operator at spec time.

## 8. DO_NOT_MIGRATE appendix

Reason classes per protocol §7. Every Phase-4 exclusion names its reason from this table.

| # | Item | Gen | Reason class | Evidence | Revisit condition |
|---|---|---|---|---|---|
| 1 | v26 typed-link persistence semantics (kind/direction erased at save) | 1 | cosmetic ontology | W2_associations_relations.md | none — Gen3 edges round-trip (C5) |
| 2 | v26 Hebbian dynamics (zero callers) | 1 | unwired | W2_associations_relations.md | manifest rule (promotion policy) |
| 3 | v26 retention sweep (never armed; all-zero "success"; hard edge deletes) | 1 | inert persistence | W2_retention_lifecycle.md | none — Gen2 link stays |
| 4 | v26 emergence organs (hardcoded patterns, random novelty; 284 runs/0 output; 329-insight claim tool-invisible) | 1 | self-verifying / timeline | W2_constellations_emergence.md; errata #27 | H8 six-condition test (wave 4) |
| 5 | v26 simulation rollout (toggle-off, self-scored; possibility winners self-scored) | 1 | self-verifying | W3_simulation_imagination.md | manifest rule + outcome-vs-ablation |
| 6 | "TZPF engine" (it is a scorecard) | 1 | name collision | W3_simulation_imagination.md | — |
| 7 | v26 SkillForge traces (33 skills, 4-verb vocabulary, write-only replay) | 1 | unwired / write-only | W2_engines_recipes.md | operator runtime (wave 2 candidate) |
| 8 | v26 RSI (proposer = verifier; success = disappearance; auto-fix dead) | 1 | self-verifying | W2_rsi_selfmodel.md | maker ≠ checker + independent verification |
| 9 | v26 calibration seed set (all-validated; destructive YAML sync) | 1 | self-verifying + destructive | W1_claims_prescience.md | declared battery; no destructive sync |
| 10 | v26 abstention threshold 0.50 (sweep-derived) | 1 | benchmark-derived threshold | errata #4 | declared floors only (already law) |
| 11 | v26 advisory locks / lock-free `shared_context` (list-under-mutation) | 1 | unwired / unsafe | W1_coordination.md | Gen3 leases + snapshot reads (wave 1) |
| 12 | v26 mesh organs (Go aux without binary; Python test-only; iceoryx2 without receiver) | 1 | unwired | W3_mesh_transport.md | transport adoption = own manifest receipt |
| 13 | Clone-swarm throughput claims (comment-seeded 500k; measured ~97/s) | 1 | timeline/comment artifact | W3_mesh_transport.md | measured evidence only |
| 14 | Identity practice forms (smarana practice; hermit) | 1 | name collision / retire ruling | E13 | homecoming gate |
| 15 | Monetary economy (XRP rails; test data) | 1 | timeline artifact / retire ruling | LINEAGE economy ruling; errata #29 | ruling's revisit condition |
| 16 | `bagua.dispatch` (symbolic router) | 1 | constitutional (§3.10) | E24 | never |
| 17 | `council.deliberate` (archetypal harness) | 1 | lineage ruling | E24 | declared conditions/poses only |
| 18 | Reflex safety mask as shipped (permissive; actuation unmasked; e-stop inconsistency; in-memory rules) | 2 | **unsafe boundary** | W3_reflex_boundary.md; errata #20 | **enforce before any link** (handoff note A) |
| 19 | Unsigned RPC frames + missing egress/consent hook | 2 | **unsafe boundary** | W3_mesh_transport.md; errata §F-19 note | handshake/frames + journaled crossing (handoff note B) |
| 20 | `tick_decay` 300 s "decay" (never called; saturations) | 2 | unwired / inert | W3_field_activation.md; errata #14 | propagation-beats-retrieval task |
| 21 | `LifecycleManager::forget` delete path (no callers) | 2 | unwired | W2_retention_lifecycle.md | retention≠lifecycle naming; never silently deleted |
| 22 | Stub world-model default under `imagine.*` | 2 | stub / smoke | W3_simulation_imagination.md | real model + outcome evidence |
| 23 | Curated-excluded, caller-asserted RSI resolution | 2 | self-verifying | W2_rsi_selfmodel.md | independent verification |
| 24 | "Calibration" used across four disjoint universes | 2 | name collision | W2_rsi_selfmodel.md (calibration universes) | spec names the universe |
| 25 | Containment harness (simulation, not wired) | 2 | unwired | W3_mesh_transport.md | wire it or don't cite it |
| 26 | Currentness strata behind env knobs | 2 | configuration artifact | W2 §6 | runtime behavior in the spec |
| 27 | Rejected primitives: T8 bridge · R1 pair gating · dispersion · 0.01 floor | both | rejected (Phase 2/3) | consolidation §4; NUCLEUS §3.1 | new registration + fresh holdout + ledger |
| 28 | Open boundaries: ≥2 insuff. · TIE · projection-agreement · multi-view · field · recipes · Geneseed · representation stack | — | named gates | NUCLEUS §3.3/S4 | per-item gate |
| 29 | Timeline artifacts (imports/backfills; backdated 2024 seed; empty handoff shells) | 1 | timeline artifact | W0; errata #21/#24/#30 | provenance rule |
| 30 | Open epistemic debts (predictive-cache 91%; trust-stamps; telemetry dedup; Q11; 3 orphan fractions) | 2 | carried, UNVERIFIED | matrix §4.8 | clear before any spec cites them as measured |

## 9. Execution order & first units

1. **Wave 1 spec batch A:** durable store + ingestion gate · evidence disclosure · revisions/
   supersession (smallest specs; the round-trip and disclosure canaries already exist).
2. **Wave 1 spec batch B:** retrieval/ranking · sessions/continuity · coordination · claims ·
   galaxies/compartments.
3. **Wave 2** per the table; recipe layer only after its anti-bloat review.
4. Owner assignment and spec freeze happen **per unit** (operator act; receipts in `receipts/`).
5. The 9.1.8 deploy (operator-side) also lands `checkpoint_nodiscovery` adoption; no migration
   depends on it.

## 10. What this plan is not

No code, no new thresholds, no primitive additions, no verdict changes, no resurrection, no
Phase-4 scheduling beyond the wave order above. The frozen 9.1.7 control remains the reference
animal; the frozen nucleus remains the floor.
