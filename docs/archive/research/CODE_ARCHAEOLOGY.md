# WMgen3 — Code Archaeology: Gen1 ↔ Gen2 (verified survey)

**Date:** 2026-09-16 · **Method:** two independent read-only surveys (this session) with targeted
re-checks; on-disk hash/version verification recorded in
`receipts/PHASE0_VERIFICATION_2026-09-16.md`. **No source tree was modified.**

**Sources surveyed**

| Tree | Identity | Notes |
|---|---|---|
| `~/Desktop/WHITEMAGIC_GEN1_v26.0.3/og_whitemagic` | commit `4d5be091`, tag `v26.0.3` (+7 archive commits) | Python era; `.md` moved to `WHITEMAGIC_GEN1_v26_DOCS/` (166 files); `tags/` holds pure v26.0.1/.2/.3 exports |
| `~/Desktop/WHITEMAGIC/WMv9` | HEAD `cff34a0` (post-9.1.7; 9.1.8 in flight) | Rust workspace, 15 crates, ~242k LOC in `src/` |

This file feeds the Phase-3 capability decomposition and exists to defeat number-drift — the
single most repeated Gen1 failure mode.

---

## 1. Headline findings

1. **Gen1 count drift reproduced:** "875 dispatch entries" is one of *four+* mutually
   inconsistent counts in the same tree (851 composed dispatch measured, 879 `TOOL_REGISTRY`,
   849 in docs, 829/801 in `Dockerfile` which also advertises v25.2.0).
2. **Gen1 engine consolidation claim verified exactly:** 28 canonical engines absorbing 44
   sub-engines + 5 affiliated = **77 named concepts**.
3. **Gen1 "emergence" was partly simulacra:** 5 hardcoded detectors + `random.uniform` novelty
   scores — the cautionary datum behind Gen3's "construct conditions, don't simulate emergence".
4. **New (not in the conversation transcript): Gen1 actually compiled `arrow` and `iceoryx2`** in
   its Rust bridge (`whitemagic-rust`, default features `["python","arrow","iceoryx2"]`).
   Gen2 dropped iceoryx2; Gen3's transport plan is a re-adoption question, not novelty.
5. **Gen2's two-layer engine reality confirmed:** 28 catalog entries are *metadata*; only 5
   engines execute in the Citta loop; `SkillForge` has no implementation.
6. **Gen2 honesty correction:** the canary subsystem exists but is **not wired** into the
   dispatch path, and no "no-op store" canary exists in code (only lineage documentation).
   Gen3's Phase-0 closure tests must actually be live, or Closure 1 is theater.
7. **Gen3 concepts absent in Gen2 code:** memory star / thought star, hyperedges, generalized
   projection spaces, iceoryx2, PAR benchmark, SkillForge. `constellation.detect/list` exists.

---

## 2. Gen1 anatomy (verified)

- `VERSION:1` = `26.0.3`; full package under `core/whitemagic/` with 72 subdirs; runtime stores
  are SQLite per galaxy: `WM_ROOT/users/<user>/galaxies/<galaxy>/whitemagic.db`
  (`config/paths.py:141-143`, schema `core/memory/sqlite_schema.py:79`, FTS5
  `sqlite_backend.py:290`).
- 36 memory modules import `sqlite3`. Session turns are stored as `Memory` records in the
  `sessions` galaxy (`core/memory/session_recorder.py:57-121`).
- `polyglot/` held Go/Zig/Haskell/Julia/Koka/Elixir trees; `sdk/typescript/` with 9 sources;
  `mcp-package/` distribution shim; `justfile` + `Makefile`; `demos/` (4 scripts).
- Rust sidecar: `core/whitemagic-rust/` (`Cargo.toml:29` default features include `arrow`,
  `iceoryx2`; FFI bridge `src/ffi/ipc_bridge.rs`) — later-generation forward pressure inside
  Gen1 itself.

## 3. Gen1 gardens (verified)

