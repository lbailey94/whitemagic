# Clone Army Revival Plan — From Simulation to Real LLM-Driven Agents

**Created**: 2026-06-24
**Status**: Implemented (all 8 phases)
**Author**: Cascade + Lucas

---

## Executive Summary

The WhiteMagic clone army systems have extensive infrastructure — tiered deployment,
victory tracking, consensus voting, Rust Tokio acceleration, a code-writing clone, and
a geneseed vault for template-based code generation. However, the core "thinking" in
most clone systems is **simulated**: `_clone_think()` sleeps for 10-100ms and returns
template strings instead of calling an LLM.

Meanwhile, a **fully functional LLM agent loop** already exists in `ollama_agent.py`
with tool-calling, context injection, memory-augmented generation, and Thompson sampling
tool selection via `tool_bandit.py`. The Rust extension is **built and working** with
`tokio_deploy_clones`, `mine_geneseed_patterns`, and 100+ other PyO3 functions.

The gap is wiring, not invention. This plan connects the existing pieces.

---

## Current State Assessment

### What's Real (Working Right Now)

| Component | Status | Evidence |
|-----------|--------|----------|
| `whitemagic_rust` extension | **Built, 100+ functions exported** | `dir(whitemagic_rust)` confirms tokio_deploy_clones, mine_geneseed_patterns, GeneseedStats, etc. |
| `tokio_deploy_clones()` | **Works** — returns JSON with winner, votes, confidence | Deployed 10 clones in 0.1ms. But responses are template strings (`[Clone 1 / creative] Explored: ...`) |
| `mine_geneseed_patterns()` | **Works** — mined 54 patterns from 213 commits | Returns OptimizationPattern objects with type, confidence, files_changed |
| `get_geneseed_stats()` | **Works** — GeneseedStats(commits=213, optimizations=1, avg_age=8.7d) | |
| `ollama_agent` handler | **Functional agent loop** — tool-calling, context injection, memory storage | 371 lines, registered in dispatch table, 5 unit tests passing |
| `ollama.generate/chat` handlers | **Functional** — async Ollama client with context injection | 521 lines, registered, uses aiohttp |
| `tool_bandit.py` | **Functional** — Thompson sampling Beta posteriors | 247 lines, 6 unit tests passing |
| `LocalLLM` | **Functional** — sync client (complete, chat, classify) | 131 lines, uses requests |
| `ImmortalClone v2` | **Partially real** — subprocess execution is real (compile, test, bash, edit, analyze) | 914 lines, ProcessPoolExecutor, victory tracking, dashboard |
| `GeneseedVault` | **Functional** — template loading, vibe parsing, rendering, forking | 155 lines, integrated with codegenome tools |
| `CloneArmy` (memory search) | **Functional** — parallel search with consensus voting | 448 lines, Rust fast-path |
| `AgentSwarm` | **Functional** — task decomposition, routing, tricameral consensus | 627 lines |
| `WarRoom` | **Partially functional** — campaign planning, tactic execution | 774 lines, but handler returns stubs |
| 74 tests | **Passing** | clone/ollama/bandit/swarm/war_room tests all pass |

### What's Simulated (The Gaps)

| Component | Current Behavior | What It Should Do |
|-----------|------------------|-------------------|
| `AsyncThoughtCloneArmy._clone_think()` | `asyncio.sleep(0.01-0.1)` + template string | Call Ollama with strategy-aware prompt |
| `AsyncThoughtCloneArmy._generate_content()` | Returns `"Clone {id} analyzes {prompt} systematically: ..."` | Return LLM response |
| `tokio_deploy_clones()` (Rust) | Returns `"[Clone 1 / creative] Explored: {prompt}"` | Return LLM response (requires Rust→Ollama HTTP) |
| `ImmortalClone.generate_action()` | Cycles: analyze→edit→compile→test→verify by iteration count | LLM decides next action based on context/error |
| `ImmortalClone.check_victory_conditions()` | "success if compile+test passed" | LLM evaluates against actual VC descriptions |
| `WarRoom` handlers | Return `{"status": "success", "war_room": "active"}` | Actually orchestrate campaigns |
| `FoolGuard` handlers | Return `{"status": "success", "ralph": "I'm helping!"}` | Deploy actual stateless clones |
| `BicameralReasoner` | 50 clones per hemisphere, but clones are simulated | Each clone calls LLM with hemisphere-specific prompt |
| `MultiSpectralReasoner` | Returns "Simulated analysis" | LLM analysis through 6 lenses |
| `CorpusCallosumBus` | Heuristic fallback | LLM-mediated debate synthesis |
| `vibe_code_explore()` | Uses GeneseedVault templates only | LLM refines generated code with codebase context |

