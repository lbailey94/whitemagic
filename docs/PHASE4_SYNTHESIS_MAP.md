# Phase 4 — Synthesis map (Gen1/Gen2 organs → Gen3 expression)

**Status:** study · 2026-09-17 · compiled against WMgen3 tip `77c812c`; source tree clean before
creation of this untracked synthesis document (session `6c634017`) · **read-only synthesis;
assigns no verdicts, changes no gates, authorizes no migration, writes no code.** The code
boundary stays closed until the acceptance campaign finishes.

**Joins:** `PHASE4_WAVE_PLAN.md` (rows + gates) · `PHASE4_GEN1_TREE.md` (Track B) ·
`PHASE4_GEN2_DELTA.md` (Track A) · `PHASE4_GEN2_FOLDIN.md` (9.1.8 fold-in) ·
`docs/findings/W0_*`–`W3_*` (the extraction) · `PHASE4_ERRATA.md` · `WAVE_EXTRACTION_PROTOCOL.md`
(method) · `NUCLEUS.md` (primitive ceiling) · `docs/specs/` (frozen per-row specs).

**Why this exists (external review, 2026-09-17):** the extraction answered *what each generation
was*; the wave plan assigned *who migrates what*; this map answers the function-level question
queued for it: for every organ found, what does Gen3 actually require — **a primitive**, an
**invariant**, or a **10-line replacement**? Where the answer is a replacement, the organ needs no
migration at all; the capability compiles as a short composition over existing primitives.

**Reading rules (protocol §3/§5):** classify by function, never by name · every row carries its
evidence file · counts are generated, never narrated · WEAK stays WEAK · rejected primitives and
9.1.7-control wording are untouched · nothing here resurrects a disposition.

---

## 1. The Gen3 side of the join (what there is to compile into)

The primitive basis is frozen (`NUCLEUS.md`); this map may not add to it. Verbatim inventory:

| Element | State | Source |
|---|---|---|
| Verbs `remember · recall · think · inspect` | Phase-1 substrate, closure-tested | `PHASE1_CONTRACTS.md`; closure canaries C1/C4 |
| **N1** durable records + provenance chains | admitted | `NUCLEUS.md` §2.1 |
| **N2** supersedes relation + currentness strata | admitted | §2.1; `PHASE1_CONTRACTS.md` §1.2/§2.3 |
| **N3** selection explanations | admitted | §2.1 |
| **N4** journal-as-evidence | admitted | §2.1; schema in `PREREG_FREEZE_2026-09-16.md` §2 |
| **N5** audit discipline | admitted | §2.1 |
| **C1** — S as declared optional lens (`count < 2`, gate-scoped) | slot, scoped | §2.2 |
| Relation `e=(w,s,c,t)` + kind + `state` | substrate shape | `PHASE1_CONTRACTS.md` §1.2 |
| Lifecycle `transient → candidate → persistent → cold` | substrate shape | §1.3 |
| Scope labels (views over one store) | compile side accepted | `impl_b5_2026-09-17` |
| Statutory baseline + switches | Tier-2, versioned | `NUCLEUS.md` §3 |