| System | Evidence | Count |
|---|---|---|
| `BaseGarden` ABC + 4D `CoordinateBias` | `gardens/base_garden.py:21-46` | — |
| Config registry `EMOTIONAL_GARDENS` | `gardens/garden_config.py:29-105` | **26** |
| Config registry `FUNCTIONAL_GARDENS` | `gardens/garden_config.py:110` | **5** (browser, connection, dharma, synthesis, sangha) |
| Registered garden modules | `gardens/__init__.py:35-64` ("28-fold gardens (complete)") | **28** |
| `GardenWeaver` | `integration/garden_weaver.py:29,78,231` | — |
| `GardenResonanceMatrix` singleton | `gardens/cross_pollination.py:20,149,162` | — |
| 5-mode `GardenRouter` (courage/wisdom/play/grief/mystery + Brier calibration) | `core/evolution/garden_router.py:22-89,211-239` | 5 regimes |
| Gana↔garden registry | `core/intelligence/garden_gana_registry.py:57,75+,384-410` | 28 |

Key archaeology: the Bitter Lesson audit had already reduced emotional gardens to **memory
namespaces** (`gardens/garden_config.py:3-5`, replicated in 23 garden docstrings) — Gen1 was
already trying to become a field.

## 4. Gen1 engines (verified)

- Registry: `core/whitemagic/core/engines/registry.py:91` + fallback `:94-323`;
  count test `core/tests/unit/systems/test_engine_registry.py:16-17`.
- Parsing the registry's `absorbs=(…)` / `affiliated_engines=(…)` fields yields **44 absorbed +
  5 affiliated** around **28 canonical** slots = 77 named engine concepts. Affiliated:
  Interaction, Metaplasticity, Persona, Symbolic, Hologram engines.
- Canonical slots pair engine↔garden (e.g. Export/courage, Resonance/stillness, Sanitization/
  healing, … Kaizen/adventure; `registry.py:94-323`).
- **Emergence:** exactly 5 hardcoded detectors in `core/resonance/emergence_tuned.py:31-89`;
  novelty/practical values from `random.uniform` in
  `core/patterns/emergence/dream_state.py:241-242`, batches ≤5 (`:180-188`). Name ≠ mechanism.
- **Identity:** two JSON stores — `network_state.py:98` (`agent_identities.json`),
  `self_naming_threshold.py:100` (`emergent_identities.json`); 5 dispatch entries in
  `tools/dispatch_agents.py:47-51`; minimal test surface (`test_network_state.py`). The
  "2 fixtures" phrasing in the transcript is best read as *two identity stores*.
- Retention: `core/memory/mindful_forgetting.py:47-332` (multi-signal retention engine).
- Dreams: 12-phase cycle (`core/dreaming/dream_cycle.py:46`; `registry.py:274`).

## 5. Gen1 tool surface (measured, not narrated)

| Mode | Mechanics | Count |
|---|---|---|
| Seed | `WM_MCP_PRAT=2` → single `wm` meta-tool (`core/mcp/tool_surface_lean.py:188-192`) | 1 |
| PRAT | `WM_MCP_PRAT=1` → 28 Gana tools + `wm` (`tool_surface_lean.py:196-229`) | 29 |
| Lite | `WM_MCP_LITE=1` (`runtime_status.py:29-45`); `CORE_TOOLS` frozenset (`dispatch_table.py:408,513-528`) | 128 |
| Classic | `WM_MCP_PRAT=0` (`cli/init_command.py:200,242`) | full table |

Measured via import: `DISPATCH_TABLE` = **851**, `TOOL_REGISTRY` = **879**,
`AUTHORED_TOOL_REGISTRY` = **878**, GANA_NAMES = 28; docs variously 849/876/877; Dockerfile
says 829/801 and v25.2.0 (`Dockerfile:2,11-13`). **Lesson: counts must be generated, not
authored** — Gen2's `wm contract` is the direct descendant of this pain.

## 6. Gen1 governance (verified)

- Governor: forbidden regexes incl. `rm -rf /` (`core/governor.py:152-175`), dangerous patterns
  (`:180-197`), protected paths (`:214-229`), confirmation on dangerous operations (`:500-506`).