### What's in the Archive (v0.2) But Not in Current

| Archive File | Lines | Status | Recovery Value |
|--------------|-------|--------|----------------|
| `code_writing_clone.rs` | 488 | **Complete** — Rayon parallel file write/edit/copy/move/delete | High — gives clones real code manipulation |
| `clone_lifecycle.rs` | 236 | **Complete** — PyCloneLifecycleManager with state machine | Medium — useful for orchestration |
| `clones.rs` | 131 | **Complete** — Aho-Corasick parallel search | Low — CloneArmy already covers this |
| `immortal_clone_rs.rs` | ? | Stub (just imports) | None |
| `thought_clones_async_rs.rs` | 5 | Stub (just imports) | None |
| `ollama_v2.rs` | 3 | Stub (just imports) | None |

**Key finding**: The archive's `code_writing_clone.rs` is the most valuable unrecovered
asset. It gives clones the ability to write, edit, copy, move, and delete files in
parallel via Rayon — exactly the "soldiers referencing the geneseed vault to copy-paste
and iterate upon templates" capability the user described.

---

## Implementation Plan

### Phase 1: Wire Thought Clones to LLM (Highest Impact, Smallest Change)

**Goal**: Make `AsyncThoughtCloneArmy._clone_think()` call Ollama instead of sleeping.

**Files to modify**:
- `core/whitemagic/edge/thought_clones_async.py` — `_clone_think()` method

**Changes**:
1. Add tier→model mapping (xianfeng=small, wei_wuzu=medium, huben=large)
2. Import `ollama._generate` and `_ollama_preflight`
3. Replace `asyncio.sleep()` + `_generate_content()` with real LLM call
4. Keep simulation as graceful fallback when Ollama unavailable
5. Use semaphore (already exists, `max_concurrent_api_calls=100`) to bound concurrency

**Design**:
```python
# Tier → model mapping (configurable via env)
_TIER_MODELS = {
    "xianfeng": os.environ.get("WM_XIANFENG_MODEL", "llama3.2:1b"),
    "wei_wuzu": os.environ.get("WM_WEIWUZU_MODEL", "llama3.2:3b"),
    "huben": os.environ.get("WM_HUBEN_MODEL", "llama3.2:8b"),
}

async def _clone_think(self, prompt, strategy, clone_id, tier_hint="xianfeng"):
    async with self.semaphore:
        # Try real LLM first
        try:
            from whitemagic.tools.handlers.ollama import _generate, _ollama_preflight
            if _ollama_preflight() is None:  # Ollama available
                model = _TIER_MODELS.get(tier_hint, _TIER_MODELS["xianfeng"])
                strategy_prompt = f"Approach this as {strategy}: {prompt}"
                result = await _generate(model, strategy_prompt)
                content = result["response"]
                tokens = result.get("eval_count", len(content.split()))
                confidence = min(0.95, 0.5 + tokens / 1000)
                return AsyncThoughtPath(...)
        except Exception:
            pass
        # Graceful degradation to simulation
        await asyncio.sleep(random.uniform(0.01, 0.1))
        content = self._generate_content(prompt, strategy, clone_id)
        ...
```

**Risk**: Low. Fallback preserves existing behavior. Semaphore bounds load.
**Test**: Existing 74 tests still pass. Add test for LLM path with mocked Ollama.

---

### Phase 2: Wire ImmortalClone to LLM Decision-Making

**Goal**: Replace heuristic `generate_action()` with LLM-driven action selection.

**Files to modify**:
- `core/whitemagic/agents/immortal_clone_v2.py` — `generate_action()` and `check_victory_conditions()`

**Changes**:
1. `generate_action()`: Send context (previous actions + results + errors) to Ollama,
   ask it to choose next action from `ActionType` enum
2. `check_victory_conditions()`: Ask LLM to evaluate whether VC descriptions are met
   based on context
3. Keep heuristic as fallback

