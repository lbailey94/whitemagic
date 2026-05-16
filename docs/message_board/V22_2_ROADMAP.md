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

## Phase 2: Short Term (1-2 Weeks) — COMPLETE ✅

> **Goal**: Complete the surface. Every dispatchable tool has a working handler.
> **Completed in parallel session**: `2dd17eb`

### 2.1 Create Remaining Handler Modules ✅
- `handlers/ollama_agent.py` — autonomous agentic loop
- `handlers/galactic_dashboard.py` — galactic map visualization data
- All LazyHandler gaps resolved

### 2.2 Expand Northern Quadrant Grimoire ✅
**Result**: Chapters 23-28 average **484 lines** (target: 400+)

### 2.3 Replace Dashboard Mock Data ✅
**Result**: Dashboard wired to real Gan Ying event bus / PRAT resonance state

### 2.4 Implement Missing Fusions ✅
**Result**: **23/28** fusions active (target: 21/28)

### Phase 2 Deliverables
- [x] 450+ tools with working handlers (451 dispatch / 479 callable)
- [x] Northern Quadrant chapters average 400+ lines
- [x] Dashboard serves real data
- [x] 21/28 fusions active

---

## Phase 3: Medium Term (2-4 Weeks) — ALL WILD IDEAS COMPLETE ✅

> **Goal**: The wild stuff. Differentiation.

### 3.1 Memory Dreams as YAML Artifacts ✅
- `DreamArtifact` dataclass + YAML serializer
- Event listener on `CREATIVE_BRIDGE_LOW_CONFIDENCE`
- Nightly consolidator with promote/expire logic
- Tools: `dream.list`, `dream.read`, `dream.promote`, `dream.expire`

### 3.2 Corpus Callosum Bus ✅
- `CorpusCallosumBus` with multi-round debate (max 3)
- `SynthesisArbiter` with tension threshold escalation (>0.9)
- `LeftHemisphereAgent` + `RightHemisphereAgent` event listeners
- Tools: `corpus_callosum.debate`, `corpus_callosum.status`

### 3.3 Jaynes Voice Audit ✅
- `ClaimLog` + `VoiceAuditScanner` with Karma Ledger cross-check
- `QuarantineManager` with session isolation
- Wired into `call_tool()` as claim registration/verification
- Tools: `voice_audit.scan`, `voice_audit.status`, `voice_audit.quarantine_list`

### 3.4 Neurotransmitter Vectors ✅
- 7-dimension biochemical vector (dopamine, oxytocin, serotonin, cortisol, acetylcholine, GABA, glutamate)
- Auto-fed by `call_tool()` on every invocation
- Tools: `neurotransmitter.status`, `neurotransmitter.report`

### 3.5 Grimoire as MCP Resource ✅
- 33 dynamic MCP resources (28 chapters + 4 quadrants + current)
- Live state interpolation (harmony, neurotransmitters, dream phase)

### 3.6 Fix Polyglot Builds — REMAINING
- Zig: Fix `linkLibC` API compatibility
- Rust: Fix pyo3 linking for tests
- Haskell: Install cabal or document dependency

### Phase 3 Deliverables
- [x] Dream YAML pipeline active
- [x] Corpus Callosum Bus prototype
- [x] Jaynes Voice Audit scanner
- [x] Neurotransmitter Vector expansion
- [x] Grimoire MCP resources (33 total)
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

| Metric | v22.0.0 | v22.2 Target | v22.2 Actual |
|--------|---------|--------------|--------------|
| Tests passing | 2,068 | 2,100+ | **2,216** |
| Tools with handlers | ~400 | 450+ | **479 callable / 451 dispatch** |
| Gana tools working | 0/28 | 28/28 | **28/28** |
| Broken core tools | 2+ | 0 | **0** |
| Fusions active | 13/28 | 21/28 | **21/28** |
| Northern Quadrant avg lines | 141 | 400+ | **484** |
| Polyglot languages building | 2/7 | 4/7 | **2/7** *(remaining)* |

---

## Notes

- **The archive is mostly already recovered.** The v22.0.0 session did the heavy lifting (lifecycle, solver_engine, db_manager, galactic_map, consolidation, kaizen_engine). Remaining high-value recovery is browser automation + simd_unified.
- **The Gana bridge gap is the most critical finding.** The entire PRAT meta-tool layer is non-functional because a single bridge module is missing. This is a 2-hour fix with massive impact.
- **Current fusions.py is BETTER than archive.** Don't recover it — the current inline version has 7 more functions than the archive's modular approach.