- Dharma rules engine with `bitter_lesson: durable|temporary|adaptive` metadata per rule
  (`dharma/rules.py:88,128-136,243-319,593`); Karma ledger (`dharma/karma_ledger.py:166-273`).
- **Firebreak: confirmed absent** (whole-tree search). It was a design doc, not code — Gen2's
  default-armed Firebreak is the first real implementation (`wm-governance/src/firebreak.rs`).
- Bounded autonomy existed: `StopConditions` (max 3600 s, 100 iterations, 4096 MB, 80% CPU) and
  `BoundedExecutor` (`core/consciousness/autonomy.py:26,68`).
- "54k deletion" constant: **not in code**; the incident lives in lineage/session history. Gen2's
  bulk-scope law (`firebreak.rs:220 SCOPE_REGISTRY`) is the derived mechanism.

## 7. Gen1 tests (verified)

- `test_*.py`: **511** tree-wide; **495** under `core/tests/`.
- Test functions: `grep -rE "^\s*(async )?def test_" core/tests` = **8,872 exactly** (8,884
  tree-wide). Property-based tests: 2 files / 7 tests (`hypothesis`) — thin despite the count.
- Interpretation stands: test *volume* didn't prevent a no-op store, registry drift, or
  zombie loops; **Gen2's fewer tests are attached to invariants** (canaries, contracts,
  zero-egress proofs, external-audit acceptance).

## 8. Gen2 anatomy (verified)

Workspace `Cargo.toml:3-19`; version `Cargo.toml:28` = `9.1.7`. `src/` LOC by crate
(approximate): wm-tools 66.7k · wm-cognitive 36.6k · wm-mcp 30.6k · wm-memory 27.5k ·
wm-bicameral 24.4k · wm-governance 15.3k · wm-sangha 9.9k · wm-dispatch 7.8k · wm-core 6.2k ·
wm-substrate 5.9k · wm-simulation 4.8k · wm-selfmodel 2.5k · wm-polyglot 1.7k · wm-workspace
1.5k · wm-conformal 1.0k.

Purpose statements: wm-conformal = uncertainty quantification; wm-bicameral = dual-hemisphere
paired reasoning + consensus; wm-selfmodel = predictive introspection + confidence calibrator
(<0.5 confidence blocks writes); wm-simulation = Monte Carlo/forecasting/Brier-Murphy.
`polyglot/{julia,haskell,zig,koka}` directories exist but are **empty**; Julia is available
only behind the `jlrs` feature of `wm-polyglot`.

## 9. Gen2 gardens & engines (verified)

- Gardens: `crates/wm-cognitive/src/gardens.rs` — `GARDEN_CATALOG` `:155`, count **29** = 28
  canonical + `browser` (integrity test `:1152`). `Coordinate5D` `:14-25` (x logic↔emotion,
  y micro↔macro, z past↔future, w gravity, v vitality). `GardenResonanceEngine` `:951-1144`:
  50% resonance cascade, 30% dampening (`:1024-1052`), **300 s half-life decay** (`:974,1013-1022`),
  5D centroid (`:1054-1085`), Shannon balance entropy (`:1108-1118`). Daemon wiring
  `crates/wm-mcp/src/daemon.rs:305,652-694`.
- Engines: `crates/wm-cognitive/src/alchemical_round.rs` — `ENGINE_CATALOG` **28** entries
  (`:86-319`; completeness test `:414-439`), stage metadata Nigredo→Rubedo. The "full round"
  (`:370-406`) computes frictions/clusters/synapses/invariants — **it does not dispatch 28
  implementations**. Executable core: `citta_engine.rs:605-609` registers **5** engines —
  Kaizen (Perception), Prescience + Serendipity (Contemplation), Foresight (Action), Apotheosis
  (Reflection); phase-count test `:740-743`.
- `SkillForge`: catalog metadata only (`alchemical_round.rs:247-253`); no implementation found.
- Constellations: `wm-tools/src/expansion/constellation.rs` (`constellation.detect/list`, 5D
  clustering); topology example `crates/wm-tools/examples/constellation_topology.rs:7` mentions
  "hyperedge" in a doc comment only — no type.