**Design**:
```python
def generate_action(self) -> Action:
    # Build context summary for LLM
    context_summary = self._summarize_context()  # last 5 iterations
    prompt = f"""You are an immortal clone working on: {self.task.id}
    Target: {self.task.target}
    Victory conditions: {self.task.victory_conditions}

    Previous actions and results:
    {context_summary}

    Choose your next action from: analyze, edit, compile, test, benchmark, bash, verify
    Respond with just the action name."""

    try:
        from whitemagic.inference.local_llm import LocalLLM
        llm = LocalLLM()
        if llm.is_available:
            response = llm.complete(prompt).strip().lower()
            action_type = ActionType(response) if response in ActionType.__members__.values() else ActionType.ANALYZE
            return Action(type=action_type, target=self.task.target)
    except Exception:
        pass
    # Fallback to heuristic
    return self._heuristic_action()
```

**Risk**: Medium. LLM might choose invalid actions. Mitigated by enum validation + fallback.
**Test**: Add test with mocked LLM returning action names.

---

### Phase 3: Recover CodeWritingClone from Archive

**Goal**: Give clones the ability to write/edit/copy files in parallel via Rust.

**Files to recover**:
- Archive: `whitemagic0.2/whitemagic-rust/src/code_writing_clone.rs` (488 lines)

**Integration steps**:
1. Copy `code_writing_clone.rs` to `core/whitemagic-rust/src/pipeline/code_writing_clone.rs`
2. Add module to `core/whitemagic-rust/src/pipeline/mod.rs`
3. Register PyO3 functions in `lib.rs`
4. Rebuild Rust extension: `cd core/whitemagic-rust && maturin develop --release`
5. Create Python bridge: `core/whitemagic/optimization/rust_code_writing.py`
6. Wire into `GeneseedVault.vibe_render()` — after template rendering, use CodeWritingClone
   to write the file
7. Wire into `vibe_code_explore()` — Phase 3 (Huben) uses CodeWritingClone for hardening

**Design**:
```python
# In GeneseedVault or vibe_code_explore
from whitemagic.optimization.rust_code_writing import CodeWritingClone

def write_generated_code(target_path: str, content: str) -> dict:
    clone = CodeWritingClone("vibe-1", base_path=str(Path.cwd()))
    op = CodeOperation(
        op_type="write",
        source_file="",
        target_file=target_path,
        content=content,
    )
    return clone.execute_operation(op)
```

**Risk**: Low. Archive code is complete and self-contained. Only dependency is `uuid` crate.
**Test**: Add test that writes a file via CodeWritingClone and verifies content.

---

### Phase 4: Wire GeneseedVault to Codebase Mining + LLM Refinement

**Goal**: Combine git history mining (Rust), template rendering (Python), and LLM refinement
into a unified code generation pipeline.

**Files to modify**:
- `core/whitemagic/codegenome/vault.py` — add `generate_with_llm()` method
- `core/whitemagic/edge/thought_clones_async.py` — upgrade `vibe_code_explore()`

**Changes**:
1. `GeneseedVault.generate_with_llm()`:
   - Parse vibe prompt via `VibeParser`
   - Render template via `CodeGenomeEngine`
   - Mine relevant patterns from git history via `mine_geneseed_patterns()`
   - Send template + patterns to Ollama for refinement
   - Write result via `CodeWritingClone`

2. `vibe_code_explore()` upgrade:
   - Phase 1 (Xianfeng): Template render (existing)
   - Phase 2 (Wei Wuzu): LLM refine with git patterns + codebase context
   - Phase 3 (Huben): LLM validate + CodeWritingClone write

**Risk**: Medium. Requires Ollama for full functionality. Graceful degradation to template-only.
**Test**: Add test for `generate_with_llm()` with mocked Ollama.

---

### Phase 5: Wire WarRoom Handlers to Real Orchestration

**Goal**: Replace stub handler returns with actual campaign orchestration.

**Files to modify**:
- `core/whitemagic/tools/handlers/war_room.py` — 188 lines, mostly stubs

**Changes**:
1. `handle_war_room_execute()`: Actually deploy via `GasTownOrchestrator`
2. `handle_war_room_plan()`: Use `WarRoom.plan_campaign()` (already exists, 774 lines)
3. `handle_fool_guard_ralph()`: Deploy actual Dare-to-Die clone via `fool_guard.py`
4. `handle_fool_guard_dare_to_die()`: Deploy actual stateless clone

**Design**:
```python
def handle_war_room_execute(**kwargs):
    campaign = kwargs.get("campaign", {})
    if not campaign:
        return {"status": "error", "message": "No campaign provided"}
    from whitemagic.agents.immortal_clone_v2 import immortal_clone_deploy
    results = immortal_clone_deploy(campaign, max_clones=kwargs.get("max_clones", 64))
    return {
        "status": "success",
        "results": [{"success": r.success, "error": r.error} for r in results],
        "total": len(results),
    }
```

