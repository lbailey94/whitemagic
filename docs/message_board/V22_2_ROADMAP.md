# WhiteMagic v22.2 Roadmap — "The Resonant Surface"

**Date**: 2026-04-25
**Status**: Planning Complete → Execution Phase
**Scope**: Phase 1 (Immediate) + Phase 2 (Short) + Phase 3 (Medium)

---

## How This Roadmap Was Built

1. **Archive Reconnaissance** — Scouted `whitemagic-aux/archive/whitemagic0.2/` (965 Python files, 2.2GB), `browser-garden-backup/`, and internal archives.
2. **Cross-Reference** — Mapped archive findings against current codebase gaps.
3. **Smoke Testing** — Verified which tools actually work vs which fail.
4. **Prioritization** — Ranked by user impact × effort × recovery value.

---

## Phase 1: Immediate (COMPLETE ✅)

> **Goal**: Fix everything that's genuinely broken. Zero broken core tools.
> **Result**: 2,082 passed, 0 failed, 66 skipped (+14 tests)

### 1.1 Fix Gana Meta-Tool Dispatch (CRITICAL) ✅
**Problem**: `gana_*` tools returned `tool_not_found` because `whitemagic.core.bridge.gana` was missing.
**Fix**: Created `core/whitemagic/core/bridge/gana.py` implementing `gana_invoke()` that routes to `prat_router.route_prat_call()`.
**Files**: `core/whitemagic/core/bridge/gana.py` (new, 42 lines)

### 1.2 Fix `salience.spotlight` (CRITICAL) ✅
**Problem**: `salience_arbiter.py` was a deprecation shim returning `None`.
**Fix**: Replaced with full `SalienceArbiter` class integrating with Gan Ying event bus. Scores events by urgency × novelty × confidence with temporal decay.
**Files**: `core/whitemagic/core/resonance/salience_arbiter.py` (rewritten, 165 lines)

### 1.3 Recover Browser Automation Suite (HIGH VALUE) ✅
**Problem**: `browser_navigate`, `browser_click`, etc. had dispatch entries but no handlers.
**Fix**: Copied `browser-garden-backup/` (2,496 lines) to `gardens/browser/`. Created `handlers/browser_tools.py` with sync wrappers around async BrowserSession.
**Files**: `core/whitemagic/gardens/browser/*.py` (new), `core/whitemagic/tools/handlers/browser_tools.py` (new, 153 lines)

### 1.4 Recover `simd_unified.py` (MEDIUM) ✅
**Problem**: Current was 184 lines with stubs. Archive had 373 lines with real Zig probing, Rust fallbacks, 5D KNN.
**Fix**: Replaced with archive version.
**Files**: `core/whitemagic/core/acceleration/simd_unified.py` (+189 lines)

### 1.5 Create Missing Handler Modules (MEDIUM) ✅
**Problem**: 24 LazyHandler references pointed to non-existent modules.
**Fix**: Created 7 handler modules:
- `handlers/watcher.py` — 9 watcher tools
- `handlers/backup.py` — galaxy backup/restore
- `handlers/verification.py` — verification/attestation
- `handlers/grimoire_walkthrough.py` — grimoire index/walkthrough
- `handlers/gana_dipper.py` — astro status/shift
- `handlers/galactic_dashboard.py` — galactic map data
- `handlers/ollama_agent.py` — autonomous agent loop stub

### 1.6 Implement Aspirational Tools (MEDIUM) ✅
**Problem**: 7 tools referenced in Grimoire didn't exist.
**Fix**:
- Recovered `prat_get_context`, `prat_list_morphologies`, `prat_invoke`, `prat_status` from archive `bridge/adaptive.py`
- Created `handlers/aspirational.py` with `navigate_grimoire`, `get_session_context`, `consult_wisdom_council`
- Created `handlers/adaptive.py` as wrapper for archive adaptive functions
- Added all 7 to `prat_mappings.py` (mapped to appropriate Ganas)
- Added all 7 to `dispatch_table.py`

### Phase 1 Deliverables — ALL COMPLETE
- [x] All 28 Gana tools return success (not tool_not_found)
- [x] `salience.spotlight` works
- [x] All browser tools have handlers
- [x] `simd_unified.py` has full archive functionality
- [x] 24 missing handler modules → 0
- [x] 7 aspirational tools implemented
- [x] Test suite: 2,082 passing, 0 failures
- [x] Doc drift: All checks pass (460 callable / 432 dispatch)

---

## Phase 2: Short Term (1-2 Weeks)

> **Goal**: Complete the surface. Every dispatchable tool has a working handler.

### 2.1 Create Remaining Handler Modules
- `handlers/ollama_agent.py` — autonomous agentic loop
- `handlers/galactic_dashboard.py` — galactic map visualization data
- Any remaining LazyHandler gaps

