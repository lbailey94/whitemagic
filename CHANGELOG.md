# Changelog

All notable changes to WhiteMagic will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [22.2.0] - 2026-04-26

### Added — Phase 2: Surface Completion
- Recovered browser automation suite (`gardens/browser/`, 2,496 lines) with sync handlers
- `handlers/galactic_dashboard.py`, `handlers/ollama_agent.py` — filled LazyHandler gaps
- Northern Quadrant Grimoire chapters (23-28) expanded to 400+ lines each (avg 484)
- Dashboard API wired to real Gan Ying event bus (removed `random.randint` mock data)
- 10 additional fusion functions (23/28 total, target was 21/28)
- `core/whitemagic/core/bridge/gana.py` — Gana meta-tool dispatch bridge
- Real `SalienceArbiter` with Gan Ying event scoring and temporal decay
- Archive-recovered `simd_unified.py` with Zig probing, Rust fallbacks, 5D KNN
- 7 aspirational tools: `prat_get_context`, `prat_list_morphologies`, `prat_invoke`, `prat_status`, `navigate_grimoire`, `get_session_context`, `consult_wisdom_council`

### Added — Phase 3: Cognitive Differentiation (Wild Ideas)
- **Neurotransmitter Vectors** (`core/monitoring/neurotransmitter_vector.py`) — 7-dimension biochemical vector (dopamine, oxytocin, serotonin, cortisol, acetylcholine, GABA, glutamate) auto-fed on every `call_tool()`
- **Grimoire as MCP Resource** — 33 dynamic resources (`whitemagic://grimoire/chapter/{01-28}`, quadrant summaries, current chapter) with live state interpolation
- **Memory Dreams as YAML Artifacts** (`core/dreaming/dream_artifacts.py`) — captures low-confidence creative bridges from bicameral reasoner; nightly consolidator promotes/expires dreams
- **Jaynes Voice Audit** (`core/governance/voice_audit.py`) — claim/ledger cross-check scanner with `QuarantineManager` session isolation; wired into `unified_api.call_tool()`
- **Corpus Callosum Bus** (`core/intelligence/corpus_callosum.py`) — multi-round bicameral debate (max 3 rounds, tension threshold escalation); `LeftHemisphereAgent` + `RightHemisphereAgent` event listeners

### Changed
- `dispatch_table.py`: 443 dispatch tools, 471 callable tools
- `prat_mappings.py`: full coverage of all dispatch tools
- Test suite: 2,154 passed, 66 skipped, 0 failed (+91 from v22.0.0)
- Doc drift checker: 7/7 checks passing

### Fixed
- Gana meta-tools (`gana_*`) now return success instead of `tool_not_found`
- `salience.spotlight` functional after replacing deprecation shim
- All browser tools have working handlers
- Path hygiene tests (`test_strict_mode_blocks_cwd_fallback`, etc.) converted from xfail to real assertions
- Stale v15.0 references in `AI_PRIMARY.md` updated to v22.0.0
- `grimoire/TRUTH_TABLE.md` stale registry bug warning corrected

## [22.0.0] - 2026-04-16

### Added
- Modular installation tiers: `lite`, `mcp`, `cli`, `api`, `embeddings`, `heavy`
- 28 PRAT Gana meta-tools via MCP protocol
- Rust core with PyO3 bindings (memory, search, embeddings, graph, safety)
- WASM compilation target for browser/edge deployment
- Polyglot bridges: Koka, Mojo, Haskell
- CI/CD workflow (GitHub Actions)
- Comprehensive test suite (2259 tests)
- Safety governance: Governor, input sanitizer, rate limiter, constitutional checks
- MCP health endpoint (`whitemagic://health`) for liveness checks
- CLI command registration registry pattern for better decoupling
- Batch embedding backfill script for 93K memories without embeddings
- Exception block narrowing automation scripts

### Changed
- Removed SD card path fallback from `paths.py`
- Consolidated stub packages (removed 6 unused: cache, db, search, monitoring, parallel, plugins)
- Moved frontend to separate project
- Archived `campaigns_public_backup` to legacy
- Removed duplicate contributing guide
- Resonance subsystem consolidated to single module with backward-compatible shim packages
- Fixed 537 except Exception blocks (45% of total) with specific exception types
- Fixed 212 ruff errors automatically
- Updated justfile setup targets to use correct extras
- Fixed Aria manifest paths (290 entries updated)

### Removed
- SD card fallback in path resolution
- Unused stub packages
- Duplicate `docs/community/CONTRIBUTING.md`
- Koka and Rust build binaries (now gitignored)
- Non-existent Rust lazy modules (embeddings, data_lake, bindings) from _LAZY_MODULES
- Incomplete agentic module from lazy loading