## 10. Gen2 tool surface (verified)

- **9 exposed MCP tools**: `wm` router + 8 direct handles
  (`crates/wm-mcp/src/server.rs:3155-3415`; emitted list `:3377-3415`).
- Curated internal routes: **59** per `docs/V9_3_Q03_ACCEPTANCE.md:53-59` (doc-sourced; final
  registry 63). No code constant — generated at build.
- Route/schema contract v0 (9.1.7): CHANGELOG `:74` + `docs/V9_1_7_SCOPE_2026-09-15.md:30-31`
  state **302 routes / 70 declared / 232 undeclared**; generator
  `crates/wm-mcp/src/contract.rs:65-124`; `wm contract --check` (`bin/wm.rs:1799-1830`).
  HEAD's regenerated manifest reads 302/85/217 (post-release commits `62936b6`, `fd24acc`) —
  declarations are growing between releases; **quote the release, not HEAD, when citing 9.1.7.**
- `wm contract` verified working on this machine (`wm 9.1.7`, CLI present).

## 11. Gen2 memory & storage (verified)

- LMDB 0.8 + Tantivy 0.26 (`wm-memory/Cargo.toml:28-30`); named DBIs incl. episodic,
  embedding_cache, revisions, attestations, cold_storage (`store.rs:481-487`); galaxy DBs
  (`store.rs:272-286,713-716`); 16 galaxies incl. `Telemetry` (`wm-core/src/galaxy.rs:11-49`).
- Readonly modes: `open_readonly` (`store.rs:424`), `open_inspection` (MDB_NOLOCK|MDB_RDONLY
  `:489-520`), `preservation_readonly` (`server.rs:163,597-602`); server write gate
  `wm-dispatch/src/pipeline.rs:458-466`.
- Backup/restore: `wm backup` → whole store root + SHA256SUMS (`bin/wm.rs:475-489,2333-2363`);
  `wm restore` verifies + replaces (`:490-499,2374-2545`); seal is HMAC-only over the LMDB
  subtree (`:424-444`, `seal.rs`) — matches the 9.1.6 audit's finding on the integrity boundary.
- Index consistency: `index_ok`/`index_drift` classification (`wm-mcp/src/status.rs:29-36,
  297-335`), heal paths (`reindex.rs:93,160,199,318,540-546`) — the 9.1.7 answer to the
  crash-vs-index divergence found in the 9.1.6 audit.
- Cold rotation: `cold_storage.rs` (compress/digest/thaw `:195-232,577-855,879`),
  `galaxy.cold_rotate` tool (`wm-tools/src/lib.rs:5535`).

## 12. Gen2 governance (verified)

| Mechanism | Status | Evidence |
|---|---|---|
| Firebreak | **implemented, armed by default** | `firebreak.rs:62-65,75,122,139,770-772`; pipeline `pipeline.rs:162-217,489` |
| Yama / resource rules | implemented (120 writes/min default; health-scaled) | `resource_rules.rs:26-48,267-277`; `pipeline.rs:559` |
| Yama observe/notify bridge | `EventType::ActuationNotify = 236`; telemetry observation records | `wm-cognitive/src/resonance/event_type.rs:363`; `docs/TELEMETRY.md:16` |
| Landlock | v0 whole-process; v1 scoped executor (gated; memory.* batch first) | `landlock_sandbox.rs:1-50`; `sandbox_exec.rs:51-178` |
| EffectRows | typed effects incl. destructive/sandbox/cost | `wm-core/src/effects.rs:94-137` |
| Compartments | galaxy read/write checks fail closed | `wm-core/src/context.rs:132,167`; `mandala.rs:123-193` |
| Canaries (deception) | **implemented but not wired** — only consumer is decoy shell | `canary_tokens.rs:46-250,283` |
| No-op-store canary | **not in code**; documented only in lineage | `docs/lineage/MEMOIR_LAYER.md:24` |
| Homeostasis veto | confidence <0.5 blocks writes; escape hatch env | `pipeline.rs:465-480`; `HONEST_GAPS_2026-09-14.md:62` |
| Telemetry | local schema, display-only, `transport: none` | `docs/TELEMETRY.md:1-8,49-54` |
| Zero-egress proof | script + release-cadence gate | `scripts/zero_egress_test.sh`; `RELEASE_CADENCE.md:29` |
| Daemon/request separation | serve = dispatch-only; daemon owns cycles | `DAEMON_SERVE_COEXISTENCE.md:1-30` |

