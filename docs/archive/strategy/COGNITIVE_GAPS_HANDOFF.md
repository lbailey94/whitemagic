# Cognitive System Gaps — Session Handoff

**Date**: 2026-06-24
**Status**: Survey complete. 5 gaps identified, prioritized by impact.

---

## Strategic Context

Per the 2026-06-24 strategic direction: **perfect reading, writing, memory, and cognitive systems BEFORE building self-directed evolution**. The memory pillar is strongest. The cognitive layer is the most fragmented. This guide covers the work needed to close the cognitive gaps.

---

## Gap 1: CorpusCallosumBus Heuristic Fallback

**File**: `core/whitemagic/core/intelligence/corpus_callosum.py` (324 lines)
**Priority**: High — this is the debate arbiter between left/right hemispheres

### Current State
The `debate()` method tries to use the real `BicameralReasoner` via `asyncio.run()`, but falls back to hardcoded string templates when async execution fails:
```python
# Line 261: Heuristic fallback (deterministic, no external deps)
left_pos = f"Left: '{topic}' requires systematic analysis..."
right_pos = f"Right: '{topic}' is an opportunity for creative..."
```

### What to Fix
1. The fallback fires when `asyncio.run()` raises — likely because an event loop is already running. Use `asyncio.get_event_loop().run_until_complete()` or `nest_asyncio` to handle nested loops.
2. The heuristic strings are static — they don't adapt to the topic. Even if kept as fallback, they should incorporate the topic context.
3. The `SynthesisArbiter` (decides consensus/tension/escalation) uses simple string matching — should use semantic similarity.

### How to Verify
```bash
cd core && python -m pytest tests/unit/test_bicameral.py tests/unit/test_corpus_callosum.py -v --timeout=15
```

---

## Gap 2: Cognitive Modes Enforcement in Dispatch Pipeline

**File**: `core/whitemagic/tools/unified_api.py` (lines 624-648)
**Priority**: Medium — partially implemented, needs completion

### Current State
The dispatch pipeline already checks cognitive mode and blocks avoided tools in GUARDIAN mode:
```python
if _cognitive_mode == "guardian":
    return _finish(err(..., error_code=ErrorCode.POLICY_BLOCKED, ...))
```

### What's Missing
1. **Only GUARDIAN blocks** — other modes (EXPLORER, EXECUTOR, REFLECTOR, BALANCED) log a warning but don't enforce. Should at least adjust behavior:
   - EXPLORER: prefer discovery/search tools, lower temperature
   - EXECUTOR: prefer write/action tools, higher strictness
   - REFLECTOR: prefer analysis/read tools, slower pace
2. **Mode persistence** — `_cognitive_mode` is a local variable, reset on every call. Should persist across calls within a session.
3. **Mode transitions** — no automatic mode switching based on task type. The `cognitive.hints` tool exists but isn't called automatically.

### How to Verify
```bash
cd core && python -m pytest tests/unit/test_cognitive_modes.py -v --timeout=15
```

---

## Gap 3: Working Memory → Scratchpad Wiring

**File**: `core/whitemagic/core/intelligence/working_memory.py` (293 lines)
**Priority**: Medium — working memory exists but isn't connected to session scratchpads

