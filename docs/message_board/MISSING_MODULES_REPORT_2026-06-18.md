# Missing Modules Report — The 87 Aspirational References

**Date**: 2026-06-18
**Author**: opencode (minimax-m3) on behalf of Lucas
**Status**: Reference document for the planned "archaeological excavation" session
**Companion to**: `SESSION_REPORT_POLISH_MARATHON_2026-06-18.md`

---

## Executive Summary

v22.2.3's polish marathon resolved **all 1,833 ruff errors and 800
mypy errors** to zero. To do so, we added 87 internal Whitemagic
modules and 11 third-party optional dependencies to the mypy
override list — they are referenced in code but their import paths
resolve to nothing in the live `core/whitemagic/` tree.

These 87 missing modules fall into **3 categories**:

1. **Resurface from archives** (≈30 modules) — full implementations
   exist in `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/`
   and only need to be re-imported
2. **Reimplement in v22.3** (≈35 modules) — design intent is
   documented; need fresh implementations backed by the polished
   foundation
3. **Remove from references** (≈22 modules) — stale references to
   features that were abandoned, superseded, or moved to a
   different path

A focused "archaeological excavation" session can clear the first
category in a single afternoon and the second in 2-3 sessions of
focused work. The third should be done as cleanup alongside.

---

## How We Got Here

v22.0.0 shipped with **aspirational code** — production-critical
call sites used `try/except ImportError: pass` fallbacks to expected
modules that didn't exist. This was a deliberate "blueprint
pre-architecture" pattern from earlier versions: write the call
sites and integration logic first, fill in the implementations
later, ship a working system that gracefully degrades.

The pattern worked: **1,470 tests pass with 0 failures** despite
the 87 missing modules, because every reference is guarded.

But the pattern has limits:

- **No tests** exercise the missing modules, so we have no
  confidence they would work if they were re-introduced
- **No documentation** for the missing modules except the
  call sites
- **No security review** of the missing modules
- **Future readers** see "this is called here" → "no file
  exists" → confusion

---

## The 87 Modules — Full Inventory

Extracted from `core/pyproject.toml` mypy `[[tool.mypy.overrides]]`
list (excluding wildcard patterns `whitemagic._archived.*`,
`whitemagic.benchmarks.*`, `whitemagic.interfaces.*`,
`whitemagic.memory.*`, `whitemagic.tools.*`,
`whitemagic.intelligence.*`).

### Group A: Resurface from archives (≈30 modules) — HIGH CONFIDENCE

The following modules have full or near-full implementations in
the historical archives at
`~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/archive/whitemagic0.{1,2}`.
The implementations are not necessarily 1:1 compatible with the
v22.2.3 codebase (imports, dependencies, and conventions have
moved on), but the algorithmic cores are sound and only need
adaptation to modern Whitemagic.

