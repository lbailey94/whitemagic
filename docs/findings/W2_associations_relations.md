# W2 — Associations & relations (Gen1 v26 observable behavior)

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md`. Repo root for citations: `og_whitemagic/` @ v26.0.3 (`4d5be091`).
Row target: *Associations* — verdict CLEANLY → compile for **typed edges only**; Hebbian
dynamics `pending`, re-entry only via the manifest rule (`PHASE3_DECOMPOSITION.md:54,109-111`;
`PHASE4_GEN1_TREE.md:56`). Gen2 side not read in this pass; fold statements are docs-sourced.

## Observed behavior (cites)

- **Two link vocabularies, one physical store.** (a) `Memory.associations: dict[str,float]`
  (id → strength, no kind) hydrates from the `associations` SQL table
  (`core/whitemagic/core/memory/backends/hydration.py:47,75`) and persists on save; (b)
  `Memory.links: dict[str, MemoryLink]` carries `LinkType` + `activation_count`/`last_activated`
  (`core/whitemagic/core/memory/unified_types.py:57-77,107`) and appears only in
  `to_dict`/`from_dict` — no DB column/table found for it (`rg -uu 'link_type'
  core/whitemagic/core/memory/{sqlite_backend.py,backends/*.py}` → 0 hits).
- **`LinkType` = 7 declared kinds** (`unified_types.py:36-45`): `related · extends ·
  contradicts · supersedes · temporal · causal · cascade`. Writers: `agent_memory.py:252-260`
  maps external API strings → enum then calls in-memory `mem.add_link` (never the DB);
  `linking/auto_linker.py:110-138` writes only `RELATED`; `linking/cascade.py:58-62` only
  `CASCADE`. No path writes a `LinkType` value into the DB; the `relation_type` column receives
  extractor predicates, causal labels, or default `'associated_with'`
  (`sqlite_schema.py:249-251`). A declared vocabulary with no store enforcement.
- **One table, accreted columns.** Base `(source_id, target_id, strength, PK(source,target))`
  (`sqlite_schema.py:166-173`); v14.0 adds 9 columns — `last_traversed_at, traversal_count,
  created_at, direction DEFAULT 'undirected', relation_type DEFAULT 'associated_with',
  edge_type DEFAULT 'semantic', valid_from, valid_until, ingestion_time` (`:240-255`); indexes
  on source/target/edge_type/direction/strength (`:362-368`). 37 py files name the table
  (`rg -uu -l 'FROM associations|INTO associations|UPDATE associations' --type py core/whitemagic | wc -l`).
- **`AssociationMiner` (keyword path)** samples `list_recent`+`search`, builds keyword
  fingerprints (50-item stopword list), scores Jaccard + 0.3·min(1, shared/5), gates score
  ≥0.15 **and** ≥3 shared keywords, top-50, then `add_association` both directions with the same
  score (`association_miner.py:36-51,160-175,338-355`); strong (≥0.3) proposals also become KG
  `associated_with` relations (`:375-409`). `mine_semantic` swaps overlap for embedding cosine
  (weak ≥0.50, strong ≥0.70), same bidirectional persist (`:411-528`).
- **The miner's failure mode was edge-count bloat, gated by exclusion.** Module comment records
  2026-07-21: 1.36M associations on 36.7K session memories ≈ 37 edges/memory, ~460MB bloat in one
  galaxy DB; fix = exclude `sessions` + class-isolated galaxies + env
  `WM_ASSOCIATION_MINER_EXCLUDE_GALAXIES` (`association_miner.py:215-243`). 460MB figure
  comment-sourced → **UNVERIFIED live**.
- **`CausalMiner` = directed edge by time order + similarity.** Docstring claims
  `led_to/caused_by/preceded/followed_by`; classifier returns four labels
  (`led_to/influenced/preceded/related_to`, `causal_miner.py:155-166`). Source = earlier memory
  always; strength = 0.50·cosine + 0.35·exp(−0.693·Δt/24h) + 0.15·tag-Jaccard; Δt>168h dropped;
  persisted `direction='directed', edge_type='causal', relation_type=<label>`
  (`:104-107,137-182,274-355`). No embeddings → temporal fallback uses temporal proximity as the
  "similarity" term (`:377-440`). **Zero invocation sites** (`rg -uu 'get_causal_miner' --type py
  core/whitemagic` → only itself + unimported duplicate `memory/miners.py`, 1,128 lines, itself
  importer-less).
- **Hebbian exists in three places; none load-bearing on the live path.** (1)
  `MemoryLink.activate()` → `min(1, s+0.05)`, `decay(0.99)` floor 0.1 (`unified_types.py:68-77`);
  reachable only via `Memory.strengthen_link` (no callers) and
  `linking/strength_tracker.py:43-76` (5-min co-access window calling `activate`); the `linking/`
  package has **zero importers** (`rg -uu 'from whitemagic.core.memory.linking'` → own `__init__`
  only). (2) SQL `hebbian_strengthen` (`+=0.05·(1−s)`, `traversal_count+1`)
  (`backends/graph_commands.py:289-307`, proxy `sqlite_backend.py:1489`) — **zero callers**.
  (3) Graph-walk bookkeeping is live but **counter-only** (`graph_walker.py:938-950`;
  `core_access.py:492-520`). The only scheduled weight dynamics is **decay+prune**
  (`graph_commands.py:39-121`: episodic `exp(−0.0231·days)`, else `(1+0.1·days)^−0.5`, prune
  <0.05, skip <0.5 day old), called from `memory/lifecycle.py:214` and the homeostat when >30 %
  of edges sit <0.1 (`harmony/homeostatic_loop.py:1016-1035`). Net: use increments counters,
  time decrements strength — the live asymmetry is anti-Hebbian.
- **Edges influence retrieval via three couplings, all extraction/mining-dependent:**
  (1) entity boost — `lookup_entity_memories` reads default-DB `associations` for
  `target_id='entity:…'` neighbors, feeds `adjustment += 0.25·entity_score` into
  `final = rrf × (1+adj)` (`entity_reranker.py:78-123,240-250,275-291`); (2) graph channel —
  transition prob multiplies `edge.strength` (`graph_walker.py:181-251,437-455`), weight 0.4 in
  the RRF planner; (3) spreading activation — neighbors with `strength ≥ 0.1`, factor = strength,
  default hop decay 0.7, as planner candidate channel (`spreading_activation.py:312-348`;
  `search_planner.py:354-368`). Non-ranking reader: `serendipity_engine.py:136`.
- **Save round-trip strips edge typing.** Store/update deletes all rows `WHERE source_id = mem.id`
  and re-inserts only 3-column dict triples (`sqlite_backend.py:564-568,735-739`) —
  `direction/relation_type/edge_type/created_at` revert to defaults. Cross-galaxy transfer does
  copy typed columns, filtered to `relation_type != 'associated_with'`
  (`galaxy_manager.py:495-525`).
- **Write-side coupling:** on store, KG v2 extracts entities/relations from `title+content`
  (≤4000 chars) and inserts memory→`entity:<name>` edges with extractor confidence as strength
  (regex path 0.3) (`unified.py:456-465`; `entity_extractor.py:302-352`;
  `knowledge_graph_v2.py:210-240,350-390`) — this is what makes the entity boost non-zero later.
- **Fold context (docs-sourced):** Gen2 keeps `associations.rs`, Hebbian PARTIAL / promotion
  candidate with no evidence (`THEORY_MECHANISM_MAP.md:87`; `PHASE3_DECOMPOSITION.md:87-88`);
  Gen2 has no first-class `supersedes` relation (`PHASE4_WAVE1_FINDINGS.md:143-144`); cold
  rotation does association cleanup (`W1_gen2_source_map.md:140`). Gen3 relation form
  `e=(w,s,c,t)` = learned strength / sign-direction / resource cost / trust, plus `kind`,
  `src`/`dst`, `class`, provenance, `state` (`PHASE1_CONTRACTS.md:58-63`).

## Selection history

v14.0 added temporal/graph columns to a plain `(src,dst,strength)` table; v14.1 added the
directed CausalMiner; v15.2 added write-time extraction; v24 the dream cycle calls cross-galaxy
mining. Each wave appended a *writer*, never a reader contract: typed columns exist in schema
but hydration ignores them and save overwrites them. Decay/prune landed as maintenance; no
caller was ever wired to SQL `hebbian_strengthen`. The ratified decomposition folded the table
into Gen2 `associations.rs`, compiled typed-edge behavior only, and parked Hebbian behind E6.

## Candidate Gen3 expression / manifest notes

Expressibility observations (not design): `e=(w,s,c,t)` must carry (1) `kind` — a closed
vocabulary with operational meaning per kind (LinkType's 7 vs labels actually written:
`associated_with`/predicates/`led_to`…); (2) direction/sign — mined edges were bidirectional,
causal one-way, decay per-row (asymmetry possible); (3) `w` as derived strength (miner score,
extractor confidence, cosine) vs use-learned strength — v26 never demonstrated the latter live;
(4) edge provenance (miner run/extractor/transfer/manual) — v26 kept only `edge_type='causal'`
and KG-feed metadata; (5) decay policy per kind (episodic decays ~10× faster). Manifest: ancestor
named; wire/acceptance/owner unset (`PHASE3_DECOMPOSITION.md:109-111`).

## Adversarial cases (for the frozen spec)

1. **Save round-trip erases typing/direction.** Mine a directed causal edge, recall+save the
   source memory: `sqlite_backend.py:735-739` re-inserts 3 columns → edge reverts to
   `undirected/associated_with`. Test both typed-update and dict-hydration paths.
2. **Target-side invisibility.** Hydration loads only `source_id` edges
   (`hydration.py:47`), while the entity boost queries `target_id='entity:…'`; one side re-saved
   can revert the other's symmetry. Divergent decay is then per-row.
3. **Extraction-dependent ranking signal.** The 0.25 entity term is 0 if extraction never ran or
   wrote elsewhere than the queried `DB_PATH`; the weight stays in the formula regardless. A/B
   must separate "no edges" from "edges present but unhelpful".
4. **Session-stream incident class.** Edge count on homogeneous writes is the failure mode
   (1.36M edges, comment-sourced); the shipped control is name/class-based galaxy exclusion plus
   an env var (`association_miner.py:224-243`) — a blacklist, not a rate/quality gate.
5. **Causal claims from weak ordering.** `Δt=0 → proximity 1.0`, and `src_time > tgt_time`
   silently swaps hands (`causal_miner.py:283-300`): tie-broken creation order decides direction;
   future-dated clock skew can invert "cause".
6. **Counts are attempts, not rows.** `add_association` returns True regardless
   (`graph_commands.py:32-36`) and `INSERT OR IGNORE` skips re-mining, yet
   `links_created`/`edges_created` still increment (`association_miner.py:349-351`;
   `causal_miner.py:356`).

## Ablation ideas

- Entity weight 0 vs 0.25 × extraction on/off: separates the signal's contribution from its
  presence in the formula.
- `staleness_beta` 0 vs default: traversal counters are live, so measure ranking effect before
  any Hebbian admission discussion.
- Disable `decay_associations` (lifecycle + homeostat) for N sweeps: strength distribution, edge
  survival, and whether mined edges outlive prune at 0.05.
- Graph channel weight 0 vs 0.4 with a mined vs emptied `associations` table: attributes the
  graph channel to the edge store.
- Cross-galaxy mining with/without the sessions+isolated exclusion on a fixture: reproduce the
  1.36M-edge class; measure edges vs distinct pairs.

## Open questions

- Was `linking/` (StrengthTracker, AutoLinker, cascade, `MemoryLink.activate`) reachable from any
  shipped entrypoint? No importers found; agent adapters could call `add_link` at runtime — UNVERIFIED.
- No live Gen1 DB exists on this host (per `W1_retrieval.md`); live row counts, direction/
  `relation_type` distributions, orphan/strength histograms are UNVERIFIED.
- `entity_reranker` reads `config.paths.DB_PATH` only — do cross-galaxy entity edges ever
  contribute, and was CausalMiner ever scheduled (labels consumed at retrieval)? UNVERIFIED.
