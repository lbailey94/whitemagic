# Phase 4 — Track B: Gen1 v26 tree build (first wave: surfaces)

**Status:** study opened · 2026-09-17 · **read-only research; assigns no verdicts, authorizes no
migration.** Wave-1/2 execution waits on the nucleus freeze (`NUCLEUS_FREEZE_CRITERIA.md`);
waves 3–5 additionally need their own registrations/holdouts. Track A (Gen2 side):
`PHASE4_GEN2_DELTA.md`; per-row extractions: `docs/findings/` (wave-1 batch complete, indexed in
`PHASE4_WAVE1_FINDINGS.md`).

Capstone deliverable: the **Phase-4 wave plan** — each migration carrying ancestor · wire ·
acceptance · owner + frozen behavioral spec + adversarial cases + ablation design.

---

## 0. Sources and rules

| Source | What it gives |
|---|---|
| `~/Desktop/WHITEMAGIC_GEN1_v26.0.3/og_whitemagic` @ `4d5be091` (tag v26.0.3) | the organism's body: package 1,669 files / 445,356 LOC (tree 2,420 py / 617,919 LOC) |
| `WHITEMAGIC_GEN1_v26_DOCS/` (166 `.md`) | what v26 said about itself (checked against behavior, never trusted alone) |
| Gen1 sessions DB (21,351 turns: CITTA 18,204 · code_change 2,593 · error 2,379 · decision 326 · breakthrough 8) | the fossil record — but **source-dated**: ~10.6 % imports; lived era ≈ late May → Aug 2 (`PHASE4_WAVE0_SESSIONS.md`) |
| `LINEAGE_LEDGER.md` · `CODE_ARCHAEOLOGY.md` · matrix | verified skeletons (folded / partial / missing / obsolete-by-design + evidence) |

Rules: **classify by function, never by name** (homology rule, `PHYLOGENETIC_FRAMING.md` §4);
every row names ancestor (file/symbol) · observed behavior · selection fate · candidate Gen3
expression; counts generated, never narrated; nothing resurrected without the manifest rule.

## 1. Wave taxonomy (operator direction)

| Wave | Content | Gate |
|---|---|---|
| **1 — Surfaces** | client-facing capability surfaces (the verb path + links): store/ingest, retrieval, disclosure, revisions, sessions/continuity, coordination, claims, galaxies, compartments | nucleus freeze |
| **2 — Native cognitive** | substrate-native mechanisms: relations/associations, lifecycle/retention, currentness strata, consolidation passes (citta/dream half), recipe layer, RSI-over-journal, self-model/inspect | nucleus freeze + per-mechanism spec |
| **3 — Lenses** | optional projections/views: S (conditional lens, `count < 2`), future projections per the multi-view notes | new registration + fresh holdout |
| **4 — Strange Gen1** | never-fairly-tried ancestors: emergence/constellations, Geneseed/inheritance, simulation/imagination, field dynamics (candidate primitive) | manifest rule + selection demonstrated where required |
| **5 — Hard remainder** | mesh/agents (two-gate), reflex/sensor/actuator (MandalaOS boundary), transports; retirements stay retired | deferred gates |

## 2. Wave 1 — surfaces (candidate rows)

Ancestor pointers marked ✓ are verified; all rows were extracted 2026-09-17 (subagent batch 1)
— per-row detail in `docs/findings/`, errata consolidated in `PHASE4_WAVE1_FINDINGS.md`.

