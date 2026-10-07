# Phase 4 — Wave-2 findings (native cognitive) + batch index

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md` (wave-1 master), `PHASE4_GEN1_TREE.md` (§3 wave map). Detail in
`docs/findings/W2_*.md` (seven files, ~1,060 lines). Format per row: **observed behavior ·
selection history · candidate expression/manifest · adversarial cases · ablation**.

---

## Subagent batch 2 (2026-09-17) — file index

| File | Scope | Headline findings |
|---|---|---|
| `W2_associations_relations.md` | associations/relations | typed edges were **declared but never persisted** (LinkType 7 kinds live only in-memory; every save re-inserts 3-column triples, kind/direction revert to defaults); Hebbian is **three dormant organs** (zero callers) while the live dynamics are decay+prune — i.e. use increments counters, time decrements strength; retrieval influence is extraction-dependent (entity boost 0.25, graph walk ×strength, spreading-activation channel); `CausalMiner` dormant (its own comment records a 1.36M-edge / ~460 MB bloat incident) |
| `W2_constellations_emergence.md` | constellations/emergence | constellation = **5D coordinate clustering** (HDBSCAN + grid fallback) emitting named objects, memberships, KG edges and Gan Ying events; it *was* wired into retrieval (× (1+0.3·conf)) but the batch path queried the wrong table name and swallowed the error → boosts always empty, no prune; emergence = **three organs** (the adjudicated zombie, the hardcoded+random variant, and a real SQL detector that persisted 329 insights 7/28–8/1); membership table single-valued per galaxy, 74,571 rows, never lifecycle-managed |
| `W2_retention_lifecycle.md` | retention/lifecycle | five signals = semantic 1.0 / recency 0.9 / emotional 0.8 / connection 0.7 / protection (hard override); thresholds keep ≥0.35 / decay ≥0.15 / archive <0.15; the sweep was **never armed automatically** (`attach()` no caller); persist path is **broken on the shipped backend** (missing batch methods → archive verdicts raise, manager returns all-zeros "success"); memory rows are never deleted, but **association edges are hard-DELETEd** (rotation-not-deletion is not uniform across object types) |
| `W2_citta_dream_cycles.md` | citta/dream/cycles | "CITTA 18,204 (85 %)" is a **storage-label artifact** — every session turn is written as `MemoryType.CITTA`; the real taxonomy is `turn_type` tags; citta is a real per-dispatch pipeline but its stream sink is lossy (deque 100, rewritten); `CycleEngine` writes nothing (in-memory only, no attestation it ran); Gen1 dream = **13 phases** (Gen2 has 12) and it does write (triage DELETEs, edge halving, promotions, kaizen insights); field half never integrated (tool-only `apply_priming`) |
| `W2_engines_recipes.md` | engines/recipes | the 28-slot Engine Framework was **metadata** (77 concepts verified; 54/77 classes exist, 12/28 canonical names have a class in the declared path; no base class, no dispatcher); executable engines ran as pipelines (Kaizen detectors, Serendipity live at startup, Apotheosis in-memory); **SkillForge actually ran and persisted 33 skill JSONs** (22 auto-forged) — whole-call traces, ops string-matched into **4 verbs** (SEARCH/ANALYZE/TRANSFORM/CONSOLIDATE), `parameters={}`, 4/33 with execution history, zero amendments; replay was dormant (router never matched forged skills) — recipes were **write-only** |
| `W2_rsi_selfmodel.md` | RSI/self-model | `feedback.db` verified: 906 applications / **36 outcomes (4.0 % coverage)** / 29 correlations (1 nonzero); success 2/36 — both the same event; "never self-certify" was **violated at mechanism level** (`verify_outcome` re-runs the same analyzer; maker = checker; success scored as proposal *disappearance*); auto-fix path structurally dead (method strings vs closed 9-verb vocabulary → "Unknown action"); self-model in-memory, unfed; homeostat log 55 rows all "READ" (CORRECT/INTERVENE absent from `harmony/` — but `whitemagic_dream.log` carries 361 CORRECT lines; §G-26); possibility-winners = self-scored optimizer overwriting boot constants, no outcome verification |
| `W2_gen2_source_map.md` | Gen2 9.1.8 map | pointers per wave-2 row (associations.rs typed edges + live Hebbian counters, recall graph-walk knob default 0.0; retention.rs decay-only sweep wired only to dream vs delete-capable unwired lifecycle.rs `forget`; 12-phase dream + learned selection; gan_ying daemon pulse; alchemical_round 28 declarative "engines" as report generators; rsi.rs caller-asserted resolution, excluded from curated; selfmodel + env-gated conformal; calibration = **four disjoint universes**) |

## Consolidated errata candidates (batch 2 — dispositioned 2026-09-17 — see `PHASE4_ERRATA.md`)

1. **Associations ancestry:** "typed links folded" overstates v26 — typing never survived a
   save and Hebbian was unreachable; the verdict (edges compile, dynamics parked) is
   *strengthened*, not changed. No `memory.associate`-style route existed in v26.
2. **Hebbian status (Gen2 map):** "Hebbian parked" is false at the mechanism level — it is
   **live in `wm-memory`** and only absent from the serving path; specs must say which.
3. **Citta headline:** matrix L163's "session stream was mostly citta stream" is a labeling
   artifact (every turn is written as CITTA); the real signal is `turn_type`.
4. **Dream phases:** Gen1 `DreamPhase` has **13** members vs Gen2's 12; `LearnedDreamCycle`
   reordering is Gen2-only (E15/matrix L115 wording).
5. **Engine/recipe framing (E16):** "SkillForge is metadata-only today" holds for **Gen2**; v26
   had a working, persisted forge over a 4-verb vocabulary — E16 should read "whole-call trace
   mining existed; the operator-level runtime did not." (Stale registry doc-ref and "39
   absorbed" test comment noted.)
6. **RSI ledger phrasing:** lineage's "906 → 36 → 29" reads as a healthy loop; annotate with
   coverage (4.0 %), success (2/36, one event), correlation (1/29 nonzero). "Friction" is Gen2
   vocabulary — Gen1 ancestry is the kaizen/autodidactic loop.
7. **Retention pointers:** the brief's matrix "L74/§2.4" does not resolve (retention row is
   §2.1); and default `rg` traversal silently skips `core/memory/sqlite_backend.py` — wave-1
   passes may have undercounted hits there (re-check flagged rows with `--no-ignore`).
8. **Emergence ancestry row** conflates at least three organs (see index);
   `constellation.stats/merge` handlers are constant-zero no-ops.

## Migration-spec divergences flagged (Gen2 map, wave-2)

1. "Hebbian parked" (above) — serving-path vs mechanism split.
2. **Retention ≠ lifecycle:** gentle `RetentionEngine` (decay-only, dream-wired) vs
   delete-capable `LifecycleManager::forget` (no callers) — two organs, name them separately.
3. "Engines" in Gen2 are catalog names + report generators, not execution units; recipes are
   not a Gen2 runtime.
4. RSI resolution is **caller-asserted** (no independent verification) and excluded from the
   curated profile — a migration must not claim "verified" in the tested sense.
5. "Calibration" spans four disjoint universes (self-model, conformal store, recall conformal,
   claims ledger) — specs must name the one they mean.
6. Currentness strata are enum+sweep **behind env knobs**, not a request-time relation.

## Remaining open questions (aggregate, batch 2)

UNVERIFIED items carried from the files: the 460 MB bloat figure (comment-sourced); live
associations distributions (no Gen1 DB on host); whether the constellation boost was ever
live; who wrote the 11 free-text-op skills; whether `apply_auto_fixes` ran non-dry-run; the
"untitled" fix author; any homeostatic CORRECT/INTERVENE firing; EventType "234" count
(doc-only); whether `WM_VALIDITY_SWEEP` runs by default. Wave-3–5 extraction queue (lenses,
strange Gen1, hard remainder) remains — see `PHASE4_GEN1_TREE.md` §3–§4.