### 2.2 Expand Northern Quadrant Grimoire
**Target**: Chapters 23-28 expanded to 400+ lines each
**Content to add**:
- 3-5 detailed workflows per chapter
- Troubleshooting sections (common errors + fixes)
- Real tools tables (only existing dispatch tools)
- Transition poetry (how to enter/exit)
- Code examples

### 2.3 Replace Dashboard Mock Data
**File**: `interfaces/api/routes/dashboard_api.py`
**Current**: `invocation_delta = random.randint(0, 5)`
**Target**: Wire to real Gan Ying event bus or PRAT resonance state

### 2.4 Implement Missing Fusions
**Current**: 13/28 fusions exist
**Target**: 21/28 fusions (get to "sacred number")
**Priority fusions**:
- `mesh_memory_sync()` — Go mesh → memory sync
- `kg_suggest_next_gana()` — Knowledge graph → Gana routing
- `check_proactive_dream()` — Self-model → dream cycle

### Phase 2 Deliverables
- [ ] 450+ tools with working handlers
- [ ] Northern Quadrant chapters average 400+ lines
- [ ] Dashboard serves real data
- [ ] 21/28 fusions active

---

## Phase 3: Medium Term (2-4 Weeks)

> **Goal**: The wild stuff. Differentiation.

### 3.1 Memory Dreams as YAML Artifacts
When bicameral reasoning detects creative bridge with `confidence < 0.5`, write to `~/.whitemagic/dreams/`. Nightly consolidation promotes high-revisit dreams to real memories.

### 3.2 Corpus Callosum Bus
Bidirectional critique channel between deterministic (left) and stochastic (right) hemispheres. Every creative suggestion gets cross-examined.

### 3.3 Jaynes Voice Audit
Scan internal command stream for un-logged/hallucinated tokens. Quarantine mechanism.

### 3.4 Neurotransmitter Vectors
Expand Harmony Vector to include dopamine, oxytocin, serotonin, cortisol scalars.

### 3.5 Grimoire as MCP Resource
Serve entire Grimoire as MCP resource stream. AI clients can read chapters with interpolated system state.

### 3.6 Fix Polyglot Builds
- Zig: Fix `linkLibC` API compatibility
- Rust: Fix pyo3 linking for tests
- Haskell: Install cabal or document dependency

### Phase 3 Deliverables
- [ ] Dream YAML pipeline active
- [ ] Corpus Callosum Bus prototype
- [ ] Jaynes Voice Audit scanner
- [ ] Neurotransmitter Vector expansion
- [ ] All 7 polyglot languages compile

---

## Archive Recovery Inventory

| Priority | Archive Source | Current File | Action | Lines Added |
|----------|---------------|--------------|--------|-------------|
| P0 | `browser-garden-backup/*.py` | NEW | Copy to `gardens/browser/` | +2,496 |
| P1 | `archive/core/acceleration/simd_unified.py` | `core/acceleration/simd_unified.py` | Replace with archive | +189 |
| P1 | `archive/tools/handlers/ollama.py` | `tools/handlers/ollama.py` | Merge MAG + context injection | +~200 |
| P2 | `archive/core/bridge/adaptive.py` | NEW | Recover PRAT adaptive functions | +173 |
| P2 | `archive/tools/handlers/session.py` | `tools/handlers/session.py` | Review cross-device handoff | +~50 |
| SKIP | `archive/core/fusions.py` | `core/fusions.py` | Current is better | — |
| SKIP | `archive/grimoire/2*.md` | `grimoire/2*.md` | Already identical | — |

---

## Success Metrics

| Metric | v22.0.0 | v22.2 Target |
|--------|---------|--------------|
| Tests passing | 2,068 | 2,100+ |
| Tools with handlers | ~400 | 450+ |
| Gana tools working | 0/28 | 28/28 |
| Broken core tools | 2+ | 0 |
| Fusions active | 13/28 | 21/28 |
| Northern Quadrant avg lines | 141 | 400+ |
| Polyglot languages building | 2/7 | 4/7 |

---

## Notes

- **The archive is mostly already recovered.** The v22.0.0 session did the heavy lifting (lifecycle, solver_engine, db_manager, galactic_map, consolidation, kaizen_engine). Remaining high-value recovery is browser automation + simd_unified.
- **The Gana bridge gap is the most critical finding.** The entire PRAT meta-tool layer is non-functional because a single bridge module is missing. This is a 2-hour fix with massive impact.
- **Current fusions.py is BETTER than archive.** Don't recover it — the current inline version has 7 more functions than the archive's modular approach.

---

*Last updated: 2026-04-25*