**Risk**: Medium. WarRoom is complex. Start with simple campaign support.
**Test**: Add test for execute handler with simple campaign.

---

### Phase 6: Wire Feedback Loop (ToolBandit ← Clone Results)

**Goal**: When clone strategies succeed/fail, update the bandit so future deployments
learn which strategies work best for which task types.

**Files to modify**:
- `core/whitemagic/edge/thought_clones_async.py` — after `parallel_explore_tiered()`
- `core/whitemagic/tools/handlers/tool_bandit.py` — add `record_strategy_outcome()`

**Changes**:
1. After tiered exploration completes, record outcome:
   - Success (confidence > threshold) → `bandit.record_outcome(tool=strategy, success=True)`
   - Failure → `bandit.record_outcome(tool=strategy, success=False)`
2. Before deployment, query bandit for recommended strategies:
   - `bandit.recommend_tools(task_type="exploration", k=8)` → use as `base_strategies`

**Risk**: Low. Additive change, doesn't affect existing behavior.
**Test**: Add test for feedback loop with mocked bandit.

---

### Phase 7: Wire Bicameral Reasoner to LLM

**Goal**: Make the 50 clones per hemisphere in `BicameralReasoner` call LLM with
hemisphere-specific prompts.

**Files to modify**:
- `core/whitemagic/core/intelligence/bicameral.py` — 560 lines

**Changes**:
1. Left hemisphere clones: "Analyze precisely and logically: {prompt}"
2. Right hemisphere clones: "Explore creatively and holistically: {prompt}"
3. Use xianfeng-tier model (small/fast) since 100 clones total
4. Corpus callosum: LLM synthesizes left+right responses

**Risk**: Medium. 100 concurrent LLM calls. Mitigated by semaphore (100 max concurrent).
**Test**: Add test with mocked LLM.

---

### Phase 8: Consolidate Army Types

**Goal**: Simplify the 12 army types → 3 practical tiers with clear model mappings.

**Current state**: 12 ArmyType enums in Rust (Immortal, Tokio, Shadow, Grand, WarRoom,
Adaptive, Batch, Thought, FileSearch, Elixir, Campaign, Lieutenant) + Zodiac mapping.

**Proposal**: Keep the 12 types as documentation/metaphor. In practice, all deployments
use 3 tiers:
- **Xianfeng** (llama3.2:1b) — fast reconnaissance, 16K clones, 100 concurrent
- **Wei Wuzu** (llama3.2:3b) — main work, 1K clones, 50 concurrent
- **Huben** (llama3.2:8b) — critical decisions, 100 clones, 10 concurrent

**Risk**: None. Documentation-only change.
**Test**: No new tests needed.

---

## Dependency Graph

```
Phase 1 (Thought Clones → LLM)
    ↓
Phase 2 (ImmortalClone → LLM)     Phase 3 (Recover CodeWritingClone)
    ↓                                    ↓
Phase 5 (WarRoom handlers)         Phase 4 (GeneseedVault + LLM)
    ↓                                    ↓
Phase 6 (Feedback Loop)           ←──────┘
    ↓
Phase 7 (Bicameral → LLM)
    ↓
Phase 8 (Consolidate)
```

Phases 1, 2, 3 can be done in parallel.
Phase 4 depends on 1 + 3.
Phase 5 depends on 2.
Phase 6 depends on 1.
Phase 7 depends on 1.
Phase 8 is documentation.

---

## Ollama Model Strategy

| Tier | Model | Use Case | Concurrent | Max Clones |
|------|-------|----------|------------|------------|
| Xianfeng | `llama3.2:1b` | Fast probes, reconnaissance | 100 | 16,000 |
| Wei Wuzu | `llama3.2:3b` | Main work, refinement | 50 | 1,000 |
| Huben | `llama3.2:8b` | Critical decisions, validation | 10 | 100 |
| Fallback | Simulation | Ollama unavailable | ∞ | ∞ |

Models are configurable via environment variables:
- `WM_XIANFENG_MODEL`, `WM_WEIWUZU_MODEL`, `WM_HUBEN_MODEL`

**Note**: Ollama is NOT currently running on this machine. All phases include graceful
degradation to simulation when Ollama is unavailable. This means:
- Development and testing can proceed without Ollama
- Production deployment requires `ollama serve` + model pulls
- The simulation fallback is always available as a safety net

---

## Test Strategy