**Acceptance-campaign state at writing** (does not change any row's destination — only its
status): **exited** A1, A2, A3, B1 (`f6132f3`; four `W1_ROW_EXIT_*` receipts) · **landed
acceptance**: B5 (compile/link side), W2_01 (edges), W2_03 (no-knob strata), W2_07 (inspect) ·
**queued construction units**: B2/B3/B4 boundary rows, B5 recall-side scope view (registration
first — changes the recall surface), W2_02, W2_04 · **gated**: W2_05 (anti-bloat review), W2_06
(maker ≠ checker) · spec headers B1/W2_03/W2_07 still read "DRAFT"; **freeze receipts are
canonical** (errata §H #33).

## 2. Disposition vocabulary (this document only)

The review asked for three answers; two boundary states complete the accounting. No new
disposition class is created for the program — classes below map onto the wave plan's language.

| Class | Means |
|---|---|
| **PRIMITIVE** | the function needs the nucleus basis as-is (N1–N5 / C1) — no new mechanism |
| **INVARIANT** | not carried as mechanism; its lesson is already Part-1 law |
| **RECIPE** | *10-line replacement*: composes from verbs + relations + journal over existing primitives; anti-bloat law forbids a module for it |
| **LINK** | stays Gen2-side for alpha; Gen3 states the boundary (PRESERVE→link rows) |
| **GATED** | waits on its named gate (wave-3/4/5 EXPERIMENT rows; missing-primitive candidates) |
| **EXCLUDED** | DO_NOT_MIGRATE reason class (wave plan §8 appendix) |

A row may carry two classes (e.g. `RECIPE · LINK`) when an organ splits by function.

## 3. Homology table — one function, three generations

Gen1 = `og_whitemagic` @ `v26.0.3` (`4d5be091`); Gen2 = WMv9 @ `9.1.8`. Evidence cites the
findings file that carries the source-level proof.

| # | Function family | Gen1 organ (function, not name) | Gen2 organ | Gen3 expression | Class |
|---|---|---|---|---|---|
| 1 | Store + ingestion | 36 sqlite3-importing modules; dedup as cleanup campaign (37.2 % migration dup) (`W1_retrieval.md`, `W1_galaxies_compartments.md`) | LMDB + `write_gate` (junk→dedup→plausibility) + per-file `ingest_ledger.jsonl`; non-journaled dup short-circuit (`W1_gen2_source_map.md` §1) | `remember` + A1 exact-hash gate; noise = refuse-with-journal rev 2; disclosure side owned by the spec | **PRIMITIVE** (exited) |
| 2 | Retrieval + ranking | 8-stage planner, RRF k=60, multiplicative rerank, CE 0.6/0.4, tag-Jaccard 0.85, qFHRR 8-bit prefilter (`W1_retrieval.md`) | BM25 .5 / vector .3 / importance .2; post-fusion knobs off (`W1_gen2_source_map.md` §2) | `recall` + N2 ordering; no planners imported; B1 behavioral 0-diff on a gate-neutralized corpus | **PRIMITIVE** (exited) |
| 3 | Supersession + currentness | `temporal_kg` fact table + FAMA ±scores; extraction-dependent (`PHASE4_WAVE1_FINDINGS.md` row 3; `W1_retrieval.md` FAMA) | hash-chain revisions + episodic change markers; `ValidityState` swept only in dream behind env knobs (`W2_gen2_source_map.md` §2) | relation kind `supersedes` + structural strata (N2); A3 exit on declared property; W2_03 no-knob strata landed | **PRIMITIVE** |
| 4 | Evidence disclosure | `abstention_gate.py` 0.50, sweep-derived, opt-in (`W1_retrieval.md`) | declared floors + `insufficient_evidence` + bundles (`W1_gen2_source_map.md` §2) | A2: one reason vocabulary, floors fail-closed, no swept thresholds | **INVARIANT** (truthful surfaces) + **PRIMITIVE** (exited) |
| 5 | Sessions + continuity | machine turn log bypassing gates; 24/24 handoffs empty shells; dormant `continuity/`; sleep consolidation to codex (`W1_sessions_continuity.md`, `W0_handoffs_sessions.md`) | `session.*` typed turns; `checkpoint` + `checkpoint_nodiscovery` (caller fields only); time-based prior-session resolution (`W1_gen2_source_map.md` §4) | records + relations (link); continuity = `recall` + `think` over the record layer (E11 anti-bloat); payload-less handoffs are not inheritance | **RECIPE · LINK** |
| 6 | Coordination | advisory `ResourceManager` (nothing consults it); `shared_context.json` lost updates; single-slot handoff (`W1_coordination.md`) | lease ledger (intent + TTL, exact-owner release); `snapshot_readonly` reads; typed effects; strict refuses acquisition, always admits release (`W1_gen2_source_map.md` §5) | statutes + journal; link to the lease ledger; no mutable-JSON board; reads never mutate | **LINK** |
| 7 | Claims + calibration | `prescience_claims.yaml` + SQLite mirror; destructive seed sync; all-validated seed = degenerate BS; Brier/Murphy/ECCE shipped (`W1_claims_prescience.md`) | claims ledger; raw confidence never edited; calibration over resolved only; Wilson + empirical-Bayes; "calibration" = four universes (`W1_gen2_source_map.md` §6, `W2_gen2_source_map.md` §7) | belief-class records + resolution events; calibration = **statutory statistic**; each statement names its universe | **PRIMITIVE** (B4 boundary queued) |
| 8 | Galaxies | per-name SQLite DBs, no cap; taxonomy advisory-only; class filter partial (`W1_galaxies_compartments.md`) | enum 16 + `DynamicGalaxyRegistry` cap 20 (physical bypass UNVERIFIED); `can_access_galaxy` fails closed (`W1_gen2_source_map.md` §7) | scope labels as **views over one store**; compile/link side accepted; recall-side view registration queued | **PRIMITIVE** (B5) |
| 9 | Compartments | shelter templates with silent tier degradation; capability typos dropped; Dharma fail-open (`W1_galaxies_compartments.md`) | Mandala tiers (research/sandbox/production/secure); `_meta.compartment` = membership ≠ authz (`W1_gen2_source_map.md` §7) | statutes + scopes; fail-closed unknowns; effective grants reported, never template labels | **LINK** |
| 10 | Relations / edges | typing never survived a save; Hebbian dormant; live dynamics = decay+prune (anti-Hebbian) (`W2_associations_relations.md`) | typed edges persist; Hebbian mechanism live in `wm-memory`, serving path default-off (`W2_gen2_source_map.md` §1) | `e=(w,s,c,t)` + kind + provenance; W2_01 edges acceptance landed; dynamics parked behind the manifest rule | **PRIMITIVE · GATED** |
| 11 | Retention / lifecycle | 5-signal engine, never armed; persist path broken → all-zero "success"; edges hard-deleted (`W2_retention_lifecycle.md`) | `RetentionEngine` decay-only, dream-wired; `Lifecycle::forget` delete-capable, **no callers outside `wm-memory`** (spot-verified `lifecycle.rs:156`); cold rotation propose/thaw (`W2_gen2_source_map.md` §2) | link (fix `persistent` until earned); proposal-only prunes; rotation not deletion; W2_02 spec freeze is the queued unit | **LINK · INVARIANT** |
| 12 | Dream / consolidation | 13-phase dream that wrote (triage DELETEs, edge halving); `CycleEngine` in-memory; 284 zero-output dreams (`W2_citta_dream_cycles.md`, `W0_state_ledgers.md`) | 12-phase daemon dream; learned phase selection experimental; "engines" = catalogs/counters (`W2_gen2_source_map.md` §3) | selection/lifecycle pass over the journal, journal-attested, measured ordering delta; phase sets never inherited; W2_04 spec freeze is the queued unit | **RECIPE** (pass = `think` over journal) · **GATED** (spec) |
| 13 | Recipes / engines | 28-slot lattice = naming map; SkillForge persisted 33 skills, 4-verb, write-only replay (`W2_engines_recipes.md`) | 28 catalog entries; `skill.invoke` = lookup/echo; no compiler (`W2_gen2_source_map.md` §5) | operator vocabulary + recipe runtime candidate; **anti-bloat law** — compositions enter as recipes, not classes; W2_05 gated on its anti-bloat review | **GATED** |
| 14 | RSI / friction | `feedback.db` 4.0 % coverage; success 2/36 (one event twice); maker = checker; auto-fix structurally dead (`W2_rsi_selfmodel.md`) | friction ledger + review-gated proposals; resolutions **caller-asserted**, curated-excluded (`W2_gen2_source_map.md` §6) | `think` over journal + proposal records; success only via a witness independent of the proposing organ; W2_06 gated | **GATED · INVARIANT** (audit) |
| 15 | Self-model / inspect | in-memory deques, unfed; self-scored possibility winners overwrite boot constants (`W2_rsi_selfmodel.md`) | `SelfModel` + conformal store + env-gated recall conformal; recall conformal refuses honestly when unconfigured (`W2_gen2_source_map.md` §7) | `inspect` (tier map + explanations, read-only); calibration only as statutory statistic; W2_07 acceptance landed | **RECIPE** (inspect answers) |
| 16 | Lenses / projection | 5D spatial stage always-on (weight 0.5), silent skips; query coords bypass embeddings; HRR write-side unconsumed (`W3_lens_projection.md`, `W1_retrieval.md`) | coords hash-derived, self-documented "semantically meaningless"; `put_semantic` zero production callers; serving path has no lens (`W3_lens_projection.md`) | C1 slot as-is; any future lens = new registration + fresh holdout; projection-agreement stays dormant | **PRIMITIVE** (C1) · **GATED** (wave 3) |
| 17 | Emergence / constellations | three organs (zombie 284/0; hardcoded+random; real SQL detector, 329 rows); single-valued memberships, no prune (`W2_constellations_emergence.md`) | `constellation.detect/list` (5D clustering); topology comparison non-shipped | EXPERIMENT: topology over relations + H8 six-condition acceptance vs ablation; no cluster boosts | **GATED** (H8) |
| 18 | Geneseed / inheritance | git miner + `GeneseedVault` template forker (name collision); no memory lineage (`W3_geneseed.md`) | miner port, routes registered **undeclared**; Q04 disposition: retire code | EXPERIMENT: typed parent edges + selection events; acyclicity rule owed; gate = selection demonstrated | **GATED** (selection) |
| 19 | Simulation / imagination | TZPF = scorecard; rollout toggle-off, self-scored (`W3_simulation_imagination.md`) | four disjoint organs; stub world-model default; dream Oracle hypothesis replay (`W3_simulation_imagination.md`) | law = `simulated` domain tagging (Closure 2) — **INVARIANT**; rollout = E19 acceptance (domain canaries + outcome vs ablation) | **INVARIANT · GATED** |
| 20 | Field / activation / decay | read-side spreading activation **live** in the default planner, no measured win; write-back tool-only (`W3_field_activation.md`) | four offline organs; garden 300 s decay declared, `tick_decay` never called (spot-verified: 1 definition, 0 callers); saturations | missing-primitive candidate; gate = a task where propagation beats retrieval; no temperature parameter until then | **GATED** (missing primitive) |
| 21 | Mesh / transport | three unwired systems (Go aux, Python test-only, iceoryx2 no receiver); clone swarm = local search (`W3_mesh_transport.md`) | `wm-sangha` live opt-in; gate 1 real (signed beacons); gate 2 authority-only; RPC frames unsigned; no egress/consent hook (`W3_mesh_transport.md`) | deferred; two-gate boundary + egress record before any `communicate`; transport adoption = own manifest receipt | **GATED** |
| 22 | Reflex / sensor / actuator | dormant sensing only; no actuation (`W3_reflex_boundary.md`) | live sysfs bus + unreviewed Sensorimotor cycle; safety mask **inert** (`permissive()` = `SAFETY_ALLOW_ALL`, spot-verified); e-stop refusable by mask | deferred; any link must **enforce, not document** its boundary; hard real-time stays outside cognition | **GATED · EXCLUDED** (as-shipped mask) |
| 23 | Identity (practice forms) | smarana practice, hermit; practice content absent from stores (`W0_earliest_memories.md`) | — | E13 ruling: RETIRE; provenance duty already carried by N1 | **EXCLUDED** |
| 24 | Monetary economy | XRP rails; marketplace fixtures (`W0_state_ledgers.md`) | — | economy ruling upheld: monetary RETIRE; shipped `bounty.*` ledger preserved as product | **EXCLUDED** |
| 25 | Symbolic dispatch | `bagua`, council harness archetypes | `bagua.dispatch`, `council.deliberate` retired (`PHASE4_WAVE_PLAN.md` §5) | Charter §3.10 — symbols render, never dispatch | **EXCLUDED** |

## 4. The 10-line composition/replacement ledger

"10-line replacement" is a discipline, not a line count: if the behavior is expressible as a
short composition over verbs, records, relations, and the journal, then **no module, class, or
migration is owed** — the anti-bloat law (`DESIGN_CANON.md` §7/§13) is the judge. The falsifier
column states what would instead force a registration for a primitive. An entry here is not
necessarily classed RECIPE in §3; this ledger records places where an inherited organ does not
justify migration as a standalone module.

| Capability | Composition (contract-level, not code) | Falsifier → primitive path |
|---|---|---|
| Continuity / digest | `recall` over session records + `think` digest = one pass (E11) | digest cannot be reconstructed from journaled records → B2 spec review |
| Checkpoint / handoff | record write with caller-supplied fields + provenance (no discovery — adopt `checkpoint_nodiscovery` semantics) | a field that the record model cannot carry |
| Recall-side scope view | label filter over one store on the recall path (registration + 0-diff regression first — **next unit**) | labels change ordering beyond filtering → new registration |
| Retention decay | `think` pass over records: decay/promotion per statutory thresholds, journaled; no delete | acceptance needs deletion semantics → never (invariant 2); otherwise W2_02 spec |
| Consolidation pass | same pass class, measured ordering delta, journal-attested | a pass that cannot change a measured ordering is decoration (W2_04 adversarial case 7) |
| Claims resolution | belief-class record + resolution event + statutory calibration statistic | a resolution witness the journal cannot express |
| Inspect answers | journal read + tier map (read-only) | an explanation not derivable from N3/N4 events |
| Disclosure | provenance chain + declared floors (already A2) | a floor that must be learned rather than declared (banned as swept) |
| Coordination read path | journal + lease-ledger read; no board | a lock semantic the ledger lacks |
| Exact-dup gate | A1 gate (already landed); noise table rev 2 | a near-dup policy that needs a declared battery (registration) |

## 5. Missing-primitive candidates (named, gated — unchanged)

Only four survive the whole extraction, each with its gate untouched by this map:

1. **Activation/decay field** with an operational regime parameter — gate: a task where
   propagation beats retrieval (`NUCLEUS.md` §2.4; `W3_field_activation.md` §"candidate").
2. **Operator vocabulary + recipe runtime** — attaches to the anti-bloat review; SkillForge
   metadata is not evidence (E16; W2_05 gate).
3. **Selection policy layer** (Pareto/statutory + exploration budget) — Phase-3 question, no
   mechanism exercised (`THEORY_MECHANISM_MAP.md` §3.3).
4. **Credit assignment** (traceable participation, delayed horizon) — ratified as the causal
   attribution gate (Charter §6); no mechanism exercised; co-occurrence permanently ineligible.

Everything else the extraction found resolves to §3 as PRIMITIVE/INVARIANT/RECIPE/LINK/GATED/
EXCLUDED — i.e. **no further primitive demand has been identified in the extracted and
spot-verified Gen1/Gen2 corpus**.

## 6. Coverage accounting (generated)

Counts generated from the §3 class column (command as run):
`awk -F'|' '/^\| [0-9]+ \|/ {print $(NF-1)}' docs/PHASE4_SYNTHESIS_MAP.md | rg -o 'PRIMITIVE|INVARIANT|RECIPE|LINK|GATED|EXCLUDED' | sort | uniq -c`

| Class token | Occurrences |
|---|---|
| PRIMITIVE | 8 |
| INVARIANT | 4 |
| RECIPE | 3 |
| LINK | 4 |
| GATED | 11 |
| EXCLUDED | 4 |

Family rows: 25 (every row carries at least one class; 9 rows carry two → 34 token occurrences).
10-line composition ledger entries: 10. Missing-primitive candidates: 4.
DO_NOT_MIGRATE appendix items: 30, unchanged (`PHASE4_WAVE_PLAN.md` §8) — this map adds no
exclusion and removes none. Ledger: 8 claims, unchanged; WEAK stays WEAK.

## 7. What this map does not do — and the next units it hands off

- No code, no new threshold, no verdict/claim/gate movement, no resurrection.
- The **B5 recall-side scope view** is the next construction unit: registration first
  (view-not-boundary), then a fresh 0-diff regression (it changes the recall surface).
- **W2_02 / W2_04** are the next spec freezes (owner assignment is an operator act), then their
  acceptance slices; W2_05/W2_06 stay gated.
- Ops leftovers and WMv9-tree fixes stay in their lanes: stress fixtures wire with B3/W2_02
  slices; JSON write-through fixes are **Gen2-lane** (never mixed into Gen3 commits).
- Amendment rule: additive errata only; a revision lands as a new commit with its own receipt.
  A row that turns out wrong is corrected by errata, not edited silently.

**Explicit non-claims:** nothing here re-litigates a falsified claim (claims 0000–0007 stand as
recorded); the 9.1.7 control is never re-baselined; counts are generated, never narrated; rows
citing UNVERIFIED items carry that label in their source findings files.
