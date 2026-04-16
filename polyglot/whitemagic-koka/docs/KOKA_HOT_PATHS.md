# Koka Hot Path Migration Priorities (S023)

**Generated:** 2026-02-21  
**Based on:** Python baseline benchmark results from `reports/S023_koka_benchmarks.md`

## Benchmark Summary

| Operation | Python (µs) | Priority | Reason |
|-----------|-------------|----------|--------|
| PRAT Dispatch | 1.00 | **HIGH** | Core to every MCP call |
| Gana Invoke | 1.12 | **HIGH** | 28 Ganas = frequent dispatch |
| Circuit Breaker | 0.75 | **MEDIUM** | Error paths, not hot |
| Resonance Tracking | 5.36 | **HIGH** | 5× slower, called per invocation |
| 28-Gana Chain | 32.06 | **CRITICAL** | Complex composition, ideal for Koka |

## Identified Hot Paths

### 1. Resonance Tracking (CRITICAL - 5.36 µs)
**Location:** `whitemagic/tools/prat_resonance.py`  
**Why Koka:** State machine with typed effects perfect for algebraic handlers
**Impact:** Called on every PRAT invocation (~5µs overhead)
**Effort:** 1 session (already have Koka effect)

```python
# Current Python
def track_prat_invocation(gana_name, tool_name, output):
    # ~5µs due to state lookups, lunar calculations
    
# Koka equivalent
# effect resonance
#   fun track-invocation(gana, tool, output): snapshot
# Single handler with all state in effect row
```

### 2. PRAT Dispatch Chain (HIGH - 1.00 µs)
**Location:** `whitemagic/tools/prat_router.py:route_prat_call()`  
**Why Koka:** Handler chain (auth → rate limit → route → log) maps to effect composition
**Impact:** Every MCP tool call flows through here
**Effort:** 1-2 sessions (complex Python dependencies)

```python
# Current: sequential Python calls
def route_prat_call(tool, context):
    if not auth_check(context): raise
    if not rate_limiter.allow(context): raise
    result = dispatch(tool)
    karma_log(context, result)
    return result

# Koka: composed effects
# route-prat-call with <prat-auth, prat-rate, prat-route, prat-karma>
```

### 3. Gana Handler Composition (HIGH - 32.06 µs chain)
**Location:** `whitemagic/tools/prat_router.py` Gana dispatch  
**Why Koka:** 28 Gana handlers as polymorphic effect instances
**Impact:** Multi-Gana sequences (rare but expensive)
**Effort:** 2 sessions (need complete 28 specializations)

```koka
// Sequential composition gains from single process
fun chain-ganas(names: list<string>, input: string): string
  names.foldl(input) fn(acc, gana)
    invoke-gana(gana, "process", acc)
```

### 4. Dream Cycle Phase Transitions (MEDIUM)
**Location:** `whitemagic/core/intelligence/dream_cycle.py`  
**Why Koka:** 8 phases as effect state machine
**Impact:** Batch operation, not per-call hot path
**Effort:** 1 session (effect already implemented)

### 5. Circuit Breaker + Retry + Timeout (MEDIUM)
**Location:** Error handling throughout  
**Why Koka:** Composable error effects
**Impact:** Only on failures, not normal paths
**Effort:** ½ session (effects complete, just wiring)

## Migration Order Recommendation

1. **Phase 1:** Resonance tracking (quick win, clear isolation)
2. **Phase 2:** PRAT dispatch (biggest impact, needs careful testing)
3. **Phase 3:** Complete 28 Gana specializations (enables composition)
4. **Phase 4:** Dream cycle (batch background process)
5. **Phase 5:** Error handling (compose with other effects)

## Prerequisites for Each

| Path | Prerequisites |
|------|---------------|
| Resonance | Koka compiler, FFI bridge working |
| PRAT | Rust/JSON bridge for complex args, Python callback integration |
| Gana | Complete 20 more Gana specializations in Koka |
| Dream | Koka scheduler integration for background tasks |
| Errors | All other effects stable (error handlers wrap them) |

## Expected Performance Gains

Based on benchmark baselines and Koka effect handler optimization:

| Path | Python | Koka Target | Expected Speedup |
|------|--------|-------------|------------------|
| Resonance tracking | 5.36 µs | 2-3 µs | **2×** |
| PRAT dispatch chain | 4-5 µs | 2-3 µs | **1.5-2×** |
| Gana composition | 32 µs (chain) | 15-20 µs | **1.5-2×** |
| Error handling | Variable | Consistent | **Maintainability** |

Note: Single operations may have FFI overhead, but chains/compositions should win.

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Koka compile time | Cache binaries, incremental builds |
| FFI overhead | Batch operations, persistent processes |
| Python interop complexity | Start with simple, isolated operations |
| Debugging difficulty | Effect visualization tool (completed in S022) |

## Next Steps

1. Install Koka compiler (v3.2.2+) in environment
2. Compile `prat_resonance.kk` → native binary
3. Wire resonance tracking to use Koka
4. Benchmark Python vs Koka resonance
5. If successful, proceed to PRAT dispatch

## Files Ready for Implementation

- `whitemagic-koka/src/effects/prat_resonance.kk` — Complete
- `whitemagic/core/acceleration/koka_native_bridge.py` — Complete
- `whitemagic/tools/prat_resonance.py` — Ready for integration

## Blocking Issues

1. **Koka compiler not available** — Need environment setup
2. **No compiled binaries** — Build system ready, needs compiler
3. **FFI latency unknown** — Will know after first compile

See `campaigns/S023_koka_hot_path_activation.md` for detailed VCs and build steps.