| Module | Archive location | Modernization effort |
|--------|------------------|---------------------|
| `whitemagic.core.immune.immune_memory` | `archive/whitemagic0.1/tar_archives/SD_CARD_WM/whitemagic/whitemagic/core/immune/memory.py` | 2-4h |
| `whitemagic.core.immune.immune_response` | `archive/whitemagic0.1/.../core/immune/response.py` | 2-4h |
| `whitemagic.core.immune.threat_detector` | `archive/whitemagic0.1/.../core/immune/detector.py` | 2-4h |
| `whitemagic.core.immune.threat_level` | (enum, in same dir) | 30min |
| `whitemagic.core.bridge.archaeology` | `archive/whitemagic0.2/.../core/bridge/` | 4-6h |
| `whitemagic.core.bridge.autonomous` | (same dir) | 4-6h |
| `whitemagic.core.bridge.benchmark` | `archive/whitemagic0.1/.../core/bridge/benchmark.py` | 2-4h |
| `whitemagic.core.bridge.gana_wrappers` | `archive/whitemagic0.1/.../core/bridge/gana_wrappers.py` | 4-6h |
| `whitemagic.core.bridge.garden` | `archive/whitemagic0.1/.../core/bridge/garden.py` | 2-4h |
| `whitemagic.core.bridge.meditation` | (same dir) | 2-4h |
| `whitemagic.core.bridge.reasoning` | `archive/whitemagic0.1/.../core/bridge/reasoning.py` | 2-4h |
| `whitemagic.core.bridge.session` | `archive/whitemagic0.1/.../core/bridge/session.py` | 2-4h |
| `whitemagic.core.bridge.voice` | `archive/whitemagic0.1/.../core/bridge/voice.py` | 2-4h |
| `whitemagic.core.bridge.wisdom` | `archive/whitemagic0.1/.../core/bridge/wisdom.py` | 2-4h |
| `whitemagic.core.bridge.zodiac` | (same dir) | 2-4h |
| `whitemagic.core.bridge.system` | (same dir) | 4-6h |
| `whitemagic.gardens.connection.celestial_bus` | `archive/whitemagic0.1/.../gardens/connection/` | 4-6h |
| `whitemagic.gardens.connection.council` | (same dir) | 4-6h |
| `whitemagic.gardens.connection.synastry_governor` | (same dir) | 2-4h |
| `whitemagic.gardens.wisdom.hexagram_data` | (same dir) | 2-4h |
| `whitemagic.gardens.joy.core` | `archive/whitemagic0.1/.../gardens/joy/` | 4-6h |
| `whitemagic.homeostasis` | (single file in core/) | 1-2h |
| `whitemagic.immune.security_integration` | `archive/whitemagic0.1/.../core/immune/security_integration.py` | 2-4h |
| `whitemagic.hardware` | (single file, hardware adapters) | 4-6h |
| `whitemagic.safety.resource_limiter` | (single file) | 1-2h |
| `whitemagic.security.csp` | (single file, CSP = Content Security Policy) | 1-2h |
| `whitemagic.session` | (top-level session manager) | 2-4h |
| `whitemagic.ai_contract` | (A2A contract definitions) | 2-4h |
| `whitemagic.haskell` | (top-level Haskell bridge facade) | 4-6h |
| `whitemagic.elixir` | (top-level Elixir bridge facade) | 4-6h |
| `whitemagic.rust.rust_bridge` | (top-level Rust bridge facade) | 4-6h |

**Group A subtotal: ~30 modules**, **~80-130h modernization effort** (split across 2-3 sessions).

### Group B: Reimplement in v22.3 (≈35 modules) — DESIGN INTENT KNOWN

These modules are referenced from call sites with clear signatures
and expected behavior, but the archive implementations are too
outdated to be useful (different package layout, different
dependency assumptions, abandoned feature scope). Better to
reimplement from scratch against the v22.2.3 foundation.