---

---

## Phase 3: The Wild Ideas — "Cognitive Differentiation" (COMPLETE ✅)

> **Decision**: Implement all five wild ideas in sequence.
> **Rationale**: Each builds on existing systems. No external dependencies. High differentiation value.
> **Archive reconnaissance**: No existing implementations found for neurotransmitters, dream YAML, voice audit, or corpus callosum. Must build fresh. MCP resource infrastructure exists and is functional.

---

### 3.1 Neurotransmitter Vectors (Sequence #1)

**Effort**: 2 days  
**Builds on**: `harmony/vector.py` (HarmonyVector), `intelligence/emotion_drive.py` (DriveCore)

**What**: Expand Harmony Vector with 7 biochemical analogues that make system health intuitive.

| Neurotransmitter | Computational Analogue | Source Signal |
|-----------------|----------------------|---------------|
| Dopamine | Reward prediction error | Expected vs actual tool outcome |
| Oxytocin | Trust / social bonding | Agent cooperation rate, mesh sync success |
| Serotonin | Mood stability | Rolling variance of Harmony Vector |
| Cortisol | Stress / alarm | Error rate, circuit breaker trips, rate limit hits |
| Acetylcholine | Attention / focus | Salience Arbiter spotlight density |
| GABA | Inhibition / calm | Rate of "PROCEED_WITH_CAUTION" from explain_this |
| Glutamate | Excitation / drive | Rate of creative bridges from bicameral reasoner |

**Files to create**:
- `core/whitemagic/core/monitoring/neurotransmitter_vector.py` — `NeurotransmitterVector` dataclass + signal collectors
- `core/whitemagic/tools/handlers/neurotransmitters.py` — `neurotransmitter.status`, `neurotransmitter.report`
- Tests: `tests/unit/test_neurotransmitter_vector.py`

**Integration points**:
- Auto-fed by `call_tool()` on every invocation (like Harmony Vector)
- Displayed in dashboard as "System Biochemistry"
- Fed into Homeostatic Loop for auto-correction decisions

---

### 3.2 Grimoire as MCP Resource (Sequence #2)

**Effort**: 1-2 days  
**Builds on**: `run_mcp_lean.py` (existing `list_resources()` + `read_resource()`)

**What**: Serve Grimoire chapters as dynamic MCP resources with live system state interpolated.

**Current resources** (already working):
- `whitemagic://health`
- `whitemagic://orientation/prologue`
- `whitemagic://orientation/ai-primary`
- `whitemagic://orientation/server-instructions`
- `whitemagic://orientation/system-map`
- `whitemagic://workflow/*`

**New resources to add**:
- `whitemagic://grimoire/chapter/{1-28}` — Individual chapters with live state
- `whitemagic://grimoire/quadrant/{eastern,southern,western,northern}` — Quadrant summaries
- `whitemagic://grimoire/current` — The chapter most resonant with current system state

**Example dynamic response** for `whitemagic://grimoire/chapter/14`:
```yaml
chapter: 14 — Abundance (Feng)
garden: joy
current_harmony: 0.87          # live from HarmonyVector
active_dream_phase: NARRATIVE  # live from DreamCycle
recommended_tool: dream        # based on current state
wu_xing_boost: Fire +15%       # live from fusions
last_consolidation: 2026-04-25T22:00:00Z
narrative_memories_compressed_today: 3
```

**Files to modify**:
- `core/whitemagic/run_mcp_lean.py` — Add Grimoire resources to `list_resources()` and `read_resource()`
- `core/whitemagic/grimoire/resource_renderer.py` — New: markdown + live data interpolator

---

### 3.3 Memory Dreams as YAML Artifacts (Sequence #3)

**Effort**: 2-3 days  
**Builds on**: `core/dreaming/dream_cycle.py` (977 lines), `core/dreaming/narrative_compressor.py` (501 lines), `core/intelligence/bicameral.py` (513 lines)

**What**: When bicameral reasoning detects a creative bridge with `confidence < 0.5`, write it to `~/.whitemagic/dreams/YYYY-MM-DD_HH-MM-SS.yaml`. Nightly consolidation promotes high-revisit dreams to real memories.

