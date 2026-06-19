# Architectural Excavation — Module Recovery Tracker

**Started**: 2026-06-18 23:17
**Phase 1 (Group C audit)**: 23:17 → 23:48 (31 min)
**Goal**: Resurface, reimplement, or remove aspirational modules.

## Status Legend
- **[A] Active** — call site reachable at runtime
- **[D] Defensive** — only executed on import error
- **[S] Stale** — no longer reachable, candidate for removal
- **[?] TBD** — needs further audit
- **[R] Resurface** — found in archive, can be ported
- **[N] Reimplement** — design intent known, needs fresh code
- **[X] Remove** — stale reference

## Source Archive Priority (CONFIRMED locations)
1. `0.1-SD-card` — `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/archive/whitemagic0.1/tar_archives/SD_CARD_WM/whitemagic/`
   - Has: full `core/bridge/` (13 modules), `core/immune/security_integration.py`, `core/plugin/base.py`, `edge/onnx_export.py`, `homeostasis.py`
2. `0.1-WM-desktop` — `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/archive/whitemagic0.1/tar_archives/WM_desktop/WM/wm_archive/`
   - Has: `ai_contract.py`, `cli/{holo_commands,infer_commands}.py`, `autonomous/continuous_awareness.py`, `gardens/wisdom/hexagram_data.py`
3. `0.2-main` — `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/archive/whitemagic0.2/`
   - Has: `core/memory/memory_matrix/timeline.py` (closest to v22.x)

## Phase 1 (Group C audit) — COMPLETE

### Key finding
**`mcp_api_bridge.py` is broken** — 14 star imports are NOT in try/except blocks.
Confirmed via `python3 -c "from whitemagic.mcp_api_bridge import *"` → 
`ModuleNotFoundError: No module named 'whitemagic.core.bridge.zodiac'`

This contradicts the v22.2.3 session report's claim that the star imports
were "intentional facade pattern." They are unguarded imports that crash
the entire MCP API surface.

## Phase 2 (Group A — Resurface from archives) — 23 found

| Module | Archive | Size | Status |
|--------|---------|------|--------|
| whitemagic.ai_contract | 0.1-WM-desktop | 2.6KB | [R] |
| whitemagic.autonomous.continuous_awareness | 0.1-WM-desktop | 3.5KB | [R] |
| whitemagic.cli.holo_commands | 0.1-WM-desktop | 15.8KB | [R] |
| whitemagic.cli.infer_commands | 0.1-WM-desktop | 4.0KB | [R] |
| whitemagic.core.bridge.archaeology | 0.1-SD-card | 5.1KB | [R] |
| whitemagic.core.bridge.autonomous | 0.1-SD-card | 1.3KB | [R] |
| whitemagic.core.bridge.benchmark | 0.1-SD-card | 0.7KB | [R] |
| whitemagic.core.bridge.gana_wrappers | 0.1-SD-card | 15.1KB | [R] |
| whitemagic.core.bridge.garden | 0.1-SD-card | 4.4KB | [R] |
| whitemagic.core.bridge.inference | 0.1-SD-card | 6.5KB | [R] |
| whitemagic.core.bridge.meditation | 0.1-SD-card | 0.5KB | [R] |
| whitemagic.core.bridge.reasoning | 0.1-SD-card | 3.0KB | [R] |
| whitemagic.core.bridge.session | 0.1-SD-card | 3.5KB | [R] |
| whitemagic.core.bridge.system | 0.1-SD-card | 3.8KB | [R] |
| whitemagic.core.bridge.voice | 0.1-SD-card | 1.3KB | [R] |
| whitemagic.core.bridge.wisdom | 0.1-SD-card | 5.4KB | [R] |
| whitemagic.core.bridge.zodiac | 0.1-SD-card | 2.9KB | [R] |
| whitemagic.core.memory.memory_matrix.timeline | 0.2-main | 8.7KB | [R] |
| whitemagic.core.plugin.base | 0.1-SD-card | 0.8KB | [R] |
| whitemagic.edge.onnx_export | 0.1-SD-card | 10.3KB | [R] |
| whitemagic.gardens.wisdom.hexagram_data | 0.1-WM-desktop | 11.8KB | [R] |
| whitemagic.homeostasis | 0.1-SD-card | 4.8KB | [R] |
| whitemagic.immune.security_integration | 0.1-SD-card | 0.8KB | [R] |

## Phase 3 (Group B — Reimplement) — 35 found

| Module | Notes |
|--------|-------|
| whitemagic.agents.blackboard | Multi-agent shared scratchpad |
| whitemagic.brain | High-level brain facade |
| whitemagic.core.gan_ying | Resonant communication |
| whitemagic.core.immune.immune_memory |  |
| whitemagic.core.immune.immune_response |  |
| whitemagic.core.immune.threat_detector |  |
| whitemagic.core.immune.threat_level |  |
| whitemagic.core.intelligence.emergence |  |
| whitemagic.core.intelligence.entity_resolver |  |
| whitemagic.core.intelligence.graph_engine |  |
| whitemagic.core.intelligence.guideline_evolution |  |
| whitemagic.core.intelligence.hologram.galactic_sweep |  |
| whitemagic.core.intelligence.jit_researcher |  |
| whitemagic.core.intelligence.narrative_compression |  |
| whitemagic.core.intelligence.novelty |  |
| whitemagic.core.intelligence.pattern_consciousness |  |
| whitemagic.core.intelligence.surprise |  |
| whitemagic.core.intelligence.synthesis.association_miner |  |
| whitemagic.core.intelligence.synthesis.bridge_builder |  |
| whitemagic.core.intelligence.synthesis.bridge_synthesizer |  |
| whitemagic.core.intelligence.synthesis.constellation |  |
| whitemagic.core.intelligence.synthesis.multispectral |  |
| whitemagic.core.intelligence.synthesis.satkona |  |
| whitemagic.core.intelligence.vector_lake |  |
| whitemagic.core.intelligence.wu_xing_optimizer |  |
| whitemagic.core.memory.hologram |  |
| whitemagic.core.memory.neural.engine |  |
| whitemagic.core.memory_matrix |  |
| whitemagic.core.privacy.hermit_crab |  |
| whitemagic.core.telemetry.green_score |  |
| whitemagic.elixir |  |
| whitemagic.emergence.detector |  |
| whitemagic.hardware |  |
| whitemagic.haskell |  |
| whitemagic.session |  |