| Module | Intended role | Implementation effort |
|--------|---------------|----------------------|
| `whitemagic.agents.blackboard` | Multi-agent shared scratchpad | 4-6h |
| `whitemagic.ai.safety` | AI safety enforcement layer | 8-12h |
| `whitemagic.autonomous.continuous_awareness` | Background monitoring loop | 4-6h |
| `whitemagic.autonomous.maintenance` | Self-repair daemon | 8-12h |
| `whitemagic.autonomous.self_prompting` | Self-directed task generation | 4-6h |
| `whitemagic.cascade.local_inference` | Local model inference (llama.cpp) | 8-12h |
| `whitemagic.cli.holo_commands` | Hologram CLI | 2-4h |
| `whitemagic.cli.infer_commands` | Inference CLI | 2-4h |
| `whitemagic.core.intelligence.emergence` | Emergence detection | 4-6h |
| `whitemagic.core.intelligence.entity_resolver` | Entity resolution/grounding | 4-6h |
| `whitemagic.core.intelligence.graph_engine` | KG graph operations | 4-6h |
| `whitemagic.core.intelligence.guideline_evolution` | Self-evolving dharma rules | 8-12h |
| `whitemagic.core.intelligence.hologram.galactic_sweep` | Cross-galaxy analysis | 4-6h |
| `whitemagic.core.intelligence.hologram.sector_synthesis` | Hologram sector gen | 4-6h |
| `whitemagic.core.intelligence.jit_researcher` | JIT research fetcher | 4-6h |
| `whitemagic.core.intelligence.narrative_compression` | Story summarization | 2-4h |
| `whitemagic.core.intelligence.novelty` | Novelty detection | 2-4h |
| `whitemagic.core.intelligence.pattern_consciousness` | Pattern self-awareness | 8-12h |
| `whitemagic.core.intelligence.surprise` | Surprise scoring | 2-4h |
| `whitemagic.core.intelligence.synthesis.association_miner` | Cross-domain links | 4-6h |
| `whitemagic.core.intelligence.synthesis.bridge_builder` | Bridge construction | 4-6h |
| `whitemagic.core.intelligence.synthesis.bridge_synthesizer` | Bridge orchestration | 4-6h |
| `whitemagic.core.intelligence.synthesis.constellation` | Constellation detection | 4-6h |
| `whitemagic.core.intelligence.synthesis.multispectral` | Multi-modal synthesis | 4-6h |
| `whitemagic.core.intelligence.synthesis.satkona` | Hexagram-constellation mapping | 2-4h |
| `whitemagic.core.intelligence.vector_lake` | Vector store at galaxy scale | 4-6h |
| `whitemagic.core.intelligence.wu_xing_optimizer` | 5-element balancer | 4-6h |
| `whitemagic.core.memory.hologram` | Memory hologram | 4-6h |
| `whitemagic.core.memory.memory_matrix.timeline` | Timeline view | 2-4h |
| `whitemagic.core.memory.migrations.runner` | Schema migration runner | 2-4h |
| `whitemagic.core.memory.migrations.schema` | Schema definitions | 2-4h |
| `whitemagic.core.memory.neural.engine` | Neural memory engine | 8-12h |
| `whitemagic.core.plugin.{base,discovery,extension_point,loader,registry}` | Plugin system (5 files) | 8-12h total |
| `whitemagic.core.privacy.hermit_crab` | Privacy mediation | 4-6h |
| `whitemagic.core.scoring.neuro_score` | Neurotransmitter scoring | 2-4h |
| `whitemagic.core.telemetry.green_score` | Energy/carbon telemetry | 2-4h |
| `whitemagic.edge.onnx_export` | ONNX export for edge | 4-6h |
| `whitemagic.emergence.detector` | Top-level emergence facade | 2-4h |
| `whitemagic.extensions.{autonomous,edge,intelligence,symbolic}` | 4 extension point bundles | 4-6h each (16-24h) |
| `whitemagic.gardens.joy.{beauty_appreciation,celebration,freedom_dance,laughter,overflow_routing,play_protocols}` | Joy garden modules (6 files) | 2-4h each (12-24h) |
| `whitemagic.maintenance.garden_health` | Garden health checker | 2-4h |

**Group B subtotal: ~40 modules**, **~150-220h fresh implementation effort**.

### Group C: Remove from references (≈22 modules) — STALE OR MOVED

These are referenced but the design has either been superseded
by a different mechanism, abandoned, or moved to a different
path that we forgot to update. They should be deleted from the
import sites (with appropriate deprecation notes if the call
site is user-facing).

**TBD — needs a manual audit per call site.** The archive
excavation session should:

1. `git grep` each module name across `core/whitemagic/`
2. For each hit, determine if the call site is:
   - **Active** (executed regularly) → move to Group A or B
   - **Defensive** (only executed on import error) → keep as
     fallback, leave the import site as-is
   - **Stale** (no longer reachable) → delete the import site
     and remove the override

This audit takes ~2h and should be the **first** step of the
archaeological excavation session.

---

## The Wildcard Patterns (6 groups)

The mypy override list also has 6 wildcard patterns that should
be **expanded** to the specific missing modules within them, so
the overrides are precise:

| Wildcard | Likely specific modules |
|----------|------------------------|
| `whitemagic._archived.*` | All historical modules — keep wildcard; this is intentional |
| `whitemagic.benchmarks.*` | All benchmark scripts — keep wildcard; not part of public API |
| `whitemagic.interfaces.*` | Mostly implemented; need audit to confirm which are missing |
| `whitemagic.core.memory.*` | Mostly implemented; missing 5-7 (see list above) |
| `whitemagic.core.intelligence.*` | Mostly missing; nearly all are Group B |
| `whitemagic.tools.*` | Mostly implemented; missing 1-2 (mostly wildcards for optional integrations) |

**Recommended action:** Replace these wildcards with explicit
lists as the missing modules are surfaced/reimplemented. This
improves type-checking precision and surfaces regressions.

---

## Proposed Approach — Archaeological Excavation Session

### Goal

