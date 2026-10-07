# Phase 4 — Wave-1 findings: Galaxies & compartments

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md`; ancestor rows Galaxies/registry (CLEANLY→compile) · Compartments
(PRESERVE IMPL→link); ratified notes `PHASE3_DECOMPOSITION.md` E8/E10 (L92–99).

## Observed behavior — galaxy taxonomy and store

- **The taxonomy is constants plus a heuristic classifier, not a gate.** `galaxy_taxonomy.py`
  defines the 14 names (`:34–64`), `GALAXY_ORDER` (`:66–81`), zones CORE/INNER_RIM/MID_BAND/
  OUTER_RIM/FAR_EDGE (`:83–98`; default-search set `:100–104`), and deprecated aliases
  (`:106–114`). `classify_memory()` (`:117–265`) / `get_galaxy_for_tags()` (`:268–291`) map
  title/tag/content to one name; callers are the `galaxy.taxonomy` handler
  (`handlers/galaxy.py:386,607`) and consciousness modules (`meta_galaxy.py:171,312`,
  `citta_bridge.py:29`) — the write path does not call it.
- **What the store enforces is a single-valued container.** `memories.galaxy TEXT DEFAULT
  'universal'` plus an index (`sqlite_schema.py:124,369–370`); each galaxy is its own SQLite DB
  (`galaxy_router.py:8–9,132–162`; `galaxy_manager.py:200–203`). No per-memory multi-galaxy
  membership weights were found (`constellation_membership`, `graph_commands.py:124–184`, is a
  cluster concept); the only galaxy weights are per-context retrieval multipliers
  (`galaxy_gating.py:71–168`, tools `neuro_cognitive.py:88–148`), keyed by context, not stored.
- **No enum enforcement and no creation cap.** `_get_galaxy_backend()` sanitizes a name
  (`validate_galaxy_name`, `backends/protocol.py:119–143`) then creates a DB for any non-empty
  name; `_get_backend_for_memory()` always routes per-galaxy (`galaxy_router.py:183–194`);
  `create_galaxy()` has no limit (`galaxy_manager.py:175–230`). Registry metadata lives in
  `galaxies.json` (`:47,124–171`); global switching is deprecated (`:275–318`) in favor of
  request-scoped `get_memory_for_galaxy()`/`galaxy_context()` (`:338–398`); `share_galaxy()` is a
  registry pointer to the same DB file (`:962–1020`).
- **Isolation classes are real but partially wired.** `galaxy_class.py` resolves
  canonical/benchmark/eval/quarantine/test via `.galaxy_class` marker, name rules, env override
  (`:34–63,82–107`); `galaxy.classify` writes markers (`handlers/galaxy.py:152–208`). The filter is
  consulted by federated search (`search_planner.py:586–594`) and association mining
  (`association_miner.py:231–243`), but **not** by cross-galaxy transfer/dedup
  (`galaxy_manager.py:466–476`) despite the docstring claim (`galaxy_class.py:147–153`). Explicit
  `galaxy=`/`galaxies=` selection bypasses the filter by design (`search_planner.py:599–605`).
- **Cross-galaxy transfer.** `transfer_memories()` selects by query/tags/importance/distance, skips
  candidates whose content SHA-256 exists in target (`:466–476`), tags copies
  `transferred_from:<galaxy>` plus source metadata (`:480–493`), copies associations except
  `associated_with` (`:496–527`), archives moves at `galactic_distance=0.95` (`:543–544`), and
  records a phylogenetics transfer edge (`:529–539`). Unscoped `find_by_content_hash()` checks
  default backend, cached backends, then every on-disk DB by read-only probe
  (`galaxy_router.py:365–407`).
- **Federated search.** Unscoped search federates over discovered backends (over-fetch 3×,
  concurrency 4, merge by importance) after `_discover_galaxy_backends()` (`search_planner.py:
  552–631,589`). The older `search_multi_galaxy()` excludes only `archive` and was serialized
  because a thread pool deadlocked loading HNSW indices under a global lock
  (`galaxy_manager.py:862–867,929–931`).

## Observed behavior — sprawl incident and fd exhaustion (UNVERIFIED cause)

- The collapse count is narrative in this program only: matrix L56 ("47 at collapse") and
  `CODE_ARCHAEOLOGY.md:270` ("47 = runtime DB count in memory core"). No v26 source comment,
  CHANGELOG line, or test attests descriptor exhaustion or a reset to 14 — mark **UNVERIFIED**;
  a session-record dig is owed (see Open questions).
- The mechanism the code exposes (inferred, undocumented): discovery constructs a full
  `SQLiteBackend` for every on-disk galaxy (`galaxy_router.py:164–181`), each backend pools
  connections (`db_manager.py:181–183`, max 5; pools are per-DB-path globals `:317–329`), and every
  unscoped federated search rediscovers (`search_planner.py:589`). 47 DBs × 5 connections = up to
  235 descriptors from pools alone, before schema/backup work (`sqlite_schema.py:23–60`); nothing
  bounds count.
- Trajectory in the CHANGELOG: 10 canonical galaxies (`tags/v26.0.3/CHANGELOG.md:572`), "32
  galaxies" during the association build (`:261`), then 14 taxonomy constants; per-galaxy DB loss
  is a known failure class (sessions galaxy wiped 2026-07-28, `sqlite_schema.py:31–32`).

## Observed behavior — compartments

- `mandala.*` is a thin front over the shelter manager: templates research / sandbox / production /
  secure (plus `violet`) with capability grants, resource limits, Dharma profile
  (`shelter/manager.py:688–719`; defs `registry_defs/mandala.py:11–59`; handlers
  `handlers/shelter.py:96–175`). Isolation is tiered and best-effort: THREAD/NAMESPACE/CONTAINER/
  MICROVM/WASM (`:36–43`) are detected at startup (`:163–196`), an unavailable requested tier
  silently degrades to the best available (`:388–401`), and MICROVM executes as a container
  (`:532–537`).
- Capability enforcement is uneven: unknown capability strings are silently dropped (`:403–415`);
  the thread tier honors only a timeout, ignoring filesystem/network grants (`:218–229`); the
  container tier maps network mode to `--network` (`:262–288`). Default grants are empty
  ("Everything else denied", `:65–74`), so an unrecognized template falls through to an empty
  grant set (`handlers/shelter.py:127–135`) — the closest v26 match to "fail-closed unknown
  values"; matrix L63's `v4.3.0` attribution is not in the v26 CHANGELOG (**UNVERIFIED**).
- Dharma governance runs before execution but fails open on engine error ("proceeding without
  governance", `:497–518`); blocked verdicts return `status: blocked`. Violet shelter creation
  flips the process-global Dharma profile (`:446–456`). `WM_SHELTER_MAX_CONCURRENT` caps live
  shelters (default 4, `:338,377–386`).
- No compartment-to-galaxy access rule was found in v26 Python: the sandbox/production/secure
  mapping in matrix L63 appears here as execution templates, not memory access control
  (`can_access_galaxy` / context compartments are Gen2-side per `WMv9/AGENTS.md`).

## Selection history

- Gen1 shipped a 14-name taxonomy + zones over physical per-galaxy SQLite DBs, later adding
  name-level isolation classes (`CHANGELOG.md:110–111`); runtime DB count outgrew the taxonomy (32
  at the association build; 47 claimed at collapse) because creation was unbounded. Gen2 distilled
  to a 16-value enum over one LMDB env (`WMv9/crates/wm-core/src/galaxy.rs:11–49`, `COUNT=16`; 11
  memory galaxies `:82–96`) plus `DynamicGalaxyRegistry` capped at 20 virtual galaxies with
  effectiveness prune (`mutable.rs:284–285,372–375`) — matrix L62, verified by cheap read;
  compartments folded to Mandala isolated LMDB envs (matrix L63).
- Ratified rows stand: Galaxies CLEANLY→compile (`PHASE3_DECOMPOSITION.md:56`, E8 `:92–93`);
  Compartments PRESERVE IMPL→link (`:58`, E10 `:96–99`); worklist 7 asks the same questions
  (`PHASE4_GEN1_TREE.md:84–85`).

## Candidate Gen3 expression / manifest notes

- Galaxies: scope labels/views over one store (tree L50; E8). Any future manifest must name the
  container-vs-weight question explicitly — v26 provided single-valued containers plus retrieval
  context weights, no stored multi-membership.
- Compartments: statutes + scopes (tree L51; E10), enforcement machinery Gen2-side for alpha
  (`PHASE3_DECOMPOSITION.md:96–99`). No manifest change is proposed here.

## Adversarial cases (for the frozen spec)

1. **Unbounded scope names.** v26 wrote any name to a new DB with no cap; a scope label must either
   bound names or demonstrably not create per-name resources.
2. **Isolation asymmetry.** With a `.galaxy_class` marker on a source galaxy, federated search
   excludes it but `transfer_memories()` hash-dedup does not (`galaxy_class.py:147–153` vs
   `galaxy_manager.py:466–476`); confirm the successor refuses or discloses cross-class transfer.
3. **Explicit selection bypass.** `galaxy=` intentionally bypasses class isolation
   (`search_planner.py:599–605`); ensure the explicit path cannot become the default path.
4. **Capability typos.** Misspelled grants are dropped silently while the shelter still reports
   the requested template (`manager.py:403–415`); a typo must not yield a laxer run.
5. **Tier degradation label.** With only the thread tier available, a `secure` template executes
   with grants unenforced (`:388–401,218–229,431–441`); template labels must not outrun enforcement
   in Gen3 reporting.

## Ablation ideas

- Disable classification calls: explicit-galaxy writes/recall should be unchanged — confirms the
  taxonomy is advisory labeling, not containment.
- Drop the `_discover_galaxy_backends()` pre-pass in federated search: never-loaded galaxies should
  disappear from results while isolation filtering holds.
- Mark one galaxy non-canonical and A/B federated search vs `transfer_memories()` to isolate the
  asymmetry.
- Force tier availability and `WM_SHELTER_MAX_CONCURRENT` down; verify each template's effective
  capability set rather than its declared one; and create N galaxies to measure open descriptors
  per unscoped search (falsifies or confirms the inferred fd mechanism cheaply).

## Open questions

- Where do "47" and "fd exhaustion" come from? No v26 source says either; sessions DB / state-root
  `galaxies.json` were not read (UNVERIFIED).
- Was "reset to 14" an operation or a doc convention? No migration code was found;
  `GALAXY_DEPRECATED` (`galaxy_taxonomy.py:106–114`) maps renames and defers substrate/journals
  merges (`:112–113`).
- Is `is_galaxy_isolated()` meant to guard surprise-gate matching as its docstring claims
  (`galaxy_class.py:149–153`)? Only search and mining callers were found.
- Did any v26 version validate compartment values fail-closed (matrix L63's v4.3.0)? Not in the
  v26 package or its CHANGELOG.
- Did retrieval ever consume `galaxy_gating` weights? `apply_to_results()`
  (`galaxy_gating.py:250–277`) has no in-repo callers; only the gating control tools are wired
  (`neuro_cognitive.py:88–148`).
