# Cascade Error Investigation - v2.2.9

**Date**: November 17, 2025
**Issue**: 20% of AI models (Kimi K2, Qwen 3) caused Cascade internal errors during v2.2.8 testing
**Impact**: Reduces AI compatibility from potential 100% to 70%

---

## 🔍 Problem Statement

During multi-AI testing of WhiteMagic v2.2.8:

- **7/10 AIs succeeded** (GPT-5.1, GPT Codex, o3, DeepSeek R1, Grok 3 mini, Claude Haiku, Gemini)
- **2/10 AIs failed** (Kimi K2, Qwen 3) - Cascade internal errors
- **1/10 partially succeeded** (Cascade SWE-1) - Found bugs then crashed

**Pattern**: Failures are Cascade-specific, not WhiteMagic-specific.

---

## 🧩 Hypotheses

### Hypothesis 1: MCP Timeout Issues

**Theory**: Cascade's MCP client times out when WhiteMagic operations take too long.

**Evidence**:

- WhiteMagic operations (parallel reads, context loading) can take 5-10 seconds
- MCP default timeouts are often 5 seconds
- Kimi K2 and Qwen 3 may have slower processing speeds

**Mitigation Added**:

```typescript
// whitemagic-mcp/src/cache.ts
const CACHE_TTL_MS = 10 * 60 * 1000; // 10 minutes (was 5)
const MAX_CACHE_SIZE = 500; // (was 100)
```

**Test**: Increase MCP response timeouts in `whitemagic-mcp/src/index.ts`

---

### Hypothesis 2: Memory/Context Size Limits

**Theory**: Some AI models have stricter memory limits that Cascade enforces.

**Evidence**:

- WhiteMagic can return large contexts (100K+ characters)
- Tier 1/2 memory loads can be substantial
- Kimi K2 and Qwen 3 may have lower memory limits

**Mitigation**: Add size checks and truncation

```python
def get_context(tier, query, max_size=100000):
    context = load_tiered_context(tier, query)
    if len(context) > max_size:
        # Truncate and warn
        context = context[:max_size] + "\n\n[TRUNCATED]"
    return context
```

---

### Hypothesis 3: Tool Compatibility Issues

**Theory**: Certain MCP tools don't work with specific AI models.

**Evidence**:

- WhiteMagic uses advanced MCP features (parallel operations, streaming)
- Not all AI platforms implement full MCP spec
- Cascade may have model-specific tool restrictions

**Investigation Needed**:

1. Check which specific tools caused errors
2. Test with minimal tool set
3. Add graceful degradation

---

### Hypothesis 4: Error Recovery Gaps

**Theory**: WhiteMagic doesn't handle edge cases that trigger Cascade crashes.

**Evidence**:

- Cascade SWE-1 found 4 bugs before crashing
- May have hit an unhandled exception
- Cascade error reporting is opaque

**Mitigation**: Add comprehensive error handling

```python
try:
    result = whitemagic_operation()
except TimeoutError:
    return {"error": "timeout", "fallback": simplified_result()}
except MemoryError:
    return {"error": "memory", "fallback": None}
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return {"error": "unknown", "details": str(e)}
```

---

## 🔧 Immediate Actions (v2.2.9)

### 1. Add Response Size Limits

**File**: `whitemagic-mcp/src/index.ts`

```typescript
const MAX_RESPONSE_SIZE = 100000; // 100K chars

function truncateResponse(content: string): string {
    if (content.length > MAX_RESPONSE_SIZE) {
        return content.substring(0, MAX_RESPONSE_SIZE) +
               "\n\n[Response truncated for compatibility]";
    }
    return content;
}
```

### 2. Add Timeout Configuration

**File**: `whitemagic-mcp/src/client.ts`

```typescript
const DEFAULT_TIMEOUT = 30000; // 30 seconds (was implicit 5s)
const LONG_OPERATION_TIMEOUT = 60000; // 60 seconds for parallel ops
```

### 3. Add Graceful Degradation

**File**: `whitemagic/optimized_context.py`

```python
def get_tiered_context_safe(tier, query, fallback_tier=0):
    """Get context with automatic fallback on error."""
    try:
        return get_tiered_context(tier, query)
    except (TimeoutError, MemoryError):
        if fallback_tier < tier:
            return get_tiered_context_safe(fallback_tier, query, fallback_tier)
        return {"error": "context_unavailable", "tier": tier}
```

### 4. Add Debug Logging

**File**: `whitemagic-mcp/src/index.ts`

```typescript
server.setRequestHandler(ListResourcesRequestSchema, async (request) => {
    const startTime = Date.now();
    try {
        const result = await handleRequest(request);
        const duration = Date.now() - startTime;
        console.error(`[DEBUG] ListResources took ${duration}ms`);
        return result;
    } catch (error) {
        console.error(`[ERROR] ListResources failed:`, error);
        throw error;
    }
});
```

---

## 🧪 Testing Protocol

### Test Setup

1. Create minimal MCP test client
2. Test with increasing complexity:
   - Single memory read
   - Parallel reads (8 files)
   - Tiered context (Tier 0 → 1 → 2)
   - Large responses (50K, 100K, 200K chars)

### Success Criteria

- No crashes with responses up to 100K chars
- Graceful degradation on timeouts
- Clear error messages (no "internal error")
- 90%+ compatibility with AI models

---

## 📊 Metrics to Track

### Error Rate Metrics

```python
track_metric("cascade_errors", "error_rate", error_count / total_requests)
track_metric("cascade_errors", "timeout_rate", timeout_count / total_requests)
track_metric("cascade_errors", "memory_rate", memory_error_count / total_requests)
```

### Response Size Metrics

```python
track_metric("mcp_response", "avg_size_bytes", avg_response_size)
track_metric("mcp_response", "max_size_bytes", max_response_size)
track_metric("mcp_response", "truncation_rate", truncated_count / total_responses)
```

### Performance Metrics

```python
track_metric("mcp_latency", "p50_ms", p50_latency)
track_metric("mcp_latency", "p95_ms", p95_latency)
track_metric("mcp_latency", "p99_ms", p99_latency)
```

---

## 🎯 Expected Outcomes

### Short-Term (v2.2.9)

- Add size limits and timeouts
- Improve error messages
- Add debug logging
- **Goal**: Reduce error rate from 20% → 10%

### Medium-Term (v2.3.0)

- Test with Kimi K2 and Qwen 3 specifically
- Implement model-specific optimizations
- Add auto-tuning based on model capabilities
- **Goal**: Reduce error rate from 10% → 5%

### Long-Term (v2.4.0)

- Full compatibility matrix
- Automatic compatibility detection
- Model-specific presets
- **Goal**: 95%+ compatibility across all models

---

## 📝 Notes for Future Investigation

### Questions to Answer

1. Can we get Cascade error logs from failed sessions?
2. Do Kimi K2 and Qwen 3 have documented MCP limitations?
3. Is there a Cascade compatibility test suite?
4. Can we reproduce errors in isolation?

### Resources Needed

- Access to Kimi K2 and Qwen 3 for testing
- Cascade debugging tools
- MCP specification deep dive
- Error log analysis tools

---

## 🚀 Action Items for This Session

- [x] Document investigation hypotheses
- [ ] Implement response size limits (TypeScript)
- [ ] Add timeout configuration (TypeScript)
- [ ] Add graceful degradation (Python)
- [ ] Add debug logging (TypeScript)
- [ ] Test with large responses
- [ ] Update documentation

**Time Estimate**: 4 hours (matches Phase 1A plan)

---

**Status**: Investigation documented, implementation next
**Next Step**: Implement mitigations in MCP server and Python code