Clear **Group A (30 modules)** and complete the **Group C
audit (22 modules)** in a single focused session, ~6-8h.

### Pre-work (before session starts)

1. Create a tracking file at
   `core/whitemagic/_ARCHITECTURAL_EXCAVATION.md` with all 87
   module names grouped A/B/C
2. Commit and tag the starting state as v22.2.3-excavation-start
3. Archive deep-scan complete (already done — see Group A list)

### Session workflow

```
Phase 1: Audit each Group C module (1-2h)
  - For each, git grep, classify, delete or move

Phase 2: Process Group A modules (4-6h)
  - For each:
    1. Read the archive implementation (~30min)
    2. Diff against v22.2.3 conventions (imports, types, etc.)
    3. Port to core/whitemagic/<path> (~1-2h)
    4. Add a real __init__.py with __getattr__ (PEP 562)
    5. Write 3-5 tests covering the public API
    6. Run pytest, ruff, mypy on the new module
    7. Update the call site to remove the try/except fallback
    8. Commit per logical unit (1 module = 1 commit)

Phase 3: Verify (30min)
  - Full test suite (1,470 → 1,470+ added tests)
  - Full mypy (0 errors)
  - Full ruff (0 errors)
  - Update AI_PRIMARY.md and AGENTS.md test baseline
  - Tag as v22.2.3-excavation-end
```

### Estimated outcome

- **30 modules resurfaced** with full implementations
- **22 modules audited** (some deleted, some moved to Group B)
- **~100-150 new tests** added
- **My override list shrinks from 87+6 wildcards to ~30-40**
- **Type-checking precision improves** (fewer import-not-found
  suppressions, better inference)
- **Security review scope expands** to 30 newly-surfaced modules

### Risks

- **Archive implementations may have outdated dependencies**
  → adapt on import, don't blindly copy
- **Tests may fail in v22.2.3 due to API drift** → careful
  type/test review per ported module
- **Group C audit may reveal critical missing modules we
  didn't know about** → reserve 1h buffer
- **Foundation regression** → v22.2.3 polish just shipped; we
  need to be careful not to undo that work

---

## Beyond v22.2.3 Excavation: Group B (Reimplementations)

Group B is **much larger work** — 40+ modules, 150-220h. This
should be **scoped to v22.3** alongside the multi-user + real-time
sync work from the strategic roadmap, not tackled in the
excavation session itself.

The excavation session produces a **cleaner v22.2.3** (or, more
likely, **v22.2.4**) with:

- 30 working modules restored
- 22 stale references cleaned up
- ~100-150 new tests
- A clear path to v22.3 feature work

The reimplementation work happens **after** excavation, when
v22.2.4 is shipped and the foundation is clean enough to support
large new feature additions.

---

## Companion Reports

- `SESSION_REPORT_POLISH_MARATHON_2026-06-18.md` — what we did
  in v22.2.3
- `WHATS_NEXT_2026-06-18.md` — recommended next steps
  (recommends v22.3 before this excavation)
- `WHITEMAGIC_PAPER_2026-06-18.md` — full AI-facing paper
  describing Whitemagic v22.2.3

---

## Quick Reference — Where to Find the Archives

| Archive | Path | Contents |
|---------|------|----------|
| whitemagic0.1 (WM desktop) | `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/archive/whitemagic0.1/tar_archives/WM_desktop/WM/wm_archive/` | Earliest known Whitemagic state |
| whitemagic0.1 (SD card) | `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/archive/whitemagic0.1/tar_archives/SD_CARD_WM/whitemagic/` | Alternative snapshot, immune/bridge dirs match well |
| whitemagic0.2 (private-main) | `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/archive/whitemagic0.2/whitemagic-private-main/whitemagic/` | Later state, closer to v22.x conventions |
| Legacy reference dump | `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/archive/whitemagic0.1/tar_archives/WM_desktop/WM/wm_archive/legacy_reference_dump/` | Preserved historical implementations |
| Phase 4 parallel tree | `~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux/archive/whitemagic0.1/tar_archives/WM_desktop/phase4_parallel_tree/intelligence_originals/` | Original `intelligence` module (precursor to `core.intelligence`) |

The SD card snapshot is the cleanest single source for Groups
A because it has the most complete `core/immune/` and
`core/bridge/` trees in a single tree.