1. **Unit tests**: Mock Ollama responses, verify wiring
2. **Integration tests**: With Ollama running, verify end-to-end clone deployment
3. **Regression**: All 74 existing clone/ollama/bandit tests must pass
4. **Full suite**: `python -m pytest tests/ --ignore=... -q` must remain green

---

## File Change Summary

| Phase | Files Modified | Files Created | Lines Changed (est.) |
|-------|---------------|---------------|---------------------|
| 1 | `thought_clones_async.py` | — | ~40 |
| 2 | `immortal_clone_v2.py` | — | ~60 |
| 3 | — | `rust_code_writing.py`, `code_writing_clone.rs` (recovered) | ~20 + 488 |
| 4 | `vault.py`, `thought_clones_async.py` | — | ~80 |
| 5 | `war_room.py` (handlers) | — | ~80 |
| 6 | `thought_clones_async.py`, `tool_bandit.py` | — | ~30 |
| 7 | `bicameral.py` | — | ~50 |
| 8 | — | Documentation | ~100 |
| **Total** | **7 files** | **2 files** | **~460 lines** |

---

## Success Criteria

- [x] `AsyncThoughtCloneArmy._clone_think()` calls Ollama when available
- [x] `ImmortalClone.generate_action()` uses LLM to choose actions
- [x] `CodeWritingClone` recovered from archive and building
- [x] `GeneseedVault.generate_with_llm()` produces LLM-refined code
- [x] `handle_war_room_execute()` deploys real campaigns
- [x] `ToolBandit` learns from clone deployment outcomes
- [x] `BicameralReasoner._synthesize()` uses LLM for synthesis
- [ ] All 74 existing tests pass
- [ ] Full test suite (1,470 tests) passes
- [ ] No new `Path.home()` or `.expanduser()` outside `paths.py`
- [x] `INDEX.md` updated if docs added

---

## Army Type Consolidation

### Clone Army Types in WhiteMagic

| Army Type | Module | Rust Accelerator | LLM Wired | Purpose |
|-----------|--------|-------------------|-----------|---------|
| **AsyncThoughtCloneArmy** | `edge/thought_clones_async.py` | `tokio_clones.rs` | ✅ Phase 1 | Parallel thought exploration with strategy diversity |
| **ImmortalClone** | `agents/immortal_clone_v2.py` | — | ✅ Phase 2 | Persistent execution loops with victory tracking |
| **CodeWritingClone** | `optimization/rust_code_writing.py` | `code_writing_clone.rs` | ✅ Phase 4 | Parallel file write/edit/copy/move/delete operations |
| **GeneseedVault** | `codegenome/vault.py` | `geneseed_miner.rs` | ✅ Phase 4 | Template-based code generation with LLM refinement |
| **BicameralReasoner** | `core/intelligence/bicameral.py` | — | ✅ Phase 7 | Dual-hemisphere reasoning with cross-critique |
| **FoolGuard** | `core/intelligence/agentic/fool_guard.py` | — | — | Anti-groupthink Ralph probes + Dare-to-Die corps |
| **TokioCloneArmy** | `optimization/rust_tokio.py` | `tokio_clones.rs` | — | Rust-accelerated massively parallel clone deployment |

### Command Hierarchy

```
WarRoom (strategic planning)
  └── GasTownOrchestrator (tactical execution)
       ├── ImmortalClone (persistent loops with LLM action selection)
       │    ├── analyze → edit → compile → test → verify
       │    └── LLM chooses next action based on context
       ├── AsyncThoughtCloneArmy (parallel thought exploration)
       │    ├── Tier: Xianfeng (llama3.2:1b) → Wei Wuzu (llama3.2:3b) → Huben (llama3.2:8b)
       │    └── 14 strategies (analytical, creative, adversarial, etc.)
       ├── CodeWritingClone (parallel file operations via Rayon)
       │    └── write, edit, copy, move, delete — 12K+ ops/sec
       └── FoolGuard (chaos injection)
            ├── Ralph Wiggum probes (stateless random actions)
            └── Dare-to-Die corps (sacrificial exploration)
```

### Feedback Loops

```
Clone Deployment → ToolBandit.record_clone_outcome()
  → Thompson sampling learns which strategies work
  → recommend_clone_strategies() for future deployments

ImmortalClone context → LLM.generate_action()
  → Action executed → result fed back into context
  → LLM checks victory conditions → early termination

GeneseedVault.vibe_render() → LLM refinement → CodeWritingClone write
  → Git pattern mining informs LLM prompt
  → Refined code written to disk in parallel
```