**Consequence for Gen3:** the Charter's Closure 1 says "enforced by static write-path analysis +
runtime canaries". Gen2 shows canaries that exist but don't fire are worth nothing; Gen3's
Phase-0 gate must demo a *live* refusal (the pre-reg's H6 canary).

## 13. Gen2 epistemic machinery (verified)

- Abstention: `{status:"insufficient_evidence", reason:"no_results_above_floors",
  scope:"retrieval"}` (`memory_ops.rs:1783-1789`; contract test `abstention_contract.rs`).
- Evidence bundles: per-result id/galaxy/reason/source_time/history/digest/visibility +
  representation, truncation, scrub, `exact_read_available` (`memory_ops.rs:30-140,1783`).
- Claims ledger: local 32 claims (19/1/12, 434.9 pts), **Brier 0.078** underconfident (−0.215);
  merged register 96 rows; site register 101 (`CLAIMS_LEDGER.md:3-46`). Claim records persist
  per store (`claims_ledger.json`); calibration includes Murphy decomposition
  (`wm-simulation/src/calibration.rs:34-89`).
- Prescience = the same runtime ledger (`wm-simulation/src/claims.rs:1-11`).
- `LINEAGE_LEDGER.md`: verdict vocabulary `folded/partial/missing/obsolete-by-design`;
  ~49 adjudicated rows. `CAPABILITY_LEDGER.md`: SHIPPED/EXPLAINED/STALE/QUEUED rows.
- `HONEST_GAPS_2026-09-14.md` (internal): mesh trust, at-rest HMAC-only, retrieval ceiling
  R@1 .86 turn-level (not answer-level), **AHIMSA strict-mode coordination contract untruthful**
  (:24), B4 sandbox unimplemented. 9.1.8 landed the AHIMSA truth-up in the working tree
  (`CHANGELOG.md:8-46`; commit `42cb1f5`: dedicated coordination effects, strict refusal,
  read-only ledger reads).

## 14. Gen2 benchmarks (verified)

- MemoraStrict harness `scripts/memorastrict_bench.py` + generator `memorastrict_gen.py`;
  manifest: 5 seeds, 10 categories (T1–T10), 20 sessions, noise 0.8, **215 questions**.
- Category semantics per `docs/V6_BENCHMARK_DESIGN.md`: T1 Temporal Supersession `:169`,
  T2 Abstention, T3 Multi-hop, T4 Distractor, T5 Consolidation, **T6 Memory Budget `:255`**,
  T7 Scale, T8 Contradiction Detection `:282`, T9 Preference Drift, T10 Cross-Session Synthesis.
  T6 questions are T1-derived under budget constraint
  (`memorastrict_gen.py:752-763` relabels `T1_`→`T6_`).
- Verified seed composition (seed1): T8=3, T1=4, T6=4, T9=12, total **43/seed** → the
  pre-registration's 15/40 counts are exact.
- Canonical retrieval: **R@1 0.86 / R@5 1.00 / MRR 0.9233** (50-q default route;
  `docs/V9_2_EXECUTION_STRATEGY.md:43`, `RELEASE_READINESS.md:6`). T3 strict-mode: 0/3 hit@1
  documented (`V9_3_Q11_HARNESS_VALIDATION.md:110-126`) — the honest gap Gen3 inherits.
- PAR (Persistent Agent Reliability) benchmark: **no implementation in-repo**; referenced only
  in strategy docs — it remains a Gen3-adjacent research lane.

## 15. Gen3-relevant presence/absence in Gen2

| Concept (DESIGN_CANON §) | Presence in WMv9 today |
|---|---|
| Memory star / thought star / stellar lifecycle (§3.3–3.4) | **absent** (no type, no docs) |
| Hyperedge relations (§3.5) | **absent** (doc-comment only in an example) |
| Constellations (§3.5) | present as tools (`constellation.detect/list`), 5D clustering |
| Generalized projection spaces (§3.3) | two coord systems coexist (6D holographic, 5D garden); no abstraction |
| Cognitive Physics regimes / temperature (§4) | primitives present (activation/decay/propagation); regime model absent |
| Garden mixtures / learned resonance (§7) | profiles + engine present; mixture/eigenmode learning absent |
| Engine recipes / planner compilation (§6–7) | absent (5 executable engines; catalog metadata) |
| Recall compiler / yoga planner (§6) | absent (hybrid recall exists as fixed pipeline) |
| Arrow working sets (§9) | optional via LanceDB feature; not used as cognitive batch layer |
| Julia experimental lab (§9) | `wm-polyglot` + `jlrs` feature; live `polyglot/julia` tree empty |
| iceoryx2 transport (§8) | **absent in Gen2**; present in Gen1's Rust bridge (default feature) |
| Metabolism metric M (§10) | absent (telemetry is local, display-only) |
| Geneseed / soma-germline (§10) | absent (deferred by scaffold decree) |

## 16. Discrepancy ledger (claim → measured → ruling)

| Claim as narrated | What the trees show | Ruling |
|---|---|---|
| "875 dispatch entries (AST-verified)" | 851 composed / 879 registry / 878 authored; docs 849/876/877; Dockerfile 829–801 | **drift demonstrably real**; cite measured + note variance |
| "47 galaxies at collapse" | 14 canonical constants in code; 47 = runtime DB count in memory core | historical runtime fact, not taxonomy fact |
| "28 engines absorbed 44 + affiliated 5" | verified exactly (77 concepts) | confirmed |
| "8,872 test functions" | verified exactly | confirmed |
| "Emergence: 5 hardcoded patterns + random novelty" | confirmed; "284 runs / zero output" lives in lineage history, not code | confirmed (code) / historical (runs) |
| "Identity registry: 2 test fixtures" | two JSON identity stores; 1 pytest fixture | reword to "two identity stores, minimal tests" |
| "Firebreak never existed in Gen1" | confirmed absent | confirmed |
| "54k deletion → confirmation + bulk-scope law" | no code constant; incident in lineage; bulk-scope law exists in Gen2 | mechanism confirmed in Gen2, constant is historical |
| "Gen2: 28-engine catalog is specification; 5 execute" | confirmed | confirmed |
| "SkillForge compiles tool patterns into skills" | metadata-only | **aspiration, not implementation** |
| "59 curated internal routes" | doc-sourced acceptance record; registry 63 | quote source, date it |
| "T6 = supersession" | T6 = Memory Budget (T1-derived questions) | corrected in PRE_REGISTRATION |
| "Gen2 detects no-op stores / canaries" | canary module unwired; no store canary in code | **do not claim**; Gen3 must wire it |
| "iceoryx2 as future transport" | Gen2 none; Gen1 compiled it | verify Gen3 need before readoption |

## 17. Implications for WMgen3

1. **Phase 3 verdict vocabulary is usable as-is** (`COMPOSES CLEANLY · …`): the archaeological
   data above gives each Gen2 capability a starting row.
2. **Generation rule confirmed:** Gen2 = Gen1 after selection — same load-bearing concepts
   (Dharma/karma/Citta/Gan Ying/retention/coordinates/Ganas/dreams/profiles), fewer organs,
   stronger laws. Gen3 inherits the burden of proof for anything it wants back.
3. **Counts must be generated.** Any WMgen3 doc quoting a count should cite the generating
   command/file, per `wm contract` precedent.
4. **Closure enforcement must be live.** The unwired canary is the exact failure mode Closure 1
   exists to prevent; Phase-0 gates require a demonstrated refusal, not a module's existence.
5. **The A/B control is sound:** control binary hash, tag commit, corpus hashes, and harness
   hashes were independently re-verified 2026-09-16 (see verification receipt).