| Family (pass verdict) | Gen1 v26 ancestor | Observed behavior | Selection fate | Candidate Gen3 expression |
|---|---|---|---|---|
| Durable store + ingestion (CLEANLY→compile) | sqlite3-backed memory core — 36 modules import sqlite3 ✓ | 59,831 migratable rows / 35,930 distinct / **37.2 % dup because dedup was cleanup, not a gate** (`findings/W1_retrieval.md` + row 1 findings) | folded → LMDB + Tantivy + provenance | `remember` contract + journal refusals (exact-hash gate candidate) |
| Retrieval & ranking (CLEANLY→compile) | multi-stage: weighted RRF planner (k=60) → **multiplicative** reranker (entity/importance/recency/lexical/FAMA) → CE blend (0.6/0.4); qFHRR **8-bit** prefilter; dedup 0.85 = **tag-set Jaccard**; active embedder constant `bge-small-en-v1.5` (**matrix said MiniLM — corrected**) ✓ | fused, reranked, stage-order dependent under fail-soft | distilled → hybrid/episodic + disclosure | `recall` + earned ordering (R/strata); no planners imported |
| Evidence disclosure (CLEANLY→compile) | v26 `abstention_gate.py` existed (0.50, sweep-derived) → **transformed** (errata, E4) ✓ | threshold abstention, opt-in and standalone | added/transformed in Gen2 (declared floors + `insufficient_evidence`; bundles) | record provenance + selection explanations + journal |
| Revisions/supersession (CLEANLY→compile) | `temporal_kg.py` (Temporal KG, Gap C): (s,p,o,valid_from/valid_to,superseded_by) + FAMA ±scores + `extract_and_assert` ✓ | fact-graph supersession, extraction-dependent | folded; earned natively in Gen3 (R) — **same goal, different organs** | `supersedes` relation + strata + provenance |
| Sessions & continuity (split: link + compile) | `session_recorder.py:57-121` ✓ — rows are **machine-generated tool-call records** via a private backend handle (bypasses ingestion gates); ~10.6 % of the 21,351 rows are **back-filled imports** (`W0_early_sessions.md`); `current_state.py` dual-store, injected on connect; `continuity/` module **dormant** (name ≠ function) | 21,351 rows; "Total Recall" = three divergent paths; endgame shows handoffs empty + journals stubs (`W0_handoffs_sessions.md`) | folded & hardened (session.*; 9.1.8 adds `checkpoint_nodiscovery`) | records + relations (link); continuity = recall/think |
| Coordination (PRESERVE→link) | advisory-only `ResourceManager` (never consulted; silent no-op fallback); lock-free `shared_context.json`; single-slot handoff drops a second session; collective dirs `…/sangha/memory/collective/` (2026-05-29) | parallel-session interference 2026-07-16 handled narratively; `list_locks` mutated while listing (the bug 9.1.8's snapshot fixes) | added in Gen2 (leases; two-writer live-fire) | statutes + journal; link to lease ledger |
| Claims/prescience (CLEANLY→compile) | `forecasting/` + `prescience_claims.yaml` ✓ — **Brier/Murphy/ECCE shipped** (degenerate: all-validated seed set); ledger destructively syncs to the YAML seed; external validation = free-text curation | lead/points scoring not mechanically reproducible (6/52 rows deviate) | partial → Gen2 claims ledger (Brier, empirically honest) | belief-class records + calibration statute |
| Galaxies/registry (CLEANLY→compile) | single-valued physical containers (one column, one SQLite DB per name; no enum enforcement/cap); taxonomy **advisory only**; 47-galaxy sprawl **narrative-only** (mechanism plausible) | per-galaxy backends + connection pools explain fd pressure | distilled → enum + capped dynamic registry | scope labels/views over one store |
| Compartments (PRESERVE→link) | `mandala.*` shelter templates (research/sandbox/production/secure) — **silent degradation**; capability typos dropped; Dharma fails open on engine error | access tiers real but leaky; no authenticated authz | folded → mandala DBIs; economy ruling descendant | statutes + scopes; link preserved |

## 3. Wave 2–5 assignment (tentative, from the ratified verdict set)

- **Wave 2 (extracted 2026-09-17 — `docs/PHASE4_WAVE2_FINDINGS.md`):** relations/associations
  (v26 typing never persisted; Hebbian dormant there but **live in Gen2's serving mechanism** —
  see the map), retention/lifecycle (v26 sweep never auto-armed and its persist path was broken;
  Gen2 splits retention vs delete-capable lifecycle), currentness strata (already native), citta/
  dream consolidation half (13 phases in Gen1, 12 in Gen2; CITTA headline is a label artifact),
  engines→recipes (v26 SkillForge ran and persisted 33 skills over a 4-verb vocabulary; no
  operator runtime), RSI/friction (self-certification violated at mechanism level), self-model/
  conformal (in-memory, unfed), ingestion gates (already compiled).
- **Wave 3 (extracted 2026-09-17 — `W3_lens_projection.md`):** S projection as declared
  optional lens (gate-scoped `count < 2`); v26's coordinate "lens" was a silent always-on
  stage, Gen2 coords are hash-derived/diagnostic — there is no inherit-able lens behavior;
  projection-agreement and multi-view selection remain parked/dormant until a new registration.
- **Wave 4 (extracted — `W3_geneseed.md`, `W3_simulation_imagination.md`,
  `W3_field_activation.md` + wave-2 files):** constellations/emergence (v26 = coordinate
  clustering + three emergence organs; H8 six-condition acceptance); Geneseed (today's miner is
  an *unrelated* git classifier; the V9.1 typed-parent-edge design has zero code; Phase-4 gate:
  after selection demonstrated); simulation/imagination (TZPF = scorecard; four disjoint Gen2
  organs; domain law already enforced); field dynamics (v26 read-side channel was live, no
  measured win; Gen2's 300 s decay never applied — candidate gated on a task where propagation
  beats retrieval).
- **Wave 5 (extracted — `W3_mesh_transport.md`, `W3_reflex_boundary.md`):** mesh/agents (Gen1
  mesh was unwired; Gen2 is opt-in with discovery-gate real and semantic gate authority-only;
  RPC frames unsigned; consent/egress hook missing — two-gate work stands); reflex/sensor/
  actuator (hardware path live in production with an **inert safety mask** — any link must
  enforce, not document, its boundary); Gan Ying transport (iceoryx2 re-adoption needs its own
  receipt); retirements stay retired.

## 4. Wave-1 source extraction — status

**Complete 2026-09-17** (subagent batch 1; files in `docs/findings/`): store/dedup ·
revisions/supersession · retrieval · sessions/continuity · coordination · claims/prescience ·
galaxies/compartments · Gen2 9.1.8 source map. Errata candidates and migration-spec divergences
are consolidated in `PHASE4_WAVE1_FINDINGS.md` (pending operator wording).

Remaining before the wave plan is written: (a) resolve the consolidated errata wording from
**both** batches (`PHASE4_WAVE1_FINDINGS.md`, `PHASE4_WAVE2_FINDINGS.md`); (b) clear the live-data
verification items (aggregate lists in both masters); (c) extract waves 3–5 — **complete**
(`PHASE4_WAVE3_FINDINGS.md`). The **wave plan** is now the next artifact: one row per
capability with destination, migration recipe (ancestor · wire · acceptance · owner), frozen
behavioral spec source, adversarial cases, and ablation design.

Each extracted row already carries: behavioral spec draft · selection history · adversarial
cases (9.1.7 fix list + `PHASE4_GEN2_DELTA.md` §3 additions) · candidate ablation.

## 5. What this study does not do

No verdict changes; no code; no resurrection by narrative; no migration before the nucleus
freeze; no v26 "magic" claims — the tree is built from code, sessions, and rulings, and the
lightning stays a hypothesis with measured conditions (`PHYLOGENETIC_FRAMING.md` §2).