**Why YAML**:
- Human-inspectable (read the AI's dreams)
- Git-diffable (track imagination evolution)
- Branchable (`dreams/experiment_7.yaml` without touching SQLite)
- Safe (bounded parsing, no code execution)
- Non-destructive (expire unless revisited)

**Schema**:
```yaml
dream_id: dream_20260425_223000_abc123
created_at: "2026-04-25T22:30:00Z"
source: bicameral_reasoner
confidence: 0.42
tension_score: 0.78
left_hemisphere: "Module caching should be deterministic"
right_hemisphere: "What if caching had emotional valence?"
creative_bridge: "Cache warmth — frequently-accessed items get 'warm' tags that boost recall priority"
keywords: [cache, valence, warmth, emotion]
revisit_count: 0
status: incubating  # incubating → reconsidered → promoted → archived → expired
```

**Files to create**:
- `core/whitemagic/core/dreaming/dream_artifacts.py` — `DreamArtifact` dataclass, YAML serializer, directory watcher
- `core/whitemagic/core/dreaming/dream_consolidator.py` — Nightly consolidation: check revisit counts, promote to memory, expire unvisited
- `core/whitemagic/tools/handlers/dream_artifacts.py` — `dream.list`, `dream.read`, `dream.promote`, `dream.expire`

**Integration points**:
- Bicameral reasoner emits `CREATIVE_BRIDGE_LOW_CONFIDENCE` event → DreamArtifact writer listens
- Dream daemon runs consolidation every night at 3AM (SLOW lane)
- Promoted dreams become memories with `dream_source` provenance

---

### 3.4 Jaynes Voice Audit (Sequence #4)

**Effort**: 3-4 days  
**Builds on**: `dharma/karma_ledger.py` (declared vs actual tracking), `tools/unified_api.py` (single entry point)

**What**: Scan internal command stream for un-logged / hallucinated tool invocations. If a module claims it called `delete_memory` but the Karma Ledger has no entry, quarantine the session.

**Named after**: Julian Jaynes' bicameral mind theory — the "voice" that commands action. In AI, this is the internal monologue generating tool-call intents.

**How it works**:
1. Every tool call through `call_tool()` writes to Karma Ledger
2. Every internal module that CLAIMS to have called a tool registers the claim in a parallel `claim_log`
3. Voice Audit scanner runs periodically: compare claims vs ledger
4. Mismatch = "hallucinated invocation" → quarantine, alert, flag for review

**Files to create**:
- `core/whitemagic/core/governance/voice_audit.py` — `VoiceAuditScanner`, `ClaimLog`, quarantine logic
- `core/whitemagic/core/governance/quarantine.py` — `QuarantineManager` (session isolation, review queue)
- `core/whitemagic/tools/handlers/voice_audit.py` — `voice_audit.scan`, `voice_audit.status`, `voice_audit.quarantine_list`

**Integration points**:
- Wired into `unified_api.call_tool()` as step 0.5 (after input sanitizer, before circuit breaker)
- Quarantine state feeds into Harmony Vector (cortisol spike)
- Audit trail anchored to Karma Ledger for external verification

---

### 3.5 Corpus Callosum Bus (Sequence #5)

**Effort**: 4-5 days  
**Builds on**: `core/intelligence/bicameral.py` (CrossCritique, HemisphereResult), `core/resonance/_consolidated.py` (GanYingBus)

**What**: A persistent bidirectional critique channel between "left hemisphere" (deterministic, precise) and "right hemisphere" (stochastic, creative). Not a one-shot `reason()` call — a living argument that resolves through synthesis.

**Protocol**:
```
Right Hemisphere: "I propose we merge the memory tiers."
    → emits to gan_ying://corpus_callosum/right

Left Hemisphere (listener): "Challenge: you haven't proven this preserves
                            the no-delete policy."
    → emits to gan_ying://corpus_callosum/left

Right Hemisphere: "Counter: galactic rotation already handles this."

Left Hemisphere: "Accepted with modification: require dry_run=True on first execution."
    → Synthesis event emitted. Both hemispheres agree.
```

**Files to create**:
- `core/whitemagic/core/intelligence/corpus_callosum.py` — `CorpusCallosumBus`, `HemisphereAgent`, `SynthesisArbiter`
- `core/whitemagic/core/intelligence/hemisphere_agents.py` — `LeftHemisphereAgent`, `RightHemisphereAgent` (event-driven listeners)
- `core/whitemagic/tools/handlers/corpus_callosum.py` — `corpus_callosum.debate`, `corpus_callosum.status`

**Safety guardrails**:
- Max rounds: 3 (prevents infinite loops)
- Timeout: 30 seconds per round
- Tension-score threshold: if >0.9, auto-escalate to Wisdom Council
- All debates logged to Karma Ledger

---

## Phase 4: Immediate Objectives (Single Session — 2026-04-26)

All 4 immediate objectives from `SESSION_SUMMARY.md` Section 10 were completed in one focused session (~22 minutes total).

### 4.1 MCP Startup Latency ✅
- Added `_LazyMCPTypes` and `_LazyServer` proxies to `run_mcp_lean.py`
- Deferred `mcp.types`, `mcp.server.Server`, `mcp.shared.message.SessionMessage`, `runtime_status`, `tool_surface`, and `fast_json` imports
- Module import time: ~2,800ms → ~400ms (7× improvement)
- Target <100ms not reached due to Python module parsing overhead; further gains require splitting the module

### 4.2 Stub Audit CI Gate ✅
- Created `core/scripts/check_stubs.py` with AST-based detection
- Filters: Click decorators, `@abstractmethod`, intentional no-op hooks (`_on_*`, `_check_*`, etc.)
- Allowlist support via `core/scripts/stub_allowlist.json` for known intentional empties
- Added `stub-audit` job to `.github/workflows/ci.yml`
- Current state: 5 genuine stubs tracked (down from 41)

### 4.3 Engine Registry Garden Bug ✅
- Fixed 18 garden mismatches in `core/engines/registry.py` to align with `grimoire/TRUTH_TABLE.md`
- Removed incorrect `test_all_gardens_unique` test (gardens are intentionally shared)
- Added `test_gardens_match_truth_table` that validates the canonical 28-fold mapping
- All 36 engine registry tests pass

### 4.4 Documentation Sync ✅
- Updated `SESSION_SUMMARY.md` test metrics table and immediate objectives status
- Updated `V22_2_ROADMAP.md` with Phase 4 completion section
- Updated `AGENTS.md` with time-tracking protocol refinements

---

## Updated Success Metrics

| Metric | v22.0.0 | v22.2 Phase 1 | v22.2 Phase 2 | v22.2 Final |
|--------|---------|---------------|---------------|-------------|
| Tests passing | 2,068 | 2,082 ✅ | 2,100+ ✅ | **2,154 ✅** |
| Tools with handlers | ~400 | 450+ ✅ | 450+ ✅ | **471 ✅** |
| Gana tools working | 0/28 | 28/28 ✅ | 28/28 ✅ | **28/28 ✅** |
| Broken core tools | 2+ | 0 ✅ | 0 ✅ | **0 ✅** |
| Neurotransmitter Vector | — | — | — | **7 dimensions ✅** |
| Grimoire MCP resources | 0 | 5 ✅ | 5 ✅ | **33 ✅** |
| Dream YAML artifacts | — | — | — | **Active ✅** |
| Voice Audit | — | — | — | **Scanning + quarantine ✅** |
| Corpus Callosum debates | — | — | — | **Available via MCP ✅** |
| Northern Quadrant avg lines | 141 | — | **484 ✅** | 484 ✅ |
| Fusions active | 13/28 | — | **23/28 ✅** | 23/28 ✅ |
| Polyglot languages building | 2/7 | — | 2/7 | **2/7** |

---

## Archive Recovery Status

| Wild Idea | Archive Found? | Action |
|-----------|---------------|--------|
| Neurotransmitter Vectors | ❌ No | Build fresh (2 days) |
| Grimoire as MCP Resource | ⚠️ Partial (MCP infra exists) | Extend existing resources (1-2 days) |
| Memory Dreams YAML | ❌ No | Build fresh using dream daemon + narrative compressor (2-3 days) |
| Jaynes Voice Audit | ❌ No | Build fresh using karma ledger + unified_api (3-4 days) |
| Corpus Callosum Bus | ❌ No | Build fresh using bicameral + gan_ying bus (4-5 days) |

**Total Phase 3 effort**: 12-17 days of focused implementation.

---

*Last updated: 2026-04-26*
