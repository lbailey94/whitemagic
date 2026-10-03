# Phase 4 — Wave-2 findings: constellations / emergence

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md`. Assignment: `PHASE4_GEN1_TREE.md` §3 (wave 4) and
`PHASE3_DECOMPOSITION.md` §2.1 row "Constellations/emergence" — verdict **EXPERIMENT**
(manifest-gated; never re-adopt the v26 simulation; E7 §). Ancestors read at tag v26.0.3:
`core/memory/constellations.py`, `.../constellation_algorithms.py`, `whitemagic/emergence/`,
`core/patterns/emergence/dream_state.py`, `core/intelligence/agentic/emergence_engine.py` (package
root `core/whitemagic/`). Counts are command-generated; live-state counts are read-only
`sqlite3 file:<copy>?mode=ro` queries over `.../v26/state/` (a frozen copy). The emergence zombie is
adjudicated and not re-litigated (its mechanism is only pinned below).

---

## Observed behavior — constellations

**What defined a constellation (algorithm).** Not clustering over relations or co-access: the
input is the 5D holographic coordinates table. `detect()` selects `holographic_coords JOIN
memories` ordered by importance (`constellations.py:183-193`), then prefers HDBSCAN — euclidean
metric, `min_cluster_size=max(min_cluster_size,5)`, `min_samples=max(ms//2,2)`, noise label −1
skipped, per-cluster mean `probabilities_` = stability (`constellation_algorithms.py:244-286`);
fallback grid: 8 bins/axis, cells with ≥`min_size`, flood-fill merge, stability always 0.0
(`:335-383`). Siblings exist unused by `detect()`: Rust KD-tree (`:289-332`), Julia
single-linkage/KD-tree/coherence (`:152-241`), cosine-graph components (`:443-535`).

**What it emitted.** `Constellation` objects: name, member_ids, 5D centroid, radius, dominant_tags
(top 5 by tag count), dominant_type, avg_importance, `zone = classify_zone(1.0 - centroid.v)`,
stability (`constellations.py:61-98`, `:245-247`); names = zone prefix + top-2 tags + roman
suffixes (`:349-385`). Persisted outputs: (a) DB memberships (`:551-577`; DDL
`sqlite_backend.py:397-405`, `memory_id` **PK**, confidence default 1.0; writer
`graph_commands.py:124-140` `INSERT OR REPLACE`); (b) KG entity + `belongs_to_constellation`
relations for the first 20 members (`:387-432`); (c) Gan Ying `NOVEL_CONCEPT`/`FORGOTTEN_CONCEPT`
from Hungarian drift matching (`:726-909`, emitted `:911-933`). The docstring says "persisted as
PATTERN memories with special tags" (`:9-10`) while the strategy line and code say metadata, not
new memories (`:17`, `:551-577`) — a doc/code contradiction. Recorded names differ: state DBs hold
`constellation_0000`-style names (`constellation_detector.rs:82-83`, Rust fast path
`pattern_engines.py:292`) — sessions 10,394 rows under one name, meta 27,016/1, archive
33,358/4 (queries below).

**Was it consumed at retrieval/cognition?** Yes — as a tuned multiplicative boost over fused
rankings. `unified.py:895-931`: encode query, `closest_constellation` scores it against dominant-tag
texts (cosine, `embeddings.py:1190-1225`); if similarity ≥ 0.25 (hardcoded), same-constellation
candidates get `score *= 1 + 0.3 * max_confidence`; others get `+= 0.05 * (1 - confidence)`.
`search_planner.py:280-299` writes `constellation_score` and tags the channel. Other consumers:
annotation hook (`constellations.py:957-972`), foresight drift vectors (`foresight_engine.py:66-69`),
CoreAccess context/bridge queries (`core_access.py:258+`, `:1056-1081`), dream cycle detect +
merge (`dream_cycle.py:57,150,587-592,1063+`). Rust `constellation_boost` is registered
(`lib.rs:133-134`) but no Python caller found (UNVERIFIED dead).

**Dead or constant-zero edges (name ≠ function).** `handle_constellation_stats`/`_merge` call
`get_stats`/`merge_similar`, which the detector does not define → constant zeros
(`pattern_engines.py:361-372,382+`). The batch retrieval path queries plural
`constellation_memberships` (`entity_reranker.py:437`) while DDL/writer use singular
`constellation_membership` (`sqlite_backend.py:398`), swallowed at `:448-451` — planner-side
membership boosts were always empty. No prune path exists (rg: zero DELETE hits), and PK
`memory_id` makes membership single-valued per galaxy: stale rows survive re-detection and a
memory in two clusters keeps only the last-written one.

**Command-generated live counts** (read-only loop over `v26/state/**/*.db`,
`SELECT COUNT(*) FROM constellation_membership`): 74,571 membership rows across scanned state DBs;
sessions 10,394 (holo coords 18,351), meta 27,016 (270), archive 33,358 (1,051), codex 2,785
(13,240), research 453, dreams 218, aria 104, citta 63, universal 47, insight 46, tutorial 41,
creative_solutions 25, openai_archives 20, telemetry 1; top-level `state/whitemagic.db` has none
(0 coords). UNVERIFIED: meta/archive membership counts vastly exceed their coord counts.

## Observed behavior — emergence (mechanism pinned; verdict untouched)

Three distinct organs carried the name:

1. **`whitemagic/emergence/` DreamState** writes `state/emergence/dreams.jsonl` (`dream_state.py:44`,
   `:123-125`). `DreamSequence.insights` (`:32`) is never assigned — `dream()` stores only counts
   (`:73-79`). Its helpers fail-soft to 0: `_consolidate_memories` = `recent(limit=50)` (`:91-99`),
   `_find_connections` = TemporalWeaver threads (`:101-109`), `_synthesize_patterns` delegates to
   EmergenceEngine (`:111-121`). Recorded fossil: `wc -l dreams.jsonl` = **284**; all 284 lines
   carry zero counts and `"insights": []` (rg count = 284) — the adjudicated 284-runs/0-output.
2. **`core/patterns/emergence/dream_state.py`** is the hardcoded/random synthesizer the ledger
   cites: literal fallback pattern list (`:166-172`), `random.sample` combinations (`:183-186`),
   "Neural Brain Synthesis" is a literal dict/f-string, no model call (`:224-235`), novelty/value
   `random.uniform(0.7,0.98)` / `(0.6,0.95)` (`:241-242`), stored as PATTERN memories (`:252-265`).
   Errata candidate: the ledger quotes novelty 0.6–0.95 (here 0.7–0.98, on `practical_value`) and
   a "Simplified" comment absent from the tagged tree (vault copy may differ).
3. **`core/intelligence/agentic/emergence_engine.py`** is different and non-random:
   `scan_for_emergence` aggregates five SQL detectors (`:247-268`), e.g. tag co-occurrence over the
   last 7 days (`:467-502`), filters recursive echoes (`:270`), persists to knowledge-galaxy
   `emergence_insights` (`:354-369`) and feeds LearningBus (`:304-325`) + LearnedRouter
   (`:327-350`). Recorded store: **329 rows**, 2026-07-28→2026-08-01, tag_cluster 178 /
   resonance_cascade 128 / novelty_spike 22 / cross_domain 1 (generated query). "0 output" is true
   of `dreams.jsonl`, not this table — an ancestry-split errata candidate, no verdict change.
   **Correction (W0 intermission, 2026-09-17):** the 329-row table is real, but July's
   `tool_usage.db` contains **zero `emergence.*` rows** — records exist without a visible
   execution trace at the tool layer; evidence level = RUNTIME-ARTIFACT, not RUNTIME-OBSERVED
   (`PHASE4_ERRATA.md` G-27). The
   `whitemagic/emergence/pattern_discovery.py` meta-counter (`:35-89`) has only test callers found
   (UNVERIFIED runtime).

Only organ 3 loads a real SQL substrate; organs 1–2 are the simulation the canon bans (§13; E7).

## Selection history

Never fairly tried (EXPERIMENT, manifest-gated). Constellation machinery shipped into retrieval
unmeasured: the only test found (`tests/unit/test_constellation_eval.py`) exercises a separate
`ConstellationEvaluator` shape, not detector accuracy or any A/B; the boosts are tuned ranking
constants. Gen2 context (cite only): matrix row 60 lists constellation detection under FOLDED
associations; canon §3.5 marks the family PARTIAL-G2 with `constellation.detect/list` (5D
clustering), topology comparison non-shipped. The Gen3 manifest (ancestor v26 emergence; wire
topology over relations; acceptance H8 six-condition test vs ablation; owner unset) is unchanged.

## Candidate Gen3 expression / manifest notes

Canon §3.5 requires a **reusable relational pattern** promoted to a first-class star. Measured
against v26: (a) no relations — membership derives from coordinate proximity, no edge set, no
relation kinds, no strength/confidence/activation_history per edge; (b) no reuse — the name is
generated from tags, never earned by recurrence, and nothing counts pattern reuse; (c) no
lifecycle — no prune/decay/rotation of memberships, and `memory_id`-PK membership is single-valued,
so overlap across patterns is unrepresentable; (d) no evidence — no ablation, accuracy, or
promotion event; every consumer uses fixed constants. Those four gaps are what the §3.5 reading
needs and what v26 lacked. Manifest stays as E7 (owner unset); this file adds no proposals.

## Adversarial cases (for any frozen successor spec)

1. **Overlapping patterns.** v26 PK forces one membership per memory per galaxy; any successor must
   define multi-membership and membership-with-weight, and test a memory genuinely in two patterns.
2. **Identity across re-detection.** Names are tag-derived in Python but `constellation_NNNN` from
   the Rust tool path; drift matching allows a 2.0-unit Hungarian radius. Test: a re-clustered
   pattern must not surface as NOVEL plus FORGOTTEN simultaneously.
3. **Stale memberships.** No prune path exists; confidence defaults to 0.8 when stability is 0 (grid
   path). Test retrieval after a pattern effectively dissolves — the boost must not persist.
4. **Tuned constants.** 0.25 floor / 0.3 boost / 0.05 diversity are the swept-threshold pattern E4
   warns about; re-entry needs declared floors and a battery, never these numbers.
5. **Tool-surface honesty.** `constellation.stats/merge` return constants and the planner's batch
   membership query hits a nonexistent (plural) table; acceptance must establish which paths ever
   produced signal before crediting the family.

## Ablation ideas

- Disable the constellation multiplier in fused ranking (`unified.py:920-929`) on a corpus with
  populated memberships; unchanged ordering means the boost was inert (the dead batch path
  suggests it largely was).
- Same coordinates through `detect_hdbscan` / `detect_grid` / `detect_kdtree`: stability is 0 for
  grid, persistence for HDBSCAN, radius-derived for KD-tree — three semantics for one field.
- EmergenceEngine detector-by-detector against its 329-row history; tag pairs and cascades
  dominate, so baseline them against simple tag frequency before attributing emergence.

## Open questions

- Was the constellation boost ever live on a real query path? It needs an in-process `detect()`
  (centroid cache) plus populated memberships; recorded rows come from larger galaxies, so
  demo-path activation is UNVERIFIED.
- Who wrote archive's 33,358 rows/4 names and meta's 27,016/1 name given their coord counts —
  detector, seeding, or migration? Producer provenance UNVERIFIED.
- Is Rust `constellation_boost` genuinely unused (registration-only)? UNVERIFIED.
- Which organ the ledger's `emergence/` row covers; the overlap (two `dream_state.py`, two
  `pattern_discovery.py`, plus `emergence_engine.py`) invites a naming errata even though the
  random/hardcoded evidence is real (organ 2 above).