### Current State
Working memory has a bounded LRU cache (default 7 items, Miller's Law), time-based decay, and `attend()`/`group()`/`get_context()` methods. But it's not wired to the scratchpad system — scratchpads are managed separately in `core/whitemagic/core/` (session context Gana).

### What's Missing
1. **No bridge** — working memory and scratchpads don't share state. A scratchpad finalize should populate working memory. Working memory eviction should be logged to scratchpad.
2. **No token budget integration** — `get_context()` has a token budget parameter, but it's not used by the dispatch pipeline for prompt injection.
3. **No rehearsal mechanism** — `attend()` can rehearse (keep alive) or evict, but there's no automatic rehearsal based on tool usage patterns.

### How to Fix
1. In the scratchpad finalize handler, call `working_memory.attend()` for each key insight.
2. In `unified_api.py` dispatch, inject `working_memory.get_context()` into the tool context.
3. Add a periodic rehearsal check that keeps items referenced by recent tool calls.

### How to Verify
```bash
cd core && python -m pytest tests/unit/test_working_memory.py -v --timeout=15
```

---

## Gap 4: Self-Model Forecasts → Dispatch Feedback Loop

**File**: `core/whitemagic/core/intelligence/self_model.py` (331 lines)
**Priority**: Medium — forecasts exist but aren't fed back into dispatch decisions

### Current State
SelfModel tracks rolling windows of energy, karma debt, error rate, galactic distribution, drive, circuit breaker. It uses linear regression to forecast trends and generates alerts when thresholds are likely crossed. The `gnosis_portal()` method returns a dict with forecasts and alerts.

### What's Missing
1. **No dispatch integration** — forecasts are not checked before tool dispatch. If energy is forecasted to drop, the system should:
   - Reduce concurrency (fewer ThreadPoolExecutor workers)
   - Prefer lighter-weight tools
   - Skip optional enrichment steps
2. **No automatic recording** — metrics are recorded manually via `model.record()`. The dispatch pipeline should auto-record after each tool call:
   - `energy`: based on tool latency
   - `error_rate`: based on success/failure
   - `karma_debt`: from karma ledger
3. **No alert routing** — alerts are stored but not routed to the homeostasis loop or Dharma system.

### How to Fix
1. In `unified_api.py`, after each tool call, record metrics to self-model.
2. Before dispatch, check `self_model.get_alerts()` — if critical alerts exist, adjust behavior.
3. Route alerts to `homeostatic_loop` for corrective action.

### How to Verify
```bash
cd core && python -m pytest tests/unit/test_self_model.py -v --timeout=15
```

---

## Gap 5: MultiSpectralReasoner — Sequential Thinking Not Wired

**File**: `core/whitemagic/core/intelligence/multi_spectral_reasoning.py` (534 lines)
**Priority**: Low — the reasoner is more implemented than previously assessed

### Current State (Better Than Expected)
The `reason()` method has real implementations for:
- I Ching lens (cast hexagram → judgment/guidance)
- Wu Xing lens (identify element → suggest optimization)
- Art of War lens (get_war_wisdom → principle/application)
- Zodiac lens (find best core → activate → wisdom)
- Pattern matching (similarity to past reasoning history)
- Synthesis with consensus detection, theme extraction, weighted perspectives
- Recommendation generation with context-awareness

### What's Still Missing
1. **Sequential thinking** — `use_sequential_thinking=True` is accepted but the `thoughts` list is always empty. The sequential reasoning chain (step-by-step thought generation) is not implemented. Should use the `sequential-thinking` MCP tool pattern.
2. **No LLM integration** — all lenses use local heuristic systems (I Ching, Wu Xing, etc.). No option to route through an LLM for richer analysis.
3. **No memory persistence** — `reasoning_history` is in-memory only. Should persist to the memory DB for cross-session pattern matching.

### How to Fix
1. Implement `_sequential_think()` that breaks the question into sub-questions, reasons through each, and builds a thought chain.
2. Add an optional `llm_callback` parameter to `reason()` for LLM-augmented analysis.
3. Persist reasoning results to `UnifiedMemory` with type="reasoning".

### How to Verify
```bash
cd core && python -m pytest tests/unit/test_multi_spectral.py -v --timeout=15
```

---

## Suggested Session Order

1. **Gap 1** (CorpusCallosumBus) — highest impact, fixes the core reasoning debate
2. **Gap 4** (Self-Model feedback) — enables the system to self-regulate
3. **Gap 2** (Cognitive modes) — completes the dispatch enforcement
4. **Gap 3** (Working memory wiring) — connects two isolated systems
5. **Gap 5** (Sequential thinking) — enrichment, not critical path

Each gap is a 1-2 hour focused session. Run the full test suite after each fix.

---

## Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `core/whitemagic/core/intelligence/bicameral.py` | 607 | Dual-hemisphere reasoning (left=precise, right=creative) |
| `core/whitemagic/core/intelligence/corpus_callosum.py` | 324 | Debate bus between hemispheres |
| `core/whitemagic/core/intelligence/multi_spectral_reasoning.py` | 534 | 6-lens reasoning (I Ching, Wu Xing, Art of War, Zodiac, Sequential) |
| `core/whitemagic/core/intelligence/cognitive_modes.py` | 371 | 5 modes (EXPLORER, EXECUTOR, REFLECTOR, BALANCED, GUARDIAN) |
| `core/whitemagic/core/intelligence/working_memory.py` | 293 | Bounded LRU cache with decay, rehearsal, token budget |
| `core/whitemagic/core/intelligence/self_model.py` | 331 | Predictive introspection with linear regression forecasts |
| `core/whitemagic/core/intelligence/insight_pipeline.py` | 603 | Orchestrates 4 engines through CoreAccessLayer |
| `core/whitemagic/core/intelligence/foresight_engine.py` | 185 | Constellation drift, decay prediction, convergence detection |
| `core/whitemagic/tools/unified_api.py` | 764 | Dispatch pipeline (cognitive mode check at line 624) |
